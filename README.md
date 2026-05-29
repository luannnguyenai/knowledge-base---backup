# HC-NS Enterprise Knowledge Base Agent

> **Trợ lý hỏi-đáp tri thức Hành chính – Nhân sự** · Baseline RAG/Agent pipeline + Evaluation Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## Vision

Build an end-to-end RAG/agent baseline for enterprise **HC-NS (Hành chính – Nhân sự)** knowledge queries — policies, procedures, forms, and HR regulations — with **measurable, reproducible evaluation** to objectively compare against existing pipelines and future **Pipecon Nexus** upgrades.

### Goals

1. **E2E pipeline:** SharePoint ingest → parse → chunk → embed → retrieve → answer with citations.
2. **Evaluation framework:** retrieval, generation, agent behavior, and guardrail metrics on a shared golden dataset.
3. **Quantitative comparison:** baseline vs. current team pipeline vs. Pipecon Nexus on the same test set.
4. **Model monorepo:** standardized repo with coding conventions, bilingual docs, and `.skills` for both human and AI agents.
5. **Modular architecture:** swap any component (parser, embedding, reranker, LLM) without breaking the system.

### Non-goals (this phase)

- No custom guardrail/LLM-route development (third-party or TBD).
- No production-scale infra optimization (measurement first).
- No training custom embedding/LLM models.

## Architecture

```
SharePoint ──► Scheduled Sync ──► Parse (LlamaParse / VLM fallback)
                                          │
                                    Parent-Child Chunking
                                          │
                              Embedding (Gemini 3072d)
                                          │
                                  Vector Store
                                          │
                              Retrieval (Top-k = 5)
                                          │
                          Generation (Gemini 3 Flash + citations)
                                          │
                              Guardrail / LLM-route (TBD)
                                          │
                                    User (Chat UI)
```

| Component | Baseline Choice | Notes |
|-----------|----------------|-------|
| Data source | SharePoint (fetch/crawl) | Auth + permission-aware |
| Parse | LlamaParse (primary), VLM fallback | VLM for scanned images/tables |
| Chunking | Parent-child | Tune sizes via eval |
| Embedding | Gemini embedding large (3072 dims) | Fixed for fair comparison |
| Retrieval | Top-k = 5 | No reranker yet — A/B candidate |
| Generation | Gemini 3 Flash | Must include source citations |
| Guardrail | Third-party LLM-route | Scope TBD |

### Two-track strategy

**Pipecon Nexus** is preferred (early access requested). If unavailable, the **baseline** above serves as fallback. A common abstract pipeline interface (`ingest/retrieve/generate`) enables hot-swapping. The same evaluation harness runs on both.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS 4, App Router |
| Backend | Python (ingestion, retrieval, orchestration, API) |
| Embedding | Gemini embedding large (3072 dims) |
| LLM | Gemini 3 Flash |
| Parse | LlamaParse + VLM fallback |
| Evaluation | Custom harness + DeepEval cross-check + LLM-as-a-judge |
| Package manager | Bun (frontend) |

## Directory Structure

| Directory | Responsibility |
|-----------|---------------|
| `frontend/` | Chat UI — query input, answer display with citations |
| `backend/` | SharePoint ingest, parse, chunk, embed, retrieve, API |
| `agents/` | Agent logic, prompts, tools (evaluation excluded) |
| `eval/` | **Independent deliverable:** golden set, harness, metrics, judges, reports; pipeline-agnostic via adapter pattern |
| `docs/human/` | Developer and operator documentation |
| `docs/ai/` | Context and instructions optimized for AI/agent consumption |
| `.skills/` | Reusable agent skills |
| `AGENTS.md` | Shared coding standards for all agents (human & AI) |

> **Why `eval/` is separate:** Evaluation is the core deliverable — not a side effect of agents. It must run on any pipeline (baseline, current team, Nexus) via a shared adapter interface, with its own CI, versioning, and ownership.

## Milestone Roadmap

| Milestone | Focus | Key Deliverables |
|-----------|-------|-----------------|
| **M001 — Bootstrap** | Repo scaffolding | Directory structure, purpose READMEs, Next.js frontend, AGENTS.md, root README.md |
| **M002 — Ingestion** | SharePoint sync & processing | Fetch/crawl, LlamaParse parsing, parent-child chunking, Gemini embedding, vector store |
| **M003 — Retrieval & Agent** | Answer pipeline | Top-k retrieval, Gemini 3 Flash generation with citations, basic chat UI, multi-turn context |
| **M004 — Eval Framework** | Measurement | Golden set ingestion, eval harness, retrieval & generation metrics, LLM-as-a-judge, reports |
| **M005 — Comparison** | Benchmarking | Run baseline + current team pipeline on same golden set, comparison report, open questions resolved |

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url>
cd <repo-name>

# 2. Frontend — install dependencies and start dev server
cd frontend
bun install
bun dev
# → http://localhost:3000

# 3. Backend — see backend/README.md for Python setup
cd ../backend
# (coming in M002)

# 4. Evaluation — see eval/README.md
cd ../eval
# (coming in M004)
```

## Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | Guardrail: self-built or third-party? Scope & SLA? | TBD | 🟡 Pending |
| 2 | Pipecon Nexus: when is early access available? | TBD | 🟡 Pending |
| 3 | Reranker: add to baseline for A/B now, or keep top-k=5 for fairness? | TBD | 🟡 Pending |
| 4 | Acceptable metric thresholds for HC-NS domain? | TBD | 🟡 Pending |
| 5 | SharePoint permission enforcement level in baseline phase? | TBD | 🟡 Pending |
| 6 | Vector store & infra: which solution? | TBD | 🟡 Pending |
| 7 | Golden set: who owns content and approves HC-NS answers? | TBD | 🟡 Pending |

## Success Metrics

- Retrieval Recall@5 and Faithfulness meet TBD threshold on golden set.
- Baseline runs E2E stably and reproducibly.
- Clear comparison table between baseline and current team pipeline.
- Repo adopted as team standard.

---

*This project is a baseline knowledge base agent for HC-NS enterprise use — built for measurement, comparison, and modular upgrade.*
