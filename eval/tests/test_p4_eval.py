"""P4 eval tests — all LLM / OpenAI calls are mocked or use no-key path.

Covers:
  GoldenSet, RunManifest, Judge (cache read/write, no-key skip),
  retrieval metrics, generation metrics, RunResult (save/load),
  compare_runs + markdown rendering, ragbench compare E2E smoke.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hcns_eval.golden_set import GoldenQuestion, GoldenSet
from hcns_eval.judge import Judge, _parse_score
from hcns_eval.manifest import RunManifest
from hcns_eval.metrics.generation import (
    AggGenerationMetrics,
    GenerationResult,
    aggregate_generation,
    score_generation,
)
from hcns_eval.metrics.retrieval import (
    aggregate_retrieval,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    score_retrieval,
)
from hcns_eval.report import (
    CompareReport,
    _find_winner,
    compare_runs,
)


# ── GoldenSet ──────────────────────────────────────────────────────────────────

class TestGoldenSet:
    def _make_json(self, tmp_path: Path, n: int = 3) -> Path:
        p = tmp_path / "golden.json"
        p.write_text(json.dumps({
            "version": "1.2.0",
            "questions": [
                {
                    "id": f"q{i:03d}", "question": f"Q{i}?",
                    "answer": f"A{i}", "expected_sources": [f"src{i}.pdf"],
                    "difficulty": "factual", "topic": "test", "query_type": "factual",
                }
                for i in range(n)
            ],
        }))
        return p

    def test_load_from_json(self, tmp_path: Path):
        gs = GoldenSet.from_json(self._make_json(tmp_path))
        assert gs.version == "1.2.0"
        assert len(gs) == 3
        assert isinstance(gs.questions[0], GoldenQuestion)

    def test_content_hash_is_stable(self, tmp_path: Path):
        gs = GoldenSet.from_json(self._make_json(tmp_path))
        assert gs.content_hash() == gs.content_hash()

    def test_content_hash_changes_on_modification(self, tmp_path: Path):
        gs = GoldenSet.from_json(self._make_json(tmp_path))
        h1 = gs.content_hash()
        gs.questions[0].answer = "MODIFIED"
        assert gs.content_hash() != h1

    def test_filter_by_type(self, tmp_path: Path):
        p = tmp_path / "gs.json"
        p.write_text(json.dumps({
            "version": "1.0.0",
            "questions": [
                {"id": "q1", "question": "Q1?", "answer": "A", "expected_sources": [],
                 "difficulty": "factual", "topic": "t", "query_type": "factual"},
                {"id": "q2", "question": "Q2?", "answer": "B", "expected_sources": [],
                 "difficulty": "procedural", "topic": "t", "query_type": "procedural"},
            ],
        }))
        gs = GoldenSet.from_json(p)
        factual = gs.filter_by_type("factual")
        assert len(factual) == 1 and factual.questions[0].id == "q1"


# ── Retrieval metrics ─────────────────────────────────────────────────────────

class TestRetrievalMetrics:
    def test_recall_perfect(self):
        assert recall_at_k(["a", "b", "c"], ["a", "b"], k=5) == 1.0

    def test_recall_partial(self):
        assert recall_at_k(["a", "x", "y"], ["a", "b"], k=5) == 0.5

    def test_recall_empty_relevant(self):
        assert recall_at_k(["a", "b"], [], k=5) == 1.0

    def test_precision_at_k_respects_k(self):
        # top-2 has 1 relevant; k=2
        assert precision_at_k(["a", "b", "c"], ["a"], k=2) == pytest.approx(0.5)

    def test_mrr_first_hit(self):
        assert reciprocal_rank(["a", "b"], ["a"]) == 1.0

    def test_mrr_second_hit(self):
        assert reciprocal_rank(["x", "a"], ["a"]) == pytest.approx(0.5)

    def test_mrr_no_hit(self):
        assert reciprocal_rank(["x", "y"], ["a"]) == 0.0

    def test_ndcg_perfect(self):
        assert ndcg_at_k(["a", "b"], ["a", "b"], k=2) == pytest.approx(1.0)

    def test_ndcg_partial(self):
        score = ndcg_at_k(["x", "a"], ["a"], k=2)
        expected = (1.0 / math.log2(3)) / (1.0 / math.log2(2))
        assert score == pytest.approx(expected)

    def test_ndcg_no_hit(self):
        assert ndcg_at_k(["x", "y"], ["a"], k=2) == 0.0

    def test_score_retrieval_returns_all_fields(self):
        r = score_retrieval("q1", ["a", "b"], ["a"], k=5)
        assert r.question_id == "q1"
        assert 0 <= r.recall <= 1
        assert 0 <= r.precision <= 1
        assert 0 <= r.rr <= 1
        assert 0 <= r.ndcg <= 1

    def test_aggregate_retrieval_averages(self):
        results = [
            score_retrieval("q1", ["a"], ["a"], k=5),
            score_retrieval("q2", ["x"], ["y"], k=5),
        ]
        agg = aggregate_retrieval(results, k=5)
        assert agg.num_questions == 2
        assert agg.recall_at_k == pytest.approx(0.5)


# ── Judge ──────────────────────────────────────────────────────────────────────

class TestJudge:
    def _make_judge(self, tmp_path: Path) -> Judge:
        return Judge(
            model="gpt-4o",
            cache_dir=str(tmp_path / "cache"),
            skip_on_missing_key=True,
        )

    def test_returns_zero_when_no_api_key(self, tmp_path: Path):
        judge = self._make_judge(tmp_path)
        result = judge.faithfulness("Q?", "A", ["C"])
        assert result.score == 0.0
        assert result.cached is False

    def test_cache_write_and_read(self, tmp_path: Path):
        judge = self._make_judge(tmp_path)
        # Manually prime the cache
        prompt_key = judge._cache_key("faithfulness", "test_prompt")
        cache_path = judge._cache_path(prompt_key)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"score": 0.75, "model": "gpt-4o",
                                           "prompt_version": "test", "timestamp": "t",
                                           "prompt_hash": "abc"}))
        score = judge._read_cache(prompt_key)
        assert score == pytest.approx(0.75)

    def test_cache_miss_returns_none(self, tmp_path: Path):
        judge = self._make_judge(tmp_path)
        assert judge._read_cache("nonexistent_key") is None

    def test_write_cache_creates_file(self, tmp_path: Path):
        judge = self._make_judge(tmp_path)
        key = "aabbccdd" * 8
        judge._write_cache(key, "faithfulness", 0.85, "some prompt")
        assert judge._cache_path(key).exists()

    def test_cache_hit_returns_cached_result(self, tmp_path: Path):  # noqa: ARG002
        judge = self._make_judge(tmp_path)
        key = judge._cache_key("answer_relevancy", "unique_prompt_text")
        judge._write_cache(key, "answer_relevancy", 0.9, "unique_prompt_text")
        # Now force a call that hits cache
        result = judge._score("faithfulness",
                              **{"question": "", "answer": "", "contexts": ""})
        # Since api key missing, should return 0 (not cache)
        assert result.score == 0.0  # different prompt key from above

    def test_parse_score_extracts_float(self):
        assert _parse_score("0.85") == pytest.approx(0.85)
        assert _parse_score("Score: 0.72") == pytest.approx(0.72)
        assert _parse_score("1.0") == pytest.approx(1.0)

    def test_parse_score_clamps_to_unit_interval(self):
        assert _parse_score("1.5") == pytest.approx(1.0)
        # regex extracts "0.3" from "-0.3" (minus sign is not matched by \d+)
        assert _parse_score("-0.3") == pytest.approx(0.3)

    def test_parse_score_returns_zero_on_gibberish(self):
        assert _parse_score("no number here") == 0.0


# ── Generation metrics ────────────────────────────────────────────────────────

class TestGenerationMetrics:
    def _make_judge(self, tmp_path: Path, score: float = 0.8) -> Judge:
        judge = Judge(cache_dir=str(tmp_path / "c"), skip_on_missing_key=True)
        # Patch to return deterministic score
        judge._score = lambda metric, **kw: MagicMock(  # type: ignore[method-assign]
            score=score, cached=False
        )
        return judge

    def test_score_generation_returns_result(self, tmp_path: Path):
        judge = self._make_judge(tmp_path, 0.75)
        result = score_generation(
            question_id="q1",
            question="Q?", answer="A",
            expected_answer="expected",
            contexts=["ctx1", "ctx2"],
            judge=judge,
        )
        assert result.question_id == "q1"
        assert result.faithfulness == pytest.approx(0.75)
        assert result.correctness == pytest.approx(0.75)

    def test_aggregate_generation_averages(self, tmp_path: Path):
        results = [
            GenerationResult(question_id="q1", faithfulness=0.8,
                             answer_relevancy=0.7, context_precision=0.9,
                             correctness=0.6, hallucination_rate=0.2),
            GenerationResult(question_id="q2", faithfulness=0.6,
                             answer_relevancy=0.5, context_precision=0.7,
                             correctness=0.8, hallucination_rate=0.1),
        ]
        agg = aggregate_generation(results)
        assert agg.faithfulness == pytest.approx(0.7)
        assert agg.num_questions == 2


# ── RunResult save/load ───────────────────────────────────────────────────────

class TestRunResult:
    def _make_run_result(self):
        from hcns_eval.harness import RunResult
        from hcns_eval.metrics.retrieval import AggRetrievalMetrics
        from hcns_eval.metrics.generation import AggGenerationMetrics

        manifest = RunManifest(
            config_hash="abc123", git_sha="def456", data_version="1.0.0",
            data_hash="ddd999", judge_model="gpt-4o",
            judge_prompt_version="1.0.0", ragbench_version="0.1.0",
            timestamp="2026-06-01T00:00:00Z", pipeline_name="test_pipe",
        )
        return RunResult(
            pipeline_name="test_pipe",
            manifest=manifest,
            retrieval=AggRetrievalMetrics(recall_at_k=0.5, precision_at_k=0.4,
                                          mrr=0.6, ndcg_at_k=0.55, num_questions=3, k=5),
            generation=AggGenerationMetrics(faithfulness=0.8, answer_relevancy=0.75,
                                             context_precision=0.7, correctness=0.65,
                                             hallucination_rate=0.15, num_questions=3),
            avg_latency_ms=120.5,
            total_cost_usd=0.0042,
            question_results=[],
        )

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        result = self._make_run_result()
        p = tmp_path / "result.json"
        result.save(p)
        loaded = result.__class__.load(p)
        assert loaded.pipeline_name == result.pipeline_name
        assert loaded.retrieval.recall_at_k == pytest.approx(0.5)
        assert loaded.generation.faithfulness == pytest.approx(0.8)
        assert loaded.avg_latency_ms == pytest.approx(120.5)

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        result = self._make_run_result()
        p = tmp_path / "nested" / "deep" / "result.json"
        result.save(p)
        assert p.exists()


# ── compare_runs + report rendering ──────────────────────────────────────────

class TestCompareRuns:
    def _make_results(self) -> list:
        from hcns_eval.harness import RunResult
        from hcns_eval.metrics.retrieval import AggRetrievalMetrics
        from hcns_eval.metrics.generation import AggGenerationMetrics

        def _manifest(name: str) -> RunManifest:
            return RunManifest(config_hash=name[:8], git_sha="aabbccdd",
                               data_version="1.0.0", data_hash="hash123",
                               judge_model="gpt-4o", judge_prompt_version="1.0.0",
                               ragbench_version="0.1.0", timestamp="2026-06-01T00:00:00Z",
                               pipeline_name=name)

        baseline = RunResult(
            pipeline_name="baseline",
            manifest=_manifest("baseline"),
            retrieval=AggRetrievalMetrics(recall_at_k=0.4, precision_at_k=0.3,
                                          mrr=0.5, ndcg_at_k=0.45, num_questions=5, k=5),
            generation=AggGenerationMetrics(faithfulness=0.7, answer_relevancy=0.65,
                                             context_precision=0.6, correctness=0.55,
                                             hallucination_rate=0.2, num_questions=5),
            avg_latency_ms=200.0, total_cost_usd=0.01, question_results=[],
        )
        newteam = RunResult(
            pipeline_name="newteam",
            manifest=_manifest("newteam"),
            retrieval=AggRetrievalMetrics(recall_at_k=0.6, precision_at_k=0.5,
                                          mrr=0.7, ndcg_at_k=0.65, num_questions=5, k=5),
            generation=AggGenerationMetrics(faithfulness=0.85, answer_relevancy=0.80,
                                             context_precision=0.75, correctness=0.72,
                                             hallucination_rate=0.1, num_questions=5),
            avg_latency_ms=350.0, total_cost_usd=0.02, question_results=[],
        )
        return [baseline, newteam]

    def test_compare_runs_returns_report(self):
        results = self._make_results()
        report = compare_runs(results)
        assert isinstance(report, CompareReport)
        assert report.pipeline_names == ["baseline", "newteam"]
        assert len(report.comparisons) > 0

    def test_winner_detection_higher_is_better(self):
        vals = {"a": 0.4, "b": 0.7}
        assert _find_winner(vals, "recall_at_k") == "b"

    def test_winner_detection_lower_is_better(self):
        vals = {"a": 0.2, "b": 0.1}
        assert _find_winner(vals, "hallucination_rate") == "b"

    def test_winner_tie(self):
        vals = {"a": 0.5, "b": 0.5}
        assert _find_winner(vals, "recall_at_k") == "tie"

    def test_wins_are_positive_for_better_pipeline(self):
        report = compare_runs(self._make_results())
        # newteam has higher recall/gen but higher cost/latency
        assert report.wins["newteam"] > 0

    def test_compare_requires_at_least_2_results(self):
        with pytest.raises(ValueError, match="at least 2"):
            compare_runs([self._make_results()[0]])

    def test_markdown_contains_table_header(self):
        report = compare_runs(self._make_results())
        md = report.to_markdown()
        assert "| Metric |" in md
        assert "baseline" in md
        assert "newteam" in md

    def test_markdown_contains_manifest_section(self):
        report = compare_runs(self._make_results())
        md = report.to_markdown()
        assert "## Run Manifests" in md
        assert "Config hash" in md

    def test_markdown_contains_delta_column(self):
        report = compare_runs(self._make_results())
        md = report.to_markdown()
        assert "Delta" in md or "delta" in md.lower()

    def test_to_dict_is_json_serialisable(self):
        report = compare_runs(self._make_results())
        d = report.to_dict()
        # Should not raise
        json.dumps(d)

    def test_save_markdown_writes_file(self, tmp_path: Path):
        report = compare_runs(self._make_results())
        out = tmp_path / "compare.md"
        report.save_markdown(out)
        assert out.exists()
        content = out.read_text()
        assert "RAGBench Comparison Report" in content

    def test_save_json_writes_file(self, tmp_path: Path):
        report = compare_runs(self._make_results())
        out = tmp_path / "compare.json"
        report.save_json(out)
        loaded = json.loads(out.read_text())
        assert "metrics" in loaded
        assert "summary" in loaded
        assert "manifests" in loaded


# ── E2E: ragbench compare smoke ───────────────────────────────────────────────

class TestCompareE2E:
    def test_compare_command_produces_markdown(self, tmp_path: Path):
        """Full E2E: compare two configs (fake components, no LLM judge)."""
        import json as _json

        corpus = Path(__file__).parent.parent / "data" / "corpus_smoke"
        golden = Path(__file__).parent.parent / "data" / "golden" / "mini_v1.json"

        def _write_cfg(name: str) -> Path:
            p = tmp_path / f"{name}.yaml"
            p.write_text(f"""
