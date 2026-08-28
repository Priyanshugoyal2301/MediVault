"""Retrieval quality metrics."""

from __future__ import annotations

from typing import Sequence


def recall_at_k(
    relevant: Sequence[Sequence[str]],
    retrieved: Sequence[Sequence[str]],
    k: int,
) -> float:
    if not relevant:
        return 0.0
    hits = 0
    for gold, pred in zip(relevant, retrieved):
        g = set(gold)
        p = list(pred)[:k]
        if g and any(x in g for x in p):
            hits += 1
        elif not g:
            hits += 1
    return hits / len(relevant)


def precision_at_k(
    relevant: Sequence[Sequence[str]],
    retrieved: Sequence[Sequence[str]],
    k: int,
) -> float:
    if not relevant:
        return 0.0
    scores = []
    for gold, pred in zip(relevant, retrieved):
        g = set(gold)
        p = list(pred)[:k]
        if not p:
            scores.append(0.0)
            continue
        scores.append(sum(1 for x in p if x in g) / len(p))
    return sum(scores) / len(scores)


def mrr(
    relevant: Sequence[Sequence[str]],
    retrieved: Sequence[Sequence[str]],
) -> float:
    if not relevant:
        return 0.0
    total = 0.0
    for gold, pred in zip(relevant, retrieved):
        g = set(gold)
        rank = 0.0
        for i, p in enumerate(pred, start=1):
            if p in g:
                rank = 1.0 / i
                break
        total += rank
    return total / len(relevant)


def ndcg_at_k(
    relevant: Sequence[Sequence[str]],
    retrieved: Sequence[Sequence[str]],
    k: int,
) -> float:
    def dcg(rels: list[int]) -> float:
        s = 0.0
        for i, r in enumerate(rels, start=1):
            s += (2**r - 1) / __import__("math").log2(i + 1)
        return s

    if not relevant:
        return 0.0
    scores = []
    for gold, pred in zip(relevant, retrieved):
        g = set(gold)
        rels = [1 if p in g else 0 for p in list(pred)[:k]]
        ideal = sorted(rels, reverse=True)
        idcg = dcg(ideal)
        scores.append(0.0 if idcg == 0 else dcg(rels) / idcg)
    return sum(scores) / len(scores)


def keyword_hit(text: str, keywords: Sequence[str]) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in keywords if k)
