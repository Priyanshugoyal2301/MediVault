"""Dataset loaders for test-name normalization (no proprietary content)."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Iterator

from .vocabulary import build_full_vocabulary


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_data_dir() -> Path:
    return _repo_root() / "datasets" / "test_normalization"


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


def pairs_from_vocabulary() -> list[dict[str, Any]]:
    """Generate alias → canonical pairs from built-in vocabulary."""
    rows: list[dict[str, Any]] = []
    for c in build_full_vocabulary():
        canon = c["canonical"]
        loinc = c.get("loinc")
        seen: set[str] = set()
        for a in c.get("aliases") or []:
            key = str(a).strip()
            if not key or key.lower() in seen:
                continue
            seen.add(key.lower())
            rows.append(
                {
                    "raw": key,
                    "canonical": canon,
                    "loinc": loinc,
                    "unknown": False,
                    "source": "vocabulary",
                }
            )
        rows.append(
            {
                "raw": canon,
                "canonical": canon,
                "loinc": loinc,
                "unknown": False,
                "source": "canonical",
            }
        )
    return rows


def generate_synthetic_variants(seed: int = 42) -> list[dict[str, Any]]:
    """Extra noisy variants (mixed case, punct, misspell-ish) for training/eval."""
    rng = random.Random(seed)
    base = pairs_from_vocabulary()
    out: list[dict[str, Any]] = []
    for row in base:
        raw = row["raw"]
        # CASE MIX
        out.append({**row, "raw": raw.upper(), "source": "synthetic_case"})
        out.append({**row, "raw": raw.title(), "source": "synthetic_title"})
        # punctuation noise
        noisy = f"{raw}:"
        out.append({**row, "raw": noisy, "source": "synthetic_punct"})
        if " " in raw and rng.random() < 0.5:
            out.append({**row, "raw": raw.replace(" ", "  "), "source": "synthetic_space"})
        # parentheses style common on labs
        out.append(
            {
                **row,
                "raw": f"{raw} (blood)",
                "source": "synthetic_blood_suffix",
            }
        )
    # Unknown terms (should not map confidently)
    for unk in ("vitamin d", "covid igg", "psa free", "random analyte xyz", "foo bar test"):
        out.append(
            {
                "raw": unk,
                "canonical": "__UNKNOWN__",
                "loinc": None,
                "unknown": True,
                "source": "unknown_seed",
            }
        )
    return out


def load_train_pairs(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    rows = load_jsonl(d / "train_pairs.jsonl")
    if rows:
        return rows
    # compose in-memory if files not written yet
    return pairs_from_vocabulary() + [
        r for r in generate_synthetic_variants() if not r.get("unknown")
    ]


def load_eval_pairs(data_dir: Path | None = None) -> list[dict[str, Any]]:
    d = data_dir or default_data_dir()
    rows = load_jsonl(d / "eval_benchmark.jsonl")
    if rows:
        return rows
    return generate_synthetic_variants(seed=7)


def iterate_raw_labels(rows: list[dict[str, Any]]) -> Iterator[tuple[str, str, bool, str | None]]:
    for r in rows:
        yield (
            str(r.get("raw") or ""),
            str(r.get("canonical") or ""),
            bool(r.get("unknown")),
            r.get("loinc"),
        )


def ensure_dataset_files(data_dir: Path | None = None) -> dict[str, Path]:
    """Materialize JSONL datasets if missing."""
    d = data_dir or default_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    paths = {
        "train": d / "train_pairs.jsonl",
        "eval": d / "eval_benchmark.jsonl",
        "synonyms": d / "synthetic_indian_synonyms.jsonl",
        "loinc": d / "loinc_subset.json",
    }
    if not paths["train"].exists():
        write_jsonl(paths["train"], pairs_from_vocabulary() + [
            r for r in generate_synthetic_variants(seed=42) if not r.get("unknown")
        ])
    if not paths["eval"].exists():
        write_jsonl(paths["eval"], generate_synthetic_variants(seed=7))
    if not paths["synonyms"].exists():
        write_jsonl(paths["synonyms"], pairs_from_vocabulary())
    if not paths["loinc"].exists():
        loinc_rows = [
            {"canonical": c["canonical"], "loinc": c.get("loinc"), "panel": c.get("panel")}
            for c in build_full_vocabulary()
        ]
        paths["loinc"].write_text(json.dumps(loinc_rows, indent=2), encoding="utf-8")
    return paths
