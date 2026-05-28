from __future__ import annotations

import json
import os
import pathlib
import time
import uuid
from dataclasses import dataclass
from typing import Any

from diopside_core import DynamoRepository, MemoryRepository, now_iso

try:
    import boto3
except Exception:  # pragma: no cover - boto3 is available in Lambda and local dev image.
    boto3 = None


PUBLIC_DATA_DIR = pathlib.Path(os.environ.get("DIOPSIDE_PUBLIC_DATA_DIR", "data/fixtures/public"))
PUBLIC_DATA_BUCKET = os.environ.get("DIOPSIDE_PUBLIC_DATA_BUCKET", "")
PUBLIC_DATA_PREFIX = os.environ.get("DIOPSIDE_PUBLIC_DATA_PREFIX", "data").strip("/")
SERVICE = "diopside"
VERSION = os.environ.get("DIOPSIDE_VERSION", "local")
_REPOSITORY: Any | None = None


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: dict[str, Any] | None


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    trace_id = _header_map(event).get("x-trace-id") or f"trc_{uuid.uuid4().hex}"
    try:
        request = _request_from_event(event)
        result = route(request, trace_id)
        return _response(result, trace_id=trace_id)
    except ApiError as exc:
        return _response(
            {"code": exc.code, "message": exc.message, "details": exc.details, "trace_id": trace_id},
            status=exc.status,
            trace_id=trace_id,
        )
    except Exception as exc:  # pragma: no cover - defensive Lambda boundary.
        return _response(
            {"code": "INTERNAL_ERROR", "message": "想定外のエラーが発生しました。", "details": {"type": type(exc).__name__}, "trace_id": trace_id},
            status=500,
            trace_id=trace_id,
        )


def route(request: Request, trace_id: str) -> dict[str, Any]:
    if request.method == "GET" and request.path == "/api/health":
        return _health(request)
    if request.method == "GET" and request.path == "/api/config":
        return _config()
    if request.method == "GET" and request.path == "/api/home":
        return _home()
    if request.method == "GET" and request.path == "/api/videos":
        return _videos(request.query)
    if request.method == "GET" and request.path == "/api/tags":
        return _tags()
    if request.method == "GET" and request.path == "/api/random-videos":
        return _random_videos(request.query)
    if request.method == "GET" and request.path.startswith("/api/videos/"):
        parts = request.path.strip("/").split("/")
        if len(parts) == 3:
            return _video_detail(parts[2])
        if len(parts) == 4 and parts[3] == "artifacts":
            return _video_artifacts(parts[2])
    if request.path.startswith("/api/admin/"):
        _require_admin(request)
        if request.method == "GET" and request.path == "/api/admin/jobs":
            return {"schema_version": "admin-job-list/v1", "items": _repository().list_jobs(), "trace_id": trace_id}
        if request.method == "GET" and request.path.startswith("/api/admin/jobs/"):
            parts = request.path.strip("/").split("/")
            if len(parts) == 4:
                job = _repository().get_job(parts[3])
                if not job:
                    raise ApiError(404, "JOB_NOT_FOUND", "指定された job は存在しません。")
                return {"schema_version": "admin-job-detail/v1", "item": job, "trace_id": trace_id}
        if request.method == "GET" and request.path == "/api/admin/channels":
            return {"schema_version": "admin-channel-list/v1", "items": _list_channels(), "trace_id": trace_id}
        if request.method == "GET" and request.path == "/api/admin/quota-usage":
            return {"schema_version": "admin-quota-usage/v1", "items": _list_quota_usage(), "trace_id": trace_id}
        if request.method == "POST":
            return _start_job(request, trace_id)
    raise ApiError(404, "NOT_FOUND", "指定された API は存在しません。")


def _health(request: Request) -> dict[str, Any]:
    dependencies: dict[str, Any] | None = None
    if request.query.get("detail") == "true":
        dependencies = {
            "public_data": {"status": "ok" if (PUBLIC_DATA_DIR / "latest-manifest.json").exists() else "error"},
            "dynamodb": {"status": "configured" if os.environ.get("DIOPSIDE_TABLE_NAME") else "not_configured"},
            "sqs": {"status": "configured" if _queue_urls() else "not_configured"},
        }
    return {
        "service": SERVICE,
        "version": VERSION,
        "status": "ok",
        "checked_at": _now(),
        **({"dependencies": dependencies} if dependencies is not None else {}),
    }


def _config() -> dict[str, Any]:
    return {
        "schema_version": "public-config/v1",
        "system_name": SERVICE,
        "default_locale": "ja-JP",
        "public_data_manifest": "/data/latest-manifest.json",
        "admin_api_enabled": bool(os.environ.get("DIOPSIDE_ADMIN_TOKEN")),
    }


