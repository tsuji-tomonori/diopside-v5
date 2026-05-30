import io
import json
import socket
import urllib.error
from pathlib import Path

import pytest

from botocore.exceptions import ClientError

from diopside_core import CHAT_MESSAGE_REQUIRED_KEYS, CHAT_MESSAGE_SCHEMA_VERSION, DynamoRepository, MemoryRepository, YouTubeClient, YouTubeClientError, build_timestamp_candidates, extract_initial_data_from_watch_html, extract_replay_continuations_from_initial_data, normalize_live_chat_items, normalize_replay_actions, normalize_video_resource, parse_iso8601_duration, summarize_chat_messages
import static_exporter.pipeline as pipeline
from static_exporter.pipeline import archive_finalize, cancel_job, chat_collect, chat_normalize, cleanup, dispatch_job, file_output, metadata_sync, notification_plan, quota_rollup, rebuild_artifacts, retry_job


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


@pytest.mark.parametrize(
    ("status_code", "reason", "retryable"),
    [
        (403, "quotaExceeded", True),
        (403, "insufficientPermissions", False),
        (404, "videoNotFound", False),
    ],
)
def test_youtube_client_normalizes_http_errors(monkeypatch, status_code, reason, retryable):
    body = json.dumps({"error": {"message": f"{reason} message", "errors": [{"reason": reason}]}}).encode("utf-8")

    def fake_urlopen(url, timeout):
        raise urllib.error.HTTPError(url, status_code, "error", hdrs={}, fp=io.BytesIO(body))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = YouTubeClient(api_key="test-key", base_url="https://example.test/youtube/v3")

    with pytest.raises(YouTubeClientError) as exc_info:
        client.videos(["abc123"])

    assert str(exc_info.value) == f"{reason} message"
    assert exc_info.value.status_code == status_code
    assert exc_info.value.reason == reason
    assert exc_info.value.retryable is retryable


def test_youtube_client_normalizes_network_timeout(monkeypatch):
    def fake_urlopen(url, timeout):
        raise socket.timeout("timed out")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = YouTubeClient(api_key="test-key", base_url="https://example.test/youtube/v3")

    with pytest.raises(YouTubeClientError) as exc_info:
        client.playlist_items("uploads")

    assert exc_info.value.status_code is None
    assert exc_info.value.reason == "network_error"
    assert exc_info.value.retryable is True


@pytest.mark.parametrize("body", [b"{", b"[]"])
def test_youtube_client_rejects_malformed_response(monkeypatch, body):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self):
            return body

    monkeypatch.setattr("urllib.request.urlopen", lambda url, timeout: Response())
    client = YouTubeClient(api_key="test-key", base_url="https://example.test/youtube/v3")

    with pytest.raises(YouTubeClientError) as exc_info:
        client.live_chat_messages("chat-id")

    assert exc_info.value.status_code is None
    assert exc_info.value.reason == "malformed_response"
    assert exc_info.value.retryable is False


class FakeYouTubeMetadataClient:
    def __init__(self):
        self.channel_calls = []
        self.playlist_calls = []
        self.video_calls = []

    def channels(self, channel_ids):
        self.channel_calls.append(list(channel_ids))
        return {
            "items": [
                {
                    "id": channel_id,
                    "snippet": {"title": "白雪巴", "description": "channel description", "publishedAt": "2019-11-01T00:00:00Z"},
                    "contentDetails": {"relatedPlaylists": {"uploads": "uploads"}},
                }
                for channel_id in channel_ids
            ]
        }

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
            "job_id": "job-meta",
        },
    )

    cursor = repo.get_channel_sync_cursor("ch")
    channel = repo.get_channel("ch")
    video = repo.get_video("vid001")
    assert result["next_page_token"] == "next-token"
    assert result["raw_channel_uri"]
    assert result["raw_playlist_uri"]
    assert result["raw_videos_uri"]
    assert channel["channel_title"] == "白雪巴"
    assert channel["display_name"] == "白雪巴"
    assert channel["uploads_playlist_id"] == "uploads"
    assert channel["raw_metadata_uri"] == result["raw_channel_uri"]
    assert cursor["item_type"] == "ChannelSyncCursor"
    assert cursor["pk"] == "CH#ch"
    assert cursor["sk"] == "CURSOR#uploads"
    assert cursor["uploads_playlist_id"] == "uploads"
    assert cursor["next_page_token"] == "next-token"
    assert cursor["next_page_token_hash"].startswith("page_")
    assert cursor["last_seen_video_id"] == "vid001"
    assert cursor["last_video_ids"] == ["vid001", "vid002"]
    assert "items" not in cursor
    assert video["raw_metadata_uri"] == result["raw_videos_uri"]
    assert "items" not in video
    assert client.channel_calls == [["ch"]]
    assert client.playlist_calls[0]["page_token"] is None
    usage = repo.list_quota_usage()
    assert {item["method"] for item in usage} == {"channels.list", "playlistItems.list", "videos.list"}
    assert all(item["channel_id"] == "ch" for item in usage)
    assert {item["video_count"] for item in usage} == {0, 2}
    assert all(item["job_id"] == "job-meta" for item in usage)
    assert enqueued[0]["queue_env"] == "DIOPSIDE_METADATA_QUEUE_URL"
    assert enqueued[0]["payload"]["requested_by"] == "worker"
    assert enqueued[0]["payload"]["payload"]["page_token"] == "next-token"
    assert list((tmp_path / "raw/youtube/metadata/channel_id=ch/channels").glob("*.json"))
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


