# 04 — Thiết kế Backend — IMM-08 Bảo trì định kỳ (PM)

| Mục | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | [02 Analysis & Design](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) |
| Cập nhật | 2026-05-27 |

---

## 1. Tổng quan kiến trúc

IMM-08 bám kiến trúc **3-tier strict**: API (`api/imm08.py`) → Service (`services/imm08.py`) → Repository (`repositories/pm_repo.py`). Controller `pm_work_order.py` / `pm_schedule.py` chỉ delegate sang service (`validate_work_order`, `handle_work_order_submit`). API layer là thin wrapper dùng `_handle / _ok / _err`. Scheduler `generate_pm_work_orders_from_schedule` chạy daily.

```
Browser/Client
    │ HTTP (token/sid)
    ▼
api/imm08.py            ← 24 endpoints, thin wrapper (_handle/_ok/_err)
    │
    ▼
services/imm08.py       ← business logic (PMStatus / PMScheduleStatus enums)
    │
    ▼
repositories/pm_repo.py ← 4 Repo (Schedule / WO / Template / TaskLog)
    │
    ▼
Frappe ORM + MariaDB    ← 8 DocTypes (xem §2)
```

> **Quy ước ngôn ngữ:** Code/fieldname tiếng Anh · Field label tiếng Việt · Error message tiếng Việt qua `frappe._()` · DTO mirror FE TypeScript types

---

## 2. Domain Model — DocType

### 2.1 PM Schedule

- **Naming:** `format:PMS-{asset_ref}-{pm_type}` → unique per (asset, pm_type)
- **Submittable:** No — master record
- **Track changes:** Yes

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `asset_ref` | Link → Asset | ✓ | — | search_index |
| `pm_type` | Select | ✓ | — | Quarterly/Semi-Annual/Annual/Ad-hoc |
| `status` | Select | — | Active | Active/Paused/Suspended |
| `pm_interval_days` | Int | ✓ | — | > 0 |
| `checklist_template` | Link → PM Checklist Template | ✓ | — | BR-08-01 |
| `alert_days_before` | Int | — | 7 | ≥ 0 |
| `responsible_technician` | Link → User | — | — | default KTV khi tạo WO |
| `last_pm_date` | Date | — | — | controller advance sau on_submit |
| `next_due_date` | Date | — | — | list_view, controller compute |
| `created_from_commissioning` | Link → Asset Commissioning | — | — | read_only, IMM-04 fill |

**Permissions sơ bộ:** PM Manager / AssetCore System User / System Manager = full · PM User / Corrective Manager / AssetCore Auditor = R

### 2.2 PM Checklist Template

- **Naming:** `format:PMCT-{asset_category}-{pm_type}`
- **Submittable:** No

| Trường | Type | Required | Notes |
|---|---|---|---|
| `template_name` | Data | ✓ | list_view |
| `asset_category` | Link → Asset Category | ✓ | search_index |
| `pm_type` | Select | ✓ | same options |
| `version` | Data | — | default "1.0" |
| `checklist_items` | Table → PM Checklist Item | ✓ | child table |

### 2.3 PM Work Order

- **Naming:** `PM-WO-.YYYY.-.#####`
- **Submittable:** Yes (docstatus 0→1 khi Completed)
- **Track changes:** Yes

| Trường | Type | Required | Notes |
|---|---|---|---|
| `asset_ref` | Link → Asset | ✓ | search_index |
| `pm_schedule` | Link → PM Schedule | ✓ | — |
| `pm_type` | Data | — | read_only, copy từ Schedule |
| `wo_type` | Select | — | Preventive/Corrective, default Preventive |
| `status` | Select | ✓ | 7 states, default Open |
| `is_late` | Check | — | read_only, controller compute |
| `due_date` | Date | ✓ | — |
| `completion_date` | Date | — | read_only, auto on_submit |
| `assigned_to` | Link → User | — | KTV |
| `overall_result` | Select | — | Pass/Pass with Minor Issues/Fail |
| `checklist_results` | Table → PM Checklist Result | — | child |
| `source_pm_wo` | Link → PM Work Order | conditional | `mandatory_depends_on: wo_type==='Corrective'` BR-08-02 |
| `attachments` | Attach Multiple | — | bắt buộc khi Class III BR-08-06 |

**Permissions:**

| Role | R | W | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| PM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| AssetCore System User | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PM User | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Corrective Manager | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| AssetCore Auditor | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

### 2.4 PM Task Log

- **Naming:** autoname hash
- **`in_create: 1`** — chặn update sau insert (BR-08-10)
- **Permissions:** all roles Read · PM Manager / AssetCore System User có Create · **KHÔNG có Write / Delete**

| Trường | Type | Required | Notes |
|---|---|---|---|
| `asset_ref` | Link → Asset | ✓ | search_index |
| `pm_work_order` | Link → PM Work Order | ✓ | — |
| `completion_date` | Date | ✓ | — |
| `is_late` | Check | — | mirror từ WO |
| `days_late` | Int | — | `date_diff(completion, due)` |
| `next_pm_date` | Date | — | `completion + interval` |
| `summary` | Text | — | mirror `technician_notes` |

---

## 3. Workflow (State Machine)

File fixture: `assetcore/workflow/imm_08_pm_work_order_workflow.json` (optional — hiện enforce qua controller + scheduler)

**States:**

<!-- allow_edit role đồng bộ source-of-truth `assetcore/assetcore/workflow/imm_08_pm_workflow.json` (reconcile vòng 8, 2026-05-29). -->

| State | Style | docstatus | allow_edit role |
|---|---|---|---|
| Open | Warning | 0 | PM User |
| In Progress | Primary | 0 | PM User |
| Pending–Device Busy | Warning | 0 | PM User |
| Overdue | Danger | 0 | System Manager |
| Completed | Success | 1 | System Manager |
| Halted–Major Failure | Danger | 0 | System Manager |
| Cancelled | Secondary | 2 | System Manager |

**Transitions:**

| From | To | Action label | Allowed role | Trigger |
|---|---|---|---|---|
| (insert) | Open | — | Scheduler | `tasks.generate_pm_work_orders` |
| Open / Overdue | In Progress | Phân công KTV | PM Manager | `assign_technician` |
| In Progress | Completed | Hoàn thành PM | PM User | `submit_pm_result` → `wo.submit()` |
| In Progress | Halted–Major Failure | Báo lỗi Major | PM User | `report_major_failure` |
| In Progress / Overdue | Pending–Device Busy | Hoãn lịch | PM Manager | `reschedule_pm` |
| Any (Open/In Progress) | Cancelled | Hủy | PM Manager | `on_cancel` |

