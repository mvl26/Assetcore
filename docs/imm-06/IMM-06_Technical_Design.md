# IMM-06 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — Bàn giao & Đào tạo |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. DocType Schema

### 1.1 Handover Record

| Field | Fieldtype | Options / Reqd | Mô tả |
|---|---|---|---|
| `name` | — | autoname: `HR-.YY.-.MM.-.#####` | Khóa chính |
| `workflow_state` | Data | — | Quản lý bởi Frappe Workflow |
| `status` | Select | Draft/Training Scheduled/Training Completed/Handover Pending/Handed Over/Cancelled; reqd | Mirror workflow |
| `commissioning_ref` | Link | Asset Commissioning; reqd | Liên kết phiếu nghiệm thu |
| `asset` | Link | AC Asset; reqd; fetch_from: commissioning_ref.final_asset | Fetch từ commissioning |
| `clinical_dept` | Link | AC Department; reqd | Khoa nhận thiết bị |
| `handover_date` | Date | reqd | Ngày bàn giao kế hoạch |
| `received_by` | Link | User; reqd | Người đại diện nhận |
| `handover_type` | Select | Full/Conditional/Temporary; reqd | Loại bàn giao |
| `conditions_if_conditional` | Text | — | Điều kiện nếu Conditional |
| `htm_engineer_signoff` | Link | User | Chữ ký kỹ sư HTM |
| `dept_head_signoff` | Link | User | Chữ ký Trưởng khoa |
| `handover_notes` | Text Editor | — | Ghi chú bàn giao |
| `is_submittable` | — | 1 | Submittable DocType |

### 1.2 Training Session

| Field | Fieldtype | Options / Reqd | Mô tả |
|---|---|---|---|
| `name` | — | autoname: `TS-.YY.-.MM.-.#####` | Khóa chính |
| `handover_ref` | Link | Handover Record; reqd | Liên kết phiếu bàn giao |
| `asset` | Link | AC Asset; fetch_from: handover_ref.asset | Fetch |
| `training_type` | Select | Operation/Safety/Emergency/Maintenance/Full; reqd | Loại đào tạo |
| `trainer_type` | Select | HTM/Vendor; reqd | Nguồn đào tạo |
| `trainer` | Link | User; reqd | Người đào tạo |
| `training_date` | Date; reqd | Ngày đào tạo |
| `duration_hours` | Float | — | Thời lượng (giờ) |
| `venue` | Data | — | Địa điểm |
| `materials_url` | Data | — | URL tài liệu |
| `trainees` | Table | Training Trainee | Danh sách học viên |
| `competency_confirmed` | Check | — | Tất cả đạt |
| `notes` | Text | — | Ghi chú |
| `status` | Select | Scheduled/Completed/Cancelled | Trạng thái buổi học |

### 1.3 Training Trainee (child table)

| Field | Fieldtype | Reqd | Mô tả |
|---|---|---|---|
| `trainee_user` | Link → User | Yes | Học viên |
| `full_name` | Data | — | Tên đầy đủ |
| `role` | Data | — | Vai trò |
| `attendance` | Select (Present/Absent) | — | Điểm danh |
| `score` | Float | — | Điểm số (0-100) |
| `passed` | Check | — | Đạt (score ≥ 70) |

---

## 2. Workflow

File: `assetcore/workflows/imm_06_workflow.json` — `IMM-06 Workflow`
`workflow_state_field = workflow_state`
`document_type = Handover Record`

### States

| State | doc_status | Style | allowed_edit |
|---|---|---|---|
| Draft | 0 | — | HTM Technician / Biomed Engineer |
| Training Scheduled | 0 | primary | Biomed Engineer / Vendor Engineer |
| Training Completed | 0 | success | Biomed Engineer / QA Officer |
| Handover Pending | 0 | warning | Dept Head |
| Handed Over | 1 | success | System Manager |
| Cancelled | 2 | danger | CMMS Admin |

### Transitions

| Action | From | To | Allowed Role |
|---|---|---|---|
| Lên lịch đào tạo | Draft | Training Scheduled | HTM Technician / Biomed Engineer |
| Xác nhận hoàn thành đào tạo | Training Scheduled | Training Completed | Biomed Engineer / QA Officer |
| Huỷ lịch | Training Scheduled | Draft | HTM Technician |
| Gửi bàn giao | Training Completed | Handover Pending | Biomed Engineer |
| Ký nhận bàn giao | Handover Pending | Handed Over | Dept Head / CMMS Admin |
| Yêu cầu đào tạo thêm | Handover Pending | Training Scheduled | QA Officer |
| Huỷ bỏ | Draft | Cancelled | CMMS Admin |

---

## 3. Controller Hooks

File: `assetcore/assetcore/doctype/handover_record/handover_record.py`

```python
def before_insert(self):
    # VR-01: validate commissioning is Clinical Release
    # Fetch asset from commissioning_ref

def validate(self):
    # VR-02: no duplicate Handed Over for same asset
    # VR-03: gate — training required before Handover Pending
    # Sync status field with workflow_state

def before_submit(self):
    # VR-04: dept_head_signoff bắt buộc

def on_submit(self):
    # Log lifecycle event: handover_completed
    # Update asset.current_dept if applicable

def on_cancel(self):
    # Block cancel if Handed Over
```

---

## 4. Service Functions

File: `assetcore/services/imm06.py`

| Function | Signature | Logic |
|---|---|---|
| `create_handover_record` | `(commissioning_ref, clinical_dept, handover_date, received_by, handover_type)` | Validate VR-01, insert Handover Record |
| `get_handover_record` | `(name)` | Get record + linked training sessions |
| `list_handover_records` | `(filters, page, page_size)` | Paginated list |
| `schedule_training` | `(handover_name, training_type, trainer, training_date, duration_hours, trainees)` | Insert Training Session |
| `complete_training` | `(session_name, scores, notes)` | Update trainee scores, set competency_confirmed |
| `confirm_handover` | `(name, dept_head_signoff, notes)` | VR-04, submit doc |
| `get_asset_training_history` | `(asset_name)` | All Training Sessions for asset |
| `get_dashboard_stats` | `()` | KPI counts by status |

---

## 5. Database Indexes

```sql
-- Handover Record
CREATE INDEX idx_hr_asset ON `tabHandover Record` (asset);
CREATE INDEX idx_hr_commissioning ON `tabHandover Record` (commissioning_ref);
CREATE INDEX idx_hr_status ON `tabHandover Record` (status);

-- Training Session
CREATE INDEX idx_ts_handover ON `tabTraining Session` (handover_ref);
CREATE INDEX idx_ts_asset ON `tabTraining Session` (asset);
```

---

## 6. Lifecycle Events Created

| Event Type | Trigger | From Status | To Status |
|---|---|---|---|
| `handover_completed` | `on_submit` | Handover Pending | Handed Over |
| `training_scheduled` | `schedule_training()` | — | Training Scheduled |
| `training_completed` | `complete_training()` | — | Training Completed |

*End of Technical Design v1.0.0 — IMM-06*
