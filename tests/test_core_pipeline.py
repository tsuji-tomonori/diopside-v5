import json

import pytest

from diopside_core import MemoryRepository, YouTubeClient, build_timestamp_candidates, extract_initial_data_from_watch_html, normalize_replay_actions, normalize_video_resource, parse_iso8601_duration, summarize_chat_messages
from static_exporter.pipeline import cancel_job, chat_collect, chat_normalize, dispatch_job, metadata_sync, rebuild_artifacts, retry_job


def test_youtube_video_normalization():
    video = normalize_video_resource(
        {
            "id": "abc123",
            "snippet": {"title": "title", "description": "desc", "publishedAt": "2026-05-28T00:00:00Z", "channelId": "ch", "tags": ["雑談"]},
            "contentDetails": {"duration": "PT1H02M03S"},
            "liveStreamingDetails": {"actualEndTime": "2026-05-28T01:00:00Z"},
            "statistics": {"viewCount": "10"},
            "status": {"privacyStatus": "public"},
        }
    )
    assert parse_iso8601_duration("PT1H02M03S") == 3723
    assert video["video_id"] == "abc123"
    assert video["duration_sec"] == 3723
    assert video["live_state"] == "archived"


def test_youtube_client_uses_http_mock(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self):
            return json.dumps({"items": [{"id": "abc123"}]}).encode("utf-8")

    requested = {}

    def fake_urlopen(url, timeout):
        requested["url"] = url
        requested["timeout"] = timeout
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = YouTubeClient(api_key="test-key", base_url="https://example.test/youtube/v3")
    result = client.videos(["abc123"])
    assert result["items"][0]["id"] == "abc123"
    assert "videos?" in requested["url"]
    assert "key=test-key" in requested["url"]
    assert requested["timeout"] == 20


