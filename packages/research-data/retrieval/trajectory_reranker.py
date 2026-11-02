"""
packages/research-data/retrieval/trajectory_reranker.py

Trajectory-Aware Evidence Re-ranking Layer (CP-07).
Consumes candidate RetrievalResults from CP-06, constructs longitudinal trajectories,
and re-ranks candidates by longitudinal informativeness (baseline, inflection, endpoint)
for trend and comparison queries.

Guarantees:
  1. Patient Isolation: Evaluates strictly within each patient's candidate trajectory.
  2. Hard Temporal Preservation: Candidates with score == 0.0 (filtered by CP-06 hard bounds)
     remain strictly 0.0 and are NEVER resurrected.
  3. Provenance & Identity: All original evidence_id, metadata, and provenance are preserved.
  4. Deterministic Tie-Breaking: Strict (-score, -timestamp, evidence_id) contract preserved.
  5. Decoupled Pipeline: Operates after candidate retrieval without replacing CP-06 scorers.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from packages.ml_interfaces.query import ClinicalQuery, QueryIntent
from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.retrieval.contract import (
    EvidenceRetriever,
    RetrievalResult,
    sort_and_rank_results,
)
from packages.research_data.retrieval.trajectory import (
    TrajectoryBlock,
    build_trajectories,
    calculate_inflection_point,
    parse_numeric_value,
)

logger = logging.getLogger(__name__)


def is_longitudinal_trajectory_query(query: ClinicalQuery) -> bool:
    """
    Identifies whether the query possesses longitudinal, trend, or comparison retrieval intent
    where establishing a trajectory (baseline -> inflection -> endpoint) is clinically meaningful.
    """
    intent = query.intent
    raw_text = (query.raw_query or "").lower()

    if intent in (QueryIntent.TREND, QueryIntent.COMPARISON):
        return True

    # Check for intent string or natural phrasing
    intent_str = str(getattr(query, "intent", "")).lower()
    if any(k in intent_str for k in ("trend", "comparison", "longitudinal")):
        return True

    keywords = ("trend", "change", "over time", "compare", "progression", "trajectory", "histor")
    return any(k in raw_text for k in keywords)


class TrajectoryReranker:
    """
    Trajectory-aware re-ranking layer (CP-07).
    Reranks CP-06 evidence observations by prioritizing structurally informative
    trajectory anchors (baseline, significant intermediate changes, endpoint).
    """

    def __init__(self, trajectory_weight: float = 0.25) -> None:
        self.trajectory_weight = trajectory_weight

    def get_trajectory_blocks(
        self, candidates: Sequence[RetrievalResult]
    ) -> list[TrajectoryBlock]:
        """Builds and returns all trajectory blocks for the provided candidate set."""
        trajectory_map = build_trajectories(candidates)
        return list(trajectory_map.values())

    def rerank(
        self,
        query: ClinicalQuery,
        candidates: Sequence[RetrievalResult],
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """
        Re-ranks candidate observations using trajectory informativeness.
        Preserves patient isolation, hard temporal exclusions, and deterministic tie-breaking.
        """
        if not candidates:
            return []

        # 1. Build chronological trajectory blocks
        trajectory_map = build_trajectories(candidates)
        is_traj_query = is_longitudinal_trajectory_query(query)

        # 2. Assign trajectory informativeness scores S_traj in [0.0, 1.0]
        # and identify observational roles
        trajectory_scores: dict[str, float] = {}
        trajectory_roles: dict[str, str] = {}
        trajectory_meta_map: dict[str, dict[str, Any]] = {}

        for (pid, analyte), block in trajectory_map.items():
            obs_list = block.observations
            n_obs = len(obs_list)

            # Store summary features for attachment
            feat_summary = {
                "trajectory_direction": block.direction,
                "trajectory_delta": block.delta,
                "trajectory_relative_change": block.relative_change,
                "trajectory_slope_per_day": block.slope_per_day,
                "trajectory_count": block.observation_count,
                "trajectory_span_days": block.date_span_days,
            }

            if n_obs <= 2:
                # 1 or 2 points: all points are essential boundary anchors
                for obs in obs_list:
                    trajectory_scores[obs.evidence_id] = 1.0
                    trajectory_roles[obs.evidence_id] = "anchor"
                    trajectory_meta_map[obs.evidence_id] = feat_summary
                continue

            # 3 or more points:
            # Baseline (earliest) and Endpoint (latest) are critical structural anchors
            baseline_obs = obs_list[0]
            endpoint_obs = obs_list[-1]

            trajectory_scores[baseline_obs.evidence_id] = 1.0
            trajectory_roles[baseline_obs.evidence_id] = "baseline"
            trajectory_meta_map[baseline_obs.evidence_id] = feat_summary

            trajectory_scores[endpoint_obs.evidence_id] = 1.0
            trajectory_roles[endpoint_obs.evidence_id] = "endpoint"
            trajectory_meta_map[endpoint_obs.evidence_id] = feat_summary

            # Find intermediate point with maximum secular chord deviation (inflection point)
            inflection_info = calculate_inflection_point(obs_list, method="secant_chord")
            best_inflection_id = inflection_info["inflection_evidence_id"]
            max_deviation = inflection_info["inflection_deviation"]

            intermediate_obs = obs_list[1:-1]
            # Score intermediate points
            for int_obs in intermediate_obs:
                trajectory_meta_map[int_obs.evidence_id] = feat_summary
                if int_obs.evidence_id == best_inflection_id and max_deviation > 0.0:
                    trajectory_scores[int_obs.evidence_id] = 0.90
                    trajectory_roles[int_obs.evidence_id] = "inflection"
                else:
                    trajectory_scores[int_obs.evidence_id] = 0.50
                    trajectory_roles[int_obs.evidence_id] = "intermediate"

        # 3. Combine base score with trajectory score
        reranked_results: list[RetrievalResult] = []
        for cand in candidates:
            orig_score = cand.score
            traj_score = trajectory_scores.get(cand.evidence_id, 0.5)
            role = trajectory_roles.get(cand.evidence_id, "unassigned")
            traj_meta = trajectory_meta_map.get(cand.evidence_id, {})

            # Copy metadata and attach trajectory features
            new_meta = dict(cand.metadata)
            new_meta.update(traj_meta)
            new_meta["score_trajectory"] = round(traj_score, 6)
            new_meta["trajectory_role"] = role

            # HARD TEMPORAL PRESERVATION:
            # If the candidate was gated out by CP-06 hard temporal filtering (score == 0.0),
            # it MUST remain 0.0 and cannot be resurrected by trajectory signals.
            if orig_score == 0.0:
                final_score = 0.0
            elif is_traj_query and self.trajectory_weight > 0.0:
                final_score = (1.0 - self.trajectory_weight) * orig_score + (self.trajectory_weight * traj_score)
                new_meta["is_trajectory_reranked"] = True
            else:
                final_score = orig_score
                new_meta["is_trajectory_reranked"] = False

            updated = RetrievalResult(
                evidence_id=cand.evidence_id,
                patient_id=cand.patient_id,
                score=float(final_score),
                rank=0,  # will be assigned by sort_and_rank_results
                retrieval_method=cand.retrieval_method if not is_traj_query else f"{cand.retrieval_method}+Trajectory",
                analyte_canonical=cand.analyte_canonical,
                concept_id=cand.concept_id,
                loinc_code=cand.loinc_code,
                observation_date=cand.observation_date,
                value=cand.value,
                unit=cand.unit,
                flag=cand.flag,
                source_provenance=cand.source_provenance,
                metadata=new_meta,
            )
            reranked_results.append(updated)

        # 4. Apply deterministic tie-breaking and assign ranks
        return sort_and_rank_results(reranked_results, top_k=top_k)


class TrajectoryAwareRetriever(EvidenceRetriever):
    """
    Composite evidence retriever implementing EvidenceRetriever (CP-07).
    Executes an underlying CP-06 base retriever, constructs patient trajectories,
    and applies trajectory-aware re-ranking.
    """

    def __init__(
        self,
        base_retriever: EvidenceRetriever,
        reranker: TrajectoryReranker | None = None,
        method_name: str | None = None,
    ) -> None:
        self.base_retriever = base_retriever
        self.reranker = reranker or TrajectoryReranker()
        base_name = getattr(base_retriever, "method_name", "BaseRetriever")
        self.method_name = method_name or f"{base_name}+Trajectory"

    def retrieve(
        self,
        query: ClinicalQuery,
        evidence: Sequence[ResearchEvidenceRecord],
        top_k: int = 10,
        patient_id: str | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieves candidates from the base retriever and applies trajectory-aware re-ranking.
        """
        # Retrieve candidate pool from CP-06
        candidate_pool_size = max(top_k * 2, 25)
        base_results = self.base_retriever.retrieve(
            query=query,
            evidence=evidence,
            top_k=candidate_pool_size,
            patient_id=patient_id,
        )

        if not base_results:
            return []

        # Re-rank using trajectory-aware layer
        return self.reranker.rerank(
            query=query,
            candidates=base_results,
            top_k=top_k,
        )
