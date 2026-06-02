"""Eval harness — runs a Pipeline against a golden set and returns RunMetrics.

The harness knows NOTHING about pipeline internals.
It only calls pipeline.index() and pipeline.query().
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

from hcns_shared.interfaces import Pipeline
from hcns_shared.types import Answer
from hcns_eval.legacy_metrics import (
    RunMetrics,
    aggregate_generation,
    aggregate_retrieval,
)


def load_golden(path: Path) -> list[dict]:
    """Load and return the list of question dicts from a golden set JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["questions"]


def run_eval(
    pipeline: Pipeline,
    golden_path: Path,
    top_k: int = 5,
    seed: int = 42,
    pipeline_name: str = "unnamed",
) -> RunMetrics:
    """Run *pipeline* over *golden_path* and return RunMetrics.

    Params:
        pipeline      -- any object implementing the Pipeline Protocol
        golden_path   -- path to golden set JSON
        top_k         -- retrieval depth to evaluate at
        seed          -- fixed seed for shuffling / reproducibility
        pipeline_name -- label for the run
    """
    random.seed(seed)
    questions = load_golden(golden_path)

    retrieval_rows: list[dict] = []
    generation_rows: list[dict] = []
    latencies: list[float] = []

    for q in questions:
        t0 = time.perf_counter()
        answer: Answer = pipeline.query(q["question"])
        latencies.append((time.perf_counter() - t0) * 1000)

        # Retrieval evaluation: map chunk sources → expected_sources
        # In smoke mode the retrieved doc ids won't match expected_sources
        # (no real corpus) — this is expected; metrics will be ~0 which is correct.
        retrieved_ids = answer.citations  # chunk ids used as proxy
        relevant_ids = q.get("expected_sources", [])
        retrieval_rows.append({"retrieved_ids": retrieved_ids, "relevant_ids": relevant_ids})

        generation_rows.append({
            "answer_text": answer.text,
            "expected_answer": q.get("answer", ""),
            "contexts": answer.contexts,
        })

    run = RunMetrics(pipeline_name=pipeline_name)
    run.retrieval = aggregate_retrieval(retrieval_rows)
    run.generation = aggregate_generation(generation_rows)
    run.avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0
    run.total_questions = len(questions)
    return run