**SSoT trạng-thái-kế-hợp-lệ — `_PM_VALID_TRANSITIONS` (server-driven CTA):**

`services/imm08.py:_PM_VALID_TRANSITIONS: dict[str, list[str]]` = map tập-trung GROUNDED chính xác `assetcore/assetcore/workflow/imm_08_pm_workflow.json` (7 state / 13 transition). `get_work_order(name)` emit `allowed_transitions = _PM_VALID_TRANSITIONS.get(wo.status, [])` vào detail dict → màn detail (web + mobile) render nút workflow **theo server**.

| Status hiện tại | `allowed_transitions[]` |
|---|---|
| `Open` | `In Progress`, `Overdue`, `Cancelled` |
| `Overdue` | `In Progress`, `Cancelled` |
| `In Progress` | `Completed`, `Halted–Major Failure`, `Pending–Device Busy`, `Cancelled` |
| `Pending–Device Busy` | `In Progress`, `Cancelled` |
| `Halted–Major Failure` | `In Progress`, `Cancelled` |
| `Completed` (terminal, docstatus=1) | `[]` |
| `Cancelled` (terminal) | `[]` |

> **ADR-IMM08-CTA — Server-driven CTA cho màn PM-detail (2026-06-16).**
> - **Context:** Trước round này CHỈ `IncidentDetail` (IMM-12, R3) emit `allowed_transitions[]`; `PmWorkOrderDetail`/Repair/Calibration KHÔNG → màn detail BUỘC hardcode `status → button` phía client (anti-pattern lifecycle/RBAC **dead-gate**, memory `factory_rounds_1_25`): client tự suy CTA, dễ lệch khi workflow đổi.
> - **Decision:** Bồi map tập-trung `_PM_VALID_TRANSITIONS` (1 SSoT) + emit `allowed_transitions[]` ở `get_work_order` — MIRROR pattern `imm12._VALID_TRANSITIONS` + `get_incident_detail` (R3). Schema mobile `array<string>` **KHÔNG enum-bound cứng** (né drift khi workflow đổi); codomain-check ở guard **phía service** (KHÔNG schema-enum).
> - **Consequences:** Client (web + codegen mobile) render CTA theo server → đổi workflow chỉ sửa 1 nơi (map + workflow JSON, guard SSoT-divergence chặn lệch). KHÔNG đụng workflow-engine / submit / start logic; handler signature `getPmWorkOrder` 0 đổi; KHÔNG path mới.
> - **Alternatives:** (a) giữ client-side state-gate — REJECTED (dead-gate, drift). (b) enum-bound `allowed_transitions.items` ở schema — REJECTED (schema phải sửa mỗi lần workflow đổi → drift-risk; codomain đã check ở guard service). (c) trả full transition-object {action,role} — DEFERRED (MVP chỉ cần next-state cho CTA; role-gate đã ở dispatcher/cap).

**Controller hooks:**

```python
# assetcore/assetcore/doctype/pm_work_order/pm_work_order.py
class PMWorkOrder(Document):
    def validate(self):
        from assetcore.services.imm08 import validate_work_order
        validate_work_order(self)   # gộp BR-08-02 / 06 / 08

    def on_submit(self):
        from assetcore.services.imm08 import handle_work_order_submit
        handle_work_order_submit(self)
```

---

## 4. Service Layer

File: `assetcore/services/imm08.py`

### Public functions

| Function | Input | Output | Side effect |
|---|---|---|---|
| `validate_work_order(doc)` | PM Work Order doc | None | raise ServiceError (BR-08-02/06/08 gộp) |
| `compute_next_pm_date(completion_date, interval=None)` | str/date + int? | `str` | None — **SoT DUY NHẤT** cho ngày PM kế tiếp (BR-08-03). `= add_days(getdate(completion_date), effective_interval)`; `effective_interval = interval nếu interval and interval > 0, else PM_DEFAULT_INTERVAL_DAYS (=90)`. Anchor LUÔN là `completion_date`, KHÔNG bao giờ `nowdate()`. Mọi write-site PHẢI gọi hàm này — CẤM inline lại `add_days(...)`. |
| `handle_work_order_submit(doc)` | PM Work Order doc | None | set completion, advance PM Schedule, sync Asset, ghi PM Task Log, tạo CM nếu Fail-Major. `next_pm_date` (Asset + PM Task Log) = `compute_next_pm_date(doc.completion_date, sched_interval)` |
| `submit_result(name, ...)` | str + kwargs | dict | đóng WO, chuyển status `Completed`. Field trả về `next_pm_date` = `compute_next_pm_date(wo.completion_date, sched_interval)` — **byte-for-byte == PM Schedule.next_due_date đã persist == AC Asset.next_pm_date == PM Task Log.next_pm_date** |
| `report_major_failure(pm_wo_name, *, failure_description)` | str + str | dict | set `Halted–Major Failure`, gọi `_create_cm_wo_from_failure` |
| `reschedule(name, *, new_date, reason)` | str + str + str | dict | chuyển `Pending–Device Busy`, lưu reason |
| `generate_pm_work_orders_from_schedule()` | — | dict | scheduler daily: tạo WO mới + đánh `Overdue` |
| `backfill_pm_schedules_for_due_assets()` | — | dict | scheduler daily: tạo PM Schedule cho Asset đến hạn chưa có lịch |
| `create_pm_schedule_from_commissioning(doc)` | Asset Commissioning doc | str / None | tạo PM Schedule khi commissioning submit |
| `create_pm_schedule_from_asset(asset_doc, method)` | AC Asset doc | str / None | hook AC Asset.after_insert → tạo PM Schedule nếu `is_pm_required=1` |
| `apply_template_to_category_assets(template_name)` | str | dict `{template, asset_category, created, skipped, errors}` | bulk-tạo PM Schedule cho mọi asset cùng danh mục; bỏ qua asset đã có lịch cùng `pm_type` |
| `get_dashboard_stats(*, year, month)` | int, int | dict | BR-08-13 — `kpis` tách 2 khối phạm vi: THÁNG (`total_scheduled`, `completed_on_time`, `overdue_in_month`, `pending_in_month`, `compliance_rate_pct` null-safe, `avg_days_late`) + GLOBAL (`overdue`=`count_overdue_pm()`, RC-10). Population THÁNG = WO **không-Cancelled** (`scheduled`, INV-PM-KPI-6). INV-PM-KPI-1..3,6 (§4.1.4) |
| `get_calendar(*, year, month, ...)` | int, int, ... | dict | — |
| `is_pm_overdue(status, due_date, ref_date=None)` | str, date, date? | `bool` | None — pure SoT predicate (BR-08-11), `due_date < today` strict + status ∈ overdue-source |
| `due_soon_filter(window_end, ref_date=None)` | date, date? | `dict` | None — pure SoT window filter builder (BR-08-12), `{due_date: [between, [ref_date, window_end]], status: [not in, [Completed, Cancelled]]}` |
| `count_overdue_pm(user=None)` | str? | `int` | None — counter dùng chung KPI/dashboard (BR-08-11), đếm `status == Overdue` |