def test_live_status_scan_records_quota_and_refreshes_state(monkeypatch):
    enqueued = []
    monkeypatch.setattr(pipeline, "_enqueue_job", lambda queue_env, payload, delay_seconds=0: enqueued.append({"queue_env": queue_env, "payload": payload}) or "queued")
    repo = MemoryRepository()
    repo.put_video(
        {
            "video_id": "vid-live",
            "title": "live",
            "published_at": "2026-05-29T00:00:00Z",
            "channel_id": "ch",
            "live_state": "upcoming",
        }
    )
    client = FakeYouTubeMetadataClient()

    result = pipeline.live_status_scan(repo, {"youtube_client": client, "job_id": "job-live"})

    usage = repo.list_quota_usage()[0]
    assert usage["method"] == "videos.list"
    assert usage["units"] == 1
    assert usage["video_count"] == 1
    assert usage["channel_id"] == "ch"
    assert usage["job_id"] == "job-live"
    assert client.video_calls == [["vid-live"]]
    assert repo.get_video("vid-live")["live_state"] == "archived"
    events = [item for item in repo.items.values() if item.get("item_type") == "VideoStateEvent"]
    assert len(events) == 1
    assert events[0]["pk"] == "VID#vid-live"
    assert events[0]["event_name"] == "video.archived"
    assert events[0]["from_state"] == "upcoming"
    assert events[0]["to_state"] == "archived"
    assert events[0]["source_job_id"] == "job-live"
    assert result["updated"] == [{"video_id": "vid-live", "from": "upcoming", "to": "archived"}]
    assert result["enqueue_archive_finalize"] == ["vid-live"]
    assert enqueued[0]["queue_env"] == "DIOPSIDE_AGGREGATE_QUEUE_URL"
    assert enqueued[0]["payload"]["job_type"] == "archive_finalize"
    assert enqueued[0]["payload"]["payload"]["video_id"] == "vid-live"


def test_live_status_scan_enqueues_notification_plan_for_upcoming_video(monkeypatch):
    enqueued = []
    monkeypatch.setattr(pipeline, "_enqueue_job", lambda queue_env, payload, delay_seconds=0: enqueued.append({"queue_env": queue_env, "payload": payload}) or "queued")
    repo = MemoryRepository()
    repo.put_video(
        {
            "video_id": "vid-upcoming",
            "title": "upcoming",
            "published_at": "2026-05-29T00:00:00Z",
            "channel_id": "ch",
            "scheduled_start_time": "2026-05-30T12:00:00Z",
            "live_state": "upcoming",
        }
    )

    result = pipeline.live_status_scan(repo, {"skip_youtube_refresh": True, "job_id": "job-live"})

    assert result["enqueue_notification_plan"] == ["vid-upcoming"]
    assert enqueued == [
        {
            "queue_env": "DIOPSIDE_AGGREGATE_QUEUE_URL",
            "payload": {
                "job_type": "notification_plan",
                "job_id": "manual-notification-plan-vid-upcoming",
                "idempotency_key": "notification_plan:manual-notification-plan-vid-upcoming",
                "requested_by": "worker",
                "attempt": 0,
                "trace_id": enqueued[0]["payload"]["trace_id"],
                "payload": {
                    "video_id": "vid-upcoming",
                    "scheduled_start_time": "2026-05-30T12:00:00Z",
                    "requested_by": "live_status_scan",
                },
            },
        }
    ]


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


def test_replay_parser_golden_fixtures_cover_renderer_variants():
    fixture_dir = Path("data/fixtures/replay-parser")
    fixture = json.loads((fixture_dir / "golden-actions.json").read_text(encoding="utf-8"))
    expected = json.loads((fixture_dir / "golden-expected.json").read_text(encoding="utf-8"))

    messages = normalize_replay_actions(fixture["actions"], fixture["video_id"])

    assert [_replay_projection(message) for message in messages] == expected["messages"]
    for message in messages:
        assert set(CHAT_MESSAGE_REQUIRED_KEYS) <= set(message)
        assert message["source"] == "replay"
        assert message["offset_msec"] == message["video_offset_time_msec"]


def _replay_projection(message):
    emoji_run = next((run for run in message["message_runs"] if run["type"] == "emoji"), None)
    return {
        "message_id": None if message["message_type"] == "unknown" else message["message_id"],
        "message_type": message["message_type"],
        "raw_renderer_type": message["raw_renderer_type"],
        "offset_msec": message["offset_msec"],
        "message_text": message["message_text"],
        "run_types": [run["type"] for run in message["message_runs"]],
        "emoji_id": emoji_run.get("emoji_id") if emoji_run else None,
        "emoji_label": emoji_run.get("label") if emoji_run else None,
        "is_custom_emoji": emoji_run.get("is_custom_emoji") if emoji_run else None,
        "paid_amount_text": message["paid"]["amount_text"],
        "sticker_emoji_id": message["sticker"]["emoji_id"] if message["sticker"] else None,
        "sticker_alt_text": message["sticker"]["alt_text"] if message["sticker"] else None,
        "parse_warning": message["parse_warning"],
        "raw_renderer_id": message["raw_renderer"].get("id") if message["raw_renderer"] else None,
    }


