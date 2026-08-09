"""
Health Service — services/health-service/main.py

Owns reports, extracted values, timeline events, and user health data CRUD.
Privacy enforcement point: every query is scoped to owner_id at the DB layer.
"""

from fastapi import FastAPI

from packages.shared_utils import get_logger

from .routers.reports import router as reports_router
from .routers.timeline import router as timeline_router

logger = get_logger(__name__)

app = FastAPI(
    title="MediVault AI — Health Service",
    description="Reports, timeline, user health data CRUD, and data-ownership enforcement.",
    version="0.1.0",
)

app.include_router(reports_router)
app.include_router(timeline_router)


@app.on_event("startup")
async def startup() -> None:
    logger.info("Health service starting")


@app.get("/health", tags=["ops"])
async def health_check() -> dict:
    return {"status": "ok", "service": "health-service"}



# ---------------------------------------------------------------------------
# Routers registered:
#   POST   /reports                           (Feature 1)
#   GET    /reports                           (Feature 1)
#   GET    /reports/{report_id}               (Feature 1)
#   DELETE /reports/{report_id}               (Feature 1 — cascade: file+DB+timeline)
#   GET    /timeline                          (Feature 2)
#   GET    /timeline/{test_name}              (Feature 2)
# ---------------------------------------------------------------------------
