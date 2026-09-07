"""Guarded auto-train — run pre-training protector, then train + evaluate.

Usage (repo root):
  python models/platform/safe_train.py
  python models/platform/safe_train.py --skip-eval
  python models/platform/safe_train.py --phases normalizer,risk_prediction

All backend / safety decisions are made by train_guard.py (no interactive prompts).
Production USE_* flags stay OFF for this process.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from models.platform.train_guard import (  # noqa: E402
    GuardReport,
    build_guard_plan,
    write_report,
)


def _run(cmd: list[str], cwd: Path) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "seconds": round(time.time() - started, 2),
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-1500:],
        "ok": proc.returncode == 0,
    }


def run_safe_train(
    *,
    skip_eval: bool = False,
    only_phases: set[str] | None = None,
) -> dict[str, Any]:
    report: GuardReport = build_guard_plan(enforce_offline=True)
    guard_path = write_report(report)

    summary: dict[str, Any] = {
        "guard_ok": report.ok,
        "guard_report": str(guard_path),
        "decisions": report.decisions,
        "warnings": report.warnings,
        "blockers": report.blockers,
        "results": [],
    }

    if not report.ok:
        summary["status"] = "BLOCKED"
        return summary

    py = sys.executable
    for plan in report.phases:
        if plan.skip_reason:
            summary["results"].append(
                {
                    "id": plan.id,
                    "phase": plan.phase,
                    "status": "SKIPPED",
                    "reason": plan.skip_reason,
                }
            )
            continue
        if only_phases and plan.id not in only_phases:
            summary["results"].append(
                {
                    "id": plan.id,
                    "phase": plan.phase,
                    "status": "SKIPPED",
                    "reason": "not in --phases filter",
                }
            )
            continue

        train_cmd = [py, str(_ROOT / plan.train_script)]
        if plan.backend:
            train_cmd.extend(["--backend", plan.backend])

        train_res = _run(train_cmd, _ROOT)
        entry: dict[str, Any] = {
            "id": plan.id,
            "phase": plan.phase,
            "backend": plan.backend,
            "train": train_res,
        }

        if not train_res["ok"]:
            entry["status"] = "TRAIN_FAILED"
            summary["results"].append(entry)
            continue

        if skip_eval:
            entry["status"] = "TRAIN_OK"
            summary["results"].append(entry)
            continue

        eval_cmd = [py, str(_ROOT / plan.evaluate_script)]
        eval_res = _run(eval_cmd, _ROOT)
        entry["evaluate"] = eval_res
        entry["status"] = "OK" if eval_res["ok"] else "EVAL_FAILED"
        summary["results"].append(entry)

    failed = [
        r
        for r in summary["results"]
        if r.get("status") in {"TRAIN_FAILED", "EVAL_FAILED"}
    ]
    summary["status"] = "PASS" if not failed else "PARTIAL_FAIL"
    summary["failed_count"] = len(failed)
    summary["ok_count"] = sum(1 for r in summary["results"] if r.get("status") in {"OK", "TRAIN_OK"})

    out = _ROOT / "datasets" / "evaluation" / "safe_train_run_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["run_report"] = str(out)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guarded MediVault offline auto-train (safe decisions, no prompts)"
    )
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        help="Train only; skip evaluate.py",
    )
    parser.add_argument(
        "--phases",
        default="",
        help="Comma-separated phase ids (e.g. normalizer,risk_prediction)",
    )
    args = parser.parse_args()
    only = {p.strip() for p in args.phases.split(",") if p.strip()} or None

    print("=== MediVault training guard ===")
    summary = run_safe_train(skip_eval=args.skip_eval, only_phases=only)

    # Compact console summary
    print(json.dumps(
        {
            "status": summary["status"],
            "guard_ok": summary["guard_ok"],
            "backends": summary.get("decisions", {}).get("backends"),
            "warnings": summary.get("warnings"),
            "blockers": summary.get("blockers"),
            "ok_count": summary.get("ok_count"),
            "failed_count": summary.get("failed_count"),
            "phases": [
                {
                    "id": r["id"],
                    "backend": r.get("backend"),
                    "status": r.get("status"),
                }
                for r in summary.get("results", [])
            ],
            "guard_report": summary.get("guard_report"),
            "run_report": summary.get("run_report"),
        },
        indent=2,
    ))

    if summary["status"] == "BLOCKED":
        return 2
    if summary["status"] == "PARTIAL_FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
