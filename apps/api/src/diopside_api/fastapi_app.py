from __future__ import annotations

import json
import inspect
from typing import Any, Callable

from .handler import lambda_handler
from .openapi_contract import all_route_contracts, build_openapi_contract


def create_app() -> Any:
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, Response
        from pydantic import BaseModel, ConfigDict
    except ModuleNotFoundError as exc:  # pragma: no cover - optional runtime dependency.
        raise RuntimeError("FastAPI adapter requires the optional 'fastapi' package.") from exc

    class HealthDependency(BaseModel):
        model_config = ConfigDict(extra="allow")
        status: str

    class HealthResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        service: str
        version: str
        status: str
        checked_at: str
        dependencies: dict[str, HealthDependency] | None = None

    class PublicConfigResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        system_name: str
        default_locale: str
        public_data_manifest: str
        admin_api_enabled: bool

    class PublicVideoListItem(BaseModel):
        model_config = ConfigDict(extra="allow")
        video_id: str
        title: str
        published_at: str | None = None
        tags: list[str] = []
        detail_path: str | None = None

    class PublicTagItem(BaseModel):
        model_config = ConfigDict(extra="allow")
        label: str
        video_count: int
        tag_id: str | None = None
        category: str | None = None

    class PublicHomeResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        latest_videos: list[PublicVideoListItem]
        popular_tags: list[PublicTagItem]
        updated_at: str | None = None
        generated_at: str | None = None

    class PublicVideoListResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        items: list[PublicVideoListItem]
        generated_at: str | None = None

    class PublicTagListResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        items: list[PublicTagItem]
        generated_at: str | None = None

    class PublicVideoDetailVideo(BaseModel):
        model_config = ConfigDict(extra="allow")
        video_id: str
        title: str
        youtube_url: str | None = None
        description: str | None = None
        published_at: str | None = None
        tags: list[str] = []

    class PublicVideoDetailResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        video: PublicVideoDetailVideo
        chat_summary: dict[str, Any] = {}
        artifacts: dict[str, Any] | None = None
        timestamps: list[dict[str, Any]] = []

    class ArchiveYearItem(BaseModel):
        model_config = ConfigDict(extra="allow")
        year: int
        video_count: int

    class ArchiveMonthItem(BaseModel):
        model_config = ConfigDict(extra="allow")
        month: int
        video_count: int
        year: int | None = None

    class ArchiveDayItem(BaseModel):
        model_config = ConfigDict(extra="allow")
        date: str
        video_count: int
        video_ids: list[str] = []

    class PublicArchiveCalendarResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        generated_at: str
        years: list[ArchiveYearItem] | None = None
        year: str | None = None
        months: list[ArchiveMonthItem]
        days: list[ArchiveDayItem] | None = None

    class PublicRandomVideosResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        items: list[PublicVideoListItem]
        seed: str
        generated_at: str

    class PublicVideoArtifactItem(BaseModel):
        model_config = ConfigDict(extra="allow")
        artifact_type: str
        public_url_path: str | None = None
        available: bool | None = None

    class PublicVideoArtifactsResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        video_id: str
        items: list[PublicVideoArtifactItem]

    class AdminSessionResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        authenticated: bool
        trace_id: str
        auth_mode: str | None = None
        csrf_token: str | None = None
        expires_at: str | None = None

    class AdminJobListResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        items: list[dict[str, Any]]
        trace_id: str

    class AdminJobDetailResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        item: dict[str, Any]
        trace_id: str

    class AdminStartJobResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        job_id: str
        job_type: str
        latest_state: str
        derived_state: str
        deduplicated: bool
        accepted_at: str
        trace_id: str
        dry_run: bool

    class AdminQuotaUsageResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        items: list[dict[str, Any]]
        daily: list[dict[str, Any]]
        by_method: list[dict[str, Any]]
        limit_per_day: int
        warning: str | None = None
        trace_id: str

    class AdminChannelItem(BaseModel):
        model_config = ConfigDict(extra="allow")
        channel_id: str
        enabled: bool
        uploads_playlist_id: str | None = None
        display_name: str | None = None
        metadata_interval_minutes: int | None = None
        live_scan_interval_minutes: int | None = None
        notification_enabled: bool | None = None
        updated_at: str | None = None

    class AdminChannelListResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        items: list[AdminChannelItem]
        trace_id: str

    class AdminChannelConfigResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        item: AdminChannelItem
        trace_id: str

    class AdminArtifactPresignedUrlResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        artifact_id: str
        purpose: str
        url: str
        expires_at: str
        trace_id: str

    class AdminVideoTagsResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        video_id: str
        tags: list[str]
        trace_id: str
        manual_tag_correction: dict[str, Any] | None = None

    class AdminStaticExportListResponse(BaseModel):
        model_config = ConfigDict(extra="allow")
        schema_version: str
        items: list[dict[str, Any]]
        trace_id: str

    app = FastAPI(title="diopside API", version="v0.4-contract")

    def custom_openapi() -> dict[str, Any]:
        return build_openapi_contract()

    app.openapi = custom_openapi  # type: ignore[method-assign]

    async def health(request: Any) -> HealthResponse:
        return HealthResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def config(request: Any) -> PublicConfigResponse:
        return PublicConfigResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def home(request: Any) -> PublicHomeResponse:
        return PublicHomeResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def videos(request: Any) -> PublicVideoListResponse:
        return PublicVideoListResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def tags(request: Any) -> PublicTagListResponse:
        return PublicTagListResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def video_detail(request: Any) -> PublicVideoDetailResponse:
        return PublicVideoDetailResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def archive_calendar(request: Any) -> PublicArchiveCalendarResponse:
        return PublicArchiveCalendarResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def random_videos(request: Any) -> PublicRandomVideosResponse:
        return PublicRandomVideosResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def video_artifacts(request: Any) -> PublicVideoArtifactsResponse:
        return PublicVideoArtifactsResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def admin_session(request: Request, response: Response) -> AdminSessionResponse:
        body, headers, status_code = await _invoke_lambda_parts(request, "POST")
        content = json.loads(body) if body else {}
        if not 200 <= status_code < 300:
            from fastapi import HTTPException

            raise HTTPException(status_code=status_code, detail=content, headers=headers)
        for key, value in headers.items():
            if key.lower() == "content-type":
                continue
            response.headers[key] = value
        return AdminSessionResponse.model_validate(content)

    async def admin_me(request: Any) -> AdminSessionResponse:
        return AdminSessionResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def admin_jobs(request: Any) -> AdminJobListResponse:
        return AdminJobListResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def admin_job_detail(request: Any) -> AdminJobDetailResponse:
        return AdminJobDetailResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def start_admin_job(request: Any) -> AdminStartJobResponse:
        return AdminStartJobResponse.model_validate(await _invoke_lambda_json(request, "POST"))

    async def admin_quota_usage(request: Any) -> AdminQuotaUsageResponse:
        return AdminQuotaUsageResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def admin_channels(request: Any) -> AdminChannelListResponse:
        return AdminChannelListResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    async def update_admin_channel(request: Any) -> AdminChannelConfigResponse:
        return AdminChannelConfigResponse.model_validate(await _invoke_lambda_json(request, "PUT"))

    async def admin_artifact_presigned_url(request: Any) -> AdminArtifactPresignedUrlResponse:
        return AdminArtifactPresignedUrlResponse.model_validate(await _invoke_lambda_json(request, "POST"))

    async def update_admin_video_tags(request: Any) -> AdminVideoTagsResponse:
        return AdminVideoTagsResponse.model_validate(await _invoke_lambda_json(request, "PUT"))

    async def admin_static_exports(request: Any) -> AdminStaticExportListResponse:
        return AdminStaticExportListResponse.model_validate(await _invoke_lambda_json(request, "GET"))

    _set_request_signature(health, Request)
    _set_request_signature(config, Request)
    _set_request_signature(home, Request)
    _set_request_signature(videos, Request)
    _set_request_signature(tags, Request)
    _set_request_signature(video_detail, Request)
    _set_request_signature(archive_calendar, Request)
    _set_request_signature(random_videos, Request)
    _set_request_signature(video_artifacts, Request)
    _set_request_response_signature(admin_session, Request, Response)
    _set_request_signature(admin_me, Request)
    _set_request_signature(admin_jobs, Request)
    _set_request_signature(admin_job_detail, Request)
    _set_request_signature(start_admin_job, Request)
    _set_request_signature(admin_quota_usage, Request)
    _set_request_signature(admin_channels, Request)
    _set_request_signature(update_admin_channel, Request)
    _set_request_signature(admin_artifact_presigned_url, Request)
    _set_request_signature(update_admin_video_tags, Request)
    _set_request_signature(admin_static_exports, Request)

    app.add_api_route(
        "/api/health",
        health,
        methods=["GET"],
        summary="health API",
        operation_id="get_api_001",
        response_model=HealthResponse,
    )
    app.add_api_route(
        "/api/config",
        config,
        methods=["GET"],
        summary="公開設定取得 API",
        operation_id="get_api_002",
        response_model=PublicConfigResponse,
    )
    app.add_api_route(
        "/api/home",
        home,
        methods=["GET"],
        summary="ホーム集約 API",
        operation_id="get_api_003",
        response_model=PublicHomeResponse,
    )
    app.add_api_route(
        "/api/videos",
        videos,
        methods=["GET"],
        summary="動画一覧・検索 API",
        operation_id="get_api_004",
        response_model=PublicVideoListResponse,
    )
    app.add_api_route(
        "/api/tags",
        tags,
        methods=["GET"],
        summary="タグ一覧 API",
        operation_id="get_api_006",
        response_model=PublicTagListResponse,
    )
    app.add_api_route(
        "/api/videos/{video_id}",
        video_detail,
        methods=["GET"],
        summary="動画詳細 API",
        operation_id="get_api_005",
        response_model=PublicVideoDetailResponse,
    )
    app.add_api_route(
        "/api/archive-calendar",
        archive_calendar,
        methods=["GET"],
        summary="年/月別アーカイブ API",
        operation_id="get_api_007",
        response_model=PublicArchiveCalendarResponse,
    )
    app.add_api_route(
        "/api/random-videos",
        random_videos,
        methods=["GET"],
        summary="ランダム動画 API",
        operation_id="get_api_008",
        response_model=PublicRandomVideosResponse,
    )
    app.add_api_route(
        "/api/videos/{video_id}/artifacts",
        video_artifacts,
        methods=["GET"],
        summary="動画成果物一覧 API",
        operation_id="get_api_009",
        response_model=PublicVideoArtifactsResponse,
    )
    app.add_api_route(
        "/api/admin/session",
        admin_session,
        methods=["POST"],
        summary="管理 session 発行 API",
        operation_id="post_admin_session",
        response_model=AdminSessionResponse,
    )
    app.add_api_route(
        "/api/admin/me",
        admin_me,
        methods=["GET"],
        summary="管理 session 確認 API",
        operation_id="get_admin_me",
        response_model=AdminSessionResponse,
    )
    app.add_api_route(
        "/api/admin/jobs",
        admin_jobs,
        methods=["GET"],
        summary="ジョブ一覧 API",
        operation_id="get_api_010",
        response_model=AdminJobListResponse,
    )
    app.add_api_route(
        "/api/admin/jobs/{job_id}",
        admin_job_detail,
        methods=["GET"],
        summary="ジョブ詳細 API",
        operation_id="get_api_011",
        response_model=AdminJobDetailResponse,
    )
    for path, operation_id, summary in [
        ("/api/admin/jobs/metadata-sync", "post_api_012", "メタデータ同期開始 API"),
        ("/api/admin/jobs/live-status-scan", "post_api_013", "ライブ状態検知開始 API"),
        ("/api/admin/jobs/chat-collect", "post_api_014", "チャット収集開始 API"),
        ("/api/admin/jobs/chat-normalize", "post_api_015", "チャット正規化開始 API"),
        ("/api/admin/jobs/rebuild-artifacts", "post_api_016", "集計再生成 API"),
        ("/api/admin/jobs/static-export", "post_api_017", "静的 export 開始 API"),
        ("/api/admin/jobs/{job_id}/retry", "post_api_018", "失敗ジョブ再実行 API"),
        ("/api/admin/jobs/{job_id}/cancel", "post_api_019", "ジョブキャンセル API"),
    ]:
        app.add_api_route(
            path,
            start_admin_job,
            methods=["POST"],
            summary=summary,
            operation_id=operation_id,
            response_model=AdminStartJobResponse,
        )
    app.add_api_route(
        "/api/admin/quota-usage",
        admin_quota_usage,
        methods=["GET"],
        summary="quota 使用量 API",
        operation_id="get_api_020",
        response_model=AdminQuotaUsageResponse,
    )
    app.add_api_route(
        "/api/admin/channels",
        admin_channels,
        methods=["GET"],
        summary="対象チャンネル設定取得 API",
        operation_id="get_api_021",
        response_model=AdminChannelListResponse,
    )
    app.add_api_route(
        "/api/admin/channels/{channel_id}",
        update_admin_channel,
        methods=["PUT"],
        summary="対象チャンネル設定更新 API",
        operation_id="put_api_022",
        response_model=AdminChannelConfigResponse,
    )
    app.add_api_route(
        "/api/admin/artifacts/presigned-url",
        admin_artifact_presigned_url,
        methods=["POST"],
        summary="管理用 S3 署名 URL 発行 API",
        operation_id="post_api_023",
        response_model=AdminArtifactPresignedUrlResponse,
    )
    app.add_api_route(
        "/api/admin/videos/{video_id}/tags",
        update_admin_video_tags,
        methods=["PUT"],
        summary="動画タグ補正 API",
        operation_id="put_admin_video_tags",
        response_model=AdminVideoTagsResponse,
    )
    app.add_api_route(
        "/api/admin/static-exports",
        admin_static_exports,
        methods=["GET"],
        summary="StaticExport 履歴 API",
        operation_id="get_admin_static_exports",
        response_model=AdminStaticExportListResponse,
    )

    native_paths = {
        ("GET", "/api/health"),
        ("GET", "/api/config"),
        ("GET", "/api/home"),
        ("GET", "/api/videos"),
        ("GET", "/api/tags"),
        ("GET", "/api/videos/{video_id}"),
        ("GET", "/api/archive-calendar"),
        ("GET", "/api/random-videos"),
        ("GET", "/api/videos/{video_id}/artifacts"),
        ("POST", "/api/admin/session"),
        ("GET", "/api/admin/me"),
        ("GET", "/api/admin/jobs"),
        ("GET", "/api/admin/jobs/{job_id}"),
        ("POST", "/api/admin/jobs/metadata-sync"),
        ("POST", "/api/admin/jobs/live-status-scan"),
        ("POST", "/api/admin/jobs/chat-collect"),
        ("POST", "/api/admin/jobs/chat-normalize"),
        ("POST", "/api/admin/jobs/rebuild-artifacts"),
        ("POST", "/api/admin/jobs/static-export"),
        ("POST", "/api/admin/jobs/{job_id}/retry"),
        ("POST", "/api/admin/jobs/{job_id}/cancel"),
        ("GET", "/api/admin/quota-usage"),
        ("GET", "/api/admin/channels"),
        ("PUT", "/api/admin/channels/{channel_id}"),
        ("POST", "/api/admin/artifacts/presigned-url"),
        ("PUT", "/api/admin/videos/{video_id}/tags"),
        ("GET", "/api/admin/static-exports"),
    }
    for route in all_route_contracts():
        if (route.method, route.path) in native_paths:
            continue
        app.add_api_route(
            route.path,
            _delegate_to_lambda(route.method, Request),
            methods=[route.method],
            summary=route.summary,
            operation_id=f"{route.method.lower()}_{route.design_id.lower().replace('-', '_')}",
        )

    async def not_found(request: Request) -> Response:
        return await _invoke_lambda(request, "GET")

    app.add_api_route("/{path:path}", not_found, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    return app


def _delegate_to_lambda(method: str, request_type: type[Any]) -> Callable[[Any], Any]:
    async def endpoint(request: Any) -> Any:
        return await _invoke_lambda(request, method)

    _set_request_signature(endpoint, request_type)
    return endpoint


def _set_request_signature(endpoint: Callable[[Any], Any], request_type: type[Any]) -> None:
    endpoint.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        parameters=[
            inspect.Parameter(
                "request",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=request_type,
            )
        ]
    )


