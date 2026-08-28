"""
BM25+intent vs optional MiniLM hybrid bake-off.

Kill criterion (Plan C Guardian): promote dense only if
  ΔMRR ≥ 0.02 AND Hit@5 not worse.
Otherwise reject — keep MEDIVAULT_FAST_KB=1 / BM25 default.
"""

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


def _eval_mode(docs: list[dict], qa_pairs: list[dict], mode: str) -> dict:
    from services.ai_service.rag.retriever import load_knowledge_base, retrieve

    load_knowledge_base(docs, mode=mode)
    hits = 0
    mrr_sum = 0.0
    n = len(qa_pairs)
    for qa in qa_pairs:
        chunks = retrieve(qa["question"], top_k=5)
        texts = [c.text.lower() for c in chunks]
        first = None
        for rank, text in enumerate(texts, 1):
            if any(kw.lower() in text for kw in qa["expected_keywords"]):
                first = rank
                break
        if first is not None:
            hits += 1
            mrr_sum += 1.0 / first
    return {
        "mode": mode,
        "hit_at_5": round(hits / n, 4) if n else 0.0,
        "mrr": round(mrr_sum / n, 4) if n else 0.0,
        "n": n,
    }


def run_dense_bakeoff() -> dict:
    from data.datasets.evaluate_rag import LABELED_QA_PAIRS
    from services.ai_service.rag.ingester import load_documents

    docs = load_documents()
    bm25 = _eval_mode([{**d, "embedding": None} for d in docs], LABELED_QA_PAIRS, "bm25")

    hybrid = None
    dense_error = None
    try:
        from services.ai_service.rag.embedder import embed_text

        dense_docs = []
        for d in docs:
            row = dict(d)
            row["embedding"] = embed_text(d["chunk_text"])
            dense_docs.append(row)
        hybrid = _eval_mode(dense_docs, LABELED_QA_PAIRS, "hybrid")
    except Exception as exc:  # noqa: BLE001
        dense_error = f"{type(exc).__name__}: {exc}"

    metric_pass = False
    delta_mrr = None
    if hybrid is not None:
        delta_mrr = round(hybrid["mrr"] - bm25["mrr"], 4)
        metric_pass = delta_mrr >= 0.02 and hybrid["hit_at_5"] >= bm25["hit_at_5"]

    # Guardian demo-risk veto: cold MiniLM download is a stage killer.
    # Metric wins → optional warm path only; never change FAST_KB demo default.
    if metric_pass:
        decision = "CONDITIONAL_PROMOTE_WARM_DENSE_ONLY"
        promote_demo_default = False
    else:
        decision = "REJECT_DENSE_KEEP_BM25"
        promote_demo_default = False

    return {
        "experiment": "dense_bakeoff",
        "bm25": bm25,
        "hybrid": hybrid,
        "dense_error": dense_error,
        "delta_mrr": delta_mrr,
        "metric_gate_passed": metric_pass,
        "promote_dense": False,
        "promote_demo_default": promote_demo_default,
        "decision": decision,
        "integration": (
            "Keep MEDIVAULT_FAST_KB=1 for demos. Optional: FAST_KB=0 "
            "MEDIVAULT_USE_DENSE=1 after warming MiniLM cache."
            if metric_pass
            else "BM25 remains sole production retriever."
        ),
    }
