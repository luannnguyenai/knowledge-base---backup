"""Pipeline orchestration: the baseline StaticPipeline and its factory."""
from hcns_agents.pipelines.static_pipeline import (
    StaticPipeline,
    build_pipeline_from_config,
)

__all__ = ["StaticPipeline", "build_pipeline_from_config"]
