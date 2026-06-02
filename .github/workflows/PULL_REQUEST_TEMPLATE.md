## 📋 Mô tả (What & Why)

<!-- Tóm tắt thay đổi này làm gì và tại sao cần nó -->


## 🎯 Loại thay đổi

- [ ] feat — tính năng mới
- [ ] fix — sửa bug
- [ ] eval — golden set / metric / adapter / harness
- [ ] perf — tối ưu latency / cost / recall
- [ ] refactor — đổi code, giữ nguyên behavior
- [ ] docs — tài liệu
- [ ] chore — CI / config / dependency

## 📦 Source / Layer bị ảnh hưởng

- [ ] frontend/
- [ ] backend/
- [ ] agents/ (LangGraph)
- [ ] eval/
- [ ] packages/shared-types/
- [ ] docs/
- [ ] .skills/ hoặc AGENTS.md

## 🔗 Liên kết

- Milestone: <!-- M001 / M002 / M003 / M004 / M005 -->
- Issue / Task liên quan: Closes #

## 🧪 Cách test / Bằng chứng

<!-- Lệnh đã chạy, screenshot, hoặc log. Với agents/backend: mô tả input → output -->


## 📊 Tác động tới Evaluation (BẮT BUỘC nếu đụng pipeline)

<!-- Nếu PR đụng parse/chunk/embed/retrieval/rerank/LLM, dán kết quả eval trước & sau -->

| Metric | Trước | Sau | Delta |
| --- | --- | --- | --- |
| Recall@5 | | | |
| Context Precision | | | |
| Faithfulness | | | |
| Correctness | | | |
| Latency P95 | | | |
| Cost/query | | | |

- [ ] Eval regression gate (CI) đã pass
- [ ] Không làm tụt metric so với baseline (hoặc đã giải thích lý do)
- [ ] Không áp dụng (PR không đụng pipeline)

## ✅ Checklist trước khi xin review

- [ ] Tuân thủ coding standard trong `AGENTS.md`
- [ ] Tên branch & commit theo Conventional Commits
- [ ] Component mới giữ được tính swappable (config-driven, không hardcode)
- [ ] Đã cập nhật docs/README liên quan (nếu cần)
- [ ] Đã chạy lint / format / type-check
- [ ] CI xanh toàn bộ
- [ ] Self-review: không còn code debug / secret / key trong diff

## 👀 Reviewer & Ghi chú

- Reviewer đề xuất: @
- Điểm cần chú ý khi review: