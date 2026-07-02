# 05 — API Specification — IMM-08 Bảo trì định kỳ (PM)

| Mục | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm08.<function>` |
| Auth | Frappe session HOẶC `Authorization: token <key>:<secret>` |
| Cập nhật | 2026-05-14 |

---

## 0. API Catalog

### PM Work Orders

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent | Liên kết US |
|---|---|---|---|---|---|---|
| 1 | `assetcore.api.imm08.list_pm_work_orders` | GET | List PM WO với filter (`filters` JSON-blob + **`mine`**) + pagination. `mine=1` scope `assigned_to==session.user` (tab "Phiếu PM của tôi" MVP-5a — §2 #1 "list_pm_work_orders — filter mine" + ADR-IMM08-MOB-04) | All IMM roles | ✓ | US-08-01 |
| 2 | `assetcore.api.imm08.get_pm_work_order` | GET | Chi tiết 1 WO + checklist | All IMM roles | ✓ | — |
| 3 | `assetcore.api.imm08.assign_technician` | POST | Phân công Kỹ thuật viên cho WO Open/Overdue | Workshop Head, CMMS Admin | ✗ | US-08-06 |
| 4 | `assetcore.api.imm08.submit_pm_result` | POST | Kỹ thuật viên nộp kết quả PM (submit WO) | HTM Technician, Workshop Head | ✗ | US-08-02 |
| 5 | `assetcore.api.imm08.report_major_failure` | POST | Dừng PM + tạo CM khẩn + Asset OOS | HTM Technician, Workshop Head | ✗ | US-08-03 |
| 6 | `assetcore.api.imm08.reschedule_pm` | POST | Hoãn lịch PM (lý do bắt buộc) | Workshop Head, CMMS Admin | ✗ | US-08-06 |
| 7 | `assetcore.api.imm08.create_pm_work_order` | POST | Tạo PM WO thủ công (ad-hoc) | Workshop Head, CMMS Admin | ✗ | — |

### Calendar & Dashboard

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent | Liên kết US |
|---|---|---|---|---|---|---|
| 8 | `assetcore.api.imm08.get_pm_calendar` | GET | Events theo tháng cho calendar view | Workshop Head, HTM Technician | ✓ | US-08-07 |
| 9 | `assetcore.api.imm08.get_pm_dashboard_stats` | GET | KPI compliance + trend 6 tháng | Workshop Head, VP Block2, CMMS Admin | ✓ | US-08-08 |
| 10 | `assetcore.api.imm08.get_asset_pm_history` | GET | Lịch sử PM Task Log của 1 thiết bị | All IMM roles | ✓ | — |

### PM Schedules

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent |
|---|---|---|---|---|---|
| 11 | `assetcore.api.imm08.list_pm_schedules` | GET | Danh sách PM Schedule | All IMM roles | ✓ |
| 12 | `assetcore.api.imm08.get_pm_schedule` | GET | Chi tiết 1 PM Schedule | All IMM roles | ✓ |
| 13 | `assetcore.api.imm08.create_pm_schedule` | POST | Tạo PM Schedule mới | Workshop Head, CMMS Admin | ✗ |
| 14 | `assetcore.api.imm08.update_pm_schedule` | POST | Cập nhật PM Schedule | Workshop Head, CMMS Admin | ✗ |
| 15 | `assetcore.api.imm08.set_pm_schedule_status` | POST | Đổi status (Active/Paused/Suspended) | Workshop Head, CMMS Admin | ✗ |
| 16 | `assetcore.api.imm08.delete_pm_schedule` | POST | Xóa PM Schedule | CMMS Admin | ✗ |

### PM Checklist Templates

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent |
|---|---|---|---|---|---|
| 17 | `assetcore.api.imm08.list_pm_templates` | GET | Danh sách checklist template | All IMM roles | ✓ |
| 18 | `assetcore.api.imm08.get_pm_template` | GET | Chi tiết 1 template | All IMM roles | ✓ |
| 19 | `assetcore.api.imm08.create_pm_template` | POST | Tạo template mới | Workshop Head, CMMS Admin | ✗ |
| 20 | `assetcore.api.imm08.update_pm_template` | POST | Cập nhật template | Workshop Head, CMMS Admin | ✗ |
| 21 | `assetcore.api.imm08.approve_pm_template` | POST | Phê duyệt template | Workshop Head, CMMS Admin | ✗ |
| 22 | `assetcore.api.imm08.version_pm_template` | POST | Tạo phiên bản mới từ template cũ | Workshop Head, CMMS Admin | ✗ |
| 23 | `assetcore.api.imm08.delete_pm_template` | POST | Xóa template | CMMS Admin | ✗ |
| 24 | `assetcore.api.imm08.apply_pm_template_to_category` | POST | Bulk-tạo PM Schedule cho mọi asset cùng danh mục với template | Workshop Head, CMMS Admin | ✗ |

---

## 0.1. Mobile Contract Binding (Mobile-BE — màn `PMWorkOrderDetailView`, MVP-flow-4)

> **Ranh giới**: endpoint dùng chung 1 handler `imm08.*` cho cả web-FE (mục §2) và mobile-BE. Contract codegen-ready cho mobile mô tả ở SSoT riêng `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3.0.3, **45 path → +1 = 46** sau round này — `reschedulePm`, §0.1.3, **ĐÓNG NỐT action-set `PMWorkOrderDetailView`**) + [`docs/mobile/ADR-MOBILE-014.md`](../mobile/ADR-MOBILE-014.md) + [`docs/mobile/ADR-MOBILE-013.md`](../mobile/ADR-MOBILE-013.md) + [`docs/mobile/ADR-MOBILE-012.md`](../mobile/ADR-MOBILE-012.md) + [`04-api-contract.md §8.25`](../mobile/04-api-contract.md). Mục này là **cross-link** — KHÔNG nhân đôi schema; mọi sửa field đồng bộ 2 nơi.

### 0.1.1. Write-action binding — `assignPmTechnician` (PM-DISPATCH, mắt-xích-GIỮA MVP-flow-4)

> **Bối cảnh (dead-end GIỮA đóng)**: Workshop Head mở `getPmWorkOrder` detail (`Open`/`Overdue`) cần **phân công 1 KTV** (+`scheduled_date` optional) TRƯỚC khi KTV `submitPmResult` (§8.14 mobile, ✅). Chuỗi PM-detail = `createPmWorkOrder` (✅) → **`assignPmTechnician` (THIẾU — bồi round này)** → `submitPmResult` (✅). Thiếu mắt-xích-GIỮA ⇒ nút "Phân công" trên `PMWorkOrderDetailView` dead-end (buộc làm trên web-FE). **Parity** repair `createRepairWorkOrder → [assignTechnician] → startRepair` (IMM-09).

| Mục | Giá trị |
|---|---|
| Mobile operationId | `assignPmTechnician` (path 44/44, mới — UNIQUE camelCase, **KHÁC** repair `assignTechnician`), tag `work-order` |
| HTTP method / path | `POST /api/method/assetcore.api.imm08.assign_technician` — **CHỈ key `post` SAU flip** (write-action DISPATCH: status Open/Overdue→In Progress + asset-transition, **KHÔNG idempotent** — KHÔNG GET) |
| Summary | `[MVP-4] PM dispatch Open/Overdue→In Progress` |
| Handler | `api/imm08.py:47` `assign_technician(name, technician, scheduled_date=None)` → `rbac.require("pm.write")` (`api/imm08.py:49`) → `handle(svc.assign_technician, name, technician=technician, scheduled_date=scheduled_date)` (`:50-51`) |
| **⚡ VERB-FLIP-THIS-ROUND** | decorator `api/imm08.py:46` flip **bare `@frappe.whitelist()` → `@frappe.whitelist(methods=['POST'])`** — ĐÚNG **1 dòng** (signature/body/cap UNCHANGED). Đóng **verb-parity gap R33 BỎ SÓT** (R33 flip `submit_pm_result` `imm08.py:54` + 3 write-action imm11, SÓT `assign_technician`) — **sibling imm08 của `add_measurement`** (ADR-MOBILE-011). ⚠️ **Doc đi-trước-code**: §0 catalog row #3 + §5 code-sketch (`:495`) đã khai POST từ lâu; flip = đưa source khớp doc-intent. Sau flip POST-only ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()` |
| Cap | `pm.write` (in-handler `rbac.require` @`api/imm08.py:49`) |
| Lifecycle | DISPATCH — `assigned_to=technician`, `assigned_by=session.user`, `scheduled_date` (chỉ khi truthy `:674-675`), `status=PMStatus.IN_PROGRESS` (`:676`) → `_transition_asset(... AssetStatus.UNDER_MAINTENANCE ...)` (`:678` — asset → "Under Maintenance" + **sinh Lifecycle Event audit**) |
| requestBody | **INLINE** (path-level, KHÔNG component — mirror repair `assignTechnician`), content **`application/json` ONLY** (KHÔNG oneOf json+form — action đơn-record) `$ref AssignPmTechnicianRequest`; `required:true` |
| Response 200 | `oneOf [AssignPmTechnicianEnvelope, Error]` Ở TẦNG response-content-schema (route-by-VALUE `body.success`, **0 discriminator** — pattern C6/C7); cả 2 nhánh `additionalProperties:false` + disjoint required-set |
| Status codes | 200 / 401 (`Unauthorized401` bearer hết-hạn/invalid → HTTP-401 THẬT) / 403 **SINGLE-SHAPE** `Forbidden` |

**`AssignPmTechnicianRequest` — closed, required EXACT 2 + optional `scheduled_date` (GROUNDED signature @`api/imm08.py:47`):**

| # | Field | type | Required? | Ghi chú |
|---|---|---|---|---|
| 1 | `name` | string | ✓ required | PK PM Work Order (positional, vd PM-2026-00001) |
| 2 | `technician` | string | ✓ required | Email KTV được gán (`assigned_to`). Đích của `listUsers` (technician-picker) |
| 3 | `scheduled_date` | string | optional | Ngày dự kiến thực hiện — `scheduled_date: str = None` @`api/imm08.py:47`; service set chỉ khi truthy `:674-675` (KHÁC repair optional `priority`) |

**`AssignPmTechnicianResponse` — RIÊNG, closed EXACT 3-key (GROUNDED return @`services/imm08.py:679`):**

| # | Field | type | Ghi chú |
|---|---|---|---|
| 1 | `name` | string (**required**) | PK echo input (`wo.name`) |
| 2 | `status` | string (**required**) | `enum` = **PMStatus** 7-state `[Open, In Progress, Completed, Overdue, Cancelled, "Halted–Major Failure", "Pending–Device Busy"]` (`services/imm08.py:43-50` — copy en-dash byte-khớp), `example: In Progress` (`PMStatus.IN_PROGRESS` sau assign `:676,679`). **KHÔNG** RepairStatus 9-state, **KHÔNG** "Assigned" (C3-split RIÊNG ≠ repair) |
| 3 | `assigned_to` | string (**required**) | Email KTV được gán (echo `technician`, `doc.assigned_to` `:672,679`) |

- **Always**: `additionalProperties:false` (closed) ở cả `AssignPmTechnicianEnvelope` (`required[success,data]`, `success.enum[true]`, `data = $ref AssignPmTechnicianResponse`) lẫn `AssignPmTechnicianResponse` (3-key đều `required`) lẫn `AssignPmTechnicianRequest`; request `required` EXACT 2, `scheduled_date` optional.
- **Always**: path vào `_MVP_BUSINESS_PATHS` **VÀ** `_MVP_ACTION_ENVELOPE` (map `→ #/components/schemas/AssignPmTechnicianEnvelope`) ⇒ 401/403 symmetry set **tự +1** (test so SET).
- **Never**: KHÔNG reuse repair `AssignTechnicianResponse`/`*ActionResponse` — **C3-split** (`status` enum domain riêng: PMStatus ≠ RepairStatus; value "In Progress" ≠ "Assigned"). KHÔNG copy optional `priority` của repair (PM dùng `scheduled_date`). KHÔNG đưa `scheduled_date` vào `required`. KHÔNG bịa status-line 404/409/422 (xem dưới).

**403 = SINGLE-SHAPE `Forbidden`:**
- *dispatcher-403* (guest/no-token) trip TRƯỚC `handle()` → HTTP-403 THẬT (`FrappeRawError`) ⇒ slot `403` = `$ref #/components/responses/Forbidden`.
- *in-handler cap-403* (`rbac.require("pm.write")` @`api/imm08.py:49` thiếu quyền) → lỗi nghiệp vụ **HTTP-200 + Error envelope** ⇒ đã **PHỦ bởi nhánh `Error` trong 200-oneOf**, KHÔNG nhân đôi shape ở slot 403. Mirror `submitPmResult`/`assignTechnician`/`startRepair` — **KHÔNG** dual-403.
- *Lỗi nghiệp vụ in-handler*: WO∄ `IMM08_WO_NOT_FOUND` @`services/imm08.py:659` (→ `code=NOT_FOUND http_status=404` `messages.py:561`) + `status ∉ {Open, Overdue}` `IMM08_BAD_STATE` @`:661` (→ `code=CONFLICT http_status=409` `messages.py:582`) + asset/`pm_schedule` đã xóa `ServiceError(VALIDATION)` @`:663-671` (→ `code=VALIDATION_ERROR http_status=422`) ARRIVE HTTP-200 + `Error` body (quirk §5, KHÔNG status-line) → gom vào nhánh `Error` 200-oneOf; route `body.http_status` ∈ bounded enum `{400,401,403,404,409,413,422,429,500}` (R11, **enum ĐÃ ⊇ {404,409,422} KHÔNG đổi**).

