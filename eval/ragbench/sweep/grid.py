"""Grid generation and config override utilities.

generate_combinations() takes a dict of {param_path: [values]} and returns
the Cartesian product as a list of {param_path: value} dicts.

apply_overrides() deep-merges a flat dot-notation override dict into a
nested YAML-style dict.
"""
from __future__ import annotations

import copy
import itertools
from typing import Any


def generate_combinations(
    grid: dict[str, list[Any]],
    max_combinations: int | None = None,
) -> list[dict[str, Any]]:
    """Return the Cartesian product of all grid values.

    Params:
        grid             -- {dot.key: [values]} defining the parameter space
        max_combinations -- optional cap; raises ValueError if exceeded
    """
    if not grid:
        return [{}]
    keys = list(grid.keys())
    value_lists = list(grid.values())
    combos = [dict(zip(keys, combo)) for combo in itertools.product(*value_lists)]
    if max_combinations is not None and len(combos) > max_combinations:
        raise ValueError(
            f"Grid produces {len(combos)} combinations but max_combinations={max_combinations}. "
            "Reduce the grid or raise max_combinations."
        )
    return combos


def apply_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge *overrides* into *base* using dot-notation keys.

    Example:
        apply_overrides(
            {"pipeline": {"chunker": {"chunk_size": 512}}},
            {"pipeline.chunker.chunk_size": 100}
        )
        → {"pipeline": {"chunker": {"chunk_size": 100}}}
    """
    result = copy.deepcopy(base)
    for dot_key, value in overrides.items():
        _set_nested(result, dot_key.split("."), value)
    return result


def combo_name(params: dict[str, Any], max_len: int = 48) -> str:
    """Generate a short human-readable name for a parameter combination.

    Example: {"pipeline.chunker.chunk_size": 200, "pipeline.retriever.top_k": 3}
             → "chunk_size=200_top_k=3"
    """
    parts = []
    for key, val in sorted(params.items()):
        short_key = key.split(".")[-1]
        parts.append(f"{short_key}={val}")
    name = "_".join(parts)
    return name[:max_len]


# ── internal ────────────────────────────────────────────────────────────────────

def _set_nested(d: dict[str, Any], parts: list[str], value: Any) -> None:
    """Set d[parts[0]][parts[1]]...[parts[-1]] = value, creating dicts as needed."""
    for part in parts[:-1]:
        if part not in d or not isinstance(d[part], dict):
            d[part] = {}
        d = d[part]
    d[parts[-1]] = value