def test_normalized_chat_message_schema_contract_for_live_and_replay_variants():
    live_messages = normalize_live_chat_items(
        [
            {
                "id": "live-text",
                "snippet": {"type": "textMessageEvent", "displayMessage": "hello", "publishedAt": "2026-05-29T00:00:00Z", "elapsedTimeMsec": "12000"},
                "authorDetails": {"channelId": "live-author", "displayName": "Live Alice", "isChatSponsor": True},
            },
            {
                "id": "live-paid",
                "snippet": {"type": "superChatEvent", "displayMessage": "paid hello", "publishedAt": "2026-05-29T00:00:01Z", "elapsedTimeMsec": "13000"},
                "authorDetails": {"channelId": "paid-author", "displayName": "Paid Bob"},
            },
        ],
        "vid-schema",
    )
    replay_messages = normalize_replay_actions(
        [
            {
                "addChatItemAction": {
                    "item": {
                        "liveChatTextMessageRenderer": {
                            "id": "replay-text",
                            "authorExternalChannelId": "replay-author",
                            "authorName": {"simpleText": "Replay Carol"},
                            "timestampUsec": "1000",
                            "videoOffsetTimeMsec": "14000",
                            "message": {"runs": [{"text": "emoji "}, {"emoji": {"emojiId": "e1", "shortcuts": [":tomoe:"], "isCustomEmoji": True}}]},
                        }
                    }
                }
            },
            {
                "addChatItemAction": {
                    "item": {
                        "liveChatPaidMessageRenderer": {
                            "id": "replay-paid",
                            "authorExternalChannelId": "paid-replay-author",
                            "timestampUsec": "2000",
                            "videoOffsetTimeMsec": "15000",
                            "purchaseAmountText": {"simpleText": "￥500"},
                            "message": {"runs": [{"text": "super chat"}]},
                        }
                    }
                }
            },
            {
                "addChatItemAction": {
                    "item": {
                        "liveChatPaidStickerRenderer": {
                            "id": "replay-sticker",
                            "authorExternalChannelId": "sticker-author",
                            "timestampUsec": "3000",
                            "videoOffsetTimeMsec": "16000",
                            "purchaseAmountText": {"simpleText": "￥200"},
                            "sticker": {"emojiId": "stk1", "image": {"accessibility": {"accessibilityData": {"label": "sticker label"}}, "thumbnails": [{"url": "https://example.invalid/sticker.png"}]}},
                        }
                    }
                }
            },
            {"liveChatMembershipItemRenderer": {"id": "unknown-membership"}},
        ],
        "vid-schema",
    )
    messages = [*live_messages, *replay_messages]

    assert {message["message_type"] for message in messages} == {"text", "paid", "sticker", "unknown"}
    for message in messages:
        assert set(CHAT_MESSAGE_REQUIRED_KEYS) <= set(message)
        assert message["schema_version"] == CHAT_MESSAGE_SCHEMA_VERSION
        assert message["plain_text"] == message["message_text"]
        assert message["offset_msec"] == message["video_offset_time_msec"]
        assert set(message["author"]) == {"display_name", "channel_id_hash", "badges"}
        assert set(message["paid"]) == {"is_paid", "amount_text", "currency"}
    assert live_messages[0]["author"]["channel_id_hash"].startswith("sha256:")
    assert live_messages[1]["message_type"] == "paid"
    assert replay_messages[0]["message_runs"][1]["type"] == "emoji"
    assert replay_messages[0]["message_runs"][1]["emoji_id"] == "e1"
    assert replay_messages[1]["paid"]["amount_text"] == "￥500"
    assert replay_messages[2]["message_type"] == "sticker"
    assert replay_messages[2]["sticker"]["emoji_id"] == "stk1"
    assert replay_messages[3]["parse_warning"] == "unknown_renderer"
    assert replay_messages[3]["raw_renderer"]["id"] == "unknown-membership"


def test_public_replay_initial_data_extractor():
    html = 'x; ytInitialData = {"actions":[{"addChatItemAction":{"item":{"liveChatTextMessageRenderer":{"id":"m1","message":{"runs":[{"text":"hello"}]}}}}}]}; y'
    data = extract_initial_data_from_watch_html(html)
    collected = chat_collect(MemoryRepository(), {"video_id": "vid001", "mode": "replay", "replay_initial_data": data})
    assert collected["source"] == "replay"
    assert collected["message_count"] == 1
    assert collected["parser_stats"]["action_count"] == 1


