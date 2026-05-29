import json

import pytest

from botocore.exceptions import ClientError

from diopside_core import DynamoRepository, MemoryRepository, YouTubeClient, build_timestamp_candidates, extract_initial_data_from_watch_html, extract_replay_continuations_from_initial_data, normalize_replay_actions, normalize_video_resource, parse_iso8601_duration, summarize_chat_messages
import static_exporter.pipeline as pipeline
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


class FakeYouTubeMetadataClient:
    def __init__(self):
        self.playlist_calls = []
        self.video_calls = []

    def playlist_items(self, playlist_id, page_token=None, max_results=50):
        self.playlist_calls.append({"playlist_id": playlist_id, "page_token": page_token, "max_results": max_results})
        return {
            "nextPageToken": "next-token",
            "items": [
                {"contentDetails": {"videoId": "vid001"}},
                {"contentDetails": {"videoId": "vid002"}},
            ],
        }

    def videos(self, video_ids):
        self.video_calls.append(list(video_ids))
        return {
            "items": [
                {
                    "id": video_id,
                    "snippet": {"title": video_id, "description": "", "publishedAt": "2026-05-28T00:00:00Z", "channelId": "ch"},
                    "contentDetails": {"duration": "PT1M"},
                    "liveStreamingDetails": {},
                    "statistics": {},
                    "status": {"privacyStatus": "public"},
                }
                for video_id in video_ids
            ]
        }


