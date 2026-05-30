from pathlib import Path

from diopside_core.repository import ITEM_TYPES, MemoryRepository, random_bucket_item, tag_id_for_label, video_item, video_state_event_item


V04_ITEM_TYPES = {
    "AppConfig",
    "Channel",
    "ChannelRef",
    "ChannelSyncCursor",
    "Video",
    "VideoMonthIndex",
    "VideoStateEvent",
    "VideoStatSnapshot",
    "VideoTagLink",
    "TagSummary",
    "ChatManifest",
    "ChatPageManifest",
    "ChatAggregate",
    "Artifact",
    "NotificationPlan",
    "StaticExport",
    "Job",
    "JobEvent",
    "Lock",
    "Idempotency",
    "QuotaUsage",
    "RandomBucket",
}


def test_dynamodb_schema_audit_covers_v04_item_types_and_current_allowlist():
    audit = Path("docs/design/dynamodb-schema-audit.md").read_text(encoding="utf-8")

    for item_type in sorted(V04_ITEM_TYPES):
        assert f"`{item_type}`" in audit
    for item_type in sorted(ITEM_TYPES):
        assert f"`{item_type}`" in audit

    assert "未対応" in audit
    assert "差分あり" in audit
    assert "部分実装" in audit


def test_video_item_current_schema_contract():
    item = video_item(
        {
            "video_id": "vid001",
            "channel_id": "ch001",
            "title": "archive",
            "published_at": "2026-05-30T00:00:00Z",
            "tags": ["歌枠", "歌枠", "雑談"],
            "public": True,
        }
    )

    assert item["item_type"] == "Video"
    assert item["pk"] == "VID#vid001"
    assert item["sk"] == "META"
    assert item["gsi1pk"] == "VIDEO#PUBLIC"
    assert item["gsi1sk"].startswith("PUB#")
    assert item["gsi1sk"].endswith("#vid001")
    assert item["published_at_sort"] == "2026-05-30T00:00:00Z"
    assert item["tags"] == ["歌枠", "雑談"]
    assert "updated_at" in item


def test_repository_writes_video_state_event_v04_key():
    repo = MemoryRepository()

    event = repo.append_video_state_event(
        "vid001",
        "archived",
        from_state="live",
        source_job_id="job-live",
        occurred_at="2026-05-30T00:00:00Z",
        payload={"actual_end_time": "2026-05-30T00:00:00Z"},
    )

    assert event["item_type"] == "VideoStateEvent"
    assert event["pk"] == "VID#vid001"
    assert event["sk"].startswith("EVT#STATE#2026-05-30T00:00:00Z#")
    assert event["event_id"].startswith("vse_")
    assert event["video_id"] == "vid001"
    assert event["event_name"] == "video.archived"
    assert event["from_state"] == "live"
    assert event["to_state"] == "archived"
    assert event["source_job_id"] == "job-live"
    assert event["occurred_at"] == "2026-05-30T00:00:00Z"
    assert event["payload"] == {"actual_end_time": "2026-05-30T00:00:00Z"}

    direct = video_state_event_item("vid001", "live", from_state="upcoming", occurred_at="2026-05-30T01:00:00Z")
    assert direct["event_name"] == "video.live_started"
    assert direct["sk"].startswith("EVT#STATE#2026-05-30T01:00:00Z#")


def test_repository_writes_video_stat_snapshot_from_video_statistics():
    repo = MemoryRepository()

    video = repo.put_video(
        {
            "video_id": "vid001",
            "title": "archive",
            "published_at": "2026-05-30T00:00:00Z",
            "statistics": {"viewCount": 100, "likeCount": 20, "commentCount": 3},
            "raw_metadata_uri": "s3://raw/videos.json",
            "sampled_at": "2026-05-30T12:34:56Z",
        }
    )

    snapshot = repo.get_item("VID#vid001", "STAT#2026053012")
    assert video["pk"] == "VID#vid001"
    assert snapshot["item_type"] == "VideoStatSnapshot"
    assert snapshot["video_id"] == "vid001"
    assert snapshot["sampled_at"] == "2026-05-30T12:34:56Z"
    assert snapshot["view_count"] == 100
    assert snapshot["like_count"] == 20
    assert snapshot["comment_count"] == 3
    assert snapshot["raw_s3_uri"] == "s3://raw/videos.json"

    explicit = repo.put_video_stat_snapshot(
        "vid002",
        {
            "sampled_at": "2026-05-30T13:00:00Z",
            "view_count": "7",
            "concurrent_viewers": "5",
        },
    )
    assert explicit["pk"] == "VID#vid002"
    assert explicit["sk"] == "STAT#2026053013"
    assert explicit["view_count"] == 7
    assert explicit["concurrent_viewers"] == 5


