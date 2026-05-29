import zipfile

import tools.package_deploy as package_deploy


def zip_names(path):
    with zipfile.ZipFile(path) as zf:
        return set(zf.namelist())


def assert_no_cache_entries(names):
    assert not any("__pycache__" in name.split("/") for name in names)
    assert not any(".pytest_cache" in name.split("/") for name in names)
    assert not any(".mypy_cache" in name.split("/") for name in names)
    assert not any(".ruff_cache" in name.split("/") for name in names)
    assert not any(name.endswith((".pyc", ".pyo")) for name in names)


def test_package_deploy_includes_shared_code_without_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(package_deploy, "OUT", tmp_path)

    package_deploy.main()

    api_names = zip_names(tmp_path / "api.zip")
    exporter_names = zip_names(tmp_path / "static-exporter.zip")

    assert "diopside_api/handler.py" in api_names
    assert "diopside_core/__init__.py" in api_names
    assert "diopside_core/repository.py" in api_names
    assert "static_exporter/handler.py" in exporter_names
    assert "static_exporter/pipeline.py" in exporter_names
    assert "diopside_core/__init__.py" in exporter_names
    assert "diopside_core/repository.py" in exporter_names
    assert (tmp_path / "diopside.yaml").exists()
    assert_no_cache_entries(api_names)
    assert_no_cache_entries(exporter_names)


def test_zip_dir_excludes_common_python_cache_entries(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "module.cpython-313.pyc").write_bytes(b"cache")
    (source / ".pytest_cache" / "v" / "cache").mkdir(parents=True)
    (source / ".pytest_cache" / "v" / "cache" / "nodeids").write_text("[]\n", encoding="utf-8")
    (source / ".ruff_cache").mkdir()
    (source / ".ruff_cache" / "file").write_text("cache\n", encoding="utf-8")
    dest = tmp_path / "artifact.zip"

    package_deploy.zip_dir(source, dest)

    assert zip_names(dest) == {"module.py"}
