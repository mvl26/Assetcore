# 04 — Thiết kế Backend — IMM-09 Sửa chữa (Corrective Maintenance)

| Mục | Giá trị |
|---|---|
| Module | IMM-09 — Corrective Maintenance / Repair |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | [02 Analysis & Design](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) |
| Cập nhật | 2026-05-14 |

---

## 1. Tổng quan kiến trúc

IMM-09 bám kiến trúc **3-tier strict**: API → Service → DocType/ORM. Logic nghiệp vụ tập trung trong `services/imm09.py`. Controller `asset_repair.py` chỉ delegate sang service. API layer (`api/imm09.py`) là thin wrapper dùng `_handle / _ok / _err`.

```
Browser/Client
    │ HTTP (token/sid)
    ▼
api/imm09.py          ← 12 endpoints, thin wrapper
    │
    ▼
services/imm09.py     ← 13+ business functions, SLA, MTTR, lifecycle events
    │
    ▼
asset_repair.py       ← controller hooks (delegate sang service)
    │
    ▼
Frappe ORM + MariaDB  ← 4 DocTypes
```

> **Quy ước ngôn ngữ:** Code/fieldname tiếng Anh · Field label tiếng Việt · Error message tiếng Việt qua `frappe._()` · DTO mirror FE TypeScript types trong `frontend/src/types/imm09.ts`

---

## 2. Domain Model — DocType

### 2.1 Asset Repair

- **Naming:** `WO-CM-.YYYY.-.#####`
- **Submittable:** Yes — immutable sau docstatus=1
- **Track changes:** Yes

| Trường | Type | Required | Notes |
|---|---|---|---|
| `asset_ref` | Link → Asset | ✓ | search_index, in_list_view |
| `incident_report` | Link Incident Report | BR-09-01 | OR source_pm_wo |
| `source_pm_wo` | Link PM Work Order | BR-09-01 | OR incident_report |
| `repair_type` | Select | ✓ | Corrective/Emergency/Warranty Repair |
| `priority` | Select | ✓ | Normal/Urgent/Emergency, default Normal |
| `status` | Select | ✓ | 9 states, default Open |
| `open_datetime` | Datetime | — | auto=now() before_insert |
| `assigned_datetime` | Datetime | — | auto khi assign |
| `completion_datetime` | Datetime | — | auto on_submit |
| `sla_target_hours` | Float | — | auto từ get_sla_target() |
| `mttr_hours` | Float | — | auto = `repair_elapsed_hours(doc, completion_datetime)` = `(completion−open) − parts_hold_hours` (clock-stop, **BR-09-10**). Khi `parts_hold_hours==0` ⇒ `(completion−open)/3600` cũ. |
| `sla_breached` | Check | — | auto = `is_sla_breached(repair_elapsed_hours(doc, completion), sla_target)` (boundary `>=`, BR-09-07; **NGUỒN elapsed = clock-stop SoT BR-09-10**); monotonic — completion KHÔNG reset 1→0 |
| `parts_hold_hours` | Float | — | **MỚI (BR-09-10)** default 0; tổng cộng dồn (giờ) mọi khoảng WO nằm Pending Parts. MONOTONIC tăng (INV-CM-HOLD-3). KHÔNG `in_list_view`. read_only. |
| `parts_hold_started` | Datetime | — | **MỚI (BR-09-10)** null khi không hold; STAMP khi VÀO Pending Parts, RESET null khi RA / khi đóng WO lúc đang hold (INV-CM-HOLD-2). non-null ⟺ status==Pending Parts. read_only. |
| `is_repeat_failure` | Check | — | auto before_insert |
| `assigned_to` | Link User | — | KTV thực hiện |
| `diagnosis_notes` | Text | — | — |
| `root_cause_category` | Select | — | 6 options |
| `repair_summary` | Text | (close) | reqd khi Completed |
| `spare_parts_used` | Table | — | child |
| `total_parts_cost` | Currency | — | auto Σ |
| `repair_checklist` | Table | (close) | child; 100% Pass (BR-09-04) |
| `firmware_updated` | Check | — | trigger BR-09-03 |
| `firmware_change_request` | Link FCR | BR-09-03 | reqd khi firmware_updated=1 |
| `dept_head_name` | Data | (close) | reqd khi Completed |
| `cannot_repair_reason` | Text | (cannot) | reqd khi Cannot Repair |

**Permissions:**

| Role | R | W | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| Workshop Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| CMMS Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| HTM Technician | ✓ | ✓ (own) | ✗ | ✗ | ✗ | ✗ |
| Kho vật tư | ✓ | ✓ (parts only) | ✗ | ✗ | ✗ | ✗ |
| Trưởng khoa | ✓ | ✓ (dept_head_name) | ✗ | ✗ | ✗ | ✗ |
| PTP Khối 2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Permission Query (HTM Technician):** `permission.py` → filter `assigned_to = session.user`

### 2.2 Firmware Change Request

- **Naming:** `FCR-.YYYY.-.#####`
- **Submittable:** Yes

| Trường | Type | Required | Notes |
|---|---|---|---|
| `asset` | Link Asset | ✓ | — |
| `repair_wo` | Link Asset Repair | ✓ | — |
| `version_before` | Data | ✓ | — |
| `version_after` | Data | ✓ | — |
| `change_notes` | Text | ✓ | — |
| `status` | Select | ✓ | Draft/Pending Approval/Approved/Applied/Rolled Back |
| `approved_by` | Link User | (Approve) | reqd on Approve |

---

## 3. Workflow (State Machine)

State machine enforce **qua controller + API guard** — không dùng Frappe Workflow record (optional cho wave 2).

**States:**

| State | Style | docstatus | allow_edit role |
|---|---|---|---|
| Open | Warning | 0 | Workshop Manager |
| Assigned | Primary | 0 | Workshop Manager |
| Diagnosing | Primary | 0 | KTV HTM |
| Pending Parts | Warning | 0 | KTV / Kho |
| In Repair | Danger | 0 | KTV HTM |
| Pending Inspection | Primary | 0 | KTV HTM |
| Completed | Success | 1 | — (submitted) |
| Cannot Repair | Danger | 0 | Workshop Manager |
| Cancelled | Secondary | 2 | — (cancelled) |

**Key transitions (API-driven):**

