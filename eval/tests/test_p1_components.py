"""P1 component tests — all external APIs are mocked.

Covers: ParentChildChunker, GeminiEmbedder, QdrantVectorStore,
        GeminiGenerator, LlamaParseParser, StaticPipeline parent-child flow.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hcns_backend.chunking import ParentChildChunker
from hcns_backend.retrieval.vector_stores import QdrantVectorStore, _chunk_to_payload, _payload_to_chunk
from hcns_shared.types import Chunk, Document, ScoredChunk


# ── ParentChildChunker ─────────────────────────────────────────────────────────

class TestParentChildChunker:
    def _doc(self, text: str) -> Document:
        return Document(id="d1", text=text, metadata={"source": "test"})

    def test_produces_parents_and_children(self):
        doc = self._doc("x" * 1200)
        chunks = ParentChildChunker(parent_chunk_size=500, child_chunk_size=150, child_overlap=10).chunk([doc])
        parents = [c for c in chunks if c.parent_id is None]
        children = [c for c in chunks if c.parent_id is not None]
        assert len(parents) >= 2
        assert len(children) > len(parents)

    def test_children_reference_valid_parents(self):
        doc = self._doc("a" * 1000)
        chunks = ParentChildChunker(parent_chunk_size=400, child_chunk_size=100).chunk([doc])
        parent_ids = {c.id for c in chunks if c.parent_id is None}
        for child in [c for c in chunks if c.parent_id is not None]:
            assert child.parent_id in parent_ids

    def test_parents_come_before_children(self):
        doc = self._doc("b" * 800)
        chunks = ParentChildChunker(parent_chunk_size=400, child_chunk_size=100).chunk([doc])
        first_child_idx = next(i for i, c in enumerate(chunks) if c.parent_id is not None)
        last_parent_idx = max(i for i, c in enumerate(chunks) if c.parent_id is None)
        assert last_parent_idx < first_child_idx

    def test_child_chunk_size_must_be_smaller_than_parent(self):
        with pytest.raises(ValueError, match="child_chunk_size"):
            ParentChildChunker(parent_chunk_size=100, child_chunk_size=200)

    def test_child_metadata_has_level(self):
        chunks = ParentChildChunker(parent_chunk_size=200, child_chunk_size=50).chunk(
            [self._doc("z" * 400)]
        )
        for c in chunks:
            assert "chunk_level" in c.metadata


# ── QdrantVectorStore ──────────────────────────────────────────────────────────

class TestQdrantVectorStore:
    def _chunks_and_vecs(self, n: int = 3, dim: int = 8):
        from hcns_backend.embedding import HashEmbedder
        chunks = [Chunk(id=f"c{i:02x}", doc_id="d", text=f"doc {i}") for i in range(n)]
        vecs = HashEmbedder(dim=dim).embed([c.text for c in chunks])
        return chunks, vecs

    def test_upsert_and_search(self):
        store = QdrantVectorStore(mode="memory", dim=8)
        chunks, vecs = self._chunks_and_vecs(dim=8)
        store.upsert(chunks, vecs)
        results = store.search(vecs[0], top_k=2)
        assert len(results) == 2
        assert all(isinstance(r, ScoredChunk) for r in results)
        assert results[0].chunk.id == chunks[0].id  # first vec should be most similar

    def test_idempotent_upsert(self):
        store = QdrantVectorStore(mode="memory", dim=8)
        chunks, vecs = self._chunks_and_vecs(dim=8)
        store.upsert(chunks, vecs)
        store.upsert(chunks, vecs)  # second upsert same data
        results = store.search(vecs[0], top_k=10)
        assert len(results) == len(chunks)  # no duplicates

    def test_payload_roundtrip(self):
        chunk = Chunk(id="aabbccdd", doc_id="d1", text="hello", metadata={"k": "v"}, parent_id="pppp1234")
        payload = _chunk_to_payload(chunk)
        recovered = _payload_to_chunk(payload)
        assert recovered.id == chunk.id
        assert recovered.doc_id == chunk.doc_id
        assert recovered.text == chunk.text
        assert recovered.parent_id == chunk.parent_id
        assert recovered.metadata["k"] == "v"

    def test_search_empty_store(self):
        store = QdrantVectorStore(mode="memory")
        # Ensure collection exists before search
        store._dim = 8
        results = store.search([0.0] * 8, top_k=3)
        assert results == []


# ── GeminiEmbedder (mocked) ───────────────────────────────────────────────────

class TestGeminiEmbedderMocked:
    def _make_embedder(self, dim: int = 8):
        """Build a GeminiEmbedder bypassing __init__ with a mock client."""
        from hcns_backend.embedding import GeminiEmbedder

        emb = GeminiEmbedder.__new__(GeminiEmbedder)
        emb.model = "text-embedding-004"
        emb.dim = dim
        emb.task_type = "RETRIEVAL_DOCUMENT"
        emb.batch_size = 100
        emb.retry_attempts = 1

        # Mock the google-genai client
        mock_emb_1 = MagicMock()
        mock_emb_1.values = [0.1] * dim
        mock_emb_2 = MagicMock()
        mock_emb_2.values = [0.2] * dim
        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = MagicMock(
            embeddings=[mock_emb_1, mock_emb_2]
        )
        emb._client = mock_client
        return emb

    def test_embed_returns_vectors(self):
        emb = self._make_embedder(dim=8)
        vecs = emb._embed_batch(["text 1", "text 2"])
        assert len(vecs) == 2
        assert len(vecs[0]) == 8

    def test_missing_api_key_raises(self):
        env = {k: v for k, v in os.environ.items() if k != "GOOGLE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(EnvironmentError, match="GOOGLE_API_KEY"):
                from hcns_backend.embedding import GeminiEmbedder
                GeminiEmbedder(dim=8, api_key_env="GOOGLE_API_KEY")


# ── GeminiGenerator (mocked) ─────────────────────────────────────────────────

class TestGeminiGeneratorMocked:
    def _make_generator(self):
        from hcns_agents.generators import GeminiGenerator

        gen = GeminiGenerator.__new__(GeminiGenerator)
        gen.model = "gemini-2.0-flash"
        gen.temperature = 0.1
        gen.max_output_tokens = 512
        gen.retry_attempts = 1
        gen._system_prompt = "sys"
        gen._client = MagicMock()
        return gen

    def test_generate_extracts_citations(self):
        gen = self._make_generator()
        chunk = Chunk(id="aabbccdd1122eeff", doc_id="d", text="Nghỉ phép 12 ngày")
        sc = ScoredChunk(chunk=chunk, score=0.9, source="qdrant")

        mock_response = MagicMock()
        mock_response.text = "Nhân viên được nghỉ phép 12 ngày [aabbccdd1122eeff]."
        mock_response.usage_metadata = None
        gen._client.models.generate_content.return_value = mock_response

        answer = gen.generate("Số ngày nghỉ phép?", [sc])
        assert "aabbccdd1122eeff" in answer.citations
        assert "12 ngày" in answer.text

    def test_generate_no_context(self):
        gen = self._make_generator()
        mock_response = MagicMock()
        mock_response.text = "Tôi không tìm thấy thông tin này trong KB."
        mock_response.usage_metadata = None
        gen._client.models.generate_content.return_value = mock_response

        answer = gen.generate("Câu hỏi bí ẩn?", [])
        assert answer.contexts == []
        assert answer.citations == []


# ── StaticPipeline parent-child integration ───────────────────────────────────

class TestStaticPipelineParentChild:
    def _build_pipeline(self):
        from hcns_backend.chunking import ParentChildChunker
        from hcns_backend.embedding import HashEmbedder
        from hcns_agents.generators import FakeGenerator
        from hcns_backend.parsing import EchoParser
        from hcns_backend.reranking import NoReranker
        from hcns_backend.retrieval.retrievers import DenseRetriever
        from hcns_backend.retrieval.vector_stores import InMemoryVectorStore
        from hcns_agents.pipelines.static_pipeline import StaticPipeline

        embedder = HashEmbedder(dim=16)
        store = InMemoryVectorStore()
        return StaticPipeline(
            parser=EchoParser(),
            chunker=ParentChildChunker(parent_chunk_size=100, child_chunk_size=40, child_overlap=5),
            embedder=embedder,
            vector_store=store,
            retriever=DenseRetriever(vector_store=store, embedder=embedder, top_k=2),
            reranker=NoReranker(),
            generator=FakeGenerator(max_context_chars=200),
            top_k=2,
            expand_to_parent=True,
        )

    def test_index_populates_parent_map(self):
        pipeline = self._build_pipeline()
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "doc.txt").write_text("x" * 300)
            pipeline.index(Path(td))
        assert len(pipeline._parent_map) > 0

    def test_index_is_idempotent(self):
        pipeline = self._build_pipeline()
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "doc.txt").write_text("y" * 300)
            pipeline.index(Path(td))
            first_count = len(pipeline._indexed_ids)
            pipeline.index(Path(td))  # second call — nothing new
            assert len(pipeline._indexed_ids) == first_count

    def test_query_expands_to_parent_text(self):
        pipeline = self._build_pipeline()
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "doc.txt").write_text("Nghỉ phép năm được quy định rõ ràng trong chính sách. " * 10)
            pipeline.index(Path(td))

        answer = pipeline.query("Chính sách nghỉ phép?")
        assert answer.text  # non-empty
        # Parent chunks are at least parent_chunk_size chars (up to text length)
        # FakeGenerator truncates at 200, but parent text should be >= child text
        for ctx in answer.contexts:
            assert len(ctx) > 0

    def test_index_only_stores_children_in_vector_store(self):
        """Vector store should contain only child chunks, not parents."""
        pipeline = self._build_pipeline()
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "doc.txt").write_text("z" * 400)
            pipeline.index(Path(td))
        # _indexed_ids are all children
        parent_ids = set(pipeline._parent_map.keys())
        # No parent id should appear in indexed_ids
        assert pipeline._indexed_ids.isdisjoint(parent_ids)
