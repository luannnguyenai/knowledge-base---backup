# SKILL.md — building-kb-consistently (Team Vibecoding Standard)

---
name: building-kb-consistently
description: >
  Quy chuẩn DUY NHẤT để cả team (người + AI) vibecode đồng nhất trên repo
  HC-NS KB Agent — chung patterns, chung interface, chia ranh giới sở hữu
  rõ ràng để merge KHÔNG conflict. Dùng skill này TRƯỚC mọi thay đổi code:
  thêm component (parser/chunker/embedder/retriever/reranker/LLM route),
  viết node LangGraph, viết eval adapter, tạo module/thư mục mới, hoặc
  chỉnh cấu trúc monorepo.
---
```

## 1. Skill này là gì & khi nào dùng

Đây là **skill chung duy nhất** của repo. Mọi người trong team (và mọi AI agent) **đọc skill này TRƯỚC** khi viết code, để đảm bảo:

- Cùng một **pattern** (adapter swappable, vertical slice, prompt tách file…).
- Cùng một **interface** → các component thay thế nhau được, eval chạy chung.
- **Ranh giới sở hữu rõ ràng** → hai người làm song song không đụng cùng file → merge sạch.

Dùng skill này khi:

- Thêm/sửa component pipeline (parser, chunker, embedder, retriever, reranker, LLM route).
- Viết hoặc sửa **eval adapter**.
- Viết **node LangGraph** mới.
- Tạo thư mục/module mới trong `backend/`, `agents/`, `eval/`, `frontend/`.
- Chỉnh cấu trúc monorepo, shared types, hoặc config.

## 2. Golden Rules (đọc 30 giây)

- [ ]  Đọc `AGENTS.md` (root) + `README.md` của thư mục liên quan + skill này TRƯỚC khi code.
- [ ]  **One file per implementation** — mỗi implementation 1 file riêng trong `implementations/`, không nhồi chung file.
- [ ]  **Đăng ký qua registry file riêng**, không sửa tay file barrel/`__init__.py` dùng chung khi tránh được.
- [ ]  **Không reformat / không đổi code không liên quan** trong cùng PR (giảm diff → giảm conflict).
- [ ]  **Vertical slice** + PR nhỏ + branch theo convention.
- [ ]  **Lockfile** (`bun.lock`, `uv.lock`) sinh tự động — conflict thì regenerate, KHÔNG sửa tay.
- [ ]  **Prompts tách file** `.md`/`.txt`, không embed trong code.
- [ ]  **Shared types** sống ở `packages/shared-types/` — không tự định nghĩa lại type chung.
- [ ]  Mọi thay đổi pipeline phải **kèm eval** (eval-first).
- [ ]  Commit theo **Conventional Commits**; type=English, business docs=Vietnamese.

## 3. Bản đồ sở hữu (Ownership Map) — chống merge conflict

Mỗi PR nên **chỉ chạm vào một vùng**. Nếu phải chạm nhiều vùng → tách PR.

| Vùng | Sở hữu / ai chạm | Quy tắc chống conflict |
| --- | --- | --- |
| `frontend/` | Frontend slice | Component mới = file mới trong `app/` hoặc `components/`. Không sửa `layout.tsx`/`globals.css` chung trừ khi cần. |
| `backend/<layer>/implementations/` | Người làm component đó | Mỗi implementation 1 file. Đăng ký qua registry, không sửa file người khác. |
| `agents/src/nodes/` | Người làm node đó | Mỗi node 1 file. Graph wiring tập trung 1 chỗ, sửa có chủ đích. |
| `agents/src/prompts/` | Người viết prompt | Mỗi prompt 1 file `.md`. Không gộp. |
| `eval/adapters/` | Eval owner | Mỗi pipeline 1 adapter file. Interface cố định. |
| `packages/shared-types/` | Cần review kỹ | Thay đổi type chung = breaking. Tách type theo file domain, thông báo team. |
| `AGENTS.md`, config gốc | Cần review kỹ | File "hot" — đổi phải đồng thuận, ưu tiên thêm (append) hơn sửa. |

### File "hot" dễ conflict — xử lý thế nào

Những file mà nhiều người cùng sửa (barrel `__init__.py`, file đăng ký, `package.json`, graph wiring) là nguồn conflict chính. Quy tắc:

1. **Ưu tiên thêm dòng (append-only)** thay vì sửa/sắp xếp lại dòng cũ → 3-way merge tự xử lý tốt hơn.
2. **Registry pattern:** thay vì import thủ công trong 1 file lớn, dùng cơ chế đăng ký để mỗi component tự khai báo (xem §6).
3. **Một thay đổi structural mỗi lần:** nếu phải đổi file hot, merge `main` vào branch trước, đổi, push sớm.
4. **Không sort/format lại** import hoặc key trong file hot ở PR không liên quan.

## 4. Cấu trúc repo (where things go)

```
frontend/   Next.js 16 chat UI — query input, answer + citations
backend/    Python: ingest, parse, chunk, embed, retrieval, API
agents/     LangGraph state graph: classifier, retrieve, rerank, generate
eval/        Deliverable độc lập: golden set, harness, adapters, metrics, judges, reports
packages/shared-types/   Type dùng chung cho frontend/backend/agents
docs/human/  Architecture, setup, ADRs (cho người)
docs/ai/     Context, glossary (tối ưu cho AI agent đọc)
.skills/     Agent skills (skill này + external references)
AGENTS.md    Coding standard chung
```

Mỗi thư mục module có `README.md` với 3 mục bắt buộc: **Purpose, Intended Contents, Milestone Mapping**.

## 5. Pattern lõi: Swappable Component qua Adapter Interface

Mọi layer của pipeline implement **cùng một interface** để thay thế nhau được và để eval gọi chung:

```
ingest(source)            -> List[Document]
parse(document)           -> List[Chunk]
chunk(documents)          -> List[Chunk]
embed(chunks)             -> List[Embedding]
retrieve(query, k)        -> List[ScoredChunk]
rerank(query, chunks)     -> List[ScoredChunk]
generate(query, context)  -> Answer
```

Nguyên tắc:

- Mỗi implementation (LlamaParse / VLM / docling …) implement đúng interface trên.
- **Config YAML** quyết định implementation nào đang active — không hardcode lựa chọn trong code.
- **Eval harness gọi qua adapter**, không gọi trực tiếp implementation.
- Type của `Document`, `Chunk`, `ScoredChunk`, `Answer`… sống ở `packages/shared-types/` (TS) và mirror trong backend (Python) — là **single source of truth**.

## 6. Cấu trúc 1 module & Registry pattern

Mỗi layer swappable theo khuôn:

```
<layer>/                      # ví dụ: backend/parsing/
├── README.md                 # Purpose, Intended Contents, Milestone Mapping
├── AGENTS.md                 # (nếu cần) convention riêng của module
├── src/
│   ├── __init__.py           # CHỈ export public interface — sửa hạn chế
│   ├── base.py               # Abstract base class / Protocol (interface)
│   ├── registry.py           # Cơ chế đăng ký (append-only)
│   └── implementations/
│       ├── llamaparse.py      # 1 file / 1 implementation
│       ├── vlm.py
│       └── docling.py
└── tests/
    ├── test_base.py
    └── test_implementations.py
