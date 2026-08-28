"""
ml-interfaces — protocol contracts for ML-swappable MediVault components.

Existing rule-based / statistical implementations are the *default* adapters.
ML models plug in behind the same Protocols; feature flags select the backend.

Import:

    from packages.ml_interfaces import (
        DocumentParser,
        RiskPredictor,
        Retriever,
        Normalizer,
        HealthScorer,
        AnomalyDetector,
        QualityChecker,
    )
"""

from .biomarker_forecaster import BiomarkerForecaster
from .anomaly_detector import AnomalyDetector
from .document_parser import DocumentParser
from .health_scorer import HealthScorer
from .normalizer import Normalizer
from .quality_checker import QualityChecker
from .retriever import Retriever
from .risk_predictor import RiskPredictor
from .types import (
    AnomalyDetectionResult,
    BiomarkerForecast,
    BiomarkerForecastBatch,
    HealthScoreResult,
    ParsedField,
    QualityCheckResult,
    RetrievedDocument,
    RiskPredictionResult,
)

__all__ = [
    "AnomalyDetector",
    "AnomalyDetectionResult",
    "BiomarkerForecast",
    "BiomarkerForecastBatch",
    "BiomarkerForecaster",
    "DocumentParser",
    "HealthScoreResult",
    "HealthScorer",
    "Normalizer",
    "ParsedField",
    "QualityCheckResult",
    "QualityChecker",
    "RetrievedDocument",
    "Retriever",
    "RiskPredictionResult",
    "RiskPredictor",
]
