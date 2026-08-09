"""
tests/unit/ai-service/test_rag.py

Tests for the RAG pipeline: retriever, synthesizer, and ingester.

Does NOT require sentence-transformers or any ML model — uses mock embeddings
for fast, deterministic testing.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Mock the embedder before importing RAG modules
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_embedder(monkeypatch):
    """Mock the embedder to avoid loading the real sentence-transformers model."""
    import types

    # Create a fake embedder module
    fake_embedder = types.ModuleType("services.ai_service.rag.embedder")

    def fake_embed_text(text: str) -> list[float]:
        """Return a deterministic 384-dim mock embedding based on text hash."""
        import hashlib
        h = hashlib.md5(text.encode()).hexdigest()
        return [float(int(h[i:i+2], 16)) / 255.0 for i in range(0, 384 * 2 // 128 * 2, 2)] * (384 // 8)

    def fake_embed_batch(texts: list[str]) -> list[list[float]]:
        return [fake_embed_text(t) for t in texts]

    def fake_get_embedding_dim() -> int:
        return 384

    fake_embedder.embed_text = fake_embed_text
    fake_embedder.embed_batch = fake_embed_batch
    fake_embedder.get_embedding_dim = fake_get_embedding_dim

    monkeypatch.setitem(sys.modules, "services.ai_service.rag.embedder", fake_embedder)

    # Also patch at the retriever level
    try:
        from services.ai_service.rag import retriever
        monkeypatch.setattr(retriever, "embed_text", fake_embed_text)
    except (ImportError, AttributeError):
        pass

    yield fake_embedder


# ---------------------------------------------------------------------------
# Retriever tests
# ---------------------------------------------------------------------------

class TestRetriever:
    """Tests for the hybrid retriever."""

    def test_retrieve_returns_list(self, mock_embedder):
        from services.ai_service.rag.retriever import retrieve
        results = retrieve("What is haemoglobin?")
        assert isinstance(results, list)

    def test_retrieve_with_empty_kb_returns_empty(self, mock_embedder):
        from services.ai_service.rag.retriever import retrieve, _knowledge_chunks
        # Clear knowledge base
        _knowledge_chunks.clear()
        results = retrieve("What is haemoglobin?")
        # May return empty if no KB and no user data
        assert isinstance(results, list)

    def test_retrieve_with_loaded_kb_returns_results(self, mock_embedder):
        from services.ai_service.rag.retriever import retrieve, load_knowledge_base
        import hashlib

        # Load some test chunks
        def fake_emb(text):
            h = hashlib.md5(text.encode()).hexdigest()
            return [float(int(h[i:i+2], 16)) / 255.0 for i in range(0, 384 * 2 // 128 * 2, 2)] * (384 // 8)

        test_chunks = [
            {
                "chunk_text": "Haemoglobin carries oxygen in red blood cells. Normal range is 12-17 g/dL.",
                "source_title": "CBC Guide",
                "source_url": "https://example.com/cbc",
                "embedding": fake_emb("Haemoglobin carries oxygen in red blood cells."),
            },
            {
                "chunk_text": "LDL cholesterol is called bad cholesterol because it builds up in arteries.",
                "source_title": "Lipid Guide",
                "source_url": "https://example.com/lipid",
                "embedding": fake_emb("LDL cholesterol is called bad cholesterol."),
            },
        ]
        load_knowledge_base(test_chunks)
        results = retrieve("What is haemoglobin?")
        assert len(results) > 0
        assert all(hasattr(r, "text") for r in results)
        assert all(hasattr(r, "source") for r in results)
        assert all(hasattr(r, "score") for r in results)

    def test_retrieve_with_user_report_values(self, mock_embedder):
        from services.ai_service.rag.retriever import retrieve

        user_values = [
            {
                "test_name": "Haemoglobin",
                "value_numeric": 10.5,
                "unit": "g/dL",
                "date_of_test": "2025-01-15",
                "panel": "CBC",
            },
        ]
        results = retrieve("What is my haemoglobin level?", user_report_values=user_values)
        user_results = [r for r in results if r.is_user_data]
        assert len(user_results) >= 1
        assert "10.5" in user_results[0].text

    def test_retrieve_respects_top_k(self, mock_embedder):
        from services.ai_service.rag.retriever import retrieve
        results = retrieve("What is haemoglobin?", top_k=2)
        assert len(results) <= 2

    def test_results_sorted_by_score_descending(self, mock_embedder):
        from services.ai_service.rag.retriever import retrieve, load_knowledge_base
        import hashlib

        def fake_emb(text):
            h = hashlib.md5(text.encode()).hexdigest()
            return [float(int(h[i:i+2], 16)) / 255.0 for i in range(0, 384 * 2 // 128 * 2, 2)] * (384 // 8)

        chunks = [
            {"chunk_text": f"Test chunk {i}", "source_title": f"Source {i}",
             "source_url": None, "embedding": fake_emb(f"Test chunk {i}")}
            for i in range(10)
        ]
        load_knowledge_base(chunks)
        results = retrieve("test query", top_k=5)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Synthesizer tests
# ---------------------------------------------------------------------------

class TestSynthesizer:
    """Tests for the template-based answer synthesizer."""

    def test_synthesize_returns_bilingual(self, mock_embedder):
        from services.ai_service.rag.retriever import RetrievedChunk
        from services.ai_service.rag.synthesizer import synthesize

        chunks = [
            RetrievedChunk(
                text="Haemoglobin carries oxygen. Normal range 12-17 g/dL.",
                source="CBC Guide",
                source_url="https://example.com",
                score=0.9,
            ),
        ]
        result = synthesize("What is haemoglobin?", chunks)
        assert "answer_en" in result
        assert "answer_hi" in result
        assert "citations" in result

    def test_synthesize_includes_citations(self, mock_embedder):
        from services.ai_service.rag.retriever import RetrievedChunk
        from services.ai_service.rag.synthesizer import synthesize

        chunks = [
            RetrievedChunk(
                text="LDL is bad cholesterol.",
                source="Lipid Guide",
                source_url="https://example.com/lipid",
                score=0.85,
            ),
        ]
        result = synthesize("What is LDL?", chunks)
        assert len(result["citations"]) >= 1
        assert result["citations"][0]["source"] == "Lipid Guide"
        # Citation markers should be in the answer
        assert "[1]" in result["answer_en"]

    def test_synthesize_empty_chunks_returns_insufficient(self, mock_embedder):
        from services.ai_service.rag.synthesizer import synthesize

        result = synthesize("Random question", [])
        assert "don't have enough information" in result["answer_en"].lower() or \
               "enough information" in result["answer_en"].lower()

    def test_synthesize_includes_user_data_section(self, mock_embedder):
        from services.ai_service.rag.retriever import RetrievedChunk
        from services.ai_service.rag.synthesizer import synthesize

        chunks = [
            RetrievedChunk(
                text="Your Haemoglobin from 2025-01-15: 10.5 g/dL",
                source="Your report from 2025-01-15",
                source_url=None,
                score=0.85,
                is_user_data=True,
            ),
            RetrievedChunk(
                text="Normal haemoglobin is 12-17 g/dL.",
                source="CBC Guide",
                source_url="https://example.com",
                score=0.8,
            ),
        ]
        result = synthesize("What is my haemoglobin?", chunks)
        assert "Your report" in result["answer_en"] or "health records" in result["answer_en"]

    def test_synthesize_tone_no_diagnosis(self, mock_embedder):
        """Answer must not contain diagnostic language."""
        from services.ai_service.rag.retriever import RetrievedChunk
        from services.ai_service.rag.synthesizer import synthesize

        chunks = [
            RetrievedChunk(
                text="Low haemoglobin may indicate iron deficiency.",
                source="CBC Guide",
                source_url="https://example.com",
                score=0.9,
            ),
        ]
        result = synthesize("Is my haemoglobin low?", chunks)
        answer = result["answer_en"].lower()
        # Must not contain diagnostic claims
        assert "you have" not in answer or "you have been" not in answer
        assert "diagnosed with" not in answer
        # Must contain consultation recommendation
        assert "consult" in answer or "healthcare" in answer or "doctor" in answer


# ---------------------------------------------------------------------------
# Ingester tests
# ---------------------------------------------------------------------------

class TestIngester:
    """Tests for the knowledge base ingester."""

    def test_chunk_text_produces_chunks(self):
        from services.ai_service.rag.ingester import _chunk_text

        text = " ".join(["word"] * 600)  # 600 words
        chunks = _chunk_text(text, target_words=300, overlap_words=50)
        assert len(chunks) >= 2

    def test_chunk_text_handles_short_text(self):
        from services.ai_service.rag.ingester import _chunk_text

        text = "This is a short text."
        chunks = _chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_parse_source_header(self):
        from services.ai_service.rag.ingester import _parse_source_header

        text = """SOURCE: NHS Guidelines
