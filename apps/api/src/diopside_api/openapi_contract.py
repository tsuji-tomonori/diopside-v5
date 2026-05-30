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
    ApiRouteContract("STATIC-EXPORT-HISTORY", "GET", "/api/admin/static-exports", "StaticExport 履歴 API", "admin-static-export-list/v1", "admin"),
)


def all_route_contracts() -> tuple[ApiRouteContract, ...]:
    return (*API_ROUTES, *EXTRA_ROUTES)


def operation_id(route: ApiRouteContract) -> str:
    token = route.path.strip("/").replace("/", "_").replace("{", "by_").replace("}", "")
    return f"{route.method.lower()}_{token}"


def build_openapi_contract() -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for route in all_route_contracts():
        response_schema = {"$ref": "#/components/schemas/GenericJsonResponse"}
        if route.design_id == "API-001":
            response_schema = {"$ref": "#/components/schemas/HealthResponse"}
        elif route.design_id == "API-002":
            response_schema = {"$ref": "#/components/schemas/PublicConfigResponse"}
        elif route.design_id == "API-003":
            response_schema = {"$ref": "#/components/schemas/PublicHomeResponse"}
        elif route.design_id == "API-004":
            response_schema = {"$ref": "#/components/schemas/PublicVideoListResponse"}
        elif route.design_id == "API-005":
            response_schema = {"$ref": "#/components/schemas/PublicVideoDetailResponse"}
        elif route.design_id == "API-006":
            response_schema = {"$ref": "#/components/schemas/PublicTagListResponse"}
        elif route.design_id == "API-007":
            response_schema = {"$ref": "#/components/schemas/PublicArchiveCalendarResponse"}
        elif route.design_id == "API-008":
            response_schema = {"$ref": "#/components/schemas/PublicRandomVideosResponse"}
        elif route.design_id == "API-009":
            response_schema = {"$ref": "#/components/schemas/PublicVideoArtifactsResponse"}
        elif route.design_id == "API-010":
            response_schema = {"$ref": "#/components/schemas/AdminJobListResponse"}
        elif route.design_id == "API-011":
            response_schema = {"$ref": "#/components/schemas/AdminJobDetailResponse"}
        elif route.design_id in {"API-012", "API-013", "API-014", "API-015", "API-016", "API-017", "API-018", "API-019"}:
            response_schema = {"$ref": "#/components/schemas/AdminStartJobResponse"}
        elif route.design_id == "API-020":
            response_schema = {"$ref": "#/components/schemas/AdminQuotaUsageResponse"}
        elif route.design_id == "API-021":
            response_schema = {"$ref": "#/components/schemas/AdminChannelListResponse"}
        elif route.design_id == "API-022":
            response_schema = {"$ref": "#/components/schemas/AdminChannelConfigResponse"}
        elif route.design_id == "API-023":
            response_schema = {"$ref": "#/components/schemas/AdminArtifactPresignedUrlResponse"}
        elif route.design_id in {"ADMIN-SESSION", "ADMIN-ME"}:
            response_schema = {"$ref": "#/components/schemas/AdminSessionResponse"}
        elif route.design_id == "FR-A-005":
            response_schema = {"$ref": "#/components/schemas/AdminVideoTagsResponse"}
        elif route.design_id == "STATIC-EXPORT-HISTORY":
            response_schema = {"$ref": "#/components/schemas/AdminStaticExportListResponse"}
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
                            "schema": response_schema,
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
                },
                "HealthDependency": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["status"],
                    "properties": {
                        "status": {"type": "string"},
                    },
                },
                "HealthResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["service", "version", "status", "checked_at"],
                    "properties": {
                        "service": {"type": "string"},
                        "version": {"type": "string"},
                        "status": {"type": "string"},
                        "checked_at": {"type": "string", "format": "date-time"},
                        "dependencies": {
                            "type": "object",
                            "additionalProperties": {"$ref": "#/components/schemas/HealthDependency"},
                        },
                    },
                },
                "PublicConfigResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": [
                        "schema_version",
                        "system_name",
                        "default_locale",
                        "public_data_manifest",
                        "admin_api_enabled",
                    ],
                    "properties": {
                        "schema_version": {"const": "public-config/v1"},
                        "system_name": {"type": "string"},
                        "default_locale": {"type": "string"},
                        "public_data_manifest": {"type": "string"},
                        "admin_api_enabled": {"type": "boolean"},
                    },
                },
                "PublicVideoListItem": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["video_id", "title"],
                    "properties": {
                        "video_id": {"type": "string"},
                        "title": {"type": "string"},
                        "published_at": {"type": ["string", "null"], "format": "date-time"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "detail_path": {"type": ["string", "null"]},
                    },
                },
                "PublicTagItem": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["label", "video_count"],
                    "properties": {
                        "tag_id": {"type": ["string", "null"]},
                        "label": {"type": "string"},
                        "video_count": {"type": "integer"},
                        "category": {"type": ["string", "null"]},
                    },
                },
                "PublicHomeResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "latest_videos", "popular_tags"],
                    "properties": {
                        "schema_version": {"const": "public-home/v1"},
                        "latest_videos": {"type": "array", "items": {"$ref": "#/components/schemas/PublicVideoListItem"}},
                        "popular_tags": {"type": "array", "items": {"$ref": "#/components/schemas/PublicTagItem"}},
                        "updated_at": {"type": ["string", "null"], "format": "date-time"},
                        "generated_at": {"type": ["string", "null"], "format": "date-time"},
                    },
                },
                "PublicVideoListResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "items"],
                    "properties": {
                        "schema_version": {"const": "public-video-list/v1"},
                        "items": {"type": "array", "items": {"$ref": "#/components/schemas/PublicVideoListItem"}},
                        "generated_at": {"type": ["string", "null"], "format": "date-time"},
                    },
                },
                "PublicTagListResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "items"],
                    "properties": {
                        "schema_version": {"const": "public-tag-list/v1"},
                        "items": {"type": "array", "items": {"$ref": "#/components/schemas/PublicTagItem"}},
                        "generated_at": {"type": ["string", "null"], "format": "date-time"},
                    },
                },
                "PublicVideoDetailVideo": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["video_id", "title"],
                    "properties": {
                        "video_id": {"type": "string"},
                        "youtube_url": {"type": ["string", "null"]},
                        "title": {"type": "string"},
                        "description": {"type": ["string", "null"]},
                        "published_at": {"type": ["string", "null"], "format": "date-time"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "PublicVideoDetailResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "video"],
                    "properties": {
                        "schema_version": {"const": "public-video-detail/v1"},
                        "video": {"$ref": "#/components/schemas/PublicVideoDetailVideo"},
                        "chat_summary": {"type": "object", "additionalProperties": True},
                        "artifacts": {"type": ["object", "null"], "additionalProperties": True},
                        "timestamps": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                    },
                },
                "ArchiveYearItem": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["year", "video_count"],
                    "properties": {
                        "year": {"type": "integer"},
                        "video_count": {"type": "integer"},
                    },
                },
                "ArchiveMonthItem": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["month", "video_count"],
                    "properties": {
                        "year": {"type": ["integer", "null"]},
                        "month": {"type": "integer"},
                        "video_count": {"type": "integer"},
                    },
                },
                "ArchiveDayItem": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["date", "video_count"],
                    "properties": {
                        "date": {"type": "string"},
                        "video_count": {"type": "integer"},
                        "video_ids": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "PublicArchiveCalendarResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "generated_at", "months"],
                    "properties": {
                        "schema_version": {"const": "public-archive-calendar/v1"},
                        "generated_at": {"type": "string", "format": "date-time"},
                        "years": {"type": ["array", "null"], "items": {"$ref": "#/components/schemas/ArchiveYearItem"}},
                        "year": {"type": ["string", "null"]},
                        "months": {"type": "array", "items": {"$ref": "#/components/schemas/ArchiveMonthItem"}},
                        "days": {"type": ["array", "null"], "items": {"$ref": "#/components/schemas/ArchiveDayItem"}},
                    },
                },
                "PublicRandomVideosResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "items", "seed", "generated_at"],
                    "properties": {
                        "schema_version": {"const": "public-random-videos/v1"},
                        "items": {"type": "array", "items": {"$ref": "#/components/schemas/PublicVideoListItem"}},
                        "seed": {"type": "string"},
                        "generated_at": {"type": "string", "format": "date-time"},
                    },
                },
                "PublicVideoArtifactItem": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["artifact_type"],
                    "properties": {
                        "artifact_type": {"type": "string"},
                        "public_url_path": {"type": ["string", "null"]},
                        "available": {"type": ["boolean", "null"]},
                    },
                },
                "PublicVideoArtifactsResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "video_id", "items"],
                    "properties": {
                        "schema_version": {"const": "public-video-artifacts/v1"},
                        "video_id": {"type": "string"},
                        "items": {"type": "array", "items": {"$ref": "#/components/schemas/PublicVideoArtifactItem"}},
                    },
                },
                "AdminSessionResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "authenticated", "trace_id"],
                    "properties": {
                        "schema_version": {"const": "admin-session/v1"},
                        "authenticated": {"type": "boolean"},
                        "auth_mode": {"type": ["string", "null"]},
                        "csrf_token": {"type": ["string", "null"]},
                        "expires_at": {"type": ["string", "null"], "format": "date-time"},
                        "trace_id": {"type": "string"},
                    },
                },
                "AdminJobListResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "items", "trace_id"],
                    "properties": {
                        "schema_version": {"const": "admin-job-list/v1"},
                        "items": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                        "trace_id": {"type": "string"},
                    },
                },
                "AdminJobDetailResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "item", "trace_id"],
                    "properties": {
                        "schema_version": {"const": "admin-job-detail/v1"},
                        "item": {"type": "object", "additionalProperties": True},
                        "trace_id": {"type": "string"},
                    },
                },
                "AdminStartJobResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": [
                        "job_id",
                        "job_type",
                        "latest_state",
                        "derived_state",
                        "deduplicated",
                        "accepted_at",
                        "trace_id",
                        "dry_run",
                    ],
                    "properties": {
                        "job_id": {"type": "string"},
                        "job_type": {"type": "string"},
                        "latest_state": {"type": "string"},
                        "derived_state": {"type": "string"},
                        "deduplicated": {"type": "boolean"},
                        "accepted_at": {"type": "string", "format": "date-time"},
                        "trace_id": {"type": "string"},
                        "dry_run": {"type": "boolean"},
                    },
                },
                "AdminQuotaUsageResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "items", "daily", "by_method", "limit_per_day", "trace_id"],
                    "properties": {
                        "schema_version": {"const": "admin-quota-usage/v1"},
                        "items": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                        "daily": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                        "by_method": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                        "limit_per_day": {"type": "integer"},
                        "warning": {"type": ["string", "null"]},
                        "trace_id": {"type": "string"},
                    },
                },
                "AdminChannelItem": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["channel_id", "enabled"],
                    "properties": {
                        "channel_id": {"type": "string"},
                        "enabled": {"type": "boolean"},
                        "uploads_playlist_id": {"type": ["string", "null"]},
                        "display_name": {"type": ["string", "null"]},
                        "metadata_interval_minutes": {"type": ["integer", "null"]},
                        "live_scan_interval_minutes": {"type": ["integer", "null"]},
                        "notification_enabled": {"type": ["boolean", "null"]},
                        "updated_at": {"type": ["string", "null"], "format": "date-time"},
                    },
                },
                "AdminChannelListResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "items", "trace_id"],
                    "properties": {
                        "schema_version": {"const": "admin-channel-list/v1"},
                        "items": {"type": "array", "items": {"$ref": "#/components/schemas/AdminChannelItem"}},
                        "trace_id": {"type": "string"},
                    },
                },
                "AdminChannelConfigResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "item", "trace_id"],
                    "properties": {
                        "schema_version": {"const": "admin-channel-config/v1"},
                        "item": {"$ref": "#/components/schemas/AdminChannelItem"},
                        "trace_id": {"type": "string"},
                    },
                },
                "AdminArtifactPresignedUrlResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "artifact_id", "purpose", "url", "expires_at", "trace_id"],
                    "properties": {
                        "schema_version": {"const": "admin-artifact-presigned-url/v1"},
                        "artifact_id": {"type": "string"},
                        "purpose": {"type": "string", "enum": ["download", "inspect"]},
                        "url": {"type": "string"},
                        "expires_at": {"type": "string", "format": "date-time"},
                        "trace_id": {"type": "string"},
                    },
                },
                "AdminVideoTagsResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "video_id", "tags", "trace_id"],
                    "properties": {
                        "schema_version": {"const": "admin-video-tags/v1"},
                        "video_id": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "manual_tag_correction": {"type": ["object", "null"], "additionalProperties": True},
                        "trace_id": {"type": "string"},
                    },
                },
                "AdminStaticExportListResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["schema_version", "items", "trace_id"],
                    "properties": {
                        "schema_version": {"const": "admin-static-export-list/v1"},
                        "items": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                        "trace_id": {"type": "string"},
                    },
                },
            },
        },
    }


def main() -> None:
    print(json.dumps(build_openapi_contract(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