def test_repository_writes_current_index_and_summary_item_shapes():
    repo = MemoryRepository()

    video = repo.put_video(
        {
            "video_id": "vid001",
            "channel_id": "ch001",
            "title": "archive",
            "published_at": "2026-05-30T00:00:00Z",
            "tags": ["歌枠"],
            "public": True,
        }
    )
    tag_index = repo.get_item("TAG#歌枠", "VIDEO#vid001")
    tag_link = repo.get_item("VID#vid001", f"TAG#{tag_id_for_label('歌枠')}")
    aggregate = repo.put_chat_aggregate("vid001", {"message_count": 10, "top_terms": [{"term": "ありがとう", "count": 3}]})
    artifact = repo.put_artifact(
        "vid001",
        {
            "artifact_type": "wordcloud",
            "public_url_path": "/data/artifacts/wordcloud/vid001.json",
            "content_type": "application/json",
        },
    )
    quota = repo.record_quota_usage("videos.list", 1, {}, channel_id="ch001", video_count=1, job_id="job001")
    job, deduplicated = repo.create_job("metadata_sync", {"channel_id": "ch001"}, "metadata:ch001")
    idempotency = repo.get_item("IDEMP#metadata:ch001", "META")

    assert video["pk"] == "VID#vid001"
    assert tag_index["item_type"] == "VideoTagIndex"
    assert tag_index["gsi2pk"] == "TAG#歌枠"
    assert tag_link["item_type"] == "VideoTagLink"
    assert tag_link["gsi2pk"] == f"TAG#{tag_id_for_label('歌枠')}"
    assert aggregate["pk"] == "VID#vid001"
    assert aggregate["sk"] == "CHAT#AGG#v1"
    assert aggregate["aggregate_version"] == "v1"
    assert aggregate["computed_at"]
    assert artifact["sk"] == "ARTIFACT#wordcloud#v1"
    assert artifact["artifact_version"] == "v1"
    assert artifact["content_hash"].startswith("sha256:")
    assert quota["pk"].startswith("QUOTA#")
    assert quota["gsi3pk"] == "QUOTA#ALL"
    assert quota["record_type"] == "call"
    assert job["pk"] == f"JOB#{job['job_id']}"
    assert job["dedupe_key"] == "metadata:ch001"
    assert job["idempotency_key"] == "metadata:ch001"
    assert job["target_type"] == "channel"
    assert job["target_id"] == "ch001"
    assert job["latest_state"] == "queued"
    assert job["derived_state"] == "queued"
    assert job["attempt"] == 0
    assert job["max_attempts"] == 3
    assert job["queued_at"]
    assert job["next_run_at"]
    assert job["gsi3pk"] == "JOB#STATE#queued"
    assert job["gsi3sk"].startswith("NEXT#")
    assert job["gsi3sk"].endswith(f"#{job['job_id']}")
    assert idempotency["item_type"] == "Idempotency"
    assert idempotency["dedupe_key"] == "metadata:ch001"
    assert idempotency["first_job_id"] == job["job_id"]
    assert len(idempotency["request_hash"]) == 64
    assert deduplicated is False
    assert repo.get_job(job["job_id"])["events"][0]["event_name"] == "job.queued"


def test_repository_writes_idempotency_item_and_uses_it_for_dedupe_lookup():
    repo = MemoryRepository()
    first, deduplicated = repo.create_job("metadata_sync", {"channel_id": "ch001"}, "metadata:ch001")
    repo.idempotency_index.clear()
    second, duplicate = repo.create_job("metadata_sync", {"channel_id": "ch001"}, "metadata:ch001")
    item = repo.get_item("IDEMP#metadata:ch001", "META")

    assert deduplicated is False
    assert duplicate is True
    assert second["job_id"] == first["job_id"]
    assert item["item_type"] == "Idempotency"
    assert item["pk"] == "IDEMP#metadata:ch001"
    assert item["sk"] == "META"
    assert item["dedupe_key"] == "metadata:ch001"
    assert item["idempotency_key"] == "metadata:ch001"
    assert item["first_job_id"] == first["job_id"]
    assert item["job_id"] == first["job_id"]
    assert item["job_type"] == "metadata_sync"
    assert len(item["request_hash"]) == 64
    assert item["schema_version"] == "ddb-Idempotency-v1"
    assert item["entity_id"] == "metadata:ch001"


