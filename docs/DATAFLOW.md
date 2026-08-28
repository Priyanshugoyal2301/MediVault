# Dataflow — Parse, normalize, Q&A retrieval

```
file bytes → document parser → normalizer → ParsedValueOut → DB

question → safety
        → get_retriever()
             flag 0: BM25+intent
             flag 1: SemanticRetriever (embed → FAISS/NumPy) → BM25 fallback
        → template synthesizer → QAResponse (schema unchanged)
```
