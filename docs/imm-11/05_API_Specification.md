# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-11 — Hiệu chuẩn (Calibration) |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm11.<function>` |
| Auth | Frappe session HOẶC `Authorization: token <key>:<secret>` |
| Cập nhật | 2026-07-14 (mobile-contract binding `getDueCalibrations` — read-list KHÔNG-pagination, màn "Nhắc việc" F8 · CR-28a · §0.1.9) |
| Trạng thái | ✅ Live — `assetcore/api/imm11.py` deployed (18 endpoint); mobile-contract path `listCalibrations` (read) + `submitCalibration`/`addMeasurement`/`sendToLab`/`receiveCertificate`/`cancelCalibration` (write-action) + `getCalibration.allowed_transitions[]` (read-detail) + `getDueCalibrations` (read-list F8) = §0.1 |

---

## 0. API Catalog

✅ Tất cả endpoint dưới đây đã implement trong `assetcore/api/imm11.py`.

| # | Endpoint (actual @frappe.whitelist name) | Method | Mô tả | Role | Idempotent | US |
|---|---|---|---|---|---|---|
| 1 | `assetcore.api.imm11.list_calibration_schedules` | GET | List IMM Calibration Schedule + pagination | All | ✓ | US-11-01 |
| 2 | `assetcore.api.imm11.get_calibration_schedule` | GET | Chi tiết 1 Schedule | All | ✓ | US-11-01 |
| 3 | `assetcore.api.imm11.create_calibration_schedule` | POST | Tạo Schedule mới | Workshop Lead | ✗ | US-11-01 |
| 4 | `assetcore.api.imm11.update_calibration_schedule` | POST | Patch Schedule fields | Workshop Lead | ✓ | US-11-01 |
| 5 | `assetcore.api.imm11.delete_calibration_schedule` | POST | Xóa Schedule (nếu chưa có Submitted) | Workshop Lead | ✗ | US-11-01 |
| 6 | `assetcore.api.imm11.list_calibrations` | GET | List IMM Asset Calibration + pagination (+ `mine=1` self-scope `technician` — tab "Phiếu hiệu chuẩn của tôi" MVP-5d) | All | ✓ | US-11-07 |
| 7 | `assetcore.api.imm11.get_calibration` | GET | Chi tiết 1 Calibration | All | ✓ | US-11-07 |
| 8 | `assetcore.api.imm11.create_calibration` | POST | Tạo Calibration WO | Workshop Lead, Technician | ✗ | US-11-02 |
| 9 | `assetcore.api.imm11.update_calibration` | POST | Update fields (allowed list) | Technician | ✓ | US-11-02 |
| 10 | `assetcore.api.imm11.submit_calibration` | POST | Submit → trigger Pass/Fail handler | Technician | ✗ | US-11-02 |
| 11 | `assetcore.api.imm11.add_measurement` | POST | Thêm tham số đo vào child table | Technician | ✗ | US-11-02 |
| 12 | `assetcore.api.imm11.get_calibration_kpis` | GET | KPI theo tháng | Ops Manager+ | ✓ | US-11-05 |
| 13 | `assetcore.api.imm11.get_calibration_dashboard` | GET | Dashboard đầy đủ (KPIs + lists) | All | ✓ | US-11-05 |
| 14 | `assetcore.api.imm11.get_asset_calibration_history` | GET | Lịch sử cal của 1 asset | All | ✓ | US-11-07 |
| 15 | `assetcore.api.imm11.send_to_lab` | POST | External: → Sent To Lab | Technician | ✓ | US-11-03 |
| 16 | `assetcore.api.imm11.receive_certificate` | POST | External: → In Progress (cert received) | Technician | ✓ | US-11-03 |
| 17 | `assetcore.api.imm11.cancel_calibration` | POST | Hủy phiếu chưa submit | Workshop Lead | ✗ | US-11-08 |
| 18 | `assetcore.api.imm11.get_due_calibrations` | GET | Thiết bị due ≤ N ngày (filter `AC Asset.next_calibration_date` = MIN-lịch, BR-11-13 → asset multi-schedule KHÔNG rớt) | All | ✓ | US-11-01, AC-11-21 |

> **Round 18 — CR-WF-11-CAL — dual-track lockstep (BE-only, KHÔNG đổi contract):** các endpoint transition (`create_calibration`/`update_calibration`/`send_to_lab`/`receive_certificate`/`cancel_calibration`/`submit_calibration`) THÊM side-effect nội bộ `frappe.db.set_value(..., {"workflow_state": status}, update_modified=False)` để đóng desync `workflow_state` đọng state khởi tạo (`04_Backend_Design.md §3.2` + ADR-IMM11-06). **Envelope + request/response shape KHÔNG đổi** — `workflow_state` là field nội bộ (desk workflow-engine), KHÔNG vào return-shape, KHÔNG lộ FE. DONE-gate spec-contract giữ nguyên: lỗi nghiệp vụ = **in-handler HTTP-200 + Error envelope** (`nthrow`, KHÔNG raise→4xx); 2 loại 403 = dispatcher-403 (guest/no-token) + in-handler cap-403 (thiếu quyền, đã phủ trong Error-envelope 200-oneOf). 0 endpoint mới, 0 verb đổi.

---

## 0.1. Mobile Contract Binding (Mobile-BE — tab Calibration MVP-flow-5)