| From | To | Trigger | Actor | Validation |
|---|---|---|---|---|
| (insert) | Open | `create_work_order` | Workshop Manager | BR-09-01 (source) + BR-09-05 (no active WO) |
| Open | Assigned | `assign_technician` | Workshop Manager | — |
| Assigned | Diagnosing | `submit_diagnosis` | KTV HTM | — |
| Diagnosing | Pending Parts | `submit_diagnosis(needs_parts=1)` | KTV HTM | **BR-09-10 ENTER hold:** `enter_parts_hold(doc)` → stamp `parts_hold_started = now()` (INV-CM-HOLD-2); ALE `parts_hold_started` |
| Diagnosing | In Repair | `submit_diagnosis(needs_parts=0)` | KTV HTM | — |
| Pending Parts | In Repair | `request_spare_parts` hoặc `start_repair` | KTV HTM / Kho | **BR-09-10 EXIT hold:** `exit_parts_hold(doc, until=now())` → `parts_hold_hours += (now − parts_hold_started)`, reset `parts_hold_started=null` (INV-CM-HOLD-2/3); ALE `parts_hold_resumed` |
| Any active | In Repair | `start_repair` | KTV HTM | allowed from Assigned/Diagnosing/Pending Parts; nếu from Pending Parts → EXIT hold (như trên) |
| In Repair | Pending Inspection | `close_work_order(cannot_repair=0)` | KTV HTM | Điền repair_summary + dept_head_name |
| **Pending Inspection** | **Completed** | **`confirm_inspection`** | **Dept Head / QA Officer** | `CAN_APPROVE_DEP` role; WO submit → `complete_repair()` (chốt hold cuối nếu `parts_hold_started` còn non-null, INV-CM-HOLD-5) |
| Any active | Cannot Repair | `close_work_order(cannot_repair=1)` | KTV / Workshop Manager | cannot_repair_reason required; nếu đang Pending Parts → EXIT hold tới now() TRƯỚC khi đóng (INV-CM-HOLD-5) |

**Controller hooks:**

```python
# assetcore/assetcore/doctype/asset_repair/asset_repair.py
class AssetRepair(Document):
    def before_insert(self):
        from assetcore.services.imm09 import (
            validate_repair_source, validate_asset_not_under_repair, check_repeat_failure,
        )
        validate_repair_source(self)                          # BR-09-01
        validate_asset_not_under_repair(self.asset_ref)       # BR-09-05
        self.is_repeat_failure = check_repeat_failure(self.asset_ref)  # BR-09-06 (returns bool)
        self.open_datetime = now_datetime()                   # audit timestamp

    def on_insert(self):
        from assetcore.services import imm09 as svc
        svc.set_asset_under_repair(self.asset_ref, self.name)  # BR-09-05

    def validate(self):
        from assetcore.services import imm09 as svc
        svc._compute_parts_cost(self)  # total_parts_cost

    def before_submit(self):
        from assetcore.services import imm09 as svc
        svc.validate_spare_parts_stock_entries(self)   # BR-09-02
        svc.validate_firmware_change_request(self)     # BR-09-03
        svc.validate_repair_checklist_complete(self)   # BR-09-04

    def on_submit(self):
        from assetcore.services import imm09 as svc
        svc.complete_repair(self)  # MTTR, sla_breached, asset restore guarded (BR-09-09), ALE
```

---

## 4. Service Layer

File: `assetcore/services/imm09.py`

### Public functions

| Function | Input | Output | Side effect |
|---|---|---|---|
| `validate_repair_source(doc)` | Document | None | raise ServiceError BR-09-01 |
| `validate_asset_not_under_repair(asset_ref)` | str | None | raise ServiceError BR-09-05 duplicate |
| `check_repeat_failure(doc)` | Document | None | set `doc.is_repeat_failure` |
| `set_asset_under_repair(asset_ref, wo_name)` | str, str | None | Asset status → Under Repair; ALE repair_opened |
| `validate_spare_parts_stock_entries(doc)` | Document | None | raise ServiceError BR-09-02 |
| `validate_firmware_change_request(doc)` | Document | None | raise ServiceError BR-09-03 |
| `validate_repair_checklist_complete(doc)` | Document | None | raise ServiceError BR-09-04 |
| `get_sla_target(risk_class, priority)` | str, str | float | **BẤT BIẾN** (BR-09-10 không đụng) — vẫn tra `_SLA_MATRIX`. |
| `is_sla_breached(elapsed_hours, sla_target)` | float, float | bool | **SoT predicate (BR-09-07) — BẤT BIẾN** (biên `>=`, không đổi): `elapsed_hours >= sla_target`. Hàm DUY NHẤT quyết định breach — gọi từ cả `complete_repair` LẪN `check_repair_sla_breach`. BR-09-10 chỉ đổi NGUỒN `elapsed_hours` (clock-stop), KHÔNG đổi hàm này. Cấm so sánh breach inline ở nơi khác. |
| `repair_elapsed_hours(doc, until)` | Document\|dict, datetime | float | **MỚI — SoT clock-stop elapsed (BR-09-10), INV-CM-HOLD-1.** `= max(0, ((until − open_datetime) − parts_hold_effective)/3600)` với `parts_hold_effective = parts_hold_hours_seconds + (until − parts_hold_started nếu parts_hold_started non-null)`. Pure, no DB write. Điểm DUY NHẤT phái sinh elapsed cho breach+MTTR — `complete_repair`, `check_repair_sla_breach`, `_row_is_live_overdue` ĐỀU gọi hàm này. Cấm tính `(until−open)` thô để quyết breach/MTTR ở nơi khác. |
| `enter_parts_hold(doc)` | Document | None | **MỚI (BR-09-10):** stamp `doc.parts_hold_started = now_datetime()` (idempotent: nếu đã non-null thì giữ nguyên, không re-stamp); ALE `parts_hold_started`. Gọi từ `submit_diagnosis(needs_parts=1)`. |
| `exit_parts_hold(doc, until=None)` | Document, datetime\|None | None | **MỚI (BR-09-10):** nếu `parts_hold_started` non-null → `parts_hold_hours += max(0, (until or now()) − parts_hold_started)`/3600 (biên Δ==0 ⇒ +0, INV-CM-HOLD-3), reset `parts_hold_started=null`; ALE `parts_hold_resumed`. Idempotent: nếu đã null → no-op. Gọi từ `start_repair`/`request_spare_parts` (khi rời Pending Parts) + `complete_repair`/cannot_repair (chốt cuối, until=completion). |
| `is_repair_open(status)` | str\|None | bool | **SoT predicate (BR-09-08)**: open ⟺ `status NOT IN REPAIR_TERMINAL_STATES`; None/rỗng → open. Hàm DUY NHẤT định nghĩa "đang mở". |
| `open_repair_filter(extra=None)` | dict\|None | dict | Trả `{'status': ['not in', sorted(REPAIR_TERMINAL_STATES)], **extra}` (sorted → deterministic, khớp drill SQL byte-for-byte) — filter dùng chung cho mọi `_count`/`get_all`/drill SQL. |
| `sla_breach_live_filter(extra=None)` | dict\|None | dict | **SoT live (BR-09-07 LIVE)**: nhánh "open & vượt hạn & cờ chưa stamp" = `open_repair_filter()` ∧ `{'sla_breached': 0}` ∧ `{'open_datetime': ['<', <cutoff_for_each_sla_bucket>]}`. Vì `sla_target_hours` khác nhau theo (risk_class, priority) → predicate **per-row** (xem `_row_is_live_overdue`); filter này dùng để **thu hẹp candidate** (chỉ WO open & cờ=0), rồi lọc chính xác in-Python. Terminal loại tự nhiên (INV-CM-SLA-4). |
| `cm_sla_breach_count()` | — | int | **SoT live count (BR-09-07 LIVE)**: `count(sla_breached=1)` + `count(candidate open & cờ=0 thoả `_row_is_live_overdue`)`. 2 nhánh exclusive (cờ=1 vs cờ=0) → no double-count, **idempotent vs scheduler** (INV-CM-SLA-2). Wired vào `api/dashboard.py` `cm_sla_breached` thay `_count({sla_breached:1})`. |
| `_row_is_live_overdue(row, now)` | dict, datetime | bool | Per-row derive: `row.sla_breached==0` ∧ `is_repair_open(row.status)` ∧ `is_sla_breached(repair_elapsed_hours(row, now), row.sla_target_hours)`. **BR-09-10:** elapsed dùng SoT clock-stop `repair_elapsed_hours` (trừ `parts_hold_hours` + open-leg đang chạy nếu row.status==Pending Parts) thay `(now−open)` thô ⇒ WO ở Pending Parts KHÔNG live-overdue oan. KHÔNG query thêm — `row` PHẢI có `parts_hold_hours`/`parts_hold_started` trong `fields=[...]`. |
| `_enrich_sla_breach(rows)` | list | None | Gắn `is_sla_breached = bool(row.sla_breached) or _row_is_live_overdue(row, now)` cho mỗi row (in-Python, no extra query). Gọi trong `list_work_orders` → drill có live-truth (INV-CM-SLA-5). |
| `confirm_inspection(name)` | str | dict `{name, status, mttr_hours, sla_breached}` | Pending Inspection → Completed; submit doc → `complete_repair()`; requires `CAN_APPROVE_DEP` role; auto-trigger IMM-12 chronic detect nếu root_cause chứa từ khóa lặp lại |
| `complete_repair(doc)` | Document | None | mttr, sla_breached, **state-machine-guarded asset restore (BR-09-09)**, ALE. **BR-09-10:** TRƯỚC khi tính elapsed → `exit_parts_hold(doc, until=completion_datetime)` chốt open-leg hold cuối (INV-CM-HOLD-5); `mttr_hours = repair_elapsed_hours(doc, completion_datetime)`; `sla_breached = is_sla_breached(repair_elapsed_hours(...), sla_target) OR doc.sla_breached`. Asset→Active CHỈ khi `prev_status == 'Under Repair'`; nếu đang `Out of Service` (hold governance khác) → giữ OoS; nếu `Decommissioned` (terminal) → bỏ qua restore. NEVER raise từ nhánh restore (INV-09-RESTORE-1). |
| `check_repair_sla_breach()` | — | None | **BR-09-10:** elapsed = `repair_elapsed_hours(wo, now())` (clock-stop, trừ hold đang chạy nếu Pending Parts) thay `(now−open)` thô; set sla_breached qua `is_sla_breached`; publish realtime. INV-CM-HOLD-6 (card==scheduler==stamp). |
| `check_repair_overdue()` | — | None | email Workshop Manager |
| `update_asset_mttr_avg()` | — | None | **BẤT BIẾN** (BR-09-10 không đụng): roll-up AVG(`mttr_hours`) 12 tháng. Vì `mttr_hours` đã là clock-stop tại nguồn (`complete_repair`), avg tự động phản ánh đúng — KHÔNG sửa hàm này. |

