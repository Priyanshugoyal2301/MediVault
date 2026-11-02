"""
packages/research-data/retrieval/temporal.py

Temporal Reranking Engine for Longitudinal Evidence Retrieval (CP-06).
Consumes structured ClinicalQuery objects (CP-05) as the single source of truth.
Evaluates temporal alignment between clinical queries and atomic Evidence Observations.

Supported intents and operators:
  - CURRENT_VALUE / LATEST (rewards latest observation)
  - HISTORICAL / EXACT_DATE / BETWEEN / BEFORE / AFTER / SINCE (window verification)
  - LAST_N (rewards top N most recent observations of the analyte)
  - COMPARISON / PREVIOUS (rewards previous observation or baseline/target comparison pair)
  - TREND (rewards complete longitudinal trajectory of the analyte)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Sequence

from packages.ml_interfaces.query import (
    ClinicalQuery,
    ComparisonTarget,
    QueryIntent,
    TemporalOperator,
)
from packages.research_data.models import ResearchEvidenceRecord


def parse_obs_date(obs_date_str: str) -> date | None:
    """Extracts date from ISO observation date string."""
    if not obs_date_str:
        return None
    try:
        return datetime.fromisoformat(obs_date_str.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(obs_date_str[:10], "%Y-%m-%d").date()
        except Exception:
            return None


class TemporalScorer:
    """
    Evaluates temporal relevance scores S_temporal in [0.0, 1.0]
    for a patient's evidence records given a structured ClinicalQuery.
    """

    def score_patient_evidence(
        self,
        query: ClinicalQuery,
        patient_records: Sequence[ResearchEvidenceRecord],
    ) -> dict[str, float]:
        """
        Returns a mapping of evidence_id -> temporal_score in [0.0, 1.0].
        Analyte-aware: temporal rankings (such as latest, previous, or last-N)
        are computed relative to the candidate series of the query's target analyte.
        """
        if not patient_records:
            return {}

        scores: dict[str, float] = {}

        # 1. Group records by analyte to establish chronological trajectories
        target_analyte = (query.analyte_canonical or "").lower()
        
        # Sort patient records chronologically
        sorted_records = sorted(
            patient_records,
            key=lambda r: (r.observation_date or "", r.id),
        )

        # Filter to matching analyte records if target analyte is known
        matching_series = [
            r for r in sorted_records
            if target_analyte and (
                (r.analyte_canonical and r.analyte_canonical.lower() == target_analyte)
                or (r.analyte_raw and target_analyte in r.analyte_raw.lower())
            )
        ]
        # If no analyte match in series, fallback to all records
        eval_series = matching_series if matching_series else sorted_records

        # Chronologically ordered IDs: earliest to latest
        series_ids = [r.id for r in eval_series]
        n_obs = len(series_ids)

        intent = query.intent
        op = query.temporal_operator

        # Case A: CURRENT_VALUE / LATEST
        if intent == QueryIntent.CURRENT_VALUE or op == TemporalOperator.LATEST:
            if n_obs > 0:
                latest_id = series_ids[-1]
                for r in patient_records:
                    if r.id == latest_id:
                        scores[r.id] = 1.0
                    elif r.id in series_ids:
                        # Distance from latest in chronological sequence
                        dist_from_latest = (n_obs - 1) - series_ids.index(r.id)
                        scores[r.id] = max(0.0, 1.0 / (1.0 + dist_from_latest * 2.0))
                    else:
                        scores[r.id] = 0.0
            return scores

        # Case B: LAST_N
        if intent == QueryIntent.LAST_N or op == TemporalOperator.LAST_N:
            limit = query.limit or 3
            recent_n_ids = set(series_ids[-limit:]) if n_obs > 0 else set()
            for r in patient_records:
                if r.id in recent_n_ids:
                    # Ranked within the top N (most recent gets 1.0, N-th gets slightly less or 1.0)
                    rank_from_end = (n_obs - 1) - series_ids.index(r.id)
                    scores[r.id] = max(0.8, 1.0 - (rank_from_end * 0.05))
                elif r.id in series_ids:
                    scores[r.id] = 0.1  # older observation of same analyte
                else:
                    scores[r.id] = 0.0
            return scores

        # Case C: COMPARISON / PREVIOUS
        if intent == QueryIntent.COMPARISON:
            if query.comparison_target == ComparisonTarget.PREVIOUS or "previous" in query.raw_query.lower():
                # Specific "previous" value before latest
                if n_obs >= 2:
                    prev_id = series_ids[-2]  # Second most recent
                    latest_id = series_ids[-1]
                    for r in patient_records:
                        if r.id == prev_id:
                            scores[r.id] = 1.0  # primary target
                        elif r.id == latest_id:
                            scores[r.id] = 0.5  # reference point
                        else:
                            scores[r.id] = 0.0
                    return scores
                elif n_obs == 1:
                    # Only 1 observation exists
                    return {r.id: 1.0 if r.id == series_ids[0] else 0.0 for r in patient_records}

            # Date-to-date comparison: if query has start_date and end_date
            if query.start_date and query.end_date:
                for r in patient_records:
                    obs_d = parse_obs_date(r.observation_date)
                    if obs_d in (query.start_date, query.end_date):
                        scores[r.id] = 1.0
                    else:
                        scores[r.id] = 0.0
                return scores

        # Case D: TREND / HISTORICAL ALL
        if intent in (QueryIntent.TREND, QueryIntent.HISTORICAL) and op == TemporalOperator.ALL_TIME:
            for r in patient_records:
                if r.id in series_ids:
                    scores[r.id] = 1.0  # all points in trajectory are relevant
                else:
                    scores[r.id] = 0.0
            return scores
        elif intent == QueryIntent.TREND:
            for r in patient_records:
                if r.id in series_ids:
                    scores[r.id] = 1.0  # all points in trajectory are relevant
                else:
                    scores[r.id] = 0.0
            return scores

        # Case E: DATE-BOUNDED (EXACT_DATE, BETWEEN, BEFORE, AFTER, SINCE)
        has_temporal_constraint = bool(
            query.start_date or query.end_date or op not in (None, TemporalOperator.NONE, TemporalOperator.ALL_TIME)
        )
        if has_temporal_constraint:
            for r in patient_records:
                obs_d = parse_obs_date(r.observation_date)
                if obs_d is None:
                    scores[r.id] = 0.0
                    continue

                # Exact date match
                if (op == TemporalOperator.EXACT_DATE and query.start_date) or (query.start_date and query.end_date and query.start_date == query.end_date):
                    target_d = query.start_date
                    scores[r.id] = 1.0 if obs_d == target_d else 0.0

                # Between / Range
                elif query.start_date and query.end_date:
                    if query.start_date <= obs_d <= query.end_date:
                        scores[r.id] = 1.0
                    else:
                        scores[r.id] = 0.0

                # After / Since
                elif query.start_date and not query.end_date:
                    scores[r.id] = 1.0 if obs_d >= query.start_date else 0.0

                # Before
                elif query.end_date and not query.start_date:
                    scores[r.id] = 1.0 if obs_d <= query.end_date else 0.0

                else:
                    scores[r.id] = 0.5
            return scores

        # Default fallback: neutral score
        return {r.id: 0.5 for r in patient_records}

    @staticmethod
    def has_explicit_date_constraint(query: ClinicalQuery) -> bool:
        """Determines if query specifies an explicit date or bounded range constraint."""
        if query.start_date or query.end_date:
            return True
        if query.temporal_operator in (
            TemporalOperator.EXACT_DATE,
            TemporalOperator.BETWEEN,
            TemporalOperator.BEFORE,
            TemporalOperator.AFTER,
            TemporalOperator.SINCE,
        ):
            return True
        return False