def test_repository_acquires_and_releases_lock_with_ttl_contract():
    repo = MemoryRepository()

    first = repo.acquire_lock("chat_replay#vid001", "job001", ttl_seconds=60, owner_request_id="req001")
    blocked = repo.acquire_lock("chat_replay#vid001", "job002", ttl_seconds=60, owner_request_id="req002")
    refreshed = repo.acquire_lock("chat_replay#vid001", "job001", ttl_seconds=120, owner_request_id="req003")
    wrong_release = repo.release_lock("chat_replay#vid001", "job002")
    right_release = repo.release_lock("chat_replay#vid001", "job001")

    assert first["item_type"] == "Lock"
    assert first["pk"] == "LOCK#chat_replay#vid001"
    assert first["sk"] == "META"
    assert first["lock_key"] == "chat_replay#vid001"
    assert first["owner_job_id"] == "job001"
    assert first["owner_request_id"] == "req001"
    assert first["acquired_at"]
    assert isinstance(first["expires_at"], int)
    assert first["schema_version"] == "ddb-Lock-v1"
    assert first["entity_id"] == "chat_replay#vid001"
    assert blocked is None
    assert refreshed["owner_request_id"] == "req003"
    assert refreshed["expires_at"] >= first["expires_at"]
    assert wrong_release is False
    assert right_release is True
    assert repo.get_item("LOCK#chat_replay#vid001", "META") is None


def test_repository_replaces_expired_lock_for_new_owner():
    repo = MemoryRepository()
    repo.put_item(
        {
            "item_type": "Lock",
            "pk": "LOCK#chat_replay#vid001",
            "sk": "META",
            "lock_key": "chat_replay#vid001",
            "owner_job_id": "job001",
            "acquired_at": "2026-05-30T00:00:00Z",
            "expires_at": 1,
        }
    )

    replaced = repo.acquire_lock("chat_replay#vid001", "job002", ttl_seconds=60)

    assert replaced["owner_job_id"] == "job002"
    assert repo.get_item("LOCK#chat_replay#vid001", "META")["owner_job_id"] == "job002"


def test_repository_writes_job_events_with_v04_shape_and_legacy_aliases():
    repo = MemoryRepository()
    job, _ = repo.create_job("metadata_sync", {"channel_id": "ch001"}, "metadata:ch001")
    started = repo.append_job_event(job["job_id"], "started", {"worker": "static-exporter"})
    completed = repo.append_job_event(job["job_id"], "completed", {"saved_count": 3})
    detail = repo.get_job(job["job_id"])

    assert started["item_type"] == "JobEvent"
    assert started["pk"] == f"JOB#{job['job_id']}"
    assert started["sk"] == "EVT#00000002"
    assert started["seq"] == 2
    assert started["event_name"] == "job.started"
    assert started["state_after"] == "running"
    assert started["occurred_at"]
    assert started["payload"] == {"worker": "static-exporter"}
    assert started["event_type"] == "started"
    assert started["details"] == {"worker": "static-exporter"}
    assert completed["sk"] == "EVT#00000003"
    assert completed["event_name"] == "job.succeeded"
    assert completed["state_after"] == "succeeded"
    assert detail["latest_state"] == "succeeded"
    assert detail["derived_state"] == "succeeded"
    assert [event["seq"] for event in detail["events"]] == [1, 2, 3]
    stored_job = repo.get_item(f"JOB#{job['job_id']}", "META")
    assert stored_job["latest_state"] == "succeeded"
    assert stored_job["derived_state"] == "succeeded"
    assert stored_job["gsi3pk"] == "JOB#STATE#succeeded"


def test_repository_derives_job_state_from_legacy_job_event_shape():
    repo = MemoryRepository()
    job, _ = repo.create_job("metadata_sync", {"channel_id": "ch001"}, "metadata:legacy")
    repo.put_item(
        {
            "item_type": "JobEvent",
            "pk": f"JOB#{job['job_id']}",
            "sk": "EVENT#2099-01-01T00:00:00Z#legacy",
            "job_id": job["job_id"],
            "event_type": "failed",
            "details": {"message": "boom"},
            "created_at": "2099-01-01T00:00:00Z",
        }
    )
    detail = repo.get_job(job["job_id"])

    assert detail["derived_state"] == "failed"
    assert detail["events"][-1]["event_name"] == "job.failed"
    assert detail["events"][-1]["state_after"] == "failed"
    assert detail["events"][-1]["payload"] == {"message": "boom"}


def test_repository_writes_app_config_v04_key_and_reads_legacy_fallback():
    repo = MemoryRepository()

    config = repo.put_app_config(
        {
            "system_name": "diopside",
            "target_channel_ids": ["ch001"],
            "youtube_api_key_ssm_param": "/diopside/youtube/api-key",
            "youtube_api_key": "secret-value",
            "collection_enabled": False,
            "public_export_enabled": True,
            "default_locale": "ja-JP",
            "public_base_path": "data",
            "maintenance_message": "paused",
        }
    )

    assert config["item_type"] == "AppConfig"
    assert config["pk"] == "APP#CONFIG"
    assert config["sk"] == "META"
    assert config["system_name"] == "diopside"
    assert config["target_channel_ids"] == ["ch001"]
    assert config["youtube_api_key_ssm_param"] == "/diopside/youtube/api-key"
    assert config["collection_enabled"] is False
    assert config["public_export_enabled"] is True
    assert config["default_locale"] == "ja-JP"
    assert config["public_base_path"] == "data"
    assert config["maintenance_message"] == "paused"
    assert "youtube_api_key" not in config
    assert repo.get_app_config() == config

    legacy_repo = MemoryRepository()
    legacy = legacy_repo.put_item(
        {
            "item_type": "AppConfig",
            "pk": "CONFIG#app",
            "sk": "META",
            "system_name": "legacy",
        }
    )

    assert legacy_repo.get_app_config() == legacy


