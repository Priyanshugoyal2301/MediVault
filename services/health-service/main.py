"""
Health Service — services/health-service/main.py

Owns reports, extracted values, timeline events, and user health data CRUD.
Privacy enforcement point: every query is scoped to owner_id at the DB layer.
"""

from fastapi import Depends, FastAPI
import asyncio
from contextlib import asynccontextmanager, suppress


@asynccontextmanager
async def lifespan(app):
    from .care.worker import worker_loop
    task = asyncio.create_task(worker_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


from packages.shared_utils import get_logger

try:
    from .care.router import router as care_router
    from .care.prescription_review import router as prescription_review_router
    from .care.storage_usage import router as storage_router
    from .core.internal_auth import require_internal_key
    from .routers.qa import router as qa_router
    from .routers.reports import router as reports_router
    from .routers.timeline import router as timeline_router
except ImportError:  # flat layout (Docker / `cd services/health-service`)
    from core.internal_auth import require_internal_key
    from routers.qa import router as qa_router
    from routers.reports import router as reports_router
    from routers.timeline import router as timeline_router

logger = get_logger(__name__)

app = FastAPI(
    lifespan=lifespan,
    title="MediVault AI — Health Service",
    description="Reports, timeline, user health data CRUD, and data-ownership enforcement.",
    version="0.1.0",
)

app.include_router(reports_router, dependencies=[Depends(require_internal_key)])
app.include_router(care_router, dependencies=[Depends(require_internal_key)])
app.include_router(prescription_review_router, dependencies=[Depends(require_internal_key)])
app.include_router(storage_router, dependencies=[Depends(require_internal_key)])
app.include_router(timeline_router, dependencies=[Depends(require_internal_key)])
app.include_router(qa_router, dependencies=[Depends(require_internal_key)])


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
#   POST   /qa                               (Feature 3 — proxy to ai-service)
# ---------------------------------------------------------------------------
