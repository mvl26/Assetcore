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

> ⚠️ **Data-quality note (workflow JSON):** `imm_11_calibration_workflow.json` chứa **13 dòng `transitions[]`** nhưng chỉ **12 cạnh duy nhất (unique edges)** — cạnh `Failed → Conditionally Passed` bị **lặp 2 lần** (cùng `state`/`next_state`/`action` "CAPA hoàn tất - chuyển có điều kiện", index 11 + 12). Bảng §3 ở trên (12 dòng) là **đúng theo ngữ nghĩa** (12 cạnh unique). Đây là dòng thừa trong JSON nguồn — KHÔNG đổi semantics state-machine. Guard test (xem §3.1) so map BE với codomain JSON **theo SET (tự dedup)** ⇒ không lệch; assertion đếm thô giữ `len(transitions)==13` (count thật JSON), CÓ ghi chú "13 thô = 12 unique". *(Cần khảo sát: có nên dọn dòng lặp trong JSON ở round riêng — ngoài scope vòng này vì sẽ chạm migration/fixture; flag `[ROADMAP]`.)*

### 3.1 `_CAL_VALID_TRANSITIONS` — server-driven CTA map (allowed_transitions[])

**Mục đích:** `get_calibration(name)` emit thêm key `allowed_transitions: list[str]` để client (mobile `getCalibration`) render nút workflow màn calibration-detail **theo SERVER**, KHÔNG hardcode `status → button` ở client (anti-pattern dead-gate / RBAC-drift). Đây là thành viên **THỨ TƯ và CUỐI** của họ `allowed_transitions[]` — sau `IncidentDetail` (imm12.py:778, R3) + `PmWorkOrderDetail` (imm08.py:651, R21) + `RepairWorkOrderDetail` (imm09.py:773, R22) — **ĐÓNG KÍN ASYMMETRY R3**: cả 4 `*Detail` đều emit `allowed_transitions[]`.

**Map (keyed BẰNG `CalibrationResult.*` constants — KHÔNG string literal):**

```python
# assetcore/services/imm11.py  (mirror imm09.py:83 R22 / imm08.py:80 R21)
# Keyed BẰNG CalibrationResult.* (services/shared/constants.py:112) — KHÔNG literal.
# Codomain GROUNDED edge-by-edge imm_11_calibration_workflow.json transitions[]
# (8 state / 13 transition thô = 12 unique edge). Terminal Passed/Conditionally
# Passed/Cancelled → [] (0 outgoing). Guard test chốt SSoT-divergence (map↔workflow
# theo SET) + codomain ⊆ CalibrationResult enum (chống typo/drift).
_CAL_VALID_TRANSITIONS: dict[str, list[str]] = {
    CalibrationResult.SCHEDULED: [
        CalibrationResult.IN_PROGRESS,
        CalibrationResult.SENT_TO_LAB,
        CalibrationResult.CANCELLED,
    ],
    CalibrationResult.IN_PROGRESS: [
        CalibrationResult.PASSED,
        CalibrationResult.FAILED,
        CalibrationResult.COND_PASSED,
        CalibrationResult.CANCELLED,
    ],
    CalibrationResult.SENT_TO_LAB: [CalibrationResult.CERT_RECEIVED],
    CalibrationResult.CERT_RECEIVED: [
        CalibrationResult.PASSED,
        CalibrationResult.FAILED,
        CalibrationResult.COND_PASSED,
    ],
    CalibrationResult.FAILED: [CalibrationResult.COND_PASSED],
    CalibrationResult.PASSED: [],          # terminal (docstatus=1)
    CalibrationResult.COND_PASSED: [],     # terminal (docstatus=1)
    CalibrationResult.CANCELLED: [],       # terminal (docstatus=2)
}
```

**Emit (mirror R21/R22):**

```python
# services/imm11.py:get_calibration — thêm 1 key vào dict return (KHÔNG đổi signature)
data["allowed_transitions"] = _CAL_VALID_TRANSITIONS.get(doc.status, [])
return data
```

**Boundaries:**
- **Always:** key `allowed_transitions` LUÔN emit (kể cả `[]` khi terminal); keyed bằng `CalibrationResult.*`; codomain ⊆ `CalibrationResult` enum; FE render CTA theo list này (KHÔNG suy diễn client-side).
- **Never:** ❌ đổi signature `get_calibration(name)` · ❌ đổi handler `api/imm11.py:81` (vendor IDOR guard `assert_vendor_can_access` + `handle(svc.get_calibration, name)` GIỮ nguyên — field mới chảy qua envelope tự động) · ❌ đưa `allowed_transitions` vào `required` của contract · ❌ string-literal key · ❌ enum-bound cứng `items` trong yaml (né drift).

#### ADR-IMM11-04: `allowed_transitions[]` server-driven CTA cho getCalibration

