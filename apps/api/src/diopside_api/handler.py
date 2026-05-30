from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import pathlib
import secrets
import time
import uuid
from dataclasses import dataclass
from http.cookies import CookieError, SimpleCookie
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
ADMIN_SESSION_COOKIE = "diopside_admin_session"
ADMIN_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: dict[str, Any] | None


@dataclass(frozen=True)
class AdminAuth:
    mode: str
    csrf_token: str | None = None
    expires_at: int | None = None


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    started = time.perf_counter()
    trace_id = _header_map(event).get("x-trace-id") or f"trc_{uuid.uuid4().hex}"
    request: Request | None = None
    try:
        request = _request_from_event(event)
        result = route(request, trace_id)
        response = _response(result, trace_id=trace_id)
        _log_api_request(event, request, response, started, trace_id, result=result)
        return response
    except ApiError as exc:
        response = _response(
            {"code": exc.code, "message": exc.message, "details": exc.details, "trace_id": trace_id},
            status=exc.status,
            trace_id=trace_id,
        )
        _log_api_request(event, request, response, started, trace_id, error={"type": "ApiError", "code": exc.code, "message": exc.message})
        return response
    except Exception as exc:  # pragma: no cover - defensive Lambda boundary.
        response = _response(
            {"code": "INTERNAL_ERROR", "message": "想定外のエラーが発生しました。", "details": {"type": type(exc).__name__}, "trace_id": trace_id},
            status=500,
            trace_id=trace_id,
        )
        _log_api_request(event, request, response, started, trace_id, error={"type": type(exc).__name__, "message": str(exc)})
        return response


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
    if request.method == "GET" and request.path == "/api/archive-calendar":
        return _archive_calendar(request.query)
    if request.method == "GET" and request.path == "/api/random-videos":
        return _random_videos(request.query)
    if request.method == "GET" and request.path.startswith("/api/videos/"):
        parts = request.path.strip("/").split("/")
        if len(parts) == 3:
            return _video_detail(parts[2])
        if len(parts) == 4 and parts[3] == "artifacts":
            return _video_artifacts(parts[2])
    if request.method == "POST" and request.path == "/api/admin/session":
        return _create_admin_session(request.body or {}, trace_id)
    if request.path.startswith("/api/admin/"):
        admin_auth = _require_admin(request)
        if request.method == "GET" and request.path == "/api/admin/me":
            return _admin_me(admin_auth, trace_id)
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
        if request.method == "PUT" and request.path.startswith("/api/admin/channels/"):
            _require_csrf(request, admin_auth)
            parts = request.path.strip("/").split("/")
            if len(parts) != 4:
                raise ApiError(404, "NOT_FOUND", "指定された channel API は存在しません。")
            return _update_channel(parts[3], request.body or {}, trace_id)
        if request.method == "POST" and request.path == "/api/admin/artifacts/presigned-url":
            _require_csrf(request, admin_auth)
            return _issue_artifact_presigned_url(request.body or {}, trace_id)
        if request.method == "POST":
            return _start_job(request, trace_id, admin_auth)
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
    updated_at = now_iso()
    if not os.environ.get("DIOPSIDE_TABLE_NAME"):
        updated_at = _load_json("latest-manifest.json").get("generated_at")
    return {
        "schema_version": "public-home/v1",
        "latest_videos": videos[:12],
        "popular_tags": tags[:16],
        "updated_at": updated_at,
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


def _archive_calendar(query: dict[str, str]) -> dict[str, Any]:
    year_filter = _optional_int_query(query, "year", minimum=1970, maximum=9999)
    month_filter = _optional_int_query(query, "month", minimum=1, maximum=12)
    if month_filter is not None and year_filter is None:
        raise ApiError(400, "INVALID_REQUEST", "month を指定する場合は year も必要です。")
    videos = _calendar_video_items()
    years: dict[str, int] = {}
    months: dict[tuple[str, str], int] = {}
    days: dict[str, list[str]] = {}
    for video in videos:
        published_at = str(video.get("published_at") or "")
        if len(published_at) < 10:
            continue
        year = published_at[:4]
        month = published_at[5:7]
        day = published_at[:10]
        if year_filter is not None and year != f"{year_filter:04d}":
            continue
        if month_filter is not None and month != f"{month_filter:02d}":
            continue
        years[year] = years.get(year, 0) + 1
        months[(year, month)] = months.get((year, month), 0) + 1
        days.setdefault(day, []).append(video["video_id"])
    return {
        "schema_version": "public-archive-calendar/v1",
        "generated_at": _now(),
        "years": [{"year": int(year), "video_count": count} for year, count in sorted(years.items(), reverse=True)],
        "months": [
            {"year": int(year), "month": int(month), "video_count": count}
            for (year, month), count in sorted(months.items(), reverse=True)
        ],
        **(
            {
                "days": [
                    {"date": day, "video_count": len(video_ids), "video_ids": sorted(video_ids)}
                    for day, video_ids in sorted(days.items(), reverse=True)
                ]
            }
            if month_filter is not None
            else {}
        ),
    }


def _calendar_video_items() -> list[dict[str, Any]]:
    if os.environ.get("DIOPSIDE_TABLE_NAME"):
        return [
            {"video_id": video["video_id"], "published_at": video.get("published_at")}
            for video in _repository().list_videos(limit=10000)
            if video.get("video_id")
        ]
    return [
        {"video_id": item["video_id"], "published_at": item.get("published_at")}
        for item in _load_manifest_index("videos_latest").get("items", [])
        if item.get("video_id")
    ]


def _optional_int_query(query: dict[str, str], name: str, *, minimum: int, maximum: int) -> int | None:
    raw = query.get(name)
    if raw in {None, ""}:
        return None
    try:
        value = int(str(raw))
    except ValueError as exc:
        raise ApiError(400, "INVALID_REQUEST", f"{name} は整数で指定してください。") from exc
    if value < minimum or value > maximum:
        raise ApiError(400, "INVALID_REQUEST", f"{name} は {minimum} から {maximum} の範囲で指定してください。")
    return value


def _update_channel(channel_id: str, body: dict[str, Any], trace_id: str) -> dict[str, Any]:
    if not channel_id:
        raise ApiError(400, "INVALID_REQUEST", "channel_id が必要です。")
    if not isinstance(body, dict):
        raise ApiError(400, "INVALID_JSON_BODY", "JSON object body が必要です。")
    allowed = {"enabled", "uploads_playlist_id", "display_name", "metadata_interval_minutes", "live_scan_interval_minutes", "notification_enabled"}
    unknown = set(body) - allowed
    if unknown:
        raise ApiError(400, "INVALID_REQUEST", "未対応の body field があります。", {"fields": sorted(unknown)})
    required = {"enabled", "metadata_interval_minutes", "live_scan_interval_minutes", "notification_enabled"}
    missing = sorted(key for key in required if key not in body)
    if missing:
        raise ApiError(400, "INVALID_REQUEST", "必須 field が不足しています。", {"fields": missing})
    for key in ["enabled", "notification_enabled"]:
        if not isinstance(body.get(key), bool):
            raise ApiError(400, "INVALID_REQUEST", f"{key} は boolean で指定してください。")
    for key in ["metadata_interval_minutes", "live_scan_interval_minutes"]:
        if not isinstance(body.get(key), int) or body[key] <= 0 or body[key] > 1440:
            raise ApiError(400, "INVALID_REQUEST", f"{key} は 1 から 1440 の整数で指定してください。")
    for key in ["uploads_playlist_id", "display_name"]:
        if key in body and body[key] is not None and not isinstance(body[key], str):
            raise ApiError(400, "INVALID_REQUEST", f"{key} は string で指定してください。")
    item = _repository().put_channel(
        {
            "channel_id": channel_id,
            "enabled": body["enabled"],
            "uploads_playlist_id": body.get("uploads_playlist_id"),
            "display_name": body.get("display_name"),
            "metadata_interval_minutes": body["metadata_interval_minutes"],
            "live_scan_interval_minutes": body["live_scan_interval_minutes"],
            "notification_enabled": body["notification_enabled"],
        }
    )
    return {"schema_version": "admin-channel-config/v1", "item": _channel_response(item), "trace_id": trace_id}


def _issue_artifact_presigned_url(body: dict[str, Any], trace_id: str) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ApiError(400, "INVALID_JSON_BODY", "JSON object body が必要です。")
    allowed = {"artifact_id", "purpose", "expires_in_seconds"}
    unknown = set(body) - allowed
    if unknown:
        raise ApiError(400, "INVALID_REQUEST", "未対応の body field があります。", {"fields": sorted(unknown)})
    artifact_id = body.get("artifact_id")
    purpose = body.get("purpose")
    if not isinstance(artifact_id, str) or not artifact_id:
        raise ApiError(400, "INVALID_REQUEST", "artifact_id が必要です。")
    if purpose not in {"download", "inspect"}:
        raise ApiError(400, "INVALID_REQUEST", "purpose は download または inspect を指定してください。")
    expires = body.get("expires_in_seconds", 300)
    if not isinstance(expires, int) or expires < 1 or expires > 900:
        raise ApiError(400, "INVALID_REQUEST", "expires_in_seconds は 1 から 900 の整数で指定してください。")
    artifact = _repository().get_artifact_by_id(artifact_id)
    if not artifact:
        raise ApiError(404, "ARTIFACT_NOT_FOUND", "指定された artifact は存在しません。")
    s3_uri = artifact.get("s3_uri") or artifact.get("private_s3_uri")
    bucket, key = _private_artifact_s3_location(s3_uri)
    if boto3 is None:
        raise ApiError(503, "BOTO3_UNAVAILABLE", "boto3 が利用できません。")
    url = boto3.client("s3").generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires)
    return {
        "schema_version": "admin-artifact-presigned-url/v1",
        "artifact_id": artifact_id,
        "purpose": purpose,
        "url": url,
        "expires_at": _iso_after_seconds(expires),
        "trace_id": trace_id,
    }


