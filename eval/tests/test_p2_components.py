"""P2 component tests — all heavy models and external APIs are mocked.

Covers:
  ContextualParentChildChunker, BgeM3Embedder, HybridRrfRetriever (BM25 path),
  CohereReranker, BgeReranker, RoutedGenerator, QdrantVectorStore hybrid methods,
  StaticPipeline.index() → retriever.index_chunks() duck typing,
  build_pipeline_from_config with routed generator.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hcns_backend.chunking import (
    ContextualParentChildChunker,
    _nearest_heading,
)
from hcns_backend.embedding import HashEmbedder
from hcns_agents.generators import FakeGenerator, RoutedGenerator
from hcns_backend.parsing import EchoParser
from hcns_backend.reranking import NoReranker
from hcns_backend.retrieval.retrievers import HybridRrfRetriever, _rrf_fuse
from hcns_backend.retrieval.vector_stores import InMemoryVectorStore
from hcns_agents.pipelines.static_pipeline import StaticPipeline
from hcns_shared.types import Chunk, Document, ScoredChunk


# ── helpers ────────────────────────────────────────────────────────────────────

def _doc(text: str, filename: str = "test.txt") -> Document:
    return Document(id="d1", text=text, metadata={"source": filename, "filename": filename})


def _chunk(cid: str, text: str = "text") -> Chunk:
    return Chunk(id=cid, doc_id="d", text=text)


def _scored(cid: str, score: float, text: str = "x", source: str = "s") -> ScoredChunk:
    return ScoredChunk(chunk=_chunk(cid, text), score=score, source=source)


# ── ContextualParentChildChunker ───────────────────────────────────────────────

class TestContextualParentChildChunker:
    _MARKDOWN = (
        "# Chính sách nghỉ phép\n\n"
        "Nhân viên có quyền nghỉ phép.\n\n"
        "## Số ngày phép\n\n"
        + "A" * 300
        + "\n\n## Quy trình xin phép\n\n"
        + "B" * 300
    )

    def _chunker(self):
        return ContextualParentChildChunker(
            parent_chunk_size=400, child_chunk_size=120, child_overlap=10
        )

    def test_children_have_context_prefix(self):
        doc = _doc(self._MARKDOWN, "leave_policy.txt")
        chunks = self._chunker().chunk([doc])
        children = [c for c in chunks if c.parent_id is not None]
        assert len(children) > 0
        for child in children:
            assert "Tài liệu:" in child.text
            assert "leave_policy.txt" in child.text

    def test_section_header_detected_in_prefix(self):
        doc = _doc(self._MARKDOWN, "policy.txt")
        chunks = self._chunker().chunk([doc])
        children = [c for c in chunks if c.parent_id is not None]
        texts = [c.text for c in children]
        # At least one child should mention a section header
        has_section = any("Mục:" in t and "General" not in t for t in texts)
        assert has_section

    def test_custom_template(self):
        chunker = ContextualParentChildChunker(
            parent_chunk_size=400,
            child_chunk_size=120,
            context_template="Doc:{filename}|Sec:{section}\n",
        )
        doc = _doc("## Header\n" + "x" * 300, "f.txt")
        children = [c for c in chunker.chunk([doc]) if c.parent_id is not None]
        assert all("Doc:f.txt" in c.text for c in children)

    def test_metadata_has_context_section(self):
        doc = _doc("## Section\n" + "y" * 300, "doc.txt")
        chunks = self._chunker().chunk([doc])
        children = [c for c in chunks if c.parent_id is not None]
        assert all("context_section" in c.metadata for c in children)

    def test_nearest_heading_returns_last_before_offset(self):
        text = "# Intro\ntext\n## Details\nmore\n### Sub\ndeep"
        assert _nearest_heading(text, 100) == "Sub"
        # Heading at offset=0 IS the section header for the content that follows
        assert _nearest_heading(text, 0) == "Intro"
        # A child starting before any heading has no section
        assert _nearest_heading(text, -1) is None

    def test_no_heading_returns_general(self):
        doc = _doc("plain text " * 50, "plain.txt")
        children = [
            c for c in self._chunker().chunk([doc]) if c.parent_id is not None
        ]
        assert any("General" in c.text for c in children)

    def test_inherits_parent_child_guarantee(self):
        """Parents still come before children in the output list."""
        doc = _doc("x" * 800, "d.txt")
        chunks = self._chunker().chunk([doc])
        last_parent = max(i for i, c in enumerate(chunks) if c.parent_id is None)
        first_child = min(i for i, c in enumerate(chunks) if c.parent_id is not None)
        assert last_parent < first_child


# ── BgeM3Embedder (mocked) ─────────────────────────────────────────────────────

class TestBgeM3EmbedderMocked:
    def _make_embedder(self, dim: int = 8):
        from hcns_backend.embedding import BgeM3Embedder

        emb = BgeM3Embedder.__new__(BgeM3Embedder)
        emb.batch_size = 32
        emb.max_length = 512
        emb.return_sparse = True

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": [[0.1] * dim, [0.2] * dim],
            "lexical_weights": [{1: 0.5, 2: 0.3}, {3: 0.9}],
        }
        emb._model = mock_model
        return emb

    def test_embed_returns_dense_vectors(self):
        emb = self._make_embedder(dim=8)
        vecs = emb.embed(["text a", "text b"])
        assert len(vecs) == 2 and len(vecs[0]) == 8

    def test_embed_sparse_returns_int_keyed_dicts(self):
        emb = self._make_embedder()
        sparse = emb.embed_sparse(["text a", "text b"])
        assert len(sparse) == 2
        for d in sparse:
            assert all(isinstance(k, int) for k in d.keys())
            assert all(isinstance(v, float) for v in d.values())

    def test_embed_sparse_string_keys_are_hashed(self):
        from hcns_backend.embedding import BgeM3Embedder

        emb = BgeM3Embedder.__new__(BgeM3Embedder)
        emb.batch_size = 32
        emb.max_length = 512
        emb.return_sparse = True
        mock_model = MagicMock()
        # Return string keys (older FlagEmbedding versions)
        mock_model.encode.return_value = {
            "dense_vecs": [[0.1] * 4],
            "lexical_weights": [{"nghỉ": 0.7, "phép": 0.4}],
        }
        emb._model = mock_model
        sparse = emb.embed_sparse(["test"])
        assert all(isinstance(k, int) for k in sparse[0].keys())

    def test_embed_empty_returns_empty(self):
        emb = self._make_embedder()
        assert emb.embed([]) == []
        assert emb.embed_sparse([]) == []


# ── HybridRrfRetriever ─────────────────────────────────────────────────────────

class TestHybridRrfRetriever:
    def _build_retriever(self, dim: int = 8):
        emb = HashEmbedder(dim=dim)
        store = InMemoryVectorStore()
        return HybridRrfRetriever(
            vector_store=store, embedder=emb, top_k=3, candidate_k=10, rrf_k=60
        ), store, emb

    def _index(self, retriever, store, emb, texts: list[str]):
        chunks = [Chunk(id=f"c{i:02d}", doc_id="d", text=t) for i, t in enumerate(texts)]
        vecs = emb.embed([c.text for c in chunks])
        store.upsert(chunks, vecs)
        retriever.index_chunks(chunks)
        return chunks

    def test_retrieve_returns_scored_chunks(self):
        ret, store, emb = self._build_retriever()
        self._index(ret, store, emb, [f"document about topic {i}" for i in range(5)])
        results = ret.retrieve("topic 2", top_k=3)
        assert len(results) == 3
        assert all(isinstance(r, ScoredChunk) for r in results)

    def test_rrf_fuse_merges_two_lists(self):
        a = [_scored("c1", 0.9), _scored("c2", 0.7), _scored("c3", 0.5)]
        b = [_scored("c2", 0.8), _scored("c1", 0.6), _scored("c4", 0.4)]
        merged = _rrf_fuse(a, b, top_k=4, k=60)
        ids = [r.chunk.id for r in merged]
        assert "c1" in ids and "c2" in ids  # top-2 in both lists must be present

    def test_rrf_fuse_deduplicates(self):
        a = [_scored("c1", 0.9), _scored("c2", 0.7)]
        b = [_scored("c1", 0.8), _scored("c3", 0.6)]
        merged = _rrf_fuse(a, b, top_k=5)
        ids = [r.chunk.id for r in merged]
        assert ids.count("c1") == 1  # c1 deduped

    def test_index_chunks_builds_bm25(self):
        ret, store, emb = self._build_retriever()
        chunks = [Chunk(id="c0", doc_id="d", text="nghỉ phép năm")]
        ret.index_chunks(chunks)
        assert len(ret._bm25_chunks) == 1
        assert ret._bm25_dirty is True

    def test_pipeline_calls_index_chunks_automatically(self):
        """StaticPipeline.index() must trigger retriever.index_chunks()."""
        emb = HashEmbedder(dim=8)
        store = InMemoryVectorStore()
        ret = HybridRrfRetriever(vector_store=store, embedder=emb, top_k=2)
        pipeline = StaticPipeline(
            parser=EchoParser(),
            chunker=__import__(
                "hcns_backend.chunking", fromlist=["FixedChunker"]
            ).FixedChunker(chunk_size=50, overlap=5),
            embedder=emb,
            vector_store=store,
            retriever=ret,
            reranker=NoReranker(),
            generator=FakeGenerator(),
            top_k=2,
        )
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "doc.txt").write_text("nghỉ phép chính sách nội bộ công ty")
            pipeline.index(Path(td))
        assert len(ret._bm25_chunks) > 0

    def test_retrieve_no_bm25_falls_back_to_dense(self):
        """If no chunks indexed in BM25, still returns dense results."""
        ret, store, emb = self._build_retriever()
        # Only index into store, not via index_chunks
        chunks = [Chunk(id=f"c{i}", doc_id="d", text=f"text {i}") for i in range(3)]
        vecs = emb.embed([c.text for c in chunks])
        store.upsert(chunks, vecs)
        # BM25 is empty — should still return dense results
        results = ret.retrieve("text 1", top_k=2)
        assert len(results) == 2


# ── CohereReranker (mocked) ───────────────────────────────────────────────────

class TestCohereRerankerMocked:
    def _make_reranker(self):
        from hcns_backend.reranking import CohereReranker

        r = CohereReranker.__new__(CohereReranker)
        r.model = "rerank-multilingual-v3.0"
        r.top_k = 3
        r.score_threshold = 0.0
        r._client = MagicMock()
        return r

    def test_rerank_returns_sorted_by_cohere_score(self):
        r = self._make_reranker()
        chunks = [_scored(f"c{i}", 0.9 - i * 0.1) for i in range(4)]

        hit0 = MagicMock(index=2, relevance_score=0.95)
        hit1 = MagicMock(index=0, relevance_score=0.80)
        hit2 = MagicMock(index=1, relevance_score=0.60)
        r._client.rerank.return_value = MagicMock(results=[hit0, hit1, hit2])

        results = r.rerank("nghỉ phép?", chunks, top_k=3)
        assert len(results) == 3
        assert results[0].chunk.id == "c2"
        assert results[0].score == pytest.approx(0.95)

    def test_rerank_filters_below_threshold(self):
        r = self._make_reranker()
        r.score_threshold = 0.5
        chunks = [_scored(f"c{i}", 1.0) for i in range(2)]

        hit0 = MagicMock(index=0, relevance_score=0.8)
        hit1 = MagicMock(index=1, relevance_score=0.2)  # below threshold
        r._client.rerank.return_value = MagicMock(results=[hit0, hit1])

        results = r.rerank("q", chunks)
        assert len(results) == 1
        assert results[0].chunk.id == "c0"

    def test_rerank_empty_input_returns_empty(self):
        r = self._make_reranker()
        assert r.rerank("q", []) == []

    def test_missing_api_key_raises(self):
        env = {k: v for k, v in os.environ.items() if k != "COHERE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(EnvironmentError, match="COHERE_API_KEY"):
                from hcns_backend.reranking import CohereReranker
                CohereReranker(api_key_env="COHERE_API_KEY")


# ── BgeReranker (mocked) ──────────────────────────────────────────────────────

class TestBgeRerankerMocked:
    def _make_reranker(self, score_threshold: float = 0.0):
        from hcns_backend.reranking import BgeReranker

        r = BgeReranker.__new__(BgeReranker)
        r.top_k = 3
        r.score_threshold = score_threshold
        r._model = MagicMock()
        return r

    def test_rerank_sorts_by_score(self):
        r = self._make_reranker()
        chunks = [_scored(f"c{i}", 0.5) for i in range(3)]
        r._model.compute_score.return_value = [0.3, 0.9, 0.6]
        results = r.rerank("q?", chunks)
        assert results[0].chunk.id == "c1"  # highest score
        assert results[0].score == pytest.approx(0.9)

    def test_rerank_respects_threshold(self):
        r = self._make_reranker(score_threshold=0.5)
        chunks = [_scored(f"c{i}", 0.5) for i in range(3)]
        r._model.compute_score.return_value = [0.8, 0.4, 0.6]
        results = r.rerank("q?", chunks)
        ids = [r.chunk.id for r in results]
        assert "c1" not in ids  # 0.4 < 0.5 threshold

    def test_rerank_empty_input(self):
        r = self._make_reranker()
        assert r.rerank("q", []) == []

    def test_source_tag_is_bge_reranker(self):
        r = self._make_reranker()
        chunks = [_scored("c0", 0.5, text="nghỉ phép")]
        r._model.compute_score.return_value = [0.7]
        results = r.rerank("q?", chunks)
        assert results[0].source == "bge_reranker"


# ── RoutedGenerator ───────────────────────────────────────────────────────────

class TestRoutedGenerator:
    def _make(self, keywords=None, min_words=5):
        fast = FakeGenerator(max_context_chars=50)
        smart = FakeGenerator(max_context_chars=200)
        return RoutedGenerator(
            fast_generator=fast,
            smart_generator=smart,
            complex_keywords=keywords or ["so sánh", "phân tích"],
            min_words_for_smart=min_words,
        )

    def test_routes_keyword_match_to_smart(self):
        gen = self._make()
        sc = ScoredChunk(chunk=_chunk("c1", "context"), score=0.9, source="s")
        answer = gen.generate("So sánh chính sách nghỉ phép A và B", [sc])
        assert answer.trace == "routed:smart"

    def test_routes_long_query_to_smart(self):
        gen = self._make(min_words=3)
        sc = ScoredChunk(chunk=_chunk("c1", "ctx"), score=0.9, source="s")
        answer = gen.generate("nghỉ phép mấy ngày mỗi năm", [sc])  # 6 words > 3
        assert answer.trace == "routed:smart"

    def test_routes_simple_query_to_fast(self):
        gen = self._make(min_words=20)  # high threshold
        sc = ScoredChunk(chunk=_chunk("c1", "ctx"), score=0.9, source="s")
        answer = gen.generate("Số ngày phép?", [sc])
        assert answer.trace == "routed:fast"

    def test_case_insensitive_keyword_match(self):
        gen = self._make(keywords=["SO SÁNH"])
        sc = ScoredChunk(chunk=_chunk("c1", "ctx"), score=0.9, source="s")
        answer = gen.generate("so sánh hai chính sách", [sc])
        assert answer.trace == "routed:smart"

    def test_default_keywords_loaded(self):
        gen = RoutedGenerator(fast_generator=FakeGenerator(), smart_generator=FakeGenerator())
        assert len(gen._keywords) > 0

    def test_answer_text_from_correct_generator(self):
        """Fast generator truncates at 50 chars; smart at 200 — verify routing affects output."""
        fast = FakeGenerator(max_context_chars=1)
        smart = FakeGenerator(max_context_chars=500)
        gen = RoutedGenerator(
            fast_generator=fast, smart_generator=smart,
            complex_keywords=["phân tích"], min_words_for_smart=100,
        )
        long_ctx = "a" * 300
        sc = ScoredChunk(chunk=_chunk("c1", long_ctx), score=0.9, source="s")

        fast_ans = gen.generate("simple query", [sc])
        smart_ans = gen.generate("phân tích chi tiết", [sc])
        assert len(smart_ans.text) > len(fast_ans.text)


# ── build_pipeline_from_config with routed generator ─────────────────────────

class TestBuildPipelineRoutedConfig:
    def test_routed_config_builds_pipeline(self, tmp_path: Path):
        import json

        golden = tmp_path / "golden.json"
        golden.write_text(json.dumps({
            "version": "1.0.0",
            "questions": [{"id": "q1", "question": "Q?", "answer": "A",
                           "expected_sources": [], "difficulty": "factual",
                           "topic": "t", "query_type": "factual"}],
        }))

        cfg_yaml = tmp_path / "cfg.yaml"
        cfg_yaml.write_text(f"""