#### ADR-IMM08-MOB-01 — `assignPmTechnician` VERB-FLIP-THIS-ROUND + `AssignPmTechnicianResponse` RIÊNG 3-key (`status`=PMStatus "In Progress", C3-split ≠ repair)

- **Status**: Accepted
- **Date**: 2026-06-28
- **Context**: `assignPmTechnician` là mắt-xích-GIỮA PM-detail còn THIẾU (action-set THIN). Handler `assign_technician` `api/imm08.py:46` còn bare `@frappe.whitelist()` (nhận GET) — **verb-parity gap R33 BỎ SÓT** (R33 flip `submit_pm_result` + 3 write-action imm11, SÓT `assign_technician`). Return THẬT 3-key `{name, status, assigned_to}` (`services/imm08.py:679`), `status`=PMStatus.IN_PROGRESS.
- **Decision**: (1) flip decorator `api/imm08.py:46` bare→`methods=['POST']` **NGAY** (1 dòng, mirror ADR-MOBILE-011) ⇒ contract POST khớp source ⇒ KHÔNG verb-divergence ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. (2) `AssignPmTechnicianResponse`/`AssignPmTechnicianEnvelope` RIÊNG closed 3-key, `status.enum`=PMStatus 7-state example "In Progress" — **C3-split RIÊNG**, KHÔNG reuse repair `AssignTechnician*` (status domain khác). requestBody `AssignPmTechnicianRequest` closed required-EXACT-2 + optional `scheduled_date`, content json-only INLINE.
- **Alternatives bác**: (a) reuse repair `AssignTechnicianResponse` → codegen sinh `status.enum`=RepairStatus 9-state SAI + example "Assigned" SAI domain; (b) copy optional `priority` repair → bịa field không có ở source (PM dùng `scheduled_date`); (c) đẩy verb-flip→backlog + tái-mở `_PARITY_VERB_ALLOWLIST` → đi ngược R33 closure (flip 1 dòng rẻ hơn).
- **Consequences**: +1 schema-pair (`AssignPmTechnicianResponse`/`AssignPmTechnicianEnvelope`) + 1 request-schema + path 44. **⚠️ ĐỤNG 1 dòng `api/imm08.py:46`** (verb-flip) ⇒ shift runtime get/post stat (get 234→233 / post 254→255) → **re-baseline @source** `test_oas_d12`/`d17` (KHÔNG tin tuyệt đối số acceptance). Nhất quán ADR-MOBILE-012 + C3-split family. Sau flip cần USER reload gunicorn `--preload` (LIVE reject GET 405) — guard in-process KHÔNG cần. KHÔNG migrate/commit (HARD-STOP USER).

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) flip `api/imm08.py:46` bare→`@frappe.whitelist(methods=['POST'])` (ĐÚNG 1 dòng; signature/body/`rbac.require('pm.write')` UNCHANGED). (2) YAML `43 → 44` path / `44` operationId (`assignPmTechnician` mới, UNIQUE camelCase **≠** repair `assignTechnician`, tag `work-order`, summary `[MVP-4] PM dispatch Open/Overdue→In Progress`, 0 dangling `$ref`, `info.version` GIỮ `0.1.0-skeleton`, `safe_load` OK). (3) Guard XANH @source (`bench --site miyano run-tests`): `test_mobile_oas` `_EXPECTED_TEST_COUNT` **408 → 418** (+`TestMobileAssignPmTechnicianContract a..j`, gồm TC-f assert `status` enum==PMStatus ≠ repair `AssignTechnicianResponse` (C3-split) + TC-i live-signature parity `{name,technician,scheduled_date}` + TC-j git-diff-1-dòng + `_PARITY_VERB_ALLOWLIST`==set()); re-baseline `test_oas_d12` (`_BASELINE_GET 234→233`) + `test_oas_d17` (`get_count 234→233`/`post_count 254→255`) + re-verify ALL 13 `test_oas_*`; `test_imm08` +BE-unit (`assign_technician` sinh Lifecycle Event asset→Under Maintenance `:678`); `test_mobile_docset` (path 43→44, reconcile `_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL`/`_GUARD_SUITE_EXPECTED`) + `test_mobile_security_gate` (no-regress). (4) RED-before/GREEN-after chứng minh cho MỌI TC mới. Live HTTP cần USER reload (`--preload`) — KHÔNG curl-verify LIVE (LL-DEPLOY-07; KHÔNG curl IP 192.168.10.101). Working-tree để USER review.

### 0.1.2. Write-action binding — `reportMajorFailure` (PM→CM ESCALATION, đóng nút "Báo lỗi nghiêm trọng" PM-detail)

> **Bối cảnh (dead-end escalation đóng)**: KTV/Workshop Head mở `getPmWorkOrder` detail thấy thiết bị **hỏng nặng** trong lúc PM → cần **dừng PM + leo thang sang CM khẩn + đặt asset Out of Service** ngay tại màn (KHÔNG quay về web). Thiếu path này ⇒ nút "Báo lỗi nghiêm trọng (→ CM)" trên `PMWorkOrderDetailView` dead-end. **KHÁC** `assignPmTechnician` (§0.1.1, DISPATCH) / `addMeasurement` (IMM-11) / `occurred_datetime` (IMM-12 field). Đây là **escalation cross-module** PM(IMM-08)→CM(IMM-09)+Incident(IMM-12).

| Mục | Giá trị |
|---|---|
| Mobile operationId | `reportMajorFailure` (path 45/45, mới — UNIQUE camelCase), tag `work-order`, `[MVP-4]` |
| HTTP method / path | `POST /api/method/assetcore.api.imm08.report_major_failure` — **CHỈ key `post` SAU flip** (write KHÔNG idempotent: **mỗi call tạo 1 CM WO + asset OOS** — KHÔNG GET) |
| Summary | `[MVP-4] Báo lỗi nghiêm trọng PM → CM khẩn + Asset Out of Service` |
| Handler | `api/imm08.py:74` `report_major_failure(pm_wo_name, failure_description)` → `rbac.require("pm.write")` (`:77`) → `handle(svc.report_major_failure, pm_wo_name, failure_description=failure_description)` |
| **⚡ VERB-FLIP-THIS-ROUND** | decorator `api/imm08.py:74` flip **bare `@frappe.whitelist()` → `@frappe.whitelist(methods=['POST'])`**. Đóng **verb-parity gap** còn sót (sibling `assignPmTechnician` ADR-IMM08-MOB-01). Sau flip POST-only ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. ⚠️ **Doc đi-trước-code**: §0 catalog row #5 + §5 đã khai POST từ lâu |
| **🐞 SIGNATURE-FIX-THIS-ROUND** | handler cũ parse `failed_item_indexes` + truyền `failed_item_indexes=failed` vào service → service signature `(pm_wo_name, *, failure_description)` KHÔNG nhận ⇒ **`TypeError` → HTTP-500** mỗi call. Sửa: **DROP** param + parse + pass-through (align handler↔service). Request-contract đồng bộ DROP field (`additionalProperties:false`) |
| Cap | `pm.write` (in-handler `rbac.require` @`api/imm08.py:77`) |
| Lifecycle | ESCALATION — PM WO `status=PMStatus.HALTED_MAJOR` (`:749`) → `_transition_asset(... AssetStatus.OUT_OF_SERVICE ...)` (`:750` — asset → "Out of Service" + **sinh Lifecycle Event audit**) → `RepairRepo.create({failure_description, repair_type:"Breakdown", priority:"Emergency", source_pm_wo})` (`:752-762`, **CM WO khẩn**) → Incident IMM-12 best-effort → Email khẩn |
| requestBody | **INLINE** (path-level), content **`application/json` ONLY** (KHÔNG oneOf json+form) `$ref ReportMajorFailureRequest`; `required:true` |
| Response 200 | `oneOf [ReportMajorFailureEnvelope, Error]` Ở TẦNG response-content-schema (route-by-VALUE `body.success`, **0 discriminator** — pattern C6/C7); cả 2 nhánh `additionalProperties:false` + disjoint required-set |
| Status codes | 200 / 401 (`Unauthorized401`) / 403 **SINGLE-SHAPE** `Forbidden` |

**`ReportMajorFailureRequest` — closed, required EXACT 2 (GROUNDED signature @`api/imm08.py:74` SAU fix + `services/imm08.py:744`):**

| # | Field | type | Required? | Ghi chú |
|---|---|---|---|---|
| 1 | `pm_wo_name` | string | ✓ required | PK PM Work Order (positional thứ nhất, KHÔNG default) |
| 2 | `failure_description` | string | ✓ required | Mô tả lỗi nặng (positional thứ hai, KHÔNG default — đi vào `technician_notes` CM WO `:758` + email/incident) |

> **DROP `failed_item_indexes`**: KHÔNG có ở service signature; handler cũ pass-through gây `TypeError`/500. Đã loại khỏi request closed-set + handler.

**`ReportMajorFailureResponse` — RIÊNG, closed EXACT 4-key (GROUNDED return @`services/imm08.py:792-797`):**

| # | Field | type | Ghi chú |
|---|---|---|---|
| 1 | `pm_wo` | string (**required**) | PK echo input (`pm_wo_name` `:793`) |
| 2 | `new_status` | string (**required**) | `enum` = **PMStatus** 7-state (en-dash byte-khớp `services/imm08.py:43-50`), `example: "Halted–Major Failure"` (`PMStatus.HALTED_MAJOR` `:49,794`) |
| 3 | `cm_wo_created` | string (**required**) | PK CM WO (Asset Repair) khẩn vừa tạo (`cm_wo.name` `:795`) |
| 4 | `asset_status` | string (**required**) | `example: "Out of Service"` (`AssetStatus.OUT_OF_SERVICE` `:796`) |

- **Always**: `additionalProperties:false` (closed) ở cả `ReportMajorFailureEnvelope` (`required[success,data]`, `success.enum[true]`, `data = $ref ReportMajorFailureResponse`) lẫn `ReportMajorFailureResponse` (4-key đều `required`) lẫn `ReportMajorFailureRequest` (2-key đều `required`).
- **Always**: path vào `_MVP_BUSINESS_PATHS` **VÀ** `_MVP_ACTION_ENVELOPE` (map `→ #/components/schemas/ReportMajorFailureEnvelope`) ⇒ 401/403 symmetry set **tự +1** (test so SET).
- **Never**: KHÔNG đưa `failed_item_indexes` vào request (service KHÔNG nhận). KHÔNG bịa status-line 404 (WO∄ → HTTP-200 + Error). KHÔNG reuse repair envelope (4-key PM-domain RIÊNG).

**403 = SINGLE-SHAPE `Forbidden`:**
- *dispatcher-403* (guest/no-token) trip TRƯỚC `handle()` → HTTP-403 THẬT ⇒ slot `403` = `$ref #/components/responses/Forbidden`.
- *in-handler cap-403* (`rbac.require("pm.write")` @`api/imm08.py:77`) → HTTP-200 + Error envelope ⇒ đã **PHỦ bởi nhánh `Error` trong 200-oneOf**, KHÔNG nhân đôi shape.
- *Lỗi nghiệp vụ in-handler*: WO∄ `IMM08_WO_NOT_FOUND` @`services/imm08.py:747` (→ `code=NOT_FOUND http_status=404`) ARRIVE HTTP-200 + `Error` body (quirk §5) → nhánh `Error` 200-oneOf; `body.http_status` ∈ bounded enum R11 (**⊇ {404} KHÔNG đổi**).

#### ADR-IMM08-MOB-02 — `reportMajorFailure` VERB-FLIP + SIGNATURE-FIX (DROP `failed_item_indexes`) + `ReportMajorFailureResponse` RIÊNG 4-key