def _start_job(request: Request, trace_id: str, admin_auth: AdminAuth) -> dict[str, Any]:
    _require_csrf(request, admin_auth)
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


def _create_admin_session(body: dict[str, Any], trace_id: str) -> dict[str, Any]:
    expected = os.environ.get("DIOPSIDE_ADMIN_TOKEN")
    if not expected:
        raise ApiError(503, "ADMIN_NOT_CONFIGURED", "管理 API token が設定されていません。")
    if not isinstance(body, dict):
        raise ApiError(400, "INVALID_JSON_BODY", "JSON object body が必要です。")
    passphrase = str(body.get("passphrase") or body.get("token") or "")
    if not hmac.compare_digest(passphrase, expected):
        raise ApiError(401, "UNAUTHORIZED", "管理 API の認証に失敗しました。")
    csrf_token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + ADMIN_SESSION_MAX_AGE_SECONDS
    session_value = _sign_admin_session({"sub": "admin", "csrf": csrf_token, "exp": expires_at})
    return {
        "schema_version": "admin-session/v1",
        "authenticated": True,
        "csrf_token": csrf_token,
        "expires_at": _iso_from_epoch(expires_at),
        "trace_id": trace_id,
        "_set_cookie": _admin_session_cookie(session_value),
    }


def _admin_me(admin_auth: AdminAuth, trace_id: str) -> dict[str, Any]:
    csrf_token = admin_auth.csrf_token
    if admin_auth.mode == "bearer":
        csrf_token = os.environ.get("DIOPSIDE_ADMIN_CSRF_TOKEN")
    return {
        "schema_version": "admin-session/v1",
        "authenticated": True,
        "auth_mode": admin_auth.mode,
        **({"csrf_token": csrf_token} if csrf_token else {}),
        **({"expires_at": _iso_from_epoch(admin_auth.expires_at)} if admin_auth.expires_at else {}),
        "trace_id": trace_id,
    }


