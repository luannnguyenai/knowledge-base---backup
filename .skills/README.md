# .skills — Skills tái sử dụng cho Agents

## Purpose

Thư mục chứa các skill definitions được chia sẻ cho agents trong hệ thống. Mỗi skill là một module độc lập định nghĩa khả năng, prompt template, và tool schema mà agent có thể sử dụng.

## Intended Contents

- **Skill definitions:** File cấu trúc mô tả từng skill (tên, mục đích, input/output)
- **Prompt templates:** System prompts cho từng loại agent behavior
- **Tool schemas:** JSON Schema cho các tools agent có thể gọi
- **Shared contexts:** Context snippets dùng chung giữa nhiều agents

## Design Principle

Skills được thiết kế để tái sử dụng — một skill có thể được nhiều agent types sử dụng mà không cần duplicate code.

## Milestone Mapping

- **M001 (S01):** Thư mục này được tạo, chưa có skills
- **M003+:** Skill definitions sẽ được định nghĩa khi agent logic được triển khai
