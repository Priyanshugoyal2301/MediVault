"""Authenticate gateway calls before trusting the injected owner identity."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from packages.shared_utils.service_auth import (
    service_key_is_configured,
    service_key_matches,
)

from .config import Settings, get_settings


def require_internal_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_internal_key: Annotated[str | None, Header()] = None,
) -> None:
    if not service_key_is_configured(settings.internal_service_key):
        raise HTTPException(503, "Internal authentication is not configured")
    if not service_key_matches(settings.internal_service_key, x_internal_key):
        raise HTTPException(401, "Invalid or missing internal service key")
