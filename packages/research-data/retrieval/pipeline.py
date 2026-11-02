"""
packages/research-data/retrieval/pipeline.py

Modular Evidence Retrieval Pipeline and Scoring Orchestrator (CP-06).
Combines Lexical (BM25), Semantic (Dense), Clinical Concept, Temporal, and Intent signals:

    S = alpha * S_lexical + beta * S_semantic + gamma * S_concept + delta * S_temporal + epsilon * S_intent

Supports the primary experimental progression:
  A. BM25
  B. Dense
  C. Hybrid
  D. Hybrid + Temporal
  E. Hybrid + Temporal + Concept
  F. Full Scoring
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from packages.ml_interfaces.query import ClinicalQuery, QueryIntent
from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.retrieval.bm25 import EvidenceBM25Retriever
from packages.research_data.retrieval.concept import ConceptScorer
from packages.research_data.retrieval.contract import (
    EvidenceRetriever,
    RetrievalResult,
    filter_patient_evidence,
    sort_and_rank_results,
)
from packages.research_data.retrieval.dense import EvidenceDenseRetriever
from packages.research_data.retrieval.hybrid import normalize_min_max
from packages.research_data.retrieval.temporal import TemporalScorer


def is_clinically_abnormal(record: ResearchEvidenceRecord) -> bool:
    """Evaluates whether an observation exceeds clinical reference thresholds."""
    if record.flag and record.flag.lower() in ("abnormal", "high", "low"):
        return True
    val = record.value_numeric
    if val is None:
        return False
    if record.reference_high is not None and val > record.reference_high:
        return True
    if record.reference_low is not None and val < record.reference_low:
        return True

    analyte = record.analyte_canonical or record.analyte_raw
    if analyte == "LDL Cholesterol":
        return val >= 130.0
    elif analyte == "Total Cholesterol":
        return val >= 200.0
    elif analyte == "Triglycerides":
        return val >= 150.0
    elif analyte == "HDL Cholesterol":
        return val < 40.0
    elif analyte == "HbA1c":
        return val >= 6.5
    elif analyte == "Glucose":
        return val >= 100.0
    elif analyte == "Haemoglobin":
        return val < 12.0 or val > 17.5
    elif analyte == "WBC":
        return val < 4000.0 or val > 11000.0
    elif analyte == "Platelets":
        return val < 150000.0 or val > 450000.0
    elif analyte == "Creatinine":
        return val > 1.2
    elif analyte == "TSH":
        return val < 0.4 or val > 4.0
    return False


@dataclass
class ScoringWeights:
    """Weights for the modular retrieval scoring formula."""
    alpha_lexical: float = 0.25
    beta_semantic: float = 0.25
    gamma_concept: float = 0.25
    delta_temporal: float = 0.25
    epsilon_intent: float = 0.0

    @classmethod
    def bm25(cls) -> ScoringWeights:
        return cls(alpha_lexical=1.0, beta_semantic=0.0, gamma_concept=0.0, delta_temporal=0.0, epsilon_intent=0.0)

    @classmethod
    def dense(cls) -> ScoringWeights:
        return cls(alpha_lexical=0.0, beta_semantic=1.0, gamma_concept=0.0, delta_temporal=0.0, epsilon_intent=0.0)

    @classmethod
    def hybrid(cls) -> ScoringWeights:
        return cls(alpha_lexical=0.5, beta_semantic=0.5, gamma_concept=0.0, delta_temporal=0.0, epsilon_intent=0.0)

    @classmethod
    def hybrid_temporal(cls) -> ScoringWeights:
        return cls(alpha_lexical=0.35, beta_semantic=0.35, gamma_concept=0.0, delta_temporal=0.30, epsilon_intent=0.0)

    @classmethod
    def rrf(cls) -> ScoringWeights:
        return cls(alpha_lexical=0.5, beta_semantic=0.5, gamma_concept=0.0, delta_temporal=0.0, epsilon_intent=0.0)

    @classmethod
    def rrf_temporal(cls) -> ScoringWeights:
        return cls(alpha_lexical=0.35, beta_semantic=0.35, gamma_concept=0.0, delta_temporal=0.30, epsilon_intent=0.0)

    @classmethod
    def hybrid_temporal_concept(cls) -> ScoringWeights:
        return cls(alpha_lexical=0.25, beta_semantic=0.25, gamma_concept=0.25, delta_temporal=0.25, epsilon_intent=0.0)

    @classmethod
    def full(cls) -> ScoringWeights:
        return cls(alpha_lexical=0.20, beta_semantic=0.20, gamma_concept=0.25, delta_temporal=0.25, epsilon_intent=0.10)


class ModularEvidenceRetriever(EvidenceRetriever):
    """
    Main modular research retriever for longitudinal evidence retrieval.
    Orchestrates lexical, semantic, concept, temporal, and intent signals.
    Supports both weighted linear score combination and Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        weights: ScoringWeights | None = None,
        method_name: str = "modular_pipeline",
        bm25_retriever: EvidenceBM25Retriever | None = None,
        dense_retriever: EvidenceDenseRetriever | None = None,
        temporal_scorer: TemporalScorer | None = None,
        concept_scorer: ConceptScorer | None = None,
        fusion_strategy: str = "weighted",  # "weighted" or "rrf"
        rrf_k: int = 60,
        hard_temporal_filter: bool = True,
    ) -> None:
        self.weights = weights or ScoringWeights.hybrid_temporal_concept()
        self.method_name = method_name
        self.bm25_retriever = bm25_retriever or EvidenceBM25Retriever()
        self.dense_retriever = dense_retriever or EvidenceDenseRetriever()
        self.temporal_scorer = temporal_scorer or TemporalScorer()
        self.concept_scorer = concept_scorer or ConceptScorer()
        self.fusion_strategy = fusion_strategy
        self.rrf_k = rrf_k
        self.hard_temporal_filter = hard_temporal_filter

    def _score_intent_abnormality(
        self,
        query: ClinicalQuery,
        patient_records: Sequence[ResearchEvidenceRecord],
    ) -> dict[str, float]:
        """
        Computes intent/abnormality signal S_intent in [0.0, 1.0].
        If query requests abnormal values (e.g. first abnormal or out-of-range):
        evaluates clinical abnormality flags and cutoffs.
        """
        is_abn_query = query.abnormal_only or query.intent == QueryIntent.ABNORMALITY or "abnormal" in query.raw_query.lower()
        if not is_abn_query:
            return {r.id: 1.0 for r in patient_records}

        # Check abnormality for each record
        abnormal_status: dict[str, bool] = {}
        for r in patient_records:
            is_abn = False
            if r.flag and r.flag.lower() in ("abnormal", "high", "low"):
                is_abn = True
            elif r.value_numeric is not None:
                is_abn = is_clinically_abnormal(r)
            abnormal_status[r.id] = is_abn

        # If query is specifically looking for the first abnormal
        is_first_abn = "first abnormal" in query.raw_query.lower() or "first" in query.raw_query.lower()
        if is_first_abn:
            # Chronologically sort abnormal records for the target analyte
            target_analyte = (query.analyte_canonical or "").lower()
            matching_abn = [
                r for r in sorted(patient_records, key=lambda x: (x.observation_date or "", x.id))
                if abnormal_status.get(r.id, False)
                and (
                    not target_analyte
                    or (r.analyte_canonical and r.analyte_canonical.lower() == target_analyte)
                    or (r.analyte_raw and target_analyte in r.analyte_raw.lower())
                )
            ]
            scores: dict[str, float] = {}
            if matching_abn:
                first_abn_id = matching_abn[0].id
                for r in patient_records:
                    if r.id == first_abn_id:
                        scores[r.id] = 1.0
                    elif abnormal_status.get(r.id, False):
                        scores[r.id] = 0.5  # abnormal but not first
                    else:
                        scores[r.id] = 0.0  # normal
            else:
                scores = {r.id: 1.0 if abnormal_status.get(r.id, False) else 0.0 for r in patient_records}
            return scores

        return {r.id: 1.0 if abnormal_status.get(r.id, False) else 0.0 for r in patient_records}

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

        w = self.weights

        # 1. Lexical BM25 component
        bm25_raw = self.bm25_retriever.retrieve(
            query, patient_records, top_k=len(patient_records), patient_id=target_pid
        )
        bm25_score_map = {r.evidence_id: r.score for r in bm25_raw}
        bm25_rank_map = {r.evidence_id: r.rank for r in bm25_raw}

        if w.alpha_lexical > 0.0 or self.fusion_strategy == "rrf":
            bm25_scores = [bm25_score_map.get(r.id, 0.0) for r in patient_records]
            s_lex = normalize_min_max(bm25_scores)
        else:
            s_lex = [0.0] * len(patient_records)

        # 2. Semantic Dense component
        dense_raw = self.dense_retriever.retrieve(
            query, patient_records, top_k=len(patient_records), patient_id=target_pid
        )
        dense_score_map = {r.evidence_id: r.score for r in dense_raw}
        dense_rank_map = {r.evidence_id: r.rank for r in dense_raw}

        if w.beta_semantic > 0.0 or self.fusion_strategy == "rrf":
            s_sem = [dense_score_map.get(r.id, 0.0) for r in patient_records]
        else:
            s_sem = [0.0] * len(patient_records)

        # Reciprocal Rank Fusion base score
        if self.fusion_strategy == "rrf":
            rrf_raw = [
                (1.0 / (self.rrf_k + bm25_rank_map.get(r.id, len(patient_records))))
                + (1.0 / (self.rrf_k + dense_rank_map.get(r.id, len(patient_records))))
                for r in patient_records
            ]
            s_base = normalize_min_max(rrf_raw)
        else:
            s_base = [0.0] * len(patient_records)

        # 3. Concept matching component
        if w.gamma_concept > 0.0:
            concept_map = self.concept_scorer.score_patient_evidence(query, patient_records)
            s_con = [concept_map.get(r.id, 0.0) for r in patient_records]
        else:
            s_con = [0.0] * len(patient_records)

        # 4. Temporal component
        if w.delta_temporal > 0.0 or self.hard_temporal_filter:
            temp_map = self.temporal_scorer.score_patient_evidence(query, patient_records)
            s_tem = [temp_map.get(r.id, 0.0) for r in patient_records]
        else:
            s_tem = [0.0] * len(patient_records)

        # 5. Intent / Abnormality component
        if w.epsilon_intent > 0.0:
            intent_map = self._score_intent_abnormality(query, patient_records)
            s_int = [intent_map.get(r.id, 0.0) for r in patient_records]
        else:
            s_int = [0.0] * len(patient_records)

        # Explicit date constraint detection for hard gating
        has_explicit_date = self.temporal_scorer.has_explicit_date_constraint(query)
        in_window_exists = has_explicit_date and any(s_tem[i] > 0.0 for i in range(len(patient_records)))

        # Combine scores
        results: list[RetrievalResult] = []
        for idx, rec in enumerate(patient_records):
            if self.fusion_strategy == "rrf":
                base_weight = max(0.0, 1.0 - w.delta_temporal - w.gamma_concept - w.epsilon_intent)
                final_score = (
                    base_weight * s_base[idx]
                    + w.gamma_concept * s_con[idx]
                    + w.delta_temporal * s_tem[idx]
                    + w.epsilon_intent * s_int[idx]
                )
            else:
                final_score = (
                    w.alpha_lexical * s_lex[idx]
                    + w.beta_semantic * s_sem[idx]
                    + w.gamma_concept * s_con[idx]
                    + w.delta_temporal * s_tem[idx]
                    + w.epsilon_intent * s_int[idx]
                )

            # Hard temporal gating: out-of-window observations cannot outrank valid in-window observations
            if self.hard_temporal_filter and has_explicit_date and in_window_exists and s_tem[idx] == 0.0:
                final_score = 0.0

            results.append(
                RetrievalResult(
                    evidence_id=rec.id,
                    patient_id=rec.source_patient_id,
                    score=float(final_score),
                    rank=0,
                    retrieval_method=self.method_name,
                    analyte_canonical=rec.analyte_canonical,
                    concept_id=rec.concept_id,
                    loinc_code=rec.loinc_code,
                    observation_date=rec.observation_date,
                    value=rec.value_numeric if rec.value_numeric is not None else rec.value_text,
                    unit=rec.unit,
                    flag=rec.flag,
                    source_provenance=rec.source_provenance,
                    metadata={
                        "score_lexical": round(s_lex[idx], 6),
                        "score_semantic": round(s_sem[idx], 6),
                        "score_concept": round(s_con[idx], 6),
                        "score_temporal": round(s_tem[idx], 6),
                        "score_intent": round(s_int[idx], 6),
                        "weights": {
                            "alpha": w.alpha_lexical,
                            "beta": w.beta_semantic,
                            "gamma": w.gamma_concept,
                            "delta": w.delta_temporal,
                            "epsilon": w.epsilon_intent,
                        },
                    },
                )
            )

        return sort_and_rank_results(results, top_k=top_k)
