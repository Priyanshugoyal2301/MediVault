"""Aggregate per-phase eval JSON into unified benchmark artifact + markdown."""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    import conftest  # noqa: F401 — hyphenated services.* imports
except Exception:
    pass

EVAL_FILES = {
    "ocr": "datasets/evaluation/ocr_phase1_latest.json",
    "ocr_1a": "datasets/evaluation/ocr_phase1a_bench.json",
    "normalizer": "datasets/evaluation/normalizer_phase2_latest.json",
    "retrieval": "datasets/evaluation/retrieval_phase3_latest.json",
    "risk": "datasets/evaluation/risk_phase4_latest.json",
    "forecast": "datasets/evaluation/forecast_phase5_latest.json",
    "health_score": "datasets/evaluation/health_score_phase6_latest.json",
    "anomaly": "datasets/evaluation/anomaly_phase7_latest.json",
    "image_quality": "datasets/evaluation/image_quality_phase8_latest.json",
}


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cpu_probe() -> dict[str, Any]:
    import os

    try:
        import psutil  # type: ignore

        mem = psutil.virtual_memory()
        process = psutil.Process(os.getpid())
        rss = process.memory_info().rss / (1024 * 1024)
        return {
            "cpu_count": os.cpu_count(),
            "system_ram_gb": round(mem.total / (1024**3), 2),
            "process_rss_mb": round(rss, 2),
        }
    except Exception:
        return {
            "cpu_count": os.cpu_count(),
            "system_ram_gb": None,
            "process_rss_mb": None,
        }


def _gpu_probe() -> dict[str, Any]:
    try:
        import torch

        if torch.cuda.is_available():
            return {
                "available": True,
                "name": torch.cuda.get_device_name(0),
                "device_count": torch.cuda.device_count(),
            }
    except Exception:
        pass
    return {"available": False}


def _artifact_size_mb(path: Path) -> float | None:
    if not path.exists():
        return None
    total = 0
    if path.is_file():
        total = path.stat().st_size
    else:
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return round(total / (1024 * 1024), 3)


def collect(root: Path | None = None) -> dict[str, Any]:
    root = root or _ROOT
    components: dict[str, Any] = {}
    for key, rel in EVAL_FILES.items():
        data = _load(root / rel)
        components[key] = {
            "eval_path": rel,
            "present": data is not None,
            "metrics": data,
        }

    # model sizes from artifacts
    packages = {
        "ocr": "models/ocr/artifacts",
        "normalizer": "models/normalizer/artifacts",
        "retrieval": "models/retrieval/artifacts",
        "risk": "models/risk_prediction/artifacts",
        "forecast": "models/forecasting/artifacts",
        "health_score": "models/health_score/artifacts",
        "anomaly": "models/anomaly_detection/artifacts",
        "image_quality": "models/image_quality/artifacts",
    }
    sizes = {k: _artifact_size_mb(root / v) for k, v in packages.items()}

    # lightweight inference smoke timings (registry default off = safe)
    timings: dict[str, float] = {}
    try:
        from datetime import date, timedelta

        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import (
            get_anomaly_detector,
            get_biomarker_forecaster,
            get_document_parser,
            get_health_scorer,
            get_normalizer,
            get_quality_checker,
            get_retriever,
            get_risk_predictor,
            reset_registry_cache,
        )

        reset_feature_flags_cache()
        reset_registry_cache()

        def timed(name, fn):
            t0 = time.perf_counter()
            fn()
            timings[name] = round((time.perf_counter() - t0) * 1000, 3)

        timed("quality_passthrough_ms", lambda: get_quality_checker().check(b"%PDF-1.4", "application/pdf"))
        timed("normalizer_alias_ms", lambda: get_normalizer().normalize_test_name("HbA1c"))
        timed("risk_unavailable_ms", lambda: get_risk_predictor().predict([]))
        timed("forecast_unavailable_ms", lambda: get_biomarker_forecaster().forecast([]))
        timed("health_unavailable_ms", lambda: get_health_scorer().score([]))
        pts = [(date(2023, 1, 1) + timedelta(days=30 * i), 13.0 + 0.05 * i) for i in range(5)]
        timed("anomaly_statistical_ms", lambda: get_anomaly_detector().detect("Haemoglobin", pts, unit="g/dL"))
        timed("retriever_bm25_ms", lambda: get_retriever())
        timed("parser_legacy_ms", lambda: get_document_parser())
    except Exception as exc:
        timings["error"] = str(exc)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "platform": {
            "python": sys.version.split()[0],
            "system": platform.system(),
            "machine": platform.machine(),
            "cpu": _cpu_probe(),
            "gpu": _gpu_probe(),
        },
        "artifact_sizes_mb": sizes,
        "default_path_latency_ms": timings,
        "components": components,
        "notes": [
            "Default feature flags are OFF — latency figures are production-safe paths.",
            "Phase metrics come from prior offline synthetic/real-fixture evaluations.",
            "GPU optional; most models train/infer on CPU.",
        ],
    }


