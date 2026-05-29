# packages/shared-types

Shared type definitions and interfaces used across `frontend/`, `backend/`, and `agents/`.

## Purpose

Ensure type consistency across the monorepo by centralizing:
- API request/response schemas
- Eval golden set types
- Agent state graph types (LangGraph state)
- Pipeline adapter interfaces (`ingest`, `retrieve`, `generate`)

## Usage

- **TypeScript:** Import from `@shared-types` (configured in `tsconfig.json` paths).
- **Python:** Use `pydantic` models mirrored from the TypeScript interfaces.

## Milestone Mapping

- **M001:** Package scaffolded
- **M002+:** Types added as each component is implemented
