# IMM-09 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-09 — Corrective Maintenance / Repair |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |

---

## 1. Overview

Module IMM-09 hiện thực hoá CMMS Corrective Maintenance trên Frappe v15. Toàn bộ logic tách thành 3 lớp:

1. **DocType layer** — `Asset Repair`, `Spare Parts Used`, `Repair Checklist`, `Firmware Change Request` + JSON schema + controller hooks.
2. **Service layer** — `assetcore/services/imm09.py` — toàn bộ business logic, validation, lifecycle event creation, scheduler.
3. **API layer** — `assetcore/api/imm09.py` — 12 endpoint REST `@frappe.whitelist()` gọi service layer; trả `_ok`/`_err` chuẩn hoá.

Frontend Vue 3 + Pinia store (`stores/imm09.ts`) + 7 view (`CM*.vue`) — gọi API qua axios + token auth.

---

## 2. Architecture Layers

```
┌──────────────────────────────────────────────────────────┐
│  Frontend (Vue 3 + Frappe UI + Pinia)                   │
│  ─ CMDashboardView · CMWorkOrderListView                │
│  ─ CMCreateView · CMWorkOrderDetailView                 │
│  ─ CMDiagnoseView · CMPartsView · CMChecklistView       │
│  ─ CMMttrView                                            │
│  Store: stores/imm09.ts (cmStore)                        │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP (token / sid)
                         ▼
┌──────────────────────────────────────────────────────────┐
│  API layer — assetcore/api/imm09.py (12 endpoints)      │
│  + utils/helpers.py (_ok / _err)                         │
└────────────────────────┬─────────────────────────────────┘
                         │ Python call
                         ▼
┌──────────────────────────────────────────────────────────┐
│  Service layer — assetcore/services/imm09.py            │
│  validate_* · check_* · get_sla_target · complete_repair│
│  _create_lifecycle_event · scheduler functions           │
└────────────────────────┬─────────────────────────────────┘
                         │ ORM (frappe.get_doc / db.set_value)
                         ▼
┌──────────────────────────────────────────────────────────┐
│  DocType layer (controller + hooks)                     │
│  Asset Repair: before_insert · validate · before_submit │
│                · on_insert · on_submit                   │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  MariaDB (tabAsset Repair · tabSpare Parts Used ...)    │
└──────────────────────────────────────────────────────────┘
```

---

## 3. ERD

```
┌──────────────────┐      ┌────────────────────┐
│   AC Asset       │ 1  N │  Asset Repair      │
│  (IMM-00 core)   │◄─────┤  (WO-CM-...)       │
│                  │      │                    │
│  + status        │      │  asset_ref FK      │
│  + custom_risk_  │      │  status            │
│    class         │      │  priority          │
│  + custom_last_  │      │  open_datetime     │
│    repair_date   │      │  completion_dt     │
│  + custom_mttr_  │      │  mttr_hours        │
│    avg_hours     │      │  sla_breached      │
└────────┬─────────┘      │  is_repeat_failure │
         │                │  source: incident_ │
         │                │    report or       │
         │                │    source_pm_wo    │
         │                └──┬──────┬──────┬───┘
         │                   │ 1  N │ 1  N │ 1  1
         │                   ▼      ▼      ▼
         │      ┌────────────────┐ ┌────────────────┐ ┌────────────────────┐
         │      │ Spare Parts    │ │ Repair         │ │ Firmware Change    │
         │      │ Used (child)   │ │ Checklist      │ │ Request (FCR-...)  │
         │      │                │ │ (child)        │ │                    │
         │      │ item_code      │ │ test_desc      │ │ asset, repair_wo   │
         │      │ qty            │ │ test_category  │ │ version_before     │
         │      │ unit_cost      │ │ expected_value │ │ version_after      │
         │      │ stock_entry_   │ │ measured_value │ │ status (Approved)  │
         │      │   ref (reqd)   │ │ result         │ │ approved_by        │
         │      └────────────────┘ │   (Pass/Fail)  │ └────────────────────┘
         │                         └────────────────┘
         │
         │ 1  N
         ▼
┌──────────────────────┐         ┌──────────────────┐
│ Asset Lifecycle      │         │  Incident Report │
│ Event (immutable)    │         │  (IMM-12)        │
│                      │         │                  │
│ event_type:          │         │  IR-2026-...     │
│  repair_opened       │         └──────────────────┘
│  diagnosis_submitted │                  ▲
│  repair_completed    │                  │ FK
│  cannot_repair       │                  │
│ from_status →        │         ┌──────────────────┐
│ to_status            │         │  PM Work Order   │
│ root_record (WO ref) │         │  (IMM-08)        │
└──────────────────────┘         │  PM-WO-2026-...  │
                                 └──────────────────┘
                                          ▲
                                          │ FK source_pm_wo
                                          └─── (Asset Repair)
```