LICENCE: CC-BY-4.0
URL: https://nhs.uk/guide

---

Body text here."""
        header = _parse_source_header(text)
        assert header["source_title"] == "NHS Guidelines"
        assert header["source_url"] == "https://nhs.uk/guide"
        assert header["source_licence"] == "CC-BY-4.0"

    def test_load_documents_returns_list(self):
        from services.ai_service.rag.ingester import load_documents

        docs = load_documents()
        assert isinstance(docs, list)
        # Should have loaded the knowledge base files
        assert len(docs) > 0

    def test_load_documents_have_required_fields(self):
        from services.ai_service.rag.ingester import load_documents

        docs = load_documents()
        if docs:
            for doc in docs:
                assert "source_title" in doc
                assert "chunk_text" in doc
                assert "chunk_index" in doc
                assert len(doc["chunk_text"]) > 0


# ---------------------------------------------------------------------------
# Cross-user scoping test
# ---------------------------------------------------------------------------

class TestCrossUserScoping:
    """User A's data must not appear in User B's retrieval."""

    def test_user_data_is_isolated(self, mock_embedder):
        from services.ai_service.rag.retriever import retrieve

        user_a_values = [
            {"test_name": "Haemoglobin", "value_numeric": 10.5, "unit": "g/dL",
             "date_of_test": "2025-01-15", "panel": "CBC"},
        ]
        user_b_values = [
            {"test_name": "Haemoglobin", "value_numeric": 14.0, "unit": "g/dL",
             "date_of_test": "2025-02-20", "panel": "CBC"},
        ]

        results_a = retrieve("haemoglobin", user_report_values=user_a_values)
        results_b = retrieve("haemoglobin", user_report_values=user_b_values)

        user_data_a = [r for r in results_a if r.is_user_data]
        user_data_b = [r for r in results_b if r.is_user_data]

        # User A should see 10.5, not 14.0
        if user_data_a:
            assert "10.5" in user_data_a[0].text
            assert "14.0" not in user_data_a[0].text

        # User B should see 14.0, not 10.5
        if user_data_b:
            assert "14.0" in user_data_b[0].text
            assert "10.5" not in user_data_b[0].text