def test_repository_writes_channel_sync_cursor_v04_key_and_reads_legacy_fallback():
    repo = MemoryRepository()

    cursor = repo.put_channel_sync_cursor(
        "ch001",
        {
            "uploads_playlist_id": "uploads",
            "next_page_token": "next-token",
            "last_seen_video_id": "vid001",
            "last_seen_published_at": "2026-05-30T00:00:00Z",
            "raw_playlist_uri": "s3://raw/playlist.json",
            "raw_videos_uri": "s3://raw/videos.json",
            "saved_count": 2,
            "job_id": "job-meta",
        },
    )

    assert cursor["item_type"] == "ChannelSyncCursor"
    assert cursor["pk"] == "CH#ch001"
    assert cursor["sk"] == "CURSOR#uploads"
    assert cursor["channel_id"] == "ch001"
    assert cursor["uploads_playlist_id"] == "uploads"
    assert cursor["next_page_token"] == "next-token"
    assert cursor["next_page_token_hash"].startswith("page_")
    assert cursor["last_seen_video_id"] == "vid001"
    assert cursor["raw_playlist_uri"] == "s3://raw/playlist.json"
    assert cursor["raw_videos_uri"] == "s3://raw/videos.json"
    assert cursor["saved_count"] == 2
    assert cursor["job_id"] == "job-meta"
    assert repo.get_channel_sync_cursor("ch001") == cursor

    legacy_repo = MemoryRepository()
    legacy = legacy_repo.put_item(
        {
            "item_type": "ChannelCursor",
            "pk": "CHANNEL#legacy",
            "sk": "CURSOR#metadata",
            "channel_id": "legacy",
            "cursor_name": "metadata",
            "next_page_token": "resume-token",
        }
    )

    assert legacy_repo.get_channel_sync_cursor("legacy") == legacy


def test_repository_adds_common_item_metadata_and_preserves_created_at():
    repo = MemoryRepository()

    first = repo.put_item(
        {
            "item_type": "AppConfig",
            "pk": "CONFIG#app",
            "sk": "META",
            "system_name": "diopside",
        }
    )
    updated = repo.put_item(
        {
            "item_type": "AppConfig",
            "pk": "CONFIG#app",
            "sk": "META",
            "system_name": "diopside-v5",
        }
    )
    explicit = repo.put_item(
        {
            "item_type": "Lock",
            "pk": "LOCK#manual",
            "sk": "META",
            "schema_version": "custom-lock/v1",
            "entity_id": "manual-lock",
            "created_at": "2026-05-30T00:00:00Z",
            "updated_at": "2026-05-30T01:00:00Z",
        }
    )

    assert first["schema_version"] == "ddb-AppConfig-v1"
    assert first["entity_id"] == "CONFIG#app#META"
    assert "created_at" in first
    assert "updated_at" in first
    assert updated["created_at"] == first["created_at"]
    assert updated["schema_version"] == first["schema_version"]
    assert updated["entity_id"] == first["entity_id"]
    assert explicit["schema_version"] == "custom-lock/v1"
    assert explicit["entity_id"] == "manual-lock"
    assert explicit["created_at"] == "2026-05-30T00:00:00Z"
    assert explicit["updated_at"] == "2026-05-30T01:00:00Z"


def test_repository_writes_channel_ref_and_lists_channels_from_read_model():
    repo = MemoryRepository()

    channel = repo.put_channel(
        {
            "channel_id": "ch001",
            "enabled": True,
            "display_name": "白雪巴",
            "uploads_playlist_id": "UUuploads",
            "metadata_interval_minutes": 720,
            "live_scan_interval_minutes": 30,
            "notification_enabled": True,
            "priority": 10,
        }
    )
    ref = repo.get_item("APP#CHANNELS", "CH#ch001")

    assert channel["item_type"] == "Channel"
    assert channel["pk"] == "CH#ch001"
    assert channel["sk"] == "META"
    assert channel["channel_id"] == "ch001"
    assert channel["channel_title"] == "白雪巴"
    assert channel["display_name"] == "白雪巴"
    assert channel["collect_enabled"] is True
    assert channel["enabled"] is True
    assert channel["default_tags"] == []
    assert repo.get_channel("ch001") == channel
    assert ref["item_type"] == "ChannelRef"
    assert ref["pk"] == "APP#CHANNELS"
    assert ref["sk"] == "CH#ch001"
    assert ref["channel_id"] == "ch001"
    assert ref["collect_enabled"] is True
    assert ref["enabled"] is True
    assert ref["priority"] == 10
    assert ref["channel_title"] == "白雪巴"
    assert ref["display_name"] == "白雪巴"
    assert ref["uploads_playlist_id"] == "UUuploads"
    assert ref["notification_enabled"] is True
    assert repo.list_channels() == [ref]


