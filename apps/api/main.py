"""
API Gateway / BFF — apps/api/main.py

Routes client requests to downstream services.
No business logic lives here.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MediVault AI — API Gateway",
    description="Backend-for-Frontend: routes web client requests to auth, health, and ai services.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: lock down to actual frontend origin before prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
async def health_check() -> dict:
    """Service liveness probe."""
    return {"status": "ok", "service": "api-gateway"}


# ---------------------------------------------------------------------------
# Routes are added here as each downstream service is built.
# Pattern: import a router from apps/api/routers/<service>.py and include it.
# ---------------------------------------------------------------------------
