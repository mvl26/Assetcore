# IMM-01 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh Giá Nhu Cầu & Dự Toán |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-21 |

---

## 1. DocType Schema

### 1.1 Needs Assessment

```json
{
  "name": "Needs Assessment",
  "module": "Assetcore",
  "naming_rule": "Expression",
  "autoname": "NA-.YY.-.MM.-.#####",
  "is_submittable": 1,
  "track_changes": 1,
  "fields": [
    {"fieldname": "requesting_dept", "fieldtype": "Link", "options": "AC Department", "label": "Khoa yêu cầu", "reqd": 1, "in_list_view": 1},
    {"fieldname": "request_date",    "fieldtype": "Date",    "label": "Ngày lập",       "reqd": 1, "default": "Today"},
    {"fieldname": "requested_by",    "fieldtype": "Link",    "options": "User",          "label": "Người đề xuất","reqd": 1},
    {"fieldname": "equipment_type",  "fieldtype": "Data",    "label": "Loại thiết bị",  "reqd": 1, "in_list_view": 1},
    {"fieldname": "linked_device_model","fieldtype": "Link", "options": "IMM Device Model","label": "Model thiết bị"},
    {"fieldname": "quantity",        "fieldtype": "Int",     "label": "Số lượng",       "reqd": 1, "default": 1},
    {"fieldname": "priority",        "fieldtype": "Select",  "label": "Ưu tiên",
      "options": "Critical\nHigh\nMedium\nLow", "reqd": 1, "default": "Medium", "in_list_view": 1},
    {"fieldname": "clinical_justification","fieldtype": "Text Editor","label": "Lý do y tế","reqd": 1},
    {"fieldname": "current_equipment_age","fieldtype": "Int","label": "Tuổi thiết bị hiện tại (năm)"},
    {"fieldname": "failure_frequency","fieldtype": "Select", "label": "Tần suất hỏng hóc",
      "options": "Never\nRarely\nMonthly\nWeekly\nDaily"},
    {"fieldname": "estimated_budget","fieldtype": "Currency","label": "Dự toán (VND)",  "reqd": 1},
    {"fieldname": "section_review",  "fieldtype": "Section Break","label": "Đánh giá HTM"},
    {"fieldname": "htmreview_notes", "fieldtype": "Text",    "label": "Nhận xét HTM"},
    {"fieldname": "finance_notes",   "fieldtype": "Text",    "label": "Nhận xét tài chính"},
    {"fieldname": "approved_budget", "fieldtype": "Currency","label": "Ngân sách được duyệt"},
    {"fieldname": "reject_reason",   "fieldtype": "Text",    "label": "Lý do từ chối"},
    {"fieldname": "section_lifecycle","fieldtype": "Section Break","label": "Lịch sử"},
    {"fieldname": "lifecycle_events","fieldtype": "Table",   "options": "Asset Lifecycle Event","label": "Sự kiện vòng đời"},
    {"fieldname": "status",          "fieldtype": "Select",
      "options": "Draft\nSubmitted\nUnder Review\nApproved\nRejected\nPlanned",
      "default": "Draft", "read_only": 1, "in_list_view": 1}
  ],
  "permissions": [
    {"role": "HTM Technician",  "read": 1, "write": 1, "create": 1},
    {"role": "Biomed Engineer", "read": 1, "write": 1, "create": 1},
    {"role": "HTM Manager",     "read": 1, "write": 1, "submit": 1, "cancel": 1},
    {"role": "Workshop Head",   "read": 1, "write": 1, "submit": 1, "cancel": 1},
    {"role": "CMMS Admin",      "read": 1, "write": 1, "submit": 1, "cancel": 1, "delete": 1}
  ]
}
```

---

## 2. Service Functions

File: `assetcore/services/imm01.py` (to be created as needed)

| Function | Caller | Mục đích |
|---|---|---|
| `validate_needs_assessment(doc)` | `validate()` hook | VR-01-01 → VR-01-04 |
| `_vr01_duplicate_check(doc)` | validate | Kiểm tra trùng yêu cầu cùng khoa cùng năm |
| `_vr02_budget_range(doc)` | validate | 0 < budget ≤ 50B VND |
| `_vr03_quantity_range(doc)` | validate | 1 ≤ qty ≤ 100 |
| `_vr04_justification_length(doc)` | validate | ≥ 50 ký tự khi submit |
| `on_submit(doc)` | `on_submit` hook | Tạo lifecycle event "needs_assessment_approved" |

---

## 3. Workflow Transitions

| Transition | From | To | Actor Role | Guard |
|---|---|---|---|---|
| submit_for_review | Draft | Submitted | Department Head | VR-01-03, VR-01-04 |
| start_review | Submitted | Under Review | HTM Manager | — |
| approve | Under Review | Approved | Finance Director | htmreview_notes filled |
| reject | Under Review | Rejected | HTM Manager / Finance | reason required |
| plan | Approved | Planned | HTM Manager | linked to PP item |

---

## 4. Hooks

```python
# hooks.py additions
doc_events = {
    "Needs Assessment": {
        "validate": "assetcore.assetcore.doctype.needs_assessment.needs_assessment.validate",
        "on_submit": "assetcore.assetcore.doctype.needs_assessment.needs_assessment.on_submit",
    }
}
```

---

## 5. Lifecycle Events

| Event Type | Trigger | from_status | to_status |
|---|---|---|---|
| needs_assessment_created | on_insert | — | Draft |
| submitted_for_review | submit_for_review API | Draft | Submitted |
| review_started | start_review API | Submitted | Under Review |
| approved | approve API | Under Review | Approved |
| rejected | reject API | Under Review | Rejected |
| added_to_plan | plan API | Approved | Planned |
