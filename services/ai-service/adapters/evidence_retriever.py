"""
services/ai-service/adapters/evidence_retriever.py

Adapter boundary for Longitudinal Evidence Retrieval (CP-06).
Provides a decoupled service adapter bridging ClinicalQuery parsing (CP-05)
and Evidence Observation retrieval (CP-06) for AI Service components.

Does NOT replace existing Q&A knowledge-base retrieval.
Does NOT introduce hard sentence-transformers or LLM dependencies into production APIs.
"""

from __future__ import annotations

from typing import Any, Sequence

from packages.ml_interfaces.query import ClinicalQuery
from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.retrieval.contract import EvidenceRetriever, RetrievalResult
from packages.research_data.retrieval.pipeline import ModularEvidenceRetriever, ScoringWeights
from services.ai_service.rag.query_understanding import ClinicalQueryParser


class LongitudinalEvidenceRetrieverAdapter:
    """
    Adapter bridging query understanding with longitudinal evidence retrieval.
    Can be used by routers or downstream explanation generators to fetch
    evidence observations for a specific patient.
    """

    def __init__(
        self,
        retriever: EvidenceRetriever | None = None,
        query_parser: ClinicalQueryParser | None = None,
    ) -> None:
        self.retriever = retriever or ModularEvidenceRetriever(
            weights=ScoringWeights.hybrid_temporal_concept(),
            method_name="Hybrid+Temporal+Concept",
        )
        self.query_parser = query_parser or ClinicalQueryParser()

    def retrieve_for_patient(
        self,
        query: str | ClinicalQuery,
        evidence: Sequence[ResearchEvidenceRecord],
        patient_id: str,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """
        Retrieves top-k evidence observations for a specific patient.
        Guarantees strict patient isolation.
        """
        if isinstance(query, str):
            c_query = self.query_parser.parse(query)
            setattr(c_query, "patient_id", patient_id)
        else:
            c_query = query
            if not getattr(c_query, "patient_id", None):
                setattr(c_query, "patient_id", patient_id)

        return self.retriever.retrieve(
            query=c_query,
            evidence=evidence,
            top_k=top_k,
            patient_id=patient_id,
        )
