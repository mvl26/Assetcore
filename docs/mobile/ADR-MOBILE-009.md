# ADR-MOBILE-009 — Repair-action TERMINAL-THẬT (`confirmInspection`): schema RIÊNG 4-key C3-split cross-ACTION (shape-trùng `CloseWorkOrderResponse` nhưng `status` INVARIANT `Completed`) + cap `repair.submit` (phê-duyệt-chất-lượng) + clean POST

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-009 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-16 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | ADR-MOBILE-006 (POST-action route-by-VALUE + 403 SINGLE-SHAPE) · Decision-B (closed-schema oneOf) · C6/C7 (200 oneOf [Env, Error]) · C3-split (ResolveIncidentResponse/CloseIncidentResponse precedent cross-action) · C8-ACTION (route-by-VALUE `body.success`, 0 discriminator) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm09.py`, `assetcore/services/imm09.py`, `assetcore/utils/messages.py`, `assetcore/assetcore/doctype/asset_repair/asset_repair.json`). Contract: [`04-api-contract.md §8.20`](./04-api-contract.md).

---

## Context

Vòng 30 bồi path `confirmInspection` (`POST /api/method/assetcore.api.imm09.confirm_inspection`, opId `confirmInspection`) vào contract mobile — đây là **POST-action lifecycle TERMINAL-THẬT cho domain Repair (IMM-09)**, mắt-xích **CUỐI** của vòng-đời Repair Work Order: nghiệm-thu sau sửa chữa, chuyển Repair WO `Pending Inspection → Completed` (`doc.submit()` `services/imm09.py:1108`, docstatus 0→1 → `on_submit → complete_repair()` chốt MTTR/SLA + restore Asset có điều kiện BR-09-09).

`closeWorkOrder` (§ path block) chỉ đưa WO về **`Pending Inspection` (NON-terminal)** — chờ nghiệm-thu cấp khoa; thiết bị CHƯA về `Active`, MTTR/SLA CHƯA chốt cứng, docstatus VẪN 0. `getRepairWorkOrder.allowed_transitions[]` (C6-DETAIL, mirror Incident R3 / PM R21) ĐÃ surface CTA **`Completed`** trên màn repair-detail khi `status="Pending Inspection"` (`_REPAIR_VALID_TRANSITIONS[Pending Inspection]=[Completed, In Repair, Cancelled]` `services/imm09.py`) — **NHƯNG KHÔNG có endpoint mobile để thực thi** transition đó (dead-end CUỐI). `confirmInspection` đóng dead-end này.

Kế thừa mẫu POST-action ADR-MOBILE-006, NHƯNG `confirm_inspection` khác mọi action trước ở **3 điểm hợp đồng** cần quyết định:

1. **Shape `data` TRÙNG ĐÚNG `CloseWorkOrderResponse` 4-key NHƯNG semantics KHÁC.** `confirm_inspection` return `{name, status, mttr_hours, sla_breached}` (`services/imm09.py:1116-1121`) — **cùng 4 field, cùng type** với `CloseWorkOrderResponse`. NHƯNG: (a) `status` = **INVARIANT `Completed`** (single-value — `RepairStatus.COMPLETED` `services/imm09.py:1118` trả CỨNG, KHÔNG rẽ nhánh) vs `CloseWorkOrderResponse.status` = **2-value** `[Pending Inspection, Cannot Repair]` (rẽ theo `cannot_repair`); (b) `confirmInspection` LUÔN có MTTR/SLA (chốt sau `complete_repair()`) vs `CloseWorkOrderResponse` để 2 field nullable (nhánh `cannot_repair` không tính MTTR).
2. **Cap-gate `repair.submit` ≠ `repair.create`.** `confirm_inspection` cần `rbac.require('repair.submit')` (`api/imm09.py:105`) — vai **phê-duyệt-chất-lượng** (QA Officer / Trưởng khoa / Workshop Manager); KHÁC `createRepairWorkOrder`/`closeWorkOrder` của KTV (`repair.create`). Đây là **gate kiểm-soát chất lượng RIÊNG**: KTV đóng phiếu sang Pending Inspection, chỉ vai duyệt mới chốt Completed.
3. **Clean POST — KHÔNG verb-divergence (KHÁC `submitPmResult` §8.14 / `submitCalibration` §8.15).** Handler `confirm_inspection` `api/imm09.py:103` đã có decorator **`@frappe.whitelist(methods=['POST'])`** SẴN — write-action (mutate `status`, `docstatus 0→1`) khai POST đúng-semantics. KHÔNG cần fix backlog.

## Decision

**(1) Schema RIÊNG `ConfirmInspectionEnvelope`/`ConfirmInspectionResponse` 4-key — KHÔNG reuse `CloseWorkOrderResponse` dù SHAPE TRÙNG (C3-split cross-ACTION).** `ConfirmInspectionResponse` closed `additionalProperties:false`, **EXACT 4 prop** `{name string, status string, mttr_hours number nullable, sla_breached integer enum[0,1]}`, **`required[name, status]`** — khai đúng `confirm_inspection:1116-1121`. `status` enum = **single-value `[Completed]`** (terminal-thật INVARIANT — service trả cứng `RepairStatus.COMPLETED` `:1118`). `mttr_hours` = `number nullable:true` (Float `asset_repair.json` — phòng giá-trị chưa-set). `sla_breached` = **`integer enum[0,1]` KHÔNG `boolean`** (Check `asset_repair.json` → `int()` 0/1; Open#1 int-vs-bool sweep — mirror `CloseWorkOrderResponse.sla_breached`, `IncidentListItem.rca_required`…). KHÔNG reuse `CloseWorkOrderResponse` vì `status` mang nghĩa khác (1-value terminal vs 2-value branch) ⇒ 1 schema 2 nghĩa → codegen sinh enum sai cho 1 trong 2 action.

**(2) Envelope đóng route-by-VALUE C8-ACTION (0 discriminator).** 200 = oneOf `[ConfirmInspectionEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C8-ACTION; `success` là BOOLEAN ⇒ KHÔNG hợp discriminator-key §5c). `ConfirmInspectionEnvelope` closed `required[success,data]`, `success enum[true]`, `data → $ref ConfirmInspectionResponse`. `Error` closed `required[success,error,code,http_status]`, `success enum[false]`. 2 nhánh `additionalProperties:false` + disjoint required-set ⇒ codegen loại-trừ ĐÚNG KHÔNG discriminator.

