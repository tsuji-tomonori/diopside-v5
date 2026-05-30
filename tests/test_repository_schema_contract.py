from pathlib import Path

from diopside_core.repository import ITEM_TYPES, MemoryRepository, random_bucket_item, tag_id_for_label, video_item


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
    assert quota["record_type"] == "call"
    assert job["pk"] == f"JOB#{job['job_id']}"
    assert job["gsi3pk"] == "JOB#ALL"
    assert deduplicated is False
    assert repo.get_job(job["job_id"])["events"][0]["event_type"] == "queued"


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
    assert [item["label"] for item in repo.list_tags()] == ["手動", "歌枠"]


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
            "updated_at": "2026-05-30T12:27:00Z",
            "gsi3pk": "QUOTA#ROLLUP",
            "gsi3sk": "20260530#videos.list",
        }
    )

    assert repo.get_item("QUOTA#20260530", "METHOD#videos.list") == summary
    assert repo.list_quota_usage() == [call]


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

    assert {"ChannelRef", "VideoMonthIndex", "VideoTagLink"} <= unsupported_v04_types
    assert "RandomBucket" not in unsupported_v04_types
    assert "NotificationPlan" not in unsupported_v04_types
    assert "StaticExport" not in unsupported_v04_types
    assert "TagSummary" not in unsupported_v04_types
    for item_type in sorted(unsupported_v04_types):
        try:
            repo.put_item({"item_type": item_type, "pk": f"TEST#{item_type}", "sk": "META"})
        except ValueError as exc:
            assert f"unsupported item_type: {item_type}" in str(exc)
        else:
            raise AssertionError(f"{item_type} should remain explicitly unsupported until implemented")
