from pathlib import Path

from diopside_core.repository import ITEM_TYPES, MemoryRepository, video_item


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
    assert item["pk"] == "VIDEO#vid001"
    assert item["sk"] == "META"
    assert item["gsi1pk"] == "VIDEO#PUBLIC"
    assert item["gsi1sk"] == "2026-05-30T00:00:00Z#vid001"
    assert item["tags"] == ["歌枠", "雑談"]
    assert "updated_at" in item


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

    assert video["pk"] == "VIDEO#vid001"
    assert tag_index["item_type"] == "VideoTagIndex"
    assert tag_index["gsi2pk"] == "TAG#歌枠"
    assert aggregate["pk"] == "VIDEO#vid001"
    assert aggregate["sk"] == "CHAT#AGGREGATE"
    assert artifact["sk"] == "ARTIFACT#wordcloud"
    assert quota["pk"].startswith("QUOTA#")
    assert quota["gsi3pk"] == "QUOTA#ALL"
    assert job["pk"] == f"JOB#{job['job_id']}"
    assert job["gsi3pk"] == "JOB#ALL"
    assert deduplicated is False
    assert repo.get_job(job["job_id"])["events"][0]["event_type"] == "queued"


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


def test_repository_rejects_item_types_not_yet_supported_by_current_allowlist():
    repo = MemoryRepository()

    unsupported_v04_types = V04_ITEM_TYPES - ITEM_TYPES

    assert {"ChannelRef", "VideoMonthIndex", "RandomBucket"} <= unsupported_v04_types
    assert "NotificationPlan" not in unsupported_v04_types
    for item_type in sorted(unsupported_v04_types):
        try:
            repo.put_item({"item_type": item_type, "pk": f"TEST#{item_type}", "sk": "META"})
        except ValueError as exc:
            assert f"unsupported item_type: {item_type}" in str(exc)
        else:
            raise AssertionError(f"{item_type} should remain explicitly unsupported until implemented")
