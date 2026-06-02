"""hcns_agents — orchestration for the HC-NS KB pipelines.

Contains:
    generators/  -- FakeGenerator, GeminiGenerator, RoutedGenerator (route & generate)
    prompts/     -- prompt templates (.md), loaded via load_prompt()
    pipelines/   -- StaticPipeline (baseline) + build_pipeline_from_config
    graph/       -- LangGraphAgent state graph + build_langgraph_from_config

Importing this package registers all generators via @register.
"""
from hcns_agents import generators  # noqa: F401  (side-effect: @register generators)
from hcns_agents.graph import LangGraphAgent, build_langgraph_from_config
from hcns_agents.pipelines import StaticPipeline, build_pipeline_from_config

__all__ = [
    "StaticPipeline",
    "build_pipeline_from_config",
    "LangGraphAgent",
    "build_langgraph_from_config",
]
