"""
AI Service — services/ai-service/main.py

Owns: report OCR + parsing, anomaly detection, RAG Q&A, deterministic safety layer.

SAFETY RULE (mandatory — do not refactor away):
  On every /qa request, the deterministic safety layer (rule-based keyword/pattern
  check) MUST run BEFORE any LLM call. If a red-flag pattern matches, the fixed
  emergency-guidance message is returned immediately without invoking the LLM.
OCR, report parsing, plain-language explanation generation.
Internal endpoints only — not exposed through the API gateway directly.
"""

from fastapi import FastAPI

from packages.shared_utils import get_logger

from .routers.anomaly import router as anomaly_router
from .routers.embed_report import router as embed_report_router
from .routers.parse import router as parse_router
from .routers.qa import router as qa_router

logger = get_logger(__name__)

app = FastAPI(
    title="MediVault AI — AI Service",
    description="OCR, parsing, explanation generation. Internal use only.",
    version="0.1.0",
)

app.include_router(parse_router)
app.include_router(anomaly_router)
app.include_router(qa_router)
app.include_router(embed_report_router)


@app.on_event("startup")
async def startup() -> None:
    logger.info("AI service starting")


@app.get("/health", tags=["ops"])
async def health_check() -> dict:
    return {"status": "ok", "service": "ai-service"}


# ---------------------------------------------------------------------------
# Routers registered:
#   POST   /parse                             (Feature 1)
#   POST   /anomaly/detect                    (Feature 2)
#   POST   /qa                                (Feature 3 — safety layer runs first)
#   POST   /embed-report                      (Feature 3)
#   DELETE /embeddings/{owner_id}/{report_id}  (Feature 3)
# ---------------------------------------------------------------------------