def test_public_replay_initial_data_keeps_unknown_renderer_and_continuation(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    enqueued = []
    monkeypatch.setattr(pipeline, "_enqueue_job", lambda queue_env, payload, delay_seconds=0: enqueued.append({"queue_env": queue_env, "payload": payload, "delay_seconds": delay_seconds}) or "queued")
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
    assert enqueued == [
        {
            "queue_env": "DIOPSIDE_CHAT_QUEUE_URL",
            "delay_seconds": 1,
            "payload": {
                "job_id": enqueued[0]["payload"]["job_id"],
                "job_type": "chat_collect",
                "idempotency_key": "chat_collect:manual-replay-vid-replay-replay-token-1",
                "requested_by": "worker",
                "attempt": 0,
                "trace_id": enqueued[0]["payload"]["trace_id"],
                "payload": {
                    "video_id": "vid-replay",
                    "mode": "replay",
                    "replay_continuation": {"token": "replay-token-1", "source": "reloadContinuationData", "timeout_ms": 1500},
                },
            },
        }
    ]
    assert chunk["item_type"] == "ChatPageManifest"
    assert chunk["pk"] == "VID#vid-replay"
    assert chunk["sk"] == "CHAT#PAGE#replay#1"
    assert chunk["raw_s3_uri"] == chunk["s3_uri"]
    assert chunk["item_count"] == 2
    assert chunk["checksum"] == chunk["sha256"]
    assert chunk["job_id"] == "chat_collect#vid-replay"
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
    assert enqueued[0]["payload"]["payload"]["page_token"] == "next-live-token"
    assert chunks[0]["next_poll"]["action"] == "requeue"
    assert chunks[0]["item_type"] == "ChatPageManifest"
    assert chunks[0]["pk"] == "VID#live001"
    assert chunks[0]["sk"] == "CHAT#PAGE#live#1"
    assert chunks[0]["raw_s3_uri"] == chunks[0]["s3_uri"]
    assert chunks[0]["item_count"] == 1
    assert chunks[0]["checksum"] == chunks[0]["sha256"]
    assert chunks[0]["message_count"] == 1
    assert chunks[0]["s3_uri"]


def test_live_chat_collect_records_quota_when_calling_youtube(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr(pipeline, "_enqueue_job", lambda queue_env, payload, delay_seconds=0: None)

    class FakeLiveChatClient:
        def __init__(self):
            self.calls = []

        def live_chat_messages(self, live_chat_id, page_token=None):
            self.calls.append({"live_chat_id": live_chat_id, "page_token": page_token})
            return {"items": [], "offlineAt": "2026-05-29T00:00:00Z"}

    repo = MemoryRepository()
    repo.put_video({"video_id": "live-quota", "title": "live", "published_at": "2026-05-29T00:00:00Z", "channel_id": "ch", "live_chat_id": "chat-quota"})
    client = FakeLiveChatClient()

    chat_collect(repo, {"video_id": "live-quota", "mode": "live", "youtube_client": client, "page_token": "page-1", "job_id": "job-chat"})

    usage = repo.list_quota_usage()[0]
    assert client.calls == [{"live_chat_id": "chat-quota", "page_token": "page-1"}]
    assert usage["method"] == "liveChatMessages.list"
    assert usage["units"] == 1
    assert usage["video_count"] == 1
    assert usage["channel_id"] == "ch"
    assert usage["job_id"] == "job-chat"


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


def test_file_output_writes_public_artifact_and_records_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    repo = MemoryRepository()

    result = file_output(
        repo,
        {
            "video_id": "vid001",
            "artifact_type": "wordcloud-json",
            "artifact_version": "20260530T121700Z",
            "key": "data/artifacts/wordcloud/vid001.json",
            "content_type": "application/json",
            "visibility": "public",
            "json_body": {"schema_version": "public-wordcloud/v1", "video_id": "vid001", "terms": []},
            "job_id": "job-file-output",
        },
    )

    artifact = repo.get_artifact_by_id("vid001:wordcloud-json")
    assert result["artifact_id"] == "vid001:wordcloud-json"
    assert result["public_url_path"] == "/data/artifacts/wordcloud/vid001.json"
    assert result["content_hash"].startswith("sha256:")
    assert artifact["artifact_version"] == "20260530T121700Z"
    assert artifact["content_hash"] == result["content_hash"]
    assert artifact["byte_size"] > 0
    assert artifact["source_job_id"] == "job-file-output"
    assert artifact["public_url_path"] == "/data/artifacts/wordcloud/vid001.json"
    assert (tmp_path / "data/artifacts/wordcloud/vid001.json").exists()


def test_dispatch_file_output_writes_private_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    repo = MemoryRepository()
    job, _ = repo.create_job("file_output", {"video_id": "vid001"}, "file-output-job")

    result = dispatch_job(
        repo,
        {
            "job_type": "file_output",
            "job_id": job["job_id"],
            "input": {
                "video_id": "vid001",
                "artifact_type": "chat-summary",
                "key": "processed/custom/vid001-summary.json",
                "content_type": "application/json",
                "visibility": "private",
                "body": "{}",
            },
        },
    )

    artifact = repo.get_artifact_by_id("vid001:chat-summary")
    assert result["status"] == "succeeded"
    assert artifact["artifact_version"] == "v1"
    assert artifact["s3_uri"] == str(tmp_path / "processed/custom/vid001-summary.json")
    assert "public_url_path" not in artifact
    assert repo.get_job(job["job_id"])["derived_state"] == "succeeded"


def test_file_output_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    repo = MemoryRepository()

    with pytest.raises(ValueError, match="relative path"):
        file_output(
            repo,
            {
                "video_id": "vid001",
                "artifact_type": "bad",
                "key": "../bad.json",
                "json_body": {},
            },
        )


def test_worker_pipeline_integration_uses_local_fakes(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    enqueued = []
    monkeypatch.setattr(
        pipeline,
        "_enqueue_job",
        lambda queue_env, payload, delay_seconds=0: enqueued.append(
            {"queue_env": queue_env, "payload": payload, "delay_seconds": delay_seconds}
        )
        or f"queued-{len(enqueued)}",
    )
    repo = MemoryRepository()
    metadata_job, _ = repo.create_job("metadata_sync", {"video_resources": ["vid-int"]}, "int-metadata")

    metadata = dispatch_job(
        repo,
        {
            "job_type": "metadata_sync",
            "job_id": metadata_job["job_id"],
            "input": {
                "video_resources": [
                    {
                        "id": "vid-int",
                        "snippet": {
                            "title": "統合テストアーカイブ",
                            "description": "00:45 見どころ",
                            "publishedAt": "2026-05-28T00:00:00Z",
                            "channelId": "ch",
                            "tags": ["統合"],
                        },
                        "contentDetails": {"duration": "PT10M"},
                        "liveStreamingDetails": {},
                        "statistics": {},
                        "status": {"privacyStatus": "public"},
                    }
                ]
            },
        },
    )

    assert metadata["status"] == "succeeded"
    assert repo.get_video("vid-int")["raw_metadata_uri"]
    assert repo.get_job(metadata_job["job_id"])["derived_state"] == "succeeded"
    assert list((tmp_path / "raw/youtube/metadata/video_id=vid-int").rglob("*.json"))

    repo.put_video(
        {
            "video_id": "live-int",
            "title": "配信中",
            "published_at": "2026-05-29T00:00:00Z",
            "live_chat_id": "chat-int",
            "public": True,
        }
    )
    scan_job, _ = repo.create_job("live_status_scan", {"skip_youtube_refresh": True}, "int-live-scan")
    scan = dispatch_job(
        repo,
        {
            "job_type": "live_status_scan",
            "job_id": scan_job["job_id"],
            "input": {"skip_youtube_refresh": True},
        },
    )

    assert scan["status"] == "succeeded"
    assert enqueued == [
        {
            "queue_env": "DIOPSIDE_CHAT_QUEUE_URL",
            "payload": {
                "job_type": "chat_collect",
                "job_id": "manual-live-live-int",
                "idempotency_key": "chat_collect:manual-live-live-int",
                "requested_by": "worker",
                "attempt": 0,
                "trace_id": enqueued[0]["payload"]["trace_id"],
                "payload": {"video_id": "live-int", "mode": "live", "live_chat_id": "chat-int"},
            },
            "delay_seconds": 0,
        }
    ]

    collect_job, _ = repo.create_job("chat_collect", {"video_id": "vid-int", "mode": "replay"}, "int-chat-collect")
    collect = dispatch_job(
        repo,
        {
            "job_type": "chat_collect",
            "job_id": collect_job["job_id"],
            "input": {
                "video_id": "vid-int",
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
                                    "videoOffsetTimeMsec": "45000",
                                    "message": {"runs": [{"text": "統合テスト ありがとう"}]},
                                }
                            }
                        }
                    }
                ],
            },
        },
    )
    normalize_job, _ = repo.create_job("chat_normalize", {"video_id": "vid-int"}, "int-chat-normalize")
    normalized = dispatch_job(
        repo,
        {"job_type": "chat_normalize", "job_id": normalize_job["job_id"], "input": {"video_id": "vid-int"}},
    )
    rebuild_job, _ = repo.create_job("rebuild_artifacts", {"video_id": "vid-int"}, "int-rebuild")
    rebuilt = dispatch_job(
        repo,
        {"job_type": "rebuild_artifacts", "job_id": rebuild_job["job_id"], "input": {"video_id": "vid-int"}},
    )

    assert collect["message_count"] == 1
    assert normalized["message_count"] == 1
    assert rebuilt["timestamp_count"] >= 1
    assert rebuilt["wordcloud_available"] is True
    assert {item["term"] for item in repo.get_chat_aggregate("vid-int")["top_terms"]} >= {"統合テスト", "ありがとう"}
    assert repo.get_job(collect_job["job_id"])["derived_state"] == "succeeded"
    assert repo.get_job(normalize_job["job_id"])["derived_state"] == "succeeded"
    assert repo.get_job(rebuild_job["job_id"])["derived_state"] == "succeeded"
    assert repo.list_artifacts("vid-int")
    assert list((tmp_path / "raw/youtube/chat/video_id=vid-int").rglob("*.jsonl"))
    assert list((tmp_path / "processed/chat-normalized/video_id=vid-int").rglob("*.jsonl"))
    assert list((tmp_path / "processed/chat-aggregate/video_id=vid-int").rglob("summary.json"))


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
    manifest = repo.get_chat_manifest("vid001")
    assert manifest["pk"] == "VID#vid001"
    assert manifest["normalized_s3_uri"].endswith("processed/chat-normalized/video_id=vid001/part-000.jsonl")
    assert manifest["message_count"] == 1


