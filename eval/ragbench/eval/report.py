"""Comparison report — compare 2+ RunResults and produce markdown + JSON.

Design:
- Higher = better for all metrics except hallucination_rate and latency.
- Delta = challenger value − baseline value (first result = baseline).
- Winner column shows 🏆 {name} or "tie" (|delta| ≤ TIE_EPSILON).
- Win/loss counts are per-metric, not per-question.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ragbench.eval.harness import RunResult

TIE_EPSILON = 1e-4   # absolute difference below which scores are considered tied

# Metrics where lower is better
_LOWER_IS_BETTER = {"hallucination_rate", "avg_latency_ms", "total_cost_usd"}

# Ordered display groups for the markdown table
_METRIC_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Retrieval", [
        ("recall_at_k",    "Recall@k"),
        ("precision_at_k", "Precision@k"),
        ("mrr",            "MRR"),
        ("ndcg_at_k",      "NDCG@k"),
    ]),
    ("Generation (LLM-judged)", [
        ("faithfulness",      "Faithfulness"),
        ("answer_relevancy",  "Answer Relevancy"),
        ("context_precision", "Context Precision"),
        ("correctness",       "Correctness"),
        ("hallucination_rate","Hallucination Rate ↓"),
    ]),
    ("Efficiency", [
        ("avg_latency_ms",  "Avg Latency (ms) ↓"),
        ("total_cost_usd",  "Total Cost (USD) ↓"),
    ]),
]


@dataclass
class MetricComparison:
    metric_key: str
    display_name: str
    values: dict[str, float]   # pipeline_name → score
    deltas: dict[str, float]   # pipeline_name → delta vs baseline
    winner: str                # pipeline name or "tie"


@dataclass
class CompareReport:
    generated_at: str
    pipeline_names: list[str]
    golden_set_version: str
    total_questions: int
    comparisons: list[MetricComparison]
    wins: dict[str, int]       # pipeline_name → win count
    losses: dict[str, int]
    ties: dict[str, int]
    manifests: dict[str, dict]  # pipeline_name → manifest dict

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "pipeline_names": self.pipeline_names,
            "golden_set_version": self.golden_set_version,
            "total_questions": self.total_questions,
            "metrics": {
                c.metric_key: {
                    "display_name": c.display_name,
                    **{n: round(v, 6) for n, v in c.values.items()},
                    "deltas": {n: round(d, 6) for n, d in c.deltas.items()},
                    "winner": c.winner,
                }
                for c in self.comparisons
            },
            "summary": {
                "wins":   self.wins,
                "losses": self.losses,
                "ties":   self.ties,
            },
            "manifests": self.manifests,
        }

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))

    def save_markdown(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")

    def to_markdown(self) -> str:
        return _render_markdown(self)


# ── Compare entry point ───────────────────────────────────────────────────────

def compare_runs(results: list[RunResult]) -> CompareReport:
    """Build a CompareReport from 2 or more RunResults.

    The first result is treated as the baseline; all deltas are computed
    relative to it.
    """
    if len(results) < 2:
        raise ValueError("compare_runs requires at least 2 RunResult objects.")

    names = [r.pipeline_name for r in results]
    baseline = results[0]

    # Flatten all metric values into dicts
    all_values: dict[str, dict[str, float]] = _extract_metrics(results)

    comparisons: list[MetricComparison] = []
    wins:   dict[str, int] = {n: 0 for n in names}
    losses: dict[str, int] = {n: 0 for n in names}
    ties:   dict[str, int] = {n: 0 for n in names}

    for _, metrics in _METRIC_GROUPS:
        for key, display in metrics:
            if key not in all_values:
                continue
            values = all_values[key]
            base_val = values[names[0]]

            deltas = {n: (v - base_val) for n, v in values.items()}
            winner = _find_winner(values, key)

            comparisons.append(MetricComparison(
                metric_key=key,
                display_name=display,
                values=values,
                deltas=deltas,
                winner=winner,
            ))

            # Tally wins/losses per-metric
            for name in names:
                if winner == "tie":
                    ties[name] += 1
                elif winner == name:
                    wins[name] += 1
                else:
                    losses[name] += 1

    return CompareReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        pipeline_names=names,
        golden_set_version=baseline.manifest.data_version,
        total_questions=baseline.retrieval.num_questions,
        comparisons=comparisons,
        wins=wins,
        losses=losses,
        ties=ties,
        manifests={r.pipeline_name: r.manifest.to_dict() for r in results},
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_metrics(results: list[RunResult]) -> dict[str, dict[str, float]]:
    """Build {metric_key: {pipeline_name: value}} from a list of RunResults."""
    out: dict[str, dict[str, float]] = {}

    def _set(key: str, name: str, value: float) -> None:
        out.setdefault(key, {})[name] = value

    for r in results:
        n = r.pipeline_name
        _set("recall_at_k",        n, r.retrieval.recall_at_k)
        _set("precision_at_k",     n, r.retrieval.precision_at_k)
        _set("mrr",                n, r.retrieval.mrr)
        _set("ndcg_at_k",          n, r.retrieval.ndcg_at_k)
        _set("faithfulness",       n, r.generation.faithfulness)
        _set("answer_relevancy",   n, r.generation.answer_relevancy)
        _set("context_precision",  n, r.generation.context_precision)
        _set("correctness",        n, r.generation.correctness)
        _set("hallucination_rate", n, r.generation.hallucination_rate)
        _set("avg_latency_ms",     n, r.avg_latency_ms)
        _set("total_cost_usd",     n, r.total_cost_usd)
    return out


def _find_winner(values: dict[str, float], metric_key: str) -> str:
    lower_better = metric_key in _LOWER_IS_BETTER
    names = list(values.keys())
    scores = list(values.values())

    best_val = min(scores) if lower_better else max(scores)
    tied = all(abs(v - best_val) <= TIE_EPSILON for v in scores)
    if tied:
        return "tie"

    for name, val in values.items():
        if abs(val - best_val) <= TIE_EPSILON:
            return name
    return names[0]


# ── Markdown renderer ──────────────────────────────────────────────────────────

def _render_markdown(report: CompareReport) -> str:
    lines: list[str] = []
    names = report.pipeline_names

    lines += [
        "# RAGBench Comparison Report",
        "",
        f"**Generated:** {report.generated_at}  ",
        f"**Golden Set Version:** {report.golden_set_version}  ",
        f"**Questions:** {report.total_questions}  ",
        f"**Pipelines:** {', '.join(f'`{n}`' for n in names)}  ",
        "",
        "---",
        "",
        "## Metrics",
        "",
    ]

    # Header row
    header_cols = ["Metric"] + names + (["Delta"] if len(names) == 2 else []) + ["Winner"]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")

    comparisons_by_key = {c.metric_key: c for c in report.comparisons}

    for group_name, metrics in _METRIC_GROUPS:
        group_rows = [m for key, _ in metrics if (m := comparisons_by_key.get(key))]
        if not group_rows:
            continue
        # Group separator row (bold label)
        lines.append(f"| **{group_name}** | " + " | ".join([""] * (len(header_cols) - 1)) + " |")
        for c in group_rows:
            row = [f"`{c.display_name}`"]
            for name in names:
                row.append(f"{c.values.get(name, 0):.4f}")
            if len(names) == 2:
                delta = c.deltas.get(names[1], 0)
                sign = "+" if delta >= 0 else ""
                row.append(f"{sign}{delta:.4f}")
            winner_cell = f"🏆 {c.winner}" if c.winner != "tie" else "tie"
            row.append(winner_cell)
            lines.append("| " + " | ".join(row) + " |")

    lines += [
        "",
        "---",
        "",
        "## Win / Loss Summary",
        "",
        "| Pipeline | Wins | Losses | Ties |",
        "| --- | --- | --- | --- |",
    ]
    for name in names:
        lines.append(
            f"| `{name}` | {report.wins[name]} | {report.losses[name]} | {report.ties[name]} |"
        )

    lines += ["", "---", "", "## Run Manifests", ""]
    for name in names:
        m = report.manifests.get(name, {})
        lines += [
            f"### `{name}`",
            "",
            f"- **Config hash:** `{m.get('config_hash', 'n/a')}`",
            f"- **Git SHA:** `{m.get('git_sha', 'n/a')}`",
            f"- **Data version:** `{m.get('data_version', 'n/a')}`",
            f"- **Data hash:** `{m.get('data_hash', 'n/a')}`",
            f"- **Judge model:** `{m.get('judge_model', 'n/a')}`",
            f"- **Judge prompt version:** `{m.get('judge_prompt_version', 'n/a')}`",
            f"- **RAGBench version:** `{m.get('ragbench_version', 'n/a')}`",
            f"- **Timestamp:** `{m.get('timestamp', 'n/a')}`",
            "",
        ]

    return "\n".join(lines)
