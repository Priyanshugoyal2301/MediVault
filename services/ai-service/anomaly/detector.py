"""
ai-service/anomaly/detector.py

Unified anomaly detection pipeline.

Combines Z-score trend analysis + statistical personal-series monitor
(causal z, %Δ, CUSUM), then generates plain-language summaries in EN/HI.

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
    summary_en: str
    summary_hi: str


def detect(
    test_name: str,
    data_points: list[tuple[date, float]],
    unit: str | None = None,
    reference_range_low: float | None = None,
    reference_range_high: float | None = None,
) -> DetectionResult:
    """
    Run the full anomaly detection pipeline for a single health metric.

    Optional reference_range_* add a soft summary note only (Plan C):
    bake-off showed OR-ing ref-range into is_anomaly raised FAR — rejected.
    """
    z_result: ZScoreResult = compute_zscore(data_points)
    m_result: ModelAnomalyResult = score_anomaly(data_points, z_score=z_result.z_score)

    summary_en, summary_hi = _build_summaries(
        test_name,
        unit,
        z_result,
        m_result,
        data_points=data_points,
        reference_range_low=reference_range_low,
        reference_range_high=reference_range_high,
    )

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


def _unit_str(unit: str | None) -> str:
    return f" ({unit})" if unit else ""


def _build_summaries(
    test_name: str,
    unit: str | None,
    z: ZScoreResult,
    m: ModelAnomalyResult,
    data_points: list[tuple[date, float]] | None = None,
    reference_range_low: float | None = None,
    reference_range_high: float | None = None,
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

    streak_en = ""
    streak_hi = ""
    if z.out_of_range_streak >= 2:
        streak_en = (
            f" The last {z.out_of_range_streak} readings are outside the usual range."
        )
        streak_hi = (
            f" पिछली {z.out_of_range_streak} रीडिंग सामान्य सीमा से बाहर हैं।"
        )

    delta_en = ""
    delta_hi = ""
    if m.pct_delta is not None and abs(m.pct_delta) >= 0.10:
        pct = abs(m.pct_delta) * 100.0
        direction = "higher" if m.pct_delta > 0 else "lower"
        direction_hi = "अधिक" if m.pct_delta > 0 else "कम"
        delta_en = f" The latest reading is about {pct:.0f}% {direction} than the previous one."
        delta_hi = f" नवीनतम रीडिंग पिछली रीडिंग से लगभग {pct:.0f}% {direction_hi} है।"

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

    ref_en = ""
    ref_hi = ""
    if (
        data_points
        and reference_range_low is not None
        and reference_range_high is not None
    ):
        latest = data_points[-1][1]
        if latest < reference_range_low or latest > reference_range_high:
            ref_en = (
                f" The latest value is outside the report reference interval "
                f"({reference_range_low}–{reference_range_high})."
            )
            ref_hi = (
                f" नवीनतम मान रिपोर्ट संदर्भ सीमा "
                f"({reference_range_low}–{reference_range_high}) से बाहर है।"
            )

    en = (
        f"Your {test_name}{u} readings show {trend_en} "
        f"across {z.data_points_used} data point(s)."
        f"{streak_en}{delta_en}{ref_en}{anomaly_en}"
    )
    hi = (
        f"आपकी {test_name}{u} रीडिंग {z.data_points_used} डेटा पॉइंट में {trend_hi} दिखाती है।"
        f"{streak_hi}{delta_hi}{ref_hi}{anomaly_hi}"
    )

    return en, hi