def test_summarize_chat_messages_accepts_single_pass_iterable():
    consumed = False

    def messages():
        nonlocal consumed
        assert consumed is False
        consumed = True
        yield {"message_type": "text", "author_external_channel_id": "a1", "message_runs": [{"type": "emoji"}], "message_text": "ありがとう", "video_offset_time_msec": 60000}
        yield {"message_type": "paid", "author_external_channel_id": "a2", "message_runs": [], "message_text": "ありがとう", "video_offset_time_msec": 61000}

    summary = summarize_chat_messages(messages())

    assert summary["message_count"] == 2
    assert summary["unique_author_count"] == 2
    assert summary["paid_message_count"] == 1
    assert summary["emoji_count"] == 1
    assert summary["top_terms"][0] == {"term": "ありがとう", "score": 2}


def test_chat_normalize_streams_jsonl_chunks_without_read_jsonl_list(tmp_path, monkeypatch):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr(pipeline, "_read_jsonl", lambda uri: (_ for _ in ()).throw(AssertionError("_read_jsonl should not be used by chat_normalize")))
    repo = MemoryRepository()
    for index, text in enumerate(["ありがとう ありがとう", "おはよう"]):
        raw_path = tmp_path / f"raw/youtube/chat/video_id=vid-stream/source=replay/part-{index:03d}.jsonl"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "message_id": f"m{index}",
                "video_id": "vid-stream",
                "source": "replay",
                "message_type": "paid" if index == 1 else "text",
                "author_external_channel_id": f"a{index}",
                "author_name": None,
                "message_runs": [{"type": "text", "text": text}],
                "message_text": text,
                "video_offset_time_msec": 60000 + index * 1000,
            }
        ]
        if index == 1:
            rows.append({**rows[0], "message_id": "m0", "message_text": "ありがとう ありがとう", "video_offset_time_msec": 60000})
        raw_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
        repo.put_item(
            {
                "item_type": "ChatMessageChunkManifest",
                "pk": "VIDEO#vid-stream",
                "sk": f"CHAT#RAW#replay#{index}",
                "video_id": "vid-stream",
                "source": "replay",
                "s3_uri": str(raw_path),
                "message_count": 1,
                "sha256": "fixture",
                "first_offset_msec": 60000 + index * 1000,
                "last_offset_msec": 60000 + index * 1000,
                "next_poll": None,
            }
        )

    normalized = chat_normalize(repo, {"video_id": "vid-stream"})

    normalized_path = tmp_path / "processed/chat-normalized/video_id=vid-stream/part-000.jsonl"
    aggregate_path = tmp_path / "processed/chat-aggregate/video_id=vid-stream/summary.json"
    normalized_rows = [json.loads(line) for line in normalized_path.read_text(encoding="utf-8").splitlines()]
    summary = json.loads(aggregate_path.read_text(encoding="utf-8"))
    assert normalized["message_count"] == 2
    assert normalized["top_term_count"] == 2
    assert len(normalized_rows) == 2
    assert [row["message_id"] for row in normalized_rows] == ["m0", "m1"]
    assert summary["message_count"] == 2
    assert summary["paid_message_count"] == 1
    assert repo.get_chat_aggregate("vid-stream")["top_terms"][0]["term"] == "ありがとう"


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
    assert any("keyword_spike" in candidate["merged_sources"] and "ありがとう" in candidate["evidence_terms"] for candidate in candidates)