- **Status**: Accepted
- **Date**: 2026-06-28
- **Context**: `reportMajorFailure` (escalation PM→CM) là action-set THIN còn THIẾU trên PM-detail. Handler `report_major_failure` `api/imm08.py:74` (a) còn bare `@frappe.whitelist()` (nhận GET) và (b) **parse + truyền `failed_item_indexes=` vào service** trong khi service signature `(pm_wo_name, *, failure_description)` (`services/imm08.py:744`) **KHÔNG nhận** ⇒ `TypeError` → HTTP-500 mỗi call (lỗi thiết-kế-gốc, RED-before). Return THẬT 4-key `{pm_wo, new_status, cm_wo_created, asset_status}` (`:792-797`).
- **Decision**: (1) flip decorator `api/imm08.py:74` bare→`methods=['POST']` (write KHÔNG idempotent: tạo 1 CM WO + asset OOS) ⇒ POST-only @source ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. (2) **DROP `failed_item_indexes`** khỏi handler (param + `parse_json` + pass-through) → align handler↔service signature ⇒ hết `TypeError`/500. (3) `ReportMajorFailureRequest` closed required-EXACT-2 `[pm_wo_name, failure_description]` + `ReportMajorFailureResponse`/`Envelope` RIÊNG closed 4-key `new_status.enum`=PMStatus example "Halted–Major Failure", `asset_status` example "Out of Service".
- **Alternatives bác**: (a) giữ `failed_item_indexes` ở request "để FE log" + sửa service nhận thêm → bịa field không-dùng + mở rộng signature service không cần thiết (service+§200+web-FE đều bỏ qua); (b) bọc try/except nuốt `TypeError` ở handler → che lỗi thiết kế, vẫn 500-prone; (c) đẩy verb-flip→backlog → đi ngược verb-parity closure.
- **Consequences**: +1 schema-pair (`ReportMajorFailureResponse`/`Envelope`) + 1 request-schema + path 45. **⚠️ ĐỤNG `api/imm08.py:74-83`** (verb-flip 1 dòng + drop 6 dòng param/parse/pass) ⇒ shift runtime get/post stat (1 GET→POST) → **re-baseline @source** `test_oas_d12`/`d15`/`d17` bằng `bench execute generate_spec` (KHÔNG tin số học). Sau flip cần USER reload gunicorn `--preload` (LIVE reject GET 405). KHÔNG migrate/commit (HARD-STOP USER).

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) flip `api/imm08.py:74` bare→`@frappe.whitelist(methods=['POST'])` + DROP `failed_item_indexes` (handler signature → `(pm_wo_name, failure_description)`; bỏ `parse_json` + bỏ kwarg pass-through; `rbac.require('pm.write')` UNCHANGED). (2) YAML `44 → 45` path / `45` operationId (`reportMajorFailure` mới UNIQUE camelCase, tag `work-order`, `[MVP-4]`, 0 dangling `$ref`, `info.version` GIỮ `0.1.0-skeleton`); `ReportMajorFailureRequest` closed required-EXACT-2 + `ReportMajorFailureResponse` closed 4-key + `ReportMajorFailureEnvelope`; 200 = `oneOf [ReportMajorFailureEnvelope, Error]` closed 0-discr; slot {200,401,403}; `Error.http_status ⊇ {404}` (KHÔNG đổi). (3) Guard XANH @source: `test_mobile_oas` `_EXPECTED_TEST_COUNT` += class `TestMobileReportMajorFailureContract` + path-count 44→45; **re-baseline @source** `test_oas_d12/d15/d17` bằng `bench execute generate_spec` (re-read get/post — KHÔNG tin số học); `test_imm08` +BE-unit happy-path (200 envelope 4-key, RED-before do `TypeError`) + missing-WO 404; `test_mobile_docset` reconcile. (4) RED-before/GREEN-after cho MỌI TC mới. Live HTTP cần USER reload (`--preload`). Working-tree để USER review.

### 0.1.3. Write-action binding — `reschedulePm` (PM RESCHEDULE thiết-bị-bận, **ĐÓNG NỐT** action-set `PMWorkOrderDetailView` 45→46)

> **Bối cảnh (mắt-xích CUỐI đóng action-set)**: Workshop Head/KTV mở `getPmWorkOrder` detail thấy **thiết bị đang dùng** (cấp cứu/ca mổ) đúng ngày PM → cần **hoãn lịch** + ghi lý do ngay tại màn (KHÔNG quay về web). Nút "Hoãn lịch (thiết bị bận)" trên `PMWorkOrderDetailView` là **action CUỐI** của action-set THIN — sau path này action-set `{createPmWorkOrder ✅ → assignPmTechnician ✅(§0.1.1) → submitPmResult ✅ → reportMajorFailure ✅(§0.1.2) → reschedulePm (ĐÓNG NỐT round này)}` đầy đủ, KHÔNG còn nút dead-end. **KHÁC** `assignPmTechnician` (DISPATCH §0.1.1) / `reportMajorFailure` (ESCALATION §0.1.2): đây là **RESCHEDULE cùng-domain PM** (status → `Pending–Device Busy`, KHÔNG cross-module).

| Mục | Giá trị |
|---|---|
| Mobile operationId | `reschedulePm` (path 46/46, mới — UNIQUE camelCase), tag `work-order`, `[MVP-4]` |
| HTTP method / path | `POST /api/method/assetcore.api.imm08.reschedule_pm` — **CHỈ key `post`** (write KHÔNG idempotent: mỗi call đổi `due_date` + set `Pending–Device Busy` + append `technician_notes` — KHÔNG GET) |
| Summary | `[MVP-4] Hoãn lịch PM (thiết bị đang dùng) → Pending–Device Busy` |
| Handler | `api/imm08.py:86` `reschedule_pm(name, new_date, reason)` → `rbac.require("pm.reschedule")` (`:88`) → `handle(svc.reschedule, name, new_date=new_date, reason=reason)` (`:89`) |
| **🟢 ATOMIC-THIS-ROUND (KHÔNG verb-flip, KHÔNG signature-fix)** | Handler `api/imm08.py:86` **ĐÃ** `@frappe.whitelist(methods=['POST'])` (đã flip từ round trước) **VÀ** signature `reschedule_pm(name, new_date, reason)` **ĐÃ** khớp service `reschedule(name, *, new_date, reason)` (`services/imm08.py:807`) ⇒ **KHÔNG đụng `api`/`service` 1 dòng nào** — round PURE-YAML+test. `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. ⚠️ **Doc đi-trước-code**: §0 catalog row #6 + §8 (`:729`) đã khai POST + response shape 4-key từ lâu; round này = đưa contract mobile khớp source-intent ĐÃ-CÓ. |
| Cap | `pm.reschedule` (in-handler `rbac.require` @`api/imm08.py:88`) — map `("PM Work Order","write")` `services/shared/rbac.py:94`. **KHÁC** sibling `pm.write` (assignPmTechnician/reportMajorFailure) — cap-name riêng cho reschedule |
| Lifecycle | RESCHEDULE (cùng-domain) — guard `len(reason.strip()) ≥ 5` (`services/imm08.py:808`); `wo.due_date = new_date` (`:816`); `wo.status = PMStatus.PENDING_BUSY` (`:817`); append `wo.technician_notes` `[Hoãn lịch {old}→{new}]: {reason}` (`:818`); **nếu** WO đang `In Progress` → `_transition_asset(wo.asset_ref, AssetStatus.ACTIVE, wo.name)` (`:821-822` — asset khôi phục "Active" + **sinh Lifecycle Event audit**) |
| requestBody | **INLINE** (path-level), content **`application/json` ONLY** (KHÔNG oneOf json+form) `$ref ReschedulePmRequest`; `required:true` |
| Response 200 | `oneOf [ReschedulePmEnvelope, Error]` Ở TẦNG response-content-schema (route-by-VALUE `body.success`, **0 discriminator** — pattern C6/C7); cả 2 nhánh `additionalProperties:false` + disjoint required-set |
| Status codes | 200 / 401 (`Unauthorized401`) / 403 **SINGLE-SHAPE** `Forbidden` |

**`ReschedulePmRequest` — closed, required EXACT 3 (GROUNDED signature @`api/imm08.py:87`):**

| # | Field | type | Required? | Ghi chú |
|---|---|---|---|---|
| 1 | `name` | string | ✓ required | PK PM Work Order (positional thứ nhất, vd PM-WO-2026-00004) |
| 2 | `new_date` | string, **`format: date`** | ✓ required | Ngày dời tới (YYYY-MM-DD) — `wo.due_date = new_date` (`services/imm08.py:816`) |
| 3 | `reason` | string, **`minLength: 5`** | ✓ required | Lý do hoãn — **mirror guard service** `len(reason.strip()) < 5 → VALIDATION 422` (`services/imm08.py:808-810`, VR-08-09); đi vào `technician_notes` (`:818`) |

> **`reason.minLength: 5`**: codegen sinh client-side guard ≥5 ký tự khớp service-guard (`services/imm08.py:808`) ⇒ giảm round-trip 422. `new_date.format: date` ⇒ codegen sinh kiểu Date.

**`ReschedulePmResponse` — RIÊNG, closed EXACT 4-key (GROUNDED return @`services/imm08.py:823`):**

| # | Field | type | Ghi chú |
|---|---|---|---|
| 1 | `name` | string (**required**) | PK echo input (`wo.name` `:823`) |
| 2 | `old_date` | string (**required**) | `due_date` TRƯỚC hoãn — `str(wo.due_date)` chụp trước khi ghi đè (`:815,823`) |
| 3 | `new_date` | string (**required**) | `due_date` SAU hoãn — echo input (`:816,823`) |
| 4 | `status` | string (**required**) | `enum` = **PMStatus** 7-state `[Open, In Progress, Completed, Overdue, Cancelled, "Halted–Major Failure", "Pending–Device Busy"]` (`services/imm08.py:43-50` — en-dash byte-khớp), `example: "Pending–Device Busy"` (`PMStatus.PENDING_BUSY` `:50,817` — **en-dash U+2013, KHÔNG hyphen-minus U+002D**) |

- **Always**: `additionalProperties:false` (closed) ở cả `ReschedulePmEnvelope` (`required[success,data]`, `success.enum[true]`, `data = $ref ReschedulePmResponse`) lẫn `ReschedulePmResponse` (4-key đều `required`) lẫn `ReschedulePmRequest` (3-key đều `required`, `reason.minLength:5`, `new_date.format:date`).
- **Always**: path vào `_MVP_BUSINESS_PATHS` **VÀ** `_MVP_ACTION_ENVELOPE` (map `→ #/components/schemas/ReschedulePmEnvelope`) ⇒ 401/403 symmetry set **tự +1** (test so SET).
- **Never**: KHÔNG verb-flip / KHÔNG đụng `api` (đã POST + signature khớp). KHÔNG đổi default `ServiceError.__init__` (`errors.py:36`) — các VALIDATION raise khác trong `imm08` GIỮ 400 (regression-fence; blast-radius = 1 raise tại `:809`). KHÔNG reuse `AssignPmTechnician*`/`ReportMajorFailure*` envelope (4-key `{name,old_date,new_date,status}` là shape date-pair RIÊNG). KHÔNG bịa status-line 404/422 (WO∄/reason<5 → HTTP-200 + Error). KHÔNG đưa `reason.minLength`/`new_date.format` ra ngoài request.
- **Always (vòng-2 RECONCILE — đóng OPEN ISSUE 400-vs-422)**: `reason`<5 → HTTP `422` (KHÔNG 400). Đúng-1-dòng tại `services/imm08.py:809` đổi raw `ServiceError(ErrorCode.VALIDATION, msg)` → helper `validation(msg)` (`errors.py:62` → `http_status=422`) HOẶC kwarg `http_status=422`. Honor contract đã công bố + canonical `_HTTP_FOR_CODE[VALIDATION]=422` (`utils/response.py:61`). LIVE-effect ⇒ USER reload gunicorn `--preload` (HARD-STOP). Xem ADR-IMM08-MOB-03-R2 dưới.

**403 = SINGLE-SHAPE `Forbidden`:**
- *dispatcher-403* (guest/no-token) trip TRƯỚC `handle()` → HTTP-403 THẬT ⇒ slot `403` = `$ref #/components/responses/Forbidden`.
- *in-handler cap-403* (`rbac.require("pm.reschedule")` @`api/imm08.py:88` thiếu quyền) → lỗi nghiệp vụ **HTTP-200 + Error envelope** ⇒ đã **PHỦ bởi nhánh `Error` trong 200-oneOf**, KHÔNG nhân đôi shape.
- *Lỗi nghiệp vụ in-handler* (**2 guard** — `Error.http_status ⊇ {404,422}`): (a) `reason` < 5 ký tự → `validation(...)` helper @`services/imm08.py:809` (`services/shared/errors.py:62` → `ServiceError(VALIDATION, ..., http_status=422)`) (→ `code=VALIDATION http_status=422`, canonical `_HTTP_FOR_CODE[VALIDATION]=422` `utils/response.py:61`); (b) WO∄ → `nthrow(MSG.IMM08_WO_NOT_FOUND, name=name)` @`:813` (→ `code=NOT_FOUND http_status=404`). Cả 2 ARRIVE HTTP-200 + `Error` body (quirk §5, KHÔNG status-line) → gom vào nhánh `Error` 200-oneOf; route `body.http_status` ∈ bounded enum R11 `{400,401,403,404,409,413,422,429,500}` (**ĐÃ ⊇ {404,422} — KHÔNG đổi enum/Error schema**).

#### ADR-IMM08-MOB-03 — `reschedulePm` ATOMIC-wire (KHÔNG verb-flip) + `ReschedulePmResponse` RIÊNG 4-key date-pair + ĐÓNG NỐT action-set `PMWorkOrderDetailView`

