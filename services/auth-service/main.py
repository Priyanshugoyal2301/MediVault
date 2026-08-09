"""
Auth Service — services/auth-service/main.py

Owns user identity, JWT issuance, and session management.
Future hook point: add biometric / ABHA / government-ID strategies here
as additional auth backends without touching health-service or ai-service.
"""

from fastapi import FastAPI

from packages.shared_utils import get_logger

from .routers.auth import router as auth_router

logger = get_logger(__name__)

app = FastAPI(
    title="MediVault AI — Auth Service",
    description="User identity, credentials, JWT issuance. Future: biometric/ID-verification hook point.",
    version="0.1.0",
)

app.include_router(auth_router)


@app.on_event("startup")
async def startup() -> None:
    logger.info("Auth service starting")


@app.get("/health", tags=["ops"])
async def health_check() -> dict:
    """Service liveness probe."""
    return {"status": "ok", "service": "auth-service"}



# ---------------------------------------------------------------------------
# Routers added here as auth feature is built (Feature 1 prerequisite):
#   POST /auth/register
#   POST /auth/login
#   POST /auth/logout
#   GET  /auth/me
# ---------------------------------------------------------------------------
