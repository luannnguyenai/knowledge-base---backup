# backend — API, Ingestion, Retrieval, Orchestration

## Purpose

Backend là trung tâm của pipeline RAG/agent, chịu trách nhiệm ingest dữ liệu từ SharePoint, parse/chunk/embed, lưu vector store, và phục vụ API retrieval cho frontend và agents.

## Intended Contents

- **Ingestion:** SharePoint connector, scheduled sync, incremental update logic
- **Processing:** LlamaParse/VLM parser, parent-child chunking, Gemini embedding (3072 dims)
- **Vector Store:** lưu trữ + metadata (nguồn, ngày cập nhật, phòng ban)
- **Retrieval:** top-k retrieval API (k=5 mặc định, hỗ trợ reranker sau)
- **API Routes:** REST endpoints cho query, ingestion status, health check

## Milestone Mapping

- **M001 (S01):** Thư mục này được tạo, chưa có code
- **M002 (Ingestion & Processing):** SharePoint sync, parse, chunk, embed, vector store
- **M003 (Retrieval & Agent):** top-k retrieval API, orchestration logic
