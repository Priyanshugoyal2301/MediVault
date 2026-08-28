"""
AI Service — services/ai-service/main.py

Owns: report OCR + parsing, anomaly detection, RAG Q&A, deterministic safety layer.

SAFETY RULE (mandatory — do not refactor away):
  On every /qa request, the deterministic safety layer (rule-based keyword/pattern
  check) MUST run BEFORE any LLM/RAG call. If a red-flag pattern matches, the fixed
  emergency-guidance message is returned immediately without invoking the model.
"""

from fastapi import FastAPI

from packages.shared_utils import get_logger

try:
    from .routers.anomaly import router as anomaly_router
    from .routers.embed_report import router as embed_report_router
    from .routers.parse import router as parse_router
    from .routers.qa import router as qa_router
    from .rag.bootstrap import bootstrap_knowledge_base
    from .rag.retriever import knowledge_base_stats
except ImportError:  # flat layout
    from routers.anomaly import router as anomaly_router
    from routers.embed_report import router as embed_report_router
    from routers.parse import router as parse_router
    from routers.qa import router as qa_router
    from rag.bootstrap import bootstrap_knowledge_base
    from rag.retriever import knowledge_base_stats

logger = get_logger(__name__)

app = FastAPI(
    title="MediVault AI — AI Service",
    description="OCR, parsing, anomaly, template RAG. Internal use only.",
    version="0.2.0",
)

app.include_router(parse_router)
app.include_router(anomaly_router)
app.include_router(qa_router)
app.include_router(embed_report_router)

_kb_status: dict = {
    "kb_chunks": 0,
    "kb_embedder": "none",
    "kb_retriever": "none",
    "kb_ready": False,
}


@app.on_event("startup")
async def startup() -> None:
    global _kb_status
    logger.info("AI service starting — bootstrapping knowledge base")
    try:
        _kb_status = bootstrap_knowledge_base()
    except Exception as exc:  # noqa: BLE001
        logger.error("KB bootstrap failed: %s", type(exc).__name__)
        _kb_status = {
            "kb_chunks": 0,
            "kb_embedder": "error",
            "kb_retriever": "error",
            "kb_ready": False,
        }

    # Phase 1A: OCR readiness log (no weight download)
    try:
        from .core.feature_flags import get_feature_flags
        from models.ocr.config_loader import readiness_check

        flags = get_feature_flags()
        if flags.use_unlimited_ocr:
            ready = readiness_check()
            logger.info(
                "Unlimited-OCR readiness ready=%s mode=%s reason=%s "
                "(restart service after flag/env changes)",
                ready.get("ready"),
                ready.get("mode"),
                ready.get("reason"),
            )
        else:
            logger.info("Unlimited-OCR disabled (USE_UNLIMITED_OCR=0) — legacy parser default")
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR readiness check skipped: %s", type(exc).__name__)


@app.get("/health", tags=["ops"])
async def health_check() -> dict:
    stats = knowledge_base_stats()
    try:
        from .core.feature_flags import flags_as_dict, get_feature_flags
    except ImportError:
        from core.feature_flags import flags_as_dict, get_feature_flags  # type: ignore

    ocr_status: dict = {"enabled": False, "ready": True, "mode": "legacy"}
    try:
        flags = get_feature_flags()
        if flags.use_unlimited_ocr:
            from models.ocr.config_loader import readiness_check

            ocr_status = {"enabled": True, **readiness_check()}
        else:
            ocr_status = {
                "enabled": False,
                "ready": True,
                "mode": "legacy",
                "reason": "USE_UNLIMITED_OCR=0",
            }
    except Exception as exc:  # noqa: BLE001
        ocr_status = {"enabled": None, "ready": False, "mode": "error", "reason": type(exc).__name__}

    return {
        "status": "ok",
        "service": "ai-service",
        "kb_ready": stats.get("kb_ready", False),
        "kb_chunks": stats.get("kb_chunks", 0),
        "kb_retriever": stats.get(
            "kb_retriever", _kb_status.get("kb_retriever", "unknown")
        ),
        "kb_embedder": _kb_status.get("kb_embedder", "unknown"),
        "ml_feature_flags": flags_as_dict(),
        "unlimited_ocr": ocr_status,
    }
