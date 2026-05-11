# AssetCore Skills

Project-scoped skills cho phát triển AssetCore (Frappe v15 + Vue 3, HTM domain).
Claude Code tự discover các skill này khi chạy trong workspace, không cần đăng ký.

> **CONVENTIONS.md** — single source of truth cho cross-skill rules (naming, 3-tier, ErrorCode, audit, permissions, doc-sync). Mọi skill đều reference file này. Đọc trước khi build feature mới.

## Khi nào dùng skill nào

### Build skills (dev hằng ngày)

| Bạn nói… | Claude sẽ kích hoạt |
|---|---|
| "viết API IMM-XX", "thêm validator", "service mới", "controller hook" | **assetcore-be-module** |
| "tạo view", "trang IMM-XX", "Pinia store", "form WO", "list table" | **assetcore-fe-module** |
| "tạo DocType", "thêm field", "child table", "AC X" | **assetcore-doctype-designer** |
| "workflow", "transition", "approval flow", "state machine" | **assetcore-workflow-builder** |
| "viết test", "TDD", "kiểm thử", "bench run-tests" | **assetcore-tester** |

### Ops skills (vận hành / triển khai)

| Bạn nói… | Claude sẽ kích hoạt |
|---|---|
| "bench", "migrate", "fixture", "patch", "site lỗi" | **assetcore-devops** |
| "phân quyền", "permission", "audit trail", "vendor isolation" | **assetcore-security** |
| "deploy", "lên prod", "release", "rollback", "site mới cho hospital" | **assetcore-deployment** |

### Audit / domain skills (mới — Wave 2/3)

| Bạn nói… | Claude sẽ kích hoạt |
|---|---|
| "is IMM-XX ready?", "module audit", "kiểm tra module hoàn chỉnh chưa", "gap analysis" | **assetcore-module-audit** |
| "WHO HTM", "NĐ98", "GMDN", "lifecycle stage", "phân loại thiết bị y tế" | **assetcore-htm-domain** |
| "imm-XX gọi imm-yy", "module integration", "compliance gate", "shared enum" | **assetcore-integration-patterns** |

## Hai skill quan trọng nhất (theo CLAUDE.md)

- `assetcore-be-module/` — kiến trúc 3-tier (api → service → repository), chuẩn ServiceError/ErrorCode, lifecycle event bắt buộc
- `assetcore-fe-module/` — Vue 3 + Pinia + Vue Router, useApi pattern, ApiError typing

Hai skill này có thêm `references/` (error-codes, permission-matrix, component-patterns) để nạp khi cần.

## Build sequence khi thêm IMM module mới

1. `assetcore-htm-domain` → confirm WHO HTM stage + NĐ98 compliance scope
2. `assetcore-doctype-designer` → schema
3. `assetcore-workflow-builder` → state machine
4. `assetcore-tester` → viết test trước (TDD per CLAUDE.md §17)
5. `assetcore-be-module` → service + api + controller hook
6. `assetcore-integration-patterns` → wire cross-module hooks (nếu module phụ thuộc IMM-04/08/16)
7. `assetcore-fe-module` → api client + store + view
8. `assetcore-security` → review trước khi merge
9. `assetcore-module-audit` → 8-pillar checklist (BE/FE/test/docs/...)
10. `assetcore-devops` → migrate, fixture export
11. `assetcore-deployment` → release lên prod

## Skill catalog

| # | Skill | Loại | Lines | Refs |
|---|---|---|---|---|
| 1 | assetcore-be-module | Build | 318 | error-codes, permission-matrix |
| 2 | assetcore-fe-module | Build | 374 | component-patterns |
| 3 | assetcore-doctype-designer | Build | 233 | — |
| 4 | assetcore-workflow-builder | Build | 191 | — |
| 5 | assetcore-tester | Build | 248 | — |
| 6 | assetcore-devops | Ops | 228 | — |
| 7 | assetcore-security | Ops | 242 | — |
| 8 | assetcore-deployment | Ops | 262 | — |
| 9 | assetcore-module-audit | Audit | 221 | — |
| 10 | assetcore-htm-domain | Domain | 168 | — |
| 11 | assetcore-integration-patterns | Architecture | 259 | — |

Tất cả skill có Cross-skill conventions section ở cuối, link về [`CONVENTIONS.md`](./CONVENTIONS.md).

## Cách edit skill

Mỗi skill là 1 thư mục với `SKILL.md` (frontmatter `name` + `description` quyết định khi nào trigger). Sửa nội dung trực tiếp; Claude reload mỗi turn. Nếu thêm reference dài, đặt vào `references/` và link từ SKILL.md.

Khi thay đổi rule cross-cutting (e.g., naming, error code), update `CONVENTIONS.md` trước, rồi audit các skill bị ảnh hưởng.