### Validators

```python
def _validate_checklist_complete(doc) -> None:
    """BR-08-08: mọi checklist item phải có result."""
    for row in doc.checklist_results:
        if not row.result:
            raise ServiceError(
                ErrorCode.VALIDATION,
                frappe._(f"Tất cả mục checklist phải có kết quả trước khi Submit (BR-08-08). Mục '{row.description}' chưa điền.")
            )

def _validate_photo_for_high_risk(doc) -> None:
    """BR-08-06: Asset Class III phải có ảnh."""
    risk = frappe.db.get_value("Asset", doc.asset_ref, "custom_risk_class")
    if risk in ("III", "C", "D") and not doc.attachments:
        raise ServiceError(
            ErrorCode.VALIDATION,
            frappe._(f"Thiết bị nguy cơ cao (Class {risk}) bắt buộc upload ảnh trước/sau PM (BR-08-06).")
        )
```

### Error handling pattern

```python
from assetcore.services.shared.constants import ErrorCode
from assetcore.services.shared.errors import ServiceError

def handle_work_order_submit(doc) -> None:
    """Trigger on_submit: chốt completion, advance PM Schedule, sync Asset,
    ghi PM Task Log, sinh CM nếu Fail-Major."""
    if doc.docstatus != 1:
        raise ServiceError(ErrorCode.BAD_STATE, "PM Work Order chưa được Submit.")
    _set_completion(doc)
    _update_pm_schedule(doc)
    _update_asset_fields(doc)
    _create_pm_task_log(doc)
    _handle_failures(doc)
```

---

## 4.1 SoT — "PM đến hạn (due-soon)" vs "PM quá hạn (overdue)" (BR-08-11 / BR-08-12)

> **Self-Correction (vòng 23).** Trước fix có **2 định nghĩa cửa-sổ due-soon phân kỳ**:
> - KPI `pm_due_next7` (`api/dashboard.py:87`) đếm `due_date BETWEEN [today, today+7]` AND status NOT IN [Completed, Cancelled] — cửa sổ **có cận dưới** `today`.
> - Drill `/pm/work-orders?due_before=today+7` → `services/imm08.py::_normalize_filters` dịch thành `due_date <= today+7` — **KHÔNG có cận dưới** → mọi WO quá hạn (`due_date < today`, chưa Completed/Cancelled) lọt vào danh sách drill nhưng KHÔNG được KPI đếm.
>
> Hệ quả: số trên thẻ "PM đến hạn" ≠ số dòng khi click drill (drill là superset gồm cả overdue). Test cũ `test_d_be_18`/dashboard chỉ assert *route* của drill, không assert *convergence* — hợp-thức-hoá divergence.
>
> **Quyết định:** hợp nhất về **1 predicate cửa-sổ due-soon** dùng CHUNG cho KPI count + drill filter. `_normalize_filters(due_before=X)` PHẢI sinh `due_date BETWEEN [today, X]` (cận dưới = today, KHÔNG còn `<= X`). WO quá hạn KHÔNG còn thuộc due-soon — nó thuộc thẻ "PM quá hạn" (`pm_overdue`, status == Overdue) → hai tập **disjoint** (giống mô hình IMM-11 overdue vs due_soon, round 9).

### 4.1.1 Hằng + helper SoT (pure, không I/O)

```python
# services/imm08.py — module-level constant (1 hằng, KHÔNG hardcode "7" rải rác)
PM_DUE_SOON_WINDOW_DAYS = 7

def due_soon_filter(window_end, ref_date=None) -> dict:
    """SoT (BR-08-12): filter dict cho 'PM đến hạn (due-soon)' — dùng CHUNG bởi
    KPI count (dashboard.pm_due_next7) và drill list (_normalize_filters(due_before)).

    Cửa sổ = [ref_date, window_end] (cả 2 biên inclusive). status NOT IN
    [Completed, Cancelled] (đến hạn = chưa hoàn tất). WO quá hạn (due_date <
    ref_date) NẰM NGOÀI — thuộc tập overdue (BR-08-11, is_pm_overdue), disjoint.

    Args:
        window_end: cận trên cửa sổ (str/date) — KPI truyền today+PM_DUE_SOON_WINDOW_DAYS;
                    drill truyền due_before verbatim từ query.
        ref_date: cận dưới = mốc hôm nay (mặc định nowdate()).

    Returns:
        dict filter: {"due_date": ["between", [ref, window_end]],
                      "status": ["not in", [PMStatus.COMPLETED, PMStatus.CANCELLED]]}
    """
    ref = ref_date or nowdate()
    return {
        "due_date": ["between", [ref, window_end]],
        "status": ["not in", [PMStatus.COMPLETED, PMStatus.CANCELLED]],
    }
```

**Boundary chốt (BR-08-12):**

| `due_date` | Phân loại | Lý do |
|---|---|---|
| `today` | **DUE_SOON** (trong cửa sổ) | inclusive cận dưới |
| `today+7` | **DUE_SOON** (trong cửa sổ) | inclusive cận trên |
| `today+8` | NGOÀI cửa sổ | quá cận trên |
| `today-1` | NGOÀI due-soon → **OVERDUE** (BR-08-11) | `due_date < today` |
| bất kỳ + status ∈ {Completed, Cancelled} | luôn NGOÀI | đã hoàn tất/hủy |

### 4.1.2 Consumer dùng chung (count == drill, INVARIANT)

