"""
packages/research-data/retrieval/dense.py

Local Dense Semantic Evidence Retrieval Baseline (CP-06).
Uses local SentenceTransformer ('sentence-transformers/all-MiniLM-L6-v2') without network calls.
Includes a deterministic TF-IDF + SVD fallback if torch/transformers cannot be loaded.
Caches precomputed embeddings to disk for instant, reproducible benchmark runs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from packages.ml_interfaces.query import ClinicalQuery
from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.retrieval.contract import (
    EvidenceRetriever,
    RetrievalResult,
    filter_patient_evidence,
    sort_and_rank_results,
)

logger = logging.getLogger(__name__)

CACHE_DIR = Path("validation/retrieval/embeddings")
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
REPRESENTATION_VERSION = "v1.0"


def format_evidence_dense_doc(record: ResearchEvidenceRecord) -> str:
    """
    Constructs a clinically grounded textual description of an Evidence Observation
    for dense semantic embedding.
    """
    analyte = record.analyte_canonical or record.analyte_raw
    val_str = str(record.value_numeric) if record.value_numeric is not None else (record.value_text or "not recorded")
    unit_str = record.unit or ""
    flag_str = f"Flag: {record.flag}." if record.flag else "Flag: normal."
    loinc_str = f"LOINC: {record.loinc_code}." if record.loinc_code else ""
    concept_str = f"Concept: {record.concept_id}." if record.concept_id else ""
    date_str = f"Date: {record.observation_date[:10]}." if record.observation_date else ""

    parts = [
        f"Patient observation: {analyte}.",
        f"Original test name: {record.analyte_raw}.",
        f"Measurement value: {val_str} {unit_str}.",
        date_str,
        flag_str,
        concept_str,
        loinc_str,
    ]
    return " ".join(p for p in parts if p)


def format_query_dense_text(query: ClinicalQuery) -> str:
    """Formats clinical query for semantic embedding."""
    parts = [query.raw_query]
    if query.analyte_canonical:
        parts.append(f"Analyte: {query.analyte_canonical}.")
    if query.loinc_code:
        parts.append(f"LOINC: {query.loinc_code}.")
    return " ".join(parts)


class DenseEmbeddingBackend:
    """
    Manages embedding generation with fallback capability.
    Prefers local cached SentenceTransformer; falls back to deterministic TF-IDF+SVD.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name
        self._st_model = None
        self._fallback_vectorizer = None
        self._fallback_svd = None
        self._backend_type = "sentence_transformer"

        try:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer(self.model_name, local_files_only=True)
            self._dimension = (
                self._st_model.get_embedding_dimension()
                if hasattr(self._st_model, "get_embedding_dimension")
                else self._st_model.get_sentence_embedding_dimension()
            )
            logger.info("Loaded local SentenceTransformer model: %s (dim=%d)", model_name, self._dimension)
        except Exception as exc:
            logger.warning("Could not load SentenceTransformer (%s). Initializing TF-IDF+SVD fallback: %s", model_name, exc)
            self._init_fallback()

    def _init_fallback(self) -> None:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._backend_type = "tfidf_svd_fallback"
        self._dimension = 128
        self._fallback_vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        self._fallback_svd = TruncatedSVD(n_components=128, random_state=42)

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def backend_type(self) -> str:
        return self._backend_type

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._st_model is not None:
            embeddings = self._st_model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return embeddings.astype(np.float32)

        # Fallback
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)
        tfidf = self._fallback_vectorizer.fit_transform(texts)
        n_comps = min(self._dimension, tfidf.shape[1] - 1, len(texts) - 1)
        if n_comps >= 2:
            svd = TruncatedSVD(n_components=n_comps, random_state=42)
            dense = svd.fit_transform(tfidf)
            # Pad to self._dimension if needed
            if dense.shape[1] < self._dimension:
                dense = np.pad(dense, ((0, 0), (0, self._dimension - dense.shape[1])))
        else:
            dense = tfidf.toarray()
            if dense.shape[1] < self._dimension:
                dense = np.pad(dense, ((0, 0), (0, self._dimension - dense.shape[1])))
            else:
                dense = dense[:, :self._dimension]

        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (dense / norms).astype(np.float32)