def _set_request_response_signature(endpoint: Callable[[Any], Any], request_type: type[Any], response_type: type[Any]) -> None:
    endpoint.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        parameters=[
            inspect.Parameter(
                "request",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=request_type,
            ),
            inspect.Parameter(
                "response",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=response_type,
            ),
        ]
    )


async def _invoke_lambda(request: Any, method: str) -> Any:
    from fastapi.responses import JSONResponse, Response

    body, headers, status_code = await _invoke_lambda_parts(request, method)
    try:
        content = json.loads(body) if body else None
    except json.JSONDecodeError:
        return Response(content=body, status_code=status_code, headers=headers)
    return JSONResponse(content=content, status_code=status_code, headers=headers)


async def _invoke_lambda_json(request: Any, method: str) -> dict[str, Any]:
    body, _headers, status_code = await _invoke_lambda_parts(request, method)
    content = json.loads(body) if body else None
    if not 200 <= status_code < 300:
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=content)
    return content or {}


async def _invoke_lambda_parts(request: Any, method: str) -> tuple[str, dict[str, str], int]:

    raw_body = await request.body()
    event = {
        "rawPath": request.url.path,
        "requestContext": {"http": {"method": method}},
        "headers": dict(request.headers),
        "queryStringParameters": dict(request.query_params),
        "body": raw_body.decode("utf-8") if raw_body else None,
    }
    result = lambda_handler(event, None)
    body = result.get("body", "")
    headers = {key: value for key, value in result.get("headers", {}).items() if key.lower() != "content-length"}
    status_code = int(result.get("statusCode", 200))
    return body, headers, status_code