> **Ranh giới**: endpoint dùng chung 1 handler `imm11.list_calibrations` cho cả web-FE (mục #6) và mobile-BE. Contract codegen-ready cho mobile được mô tả ở SSoT riêng `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3.0.3, 22 path). Mục này là **cross-link** — KHÔNG nhân đôi schema, mọi sửa field phải đồng bộ 2 nơi.

| Mục | Giá trị |
|---|---|
| Mobile operationId | `listCalibrations` (path 47/47) |
| HTTP method / path | `GET /api/method/assetcore.api.imm11.list_calibrations` |
| Cap đọc | `calibration.read` (DocPerm) + `apply_vendor_scope("Calibration Record")` (vendor-isolation cột `asset`). **Calibration Record KHÔNG có `permission_query_conditions` riêng** (khác PM/CM `pm_work_order_query`/`asset_repair_query` — `hooks.py:388`). **Invariant count==rows** giữ vì `CalibrationRepo.list` (`BaseRepository`) đếm `count_with_or` + lấy `get_all` trên CÙNG `filters` dict. |
| Params | `filters` (JSON-string, default `'{}'`, reuse `WorkOrderFilters` — handler nhận `filters: str` không discrete) · **`mine` (int `0\|1`, default `0`, REUSE `WorkOrderMine` — `mine=1` self-scope `technician == session.user`, tab "Phiếu hiệu chuẩn của tôi" MVP-5d; xem BR-11-LISTMINE + ADR-MOBILE-019)** · `Page`/`PageSize` (`$ref`, default 1/20). **0 param required ngoài chuẩn.** Signature: `(filters, mine, page, page_size)` — `mine` chèn GIỮA filters↔page (mirror imm08/imm09). |
| Response 200 | `oneOf [CalibrationListEnvelope, Error]` Ở TẦNG response-content-schema của response-component `CalibrationList` (mirror 4 list path C7, route-by-VALUE `body.success`, **0 discriminator**) |
| Status codes | 200 / 401 (bearer hết hạn = dispatcher) / 403 (dual: dispatcher guest/no-token + in-handler cap thiếu quyền). Lỗi nghiệp vụ (malformed `filters`) = **in-handler HTTP-200 + Error envelope** — `imm11.py:72-75` đã `parse_json` trong `try/except → _err(...)` (KHÔNG raise→4xx; KHÔNG cần dời như imm09 C7). |

**`CalibrationListItem` — field-disjoint (C3-split, **17 field** `svc.list_calibrations` trả = 15 base/enrich + 2 cờ derive server-side, imm11.py:937-976 + §0.1.5):**

| # | Field | type | Ghi chú (SSoT = `imm_asset_calibration.json` DocType) |
|---|---|---|---|
| 1 | `name` | string (**required**) | PK naming-series. CAL-xxxx |
| 2 | `asset` | string | Link `AC Asset` |
| 3 | `device_model` | string | Link `IMM Device Model` |
| 4 | `calibration_type` | string enum `[External, In-House]` | Select |
| 5 | `status` | string enum `[Scheduled, Sent to Lab, In Progress, Certificate Received, Passed, Failed, Conditionally Passed, Cancelled]` | Select (8 canonical) |
| 6 | `scheduled_date` | string `format:date` | order_by `scheduled_date desc` |
| 7 | `actual_date` | string `format:date` `nullable:true` | |
| 8 | `technician` | string | Link `User` |
| 9 | `overall_result` | string enum `['', Passed, Failed, Conditionally Passed]` | Select (rỗng = chưa có) |
| 10 | `next_calibration_date` | string `format:date` `nullable:true` | |
| 11 | `lab_supplier` | string | Link `AC Supplier` |
| 12 | `is_recalibration` | **integer enum `[0, 1]`** | **Check** fieldtype → int 0/1 (KHÔNG `boolean` — Open#1 int-vs-bool sweep) |
| 13 | `asset_name` | string | enrich `AC Asset.asset_name` |
| 14 | `lab_name` | string | enrich `AC Supplier.supplier_name` |
| 15 | `technician_name` | string | enrich `User.full_name` |
| 16 | `is_overdue` | **integer enum `[0, 1]`** | Cờ hiệu chuẩn quá hạn DERIVED server-side (`int(is_calibration_overdue(row.next_calibration_date))`, BR-11-14/§0.1.5). `next_calibration_date < today`. int 0/1 (Open#1). |
| 17 | `is_due_soon` | **integer enum `[0, 1]`** | Cờ sắp đến hạn DERIVED server-side (`int(is_calibration_due_soon(row.next_calibration_date))`). `today <= next <= today+CAL_DUE_SOON_WINDOW_DAYS`. Overdue ưu tiên → 2 cờ không cùng 1. |

- **Always**: `additionalProperties:false` (closed) ở cả `CalibrationListEnvelope` (`required[success,data]`, `success.enum[true]`) lẫn `CalibrationListItem`; chỉ `name` required, field khác optional. Vì `CalibrationListItem` là **closed** (`additionalProperties:false`), 2 cờ derive `is_overdue`/`is_due_soon` PHẢI khai tường minh trong schema (không thì payload BE emit vi phạm closed-schema) — xem §0.1.5.
- **Never**: KHÔNG nhồi field financial (`gross_purchase_amount`/`accumulated_depreciation`/`current_book_value`) — `list_calibrations` vốn KHÔNG trả (né sẵn LL-BE-57 mobile-meta-no-financial); KHÔNG ép chung WO/Incident list-item; KHÔNG thêm Check field thứ 2 (chỉ `is_recalibration` là Check → đúng 1 prop integer-enum).

**ADR-IMM11-MOB-01 — `is_recalibration` = `integer enum[0,1]`, KHÔNG `boolean`:**
- *Context*: Frappe `Check` fieldtype emit `0`/`1` (int) qua REST, không phải JSON `true`/`false`.
- *Decision*: khai `type:integer enum:[0,1]` cho mọi Check field ra wire (sweep Open#1 toàn contract).
- *Consequences*: codegen sinh `int?` thay `bool?` → deser KHÔNG fail; client so `== 1`.
- *Alternatives bác*: `type:boolean` → codegen `bool` deser-fail trên payload `1` (int); coerce `bool()` ở handler → đụng `services/*.py` (vi phạm ranh giới CHỈ-yaml round này).

> **BR-11-LISTMINE (self-scope opt-in — tab "Phiếu hiệu chuẩn của tôi" MVP-5d):** `mine` là **filter ứng-dụng**, KHÔNG phải hàng-rào-bảo-mật — read-gating GIỮ DocPerm `calibration.read` + `apply_vendor_scope("Calibration Record")` (`scope.py:117` → cột `asset`, chỉ role `Vendor Engineer`). Inject `f["technician"] = frappe.session.user` ở API-layer **SAU** `apply_vendor_scope`, **TRƯỚC** `handle(svc.list_calibrations)` (mirror `api/imm08.py::list_pm_work_orders` / `api/imm09.py::list_repair_work_orders`). **KHÁC PM/CM: cột scope = `technician`** (Link `User`, reqd — `imm_asset_calibration.json:131`), KHÔNG `assigned_to` (Calibration Record không có cột này). Invariant **count==rows**: `count_with_or` + `get_all` (`BaseRepository.list` `base.py:65-71`) dùng CÙNG `filters` dict (đã có `technician`) ⇒ `pagination.total == len(data.data)`; Calibration Record KHÔNG có `permission_query_conditions` riêng ⇒ KHÔNG có nhánh count/rows lệch nhau. `mine=0`/absent ⇒ `filters` BYTE-IDENTICAL baseline (web-FE `CalibrationListView` KHÔNG đổi — phiếu giao KTV khác VẪN hiện cho Calibration Manager/QA). `mine=1` AND với mọi key trong `filters` (vd `{"status":"Scheduled"}` → phiếu hiệu chuẩn của tôi đang chờ). Quyết định thiết kế: `04_Backend_Design.md §3.x ADR-IMM11-LISTMINE` + mobile `ADR-MOBILE-019` (đóng-nốt quartet phiếu-của-tôi sau PM/CM/Incident). REUSE component `WorkOrderMine` (0 component mới); path-count mobile GIỮ 47.

### 0.1.2. Write-action binding — `submitCalibration` (COMPLETION/TERMINAL, MVP-flow-5)

> **Bối cảnh (dead-end đóng)**: KTV mở `getCalibration` detail xem 1 phiếu hiệu chuẩn nhưng **KHÔNG có endpoint hoàn thành hiệu chuẩn** trên mobile contract → MVP-flow-5 cụt. `submitCalibration` là **thành viên THỨ BA** của họ completion-action mobile (sau `submitPmResult` IMM-08 + `closeWorkOrder` IMM-09) — mắt xích còn THIẾU của chuỗi `createCalibration → … → submitCalibration`. Đây là cross-link tới SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3.0.3, hiện **30 path → +1 = 31** sau round này) — **KHÔNG nhân đôi schema**; mọi sửa field đồng bộ 2 nơi.

| Mục | Giá trị |
|---|---|
| Mobile operationId | `submitCalibration` (path 31/31, mới) |
| HTTP method / path | `POST /api/method/assetcore.api.imm11.submit_calibration` — **CHỈ key `post`** (write-action: mutate `docstatus 0 → 1`, KHÔNG idempotent, KHÔNG GET) |
| Handler | `api/imm11.py:115` `submit_calibration(name)` → `rbac.require("calibration.submit")` (`api/imm11.py:116`) → `handle(svc.submit_calibration, name)` |
| Cap | `calibration.submit` (in-handler `rbac.require` @`api/imm11.py:116`) |
| Lifecycle | COMPLETION/TERMINAL — `docstatus 0 → 1`; controller `on_submit` → `handle_calibration_pass` / `handle_calibration_fail`; `status → Passed / Failed / Conditionally Passed` (xem §10) |
| requestBody | `application/json` `$ref SubmitCalibrationRequest` — **closed `{name string}` REQUIRED, `additionalProperties:false`, 0 optional** — khớp signature `submit_calibration(name)` @`services/imm11.py:1047` (chỉ 1 positional, 0 default) |
| Response 200 | `oneOf [SubmitCalibrationEnvelope, Error]` Ở TẦNG response-content-schema (route-by-VALUE `body.success`, **0 discriminator** — pattern C6/C7, mirror `closeWorkOrder`/`submitPmResult`); cả 2 nhánh `additionalProperties:false` + disjoint required-set |
| Status codes | 200 / 401 (`Unauthorized401` — bearer hết-hạn/invalid → HTTP-401 THẬT) / 403 **SINGLE-SHAPE** `Forbidden` |

**`SubmitCalibrationResponse` — RIÊNG, closed 4-key (GROUNDED return @`services/imm11.py:1054-1059`):**

| # | Field | type | Ghi chú (SSoT = `imm_asset_calibration.json` DocType) |
|---|---|---|---|
| 1 | `name` | string (**required**) | PK echo input (`doc.name` @`services/imm11.py:1055`). CAL-YYYY-##### |
| 2 | `status` | string enum `[Scheduled, Sent to Lab, In Progress, Certificate Received, Passed, Failed, Conditionally Passed, Cancelled]` (**required**) | `doc.status` @`:1056`. Select 8-canonical 1:1 `imm_asset_calibration.json`. Sau submit-bình-thường = `Passed`/`Failed`/`Conditionally Passed` (controller on_submit) nhưng enum khai ĐỦ 8 để codegen sinh đúng máy-trạng-thái |
| 3 | `overall_result` | string enum `['', Passed, Failed, Conditionally Passed]` (**required**) | `doc.overall_result` @`:1057`. Select 4-value (rỗng `''` = chưa kết luận). Field RIÊNG của Calibration — KHÔNG có ở Pm/Repair/Incident response |
| 4 | `next_calibration_date` | string `nullable:true` (**required**) | `str(doc.next_calibration_date or "")` @`:1058` → date-string `YYYY-MM-DD` HOẶC `""` (rỗng) khi chưa có. `nullable:true` (không `format:date` cứng vì wire có thể là chuỗi rỗng) |

- **Always**: `additionalProperties:false` (closed) ở cả `SubmitCalibrationEnvelope` (`required[success,data]`, `success.enum[true]`, `data = $ref SubmitCalibrationResponse`) lẫn `SubmitCalibrationResponse` (4-key đều `required` — service luôn trả đủ 4 key @`:1054-1059`); `SubmitCalibrationRequest` `required[name]` đúng 1 prop.
- **Always**: path vào `_MVP_BUSINESS_PATHS` **VÀ** `_MVP_ACTION_ENVELOPE` (map `→ #/components/schemas/SubmitCalibrationEnvelope`) ⇒ 401/403 symmetry set **tự +1** (test so SET, KHÔNG literal).
- **Never**: KHÔNG reuse `PmSubmitResultResponse` / `CloseWorkOrderResponse` / `Resolve/IncidentActionResponse` — **C3-split cross-domain** (field-set `{name,status,overall_result,next_calibration_date}` ≠ mọi action khác; `overall_result` là field Calibration-riêng). KHÔNG thêm optional vào request (signature 0 default). KHÔNG nhồi `mttr_hours`/`is_late`/`rca_created` (không thuộc return Calibration).
- **Never**: KHÔNG để `status` lọt vào request body (server-derived qua controller on_submit — client KHÔNG set).

**403 = SINGLE-SHAPE `Forbidden` (KHÁC `reportIncident` DUAL-403):**
- *dispatcher-403* (guest/no-token) trip TRƯỚC `handle()` → HTTP-403 THẬT (`FrappeRawError`) ⇒ slot `403` = `$ref #/components/responses/Forbidden`.
- *in-handler cap-403* (`rbac.require("calibration.submit")` @`api/imm11.py:116` thiếu quyền) → lỗi nghiệp vụ **HTTP-200 + Error envelope** (in-handler, route theo `body.success`/`body.http_status`) ⇒ đã **PHỦ bởi nhánh `Error` trong 200-oneOf**, KHÔNG nhân đôi shape ở slot 403. Mirror `closeWorkOrder`/`startRepair`/`startWork` (single-shape) — **KHÔNG** dùng dual-403 như `reportIncident`.
- *Lỗi nghiệp vụ in-handler* khác (NOT_FOUND `IMM11_CAL_NOT_FOUND` @`services/imm11.py:1050` khi WO∄; `IMM11_ALREADY_SUBMITTED` @`:1052` khi `docstatus==1`) cũng ARRIVE HTTP-200 + `Error` body → gom vào nhánh `Error` 200-oneOf (KHÔNG raise→4xx).

#### ADR-IMM11-MOB-02 — `SubmitCalibrationResponse` RIÊNG (C3-split), KHÔNG reuse Pm/Repair/Incident ActionResponse

- **Status**: Accepted
- **Date**: 2026-06-16
- **Context**: `submitCalibration` là completion-action thứ 3 (sau `submitPmResult`, `closeWorkOrder`). Cám dỗ "gộp 1 `ActionResponse {name,status}` chung" cho mọi completion-action để đỡ schema. NHƯNG return THẬT @`services/imm11.py:1054-1059` trả **4-key** gồm `overall_result` (Select 4-value Calibration-riêng) + `next_calibration_date` (nullable date-string) — KHÔNG có ở Pm (`new_status`+`is_late`+`next_pm_date`+`cm_wo_created`) hay Repair (`mttr_hours`+`sla_breached`).
- **Decision**: tách `SubmitCalibrationResponse` + `SubmitCalibrationEnvelope` RIÊNG, closed 4-key, ground 1:1 return-shape. requestBody `SubmitCalibrationRequest` closed `{name}`-only.
- **Alternatives bác**: (a) reuse 1 `ActionResponse {name,status}` chung → mất `overall_result`/`next_calibration_date` (under-specify, codegen client KHÔNG đọc được kết luận hiệu chuẩn → KTV không thấy Pass/Fail); (b) `oneOf` chung cho cả 3 action → required-set không disjoint, route-by-value mơ hồ.
- **Consequences**: +1 schema-pair (`SubmitCalibrationResponse`/`SubmitCalibrationEnvelope`) + path 31; test `TestMobileSubmitCalibrationContract` guard C3-split (assert response field-set ≠ Pm/Repair/Incident). Nhất quán với ADR-MOBILE-007 (close/submit action RIÊNG-schema) + `C3-split` family. **0 đụng** `api/imm11.py` + `services/imm11.py` (handler + cap-gate + return-shape đã sẵn @source) ⇒ KHÔNG reload gunicorn / migrate / commit.

> **Acceptance contract (chock cho BE/Test — Bước 4)**: YAML `30 → 31` path / `31` operationId (`submitCalibration` mới, unique camelCase, 0 dangling `$ref`). Test `assetcore.tests.test_mobile_oas` XANH; `_EXPECTED_TEST_COUNT 265 → 274` (+9 TC `TestMobileSubmitCalibrationContract a..i`, gồm live-signature parity TC-i `inspect.signature(imm11.submit_calibration) == {name}`). `test_mobile_docset` re-run THẬT (KHÔNG tin doc — phiên trước có 1 FAIL orphan ADR). Working-tree để USER review.

### 0.1.3. Read-detail binding — `getCalibration.allowed_transitions[]` (server-driven CTA, MVP-flow-5 detail)

> **Bối cảnh (ASYMMETRY R3 ĐÓNG KÍN)**: KTV mở `getCalibration` detail → cần biết "từ status hiện tại được phép chuyển sang state nào" để render nút workflow. 3 `*Detail` kia đã emit `allowed_transitions[]` (`IncidentDetail` R3 + `PmWorkOrderDetail` R21 + `RepairWorkOrderDetail` R22); `CalibrationDetail` là `*Detail` **THỨ TƯ và CUỐI** còn THIẾU ⇒ vòng này đóng kín ASYMMETRY R3: **cả 4/4 `*Detail` đều emit `allowed_transitions[]`**. Cross-link SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (`CalibrationDetail` line ~3607) — KHÔNG nhân đôi schema.

| Mục | Giá trị |
|---|---|
| Mobile operationId | `getCalibration` (GET, KHÔNG path mới — `33` path GIỮ NGUYÊN) |
| HTTP method / path | `GET /api/method/assetcore.api.imm11.get_calibration` (handler `api/imm11.py:81` — vendor IDOR guard `assert_vendor_can_access` + `handle(svc.get_calibration, name)`, **KHÔNG đổi**) |
| Cap đọc | `calibration.read` (qua vendor guard) |
| Delta contract | `CalibrationDetail` (line ~3607) thêm property `allowed_transitions: {type: array, items: {type: string}}` — **NOT trong `required`** (`required` GIỮ `[name]`, không bắt buộc), `additionalProperties:true` GIỮ. Mirror `IncidentDetail`/`PmWorkOrderDetail`/`RepairWorkOrderDetail`. |
| Status codes | 200 / 401 (bearer hết hạn = dispatcher) / 403 (dual: dispatcher guest/no-token + in-handler cap thiếu quyền). Lỗi nghiệp vụ (NOT_FOUND) = **in-handler HTTP-200 + Error envelope** (`get_calibration` → `nthrow(MSG.IMM11_CAL_NOT_FOUND)` → handle → 200+Error). |

**`allowed_transitions[]` — codomain (SSoT = `services/imm11.py:_CAL_VALID_TRANSITIONS`, GROUNDED `imm_11_calibration_workflow.json` edge-by-edge):**

| status hiện tại | allowed_transitions[] | Ghi chú |
|---|---|---|
| `Scheduled` | `[In Progress, Sent to Lab, Cancelled]` | bắt đầu / gửi lab / hủy |
| `In Progress` | `[Passed, Failed, Conditionally Passed, Cancelled]` | kết luận in-house / hủy |
| `Sent to Lab` | `[Certificate Received]` | nhận chứng chỉ |
| `Certificate Received` | `[Passed, Failed, Conditionally Passed]` | phê duyệt theo chứng chỉ |
| `Failed` | `[Conditionally Passed]` | CAPA hoàn tất → có điều kiện |
| `Passed` | `[]` | terminal (docstatus=1) |
| `Conditionally Passed` | `[]` | terminal (docstatus=1) |
| `Cancelled` | `[]` | terminal (docstatus=2) |

- **Always**: emit key LUÔN có (kể cả `[]`); phần tử ⊆ `CalibrationResult` enum (8 canonical); FE render CTA theo list (KHÔNG hardcode `status→button` client-side = dead-gate). Items KHÔNG enum-bound cứng trong yaml (né drift; codomain-check ở guard test phía service).
- **Never**: ❌ đổi signature `get_calibration(name)` · ❌ đổi handler `api/imm11.py:81` · ❌ đưa `allowed_transitions` vào `required` · ❌ string-literal key trong map (dùng `CalibrationResult.*`).

> ⚠️ **Data-quality (workflow JSON)**: `imm_11_calibration_workflow.json` có **13 dòng `transitions[]`** = **12 cạnh unique** (`Failed → Conditionally Passed` lặp 2 lần — dòng thừa, không đổi semantics). Guard SSoT-divergence so map↔workflow **theo SET (tự dedup)** ⇒ map (12 cạnh) khớp; assertion count thô giữ `len(transitions)==13`. Chi tiết + ADR-IMM11-04 ở `04_Backend_Design.md §3 / §3.1`.

> **Acceptance contract (chock cho BE/Test — Bước 4)**: (1) `services/imm11.py` thêm `_CAL_VALID_TRANSITIONS` (dict keyed `CalibrationResult.*`) + `get_calibration` emit `data["allowed_transitions"]=_CAL_VALID_TRANSITIONS.get(doc.status,[])` (mirror imm09.py R22 / imm08.py R21) — KHÔNG đổi signature, KHÔNG đổi `api/imm11.py:81`. (2) YAML `CalibrationDetail` (line ~3607) thêm `allowed_transitions: array<string>`, NOT-required, AP:true GIỮ — `33` path GIỮ (KHÔNG path mới), `33` opId unique camelCase, 0 dangling `$ref`, `safe_load` OK. (3) Guard XANH @source: `test_mobile_oas` `_EXPECTED_TEST_COUNT 304 → 310` (+6 TC `TestMobileCalibrationAllowedTransitionsContract a..f`); `test_imm11` `TestCalibrationAllowedTransitions` (+2 BE unit TC: codomain⊆enum + map==workflow JSON edges theo SET + live `get_calibration` emit Scheduled/In Progress/Passed-terminal); `test_mobile_docset` `_GUARD_SUITE_SUM 447 → 453` + `_MOBILE_OAS_TOTAL 473 → 479` + `cal_allowed_transitions_delta=6` trong `test_09` baseline. `test_imm08`/`test_imm09`/`test_imm12` untouched GREEN (R21/R22/R3 không regress). (4) ASYMMETRY R3 đóng kín: `grep allowed_transitions` trong `CalibrationDetail` block = PRESENT (trước = 0). Live HTTP cần reload gunicorn (`--preload`) — guard in-process KHÔNG cần (HARD-STOP user). Working-tree để USER review.

### 0.1.4. Write-action binding — `addMeasurement` (MEASUREMENT-ENTRY, mắt-xích-GIỮA MVP-flow-5)

> **Bối cảnh (dead-end GIỮA đóng)**: KTV mở `getCalibration` detail (`Scheduled`/`In Progress`) cần **ghi N điểm-đo** (`parameter_name`/`nominal_value`/`tolerance ±`/`measured_value`) vào child table `measurements` TRƯỚC khi `submitCalibration` chốt verdict. Mắt-xích-GIỮA `addMeasurement` còn THIẾU ⇒ chuỗi `createCalibration → … → submitCalibration` cụt ở giữa, `submitCalibration` tính `overall_result` trên measurement-set **RỖNG**. Cross-link SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3.0.3, hiện **42 path → +1 = 43** sau round này) + [`docs/mobile/ADR-MOBILE-011.md`](../mobile/ADR-MOBILE-011.md) + [`04-api-contract.md §8.24`](../mobile/04-api-contract.md) — **KHÔNG nhân đôi schema**; mọi sửa field đồng bộ 2 nơi.

| Mục | Giá trị |
|---|---|
| Mobile operationId | `addMeasurement` (path 43/43, mới), tag `calibration` |
| HTTP method / path | `POST /api/method/assetcore.api.imm11.add_measurement` — **CHỈ key `post` SAU flip** (write-action: append child-row, **KHÔNG idempotent** — N call = N row, KHÔNG GET) |
| Handler | `api/imm11.py:121` `add_measurement(name, parameter_name, unit, nominal_value, tolerance_positive, tolerance_negative, measured_value=None)` → `rbac.require("calibration.write")` (`api/imm11.py:124`) → `handle(svc.add_measurement, name, **kwargs)` (`:125-132`) |
| **⚡ VERB-FLIP-THIS-ROUND** | decorator `api/imm11.py:120` flip **bare `@frappe.whitelist()` → `@frappe.whitelist(methods=['POST'])`** — ĐÚNG **1 dòng** (`git diff api/imm11.py` = 1 dòng decorator; signature/body/cap UNCHANGED). Đóng **verb-parity gap R33 BỎ SÓT** (R33 đã flip `create_calibration`/`submit_calibration`/`submit_pm_result`, SÓT `add_measurement`). Sau flip POST-only ⇒ KHÔNG verb-divergence ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()` |
| Cap | `calibration.write` (in-handler `rbac.require` @`api/imm11.py:124`) |
| Lifecycle | MEASUREMENT-ENTRY — append 1 row vào `measurements` (`services/imm11.py:1115-1122`) + `CalibrationRepo.save` (`:1123`); **KHÔNG đổi `docstatus`** (giữ draft 0; pre-condition `docstatus==0`) |
| requestBody | content **oneOf** `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict`) `$ref AddMeasurementRequest` — `required:true` (component); path-level `$ref`-ONLY (G-OAS-403-DISAMBIG) |
| Response 200 | `oneOf [AddMeasurementEnvelope, Error]` Ở TẦNG response-content-schema (route-by-VALUE `body.success`, **0 discriminator** — pattern C6/C7); cả 2 nhánh `additionalProperties:false` + disjoint required-set |
| Status codes | 200 / 401 (`Unauthorized401` bearer hết-hạn/invalid → HTTP-401 THẬT) / 403 **SINGLE-SHAPE** `Forbidden` |

**`AddMeasurementRequest` — closed, required EXACT 6 + optional `measured_value` (GROUNDED signature @`api/imm11.py:121-123` + svc @`services/imm11.py:1107-1109`):**

| # | Field | type | Required? | Ghi chú |
|---|---|---|---|---|
| 1 | `name` | string | ✓ required | PK phiếu Calibration (positional) |
| 2 | `parameter_name` | string | ✓ required | Tên tham-số đo (vd "Nhiệt độ") |
| 3 | `unit` | string | ✓ required | Đơn-vị (vd "°C") |
| 4 | `nominal_value` | number | ✓ required | Giá-trị danh-định |
| 5 | `tolerance_positive` | number | ✓ required | Dung-sai dương (+) |
| 6 | `tolerance_negative` | number | ✓ required | Dung-sai âm (−) |
| 7 | `measured_value` | number `nullable:true` | optional | Giá-trị đo thực-tế — `measured_value: float = None` @`api/imm11.py:123` (KTV có thể ghi tham-số trước, đo sau) |

**`AddMeasurementResponse` — RIÊNG, closed EXACT 2-key (GROUNDED return @`services/imm11.py:1124`):**

| # | Field | type | Ghi chú |
|---|---|---|---|
| 1 | `name` | string (**required**) | PK echo input (`doc.name`). CAL-YYYY-##### |
| 2 | `measurement_count` | **integer** (**required**) | `len(doc.measurements)` — số row child-table SAU append. **GENUINE integer count** (có thể >1 — N điểm-đo), **KHÔNG `enum[0,1]`** (không phải Check-field; precedent `updated`/`requestSpareParts` ADR-MOBILE-010). Client hiển thị "đã ghi N điểm-đo" |

- **Always**: `additionalProperties:false` (closed) ở cả `AddMeasurementEnvelope` (`required[success,data]`, `success.enum[true]`, `data = $ref AddMeasurementResponse`) lẫn `AddMeasurementResponse` (2-key đều `required`) lẫn `AddMeasurementRequest`; request `required` EXACT 6, `measured_value` optional.
- **Always**: path vào `_MVP_BUSINESS_PATHS` **VÀ** `_MVP_ACTION_ENVELOPE` (map `→ #/components/schemas/AddMeasurementEnvelope`) ⇒ 401/403 symmetry set **tự +1** (test so SET).
- **Never**: KHÔNG reuse `SubmitCalibrationResponse` 4-key / `*ActionResponse` 2-key `{name,status}` — **C3-split** (field-set `{name,measurement_count}` ≠ mọi action khác; `add_measurement` KHÔNG trả `status`/`overall_result`). KHÔNG khai `measurement_count` là `integer enum[0,1]` (số đếm thật, >1 hợp lệ). KHÔNG đưa `measured_value` vào `required`. KHÔNG bịa status-line 404/409 (xem dưới).

**403 = SINGLE-SHAPE `Forbidden` (KHÁC `reportIncident` DUAL-403):**
- *dispatcher-403* (guest/no-token) trip TRƯỚC `handle()` → HTTP-403 THẬT (`FrappeRawError`) ⇒ slot `403` = `$ref #/components/responses/Forbidden`.
- *in-handler cap-403* (`rbac.require("calibration.write")` @`api/imm11.py:124` thiếu quyền) → lỗi nghiệp vụ **HTTP-200 + Error envelope** ⇒ đã **PHỦ bởi nhánh `Error` trong 200-oneOf**, KHÔNG nhân đôi shape ở slot 403. Mirror `submitCalibration`/`startRepair` — **KHÔNG** dual-403.
- *Lỗi nghiệp vụ in-handler*: phiếu∄ `IMM11_CAL_NOT_FOUND` @`services/imm11.py:1112` (→ `code=NOT_FOUND http_status=404`) + đã-submit `IMM11_ALREADY_SUBMITTED` khi `docstatus==1` @`services/imm11.py:1114` (→ `code=CONFLICT http_status=409`) ARRIVE HTTP-200 + `Error` body (quirk §5, KHÔNG status-line) → gom vào nhánh `Error` 200-oneOf; route `body.http_status` ∈ bounded enum `{400,401,403,404,409,413,422,429,500}` (R11, **enum ĐÃ ⊇ {404,409} KHÔNG đổi**).

#### ADR-IMM11-MOB-03 — `addMeasurement` VERB-FLIP-THIS-ROUND + `AddMeasurementResponse` RIÊNG 2-key (`measurement_count` GENUINE integer)

- **Status**: Accepted
- **Date**: 2026-06-27
- **Context**: `addMeasurement` là mắt-xích-GIỮA calibration-detail còn THIẾU. Handler `add_measurement` `api/imm11.py:120` còn bare `@frappe.whitelist()` (nhận GET) — **verb-parity gap R33 BỎ SÓT** (R33 đã flip 3 write-action khác + làm rỗng `_PARITY_VERB_ALLOWLIST`). Return THẬT 2-key `{name, measurement_count}` (`services/imm11.py:1124`).
- **Decision**: (1) flip decorator `api/imm11.py:120` bare→`methods=['POST']` **NGAY** (1 dòng, KHÔNG backlog như §8.15 từng làm) ⇒ contract POST khớp source ⇒ KHÔNG verb-divergence ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. (2) `AddMeasurementResponse`/`AddMeasurementEnvelope` RIÊNG closed 2-key, `measurement_count` = `type:integer` THUẦN (số đếm thật). requestBody `AddMeasurementRequest` closed required-EXACT-6 + optional `measured_value` nullable, content oneOf json+form.
- **Alternatives bác**: (a) reuse `SubmitCalibrationResponse`/`*ActionResponse` → DROP `measurement_count` hoặc bịa `status` không có trong return; (b) `measurement_count` `enum[0,1]` → sai-deser khi N≥2; (c) đẩy verb-flip→backlog + tái-mở `_PARITY_VERB_ALLOWLIST` → đi ngược R33 closure (flip 1 dòng rẻ hơn track backlog).
- **Consequences**: +1 schema-pair (`AddMeasurementResponse`/`AddMeasurementEnvelope`) + 1 request-schema + 1 requestBody-component + path 43. **⚠️ ĐỤNG 1 dòng `api/imm11.py:120`** (verb-flip) ⇒ shift runtime get/post stat (get 235→234 / post 253→254) → **re-baseline @source** `test_oas_d12`/`d17` (KHÔNG tin tuyệt đối số acceptance). Nhất quán ADR-MOBILE-011 + C3-split family. Sau flip cần USER reload gunicorn `--preload` (LIVE reject GET 405) — guard in-process KHÔNG cần. KHÔNG migrate/commit (HARD-STOP USER).

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) flip `api/imm11.py:120` bare→`@frappe.whitelist(methods=['POST'])` (ĐÚNG 1 dòng; signature/body/`rbac.require('calibration.write')` UNCHANGED). (2) YAML `42 → 43` path / `43` operationId (`addMeasurement` mới, unique camelCase, tag `calibration`, 0 dangling `$ref`, `info.version` GIỮ `0.1.0-skeleton`, `safe_load` OK). (3) Guard XANH @source (`bench --site miyano run-tests`): `test_mobile_oas` `_EXPECTED_TEST_COUNT` **bump từ 397** (+ `TestMobileAddMeasurementContract a..j`, gồm TC-i live-signature parity 7-param + TC-j git-diff-1-dòng + `_PARITY_VERB_ALLOWLIST`==set()); re-baseline `test_oas_d12` (`_BASELINE_GET 235→234`) + `test_oas_d17` (`get_count 235→234`/`post_count 253→254`) + re-verify ALL 13 `test_oas_*`; `test_mobile_docset` (9, reconcile `_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL`/`_GUARD_SUITE_EXPECTED`) + `test_mobile_security_gate` (no-regress) + `test_imm11` (no-regress). (4) RED-before/GREEN-after chứng minh cho MỌI TC mới. Live HTTP cần USER reload (`--preload`) — KHÔNG curl-verify LIVE (LL-DEPLOY-07). Working-tree để USER review.

---

### 0.1.5. Read-flag binding — `is_overdue` / `is_due_soon` (SERVER-FLAG SSoT, CR-02 · listCalibrations + getCalibration)

> **Bối cảnh (server-flag SSoT).** Module Hiệu chuẩn mobile cần cờ **quá hạn / sắp hạn** trên MỖI phiếu để KTV ưu tiên — nhưng KHÔNG được để consumer so `next_calibration_date` với đồng-hồ-thiết-bị (client-clock). Derive SERVER-SIDE 2 cờ `is_overdue`/`is_due_soon` (int 0/1) trên `next_calibration_date` của CHÍNH bản ghi, dùng CHUNG predicate thuần `is_calibration_overdue`/`is_calibration_due_soon` (`services/imm11.py:97-114`, §04 §4.1.1) — **KHÔNG re-implement**, **KHÔNG thêm query DB** (field đã trả sẵn). Đối xứng `calibration_overdue` của `getAssetScanInfo` (imm00, CR-21) + `is_response_breached`/`is_resolution_breached` của `getIncident` (imm12, INV-SLA-5). Ref bền: `memory/overdue_server_flag_ssot.md`. Cross-link SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — sửa field đồng bộ 2 nơi; **path-count mobile GIỮ nguyên** (đây là +property, KHÔNG path/opId mới).

| Endpoint | Nơi emit | Schema OAS + property |
|---|---|---|
| `listCalibrations` (`imm11.list_calibrations`) | vòng `for r in rows` (`imm11.py:1012-1015`) — mỗi row | `CalibrationListItem` += `is_overdue`, `is_due_soon` (`integer enum[0,1]`). Vì item `additionalProperties:false` → **BẮT BUỘC** khai. |
| `getCalibration` (`imm11.get_calibration`) | sau build `data` (`imm11.py:1023-1029`), cạnh `allowed_transitions` | `CalibrationDetail` += `is_overdue`, `is_due_soon` (`integer enum[0,1]`, NOT-required, AP:true GIỮ). |

**Boundaries:**
- **Always**: 2 cờ = `int(predicate(record.next_calibration_date, ref))`; ref = `getdate(nowdate())` server, tính 1 lần/call; emit trên CẢ list-row lẫn detail; `int` 0/1 (KHÔNG bool). Parity list==detail tại cùng ref-date (INV-CALFLAG-1). `None` → cả 2 = 0. Overdue ưu tiên (2 cờ không cùng 1).
- **Never**: ❌ đổi signature `list_calibrations`/`get_calibration` · ❌ đổi handler `api/imm11.py:71`/`:81` · ❌ thêm query DB / JOIN Schedule · ❌ dùng `_overdue_asset_ids` (asset-SoT ≠ record-flag — ADR-IMM11-05) · ❌ re-implement so-ngày inline (dùng predicate chung) · ❌ đưa cờ vào `required` · ❌ thêm field web-only (cờ có trong CẢ 2 contract) · ❌ `type:boolean` (Open#1).

#### ADR-IMM11-MOB-04 — `is_overdue`/`is_due_soon` = `integer enum[0,1]` derive server, KHÔNG `boolean`, KHÔNG re-query

- **Status**: Accepted
- **Date**: 2026-07-09
- **Context**: CR-02 cần cờ quá-hạn/sắp-hạn per-record cho tab Hiệu chuẩn mobile. Predicate thuần đã tồn tại (`is_calibration_overdue`/`is_calibration_due_soon` + hằng `CAL_DUE_SOON_WINDOW_DAYS=30`). `next_calibration_date` đã có trong `fields=[...]` (list) và `doc.as_dict()` (detail).
- **Decision**: emit 2 cờ `integer enum[0,1]` bằng cách bọc `int(predicate(...))` trong vòng-lặp-đã-có (list) / khối build `data` (detail). 0 query mới, 0 signature-change. Khai property tường minh trong `CalibrationListItem` (closed) + `CalibrationDetail`.
- **Alternatives bác**: (a) `type:boolean` → codegen `bool` deser-fail trên payload `1` (int) — vi phạm Open#1 (mirror `is_recalibration`/`is_response_breached`). (b) Join Schedule / `_overdue_asset_ids` per row → +N query + sai ngữ nghĩa (asset-level). (c) So-ngày client-side ở app → client-clock drift → sai an-toàn (server-flag SSoT là bắt buộc).
- **Consequences**: `CalibrationListItem` 15→17 field; `CalibrationDetail` +2 property. Consumer (mobile + web-FE) CHỈ render cờ. ⚠️ ĐỘNG `services/imm11.py` (list_calibrations + get_calibration) → cần USER reload gunicorn `--preload` để LIVE emit — guard in-process KHÔNG cần. Cùng họ server-flag với CR-21 (scan) + INV-SLA-5 (incident).

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) `services/imm11.py`: `list_calibrations` gán mỗi row `r["is_overdue"]=int(is_calibration_overdue(r.get("next_calibration_date"), ref))` + `r["is_due_soon"]=int(is_calibration_due_soon(..., ref))` (ref = `getdate(nowdate())` tính 1 lần TRƯỚC vòng lặp); `get_calibration` gán `data["is_overdue"]`/`data["is_due_soon"]` tương tự trên `data["next_calibration_date"]`. KHÔNG re-implement predicate, KHÔNG thêm query. (2) YAML: `CalibrationListItem` += `is_overdue`/`is_due_soon` (`integer enum[0,1]`); `CalibrationDetail` += 2 property tương tự (NOT-required, AP:true GIỮ). **Path-count/opId GIỮ NGUYÊN** (0 path mới), 0 dangling `$ref`, `safe_load` OK. (3) Guard XANH @source (`bench --site miyano run-tests`): `test_imm11` += `TestCalibrationReadFlags` — acceptance matrix (overdue/due_soon/beyond/None) + **INV parity list==detail cùng ref-date** + None-guard → `Ran N OK` (XANH THẬT); `test_mobile_oas` += TC contract-shape 2 property × 2 schema (`integer enum[0,1]`) + reconcile `_EXPECTED_TEST_COUNT`; `test_mobile_docset` reconcile `_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL`. (4) Consumer test/audit: KHÔNG có nơi nào so `next_calibration_date` với client-clock (grep FE/consumer = 0). (5) RED-before/GREEN-after cho MỌI TC mới. Live HTTP cần USER reload (`--preload`, HARD-STOP). Working-tree để USER review.

### 0.1.6. Write-action binding — `sendToLab` (EXTERNAL DISPATCH, MỞ nhánh External-calibration · CR-CAL-EXT-01)

> **Bối cảnh (dead-end nhánh External mở)**: Module Hiệu chuẩn có **2 nhánh vòng-đời** theo `calibration_type` — **In-House** (`createCalibration`→`addMeasurement`×N→`submitCalibration`, ĐÃ curate mobile §0.1.2/§0.1.4) và **External/NGOẠI KIỂM** (`createCalibration(External)`→**`sendToLab`**→`receiveCertificate`→`submitCalibration`). Nhánh External **CHƯA có action nào** trên mobile contract → tab Calibration External **cụt** sau khi tạo phiếu. `sendToLab` là **mắt-xích ĐẦU** nhánh External — dispatch phiếu đi lab: `Scheduled`/`In Progress` → **`Sent to Lab`** (+ asset `ACTIVE`→`CALIBRATING` + lifecycle-event `Calibration Sent To Lab`). Cross-link SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3.0.3, hiện **62 path → +1 = 63** sau round này — số grounded @source 2026-07-11 sau ADR-030, **BE grep-verify TRƯỚC bump**) + [`docs/mobile/ADR-MOBILE-031.md`](../mobile/ADR-MOBILE-031.md) + [`04-api-contract.md §8.37`](../mobile/04-api-contract.md) — **KHÔNG nhân đôi schema**; mọi sửa field đồng bộ 2 nơi. `receiveCertificate`+`cancelCalibration` = **forward-reserve** vòng kế.

