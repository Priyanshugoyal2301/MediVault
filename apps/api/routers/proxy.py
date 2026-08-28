"""
Reverse-proxy routes: browser → BFF (JWT) → auth/health services.

AI service is intentionally NOT proxied.
"""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from core.auth import require_user_id
from core.config import Settings, get_settings

router = APIRouter(tags=["proxy"])

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def _filter_request_headers(request: Request) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in request.headers.items():
        lk = key.lower()
        if lk in _HOP_BY_HOP or lk == "x-user-id":
            continue
        out[key] = value
    return out


async def _forward(
    request: Request,
    upstream_base: str,
    path: str,
    *,
    user_id: str | None = None,
) -> Response:
    url = f"{upstream_base.rstrip('/')}/{path.lstrip('/')}"
    headers = _filter_request_headers(request)
    if user_id is not None:
        headers["X-User-ID"] = user_id

    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            upstream = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=request.query_params,
            )
    except httpx.RequestError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Upstream service unavailable",
                "upstream": upstream_base,
                "error": type(exc).__name__,
            },
        )

    response_headers = {
        k: v
        for k, v in upstream.headers.items()
        if k.lower() not in _HOP_BY_HOP and k.lower() != "content-encoding"
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


@router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_auth(
    path: str,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    return await _forward(request, settings.auth_service_url, f"/auth/{path}")


@router.api_route("/reports", methods=["GET", "POST"])
@router.api_route("/reports/{path:path}", methods=["GET", "POST", "DELETE", "PUT", "PATCH"])
async def proxy_reports(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: Annotated[str, Depends(require_user_id)],
    path: str = "",
) -> Response:
    target = f"/reports/{path}" if path else "/reports"
    return await _forward(request, settings.health_service_url, target, user_id=user_id)


@router.api_route("/timeline", methods=["GET"])
@router.api_route("/timeline/{path:path}", methods=["GET", "POST"])
async def proxy_timeline(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: Annotated[str, Depends(require_user_id)],
    path: str = "",
) -> Response:
    target = f"/timeline/{path}" if path else "/timeline"
    return await _forward(request, settings.health_service_url, target, user_id=user_id)


@router.api_route("/qa", methods=["POST"])
@router.api_route("/qa/{path:path}", methods=["POST", "GET"])
async def proxy_qa(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: Annotated[str, Depends(require_user_id)],
    path: str = "",
) -> Response:
    target = f"/qa/{path}" if path else "/qa"
    return await _forward(request, settings.health_service_url, target, user_id=user_id)
