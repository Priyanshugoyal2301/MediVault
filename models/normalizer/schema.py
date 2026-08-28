"""Normalization result schema (internal). Not exposed on public /parse API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class NormalizationStatus(str, Enum):
    NORMALIZED = "NORMALIZED"
    UNKNOWN = "UNKNOWN"
    PASSTHROUGH = "PASSTHROUGH"
    FAILED = "FAILED"


@dataclass
class AlternativeMatch:
    canonical_name: str
    confidence: float
    loinc: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizationResult:
    """Full output of MedicalTestNormalizer."""

    raw_name: str
    canonical_name: str
    confidence: float
    loinc: str | None
    alternatives: list[AlternativeMatch] = field(default_factory=list)
    status: NormalizationStatus = NormalizationStatus.UNKNOWN
    unknown_term: bool = True
    backend: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_name": self.raw_name,
            "canonical_name": self.canonical_name,
            "confidence": self.confidence,
            "loinc": self.loinc,
            "alternatives": [a.to_dict() for a in self.alternatives],
            "status": self.status.value if isinstance(self.status, NormalizationStatus) else self.status,
            "unknown_term": self.unknown_term,
            "backend": self.backend,
            "metadata": self.metadata,
        }