```

### Registry pattern (giảm conflict ở file đăng ký)

Mỗi implementation **tự đăng ký** bằng decorator trong chính file của nó, thay vì sửa 1 file danh sách chung:

```python
# src/registry.py  (hiếm khi phải sửa)
PARSERS: dict[str, type["ParserBase"]] = {}

def register_parser(name: str):
    def deco(cls):
        PARSERS[name] = cls
        return cls
    return deco

# src/implementations/docling.py  (chỉ chạm file của bạn)
from ..registry import register_parser
from ..base import ParserBase

@register_parser("docling")
class DoclingParser(ParserBase):
    def parse(self, document): ...
```

→ Hai người thêm 2 parser khác nhau = 2 file khác nhau = **không đụng nhau khi merge**.

## 7. Quy trình thêm 1 component (vibecode recipe)

1. Xác định layer (parse/chunk/embed/retrieve/rerank/generate) và đọc `base.py` của layer đó.
2. Tạo file mới trong `implementations/<ten>.py` — implement đúng interface.
3. `@register_<layer>("<ten>")` trong chính file đó.
4. Thêm nhánh config YAML cho implementation (append, không sửa nhánh người khác).
5. Viết test trong `tests/` (1 file/implementation).
6. Viết/cập nhật **eval**: đảm bảo adapter chạy được component mới trên golden set.
7. Cập nhật `README.md` của module nếu đổi Intended Contents.
8. Commit `feat(<scope>): add <ten> <layer>` + mở PR nhỏ.

## 8. LangGraph agent conventions

- Mỗi **node = 1 function thuần**, 1 file trong `agents/src/nodes/`, test độc lập được.
- **State graph typed** bằng `TypedDict` hoặc Pydantic — đặt ở 1 file state chung, sửa có chủ đích.
- Graph wiring (nối node) tập trung ở `agents/src/graph/` — đây là file hot, append node theo thứ tự, tránh sửa lại các cạnh cũ không liên quan.
- **Prompts tách file** `.md`/`.txt` trong `agents/src/prompts/`, không embed trong code.
- **Citation bắt buộc** trong output của node generate.
- Các node chuẩn: `classifier` → `retrieve` → `rerank` → `route_generate` → (`self_correct` optional).

## 9. Eval-first mindset

- `eval/` là **deliverable độc lập**, không phụ thuộc implementation của `agents/`/`backend/`.
- Mọi pipeline (baseline, team mới, Pipecon Nexus) expose cùng interface: `ingest()`, `retrieve(query)`, `generate(query, context)`.
- Mỗi pipeline = **1 adapter file** trong `eval/adapters/` (vd `baseline_adapter.py`, `newteam_adapter.py`).
- **Golden set** versioned (JSON), HR validate đáp án. Schema:
    
    `{question: str, answer: str, expected_sources: list[str], difficulty: str, topic: str}`.
    
- Kết quả ghi vào `eval/reports/` dạng JSON + markdown summary; ghi seed, version dữ liệu, version model.
- **Regression gate** trong CI: PR rớt ngưỡng metric → block merge.
- Mọi thay đổi pipeline phải kèm eval test.

## 10. Coding conventions

### TypeScript / Frontend

- `strict: true`, **không dùng `any`** → dùng `unknown` hoặc typed interface.
- **Server Components mặc định**; chỉ `"use client"` khi cần state/effect/handlers/browser API.
- Data fetching: `async` Server Components hoặc Server Actions. Không `getServerSideProps`/`getStaticProps`.
- Styling: Tailwind CSS 4. Import alias `@/*` (tránh `../../`).
- `bun lint` trước khi commit. ESLint + Prettier theo cấu hình `frontend/`.

### Python / Backend & Agents

- **Type hints bắt buộc** (`def f(x: str) -> int:`), `mypy` khi project trưởng thành.
- Docstring cho mọi public interface (mô tả purpose + I/O).
- Ruff lint + format; `black` line length 88; `isort` cho imports.
- Env qua `os.environ` hoặc `pydantic-settings`; **không hardcode secrets**.
- API routes có OpenAPI schema (FastAPI auto-generate).

## 11. Naming conventions (đồng nhất → ít nhầm, ít conflict)

| Đối tượng | Quy ước | Ví dụ |
| --- | --- | --- |
| Branch | `<type>/<scope>-<short-desc>` | `feat/backend-docling-parser` |
| Commit | Conventional Commits | `feat(agents): add rerank node` |
| File implementation | `snake_case`, tên ngắn gọn của impl | `bge_m3.py`, `cohere_v35.py` |
| Test | `test_<unit>_<condition>_<expected>` | `test_parse_sharepoint_doc_returns_metadata` |
| Biến/hàm/class | English | `scored_chunks`, `HybridRetriever` |
| Prompt file | `<node>_<purpose>.md` | `classifier_intent.md` |

## 12. Shared types — single source of truth

- Type dùng chung qua frontend/backend/agents sống ở `packages/shared-types/`.
- **Không tự định nghĩa lại** type chung trong từng module → tránh divergence.
- Tách type theo file domain (`document.ts`, `chunk.ts`, `answer.ts`) để giảm conflict khi nhiều người sửa.
- Đổi type chung = breaking change → ghi vào commit body + thông báo team.

## 13. Config & secrets

- Lựa chọn implementation, top-k, alpha (RRF), model… đều qua **config YAML**, không hardcode.
- Mỗi component thêm **nhánh config riêng** (append), không sửa nhánh người khác.
- Secrets qua env; không commit `.env`. Không commit file sinh tự động (`.next/`, `__pycache__/`, `*.pyc`, `node_modules/`).

## 14. Testing standards

- Frontend: Vitest/Jest (unit cho utils, component test cho UI logic).
- Backend/Agents: `pytest`, test đặt trong `tests/` cạnh source.
- Eval: golden set chạy reproducible (ghi seed + version).
- Integration: `httpx` (backend) / Playwright (frontend).

## 15. Commit, PR & quy trình giải quyết conflict

- **PR nhỏ, vertical slice**, 1 vùng / 1 PR.
- Trước khi push: `git pull --rebase origin main` để rebase sớm, phát hiện conflict sớm.
- Conflict ở **lockfile** → bỏ phiên bản merge, chạy lại `bun install` / `uv lock` để regenerate.
- Conflict ở **registry/barrel** → giữ cả hai dòng đăng ký (append), bỏ marker.
- Conflict ở **shared-types / [AGENTS.md](http://AGENTS.md)** → dừng, trao đổi với owner trước khi resolve.
- Không bao giờ "resolve" bằng cách xóa code người khác mà chưa hiểu.

## 16. Bilingual documentation

- Code comments, docstrings, API docs: **English** (để AI đọc nhất quán).
- PRD, user stories, HC-NS policy: **tiếng Việt** (stakeholders).
- README/AGENTS thư mục chính: **song ngữ** (tiêu đề English, nội dung Việt).
- Commit messages: **English** (Conventional Commits).
- Comment giải thích "tại sao", ngắn gọn, bằng English.

## 17. Vibecoding với AI agent — thứ tự đọc & cách prompt

Khi giao việc cho AI agent (hoặc tự vibecode), yêu cầu agent **đọc theo thứ tự**:

1. `AGENTS.md` (root) → 2. `.skills/building-kb-consistently/SKILL.md` (file này) → 3. `README.md` + `AGENTS.md` của thư mục đang sửa → 4. `base.py`/interface của layer → 5. `docs/ai/context.md` & `glossary.md` khi cần domain.

Quy tắc cho agent:

- Ưu tiên **vertical slice** (end-to-end mỏng) hơn horizontal layer.
- Không xóa comment/docs có sẵn trừ khi đã confirm obsolete.
- Khi phát sinh quyết định kiến trúc → ghi vào `docs/human/decisions/` (ADR) hoặc `.gsd/DECISIONS.md`.
- Gặp ambiguity (đặc biệt domain HC-NS nhạy cảm) → hỏi/ghi nhận, **không đoán**.
- Tạo component mới → luôn theo §6–§7, dùng registry, kèm test + eval.

## 18. Definition of Done (checklist trước khi mở PR)

- [ ]  Theo đúng interface/adapter của layer.
- [ ]  Implementation là file riêng + đăng ký qua registry.
- [ ]  Có config YAML (nếu cần), không hardcode lựa chọn/secret.
- [ ]  Có test (unit) + eval cập nhật (nếu chạm pipeline).
- [ ]  Lint/format pass (`bun lint` / Ruff).
- [ ]  Không reformat / không đụng code ngoài phạm vi.
- [ ]  README/docs cập nhật nếu đổi Intended Contents.
- [ ]  Commit Conventional Commits; PR nhỏ, 1 vùng.
- [ ]  Đã rebase `main`, conflict (nếu có) đã resolve đúng §15.

## 19. Anti-patterns (đừng làm)

- ❌ Nhồi nhiều implementation vào 1 file.
- ❌ Hardcode lựa chọn model/parser thay vì config.
- ❌ Sửa/sắp xếp lại file hot (barrel, graph wiring, package.json) không cần thiết.
- ❌ Embed prompt dài trong code.
- ❌ Tự định nghĩa lại type chung trong module riêng.
- ❌ Sửa tay lockfile khi conflict.
- ❌ Reformat toàn bộ file trong PR feature.
- ❌ Đoán đáp án domain HC-NS khi chưa có golden set/validate.
- ❌ PR khổng lồ chạm nhiều vùng cùng lúc.

## 20. Scripts & References

- `.skills/building-kb-consistently/scripts/` — automation helpers (scaffold module, kiểm tra interface, chạy eval gate).
- `.skills/building-kb-consistently/references/` — tài liệu tham khảo chi tiết (adapter spec đầy đủ, ví dụ config YAML, ADR template).
- External skills (tái sử dụng, không tự viết): LangChain Skills (LangGraph patterns), rag-implementation, hybrid search + reranking, RAG evaluation (DeepEval + RAGAS).