| Mục | Giá trị |
|---|---|
| Mobile operationId | `sendToLab` (POST, path 63/63 mới), tag `calibration` |
| Handler LIVE | `assetcore.api.imm11.send_to_lab` def@`api/imm11.py:169-170` (`@whitelist(methods=["POST"])`@168, `rbac.require("cal.send_lab")`@171 → `("IMM Asset Calibration","write")` `rbac.py:109`, `handle(svc.send_to_lab,…)`@172-176) |
| Service LIVE | `services/imm11.py:1270` — 4-nhánh ladder + patch + asset-transition + audit; `return {name,status,sent_date}`@1304 EXACT 3-key |
| requestBody | 2 media-type `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict` §9) cùng `$ref SendToLabRequest` — **∈ `_REQBODY_PATHS`**, subject sweep `_RPC_FORM_JSON_MEDIA` (**KHÁC 3 path multipart** ∉ `_REQBODY_PATHS` + có hằng exempt) |

**`SendToLabRequest`** — CLOSED (`additionalProperties:false`) `required[name]` EXACT **4 prop** khớp HỆT signature @169-170 (chỉ `name` bắt buộc):

| # | Field | Type | Ground |
|---|---|---|---|
| 1 | `name` | string (**required**) | name IMM Asset Calibration (phiếu External đang mở). @169 `form_dict` |
| 2 | `sent_date` | string, nullable | absent/`null` ⇒ service default `nowdate()` @1285. `sent_date=None` @169 optional |
| 3 | `lab_supplier` | string, nullable | NCC/lab nhận (Link Supplier, mô hình `string`); absent ⇒ KHÔNG patch. optional |
| 4 | `lab_contract_ref` | string, nullable | tham chiếu HĐ/PO gửi lab (free-text); absent ⇒ KHÔNG patch. optional |

**`SendToLabResponse`** (data) — CLOSED `required[name,status,sent_date]` EXACT **3 prop** (GROUNDED `return {name,status,sent_date}` @1304):

| # | Field | Type | Ground |
|---|---|---|---|
| 1 | `name` | string (**required**) | echo name phiếu @1304 |
| 2 | `status` | string **enum 8-canonical** `[Scheduled, Sent to Lab, In Progress, Certificate Received, Passed, Failed, Conditionally Passed, Cancelled]` (**required**) | `patch["status"]` @1304 = `CalibrationResult.SENT_TO_LAB` @1285 (`constants.py:123`). **Giá-trị trả LUÔN `"Sent to Lab"`** — khai đủ 8 (Select 1:1) để codegen sinh đúng máy-trạng-thái |
| 3 | `sent_date` | string (date) (**required**) | `patch["sent_date"]` @1304 = `sent_date or nowdate()` @1285 (LUÔN resolved) |

**200 = oneOf [`SendToLabResponseEnvelope`, `Error`]** (Decision-B route-by-VALUE `body.success`, 0 discriminator). Nhánh `Error` gom **4 nhánh service** ARRIVE HTTP-200 `Error.http_status` ⊇ **{404,409,422}**: NOT_FOUND 404 (doc∄ @1276) → CONFLICT 409 (docstatus==1 đã-chốt @1278) → VALIDATION 422 (không-External @1280) → CONFLICT 409 (sai-state ∉{Scheduled,In Progress} @1282) — grounded `messages.py` (404@904/409@939/422@953/409@960).

#### ADR-IMM11-SENDLAB — `sendToLab` write-ACTION json+form + `SendToLabResponse` RIÊNG 3-prop + 403 SINGLE qua `rbac.require` same-shape
- **Status**: Accepted · **Date**: 2026-07-11
- **Context**: Nhánh External-calibration còn cụt trên mobile (in-house đã đủ). `send_to_lab` LIVE @source (handler+service+cap-gate+return-shape sẵn). Cần contract để codegen sinh method dispatch-lab.
- **Decision**: Curate 1 path POST, requestBody 2 media-type (json+form §9, KHÔNG multipart — action state-machine KHÔNG upload), **3 schema RIÊNG** (`SendToLabRequest`/`SendToLabResponse`/`SendToLabResponseEnvelope`), 200 = oneOf [Env, Error], **403 SINGLE-SHAPE `Forbidden`**. Tag `calibration`. Path 62→63.
- **Alternatives (loại)**: multipart body (sai transport — đọc `form_dict`) · reuse `SubmitCalibrationResponse` 4-prop / `CreateCalibrationResponse` 2-prop (svc trả 3-key → `additionalProperties:false` FAIL — số key response drift theo op) · dual-403 (cap-403 CÙNG shape dispatcher) · SINGLE-200 (giấu 4 nhánh Error) · `required[name,sent_date]` (sent_date optional @169).
- **Consequences**: +1 path +3 schema RIÊNG (PURE-YAML). **0 đụng** `api/imm11.py`+`services/imm11.py` (handler+service+cap-gate+return-shape đã sẵn @source) ⇒ KHÔNG reload/migrate/commit. C3-split family (như submit/create response RIÊNG). Test `TestMobileSendToLabContract` guard response field-set ≠ Submit/Create.
- **⚠️ Self-Correction (rationale 403 — grounded, sửa chữ acceptance Bước-2)**: acceptance đề mục ghi "cap-403 (cal.send_lab) ... **đã phủ bởi nhánh Error của 200-oneOf** ⇒ KHÔNG dual-403 (mirror ADR-027 acknowledgeIncident)". KẾT-LUẬN (403 SINGLE) ĐÚNG nhưng RATIONALE SAI @source: cap-403 đến từ `rbac.require("cal.send_lab")` @171 = `frappe.throw(PermissionError)` **TRƯỚC** `handle()` → **raw HTTP-403 status-line** (`FrappeRawError`), **KHÔNG** qua `_err`/200-oneOf. 403 SINGLE vì cap-403 **CÙNG SHAPE** dispatcher-403 (same-shape collapse), mirror same-module **`createCalibration` §8.6 / `submitCalibration` §8.15** (`rbac.require`) — KHÔNG phải cơ-chế `_err(403)`@200 của acknowledgeIncident/attach-photo. Cái được 200-oneOf Error phủ = **4 nhánh service {404,409,422}** (KHÔNG có 403 trong đó).

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) YAML `62 → 63` path / `63` operationId (`sendToLab` mới, unique camelCase, tag `calibration`, 0 dangling `$ref`, `safe_load` OK); requestBody `required:true` content 2 media-type json+form cùng `$ref SendToLabRequest`; 200 oneOf [`SendToLabResponseEnvelope`, Error]; slot `{200,401,403}` (`401 Unauthorized401` + **`403 Forbidden` SINGLE-SHAPE** — KHÔNG dual). (2) +3 schema closed (`SendToLabRequest` `req[name]` 4-prop 3-nullable · `SendToLabResponse` `req[name,status,sent_date]` 3-prop `status` enum 8-canonical · `SendToLabResponseEnvelope`) tái-dùng `Unauthorized401`/`Forbidden`/`Error`; naming-guard `SendToLab*` ∩ (`SubmitCalibration*`∪`CreateCalibration*`∪`AddMeasurement*`) == ∅. (3) Guard XANH @source (`bench --site miyano run-tests --app assetcore --module assetcore.tests.test_mobile_oas`): `_EXPECTED_TEST_COUNT` **571→581** (+10 TC `TestMobileSendToLabContract a..j`, gồm TC-g response-3-prop-status-enum-8-canonical anti-drift vs Submit-4/Create-2, TC-i live-signature parity `inspect.signature(imm11.send_to_lab)=={name,sent_date,lab_supplier,lab_contract_ref}`, TC-j git-diff-0-hunk pure-yaml) + c5 **51→52** + membership `_MVP_ACTION_ENVELOPE`+`_REQBODY_PATHS`; `test_mobile_docset` **Ran 9 OK** (reconcile `_GUARD_SUITE_SUM` **714→724** + `_MOBILE_OAS_TOTAL` **740→750**); `test_mobile_security_gate` GREEN; `test_oas_d12/d15/d17` **UNCHANGED** (pure mobile-yaml — KHÔNG đụng `generate_spec`). ⚠️ Baseline 571/62/51/714/740 grounded sau ADR-030 — **BE grep-verify @source TRƯỚC bump** (đa-phiên race). (4) **CONTRACT-ONLY**: `git diff` `api/imm11.py`+`services/imm11.py` vùng `send_to_lab` = 0 hunk MỚI (registry-resolvability KHÔNG HEAD-diff). RED-before/GREEN-after cho MỌI TC mới. KHÔNG reload/migrate/commit (HARD-STOP USER — working-tree để USER review).

