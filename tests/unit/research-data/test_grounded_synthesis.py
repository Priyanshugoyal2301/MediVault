"""
tests/unit/research-data/test_grounded_synthesis.py

Comprehensive unit test suite for Grounded Clinical Evidence Synthesis (CP-09).
Verifies:
  1. Claim-level grounding and citation attribution ([evidence_id])
  2. Distinction between Observed Fact, Derived Calculation, and Clinical Interpretation
  3. Interpretation disabled by default (no diagnostic speculation)
  4. Constrained interpretation mode (non-prescriptive, reference only)
  5. Intent-specific synthesis: previous_value (predecessor strictly preserved)
  6. Intent-specific synthesis: current_value (latest state)
  7. Intent-specific synthesis: last_n (exact sequence)
  8. Intent-specific synthesis: first_abnormal (earliest abnormal)
  9. Intent-specific synthesis: date_comparison (pairwise comparison)
  10. Intent-specific synthesis: historical_interval (bounded interval)
  11. Intent-specific synthesis: longitudinal_trend (trajectory anchors + inflection)
  12. Adversarial test: GroundingVerifier detects fabricated numerical hallucination
  13. Adversarial test: GroundingVerifier detects fabricated date hallucination
  14. Adversarial test: GroundingVerifier detects fabricated evidence ID
  15. Safe fallback on empty evidence package (zero hallucinations)
  16. Contract serialization (.to_dict())
"""

from __future__ import annotations

import pytest

from packages.ml_interfaces.query import (
    ClinicalQuery,
    ComparisonTarget,
    QueryIntent,
    TemporalOperator,
)
from packages.research_data.retrieval.contract import RetrievalResult
from packages.research_data.retrieval.longitudinal_selection import (
    LongitudinalEvidencePackage,
    LongitudinalEvidenceSelector,
)
from packages.research_data.synthesis.contracts import (
    FactType,
    GroundedClaim,
    InterpretationPolicy,
)
from packages.research_data.synthesis.fact_extractor import DeterministicFactExtractor
from packages.research_data.synthesis.grounding_verifier import GroundingVerifier
from packages.research_data.synthesis.synthesizer import GroundedEvidenceSynthesizer


def make_cand(
    evidence_id: str,
    date_str: str,
    value: float | str | None,
    score: float = 0.9,
    patient_id: str = "p1",
    analyte: str = "HbA1c",
    flag: str = "normal",
    unit: str = "%",
) -> RetrievalResult:
    return RetrievalResult(
        evidence_id=evidence_id,
        patient_id=patient_id,
        score=score,
        rank=0,
        retrieval_method="test",
        analyte_canonical=analyte,
        concept_id="LOINC:4548-4",
        loinc_code="4548-4",
        observation_date=date_str,
        value=value,
        unit=unit,
        flag=flag,
        source_provenance="synthea:sample",
    )


