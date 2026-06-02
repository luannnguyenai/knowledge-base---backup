"""P4 Eval harness — run a pipeline on a GoldenSet and produce a full RunResult.

Usage:
    from hcns_eval.harness import run_full_eval, RunResult

    result = run_full_eval(pipeline, golden_set, config, config_path)
    result.save(Path("reports/baseline_result.json"))
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from hcns_shared.interfaces import Pipeline
from hcns_shared.types import Answer, ScoredChunk
from hcns_eval.golden_set import GoldenQuestion, GoldenSet
from hcns_eval.judge import Judge, PROMPT_VERSION_HASH
from hcns_eval.manifest import RunManifest
from hcns_eval.metrics.generation import (
    AggGenerationMetrics,
    GenerationResult,
    aggregate_generation,
    score_generation,
)
from hcns_eval.metrics.retrieval import (
    AggRetrievalMetrics,
    RetrievalResult,
    aggregate_retrieval,
    score_retrieval,
)

# OpenAI pricing per million tokens (USD) — update when pricing changes
_MODEL_PRICES: dict[str, dict[str, float]] = {
    "gpt-4o":           {"input": 5.0,   "output": 15.0},
    "gpt-4o-mini":      {"input": 0.15,  "output": 0.60},
    "gpt-4-turbo":      {"input": 10.0,  "output": 30.0},
    "gpt-3.5-turbo":    {"input": 0.5,   "output": 1.5},
    "o1-preview":       {"input": 15.0,  "output": 60.0},
}


@dataclass
class QuestionResult:
    """All data for one question in a run."""
    question_id: str
    question: str
    expected_answer: str
    expected_sources: list[str]
    generated_answer: str
    citations: list[str]
    contexts: list[str]
    latency_ms: float
    usage: dict[str, int]
    retrieval: RetrievalResult
    generation: GenerationResult

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class RunResult:
    """Complete output of a single pipeline evaluation run.

    Serialisable to JSON for persistent storage and later comparison.
    """
    pipeline_name: str
    manifest: RunManifest
    retrieval: AggRetrievalMetrics
    generation: AggGenerationMetrics
    avg_latency_ms: float
    total_cost_usd: float
    question_results: list[QuestionResult]

    def save(self, path: Path) -> None:
        """Persist to JSON (creates parent dirs)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._to_serialisable(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "RunResult":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls._from_dict(raw)

    # ── serialisation helpers ──────────────────────────────────────────────────

    def _to_serialisable(self) -> dict[str, Any]:
        """Convert to a JSON-safe dict."""
        return {
            "pipeline_name": self.pipeline_name,
            "manifest": asdict(self.manifest),
            "retrieval": {
                "recall_at_k":     self.retrieval.recall_at_k,
                "precision_at_k":  self.retrieval.precision_at_k,
                "mrr":             self.retrieval.mrr,
                "ndcg_at_k":       self.retrieval.ndcg_at_k,
                "num_questions":   self.retrieval.num_questions,
                "k":               self.retrieval.k,
            },
            "generation": {
                "faithfulness":       self.generation.faithfulness,
                "answer_relevancy":   self.generation.answer_relevancy,
                "context_precision":  self.generation.context_precision,
                "correctness":        self.generation.correctness,
                "hallucination_rate": self.generation.hallucination_rate,
                "num_questions":      self.generation.num_questions,
                "num_cached":         self.generation.num_cached,
                "num_llm_calls":      self.generation.num_llm_calls,
            },
            "avg_latency_ms":   self.avg_latency_ms,
            "total_cost_usd":   self.total_cost_usd,
            "question_results": [qr.to_dict() for qr in self.question_results],
        }

    @classmethod
    def _from_dict(cls, d: dict[str, Any]) -> "RunResult":
        manifest = RunManifest.from_dict(d["manifest"])
        ret_d = d["retrieval"]
        gen_d = d["generation"]
        retrieval = AggRetrievalMetrics(
            recall_at_k=ret_d["recall_at_k"],
            precision_at_k=ret_d["precision_at_k"],
            mrr=ret_d["mrr"],
            ndcg_at_k=ret_d["ndcg_at_k"],
            num_questions=ret_d["num_questions"],
            k=ret_d["k"],
        )
        generation = AggGenerationMetrics(
            faithfulness=gen_d["faithfulness"],
            answer_relevancy=gen_d["answer_relevancy"],
            context_precision=gen_d["context_precision"],
            correctness=gen_d["correctness"],
            hallucination_rate=gen_d["hallucination_rate"],
            num_questions=gen_d["num_questions"],
            num_cached=gen_d.get("num_cached", 0),
            num_llm_calls=gen_d.get("num_llm_calls", 0),
        )
        return cls(
            pipeline_name=d["pipeline_name"],
            manifest=manifest,
            retrieval=retrieval,
            generation=generation,
            avg_latency_ms=d["avg_latency_ms"],
            total_cost_usd=d["total_cost_usd"],
            question_results=[],  # not restored (large, use per-question JSON for detail)
        )


# ── Main entry point ──────────────────────────────────────────────────────────

def run_full_eval(
    pipeline: Pipeline,
    golden_set: GoldenSet,
    judge: Judge,
    config_path: Path | None = None,
    pipeline_name: str = "unnamed",
    top_k: int = 5,
    seed: int = 42,
) -> RunResult:
    """Run *pipeline* on *golden_set*, score with *judge*, return RunResult.

    Params:
        pipeline      -- any object implementing Pipeline Protocol (index/query)
        golden_set    -- GoldenSet instance
        judge         -- Judge instance (cached LLM or no-op)
        config_path   -- YAML config path for manifest hashing (None = use placeholder)
        pipeline_name -- human label for the run
        top_k         -- retrieval depth
        seed          -- fixed random seed
    """
    random.seed(seed)
    manifest = RunManifest.create(
        config_path=config_path or Path("/dev/null"),
        golden_set=golden_set,
        judge_model=judge.model,
        judge_prompt_version=judge.prompt_version,
        pipeline_name=pipeline_name,
    )

    q_results: list[QuestionResult] = []
    total_cost = 0.0

    for q in golden_set.questions:
        t0 = time.perf_counter()
        answer: Answer = pipeline.query(q.question)
        latency_ms = (time.perf_counter() - t0) * 1000

        # Retrieval: use citations as proxy for retrieved source ids
        retrieval = score_retrieval(
            question_id=q.id,
            retrieved_ids=answer.citations,
            relevant_ids=q.expected_sources,
            k=top_k,
        )

        # Generation: LLM-judged
        generation = score_generation(
            question_id=q.id,
            question=q.question,
            answer=answer.text,
            expected_answer=q.answer,
            contexts=answer.contexts,
            judge=judge,
        )

        # Cost estimation
        total_cost += _estimate_cost(answer.usage, judge.model)

        q_results.append(QuestionResult(
            question_id=q.id,
            question=q.question,
            expected_answer=q.answer,
            expected_sources=q.expected_sources,
            generated_answer=answer.text,
            citations=answer.citations,
            contexts=answer.contexts,
            latency_ms=latency_ms,
            usage=answer.usage,
            retrieval=retrieval,
            generation=generation,
        ))

    avg_latency = sum(r.latency_ms for r in q_results) / max(1, len(q_results))

    return RunResult(
        pipeline_name=pipeline_name,
        manifest=manifest,
        retrieval=aggregate_retrieval([r.retrieval for r in q_results], k=top_k),
        generation=aggregate_generation([r.generation for r in q_results]),
        avg_latency_ms=avg_latency,
        total_cost_usd=total_cost,
        question_results=q_results,
    )


# ── Cost helpers ───────────────────────────────────────────────────────────────

def _estimate_cost(usage: dict[str, int], judge_model: str) -> float:
    """Estimate USD cost from token counts and judge model pricing."""
    prices = _MODEL_PRICES.get(judge_model, {"input": 0.0, "output": 0.0})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    return (
        prompt_tokens     / 1_000_000 * prices["input"] +
        completion_tokens / 1_000_000 * prices["output"]
    )
