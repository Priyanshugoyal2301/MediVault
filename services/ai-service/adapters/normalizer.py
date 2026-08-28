"""
Normalizer adapters.

AliasNormalizer — legacy rule-based (default).
MLMedicalTestNormalizer — Phase 2 ML engine.
FallbackNormalizer — ML primary → rules on failure.
"""

from __future__ import annotations

from typing import Any

from packages.shared_utils import get_logger

logger = get_logger(__name__)


def _build_full_alias_table() -> dict[str, str]:
    """Prefer ML vocabulary (full); fall back to compact legacy map."""
    try:
        from models.normalizer.vocabulary import alias_lookup_table

        return alias_lookup_table()
    except Exception:
        return {k: v for k, v in _LEGACY_ALIAS.items()}


_LEGACY_ALIAS: dict[str, str] = {
    "hb": "Haemoglobin",
    "hgb": "Haemoglobin",
    "hemoglobin": "Haemoglobin",
    "haemoglobin": "Haemoglobin",
    "wbc": "WBC",
    "tlc": "WBC",
    "rbc": "RBC",
    "plt": "Platelets",
    "platelets": "Platelets",
    "ldl": "LDL Cholesterol",
    "hdl": "HDL Cholesterol",
    "triglycerides": "Triglycerides",
    "tg": "Triglycerides",
    "total cholesterol": "Total Cholesterol",
    "cholesterol": "Total Cholesterol",
    "tsh": "TSH",
    "hba1c": "HbA1c",
    "a1c": "HbA1c",
    "pcv": "Hematocrit",
    "hematocrit": "Hematocrit",
    "haematocrit": "Hematocrit",
}

_UNIT_CANONICAL: dict[str, str] = {
    "haemoglobin": "g/dL",
    "wbc": "/µL",
    "rbc": "million/µL",
    "platelets": "/µL",
    "ldl cholesterol": "mg/dL",
    "hdl cholesterol": "mg/dL",
    "total cholesterol": "mg/dL",
    "triglycerides": "mg/dL",
    "tsh": "µIU/mL",
    "hba1c": "%",
}


class AliasNormalizer:
    """
    Rule-based default for Normalizer Protocol.

    Never deleted. Expanded via models.normalizer.vocabulary when available.
    """

    def __init__(self) -> None:
        self._alias = _build_full_alias_table()

    def normalize_test_name(self, raw_name: str) -> str:
        key = (raw_name or "").strip().lower()
        if not key:
            return raw_name
        try:
            from models.normalizer.preprocess import preprocess_for_exact

            key = preprocess_for_exact(raw_name)
        except Exception:
            pass
        if key in self._alias:
            return self._alias[key]
        for canon in set(self._alias.values()):
            if canon.lower() == key:
                return canon
        return (raw_name or "").strip()

    def normalize_unit(self, test_name: str, raw_unit: str | None) -> str | None:
        if raw_unit:
            return raw_unit.strip()
        key = (test_name or "").strip().lower()
        if key in _UNIT_CANONICAL:
            return _UNIT_CANONICAL[key]
        try:
            from models.normalizer.vocabulary import unit_for

            return unit_for(self.normalize_test_name(test_name))
        except Exception:
            return None


class MLMedicalTestNormalizer:
    """
    Phase 2 ML engine wrapper implementing Normalizer Protocol.
    """

    def __init__(self, engine: Any | None = None) -> None:
        if engine is None:
            from models.normalizer.infer import MedicalTestNormalizer

            engine = MedicalTestNormalizer()
        self._engine = engine
        self.last_result: Any = None

    def normalize(self, raw_name: str) -> Any:
        self.last_result = self._engine.normalize(raw_name)
        return self.last_result

    def normalize_test_name(self, raw_name: str) -> str:
        self.last_result = self._engine.normalize(raw_name)
        return self.last_result.canonical_name

    def normalize_unit(self, test_name: str, raw_unit: str | None) -> str | None:
        return self._engine.normalize_unit(test_name, raw_unit)


class FallbackNormalizer:
    """
    Try primary (ML); on exception use rule AliasNormalizer.
    """

    def __init__(self, primary: Any, fallback: AliasNormalizer | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or AliasNormalizer()
        self.last_path = "unset"
        self.last_result: Any = None

    def normalize(self, raw_name: str) -> Any:
        try:
            if hasattr(self.primary, "normalize"):
                r = self.primary.normalize(raw_name)
                self.last_result = r
                self.last_path = "ml"
                return r
            name = self.primary.normalize_test_name(raw_name)
            self.last_path = "ml"
            return name
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ML normalizer failed; using rule alias fallback reason=%s",
                type(exc).__name__,
            )
            self.last_path = "rule_fallback"
            name = self.fallback.normalize_test_name(raw_name)
            return name

    def normalize_test_name(self, raw_name: str) -> str:
        try:
            name = self.primary.normalize_test_name(raw_name)
            self.last_path = "ml"
            return name
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ML normalizer failed; using rule alias fallback reason=%s",
                type(exc).__name__,
            )
            self.last_path = "rule_fallback"
            return self.fallback.normalize_test_name(raw_name)

    def normalize_unit(self, test_name: str, raw_unit: str | None) -> str | None:
        try:
            return self.primary.normalize_unit(test_name, raw_unit)
        except Exception:
            return self.fallback.normalize_unit(test_name, raw_unit)