- **Status:** Accepted — 2026-06-16 (đóng kín ASYMMETRY R3; mirror ADR R3/R21/R22 của Incident/PM/Repair)
- **Context:** Mobile `getCalibration` detail cần biết "từ status hiện tại được phép chuyển sang state nào" để render nút workflow. 3 *Detail kia (Incident/PM/Repair) đã emit `allowed_transitions[]`; CalibrationDetail là *Detail DUY NHẤT còn THIẾU ⇒ ASYMMETRY. Client KHÔNG được hardcode `status→button` (dead-gate: workflow đổi → FE lệch âm thầm).
- **Decision:** Thêm map module-level `_CAL_VALID_TRANSITIONS` (dict keyed `CalibrationResult.*`) + emit `data["allowed_transitions"]` trong `get_calibration` (chỉ thêm 1 key vào dict return). KHÔNG đổi signature/handler. Contract `CalibrationDetail` thêm property `allowed_transitions: array<string>`, NOT-required, `additionalProperties:true` GIỮ.
- **Alternatives:** (a) FE hardcode `status→button` — LOẠI: dead-gate, drift khi workflow đổi. (b) Endpoint riêng `getCalibrationTransitions` — LOẠI: thừa round-trip; allowed_transitions là thuộc tính của chính doc-detail (mirror 3 *Detail kia). (c) enum-bound cứng `items.enum` trong yaml — LOẠI: drift khi workflow thêm state; codomain-check để ở guard test phía service (`test_imm11`).
- **Consequences:** (+) 4/4 *Detail đối xứng, FE render CTA thống nhất 1 pattern. (+) Guard test SSoT-divergence (map↔workflow JSON theo SET) bắt drift sớm. (−) Workflow JSON có 1 cạnh lặp (`Failed→Conditionally Passed` ×2) ⇒ guard so theo SET (tự dedup), count thô giữ 13 — phải ghi chú rõ (xem note §3). (−) Live HTTP cần reload gunicorn (`--preload`) để key mới hiện — guard in-process KHÔNG cần (HARD-STOP user).

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
| `check_calibration_expiry()` | — | None | Scheduler: **rollup cache + FULL-SET reconcile** `AC Asset.calibration_status` TỪ SoT schedule (`§4.1.3`). Phạm vi = UNION(asset có active schedule, asset có `calibration_status != ''`). **BR-11-10** stale-clear: hết active schedule → reset `Not Required`. **BR-11-11** preserve terminal `Calibration Failed` khi `lifecycle_status = Out of Service`. Idempotent (chạy 2× = nhau). `notifications.notify_calibration_due(asset, old, new)` (E4) chỉ khi status đổi (anti-spam). Spec: `docs/imm-00/04_Backend_Design.md §III.1b-2`. |
| `_reconcile_calibration_status(asset, old, derived)` | str, str, str? | `str` | None — pure decision per-asset (`§4.1.3`): FAILED-preserve / SoT derived / stale→NOT_REQUIRED |
| `_nonempty_cache_asset_ids()` | — | `set[str]` | None — asset có `calibration_status != ''` (để reconcile thăm CẢ asset hết active schedule, BR-11-10) |
| `is_calibration_overdue(next_due, ref_date)` | date, date? | `bool` | None — pure SoT predicate (`§4.1.1`), `next_due < today` strict |
| `is_calibration_due_soon(next_due, ref_date)` | date, date? | `bool` | None — pure SoT predicate, `today <= next_due <= today+30` inclusive |
| `_overdue_asset_ids(ref_date)` / `_due_soon_asset_ids(ref_date)` | date? | `set[str]` | None — SoT tập asset de-dup (`§4.1.2`), JOIN schedule active + asset không decommissioned |
| `handle_calibration_pass(cal_doc)` | `IMM Asset Calibration` doc | None | Advance `CalibrationSchedule.next_due_date = basis+interval` (BR-11-04) + **ghi ASSET-cache `{calibration_status, next_calibration_date, last_calibration_date}` theo ROLLUP đa-lịch qua `_apply_asset_calibration_rollup()` (BR-11-13, §4.1.7) — KHÔNG hardcode ON_SCHEDULE 1-lịch** + ghi ALE `calibration_passed`; restore CÓ ĐIỀU KIỆN: `Calibrating → Active` luôn; `Out of Service → Active` CHỈ qua `_can_restore_from_oos()` (BR-11-12, §4.1.5). KHÔNG raise ở nhánh restore. |
| `_apply_asset_calibration_rollup(asset, basis)` | str, str | None | Ghi ASSET-cache 3 field theo rollup worst-of-all + `MIN(next_due_date)` (BR-11-13, §4.1.7). Dùng CÙNG SoT `_calibration_status_asset_ids` → ROLLUP-CONSISTENCY với `check_calibration_expiry`. Bounded query (no N+1). |
| `_asset_min_next_due(asset)` | str | `str?` | `MIN(next_due_date)` trên MỌI active schedule của asset (1 aggregate query). None nếu hết active schedule. §4.1.7. |
| `_can_restore_from_oos(asset, cal)` | str, `IMM Asset Calibration` doc | `bool` | None — pure predicate (BR-11-12, §4.1.5): True ⟺ chủ-hold OoS == `IMM Asset Calibration` (ALE mới nhất vào OoS) ∧ 0 hold khác mở (Incident IMM-12 / Repair WO IMM-09 / PM WO OoS-finding IMM-08). MỌI nhánh ép Active-từ-OoS đi qua đây (grep-guard SoT). |
| `_latest_oos_root_doctype(asset)` | str | `str?` | None — đọc ALE mới nhất `to_status='Out of Service'` của asset → trả `root_doctype` (chủ-hold). None nếu không có. |
| `_oos_hold_note(asset, source_label)` | str, str | `str` | None — dựng note VI `giữ Ngừng hoạt động do hạng mục khác (<nguồn>)` cho ALE giữ-OoS. |
| `handle_calibration_fail(cal_doc)` | `IMM Asset Calibration` doc | None | OOS transition + `create_capa()` (severity Major) + lookback + auto-report IMM-12 incident + **hạ MỌI active `Schedule.next_due_date` về basis-date (due-now, BR-11-08b §4.1.6)** — asset rơi vào overdue/due-soon SoT, hết mask ON_SCHEDULE; null-safe (0 schedule → no-op) |
| `perform_lookback_assessment(device_model, exclude_asset)` | str, str | `list[str]` | Read-only: assets same device_model in Active status |
| `list_schedules(filters, page, page_size)` | dict, int, int | `{data, pagination}` | None |
| `get_schedule(name)` | str | dict | None |
| `create_schedule(asset, calibration_type, interval_days, ...)` | kwargs | `{name, next_due_date}` | Insert `IMM Calibration Schedule` |
| `update_schedule(name, patch)` | str, dict | `{name}` | Patch allowed fields only |
| `delete_schedule(name)` | str | `{name, deleted}` | Blocked if submitted calibrations exist |
| `list_calibrations(filters, page, page_size)` | dict, int, int | `{data, pagination}` | None |
| `get_calibration(name)` | str | dict | + key `allowed_transitions: list[str]` = `_CAL_VALID_TRANSITIONS.get(doc.status, [])` (server-driven CTA, §3.1). KHÔNG đổi signature `get_calibration(name)`; KHÔNG đổi handler `api/imm11.py:81`. |
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
- `CalibrationStatus` constants: ON_SCHEDULE (`"On Schedule"`), DUE_SOON (`"Due Soon"`), OVERDUE (`"Overdue"`), FAILED (`"Calibration Failed"`, terminal), NOT_REQUIRED (`"Not Required"`, neutral/stale-clear) — written to `AC Asset.calibration_status`. FE phải map ĐỦ 5 giá trị literal này sang nhãn VI (06_Frontend_Design §badge) — KHÔNG để rò EN.
- IMM-12 cross-module: `handle_calibration_fail` auto-calls `imm12.report_incident(...)` with fault_code=`"CAL_FAIL"` (wrapped in try/except, non-blocking).