---

## 4. State Machine

```
                      ┌─────────► Cancelled (manual)
                      │
[start] ──► Open ─────┼─────► Assigned ─────► Diagnosing
                      │                            │
                      │                            ├─► Pending Parts ──┐
                      │                            │                   │
                      │                            └────────► In Repair ◄
                      │                                          │
                      │                                          ▼
                      │                              Pending Inspection
                      │                                    │      │
                      │                          (BR-09-04)│      │ (cannot_repair=1)
                      │                                    ▼      ▼
                      │                              Completed   Cannot Repair
                      │                                  │            │
                      │                            Asset=Active  Asset=Out of Service
                      │                                  │            │
                      └──────────────────────────────────┴────────────┘
                                                                ALE created
                                                                (every transition)
```

| Transition | Trigger | Service | Side-effects |
|---|---|---|---|
| → Open | `create_repair_work_order` | API + `before_insert` controller | Validate BR-09-01; set sla_target; Asset → Under Repair; ALE `repair_opened` |
| Open → Assigned | `assign_technician` | API | Set assigned_to / assigned_datetime |
| Assigned → Diagnosing | (auto or `start_repair`) | controller | — |
| Diagnosing → Pending Parts | `submit_diagnosis(needs_parts=1)` | API | ALE `diagnosis_submitted` |
| Diagnosing → In Repair | `submit_diagnosis(needs_parts=0)` | API | ALE `diagnosis_submitted` |
| Pending Parts → In Repair | `request_spare_parts` (parts confirmed) | API | Set stock_entry_ref |
| In Repair → Pending Inspection | `close_work_order` (pre-submit) | API | Fill repair_summary, checklist |
| Pending Inspection → Completed | `doc.submit()` qua `close_work_order` | controller `on_submit` → `complete_repair()` | Tính MTTR, sla_breached, Asset → Active, ALE `repair_completed` |
| In Repair → Cannot Repair | `close_work_order(cannot_repair=1)` | API → `_mark_cannot_repair()` | Asset → Out of Service, ALE `cannot_repair` |
| any → Cancelled | manual (Workshop Manager) | controller | — |

---

## 5. Data Dictionary

### 5.1 Asset Repair (`WO-CM-.YYYY.-.#####`, submittable)

| Field | Type | Reqd | Notes |
|---|---|---|---|
| `asset_ref` | Link Asset | Y | search_index, in_list_view |
| `asset_name` | Data | — | fetch_from `asset_ref.asset_name` |
| `asset_category` | Data | — | fetch_from `asset_ref.asset_category` |
| `risk_class` | Select (Class I/II/III) | — | read_only; set khi create |
| `serial_no` | Data | — | read_only |
| `incident_report` | Link Incident Report | (BR-09-01) | OR `source_pm_wo` |
| `source_pm_wo` | Link PM Work Order | (BR-09-01) | OR `incident_report` |
| `repair_type` | Select (Corrective / Emergency / Warranty Repair) | Y | in_list_view |
| `priority` | Select (Normal / Urgent / Emergency) | Y | default Normal, in_list_view |
| `status` | Select (9 states) | — | default Open, in_list_view |
| `open_datetime` | Datetime | — | auto = `now()` `before_insert` |
| `assigned_datetime` | Datetime | — | auto khi `assign_technician` |
| `completion_datetime` | Datetime | — | auto = `now()` khi `complete_repair()` |
| `sla_target_hours` | Float | — | auto từ `get_sla_target` |
| `mttr_hours` | Float | — | auto = `(completion − open) / 3600` |
| `sla_breached` | Check | — | auto = 1 nếu `mttr_hours > sla_target_hours` |
| `is_repeat_failure` | Check | — | auto từ `check_repeat_failure()` (30 days lookback) |
| `assigned_to` | Link User | — | KTV thực hiện |
| `assigned_by` | Link User | — | read_only |
| `diagnosis_notes` | Text | — | KTV điền |
| `root_cause_category` | Select (6 options) | — | Mechanical / Electrical / Software / User Error / Wear and Tear / Unknown |
| `repair_summary` | Text | (close) | reqd khi Completed |
| `spare_parts_used` | Table → Spare Parts Used | — | child |
| `total_parts_cost` | Currency | — | auto = Σ row.total_cost |
| `repair_checklist` | Table → Repair Checklist | (close) | child; reqd khi Completed |
| `firmware_updated` | Check | — | trigger BR-09-03 |
| `firmware_change_request` | Link FCR | (BR-09-03) | reqd khi `firmware_updated=1` |
| `dept_head_name` | Data | (close) | reqd khi Completed |
| `dept_head_confirmation_datetime` | Datetime | — | auto = `now()` khi close |
| `is_warranty_claim` | Check | — | — |
| `warranty_claim_ref` | Data | — | — |
| `cannot_repair_reason` | Text | (cannot_repair) | reqd khi Cannot Repair |
| `technician_notes` | Text | — | optional KTV note |
| `attachments` | Attach Multiple | — | ảnh trước/sau |

