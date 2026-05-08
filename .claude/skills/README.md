# AssetCore Skills

Project-scoped skills cho phát triển AssetCore (Frappe v15 + Vue 3, HTM domain).
Claude Code tự discover các skill này khi chạy trong workspace, không cần đăng ký.

## Khi nào dùng skill nào

| Bạn nói… | Claude sẽ kích hoạt |
|---|---|
| "viết API IMM-XX", "thêm validator", "service mới", "controller hook" | **assetcore-be-module** |
| "tạo view", "trang IMM-XX", "Pinia store", "form WO", "list table" | **assetcore-fe-module** |
| "tạo DocType", "thêm field", "child table", "AC X" | **assetcore-doctype-designer** |
| "workflow", "transition", "approval flow", "state machine" | **assetcore-workflow-builder** |
| "viết test", "TDD", "kiểm thử", "bench run-tests" | **assetcore-tester** |
| "bench", "migrate", "fixture", "patch", "site lỗi" | **assetcore-devops** |
| "phân quyền", "permission", "audit trail", "vendor isolation" | **assetcore-security** |
| "deploy", "lên prod", "release", "rollback", "site mới cho hospital" | **assetcore-deployment** |

## Hai skill quan trọng nhất (theo CLAUDE.md)

- `assetcore-be-module/` — kiến trúc 3-tier (api → service → repository), chuẩn ServiceError/ErrorCode, lifecycle event bắt buộc
- `assetcore-fe-module/` — Vue 3 + Pinia + Vue Router, useApi pattern, ApiError typing

Hai skill này có thêm `references/` (error-codes, permission-matrix, component-patterns) để nạp khi cần.

## Build sequence khi thêm IMM module mới

1. `assetcore-doctype-designer` → schema
2. `assetcore-workflow-builder` → state machine
3. `assetcore-tester` → viết test trước (TDD per CLAUDE.md §17)
4. `assetcore-be-module` → service + api + controller hook
5. `assetcore-fe-module` → api client + store + view
6. `assetcore-security` → review trước khi merge
7. `assetcore-devops` → migrate, fixture export
8. `assetcore-deployment` → release lên prod

## Cách edit skill

Mỗi skill là 1 thư mục với `SKILL.md` (frontmatter `name` + `description` quyết định khi nào trigger). Sửa nội dung trực tiếp; Claude reload mỗi turn. Nếu thêm reference dài, đặt vào `references/` và link từ SKILL.md.
