"""Evaluate rule-based vs ML medical test normalization."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _rule_normalize(raw: str) -> str:
    """Standalone rule path using AliasNormalizer when available."""
    try:
        from services.ai_service.adapters.normalizer import AliasNormalizer

        return AliasNormalizer().normalize_test_name(raw)
    except Exception:
        from models.normalizer.vocabulary import alias_lookup_table
        from models.normalizer.preprocess import preprocess_for_exact

        table = alias_lookup_table()
        key = preprocess_for_exact(raw)
        return table.get(key, (raw or "").strip())


def evaluate(config_path: Path | None = None) -> dict:
    from models.normalizer.config_loader import load_config
    from models.normalizer.dataset import ensure_dataset_files, load_eval_pairs
    from models.normalizer.infer import MedicalTestNormalizer
    from models.normalizer.metrics import (
        confusion_matrix,
        loinc_accuracy,
        precision_recall_f1,
        summarize_latency,
        top1_accuracy,
        topk_accuracy,
        unknown_term_accuracy,
    )
    from models.normalizer.vocabulary import loinc_for

    cfg = load_config(config_path, validate=True)
    data_dir = Path(cfg["paths"]["train_data"])
    if not data_dir.is_absolute():
        data_dir = (Path(__file__).resolve().parent / data_dir).resolve()
    ensure_dataset_files(data_dir)
    rows = load_eval_pairs(data_dir)

    ml = MedicalTestNormalizer(cfg, auto_train_if_missing=True)

    y_true: list[str] = []
    y_rule: list[str] = []
    y_ml: list[str] = []
    y_ml_top3: list[list[str]] = []
    gold_unk: list[bool] = []
    pred_unk: list[bool] = []
    gold_loinc: list[str | None] = []
    pred_loinc: list[str | None] = []
    lat_ml: list[float] = []
    lat_rule: list[float] = []

    for r in rows:
        raw = str(r.get("raw") or "")
        gold = str(r.get("canonical") or "")
        unknown = bool(r.get("unknown"))
        g_loinc = r.get("loinc") or (None if unknown else loinc_for(gold))

        t0 = time.perf_counter()
        rule = _rule_normalize(raw)
        lat_rule.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        result = ml.normalize(raw)
        lat_ml.append((time.perf_counter() - t0) * 1000)

        y_true.append(gold if not unknown else "__UNKNOWN__")
        y_rule.append(rule if not unknown else ("__UNKNOWN__" if rule == raw.strip() else rule))
        # For unknown gold, ML success = predicted unknown_term
        if unknown:
            y_ml.append("__UNKNOWN__" if result.unknown_term else result.canonical_name)
        else:
            y_ml.append(result.canonical_name)

        tops = [result.canonical_name] + [a.canonical_name for a in result.alternatives]
        y_ml_top3.append(tops)
        gold_unk.append(unknown)
        pred_unk.append(bool(result.unknown_term))
        gold_loinc.append(g_loinc)
        pred_loinc.append(result.loinc)

    # For top1 on known only
    known_idx = [i for i, u in enumerate(gold_unk) if not u]
    yt = [y_true[i] for i in known_idx]
    yr = [y_rule[i] for i in known_idx]
    ym = [y_ml[i] for i in known_idx]
    ym3 = [y_ml_top3[i] for i in known_idx]

    report = {
        "model": "medical_test_normalizer",
        "backend": ml.backend_name,
        "n_eval": len(rows),
        "n_known": len(known_idx),
        "rule_based": {
            "top1_accuracy": top1_accuracy(yt, yr),
            **precision_recall_f1(yt, yr),
            "latency": summarize_latency([lat_rule[i] for i in known_idx] or lat_rule),
        },
        "ml_normalizer": {
            "top1_accuracy": top1_accuracy(yt, ym),
            "top3_accuracy": topk_accuracy(yt, ym3, k=3),
            **precision_recall_f1(yt, ym),
            "unknown_term_accuracy": unknown_term_accuracy(gold_unk, pred_unk),
            "loinc_mapping_accuracy": loinc_accuracy(gold_loinc, pred_loinc),
            "latency": summarize_latency(lat_ml),
            "confusion": confusion_matrix(yt, ym, top_n=20),
        },
        "notes": [
            "Rule path uses AliasNormalizer (service default when flag off).",
            "ML path = alias exact OR char_tfidf/ModernBERT/ClinicalBERT NN.",
            "Default active_backend=char_tfidf keeps deploy offline-safe.",
        ],
    }

    # Config paths like ../../datasets/... are relative to models/normalizer/
    out = Path(cfg["paths"]["evaluation_out"])
    if not out.is_absolute():
        out = (Path(__file__).resolve().parent / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()
    evaluate(args.config)


if __name__ == "__main__":
    main()
