# backend — API, Ingestion, Retrieval, Orchestration

## Purpose

Backend là trung tâm của pipeline RAG/agent, chịu trách nhiệm ingest dữ liệu từ SharePoint, parse/chunk/embed, lưu vector store, và phục vụ API retrieval cho frontend và agents.

## Actual Structure (P0-P2 Implemented)

```
backend/src/hcns_backend/
├── parsing/              # EchoParser (test), LlamaParseParser (cloud)
├── chunking/             # FixedChunker, ParentChildChunker, ContextualParentChildChunker
├── embedding/            # HashEmbedder (test), GeminiEmbedder (3072d), BgeM3Embedder (dense+sparse)
├── retrieval/            # vector_stores (InMemory, Qdrant) + retrievers (Dense, HybridRRF)
├── reranking/            # NoReranker, CohereReranker, BgeReranker
└── pyproject.toml        # Declares dependency on hcns-shared
```

## Layer Design

Each layer implements a Protocol from hcns-shared, allowing component swapping:

| Layer | Responsibility | Key Implementations |
|-------|---|---|
| **Parsing** | Raw file → Document objects | EchoParser (test), LlamaParseParser (cloud) |
| **Chunking** | Document → Chunk objects | FixedChunker, ParentChildChunker (with context headers) |
| **Embedding** | Text → dense & sparse vectors | HashEmbedder (test), GeminiEmbedder, BgeM3Embedder (HybridEmbedder) |
| **Retrieval (Vector Store)** | Persist & search chunks + metadata | InMemoryVectorStore (test), QdrantVectorStore (memory/persistent) |
| **Retrieval (Retriever)** | Query → scored results | DenseRetriever (vector), HybridRrfRetriever (dense+sparse) |
| **Reranking** | Reorder/filter results | NoReranker (passthrough), CohereReranker, BgeReranker |

## Planned Future Work

- **Ingestion (M002):** SharePoint connector, scheduled sync, incremental updates
- **API (M003):** REST endpoints for query, ingestion status, health check
- **Optimization:** Fine-tuned embeddings, domain-specific models, adaptive chunk sizing
