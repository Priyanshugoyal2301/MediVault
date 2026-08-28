"""
ai-service/rag/ingester.py

Knowledge base ingestion pipeline.

Reads plain-text documents from data/knowledge-base/, chunks them into
~300-word overlapping passages, embeds each chunk via embedder.py, and
stores them in the knowledge_documents table.

CLI usage (from project root):
    python -m services.ai_service.rag.ingester

Idempotent: clears existing documents and re-ingests on each run.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, UTC
from pathlib import Path

from packages.shared_utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Chunking parameters
# ---------------------------------------------------------------------------

CHUNK_WORD_TARGET = 300
CHUNK_WORD_OVERLAP = 50
def _resolve_knowledge_base_dir() -> Path:
    """Prefer repo-root data/knowledge-base; fall back to CWD for alternate launches."""
    candidates = [
        Path(__file__).resolve().parents[3] / "data" / "knowledge-base",
        Path.cwd() / "data" / "knowledge-base",
        Path(__file__).resolve().parents[2] / "data" / "knowledge-base",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


KNOWLEDGE_BASE_DIR = _resolve_knowledge_base_dir()


# ---------------------------------------------------------------------------
# Document parsing
# ---------------------------------------------------------------------------

def _parse_source_header(text: str) -> dict:
    """Extract SOURCE / LICENCE / URL from the header lines of a KB file."""
    header: dict = {"source_title": "Unknown", "source_url": None, "source_licence": None}
    for line in text.split("\n")[:10]:
        if line.startswith("SOURCE:"):
            header["source_title"] = line[len("SOURCE:"):].strip()
        elif line.startswith("URL:"):
            header["source_url"] = line[len("URL:"):].strip()
        elif line.startswith("LICENCE:") or line.startswith("LICENSE:"):
            header["source_licence"] = line.split(":", 1)[1].strip()
    return header


def _chunk_text(text: str, target_words: int = CHUNK_WORD_TARGET,
                overlap_words: int = CHUNK_WORD_OVERLAP) -> list[str]:
    """Split text into overlapping chunks of approximately *target_words*.

    Chunks are split at section boundaries (--- or double-newlines) when
    possible, falling back to word-level splitting.
    """
    # Split on section dividers first
    sections = re.split(r"\n---\n|\n\n(?=[A-Z]{2,})", text)

    chunks: list[str] = []
    current_words: list[str] = []

    for section in sections:
        words = section.split()
        if not words:
            continue

        # If adding this section would exceed target, flush current chunk
        if len(current_words) + len(words) > target_words and current_words:
            chunks.append(" ".join(current_words))
            # Keep overlap
            current_words = current_words[-overlap_words:] if len(current_words) > overlap_words else current_words[:]

        current_words.extend(words)

        # If current chunk exceeds target, split it
        while len(current_words) > target_words:
            chunks.append(" ".join(current_words[:target_words]))
            current_words = current_words[target_words - overlap_words:]

    # Flush remainder
    if current_words:
        chunks.append(" ".join(current_words))

    return [c.strip() for c in chunks if c.strip()]


def load_documents() -> list[dict]:
    """Load and chunk all .txt files from the knowledge base directory.

    Returns a list of dicts ready for embedding + DB insertion:
        [{"source_title", "source_url", "source_licence", "chunk_text", "chunk_index"}, ...]
    """
    kb_dir = _resolve_knowledge_base_dir()
    if not kb_dir.exists():
        logger.warning("Knowledge base directory not found: %s", kb_dir)
        return []

    documents: list[dict] = []
    txt_files = sorted(kb_dir.glob("*.txt"))

    if not txt_files:
        logger.warning("No .txt files found in %s", kb_dir)
        return []

    for filepath in txt_files:
        text = filepath.read_text(encoding="utf-8")
        header = _parse_source_header(text)

        # Remove the header block (everything before the first ---)
        body_match = re.split(r"\n---\n", text, maxsplit=1)
        body = body_match[1] if len(body_match) > 1 else text

        chunks = _chunk_text(body)
        logger.info(
            "Loaded %s: %d chunks from %s",
            filepath.name,
            len(chunks),
            header["source_title"][:60],
        )

        for i, chunk in enumerate(chunks):
            documents.append({
                "id": uuid.uuid4(),
                "source_title": header["source_title"],
                "source_url": header["source_url"],
                "source_licence": header["source_licence"],
                "chunk_text": chunk,
                "chunk_index": i,
            })

    return documents


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Ensure project root is on sys.path
    ROOT = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(ROOT))

    # Install hyphenated module finder
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

    from services.ai_service.rag.embedder import embed_batch  # type: ignore

    docs = load_documents()
    if not docs:
        print("No documents to ingest.")
        sys.exit(0)

    print(f"Loaded {len(docs)} chunks from {KNOWLEDGE_BASE_DIR}")
    print("Embedding chunks (this may take a moment on first run)...")

    texts = [d["chunk_text"] for d in docs]
    embeddings = embed_batch(texts)

    for doc, emb in zip(docs, embeddings):
        doc["embedding"] = emb

    print(f"[OK] Embedded {len(docs)} chunks (dim={len(embeddings[0])})")
    print("Chunks ready for database insertion.")
    print("(In production, this would write to the knowledge_documents table.)")

    # Print summary
    sources = set(d["source_title"] for d in docs)
    for src in sorted(sources):
        count = sum(1 for d in docs if d["source_title"] == src)
        print(f"  - {src[:80]}: {count} chunks")
