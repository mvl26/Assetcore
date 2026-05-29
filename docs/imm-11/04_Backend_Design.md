# 04 — Thiết kế Backend (Backend Design)

| Mục | Giá trị |
|---|---|
| Module | IMM-11 — Hiệu chuẩn (Calibration) |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | 02 Analysis & Design · 03 Diagrams · 05 API |
| Cập nhật | 2026-05-14 |
| Trạng thái | ✅ Live — `services/imm11.py` và `api/imm11.py` đã implement |

---

## 1. Tổng quan kiến trúc

IMM-11 bám kiến trúc 3-tier strict của AssetCore:

```
FE Vue 3
    │ REST @frappe.whitelist
    ▼
api/imm11.py          ← thin wrapper: parse → service → _ok/_err
    │
    ▼
services/imm11.py     ← business logic: BR-11-xx, tolerance compute
    │          │
    ▼          ▼
IMM-11        services/imm00.py   ← KHÔNG reimplement: transition_asset_status,
DocTypes      (LIVE)                  create_capa, log_audit_event, etc.
```

**Quy ước ngôn ngữ BE:**
- Code (function, class, variable): tiếng Anh snake_case
- DocType `fieldname`: tiếng Anh (`asset`, `calibration_type`, `overall_result`)
- DocType field `label`: tiếng Việt (`Thiết bị`, `Loại hiệu chuẩn`, `Kết quả tổng`)
- Enum value: tiếng Anh (`External`, `In-House`, `Passed`, `Failed`)
- Error message: tiếng Việt (user-facing)

---

## 2. Domain Model — DocType

### 2.1 IMM Calibration Schedule ✅ DocType: `imm_calibration_schedule`

- **Naming:** `CAL-SCH-.YYYY.-.#####`
- **Type:** Non-submittable

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `asset` | Link AC Asset | ✓ | — | must be Active |
| `device_model` | Link IMM Device Model | ✓ | auto-fetch | — |
| `calibration_type` | Select | ✓ | External | External, In-House |
| `interval_days` | Int | ✓ | từ Device Model | > 0 |
| `last_calibration_date` | Date | ✗ | auto | Set on pass |
| `next_due_date` | Date | ✓ | computed | last + interval |
| `preferred_lab` | Link AC Supplier | ✗ | — | iso_17025_certified=1 |
| `is_active` | Check | ✓ | 1 | — |

**Indexes:** `(asset, is_active)`, `(next_due_date, is_active)`

### 2.2 IMM Asset Calibration ✅ DocType: `imm_asset_calibration`

Child table: **IMM Calibration Measurement** (`imm_calibration_measurement`) — linked via `measurements` child table field.

- **Naming:** `CAL-.YYYY.-.#####`
- **Type:** Submittable

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `asset` | Link AC Asset | ✓ | — | `validate_asset_for_operations` (trừ recal) |
| `calibration_type` | Select | ✓ | — | External, In-House |
| `status` | Select | ✓ | Scheduled | 8 states |
| `overall_result` | Select | ✗ | — | Computed `before_submit` |
| `lab_supplier` | Link AC Supplier | Conditional | — | External: iso_17025_certified=1 |
| `certificate_file` | Attach | Conditional | — | External Submit |
| `certificate_date` | Date | Conditional | — | ≤ today; External Pass |
| `lab_accreditation_number` | Data | Conditional | — | External Submit |
| `technician` | Link User | ✓ | — | — |
| `measurements` | Table | ✓ | — | ≥1 row |
| `is_recalibration` | Check | ✗ | 0 | — |
| `amendment_reason` | Small Text | Conditional | — | Amend |
| `capa_record` | Link IMM CAPA Record | ✗ | Auto | Set by service on Fail |

**Permission query (IMM Technician):**
```python
"`tabIMM Asset Calibration`.`technician` = '{user}' OR `tabIMM Asset Calibration`.`assigned_by` = '{user}'"
```

---

## 3. Workflow