---

## 4.1 SoT predicate — "calibration due / overdue" (BR-11-08 / BR-11-09)

> **Self-Correction.** Trước fix có **2 nguồn ngày phân kỳ**: dashboard đếm `IMM Calibration Schedule.next_due_date` (không lọc `is_active`/decommissioned → đếm dư), còn IMM-11 KPI/drill đếm `AC Asset.calibration_status` derive từ `AC Asset.next_calibration_date` (field KHÁC, NULL với asset minted → KPI=0). Hợp nhất về **1 predicate + 1 date-field + 1 tập filter**.

### 4.1.1 Hằng + predicate thuần (pure, không I/O)

```python
# services/imm11.py — module-level constants
CAL_DUE_SOON_WINDOW_DAYS = 30      # 1 hằng dùng chung MỌI nơi (KHÔNG hardcode "30" rải rác)
_CAL_AUTH_DATE_FIELD = "next_due_date"   # authoritative date = Schedule.next_due_date

def is_calibration_overdue(next_due, ref_date=None) -> bool:
    """OVERDUE ⟺ next_due < today (strict <). None → False (không có hạn = không quá hạn)."""
    if not next_due:
        return False
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    return getdate(next_due) < ref

def is_calibration_due_soon(next_due, ref_date=None) -> bool:
    """DUE_SOON ⟺ today <= next_due <= today + CAL_DUE_SOON_WINDOW_DAYS (cả 2 biên inclusive).
    Loại trừ overdue (overdue ưu tiên). None → False."""
    if not next_due:
        return False
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    nd = getdate(next_due)
    return ref <= nd <= add_days(ref, CAL_DUE_SOON_WINDOW_DAYS)
```

Boundary chốt: `next_due == today` → **DUE_SOON** (KHÔNG overdue); `next_due == today+30` → **DUE_SOON** (inclusive); `next_due == today+31` → ON_SCHEDULE; `next_due == today-1` → OVERDUE.

### 4.1.2 Tập filter SoT (dùng chung dashboard + IMM-11)

Mọi consumer đếm/list theo cùng JOIN + filter:

```python
# Schedule active + asset KHÔNG decommissioned. De-dup theo asset (BR-11-09).
_NOT_DECOMMISSIONED = ("not in", [AssetStatus.DECOMMISSIONED])

def _overdue_asset_ids(ref_date=None) -> set[str]:
    """SoT: tập DISTINCT asset có >=1 active schedule overdue, asset không decommissioned."""
    ref = ref_date or nowdate()
    rows = frappe.db.sql("""
        SELECT DISTINCT s.asset
        FROM `tabIMM Calibration Schedule` s
        JOIN `tabAC Asset` a ON a.name = s.asset
        WHERE s.is_active = 1
          AND s.next_due_date < %(ref)s
          AND a.lifecycle_status != %(decom)s
    """, {"ref": ref, "decom": AssetStatus.DECOMMISSIONED}, as_dict=True)
    return {r["asset"] for r in rows}

def _due_soon_asset_ids(ref_date=None) -> set[str]:
    """SoT: tập DISTINCT asset có >=1 active schedule due trong [today, today+30],
    LOẠI những asset đã overdue (overdue ưu tiên — không double-tally)."""
    ref = ref_date or nowdate()
    window_end = add_days(ref, CAL_DUE_SOON_WINDOW_DAYS)
    rows = frappe.db.sql("""
        SELECT DISTINCT s.asset
        FROM `tabIMM Calibration Schedule` s
        JOIN `tabAC Asset` a ON a.name = s.asset
        WHERE s.is_active = 1
          AND s.next_due_date >= %(ref)s AND s.next_due_date <= %(end)s
          AND a.lifecycle_status != %(decom)s
    """, {"ref": ref, "end": window_end, "decom": AssetStatus.DECOMMISSIONED}, as_dict=True)
    return {r["asset"] for r in rows} - _overdue_asset_ids(ref_date)
```

- **De-dup (BR-11-09):** `SELECT DISTINCT s.asset` → 1 asset có nhiều active schedule overdue chỉ đếm **1 lần theo asset**. `len(_overdue_asset_ids())` == KPI card == số dòng drill (drill cũng group theo asset).
- **Count == drill:** `get_calibration_kpis().overdue_assets == len(_overdue_asset_ids())`; drill `/calibration/schedules?overdue=1` trả CÙNG tập asset (de-dup). Tương tự `due_soon_assets == len(_due_soon_asset_ids())`; drill `?due_soon=1` (cửa-sổ-2-biên `next_due BETWEEN [today, today+30]` + `asset IN _due_soon_asset_ids()`) tái lập CHÍNH XÁC tập KPI — KHÔNG cần post-filter `next_due >= today`. (Param `due_before=X` là cutoff-tùy-ý tập-BAO legacy, GỒM cả overdue — KHÔNG dùng cho card due-soon. `_normalize_schedule_filters` ưu tiên `overdue` > `due_soon` > `due_before`; cả 3 nhánh GIAO caller `asset IN` scope thay vì clobber → vendor-scope an toàn.)
- **Dashboard parity:** `dashboard.py` `calib_overdue = len(_overdue_asset_ids())` và `calib_due = len(_due_soon_asset_ids())` (import từ `services.imm11`) → tổng dashboard == module overdue/due_soon (cùng SoT, KHÔNG lệch).

### 4.1.3 `check_calibration_expiry` — rollup cache + FULL-SET reconcile (BR-11-10 / BR-11-11)

> **Self-Correction (vòng 33).** Bản cũ duyệt CHỈ `rollup.items()` = tập asset CÓ active schedule (`_calibration_status_asset_ids`). Hệ quả 2 lỗi:
> - **BUG-1 stale-never-cleared:** asset từng `Overdue`/`Due Soon`, sau đó lịch DUY NHẤT bị `is_active=0`/xóa → biến mất khỏi rollup map → vòng quét KHÔNG bao giờ thăm lại → cache giữ `Overdue` **vĩnh viễn** (badge ma).
> - **BUG-2 FAILED-clobber:** asset `handle_calibration_fail` set `calibration_status = Calibration Failed` (terminal, `lifecycle_status = Out of Service`, CAPA mở). Nếu lịch vẫn `is_active=1` và quá hạn, rollup map trả `Overdue` cho asset đó → ghi đè **mất terminal FAILED**.
>
> **Chốt:** phạm vi reconcile = **UNION** (asset có ≥1 active schedule) ∪ (asset có `calibration_status != ''`). Rollup iterate TOÀN tập → không cache row nào bị bỏ sót. Thêm 2 guard: **preserve terminal FAILED** + **stale-clear về neutral**.