- **Status**: Accepted
- **Date**: 2026-06-28
- **Context**: `reschedulePm` là action **CUỐI** của action-set THIN `PMWorkOrderDetailView` (đóng nốt 45→46). KHÁC §0.1.1 (assignPmTechnician — VERB-FLIP) + §0.1.2 (reportMajorFailure — VERB-FLIP + SIGNATURE-FIX): handler `reschedule_pm` `api/imm08.py:86` **ĐÃ** `@frappe.whitelist(methods=['POST'])` **VÀ** signature `(name, new_date, reason)` **ĐÃ** khớp service `reschedule(name, *, new_date, reason)` `services/imm08.py:807` ⇒ **KHÔNG có gap source** → round **ATOMIC** (chỉ +YAML +test, KHÔNG đụng `api`/`service`). Return THẬT 4-key `{name, old_date, new_date, status}` `:823`, `status`=PMStatus.PENDING_BUSY (`:50,817` — en-dash). Cap riêng `pm.reschedule` (`:88`, KHÁC sibling `pm.write`).
- **Decision**: (1) +1 path `POST /api/method/assetcore.api.imm08.reschedule_pm` opId `reschedulePm` UNIQUE camelCase, tag `work-order`, `[MVP-4]`. `ReschedulePmRequest` closed required-EXACT-3 `[name, new_date, reason]`, `reason.minLength:5` (mirror guard `:808`), `new_date.format:date`, content json-only INLINE. `ReschedulePmResponse`/`Envelope` RIÊNG closed 4-key `{name, old_date, new_date, status}`, `status.enum`=PMStatus 7-state example `"Pending–Device Busy"` (en-dash byte-khớp). 200 = `oneOf [ReschedulePmEnvelope, Error]` closed 0-discr; slot `{200,401,403}`. (2) **KHÔNG verb-flip, KHÔNG signature/service/api edit** — ATOMIC; `_PARITY_VERB_ALLOWLIST` GIỮ `set()`.
- **Alternatives bác**: (a) reuse `AssignPmTechnician*`/`ReportMajorFailure*` envelope → return 4-key date-pair `{name,old_date,new_date,status}` là shape DUY NHẤT (old/new date pair — KHÔNG envelope nào khác có) → codegen sai field; (b) `reason` KHÔNG `minLength` → codegen mất guard ≥5 ⇒ FE đẩy reason rỗng → service trả VALIDATION 422 round-trip thừa; (c) `status` literal-single `enum:[Pending–Device Busy]` → return `wo.status` field PMStatus, khai đủ 7-state forward-safe mirror sibling §0.1.1/§0.1.2; (d) mở status-line 404/422 → 2 guard arrive HTTP-200 + Error (route `body.http_status`), KHÔNG status-line (quirk §5) — slot GIỮ `{200,401,403}`.
- **Consequences**: +1 schema-pair (`ReschedulePmResponse`/`Envelope`) + 1 request-schema + path 46 → **action-set `PMWorkOrderDetailView` ĐÓNG NỐT** (0 nút dead-end). `info.version` GIỮ `0.1.0-skeleton`. 0 dangling `$ref`. **🟢 ATOMIC — KHÔNG đụng `api/imm08.py`/`services/imm08.py`** ⇒ `generate_spec` get/post stat **UNCHANGED** *(⚠️ điểm "KHÔNG đụng service" LẬT bởi `ADR-IMM08-MOB-03-R2` vòng-2: đụng `services/imm08.py:809` ĐÚNG 1 dòng để honor 422 — `generate_spec` vẫn UNCHANGED vì http_status là giá-trị-runtime)* ⇒ `test_oas_d12/d15/d17` **RE-VERIFY @source** (re-run `bench execute generate_spec`, kỳ vọng count KHÔNG đổi → **KHÔNG re-baseline** trừ khi phát hiện drift) — **KHÁC R36** (R36 verb-flip shift 1 GET→POST nên phải re-baseline). `Error.http_status` ĐÃ ⊇ `{404,422}` trong bounded enum R11 → **KHÔNG đổi `Error` schema**. KHÔNG migrate/commit (HARD-STOP USER).

#### ADR-IMM08-MOB-03-R2 — RECONCILE `reschedulePm` VALIDATION `400 → 422` (honor published contract)

- **Status**: Accepted — addendum cho ADR-IMM08-MOB-03 (KHÔNG supersede phần schema/path/envelope; CHỈ lật điểm "ATOMIC KHÔNG đụng service" + chốt http_status).
- **Date**: 2026-06-28 (vòng 2)
- **Context**: R37 (ADR-MOB-03) khai `reason`<5 → **422** NHƯNG đồng thời chốt "ATOMIC = KHÔNG đụng service" — **mâu thuẫn**: service `:809` raise raw `ServiceError(ErrorCode.VALIDATION, msg)` → trúng default `http_status=400` (`errors.py:36`), KHÔNG 422. BE-unit trung thực assert **400** + flag OPEN ISSUE cho [BA]/[QA]. Doc đúng (422), code lệch (400).
- **Decision**: **BE honor contract → 422.** Đúng-1-dòng tại `services/imm08.py:809`: raw `ServiceError(ErrorCode.VALIDATION, msg)` → helper `validation(msg)` (`errors.py:62` = `ServiceError(VALIDATION, msg, http_status=422)`) HOẶC kwarg `http_status=422`. Grounding: canonical SSoT `_HTTP_FOR_CODE[ErrorCode.VALIDATION]=422` (`utils/response.py:61`) — 422 là giá trị canonical-đúng cho `VALIDATION`; default 400 của `ServiceError.__init__` là legacy KHÔNG tra canonical map.
- **Alternatives bác**: (a) sửa doc→400 (hạ contract đã công bố + nghịch canonical SSoT) — Loại; (b) đổi default `ServiceError.__init__`→422 (clean nhưng blast-radius = MỌI raw VALIDATION raise toàn repo, nhiều test assert 400) — Loại (regression-bom); (c) giữ nguyên 400, flag tiếp — Loại (open-issue không đóng).
- **Boundaries**: **blast-radius = 1 raise** (`:809`). Các VALIDATION raise khác trong `imm08` (`:664,:668,:709,:716,:830,:842,:1054,:1094,:1167,...`) GIỮ **400** nguyên trạng (regression-fence). KHÔNG đổi `errors.py:36`. Mirror tiền lệ IMM-09 (`test_imm09.py:1683-1685`: cặp code×status ngoại-lệ-có-chủ-đích, guard chống "fix cho khớp _HTTP_FOR_CODE"). *(Reconcile toàn-cục VALIDATION→422 cho mọi endpoint = `[ROADMAP]`, KHÔNG round này.)*
- **Consequences**: (1) `services/imm08.py:809` +helper `validation()` (LIVE-effect → USER reload `--preload`, HARD-STOP). (2) `test_imm08.py` `test_reschedule_reason_too_short_validation_422_envelope` assert `http_status` `400 → 422` + comment "DRIFT/SOURCE-TRUTH 400" → "RECONCILED 422 (canonical `_HTTP_FOR_CODE`)". (3) OpenAPI `assetcore-mobile.openapi.yaml` **UNCHANGED** — 422 ĐÃ ∈ `Error.http_status` bounded-enum (line 597); `generate_spec` get/post/total **UNCHANGED** (http_status là giá-trị-runtime, KHÔNG ảnh hưởng static spec) ⇒ `test_oas_d12/d15/d17` re-verify @source GREEN, **KHÔNG re-baseline**. (4) Đóng OPEN ISSUE Round-1.

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) **Đụng `service` ĐÚNG 1 dòng** (`services/imm08.py:809` raw `ServiceError(ErrorCode.VALIDATION)` → `validation()` helper =422; **KHÔNG đụng `api`**; KHÔNG verb-flip; KHÔNG đổi `errors.py:36` default). (2) YAML `45 → 46` path / `46` operationId (`reschedulePm` mới UNIQUE camelCase, tag `work-order`, `[MVP-4]`, summary `[MVP-4] Hoãn lịch PM (thiết bị đang dùng) → Pending–Device Busy`, 0 dangling `$ref`, `info.version` GIỮ `0.1.0-skeleton`, `safe_load` OK); parity grep `^\s{2}/`==46 và `operationId:`==46. `ReschedulePmRequest` closed required-EXACT-3 `[name,new_date,reason]` (`reason.minLength:5`, `new_date.format:date`, `additionalProperties:false`) + `ReschedulePmResponse` closed 4-key `{name,old_date,new_date,status}` (`status.example` BYTE-MATCH `'Pending–Device Busy'` en-dash U+2013) + `ReschedulePmEnvelope`; 200 = `oneOf [ReschedulePmEnvelope, Error]` closed 0-discr; slot `{200,401,403}` parity với `assignPmTechnician`/`reportMajorFailure`; `Error.http_status ⊇ {404,422}` (ĐÃ có — KHÔNG đổi). (3) **@source `generate_spec` (KHÔNG tin số học)**: confirm `reschedule_pm` POST-only; vì ATOMIC ⇒ get/post stat KHÔNG đổi ⇒ `test_oas_d12/d15/d17` **re-verify** (KHÔNG re-baseline trừ drift). `test_mobile_oas` GREEN + class `TestMobileReschedulePmContract` (≥8 TC a..h: path/opId UNIQUE · Request closed req-3 + reason.minLength:5 + new_date.format:date · Response closed 4-key · status.example en-dash byte-match · 200 oneOf[Env,Error] 0-discr · slot{200,401,403} · Error.http_status⊇{404,422} · live-signature parity `{name,new_date,reason}` @`api/imm08.py:87`) + self-count meta-guard bump (`_EXPECTED_TEST_COUNT`, path-count 45→46). (4) `test_mobile_docset` GREEN + **ADR-MOBILE-014** đăng ký `README` (`TC-MOB-DOC` parity glob). `test_imm08` GREEN + 3 BE-unit (happy-path 4-key envelope · reason<5 → VALIDATION 422 · missing-WO → NOT_FOUND 404). (5) RED-before/GREEN-after cho MỌI TC mới. Live HTTP cần USER reload (`--preload`) — KHÔNG curl-verify LIVE (LL-DEPLOY-07; KHÔNG curl IP 192.168.10.101). Working-tree để USER review.

---

## 1. Quy ước chung

### 1.1. Response success — format chuẩn AssetCore

```jsonc
{
  "success": true,
  "data": <payload — object / array / null>
}
```

FE đọc qua `response.data.data` (Frappe axios wrapper strip outer `message`).

**HTTP status:** Frappe luôn trả **HTTP 200**. Phân biệt success/error qua field `success` trong body. HTTP ≠ 200 chỉ khi: 401 (session hết hạn), 403 (CSRF/role Frappe), 500 (unhandled).

### 1.2. Response error — format chuẩn

```jsonc
{
  "success": false,
  "error": "Mô tả lỗi tiếng Việt",
  "code": "NOT_FOUND",
  "fields": { "field_name": "lỗi inline" }  // optional
}
```

CẤM trả raw traceback / SQL error.

### 1.3. Error code catalog

| Code | Khi nào | message_code (xem §11) |
|---|---|---|
| `NOT_FOUND` | Record không tồn tại | `IMM08-WO-NOT-FOUND` / `IMM08-SCHEDULE-NOT-FOUND` / `IMM08-TEMPLATE-NOT-FOUND` |
| `FORBIDDEN` | Không có role phù hợp | `AUTH-403` |
| `VALIDATION` | Input validation fail | `IMM08-CHECKLIST-INCOMPLETE` / `IMM08-DURATION-REQUIRED` / `IMM08-STICKER-REQUIRED` / `IMM08-PHOTO-REQUIRED` / `IMM08-SOURCE-PM-REQUIRED` |
| `BAD_STATE` | State machine fail (vd WO đã submitted) | `IMM08-BAD-STATE` |
| `CONFLICT` | Concurrent modify / đã submit | `IMM08-ALREADY-SUBMITTED` |
| `INVALID_PARAMS` | JSON parse fail | `VAL-INVALID-PARAMS` |
| `INTERNAL` | Lỗi hệ thống | `SYS-500` |

> Từ Sprint Notification vòng 3, error envelope IMM-08 hydrate thêm `message_code`,
> `severity`, `title`, `action_hint` qua `api_handler.handle()`. Xem **§11**.

### 1.4. Mapping FE ↔ BE error code

| BE `ErrorCode` | FE `ErrorCode` |
|---|---|
| `VALIDATION` | `VALIDATION_ERROR` |
| `BAD_STATE` | `BAD_STATE` |
| `NOT_FOUND` | `NOT_FOUND` |
| `FORBIDDEN` | `FORBIDDEN` |
| `CONFLICT` | `CONFLICT` |
| `INVALID_PARAMS` | `INVALID_PARAMS` |
| `ALREADY_SUBMITTED` | `BAD_STATE` |
| `INTERNAL` | `INTERNAL_ERROR` |

### 1.5. Type definitions