def _home() -> dict[str, Any]:
    videos = _videos({})["items"]
    tags = _tags()["items"]
    return {
        "schema_version": "public-home/v1",
        "latest_videos": videos[:12],
        "popular_tags": tags[:16],
        "updated_at": _load_json("latest-manifest.json").get("generated_at"),
    }


def _videos(query: dict[str, str]) -> dict[str, Any]:
    if os.environ.get("DIOPSIDE_TABLE_NAME"):
        items = [_public_video_item(video) for video in _repository().list_videos(limit=10000)]
        data = {"schema_version": "public-video-list/v1", "generated_at": now_iso(), "items": items}
    else:
        data = _load_manifest_index("videos_latest")
        items = data["items"]
    keyword = query.get("q", "").strip().lower()
    tag = query.get("tag", "").strip()
    if keyword:
        items = [item for item in items if keyword in f"{item['title']} {' '.join(item.get('tags', []))}".lower()]
    if tag:
        items = [item for item in items if tag in item.get("tags", [])]
    limit = min(int(query.get("limit", "50")), 100)
    return {**data, "items": items[:limit]}


def _tags() -> dict[str, Any]:
    if os.environ.get("DIOPSIDE_TABLE_NAME"):
        return {"schema_version": "public-tag-list/v1", "generated_at": now_iso(), "items": _repository().list_tags()}
    return _load_manifest_index("tags")


def _video_detail(video_id: str) -> dict[str, Any]:
    if os.environ.get("DIOPSIDE_TABLE_NAME"):
        video = _repository().get_video(video_id)
        if not video:
            raise ApiError(404, "VIDEO_NOT_FOUND", "指定された動画は公開対象に存在しません。")
        aggregate = _repository().get_chat_aggregate(video_id) or {"message_count": 0, "top_terms": []}
        artifacts = {item["artifact_type"]: item for item in _repository().list_artifacts(video_id)}
        return {
            "schema_version": "public-video-detail/v1",
            "video": {
                "video_id": video_id,
                "youtube_url": video.get("youtube_url") or f"https://www.youtube.com/watch?v={video_id}",
                "title": video.get("title", ""),
                "description": video.get("description", ""),
                "published_at": video.get("published_at"),
                "live_details": {k: video.get(k) for k in ["scheduled_start_time", "actual_start_time", "actual_end_time", "live_state"] if video.get(k) is not None},
                "statistics": video.get("statistics", {}),
                "tags": video.get("tags", []),
            },
            "chat_summary": {**aggregate, "wordcloud_url": artifacts.get("wordcloud", {}).get("public_url_path")},
            "timestamps": video.get("timestamps", []),
        }
    for item in _videos({})["items"]:
        if item.get("video_id") == video_id:
            return _load_json(str(item["detail_path"]).lstrip("/"))
    raise ApiError(404, "VIDEO_NOT_FOUND", "指定された動画は公開対象に存在しません。")


def _video_artifacts(video_id: str) -> dict[str, Any]:
    if os.environ.get("DIOPSIDE_TABLE_NAME"):
        artifacts = _repository().list_artifacts(video_id)
        if not _repository().get_video(video_id):
            raise ApiError(404, "VIDEO_NOT_FOUND", "指定された動画は公開対象に存在しません。")
        return {"schema_version": "public-video-artifacts/v1", "video_id": video_id, "items": artifacts}
    detail = _video_detail(video_id)
    chat_summary = detail.get("chat_summary", {})
    return {
        "schema_version": "public-video-artifacts/v1",
        "video_id": video_id,
        "items": [
            {
                "artifact_type": "wordcloud",
                "public_url_path": chat_summary.get("wordcloud_url"),
                "available": bool(chat_summary.get("wordcloud_url")),
            },
            {
                "artifact_type": "timestamp",
                "public_url_path": f"/data/v/dev-fixture/public/videos/{video_id}.json",
                "available": bool(detail.get("timestamps")),
            },
        ],
    }


def _random_videos(query: dict[str, str]) -> dict[str, Any]:
    items = _videos({})["items"]
    limit = min(int(query.get("limit", "3")), 12)
    offset = int(time.time()) % max(len(items), 1)
    rotated = items[offset:] + items[:offset]
    return {"schema_version": "public-random-videos/v1", "items": rotated[:limit], "generated_at": _now()}