class TestGroundedClinicalSynthesis:
    @pytest.fixture
    def selector(self) -> LongitudinalEvidenceSelector:
        return LongitudinalEvidenceSelector()

    @pytest.fixture
    def synthesizer(self) -> GroundedEvidenceSynthesizer:
        return GroundedEvidenceSynthesizer(interpretation_policy=InterpretationPolicy.DISABLED)

    def test_observed_and_derived_fact_extraction(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [
            make_cand("ev_1", "2022-01-01T00:00:00Z", 5.5),
            make_cand("ev_2", "2023-01-01T00:00:00Z", 7.0),
        ]
        query = ClinicalQuery(
            raw_query="How has my HbA1c changed?",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        # 1. Observed facts
        assert len(synthesis.observed_facts) == 2
        obs_ids = {f.evidence_id for f in synthesis.observed_facts}
        assert obs_ids == {"ev_1", "ev_2"}

        # 2. Derived facts
        metric_names = {df.metric for df in synthesis.derived_facts}
        assert "absolute_delta" in metric_names
        assert "relative_change_pct" in metric_names
        assert "direction" in metric_names
        assert "span_days" in metric_names

        # Delta calculation verification
        delta_fact = next(df for df in synthesis.derived_facts if df.metric == "absolute_delta")
        assert delta_fact.value == 1.5
        assert set(delta_fact.contributing_evidence_ids) == {"ev_1", "ev_2"}

    def test_claim_level_grounding_audit_passes_100_percent(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [
            make_cand("ev_1", "2022-01-01T00:00:00Z", 5.5),
            make_cand("ev_2", "2023-01-01T00:00:00Z", 7.0),
        ]
        query = ClinicalQuery(
            raw_query="How has my HbA1c changed?",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        # Audit report verification
        assert synthesis.audit_report.total_claims > 0
        assert synthesis.audit_report.claim_grounding_rate == 1.0
        assert synthesis.audit_report.unsupported_claims == 0
        assert synthesis.audit_report.hallucination_detected is False
        assert all(c.is_grounded for c in synthesis.claims)

    def test_interpretation_disabled_by_default(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [
            make_cand("ev_1", "2023-01-01T00:00:00Z", 9.5, flag="high"),
        ]
        query = ClinicalQuery(
            raw_query="What is my HbA1c?",
            intent=QueryIntent.CURRENT_VALUE,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg, interpretation_policy=InterpretationPolicy.DISABLED)

        assert len(synthesis.interpretations) == 0
        assert synthesis.audit_report.interpretation_policy == "DISABLED"

    def test_constrained_interpretation_mode(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [
            make_cand("ev_1", "2023-01-01T00:00:00Z", 9.5, flag="high"),
        ]
        query = ClinicalQuery(
            raw_query="What is my HbA1c?",
            intent=QueryIntent.CURRENT_VALUE,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(
            pkg, interpretation_policy=InterpretationPolicy.CONSTRAINED_REFERENCE_ONLY
        )

        assert len(synthesis.interpretations) == 1
        interp = synthesis.interpretations[0]
        assert interp.evidence_id == "ev_1"
        assert "reference thresholds" in interp.statement
        assert "healthcare provider" in interp.statement
        # Must NOT diagnose
        assert "you have diabetes" not in interp.statement.lower()

    def test_previous_value_synthesis_preserves_predecessor_citation(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [
            make_cand("ev_1", "2021-01-01T00:00:00Z", 5.5),
            make_cand("ev_2", "2022-01-01T00:00:00Z", 6.0),
            make_cand("ev_3", "2023-01-01T00:00:00Z", 6.8),
            make_cand("ev_4", "2024-01-01T00:00:00Z", 7.2),
        ]
        query = ClinicalQuery(
            raw_query="What was my previous HbA1c reading before the latest?",
            intent=QueryIntent.COMPARISON,
            comparison_target=ComparisonTarget.PREVIOUS,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        # Predecessor claim must cite ev_3 (NOT baseline ev_1)
        prev_claim = next(c for c in synthesis.claims if c.claim_id == "claim_prev_val")
        assert prev_claim.evidence_ids == ["ev_3"]
        assert "6.8" in prev_claim.sentence
        assert "[ev_3]" in prev_claim.sentence
        assert "ev_1" not in prev_claim.evidence_ids

        # Reference latest claim must cite ev_4
        ref_claim = next((c for c in synthesis.claims if c.claim_id == "claim_ref_latest"), None)
        assert ref_claim is not None
        assert ref_claim.evidence_ids == ["ev_4"]
        assert "7.2" in ref_claim.sentence

    def test_current_value_synthesis(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [
            make_cand("ev_1", "2023-01-01T00:00:00Z", 6.0),
            make_cand("ev_2", "2024-01-01T00:00:00Z", 6.5),
        ]
        query = ClinicalQuery(
            raw_query="What is my most recent HbA1c level?",
            intent=QueryIntent.CURRENT_VALUE,
            temporal_operator=TemporalOperator.LATEST,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        claim = synthesis.claims[0]
        assert claim.evidence_ids == ["ev_2"]
        assert "6.5 %" in claim.sentence
        assert "[ev_2]" in claim.sentence

    def test_last_n_synthesis(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [
            make_cand("ev_1", "2022-01-01T00:00:00Z", 5.5),
            make_cand("ev_2", "2023-01-01T00:00:00Z", 6.0),
            make_cand("ev_3", "2024-01-01T00:00:00Z", 6.5),
        ]
        query = ClinicalQuery(
            raw_query="Show my last 3 HbA1c results.",
            intent=QueryIntent.LAST_N,
            limit=3,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        list_claim = next(c for c in synthesis.claims if c.claim_id == "claim_last_n_list")
        assert set(list_claim.evidence_ids) == {"ev_1", "ev_2", "ev_3"}
        assert "[ev_1]" in list_claim.sentence
        assert "[ev_2]" in list_claim.sentence
        assert "[ev_3]" in list_claim.sentence

    def test_first_abnormal_synthesis(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [
            make_cand("ev_norm", "2021-01-01T00:00:00Z", 5.4, flag="normal"),
            make_cand("ev_abn1", "2022-01-01T00:00:00Z", 7.2, flag="abnormal"),
            make_cand("ev_abn2", "2023-01-01T00:00:00Z", 8.0, flag="abnormal"),
        ]
        query = ClinicalQuery(
            raw_query="When did my HbA1c first become abnormal?",
            intent=QueryIntent.ABNORMALITY,
            abnormal_only=True,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        abn_claim = synthesis.claims[0]
        assert abn_claim.evidence_ids == ["ev_abn1"]
        assert "7.2 %" in abn_claim.sentence
        assert "[ev_abn1]" in abn_claim.sentence

    def test_adversarial_verifier_catches_fabricated_number(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [make_cand("ev_1", "2023-01-01T00:00:00Z", 6.0)]
        query = ClinicalQuery(raw_query="My HbA1c", intent=QueryIntent.CURRENT_VALUE, analyte_canonical="HbA1c")
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        # Inject an adversarial hallucinated claim with a fabricated number 99.9
        hallucinated_claim = GroundedClaim(
            claim_id="hallucination_num",
            sentence="Your HbA1c spiked to 99.9% unexpectedly [ev_1].",
            fact_type=FactType.OBSERVED,
            evidence_ids=["ev_1"],
            numeric_values=[99.9],
        )

        verifier = GroundingVerifier()
        audit = verifier.audit_synthesis(
            package=pkg,
            claims=[hallucinated_claim],
            observed_facts=synthesis.observed_facts,
            derived_facts=synthesis.derived_facts,
        )

        assert audit.hallucination_detected is True
        assert audit.unsupported_claims == 1
        assert audit.claim_grounding_rate == 0.0

    def test_adversarial_verifier_catches_fabricated_date(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [make_cand("ev_1", "2023-01-01T00:00:00Z", 6.0)]
        query = ClinicalQuery(raw_query="My HbA1c", intent=QueryIntent.CURRENT_VALUE, analyte_canonical="HbA1c")
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        # Inject an adversarial claim with a fabricated date
        hallucinated_claim = GroundedClaim(
            claim_id="hallucination_date",
            sentence="On 2099-12-31 your HbA1c was 6.0% [ev_1].",
            fact_type=FactType.OBSERVED,
            evidence_ids=["ev_1"],
            numeric_values=[6.0],
            date_mentions=["2099-12-31"],
        )

        verifier = GroundingVerifier()
        audit = verifier.audit_synthesis(
            package=pkg,
            claims=[hallucinated_claim],
            observed_facts=synthesis.observed_facts,
            derived_facts=synthesis.derived_facts,
        )

        assert audit.hallucination_detected is True
        assert audit.unsupported_claims == 1
        assert audit.claim_grounding_rate == 0.0

    def test_adversarial_verifier_catches_unselected_evidence_id(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [make_cand("ev_1", "2023-01-01T00:00:00Z", 6.0)]
        query = ClinicalQuery(raw_query="My HbA1c", intent=QueryIntent.CURRENT_VALUE, analyte_canonical="HbA1c")
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        # Inject an adversarial claim citing a fake evidence ID
        fake_id_claim = GroundedClaim(
            claim_id="hallucination_id",
            sentence="Your reading was 6.0% [ev_fabricated].",
            fact_type=FactType.OBSERVED,
            evidence_ids=["ev_fabricated"],
            numeric_values=[6.0],
        )

        verifier = GroundingVerifier()
        audit = verifier.audit_synthesis(
            package=pkg,
            claims=[fake_id_claim],
            observed_facts=synthesis.observed_facts,
            derived_facts=synthesis.derived_facts,
        )

        assert audit.hallucination_detected is True
        assert audit.unsupported_claims == 1
        assert audit.claim_grounding_rate == 0.0

    def test_empty_evidence_package_fallback(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        query = ClinicalQuery(raw_query="My HbA1c", intent=QueryIntent.CURRENT_VALUE, analyte_canonical="HbA1c")
        pkg = selector.select(query, [])
        synthesis = synthesizer.synthesize(pkg)

        assert "No eligible observations" in synthesis.summary_text
        assert len(synthesis.claims) == 0
        assert synthesis.audit_report.hallucination_detected is False
        assert synthesis.audit_report.unsupported_claims == 0
        assert synthesis.audit_report.claim_grounding_rate == 1.0

    def test_contract_serialization_to_dict(
        self, selector: LongitudinalEvidenceSelector, synthesizer: GroundedEvidenceSynthesizer
    ):
        candidates = [
            make_cand("ev_1", "2022-01-01T00:00:00Z", 5.5),
            make_cand("ev_2", "2023-01-01T00:00:00Z", 7.0),
        ]
        query = ClinicalQuery(
            raw_query="How has my HbA1c changed?",
            intent=QueryIntent.TREND,
            analyte_canonical="HbA1c",
        )
        pkg = selector.select(query, candidates)
        synthesis = synthesizer.synthesize(pkg)

        data = synthesis.to_dict()
        assert isinstance(data, dict)
        assert data["patient_id"] == "p1"
        assert len(data["claims"]) > 0
        assert "audit_report" in data
        assert data["audit_report"]["claim_grounding_rate"] == 1.0
