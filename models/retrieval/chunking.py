"""Document chunking for semantic index construction."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any


def parse_source_header(text: str) -> dict[str, Any]:
    header: dict[str, Any] = {
        "source_title": "Unknown",
        "source_url": None,
        "source_licence": None,
    }
    for line in text.split("\n")[:12]:
        if line.startswith("SOURCE:"):
            header["source_title"] = line[len("SOURCE:") :].strip()
        elif line.startswith("URL:"):
            header["source_url"] = line[len("URL:") :].strip()
        elif line.startswith("LICENCE:") or line.startswith("LICENSE:"):
            header["source_licence"] = line.split(":", 1)[1].strip()
    return header


def chunk_text(
    text: str,
    *,
    target_words: int = 300,
    overlap_words: int = 50,
) -> list[str]:
    sections = re.split(r"\n---\n|\n\n(?=[A-Z]{2,})", text)
    chunks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            chunks.append(" ".join(current).strip())
            if overlap_words > 0 and len(current) > overlap_words:
                current = current[-overlap_words:]
            else:
                current = []

    for section in sections:
        words = section.split()
        if not words:
            continue
        if len(words) > target_words and not current:
            start = 0
            while start < len(words):
                end = min(start + target_words, len(words))
                chunks.append(" ".join(words[start:end]).strip())
                if end >= len(words):
                    break
                start = max(0, end - overlap_words)
            continue
        if len(current) + len(words) > target_words and current:
            flush()
        current.extend(words)
        if len(current) >= target_words:
            flush()
    if current:
        chunks.append(" ".join(current).strip())
    return [c for c in chunks if c]


def load_kb_directory(
    directory: Path,
    *,
    target_words: int = 300,
    overlap_words: int = 50,
) -> list[dict[str, Any]]:
    """Load MediVault knowledge-base .txt files into chunk dicts."""
    directory = Path(directory)
    out: list[dict[str, Any]] = []
    if not directory.exists():
        return out
    for path in sorted(directory.glob("*.txt")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        header = parse_source_header(raw)
        # strip header block heuristically
        body = raw
        if "\n---\n" in raw:
            body = raw.split("\n---\n", 1)[1]
        pieces = chunk_text(
            body, target_words=target_words, overlap_words=overlap_words
        )
        doc_id = path.stem
        for i, piece in enumerate(pieces):
            out.append(
                {
                    "document_id": doc_id,
                    "chunk_id": f"{doc_id}::{i}",
                    "id": str(uuid.uuid4()),
                    "source_title": header["source_title"],
                    "source_url": header["source_url"],
                    "source_licence": header.get("source_licence"),
                    "chunk_text": piece,
                    "chunk_index": i,
                    "metadata": {
                        "file": path.name,
                        "panel_hint": doc_id,
                    },
                }
            )
    return out
