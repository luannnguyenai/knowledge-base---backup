# eval — Evaluation Framework (Independent Deliverable)

## Purpose

Evaluation framework độc lập, đo lường khách quan và so sánh được giữa baseline, pipeline team hiện tại, và Pipecon Nexus trên cùng bộ test. Eval tách riêng khỏi agents/ vì là deliverable cốt lõi với vòng life, owner, và CI riêng.

## Actual Structure

```
eval/src/hcns_eval/
├── adapters/             # Pipeline-agnostic boundary — ONLY place eval imports pipeline
│   ├── baseline_adapter.py      # StaticPipeline wrapper
│   └── newteam_adapter.py       # LangGraphAgent wrapper
├── cli.py                # Typer CLI: index, query, eval, compare, sweep, gate
├── golden_set.py         # GoldenSet + GoldenQuestion (Q&A, expected_sources, difficulty, topic)
├── judge.py              # Judge: OpenAI client + file-based cache → reproducible scoring
├── manifest.py           # RunManifest: config_hash, git_sha, data_version, judge_model, timestamp
├── harness.py            # run_full_eval() → RunResult (JSON-saveable: retrieval, generation, latency, cost)
├── report.py             # compare_runs() → CompareReport (markdown + JSON with delta/win-loss)
├── legacy_harness.py     # P0 run_eval (deprecated, kept for test compatibility)
├── legacy_metrics.py     # P0 metric functions (deprecated)
├── metrics/
│   ├── retrieval.py      # Recall@k, Precision@k, MRR, NDCG@k (k-parameterized)
│   └── generation.py     # RAGAS (faithfulness, answer_relevancy, context_precision) + DeepEval (correctness, hallucination)
└── sweep/
    ├── config.py         # SweepConfig (grid, optimize_metric), GateConfig (thresholds: max_drop/max_increase)
    ├── grid.py           # generate_combinations (Cartesian), apply_overrides (dot-notation nesting)
    ├── runner.py         # run_sweep() → SweepResult (ranked by metric, per-question breakdown)
    ├── report.py         # format_ranking_markdown, format_ablation_markdown
    └── gate.py           # check_gate() → GateResult (exit code 0/1 for CI regression detection)
```

## Key Design

| Component | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **PipelineAdapter** | Boundary between eval & pipeline (index/query) | BenchmarkConfig | RunResult |
| **Judge** | LLM-as-judge with file cache for reproducibility | question, answer, context | JudgeResult (score, cached flag) |
| **Metrics** | Per-question + aggregated retrieval & generation scores | retrieved_ids, generated_text | RetrievalResult, GenerationResult |
| **RunResult** | Complete eval run: manifest + metrics + per-question details | — | JSON serializable |
| **Sweep** | Grid search with ranking and ablation analysis | grid config, base pipeline | SweepResult (ranked combos) |
| **Gate** | Regression check: candidate vs baseline with thresholds | 2 RunResults + thresholds | GateResult (exit code) |

## Evaluation Layers (Implemented)

1. **Retrieval (P0):** Recall@k, Precision@k, MRR, NDCG@k
2. **Generation (P4):** Faithfulness, Answer Relevancy, Context Precision, Correctness, Hallucination (LLM-judged)
3. **Sweep & Ranking (P5):** Grid search, per-dimension ablation, reproducible ranking
4. **Regression Gate (P5):** Compare candidate vs baseline, exit code 0/1 for CI

## Milestone Mapping

- **M001 (S01):** Thư mục này được tạo, chưa có code
- **M004 (Evaluation Framework):** Golden set + harness + metric definitions + báo cáo
