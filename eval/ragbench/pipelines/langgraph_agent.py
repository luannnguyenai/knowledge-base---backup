"""LangGraph-based RAG agent pipeline.

State graph topology
--------------------
START → classify → [conditional]
    out-of-scope → handle_oos → END
    factual/procedural/multi-hop/comparative → retrieve → rerank
                                                            ↓
                                                     route_generate
                                                            ↓
                                                     self_correct → [conditional]
                                                        pass     → END
                                                        retry    → retrieve  (loop, max_retry times)
                                                        escalate → escalate_node → END

Design constraints (from spec)
-------------------------------
- Nodes ONLY call shared components via build() — no direct implementation imports.
- Same index()/query() interface as StaticPipeline.
- Every node appends a trace event to AgentState.trace_events.
- Answer.trace receives the serialised trace_events list (JSON string).
"""
from __future__ import annotations

import json
import operator
import re
import time
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

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
from ragbench.metrics import token_overlap_score

# ── Query-type keywords (used by keyword classifier) ─────────────────────────

_PROCEDURAL_KW = [
    "quy trình", "các bước", "làm thế nào", "cách", "hướng dẫn",
    "step", "how to", "thủ tục",
]
_MULTIHOP_KW = [
    "liên quan đến", "ảnh hưởng", "dựa trên", "từ đó",
    "ngoài ra còn", "kết hợp với",
]
_COMPARATIVE_KW = [
    "so sánh", "khác nhau", "ưu nhược điểm", "giống nhau",
    "hơn hay kém", "tốt hơn", "bằng nhau",
]
_OOS_KW = [
    "thời tiết", "bóng đá", "nấu ăn", "du lịch",
    "giải trí", "âm nhạc", "phim", "chứng khoán",
]

# Strategy prompt suffixes appended to the query inside route_generate
_STRATEGY_SUFFIX: dict[str, str] = {
    "factual": "",
    "procedural": "\n(Trả lời theo từng bước rõ ràng, đánh số thứ tự.)",
    "multi-hop": "\n(Phân tích từng khía cạnh, trình bày suy luận trước khi kết luận.)",
    "comparative": "\n(Trình bày dạng bảng so sánh hoặc theo từng tiêu chí.)",
}


