import json
import os

os.environ.setdefault("DIOPSIDE_LOCAL_FIXTURE_MODE", "true")

import diopside_api.handler as handler
from diopside_core import MemoryRepository

from diopside_api.handler import lambda_handler


def call(method, path, body=None, headers=None, query=None):
    response = call_response(method, path, body=body, headers=headers, query=query)
    return response["statusCode"], json.loads(response["body"])


def call_response(method, path, body=None, headers=None, query=None):
    event = {
        "rawPath": path,
        "requestContext": {"http": {"method": method}},
        "headers": headers or {},
        "queryStringParameters": query or {},
        "body": json.dumps(body) if body is not None else None,
    }
    return lambda_handler(event, None)


def test_health_public():
    status, body = call("GET", "/api/health")
    assert status == 200
    assert body["service"] == "diopside"
    assert body["status"] == "ok"


def test_api_emits_json_request_log(capsys):
    status, body = call("GET", "/api/videos/fixture001", headers={"x-trace-id": "trace-unit"})

    log = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert status == 200
    assert body["video"]["video_id"] == "fixture001"
    assert log["component"] == "api"
    assert log["event"] == "api_request"
    assert log["trace_id"] == "trace-unit"
    assert log["status"] == 200
    assert log["result"] == "succeeded"
    assert log["video_id"] == "fixture001"
    assert isinstance(log["duration_ms"], float)
    assert "authorization" not in log


def test_api_error_log_matches_error_response_trace(capsys):
    status, body = call("GET", "/api/admin/jobs", headers={"x-trace-id": "trace-error"})

    log = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert status == 503
    assert body["trace_id"] == "trace-error"
    assert log["trace_id"] == body["trace_id"]
    assert log["status"] == 503
    assert log["result"] == "failed"
    assert log["error"]["code"] == "ADMIN_NOT_CONFIGURED"
    assert log["error"]["type"] == "ApiError"


def test_public_video_search_and_detail():
    status, body = call("GET", "/api/videos", query={"tag": "歌枠"})
    assert status == 200
    assert [item["video_id"] for item in body["items"]] == ["fixture002"]

    status, detail = call("GET", "/api/videos/fixture001")
    assert status == 200
    assert detail["schema_version"] == "public-video-detail/v1"
    assert detail["chat_summary"]["wordcloud_url"]


def test_archive_calendar_filters_year_month():
    status, body = call("GET", "/api/archive-calendar", query={"year": "2026", "month": "5"})

    assert status == 200
    assert body["schema_version"] == "public-archive-calendar/v1"
    assert body["years"] == [{"year": 2026, "video_count": 2}]
    assert body["months"] == [{"year": 2026, "month": 5, "video_count": 2}]
    assert {day["date"]: day["video_ids"] for day in body["days"]} == {
        "2026-05-27": ["fixture001"],
        "2026-05-20": ["fixture002"],
    }


def test_archive_calendar_rejects_invalid_query():
    status, body = call("GET", "/api/archive-calendar", query={"month": "5"})

    assert status == 400
    assert body["code"] == "INVALID_REQUEST"


def test_home_uses_repository_when_table_name_is_configured(monkeypatch):
    repo = MemoryRepository()
    repo.put_video(
        {
            "video_id": "repo001",
            "title": "repository video",
            "published_at": "2026-05-29T00:00:00Z",
            "tags": ["repo"],
            "public": True,
        }
    )
    monkeypatch.setenv("DIOPSIDE_TABLE_NAME", "unit-table")
    monkeypatch.setattr(handler, "_REPOSITORY", repo)
    monkeypatch.setattr(
        handler,
        "_load_json",
        lambda path: (_ for _ in ()).throw(AssertionError(f"fixture manifest should not be loaded: {path}")),
    )

    status, body = call("GET", "/api/home")

    assert status == 200
    assert body["latest_videos"][0]["video_id"] == "repo001"
    assert body["popular_tags"][0]["label"] == "repo"
    monkeypatch.delenv("DIOPSIDE_TABLE_NAME", raising=False)
    monkeypatch.setattr(handler, "_REPOSITORY", None)