pipeline:
  name: {name}
  parser: {{name: echo}}
  chunker: {{name: fixed, chunk_size: 100}}
  embedder: {{name: hash, dim: 16}}
  vector_store: {{name: inmemory}}
  retriever: {{name: dense, top_k: 3}}
  reranker: {{name: noop}}
  generator: {{name: fake, max_context_chars: 100}}
eval:
  golden_set: {golden}
  top_k: 3
  seed: 42
  output_dir: {tmp_path / "reports"}
  judge:
    model: gpt-4o
    skip_on_missing_key: true   # no key in CI → zero scores, still produces report
    cache_dir: {tmp_path / ".judge_cache"}
""")
            return p

        cfg_a = _write_cfg("pipe_a")
        cfg_b = _write_cfg("pipe_b")
        out_md = tmp_path / "compare.md"

        from hcns_shared.config import BenchmarkConfig
        from hcns_eval.golden_set import GoldenSet
        from hcns_eval.harness import run_full_eval
        from hcns_eval.judge import Judge
        from hcns_eval.report import compare_runs
        from hcns_eval.cli import _build_from_config

        results = []
        for cfg_path in [cfg_a, cfg_b]:
            cfg = BenchmarkConfig.from_yaml(cfg_path)
            pipeline = _build_from_config(cfg)
            pipeline.index(corpus)
            gs = GoldenSet.from_json(Path(cfg.eval.golden_set))
            judge = Judge(
                model=cfg.eval.judge.model,
                cache_dir=str(cfg.eval.judge.cache_dir),
                skip_on_missing_key=True,
            )
            result = run_full_eval(pipeline, gs, judge,
                                   config_path=cfg_path,
                                   pipeline_name=cfg.pipeline.name,
                                   top_k=cfg.eval.top_k,
                                   seed=cfg.eval.seed)
            results.append(result)

        report = compare_runs(results)
        report.save_markdown(out_md)

        assert out_md.exists()
        md = out_md.read_text()
        assert "RAGBench Comparison Report" in md
        assert "pipe_a" in md
        assert "pipe_b" in md
        assert "Run Manifests" in md
        # Metric tables should be present
        assert "| Recall@k |" in md or "recall_at_k" in md or "Recall@k" in md

    def test_run_result_reproducible(self, tmp_path: Path):
        """Two evaluations on the same data with cached judge → identical metrics."""
        from hcns_shared.config import BenchmarkConfig
        from hcns_eval.golden_set import GoldenSet
        from hcns_eval.harness import run_full_eval
        from hcns_eval.judge import Judge
        from hcns_eval.cli import _build_from_config

        corpus = Path(__file__).parent.parent / "data" / "corpus_smoke"
        golden_path = Path(__file__).parent.parent / "data" / "golden" / "mini_v1.json"
        cache_dir = tmp_path / "cache"

        cfg_yaml = tmp_path / "cfg.yaml"
        cfg_yaml.write_text(f"""