**File:** `assetcore/assetcore/workflow/imm_11_calibration_workflow.json` (document_type = `IMM Asset Calibration`, workflow_state_field = `workflow_state`)

| State | Style | docstatus | allow_edit role |
|---|---|---|---|
| Scheduled | Primary | 0 | Workshop Lead, Technician |
| Sent to Lab | Warning | 0 | Technician |
| In Progress | Warning | 0 | Technician |
| Certificate Received | Primary | 0 | Technician |
| Passed | Success | 1 | — |
| Failed | Danger | 1 | — |
| Conditionally Passed | Warning | 1 | — |
| Cancelled | Danger | 2 | — |

Actual transitions (from `imm_11_calibration_workflow.json`):

| From | To | Action label (tiếng Việt) | Allowed role | Condition |
|---|---|---|---|---|
| Scheduled | In Progress | Bắt đầu hiệu chuẩn | Technician | calibration_type=In-House |
| Scheduled | Sent to Lab | Gửi phòng hiệu chuẩn | Technician | calibration_type=External |
| Scheduled | Cancelled | Hủy lịch | Workshop Lead | docstatus=0 |
| In Progress | Passed | Đạt hiệu chuẩn | Technician | overall_result=Passed |
| In Progress | Failed | Không đạt hiệu chuẩn | Technician | overall_result=Failed |
| In Progress | Conditionally Passed | Đạt có điều kiện | Technician | overall_result=Conditionally Passed |
| In Progress | Cancelled | Hủy hiệu chuẩn | Technician | — |
| Sent to Lab | Certificate Received | Nhận chứng chỉ | Technician | — |
| Certificate Received | Passed | Phê duyệt đạt | Workshop Lead / QA | — |
| Certificate Received | Failed | Phê duyệt không đạt | Workshop Lead / QA | — |
| Certificate Received | Conditionally Passed | Phê duyệt có điều kiện | Workshop Lead / QA | — |
| Failed | Conditionally Passed | CAPA hoàn tất - chuyển có điều kiện | QA Officer | CAPA Closed + recal Pass |

**Controller hooks (delegate-only):**

```python
# assetcore/assetcore/doctype/imm_asset_calibration/imm_asset_calibration.py  ✅ EXISTS
# Controller delegates on_submit → service layer handles Pass/Fail branching
# Pass path: services.imm11.handle_calibration_pass(cal_doc)
# Fail path: services.imm11.handle_calibration_fail(cal_doc)
```

---

## 4. Service Layer

**File:** `assetcore/services/imm11.py` ✅ LIVE

### Public functions (implemented)

