"""P5 sweep & gate tests — no real API calls, no file I/O for most tests.

Covers:
  generate_combinations, apply_overrides, combo_name,
  SweepConfig, GateConfig (from_yaml),
  check_gate (pass/fail/threshold), GateResult.exit_code(),
  format_ranking_markdown, format_ablation_markdown,
  SweepResult.save/load,
  E2E: ragbench sweep smoke_sweep.yaml (fake components),
  E2E: ragbench gate pass and FAIL cases.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ragbench.sweep.config import GateConfig, MetricThreshold, SweepConfig
from ragbench.sweep.gate import _check_metric, check_gate
from ragbench.sweep.grid import apply_overrides, combo_name, generate_combinations


# ── generate_combinations ──────────────────────────────────────────────────────

class TestGenerateCombinations:
    def test_single_param(self):
        combos = generate_combinations({"a": [1, 2, 3]})
        assert len(combos) == 3
        assert combos[0] == {"a": 1}

    def test_two_params_cartesian(self):
        combos = generate_combinations({"a": [1, 2], "b": ["x", "y"]})
        assert len(combos) == 4

    def test_empty_grid_returns_one_empty(self):
        combos = generate_combinations({})
        assert combos == [{}]

    def test_max_combinations_raises(self):
        with pytest.raises(ValueError, match="max_combinations"):
            generate_combinations({"a": [1, 2, 3], "b": [4, 5, 6]}, max_combinations=5)

    def test_max_combinations_ok_at_limit(self):
        combos = generate_combinations({"a": [1, 2], "b": [3, 4]}, max_combinations=4)
        assert len(combos) == 4

    def test_order_is_cartesian_product(self):
        combos = generate_combinations({"a": [1, 2], "b": ["x", "y"]})
        expected = [
            {"a": 1, "b": "x"}, {"a": 1, "b": "y"},
            {"a": 2, "b": "x"}, {"a": 2, "b": "y"},
        ]
        assert combos == expected


# ── apply_overrides ────────────────────────────────────────────────────────────

class TestApplyOverrides:
    def test_shallow_override(self):
        base = {"a": 1, "b": 2}
        result = apply_overrides(base, {"a": 99})
        assert result == {"a": 99, "b": 2}

    def test_nested_override_dot_notation(self):
        base = {"pipeline": {"chunker": {"chunk_size": 512}}}
        result = apply_overrides(base, {"pipeline.chunker.chunk_size": 100})
        assert result["pipeline"]["chunker"]["chunk_size"] == 100

    def test_deeply_nested_creates_missing_dicts(self):
        base = {}
        result = apply_overrides(base, {"a.b.c": 42})
        assert result["a"]["b"]["c"] == 42

    def test_does_not_mutate_original(self):
        base = {"x": {"y": 1}}
        apply_overrides(base, {"x.y": 99})
        assert base["x"]["y"] == 1  # unchanged

    def test_multiple_overrides(self):
        base = {"p": {"a": 1, "b": 2}}
        result = apply_overrides(base, {"p.a": 10, "p.b": 20})
        assert result == {"p": {"a": 10, "b": 20}}


# ── combo_name ─────────────────────────────────────────────────────────────────

def test_combo_name_basic():
    name = combo_name({"pipeline.chunker.chunk_size": 200, "pipeline.retriever.top_k": 3})
    assert "chunk_size=200" in name
    assert "top_k=3" in name


def test_combo_name_truncates():
    name = combo_name({"a": "x" * 100}, max_len=10)
    assert len(name) <= 10


# ── SweepConfig ────────────────────────────────────────────────────────────────

class TestSweepConfig:
    def _write_sweep_yaml(self, tmp_path: Path) -> Path:
        base_cfg = tmp_path / "base.yaml"
        base_cfg.write_text("pipeline:\n  name: test\neval:\n  golden_set: data/golden.json\n  top_k: 3\n  seed: 42\n")
        p = tmp_path / "sweep.yaml"
        p.write_text(f"""
name: test_sweep
base_config: base.yaml
corpus: data/corpus
grid:
  pipeline.chunker.chunk_size: [100, 200]
  pipeline.retriever.top_k: [3, 5]
optimize_metric: recall_at_k
optimize_direction: maximize
""")
        return p

    def test_load_from_yaml(self, tmp_path: Path):
        p = self._write_sweep_yaml(tmp_path)
        cfg = SweepConfig.from_yaml(p)
        assert cfg.name == "test_sweep"
        assert cfg.optimize_metric == "recall_at_k"
        assert len(cfg.grid) == 2

    def test_invalid_direction_raises(self, tmp_path: Path):
        p = self._write_sweep_yaml(tmp_path)
        raw = p.read_text().replace("maximize", "invalid")
        p.write_text(raw)
        with pytest.raises(Exception):
            SweepConfig.from_yaml(p)


# ── GateConfig ────────────────────────────────────────────────────────────────

class TestGateConfig:
    def _write_gate_yaml(self, tmp_path: Path, baseline_path: Path) -> Path:
        p = tmp_path / "gate.yaml"
        p.write_text(f"""
