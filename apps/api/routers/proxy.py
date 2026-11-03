"""
Reverse-proxy routes: browser → BFF (JWT) → auth/health services.

AI service is intentionally NOT proxied.
"""

from typing import Annotated
import ipaddress

import httpx
import json
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from core.auth import require_user_id
from core.config import Settings, get_settings
from packages.shared_utils.service_auth import service_key_is_configured

router = APIRouter(tags=["proxy"])


@router.api_route("/care/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_care(path: str, request: Request,
                     settings: Annotated[Settings, Depends(get_settings)],
                     user_id: Annotated[str, Depends(require_user_id)]) -> Response:
    return await _forward(request, settings.health_service_base_url, f"/care/{path}",
                          user_id=user_id, internal_service_key=settings.internal_service_key)

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
        if lk in _HOP_BY_HOP or lk in {
            "x-user-id",
            "x-internal-key",
            "x-user-role",
            "x-doctor-verified",
            "cookie",
            "x-auth-client-ip",
            "cf-connecting-ip",
        }:
            continue
        out[key] = value
    return out


async def _forward(
    request: Request,
    upstream_base: str,
    path: str,
    *,
    user_id: str | None = None,
    internal_service_key: str = "",
    auth_client_ip: str | None = None,
) -> Response:
    url = f"{upstream_base.rstrip('/')}/{path.lstrip('/')}"
    headers = _filter_request_headers(request)
    if auth_client_ip:
        headers["X-Auth-Client-IP"] = auth_client_ip
    if user_id is not None:
        if not service_key_is_configured(internal_service_key):
            return JSONResponse(
                status_code=503,
                content={"detail": "Internal authentication is not configured"},
            )
        headers["X-User-ID"] = user_id
        headers["X-Internal-Key"] = internal_service_key.strip()

    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 21 * 1024 * 1024:
            return JSONResponse(status_code=413, content={"detail": "Request too large (maximum 20 MB document)"})
        chunks.append(chunk)
    body = b"".join(chunks)
    if request.cookies.get("medivault_session"):
        headers["Authorization"] = "Bearer " + request.cookies["medivault_session"]
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            upstream = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=request.query_params,
            )
    except httpx.RequestError:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Upstream service unavailable",
            },
        )

    response_headers = {
        k: v
        for k, v in upstream.headers.items()
        if k.lower() not in _HOP_BY_HOP and k.lower() != "content-encoding"
    }
    response_headers["cache-control"] = "no-store"
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
    if request.method not in ("GET", "HEAD") and request.headers.get("origin") not in settings.cors_origin_list:
        # Non-browser API clients may use bearer credentials without cookie auth.
        if request.cookies.get("medivault_session") or request.headers.get("origin"):
            return JSONResponse(status_code=403, content={"detail": "Request origin is not allowed"})
    auth_client_ip = None
    if path == "login":
        candidate = request.headers.get("cf-connecting-ip") if settings.trust_cf_connecting_ip else None
        if not candidate and request.client:
            candidate = request.client.host
        try:
            auth_client_ip = str(ipaddress.ip_address(candidate)) if candidate else None
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid client address"})
        if not auth_client_ip:
            return JSONResponse(status_code=503, content={"detail": "Sign-in rate limiting is unavailable"})
    response = await _forward(request, settings.auth_service_base_url, f"/auth/{path}", auth_client_ip=auth_client_ip)
    if path in ("login", "register") and response.status_code in (200, 201):
        data = json.loads(response.body)
        response = JSONResponse({"authenticated": True}, status_code=response.status_code,
                                headers={"Cache-Control": "no-store"})
        response.set_cookie("medivault_session", data["access_token"], httponly=True,
                            secure=settings.cookie_secure, samesite="strict", path="/")
    if path == "logout" and response.status_code == 204:
        response.delete_cookie("medivault_session", path="/", secure=settings.cookie_secure, httponly=True, samesite="strict")
    return response


@router.api_route("/reports", methods=["GET", "POST"])
@router.api_route("/reports/{path:path}", methods=["GET", "POST", "DELETE", "PUT", "PATCH"])
async def proxy_reports(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: Annotated[str, Depends(require_user_id)],
    path: str = "",
) -> Response:
    target = f"/reports/{path}" if path else "/reports"
    return await _forward(
        request, settings.health_service_base_url, target,
        user_id=user_id, internal_service_key=settings.internal_service_key,
    )


@router.api_route("/timeline", methods=["GET"])
@router.api_route("/timeline/{path:path}", methods=["GET", "POST"])
async def proxy_timeline(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: Annotated[str, Depends(require_user_id)],
    path: str = "",
) -> Response:
    target = f"/timeline/{path}" if path else "/timeline"
    return await _forward(
        request, settings.health_service_base_url, target,
        user_id=user_id, internal_service_key=settings.internal_service_key,
    )


@router.api_route("/qa", methods=["POST"])
@router.api_route("/qa/{path:path}", methods=["POST", "GET"])
async def proxy_qa(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: Annotated[str, Depends(require_user_id)],
    path: str = "",
) -> Response:
    target = f"/qa/{path}" if path else "/qa"
    return await _forward(
        request, settings.health_service_base_url, target,
        user_id=user_id, internal_service_key=settings.internal_service_key,
    )
