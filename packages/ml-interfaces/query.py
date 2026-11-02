"""
packages/ml-interfaces/query.py

Standardized contracts and typed schema for Clinical Query Understanding
and Temporal Intent Parsing (CP-05).

Defines the output representation for the query-understanding layer:
an evidence-aware structured query object encoding clinical analyte mentions,
canonical concepts, temporal operators, date boundaries, comparison targets,
abnormality constraints, and confidence metrics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class QueryIntent(str, Enum):
    """
    Primary clinical retrieval and reasoning intent.
    Minimum taxonomy required by CP-05 specification.
    """
    CURRENT_VALUE = "CURRENT_VALUE"
    HISTORICAL = "HISTORICAL"
    LAST_N = "LAST_N"
    COMPARISON = "COMPARISON"
    TREND = "TREND"
    DEFINITION_GUIDELINE = "DEFINITION_GUIDELINE"
    ABNORMALITY = "ABNORMALITY"


class TemporalOperator(str, Enum):
    """
    Temporal constraint operator for longitudinal evidence retrieval.
    """
    LATEST = "LATEST"
    EXACT_DATE = "EXACT_DATE"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    BETWEEN = "BETWEEN"
    SINCE = "SINCE"
    LAST_N = "LAST_N"
    ALL_TIME = "ALL_TIME"
    NONE = "NONE"


class ComparisonTarget(str, Enum):
    """
    Target comparison benchmark when intent is COMPARISON.
    """
    PREVIOUS = "PREVIOUS"
    HISTORICAL = "HISTORICAL"
    PERIOD = "PERIOD"
    BASELINE = "BASELINE"


class WindowUnit(str, Enum):
    """Time unit for relative temporal retrieval windows."""
    DAYS = "DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"
    YEARS = "YEARS"


@dataclass(frozen=True)
class RelativeWindow:
    """Relative temporal window specification (e.g. past 6 months)."""
    value: int
    unit: WindowUnit

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelativeWindow:
        return cls(
            value=int(data["value"]),
            unit=WindowUnit(data["unit"]),
        )


@dataclass
class ClinicalQuery:
    """
    Versioned typed representation of a parsed clinical query (CP-05).

    Contract fields:
      - raw_query: verbatim input string
      - intent: detected QueryIntent
      - analyte_mentions: verbatim analyte substrings detected in query
      - analyte_canonical: normalized canonical analyte name
      - concept_id: canonical concept identifier (e.g. 'LOINC:718-7')
      - loinc_code: plain LOINC code without prefix (e.g. '718-7')
      - temporal_operator: temporal restriction operator
      - start_date: ISO date boundary (lower bound)
      - end_date: ISO date boundary (upper bound)
      - relative_window: relative duration constraint (e.g. 6 MONTHS)
      - limit: maximum number of observations requested (e.g. for LAST_N)
      - comparison_target: baseline/target for comparison queries
      - abnormal_only: flag indicating abnormal/out-of-range constraint
      - confidence: deterministic parse confidence score [0.0 - 1.0]
      - unresolved_terms: terms identified as potentially clinical but unmapped
      - version: schema version string
    """
    raw_query: str
    intent: QueryIntent
    analyte_mentions: list[str] = field(default_factory=list)
    analyte_canonical: str | None = None
    concept_id: str | None = None
    loinc_code: str | None = None
    temporal_operator: TemporalOperator | None = None
    start_date: date | None = None
    end_date: date | None = None
    relative_window: RelativeWindow | None = None
    limit: int | None = None
    comparison_target: ComparisonTarget | None = None
    abnormal_only: bool = False
    confidence: float = 1.0
    unresolved_terms: list[str] = field(default_factory=list)
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "intent": self.intent.value,
            "analyte_mentions": list(self.analyte_mentions),
            "analyte_canonical": self.analyte_canonical,
            "concept_id": self.concept_id,
            "loinc_code": self.loinc_code,
            "temporal_operator": self.temporal_operator.value if self.temporal_operator else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "relative_window": self.relative_window.to_dict() if self.relative_window else None,
            "limit": self.limit,
            "comparison_target": self.comparison_target.value if self.comparison_target else None,
            "abnormal_only": self.abnormal_only,
            "confidence": round(self.confidence, 4),
            "unresolved_terms": list(self.unresolved_terms),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClinicalQuery:
        start_d = date.fromisoformat(data["start_date"]) if data.get("start_date") else None
        end_d = date.fromisoformat(data["end_date"]) if data.get("end_date") else None
        rel_win = (
            RelativeWindow.from_dict(data["relative_window"])
            if data.get("relative_window")
            else None
        )
        return cls(
            raw_query=data["raw_query"],
            intent=QueryIntent(data["intent"]),
            analyte_mentions=data.get("analyte_mentions", []),
            analyte_canonical=data.get("analyte_canonical"),
            concept_id=data.get("concept_id"),
            loinc_code=data.get("loinc_code"),
            temporal_operator=(
                TemporalOperator(data["temporal_operator"])
                if data.get("temporal_operator")
                else None
            ),
            start_date=start_d,
            end_date=end_d,
            relative_window=rel_win,
            limit=data.get("limit"),
            comparison_target=(
                ComparisonTarget(data["comparison_target"])
                if data.get("comparison_target")
                else None
            ),
            abnormal_only=bool(data.get("abnormal_only", False)),
            confidence=float(data.get("confidence", 1.0)),
            unresolved_terms=data.get("unresolved_terms", []),
            version=data.get("version", "1.0"),
        )
