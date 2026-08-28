"""Dataset loaders for retrieval evaluation (no proprietary payloads)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_data_dir() -> Path:
    return _repo_root() / "datasets" / "retrieval"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def synthetic_medical_qa_benchmark() -> list[dict[str, Any]]:
    """
    Custom MediVault-oriented questions with expected source keywords.
    PubMedQA/MedQA full dumps are NOT redistributed (license/size).
    Loaders accept external paths if the operator supplies them offline.
    """
    return [
        {
            "id": "q1",
            "question": "What does a high hemoglobin mean?",
            "expected_keywords": ["haemoglobin", "hemoglobin", "cbc"],
            "expected_sources": ["cbc"],
            "kind": "medical",
        },
        {
            "id": "q2",
            "question": "LDL cholesterol is high what should I know?",
            "expected_keywords": ["ldl", "cholesterol", "lipid"],
            "expected_sources": ["lipid"],
            "kind": "medical",
        },
        {
            "id": "q3",
            "question": "Explain HbA1c",
            "expected_keywords": ["hba1c", "glucose", "a1c"],
            "expected_sources": ["hba1c"],
            "kind": "abbreviation",
        },
        {
            "id": "q4",
            "question": "TSH thyroid stimulating hormone elevated",
            "expected_keywords": ["tsh", "thyroid"],
            "expected_sources": ["thyroid"],
            "kind": "synonym",
        },
        {
            "id": "q5",
            "question": "wbc white blood cell count low meaning",
            "expected_keywords": ["wbc", "white", "leucocyte", "leukocyte"],
            "expected_sources": ["cbc"],
            "kind": "synonym",
        },
        {
            "id": "q6",
            "question": "triglicerides high in blood report",
            "expected_keywords": ["triglyceride", "lipid"],
            "expected_sources": ["lipid"],
            "kind": "misspelled",
        },
        {
            "id": "q7",
            "question": (
                "I had a lipid panel last month and my doctor mentioned "
                "non-hdl — what is non hdl cholesterol?"
            ),
            "expected_keywords": ["non-hdl", "non hdl", "cholesterol", "lipid"],
            "expected_sources": ["lipid"],
            "kind": "long",
        },
        {
            "id": "q8",
            "question": "platelets PLT count information",
            "expected_keywords": ["platelet"],
            "expected_sources": ["cbc"],
            "kind": "abbreviation",
        },
        {
            "id": "q9",
            "question": "free t4 vs total t4 thyroid labs",
            "expected_keywords": ["t4", "thyroid", "free"],
            "expected_sources": ["thyroid"],
            "kind": "contextual",
        },
        {
            "id": "q10",
            "question": "general tips for reading lab reports safely",
            "expected_keywords": ["doctor", "lab", "report", "guid"],
            "expected_sources": ["general"],
            "kind": "contextual",
        },
        {
            "id": "q11",
            "question": "HGB low symptoms education",
            "expected_keywords": ["haemoglobin", "hemoglobin", "anemia", "anaemia"],
            "expected_sources": ["cbc"],
            "kind": "abbreviation",
        },
        {
            "id": "q12",
            "question": "hdl good cholesterol role",
            "expected_keywords": ["hdl", "cholesterol"],
            "expected_sources": ["lipid"],
            "kind": "synonym",
        },
    ]


def ensure_dataset_files(data_dir: Path | None = None) -> dict[str, Path]:
    d = data_dir or default_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    eval_path = d / "eval_benchmark.jsonl"
    if not eval_path.exists():
        write_jsonl(eval_path, synthetic_medical_qa_benchmark())
    lic = d / "LICENSING.md"
    if not lic.exists():
        lic.write_text(
            """# Retrieval dataset licensing

| Resource | Redistributed? | Notes |
|----------|----------------|-------|
| MediVault KB (`data/knowledge-base`) | Yes | Project educational text |
| Synthetic QA benchmark | Yes | Generated for MediVault panels |
| PubMedQA | **No** full dump | Optional operator path via env `PUBMEDQA_PATH` |
| MedQA | **No** full dump | Optional operator path via env `MEDQA_PATH` |

Do not commit PHI or proprietary question banks.
""",
            encoding="utf-8",
        )
    return {"eval": eval_path, "licensing": lic}


def load_eval_benchmark(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    ensure_dataset_files(d)
    rows = load_jsonl(d / "eval_benchmark.jsonl")
    return rows or synthetic_medical_qa_benchmark()


def load_external_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    return load_jsonl(Path(path))
