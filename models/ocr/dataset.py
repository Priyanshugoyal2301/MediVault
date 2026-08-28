"""
Dataset infrastructure for document understanding (Phase 1).

Supports cataloging:
  - Medical Laboratory OCR Dataset (local fixtures)
  - Synthetic reports
  - Indian lab reports
  - MIMIC-derived reports (placeholder layout only)

No downloads. No training loops.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Literal

DatasetKind = Literal[
    "synthetic",
    "indian_lab",
    "medical_laboratory_ocr",
    "mimic_future",
]


@dataclass
class DocumentSample:
    sample_id: str
    kind: DatasetKind
    # Either raw text (for IE-from-text eval) or path to binary
    text: str | None = None
    file_path: Path | None = None
    mime_type: str = "text/plain"
    # gold lab fields: test_name -> numeric value
    gold_fields: dict[str, float] = field(default_factory=dict)
    gold_units: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOC_PARSING = ROOT / "datasets" / "document_parsing"
PLAN_C = ROOT / "data" / "datasets" / "plan_c"


class DocumentParsingDataset:
    """
    Lightweight dataset loader / enumerator.

    layout expected (when populated)::

        datasets/document_parsing/
          synthetic/
          indian_lab/
          medical_laboratory_ocr/
          mimic_future/
          index.jsonl
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else DEFAULT_DOC_PARSING

    def list_splits(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )

    def iter_index(self) -> Iterator[DocumentSample]:
        index = self.root / "index.jsonl"
        if index.exists():
            for line in index.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                yield self._from_json(json.loads(line))
            return
        # Fallback: synthetic fixtures from Plan C IE (text-only)
        yield from self.iter_synthetic_from_plan_c()

    def iter_synthetic_from_plan_c(self) -> Iterator[DocumentSample]:
        try:
            from data.datasets.plan_c.ie_fixtures import load_fixtures
        except Exception:
            # path import
            import sys

            sys.path.insert(0, str(ROOT))
            from data.datasets.plan_c.ie_fixtures import load_fixtures  # type: ignore

        for fx in load_fixtures():
            gold = {g.test_name: g.value for g in fx.gold}
            units = {g.test_name: g.unit for g in fx.gold if g.unit}
            yield DocumentSample(
                sample_id=fx.fixture_id,
                kind="synthetic",
                text=fx.text,
                mime_type="text/plain",
                gold_fields=gold,
                gold_units={k: v for k, v in units.items() if v},
                metadata={"layout": fx.layout, "source": "plan_c/ie_fixtures"},
            )

    def iter_kind(self, kind: DatasetKind) -> Iterator[DocumentSample]:
        for s in self.iter_index():
            if s.kind == kind:
                yield s

    def summary(self) -> dict[str, Any]:
        samples = list(self.iter_index())
        by_kind: dict[str, int] = {}
        for s in samples:
            by_kind[s.kind] = by_kind.get(s.kind, 0) + 1
        return {
            "root": str(self.root),
            "n_samples": len(samples),
            "by_kind": by_kind,
            "splits": self.list_splits(),
            "mimic_status": "placeholder_only",
        }

    def _from_json(self, obj: dict[str, Any]) -> DocumentSample:
        fp = obj.get("file_path")
        return DocumentSample(
            sample_id=str(obj["sample_id"]),
            kind=obj.get("kind") or "synthetic",  # type: ignore[arg-type]
            text=obj.get("text"),
            file_path=Path(fp) if fp else None,
            mime_type=obj.get("mime_type") or "text/plain",
            gold_fields={k: float(v) for k, v in (obj.get("gold_fields") or {}).items()},
            gold_units=dict(obj.get("gold_units") or {}),
            metadata=dict(obj.get("metadata") or {}),
        )


def write_sample_index(samples: list[DocumentSample], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for s in samples:
            row = {
                "sample_id": s.sample_id,
                "kind": s.kind,
                "text": s.text,
                "file_path": str(s.file_path) if s.file_path else None,
                "mime_type": s.mime_type,
                "gold_fields": s.gold_fields,
                "gold_units": s.gold_units,
                "metadata": s.metadata,
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
