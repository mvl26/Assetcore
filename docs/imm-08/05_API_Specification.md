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
| 1 | `assetcore.api.imm08.list_pm_work_orders` | GET | List PM WO với filter (`filters` JSON-blob + **`mine`** + **`search`**) + pagination. `mine=1` scope `assigned_to==session.user` (tab "Phiếu PM của tôi" MVP-5a); `search` OR-LIKE `name`/`asset_code`/`asset_name` toàn tập (CR-18 — §2 #1 "free-text search" + BR-08-17 + ADR-IMM08-SEARCH-01) | All IMM roles | ✓ | US-08-01 |
| 2 | `assetcore.api.imm08.get_pm_work_order` | GET | Chi tiết 1 WO + checklist. **CR-74:** read-gate 3 lớp ROLE→EXISTS→ROW, 403 in-envelope (§12). **AC-CR-77 (2026-07-26):** response += `available_actions[]` = **4 CTA server-driven** `[start_work, submit_result, reschedule, report_major_failure]` — hết "nút chết" + hết CTA ma `Cancelled` (§13) | All IMM roles | ✓ | — |
| 3 | `assetcore.api.imm08.assign_technician` | POST | Phân công Kỹ thuật viên cho WO Open/Overdue | Workshop Head, CMMS Admin | ✗ | US-08-06 |
| 4 | `assetcore.api.imm08.submit_pm_result` | POST | Kỹ thuật viên nộp kết quả PM (submit WO). **Idempotent replay khi có `client_request_id`** (mobile write-outbox — BR-08-18 / ADR-IMM08-IDEMPOTENCY-01) | HTM Technician, Workshop Head | ✗ legacy · ✓ replay khi có `client_request_id` | US-08-02 |
| 5 | `assetcore.api.imm08.report_major_failure` | POST | Dừng PM + tạo CM khẩn + Asset OOS | HTM Technician, Workshop Head | ✗ | US-08-03 |
| 6 | `assetcore.api.imm08.reschedule_pm` | POST | Hoãn lịch PM (lý do bắt buộc) | Workshop Head, CMMS Admin | ✗ | US-08-06 |
| 7 | `assetcore.api.imm08.create_pm_work_order` | POST | Tạo PM WO thủ công (ad-hoc) | Workshop Head, CMMS Admin | ✗ | — |
| 25 | `assetcore.api.imm08.attach_pm_checklist_photo` | POST (multipart) | Đính **ảnh bằng chứng theo TỪNG mục checklist PM** (NĐ98 Class C/D) vào 1 PM Work Order → File private (`attached_to='PM Work Order'`) + populate `pm_checklist_result[idx].photo` + đúng 1 lifecycle `pm_checklist_photo_attached`. Permission = **KTV được giao (`assigned_to`) HOẶC `pm_work_order.write`** (§2 #11 + BR-08-15). Mobile CR-14/G6. Đối xứng `imm12.attach_incident_photo` (KHÁC module/doctype/discriminator per-item). | assigned KTV OR `pm.write` | US-08-02 |

### Calendar & Dashboard

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent | Liên kết US |
|---|---|---|---|---|---|---|
| 8 | `assetcore.api.imm08.get_pm_calendar` | GET | Events theo tháng cho calendar view | Workshop Head, HTM Technician | ✓ | US-08-07 |
| 9 | `assetcore.api.imm08.get_pm_dashboard_stats` | GET | KPI compliance + trend 6 tháng | Workshop Head, VP Block2, CMMS Admin | ✓ | US-08-08 |
| 10 | `assetcore.api.imm08.get_asset_pm_history` | GET | Lịch sử PM Task Log của 1 thiết bị | ~~All IMM roles~~ → **DocPerm `read` trên `PM Task Log`** (cap `pm.read_history`) — cải chính `AC-CR-119`,  xem §9.4 | ✓ | — |

> **📱 Mobile OAS mirror (CR-31a):** endpoint #9 `get_pm_dashboard_stats` được curate VERBATIM vào hợp-đồng máy-đọc mobile (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`, opId `getPmDashboardStats`, tag `pm`, `200 = oneOf [PmDashboardStatsEnvelope, Error]`) — quyết định + schema 7-key `kpis`/`trend_6months` VERBATIM ở [`../mobile/ADR-MOBILE-056.md`](../mobile/ADR-MOBILE-056.md). `compliance_rate_pct=null` khi `total_scheduled==0` (INV-PM-KPI-3) ⇒ mobile khai `nullable:true ∉ required`; `overdue` = count GLOBAL (RC-10, KHÁC `overdue_in_month`). CONTRACT-ONLY (backend LIVE, 0 `.py`/reload/migrate). `getCalibrationKpis`/`getRepairKpis` forward-reserve.

### PM Schedules

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent |
|---|---|---|---|---|---|
| 11 | `assetcore.api.imm08.list_pm_schedules` | GET | Danh sách PM Schedule | All IMM roles | ✓ |
| 12 | `assetcore.api.imm08.get_pm_schedule` | GET | Chi tiết 1 PM Schedule | All IMM roles | ✓ |
| 13 | `assetcore.api.imm08.create_pm_schedule` | POST | Tạo PM Schedule mới | Workshop Head, CMMS Admin | ✗ |
| 14 | `assetcore.api.imm08.update_pm_schedule` | POST | Cập nhật PM Schedule | Workshop Head, CMMS Admin | ✗ |
| 15 | `assetcore.api.imm08.set_pm_schedule_status` | POST | Đổi status (Active/Paused/Suspended) | Workshop Head, CMMS Admin | ✗ |
| 16 | `assetcore.api.imm08.delete_pm_schedule` | POST | Xóa PM Schedule | CMMS Admin | ✗ |
| 26 | `assetcore.api.imm08.get_due_pm_schedules` | GET | Lịch PM sắp/quá hạn ≤ N ngày (nguồn `PM Schedule.next_due_date`, filter `status=Active`) — màn "Nhắc việc" mobile **F8 nửa-PM**, ĐỐI XỨNG `get_due_calibrations` (IMM-11 §0.1.9). NEW `.py` (Bước-4) → reload PENDING USER | All IMM roles | ✓ |

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

### 0.1.4. Write-action binding — `attachPmChecklistPhoto` (PM EVIDENCE per-item, mobile CR-14/G6)

> **Bối cảnh (Vòng 2)**: KTV thực hiện PM trên mobile cần đính **ảnh bằng chứng cho từng mục checklist** (NĐ98 Class C/D) TRƯỚC khi `submitPmResult` (§2 #4). Đây là **write-path multipart** ĐẦU TIÊN của IMM-08 — đối xứng `attachIncidentPhoto` (IMM-12, Vòng 1). Đặc tả đầy đủ nghiệp vụ + bảng lỗi + ADR ở **§2 #11**; mục này là cross-link contract mobile.

| Mục | Giá trị |
|---|---|
| Mobile operationId | `attachPmChecklistPhoto` (mới — UNIQUE camelCase, **KHÁC** `attachIncidentPhoto`), tag `work-order` |
| HTTP method / path | `POST /api/method/assetcore.api.imm08.attach_pm_checklist_photo` — **multipart/form-data** (KHÔNG oneOf json+form; write-path binary, KHÔNG idempotent) |
| Summary | `[MVP-4] Đính ảnh bằng chứng theo mục checklist PM (NĐ98)` |
| requestBody | `multipart/form-data`: `work_order_name` (string, required), `checklist_item_idx` (integer, required), `file` (string binary, required); `required:true` |
| Response 200 | `oneOf [AttachPmChecklistPhotoEnvelope, Error]` (route-by-VALUE `body.success`, **0 discriminator**); data = `{file_url, file_name, checklist_item_idx}` closed |
| Status codes (OAS slot) | 200 / 401 `Unauthorized401` (bearer hết-hạn/invalid) / **403 `Forbidden` SINGLE-SHAPE = dispatcher-403 (guest/no-token)**. ⚠️ **Self-Correction:** slot 403 chỉ giữ **dispatcher-403**; **in-handler cap-403 KHÔNG ở slot 403** mà đến qua nhánh Error của 200-oneOf (`http_status=403`) — mirror `attachIncidentPhoto` ADR-MOBILE-027/029, KHÁC `reportIncident` DUAL-403 |
| Lifecycle | File private (`attached_to='PM Work Order'`) + `pm_checklist_result[idx].photo` set + đúng 1 event `pm_checklist_photo_attached` |
| Cross-ref | §2 #11 (spec đầy đủ) · ADR-IMM08-PHOTO-03 (reconcile MAX=1 write-once, supersede PHOTO-01) · PHOTO-02 (lifecycle) · PHOTO-04 (HEIC policy cross-module) · **mobile OpenAPI mirror ĐÃ CURATE**: [`docs/mobile/ADR-MOBILE-029.md`](../mobile/ADR-MOBILE-029.md) + [`04-api-contract.md`](../mobile/04-api-contract.md) §8.35 (opId `attachPmChecklistPhoto`, path/opId 60→61, CONTRACT-ONLY pure-yaml) |

### 0.1.5. Read-list binding — `getDuePmSchedules` (DUE/OVERDUE PM LIST, màn "Nhắc việc" **nửa-PM** · MỞ NHÁNH F8 · CR-28b)

> **Bối cảnh (MỞ NHÁNH F8-Nhắc-việc, ĐÓNG NỬA PM)**: Màn **"Nhắc việc"** trên mobile cần 2 danh sách song song để KTV ưu tiên đi làm: **(1) Hiệu chuẩn sắp/quá hạn** (`getDueCalibrations`, IMM-11 §0.1.9 — ✅ LIVE) và **(2) PM sắp/quá hạn** (`getDuePmSchedules` — **nửa CHẾT bồi round này**). Đây là danh sách **LỊCH PM (PM Schedule) due** — nguồn `PM Schedule.next_due_date` (**KHÁC** `getDueCalibrations` dùng `AC Asset.next_calibration_date`; **KHÁC** `listPmSchedules` §catalog #11 là liệt-kê-CRUD toàn tập không cửa-sổ due). Endpoint **MỚI** (`.py` chưa tồn tại) → Bước-4 BE build service + handler; NEW `.py` ⇒ **reload gunicorn = HARD-STOP USER** (test qua `bench run-tests` fresh-load nên vẫn xanh; 0 migrate). Cross-link SSoT `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3.0.3) — **KHÔNG nhân đôi schema**; mọi sửa field đồng bộ 2 nơi.

> **⚠️ ĐIỂM KHÁC CỐT-LÕI vs `listPmSchedules`/mọi list khác — KHÔNG PAGINATION.** `data` = **`{items[], threshold_days}` CHÍNH XÁC 2 key** (ĐỐI XỨNG `get_due_calibrations` @`services/imm11.py:1421` `return {"items": rows, "threshold_days": int(days)}`). Handler KHÔNG surface `pagination` (mirror `get_due_calibrations`: `rows, _ = Repo.list(..., page_size=int(limit))` — bỏ pagination meta, chỉ limit-cap trang đầu ASC). ⇒ `DuePmScheduleListPage` **KHÔNG có `pagination` `$ref`** — điểm PHÂN BIỆT vs `PmScheduleListEnvelope` (§catalog #11, `{data[], pagination}`). Vẫn vào `_MVP_LIST_ENVELOPE` vì 200 = **oneOf [Env, Error]** (`handle()`-contract). **Invariant `count==rows` KHÔNG áp** (KHÔNG surface count/pagination — mirror `getDueCalibrations`; rows = trang-đầu `limit` sort `next_due_date asc`).

| Mục | Giá trị |
|---|---|
| Mobile operationId | `getDuePmSchedules` (GET, **path 84 → 85**), tag **`pm`** (REUSE tag của `getPmWorkOrder` @YAML — read-endpoint IMM-08; **KHÔNG** `work-order` vì đây READ-list không action) |
| Handler (Bước-4 BE build) | `assetcore.api.imm08.get_due_pm_schedules` — **`@frappe.whitelist()` BARE** (nhận GET; **KHÔNG `methods=["POST"]`**, **KHÔNG `rbac.require`** → 0 cap-gate) → `return handle(svc.get_due_pm_schedules, int(days), int(limit))`. **VERBATIM mirror** `api/imm11.py:202-203`. `_form_dict` KHÔNG cần (2 param typed). |
| Service (Bước-4 BE build) | `services/imm08.py` `get_due_pm_schedules(days: int = 30, limit: int = 50) -> dict` — `today = nowdate()`; `threshold = add_days(today, int(days))`; `rows, _ = PMScheduleRepo.list(filters=[["status","=",PMScheduleStatus.ACTIVE], ["next_due_date","is","set"], ["next_due_date","<=",threshold]], fields=[name,asset_ref,pm_type,status,next_due_date,last_pm_date,responsible_technician], order_by="next_due_date asc", page_size=int(limit))`; enrich `r["asset_name"] = AssetRepo.get_value(r["asset_ref"], "asset_name") or ""` (mirror `list_schedules` @`services/imm08.py:1327`); derive `r["days_left"] = date_diff(nd, today_d) if nd else None` (dead-branch — filter is-set loại NULL); `return {"items": rows, "threshold_days": int(days)}`. `add_days`/`date_diff`/`getdate`/`nowdate` đã import @`services/imm08.py:9`; `PMScheduleStatus` @`:227`; `PMScheduleRepo`/`AssetRepo` đã import. |
| Params | **2 typed query-param INLINE** (mirror `getDueCalibrations`): `days` (`integer`, **default 30**, `in:query`, `required:false`) — cửa-sổ ngày "due" (`threshold = add_days(today, days)`) · `limit` (`integer`, **default 50**, `in:query`, `required:false`) — cap số dòng (`page_size`). Signature 2-default ⇒ CẢ 2 `required:false`. **0 param `filters`, 0 `mine`, 0 `page`.** |
| Response 200 | `oneOf [DuePmScheduleListEnvelope, Error]` (Decision-B route-by-VALUE `body.success`, **0 discriminator**, đối xứng `getDueCalibrations`). ∈ `_MVP_LIST_ENVELOPE` (map `→ #/components/schemas/DuePmScheduleListEnvelope`) |
| Status codes | 200 / 401 (`Unauthorized401` — bearer hết-hạn = dispatcher) / **403 SINGLE-SHAPE `Forbidden` — dispatcher-ONLY** (guest/no-token, `@whitelist` no `allow_guest`). **KHÔNG có 403-cap-branch REACHABLE** (bare `@whitelist`, 0 `rbac.require` — mirror `getDueCalibrations`/`listTransfers`). Path ∈ `_MVP_BUSINESS_PATHS` ⇒ 401/403 symmetry set tự +1. |

**`DuePmScheduleListItem`** — CLOSED (`additionalProperties:false`) **EXACT 11 prop** = 7 field `PMScheduleRepo.list` ∪ `asset_name` (enrich) ∪ `days_left` (derive) ∪ **CR-45** `next_wo_ref` + `next_wo_status` (enrich 1-batch PM Work Order). **0 field thừa/thiếu** (SSoT DocType = `pm_schedule.json`; 2 field cuối KHÔNG field DocType — enrich cross-doctype). ⚠️ **9 field cũ + `threshold_days`/`total`/`truncated` GIỮ NGUYÊN byte-identical — CR-45 ADDITIVE 0-breaking**:

| # | Field | Type | Ground (SSoT `pm_schedule.json` field) |
|---|---|---|---|
| 1 | `name` | string (**required**) | PK `PM Schedule.name` (naming-series) |
| 2 | `asset_ref` | string | `PM Schedule.asset_ref` (Link `AC Asset`, `reqd`) |
| 3 | `asset_name` | string | **ENRICH** — `AssetRepo.get_value(asset_ref, "asset_name") or ""` (KHÔNG field DocType `PM Schedule`; join `AC Asset.asset_name`, mirror `list_schedules`) |
| 4 | `pm_type` | string enum `['Quarterly','Semi-Annual','Annual','Ad-hoc']` | `PM Schedule.pm_type` (Select 4-value). **String Select — KHÔNG Check ⇒ KHÔNG integer-enum** |
| 5 | `status` | string enum `['Active','Paused','Suspended']` | `PM Schedule.status` (Select 3-value). Runtime **LUÔN `Active`** (filter `["status","=","Active"]` loại Paused/Suspended) — enum giữ đủ 3 value domain DocType (schema-honest), example `Active` |
| 6 | `next_due_date` | string `format:date` (**KHÔNG `nullable`**) | `PM Schedule.next_due_date` (Date). **Non-nullable Ở ĐÂY** — filter `["next_due_date","is","set"]` loại NULL ⇒ MỌI dòng có date thật |
| 7 | `last_pm_date` | string `format:date` (**`nullable:true`**) | `PM Schedule.last_pm_date` (Date). **CÓ THỂ NULL** — lịch mới tạo từ commissioning chưa từng chạy PM (KHÁC `next_due_date` — điểm nullable KHÁC nhau, đừng copy-nhầm) |
| 8 | `responsible_technician` | string (**`nullable:true`**) | `PM Schedule.responsible_technician` (Link `User`, optional — có thể chưa gán). FE mobile lọc/hiển thị "PM của tôi" client-side theo field này |
| 9 | `days_left` | **`integer`** signed (**KHÔNG `nullable`**, KHÔNG enum) | **DERIVE** — `date_diff(next_due_date, today)`. **Âm = quá hạn** (vd `-3` = quá 3 ngày), `0` = đến hạn hôm nay, dương = còn N ngày. Client DÙNG TRỰC TIẾP sort/ưu-tiên — **KHÔNG re-derive** vs client-clock (server-flag SSoT, `memory/overdue_server_flag_ssot.md`) |
| 10 | `next_wo_ref` | string (**`nullable:true`**) | **ENRICH CR-45** (1-batch) — PK `PM Work Order` MỞ **gần hạn nhất** của lịch này (`order scheduled_date asc`), HOẶC `null` nếu lịch 0 phiếu mở. "Phiếu MỞ" = `status ∈ {Open, Overdue, In Progress, Pending–Device Busy}` (loại Completed/Cancelled/Halted–Major). Cho màn "Nhắc việc" **mở đường vào phiếu** (deep-link) — KTV bấm dòng lịch → vào thẳng phiếu đang chờ, KHÔNG phải tự dò |
| 11 | `next_wo_status` | string (**`nullable:true`**) | **ENRICH CR-45** — `status` của phiếu `next_wo_ref` (khớp 1-1). `null` khi `next_wo_ref` là `null`. FE render nhãn trạng thái phiếu ngay trên dòng nhắc việc + quyết định CTA («Dời lịch»/«Bắt đầu») |

#### CR-45 — Bồi `next_wo_ref`/`next_wo_status` (mở đường vào phiếu từ màn "Nhắc việc")

> **Bối cảnh (đề mục vòng 3 · CR-45a):** Màn "Nhắc việc" trước đây chỉ liệt-kê LỊCH PM (PM Schedule) due nhưng **KHÔNG chỉ ra phiếu (PM Work Order) đang chờ** của lịch đó ⇒ KTV thấy "lịch quá hạn" nhưng phải rời màn, tự dò danh sách WO để tìm phiếu tương ứng rồi mới «Dời lịch»/«Bắt đầu». CR-45 **bồi 2 field enrich** để mỗi dòng nhắc việc **deep-link thẳng vào phiếu MỞ gần hạn nhất**. Application code (`services/imm08.py`) = **[BE] Bước-4**; slice OAS + shape-guard đóng ở **Bước-2 (BA)**.

| Khóa | Kiểu | Ngữ nghĩa (SSoT enrich) |
|---|---|---|
| `next_wo_ref` | string \| null | PK `PM Work Order` MỞ gần hạn nhất của lịch (`pm_schedule == row.name`), HOẶC `null` nếu 0 phiếu mở. |
| `next_wo_status` | string \| null | `status` phiếu `next_wo_ref`; `null` khi `next_wo_ref` null. |

- **"Phiếu MỞ" (SSoT — hằng `NEXT_WO_OPEN_STATES`):** `frozenset({Open, Overdue, In Progress, Pending–Device Busy})` — tức **non-terminal ∧ non-halted** (= `OVERDUE_SOURCE_STATES` ∪ `{Overdue}`). Loại `Completed`/`Cancelled` (terminal) **VÀ** `Halted–Major Failure` (đã escalate sang CM — không còn là PM chờ xử lý). Lịch chỉ có phiếu ngoài tập này (hoặc 0 phiếu) → `next_wo_ref = next_wo_status = null`.
- **"Gần hạn nhất" = `order scheduled_date asc`** (phiếu đầu tiên sau sort) — khớp acceptance AC2. Thêm `name asc` làm tie-break xác định (test-stable + dàn NULL `scheduled_date`). ⚠️ *(Cần khảo sát)* MariaDB xếp `NULL` **đầu** trong `asc` ⇒ nếu 1 lịch có cả phiếu `scheduled_date=NULL` lẫn phiếu có ngày, phiếu NULL bị chọn trước; production PM Work Order thường set `scheduled_date` khi `assign_technician`; nếu dữ liệu thực NULL nhiều, mở CR sau đổi anchor sang `due_date` (luôn set). Round này giữ `scheduled_date asc` đúng AC.
- **Enrich = 1 BATCH query (KHÔNG N+1 — INVARIANT hiệu năng):** sau khi có `rows` (≤ `limit` lịch), gom `sched_names = [r["name"] for r in rows]`; 1 lần `PMWorkOrderRepo.list(filters=[["pm_schedule","in",sched_names], ["status","in", list(NEXT_WO_OPEN_STATES)]], fields=["name","pm_schedule","status","scheduled_date"], order_by="scheduled_date asc, name asc", page_size=<đủ lớn>)`; duyệt 1 vòng dựng `first_by_sched: dict[str,dict]` = **phiếu ĐẦU TIÊN gặp cho mỗi `pm_schedule`** (vì đã sort asc ⇒ first == gần hạn nhất); gán `r["next_wo_ref"] = wo["name"]`, `r["next_wo_status"] = wo["status"]` nếu có, else cả 2 = `None`. **TUYỆT ĐỐI KHÔNG** query trong vòng `for r in rows` (N+1). `rows` rỗng ⇒ bỏ qua batch (gán None cho mọi row — thực ra vòng rỗng).
- **Vị trí trong service:** enrich `next_wo_*` chạy **sau** enrich `asset_name`/`days_left` và **trước** `truncation_meta`/`return`. `total`/`truncated` (CR-46) tính trên PM **Schedule** filter — KHÔNG đổi (enrich WO không ảnh hưởng count lịch).

#### CR-46 — Hợp đồng TRUNG THỰC khi cắt (`total` + `truncated`)

> **Quyết định: đối xứng CR-43 (inbox IMM-00 §III.22) + CR-47 (competencies IMM-06 C.2) — cùng khối "hợp đồng TRUNG THỰC khi cắt danh sách mobile".** `getDuePmSchedules` cắt ở `page_size=int(limit)` (default 50) NHƯNG KHÔNG cho client biết còn bao nhiêu lịch chưa hiển thị → KTV tưởng đã xem hết danh sách nhắc-việc. **Slice contract (OAS + shape-guard `test_mobile_oas` đã verify `Ran 893 OK`) đóng ở Bước-2 (BA); application code (`services/imm08.py`) = [BE] Bước-4** (cùng build service `get_due_pm_schedules`).

| Khóa | Kiểu | Ngữ nghĩa |
|---|---|---|
| `total` | int ≥ 0 | **COUNT THẬT** trên ĐÚNG filter-set (`status=='Active'` ∧ `next_due_date is set` ∧ `<= threshold`) **TRƯỚC khi cắt** `limit` — `PMScheduleRepo.count(filters)` cùng predicate (KHÁC `frappe.db.count` phải áp CÙNG filter). **KHI `truncated==0` thì `total == len(items)`.** |
| `truncated` | int ∈ {0,1} | `= int(len(items) >= limit ∧ total > limit)`. **int, KHÔNG bool/None** (parity CR-01). FE hiện dải "đang xem một phần" (KHÔNG nêu con số). |

- **ADDITIVE-OPTIONAL:** `DuePmScheduleListPage` giờ **4 khóa** `{items, threshold_days, total, truncated}` nhưng `required` **GIỮ `[items, threshold_days]`** byte-identical (backward-compat). `additionalProperties:false` GIỮ.
- **AC4 test (BE Bước-4):** seed 2 lịch PM due → `limit=1` ⇒ `len(items)==1 ∧ total==2 ∧ truncated==1`; `limit=100` ⇒ `truncated==0 ∧ total==len(items)`.
- **§BE task:** trong `get_due_pm_schedules` @`services/imm08.py`: sau khi build `filters` (3-clause) → `total = PMScheduleRepo.count(<same filters dict>)`; sau khi có `rows` → `truncated = int(len(rows) >= int(limit) and total > int(limit))`; `return {"items": rows, "threshold_days": int(days), "total": total, "truncated": truncated}`. ⚠️ `count` PHẢI dùng CÙNG filter-set với `list` (nếu `BaseRepository.count` chỉ nhận dict AND-filter, chuyển 3-clause list sang dict `{status:'Active', next_due_date:['<=',threshold]}` + guard is-set — hoặc `frappe.db.count` với filter tương đương; KHÔNG đếm lệch predicate). **COUNT vô-điều-kiện chấp nhận** (1-nguồn, 1 query rẻ — KHÁC inbox 4-nguồn zero-cost CR-43).

- **Always**: `additionalProperties:false` (closed) ở CẢ 3 schema: `DuePmScheduleListEnvelope` (`required[success,data]`, `success.enum[true]`, `data=$ref DuePmScheduleListPage`), `DuePmScheduleListPage` (`required[items,threshold_days]` — **CR-46: +`total`/`truncated` ADDITIVE-OPTIONAL, 4 key tổng, required GIỮ 2 key**), `DuePmScheduleListItem` (`required[name]`, **10 field khác optional — CR-45 +`next_wo_ref`/`next_wo_status`**). `days_left` = `type:integer` NON-nullable. `next_wo_ref`/`next_wo_status` = `type:string` **`nullable:true`** (0 phiếu mở = ca hợp lệ → null). `total`/`truncated` = `type:integer` (`truncated` `enum[0,1]`).
- **Always**: path vào `_MVP_BUSINESS_PATHS` (401/403 symmetry) **VÀ** `_MVP_LIST_ENVELOPE` (`→ DuePmScheduleListEnvelope`) ⇒ 2 set tự +1 (test so SET, KHÔNG literal).
- **Never**: KHÔNG thêm `pagination` vào `DuePmScheduleListPage` (service KHÔNG `paginate()` surface — chỉ limit-cap; thêm = payload KHÔNG khớp closed-schema). KHÔNG khai `days_left`/`next_due_date` `nullable:true` (filter is-set ⇒ dead-branch `else None`). KHÔNG khai `last_pm_date` NON-nullable (CÓ THỂ NULL thật). **KHÔNG khai `next_wo_ref`/`next_wo_status` NON-nullable** (lịch 0 phiếu mở là ca phổ biến hợp-lệ → null; NON-nullable = codegen reject-valid → CRASH). **KHÔNG enrich `next_wo_*` bằng N+1** (1 query/lịch = anti-pattern hiệu năng — PHẢI 1-batch `pm_schedule IN [...]`). KHÔNG khai bất kỳ field nào `integer enum[0,1]`/`boolean` — 0 Check field ở item này ⇒ **MIỄN CR-01 int-vs-bool**. KHÔNG nhồi field financial. KHÔNG thêm `mine`/`page`/`filters` param. KHÔNG thêm slot 403 dual-shape (cap-403 KHÔNG reachable).

**403 = SINGLE-SHAPE `Forbidden` DISPATCHER-ONLY (KHÔNG cap-403 — mirror `getDueCalibrations`):**
- *dispatcher-403* (guest/no-token) trip TRƯỚC `handle()` (bare `@whitelist` no `allow_guest`) → HTTP-403 THẬT (`FrappeRawError`) ⇒ slot `403` = `$ref #/components/responses/Forbidden`.
- **KHÔNG có in-handler cap-403**: handler `get_due_pm_schedules` **KHÔNG gọi `rbac.require`** ⇒ KHÔNG có nhánh `Error.http_status==403` in-handler. Mirror `getDueCalibrations`/`listTransfers` (bare-@whitelist read dispatcher-only 403, ADR-043 family).
- **200-oneOf `Error` branch = `handle()`-wrapper DEFENSIVE** (catch-all): service `get_due_pm_schedules` **KHÔNG** `frappe.throw`/`nthrow`/`ServiceError` (query-only, KHÔNG raise domain) ⇒ 0 domain `Error.http_status` reachable; nhánh `Error` khai để đối-xứng `handle()`-contract + thỏa `_MVP_LIST_ENVELOPE` sweep. Mọi lỗi bất-thường vẫn ARRIVE **HTTP-200 + Error body** (Decision-B, KHÔNG status-line, KHÔNG raise→4xx).

#### ADR-IMM08-DUEPM — `getDuePmSchedules` read-list KHÔNG-pagination `{items, threshold_days}` nguồn `PM Schedule.next_due_date` + `DuePmScheduleListItem` 9-prop + `days_left` signed non-nullable + `last_pm_date` nullable + 403 dispatcher-only

- **Status**: Accepted · **Date**: 2026-07-15
- **Context**: Màn "Nhắc việc" (F8) có 2 nửa — Hiệu chuẩn (✅ `getDueCalibrations` LIVE) và **PM (nửa CHẾT)**. Cần list LỊCH PM (PM Schedule) sắp/quá hạn ĐỐI XỨNG `getDueCalibrations`, NHƯNG nguồn KHÁC: PM dùng `PM Schedule.next_due_date` (SoT lịch PM, BR-08-03), calib dùng `AC Asset.next_calibration_date`. `get_due_pm_schedules` **CHƯA tồn tại** (khác `getDueCalibrations` đã LIVE) ⇒ Bước-4 BE build service + handler MỚI (NEW `.py` → reload PENDING USER).
- **Decision**: (1) BE build 1 service `get_due_pm_schedules(days=30, limit=50)` + 1 handler bare `@frappe.whitelist()` VERBATIM mirror `imm11.get_due_calibrations`; return-shape **`{items, threshold_days}` EXACT 2-key rows-key `items`** (KHÔNG `data` — điểm KHÁC `list_schedules`). (2) Filter 3-clause: `status=='Active'` (LOẠI Paused/Suspended — PMScheduleStatus 3-state, positive-form rõ hơn `not in`) + **`next_due_date is set`** (NULL-coerce guard) + `next_due_date <= threshold`; `order_by next_due_date asc`; `page_size=limit`. (3) Curate 1 path GET (**tag `pm`**), 2 typed query-param INLINE `days`/`limit`, 3 schema CLOSED: `DuePmScheduleListItem` `req[name]` EXACT 9-prop (7 Repo-field ∪ `asset_name` enrich ∪ `days_left` derive) · `DuePmScheduleListPage` `req[items,threshold_days]` NO-pagination · `DuePmScheduleListEnvelope`. `days_left`/`next_due_date` NON-nullable; `last_pm_date`/`responsible_technician` nullable. 403 SINGLE-SHAPE dispatcher-only. Path 84→85.
- **Alternatives (loại)**: (a) nguồn `AC Asset.next_pm_date` thay `PM Schedule.next_due_date` → SAI SoT: `next_pm_date` là rollup cache trên Asset (BR-08-03 mirror), nhưng "Nhắc việc" cần TỪNG LỊCH PM (1 asset multi-schedule Quarterly+Annual) ⇒ phải liệt-kê PM Schedule, KHÔNG asset-rollup; (b) filter `["status","not in",["Paused","Suspended"]]` → tương-đương nhưng kém-rõ (3-state enum ⇒ positive `=="Active"` an-toàn hơn nếu thêm state tương-lai); (c) BỎ guard `["next_due_date","is","set"]` → Frappe render `ifnull(next_due_date,'0001-01-01') <= threshold` ⇒ lịch chưa-set-ngày LỌT filter, sort ASC lên đầu, lấp `limit`, đẩy lịch overdue thật khỏi list (SAI KPI — mirror bẫy `get_due_calibrations`); (d) thêm `pagination` parity `PmScheduleListEnvelope` → payload `{items, threshold_days}` KHÔNG khớp closed-schema; (e) `days_left` `nullable:true`/`enum[0,1]`/`boolean` → dead-branch/sai-kiểu (quantity signed ≠ flag, mất độ-lớn quá-hạn); (f) `last_pm_date` NON-nullable → codegen reject-valid row lịch chưa-chạy-PM (`last_pm_date=NULL` hợp-lệ) → CRASH; (g) scope `mine`/`responsible_technician` server-side → task chốt mirror `getDueCalibrations` (bare, all-role, 0 scope); FE lọc client-side theo field `responsible_technician` (đã có trong row) — mở CR sau nếu cần server-scope.
- **Consequences**: **+1 service +1 handler +1 path +3 schema** (KHÁC `getDueCalibrations` CONTRACT-ONLY — đây có `.py` MỚI). NEW `.py` ⇒ **worker reload = HARD-STOP USER** (`bench run-tests` fresh-load vẫn xanh; 0 `bench migrate`; 0 commit). Bộ list-read PM nay 2 shape: `listPmSchedules` (paginated `data[]+pagination`, CRUD toàn-tập) / **`getDuePmSchedules` (KHÔNG pagination `{items,threshold_days}`, cửa-sổ due, `days_left` signed)** — 2 view CÙNG DocType `PM Schedule`, KHÁC mục-đích. ĐỐI XỨNG hoàn-chỉnh nửa-Calib (§0.1.9 IMM-11): màn "Nhắc việc" mobile đủ 2 nửa.
- **Self-Correction (grounding)**: task ghi field-set/`days_left else-None` — grounding THẬT `services/imm08.py`: `PMScheduleStatus.ACTIVE` @`:228`, `list_schedules` enrich `asset_name` pattern @`:1326-1327`, imports `add_days`/`date_diff` @`:9`. `getDueCalibrations` source-of-truth pattern @`services/imm11.py:1393-1421`. Field names khớp `pm_schedule.json` (asset_ref/pm_type/status/next_due_date/last_pm_date/responsible_technician — KHÔNG `asset`/`asset_code`).

> **Acceptance contract (chốt cho BE/Test — Bước 4)**:
> **(1) BE `.py` (NEW — worker reload PENDING USER):** service `assetcore/services/imm08.py::get_due_pm_schedules(days=30, limit=50)` trả `{"items": rows, "threshold_days": int(days)}` (rows-key `items`) — filter 3-clause `[status="Active", next_due_date is set, next_due_date<=add_days(today,days)]`, `order_by next_due_date asc`, `page_size=int(limit)`, enrich `asset_name`, derive `days_left=date_diff(next_due_date,today)` signed; handler `assetcore/api/imm08.py::get_due_pm_schedules` bare `@frappe.whitelist()` → `handle(svc.get_due_pm_schedules, int(days), int(limit))`.
> **(2) YAML `84 → 85` path / `85` operationId** (`getDuePmSchedules` mới, UNIQUE camelCase `^[a-z][a-zA-Z0-9]*$`, tag `pm`, method GET, 0 dangling `$ref`, `safe_load` OK); 2 typed query-param INLINE `days`+`limit` (`integer`, default `30`/`50`, `in:query`, `required:false`); 200 = response oneOf [`DuePmScheduleListEnvelope`, `Error`]; slot `{200,401,403}` (`401 Unauthorized401` + **`403 Forbidden` SINGLE-SHAPE dispatcher-only** — description GHI RÕ bare-@whitelist 0 cap-403). **+3 schema CLOSED** (`additionalProperties:false`): `DuePmScheduleListItem` `req[name]` EXACT 9-prop {name,asset_ref,asset_name,pm_type,status,next_due_date,last_pm_date,responsible_technician,days_left} — `days_left` `integer` NON-nullable, `next_due_date` `format:date` NON-nullable, `last_pm_date` `format:date` **nullable:true**, `responsible_technician` nullable:true, 0 Check integer-enum · `DuePmScheduleListPage` `req[items,threshold_days]` **CHÍNH XÁC 2-key KHÔNG `pagination`** · `DuePmScheduleListEnvelope` `{success:enum[true], data:$ref DuePmScheduleListPage}`; tái-dùng `Unauthorized401`/`Forbidden`/`Error`; naming-guard `DuePmSchedule*` ∩ (`PmSchedule*`∪`PmWorkOrder*`) == ∅.
> **(3) Guard XANH THẬT `bench --site miyano run-tests` (KHÔNG false-green — 'Ran N OK' in ra):** `test_mobile_oas` class RIÊNG `TestMobileDuePmSchedulesContract a..g` (+7 TC ĐỐI XỨNG `TestMobileDueCalibrationsContract`: a=path+opId+GET+tag-pm, b=2-typed-param days/limit integer-default-required:false, c=Item-9-field-VERBATIM-closed-0-extra, d=`days_left`+`next_due_date` NON-nullable ∧ `last_pm_date`+`responsible_technician` nullable (anti dead-branch + anti false-non-null), e=`DuePmScheduleListPage`-EXACT-2-key-NO-pagination, f=200-oneOf[Env,Error] + Envelope-closed{success:[true],data}, g=naming-guard + **live-signature parity** `inspect.signature(imm08.get_due_pm_schedules)=={days,limit}`); anchors bump: `_EXPECTED_TEST_COUNT` **767 → 774** (+7) · path/opId + `c5`/`_PARITY_BUSINESS_PATHS` **73 → 74** · `_MVP_LIST_ENVELOPE` **12 → 13** (thêm `_DUE_PM_SCHEDULES_PATH: "#/components/schemas/DuePmScheduleListEnvelope"` — ĐỊNH NGHĨA path-const mới) · membership `_MVP_BUSINESS_PATHS` (401/403 symmetry tự +1). `test_mobile_docset` **Ran N OK** (reconcile `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` **767 → 774** + `_GUARD_SUITE_SUM` **910 → 917** + `_MOBILE_OAS_TOTAL` **936 → 943**). `test_imm08` **+BE-unit TDD** (RED-trước do handler∄): happy-path 200 `{items,threshold_days}` 9-field · NULL-coerce guard (lịch `next_due_date=NULL` KHÔNG lọt) · status-filter (Paused/Suspended loại) · `days_left` signed (asset overdue → âm) · empty-window (days=0 → chỉ ≤ hôm nay). ⚠️ Baseline **84/767/73/12/910/936 grounded @source 2026-07-15** — **BE grep-verify @source TRƯỚC bump** (đa-phiên race, per multi_session_concurrency).
> **(4) Đếm đồng bộ & HARD-STOP:** path/opId 84→85; MỌI anchor `test_mobile_oas`/`test_mobile_docset` bump KHỚP (liệt kê ở (3)); **0 `bench migrate`**; NEW `.py` ⇒ **worker reload = PENDING USER** (KHÔNG tự chạy; KHÔNG curl-verify LIVE — LL-DEPLOY-07). ADR-MOBILE mirror: [`docs/mobile/ADR-MOBILE-054.md`](../mobile/ADR-MOBILE-054.md). RED-before/GREEN-after cho MỌI TC mới. Working-tree để USER review — **KHÔNG git commit/push/merge**.

#### ADR-IMM08-NEXTWO — `getDuePmSchedules` bồi `next_wo_ref`/`next_wo_status` (deep-link phiếu từ màn "Nhắc việc"), 1-batch, ADDITIVE 0-breaking

- **Status**: Accepted · **Date**: 2026-07-24 · **Đề mục**: vòng 3 CR-45a
- **Context**: `getDuePmSchedules` (§0.1.5) liệt-kê LỊCH PM due nhưng KHÔNG chỉ phiếu (PM Work Order) đang chờ ⇒ KTV không mở thẳng vào phiếu được. Cần bồi con-trỏ tới phiếu MỞ gần hạn nhất mà **KHÔNG breaking** contract 9-field + `threshold_days`/`total`/`truncated` hiện hữu, và **KHÔNG N+1**.
- **Decision**: (1) Bồi **đúng 2 field** `next_wo_ref` (PK phiếu MỞ gần hạn nhất, `order scheduled_date asc` + `name asc` tie-break) + `next_wo_status` (status phiếu đó); cả 2 `= null` nếu lịch 0 phiếu MỞ. (2) "Phiếu MỞ" = hằng SSoT `NEXT_WO_OPEN_STATES = {Open, Overdue, In Progress, Pending–Device Busy}` (non-terminal ∧ non-halted). (3) Enrich bằng **1 batch** `PMWorkOrderRepo.list(filters=[["pm_schedule","in",sched_names],["status","in",list(NEXT_WO_OPEN_STATES)]], fields=[name,pm_schedule,status,scheduled_date], order_by="scheduled_date asc, name asc")` → dựng `first_by_sched` (first == gần hạn nhất do đã sort). (4) OAS 2 field `type:string nullable:true`, `required` GIỮ `[name]`, `additionalProperties:false` GIỮ.
- **Alternatives (loại)**: (a) query WO trong vòng `for r in rows` → **N+1** (loại — hiệu năng); (b) đưa `Halted–Major Failure` vào "phiếu MỞ" → SAI: đã escalate CM, không còn PM chờ (loại); (c) `order due_date asc` thay `scheduled_date` → AC2 chốt `scheduled_date` (giữ AC; NULL-edge ghi *(Cần khảo sát)*); (d) trả **danh sách** phiếu thay 1 con-trỏ → over-fetch, màn nhắc-việc chỉ cần 1 deep-link (loại — mở CR sau nếu cần); (e) NON-nullable → crash codegen khi lịch 0 phiếu (loại).
- **Consequences**: `DuePmScheduleListItem` 9→**11 prop** (ADDITIVE, required GIỮ `[name]`). +1 batch query/call (KHÔNG N+1). `total`/`truncated` (CR-46) đếm trên **PM Schedule** KHÔNG đổi. **CONTRACT-ONLY ở Bước-2** (OAS + shape-guard `test_mobile_oas` do BA chốt); enrich `.py` (`services/imm08.py`) = **[BE] Bước-4** — NEW logic ⇒ worker reload PENDING USER.

> **Acceptance contract CR-45 (chốt cho BE/Test — Bước 4):**
> **(1) BA doc-layer (ĐÓNG Bước-2):** OAS `DuePmScheduleListItem` +2 prop `next_wo_ref`/`next_wo_status` (`string` `nullable:true`, description CR-45), desc «9 field»→«11 field», `required[name]` + `additionalProperties:false` GIỮ. Shape-guard `test_mobile_oas::TestMobileDuePmSchedulesContract` cập nhật `_DUE_PM_SCHEDULE_ITEM_FIELDS` 9→11 + `len(props)==11` + assert 2 field mới `type:string ∧ nullable:true`. **KHÔNG +TC method** (mở-rộng TC hiện có ⇒ `_EXPECTED_TEST_COUNT` GIỮ 893, `_MOBILE_OAS_TOTAL`/`_GUARD_SUITE_*` GIỮ). BA tự chạy `test_mobile_oas`+`test_mobile_docset` XANH.
> **(2) BE `.py` (Bước-4, worker reload PENDING USER):** trong `get_due_pm_schedules` (`services/imm08.py`): thêm hằng module `NEXT_WO_OPEN_STATES = frozenset({PMStatus.OPEN, PMStatus.OVERDUE, PMStatus.IN_PROGRESS, PMStatus.PENDING_BUSY})`; sau enrich `asset_name`/`days_left`, TRƯỚC `truncation_meta`: 1-batch WO-list theo `pm_schedule IN sched_names` ∧ `status IN NEXT_WO_OPEN_STATES`, `order_by "scheduled_date asc, name asc"`; dựng `first_by_sched`; gán `r["next_wo_ref"]`/`r["next_wo_status"]` (None nếu 0 phiếu). **PMWorkOrderRepo đã import** (dùng trong reschedule). `return` giữ nguyên 4 top-key.
> **(3) Guard XANH THẬT `bench --site miyano run-tests --module assetcore.tests.test_imm08` ('Ran N OK'):** cập nhật `test_due_pm_07_shape_and_row_fields` (`test_imm08.py:4206`) field-set 9→**11** (thêm `next_wo_ref`/`next_wo_status`); **+TC mới AC1/AC2** (class `TestDuePmSchedules`): lịch có 2 phiếu Open scheduled_date lệch → `next_wo_ref`==phiếu sớm nhất, `next_wo_status` khớp · lịch chỉ phiếu Completed/Cancelled → cả 2 null · lịch 0 phiếu → cả 2 null · lịch có Pending–Device Busy → lọt "phiếu MỞ". RED-before/GREEN-after. **0 N+1** (có thể assert số query nếu repo hỗ trợ).
> **(4) HARD-STOP:** 0 `bench migrate`; 0 commit; working-tree USER review; NEW `.py` reload = USER (`--preload`), KHÔNG curl-verify LIVE (LL-DEPLOY-07).

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
| `VALIDATION` | Input validation fail | `IMM08-CHECKLIST-EMPTY` (BR-08-19, bảng kiểm 0 mục) / `IMM08-CHECKLIST-IDX-UNKNOWN` (BR-08-20, idx payload lệch — OPTIONAL) / `IMM08-CHECKLIST-INCOMPLETE` / `IMM08-DURATION-REQUIRED` / `IMM08-STICKER-REQUIRED` / `IMM08-PHOTO-REQUIRED` / `IMM08-SOURCE-PM-REQUIRED` |
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
| `search` | string | ✗ | default `""`; free-text OR-LIKE trên `name` / `asset_code` / `asset_name` — case-insensitive, TOÀN tập mọi trang (xem "free-text search" + BR-08-17 dưới, CR-18). `""`/absent ⇒ hành vi list BYTE-IDENTICAL baseline. |
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

**Errors:** `INVALID_PARAMS` (filters JSON sai) · `FORBIDDEN` (403 **in-handler trên HTTP-200** — persona thiếu DocPerm `read` trên `PM Work Order`; xem BR-08-LISTSCOPE).

#### BR-08-LISTSCOPE — row-scope của danh sách PM WO (CHỐT 2026-07-25, INV-ROWSCOPE) 🟡 SPEC (BE/FE Bước-4)

> **SSoT quyết định:** [`ADR-IMM00-LIST-SCOPE.md` §8](../imm-00/ADR-IMM00-LIST-SCOPE.md) (D4–D7). **ĐỐI XỨNG VERBATIM** với `BR-09-LISTSCOPE` (IMM-09) — khác module/doctype/predicate-field, giống hệt cơ chế.
>
> **Bug gốc:** `BaseRepository.list` đếm `total` bằng `frappe.get_list` (permission-aware, `services/shared/filters.py:275-281`) nhưng lấy `rows` bằng `frappe.get_all` (`repositories/base.py:67-75`) = **KHÔNG** áp `permission_query_conditions`. Với `pm_work_order_query` (`permissions.py:123-131`, scope `assigned_to = <user>` cho technician + vendor) ⇒ KTV **thấy phiếu PM của người khác** và header "Tổng N" ≠ số dòng.
>
> | Ràng buộc | Nội dung |
> |---|---|
> | Predicate SSoT | `PM Work Order`.`assigned_to` cho `_TECHNICIAN_ROLES` + `Vendor Engineer` — **GIỮ NGUYÊN, KHÔNG sửa `pm_work_order_query`** (D4). `AC Asset` read-all (D1) KHÔNG áp cho phiếu công việc. |
> | Chế độ | `services/imm08.py::list_work_orders` → `PMWorkOrderRepo.list(..., scope="user")`; nhánh chip LIVE `overdue_live=1` (`_list_pm_overdue_live` → `_fetch_all_pm_rows`) cũng `scope="user"` |
> | Bất biến | **`pagination.total == len(data.data)`** khi `total ≤ page_size`, cho MỌI persona; 0 phiếu `assigned_to` người khác trong list của KTV |
> | Card ↔ drill (D7) | `count_overdue_pm()` (`services/imm08.py:287`) đổi `PMWorkOrderRepo.count` → `count_with_or("PM Work Order", filters, None)`. Docstring hàm này tự khẳng định *"KPI == drill-down `_normalize_filters(overdue=1)`, KHÔNG divergence"* — drill nay `user`-scoped nên card global sẽ **phá chính lời khẳng định đó** (và phá INVARIANT BR-08-12 card==drill). |
> | Giữ `system` (D6) | `get_calendar` (`imm08.py:1373` — **plan-centric**: lịch PM toàn viện phục vụ điều phối ca trực, đã có param `technician` để tự thu hẹp) · `get_dashboard_stats` tile + trend (`:1404`, `:1456` — KPI tổng hợp, không phơi danh tính từng phiếu). **Read-only, không nút hành động, KHÔNG dùng làm căn cứ cấp quyền.** Ratify lại = [ADR §8.10 B4] (cần USER). |
> | Lỗi quyền | `frappe.get_list` raise `PermissionError` khi thiếu DocPerm `read` → service chuyển `ServiceError(FORBIDDEN, http_status=403)` → `handle()` trả **HTTP-200 + Error envelope** (BR-00-ROWSCOPE-403). KHÔNG 500, KHÔNG list rỗng giả. Persona ảnh hưởng trên `PM Work Order`: `Calibration User`, `Corrective User`, `Repair User`, **`Vendor Engineer`** (không có DocPerm read — verify `pm_work_order.json` permissions block). Phân biệt với **dispatcher-403** (guest/no-token). |
> | Không nới / không over-block | Senior (`PM Manager`/Super Admin/Auditor) vẫn thấy ĐỦ; Vendor vẫn isolated (D2). **TUYỆT ĐỐI KHÔNG nới DocPerm** để chữa test đỏ (ADR §8.7). |
>
> **Quan hệ với `mine`:** `mine=1` là **filter ứng-dụng** (thu hẹp cho senior/QA), row-scope là **hàng rào bảo mật**. Với KTV thì `pm_work_order_query` đã tự scope ⇒ `mine` thừa nhưng vô hại (AND idempotent). A3/A5 của acceptance yêu cầu KTV **KHÔNG truyền `mine`** mà vẫn phải 0 phiếu người khác — chứng minh hàng rào nằm ở row-scope, KHÔNG ở `mine`.
>
> **BE Bước-4:** `repositories/base.py` (`scope` param) · `services/shared/filters.py` (`count_ignore_permissions`) · `services/imm08.py` (5 call site `PMWorkOrderRepo.list` khai `scope` tường minh + `count_overdue_pm` permission-aware + `PermissionError`→`ServiceError`) · test `assetcore/tests/test_rowscope_invariant.py` (TC-00-RS-06). **0 delta OpenAPI mobile** (shape/param KHÔNG đổi — chỉ đổi TẬP row theo persona).
>
> **⚠️ CẢI CHÍNH sau thực thi (2026-07-25 — ADR [§8.3b](../imm-00/ADR-IMM00-LIST-SCOPE.md), chờ [BA] ratify hậu kiểm):**
> 1. **`scope="system"` KHÔNG còn nghĩa "bỏ mọi kiểm tra quyền".** Nó chỉ bỏ **ROW-scope**; **DocPerm `read` cấp vai-trò VẪN được gate** (`assert_doctype_read_permission`). Trước cải chính, `Repair User` (0 DocPerm read `PM Work Order`) gọi `get_pm_calendar` nhận **lịch PM của người khác kèm `assigned_to`** = rò dữ liệu (OWASP A01). ⟹ `get_pm_calendar` / `get_pm_dashboard_stats` nay trả **403 envelope** cho persona thiếu DocPerm read.
> 2. **`count_overdue_pm` permission-aware tạo bề mặt raise MỚI** trên `get_dashboard_stats` (không có wrapper) ⇒ **500 câm**. Khắc phục: decorator **`@rowscoped`** dán cho MỌI entrypoint đọc của IMM-08 (`get_calendar`, `get_dashboard_stats`, `get_asset_history`, `list_schedules`, `get_due_pm_schedules`, `list_templates`) — trước đó CHỈ `list_work_orders` được bọc, nên `get_due_pm_schedules` (bare `@whitelist`) cũng đang ném `PermissionError` trần.
> 3. Guard chống tái phát: `tests/test_rowscope_docperm_gate.py` (4 TC hành vi) + `tests/test_rowscope_scope_guard.py` (3 guard AST + 3 contract repo).

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
- **INVARIANT count==rows (INV-08-LIST):** `BaseRepository.list` (`repositories/base.py:65-75`) đếm `count_with_or(DOCTYPE, filters, or_filters)` + lấy `frappe.get_all(DOCTYPE, filters=filters, or_filters=or_filters)` dùng **CÙNG** `filters` dict đã có `assigned_to` **VÀ CÙNG** `or_filters` (khi có `search` — xem BR-08-17) ⇒ `pagination.total == len(data.data)` khi `mine=1` (và khi kèm `search`). Khi KHÔNG có `search`, `or_filters=None` ⇒ count/rows byte-identical baseline (`count_with_or` chạy `frappe.get_list(limit_page_length=0)` — permission-query-aware, KHÔNG phải `frappe.db.count` thuần). KHÔNG đếm trên dict khác (chống count-vs-rows drift — memory `asset_list_count_drill_technician`).
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

#### list_pm_work_orders — free-text `search` (CR-18) ✅ SPEC (BE/FE Bước-4)

> **Mục tiêu (CR-18 — KTV không bỏ sót phiếu ở trang sau):** ô "Tìm phiếu" trên `PMWorkOrderListView` (web) hiện lọc **client-side chỉ trang đã tải** (`filteredWOs` — `06_Frontend_Design`) → KTV gõ mã thiết bị mà phiếu nằm ở trang 2+ ⇒ "không thấy" (search-trap). Vòng này chuyển tìm kiếm sang **SERVER** — OR-LIKE trên `name` (mã lệnh PM) / `asset_code` (mã thiết bị) / `asset_name` (tên thiết bị), tính trên **TOÀN tập** mọi trang.

**Param mới:** `search` (string, default `""`, `in:query`) — bổ sung vào `list_pm_work_orders(filters, mine, page, page_size)` → `list_pm_work_orders(filters, mine, search, page, page_size)`.

| `search` | Hành vi | or_filters sinh ra |
|---|---|---|
| `""` / absent | **UNCHANGED** (byte-identical baseline) — KHÔNG dựng `or_filters`; web-FE list KHÔNG đổi khi trống | `or_filters = None` |
| non-empty | **OR-LIKE toàn tập** — chỉ phiếu có `name` HOẶC `asset_code` HOẶC `asset_name` chứa term (case-insensitive), TOÀN tập mọi trang | xem BR-08-17 |

**BR-08-17 (free-text search — application filter, AND-combine, KHÔNG nới quyền):**
- **Điểm inject:** discrete param `search` → API-layer (`api/imm08.py::list_pm_work_orders`) inject `f["search"] = search.strip()` **CHỈ khi** non-empty, **SAU** `apply_vendor_scope` + `mine`-inject (đối xứng cách `mine` inject `assigned_to`). Trống ⇒ KHÔNG đụng `f` ⇒ byte-identical.
- **Dịch sang `or_filters` @service-layer:** `services/imm08.py::list_work_orders` gọi SSoT `pop_search(base, searchable_fields=["name"], link_search={"asset_ref": ("AC Asset", ["asset_code", "asset_name"])})` **TRƯỚC** `_normalize_filters` (nếu `search` lọt xuống `frappe.get_all` → `Unknown column 'tabPM Work Order.search'`). `pop_search` trả:
  - `["name", "like", "%<esc>%"]` — LIKE trực tiếp cột PK phiếu PM.
  - `["asset_ref", "in", <AC Asset.name khớp>]` — resolve 1 lần: AC Asset có `asset_code` LIKE `%<esc>%` **HOẶC** `asset_name` LIKE `%<esc>%` **HOẶC** `name` LIKE `%<esc>%` (cap `_LINK_LOOKUP_LIMIT=500`). `asset_code`/`asset_name` nằm trên **AC Asset** (link qua `asset_ref`), KHÔNG phải cột PM WO ⇒ bắt buộc link-lookup, KHÔNG LIKE thẳng.
- **Escape LIKE-metachar (SSoT `escape_like_term`):** term đi qua `escape_like_term` (imm00 SSoT / ADR-IMM00-SEARCH-ESCAPE) — `%`→`\%`, `_`→`\_` — TRƯỚC khi bọc `%…%`, áp NHẤT QUÁN cho CẢ `name` LIKE LẪN link-lookup AC Asset. `search='%'`/`'_'` ⇒ khớp literal (KHÔNG match toàn bảng); `search='%%%%%'` ⇒ KHÔNG LIKE-backtracking DoS. `pop_search` (shared) chịu trách nhiệm escape — imm08/imm09 KHÔNG tự ráp `.replace`.
- **AND-combine (KHÔNG nới quyền):** Frappe kết hợp `filters` (AND) với `or_filters` (OR) thành `filters AND (or_filters…)`. ⇒ `search` AND với `status`/`asset_ref`/virtual-key + `mine`(`assigned_to==user`) + vendor-scope(`asset_ref IN [asset của vendor]`). KTV `mine=1` và Vendor **KHÔNG** thấy phiếu ngoài scope dù khớp `search` (vendor/mine filter luôn AND, `search` chỉ THU HẸP). Link-lookup AC Asset chạy `ignore_permissions=True` chỉ để **resolve id text-match**; phạm vi phiếu VẪN do `filters` + `permission_query`/vendor quyết định ⇒ KHÔNG rò.
- **INVARIANT count==rows (INV-08-LIST, giữ nguyên):** `or_filters` (gồm id link đã resolve) dựng **1 lần** ở `list_work_orders`, truyền vào `BaseRepository.list` → thread **CÙNG** list cho `count_with_or` (`frappe.get_list(limit_page_length=0)`) LẪN `frappe.get_all` ⇒ `pagination.total == số phiếu thực khớp search` trên MỌI trang (test paginate `page_size` nhỏ vẫn đúng tổng). KHÔNG resolve id link riêng cho count vs rows (chống drift).
- **⚠ VERIFY BE Bước-4 (bất đối xứng PQC rows-vs-count — KHÔNG do CR-18 sinh, nhưng acceptance "count==rows"+"vendor no-leak" bắt phải đúng):** `BaseRepository.list` lấy rows bằng `frappe.get_all` (**KHÔNG** áp `permission_query_conditions`) trong khi `count_with_or` đếm bằng `frappe.get_list` (**CÓ** áp `pm_work_order_query` = `assigned_to==user` cho persona vendor/KTV). Với persona **read-all** (senior/auditor/other → pqc trả `""`) 2 path khớp ⇒ count==rows. Với **vendor**: `apply_vendor_scope` inject `asset_ref IN […]` (KHÁC predicate pqc `assigned_to`) → nếu có phiếu trên asset của vendor NHƯNG `assigned_to` = KTV khác thì `get_all` (rows) đếm phiếu đó còn `get_list` (count) loại ⇒ **count < rows + rò phiếu ngoài `assigned_to`** — latent baseline, `search` KHÔNG che/khoét thêm nhưng test TC-PM-SEARCH-05/02 SẼ phơi ra. **BE phải chốt**: hoặc rows cũng đi `frappe.get_list` (áp pqc, đối xứng count), hoặc canh explicit-filter khớp pqc; **thêm regression count==rows cho persona vendor** (search rỗng LẪN có search). KHÔNG mở rộng scope CR-18 để "vá" — nếu là bug baseline, tách finding riêng cho orchestrator.
- **Nhánh live-membership (`overdue_live`):** `search` pop **TRƯỚC** rẽ nhánh live; `or_filters` forward vào `_fetch_all_pm_rows`/`_list_pm_overdue_live` để chip "Quá hạn" + `search` compose đúng, count==rows giữ trong tập ĐÃ LỌC live. (`_fetch_all_pm_rows` nhận thêm `or_filters`.)
- **Recall cap [ROADMAP]:** link-lookup cap 500 asset khớp → term quá rộng (>500 asset match) chỉ resolve 500 id ⇒ count==rows VẪN giữ (count & rows dùng chung id đã cap) nhưng recall giảm. Chấp nhận ở scale hiện tại (~1.4k asset); term-quá-rộng streaming = `[ROADMAP]` (đối xứng ADR-IMM00-LIST-SCOPE §4b).

**Boundaries:**
- **Always:** inject `f["search"]` @api CHỈ khi non-empty (giữ byte-identical baseline); dịch → `or_filters` qua `pop_search` (shared SSoT) TRƯỚC `_normalize_filters`; escape term qua `escape_like_term`; dựng `or_filters` 1 lần + thread CÙNG list cho count & rows; `search` AND với vendor-scope/`mine`/`status`; forward `or_filters` vào nhánh live.
- **Never:** LIKE thẳng `asset_code`/`asset_name` trên `tabPM Work Order` (2 cột đó nằm trên AC Asset — sẽ `Unknown column`); ráp `%{term}%` KHÔNG escape (mở wildcard-injection + DoS); resolve id link riêng cho count vs rows (vỡ count==rows); dùng `search` để BYPASS vendor/`mine` (nới quyền); đổi hành vi khi `search` trống (vỡ web-FE regression=0); thêm endpoint `search_pm_work_orders` mới (+1 path — dùng param, KHÔNG endpoint riêng).

#### ADR-IMM08-SEARCH-01: `search` discrete param + `pop_search`/`escape_like_term` SSoT (vs client-filter, vs raw `%term%`, vs endpoint riêng)

- **Status**: Accepted — Date 2026-07-10. Đối xứng CM `ADR-IMM09-SEARCH-01` + tái dùng `ADR-IMM00-SEARCH-ESCAPE`.
- **Context**: FE lọc client-side chỉ trang đã tải (search-trap) → KTV bỏ sót phiếu trang sau. `asset_code`/`asset_name` nằm trên AC Asset (link `asset_ref`), KHÔNG phải cột PM WO. Ràng buộc: count==rows, byte-identical baseline khi trống, KHÔNG nới quyền, chống wildcard-injection/DoS.
- **Decision**: 1 discrete query-param `search` (default `""`) → inject `f["search"]` @api khi non-empty → `pop_search` @service dịch sang `or_filters` (parent `name` LIKE + link-lookup AC Asset `asset_code`/`asset_name`/`name`) đã escape qua `escape_like_term`; `BaseRepository.list` thread `or_filters` chung cho `count_with_or`+`get_all`.
- **Alternatives**: (A) giữ lọc client-side → search-trap không sửa được (chỉ trang tải) → loại. (B) raw `f"%{term}%"` KHÔNG escape → wildcard-injection (`_`/`%` match-all) + LIKE-DoS → loại. (C) endpoint riêng `search_pm_work_orders` → +1 path, nhân đôi pagination/enrich/scope surface → loại. (D) full-text index (MATCH…AGAINST) → cần schema migration + đổi count semantics → `[ROADMAP]`, loại khỏi vòng này.
- **Consequences**: blast-radius = 1 param @api + 1 nhánh `pop_search` @service + forward `or_filters` vào nhánh live; count==rows giữ; backward-compat khi trống; tái dùng `pop_search`/`escape_like_term` (mở rộng `pop_search.link_search` nhận **list** display-field — dùng chung imm09). Đánh đổi: recall cap 500 khi term quá rộng (`[ROADMAP]` streaming); `search` là filter ứng-dụng (bảo mật read vẫn do DocPerm/permission_query + vendor-scope).

> **DELTA vòng này (CR-18, so với bản trước):** (1) Request-table thêm param `search`; (2) section "free-text search" + BR-08-17 + ADR-IMM08-SEARCH-01 mới; (3) làm rõ INV-08-LIST khi kèm `or_filters`. **BE Bước-4 delta** (KHÔNG thuộc file doc này): `api/imm08.py` (`list_pm_work_orders(filters, mine, search: str = "", page, page_size)` — inject `f["search"]` khi non-empty SAU `apply_vendor_scope`+`mine`); `services/imm08.py::list_work_orders` (pop `search`→`or_filters` qua `pop_search` TRƯỚC `_normalize_filters`, forward vào `_fetch_all_pm_rows`/`_list_pm_overdue_live`); `services/shared/filters.py::pop_search` (escape qua `escape_like_term` + `link_search` nhận list display-field); `api/openapi_overrides.py` (khai `search` string optional cho `list_pm_work_orders` + mirror `docs/mobile/openapi/assetcore-mobile.openapi.yaml`); tests (`test_imm08` search count==rows-paginated + escape-literal + AND-vendor/mine + byte-identical-empty). **FE Bước-4 delta:** `PMWorkOrderListView.vue` (server refetch debounce+reset page=1, gỡ `filteredWOs` client-filter + search-trap, giữ chip); `api/imm08.ts::listPMWorkOrders` (+`search`); `stores/imm08.ts::fetchWorkOrders` (forward `search`).

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
    "is_overdue": true,
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

**`is_overdue` — cờ LIVE quá-hạn (CR-37, mobile parity list↔detail):** `boolean` DERIVED Python-bool tại `get_work_order` qua **CÙNG predicate `_enrich_pm_overdue`** của list-item (`status == "Overdue"` OR `is_pm_overdue`: `due_date < today` ∧ `status ∈ {Open, In Progress, Pending–Device Busy}`). Emit BÊN CẠNH `is_late` (STORED, `Check` → wire cờ trễ-hoàn-thành), 2 cờ KHÁC nghĩa. **GIỮ boolean** (KHÔNG int-0/1 — derived, KHÔNG raw Check). Badge "Bảo trì quá hạn" màn detail đọc cờ LIVE này ⇒ KHÔNG trễ 1 nhịp cron `check_pm_overdue`. **INVARIANT parity:** cờ `is_overdue` trên detail == cờ `is_overdue` trên list-item cùng record.

**`allowed_transitions[]` — server-driven CTA (Boundaries Always/Never):** detail emit tập trạng-thái-kế hợp-lệ từ `status` hiện tại → màn detail render nút workflow theo server.
- **Always:** giá trị = `_PM_VALID_TRANSITIONS.get(status, [])` (SSoT workflow, **GROUNDED** `imm_08_pm_workflow.json` 7 state / 13 transition) **∪ CR-45 reschedule-CTA overlay**: nếu `status ∈ RESCHEDULE_CTA_STATES = {Open, Overdue}` thì **append `Pending–Device Busy`** (đích của action «Dời lịch» = `reschedule()`; `In Progress` ĐÃ có `Pending–Device Busy` sẵn từ workflow ⇒ overlay chỉ tác động Open/Overdue):

  | Status hiện tại | `allowed_transitions[]` |
  |---|---|
  | `Open` | `In Progress`, `Overdue`, `Cancelled`, **`Pending–Device Busy`** ← CR-45 overlay (CTA «Dời lịch») |
  | `Overdue` | `In Progress`, `Cancelled`, **`Pending–Device Busy`** ← CR-45 overlay (CTA «Dời lịch») |
  | `In Progress` | `Completed`, `Halted–Major Failure`, `Pending–Device Busy`, `Cancelled` (Pending SẴN CÓ từ workflow — overlay no-op) |
  | `Pending–Device Busy` | `In Progress`, `Cancelled` |
  | `Halted–Major Failure` | `In Progress`, `Cancelled` |
  | `Completed` (terminal) | `[]` (rỗng) |
  | `Cancelled` (terminal) | `[]` (rỗng) |

- **Vì sao overlay (khớp hành vi reschedule THẬT):** `reschedule()` là **service action** (KHÔNG phải Frappe workflow transition) — set `status → Pending–Device Busy` từ Open/Overdue/In Progress kèm `new_date`+`reason`. Workflow JSON KHÔNG mô-hình-hoá Open→Pending / Overdue→Pending (chỉ In Progress→Pending qua action "Thiết bị bận - hoãn") ⇒ nếu `allowed_transitions` chỉ mirror workflow, mobile/web KHÔNG render được CTA «Dời lịch» ở **ca phổ biến nhất** (phiếu Open/Overdue chưa ai bắt đầu). Overlay đưa `Pending–Device Busy` vào tập CTA cho Open/Overdue ⇒ FE map đích `Pending–Device Busy` → CTA «Dời lịch» → gọi `reschedule_pm` (đúng như đã map cho In Progress).
- **Never:** client KHÔNG hardcode `status → button` (anti-pattern lifecycle dead-gate); map BE KHÔNG sinh state ngoài enum `PMStatus`. `_PM_VALID_TRANSITIONS` **GIỮ nguyên** = pure workflow-mirror (parity-guard `map ↔ workflow JSON` KHÔNG đổi, KHÔNG `bench migrate`); overlay áp **chỉ ở tầng emit** `get_work_order`. **KHÔNG** thêm transition Open→Pending / Overdue→Pending vào workflow JSON (sẽ đổi hành vi Frappe workflow thật + cần migrate — reschedule KHÔNG đi qua workflow-transition). Mirror `IncidentDetail.allowed_transitions` (IMM-12, R3) về nguyên tắc server-driven.

> **ADR-IMM08-RESCHED-CTA** · Accepted 2026-07-24 (CR-45b) — **Context**: `allowed_transitions` xưa == pure workflow-mirror; nhưng `reschedule()` (custom service action) chuyển Open/Overdue→Pending ngoài workflow ⇒ CTA «Dời lịch» không phơi được ở Open/Overdue. **Decision**: `allowed_transitions` = workflow-mirror **∪** reschedule-CTA-overlay (`+Pending–Device Busy` cho `{Open, Overdue}`), overlay CHỈ ở emit `get_work_order`; `_PM_VALID_TRANSITIONS` + workflow JSON + parity-guard GIỮ NGUYÊN. **Alternatives loại**: (a) thêm transition vào workflow JSON → đổi workflow thật + migrate + reschedule vẫn KHÔNG đi qua transition (sai mô hình); (b) field riêng `reschedulable:bool` → mobile đã dùng `allowed_transitions`-driven CTA, tách field = 2 nguồn CTA (loại). **Consequences**: `allowed_transitions` giờ = **superset** workflow-mirror (KHÔNG còn == `_PM_VALID_TRANSITIONS[status]` cho Open/Overdue); test emit (`test_imm08.py:465` `test_get_work_order_emits_allowed_transitions_per_status`) PHẢI cập nhật cho Open/Overdue; parity-guard workflow (`test_imm08.py:438`) KHÔNG đổi.

> **Acceptance contract CR-45b (BE Bước-4):** (1) thêm hằng `RESCHEDULE_CTA_STATES = frozenset({PMStatus.OPEN, PMStatus.OVERDUE})` (`services/imm08.py`, cạnh `_PM_VALID_TRANSITIONS`). (2) `get_work_order`: `transitions = list(_PM_VALID_TRANSITIONS.get(wo.status, []))`; `if wo.status in RESCHEDULE_CTA_STATES and PMStatus.PENDING_BUSY not in transitions: transitions.append(PMStatus.PENDING_BUSY)`; emit `transitions`. (3) test: cập nhật `test_get_work_order_emits_allowed_transitions_per_status` (Open/Overdue kỳ vọng `+Pending–Device Busy`); **+TC AC3** khẳng định `Pending–Device Busy ∈ allowed_transitions` cho phiếu Open VÀ Overdue; parity-guard workflow GIỮ XANH. `bench --site miyano run-tests --module assetcore.tests.test_imm08` 'Ran N OK'. NEW `.py` reload = USER.

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
| Role | HTM Technician, Workshop Head (cap `pm.submit` — `api/imm08.py:115`) |
| Idempotent | No (legacy) · **Yes-replay khi có `client_request_id`** (BR-08-18) |

**Request:**

```jsonc
{
  "name": "PM-WO-2026-00001",
  "checklist_results": "[{\"idx\":1,\"result\":\"Pass\",\"measured_value\":220.5,\"notes\":\"\"}]",
  "overall_result": "Pass",
  "technician_notes": "Sticker đã gắn",
  "pm_sticker_attached": 1,
  "duration_minutes": 52,
  "client_request_id": "a3f1c0de-…-outbox-uuid"   // optional — mobile write-outbox key (BR-08-18); rỗng/absent ⇒ legacy no-dedup
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

#### 4.1 Idempotency `client_request_id` (BR-08-18 / ADR-IMM08-IDEMPOTENCY-01 — mobile write-outbox)

> **Bản chất**: đóng cửa sổ *re-drain outbox tạo side-effect PM TRÙNG* khi response `submit_pm_result` rớt mạng (server ĐÃ complete WO nhưng client chưa persist payload → re-POST cùng body). Client gửi kèm khoá bền `client_request_id` (= `item.id` outbox, UUID mint-1-lần, ổn định qua mọi re-drain) → server replay idempotent. **KHÁC CR-24 (report_incident)**: KHÔNG DocField mới, KHÔNG `bench migrate` — idempotency neo trên **terminal-state của chính PM Work Order** (xem ADR-IMM08-IDEMPOTENCY-01, `04 §4`).

| Trường hợp | Hành vi |
|---|---|
| `client_request_id` **rỗng / absent** | **Legacy no-dedup (byte-identical hiện trạng)**. Submit lần 2 lên WO `docstatus==1` → Error envelope `IMM08_ALREADY_SUBMITTED` (in-handler HTTP-200). NULL-semantics. |
| `client_request_id` **non-empty**, WO CHƯA submit | Áp side-effect BÌNH THƯỜNG → complete WO → trả payload 5-key. |
| `client_request_id` **non-empty**, WO ĐÃ Completed (replay) | **Idempotent replay**: re-read state terminal → dựng lại **CÙNG payload 5-key** `{name,new_status,is_late,next_pm_date,cm_wo_created}` (byte-for-byte == lần 1) → return success, **KHÔNG raise**, **KHÔNG áp lại side-effect**. `completion_date`/`next_pm_date` KHÔNG drift; `cm_wo_created` re-đọc `find_one(source_pm_wo, Corrective)` ⇒ **CM WO count KHÔNG tăng**. |
| **Race** — 2 request gần-đồng-thời CÙNG key, CÙNG WO `docstatus==0` | Đúng **1 winner** commit `wo.submit()`; loser bắt exception va-chạm (stale-doc / `DocstatusTransitionError` / duplicate) → convert sang re-read terminal → trả payload winner. **KHÔNG double CM WO**, **KHÔNG rò** `IMM08_ALREADY_SUBMITTED`/'must be unique' ra caller. |
| 2 `client_request_id` khác nhau trên 2 WO khác nhau | Độc lập — dedup scope theo natural key `(wo_name, client_request_id)`, KHÔNG nhiễm chéo. |

**⚠️ Self-Correction (payload shape — KHÔNG đổi).** Acceptance đề mục liệt kê payload `{name,new_status,completion_date,next_pm_date,cm_wo_created}` là **KHÔNG chính xác**: payload authoritative của `submit_pm_result` là **5-key `{name, new_status, is_late, next_pm_date, cm_wo_created}`** (có `is_late`, KHÔNG `completion_date`) — khoá bởi `services/imm08.py:1020-1026` + OAS closed schema `PmSubmitResultResponse` required-EXACT-5 + FE type `frontend/src/api/imm08.ts:131` + guard `test_mob_oas_submitpm_f/_i` (`_SUBMIT_PM_RESULT_DATA_KEYS`). **KHÔNG thêm `completion_date` vào payload** (sẽ vỡ closed-schema guard + lệch FE type + là contract-change ngoài scope). Bất biến "`completion_date` KHÔNG drift" được **quan sát gián tiếp** qua (a) field `completion_date` persist trên WO (đọc bằng `get_pm_work_order`) không đổi + (b) `next_pm_date` trong payload (derive từ completion_date, BR-08-03) không đổi.

**Bất biến giữ nguyên**: `rbac.require("pm.submit")` (`api/imm08.py:115`) + `@frappe.whitelist(methods=["POST"])` (`:111`) + anti-spoof (signature KHÔNG nhận `user`) + envelope Decision-B (`handle`/`_ok`). Không schema/DocField mới ⇒ **KHÔNG `bench migrate`** (deploy = worker reload `--preload`, HARD-STOP user).

> **Mobile-BE binding (BE-owned atomic slice — CHƯA land round này).** Đóng contract cần **3 artifact land ATOMIC** (như CR-24 attach-photo) — vì guard `test_mob_oas_submitpm_i` introspect **LIVE `inspect.signature(imm08.submit_pm_result)`**: nếu curate OAS trước khi `.py` có param ⇒ suite RED. BE Bước-4 land cùng lượt:
> 1. **`api/imm08.py::submit_pm_result`** — thêm param CUỐI `client_request_id: str = ""` (KHÔNG `str|None` → tránh 417), truyền xuống `handle(svc.submit_result, name, …, client_request_id=client_request_id)`.
> 2. **`services/imm08.py::submit_result`** — thêm kwarg `client_request_id: str = ""`; gate nhánh `docstatus==1` (replay vs legacy-raise) + race-catch → re-read terminal (§4.1).
> 3. **OAS `docs/mobile/openapi/assetcore-mobile.openapi.yaml`** — `SubmitPmResultRequest.properties` **+`client_request_id`** (`type: string`, `default: ''`, description nêu 'idempotency'/'mobile write-outbox'); GIỮ `additionalProperties: false`; GIỮ `required: [name]` (client_request_id **optional**, KHÔNG vào required). `PmSubmitResultResponse` **KHÔNG đổi** (5-key). Path/opId/`oas_baseline` KHÔNG đổi (0 endpoint mới).
> 4. **Guard `assetcore/tests/test_mobile_oas.py`** — `_SUBMIT_PM_RESULT_REQUEST_PROPS` **6→7** (thêm `"client_request_id"`) ⇒ CẢ guard `_c` (OAS props EXACT) LẪN `_i` (live-sig EXACT) tự khớp; `_SUBMIT_PM_RESULT_REQUEST_REQUIRED` GIỮ `["name"]`. **KHÔNG TC mới** ⇒ `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_*` / `_MOBILE_OAS_TOTAL` **KHÔNG đổi** (khác CR-24 vốn +3 TC vì schema OPEN; schema PM CLOSED nên prop-set 6→7 đủ enforce).
> 5. **Runtime guard `assetcore/tests/test_imm08.py`** — class idempotency mới (`TestPmResultIdempotency`, RED-before/GREEN-after) TC-PM-IDEM-01..06: (01) same-key×2 → WO Completed 1 lần + payload lần2==lần1 + KHÔNG raise; (02) next_pm_date/completion_date KHÔNG drift (WO backdated); (03) escalate CM → CM WO count KHÔNG tăng lần 2; (04) key rỗng → lần 2 Error `IMM08_ALREADY_SUBMITTED` (legacy); (05) race cùng key → 1 winner + loser re-read cùng payload + KHÔNG double CM + KHÔNG leak lỗi; (06) scope `(wo_name, client_request_id)` — 2 WO/2 key độc lập.
>
> Cross-link mobile contract: khi land, mirror thêm 1 mục §8.x vào [`docs/mobile/04-api-contract.md`](../mobile/04-api-contract.md) (cạnh CR-24 §8.3b) — SSoT contract vẫn là mục này (`05 §4.1`). ⚠️ Sau land: **USER reload gunicorn `--preload`** cho HTTP live (LL-DEPLOY-07 — KHÔNG curl-verify LIVE trước reload).

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
| `ALREADY_SUBMITTED` | WO đã docstatus=1 VR-08-10 — **CHỈ khi `client_request_id` rỗng** (legacy). Có `client_request_id` ⇒ nhánh này thay bằng idempotent replay (§4.1), KHÔNG raise |
| `VALIDATION` | BR-08-06 (ảnh) / **BR-08-19 bảng kiểm RỖNG `IMM08-CHECKLIST-EMPTY`** / BR-08-08 thiếu-result `IMM08-CHECKLIST-INCOMPLETE` / BR-08-20 idx payload lệch `IMM08-CHECKLIST-IDX-UNKNOWN` (OPTIONAL) / BR-08-09 duration / BR-08-10 sticker. Precedence: EMPTY > IDX_UNKNOWN > INCOMPLETE. |

**Side effects (áp ĐÚNG 1 lần / WO — replay KHÔNG lặp lại, §4.1):**
- PM Task Log immutable tạo
- PM Schedule `last_pm_date`, `next_due_date` advance (BR-08-03)
- Asset `custom_last_pm_date`, `custom_next_pm_date` sync
- CM Work Order tạo nếu Fail-Minor/Major (BR-08-09)

**Boundaries (BR-08-18):**
- **Always**: replay (key non-empty, WO Completed) trả CÙNG payload 5-key byte-for-byte + KHÔNG áp lại side-effect; race → 1 winner + loser re-read; dedup scope theo `(wo_name, client_request_id)`; `client_request_id=""` ⇒ hành vi legacy byte-identical; giữ `rbac.require("pm.submit")` + POST-only + anti-spoof + envelope Decision-B.
- **Never**: thêm DocField/schema mới hay `bench migrate`; đổi payload shape (thêm `completion_date` vào `data`); drift `completion_date`/`next_pm_date` trên replay; tạo CM WO thứ 2 trên replay; rò `IMM08_ALREADY_SUBMITTED`/'must be unique' khi có key; nhận `str|None` cho param (417); nhận `user` trong signature; commit / reload / migrate (HARD-STOP user).

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

**Errors:** `VALIDATION` (reason < 5 ký tự — VR-08-09 · **HOẶC CR-45c: phiếu ở trạng thái terminal Completed/Cancelled**) · `NOT_FOUND` (WO không tồn tại).

#### CR-45c — Siết guard reschedule ở phiếu terminal (VR-08-13)

> **Bối cảnh (đề mục vòng 3 · CR-45c):** `reschedule()` hiện **KHÔNG kiểm tra `status` phiếu** — set `due_date`+`Pending–Device Busy` **vô-điều-kiện** ⇒ có thể "dời lịch" 1 phiếu **đã Hoàn thành / đã Hủy** (ghi đè `due_date`, hồi-sinh phiếu terminal → sai audit trail + KPI). CR-45c thêm guard chặn ca terminal.

- **VR-08-13 (mới):** nếu `wo.status ∈ RESCHEDULE_TERMINAL_STATES = frozenset({Completed, Cancelled})` → `raise validation("Không thể dời lịch phiếu đã ở trạng thái kết thúc (Hoàn thành/Đã hủy)")` ⇒ `ErrorCode.VALIDATION` **HTTP-422** (qua helper `validation()` — **KHÔNG thêm MSG-code mới**, né FE i18n-regen SYS-500). Lỗi ARRIVE **HTTP-200 + Error envelope** (Decision-B, KHÔNG raise→4xx).
- **Thứ tự guard (BẮT BUỘC — TRƯỚC mọi mutate):** (1) reason < 5 → `validation` (giữ nguyên); (2) `wo = PMWorkOrderRepo.get(name)`; not found → `nthrow NOT_FOUND`; (3) **CR-45c** `wo.status ∈ terminal → validation(422)` **TRƯỚC** khi gán `wo.due_date`/`wo.status`/`save`. ⇒ **`due_date` KHÔNG bị ghi đè** ở ca terminal (INVARIANT — test đọc `due_date` sau lỗi == cũ).
- **Ca hợp lệ GIỮ NGUYÊN:** Open / Overdue / In Progress (và Pending–Device Busy / Halted–Major Failure — non-terminal) vẫn dời lịch như cũ: set `due_date=new_date`, `status=Pending–Device Busy`, append note, restore asset Active nếu đang In Progress. **KHÔNG mở rộng guard** ra ngoài `{Completed, Cancelled}` (AC4 chốt CHỈ terminal).

> **ADR-IMM08-RESCHED-GUARD** · Accepted 2026-07-24 (CR-45c) — **Context**: `reschedule()` không guard status → dời-lịch được phiếu terminal. **Decision**: chặn `{Completed, Cancelled}` bằng `validation()` (422, reuse ErrorCode.VALIDATION — KHÔNG MSG-code mới), guard đặt SAU lookup TRƯỚC mutate ⇒ `due_date` bất biến khi reject. **Alternatives loại**: (a) MSG-code `IMM08_RESCHEDULE_TERMINAL` riêng → buộc FE regen `messages.ts` (Blocker#1 pattern SYS-500) — loại, dùng `validation()` literal; (b) chặn cả Pending/Halted → vượt AC4, có thể vỡ flow re-postpone (loại); (c) `raise frappe.throw`→HTTP-4xx → vi phạm Decision-B in-handler HTTP-200 (loại). **Consequences**: +1 guard-clause, 0 field/enum mới, 0 MSG-code, 0 migrate. `reschedule_pm` slot lỗi đã có `{404,422}` (không đổi OAS `Error.http_status`).

> **Acceptance contract CR-45c (BE Bước-4):** (1) hằng `RESCHEDULE_TERMINAL_STATES = frozenset({PMStatus.COMPLETED, PMStatus.CANCELLED})` (`services/imm08.py`). (2) trong `reschedule()` sau lookup WO, TRƯỚC gán `wo.due_date`: `if wo.status in RESCHEDULE_TERMINAL_STATES: raise validation("Không thể dời lịch phiếu đã ở trạng thái kết thúc (Hoàn thành/Đã hủy)")`. (3) **+TC AC4** (`test_imm08.py`): phiếu Completed → `reschedule_pm` trả Error envelope `success=False` code `VALIDATION` (http_status 422) **VÀ** `due_date` DB == cũ (KHÔNG ghi đè); phiếu Cancelled tương tự; ca Open/Overdue/In Progress vẫn dời-lịch thành công (regression giữ). RED-before/GREEN-after. `bench --site miyano run-tests --module assetcore.tests.test_imm08` 'Ran N OK'. NEW `.py` reload = USER. **OAS reschedule_pm KHÔNG đổi** (422 đã trong `Error.http_status` — CONTRACT-STABLE).

---

### 9. get_asset_pm_history — Lịch sử PM của thiết bị
> 🔌 **CONSUMER (từ 2026-07-30 — AC-CR-102):** endpoint này nay có **caller THẬT ở web-FE**: section «Kết quả bảo trì» trong tab «Bản ghi liên quan» của màn Chi tiết tài sản (IMM-00). Hợp đồng ĐỌC phía consumer: [`docs/imm-00/05 §III.26`](../imm-00/05_API_Specification.md) · quyết định: [`ADR-IMM00-ASSET-OP-HISTORY`](../imm-00/ADR-IMM00-ASSET-OP-HISTORY.md). **Hệ quả**: đơn vị dòng là **`PM Task Log`** (KHÔNG `PM Work Order`) — FE khai `PMTaskLogHistoryItem` đúng 10 field và deep-link bằng **`row.pm_work_order`** (`PM Task Log` không có màn chi tiết). Đổi `fields`/rows-key/`asset_ref` ⇒ **vỡ FE câm** ⇒ phải sửa `docs/imm-00/05 §III.26.3` + guard `assetcore/tests/test_asset_operational_history_contract.py` trong **cùng vòng**.


| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.get_asset_pm_history` |
| Role | ~~All IMM roles~~ → **DocPerm `read` trên `PM Task Log`** — cap SOUND `pm.read_history` (`AC-CR-119` §9.4) |
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

#### 9.2 `get_asset_pm_history` — hợp đồng TRUNG THỰC khi cắt: `+total` `+truncated` (CR-69) ✅ BE IMPLEMENTED (2026-07-25)

> ✅ **BE Bước-4 ĐÃ LAND** (`services/imm08.py::get_asset_history` `:1530-1551` — `logs, pg = PMTaskLogRepo.list(...)` + `truncation_meta(len(logs), int(pg["page_size"]), lambda: int(pg["total"]))` `:1548-1549`). Guard: `assetcore/tests/test_imm08.py::TestAssetPmHistoryTruncation` (5 TC — HIST-01/02/03 + int-parity + INV-PMH-6 clamp `limit=500`/105 log) — `test_imm08` **167 OK**. FE `.ts` = việc của Bước-4 [FE] (song song).

> **Mục tiêu (CR-69):** tab **"Lịch sử bảo trì"** của màn hồ-sơ-vận-hành thiết bị đang **cắt IM LẶNG** theo `limit` (mặc định 10). KTV mở máy có 40 lần PM chỉ thấy 10 dòng và kết luận *"máy này PM 10 lần"* — không có bất kỳ tín hiệu nào cho biết danh sách bị cắt. Đây là lần **thứ 4** của cùng một lớp lỗi (CR-43 inbox · CR-46 due-list · CR-47 competencies) ⇒ quyết định gốc ghi ở [`ADR-IMM00-TRUNCATION-SSOT`](../imm-00/ADR-IMM00-TRUNCATION-SSOT.md); mục này chỉ là **áp dụng**, KHÔNG định nghĩa lại ngữ nghĩa.

**Endpoint KHÔNG đổi:** `GET assetcore.api.imm08.get_asset_pm_history` (`api/imm08.py:198` → `services/imm08.py::get_asset_history` `:1530-1539`). Auth/param/row-scope **GIỮ NGUYÊN**.

**Response — 2 khoá MỚI (ADDITIVE) trong `data`:**

```jsonc
{
  "success": true,
  "data": {
    "asset_ref": "AC-ASSET-2026-0003",
    "history": [ /* ≤ limit dòng, mới→cũ — KHÔNG đổi */ ],
    "total": 40,      // COUNT thật trên {asset_ref} @PM Task Log TRƯỚC khi cắt
    "truncated": 1    // int 0/1 — 1 = còn phiếu chưa hiển thị
  }
}
```

| Field | Kiểu wire | Nguồn (SSoT) | Ràng buộc |
|---|---|---|---|
| `total` | `integer` ≥ 0 | `pg["total"]` do `PMTaskLogRepo.list` **ĐÃ tính** (`repositories/base.py:147-148`, filter `{asset_ref}`) | KHÔNG query COUNT thứ hai · KHÔNG `nullable` |
| `truncated` | `integer` ∈ `{0,1}` | `truncation_meta(len(logs), eff_limit, lambda: pg["total"])` | KHÔNG `boolean`, KHÔNG `None` (CR-01 int-vs-bool trap) |

**BE Bước-4 delta** (`services/imm08.py::get_asset_history` — 3 dòng):

1. Đổi `logs, _ = PMTaskLogRepo.list(...)` → `logs, pg = PMTaskLogRepo.list(...)` (đang **vứt** meta phân trang đi).
2. `total, truncated = truncation_meta(len(logs), pg["page_size"], lambda: pg["total"])`.
3. `return {"asset_ref": asset_ref, "history": logs, "total": total, "truncated": truncated}`.

> ⚠️ **Bẫy DUY NHẤT của mục này (INV-TRUNC-LIMIT / ADR §D5):** đối số thứ 2 PHẢI là **`pg["page_size"]`**, **KHÔNG** phải `limit` thô. `paginate` **clamp** `page_size` về `[1, 100]` (`utils/pagination.py:23`): client gửi `limit=500` ⇒ rows thực bị cắt ở **100** nhưng `len(logs)=100 < 500` ⇒ `truncation_meta` kết luận *"không cắt"* — **nói dối đúng thứ CR-69 sinh ra để xoá**. Dùng `pg["page_size"]` là trần THỰC ÁP ⇒ đúng ở mọi giá trị `limit`. **Cải chính 2026-07-25 (`limit=0`):** trước đó endpoint truyền `page_size=int(limit)` ⇒ `paginate` thay falsy bằng default **20 CỦA CHÍNH `paginate`**, trong khi tab "Sự cố" (imm12) clamp về **10** ⇒ cùng `limit=0` mà 2 tab của CÙNG một màn trả số dòng khác nhau. Nay cả 3 endpoint history clamp bằng **cùng một** lời gọi `clamp_page_size(limit, 10)` (10 = default của chính endpoint) TRƯỚC khi truyền `page_size`; `pg["page_size"]` vẫn là trần THỰC ÁP (clamp idempotent). Guard: `test_imm08::test_tc_be_08_hist_07_limit_zero_falls_back_to_endpoint_default_10`.

**Boundaries (Always / Never):**
- **Always:** derive qua SSoT `services/shared/truncation.py::truncation_meta` (imm08 **đã import sẵn** `:23`, dùng ở due-PM `:1643`) · `count_fn` tái dùng `pg["total"]` (⇒ **0 query thêm** ở MỌI ca, không chỉ ca không-cắt) · `truncated` là `int` · giữ `data.required = [asset_ref, history]`.
- **Never:** KHÔNG đổi **tập row** trả về (CR-69 là read-meta, KHÔNG phải CR row-scope — `PMTaskLogRepo.list` GIỮ `scope` mặc định `"user"`, xem §9.3) · KHÔNG thêm param/endpoint/DocType/field · KHÔNG dùng `frappe.db.count` thô cho `total` (lệch engine với rows ⇒ tái sinh bug `count != rows`, ADR-IMM00-LIST-SCOPE §8.3) · KHÔNG đưa 2 khoá vào `required`.

**BẤT BIẾN ĐO ĐƯỢC (test `test_imm08`):**

| Invariant | Kiểm chứng |
|---|---|
| **INV-PMH-1** (không cắt ⇒ trung thực) | asset có 3 PM Task Log, `limit=10` ⇒ `len(history)==3` ∧ `total==3` ∧ `truncated==0` |
| **INV-PMH-2** (cắt ⇒ khai báo) | asset có 12 log, `limit=5` ⇒ `len(history)==5` ∧ `total==12` ∧ `truncated==1` |
| **INV-PMH-3** (vừa khít trần ⇒ KHÔNG báo oan) | asset có ĐÚNG 5 log, `limit=5` ⇒ `total==5` ∧ **`truncated==0`** |
| **INV-PMH-4** (kiểu wire) | `type(total) is int` ∧ `type(truncated) is int` ∧ `truncated in (0,1)` — assert bằng `type(x) is int` (KHÔNG `isinstance`: `bool` là subclass của `int`, `isinstance(True,int)` == `True` ⇒ test **false-green** đúng lỗi cần chặn) |
| **INV-PMH-5** (additive) | `asset_ref` + `history` GIỮ NGUYÊN key và nội dung so với trước CR-69 (0 breaking) |
| **INV-PMH-6** (clamp) | `limit=500` trên asset có 150 log ⇒ `len(history)==100` ∧ `total==150` ∧ `truncated==1` (chống bẫy D5) |

**FE Bước-4 delta — `frontend/src/api/imm08.ts:205-213` (SỬA LỜI NÓI DỐI ĐANG TỒN TẠI):**

Type trả về hiện khai `total: number` **bắt buộc** trong khi BE **chưa bao giờ** phát khoá này ⇒ mọi call site đọc `res.total` nhận `undefined` với kiểu `number` — TypeScript đang **bảo chứng cho một giá trị không tồn tại**. Sau CR-69:

```ts
export function getAssetPMHistory(
  assetRef: string,
  limit = 10,
): Promise<{ asset_ref: string; history: PMWorkOrder[]; total?: number; truncated?: 0 | 1 }> {
```

- **`total?` / `truncated?` là OPTIONAL — CỐ Ý, không phải lười.** Hai lý do cùng chiều: (1) OAS khai chúng **ngoài `required`** (ADR §D3) ⇒ type bắt buộc sẽ **lệch contract**; (2) `.py` production chạy dưới gunicorn `--preload` **chỉ reflect sau khi USER reload** — trong cửa sổ đó bundle FE mới vẫn nhận response CŨ không có 2 khoá. Khai bắt buộc = tái lập đúng lớp nói dối mà CR-69 đang xoá.
- Call site: `truncated === 1` ⇒ hiện dải "Đang xem một phần lịch sử bảo trì — thiết bị có tổng {total} lượt." · `truncated === 0` ⇒ không hiện gì · `undefined` ⇒ **không hiện gì** (không rõ ≠ không bị cắt), TUYỆT ĐỐI KHÔNG render `total` khi nó `undefined`.
- **Never:** KHÔNG `any`; KHÔNG `truncated: boolean` (BE phát `0/1`); KHÔNG so `history.length < total` để tự suy "còn nữa" (client không biết trần đã clamp — ADR §D5, alternative B đã loại).

#### 9.3 *(Cần BA ratify — KHÔNG thuộc CR-69)* Bất đối xứng row-scope giữa 3 tab history

Ghi nhận để không ai "tiện tay sửa" trong lúc làm CR-69:

| Endpoint | `scope` hiện tại | Ngữ nghĩa `total` |
|---|---|---|
| `imm08.get_asset_history` (PM) | mặc định `"user"` (`services/imm08.py:1531`) | tổng **user này được thấy** |
| `imm09.get_asset_history` (CM) | **`"system"`** tường minh (`services/imm09.py:2061`, R5/D6 device-centric) | tổng **toàn thiết bị** |
| `imm11.get_asset_history` (hiệu chuẩn) | mặc định `"user"` (`services/imm11.py:1676-1677`) | tổng **user này được thấy** |

⇒ Cùng một màn hồ-sơ thiết bị, 3 tab đang trả lời câu hỏi **khác nhau**. IMM-09 đã ratify device-centric (lịch sử hỏng hóc của MÁY, không gắn danh tính người sửa); PM/hiệu chuẩn thì chưa. **CR-69 CỐ Ý giữ nguyên** (đổi scope = đổi tập row = blast-radius quyền, phải đi cùng cụm INV-ROWSCOPE). Đề mục cho vòng sau: BA chốt 1 quy ước cho cả 3 tab.

#### 9.4 `AC-CR-119` — hợp đồng **QUYỀN**: cap SOUND là `pm.read_history`, **KHÔNG** `pm.read` (cải chính «All IMM roles»)

> Quyết định đầy đủ: [`docs/imm-00/ADR-IMM00-ASSET-OP-HISTORY §11`](../imm-00/ADR-IMM00-ASSET-OP-HISTORY.md) (`D-OPH-21/22/27`) · hợp đồng quyền consumer: [`docs/imm-00/05 §III.26.7`](../imm-00/05_API_Specification.md). Endpoint **KHÔNG đổi** path/param/`fields`/`order_by`/khoá response ⇒ **0** OAS delta.

**Cải chính claim quyền (cite-drift đóng ở đây).** Bảng §1 dòng 10 và bảng §9 ghi «Role: **All IMM roles**» — **SAI**. Đường gate THẬT là DocPerm `read` trên **`PM Task Log`** (`PMTaskLogRepo.list(...)` scope mặc định `"user"` → `count_with_or` → `frappe.get_list` — `services/shared/filters.py:281 (invariant docstring :249-262)`), và `pm_task_log.json` chỉ khai **4** role (`AssetCore Super Admin`, `PM Manager`, `PM User`, `AssetCore Auditor`). Ví dụ cứng: `Commissioning Manager` có `read=1` trên `PM Work Order` nhưng **không có dòng nào** trên `PM Task Log` ⇒ endpoint trả **403**.

**Cap SOUND — MỚI trong `CAPABILITY_MAP`:**

```python
"pm.read_history": ("PM Task Log", "read")     # services/shared/rbac.py
```

⚠️ **`pm.read` KHÔNG dùng được để gate nhánh này**: nó bind `("PM Work Order","read")` (auto-gen từ `_DOMAIN_PRIMARY["PM"]` — `rbac.py:70,100-103`) ⇒ `rbac.can("pm.read")` có thể **True** trong khi endpoint **403**. `pm.read` **KHÔNG đổi** (vẫn đúng cho route-guard `/pm/*`, sidebar, `list_pm_work_orders`).

**BE thêm gate TƯỜNG MINH** (`D-OPH-27`) trong `services/imm08.py::get_asset_history`, **trước** `PMTaskLogRepo.list`:

```python
assert_doctype_read_permission(_DT_PM_TASK_LOG)   # L0 ROLE — KHÔNG dựa tác dụng phụ của count_with_or
```

Vì sao: hôm nay 403 đến từ **tác dụng phụ** (`count_with_or` tình cờ dùng `frappe.get_list`), và `repositories/base.py:37` cho thấy `_ROLE_GATED_SCOPES = (LIST_SCOPE_SYSTEM,)` ⇒ nhánh `scope="user"` **không** có gate tường minh nào. Chính lớp phụ thuộc đó đã một lần gây finding CRITICAL A01 (nguyên văn `services/shared/permissions.py:57-62`), và recipe tối ưu `count` đã ghi sẵn trong repo (`filters.py:274-276`) là đúng loại thay đổi sẽ **im lặng gỡ** cái 403 này. **0 đổi hành vi**: `PermissionError` → `@rowscoped` → **cùng** envelope `{success:false, code:"FORBIDDEN", http_status:403}`, **cùng** message hằng `MSG.AUTH_FORBIDDEN`; chỉ sớm hơn một truy vấn.

**Hệ quả FE (consumer IMM-00):** nhánh «Kết quả bảo trì» hỏi `pm.read_history` **TRƯỚC** khi gọi; thiếu quyền ⇒ **trạng thái KHOÁ** (`[op-history-locked]`, 0 «Thử lại», 0 «Xem tất cả») — **KHÔNG** phải dải lỗi đỏ. Xem [`docs/imm-00/06 §VIII.16`](../imm-00/06_Frontend_Design.md).

**Hệ quả vận hành:** `CAPABILITY_MAP` **104 → 105**, `CAP_SET_VERSION` đổi ⇒ cần `bench restart` + `bench --site miyano clear-cache` (xoá cache caps `ac_caps::*`, TTL 1h — `rbac.py:217`); **KHÔNG** cần `bench migrate`. Blast-radius assert: [ADR §11.9](../imm-00/ADR-IMM00-ASSET-OP-HISTORY.md).

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

### 11. attach_pm_checklist_photo — Đính ảnh bằng chứng theo TỪNG mục checklist PM (NĐ98) 🟡 SPEC (BE/FE Bước-4)

> **Mục tiêu (mobile CR-14/G6):** KTV thực hiện PM tại hiện trường chụp ảnh bằng chứng cho **từng mục checklist** (vd đo áp lực, kiểm tra dây nguồn, dán tem) → đính **trực tiếp vào đúng mục** của PM Work Order làm **bằng chứng NĐ98** cho thiết bị **Class C/D** (BR-08-06 đã bắt buộc ảnh trước/sau PM với thiết bị nguy cơ cao; endpoint này là kênh nạp ảnh per-item cho mobile). **Đối xứng** `imm12.attach_incident_photo` (Vòng 1) — CÙNG pattern write-path multipart + File private + lifecycle-hard-req + Decision-B; **KHÁC**: module IMM-08, doctype `PM Work Order`, và ảnh gắn **theo mục checklist** (discriminator per-item) thay vì gộp cả phiếu.

**Endpoint:** `POST assetcore.api.imm08.attach_pm_checklist_photo`

**Request — `multipart/form-data`** (KHÁC mọi endpoint imm08 khác dùng JSON/form_dict):

| Phần | Nguồn | Bắt buộc | Ghi chú |
|---|---|---|---|
| `work_order_name` | form-field / query (`frappe.form_dict`) | ✅ | tên PM Work Order đang mở |
| `checklist_item_idx` | form-field (`frappe.form_dict`) → `int()` | ✅ | STT mục checklist (`pm_checklist_result.checklist_item_idx`, 1-based); parse-fail / không khớp row → `VALIDATION` |
| `file` | `frappe.request.files["file"]` (binary) | ✅ | ảnh JPG/PNG; đọc `upload.stream.read()` (mirror `imm12.attach_incident_photo` `api/imm12.py:262`) |

**Response 200 — success (Decision-B):**
```jsonc
{ "success": true, "data": { "file_url": "/private/files/pm_xxx.jpg", "file_name": "pm_xxx.jpg", "checklist_item_idx": 3 } }
```

**Side-effects khi success (BR-08-15 + BR-08-16):**
1. Sinh **đúng 1** `File` **private** (`attached_to_doctype="PM Work Order"`, `attached_to_name=<WO>`, `is_private=1`) attach vào **parent WO** — **KHÔNG** set `attached_to_field` discriminator (khớp code `services/imm08.py:866-874`). Phân biệt mục = ghi `file_url` vào đúng field `pm_checklist_result[idx].photo` (bước 2). Xem **ADR-IMM08-PHOTO-03** (reconcile MAX=1 write-once, supersede PHOTO-01).
2. Ghi `file_url` vào field `pm_checklist_result[idx].photo` bằng **`frappe.db.set_value("PM Checklist Result", <row.name>, "photo", file_url)`** — **KHÔNG** `wo.save()` (tránh re-chạy `validate_work_order` → BR-08-08 chưa-đủ-result sẽ throw khi PM đang dở, và tránh docstatus-1 lock; `photo` permlevel=0 nên không strip). Read-back: `get_pm_work_order(WO).checklist_results[idx].photo == file_url` (get_work_order KHÔNG đổi — đã trả `r.photo` `services/imm08.py:725`).
3. Sinh **đúng 1** `Asset Lifecycle Event` `event_type="pm_checklist_photo_attached"` (`asset=wo.asset_ref`, `actor=frappe.session.user`, `timestamp=now`, `root_doctype="PM Work Order"`, `root_record=<WO>`, `notes="Đính ảnh mục <idx>: <filename>"`) — evidence trail NĐ98, **hard-requirement KHÔNG swallow**. Event throw → File.insert + set_value rollback (chưa commit) ⇒ **không orphan, không silent** (đối xứng ADR-IMM12-07).

**Bảng lỗi (tất cả in-handler HTTP-200 + Error envelope — Decision-B, KHÔNG raise→4xx):**

| Nhánh | `success` | `code` | `http_status` | `fields` | File tạo? |
|---|---|---|---|---|---|
| **Guest/no-session** | — | — | **401 (in-handler guard) / 403 (dispatcher)** | — | ❌ (chặn TRƯỚC service; `@frappe.whitelist(methods=["POST"])` KHÔNG `allow_guest`) |
| WO không tồn tại | `false` | `NOT_FOUND` | 404 | — | ❌ |
| Không phải KTV được giao **VÀ** không `pm_work_order.write` | `false` | `FORBIDDEN` | 403 | — | ❌ (in-handler cap-403; check TRƯỚC khi tạo File) |
| `checklist_item_idx` thiếu / không parse int (sentinel `-1`) / KHÔNG khớp mục nào của WO | `false` | `VALIDATION` | 422 | `{file: "Không tìm thấy mục checklist trong lệnh bảo trì này"}` ⚠️ **Self-Correction:** mọi VALIDATION qua `_pm_photo_validation_error` (`services/imm08.py:839`) → key `fields.file` (KHÔNG `checklist_item_idx`); message = `_MSG_PM_PHOTO_IDX_NOT_FOUND` `services/imm08.py:52` | ❌ |
| Thiếu `file` | `false` | `VALIDATION` | 422 | `{file: "Thiếu tệp ảnh"}` | ❌ |
| Content-type KHÔNG ∈ allowlist 3 giá-trị (`image/jpeg`/`image/jpg`/`image/png`) | `false` | `VALIDATION` | 422 | `{file: "Tệp phải là ảnh JPG hoặc PNG"}` | ❌ |
| Size > cap (`MAX_PM_CHECKLIST_PHOTO_BYTES` = 10 MB — parity mobile) | `false` | `VALIDATION` | 422 | `{file: "Ảnh vượt quá dung lượng cho phép (tối đa 10 MB)"}` | ❌ |
| Mục đã có ảnh (`len(_checklist_item_photos(row)) >= MAX_PM_CHECKLIST_PHOTOS=1` — write-once, KHÔNG ghi đè) | `false` | `VALIDATION` | 422 | `{file: "Mỗi mục checklist chỉ đính 1 ảnh"}` | ❌ |
| **Ảnh hỏng / đứt-truyền** (`UnidentifiedImageError\|OSError` khi Frappe `File.before_insert`→`strip_exif`→`PIL.Image.open`; `services/imm08.py:901-912`) ⚠️ **Self-Correction (bổ sung nhánh còn thiếu)** | `false` | `VALIDATION` | 422 | `{file: "Tệp ảnh bị lỗi hoặc không đọc được, vui lòng chụp/chọn lại."}` | ❌ (PIL fail TRONG `before_insert` — TRƯỚC db_insert + write đĩa ⇒ KHÔNG orphan) |

> **HEIC/HEIF (ADR-IMM08-PHOTO-04 · cross-module imm08/09/12):** allowlist BE **GIỮ 3 giá-trị** `{image/jpeg, image/jpg, image/png}` (`_PM_PHOTO_CONTENT_TYPES` `services/imm08.py:42` — ⚠️ **Self-Correction**: 3 giá-trị KHÔNG 2, có `image/jpg`; đối xứng `_INCIDENT_PHOTO_CONTENT_TYPES`). iPhone chụp HEIC/HEIF **PHẢI được app mobile transcode → JPEG TRƯỚC upload** (fix tại-nguồn, 0 dependency BE, JPEG xem được trong web-audit). BE-transcode (pillow-heif) = `[ROADMAP]` defensive fallback (measure-first); mở-allowlist-nhận-HEIC = **loại** (HEIC không render trên trình duyệt/web-audit). Xem ADR-IMM08-PHOTO-04.

**2 loại 403 (DONE-gate spec-contract — mirror imm12):**
- **dispatcher-403 / guard-401** = Guest/no-token → chặn TRƯỚC khi vào service. Handler mở đầu `if frappe.session.user == "Guest": return _err(_MSG_UNAUTHENTICATED, 401)` (mirror `api/imm12.py:257`); nếu bỏ guard thì dispatcher POST-@whitelist trả 403 thật. Đây KHÔNG phải lỗi nghiệp vụ.
- **in-handler cap-403** = đã đăng nhập nhưng không phải KTV được giao và thiếu `pm.write` → `ServiceError(FORBIDDEN)` surface Decision-B HTTP-200 body `code=FORBIDDEN`, `http_status=403`. **KHÔNG leak** raw cap.

**Thứ tự thực thi (BẮT BUỘC — mọi nhánh reject TRƯỚC khi ghi File):** Guest(401) → exists(WO) NOT_FOUND → permission (assigned/write) FORBIDDEN → resolve `checklist_item_idx`→row (idx hợp lệ) VALIDATION → file present VALIDATION → content-type VALIDATION → size VALIDATION → max-count VALIDATION → `File.insert(is_private=1)` → `db.set_value(row.photo)` → `create_lifecycle_event(pm_checklist_photo_attached)` → `frappe.db.commit()` → `_ok`. **KHÔNG commit trước khi emit event** (giữ rollback-on-throw).

**Permission model (BR-08-15) — mirror `_assert_can_attach_photo` (imm12):**
```
is_assignee = (wo.assigned_to == frappe.session.user)
has_write   = frappe.has_permission("PM Work Order", ptype="write", doc=wo)
allowed     = is_assignee OR has_write
```
- `frappe.has_permission(..., doc=wo)` áp CẢ role-DocPerm write (PM Manager / PM User / Super Admin) LẪN row-level `pm_work_order_has_permission` hook (`permissions.py:443`) ⇒ **tái dùng IDOR-guard** — Vendor Engineer / KTV ngoài `assigned_to` → `has_write=False` → FORBIDDEN.
- KTV được giao luôn được đính ảnh cho chính WO của mình (ngay cả khi DocPerm write bị scope row-level `assigned_to`).

**Boundaries (Always / Never):**
- **Always:** File `is_private=1` (NĐ98 — ảnh thiết bị y tế KHÔNG public); check permission + idx + validation + max-count(=1, write-once) TRƯỚC `File.insert`; emit ĐÚNG 1 lifecycle event `pm_checklist_photo_attached` per success (không swallow); ghi `row.photo` bằng `db.set_value(update_modified=False)` (KHÔNG `wo.save()`); dùng CÙNG helper `_checklist_item_photos(row)` (đọc `row.photo`) cho cả max-count check LẪN read-side hiển thị (invariant **count==rows**, parity imm09 `_repair_checklist_item_photos`).
- **Never:** tạo File ở nhánh reject; `is_private=0`; `wo.save()` để set photo (re-validate BR-08-08 khi PM chưa xong → false-500); raise `frappe.throw`→HTTP-4xx cho lỗi nghiệp vụ (phải Decision-B HTTP-200); dùng event ngoài `pm_checklist_photo_attached` (giá trị ngoài Select `Asset Lifecycle Event` sẽ bị nuốt/throw); commit trước khi emit event (mất rollback-on-throw); leak raw cap trong message FORBIDDEN; đổi shape `get_pm_work_order` round này (chỉ đọc `r.photo` sẵn có).

### ADR-IMM08-PHOTO-01: Lưu ảnh bằng chứng PM = Frappe `File` private attach vào PM Work Order + discriminator per-mục; `photo` field mirror ảnh mới nhất
- **Status**: ⛔ **Superseded by ADR-IMM08-PHOTO-03** (2026-07-09) — code THẬT implement MAX=1 write-once trên `pm_checklist_result.photo` (Attach đơn trị), KHÔNG File-discriminator; giữ block này làm bản ghi lịch sử (P-DOC-3, KHÔNG xoá). Mọi mô tả "MAX=5 / `attached_to_field=checklist_results.photo.{idx}` / query bộ-3" DƯỚI ĐÂY là **KHÔNG còn hiệu lực** — đọc PHOTO-03. · **Date**: 2026-07-09
- **Context**: NĐ98 (thiết bị Class C/D) đòi ảnh bằng chứng **theo từng mục** checklist PM; `pm_checklist_result.photo` là field `Attach` **đơn trị** đã tồn tại (KHÔNG schema-change); `get_pm_work_order` đã trả `r.photo`; cần max-count per-mục với invariant **count==nguồn-liệt-kê** (mirror `_scene_photos` Vòng 1). Ràng buộc acceptance: `attached_to_doctype='PM Work Order'`, `attached_to_name=WO` (KHÔNG attach vào child-row).
- **Decision**: (1) store = Frappe `File` private, attach vào **parent WO**; phân biệt mục bằng **`attached_to_field = f"checklist_results.photo.{checklist_item_idx}"`** (khóa tổng hợp ổn định, KHÔNG trùng field thật trên PM Work Order ⇒ Frappe on-trash field-clear là no-op vô hại; ảnh evidence append-only nên on-trash gần như không xảy ra). (2) helper `_pm_checklist_photos(WO, idx)` query File theo bộ 3 (`attached_to_doctype/name/attached_to_field`) `order_by creation asc` → `[{file_url,file_name}]` = **1 SoT** cho max-count + mọi liệt kê per-item ⇒ count==rows. (3) `row.photo` (đơn trị) = `db.set_value` file_url **mới nhất** → phục vụ read-back parity + hiển thị thumbnail; get_pm_work_order KHÔNG đổi.
- **Alternatives**: (A) attach File vào child-row (`attached_to_doctype='PM Checklist Result'`, `attached_to_name=row.name`) → child-row name là hash ngẫu nhiên + resolve permission trên child doctype phức tạp + trái acceptance → loại. (B) 1-ảnh-mỗi-mục (MAX=1, ghi đè `photo`) → đơn giản hơn nhưng KHÔNG mirror `_scene_photos` max-count (=5) và mất ảnh cũ (vi phạm append-only NĐ98) → loại. (C) child table `pm_checklist_photos` (URL rows) → nhân đôi hạ tầng File + drift + schema-change → loại. (D) discriminator = filename-prefix → không ổn định (client đặt tên tùy ý) → loại.
- **Consequences**: 0 field mới / 0 child table; MAX_PM_CHECKLIST_PHOTOS=5 per mục; `row.photo` chỉ hiển thị ảnh mới nhất (bộ đầy đủ per-mục truy được qua helper — surface `checklist_item_photos[]` trong get_pm_work_order để `[ROADMAP]` round sau, out-of-scope). Đánh đổi: dựa trên `File.attached_to_field` như khóa nghiệp vụ (BE xác nhận Frappe chấp nhận chuỗi tùy ý ở cột này — nếu môi trường validate, fallback discriminator tương đương giữ invariant count==rows).

### ADR-IMM08-PHOTO-02: Audit đính ảnh PM = canonical `Asset Lifecycle Event` `pm_checklist_photo_attached` (thêm option Select) — hard-requirement
- **Status**: Accepted · **Date**: 2026-07-09
- **Context**: NĐ98 đòi evidence trail cho mọi thao tác trên hồ sơ PM; `Asset Lifecycle Event.event_type` là Select enum cố định (`asset_lifecycle_event.json`); `pm_checklist_photo_attached` CHƯA có trong options (hiện có `pm_started`, `pm_completed`, `incident_photo_attached` Vòng 1…).
- **Decision**: (1) **THÊM option `pm_checklist_photo_attached`** vào Select `event_type` của `Asset Lifecycle Event` (KHÔNG cần migration schema field khác — chỉ mở rộng enum → deploy `bench reload-doctype "Asset Lifecycle Event"`, HARD-STOP USER, KHÔNG chặn test vì test seed event trực tiếp). (2) emit canonical event ở success-path, **hard-requirement** (trong transaction, commit cùng File + set_value) — KHÁC event best-effort (`pm_started`) vì đây là **bản ghi bằng chứng** không được mất im lặng. Mirror ADR-IMM12-07.
- **Alternatives**: (A) tái dùng `pm_completed`/`pm_started` → sai nghĩa (đính ảnh ≠ hoàn thành PM), loại. (B) audit best-effort try/except-swallow → mất evidence im lặng, vi phạm NĐ98, loại.
- **Consequences**: enum +1; deploy cần reload-doctype 1 lần; test seed event bằng `create_lifecycle_event` không phụ thuộc reload live (không chặn `run-tests`). Đánh đổi: enum drift phải đồng bộ với `docs/mobile` nếu mobile map event-type.

### ADR-IMM08-PHOTO-03: RECONCILE ảnh/mục = **MAX=1 write-once** trên field `Attach` đơn trị hiện có (supersede ADR-IMM08-PHOTO-01)
- **Status**: Accepted (supersedes ADR-IMM08-PHOTO-01) · **Date**: 2026-07-09
- **Context (Self-Correction 3-chiều spec↔code↔FE)**: ADR-IMM08-PHOTO-01 (Accepted cùng ngày) chốt MAX=5 append-only qua File-discriminator `attached_to_field='checklist_results.photo.{idx}'` + loại tường minh phương án MAX=1. NHƯNG code THẬT — `MAX_PM_CHECKLIST_PHOTOS=1` (`services/imm08.py:38`), helper `_checklist_item_photos(row)` đọc `row.photo` (`:791-797`), `File.insert` KHÔNG set `attached_to_field` (`:866-874`), `db.set_value("PM Checklist Result", row.name, "photo", …)` (`:879-882`) — implement MAX=1 trên field `pm_checklist_result.photo` (Attach **đơn trị**, `pm_checklist_result.json:70-72`). FE doc `06_Frontend_Design.md §UX` ghi "Max 5 ảnh/mục". → lệch 3 chiều trên **1 quyết định tuân thủ NĐ98**. Sibling imm09 `ADR-IMM09-PHOTO-01` ĐÃ reconcile về MAX=1 và ghi rõ imm08-doc multi-photo là "bản mô tả cũ".
- **Decision**: SoT DUY NHẤT = **MAX_PM_CHECKLIST_PHOTOS=1**. Lưu `file_url` vào `row.photo` (Attach đơn trị, `db.set_value(update_modified=False)`), File private attach parent WO (`attached_to_doctype='PM Work Order'`, **KHÔNG** `attached_to_field`). Hành vi = **write-once**: mục đã có ảnh → ảnh thứ 2 bị **REJECT `VALIDATION`** (`"Mỗi mục checklist chỉ đính 1 ảnh"`), **KHÔNG ghi đè** (khác Alternative-B của ADR-01 vốn giả định overwrite → ADR-01 gán nhầm rủi ro).
- **Append-only NĐ98 posture (KHÔNG phải waiver, mà là SATISFIED)**: write-once **BẢO TOÀN** append-only — không bao giờ overwrite/xoá ảnh đã đính. NĐ98 (thiết bị Class C/D) đòi **CÓ** bằng chứng ảnh, KHÔNG quy định ≥5 ảnh/mục ⇒ 1 ảnh/mục là mức bằng chứng tối thiểu hợp lệ. Hạn chế còn lại = **SỐ LƯỢNG** (1 vs 5) = enhancement `[ROADMAP]`, KHÔNG phải lỗ hổng tuân thủ. (Nỗi lo "mất ảnh cũ" của ADR-01 áp cho biến thể overwrite — code KHÔNG overwrite.)
- **Đường thay-ảnh-có-audit `[ROADMAP]`**: write-once làm kẹt ảnh chụp lỗi (mờ/nhầm mục). Bổ sung sau endpoint `remove_pm_checklist_photo` (CHỈ khi WO chưa `Completed`) → xoá File + clear `row.photo` + lifecycle `pm_checklist_photo_removed` (audit) → cho đính lại. Đối xứng backlog Finding F (imm12 `incident_photo_removed`). Ngoài scope vòng này.
- **Multi-photo/mục (MAX=5) `[ROADMAP]`**: nếu NĐ98/khách yêu cầu >1 ảnh/mục → nâng qua File-query discriminator HOẶC child table `pm_checklist_photos` + surface `checklist_item_photos[]` trong `get_pm_work_order` (đúng như ADR-01 mô tả) — schema/BE-change, đo nhu cầu trước khi làm.
- **Alternatives**: (A) MAX=5 File-discriminator (ADR-01) → schema/complexity cao, `[ROADMAP]`. (B) MAX=1 **overwrite** → mất ảnh cũ (vi phạm append-only) → loại; chọn **write-once** thay thế. (C) child table `pm_checklist_photos` → nhân đôi hạ tầng File → loại.
- **Consequences**: **docs-only reconcile** (BE code đã đúng — KHÔNG đụng `services/imm08.py`); FE doc 06 sửa "Max 5"→"1 ảnh/mục"; parity với imm09 MAX=1. Đánh đổi: chưa multi-photo/mục tới khi `[ROADMAP]`; ảnh lỗi kẹt tới khi có remove-endpoint `[ROADMAP]`.

### ADR-IMM08-PHOTO-04 (CROSS-MODULE imm08/09/12): HEIC/HEIF policy = client transcode → JPEG tại nguồn; BE giữ allowlist JPG/PNG
- **Status**: Accepted · **Date**: 2026-07-09 · **Scope**: `attach_pm_checklist_photo` (imm08) · `attach_repair_checklist_photo` (imm09) · `attach_incident_photo` (imm12) — ADR canonical đặt ở đây, imm09/12 cross-link.
- **Context**: cả 3 endpoint allowlist `{image/jpeg, image/jpg, image/png}` (`_PM_PHOTO_CONTENT_TYPES` `imm08:40` / `_REPAIR_PHOTO_CONTENT_TYPES` `imm09:129` / `_INCIDENT_PHOTO_CONTENT_TYPES` `imm12:48`). iPhone mặc định chụp **HEIC/HEIF** ⇒ upload bị reject `"Tệp phải là ảnh JPG hoặc PNG"` ⇒ **KTV hiện trường mất bằng chứng NĐ98**. Nguồn phát HEIC = app mobile (repo riêng — Expo/RN, xem memory `mobile_app_build_docset`).
- **Decision**: **(c) client-side transcode HEIC/HEIF → JPEG TRƯỚC upload** ở app mobile (`expo-image-manipulator` `SaveFormat.JPEG` / `expo-image-picker`), giữ EXIF timestamp. BE allowlist **GIỮ NGUYÊN `{jpeg,png}`** làm contract-guarantee. Lý do: fix tại-nguồn, chuyển-mã-ở-thiết-bị (không re-encode lần 2 ở server), **0 dependency BE**, JPEG xem được ngay trong web-audit UI + sinh thumbnail.
- **Alternatives**:
  - (a) **BE transcode** HEIC→JPEG (`pillow-heif` + system `libheif`) → thêm native system-dependency trên MỌI site bệnh viện on-prem (deploy-risk) + re-encode lossy bằng chứng → **`[ROADMAP]` defensive fallback**, CHỈ bật nếu telemetry cho thấy HEIC-reject thực tế (measure-first). Loại làm primary vì gánh nặng deploy đa-site.
  - (b) **mở allowlist nhận HEIC** lưu as-is → HEIC **KHÔNG render** trên Chrome/Firefox/web-audit UI ⇒ auditor không xem được bằng chứng + thumbnail fail ⇒ phản mục tiêu NĐ98 → **loại**.
- **Consequences**: **BE 0 đổi** (allowlist giữ). Ràng buộc chuyển sang **mobile contract**: `docs/mobile` phải ghi "client PHẢI transcode HEIC/HEIF→JPEG trước upload; endpoint chỉ nhận `image/jpeg`,`image/png`". Web-FE: giữ pre-hint đuôi jpg/png. Đánh đổi: phụ thuộc mobile client làm đúng (không enforce được từ repo này) — bù bằng thông điệp lỗi rõ + `[ROADMAP]` (a) nếu cần robust cho web-desktop upload HEIC.

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
| `IMM08_CHECKLIST_EMPTY` _(bổ sung BR-08-19)_ | `IMM08-CHECKLIST-EMPTY` | warning | 422 | Chưa gắn bảng kiểm | Không thể hoàn thành PM: bảng kiểm chưa có mục nào (thiếu bảng kiểm mẫu) — vui lòng gắn bảng kiểm trước khi nghiệm thu. | Gắn bảng kiểm mẫu (PM Checklist Template) cho lệnh này rồi thử lại. |
| `IMM08_CHECKLIST_IDX_UNKNOWN` _(bổ sung BR-08-20, OPTIONAL)_ | `IMM08-CHECKLIST-IDX-UNKNOWN` | warning | 422 | Mục bảng kiểm không hợp lệ | Kết quả gửi lên tham chiếu mục bảng kiểm không tồn tại (idx {idx}) — không có mục nào được ghi nhận. | Tải lại lệnh để đồng bộ bảng kiểm rồi gửi lại. |
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
- **BR-08-19 (Vòng 3, bịt lỗ vacuous-pass):** trong CÙNG hook, THÊM guard TRƯỚC vòng lặp
  thiếu-result — `if not (doc.checklist_results or []): nthrow_in_hook(MSG.IMM08_CHECKLIST_EMPTY)`.
  Thêm `MSG.IMM08_CHECKLIST_EMPTY` vào `utils/messages.py` (bảng §11.2) + regen
  `frontend/src/i18n/messages.ts` (`python scripts/gen_fe_messages.py`). `submit_result`
  KHÔNG cần sửa (`wo.save()` → validate → ValidationError → `except` line ~1043 wrap
  `ServiceError(VALIDATION)`; status giữ + docstatus=0). **OPTIONAL BR-08-20:** guard idx-drift
  trong `submit_result` (khi WO ≥1 dòng) + `MSG.IMM08_CHECKLIST_IDX_UNKNOWN`.
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

## §12 CR-74 — Read-gate CHI TIẾT phiếu PM (`getPmWorkOrder`) — in-handler 403, ĐÓNG IDOR-đọc

> **SSoT quyết định:** [ADR-IMM00-LIST-SCOPE §9 — INV-ROWSCOPE-DETAIL (CR-74)](../imm-00/ADR-IMM00-LIST-SCOPE.md) · ADR-IMM00-DETAIL-READ-01/02/03 (D8/D9/D10).
> **Trạng thái:** ✅ **RESOLVED-BE 2026-07-25 (Bước-4)** — khuôn 3 lớp LANDED @`services/imm08.py:816-904` (`@rowscoped` :816 · L0 `assert_doctype_read_permission(_DT_PM_WO)` :829 · L1 `PMWorkOrderRepo.get` :830 · L2 `assert_can_read_doc` :833). **0 delta shape** (0 endpoint / 0 param / 0 field / 0 DocType / 0 DocPerm / 0 cap). Test: `test_rowscope_docperm_gate::TestDetailReadGateCR74` + `test_rowscope_invariant::TestDetailReadGateCR74Invariant` + guard tĩnh G5a/G5b (`test_rowscope_scope_guard`) — `test_imm08` **168 OK**. 🟡 Còn lại: **[FE] B13** (render 403 in-envelope, **KHÔNG logout**).

### §12.1 Vấn đề (verify @source 2026-07-25)

`services/imm08.py:814` `get_work_order` nạp bản ghi bằng `PMWorkOrderRepo.get(name)` → `frappe.get_doc` (`repositories/base.py:53-57`). **`frappe.get_doc` KHÔNG kiểm tra quyền** (`frappe/model/document.py:36`; kiểm tra nằm ở `Document.check_permission:227` — không đường nào chạm tới). Gate duy nhất đang có là `assert_vendor_can_access` ở API tier (`api/imm08.py:53-58`), mà hàm này **no-op cho mọi user KHÔNG mang role `Vendor Engineer`** (`services/shared/scope.py:192-193`).

⟹ Hệ quả: (a) persona **0 DocPerm read** trên `PM Work Order` vẫn đọc trọn hồ sơ qua URL trực tiếp; (b) KTV **có** DocPerm read vẫn mở được phiếu `assigned_to`/`supervisor` của đồng nghiệp — trong khi `list_work_orders` đã ẩn (`services/imm08.py` `scope="user"`, D4).

### §12.2 Hợp đồng SAU CR-74 — 3 lớp theo thứ tự BẮT BUỘC (D9)

| Lớp | Gọi gì | Khi hỏng | Vì sao thứ tự này |
|---|---|---|---|
| **L0 · ROLE** | `assert_doctype_read_permission("PM Work Order")` | `frappe.PermissionError` → `@rowscoped` → **HTTP-200** + `Error{success:false, code:"FORBIDDEN", http_status:403}` | Chạy **TRƯỚC** `exists` ⇒ thiếu quyền thì `name` bịa và `name` thật trả **cùng một** 403 ⇒ 0 existence-oracle (tiền lệ `api/imm00.py:483-509`) |
| **L1 · EXISTS** | `PMWorkOrderRepo.get(name)` → không có ⇒ `nthrow(`MSG.IMM08_WO_NOT_FOUND`)` | **HTTP-200** + `Error{code:"NOT_FOUND", http_status:404}` — **GIỮ NGUYÊN** | Chỉ người **CÓ** DocPerm read mới tới được đây ⇒ 404 không còn là kênh dò |
| **L2 · ROW** | `assert_can_read_doc("PM Work Order", doc)` → `frappe.has_permission("PM Work Order", ptype="read", doc=doc)` | như L0 (**403 in-envelope**) | Dispatch hook `hooks.py:452` (`pm_work_order_has_permission` `permissions.py:234-244` — KTV/NCC chỉ đọc phiếu có `assigned_to` **hoặc** `supervisor` == mình; senior/auditor `True`) — dùng **doc đã load ở L1** ⇒ **0 query thêm** |

**Bất biến giữ nguyên (A5 — KHÔNG gỡ, KHÔNG thay):** `assert_vendor_can_access("PM Work Order", name)` ở API tier **giữ nguyên vị trí + thứ tự**. Hai lớp cùng tồn tại: isolation NCC (API) ∧ read-gate (service). Vendor ngoài scope vẫn **403 in-envelope**, KHÔNG rơi nhánh 500.

### §12.3 Ma trận persona (KHÔNG đổi DocPerm — chỉ mô tả hệ quả)

| Persona | DocPerm read `PM Work Order` | Phiếu `assigned_to`/`supervisor` | Kết quả sau CR-74 |
|---|---|---|---|
| `AssetCore Super Admin` / `PM Manager` (senior `permissions.py:34-51`) | ✔ | bất kỳ | **200 success** — payload **byte-identical** trước/sau |
| `AssetCore Auditor` | ✔ (read-only) | bất kỳ | **200 success** |
| `PM User` (`_TECHNICIAN_ROLES` `permissions.py:50`) | ✔ | **của mình** | **200 success** |
| `PM User` | ✔ | **của người khác** | **403 in-envelope** (hook `permissions.py:234-244`) — trước CR-74: **200 + đọc trọn** |
| Persona thiếu DocPerm read (vd `Calibration User`, `Corrective User`, `Repair User`, `Vendor Engineer` — bảng ADR §8.5) | ✘ | bất kỳ | **403 in-envelope** (trước CR-74: đọc được trọn hồ sơ) |
| `Vendor Engineer` ngoài scope | (xem B2) | bất kỳ | **403** — lớp API tier, GIỮ NGUYÊN |

> ⚠️ **KHÔNG được "chữa" bằng cách cấp DocPerm/role.** Persona nào **cần** đọc thì mở riêng bằng ratify B2 (ADR §9.9), KHÔNG sửa trong vòng CR-74.

### §12.4 Envelope 403 — hợp đồng client (BR-00-DETAIL-403)

```json
{ "success": false, "error": "Không đủ quyền", "code": "FORBIDDEN", "http_status": 403 }
```

- **HTTP status-line = 200**; client route **theo GIÁ TRỊ** `body.success` / `body.http_status` — **KHÔNG** theo status-line.
- Client **PHẢI hiển thị message** và **KHÔNG logout** (phân biệt dispatcher-403 = hết phiên → re-auth).
- Body **KHÔNG** được chứa bất kỳ field nghiệp vụ nào (`asset_ref` · `assigned_to` · `overall_result` · `technician_notes` · `checklist_results[]`) — chỉ khoá của `Error` envelope.
- Message hằng `MSG.AUTH_FORBIDDEN` (`utils/messages.py:61` = `"AUTH-403"`) — **KHÔNG** mã lỗi mới.

### §12.5 Test bắt buộc (DoD — `bench --site miyano run-tests --module ...`, KHÔNG curl)

| TC | Điều kiện | Kỳ vọng | INV |
|---|---|---|---|
| `TC-PM-DETAILGATE-01` | user đăng nhập, **0 DocPerm read** `PM Work Order` | `success:false` · `code:"FORBIDDEN"` · `http_status:403` trên **HTTP-200**; 0 field nghiệp vụ | INV-DETAIL-1 |
| `TC-PM-DETAILGATE-02` | `PM User` có DocPerm read, phiếu `assigned_to`/`supervisor` **của người khác** | **403 in-envelope** (hook row-scope) | INV-DETAIL-2 |
| `TC-PM-DETAILGATE-03` | senior/auditor có DocPerm read | **200**, payload **byte-identical** baseline | INV-DETAIL-4 |
| `TC-PM-DETAILGATE-04` | 0 DocPerm read + `name` **KHÔNG tồn tại** | **403 y hệt** TC-01 (0 existence-oracle) | INV-DETAIL-5 |
| `TC-PM-DETAILGATE-05` | **có** DocPerm read + `name` **KHÔNG tồn tại** | **404 GIỮ NGUYÊN** (`MSG.IMM08_WO_NOT_FOUND`) | INV-DETAIL-6 |
| `TC-PM-DETAILGATE-06` | vendor ngoài scope | **403** từ API tier, KHÔNG 500 ⇒ 2 lớp cùng tồn tại | INV-DETAIL-7 |

> **BẮT BUỘC `frappe.set_user(<persona thật>)`** — `frappe/permissions.py:107-109` cho Administrator `return True` ngay ⇒ chạy bằng Administrator là **xanh giả**.

### §12.6 Boundaries

**Always** — gate ROLE trước `exists`; gate ROW trên doc đã load; lỗi quyền = HTTP-200 + Error envelope; test bằng persona thật.
**Ask-first** — cấp DocPerm read cho persona đang bị chặn (B2); nới `get_calendar` (P3) sang row-scope.
**Never** — ❌ sửa `permissions.py` / DocPerm / role JSON để test xanh · ❌ gỡ `assert_vendor_can_access` · ❌ trả `data` rỗng hay 404 thay 403 · ❌ dùng `doc.check_permission()` (msgprint rò `_server_messages`) · ❌ thêm path/opId/param/schema OAS · ❌ đổi shape payload success · ❌ `git commit/push` · `bench migrate` · reload gunicorn (HARD-STOP USER).

---

## §13 AC-CR-77 — `get_pm_work_order` phơi `available_actions[]` server-driven 4 CTA (hết "nút chết" + CTA ma `Cancelled`) 🟢 BE+OAS ĐÃ LAND (2026-07-26) · 🟡 FE Bước-4

> ✅ **ĐÃ LAND (BE Bước-4, 2026-07-26) — dòng THẬT sau khi land** (mọi cite `services/imm08.py:<dòng>` bên dưới là dòng LÚC CHỐT SPEC, đã dịch ~+180 vì khối hằng mới chèn ngay sau `RESCHEDULE_CTA_STATES`):
> `_PM_VALID_TRANSITIONS` **:127** · `RESCHEDULE_CTA_STATES` **:153** · `_CAP_PM_WRITE/_CAP_PM_SUBMIT/_CAP_PM_RESCHEDULE` **:163-165** · `RESCHEDULE_ACTION_STATES` **:175** · 4 hằng reason VI **:182-188** · `_PM_ACTION_SPECS` **:196-209** · `_pm_checklist_has_items` **:212-229** · `_build_pm_available_actions` **:231-302** · `get_work_order` **:968-1060** (emit `available_actions` **:1058**, `allowed_transitions` **:1052** GIỮ NGUYÊN) · `validate_work_order` **:530** (dùng chung predicate) · `assign_technician` **:1248** (+guard KTV rỗng **:1257-1258**) · `reschedule` **:1483** (guard **:1501** đọc `RESCHEDULE_ACTION_STATES`).
> **Verify:** `test_imm08` **182 OK** (14 TC mới `TestPmAvailableActions`) · `test_mobile_oas` **951 OK** (+9 `cr77_a..i`) · `test_mobile_docset` **9 OK**. Mutation-verified 3/3: cap drift ⇒ TC-PMCTA-06 ĐỎ · cite rot ⇒ `cr77_h` ĐỎ · thêm 1 phần tử `allowed_transitions` ⇒ TC-PMCTA-13 ĐỎ. **BLOCKED-RELOAD**: sửa `.py` ⇒ cần USER reload gunicorn (`--preload`) mới thấy trên HTTP live — KHÔNG chấm bằng curl.

> **SSoT quyết định:** ADR-IMM08-CTA-01 / -02 / -03 (cuối §13). **Tiền lệ:** CR-39 IMM-12 (`docs/imm-12/05 §18` + ADR-IMM12-09) và R1 QR-scan IMM-00 (`_build_available_actions`, `services/imm00.py`). **Mã CR:** tiền tố `AC-CR-` (sổ nội bộ) — **KHÔNG** trùng sổ mobile `CONTRACT-REQUESTS.md` (ở đó `CR-74m` = cùng ý tưởng nhưng đánh số khác; xem §13.9).

### §13.1 Vấn đề đo được (verify @source 2026-07-26 — 4 lỗ, không phải 1)

| # | Lỗ | Bằng chứng @source | Hệ quả người dùng |
|---|---|---|---|
| **D-1** | **NÚT CHẾT `start_work`** — FE gate bằng `allowedTransitions.includes('In Progress')` (`frontend/src/views/pm/PMWorkOrderDetailView.vue:196`), mà `'In Progress'` là đích hợp lệ ở **4** trạng thái (`_PM_VALID_TRANSITIONS` `services/imm08.py:128-139`: Open · Overdue · **Pending–Device Busy** · **Halted–Major Failure**). Enforcement `assign_technician` chỉ nhận **Open/Overdue** (`services/imm08.py:1096-1097` → `MSG.IMM08_BAD_STATE`) | advertise ⊋ enforce | KTV bấm "Bắt đầu bảo trì" ở phiếu *Hoãn vì máy bận* / *Dừng do lỗi nặng* → **lỗi sau khi bấm** |
| **D-2** | **CTA MA `Cancelled`** — `_PM_VALID_TRANSITIONS` khai `Cancelled` là đích hợp lệ từ **5** trạng thái, nhưng `api/imm08.py` **KHÔNG có endpoint hủy phiếu nào** (0 hàm `cancel*` whitelisted — verify toàn file) | hợp đồng OAS `PmWorkOrderDetail.allowed_transitions` nói "client render nút workflow" (`assetcore-mobile.openapi.yaml:9548`) | Client (đặc biệt **mobile mới**) render nút "Hủy phiếu" **không có đường đi** — bấm = 404/không làm gì |
| **D-3** | **CTA ẨN `reschedule`** — web chỉ render «Hoãn lịch» **bên trong banner quá hạn** (`PMWorkOrderDetailView.vue:272` `v-if="isOverdue"` → nút `:287`), trong khi `reschedule()` nhận **mọi** trạng thái trừ Completed/Cancelled (`services/imm08.py:1335-1336`) | enforce ⊋ advertise | Phiếu *Open* chưa quá hạn / *Đang thực hiện*: máy bận nhưng **không thấy nút Hoãn lịch** — đúng ca mà CR-45b sinh ra để mở (`RESCHEDULE_CTA_STATES`, `services/imm08.py:147-153`) nhưng client chưa dùng |
| **D-4** | **Predicate nhân bản 4 lần ở FE** — `canStart` / `canCompleteRender` / `canReschedule` / `canReportMajor` mỗi cái tự ghép `can('pm.*') && allowedTransitions.includes(...)` (`:91-107`, `:196`) | — | Mỗi lần BE đổi cap/transition → FE drift âm thầm (class-of-bug "RBAC dead-gate") |

**Cách sửa (1 quyết định cho cả 4 lỗ):** BE trả **mảng CTA có sẵn `enabled` + `reason`** — FE **chỉ render**, KHÔNG tự suy. `available_actions` = tập CTA **CÓ ENDPOINT THẬT** (⟹ `Cancelled` biến mất tự nhiên vì không có endpoint), `enabled` neo vào **CHÍNH predicate enforcement** (⟹ hết nút chết & hết CTA ẩn).

### §13.2 Hợp đồng — `get_pm_work_order` += `available_actions[]`

**Endpoint:** `GET assetcore.api.imm08.get_pm_work_order` (§0 #2 → service `get_work_order(name)` `services/imm08.py:817`). Auth/handler/envelope **KHÔNG đổi** (CR-74 3 lớp ROLE→EXISTS→ROW giữ nguyên, §12). Field **ADDITIVE**.

`get_work_order(name)` trả **THÊM** khoá `available_actions`: **mảng ĐÚNG 4 phần tử**, thứ tự **CỐ ĐỊNH** `[start_work, submit_result, reschedule, report_major_failure]`, **LUÔN đủ 4** kể cả khi `enabled=false`:

```jsonc
"available_actions": [
  { "key": "start_work",           "label": "Bắt đầu bảo trì",     "route": "", "enabled": true,  "reason": "" },
  { "key": "submit_result",        "label": "Hoàn thành bảo trì",  "route": "", "enabled": false, "reason": "Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu" },
  { "key": "reschedule",           "label": "Hoãn lịch",           "route": "", "enabled": true,  "reason": "" },
  { "key": "report_major_failure", "label": "Báo lỗi nghiêm trọng","route": "", "enabled": false, "reason": "Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu" }
]
```

- **Shape phần tử = `AvailableAction`** — **TÁI DÙNG** schema QR-scan/`IncidentDetail` `{key, label, route, enabled, reason}` (`assetcore-mobile.openapi.yaml:8005`). **KHÔNG mint schema mới** ⇒ OAS giữ **107 paths / 280 schemas**.
- `route` **luôn `""`** (4 CTA nằm **trong màn** chi tiết, KHÔNG deep-link; khoá giữ trong shape vì `required` của `AvailableAction` gồm `route`).
- **SSoT = `_build_pm_available_actions(wo)`** (`services/imm08.py`, gọi trong `get_work_order`). Spec helper + tuple `_PM_ACTION_SPECS`: `04 §4.3`.
- **READ-ONLY tuyệt đối** — chỉ đọc `wo.status` / `wo.assigned_to` / `len(wo.checklist_results)` + `rbac.can(...)`. KHÔNG audit / lifecycle / modify doc / query thêm (dữ liệu đã nạp ở L1 của CR-74).

### §13.3 Bảng 4 CTA — key ↔ endpoint THẬT ↔ cap SSoT (A2/A3)

| `key` | `label` (VI) | Endpoint whitelisted **CÓ THẬT** | Service | `target` | `from` (status nguồn) | `cap` (SSoT = `rbac.require` của endpoint) |
|---|---|---|---|---|---|---|
| `start_work` | Bắt đầu bảo trì | `assetcore.api.imm08.assign_technician` (`api/imm08.py:110`) | `assign_technician` (`services/imm08.py:1092`) | `In Progress` | `{Open, Overdue}` | **`pm.write`** (`api/imm08.py:114`) |
| `submit_result` | Hoàn thành bảo trì | `assetcore.api.imm08.submit_pm_result` (`:120`) | `submit_result` (`:1152`) | `Completed` | `{In Progress}` | **`pm.submit`** (`api/imm08.py:129`) |
| `reschedule` | Hoãn lịch | `assetcore.api.imm08.reschedule_pm` (`:157`) | `reschedule` (`:1320`) | `Pending–Device Busy` | `RESCHEDULE_ACTION_STATES` (§13.4-b) | **`pm.reschedule`** (`api/imm08.py:158`) |
| `report_major_failure` | Báo lỗi nghiêm trọng | `assetcore.api.imm08.report_major_failure` (`:145`) | `report_major_failure` (`:1257`) | `Halted–Major Failure` | `{In Progress}` | **`pm.write`** (`api/imm08.py:151`) |

> ⚠️ **`start_work` → `assign_technician` là ĐÚNG, không phải nhầm tên.** Trên màn chi tiết, "bắt đầu bảo trì" = **dispatch** (gán KTV hiện tại + flip `Open/Overdue → In Progress` + đặt thiết bị `Under Maintenance`) — chính là `assign_technician` (VERB-FLIP R35, §0.1.1). Tên `key` mô tả **CTA của màn**, tên endpoint mô tả **thao tác nghiệp vụ**.

> 🚫 **`Cancelled` TUYỆT ĐỐI không xuất hiện dưới dạng action** (A2). Nó **có** trong `_PM_VALID_TRANSITIONS` (đích hợp lệ từ 5 status) nhưng **KHÔNG có endpoint** ⇒ không có spec ⇒ không có phần tử. Guard: mỗi `key` phải **resolve động** ra một callable whitelisted trong `assetcore.api.imm08` (`fn in frappe.whitelisted`) — TC INV-PMCTA-5.

### §13.4 `enabled = transition_allowed ∩ has_cap ∩ business_gate` (A3)

| Tầng | Định nghĩa | Nguồn SSoT |
|---|---|---|
| `transition_allowed` | **(a) mặc định:** `spec.target ∈ _PM_VALID_TRANSITIONS[wo.status]` **∧** `wo.status ∈ spec.from`<br>**(b) riêng `reschedule`:** `wo.status ∈ RESCHEDULE_ACTION_STATES` (KHÔNG xét `target ∈ map` — `reschedule()` là **service action NGOÀI Frappe workflow**, workflow JSON không mô-hình-hoá `Open→Pending`/`Overdue→Pending`) | `_PM_VALID_TRANSITIONS` (`services/imm08.py:127`) + `from` per-CTA. **KHÔNG suy từ overlay `allowed_transitions`** (overlay là tầng emit, không phải predicate — ADR-IMM08-CTA-02) |
| `has_cap` | `rbac.can(spec.cap)` với cap **ĐÚNG bằng** cap mà endpoint ghi `rbac.require(...)` | Bảng §13.3. **CẤM** literal cap thứ 2 (drift cap = "gate nói dối"). Khuyến nghị hoist 3 hằng `_CAP_PM_WRITE/_CAP_PM_SUBMIT/_CAP_PM_RESCHEDULE` để advertise & enforce đọc **1 chỗ** |
| `business_gate` | `start_work`: `bool(wo.assigned_to)` — phiếu phải có KTV để dispatch<br>`submit_result`: `_pm_checklist_has_items(wo)` = `len(wo.checklist_results or []) > 0` (**BR-08-19**)<br>`reschedule` / `report_major_failure`: `True` | `_pm_checklist_has_items` = **CÙNG predicate** mà `validate_work_order` dùng để chặn (`services/imm08.py:379-380` → `MSG.IMM08_CHECKLIST_EMPTY`) ⇒ **advertise == enforce** (A5). `bool(assigned_to)` ⇔ guard mới ở `assign_technician` (§13.6-c) |

**Reason (CHỈ khi `enabled=false`) — 3 bậc ưu tiên `transition > capability > business-gate`, 100% tiếng Việt:**

| Hằng | Chuỗi VI | Dùng khi |
|---|---|---|
| `_PM_ACTION_REASON_TRANSITION` | `"Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu"` | `transition_allowed=False` — **phủ luôn** `status=""` và mã LẠ (mọi CTA đều fail bậc 1 vì `map.get(status, [])` rỗng / `status ∉ from`) ⇒ bất biến D9 luôn đúng |
| `_PM_ACTION_REASON_CAPABILITY` | `"Bạn không có quyền thực hiện thao tác này"` | transition OK nhưng thiếu cap |
| `_PM_ACTION_REASON_NO_TECHNICIAN` | `"Phiếu chưa được phân công kỹ thuật viên"` | chỉ `start_work` — business-gate chặn |
| `_PM_ACTION_REASON_CHECKLIST_EMPTY` | `"Chưa có mục bảng kiểm — không thể nghiệm thu phiếu bảo trì định kỳ"` | chỉ `submit_result` — business-gate chặn (BR-08-19) |

> 🇻🇳 **KHÔNG BAO GIỜ nội suy mã trạng thái thô** (`"In Progress"`, `"Halted–Major Failure"`…) vào `reason` — chuỗi status là tiếng Anh, nội suy = **rò EN ra UI** (vi phạm chính sách ngôn ngữ FE §06 §7 + A4). Reason là **hằng**, không f-string.

### §13.5 Bảng chân trị đầy đủ (oracle nghiệm thu) — đủ cap · `assigned_to` set · bảng kiểm ≥1 mục

| `status` | `start_work` | `submit_result` | `reschedule` | `report_major_failure` |
|---|---|---|---|---|
| `Open` | ✅ | ❌ transition | ✅ | ❌ transition |
| `Overdue` | ✅ | ❌ transition | ✅ | ❌ transition |
| `In Progress` | ❌ transition | ✅ | ✅ | ✅ |
| `Pending–Device Busy` | ❌ transition | ❌ transition | ✅ | ❌ transition |
| `Halted–Major Failure` | ❌ transition | ❌ transition | ✅ | ❌ transition |
| `Completed` | ❌ transition | ❌ transition | ❌ transition | ❌ transition |
| `Cancelled` | ❌ transition | ❌ transition | ❌ transition | ❌ transition |
| `""` / mã lạ (`"BOGUS"`) | ❌ transition | ❌ transition | ❌ transition | ❌ transition |

Biến thể: thiếu cap ⇒ ô ✅ thành ❌ **capability**; `assigned_to` rỗng ⇒ `start_work` ✅→❌ **no-technician**; bảng kiểm 0 mục ⇒ `submit_result` ✅→❌ **checklist-empty**.

### §13.6 Bất biến đo được (D9 — parity `imm00` / `imm12`)

| Invariant | Kỳ vọng |
|---|---|
| **INV-PMCTA-1** (reason ⟺ enabled) | `enabled is False` ⟹ `reason != ""`; `enabled is True` ⟹ `reason == ""` — với **MỌI** `status` kể cả `""` và mã lạ ngoài enum (A4) |
| **INV-PMCTA-2** (VI 100%) | mọi `reason` ∈ 4 hằng VI §13.4; **0 chuỗi EN** rò ra (kể cả qua nội suy status) |
| **INV-PMCTA-3** (đúng 4, thứ tự cố định, shape đúng) | `len == 4`; `key` theo thứ tự `[start_work, submit_result, reschedule, report_major_failure]`; mỗi phần tử **đúng 5 khoá** `{key,label,route,enabled,reason}`, `route == ""` (A1) |
| **INV-PMCTA-4** (key ↔ endpoint thật, 1-1) | mỗi `key` resolve động ra callable whitelisted trong `assetcore.api.imm08`; **`"cancel"`/`"Cancelled"` KHÔNG là `key` và KHÔNG là `target` của bất kỳ spec nào** (A2) |
| **INV-PMCTA-5** (cap parity advertise↔enforce) | tập `spec.cap` == tập cap trong `rbac.require(...)` của đúng 4 endpoint (đọc AST `api/imm08.py`, KHÔNG chép tay) — mirror kỹ thuật `cr73a_e`/`cr76_h` (A3) |
| **INV-PMCTA-6** (A5 display⇔enforcement · bảng kiểm rỗng) | phiếu `In Progress` **0 mục** bảng kiểm ⇒ `submit_result.enabled is False` + `reason == _PM_ACTION_REASON_CHECKLIST_EMPTY`; thêm **≥1 mục** ⇒ `enabled is True`. **CÙNG điều kiện** mà `validate_work_order` chặn bằng `MSG.IMM08_CHECKLIST_EMPTY` (`services/imm08.py:380`) |
| **INV-PMCTA-7** (advertise ⟹ enforce, không nút chết) | với mỗi CTA `enabled is True` (persona thật) ⟹ gọi endpoint tương ứng **KHÔNG** trả `FORBIDDEN` / `IMM08_BAD_STATE` / VALIDATION-precondition. Đặc biệt: `start_work.enabled` ⟺ `wo.status ∈ (Open, Overdue)` — **đóng D-1** |
| **INV-PMCTA-8** (reschedule display == enforcement) | với **cả 7** status: `reschedule.enabled` (đủ cap) ⟺ `reschedule(name, …)` **KHÔNG** raise guard terminal (`services/imm08.py:1335`) — 7/7 trùng khớp |
| **INV-PMCTA-9** (A6 back-compat) | `allowed_transitions` **GIỮ NGUYÊN 100%** (giá trị **+ thứ tự**, gồm overlay CR-45b `+Pending–Device Busy` cho Open/Overdue) cho cả 7 status ⇒ payload mới là **superset**, 0 client hiện hữu gãy. Key-set cũ bất biến (chỉ **thêm** 1 khoá) |
| **INV-PMCTA-10** (READ-ONLY) | gọi `get_work_order` KHÔNG tạo `IMM Audit Trail` / `Asset Lifecycle Event` / KHÔNG `save()` (`count-before == count-after`) |

### §13.7 Boundaries (Always / Never)

- **Always:** trả đủ **4** CTA thứ tự cố định (kể cả disabled); `enabled` = 3 tầng qua **SSoT** (`_PM_VALID_TRANSITIONS` + `RESCHEDULE_ACTION_STATES` + cap-hằng endpoint + `_pm_checklist_has_items`); `reason` VI non-empty khi disabled; `route=""`; READ-ONLY; `allowed_transitions` bất biến (superset-only).
- **Never:** ❌ mint schema OAS mới (phải `$ref AvailableAction`) · ❌ hardcode cap-string khác endpoint ghi · ❌ suy `enabled` từ **role-name** (chỉ `rbac.can`) · ❌ suy `reschedule` từ overlay `allowed_transitions` · ❌ đưa `Cancelled` (hoặc bất kỳ transition không-endpoint) thành action · ❌ nội suy mã status/EN vào `reason` · ❌ gate `submit_result` bằng duration/tem/"đã chấm hết mục" (3 thứ này đến từ **form lúc submit**, KHÔNG phải trạng thái phiếu — xem §13.8) · ❌ đổi shape/nghĩa `allowed_transitions` · ❌ thêm path/opId/param/schema · ❌ `bench migrate` · ❌ `git commit/push` (HARD-STOP USER).
- **Ask-first (KHÔNG làm trong vòng này — backlog §13.10):** mở `assign_technician` cho `Pending–Device Busy`/`Halted–Major Failure` (đường "tiếp tục bảo trì") · chặn `reschedule` ở `Halted–Major Failure` · thêm endpoint hủy phiếu PM.

### §13.8 Vì sao `submit_result.business_gate` CHỈ có "bảng kiểm rỗng"

`validate_work_order` (`services/imm08.py:365-390`) chặn hoàn thành bằng **4** cổng: (1) bảng kiểm RỖNG (BR-08-19) · (2) còn mục chưa chấm `result` (BR-08-08) · (3) `duration_minutes <= 0` (BR-08-09) · (4) chưa gắn tem (BR-08-10). **Chỉ (1) là thuộc tính của PHIẾU** tại thời điểm đọc; (2)(3)(4) là **giá trị người dùng nhập trong form submit** (`submit_pm_result` ghi đè `result`/`duration_minutes`/`pm_sticker_attached` từ payload trước khi save) ⇒ **không thể** đánh giá ở `get_work_order` mà không nói dối. Vì vậy:

- **Server** (`available_actions`): chỉ (1).
- **FE**: giữ nguyên `completionBlockReason` cho (2)(3)(4) như **lớp thứ hai**, tổ hợp `disabled = !action.enabled || formBlockReason !== ''`, tooltip `action.reason || formBlockReason` (§06 §3.4.a). Không xoá — xoá là mất cảnh báo tại chỗ.

### §13.9 Mobile contract (OAS mirror) — DELTA CHÍNH XÁC cho Bước-4

`PmWorkOrderDetail` (`docs/mobile/openapi/assetcore-mobile.openapi.yaml:9170`) **+= 1 property** `available_actions`, đặt **cạnh `allowed_transitions`** (mirror `IncidentDetail:9885`):

```yaml
        available_actions:
          type: array
          description: >
            4 CTA vòng đời phiếu PM (màn Chi tiết phiếu bảo trì định kỳ) SERVER-DRIVEN (AC-CR-77) —
            thứ tự CỐ ĐỊNH [start_work, submit_result, reschedule, report_major_failure], LUÔN đủ 4
            phần tử. Phần tử = AvailableAction (TÁI DÙNG schema QR-scan/IncidentDetail, KHÔNG mint
            schema mới). enabled = transition_allowed ∩ has_cap ∩ business_gate. transition_allowed
            dựa _PM_VALID_TRANSITIONS[status] (imm08.py:127) ∧ status ∈ spec.from; RIÊNG reschedule
            dùng RESCHEDULE_ACTION_STATES (service-action ngoài workflow — KHÔNG suy từ overlay
            Pending–Device Busy). has_cap = ĐÚNG cap endpoint ghi (start_work/report_major_failure→
            pm.write · submit_result→pm.submit · reschedule→pm.reschedule). business_gate: start_work
            = có assigned_to; submit_result = bảng kiểm ≥1 mục (BR-08-19, cùng predicate validator
            IMM08-CHECKLIST-EMPTY). Trạng thái 'Cancelled' KHÔNG BAO GIỜ là action (có trong bảng
            transition nhưng KHÔNG có endpoint). route="" (CTA nằm TRONG màn, KHÔNG deep-link).
            enabled=false ⟹ reason VI != ""; enabled=true ⟹ reason "". READ-ONLY (KHÔNG audit/
            lifecycle/modify). SSoT services/imm08.py:<DÒNG_THẬT> _build_pm_available_actions
            (gọi trong get_work_order). OPTIONAL (∉ required; additive trên schema MỞ
            additionalProperties:true — client cũ/mobile KHÔNG bắt buộc gen lại).
          items:
            $ref: '#/components/schemas/AvailableAction'
```

**Ràng buộc bất biến của OAS:** `required` GIỮ `['name']` · `additionalProperties: true` GIỮ · **paths 107 / schemas 280 KHÔNG đổi** · `AvailableAction` **KHÔNG sửa** (đang phục vụ 3 schema: QR-scan, `IncidentDetail`, nay `PmWorkOrderDetail`).

> 🔴 **RÀNG BUỘC THỨ TỰ (bài học CR-76 — cite-rot):** cite `services/imm08.py:<dòng> _build_pm_available_actions` phải nằm **TRONG `description`** (KHÔNG trong comment YAML — comment không vào spec đã parse ⇒ guard không bắt được) **và** dòng phải trỏ **trong vùng AST** của hàm. ⟹ **BE land `.py` TRƯỚC, rồi mới dán YAML + guard trong CÙNG vòng** (atomic). Dán YAML trước khi hàm tồn tại = guard ĐỎ ngay. Đây là lý do slice contract của AC-CR-77 **KHÔNG đóng được ở Bước-2** như CR-74/75/76.

**Guard hợp đồng (`assetcore/tests/test_mobile_oas.py`) — class MỚI `TestMobilePmAvailableActionsParity`, 9 TC `cr77_a..i`:**

| TC | Kiểm |
|---|---|
| `cr77_a` | `PmWorkOrderDetail.available_actions` tồn tại, `type: array` |
| `cr77_b` | `items.$ref == '#/components/schemas/AvailableAction'` (tái dùng — KHÔNG inline object) |
| `cr77_c` | `available_actions ∉ required`; `required` GIỮ `['name']` |
| `cr77_d` | `additionalProperties` GIỮ `true` |
| `cr77_e` | `paths == 107` và `components.schemas == 280` (0 path/opId/schema mới) |
| `cr77_f` | description nêu **đủ 4 key đúng thứ tự** + cụm "Cancelled … KHÔNG … action" (chống drift mô tả) |
| `cr77_g` | parity liên-màn: `PmWorkOrderDetail` và `IncidentDetail` cùng `$ref` **một** `AvailableAction` (1 từ vựng CTA cho mọi màn chi tiết) |
| `cr77_h` | **cite-parity AST**: mọi cite `services/imm08.py:<dòng> <symbol>` trong description **nằm trong vùng AST** của `<symbol>` (tái dùng kỹ thuật `cr74_g`/`cr75_i`/`cr76_h`; **lưu ý `cr74_g` chỉ quét description của OP, KHÔNG quét schema** ⇒ TC này bắt buộc) |
| `cr77_i` | **parity OAS ↔ BE**: 4 key trong description == `[s["key"] for s in services.imm08._PM_ACTION_SPECS]` (import thật, chống drift 2 chiều) |

**Counter guard — cộng theo DELTA `+9`, ĐỌC TẠI CHỖ trước khi sửa** (bài học: số tuyệt đối có thể stale nếu CR khác landed xen giữa):

| Counter | File:dòng | Giá trị đọc lúc chốt spec (2026-07-26) | Sau AC-CR-77 |
|---|---|---|---|
| `_EXPECTED_TEST_COUNT` | `assetcore/tests/test_mobile_oas.py:212` | 942 | 951 |
| `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` | `assetcore/tests/test_mobile_docset.py:781` | 942 | 951 |
| `_GUARD_SUITE_SUM` | `assetcore/tests/test_mobile_docset.py:949` | 1085 | 1094 |
| `_MOBILE_OAS_TOTAL` | `assetcore/tests/test_mobile_docset.py:1138` | 1111 | 1120 |
| delta-name MỚI | `test_mobile_docset.py` | — | `cr77_pm_available_actions_delta = 9` |

**Quan hệ với sổ CR mobile:** `CONTRACT-REQUESTS.md` (repo `/home/miyano/assetcore-mobile`) đã mở **CR-74m** = `available_actions[]` cho **cả** `PmWorkOrderDetail` **và** `RepairWorkOrderDetail`. AC-CR-77 đóng **nửa PM**; **nửa CM (`RepairWorkOrderDetail`) VẪN MỞ** → backlog `[BA] AC-CR-78` (cùng khuôn, endpoint CM: `start_repair`/`complete_repair`/`cannot_repair`… — phải khảo sát `api/imm09.py` trước, KHÔNG copy mù).

### §13.10 Phát hiện phụ (KHÔNG sửa trong vòng này — backlog có bằng chứng)

| # | Phát hiện | Bằng chứng | Đề xuất |
|---|---|---|---|
| **B1** | **Không có đường "tiếp tục bảo trì"** — `_PM_VALID_TRANSITIONS` khai `Pending–Device Busy → In Progress` và `Halted–Major Failure → In Progress`, nhưng **0 endpoint** thực hiện (chỉ `assign_technician`, mà nó chặn 2 status này) | `services/imm08.py:135-138` vs `:1096` | **[BA-P1]** ratify: nới `assign_technician` (thêm 2 status vào guard) **hay** thêm endpoint `resume_pm`? Cho tới lúc đó `start_work` **phải** disabled ở 2 status này (đúng như spec này) |
| **B2** | **Nút CHẾT `cta-resume` ở FE** — "Tiếp tục bảo trì" chỉ gọi `store.fetchWorkOrder(props.id)` (refetch), **không** đổi trạng thái gì | `PMWorkOrderDetailView.vue:288` | **[FE-P1]** ẩn nút hoặc đổi nhãn "Tải lại" cho tới khi B1 ratify (LL-FE-47 dead-control) |
| **B3** | **`report_major_failure` KHÔNG có guard trạng thái** — set thẳng `Halted–Major Failure` từ **bất kỳ** status (kể cả `Completed`/`Cancelled`) qua `set_values` (bỏ qua `validate`) | `services/imm08.py:1257-1263` | **[BE-P1]** thêm guard `status ∈ {In Progress}` (mirror `_PM_VALID_TRANSITIONS`). Hiện `available_actions` đã **hẹp hơn** enforcement (fail-safe, KHÔNG sinh nút chết) nhưng lỗ vẫn mở với client gọi thẳng |
| **B4** | **`reschedule` xoá tín hiệu `Halted–Major Failure`** — dời lịch từ trạng thái này ghi đè `status → Pending–Device Busy` | `services/imm08.py:1336-1338` | **[BA-P2]** ratify có nên chặn; nếu chặn → sửa **1 chỗ** `RESCHEDULE_ACTION_STATES` (display + enforcement đổi **cùng lúc** nhờ dùng chung predicate) |

### ADR-IMM08-CTA-01: `available_actions` = tập CTA **CÓ ENDPOINT**, KHÔNG phải mirror bảng transition
- **Status**: Accepted · **Date**: 2026-07-26
- **Context**: `allowed_transitions` (CR-45b/R21) là **mirror máy trạng thái** — nó nói "trạng thái kế hợp lệ", KHÔNG nói "có thao tác nào để tới đó". Hai lỗ sinh ra từ việc client hiểu nó là danh sách nút: `Cancelled` (đích hợp lệ, **0 endpoint** — CTA ma, D-2) và `In Progress` (đích hợp lệ ở 4 status nhưng endpoint chỉ nhận 2 — nút chết, D-1).
- **Decision**: `available_actions` được sinh từ **`_PM_ACTION_SPECS`** — danh sách **THAO TÁC** (mỗi spec bắt buộc trỏ tới **1 endpoint whitelisted có thật**), KHÔNG sinh từ `_PM_VALID_TRANSITIONS`. Bảng transition chỉ tham gia làm **1 trong 3 điều kiện** của `enabled`. `allowed_transitions` **giữ nguyên** (back-compat A6) và tiếp tục mang nghĩa "máy trạng thái", KHÔNG mang nghĩa "nút".
- **Alternatives**: (A) sinh action từ `_PM_VALID_TRANSITIONS` + bảng loại trừ `Cancelled` → danh sách đúng *hôm nay* nhưng mọi transition mới lại đẻ CTA ma → loại. (B) xoá `Cancelled` khỏi `_PM_VALID_TRANSITIONS` → sai mô hình (workflow JSON **thật sự** có transition hủy ở tầng desk) + vỡ parity-guard map↔workflow → loại. (C) để FE tự lọc → chính là lỗi đang sửa → loại.
- **Consequences**: thêm 1 SSoT nhỏ (`_PM_ACTION_SPECS`, 4 dòng) và 1 guard "key ⇒ endpoint whitelisted tồn tại" (INV-PMCTA-4). Đổi lại: thêm transition vào workflow **không** tự đẻ nút; thêm endpoint mới **bắt buộc** khai spec mới → CTA và endpoint không bao giờ lệch. Nghĩa của `allowed_transitions` được giữ nguyên cho client cũ.

### ADR-IMM08-CTA-02 (Self-Correction đề mục): `from` của `reschedule` = `RESCHEDULE_ACTION_STATES` (⊇ `RESCHEDULE_CTA_STATES`), dùng CHUNG với enforcement
- **Status**: Accepted · **Date**: 2026-07-26 · **Extends**: ADR-IMM08-RESCHED-CTA (CR-45b), ADR-IMM08-RESCHED-GUARD
- **Context**: Đề mục yêu cầu `reschedule` dùng `RESCHEDULE_CTA_STATES` (`= {Open, Overdue}`, `services/imm08.py:153`) và **không** suy từ overlay. Vế "không suy từ overlay" là **đúng** (overlay `allowed_transitions` là tầng emit, không phải predicate). Nhưng dùng **đúng bằng** `{Open, Overdue}` thì sai ở 2 chỗ đo được: (1) **regression FE** — hôm nay web vẫn render «Hoãn lịch» ở `In Progress` (qua `allowedTransitions.includes('Pending–Device Busy')`, edge có sẵn trong workflow) ⇒ đổi sang server-driven mà chỉ cho `{Open, Overdue}` là **mất nút** ở đúng ca KTV đang làm dở thì máy bị trưng dụng; (2) **display ≠ enforcement** — `reschedule()` nhận **mọi** status trừ `Completed`/`Cancelled` (`:1335`) ⇒ ở `Pending–Device Busy` (máy vẫn bận, cần dời tiếp) và `Halted–Major Failure` (máy đang sửa) server **cho phép** nhưng UI **báo không được**. Đây đúng class-of-bug "display ⇔ enforcement parity" mà dự án đã dính 2 lần liên tiếp (CR-54 G05, CR-76 G01/G03).
- **Decision**: khai **1 hằng SSoT** `RESCHEDULE_ACTION_STATES = frozenset(_PM_VALID_TRANSITIONS) - {PMStatus.COMPLETED, PMStatus.CANCELLED}` (= 5 status không-terminal) và dùng nó ở **CẢ HAI** phía: `_build_pm_available_actions` (advertise) **và** `reschedule()` (enforce — thay literal `if wo.status in (COMPLETED, CANCELLED)` bằng `if wo.status not in RESCHEDULE_ACTION_STATES`, **0 đổi hành vi**: cùng đúng 2 status bị chặn). `RESCHEDULE_CTA_STATES` **GIỮ NGUYÊN** (overlay CR-45b bất biến — A6) và được neo bằng invariant `RESCHEDULE_CTA_STATES ⊆ RESCHEDULE_ACTION_STATES` (test), nên hằng gốc của đề mục vẫn là mỏ neo, không bị bỏ rơi.
- **Alternatives**: (A) `from = RESCHEDULE_CTA_STATES` nguyên văn → 2 lỗi trên → loại. (B) `from = RESCHEDULE_CTA_STATES ∪ {In Progress}` → hết regression nhưng vẫn lệch enforcement ở 2 status → loại. (C) siết `reschedule()` xuống `{Open, Overdue}` cho khớp → **đổi hành vi endpoint đang chạy** (mobile/web đang dùng), ngoài phạm vi CR → loại. (D) mở rộng `RESCHEDULE_CTA_STATES` tại chỗ → **đổi overlay** `allowed_transitions` ở `Pending–Device Busy` ⇒ **vỡ A6** → loại.
- **Consequences**: `reschedule.enabled` = "phiếu chưa đóng" — dễ giải thích, 7/7 status khớp enforcement (INV-PMCTA-8). Nếu sau này ratify chặn dời lịch ở `Halted–Major Failure` (B4) thì sửa **1 dòng** và cả 2 phía đổi cùng lúc. Chi phí: 1 hằng mới + 1 invariant neo với hằng cũ.

### ADR-IMM08-CTA-03: `business_gate` chỉ nhận predicate **thuộc trạng thái phiếu**, dùng CHUNG với validator
- **Status**: Accepted · **Date**: 2026-07-26
- **Context**: Màn hoàn thành PM có 4 cổng (BR-08-08/09/10/19). Nếu `available_actions` cố "đoán" cả 4 thì `submit_result.enabled` sẽ **luôn false** cho mọi phiếu chưa nhập form (duration=0, tem chưa tick) ⇒ nút chết kiểu ngược, và server phải **đoán** dữ liệu người dùng sắp nhập.
- **Decision**: `business_gate` **chỉ** chứa predicate đọc được từ **trạng thái phiếu tại lúc GET** — với `submit_result` là `_pm_checklist_has_items(wo)` (BR-08-19), với `start_work` là `bool(wo.assigned_to)`. Predicate này **DÙNG CHUNG** với `validate_work_order` (advertise == enforce). 3 cổng còn lại (mục chưa chấm / duration / tem) thuộc **form-layer** và ở lại FE (`completionBlockReason`) như lớp 2 — có tooltip riêng, không bị server ghi đè.
- **Alternatives**: (A) đưa cả 4 vào server → false-negative toàn cục → loại. (B) bỏ hẳn business_gate (chỉ transition+cap) → `submit_result` bật ở phiếu 0 mục bảng kiểm ⇒ bấm là dính `IMM08-CHECKLIST-EMPTY` (đúng lỗi A5 muốn diệt) → loại.
- **Consequences**: FE có **2 lớp** disable (server-reason + form-reason) — phải hợp nhất tooltip theo thứ tự `action.reason || formBlockReason` (§06 §3.4.a) để không hiện 2 thông điệp mâu thuẫn.

### §13.11 Handoff Bước-4 (thứ tự BẮT BUỘC, atomic trong 1 vòng)

1. **[BE]** `services/imm08.py`: `+ from assetcore.services.shared import rbac` · 3 hằng cap · 4 hằng reason VI · `RESCHEDULE_ACTION_STATES` · `_PM_ACTION_SPECS` · `_pm_checklist_has_items(doc)` (và **dùng lại** trong `validate_work_order:379`) · `_build_pm_available_actions(wo)` · `get_work_order` += `"available_actions"` · `reschedule()` dùng `RESCHEDULE_ACTION_STATES` · `assign_technician` guard `technician` rỗng. Chi tiết: `04 §4.3`.
2. **[BE]** `assetcore/tests/test_imm08.py`: class `TestPmAvailableActions` — INV-PMCTA-1..10 (`07 §IX`), **RED-before** với ít nhất INV-PMCTA-4 (`Cancelled`) và INV-PMCTA-6 (A5).
3. **[BE]** *(sau bước 1 — cần dòng THẬT)* OAS `docs/mobile/openapi/assetcore-mobile.openapi.yaml` §13.9 + `test_mobile_oas.py` class `TestMobilePmAvailableActionsParity` (9 TC) + 4 counter (+9) + delta-name ở `test_mobile_docset.py`.
4. **[FE]** `frontend/src/api/imm08.ts` (type `AvailableAction` + `available_actions?`) · `PMWorkOrderDetailView.vue` render 4 CTA từ payload + fallback đường cũ khi thiếu khoá · test render mới. Chi tiết: `06 §3.4.a`.
5. **DoD:** `bench --site miyano run-tests --module assetcore.tests.test_imm08` · `...test_mobile_oas` · `...test_mobile_docset` (timeout tool **≥600000ms**, module-isolated) + `vue-tsc --noEmit` 0 lỗi + `vitest run` file test mới. **KHÔNG curl** (BLOCKED-RELOAD gunicorn `--preload`), **KHÔNG `bench migrate`**, **KHÔNG `npm run build`**.

## §14 AC-CR-79 — Whitelist khoá `filters` cho `list_pm_work_orders` (SSoT) · khoá lạ = **400 in-envelope**, hết HTTP-500 lộ SQL 🔴 SPEC (BE+FE Bước-4)

> **Canonical section của AC-CR-79.** IMM-09 (`list_repair_work_orders`) là **mirror**: chỉ khác tập khoá +
> tên module — xem [`docs/imm-09/05_API_Specification.md §14`](../imm-09/05_API_Specification.md).
> Đóng **`CR-70`** sổ mobile (`/home/miyano/assetcore-mobile/docs/api/CONTRACT-REQUESTS.md:3073`) **kèm cải chính**
> (§14.9): mô tả "BE bỏ qua im lặng" trong CR-70 là **SAI** với imm08/imm09 — BE **CRASH**.

### §14.1 Vấn đề đo được — probe LIVE 2026-07-27 (`bench --site miyano console`, KHÔNG suy đoán)

| # | Probe | Kết quả THẬT |
|---|---|---|
| P1 | `imm08.list_work_orders({"khong_ton_tai_abc": "x"})` | `OperationalError (1054, "Unknown column 'tabPM Work Order.khong_ton_tai_abc' in 'WHERE'")` |
| P2 | `imm09.list_work_orders({"khong_ton_tai_abc": "x"})` | `OperationalError (1054, "Unknown column 'tabAsset Repair.khong_ton_tai_abc' in 'WHERE'")` |
| **P3** | `imm08.list_work_orders({"due_date_from": ["2026-01-01"], "due_date_to": ["2026-12-31"]})` | `OperationalError (1054, "Unknown column 'tabPM Work Order.due_date_from' in 'WHERE'")` — **web FE gửi ĐÚNG 2 khoá này** (`frontend/src/views/pm/PMWorkOrderListView.vue:72-73`) ⇒ **bộ lọc khoảng ngày của màn PM đang 500 THẬT trên production** |
| P4 | `imm09.list_work_orders({"sla_breached":"1","is_repeat_failure":"1"})` | `OK` (2 cột THẬT trên `Asset Repair`) — đối chứng chống vacuous |
| P5 | `imm11.list_calibrations({"khong_ton_tai_abc": "x"})` | `OperationalError (1054, "Unknown column 'tabIMM Asset Calibration...")` — **CÙNG lớp lỗi, NGOÀI phạm vi vòng này** (§14.10 backlog) |

**Vì sao thoát ra HTTP-500 thô:** `assetcore/utils/api_handler.py:44-49` **CỐ Ý** chỉ bắt `ServiceError`
("KHÔNG bắt Exception chung … system error phải đi qua Frappe global handler"). `OperationalError` không phải
`ServiceError` ⇒ bubble → HTTP-500 **KHÔNG có `body.success`**. Hệ quả đo được:

1. **Client mobile route theo `body.success` ⇒ không phân loại được** — rơi vào nhánh "lỗi mạng/hệ thống", có
   app còn hiểu nhầm là hết phiên → **đăng xuất người dùng** (cùng lớp bug đã đóng ở BR-00-ROWSCOPE-403).
2. **Lộ tên bảng/cột SQL** (`tabPM Work Order`, `tabAsset Repair`) — vi phạm nguyên tắc "không leak schema"
   mà `run_rowscoped` (`services/shared/permissions.py:160-162`) đã tuân thủ cho nhánh 403.
3. **Lỗi INPUT bị gắn nhãn lỗi SERVER** — 5xx làm nhiễu alerting/Error Log, che sự cố thật.

### §14.2 Hợp đồng SAU AC-CR-79

`GET /api/method/assetcore.api.imm08.list_pm_work_orders`

**Nhánh khoá hợp lệ** — **KHÔNG ĐỔI GÌ**: payload success byte-identical baseline (A5, §14.6).

**Nhánh khoá lạ** — HTTP **200** + Error envelope:

> 🔴 **CẢI CHÍNH SHAPE (BE Bước-4, 2026-07-27):** bản Bước-2 vẽ envelope **lồng** (`error: {code, message, …}`).
> Envelope THẬT của AssetCore là **PHẲNG** — `utils/response._err` (`:130-140`) và schema OAS `Error`
> (`additionalProperties: false`, `error` **kiểu string**). Đổi sang shape lồng = breaking **mọi** client của
> **mọi** endpoint (Hyrum) ⇒ BE giữ nguyên shape phẳng; JSON dưới đây là payload **đo được**.

```json
{
  "success": false,
  "error": "Bộ lọc chứa khoá không được hỗ trợ: khong_ton_tai_abc. Các khoá hợp lệ: asset_ref, assigned_to, completion_date, due_before, due_date, is_late, name, overall_result, overdue, overdue_live, pm_type, search, source_pm_wo, status, supervisor, wo_type.",
  "code": "INVALID_PARAMS",
  "http_status": 400,
  "message_code": "VAL-INVALID-FILTER-KEY",
  "title": "Bộ lọc không hợp lệ",
  "severity": "warning",
  "action_hint": "Bỏ các khoá lọc không hợp lệ rồi thử lại. Nếu bạn không tự đặt bộ lọc này, hãy tải lại trang.",
  "context": {
    "invalid_keys": "khong_ton_tai_abc",
    "allowed_keys": "asset_ref, assigned_to, …, wo_type"
  }
}
```

**Bất biến observable (client route theo đây):**

| Thuộc tính | Giá trị CỐ ĐỊNH | Vì sao |
|---|---|---|
| HTTP status-line | **200** | Decision-B in-handler (LL-BE-42..49) — lỗi nghiệp vụ KHÔNG raise→4xx |
| `body.success` | `false` | client phân loại được (đóng CR-70) |
| `code` (top-level, KHÔNG `error.code` — envelope PHẲNG) | **`INVALID_PARAMS`** | bucket ĐÃ CÓ, `_HTTP_TO_BUCKET[400]` (`utils/notify.py:38`); **KHÔNG thêm bucket mới** (ADR-IMM08-FILTERKEY-02) |
| `http_status` (top-level) | **400** | lỗi INPUT, không phải 5xx |
| `message_code` (top-level) | **`VAL-INVALID-FILTER-KEY`** | phân biệt với malformed-JSON (`VAL-INVALID-PARAMS`) cho telemetry/i18n |
| message | **tiếng Việt**, nêu **khoá sai** + **tập khoá hợp lệ** | AC1 |

**Assert phủ định (bắt buộc, AC1):** với probe `{"khong_ton_tai_abc":"x"}`, chuỗi `json.dumps(resp, ensure_ascii=False)`
**KHÔNG** chứa: `Unknown column` · `tabPM Work Order` · `tabAsset Repair` · `OperationalError` · `SELECT`.

### §14.3 `_ALLOWED_FILTER_KEYS` (IMM-08) — **16 khoá**, mỗi khoá có consumer THẬT

SSoT khai ở `services/imm08.py` (mirror precedent `services/imm04.py:133 _ALLOWED_FILTER_KEYS`). **KHÔNG bản
chép tay thứ hai** — OAS và test **đọc/so** với hằng này (AC2).

| Khoá | Loại | Consumer / bằng chứng |
|---|---|---|
| `name` | cột | PK trả trong `_PM_LIST_FIELDS` (`services/imm08.py:783`) — nhảy thẳng theo mã phiếu |
| `status` | cột | `PMWorkOrderListView.vue:71` · `PMDashboardView.vue:19` · ví dụ OAS |
| `asset_ref` | cột | `PMWorkOrderListView.vue:74` · **`apply_vendor_scope` bơm** (`services/shared/scope.py:114`) — AC4 |
| `assigned_to` | cột | `api/imm08.py:41` (`mine=1`) |
| `supervisor` | cột | `_PM_LIST_FIELDS` |
| `pm_type` | cột | `_PM_LIST_FIELDS` |
| `wo_type` | cột | `_PM_LIST_FIELDS` |
| `due_date` | cột | đích của cửa-sổ `due_before`; **khoảng ngày dùng khoá này** (§14.4) |
| `completion_date` | cột | `_PM_LIST_FIELDS` |
| `overall_result` | cột | `_PM_LIST_FIELDS` |
| `is_late` | cột | `_PM_LIST_FIELDS` (BR-08-05) |
| `source_pm_wo` | cột | `_PM_LIST_FIELDS` (BR-08-02) |
| `overdue` | **ảo** | `PMWorkOrderListView.vue:69` → `_normalize_filters` (`services/imm08.py:461`) → `status = Overdue` |
| `due_before` | **ảo** | `PMWorkOrderListView.vue:70` → `due_soon_filter` (BR-08-12) |
| `overdue_live` | **ảo** | chip mobile "Quá hạn" → `_list_pm_overdue_live` (`services/imm08.py:931`) |
| `search` | **ảo** | `api/imm08.py:47` → `pop_search` (`services/shared/filters.py:162`) |

**Khoá CỐ Ý KHÔNG whitelist** (có trên DocType nhưng **0 consumer**): `workflow_state`, `pm_schedule`,
`scheduled_date`, `assigned_by`, `duration_minutes`, `pm_sticker_attached`, `technician_notes`, và 2 child
table `checklist_results`/`attachments` (child table **không filter được** ở `frappe.get_list` parent).
→ Luật: **thêm khoá CHỈ khi có consumer THẬT + TC**, không "thêm cho đủ" (Boundaries §14.8).

### §14.4 Khoảng ngày = **toán tử Frappe trên `due_date`**, KHÔNG đẻ khoá `due_date_from`/`due_date_to`

`_normalize_filters` (`services/imm08.py:450-478`) **đã** cho lọt nguyên dạng mọi giá trị `[<op>, <v>]` với
`op ∈ _OP_TOKENS` (`:447` — `in, not in, between, like, =, !=, <, >, <=, >=`). Vì vậy khoảng ngày **đã dùng
được ngay** bằng khoá đã whitelist:

| Ý định | `filters` ĐÚNG |
|---|---|
| Từ ngày → đến ngày | `{"due_date": ["between", ["2026-01-01", "2026-12-31"]]}` |
| Chỉ "từ ngày" | `{"due_date": [">=", "2026-01-01"]}` |
| Chỉ "đến ngày" | `{"due_date": ["<=", "2026-12-31"]}` |
| Nhiều trạng thái | `{"status": ["in", ["Open", "In Progress"]]}` |

⇒ **BE KHÔNG thêm khoá ảo mới.** Thay vào đó **FE sửa** `PMWorkOrderListView.vue:72-73` (§14.7) — đây là
Self-Correction: khoá `due_date_from`/`due_date_to` **chưa từng tồn tại ở BE**, FE tự bịa ⇒ 500 im lặng
(P3 §14.1). Xem **ADR-IMM08-FILTERKEY-03**.

### §14.5 Vị trí validate — **TRƯỚC** mọi biến đổi (AC5)

```
api/imm08.list_pm_work_orders
  ├ parse_json(filters)                     ← malformed JSON  → VAL-INVALID-PARAMS (đã có)
  ├ apply_vendor_scope(f, "PM Work Order")  ← bơm asset_ref   (∈ whitelist — AC4)
  ├ f["assigned_to"] = session.user          nếu mine=1        (∈ whitelist)
  ├ f["search"] = …                          nếu search khác rỗng (∈ whitelist)
  └ handle(svc.list_work_orders, f, …)
        └ services.imm08.list_work_orders
             ├ ① assert_allowed_filter_keys(filters, _ALLOWED_FILTER_KEYS)   ← ĐIỂM CẮM DUY NHẤT
             └ ② run_rowscoped(_list_work_orders, …)
                    ├ pop overdue_live        (③)
                    ├ pop_search              (④)
                    └ _normalize_filters      (⑤)
```

① **trước** ③④⑤ ⇒ khoá ảo (`search`/`overdue`/`overdue_live`/`due_before`) vẫn còn trong dict lúc validate
⇒ **phải nằm trong whitelist**; và **ngữ nghĩa khoá ảo KHÔNG đổi** (AC5). ① đặt ở entrypoint công khai
`list_work_orders`, **ngoài** `run_rowscoped` — `ServiceError` không phải `PermissionError` nên không bị
nhánh 403 nuốt.

### §14.6 Bất biến KHÔNG được đổi (A5 — no-regress)

| ID | Bất biến |
|---|---|
| INV-FKEY-1 | 16 khoá PM / 18 khoá CM **honor y hệt baseline** — rows + `pagination` byte-identical |
| INV-FKEY-2 | `pagination.total == len(data.data)` (**INV-ROWSCOPE**) giữ cho ≥1 persona row-scoped với filter hợp lệ |
| INV-FKEY-3 | Vendor Engineer **KHÔNG bị 400 oan**: `_VENDOR_SCOPE_FIELD_MAP["PM Work Order"]` (`scope.py:114`) ∈ whitelist — guard **tính từ map**, không hardcode (AC4) |
| INV-FKEY-4 | `filters` **rỗng/absent** (`'{}'`) ⇒ **không** validate lỗi (whitelist chỉ chặn khoá LẠ, không bắt buộc khoá nào) |
| INV-FKEY-5 | malformed JSON vẫn đi đường cũ `parse_json`, **không** bị AC-CR-79 nuốt. 🔴 **Cải chính BE Bước-4:** `parse_json` (`utils/api_handler.py:104-113`) raise `ServiceError` **legacy KHÔNG `message_code`** ⇒ envelope chỉ có `code=INVALID_PARAMS`/`http_status=400`, **KHÔNG** có `VAL-INVALID-PARAMS`. Bất biến load-bearing = **phân biệt được** 2 cách hỏng của cùng tham số `filters` (khoá-lạ có `message_code=VAL-INVALID-FILTER-KEY`, malformed JSON thì không). Bồi `message_code` vào `parse_json` = đổi envelope của **mọi** endpoint ⇒ cần CR riêng (backlog §14.10) |
| INV-FKEY-6 | `test_imm08` ≥ baseline **182 `def test`** · `test_imm09` ≥ baseline **230** (đọc lại trước khi sửa — chấm theo **delta**) |

### §14.7 Hợp đồng FE (AC6) — chi tiết ở [`06_Frontend_Design.md`](./06_Frontend_Design.md)

1. **Banner KHÔNG thay thế bảng.** Hiện tại `PMWorkOrderListView.vue:251` dùng `v-else-if="store.error"` ⇒
   khi lỗi, **toàn bộ bảng biến mất** (đúng cái AC6 cấm: "GIỮ dữ liệu đang xem, KHÔNG trắng trang"). Đổi thành
   banner **cộng thêm** phía trên bảng khi `store.workOrders.length > 0`; giữ khối lỗi chiếm-chỗ chỉ khi
   **chưa có dữ liệu nào**.
2. **Dùng message của BE** (`store.error` đã là `err.message` — `stores/imm08.ts:36-40`), KHÔNG chuỗi tự chế.
3. **KHÔNG logout** (đã đúng: 400 ≠ 401) · **0 lỗi console** · `store.workOrders` **không bị xoá** trong `catch`
   của `fetchWorkOrders` (đã đúng — `stores/imm08.ts:74-76` chỉ `_captureError`; **không được** thêm reset).
4. **Sửa nguồn gây lỗi**: `buildFilters()` `:72-73` đổi sang `due_date` + toán tử (§14.4).

### §14.8 Boundaries (Always / Never)

**Always** — whitelist là `frozenset` **module-level** ở `services/imm08.py`/`services/imm09.py` · cơ chế raise
dùng **1 helper CHUNG** `services/shared/filters.py::assert_allowed_filter_keys` · validate **trước**
`pop_search`/`_normalize_filters`/`_apply_open_drill` · message VI nêu khoá sai + tập hợp lệ · OAS liệt kê
**đúng** tập khoá + đọc-so bằng guard import THẲNG hằng số BE.

**Ask-first** — thêm/bớt khoá whitelist · mở whitelist cho `list_calibrations` (IMM-11, §14.10) · đổi
`error.code` khỏi `INVALID_PARAMS`.

**Never** — ❌ raise → HTTP-4xx (phải in-handler 200) · ❌ echo tên bảng/cột SQL vào message · ❌ chép tập khoá
lần thứ hai trong test/OAS/FE · ❌ thêm khoá "cho đủ" khi không có consumer · ❌ đổi ngữ nghĩa 4 khoá ảo ·
❌ đẻ khoá `due_date_from`/`due_date_to` ở BE · ❌ sửa `_VENDOR_SCOPE_FIELD_MAP` để test xanh · ❌ đụng
`services/imm11.py` trong vòng này.

### §14.9 Cải chính sổ mobile CR-70 (AC8)

CR-70 viết: *"key sai **không báo lỗi** — BE **bỏ qua im lặng** ⟹ client gửi `{"asset_ref": "..."}` sẽ nhận về
danh sách KHÔNG lọc"*. **SAI ở hai điểm, có bằng chứng:**

1. BE **KHÔNG bỏ qua im lặng** — BE **CRASH HTTP-500** (P1/P2 §14.1). Rủi ro thật **nặng hơn** CR-70 mô tả.
2. Ví dụ CR-70 chọn nhầm khoá: **`asset_ref` là khoá HỢP LỆ** và **được honor** trên cả 2 endpoint (P4 + §14.3).

CR-70 suy diễn từ `CommissioningFilters`/`imm04` (nơi khoá lạ **thật sự** bị bỏ qua vì imm04 lọc dict theo
whitelist **im lặng**) rồi khái quát sang imm08/imm09 — đó là **suy đoán**, không phải quan sát. Ghi trạng thái
**RESOLVED-BE** vào ledger [`docs/imm-09/05 §10.4`](../imm-09/05_API_Specification.md) + **đề nghị sync** sang
repo mobile. **KHÔNG tự sửa** `/home/miyano/assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` (repo KHÁC — cần
user cho phép).

### §14.10 Phát hiện phụ — KHÔNG sửa trong vòng này (backlog có bằng chứng)

- **[P1 — ba+be] `imm11.list_calibrations` cùng lớp lỗi** (P5 §14.1): khoá lạ → 500 lộ `tabIMM Asset Calibration`.
  Đóng bằng CR riêng (`_ALLOWED_FILTER_KEYS` cho IMM-11 + param OAS riêng). Cho tới lúc đó, param OAS dùng chung
  `WorkOrderFilters` **phải ghi rõ** IMM-11 chưa whitelist (§14.11).
- **[P2 — ba] Đổi tên `WorkOrderFilters` → `CalibrationFilters`** sau khi IMM-11 có whitelist riêng (lúc đó
  component này chỉ còn 1 consumer duy nhất là `listCalibrations`).
- **[P2 — be] Giá trị ngày sai định dạng** (vd `{"due_date": ["between", ["hôm qua", "x"]]}`) vẫn có thể làm
  `frappe.get_list` nổ — whitelist chỉ chặn **khoá**, chưa chặn **giá trị**. Cần CR "validate value-shape".

- **[P2 — be] `parse_json` thiếu `message_code`** (`utils/api_handler.py:104-113`): malformed JSON trả
  `ServiceError` **legacy** ⇒ envelope không có `message_code`/`title`/`action_hint`/`severity`. Bồi
  `MSG.VAL_INVALID_PARAMS` vào đó sẽ làm **mọi** endpoint dùng `parse_json` bắt đầu phát thêm 4 khoá envelope
  (additive nhưng blast-radius toàn app — Hyrum) ⇒ **CR riêng**, KHÔNG làm ké vòng AC-CR-79.
- **[Ghi nhận — cite-drift toàn cục] Vòng này phải remap 332 cite `services/imm08|imm09.py:<dòng>` trong OAS**
  vì 2 file service dịch **+32 dòng** mỗi file. 4 guard cite-parity (`cr73a_e`, `cr74_g`, `cr77_h`, `cr78_e`)
  bắt được 4/4 ca rot — **bằng chứng guard hoạt động**, nhưng cũng cho thấy cite **theo số dòng** rot mỗi lần
  chèn code. Đề xuất backlog: chuyển dần sang cite **theo symbol** (`@services/immXX.py::<symbol>`, đã có
  `_CR74_SYMBOL_CITE_RE`) cho những chỗ không cần chỉ đúng dòng.

### §14.11 OAS mirror — DELTA CHÍNH XÁC cho Bước-4 (AC7)

**Ràng buộc phát hiện được (verify 2026-07-27):** `WorkOrderFilters` (`:235-245`) đang được **$ref bởi 3 op**:
`listPmWorkOrders` (`:16991`), `listRepairWorkOrders` (`:17047`), **`listCalibrations`** (`:17103`). Ba op có
**tập khoá KHÁC nhau**; IMM-11 lại **chưa** whitelist ⇒ **không thể** viết "khoá ngoài danh sách ⇒ 400" vào
component dùng chung mà không nói dối cho `listCalibrations`.

**Quyết định: TÁCH component theo op** — đúng precedent `CommissioningFilters` (CR-25a: tập khoá khác ⇒ component
khác). Xem **ADR-IMM08-FILTERKEY-01**.

| # | Việc | Chi tiết |
|---|---|---|
| 1 | **+2 `components.parameters`** | `PmWorkOrderFilters` · `RepairWorkOrderFilters` (`name: filters`, `in: query`, `required: false`, `schema.type: string`, `schema.default: '{}'` — shape **y hệt** `WorkOrderFilters` để guard `:5463-5467` áp được) |
| 2 | **Đổi `$ref`** | `listPmWorkOrders` → `PmWorkOrderFilters` · `listRepairWorkOrders` → `RepairWorkOrderFilters` |
| 3 | **Giữ `WorkOrderFilters`** | chỉ còn `listCalibrations` $ref; **bồi 1 câu** vào `description`: `⚠️ IMM-11 CHƯA whitelist khoá — khoá lạ hiện làm truy vấn LỖI (AC-CR-79 §14.10 backlog).` |
| 4 | **Marker máy-đọc** trong `description` của 2 component mới (guard parse) | dòng `KHOÁ HỢP LỆ listPmWorkOrders (16): <a, b, …>.` và `KHOÁ HỢP LỆ listRepairWorkOrders (18): <…>.` — **sắp xếp `sorted()`**, phân tách `, `, kết thúc bằng `.` (khoá không chứa dấu `.` ⇒ regex `\(\d+\): ([^.]+)\.` an toàn) |
| 5 | **Câu hành vi** (bắt buộc, AC7) | `Khoá ngoài danh sách ⇒ 400 IN-ENVELOPE (HTTP-200, success:false, error.code=INVALID_PARAMS, message_code=VAL-INVALID-FILTER-KEY) — KHÔNG HTTP-500.` |
| 6 | **Cite** | đặt **trong `description`** (KHÔNG comment YAML — bài học CR-76): `services/imm08.py:<dòng THẬT> _ALLOWED_FILTER_KEYS` / `services/imm09.py:<dòng THẬT> _ALLOWED_FILTER_KEYS` |
| 7 | **Bỏ mô tả 1-ví-dụ** | câu cũ *"Bộ lọc dạng JSON-string (vd '{"status":"Open"}')"* giữ được, nhưng **phải kèm** tập khoá + toán tử (§14.4) |
| 8 | **Guard `$ref`-set** | `test_mobile_oas.py::_LIST_PARAM_EXPECT[_LIST_PM_PATH]` / `[_LIST_REPAIR_PATH]` (`:3007-3008`) đổi sang ref mới; `_LIST_CALIBRATION_PARAM_REFS` (`:5752`) **GIỮ NGUYÊN** |

**Bất biến OAS (đếm THẬT trên đĩa 2026-07-27):** `paths` **GIỮ 107** · `components.schemas` **GIỮ 281** ·
`components.parameters` **36 → 38** · 0 opId mới. Cả 2 component mới **được $ref ngay** ⇒ no-orphan.

### §14.12 Counters (AC7) — ⚠️ ĐỌC LẠI TRÊN ĐĨA TRƯỚC KHI SỬA, chấm theo **delta**

Base **đã đọc 2026-07-27** (khác con số trong đề mục vì AC-CR-78 đã land giữa spec↔exec — blocker #12):

| # | Chỗ | Base ĐỌC ĐƯỢC | Sau (delta **+8**) |
|---|---|---|---|
| 1 | `test_mobile_oas.py:212 _EXPECTED_TEST_COUNT` | **959** | **967** |
| 2 | `test_mobile_docset.py:781 _GUARD_SUITE_EXPECTED['test_mobile_oas.py']` | **959** | **967** |
| 3 | `test_mobile_docset.py:949 _GUARD_SUITE_SUM` | **1102** | **1110** |
| 4 | `test_mobile_docset.py:1138 _MOBILE_OAS_TOTAL` | **1128** | **1136** |
| 5 | 2 echo `assertEqual(_EXPECTED_TEST_COUNT, …)` trong `test_mobile_oas.py` | 959 | 967 |
| 6 | delta-name mới ở `test_mobile_docset.py` | — | `cr79_filter_key_whitelist_delta = 8` |

`components.schemas` pinned (`_CR74_SCHEMA_COUNT`, `cr77_e`, `cr78_*`) = **281 GIỮ NGUYÊN** (param ≠ schema).
Nếu tồn tại guard pin **số `components.parameters`** → bump **+2** (đọc lại trước khi sửa).

### §14.13 ⚠️ Slice contract KHÔNG đóng ở Bước-2 (BA→BE handoff) — mirror §13.10 / imm-09 §13.10

Cite-parity đòi symbol **đã tồn tại ở dòng thật**; guard AC2 lại **import THẲNG** `_ALLOWED_FILTER_KEYS` từ
service. Cả hai **chưa có trên đĩa** ⇒ dán OAS + guard ngay bây giờ = **ĐỎ tức thì**. Trình tự **BẮT BUỘC**:

1. **[BE]** `utils/messages.py`: `MSG.VAL_INVALID_FILTER_KEY = "VAL-INVALID-FILTER-KEY"` + entry registry
   (`04 §4.4`) → chạy `python3 scripts/gen_fe_messages.py` (sinh `frontend/src/i18n/messages.ts`) rồi
   `--check` phải OK.
2. **[BE]** `services/shared/filters.py::assert_allowed_filter_keys` + `services/imm08.py`/`services/imm09.py`
   `_ALLOWED_FILTER_KEYS` + 1 dòng cắm ở `list_work_orders` (`04 §4.4` / imm-09 `04 §3.9`).
3. **[BE]** TC hành vi `test_imm08.py::TestPmFilterKeyWhitelist` · `test_imm09.py::TestCmFilterKeyWhitelist`
   (`07 §X`) — **RED-before** bằng TC khoá-lạ (hiện `OperationalError`).
4. **[BE] CÙNG VÒNG (atomic)** OAS §14.11 (cite = **dòng THẬT sau khi land**) + `test_mobile_oas.py::TestMobileWorkOrderFilterKeysContract`
   (`cr79_a..h`, 8 TC) + 6 counter §14.12.
5. **[FE] CÙNG VÒNG** `06 §FilterKeyError` — banner không-thay-bảng + sửa `buildFilters()` + test RENDER.
6. **DoD:** `bench --site miyano run-tests --module assetcore.tests.test_imm08` · `...test_imm09` ·
   `...test_mobile_oas` · `...test_mobile_docset` (**timeout tool ≥600000ms**, module-isolated) +
   `vue-tsc --noEmit` 0 lỗi + `vitest run`. **KHÔNG curl** (BLOCKED-RELOAD gunicorn `--preload`),
   **KHÔNG `bench migrate`**, **KHÔNG `npm run build`**.

### ADR-IMM08-FILTERKEY-01: Tách `PmWorkOrderFilters`/`RepairWorkOrderFilters` khỏi `WorkOrderFilters` dùng chung

- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: 1 component `WorkOrderFilters` đang phục vụ **3 op** với **3 tập khoá khác nhau**; `listCalibrations`
  (IMM-11) **chưa** whitelist và vẫn 500 khi gặp khoá lạ (P5 §14.1).
- **Decision**: tách 2 component mới cho PM/CM; `WorkOrderFilters` ở lại phục vụ `listCalibrations` kèm cảnh báo
  "chưa whitelist".
- **Alternatives**: (a) giữ 1 component, liệt kê 3 tập → mô tả tự mâu thuẫn, codegen sinh 1 doc-string mô tả 3
  hành vi ⇒ loại; (b) whitelist luôn IMM-11 trong vòng này → vượt phạm vi đề mục + IMM-11 còn blocker vendor-alias
  (`scope.py:117` trỏ DocType không tồn tại) ⇒ loại, đưa vào §14.10.
- **Consequences**: `components.parameters` +2; `_LIST_PARAM_EXPECT` phải cập nhật 2 dòng; đổi lại **mỗi op nói
  đúng sự thật của chính nó**. Precedent đã có: `CommissioningFilters` (CR-25a).

### ADR-IMM08-FILTERKEY-02: `error.code` **tái dùng** `INVALID_PARAMS`, phân biệt bằng `message_code`

- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: đề mục đề xuất `error.code = INVALID_FILTER_KEY`. `ErrorCode` là **enum đóng, khớp FE**
  (`utils/response.py:37-57` ↔ `frontend/src/api/errors.ts`) và là **bucket điều hướng** của client.
- **Decision**: dùng bucket **`INVALID_PARAMS`** (đã có, đã map 400); danh tính riêng nằm ở
  **`message_code = VAL-INVALID-FILTER-KEY`** + `context.invalid_keys`/`allowed_keys`.
- **Alternatives**: thêm bucket `INVALID_FILTER_KEY` → buộc sửa enum FE + mọi switch phân nhánh, trong khi client
  **xử lý y hệt** `INVALID_PARAMS` (sửa tham số rồi gọi lại) ⇒ chi phí Hyrum cao, giá trị 0.
- **Consequences**: **cùng một tham số `filters`** hỏng theo 2 cách (malformed JSON / khoá lạ) trả **cùng bucket** ⇒
  client route 1 lần; telemetry vẫn tách được nhờ `message_code`. Đổi lại: ai chỉ nhìn `error.code` sẽ không phân
  biệt được — **có chủ đích**.

### ADR-IMM08-FILTERKEY-03: Khoảng ngày dùng **toán tử trên `due_date`**, KHÔNG thêm khoá ảo `due_date_from/to`

- **Status**: Accepted — **Date**: 2026-07-27
- **Context**: web FE đang gửi `due_date_from`/`due_date_to` — **hai khoá chưa từng tồn tại ở BE** ⇒ 500 THẬT (P3).
  Whitelist buộc phải quyết: hợp thức hoá 2 khoá ảo mới, hay sửa FE?
- **Decision**: **sửa FE**. `_OP_TOKENS` (`services/imm08.py:447`) **đã** cho lọt `["between", [a,b]]` /
  `[">=", a]` / `["<=", b]` trên `due_date` — khoá đã whitelist, 0 dòng BE mới.
- **Alternatives**: thêm 2 khoá ảo + logic gộp `due_before`/`overdue`/`from`/`to` → **4 nguồn cùng ghi `due_date`**,
  luật ưu tiên phải bịa thêm, và mobile phải học 1 phương ngữ riêng của AssetCore ⇒ loại.
- **Consequences**: nếu FE **không** land cùng vòng, bộ lọc khoảng ngày PM đi từ **500 câm** → **400 có banner**
  (vẫn là cải thiện, và **lộ ra ngay** thay vì im lặng). DoD §14.13 bước 5 là bắt buộc.

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