def test_replay_parser_normalizes_known_and_unknown_renderer():
    messages = normalize_replay_actions(
        [
            {
                "replayChatItemAction": {
                    "videoOffsetTimeMsec": "83000",
                    "actions": [
                        {
                            "addChatItemAction": {
                                "item": {
                                    "liveChatTextMessageRenderer": {
                                        "id": "m1",
                                        "authorExternalChannelId": "author1",
                                        "authorName": {"simpleText": "Alice"},
                                        "timestampText": {"simpleText": "1:23"},
                                        "timestampUsec": "1000",
                                        "videoOffsetTimeMsec": "999999",
                                        "message": {"runs": [{"text": "ありがとう"}, {"emoji": {"shortcuts": [":)"]}}]},
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            {"unknownRenderer": {"value": 1}},
        ],
        "vid001",
    )
    assert messages[0]["message_text"] == "ありがとう:)"
    assert messages[0]["video_offset_time_msec"] == 83000
    assert messages[0]["message_runs"][1]["type"] == "emoji"
    assert messages[1]["parse_warning"] == "unknown_renderer"


def test_public_replay_initial_data_extractor():
    html = 'x; ytInitialData = {"actions":[{"addChatItemAction":{"item":{"liveChatTextMessageRenderer":{"id":"m1","message":{"runs":[{"text":"hello"}]}}}}}]}; y'
    data = extract_initial_data_from_watch_html(html)
    collected = chat_collect(MemoryRepository(), {"video_id": "vid001", "mode": "replay", "replay_initial_data": data})
    assert collected["source"] == "replay"
    assert collected["message_count"] == 1


def test_pipeline_collect_normalize_and_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    repo = MemoryRepository()
    metadata_sync(
        repo,
        {
            "video_resources": [
                {
                    "id": "vid001",
                    "snippet": {"title": "公開アーカイブ", "description": "00:10 開始", "publishedAt": "2026-05-28T00:00:00Z", "channelId": "ch"},
                    "contentDetails": {"duration": "PT10M"},
                    "liveStreamingDetails": {},
                    "statistics": {},
                    "status": {"privacyStatus": "public"},
                }
            ]
        },
    )
    chat_collect(
        repo,
        {
            "video_id": "vid001",
            "mode": "replay",
            "replay_actions": [
                {
                    "addChatItemAction": {
                        "item": {
                            "liveChatTextMessageRenderer": {
                                "id": "m1",
                                "authorExternalChannelId": "author1",
                                "authorName": {"simpleText": "Alice"},
                                "timestampUsec": "1000",
                                "videoOffsetTimeMsec": "60000",
                                "message": {"runs": [{"text": "ありがとう ありがとう"}]},
                            }
                        }
                    }
                }
            ],
        },
    )
    normalized = chat_normalize(repo, {"video_id": "vid001"})
    artifacts = rebuild_artifacts(repo, {"video_id": "vid001"})
    assert normalized["message_count"] == 1
    chunks = repo.list_chat_chunks("vid001")
    assert chunks[0]["message_count"] == 1
    assert "messages" not in chunks[0]
    assert chunks[0]["s3_uri"]
    assert chunks[0]["sha256"]
    assert chunks[0]["first_offset_msec"] == 60000
    assert chunks[0]["last_offset_msec"] == 60000
    assert artifacts["wordcloud_available"] is True
    assert repo.get_chat_aggregate("vid001")["top_terms"][0]["term"] == "ありがとう"
    assert list((tmp_path / "raw/youtube").rglob("*.json"))
    assert list((tmp_path / "processed/chat-normalized").rglob("*.jsonl"))
    assert list((tmp_path / "processed/chat-aggregate").rglob("summary.json"))


def test_chat_normalize_reads_s3_jsonl_manifest_not_dynamodb_messages(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    repo = MemoryRepository()
    raw_path = tmp_path / "raw/youtube/chat/video_id=vid001/source=replay/part-000.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        json.dumps(
            {
                "message_id": "m1",
                "video_id": "vid001",
                "source": "replay",
                "message_type": "text",
                "author_external_channel_id": "a1",
                "message_runs": [{"type": "text", "text": "ありがとう ありがとう"}],
                "message_text": "ありがとう ありがとう",
                "video_offset_time_msec": 60000,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    repo.put_item(
        {
            "item_type": "ChatMessageChunkManifest",
            "pk": "VIDEO#vid001",
            "sk": "CHAT#RAW#replay#fixture",
            "video_id": "vid001",
            "source": "replay",
            "s3_uri": "raw/youtube/chat/video_id=vid001/source=replay/part-000.jsonl",
            "message_count": 1,
            "sha256": "fixture",
            "first_offset_msec": 60000,
            "last_offset_msec": 60000,
            "next_poll": None,
        }
    )
    normalized = chat_normalize(repo, {"video_id": "vid001"})
    assert normalized["message_count"] == 1
    assert repo.get_chat_aggregate("vid001")["top_terms"][0]["term"] == "ありがとう"


def test_timestamp_candidates_include_keyword_spike():
    summary = summarize_chat_messages(
        [
            {"message_text": "ありがとう", "video_offset_time_msec": 60000, "message_runs": []},
            {"message_text": "ありがとう", "video_offset_time_msec": 61000, "message_runs": []},
            {"message_text": "ありがとう", "video_offset_time_msec": 62000, "message_runs": []},
            {"message_text": "別語", "video_offset_time_msec": 180000, "message_runs": []},
        ]
    )
    candidates = build_timestamp_candidates(summary)
    assert any(candidate["source"] == "keyword_spike" and candidate["evidence_terms"] == ["ありがとう"] for candidate in candidates)


def test_repository_job_idempotency_and_lists():
    repo = MemoryRepository()
    repo.put_item({"item_type": "Channel", "pk": "CHANNEL#ch", "sk": "META", "channel_id": "ch", "uploads_playlist_id": "uploads"})
    repo.record_quota_usage("videos.list", 1, {"video_count": 1})
    first, dedup_first = repo.create_job("metadata_sync", {"channel_id": "ch"}, "same-key")
    second, dedup_second = repo.create_job("metadata_sync", {"channel_id": "ch"}, "same-key")
    repo.append_job_event(first["job_id"], "completed", {"saved_count": 0})

    assert dedup_first is False
    assert dedup_second is True
    assert second["job_id"] == first["job_id"]
    assert repo.get_job(first["job_id"])["derived_state"] == "succeeded"
    assert repo.list_channels()[0]["channel_id"] == "ch"
    assert repo.list_quota_usage()[0]["method"] == "videos.list"


def test_failed_job_writes_debug_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    repo = MemoryRepository()
    created, _ = repo.create_job("unknown", {}, "failed-job")
    with pytest.raises(ValueError):
        dispatch_job(repo, {"job_type": "unknown", "job_id": created["job_id"]})
    job = repo.get_job(created["job_id"])
    assert job["derived_state"] == "failed"
    assert job["events"][-1]["details"]["debug_uri"].endswith(".json")
    assert list((tmp_path / f"failed/jobs/job_id={created['job_id']}").rglob("*.json"))


def test_retry_and_cancel_job_update_target_events():
    repo = MemoryRepository()
    failed, _ = repo.create_job("chat_normalize", {"video_id": "vid001"}, "retry-source")
    repo.append_job_event(failed["job_id"], "failed", {"message": "boom"})
    retry = retry_job(repo, {"target_job_id": failed["job_id"], "reason": "manual"})
    assert retry["target_job_id"] == failed["job_id"]
    assert retry["enqueued"] is False
    assert repo.get_job(failed["job_id"])["events"][-1]["event_type"] == "retry_requested"

    queued, _ = repo.create_job("chat_collect", {"video_id": "vid002"}, "cancel-source")
    cancelled = cancel_job(repo, {"target_job_id": queued["job_id"], "reason": "manual"})
    assert cancelled["cancelled"] is True
    assert repo.get_job(queued["job_id"])["derived_state"] == "cancelled"