def test_repository_list_channels_falls_back_to_channel_items_without_refs():
    repo = MemoryRepository()
    repo.put_item(
        {
            "item_type": "Channel",
            "pk": "CHANNEL#ch001",
            "sk": "META",
            "channel_id": "ch001",
            "display_name": "fallback",
            "enabled": True,
        }
    )

    assert repo.list_channels()[0]["item_type"] == "Channel"
    assert repo.get_channel("ch001")["pk"] == "CHANNEL#ch001"


def test_repository_writes_random_bucket_for_public_videos_and_removes_private_entries():
    repo = MemoryRepository()

    video = repo.put_video(
        {
            "video_id": "vid001",
            "title": "archive",
            "published_at": "2026-05-30T00:00:00Z",
            "duration_sec": 1200,
            "thumbnail_url": "/thumb.jpg",
            "tags": ["歌枠"],
            "public": True,
        }
    )
    expected_bucket = random_bucket_item(video)
    bucket = repo.get_item("RANDOM#DEFAULT", expected_bucket["sk"])

    assert bucket["item_type"] == "RandomBucket"
    assert bucket["pk"] == "RANDOM#DEFAULT"
    assert bucket["sk"].startswith("VID#")
    assert bucket["bucket_no"] == expected_bucket["bucket_no"]
    assert bucket["video_id"] == "vid001"
    assert bucket["title"] == "archive"
    assert bucket["thumbnail_url"] == "/thumb.jpg"
    assert bucket["duration_sec"] == 1200
    assert bucket["tags"] == ["歌枠"]
    assert bucket["published_at"] == "2026-05-30T00:00:00Z"
    assert "generated_at" in bucket
    assert repo.list_random_videos() == [bucket]

    repo.put_video({**video, "public": False})

    assert repo.get_item("RANDOM#DEFAULT", expected_bucket["sk"]) is None
    assert repo.list_random_videos() == []


def test_repository_writes_video_month_index_and_removes_stale_entries():
    repo = MemoryRepository()

    repo.put_video(
        {
            "video_id": "vid001",
            "title": "archive",
            "published_at": "2026-05-30T00:00:00Z",
            "duration_sec": 1200,
            "thumbnail_url": "/thumb.jpg",
            "tags": ["歌枠"],
            "public": True,
        }
    )
    index = repo.get_item("VID#vid001", "INDEX#MONTH#202605")

    assert index["item_type"] == "VideoMonthIndex"
    assert index["pk"] == "VID#vid001"
    assert index["sk"] == "INDEX#MONTH#202605"
    assert index["video_id"] == "vid001"
    assert index["yyyy_mm"] == "2026-05"
    assert index["published_at"] == "2026-05-30T00:00:00Z"
    assert index["title"] == "archive"
    assert index["thumbnail_url"] == "/thumb.jpg"
    assert index["duration_sec"] == 1200
    assert index["archive_state"] == "archived"
    assert index["gsi1pk"] == "VIDEO#MONTH#202605"
    assert index["gsi1sk"] == "PUB#2026-05-30T00:00:00Z#vid001"
    assert repo.list_video_month_indexes(year=2026, month=5) == [index]

    repo.put_video(
        {
            "video_id": "vid001",
            "title": "archive moved",
            "published_at": "2026-06-01T00:00:00Z",
            "tags": ["歌枠"],
            "public": True,
        }
    )

    assert repo.get_item("VID#vid001", "INDEX#MONTH#202605") is None
    assert repo.get_item("VID#vid001", "INDEX#MONTH#202606")["title"] == "archive moved"

    repo.put_video(
        {
            "video_id": "vid001",
            "title": "archive private",
            "published_at": "2026-06-01T00:00:00Z",
            "tags": ["歌枠"],
            "public": False,
        }
    )

    assert repo.get_item("VID#vid001", "INDEX#MONTH#202606") is None
    assert repo.list_video_month_indexes(year=2026, month=6) == []


