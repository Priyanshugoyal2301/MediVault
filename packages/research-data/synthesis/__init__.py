"""
packages/research-data/synthesis/__init__.py

Grounded Clinical Evidence Synthesis Package (CP-09).
Provides deterministic fact extraction, claim-level grounded synthesis,
and formal provenance verification.
"""

from .contracts import (
    ClinicalInterpretation,
    DerivedFact,
    FactType,
    GroundedClaim,
    GroundedEvidenceSynthesis,
    GroundingAuditReport,
    InterpretationPolicy,
    ObservedFact,
)
from .fact_extractor import DeterministicFactExtractor
from .grounding_verifier import GroundingVerifier
from .synthesizer import GroundedEvidenceSynthesizer

__all__ = [
    "ClinicalInterpretation",
    "DerivedFact",
    "DeterministicFactExtractor",
    "FactType",
    "GroundedClaim",
    "GroundedEvidenceSynthesis",
    "GroundedEvidenceSynthesizer",
    "GroundingAuditReport",
    "GroundingVerifier",
    "InterpretationPolicy",
    "ObservedFact",
]
