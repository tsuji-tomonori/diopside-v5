import json

from static_exporter.handler import export_from_fixture


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
