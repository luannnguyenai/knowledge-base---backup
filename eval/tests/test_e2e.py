"""E2E integration test: index → query using fully in-memory fake components."""
import tempfile
from pathlib import Path

from ragbench.components.chunkers import FixedChunker
from ragbench.components.embedders import HashEmbedder
from ragbench.components.generators import FakeGenerator
from ragbench.components.parsers import EchoParser
from ragbench.components.rerankers import NoReranker
from ragbench.components.retrievers import DenseRetriever
from ragbench.components.vector_stores import InMemoryVectorStore
from ragbench.core.pipeline import StaticPipeline
from ragbench.core.types import Answer


def _build_smoke_pipeline() -> StaticPipeline:
    embedder = HashEmbedder(dim=32)
    store = InMemoryVectorStore()
    retriever = DenseRetriever(vector_store=store, embedder=embedder, top_k=2)
    return StaticPipeline(
        parser=EchoParser(),
        chunker=FixedChunker(chunk_size=100, overlap=10),
        embedder=embedder,
        vector_store=store,
        retriever=retriever,
        reranker=NoReranker(),
        generator=FakeGenerator(max_context_chars=80),
        top_k=2,
    )


def test_e2e_index_and_query():
    pipeline = _build_smoke_pipeline()
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "doc.txt").write_text("Nhân viên được nghỉ phép 12 ngày mỗi năm theo quy định.")
        pipeline.index(Path(td))

    answer: Answer = pipeline.query("Số ngày nghỉ phép là bao nhiêu?")
    assert isinstance(answer, Answer)
    assert isinstance(answer.text, str) and len(answer.text) > 0
    assert answer.query == "Số ngày nghỉ phép là bao nhiêu?"
    assert answer.latency_ms >= 0


def test_e2e_from_yaml_config(tmp_path: Path):
    """Build pipeline via BenchmarkConfig.from_yaml and run eval harness."""
    import json

    from ragbench.core.config import BenchmarkConfig
    from ragbench.core.pipeline import build_pipeline_from_config
    from ragbench.harness import run_eval

    # Write minimal corpus
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "policy.txt").write_text("Nghỉ phép năm: 12 ngày. Bảo hiểm y tế áp dụng từ tháng đầu.")

    # Write minimal golden set
    golden = tmp_path / "golden.json"
    golden.write_text(json.dumps({
        "version": "1.0.0",
        "questions": [
            {
                "id": "q1",
                "question": "Số ngày nghỉ phép?",
                "answer": "12 ngày",
                "expected_sources": ["policy.txt"],
                "difficulty": "factual",
                "topic": "nghỉ phép",
                "query_type": "factual",
            }
        ],
    }), encoding="utf-8")

    # Write minimal config
    cfg_yaml = tmp_path / "test.yaml"
    cfg_yaml.write_text(f"""
pipeline:
  name: e2e_test
  parser: {{name: echo}}
  chunker: {{name: fixed, chunk_size: 100, overlap: 10}}
  embedder: {{name: hash, dim: 32}}
  vector_store: {{name: inmemory}}
  retriever: {{name: dense, top_k: 2}}
  reranker: {{name: noop}}
  generator: {{name: fake}}
eval:
  golden_set: {golden}
  top_k: 2
  seed: 42
  output_dir: {tmp_path / "reports"}
""")

    cfg = BenchmarkConfig.from_yaml(cfg_yaml)
    pipeline = build_pipeline_from_config(cfg)
    pipeline.index(corpus)

    run = run_eval(pipeline, golden, top_k=2, seed=42, pipeline_name="e2e_test")
    assert run.total_questions == 1
    assert run.avg_latency_ms >= 0
    assert 0.0 <= run.retrieval.recall_at_k <= 1.0
    assert 0.0 <= run.generation.answer_relevancy <= 1.0
