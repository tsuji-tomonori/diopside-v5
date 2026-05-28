from __future__ import annotations

import pathlib
import shutil
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "deploy"


def zip_dir(source: pathlib.Path, dest: pathlib.Path) -> None:
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    api_src = ROOT / "apps" / "api" / "src"
    exporter_src = ROOT / "apps" / "workers" / "static-exporter" / "src"
    zip_dir(api_src, OUT / "api.zip")
    zip_dir(exporter_src, OUT / "static-exporter.zip")
    shutil.copy2(ROOT / "infra" / "cloudformation" / "diopside.yaml", OUT / "diopside.yaml")
    print(f"deployment artifacts written to {OUT}")


if __name__ == "__main__":
    main()
