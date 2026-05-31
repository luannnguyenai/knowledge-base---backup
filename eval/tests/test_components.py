"""Unit tests for stub component implementations."""
import tempfile
from pathlib import Path

import pytest

from ragbench.components.chunkers import FixedChunker
from ragbench.components.embedders import HashEmbedder
from ragbench.components.generators import FakeGenerator
from ragbench.components.parsers import EchoParser
from ragbench.components.rerankers import NoReranker
from ragbench.components.retrievers import DenseRetriever
from ragbench.components.vector_stores import InMemoryVectorStore
from ragbench.core.types import Chunk, Document, ScoredChunk


# ── Parser ─────────────────────────────────────────────────────────────────────

def test_echo_parser_single_file():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Hello world")
        path = Path(f.name)
    docs = EchoParser().parse(path)
    assert len(docs) == 1
    assert docs[0].text == "Hello world"
    assert docs[0].metadata["filename"] == path.name


def test_echo_parser_directory():
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "a.txt").write_text("aaa")
        (Path(td) / "b.txt").write_text("bbb")
        docs = EchoParser().parse(Path(td))
    assert len(docs) == 2


# ── Chunker ────────────────────────────────────────────────────────────────────

def test_fixed_chunker_splits():
    doc = Document(id="d1", text="x" * 600)
    chunks = FixedChunker(chunk_size=200, overlap=0).chunk([doc])
    assert len(chunks) == 3  # 600 / 200 = 3
    assert all(c.doc_id == "d1" for c in chunks)


def test_fixed_chunker_overlap():
    doc = Document(id="d1", text="a" * 300)
    chunks = FixedChunker(chunk_size=200, overlap=100).chunk([doc])
    # step = 100, so windows at 0, 100, 200 → 3 chunks
    assert len(chunks) == 3


# ── Embedder ──────────────────────────────────────────────────────────────────

def test_hash_embedder_dimension():
    vecs = HashEmbedder(dim=64).embed(["hello", "world"])
    assert len(vecs) == 2
    assert all(len(v) == 64 for v in vecs)


def test_hash_embedder_deterministic():
    e = HashEmbedder(dim=32)
    assert e.embed(["test"])[0] == e.embed(["test"])[0]


def test_hash_embedder_different_texts():
    e = HashEmbedder(dim=32)
    assert e.embed(["foo"])[0] != e.embed(["bar"])[0]


# ── VectorStore ───────────────────────────────────────────────────────────────

def _make_chunk(cid: str, text: str = "x") -> Chunk:
    return Chunk(id=cid, doc_id="d", text=text)


def test_inmemory_upsert_and_search():
    store = InMemoryVectorStore()
    emb = HashEmbedder(dim=16)
    chunks = [_make_chunk("c1", "nghỉ phép"), _make_chunk("c2", "bảo hiểm")]
    vecs = emb.embed([c.text for c in chunks])
    store.upsert(chunks, vecs)

    q_vec = emb.embed(["nghỉ phép"])[0]
    results = store.search(q_vec, top_k=2)
    assert len(results) == 2
    assert results[0].chunk.id == "c1"  # exact match should rank first


def test_inmemory_empty_search():
    assert InMemoryVectorStore().search([0.0] * 16, top_k=3) == []


# ── Retriever ─────────────────────────────────────────────────────────────────

def test_dense_retriever_returns_scored_chunks():
    store = InMemoryVectorStore()
    emb = HashEmbedder(dim=16)
    chunks = [_make_chunk(f"c{i}", f"text {i}") for i in range(5)]
    vecs = emb.embed([c.text for c in chunks])
    store.upsert(chunks, vecs)

    ret = DenseRetriever(vector_store=store, embedder=emb, top_k=3)
    results = ret.retrieve("text 2", top_k=3)
    assert len(results) == 3
    assert all(isinstance(r, ScoredChunk) for r in results)


# ── Reranker ──────────────────────────────────────────────────────────────────

def test_noop_reranker_passthrough():
    scored = [ScoredChunk(chunk=_make_chunk("c1"), score=0.9, source="s")]
    assert NoReranker().rerank("q", scored) == scored


def test_noop_reranker_top_k():
    scored = [ScoredChunk(chunk=_make_chunk(f"c{i}"), score=float(i), source="s") for i in range(5)]
    result = NoReranker().rerank("q", scored, top_k=2)
    assert len(result) == 2


# ── Generator ─────────────────────────────────────────────────────────────────

def test_fake_generator_joins_context():
    scored = [ScoredChunk(chunk=_make_chunk("c1", "hello world"), score=1.0, source="s")]
    ans = FakeGenerator(max_context_chars=50).generate("question?", scored)
    assert "hello world" in ans.text
    assert ans.query == "question?"
    assert "c1" in ans.citations


def test_fake_generator_no_context():
    ans = FakeGenerator().generate("q?", [])
    assert ans.text == "[no context]"