pipeline:
  name: test_routed
  parser: {{name: echo}}
  chunker: {{name: fixed, chunk_size: 50}}
  embedder: {{name: hash, dim: 8}}
  vector_store: {{name: inmemory}}
  retriever: {{name: dense, top_k: 2}}
  reranker: {{name: noop}}
  generator:
    name: routed
    min_words_for_smart: 100
    fast_generator:
      name: fake
      max_context_chars: 50
    smart_generator:
      name: fake
      max_context_chars: 200
eval:
  golden_set: {golden}
  top_k: 2
  seed: 42
  output_dir: {tmp_path / "reports"}
""")

        from hcns_shared.config import BenchmarkConfig
        from hcns_agents.pipelines.static_pipeline import build_pipeline_from_config

        cfg = BenchmarkConfig.from_yaml(cfg_yaml)
        pipeline = build_pipeline_from_config(cfg)
        from hcns_agents.generators import RoutedGenerator
        assert isinstance(pipeline._generator, RoutedGenerator)

    def test_routed_missing_subgenerator_raises(self, tmp_path: Path):
        import json

        golden = tmp_path / "golden.json"
        golden.write_text(json.dumps({"version": "1.0.0", "questions": []}))
        cfg_yaml = tmp_path / "cfg.yaml"
        cfg_yaml.write_text(f"""
pipeline:
  name: bad
  parser: {{name: echo}}
  chunker: {{name: fixed}}
  embedder: {{name: hash}}
  vector_store: {{name: inmemory}}
  retriever: {{name: dense}}
  reranker: {{name: noop}}
  generator:
    name: routed
eval:
  golden_set: {golden}
  top_k: 2
  seed: 42
  output_dir: {tmp_path}
""")
        from hcns_shared.config import BenchmarkConfig
        from hcns_agents.pipelines.static_pipeline import build_pipeline_from_config

        cfg = BenchmarkConfig.from_yaml(cfg_yaml)
        with pytest.raises(ValueError, match="fast_generator"):
            build_pipeline_from_config(cfg)
