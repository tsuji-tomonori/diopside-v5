import json
import subprocess

from diopside_core import MemoryRepository
import static_exporter.handler as exporter_handler
from static_exporter.handler import export_from_fixture, export_public_data


def test_export_from_fixture(tmp_path):
    manifest = export_from_fixture(
        source_dir=__import__("pathlib").Path("data/fixtures/public"),
        out_dir=tmp_path,
        export_version="test-export",
    )
    assert manifest["export_version"] == "test-export"
    written = json.loads((tmp_path / "latest-manifest.json").read_text(encoding="utf-8"))
    assert written["schema_version"] == "public-manifest/v1"
    assert written["base_path"] == "/data/v/test-export"
    assert written["indexes"]["videos_latest"] == "/data/v/test-export/public/index/videos-latest.json"
    assert (tmp_path / "data/v/test-export/public/index/videos-latest.json").exists()
    subprocess.run(["node", "tools/check-public-contract.mjs", str(tmp_path)], check=True)


def test_export_public_data_from_repository(tmp_path):
    repo = MemoryRepository()
    repo.put_video(
        {
            "video_id": "vid001",
            "title": "公開アーカイブ",
            "description": "00:30 見どころ",
            "published_at": "2026-05-28T00:00:00Z",
            "duration_sec": 1200,
            "tags": ["雑談"],
            "thumbnail_url": "/assets/placeholder-thumbnail.svg",
        }
    )
    repo.put_chat_aggregate(
        "vid001",
        {
            "message_count": 3,
            "unique_author_count": 2,
            "paid_message_count": 0,
            "emoji_count": 1,
            "timeline_buckets": [{"offset_sec": 60, "message_count": 3}],
            "top_terms": [{"term": "ありがとう", "score": 3}],
        },
    )
    repo.put_video(
        {
            "video_id": "vid002",
            "title": "集計なしアーカイブ",
            "published_at": "2026-05-27T00:00:00Z",
            "tags": [],
        }
    )
    repo.put_chat_aggregate(
        "vid002",
        {
            "message_count": 0,
            "unique_author_count": 0,
            "paid_message_count": 0,
            "emoji_count": 0,
            "timeline_buckets": [],
            "top_terms": [],
        },
    )
    manifest = export_public_data(repo, tmp_path, "unit")
    assert manifest["indexes"]["videos_latest"] == "/data/v/unit/public/index/videos-latest.json"
    assert manifest["static_paths"]["STATIC-001"]["path"] == "/data/home.json"
    assert manifest["static_paths"]["STATIC-002"]["path"] == "/data/videos/index.json"
    assert manifest["static_paths"]["STATIC-003"]["items"]["vid001"]["path"] == "/data/videos/vid001.json"
    assert manifest["static_paths"]["STATIC-005"]["items"]["2026"]["path"] == "/data/calendar/2026.json"
    assert manifest["static_paths"]["STATIC-007"]["items"]["vid001"]["path"] == "/data/artifacts/wordcloud/vid001.json"
    assert manifest["static_paths"]["STATIC-008"]["items"]["vid001"]["path"] == "/data/artifacts/timestamps/vid001.json"
    detail = json.loads((tmp_path / "data/v/unit/public/videos/vid001.json").read_text(encoding="utf-8"))
    alias_detail = json.loads((tmp_path / "data/videos/vid001.json").read_text(encoding="utf-8"))
    home = json.loads((tmp_path / "data/home.json").read_text(encoding="utf-8"))
    calendar = json.loads((tmp_path / "data/calendar/2026.json").read_text(encoding="utf-8"))
    wordcloud_json = json.loads((tmp_path / "data/artifacts/wordcloud/vid001.json").read_text(encoding="utf-8"))
    timestamps_json = json.loads((tmp_path / "data/artifacts/timestamps/vid001.json").read_text(encoding="utf-8"))
    empty_detail = json.loads((tmp_path / "data/v/unit/public/videos/vid002.json").read_text(encoding="utf-8"))
    svg_path = tmp_path / "data/v/unit/public/artifacts/wordcloud/vid001.svg"
    assert detail["chat_summary"]["wordcloud_url"] == "/data/v/unit/public/artifacts/wordcloud/vid001.svg"
    assert detail["artifacts"]["wordcloud"] == {"path": "/data/v/unit/public/artifacts/wordcloud/vid001.svg", "content_type": "image/svg+xml"}
    assert detail["timestamps"][0]["offset_sec"] == 30
    assert alias_detail["video"]["video_id"] == "vid001"
    assert home["schema_version"] == "public-home/v1"
    assert home["latest_videos"][0]["detail_path"] == "/data/videos/vid001.json"
    assert calendar["months"][0]["items"][0]["detail_path"] == "/data/videos/vid001.json"
    assert wordcloud_json["top_terms"][0]["term"] == "ありがとう"
    assert timestamps_json["items"][0]["offset_sec"] == 30
    assert svg_path.exists()
    assert "ありがとう" in svg_path.read_text(encoding="utf-8")
    assert empty_detail["chat_summary"]["wordcloud_url"] is None
    assert empty_detail["artifacts"]["wordcloud"] is None
    assert not (tmp_path / "data/v/unit/public/artifacts/wordcloud/vid002.svg").exists()
    subprocess.run(["node", "tools/check-public-contract.mjs", str(tmp_path)], check=True)


