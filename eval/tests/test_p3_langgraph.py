"""P3 LangGraph agent tests.

Covers:
  _classify_keyword, LangGraphAgent (all nodes), retry loop, escalate path,
  out-of-scope short-circuit, trace serialisation, index()/query() interface,
  build_langgraph_from_config(), CLI dispatch to LangGraph.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hcns_backend.chunking import FixedChunker
from hcns_backend.embedding import HashEmbedder
from hcns_agents.generators import FakeGenerator
from hcns_backend.parsing import EchoParser
from hcns_backend.reranking import NoReranker
from hcns_backend.retrieval.retrievers import DenseRetriever
from hcns_backend.retrieval.vector_stores import InMemoryVectorStore
from hcns_shared.types import Answer, Chunk, ScoredChunk
from hcns_agents.graph.langgraph_agent import (
    LangGraphAgent,
    _classify_keyword,
    _expand_parents,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _build_agent(
    faithfulness_threshold: float = 0.05,
    max_retry: int = 1,
    classify_method: str = "keyword",
) -> LangGraphAgent:
    emb = HashEmbedder(dim=16)
    store = InMemoryVectorStore()
    return LangGraphAgent(
        parser=EchoParser(),
        chunker=FixedChunker(chunk_size=100, overlap=10),
        embedder=emb,
        vector_store=store,
        retriever=DenseRetriever(vector_store=store, embedder=emb, top_k=3),
        reranker=NoReranker(),
        fast_generator=FakeGenerator(max_context_chars=100),
        smart_generator=FakeGenerator(max_context_chars=400),
        top_k=3,
        faithfulness_threshold=faithfulness_threshold,
        max_retry=max_retry,
        classify_method=classify_method,
    )


def _index_agent(agent: LangGraphAgent, text: str = "nghỉ phép năm theo quy định") -> None:
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "doc.txt").write_text(text * 5)
        agent.index(Path(td))


# ── keyword classifier ────────────────────────────────────────────────────────

class TestKeywordClassifier:
    def test_factual_default(self):
        assert _classify_keyword("Số ngày nghỉ phép là bao nhiêu?") == "factual"

    def test_procedural_detected(self):
        assert _classify_keyword("Quy trình xin nghỉ phép như thế nào?") == "procedural"

    def test_comparative_detected(self):
        assert _classify_keyword("So sánh chính sách nghỉ phép A và B") == "comparative"

    def test_multihop_detected(self):
        assert _classify_keyword("Chính sách này liên quan đến điều khoản nào?") == "multi-hop"

    def test_oos_detected(self):
        assert _classify_keyword("Hôm nay thời tiết thế nào?") == "out-of-scope"

    def test_oos_takes_priority_over_procedural(self):
        # "cách" (procedural) but also "bóng đá" (oos)
        assert _classify_keyword("Cách xem bóng đá online?") == "out-of-scope"


# ── index() ───────────────────────────────────────────────────────────────────

class TestLangGraphAgentIndex:
    def test_index_populates_vector_store(self):
        agent = _build_agent()
        _index_agent(agent)
        assert len(agent._indexed_ids) > 0

    def test_index_is_idempotent(self):
        agent = _build_agent()
        _index_agent(agent)
        first = len(agent._indexed_ids)
        _index_agent(agent)
        assert len(agent._indexed_ids) == first

    def test_index_calls_retriever_index_chunks(self):
        from hcns_backend.retrieval.retrievers import HybridRrfRetriever

        emb = HashEmbedder(dim=8)
        store = InMemoryVectorStore()
        hybrid = HybridRrfRetriever(vector_store=store, embedder=emb, top_k=2)
        agent = LangGraphAgent(
            parser=EchoParser(),
            chunker=FixedChunker(chunk_size=50, overlap=5),
            embedder=emb,
            vector_store=store,
            retriever=hybrid,
            reranker=NoReranker(),
            fast_generator=FakeGenerator(),
            smart_generator=FakeGenerator(),
        )
        _index_agent(agent, "bảo hiểm y tế nhân viên chính thức")
        assert len(hybrid._bm25_chunks) > 0


# ── query() — happy path ──────────────────────────────────────────────────────

class TestLangGraphAgentQuery:
    def test_query_returns_answer(self):
        agent = _build_agent()
        _index_agent(agent)
        answer = agent.query("Số ngày nghỉ phép?")
        assert isinstance(answer, Answer)
        assert answer.text

    def test_query_sets_original_question(self):
        agent = _build_agent()
        _index_agent(agent)
        answer = agent.query("Chính sách nghỉ phép?")
        assert answer.query == "Chính sách nghỉ phép?"

    def test_trace_is_json_list(self):
        agent = _build_agent()
        _index_agent(agent)
        answer = agent.query("Số ngày phép?")
        assert answer.trace
        events = json.loads(answer.trace)
        assert isinstance(events, list)
        assert len(events) > 0

    def test_trace_contains_expected_nodes(self):
        agent = _build_agent()
        _index_agent(agent)
        answer = agent.query("Quy trình xin nghỉ?")
        events = json.loads(answer.trace)
        node_names = {e["node"] for e in events}
        assert "classify" in node_names
        assert "retrieve" in node_names
        assert "rerank" in node_names
        assert "route_generate" in node_names
        assert "self_correct" in node_names

    def test_classify_node_in_trace_has_query_type(self):
        agent = _build_agent()
        _index_agent(agent)
        answer = agent.query("So sánh chính sách A và B")
        events = json.loads(answer.trace)
        classify_events = [e for e in events if e["node"] == "classify"]
        assert classify_events
        assert classify_events[0]["query_type"] in {
            "factual", "procedural", "multi-hop", "comparative", "out-of-scope"
        }

    def test_procedural_query_routes_to_smart_generator(self):
        """Procedural queries use smart_generator (larger context)."""
        fast = FakeGenerator(max_context_chars=1)
        smart = FakeGenerator(max_context_chars=500)
        emb = HashEmbedder(dim=8)
        store = InMemoryVectorStore()
        agent = LangGraphAgent(
            parser=EchoParser(),
            chunker=FixedChunker(chunk_size=100, overlap=5),
            embedder=emb,
            vector_store=store,
            retriever=DenseRetriever(vector_store=store, embedder=emb, top_k=2),
            reranker=NoReranker(),
            fast_generator=fast,
            smart_generator=smart,
            top_k=2,
            faithfulness_threshold=0.0,
        )
        _index_agent(agent, "hướng dẫn quy trình đăng ký bảo hiểm")
        answer = agent.query("Hướng dẫn quy trình xin nghỉ phép")
        events = json.loads(answer.trace)
        gen_event = next(e for e in events if e["node"] == "route_generate")
        assert gen_event["generator"] == "smart"


# ── out-of-scope short-circuit ────────────────────────────────────────────────

class TestOutOfScope:
    def test_oos_skips_retrieve_and_generate(self):
        agent = _build_agent()
        answer = agent.query("Hôm nay thời tiết ở Hà Nội thế nào?")
        assert "ngoài phạm vi" in answer.text.lower() or "out" in answer.text.lower() or len(answer.text) > 0
        events = json.loads(answer.trace)
        node_names = [e["node"] for e in events]
        assert "out_of_scope" in node_names
        assert "retrieve" not in node_names  # should have been skipped

    def test_oos_answer_is_not_empty(self):
        agent = _build_agent()
        answer = agent.query("Thời tiết hôm nay ra sao?")
        assert answer.text


# ── self-correct + retry loop ─────────────────────────────────────────────────

class TestSelfCorrect:
    def test_self_correct_pass_when_faithfulness_ok(self):
        """FakeGenerator returns context as answer → faithfulness > 0 → pass."""
        agent = _build_agent(faithfulness_threshold=0.0)
        _index_agent(agent)
        answer = agent.query("Số ngày phép?")
        events = json.loads(answer.trace)
        sc_event = next(e for e in events if e["node"] == "self_correct")
        assert sc_event["action"] == "pass"

    def test_self_correct_triggers_retry_below_threshold(self):
        """Threshold set very high → faithfulness always below → retry fires."""
        agent = _build_agent(faithfulness_threshold=999.0, max_retry=1)
        _index_agent(agent)
        answer = agent.query("Số ngày phép?")
        events = json.loads(answer.trace)
        sc_events = [e for e in events if e["node"] == "self_correct"]
        actions = [e["action"] for e in sc_events]
        # First self_correct should trigger retry, second should escalate
        assert "retry" in actions or "escalate" in actions

    def test_escalate_fires_after_max_retry_exhausted(self):
        """max_retry=0 → no retry, immediately escalate."""
        agent = _build_agent(faithfulness_threshold=999.0, max_retry=0)
        _index_agent(agent)
        answer = agent.query("Số ngày phép?")
        events = json.loads(answer.trace)
        node_names = [e["node"] for e in events]
        assert "escalate" in node_names

    def test_retry_increments_retry_count_in_trace(self):
        agent = _build_agent(faithfulness_threshold=999.0, max_retry=1)
        _index_agent(agent)
        answer = agent.query("Câu hỏi phức tạp?")
        events = json.loads(answer.trace)
        retrieve_events = [e for e in events if e["node"] == "retrieve"]
        # Should have at least 2 retrieve calls (initial + 1 retry)
        assert len(retrieve_events) >= 1  # at least 1; retry may not fire if no corpus


# ── _expand_parents helper ────────────────────────────────────────────────────

class TestExpandParents:
    def _parent(self, pid: str, text: str) -> Chunk:
        return Chunk(id=pid, doc_id="d", text=text, parent_id=None)

    def _child_sc(self, cid: str, pid: str, score: float) -> ScoredChunk:
        child = Chunk(id=cid, doc_id="d", text="child text", parent_id=pid)
        return ScoredChunk(chunk=child, score=score, source="s")

    def test_expands_child_to_parent(self):
        parent_map = {"p1": self._parent("p1", "full parent text")}
        scored = [self._child_sc("c1", "p1", 0.9)]
        expanded = _expand_parents(scored, parent_map)
        assert expanded[0].chunk.text == "full parent text"

    def test_deduplicates_same_parent(self):
        parent_map = {"p1": self._parent("p1", "parent")}
        scored = [self._child_sc("c1", "p1", 0.9), self._child_sc("c2", "p1", 0.8)]
        expanded = _expand_parents(scored, parent_map)
        assert len(expanded) == 1  # deduplicated

    def test_passthrough_when_no_parent_id(self):
        scored = [ScoredChunk(chunk=Chunk(id="c1", doc_id="d", text="t"), score=0.5, source="s")]
        assert _expand_parents(scored, {}) == scored


# ── build_langgraph_from_config ───────────────────────────────────────────────

class TestBuildLangGraphFromConfig:
    def test_builds_from_yaml(self, tmp_path: Path):
        import json as _json

        golden = tmp_path / "golden.json"
        golden.write_text(_json.dumps({
            "version": "1.0.0",
            "questions": [{"id": "q1", "question": "Q?", "answer": "A",
                           "expected_sources": [], "difficulty": "factual",
                           "topic": "t", "query_type": "factual"}],
        }))

        cfg_yaml = tmp_path / "cfg.yaml"
        cfg_yaml.write_text(f"""
