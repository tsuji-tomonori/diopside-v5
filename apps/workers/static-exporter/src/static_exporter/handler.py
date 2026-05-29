from __future__ import annotations

import json
import os
import pathlib
import shutil
import time
from typing import Any

from diopside_core import DynamoRepository, MemoryRepository, build_timestamp_candidates, generate_wordcloud_svg, now_iso

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None


def export_public_data(repository: Any, out_dir: pathlib.Path, export_version: str | None = None) -> dict[str, Any]:
    version = export_version or f"export-{int(time.time())}"
    root = out_dir
    version_root = root / "data" / "v" / version / "public"
    index_dir = version_root / "index"
    search_dir = version_root / "search"
    videos_dir = version_root / "videos"
    artifacts_dir = version_root / "artifacts" / "wordcloud"
    for directory in [index_dir, search_dir, videos_dir, artifacts_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    videos = repository.list_videos(limit=10000)
    videos.sort(key=lambda item: item.get("published_at", ""), reverse=True)
    generated_at = now_iso()
    list_items = []
    search_by_year: dict[str, list[dict[str, Any]]] = {}

    for video in videos:
        video_id = video["video_id"]
        aggregate = repository.get_chat_aggregate(video_id) or {
            "message_count": 0,
            "unique_author_count": 0,
            "paid_message_count": 0,
            "emoji_count": 0,
            "timeline_buckets": [],
            "top_terms": [],
        }
        timestamps = video.get("timestamps") or build_timestamp_candidates(aggregate, video.get("description", ""))
        wordcloud_url = None
        wordcloud_artifact = None
        if aggregate.get("top_terms"):
            wordcloud_url = f"/data/v/{version}/public/artifacts/wordcloud/{video_id}.svg"
            (artifacts_dir / f"{video_id}.svg").write_text(generate_wordcloud_svg(aggregate["top_terms"]), encoding="utf-8")
            wordcloud_artifact = {"path": wordcloud_url, "content_type": "image/svg+xml"}
            repository.put_artifact(video_id, {"artifact_type": "wordcloud", "public_url_path": wordcloud_url, "content_type": "image/svg+xml"})
        repository.put_artifact(video_id, {"artifact_type": "timestamp", "public_url_path": f"/data/v/{version}/public/videos/{video_id}.json", "content_type": "application/json"})
        detail_path = f"/data/v/{version}/public/videos/{video_id}.json"
        public_video = {
            "video_id": video_id,
            "youtube_url": video.get("youtube_url") or f"https://www.youtube.com/watch?v={video_id}",
            "title": video.get("title", ""),
            "description": video.get("description") or "",
            "published_at": video.get("published_at"),
            "live_details": {
                key: video.get(key)
                for key in ["scheduled_start_time", "actual_start_time", "actual_end_time", "live_state", "live_chat_id"]
                if video.get(key) is not None
            },
            "statistics": video.get("statistics", {}),
            "tags": video.get("tags", []),
        }
        _write_json(
            videos_dir / f"{video_id}.json",
            {
                "schema_version": "public-video-detail/v1",
                "video": public_video,
                "chat_summary": {**aggregate, "wordcloud_url": wordcloud_url},
                "artifacts": {"wordcloud": wordcloud_artifact},
                "timestamps": timestamps,
            },
        )
        item = {
            "video_id": video_id,
            "title": video.get("title", ""),
            "published_at": video.get("published_at"),
            "scheduled_start_time": video.get("scheduled_start_time"),
            "duration_sec": video.get("duration_sec"),
            "thumbnail_url": video.get("thumbnail_url"),
            "tags": video.get("tags", []),
            "detail_path": detail_path,
            "wordcloud_available": bool(wordcloud_url),
            "timestamp_available": bool(timestamps),
        }
        list_items.append(item)
        year = (video.get("published_at") or "unknown")[:4]
        search_by_year.setdefault(year, []).append({"video_id": video_id, "title": item["title"], "tags": item["tags"], "published_at": item["published_at"]})

    _write_json(index_dir / "videos-latest.json", {"schema_version": "public-video-list/v1", "generated_at": generated_at, "items": list_items})
    _write_json(index_dir / "tags.json", {"schema_version": "public-tag-list/v1", "generated_at": generated_at, "items": repository.list_tags()})
    indexes = {
        "videos_latest": f"/data/v/{version}/public/index/videos-latest.json",
        "tags": f"/data/v/{version}/public/index/tags.json",
    }
    for year, items in sorted(search_by_year.items()):
        path = search_dir / f"videos-{year}.json"
        _write_json(path, {"schema_version": "public-video-search/v1", "generated_at": generated_at, "items": items})
        indexes[f"search_{year}"] = f"/data/v/{version}/public/search/videos-{year}.json"
    manifest = {
        "schema_version": "public-manifest/v1",
        "generated_at": generated_at,
        "export_version": version,
        "base_path": f"/data/v/{version}",
        "indexes": indexes,
    }
    _write_json(root / "latest-manifest.json", manifest)
    return manifest


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
    if event.get("Records"):
        items = []
        for record in event["Records"]:
            payload = json.loads(record.get("body", "{}"))
            items.append(lambda_handler(payload, context))
        return {"status": "succeeded", "items": items}
    job_id = event.get("job_id")
    params = event.get("input", event)
    repository = _repository_from_env()
    if job_id:
        repository.append_job_event(job_id, "started", {"job_type": event.get("job_type", "static_export")})
    try:
        out = pathlib.Path(params.get("output_dir", "/tmp/diopside-public-export"))
        if params.get("fixture_source"):
            source = pathlib.Path(params["fixture_source"])
            manifest = export_from_fixture(source, out, params.get("export_version", f"local-{int(time.time())}"))
        else:
            manifest = export_public_data(repository, out, params.get("export_version"))
        uploaded = _upload_directory(out) if os.environ.get("DIOPSIDE_PUBLIC_DATA_BUCKET") else 0
        result = {
            "status": "succeeded",
            "manifest_path": str(out / "latest-manifest.json"),
            "export_version": manifest["export_version"],
            "uploaded_object_count": uploaded,
        }
        if job_id:
            repository.append_job_event(job_id, "completed", result)
        return result
    except Exception as exc:
        if job_id:
            repository.append_job_event(job_id, "failed", {"type": type(exc).__name__, "message": str(exc)})
        raise


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _repository_from_env() -> Any:
    if os.environ.get("DIOPSIDE_TABLE_NAME"):
        return DynamoRepository(os.environ["DIOPSIDE_TABLE_NAME"])
    repo = MemoryRepository()
    seed = os.environ.get("DIOPSIDE_LOCAL_EXPORT_SEED")
    if seed:
        data = json.loads(pathlib.Path(seed).read_text(encoding="utf-8"))
        for video in data.get("videos", []):
            repo.put_video(video)
        for aggregate in data.get("chat_aggregates", []):
            repo.put_chat_aggregate(aggregate["video_id"], aggregate)
    return repo


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _upload_directory(out_dir: pathlib.Path) -> int:
    if boto3 is None:
        raise RuntimeError("boto3 is required for S3 upload")
    bucket = os.environ["DIOPSIDE_PUBLIC_DATA_BUCKET"]
    prefix = os.environ.get("DIOPSIDE_PUBLIC_DATA_PREFIX", "data").strip("/")
    s3 = boto3.client("s3")
    count = 0
    manifest_path = out_dir / "latest-manifest.json"
    versioned_paths = sorted(path for path in out_dir.rglob("*") if path.is_file() and path != manifest_path)
    for path in versioned_paths:
        _upload_file(s3, bucket, prefix, out_dir, path)
        count += 1
    if manifest_path.exists():
        _upload_file(s3, bucket, prefix, out_dir, manifest_path)
        count += 1
    return count


def _upload_file(s3: Any, bucket: str, prefix: str, out_dir: pathlib.Path, path: pathlib.Path) -> None:
    rel = path.relative_to(out_dir).as_posix()
    key = f"{prefix}/{rel}" if prefix and not rel.startswith(f"{prefix}/") else rel
    s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": _content_type(path)})


def _content_type(path: pathlib.Path) -> str:
    return {
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".svg": "image/svg+xml",
    }.get(path.suffix, "application/octet-stream")