**(3) `requestBody` INLINE `ConfirmInspectionRequest` closed single-`name` + content oneOf json+form.** `application/json` + `application/x-www-form-urlencoded` (`required:true`, KHÔNG component — Frappe RPC `/api/method` đọc `form_dict`, §4/§9; codegen JSON-only client cần header `application/json` tường minh HOẶC form-encoded). `ConfirmInspectionRequest` closed `additionalProperties:false`, **CHỈ 1 field** `{name string REQUIRED}`, **0 optional** — khớp signature `confirm_inspection(name)` (`api/imm09.py:104`, 1 positional, 0 default ⇒ 1 required 0 optional). `required[name]`.

**(4) Cap `repair.submit` (phê-duyệt-chất-lượng) — gate RIÊNG khác `repair.create`.** `rbac.require('repair.submit')` `api/imm09.py:105` — confirm cần vai duyệt; KHÁC KTV (`repair.create`). Phân-quyền 2 vai đúng kiểm-soát chất lượng (KTV → Pending Inspection; duyệt → Completed).

**(5) 403 SINGLE-SHAPE + slot `{200,401,403}` (kế thừa ADR-MOBILE-006, clean POST).** 403 = SINGLE-SHAPE `Forbidden` (`$ref components/responses/Forbidden`) = **dispatcher-403** (guest/no-token trip TRƯỚC `handle()` → HTTP-line 403 THẬT + FrappeRawError). In-handler **cap-403** (`rbac.require('repair.submit')` `api/imm09.py:105` ném `frappe.throw(PermissionError)`) cũng cho HTTP-line 403 THẬT (KHÔNG HTTP-200) → đã PHỦ bởi single-shape `Forbidden`; slot 403 **KHÔNG schema mới** (KHÁC `reportIncident` DUAL-403 — mirror `closeWorkOrder`/`closeIncident`). 401 = `Unauthorized401`. KHÔNG status-line key `404/409` — 2 lỗi nghiệp vụ in-handler arrive HTTP-200 + Error (xem (6)).

**(6) 2 case Error-on-HTTP-200 documented (ARRIVE nhánh Error 200-oneOf, KHÔNG status-line).** (a) **`IMM09_NOT_FOUND`** — WO∄ (`services/imm09.py:1101` `nthrow(MSG.IMM09_NOT_FOUND, name=name)`) ⇒ Error `code=NOT_FOUND http_status=404` (`messages.py:639`), đến trên HTTP-200 (quirk §5). (b) **`IMM09_BAD_STATE`** — `status ≠ Pending Inspection` (`services/imm09.py:1102-1103` `nthrow(MSG.IMM09_BAD_STATE, state=doc.status, expected=Pending Inspection)`) ⇒ Error `code=BAD_STATE http_status=409` (`messages.py:646`), đến trên HTTP-200. Client route theo `body.http_status`. Cả 2 chỉ biểu-diễn trong nhánh `Error` — `Error.http_status` bounded enum đã chứa `[404,409]`, `Error.code` enum chứa `NOT_FOUND`/`BAD_STATE` ⇒ KHÔNG cần mở schema/slot mới.