| Function | Input | Output | Side effect |
|---|---|---|---|
| `create_calibration_schedule_from_commissioning(doc)` | Commissioning doc | `str` (sched_name) or None | Insert `IMM Calibration Schedule` + `log_audit_event` |
| `create_post_repair_calibration(asset_name)` | str | `str` or None | Insert `IMM Asset Calibration` (`is_recalibration=1`) |
| `create_due_calibration_wos()` | — | `int` (count created) | Scheduler: Insert draft `IMM Asset Calibration` per due Schedule (threshold 30 days) |
| `check_calibration_expiry()` | — | None | Scheduler: Update `AC Asset.calibration_status` (Overdue/DueSoon/OnSchedule). **Vòng 3:** sau khi đổi status, gọi `notifications.notify_calibration_due(asset, old_status, new_status)` (E4) — báo `responsible_technician`/`custodian` khi asset CHUYỂN VÀO DUE_SOON/OVERDUE. Spec: `docs/imm-00/04_Backend_Design.md §III.1b-2`. |
| `handle_calibration_pass(cal_doc)` | `IMM Asset Calibration` doc | None | Update Asset dates + `CalibrationSchedule.next_due_date` + lifecycle event + transition back to Active |
| `handle_calibration_fail(cal_doc)` | `IMM Asset Calibration` doc | None | OOS transition + `create_capa()` (severity Major) + lookback + auto-report IMM-12 incident |
| `perform_lookback_assessment(device_model, exclude_asset)` | str, str | `list[str]` | Read-only: assets same device_model in Active status |
| `list_schedules(filters, page, page_size)` | dict, int, int | `{data, pagination}` | None |
| `get_schedule(name)` | str | dict | None |
| `create_schedule(asset, calibration_type, interval_days, ...)` | kwargs | `{name, next_due_date}` | Insert `IMM Calibration Schedule` |
| `update_schedule(name, patch)` | str, dict | `{name}` | Patch allowed fields only |
| `delete_schedule(name)` | str | `{name, deleted}` | Blocked if submitted calibrations exist |
| `list_calibrations(filters, page, page_size)` | dict, int, int | `{data, pagination}` | None |
| `get_calibration(name)` | str | dict | None |
| `create_calibration(asset, calibration_type, scheduled_date, technician, ...)` | kwargs | `{name, status}` | Insert `IMM Asset Calibration` |
| `update_calibration(name, patch)` | str, dict | `{name, status}` | Asset → Calibrating when status in (In Progress, Sent To Lab) |
| `submit_calibration(name)` | str | `{name, status, overall_result, next_calibration_date}` | Triggers controller on_submit → Pass/Fail handlers |
| `add_measurement(name, parameter_name, unit, ...)` | str, kwargs | `{name, measurement_count}` | Append to `measurements` child table |
| `send_to_lab(name, sent_date, lab_supplier, lab_contract_ref)` | str, kwargs | `{name, status, sent_date}` | Status → Sent To Lab + Asset → Calibrating |
| `receive_certificate(name, certificate_file, certificate_number, ...)` | str, kwargs | `{name, status, certificate_number}` | Status → In Progress |
| `cancel_calibration(name, reason)` | str, str | `{name, status}` | Status → Cancelled + Asset → Active if was Calibrating |
| `get_due_calibrations(days, limit)` | int, int | `{items, threshold_days}` | None |
| `get_asset_history(asset, limit)` | str, int | `{asset, history}` | None |
| `get_kpis(year, month)` | int, int | `{kpis: {...}}` | None |
| `get_dashboard()` | — | `{kpis, overdue_assets, due_soon_assets, capa_open_list, period}` | None |

### Key implementation notes

- Service uses `ServiceError(ErrorCode.X, "msg tiếng Việt")` — raised to API layer, caught by `_handle()`.
- `_UPDATE_ALLOWED` whitelist controls patchable fields in `update_calibration()`.
- `_CALIBRATING_TRIGGER_STATUSES = {In Progress, Sent To Lab}` — transitions Asset → Calibrating when status enters these.
- `CalibrationResult` constants (from `services.shared`): SCHEDULED, IN_PROGRESS, SENT_TO_LAB, PASSED, FAILED, COND_PASSED, CANCELLED plus ACTIVE_STATUSES set.
- `CalibrationStatus` constants: ON_SCHEDULE, DUE_SOON, OVERDUE, FAILED — written to `AC Asset.calibration_status`.
- IMM-12 cross-module: `handle_calibration_fail` auto-calls `imm12.report_incident(...)` with fault_code=`"CAL_FAIL"` (wrapped in try/except, non-blocking).

---

## 4b. Repository Layer

**Files:** `assetcore/repositories/calibration_repo.py` (CalibrationRepo, CalibrationScheduleRepo) ✅ LIVE

Repos live in `assetcore/repositories/` (not inline in services/imm11.py). Service imports:
```python
from assetcore.repositories.calibration_repo import CalibrationRepo, CalibrationScheduleRepo
from assetcore.repositories.asset_repo import AssetRepo, DeviceModelRepo, CapaRepo
```

Key repo methods used by service: `get`, `create`, `list`, `set_values`, `update_fields`, `submit`, `save`, `delete`, `exists`, `count`, `find_one`.

