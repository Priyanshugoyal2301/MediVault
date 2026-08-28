"""Phase 9 — platform hardening tests."""

from __future__ import annotations


def test_reproducibility_audit_all_pass():
    from models.platform.audit import run_audit

    r = run_audit()
    assert r["all_pass"] is True
    assert r["n_pass"] == 8


def test_experiment_tracking_disabled_by_default():
    from models.platform.experiment_tracking import tracking_enabled, experiment_run

    assert tracking_enabled() is False
    with experiment_run("unit") as exp:
        exp.log_metrics({"a": 1.0})


def test_e2e_validation_pass():
    from models.platform.e2e_validate import run_e2e

    r = run_e2e()
    assert r["verdict"] in ("PASS", "PASS WITH OBSERVATIONS")
    assert r["n_pass"] >= r["n_total"] - 1


def test_benchmark_collect():
    from models.platform.benchmark_suite import collect

    rep = collect()
    assert "components" in rep
    assert "platform" in rep
    assert "default_path_latency_ms" in rep
