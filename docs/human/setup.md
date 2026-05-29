# Setup Guide — HC-NS KB Agent

## Prerequisites

- **Node.js 20+** (or use `nvm`)
- **Bun** (frontend package manager): `curl -fsSL https://bun.sh/install | bash`
- **Python 3.12+** (backend, agents, eval)
- **Git** for version control
- **Docker + Docker Compose** (optional, for local infrastructure)

## Quick Start

### 1. Clone and setup

```bash
git clone <repo-url>
cd <repo-name>
```

### 2. Environment variables

Copy `.env.example` and fill in required values:

```bash
cp .env.example .env
```

Required variables:
| Variable | Purpose |
|----------|---------|
| `SHAREPOINT_TENANT_ID` | Microsoft 365 tenant for HR SharePoint |
| `SHAREPOINT_CLIENT_ID` | App registration client ID |
| `SHAREPOINT_CLIENT_SECRET` | App registration client secret |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `OPENAI_API_KEY` | OpenAI API key (for embeddings/LLM routing) |
| `COHERE_API_KEY` | Cohere API key (for reranker) |

### 3. Frontend

```bash
cd frontend
bun install
bun dev
# → http://localhost:3000
```

### 4. Backend (coming in M002)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 5. Local Infrastructure (optional)

```bash
docker compose --profile local-dev up -d
# Starts: Qdrant vector DB, frontend, backend
```

### 6. Evaluation (coming in M001/M004)

```bash
cd eval
pip install -e ".[dev]"
# Golden set not yet available — harness runs smoke tests only
```

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `frontend/` | Next.js chat UI |
| `backend/` | Python API, ingestion, retrieval |
| `agents/` | LangGraph agent state graph |
| `eval/` | Evaluation framework (independent) |
| `packages/shared-types/` | Shared type definitions |
| `docs/` | Human and AI documentation |
| `.skills/` | Reusable agent skills |

## Development Workflow

1. Create feature branch: `git checkout -b feat/your-feature`
2. Implement changes following `AGENTS.md` conventions
3. Run linting: `bun lint` (frontend), `ruff check` (Python)
4. Run tests: `bun test` (frontend), `pytest` (Python)
5. Commit with conventional commit message: `git commit -m "feat(scope): description"`
6. Open PR — eval regression gate runs automatically

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `bun install` fails | Clear cache: `bun pm cache rm`, retry |
| Python import errors | Activate venv: `source .venv/bin/activate` |
| Vector DB connection refused | Run `docker compose --profile local-dev up -d` |
| Env vars not loaded | Check `.env` exists and has correct values |