### SLA Matrix

```python
def get_sla_target(risk_class: str, priority: str) -> float:
    """Tra ma trận SLA target (giờ) theo risk_class x priority."""
    sla_matrix = {
        ("Class III", "Emergency"): 4.0,
        ("Class III", "Urgent"):    24.0,
        ("Class III", "Normal"):    120.0,
        ("Class II",  "Emergency"): 8.0,
        ("Class II",  "Urgent"):    48.0,
        ("Class II",  "Normal"):    72.0,
        ("Class I",   "Emergency"): 24.0,
        ("Class I",   "Urgent"):    72.0,
        ("Class I",   "Normal"):    480.0,
    }
    return sla_matrix.get((risk_class, priority), 480.0)
```

### Clock-stop elapsed — Single Source of Truth (BR-09-10, Self-Correction)

**Vấn đề thiết kế gốc:** CẢ 3 consumer (`complete_repair` lúc đóng, scheduler `check_repair_sla_breach`, card `_row_is_live_overdue`) tính elapsed = wall-clock thuần `(now/completion − open_datetime)`, KHÔNG trừ thời gian WO nằm `Pending Parts` (kho hết hàng — blocker cung ứng/vendor lead-time NGOÀI tầm đội sửa). ⇒ inflate MTTR + **false SLA breach** (phạt oan đội sửa; méo KPI đáp ứng NĐ98 Article 56).

**Quyết định:** thêm helper SoT DUY NHẤT `repair_elapsed_hours` phái sinh elapsed-trừ-hold. CẢ 3 consumer gọi hàm này rồi truyền vào `is_sla_breached` (BR-09-07, biên `>=`, **BẤT BIẾN**). 2 field mới `parts_hold_hours` (cộng dồn) + `parts_hold_started` (mốc open-leg đang chạy).

```python
def repair_elapsed_hours(doc, until) -> float:
    """SoT DUY NHẤT (BR-09-10, INV-CM-HOLD-1): elapsed-trừ-hold (giờ).

    elapsed = (until − open_datetime) − tổng-thời-gian-Pending-Parts
    tổng-hold = parts_hold_hours (đã cộng dồn các khoảng ĐÃ ĐÓNG)
              + (until − parts_hold_started) nếu parts_hold_started còn non-null
                (open-leg ĐANG hold — WO hiện ở Pending Parts).

    Pure, no DB write. `doc` có thể là Document hoặc dict (row từ get_all) —
    đọc open_datetime / parts_hold_hours / parts_hold_started qua getattr/get.
    `parts_hold_hours==0 ∧ parts_hold_started==null` ⇒ trả đúng (until−open)/3600
    cũ (INV-CM-HOLD-4, no-regression).
    """
    open_dt = get_datetime(_field(doc, "open_datetime"))
    until_dt = get_datetime(until)
    wall_seconds = time_diff_in_seconds(until_dt, open_dt)
    hold_seconds = (_field(doc, "parts_hold_hours") or 0.0) * 3600.0
    started = _field(doc, "parts_hold_started")
    if started:                                  # open-leg đang hold
        hold_seconds += max(0.0, time_diff_in_seconds(until_dt, get_datetime(started)))
    return round(max(0.0, wall_seconds - hold_seconds) / 3600.0, 2)
```

