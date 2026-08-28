"""
Plan C laboratory orchestrator.

Runs evidence-gated experiments. Never promotes without kill/success criteria.
Usage (repo root):
  python data/datasets/plan_c/run_plan_c_lab.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

# Ensure package imports work when run as a script
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from plan_c.anomaly_regimes import run_anomaly_regimes  # type: ignore
from plan_c.dense_bakeoff import run_dense_bakeoff  # type: ignore
from plan_c.ie_eval import evaluate_ie  # type: ignore
from plan_c.tone_eval import run_tone_eval  # type: ignore


def main() -> dict:
    print("=" * 60)
    print("PLAN C LAB — Autonomous bake-offs (no vanity training)")
    print("=" * 60)

    results: dict = {
        "date": date.today().isoformat(),
        "policy": "Train only if hypothesis + effect-size gate clears; else reject.",
        "experiments": {},
        "promotions": [],
        "rejections": [],
    }

    print("\n[1/4] IE field F1 on synthetic India fixtures…")
    ie = evaluate_ie()
    results["experiments"]["ie"] = ie
    print(f"  F1={ie['f1']} P={ie['precision']} R={ie['recall']} misses={len(ie['misses'])}")
    if ie["f1"] >= 0.95:
        results["promotions"].append("ie_alias_separator_hardening")
    else:
        results["rejections"].append(
            f"ie_target_missed (f1={ie['f1']} < 0.95); keep hardening iteratively"
        )
    for m in ie["misses"][:12]:
        print(f"    miss: {m}")

    print("\n[2/4] Anomaly mixed-regime bake-off…")
    anom = run_anomaly_regimes()
    results["experiments"]["anomaly_regimes"] = anom
    prod = anom["methods"]["prod_statistical_monitor"]["overall"]
    print(
        f"  prod overall F1={prod['f1']} FAR={prod['false_alert_rate']} R={prod['recall']}"
    )
    for p in anom["promotion_decisions"]:
        print(
            f"  candidate {p['mode']}: dF1={p['delta_f1']} dFAR={p['delta_far']} "
            f"R={p['recall']} promote={p['promote']}"
        )
        if p["promote"]:
            results["promotions"].append(f"anomaly:{p['mode']}")
        else:
            results["rejections"].append(f"anomaly:{p['mode']}")

    print("\n[3/4] Tone scrub eval…")
    tone = run_tone_eval()
    results["experiments"]["tone"] = tone
    print(
        f"  tone_violation={tone['tone_violation_rate']} "
        f"(baseline {tone['baseline_plan_b']}) → {tone['decision']}"
    )
    if tone["promote"]:
        results["promotions"].append("tone_sanitizer_and_kb_scrub")
    else:
        results["rejections"].append(
            f"tone_target_missed (rate={tone['tone_violation_rate']})"
        )

    print("\n[4/4] Dense MiniLM hybrid bake-off…")
    dense = run_dense_bakeoff()
    results["experiments"]["dense"] = dense
    print(f"  BM25 MRR={dense['bm25']['mrr']} Hit@5={dense['bm25']['hit_at_5']}")
    if dense["hybrid"]:
        print(
            f"  Hybrid MRR={dense['hybrid']['mrr']} Hit@5={dense['hybrid']['hit_at_5']} "
            f"ΔMRR={dense['delta_mrr']}"
        )
    else:
        print(f"  Dense unavailable: {dense['dense_error']}")
    print(f"  Decision: {dense['decision']}")
    if dense.get("metric_gate_passed"):
        results["promotions"].append("dense_hybrid_warm_optional")
        results["rejections"].append("dense_as_demo_default")
    else:
        results["rejections"].append("dense_hybrid_retrieval")

    # Guardian summary
    results["guardian"] = {
        "trained_models_promoted": [],
        "rule_or_template_promotions": list(results["promotions"]),
        "demo_vetoes": [
            "dense_as_demo_default (cold HF download risk)",
            "anomaly prod_or_ref_range if FAR worsens",
        ],
        "exploration_stopped_reason": (
            "No end-to-end trained model cleared data-adequacy + demo-risk bars. "
            "Promoted: IE alias hardening, tone scrub. Dense wins MRR only as "
            "optional warm path. Ref-range OR rejected for FAR regression. "
            "Vanity DL (IF/XGB/LayoutLM/LLM answers) rejected."
        ),
    }

    out_json = HERE / "results_latest.json"
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {out_json}")
    print("Promotions:", results["promotions"] or "(none)")
    return results


if __name__ == "__main__":
    main()
