"""
packages/research-data

Longitudinal clinical research data package for MediVault Information Retrieval (CP-03).
Strictly separates research/evaluation cohorts from application user models.
"""

from packages.research_data.models import (
    EvaluationQuery,
    LongitudinalSeries,
    MappingStatus,
    ResearchEvidenceRecord,
    TemporalQueryIntent,
)
from packages.research_data.parsers.mimic_parser import MimicDemoParser
from packages.research_data.parsers.synthea_parser import SyntheaParser
from packages.research_data.quality_audit import DataQualityAuditor, QualityAuditReport
from packages.research_data.splits import (
    partition_patients_disjoint,
    split_records_by_patient,
    verify_patient_disjointness,
)
from packages.research_data.terminology import (
    ClinicalTerminologyMapper,
    LOINC_TO_CANONICAL,
    TerminologyMappingResult,
)


__all__ = [
    "ResearchEvidenceRecord",
    "LongitudinalSeries",
    "EvaluationQuery",
    "MappingStatus",
    "TemporalQueryIntent",
    "SyntheaParser",
    "MimicDemoParser",
    "ClinicalTerminologyMapper",
    "LOINC_TO_CANONICAL",
    "TerminologyMappingResult",
    "DataQualityAuditor",
    "QualityAuditReport",
    "partition_patients_disjoint",
    "split_records_by_patient",
    "verify_patient_disjointness",
]
