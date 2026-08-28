"""
Vector store abstraction.

Default: FAISS (IndexFlatIP) when `faiss` is installed.
Always available: NumPy cosine / inner-product brute force.

Future adapters (stubs for interface stability): Qdrant, Chroma, Milvus —
not required at runtime; create_store falls back to FAISS/NumPy.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence

import numpy as np


class VectorStore(ABC):
    """Backend-agnostic vector index."""

    name: str = "base"

    @abstractmethod
    def build(self, vectors: np.ndarray, ids: Sequence[str]) -> None:
        ...

    @abstractmethod
    def search(
        self, query_vectors: np.ndarray, top_k: int = 5
    ) -> list[list[tuple[str, float]]]:
        """For each query, return list of (id, score) highest first."""

    @abstractmethod
    def save(self, directory: Path) -> None:
        ...

    @classmethod
    @abstractmethod
    def load(cls, directory: Path) -> "VectorStore":
        ...

    @property
    @abstractmethod
    def size(self) -> int:
        ...


class NumpyVectorStore(VectorStore):
    """In-memory L2-normalized inner product search (FAISS IndexFlatIP equivalent)."""

    name = "numpy"

    def __init__(self) -> None:
        self._matrix: np.ndarray | None = None
        self._ids: list[str] = []

    def build(self, vectors: np.ndarray, ids: Sequence[str]) -> None:
        mat = np.asarray(vectors, dtype=np.float32)
        if mat.ndim != 2:
            raise ValueError("vectors must be 2-D")
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
        self._matrix = mat / norms
        self._ids = list(ids)

    def search(
        self, query_vectors: np.ndarray, top_k: int = 5
    ) -> list[list[tuple[str, float]]]:
        assert self._matrix is not None
        q = np.asarray(query_vectors, dtype=np.float32)
        norms = np.linalg.norm(q, axis=1, keepdims=True) + 1e-12
        q = q / norms
        sims = q @ self._matrix.T  # (nq, n)
        out: list[list[tuple[str, float]]] = []
        k = min(top_k, len(self._ids))
        for row in sims:
            idx = np.argsort(-row)[:k]
            out.append([(self._ids[int(i)], float(row[int(i)])) for i in idx])
        return out

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        assert self._matrix is not None
        np.save(directory / "vectors.npy", self._matrix)
        (directory / "ids.json").write_text(
            json.dumps(self._ids), encoding="utf-8"
        )
        (directory / "store_meta.json").write_text(
            json.dumps({"name": self.name, "dim": int(self._matrix.shape[1])}),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: Path) -> "NumpyVectorStore":
        obj = cls()
        obj._matrix = np.load(directory / "vectors.npy")
        obj._ids = json.loads((directory / "ids.json").read_text(encoding="utf-8"))
        return obj

    @property
    def size(self) -> int:
        return len(self._ids)


class FaissVectorStore(VectorStore):
    """FAISS IndexFlatIP over L2-normalized vectors."""

    name = "faiss"

    def __init__(self) -> None:
        self._index = None
        self._ids: list[str] = []
        self._dim = 0

    def build(self, vectors: np.ndarray, ids: Sequence[str]) -> None:
        import faiss  # type: ignore

        mat = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
        mat = mat / norms
        self._dim = int(mat.shape[1])
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(mat)
        self._ids = list(ids)

    def search(
        self, query_vectors: np.ndarray, top_k: int = 5
    ) -> list[list[tuple[str, float]]]:
        assert self._index is not None
        q = np.asarray(query_vectors, dtype=np.float32)
        norms = np.linalg.norm(q, axis=1, keepdims=True) + 1e-12
        q = q / norms
        k = min(top_k, len(self._ids))
        scores, idxs = self._index.search(q, k)
        out: list[list[tuple[str, float]]] = []
        for row_s, row_i in zip(scores, idxs):
            hits: list[tuple[str, float]] = []
            for s, i in zip(row_s, row_i):
                if int(i) < 0:
                    continue
                hits.append((self._ids[int(i)], float(s)))
            out.append(hits)
        return out

    def save(self, directory: Path) -> None:
        import faiss  # type: ignore

        directory.mkdir(parents=True, exist_ok=True)
        assert self._index is not None
        faiss.write_index(self._index, str(directory / "index.faiss"))
        (directory / "ids.json").write_text(
            json.dumps(self._ids), encoding="utf-8"
        )
        (directory / "store_meta.json").write_text(
            json.dumps({"name": self.name, "dim": self._dim}), encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: Path) -> "FaissVectorStore":
        import faiss  # type: ignore

        obj = cls()
        obj._index = faiss.read_index(str(directory / "index.faiss"))
        obj._ids = json.loads((directory / "ids.json").read_text(encoding="utf-8"))
        obj._dim = obj._index.d
        return obj

    @property
    def size(self) -> int:
        return len(self._ids)


def create_store(kind: str) -> VectorStore:
    kind = (kind or "faiss").lower()
    if kind in ("qdrant", "chroma", "milvus"):
        # Placeholders — not implemented; fall back safely
        kind = "faiss"
    if kind == "faiss":
        try:
            import faiss  # noqa: F401

            return FaissVectorStore()
        except Exception:
            return NumpyVectorStore()
    if kind in ("numpy", "memory"):
        return NumpyVectorStore()
    return NumpyVectorStore()


def load_store(directory: Path) -> VectorStore:
    meta = json.loads((directory / "store_meta.json").read_text(encoding="utf-8"))
    name = meta.get("name", "numpy")
    if name == "faiss" and (directory / "index.faiss").exists():
        try:
            return FaissVectorStore.load(directory)
        except Exception:
            pass
    return NumpyVectorStore.load(directory)