```python
def check_calibration_expiry() -> None:
    """Scheduler daily — rollup cache AC Asset.calibration_status TỪ SoT schedule,
    reconcile FULL-SET (BR-11-10 stale-clear + BR-11-11 FAILED-preserve).

    Phạm vi = UNION(asset có >=1 active schedule, asset có calibration_status != '').
    Idempotent: chạy 2× cho kết quả như nhau; notify chỉ khi status THỰC SỰ đổi."""
    from assetcore.services import notifications      # lazy — tránh circular

    rollup = _calibration_status_asset_ids()           # map: asset -> derived status (CHỈ active-sched)
    cached = _nonempty_cache_asset_ids()               # set: asset có calibration_status != '' hiện tại
    for asset_name in (set(rollup) | cached):          # UNION — không bỏ sót cache row nào
        old = AssetRepo.get_value(asset_name, "calibration_status") or ""
        new = _reconcile_calibration_status(asset_name, old, rollup.get(asset_name))
        if new == old:
            continue                                   # idempotent — không ghi, không notify lại
        AssetRepo.set_values(asset_name, {"calibration_status": new})
        try:
            notifications.notify_calibration_due(asset_name, old, new)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "imm11 notify_calibration_due")


def _reconcile_calibration_status(asset_name, old, derived):
    """Quyết định giá trị cache mới cho 1 asset (pure decision, không I/O ngoài 1 lookup status).

    - derived = giá trị từ SoT schedule (None nếu asset KHÔNG còn active schedule).
    - BR-11-11 FAILED-preserve: old == FAILED ∧ asset Out of Service → giữ FAILED (terminal).
      Recal Pass (handle_calibration_pass) là CON ĐƯỜNG DUY NHẤT rời FAILED → set ON_SCHEDULE.
    - derived có giá trị (asset còn active schedule) → dùng derived (Overdue/DueSoon/OnSchedule).
    - derived None (BR-11-10 stale-clear): KHÔNG còn active schedule → reset neutral NOT_REQUIRED.
    """
    if old == CalibrationStatus.FAILED:
        lifecycle = AssetRepo.get_value(asset_name, "lifecycle_status")
        if lifecycle == AssetStatus.OUT_OF_SERVICE:
            return CalibrationStatus.FAILED               # BR-11-11 preserve terminal
    if derived is not None:
        return derived                                    # còn active schedule → SoT rollup
    return CalibrationStatus.NOT_REQUIRED                  # BR-11-10 stale-clear → neutral


def _nonempty_cache_asset_ids() -> set[str]:
    """Tập asset có calibration_status != '' (cache khác rỗng) — để reconcile thăm CẢ
    asset không-còn-trong-rollup (lịch deactivate/xóa) → stale-clear (BR-11-10)."""
    rows = frappe.db.sql(
        "SELECT name FROM `tabAC Asset` "
        "WHERE calibration_status IS NOT NULL AND calibration_status != ''",
        as_dict=True,
    )
    return {r["name"] for r in rows}
```

**Quyết định reconcile per-asset (decision table):**

| `old` (cache) | `lifecycle_status` | `derived` (SoT rollup) | → `new` | Rule |
|---|---|---|---|---|
| `Calibration Failed` | `Out of Service` | bất kỳ | `Calibration Failed` (giữ) | BR-11-11 preserve |
| `Calibration Failed` | KHÔNG Out of Service | có giá trị | `derived` | recal Pass đã đưa về Active → cho rollup tiếp quản |
| bất kỳ ≠ FAILED | bất kỳ | `Overdue`/`Due Soon`/`On Schedule` | `derived` | SoT rollup bình thường |
| `Overdue`/`Due Soon`/`On Schedule`/`Not Required` | bất kỳ (≠ OoS-FAILED) | `None` (hết active schedule) | `Not Required` | BR-11-10 stale-clear |
| `''` (rỗng) | bất kỳ | `None` | `''` (giữ rỗng) | không có gì để clear — bỏ qua, không notify |

- **Idempotency + anti-spam (giữ nguyên, mở rộng):** chỉ `set_values` + `notify_calibration_due` khi `new != old`. Cả nhánh stale-clear (Overdue→Not Required) và preserve (FAILED→FAILED) đều idempotent: lần 2 `new == old` → no-op, không notify. Reset stale (`Overdue → Not Required`) là chuyển RA khỏi Due Soon/Overdue → `notify_calibration_due` không spam (chỉ notify khi chuyển VÀO Due Soon/Overdue — xem `docs/imm-00/04_Backend_Design.md §III.1b-2`).
- **SoT count KHÔNG đổi:** `_overdue_asset_ids` / `_due_soon_asset_ids` / `_calibration_status_asset_ids` GIỮ NGUYÊN byte-for-byte. Fix CHỈ chạm write-path cache trong `check_calibration_expiry` (+ 2 helper mới `_reconcile_calibration_status`, `_nonempty_cache_asset_ids`). KPI/drill/dashboard parity (BR-11-08/09) không bị ảnh hưởng → `test_dashboard` + `test_imm11` SoT-cases không regress.
- `AC Asset.calibration_status` vẫn **chỉ là cache** hiển thị nhanh trên trang asset detail/list — KPI/drill/dashboard KHÔNG đọc nó (đọc SoT trực tiếp).

### 4.1.4 `get_calibration_kpis` / `get_dashboard` — đọc SoT

`overdue_assets = len(_overdue_asset_ids())`, `due_soon_assets = len(_due_soon_asset_ids())` (KHÔNG còn `AssetRepo.count({"calibration_status": OVERDUE})`). Danh sách overdue/due_soon top-N trong `get_dashboard` lấy theo cùng tập asset (JOIN schedule SoT) order by `next_due_date asc`. **Shape KPI/dashboard KHÔNG đổi** bởi BR-11-12 (§4.1.5) — guard chỉ chạm write-path lifecycle, không chạm read-path KPI.

### 4.1.5 `handle_calibration_pass` — restore-guard liên-module (BR-11-12)

