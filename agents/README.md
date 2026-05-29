# agents — Agent Definitions, Prompts, Tools

## Purpose

Định nghĩa các agent logic, system prompts, và tool definitions cho HC-NS KB agent. Tách biệt với eval — agents chỉ chứa định nghĩa hành vi, không chứa code đánh giá.

## Intended Contents

- **Agent definitions:** Prompt templates, system instructions, tool schemas
- **Conversation logic:** Multi-turn context management, fallback behavior
- **Tool implementations:** Các công cụ agent gọi (retrieval, search, document lookup)
- **Guardrail interface:** Interface trừu tượng cho LLM-route/guardrail (bên thứ 3 hoặc tự làm sau)

## Milestone Mapping

- **M001 (S01):** Thư mục này được tạo, chưa có code
- **M003 (Retrieval & Agent):** Agent trả lời có trích dẫn, hội thoại đa lượt
- **M005 (Mở rộng):** Guardrail integration, Pipecon Nexus adapter
