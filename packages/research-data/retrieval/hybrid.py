"""
packages/research-data/retrieval/hybrid.py

Hybrid Evidence Retrieval combining BM25 Lexical and Dense Semantic signals (CP-06).
Supports both score-weighted convex combination and Reciprocal Rank Fusion (RRF).
Enforces strict patient-scoping and deterministic tie-breaking.
"""

from __future__ import annotations

from typing import Sequence

from packages.ml_interfaces.query import ClinicalQuery
from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.retrieval.bm25 import EvidenceBM25Retriever
from packages.research_data.retrieval.contract import (
    EvidenceRetriever,
    RetrievalResult,
    filter_patient_evidence,
    sort_and_rank_results,
)
from packages.research_data.retrieval.dense import EvidenceDenseRetriever


def normalize_min_max(scores: list[float]) -> list[float]:
    """
    Score normalization into [0.0, 1.0].
    Uses max-scaling s / max_s so near-identical scores (e.g. 4.9 vs 4.8)
    do not artificially collapse to 1.0 vs 0.0.
    """
    if not scores:
        return []
    max_s = max(scores)
    if max_s > 0.0:
        return [max(0.0, min(1.0, s / max_s)) for s in scores]
    return [0.0 for _ in scores]


class HybridEvidenceRetriever(EvidenceRetriever):
    """
    Hybrid Evidence Retriever combining BM25 lexical search and Dense semantic search.
    Modes:
      - 'weighted': linear combination S = alpha_lexical * S_lex + alpha_dense * S_dense
      - 'rrf': Reciprocal Rank Fusion RRF = 1 / (k + rank_lex) + 1 / (k + rank_dense)
    """

    def __init__(
        self,
        bm25_retriever: EvidenceBM25Retriever | None = None,
        dense_retriever: EvidenceDenseRetriever | None = None,
        alpha_lexical: float = 0.5,
        alpha_dense: float = 0.5,
        mode: str = "weighted",
        rrf_k: int = 60,
    ) -> None:
        self.bm25_retriever = bm25_retriever or EvidenceBM25Retriever()
        self.dense_retriever = dense_retriever or EvidenceDenseRetriever()
        self.alpha_lexical = alpha_lexical
        self.alpha_dense = alpha_dense
        self.mode = mode
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: ClinicalQuery,
        evidence: Sequence[ResearchEvidenceRecord],
        top_k: int = 10,
        patient_id: str | None = None,
    ) -> list[RetrievalResult]:
        target_pid = patient_id or getattr(query, "patient_id", None)
        if not target_pid:
            return []

        patient_records = filter_patient_evidence(evidence, target_pid)
        if not patient_records:
            return []

        # Retrieve full candidate rankings from both components
        bm25_res = self.bm25_retriever.retrieve(
            query, patient_records, top_k=len(patient_records), patient_id=target_pid
        )
        dense_res = self.dense_retriever.retrieve(
            query, patient_records, top_k=len(patient_records), patient_id=target_pid
        )

        bm25_map = {r.evidence_id: r for r in bm25_res}
        dense_map = {r.evidence_id: r for r in dense_res}

        if self.mode == "rrf":
            # Reciprocal Rank Fusion
            results: list[RetrievalResult] = []
            for rec in patient_records:
                eid = rec.id
                rank_bm25 = bm25_map[eid].rank if eid in bm25_map else len(patient_records) + 1
                rank_dense = dense_map[eid].rank if eid in dense_map else len(patient_records) + 1

                rrf_score = (1.0 / (self.rrf_k + rank_bm25)) + (1.0 / (self.rrf_k + rank_dense))

                results.append(
                    RetrievalResult(
                        evidence_id=rec.id,
                        patient_id=rec.source_patient_id,
                        score=float(rrf_score),
                        rank=0,
                        retrieval_method="hybrid_rrf",
                        analyte_canonical=rec.analyte_canonical,
                        concept_id=rec.concept_id,
                        loinc_code=rec.loinc_code,
                        observation_date=rec.observation_date,
                        value=rec.value_numeric if rec.value_numeric is not None else rec.value_text,
                        unit=rec.unit,
                        flag=rec.flag,
                        source_provenance=rec.source_provenance,
                        metadata={
                            "rank_bm25": rank_bm25,
                            "rank_dense": rank_dense,
                            "rrf_score": round(rrf_score, 6),
                        },
                    )
                )
            return sort_and_rank_results(results, top_k=top_k)

        # Weighted combination
        bm25_scores = [bm25_map[r.id].score if r.id in bm25_map else 0.0 for r in patient_records]
        dense_scores = [dense_map[r.id].score if r.id in dense_map else 0.0 for r in patient_records]

        norm_bm25 = normalize_min_max(bm25_scores)
        norm_dense = normalize_min_max(dense_scores)

        results = []
        for idx, rec in enumerate(patient_records):
            s_b = norm_bm25[idx]
            s_d = norm_dense[idx]
            combined = (self.alpha_lexical * s_b) + (self.alpha_dense * s_d)

            results.append(
                RetrievalResult(
                    evidence_id=rec.id,
                    patient_id=rec.source_patient_id,
                    score=float(combined),
                    rank=0,
                    retrieval_method="hybrid",
                    analyte_canonical=rec.analyte_canonical,
                    concept_id=rec.concept_id,
                    loinc_code=rec.loinc_code,
                    observation_date=rec.observation_date,
                    value=rec.value_numeric if rec.value_numeric is not None else rec.value_text,
                    unit=rec.unit,
                    flag=rec.flag,
                    source_provenance=rec.source_provenance,
                    metadata={
                        "bm25_norm": round(s_b, 6),
                        "dense_norm": round(s_d, 6),
                        "raw_bm25": round(bm25_scores[idx], 6),
                        "raw_dense": round(dense_scores[idx], 6),
                        "alpha_lexical": self.alpha_lexical,
                        "alpha_dense": self.alpha_dense,
                    },
                )
            )

        return sort_and_rank_results(results, top_k=top_k)