> **BUG (Self-Correction):** nhánh `elif cal_doc.is_recalibration and current_status == OUT_OF_SERVICE: _transition_asset(asset, ACTIVE, ...)` ép Active VÔ ĐIỀU KIỆN trên mọi recal Pass. `Out of Service` là trạng thái dùng chung nhiều module → recal Pass force-restore xoá hold của Incident/Repair/PM (force-override liên-module) và đưa thiết bị chưa-an-toàn lại lâm sàng. FIX: thêm predicate `_can_restore_from_oos`, mọi nhánh ép Active-từ-OoS đi qua predicate; nhánh `Calibrating → Active` GIỮ NGUYÊN.

**Cấu trúc nhánh restore (sau khi ghi ALE `calibration_passed` + cập nhật dates):**

```python
# imm11.py — handle_calibration_pass (nhánh restore, thay block elif is_recalibration cũ)
current_status = AssetRepo.get_value(cal_doc.asset, "lifecycle_status")
# ALE 'calibration_passed' đã ghi from=to=current_status (audit luôn có record).

if current_status == AssetStatus.CALIBRATING:
    # Nhánh A — GIỮ NGUYÊN (BR đúng): Calibrating → Active (transition tự ghi ALE 'activated').
    _transition_asset(cal_doc.asset, AssetStatus.ACTIVE, cal_doc.name,
                      reason=f"Calibration passed — {cal_doc.name}")
elif current_status == AssetStatus.OUT_OF_SERVICE:
    # Nhánh B — restore CÓ ĐIỀU KIỆN (BR-11-12). MỌI ép-Active-từ-OoS đi qua predicate.
    if _can_restore_from_oos(cal_doc.asset, cal_doc):
        _transition_asset(cal_doc.asset, AssetStatus.ACTIVE, cal_doc.name,
                          reason=f"Recalibration Pass — hold hiệu chuẩn giải toả, không hold khác — {cal_doc.name}")
    else:
        # GIỮ OoS — ghi 1 ALE giữ-trạng-thái với hold-note (KHÔNG transition, KHÔNG raise).
        src = _hold_source_label(cal_doc.asset)   # 'Sự cố (IMM-12)' | 'Sửa chữa (IMM-09)' | 'Bảo trì (IMM-08)' | 'hiệu chuẩn còn hold khác'
        create_lifecycle_event(
            asset=cal_doc.asset, event_type="calibration_passed",
            actor=frappe.session.user,
            from_status=current_status, to_status=current_status,
            root_doctype=CalibrationRepo.DOCTYPE, root_record=cal_doc.name,
            notes=_oos_hold_note(cal_doc.asset, src),
        )
# else: prev ∈ {Decommissioned, …} → KHÔNG ép Active (no-raise). ALE 'calibration_passed' đầu hàm đã đủ audit.
```

> ⚠️ **Lưu ý ALE-kép:** ALE `calibration_passed` (from=to=current) đã ghi ở đầu `handle_calibration_pass` cho MỌI Pass. Nhánh giữ-OoS KHÔNG cần ghi ALE thứ 2 nếu hold-note đã được nhồi vào ALE đầu. **Quyết định BA:** nhồi `_oos_hold_note(...)` vào `notes` của ALE đầu khi prev==OoS ∧ ¬restore → đúng AC-11-16/17 "ghi 1 ALE `calibration_passed` from=OoS to=OoS + hold-note" (1 ALE, KHÔNG trùng). BE chọn 1 trong 2 cách (nhồi note vào ALE đầu HOẶC tách như snippet) miễn KẾT QUẢ = đúng 1 ALE giữ-OoS có hold-note. Test AC-11-18 đếm ALE để chặn double-write.

**Predicate `_can_restore_from_oos`:**

```python
def _can_restore_from_oos(asset: str, cal_doc) -> bool:
    """BR-11-12 — True ⟺ recal Pass được phép đưa asset Out of Service → Active.

    Điều kiện AND:
      1. Chủ-hold OoS == chuỗi hiệu chuẩn: ALE mới nhất đưa asset VÀO 'Out of Service'
         có root_doctype == 'IMM Asset Calibration' (_latest_oos_root_doctype).
      2. KHÔNG còn hold governance khác mở của asset:
         - Incident mở  : open_incident_filter() (IMM-12, lazy import)
         - Repair WO mở : open_repair_filter()   (IMM-09, lazy import)
         - PM WO OoS-finding mở: PM Work Order status NOT IN [Completed, Cancelled]
           + asset đã bị PM đẩy OoS (ALE root_doctype='PM Work Order').
    Pure read-only; KHÔNG raise. Bất kỳ điều kiện fail → False (giữ OoS).
    """
```

**Nguồn hold ↔ `root_doctype` (de-conflict liên-module):**

| Module | `root_doctype` ALE vào OoS | "đang mở" predicate | Stable contract reuse |
|---|---|---|---|
| IMM-11 (calibration) | `IMM Asset Calibration` | (chủ-hold điều kiện 1) | — |
| IMM-12 (incident) | `Incident Report` | `open_incident_filter()` | `services.imm12.open_incident_filter` (lazy import) |
| IMM-09 (repair) | `Asset Repair` | `is_repair_open()` / `open_repair_filter()` | `services.imm09.open_repair_filter` (lazy import) |
| IMM-08 (PM-finding) | `PM Work Order` | `status NOT IN [Completed, Cancelled]` | `PMWorkOrderRepo` filter |

- **Pattern B (cross-module)**: lazy-import `open_incident_filter` / `open_repair_filter` BÊN TRONG function body (tránh circular import — xem assetcore-doc Phần 3 Pattern B). Truyền `asset` (string PK), KHÔNG truyền Document.
- **No-raise (INV-11-RESTORE-1)**: predicate + nhánh restore KHÔNG raise; nếu asset đã `Decommissioned` giữa chừng, `current_status` ≠ OUT_OF_SERVICE → rơi vào nhánh else (no-op transition) → on_submit Pass luôn đóng được (AC-11-18).
- **Idempotent**: `transition_asset_status` đã guard `prev == to_status → return` (imm00.py:105) → chạy lại cùng cal Pass KHÔNG tạo ALE `activated` trùng. ALE `calibration_passed` from=to là append-only audit (1 lần / submit).
- **Grep-guard SoT (AC-11-18)**: trong `handle_calibration_pass`, KHÔNG còn nhánh `_transition_asset(..., ACTIVE, ...)` từ prev=OoS NGOÀI block `if _can_restore_from_oos(...)`. Test ràng buộc: 0 đường ép Active-từ-OoS bỏ qua predicate.

