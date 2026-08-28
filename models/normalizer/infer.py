"""
MedicalTestNormalizer — ML + alias cascade for lab name canonicalization.

Does NOT diagnose or predict risk. Output = name / LOINC / confidence only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_loader import artifacts_dir, load_config
from .encoder_backends import create_backend, load_backend
from .postprocess import build_result
from .preprocess import preprocess_for_exact, preprocess_test_name
from .schema import NormalizationResult, NormalizationStatus
from .vocabulary import alias_lookup_table, loinc_for, unit_for


class MedicalTestNormalizer:
    """
    Production inference object.

    Pipeline:
      1. preprocess
      2. exact alias table (high confidence)
      3. ML nearest-neighbor (char_tfidf / ModernBERT / ClinicalBERT)
      4. unknown → pass-through surface string
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        auto_train_if_missing: bool = True,
    ) -> None:
        self.config = config or load_config(validate=True)
        self.min_confidence = float(self.config.get("min_confidence") or 0.55)
        self._alias = alias_lookup_table()
        self._backend = None
        self._backend_name = "uninitialized"
        self._load_or_fit_backend(auto_train_if_missing=auto_train_if_missing)

    def _load_or_fit_backend(self, *, auto_train_if_missing: bool) -> None:
        art = artifacts_dir(self.config)
        backend_meta = art / "backend.json"
        try:
            if backend_meta.exists():
                self._backend = load_backend(art)
                self._backend_name = getattr(self._backend, "name", "loaded")
                return
        except Exception:
            self._backend = None

        kind = (self.config.get("active_backend") or "char_tfidf").lower()
        # HF backends need allow flag; otherwise force offline ML
        if kind in ("modernbert", "clinicalbert", "primary", "fallback_hf"):
            if not self.config.get("allow_hf_download"):
                kind = "char_tfidf"

        if not auto_train_if_missing and kind != "char_tfidf":
            # still build in-memory offline model
            kind = "char_tfidf"

        backend = create_backend(kind, self.config)
        texts, labels = self._train_corpus()
        backend.fit(texts, labels)
        try:
            backend.save(art)
        except Exception:
            pass
        self._backend = backend
        self._backend_name = getattr(backend, "name", kind)

    def _train_corpus(self) -> tuple[list[str], list[str]]:
        from .dataset import load_train_pairs
        from .preprocess import preprocess_test_name as prep

        data_dir = self.config.get("paths", {}).get("train_data")
        path = Path(data_dir) if data_dir else None
        pairs = load_train_pairs(path)
        texts: list[str] = []
        labels: list[str] = []
        for p in pairs:
            if p.get("unknown"):
                continue
            raw = prep(str(p.get("raw") or ""))
            canon = str(p.get("canonical") or "")
            if not raw or not canon:
                continue
            texts.append(raw)
            labels.append(canon)
        if not texts:
            # vocabulary alone
            for a, c in self._alias.items():
                texts.append(a)
                labels.append(c)
        return texts, labels

    def normalize(self, raw_name: str) -> NormalizationResult:
        raw_name = raw_name if raw_name is not None else ""
        key = preprocess_for_exact(raw_name)

        if not key:
            return NormalizationResult(
                raw_name=raw_name,
                canonical_name=raw_name,
                confidence=0.0,
                loinc=None,
                alternatives=[],
                status=NormalizationStatus.UNKNOWN,
                unknown_term=True,
                backend="empty",
            )

        # Exact / alias hit
        if key in self._alias:
            canon = self._alias[key]
            return NormalizationResult(
                raw_name=raw_name,
                canonical_name=canon,
                confidence=0.994,
                loinc=loinc_for(canon),
                alternatives=[],
                status=NormalizationStatus.NORMALIZED,
                unknown_term=False,
                backend="alias_exact",
                metadata={"preprocessed": key},
            )

        # ML rank
        try:
            ranked = self._backend.rank(key, k=5)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            return NormalizationResult(
                raw_name=raw_name,
                canonical_name=raw_name.strip(),
                confidence=0.0,
                loinc=None,
                alternatives=[],
                status=NormalizationStatus.FAILED,
                unknown_term=True,
                backend=self._backend_name,
                metadata={"error": type(exc).__name__, "preprocessed": key},
            )

        return build_result(
            raw_name,
            ranked,
            backend=self._backend_name,
            min_confidence=self.min_confidence,
            metadata={"preprocessed": key},
        )

    def normalize_test_name(self, raw_name: str) -> str:
        """Protocol-compatible surface API (canonical string only)."""
        return self.normalize(raw_name).canonical_name

    def normalize_unit(self, test_name: str, raw_unit: str | None) -> str | None:
        if raw_unit:
            return raw_unit.strip()
        # prefer unit for canonical form
        canon = self.normalize_test_name(test_name)
        return unit_for(canon)

    @property
    def backend_name(self) -> str:
        return self._backend_name