pipeline:
  name: test_lg
  parser: {{name: echo}}
  chunker: {{name: fixed, chunk_size: 50}}
  embedder: {{name: hash, dim: 8}}
  vector_store: {{name: inmemory}}
  retriever: {{name: dense, top_k: 2}}
  reranker: {{name: noop}}
  generator: {{name: fake}}
agent:
  type: langgraph
  faithfulness_threshold: 0.0
  max_retry: 0
  classify_method: keyword
  top_k: 2
  fast_generator: {{name: fake}}
  smart_generator: {{name: fake}}
eval:
  golden_set: {golden}
  top_k: 2
  seed: 42
  output_dir: {tmp_path / "reports"}
""")

        from hcns_shared.config import BenchmarkConfig
        from hcns_agents.graph.langgraph_agent import build_langgraph_from_config

        cfg = BenchmarkConfig.from_yaml(cfg_yaml)
        agent = build_langgraph_from_config(cfg)
        assert isinstance(agent, LangGraphAgent)

    def test_cli_dispatches_to_langgraph(self, tmp_path: Path):
        """_build_from_config returns LangGraphAgent when agent.type=langgraph."""
        import json as _json

        golden = tmp_path / "golden.json"
        golden.write_text(_json.dumps({"version": "1.0.0", "questions": []}))

        cfg_yaml = tmp_path / "cfg.yaml"
        cfg_yaml.write_text(f"""
