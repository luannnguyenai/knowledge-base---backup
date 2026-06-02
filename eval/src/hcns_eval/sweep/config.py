"""Sweep and gate configuration models (Pydantic-validated)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


class SweepConfig(BaseModel):
    """Configuration for a hyperparameter sweep.

    Grid values use dot-notation to address nested BenchmarkConfig fields.
    Example: "pipeline.chunker.chunk_size": [100, 200, 400]

    Params:
        name              -- human label for this sweep
        base_config       -- path to the BenchmarkConfig YAML to extend
        corpus            -- corpus directory for every run
        grid              -- {dot.key: [values]} defining the parameter space
        output_dir        -- where ranking + ablation reports are written
        optimize_metric   -- flat metric name to optimise (e.g. "recall_at_k")
        optimize_direction -- "maximize" or "minimize" (default: "maximize")
        max_combinations  -- cap on grid size; None = no cap (default: None)
        eval_overrides    -- flat dict of eval/judge settings to merge per run
                             (e.g. {"eval.judge.skip_on_missing_key": true})
    """

    name: str
    base_config: Path
    corpus: Path
    grid: dict[str, list[Any]]
    output_dir: Path = Path("reports/sweeps")
    optimize_metric: str = "recall_at_k"
    optimize_direction: str = "maximize"
    max_combinations: int | None = None
    eval_overrides: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_direction(self) -> "SweepConfig":
        if self.optimize_direction not in ("maximize", "minimize"):
            raise ValueError(
                f"optimize_direction must be 'maximize' or 'minimize', "
                f"got '{self.optimize_direction}'"
            )
        return self

    @classmethod
    def from_yaml(cls, path: Path) -> "SweepConfig":
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        # Resolve paths relative to the YAML file's directory
        base = path.parent
        if "base_config" in raw:
            raw["base_config"] = str((base / raw["base_config"]).resolve())
        if "corpus" in raw:
            raw["corpus"] = str((base / raw["corpus"]).resolve())
        if "output_dir" in raw:
            raw["output_dir"] = str((base / raw["output_dir"]).resolve())
        return cls.model_validate(raw)


class MetricThreshold(BaseModel):
    """Threshold for a single metric in the regression gate.

    Exactly one of max_drop or max_increase must be set.

    Params:
        max_drop     -- maximum allowed absolute drop (for higher-is-better metrics)
        max_increase -- maximum allowed absolute increase (for lower-is-better metrics)
        min_value    -- absolute floor; fails if result < this (optional)
        max_value    -- absolute ceiling; fails if result > this (optional)
    """

    max_drop: float | None = None       # positive number = allowed drop amount
    max_increase: float | None = None   # positive number = allowed increase amount
    min_value: float | None = None
    max_value: float | None = None


class GateConfig(BaseModel):
    """Regression gate configuration.

    Params:
        baseline   -- path to the baseline RunResult JSON
        thresholds -- {metric_name: MetricThreshold}; unlisted metrics are ignored
    """

    baseline: Path
    thresholds: dict[str, MetricThreshold] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> "GateConfig":
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        base = path.parent
        if "baseline" in raw:
            raw["baseline"] = str((base / raw["baseline"]).resolve())
        # Allow shorthand: {"recall_at_k": 0.05} → max_drop: 0.05
        if "thresholds" in raw:
            expanded: dict[str, Any] = {}
            for k, v in raw["thresholds"].items():
                if isinstance(v, (int, float)):
                    expanded[k] = {"max_drop": float(v)}
                else:
                    expanded[k] = v
            raw["thresholds"] = expanded
        return cls.model_validate(raw)