- **`_normalize_filters(due_before=X)`** PHẢI gọi `due_soon_filter(window_end=X)` thay vì literal `due_date <= X`. Output: `due_date BETWEEN [today, X]` + status NOT IN [Completed, Cancelled]. (cũ: `out["due_date"] = ["<=", due_before]` — XÓA cận-dưới-thiếu này.)
- **`api/dashboard.py` `pm_due_next7`** PHẢI gọi `due_soon_filter(next7)` (import từ `services.imm08`) — KHÔNG inline literal `{"due_date": ["between", [today_str, next7]], "status": [...]}`.
- **Persona block `dashboard.py:589` `pm_week`** (Kỹ thuật viên dashboard) cũng đếm cửa sổ `[today, today+7]` — PHẢI gọi cùng helper `due_soon_filter(add_days(today(), 7), ref_date=today())` (cộng filter `assigned_to=me`). Nếu cố ý giữ riêng phải ghi chú lý do.
- **INVARIANT đo được:** với MỌI dataset, `count(KPI pm_due_7d) == số dòng list khi drill ?due_before=today+7` (byte-for-byte cùng tập). WO quá hạn KHÔNG xuất hiện trong drill due-soon → thuộc thẻ `pm_overdue` (status==Overdue). Hai tập **disjoint** (overdue ∩ due-soon = ∅).
- **Grep guard:** 0 literal inline window cho PM due-soon còn sót ngoài `due_soon_filter`. `api/dashboard.py` không còn `{due_date: [between, [today_str, next7]]}` viết tay cho PM; kiểm cả persona `pm_week`.

### 4.1.3 Quan hệ với overdue SoT (BR-08-11 — đã có sẵn)

`is_pm_overdue(status, due_date, ref_date)` (đã tồn tại) định nghĩa overdue: `due_date < today` (strict) AND status ∈ `OVERDUE_SOURCE_STATES` {Open, In Progress, Pending–Device Busy}. Cron `check_pm_overdue` set `status=Overdue` theo predicate này; `count_overdue_pm()` đếm `status == Overdue`; drill `?overdue=1` (`_normalize_filters(overdue=1)`) trả cùng tập. Due-soon (BR-08-12) và overdue (BR-08-11) **disjoint by construction**: due-soon yêu cầu `due_date >= today`, overdue yêu cầu `due_date < today`.

### 4.1.4 Dashboard KPI — đồng nhất phạm vi tháng vs toàn-hệ-thống (BR-08-13, vòng 10)

> **Self-Correction (vòng 10).** RC-10 (vòng trước) đã đúng khi đổi `kpis.overdue` thành `count_overdue_pm()` **global** để khớp launcher widget + drill `?overdue=1`. NHƯNG sửa đó để lại **mâu thuẫn phạm vi không-đối-soát-được**: `get_dashboard_stats` đặt 1 field **toàn-hệ-thống** (`overdue`) đứng cạnh các field **bó-trong-tháng** (`total_scheduled`, `completed_on_time`, `compliance_rate_pct`) trong CÙNG dict `kpis` → FE render chung 1 strip. Phản ví dụ: tháng không có WO due nào nhưng còn 5 WO Overdue từ tháng trước → strip hiện "Tổng lên lịch: 0" cạnh "Quá hạn: 5" → người xem KHÔNG cách nào đối-soát (5 từ đâu ra khi tổng = 0?). Đồng thời `compliance_rate_pct = 0.0` khi `total==0` gây hiểu nhầm "tuân thủ 0%" trong khi thực ra "không có gì để đo".
>
> **Quyết định:** tách `kpis` thành **2 khối phạm vi** trong cùng payload, mỗi field có phạm vi DUY NHẤT & nhãn rõ ở FE. KHÔNG bỏ `overdue` global (giữ RC-10), THÊM `overdue_in_month` + `pending_in_month` cho khối tháng, và đổi `compliance_rate_pct` thành **null-safe**.

**Hai khối phạm vi (cùng payload `get_dashboard_stats(year, month)`):**

> **Self-Correction (vòng 25 — INV-PM-KPI-6).** Thiết kế gốc định nghĩa `total_scheduled = len(wos)` (MỌI status) và `pending_in_month = total − on_time − overdue_in_month` là **phần dư phủ kín mọi status còn lại** — chủ ý gồm cả `Cancelled-in-window`. Đây là **lỗi thiết kế gốc**: WO `Cancelled` (đã hủy chủ động, KHÔNG còn nghĩa vụ thực hiện) bị (a) tính vào MẪU compliance ⇒ kéo tụt `compliance_rate_pct` giả (vd 1/4=25.0 thay vì 1/3=33.3), và (b) rơi vào `pending_in_month` ⇒ phantom "chưa xong" không bao giờ ai làm. **Khắc phục:** loại `Cancelled` khỏi MẪU (`total_scheduled`) và mọi bucket tháng. Population mới = **WO không-Cancelled trong tháng** (`scheduled`).

**Population CHỐT (vòng 25):** `scheduled = [w for w in wos if w["status"] != PMStatus.CANCELLED]`. `total_scheduled = len(scheduled)`. Mọi field khối-tháng (mẫu, tử, các bucket) suy TỪ `scheduled` — KHÔNG từ `wos` thô. `Cancelled` KHÔNG vào bất kỳ bucket nào (không completed, không overdue, không pending).

| Field | Phạm vi | Định nghĩa BE |
|---|---|---|
| `total_scheduled` | **THÁNG** | `len(scheduled)` = số WO `due_date BETWEEN [start_month, end_month]` ∧ `status != Cancelled` (mẫu compliance — KHÔNG còn `len(wos)`) |
| `completed_on_time` | **THÁNG** | `⊆ scheduled`: `status==Completed ∧ !is_late` (tử compliance) |
| `overdue_in_month` | **THÁNG** | `⊆ scheduled`: `status==Overdue ∧ due_date trong tháng` — đếm TỪ `scheduled` đã lọc, KHÔNG gọi `count_overdue_pm()` |
| `pending_in_month` | **THÁNG** | `total_scheduled − completed_in_month − overdue_in_month` (phần dư trên population đã-loại-Cancelled; trừ TẤT CẢ Completed (on-time + late), KHÔNG chỉ on-time → Completed-late KHÔNG rơi vào pending; `Cancelled` đã ngoài `total_scheduled` nên cũng KHÔNG rơi vào đây) |
| `compliance_rate_pct` | **THÁNG** | `round(completed_on_time/total_scheduled*100, 1)` nếu `total_scheduled>0`, ngược lại **`None`** (FE '—') |
| `avg_days_late` | **THÁNG** | trung bình `date_diff(completion, due)` của WO completed-late trong tháng (KHÔNG đổi) |
| `overdue` | **TOÀN HỆ THỐNG** | `count_overdue_pm()` (RC-10, GIỮ NGUYÊN) — status==Overdue mọi thời gian; khớp launcher + drill `?overdue=1` |

