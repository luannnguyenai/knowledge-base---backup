# building-kb-consistently

Skill chung duy nhất của project — quy chuẩn triển khai đồng nhất trên toàn repo HC-NS KB Agent.

## Khi nào dùng skill này

- Thêm component mới (parser, chunker, embedder, retriever, reranker, LLM route)
- Viết hoặc sửa eval adapter
- Tạo thư mục mới trong `backend/`, `agents/`, `eval/`
- Chỉnh sửa cấu trúc monorepo

## Quy tắc cốt lõi

### 1. Cấu trúc module swappable

Mọi component trong pipeline phải tuân theo **adapter interface** chung:

```
ingest(source) -> List[Document]
parse(document) -> List[Chunk]
chunk(documents) -> List[Chunk]
embed(chunks) -> List[Embedding]
retrieve(query, k) -> List[ScoredChunk]
rerank(query, chunks) -> List[ScoredChunk]
generate(query, context) -> Answer
```

- Mỗi implementation (LlamaParse, VLM, docling) implement cùng interface.
- Config YAML chọn implementation nào đang active.
- Eval harness gọi qua adapter, không gọi trực tiếp implementation.

### 2. Cấu trúc thư mục

```
<module>/
├── README.md          # Purpose, intended contents, milestone mapping
├── AGENTS.md          # Module-specific conventions (nếu cần)
├── src/
│   ├── __init__.py    # Public interface exports
│   ├── adapter.py     # Abstract base class / protocol
│   └── implementations/
│       ├── llamaparse.py
│       ├── vlm.py
│       └── docling.py
└── tests/
    ├── test_adapter.py
    └── test_implementations.py
```

### 3. Eval-first mindset

- Mọi thay đổi pipeline phải đi kèm eval test.
- Golden set versioned (JSON), HR validate đáp án.
- Adapter pattern: baseline_adapter và newteam_adapter cùng interface.
- Regression gate trong CI: PR không pass metric threshold → block merge.

### 4. Coding conventions

- **Python:** Type hints bắt buộc, docstring cho public interface, Ruff lint + format.
- **TypeScript:** `strict: true`, không `any`, Server Components mặc định (Next.js).
- **Commit:** Conventional Commits (`type(scope): description`).
- **Docs:** Technical = English, Business = Vietnamese, README = bilingual.

### 5. Agent conventions (LangGraph)

- Mỗi node = function thuần, dễ test độc lập.
- State graph typed (TypedDict hoặc Pydantic).
- Prompts tách riêng file `.md`/`.txt`, không embed trong code.
- Citation bắt buộc trong generation output.

## Scripts

Xem `.skills/building-kb-consistently/scripts/` cho automation helpers.

## References

Xem `.skills/building-kb-consistently/references/` cho tài liệu tham khảo chi tiết.
