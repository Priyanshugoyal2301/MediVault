"""
Embedding backends — business logic never imports a concrete model id path.

Primary: BGE-small-en-v1.5
Fallback: all-MiniLM-L6-v2
Offline deploy: char n-gram TF-IDF projections
"""

from __future__ import annotations

import hashlib
import json
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence

import numpy as np


class EmbeddingBackend(ABC):
    name: str = "base"
    dim: int = 0

    @abstractmethod
    def fit(self, texts: Sequence[str]) -> None:
        """Optional fit step (TF-IDF); no-op for frozen transformers."""

    @abstractmethod
    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Return (n, d) float32 L2-normalized matrix."""

    @abstractmethod
    def save(self, directory: Path) -> None:
        ...

    @classmethod
    @abstractmethod
    def load(cls, directory: Path) -> "EmbeddingBackend":
        ...


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
    return (x / norms).astype(np.float32)


class CharTfidfEmbedding(EmbeddingBackend):
    """Always-on offline embedding for index + query."""

    name = "char_tfidf"

    def __init__(self, dim_hint: int = 512) -> None:
        self.dim = dim_hint
        self._vectorizer = None

    def fit(self, texts: Sequence[str]) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD

        self._vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1,
            sublinear_tf=True,
            max_features=4096,
        )
        X = self._vectorizer.fit_transform(list(texts))
        n_comp = min(self.dim, max(2, X.shape[0] - 1), X.shape[1] - 1)
        if n_comp < 2:
            n_comp = 2
        self._svd = TruncatedSVD(n_components=n_comp, random_state=42)
        self._svd.fit(X)
        self.dim = int(n_comp)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        assert self._vectorizer is not None
        X = self._vectorizer.transform(list(texts))
        emb = self._svd.transform(X)
        return _l2_normalize(emb.astype(np.float64))

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "embedder.pkl").open("wb") as fh:
            pickle.dump(
                {"vectorizer": self._vectorizer, "svd": self._svd, "dim": self.dim},
                fh,
            )
        (directory / "embedder_meta.json").write_text(
            json.dumps({"name": self.name, "dim": self.dim}), encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: Path) -> "CharTfidfEmbedding":
        obj = cls()
        with (directory / "embedder.pkl").open("rb") as fh:
            blob = pickle.load(fh)
        obj._vectorizer = blob["vectorizer"]
        obj._svd = blob["svd"]
        obj.dim = int(blob["dim"])
        return obj


class SentenceTransformerEmbedding(EmbeddingBackend):
    """BGE / MiniLM via sentence-transformers (optional heavy path)."""

    name = "sentence_transformers"

    def __init__(self, model_id: str, device: str = "cpu") -> None:
        self.model_id = model_id
        self.device = device
        self._model = None
        self.dim = 384

    def _lazy(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_id, device=self.device)
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def fit(self, texts: Sequence[str]) -> None:
        self._lazy()

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        self._lazy()
        assert self._model is not None
        emb = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(emb, dtype=np.float32)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "embedder_meta.json").write_text(
            json.dumps(
                {
                    "name": self.name,
                    "model_id": self.model_id,
                    "device": self.device,
                    "dim": self.dim,
                }
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: Path) -> "SentenceTransformerEmbedding":
        meta = json.loads(
            (directory / "embedder_meta.json").read_text(encoding="utf-8")
        )
        obj = cls(model_id=meta["model_id"], device=meta.get("device", "cpu"))
        obj.dim = int(meta.get("dim") or 384)
        return obj


class HashEmbedding(EmbeddingBackend):
    """Deterministic bag-of-features for unit tests when sklearn path broken."""

    name = "hash"

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def fit(self, texts: Sequence[str]) -> None:
        return

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        mats = []
        for t in texts:
            v = np.zeros(self.dim, dtype=np.float64)
            for tok in (t or "").lower().split():
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                v[h % self.dim] += 1.0
            mats.append(v)
        return _l2_normalize(np.stack(mats, axis=0))

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "embedder_meta.json").write_text(
            json.dumps({"name": self.name, "dim": self.dim}), encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: Path) -> "HashEmbedding":
        meta = json.loads(
            (directory / "embedder_meta.json").read_text(encoding="utf-8")
        )
        return cls(dim=int(meta.get("dim") or 256))


def create_embedding_backend(kind: str, config: dict[str, Any]) -> EmbeddingBackend:
    kind = (kind or "auto").lower()
    allow = bool(config.get("allow_hf_download"))

    def try_st(model_id: str, label: str) -> EmbeddingBackend | None:
        if not allow:
            return None
        try:
            emb = SentenceTransformerEmbedding(
                model_id, device=config.get("device", "cpu")
            )
            emb.fit(["warmup"])
            emb.name = label  # type: ignore[misc]
            return emb
        except Exception:
            return None

    if kind in ("char_tfidf", "offline", "tfidf"):
        return CharTfidfEmbedding(dim_hint=int(config.get("tfidf_dim") or 256))
    if kind == "hash":
        return HashEmbedding(dim=int(config.get("hash_dim") or 256))
    if kind == "bge":
        mid = config.get("primary_model_id") or "BAAI/bge-small-en-v1.5"
        got = try_st(mid, "bge")
        if got:
            return got
        return CharTfidfEmbedding()
    if kind == "minilm":
        mid = config.get("fallback_model_id") or "sentence-transformers/all-MiniLM-L6-v2"
        got = try_st(mid, "minilm")
        if got:
            return got
        return CharTfidfEmbedding()
    # auto
    if allow:
        bge = try_st(
            config.get("primary_model_id") or "BAAI/bge-small-en-v1.5", "bge"
        )
        if bge:
            return bge
        mini = try_st(
            config.get("fallback_model_id")
            or "sentence-transformers/all-MiniLM-L6-v2",
            "minilm",
        )
        if mini:
            return mini
    return CharTfidfEmbedding()


def load_embedding_backend(directory: Path) -> EmbeddingBackend:
    meta_path = directory / "embedder_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(meta_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    name = meta.get("name", "char_tfidf")
    if name == "char_tfidf":
        return CharTfidfEmbedding.load(directory)
    if name in ("sentence_transformers", "bge", "minilm"):
        return SentenceTransformerEmbedding.load(directory)
    if name == "hash":
        return HashEmbedding.load(directory)
    # pkl path for char
    if (directory / "embedder.pkl").exists():
        return CharTfidfEmbedding.load(directory)
    raise ValueError(f"Unknown embedder {name}")
