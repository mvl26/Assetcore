# IMM-07 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-07 — Vận hành hàng ngày |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. DocType Schema

### 1.1 Daily Operation Log

| Field | Fieldtype | Options / Reqd | Mô tả |
|---|---|---|---|
| `name` | — | autoname: `DOL-.YY.-.MM.-.DD.-.#####` | Khóa chính |
| `workflow_state` | Data | — | Quản lý bởi Frappe Workflow |
| `asset` | Link | AC Asset; reqd | Thiết bị |
| `log_date` | Date | reqd; default today | Ngày ca trực |
| `shift` | Select | Morning 06-14/Afternoon 14-22/Night 22-06; reqd | Ca trực |
| `operated_by` | Link | User; reqd | Người vận hành |
| `dept` | Link | AC Department | Khoa thực hiện |
| `start_meter_hours` | Float | — | Số giờ máy đầu ca |
| `end_meter_hours` | Float | — | Số giờ máy cuối ca |
| `runtime_hours` | Float | read_only | Tính tự động: end - start |
| `usage_cycles` | Int | — | Số chu kỳ sử dụng |
| `operational_status` | Select | Running/Standby/Fault/Under Maintenance/Not Used; reqd | Trạng thái ca |
| `anomaly_detected` | Check | — | Có bất thường |
| `anomaly_type` | Select | None/Minor/Major/Critical | Mức độ bất thường |
| `anomaly_description` | Text | — | Mô tả bất thường |
| `linked_incident` | Link | Incident Report | Liên kết sự cố |
| `reviewed_by` | Link | User | Người review |
| `review_date` | Date | — | Ngày review |
| `is_submittable` | — | 1 | Submittable DocType |

---

## 2. Workflow

File: `assetcore/workflows/imm_07_workflow.json` — `IMM-07 Workflow`
`document_type = Daily Operation Log`

### States

| State | doc_status | Style | allowed_edit |
|---|---|---|---|
| Open | 0 | — | Clinical Operator / Nurse |
| Logged | 0 | primary | Clinical Operator / Nurse |
| Reviewed | 1 | success | Dept Head / HTM Tech |

### Transitions

| Action | From | To | Role |
|---|---|---|---|
| Nộp nhật ký ca | Open | Logged | Clinical Operator / Nurse |
| Phê duyệt ca | Logged | Reviewed | Dept Head / HTM Tech |
| Yêu cầu chỉnh sửa | Logged | Open | Dept Head |

---

## 3. Controller Hooks

File: `assetcore/assetcore/doctype/daily_operation_log/daily_operation_log.py`

```python
def before_save(self):
    # Compute runtime_hours = end_meter - start_meter

def validate(self):
    # VR-01: unique per asset/date/shift
    # VR-02: end_meter >= start_meter
    # VR-03: anomaly_detected=1 → description required

def on_submit(self):
    # If anomaly Major/Critical → create Incident Report
    # Log lifecycle event: operation_logged
    # Update linked_incident if created
```

---

## 4. Service Functions

File: `assetcore/services/imm07.py`

| Function | Signature | Logic |
|---|---|---|
| `create_daily_log` | `(asset, log_date, shift, operated_by, operational_status, ...)` | Validate + insert |
| `get_daily_log` | `(name)` | Get record |
| `list_daily_logs` | `(filters, page, page_size)` | Paginated list |
| `submit_log` | `(name)` | Validate + submit, trigger incident if needed |
| `review_log` | `(name, reviewer_notes)` | Set reviewed_by, review_date, transition |
| `get_asset_operation_summary` | `(asset_name, days)` | Aggregate runtime, uptime%, anomaly |
| `get_dashboard_stats` | `(dept)` | Group by operational_status for today |
| `report_anomaly_from_log` | `(log_name, severity, description)` | Insert Incident Report |
| `_create_incident_from_log` | `(log_doc)` | Internal — insert Incident Report |
| `validate_single_log_per_shift` | `(doc)` | VR-01 unique check |
| `validate_meter_hours` | `(doc)` | VR-02 |
| `compute_runtime_hours` | `(doc)` | end - start; floor to 0 |

---

## 5. Database Indexes

```sql
-- Daily Operation Log
CREATE INDEX idx_dol_asset_date ON `tabDaily Operation Log` (asset, log_date);
CREATE INDEX idx_dol_shift ON `tabDaily Operation Log` (shift);
CREATE INDEX idx_dol_status ON `tabDaily Operation Log` (operational_status);
CREATE INDEX idx_dol_dept ON `tabDaily Operation Log` (dept);
-- Composite unique for VR-01
CREATE UNIQUE INDEX idx_dol_unique_shift
  ON `tabDaily Operation Log` (asset, log_date, shift, docstatus)
  WHERE docstatus != 2;
```

---

## 6. Incident Auto-creation Logic

Khi `on_submit` và `anomaly_type IN ("Major", "Critical")`:

```python
incident = frappe.get_doc({
    "doctype": "Incident Report",
    "asset": doc.asset,
    "reported_by": doc.operated_by,
    "report_date": doc.log_date,
    "severity": doc.anomaly_type,
    "description": doc.anomaly_description,
    "source_module": "IMM-07",
    "source_log": doc.name,
})
incident.insert(ignore_permissions=True)
doc.db_set("linked_incident", incident.name, commit=True)
```

---

## 7. Lifecycle Events Created

| Event Type | Trigger | Notes |
|---|---|---|
| `operation_logged` | `on_submit` | Per log submission |
| `anomaly_reported` | `on_submit` (if anomaly) | Linked to incident |

*End of Technical Design v1.0.0 — IMM-07*
