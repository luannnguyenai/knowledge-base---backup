# AGENTS.md — Coding Conventions for HC-NS Enterprise KB Agent

Quy chuẩn chung cho người và AI làm việc trên repo này. Mọi commit phải tuân thủ các quy ước dưới đây.

## Language Conventions

- **TypeScript-first** cho frontend (`frontend/`). `strict: true` bắt buộc trong `tsconfig.json`.
- **Python** cho backend (`backend/`), agents (`agents/`), và eval (`eval/`). Dùng Python 3.12+.
- Không dùng `any` trong TypeScript; dùng `unknown` hoặc typed interfaces khi chưa xác định được kiểu.
- Backend dùng type hints bắt buộc (`def func(x: str) -> int:`), kèm `mypy` khi project trưởng thành.
- Frontend dùng `ES2017` target (theo `tsconfig.json`), `moduleResolution: "bundler"`.

## Next.js App Router Patterns

- **Server Components là mặc định.** Chỉ thêm `"use client"` khi cần `useState`, `useEffect`, event handlers, hoặc browser-only APIs.
- Data fetching ưu tiên `async` Server Components hoặc Server Actions. Không dùng `getServerSideProps` / `getStaticProps` (App Router).
- Route conventions: `app/` là source of truth cho routing. Dùng dynamic routes `[slug]` cho content-driven pages.
- Styling: Tailwind CSS 4. Không dùng CSS modules trừ khi có lý do đặc biệt.
- Đường dẫn alias `@/*` trỏ vào root `frontend/`. Ưu tiên import tuyệt đối tương đối (`@/components/...`) thay vì relative `../../`.
- Khi chỉnh sửa code frontend, đọc `frontend/AGENTS.md` trước — nó chứa cảnh báo về API changes của Next.js 16.

## Backend & Agent Conventions

- Backend là Python monorepo workspace. Khi có `pyproject.toml`, dùng `uv` hoặc `poetry` để quản lý dependencies.
- Mỗi module trong `agents/` và `backend/` cần có docstring mô tả purpose và public interface.
- API routes phải có OpenAPI schema (FastAPI auto-generate hoặc OpenAPI spec file).
- Environment variables: đọc qua `os.environ` hoặc `pydantic-settings`. Không hardcode secrets.
- Agent prompts tách riêng thành file `.md` hoặc `.txt` trong `agents/`, không embed trong code.

## Evaluation Conventions

- `eval/` là deliverable độc lập, không phụ thuộc implementation của `agents/` hay `backend/`.
- Mọi pipeline (baseline, team hiện tại, Pipecon Nexus) expose cùng interface: `ingest()`, `retrieve(query)`, `generate(query, context)`.
- Golden set schema: `{question: str, answer: str, expected_sources: list[str], difficulty: str, topic: str}`.
- Eval results ghi vào `eval/reports/` dạng JSON + markdown summary.

## Testing Standards

- Frontend: Vitest hoặc Jest (sẽ quyết định khi thêm test framework). Unit tests cho utility functions, component tests cho UI logic.
- Backend/Agents: `pytest`. Đặt tests trong `tests/` sibling với source hoặc `tests/` tại root mỗi module.
- Eval: golden set phải chạy reproducible. Ghi seed, version dữ liệu, version model vào mỗi lần chạy.
- Integration tests cho API endpoints dùng `httpx` (backend) hoặc Playwright (frontend).
- Test naming: `test_<function>_<scenario>_<expected>`. Ví dụ: `test_parse_sharepoint_doc_returns_metadata()`.

## Commit Message Conventions

- Dùng **Conventional Commits**: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`
- Scope: tên module (`frontend`, `backend`, `agents`, `eval`, `docs`)
- Body (optional): mô tả what/why, không how. Wrap ở 72 chars.
- BREAKING CHANGE: footer với `BREAKING CHANGE:` prefix nếu có API change.
- Example: `feat(backend): add SharePoint incremental sync logic`
- Example: `fix(frontend): resolve citation link truncation on mobile`

## Code Style

- **TypeScript/JS:** ESLint + Prettier (đã cấu hình trong `frontend/`). `bun lint` trước khi commit.
- **Python:** Ruff cho linting + formatting. `black` line length 88. `isort` cho import sorting.
- Không commit file sinh tự động (`.next/`, `__pycache__/`, `*.pyc`, `node_modules/`).
- Markdown: wrap ở 100 chars, dùng `#` cho headings, không dùng HTML trong `.md`.
- README/AGENTS.md ở mỗi thư mục phải có sections: Purpose, Intended Contents, Milestone Mapping.

## Bilingual Documentation Norms

- Tài liệu kỹ thuật (code comments, docstrings, API docs): **tiếng Anh** — để AI agents đọc hiểu thống nhất.
- Tài liệu nghiệp vụ (PRD, user stories, HC-NS policy references): **tiếng Việt** — để stakeholders và team hiểu.
- README.md ở root và các thư mục chính: **song ngữ** — tiêu đề tiếng Anh, nội dung chính tiếng Việt.
- Commit messages: **tiếng Anh** (Conventional Commits).
- Khi viết code, comments giải thích "tại sao" bằng tiếng Anh, ngắn gọn.
- Tên biến, hàm, class: **tiếng Anh** (coding convention phổ biến, dễ search, AI hiểu tốt).

## AI Agent Working Guidelines

- Luôn đọc file này và `README.md` ở thư mục liên quan trước khi chỉnh sửa code.
- Khi implement tính năng mới, ưu tiên vertical slice (end-to-end thin) hơn là horizontal layer.
- Không xóa comments hoặc docs có sẵn trừ khi đã confirm là obsolete.
- Khi phát sinh quyết định kiến trúc, ghi vào `.gsd/DECISIONS.md` hoặc `docs/human/`.
- Khi gặp ambiguity, ưu tiên hỏi/ghi nhận hơn là đoán — đặc biệt với domain HC-NS nhạy cảm.
