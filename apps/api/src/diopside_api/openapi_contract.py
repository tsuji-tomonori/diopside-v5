from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ApiRouteContract:
    design_id: str
    method: str
    path: str
    summary: str
    schema_version: str | None
    auth: str


API_ROUTES: tuple[ApiRouteContract, ...] = (
    ApiRouteContract("API-001", "GET", "/api/health", "health API", None, "public"),
    ApiRouteContract("API-002", "GET", "/api/config", "公開設定取得 API", "public-config/v1", "public"),
    ApiRouteContract("API-003", "GET", "/api/home", "ホーム集約 API", "public-home/v1", "public"),
    ApiRouteContract("API-004", "GET", "/api/videos", "動画一覧・検索 API", "public-video-list/v1", "public"),
    ApiRouteContract("API-005", "GET", "/api/videos/{video_id}", "動画詳細 API", "public-video-detail/v1", "public"),
    ApiRouteContract("API-006", "GET", "/api/tags", "タグ一覧 API", "public-tag-list/v1", "public"),
    ApiRouteContract("API-007", "GET", "/api/archive-calendar", "年/月別アーカイブ API", "public-archive-calendar/v1", "public"),
    ApiRouteContract("API-008", "GET", "/api/random-videos", "ランダム動画 API", "public-random-videos/v1", "public"),
    ApiRouteContract("API-009", "GET", "/api/videos/{video_id}/artifacts", "動画成果物一覧 API", "public-video-artifacts/v1", "public"),
    ApiRouteContract("API-010", "GET", "/api/admin/jobs", "ジョブ一覧 API", "admin-job-list/v1", "admin"),
    ApiRouteContract("API-011", "GET", "/api/admin/jobs/{job_id}", "ジョブ詳細 API", "admin-job-detail/v1", "admin"),
    ApiRouteContract("API-012", "POST", "/api/admin/jobs/metadata-sync", "メタデータ同期開始 API", None, "admin"),
    ApiRouteContract("API-013", "POST", "/api/admin/jobs/live-status-scan", "ライブ状態検知開始 API", None, "admin"),
    ApiRouteContract("API-014", "POST", "/api/admin/jobs/chat-collect", "チャット収集開始 API", None, "admin"),
    ApiRouteContract("API-015", "POST", "/api/admin/jobs/chat-normalize", "チャット正規化開始 API", None, "admin"),
    ApiRouteContract("API-016", "POST", "/api/admin/jobs/rebuild-artifacts", "集計再生成 API", None, "admin"),
    ApiRouteContract("API-017", "POST", "/api/admin/jobs/static-export", "静的 export 開始 API", None, "admin"),
    ApiRouteContract("API-018", "POST", "/api/admin/jobs/{job_id}/retry", "失敗ジョブ再実行 API", None, "admin"),
    ApiRouteContract("API-019", "POST", "/api/admin/jobs/{job_id}/cancel", "ジョブキャンセル API", None, "admin"),
    ApiRouteContract("API-020", "GET", "/api/admin/quota-usage", "quota 使用量 API", "admin-quota-usage/v1", "admin"),
    ApiRouteContract("API-021", "GET", "/api/admin/channels", "対象チャンネル設定取得 API", "admin-channel-list/v1", "admin"),
    ApiRouteContract("API-022", "PUT", "/api/admin/channels/{channel_id}", "対象チャンネル設定更新 API", "admin-channel-config/v1", "admin"),
    ApiRouteContract("API-023", "POST", "/api/admin/artifacts/presigned-url", "管理用 S3 署名 URL 発行 API", "admin-artifact-presigned-url/v1", "admin"),
)

EXTRA_ROUTES: tuple[ApiRouteContract, ...] = (
    ApiRouteContract("ADMIN-SESSION", "POST", "/api/admin/session", "管理 session 発行 API", "admin-session/v1", "public"),
    ApiRouteContract("ADMIN-ME", "GET", "/api/admin/me", "管理 session 確認 API", "admin-session/v1", "admin"),
    ApiRouteContract("FR-A-005", "PUT", "/api/admin/videos/{video_id}/tags", "動画タグ補正 API", "admin-video-tags/v1", "admin"),
)


def all_route_contracts() -> tuple[ApiRouteContract, ...]:
    return (*API_ROUTES, *EXTRA_ROUTES)


def operation_id(route: ApiRouteContract) -> str:
    token = route.path.strip("/").replace("/", "_").replace("{", "by_").replace("}", "")
    return f"{route.method.lower()}_{token}"


def build_openapi_contract() -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for route in all_route_contracts():
        operation: dict[str, Any] = {
            "operationId": operation_id(route),
            "summary": route.summary,
            "tags": [route.auth],
            "x-design-id": route.design_id,
            "x-auth": route.auth,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/GenericJsonResponse"},
                        }
                    },
                }
            },
        }
        if route.schema_version:
            operation["x-schema-version"] = route.schema_version
        if route.auth == "admin":
            operation["security"] = [{"AdminSession": []}, {"AdminBearer": []}]
        paths.setdefault(route.path, {})[route.method.lower()] = operation
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "diopside API",
            "version": "v0.4-contract",
            "description": "v0.4 API-001〜023 contract generated from repository route metadata.",
        },
        "paths": paths,
        "components": {
            "securitySchemes": {
                "AdminSession": {"type": "apiKey", "in": "cookie", "name": "diopside_admin_session"},
                "AdminBearer": {"type": "http", "scheme": "bearer"},
                "CsrfToken": {"type": "apiKey", "in": "header", "name": "x-csrf-token"},
            },
            "schemas": {
                "GenericJsonResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "schema_version": {"type": "string"},
                        "trace_id": {"type": "string"},
                    },
                }
            },
        },
    }


def main() -> None:
    print(json.dumps(build_openapi_contract(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