def test_repository_updates_video_tags_and_removes_stale_tag_index():
    repo = MemoryRepository()
    repo.put_video(
        {
            "video_id": "vid001",
            "title": "archive",
            "published_at": "2026-05-30T00:00:00Z",
            "tags": ["歌枠", "雑談"],
            "public": True,
        }
    )

    updated = repo.update_video_tags("vid001", add_tags=["手動"], remove_tags=["雑談"])

    assert updated["tags"] == ["歌枠", "手動"]
    assert updated["manual_tag_correction"]["add_tags"] == ["手動"]
    assert updated["manual_tag_correction"]["remove_tags"] == ["雑談"]
    assert repo.get_item("TAG#歌枠", "VIDEO#vid001")
    assert repo.get_item("TAG#手動", "VIDEO#vid001")
    assert repo.get_item("TAG#雑談", "VIDEO#vid001") is None
    assert repo.get_item("VID#vid001", f"TAG#{tag_id_for_label('歌枠')}")
    manual_link = repo.get_item("VID#vid001", f"TAG#{tag_id_for_label('手動')}")
    assert manual_link["tag_label"] == "手動"
    assert manual_link["tag_type"] == "manual"
    assert manual_link["source"] == "manual_admin"
    assert repo.get_item("VID#vid001", f"TAG#{tag_id_for_label('雑談')}") is None
    assert [item["label"] for item in repo.list_tags()] == ["手動", "歌枠"]


def test_repository_writes_video_tag_link_v04_item_shape():
    repo = MemoryRepository()

    repo.put_video(
        {
            "video_id": "vid001",
            "title": "archive",
            "published_at": "2026-05-30T00:00:00Z",
            "thumbnail_url": "/thumb.jpg",
            "duration_sec": 1200,
            "tags": ["歌枠"],
            "public": True,
        }
    )
    tag_id = tag_id_for_label("歌枠")
    link = repo.get_item("VID#vid001", f"TAG#{tag_id}")

    assert link["item_type"] == "VideoTagLink"
    assert link["pk"] == "VID#vid001"
    assert link["sk"] == f"TAG#{tag_id}"
    assert link["video_id"] == "vid001"
    assert link["tag_id"] == tag_id
    assert link["tag_label"] == "歌枠"
    assert link["tag_type"] == "generated"
    assert link["source"] == "repository"
    assert link["published_at"] == "2026-05-30T00:00:00Z"
    assert link["title"] == "archive"
    assert link["thumbnail_url"] == "/thumb.jpg"
    assert link["duration_sec"] == 1200
    assert link["gsi2pk"] == f"TAG#{tag_id}"
    assert link["gsi2sk"].endswith("#vid001")
    assert link["schema_version"] == "ddb-VideoTagLink-v1"


def test_repository_writes_chat_aggregate_v04_key_and_reads_legacy_fallback():
    repo = MemoryRepository()

    aggregate = repo.put_chat_aggregate(
        "vid001",
        {
            "message_count": 10,
            "source_normalized_s3_uri": "s3://processed/chat-normalized/video_id=vid001/part-000.jsonl",
            "heatmap_s3_uri": "s3://processed/chat-aggregate/video_id=vid001/heatmap.json",
            "top_terms": [{"term": "ありがとう", "count": 3}],
        },
    )

    assert aggregate["item_type"] == "ChatAggregate"
    assert aggregate["pk"] == "VID#vid001"
    assert aggregate["sk"] == "CHAT#AGG#v1"
    assert aggregate["video_id"] == "vid001"
    assert aggregate["aggregate_version"] == "v1"
    assert aggregate["message_count"] == 10
    assert aggregate["computed_at"]
    assert repo.get_chat_aggregate("vid001") == aggregate

    legacy = repo.put_item(
        {
            "item_type": "ChatAggregate",
            "pk": "VIDEO#legacy",
            "sk": "CHAT#AGGREGATE",
            "video_id": "legacy",
            "message_count": 1,
            "top_terms": [],
        }
    )

    assert repo.get_chat_aggregate("legacy") == legacy


def test_repository_writes_chat_manifest_v04_key_and_reads_legacy_fallback():
    repo = MemoryRepository()

    manifest = repo.put_chat_manifest(
        "vid001",
        {
            "normalized_s3_uri": "s3://processed/chat-normalized/video_id=vid001/part-000.jsonl",
            "message_count": 10,
            "last_offset_ms": 60000,
        },
    )

    assert manifest["item_type"] == "ChatManifest"
    assert manifest["pk"] == "VID#vid001"
    assert manifest["sk"] == "CHAT#MANIFEST"
    assert manifest["video_id"] == "vid001"
    assert manifest["normalized_s3_uri"] == "s3://processed/chat-normalized/video_id=vid001/part-000.jsonl"
    assert manifest["message_count"] == 10
    assert manifest["live_collection_state"] == "not_started"
    assert manifest["replay_collection_state"] == "not_started"
    assert manifest["normalization_state"] == "succeeded"
    assert manifest["normalized_schema_version"] == "chat-message/v1"
    assert repo.get_chat_manifest("vid001") == manifest

    legacy = repo.put_item(
        {
            "item_type": "ChatManifest",
            "pk": "VIDEO#legacy",
            "sk": "CHAT#MANIFEST",
            "video_id": "legacy",
            "normalized_uri": "s3://processed/legacy.jsonl",
            "message_count": 1,
        }
    )

    assert repo.get_chat_manifest("legacy") == legacy


