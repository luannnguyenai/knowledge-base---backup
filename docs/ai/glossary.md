# Glossary — HC-NS KB Agent

## Domain Terms (HC-NS)

| Term | Definition |
|------|-----------|
| **HC-NS** | Hành chính – Nhân sự (Administrative – Human Resources) |
| **Chính sách nội bộ** | Internal policies — company regulations on leave, benefits, procedures |
| **Quy định** | Regulations — formal rules employees must follow |
| **Thủ tục** | Procedures — step-by-step processes (e.g., leave request, reimbursement) |
| **Biểu mẫu** | Forms — templates for HR administrative tasks |

## Technical Terms

| Term | Definition |
|------|-----------|
| **RAG** | Retrieval-Augmented Generation — pattern where retrieved context is injected into LLM prompt |
| **Golden set** | Curated Q&A pairs with ground-truth answers and expected sources, used for eval |
| **Adapter** | Implementation of a common interface (`ingest/retrieve/generate`) that wraps a specific pipeline |
| **Hybrid search** | Combining dense (embedding similarity) and sparse (BM25/text match) retrieval, fused with RRF |
| **RRF** | Reciprocal Rank Fusion — algorithm for combining rankings from multiple retrieval sources |
| **Reranker** | Cross-encoder model that re-scores retrieved documents for higher precision |
| **Chunking** | Splitting documents into segments for embedding — parent-child keeps context hierarchy |
| **Contextual headers** | Adding section/context headers to each chunk to preserve document structure |
| **LangGraph** | Library for building stateful, multi-actor applications with LLMs — used for agent orchestration |
| **Ablation** | Experiment that removes/toggles a component to measure its contribution |
| **Regression gate** | CI check that blocks merge if eval metrics drop below threshold |

## Pipeline Components

| Component | Baseline | Team mới |
|-----------|----------|----------|
| Orchestration | Static pipeline | LangGraph state graph |
| Parse | LlamaParse / VLM | Swappable (LlamaParse / VLM / docling) |
| Chunking | Parent-Child | Parent-Child + contextual headers + structure-aware |
| Embedding | Gemini 3072d | Multi-model benchmark (Gemini / voyage / BGE-M3) |
| Retrieval | Dense-only, k=5 | Hybrid (dense+sparse, RRF) |
| Reranker | None | Cohere v3.5 / bge-reranker-v2-m3 |
| LLM | Gemini 3 Flash | Router: Flash ↔ Pro / GPT-4o / Claude |
| Eval | DeepEval | DeepEval + RAGAS |

## Metric Definitions

| Metric | Measures | Target |
|--------|----------|--------|
| **Recall@k** | Fraction of relevant documents found in top-k results | ≥ 0.90 |
| **Context Precision** | Fraction of retrieved context that is relevant | ≥ 0.75 |
| **MRR** | Mean Reciprocal Rank — quality of ranking | ≥ 0.75 |
| **NDCG@k** | Normalized Discounted Cumulative Gain at k | ≥ 0.80 |
| **Faithfulness** | Answer is grounded in retrieved context (no hallucination) | ≥ 0.90 |
| **Answer Relevancy** | Answer actually addresses the question | ≥ 0.85 |
| **Correctness** | Answer matches ground truth | ≥ 0.80 |
| **Hallucination rate** | Fraction of answers containing fabricated info | < 5% |
| **Latency P95** | 95th percentile response time | ≤ baseline |
