"""
Pure-Python Okapi BM25 for small curated medical KB corpora.

No external IR dependency — suitable for ~O(10)–O(10³) chunks where dense
embeddings add latency/HF download risk without measurable gain.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)

# Minimal English stopwords — prevents "what/is/the" from drowning rare lab terms
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


def tokenize(text: str) -> list[str]:
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text or "")
        if t.lower() not in _STOPWORDS and len(t) > 1
    ]


@dataclass
class BM25Index:
    """In-memory BM25 index over tokenized documents."""

    docs_tokens: list[list[str]]
    doc_len: list[int]
    avgdl: float
    df: dict[str, int]
    N: int
    k1: float = 1.5
    b: float = 0.75

    @classmethod
    def build(
        cls,
        texts: list[str],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> "BM25Index":
        docs_tokens = [tokenize(t) for t in texts]
        doc_len = [len(toks) for toks in docs_tokens]
        N = len(docs_tokens)
        avgdl = (sum(doc_len) / N) if N else 0.0
        df: dict[str, int] = {}
        for toks in docs_tokens:
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        return cls(
            docs_tokens=docs_tokens,
            doc_len=doc_len,
            avgdl=avgdl,
            df=df,
            N=N,
            k1=k1,
            b=b,
        )

    def _idf(self, term: str) -> float:
        # Robertson–Sparck Jones IDF with +1 smoothing
        n_q = self.df.get(term, 0)
        return math.log(1.0 + (self.N - n_q + 0.5) / (n_q + 0.5))

    def score(self, query: str) -> list[float]:
        q_terms = tokenize(query)
        if not q_terms or self.N == 0:
            return [0.0] * self.N

        scores = [0.0] * self.N
        for i, toks in enumerate(self.docs_tokens):
            if not toks:
                continue
            tf = Counter(toks)
            dl = self.doc_len[i]
            s = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                idf = self._idf(term)
                freq = tf[term]
                denom = freq + self.k1 * (1.0 - self.b + self.b * dl / max(self.avgdl, 1e-9))
                s += idf * (freq * (self.k1 + 1.0)) / denom
            scores[i] = s
        return scores

    def top_k(self, query: str, k: int = 5) -> list[tuple[int, float]]:
        scores = self.score(query)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(i, s) for i, s in ranked[:k] if s > 0.0]
