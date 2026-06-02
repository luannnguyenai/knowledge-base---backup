"""Retriever implementations."""
from __future__ import annotations

from ragbench.core.interfaces import Embedder, VectorStore
from ragbench.core.registry import register
from ragbench.core.types import Chunk, ScoredChunk


@register("retriever", "dense")
class DenseRetriever:
    """Single-vector dense retrieval: embed query → VectorStore.search.

    Params:
        vector_store -- VectorStore instance (injected by factory)
        embedder     -- Embedder instance (injected by factory)
        top_k        -- default number of results (default: 5)
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
        top_k: int = 5,
    ) -> None:
        self._store = vector_store
        self._embedder = embedder
        self._top_k = top_k

    def retrieve(self, query: str, top_k: int | None = None) -> list[ScoredChunk]:
        k = top_k if top_k is not None else self._top_k
        [query_vec] = self._embedder.embed([query])
        return self._store.search(query_vec, top_k=k)


@register("retriever", "hybrid_rrf")
class HybridRrfRetriever:
    """Hybrid retrieval combining dense vector search with in-memory BM25, fused via RRF.

    Architecture:
        - Dense path  : embed query → VectorStore.search (same as DenseRetriever)
        - Sparse path : BM25 over all indexed child chunks (rank-bm25, in-memory)
        - Fusion      : Reciprocal Rank Fusion  score = Σ 1/(rrf_k + rank_i)

    The BM25 index is built lazily on the first retrieve() call that follows at
    least one index_chunks() call. StaticPipeline.index() calls index_chunks()
    automatically (duck-typed) after upserting into the vector store.

    If a HybridEmbedder (e.g. BgeM3Embedder) is passed AND the VectorStore
    implements search_hybrid(), this retriever delegates to that path instead.

    Params:
        vector_store  -- VectorStore (or HybridVectorStore) instance
        embedder      -- Embedder (or HybridEmbedder) instance
        top_k         -- final results to return (default: 5)
        candidate_k   -- candidates fetched per path before fusion (default: 20)
        rrf_k         -- RRF smoothing constant (default: 60)
        alpha         -- dense weight for weighted-score fallback, unused in RRF mode
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
        top_k: int = 5,
        candidate_k: int = 20,
        rrf_k: int = 60,
        alpha: float = 0.5,
    ) -> None:
        self._store = vector_store
        self._embedder = embedder
        self._top_k = top_k
        self._candidate_k = candidate_k
        self._rrf_k = rrf_k
        self._alpha = alpha

        # BM25 index (populated by index_chunks)
        self._bm25_chunks: list[Chunk] = []
        self._bm25_model: object | None = None
        self._bm25_dirty: bool = False

    # ── Called by StaticPipeline.index() via duck typing ──────────────────────

    def index_chunks(self, chunks: list[Chunk]) -> None:
        """Add *chunks* to the BM25 index. Call before retrieve()."""
        self._bm25_chunks.extend(chunks)
        self._bm25_dirty = True  # rebuild on next retrieve

    def _rebuild_bm25(self) -> None:
        try:
            from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "rank-bm25 is not installed. Run: uv add rank-bm25"
            ) from e
        tokenized = [_tokenize(c.text) for c in self._bm25_chunks]
        self._bm25_model = BM25Okapi(tokenized)
        self._bm25_dirty = False

    # ── Retrieve ───────────────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int | None = None) -> list[ScoredChunk]:
        k = top_k if top_k is not None else self._top_k
        ck = max(k, self._candidate_k)

        # Fast path: delegate to Qdrant native hybrid if both sides support it
        if _has_hybrid_store(self._store) and _has_embed_sparse(self._embedder):
            [dense_vec] = self._embedder.embed([query])
            [sparse_vec] = self._embedder.embed_sparse([query])  # type: ignore[attr-defined]
            return self._store.search_hybrid(  # type: ignore[attr-defined]
                dense_vec, sparse_vec, top_k=k, rrf_k=self._rrf_k
            )

        # BM25 + dense RRF path
        [query_vec] = self._embedder.embed([query])
        dense_results = self._store.search(query_vec, top_k=ck)

        bm25_results: list[ScoredChunk] = []
        if self._bm25_chunks:
            if self._bm25_dirty:
                self._rebuild_bm25()
            bm25_results = self._bm25_search(query, ck)

        return _rrf_fuse(dense_results, bm25_results, top_k=k, k=self._rrf_k)

    def _bm25_search(self, query: str, top_k: int) -> list[ScoredChunk]:
        assert self._bm25_model is not None
        scores = self._bm25_model.get_scores(_tokenize(query))  # type: ignore[attr-defined]
        ranked = sorted(
            zip(scores, self._bm25_chunks), key=lambda x: x[0], reverse=True
        )
        return [
            ScoredChunk(chunk=c, score=float(s), source="bm25")
            for s, c in ranked[:top_k]
        ]


# ── RRF helpers ────────────────────────────────────────────────────────────────

def _rrf_fuse(
    list_a: list[ScoredChunk],
    list_b: list[ScoredChunk],
    top_k: int,
    k: int = 60,
) -> list[ScoredChunk]:
    """Reciprocal Rank Fusion of two ranked lists, deduped by chunk.id."""
    scores: dict[str, float] = {}
    chunks: dict[str, Chunk] = {}
    sources: dict[str, str] = {}

    for rank, sc in enumerate(list_a, start=1):
        cid = sc.chunk.id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        chunks[cid] = sc.chunk
        sources[cid] = sc.source

    for rank, sc in enumerate(list_b, start=1):
        cid = sc.chunk.id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        chunks[cid] = sc.chunk
        sources[cid] = sources.get(cid, sc.source)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [
        ScoredChunk(chunk=chunks[cid], score=score, source=f"rrf+{sources[cid]}")
        for cid, score in ranked[:top_k]
    ]


def _tokenize(text: str) -> list[str]:
    """Whitespace tokeniser for BM25 — adequate for Vietnamese."""
    return text.lower().split()


def _has_hybrid_store(store: object) -> bool:
    return callable(getattr(store, "search_hybrid", None))


def _has_embed_sparse(embedder: object) -> bool:
    return callable(getattr(embedder, "embed_sparse", None))
