"""Generation metrics — RAGAS-style + DeepEval-style, all LLM-judged.

RAGAS metrics  : faithfulness, answer_relevancy, context_precision
DeepEval metrics: correctness, hallucination_rate

All metrics delegate scoring to Judge (with file-based caching) so two
identical runs always produce identical numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ragbench.eval.judge import Judge, JudgeResult


@dataclass
class GenerationResult:
    """Per-question generation evaluation result."""
    question_id: str
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    correctness: float = 0.0
    hallucination_rate: float = 0.0
    # Track which scores came from cache (for reporting)
    cached_flags: dict[str, bool] = field(default_factory=dict, compare=False)


@dataclass
class AggGenerationMetrics:
    """Aggregated generation metrics (macro-average over questions)."""
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    correctness: float = 0.0
    hallucination_rate: float = 0.0
    num_questions: int = 0
    num_cached: int = 0         # judge calls served from cache
    num_llm_calls: int = 0      # judge calls that hit the LLM
    per_question: list[GenerationResult] = field(default_factory=list, compare=False)


# ── Per-question scoring ───────────────────────────────────────────────────────

def score_generation(
    question_id: str,
    question: str,
    answer: str,
    expected_answer: str,
    contexts: list[str],
    judge: Judge,
) -> GenerationResult:
    """Run all five generation metrics for one question via the judge."""
    results: dict[str, JudgeResult] = {
        "faithfulness":     judge.faithfulness(question, answer, contexts),
        "answer_relevancy": judge.answer_relevancy(question, answer),
        "context_precision": judge.context_precision(question, contexts),
        "correctness":      judge.correctness(question, answer, expected_answer),
        "hallucination":    judge.hallucination(answer, contexts),
    }
    return GenerationResult(
        question_id=question_id,
        faithfulness=results["faithfulness"].score,
        answer_relevancy=results["answer_relevancy"].score,
        context_precision=results["context_precision"].score,
        correctness=results["correctness"].score,
        hallucination_rate=results["hallucination"].score,
        cached_flags={k: r.cached for k, r in results.items()},
    )


# ── Aggregation ────────────────────────────────────────────────────────────────

def aggregate_generation(results: list[GenerationResult]) -> AggGenerationMetrics:
    """Macro-average all per-question generation results."""
    n = len(results)
    if n == 0:
        return AggGenerationMetrics()

    def avg(attr: str) -> float:
        return sum(getattr(r, attr) for r in results) / n

    # Count cache hits across all metrics (5 per question)
    total_calls = n * 5
    cached_count = sum(sum(r.cached_flags.values()) for r in results)

    return AggGenerationMetrics(
        faithfulness=avg("faithfulness"),
        answer_relevancy=avg("answer_relevancy"),
        context_precision=avg("context_precision"),
        correctness=avg("correctness"),
        hallucination_rate=avg("hallucination_rate"),
        num_questions=n,
        num_cached=cached_count,
        num_llm_calls=total_calls - cached_count,
        per_question=results,
    )
