"""
data/datasets/evaluate_rag.py

Honest evaluation harness for template RAG (Plan B).

Default retriever: BM25 + intent (matches production demo path).
Optional: --use-dense / --use-minilm for hybrid BM25+MiniLM bake-off.

Reports:
  1. Hit@5 — ≥1 retrieved chunk contains an expected keyword (NOT classical Precision@5)
  2. citation_present — synthesizer emitted citations when chunks exist
  3. tone_violation_rate — substring “you have” / “diagnosed with”

Never cite results as “MiniLM Precision@5” unless dense MiniLM was actually used
and you clearly name the metric Hit@5.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import importlib.util


class _HyphenatedFinder:
    _DIRS = {"services": ROOT / "services", "packages": ROOT / "packages"}

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        parts = fullname.split(".")
        ns = parts[0]
        if ns not in cls._DIRS or len(parts) < 2:
            return None
        base = cls._DIRS[ns]
        pkg_dir = base / parts[1].replace("_", "-")
        if not pkg_dir.exists():
            return None
        rest = parts[2:]
        if not rest:
            init = pkg_dir / "__init__.py"
            if init.exists():
                return importlib.util.spec_from_file_location(
                    fullname, str(init), submodule_search_locations=[str(pkg_dir)]
                )
            return importlib.util.spec_from_file_location(
                fullname, None, submodule_search_locations=[str(pkg_dir)]
            )
        tp = pkg_dir.joinpath(*rest)
        init = tp / "__init__.py"
        py = tp.with_suffix(".py")
        if tp.is_dir() and init.exists():
            return importlib.util.spec_from_file_location(
                fullname, str(init), submodule_search_locations=[str(tp)]
            )
        if py.exists():
            return importlib.util.spec_from_file_location(fullname, str(py))
        return None


if not any(type(f).__name__ == "_HyphenatedFinder" for f in sys.meta_path):
    sys.meta_path.insert(0, _HyphenatedFinder)


LABELED_QA_PAIRS = [
    {"question": "What is normal haemoglobin range for men?", "expected_keywords": ["13.0", "17.0", "g/dL", "men"], "panel": "CBC"},
    {"question": "What causes low haemoglobin?", "expected_keywords": ["anaemia", "iron deficiency", "blood loss", "b12"], "panel": "CBC"},
    {"question": "What is normal white blood cell count?", "expected_keywords": ["4,000", "11,000", "cells", "leucocyte"], "panel": "CBC"},
    {"question": "What does high neutrophils mean?", "expected_keywords": ["bacterial infection", "inflammation", "neutrophilia"], "panel": "CBC"},
    {"question": "What does high lymphocytes indicate?", "expected_keywords": ["viral infection", "immunity", "dengue"], "panel": "CBC"},
    {"question": "Why are eosinophils elevated in India?", "expected_keywords": ["allergic", "parasitic", "eosinophilia"], "panel": "CBC"},
    {"question": "What is normal platelet count?", "expected_keywords": ["150,000", "400,000", "clotting"], "panel": "CBC"},
    {"question": "What causes low platelets?", "expected_keywords": ["dengue", "thrombocytopenia", "bleeding"], "panel": "CBC"},
    {"question": "What is MCV in a blood test?", "expected_keywords": ["size", "red blood cells", "femtolitres", "microcytic"], "panel": "CBC"},
    {"question": "What does low MCV indicate?", "expected_keywords": ["microcytic", "iron deficiency", "thalassaemia"], "panel": "CBC"},
    {"question": "What does high MCV mean?", "expected_keywords": ["macrocytic", "b12", "folate deficiency"], "panel": "CBC"},
    {"question": "What is ESR test used for?", "expected_keywords": ["inflammation", "settle", "infection", "esr"], "panel": "CBC"},
    {"question": "What is normal PCV range for women?", "expected_keywords": ["34.9", "44.5", "percentage", "volume"], "panel": "CBC"},
    {"question": "What are monocytes responsible for?", "expected_keywords": ["chronic", "tuberculosis", "monocytes"], "panel": "CBC"},
    {"question": "What is polycythaemia?", "expected_keywords": ["high rbc", "dehydration", "altitude", "smoking"], "panel": "CBC"},
    {"question": "What is desirable total cholesterol?", "expected_keywords": ["below 200", "mg/dL", "desirable"], "panel": "Lipid"},
    {"question": "Why is LDL called bad cholesterol?", "expected_keywords": ["plaque", "arteries", "atherosclerosis", "heart attack"], "panel": "Lipid"},
    {"question": "What is optimal LDL level?", "expected_keywords": ["below 100", "mg/dL", "optimal"], "panel": "Lipid"},
    {"question": "How can I increase my HDL cholesterol?", "expected_keywords": ["exercise", "healthy fats", "good cholesterol"], "panel": "Lipid"},
    {"question": "What is normal triglyceride level?", "expected_keywords": ["below 150", "mg/dL", "triglycerides"], "panel": "Lipid"},
    {"question": "Why are triglycerides high in Indian diets?", "expected_keywords": ["carbohydrates", "rice", "sugar", "diet"], "panel": "Lipid"},
    {"question": "What is Non-HDL cholesterol?", "expected_keywords": ["total cholesterol minus hdl", "130", "risk"], "panel": "Lipid"},
    {"question": "What is total cholesterol to HDL ratio?", "expected_keywords": ["ratio", "risk", "3.5", "5.0"], "panel": "Lipid"},
    {"question": "What is VLDL cholesterol?", "expected_keywords": ["very low-density", "triglycerides divided by 5"], "panel": "Lipid"},
    {"question": "How does exercise affect lipid levels?", "expected_keywords": ["raise hdl", "lower triglycerides", "exercise"], "panel": "Lipid"},
    {"question": "What are lifestyle changes for high LDL?", "expected_keywords": ["saturated fats", "fibre", "statins", "diet"], "panel": "Lipid"},
    {"question": "What cholesterol level is considered very high LDL?", "expected_keywords": ["190", "very high", "mg/dL"], "panel": "Lipid"},
    {"question": "What is normal TSH level?", "expected_keywords": ["0.4", "4.0", "mIU/L", "pituitary"], "panel": "Thyroid"},
    {"question": "What does high TSH indicate?", "expected_keywords": ["hypothyroidism", "underactive", "tsh"], "panel": "Thyroid"},
    {"question": "What does low TSH indicate?", "expected_keywords": ["hyperthyroidism", "overactive", "tsh"], "panel": "Thyroid"},
    {"question": "What is subclinical hypothyroidism?", "expected_keywords": ["subclinical", "10%", "tsh", "indian"], "panel": "Thyroid"},
    {"question": "What is Free T4?", "expected_keywords": ["thyroxine", "unbound", "active", "0.8"], "panel": "Thyroid"},
    {"question": "What symptoms occur in hypothyroidism?", "expected_keywords": ["fatigue", "weight gain", "cold", "constipation"], "panel": "Thyroid"},
    {"question": "What symptoms occur in hyperthyroidism?", "expected_keywords": ["weight loss", "heartbeat", "anxiety", "tremor"], "panel": "Thyroid"},
    {"question": "What is Free T3 test used for?", "expected_keywords": ["triiodothyronine", "hyperthyroidism", "active"], "panel": "Thyroid"},
    {"question": "What does positive anti-TPO mean?", "expected_keywords": ["autoimmune", "hashimoto", "antibodies"], "panel": "Thyroid"},
    {"question": "Why is TSH high when thyroid is low?", "expected_keywords": ["pituitary", "stimulate", "underactive"], "panel": "Thyroid"},
    {"question": "What is iodine deficiency role in thyroid?", "expected_keywords": ["iodine", "hypothyroidism", "india"], "panel": "Thyroid"},
    {"question": "What is the difference between Total T4 and Free T4?", "expected_keywords": ["bound", "binding proteins", "free"], "panel": "Thyroid"},
    {"question": "What is normal HbA1c percentage?", "expected_keywords": ["below 5.7%", "normal", "glycated"], "panel": "HbA1c"},
    {"question": "What HbA1c range indicates pre-diabetes?", "expected_keywords": ["5.7", "6.4%", "pre-diabetes"], "panel": "HbA1c"},
    {"question": "What HbA1c level diagnoses diabetes?", "expected_keywords": ["6.5%", "diabetes", "glycated"], "panel": "HbA1c"},
    {"question": "What time period does HbA1c measure?", "expected_keywords": ["2-3 months", "average", "blood sugar"], "panel": "HbA1c"},
    {"question": "What is target HbA1c for diabetic patients?", "expected_keywords": ["below 7.0%", "53 mmol/mol", "target"], "panel": "HbA1c"},
    {"question": "Why can iron deficiency affect HbA1c?", "expected_keywords": ["red blood cell", "lifespan", "falsely elevate"], "panel": "HbA1c"},
    {"question": "What is difference between fasting glucose and HbA1c?", "expected_keywords": ["single point", "long-term", "8 hours"], "panel": "HbA1c"},
    {"question": "Why is diabetes common in India?", "expected_keywords": ["77 million", "younger age", "central obesity", "carbohydrates"], "panel": "HbA1c"},
    {"question": "What is post-prandial glucose?", "expected_keywords": ["2 hours after eating", "140 mg/dL"], "panel": "HbA1c"},
    {"question": "What diet factors raise HbA1c in India?", "expected_keywords": ["refined carbohydrates", "white rice", "roti", "maida"], "panel": "HbA1c"},
    {"question": "What is IFCC unit for HbA1c?", "expected_keywords": ["mmol/mol", "39", "48"], "panel": "HbA1c"},
]


def run_evaluation() -> dict:
    from services.ai_service.rag.ingester import load_documents
    from services.ai_service.rag.retriever import load_knowledge_base, retrieve
    from services.ai_service.rag.synthesizer import synthesize

    parser = argparse.ArgumentParser(description="MediVault RAG eval (Plan B)")
    parser.add_argument(
        "--use-dense",
        "--use-minilm",
        action="store_true",
        dest="use_dense",
        help="Bake-off: hybrid BM25 + MiniLM (requires sentence-transformers)",
    )
    args, _unknown = parser.parse_known_args()

    docs = load_documents()
    retriever_name = "bm25+intent"
    mode = "bm25"

    if args.use_dense:
        try:
            from services.ai_service.rag.embedder import embed_text

            for d in docs:
                d["embedding"] = embed_text(d["chunk_text"])
            mode = "hybrid"
            retriever_name = "hybrid-bm25+minilm"
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] dense unavailable ({exc}); falling back to BM25")
            for d in docs:
                d.pop("embedding", None)
            mode = "bm25"
            retriever_name = "bm25+intent-fallback"

    load_knowledge_base(docs, mode=mode)

    total_questions = len(LABELED_QA_PAIRS)
    hit_at_5_count = 0
    citation_present_count = 0
    tone_violation_count = 0
    mrr_sum = 0.0

    print("=" * 60)
    print(f"RAG Evaluation Suite — {total_questions} Labeled Questions")
    print(f"Retriever: {retriever_name}")
    print("Metrics: Hit@5, MRR, citation_present, tone_violation")
    print("=" * 60)

    for qa in LABELED_QA_PAIRS:
        q_text = qa["question"]
        expected_kw = qa["expected_keywords"]
        chunks = retrieve(q_text, top_k=5)

        retrieved_texts = [c.text.lower() for c in chunks]
        hit = False
        first_rank = None
        for rank, text in enumerate(retrieved_texts, start=1):
            if any(kw.lower() in text for kw in expected_kw):
                hit = True
                if first_rank is None:
                    first_rank = rank
        if hit:
            hit_at_5_count += 1
            mrr_sum += 1.0 / float(first_rank or 1)

        synth_result = synthesize(q_text, chunks)
        answer_text = synth_result["answer_en"].lower()
        citations = synth_result["citations"]

        if chunks and len(citations) > 0:
            citation_present_count += 1

        if "you have" in answer_text or "diagnosed with" in answer_text:
            tone_violation_count += 1

    hit_at_5 = round(hit_at_5_count / total_questions, 4)
    mrr = round(mrr_sum / total_questions, 4)
    citation_present_rate = round(citation_present_count / total_questions, 4)
    tone_violation_rate = round(tone_violation_count / total_questions, 4)

    metrics = {
        "total_questions": total_questions,
        "retriever": retriever_name,
        "hit_at_5": hit_at_5,
        "mrr": mrr,
        "citation_present_rate": citation_present_rate,
        "tone_violation_rate": tone_violation_rate,
        "precision_at_5": hit_at_5,  # deprecated alias
        "citation_correctness": citation_present_rate,
        "hallucination_rate": tone_violation_rate,
        "precision_hits": hit_at_5_count,
        "citation_correct_count": citation_present_count,
        "hallucination_count": tone_violation_count,
    }

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS:")
    print(f"  - Retriever:              {retriever_name}")
    print(f"  - Questions Evaluated:    {total_questions}")
    print(f"  - Hit@5 (keyword):        {hit_at_5 * 100:.1f}% ({hit_at_5_count}/{total_questions})")
    print(f"  - MRR:                    {mrr:.4f}")
    print(f"  - Citation present:       {citation_present_rate * 100:.1f}%")
    print(f"  - Tone violation rate:    {tone_violation_rate * 100:.1f}%")
    print("Do not report these as MiniLM Precision@5.")
    print("=" * 60)

    return metrics


if __name__ == "__main__":
    run_evaluation()