> **Lưu ý phạm vi (OUT-of-scope vòng 25):** `Halted–Major Failure` (lỗi nặng → CM) GIỮ counted trong population (kết cục PM **không-tuân-thủ thật**, rơi vào `pending_in_month` như cũ). CHỈ loại `Cancelled`. `count_overdue_pm()` global + quy tắc `is_late` + shape/field-name KHÔNG đổi.

**INVARIANT đo được (BR-08-13):**
- **INV-PM-KPI-1:** `total_scheduled >= completed_on_time + overdue_in_month + pending_in_month` (luôn, mọi dataset). Đẳng thức chỉ khi KHÔNG có Completed-late; khi có Completed-late thì WO đó là phần "dôi" (đã hoàn thành nhưng KHÔNG on-time, KHÔNG overdue, KHÔNG pending — đã trừ qua `completed_in_month`) ⇒ vế phải `< total_scheduled`. `pending_in_month` là phần-dư trên population đã-loại-Cancelled → bất biến `≥` giữ kể cả khi xuất hiện status mới. ⇒ `overdue_in_month <= total_scheduled` luôn đúng. KHÔNG còn `Cancelled` lọt vào bất kỳ bucket nào.
- **INV-PM-KPI-2:** `overdue` (global) độc lập, KHÔNG ràng buộc với `total_scheduled`; có thể `overdue > total_scheduled` (chính xác về ngữ nghĩa — global ⊋ tháng) NHƯNG hai field ở 2 khối khác nhau, FE KHÔNG đặt chung strip.
- **INV-PM-KPI-3:** tử & mẫu compliance CÙNG `scheduled` (đã loại Cancelled); `total_scheduled==0 ⇒ compliance=None`.
- **INV-PM-KPI-6 (loại Cancelled khỏi mẫu — vòng 25):** WO `status==Cancelled` KHÔNG vào `total_scheduled`, KHÔNG vào MẪU compliance, KHÔNG vào `pending_in_month`/`overdue_in_month`/`completed_on_time`. Hệ quả đo được:
  - Tháng `{1 Completed on-time, 1 Completed late, 1 Overdue, 1 Cancelled}` → `total_scheduled==3` (KHÔNG 4), `compliance_rate_pct==round(1/3*100,1)==33.3` (cũ sai `1/4==25.0`), `completed_on_time==1`, `overdue_in_month==1`, `pending_in_month==0` (`3 − 2 completed − 1 overdue = 0`; Completed-late nằm trong `completed_in_month`, KHÔNG pending; Cancelled ngoài mẫu).
  - Tháng chỉ-Cancelled (vd 2 Cancelled, 0 khác) → `total_scheduled==0` ⇒ `compliance_rate_pct==None` (KHÔNG `0.0`), `pending_in_month==0`, `overdue_in_month==0`.
  - **No-regression:** tháng KHÔNG có Cancelled → mọi KPI GIỮ NGUYÊN giá trị như trước fix (Cancelled-free path bất biến — vì `scheduled == wos` khi không có Cancelled).
  - `trend_6months[*].rate` dùng CÙNG predicate loại-Cancelled (`t = số WO không-Cancelled trong tháng`) — cùng 1 SoT với tile compliance tháng hiện tại. `count_overdue_pm()` global + `is_late` + shape/field-name KHÔNG đổi.

**Implementation (delta so với `get_dashboard_stats` hiện tại, services/imm08.py:858):**

```python
# INV-PM-KPI-6: population khối-tháng = WO KHÔNG-Cancelled (loại WO đã hủy khỏi mẫu).
# Cancelled = đã hủy chủ động, KHÔNG còn nghĩa vụ → không kéo compliance, không phantom pending.
scheduled = [w for w in wos if w["status"] != PMStatus.CANCELLED]
total = len(scheduled)                                    # = total_scheduled (KHÔNG còn len(wos))
completed = [w for w in scheduled if w["status"] == PMStatus.COMPLETED]
on_time   = [w for w in completed if not w["is_late"]]
# THÁNG: đếm overdue TỪ scheduled (due_date trong tháng, đã loại Cancelled) — KHÔNG dùng count_overdue_pm()
overdue_in_month = sum(1 for w in scheduled if w["status"] == PMStatus.OVERDUE)
completed_in_month = len(completed)                       # TẤT CẢ Completed (on-time + late)
pending_in_month = total - completed_in_month - overdue_in_month  # phần dư → INV-PM-KPI-1 (Completed-late KHÔNG vào pending; Cancelled ngoài mẫu)
# GLOBAL (RC-10, giữ nguyên): khớp launcher + drill ?overdue=1
overdue_global = count_overdue_pm()
compliance_rate = round(len(on_time) / total * 100, 1) if total else None  # null-safe (INV-PM-KPI-3/6)
# avg_days_late: tính từ completed (đã trên scheduled) — Cancelled không có completion_date hợp lệ, không đổi
...
# trend_6months: t = số WO KHÔNG-Cancelled trong tháng (CÙNG predicate với tile — INV-PM-KPI-6)
#   month_scheduled = [w for w in month_wos if w["status"] != PMStatus.CANCELLED]
#   t = len(month_scheduled); rate = round(c_on / t * 100, 1) if t else 0.0
return {
    "kpis": {
        "total_scheduled":     total,             # = len(scheduled), KHÔNG còn Cancelled
        "completed_on_time":   len(on_time),
        "overdue_in_month":    overdue_in_month,
        "pending_in_month":    pending_in_month,
        "compliance_rate_pct": compliance_rate,   # number | None
        "avg_days_late":       avg_days_late,
        "overdue":             overdue_global,    # GLOBAL — KHÔNG đổi (RC-10)
    },
    "trend_6months": trend,
}
```

