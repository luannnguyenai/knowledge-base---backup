# eval — Evaluation Framework (Independent Deliverable)

## Purpose

Evaluation framework độc lập, đo lường khách quan và so sánh được giữa baseline, pipeline team hiện tại, và Pipecon Nexus trên cùng bộ test. Eval tách riêng khỏi agents/ vì là deliverable cốt lõi với vòng life, owner, và CI riêng.

## Subdirectories

| Thư mục | Mục đích |
|---------|----------|
| `datasets/` | Golden set Q&A + raw data (sẽ được cung cấp sau) |
| `harness/` | Runner + adapter cho từng pipeline (baseline/team/Nexus) |
| `metrics/` | Định nghĩa metric: retrieval, generation, agent behavior |
| `judges/` | Rubric + prompt cho LLM-as-a-judge |
| `reports/` | Kết quả eval + bảng so sánh đối chứng |

## Evaluation Layers

1. **Retrieval:** Recall@k, Precision@k, MRR, nDCG, Context Relevance
2. **Generation:** Faithfulness, Answer Relevance, Correctness, Citation accuracy
3. **Agent behavior:** Task success rate, Hallucination rate, Multi-turn coherence
4. **Guardrail:** Tỷ lệ chặn đúng, False positive/negative
5. **Vận hành:** Latency p50/p95, Cost/query, Token usage

## Milestone Mapping

- **M001 (S01):** Thư mục này được tạo, chưa có code
- **M004 (Evaluation Framework):** Golden set + harness + metric definitions + báo cáo