### 5.2 Spare Parts Used (child)

| Field | Type | Reqd | Notes |
|---|---|---|---|
| `item_code` | Link Item | Y | in_list_view |
| `item_name` | Data | — | fetch_from `item_code.item_name`, read_only |
| `qty` | Float | Y | in_list_view |
| `uom` | Link UOM | Y | — |
| `unit_cost` | Currency | Y | in_list_view |
| `total_cost` | Currency | — | auto = qty × unit_cost trong `_compute_parts_cost` |
| `stock_entry_ref` | Link Stock Entry | Y | **BR-09-02** |
| `notes` | Text | — | — |

### 5.3 Repair Checklist (child)

| Field | Type | Reqd | Notes |
|---|---|---|---|
| `test_description` | Data | Y | in_list_view |
| `test_category` | Select (Electrical/Mechanical/Software/Safety/Performance) | Y | in_list_view |
| `expected_value` | Data | — | — |
| `measured_value` | Data | — | — |
| `result` | Select (Pass/Fail/N/A) | Y (close) | in_list_view; **BR-09-04** |
| `notes` | Text | — | — |
| `photo` | Attach | — | — |

### 5.4 Firmware Change Request (`FCR-.YYYY.-.#####`, submittable)

| Field | Type | Reqd | Notes |
|---|---|---|---|
| `asset` | Link Asset | Y | — |
| `repair_wo` | Link Asset Repair | Y | — |
| `version_before` | Data | Y | — |
| `version_after` | Data | Y | — |
| `change_notes` | Text | Y | — |
| `status` | Select (Draft / Pending Approval / Approved / Applied / Rolled Back) | Y | — |
| `approved_by` | Link User | (Approve) | reqd on Approve |

---

## 6. Controller Hooks

File: `assetcore/assetcore/doctype/asset_repair/asset_repair.py`

| Hook | Service Function gọi | Mục đích |
|---|---|---|
| `before_insert` | `validate_repair_source(self)` | BR-09-01 |
| `before_insert` | `validate_asset_not_under_repair(self.asset_ref)` | Chặn duplicate |
| `before_insert` | `check_repeat_failure(self.asset_ref)` → set `is_repeat_failure` | BR-09-06 |
| `before_insert` | `self.open_datetime = now_datetime()` | Audit timestamp |
| `on_insert` | `set_asset_under_repair(self.asset_ref, self.name)` | BR-09-05 |
| `validate` | `_compute_parts_cost(self)` | Tính `total_parts_cost` + `row.total_cost` |
| `before_submit` | `validate_spare_parts_stock_entries(self)` | BR-09-02 |
| `before_submit` | `validate_firmware_change_request(self)` | BR-09-03 |
| `before_submit` | `validate_repair_checklist_complete(self)` | BR-09-04 |
| `on_submit` | `complete_repair(self)` | MTTR, SLA breach, Asset → Active, ALE `repair_completed` |

**ERPNext compatibility shims** (vì Frappe core / một số hooks ngoài có thể đọc field ERPNext-style):

- `completion_date` (property) ↔ `completion_datetime`
- `company` (property fallback) ↔ `frappe.defaults.get_global_default("company")`
- `posting_date` (property fallback) ↔ `open_datetime` / `nowdate()`

---

## 7. Service Layer

File: `assetcore/services/imm09.py` — 13 functions chính.

### 7.1 SLA Matrix

```python
def get_sla_target(risk_class: str, priority: str) -> float:
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

Default fallback **480 h** (20 ngày calendar).

### 7.2 MTTR Computation

```python
# Trong complete_repair(doc):
diff_seconds = time_diff_in_seconds(close_dt, open_dt)
doc.mttr_hours = round(diff_seconds / 3600.0, 2)
doc.sla_breached = 1 if doc.mttr_hours > doc.sla_target_hours else 0
```

> **Note:** v2.0 tính **calendar time** (không loại trừ ngày nghỉ). Util `get_working_hours_between` (Mon–Fri 07:00–17:00) đề xuất trong spec v1 chưa được implement — backlog cải tiến.

### 7.3 Repeat Failure Detection

```python
def check_repeat_failure(asset_ref: str) -> bool:
    cutoff_date = add_days(nowdate(), -30)
    return bool(frappe.db.exists("Asset Repair", {
        "asset_ref": asset_ref,
        "status": "Completed",
        "completion_datetime": (">=", cutoff_date),
        "docstatus": 1,
    }))