def _require_admin(request: Request) -> AdminAuth:
    expected = os.environ.get("DIOPSIDE_ADMIN_TOKEN")
    if not expected:
        raise ApiError(503, "ADMIN_NOT_CONFIGURED", "管理 API token が設定されていません。")
    auth = request.headers.get("authorization", "")
    if hmac.compare_digest(auth, f"Bearer {expected}"):
        return AdminAuth(mode="bearer")
    session = _admin_session_from_request(request)
    if session is not None:
        return session
    raise ApiError(401, "UNAUTHORIZED", "管理 API の認証に失敗しました。")


def _require_csrf(request: Request, admin_auth: AdminAuth) -> None:
    actual = request.headers.get("x-csrf-token", "")
    if admin_auth.mode == "cookie":
        if not admin_auth.csrf_token or not hmac.compare_digest(actual, admin_auth.csrf_token):
            raise ApiError(403, "CSRF_INVALID", "CSRF token が不正です。")
        return
    expected = os.environ.get("DIOPSIDE_ADMIN_CSRF_TOKEN")
    if not expected:
        raise ApiError(503, "CSRF_NOT_CONFIGURED", "CSRF token が設定されていません。")
    if not hmac.compare_digest(actual, expected):
        raise ApiError(403, "CSRF_INVALID", "CSRF token が不正です。")


