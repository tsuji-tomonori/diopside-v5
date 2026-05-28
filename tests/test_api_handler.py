import json
import os

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


def test_public_video_search_and_detail():
    status, body = call("GET", "/api/videos", query={"tag": "歌枠"})
    assert status == 200
    assert [item["video_id"] for item in body["items"]] == ["fixture002"]

    status, detail = call("GET", "/api/videos/fixture001")
    assert status == 200
    assert detail["schema_version"] == "public-video-detail/v1"
    assert detail["chat_summary"]["wordcloud_url"]


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
