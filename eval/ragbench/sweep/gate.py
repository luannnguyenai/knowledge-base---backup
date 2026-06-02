"""Regression gate — compare a new RunResult against a saved baseline.

Gate fails (returns exit code 1) if any metric exceeds its configured threshold.
The gate is reproducible: given the same inputs it always produces the same decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ragbench.eval.harness import RunResult
from ragbench.sweep.config import GateConfig, MetricThreshold


@dataclass
class MetricCheck:
    """Result of checking one metric against its threshold."""
    metric: str
    baseline: float
    candidate: float
    delta: float           # candidate - baseline
    passed: bool
    reason: str            # human-readable verdict


@dataclass
class GateResult:
    """Full gate decision with per-metric details."""
    passed: bool
    checks: list[MetricCheck]
    baseline_pipeline: str
    candidate_pipeline: str

    @property
    def failed_checks(self) -> list[MetricCheck]:
        return [c for c in self.checks if not c.passed]

    def exit_code(self) -> int:
        return 0 if self.passed else 1

    def format_report(self) -> str:
        lines: list[str] = [
            f"Regression Gate: {self.candidate_pipeline} vs {self.baseline_pipeline}",
            "",
        ]
        for check in sorted(self.checks, key=lambda c: c.passed):
            icon = "✓" if check.passed else "✗"
            lines.append(
                f"  {icon} {check.metric:30s}  "
                f"candidate={check.candidate:.4f}  "
                f"baseline={check.baseline:.4f}  "
                f"Δ={check.delta:+.4f}  "
                f"{'PASS' if check.passed else 'FAIL'}"
            )
            if not check.passed:
                lines.append(f"    └─ {check.reason}")
        lines += [
            "",
            f"{'✓ Gate PASSED' if self.passed else '✗ Gate FAILED'}"
            + (f" ({len(self.failed_checks)} metric(s) out of threshold)" if not self.passed else ""),
        ]
        return "\n".join(lines)


# ── Core gate check ────────────────────────────────────────────────────────────

def check_gate(
    candidate: RunResult,
    baseline: RunResult,
    gate_cfg: GateConfig,
) -> GateResult:
    """Compare *candidate* against *baseline* using *gate_cfg* thresholds.

    Returns a GateResult; call .exit_code() for the CI exit code.
    """
    cand_metrics = _extract_metrics(candidate)
    base_metrics  = _extract_metrics(baseline)

    checks: list[MetricCheck] = []
    for metric, threshold in gate_cfg.thresholds.items():
        if metric not in cand_metrics or metric not in base_metrics:
            continue
        cand_val = cand_metrics[metric]
        base_val  = base_metrics[metric]
        check = _check_metric(metric, cand_val, base_val, threshold)
        checks.append(check)

    passed = all(c.passed for c in checks)
    return GateResult(
        passed=passed,
        checks=checks,
        baseline_pipeline=baseline.pipeline_name,
        candidate_pipeline=candidate.pipeline_name,
    )


def _check_metric(
    metric: str,
    candidate: float,
    baseline: float,
    threshold: MetricThreshold,
) -> MetricCheck:
    delta = candidate - baseline
    reasons: list[str] = []

    # max_drop check (higher-is-better: candidate must not drop too much)
    if threshold.max_drop is not None:
        if delta < -abs(threshold.max_drop):
            reasons.append(
                f"dropped by {abs(delta):.4f}, threshold allows max {threshold.max_drop:.4f}"
            )

    # max_increase check (lower-is-better: candidate must not increase too much)
    if threshold.max_increase is not None:
        if delta > abs(threshold.max_increase):
            reasons.append(
                f"increased by {delta:.4f}, threshold allows max {threshold.max_increase:.4f}"
            )

    # Absolute floor
    if threshold.min_value is not None and candidate < threshold.min_value:
        reasons.append(f"value {candidate:.4f} < min_value {threshold.min_value:.4f}")

    # Absolute ceiling
    if threshold.max_value is not None and candidate > threshold.max_value:
        reasons.append(f"value {candidate:.4f} > max_value {threshold.max_value:.4f}")

    passed = len(reasons) == 0
    return MetricCheck(
        metric=metric,
        baseline=baseline,
        candidate=candidate,
        delta=delta,
        passed=passed,
        reason="; ".join(reasons) if reasons else "within threshold",
    )


def _extract_metrics(result: RunResult) -> dict[str, float]:
    r = result
    return {
        "recall_at_k":        r.retrieval.recall_at_k,
        "precision_at_k":     r.retrieval.precision_at_k,
        "mrr":                r.retrieval.mrr,
        "ndcg_at_k":          r.retrieval.ndcg_at_k,
        "faithfulness":       r.generation.faithfulness,
        "answer_relevancy":   r.generation.answer_relevancy,
        "context_precision":  r.generation.context_precision,
        "correctness":        r.generation.correctness,
        "hallucination_rate": r.generation.hallucination_rate,
        "avg_latency_ms":     r.avg_latency_ms,
        "total_cost_usd":     r.total_cost_usd,
    }
