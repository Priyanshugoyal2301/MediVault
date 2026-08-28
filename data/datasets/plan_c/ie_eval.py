"""Field-level IE evaluation against synthetic fixtures."""

from __future__ import annotations

import sys
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


class _PassthroughOcr:
    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        return file_bytes.decode("utf-8", errors="replace")


def evaluate_ie() -> dict:
    from services.ai_service.parsers.report_parser import ReportParser

    from .ie_fixtures import load_fixtures

    parser = ReportParser(_PassthroughOcr())
    fixtures = load_fixtures()

    tp = fp = fn = 0
    per_fixture: list[dict] = []
    misses: list[str] = []

    for fx in fixtures:
        parsed = parser.parse(fx.text.encode("utf-8"), "text/plain")
        pred = {
            p.test_name: float(p.value_numeric)
            for p in parsed
            if p.value_numeric is not None
        }
        gold = {g.test_name: g.value for g in fx.gold}

        f_tp = f_fp = f_fn = 0
        for name, gval in gold.items():
            if name in pred and abs(pred[name] - gval) < 0.051:
                f_tp += 1
            else:
                f_fn += 1
                misses.append(f"{fx.fixture_id}:{name} expected={gval} got={pred.get(name)}")
        for name in pred:
            if name not in gold:
                f_fp += 1

        tp += f_tp
        fp += f_fp
        fn += f_fn
        prec = f_tp / (f_tp + f_fp) if (f_tp + f_fp) else 0.0
        rec = f_tp / (f_tp + f_fn) if (f_tp + f_fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per_fixture.append({
            "fixture_id": fx.fixture_id,
            "layout": fx.layout,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "tp": f_tp,
            "fp": f_fp,
            "fn": f_fn,
        })

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "experiment": "ie_field_f1",
        "n_fixtures": len(fixtures),
        "n_gold_fields": tp + fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "per_fixture": per_fixture,
        "misses": misses,
    }