def test_repository_writes_chat_page_manifest_v04_key_and_reads_legacy_fallback():
    repo = MemoryRepository()

    page = repo.put_chat_page_manifest(
        "vid001",
        {
            "source": "replay",
            "raw_s3_uri": "s3://raw/youtube/chat/video_id=vid001/source=replay/1.jsonl",
            "item_count": 2,
            "checksum": "sha256:page",
            "job_id": "job-chat",
            "next_poll": {"action": "stop"},
        },
    )

    assert page["item_type"] == "ChatPageManifest"
    assert page["pk"] == "VID#vid001"
    assert page["sk"] == "CHAT#PAGE#replay#1"
    assert page["video_id"] == "vid001"
    assert page["source"] == "replay"
    assert page["seq"] == 1
    assert page["raw_s3_uri"] == "s3://raw/youtube/chat/video_id=vid001/source=replay/1.jsonl"
    assert page["item_count"] == 2
    assert page["checksum"] == "sha256:page"
    assert page["job_id"] == "job-chat"
    assert page["s3_uri"] == page["raw_s3_uri"]
    assert page["message_count"] == 2
    assert page["sha256"] == "sha256:page"
    assert repo.list_chat_chunks("vid001") == [page]

    legacy = repo.put_item(
        {
            "item_type": "ChatMessageChunkManifest",
            "pk": "VIDEO#legacy",
            "sk": "CHAT#RAW#replay#fixture",
            "video_id": "legacy",
            "source": "replay",
            "s3_uri": "s3://raw/legacy.jsonl",
            "message_count": 1,
            "sha256": "legacy",
        }
    )

    assert repo.list_chat_chunks("legacy") == [legacy]


def test_repository_writes_tag_summary_and_hides_stale_tags():
    repo = MemoryRepository()
    repo.put_video(
        {
            "video_id": "vid001",
            "title": "first",
            "published_at": "2026-05-29T00:00:00Z",
            "tags": ["歌枠", "雑談"],
            "public": True,
        }
    )
    repo.put_video(
        {
            "video_id": "vid002",
            "title": "second",
            "published_at": "2026-05-30T00:00:00Z",
            "tags": ["歌枠"],
            "public": True,
        }
    )

    tag_id = tag_id_for_label("歌枠")
    summary = repo.get_item(f"TAG#{tag_id}", "META")

    assert summary["item_type"] == "TagSummary"
    assert summary["pk"] == f"TAG#{tag_id}"
    assert summary["sk"] == "META"
    assert summary["tag_id"] == tag_id
    assert summary["label"] == "歌枠"
    assert summary["category"] == "auto"
    assert summary["aliases"] == []
    assert summary["video_count"] == 2
    assert summary["latest_video_id"] == "vid002"
    assert summary["latest_video_at"] == "2026-05-30T00:00:00Z"
    assert summary["sort_order"] == 0
    assert summary["public_visible"] is True
    assert summary["gsi2pk"] == "TAG#SUMMARY"
    assert [item["label"] for item in repo.list_tags()] == ["歌枠", "雑談"]

    repo.update_video_tags("vid001", remove_tags=["雑談"])

    stale = repo.get_item(f"TAG#{tag_id_for_label('雑談')}", "META")
    assert stale["video_count"] == 0
    assert stale["public_visible"] is False
    assert [item["label"] for item in repo.list_tags()] == ["歌枠"]


def test_repository_accepts_notification_plan_v04_item_shape():
    repo = MemoryRepository()

    item = repo.put_item(
        {
            "item_type": "NotificationPlan",
            "pk": "VID#vid001",
            "sk": "NOTIFY#before_30min",
            "video_id": "vid001",
            "notification_type": "before_30min",
            "due_at": "2026-05-30T11:30:00Z",
            "delivery_state": "planned",
            "gsi3pk": "NOTIFY#DUE",
            "gsi3sk": "DUE#2026-05-30T11:30:00Z#vid001#before_30min",
        }
    )

    assert item["item_type"] == "NotificationPlan"
    assert repo.get_item("VID#vid001", "NOTIFY#before_30min")["gsi3pk"] == "NOTIFY#DUE"


def test_repository_keeps_quota_daily_summary_out_of_call_record_list():
    repo = MemoryRepository()
    call = repo.record_quota_usage("videos.list", 1, {}, channel_id="ch001", video_count=1, job_id="job001")
    summary = repo.put_item(
        {
            "item_type": "QuotaUsage",
            "pk": "QUOTA#20260530",
            "sk": "METHOD#videos.list",
            "record_type": "daily_method_summary",
            "quota_date": "20260530",
            "method": "videos.list",
            "call_count": 1,
            "units_used": 1,
            "unit_per_call": 1,
            "warning_emitted": False,
            "updated_at": "2026-05-30T12:27:00Z",
            "gsi3pk": "QUOTA#ROLLUP",
            "gsi3sk": "20260530#videos.list",
        }
    )

    assert repo.get_item("QUOTA#20260530", "METHOD#videos.list") == summary
    assert repo.list_quota_summaries() == [summary]
    assert repo.list_quota_usage() == [call]


