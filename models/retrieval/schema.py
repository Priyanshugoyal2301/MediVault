"""Semantic retrieval result schema (internal; HTTP API unchanged)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RetrievalHit:
    document_id: str
    chunk_id: str
    text: str
    source: str
    source_url: str | None
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)
    is_user_data: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
