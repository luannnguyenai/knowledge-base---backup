"""Pydantic-based configuration models.

All pipeline parameters live in YAML and are validated here.
Hardcoding ANY tunable value elsewhere is forbidden.

Example YAML:
    pipeline:
      name: smoke_baseline
      parser:   {name: echo}
      chunker:  {name: fixed, chunk_size: 256, overlap: 32}
      embedder: {name: hash, dim: 128}
      vector_store: {name: inmemory}
      retriever: {name: dense, top_k: 3}
      reranker:  {name: noop}
      generator: {name: fake}
    eval:
      golden_set: data/golden/mini_v1.json
      top_k: 3
      seed: 42
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


class ComponentSpec(BaseModel):
    """Spec for a single component — name + arbitrary kwargs."""

    model_config = {"extra": "allow"}

    name: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class PipelineConfig(BaseModel):
    """Full pipeline wiring configuration.

    Params:
        name        -- human-readable run label (default: "unnamed")
        parser      -- Parser spec (default: {name: echo})
        chunker     -- Chunker spec (default: {name: fixed, chunk_size: 512, overlap: 64})
        embedder    -- Embedder spec (default: {name: hash, dim: 128})
        vector_store -- VectorStore spec (default: {name: inmemory})
        retriever   -- Retriever spec (default: {name: dense, top_k: 5})
        reranker    -- Reranker spec (default: {name: noop})
        generator   -- Generator spec (default: {name: fake})
    """

    name: str = "unnamed"
    parser: ComponentSpec = Field(default_factory=lambda: ComponentSpec(name="echo"))
    chunker: ComponentSpec = Field(
        default_factory=lambda: ComponentSpec(name="fixed", chunk_size=512, overlap=64)  # type: ignore[call-arg]
    )
    embedder: ComponentSpec = Field(
        default_factory=lambda: ComponentSpec(name="hash", dim=128)  # type: ignore[call-arg]
    )
    vector_store: ComponentSpec = Field(
        default_factory=lambda: ComponentSpec(name="inmemory")
    )
    retriever: ComponentSpec = Field(
        default_factory=lambda: ComponentSpec(name="dense", top_k=5)  # type: ignore[call-arg]
    )
    reranker: ComponentSpec = Field(
        default_factory=lambda: ComponentSpec(name="noop")
    )
    generator: ComponentSpec = Field(
        default_factory=lambda: ComponentSpec(name="fake")
    )


class JudgeConfig(BaseModel):
    """LLM-as-judge configuration for generation metrics.

    Params:
        model           -- judge model id (default: "gpt-4o")
        temperature     -- sampling temperature; 0.0 = deterministic (default: 0.0)
        api_key_env     -- env var for OpenAI API key (default: "OPENAI_API_KEY")
        cache_dir       -- directory for prompt → score cache (default: ".judge_cache")
        prompt_version  -- semver string for judge prompts; bump when prompts change
                           (default: "1.0.0")
        skip_on_missing_key -- if True and API key absent, return 0.0 instead of raising
                               (default: True)
    """

    model: str = "gpt-4o"
    temperature: float = 0.0
    api_key_env: str = "OPENAI_API_KEY"
    cache_dir: str = ".judge_cache"
    prompt_version: str = "1.0.0"
    skip_on_missing_key: bool = True


class EvalConfig(BaseModel):
    """Evaluation harness settings.

    Params:
        golden_set -- path to golden Q&A JSON file
        top_k      -- retrieval depth to evaluate at (default: 5)
        seed       -- random seed for reproducibility (default: 42)
        output_dir -- directory to write reports (default: reports/)
        judge      -- LLM-as-judge configuration (default: JudgeConfig())
    """

    golden_set: Path
    top_k: int = 5
    seed: int = 42
    output_dir: Path = Path("reports")
    judge: JudgeConfig = Field(default_factory=JudgeConfig)


class AgentConfig(BaseModel):
    """LangGraph agent behaviour parameters.

    Params:
        type                   -- "static" (StaticPipeline) or "langgraph" (LangGraphAgent)
                                  (default: "static")
        faithfulness_threshold -- self-correct triggers retry below this score (default: 0.1)
        max_retry              -- max re-retrieve attempts before escalation (default: 1)
        classify_method        -- "keyword" (rule-based) or "llm" (LLM call) (default: "keyword")
        top_k                  -- retrieval depth used inside the agent (default: 5)
        fast_generator         -- ComponentSpec for simple / factual queries (default: {name: fake})
        smart_generator        -- ComponentSpec for complex / multi-hop queries (default: {name: fake})
    """

    type: str = "static"
    faithfulness_threshold: float = 0.1
    max_retry: int = 1
    classify_method: str = "keyword"
    top_k: int = 5
    fast_generator: ComponentSpec = Field(
        default_factory=lambda: ComponentSpec(name="fake")
    )
    smart_generator: ComponentSpec = Field(
        default_factory=lambda: ComponentSpec(name="fake")
    )


class BenchmarkConfig(BaseModel):
    """Root config that ties together pipeline + eval settings.

    Params:
        pipeline -- PipelineConfig block
        agent    -- AgentConfig block (optional; default type="static")
        eval     -- EvalConfig block
    """

    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    eval: EvalConfig

    @model_validator(mode="before")
    @classmethod
    def _flatten_pipeline_component_specs(cls, data: Any) -> Any:
        """Allow plain dicts for component specs inside pipeline."""
        return data

    @classmethod
    def from_yaml(cls, path: Path) -> "BenchmarkConfig":
        """Load and validate a BenchmarkConfig from a YAML file.

        Raises:
            FileNotFoundError if *path* does not exist
            pydantic.ValidationError on schema violations
        """
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls.model_validate(raw)