def test_repository_writes_artifact_with_v04_versioned_key_and_required_hash():
    repo = MemoryRepository()

    artifact = repo.put_artifact(
        "vid001",
        {
            "artifact_type": "wordcloud",
            "artifact_version": "v2",
            "public_url_path": "/data/artifacts/wordcloud/vid001.png",
            "content_type": "image/png",
            "summary": {"width": 1200, "height": 630},
        },
    )

    assert artifact["item_type"] == "Artifact"
    assert artifact["pk"] == "VID#vid001"
    assert artifact["sk"] == "ARTIFACT#wordcloud#v2"
    assert artifact["video_id"] == "vid001"
    assert artifact["artifact_id"] == "vid001:wordcloud"
    assert artifact["artifact_type"] == "wordcloud"
    assert artifact["artifact_version"] == "v2"
    assert artifact["content_hash"].startswith("sha256:")
    assert len(artifact["content_hash"]) == len("sha256:") + 64
    assert artifact["generated_at"]
    assert repo.get_artifact_by_id("vid001:wordcloud") == artifact
    assert repo.list_artifacts("vid001") == [artifact]


def test_repository_lists_legacy_artifact_shape_as_fallback():
    repo = MemoryRepository()
    legacy = repo.put_item(
        {
            "item_type": "Artifact",
            "pk": "VIDEO#vid001",
            "sk": "ARTIFACT#timestamp",
            "video_id": "vid001",
            "artifact_type": "timestamp",
            "public_url_path": "/data/artifacts/timestamps/vid001.json",
            "content_hash": "sha256:" + ("a" * 64),
        }
    )

    assert repo.get_artifact_by_id("vid001:timestamp") == legacy
    assert repo.list_artifacts("vid001") == [legacy]


def test_repository_records_static_export_history_v04_item_shape():
    repo = MemoryRepository()
    manifest = {
        "schema_version": "public-manifest/v1",
        "generated_at": "2026-05-30T13:15:00Z",
        "export_version": "unit-export",
        "static_paths": {
            "STATIC-003": {"items": {"vid001": {"path": "/data/videos/vid001.json"}}},
            "STATIC-006": {"checksum_sha256": "a" * 64},
        },
    }

    export = repo.record_static_export(
        manifest,
        reason="manual",
        manifest_s3_uri="s3://public-data/data/latest-manifest.json",
        public_prefix="data/v/unit-export/public",
        tag_count=3,
        generated_job_id="job001",
        uploaded_object_count=12,
    )

    assert export["item_type"] == "StaticExport"
    assert export["pk"] == "EXPORT#public"
    assert export["sk"] == "VERSION#2026-05-30T13:15:00Z"
    assert export["export_id"].startswith("export_")
    assert export["export_version"] == "unit-export"
    assert export["reason"] == "manual"
    assert export["manifest_s3_uri"] == "s3://public-data/data/latest-manifest.json"
    assert export["public_prefix"] == "data/v/unit-export/public"
    assert export["video_count"] == 1
    assert export["tag_count"] == 3
    assert export["schema_versions"]["manifest"] == "public-manifest/v1"
    assert export["content_hash"] == "a" * 64
    assert export["publish_state"] == "published"
    assert export["generated_job_id"] == "job001"
    assert export["uploaded_object_count"] == 12
    assert repo.list_static_exports() == [export]


def test_repository_rejects_item_types_not_yet_supported_by_current_allowlist():
    repo = MemoryRepository()

    unsupported_v04_types = V04_ITEM_TYPES - ITEM_TYPES

    assert "RandomBucket" not in unsupported_v04_types
    assert "NotificationPlan" not in unsupported_v04_types
    assert "StaticExport" not in unsupported_v04_types
    assert "TagSummary" not in unsupported_v04_types
    assert "VideoMonthIndex" not in unsupported_v04_types
    assert "ChannelRef" not in unsupported_v04_types
    assert "Idempotency" not in unsupported_v04_types
    assert "VideoTagLink" not in unsupported_v04_types
    for item_type in sorted(unsupported_v04_types):
        try:
            repo.put_item({"item_type": item_type, "pk": f"TEST#{item_type}", "sk": "META"})
        except ValueError as exc:
            assert f"unsupported item_type: {item_type}" in str(exc)
        else:
            raise AssertionError(f"{item_type} should remain explicitly unsupported until implemented")