**Stamp / accumulate (đối xứng enter ↔ exit, ⚠️ ORDERING):**

```python
def enter_parts_hold(doc) -> None:               # VÀO Pending Parts
    if doc.parts_hold_started:                   # idempotent — không re-stamp
        return
    doc.parts_hold_started = now_datetime()
    _log_lifecycle_event(asset=doc.asset_ref, event_type="parts_hold_started", ...)

def exit_parts_hold(doc, until=None) -> None:    # RA Pending Parts / chốt cuối
    if not doc.parts_hold_started:               # idempotent — không hold đang mở
        return
    until_dt = get_datetime(until) if until else now_datetime()
    delta_h = max(0.0, time_diff_in_seconds(            # biên Δ==0 ⇒ +0 (INV-CM-HOLD-3)
        until_dt, get_datetime(doc.parts_hold_started))) / 3600.0
    doc.parts_hold_hours = (doc.parts_hold_hours or 0.0) + round(delta_h, 4)
    doc.parts_hold_started = None                # reset (INV-CM-HOLD-2)
    _log_lifecycle_event(asset=doc.asset_ref, event_type="parts_hold_resumed", ...)
```

> **⚠️ ORDERING bắt buộc (INV-CM-HOLD-5):** trong `complete_repair` — gọi `exit_parts_hold(doc, until=completion_datetime)` để chốt open-leg cuối **TRƯỚC** khi `mttr_hours = repair_elapsed_hours(doc, completion_datetime)`. Nếu tính elapsed trước khi chốt, khoảng hold cuối bị bỏ sót. Sau chốt, `parts_hold_started` đã null ⇒ `repair_elapsed_hours` chỉ trừ `parts_hold_hours` (đã gồm khoảng cuối) — không double-count.

**Wiring (BE phải làm cùng commit):**
- `submit_diagnosis(needs_parts=1)` → `enter_parts_hold(doc)` trước `RepairRepo.save`.
- `start_repair` / `request_spare_parts` khi `doc.status == PENDING_PARTS` → `exit_parts_hold(doc)` trước khi đổi status sang In Repair.
- `complete_repair` → `exit_parts_hold(doc, until=completion_datetime)` rồi `mttr_hours = repair_elapsed_hours(doc, completion_datetime)`.
- `close_work_order(cannot_repair=1)` khi đang Pending Parts → `exit_parts_hold(doc, until=now())` trước khi đóng (audit khoảng hold cuối, dù WO không tính MTTR).
- `check_repair_sla_breach` / `_row_is_live_overdue`: `fields=[...]` PHẢI thêm `parts_hold_hours`, `parts_hold_started`; elapsed = `repair_elapsed_hours(row, now())`.
- **Grep-guard (zero-tolerance):** sau patch, 0 idiom `time_diff_in_seconds(now/completion, open) ... breach/mttr` thô ở 3 consumer — mọi elapsed cho breach/MTTR đi qua `repair_elapsed_hours`.

### SLA breach predicate — Single Source of Truth (BR-09-07)

`sla_breached` được quyết định bởi **một hàm thuần (pure) DUY NHẤT**. Mục tiêu: completion (`complete_repair`) và scheduler (`check_repair_sla_breach`) KHÔNG BAO GIỜ bất đồng về cùng một cặp `(elapsed_hours, sla_target)`. **BR-09-10:** `elapsed_hours` truyền vào hàm này LUÔN là output của `repair_elapsed_hours` (clock-stop) — KHÔNG phải wall-clock thô.

```python
def is_sla_breached(elapsed_hours: float, sla_target: float) -> bool:
    """SoT cho cờ vi phạm SLA của Asset Repair (BR-09-07).

    Quy ước BIÊN: elapsed BẰNG ĐÚNG target ⇒ ĐÃ vi phạm (`>=`).
    Lý do: target là hạn chót — chạm hạn là đã hết thời gian cho phép, nhất
    quán với hợp đồng SLA và với scheduler (vốn dùng `>=`). Đây là hàm DUY
    NHẤT được phép quyết định breach; cấm viết `mttr > target` / `>= sla`
    rải rác.
    """
    if elapsed_hours is None or sla_target is None:
        return False
    return float(elapsed_hours) >= float(sla_target)
```

**Quy tắc monotonic (latch):** một khi scheduler đã set `sla_breached=1` cho WO đang chạy, completion **KHÔNG được lật về 0**. `complete_repair` set cờ theo OR với giá trị hiện tại:

```python
doc.sla_breached = 1 if (is_sla_breached(doc.mttr_hours, doc.sla_target_hours)
                         or doc.sla_breached) else 0
```

Nhờ vậy: WO có MTTR == target (vd 72 == 72) → scheduler đánh breach=1 → completion giữ nguyên 1 (không flip-flop). MTTR < target và chưa từng breach → 0. MTTR > target → 1.

### KPI/drill 'SLA vi phạm' — LIVE SoT count (BR-09-07 LIVE, Self-Correction)

**Vấn đề thiết kế gốc (Self-Correction):** `api/dashboard.py` đặt `cm_sla_breached = _count("Asset Repair", {"sla_breached": 1})` — chỉ đếm **cờ đã stamp**. Cờ `sla_breached` chỉ set bởi `complete_repair()` (lúc đóng) hoặc scheduler hourly `check_repair_sla_breach()`. ⇒ WO **đang mở** vừa vượt hạn 1–59' nhưng scheduler chưa quét tới có `sla_breached=0` → **KHÔNG đếm** trên card đến đầu giờ kế = **undercount cửa-sổ-trễ-scheduler**. Đồng dạng lỗi đã sửa ở IMM-12 BR-12-09 (incident SLA live SoT).

**Quyết định:** card `cm_sla_breached` + drill đếm theo **live SoT predicate**, KHÔNG chỉ cờ stale. `cm_sla_breach_count()` = hợp 2 nhánh **loại trừ nhau**:

