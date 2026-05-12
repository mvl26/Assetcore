# AssetCore Skills

Project-scoped skills cho phát triển AssetCore (Frappe v15 + Vue 3, HTM domain).
Claude Code tự discover các skill này khi chạy trong workspace.

> **CONVENTIONS.md** — single source of truth cho cross-skill rules (naming, 3-tier, ErrorCode, audit, permissions, doc-sync).

---

## 6 skills theo chu trình phát triển

```
Doc → BE → FE → Test → Deploy → Audit (sửa lỗi / tái cấu trúc)
```

| Skill | Khi nào dùng | Trigger phrases |
|---|---|---|
| **assetcore-doc** | Viết/chuẩn hóa tài liệu BA, domain knowledge WHO HTM/GMDN/NĐ98, integration patterns | "viết tài liệu", "docs IMM-XX", "HTM lifecycle", "GMDN", "NĐ98", "integration giữa module" |
| **assetcore-be** | Phát triển backend: API, service, repository, DocType schema, workflow state machine | "viết BE", "thêm endpoint", "service IMM-XX", "DocType mới", "workflow", "transition", "approval flow" |
| **assetcore-fe** | Phát triển frontend: Vue views, Pinia store, API client, router, components | "tạo view", "trang IMM-XX", "Pinia store", "form WO", "list table", "thêm UI" |
| **assetcore-test** | Viết/chạy tests: backend unit test, workflow smoke test, Playwright UI test | "viết test", "TDD", "bench run-tests", "test UI", "DoD", "playwright", "UI xong chưa" |
| **assetcore-deploy** | Vận hành hàng ngày (bench, migrate, fixtures) + triển khai production | "bench", "migrate", "deploy", "lên prod", "release", "site lỗi", "clear cache" |
| **assetcore-audit** | Kiểm tra production-readiness (8-pillar) + security review | "audit module", "IMM-XX sẵn sàng chưa", "tái cấu trúc", "phân quyền", "security review", "gap analysis" |

---

## References trong từng skill

| Skill | References |
|---|---|
| assetcore-be | `error-codes.md`, `permission-matrix.md` |
| assetcore-fe | `component-patterns.md` |
| assetcore-doc | `light-touch-recipes.md`, `module-catalog.md`, `source-map.md` |
| assetcore-test | `playwright-patterns.md` |

---

## Build sequence module mới

```
1. assetcore-doc   → đọc/viết BA docs (docs/imm-XX/ — 9 files: README + 02→09)
2. assetcore-be    → DocType + Workflow JSON + Repository + Service + API + hooks.py (3-list)
3. assetcore-fe    → api/immXX.ts + stores/immXX.ts + views/<domain>/ + router
4. assetcore-test  → unit tests (Python) + Playwright UI DoD
5. assetcore-deploy → export-fixtures + migrate + smoke test
6. assetcore-audit → 8-pillar check trước khi tag release
```

> **Key rules:**
> - `api/immXX.ts` và `stores/immXX.ts` dùng IMM-code; `views/` dùng domain folder (xem domain table trong assetcore-fe skill)
> - `_parse_json` + `_handle` copy từ `api/imm09.py` — không redefine
> - Fixture wiring: cập nhật CẢ 3 list trong `hooks.py` khi thêm workflow (CONVENTIONS.md §1b)
