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
    except ModuleNotFoundError as exc:  # pragma: no cover - optional runtime dependency.
        raise RuntimeError("FastAPI adapter requires the optional 'fastapi' package.") from exc

    app = FastAPI(title="diopside API", version="v0.4-contract")

    def custom_openapi() -> dict[str, Any]:
        return build_openapi_contract()

    app.openapi = custom_openapi  # type: ignore[method-assign]

    for route in all_route_contracts():
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

    endpoint.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        parameters=[
            inspect.Parameter(
                "request",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=request_type,
            )
        ]
    )
    return endpoint


async def _invoke_lambda(request: Any, method: str) -> Any:
    from fastapi.responses import JSONResponse, Response

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
    try:
        content = json.loads(body) if body else None
    except json.JSONDecodeError:
        return Response(content=body, status_code=status_code, headers=headers)
    return JSONResponse(content=content, status_code=status_code, headers=headers)