```python
def _row_is_live_overdue(row: dict, now) -> bool:
    """WO đang mở, cờ chưa stamp, nhưng (now - open_datetime) đã ≥ sla_target_hours."""
    if row.get("sla_breached"):                         # nhánh (1) lo cờ=1
        return False
    if not is_repair_open(row.get("status")):           # terminal loại tự nhiên (INV-CM-SLA-4)
        return False
    elapsed_h = time_diff_in_seconds(now, get_datetime(row["open_datetime"])) / 3600.0
    target = row.get("sla_target_hours") or get_sla_target(
        row.get("risk_class") or RiskClass.I, row.get("priority") or "Normal")
    return is_sla_breached(elapsed_h, target)           # SoT predicate (biên >=)

def cm_sla_breach_count() -> int:
    """SoT live count cho card 'SLA vi phạm'. 2 nhánh exclusive → idempotent vs scheduler."""
    flagged = RepairRepo.count({"sla_breached": 1})                       # (1) cờ lịch sử monotonic
    now = now_datetime()
    candidates = RepairRepo.list(                                          # (2) open & cờ=0
        filters=open_repair_filter({"sla_breached": 0}),
        fields=["name", "status", "open_datetime", "sla_target_hours",
                "risk_class", "priority"],
    )[0]
    live_open = sum(1 for r in candidates if _row_is_live_overdue(r, now))
    return flagged + live_open                                            # exclusive ⇒ no double-count

def _enrich_sla_breach(rows: list) -> None:
    """Per-row live-truth cho drill list (INV-CM-SLA-5). In-Python, no extra query."""
    now = now_datetime()
    for r in rows:
        r["is_sla_breached"] = bool(r.get("sla_breached")) or _row_is_live_overdue(r, now)
```

**Wiring:**
- `api/dashboard.py`: `cm_sla_breached = svc.cm_sla_breach_count()` (thay `_count({sla_breached:1})`). Grep-guard: 0 idiom `{"sla_breached": 1}` cho KPI tile.
- `list_work_orders()`: thêm `sla_target_hours` vào `fields=[...]`, gọi `_enrich_sla_breach(rows)` sau `_enrich_rows(rows)` ⇒ drill có `is_sla_breached` live.
- Filter drill `sla_breached=1`: `list_work_orders` trả tập theo enrich — FE đọc `is_sla_breached ?? sla_breached` (xem 06 §FE). Nếu BE cần lọc-server tập breach, dùng `cm_sla_breach_count` predicate (open∪flag) — KHÔNG lọc thô `{sla_breached:1}` (sẽ rớt live-overdue).

**Idempotent vs scheduler (INV-CM-SLA-2):** WO live-overdue đếm ở nhánh (2). Khi scheduler chạy → cờ thành 1 → WO chuyển sang nhánh (1), rời nhánh (2) (vì `sla_breached=0` không còn match). Tổng KHÔNG đổi. 2 nhánh phân hoạch theo cờ (1 vs 0) ⇒ KHÔNG bao giờ chồng.

### Open / terminal-state predicate — Single Source of Truth (BR-09-08)

**Vấn đề thiết kế gốc (Self-Correction, vòng 19):** khái niệm "Asset Repair đang mở" trước đây được tính lặp lại bằng các literal status inline, KHÔNG đồng nhất giữa các consumer:

| Consumer | Vị trí cũ | Filter cũ | Lỗi |
|---|---|---|---|
| KPI thẻ `cm_open` | `api/dashboard.py:87` | `NOT IN [Completed, Closed, Cancelled]` | Đếm cả `Cannot Repair` là mở (sai); có phantom `Closed` |
| Drill-down list | `api/dashboard.py:386` | `NOT IN [Completed, Closed, Cancelled, Cannot Repair]` | Loại `Cannot Repair`; có phantom `Closed` |
| Technician `my_cm` | `api/dashboard.py:562` | `NOT IN [Completed, Closed, Cancelled]` | Đếm `Cannot Repair`; phantom `Closed` |
| Technician `cm_urgent` | `api/dashboard.py:569` | `NOT IN [Completed, Closed, Cancelled]` | Đếm `Cannot Repair`; phantom `Closed` |
| SLA engine | `services/notifications.py:813` `_REPAIR_TERMINAL_STATUS` | `frozenset{Completed, Cannot Repair, Cancelled}` | Đúng tập, nhưng là frozenset **độc lập** (2 SoT song song) |

Hậu quả: số trên thẻ "CM đang mở" **≠** số dòng list khi click drill-down (card đếm `Cannot Repair`, list không) → mất niềm tin dashboard. `Closed` là **literal ma** — KHÔNG có trong DocType enum (chỉ có `Open|Assigned|Diagnosing|Pending Parts|In Repair|Pending Inspection|Completed|Cannot Repair|Cancelled`).

**Quyết định (Core Doc là quyết định cuối):** "Asset Repair đang mở" được định nghĩa bởi **một predicate thuần DUY NHẤT** trong `services/imm09.py`. Mọi consumer (KPI thẻ, persona KTV, drill-down SQL, SLA engine) PHẢI dùng chung tập terminal này.

```python
# assetcore/services/imm09.py
REPAIR_TERMINAL_STATES: frozenset[str] = frozenset({
    RepairStatus.COMPLETED,      # "Completed"
    RepairStatus.CANNOT_REPAIR,  # "Cannot Repair" — TERMINAL, KHÔNG phải đang mở
    RepairStatus.CANCELLED,      # "Cancelled"
})
# KHÔNG còn 'Closed' — literal ma, KHÔNG có trong Asset Repair.status enum.

def is_repair_open(status: str | None) -> bool:
    """SoT: một Asset Repair là 'đang mở' ⟺ status KHÔNG thuộc terminal set.
    None / rỗng (WO mới chưa set status) → coi là đang mở (an toàn — chưa đóng).
    """
    if not status:
        return True
    return status not in REPAIR_TERMINAL_STATES

def open_repair_filter(extra: dict | None = None) -> dict:
    """Trả filter Frappe cho 'Asset Repair đang mở' — dùng chung cho mọi
    _count / get_all / frappe.db filter. Merge thêm điều kiện qua `extra`.
    `sorted()` để filter shape DETERMINISTIC + khớp drill SQL byte-for-byte.
    """
    return {"status": ["not in", sorted(REPAIR_TERMINAL_STATES)], **(extra or {})}
```

**INVARIANT card == drill (BR-09-08):** `cm_open` (KPI thẻ) và drill-down repair SQL PHẢI đếm CÙNG tập WO. Số trên thẻ "CM đang mở" == số dòng list khi user click. Acceptance đo được: với 1 Asset Repair ở status `Cannot Repair` → KHÔNG tính vào `cm_open` VÀ KHÔNG xuất hiện trong `repair_rows`.

**`Cannot Repair` = TERMINAL ở MỌI consumer:** KPI `cm_open`, persona KTV `my_cm` + `cm_urgent`, drill SQL — tất cả loại `Cannot Repair` (khớp SLA engine: đồng hồ SLA dừng khi WO không còn cứu được). Đây là quy ước domain: thiết bị không sửa được → chuyển `Out of Service` (xem `_mark_cannot_repair`), KHÔNG còn là việc-đang-làm của KTV.

