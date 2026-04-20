# IMM-08 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |

---

## 1. Overview

IMM-08 implement **6 DocTypes**, **2 scheduler jobs**, **1 controller hook** và **9 API endpoints** để quản lý vòng đời PM. Logic nghiệp vụ tập trung trong:

- `pm_work_order.py` controller (validate + on_submit lifecycle).
- `tasks.py` scheduler (auto-create + overdue detection).
- `api/imm08.py` REST layer (thin wrapper, gọi `frappe.get_doc` + `db.set_value`).

```
┌─────────────────────────────────────────────────────────────┐
│                         API layer                           │
│              assetcore/api/imm08.py (9 endpoints)           │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌──────────────┐  ┌─────────────────┐
│ Controller    │  │ Scheduler    │  │ IMM-04 hook     │
│ pm_work_order │  │ tasks.py     │  │ services/imm04  │
│ .py           │  │              │  │                 │
└───────┬───────┘  └──────┬───────┘  └────────┬────────┘
        │                 │                   │
        └─────────────────┼───────────────────┘
                          ▼
        ┌────────────────────────────────────────┐
        │         Frappe ORM + MariaDB           │
        │  PM Schedule · PM Checklist Template · │
        │  PM Checklist Item · PM Work Order ·   │
        │  PM Checklist Result · PM Task Log     │
        │  Asset (custom_* fields)               │
        └────────────────────────────────────────┘
```

---

## 2. DocType Schema

### 2.1 PM Schedule

| Property | Value |
|---|---|
| Naming | `format:PMS-{asset_ref}-{pm_type}` |
| Submittable | No |
| Track changes | Yes |

| Field | Type | Required | Notes |
|---|---|---|---|
| `asset_ref` | Link → Asset | ✅ | search_index, list_view |
| `pm_type` | Select | ✅ | `Quarterly · Semi-Annual · Annual · Ad-hoc` |
| `status` | Select | — | `Active · Paused · Suspended` (default Active) |
| `created_from_commissioning` | Link → Asset Commissioning | — | read-only, IMM-04 hook fill |
| `pm_interval_days` | Int | ✅ | > 0 |
| `checklist_template` | Link → PM Checklist Template | ✅ | BR-08-01 |
| `alert_days_before` | Int | — | default 7 |
| `responsible_technician` | Link → User | — | KTV mặc định khi tạo WO |
| `last_pm_date` | Date | — | controller advance sau on_submit |
| `next_due_date` | Date | — | list_view, controller compute |
| `notes` | Text | — | — |

Permissions: `Workshop Head / CMMS Admin / System Manager` = full · `HTM Technician / Biomed Engineer / VP Block2` = R.

---

### 2.2 PM Checklist Template

| Property | Value |
|---|---|
| Naming | `format:PMCT-{asset_category}-{pm_type}` |
| Submittable | No |

| Field | Type | Required | Notes |
|---|---|---|---|
| `template_name` | Data | ✅ | list_view |
| `asset_category` | Link → Asset Category | ✅ | search_index |
| `pm_type` | Select | ✅ | same options as PM Schedule |
| `version` | Data | — | default `1.0` |
| `effective_date` | Date | — | — |
| `approved_by` | Link → User | — | — |
| `checklist_items` | Table → PM Checklist Item | ✅ | child table |

Permissions: `Workshop Head / CMMS Admin` = R/W/Create/Delete · others = R.

---

### 2.3 PM Checklist Item (child)

`istable: 1` — parent: PM Checklist Template.

| Field | Type | Required | Notes |
|---|---|---|---|
| `item_code` | Data | — | read_only, list_view |
| `description` | Text | ✅ | list_view |
| `measurement_type` | Select | ✅ | `Pass/Fail · Numeric · Text` |
| `unit` | Data | — | depends_on Numeric |
| `expected_min` | Float | — | depends_on Numeric |
| `expected_max` | Float | — | depends_on Numeric |
| `is_critical` | Check | — | default 0; mục Critical Fail-Major → Halted |
| `reference_section` | Data | — | vd "Service Manual §3.2" |

---

### 2.4 PM Work Order

| Property | Value |
|---|---|
| Naming | `PM-WO-.YYYY.-.#####` |
| Submittable | ✅ Yes |
| Track changes | Yes |

Field groups (`field_order`):

