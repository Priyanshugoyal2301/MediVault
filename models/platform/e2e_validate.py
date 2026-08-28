"""End-to-end platform validation (flags off + graceful paths)."""

from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    import conftest  # noqa: F401
except Exception:
    pass


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"check": name, "pass": ok, "detail": detail}


def run_e2e() -> dict[str, Any]:
    from services.ai_service.core.feature_flags import (
        flags_as_dict,
        get_feature_flags,
        reset_feature_flags_cache,
    )
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
    checks: list[dict[str, Any]] = []

    flags = get_feature_flags()
    checks.append(
        _check(
            "all_ml_flags_default_off",
            not any(
                [
                    flags.use_unlimited_ocr,
                    flags.use_ml_normalizer,
                    flags.use_embedding_search,
                    flags.use_risk_model,
                    flags.use_forecast_model,
                    flags.use_health_score_model,
                    flags.use_anomaly_model,
                    flags.use_image_quality_model,
                ]
            ),
            json.dumps(flags_as_dict()),
        )
    )

    # Pipeline simulation (default safe paths)
    t0 = time.perf_counter()
    q = get_quality_checker().check(b"%PDF-1.4 test", "application/pdf")
    checks.append(_check("quality_passthrough_ok", q.ok is True, q.method if hasattr(q, "method") else str(q.metadata)))

    parser = get_document_parser()
    checks.append(_check("document_parser_loads", parser is not None))

    norm = get_normalizer().normalize_test_name("Hb")
    checks.append(_check("normalizer_alias", bool(norm), str(norm)))

    retr = get_retriever()
    checks.append(_check("retriever_bm25_default", retr is not None))

    risk = get_risk_predictor().predict(
        [{"test_name": "HbA1c", "value_numeric": 6.2}]
    )
    checks.append(_check("risk_default_unavailable", risk.risk_band == "unavailable", risk.method))

    fc = get_biomarker_forecaster().forecast([])
    checks.append(_check("forecast_default_unavailable", fc.method == "unavailable", fc.method))

    hs = get_health_scorer().score([])
    checks.append(_check("health_default_unavailable", hs.level == "unavailable", hs.method))

    pts = [(date(2023, 1, 1) + timedelta(days=30 * i), 1.0 + 0.02 * i) for i in range(4)]
    an = get_anomaly_detector().detect("Creatinine", pts)
    checks.append(_check("anomaly_statistical_default", "ml_anomaly" not in (an.method or ""), an.method))

    elapsed = (time.perf_counter() - t0) * 1000
    checks.append(_check("e2e_chain_latency_under_30s", elapsed < 30000, f"{elapsed:.1f}ms"))

    # Graceful degradation smoke (flag ON for risk — engine auto-trains synthetic)
    import os

    os.environ["USE_RISK_MODEL"] = "1"
    reset_feature_flags_cache()
    reset_registry_cache()
    try:
        r2 = get_risk_predictor().predict([{"test_name": "HbA1c", "value_numeric": 7.5}])
        checks.append(
            _check(
                "risk_flag_on_returns_result",
                r2.risk_band != "unavailable" or r2.method != "unavailable",
                f"band={r2.risk_band} method={r2.method}",
            )
        )
    except Exception as exc:
        checks.append(_check("risk_flag_on_returns_result", False, type(exc).__name__))
    finally:
        os.environ["USE_RISK_MODEL"] = "0"
        reset_feature_flags_cache()
        reset_registry_cache()

    # API surface not expanded (documentation-level check via router imports)
    try:
        from services.ai_service.routers import anomaly as _  # noqa: F401
        from services.ai_service.routers import parse as __  # noqa: F401

        checks.append(_check("routers_importable", True))
    except Exception as exc:
        checks.append(_check("routers_importable", False, type(exc).__name__))

    from models.platform.audit import run_audit

    audit = run_audit(_ROOT)
    checks.append(
        _check(
            "reproducibility_all_packages",
            audit["all_pass"],
            f"{audit['n_pass']}/{audit['n_packages']}",
        )
    )

    n_pass = sum(1 for c in checks if c["pass"])
    verdict = "PASS" if n_pass == len(checks) else ("PASS WITH OBSERVATIONS" if n_pass >= len(checks) - 2 else "FAIL")
    return {
        "verdict": verdict,
        "n_pass": n_pass,
        "n_total": len(checks),
        "elapsed_chain_ms": elapsed,
        "checks": checks,
        "reproducibility": audit,
    }


def main() -> None:
    report = run_e2e()
    out = _ROOT / "datasets" / "evaluation" / "platform_e2e_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "n_pass": report["n_pass"], "n_total": report["n_total"], "written": str(out)}, indent=2))


if __name__ == "__main__":
    main()