class EvidenceDenseRetriever(EvidenceRetriever):
    """
    Dense Semantic Evidence Retriever.
    Provides embedding cache management and patient-scoped vector similarity ranking.
    """

    def __init__(
        self,
        backend: DenseEmbeddingBackend | None = None,
        cache_dir: Path = CACHE_DIR,
    ) -> None:
        self.backend = backend or DenseEmbeddingBackend()
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory document embedding index: evidence_id -> (record, embedding_vector)
        self._doc_embeddings: dict[str, np.ndarray] = {}
        self._records_by_id: dict[str, ResearchEvidenceRecord] = {}

    def index_evidence(
        self,
        evidence: Sequence[ResearchEvidenceRecord],
        cache_name: str = "synthea_sample_embeddings_v1.npz",
    ) -> None:
        """
        Indexes and embeds all evidence records, loading from cache if valid.
        """
        self._records_by_id = {r.id: r for r in evidence}
        evidence_ids = [r.id for r in evidence]
        cache_path = self.cache_dir / cache_name

        if cache_path.exists():
            try:
                data = np.load(cache_path, allow_pickle=True)
                cached_ids = list(data["evidence_ids"])
                meta = json.loads(str(data["metadata"]))

                if (
                    cached_ids == evidence_ids
                    and meta.get("model_name") == self.backend.model_name
                    and meta.get("representation_version") == REPRESENTATION_VERSION
                ):
                    cached_embs = data["embeddings"]
                    for eid, emb in zip(cached_ids, cached_embs):
                        self._doc_embeddings[eid] = emb
                    logger.info("Loaded %d dense embeddings from cache: %s", len(cached_ids), cache_path)
                    return
            except Exception as exc:
                logger.warning("Cache invalidation or load failure (%s): %s. Recomputing...", cache_path, exc)

        # Compute embeddings
        logger.info("Computing dense embeddings for %d evidence records...", len(evidence))
        texts = [format_evidence_dense_doc(r) for r in evidence]
        embs = self.backend.encode(texts)

        for eid, emb in zip(evidence_ids, embs):
            self._doc_embeddings[eid] = emb

        # Save cache
        try:
            meta = {
                "model_name": self.backend.model_name,
                "dimension": int(self.backend.dimension),
                "representation_version": REPRESENTATION_VERSION,
                "evidence_count": len(evidence),
                "backend_type": self.backend.backend_type,
            }
            np.savez_compressed(
                cache_path,
                embeddings=embs,
                evidence_ids=np.array(evidence_ids),
                metadata=np.array(json.dumps(meta)),
            )
            logger.info("Saved %d dense embeddings to cache: %s", len(evidence), cache_path)
        except Exception as exc:
            logger.warning("Failed to save dense embeddings cache: %s", exc)

    def retrieve(
        self,
        query: ClinicalQuery,
        evidence: Sequence[ResearchEvidenceRecord],
        top_k: int = 10,
        patient_id: str | None = None,
    ) -> list[RetrievalResult]:
        target_pid = patient_id or getattr(query, "patient_id", None)
        if not target_pid:
            return []

        patient_records = filter_patient_evidence(evidence, target_pid)
        if not patient_records:
            return []

        # Ensure index has the patient's records
        missing_records = [r for r in patient_records if r.id not in self._doc_embeddings]
        if missing_records:
            self.index_evidence(evidence)

        # Encode query
        q_text = format_query_dense_text(query)
        q_emb = self.backend.encode([q_text])[0]  # normalized vector

        # Compute cosine similarities for patient records only
        results: list[RetrievalResult] = []
        for rec in patient_records:
            doc_emb = self._doc_embeddings.get(rec.id)
            if doc_emb is None:
                sim = 0.0
            else:
                sim = float(np.dot(q_emb, doc_emb))  # dot product of L2-normalized vectors

            # Normalize similarity from [-1, 1] to [0, 1]
            norm_score = max(0.0, min(1.0, (sim + 1.0) / 2.0))

            results.append(
                RetrievalResult(
                    evidence_id=rec.id,
                    patient_id=rec.source_patient_id,
                    score=norm_score,
                    rank=0,
                    retrieval_method="dense",
                    analyte_canonical=rec.analyte_canonical,
                    concept_id=rec.concept_id,
                    loinc_code=rec.loinc_code,
                    observation_date=rec.observation_date,
                    value=rec.value_numeric if rec.value_numeric is not None else rec.value_text,
                    unit=rec.unit,
                    flag=rec.flag,
                    source_provenance=rec.source_provenance,
                    metadata={"cosine_similarity": round(sim, 6), "dense_score": round(norm_score, 6)},
                )
            )

        return sort_and_rank_results(results, top_k=top_k)
