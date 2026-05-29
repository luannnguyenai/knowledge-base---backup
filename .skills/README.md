# .skills — Skills tái sử dụng cho Agents

## Purpose

Thư mục chứa các skill definitions được chia sẻ cho agents trong hệ thống. Mỗi skill là một module độc lập định nghĩa khả năng, prompt template, và tool schema mà agent có thể sử dụng.

## Skills Strategy

### Self-written (duy nhất)

| Skill | Nội dung |
|-------|---------|
| `building-kb-consistently/` | **Skill chung duy nhất** — convention repo, AGENTS.md lồng nhau, coding standard, swappable component pattern, eval workflow, cách dùng skill ngoài |

### External (tái sử dụng, không tự viết)

| Skill / Nguồn | Dùng cho |
|--------------|---------|
| **LangChain Skills** (`langchain-ai/langchain-skills`) | LangGraph agent patterns, dependency management |
| **rag-implementation** (Smithery) | RAG với vector DB + semantic search |
| Hybrid search + reranking skills | Dense+sparse (RRF), cross-encoder rerank |
| Embedding evaluation skills | Benchmark đa model, tối ưu dimension |
| RAG evaluation skills | DeepEval + RAGAS, golden set, regression gate |

## Intended Contents

- **`building-kb-consistently/`:** SKILL.md + references/ + scripts/ (tự viết & maintain)
- **External skill references:** Links or installed skill packages theo Agent Skills specification

## Design Principle

Chỉ tự viết **MỘT skill chung**. Các năng lực theo tech stack thì **tái sử dụng skill có sẵn** (chuẩn Agent Skills — folder + SKILL.md, đặt tên dạng gerund). Không viết lại từ đầu.

## Milestone Mapping

- **M001 (S01):** Thư mục này + `building-kb-consistently/SKILL.md` được tạo
- **M002+:** External skills được cài đặt và reference khi cần
