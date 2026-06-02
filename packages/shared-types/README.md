# packages/shared-types — Shared Contracts

Core contracts for the HC-NS KB monorepo (hcns-shared Python package).

## Purpose

Centralize type definitions and interfaces so backend, agents, and eval are decoupled:
- **Types:** Document, Chunk, ScoredChunk, Answer (dataclasses)
- **Interfaces:** Parser, Chunker, Embedder, VectorStore, Retriever, Reranker, Generator, Pipeline, PipelineAdapter (Protocols)
- **Registry:** @register decorator + build() factory for component instantiation
- **Config:** Pydantic models for BenchmarkConfig, PipelineConfig, AgentConfig, EvalConfig, JudgeConfig
- **Utils:** token_overlap_score (used by agent self-correct)

## Structure

```
src/hcns_shared/
├── types.py          # Document, Chunk, ScoredChunk, Answer
├── interfaces.py     # Protocol classes (Parser, Generator, Pipeline, PipelineAdapter, etc.)
├── registry.py       # @register decorator, build(kind, spec) factory
├── config.py         # Pydantic config models
├── text_utils.py     # token_overlap_score utility
└── __init__.py       # Re-exports all above
```

## Key Design Decisions

1. **Protocol-based interfaces** — backend/agents implement Protocols, not inheritance. eval imports only Protocols, not implementations.
2. **Registry + factory** — all components @register at import time; build() instantiates via spec dict (no hardcoding).
3. **PipelineAdapter Protocol** — eval's only connection to pipeline (index/query); adapters live in eval/adapters/.
4. **Config-driven** — BenchmarkConfig.from_yaml() loads YAML → all components instantiated via registry → no env-var sprawl.

## Usage

```python
from hcns_shared import (
    Document, Chunk, ScoredChunk, Answer,
    Parser, Chunker, Pipeline,
    register, build, list_registered,
    BenchmarkConfig,
)

# Components register themselves
import hcns_backend        # all @register decorators fire
import hcns_agents.generators

# Config → Build → Use
cfg = BenchmarkConfig.from_yaml("config.yaml")
pipeline = build("pipeline", {"static": True})  # or via factory
answer = pipeline.query("question")
```

## Milestone Status

- **M001 (P0):** Core types + basic registry
- **P2 (M001):** HybridEmbedder, HybridVectorStore protocols
- **P4 (M001):** PipelineAdapter protocol for eval isolation
- **Current:** Full suite for P0-P5 (sweep, gate, reproducibility)
