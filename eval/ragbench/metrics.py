"""Retrieval and generation metrics for the eval harness.

All functions are pure (no side effects) and accept primitive types so they
can be tested without instantiating any pipeline.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class RetrievalMetrics:
    """Aggregated retrieval metrics over a golden set."""

    recall_at_k: float = 0.0
    context_precision: float = 0.0
    mrr: float = 0.0
    ndcg_at_k: float = 0.0
    num_questions: int = 0


@dataclass
class GenerationMetrics:
    """Aggregated generation metrics over a golden set.

    Note: In P0 with FakeGenerator, answer_relevancy and faithfulness are
    approximated by simple string overlap — real LLM-as-judge is P2+.
    """

    answer_relevancy: float = 0.0
    faithfulness: float = 0.0
    num_questions: int = 0


@dataclass
class RunMetrics:
    """Combined metrics for a single benchmark run."""

    pipeline_name: str
    retrieval: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    generation: GenerationMetrics = field(default_factory=GenerationMetrics)
    avg_latency_ms: float = 0.0
    total_questions: int = 0


# ── Retrieval helpers ──────────────────────────────────────────────────────────

def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """Fraction of relevant sources found in the retrieved set."""
    if not relevant_ids:
        return 1.0
    hits = len(set(retrieved_ids) & set(relevant_ids))
    return hits / len(relevant_ids)


def precision_at_k(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """Fraction of retrieved items that are relevant."""
    if not retrieved_ids:
        return 0.0
    hits = len(set(retrieved_ids) & set(relevant_ids))
    return hits / len(retrieved_ids)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """1/rank of the first relevant item; 0 if none found."""
    relevant_set = set(relevant_ids)
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_set:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """Normalized Discounted Cumulative Gain (binary relevance)."""
    relevant_set = set(relevant_ids)
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, rid in enumerate(retrieved_ids, start=1)
        if rid in relevant_set
    )
    ideal_hits = min(len(relevant_ids), len(retrieved_ids))
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


# ── Generation helpers ─────────────────────────────────────────────────────────

def token_overlap_score(text_a: str, text_b: str) -> float:
    """Simple token Jaccard similarity (proxy for relevancy in P0)."""
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# ── Aggregation ────────────────────────────────────────────────────────────────

def aggregate_retrieval(
    per_question: list[dict],  # each dict: {retrieved_ids, relevant_ids}
) -> RetrievalMetrics:
    n = len(per_question)
    if n == 0:
        return RetrievalMetrics()
    metrics = RetrievalMetrics(num_questions=n)
    metrics.recall_at_k = sum(
        recall_at_k(q["retrieved_ids"], q["relevant_ids"]) for q in per_question
    ) / n
    metrics.context_precision = sum(
        precision_at_k(q["retrieved_ids"], q["relevant_ids"]) for q in per_question
    ) / n
    metrics.mrr = sum(
        reciprocal_rank(q["retrieved_ids"], q["relevant_ids"]) for q in per_question
    ) / n
    metrics.ndcg_at_k = sum(
        ndcg_at_k(q["retrieved_ids"], q["relevant_ids"]) for q in per_question
    ) / n
    return metrics


def aggregate_generation(
    per_question: list[dict],  # each dict: {answer_text, expected_answer, contexts}
) -> GenerationMetrics:
    n = len(per_question)
    if n == 0:
        return GenerationMetrics()
    metrics = GenerationMetrics(num_questions=n)
    metrics.answer_relevancy = sum(
        token_overlap_score(q["answer_text"], q["expected_answer"]) for q in per_question
    ) / n
    # Faithfulness proxy: overlap between answer and concatenated context
    metrics.faithfulness = sum(
        token_overlap_score(q["answer_text"], " ".join(q["contexts"])) for q in per_question
    ) / n
    return metrics