def test_metadata_sync_paginates_saves_raw_and_cursor(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    enqueued = []
    monkeypatch.setattr(pipeline, "_enqueue_job", lambda queue_env, payload, delay_seconds=0: enqueued.append({"queue_env": queue_env, "payload": payload}) or "queued")
    repo = MemoryRepository()
    client = FakeYouTubeMetadataClient()

    result = metadata_sync(
        repo,
        {
            "youtube_client": client,
            "channel_id": "ch",
            "uploads_playlist_id": "uploads",
            "max_results": 2,
        },
    )

    cursor = repo.get_item("CHANNEL#ch", "CURSOR#metadata")
    video = repo.get_video("vid001")
    assert result["next_page_token"] == "next-token"
    assert result["raw_playlist_uri"]
    assert result["raw_videos_uri"]
    assert cursor["next_page_token"] == "next-token"
    assert cursor["last_video_ids"] == ["vid001", "vid002"]
    assert "items" not in cursor
    assert video["raw_metadata_uri"] == result["raw_videos_uri"]
    assert "items" not in video
    assert client.playlist_calls[0]["page_token"] is None
    assert enqueued[0]["queue_env"] == "DIOPSIDE_METADATA_QUEUE_URL"
    assert enqueued[0]["payload"]["input"]["page_token"] == "next-token"
    assert list((tmp_path / "raw/youtube/metadata/channel_id=ch/playlistItems").glob("*.json"))
    assert list((tmp_path / "raw/youtube/metadata/channel_id=ch/videos").glob("*.json"))


def test_metadata_sync_resumes_from_channel_cursor(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr(pipeline, "_enqueue_job", lambda queue_env, payload, delay_seconds=0: None)
    repo = MemoryRepository()
    repo.put_item(
        {
            "item_type": "ChannelCursor",
            "pk": "CHANNEL#ch",
            "sk": "CURSOR#metadata",
            "channel_id": "ch",
            "cursor_name": "metadata",
            "next_page_token": "resume-token",
            "updated_at": "2026-05-29T00:00:00Z",
        }
    )
    client = FakeYouTubeMetadataClient()

    metadata_sync(repo, {"youtube_client": client, "channel_id": "ch", "uploads_playlist_id": "uploads"})

    assert client.playlist_calls[0]["page_token"] == "resume-token"


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
    assert collected["parser_stats"]["action_count"] == 1


def test_public_replay_initial_data_keeps_unknown_renderer_and_continuation(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    html = """
    <script>
    ytInitialData = {
      "contents": {
        "twoColumnWatchNextResults": {
          "conversationBar": {
            "liveChatRenderer": {
              "continuations": [
                {"reloadContinuationData": {"continuation": "replay-token-1", "timeoutMs": 1500}}
              ],
              "actions": [
                {
                  "replayChatItemAction": {
                    "videoOffsetTimeMsec": "12000",
                    "actions": [
                      {
                        "addChatItemAction": {
                          "item": {
                            "liveChatTextMessageRenderer": {
                              "id": "m-known",
                              "authorExternalChannelId": "author1",
                              "authorName": {"simpleText": "Alice"},
                              "timestampUsec": "1000",
                              "timestampText": {"simpleText": "0:12"},
                              "message": {"runs": [{"text": "hello replay"}]}
                            }
                          }
                        }
                      }
                    ]
                  }
                },
                {
                  "replayChatItemAction": {
                    "videoOffsetTimeMsec": "13000",
                    "actions": [
                      {
                        "addChatItemAction": {
                          "item": {
                            "liveChatMembershipItemRenderer": {
                              "id": "m-unknown",
                              "headerSubtext": {"simpleText": "joined"}
                            }
                          }
                        }
                      }
                    ]
                  }
                }
              ]
            }
          }
        }
      }
    };
    </script>
    """
    data = extract_initial_data_from_watch_html(html)
    continuations = extract_replay_continuations_from_initial_data(data)
    repo = MemoryRepository()

    collected = chat_collect(repo, {"video_id": "vid-replay", "mode": "replay", "replay_initial_data": data})

    raw_files = list((tmp_path / "raw/youtube/chat/video_id=vid-replay/source=replay").glob("*.jsonl"))
    rows = [json.loads(line) for line in raw_files[0].read_text(encoding="utf-8").splitlines()]
    chunk = repo.list_chat_chunks("vid-replay")[0]
    assert continuations == [{"token": "replay-token-1", "source": "reloadContinuationData", "timeout_ms": 1500}]
    assert collected["message_count"] == 2
    assert collected["parser_stats"]["action_count"] == 2
    assert collected["parser_stats"]["unknown_count"] == 1
    assert collected["next_poll"]["action"] == "continuation_available"
    assert collected["next_poll"]["continuation_count"] == 1
    assert chunk["parser_stats"]["unknown_count"] == 1
    assert chunk["next_poll"]["continuations"][0]["token"] == "replay-token-1"
    assert rows[0]["message_text"] == "hello replay"
    assert rows[1]["parse_warning"] == "unknown_renderer"
    assert rows[1]["raw_renderer_type"] == "liveChatMembershipItemRenderer"
    assert rows[1]["raw_renderer"]["id"] == "m-unknown"


def test_live_chat_collect_requeues_with_clamped_delay(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    enqueued = []
    monkeypatch.setattr(pipeline, "_enqueue_job", lambda queue_env, payload, delay_seconds=0: enqueued.append({"queue_env": queue_env, "payload": payload, "delay_seconds": delay_seconds}) or "queued")
    repo = MemoryRepository()
    repo.put_video({"video_id": "live001", "title": "live", "published_at": "2026-05-29T00:00:00Z", "live_chat_id": "chat001"})

    result = chat_collect(
        repo,
        {
            "video_id": "live001",
            "mode": "live",
            "live_chat_response": {
                "nextPageToken": "next-live-token",
                "pollingIntervalMillis": 950000,
                "items": [{"id": "m1", "snippet": {"displayMessage": "hello", "publishedAt": "2026-05-29T00:00:00Z"}, "authorDetails": {"channelId": "a1", "displayName": "Alice"}}],
            },
        },
    )

    chunks = repo.list_chat_chunks("live001")
    assert result["next_poll"]["action"] == "requeue"
    assert result["next_poll"]["delay_seconds"] == 950
    assert result["next_poll"]["requeue_delay_seconds"] == 900
    assert enqueued[0]["queue_env"] == "DIOPSIDE_CHAT_QUEUE_URL"
    assert enqueued[0]["delay_seconds"] == 900
    assert enqueued[0]["payload"]["input"]["page_token"] == "next-live-token"
    assert chunks[0]["next_poll"]["action"] == "requeue"
    assert chunks[0]["message_count"] == 1
    assert chunks[0]["s3_uri"]


def test_live_chat_collect_stops_when_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    enqueued = []
    monkeypatch.setattr(pipeline, "_enqueue_job", lambda queue_env, payload, delay_seconds=0: enqueued.append(payload) or "queued")
    repo = MemoryRepository()

    result = chat_collect(
        repo,
        {
            "video_id": "live002",
            "mode": "live",
            "live_chat_id": "chat002",
            "live_chat_response": {
                "nextPageToken": "ignored-token",
                "pollingIntervalMillis": 10000,
                "offlineAt": "2026-05-29T01:00:00Z",
                "items": [],
            },
        },
    )

    assert result["next_poll"]["action"] == "stop"
    assert result["next_poll"]["stop_reason"] == "offline"
    assert result["next_poll"]["requeue_delay_seconds"] is None
    assert enqueued == []


def test_live_chat_collect_does_not_requeue_on_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    enqueued = []
    monkeypatch.setattr(pipeline, "_enqueue_job", lambda queue_env, payload, delay_seconds=0: enqueued.append(payload) or "queued")
    repo = MemoryRepository()

    result = chat_collect(
        repo,
        {
            "video_id": "live003",
            "mode": "live",
            "live_chat_id": "chat003",
            "live_chat_response": {
                "nextPageToken": "retry-token",
                "pollingIntervalMillis": 10000,
                "error": {"errors": [{"reason": "rateLimitExceeded"}]},
                "items": [],
            },
        },
    )

    assert result["next_poll"]["action"] == "retry_later"
    assert result["next_poll"]["rate_limited"] is True
    assert result["next_poll"]["stop_reason"] == "rate_limit_exceeded"
    assert enqueued == []


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


class FakeDynamoTable:
    def __init__(self):
        self.items = {}
        self.query_calls = []

    def put_item(self, **kwargs):
        item = kwargs["Item"]
        key = (item["pk"], item["sk"])
        if kwargs.get("ConditionExpression") == "attribute_not_exists(pk)" and key in self.items:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.items[key] = dict(item)
        return {}

    def get_item(self, Key):
        item = self.items.get((Key["pk"], Key["sk"]))
        return {"Item": dict(item)} if item else {}

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        index_name = kwargs.get("IndexName")
        if index_name == "by_public_date":
            items = [item for item in self.items.values() if item.get("gsi1pk") == "VIDEO#PUBLIC"]
            items.sort(key=lambda item: item.get("gsi1sk", ""), reverse=not kwargs.get("ScanIndexForward", True))
        elif index_name == "by_work_queue":
            items = [item for item in self.items.values() if item.get("gsi3pk") in {"JOB#ALL", "QUOTA#ALL"}]
            items.sort(key=lambda item: item.get("gsi3sk", ""), reverse=not kwargs.get("ScanIndexForward", True))
        else:
            items = [item for item in self.items.values() if item["pk"].startswith("JOB#")]
        return {"Items": [dict(item) for item in items[: kwargs.get("Limit", 100)]]}


def dynamo_repo_with_fake_table() -> tuple[DynamoRepository, FakeDynamoTable]:
    table = FakeDynamoTable()
    repo = DynamoRepository.__new__(DynamoRepository)
    repo.table_name = "fake"
    repo.table = table
    repo.idempotency_index = {}
    return repo, table


def test_dynamo_repository_lists_use_query_indexes():
    repo, table = dynamo_repo_with_fake_table()
    repo.put_video({"video_id": "v1", "title": "one", "published_at": "2026-05-29T00:00:00Z", "public": True})
    repo.put_video({"video_id": "v2", "title": "private", "published_at": "2026-05-30T00:00:00Z", "public": False})
    repo.record_quota_usage("videos.list", 1, {"video_count": 1})
    job, _ = repo.create_job("metadata_sync", {"channel_id": "ch"}, "same-key")
    repo.append_job_event(job["job_id"], "completed", {})

    assert [video["video_id"] for video in repo.list_videos()] == ["v1"]
    assert repo.list_jobs()[0]["derived_state"] == "succeeded"
    assert repo.list_quota_usage()[0]["method"] == "videos.list"
    assert {call.get("IndexName") for call in table.query_calls} >= {"by_public_date", "by_work_queue"}


def test_dynamo_create_job_condition_prevents_duplicate_events():
    repo, table = dynamo_repo_with_fake_table()
    first, dedup_first = repo.create_job("metadata_sync", {"channel_id": "ch"}, "same-key")
    second, dedup_second = repo.create_job("metadata_sync", {"channel_id": "ch"}, "same-key")

    events = [item for item in table.items.values() if item.get("item_type") == "JobEvent"]
    assert dedup_first is False
    assert dedup_second is True
    assert second["job_id"] == first["job_id"]
    assert len(events) == 1
    assert repo.get_job(first["job_id"])["derived_state"] == "queued"
