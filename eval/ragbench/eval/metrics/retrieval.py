"""Retrieval metrics — Recall@k, Precision@k, MRR, NDCG@k.

All functions are pure (no side effects, no IO).
*k* is always explicit; no global defaults.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class RetrievalResult:
    """Per-question retrieval evaluation result."""
    question_id: str
    retrieved_ids: list[str]
    relevant_ids: list[str]
    recall: float = 0.0
    precision: float = 0.0
    rr: float = 0.0      # reciprocal rank
    ndcg: float = 0.0


@dataclass
class AggRetrievalMetrics:
    """Aggregated retrieval metrics over a set of questions.

    All values are macro-averages (mean over questions).
    """
    recall_at_k: float = 0.0
    precision_at_k: float = 0.0
    mrr: float = 0.0
    ndcg_at_k: float = 0.0
    num_questions: int = 0
    k: int = 5
    per_question: list[RetrievalResult] = field(default_factory=list, compare=False)


# ── Per-question functions ─────────────────────────────────────────────────────

def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of relevant items found in the top-k retrieved.

    Returns 1.0 when *relevant* is empty (trivially satisfied).
    """
    if not relevant:
        return 1.0
    top_k = set(retrieved[:k])
    return len(top_k & set(relevant)) / len(relevant)


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of top-k retrieved items that are relevant."""
    if not retrieved:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for r in top_k if r in set(relevant))
    return hits / k


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    """1/rank of the first relevant item; 0.0 if none found."""
    relevant_set = set(relevant)
    for rank, r in enumerate(retrieved, start=1):
        if r in relevant_set:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k (binary relevance)."""
    relevant_set = set(relevant)
    top_k = retrieved[:k]
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, r in enumerate(top_k, start=1)
        if r in relevant_set
    )
    # Ideal DCG: all relevant items ranked first (up to k)
    ideal_hits = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


# ── Aggregation ────────────────────────────────────────────────────────────────

def aggregate_retrieval(
    results: list[RetrievalResult],
    k: int,
) -> AggRetrievalMetrics:
    """Macro-average all per-question retrieval results."""
    n = len(results)
    if n == 0:
        return AggRetrievalMetrics(k=k)
    return AggRetrievalMetrics(
        recall_at_k=sum(r.recall for r in results) / n,
        precision_at_k=sum(r.precision for r in results) / n,
        mrr=sum(r.rr for r in results) / n,
        ndcg_at_k=sum(r.ndcg for r in results) / n,
        num_questions=n,
        k=k,
        per_question=results,
    )


def score_retrieval(
    question_id: str,
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int,
) -> RetrievalResult:
    """Compute all retrieval metrics for one question."""
    return RetrievalResult(
        question_id=question_id,
        retrieved_ids=retrieved_ids,
        relevant_ids=relevant_ids,
        recall=recall_at_k(retrieved_ids, relevant_ids, k),
        precision=precision_at_k(retrieved_ids, relevant_ids, k),
        rr=reciprocal_rank(retrieved_ids, relevant_ids),
        ndcg=ndcg_at_k(retrieved_ids, relevant_ids, k),
    )
