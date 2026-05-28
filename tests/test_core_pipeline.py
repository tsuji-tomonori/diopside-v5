from diopside_core import MemoryRepository, normalize_replay_actions, normalize_video_resource, parse_iso8601_duration
from static_exporter.pipeline import chat_collect, chat_normalize, metadata_sync, rebuild_artifacts


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


def test_replay_parser_normalizes_known_and_unknown_renderer():
    messages = normalize_replay_actions(
        [
            {
                "replayChatItemAction": {
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
                                        "videoOffsetTimeMsec": "83000",
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
    assert messages[0]["message_runs"][1]["type"] == "emoji"
    assert messages[1]["parse_warning"] == "unknown_renderer"


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
    assert artifacts["wordcloud_available"] is True
    assert repo.get_chat_aggregate("vid001")["top_terms"][0]["term"] == "ありがとう"
    assert list((tmp_path / "raw/youtube").rglob("*.json"))
    assert list((tmp_path / "processed/chat-normalized").rglob("*.jsonl"))
    assert list((tmp_path / "processed/chat-aggregate").rglob("summary.json"))


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