```

Set trong `before_insert`. KPI dùng để tính first-time fix rate.

### 7.4 Asset Lifecycle Event

Mọi transition gọi `_create_lifecycle_event(asset, event_type, from_status, to_status, root_record, notes)`. Insert vào `Asset Lifecycle Event` (immutable). Wrap try/except (lifecycle event failure không block main op).

Event types: `repair_opened`, `diagnosis_submitted`, `repair_completed`, `cannot_repair`.

---

## 8. Scheduler Hooks

File: `assetcore/hooks.py` (đăng ký)

```python
scheduler_events = {
    "hourly": [ "assetcore.services.imm09.check_repair_sla_breach" ],
    "daily":  [ "assetcore.services.imm09.check_repair_overdue" ],
    "monthly": [ "assetcore.services.imm09.update_asset_mttr_avg" ],
}
```

| Job | Tần suất | Logic |
|---|---|---|
| `check_repair_sla_breach` | Hourly | Loop active WOs (status IN [Assigned, Diagnosing, Pending Parts, In Repair]); nếu `elapsed_h ≥ sla` → set `sla_breached=1` + `frappe.publish_realtime("cm_sla_breached", {wo, asset}, user=assigned_to)` |
| `check_repair_overdue` | Daily 07:00 | WO có `open_datetime < today − 7d` AND `status IN (Open, Assigned, Pending Parts)` → email Workshop Manager |
| `update_asset_mttr_avg` | Monthly day 01 06:00 | SQL window function (12 WO Completed gần nhất per asset) → `Asset.custom_mttr_avg_hours` |

---

## 9. Indexes & Performance

| Table | Index | Mục đích |
|---|---|---|
| `tabAsset Repair` | `asset_ref` (search_index) | Lookup history per asset |
| `tabAsset Repair` | `(status, docstatus)` composite | Filter active WO cho scheduler |
| `tabAsset Repair` | `open_datetime` desc | Sort danh sách + KPI tháng |
| `tabAsset Repair` | `completion_datetime` | KPI tháng range query |
| `tabAsset Repair` | `(asset_ref, status, completion_datetime)` | `check_repeat_failure` lookup |
| `tabSpare Parts Used` | `parent` (default Frappe) + `stock_entry_ref` | Validate BR-09-02 |
| `tabRepair Checklist` | `parent` | Iterate checklist |

Khuyến nghị thêm composite index `(asset_ref, status, completion_datetime)` qua patch khi data > 10k WO.

---

## 10. Security & Permissions

| Aspect | Implementation |
|---|---|
| Role-based perm | DocType JSON `permissions[]` (HTM Technician / Workshop Manager / CMMS Admin) |
| Permission Query | `permission.py` filter HTM Technician → chỉ thấy WO `assigned_to = session.user` |
| Audit trail | Frappe `track_changes: 1` + Asset Lifecycle Event (immutable) |
| Submittable lock | `is_submittable: 1` — sau Submit không sửa/xoá; cancel cần Workshop Manager + lý do |
| `ignore_permissions=True` | Dùng tạm trong service layer khi thao tác cross-doctype (Asset, Stock Entry); production cần audit lại |
| API auth | Token + Session; `@frappe.whitelist()` enforces login |

---

## 11. Migration & Rollout

| Bước | Hạng mục | Trạng thái |
|---|---|---|
| 11.1 | Tạo DocType JSON + controller (4 doctype) | LIVE |
| 11.2 | Service layer + scheduler hooks | LIVE |
| 11.3 | API layer (12 endpoints) | LIVE |
| 11.4 | Permission fixtures (HTM Technician / Workshop Manager / Kho vật tư) | LIVE |
| 11.5 | Frontend Vue 3 (7 views + Pinia store) | LIVE |
| 11.6 | Patch: backfill `is_repeat_failure` cho WO cũ | DRAFT |
| 11.7 | Patch: tính lại `mttr_hours` cho WO Completed thiếu data | DRAFT |
| 11.8 | Migrate sang `get_working_hours_between` (loại trừ ngày lễ) | BACKLOG |
| 11.9 | Bổ sung `search_spare_parts` endpoint chính thức | BACKLOG |
| 11.10 | Workflow JSON cho Frappe Workflow Engine (optional) | BACKLOG |

### 11.1 Migrate từ v1 (extend ERPNext Asset Repair) sang v2 (DocType native)

- DocType v1 dùng schema ERPNext `Asset Repair` + custom fields → v2 tách hẳn DocType `Asset Repair` riêng trong module AssetCore.
- Controller v2 thêm shim ERPNext-compat (xem §6) để tránh break các hook ngoài.
- Data migration: nếu hospital đã có v1 records → patch script `patches/v2_0/migrate_asset_repair.py` (BACKLOG).

---

*End of Technical Design v2.0.0 — IMM-09 Corrective Maintenance.*