def _start_job(request: Request, trace_id: str) -> dict[str, Any]:
    _require_csrf(request)
    job_type = _job_type_from_path(request.path)
    body = _validate_job_body(job_type, request.body or {}, request.path)
    idempotency_key = body.get("idempotency_key") or request.headers.get("x-idempotency-key")
    if not idempotency_key:
        raise ApiError(400, "INVALID_REQUEST", "idempotency_key が必要です。")
    repo = _repository()
    job, deduplicated = repo.create_job(job_type, body, idempotency_key)
    job_id = job["job_id"]
    queue_url = _queue_urls().get(job_type)
    if queue_url:
        _enqueue(queue_url, {"job_id": job_id, "job_type": job_type, "input": body, "trace_id": trace_id})
        dry_run = False
    elif os.environ.get("DIOPSIDE_ALLOW_DRY_RUN_JOBS") == "true":
        dry_run = True
    else:
        raise ApiError(503, "QUEUE_NOT_CONFIGURED", "対象 job の SQS queue が設定されていません。")
    return {
        "job_id": job_id,
        "job_type": job_type,
        "derived_state": "queued",
        "deduplicated": deduplicated,
        "accepted_at": _now(),
        "trace_id": trace_id,
        "dry_run": dry_run,
    }


def _require_admin(request: Request) -> None:
    expected = os.environ.get("DIOPSIDE_ADMIN_TOKEN")
    if not expected:
        raise ApiError(503, "ADMIN_NOT_CONFIGURED", "管理 API token が設定されていません。")
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {expected}":
        raise ApiError(401, "UNAUTHORIZED", "管理 API の認証に失敗しました。")


def _require_csrf(request: Request) -> None:
    expected = os.environ.get("DIOPSIDE_ADMIN_CSRF_TOKEN")
    if not expected:
        raise ApiError(503, "CSRF_NOT_CONFIGURED", "CSRF token が設定されていません。")
    if request.headers.get("x-csrf-token") != expected:
        raise ApiError(403, "CSRF_INVALID", "CSRF token が不正です。")


def _job_type_from_path(path: str) -> str:
    mapping = {
        "/api/admin/jobs/metadata-sync": "metadata_sync",
        "/api/admin/jobs/live-status-scan": "live_status_scan",
        "/api/admin/jobs/chat-collect": "chat_collect",
        "/api/admin/jobs/chat-normalize": "chat_normalize",
        "/api/admin/jobs/rebuild-artifacts": "rebuild_artifacts",
        "/api/admin/jobs/static-export": "static_export",
    }
    if path in mapping:
        return mapping[path]
    if path.startswith("/api/admin/jobs/") and path.endswith("/retry"):
        return "retry_job"
    if path.startswith("/api/admin/jobs/") and path.endswith("/cancel"):
        return "cancel_job"
    raise ApiError(404, "NOT_FOUND", "指定された管理 job API は存在しません。")


def _validate_job_body(job_type: str, body: dict[str, Any], path: str) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ApiError(400, "INVALID_JSON_BODY", "JSON object body が必要です。")
    validators = {
        "metadata_sync": {"channel_id", "uploads_playlist_id", "video_id", "max_results", "idempotency_key"},
        "live_status_scan": {"channel_id", "video_id", "idempotency_key"},
        "chat_collect": {"video_id", "mode", "live_chat_id", "page_token", "idempotency_key"},
        "chat_normalize": {"video_id", "idempotency_key"},
        "rebuild_artifacts": {"video_id", "idempotency_key"},
        "static_export": {"scope", "export_version", "idempotency_key"},
        "retry_job": {"reason", "idempotency_key"},
        "cancel_job": {"reason", "idempotency_key"},
    }
    unknown = set(body) - validators[job_type]
    if unknown:
        raise ApiError(400, "INVALID_REQUEST", "未対応の body field があります。", {"fields": sorted(unknown)})
    if job_type in {"chat_collect", "chat_normalize", "rebuild_artifacts"} and not body.get("video_id"):
        raise ApiError(400, "INVALID_REQUEST", "video_id が必要です。")
    if job_type in {"retry_job", "cancel_job"}:
        parts = path.strip("/").split("/")
        if len(parts) < 5:
            raise ApiError(400, "INVALID_REQUEST", "job_id が必要です。")
        body = {**body, "target_job_id": parts[3]}
    return body


def _enqueue(queue_url: str, message: dict[str, Any]) -> None:
    if boto3 is None:
        raise ApiError(503, "BOTO3_UNAVAILABLE", "boto3 が利用できません。")
    boto3.client("sqs").send_message(QueueUrl=queue_url, MessageBody=json.dumps(message, ensure_ascii=False))