Idempotency guard in `create_due_calibration_wos`: checks `CalibrationRepo.exists({calibration_schedule: s.name, status: ("in", ACTIVE_STATUSES)})` before inserting.

---

## 5. API Layer

**File:** `assetcore/api/imm11.py` ✅ LIVE — imports from `assetcore.utils.helpers` (`_ok`, `_err`)

**Actual @frappe.whitelist functions (see 05_API_Specification.md for full specs):**

| Function | Method | Description |
|---|---|---|
| `list_calibration_schedules(filters, page, page_size)` | GET | List schedules with pagination |
| `get_calibration_schedule(name)` | GET | Single schedule |
| `create_calibration_schedule(asset, calibration_type, interval_days, preferred_lab, next_due_date)` | POST | Create schedule |
| `update_calibration_schedule(name, **kwargs)` | POST | Update schedule fields |
| `delete_calibration_schedule(name)` | POST | Delete (if no submitted cals) |
| `list_calibrations(filters, page, page_size)` | GET | List calibrations with pagination |
| `get_calibration(name)` | GET | Single calibration detail |
| `create_calibration(asset, calibration_type, scheduled_date, technician, ...)` | POST | Create calibration WO |
| `update_calibration(name, **kwargs)` | POST | Update allowed fields |
| `submit_calibration(name)` | POST | Submit (triggers Pass/Fail handler) |
| `add_measurement(name, parameter_name, unit, nominal_value, ...)` | POST | Add measurement row |
| `get_calibration_kpis(year, month)` | GET | Monthly KPI report |
| `get_calibration_dashboard()` | GET | Full dashboard (KPIs + lists) |
| `get_asset_calibration_history(asset, limit)` | GET | Asset calibration history |
| `send_to_lab(name, sent_date, lab_supplier, lab_contract_ref)` | POST | External: → Sent To Lab |
| `receive_certificate(name, certificate_file, certificate_number, certificate_date, ...)` | POST | External: → In Progress |
| `cancel_calibration(name, reason)` | POST | Cancel pre-submit |
| `get_due_calibrations(days, limit)` | GET | Assets due ≤ N days |

> **Pattern:** All responses via `_ok(data)` / `_err(msg, code)` from `assetcore.utils.helpers`. HTTP always 200. Service raise `ServiceError(ErrorCode.X, "msg tiếng Việt")` caught by `_handle()`.

---

## 6. Audit Trail

| Trigger | Entry type | Actor | Payload |
|---|---|---|---|
| Schedule tạo từ IMM-04 | `calibration_scheduled` | System | `{sched_name, asset, interval}` |
| Bàn giao lab | `calibration_sent_to_lab` | KTV | `{cal_name, lab_supplier, sent_date}` |
| Nhận chứng chỉ | `certificate_received` | KTV | `{cal_name, certificate_date, certificate_number}` |
| Submit Pass | `calibration_completed` | KTV | `{cal_name, overall_result, next_calibration_date}` |
| Submit Fail | `calibration_failed` | System | `{cal_name, capa_ref, lookback_count}` |
| CAPA Closed + recal | `calibration_conditionally_passed` | System | `{capa_ref, new_cal_name}` |

**Hash chain:** SHA-256(canonical JSON payload + `prev_hash`). Verify qua `imm00.verify_audit_chain()`.

---

## 7. Background jobs / Scheduler

| Job | Tần suất | Hook | Mục đích |
|---|---|---|---|
| `create_due_calibration_wos` | Daily 06:00 | `scheduler_events.daily` | Tạo draft CAL WO cho Schedule due ≤ 30 ngày |
| `check_calibration_expiry` | Daily 06:30 | `scheduler_events.daily` | Update calibration_status + email alerts 90/60/30/7/0 ngày |
| `check_capa_overdue` (IMM-00) | Daily 02:00 | IMM-00 | CAPA Open > due_date → Overdue + email QA |

**hooks.py registration (actual `assetcore/hooks.py`):**

