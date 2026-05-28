import json

from diopside_core import MemoryRepository
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
    manifest = export_public_data(repo, tmp_path, "unit")
    assert manifest["indexes"]["videos_latest"] == "/data/v/unit/public/index/videos-latest.json"
    detail = json.loads((tmp_path / "data/v/unit/public/videos/vid001.json").read_text(encoding="utf-8"))
    assert detail["chat_summary"]["wordcloud_url"] == "/data/v/unit/public/artifacts/wordcloud/vid001.svg"
    assert detail["timestamps"][0]["offset_sec"] == 30
    assert (tmp_path / "data/v/unit/public/artifacts/wordcloud/vid001.svg").exists()
