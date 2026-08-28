"""Re-measure tone-violation rate after Plan C sanitizer + KB scrub."""

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


def run_tone_eval() -> dict:
    from data.datasets.evaluate_rag import LABELED_QA_PAIRS
    from services.ai_service.rag.ingester import load_documents
    from services.ai_service.rag.retriever import load_knowledge_base, retrieve
    from services.ai_service.rag.synthesizer import synthesize

    docs = load_documents()
    for d in docs:
        d.pop("embedding", None)
    load_knowledge_base(docs, mode="bm25")

    n = len(LABELED_QA_PAIRS)
    viol = 0
    cite_ok = 0
    for qa in LABELED_QA_PAIRS:
        chunks = retrieve(qa["question"], top_k=5)
        ans = synthesize(qa["question"], chunks)["answer_en"].lower()
        if "you have" in ans or "diagnosed with" in ans:
            viol += 1
        if chunks and synthesize(qa["question"], chunks)["citations"]:
            cite_ok += 1

    rate = round(viol / n, 4) if n else 0.0
    # Plan B baseline was 0.72; target ≤ 0.10
    return {
        "experiment": "tone_scrub",
        "tone_violation_rate": rate,
        "violations": viol,
        "n": n,
        "citation_present_rate": round(cite_ok / n, 4) if n else 0.0,
        "baseline_plan_b": 0.72,
        "target": 0.10,
        "promote": rate <= 0.10,
        "decision": "PROMOTE_TONE_SCRUB" if rate <= 0.10 else "PARTIAL_TONE_IMPROVEMENT",
    }