```ts
// frontend/src/types/imm08.ts
export type PMStatus =
  | 'Open' | 'In Progress' | 'Pending–Device Busy'
  | 'Overdue' | 'Completed' | 'Halted–Major Failure' | 'Cancelled';

export type PMType = 'Quarterly' | 'Semi-Annual' | 'Annual' | 'Ad-hoc';

export interface PMWorkOrder {
  name: string;
  asset_ref: string;
  asset_name: string;           // denormalized
  pm_type: PMType;
  wo_type: 'Preventive' | 'Corrective';
  status: PMStatus;
  due_date: string;             // ISO date
  completion_date: string | null;
  is_late: boolean;
  assigned_to: string | null;
  overall_result: string | null;
  checklist_results: PMChecklistResult[];
  source_pm_wo: string | null;
}

export interface PMChecklistResult {
  idx: number;
  description: string;
  measurement_type: 'Pass/Fail' | 'Numeric' | 'Text';
  result: 'Pass' | 'Fail–Minor' | 'Fail–Major' | 'N/A' | null;
  measured_value: number | null;
  unit: string | null;
  notes: string | null;
  photo: string | null;
}

export interface PMDashboardStats {
  kpis: {
    // ── KHỐI THÁNG (scope = due_date ∈ [start_month, end_month] ∧ status != Cancelled) — đối-soát số học ──
    total_scheduled: number;        // WO có due_date trong tháng VÀ không-Cancelled (mẫu của compliance — INV-PM-KPI-6)
    completed_on_time: number;      // ⊆ total_scheduled, status==Completed ∧ !is_late (tử của compliance)
    overdue_in_month: number;       // ⊆ total_scheduled, status==Overdue ∧ due_date trong tháng (KHÔNG gồm Cancelled)
    pending_in_month: number;       // ⊆ total_scheduled, phần còn lại (chưa Completed-on-time, chưa Overdue); Cancelled KHÔNG rơi vào đây (INV-PM-KPI-6)
    compliance_rate_pct: number | null;  // completed_on_time / total_scheduled; total_scheduled = WO không-Cancelled trong tháng; null khi total_scheduled==0 (FE hiện '—')
    avg_days_late: number;          // trung bình ngày trễ của WO completed-late trong tháng
    // ── KHỐI TOÀN HỆ THỐNG (scope = mọi thời gian) — KHÔNG đối-soát với khối tháng ──
    overdue: number;                // = count_overdue_pm(), status==Overdue toàn thời gian (RC-10, GIỮ NGUYÊN)
  };
  trend_6months: Array<{ month: string; total: number; on_time: number; rate: number }>;
}
```

> **Population (vòng 25 — INV-PM-KPI-6):** khối tháng tính trên `scheduled` = WO `due_date ∈ tháng` **∧ `status != Cancelled`** — KHÔNG phải `len(wos)` thô. WO `Cancelled` (hủy chủ động, hết nghĩa vụ) bị LOẠI khỏi mẫu compliance + mọi bucket.
>
> **INV-PM-KPI-1 (đối-soát strip tháng):** trên cùng một payload, các field khối-tháng PHẢI hòa hợp số học:
> `total_scheduled >= completed_on_time + overdue_in_month + pending_in_month` (đẳng thức khi KHÔNG có Completed-late; có Completed-late thì WO đó là phần dôi, đã trừ qua `completed_in_month`).
> Hệ quả: `overdue_in_month <= total_scheduled` luôn đúng. `pending_in_month` được tính bằng phần dư (`total_scheduled − completed_in_month − overdue_in_month`, trong đó `completed_in_month` = TẤT CẢ Completed on-time+late) chứ KHÔNG đếm độc lập → bao trùm mọi status **không-Cancelled chưa-xong-chưa-overdue** còn lại (Open, In Progress, Pending–Device Busy, Halted–Major Failure). `Completed-late` KHÔNG vào `pending` (đã ở `completed_in_month`). `Cancelled` đã bị loại khỏi `total_scheduled` ⇒ KHÔNG rơi vào `pending_in_month`.
>
> **INV-PM-KPI-2 (overdue global bất biến — RC-10):** field `overdue` GIỮ NGUYÊN giá trị + ngữ nghĩa = `count_overdue_pm()` (status==Overdue toàn thời gian) — khớp launcher widget + drill `?overdue=1`. KHÔNG đổi tên, KHÔNG đổi nguồn.
>
> **INV-PM-KPI-3 (compliance population-consistent):** `compliance_rate_pct = round(completed_on_time / total_scheduled * 100, 1)` — CẢ tử & mẫu cùng phạm-vi-tháng VÀ cùng population không-Cancelled. Khi `total_scheduled == 0` → trả `null` (FE render '—'/N/A, KHÔNG 0% gây hiểu nhầm "không tuân thủ"). TUYỆT ĐỐI KHÔNG trộn mẫu tháng với `overdue` global.
>
> **INV-PM-KPI-6 (loại Cancelled khỏi mẫu — vòng 25):** WO `status==Cancelled` KHÔNG vào `total_scheduled`, KHÔNG vào tử/mẫu compliance, KHÔNG vào `pending_in_month`/`overdue_in_month`/`completed_on_time`. Hệ quả đo được:
> - Tháng `{1 Completed-on-time, 1 Completed-late, 1 Overdue, 1 Cancelled}` → `total_scheduled==3` (KHÔNG 4), `compliance_rate_pct==round(1/3*100,1)==33.3` (cũ sai `1/4==25.0`), `completed_on_time==1`, `overdue_in_month==1`, `pending_in_month==0`.
> - Tháng chỉ-Cancelled (vd 2 Cancelled, 0 khác) → `total_scheduled==0` ⇒ `compliance_rate_pct==null` (FE '—', KHÔNG `0.0`), `pending_in_month==0`, `overdue_in_month==0`.
> - **No-regression:** tháng KHÔNG có Cancelled → mọi KPI GIỮ NGUYÊN như trước fix (Cancelled-free path bất biến: `scheduled == wos`).
> - **`trend_6months[*].rate`** dùng CÙNG predicate loại-Cancelled (`t = số WO không-Cancelled trong tháng`) — KHÔNG lệch chuẩn so với tile compliance tháng hiện tại (1 SoT predicate).
> - **OUT-of-scope:** `Halted–Major Failure` GIỮ counted (kết cục PM không-tuân-thủ thật). `count_overdue_pm()` global + `is_late` + shape/field-name KHÔNG đổi.

### Pagination convention

```jsonc
{
  "data": [ /* items */ ],
  "pagination": { "page": 1, "page_size": 20, "total": 137, "total_pages": 7 }
}
```

---

## 2. Endpoints

### 1. list_pm_work_orders — Danh sách PM WO

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.list_pm_work_orders` |
| Role | All IMM roles |
| Idempotent | Yes |

**Request:**

| Param | Type | Required | Validation |
|---|---|---|---|
| `filters` | JSON string | ✗ | valid JSON object |
| `mine` | int `0\|1` | ✗ | default 0; `mine=1` → scope `assigned_to==session.user` (xem "filter mine" + BR-08-15 dưới) |
| `page` | int | ✗ | ≥ 1, default 1 |
| `page_size` | int | ✗ | 1–100, default 20 |

**Virtual filter keys (drill-down từ KPI — `_normalize_filters`):**

| Key | Ngữ nghĩa BE | Predicate sinh ra |
|---|---|---|
| `due_before` | **PM đến hạn (due-soon window)** — drill từ KPI `pm_due_7d` (BR-08-12) | `due_date BETWEEN [today, due_before]` (cận dưới = today, inclusive 2 biên) AND `status NOT IN [Completed, Cancelled]` → gọi SoT `due_soon_filter(due_before)`. **KHÔNG** còn dịch `due_date <= due_before` (cũ thiếu cận dưới → WO quá hạn leak vào danh sách). |
| `overdue=1` | **PM quá hạn** — drill từ KPI `pm_overdue` (BR-08-11) | `status == Overdue`. Disjoint với `due_before` (overdue có `due_date < today`; due-soon có `due_date >= today`). |

> **INVARIANT (BR-08-12):** `count(KPI pm_due_7d) == pagination.total` khi drill `?filters={"due_before":"<today+7>"}` — card == drill byte-for-byte. KPI `pm_due_next7` (`dashboard.py`) và filter này dùng CHUNG `due_soon_filter` (1 SoT). FE forward `due_before` verbatim — BE lo cận dưới, FE KHÔNG inline-compute membership. Zero contract change ngoài label chip (xem 06_Frontend_Design §3.3).

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "data": [
      {
        "name": "PM-WO-2026-00001",
        "asset_ref": "AC-ASSET-2026-0003",
        "asset_name": "Máy thở Drager Evita V500",
        "pm_type": "Quarterly",
        "wo_type": "Preventive",
        "status": "Open",
        "due_date": "2026-04-17",
        "completion_date": null,
        "assigned_to": "ktv1@bv.vn",
        "overall_result": null,
        "is_late": false,
        "source_pm_wo": null
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
  }
}
```

**Errors:** `INVALID_PARAMS` (filters JSON sai).

#### list_pm_work_orders — filter `mine` (tab "Phiếu PM của tôi", MVP-5a) ✅ SPEC (BE Bước-4)

> **Mục tiêu (A2 known-gap closure ĐỐI XỨNG):** màn mobile `MyWorkOrdersView` › tab **"Phiếu PM của tôi"** cần CHỈ PM WO gán cho chính KTV. Contract mobile (`docs/mobile/openapi/…listPmWorkOrders`) TRƯỚC vòng này CLAIM "Scope theo user (count==rows, permission-aware)" nhưng `list_pm_work_orders` KHÔNG có cơ chế scope `assigned_to` ⇒ **claim suông** (contract nói dối). Vòng này wire param `mine` để contract TRUNG THỰC. Gap "next" nêu đích danh ở [ADR-MOBILE-015](../mobile/ADR-MOBILE-015.md) §Consequences.

**Param mới:** `mine` (int `0|1`, default `0`, `in:query`) — bổ sung vào `list_pm_work_orders(filters, page, page_size)` → `list_pm_work_orders(filters, mine, page, page_size)`.

| `mine` | Hành vi | Filter áp |
|---|---|---|
| `0` / absent | **UNCHANGED** (backward-compat) — list permission-aware như cũ; web-FE `PMWorkOrderListView` KHÔNG đổi | KHÔNG inject `assigned_to` |
| `1` | **Scope assigned_to** — chỉ PM WO `assigned_to == frappe.session.user` | `f["assigned_to"] = frappe.session.user` (inject SAU `apply_vendor_scope`) |

**BR-08-15 (mine self-scope — application filter, KHÔNG phải security boundary):**
- `mine=1` áp filter `assigned_to == frappe.session.user` (giải quyết session ở **API-layer** — KHÁC IMM-12 BR-12-14 seed @service-layer; lý do: PM `filters` là JSON-blob đã `parse_json` @api `imm08.py:30`, điểm inject tự nhiên = ngay sau `apply_vendor_scope` `imm08.py:33`).
- **AND với mọi key trong `filters` blob KỂ CẢ virtual key:** inject vào `f` dict TRƯỚC khi `handle(svc.list_work_orders, f, …)` ⇒ `assigned_to` AND với `status`/`due_before`/`overdue`… (vd `mine=1&filters={"overdue":1}` = PM của tôi quá hạn — virtual `overdue` → `status==Overdue` AND `assigned_to`; `mine=1&filters={"status":"Open"}` = PM của tôi đang mở).
- **INVARIANT count==rows (INV-08-LIST):** `BaseRepository.list` (`repositories/base.py:65-71`) đếm `count_with_or(DOCTYPE, filters, or_filters)` + lấy `frappe.get_all(DOCTYPE, filters=filters)` dùng **CÙNG** `filters` dict đã có `assigned_to` ⇒ `pagination.total == len(data.data)` khi `mine=1`. `list_pm_work_orders` KHÔNG truyền `or_filters` ⇒ `count_with_or` = `frappe.db.count` thuần. KHÔNG đếm trên dict khác (chống count-vs-rows drift — memory `asset_list_count_drill_technician`).
- **Blast-radius fence ĐO ĐƯỢC:** `mine=0`/absent ⇒ `f` dict BYTE-IDENTICAL với trước vòng này (1 nhánh điều kiện `if int(mine or 0):` duy nhất @api, KHÔNG đụng `services/imm08.py`/`_normalize_filters`/repo). Test fence: PM WO assigned cho user khác VẪN xuất hiện khi `mine=0` (chứng minh `assigned_to` không bị áp ngầm).
- **Quyền (2 lớp 403 — DONE-gate spec-contract):** `list_pm_work_orders` chỉ dispatcher-403 (Guest → re-auth) + read-gating DocPerm/permission_query "PM Work Order" (`pm.read`) + `apply_vendor_scope` (vendor isolation); KHÔNG thêm in-handler cap-403. `mine=1` là filter **opt-in** chồng LÊN scope quyền (không thay quyền): KTV `pm.read` gọi `mine=1` → 200 + chỉ PM WO của mình ⇒ **KHÔNG leak** WO gán assignee khác (vì `assigned_to` tường minh).

