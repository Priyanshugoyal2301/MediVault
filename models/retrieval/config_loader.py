"""Configuration for models/retrieval."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent


class RetrievalConfigError(ValueError):
    pass


def load_config(path: Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    cfg_path = path or (_ROOT / "config.yaml")
    data: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    if os.getenv("RETRIEVAL_EMBEDDING_BACKEND"):
        data["embedding_backend"] = os.getenv("RETRIEVAL_EMBEDDING_BACKEND")
    if os.getenv("RETRIEVAL_VECTOR_STORE"):
        data["vector_store"] = os.getenv("RETRIEVAL_VECTOR_STORE")
    if os.getenv("RETRIEVAL_TOP_K"):
        data["default_top_k"] = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    if os.getenv("RETRIEVAL_CHUNK_WORDS"):
        data.setdefault("chunking", {})["target_words"] = int(
            os.getenv("RETRIEVAL_CHUNK_WORDS", "300")
        )
    if os.getenv("RETRIEVAL_ALLOW_HF"):
        data["allow_hf_download"] = os.getenv("RETRIEVAL_ALLOW_HF", "0") in (
            "1",
            "true",
            "yes",
            "True",
        )
    if os.getenv("BGE_MODEL_ID"):
        data["primary_model_id"] = os.getenv("BGE_MODEL_ID")
    if os.getenv("MINILM_MODEL_ID"):
        data["fallback_model_id"] = os.getenv("MINILM_MODEL_ID")
    if os.getenv("RETRIEVAL_ARTIFACTS_DIR"):
        data.setdefault("paths", {})["artifacts"] = os.getenv("RETRIEVAL_ARTIFACTS_DIR")
    if os.getenv("RETRIEVAL_KB_DIR"):
        data.setdefault("paths", {})["knowledge_base"] = os.getenv("RETRIEVAL_KB_DIR")

    data.setdefault("model_name", "semantic_medical_retriever")
    data.setdefault("version", "3.0.0")
    data.setdefault("primary_architecture", "BAAI/bge-small-en-v1.5")
    data.setdefault("fallback_architecture", "sentence-transformers/all-MiniLM-L6-v2")
    data.setdefault("offline_architecture", "char_tfidf")
    data.setdefault("embedding_backend", "auto")  # auto|bge|minilm|char_tfidf
    data.setdefault("vector_store", "faiss")  # faiss|numpy|memory
    data.setdefault("allow_hf_download", False)
    data.setdefault("default_top_k", 5)
    data.setdefault("primary_model_id", "BAAI/bge-small-en-v1.5")
    data.setdefault("fallback_model_id", "sentence-transformers/all-MiniLM-L6-v2")
    data.setdefault(
        "chunking",
        {"target_words": 300, "overlap_words": 50},
    )
    data.setdefault(
        "paths",
        {
            "knowledge_base": str(
                (_ROOT.parents[2] / "data" / "knowledge-base").as_posix()
            ),
            "train_data": str((_ROOT.parents[2] / "datasets" / "retrieval").as_posix()),
            "artifacts": str((_ROOT / "artifacts").as_posix()),
            "evaluation_out": str(
                (
                    _ROOT.parents[2]
                    / "datasets"
                    / "evaluation"
                    / "retrieval_phase3_latest.json"
                ).as_posix()
            ),
        },
    )

    if validate:
        validate_config(data)
    return data


def validate_config(cfg: dict[str, Any]) -> None:
    emb = (cfg.get("embedding_backend") or "auto").lower()
    if emb not in {"auto", "bge", "minilm", "char_tfidf", "offline", "tfidf"}:
        raise RetrievalConfigError(f"Invalid embedding_backend: {emb}")
    store = (cfg.get("vector_store") or "faiss").lower()
    if store not in {"faiss", "numpy", "memory", "qdrant", "chroma", "milvus"}:
        raise RetrievalConfigError(f"Invalid vector_store: {store}")
    if store in {"qdrant", "chroma", "milvus"}:
        # Future adapters only — not fail at config if selected for docs;
        # runtime create_store will fall back to faiss/numpy.
        pass


def artifacts_dir(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config(validate=False)
    p = Path(cfg["paths"]["artifacts"])
    if not p.is_absolute():
        p = (_ROOT / p).resolve()
    return p
