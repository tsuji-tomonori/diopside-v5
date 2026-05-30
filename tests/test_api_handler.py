import json
import os

os.environ.setdefault("DIOPSIDE_LOCAL_FIXTURE_MODE", "true")

import diopside_api.handler as handler
from diopside_core import MemoryRepository

from diopside_api.handler import lambda_handler


def call(method, path, body=None, headers=None, query=None):
    event = {
        "rawPath": path,
        "requestContext": {"http": {"method": method}},
        "headers": headers or {},
        "queryStringParameters": query or {},
        "body": json.dumps(body) if body is not None else None,
    }
    response = lambda_handler(event, None)
    return response["statusCode"], json.loads(response["body"])


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
