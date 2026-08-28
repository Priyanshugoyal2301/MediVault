"""
API Gateway / BFF — apps/api/main.py

Run (from apps/api): uvicorn main:app --reload --port 8000
Requires AUTH_SECRET_KEY in environment / .env (shared with auth-service).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from routers.proxy import router as proxy_router

try:
    settings = get_settings()
except Exception as exc:  # noqa: BLE001
    raise RuntimeError(
        "API gateway failed to load settings. Copy .env.example → .env and set "
        "AUTH_SECRET_KEY (must match auth-service). Original error: "
        f"{type(exc).__name__}: {exc}"
    ) from exc

app = FastAPI(
    title="MediVault AI — API Gateway",
    description=(
        "Backend-for-Frontend: JWT validation + trusted X-User-ID injection. "
        "AI service is internal-only and not routed here."
    ),
    version="0.2.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proxy_router)


@app.get("/health", tags=["ops"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "api-gateway",
        "version": "0.2.1",
        "auth_service_url": settings.auth_service_url,
        "health_service_url": settings.health_service_url,
    }