# ── LangGraph state ───────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """Mutable state threaded through every graph node.

    trace_events uses Annotated[list, operator.add] so each node can
    return a partial list and LangGraph will append (not replace) them.
    """
    question: str
    query_type: str | None                              # set by classify
    augmented_question: str                             # query + strategy suffix
    candidates: list[ScoredChunk]                       # from retrieve
    reranked: list[ScoredChunk]                         # from rerank
    answer: Answer | None                               # from route_generate / escalate
    retry_count: int
    correction_action: Literal["pass", "retry", "escalate"]
    trace_events: Annotated[list[dict[str, Any]], operator.add]


# ── Main agent class ──────────────────────────────────────────────────────────

class LangGraphAgent:
    """RAG agent with classify → retrieve → rerank → generate → self-correct loop.

    Params:
        parser                 -- Parser component
        chunker                -- Chunker component
        embedder               -- Embedder component
        vector_store           -- VectorStore component
        retriever              -- Retriever component
        reranker               -- Reranker component
        fast_generator         -- Generator for factual/simple queries
        smart_generator        -- Generator for complex/multi-hop/escalation
        top_k                  -- retrieval depth (default: 5)
        faithfulness_threshold -- self-correct fires below this score (default: 0.1)
        max_retry              -- max retrieve retries before escalation (default: 1)
        classify_method        -- "keyword" or "llm" (default: "keyword")
        expand_to_parent       -- expand child chunks to parent at query time (default: True)
    """

    def __init__(
        self,
        parser: Parser,
        chunker: Chunker,
        embedder: Embedder,
        vector_store: VectorStore,
        retriever: Retriever,
        reranker: Reranker,
        fast_generator: Generator,
        smart_generator: Generator,
        top_k: int = 5,
        faithfulness_threshold: float = 0.1,
        max_retry: int = 1,
        classify_method: str = "keyword",
        expand_to_parent: bool = True,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store
        self._retriever = retriever
        self._reranker = reranker
        self._fast_gen = fast_generator
        self._smart_gen = smart_generator
        self._top_k = top_k
        self._faith_threshold = faithfulness_threshold
        self._max_retry = max_retry
        self._classify_method = classify_method
        self._expand_to_parent = expand_to_parent

        # Shared with StaticPipeline pattern
        self._parent_map: dict[str, Chunk] = {}
        self._indexed_ids: set[str] = set()

        self._compiled = self._build_graph()

    # ── Public interface (same as StaticPipeline) ─────────────────────────────

    def index(self, corpus_dir: Path) -> None:
        """Parse corpus, build vector index and BM25 index (idempotent)."""
        docs = self._parser.parse(corpus_dir)
        all_chunks = self._chunker.chunk(docs)

        has_children = any(c.parent_id is not None for c in all_chunks)
        if has_children:
            parent_chunks = [c for c in all_chunks if c.parent_id is None]
            index_chunks = [c for c in all_chunks if c.parent_id is not None]
        else:
            parent_chunks = []
            index_chunks = all_chunks

        for p in parent_chunks:
            self._parent_map[p.id] = p

        new_chunks = [c for c in index_chunks if c.id not in self._indexed_ids]
        if not new_chunks:
            return

        vectors = self._embedder.embed([c.text for c in new_chunks])
        self._vector_store.upsert(new_chunks, vectors)
        self._indexed_ids.update(c.id for c in new_chunks)

        if callable(getattr(self._retriever, "index_chunks", None)):
            self._retriever.index_chunks(new_chunks)  # type: ignore[attr-defined]

    def query(self, question: str) -> Answer:
        """Run the state graph end-to-end and return an Answer with full trace."""
        initial: AgentState = {
            "question": question,
            "query_type": None,
            "augmented_question": question,
            "candidates": [],
            "reranked": [],
            "answer": None,
            "retry_count": 0,
            "correction_action": "pass",
            "trace_events": [],
        }
        result = self._compiled.invoke(initial)
        answer = result["answer"]
        if answer is None:
            answer = Answer(query=question, text="[pipeline error: no answer produced]")
        answer.trace = json.dumps(result["trace_events"], ensure_ascii=False)
        return answer

    # ── Graph nodes ───────────────────────────────────────────────────────────

    def _node_classify(self, state: AgentState) -> dict[str, Any]:
        t0 = time.perf_counter()
        question = state["question"]

        if self._classify_method == "llm":
            query_type = self._classify_with_llm(question)
        else:
            query_type = _classify_keyword(question)

        event = {
            "node": "classify",
            "query_type": query_type,
            "method": self._classify_method,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        return {
            "query_type": query_type,
            "augmented_question": question + _STRATEGY_SUFFIX.get(query_type, ""),
            "trace_events": [event],
        }

    def _node_out_of_scope(self, state: AgentState) -> dict[str, Any]:
        answer = Answer(
            query=state["question"],
            text="Câu hỏi này nằm ngoài phạm vi Knowledge Base Hành chính – Nhân sự.",
            citations=[],
            contexts=[],
        )
        return {
            "answer": answer,
            "trace_events": [{"node": "out_of_scope"}],
        }

    def _node_retrieve(self, state: AgentState) -> dict[str, Any]:
        t0 = time.perf_counter()
        query = state["augmented_question"]
        if state["retry_count"] > 0:
            # On retry, append retry signal to help retriever surface different results
            query = f"{query} (thử lại {state['retry_count']})"

        candidates = self._retriever.retrieve(query, top_k=self._top_k)
        event = {
            "node": "retrieve",
            "count": len(candidates),
            "retry": state["retry_count"],
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        return {"candidates": candidates, "trace_events": [event]}

    def _node_rerank(self, state: AgentState) -> dict[str, Any]:
        t0 = time.perf_counter()
        reranked = self._reranker.rerank(
            state["augmented_question"], state["candidates"], top_k=self._top_k
        )
        if self._expand_to_parent and self._parent_map:
            reranked = _expand_parents(reranked, self._parent_map)
        event = {
            "node": "rerank",
            "count": len(reranked),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        return {"reranked": reranked, "trace_events": [event]}

    def _node_route_generate(self, state: AgentState) -> dict[str, Any]:
        t0 = time.perf_counter()
        query_type = state["query_type"] or "factual"
        chunks = state["reranked"]
        query = state["augmented_question"]

        # Route: complex types → smart_gen; factual → fast_gen
        use_smart = query_type in ("multi-hop", "comparative", "procedural")
        gen = self._smart_gen if use_smart else self._fast_gen

        answer = gen.generate(query, chunks)
        answer.query = state["question"]  # restore original question in output

        event = {
            "node": "route_generate",
            "query_type": query_type,
            "generator": "smart" if use_smart else "fast",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        return {"answer": answer, "trace_events": [event]}

    def _node_self_correct(self, state: AgentState) -> dict[str, Any]:
        t0 = time.perf_counter()
        answer = state["answer"]
        retry_count = state["retry_count"]

        if answer is None:
            action: Literal["pass", "retry", "escalate"] = "escalate"
            faithfulness = 0.0
        else:
            contexts_text = " ".join(answer.contexts)
            faithfulness = token_overlap_score(answer.text, contexts_text)
            if faithfulness >= self._faith_threshold or not contexts_text:
                action = "pass"
            elif retry_count < self._max_retry:
                action = "retry"
            else:
                action = "escalate"

        event = {
            "node": "self_correct",
            "faithfulness": round(faithfulness, 4),
            "threshold": self._faith_threshold,
            "action": action,
            "retry_count": retry_count,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        update: dict[str, Any] = {
            "correction_action": action,
            "trace_events": [event],
        }
        if action == "retry":
            update["retry_count"] = retry_count + 1
        return update

    def _node_escalate(self, state: AgentState) -> dict[str, Any]:
        """Last-resort: call smart generator; mark answer with escalation note."""
        t0 = time.perf_counter()
        answer = self._smart_gen.generate(
            state["augmented_question"], state["reranked"]
        )
        answer.query = state["question"]
        event = {
            "node": "escalate",
            "reason": "faithfulness_below_threshold_after_max_retry",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        return {"answer": answer, "trace_events": [event]}

    # ── Routing conditions ────────────────────────────────────────────────────

    def _route_after_classify(
        self, state: AgentState
    ) -> Literal["out_of_scope", "retrieve"]:
        return "out_of_scope" if state["query_type"] == "out-of-scope" else "retrieve"

    def _route_after_correct(
        self, state: AgentState
    ) -> Literal["retrieve", "escalate", "__end__"]:
        action = state["correction_action"]
        if action == "retry":
            return "retrieve"
        if action == "escalate":
            return "escalate"
        return "__end__"

    # ── Graph construction ────────────────────────────────────────────────────

    def _build_graph(self):
        from langgraph.graph import END, START, StateGraph

        g = StateGraph(AgentState)

        # Register nodes (bound methods keep access to self._components)
        g.add_node("classify",        self._node_classify)
        g.add_node("out_of_scope",    self._node_out_of_scope)
        g.add_node("retrieve",        self._node_retrieve)
        g.add_node("rerank",          self._node_rerank)
        g.add_node("route_generate",  self._node_route_generate)
        g.add_node("self_correct",    self._node_self_correct)
        g.add_node("escalate",        self._node_escalate)

        # Edges
        g.add_edge(START, "classify")
        g.add_conditional_edges(
            "classify",
            self._route_after_classify,
            {"out_of_scope": "out_of_scope", "retrieve": "retrieve"},
        )
        g.add_edge("out_of_scope",   END)
        g.add_edge("retrieve",       "rerank")
        g.add_edge("rerank",         "route_generate")
        g.add_edge("route_generate", "self_correct")
        g.add_conditional_edges(
            "self_correct",
            self._route_after_correct,
            {"retrieve": "retrieve", "escalate": "escalate", "__end__": END},
        )
        g.add_edge("escalate", END)

        return g.compile()

    # ── LLM-based classifier (optional) ──────────────────────────────────────

    def _classify_with_llm(self, question: str) -> str:
        """Classify question type using the fast generator as an LLM oracle."""
        # Inject a dummy context chunk so the generator has something to work with
        from ragbench.core.types import Chunk as _Chunk, ScoredChunk as _SC

        prompt = (
            "Classify the following query into exactly ONE of these categories:\n"
            "factual | procedural | multi-hop | comparative | out-of-scope\n\n"
            f"Query: {question}\n\n"
            "Reply with ONLY the category label, nothing else."
        )
        dummy_chunk = _SC(
            chunk=_Chunk(id="cls", doc_id="", text="classification task"),
            score=1.0,
            source="classifier",
        )
        answer = self._fast_gen.generate(prompt, [dummy_chunk])
        label = answer.text.strip().lower().split()[0] if answer.text.strip() else ""
        valid = {"factual", "procedural", "multi-hop", "comparative", "out-of-scope"}
        return label if label in valid else _classify_keyword(question)


# ── Standalone helpers ────────────────────────────────────────────────────────

def _classify_keyword(question: str) -> str:
    """Rule-based query type classifier — fast, zero API cost."""
    lower = question.lower()
    if any(kw in lower for kw in _OOS_KW):
        return "out-of-scope"
    if any(kw in lower for kw in _COMPARATIVE_KW):
        return "comparative"
    if any(kw in lower for kw in _MULTIHOP_KW):
        return "multi-hop"
    if any(kw in lower for kw in _PROCEDURAL_KW):
        return "procedural"
    return "factual"


def _expand_parents(
    scored: list[ScoredChunk],
    parent_map: dict[str, Chunk],
) -> list[ScoredChunk]:
    """Replace child ScoredChunks with their parent for richer context (same as StaticPipeline)."""
    seen: set[str] = set()
    expanded: list[ScoredChunk] = []
    for sc in scored:
        pid = sc.chunk.parent_id
        if pid and pid in parent_map:
            if pid in seen:
                continue
            seen.add(pid)
            expanded.append(ScoredChunk(chunk=parent_map[pid], score=sc.score, source=sc.source))
        else:
            expanded.append(sc)
    return expanded


# ── Factory ───────────────────────────────────────────────────────────────────

def build_langgraph_from_config(config: "BenchmarkConfig") -> LangGraphAgent:  # type: ignore[name-defined]
    """Build a LangGraphAgent from a BenchmarkConfig (agent.type must be 'langgraph').

    Shares the same registry / build() pattern as build_pipeline_from_config.
    """
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]
        load_dotenv()
    except ImportError:
        pass

    import ragbench.components  # noqa: F401  (trigger @register decorators)

    from ragbench.core.config import BenchmarkConfig
    from ragbench.core.pipeline import _build_generator
    from ragbench.core.registry import build

    pc = config.pipeline
    ac = config.agent

    embedder     = build("embedder",     pc.embedder.to_dict())
    vector_store = build("vector_store", pc.vector_store.to_dict())

    retriever_spec = pc.retriever.to_dict()
    retriever = build(
        "retriever",
        {**retriever_spec, "vector_store": vector_store, "embedder": embedder},
    )

    return LangGraphAgent(
        parser        = build("parser",  pc.parser.to_dict()),
        chunker       = build("chunker", pc.chunker.to_dict()),
        embedder      = embedder,
        vector_store  = vector_store,
        retriever     = retriever,
        reranker      = build("reranker", pc.reranker.to_dict()),
        fast_generator  = _build_generator(ac.fast_generator.to_dict()),
        smart_generator = _build_generator(ac.smart_generator.to_dict()),
        top_k                  = ac.top_k,
        faithfulness_threshold = ac.faithfulness_threshold,
        max_retry              = ac.max_retry,
        classify_method        = ac.classify_method,
    )
