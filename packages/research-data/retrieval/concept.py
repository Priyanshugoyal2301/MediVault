"""
packages/research-data/retrieval/concept.py

Clinical Concept Matching Signal for Longitudinal Evidence Retrieval (CP-06).
Provides deterministic matching between parsed ClinicalQuery concepts and
ResearchEvidenceRecords without fabricating LOINC codes or terminology.
"""

from __future__ import annotations

from typing import Sequence

from packages.ml_interfaces.query import ClinicalQuery
from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.terminology import ClinicalTerminologyMapper


class ConceptScorer:
    """
    Evaluates clinical concept alignment S_concept in [0.0, 1.0].
    Enforces that observations matching the target LOINC code or canonical concept
    receive maximum alignment, while observations for unrelated analytes receive 0.0.
    """

    def __init__(self, mapper: ClinicalTerminologyMapper | None = None) -> None:
        self.mapper = mapper or ClinicalTerminologyMapper()

    def score_record(
        self, query: ClinicalQuery, record: ResearchEvidenceRecord
    ) -> float:
        """
        Computes concept match score between query and record.
        """
        # If query has no analyte or concept information, return neutral score
        if not query.analyte_canonical and not query.loinc_code and not query.concept_id and not query.analyte_mentions:
            return 0.5

        # 1. Exact LOINC match
        if query.loinc_code and record.loinc_code:
            if query.loinc_code.strip() == record.loinc_code.strip():
                return 1.0

        # 2. Exact Concept ID match
        if query.concept_id and record.concept_id:
            if query.concept_id.strip() == record.concept_id.strip():
                return 1.0

        # 3. Exact Canonical Analyte match
        if query.analyte_canonical and record.analyte_canonical:
            if query.analyte_canonical.strip().lower() == record.analyte_canonical.strip().lower():
                return 0.95

        # 4. Alias / Synonym match via ClinicalTerminologyMapper
        if query.analyte_canonical:
            rec_map = self.mapper.map_analyte(record.analyte_raw, record.loinc_code)
            if rec_map.analyte_canonical and rec_map.analyte_canonical.lower() == query.analyte_canonical.lower():
                return 0.90

        # 5. Check analyte mentions against record text
        for mention in query.analyte_mentions:
            mention_clean = mention.strip().lower()
            if mention_clean:
                # Raw text match
                if record.analyte_raw and mention_clean in record.analyte_raw.lower():
                    return 0.75
                if record.analyte_canonical and mention_clean in record.analyte_canonical.lower():
                    return 0.75

        # Disagreement: query specifically targets an analyte that does not match this record
        return 0.0

    def score_patient_evidence(
        self,
        query: ClinicalQuery,
        patient_records: Sequence[ResearchEvidenceRecord],
    ) -> dict[str, float]:
        """
        Returns a mapping of evidence_id -> concept_score for all patient records.
        """
        return {r.id: self.score_record(query, r) for r in patient_records}