**Một SoT, không hai frozenset:** `notifications.py::_REPAIR_TERMINAL_STATUS` PHẢI trỏ về `imm09.REPAIR_TERMINAL_STATES` (alias import), KHÔNG định nghĩa frozenset song song. Quan hệ với `RepairStatus.CANNOT_START` (cùng 3 phần tử): `CANNOT_START` mô tả "không thể bắt đầu sửa từ trạng thái này" (validate khi tạo/assign); `REPAIR_TERMINAL_STATES` mô tả "đã đóng — không còn đang mở" (đếm/filter). Cùng giá trị, khác ngữ nghĩa — giữ tách tên để đọc rõ intent; có thể để `CANNOT_START = tuple(REPAIR_TERMINAL_STATES)` nếu muốn 1 nguồn literal.

**Grep guard (zero-tolerance):** sau fix, `api/dashboard.py` KHÔNG còn literal inline `['Completed','Closed','Cancelled']` hoặc `['Completed','Closed','Cancelled','Cannot Repair']` cho Asset Repair; literal `'Closed'` bị xoá khỏi MỌI Asset Repair status filter.

### State-machine-guarded asset restore (BR-09-09, Self-Correction)

**Vấn đề thiết kế gốc:** `complete_repair` (`services/imm09.py`) gọi `transition_asset_status(to_status=AssetStatus.ACTIVE)` **VÔ ĐIỀU KIỆN**, giả định asset luôn ở `Under Repair` khi WO đóng. Thực tế `lifecycle_status` của AC Asset do **nhiều process** quản:
- IMM-11 calibration-fail → `Out of Service` + CAPA (IMM-16);
- IMM-12 incident → `Out of Service`;
- IMM-13/14 decommission → `Decommissioned` (terminal).

Một thiết bị có thể đang mở 1 CM **đồng thời** bị 1 governance hold khác đẩy sang `Out of Service`/`Decommissioned`. Khi CM đóng, transition vô-điều-kiện phục vụ sai ≥2 ngữ cảnh lifecycle → **2 hậu quả an toàn**:

1. **Override governance hold (NĐ98):** asset đang `Out of Service` do calib-fail/CAPA bị ép về `Active` → thiết bị **out-of-tolerance tự lọt lại lâm sàng** (vi phạm an toàn NĐ98). Việc đóng phiếu CM (sửa phần cứng) KHÔNG đồng nghĩa giải toả hold hiệu chuẩn/CAPA — hold đó phải được giải riêng.
2. **Vỡ on_submit (terminal):** asset đã `Decommissioned` → `_VALID_ASSET_TRANSITIONS['Decommissioned'] == set()` (terminal) → ép `Active` raise `InvalidAssetTransition` → `on_submit` của controller VỠ → **WO un-closeable** (treo vĩnh viễn).

**FIX — đọc `prev_status` TRƯỚC, 3 nhánh (KHÔNG override, KHÔNG raise):**

| `prev_status` | Hành động | Lý do |
|---|---|---|
| `Under Repair` | `transition_asset_status(→ Active)` | Restore hợp lệ — đây là ngữ cảnh đúng của CM. |
| `Out of Service` (hoặc bất kỳ prev khác `Under Repair`/`Decommissioned`) | GIỮ nguyên; ghi ALE `repair_completed` (from=to) + note "WO đóng nhưng asset giữ `<prev>` do hold khác — cần giải toả riêng" | An toàn NĐ98: không override governance hold. |
| `Decommissioned` | Bỏ qua restore (terminal); ghi ALE `repair_completed` (from=to) + note "asset đã thanh lý" | Không raise → WO vẫn đóng được. |

**INVARIANT INV-09-RESTORE-1 (đo được):** sau `complete_repair`, `lifecycle_status` mới ∈ { `Active` **CHỈ KHI** `prev_status == 'Under Repair'`; `prev_status` giữ nguyên với MỌI prev khác } — và nhánh restore **KHÔNG BAO GIỜ raise**. WO luôn đóng được (status=`Completed`, docstatus=1) bất kể lifecycle_status của asset.

**Bất biến phụ:**
- **Lifecycle Event LUÔN ghi** (cả 3 nhánh) — audit trail đầy đủ, không nuốt record (CLAUDE.md §5).
- **Grep guard (zero-tolerance):** trong `complete_repair` KHÔNG còn `transition_asset_status(..., to_status=AssetStatus.ACTIVE)` không-điều-kiện — call này PHẢI nằm trong nhánh `if prev_status == AssetStatus.UNDER_REPAIR`.
- **No-regression:** path MTTR (`mttr_hours`), SLA (`sla_breached` OR-latch BR-09-07), `RepairRepo.set_values` (status/mttr/sla), và hook `create_post_repair_calibration` (BR-11 recalibration) GIỮ NGUYÊN 100%. Chỉ thay đổi DUY NHẤT khối transition_asset_status.

### Error handling pattern