---

### 0.1.7. Write-action binding — `receiveCertificate` (EXTERNAL RECEIVE-CERT, mắt-xích GIỮA nhánh External-calibration · CR-CAL-EXT-02)

> **Bối cảnh (tiếp nối nhánh External)**: Nhánh **External/NGOẠI KIỂM** = `createCalibration(External)`→**`sendToLab`** (§0.1.6, mở nhánh, `Scheduled`/`In Progress`→`Sent to Lab`)→**`receiveCertificate`**→`submitCalibration` (chốt). `sendToLab` (mắt-xích ĐẦU) ĐÃ curate §0.1.6. `receiveCertificate` là **mắt-xích GIỮA** — sau khi lab trả chứng chỉ, KTV nhập tệp/số/ngày cert để phiếu chuyển `Sent to Lab` → **`In Progress`** (chờ nhập measurement + `submitCalibration` chốt verdict). Cross-link SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3.0.3, hiện **63 path → +1 = 64** sau round này — số grounded @source 2026-07-11 sau ADR-031/sendToLab, **BE grep-verify TRƯỚC bump**) + [`docs/mobile/ADR-MOBILE-032.md`](../mobile/ADR-MOBILE-032.md) + [`04-api-contract.md §8.38`](../mobile/04-api-contract.md) — **KHÔNG nhân đôi schema**; mọi sửa field đồng bộ 2 nơi. `cancelCalibration` = **forward-reserve** vòng kế (nhánh External sẽ HOÀN TẤT). ⚠️ **Self-Correction đánh-số**: ADR = **MOBILE-032** (đề mục Bước-2 ghi 031 — numbering-drift do `sendToLab` R10 song song đã chiếm 031; narrative §8.38, binding §0.1.7).

| Mục | Giá trị |
|---|---|
| Mobile operationId | `receiveCertificate` (POST, path 64/64 mới), tag `calibration` |
| Handler LIVE | `assetcore.api.imm11.receive_certificate` def@`api/imm11.py:180-183` (`@whitelist(methods=["POST"])`@179, `rbac.require("calibration.write")`@184 → `("IMM Asset Calibration","write")` cap-family `addMeasurement`@133, `handle(svc.receive_certificate,…)`@185-192) |
| Service LIVE | `services/imm11.py:1307` — 4-nhánh ladder + patch status=`In Progress` + audit; `return {name,status,certificate_number}`@1339-1340 EXACT 3-key |
| requestBody | 2 media-type `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict` §9) cùng `$ref ReceiveCertificateRequest` — **∈ `_REQBODY_PATHS`**, subject sweep `_RPC_FORM_JSON_MEDIA` (mirror `sendToLab`, **KHÁC 3 path multipart** ∉ `_REQBODY_PATHS`). **`certificate_file` = `string` URL KHÔNG `format:binary`** (anti-nhầm multipart) |

**`ReceiveCertificateRequest`** — CLOSED (`additionalProperties:false`) `required[name, certificate_file, certificate_number, certificate_date]` EXACT **6 prop** khớp HỆT signature @180-183 (**4 bắt buộc** — KHÁC `sendToLab` chỉ `name`):

| # | Field | Type | Ground |
|---|---|---|---|
| 1 | `name` | string (**required**) | name IMM Asset Calibration (phiếu External đang `Sent to Lab`). @180 `form_dict` |
| 2 | `certificate_file` | string (**required**) | **URL/path tệp chứng chỉ** đã upload (KHÔNG binary — upload path chuẩn RỒI truyền file-url). @180 |
| 3 | `certificate_number` | string (**required**) | số chứng chỉ lab cấp. @181 |
| 4 | `certificate_date` | string (**required**) | ngày cấp chứng chỉ. @181 (BE optional `format:date` nếu generator đòi) |
| 5 | `traceability_reference` | string, nullable | tham chiếu truy-xuất-nguồn-gốc; absent ⇒ KHÔNG patch @1329-1330. `=None` @182 optional |
| 6 | `reference_standard_serial` | string, nullable | serial chuẩn tham chiếu; absent ⇒ KHÔNG patch @1331-1332. `=None` @183 optional |

**`ReceiveCertificateResponse`** (data) — CLOSED `required[name,status,certificate_number]` EXACT **3 prop** (GROUNDED `return {name,status,certificate_number}` @1339-1340):

| # | Field | Type | Ground |
|---|---|---|---|
| 1 | `name` | string (**required**) | echo name phiếu @1339 |
| 2 | `status` | **string** (KHÔNG enum) (**required**) | `patch["status"]` @1339 = `CalibrationResult.IN_PROGRESS` @1327 (`constants.py:124`). **Giá-trị trả LUÔN `"In Progress"`** (state đơn-trị — plain string cố-ý theo acceptance, KHÁC `sendToLab` enum-8-canonical) |
| 3 | `certificate_number` | string (**required**) | echo `certificate_number` request @1340. **ANTI-DRIFT: KHÔNG `sent_date` (đó là SendToLabResponse) / KHÔNG `certificate_file` (chỉ request) / KHÔNG `certificate_date`** |

**200 = oneOf [`ReceiveCertificateResponseEnvelope`, `Error`]** (Decision-B route-by-VALUE `body.success`, 0 discriminator). Nhánh `Error` gom **4 nhánh service** ARRIVE HTTP-200 `Error.http_status` ⊇ **{404,409,422}**: NOT_FOUND 404 (doc∄ @1315) → CONFLICT 409 (docstatus==1 đã-chốt @1317) → CONFLICT 409 (sai-state ≠`Sent to Lab` @1319) → VALIDATION 422 (thiếu 1/3 cert-field @1321) — grounded `messages.py` (404@904/409@939/409@967/422@974). **KHÁC `sendToLab` KHÔNG có `NOT_EXTERNAL` 422** (state `Sent to Lab` chỉ đạt qua `sendToLab` đã guard type==External).

#### ADR-IMM11-RECEIVECERT — `receiveCertificate` write-ACTION json+form + `ReceiveCertificateResponse` RIÊNG 3-prop `{name,status,certificate_number}` + status plain-string + 403 SINGLE qua `rbac.require` same-shape
- **Status**: Accepted · **Date**: 2026-07-11
- **Context**: Nhánh External-calibration đã mở (`sendToLab` §0.1.6) nhưng cụt sau khi gửi lab. `receive_certificate` LIVE @source (handler+service+cap-gate+return-shape sẵn). Cần contract để codegen sinh method nhận-cert (mắt-xích GIỮA).
- **Decision**: Curate 1 path POST, requestBody 2 media-type (json+form §9, KHÔNG multipart — `certificate_file` là string URL, action state-machine), **3 schema RIÊNG** (`ReceiveCertificateRequest` req-4/6-prop · `ReceiveCertificateResponse` 3-prop · Envelope), 200 = oneOf [Env, Error], **403 SINGLE-SHAPE `Forbidden`**. `status` = **plain string KHÔNG enum** (đơn-trị `In Progress`). Tag `calibration`. Path 63→64.
- **Alternatives (loại)**: multipart body (sai transport — `certificate_file` string URL KHÔNG binary, đọc `form_dict`) · reuse `SendToLabResponse` (cùng 3-key nhưng key#3 `sent_date`≠`certificate_number` → `additionalProperties:false` FAIL) · reuse `Submit`4-prop/`Create`2-prop · dual-403 (cap-403 CÙNG shape dispatcher) · SINGLE-200 (giấu 4 nhánh Error) · `status` enum-8-canonical (acceptance chọn plain string đơn-trị — Alt-E ADR-032; enum cũng hợp-lệ nhưng honor acceptance) · `required[name]` only (4 cert-param positional KHÔNG default — bắt buộc).
- **Consequences**: +1 path +3 schema RIÊNG (PURE-YAML). **0 đụng** `api/imm11.py`+`services/imm11.py` (handler+service+cap-gate+return-shape đã sẵn @source) ⇒ KHÔNG reload/migrate/commit. C3-split family (module 4 response-shape khác: create-2/send-lab-3{sent_date}/receive-cert-3{certificate_number}/submit-4). Test `TestMobileReceiveCertificateContract` guard response field-set ≠ SendToLab/Submit/Create + status-plain-string-no-enum.
- **⚠️ Self-Correction đánh-số ADR (numbering drift đa-phiên)**: đề mục Bước-2 ghi "ADR balance +1 → ADR-MOBILE-031". SAI @disk: **031 = `sendToLab`** (R10 Accepted trên đĩa). ADR mới = **MOBILE-032** (off-by-one do vòng sendToLab song song chiếm 031); narrative §8.38, binding §0.1.7. BE dùng ĐÚNG 032/§8.38/§0.1.7 + README-row cho 032.

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) YAML `63 → 64` path / `64` operationId (`receiveCertificate` mới, unique camelCase, tag `calibration`, 0 dangling `$ref`, `safe_load` OK); requestBody `required:true` content 2 media-type json+form cùng `$ref ReceiveCertificateRequest`; 200 oneOf [`ReceiveCertificateResponseEnvelope`, Error]; slot `{200,401,403}` (`401 Unauthorized401` + **`403 Forbidden` SINGLE-SHAPE** — KHÔNG dual). (2) +3 schema closed (`ReceiveCertificateRequest` `req[name,certificate_file,certificate_number,certificate_date]` 6-prop 4-required 2-nullable — `certificate_file` string KHÔNG binary · `ReceiveCertificateResponse` `req[name,status,certificate_number]` 3-prop `status` **plain string KHÔNG enum** · `ReceiveCertificateResponseEnvelope`) tái-dùng `Unauthorized401`/`Forbidden`/`Error`; naming-guard `ReceiveCertificate*` ∩ (`SendToLab*`∪`SubmitCalibration*`∪`CreateCalibration*`∪`AddMeasurement*`) == ∅. (3) Guard XANH @source (`bench --site miyano run-tests --app assetcore --module assetcore.tests.test_mobile_oas`): `_EXPECTED_TEST_COUNT` **581→591** (+10 TC `TestMobileReceiveCertificateContract a..j`, gồm TC-d req-4-required + certificate_file-string-NOT-binary, TC-g response-3-prop-status-plain-string-NO-enum anti-drift vs SendToLab-3-key-{sent_date}, TC-i live-signature parity `inspect.signature(imm11.receive_certificate)=={name,certificate_file,certificate_number,certificate_date,traceability_reference,reference_standard_serial}`, TC-j git-diff-0-hunk pure-yaml) + c5 **52→53** + membership `_MVP_ACTION_ENVELOPE`+`_REQBODY_PATHS`; `test_mobile_docset` **Ran 9 OK** (reconcile `_GUARD_SUITE_SUM` **724→734** + `_MOBILE_OAS_TOTAL` **750→760**); `test_mobile_security_gate` GREEN; `test_oas_d12/d15/d17` **UNCHANGED** (pure mobile-yaml — KHÔNG đụng `generate_spec`). ⚠️ Baseline 581/63/52/724/750 grounded sau ADR-031 — **BE grep-verify @source TRƯỚC bump** (đa-phiên race). (4) **CONTRACT-ONLY**: `git diff` `api/imm11.py`+`services/imm11.py` vùng `receive_certificate` = 0 hunk MỚI (registry-resolvability KHÔNG HEAD-diff). RED-before/GREEN-after cho MỌI TC mới. KHÔNG reload/migrate/commit (HARD-STOP USER — working-tree để USER review).

---

### 0.1.8. Write-action binding — `cancelCalibration` (ABORT/escape-hatch phiếu DRAFT, HOÀN TẤT bộ-ba action External-calibration · CR-CAL-EXT-03)

> **Bối cảnh (HOÀN TẤT bộ-ba External)**: Nhánh **External/NGOẠI KIỂM** = `createCalibration(External)`→**`sendToLab`** (§0.1.6, mở)→**`receiveCertificate`** (§0.1.7, giữa)→`submitCalibration` (chốt). `cancelCalibration` là **escape-hatch/abort** cho MỌI phiếu hiệu chuẩn còn **DRAFT** (In-House lẫn External) — false-alarm / thiết bị decommissioned / lập nhầm (BR-11-08): `status`→**`Cancelled`** (`amendment_reason="[Cancelled] {reason}"`) + nếu asset đang `CALIBRATING` trả về `ACTIVE` + audit `Calibration`. Cross-link SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3.0.3, hiện **64 path → +1 = 65** sau round này — số grounded @source 2026-07-12 sau ADR-032/receiveCertificate, **BE grep-verify TRƯỚC bump**) + [`docs/mobile/ADR-MOBILE-033.md`](../mobile/ADR-MOBILE-033.md) + [`04-api-contract.md §8.39`](../mobile/04-api-contract.md) — **KHÔNG nhân đôi schema**; mọi sửa field đồng bộ 2 nơi. **BỘ-BA ACTION EXTERNAL-CALIBRATION HOÀN TẤT** (sendToLab → receiveCertificate → cancelCalibration).

> **⚠️ ĐIỂM KHÁC CỐT-LÕI (403 cap-branch REACHABLE — shape KHÔNG đổi):** `sendToLab`/`receiveCertificate` gate cap permtype **`write`** mà `Calibration User` **CÓ** (`write=1`) → cap-403 gần-như-không-trip cho KTV thường. `cancelCalibration` gate cap `calibration.cancel` → permtype **`cancel`** mà `Calibration User` **cancel=0** (DocPerm `imm_asset_calibration.json`: `cancel=1` chỉ `AssetCore Super Admin`+`Calibration Manager`) ⇒ cap-403 (`rbac.require("calibration.cancel")` @197 chạy **TRƯỚC** `handle()`) là **HTTP-403 status-line THẬT** và **REACHABLE** cho một KTV cố hủy phiếu — action IMM-11 ĐẦU TIÊN mà cap-403 trip trong luồng vận-hành bình-thường. SHAPE **VẪN SINGLE `Forbidden`** (cap-403 CÙNG raw-403 status-line dispatcher-403 → collapse 1 component). KHÁC-BIỆT ở **reachability/UX** (app gate nút "Hủy phiếu" theo `calibration.cancel` — chống nút-chết), KHÔNG ở schema. **403 KHÔNG đi qua 200-oneOf Error branch.**

| Mục | Giá trị |
|---|---|
| Mobile operationId | `cancelCalibration` (POST, path 65/65 mới), tag `calibration` |
| Handler LIVE | `assetcore.api.imm11.cancel_calibration` def@`api/imm11.py:195-198` (`@whitelist(methods=["POST"])`@195, `rbac.require("calibration.cancel")`@197 → `("IMM Asset Calibration","cancel")` **auto-gen** `rbac.py:100-103`, `handle(svc.cancel_calibration, name, reason)`@198) |
| Service LIVE | `services/imm11.py:1343` — 4-nhánh ladder + patch status=`Cancelled` + `amendment_reason` @1355-1358 + asset `CALIBRATING`→`ACTIVE` NẾU applicable @1359-1362 + audit `Calibration` @1363-1367; `return {name,status}`@1368 EXACT 2-key |
| requestBody | 2 media-type `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict` §9) cùng `$ref CancelCalibrationRequest` — **∈ `_REQBODY_PATHS`**, subject sweep `_RPC_FORM_JSON_MEDIA` (mirror `sendToLab`/`receiveCertificate`, **KHÁC 3 path multipart** ∉ `_REQBODY_PATHS`) |

**`CancelCalibrationRequest`** — CLOSED (`additionalProperties:false`) `required[name, reason]` EXACT **2 prop** khớp HỆT signature @196 (**2 bắt buộc** — `reason` KHÁC `sendToLab` chỉ `name`):

| # | Field | Type | Ground |
|---|---|---|---|
| 1 | `name` | string (**required**) | name IMM Asset Calibration (phiếu DRAFT cần hủy). @196 `form_dict` |
| 2 | `reason` | string (**required**) | lý do hủy — bắt buộc (BR-11-08); service `nthrow IMM11_CANCEL_REASON_REQUIRED` @1353 nếu rỗng/whitespace; lưu `amendment_reason="[Cancelled] {reason}"` @1357. @196 |

**`CancelCalibrationResponse`** (data) — CLOSED `required[name, status]` EXACT **2 prop** (GROUNDED `return {name,status}` @1368):

| # | Field | Type | Ground |
|---|---|---|---|
| 1 | `name` | string (**required**) | echo name phiếu @1368 |
| 2 | `status` | **string** (KHÔNG enum) (**required**) | `CalibrationResult.CANCELLED` @1368 (`constants.py:119`). **Giá-trị trả LUÔN `"Cancelled"`** (state đơn-trị — plain string mirror `receiveCertificate`, KHÁC `sendToLab` enum-8-canonical). **ANTI-DRIFT: KHÔNG `sent_date` (SendToLab) / `certificate_number` (ReceiveCertificate) / `amendment_reason` (chỉ lưu server)** |

