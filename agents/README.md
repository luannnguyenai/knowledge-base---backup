# agents — LangGraph Agent Definitions, Prompts, Tools

## Purpose

Định nghĩa **LangGraph state graph** cho HC-NS KB agent. Agents chứa logic điều phối pipeline: phân loại query, retrieve, rerank, route & generate. Tách biệt với eval — agents chỉ chứa định nghĩa hành vi, không chứa code đánh giá.

## Architecture

Agent là một **state graph** với các node tách bạch:

```
Query → [Classifier] → [Retrieve] → [Rerank] → [Route & Generate] → [Guardrail] → Answer
                                                        ↕
                                              [Self-Correct / Fallback] (optional)
```

### Node Descriptions

| Node | Responsibility |
|------|---------------|
| **Classifier** | Phân loại query: factual / procedural / multi-hop / comparative / out-of-scope |
| **Retrieve** | Gọi hybrid search (dense + sparse, RRF fusion) |
| **Rerank** | Cross-encoder: N=20–30 → keep k=3–8; score threshold → "liên hệ HR" nếu không có context |
| **Route & Generate** | Route theo độ khó (Flash ↔ model mạnh), ép citation, temp 0.1 |
| **Self-Correct** | (Tùy chọn) Faithfulness/confidence thấp → escalate model mạnh hoặc re-retrieve |

## Intended Contents

- **`src/graph/`** — LangGraph state graph definition
- **`src/nodes/`** — Individual node implementations (classifier, retrieve, rerank, generate)
- **`src/prompts/`** — Prompt templates (separate .md/.txt files)
- **`src/tools/`** — Tools that agent nodes can call
- **`pyproject.toml`** — Python package config

## Conventions

- Mỗi node là function thuần, dễ test độc lập
- State graph typed (TypedDict hoặc Pydantic)
- Prompts tách riêng file, không embed trong code
- Citation bắt buộc trong generation output

## Milestone Mapping

- **M001 (S01):** Thư mục này được tạo, chưa có code
- **M003 (Retrieval & Agent):** LangGraph state graph, hybrid search, reranker, LLM routing
- **M005 (Mở rộng):** Self-correct/fallback loop, advanced routing
