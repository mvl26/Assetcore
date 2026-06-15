# AssetCore Skills

Project-scoped skills cho phát triển AssetCore (Frappe v15 + Vue 3, HTM domain).
Claude Code tự discover các skill này khi chạy trong workspace.

---

## 12 skills theo chu trình phát triển (SDLC orchestration)

Bản đồ định tuyến: từ **ý tưởng** → ship. Mỗi mũi tên là một gate; chọn skill theo bước hiện tại.

```
Plan → Doc → BE → FE → Test → Deploy → Audit (sửa lỗi / tái cấu trúc)
 ↑PM/LEAD  ↑BA                  ↑QA               ↑
 (chọn việc gì)              Import (cross-cutting — BE + FE + validation pipeline)
                                                  Commit (đóng mỗi vòng — chia commit nhỏ + push)
   ┌───────────────────────────────────────────────────────────────────────┐
   │ Session (cross-cutting — đọc STATE.md+file phiên đầu phiên, checkpoint sau mỗi việc) │
   └───────────────────────────────────────────────────────────────────────┘
   Perf · Observe (cross-cutting quality — đo hiệu năng BE/FE + telemetry vận hành; gắn ở BE/FE/Deploy/Audit)
```

**Vai trò (factory 6-role) ↔ skill:** `[PM]/[LEAD]`→plan · `[BA]`→doc · `[BE]`→be · `[FE]`→fe · `[QA]`→test+audit · `[USER]`→test(Playwright). Cross-cutting quality: `perf`→[BE]/[FE] · `observe`→deploy/[QA].

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
| **assetcore-perf** | Tối ưu hiệu năng BE+FE (measure-first): N+1 query, index, pagination, report cost, FE bundle/cache/Core Web Vitals | "chậm", "tối ưu hiệu năng", "N+1", "thiếu index", "query chậm", "API chậm", "p95", "bundle to", "Core Web Vitals" |
| **assetcore-observe** | Observability kỹ thuật: structured logging (frappe.logger), RED metrics, health Error Log/Email Queue/scheduler, alert symptom-based (**≠** business audit-trail) | "log", "structured log", "telemetry", "metric", "Error Log", "Email Queue đầy", "scheduler chết", "alert", "monitoring" |
| **assetcore-commit** | Tạo git commit theo chuẩn dự án (1 commit/tất cả file, subject EN, no Co-Authored-By) | "commit", "commit tiếp", "commit cho tôi", "lưu thay đổi", "git commit" |
| **assetcore-session** | Bàn giao CONTEXT giữa phiên: đọc `STATE.md`+file phiên đầu phiên, checkpoint `STATE.md`(ghi đè)+bồi file phiên `sessions/<ngày>/` sau MỖI việc đáng kể (hook `Stop` tự mirror toàn bộ lượt; **KHÔNG còn LOG.md**). Cross-cutting — gắn mọi skill ở ranh giới phiên + factory loop vòng→vòng. | "lưu context", "bàn giao", "handoff", "đang dở ở đâu", "phiên trước làm gì", "checkpoint", "tiếp nối phiên" |

> **Tự động hoá (hook):** `SessionStart` (gồm `compact`) → tự nạp STATE + file phiên (curated) vào context; `UserPromptSubmit` → ghi prompt thô + brief STATE; `Stop` → **mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào file phiên; `SessionEnd` → breadcrumb. Backend: `.claude/scripts/session-log.sh` + `.claude/scripts/mirror_transcript.py`. Dữ liệu phiên nằm TRONG repo nhưng **GITIGNORED** (`.claude/contexts/` — folder theo ngày), không commit.

---

## Skill anatomy chuẩn (BẮT BUỘC — mọi skill phải đủ)

Chuẩn hóa từ kiến trúc agent-skills (`.claude/agent-skills/README.md` §"How Skills Work") — **"Process, not prose"**. MỖI `SKILL.md` BẮT BUỘC đủ 6 mục, đúng thứ tự, + footer session:

| Mục (heading chuẩn) | Vai trò | BB |
|---|---|---|
| `## Overview` | Skill làm gì — core principle 1–2 câu | ✓ |
| `## When to Use` | Điều kiện kích hoạt + khi NÀO **KHÔNG** dùng | ✓ |
| `## Process` | **Quy trình từng-bước (spine)** — workflow đánh số, trỏ tới mục chi tiết bên dưới | ✓ |
| `## Common Rationalizations` | Bảng lý-do-ngụy-biện + phản bác | ✓ |
| `## Red Flags — STOP` | Dấu hiệu sai → dừng | ✓ |
| `## Verification` | Checklist bằng chứng (KHÔNG "có vẻ đúng") | ✓ |
| `## 🔗 Session context` (footer) | Bàn giao phiên — repo-specific | ✓ |

**4 nguyên tắc nền:** Process-not-prose (bước/cổng/exit, không kể-lể) · anti-rationalization (mọi excuse vào bảng) · verification-non-negotiable (bằng chứng thật) · progressive-disclosure (`SKILL.md` = spine; chi tiết nặng >100 dòng → `references/`). **Domain content sống DƯỚI Process spine — bổ sung, không thay thế nó.**

> Tự kiểm conformance: `grep -cE '^## (Overview\|When to Use\|Process\|Common Rationalizations\|Red Flags\|Verification)' skills/*/SKILL.md` → mỗi file **≥ 6**.

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
> - Fixture wiring: cập nhật CẢ 3 list trong `hooks.py` khi thêm workflow

> **Cross-cutting quality (gắn xuyên build sequence):**
> - `assetcore-perf` → khi BE (b2) viết list/query và FE (b3) render bảng lớn: measure-first, không N+1, list paginated, FE lazy/cache/CWV.
> - `assetcore-observe` → khi BE (b2) thêm API/job/integration & deploy (b5): structured logging + RED metric + alert symptom-based (KHÁC business audit-trail).

---

## Provenance — nguồn kiến trúc & principle index

Anatomy (Overview/When-to-Use/Process/Common Rationalizations/Red Flags/Verification) + named engineering principles trong bộ skill này **absorb từ** `.claude/agent-skills/skills/` (24 skill generic của Addy Osmani, MIT) — đã **tailor về Frappe/HTM**. Thư viện đó **GITIGNORED, local-only** (`.gitignore`) ⇒ KHÔNG đi theo repo/CI, nên principle được nhúng thẳng vào skill AssetCore (đã commit). Spec: `docs/superpowers/specs/2026-06-15-skill-architecture-absorb-design.md`.

| Principle (generic) | Nhà AssetCore |
|---|---|
| contract-first · Hyrum's Law · One-Version Rule · boundary validation · thin vertical slice · source-cite (context7) | assetcore-be |
| WCAG 2.1 AA · design system · component architecture | assetcore-fe |
| test pyramid 80/15/5 · Beyonce Rule · test sizes · runtime-data (Playwright) | assetcore-test |
| one-question-at-a-time · ~95% confidence · divergent/convergent · acceptance criteria · atomic task | assetcore-plan |
| spec-before-code · Boundaries · source-driven (context7) · ADR | assetcore-doc |
| doubt-driven (CLAIM→EXTRACT→DOUBT→RECONCILE→STOP) · 5-step triage · five-axis review · change sizing · Chesterton's Fence · Rule of 500 · OWASP→Frappe · three-tier boundary | assetcore-audit |
| Shift Left · quality gate · feature flag · code-as-liability · zombie code · staged rollout · rollback · pre-launch | assetcore-deploy |
| trunk-based · atomic commit · change sizing ~100 · commit-as-save-point | assetcore-commit |
| context engineering · context packing · right-info-right-time | assetcore-session |
| measure-first · N+1 · index · pagination · Core Web Vitals | **assetcore-perf** (mới) |
| structured logging · RED metrics · symptom-based alert · health surfaces | **assetcore-observe** (mới) |
