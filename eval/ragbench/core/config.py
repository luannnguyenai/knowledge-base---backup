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


class EvalConfig(BaseModel):
    """Evaluation harness settings.

    Params:
        golden_set -- path to golden Q&A JSON file
        top_k      -- retrieval depth to evaluate at (default: 5)
        seed       -- random seed for reproducibility (default: 42)
        output_dir -- directory to write reports (default: reports/)
    """

    golden_set: Path
    top_k: int = 5
    seed: int = 42
    output_dir: Path = Path("reports")


class BenchmarkConfig(BaseModel):
    """Root config that ties together pipeline + eval settings.

    Params:
        pipeline -- PipelineConfig block
        eval     -- EvalConfig block
    """

    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
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
