"""JWT validation for the API gateway (BFF)."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=True)


def require_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
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
        )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        UUID(str(sub))
        return str(sub)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