def test_admin_requires_auth():
    status, body = call("GET", "/api/admin/jobs")
    assert status == 503
    assert body["code"] == "ADMIN_NOT_CONFIGURED"


def test_admin_session_cookie_auth_and_csrf(monkeypatch):
    monkeypatch.setenv("DIOPSIDE_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("DIOPSIDE_ALLOW_DRY_RUN_JOBS", "true")

    response = call_response("POST", "/api/admin/session", body={"passphrase": "secret"})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["schema_version"] == "admin-session/v1"
    assert body["csrf_token"]
    set_cookie = response["headers"]["set-cookie"]
    assert "diopside_admin_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=Lax" in set_cookie
    cookie = set_cookie.split(";", 1)[0]

    status, me = call("GET", "/api/admin/me", headers={"cookie": cookie})
    assert status == 200
    assert me["schema_version"] == "admin-session/v1"
    assert me["auth_mode"] == "cookie"
    assert me["csrf_token"] == body["csrf_token"]

    status, jobs = call("GET", "/api/admin/jobs", headers={"cookie": cookie})
    assert status == 200
    assert jobs["schema_version"] == "admin-job-list/v1"

    status, csrf_error = call(
        "POST",
        "/api/admin/jobs/static-export",
        body={"idempotency_key": "cookie-missing-csrf", "scope": "all"},
        headers={"cookie": cookie},
    )
    assert status == 403
    assert csrf_error["code"] == "CSRF_INVALID"

    status, unauthorized = call(
        "POST",
        "/api/admin/jobs/static-export",
        body={"idempotency_key": "cookie-missing-auth", "scope": "all"},
        headers={"x-csrf-token": body["csrf_token"]},
    )
    assert status == 401
    assert unauthorized["code"] == "UNAUTHORIZED"

    status, created = call(
        "POST",
        "/api/admin/jobs/static-export",
        body={"idempotency_key": "cookie-session", "scope": "all"},
        headers={"cookie": cookie, "x-csrf-token": body["csrf_token"]},
    )
    assert status == 200
    assert created["job_type"] == "static_export"
    assert created["dry_run"] is True


def test_admin_session_rejects_invalid_passphrase(monkeypatch):
    monkeypatch.setenv("DIOPSIDE_ADMIN_TOKEN", "secret")

    status, body = call("POST", "/api/admin/session", body={"passphrase": "wrong"})

    assert status == 401
    assert body["code"] == "UNAUTHORIZED"


def test_admin_job_dry_run(monkeypatch):
    monkeypatch.setenv("DIOPSIDE_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("DIOPSIDE_ADMIN_CSRF_TOKEN", "csrf")
    monkeypatch.setenv("DIOPSIDE_ALLOW_DRY_RUN_JOBS", "true")
    status, body = call(
        "POST",
        "/api/admin/jobs/static-export",
        body={"idempotency_key": "it-1", "scope": "all"},
        headers={"authorization": "Bearer secret", "x-csrf-token": "csrf"},
    )
    assert status == 200
    assert body["job_type"] == "static_export"
    assert body["dry_run"] is True
    status, duplicate = call(
        "POST",
        "/api/admin/jobs/static-export",
        body={"idempotency_key": "it-1", "scope": "all"},
        headers={"authorization": "Bearer secret", "x-csrf-token": "csrf"},
    )
    assert status == 200
    assert duplicate["job_id"] == body["job_id"]
    assert duplicate["deduplicated"] is True
    status, detail = call(
        "GET",
        f"/api/admin/jobs/{body['job_id']}",
        headers={"authorization": "Bearer secret"},
    )
    assert status == 200
    assert detail["item"]["events"][0]["event_type"] == "queued"
    os.environ.pop("DIOPSIDE_ADMIN_TOKEN", None)
    os.environ.pop("DIOPSIDE_ADMIN_CSRF_TOKEN", None)
    os.environ.pop("DIOPSIDE_ALLOW_DRY_RUN_JOBS", None)


def test_admin_job_body_validation(monkeypatch):
    monkeypatch.setenv("DIOPSIDE_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("DIOPSIDE_ADMIN_CSRF_TOKEN", "csrf")
    monkeypatch.setenv("DIOPSIDE_ALLOW_DRY_RUN_JOBS", "true")
    status, body = call(
        "POST",
        "/api/admin/jobs/chat-collect",
        body={"idempotency_key": "it-2"},
        headers={"authorization": "Bearer secret", "x-csrf-token": "csrf"},
    )
    assert status == 400
    assert body["code"] == "INVALID_REQUEST"


def test_admin_quota_usage_returns_visible_fields(monkeypatch):
    repo = MemoryRepository()
    repo.record_quota_usage("videos.list", 1, {"source": "unit"}, channel_id="ch", video_count=3, job_id="job-1")
    monkeypatch.setenv("DIOPSIDE_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("DIOPSIDE_ADMIN_CSRF_TOKEN", "csrf")
    monkeypatch.setattr(handler, "_REPOSITORY", repo)

    status, body = call("GET", "/api/admin/quota-usage", headers={"authorization": "Bearer secret"})

    assert status == 200
    assert body["schema_version"] == "admin-quota-usage/v1"
    assert body["items"][0]["method"] == "videos.list"
    assert body["items"][0]["units"] == 1
    assert body["items"][0]["video_count"] == 3
    assert body["items"][0]["channel_id"] == "ch"
    assert body["items"][0]["job_id"] == "job-1"
    os.environ.pop("DIOPSIDE_ADMIN_TOKEN", None)
    os.environ.pop("DIOPSIDE_ADMIN_CSRF_TOKEN", None)
    monkeypatch.setattr(handler, "_REPOSITORY", None)


def test_admin_channel_update_requires_csrf_and_persists(monkeypatch):
    repo = MemoryRepository()
    monkeypatch.setenv("DIOPSIDE_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("DIOPSIDE_ADMIN_CSRF_TOKEN", "csrf")
    monkeypatch.setattr(handler, "_REPOSITORY", repo)

    status, csrf_error = call(
        "PUT",
        "/api/admin/channels/ch-1",
        body={"enabled": True, "metadata_interval_minutes": 720, "live_scan_interval_minutes": 30, "notification_enabled": False},
        headers={"authorization": "Bearer secret"},
    )
    assert status == 403
    assert csrf_error["code"] == "CSRF_INVALID"

    status, body = call(
        "PUT",
        "/api/admin/channels/ch-1",
        body={
            "enabled": True,
            "uploads_playlist_id": "UUuploads",
            "display_name": "白雪巴",
            "metadata_interval_minutes": 720,
            "live_scan_interval_minutes": 30,
            "notification_enabled": True,
        },
        headers={"authorization": "Bearer secret", "x-csrf-token": "csrf"},
    )

    assert status == 200
    assert body["schema_version"] == "admin-channel-config/v1"
    assert body["item"]["channel_id"] == "ch-1"
    assert body["item"]["uploads_playlist_id"] == "UUuploads"
    assert body["item"]["notification_enabled"] is True
    assert repo.get_item("CHANNEL#ch-1", "META")["item_type"] == "Channel"

    status, channels = call("GET", "/api/admin/channels", headers={"authorization": "Bearer secret"})
    assert status == 200
    assert channels["items"][0]["channel_id"] == "ch-1"

    os.environ.pop("DIOPSIDE_ADMIN_TOKEN", None)
    os.environ.pop("DIOPSIDE_ADMIN_CSRF_TOKEN", None)
    monkeypatch.setattr(handler, "_REPOSITORY", None)


def test_admin_channel_update_validates_body(monkeypatch):
    monkeypatch.setenv("DIOPSIDE_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("DIOPSIDE_ADMIN_CSRF_TOKEN", "csrf")

    status, body = call(
        "PUT",
        "/api/admin/channels/ch-1",
        body={"enabled": "yes", "metadata_interval_minutes": 0, "live_scan_interval_minutes": 30, "notification_enabled": True},
        headers={"authorization": "Bearer secret", "x-csrf-token": "csrf"},
    )

    assert status == 400
    assert body["code"] == "INVALID_REQUEST"
    os.environ.pop("DIOPSIDE_ADMIN_TOKEN", None)
    os.environ.pop("DIOPSIDE_ADMIN_CSRF_TOKEN", None)


def test_admin_presigned_url_restricts_private_artifacts(monkeypatch):
    repo = MemoryRepository()
    repo.put_artifact("vid001", {"artifact_type": "raw-chat", "s3_uri": "s3://raw-bucket/raw/youtube/chat/vid001.jsonl", "content_type": "application/jsonl"})

    class FakeS3:
        def generate_presigned_url(self, operation, Params, ExpiresIn):
            assert operation == "get_object"
            assert Params == {"Bucket": "raw-bucket", "Key": "raw/youtube/chat/vid001.jsonl"}
            assert ExpiresIn == 120
            return "https://signed.example/raw"

    monkeypatch.setenv("DIOPSIDE_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("DIOPSIDE_ADMIN_CSRF_TOKEN", "csrf")
    monkeypatch.setenv("DIOPSIDE_RAW_BUCKET", "raw-bucket")
    monkeypatch.setattr(handler, "_REPOSITORY", repo)
    monkeypatch.setattr(handler, "boto3", type("FakeBoto3", (), {"client": staticmethod(lambda name: FakeS3())}))

    status, body = call(
        "POST",
        "/api/admin/artifacts/presigned-url",
        body={"artifact_id": "vid001:raw-chat", "purpose": "inspect", "expires_in_seconds": 120},
        headers={"authorization": "Bearer secret", "x-csrf-token": "csrf"},
    )

    assert status == 200
    assert body["schema_version"] == "admin-artifact-presigned-url/v1"
    assert body["url"] == "https://signed.example/raw"
    assert body["artifact_id"] == "vid001:raw-chat"
    assert body["purpose"] == "inspect"

    os.environ.pop("DIOPSIDE_ADMIN_TOKEN", None)
    os.environ.pop("DIOPSIDE_ADMIN_CSRF_TOKEN", None)
    os.environ.pop("DIOPSIDE_RAW_BUCKET", None)
    monkeypatch.setattr(handler, "_REPOSITORY", None)
    monkeypatch.setattr(handler, "boto3", None)


def test_admin_presigned_url_rejects_public_or_unknown_artifacts(monkeypatch):
    repo = MemoryRepository()
    repo.put_artifact("vid001", {"artifact_type": "wordcloud", "public_url_path": "/data/artifacts/wordcloud/vid001.json", "content_type": "application/json"})
    monkeypatch.setenv("DIOPSIDE_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("DIOPSIDE_ADMIN_CSRF_TOKEN", "csrf")
    monkeypatch.setattr(handler, "_REPOSITORY", repo)

    status, body = call(
        "POST",
        "/api/admin/artifacts/presigned-url",
        body={"artifact_id": "vid001:wordcloud", "purpose": "download"},
        headers={"authorization": "Bearer secret", "x-csrf-token": "csrf"},
    )

    assert status == 403
    assert body["code"] == "ARTIFACT_NOT_SIGNABLE"

    status, missing = call(
        "POST",
        "/api/admin/artifacts/presigned-url",
        body={"artifact_id": "vid001:missing", "purpose": "download"},
        headers={"authorization": "Bearer secret", "x-csrf-token": "csrf"},
    )
    assert status == 404
    assert missing["code"] == "ARTIFACT_NOT_FOUND"

    os.environ.pop("DIOPSIDE_ADMIN_TOKEN", None)
    os.environ.pop("DIOPSIDE_ADMIN_CSRF_TOKEN", None)
    monkeypatch.setattr(handler, "_REPOSITORY", None)