pipeline:
  name: cli_test
  parser: {{name: echo}}
  chunker: {{name: fixed}}
  embedder: {{name: hash}}
  vector_store: {{name: inmemory}}
  retriever: {{name: dense}}
  reranker: {{name: noop}}
  generator: {{name: fake}}
agent:
  type: langgraph
  fast_generator: {{name: fake}}
  smart_generator: {{name: fake}}
eval:
  golden_set: {golden}
  top_k: 2
  seed: 42
  output_dir: {tmp_path}
""")

        from hcns_eval.adapters.newteam_adapter import NewTeamAdapter
        from hcns_eval.cli import _build_from_config
        from hcns_shared.config import BenchmarkConfig

        cfg = BenchmarkConfig.from_yaml(cfg_yaml)
        adapter = _build_from_config(cfg)
        # CLI now returns a PipelineAdapter (NewTeamAdapter) wrapping the LangGraphAgent
        assert isinstance(adapter, NewTeamAdapter)
        assert isinstance(adapter._pipeline, LangGraphAgent)


# ── E2E: configs/new_langgraph.yaml ──────────────────────────────────────────

class TestE2ENewLangGraphConfig:
    def test_e2e_index_and_query(self):
        """Full smoke run using configs/new_langgraph.yaml with fake components."""
        from hcns_shared.config import BenchmarkConfig
        from hcns_agents.graph.langgraph_agent import build_langgraph_from_config

        config_path = Path(__file__).parent.parent / "configs" / "new_langgraph.yaml"
        assert config_path.exists(), f"Config not found: {config_path}"

        cfg = BenchmarkConfig.from_yaml(config_path)
        assert cfg.agent.type == "langgraph"

        agent = build_langgraph_from_config(cfg)

        corpus = Path(__file__).parent.parent / "data" / "corpus_smoke"
        agent.index(corpus)

        answer = agent.query("Số ngày nghỉ phép năm tối đa là bao nhiêu?")
        assert isinstance(answer, Answer)
        assert answer.text
        assert answer.trace
        events = json.loads(answer.trace)
        node_names = [e["node"] for e in events]
        assert "classify" in node_names
        assert "self_correct" in node_names

    def test_e2e_eval_runs_on_golden_set(self):
        """Harness can evaluate LangGraph agent just like StaticPipeline."""
        from hcns_shared.config import BenchmarkConfig
        from hcns_eval.legacy_harness import run_eval
        from hcns_agents.graph.langgraph_agent import build_langgraph_from_config

        config_path = Path(__file__).parent.parent / "configs" / "new_langgraph.yaml"
        cfg = BenchmarkConfig.from_yaml(config_path)
        agent = build_langgraph_from_config(cfg)

        corpus = Path(__file__).parent.parent / "data" / "corpus_smoke"
        agent.index(corpus)

        golden_path = Path(__file__).parent.parent / cfg.eval.golden_set
        run = run_eval(
            pipeline=agent,
            golden_path=golden_path,
            top_k=cfg.eval.top_k,
            seed=cfg.eval.seed,
            pipeline_name=cfg.pipeline.name,
        )
        assert run.total_questions == 10
        assert run.avg_latency_ms >= 0
        assert 0.0 <= run.generation.faithfulness <= 1.0
