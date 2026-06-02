# RAGBench Comparison Report

**Generated:** 2026-06-01T01:47:53.085439+00:00  
**Golden Set Version:** 1.0.0  
**Questions:** 10  
**Pipelines:** `smoke_fake_pipeline`, `new_langgraph`  

---

## Metrics

| Metric | smoke_fake_pipeline | new_langgraph | Delta | Winner |
| --- | --- | --- | --- | --- |
| **Retrieval** |  |  |  |  |
| `Recall@k` | 0.0000 | 0.0000 | +0.0000 | tie |
| `Precision@k` | 0.0000 | 0.0000 | +0.0000 | tie |
| `MRR` | 0.0000 | 0.0000 | +0.0000 | tie |
| `NDCG@k` | 0.0000 | 0.0000 | +0.0000 | tie |
| **Generation (LLM-judged)** |  |  |  |  |
| `Faithfulness` | 0.0000 | 0.0000 | +0.0000 | tie |
| `Answer Relevancy` | 0.0000 | 0.0000 | +0.0000 | tie |
| `Context Precision` | 0.0000 | 0.0000 | +0.0000 | tie |
| `Correctness` | 0.0000 | 0.0000 | +0.0000 | tie |
| `Hallucination Rate ↓` | 0.0000 | 0.0000 | +0.0000 | tie |
| **Efficiency** |  |  |  |  |
| `Avg Latency (ms) ↓` | 0.0708 | 6.0349 | +5.9641 | 🏆 smoke_fake_pipeline |
| `Total Cost (USD) ↓` | 0.0000 | 0.0000 | +0.0000 | tie |

---

## Win / Loss Summary

| Pipeline | Wins | Losses | Ties |
| --- | --- | --- | --- |
| `smoke_fake_pipeline` | 1 | 0 | 10 |
| `new_langgraph` | 0 | 1 | 10 |

---

## Run Manifests

### `smoke_fake_pipeline`

- **Config hash:** `c0fec63f78c2f0dd`
- **Git SHA:** `ffb2656c`
- **Data version:** `1.0.0`
- **Data hash:** `9d1cb77f16f877a7`
- **Judge model:** `gpt-4o`
- **Judge prompt version:** `1.0.0`
- **RAGBench version:** `0.1.0`
- **Timestamp:** `2026-06-01T01:47:52.666751+00:00`

### `new_langgraph`

- **Config hash:** `dfc114c38cdce736`
- **Git SHA:** `ffb2656c`
- **Data version:** `1.0.0`
- **Data hash:** `9d1cb77f16f877a7`
- **Judge model:** `gpt-4o`
- **Judge prompt version:** `1.0.0`
- **RAGBench version:** `0.1.0`
- **Timestamp:** `2026-06-01T01:47:53.022423+00:00`
