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
    """Load BenchmarkConfig and build StaticPipeline."""
    from ragbench.core.config import BenchmarkConfig
    from ragbench.core.pipeline import build_pipeline_from_config

    cfg = BenchmarkConfig.from_yaml(_resolve(config_path))
    pipeline = build_pipeline_from_config(cfg)
    return cfg, pipeline


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
    result = {
        "query": answer.query,
        "answer": answer.text,
        "citations": answer.citations,
        "latency_ms": round(answer.latency_ms, 2),
    }
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
    output: Path | None = typer.Option(None, "--output", "-o", help="Write JSON report here"),
) -> None:
    """Run full evaluation on the golden set."""
    from ragbench.core.config import BenchmarkConfig
    from ragbench.core.pipeline import build_pipeline_from_config
    from ragbench.harness import run_eval

    cfg = BenchmarkConfig.from_yaml(_resolve(config))
    pipeline = build_pipeline_from_config(cfg)

    console.print(f"[bold cyan]Indexing[/bold cyan] corpus: {_resolve(corpus)}")
    pipeline.index(_resolve(corpus))

    golden_path = _resolve(cfg.eval.golden_set)
    console.print(
        f"[bold cyan]Evaluating[/bold cyan] pipeline=[bold]{cfg.pipeline.name}[/bold] "
        f"on {golden_path.name} (top_k={cfg.eval.top_k}, seed={cfg.eval.seed})"
    )

    run = run_eval(
        pipeline=pipeline,
        golden_path=golden_path,
        top_k=cfg.eval.top_k,
        seed=cfg.eval.seed,
        pipeline_name=cfg.pipeline.name,
    )

    report = {
        "pipeline": run.pipeline_name,
        "total_questions": run.total_questions,
        "avg_latency_ms": round(run.avg_latency_ms, 2),
        "retrieval": {
            "recall_at_k": round(run.retrieval.recall_at_k, 4),
            "context_precision": round(run.retrieval.context_precision, 4),
            "mrr": round(run.retrieval.mrr, 4),
            "ndcg_at_k": round(run.retrieval.ndcg_at_k, 4),
        },
        "generation": {
            "answer_relevancy": round(run.generation.answer_relevancy, 4),
            "faithfulness": round(run.generation.faithfulness, 4),
        },
    }
    _print_json(report)

    # Persist report
    out_dir = _resolve(cfg.eval.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = output or out_dir / f"{run.pipeline_name}_metrics.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[dim]Report saved → {report_file}[/dim]")


def _print_json(data: dict) -> None:
    rendered = json.dumps(data, ensure_ascii=False, indent=2)
    console.print(Syntax(rendered, "json", theme="monokai", background_color="default"))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
