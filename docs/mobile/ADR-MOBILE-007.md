# ADR-MOBILE-007 — PM-action contract (`submitPmResult`): schema RIÊNG 5-key + nested checklist child-array + DIVERGENCE method-verb (bare `@whitelist`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-007 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-16 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | ADR-MOBILE-006 (POST-action route-by-VALUE + 403 SINGLE-SHAPE) · Decision-B (closed-schema oneOf) · C6/C7 (200 oneOf [Env, Error]) · C3-split (field-disjoint cross-domain) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm08.py`, `assetcore/services/imm08.py`, `assetcore/assetcore/doctype/pm_work_order/pm_work_order.json`). Contract: [`04-api-contract.md §8.14`](./04-api-contract.md).

---

## Context

Vòng 16 bồi path `submitPmResult` (`POST /api/method/assetcore.api.imm08.submit_pm_result`, opId `submitPmResult`) vào contract mobile — đây là **POST-action lifecycle ĐẦU TIÊN cho domain PM (IMM-08)**: chuyển PM Work Order `Assigned/In Progress → Completed` (`svc.submit_result` `services/imm08.py:655`; `wo.status=PMStatus.COMPLETED` `:671`; `wo.submit()` `:679` → lifecycle event `pm_completed` + thiết bị `→ Active` `:686`). Mục đích: màn PM-detail (`getPmWorkOrder`, C6-DETAIL) đang là **dead-end read-only** (flow-5) — KTV mở chi tiết PM nhưng KHÔNG có endpoint để hoàn thành. `submitPmResult` mở nút "Nộp kết quả PM".

Kế thừa mẫu POST-action ADR-MOBILE-006, NHƯNG `submit_pm_result` khác mọi action trước (acknowledge/startRepair/startWork/resolve) ở **3 điểm hợp đồng** cần quyết định:

1. **Shape `data` của success envelope = 5-key, KHÔNG `{name,status}`.** `submit_result` return `{name, new_status, is_late, next_pm_date, cm_wo_created}` (`services/imm08.py:705-711`) — 5 key, và field trạng-thái tên là **`new_status`** (KHÔNG `status` như Repair/Incident). 3 field PM-riêng: `is_late` (PM nộp trễ), `next_pm_date` (ngày PM kế tiếp), `cm_wo_created` (Corrective WO auto-spawn khi PM Fail).
2. **`requestBody` mang child-array nested.** `checklist_results` là `array<PmChecklistResultInput>` (KTV gửi kết quả TỪNG DÒNG checklist) — action ĐẦU TIÊN có **nested body** (mọi action trước = single `name` hoặc `{name,notes}` phẳng). BE `parse_json` string → `result_map = {r["idx"]: r ...}` (`services/imm08.py:659`).
3. **Method-verb DIVERGENCE.** Handler `submit_pm_result` `api/imm08.py:54` là **bare `@frappe.whitelist()`** — KHÔNG `methods=['POST']` (KHÁC `imm09.start_repair:71` / `imm12.start_work:245` vốn POST-only) ⇒ runtime BE **nhận cả GET**.

## Decision

**(1) Schema RIÊNG `PmSubmitResultEnvelope`/`PmSubmitResultResponse` 5-key — KHÔNG reuse `Repair`/`IncidentActionResponse`.** `PmSubmitResultResponse` closed `{name string, new_status string, is_late boolean, next_pm_date (string format date), cm_wo_created (string|null nullable)}` — khai đúng `submit_result:705-711`. `new_status` enum = PMStatus-canonical **7-state** 1:1 `pm_work_order.json` Select (`@services/imm08.py:43-50`), post-submit = `Completed`. Đây là **C3-split cross-domain**: PM dùng field-name `new_status` (≠ `status` Repair/Incident) + 3 field PM-riêng ⇒ KHÔNG ép chung object action incident/repair. `is_late` = **genuine boolean** (`bool(wo.is_late)` `:707`) — KHÁC `pm_sticker_attached` ở request (`integer enum[0,1]`, Check `int()`-coerce `api/imm08.py:64`). `cm_wo_created` `nullable:true` (OAS 3.0.3) — name Corrective WO khi PM Fail (`find_one source_pm_wo+wo_type=Corrective` `:703-704`), `null` khi Pass.

**(2) `requestBody` INLINE + nested child-array `checklist_results[]`.** `application/json` `$ref SubmitPmResultRequest` (`required:true`). `SubmitPmResultRequest` closed `{name REQUIRED; checklist_results array<PmChecklistResultInput> default []; overall_result default 'Pass'; technician_notes default ''; pm_sticker_attached integer enum[0,1] default 0; duration_minutes integer default 0}` — khớp signature `submit_pm_result(name, checklist_results='[]', overall_result='Pass', technician_notes='', pm_sticker_attached=0, duration_minutes=0)` (`name` positional ⇒ required; 5 default ⇒ optional). Nested item **`PmChecklistResultInput`** closed `{idx integer REQUIRED, result string, measured_value string nullable, notes string default ''}` — `idx` = khoá `result_map` (`:659`), chỉ đọc `result`/`measured_value`/`notes` (`:662-664`); `measured_value` nullable (dòng định-tính không số đo).