```python
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            "assetcore.services.imm11.create_calibration_schedule_from_commissioning",
            "assetcore.services.imm16.eval_imm04_realtime",
        ],
    },
    "IMM Asset Calibration": {
        "on_submit": "assetcore.services.imm16.eval_imm11_realtime",
    },
    # Note: `create_post_repair_calibration` KHÔNG dùng doc_events.
    # IMM-09 service tự gọi nó qua Pattern B (direct service-to-service lazy import)
    # trong `services/imm09.py`.
}

scheduler_events = {
    "daily": [
        "assetcore.services.imm11.create_due_calibration_wos",   # threshold 30 days
        "assetcore.services.imm11.check_calibration_expiry",     # Overdue/DueSoon/OnSchedule
    ],
}
```

---

## 8. Integration

### Module nội bộ

| Module | Chiều | Trigger | Function |
|---|---|---|---|
| IMM-04 Installation | IN | `Asset Commissioning` doc_events.on_submit (hooks.py) | `create_calibration_schedule_from_commissioning()` |
| IMM-09 Repair | IN | `services/imm09.py` gọi trực tiếp (Pattern B lazy import, không qua hooks.py) | `create_post_repair_calibration(asset_name)` |
| IMM-00 Foundation | OUT | Mọi action nghiệp vụ | `transition_asset_status`, `create_capa`, `log_audit_event`, `create_lifecycle_event` |
| IMM-12 Incident | OUT | Cal Fail → auto-create Incident | `imm12.report_incident(fault_code="CAL_FAIL")` — non-blocking |
| IMM-16 Compliance | OUT | `IMM Asset Calibration.on_submit` (hooks.py doc_events) | `imm16.eval_imm11_realtime` — cập nhật compliance scorecard sau mỗi submit |

---

## 9. Migration & Patch

| Sprint | Patch | Path |
|---|---|---|
| 11.1 | Create IMM Calibration Schedule DocType | `assetcore/patches/v3/001_create_imm_calibration_schedule.py` |
| 11.1 | Create IMM Asset Calibration + Measurement DocType | `assetcore/patches/v3/002_create_imm_asset_calibration.py` |
| 11.1 | Custom fields on AC Asset (calibration_status, last/next_calibration_date) | `assetcore/patches/v3/003_add_calibration_fields_to_ac_asset.py` |
| 11.4 | Workflow JSON fixture | fixtures, không cần patch |
| 11.4 | Permission fixtures | `assetcore/fixtures/imm11_permissions.json` |

---

## 10. Non-functional

**Concurrency:** Frappe `modified` check (optimistic lock) — `TimestampMismatchError` → `ServiceError(CONFLICT, "Record đã được cập nhật bởi người dùng khác")`.

**Idempotency:** Scheduler `create_due_calibration_wos` kiểm tra `has_open_calibration()` trước khi insert — safe to retry.

**Caching:** Dashboard KPI cache TTL = 5 phút. Invalidate khi có IMM Asset Calibration Submit mới.

**Logging:** `frappe.logger("imm11")` với `request_id` + actor + `cal_name`.

---

## DoD — File 04 hoàn chỉnh

- [x] DocType nêu đầy đủ trường + naming + permissions sơ bộ
- [x] Quan hệ liên DocType rõ
- [x] Workflow states + transitions định nghĩa
- [x] Mọi mutation map về 1 service function (type hints)
- [x] Repository layer liệt kê method (`get`, `list`, `get_active_schedule`, `has_open_calibration`)
- [x] Mọi error raise qua `ServiceError(ErrorCode.X, msg tiếng Việt)`
- [x] API layer dùng `_handle / _ok / _err` envelope
- [x] Audit trail entry liệt kê đủ trigger
- [x] Background job đăng ký rõ
- [x] Integration nội bộ liệt kê
- [x] Patch path xác định
- [x] ✅ Implemented — `services/imm11.py` + `api/imm11.py` + DocType JSONs exist
- [ ] Reviewed bởi BE Lead + DBA