baseline: {baseline_path}
thresholds:
  recall_at_k: 0.05
  hallucination_rate:
    max_increase: 0.05
  avg_latency_ms:
    max_increase: 300.0
""")
        return p

    def test_shorthand_expands_to_max_drop(self, tmp_path: Path):
        baseline = tmp_path / "baseline.json"
        baseline.write_text("{}")
        p = self._write_gate_yaml(tmp_path, baseline)
        cfg = GateConfig.from_yaml(p)
        assert cfg.thresholds["recall_at_k"].max_drop == pytest.approx(0.05)

    def test_expanded_form_parsed(self, tmp_path: Path):
        baseline = tmp_path / "baseline.json"
        baseline.write_text("{}")
        p = self._write_gate_yaml(tmp_path, baseline)
        cfg = GateConfig.from_yaml(p)
        assert cfg.thresholds["hallucination_rate"].max_increase == pytest.approx(0.05)
        assert cfg.thresholds["avg_latency_ms"].max_increase == pytest.approx(300.0)


# ── check_gate / GateResult ───────────────────────────────────────────────────

class TestGate:
    def _make_result(self, recall: float = 0.5, faithfulness: float = 0.8,
                     latency: float = 100.0, hallucination: float = 0.1,
                     name: str = "test") -> "RunResult":  # type: ignore[name-defined]
        from ragbench.eval.harness import RunResult
        from ragbench.eval.metrics.retrieval import AggRetrievalMetrics
        from ragbench.eval.metrics.generation import AggGenerationMetrics
        from ragbench.eval.manifest import RunManifest

        manifest = RunManifest(config_hash="abc", git_sha="def", data_version="1.0",
                               data_hash="hash", judge_model="gpt-4o",
                               judge_prompt_version="1.0", ragbench_version="0.1",
                               timestamp="t", pipeline_name=name)
        return RunResult(
            pipeline_name=name,
            manifest=manifest,
            retrieval=AggRetrievalMetrics(recall_at_k=recall, precision_at_k=recall,
                                          mrr=recall, ndcg_at_k=recall, k=5),
            generation=AggGenerationMetrics(faithfulness=faithfulness,
                                             answer_relevancy=faithfulness,
                                             context_precision=faithfulness,
                                             correctness=faithfulness,
                                             hallucination_rate=hallucination),
            avg_latency_ms=latency, total_cost_usd=0.0, question_results=[],
        )

    def _make_gate_cfg(self) -> GateConfig:
        return GateConfig(
            baseline=Path("/dev/null"),
            thresholds={
                "recall_at_k":       MetricThreshold(max_drop=0.05),
                "faithfulness":      MetricThreshold(max_drop=0.05),
                "hallucination_rate":MetricThreshold(max_increase=0.05),
                "avg_latency_ms":    MetricThreshold(max_increase=300.0),
            },
        )

    def test_gate_passes_when_metrics_equal(self):
        baseline = self._make_result(name="baseline")
        candidate = self._make_result(name="candidate")
        result = check_gate(candidate, baseline, self._make_gate_cfg())
        assert result.passed
        assert result.exit_code() == 0

    def test_gate_passes_with_improvement(self):
        baseline = self._make_result(recall=0.4, faithfulness=0.7, name="baseline")
        candidate = self._make_result(recall=0.6, faithfulness=0.9, name="candidate")
        result = check_gate(candidate, baseline, self._make_gate_cfg())
        assert result.passed

    def test_gate_fails_on_recall_drop(self):
        baseline = self._make_result(recall=0.5, name="baseline")
        candidate = self._make_result(recall=0.3, name="candidate")  # -0.2 drop > 0.05
        result = check_gate(candidate, baseline, self._make_gate_cfg())
        assert not result.passed
        assert result.exit_code() == 1
        failed_metrics = [c.metric for c in result.failed_checks]
        assert "recall_at_k" in failed_metrics

    def test_gate_fails_on_hallucination_increase(self):
        baseline = self._make_result(hallucination=0.1, name="baseline")
        candidate = self._make_result(hallucination=0.25, name="candidate")  # +0.15 > 0.05
        result = check_gate(candidate, baseline, self._make_gate_cfg())
        assert not result.passed
        failed = [c.metric for c in result.failed_checks]
        assert "hallucination_rate" in failed

    def test_gate_within_threshold_passes(self):
        baseline = self._make_result(recall=0.5, name="baseline")
        candidate = self._make_result(recall=0.47, name="candidate")  # -0.03 < 0.05 → OK
        result = check_gate(candidate, baseline, self._make_gate_cfg())
        recall_check = next(c for c in result.checks if c.metric == "recall_at_k")
        assert recall_check.passed

    def test_gate_format_report_contains_metrics(self):
        baseline = self._make_result(name="baseline")
        candidate = self._make_result(recall=0.2, name="candidate")
        result = check_gate(candidate, baseline, self._make_gate_cfg())
        report = result.format_report()
        assert "recall_at_k" in report
        assert "FAIL" in report

    def test_check_metric_max_drop(self):
        t = MetricThreshold(max_drop=0.05)
        check = _check_metric("r", 0.45, 0.5, t)  # dropped 0.05 exactly → border
        assert check.passed

    def test_check_metric_max_drop_exceeded(self):
        t = MetricThreshold(max_drop=0.05)
        check = _check_metric("r", 0.44, 0.5, t)  # dropped 0.06 > 0.05
        assert not check.passed

    def test_check_metric_min_value(self):
        t = MetricThreshold(min_value=0.3)
        check = _check_metric("r", 0.25, 0.5, t)  # below min
        assert not check.passed

    def test_check_metric_max_value(self):
        t = MetricThreshold(max_value=0.5)
        check = _check_metric("latency", 600.0, 100.0, t)  # above max
        assert not check.passed


# ── sweep report rendering ────────────────────────────────────────────────────

class TestSweepReport:
    def _make_sweep_result(self) -> "SweepResult":  # type: ignore[name-defined]
        from ragbench.sweep.runner import SweepResult, ComboResult
        from ragbench.eval.harness import RunResult
        from ragbench.eval.metrics.retrieval import AggRetrievalMetrics
        from ragbench.eval.metrics.generation import AggGenerationMetrics
        from ragbench.eval.manifest import RunManifest

        def _run(name: str, recall: float, faith: float, latency: float) -> RunResult:
            m = RunManifest(config_hash="x", git_sha="y", data_version="1.0",
                            data_hash="h", judge_model="gpt-4o", judge_prompt_version="1.0",
                            ragbench_version="0.1", timestamp="t", pipeline_name=name)
            return RunResult(
                pipeline_name=name, manifest=m,
                retrieval=AggRetrievalMetrics(recall_at_k=recall, k=5),
                generation=AggGenerationMetrics(faithfulness=faith),
                avg_latency_ms=latency, total_cost_usd=0.0, question_results=[],
            )

        combos = [
            ComboResult(rank=1, params={"pipeline.chunker.chunk_size": 200}, name="cs200",
                        run_result=_run("cs200", 0.6, 0.85, 120.0)),
            ComboResult(rank=2, params={"pipeline.chunker.chunk_size": 100}, name="cs100",
                        run_result=_run("cs100", 0.4, 0.70, 80.0)),
        ]
        return SweepResult(name="test_sweep", optimize_metric="recall_at_k",
                           optimize_direction="maximize", total_combinations=2,
                           successful_combinations=2, combos=combos, duration_s=5.2)

    def test_ranking_markdown_has_table(self):
        from ragbench.sweep.report import format_ranking_markdown
        result = self._make_sweep_result()
        md = format_ranking_markdown(result)
        assert "# Sweep: test_sweep" in md
        assert "| Rank |" in md
        assert "200" in md   # param value appears in the table row

    def test_ablation_markdown_has_per_param_section(self):
        from ragbench.sweep.report import format_ablation_markdown
        result = self._make_sweep_result()
        md = format_ablation_markdown(result)
        assert "## `chunk_size`" in md
        assert "| Value |" in md

    def test_sweep_result_to_dict_is_json_serialisable(self):
        result = self._make_sweep_result()
        d = result.to_dict()
        json.dumps(d)  # should not raise

    def test_sweep_result_save(self, tmp_path: Path):
        from ragbench.sweep.report import save_sweep_reports
        result = self._make_sweep_result()
        save_sweep_reports(result, tmp_path / "out")
        assert (tmp_path / "out" / "ranking.md").exists()
        assert (tmp_path / "out" / "ablation.md").exists()
        assert (tmp_path / "out" / "ranking.json").exists()


# ── E2E: ragbench sweep (fake components, no API keys) ────────────────────────

class TestSweepE2E:
    def test_sweep_produces_ranking_and_ablation(self, tmp_path: Path):
        """Full E2E sweep with fake components — 4 combinations."""
        corpus = Path(__file__).parent.parent / "data" / "corpus_smoke"
        golden = Path(__file__).parent.parent / "data" / "golden" / "mini_v1.json"
        base_cfg = tmp_path / "base.yaml"
        base_cfg.write_text(f"""