**(3) DIVERGENCE method-verb: contract khai POST, BE bare `@whitelist` — ghi rõ + đẩy BACKLOG HARD-STOP.** Contract **chủ đích khai POST** vì `submit_pm_result` là write-action (mutate `docstatus`/`status`, sinh lifecycle event — **không idempotent**, KHÔNG hợp GET-semantics). BE hiện bare `@frappe.whitelist()` `api/imm08.py:54` (nhận cả GET) = **lệch contract↔source**. **Fix** = thêm `methods=['POST']` `api/imm08.py:54` (mirror `start_repair`/`start_work`) — **BACKLOG HARD-STOP** (fix kèm reload gunicorn, KHÔNG sửa `.py` round này). **Guard discipline (anti-false-green)**: TC-a assert path POST **tồn-tại** + opId (KHÔNG assert POST-ONLY-vì-source — claim không được vượt source); TC-i live-signature parity assert chữ-ký THẬT (`inspect.signature` độc lập với `methods`).

**(4) 403 SINGLE-SHAPE + slot `{200,401,403}` (kế thừa ADR-MOBILE-006).** 200 = oneOf `[PmSubmitResultEnvelope, Error]` route-by-VALUE `body.success` (0 discriminator). 403 = SINGLE-SHAPE `Forbidden` (dispatcher-403; in-handler cap-403 `pm.submit` `api/imm08.py:58` đã phủ bởi nhánh Error 200-oneOf) — KHÁC `reportIncident` DUAL-403. 401 = `Unauthorized401`. KHÔNG status-line key `404/409/422` — lỗi nghiệp vụ in-handler (WO∄ `IMM08_WO_NOT_FOUND` `:658` / already-submitted `IMM08_ALREADY_SUBMITTED` `:660` / completion-gate `VALIDATION` BR-08-08/09/10 `:675`) arrive HTTP-200 + Error, route theo `body.http_status`.

## Consequences

- **Tích cực:** Domain PM có envelope action chuẩn — `complete_pm`/`pause_pm`/`halt_pm`... (nếu bồi sau) tái dùng `PmSubmitResultEnvelope` HOẶC sinh `Pm*Response` riêng theo data-shape. Codegen mobile sinh `PmSubmitResultResponse` + `PmChecklistResultInput` typed → client gửi mảng kết quả checklist, đọc `cm_wo_created`/`is_late` để hiển thị "Đã tạo phiếu sửa chữa"/"PM trễ hạn". `new_status` enum 7-state ⇒ máy-trạng-thái client đúng.
- **Tiêu cực / nợ:** **DIVERGENCE method-verb** = nợ kỹ thuật ghi nhận tường minh: BE bare `@whitelist` (nhận GET) ↔ contract POST. **BACKLOG HARD-STOP**: thêm `methods=['POST']` `api/imm08.py:54` (fix kèm reload). Cho tới khi fix: client codegen gửi POST đúng (POST hợp lệ với handler bare-whitelist — Frappe nhận cả GET/POST), nhưng contract-as-spec sạch hơn source.
- **Pure-yaml:** BE handler `submit_pm_result` + service `submit_result` (5-key return) + cap-gate `pm.submit` `@api/imm08.py:58` + `result_map`/checklist-write `@services/imm08.py:659-664` ĐÃ tồn tại @source — KHÔNG sửa `.py`, KHÔNG reload gunicorn, KHÔNG migrate. Live HTTP + `methods=['POST']` fix cần USER (HARD-STOP).

## Alternatives (đã loại)

1. **Reuse `RepairActionResponse`/`IncidentActionResponse` `{name,status}`** — LOẠI: `submit_result` trả 5-key + field-name `new_status` (≠ `status`). Ép `{name,status}` → mất `is_late`/`next_pm_date`/`cm_wo_created` (signal nghiệp vụ: trễ hạn, lịch PM kế, CM auto-spawn). C3-split cross-domain: PM-enum/field ≠ repair/incident.
2. **Tên `new_status` → `status` cho đồng-bộ Repair/Incident** — LOẠI: source trả key tên `new_status` (`services/imm08.py:707`). Đổi tên = drift contract↔source, codegen sai key máy-đọc.
3. **`checklist_results` = string JSON-blob (không nested schema)** — LOẠI: mất type-safety. KTV gửi từng dòng `{idx,result,measured_value,notes}` ⇒ nested `PmChecklistResultInput` cho codegen sinh DTO khít + validate `idx` required client-side.
4. **Sửa `api/imm08.py` thêm `methods=['POST']` ngay round này** — LOẠI: sửa `.py` = cần reload gunicorn (HARD-STOP USER, `--preload` staleness). Round này pure-yaml + guard-test; divergence ghi rõ + đẩy backlog.
5. **Khai contract GET (theo đúng BE bare `@whitelist`)** — LOẠI: `submit_pm_result` mutate state + sinh event = không idempotent, vi phạm GET-semantics. Contract giữ POST (đúng nghiệp vụ), source-fix = backlog.
