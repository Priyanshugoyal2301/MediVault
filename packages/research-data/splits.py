"""
packages/research-data/splits.py

Patient-disjoint dataset splitting (CP-03).
Guarantees zero patient overlap across dev, val, and test splits to prevent
data and benchmark leakage in longitudinal Information Retrieval evaluation.
"""

from __future__ import annotations

import hashlib
import random
from typing import Sequence

from packages.research_data.models import ResearchEvidenceRecord


def partition_patients_exact(
    patient_ids: Sequence[str],
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
    seed: int = 42,
) -> dict[str, list[str]]:
    """
    Deterministically partitions patient IDs into dev, val, and test sets with
    exact cardinality guarantees using seeded permutation/shuffle (seed=42).

    For N=60 with ratios=(0.6, 0.2, 0.2):
      dev = 36 patients (60.0%)
      val = 12 patients (20.0%)
      test = 12 patients (20.0%)
    """
    dev_r, val_r, test_r = ratios
    if round(dev_r + val_r + test_r, 4) != 1.0:
        raise ValueError(f"Split ratios must sum to 1.0, got {ratios}")

    unique_patients = sorted(set(patient_ids))
    n = len(unique_patients)
    if n == 0:
        return {"dev": [], "val": [], "test": []}

    rng = random.Random(seed)
    shuffled = list(unique_patients)
    rng.shuffle(shuffled)

    val_count = int(round(n * val_r))
    test_count = int(round(n * test_r))
    dev_count = n - val_count - test_count

    dev_p = sorted(shuffled[:dev_count])
    val_p = sorted(shuffled[dev_count : dev_count + val_count])
    test_p = sorted(shuffled[dev_count + val_count :])

    splits = {"dev": dev_p, "val": val_p, "test": test_p}
    verify_patient_disjointness(splits)
    return splits


def partition_patients_hash(
    patient_ids: Sequence[str],
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
    seed: int = 42,
) -> dict[str, list[str]]:
    """
    Legacy hash-based partitioning using cryptographic SHA-256 modulo 10000.
    Preserved for reproducibility and provenance verification.
    """
    dev_r, val_r, test_r = ratios
    if round(dev_r + val_r + test_r, 4) != 1.0:
        raise ValueError(f"Split ratios must sum to 1.0, got {ratios}")

    dev_threshold = int(dev_r * 10000)
    val_threshold = int((dev_r + val_r) * 10000)

    unique_patients = sorted(set(patient_ids))
    dev_p: list[str] = []
    val_p: list[str] = []
    test_p: list[str] = []

    for pid in unique_patients:
        hash_val = int(
            hashlib.sha256(f"{seed}:{pid}".encode("utf-8")).hexdigest()[:8],
            16,
        ) % 10000

        if hash_val < dev_threshold:
            dev_p.append(pid)
        elif hash_val < val_threshold:
            val_p.append(pid)
        else:
            test_p.append(pid)

    splits = {"dev": sorted(dev_p), "val": sorted(val_p), "test": sorted(test_p)}
    verify_patient_disjointness(splits)
    return splits


def partition_patients_disjoint(
    patient_ids: Sequence[str],
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
    seed: int = 42,
    policy: str = "exact",
) -> dict[str, list[str]]:
    """
    Deterministically partitions patient IDs into dev, val, and test sets.
    Defaults to exact-cardinality policy (seed=42) for CP-05.5 research benchmark.
    Supports legacy 'hash' policy for backward compatibility.
    """
    if policy == "exact":
        return partition_patients_exact(patient_ids, ratios=ratios, seed=seed)
    elif policy == "hash":
        return partition_patients_hash(patient_ids, ratios=ratios, seed=seed)
    else:
        raise ValueError(f"Unknown split policy '{policy}'. Supported: 'exact', 'hash'")


def verify_patient_disjointness(patient_splits: dict[str, list[str]]) -> bool:
    """Asserts that dev, val, and test patient sets are mutually disjoint."""
    dev_set = set(patient_splits.get("dev", []))
    val_set = set(patient_splits.get("val", []))
    test_set = set(patient_splits.get("test", []))

    dev_val = dev_set.intersection(val_set)
    dev_test = dev_set.intersection(test_set)
    val_test = val_set.intersection(test_set)

    if dev_val or dev_test or val_test:
        raise ValueError(
            f"Patient leakage detected across splits! "
            f"dev-val overlap: {len(dev_val)}, "
            f"dev-test overlap: {len(dev_test)}, "
            f"val-test overlap: {len(val_test)}"
        )
    return True


def split_records_by_patient(
    records: Sequence[ResearchEvidenceRecord],
    patient_splits: dict[str, list[str]],
) -> dict[str, list[ResearchEvidenceRecord]]:
    """Partitions research evidence records based on pre-assigned patient splits."""
    dev_set = set(patient_splits["dev"])
    val_set = set(patient_splits["val"])
    test_set = set(patient_splits["test"])

    out: dict[str, list[ResearchEvidenceRecord]] = {
        "dev": [],
        "val": [],
        "test": [],
        "unassigned": [],
    }

    for rec in records:
        pid = rec.source_patient_id
        if pid in dev_set:
            out["dev"].append(rec)
        elif pid in val_set:
            out["val"].append(rec)
        elif pid in test_set:
            out["test"].append(rec)
        else:
            out["unassigned"].append(rec)

    return out
