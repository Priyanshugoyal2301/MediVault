"""
packages/research-data/retrieval/__init__.py

Longitudinal Evidence Retrieval Engine (CP-06).
Provides lexical (BM25), dense semantic, hybrid, temporal reranking, clinical concept matching,
and modular scoring pipelines for atomic Evidence Observations.
"""

from .bm25 import EvidenceBM25Index, EvidenceBM25Retriever, format_evidence_lexical_doc
from .concept import ConceptScorer
from .contract import (
    EvidenceRetriever,
    RetrievalResult,
    filter_patient_evidence,
    sort_and_rank_results,
)
from .dense import DenseEmbeddingBackend, EvidenceDenseRetriever, format_evidence_dense_doc
from .hybrid import HybridEvidenceRetriever
from .pipeline import ModularEvidenceRetriever, ScoringWeights
from .temporal import TemporalScorer
from .trajectory import (
    TrajectoryBlock,
    build_trajectories,
    calculate_inflection_point,
    calculate_trajectory_features,
)
from .trajectory_reranker import TrajectoryAwareRetriever, TrajectoryReranker
from .longitudinal_selection import (
    LongitudinalEvidencePackage,
    LongitudinalEvidenceSelector,
)

__all__ = [
    "ConceptScorer",
    "DenseEmbeddingBackend",
    "EvidenceBM25Index",
    "EvidenceBM25Retriever",
    "EvidenceDenseRetriever",
    "EvidenceRetriever",
    "HybridEvidenceRetriever",
    "LongitudinalEvidencePackage",
    "LongitudinalEvidenceSelector",
    "ModularEvidenceRetriever",
    "RetrievalResult",
    "ScoringWeights",
    "TemporalScorer",
    "TrajectoryAwareRetriever",
    "TrajectoryBlock",
    "TrajectoryReranker",
    "build_trajectories",
    "calculate_inflection_point",
    "calculate_trajectory_features",
    "filter_patient_evidence",
    "format_evidence_dense_doc",
    "format_evidence_lexical_doc",
    "sort_and_rank_results",
]`n