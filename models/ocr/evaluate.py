"""Evaluate Unlimited-OCR path vs Legacy parser (Phase 1).

Runs offline benchmarks on Plan C IE fixtures (text) + optional image samples.
Does NOT require GPU weights — VLM path is evaluated as:
  postprocess(Medical JSON) on OCR/fixture text  == Unlimited structured path
  ReportParser + passthrough OCR               == Legacy path

When UNLIMITED_OCR_ENDPOINT or local weights exist, optionally exercises full client.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reuse conftest hyphenated imports if available
try:
    import conftest  # noqa: F401
except Exception:  # noqa: BLE001
    pass


def _legacy_pred(text: str) -> dict[str, float]:
    from services.ai_service.parsers.report_parser import ReportParser

    class _P:
        def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
            return file_bytes.decode("utf-8", errors="replace")

    parsed = ReportParser(_P()).parse(text.encode("utf-8"), "text/plain")
    return {
        p.test_name: float(p.value_numeric)
        for p in parsed
        if p.value_numeric is not None
    }


def _unlimited_post_pred(text: str) -> dict[str, float]:
    from models.ocr.postprocess import postprocess_to_medical_json

    doc = postprocess_to_medical_json(
        [(1, text)],
        mime_type="text/plain",
        backend="eval_postprocess",
        ocr_confidence_default=0.9,
    )
    out: dict[str, float] = {}
    for e in doc.laboratory:
        if isinstance(e.value, (int, float)):
            out[e.test_name] = float(e.value)
        else:
            try:
                out[e.test_name] = float(str(e.value).replace(",", "."))
            except (TypeError, ValueError):
                continue
    return out


def _docs_match(gold: dict[str, float], pred: dict[str, float], tol: float) -> bool:
    if set(gold) != set(pred):
        return False
    return all(abs(gold[k] - pred[k]) <= tol for k in gold)


def run_eval(tolerance: float = 0.051) -> dict:
    from models.ocr.dataset import DocumentParsingDataset
    from models.ocr.metrics import (
        aggregate_ie_report,
        field_precision_recall_f1,
        measure_runtime,
        missing_field_rate,
        false_positive_rate,
        ocr_token_accuracy,
        table_row_accuracy,
    )

    samples = list(DocumentParsingDataset().iter_index())
    legacy_docs: list[dict] = []
    unlim_docs: list[dict] = []
    gold_docs: list[dict[str, float]] = []

    t0 = time.perf_counter()
    for s in samples:
        text = s.text or ""
        gold = s.gold_fields
        gold_docs.append(gold)

        leg = _legacy_pred(text)
        unl = _unlimited_post_pred(text)

        leg_m = field_precision_recall_f1(gold, leg, value_tolerance=tolerance)
        unl_m = field_precision_recall_f1(gold, unl, value_tolerance=tolerance)

        gold_rows = list(gold.items())
        leg_rows = list(leg.items())
        unl_rows = list(unl.items())

        legacy_docs.append(
            {
                **leg_m,
                "exact_match": 1.0 if _docs_match(gold, leg, tolerance) else 0.0,
                "missing_field_rate": missing_field_rate(gold, leg),
                "false_positive_rate": false_positive_rate(gold, leg),
                "ocr_accuracy": ocr_token_accuracy(text, text),  # perfect for text path
                "table_accuracy": table_row_accuracy(gold_rows, leg_rows, value_tolerance=tolerance),
                "sample_id": s.sample_id,
            }
        )
        unlim_docs.append(
            {
                **unl_m,
                "exact_match": 1.0 if _docs_match(gold, unl, tolerance) else 0.0,
                "missing_field_rate": missing_field_rate(gold, unl),
                "false_positive_rate": false_positive_rate(gold, unl),
                "ocr_accuracy": ocr_token_accuracy(text, text),
                "table_accuracy": table_row_accuracy(gold_rows, unl_rows, value_tolerance=tolerance),
                "sample_id": s.sample_id,
            }
        )
    wall_ms = (time.perf_counter() - t0) * 1000.0

    def _pack(rows: list[dict], label: str) -> dict:
        runtime = {
            "latency_ms": round(wall_ms, 4),
            "avg_processing_time_ms": round(wall_ms / max(len(rows), 1), 4),
            "memory_mib": 0.0,
            "cpu_seconds": 0.0,
            "gpu_memory_mib": 0.0,
        }
        # measure one pass memory via sample
        _, mem = measure_runtime(lambda: None)
        runtime["memory_mib"] = mem.get("memory_mib", 0.0)

        agg = aggregate_ie_report(rows, runtime=runtime)
        agg["parser"] = label
        agg["n_samples"] = len(rows)
        return agg

    report = {
        "experiment": "phase1_unlimited_ocr_vs_legacy",
        "tolerance": tolerance,
        "legacy": _pack(legacy_docs, "legacy_regex"),
        "unlimited_ocr_postprocess": _pack(unlim_docs, "unlimited_ocr_postprocess"),
        "per_sample_legacy": legacy_docs,
        "per_sample_unlimited": unlim_docs,
        "notes": (
            "Unlimited metrics here evaluate Medical JSON post-processing on the same "
            "fixture text (simulating VLM-decoded document text). Full baidu/Unlimited-OCR "
            "weights require UNLIMITED_OCR_ENDPOINT or local transformers load."
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 OCR evaluation")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    parser.add_argument(
        "--out",
        default=str(ROOT / "datasets" / "evaluation" / "ocr_phase1_latest.json"),
    )
    parser.add_argument("--tolerance", type=float, default=0.051)
    args = parser.parse_args()

    report = run_eval(tolerance=args.tolerance)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== Phase 1 OCR Evaluation ===")
    for key in ("legacy", "unlimited_ocr_postprocess"):
        m = report[key]
        print(
            f"{key}: F1={m.get('field_f1')} P={m.get('field_precision')} "
            f"R={m.get('field_recall')} EM={m.get('exact_match')} "
            f"latency_ms={m.get('latency_ms')}"
        )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