def test_export_public_data_reflects_manual_tag_correction(tmp_path):
    repo = MemoryRepository()
    repo.put_video(
        {
            "video_id": "vid001",
            "title": "公開アーカイブ",
            "published_at": "2026-05-28T00:00:00Z",
            "tags": ["自動", "雑談"],
        }
    )
    repo.update_video_tags("vid001", add_tags=["手動"], remove_tags=["雑談"])

    export_public_data(repo, tmp_path, "unit")

    tags = json.loads((tmp_path / "data/tags.json").read_text(encoding="utf-8"))
    detail = json.loads((tmp_path / "data/videos/vid001.json").read_text(encoding="utf-8"))
    labels = {item["label"] for item in tags["items"]}
    assert labels == {"手動", "自動"}
    assert detail["video"]["tags"] == ["自動", "手動"]


def test_export_public_wordcloud_svg_is_deterministic(tmp_path):
    repo = MemoryRepository()
    repo.put_video({"video_id": "vid001", "title": "公開アーカイブ", "published_at": "2026-05-28T00:00:00Z", "tags": []})
    repo.put_chat_aggregate(
        "vid001",
        {
            "message_count": 2,
            "unique_author_count": 1,
            "paid_message_count": 0,
            "emoji_count": 0,
            "timeline_buckets": [],
            "top_terms": [{"term": "巴さん", "score": 4}, {"term": "ありがとう", "score": 2}],
        },
    )
    first = tmp_path / "first"
    second = tmp_path / "second"

    export_public_data(repo, first, "unit")
    export_public_data(repo, second, "unit")

    first_svg = (first / "data/v/unit/public/artifacts/wordcloud/vid001.svg").read_text(encoding="utf-8")
    second_svg = (second / "data/v/unit/public/artifacts/wordcloud/vid001.svg").read_text(encoding="utf-8")
    assert first_svg == second_svg
    assert first_svg.startswith("<svg ")
    assert "巴さん" in first_svg


def test_static_export_job_records_completion(monkeypatch, tmp_path):
    repo = MemoryRepository()
    repo.put_video({"video_id": "vid001", "title": "公開アーカイブ", "published_at": "2026-05-28T00:00:00Z", "tags": []})
    job, _ = repo.create_job("static_export", {"scope": "all"}, "static-export-job")
    monkeypatch.setattr(exporter_handler, "_repository_from_env", lambda: repo)

    result = exporter_handler.lambda_handler(
        {
            "job_id": job["job_id"],
            "job_type": "static_export",
            "input": {"output_dir": str(tmp_path), "export_version": "job-unit"},
        },
        None,
    )

    assert result["status"] == "succeeded"
    assert repo.get_job(job["job_id"])["derived_state"] == "succeeded"
    assert (tmp_path / "latest-manifest.json").exists()


def test_upload_directory_publishes_manifest_last(monkeypatch, tmp_path):
    uploads = []

    class FakeS3:
        def upload_file(self, filename, bucket, key, ExtraArgs):
            uploads.append({"filename": filename, "bucket": bucket, "key": key, "content_type": ExtraArgs["ContentType"]})

    monkeypatch.setenv("DIOPSIDE_PUBLIC_DATA_BUCKET", "public-bucket")
    monkeypatch.setattr(exporter_handler, "boto3", type("FakeBoto3", (), {"client": staticmethod(lambda name: FakeS3())}))
    (tmp_path / "data/v/unit/public/index").mkdir(parents=True)
    (tmp_path / "data/v/unit/public/index/videos-latest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data/v/unit/public/artifacts/wordcloud").mkdir(parents=True)
    (tmp_path / "data/v/unit/public/artifacts/wordcloud/vid001.svg").write_text("<svg></svg>", encoding="utf-8")
    (tmp_path / "latest-manifest.json").write_text("{}", encoding="utf-8")

    count = exporter_handler._upload_directory(tmp_path)

    assert count == 3
    assert [item["key"] for item in uploads][-1] == "data/latest-manifest.json"
    assert uploads[-1]["content_type"] == "application/json; charset=utf-8"
    assert any(item["key"].endswith("vid001.svg") and item["content_type"] == "image/svg+xml" for item in uploads)


def test_upload_directory_does_not_publish_manifest_after_versioned_failure(monkeypatch, tmp_path):
    uploads = []

    class FakeS3:
        def upload_file(self, filename, bucket, key, ExtraArgs):
            if key.endswith("videos-latest.json"):
                raise RuntimeError("versioned upload failed")
            uploads.append(key)

    monkeypatch.setenv("DIOPSIDE_PUBLIC_DATA_BUCKET", "public-bucket")
    monkeypatch.setattr(exporter_handler, "boto3", type("FakeBoto3", (), {"client": staticmethod(lambda name: FakeS3())}))
    (tmp_path / "data/v/unit/public/index").mkdir(parents=True)
    (tmp_path / "data/v/unit/public/index/videos-latest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "latest-manifest.json").write_text("{}", encoding="utf-8")

    try:
        exporter_handler._upload_directory(tmp_path)
    except RuntimeError as exc:
        assert str(exc) == "versioned upload failed"
    else:
        raise AssertionError("_upload_directory should fail before publishing manifest")

    assert "data/latest-manifest.json" not in uploads