```
asset_ref · pm_schedule · pm_type · wo_type · | status · is_late · due_date · scheduled_date · completion_date
[Phân công]   assigned_to · assigned_by
[Kết quả PM]  overall_result · technician_notes · pm_sticker_attached · duration_minutes · attachments
[Checklist]   checklist_results
[Liên kết CM] source_pm_wo
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `asset_ref` | Link → Asset | ✅ | search_index |
| `pm_schedule` | Link → PM Schedule | ✅ | — |
| `pm_type` | Data | — | read_only, copy từ Schedule |
| `wo_type` | Select | — | `Preventive · Corrective` (default Preventive) |
| `status` | Select | ✅ | 7 states (xem §3) |
| `is_late` | Check | — | read_only, controller compute |
| `due_date` | Date | ✅ | — |
| `scheduled_date` | Date | — | KTV plan date (≠ due_date khi reschedule) |
| `completion_date` | Date | — | read_only, set on_submit |
| `assigned_to` | Link → User | — | KTV thực hiện |
| `assigned_by` | Link → User | — | session.user khi assign |
| `overall_result` | Select | — | `Pass · Pass with Minor Issues · Fail` |
| `technician_notes` | Text | — | — |
| `pm_sticker_attached` | Check | — | — |
| `duration_minutes` | Int | — | — |
| `attachments` | Attach Multiple | — | bắt buộc khi Class III (BR-08-06) |
| `checklist_results` | Table → PM Checklist Result | — | clone từ template khi tạo |
| `source_pm_wo` | Link → PM Work Order | conditional | `mandatory_depends_on: eval:doc.wo_type==='Corrective'` (BR-08-02) |

Permissions:

| Role | R | W | C | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| Workshop Head | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| CMMS Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HTM Technician | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Biomed Engineer | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| VP Block2 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| System Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

---

### 2.5 PM Checklist Result (child)

`istable: 1` — parent: PM Work Order.

| Field | Type | Required | Notes |
|---|---|---|---|
| `checklist_item_idx` | Int | — | read_only, list_view |
| `description` | Data | — | read_only, copy từ template |
| `measurement_type` | Select | — | read_only |
| `result` | Select | ✅ | `Pass · Fail–Minor · Fail–Major · N/A` |
| `measured_value` | Float | — | depends_on Numeric |
| `unit` | Data | — | read_only |
| `notes` | Text | conditional | `mandatory_depends_on: result IN (Fail–Minor, Fail–Major)` |
| `photo` | Attach | — | — |

---

### 2.6 PM Task Log

| Property | Value |
|---|---|
| Naming | autoname (default Frappe hash) |
| Submittable | No |
| `in_create: 1` | ✅ — chặn update sau insert (BR-08-10) |
| Track changes | No (immutable) |

| Field | Type | Required | Notes |
|---|---|---|---|
| `asset_ref` | Link → Asset | ✅ | search_index |
| `pm_work_order` | Link → PM Work Order | ✅ | — |
| `pm_type` | Data | — | — |
| `completion_date` | Date | ✅ | — |
| `technician` | Link → User | — | — |
| `overall_result` | Select | — | mirror từ WO |
| `is_late` | Check | — | read_only |
| `days_late` | Int | — | read_only, `date_diff(completion_date, due_date)` |
| `next_pm_date` | Date | — | `completion_date + interval` |
| `summary` | Text | — | mirror `technician_notes` |

Permissions: tất cả role có `read` · `Workshop Head / CMMS Admin / System Manager` có `create` (cho controller insert) · **không ai có `write` hoặc `delete`** → enforce immutability.

---

## 3. State Machine — PM Work Order

States: `Open · In Progress · Pending–Device Busy · Overdue · Completed · Halted–Major Failure · Cancelled`.

| From | To | Trigger | Service / API |
|---|---|---|---|
| (insert) | `Open` | scheduler tạo WO | `tasks.generate_pm_work_orders` |
| `Open` / `Overdue` | `In Progress` | Workshop assign KTV | `api.imm08.assign_technician` |
| `Open` / `In Progress` | `Overdue` | scheduler — `today > due_date` | `tasks.check_pm_overdue` |
| `In Progress` / `Overdue` | `Pending–Device Busy` | Workshop hoãn lịch | `api.imm08.reschedule_pm` |
| `Pending–Device Busy` | `In Progress` | KTV resume (manual) | UI / `db_set` |
| `In Progress` / `Overdue` | `Completed` | KTV submit | `api.imm08.submit_pm_result` → `wo.submit()` |
| `In Progress` | `Halted–Major Failure` | KTV báo lỗi nghiêm trọng | `api.imm08.report_major_failure` |
| `In Progress` (auto) | `Halted–Major Failure` | submit có Fail-Major | controller `_handle_failures()` |
| `Open` / `In Progress` | `Cancelled` | Workshop huỷ | UI manual + `on_cancel` log |

---

## 4. Validation Rules

| VR ID | Field / Action | Implementation | Source |
|---|---|---|---|
| VR-08-01 | `pm_schedule.checklist_template` | scheduler skip + email Admin nếu thiếu | `tasks.generate_pm_work_orders` |
| VR-08-02 | `Asset.status` ≠ Out of Service | scheduler skip | `tasks.generate_pm_work_orders` |
| VR-08-03 | Checklist 100% có result | `_validate_checklist_complete()` | `pm_work_order.py` |
| VR-08-04 | Class III/C/D phải có ảnh | `_validate_photo_for_high_risk()` | `pm_work_order.py` |
| VR-08-05 | CM WO có `source_pm_wo` | `_validate_cm_source()` + DocType `mandatory_depends_on` | `pm_work_order.py` + JSON |
| VR-08-06 | `Fail-*` phải có `notes` | DocType `mandatory_depends_on` | `pm_checklist_result.json` |
| VR-08-07 | PM Schedule unique theo (asset, pm_type) | naming `PMS-{asset_ref}-{pm_type}` | `pm_schedule.json` |
| VR-08-08 | `assign_technician` chỉ Open/Overdue | API guard | `api/imm08.py` |
| VR-08-09 | Reason ≥ 5 ký tự | API guard | `api/imm08.py` |
| VR-08-10 | Submit khi đã docstatus=1 | API guard | `api/imm08.py` |

---

## 5. Hooks (controller lifecycle)

```python
# pm_work_order.py — đã code
def validate(self):
    self._validate_checklist_complete()      # BR-08-08
    self._validate_photo_for_high_risk()     # BR-08-06
    self._validate_cm_source()               # BR-08-02

