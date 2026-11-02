"""
packages/research-data/retrieval/bm25.py

Lexical Evidence Retrieval Baseline using Robertson–Sparck Jones Okapi BM25 (CP-06).
Builds patient-scoped lexical indexes over atomic ResearchEvidenceRecords.
Enriches documents with canonical concepts, LOINC codes, and vocabulary aliases.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Sequence

from packages.ml_interfaces.query import ClinicalQuery
from packages.research_data.models import ResearchEvidenceRecord
from packages.research_data.retrieval.contract import (
    EvidenceRetriever,
    RetrievalResult,
    filter_patient_evidence,
    sort_and_rank_results,
)
from packages.research_data.terminology import ClinicalTerminologyMapper

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "do", "does", "did", "of", "in", "on", "for", "to", "from",
    "with", "as", "by", "at", "or", "and", "but", "if", "then", "than",
    "so", "such", "no", "nor", "not", "only", "own", "same", "too",
    "very", "can", "will", "just", "about", "into", "over", "after",
    "how", "why", "when", "where", "my", "your", "our", "their", "it",
    "its", "me", "you", "we", "they", "i", "he", "she",
})

# Canonical analyte to common clinical query synonyms
_COMMON_SYNONYMS: dict[str, list[str]] = {
    "HbA1c": ["glycated hemoglobin", "glycated haemoglobin", "a1c", "hemoglobin a1c", "haemoglobin a1c"],
    "Glucose": ["blood sugar", "fasting glucose", "serum glucose", "plasma glucose", "sugar level", "fasting blood sugar"],
    "Total Cholesterol": ["cholesterol", "serum cholesterol", "total lipid"],
    "LDL Cholesterol": ["ldl", "bad cholesterol", "low density lipoprotein"],
    "HDL Cholesterol": ["hdl", "good cholesterol", "high density lipoprotein"],
    "Triglycerides": ["triglyceride", "triacylglycerol", "tg"],
    "Haemoglobin": ["hemoglobin", "hb", "hgb", "blood count hemoglobin"],
    "Creatinine": ["serum creatinine", "kidney creatinine", "cr", "creat"],
    "TSH": ["thyroid stimulating hormone", "thyrotropin", "thyroid function"],
    "Platelets": ["platelet count", "thrombocytes", "plt"],
    "WBC": ["white blood cell", "leukocytes", "white count", "wbc count"],
}


def tokenize(text: str) -> list[str]:
    """Tokenize and filter standard English stopwords."""
    if not text:
        return []
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text)
        if t.lower() not in _STOPWORDS and len(t) > 1
    ]


def format_evidence_lexical_doc(
    record: ResearchEvidenceRecord,
    mapper: ClinicalTerminologyMapper | None = None,
) -> str:
    """
    Constructs a rich textual representation of an atomic Evidence Observation.
    Exposes canonical concepts, raw description, LOINC code, synonyms, values, units,
    abnormality flags, and temporal tokens.
    """
    parts: list[str] = []

    # 1. Analyte identity
    if record.analyte_canonical:
        parts.append(record.analyte_canonical)
        syns = _COMMON_SYNONYMS.get(record.analyte_canonical, [])
        if syns:
            parts.extend(syns)

    if record.analyte_raw:
        parts.append(record.analyte_raw)

    # 2. Concept & LOINC
    if record.loinc_code:
        parts.append(record.loinc_code)
        parts.append(f"LOINC:{record.loinc_code}")
    if record.concept_id and record.concept_id != f"LOINC:{record.loinc_code}":
        parts.append(record.concept_id)

    # 3. Numeric / text value & unit
    if record.value_numeric is not None:
        parts.append(str(record.value_numeric))
    if record.value_text:
        parts.append(record.value_text)
    if record.unit:
        parts.append(record.unit)

    # 4. Abnormality / clinical flag
    if record.flag:
        parts.append(record.flag)
        if record.flag.lower() in ("abnormal", "high", "low"):
            parts.append("abnormal")
            parts.append("out of range")

    # 5. Temporal / date tokens (e.g. 2024-04-05 -> 2024, 04, 05, April)
    if record.observation_date:
        parts.append(record.observation_date[:10])
        year = record.observation_date[:4]
        month = record.observation_date[5:7] if len(record.observation_date) >= 7 else ""
        parts.append(year)
        if month:
            parts.append(month)

    return " ".join(parts)


class EvidenceBM25Index:
    """
    In-memory Okapi BM25 Index over a collection of ResearchEvidenceRecords.
    """

    def __init__(
        self,
        records: Sequence[ResearchEvidenceRecord],
        k1: float = 1.5,
        b: float = 0.75,
        mapper: ClinicalTerminologyMapper | None = None,
    ) -> None:
        self.records = list(records)
        self.k1 = k1
        self.b = b
        self.mapper = mapper or ClinicalTerminologyMapper()

        self.docs_tokens = [
            tokenize(format_evidence_lexical_doc(r, self.mapper)) for r in self.records
        ]
        self.doc_lens = [len(toks) for toks in self.docs_tokens]
        self.N = len(self.docs_tokens)
        self.avgdl = (sum(self.doc_lens) / self.N) if self.N > 0 else 0.0

        self.df: dict[str, int] = {}
        for toks in self.docs_tokens:
            for term in set(toks):
                self.df[term] = self.df.get(term, 0) + 1

    def _idf(self, term: str) -> float:
        n_q = self.df.get(term, 0)
        return math.log(1.0 + (self.N - n_q + 0.5) / (n_q + 0.5))

    def score(self, query_text: str) -> list[float]:
        q_terms = tokenize(query_text)
        if not q_terms or self.N == 0:
            return [0.0] * self.N

        scores = [0.0] * self.N
        for idx, toks in enumerate(self.docs_tokens):
            if not toks:
                continue
            tf = Counter(toks)
            dl = self.doc_lens[idx]
            s = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                idf = self._idf(term)
                freq = tf[term]
                denom = freq + self.k1 * (1.0 - self.b + self.b * dl / max(self.avgdl, 1e-9))
                s += idf * (freq * (self.k1 + 1.0)) / denom
            scores[idx] = s
        return scores


class EvidenceBM25Retriever(EvidenceRetriever):
    """
    Standalone deterministic BM25 Retriever for longitudinal evidence records.
    Enforces strict patient-scoping before scoring.
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        mapper: ClinicalTerminologyMapper | None = None,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.mapper = mapper or ClinicalTerminologyMapper()

    def build_query_string(self, query: ClinicalQuery) -> str:
        """Constructs an enriched query string leveraging parsed clinical concepts."""
        parts = [query.raw_query]
        if query.analyte_canonical:
            parts.append(query.analyte_canonical)
            syns = _COMMON_SYNONYMS.get(query.analyte_canonical, [])
            if syns:
                parts.extend(syns)
        if query.loinc_code:
            parts.append(query.loinc_code)
        if query.start_date:
            parts.append(query.start_date.isoformat())
        if query.end_date:
            parts.append(query.end_date.isoformat())
        if query.abnormal_only:
            parts.append("abnormal out of range")
        return " ".join(parts)

    def retrieve(
        self,
        query: ClinicalQuery,
        evidence: Sequence[ResearchEvidenceRecord],
        top_k: int = 10,
        patient_id: str | None = None,
    ) -> list[RetrievalResult]:
        target_pid = patient_id or (getattr(query, "patient_id", None))
        if not target_pid:
            # If query has no patient_id specified and not passed, raise or check
            return []

        patient_records = filter_patient_evidence(evidence, target_pid)
        if not patient_records:
            return []

        index = EvidenceBM25Index(
            patient_records, k1=self.k1, b=self.b, mapper=self.mapper
        )
        q_str = self.build_query_string(query)
        raw_scores = index.score(q_str)

        results: list[RetrievalResult] = []
        for rec, score in zip(patient_records, raw_scores):
            results.append(
                RetrievalResult(
                    evidence_id=rec.id,
                    patient_id=rec.source_patient_id,
                    score=float(score),
                    rank=0,  # assigned by sort_and_rank_results
                    retrieval_method="bm25",
                    analyte_canonical=rec.analyte_canonical,
                    concept_id=rec.concept_id,
                    loinc_code=rec.loinc_code,
                    observation_date=rec.observation_date,
                    value=rec.value_numeric if rec.value_numeric is not None else rec.value_text,
                    unit=rec.unit,
                    flag=rec.flag,
                    source_provenance=rec.source_provenance,
                    metadata={"raw_bm25_score": round(score, 6)},
                )
            )

        return sort_and_rank_results(results, top_k=top_k)