**200 = oneOf [`CancelCalibrationResponseEnvelope`, `Error`]** (Decision-B route-by-VALUE `body.success`, 0 discriminator). Nhánh `Error` gom **4 nhánh service** ARRIVE HTTP-200 `Error.http_status` ⊇ **{404,409,422}**: NOT_FOUND 404 (doc∄ @1347) → CONFLICT 409 (docstatus==1 đã-chốt @1349) → CONFLICT 409 (đã-hủy @1351) → VALIDATION 422 (thiếu lý do @1353) — grounded `messages.py` (404@917/409@1001/409@1008/422@994). **KHÁC `sendToLab`/`receiveCertificate` KHÔNG có `NOT_EXTERNAL`/state-guard** — cancel áp MỌI DRAFT (guard #2 chặn docstatus==1, #3 chặn đã-hủy). **KHÔNG có 403** trong 200-Error (cap-403 đi raw status-line — xem Slot).

#### ADR-IMM11-CANCELCAL — `cancelCalibration` write-ACTION json+form + `CancelCalibrationResponse` RIÊNG 2-prop `{name,status}` + status plain-string + 403 SINGLE `Forbidden` REACHABLE (cap `cancel`, Calibration User cancel=0)
- **Status**: Accepted · **Date**: 2026-07-12
- **Context**: Nhánh External-calibration đã đủ dispatch+receive (`sendToLab` §0.1.6 / `receiveCertificate` §0.1.7) nhưng thiếu escape-hatch hủy phiếu DRAFT. `cancel_calibration` LIVE @source (handler+service+cap-gate+return-shape sẵn). Cần contract để codegen sinh method "Hủy phiếu" (abort — HOÀN TẤT bộ-ba).
- **Decision**: Curate 1 path POST, requestBody 2 media-type (json+form §9, KHÔNG multipart — action state-machine), **3 schema RIÊNG** (`CancelCalibrationRequest` req-2/2-prop · `CancelCalibrationResponse` 2-prop `{name,status}` · Envelope), 200 = oneOf [Env, Error], **403 SINGLE-SHAPE `Forbidden` — description GHI RÕ REACHABLE** cho Calibration User (cap `calibration.cancel`, DocPerm cancel=0). `status` = **plain string KHÔNG enum** (đơn-trị `Cancelled`, mirror `receiveCertificate`). `reason` bắt buộc (BR-11-08). Tag `calibration`. Path 64→65.
- **Alternatives (loại)**: multipart body (action KHÔNG upload, đọc `form_dict`) · dual-403 (cap-403 REACHABLE NHƯNG CÙNG shape dispatcher — reachability ≠ shape, ghi ở description KHÔNG đổi schema) · SINGLE-200 (giấu 4 nhánh Error) · reuse `CreateCalibrationResponse` 2-prop (field-set khác → `additionalProperties:false` FAIL) · `status` enum-8-canonical (acceptance chọn plain string đơn-trị, mirror receiveCertificate) · `required[name]` only (`reason` positional KHÔNG default — bắt buộc) · KHÔNG ghi reachability 403 (app render nút-chết cho KTV cancel=0).
- **Consequences**: +1 path +3 schema RIÊNG (PURE-YAML). **0 đụng** `api/imm11.py`+`services/imm11.py` (handler+service+cap-gate+return-shape đã sẵn @source) ⇒ KHÔNG reload/migrate/commit. C3-split family (module 5 response-shape: create-2/send-lab-3{sent_date}/receive-cert-3{certificate_number}/**cancel-2{name,status}**/submit-4). **403 REACHABLE documented** (cap `cancel` Calibration User cancel=0 — action ĐẦU TIÊN cap-403 trip vận-hành thường; shape VẪN SINGLE `Forbidden` same-shape collapse). Test `TestMobileCancelCalibrationContract` guard response field-set 2-prop ≠ SendToLab/ReceiveCert/Submit/Create + status-plain-string-no-enum + naming-guard + cap-map-grounded.
- **Self-Correction from-state**: acceptance ghi "Scheduled/In Progress → Cancelled" NHƯNG guard THẬT service @1346-1353 = `docstatus!=1` (DRAFT) AND `status!=Cancelled` — KHÔNG whitelist `{Scheduled, In Progress}`; MỌI phiếu DRAFT (Scheduled/Sent to Lab/In Progress/Certificate Received) hủy được. "Scheduled/In Progress" là case điển-hình. Contract KHÔNG khai from-state (request `{name, reason}`) — nhưng ghi để BE/FE KHÔNG thêm client-guard hẹp hơn server (chặn nhầm phiếu External `Sent to Lab` đáng-hủy).

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) YAML `64 → 65` path / `65` operationId (`cancelCalibration` mới, unique camelCase, tag `calibration`, 0 dangling `$ref`, `safe_load` OK); requestBody `required:true` content 2 media-type json+form cùng `$ref CancelCalibrationRequest`; 200 oneOf [`CancelCalibrationResponseEnvelope`, Error]; slot `{200,401,403}` (`401 Unauthorized401` + **`403 Forbidden` SINGLE-SHAPE** — KHÔNG dual; **description path GHI RÕ 403 REACHABLE** cho Calibration User cap `calibration.cancel`). (2) +3 schema closed (`CancelCalibrationRequest` `req[name, reason]` 2-prop cả-2-required — KHÁC `sendToLab` 1 · `CancelCalibrationResponse` `req[name, status]` 2-prop `status` **plain string KHÔNG enum** · `CancelCalibrationResponseEnvelope`) tái-dùng `Unauthorized401`/`Forbidden`/`Error`; naming-guard `CancelCalibration*` ∩ (`SendToLab*`∪`ReceiveCertificate*`∪`SubmitCalibration*`∪`CreateCalibration*`∪`AddMeasurement*`) == ∅. (3) Guard XANH @source (`bench --site miyano run-tests --app assetcore --module assetcore.tests.test_mobile_oas`): `_EXPECTED_TEST_COUNT` **591→601** (+10 TC `TestMobileCancelCalibrationContract a..j`, gồm TC-d req-2-required[name,reason], TC-g response-2-prop-status-plain-string-NO-enum anti-drift vs SendToLab enum/sent_date + ReceiveCert certificate_number, TC-h 403-SINGLE + reachability, TC-i naming-guard + cap-map `calibration.cancel→(IMM Asset Calibration,cancel)`, TC-j live-signature parity `inspect.signature(imm11.cancel_calibration)=={name, reason}` + git-diff-0-hunk pure-yaml) + c5 **53→54** + membership `_MVP_ACTION_ENVELOPE`+`_REQBODY_PATHS`; `test_mobile_docset` **Ran 9 OK** (reconcile `_GUARD_SUITE_SUM` **734→744** + `_MOBILE_OAS_TOTAL` **760→770**); `test_mobile_security_gate` GREEN; `test_oas_d12/d15/d17` **UNCHANGED** (pure mobile-yaml — KHÔNG đụng `generate_spec`). ⚠️ Baseline 591/64/53/734/760 grounded @source 2026-07-12 sau ADR-032 — **BE grep-verify @source TRƯỚC bump** (đa-phiên race). (4) **CONTRACT-ONLY**: `git diff` `api/imm11.py`+`services/imm11.py` vùng `cancel_calibration` = 0 hunk MỚI (registry-resolvability KHÔNG HEAD-diff). RED-before/GREEN-after cho MỌI TC mới. KHÔNG reload/migrate/commit (HARD-STOP USER — working-tree để USER review).

### 0.1.9. Read-list binding — `getDueCalibrations` (DUE/OVERDUE LIST, màn "Nhắc việc" · MỞ NHÁNH F8 · CR-28a)

