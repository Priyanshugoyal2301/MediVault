"""
tests/unit/ai-service/test_rag.py

Tests for the RAG pipeline: BM25+intent retriever, synthesizer, and ingester.
Does NOT require sentence-transformers.
"""

from __future__ import annotations

import pytest


class TestBM25:
    def test_bm25_ranks_relevant_doc_first(self):
        from services.ai_service.rag.bm25 import BM25Index

        idx = BM25Index.build([
            "Haemoglobin carries oxygen in red blood cells.",
            "LDL cholesterol builds up in arteries.",
            "TSH is a thyroid stimulating hormone.",
        ])
        top = idx.top_k("What is haemoglobin?", k=2)
        assert top
        assert top[0][0] == 0
        assert top[0][1] > 0


class TestIntent:
    def test_detects_lipid_intent(self):
        from services.ai_service.rag.intent import detect_intents

        intents = detect_intents("Why is my LDL cholesterol high?")
        names = {i.name for i in intents}
        assert "lipid" in names


class TestRetriever:
    def test_retrieve_returns_list(self):
        from services.ai_service.rag.retriever import retrieve, load_knowledge_base

        load_knowledge_base([])
        results = retrieve("What is haemoglobin?")
        assert isinstance(results, list)

    def test_retrieve_with_empty_kb_returns_empty(self):
        from services.ai_service.rag.retriever import retrieve, load_knowledge_base

        load_knowledge_base([])
        results = retrieve("What is haemoglobin?")
        assert results == []

    def test_retrieve_with_loaded_kb_returns_results(self):
        from services.ai_service.rag.retriever import retrieve, load_knowledge_base

        test_chunks = [
            {
                "chunk_text": "Haemoglobin carries oxygen in red blood cells. Normal range is 12-17 g/dL.",
                "source_title": "CBC Guide",
                "source_url": "https://example.com/cbc",
            },
            {
                "chunk_text": "LDL cholesterol is called bad cholesterol because it builds up in arteries.",
                "source_title": "Lipid Guide",
                "source_url": "https://example.com/lipid",
            },
        ]
        load_knowledge_base(test_chunks, mode="bm25")
        results = retrieve("What is haemoglobin?")
        assert len(results) > 0
        assert "Haemoglobin" in results[0].text or "haemoglobin" in results[0].text.lower()
        assert results[0].source == "CBC Guide"

    def test_retrieve_with_user_report_values(self):
        from services.ai_service.rag.retriever import retrieve, load_knowledge_base

        load_knowledge_base([])
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

    def test_retrieve_respects_top_k(self):
        from services.ai_service.rag.retriever import retrieve, load_knowledge_base

        chunks = [
            {
                "chunk_text": f"Haemoglobin fact number {i} about blood oxygen capacity.",
                "source_title": f"Source {i}",
                "source_url": None,
            }
            for i in range(10)
        ]
        load_knowledge_base(chunks, mode="bm25")
        results = retrieve("What is haemoglobin?", top_k=2)
        assert len(results) <= 2

    def test_results_sorted_by_score_descending(self):
        from services.ai_service.rag.retriever import retrieve, load_knowledge_base

        chunks = [
            {"chunk_text": f"Test chunk {i} haemoglobin blood", "source_title": f"Source {i}",
             "source_url": None}
            for i in range(10)
        ]
        load_knowledge_base(chunks, mode="bm25")
        results = retrieve("haemoglobin blood", top_k=5)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_kb_stats_report_bm25(self):
        from services.ai_service.rag.retriever import load_knowledge_base, knowledge_base_stats

        load_knowledge_base(
            [{"chunk_text": "hello haemoglobin", "source_title": "t", "source_url": None}],
            mode="bm25",
        )
        stats = knowledge_base_stats()
        assert stats["kb_ready"] is True
        assert stats["kb_retriever"] == "bm25"


class TestSynthesizer:
    def test_synthesize_returns_bilingual(self):
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

    def test_synthesize_includes_citations(self):
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
        assert "[1]" in result["answer_en"]

    def test_synthesize_empty_chunks_returns_insufficient(self):
        from services.ai_service.rag.synthesizer import synthesize

        result = synthesize("Random question", [])
        assert "don't have enough information" in result["answer_en"].lower() or \
               "enough information" in result["answer_en"].lower()

    def test_synthesize_includes_user_data_section(self):
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

    def test_synthesize_tone_no_diagnosis(self):
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
        assert "diagnosed with" not in answer
        assert "consult" in answer or "healthcare" in answer or "doctor" in answer


class TestIngester:
    def test_chunk_text_produces_chunks(self):
        from services.ai_service.rag.ingester import _chunk_text

        text = " ".join(["word"] * 600)
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


class TestCrossUserScoping:
    def test_user_data_is_isolated(self):
        from services.ai_service.rag.retriever import retrieve, load_knowledge_base

        load_knowledge_base([])
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

        if user_data_a:
            assert "10.5" in user_data_a[0].text
            assert "14.0" not in user_data_a[0].text
        if user_data_b:
            assert "14.0" in user_data_b[0].text
            assert "10.5" not in user_data_b[0].text