**Boundaries:**
- **Always:** inject `assigned_to` @api-layer SAU `apply_vendor_scope` (sau vendor-isolation, trước service); giải quyết `frappe.session.user` ở API (service nhận `filters` dict thuần); `mine` int `0|1` (mirror `IncidentMine`/`overdue` — né int-vs-bool trap); contract OpenAPI + cơ-chế khớp nhau; `count`+`rows` cùng `filters` dict.
- **Never:** áp `assigned_to` khi `mine=0` (vỡ backward-compat web-FE `PMWorkOrderListView`); đếm `total` trên filters dict khác `get_all` (vỡ count==rows); thêm endpoint mới `list_my_pm_work_orders` (+1 path — vỡ "path-count UNCHANGED" 46); auto-scope mọi read theo `assigned_to` qua `permission_query_conditions` (vỡ view supervisor/QA cần thấy TẤT CẢ); đụng `services/imm08.py`/repo (blast-radius phải = 1 nhánh @api + 1 param).

#### ADR-IMM08-MOB-04: Opt-in `mine` query-param (inject @api) vs endpoint riêng vs permission auto-scope vs seed @service

- **Status**: Accepted — Date 2026-06-28. Đối-xứng `ADR-IMM12-05` (IncidentMine) + đăng-ký mobile `ADR-MOBILE-016`.
- **Context**: tab "Phiếu PM của tôi" (MVP-5a) cần self-scope `assigned_to`, NHƯNG web-FE `PMWorkOrderListView` (supervisor/QA) cần thấy mọi PM WO; contract đã claim "Scope theo user" mà thiếu cơ chế; ràng buộc "path-count UNCHANGED 46" + "count==rows". `list_pm_work_orders` nhận `filters` dạng **JSON-blob** (KHÁC `list_incidents` discrete param) → đã `parse_json` + `apply_vendor_scope` @api.
- **Decision**: thêm **1 query-param opt-in `mine`** (default 0 = cũ; 1 = filter `assigned_to==session.user`) — inject `f["assigned_to"]=frappe.session.user` @api-layer SAU `apply_vendor_scope`, ANDed vào CÙNG `filters` dict; **KHÔNG đụng service/repo**.
- **Alternatives**: (A) endpoint riêng `list_my_pm_work_orders` → +1 path (vỡ ràng buộc) + nhân đôi pagination/enrich/contract surface → loại. (B) auto-scope mọi read theo `assigned_to` qua `permission_query_conditions` → vỡ view supervisor/QA + đổi security-semantics + count-vs-rows cho persona không-self → loại. (C) seed @service-layer (giống IncidentMine `_build_incident_filters`) → KHÁC cấu trúc (PM filters là JSON-blob @api, KHÔNG discrete param) → inject @api nhỏ hơn (KHÔNG đụng service) → loại C để giữ blast-radius tối thiểu.
- **Consequences**: blast-radius = 1 nhánh `if int(mine or 0):` @api + 1 param; backward-compat tuyệt đối; codegen mobile sinh client truyền `mine=1` cho tab; KHÔNG migration DB; KHÔNG đụng `services/imm08.py`/repo. Đánh đổi: `mine` là filter ứng-dụng (KHÔNG phải hàng-rào-bảo-mật) — bảo mật read VẪN do DocPerm/permission_query (`pm.read`) + `apply_vendor_scope` đảm trách. Đối-xứng A2 còn lại: `listRepairWorkOrders` (CM, `assigned_to`) — Phase tiếp.

> **DELTA vòng này (so với bản trước):** (1) catalog row #1 + Request-table thêm param `mine`; (2) section "list_pm_work_orders — filter mine" + BR-08-15 + ADR-IMM08-MOB-04 mới; (3) đồng bộ contract mobile (OpenAPI `WorkOrderMine`, `04-api-contract §6.2/§8.4`, ADR-MOBILE-016). **BE Bước-4 delta** (KHÔNG thuộc file doc này): `api/imm08.py` (`list_pm_work_orders(filters, mine: int = 0, page, page_size)` — inject `f["assigned_to"]=session.user` khi `int(mine)` SAU `apply_vendor_scope` `:33`; **KHÔNG đụng** `services/imm08.py`/repo), tests (`test_imm08` mine-filter + backward-compat fence + count==rows + AND-with-filters; `test_mobile_oas` `WorkOrderMine` param — `_LIST_PARAM_EXPECT[_LIST_PM_PATH]` +`WorkOrderMine` + `_LIST_LIVE_FN` PM +`mine` + 14d shape-assert).

---

### 2. get_pm_work_order — Chi tiết PM WO

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.get_pm_work_order` |
| Role | All IMM roles |
| Idempotent | Yes |

**Request:** `?name=PM-WO-2026-00001`

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "name": "PM-WO-2026-00001",
    "asset_ref": "AC-ASSET-2026-0003",
    "asset_name": "Máy thở Drager Evita V500",
    "asset_category": "Mechanical Ventilator",
    "risk_class": "III",
    "pm_type": "Quarterly",
    "status": "In Progress",
    "due_date": "2026-04-17",
    "completion_date": null,
    "assigned_to": "ktv1@bv.vn",
    "is_late": false,
    "allowed_transitions": ["Completed", "Halted–Major Failure", "Pending–Device Busy", "Cancelled"],
    "checklist_results": [
      {
        "idx": 1,
        "description": "Kiểm tra điện áp đầu vào",
        "measurement_type": "Numeric",
        "unit": "V",
        "result": null,
        "measured_value": null,
        "notes": null
      }
    ]
  }
}
```

**`allowed_transitions[]` — server-driven CTA (Boundaries Always/Never):** detail emit tập trạng-thái-kế hợp-lệ từ `status` hiện tại → màn detail render nút workflow theo server.
- **Always:** giá trị = `_PM_VALID_TRANSITIONS.get(status, [])` (`services/imm08.py`) — SSoT duy nhất, **GROUNDED** workflow `imm_08_pm_workflow.json` (7 state / 13 transition):

  | Status hiện tại | `allowed_transitions[]` |
  |---|---|
  | `Open` | `In Progress`, `Overdue`, `Cancelled` |
  | `Overdue` | `In Progress`, `Cancelled` |
  | `In Progress` | `Completed`, `Halted–Major Failure`, `Pending–Device Busy`, `Cancelled` |
  | `Pending–Device Busy` | `In Progress`, `Cancelled` |
  | `Halted–Major Failure` | `In Progress`, `Cancelled` |
  | `Completed` (terminal) | `[]` (rỗng) |
  | `Cancelled` (terminal) | `[]` (rỗng) |

- **Never:** client KHÔNG hardcode `status → button` (anti-pattern lifecycle dead-gate); map BE KHÔNG sinh state ngoài enum `PMStatus` / ngoài workflow JSON. Mirror `IncidentDetail.allowed_transitions` (IMM-12, R3). Guard: SSoT-divergence (map ↔ workflow JSON) + codomain ⊆ `PMStatus` enum.

**Errors:** `NOT_FOUND`.

---

### 3. assign_technician — Phân công Kỹ thuật viên

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm08.assign_technician` |
| Role | Workshop Head, CMMS Admin |
| Idempotent | No |

**Request:**

```jsonc
{
  "name": "PM-WO-2026-00001",
  "technician": "ktv1@bv.vn",
  "scheduled_date": "2026-04-17"
}
```

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "name": "PM-WO-2026-00001",
    "status": "In Progress",
    "assigned_to": "ktv1@bv.vn"
  }
}
```

**Errors:** `NOT_FOUND` · `BAD_STATE` (WO không ở Open/Overdue — VR-08-08).

---

### 4. submit_pm_result — Kỹ thuật viên nộp kết quả PM

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm08.submit_pm_result` |
| Role | HTM Technician, Workshop Head |
| Idempotent | No |

**Request:**

```jsonc
{
  "name": "PM-WO-2026-00001",
  "checklist_results": "[{\"idx\":1,\"result\":\"Pass\",\"measured_value\":220.5,\"notes\":\"\"}]",
  "overall_result": "Pass",
  "technician_notes": "Sticker đã gắn",
  "pm_sticker_attached": 1,
  "duration_minutes": 52
}
```

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "name": "PM-WO-2026-00001",
    "new_status": "Completed",
    "is_late": false,
    "next_pm_date": "2026-07-17",
    "cm_wo_created": null
  }
}
```

> **`next_pm_date` (BR-08-03 — SoT contract).** Trường này = `compute_next_pm_date(wo.completion_date, sched_interval)` (services/imm08.py §4.2), kiểu **string** `YYYY-MM-DD`. Anchor LUÔN là `completion_date` của WO (KHÔNG `nowdate()`) → khi PM hoàn thành trễ/backdated, giá trị API trả về **bằng byte-for-byte** với `PM Schedule.next_due_date` đã persist, `AC Asset.next_pm_date`, và `PM Task Log.next_pm_date`. Khi `pm_interval_days` rỗng/0 → mặc định `+90` ngày (`PM_DEFAULT_INTERVAL_DAYS`). FE hiển thị **verbatim** field này, KHÔNG tự tính lại.

**Response error:**

```jsonc
{
  "success": false,
  "error": "Tất cả mục checklist phải có kết quả trước khi Submit (BR-08-08). Mục 'Kiểm tra áp suất' chưa điền.",
  "code": "VALIDATION"
}
```

**Errors:**

| Code | Khi nào |
|---|---|
| `NOT_FOUND` | WO không tồn tại |
| `INVALID_PARAMS` | `checklist_results` không phải JSON |
| `ALREADY_SUBMITTED` | WO đã docstatus=1 VR-08-10 |
| `VALIDATION` | BR-08-06 hoặc BR-08-08 fail |

**Side effects:**
- PM Task Log immutable tạo
- PM Schedule `last_pm_date`, `next_due_date` advance (BR-08-03)
- Asset `custom_last_pm_date`, `custom_next_pm_date` sync
- CM Work Order tạo nếu Fail-Minor/Major (BR-08-09)

---

### 5. report_major_failure — Dừng PM + Asset Out of Service

> **Mobile-BE binding**: ràng buộc codegen-ready (verb-flip, schema closed, oneOf 200, slot 401/403, ADR) ở **§0.1.2** + [`docs/mobile/ADR-MOBILE-013.md`](../mobile/ADR-MOBILE-013.md). Mục này là spec web-FE + cross-link mobile — KHÔNG nhân đôi schema.

| Mục | Giá trị |
|---|---|
| Method | POST (non-idempotent — mỗi call tạo **1 CM WO** + đặt asset **Out of Service**) |
| Path | `/api/method/assetcore.api.imm08.report_major_failure` |
| Role | HTM Technician, Workshop Head (cap `pm.write` — `api/imm08.py:77`) |
| Idempotent | No |

**Request — closed, required EXACT 2 (GROUNDED signature @`services/imm08.py:744` `report_major_failure(pm_wo_name, *, failure_description)`):**

```jsonc
{
  "pm_wo_name": "PM-WO-2026-00003",
  "failure_description": "Compressor không khởi động — điện áp 0V"
}
```

> **Self-Correction (round này)**: `failed_item_indexes` **đã LOẠI khỏi request** (`additionalProperties:false`). Lý do: service `report_major_failure(pm_wo_name, *, failure_description)` **KHÔNG nhận** field này (signature @`services/imm08.py:744`); §200 (`04_Backend_Design.md`) + web-FE đều bỏ qua. Bản cũ giữ field trong handler để "FE log" nhưng handler **truyền `failed_item_indexes=` vào service** → `TypeError` → HTTP-500 (lỗi thiết-kế-gốc). Sửa: drop field ở cả request-contract LẪN handler (`api/imm08.py:74-83` align signature). Mọi 2 field đều `required`.

**Response success — closed EXACT 4-key (GROUNDED return @`services/imm08.py:792-797`):**

```jsonc
{
  "success": true,
  "data": {
    "pm_wo": "PM-WO-2026-00003",
    "new_status": "Halted–Major Failure",
    "cm_wo_created": "WO-CM-2026-00019",
    "asset_status": "Out of Service"
  }
}
```

| # | Field | type | Ghi chú |
|---|---|---|---|
| 1 | `pm_wo` | string (**required**) | PK PM WO echo input (`pm_wo_name` `:793`) |
| 2 | `new_status` | string (**required**) | `enum` = **PMStatus** 7-state `[Open, In Progress, Completed, Overdue, Cancelled, "Halted–Major Failure", "Pending–Device Busy"]` (`services/imm08.py:43-50` — copy en-dash byte-khớp), `example: "Halted–Major Failure"` (`PMStatus.HALTED_MAJOR` `:49,794`) |
| 3 | `cm_wo_created` | string (**required**) | PK CM Work Order (Asset Repair) khẩn vừa tạo (`cm_wo.name` `:795`; autoname `WO-CM-.YYYY.-.#####`) |
| 4 | `asset_status` | string (**required**) | `example: "Out of Service"` (`AssetStatus.OUT_OF_SERVICE` `constants.py:94` `:796`) |

**Errors:** `NOT_FOUND` (WO∄ `IMM08_WO_NOT_FOUND` @`services/imm08.py:747` → `code=NOT_FOUND http_status=404` `messages.py:556`) ARRIVE **HTTP-200 + Error envelope** (quirk §5, KHÔNG status-line) → nhánh `Error` của 200-oneOf. `body.http_status` ∈ bounded enum R11 (**ĐÃ ⊇ {404} KHÔNG đổi**).