def _queue_urls() -> dict[str, str]:
    return {
        "metadata_sync": os.environ.get("DIOPSIDE_METADATA_QUEUE_URL", ""),
        "live_status_scan": os.environ.get("DIOPSIDE_METADATA_QUEUE_URL", ""),
        "chat_collect": os.environ.get("DIOPSIDE_CHAT_QUEUE_URL", ""),
        "chat_normalize": os.environ.get("DIOPSIDE_NORMALIZE_QUEUE_URL", ""),
        "rebuild_artifacts": os.environ.get("DIOPSIDE_AGGREGATE_QUEUE_URL", ""),
        "static_export": os.environ.get("DIOPSIDE_STATIC_EXPORT_QUEUE_URL", ""),
        "retry_job": os.environ.get("DIOPSIDE_METADATA_QUEUE_URL", ""),
        "cancel_job": os.environ.get("DIOPSIDE_METADATA_QUEUE_URL", ""),
    }


def _request_from_event(event: dict[str, Any]) -> Request:
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "GET")
    path = event.get("rawPath") or event.get("path") or "/"
    raw_body = event.get("body")
    try:
        body = json.loads(raw_body) if raw_body else None
    except json.JSONDecodeError as exc:
        raise ApiError(400, "INVALID_JSON_BODY", "JSON body を解析できません。", {"error": str(exc)}) from exc
    return Request(
        method=method.upper(),
        path=path,
        query={k: str(v) for k, v in (event.get("queryStringParameters") or {}).items()},
        headers=_header_map(event),
        body=body,
    )


def _header_map(event: dict[str, Any]) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in (event.get("headers") or {}).items()}


def _load_manifest_index(name: str) -> dict[str, Any]:
    manifest = _load_json("latest-manifest.json")
    index_path = manifest["indexes"][name].lstrip("/")
    return _load_json(index_path)


def _load_json(relative_path: str) -> dict[str, Any]:
    path = PUBLIC_DATA_DIR / relative_path
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if PUBLIC_DATA_BUCKET:
        return _load_json_from_s3(relative_path)
    raise ApiError(503, "PUBLIC_DATA_MISSING", f"公開データが見つかりません: {relative_path}")


def _repository() -> Any:
    global _REPOSITORY
    if _REPOSITORY is not None:
        return _REPOSITORY
    if os.environ.get("DIOPSIDE_TABLE_NAME"):
        _REPOSITORY = DynamoRepository(os.environ["DIOPSIDE_TABLE_NAME"])
    else:
        _REPOSITORY = MemoryRepository()
    return _REPOSITORY


def _public_video_item(video: dict[str, Any]) -> dict[str, Any]:
    video_id = video["video_id"]
    return {
        "video_id": video_id,
        "title": video.get("title", ""),
        "published_at": video.get("published_at"),
        "scheduled_start_time": video.get("scheduled_start_time"),
        "duration_sec": video.get("duration_sec"),
        "thumbnail_url": video.get("thumbnail_url"),
        "tags": video.get("tags", []),
        "detail_path": f"/api/videos/{video_id}",
        "wordcloud_available": any(item.get("artifact_type") == "wordcloud" for item in _repository().list_artifacts(video_id)),
        "timestamp_available": bool(video.get("timestamps")),
    }


def _list_channels() -> list[dict[str, Any]]:
    repo = _repository()
    items = getattr(repo, "items", {}).values() if hasattr(repo, "items") else []
    return [item for item in items if item.get("item_type") == "Channel"]


def _list_quota_usage() -> list[dict[str, Any]]:
    repo = _repository()
    items = getattr(repo, "items", {}).values() if hasattr(repo, "items") else []
    usage = [item for item in items if item.get("item_type") == "QuotaUsage"]
    usage.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return usage[:100]


def _load_json_from_s3(relative_path: str) -> dict[str, Any]:
    if boto3 is None:
        raise ApiError(503, "BOTO3_UNAVAILABLE", "boto3 が利用できません。")
    key = _public_data_key(relative_path)
    try:
        body = boto3.client("s3").get_object(Bucket=PUBLIC_DATA_BUCKET, Key=key)["Body"].read()
        return json.loads(body.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - exercised in AWS.
        raise ApiError(503, "PUBLIC_DATA_MISSING", f"S3 公開データを読み込めません: {key}", {"type": type(exc).__name__}) from exc


def _public_data_key(relative_path: str) -> str:
    rel = relative_path.lstrip("/")
    if rel.startswith(f"{PUBLIC_DATA_PREFIX}/"):
        return rel
    return f"{PUBLIC_DATA_PREFIX}/{rel}" if PUBLIC_DATA_PREFIX else rel


def _response(payload: dict[str, Any], status: int = 200, trace_id: str = "") -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": "no-store, no-cache, max-age=0",
            "x-trace-id": trace_id,
        },
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