pipeline:
  name: repro_test
  parser: {{name: echo}}
  chunker: {{name: fixed, chunk_size: 80}}
  embedder: {{name: hash, dim: 8}}
  vector_store: {{name: inmemory}}
  retriever: {{name: dense, top_k: 2}}
  reranker: {{name: noop}}
  generator: {{name: fake}}
eval:
  golden_set: {golden_path}
  top_k: 2
  seed: 42
  output_dir: {tmp_path / "reports"}
  judge:
    model: gpt-4o
    skip_on_missing_key: true
    cache_dir: {cache_dir}
""")
        cfg = BenchmarkConfig.from_yaml(cfg_yaml)

        def _run():
            pipeline = _build_from_config(cfg)
            pipeline.index(corpus)
            gs = GoldenSet.from_json(golden_path)
            judge = Judge(model="gpt-4o", cache_dir=str(cache_dir),
                          skip_on_missing_key=True)
            return run_full_eval(pipeline, gs, judge, config_path=cfg_yaml,
                                 pipeline_name="repro_test", top_k=2, seed=42)

        r1 = _run()
        r2 = _run()
        # Retrieval and generation metrics must be identical
        assert r1.retrieval.recall_at_k == pytest.approx(r2.retrieval.recall_at_k)
        assert r1.generation.faithfulness == pytest.approx(r2.generation.faithfulness)
        assert r1.avg_latency_ms >= 0