## Consequences

- **Tích cực:** Domain Repair có **action TERMINAL-THẬT** đóng dead-end CUỐI flow-5 — `allowed_transitions[]` CTA `Completed` nay thực-thi-được. Codegen mobile sinh `ConfirmInspectionResponse` typed RIÊNG (status enum 1-value `[Completed]` ⇒ client hiển thị "Đã nghiệm thu hoàn tất", đọc `mttr_hours`/`sla_breached` cho dashboard KPI). Gate `repair.submit` ≠ `repair.create` ⇒ client ẩn/hiện CTA "Nghiệm thu" theo `imm_roles` vai duyệt (UI), server vẫn gate cứng. Clean POST ⇒ KHÔNG nợ verb-divergence (KHÁC §8.14/§8.15 — KHÔNG vào `_PARITY_VERB_ALLOWLIST`).
- **C3-split cross-ACTION (precedent mới):** đây là lần đầu C3-split áp cho 2 action **shape-trùng 4-key** (vs `ResolveIncidentResponse`/`CloseIncidentResponse` 3-key shape-trùng nhưng field-name-disjoint `rca_created`≠`closed_date`). Ở đây field-name TRÙNG HẾT nhưng `status`-enum-domain disjoint (`[Completed]` vs `[Pending Inspection, Cannot Repair]`) ⇒ vẫn split. Quy-tắc bổ-sung: **C3-split khi enum-domain của field chung disjoint, dù field-name + type trùng**.
- **Tiêu cực / nợ:** acceptance text BA gợi-ý `IMM09_BAD_STATE` http 422 (`VALIDATION_ERROR`); **source THẬT** = **409 `BAD_STATE`** (`messages.py:646`). Contract khai theo source (409). Nếu nghiệp-vụ muốn 422 → đổi `messages.py:646` (BE round riêng + guard test, KHÔNG đụng round pure-yaml này). Ghi nhận để QA không cảnh-báo false-positive.
- **Pure-yaml:** BE handler `confirm_inspection` + service (4-key return) + cap-gate `repair.submit` `@api/imm09.py:105` + `methods=['POST']` `@api/imm09.py:103` ĐÃ tồn tại @source — `git status api/imm09.py` + `services/imm09.py` = EMPTY (KHÔNG sửa `.py`). KHÔNG reload gunicorn, KHÔNG migrate, KHÔNG commit. Live HTTP cần USER reload (HARD-STOP).

## Alternatives (đã loại)

1. **Reuse `CloseWorkOrderResponse` (nới `status` enum thành 3-value gộp `Completed`)** — LOẠI: mất tín-hiệu INVARIANT-terminal của confirm; client không biết status nào hợp-lệ cho action nào (`closeWorkOrder` KHÔNG bao giờ trả `Completed`; `confirmInspection` LUÔN trả `Completed`). 1 schema 2 nghĩa `status` ⇒ codegen sinh enum lẫn-lộn.
2. **Nhồi `confirmInspection` vào path `closeWorkOrder` (thêm cờ `confirm=1`)** — LOẠI: 1 path 2 cap-gate (`repair.create` vs `repair.submit`) ⇒ phá phân-quyền 2 vai (KTV vs duyệt). OpenAPI 1 operation 1 security-context — không khai được 2 cap.
3. **`status` để `type:string` không enum (free-form)** — LOẠI: source trả CỨNG `RepairStatus.COMPLETED` `:1118` ⇒ enum `[Completed]` 1-value là source-grounded; bỏ enum = mất type-safety + client không biết invariant terminal.
4. **`sla_breached` `type:boolean`** — LOẠI: Check field `asset_repair.json` → BE `int()` 0/1; nhiều Check-field khác toàn contract đã `integer enum[0,1]` (Open#1 sweep). Boolean = bất-nhất ⇒ codegen strict-deser 2 kiểu cho cùng-nghĩa cờ.
5. **Khai status-line `404/409` cho 2 case in-handler** — LOẠI: `nthrow → handle()` return Error-dict trên **HTTP-200** (quirk §5), KHÔNG raise→HTTP-4xx. Khai 404/409 status-line = sai wire-shape, codegen route nhầm theo status-line thay vì `body.http_status`.
6. **Sửa `messages.py:646` 409→422 để khớp acceptance text** — LOẠI: sửa `.py` round pure-yaml (cần reload, HARD-STOP). Contract khai theo source THẬT (409); đổi-semantics http-status = BE round riêng + guard.
