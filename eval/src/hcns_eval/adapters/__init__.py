"""Adapter layer — the boundary between eval and concrete pipelines.

build_adapter() dispatches on agent.type to return the right PipelineAdapter,
so the harness/CLI never needs to know which pipeline implementation runs.
"""
from __future__ import annotations

from hcns_shared.config import BenchmarkConfig
from hcns_shared.interfaces import PipelineAdapter

from hcns_eval.adapters.baseline_adapter import BaselineAdapter
from hcns_eval.adapters.newteam_adapter import NewTeamAdapter


def build_adapter(config: BenchmarkConfig) -> PipelineAdapter:
    """Return a PipelineAdapter for *config*, dispatching on agent.type.

    agent.type == "langgraph" → NewTeamAdapter (LangGraphAgent)
    otherwise                 → BaselineAdapter (StaticPipeline)
    """
    if config.agent.type == "langgraph":
        return NewTeamAdapter(config)
    return BaselineAdapter(config)


__all__ = ["BaselineAdapter", "NewTeamAdapter", "build_adapter"]
