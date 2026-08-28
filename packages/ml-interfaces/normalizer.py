"""Normalizer — map lab test aliases / units to canonical forms."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Normalizer(Protocol):
    """
    Canonicalize free-text lab names (and optionally units/values).

    Default: alias-table / regex normalizer (AliasNormalizer).
    Phase 2: USE_ML_NORMALIZER=1 → MedicalTestNormalizer under models/normalizer/.

    Contract:
      normalize_test_name → canonical string (pass-through if unknown).
      Optional adapters may also expose normalize() for confidence/LOINC.
    """

    def normalize_test_name(self, raw_name: str) -> str:
        """Return canonical test name; pass-through if unknown."""
        ...

    def normalize_unit(self, test_name: str, raw_unit: str | None) -> str | None:
        """Return preferred unit string for a canonical test; pass-through if unknown."""
        ...


@runtime_checkable
class MedicalTestNormalizerProtocol(Protocol):
    """
    Rich Phase 2 normalizer (optional). Implementations live in models/normalizer.
    Public HTTP API does not expose LOINC/confidence (BC).
    """

    def normalize(self, raw_name: str) -> object:
        """Return rich result with canonical, confidence, loinc, alternatives, status."""
        ...

    def normalize_test_name(self, raw_name: str) -> str:
        ...

    def normalize_unit(self, test_name: str, raw_unit: str | None) -> str | None:
        ...
