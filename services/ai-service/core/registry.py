"""
Component registry — resolve ML-swappable interfaces to concrete adapters.

Selection is driven solely by feature flags. When a flag is on but the ML
backend is not yet trained / available, adapters **fall back** to the current
rule-based / statistical implementation so production never hard-fails.
"""

from __future__ import annotations

from functools import lru_cache

from packages.shared_utils import get_logger

from .feature_flags import get_feature_flags

logger = get_logger(__name__)


@lru_cache
def get_document_parser():
    """
    DocumentParser selection:

      USE_UNLIMITED_OCR=0 → RegexDocumentParser (legacy Tesseract+regex)  [DEFAULT]
      USE_UNLIMITED_OCR=1 → FallbackDocumentParser(
                               UnlimitedOCRDocumentParser,
                               RegexDocumentParser,
                            )

    Note: result is process-cached (@lru_cache). Restart ai-service after flag/env changes
    (Phase 1A O-01). Call reset_registry_cache() in tests after monkeypatching env.
    """
    from ..adapters.document_parser import (
        FallbackDocumentParser,
        RegexDocumentParser,
        UnlimitedOCRDocumentParser,
    )

    flags = get_feature_flags()
    if not flags.use_unlimited_ocr:
        logger.info("document_parser=legacy USE_UNLIMITED_OCR=0")
        return RegexDocumentParser()

    try:
        from models.ocr.config_loader import load_config, readiness_check

        cfg = load_config(validate=True)
        ready = readiness_check(cfg)
        logger.info(
            "USE_UNLIMITED_OCR=1 readiness mode=%s ready=%s reason=%s",
            ready.get("mode"),
            ready.get("ready"),
            ready.get("reason"),
        )
        if ready.get("config_summary", {}).get("http_endpoint_configured"):
            logger.info(
                "Unlimited-OCR will send document images to configured HTTP endpoint "
                "(PHI egress — use only trusted private endpoints)"
            )
        primary = UnlimitedOCRDocumentParser(config=cfg)
        logger.info(
            "document_parser=unlimited+legacy_fallback "
            "(empty/error → legacy automatically)"
        )
        return FallbackDocumentParser(primary=primary, fallback=RegexDocumentParser())
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Unlimited-OCR adapter init failed (%s); using legacy only",
            type(exc).__name__,
        )
        return RegexDocumentParser()


@lru_cache
def get_quality_checker():
    """
    QualityChecker selection:

      USE_IMAGE_QUALITY_MODEL=0 → PassThroughQualityChecker [DEFAULT]
      USE_IMAGE_QUALITY_MODEL=1 → FallbackQualityChecker(ML, OpenCV rules)
    """
    from ..adapters.quality_checker import (
        FallbackQualityChecker,
        MLImageQualityChecker,
        OpenCVQualityChecker,
        PassThroughQualityChecker,
    )

    flags = get_feature_flags()
    if not flags.use_image_quality_model:
        logger.info("quality_checker=passthrough USE_IMAGE_QUALITY_MODEL=0")
        return PassThroughQualityChecker()

    try:
        primary = MLImageQualityChecker()
        logger.info(
            "quality_checker=ml USE_IMAGE_QUALITY_MODEL=1 backend=%s",
            getattr(getattr(primary, "_engine", None), "backend_name", "ml"),
        )
        return FallbackQualityChecker(
            primary=primary, fallback=OpenCVQualityChecker()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ML image quality init failed (%s); using OpenCV baseline",
            type(exc).__name__,
        )
        try:
            return OpenCVQualityChecker()
        except Exception:
            return PassThroughQualityChecker()


@lru_cache
def get_normalizer():
    """
    Normalizer selection:

      USE_ML_NORMALIZER=0 → AliasNormalizer (rule-based)  [DEFAULT]
      USE_ML_NORMALIZER=1 → FallbackNormalizer(ML MedicalTestNormalizer, Alias)
    """
    from ..adapters.normalizer import (
        AliasNormalizer,
        FallbackNormalizer,
        MLMedicalTestNormalizer,
    )

    flags = get_feature_flags()
    if not flags.use_ml_normalizer:
        logger.info("normalizer=alias_rules USE_ML_NORMALIZER=0")
        return AliasNormalizer()

    try:
        primary = MLMedicalTestNormalizer()
        logger.info(
            "normalizer=ml+rule_fallback USE_ML_NORMALIZER=1 backend=%s",
            getattr(getattr(primary, "_engine", None), "backend_name", "ml"),
        )
        return FallbackNormalizer(primary=primary, fallback=AliasNormalizer())
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ML normalizer init failed (%s); using alias rules only",
            type(exc).__name__,
        )
        return AliasNormalizer()


@lru_cache
def get_anomaly_detector():
    """
    AnomalyDetector selection:

      USE_ANOMALY_MODEL=0 and USE_OUTLIER_MODEL=0 → StatisticalAnomalyDetector [DEFAULT]
      either flag=1 → FallbackAnomalyDetector(ML IsolationForest, Statistical)
    """
    from ..adapters.anomaly_detector import (
        FallbackAnomalyDetector,
        MLAnomalyDetector,
        StatisticalAnomalyDetector,
    )

    flags = get_feature_flags()
    ml_on = flags.use_anomaly_model or flags.use_outlier_model
    if not ml_on:
        logger.info("anomaly_detector=statistical USE_ANOMALY_MODEL=0")
        return StatisticalAnomalyDetector()

    try:
        primary = MLAnomalyDetector()
        logger.info(
            "anomaly_detector=ml+stats_fallback USE_ANOMALY_MODEL=1 backend=%s",
            getattr(getattr(primary, "_engine", None), "backend_name", "ml"),
        )
        return FallbackAnomalyDetector(
            primary=primary, fallback=StatisticalAnomalyDetector()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ML anomaly init failed (%s); using statistical only",
            type(exc).__name__,
        )
        return StatisticalAnomalyDetector()


