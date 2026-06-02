"""StaticPipeline — wires components together and implements the Pipeline Protocol.

All components are injected; StaticPipeline never imports concrete implementations.

Parent-child support
--------------------
When the Chunker returns ParentChildChunker output, chunks whose parent_id=None are
PARENT chunks (large context blocks). Chunks with a parent_id are CHILD chunks
(small, precision-indexed slices).

StaticPipeline.index() separates them:
  - Parents → stored in self._parent_map (dict[chunk_id → Chunk])
  - Children → embedded and upserted into the VectorStore

StaticPipeline.query() optionally expands each retrieved child to its parent's text
before passing context to the Generator (expand_to_parent=True by default).

Content-hash caching
--------------------
The pipeline tracks which chunk IDs have been indexed in self._indexed_ids.
Re-calling index() on the same corpus is idempotent: already-indexed chunks are
skipped, avoiding redundant API calls to the embedder.
"""
from __future__ import annotations

import time
from pathlib import Path

from ragbench.core.interfaces import (
    Chunker,
    Embedder,
    Generator,
    Parser,
    Reranker,
    Retriever,
    VectorStore,
)
from ragbench.core.types import Answer, Chunk, ScoredChunk


class StaticPipeline:
    """Fixed-topology RAG pipeline: parse → chunk → embed → store → retrieve → rerank → generate.

    Params:
        parser            -- Parser implementation
        chunker           -- Chunker implementation
        embedder          -- Embedder implementation
        vector_store      -- VectorStore implementation
        retriever         -- Retriever implementation
        reranker          -- Reranker implementation
        generator         -- Generator implementation
        top_k             -- default retrieval depth (default: 5)
        expand_to_parent  -- replace retrieved child chunks with their parent chunk
                             text before generation (default: True)
    """

    def __init__(
        self,
        parser: Parser,
        chunker: Chunker,
        embedder: Embedder,
        vector_store: VectorStore,
        retriever: Retriever,
        reranker: Reranker,
        generator: Generator,
        top_k: int = 5,
        expand_to_parent: bool = True,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store
        self._retriever = retriever
        self._reranker = reranker
        self._generator = generator
        self._top_k = top_k
        self._expand_to_parent = expand_to_parent

        # Parent chunks keyed by chunk.id — populated during index()
        self._parent_map: dict[str, Chunk] = {}
        # Set of chunk IDs already upserted into the vector store (content-hash cache)
        self._indexed_ids: set[str] = set()

    # ── Indexing ───────────────────────────────────────────────────────────────

    def index(self, corpus_dir: Path) -> None:
        """Parse *corpus_dir*, build/update the vector index.

        - Skips chunks whose id is already in _indexed_ids (idempotent re-runs).
        - Separates parent chunks from child chunks (ParentChildChunker convention).
        - Only child chunks (parent_id ≠ None) are embedded and stored in the
          VectorStore; parent chunks are kept in _parent_map for context expansion.
        - Falls back to flat chunking when no parent/child distinction is present.
        """
        docs = self._parser.parse(corpus_dir)
        all_chunks = self._chunker.chunk(docs)

        # Split into parents and indexable chunks
        parent_chunks: list[Chunk] = []
        index_chunks: list[Chunk] = []

        has_children = any(c.parent_id is not None for c in all_chunks)
        if has_children:
            for c in all_chunks:
                if c.parent_id is None:
                    parent_chunks.append(c)
                else:
                    index_chunks.append(c)
        else:
            # Flat chunking: every chunk goes to the index
            index_chunks = all_chunks

        # Register parents in the lookup map
        for p in parent_chunks:
            self._parent_map[p.id] = p

        # Filter out already-indexed chunks (content-hash cache)
        new_chunks = [c for c in index_chunks if c.id not in self._indexed_ids]
        if not new_chunks:
            return

        texts = [c.text for c in new_chunks]
        vectors = self._embedder.embed(texts)
        self._vector_store.upsert(new_chunks, vectors)
        self._indexed_ids.update(c.id for c in new_chunks)

        # Allow retrievers (e.g. HybridRrfRetriever) to build their own index
        if callable(getattr(self._retriever, "index_chunks", None)):
            self._retriever.index_chunks(new_chunks)  # type: ignore[attr-defined]

    # ── Querying ───────────────────────────────────────────────────────────────

    def query(self, question: str) -> Answer:
        """Answer *question* end-to-end; returns an Answer."""
        t0 = time.perf_counter()

        candidates = self._retriever.retrieve(question, top_k=self._top_k)
        reranked = self._reranker.rerank(question, candidates, top_k=self._top_k)

        # Parent expansion: swap child chunk text for richer parent context
        if self._expand_to_parent and self._parent_map:
            reranked = _expand_parents(reranked, self._parent_map)

        answer = self._generator.generate(question, reranked)
        answer.latency_ms = (time.perf_counter() - t0) * 1000
        return answer


def _expand_parents(
    scored: list[ScoredChunk],
    parent_map: dict[str, Chunk],
) -> list[ScoredChunk]:
    """Replace each ScoredChunk with its parent chunk if available.

    Preserves score and source; deduplicates by parent_id so the same parent
    block is not fed to the LLM twice.
    """
    seen_parent_ids: set[str] = set()
    expanded: list[ScoredChunk] = []
    for sc in scored:
        pid = sc.chunk.parent_id
        if pid and pid in parent_map:
            if pid in seen_parent_ids:
                continue
            seen_parent_ids.add(pid)
            expanded.append(
                ScoredChunk(chunk=parent_map[pid], score=sc.score, source=sc.source)
            )
        else:
            expanded.append(sc)
    return expanded


# ── Factory ────────────────────────────────────────────────────────────────────

def build_pipeline_from_config(config: "BenchmarkConfig") -> StaticPipeline:  # type: ignore[name-defined]
    """Build a StaticPipeline from a BenchmarkConfig.

    Imports all component modules so @register decorators fire before build().
    Loads .env if python-dotenv is available.
    """
    # Load .env so API keys are available to component constructors
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]
        load_dotenv()
    except ImportError:
        pass

    # Trigger @register decorators for all components
    import ragbench.components  # noqa: F401

    from ragbench.core.registry import build

    pc = config.pipeline
    embedder = build("embedder", pc.embedder.to_dict())
    vector_store = build("vector_store", pc.vector_store.to_dict())

    retriever_spec = pc.retriever.to_dict()
    retriever = build(
        "retriever",
        {**retriever_spec, "vector_store": vector_store, "embedder": embedder},
    )

    return StaticPipeline(
        parser=build("parser", pc.parser.to_dict()),
        chunker=build("chunker", pc.chunker.to_dict()),
        embedder=embedder,
        vector_store=vector_store,
        retriever=retriever,
        reranker=build("reranker", pc.reranker.to_dict()),
        generator=_build_generator(pc.generator.to_dict()),
        top_k=retriever_spec.get("top_k", 5),
    )


def _build_generator(spec: dict) -> object:
    """Build a Generator from a spec dict, handling the nested 'routed' case."""
    from ragbench.core.registry import build

    if spec.get("name") != "routed":
        return build("generator", spec)

    # Routed generator: build each sub-generator separately
    fast_spec = spec.get("fast_generator")
    smart_spec = spec.get("smart_generator")
    if not fast_spec or not smart_spec:
        raise ValueError(
            "RoutedGenerator config requires 'fast_generator' and 'smart_generator' sub-specs."
        )
    kwargs = {
        k: v for k, v in spec.items()
        if k not in ("name", "fast_generator", "smart_generator")
    }
    from ragbench.components.generators import RoutedGenerator  # noqa: PLC0415
    return RoutedGenerator(
        fast_generator=build("generator", fast_spec),
        smart_generator=build("generator", smart_spec),
        **kwargs,
    )
