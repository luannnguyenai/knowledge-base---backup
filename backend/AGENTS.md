# AGENTS.md — Backend Conventions

Backend handles SharePoint ingestion, document processing (parse/chunk/embed), retrieval, and API serving.

## Structure

```
backend/
├── src/
│   ├── ingestion/       # SharePoint fetch/crawl + incremental sync
│   ├── parsing/         # Swappable: llamaparse / vlm / docling
│   ├── chunking/        # Swappable strategies
│   ├── embedding/       # Swappable models
│   ├── retrieval/       # Hybrid search + rerank
│   └── api/             # FastAPI routes
├── pyproject.toml
└── AGENTS.md
```

## Conventions

### Adapter Pattern

Every component layer implements a common interface:

```python
from abc import ABC, abstractmethod
from typing import Protocol

class Parser(Protocol):
    def parse(self, document: bytes) -> list[Chunk]: ...

class Chunker(Protocol):
    def chunk(self, documents: list[Chunk]) -> list[Chunk]: ...

class Embedder(Protocol):
    def embed(self, chunks: list[Chunk]) -> list[Embedding]: ...

class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 5) -> list[ScoredChunk]: ...

class Reranker(Protocol):
    def rerank(self, query: str, chunks: list[Chunk]) -> list[ScoredChunk]: ...
```

### API Design

- FastAPI with auto-generated OpenAPI schema
- All routes under `/api/v1/`
- Health check at `/health`
- Error responses use consistent shape: `{"error": {"code": str, "message": str}}`

### Data Flow

1. **Ingestion:** SharePoint → parse → chunk → embed → vector store
2. **Query:** API receives query → retrieve → rerank → return results (or forward to agents)

### Environment Variables

Use `pydantic-settings` for validation:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    sharepoint_tenant_id: str
    sharepoint_client_id: str
    sharepoint_client_secret: str
    vector_db_url: str = "http://localhost:6333"
    
    class Config:
        env_file = ".env"
```

### Testing

- `pytest` with `conftest.py` for shared fixtures
- Mock external services (SharePoint, embedding APIs)
- Integration tests with testcontainers for vector DB
