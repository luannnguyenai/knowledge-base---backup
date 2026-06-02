"""hcns_shared — shared contracts for the HC-NS KB monorepo.

Re-exports the canonical types, interfaces, registry, config, and text utils
so downstream packages import from a single stable namespace.
"""
from hcns_shared.config import (
    AgentConfig,
    BenchmarkConfig,
    ComponentSpec,
    EvalConfig,
    JudgeConfig,
    PipelineConfig,
)
from hcns_shared.interfaces import (
    Chunker,
    Embedder,
    Generator,
    HybridEmbedder,
    HybridVectorStore,
    Parser,
    Pipeline,
    PipelineAdapter,
    Reranker,
    Retriever,
    VectorStore,
)
from hcns_shared.registry import (
    ComponentNotFoundError,
    build,
    list_registered,
    register,
)
from hcns_shared.text_utils import token_overlap_score
from hcns_shared.types import Answer, Chunk, Document, ScoredChunk

__all__ = [
    # types
    "Document", "Chunk", "ScoredChunk", "Answer",
    # interfaces
    "Parser", "Chunker", "Embedder", "VectorStore", "Retriever", "Reranker",
    "Generator", "Pipeline", "PipelineAdapter", "HybridEmbedder", "HybridVectorStore",
    # registry
    "register", "build", "list_registered", "ComponentNotFoundError",
    # config
    "BenchmarkConfig", "PipelineConfig", "AgentConfig", "EvalConfig",
    "JudgeConfig", "ComponentSpec",
    # utils
    "token_overlap_score",
]
