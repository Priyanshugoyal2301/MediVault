"""RAG pipeline — knowledge base ingestion, embedding, retrieval, and answer synthesis."""

from .retriever import RetrievedChunk, retrieve
from .synthesizer import synthesize

__all__ = ["RetrievedChunk", "retrieve", "synthesize"]