### 4.1.6 `handle_calibration_fail` — Schedule due-now write (BR-11-08b)

> **Self-Correction (RC-FAIL-DUENOW).** `handle_calibration_fail` hiện set `calibration_status=FAILED` (cache) + transition OoS + CAPA + lookback + Incident NHƯNG **không chạm `Schedule.next_due_date`**. Vì KPI/drill đếm theo SoT schedule date (BR-11-08, KHÔNG đọc cache), schedule giữ ngày-tương-lai → asset FAIL bị KPI xếp ON_SCHEDULE (mask gap). Thêm 1 write-path **trong cùng** `handle_calibration_fail` để hạ MỌI active schedule về basis-date (due-now).

**Basis-date (dùng chung PASS):**
```python
basis = cal_doc.certificate_date or cal_doc.actual_date or nowdate()
```
Đúng 1 nguồn — `handle_calibration_pass` (line ~552) advance = `basis + interval`; FAIL set = `basis` (due-now). Không drift.

**Write-path (đặt SAU `transition_asset_status(... OUT_OF_SERVICE ...)` trong `handle_calibration_fail`):**
```python
# BR-11-08b: hạ MỌI active schedule của asset về due-now (basis <= today) →
# asset rơi vào overdue/due-soon set (SoT), KHÔNG còn ON_SCHEDULE.
# Theo ASSET (không chỉ cal_doc.calibration_schedule) — asset Class B+ có thể
# có nhiều loại calibration → nhiều schedule active; tất cả phải due-now.
active_scheds, _ = CalibrationScheduleRepo.list(
    filters={"asset": cal_doc.asset, "is_active": 1},
    fields=["name"], page_size=10_000,
)
for s in active_scheds:                          # null-safe: rỗng → no-op
    CalibrationScheduleRepo.set_values(s["name"], {"next_due_date": basis})
```

**Invariants:**
- **INV-FAIL-DUENOW-1 (due-now):** sau FAIL, ∀ active schedule của asset có `next_due_date == basis <= today` → asset ∈ `_overdue_asset_ids()` (basis<today) ∪ `_due_soon_asset_ids()` (basis==today). KPI overdue_assets/due_soon_assets đếm asset; count == drill (BR-11-08).
- **INV-FAIL-DUENOW-2 (theo asset, 1 batch):** dùng `CalibrationScheduleRepo.list({asset, is_active=1})` (1 query) + loop set_values — KHÔNG N+1 trên list; KHÔNG giới hạn ở `cal_doc.calibration_schedule` (cal có thể không gắn schedule, hoặc asset có schedule loại khác).
- **INV-FAIL-DUENOW-3 (null-safe / idempotent):** 0 active schedule → loop rỗng → no-op, KHÔNG raise; CAPA + Incident + lookback (đường FAIL hiện hữu) KHÔNG đổi. Resubmit/amend cùng basis → bất biến.
- **INV-FAIL-DUENOW-4 (không ép vòng đời khác):** chỉ ghi `next_due_date`; `lifecycle_status` giữ Out of Service (do transition trên), `calibration_status` giữ FAILED (BR-11-11). KHÔNG đổi state machine, KHÔNG đổi `is_active` (schedule vẫn active → vẫn được KPI đếm).
- **INV-FAIL-DUENOW-5 (khép kín):** recalibration Pass sau đó (`handle_calibration_pass`) advance `next_due_date = basis + interval` (tương lai) → asset rời overdue/due-soon → ON_SCHEDULE. Vòng đời fail→due-now→pass→on-schedule khép kín.

**PASS không đổi bởi BR-11-08b (regression xanh):** fix BR-11-08b CHỉ thêm write-path vào nhánh FAIL; SoT `Schedule.next_due_date` của nhánh PASS (advance `= basis + interval`) byte-for-byte bất biến. ⚠️ ASSET-cache của PASS (`calibration_status` / `next_calibration_date`) ĐƯỢC sửa riêng ở **§4.1.7 (BR-11-13)** — KHÔNG do BR-11-08b; 2 fix độc lập, không trộn.

### 4.1.7 `handle_calibration_pass` — Asset-cache ROLLUP đa-lịch (BR-11-13)

> **Self-Correction (RC-PASS-ROLLUP).** `handle_calibration_pass` ghi ASSET-cache `{calibration_status: ON_SCHEDULE (hardcode), next_calibration_date: add_days(basis, interval)}` = trạng-thái/hạn của **CHỈ schedule vừa Pass**, bỏ qua active schedule KHÁC. Trong khi `check_calibration_expiry` rollup cache từ MỌI active schedule (`_calibration_status_asset_ids`, worst-of). → 2 write-path cùng ghi 1 cache field theo 2 logic ≠ → asset multi-schedule: badge "Đúng lịch" sau Pass while dashboard SoT vẫn Overdue + asset rớt khỏi `get_due_calibrations` (filter cache `next_calibration_date`). Mirror của BR-11-08b. Chi tiết RC: `02_Analysis_Design.md §BR-11-13`.

**Helper rollup (tái dùng SoT — KHÔNG copy logic):**
```python
def _asset_min_next_due(asset_name: str) -> str | None:
    """MIN(next_due_date) trên MỌI active schedule của asset (1 query bounded).
    None nếu asset không còn active schedule với next_due_date."""
    row = frappe.db.sql(
        """
        SELECT MIN(next_due_date) AS min_due
        FROM `tabIMM Calibration Schedule`
        WHERE asset = %(a)s AND is_active = 1 AND next_due_date IS NOT NULL
        """,
        {"a": asset_name}, as_dict=True,
    )
    return (row[0]["min_due"] if row and row[0]["min_due"] else None)


def _apply_asset_calibration_rollup(asset_name: str, basis: str) -> None:
    """Ghi ASSET-cache 3 field theo ROLLUP đa-lịch (BR-11-13). Gọi SAU khi schedule
    vừa Pass đã advance next_due_date (để rollup thấy date mới). CÙNG SoT
    `_calibration_status_asset_ids` mà check_calibration_expiry dùng → ROLLUP-CONSISTENCY.
    """
    status = _calibration_status_asset_ids().get(
        asset_name, CalibrationStatus.ON_SCHEDULE)   # worst-of-all; fallback ON_SCHEDULE
    min_due = _asset_min_next_due(asset_name)         # hạn gần nhất thật (MỌI active sched)
    AssetRepo.set_values(asset_name, {
        "last_calibration_date": basis,
        "next_calibration_date": min_due,             # MIN, KHÔNG next của 1 lịch
        "calibration_status": status,                 # rollup, KHÔNG hardcode ON_SCHEDULE
    })
```
> **N+1 note:** `_calibration_status_asset_ids()` là 3 set-query toàn-tập (đã có, KHÔNG per-asset loop) + `_asset_min_next_due` 1 aggregate-query → rollup 1 asset = **4 query bounded**, độc lập số schedule. Nếu BE thấy build map toàn-tập chỉ cho 1 asset là phí, có thể viết `_asset_rollup_status(asset)` chạy CÙNG predicate (`is_calibration_overdue`/`is_calibration_due_soon`) trên đúng schedule của 1 asset (≤2 query) — miễn KẾT QUẢ == `_calibration_status_asset_ids()[asset]` (INV-PASS-ROLLUP-1 là invariant chốt, không ràng buộc cách viết).

