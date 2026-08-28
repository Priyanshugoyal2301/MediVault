"""Evaluate BM25 vs Semantic retrieval."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import conftest  # noqa: E402,F401 — hyphenated service path aliases


def evaluate(config_path: Path | None = None) -> dict:
    from models.retrieval.config_loader import load_config
    from models.retrieval.dataset import load_eval_benchmark
    from models.retrieval.infer import SemanticRetriever, resolve_repo_path
    from models.retrieval.metrics import (
        keyword_hit,
        mrr,
        ndcg_at_k,
        precision_at_k,
        recall_at_k,
    )

    cfg = load_config(config_path, validate=True)
    data_dir = resolve_repo_path(cfg["paths"]["train_data"])
    rows = load_eval_benchmark(data_dir)

    try:
        from services.ai_service.rag.bootstrap import bootstrap_knowledge_base
        from services.ai_service.rag import retriever as rag_ret

        bootstrap_knowledge_base()
    except Exception:
        from models.retrieval.chunking import load_kb_directory
        from services.ai_service.rag.retriever import load_knowledge_base
        from services.ai_service.rag import retriever as rag_ret

        kb = resolve_repo_path(cfg["paths"]["knowledge_base"])
        chunks = load_kb_directory(kb)
        mapped = [
            {
                "chunk_text": c["chunk_text"],
                "source_title": c["source_title"],
                "source_url": c.get("source_url"),
            }
            for c in chunks
        ]
        load_knowledge_base(mapped, mode="bm25")

    semantic = SemanticRetriever(cfg, auto_build_if_missing=True)
    if semantic.index_size < 2:
        semantic.build_index()

    bm25_ids: list[list[str]] = []
    sem_ids: list[list[str]] = []
    gold_ids: list[list[str]] = []
    lat_bm25: list[float] = []
    lat_sem: list[float] = []
    bm25_kw_hits = 0
    sem_kw_hits = 0

    for r in rows:
        q = r["question"]
        kws = r.get("expected_keywords") or []
        gold = list(r.get("expected_sources") or [])
        gold_ids.append(gold)

        t0 = time.perf_counter()
        bchunks = rag_ret.retrieve(q, top_k=10)
        lat_bm25.append((time.perf_counter() - t0) * 1000)
        b_sources: list[str] = []
        b_text = ""
        for c in bchunks:
            b_text += " " + c.text
            src = (c.source or "").lower()
            for g in gold:
                if g.lower() in src or g.lower() in c.text.lower():
                    b_sources.append(g.lower())
            b_sources.append(src[:40])
        bm25_ids.append(list(dict.fromkeys(b_sources)))
        if keyword_hit(b_text, kws):
            bm25_kw_hits += 1

        t0 = time.perf_counter()
        shits = semantic.retrieve(q, top_k=10)
        lat_sem.append((time.perf_counter() - t0) * 1000)
        s_sources: list[str] = []
        s_text = ""
        for h in shits:
            s_text += " " + h.text
            src = (h.source or "").lower()
            panel = str((h.metadata or {}).get("panel_hint") or h.document_id or "")
            for g in gold:
                if (
                    g.lower() in src
                    or g.lower() in panel.lower()
                    or g.lower() in h.text.lower()
                ):
                    s_sources.append(g.lower())
            s_sources.append(panel.lower() or src[:40])
        sem_ids.append(list(dict.fromkeys(s_sources)))
        if keyword_hit(s_text, kws):
            sem_kw_hits += 1

    n = max(1, len(rows))
    report = {
        "model": "semantic_medical_retriever",
        "embedding_backend": semantic.backend_name,
        "vector_store": semantic.store_name,
        "index_chunks": semantic.index_size,
        "n_queries": len(rows),
        "bm25": {
            "keyword_hit_rate": bm25_kw_hits / n,
            "recall@5": recall_at_k(gold_ids, bm25_ids, 5),
            "recall@10": recall_at_k(gold_ids, bm25_ids, 10),
            "precision@5": precision_at_k(gold_ids, bm25_ids, 5),
            "mrr": mrr(gold_ids, bm25_ids),
            "ndcg@5": ndcg_at_k(gold_ids, bm25_ids, 5),
            "latency_ms_mean": sum(lat_bm25) / n,
            "latency_ms_p95": sorted(lat_bm25)[int(0.95 * (n - 1))] if lat_bm25 else 0,
        },
        "semantic": {
            "keyword_hit_rate": sem_kw_hits / n,
            "recall@5": recall_at_k(gold_ids, sem_ids, 5),
            "recall@10": recall_at_k(gold_ids, sem_ids, 10),
            "precision@5": precision_at_k(gold_ids, sem_ids, 5),
            "mrr": mrr(gold_ids, sem_ids),
            "ndcg@5": ndcg_at_k(gold_ids, sem_ids, 5),
            "latency_ms_mean": sum(lat_sem) / n,
            "latency_ms_p95": sorted(lat_sem)[int(0.95 * (n - 1))] if lat_sem else 0,
        },
        "notes": [
            "Gold labels are panel stems (cbc/lipid/thyroid/hba1c/general).",
            "Default semantic embeddings are offline char_tfidf unless RETRIEVAL_ALLOW_HF=1.",
            "Primary architecture config: BGE-small; fallback MiniLM.",
        ],
    }

    out = resolve_repo_path(cfg["paths"]["evaluation_out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=None)
    args = p.parse_args()
    evaluate(args.config)


if __name__ == "__main__":
    main()