def _admin_session_from_request(request: Request) -> AdminAuth | None:
    raw_cookie = request.headers.get("cookie", "")
    if not raw_cookie:
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(raw_cookie)
    except CookieError:
        return None
    morsel = cookie.get(ADMIN_SESSION_COOKIE)
    if not morsel:
        return None
    payload = _verify_admin_session(morsel.value)
    if payload is None:
        return None
    return AdminAuth(mode="cookie", csrf_token=str(payload["csrf"]), expires_at=int(payload["exp"]))


def _sign_admin_session(payload: dict[str, Any]) -> str:
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64(hmac.new(_admin_session_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def _verify_admin_session(value: str) -> dict[str, Any] | None:
    try:
        body, signature = value.split(".", 1)
    except ValueError:
        return None
    expected_signature = _b64(hmac.new(_admin_session_secret(), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("sub") != "admin" or not payload.get("csrf") or not isinstance(payload.get("exp"), int):
        return None
    if int(payload["exp"]) <= int(time.time()):
        return None
    return payload


def _admin_session_secret() -> bytes:
    secret = os.environ.get("DIOPSIDE_ADMIN_SESSION_SECRET") or os.environ.get("DIOPSIDE_ADMIN_TOKEN") or ""
    return secret.encode("utf-8")


def _admin_session_cookie(value: str) -> str:
    return f"{ADMIN_SESSION_COOKIE}={value}; Max-Age={ADMIN_SESSION_MAX_AGE_SECONDS}; Path=/api/admin; HttpOnly; Secure; SameSite=Lax"


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


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
    if not _local_fixture_mode_enabled():
        raise ApiError(
            503,
            "PUBLIC_DATA_REPOSITORY_NOT_CONFIGURED",
            "公開データ repository が未設定です。DIOPSIDE_TABLE_NAME または明示的な local fixture mode が必要です。",
        )
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
    return [_channel_response(item) for item in _repository().list_channels()]


def _channel_response(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "channel_id": item["channel_id"],
        "enabled": bool(item.get("enabled", True)),
        "uploads_playlist_id": item.get("uploads_playlist_id"),
        "display_name": item.get("display_name"),
        "metadata_interval_minutes": item.get("metadata_interval_minutes"),
        "live_scan_interval_minutes": item.get("live_scan_interval_minutes"),
        "notification_enabled": bool(item.get("notification_enabled", False)),
        "updated_at": item.get("updated_at"),
    }


def _private_artifact_s3_location(s3_uri: Any) -> tuple[str, str]:
    if not isinstance(s3_uri, str) or not s3_uri.startswith("s3://"):
        raise ApiError(403, "ARTIFACT_NOT_SIGNABLE", "署名 URL を発行できる private S3 artifact ではありません。")
    rest = s3_uri[5:]
    if "/" not in rest:
        raise ApiError(403, "ARTIFACT_NOT_SIGNABLE", "artifact の S3 URI が不正です。")
    bucket, key = rest.split("/", 1)
    if not bucket or not key or ".." in pathlib.PurePosixPath(key).parts:
        raise ApiError(403, "ARTIFACT_NOT_SIGNABLE", "artifact の S3 URI が不正です。")
    allowed_buckets = {value for value in [os.environ.get("DIOPSIDE_RAW_BUCKET"), os.environ.get("DIOPSIDE_PROCESSED_BUCKET")] if value}
    if not allowed_buckets:
        raise ApiError(503, "PRIVATE_ARTIFACT_BUCKET_NOT_CONFIGURED", "private artifact bucket が設定されていません。")
    if bucket not in allowed_buckets:
        raise ApiError(403, "ARTIFACT_NOT_SIGNABLE", "許可されていない S3 bucket の artifact です。")
    allowed_prefixes = ("raw/", "processed/", "failed/")
    if not key.startswith(allowed_prefixes):
        raise ApiError(403, "ARTIFACT_NOT_SIGNABLE", "許可されていない S3 prefix の artifact です。")
    return bucket, key


def _iso_after_seconds(seconds: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + seconds))


def _iso_from_epoch(epoch_seconds: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch_seconds))


def _list_quota_usage() -> list[dict[str, Any]]:
    items = []
    for item in _repository().list_quota_usage(100):
        details = item.get("details") or {}
        items.append(
            {
                **item,
                "channel_id": item.get("channel_id", details.get("channel_id")),
                "video_count": item.get("video_count", details.get("video_count")),
                "job_id": item.get("job_id", details.get("job_id")),
            }
        )
    return items


def _local_fixture_mode_enabled() -> bool:
    return os.environ.get("DIOPSIDE_LOCAL_FIXTURE_MODE") == "true" or "DIOPSIDE_PUBLIC_DATA_DIR" in os.environ


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
    headers = {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store, no-cache, max-age=0",
        "x-trace-id": trace_id,
    }
    body = dict(payload)
    set_cookie = body.pop("_set_cookie", None)
    if set_cookie:
        headers["set-cookie"] = str(set_cookie)
    return {
        "statusCode": status,
        "headers": headers,
        "body": json.dumps(body, ensure_ascii=False),
    }


def _log_api_request(
    event: dict[str, Any],
    request: Request | None,
    response: dict[str, Any],
    started: float,
    trace_id: str,
    *,
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> None:
    status = int(response["statusCode"])
    method = request.method if request else (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "GET"))
    path = request.path if request else (event.get("rawPath") or event.get("path") or "/")
    body = request.body if request else None
    log = {
        "service": SERVICE,
        "component": "api",
        "event": "api_request",
        "trace_id": trace_id,
        "method": method,
        "path": path,
        "status": status,
        "result": "succeeded" if status < 400 else "failed",
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "job_id": _first_present(result, body, key="job_id"),
        "job_type": _first_present(result, body, key="job_type"),
        "video_id": _extract_video_id(path, result, body),
        **({"error": error} if error else {}),
    }
    print(json.dumps({key: value for key, value in log.items() if value is not None}, ensure_ascii=False), flush=True)


def _first_present(*sources: dict[str, Any] | None, key: str) -> Any:
    for source in sources:
        if source and source.get(key) is not None:
            return source[key]
    return None


def _extract_video_id(path: str, *sources: dict[str, Any] | None) -> str | None:
    for source in sources:
        if not source:
            continue
        if source.get("video_id"):
            return str(source["video_id"])
        if isinstance(source.get("video"), dict) and source["video"].get("video_id"):
            return str(source["video"]["video_id"])
    parts = path.strip("/").split("/")
    if len(parts) >= 3 and parts[:2] == ["api", "videos"]:
        return parts[2]
    return None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