> `avg_days_late` KHÔNG đổi ngữ nghĩa (INV-PM-KPI-6 no-regression). `trend_6months[*].rate` dùng CÙNG mẫu loại-Cancelled (`t = số WO không-Cancelled trong tháng`) — KHÔNG để trend lệch chuẩn so với tile compliance tháng hiện tại (cùng 1 SoT predicate). Drill từ tile "Quá hạn (toàn hệ thống)" vẫn route `?overdue=1` → `count_overdue_pm()`.

---

## 4.2 SoT — "Ngày PM kế tiếp" (next_pm_date / next_due_date) (BR-08-03)

> **Self-Correction (vòng 1).** Thiết kế gốc của BR-08-03 chỉ ghi công thức (`next_pm_date = completion_date + interval`, KHÔNG due_date) NHƯNG **không bắt buộc 1 nguồn-sự-thật-duy-nhất** → implementation đã trôi thành **3 bản inline phân kỳ trên 2 trục**:
>
> | Write-site | Anchor (mốc) | Default interval khi `pm_interval_days` rỗng/0 |
> |---|---|---|
> | `update_pm_schedule_after_completion` (:452-453) → persist `PM Schedule.next_due_date` | `completion_date` ✅ | `or 90` ✅ |
> | `handle_work_order_submit` (:253-256, :269) → set `AC Asset.next_pm_date` + `PM Task Log.next_pm_date` | `completion_date` ✅ | `or 0` ❌ |
> | `submit_result` (:622-623) → field `next_pm_date` API trả về | `nowdate()` ❌ | `or 0` ❌ |
>
> **2 hệ quả divergence thật:**
> 1. **Anchor lệch (`nowdate()` vs `completion_date`):** khi PM hoàn thành trễ / backdated (`completion_date != today`), `submit_result` trả `next_pm_date` tính từ HÔM NAY, trong khi `PM Schedule.next_due_date` (đã persist) tính từ `completion_date` → API trả 1 ngày, DB lưu 1 ngày khác → KTV thấy lịch kế tiếp mâu thuẫn với phản hồi vừa nhận. Vi phạm trực tiếp mệnh đề BR-08-03 "KHÔNG dùng due_date" (và mặc nhiên KHÔNG dùng nowdate).
> 2. **Default lệch (`or 0` vs `or 90`):** khi `pm_interval_days` rỗng/0, `PM Schedule.next_due_date` nhảy `+90` ngày, nhưng `AC Asset.next_pm_date` chỉ `+0` = `completion_date` (hôm nay) → asset LẬP TỨC bị scheduler `backfill_pm_schedules_for_due_assets` coi là **PM-overdue giả** (`next_pm_date <= today`) trong khi PM Schedule báo còn 90 ngày. Báo động sai + tạo lịch trùng.
>
> **Quyết định:** hợp nhất về **1 helper SoT `compute_next_pm_date`** + **1 hằng `PM_DEFAULT_INTERVAL_DAYS = 90`**. Mọi write-site gọi CHUNG — KHÔNG inline lại `add_days(...)`, KHÔNG dùng literal `90`, KHÔNG dùng `nowdate()` làm anchor.

### 4.2.1 Hằng + helper SoT (pure, không I/O)

```python
# services/imm08.py — module-level constant (1 hằng, KHÔNG literal 90 rải rác)
PM_DEFAULT_INTERVAL_DAYS = 90

def compute_next_pm_date(completion_date, interval=None) -> str:
    """SoT DUY NHẤT (BR-08-03): ngày PM kế tiếp = completion_date + interval hiệu lực.

    INVARIANT anchor: LUÔN dùng completion_date (mốc hoàn thành thực tế của WO),
    KHÔNG bao giờ nowdate(). Khi PM hoàn thành trễ/backdated, giá trị này phải
    bằng nhau byte-for-byte ở MỌI nơi: PM Schedule.next_due_date (persist),
    AC Asset.next_pm_date, PM Task Log.next_pm_date, và field next_pm_date mà
    submit_result trả về.

    INVARIANT default: interval hiệu lực = interval nếu interval và interval > 0,
    else PM_DEFAULT_INTERVAL_DAYS (=90). Khi pm_interval_days rỗng/0, schedule —
    asset — API CÙNG nhảy +90 ngày → asset KHÔNG còn hiện PM-overdue giả trong khi
    schedule báo 90 ngày.

    Args:
        completion_date: mốc hoàn thành WO (str/date) — anchor BẮT BUỘC.
        interval: số ngày chu kỳ PM (int/None). None hoặc <= 0 → dùng default 90.

    Returns:
        str: ngày PM kế tiếp (chuỗi YYYY-MM-DD do add_days trả về).
    """
    effective = interval if interval and interval > 0 else PM_DEFAULT_INTERVAL_DAYS
    return add_days(getdate(completion_date), effective)
```

### 4.2.2 Consumer dùng chung (4 write-site, INVARIANT byte-for-byte)

| Write-site | TRƯỚC (inline, phân kỳ) | SAU (gọi SoT) |
|---|---|---|
| `update_pm_schedule_after_completion` | `interval = sched.pm_interval_days or 90; sched.next_due_date = add_days(getdate(completion_date), interval)` | `sched.next_due_date = compute_next_pm_date(completion_date, sched.pm_interval_days)` |
| `handle_work_order_submit` → `AC Asset.next_pm_date` | `sched_interval = ... or 0; _add_days(doc.completion_date, sched_interval)` | `compute_next_pm_date(doc.completion_date, sched_interval)` |
| `handle_work_order_submit` → `PM Task Log.next_pm_date` | `_add_days(doc.completion_date, sched_interval)` | `compute_next_pm_date(doc.completion_date, sched_interval)` |
| `submit_result` → field trả về | `add_days(nowdate(), sched_interval)` (anchor SAI) | `compute_next_pm_date(wo.completion_date, sched_interval)` |
| `PM Schedule.before_save` (controller — **PERSISTER thực sự** của `next_due_date`) | `interval = pm_interval_days or 0; next_due_date = add_days(last_pm_date, interval)` (inline, `or 0` ⇒ interval=0 bỏ qua recompute → giá trị cũ kẹt) | `next_due_date = compute_next_pm_date(last_pm_date, pm_interval_days)` (anchor=last_pm_date, default trong helper) |

