# models/retrieval — Semantic Medical Retrieval (Phase 3)

## Status

| Flag | Path |
|------|------|
| `USE_EMBEDDING_SEARCH=0` (default) | BM25 + intent (legacy, never removed) |
| `USE_EMBEDDING_SEARCH=1` | SemanticRetriever (BGE / MiniLM / offline TF-IDF) + BM25 fallback |

## Architecture

| Role | Implementation |
|------|----------------|
| Primary embedder | `BAAI/bge-small-en-v1.5` |
| Fallback embedder | `all-MiniLM-L6-v2` |
| Offline default | char n-gram TF-IDF → dense SVD |
| Vector DB default | FAISS IndexFlatIP (NumPy IP if faiss missing) |
| Future stores | Qdrant / Chroma / Milvus interface reserved |

Business logic uses `EmbeddingBackend` + `VectorStore` protocols — swap without changing `/qa`.

## Pipeline

```
KB docs → chunk → embed → vector index
Query → embed → top-k similarity → RetrievedDocument for synthesizer
```

## Commands

```bash
python models/retrieval/train.py
python models/retrieval/evaluate.py
```

## Env

| Variable | Default | Meaning |
|----------|---------|---------|
| `USE_EMBEDDING_SEARCH` | `0` | Registry switch |
| `RETRIEVAL_EMBEDDING_BACKEND` | `auto` | auto\|bge\|minilm\|char_tfidf |
| `RETRIEVAL_VECTOR_STORE` | `faiss` | faiss\|numpy |
| `RETRIEVAL_ALLOW_HF` | `0` | Permit HF weight load |
| `RETRIEVAL_CHUNK_WORDS` | `300` | Chunk size |