**Thay block hardcode trong `handle_calibration_pass` (services/imm11.py:563-567):**
```python
# CŨ (XÓA) — hardcode 1-lịch:
# AssetRepo.set_values(cal_doc.asset, {
#     "last_calibration_date": basis_date,
#     "next_calibration_date": next_date,
#     "calibration_status": CalibrationStatus.ON_SCHEDULE,
# })

# MỚI — ghi schedule vừa Pass TRƯỚC (advance next_due_date), RỒI rollup ASSET-cache:
CalibrationRepo.set_values(cal_doc.name, {"next_calibration_date": next_date})  # phiếu — GIỮ
if cal_doc.calibration_schedule:
    CalibrationScheduleRepo.set_values(cal_doc.calibration_schedule, {
        "last_calibration_date": basis_date,
        "next_due_date": next_date,                  # BR-11-04 — SoT schedule advance, GIỮ
    })
_apply_asset_calibration_rollup(cal_doc.asset, basis_date)  # BR-11-13 — cache rollup đa-lịch
```
> ⚠️ **Thứ tự bắt buộc:** `_apply_asset_calibration_rollup` phải chạy SAU `CalibrationScheduleRepo.set_values(...next_due_date=next_date)` để rollup đọc được date đã advance của schedule vừa Pass (nếu chạy trước, rollup thấy date cũ → sai cho happy-path 1-lịch). ALE `calibration_passed` + restore-guard 3-nhánh (§4.1.5) chạy SAU rollup, KHÔNG đổi.

**Invariants:**
- **INV-PASS-ROLLUP-1 (status == SoT):** sau PASS, `AC Asset.calibration_status == _calibration_status_asset_ids().get(asset, ON_SCHEDULE)`. Multi-schedule còn lịch overdue → `Overdue` (KHÔNG ON_SCHEDULE).
- **INV-PASS-ROLLUP-2 (next == MIN):** `AC Asset.next_calibration_date == MIN(next_due_date)` trên MỌI active schedule → asset KHÔNG rớt khỏi `get_due_calibrations` khi còn lịch sớm hơn.
- **INV-PASS-ROLLUP-3 (idempotent scheduler):** `check_calibration_expiry()` ngay sau PASS → `_reconcile_calibration_status` thấy `new == old` → no-write, no-notify (no flip-flop badge). Vì PASS-cache và scheduler-cache cùng nguồn `_calibration_status_asset_ids`.
- **INV-PASS-ROLLUP-4 (happy-path bất biến):** asset 1-lịch → schedule duy nhất sau advance có `next_due > today+30` → rollup `ON_SCHEDULE`, `MIN` = chính `basis+interval` → cache y hệt cũ (`On Schedule` + `add_days(basis, interval)`).
- **INV-PASS-ROLLUP-5 (BR-11-04/12 bất biến):** `Schedule.next_due_date` (vừa Pass) = `basis+interval`; `CalibrationRepo.next_calibration_date` set như cũ; ALE `calibration_passed` (1 record) + restore-guard 3-nhánh KHÔNG đổi. BR-11-13 CHỈ chạm 3 field ASSET-cache.
- **INV-PASS-ROLLUP-6 (no N+1):** rollup 1 asset = số query bounded (≤4), độc lập số schedule — KHÔNG loop per-schedule SQL.

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
| `list_calibrations(filters, mine, page, page_size)` | GET | List calibrations with pagination (+ `mine=1` self-scope `technician` — §5.1) |
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

> ⚡ **VERB-FLIP `add_measurement` (R34 — ADR-IMM11-MOB-03 / ADR-MOBILE-011, xem `05_API_Specification.md §0.1.4`):** cột Method = **POST** ở trên là verb-INTENT (write-action: append child-row, KHÔNG idempotent). Decorator THẬT `api/imm11.py:120` hiện **bare `@frappe.whitelist()`** (nhận cả GET — verb-parity gap R33 BỎ SÓT). **Fix R34 = flip ĐÚNG 1 dòng** `api/imm11.py:120` → `@frappe.whitelist(methods=['POST'])` (signature `:121-123` + body `:124-132` + `rbac.require('calibration.write')` `:124` UNCHANGED; `git diff api/imm11.py` = 1 dòng decorator). Mirror `create_calibration` `:89` / `submit_calibration` `:114` (đã flip @R33). Sau flip POST-only ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. Cần USER reload gunicorn `--preload` để LIVE reject GET(405) — guard in-process KHÔNG cần (HARD-STOP USER).

---

### 5.1 Mobile-BE contract — `listCalibrations` self-scope `mine` (đóng-nốt quartet phiếu-của-tôi: tab "Phiếu hiệu chuẩn của tôi" MVP-5d)

**Vấn đề gốc (contract nói dối — đối-xứng A2 known-gap):** OpenAPI `listCalibrations` summary `[MVP-5d] Hiệu chuẩn của tôi` ĐÃ hứa semantics "của tôi", NHƯNG `list_calibrations(filters, page, page_size)` (`api/imm11.py:71`) **KHÔNG có cơ chế** scope theo `technician` — chỉ `parse_json(filters)` (`:72-75`, in-try/except → `_err` Error-trên-HTTP-200) + `apply_vendor_scope("Calibration Record")` (`:76`) rồi `handle(svc.list_calibrations, …)` (`:77`). ⇒ tab trả **mọi** Calibration Record mà quyền đọc cho phép (kể cả phiếu giao KTV khác), KHÔNG self-scope. Đối-xứng PM (ADR-MOBILE-016) / CM (ADR-MOBILE-017) / Incident (ADR-MOBILE-015) — đây là **mắt-xích THỨ TƯ đóng-nốt quartet** phiếu-của-tôi của MyWorkOrdersView.

