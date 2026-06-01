"""Sweep report formatters — ranking table + per-dimension ablation analysis."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ragbench.sweep.runner import SweepResult, ComboResult

# Metrics shown in the ranking table (ordered)
_DISPLAY_METRICS: list[tuple[str, str]] = [
    ("recall_at_k",       "Recall@k"),
    ("precision_at_k",    "Precision@k"),
    ("mrr",               "MRR"),
    ("ndcg_at_k",         "NDCG@k"),
    ("faithfulness",      "Faithfulness"),
    ("answer_relevancy",  "Ans.Relevancy"),
    ("correctness",       "Correctness"),
    ("hallucination_rate","Hallucination↓"),
    ("avg_latency_ms",    "Latency(ms)↓"),
]


# ── Ranking report ─────────────────────────────────────────────────────────────

def format_ranking_markdown(result: SweepResult) -> str:
    """Format a ranked table of all sweep combinations as Markdown."""
    lines: list[str] = [
        f"# Sweep: {result.name}",
        "",
        f"**Optimize:** `{result.optimize_metric}` ({result.optimize_direction})  ",
        f"**Combinations:** {result.successful_combinations}/{result.total_combinations} succeeded  ",
        f"**Duration:** {result.duration_s:.1f}s  ",
        "",
    ]

    if result.best:
        lines += [
            "## Best Configuration",
            "",
            f"**Score ({result.optimize_metric}):** "
            f"`{result.best.metric.get(result.optimize_metric, 0):.4f}`",
            "",
            "```yaml",
        ]
        for k, v in sorted(result.best.params.items()):
            lines.append(f"{k}: {v}")
        lines += ["```", ""]

    # Ranking table
    success_combos = [c for c in result.combos if c.run_result is not None]
    if not success_combos:
        lines.append("*No successful combinations to display.*")
        return "\n".join(lines)

    # Determine which params vary across combos
    all_params = sorted({k for c in success_combos for k in c.params})

    # Header
    param_headers = [k.split(".")[-1] for k in all_params]
    metric_headers = [disp for _, disp in _DISPLAY_METRICS]
    header_cols = ["Rank"] + param_headers + metric_headers
    lines += [
        "## Ranking",
        "",
        "| " + " | ".join(header_cols) + " |",
        "| " + " | ".join(["---"] * len(header_cols)) + " |",
    ]

    for c in success_combos:
        param_vals = [str(c.params.get(k, "—")) for k in all_params]
        metric_vals = [f"{c.metric.get(k, 0):.4f}" for k, _ in _DISPLAY_METRICS]
        lines.append("| " + " | ".join([str(c.rank)] + param_vals + metric_vals) + " |")

    # Failed combos
    failed = [c for c in result.combos if c.run_result is None]
    if failed:
        lines += ["", "### Failed Combinations", ""]
        for c in failed:
            lines.append(f"- `{c.name}` — {c.error or 'unknown error'}")

    return "\n".join(lines)


# ── Ablation report ────────────────────────────────────────────────────────────

def format_ablation_markdown(result: SweepResult) -> str:
    """Per-dimension ablation analysis.

    For each swept parameter, shows average metric value when that parameter
    takes each of its possible values — holding all other params constant
    (macro-average approach).
    """
    lines: list[str] = [
        f"# Ablation: {result.name}",
        "",
        f"**Target metric:** `{result.optimize_metric}` ({result.optimize_direction})",
        "",
    ]

    success_combos = [c for c in result.combos if c.run_result is not None]
    if not success_combos:
        lines.append("*No data available.*")
        return "\n".join(lines)

    all_params = sorted({k for c in success_combos for k in c.params})
    target = result.optimize_metric

    for param in all_params:
        short_name = param.split(".")[-1]
        lines += [f"## `{short_name}` (`{param}`)", ""]

        # Group combos by param value
        by_value: dict[Any, list[float]] = defaultdict(list)
        for c in success_combos:
            val = c.params.get(param)
            score = c.metric.get(target, 0.0)
            if val is not None:
                by_value[val].append(score)

        # Sort values
        try:
            sorted_vals = sorted(by_value.keys())
        except TypeError:
            sorted_vals = list(by_value.keys())

        lines += [
            f"| Value | Avg `{target}` | Δ vs first |",
            "| --- | --- | --- |",
        ]
        first_avg: float | None = None
        for val in sorted_vals:
            scores = by_value[val]
            avg = sum(scores) / len(scores)
            if first_avg is None:
                first_avg = avg
                delta_str = "—"
            else:
                delta = avg - first_avg
                sign = "+" if delta >= 0 else ""
                delta_str = f"{sign}{delta:.4f}"
            lines.append(f"| `{val}` | {avg:.4f} | {delta_str} |")
        lines.append("")

    return "\n".join(lines)


def save_sweep_reports(result: SweepResult, output_dir: Path) -> dict[str, Path]:
    """Save ranking.md, ablation.md, and ranking.json to *output_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    ranking_md = output_dir / "ranking.md"
    ranking_md.write_text(format_ranking_markdown(result), encoding="utf-8")
    paths["ranking_md"] = ranking_md

    ablation_md = output_dir / "ablation.md"
    ablation_md.write_text(format_ablation_markdown(result), encoding="utf-8")
    paths["ablation_md"] = ablation_md

    ranking_json = output_dir / "ranking.json"
    result.save(ranking_json)
    paths["ranking_json"] = ranking_json

    # Save best result separately for gate usage
    if result.best and result.best.run_result:
        best_path = output_dir / "best_result.json"
        result.best.run_result.save(best_path)
        paths["best_result"] = best_path

    return paths