@lru_cache
def get_retriever():
    """
    Retriever selection:

      USE_EMBEDDING_SEARCH=0 → BM25Retriever  [DEFAULT]
      USE_EMBEDDING_SEARCH=1 → FallbackRetriever(Semantic, BM25)
    """
    from ..adapters.retriever import (
        BM25Retriever,
        FallbackRetriever,
        SemanticRetrieverAdapter,
    )

    flags = get_feature_flags()
    if not flags.use_embedding_search:
        logger.info("retriever=bm25 USE_EMBEDDING_SEARCH=0")
        return BM25Retriever()

    try:
        primary = SemanticRetrieverAdapter()
        logger.info(
            "retriever=semantic+bm25_fallback USE_EMBEDDING_SEARCH=1 backend=%s store=%s",
            getattr(getattr(primary, "_engine", None), "backend_name", "semantic"),
            getattr(getattr(primary, "_engine", None), "store_name", "?"),
        )
        return FallbackRetriever(primary=primary, fallback=BM25Retriever())
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Semantic retriever init failed (%s); using BM25 only",
            type(exc).__name__,
        )
        return BM25Retriever()


@lru_cache
def get_risk_predictor():
    """
    RiskPredictor selection:

      USE_RISK_MODEL=0 and USE_DISEASE_RISK_MODEL=0 → UnavailableRiskPredictor [DEFAULT]
      either flag=1 → FallbackRiskPredictor(MLDiseaseRiskPredictor, Unavailable)
    """
    from ..adapters.risk_predictor import (
        FallbackRiskPredictor,
        MLDiseaseRiskPredictor,
        UnavailableRiskPredictor,
    )

    flags = get_feature_flags()
    if not flags.use_risk_model:
        logger.info("risk_predictor=unavailable USE_RISK_MODEL=0")
        return UnavailableRiskPredictor()

    try:
        primary = MLDiseaseRiskPredictor()
        logger.info(
            "risk_predictor=ml_disease USE_RISK_MODEL=1 backend=%s",
            getattr(getattr(primary, "_engine", None), "backend_name", "ml"),
        )
        return FallbackRiskPredictor(
            primary=primary, fallback=UnavailableRiskPredictor()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ML risk init failed (%s); remaining unavailable",
            type(exc).__name__,
        )
        return UnavailableRiskPredictor()


@lru_cache
def get_biomarker_forecaster():
    """
    BiomarkerForecaster selection:

      USE_FORECAST_MODEL=0 → UnavailableBiomarkerForecaster [DEFAULT]
      USE_FORECAST_MODEL=1 → FallbackBiomarkerForecaster(ML, Unavailable)
    """
    from ..adapters.biomarker_forecaster import (
        FallbackBiomarkerForecaster,
        MLBiomarkerForecaster,
        UnavailableBiomarkerForecaster,
    )

    flags = get_feature_flags()
    if not flags.use_forecast_model:
        logger.info("biomarker_forecaster=unavailable USE_FORECAST_MODEL=0")
        return UnavailableBiomarkerForecaster()

    try:
        primary = MLBiomarkerForecaster()
        logger.info(
            "biomarker_forecaster=ml USE_FORECAST_MODEL=1 backend=%s",
            getattr(getattr(primary, "_engine", None), "backend_name", "ml"),
        )
        return FallbackBiomarkerForecaster(
            primary=primary, fallback=UnavailableBiomarkerForecaster()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ML forecaster init failed (%s); remaining unavailable",
            type(exc).__name__,
        )
        return UnavailableBiomarkerForecaster()


@lru_cache
def get_health_scorer():
    """
    HealthScorer selection:

      USE_HEALTH_SCORE_MODEL=0 → UnavailableHealthScorer [DEFAULT]
      USE_HEALTH_SCORE_MODEL=1 → FallbackHealthScorer(ML, Unavailable)
    """
    from ..adapters.health_scorer import (
        FallbackHealthScorer,
        MLHealthScorer,
        UnavailableHealthScorer,
    )

    flags = get_feature_flags()
    if not flags.use_health_score_model:
        logger.info("health_scorer=unavailable USE_HEALTH_SCORE_MODEL=0")
        return UnavailableHealthScorer()

    try:
        primary = MLHealthScorer()
        logger.info(
            "health_scorer=ml USE_HEALTH_SCORE_MODEL=1 backend=%s",
            getattr(getattr(primary, "_engine", None), "backend_name", "ml"),
        )
        return FallbackHealthScorer(primary=primary, fallback=UnavailableHealthScorer())
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ML health scorer init failed (%s); remaining unavailable",
            type(exc).__name__,
        )
        return UnavailableHealthScorer()


def reset_registry_cache() -> None:
    """Test helper."""
    get_document_parser.cache_clear()
    get_quality_checker.cache_clear()
    get_normalizer.cache_clear()
    get_anomaly_detector.cache_clear()
    get_retriever.cache_clear()
    get_risk_predictor.cache_clear()
    get_biomarker_forecaster.cache_clear()
    get_health_scorer.cache_clear()
