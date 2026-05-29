# System Architecture — HC-NS KB Agent

## Overview

This document describes the architecture of the HC-NS (Hành chính – Nhân sự) Enterprise Knowledge Base agent system.

## Two-Pipeline Strategy

The project maintains **two pipelines** running against the same golden dataset for objective comparison:

### Pipeline 1: Team hiện tại (Baseline)

- **Static pipeline** with fixed components
- Dense-only retrieval, top-k=5, no reranker
- Single LLM (Gemini 3 Flash)
- Eval via DeepEval

### Pipeline 2: Team mới (Our pipeline)

- **LangGraph agent** with swappable components
- Hybrid search (dense + sparse with RRF fusion)
- Cross-encoder reranker (Cohere v3.5 / bge-reranker)
- LLM routing (Flash for easy queries, Pro/GPT-4o/Claude for complex)
- Eval via DeepEval + RAGAS

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     LangGraph Agent                      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │Classifier│→ │ Retrieve │→ │ Reranker │→ │ Generate│ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│                                    ↓                     │
│                            LLM Router                    │
│                        (Flash ↔ Pro/Claude)             │
└─────────────────────────────────────────────────────────┘
         ↑                                        ↓
   Hybrid Search                          Guardrail (vendor)
   (dense + sparse, RRF)                       ↓
                                          User Answer
                                          + Citations
```

## Swappable Components

Each pipeline layer follows an **adapter interface** (`ingest` / `retrieve` / `generate`), enabling:

- **A/B testing** different implementations
- **Ablation studies** (turn components on/off)
- **Fair comparison** between baseline and team mới via shared eval harness

| Layer | Implementations | Config Key |
|-------|----------------|------------|
| Parse | LlamaParse, VLM, docling | `parser.active` |
| Chunking | Parent-child, contextual headers, structure-aware | `chunker.strategy` |
| Embedding | Gemini 3072, voyage-3-large, BGE-M3 | `embedding.model` |
| Retrieval | Dense-only, Hybrid (RRF) | `retrieval.mode` |
| Reranker | None, Cohere v3.5, bge-reranker-v2-m3 | `reranker.model` |
| LLM | Gemini 3 Flash, Pro, GPT-4o, Claude | `llm.router` |

## Data Flow

1. **Ingestion:** SharePoint HR → fetch/crawl → incremental sync → parse → chunk → embed → vector DB
2. **Query:** User query → classifier → hybrid search → rerank → route → generate → guardrail → answer

## Eval Architecture

Eval is an **independent deliverable** at `eval/`:

- **Pipeline-agnostic** via adapter pattern
- **Two adapters:** `baseline_adapter` and `newteam_adapter` implement the same interface
- **Golden set** versioned in JSON (provided later)
- **Two metric tiers:** Retrieval (Recall@k, Context Precision, MRR, NDCG) + Generation (Faithfulness, Answer Relevancy, Correctness)
- **CI gate:** Regression threshold check on every PR touching pipeline components

## Technology Choices

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Agent framework | LangGraph | State graph for visualize, test, and isolate behavior |
| Orchestration | Pipecon Nexus (preferred) / fallback self-hosted | Early access requested |
| Vector DB | Pinecone (sparse-native) or Qdrant | TBD — Pinecone supports sparse natively |
| Frontend | Next.js 16 + TypeScript + Tailwind CSS 4 | Modern, fast, type-safe |
| Backend | Python (FastAPI) | Native ecosystem for ML/NLP tools |

## See Also

- `docs/human/setup.md` — Developer setup guide
- `docs/human/decisions/` — Architecture Decision Records (ADRs)
- `docs/ai/glossary.md` — HC-NS domain glossary
