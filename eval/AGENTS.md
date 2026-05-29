# AGENTS.md — Evaluation Framework Conventions

`eval/` is an **independent deliverable** — pipeline-agnostic evaluation framework that runs on any pipeline (baseline, team mới) via the adapter pattern.

## Structure

```
eval/
├── AGENTS.md
├── README.md
├── datasets/
│   ├── golden/          # Golden set Q&A (versioned JSON, provided later)
│   └── raw/             # Raw data (provided later)
├── adapters/            # baseline_adapter, newteam_adapter
├── harness/             # Runner — executes eval on golden set
├── metrics/             # Retrieval + generation metric definitions
├── judges/              # LLM-as-judge configs
├── reports/             # Benchmark + ablation outputs
└── pyproject.toml
```

## Core Principles

1. **Pipeline-agnostic:** Eval knows nothing about pipeline internals. It only calls the adapter interface.
2. **Reproducible:** Every eval run records seed, data version, model version.
3. **Two-tier metrics:** Retrieval metrics + Generation metrics, reported separately.
4. **Regression gate:** CI blocks merge if metrics drop below threshold.

## Adapter Interface

Both `baseline_adapter` and `newteam_adapter` implement:

```python
class PipelineAdapter(Protocol):
    def retrieve(self, query: str, k: int = 5) -> list[ScoredChunk]: ...
    def generate(self, query: str, context: list[Chunk]) -> Answer: ...
    def ingest(self, source: str) -> list[Document]: ...  # optional for eval
```

## Golden Set Schema

```json
{
  "version": "1.0.0",
  "questions": [
    {
      "id": "q001",
      "question": "string",
      "answer": "string",
      "expected_sources": ["source_id_1", "source_id_2"],
      "difficulty": "factual | procedural | multi-hop | comparative | edge | out-of-scope",
      "topic": "string",
      "query_type": "factual | procedural | multi-hop | comparative | out-of-scope"
    }
  ]
}
```

## Metric Definitions

### Retrieval
- **Recall@k:** Fraction of relevant sources found in top-k
- **Context Precision:** Fraction of retrieved context that is relevant
- **MRR:** Mean Reciprocal Rank
- **NDCG@k:** Normalized Discounted Cumulative Gain

### Generation
- **Faithfulness:** Answer grounded in context (no hallucination)
- **Answer Relevancy:** Answer addresses the question
- **Correctness:** Answer matches ground truth
- **Hallucination rate:** Fraction of answers with fabricated info

## Running Eval

```bash
# Run on golden set
python -m eval.harness.run --golden=datasets/golden/v1.json --adapter=newteam

# Generate comparison report
python -m eval.harness.compare --adapters=baseline,newteam --output=reports/comparison.md

# Check regression thresholds
python -m eval.harness.check_regression --report=reports/latest.json
```

## Testing

- Unit tests for each metric calculator
- Integration tests with mock adapter
- Golden set validation (schema check before run)
