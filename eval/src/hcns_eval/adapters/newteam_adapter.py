"""NewTeamAdapter — wraps the new-team LangGraph agent pipeline.

This is the ONLY eval module (besides baseline_adapter) that imports a concrete
pipeline. The harness depends solely on the PipelineAdapter Protocol.
"""
from __future__ import annotations

from pathlib import Path

from hcns_shared.config import BenchmarkConfig
from hcns_shared.types import Answer


class NewTeamAdapter:
    """Adapts LangGraphAgent to the PipelineAdapter Protocol (index/query).

    Params:
        config -- validated BenchmarkConfig with agent.type == "langgraph"
    """

    def __init__(self, config: BenchmarkConfig) -> None:
        from hcns_agents.graph import build_langgraph_from_config

        self._pipeline = build_langgraph_from_config(config)
        self.name = config.pipeline.name

    def index(self, corpus_dir: Path) -> None:
        self._pipeline.index(corpus_dir)

    def query(self, question: str) -> Answer:
        return self._pipeline.query(question)