- `sched_interval` ở `handle_work_order_submit` / `submit_result` truyền `pm_interval_days` **THÔ** từ PM Schedule (có thể rỗng/0/None) — KHÔNG còn `or 0` / `or 90` tại call-site; việc chọn default 90 nằm DUY NHẤT trong `compute_next_pm_date`.
- **Latent 4th site (controller persister):** `PM Schedule.before_save` chạy SAU service-layer set `next_due_date` và RECOMPUTE từ `last_pm_date` (== `completion_date` sau PM). Trước đây dùng inline `add_days(last_pm_date, pm_interval_days or 0)` → là nguồn phân kỳ ẩn (đặc biệt khi `pm_interval_days=0`: nhánh `if last_pm_date and interval` bị bỏ qua, để giá trị cũ kẹt). Nay đi qua `compute_next_pm_date` → đồng nhất default 90 + anchor=last_pm_date với toàn bộ SoT. Lazy-import `compute_next_pm_date` trong `before_save` (tránh circular).
- **INVARIANT byte-for-byte:** sau 1 lần submit WO, với MỌI `completion_date` (kể cả backdated) và MỌI `pm_interval_days` (kể cả 0/rỗng):
  `submit_result.next_pm_date == PM Schedule.next_due_date (persist) == AC Asset.next_pm_date == PM Task Log.next_pm_date`.
- **Grep guard (PASS bắt buộc):**
  - 0 occurrence `add_days(nowdate(), <interval>)` cho next_pm_date/next_due_date ở BẤT KỲ đâu (anchor nowdate bị cấm cho ngày PM kế tiếp).
  - 0 occurrence inline `add_days(...completion_date.../last_pm_date..., interval)` cho next_pm_date/next_due_date NGOÀI thân `compute_next_pm_date` (chỉ còn trong helper + docstring) — kể cả `PM Schedule.before_save`.
  - 0 literal `90` cho interval ngoài hằng `PM_DEFAULT_INTERVAL_DAYS`; 0 `or 0` / `or 90` rải rác ở call-site (service + controller). _Lưu ý:_ `create_pm_schedule_from_asset` còn `pm_interval_days or 0` để CHỌN `pm_type` (qua `_PM_TYPE_FROM_INTERVAL`) — KHÔNG phải tính next-date, nằm ngoài phạm vi BR-08-03.

### 4.2.3 Quan hệ với BR-08-05 (is_late) và overdue (BR-08-11)

`compute_next_pm_date` chỉ tính NGÀY KẾ TIẾP, độc lập với `is_late` (BR-08-05: `is_late = completion_date > due_date`). Khi anchor đã đúng = `completion_date`, asset chỉ bị scheduler coi PM-overdue khi `next_pm_date <= today` THẬT (đến hạn) — không còn overdue-giả do `+0`. Default 90 đảm bảo asset thiếu cấu hình `pm_interval_days` vẫn có chu kỳ hợp lý thay vì kẹt ở hôm nay.

---

## 4b. Repository Layer

File `assetcore/repositories/pm_repo.py` định nghĩa 4 repository extends `BaseRepository`:

| Repo | DocType | Dùng cho |
|---|---|---|
| `PMScheduleRepo` | `PM Schedule` | CRUD + scheduler query (`status=Active`, `next_due_date<=today+alert`) |
| `PMWorkOrderRepo` | `PM Work Order` | CRUD + dashboard / calendar aggregate |
| `PMChecklistTemplateRepo` | `PM Checklist Template` | Template CRUD + clone vào WO |
| `PMTaskLogRepo` | `PM Task Log` | Audit-final insert sau khi WO Completed |

Service `imm08.py` gọi qua repository (`PMWorkOrderRepo.set_values`, `PMWorkOrderRepo.get`, …) — không `frappe.db.*` thô trừ ở scheduler `generate_pm_work_orders_from_schedule` (idempotency check).

Idempotency key scheduler: `(pm_schedule, status NOT IN [Completed, Cancelled])` — xem `generate_pm_work_orders_from_schedule` line 175.

---

## 5. API Layer

File: `assetcore/api/imm08.py`

Pattern thin wrapper dùng `_handle / _ok / _err`:

```python
import frappe
from assetcore.utils.helpers import _handle, _ok, _err, _parse_json
from assetcore.services import imm08 as service

@frappe.whitelist()
def list_pm_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    parsed = _parse_json(filters, field_name="filters", default={})
    return _handle(service.list_pm_work_orders, parsed, int(page), int(page_size))

@frappe.whitelist(methods=["POST"])
def assign_technician(name: str, technician: str, scheduled_date: str = None) -> dict:
    return _handle(service.assign_technician, name, technician, scheduled_date)

@frappe.whitelist(methods=["POST"])
def submit_pm_result(name: str, checklist_results: str = "[]",
                     overall_result: str = "", technician_notes: str = "",
                     pm_sticker_attached: int = 0, duration_minutes: int = 0) -> dict:
    results = _parse_json(checklist_results, field_name="checklist_results", default=[])
    return _handle(service.submit_pm_result, name, results, overall_result,
                   technician_notes, pm_sticker_attached, duration_minutes)

@frappe.whitelist(methods=["POST"])
def reschedule_pm(name: str, new_date: str, reason: str) -> dict:
    if not reason or len(reason.strip()) < 5:
        return _err("Lý do hoãn lịch là bắt buộc (tối thiểu 5 ký tự).", "VALIDATION")
    return _handle(service.reschedule_pm, name, new_date, reason)
```

**Helper `_handle`:**

```python
def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "IMM-08 API Error")
        return _err("Lỗi hệ thống. Vui lòng thử lại.", "INTERNAL")
```

> **⚡ Verb-flip `assign_technician` (Mobile-BE binding — ADR-IMM08-MOB-01 / ADR-MOBILE-012):** code-sketch trên đã khai `@frappe.whitelist(methods=["POST"])` cho `assign_technician` (đúng doc-intent có sẵn) NHƯNG **source thật `api/imm08.py:46` vẫn còn bare `@frappe.whitelist()`** (nhận GET) — **verb-parity gap R33 BỎ SÓT** (R33 đã flip `submit_pm_result` `imm08.py:54` + 3 write-action imm11, SÓT `assign_technician`; sibling imm08 của `add_measurement` imm11 — ADR-MOBILE-011). `assign_technician` là **write-action DISPATCH** (status Open/Overdue→In Progress + asset→Under Maintenance, KHÔNG idempotent ⇒ POST đúng-semantics). **Hành động (BE Bước 4):** flip ĐÚNG 1 dòng decorator `api/imm08.py:46` bare→`@frappe.whitelist(methods=['POST'])` (signature/body/`rbac.require('pm.write')` `:49` UNCHANGED) ⇒ source khớp doc + mobile-contract POST ⇒ `_PARITY_VERB_ALLOWLIST` GIỮ `set()`. Mobile contract đầy đủ: [`05_API_Specification.md §0.1.1`](./05_API_Specification.md) + [`docs/mobile/04-api-contract.md §8.25`](../mobile/04-api-contract.md) + [`docs/mobile/ADR-MOBILE-012.md`](../mobile/ADR-MOBILE-012.md). Sau flip cần USER reload gunicorn `--preload` (LIVE reject GET 405) — HARD-STOP USER, KHÔNG curl-verify LIVE (LL-DEPLOY-07).

