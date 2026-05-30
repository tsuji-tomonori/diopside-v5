import json
from pathlib import Path

from diopside_api.openapi_contract import API_ROUTES, build_openapi_contract


def test_openapi_contract_covers_api_001_to_023():
    spec = build_openapi_contract()
    operations = [
        operation
        for path_item in spec["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]
    design_ids = {operation["x-design-id"] for operation in operations}

    assert spec["openapi"] == "3.1.0"
    assert {f"API-{index:03d}" for index in range(1, 24)} <= design_ids
    assert len(API_ROUTES) == 23


def test_openapi_contract_records_paths_methods_and_schema_versions():
    spec = build_openapi_contract()

    assert spec["paths"]["/api/health"]["get"]["x-design-id"] == "API-001"
    assert spec["paths"]["/api/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/HealthResponse"}
    assert spec["paths"]["/api/config"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/PublicConfigResponse"}
    assert spec["paths"]["/api/videos/{video_id}"]["get"]["x-schema-version"] == "public-video-detail/v1"
    assert spec["paths"]["/api/admin/jobs/{job_id}/cancel"]["post"]["x-design-id"] == "API-019"
    assert spec["paths"]["/api/admin/channels/{channel_id}"]["put"]["x-schema-version"] == "admin-channel-config/v1"
    assert spec["paths"]["/api/admin/videos/{video_id}/tags"]["put"]["x-schema-version"] == "admin-video-tags/v1"
    assert spec["components"]["securitySchemes"]["AdminSession"]["in"] == "cookie"
    assert spec["components"]["schemas"]["HealthResponse"]["required"] == ["service", "version", "status", "checked_at"]
    assert spec["components"]["schemas"]["PublicConfigResponse"]["properties"]["schema_version"]["const"] == "public-config/v1"


def test_openapi_contract_routes_are_documented_and_present_in_lambda_handler_source():
    readme = Path("README.md").read_text(encoding="utf-8")
    handler = Path("apps/api/src/diopside_api/handler.py").read_text(encoding="utf-8")

    for route in API_ROUTES:
        assert f"`{route.method} {route.path}`" in readme
        stable_fragment = route.path.split("{", 1)[0].rstrip("/")
        assert stable_fragment in handler


def test_openapi_contract_module_emits_json(capsys):
    from diopside_api import openapi_contract

    openapi_contract.main()

    emitted = json.loads(capsys.readouterr().out)
    assert emitted["info"]["version"] == "v0.4-contract"
    assert "/api/random-videos" in emitted["paths"]
