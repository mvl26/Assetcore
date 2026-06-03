# AssetCore Skills

Project-scoped skills cho phát triển AssetCore (Frappe v15 + Vue 3, HTM domain).
Claude Code tự discover các skill này khi chạy trong workspace.

> **CONVENTIONS.md** — single source of truth cho cross-skill rules (naming, 3-tier, ErrorCode, audit, permissions, doc-sync).

---

## 9 skills theo chu trình phát triển (SDLC orchestration)

Bản đồ định tuyến: từ **ý tưởng** → ship. Mỗi mũi tên là một gate; chọn skill theo bước hiện tại.

```
Plan → Doc → BE → FE → Test → Deploy → Audit (sửa lỗi / tái cấu trúc)
 ↑PM/LEAD  ↑BA                  ↑QA               ↑
 (chọn việc gì)              Import (cross-cutting — BE + FE + validation pipeline)
                                                  Commit (đóng mỗi vòng — chia commit nhỏ + push)
   ┌───────────────────────────────────────────────────────────────────────┐
   │ Session (cross-cutting — đọc STATE.md đầu phiên, ghi STATE.md+LOG.md cuối phiên) │
   └───────────────────────────────────────────────────────────────────────┘
```

**Vai trò (factory 6-role) ↔ skill:** `[PM]/[LEAD]`→plan · `[BA]`→doc · `[BE]`→be · `[FE]`→fe · `[QA]`→test+audit · `[USER]`→test(Playwright).

**Gate quan trọng:** `[PM] chốt việc → [BA] cập nhật Core Doc (docs/imm-XX/) → code`. Chưa có Core Doc thì KHÔNG code.

| Skill | Khi nào dùng | Trigger phrases |
|---|---|---|
| **assetcore-plan** | Quyết định làm gì tiếp / ưu tiên sprint / scope / chia task BE-FE (điểm vào khi mới có "ý tưởng") | "sprint tới làm gì", "nên làm gì tiếp", "đề xuất tính năng", "lên kế hoạch", "ưu tiên việc nào", "module nào trước", "PM", "LEAD" |
| **assetcore-doc** | Viết/chuẩn hóa tài liệu BA, domain knowledge WHO HTM/GMDN/NĐ98, integration patterns | "viết tài liệu", "docs IMM-XX", "HTM lifecycle", "GMDN", "NĐ98", "integration giữa module" |
| **assetcore-be** | Phát triển backend: API, service, repository, DocType schema, workflow state machine | "viết BE", "thêm endpoint", "service IMM-XX", "DocType mới", "workflow", "transition", "approval flow" |
| **assetcore-fe** | Phát triển frontend: Vue views, Pinia store, API client, router, components | "tạo view", "trang IMM-XX", "Pinia store", "form WO", "list table", "thêm UI" |
| **assetcore-import** | Tính năng import hàng loạt: BE validation layer, post-processing, FE Import Wizard 4-bước | "import dữ liệu", "bulk import", "upload excel", "import tài sản", "wizard import", "template import", "ImportWizardView", "useImport", "import_validators" |
| **assetcore-test** | Viết/chạy tests: backend unit test, workflow smoke test, Playwright UI test | "viết test", "TDD", "bench run-tests", "test UI", "DoD", "playwright", "UI xong chưa" |
| **assetcore-deploy** | Vận hành hàng ngày (bench, migrate, fixtures) + triển khai production | "bench", "migrate", "deploy", "lên prod", "release", "site lỗi", "clear cache" |
| **assetcore-audit** | Kiểm tra production-readiness (8-pillar) + security review | "audit module", "IMM-XX sẵn sàng chưa", "tái cấu trúc", "phân quyền", "security review", "gap analysis" |
| **assetcore-commit** | Tạo git commit theo chuẩn dự án (1 commit/tất cả file, subject EN, no Co-Authored-By) | "commit", "commit tiếp", "commit cho tôi", "lưu thay đổi", "git commit" |
| **assetcore-session** | Bàn giao CONTEXT giữa phiên: đọc `STATE.md` đầu phiên, ghi `STATE.md`+`LOG.md` cuối phiên. Cross-cutting — gắn mọi skill ở ranh giới phiên + factory loop vòng→vòng. | "lưu context", "bàn giao", "handoff", "đang dở ở đâu", "phiên trước làm gì", "checkpoint", "tiếp nối phiên" |

> **Tự động hoá (hook):** `SessionStart` → tự `cat STATE.md` vào context; `SessionEnd` → tự ghi breadcrumb vào `LOG.md`. Backend: `.claude/scripts/session-log.sh`. Dữ liệu phiên nằm NGOÀI repo (cạnh `memory/`), không commit.

---

## References trong từng skill

| Skill | References |
|---|---|
| assetcore-be | `error-codes.md`, `permission-matrix.md`, `lessons-learned.md` (LL-BE-* — BẮT BUỘC đọc) |
| assetcore-fe | `component-patterns.md`, `lessons-learned.md` (LL-FE-* — BẮT BUỘC đọc) |
| assetcore-audit | `lessons-learned.md` (regression classes A–L, LL-AUDIT-* — BẮT BUỘC đọc) |
| assetcore-doc | `light-touch-recipes.md`, `module-catalog.md`, `source-map.md` |
| assetcore-test | `playwright-patterns.md` |

---

## Build sequence module mới

```
0. assetcore-plan  → [PM] chốt việc + ưu tiên (stabilize-before-expand) → [LEAD] chia task
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