---

## 6. Audit Trail

| Trigger | Entry type | Actor | Payload |
|---|---|---|---|
| WO on_submit (Completed) | PM Task Log insert | KTV | asset, pm_type, completion, is_late, overall_result |
| Fail-Major submit | PM Task Log + CM WO insert | KTV | failure_description, failed_items |
| Overdue scheduler | db.set_value log | System | status=Overdue, days_overdue |
| Reschedule | technician_notes append | Workshop Manager | old_date → new_date, reason |

Hash chain: sử dụng Frappe native `track_changes` trên PM Work Order. PM Task Log immutable (`in_create=1`) là audit-final record.

---

## 7. Background jobs / Scheduler

Đăng ký trong `assetcore/hooks.py`:

```python
scheduler_events = {
    "daily": [
        "assetcore.services.imm08.backfill_pm_schedules_for_due_assets",
        "assetcore.services.imm08.generate_pm_work_orders_from_schedule",
    ],
}

doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            # ...
        ],
    },
    "AC Asset": {
        "after_insert": "assetcore.services.imm08.create_pm_schedule_from_asset",
    },
    "PM Work Order": {
        "validate": "assetcore.services.imm16.gate_wo_submit",
        "on_submit": "assetcore.services.imm16.eval_imm08_09_realtime",
    },
}
```

| Job | Tần suất | Hook | Mục đích |
|---|---|---|---|
| `backfill_pm_schedules_for_due_assets` | Daily | `services.imm08` | Tạo PM Schedule cho Asset đến hạn nhưng chưa có lịch (safety net) |
| `generate_pm_work_orders_from_schedule` | Daily | `services.imm08` | Sinh PM WO mới từ PM Schedule đến hạn + đánh `Overdue` cho WO quá ngày |

**Idempotency key:** trong service đã check `(pm_schedule, status NOT IN [Completed, Cancelled])` → skip nếu đã tồn tại.

---

## 8. Integration

**Module nội bộ:**
- IMM-04 → IMM-08 (Pattern A): `Asset Commissioning.on_submit` → `assetcore.services.imm08.create_pm_schedule_from_commissioning` tạo PM Schedule đầu tiên (xem `hooks.py` §doc_events).
- AC Asset → IMM-08 (Pattern A): `AC Asset.after_insert` → `assetcore.services.imm08.create_pm_schedule_from_asset` tạo PM Schedule ngay khi Asset được tạo nếu `is_pm_required=1`.
- IMM-08 (backfill scheduler): `backfill_pm_schedules_for_due_assets` daily — safety net tạo PM Schedule cho Asset chưa có lịch.
- IMM-08 → IMM-09: Halted–Major Failure hoặc Fail-Major → `_create_cm_wo_from_failure(doc, priority)` insert một `Asset Repair` (doctype CM, không phải PM Work Order) với `source_pm_wo` liên kết. Function nằm trong `services/imm08.py`.
- IMM-08 ↔ IMM-16 (Pattern C compliance gate): `PM Work Order.validate` gọi `imm16.gate_wo_submit(doc, method=None)` — gate raise ServiceError nếu CAPA Critical chặn. `on_submit` gọi `imm16.eval_imm08_09_realtime` để cập nhật scorecard.
- IMM-08 → Notification Framework (E5, Pattern A — vòng 7): `PM Work Order.on_update` → `assetcore.services.notifications.notify_escalation`. Khi WO chuyển VÀO state escalation (`Halted–Major Failure`: `doc_status=0`, VÀO bởi PM User, GỠ bởi System Manager) → báo supervisor + System Manager để can thiệp. Engine đọc Workflow metadata động (KHÔNG hard-code tên state). Spec: `docs/imm-00/04_Backend_Design.md §III.1b-5`.

**Bên ngoài:**
- Frappe Email Queue: daily summary + escalation email

---

## 9. Migration & Patch

| Patch | Path | Mục đích |
|---|---|---|
| Wave 1 (current) | deploy via `bench migrate` | DocTypes + roles fixtures |
| Wave 2 (planned) | `assetcore/patches/v3_0/imm08_align_to_ac_asset.py` | Migrate `Link→Asset` sang `Link→AC Asset`, cập nhật field paths |

Fixtures: roles (`Workshop Head`, `HTM Technician`, `VP Block2`, `CMMS Admin`, `Biomed Engineer`) tại `fixtures/roles.json`.

---

## 10. Non-functional

**Concurrency:** Frappe optimistic lock qua `doc.modified` check — 2 KTV không thể submit cùng WO.

**Caching:** Dashboard stats không cache hiện tại — xem xét Redis cache TTL 5 phút nếu latency > 800ms.

**Logging:**
```python
frappe.logger("imm08").info(f"PM WO {wo_name} submitted by {frappe.session.user}")
frappe.logger("imm08").warning(f"Skip PM WO for {asset} — Out of Service")
```

**Idempotency:** Scheduler `generate_pm_work_orders` kiểm tra existing WO trước khi insert.

---

## DoD — File 04 hoàn chỉnh

- [x] Quy ước ngôn ngữ BE: code tiếng Anh + field label tiếng Việt
- [x] 6 DocType nêu đầy đủ trường + naming + permissions
- [x] Quan hệ liên DocType vẽ rõ
- [x] State machine + transitions định nghĩa
- [x] Mọi mutation map về service function với type hints
- [x] Mọi error raise qua `ServiceError(ErrorCode.X, "msg tiếng Việt")`
- [x] API layer dùng `_handle / _ok / _err`
- [x] Audit trail trigger liệt kê
- [x] Index DB cho query nóng
- [x] 2 background job đăng ký rõ
- [x] Integration IMM-04 + IMM-09 liệt kê
- [x] Patch path xác định