def test_timestamp_candidates_merge_sources_and_sort_by_score():
    summary = {
        "message_count": 20,
        "timeline_buckets": [
            {"offset_sec": 120, "message_count": 8},
            {"offset_sec": 300, "message_count": 12},
        ],
        "top_terms": [{"term": "ありがとう", "score": 12}, {"term": "かわいい", "score": 4}],
        "term_timeline": {
            "ありがとう": [{"offset_sec": 125, "count": 10}, {"offset_sec": 360, "count": 2}],
            "かわいい": [{"offset_sec": 300, "count": 4}],
        },
    }

    candidates = build_timestamp_candidates(summary, "02:05 見どころ\n05:00 別場面")

    assert candidates == sorted(candidates, key=lambda item: (-item["score"], item["offset_sec"], item["source"]))
    merged = next(candidate for candidate in candidates if candidate["offset_sec"] == 125)
    assert merged["source"] == "description"
    assert merged["label"] == "見どころ"
    assert merged["score"] == 1.0
    assert merged["merged_sources"] == ["chat_burst", "description", "keyword_spike"]
    assert merged["evidence_terms"] == ["ありがとう", "かわいい"]
    assert merged["message_count"] == 10
    assert [candidate["offset_sec"] for candidate in candidates].count(125) == 1
    assert any(candidate["source"] == "description" and candidate["offset_sec"] == 300 for candidate in candidates)


def test_repository_job_idempotency_and_lists():
    repo = MemoryRepository()
    repo.put_item({"item_type": "Channel", "pk": "CHANNEL#ch", "sk": "META", "channel_id": "ch", "uploads_playlist_id": "uploads"})
    repo.record_quota_usage("videos.list", 1, {}, channel_id="ch", video_count=1, job_id="job-quota")
    first, dedup_first = repo.create_job("metadata_sync", {"channel_id": "ch"}, "same-key")
    second, dedup_second = repo.create_job("metadata_sync", {"channel_id": "ch"}, "same-key")
    repo.append_job_event(first["job_id"], "completed", {"saved_count": 0})

    assert dedup_first is False
    assert dedup_second is True
    assert second["job_id"] == first["job_id"]
    assert repo.get_job(first["job_id"])["derived_state"] == "succeeded"
    assert repo.list_channels()[0]["channel_id"] == "ch"
    quota = repo.list_quota_usage()[0]
    assert quota["method"] == "videos.list"
    assert quota["channel_id"] == "ch"
    assert quota["video_count"] == 1
    assert quota["job_id"] == "job-quota"


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


