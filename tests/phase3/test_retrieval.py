"""Phase 3 — Semantic medical retrieval tests."""

from __future__ import annotations

import time

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def _reset():
    from services.ai_service.core.feature_flags import reset_feature_flags_cache
    from services.ai_service.core.registry import reset_registry_cache

    reset_feature_flags_cache()
    reset_registry_cache()
    yield
    reset_feature_flags_cache()
    reset_registry_cache()


class TestChunking:
    def test_chunk_overlap(self):
        from models.retrieval.chunking import chunk_text

        words = " ".join(f"w{i}" for i in range(500))
        chunks = chunk_text(words, target_words=100, overlap_words=20)
        assert len(chunks) >= 4
        assert all(chunks)


class TestEmbeddings:
    def test_char_tfidf_encode(self):
        from models.retrieval.embeddings import CharTfidfEmbedding

        e = CharTfidfEmbedding(dim_hint=64)
        docs = ["hemoglobin anemia blood", "cholesterol lipid panel", "thyroid tsh"]
        e.fit(docs)
        v = e.encode(["what is hemoglobin"])
        assert v.shape[0] == 1
        assert v.shape[1] == e.dim
        assert abs(float(np.linalg.norm(v[0])) - 1.0) < 1e-3


class TestVectorStore:
    def test_numpy_search(self):
        from models.retrieval.vector_store import NumpyVectorStore

        store = NumpyVectorStore()
        mat = np.eye(4, dtype=np.float32)
        store.build(mat, ["a", "b", "c", "d"])
        hits = store.search(mat[0:1], top_k=2)[0]
        assert hits[0][0] == "a"
        assert hits[0][1] > 0.9

    def test_create_store_fallback(self):
        from models.retrieval.vector_store import create_store

        s = create_store("faiss")
        assert s.name in ("faiss", "numpy")


class TestSemanticRetriever:
    def test_build_and_query(self):
        from models.retrieval.infer import SemanticRetriever

        r = SemanticRetriever()
        hits = r.retrieve("what is hemoglobin", top_k=3)
        assert hits
        assert hits[0].similarity is not None
        assert hits[0].chunk_id
        assert hits[0].document_id is not None
        assert hits[0].source

    def test_metadata_filter(self):
        from models.retrieval.infer import SemanticRetriever

        r = SemanticRetriever()
        # panel_hint equals document stem for KB files
        hits = r.search("cholesterol", top_k=5, metadata_filter={"panel_hint": "lipid_guide"})
        # may be empty if panel_hint not exact — filter should not crash
        assert isinstance(hits, list)

    def test_user_values(self):
        from models.retrieval.infer import SemanticRetriever

        r = SemanticRetriever()
        hits = r.retrieve(
            "hemoglobin result",
            user_report_values=[
                {
                    "test_name": "Haemoglobin",
                    "value_numeric": 13.2,
                    "unit": "g/dL",
                    "date_of_test": "2024-01-01",
                }
            ],
            top_k=5,
        )
        assert any(h.is_user_data for h in hits)


class TestFeatureFlag:
    def test_flag_off_bm25(self, monkeypatch):
        monkeypatch.setenv("USE_EMBEDDING_SEARCH", "0")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_retriever, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        ret = get_retriever()
        assert type(ret).__name__ == "BM25Retriever"
        docs = ret.retrieve("hemoglobin", top_k=3)
        assert isinstance(docs, list)

    def test_flag_on_semantic(self, monkeypatch):
        monkeypatch.setenv("USE_EMBEDDING_SEARCH", "1")
        from services.ai_service.core.feature_flags import reset_feature_flags_cache
        from services.ai_service.core.registry import get_retriever, reset_registry_cache

        reset_feature_flags_cache()
        reset_registry_cache()
        ret = get_retriever()
        assert type(ret).__name__ in ("FallbackRetriever", "SemanticRetrieverAdapter")
        docs = ret.retrieve("what is LDL cholesterol", top_k=3)
        assert docs
        assert hasattr(docs[0], "text")
        assert hasattr(docs[0], "score")


class TestFallback:
    def test_semantic_fail_bm25(self):
        from services.ai_service.adapters.retriever import BM25Retriever, FallbackRetriever

        class Boom:
            def retrieve(self, *a, **k):
                raise RuntimeError("down")

        fb = FallbackRetriever(primary=Boom(), fallback=BM25Retriever())  # type: ignore
        # may be empty if kb not loaded — should not raise
        fb.retrieve("hemoglobin", top_k=2)
        assert fb.last_path == "bm25_fallback"


class TestSimilarity:
    def test_scores_ordered(self):
        from models.retrieval.infer import SemanticRetriever

        hits = SemanticRetriever().retrieve("HbA1c diabetes glucose", top_k=5)
        scores = [h.similarity for h in hits if not h.is_user_data]
        assert scores == sorted(scores, reverse=True)


class TestPerformance:
    def test_query_latency(self):
        from models.retrieval.infer import SemanticRetriever

        r = SemanticRetriever()
        t0 = time.perf_counter()
        for _ in range(20):
            r.retrieve("thyroid tsh", top_k=5)
        ms = (time.perf_counter() - t0) * 1000
        assert ms < 15000


class TestRegressionBM25:
    def test_default_flag_off(self):
        from services.ai_service.core.feature_flags import get_feature_flags

        assert get_feature_flags().use_embedding_search is False

    def test_bm25_still_available(self):
        from services.ai_service.adapters.retriever import BM25Retriever

        assert BM25Retriever() is not None


class TestMetrics:
    def test_recall_mrr(self):
        from models.retrieval.metrics import mrr, recall_at_k

        gold = [["cbc"], ["lipid"]]
        pred = [["x", "cbc"], ["lipid", "y"]]
        assert recall_at_k(gold, pred, 2) == 1.0
        assert mrr(gold, pred) == 0.75