> **Bối cảnh (MỞ NHÁNH F8-Nhắc-việc)**: Màn **"Nhắc việc"** trên mobile cần 1 danh sách thiết bị **sắp/quá hạn hiệu chuẩn** để KTV ưu tiên đi làm — KHÁC `listCalibrations` (§0.1.1, liệt-kê PHIẾU hiệu chuẩn) vì đây là danh sách **THIẾT BỊ due** (nguồn `AC Asset.next_calibration_date`, BR-11-13 = MIN-lịch multi-schedule). `getDueCalibrations` là **read-list binding ĐẦU TIÊN của nhánh F8** (song song nhánh External-calibration §0.1.6–0.1.8 đã HOÀN TẤT). Cross-link SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3.0.3) — **KHÔNG nhân đôi schema**; mọi sửa field đồng bộ 2 nơi. Endpoint đã LIVE (API catalog #18) → binding này CHỈ curate mirror OAS (CONTRACT-ONLY).

> **⚠️ ĐIỂM KHÁC CỐT-LÕI vs `listCommissioning`/mọi list khác — KHÔNG PAGINATION.** `data` = **`{items[], threshold_days}` CHÍNH XÁC 2 key** (GROUNDED `return {"items": rows, "threshold_days": int(days)}` @`services/imm11.py:1421`). `get_due_calibrations` KHÔNG gọi `paginate()`, KHÔNG trả `pagination` — chỉ cắt `page_size=int(limit)` (limit-cap, mirror `getAssetTimeline` limit-cap). ⇒ `DueCalibrationListPage` **KHÔNG có `pagination` `$ref`** — đây là điểm PHÂN BIỆT vs `CommissioningListPage`/`CalibrationListPage` (đều `{items, pagination}`). Vẫn vào `_MVP_LIST_ENVELOPE` vì 200 = **oneOf [Env, Error]** (`handle()`-contract), KHÔNG vào `_MVP_SINGLE_LIST_ENVELOPE` (đó là single-$ref, handler 0 `_err`).

| Mục | Giá trị |
|---|---|
| Mobile operationId | `getDueCalibrations` (GET, path 77/77 mới), tag `calibration` |
| Handler LIVE | `assetcore.api.imm11.get_due_calibrations` def@`api/imm11.py:202-203` — **`@frappe.whitelist()` BARE @201** (nhận GET; **KHÔNG `methods=["POST"]`**, **KHÔNG `rbac.require`** → 0 cap-gate) → `handle(svc.get_due_calibrations, int(days), int(limit))`@203 |
| Service LIVE | `services/imm11.py:1393` `get_due_calibrations(days=30, limit=50)` — `AssetRepo.list` filter 3-clause (`lifecycle_status not in [DECOMMISSIONED]` + **`next_calibration_date is set`@1409** + `next_calibration_date <= threshold`) `fields=[name,asset_name,device_model,location,next_calibration_date,calibration_status]`@1412-1413 `page_size=int(limit)`; loop bồi `days_left = date_diff(nd, today_d) if nd else None`@1420; `return {items, threshold_days}`@1421 EXACT 2-key |
| Params | **2 typed query-param INLINE** (mirror `year` CR-05/CR-11b, KHÔNG `$ref`): `days` (`integer`, **default 30**, `in:query` `required:false`) — cửa-sổ ngày tính "due" (`threshold = add_days(today, days)`@1408) · `limit` (`integer`, **default 50**, `in:query` `required:false`) — cap số dòng (`page_size`). Signature `get_due_calibrations(days=30, limit=50)` — 2 param CÓ default ⇒ CẢ 2 `required:false`. **0 param JSON-filters, 0 param `mine`, 0 param `page`.** |
| Response 200 | `oneOf [DueCalibrationListEnvelope, Error]` Ở TẦNG response-content-schema của response-component (Decision-B route-by-VALUE `body.success`, **0 discriminator**, đối xứng `listCommissioning`). ∈ `_MVP_LIST_ENVELOPE` (map `→ #/components/schemas/DueCalibrationListEnvelope`) |
| Status codes | 200 / 401 (`Unauthorized401` — bearer hết-hạn = dispatcher) / **403 SINGLE-SHAPE `Forbidden`** — **dispatcher-ONLY** (guest/no-token, `@whitelist` no `allow_guest`). **KHÔNG có 403-cap-branch REACHABLE** (bare `@whitelist`, 0 `rbac.require` — KHÁC `sendToLab`/`cancelCalibration`). Mirror `listTransfers`/`listDepartments`/`listLocations` (bare-@whitelist read, 403 dispatcher-only). Path ∈ `_MVP_BUSINESS_PATHS` ⇒ 401/403 symmetry set tự +1 (test so SET). |

**`DueCalibrationListItem`** — CLOSED (`additionalProperties:false`) **EXACT 7 prop** = 6 field `AssetRepo.list` @`services/imm11.py:1412-1413` ∪ `days_left` bồi @`:1420`. **0 field thừa/thiếu** (VERBATIM service; SSoT DocType = `ac_asset.json`):

| # | Field | Type | Ground (SSoT `ac_asset.json` field) |
|---|---|---|---|
| 1 | `name` | string (**required**) | PK `AC Asset.name` (AC-ASSET-xxxx) |
| 2 | `asset_name` | string | `AC Asset.asset_name` (Data, `reqd=1` @DocType ⇒ luôn có) |
| 3 | `device_model` | string | `AC Asset.device_model` (Link `IMM Device Model`) |
| 4 | `location` | string | `AC Asset.location` (Link `AC Location`) |
| 5 | `next_calibration_date` | string `format:date` (**KHÔNG `nullable`**) | `AC Asset.next_calibration_date` (Date). **Non-nullable Ở ĐÂY** vì filter `["next_calibration_date","is","set"]`@1409 loại NULL ⇒ MỌI dòng trả về đều có date thật (KHÁC §0.1.5 `listCalibrations` nơi field này `nullable:true`) |
| 6 | `calibration_status` | string enum `['', Not Required, On Schedule, Due Soon, Overdue, Calibration Failed]` | `AC Asset.calibration_status` (Select 6-value, leading-blank). Cache rollup worst-of (`check_calibration_expiry`, §0.1.5/§6.1). **String Select — KHÔNG Check ⇒ KHÔNG integer-enum** |
| 7 | `days_left` | **`integer`** signed (**KHÔNG `nullable`**, KHÔNG enum) | Bồi @`:1420` `date_diff(next_calibration_date, today)`. **Âm = quá hạn** (vd `-3` = quá hạn 3 ngày), `0` = đến hạn hôm nay, dương = còn N ngày. Client DÙNG TRỰC TIẾP để sort/ưu-tiên — **KHÔNG re-derive** vs client-clock (server-flag SSoT, `memory/overdue_server_flag_ssot.md`) |

- **Always**: `additionalProperties:false` (closed) ở CẢ `DueCalibrationListEnvelope` (`required[success,data]`, `success.enum[true]`, `data = $ref DueCalibrationListPage`), `DueCalibrationListPage` (`required[items,threshold_days]`) LẪN `DueCalibrationListItem` (`required[name]`, 6 field khác optional). `days_left` = `type:integer` NON-nullable (dead-branch — xem ADR).
- **Always**: path vào `_MVP_BUSINESS_PATHS` (401/403 symmetry) **VÀ** `_MVP_LIST_ENVELOPE` (`→ DueCalibrationListEnvelope`, oneOf-bucket) ⇒ 2 set tự +1 (test so SET, KHÔNG literal).
- **Never**: KHÔNG thêm `pagination` vào `DueCalibrationListPage` (service KHÔNG `paginate()` — chỉ limit-cap; thêm = payload BE KHÔNG khớp closed-schema). KHÔNG khai `days_left` `nullable:true` (dead-branch `else None` không đạt-tới). KHÔNG khai `calibration_status`/bất kỳ field nào là `integer enum[0,1]` — 0 Check field ở list-item này (KHÁC `listCalibrations` `is_recalibration`/`is_overdue`/`is_due_soon`). KHÔNG nhồi field financial. KHÔNG thêm `mine`/`page`/JSON-`filters` param (signature chỉ `days,limit`). KHÔNG thêm slot 403 dual-shape (cap-403 KHÔNG reachable — bare `@whitelist`).

**403 = SINGLE-SHAPE `Forbidden` DISPATCHER-ONLY (KHÔNG cap-403 — KHÁC `sendToLab`/`cancelCalibration`):**
- *dispatcher-403* (guest/no-token) trip TRƯỚC `handle()` (bare `@whitelist` no `allow_guest`) → HTTP-403 THẬT (`FrappeRawError`) ⇒ slot `403` = `$ref #/components/responses/Forbidden`.
- **KHÔNG có in-handler cap-403**: handler `get_due_calibrations` **KHÔNG gọi `rbac.require`** (0 dòng cap-gate @`api/imm11.py:202-203`) ⇒ KHÔNG có nhánh `Error.http_status==403` in-handler. Mirror `listTransfers`/`listDepartments`/`listLocations` (bare-@whitelist read dispatcher-only 403 — ADR-043 family), KHÁC `cancelCalibration` (cap `calibration.cancel` REACHABLE) / `submitCalibration` (cap `calibration.submit`).
- **200-oneOf `Error` branch = handle()-wrapper DEFENSIVE** (catch-all exception): service `get_due_calibrations` **KHÔNG** `frappe.throw`/`nthrow`/`ServiceError` (khác `list_commissioning` raise FORBIDDEN) ⇒ KHÔNG có domain `Error.http_status` code enumerated reachable; nhánh `Error` khai để đối-xứng `handle()`-contract + thỏa `_MVP_LIST_ENVELOPE` sweep (200 comp.schema = oneOf [Env, Error]). Mọi lỗi bất-thường vẫn ARRIVE **HTTP-200 + Error body** (Decision-B, KHÔNG status-line, KHÔNG raise→4xx).

#### ADR-IMM11-DUECAL — `getDueCalibrations` read-list KHÔNG-pagination `{items, threshold_days}` + `DueCalibrationListItem` 7-prop VERBATIM + `days_left` signed-integer non-nullable + 403 dispatcher-only

- **Status**: Accepted · **Date**: 2026-07-14
- **Context**: Màn "Nhắc việc" (F8) cần list thiết bị due/overdue hiệu chuẩn. `get_due_calibrations` LIVE @source (bare `@whitelist`, service trả `{items, threshold_days}` với item 7-field + `days_left` signed). Cần contract mirror OAS để codegen sinh method — NHƯNG shape KHÁC mọi list đã curate ở **3 điểm**: (1) KHÔNG pagination; (2) `days_left` = quantity signed-int (KHÔNG flag `enum[0,1]`); (3) bare `@whitelist` 0 cap-gate.
- **Decision**: Curate 1 path GET, **2 typed query-param INLINE** `days`/`limit` (integer, default 30/50, `required:false` — mirror `year` CR-05/CR-11b), **3 schema RIÊNG CLOSED**: (a) `DueCalibrationListItem` `req[name]` EXACT 7-prop VERBATIM service (6 `AssetRepo.list` field ∪ `days_left`); (b) `DueCalibrationListPage` `req[items,threshold_days]` **CHÍNH XÁC 2 key KHÔNG pagination**; (c) `DueCalibrationListEnvelope` `{success:[true], data:$ref DueCalibrationListPage}`. 200 = oneOf [Env, Error] (Decision-B). `days_left` = `type:integer` **non-nullable** (âm=overdue, dùng trực tiếp). `next_calibration_date` **non-nullable** (filter "is set" đảm bảo). 403 SINGLE-SHAPE `Forbidden` **dispatcher-ONLY** (bare `@whitelist`, 0 cap-403). Path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_LIST_ENVELOPE`. Tag `calibration`. Path 76→77.
- **Alternatives (loại)**: (a) thêm `pagination` cho parity `CommissioningListPage` → payload BE `{items, threshold_days}` KHÔNG khớp closed-schema (bịa field service KHÔNG trả); (b) `days_left` `type:integer nullable:true` → codegen `int?` cho branch `else None` **DEAD** (filter "is set" @1409 loại NULL ⇒ `nd` LUÔN truthy ⇒ `date_diff` LUÔN trả int) — non-nullable phản-ánh sự-thật runtime; (c) `days_left` `integer enum[0,1]`/`boolean` → SAI kiểu (quantity ≠ flag; mất dấu/độ-lớn "quá hạn bao nhiêu ngày"); (d) vào `_MVP_SINGLE_LIST_ENVELOPE` (single-$ref như `listTransfers`) → SAI vì handler DÙNG `handle()` ⇒ 200 = oneOf [Env, Error] (KHÔNG single-$ref); (e) dual-403 (như `reportIncident`) → cap-403 KHÔNG reachable (bare `@whitelist`); (f) `$ref Page/PageSize` cho `days`/`limit` → sai semantics (`days` = cửa-sổ-ngày KHÔNG số-trang; `limit` = row-cap KHÔNG `page_size` phân-trang có `offset`).
- **Consequences**: +1 path +3 schema RIÊNG (PURE-YAML). **0 đụng** `api/imm11.py`+`services/imm11.py` (handler+service+return-shape đã sẵn @source) ⇒ KHÔNG reload/migrate/commit. Bộ list-read Calibration nay 3 shape: `listCalibrations` (paginated `data.data[]`, 17-field 3-Check) / **`getDueCalibrations` (KHÔNG pagination `{items,threshold_days}`, 7-field 0-Check, `days_left` signed)** — cross-ref §0.1.5: `listCalibrations` dùng `is_overdue`/`is_due_soon` (flag `enum[0,1]`), `getDueCalibrations` dùng `days_left` (quantity signed) — 2 cách render server-flag KHÁC nhau, CÙNG SSoT server-derive KHÔNG client-clock. Test `TestMobileDueCalibrationsContract a..g` guard 7-field VERBATIM + no-pagination + `days_left` integer-non-nullable + 2 typed-param + oneOf + naming-guard + live-signature parity.
- **Self-Correction (line-ref)**: task ghi field @`imm11.py:1413-1414` / `days_left else-None @1421` / `return @1420` — grounding THẬT `services/imm11.py`: `fields=[...]` @**1412-1413**, `days_left ... else None` @**1420**, `return {items, threshold_days}` @**1421**, filter "is set" @**1409**. Dùng số grounded @source (không lệch nghĩa — chỉ chỉnh line-ref).

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) YAML `76 → 77` path / `77` operationId (`getDueCalibrations` mới, unique camelCase `^[a-z][a-zA-Z0-9]*$`, tag `calibration`, method GET, 0 dangling `$ref`, `safe_load`/parse OK); 2 typed query-param INLINE `days`+`limit` (`integer`, default `30`/`50`, `in:query`, `required:false`); 200 = response oneOf [`DueCalibrationListEnvelope`, `Error`]; slot `{200,401,403}` (`401 Unauthorized401` + **`403 Forbidden` SINGLE-SHAPE dispatcher-only** — description GHI RÕ bare-@whitelist 0 cap-403). (2) +3 schema CLOSED (`additionalProperties:false`): `DueCalibrationListItem` `req[name]` EXACT 7-prop {name,asset_name,device_model,location,next_calibration_date,calibration_status,days_left} — 0 field thừa/thiếu, `days_left` `type:integer` NON-nullable, `next_calibration_date` `format:date` NON-nullable, `calibration_status` string-enum-6 (leading-blank), 0 Check integer-enum · `DueCalibrationListPage` `req[items,threshold_days]` **CHÍNH XÁC 2-key KHÔNG `pagination`** (`items:array<$ref DueCalibrationListItem>` + `threshold_days:integer`) · `DueCalibrationListEnvelope` `{success:enum[true], data:$ref DueCalibrationListPage}`; tái-dùng `Unauthorized401`/`Forbidden`/`Error`; naming-guard `DueCalibration*` ∩ (`Calibration*`∪`SendToLab*`∪`ReceiveCertificate*`∪`SubmitCalibration*`∪`CancelCalibration*`∪`AddMeasurement*`) == ∅. (3) Guard XANH @source (`bench --site miyano run-tests --app assetcore --module assetcore.tests.test_mobile_oas`): `_EXPECTED_TEST_COUNT` **714→721** (+7 TC `TestMobileDueCalibrationsContract a..g`: a=path+opId+GET+tag, b=2-typed-param days/limit integer-default-required:false, c=Item-7-field-VERBATIM-closed-0-extra, d=`days_left` integer-NON-nullable + `next_calibration_date` NON-nullable (anti dead-branch), e=`DueCalibrationListPage`-EXACT-2-key-NO-pagination (điểm KHÁC listCommissioning), f=200-oneOf[Env,Error] + Envelope-closed{success:[true],data}, g=naming-guard + live-signature parity `inspect.signature(imm11.get_due_calibrations)=={days,limit}` + git-diff-0-hunk pure-yaml) + `_MVP_LIST_ENVELOPE` **9→10** + c5 **65→66** + membership `_MVP_BUSINESS_PATHS` (401/403 symmetry tự +1); `test_mobile_docset` **Ran N OK** THẬT (reconcile `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` **714→721** + `_GUARD_SUITE_SUM` **857→864** + `_MOBILE_OAS_TOTAL` **883→890**) — KHÔNG skip/xfail. `test_mobile_security_gate`/`test_oas_*` UNCHANGED (pure mobile-yaml). ⚠️ Baseline 76/714/9/65/857/883 grounded @source 2026-07-14 sau CR-25a (`listCommissioning`) — **BE grep-verify @source TRƯỚC bump** (đa-phiên race). (4) **CONTRACT-ONLY**: `git diff` CHỈ 3 file (`docs/mobile/openapi/assetcore-mobile.openapi.yaml` + `assetcore/tests/test_mobile_oas.py` + `assetcore/tests/test_mobile_docset.py`); `api/imm11.py`+`services/imm11.py` = **0 hunk** (0 worker-reload, 0 bench migrate). RED-before/GREEN-after cho MỌI TC mới. KHÔNG reload/migrate/commit (HARD-STOP USER — working-tree để USER review).

### 0.1.10. Read-dashboard binding — `getCalibrationKpis` (BỘ CHỈ SỐ hiệu chuẩn theo THÁNG, màn "Bảng chỉ số hiệu chuẩn" · Dashboard-KPI Trục B · CR-31b)

> **Bối cảnh (Dashboard-KPI R1b)**: Màn **"Bảng chỉ số hiệu chuẩn"** trên mobile hiển thị **1 khối 6 chỉ số** hiệu chuẩn phạm-vi THÁNG (tổng phiếu, đạt, không-đạt, tỉ-lệ-đạt, số THIẾT BỊ quá-hạn, số THIẾT BỊ sắp-đến-hạn) cho quản-lý xưởng / PTP Khối 2 / CMMS Admin. `getCalibrationKpis` là endpoint Dashboard-KPI **THỨ HAI** — **SIBLING của `getPmDashboardStats`** (IMM-08, ADR-MOBILE-056, endpoint ĐẦU surface); `getRepairKpis` (IMM-09) = forward-reserve. Mỗi KPI-endpoint đơn-module theo module-tag riêng — "màn Bảng chỉ số" là **FE-composition**, KHÔNG API-tag. Endpoint đã LIVE (API catalog #12, §12 dưới) → binding này CHỈ curate mirror OAS (CONTRACT-ONLY). Cross-link SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — **KHÔNG nhân đôi schema**.

> **⚠️ ĐIỂM KHÁC CỐT-LÕI vs `getPmDashboardStats`/ADR-056 — SINGLE khối `kpis`, KHÔNG `trend_6months`.** `data` = **`CalibrationKpisData` = `{kpis}` CHÍNH XÁC 1 key** (GROUNDED `return {"kpis": {...}}` @`services/imm11.py:1192-1201`). `get_kpis` KHÔNG tính/trả `trend_6months`, KHÔNG `period`. ⇒ `CalibrationKpisData` **KHÔNG có key `trend_6months`** — điểm PHÂN BIỆT vs `PmDashboardStats` `{kpis, trend_6months}`. Thêm `trend_6months` = bịa field service KHÔNG trả. Thứ hai: **`pass_rate_pct` NON-nullable** (`else 0.0` @`:1190`) — ĐỐI-NGHỊCH `PmDashboardKpis.compliance_rate_pct` (nullable, `None` khi mẫu 0). Thứ ba: `overdue_assets`/`due_soon_assets` = **COUNT distinct-asset scalar** (`len(_overdue/_due_soon_asset_ids())` @`:1188-1189`), KHÔNG list.

| Mục | Giá trị |
|---|---|
| Mobile operationId | `getCalibrationKpis` (GET, path 88/88 mới), tag `calibration` |
| Handler LIVE | `assetcore.api.imm11.get_calibration_kpis` def@`api/imm11.py:147` — **`@frappe.whitelist()` BARE @146** (nhận GET; **KHÔNG `methods=["POST"]`**, **KHÔNG `rbac.require`** → 0 cap-gate) → `now = datetime.date.today()`@148 → `handle(svc.get_kpis, int(year) if year else now.year, int(month) if month else now.month)`@149-152 |
| Service LIVE | `services/imm11.py:1171` `get_kpis(year, month)` — `total = CalibrationRepo.count(scheduled_date between)`@1177 · `completed = count(status in [PASSED, COND_PASSED])`@1178 · `failed = count(status==FAILED)`@1182 · `overdue_assets = len(_overdue_asset_ids())`@1188 · `due_soon = len(_due_soon_asset_ids())`@1189 · `pass_rate = round((completed/total*100),1) if total else 0.0`@1190 · `return {"kpis": {6-key}}`@1192-1201 EXACT 1-khối |
| Params | **2 typed query-param INLINE** (mirror `getPmDashboardStats` CR-31a): `year` (`integer`, `in:query` `required:false`, **KHÔNG default YAML** — BE default `now.year`@148) · `month` (`integer`, `in:query` `required:false`, **KHÔNG default YAML** — BE default `now.month`@148). Signature `get_calibration_kpis(year=None, month=None)`@147 ⇒ CẢ 2 `required:false`. **0 param JSON-filters, 0 `mine`, 0 `page`.** |
| Response 200 | `oneOf [CalibrationKpisEnvelope, Error]` INLINE ở response-content (Decision-B route-by-VALUE `body.success`, **0 discriminator**, mirror `getPmDashboardStats`/`getAssetKpi`). ∈ `_MVP_READ_ENVELOPE` (map `→ #/components/schemas/CalibrationKpisEnvelope`, KHÔNG response-component). **∉ `_MVP_LIST_ENVELOPE`** (dashboard read ≠ list). |
| Status codes | 200 / 401 (`Unauthorized401` — bearer hết-hạn) / **403 SINGLE-SHAPE `Forbidden`** — **dispatcher-ONLY** (guest/no-token, bare `@whitelist` no `allow_guest`, **0 `rbac.require`** — KHÁC `sendToLab`/`cancelCalibration`). Mirror `getDueCalibrations`/`getPmDashboardStats`. Path ∈ `_MVP_BUSINESS_PATHS` ⇒ 401/403 symmetry set tự +1. |

**`CalibrationKpis`** — CLOSED (`additionalProperties:false`) **EXACT 6 prop** = 6 key `return["kpis"]` @`services/imm11.py:1194-1199`. **0 field thừa/thiếu** (VERBATIM service). **`required` = CẢ 6** (0 field nullable):

| # | Field | Type | Ground (`services/imm11.py`) |
|---|---|---|---|
| 1 | `total_this_month` | `integer` (**required**) | `total = CalibrationRepo.count({scheduled_date between})` @1177/1194 — count LUÔN int |
| 2 | `completed` | `integer` (**required**) | `count({status in [PASSED, COND_PASSED]})` @1178/1195 |
| 3 | `failed` | `integer` (**required**) | `count({status == FAILED})` @1182/1196 |
| 4 | `pass_rate_pct` | `number` (**required**, **KHÔNG `nullable`**) | `round((completed/total*100),1) if total else 0.0` @1190/1197. **Nhánh `else` = `0.0`** ⇒ LUÔN number, KHÔNG `None`. **ĐỐI-NGHỊCH `PmDashboardKpis.compliance_rate_pct`** (PM return `None` khi mẫu 0 ⇒ nullable ∉ required). Ở đây `else 0.0` ⇒ NON-null ∈ required |
| 5 | `overdue_assets` | `integer` (**required**, **KHÔNG array**) | `len(_overdue_asset_ids())` @1188/1198 — **COUNT distinct-asset** (quá hạn toàn-hệ, SoT schedule, BR-11-08). Khớp drill `?overdue=1` (§6.1: card == #asset). SCALAR, KHÔNG list |
| 6 | `due_soon_assets` | `integer` (**required**, **KHÔNG array**) | `len(_due_soon_asset_ids())` @1189/1199 — **COUNT distinct-asset** (cửa-sổ 30 ngày, BR-11-09). Khớp drill `?due_soon=1` (§6.1). SCALAR, KHÔNG list |

- **Always**: `additionalProperties:false` (closed) ở CẢ `CalibrationKpisEnvelope` (`required[success,data]`, `success.enum[true]`, `data = $ref CalibrationKpisData`), `CalibrationKpisData` (`required[kpis]`, CHỈ 1 key) LẪN `CalibrationKpis` (`required` = CẢ 6). `pass_rate_pct` = `type:number` NON-nullable.
- **Always**: path vào `_MVP_BUSINESS_PATHS` (401/403 symmetry) **VÀ** `_MVP_READ_ENVELOPE` (`→ CalibrationKpisEnvelope`, inline oneOf mirror `getPmDashboardStats`) ⇒ 2 set reconcile. `_MVP_LIST_ENVELOPE` GIỮ NGUYÊN.
- **Never**: KHÔNG thêm `trend_6months` vào `CalibrationKpisData` (service trả DUY NHẤT `{kpis}` — thêm = bịa field, codegen sinh property luôn absent). KHÔNG khai `pass_rate_pct` `nullable:true` (else=0.0, LUÔN number). KHÔNG khai `overdue_assets`/`due_soon_assets` là `type:array` (LIVE = COUNT scalar `len(...)`; shape-cũ §12 list = STALE). KHÔNG khai `default:` year/month YAML (BE default động `today()`). KHÔNG field Check integer-enum[0,1] (0 Check field). KHÔNG slot 403 dual-shape (cap-403 KHÔNG reachable — bare `@whitelist`). KHÔNG coi là list (∉ `_MVP_LIST_ENVELOPE`).

**403 = SINGLE-SHAPE `Forbidden` DISPATCHER-ONLY (KHÔNG cap-403 — mirror `getDueCalibrations`/`getPmDashboardStats`):**
- *dispatcher-403* (guest/no-token) trip TRƯỚC `handle()` (bare `@whitelist` no `allow_guest`) → HTTP-403 THẬT (`FrappeRawError`) ⇒ slot `403` = `$ref #/components/responses/Forbidden`.
- **KHÔNG có in-handler cap-403**: `get_calibration_kpis` **KHÔNG gọi `rbac.require`** (0 dòng cap-gate @`api/imm11.py:146-153`). Bearer-expired → **401** (`AuthenticationError`).
- **200-oneOf `Error` branch = `handle()`-wrapper DEFENSIVE** (catch-all): `get_kpis` KHÔNG `frappe.throw`/`ServiceError` domain ⇒ 0 code 4xx reachable; nhánh `Error` khai để đối-xứng `handle()`-contract. Mọi lỗi bất-thường ARRIVE **HTTP-200 + Error body** (Decision-B).

#### ADR-IMM11-CALKPI — `getCalibrationKpis` read-dashboard SINGLE-khối-`kpis` (KHÔNG `trend_6months`) + `CalibrationKpis` 6-prop VERBATIM + `pass_rate_pct` NON-nullable + 403 dispatcher-only

- **Status**: Accepted · **Date**: 2026-07-15
- **Context**: Màn "Bảng chỉ số hiệu chuẩn" (Dashboard-KPI Trục B) cần bộ chỉ số hiệu chuẩn theo tháng. `get_calibration_kpis` LIVE @source (bare `@whitelist`, service `get_kpis` trả `{"kpis": {6-key}}`). Cần contract mirror OAS để codegen — NHƯNG shape KHÁC `getPmDashboardStats` (ADR-056, endpoint sibling) ở **3 điểm**: (1) SINGLE khối `kpis`, KHÔNG `trend_6months`; (2) `pass_rate_pct` NON-nullable (else=0.0) vs PM `compliance_rate_pct` nullable; (3) `overdue_assets`/`due_soon_assets` = COUNT scalar (KHÔNG list, KHÁC shape-cũ §12).
- **Decision**: Curate 1 path GET, **2 typed query-param INLINE** `year`/`month` (integer, `required:false`, **KHÔNG default YAML** — BE default `datetime.date.today()`), **3 schema RIÊNG CLOSED**: (a) `CalibrationKpis` `required` = **CẢ 6-prop** VERBATIM (`total_this_month`/`completed`/`failed`/`overdue_assets`/`due_soon_assets` integer + `pass_rate_pct` number NON-nullable); (b) `CalibrationKpisData` `required[kpis]` **CHÍNH XÁC 1 key KHÔNG `trend_6months`**; (c) `CalibrationKpisEnvelope` `{success:[true], data:$ref CalibrationKpisData}`. 200 = inline oneOf [Env, Error] (Decision-B). `pass_rate_pct` NON-nullable (else=0.0). `overdue_assets`/`due_soon_assets` = `type:integer` COUNT. 403 SINGLE-SHAPE `Forbidden` dispatcher-ONLY. Path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_READ_ENVELOPE` (∉ `_MVP_LIST_ENVELOPE`). Tag `calibration`. Path 87→88. Đặt tên wrapper `CalibrationKpisData` (KHÔNG `...Stats`) để đối-xứng 3-tầng Envelope→Data→Kpis của PM + làm rõ payload chỉ có `kpis`.
- **Alternatives (loại)**: (a) thêm `trend_6months` cho parity `PmDashboardStats` → `get_kpis` trả DUY NHẤT `{kpis}` (bịa field); (b) `pass_rate_pct` `nullable:true` ∉ required (copy PM) → nhánh else=0.0 LUÔN number (nullable = sai-nguồn, ĐỐI-NGHỊCH chủ-đích PM); (c) `overdue_assets`/`due_soon_assets` `type:array` (list asset, như §12 STALE) → LIVE = COUNT scalar `len(...)`, drill-parity chốt §6.1 KHÔNG nhồi list vào card; (d) tag `dashboard` MỚI → fork module-taxonomy (siblings đơn-module + FE-composition, ADR-056 §2(c)); (e) inline `kpis` bỏ `CalibrationKpisData` → phá đối-xứng 3-tầng; (f) khai `default:` YAML → default động `today()`; (g) ∈ `_MVP_LIST_ENVELOPE` → dashboard ≠ list; (h) 403 dual-shape → 0 `rbac.require`.
- **Consequences**: +1 path +3 schema RIÊNG (PURE-YAML). **0 đụng** `api/imm11.py`+`services/imm11.py` (handler+service đã sẵn @source) ⇒ KHÔNG reload/migrate/commit. Bộ Dashboard-KPI nay 2 endpoint: `getPmDashboardStats` ({kpis 7-key + trend_6months}, nullable `compliance_rate_pct`) / **`getCalibrationKpis` ({kpis 6-key} SINGLE-khối, NON-null `pass_rate_pct`)** — cross-ref surface CÙNG FE-composition, KHÁC shape có-chủ-đích. **+ Self-Correction §12**: example `get_calibration_kpis` cũ (7-key compliance-report + `period` + `overdue_assets[]` LIST) STALE → cập-nhật 6-key LIVE (đồng-bộ §6.1 vốn đã đúng — xem §12). Test `TestMobileGetCalibrationKpisContract a..i` guard 6-field VERBATIM + `pass_rate_pct` NON-null + `trend_6months`-absent + overdue/due_soon integer-scalar + oneOf + naming-guard + live-signature parity.

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) YAML `87 → 88` path / `88` operationId (`getCalibrationKpis` mới, unique camelCase `^[a-z][a-zA-Z0-9]*$`, tag `calibration`, method GET, 0 dangling `$ref`, `safe_load`/parse OK); 2 typed query-param INLINE `year`+`month` (`integer`, `in:query`, `required:false`, **KHÔNG `default` key**); 200 = inline oneOf [`CalibrationKpisEnvelope`, `Error`]; slot `{200,401,403}` (`401 Unauthorized401` + **`403 Forbidden` SINGLE-SHAPE dispatcher-only** — description GHI RÕ bare-@whitelist 0 cap-403). (2) +3 schema CLOSED (`additionalProperties:false`): `CalibrationKpis` `required` = **CẢ 6-prop** {total_this_month,completed,failed,pass_rate_pct,overdue_assets,due_soon_assets} — 0 field thừa/thiếu, 5 `integer` + `pass_rate_pct` `number` **NON-nullable** (0 field nullable), `overdue_assets`/`due_soon_assets` `type:integer` (COUNT, KHÔNG array), 0 Check integer-enum · `CalibrationKpisData` `required[kpis]` **CHÍNH XÁC 1-key KHÔNG `trend_6months`** (`kpis:$ref CalibrationKpis`) · `CalibrationKpisEnvelope` `{success:enum[true], data:$ref CalibrationKpisData}`; tái-dùng `Unauthorized401`/`Forbidden`/`Error`; naming-guard `CalibrationKpis*` ∩ (`CalibrationDetail*`∪`DueCalibration*`∪`SubmitCalibration*`∪`CreateCalibration*`∪`CancelCalibration*`∪`SendToLab*`∪`ReceiveCertificate*`∪`AddMeasurement*`) == ∅. (3) Guard XANH @source (`bench --site miyano run-tests --app assetcore --module assetcore.tests.test_mobile_oas`): `_EXPECTED_TEST_COUNT` **792→801** (+9 TC `TestMobileGetCalibrationKpisContract a..i`: a=path+opId 88+GET+tag calibration+∈`_MVP_READ_ENVELOPE`+∉`_MVP_LIST_ENVELOPE`, b=2-typed-param year/month integer-required:false-KHÔNG-default-key, c=Kpis-CLOSED-EXACT-6-field + required==6 + 5-integer/1-number, d=`pass_rate_pct`-NON-nullable-∈required (anti false-null, đối-nghịch PM) + 0-nullable + overdue/due_soon-integer-scalar-KHÔNG-array + 0-Check, e=`CalibrationKpisData`-CLOSED-req[kpis] + `trend_6months`-ABSENT (anti-drift vs PmDashboardStats), f=`CalibrationKpisEnvelope`-CLOSED-{success:[true],data}, g=200-oneOf[Env,Error]-0-discr + slot{200,401,403}, h=3-schema-KHÔNG-orphan+0-dangling+count-reconcile, i=naming-guard-disjoint + live-signature parity `inspect.signature(imm11.get_calibration_kpis)=={year,month}` + git-diff-0-hunk pure-yaml) + `_MVP_READ_ENVELOPE` +1 (ĐỊNH NGHĨA `_CALIBRATION_KPIS_PATH` const + entry) + c5 **76→77** + `_MVP_LIST_ENVELOPE` **GIỮ 13** + membership `_MVP_BUSINESS_PATHS` (401/403 symmetry tự +1); `test_mobile_docset` **Ran 9 OK** THẬT (reconcile `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` **792→801** + `_GUARD_SUITE_SUM` **935→944** + `_MOBILE_OAS_TOTAL` **961→970** + delta var `calibration_kpis_delta=9`) — KHÔNG skip/xfail. `test_mobile_security_gate`/`test_oas_*` UNCHANGED (pure mobile-yaml). ⚠️ Baseline 87/792/76/13/935/961 grounded @source 2026-07-15 sau CR-31a/ADR-056 — **BE grep-verify @source TRƯỚC bump** (đa-phiên race). (4) **CONTRACT-ONLY**: `git diff` CHỈ `docs/mobile/openapi/assetcore-mobile.openapi.yaml` + `assetcore/tests/test_mobile_oas.py` + `assetcore/tests/test_mobile_docset.py` (+ docs md); `api/imm11.py`+`services/imm11.py` = **0 hunk** (0 worker-reload, 0 bench migrate). RED-before/GREEN-after cho MỌI TC mới. KHÔNG reload/migrate/commit (HARD-STOP USER — working-tree để USER review).

---

## 1. Quy ước chung

### 1.1. Response success — format chuẩn AssetCore

```jsonc
{
  "success": true,
  "data": <payload — object / array / null>
}
```

FE đọc `response.data.data` (axios + Frappe lớp ngoài đã wrap).

**HTTP status:** Frappe luôn trả **HTTP 200** khi không có unhandled exception. Phân biệt success/error qua field `success`, KHÔNG qua HTTP code.

### 1.2. Response error — format chuẩn

```jsonc
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt",
  "code": "BUSINESS_RULE",
  "fields": {
    "lab_supplier": "Vui lòng chọn lab có chứng chỉ ISO/IEC 17025"
  }
}
```

> Từ Sprint Notification 2026-05-29 vòng 4, error envelope IMM-11 hydrate thêm
> `message_code`, `severity`, `title`, `action_hint`, `context` qua
> `api_handler.handle()`. Xem **§11 — Notification Contract**.

### 1.3. Error code catalog

| Code | Khi nào |
|---|---|
| `NOT_FOUND` | IMM Asset Calibration / Asset / CAPA không tồn tại |
| `FORBIDDEN` | Không có quyền (role / Permission Query) |
| `VALIDATION` | Input validation fail (format, type, field thiếu) |
| `BUSINESS_RULE` | Vi phạm BR-11-xx (lab không ISO, lookback pending) |
| `CONFLICT` | Concurrent modify hoặc đã có CAL đang xử lý |
| `BAD_STATE` | State machine fail (Cancel sau Submit, OOS asset) |
| `INTERNAL` | Lỗi hệ thống unexpected |

### 1.4. Mapping FE ↔ BE error code

| BE (`ErrorCode`) | FE (`ErrorCode`) |
|---|---|
| `VALIDATION` | `VALIDATION_ERROR` |
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` |
| `NOT_FOUND` | `NOT_FOUND` |
| `FORBIDDEN` | `FORBIDDEN` |
| `CONFLICT` | `CONFLICT` |
| `BAD_STATE` | `BAD_STATE` |
| `INTERNAL` | `INTERNAL_ERROR` |

### 1.5. Pagination convention

```jsonc
{
  "success": true,
  "data": {
    "data": [...],
    "page": 1,
    "page_size": 20,
    "total": 145,
    "total_pages": 8
  }
}
```

---

## 2. Endpoint chi tiết

### 8. create_calibration — Tạo IMM Asset Calibration ✅ LIVE

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm11.create_calibration` |
| Role | Workshop Lead, IMM Technician |
| Idempotent | No |

**Request:**
```jsonc
{
  "asset": "AC-ASSET-2026-00101",       // required
  "calibration_type": "External",       // External | In-House
  "lab_supplier": "AC-SUP-2026-0010",   // required if External
  "scheduled_date": "2026-05-01",       // required
  "technician": "ktv.a@hospital.vn",   // required
  "is_recalibration": 0,               // default 0
  "pm_work_order": null
}
```

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "CAL-2026-00001",
    "asset": "AC-ASSET-2026-00101",
    "calibration_type": "External",
    "status": "Scheduled",
    "scheduled_date": "2026-05-01",
    "lab_supplier": "AC-SUP-2026-0010"
  }
}
```

**Errors:**
| Code (BE) | Code (FE) | Khi nào |
|---|---|---|
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` | lab không ISO 17025 (BR-11-01) |
| `BAD_STATE` | `BAD_STATE` | Asset Out of Service (không phải recal) |
| `CONFLICT` | `CONFLICT` | Đã có CAL đang xử lý cho asset này |

---

### 10. submit_calibration — Submit kết quả (quan trọng nhất) ✅ LIVE

> **Tên thực tế là `submit_calibration` (không phải `submit_calibration_results`).** Kết quả Pass/Fail được xác định bởi `overall_result` field trên DocType — tính từ measurements trước khi submit.

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm11.submit_calibration` |
| Role | IMM Technician |
| Idempotent | No |

**Request:**
```jsonc
{
  "name": "CAL-2026-00001"   // required — measurements đã add trước via add_measurement endpoint
}
```

> Measurements được nhập trước qua `add_measurement`. Sau đó `submit_calibration` submit DocType → controller on_submit → service `handle_calibration_pass` hoặc `handle_calibration_fail`.

**Response success (Pass):**
```jsonc
{
  "success": true,
  "data": {
    "name": "CAL-2026-00001",
    "status": "Passed",
    "overall_result": "Passed",
    "certificate_date": "2026-04-24",
    "next_calibration_date": "2027-04-24",   // = next_due của PHIẾU/lịch vừa Pass (basis+interval) — KHÔNG đổi (BR-11-04)
    "asset": "AC-ASSET-2026-00101",
    "asset_lifecycle_status": "Active",
    "capa_created": null,
    "lifecycle_event": "ALE-2026-00088",
    "measurements_summary": {"total": 1, "passed": 1, "failed": 0}
  }
}
```

> ⚠️ **Phân biệt 2 `next_calibration_date` (BR-11-13):** field `next_calibration_date` trong response NÀY = hạn của **chính phiếu/lịch vừa Pass** (`basis + interval`) — giữ nguyên cho backward-compat. KHÁC với `AC Asset.next_calibration_date` (CACHE thiết bị) mà `handle_calibration_pass` ghi = **`MIN(next_due_date)` trên MỌI active schedule** (rollup đa-lịch). Với asset multi-schedule, 2 giá trị này có thể KHÁC nhau (response = lịch vừa Pass; asset-cache = lịch sớm nhất). `get_due_calibrations` (endpoint 18) filter theo asset-cache → asset multi-schedule còn lịch sớm hơn KHÔNG bị rớt khỏi list.

**Response success (Fail):**
```jsonc
{
  "success": true,
  "data": {
    "name": "CAL-2026-00002",
    "status": "Failed",
    "overall_result": "Failed",
    "asset": "AC-ASSET-2026-00102",
    "asset_lifecycle_status": "Out of Service",
    "capa_created": "CAPA-2026-00015",
    "lookback_assets": ["AC-ASSET-2026-00104", "AC-ASSET-2026-00105"],
    "lifecycle_event": "ALE-2026-00089",
    "measurements_summary": {"total": 3, "passed": 2, "failed": 1, "failed_parameters": ["HGB"]}
  }
}
```

**Errors:**
| Code (BE) | Code (FE) | Khi nào |
|---|---|---|
| `VALIDATION` | `VALIDATION_ERROR` | Thiếu measured_value cho tham số |
| `VALIDATION` | `VALIDATION_ERROR` | External thiếu certificate_file hoặc accreditation (BR-11-01) |
| `VALIDATION` | `VALIDATION_ERROR` | certificate_date > today (BR-11-04) |
| `BAD_STATE` | `BAD_STATE` | Cancel record đã Submit (BR-11-05) |

**Side effects (Fail):**
- `transition_asset_status(asset, "Out of Service")` (IMM-00)
- `create_capa(asset, "IMM Asset Calibration", name, "Major")` (IMM-00)
- `perform_lookback_assessment(device_model, exclude=asset)` → ghi lookback_assets vào CAPA
- **Schedule due-now (BR-11-08b):** hạ `next_due_date = basis` (`certificate_date \| actual_date \| nowdate()`) cho MỌI `IMM Calibration Schedule` `{asset, is_active=1}` → `next_due_date <= today` → asset xuất hiện trong overdue/due-soon SoT (`get_calibration_kpis`/dashboard hết mask ON_SCHEDULE). Null-safe: 0 active schedule → no-op. Không đổi field response (shape bất biến — schedule là side-effect DB, không trả trong envelope submit).
- `create_lifecycle_event(asset, "calibration_failed")` (IMM-00)
- Email QA Officer + Operations Manager

**Curl ví dụ:**
```bash
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.submit_calibration' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "CAL-2026-00001"}'

# Measurements được nhập trước qua `add_measurement` (xem §7 Smoke test).
```

---

### 12. get_calibration_kpis — KPI report ✅ LIVE

> **Tên thực tế là `get_calibration_kpis` (không phải `get_calibration_compliance_report`).**

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm11.get_calibration_kpis` |
| Role | All |
| Idempotent | Yes |

**Request:** 2 query-param `year` + `month` (integer, **optional** — bỏ trống ⇒ BE default `datetime.date.today()` năm/tháng hiện tại @`api/imm11.py:148`).
```jsonc
GET /api/method/assetcore.api.imm11.get_calibration_kpis?year=2026&month=4
```

**Response success (GROUNDED `services/imm11.py:1192-1201` — 6-key, SINGLE khối `kpis`):**
```jsonc
{
  "success": true,
  "data": {
    "kpis": {
      "total_this_month": 16,   // count phiếu scheduled_date trong tháng (int)
      "completed": 14,          // count status ∈ [Passed, Conditional Pass] (int)
      "failed": 1,              // count status == Failed (int)
      "pass_rate_pct": 87.5,    // completed/total×100 round1; 0.0 khi total==0 (number NON-null)
      "overdue_assets": 4,      // len(_overdue_asset_ids()) — COUNT distinct-asset quá hạn (int scalar)
      "due_soon_assets": 7      // len(_due_soon_asset_ids()) — COUNT distinct-asset sắp hạn (int scalar)
    }
  }
}
```

> **⚠️ Self-Correction (2026-07-15, CR-31b / ADR-MOBILE-057):** Example CŨ của §12 mô-tả shape STALE (7-key compliance-report `compliance_rate_pct`/`total_scheduled`/`completed_on_time`/`out_of_tolerance_rate_pct`/`capa_open_count`/`capa_closure_rate_pct`/`avg_days_sent_to_cert` + `period` + `overdue_assets[]` **LIST**) — KHÔNG khớp `get_kpis` LIVE. Nguồn thật `services/imm11.py:1171-1201` trả **DUY NHẤT `{"kpis": {6-key}}`** (KHÔNG `period`, KHÔNG `trend_6months`); `overdue_assets`/`due_soon_assets` là **COUNT scalar** (`len(...)` @`:1188-1189`) — KHÔNG list asset. Shape mới đồng-bộ với §6.1 (vốn đã đúng: `get_calibration_kpis().overdue_assets` = `len(_overdue_asset_ids())`) + OAS mirror `CalibrationKpis` (ADR-MOBILE-057). Nếu cần bộ chỉ số compliance/CAPA đầy-đủ (7-key + trend) → dùng `get_calibration_dashboard` (endpoint #13, KPIs + lists), KHÔNG `get_calibration_kpis`.

---

## 6.1 Canonical-value rule — KPI calibration due/overdue == drill (BR-11-08/09)

Số trên KPI card PHẢI bằng số dòng khi click drill (cùng SoT, không lệch). 1 nguồn predicate (`services/imm11.py §4.1`), dùng chung dashboard + module.

| KPI / field | Predicate (SoT) | Drill route + query | Quan hệ |
|---|---|---|---|
| `get_calibration_kpis().overdue_assets` | `len(_overdue_asset_ids())` — DISTINCT asset, active schedule, `next_due < today`, không decommissioned | `/calibration/schedules?overdue=1` | card == `len(drill)` (de-dup theo asset) |
| `get_calibration_kpis().due_soon_assets` | `len(_due_soon_asset_ids())` — DISTINCT asset, `today <= next_due <= today+30`, loại overdue, không decommissioned | `/calibration/schedules?due_soon=1` (cửa-sổ-2-biên `next_due BETWEEN [today, today+30]` + `asset IN _due_soon_asset_ids()`) | card == `len(drill)` (de-dup theo asset, KHÔNG cần post-filter `next_due >= today`) |
| Dashboard `calibration.overdue` (`api/dashboard.py`) | `len(_overdue_asset_ids())` (import từ `services.imm11`) | giống trên | == module `overdue_assets` (CÙNG SoT) |
| Dashboard `calibration.due_30d` | `len(_due_soon_asset_ids())` | giống trên | == module `due_soon_assets` |

**Boundary (chốt):** OVERDUE ⟺ `next_due < today` (strict `<`); DUE_SOON ⟺ `today <= next_due <= today+30` (2 biên inclusive); `next_due == today` → DUE_SOON; `next_due == today+30` → DUE_SOON; `next_due == today+31` → ON_SCHEDULE.

**FAIL → due-now nằm trong tập (BR-11-08b):** asset vừa `overall_result=Fail` được `handle_calibration_fail` hạ `next_due = basis` (`<= today`). `basis < today` (cert/actual quá khứ) → asset vào `overdue_assets`; `basis == today` (nowdate) → vào `due_soon_assets` (due-now). Hai trường hợp đều khiến card overdue-or-due TĂNG +1 asset và drill `?overdue=1` HOẶC `?due_soon=1` chứa asset đó → count == drill bất biến, KHÔNG undercount asset FAIL. Asset FAIL KHÔNG còn ON_SCHEDULE.

**Phân biệt drill param (`_normalize_schedule_filters`, 3 nhánh — ưu tiên `overdue` > `due_soon` > `due_before`):**

- `?overdue=1` — card `calib_overdue`: `next_due < today` + `is_active=1` + `asset IN _overdue_asset_ids()`.
- `?due_soon=1` — card `calib_due` "Hiệu chuẩn đến hạn": **cửa-sổ-2-biên** `next_due BETWEEN [today, today+30]` + `is_active=1` + `asset IN _due_soon_asset_ids()` (đã LOẠI overdue). Drill tái lập CHÍNH XÁC tập KPI — số asset distinct == `calib_due`. Overdue rows KHÔNG lẫn (thuộc `?overdue=1`).
- `?due_before=<X>` — **cutoff-tùy-ý LEGACY (tập-BAO)**: `next_due <= X` + `is_active=1`, chỉ loại asset thanh lý. GỒM cả overdue (`<= X`). KHÔNG dùng cho card due-soon (sẽ lệch count). Giữ riêng cho caller cũ cần cutoff bất kỳ.

**Vendor-scope an toàn:** khi `apply_vendor_scope` đã inject `asset IN [allowed]`, cả 3 nhánh GIAO (intersect) caller-scope với tập SoT/decom — KHÔNG clobber → vendor KHÔNG thấy asset ngoài phạm vi khi drill.

**Drill `overdue=1` vs `due_before`:** `_normalize_schedule_filters` đã dịch `overdue=1` → `next_due_date < today` và `due_before=X` → `next_due_date <= X` trên `IMM Calibration Schedule` (is_active=1). Drill list trả theo SCHEDULE ROW; KPI card đếm theo ASSET (de-dup) → khi 1 asset có >1 schedule overdue, FE hiển thị nhiều row drill nhưng KPI đếm 1; doc-of-record: **KPI = #asset, drill list có thể >#asset nhưng tập asset của drill == tập KPI**. FE render BE count/list verbatim (KHÔNG inline compute).

**Mint-gap:** asset tạo trực tiếp với `is_calibration_required` (`create_calibration_schedule_from_asset`) set `Schedule.next_due_date` → xuất hiện đồng nhất ở CẢ dashboard VÀ module (trước fix: chỉ dashboard thấy).

---

## 7. Smoke test playbook

```bash
# 1. Tạo Calibration record
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.create_calibration' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"asset":"AC-ASSET-2026-00101","calibration_type":"External","scheduled_date":"2026-05-01","technician":"ktv@hospital.vn"}'

# 2. Thêm measurement
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.add_measurement' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"name":"CAL-2026-00001","parameter_name":"WBC","unit":"10³/µL","nominal_value":7.5,"tolerance_positive":3,"tolerance_negative":3,"measured_value":7.6}'

# 3. Submit (triggers Pass/Fail handler)
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.submit_calibration' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"name":"CAL-2026-00001"}'

# 4. KPI report
curl 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.get_calibration_kpis?year=2026&month=4' \
  -H 'Authorization: token <key>:<secret>'

# 5. Dashboard
curl 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.get_calibration_dashboard' \
  -H 'Authorization: token <key>:<secret>'
```

---

## 11. Notification Contract (Sprint Notification 2026-05-29 vòng 4) — SINGLE SOURCE OF TRUTH

Mọi tương tác IMM-11 trả về **envelope chuẩn** đã chuẩn hoá BE → FE. FE KHÔNG
hardcode câu chữ — chỉ đọc `message_code` rồi render qua `useNotify`. Contract đã
chốt vòng 1 (IMM-09), vòng 2 (IMM-12), vòng 3 (IMM-08) — vòng 4 áp dụng cho IMM-11.

### 11.1 Envelope shape

Success (`_ok`):
```json
{ "success": true, "data": { ... } }
```
Lỗi (`_err`, hydrate từ registry qua `api_handler.handle()`):
```json
{
  "success": false,
  "error": "Phiếu hiệu chuẩn này đã được chốt — không thể thao tác lại.",
  "code": "CONFLICT",
  "message_code": "IMM11-ALREADY-SUBMITTED",
  "severity": "warning",
  "title": "Phiếu hiệu chuẩn đã chốt",
  "action_hint": "Không cần thao tác lại — dùng Amend nếu cần điều chỉnh.",
  "context": {},
  "http_status": 409
}
```

**Bất biến (contract):** mọi error envelope nghiệp vụ IMM-11 PHẢI có `message_code`,
`severity`, `title`. Không còn `frappe.throw(_("..."))` leak message Frappe ra FE, và
không còn `ServiceError(ErrorCode.*, "...")` thô (rớt message_code/severity). Service
raise qua `nthrow(MSG.IMM11_*)`; DocType `validate`/`before_submit`/`on_cancel`/`on_trash`
hook (BR-11-*/VR-11-*/CAL-*) raise qua `nthrow_in_hook(MSG.IMM11_*)`.

### 11.2 Danh mục MSG cần bổ sung vào `utils/messages.py`

Severity tuân quy tắc §11.5. Tái dùng mã hệ thống (`AUTH_FORBIDDEN`,
`VAL_INVALID_PARAMS`, `SYS_500`) khi phù hợp.

| MSG.* | code (kebab) | severity | http | title | template (VI) | action_hint |
|---|---|---|---|---|---|---|
| `IMM11_CAL_NOT_FOUND` | `IMM11-CAL-NOT-FOUND` | warning | 404 | Không tìm thấy phiếu hiệu chuẩn | Không tìm thấy phiếu hiệu chuẩn: {name}. | Kiểm tra lại mã phiếu trong danh sách hiệu chuẩn. |
| `IMM11_SCHEDULE_NOT_FOUND` | `IMM11-SCHEDULE-NOT-FOUND` | warning | 404 | Không tìm thấy lịch hiệu chuẩn | Không tìm thấy lịch hiệu chuẩn: {name}. | Kiểm tra lại mã lịch trong danh sách. |
| `IMM11_ASSET_NOT_FOUND` | `IMM11-ASSET-NOT-FOUND` | warning | 404 | Không tìm thấy thiết bị | Thiết bị không tồn tại trong danh mục tài sản. | Kiểm tra lại mã thiết bị. |
| `IMM11_ASSET_BLOCKED` | `IMM11-ASSET-BLOCKED` | warning | 409 | Thiết bị không thể hiệu chuẩn | Thiết bị đang ở trạng thái không cho phép tạo phiếu hiệu chuẩn (CAL-008). | Chuyển thiết bị về trạng thái hoạt động hoặc dùng tái hiệu chuẩn. |
| `IMM11_NO_FIELDS` | `IMM11-NO-FIELDS` | warning | 400 | Không có thay đổi | Không có trường hợp lệ nào để cập nhật. | Chọn ít nhất một trường để cập nhật rồi thử lại. |
| `IMM11_ALREADY_SUBMITTED` | `IMM11-ALREADY-SUBMITTED` | warning | 409 | Phiếu hiệu chuẩn đã chốt | Phiếu hiệu chuẩn này đã được chốt — không thể thao tác lại. | Không cần thao tác lại — dùng Amend nếu cần điều chỉnh. |
| `IMM11_SCHEDULE_HAS_SUBMITTED` | `IMM11-SCHEDULE-HAS-SUBMITTED` | warning | 409 | Lịch còn phiếu đã chốt | Không thể xoá lịch hiệu chuẩn đang có phiếu đã chốt. | Huỷ hoặc lưu trữ các phiếu liên quan trước khi xoá lịch. |
| `IMM11_NOT_EXTERNAL` | `IMM11-NOT-EXTERNAL` | warning | 422 | Chỉ áp dụng cho hiệu chuẩn ngoài | Thao tác này chỉ áp dụng cho phiếu hiệu chuẩn External (gửi lab). | Chọn phiếu có loại hiệu chuẩn External rồi thử lại. |
| `IMM11_SEND_LAB_BAD_STATE` | `IMM11-SEND-LAB-BAD-STATE` | warning | 409 | Không thể gửi lab | Không thể gửi lab khi phiếu đang ở trạng thái '{state}'. | Chỉ gửi lab khi phiếu ở trạng thái Đã lên lịch hoặc Đang xử lý. |
| `IMM11_RECEIVE_CERT_BAD_STATE` | `IMM11-RECEIVE-CERT-BAD-STATE` | warning | 409 | Không thể nhận chứng chỉ | Chỉ nhận chứng chỉ khi phiếu ở trạng thái Đã gửi lab. | Gửi phiếu cho lab trước khi nhận chứng chỉ. |
| `IMM11_CERT_FIELDS_REQUIRED` | `IMM11-CERT-FIELDS-REQUIRED` | warning | 422 | Thiếu thông tin chứng chỉ | Cần đủ tệp chứng chỉ, số chứng chỉ và ngày cấp. | Điền đủ ba thông tin chứng chỉ rồi thử lại. |
| `IMM11_CANCEL_REASON_REQUIRED` | `IMM11-CANCEL-REASON-REQUIRED` | warning | 422 | Thiếu lý do huỷ | Bắt buộc nhập lý do khi huỷ phiếu hiệu chuẩn. | Nhập lý do huỷ rồi thử lại. |
| `IMM11_CANCEL_SUBMITTED` | `IMM11-CANCEL-SUBMITTED` | warning | 409 | Không thể huỷ phiếu đã chốt | Phiếu hiệu chuẩn đã chốt — không thể huỷ (BR-11-05). | Dùng chức năng Amend để điều chỉnh phiếu đã chốt. |
| `IMM11_ALREADY_CANCELLED` | `IMM11-ALREADY-CANCELLED` | warning | 409 | Phiếu đã huỷ | Phiếu hiệu chuẩn này đã được huỷ trước đó. | Không cần thao tác lại. |
| `IMM11_NO_MEASUREMENTS` | `IMM11-NO-MEASUREMENTS` | warning | 422 | Thiếu tham số đo | Phải nhập ít nhất một tham số đo trước khi gửi duyệt (CAL-005). | Thêm tham số đo rồi gửi duyệt lại. |
| `IMM11_MEASUREMENT_VALUE_REQUIRED` | `IMM11-MEASUREMENT-VALUE-REQUIRED` | warning | 422 | Thiếu giá trị đo | Tham số '{parameter}' chưa có giá trị đo (CAL-004). | Nhập giá trị đo cho mọi tham số rồi thử lại. |
| `IMM11_RESULT_REQUIRED` | `IMM11-RESULT-REQUIRED` | warning | 422 | Thiếu kết quả tổng | Phiếu hiệu chuẩn phải có kết quả tổng trước khi gửi duyệt (CAL-006). | Hoàn tất nhập đo để hệ thống tính kết quả rồi thử lại. |
| `IMM11_LAB_REQUIRED` | `IMM11-LAB-REQUIRED` | warning | 422 | Chưa chọn lab hiệu chuẩn | Hiệu chuẩn ngoài bắt buộc chọn lab hiệu chuẩn (VR-11-01). | Chọn lab hiệu chuẩn rồi thử lại. |
| `IMM11_LAB_NOT_ACCREDITED` | `IMM11-LAB-NOT-ACCREDITED` | warning | 422 | Lab chưa đủ điều kiện | Lab phải có loại 'Calibration Lab' và chứng chỉ ISO/IEC 17025 còn hạn (VR-11-02). | Chọn lab khác hoặc cập nhật chứng chỉ ISO/IEC 17025. |
| `IMM11_CERT_FILE_REQUIRED` | `IMM11-CERT-FILE-REQUIRED` | warning | 422 | Thiếu tệp chứng chỉ | Vui lòng tải lên chứng chỉ hiệu chuẩn (VR-11-03). | Đính kèm tệp chứng chỉ rồi thử lại. |
| `IMM11_LAB_ACCRED_NUMBER_REQUIRED` | `IMM11-LAB-ACCRED-NUMBER-REQUIRED` | warning | 422 | Thiếu số công nhận | Vui lòng nhập số công nhận ISO/IEC 17025 (VR-11-04). | Nhập số công nhận của lab rồi thử lại. |
| `IMM11_REF_STANDARD_REQUIRED` | `IMM11-REF-STANDARD-REQUIRED` | warning | 422 | Thiếu thiết bị chuẩn | Hiệu chuẩn nội bộ bắt buộc nhập serial thiết bị chuẩn (VR-11-06). | Nhập serial thiết bị chuẩn rồi thử lại. |
| `IMM11_CERT_DATE_FUTURE` | `IMM11-CERT-DATE-FUTURE` | warning | 422 | Ngày chứng chỉ không hợp lệ | Ngày cấp chứng chỉ không thể nằm trong tương lai (VR-11-07). | Chọn lại ngày cấp chứng chỉ. |
| _(success)_ `IMM11_CREATE_SUCCESS` | `IMM11-CREATE-SUCCESS` | success | 200 | Đã tạo phiếu hiệu chuẩn | Đã tạo phiếu hiệu chuẩn {name} cho thiết bị {asset}. | — |
| _(success)_ `IMM11_SUBMIT_SUCCESS` | `IMM11-SUBMIT-SUCCESS` | success | 200 | Đã chốt phiếu hiệu chuẩn | Đã ghi nhận kết quả hiệu chuẩn {name}. | — |
| _(success)_ `IMM11_SCHEDULE_CREATE_SUCCESS` | `IMM11-SCHEDULE-CREATE-SUCCESS` | success | 200 | Đã tạo lịch hiệu chuẩn | Đã tạo lịch hiệu chuẩn cho thiết bị, đến hạn {next_due_date}. | — |
| _(success)_ `IMM11_SEND_LAB_SUCCESS` | `IMM11-SEND-LAB-SUCCESS` | success | 200 | Đã gửi lab | Đã gửi phiếu {name} tới lab hiệu chuẩn. | — |
| _(success)_ `IMM11_CERT_RECEIVED_SUCCESS` | `IMM11-CERT-RECEIVED-SUCCESS` | success | 200 | Đã nhận chứng chỉ | Đã nhận chứng chỉ #{certificate_number} cho phiếu {name}. | — |
| _(success)_ `IMM11_CANCEL_SUCCESS` | `IMM11-CANCEL-SUCCESS` | success | 200 | Đã huỷ phiếu | Đã huỷ phiếu hiệu chuẩn {name}. | — |

> Content tuân `messages.py` §quy chuẩn — Chủ thể + Hậu quả + Hành động, không từ
> kỹ thuật, không đổ lỗi user. Sau khi thêm vào `messages.py`, chạy
> `python scripts/gen_fe_messages.py` để regen `frontend/src/i18n/messages.ts`.

### 11.3 BE migration checklist (cho assetcore-be)

- `services/imm11.py` service layer: thay TẤT CẢ `raise ServiceError(ErrorCode.*, "...")`
  thô bằng `nthrow(MSG.IMM11_*)` tương ứng (xem bảng §11.2). `ServiceError` thô làm rớt
  `message_code`/`severity` → envelope không hydrate được. Đây chính là backlog vòng 3.
- `assetcore/doctype/imm_asset_calibration/imm_asset_calibration.py` hook
  `validate`/`before_submit`/`on_cancel`/`on_trash`: 11 `frappe.throw(_(...))` (CAL-004/005/006,
  VR-11-01/02/03/04/06/07, BR-11-05) → `nthrow_in_hook(MSG.IMM11_*)`. DocType hook BẮT BUỘC
  dùng `nthrow_in_hook` (không phải `nthrow`).
- `api/imm11.py`: bỏ `_parse_filters`/`_handle` cục bộ + `from utils.helpers import _err,_ok`
  → dùng `from assetcore.utils.api_handler import handle, parse_json` +
  `from assetcore.utils.response import _ok, _err`. Giữ guard rbac/vendor-scope trước `handle`.
- Audit trail (`log_audit_event`, `create_lifecycle_event`), CAPA/lookback side-effect
  (`handle_calibration_fail`), cross-module IMM-12 incident KHÔNG đổi — framework chỉ
  chuẩn hoá phản hồi user.
- KHÔNG chạm Wave N1 treo: `services/notifications.py`, `notify_calibration_due` call site
  (chỉ giữ nguyên).

### 11.4 FE migration checklist (cho assetcore-fe)

- Store `stores/imm11.ts`: expose `lastApiError` (`ApiError | null`) + helper `_captureError`;
  mọi action catch → `_captureError(e)` (giống `stores/imm08.ts`).
- Views `calibration/*` (CalibrationDetailView, CalibrationCreateView, CalibrationListView,
  CalibrationScheduleListView, CalibrationDashboard): success → `notify.show(MSG.IMM11_*)`;
  fail → `notify.fromError(store.lastApiError)`. Bỏ try/catch tự build string từ `e.message` BE.
- Thêm test store `stores/imm11.test.ts` nếu store có action mutate (capture error path).

### 11.5 Quy tắc severity (chốt cho IMM-11)

- `warning` = lỗi nghiệp vụ user tự sửa được (validation CAL-*/VR-11-*, bad-state, not-found,
  conflict) → toast vàng, GIỮ form, không reload.