def test_failed_job_emits_json_error_log(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DIOPSIDE_LOCAL_ARTIFACT_DIR", str(tmp_path))
    repo = MemoryRepository()
    with pytest.raises(ValueError):
        dispatch_job(repo, {"job_type": "unknown", "job_id": "failed-log", "trace_id": "trace-worker-error"})

    log = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert log["component"] == "worker"
    assert log["event"] == "worker_job"
    assert log["trace_id"] == "trace-worker-error"
    assert log["job_id"] == "failed-log"
    assert log["job_type"] == "unknown"
    assert log["result"] == "failed"
    assert log["error"]["type"] == "ValueError"
    assert log["error"]["debug_uri"].endswith(".json")


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


def test_quota_rollup_summarizes_usage_and_stores_daily_method_items():
    repo = MemoryRepository()
    repo.record_quota_usage("videos.list", 1, {}, channel_id="ch", video_count=2, job_id="job-video")
    repo.record_quota_usage("playlistItems.list", 1, {}, channel_id="ch", video_count=2, job_id="job-playlist")
    repo.record_quota_usage("videos.list", 1, {}, channel_id="ch", video_count=1, job_id="job-live")

    result = quota_rollup(repo, {"requested_by": "scheduler"})
    quota_date = repo.list_quota_usage()[0]["pk"].removeprefix("QUOTA#").replace("-", "")
    videos_summary = repo.get_item(f"QUOTA#{quota_date}", "METHOD#videos.list")
    playlist_summary = repo.get_item(f"QUOTA#{quota_date}", "METHOD#playlistItems.list")

    assert result["requested_by"] == "scheduler"
    assert result["item_count"] == 3
    assert result["total_units"] == 3
    assert result["by_method"] == {"videos.list": 2, "playlistItems.list": 1}
    assert result["summary_count"] == 2
    assert videos_summary["record_type"] == "daily_method_summary"
    assert videos_summary["quota_date"] == quota_date
    assert videos_summary["call_count"] == 2
    assert videos_summary["units_used"] == 2
    assert videos_summary["unit_per_call"] == 1
    assert videos_summary["video_count"] == 3
    assert videos_summary["channel_ids"] == ["ch"]
    assert videos_summary["job_ids"] == ["job-live", "job-video"]
    assert playlist_summary["call_count"] == 1
    assert playlist_summary["units_used"] == 1
    assert len(repo.list_quota_usage()) == 3


def test_cleanup_returns_safe_dry_run_report_without_deleting():
    repo = MemoryRepository()
    repo.put_video({"video_id": "vid001", "title": "keep", "published_at": "2026-05-29T00:00:00Z"})

    result = cleanup(repo, {"requested_by": "scheduler", "dry_run": False, "policy_version": "test"})

    assert result == {"requested_by": "scheduler", "dry_run": True, "deleted_count": 0, "policy_version": "test"}
    assert repo.get_video("vid001")["title"] == "keep"


def test_archive_finalize_refreshes_metadata_and_enqueues_replay_and_export(monkeypatch):
    enqueued = []
    monkeypatch.setattr(
        pipeline,
        "_enqueue_job",
        lambda queue_env, payload, delay_seconds=0: enqueued.append({"queue_env": queue_env, "payload": payload, "delay_seconds": delay_seconds}) or "queued",
    )
    repo = MemoryRepository()
    repo.put_video({"video_id": "vid-final", "title": "old", "published_at": "2026-05-29T00:00:00Z", "channel_id": "ch", "live_state": "live"})
    client = FakeYouTubeMetadataClient()

    result = archive_finalize(repo, {"video_id": "vid-final", "youtube_client": client, "job_id": "job-finalize"})

    video = repo.get_video("vid-final")
    quota = repo.list_quota_usage()[0]
    assert result["video_id"] == "vid-final"
    assert result["refreshed"] is True
    assert result["replay_enqueued"] is True
    assert result["static_export_enqueued"] is True
    assert video["title"] == "vid-final"
    assert video["live_state"] == "archived"
    assert video["archive_finalized_at"]
    events = [item for item in repo.items.values() if item.get("item_type") == "VideoStateEvent"]
    assert len(events) == 1
    assert events[0]["event_name"] == "video.archive_finalized"
    assert events[0]["from_state"] == "live"
    assert events[0]["to_state"] == "archived"
    assert events[0]["source_job_id"] == "job-finalize"
    assert events[0]["payload"]["refreshed"] is True
    assert repo.get_item("VID#vid-final", "NOTIFY#archive_available")["delivery_state"] == "planned"
    assert quota["method"] == "videos.list"
    assert quota["job_id"] == "job-finalize"
    assert [item["queue_env"] for item in enqueued] == ["DIOPSIDE_CHAT_QUEUE_URL", "DIOPSIDE_STATIC_EXPORT_QUEUE_URL"]
    assert enqueued[0]["payload"]["job_type"] == "chat_collect"
    assert enqueued[0]["payload"]["payload"]["mode"] == "replay"
    assert enqueued[1]["payload"]["job_type"] == "static_export"
    assert enqueued[1]["payload"]["payload"]["scope"] == "video"


def test_notification_plan_creates_due_items_idempotently():
    repo = MemoryRepository()
    repo.put_video(
        {
            "video_id": "vid-plan",
            "title": "upcoming",
            "published_at": "2026-05-29T00:00:00Z",
            "scheduled_start_time": "2026-05-30T12:00:00Z",
        }
    )

    first = notification_plan(repo, {"video_id": "vid-plan", "job_id": "job-notify"})
    second = notification_plan(repo, {"video_id": "vid-plan", "job_id": "job-notify-2"})

    before = repo.get_item("VID#vid-plan", "NOTIFY#before_30min")
    at_start = repo.get_item("VID#vid-plan", "NOTIFY#at_start")
    assert first["planned_count"] == 2
    assert second["planned_count"] == 2
    assert before["due_at"] == "2026-05-30T11:30:00Z"
    assert before["gsi3pk"] == "NOTIFY#DUE"
    assert before["gsi3sk"] == "DUE#2026-05-30T11:30:00Z#vid-plan#before_30min"
    assert before["delivery_state"] == "planned"
    assert before["message_template_id"] == "before_30min"
    assert before["created_at"]
    assert before["updated_at"]
    assert before["source_job_id"] == "job-notify-2"
    assert at_start["due_at"] == "2026-05-30T12:00:00Z"


def test_dispatch_job_supports_scheduled_maintenance_jobs():
    repo = MemoryRepository()
    repo.record_quota_usage("videos.list", 1, {}, channel_id="ch", video_count=1, job_id="job-quota")

    quota = dispatch_job(repo, {"job_type": "quota_rollup", "job_id": "scheduler-quota", "input": {"requested_by": "scheduler"}})
    cleanup_result = dispatch_job(repo, {"job_type": "cleanup", "job_id": "scheduler-cleanup", "input": {"requested_by": "scheduler"}})

    assert quota["status"] == "succeeded"
    assert quota["total_units"] == 1
    assert cleanup_result["status"] == "succeeded"
    assert cleanup_result["deleted_count"] == 0


def test_dispatch_job_accepts_v04_payload_job_message():
    repo = MemoryRepository()

    result = dispatch_job(
        repo,
        {
            "job_id": "scheduler-cleanup-v04",
            "job_type": "cleanup",
            "idempotency_key": "cleanup:scheduler",
            "requested_by": "scheduler",
            "attempt": 0,
            "trace_id": "trace-v04-message",
            "payload": {"requested_by": "scheduler", "retention_days": 30},
        },
    )

    assert result["status"] == "succeeded"
    assert result["deleted_count"] == 0
    events = [item for item in repo.items.values() if item.get("pk") == "JOB#scheduler-cleanup-v04"]
    assert [event["event_name"] for event in events] == ["job.started", "job.succeeded"]


def test_worker_emits_json_success_log(capsys):
    repo = MemoryRepository()

    result = dispatch_job(
        repo,
        {
            "job_type": "cleanup",
            "job_id": "scheduler-cleanup-log",
            "trace_id": "trace-worker-success",
            "input": {"requested_by": "scheduler", "video_id": "vid-log"},
        },
    )

    log = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert result["status"] == "succeeded"
    assert log["component"] == "worker"
    assert log["event"] == "worker_job"
    assert log["trace_id"] == "trace-worker-success"
    assert log["job_id"] == "scheduler-cleanup-log"
    assert log["job_type"] == "cleanup"
    assert log["video_id"] == "vid-log"
    assert log["result"] == "succeeded"
    assert isinstance(log["duration_ms"], float)


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

    def delete_item(self, Key):
        self.items.pop((Key["pk"], Key["sk"]), None)
        return {}

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        index_name = kwargs.get("IndexName")
        if index_name == "by_public_date":
            items = [item for item in self.items.values() if item.get("gsi1pk") == "VIDEO#PUBLIC"]
            items.sort(key=lambda item: item.get("gsi1sk", ""), reverse=not kwargs.get("ScanIndexForward", True))
        elif index_name == "by_work_queue":
            items = [
                item
                for item in self.items.values()
                if item.get("gsi3pk") in {"JOB#ALL", "QUOTA#ALL"} or str(item.get("gsi3pk", "")).startswith("JOB#STATE#")
            ]
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
    repo.record_quota_usage("videos.list", 1, {}, channel_id="ch", video_count=1, job_id="job-quota")
    job, _ = repo.create_job("metadata_sync", {"channel_id": "ch"}, "same-key")
    repo.append_job_event(job["job_id"], "completed", {})

    assert [video["video_id"] for video in repo.list_videos()] == ["v1"]
    assert repo.list_jobs()[0]["derived_state"] == "succeeded"
    quota = repo.list_quota_usage()[0]
    assert quota["method"] == "videos.list"
    assert quota["channel_id"] == "ch"
    assert quota["video_count"] == 1
    assert quota["job_id"] == "job-quota"
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
