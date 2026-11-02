"""
packages/research-data/evaluation_builder.py

Longitudinal clinical Information Retrieval evaluation benchmark builder (CP-03).
Generates verifiable benchmark queries across 7 clinical temporal intents,
linking queries to ground-truth relevant evidence record IDs.

Benchmark Classification: Synthetic / Generated Functional IR Benchmark.
Constructed using deterministic rule-based temporal heuristics over longitudinal patient series
for pipeline verification. Does NOT claim human-annotated clinical IR benchmark status.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any, Sequence

from packages.research_data.models import (
    EvaluationQuery,
    LongitudinalSeries,
    ResearchEvidenceRecord,
    TemporalQueryIntent,
)


logger = logging.getLogger(__name__)


class EvaluationBenchmarkBuilder:
    """
    Constructs high-quality, reproducible Information Retrieval benchmark queries
    grounded directly in longitudinal patient records.

    Architecture (CP-05.5):
      SPLIT -> PATIENT -> ANALYTE -> INTENT
      - Disjoint patient assignment is established prior to query generation.
      - Queries are sampled using deterministic round-robin across eligible patients.
      - Broad patient coverage in every split (no concentration on 1-2 patients).
      - Repair of 'first_abnormal' starvation via evidence-based clinical thresholds.
      - Zero label leakage: queries use natural clinical phrasing without database IDs.
    """

    # Controlled clinical analytes in priority order
    PRIORITY_ANALYTES: list[str] = [
        "LDL Cholesterol",
        "HbA1c",
        "Total Cholesterol",
        "Haemoglobin",
        "Creatinine",
        "TSH",
        "Triglycerides",
        "Glucose",
        "Platelets",
        "WBC",
        "HDL Cholesterol",
    ]

    ALL_INTENTS: list[TemporalQueryIntent] = [
        "current_value",
        "previous_value",
        "longitudinal_trend",
        "last_n_observations",
        "date_comparison",
        "historical_interval",
        "first_abnormal",
    ]

    def build_longitudinal_series_map(
        self, records: Sequence[ResearchEvidenceRecord]
    ) -> dict[tuple[str, str], list[ResearchEvidenceRecord]]:
        grouped: dict[tuple[str, str], list[ResearchEvidenceRecord]] = defaultdict(list)
        for r in records:
            analyte = r.analyte_canonical or r.analyte_raw
            grouped[(r.source_patient_id, analyte)].append(r)

        # Sort each group chronologically
        for key in grouped:
            grouped[key].sort(key=lambda x: str(x.observation_date))

        return grouped

    def is_clinically_abnormal(self, record: ResearchEvidenceRecord) -> bool:
        """
        Evaluates whether an observation is clinically abnormal based on
        explicit flags, laboratory reference ranges, or established clinical thresholds.
        Grounded strictly in real observation evidence (no fabricated values).
        """
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

    def generate_patient_candidates(
        self,
        pid: str,
        patient_series: dict[str, list[ResearchEvidenceRecord]],
    ) -> dict[str, list[tuple[str, dict[str, Any]]]]:
        """
        Precomputes all valid candidate queries for a patient across the 7 intents.
        Returns a mapping from intent -> list of (analyte, query_kwargs).
        """
        candidates: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)

        # Order analytes: priority analytes first, then any remaining
        analytes = [a for a in self.PRIORITY_ANALYTES if a in patient_series]
        for a in patient_series:
            if a not in analytes:
                analytes.append(a)

        for a in analytes:
            recs = patient_series[a]
            n = len(recs)
            if n == 0:
                continue

            # 1. current_value (Latest observation, requires n >= 1)
            candidates["current_value"].append(
                (
                    a,
                    {
                        "query": f"What is my most recent {a} level?",
                        "relevant_evidence_ids": [recs[-1].id],
                        "metadata": {
                            "latest_date": recs[-1].observation_date,
                            "total_series_len": n,
                        },
                    },
                )
            )

            # 2. previous_value (Second to latest observation, requires n >= 2)
            if n >= 2:
                candidates["previous_value"].append(
                    (
                        a,
                        {
                            "query": f"What was my previous {a} reading before the latest one?",
                            "relevant_evidence_ids": [recs[-2].id],
                            "metadata": {
                                "target_date": recs[-2].observation_date,
                                "latest_date": recs[-1].observation_date,
                            },
                        },
                    )
                )

            # 3. longitudinal_trend (Complete historical trajectory, requires n >= 2)
            if n >= 2:
                candidates["longitudinal_trend"].append(
                    (
                        a,
                        {
                            "query": f"How has my {a} changed over time?",
                            "relevant_evidence_ids": [r.id for r in recs],
                            "metadata": {
                                "trajectory_points": n,
                                "first_date": recs[0].observation_date,
                                "last_date": recs[-1].observation_date,
                            },
                        },
                    )
                )

            # 4. last_n_observations (Recent subset, requires n >= 3)
            if n >= 3:
                k = min(3, n)
                subset = recs[-k:]
                candidates["last_n_observations"].append(
                    (
                        a,
                        {
                            "query": f"Show my last {k} {a} results.",
                            "relevant_evidence_ids": [r.id for r in subset],
                            "metadata": {"n_requested": k},
                        },
                    )
                )

            # 5. date_comparison (Earliest vs latest observation, requires n >= 2)
            if n >= 2:
                d_first = str(recs[0].observation_date)[:10]
                d_last = str(recs[-1].observation_date)[:10]
                candidates["date_comparison"].append(
                    (
                        a,
                        {
                            "query": f"Compare my {a} from {d_first} with {d_last}.",
                            "relevant_evidence_ids": [recs[0].id, recs[-1].id],
                            "metadata": {
                                "date_a": recs[0].observation_date,
                                "date_b": recs[-1].observation_date,
                            },
                        },
                    )
                )

            # 6. historical_interval (Calendar-year bounded, requires n >= 2)
            if n >= 2:
                year_recs: dict[str, list[ResearchEvidenceRecord]] = defaultdict(list)
                for r in recs:
                    yr = str(r.observation_date)[:4]
                    year_recs[yr].append(r)
                # Pick the year with the most observations
                best_yr = max(year_recs.keys(), key=lambda y: len(year_recs[y]))
                candidates["historical_interval"].append(
                    (
                        a,
                        {
                            "query": f"What were my {a} levels during {best_yr}?",
                            "relevant_evidence_ids": [r.id for r in year_recs[best_yr]],
                            "metadata": {
                                "year": best_yr,
                                "matched_count": len(year_recs[best_yr]),
                            },
                        },
                    )
                )

            # 7. first_abnormal (Earliest abnormal observation, evidence-based)
            abnormal_candidates = [r for r in recs if self.is_clinically_abnormal(r)]
            if abnormal_candidates:
                first_abn = abnormal_candidates[0]
                candidates["first_abnormal"].append(
                    (
                        a,
                        {
                            "query": f"When was my {a} first flagged as elevated or abnormal?",
                            "relevant_evidence_ids": [first_abn.id],
                            "metadata": {
                                "first_abnormal_date": first_abn.observation_date,
                                "value": first_abn.value_numeric,
                            },
                        },
                    )
                )

        return candidates

    def generate_benchmark(
        self,
        records: Sequence[ResearchEvidenceRecord],
        patient_splits: dict[str, list[str]],
        target_count: int = 86,
        split_targets: dict[str, int] | None = None,
        seed: int = 42,
    ) -> list[EvaluationQuery]:
        """
        Generates deterministic, patient-disjoint Information Retrieval benchmark queries.
        Follows SPLIT -> PATIENT -> ANALYTE -> INTENT round-robin generation.
        """
        series_map = self.build_longitudinal_series_map(records)
        queries: list[EvaluationQuery] = []
        query_idx = 1

        # Reorganize series map by patient: pid -> {analyte: list[records]}
        patient_series_map: dict[str, dict[str, list[ResearchEvidenceRecord]]] = defaultdict(dict)
        for (pid, analyte), rec_list in series_map.items():
            patient_series_map[pid][analyte] = rec_list

        # Determine split targets
        if split_targets is not None:
            active_targets = split_targets
        else:
            active_splits = [s for s in ("dev", "val", "test") if patient_splits.get(s)]
            if not active_splits:
                return []

            # Exact 36/12/12 default distribution: 36 dev, 25 val, 25 test = 86 total
            if (
                set(active_splits) == {"dev", "val", "test"}
                and len(patient_splits.get("dev", [])) == 36
                and target_count == 86
            ):
                active_targets = {"dev": 36, "val": 25, "test": 25}
            else:
                total_pats = sum(len(patient_splits.get(s, [])) for s in active_splits)
                active_targets = {}
                remaining = target_count
                for idx, s in enumerate(active_splits):
                    if idx == len(active_splits) - 1:
                        active_targets[s] = remaining
                    else:
                        share = max(1, int(round(target_count * (len(patient_splits[s]) / total_pats))))
                        active_targets[s] = min(remaining, share)
                        remaining -= active_targets[s]

        # Iterate through splits in fixed deterministic order
        for split_name in ("dev", "val", "test"):
            target = active_targets.get(split_name, 0)
            if target <= 0:
                continue

            pids = sorted(patient_splits.get(split_name, []))
            if not pids:
                continue

            # Precompute candidates per patient
            pat_candidates = {
                pid: self.generate_patient_candidates(pid, patient_series_map.get(pid, {}))
                for pid in pids
            }

            used_combinations: set[tuple[str, str, str]] = set()
            patient_query_count: Counter[str] = Counter()
            intent_idx = 0
            split_queries: list[EvaluationQuery] = []

            attempts = 0
            max_attempts = 2000
            while len(split_queries) < target and attempts < max_attempts:
                attempts += 1
                intent = self.ALL_INTENTS[intent_idx % len(self.ALL_INTENTS)]
                intent_idx += 1

                # Prioritize patients with the fewest queries, tie-break by deterministic pid
                sorted_pats = sorted(pids, key=lambda p: (patient_query_count[p], p))

                chosen: tuple[str, str, str, dict[str, Any]] | None = None
                for pid in sorted_pats:
                    for a, q_data in pat_candidates[pid].get(intent, []):
                        if (pid, a, intent) not in used_combinations:
                            chosen = (pid, a, intent, q_data)
                            break
                    if chosen:
                        break

                if chosen:
                    pid, a, intent, q_data = chosen
                    used_combinations.add((pid, a, intent))
                    patient_query_count[pid] += 1

                    q = EvaluationQuery(
                        query_id=f"Q_{query_idx:03d}",
                        patient_id=pid,
                        query=q_data["query"],
                        intent=intent,
                        target_analyte=a,
                        relevant_evidence_ids=q_data["relevant_evidence_ids"],
                        split=split_name,  # type: ignore[arg-type]
                        metadata=q_data["metadata"],
                    )
                    split_queries.append(q)
                    query_idx += 1

            queries.extend(split_queries)

        return queries