**Side effects:** PM WO `status = "Halted–Major Failure"` (`:749`) · Asset `lifecycle_status = "Out of Service"` + **sinh Lifecycle Event audit** (`:750`) · **CM WO khẩn tạo** (Asset Repair `repair_type="Breakdown"` + `priority="Emergency"`, `failure_description` = mô tả lỗi, `source_pm_wo` link `:752-762`) · Incident IMM-12 (`Malfunction/High`, best-effort) · Email khẩn Workshop Head + VP Block2.

> **Self-Correction (round này, cùng escalation — 2 bug runtime CM-WO)**: `RepairRepo.create` ở `report_major_failure` TRƯỚC đây sai 2 chỗ → mỗi escalation HTTP-500 (lộ ra khi BE-unit gọi handler): (1) KHÔNG set `failure_description` — `Asset Repair.failure_description` **mandatory** (`asset_repair.json reqd:1`) ⇒ `MandatoryError`; (2) `repair_type="Emergency"` KHÔNG hợp lệ (Select-options `{Corrective, Breakdown, Warranty Repair}`) ⇒ `ValidationError`. Sửa: thêm `"failure_description": failure_description` (mirror `imm09:840`) + `repair_type="Breakdown"` (độ-khẩn ở `priority="Emergency"`). KHÔNG chỉ nhét mô tả vào `technician_notes`.

---

### 6. get_pm_calendar — Calendar view tháng

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.get_pm_calendar` |
| Role | Workshop Head, HTM Technician |
| Idempotent | Yes |

**Request:** `?year=2026&month=4&asset_ref=&technician=`

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "month": "2026-04",
    "events": [
      {
        "name": "PM-WO-2026-00001",
        "asset_name": "Máy thở Drager Evita V500",
        "pm_type": "Quarterly",
        "due_date": "2026-04-17",
        "status": "Completed",
        "assigned_to": "ktv1@bv.vn",
        "is_late": false
      }
    ],
    "summary": { "total": 16, "completed": 14, "overdue": 2, "pending": 0 }
  }
}
```

---

### 7. get_pm_dashboard_stats — KPI dashboard

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.get_pm_dashboard_stats` |
| Role | Workshop Head, VP Block2, CMMS Admin |
| Idempotent | Yes |

**Request:** `?year=2026&month=4`

**Response success (tháng có WO due trong tháng — `total_scheduled` đã loại Cancelled):**

```jsonc
{
  "success": true,
  "data": {
    "kpis": {
      "total_scheduled": 16,        // WO không-Cancelled trong tháng (INV-PM-KPI-6) — KHÔNG gồm WO đã hủy
      "completed_on_time": 14,      // ⊆ 16
      "overdue_in_month": 1,        // ⊆ 16 (status==Overdue ∧ due_date trong tháng)
      "pending_in_month": 1,        // 16 − 14 − 1 (phần dư, đối-soát INV-PM-KPI-1)
      "compliance_rate_pct": 87.5,  // 14/16
      "avg_days_late": 3.5,
      "overdue": 5                  // GLOBAL — count_overdue_pm() toàn thời gian (RC-10), ≠ overdue_in_month
    },
    "trend_6months": [
      { "month": "2025-11", "total": 14, "on_time": 12, "rate": 85.7 },  // total = WO không-Cancelled
      { "month": "2026-04", "total": 16, "on_time": 14, "rate": 87.5 }
    ]
  }
}
```

**Response success (INV-PM-KPI-6 — tháng có 1 WO Cancelled bị loại khỏi mẫu):**

Dataset: tháng `{1 Completed on-time, 1 Completed late, 1 Overdue, 1 Cancelled}` (4 WO due trong tháng).

```jsonc
{
  "success": true,
  "data": {
    "kpis": {
      "total_scheduled": 3,         // 4 WO − 1 Cancelled = 3 (KHÔNG 4 — INV-PM-KPI-6)
      "completed_on_time": 1,
      "overdue_in_month": 1,
      "pending_in_month": 0,        // 3 − 2 completed (on-time+late) − 1 overdue = 0
      "compliance_rate_pct": 33.3,  // round(1/3*100,1) — cũ SAI 1/4=25.0
      "avg_days_late": 5.0,         // ngày trễ của WO Completed-late (không đổi quy tắc)
      "overdue": 5                  // GLOBAL — không phụ thuộc Cancelled
    },
    "trend_6months": [ /* rate tháng này = 33.3, t = 3 (không-Cancelled) */ ]
  }
}
```

> **Số học ví dụ trên:** `pending_in_month = total_scheduled − completed_in_month − overdue_in_month = 3 − 2 − 1 = 0` — `completed_in_month` trừ TẤT CẢ Completed (cả on-time lẫn late), nên WO `Completed-late` KHÔNG rơi vào `pending`. INV-PM-KPI-1 (`≥`): vế phải `= completed_on_time + overdue_in_month + pending_in_month = 1 + 1 + 0 = 2 ≤ total_scheduled = 3` (WO Completed-late là phần dôi). `Cancelled` ngoài mọi bucket. Khớp acceptance: `total_scheduled==3, compliance==33.3, completed_on_time==1, overdue_in_month==1, pending_in_month==0`.

**Response success (INV-PM-KPI-6 — tháng CHỈ có Cancelled WO):**

Dataset: tháng `{2 Cancelled, 0 khác}`.

```jsonc
{
  "success": true,
  "data": {
    "kpis": {
      "total_scheduled": 0,         // 2 Cancelled bị loại hết → 0 (KHÔNG 2)
      "completed_on_time": 0,
      "overdue_in_month": 0,
      "pending_in_month": 0,        // Cancelled KHÔNG rơi vào pending
      "compliance_rate_pct": null,  // total_scheduled==0 → null → FE '—' (KHÔNG 0.0 hiểu nhầm "không tuân thủ")
      "avg_days_late": 0.0,
      "overdue": 5
    },
    "trend_6months": [ /* ... */ ]
  }
}
```

**Response success (INV-PM-KPI-4 — phản ví dụ: tháng KHÔNG có WO due trong tháng nhưng 5 WO Overdue từ tháng trước):**

```jsonc
{
  "success": true,
  "data": {
    "kpis": {
      "total_scheduled": 0,
      "completed_on_time": 0,
      "overdue_in_month": 0,         // không WO nào due trong tháng → 0, KHÔNG = 5
      "pending_in_month": 0,
      "compliance_rate_pct": null,   // total==0 → null → FE hiện '—' (KHÔNG 0%)
      "avg_days_late": 0.0,
      "overdue": 5                   // global vẫn = 5 (Overdue từ tháng trước), drill ?overdue=1 ra đúng 5
    },
    "trend_6months": [ /* ... */ ]
  }
}
```

> FE PHẢI render 2 nhãn KHÁC NHAU: tile khối-tháng "Quá hạn trong tháng" = `overdue_in_month` (gắn "Phạm vi: tháng M/Y"); tile riêng "Quá hạn (toàn hệ thống)" = `overdue` (gắn "Toàn hệ thống") + là tile drill `?overdue=1`. KHÔNG để tile "Quá hạn: 5" đứng cạnh "Tổng lên lịch: 0" trong cùng strip không-đối-soát (root cause vòng 10).

---

### 8. reschedule_pm — Hoãn lịch PM

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm08.reschedule_pm` |
| Role | Workshop Head, CMMS Admin |
| Idempotent | No |

**Request:**

```jsonc
{
  "name": "PM-WO-2026-00004",
  "new_date": "2026-04-25",
  "reason": "Thiết bị đang dùng cấp cứu chiều 22/4 — dời sang 25/4"
}
```

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "name": "PM-WO-2026-00004",
    "old_date": "2026-04-22",
    "new_date": "2026-04-25",
    "status": "Pending–Device Busy"
  }
}
```

**Errors:** `VALIDATION` (reason < 5 ký tự — VR-08-09) · `NOT_FOUND`.

---

### 9. get_asset_pm_history — Lịch sử PM của thiết bị

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.get_asset_pm_history` |
| Role | All IMM roles |
| Idempotent | Yes |

**Request:** `?asset_ref=AC-ASSET-2026-0003&limit=10`

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "asset_ref": "AC-ASSET-2026-0003",
    "history": [
      {
        "name": "PMTL-2026-04-00012",
        "pm_work_order": "PM-WO-2026-00001",
        "pm_type": "Quarterly",
        "completion_date": "2026-04-17",
        "technician": "ktv1@bv.vn",
        "overall_result": "Pass with Minor Issues",
        "is_late": 0,
        "days_late": 0,
        "next_pm_date": "2026-07-17",
        "summary": "PM Q2 hoàn tất; thay filter, vệ sinh cảm biến."
      }
    ]
  }
}
```

> **[SELF-CORRECTION 2026-06-29]** Ví dụ cũ ghi `"is_late": false` (boolean) — SAI wire-type. `PM Task Log.is_late` = Frappe **Check** ⇒ wire **`0`/`1` (integer)**, KHÔNG `true`/`false`. Đã sửa `0` + bổ sung field `summary` (prop thứ 10 thiếu trong ví dụ cũ) để khớp đúng `services/imm08.py:1015-1017` → tránh int-vs-bool trap khi codegen mobile (xem §9.1).

#### 9.1 Mobile-BE binding — `getAssetPmHistory` (FLOW-2 device-profile, tab "Lịch sử bảo trì")

> **Ranh giới**: cùng 1 handler `imm08.get_asset_pm_history` phục vụ cả web-FE (mục này) và mobile-BE. Contract codegen-ready cho mobile mô tả ở SSoT riêng `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (`operationId: getAssetPmHistory`, path-count **52 → 53**) + [`docs/mobile/ADR-MOBILE-023.md`](../mobile/ADR-MOBILE-023.md). Mục này là **cross-link** — KHÔNG nhân đôi schema; mọi sửa field đồng bộ 2 nơi.

**Bối cảnh (ĐÓNG quartet device-profile read-history):** KTV quét QR → màn hồ-sơ-thiết-bị flow-2 đã có 3 tab read-history (`getAssetIncidentHistory` sự-cố · `getAssetTimeline` vòng-đời · `getAssetRepairHistory` CM). Tab **"Lịch sử bảo trì"** (PM) là mắt-xích CUỐI — "máy này PM lần cuối khi nào, Pass/Fail, có trễ hạn, lịch PM tới?". Endpoint nguồn **ĐÃ LIVE** (CONTRACT-ONLY, BE không đụng `.py`).

**Schema `AssetPmHistoryItem` (closed, EXACT 10 prop — GROUNDED `pm_task_log.json`):**

| Field | Frappe type | Wire type | Ràng buộc |
|---|---|---|---|
| `name` | PK (autoname) | `string` | **required** (PMTL-…) |
| `pm_work_order` | Link `PM Work Order` | `string` | — |
| `pm_type` | Data | `string` | tự-do (KHÔNG enum) |
| `completion_date` | **Date** | `string` | KHÔNG `format:date-time` (date-trap) |
| `technician` | Link `User` | `string` | — |
| `overall_result` | **Select** | `string` **enum** | `[Pass, Pass with Minor Issues, Fail]` |
| `is_late` | **Check** (0/1) | **`integer`** | KHÔNG `boolean` (int-bool-trap) |
| `days_late` | **Int** | **`integer`** | count ≥ 0 |
| `next_pm_date` | **Date** | `string` | KHÔNG `format:date-time` (date-trap) |
| `summary` | Text | `string` | "" nếu trống |

**Boundaries:**
- **Always**: 200 = SINGLE `$ref AssetPmHistoryEnvelope` `{success:true, data:{asset_ref:string, history:AssetPmHistoryItem[]}}` (handler `handle(svc.get_asset_history)` + svc 0 raise `ServiceError` ⇒ LUÔN `_ok`) · param `asset_ref` (query, required, NO default — `imm08.py:125`) + `limit` (integer, default 10, minimum 1) · slot EXACTLY `{200,401,403}` · `is_late`/`days_late` = `integer` · `overall_result` = enum 3-value · dates = `string` no-format.
- **Never**: `oneOf [Env, Error]` (svc 0 `_err` ⇒ KHÔNG có Error branch trên HTTP-200) · `404` (`history[]` rỗng hợp-lệ nếu asset chưa-PM) · `page`/`page_size` (chỉ limit cap) · param tên `asset` (phải `asset_ref`) · `boolean` cho `is_late` · `format:date-time` cho dates · sửa `api/imm08.py`/`services/imm08.py` (BE LIVE — contract-only).

