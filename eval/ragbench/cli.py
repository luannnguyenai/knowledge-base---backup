"""RAGBench CLI — entry point for `ragbench` command.

Commands:
    ragbench index  --config <yaml> --corpus <dir>
    ragbench query  --config <yaml> <question>
    ragbench eval   --config <yaml>
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax

app = typer.Typer(name="ragbench", help="Pipeline-agnostic RAG benchmark tool.")
console = Console()

# Resolve paths relative to the CLI working directory
_CWD = Path.cwd()


def _resolve(p: Path) -> Path:
    return p if p.is_absolute() else _CWD / p


def _load(config_path: Path):
    """Load BenchmarkConfig and build the appropriate pipeline/agent."""
    from ragbench.core.config import BenchmarkConfig

    cfg = BenchmarkConfig.from_yaml(_resolve(config_path))
    pipeline = _build_from_config(cfg)
    return cfg, pipeline


def _build_from_config(cfg: "BenchmarkConfig"):  # type: ignore[name-defined]
    """Dispatch to StaticPipeline or LangGraphAgent based on agent.type."""
    if cfg.agent.type == "langgraph":
        from ragbench.pipelines.langgraph_agent import build_langgraph_from_config
        return build_langgraph_from_config(cfg)
    from ragbench.core.pipeline import build_pipeline_from_config
    return build_pipeline_from_config(cfg)


@app.command()
def index(
    config: Path = typer.Option(..., "--config", "-c", help="Path to benchmark YAML config"),
    corpus: Path = typer.Option(
        ..., "--corpus", "-d", help="Directory of documents to index"
    ),
) -> None:
    """Parse and index a corpus directory."""
    cfg, pipeline = _load(config)
    corpus_path = _resolve(corpus)
    console.print(f"[bold cyan]Indexing[/bold cyan] corpus: {corpus_path}")
    pipeline.index(corpus_path)
    console.print("[bold green]✓ Indexing complete.[/bold green]")


@app.command()
def query(
    question: str = typer.Argument(..., help="Question to answer"),
    config: Path = typer.Option(..., "--config", "-c", help="Path to benchmark YAML config"),
    corpus: Path = typer.Option(
        Path("data/corpus_smoke"),
        "--corpus",
        "-d",
        help="Corpus dir to index before querying",
    ),
) -> None:
    """Index corpus then answer a single question."""
    cfg, pipeline = _load(config)
    pipeline.index(_resolve(corpus))
    answer = pipeline.query(question)
    result: dict = {
        "query": answer.query,
        "answer": answer.text,
        "citations": answer.citations,
        "latency_ms": round(answer.latency_ms, 2),
    }
    if answer.trace:
        try:
            result["trace"] = json.loads(answer.trace)
        except (json.JSONDecodeError, TypeError):
            result["trace"] = answer.trace
    _print_json(result)


@app.command()
def eval(
    config: Path = typer.Option(..., "--config", "-c", help="Path to benchmark YAML config"),
    corpus: Path = typer.Option(
        Path("data/corpus_smoke"),
        "--corpus",
        "-d",
        help="Corpus dir to index before evaluating",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write JSON metrics report here"),
    save_result: Path | None = typer.Option(
        None, "--save-result", "-r",
        help="Also save full RunResult JSON here (for gate/compare later)"
    ),
) -> None:
    """Run full evaluation on the golden set."""
    from ragbench.core.config import BenchmarkConfig
    from ragbench.eval.golden_set import GoldenSet
    from ragbench.eval.harness import run_full_eval
    from ragbench.eval.judge import Judge

    cfg = BenchmarkConfig.from_yaml(_resolve(config))
    pipeline = _build_from_config(cfg)

    console.print(f"[bold cyan]Indexing[/bold cyan] corpus: {_resolve(corpus)}")
    pipeline.index(_resolve(corpus))

    golden_path = _resolve(cfg.eval.golden_set)
    golden = GoldenSet.from_json(golden_path)
    judge = Judge(
        model=cfg.eval.judge.model,
        temperature=cfg.eval.judge.temperature,
        api_key_env=cfg.eval.judge.api_key_env,
        cache_dir=str(_resolve(Path(cfg.eval.judge.cache_dir))),
        prompt_version=cfg.eval.judge.prompt_version,
        skip_on_missing_key=cfg.eval.judge.skip_on_missing_key,
    )
    console.print(
        f"[bold cyan]Evaluating[/bold cyan] pipeline=[bold]{cfg.pipeline.name}[/bold] "
        f"on {golden_path.name} (top_k={cfg.eval.top_k}, seed={cfg.eval.seed}, "
        f"judge={cfg.eval.judge.model})"
    )

    run = run_full_eval(
        pipeline=pipeline,
        golden_set=golden,
        judge=judge,
        config_path=_resolve(config),
        pipeline_name=cfg.pipeline.name,
        top_k=cfg.eval.top_k,
        seed=cfg.eval.seed,
    )

    report = {
        "pipeline": run.pipeline_name,
        "total_questions": run.retrieval.num_questions,
        "avg_latency_ms": round(run.avg_latency_ms, 2),
        "total_cost_usd": round(run.total_cost_usd, 6),
        "retrieval": {
            "recall_at_k":    round(run.retrieval.recall_at_k, 4),
            "precision_at_k": round(run.retrieval.precision_at_k, 4),
            "mrr":            round(run.retrieval.mrr, 4),
            "ndcg_at_k":      round(run.retrieval.ndcg_at_k, 4),
        },
        "generation": {
            "faithfulness":       round(run.generation.faithfulness, 4),
            "answer_relevancy":   round(run.generation.answer_relevancy, 4),
            "context_precision":  round(run.generation.context_precision, 4),
            "correctness":        round(run.generation.correctness, 4),
            "hallucination_rate": round(run.generation.hallucination_rate, 4),
        },
    }
    _print_json(report)

    out_dir = _resolve(cfg.eval.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = output or out_dir / f"{run.pipeline_name}_metrics.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[dim]Metrics saved → {report_file}[/dim]")

    if save_result:
        result_path = _resolve(save_result)
        run.save(result_path)
        console.print(f"[dim]Full result saved → {result_path}[/dim]")


@app.command()
def compare(
    configs: list[Path] = typer.Argument(
        ..., help="2+ benchmark YAML config files to compare (first = baseline)"
    ),
    corpus: Path = typer.Option(
        Path("data/corpus_smoke"), "--corpus", "-d", help="Corpus directory"
    ),
    output: Path = typer.Option(
        Path("reports/compare.md"), "--output", "-o", help="Output markdown path"
    ),
    result_files: list[Path] | None = typer.Option(
        None, "--result", "-r",
        help="Load pre-computed RunResult JSON instead of running eval",
    ),
    skip_generation_metrics: bool = typer.Option(
        False, "--skip-gen", help="Skip LLM judge (retrieval metrics only)"
    ),
) -> None:
    """Compare 2+ pipeline configs on the same golden set → reports/compare.md."""
    from ragbench.core.config import BenchmarkConfig
    from ragbench.eval.golden_set import GoldenSet
    from ragbench.eval.harness import run_full_eval
    from ragbench.eval.judge import Judge
    from ragbench.eval.report import CompareReport, compare_runs
    from ragbench.eval.harness import RunResult

    # -- Load pre-computed results or run fresh eval --
    if result_files:
        console.print("[bold cyan]Loading pre-computed results…[/bold cyan]")
        run_results = [RunResult.load(_resolve(rf)) for rf in result_files]
    else:
        if len(configs) < 2:
            console.print("[red]Error:[/red] provide at least 2 config files to compare.")
            raise typer.Exit(1)

        run_results = []
        for cfg_path in configs:
            cfg = BenchmarkConfig.from_yaml(_resolve(cfg_path))
            pipeline = _build_from_config(cfg)

            console.print(f"[bold cyan]Indexing[/bold cyan] {cfg.pipeline.name}…")
            pipeline.index(_resolve(corpus))

            golden_path = _resolve(cfg.eval.golden_set)
            golden = GoldenSet.from_json(golden_path)

            judge = Judge(
                model=cfg.eval.judge.model,
                temperature=cfg.eval.judge.temperature,
                api_key_env=cfg.eval.judge.api_key_env,
                cache_dir=str(_resolve(Path(cfg.eval.judge.cache_dir))),
                prompt_version=cfg.eval.judge.prompt_version,
                skip_on_missing_key=cfg.eval.judge.skip_on_missing_key
                or skip_generation_metrics,
            )

            console.print(
                f"[bold cyan]Evaluating[/bold cyan] [bold]{cfg.pipeline.name}[/bold] "
                f"({len(golden)} questions, judge={cfg.eval.judge.model})"
            )
            result = run_full_eval(
                pipeline=pipeline,
                golden_set=golden,
                judge=judge,
                config_path=_resolve(cfg_path),
                pipeline_name=cfg.pipeline.name,
                top_k=cfg.eval.top_k,
                seed=cfg.eval.seed,
            )
            # Auto-save result JSON
            out_dir = _resolve(cfg.eval.output_dir)
            result_path = out_dir / f"{cfg.pipeline.name}_result.json"
            result.save(result_path)
            console.print(f"[dim]Result saved → {result_path}[/dim]")
            run_results.append(result)

    # -- Generate comparison report --
    report: CompareReport = compare_runs(run_results)
    output_path = _resolve(output)
    report.save_markdown(output_path)
    json_path = output_path.with_suffix(".json")
    report.save_json(json_path)

    console.print(f"\n[bold green]✓ Comparison report saved:[/bold green]")
    console.print(f"  Markdown → [link={output_path}]{output_path}[/link]")
    console.print(f"  JSON     → [link={json_path}]{json_path}[/link]")

    # Print win summary to console
    summary_rows = [
        f"  [bold]{name}[/bold]: {report.wins[name]} wins, "
        f"{report.losses[name]} losses, {report.ties[name]} ties"
        for name in report.pipeline_names
    ]
    console.print("\n[bold]Win/Loss Summary:[/bold]")
    for row in summary_rows:
        console.print(row)


@app.command()
def sweep(
    sweep_config: Path = typer.Argument(..., help="Path to sweep YAML config"),
) -> None:
    """Run a hyperparameter sweep and output a ranked ablation report."""
    from ragbench.sweep.config import SweepConfig
    from ragbench.sweep.runner import run_sweep
    from ragbench.sweep.report import save_sweep_reports

    cfg = SweepConfig.from_yaml(_resolve(sweep_config))
    out_dir = cfg.output_dir / cfg.name
    total = 1
    for vals in cfg.grid.values():
        total *= len(vals)
    console.print(
        f"[bold cyan]Sweep:[/bold cyan] {cfg.name} — "
        f"{total} combinations (optimize: {cfg.optimize_metric} {cfg.optimize_direction})"
    )

    def _progress(idx: int, total: int, name: str) -> None:
        console.print(f"  [{idx + 1}/{total}] {name}")

    result = run_sweep(cfg, progress_callback=_progress)
    paths = save_sweep_reports(result, out_dir)

    console.print(f"\n[bold green]✓ Sweep complete:[/bold green] {result.successful_combinations}/{result.total_combinations} runs succeeded")
    if result.best:
        best_score = result.best.metric.get(cfg.optimize_metric, 0)
        console.print(f"[bold]Best {cfg.optimize_metric}:[/bold] {best_score:.4f} → {result.best.name}")
    for label, path in paths.items():
        console.print(f"  {label}: {path}")


@app.command()
def gate(
    new: Path = typer.Option(..., "--new", "-n", help="Path to candidate RunResult JSON"),
    baseline: Path | None = typer.Option(None, "--baseline", "-b", help="Path to baseline RunResult JSON"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to gate.yaml config"),
) -> None:
    """Regression gate — fail (exit 1) if metrics drop beyond threshold.

    If --baseline is not supplied, the path from gate.yaml is used.
    """
    import sys
    from ragbench.eval.harness import RunResult
    from ragbench.sweep.config import GateConfig, MetricThreshold
    from ragbench.sweep.gate import check_gate

    # Load gate config (or use defaults)
    if config:
        gate_cfg = GateConfig.from_yaml(_resolve(config))
    else:
        gate_cfg = GateConfig(baseline=Path("reports/baseline_result.json"))

    # Allow --baseline to override gate config's baseline path
    baseline_path = _resolve(baseline) if baseline else _resolve(gate_cfg.baseline)
    if not baseline_path.exists():
        console.print(f"[red]Error:[/red] baseline result not found: {baseline_path}")
        raise typer.Exit(1)

    candidate = RunResult.load(_resolve(new))
    base = RunResult.load(baseline_path)

    result = check_gate(candidate, base, gate_cfg)

    # Print per-metric report
    for check in result.checks:
        icon = "[green]✓[/green]" if check.passed else "[red]✗[/red]"
        console.print(
            f"  {icon} [bold]{check.metric:30s}[/bold]  "
            f"candidate={check.candidate:.4f}  baseline={check.baseline:.4f}  "
            f"Δ={check.delta:+.4f}  "
            + ("[green]PASS[/green]" if check.passed else f"[red]FAIL[/red] — {check.reason}")
        )

    console.print()
    if result.passed:
        console.print("[bold green]✓ Gate PASSED[/bold green]")
    else:
        n_fail = len(result.failed_checks)
        console.print(f"[bold red]✗ Gate FAILED[/bold red] ({n_fail} metric(s) out of threshold)")

    raise typer.Exit(result.exit_code())


def _print_json(data: dict) -> None:
    rendered = json.dumps(data, ensure_ascii=False, indent=2)
    console.print(Syntax(rendered, "json", theme="monokai", background_color="default"))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
