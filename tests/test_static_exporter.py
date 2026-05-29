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
    assert (tmp_path / "data/v/dev-fixture/public/index/videos-latest.json").exists()


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
    detail = json.loads((tmp_path / "data/v/unit/public/videos/vid001.json").read_text(encoding="utf-8"))
    empty_detail = json.loads((tmp_path / "data/v/unit/public/videos/vid002.json").read_text(encoding="utf-8"))
    svg_path = tmp_path / "data/v/unit/public/artifacts/wordcloud/vid001.svg"
    assert detail["chat_summary"]["wordcloud_url"] == "/data/v/unit/public/artifacts/wordcloud/vid001.svg"
    assert detail["artifacts"]["wordcloud"] == {"path": "/data/v/unit/public/artifacts/wordcloud/vid001.svg", "content_type": "image/svg+xml"}
    assert detail["timestamps"][0]["offset_sec"] == 30
    assert svg_path.exists()
    assert "ありがとう" in svg_path.read_text(encoding="utf-8")
    assert empty_detail["chat_summary"]["wordcloud_url"] is None
    assert empty_detail["artifacts"]["wordcloud"] is None
    assert not (tmp_path / "data/v/unit/public/artifacts/wordcloud/vid002.svg").exists()
    subprocess.run(["node", "tools/check-public-contract.mjs", str(tmp_path)], check=True)


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
