"""hcns_backend — component layers for the HC-NS KB pipeline.

Layers (each registers its implementations via @register on import):
    parsing    -- EchoParser, LlamaParseParser
    chunking   -- FixedChunker, ParentChildChunker, ContextualParentChildChunker
    embedding  -- HashEmbedder, GeminiEmbedder, BgeM3Embedder
    retrieval  -- InMemoryVectorStore, QdrantVectorStore, DenseRetriever, HybridRrfRetriever
    reranking  -- NoReranker, CohereReranker, BgeReranker

Call register_all() (or simply `import hcns_backend`) before build()-ing any
component so the registry is populated.
"""
from hcns_backend import (  # noqa: F401  (side-effect: @register decorators fire)
    chunking,
    embedding,
    parsing,
    reranking,
    retrieval,
)


def register_all() -> None:
    """Idempotent no-op: importing this module already registered every layer.

    Provided as an explicit, self-documenting hook for factories that want to
    guarantee registration before calling build().
    """
    return None
