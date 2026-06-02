"""Sweep runner — executes all grid combinations and collects RunResults."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml

from ragbench.eval.golden_set import GoldenSet
from ragbench.eval.harness import RunResult, run_full_eval
from ragbench.eval.judge import Judge
from ragbench.sweep.config import SweepConfig
from ragbench.sweep.grid import apply_overrides, combo_name, generate_combinations


@dataclass
class ComboResult:
    """Result for a single grid combination."""
    rank: int                   # set after sorting
    params: dict[str, Any]      # the override params for this combo
    name: str                   # human-readable combo label
    run_result: RunResult | None
    error: str | None = None    # set if the run failed

    @property
    def metric(self) -> dict[str, float]:
        """Flat metrics dict for reporting."""
        if self.run_result is None:
            return {}
        r = self.run_result
        return {
            "recall_at_k":       r.retrieval.recall_at_k,
            "precision_at_k":    r.retrieval.precision_at_k,
            "mrr":               r.retrieval.mrr,
            "ndcg_at_k":         r.retrieval.ndcg_at_k,
            "faithfulness":      r.generation.faithfulness,
            "answer_relevancy":  r.generation.answer_relevancy,
            "context_precision": r.generation.context_precision,
            "correctness":       r.generation.correctness,
            "hallucination_rate":r.generation.hallucination_rate,
            "avg_latency_ms":    r.run_result.avg_latency_ms if False else r.avg_latency_ms,
            "total_cost_usd":    r.total_cost_usd,
        }


@dataclass
class SweepResult:
    """All outputs of a completed sweep."""
    name: str
    optimize_metric: str
    optimize_direction: str
    total_combinations: int
    successful_combinations: int
    combos: list[ComboResult]
    duration_s: float

    @property
    def best(self) -> ComboResult | None:
        ranked = [c for c in self.combos if c.run_result is not None]
        return ranked[0] if ranked else None

    def to_dict(self) -> dict[str, Any]:
        combos_dicts = []
        for c in self.combos:
            d: dict[str, Any] = {
                "rank": c.rank,
                "name": c.name,
                "params": c.params,
                "metrics": c.metric,
            }
            if c.error:
                d["error"] = c.error
            combos_dicts.append(d)
        return {
            "name": self.name,
            "optimize_metric": self.optimize_metric,
            "optimize_direction": self.optimize_direction,
            "total_combinations": self.total_combinations,
            "successful_combinations": self.successful_combinations,
            "duration_s": round(self.duration_s, 2),
            "best": {"params": self.best.params, "metrics": self.best.metric} if self.best else None,
            "ranking": combos_dicts,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))


def run_sweep(
    sweep_cfg: SweepConfig,
    progress_callback=None,   # optional callable(combo_idx, total, name)
) -> SweepResult:
    """Execute all grid combinations and return a ranked SweepResult.

    Each combination:
    1. Merges its overrides into the base config YAML
    2. Builds the pipeline via the registry
    3. Indexes the corpus
    4. Runs full eval (with judge caching for reproducibility)
    5. Saves individual RunResult JSON to output_dir/results/

    Params:
        sweep_cfg         -- validated SweepConfig
        progress_callback -- optional fn(combo_idx: int, total: int, name: str)
    """
    from ragbench.cli import _build_from_config as _build  # late import to avoid circular
    from ragbench.core.config import BenchmarkConfig

    base_yaml = yaml.safe_load(
        sweep_cfg.base_config.read_text(encoding="utf-8")
    )

    # Apply eval overrides to the base YAML template once
    base_with_eval_overrides = apply_overrides(base_yaml, sweep_cfg.eval_overrides)

    combos = generate_combinations(sweep_cfg.grid, sweep_cfg.max_combinations)
    total = len(combos)
    results_dir = sweep_cfg.output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    combo_results: list[ComboResult] = []
    t_start = time.perf_counter()

    for idx, params in enumerate(combos):
        name = combo_name(params)
        if progress_callback:
            progress_callback(idx, total, name)

        try:
            # Build per-combo config dict and parse
            merged = apply_overrides(base_with_eval_overrides, params)
            # Inject a unique pipeline name so results don't overwrite each other
            combo_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
            merged.setdefault("pipeline", {})["name"] = f"combo_{combo_hash}"

            cfg = BenchmarkConfig.model_validate(merged)
            pipeline = _build(cfg)
            pipeline.index(sweep_cfg.corpus)

            golden = GoldenSet.from_json(
                _resolve_golden(cfg.eval.golden_set, sweep_cfg.base_config.parent)
            )
            judge = Judge(
                model=cfg.eval.judge.model,
                temperature=cfg.eval.judge.temperature,
                api_key_env=cfg.eval.judge.api_key_env,
                cache_dir=str(_resolve_path(cfg.eval.judge.cache_dir, sweep_cfg.base_config.parent)),
                prompt_version=cfg.eval.judge.prompt_version,
                skip_on_missing_key=cfg.eval.judge.skip_on_missing_key,
            )
            run_result = run_full_eval(
                pipeline=pipeline,
                golden_set=golden,
                judge=judge,
                config_path=sweep_cfg.base_config,
                pipeline_name=f"combo_{combo_hash}",
                top_k=cfg.eval.top_k,
                seed=cfg.eval.seed,
            )
            # Save individual result
            run_result.save(results_dir / f"{name}.json")
            combo_results.append(ComboResult(rank=0, params=params, name=name, run_result=run_result))

        except Exception as exc:
            combo_results.append(ComboResult(rank=0, params=params, name=name, run_result=None, error=str(exc)))

    # Sort by optimize_metric
    direction = sweep_cfg.optimize_direction
    def _sort_key(c: ComboResult) -> float:
        val = c.metric.get(sweep_cfg.optimize_metric, 0.0)
        return val if direction == "maximize" else -val

    ranked = sorted([c for c in combo_results if c.run_result is not None],
                    key=_sort_key, reverse=True)
    failed = [c for c in combo_results if c.run_result is None]

    for rank, c in enumerate(ranked, start=1):
        c.rank = rank
    for c in failed:
        c.rank = len(ranked) + 1

    return SweepResult(
        name=sweep_cfg.name,
        optimize_metric=sweep_cfg.optimize_metric,
        optimize_direction=sweep_cfg.optimize_direction,
        total_combinations=total,
        successful_combinations=len(ranked),
        combos=ranked + failed,
        duration_s=time.perf_counter() - t_start,
    )


def _resolve_golden(golden_path: Path, base_dir: Path) -> Path:
    if golden_path.is_absolute():
        return golden_path
    resolved = base_dir / golden_path
    if resolved.exists():
        return resolved
    return golden_path


def _resolve_path(p: str | Path, base_dir: Path) -> Path:
    p = Path(p)
    if p.is_absolute():
        return p
    resolved = base_dir / p
    return resolved
