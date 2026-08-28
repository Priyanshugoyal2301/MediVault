"""
Encoder backends for nearest-neighbor lab name normalization.

Primary (config): ModernBERT — optional transformers
Fallback (config): ClinicalBERT — optional transformers
Deployable default offline: char n-gram TF-IDF (sklearn) — always available

Business logic never imports a specific HF model id directly; load via
EncoderBackend protocol selected by config.
"""

from __future__ import annotations

import json
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence

import numpy as np


class EncoderBackend(ABC):
    name: str = "base"

    @abstractmethod
    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> None:
        ...

    @abstractmethod
    def encode(self, texts: Sequence[str]) -> np.ndarray:
        ...

    @abstractmethod
    def save(self, directory: Path) -> None:
        ...

    @classmethod
    @abstractmethod
    def load(cls, directory: Path) -> "EncoderBackend":
        ...


def _cosine_topk(
    query_vec: np.ndarray,
    matrix: np.ndarray,
    labels: list[str],
    k: int = 5,
) -> list[tuple[str, float]]:
    """Return unique labels by max similarity."""
    q = query_vec.reshape(1, -1)
    denom = (np.linalg.norm(matrix, axis=1) * (np.linalg.norm(q) + 1e-12) + 1e-12)
    sims = (matrix @ q.ravel()) / denom
    order = np.argsort(-sims)
    seen: set[str] = set()
    out: list[tuple[str, float]] = []
    for i in order:
        lab = labels[int(i)]
        if lab in seen:
            continue
        seen.add(lab)
        score = float(sims[int(i)])
        conf = min(1.0, max(0.0, score if score >= 0 else (score + 1.0) / 2.0))
        out.append((lab, conf))
        if len(out) >= k:
            break
    return out


class CharTfidfBackend(EncoderBackend):
    """Always-on ML backend: character n-gram TF-IDF + cosine NN."""

    name = "char_tfidf"

    def __init__(self) -> None:
        self._vectorizer = None
        self._matrix: np.ndarray | None = None
        self._labels: list[str] = []

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
            sublinear_tf=True,
        )
        X = self._vectorizer.fit_transform(list(texts))
        self._matrix = X.astype(np.float64).toarray()
        norms = np.linalg.norm(self._matrix, axis=1, keepdims=True) + 1e-12
        self._matrix = self._matrix / norms
        self._labels = list(labels)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        assert self._vectorizer is not None
        X = self._vectorizer.transform(list(texts)).astype(np.float64).toarray()
        norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
        return X / norms

    def rank(self, text: str, k: int = 5) -> list[tuple[str, float]]:
        assert self._matrix is not None
        q = self.encode([text])[0]
        return _cosine_topk(q, self._matrix, self._labels, k=k)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "tfidf_vectorizer.pkl").open("wb") as fh:
            pickle.dump(self._vectorizer, fh)
        np.save(directory / "matrix.npy", self._matrix)
        (directory / "labels.json").write_text(
            json.dumps(self._labels, ensure_ascii=False), encoding="utf-8"
        )
        (directory / "backend.json").write_text(
            json.dumps({"name": self.name}), encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: Path) -> "CharTfidfBackend":
        obj = cls()
        with (directory / "tfidf_vectorizer.pkl").open("rb") as fh:
            obj._vectorizer = pickle.load(fh)
        obj._matrix = np.load(directory / "matrix.npy")
        obj._labels = json.loads((directory / "labels.json").read_text(encoding="utf-8"))
        return obj


class TransformersEmbeddingBackend(EncoderBackend):
    """
    Optional HF encoder (ModernBERT / ClinicalBERT family).
    """

    name = "transformers"

    def __init__(self, model_id: str, device: str = "cpu") -> None:
        self.model_id = model_id
        self.device = device
        self._tokenizer = None
        self._model = None
        self._matrix: np.ndarray | None = None
        self._labels: list[str] = []
        self._torch = None

    def _lazy_load_model(self) -> None:
        if self._model is not None:
            return
        try:
            from transformers import AutoModel, AutoTokenizer
            import torch
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "transformers/torch required for ModernBERT/ClinicalBERT backends"
            ) from exc
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModel.from_pretrained(self.model_id)
        self._model.to(self.device)
        self._model.eval()

    def _embed_batch(self, texts: Sequence[str]) -> np.ndarray:
        self._lazy_load_model()
        torch = self._torch
        assert self._tokenizer is not None and self._model is not None
        enc = self._tokenizer(
            list(texts),
            padding=True,
            truncation=True,
            max_length=64,
            return_tensors="pt",
        )
        enc = {k: v.to(self.device) for k, v in enc.items()}
        with torch.no_grad():
            out = self._model(**enc)
            mask = enc["attention_mask"].unsqueeze(-1)
            summed = (out.last_hidden_state * mask).sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1)
            emb = summed / counts
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
        return emb.cpu().numpy().astype(np.float64)

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> None:
        embs = self._embed_batch(texts)
        buckets: dict[str, list[np.ndarray]] = {}
        for e, lab in zip(embs, labels):
            buckets.setdefault(lab, []).append(e)
        self._labels = []
        mats = []
        for lab, vecs in buckets.items():
            proto = np.mean(np.stack(vecs, axis=0), axis=0)
            proto = proto / (np.linalg.norm(proto) + 1e-12)
            self._labels.append(lab)
            mats.append(proto)
        self._matrix = np.stack(mats, axis=0)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed_batch(texts)

    def rank(self, text: str, k: int = 5) -> list[tuple[str, float]]:
        assert self._matrix is not None
        q = self.encode([text])[0]
        return _cosine_topk(q, self._matrix, self._labels, k=k)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "matrix.npy", self._matrix)
        (directory / "labels.json").write_text(
            json.dumps(self._labels, ensure_ascii=False), encoding="utf-8"
        )
        (directory / "backend.json").write_text(
            json.dumps(
                {"name": self.name, "model_id": self.model_id, "device": self.device}
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: Path) -> "TransformersEmbeddingBackend":
        meta = json.loads((directory / "backend.json").read_text(encoding="utf-8"))
        obj = cls(model_id=meta["model_id"], device=meta.get("device", "cpu"))
        obj._matrix = np.load(directory / "matrix.npy")
        obj._labels = json.loads((directory / "labels.json").read_text(encoding="utf-8"))
        return obj


def create_backend(kind: str, config: dict[str, Any]) -> EncoderBackend:
    kind = (kind or "char_tfidf").lower()
    if kind in ("char_tfidf", "tfidf", "sklearn", "offline"):
        return CharTfidfBackend()
    if kind in ("modernbert", "primary"):
        mid = config.get("modernbert_model_id") or "answerdotai/ModernBERT-base"
        return TransformersEmbeddingBackend(mid, device=config.get("device", "cpu"))
    if kind in ("clinicalbert", "fallback_hf"):
        mid = config.get("clinicalbert_model_id") or "emilyalsentzer/Bio_ClinicalBERT"
        return TransformersEmbeddingBackend(mid, device=config.get("device", "cpu"))
    raise ValueError(f"Unknown normalizer backend: {kind}")


def load_backend(directory: Path) -> EncoderBackend:
    meta_path = directory / "backend.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No normalizer backend at {directory}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    name = meta.get("name", "char_tfidf")
    if name == CharTfidfBackend.name:
        return CharTfidfBackend.load(directory)
    if name == TransformersEmbeddingBackend.name:
        return TransformersEmbeddingBackend.load(directory)
    raise ValueError(f"Cannot load backend type {name}")
