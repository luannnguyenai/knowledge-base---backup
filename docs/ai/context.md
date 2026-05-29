# AI Context — HC-NS KB Agent

## System Overview

This is an enterprise Knowledge Base agent for **HC-NS (Hành chính – Nhân sự / Administrative – HR)** domain. The project builds a **new team pipeline** (LangGraph) to **compare objectively** against an **existing team's baseline pipeline** using the same golden dataset and evaluation framework.

## Key Architecture Concepts

### Two Pipelines

- **Baseline (team hiện tại):** Static RAG pipeline — dense retrieval only, no reranker, single LLM (Gemini 3 Flash), evaluated with DeepEval.
- **New team (team mới):** LangGraph agent with swappable components — hybrid search (dense+sparse+RRF), cross-encoder reranker, LLM routing (Flash ↔ Pro/GPT-4o/Claude), evaluated with DeepEval + RAGAS.

### Swappable Component Pattern

Every pipeline layer implements a common adapter interface:

```
ingest(source) → List[Document]
parse(document) → List[Chunk]
chunk(documents) → List[Chunk]
embed(chunks) → List[Embedding]
retrieve(query, k) → List[ScoredChunk]
rerank(query, chunks) → List[ScoredChunk]
generate(query, context) → Answer
```

### Eval is First-Class

- `eval/` is an **independent deliverable**, not a test side-effect.
- Runs on any pipeline via adapter pattern.
- Has its own CI gate (regression threshold check).
- Golden set is versioned JSON (provided later).

## LangGraph Agent State Graph

```
Query → Classifier → Retrieve (hybrid) → Rerank → Route/Generate → Guardrail → Answer
                                                                    ↕
                                                          Self-correct (optional)
```

**Nodes:**
1. `classifier` — factual / procedural / multi-hop / comparative / out-of-scope
2. `retrieve` — hybrid search (dense + sparse, RRF fusion)
3. `rerank` — cross-encoder, N=20-30 → k=3-8, score threshold → "contact HR"
4. `route_generate` — route by difficulty, force citations, temp=0.1
5. `self_correct` — (optional) low confidence → escalate or re-retrieve

## Important Conventions

- **TypeScript strict mode** in frontend — no `any`.
- **Python type hints required** for all functions.
- **Prompts in separate files** — never embed in code.
- **Conventional Commits** for all commit messages.
- **Bilingual docs** — technical: English, business: Vietnamese.
- **Vertical slices** preferred over horizontal layers.

## Data Source

- **SharePoint HR** is source of truth.
- We **fetch to index embeddings only** — do NOT store raw data.
- No PII handling (no personal data in scope).

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS 4 |
| Backend | Python (FastAPI) |
| Agents | LangGraph |
| Vector DB | Pinecone or Qdrant (TBD) |
| Embedding | Gemini / voyage / BGE-M3 |
| LLM | Gemini 3 Flash ↔ Pro / GPT-4o / Claude |
| Eval | DeepEval + RAGAS |

## See Also

- `AGENTS.md` — Coding conventions
- `docs/ai/glossary.md` — HC-NS domain glossary
- `docs/human/architecture.md` — Detailed architecture
- `.skills/building-kb-consistently/SKILL.md` — Shared skill
