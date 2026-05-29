---
name: assetcore-plan
description: >
  Dùng khi cần quyết định AssetCore "làm gì tiếp theo" hoặc lên kế hoạch trước khi
  code — ideation, chọn ưu tiên sprint, backlog, scoping, chia task cho BE/FE.
  Dùng khi user nói "sprint tới làm gì", "nên làm gì tiếp", "đề xuất tính năng",
  "lên kế hoạch", "kế hoạch sprint", "ưu tiên việc nào", "roadmap", "backlog",
  "planning", "chia task", "scope module", "module nào trước", "PM", "LEAD",
  hoặc bắt đầu bất kỳ việc gì mà chưa rõ làm module/feature nào. Kích hoạt TRƯỚC
  assetcore-doc/be/fe khi đầu vào còn là "ý tưởng" chứ chưa là module cụ thể.
---

# AssetCore — Planning (PM + LEAD)

## Overview

Skill cho 2 vai trò đầu nguồn của vòng đời phát triển:
- **[PM]** — *chọn LÀM GÌ*: ideation, ưu tiên backlog, scope in/out.
- **[LEAD]** — *chia LÀM SAO*: task breakdown cho BE/FE theo build sequence.

**Nguyên tắc cốt lõi:** Quyết định ưu tiên phải **dựa trên hiện trạng đã verify**, không dựa trên trí nhớ/đoán. Đọc trước khi đề xuất.

## When to use / NOT

- ✅ "Sprint tới làm gì?", "đề xuất tính năng", "module nào trước", chưa có module cụ thể.
- ✅ Có module rồi nhưng cần chia task BE/FE + thứ tự build.
- ❌ Đã biết chính xác việc + đã có Core Doc → vào thẳng `assetcore-be`/`assetcore-fe`.
- ❌ Viết/sửa nội dung tài liệu module → `assetcore-doc`.

---

## [PM] Ideation — chọn việc gì (làm ĐÚNG THỨ TỰ)

### Bước 1 — Quét backlog từ 5 nguồn, theo ĐÚNG thứ tự ưu tiên

| # | Nguồn | Cách lấy |
|---|-------|----------|
| 1 | **Bug vỡ-prod / fix chưa commit** | `git status` — fix treo trong working tree (install/migrate/hook breakers) phải ship TRƯỚC |
| 2 | **Bug list đang mở** | Memory `imm*_ui_bugs.md`, `wave*_ui_bugs*.md` |
| 3 | **Gap production-readiness** | `assetcore-audit` 8-pillar (module "Live" nhưng thiếu pillar) |
| 4 | **Gap tài liệu** | `assetcore-doc` — module thiếu docs/imm-XX/ |
| 5 | **Feature mới** | Theo WHO HTM lifecycle + thứ tự Wave (xem catalog) |

### Bước 2 — Quy tắc Stabilize-before-Expand (BẮT BUỘC)

> **KHÔNG mở module/Wave mới khi còn blocker ở nguồn #1–#3.**

Còn bug vỡ-prod chưa commit, còn P1/P2 mở, còn pillar audit fail → sprint tới là **stabilize & ship**, không phải bành trướng diện tích lỗi. Chỉ khi nền sạch mới mở việc mới.

### Bước 3 — Verify-before-Claim (BẮT BUỘC)

Trước khi khẳng định bất cứ điều gì về module:
- **Tên + scope module** → đọc `assetcore-doc/references/module-catalog.md`. KHÔNG tự bịa "IMM-10 = …".
- **Trạng thái / Wave** → đọc memory + catalog (`Đợt 1/2/3`). KHÔNG đoán.
- **Code đã có chưa** → grep `services/immXX.py`, `api/immXX.py` trước khi nói "chưa có".

> Wave 1 = IMM-04/05/08/09/11/12 · Wave 2 = IMM-01/02/03/06/15/16 · Wave 3 = IMM-07/10/13/14/17.

### Bước 4 — Output ideation brief (ngắn)
- **Làm gì** (1 đề mục, module IMM-XX, actor).
- **Tại sao ưu tiên hơn alternatives** (so sánh ≥2 lựa chọn khác + lý do loại).
- **Next concrete step**.

---

## [LEAD] Planning — chia task (khi đã chốt việc)

1. **Scope in/out** — 1 đề mục/sprint. Liệt kê rõ **OUT-of-scope** để chống gold-plating.
2. **Verify doc-vs-code** — đọc `docs/imm-XX/` + code thật; mọi drift doc↔code là **Phase 0 blocking** (BA reconcile trước).
3. **Task breakdown** theo build sequence — KHÔNG chép lại ở đây, dùng:
   - BE build sequence (9 bước, exact paths) → `assetcore-be`
   - FE build sequence → `assetcore-fe`
4. **Acceptance** mỗi task: có record/audit trail, test (TDD), KPI nếu có.
5. **Sequencing** — đánh dấu task song song được vs phụ thuộc.

---

## Gate PM → BA → LEAD → Dev (không nhảy bước)

```
[PM] chốt việc ──> [BA] cập nhật Core Doc (docs/imm-XX/) ──> [LEAD] chia task ──> BE/FE code
                         ▲ GATE: chưa update Core Doc thì KHÔNG code (single source of truth)
```

## Skill routing (giao việc cho skill nào)

| Sau planning, việc gì | Skill |
|---|---|
| Cập nhật Core Doc / domain / integration | `assetcore-doc` |
| BE: DocType, service, API, workflow | `assetcore-be` |
| FE: view, store, client | `assetcore-fe` |
| Test (TDD) | `assetcore-test` |
| Production-readiness / security | `assetcore-audit` |
| Migrate / fixture / deploy | `assetcore-deploy` |
| Commit | `assetcore-commit` |

---

## Red Flags — STOP

| Dấu hiệu | Sự thật |
|----------|---------|
| Đề xuất mở module/Wave mới khi còn fix chưa commit | Stabilize-before-Expand → ship blocker trước |
| Khẳng định tên/scope module từ trí nhớ | Đọc `module-catalog.md` — bịa scope là lỗi nặng nhất |
| Bug vỡ-prod xếp xuống sub-bullet | Blocker = ưu tiên #1, không phải "rủi ro phụ" |
| Nhảy thẳng vào code khi chưa có Core Doc | Gate PM→BA: Core Doc trước |
| Plan ôm nhiều module/feature 1 sprint | Cắt còn 1 đề mục, ghi rõ OUT-of-scope |
| "Wave 2 còn 5 module" mà không tra | Verify Wave từ catalog trước khi nói |

## Common mistakes

- **Hallucinate module scope** (gán sai IMM-XX) — luôn tra catalog.
- **Bành trướng khi nền chưa vững** — ưu tiên đóng nợ trước feature mới.
- **Chép build sequence vào plan** — chỉ trỏ tới `assetcore-be`/`assetcore-fe`.
- **Quên OUT-of-scope** — không khoanh vùng → scope creep.
