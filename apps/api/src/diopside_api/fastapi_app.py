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

    _set_request_signature(health, Request)
    _set_request_signature(config, Request)
    _set_request_signature(home, Request)
    _set_request_signature(videos, Request)
    _set_request_signature(tags, Request)

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

    native_paths = {("GET", "/api/health"), ("GET", "/api/config"), ("GET", "/api/home"), ("GET", "/api/videos"), ("GET", "/api/tags")}
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
