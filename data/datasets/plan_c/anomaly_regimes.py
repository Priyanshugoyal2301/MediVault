"""
Mixed-regime anomaly bake-off (no training).

Hypotheses:
  H1: causal_z ∨ CUSUM remains best on spikes.
  H2: CUSUM improves F1 on gradual ramps/steps vs causal_z alone.
  H3: optional ref-range breach flag reduces FAR without killing recall.

Promote feature change only if ΔF1 ≥ 0.03 OR ΔFAR ≤ −0.02 at recall ≥ 0.95.
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import importlib.util


class _HyphenatedFinder:
    _DIRS = {"services": ROOT / "services", "packages": ROOT / "packages"}

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        parts = fullname.split(".")
        ns = parts[0]
        if ns not in cls._DIRS or len(parts) < 2:
            return None
        base = cls._DIRS[ns]
        pkg_dir = base / parts[1].replace("_", "-")
        if not pkg_dir.exists():
            return None
        rest = parts[2:]
        if not rest:
            init = pkg_dir / "__init__.py"
            if init.exists():
                return importlib.util.spec_from_file_location(
                    fullname, str(init), submodule_search_locations=[str(pkg_dir)]
                )
            return importlib.util.spec_from_file_location(
                fullname, None, submodule_search_locations=[str(pkg_dir)]
            )
        tp = pkg_dir.joinpath(*rest)
        init = tp / "__init__.py"
        py = tp.with_suffix(".py")
        if tp.is_dir() and init.exists():
            return importlib.util.spec_from_file_location(
                fullname, str(init), submodule_search_locations=[str(tp)]
            )
        if py.exists():
            return importlib.util.spec_from_file_location(fullname, str(py))
        return None


if not any(type(f).__name__ == "_HyphenatedFinder" for f in sys.meta_path):
    sys.meta_path.insert(0, _HyphenatedFinder)

from services.ai_service.anomaly.model import score_anomaly  # noqa: E402

HB_MEAN = 13.5
HB_STD = 1.2
REF_LOW, REF_HIGH = 12.0, 17.0
N_PER_REGIME = 100


def _dates(n: int) -> list[date]:
    start = date(2024, 1, 1)
    return [start + timedelta(days=30 * i) for i in range(n)]


def _metrics(y_true: list[bool], y_pred: list[bool]) -> dict:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    far = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "false_alert_rate": round(far, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def _gen_series(rng: random.Random, regime: str, anomalous: bool) -> list[tuple[date, float]]:
    n = rng.randint(6, 10)
    dates = _dates(n)
    values = [round(rng.gauss(HB_MEAN, HB_STD), 2) for _ in range(n)]
    if anomalous:
        if regime == "spike":
            values[-1] = round(HB_MEAN - 3.5 * HB_STD, 2)
        elif regime == "ramp":
            # Gradual decline over last 4 points
            for i, idx in enumerate(range(n - 4, n)):
                values[idx] = round(HB_MEAN - 0.9 * (i + 1), 2)
        elif regime == "step":
            # Level shift on last 3 points
            for idx in range(n - 3, n):
                values[idx] = round(HB_MEAN - 2.8, 2)
    return list(zip(dates, values))


def _predict(series: list[tuple[date, float]], mode: str) -> bool:
    result = score_anomaly(series)
    latest = series[-1][1]
    ref_breach = latest < REF_LOW or latest > REF_HIGH

    if mode == "prod_statistical_monitor":
        return result.is_anomaly
    if mode == "causal_z_only":
        return "causal_z" in result.triggers
    if mode == "cusum_only":
        return "cusum" in result.triggers
    if mode == "prod_or_ref_range":
        return result.is_anomaly or ref_breach
    if mode == "prod_and_ref_range":
        return result.is_anomaly and ref_breach
    raise ValueError(mode)


def run_anomaly_regimes(seed: int = 42) -> dict:
    rng = random.Random(seed)
    regimes = ["spike", "ramp", "step"]
    modes = [
        "prod_statistical_monitor",
        "causal_z_only",
        "cusum_only",
        "prod_or_ref_range",
        "prod_and_ref_range",
    ]

    # Build fixed dataset once
    dataset: list[tuple[str, bool, list]] = []
    for regime in regimes:
        for i in range(N_PER_REGIME):
            anomalous = i < int(N_PER_REGIME * 0.25)
            dataset.append((regime, anomalous, _gen_series(rng, regime, anomalous)))

    out: dict = {"experiment": "anomaly_mixed_regimes", "seed": seed, "methods": {}}
    for mode in modes:
        by_regime: dict = {}
        all_true: list[bool] = []
        all_pred: list[bool] = []
        for regime in regimes:
            yt, yp = [], []
            for r, anomalous, series in dataset:
                if r != regime:
                    continue
                pred = _predict(series, mode)
                yt.append(anomalous)
                yp.append(pred)
            by_regime[regime] = _metrics(yt, yp)
            all_true.extend(yt)
            all_pred.extend(yp)
        out["methods"][mode] = {
            "overall": _metrics(all_true, all_pred),
            "by_regime": by_regime,
        }

    prod = out["methods"]["prod_statistical_monitor"]["overall"]
    # Promotion candidates vs prod
    promotions = []
    for mode, blob in out["methods"].items():
        if mode == "prod_statistical_monitor":
            continue
        m = blob["overall"]
        df1 = m["f1"] - prod["f1"]
        dfar = m["false_alert_rate"] - prod["false_alert_rate"]
        # Guardian: never promote a rule that worsens FAR (demo trust).
        ok = (
            m["recall"] >= 0.95
            and dfar <= 0.0
            and (df1 >= 0.03 or dfar <= -0.02)
        )
        promotions.append({
            "mode": mode,
            "delta_f1": round(df1, 4),
            "delta_far": round(dfar, 4),
            "recall": m["recall"],
            "promote": ok,
            "notes": "FAR must not worsen vs production statistical_monitor",
        })
    out["promotion_decisions"] = promotions
    out["promote_any"] = any(p["promote"] for p in promotions)
    return out