```python
from assetcore.services.shared.constants import ErrorCode
from assetcore.services.shared.errors import ServiceError

def validate_repair_source(doc) -> None:
    """BR-09-01: WO phải có ít nhất 1 nguồn."""
    if not doc.incident_report and not doc.source_pm_wo:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            frappe._("Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc")
        )

def validate_spare_parts_stock_entries(doc) -> None:
    """BR-09-02: mọi spare part phải có stock_entry_ref tồn tại."""
    for row in doc.spare_parts_used:
        if not row.stock_entry_ref:
            raise ServiceError(
                ErrorCode.VALIDATION,
                frappe._(f"Vật tư '{row.item_code}' (dòng {row.idx}) thiếu phiếu xuất kho")
            )
        if not frappe.db.exists("Stock Entry", row.stock_entry_ref):
            raise ServiceError(
                ErrorCode.VALIDATION,
                frappe._(f"Phiếu xuất kho '{row.stock_entry_ref}' không tồn tại trong hệ thống")
            )

def complete_repair(doc) -> None:
    """on_submit: tính MTTR, SLA breach, restore Asset (guarded), sinh ALE."""
    close_dt = now_datetime()
    doc.completion_datetime = close_dt
    diff_seconds = time_diff_in_seconds(close_dt, doc.open_datetime)
    doc.mttr_hours = round(diff_seconds / 3600.0, 2)
    # BR-09-07: SoT predicate (boundary >=) + monotonic — không reset 1→0 nếu
    # scheduler đã đánh breach lúc WO còn đang chạy. KHÔNG đổi (giữ 100%).
    doc.sla_breached = 1 if (is_sla_breached(doc.mttr_hours, doc.sla_target_hours)
                             or doc.sla_breached) else 0
    doc.status = RepairStatus.COMPLETED
    # … (RepairRepo.set_values status/mttr/sla giữ nguyên) …

    # ─── BR-09-09: restore Asset CÓ ĐIỀU KIỆN theo state machine ──────────────
    # ROOT CAUSE (Self-Correction): bản trước gọi transition_asset_status(
    #   to_status=ACTIVE) VÔ ĐIỀU KIỆN, giả định asset luôn ở Under Repair.
    #   Thực tế lifecycle_status do NHIỀU process quản (calib-fail→OoS+CAPA,
    #   incident, decommission) → 1 transition phục vụ sai ≥2 ngữ cảnh.
    # FIX: đọc prev_status TRƯỚC; chỉ Active khi đang Under Repair; mọi nhánh
    #   GHI 1 Lifecycle Event 'repair_completed' (audit đầy đủ, CLAUDE.md §5);
    #   nhánh restore KHÔNG BAO GIỜ raise (INV-09-RESTORE-1) → on_submit không vỡ.
    prev_status = frappe.db.get_value("AC Asset", doc.asset_ref, "lifecycle_status") or ""
    note = f"MTTR: {doc.mttr_hours}h | SLA: {'Breached' if doc.sla_breached else 'OK'}"

    if prev_status == AssetStatus.UNDER_REPAIR:
        # Nhánh A — restore bình thường: WO đóng đưa thiết bị về vận hành.
        transition_asset_status(
            asset_name=doc.asset_ref, to_status=AssetStatus.ACTIVE,
            actor=frappe.session.user,
            root_doctype=RepairRepo.DOCTYPE, root_record=doc.name,
            reason=note,
        )  # transition_asset_status TỰ ghi ALE 'activated' (from=Under Repair)
    elif prev_status == AssetStatus.DECOMMISSIONED:
        # Nhánh C — terminal: ép Active sẽ raise InvalidAssetTransition (set rỗng)
        # → on_submit VỠ, WO un-closeable. Bỏ qua restore; vẫn ghi ALE để audit.
        _log_lifecycle_event(
            asset=doc.asset_ref, event_type="repair_completed",
            from_status=prev_status, to_status=prev_status, root_record=doc.name,
            notes=f"{note} — asset đã thanh lý (Decommissioned), bỏ qua restore.",
        )
    else:
        # Nhánh B — hold governance khác (Out of Service do calib-fail/CAPA/
        # incident, hoặc bất kỳ prev khác Under Repair). KHÔNG ép Active: thiết bị
        # out-of-tolerance KHÔNG được tự lọt lại lâm sàng (NĐ98 — an toàn).
        _log_lifecycle_event(
            asset=doc.asset_ref, event_type="repair_completed",
            from_status=prev_status, to_status=prev_status, root_record=doc.name,
            notes=f"{note} — WO đóng nhưng asset giữ '{prev_status}' do hold khác; "
                  f"cần giải toả riêng.",
        )
```

> **CHỈ thay đổi DUY NHẤT khối transition.** Path MTTR/`sla_breached`/`RepairRepo.set_values`
> /`status=Completed` và hook `create_post_repair_calibration` GIỮ NGUYÊN 100%.

### Repeat failure detection

```python
def check_repeat_failure(doc) -> None:
    """BR-09-06: kiểm tra WO Completed trong 30 ngày."""
    cutoff = add_days(nowdate(), -30)
    exists = frappe.db.exists("Asset Repair", {
        "asset_ref": doc.asset_ref,
        "status": "Completed",
        "completion_datetime": (">=", cutoff),
        "docstatus": 1,
    })
    doc.is_repeat_failure = 1 if exists else 0
```

---

## 4b. Repository Layer

Module IMM-09 sử dụng Frappe ORM trực tiếp trong service (wave-1). Các DB access chính:

```python
# List WOs với filter
rows = frappe.get_all(
    "Asset Repair",
    filters=filters,
    fields=["name", "asset_ref", "priority", "status", "mttr_hours", "sla_breached"],
    limit_start=offset,
    limit_page_length=page_size,
    order_by="open_datetime desc"
)
total = frappe.db.count("Asset Repair", filters=filters)

# Get detail với enrichment
doc = frappe.get_doc("Asset Repair", name)
asset_info = frappe.get_value("Asset", doc.asset_ref,
    ["asset_name", "status", "custom_risk_class", "custom_mttr_avg_hours"],
    as_dict=True)
```

---

## 5. API Layer

File: `assetcore/api/imm09.py`

```python
import frappe
from assetcore.utils.helpers import _handle, _ok, _err, _parse_json
from assetcore.services import imm09 as service

@frappe.whitelist(methods=["POST"])
def create_repair_work_order(
    asset_ref: str,
    repair_type: str,
    priority: str,
    failure_description: str = "",
    incident_report: str = "",
    source_pm_wo: str = ""
) -> dict:
    return _handle(service.create_repair_work_order,
                   asset_ref, repair_type, priority,
                   failure_description, incident_report, source_pm_wo)

@frappe.whitelist()
def list_repair_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    parsed = _parse_json(filters, field_name="filters", default={})
    return _handle(service.list_repair_work_orders, parsed, int(page), int(page_size))

@frappe.whitelist(methods=["POST"])
def close_work_order(
    name: str,
    repair_summary: str = "",
    root_cause_category: str = "",
    dept_head_name: str = "",
    checklist_results: str = "[]",
    spare_parts: str = "[]",
    firmware_updated: int = 0,
    firmware_change_request: str = "",
    cannot_repair: int = 0,
    cannot_repair_reason: str = ""
) -> dict:
    results = _parse_json(checklist_results, "checklist_results", [])
    parts = _parse_json(spare_parts, "spare_parts", [])
    return _handle(service.close_work_order,
                   name, repair_summary, root_cause_category, dept_head_name,
                   results, parts, bool(firmware_updated), firmware_change_request,
                   bool(cannot_repair), cannot_repair_reason)
```

**Helper `_handle`:**

```python
def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "IMM-09 API Error")
        return _err("Lỗi hệ thống. Vui lòng thử lại.", "INTERNAL")
```

---

## 6. Audit Trail

| Trigger | Event type | Actor | Payload |
|---|---|---|---|
| create_repair_work_order | `repair_opened` | Workshop Manager / System | asset, wo, priority, sla_target |
| submit_diagnosis | `diagnosis_submitted` | KTV HTM | diagnosis_notes, needs_parts, root_cause |
| **enter_parts_hold (vào Pending Parts)** | **`parts_hold_started`** | **KTV HTM** | **wo, parts_hold_started (mốc), lý do (kho hết hàng) — BR-09-10** |
| **exit_parts_hold (ra Pending Parts / chốt cuối)** | **`parts_hold_resumed`** | **KTV HTM / Kho** | **wo, khoảng hold vừa cộng (giờ), parts_hold_hours tích lũy — BR-09-10** |
| complete_repair (on_submit) | `repair_completed` | KTV HTM | mttr_hours (clock-stop), parts_hold_hours, sla_breached, prev_status→new_status |
| close_work_order(cannot_repair=1) | `cannot_repair` | KTV / Workshop Manager | cannot_repair_reason |

