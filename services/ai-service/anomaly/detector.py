"""
ai-service/anomaly/detector.py

Unified anomaly detection pipeline.

Combines Z-score analysis + IsolationForest model scoring, then generates
plain-language trend summaries in English and Hindi.

TONE RULES (non-negotiable — enforced by test_anomaly.py):
  - Do NOT say "you have [condition]" or "you are diagnosed with".
  - Do NOT say "your [metric] is dangerous / critical / alarming".
  - DO say "your readings show a [rising/falling/stable] pattern".
  - DO recommend consulting a doctor, never prescribe or diagnose.
  - Bilingual: every summary must be returned in both EN and HI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .model import ModelAnomalyResult, score_anomaly
from .zscore import TrendDirection, ZScoreResult, compute_zscore


@dataclass(frozen=True)
class DetectionResult:
    test_name: str
    trend: str                    # "rising" | "falling" | "stable" | "insufficient_data"
    anomaly_score: float          # [-1, +1]; +1 = normal, -1 = anomalous
    is_anomaly: bool
    z_score: float | None
    out_of_range_streak: int
    method: str                   # which model was used
    data_points_used: int
    summary_en: str               # plain-language EN summary (non-diagnostic)
    summary_hi: str               # plain-language HI summary (non-diagnostic)


def detect(
    test_name: str,
    data_points: list[tuple[date, float]],
    unit: str | None = None,
) -> DetectionResult:
    """
    Run the full anomaly detection pipeline for a single health metric.

    Args:
        test_name:   Human-readable metric name (e.g., "Haemoglobin").
        data_points: Chronological (date, value) pairs, oldest first.
        unit:        Optional unit string for use in summary messages.

    Returns:
        DetectionResult with trend, anomaly score, and bilingual summaries.
    """
    z_result: ZScoreResult = compute_zscore(data_points)
    m_result: ModelAnomalyResult = score_anomaly(data_points, z_score=z_result.z_score)

    summary_en, summary_hi = _build_summaries(test_name, unit, z_result, m_result)

    return DetectionResult(
        test_name=test_name,
        trend=z_result.trend.value,
        anomaly_score=m_result.anomaly_score,
        is_anomaly=m_result.is_anomaly,
        z_score=z_result.z_score,
        out_of_range_streak=z_result.out_of_range_streak,
        method=m_result.method,
        data_points_used=z_result.data_points_used,
        summary_en=summary_en,
        summary_hi=summary_hi,
    )


# ---------------------------------------------------------------------------
# Plain-language summary generation (non-diagnostic)
# ---------------------------------------------------------------------------

_UNIT_SEP = " "  # space before unit string


def _unit_str(unit: str | None) -> str:
    return f" ({unit})" if unit else ""


def _build_summaries(
    test_name: str,
    unit: str | None,
    z: ZScoreResult,
    m: ModelAnomalyResult,
) -> tuple[str, str]:
    u = _unit_str(unit)

    if z.trend == TrendDirection.INSUFFICIENT_DATA:
        en = (
            f"Only {z.data_points_used} reading(s) found for {test_name}{u}. "
            "At least 3 readings are needed to identify a pattern. "
            "Keep adding reports over time so trends can be tracked."
        )
        hi = (
            f"{test_name}{u} के लिए केवल {z.data_points_used} रीडिंग मिली। "
            "पैटर्न पहचानने के लिए कम से कम 3 रीडिंग चाहिए। "
            "समय के साथ अधिक रिपोर्ट जोड़ते रहें।"
        )
        return en, hi

    # Build trend description
    trend_en = {
        TrendDirection.RISING: "an upward trend",
        TrendDirection.FALLING: "a downward trend",
        TrendDirection.STABLE: "a stable pattern",
    }[z.trend]
    trend_hi = {
        TrendDirection.RISING: "ऊपर की ओर रुझान",
        TrendDirection.FALLING: "नीचे की ओर रुझान",
        TrendDirection.STABLE: "स्थिर पैटर्न",
    }[z.trend]

    # Streak context
    streak_en = ""
    streak_hi = ""
    if z.out_of_range_streak >= 2:
        streak_en = (
            f" The last {z.out_of_range_streak} readings are outside the usual range."
        )
        streak_hi = (
            f" पिछली {z.out_of_range_streak} रीडिंग सामान्य सीमा से बाहर हैं।"
        )

    # Anomaly context
    anomaly_en = ""
    anomaly_hi = ""
    if m.is_anomaly:
        anomaly_en = (
            " The most recent reading appears unusual compared to your past readings. "
            "Consider sharing this with your doctor at your next visit."
        )
        anomaly_hi = (
            " सबसे हाल की रीडिंग आपकी पिछली रीडिंग की तुलना में असामान्य लगती है। "
            "अपने अगले डॉक्टर दौरे पर इसे उनसे साझा करने पर विचार करें।"
        )
    else:
        anomaly_en = " No unusual pattern detected in recent readings."
        anomaly_hi = " हाल की रीडिंग में कोई असामान्य पैटर्न नहीं मिला।"

    en = (
        f"Your {test_name}{u} readings show {trend_en} "
        f"across {z.data_points_used} data point(s)."
        f"{streak_en}{anomaly_en}"
    )
    hi = (
        f"आपकी {test_name}{u} रीडिंग {z.data_points_used} डेटा पॉइंट में {trend_hi} दिखाती है।"
        f"{streak_hi}{anomaly_hi}"
    )

    return en, hi