def write_markdown(report: dict[str, Any], out_md: Path) -> None:
    c = report["components"]
    lines = [
        "# Unified Benchmark Suite — MediVault ML Platform",
        "",
        f"**Generated:** {report['generated_at']}  ",
        f"**Python:** {report['platform']['python']} · **OS:** {report['platform']['system']} {report['platform']['machine']}",
        "",
        "## Host probes",
        "",
        f"- CPU count: `{report['platform']['cpu'].get('cpu_count')}`",
        f"- Process RSS (MB): `{report['platform']['cpu'].get('process_rss_mb')}`",
        f"- GPU available: `{report['platform']['gpu'].get('available')}`"
        + (
            f" ({report['platform']['gpu'].get('name')})"
            if report["platform"]["gpu"].get("available")
            else ""
        ),
        "",
        "## Production-safe path latency (flags default OFF)",
        "",
        "| Component | Latency (ms) |",
        "|-----------|--------------|",
    ]
    for k, v in (report.get("default_path_latency_ms") or {}).items():
        if k == "error":
            lines.append(f"| error | {v} |")
        else:
            lines.append(f"| `{k}` | {v} |")

    lines += [
        "",
        "## Artifact sizes (on-disk MB)",
        "",
        "| Package | Size (MB) |",
        "|---------|-----------|",
    ]
    for k, v in (report.get("artifact_sizes_mb") or {}).items():
        lines.append(f"| `{k}` | {v if v is not None else '—'} |")

    lines += [
        "",
        "## Component evaluation snapshot",
        "",
        "| # | Component | Eval artifact present | Headline metrics (from JSON) |",
        "|---|-----------|----------------------|------------------------------|",
    ]

    def headline(key: str, data: dict | None) -> str:
        if not data:
            return "missing eval JSON"
        if key == "ocr":
            return "see ocr_phase1_latest (field F1 bake-off)"
        if key == "ocr_1a":
            return "hardening timings"
        if key == "normalizer":
            return f"top1/f1 available in JSON keys: {', '.join(list(data.keys())[:6])}"
        if key == "retrieval":
            return f"MRR/Recall keys: {', '.join(list(data.keys())[:6])}"
        if key == "risk":
            return f"backend={data.get('backend') or data.get('model')}"
        if key == "forecast":
            return f"macro_mae={data.get('macro_mae')} e2e_ms={data.get('e2e_forecast_ms')}"
        if key == "health_score":
            return f"mae={data.get('mae')} r2={data.get('r2')} e2e_ms={data.get('e2e_score_explain_ms')}"
        if key == "anomaly":
            comp = data.get("comparison") or {}
            ifor = (comp.get("isolation_forest") or {}).get("pr_auc")
            return f"active={data.get('active_backend')} IF_PR-AUC={ifor}"
        if key == "image_quality":
            comp = data.get("comparison") or {}
            m = (comp.get("mobilenet_v3") or {}).get("f1_macro")
            return f"active={data.get('active_backend')} F1={m}"
        return "see JSON"

    order = [
        ("1 OCR", "ocr"),
        ("1A OCR harden", "ocr_1a"),
        ("2 Normalizer", "normalizer"),
        ("3 Retrieval", "retrieval"),
        ("4 Risk", "risk"),
        ("5 Forecast", "forecast"),
        ("6 Health score", "health_score"),
        ("7 Anomaly", "anomaly"),
        ("8 Image quality", "image_quality"),
    ]
    for label, key in order:
        block = c.get(key) or {}
        present = "yes" if block.get("present") else "no"
        lines.append(f"| {label} | present={present} | {headline(key, block.get('metrics'))} |")

    lines += [
        "",
        "## Known failure cases (cross-platform)",
        "",
        "| Component | Failure class | Mitigation |",
        "|-----------|---------------|------------|",
        "| OCR | Empty Unlimited response | Legacy fallback |",
        "| Normalizer | Unknown alias | Soft leave original / rules |",
        "| Retrieval | Dense load fail | BM25 fallback |",
        "| Risk / Forecast / Health / Anomaly ML | Init error | Unavailable or statistical path |",
        "| Image quality | Init error | OpenCV rules / passthrough |",
        "| All flags ON | Cumulative latency / memory | Staged enablement |",
        "",
        "## Notes",
        "",
    ]
    for n in report.get("notes") or []:
        lines.append(f"- {n}")
    lines.append("")
    lines.append("Per-phase detail: `docs/benchmark_phase*.md`.")
    lines.append("")
    lines.append("Regenerate: `python models/platform/benchmark_suite.py`")
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    report = collect()
    out_json = _ROOT / "datasets" / "evaluation" / "platform_benchmark_complete.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, _ROOT / "benchmark_complete.md")
    write_markdown(report, _ROOT / "docs" / "benchmark_complete.md")
    print(
        json.dumps(
            {
                "json": str(out_json),
                "md": str(_ROOT / "benchmark_complete.md"),
                "gpu": report["platform"]["gpu"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
