from __future__ import annotations

import json
import os
import pathlib
import shutil
import time
from typing import Any

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None


def export_from_fixture(source_dir: pathlib.Path, out_dir: pathlib.Path, export_version: str = "local") -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.exists():
        for child in out_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    shutil.copytree(source_dir, out_dir, dirs_exist_ok=True)
    manifest_path = out_dir / "latest-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generated_at"] = _now()
    manifest["export_version"] = export_version
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # The deployable worker boundary is in place; production data loading from
    # DynamoDB/S3 is intentionally implemented behind a later repository adapter.
    source = pathlib.Path(event.get("fixture_source", "data/fixtures/public"))
    out = pathlib.Path(event.get("output_dir", "/tmp/diopside-public-export"))
    manifest = export_from_fixture(source, out, event.get("export_version", f"lambda-{int(time.time())}"))
    uploaded = _upload_directory(out) if os.environ.get("DIOPSIDE_PUBLIC_DATA_BUCKET") else 0
    return {
        "status": "succeeded",
        "manifest_path": str(out / "latest-manifest.json"),
        "export_version": manifest["export_version"],
        "uploaded_object_count": uploaded,
    }


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _upload_directory(out_dir: pathlib.Path) -> int:
    if boto3 is None:
        raise RuntimeError("boto3 is required for S3 upload")
    bucket = os.environ["DIOPSIDE_PUBLIC_DATA_BUCKET"]
    prefix = os.environ.get("DIOPSIDE_PUBLIC_DATA_PREFIX", "data").strip("/")
    s3 = boto3.client("s3")
    count = 0
    for path in out_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(out_dir).as_posix()
            key = f"{prefix}/{rel}" if prefix and not rel.startswith(f"{prefix}/") else rel
            s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": _content_type(path)})
            count += 1
    return count


def _content_type(path: pathlib.Path) -> str:
    return {
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".svg": "image/svg+xml",
    }.get(path.suffix, "application/octet-stream")