def on_submit(self):
    self._set_completion()                   # is_late, completion_date (BR-08-05)
    self._update_pm_schedule()               # BR-08-03
    self._update_asset_fields()              # custom_*_pm_date trên Asset
    self._create_pm_task_log()               # BR-08-10
    self._handle_failures()                  # auto CM WO (BR-08-09)
```

### IMM-04 → IMM-08 hook

`Asset Commissioning.on_submit` (in `services/imm04.py`) tạo `PM Schedule` đầu tiên với:

```python
PM Schedule {
  asset_ref: commissioning.asset,
  pm_type:   <từ Asset Category default>,
  pm_interval_days: <từ template>,
  checklist_template: <PMCT-{category}-{pm_type}>,
  last_pm_date: commissioning.completion_date,
  next_due_date: completion_date + pm_interval_days,   # BR-08-03 cho first PM
  created_from_commissioning: commissioning.name,
}
```

---

## 6. API

9 endpoints — chi tiết tại `IMM-08_API_Interface.md`. Tóm tắt mapping endpoint → service / DocType:

| Endpoint | Touches |
|---|---|
| `list_pm_work_orders` | `frappe.db.get_all("PM Work Order")` + enrich asset_name |
| `get_pm_work_order` | `frappe.get_doc("PM Work Order")` + Asset lookup |
| `assign_technician` | `wo.save()` (set assigned_to/by, scheduled_date, status) |
| `submit_pm_result` | Update child rows + `wo.submit()` → controller lifecycle |
| `report_major_failure` | `db.set_value` Asset+WO + `frappe.get_doc(CM WO).insert()` + email |
| `get_pm_calendar` | `db.get_all` filter date range, summary aggregate |
| `get_pm_dashboard_stats` | `db.get_all` + Python aggregation 6 tháng trend |
| `reschedule_pm` | `wo.save()` (due_date + status + append notes) |
| `get_asset_pm_history` | `db.get_all("PM Task Log", filters={asset_ref})` |

---

## 7. Schedulers

`hooks.py`:

```python
scheduler_events = {
    "daily": [
        "assetcore.tasks.generate_pm_work_orders",   # 06:00
        "assetcore.tasks.check_pm_overdue",          # 08:00
    ],
}
```

### 7.1 `generate_pm_work_orders`

```
1. Query PM Schedule WHERE status=Active AND next_due_date <= today + alert_days_before
2. Cho mỗi schedule:
   a. Skip nếu đã tồn tại WO {pm_schedule, status IN [Open, In Progress, Pending–Device Busy]}
   b. Skip + email Admin nếu thiếu checklist_template (BR-08-01)
   c. Skip nếu Asset.status = Out of Service (BR-08-04)
   d. Insert PM Work Order: status=Open, due_date=next_due_date, wo_type=Preventive,
      assigned_to=responsible_technician (nếu có), clone checklist từ template
