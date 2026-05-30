from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "deploy"
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def should_package_file(path: pathlib.Path) -> bool:
    return not (EXCLUDED_DIRS.intersection(path.parts) or path.suffix in EXCLUDED_SUFFIXES)


def zip_dir(source: pathlib.Path, dest: pathlib.Path, extra_sources: list[pathlib.Path] | None = None) -> None:
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root in [source, *(extra_sources or [])]:
            for path in root.rglob("*"):
                if path.is_file() and should_package_file(path):
                    zf.write(path, path.relative_to(root))


def install_requirements(requirements: pathlib.Path, target: pathlib.Path) -> None:
    if not requirements.exists():
        return
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-compile",
            "--target",
            str(target),
            "-r",
            str(requirements),
        ],
        check=True,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    api_src = ROOT / "apps" / "api" / "src"
    exporter_src = ROOT / "apps" / "workers" / "static-exporter" / "src"
    shared_src = ROOT / "apps" / "shared" / "src"
    with tempfile.TemporaryDirectory() as tmp:
        api_deps = pathlib.Path(tmp) / "api-deps"
        install_requirements(ROOT / "requirements-api.txt", api_deps)
        zip_dir(api_src, OUT / "api.zip", [shared_src, api_deps])
    zip_dir(exporter_src, OUT / "static-exporter.zip", [shared_src])
    shutil.copy2(ROOT / "infra" / "cloudformation" / "diopside.yaml", OUT / "diopside.yaml")
    print(f"deployment artifacts written to {OUT}")


if __name__ == "__main__":
    main()
