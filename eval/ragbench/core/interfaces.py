"""Protocol interfaces for every pipeline component.

Pipelines depend ONLY on these Protocols — never on concrete implementations.
Adding a new implementation never requires touching this file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ragbench.core.types import Answer, Chunk, Document, ScoredChunk


@runtime_checkable
class Parser(Protocol):
    """Convert a raw file / directory into Documents.

    Params:
        source -- file path or directory to parse
    Returns:
        list of Document objects
    """

    def parse(self, source: Path) -> list[Document]: ...


@runtime_checkable
class Chunker(Protocol):
    """Split Documents into Chunks.

    Params:
        documents -- list of Document objects to chunk
    Returns:
        list of Chunk objects
    """

    def chunk(self, documents: list[Document]) -> list[Chunk]: ...


@runtime_checkable
class Embedder(Protocol):
    """Encode texts into dense vectors.

    Params:
        texts -- list of strings to embed
    Returns:
        list of float vectors (same order as input)
    """

    def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class VectorStore(Protocol):
    """Persist and search chunk embeddings.

    upsert -- index chunks with their vectors
    search -- return top-k ScoredChunks for a query vector
    """

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    def search(self, query_vector: list[float], top_k: int = 5) -> list[ScoredChunk]: ...


@runtime_checkable
class Retriever(Protocol):
    """High-level retrieval: query text → ScoredChunks.

    Params:
        query  -- natural-language question
        top_k  -- number of results to return (default: 5)
    Returns:
        list of ScoredChunk sorted descending by score
    """

    def retrieve(self, query: str, top_k: int = 5) -> list[ScoredChunk]: ...


@runtime_checkable
class Reranker(Protocol):
    """Re-score / filter a candidate list of ScoredChunks.

    Params:
        query   -- original question
        chunks  -- candidate ScoredChunks from retriever
        top_k   -- keep this many after reranking (default: same as input)
    Returns:
        re-ranked list of ScoredChunk
    """

    def rerank(
        self,
        query: str,
        chunks: list[ScoredChunk],
        top_k: int | None = None,
    ) -> list[ScoredChunk]: ...


@runtime_checkable
class Generator(Protocol):
    """Generate an Answer given a query and retrieved context.

    Params:
        query   -- natural-language question
        chunks  -- retrieved / reranked ScoredChunks
    Returns:
        Answer dataclass
    """

    def generate(self, query: str, chunks: list[ScoredChunk]) -> Answer: ...


@runtime_checkable
class Pipeline(Protocol):
    """Top-level interface the eval harness calls.

    index -- ingest a corpus directory and build the index
    query -- answer a single question end-to-end
    """

    def index(self, corpus_dir: Path) -> None: ...

    def query(self, question: str) -> Answer: ...


@runtime_checkable
class HybridEmbedder(Protocol):
    """Extension of Embedder that also produces sparse vectors (e.g. BGE-M3).

    Implementations MUST also implement the plain Embedder.embed() method
    so they are substitutable anywhere a regular Embedder is expected.

    embed_sparse returns one sparse dict per input text:
        {token_id (int): weight (float)}
    """

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_sparse(self, texts: list[str]) -> list[dict[int, float]]: ...


@runtime_checkable
class HybridVectorStore(Protocol):
    """Extension of VectorStore that stores and searches both dense + sparse vectors.

    Implementations MUST also implement the plain VectorStore interface.
    Sparse vectors are dicts mapping token_id → weight (BGE-M3 lexical format).

    rrf_k -- RRF smoothing constant used in hybrid search (60 is standard default)
    """

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    def search(self, query_vector: list[float], top_k: int = 5) -> list[ScoredChunk]: ...

    def upsert_hybrid(
        self,
        chunks: list[Chunk],
        dense_vecs: list[list[float]],
        sparse_vecs: list[dict[int, float]],
    ) -> None: ...

    def search_hybrid(
        self,
        dense_vec: list[float],
        sparse_vec: dict[int, float],
        top_k: int = 5,
        rrf_k: int = 60,
    ) -> list[ScoredChunk]: ...


# Convenience type alias
ComponentConfig = dict[str, Any]
