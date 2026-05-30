from __future__ import annotations

import json
import os
import pathlib
import shutil
import time
import hashlib
from typing import Any

from diopside_core import DynamoRepository, MemoryRepository, build_timestamp_candidates, generate_chapters_suggestion_markdown, generate_wordcloud_png, generate_wordcloud_svg, now_iso

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None


def export_public_data(repository: Any, out_dir: pathlib.Path, export_version: str | None = None) -> dict[str, Any]:
    version = export_version or f"export-{int(time.time())}"
    root = out_dir
    version_root = root / "data" / "v" / version / "public"
    alias_root = root / "data"
    index_dir = version_root / "index"
    search_dir = version_root / "search"
    videos_dir = version_root / "videos"
    calendar_dir = version_root / "calendar"
    artifacts_dir = version_root / "artifacts" / "wordcloud"
    timestamps_dir = version_root / "artifacts" / "timestamps"
    alias_videos_dir = alias_root / "videos"
    alias_calendar_dir = alias_root / "calendar"
    alias_wordcloud_dir = alias_root / "artifacts" / "wordcloud"
    alias_timestamps_dir = alias_root / "artifacts" / "timestamps"
    for directory in [index_dir, search_dir, videos_dir, calendar_dir, artifacts_dir, timestamps_dir, alias_videos_dir, alias_calendar_dir, alias_wordcloud_dir, alias_timestamps_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    videos = repository.list_videos(limit=10000)
    videos.sort(key=lambda item: item.get("published_at", ""), reverse=True)
    generated_at = now_iso()
    list_items = []
    alias_list_items = []
    search_by_year: dict[str, list[dict[str, Any]]] = {}
    calendar_by_year_month: dict[str, dict[str, list[dict[str, Any]]]] = {}
    alias_detail_paths: dict[str, str] = {}
    static_detail_entries: dict[str, dict[str, str]] = {}
    static_calendar_entries: dict[str, dict[str, str]] = {}
    static_wordcloud_entries: dict[str, dict[str, str]] = {}
    static_wordcloud_png_entries: dict[str, dict[str, str]] = {}
    static_timestamp_entries: dict[str, dict[str, str]] = {}
    static_timestamp_chapter_entries: dict[str, dict[str, str]] = {}

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
        wordcloud_json_url = None
        wordcloud_artifact = None
        wordcloud_svg_artifact = None
        wordcloud_json_artifact = None
        if aggregate.get("top_terms"):
            versioned_wordcloud_png_path = f"/data/v/{version}/public/artifacts/wordcloud/{video_id}.png"
            alias_wordcloud_png_path = f"/data/artifacts/wordcloud/{video_id}.png"
            wordcloud_url = alias_wordcloud_png_path
            wordcloud_png = generate_wordcloud_png(aggregate["top_terms"])
            _write_public_bytes(root, versioned_wordcloud_png_path, wordcloud_png)
            _write_public_bytes(root, alias_wordcloud_png_path, wordcloud_png)
            wordcloud_artifact = {"path": alias_wordcloud_png_path, "versioned_path": versioned_wordcloud_png_path, "content_type": "image/png"}
            repository.put_artifact(video_id, {"artifact_type": "wordcloud", "public_url_path": wordcloud_url, "content_type": "image/png"})
            wordcloud_svg_url = f"/data/v/{version}/public/artifacts/wordcloud/{video_id}.svg"
            (artifacts_dir / f"{video_id}.svg").write_text(generate_wordcloud_svg(aggregate["top_terms"]), encoding="utf-8")
            wordcloud_svg_artifact = {"path": wordcloud_svg_url, "content_type": "image/svg+xml"}
            versioned_wordcloud_json_path = f"/data/v/{version}/public/artifacts/wordcloud/{video_id}.json"
            alias_wordcloud_json_path = f"/data/artifacts/wordcloud/{video_id}.json"
            wordcloud_json_payload = {
                "schema_version": "public-wordcloud/v1",
                "video_id": video_id,
                "generated_at": generated_at,
                "top_terms": aggregate.get("top_terms", []),
                "message_count": aggregate.get("message_count", 0),
                "source_png_path": alias_wordcloud_png_path,
                "source_svg_path": wordcloud_svg_url,
            }
            _write_public_json(root, versioned_wordcloud_json_path, wordcloud_json_payload)
            _write_public_json(root, alias_wordcloud_json_path, wordcloud_json_payload)
            wordcloud_json_url = alias_wordcloud_json_path
            wordcloud_json_artifact = {"path": alias_wordcloud_json_path, "versioned_path": versioned_wordcloud_json_path, "content_type": "application/json"}
            static_wordcloud_entries[video_id] = _static_entry(root, alias_wordcloud_json_path, versioned_wordcloud_json_path)
            static_wordcloud_png_entries[video_id] = _static_entry(root, alias_wordcloud_png_path, versioned_wordcloud_png_path)
        versioned_timestamp_path = f"/data/v/{version}/public/artifacts/timestamps/{video_id}.json"
        alias_timestamp_path = f"/data/artifacts/timestamps/{video_id}.json"
        versioned_chapters_path = f"/data/v/{version}/public/artifacts/timestamps/{video_id}.md"
        alias_chapters_path = f"/data/artifacts/timestamps/{video_id}.md"
        timestamp_payload = {
            "schema_version": "public-timestamp-list/v1",
            "video_id": video_id,
            "generated_at": generated_at,
            "items": timestamps,
        }
        _write_public_json(root, versioned_timestamp_path, timestamp_payload)
        _write_public_json(root, alias_timestamp_path, timestamp_payload)
        chapters_suggestion = generate_chapters_suggestion_markdown(video_id, timestamps).encode("utf-8")
        _write_public_bytes(root, versioned_chapters_path, chapters_suggestion)
        _write_public_bytes(root, alias_chapters_path, chapters_suggestion)
        static_timestamp_entries[video_id] = _static_entry(root, alias_timestamp_path, versioned_timestamp_path)
        static_timestamp_chapter_entries[video_id] = _static_entry(root, alias_chapters_path, versioned_chapters_path)
        repository.put_artifact(video_id, {"artifact_type": "timestamp", "public_url_path": alias_timestamp_path, "content_type": "application/json"})
        repository.put_artifact(video_id, {"artifact_type": "timestamp_chapters", "public_url_path": alias_chapters_path, "content_type": "text/markdown; charset=utf-8", "byte_size": len(chapters_suggestion)})
        detail_path = f"/data/v/{version}/public/videos/{video_id}.json"
        alias_detail_path = f"/data/videos/{video_id}.json"
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
        detail_payload = {
            "schema_version": "public-video-detail/v1",
            "video": public_video,
            "chat_summary": {**aggregate, "wordcloud_url": wordcloud_url, "wordcloud_json_url": wordcloud_json_url},
            "artifacts": {"wordcloud": wordcloud_artifact, "wordcloud_svg": wordcloud_svg_artifact, "wordcloud_json": wordcloud_json_artifact, "timestamps": {"path": alias_timestamp_path, "versioned_path": versioned_timestamp_path, "content_type": "application/json"}, "timestamp_chapters": {"path": alias_chapters_path, "versioned_path": versioned_chapters_path, "content_type": "text/markdown; charset=utf-8"}},
            "timestamps": timestamps,
        }
        _write_public_json(root, detail_path, detail_payload)
        _write_public_json(
            root,
            alias_detail_path,
            {
                **detail_payload,
                "chat_summary": {**detail_payload["chat_summary"], "wordcloud_json_url": wordcloud_json_url},
            },
        )
        static_detail_entries[video_id] = _static_entry(root, alias_detail_path, detail_path)
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
        alias_item = {**item, "detail_path": alias_detail_path, "timestamp_path": alias_timestamp_path, **({"wordcloud_path": wordcloud_url, "wordcloud_json_path": wordcloud_json_url} if wordcloud_json_url else {})}
        list_items.append(item)
        alias_list_items.append(alias_item)
        alias_detail_paths[video_id] = alias_detail_path
        year = (video.get("published_at") or "unknown")[:4]
        month = (video.get("published_at") or "unknown-00")[5:7] if year != "unknown" else "unknown"
        search_by_year.setdefault(year, []).append({"video_id": video_id, "title": item["title"], "tags": item["tags"], "published_at": item["published_at"]})
        calendar_by_year_month.setdefault(year, {}).setdefault(month, []).append(
            {
                "video_id": video_id,
                "title": item["title"],
                "published_at": item["published_at"],
                "detail_path": alias_detail_path,
                "tags": item["tags"],
            }
        )

    _write_json(index_dir / "videos-latest.json", {"schema_version": "public-video-list/v1", "generated_at": generated_at, "items": list_items})
    _write_json(alias_videos_dir / "index.json", {"schema_version": "public-video-list/v1", "generated_at": generated_at, "items": alias_list_items})
    tags_payload = {"schema_version": "public-tag-list/v1", "generated_at": generated_at, "items": repository.list_tags()}
    _write_json(index_dir / "tags.json", tags_payload)
    _write_json(alias_root / "tags.json", tags_payload)
    home_payload = {
        "schema_version": "public-home/v1",
        "generated_at": generated_at,
        "latest_videos": alias_list_items[:12],
        "popular_tags": tags_payload["items"][:16],
        "live_videos": [item for item in alias_list_items if item.get("live_state") == "live"],
        "upcoming_videos": [item for item in alias_list_items if item.get("live_state") == "upcoming"],
    }
    versioned_home_path = f"/data/v/{version}/public/home.json"
    _write_public_json(root, versioned_home_path, home_payload)
    _write_json(alias_root / "home.json", home_payload)
    indexes = {
        "videos_latest": f"/data/v/{version}/public/index/videos-latest.json",
        "tags": f"/data/v/{version}/public/index/tags.json",
    }
    for year, items in sorted(search_by_year.items()):
        path = search_dir / f"videos-{year}.json"
        _write_json(path, {"schema_version": "public-video-search/v1", "generated_at": generated_at, "items": items})
        indexes[f"search_{year}"] = f"/data/v/{version}/public/search/videos-{year}.json"
    calendar_indexes = repository.list_video_month_indexes() if hasattr(repository, "list_video_month_indexes") else []
    if calendar_indexes:
        calendar_by_year_month = {}
        for item in calendar_indexes:
            published_at = str(item.get("published_at") or "")
            video_id = item.get("video_id")
            if len(published_at) < 7 or not video_id or video_id not in alias_detail_paths:
                continue
            year = published_at[:4]
            month = published_at[5:7]
            calendar_by_year_month.setdefault(year, {}).setdefault(month, []).append(
                {
                    "video_id": video_id,
                    "title": item.get("title", ""),
                    "published_at": item.get("published_at"),
                    "detail_path": alias_detail_paths[video_id],
                    "tags": item.get("tags", []),
                }
            )
    for year, months in sorted(calendar_by_year_month.items()):
        items = [
            {"month": month, "video_count": len(month_items), "items": month_items}
            for month, month_items in sorted(months.items(), reverse=True)
        ]
        calendar_payload = {
            "schema_version": "public-archive-calendar/v1",
            "generated_at": generated_at,
            "year": year,
            "months": items,
        }
        versioned_calendar_path = f"/data/v/{version}/public/calendar/{year}.json"
        alias_calendar_path = f"/data/calendar/{year}.json"
        _write_public_json(root, versioned_calendar_path, calendar_payload)
        _write_public_json(root, alias_calendar_path, calendar_payload)
        static_calendar_entries[year] = _static_entry(root, alias_calendar_path, versioned_calendar_path)
    manifest = {
        "schema_version": "public-manifest/v1",
        "generated_at": generated_at,
        "export_version": version,
        "base_path": f"/data/v/{version}",
        "indexes": indexes,
        "static_paths": {
            "STATIC-001": _static_entry(root, "/data/home.json", versioned_home_path),
            "STATIC-002": _static_entry(root, "/data/videos/index.json", f"/data/v/{version}/public/index/videos-latest.json"),
            "STATIC-003": {"path_pattern": "/data/videos/{video_id}.json", "items": static_detail_entries},
            "STATIC-004": _static_entry(root, "/data/tags.json", f"/data/v/{version}/public/index/tags.json"),
            "STATIC-005": {"path_pattern": "/data/calendar/{year}.json", "items": static_calendar_entries},
            "STATIC-006": {"path": "/data/latest-manifest.json", "versioned_path": None, "checksum_sha256": None},
            "STATIC-007": {"path_pattern": "/data/artifacts/wordcloud/{video_id}.{png|json}", "items": static_wordcloud_entries, "image_items": static_wordcloud_png_entries},
            "STATIC-008": {"path_pattern": "/data/artifacts/timestamps/{video_id}.json", "items": static_timestamp_entries, "chapter_path_pattern": "/data/artifacts/timestamps/{video_id}.md", "chapter_items": static_timestamp_chapter_entries},
        },
    }
    manifest["static_paths"]["STATIC-006"]["checksum_sha256"] = _manifest_payload_checksum(manifest)
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
    source_version = manifest["export_version"]
    source_public_dir = out_dir / "data" / "v" / source_version / "public"
    target_public_dir = out_dir / "data" / "v" / export_version / "public"
    if source_version != export_version and source_public_dir.exists():
        target_public_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_public_dir.exists():
            shutil.rmtree(target_public_dir)
        shutil.move(str(source_public_dir), str(target_public_dir))
        source_version_dir = out_dir / "data" / "v" / source_version
        if source_version_dir.exists() and not any(source_version_dir.iterdir()):
            source_version_dir.rmdir()
    old_prefix = f"/data/v/{source_version}/"
    new_prefix = f"/data/v/{export_version}/"
    manifest["generated_at"] = _now()
    manifest["export_version"] = export_version
    manifest["base_path"] = f"/data/v/{export_version}"
    manifest["indexes"] = {key: value.replace(old_prefix, new_prefix, 1) for key, value in manifest["indexes"].items()}
    _replace_manifest_static_prefix(manifest, old_prefix, new_prefix)
    for path in out_dir.rglob("*.json"):
        path.write_text(path.read_text(encoding="utf-8").replace(old_prefix, new_prefix), encoding="utf-8")
    _refresh_manifest_checksums(out_dir, manifest)
    manifest["static_paths"]["STATIC-006"]["checksum_sha256"] = _manifest_payload_checksum(manifest)
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
        repository.record_static_export(
            manifest,
            reason=params.get("reason", "manual"),
            manifest_s3_uri=_manifest_s3_uri(),
            public_prefix=_public_data_prefix(manifest["export_version"]),
            generated_job_id=job_id,
            uploaded_object_count=uploaded,
            tag_count=_export_tag_count(out),
        )
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


def _manifest_s3_uri() -> str:
    bucket = os.environ.get("DIOPSIDE_PUBLIC_DATA_BUCKET")
    if not bucket:
        return "local://latest-manifest.json"
    prefix = os.environ.get("DIOPSIDE_PUBLIC_DATA_PREFIX", "data").strip("/")
    key = f"{prefix}/latest-manifest.json" if prefix else "latest-manifest.json"
    return f"s3://{bucket}/{key}"


def _public_data_prefix(export_version: str) -> str:
    prefix = os.environ.get("DIOPSIDE_PUBLIC_DATA_PREFIX", "data").strip("/")
    base = f"data/v/{export_version}/public"
    return f"{prefix}/{base}" if prefix and prefix != "data" else base


def _export_tag_count(out_dir: pathlib.Path) -> int:
    path = out_dir / "data" / "tags.json"
    if not path.exists():
        return 0
    return len(json.loads(path.read_text(encoding="utf-8")).get("items", []))


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


def _write_public_json(root: pathlib.Path, public_path: str, payload: dict[str, Any]) -> None:
    _write_json(_public_path_to_file(root, public_path), payload)


def _write_public_bytes(root: pathlib.Path, public_path: str, payload: bytes) -> None:
    path = _public_path_to_file(root, public_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _public_path_to_file(root: pathlib.Path, public_path: str) -> pathlib.Path:
    normalized = public_path.lstrip("/")
    return root / normalized


def _static_entry(root: pathlib.Path, alias_path: str, versioned_path: str | None) -> dict[str, str | None]:
    return {
        "path": alias_path,
        "versioned_path": versioned_path,
        "checksum_sha256": _sha256_file(_public_path_to_file(root, alias_path)),
    }


def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_payload_checksum(manifest: dict[str, Any]) -> str:
    payload = json.loads(json.dumps(manifest, ensure_ascii=False))
    payload.get("static_paths", {}).get("STATIC-006", {})["checksum_sha256"] = None
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _replace_manifest_static_prefix(manifest: dict[str, Any], old_prefix: str, new_prefix: str) -> None:
    def replace(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(old_prefix, new_prefix, 1)
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    manifest["static_paths"] = replace(manifest.get("static_paths", {}))


def _refresh_manifest_checksums(root: pathlib.Path, manifest: dict[str, Any]) -> None:
    def refresh_entry(entry: dict[str, Any]) -> None:
        path = entry.get("path")
        if path and path != "/data/latest-manifest.json":
            entry["checksum_sha256"] = _sha256_file(_public_path_to_file(root, path))

    for value in manifest.get("static_paths", {}).values():
        if isinstance(value, dict) and "items" in value:
            for entry in value["items"].values():
                refresh_entry(entry)
            for entry in value.get("image_items", {}).values():
                refresh_entry(entry)
        elif isinstance(value, dict):
            refresh_entry(value)


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