**5-câu-hỏi domain:** (stage HTM) Operation/Maintenance — calibration/performance; (NĐ98) traceability hiệu chuẩn gắn ĐÚNG KTV thực hiện (chứng chỉ truy được người chịu trách nhiệm); (stakeholder) KTV field-tech mobile + Calibration Manager/QA web; (lifecycle event) calibration tạo với `technician` reqd (`services/imm11.py:1052`); (hậu quả nếu data sai) tab hiển thị phiếu người khác → KTV nhầm việc, nhưng **KHÔNG leak quyền** vì read-gating GIỮ DocPerm — `mine` chỉ là filter hiển thị.

| Khía cạnh | Quyết định | Evidence |
|---|---|---|
| Param | `mine: int = 0` (`0\|1`), chèn GIỮA `filters`↔`page` (mirror `imm08.py:29` / `imm09.py:22`); inject @api SAU `apply_vendor_scope("Calibration Record")`, TRƯỚC `handle(svc.list_calibrations)` | `api/imm11.py:71,76-77` |
| Injection | `if int(mine or 0): f["technician"] = frappe.session.user` — **cột `technician`** (KHÁC PM/CM `assigned_to`) | `imm_asset_calibration.json:131` (Link `User`, reqd) |
| count==rows | `count_with_or` + `get_all` (`BaseRepository.list base.py:65-71`) dùng CÙNG `filters` dict (đã có `technician`); list_calibrations KHÔNG truyền `or_filters` ⇒ `count_with_or`=`frappe.db.count` thuần. Calibration Record **KHÔNG có** `permission_query_conditions` riêng ⇒ KHÔNG có nhánh count/rows lệch | `repositories/base.py:48-76`, `hooks.py:388` |
| Backward-compat | `mine=0`/absent ⇒ `filters` BYTE-IDENTICAL baseline (web-FE `CalibrationListView` KHÔNG đổi) | — |
| Contract | OpenAPI REUSE `components/parameters/WorkOrderMine` (R38) — **0 component mới**; param-set `{WorkOrderFilters,Page,PageSize}`→+`WorkOrderMine`=4; path-count GIỮ 47 | `docs/mobile/openapi/assetcore-mobile.openapi.yaml`, `docs/mobile/ADR-MOBILE-019.md` |

**Boundaries:**

| | |
|---|---|
| **Always** | `mine` ANDed với mọi key trong `filters` JSON-blob (vd `{"status":"Scheduled"}`, `{"calibration_type":"External"}`). Inject `technician=session.user` @api SAU `apply_vendor_scope`. count==rows giữ (cùng filters dict). `mine=0`/absent = baseline byte-identical. REUSE `WorkOrderMine` (KHÔNG component mới). Signature LIVE `['filters','mine','page','page_size']`. |
| **Never** | KHÔNG inject `assigned_to` (Calibration Record không có cột này — PHẢI `technician`). KHÔNG tạo component `CalibrationMine` (shape trùng `WorkOrderMine`). KHÔNG thêm endpoint `list_my_calibrations` (+path). KHÔNG auto-scope qua `permission_query_conditions` (Calibration hiện KHÔNG có; thêm sẽ vỡ view Manager/QA). KHÔNG coi `mine` là security-boundary (read-gating vẫn DocPerm `calibration.read` + `apply_vendor_scope`). KHÔNG đụng `services/imm11.py`/`repositories/`. |

**ADR-IMM11-LISTMINE — `listCalibrations` self-scope qua param opt-in `mine` (REUSE `WorkOrderMine`, inject cột `technician` @api SAU `apply_vendor_scope`)**

- **Status:** Accepted · **Date:** 2026-06-29 · đối-xứng ADR-MOBILE-016/017 (PM/CM) — xem mobile `docs/mobile/ADR-MOBILE-019.md`.
- **Context:** `list_calibrations` summary hứa "của tôi" nhưng không có cơ chế scope `technician` (claim suông). Tab "Phiếu hiệu chuẩn của tôi" (MVP-5d) cần self-scope. `WorkOrderMine` đã tồn tại từ R38 (PM) — cùng shape int 0|1. CAL filters là JSON-blob `parse_json` @api (như PM/CM, KHÁC imm12 discrete).
- **Decision:** REUSE `WorkOrderMine` + `$ref` vào `listCalibrations.parameters` + generalize description (PM/CM→PM/CM/CAL, ghi rõ cột scope khác theo list); `api/imm11.py` thêm `mine: int = 0` GIỮA filters↔page + `if int(mine or 0): f["technician"]=frappe.session.user` SAU `apply_vendor_scope`. KHÔNG đụng service/repo.
- **Alternatives (rejected):** (a) inject `assigned_to` mirror PM/CM — SAI source (Calibration Record không có cột `assigned_to`, KTV = `technician`); (b) endpoint riêng — +path, nhân đôi enrich (asset_name/lab_name/technician_name); (c) component `CalibrationMine` mới — shape trùng `WorkOrderMine`, vỡ "0 component mới"; (d) `permission_query_conditions` auto-scope — Calibration hiện không có, thêm sẽ vỡ view Manager/QA cần thấy tất cả; (e) seed @service — CAL filters parse @api, inject @api blast-radius nhỏ hơn.
- **Consequences:** contract trung thực; `mine=0` backward-compat đo được; count==rows giữ; path-count 47 + 0 component mới ⇒ `generate_spec` get/post/total UNCHANGED (`test_oas_d12/d15/d17` re-verify, KHÔNG re-baseline). **Quartet phiếu-của-tôi ĐÓNG TRỌN** (Incident/PM/CM/Calibration). Ghi rõ tiền-lệ "1 component `WorkOrderMine`, cột scope per-op khác" — param shape là contract, column-mapping (`assigned_to`/`technician`/`reported_by`) là chuyện @api-handler. `mine` = filter ứng-dụng KHÔNG-phải-security-boundary.

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
| `check_calibration_expiry` | Daily 06:30 | `scheduler_events.daily` | Rollup cache `calibration_status` từ SoT schedule (§4.1.3); notify khi chuyển VÀO Due Soon/Overdue (anti-spam, chỉ khi status đổi) |
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
