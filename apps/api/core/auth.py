"""JWT validation for the API gateway (BFF)."""

from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=True)


async def browser_credentials(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    token = request.cookies.get("medivault_session")
    if token:
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("origin") not in settings.cors_origin_list:
            raise HTTPException(403, "Request origin is not allowed")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return await _bearer(request)


async def require_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(browser_credentials)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """
    Decode Bearer JWT and return the user id (sub).
    Never trust a client-supplied X-User-ID — that header is stripped and
    re-injected by the proxy using this value.
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.auth_secret_key,
            algorithms=[settings.auth_algorithm],
            options={"require_exp": True, "require_sub": True, "require_iat": True},
        )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        UUID(str(sub))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Check current account state on every protected request. A previously
    # issued token must not keep a deactivated account authorized until expiry.
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.auth_service_base_url}/auth/me",
                headers={"Authorization": f"Bearer {credentials.credentials}"},
            )
        if response.status_code in (401, 403, 404):
            raise HTTPException(401, "Invalid token or inactive account")
        if response.status_code != 200:
            raise HTTPException(503, "Authentication service unavailable")
        profile = response.json()
        if not isinstance(profile, dict) or profile.get("id") != str(sub):
            raise HTTPException(401, "Invalid account identity")
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Authentication service unavailable") from None
    return str(sub)