> **Acceptance contract (chốt cho BE/Test — Bước 4)**: (1) **CONTRACT-ONLY** — `git diff HEAD -- api/imm08.py services/imm08.py` phần `get_asset_pm_history`/`get_asset_history` = TRỐNG (KHÔNG đụng `.py`, KHÔNG reload gunicorn, KHÔNG migrate — `[AUTO]` thật). (2) YAML **52 → 53** path / **52 → 53** operationId (`getAssetPmHistory` mới UNIQUE camelCase, dotted-tail == opId, tag `pm`, summary `[MVP flow-2] Lịch sử bảo trì PM của thiết bị (màn hồ-sơ sau quét QR)`, 0 dangling `$ref`, `safe_load` OK); 52 path/opId cũ **byte-identical** (additive, 0 regress). Path GET-only; param `asset_ref` (query, required, no-default) + `limit` (integer, default 10, minimum 1); KHÔNG `page`/`page_size`; security authed (bearer/sid). (3) `AssetPmHistoryEnvelope` closed `{success enum[true], data{asset_ref, history[]}}` `data.required[asset_ref, history]` no-pagination + `AssetPmHistoryItem` closed (`additionalProperties:false`) EXACT 10 prop `required[name]` (bảng trên — `is_late`/`days_late integer`, `overall_result` enum, dates `string` no-format); **200 = SINGLE `$ref AssetPmHistoryEnvelope` (KHÔNG `oneOf`)**; slot `{200,401,403}` (`401 Unauthorized401`, `403 Forbidden` $ref — guest dispatcher-403). (4) Guard XANH @source (`bench --site miyano run-tests --module assetcore.tests.test_mobile_oas`): +TC class `TestMobileGetAssetPmHistoryContract` (a..j, ≈10 TC mirror `TestMobileGetAssetRepairHistoryContract` +1 TC `overall_result` enum-bound + 1 TC `is_late`/`days_late` cả-hai-integer); `_EXPECTED_TEST_COUNT` **492 → ~502** (= giá-trị introspect THẬT, KHÔNG tin số-học); `_MVP_BUSINESS_PATHS` +`_ASSET_PM_HISTORY_PATH`; `test_oas_d12/d15/d17` **UNCHANGED** (pure mobile-yaml — KHÔNG đụng `generate_spec`); `test_mobile_docset` XANH (`_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 492→~502 + `_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL` +cùng N + **ADR-MOBILE-023 registered README** TC-MOB-DOC-02). (5) RED-before/GREEN-after cho MỌI TC mới. Working-tree để USER review.

---

### 10. apply_pm_template_to_category — Bulk tạo PM Schedule theo danh mục

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm08.apply_pm_template_to_category` |
| Role | Workshop Head, CMMS Admin |
| Idempotent | Yes (bỏ qua asset đã có PM Schedule cùng pm_type) |

**Request:**

```jsonc
{
  "template_name": "PMCT-Ventilator-Quarterly"
}
```

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "template": "PMCT-Ventilator-Quarterly",
    "asset_category": "Mechanical Ventilator",
    "created": ["PMS-AC-ASSET-0001-Quarterly", "PMS-AC-ASSET-0003-Quarterly"],
    "skipped": ["PMS-AC-ASSET-0002-Quarterly"],
    "errors": []
  }
}
```

**Errors:** `NOT_FOUND` (template không tồn tại) · `VALIDATION` (template chưa gán danh mục).

**Side effects:**
- Tạo `PM Schedule` mới cho mọi AC Asset thuộc `template.asset_category`, trừ: asset đã có lịch cùng `pm_type` (bỏ qua), asset Decommissioned/Disposed (bỏ qua).
- `pm_interval_days` lấy từ `AC Asset Category.default_pm_interval_days` (fallback 180 ngày).

---

## 7. Smoke test playbook

```bash
BASE="https://erp.bv.vn/api/method"
AUTH="Authorization: token KEY:SECRET"

# 1. List WO Overdue
curl -H "$AUTH" "$BASE/assetcore.api.imm08.list_pm_work_orders?filters=%7B%22status%22%3A%22Overdue%22%7D"

# 2. Get PM Dashboard
curl -H "$AUTH" "$BASE/assetcore.api.imm08.get_pm_dashboard_stats?year=2026&month=4"

# 3. Submit PM Result
curl -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"PM-WO-2026-00001","checklist_results":"[{\"idx\":1,\"result\":\"Pass\"}]","overall_result":"Pass","pm_sticker_attached":1,"duration_minutes":45}' \
  "$BASE/assetcore.api.imm08.submit_pm_result"
```

---

## 11. Notification Contract (Sprint Notification 2026-05-29 vòng 3) — SINGLE SOURCE OF TRUTH

Mọi tương tác IMM-08 trả về **envelope chuẩn** đã chuẩn hoá BE → FE. FE KHÔNG
hardcode câu chữ — chỉ đọc `message_code` rồi render qua `useNotify`. Contract đã
chốt vòng 1 (pilot IMM-09), vòng 2 (IMM-12) — vòng 3 áp dụng cho IMM-08.

### 11.1 Envelope shape

Success (`_ok`):
```json
{ "success": true, "data": { ... } }
```
Lỗi (`_err`, hydrate từ registry qua `api_handler.handle()`):
```json
{
  "success": false,
  "error": "Tất cả mục checklist phải có kết quả trước khi hoàn thành PM.",
  "code": "VALIDATION",
  "message_code": "IMM08-CHECKLIST-INCOMPLETE",
  "severity": "warning",
  "title": "Checklist chưa hoàn tất",
  "action_hint": "Điền kết quả cho mọi mục checklist rồi thử lại.",
  "context": { "item": "Kiểm tra nguồn điện" },
  "http_status": 422
}
```

**Bất biến (contract):** mọi error envelope IMM-08 PHẢI có `message_code`, `severity`,
`title`. Không còn `frappe.throw(_("..."))` leak message Frappe ra FE. Service raise
qua `nthrow(MSG.IMM08_*)`; DocType `validate` hook (BR-08-06/08/09/10/02) raise qua
`nthrow_in_hook(MSG.IMM08_*)`.

### 11.2 Danh mục MSG cần bổ sung vào `utils/messages.py`

11 mã mới + tái dùng mã hệ thống (`AUTH_FORBIDDEN`, `VAL_INVALID_PARAMS`, `SYS_500`
— đã có). Severity tuân quy tắc §11.5.

| MSG.* | code (kebab) | severity | http | title | template (VI) | action_hint |
|---|---|---|---|---|---|---|
| `IMM08_WO_NOT_FOUND` | `IMM08-WO-NOT-FOUND` | warning | 404 | Không tìm thấy lệnh PM | Không tìm thấy lệnh bảo trì định kỳ: {name}. | Kiểm tra lại mã lệnh PM trong danh sách. |
| `IMM08_SCHEDULE_NOT_FOUND` | `IMM08-SCHEDULE-NOT-FOUND` | warning | 404 | Không tìm thấy lịch PM | Không tìm thấy lịch bảo trì định kỳ: {name}. | Kiểm tra lại mã lịch PM trong danh sách. |
| `IMM08_TEMPLATE_NOT_FOUND` | `IMM08-TEMPLATE-NOT-FOUND` | warning | 404 | Không tìm thấy mẫu checklist | Không tìm thấy mẫu checklist PM: {name}. | Kiểm tra lại mã mẫu trong danh sách. |
| `IMM08_BAD_STATE` | `IMM08-BAD-STATE` | warning | 409 | Sai trạng thái lệnh PM | Không thể thực hiện hành động khi lệnh PM đang ở trạng thái '{state}'. | Chỉ thực hiện hành động hợp lệ với trạng thái hiện tại. |
| `IMM08_ALREADY_SUBMITTED` | `IMM08-ALREADY-SUBMITTED` | warning | 409 | Lệnh PM đã chốt | Lệnh bảo trì định kỳ này đã được hoàn thành và chốt. | Không cần thao tác lại — lệnh PM đã chốt. |
| `IMM08_CHECKLIST_INCOMPLETE` | `IMM08-CHECKLIST-INCOMPLETE` | warning | 422 | Checklist chưa hoàn tất | Tất cả mục checklist phải có kết quả trước khi hoàn thành PM. Mục '{item}' chưa điền. | Điền kết quả cho mọi mục checklist rồi thử lại. |
| `IMM08_DURATION_REQUIRED` | `IMM08-DURATION-REQUIRED` | warning | 422 | Thiếu thời gian thực hiện | Thời gian thực hiện (phút) phải lớn hơn 0 trước khi hoàn thành PM. | Nhập thời gian thực hiện rồi thử lại. |
| `IMM08_STICKER_REQUIRED` | `IMM08-STICKER-REQUIRED` | warning | 422 | Chưa gắn tem bảo trì | Phải xác nhận đã gắn tem bảo trì trước khi hoàn thành PM. | Gắn tem bảo trì và tích xác nhận rồi thử lại. |
| `IMM08_PHOTO_REQUIRED` | `IMM08-PHOTO-REQUIRED` | warning | 422 | Thiếu ảnh bằng chứng | Thiết bị nguy cơ cao ({risk_class}) bắt buộc đính kèm ảnh trước/sau PM. | Đính kèm ảnh bằng chứng rồi thử lại. |
| `IMM08_SOURCE_PM_REQUIRED` | `IMM08-SOURCE-PM-REQUIRED` | warning | 422 | Thiếu lệnh PM gốc | Lệnh khắc phục (CM) phải tham chiếu lệnh PM gốc. | Chọn lệnh PM gốc rồi thử lại. |
| _(success)_ `IMM08_SUBMIT_SUCCESS` | `IMM08-SUBMIT-SUCCESS` | success | 200 | Đã hoàn thành PM | Đã ghi nhận kết quả bảo trì định kỳ {name}. | — |

> Content tuân `messages.py` §quy chuẩn — Chủ thể + Hậu quả + Hành động, không từ
> kỹ thuật, không đổ lỗi user. Sau khi thêm vào `messages.py`, chạy
> `python scripts/gen_fe_messages.py` để regen `frontend/src/i18n/messages.ts`.

### 11.3 BE migration checklist (cho assetcore-be)

- `services/imm08.py` hook `validate_work_order`: 5 `frappe.throw(_(...))` (BR-08-08
  checklist, BR-08-09 duration, BR-08-10 sticker, BR-08-06 photo, BR-08-02 source PM)
  → `nthrow_in_hook(MSG.IMM08_*)` tương ứng. Đây là DocType `validate` hook → BẮT BUỘC
  dùng `nthrow_in_hook` (không phải `nthrow`).
- `services/imm08.py` service layer: các `raise ServiceError(ErrorCode.NOT_FOUND, ...)`
  cho PM WO / Schedule / Template → `nthrow(MSG.IMM08_WO_NOT_FOUND / _SCHEDULE_NOT_FOUND
  / _TEMPLATE_NOT_FOUND, name=...)`. `ErrorCode.CONFLICT` "đã Submit" →
  `nthrow(MSG.IMM08_ALREADY_SUBMITTED)`. `ErrorCode.BAD_STATE` reschedule →
  `nthrow(MSG.IMM08_BAD_STATE, state=...)`. Các wrap generic `str(e)` (VALIDATION/INTERNAL)
  GIỮ NGUYÊN — handler hydrate fallback.
- `api/imm08.py`: bỏ `_parse_json`/`_handle` cục bộ + `from utils.helpers import _err,_ok`
  → dùng `from assetcore.utils.api_handler import handle, parse_json` +
  `from assetcore.utils.response import _ok, _err`. Giữ guard rbac/vendor-scope trước `handle`.
- Audit trail (`log_lifecycle_event`, PM Task Log) KHÔNG đổi. Auto-CM-WO side-effect
  (`_create_cm_wo_from_failure`) KHÔNG đổi — message framework chỉ chuẩn hoá phản hồi user.

### 11.4 FE migration checklist (cho assetcore-fe)

- Store `stores/imm08.ts`: expose `lastApiError`; mọi action catch → set `lastApiError`
  từ error envelope (giống `stores/imm09.ts`).
- Views `pm/*` (PMWorkOrderDetailView, PMWorkOrderCreateView, PmScheduleListView,
  PmTemplateListView, …): thay `toast.error(msg)` / hardcode success →
  `notify.fromError(store.lastApiError)` trong catch; success →
  `notify.show(MSG.IMM08_SUBMIT_SUCCESS, ctx)` hoặc `notify.fromOk(resp)`.
- KHÔNG còn `try/catch` tự build string từ `e.message` BE.

### 11.5 Quy tắc severity (chốt cho IMM-08)

- `warning` = lỗi nghiệp vụ user tự sửa được (validation BR-08-*, bad-state, not-found,
  conflict) → toast vàng, GIỮ form, không reload.
- `error` = lỗi hệ thống (`SYS-*`) → toast đỏ.
- `success` = thao tác thành công → toast xanh.

> Lưu ý: BR-08-* của PM là validation nghiệp vụ user sửa được, KHÔNG phải compliance
> blocking như BR-12 (clinical impact / RCA gate). Do đó severity = `warning`, không
> `critical`. Photo evidence BR-08-06 dù bắt buộc theo ISO 13485 vẫn để `warning`
> (user tự đính kèm ảnh, không cần modal blocking).

---

## DoD — File 05 hoàn chỉnh

- [x] API Catalog liệt kê 100% 24 endpoint (7 WO + 3 Calendar/Dashboard + 6 Schedule + 7 Template + 1 Bulk)
- [x] Response format `{"success": true, "data": {...}}` chuẩn AssetCore
- [x] Error format `{"success": false, "error": "...", "code": "..."}` chuẩn
- [x] Error code catalog đầy đủ + FE mapping
- [x] TypeScript type definitions đầy đủ
- [x] Mỗi endpoint có request schema + response example
- [x] Side effects nêu rõ
- [x] Pagination convention nhất quán
- [x] Smoke test playbook