pipeline:
  name: sweep_test
  parser: {{name: echo}}
  chunker: {{name: fixed, chunk_size: 200, overlap: 10}}
  embedder: {{name: hash, dim: 8}}
  vector_store: {{name: inmemory}}
  retriever: {{name: dense, top_k: 3}}
  reranker: {{name: noop}}
  generator: {{name: fake}}
eval:
  golden_set: {golden}
  top_k: 3
  seed: 42
  output_dir: {tmp_path / "reports"}
  judge:
    model: gpt-4o
    skip_on_missing_key: true
    cache_dir: {tmp_path / "cache"}
""")
        sweep_yaml = tmp_path / "sweep.yaml"
        sweep_yaml.write_text(f"""
name: e2e_test
base_config: {base_cfg}
corpus: {corpus}
grid:
  pipeline.chunker.chunk_size: [100, 200]
  pipeline.retriever.top_k: [2, 3]
optimize_metric: faithfulness
optimize_direction: maximize
output_dir: {tmp_path / "reports" / "sweeps"}
""")

        from ragbench.sweep.config import SweepConfig
        from ragbench.sweep.runner import run_sweep
        from ragbench.sweep.report import save_sweep_reports

        cfg = SweepConfig.from_yaml(sweep_yaml)
        result = run_sweep(cfg)
        assert result.total_combinations == 4
        assert result.successful_combinations == 4
        assert result.best is not None

        out_dir = tmp_path / "reports" / "sweeps" / "e2e_test"
        paths = save_sweep_reports(result, out_dir)
        assert paths["ranking_md"].exists()
        assert paths["ablation_md"].exists()
        assert paths["best_result"].exists()
        ranking_md = paths["ranking_md"].read_text()
        assert "# Sweep: e2e_test" in ranking_md

    def test_gate_passes_on_identical_result(self, tmp_path: Path):  # noqa: ARG002
        """Gate with identical baseline and candidate → all checks PASS."""
        from ragbench.eval.harness import RunResult
        from ragbench.eval.metrics.retrieval import AggRetrievalMetrics
        from ragbench.eval.metrics.generation import AggGenerationMetrics
        from ragbench.eval.manifest import RunManifest
        from ragbench.sweep.gate import check_gate
        from ragbench.sweep.config import GateConfig, MetricThreshold

        m = RunManifest(config_hash="x", git_sha="y", data_version="1.0",
                        data_hash="h", judge_model="gpt-4o", judge_prompt_version="1.0",
                        ragbench_version="0.1", timestamp="t", pipeline_name="p")
        result = RunResult(
            pipeline_name="p", manifest=m,
            retrieval=AggRetrievalMetrics(recall_at_k=0.5, k=5),
            generation=AggGenerationMetrics(faithfulness=0.8),
            avg_latency_ms=100.0, total_cost_usd=0.0, question_results=[],
        )
        gate_cfg = GateConfig(
            baseline=Path("/dev/null"),
            thresholds={"recall_at_k": MetricThreshold(max_drop=0.05)},
        )
        gate_result = check_gate(result, result, gate_cfg)
        assert gate_result.passed
        assert gate_result.exit_code() == 0

    def test_gate_fails_on_degraded_result(self, tmp_path: Path):  # noqa: ARG002
        """Gate with severely degraded candidate → FAIL (exit code 1)."""
        from ragbench.eval.harness import RunResult
        from ragbench.eval.metrics.retrieval import AggRetrievalMetrics
        from ragbench.eval.metrics.generation import AggGenerationMetrics
        from ragbench.eval.manifest import RunManifest
        from ragbench.sweep.gate import check_gate
        from ragbench.sweep.config import GateConfig, MetricThreshold

        def _run(name: str, recall: float) -> RunResult:
            m = RunManifest(config_hash="x", git_sha="y", data_version="1.0",
                            data_hash="h", judge_model="gpt-4o", judge_prompt_version="1.0",
                            ragbench_version="0.1", timestamp="t", pipeline_name=name)
            return RunResult(
                pipeline_name=name, manifest=m,
                retrieval=AggRetrievalMetrics(recall_at_k=recall, k=5),
                generation=AggGenerationMetrics(),
                avg_latency_ms=100.0, total_cost_usd=0.0, question_results=[],
            )

        baseline  = _run("baseline",  recall=0.7)
        candidate = _run("candidate", recall=0.2)  # -0.5 drop >> 0.05 threshold
        gate_cfg = GateConfig(
            baseline=Path("/dev/null"),
            thresholds={"recall_at_k": MetricThreshold(max_drop=0.05)},
        )
        gate_result = check_gate(candidate, baseline, gate_cfg)
        assert not gate_result.passed
        assert gate_result.exit_code() == 1