- `error` = lỗi hệ thống (`SYS-*`) → toast đỏ.
- `success` = thao tác thành công → toast xanh.

> Lưu ý: VR-11-02 (lab ISO/IEC 17025) là validation nghiệp vụ user sửa được (chọn lab khác),
> KHÔNG phải compliance-blocking như BR-12 clinical impact. Do đó severity = `warning`,
> không `critical`. Calibration Fail → CAPA/lookback là side-effect tự động của `on_submit`
> (submit vẫn THÀNH CÔNG, severity success), không phải lỗi chặn user.

---

## DoD — File 05 hoàn chỉnh

- [x] API Catalog (§0) liệt kê 18 endpoint thực tế (actual @frappe.whitelist names)
- [x] Response success format `{"success": true, "data": {...}}`
- [x] Response error format `{"success": false, "error": "...", "code": "..."}`
- [x] Error code catalog + FE mapping
- [x] Endpoint `submit_calibration` (actual name) với request schema + response Pass + Fail
- [x] Side effects nêu rõ (Fail path)
- [x] Curl ví dụ (5 commands)
- [x] Pagination convention
- [x] ✅ FE types: `frontend/src/api/imm11.ts` (interfaces CalibrationSchedule, AssetCalibration, CalibrationMeasurement, CalibrationKpis, DueCalibrationItem)
- [x] ✅ FE store: `frontend/src/stores/imm11.ts` (useImm11Store)
- [ ] Reviewed bởi BE Lead + FE Lead
