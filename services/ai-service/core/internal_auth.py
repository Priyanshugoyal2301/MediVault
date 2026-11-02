"""Service-to-service auth for internal AI endpoints."""

from pathlib import Path
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from packages.shared_utils.service_auth import (
    service_key_is_configured,
    service_key_matches,
)

from .config import Settings, get_settings


def require_internal_key(
    x_internal_key: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = ...,
) -> None:
    """
    Require a configured service key; configuration errors never disable auth.
    """
    expected = (settings.internal_service_key or "").strip()
    if not service_key_is_configured(expected):
        raise HTTPException(503, "Internal authentication is not configured")
    if not service_key_matches(expected, x_internal_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal service key",
        )


def resolve_safe_storage_path(storage_path: str, storage_root: Path) -> Path:
    """Resolve path and ensure it stays under the configured storage root."""
    root = storage_root.resolve()
    candidate = Path(storage_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="storage_path outside allowed storage root",
        ) from exc
    return candidate