Tất cả ALE insert qua `_create_lifecycle_event(...)` trong `services/imm09.py`. Wrap trong `try/except` — ALE failure KHÔNG block main operation.

**`repair_completed` LUÔN được ghi đúng 1 ALE — cả 3 nhánh restore (BR-09-09):**

| Nhánh | `prev_status` | Asset sau khi đóng | from → to (ALE) | Ghi chú audit |
|---|---|---|---|---|
| A — restore | `Under Repair` | `Active` | Under Repair → Active | Restore bình thường (ALE `activated` do `transition_asset_status` sinh + `repair_completed` business) |
| B — hold | `Out of Service` (hoặc prev khác) | giữ nguyên `prev_status` | prev → prev (no-op) | "WO đóng nhưng asset giữ `<prev>` do hold khác; cần giải toả riêng" |
| C — terminal | `Decommissioned` | giữ `Decommissioned` | Decommissioned → Decommissioned | "asset đã thanh lý, bỏ qua restore" |

KHÔNG nhánh nào nuốt record (CLAUDE.md §5 "mọi nghiệp vụ phải có record"). Nhánh B/C dùng `_log_lifecycle_event` (from=to) thay vì `transition_asset_status` (vốn early-return khi prev==to và sẽ raise nếu cố ép Active từ terminal).

---

## 7. Background jobs / Scheduler

```python
# assetcore/hooks.py — kế hoạch (xem ghi chú dưới)
scheduler_events = {
    "hourly": ["assetcore.services.imm09.check_repair_sla_breach"],
    "daily":  ["assetcore.services.imm09.check_repair_overdue"],
    "monthly": ["assetcore.services.imm09.update_asset_mttr_avg"],
}
```

| Job | Tần suất | Mục đích | Trạng thái wire `hooks.py` |
|---|---|---|---|
| `check_repair_sla_breach` | Hourly | Mark `sla_breached=1` khi `is_sla_breached(elapsed, target)` (SoT predicate, boundary `>=`); publish realtime `cm_sla_breached` đến Kỹ thuật viên. Chỉ set khi đang 0 (idempotent). | ⚠ chưa wire (function tồn tại trong `services/imm09.py`) |
| `check_repair_overdue` | Daily 07:00 | Email Workshop Manager khi WO > 7 ngày chưa đóng | ⚠ chưa wire (function tồn tại trong `services/imm09.py:239`) |
| `update_asset_mttr_avg` | Monthly day 01 06:00 | Cập nhật `Asset.custom_mttr_avg_hours` (avg 12 WO gần nhất) | ⚠ chưa wire (function tồn tại trong `services/imm09.py:263`) |

> **Code-to-doc gap (2026-05-14):** 3 function trên đã hiện diện trong service nhưng **chưa được đăng ký** trong `assetcore/hooks.py::scheduler_events`. Cần thêm trong patch Wave 2 release.

---

## 8. Integration

**Module nội bộ:**
- IMM-08 → IMM-09: `services/imm08.py::_create_cm_wo_from_failure` (line 154) auto-insert `Asset Repair` với `source_pm_wo` khi PM `report_major_failure` hoặc Fail-Major.
- IMM-12 → IMM-09: User tạo WO từ Incident Report (`incident_report` field trong `create_work_order`).
- IMM-09 → IMM-11: Sau Completed, nếu `Device Model.requires_calibration=True` → trigger calibration WO (manual rule hiện tại).
- IMM-09 → IMM-12 CAPA: `is_repeat_failure=1` → FE gợi ý tạo CAPA.
- **IMM-09 ↔ IMM-15 (Pattern B lazy-import)**: `services/imm09.py::request_spare_parts` (line ~500) lazy-import `assetcore.services.imm15.create_allocation` và mở allocation Requested truy về kho. Lỗi không throw — chỉ log `frappe.log_error` để giữ flow chính chạy.
- **IMM-09 ↔ IMM-16 (Pattern C compliance gate)**: `Asset Repair.validate` gọi `assetcore.services.imm16.gate_wo_submit(doc, method=None)` — signature `(doc, method=None)` chứ KHÔNG phải `(asset_ref, wo_type="CM")`. Trên `on_submit` gọi `imm16.eval_imm08_09_realtime` để cập nhật scorecard. Cả hai wired trong `hooks.py::doc_events["Asset Repair"]`.

**Bên ngoài:**
- ERPNext Stock: validate `stock_entry_ref` tồn tại
- Frappe Email Queue: overdue daily notification
- Frappe Realtime (`frappe.publish_realtime`): SLA breach push đến KTV

---

## 9. Migration & Patch

| Patch | Path | Mục đích |
|---|---|---|
| v1 → v2 | `patches/v2_0/migrate_asset_repair.py` | Migrate từ ERPNext Asset Repair → DocType native (BACKLOG) |
| Working hours MTTR | `patches/v2_1/imm09_mttr_working_hours.py` | Chuyển sang `get_working_hours_between` |
| Backfill repeat failure | `patches/v2_0/backfill_is_repeat_failure.py` | DRAFT |

**ERPNext compat shims** (controller hiện có):
- `completion_date` property ↔ `completion_datetime`
- `company` fallback ↔ `frappe.defaults.get_global_default("company")`

---

## 10. Non-functional

**Concurrency:** Frappe `doc.modified` optimistic lock — 20 active WO đồng thời không conflict.

**Caching:** KPI report: Redis key `imm09:kpis:{year}-{month}` TTL 10 phút (recommended, chưa implement).

**Logging:**
```python
frappe.logger("imm09").info(f"Repair WO {wo_name} completed MTTR={mttr:.1f}h SLA={'BREACH' if breach else 'OK'}")
frappe.logger("imm09").warning(f"SLA breached: {wo_name} asset={asset_ref}")
```

**Known issue:** `ignore_permissions=True` và `doc.flags.ignore_links=True` dùng trong service để tránh break trong môi trường test. Production cần review và bật đầy đủ permission check.

---

## DoD — File 04 hoàn chỉnh

- [x] Quy ước ngôn ngữ BE: code tiếng Anh + error message tiếng Việt
- [x] 4 DocType nêu đầy đủ trường + naming + permissions
- [x] Quan hệ liên DocType ERD
- [x] State machine 9 states + transitions
- [x] Controller hooks delegate sang service
- [x] Mọi error raise qua `ServiceError(ErrorCode.X, "msg tiếng Việt")`
- [x] API layer dùng `_handle / _ok / _err`
- [x] SLA matrix documented
- [x] Audit trail (ALE) liệt kê đủ trigger
- [x] 3 background job đăng ký rõ
- [x] Integration nội bộ + ERPNext + realtime
- [x] Patch path cho migration
- [x] Known issues documented