3. Email tóm tắt cho Workshop Head: "{N} PM Work Order mới được tạo hôm nay"
```

### 7.2 `check_pm_overdue`

```
1. Query PM WO WHERE status IN [Open, In Progress] AND due_date < today
2. Cho mỗi WO:
   a. db.set_value status = "Overdue"
   b. days_overdue = date_diff(today, due_date)
   c. Phân loại:
      - days ≤ 7   → email Workshop Head
      - 8–30       → email VP Block2 (escalation)
      - > 30       → email BGĐ (critical, leo thang)
3. Log "{count} WOs marked Overdue"
```

---

## 8. Fixtures

| Fixture | Path | Mục đích |
|---|---|---|
| Roles | `fixtures/roles.json` | Workshop Head, HTM Technician, VP Block2, CMMS Admin, Biomed Engineer |
| Sample PM Checklist Templates | manual seed | Bộ template cho 5 category mẫu (Ventilator, Monitor, Infusion, X-ray, Defibrillator) |

(IMM-08 hiện chưa ship fixture file riêng — dùng sample seed script `tests/uat_imm08.py`.)

---

## 9. `hooks.py` snippet

```python
# assetcore/hooks.py (rút gọn phần liên quan IMM-08)
scheduler_events = {
    "daily": [
        "assetcore.tasks.generate_pm_work_orders",
        "assetcore.tasks.check_pm_overdue",
    ],
}

# IMM-04 → IMM-08 hook (in services/imm04.py)
doc_events = {
    "Asset Commissioning": {
        "on_submit": "assetcore.services.imm04.on_commissioning_submit",
    },
}
```

---

## 10. Indexes

| Table | Index | Lý do |
|---|---|---|
| `tabPM Work Order` | `asset_ref` (search_index trong DocType JSON) | filter dashboard / list |
| `tabPM Work Order` | `(status, due_date)` | scheduler check_pm_overdue + list view |
| `tabPM Work Order` | `assigned_to` | KTV xem WO của mình |
| `tabPM Schedule` | `asset_ref` (search_index) | hook IMM-04 lookup |
| `tabPM Schedule` | `(status, next_due_date)` | scheduler generate |
| `tabPM Checklist Template` | `asset_category` (search_index) | scheduler lookup template |
| `tabPM Task Log` | `asset_ref` (search_index) | `get_asset_pm_history` |

---

## 11. Migration

### 11.1 Wave 1 (current — LIVE)

- DocTypes deploy qua `bench migrate`.
- Asset core là ERPNext `Asset` + `custom_*` fields (`custom_last_pm_date`, `custom_next_pm_date`, `custom_pm_status`, `custom_risk_class`).
- Roles `Workshop Head`, `HTM Technician`, `VP Block2`, `CMMS Admin`, `Biomed Engineer` từ wave-1 fixtures.

### 11.2 Wave 2 (planned — IMM-00 v3 alignment)

| Item | Action |
|---|---|
| Asset → AC Asset | Replace `Link → Asset` bằng `Link → AC Asset` trên `pm_schedule.asset_ref`, `pm_work_order.asset_ref`, `pm_task_log.asset_ref` |
| `custom_risk_class` → `AC Asset.risk_classification` | Update `pm_work_order._validate_photo_for_high_risk()` |
| `custom_*_pm_date` → `AC Asset.last_pm_date / next_pm_date` | Update `_update_asset_fields()` |
| Roles | Map `Workshop Head` → `IMM Workshop Lead`, `HTM Technician` → `IMM Technician`, `VP Block2` → `IMM Department Head` |
| Lifecycle Event | `_create_pm_task_log()` thêm `create_lifecycle_event("pm_completed")` qua IMM-00 service |

Migration patch sẽ ở `assetcore/patches/v3_0/imm08_align_to_ac_asset.py`.

---

*End of Technical Design v2.0.0 — IMM-08 Preventive Maintenance*
