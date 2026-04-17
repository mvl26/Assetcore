# ASSETCORE — MASTER BUILD PROMPT
# Dành cho Claude Code — Tầng 1 + Tầng 2
# Chạy một lần, output hoàn chỉnh

---

## NHIỆM VỤ TỔNG QUÁT

Bạn là Senior Frappe/ERPNext Developer. Nhiệm vụ của bạn là xây dựng **Foundation (Tầng 1 + Tầng 2)** của ứng dụng Frappe có tên `assetcore` — hệ thống quản lý vòng đời tài sản thiết bị y tế cho bệnh viện Việt Nam.

Hãy đọc file `CLAUDE.md` ngay bây giờ trước khi làm bất cứ điều gì.

Sau đó thực hiện tuần tự tất cả các Task dưới đây theo đúng thứ tự.

---

## TASK 0 — KHỞI TẠO APP VÀ CẤU TRÚC

```bash
# Tạo Frappe app mới
cd /home/frappe/frappe-bench
bench new-app assetcore \
  --no-git-init \
  --app-description "AssetCore - Medical Device Lifecycle Management System" \
  --app-publisher "BVND1 IT Team" \
  --app-email "it@bvnd1.vn" \
  --app-license "MIT"
```

Sau khi tạo app, tạo cấu trúc thư mục sau:

```
assetcore/assetcore/
├── imm_master/
│   ├── __init__.py
│   └── doctype/
├── imm_deployment/
│   ├── __init__.py
│   ├── doctype/
│   └── scheduler.py
├── imm_operations/
│   ├── __init__.py
│   ├── doctype/
│   └── scheduler.py
├── imm_planning/
│   ├── __init__.py
│   └── doctype/
└── imm_eol/
    ├── __init__.py
    └── doctype/
```

Tạo/cập nhật các file cấu hình sau:

### modules.txt
```
IMM Master
IMM Deployment
IMM Operations
IMM Planning
IMM EOL
```

### hooks.py — thêm vào cuối file hiện có

```python
# ============================================================
# AssetCore Hooks
# ============================================================

app_name = "assetcore"
app_title = "AssetCore"
app_publisher = "BVND1"
app_description = "Medical Device Lifecycle Management"
app_version = "0.1.0"

# Fixtures — load theo thứ tự
fixtures = [
    {"dt": "Custom Field", "filters": [["dt", "in", ["Asset"]]]},
    {"dt": "Role", "filters": [["role_name", "like", "IMM%"]]},
    {"dt": "Workflow", "filters": [["document_type", "like", "IMM%"]]},
]

# Scheduler
scheduler_events = {
    "daily": [
        "assetcore.imm_operations.scheduler.check_pm_due_dates",
        "assetcore.imm_operations.scheduler.check_calibration_expiry",
        "assetcore.imm_deployment.scheduler.check_document_expiry",
        "assetcore.imm_operations.scheduler.escalate_overdue_wo",
    ],
    "hourly": [
        "assetcore.imm_operations.scheduler.sync_asset_lifecycle_status",
    ],
}

# DocType events
doc_events = {
    "Asset": {
        "on_update": "assetcore.imm_master.utils.on_asset_update",
    }
}

# Permissions
has_permission = {
    "IMM PM Work Order": "assetcore.imm_operations.permission.has_permission",
    "IMM CM Work Order": "assetcore.imm_operations.permission.has_permission",
}
```

---

## TASK 1 — TẠO ROLES

Tạo file `assetcore/fixtures/roles.json`:

```json
[
  {"doctype": "Role", "role_name": "IMM Department Head", "desk_access": 1},
  {"doctype": "Role", "role_name": "IMM Operations Manager", "desk_access": 1},
  {"doctype": "Role", "role_name": "IMM Technician", "desk_access": 1},
  {"doctype": "Role", "role_name": "IMM Document Officer", "desk_access": 1},
  {"doctype": "Role", "role_name": "IMM Workshop Lead", "desk_access": 1},
  {"doctype": "Role", "role_name": "IMM Storekeeper", "desk_access": 1},
  {"doctype": "Role", "role_name": "IMM QA Officer", "desk_access": 1},
  {"doctype": "Role", "role_name": "IMM System Admin", "desk_access": 1}
]
```

---

## TASK 2 — CUSTOM FIELDS CHO CORE ASSET DOCTYPE

Tạo file `assetcore/fixtures/custom_fields_asset.json` với nội dung là danh sách Custom Field cho DocType `Asset`. Các field cần thêm:

```python
# Tạo danh sách JSON cho custom fields sau vào tabAsset:

custom_fields = [
    # --- Section: IMM Identity ---
    {
        "fieldname": "imm_identity_section",
        "label": "IMM — Định danh thiết bị",
        "fieldtype": "Section Break",
        "insert_after": "asset_name",
        "collapsible": 0,
    },
    {
        "fieldname": "imm_device_model",
        "label": "Model thiết bị (IMM)",
        "fieldtype": "Link",
        "options": "IMM Device Model",
        "insert_after": "imm_identity_section",
        "in_list_view": 1,
        "in_standard_filter": 1,
    },
    {
        "fieldname": "imm_medical_device_class",
        "label": "Phân loại thiết bị y tế",
        "fieldtype": "Select",
        "options": "\nClass I\nClass II\nClass III",
        "insert_after": "imm_device_model",
    },
    {
        "fieldname": "imm_registration_number",
        "label": "Số đăng ký BYT",
        "fieldtype": "Data",
        "insert_after": "imm_medical_device_class",
        "in_standard_filter": 1,
    },
    {
        "fieldname": "imm_serial_number_manufacturer",
        "label": "Serial Number (nhà sản xuất)",
        "fieldtype": "Data",
        "insert_after": "imm_registration_number",
        "in_list_view": 1,
    },
    {
        "fieldname": "imm_col_break_1",
        "fieldtype": "Column Break",
        "insert_after": "imm_serial_number_manufacturer",
    },
    {
        "fieldname": "imm_lifecycle_status",
        "label": "Trạng thái vòng đời (IMM)",
        "fieldtype": "Select",
        "options": "\nCommissioning\nActive\nUnder Repair\nCalibrating\nInactive\nDecommissioned",
        "insert_after": "imm_col_break_1",
        "in_list_view": 1,
        "in_standard_filter": 1,
        "default": "Commissioning",
    },
    {
        "fieldname": "imm_risk_class",
        "label": "Mức độ rủi ro",
        "fieldtype": "Select",
        "options": "\nLow\nMedium\nHigh\nCritical",
        "insert_after": "imm_lifecycle_status",
    },
    {
        "fieldname": "imm_department",
        "label": "Khoa/Phòng sử dụng",
        "fieldtype": "Link",
        "options": "Department",
        "insert_after": "imm_risk_class",
        "in_list_view": 1,
        "in_standard_filter": 1,
    },
    {
        "fieldname": "imm_responsible_technician",
        "label": "Kỹ thuật viên phụ trách",
        "fieldtype": "Link",
        "options": "User",
        "insert_after": "imm_department",
    },
    # --- Section: IMM Maintenance Schedule ---
    {
        "fieldname": "imm_maintenance_section",
        "label": "IMM — Lịch bảo trì & hiệu chuẩn",
        "fieldtype": "Section Break",
        "insert_after": "imm_responsible_technician",
        "collapsible": 1,
    },
    {
        "fieldname": "imm_last_pm_date",
        "label": "Ngày bảo trì định kỳ cuối",
        "fieldtype": "Date",
        "insert_after": "imm_maintenance_section",
        "read_only": 1,
    },
    {
        "fieldname": "imm_next_pm_date",
        "label": "Ngày bảo trì định kỳ tiếp theo",
        "fieldtype": "Date",
        "insert_after": "imm_last_pm_date",
        "in_standard_filter": 1,
    },
    {
        "fieldname": "imm_pm_col_break",
        "fieldtype": "Column Break",
        "insert_after": "imm_next_pm_date",
    },
    {
        "fieldname": "imm_last_calibration_date",
        "label": "Ngày hiệu chuẩn cuối",
        "fieldtype": "Date",
        "insert_after": "imm_pm_col_break",
        "read_only": 1,
    },
    {
        "fieldname": "imm_next_calibration_date",
        "label": "Ngày hiệu chuẩn tiếp theo",
        "fieldtype": "Date",
        "insert_after": "imm_last_calibration_date",
        "in_standard_filter": 1,
    },
]
```

Chuyển danh sách này thành JSON fixture chuẩn Frappe với dt="Custom Field" và document_type="Asset".

---

## TASK 3 — IMM DEVICE MODEL DOCTYPE (Master Data)

**Mục tiêu:** Quản lý danh mục model thiết bị y tế (tách khỏi asset instance)

Tạo DocType `IMM Device Model` trong module `imm_master`:

```
Fields:
  name                   → auto (naming series)
  naming_series          → IMM-MDL-.YYYY.-.####
  model_name             → Data, Required, in_list_view
  manufacturer           → Data, Required, in_standard_filter
  country_of_origin      → Data
  device_category        → Link → Asset Category
  medical_device_class   → Select: Class I / Class II / Class III, Required
  gmdn_code              → Data (Global Medical Device Nomenclature)
  hsn_code               → Data (mã HS theo BYT Việt Nam)
  risk_classification    → Select: Low / Medium / High / Critical
  
  --- Section: Thông số kỹ thuật ---
  power_supply           → Data (ví dụ: 220V/50Hz)
  operating_temperature  → Data
  storage_temperature    → Data
  weight_kg              → Float
  dimensions             → Data
  
  --- Section: Bảo trì ---
  recommended_pm_frequency → Select: Monthly/Quarterly/Semi-annual/Annual
  recommended_calibration_frequency → Select: 6 months/Annual/2 years/3 years/5 years
  expected_lifespan_years → Int
  
  --- Section: Hồ sơ ---
  registration_required  → Check
  typical_documents      → Small Text (mô tả loại hồ sơ cần có)
  
  --- Section: Ghi chú ---
  notes                  → Text Editor

Permissions:
  IMM Document Officer   → Read, Write, Create
  IMM Technician         → Read
  IMM Department Head    → Read, Write, Create, Delete
  IMM System Admin       → All
```

Tạo đủ: JSON DocType, Python controller, JS controller, test file.

Controller phải có:
- `validate()`: Kiểm tra model_name không trùng lặp với cùng manufacturer
- `before_save()`: Auto-set risk_classification từ medical_device_class nếu chưa set

---

## TASK 4 — IMM ASSET PROFILE DOCTYPE (Mở rộng Asset)

**Mục tiêu:** Hồ sơ kỹ thuật-pháp lý đầy đủ của một tài sản cụ thể, link về ERPNext Asset

Tạo DocType `IMM Asset Profile` trong module `imm_master`:

```
Fields:
  name                   → auto
  naming_series          → IMM-ASP-.YYYY.-.####
  asset                  → Link → Asset, Required, in_list_view (ERPNext core)
  asset_name             → Data, Fetch from asset.asset_name, Read Only
  device_model           → Link → IMM Device Model, Required
  
  --- Section: Định danh ---
  imm_asset_code         → Data, Required, Unique (mã tài sản nội bộ bệnh viện)
  barcode                → Data
  qr_code                → Data
  serial_number_manufacturer → Data (S/N nhà sản xuất)
  lot_number             → Data
  
  --- Section: Pháp lý ---
  registration_number    → Data (số đăng ký lưu hành BYT)
  registration_expiry    → Date
  import_permit_number   → Data (số phép nhập khẩu)
  
  --- Section: Vị trí & Sử dụng ---
  current_location       → Link → Location
  current_department     → Link → Department
  primary_user_group     → Data (nhóm người dùng chính: Bác sĩ/Điều dưỡng/KTV)
  
  --- Section: Vòng đời ---
  lifecycle_status       → Select: Commissioning/Active/Under Repair/
                                   Calibrating/Inactive/Decommissioned
                           Default: Commissioning
  commissioning_date     → Date
  decommission_date      → Date
  
  --- Section: Bảo trì ---
  pm_frequency           → Select: Monthly/Quarterly/Semi-annual/Annual
  last_pm_date           → Date, Read Only
  next_pm_date           → Date
  calibration_required   → Check
  calibration_frequency  → Select: 6 months/Annual/2 years/3 years
  last_calibration_date  → Date, Read Only
  next_calibration_date  → Date
  
  --- Section: Hồ sơ đính kèm ---
  document_attachments   → Child Table → IMM Profile Document (child table)
  
  --- Section: Ghi chú ---
  technical_notes        → Text Editor
  
  imm_status             → Select: Active/Inactive, Default: Active

Permissions:
  IMM Document Officer   → Read, Write, Create
  IMM Technician         → Read, Write (chỉ section bảo trì)
  IMM Workshop Lead      → Read, Write
  IMM Department Head    → Read, Write, Create, Delete
```

**Child Table — IMM Profile Document:**
```
Fields:
  document_type   → Select: Hợp đồng mua bán/Hóa đơn VAT/C/O/C/Q/
                            Giấy đăng ký lưu hành/Phép nhập khẩu/
                            Tài liệu kỹ thuật/Hướng dẫn sử dụng/
                            Biên bản bàn giao/Biên bản kiểm tra/Khác
  document_name   → Data, Required
  document_date   → Date
  expiry_date     → Date
  issuing_body    → Data (cơ quan cấp)
  document_number → Data
  attachment      → Attach
  notes           → Small Text
```

Controller `imm_asset_profile.py` phải:
- `validate()`: Kiểm tra imm_asset_code unique trong toàn hệ thống
- `on_submit()`: Sync lifecycle_status về Asset custom field `imm_lifecycle_status`
- `after_insert()`: Tạo entry trong `Asset Activity` với subject = "IMM Asset Profile created"

---

## TASK 5 — IMM AUDIT TRAIL DOCTYPE

**Mục tiêu:** Log mọi thay đổi trạng thái quan trọng trong hệ thống

Tạo DocType `IMM Audit Trail` trong module `imm_master`:

```
Fields:
  name             → auto
  asset            → Link → Asset, in_list_view, in_standard_filter
  asset_name       → Fetch from asset.asset_name, Read Only
  event_type       → Select: Status Change/Document Submitted/WO Created/
                             WO Completed/Calibration Done/Incident Reported/
                             Transfer/Decommission/System Event
  event_datetime   → Datetime, Required, Default: now
  from_status      → Data
  to_status        → Data
  reference_doctype → Link → DocType
  reference_name   → Dynamic Link → reference_doctype
  performed_by     → Link → User, Default: current user
  role_at_time     → Data (role của user tại thời điểm thực hiện)
  remarks          → Small Text
  ip_address       → Data, Read Only

Permissions: Read Only cho tất cả role (chỉ System Admin mới có quyền xóa)
Is Submittable: NO
```

Tạo helper function `assetcore/imm_master/utils.py`:

```python
import frappe
from frappe import _

def log_audit_trail(asset, event_type, from_status=None, to_status=None,
                    reference_doctype=None, reference_name=None, remarks=None):
    """
    Ghi audit trail cho mọi sự kiện quan trọng.
    Gọi hàm này từ mọi IMM controller khi có thay đổi trạng thái.
    """
    try:
        doc = frappe.get_doc({
            "doctype": "IMM Audit Trail",
            "asset": asset,
            "event_type": event_type,
            "from_status": from_status,
            "to_status": to_status,
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "performed_by": frappe.session.user,
            "role_at_time": get_current_user_roles(),
            "remarks": remarks,
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else None,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"IMM Audit Trail Error: {str(e)}", "IMM Audit Trail")


def get_current_user_roles():
    """Lấy roles của user hiện tại dưới dạng string."""
    roles = frappe.get_roles(frappe.session.user)
    imm_roles = [r for r in roles if r.startswith("IMM")]
    return ", ".join(imm_roles) if imm_roles else "Unknown"


def sync_asset_lifecycle_status(asset_name, new_status):
    """Sync lifecycle status về Asset custom field."""
    frappe.db.set_value("Asset", asset_name, "imm_lifecycle_status", new_status)
    frappe.db.commit()


def on_asset_update(doc, method):
    """Hook khi Asset được update."""
    pass  # Placeholder cho future logic
```

---

## TASK 6 — IMM DOCUMENT REPOSITORY DOCTYPE (IMM-05)

**Mục tiêu:** Quản lý kho hồ sơ pháp lý-kỹ thuật theo từng tài sản/model

Tạo DocType `IMM Document Repository` trong module `imm_deployment`:

```
Fields:
  name                  → auto
  naming_series         → IMM-05-DOC-.YYYY.-.####
  title                 → Data, Required, in_list_view
  
  --- Section: Phân loại ---
  document_category     → Select: Legal/Technical/Commercial/Training/
                                  Maintenance/Calibration/CAPA/Other
                          Required, in_standard_filter
  document_type         → Select: (xem bảng đầy đủ bên dưới)
  
  --- Section: Liên kết ---
  linked_to             → Select: Asset/Device Model, Default: Asset
  asset                 → Link → Asset (hiển thị khi linked_to = Asset)
  device_model          → Link → IMM Device Model (hiển thị khi linked_to = Device Model)
  
  --- Section: Thông tin hồ sơ ---
  document_number       → Data (số hiệu tài liệu)
  issuing_authority     → Data (cơ quan cấp/ban hành)
  issue_date            → Date
  effective_date        → Date
  expiry_date           → Date, in_standard_filter
  is_permanent          → Check (không có ngày hết hạn)
  version               → Data, Default: 1.0
  
  --- Section: File đính kèm ---
  primary_attachment    → Attach, Required
  additional_attachments → Child Table → IMM Document Attachment
  
  --- Section: Trạng thái ---
  document_status       → Select: Draft/Active/Expired/Superseded/Cancelled
                          Default: Draft, in_list_view, in_standard_filter
  imm_status            → Select: Active/Inactive, Default: Active
  
  --- Section: Kiểm soát ---
  controlled_copy       → Check
  review_required       → Check
  next_review_date      → Date
  reviewed_by           → Link → User
  
  remarks               → Small Text

document_type options:
  Hợp đồng mua bán|Hóa đơn VAT|Chứng nhận xuất xứ (C/O)|
  Chứng nhận chất lượng (C/Q)|Giấy đăng ký lưu hành BYT|
  Phép nhập khẩu|Biên bản bàn giao|Biên bản nghiệm thu|
  Tài liệu kỹ thuật (IFU)|Hướng dẫn sử dụng|
  Tài liệu bảo trì|Chứng chỉ hiệu chuẩn|Biên bản kiểm định|
  Báo cáo thử nghiệm|Kế hoạch bảo trì|Biên bản sửa chữa|
  Hồ sơ đào tạo|CAPA Record|Báo cáo audit|Khác

Workflow: Document Review Workflow
  Draft → Submitted → Under Review → Approved → Active
                                  ↘ Rejected → Draft
  Active → Expired (auto khi expiry_date < today)
```

**Child Table — IMM Document Attachment:**
```
Fields:
  attachment_type  → Data
  file             → Attach, Required
  description      → Small Text
  uploaded_on      → Date, Default: today
```

**Controller `imm_document_repository.py`:**
```python
# Phải có:
# validate(): 
#   - Nếu is_permanent=True, clear expiry_date
#   - Nếu linked_to=Asset, bắt buộc asset field
#   - Nếu linked_to=Device Model, bắt buộc device_model field
# before_submit():
#   - Kiểm tra primary_attachment không rỗng
# on_submit():
#   - Gọi log_audit_trail()
#   - Set document_status = "Active"
# on_update_after_submit():
#   - Nếu expiry_date < today, set document_status = "Expired"
```

**Workflow JSON** tạo tại `assetcore/fixtures/workflows/document_review_workflow.json`

**Scheduler** trong `imm_deployment/scheduler.py`:
```python
def check_document_expiry():
    """
    Chạy daily. Tìm document sắp hết hạn (trong 30 ngày) 
    và đã hết hạn, cập nhật status và gửi notification.
    """
    pass  # Implement đầy đủ
```

---

## TASK 7 — IMM PM WORK ORDER DOCTYPE (IMM-08)

**Mục tiêu:** Quản lý công việc bảo trì định kỳ (Preventive Maintenance)

Tạo DocType `IMM PM Work Order` trong module `imm_operations`:

```
Fields:
  name                → auto
  naming_series       → IMM-08-PM-.YYYY.-.####
  title               → Data, auto-populated, Read Only
  
  --- Section: Tài sản ---
  asset               → Link → Asset, Required, in_list_view
  asset_name          → Fetch from asset.asset_name, Read Only
  device_model        → Fetch from asset.imm_device_model, Read Only
  current_location    → Fetch from asset.location, Read Only
  current_department  → Fetch from asset.imm_department, Read Only
  
  --- Section: Lịch bảo trì ---
  pm_type             → Select: Preventive Maintenance/Periodic Inspection/
                                Lubrication/Cleaning/Calibration Check
                        Required, Default: Preventive Maintenance
  scheduled_date      → Date, Required, in_list_view
  scheduled_duration_hours → Float, Default: 2.0
  
  --- Section: Phân công ---
  assigned_team_lead  → Link → User (phải có role IMM Workshop Lead)
  assigned_technician → Link → User (phải có role IMM Technician), Required
  
  --- Section: Thực hiện ---
  actual_start_datetime → Datetime
  actual_end_datetime   → Datetime
  actual_duration_hours → Float, Read Only (tính từ actual_start/end)
  
  --- Section: Checklist ---
  checklist_items     → Child Table → IMM PM Checklist Item
  checklist_completion_pct → Percent, Read Only (tính từ checklist)
  
  --- Section: Kết quả ---
  pm_result           → Select: Pass/Pass with Observation/Fail/Inconclusive
  findings            → Text Editor
  corrective_actions  → Text Editor
  follow_up_required  → Check
  follow_up_description → Small Text
  
  --- Section: Phụ tùng sử dụng ---
  spare_parts_used    → Child Table → IMM PM Spare Part Used
  
  --- Section: Hồ sơ ---
  pm_report_attachment → Attach
  checklist_attachment → Attach
  
  --- Section: Trạng thái ---
  imm_status          → Select: Draft/Scheduled/In Progress/Completed/Verified/Cancelled
                        Default: Draft, in_list_view
  is_overdue          → Check, Read Only
  overdue_days        → Int, Read Only
  
  reference_asset_maintenance → Link → Asset Maintenance (link về ERPNext core)
  remarks             → Small Text

Workflow: PM Work Order Workflow
  States: Draft → Scheduled → Assigned → In Progress → Completed → Verified → Closed
  Transitions:
    Draft→Scheduled: Role IMM Workshop Lead, Action: Schedule
    Scheduled→Assigned: Role IMM Workshop Lead, Action: Assign Technician  
    Assigned→In Progress: Role IMM Technician, Action: Start Work
    In Progress→Completed: Role IMM Technician, Action: Complete
    Completed→Verified: Role IMM Workshop Lead + IMM Operations Manager, Action: Verify
    Verified→Closed: Role IMM Operations Manager, Action: Close
    Any→Cancelled: Role IMM Workshop Lead, Action: Cancel
```

**Child Table — IMM PM Checklist Item:**
```
Fields:
  task_description  → Data, Required
  task_category     → Select: Safety/Electrical/Mechanical/Calibration/Cleaning/Functional
  is_mandatory      → Check, Default: 1
  expected_value    → Data (giá trị kỳ vọng nếu có đo lường)
  actual_value      → Data (giá trị thực đo được)
  unit              → Data
  result            → Select: Pass/Fail/N/A/Observation
  completed         → Check
  remarks           → Small Text
```

**Child Table — IMM PM Spare Part Used:**
```
Fields:
  item_code         → Link → Item (ERPNext Item)
  item_name         → Fetch from item.item_name
  quantity          → Float, Required
  uom               → Link → UOM
  serial_number     → Data
  lot_number        → Data
  remarks           → Small Text
```

**Controller `imm_pm_work_order.py` phải có:**
```python
# validate():
#   - Kiểm tra asset không ở trạng thái Decommissioned
#   - Kiểm tra không có WO PM đang active cho cùng asset
#   - Auto-set title = f"PM - {asset_name} - {scheduled_date}"
#   - Tính checklist_completion_pct
#   - Tính actual_duration_hours từ actual_start/end
#   - Set is_overdue và overdue_days

# before_submit():
#   - pm_result bắt buộc phải có

# on_submit():
#   - Cập nhật asset.imm_last_pm_date = completion_date
#   - Cập nhật asset.imm_next_pm_date (dựa trên frequency)
#   - Tạo Asset Maintenance Log trong ERPNext
#   - Gọi log_audit_trail()
#   - Nếu follow_up_required: tạo IMM CM Work Order draft

# on_cancel():
#   - Gọi log_audit_trail() với event_type = "WO Cancelled"
```

**Scheduler** trong `imm_operations/scheduler.py`:
```python
def check_pm_due_dates():
    """
    Chạy daily. Tìm asset có next_pm_date trong 7 ngày tới.
    Nếu chưa có WO PM đang mở: tạo WO PM tự động ở trạng thái Draft.
    Gửi notification cho IMM Workshop Lead.
    """
    pass  # Implement đầy đủ

def escalate_overdue_wo():
    """
    Tìm WO PM quá hạn > 3 ngày, set is_overdue=True, 
    gửi notification cho IMM Operations Manager.
    """
    pass
```

---

## TASK 8 — IMM CM WORK ORDER DOCTYPE (IMM-09 + IMM-12)

**Mục tiêu:** Quản lý sửa chữa / bảo trì khắc phục (Corrective Maintenance)

Tạo DocType `IMM CM Work Order` trong module `imm_operations`:

```
Fields:
  name                → auto
  naming_series       → IMM-09-CM-.YYYY.-.####
  title               → Data, auto-populated
  
  --- Section: Tài sản ---
  asset               → Link → Asset, Required, in_list_view
  asset_name          → Fetch, Read Only
  current_location    → Fetch from asset.location, Read Only
  
  --- Section: Sự cố ---  
  failure_datetime    → Datetime, Required
  reported_by         → Link → User, Default: current user
  reporter_department → Link → Department
  failure_description → Text Editor, Required
  failure_category    → Select: Electrical/Mechanical/Software/
                                User Error/Unknown/Wear & Tear/
                                Accident/Other
  severity_level      → Select: Critical/High/Medium/Low
                        Required, in_list_view
  
  --- Section: Triage ---
  triage_result       → Select: Repair In-house/Send to Vendor/
                                Replace Component/Decommission/No Fault Found
  estimated_downtime_hours → Float
  
  --- Section: Phân công ---
  assigned_technician → Link → User
  assigned_datetime   → Datetime
  
  --- Section: Chẩn đoán ---
  diagnosis_datetime  → Datetime
  root_cause          → Text Editor
  root_cause_category → Select: Design Defect/Manufacturing Defect/
                                Improper Use/Maintenance Failure/
                                External Factor/Unknown
  
  --- Section: Sửa chữa ---
  repair_actions      → Text Editor
  spare_parts_used    → Child Table → IMM CM Spare Part Used
  vendor_repair       → Check
  vendor_name         → Link → Supplier (hiện khi vendor_repair=True)
  vendor_repair_cost  → Currency
  vendor_reference    → Data
  
  --- Section: Kết quả ---
  repair_result       → Select: Repaired/Partially Repaired/Cannot Repair/Replaced
  actual_start_datetime → Datetime
  actual_end_datetime   → Datetime
  actual_downtime_hours → Float, Read Only
  post_repair_test_result → Select: Pass/Fail/Not Tested
  
  --- Section: Hồ sơ ---
  repair_report_attachment → Attach
  
  --- Section: RCA (nếu Critical/High) ---
  rca_required        → Check
  rca_completed       → Check
  rca_report          → Attach
  capa_required       → Check
  capa_reference      → Data
  
  --- Section: Trạng thái ---
  imm_status          → Select: Reported/Triaged/Assigned/Diagnosing/
                                In Repair/Waiting Parts/Testing/Completed/Closed/Cancelled
                        Default: Reported, in_list_view
  sla_target_hours    → Float (dựa trên severity_level)
  sla_breach          → Check, Read Only
  
  reference_asset_repair → Link → Asset Repair (ERPNext core)

Workflow: CM Work Order Workflow
  States: Reported → Triaged → Assigned → Diagnosing → In Repair → 
          Waiting Parts → Testing → Completed → Closed
  (xem Workflow Map để biết transitions và roles)
```

Controller phải:
- Tính `actual_downtime_hours` từ `failure_datetime` đến `actual_end_datetime`
- Tự động set `sla_target_hours` dựa theo `severity_level`: Critical=4h, High=24h, Medium=72h, Low=168h
- Khi submit: cập nhật Asset lifecycle_status, tạo `Asset Repair` entry trong ERPNext
- Link về `Asset Repair` core DocType sau khi tạo

---

## TASK 9 — IMM CALIBRATION RECORD DOCTYPE (IMM-11)

**Mục tiêu:** Quản lý hiệu chuẩn, kiểm định thiết bị

Tạo DocType `IMM Calibration Record` trong module `imm_operations`:

```
Fields:
  name                    → auto
  naming_series           → IMM-11-CAL-.YYYY.-.####
  
  asset                   → Link → Asset, Required, in_list_view
  asset_name              → Fetch, Read Only
  
  calibration_type        → Select: Internal Calibration/External Calibration/
                                    Legal Inspection/Performance Test/
                                    Functional Check
                            Required, in_list_view
  
  scheduled_date          → Date, Required
  actual_date             → Date
  
  calibrating_entity      → Select: Internal/Accredited Lab/Manufacturer/Regulatory Body
  calibrating_lab_name    → Data
  calibrating_technician  → Link → User (nếu Internal)
  accreditation_number    → Data (số công nhận phòng lab)
  
  --- Section: Kết quả ---
  calibration_result      → Select: Pass/Pass with Conditions/Fail/Out of Tolerance
  certificate_number      → Data
  certificate_date        → Date
  certificate_expiry      → Date, Required, in_standard_filter, in_list_view
  
  measurement_results     → Child Table → IMM Calibration Measurement
  
  out_of_tolerance        → Check
  out_of_tolerance_action → Select: Recalibrate/Repair/Restrict Use/Decommission
  
  --- Section: Hồ sơ ---
  certificate_attachment  → Attach
  calibration_report      → Attach
  
  imm_status              → Select: Scheduled/In Progress/Completed/Expired/Cancelled
                            Default: Scheduled

Workflow: Calibration Workflow
  Scheduled → In Progress → Completed → [Expired auto]
```

**Child Table — IMM Calibration Measurement:**
```
Fields:
  parameter       → Data, Required (ví dụ: Temperature, Pressure)
  nominal_value   → Data
  tolerance       → Data (ví dụ: ±0.5°C)
  measured_value  → Data
  unit            → Data
  result          → Select: Within Tolerance/Out of Tolerance/N/A
```

**Scheduler:**
```python
def check_calibration_expiry():
    """
    Daily. Tìm asset có certificate_expiry trong 30 ngày tới.
    Gửi alert cho IMM Operations Manager và IMM Technician phụ trách.
    """
    pass
```

---

## TASK 10 — IMM COMMISSIONING RECORD DOCTYPE (IMM-04)

**Mục tiêu:** Ghi nhận quá trình lắp đặt, định danh và kiểm tra ban đầu

Tạo DocType `IMM Commissioning Record` trong module `imm_deployment`:

```
Fields:
  name                  → auto
  naming_series         → IMM-04-COM-.YYYY.-.####
  
  asset                 → Link → Asset, Required
  asset_name            → Fetch, Read Only
  device_model          → Link → IMM Device Model, Required
  
  --- Section: Thông tin lắp đặt ---
  installation_date     → Date, Required
  installation_location → Link → Location, Required
  installation_department → Link → Department
  installation_team     → Data (tên đội lắp đặt)
  vendor_representative → Data (đại diện nhà cung cấp)
  
  --- Section: Định danh ---
  manufacturer_serial_no → Data, Required
  internal_asset_code    → Data (mã tài sản nội bộ BV)
  barcode_applied        → Check
  qr_code_applied        → Check
  asset_tag_location     → Data (mô tả vị trí gắn tag)
  
  --- Section: Kiểm tra ban đầu ---
  inspection_checklist  → Child Table → IMM Commissioning Checklist
  overall_inspection_result → Select: Pass/Pass with Observations/Fail
  
  --- Section: Kiểm tra kỹ thuật ---
  electrical_safety_test → Select: Pass/Fail/N/A
  functional_test        → Select: Pass/Fail/N/A
  performance_baseline   → Text Editor (ghi giá trị baseline ban đầu)
  
  --- Section: Tài liệu ---
  documents_received     → Child Table → IMM Commissioning Document
  
  --- Section: Phê duyệt ---
  inspected_by           → Link → User
  inspection_date        → Date
  approved_by            → Link → User  
  approval_date          → Date
  release_for_use        → Check (chỉ set khi overall_inspection_result = Pass)
  release_date           → Date
  
  --- Section: Hồ sơ ---
  commissioning_report   → Attach
  handover_certificate   → Attach
  
  imm_status             → Select: Draft/In Progress/Completed/Approved/Rejected
                           Default: Draft

Workflow: Commissioning Workflow
  Draft → In Progress → Completed → Approved (→ tự động update Asset lifecycle_status = Active)
                                 ↘ Rejected → In Progress
```

**on_submit():** 
- Nếu `release_for_use=True` và `overall_inspection_result=Pass`:
  - Cập nhật `Asset.imm_lifecycle_status = "Active"`
  - Cập nhật `Asset.available_for_use_date = release_date`
  - Tạo IMM Asset Profile nếu chưa có
  - Gọi `log_audit_trail()` với event_type = "Commissioning Completed"

---

## TASK 11 — SCHEDULER HOÀN CHỈNH

Tạo `assetcore/imm_operations/scheduler.py` đầy đủ:

```python
import frappe
from frappe import _
from frappe.utils import today, add_days, date_diff, now_datetime
from assetcore.imm_master.utils import log_audit_trail


def check_pm_due_dates():
    """
    Daily job: Tìm asset cần bảo trì trong 7 ngày tới.
    Tạo WO PM tự động nếu chưa có WO đang mở.
    """
    alert_window_days = 7
    target_date = add_days(today(), alert_window_days)
    
    # Lấy asset có next_pm_date <= target_date và lifecycle_status = Active
    assets = frappe.db.sql("""
        SELECT name, asset_name, imm_next_pm_date, imm_responsible_technician, imm_department
        FROM `tabAsset`
        WHERE imm_next_pm_date <= %s
          AND imm_lifecycle_status = 'Active'
          AND docstatus = 1
    """, target_date, as_dict=True)
    
    for asset in assets:
        # Kiểm tra xem đã có WO PM đang mở chưa
        existing_wo = frappe.db.exists("IMM PM Work Order", {
            "asset": asset.name,
            "imm_status": ["in", ["Draft", "Scheduled", "Assigned", "In Progress"]],
            "docstatus": ["!=", 2]
        })
        
        if not existing_wo:
            # Tạo WO PM draft mới
            wo = frappe.get_doc({
                "doctype": "IMM PM Work Order",
                "asset": asset.name,
                "scheduled_date": asset.imm_next_pm_date,
                "assigned_technician": asset.imm_responsible_technician,
                "imm_status": "Draft",
            })
            wo.insert(ignore_permissions=True)
            
            # Gửi notification cho Workshop Lead
            _send_pm_notification(asset, wo.name)
    
    frappe.db.commit()


def check_calibration_expiry():
    """Daily job: Alert calibration sắp hết hạn (30 ngày)."""
    alert_window_days = 30
    target_date = add_days(today(), alert_window_days)
    
    records = frappe.db.sql("""
        SELECT name, asset, certificate_expiry
        FROM `tabIMM Calibration Record`
        WHERE certificate_expiry <= %s
          AND certificate_expiry >= %s
          AND imm_status = 'Completed'
          AND docstatus = 1
    """, (target_date, today()), as_dict=True)
    
    for rec in records:
        days_left = date_diff(rec.certificate_expiry, today())
        _send_calibration_alert(rec, days_left)
    
    # Cập nhật expired records
    frappe.db.sql("""
        UPDATE `tabIMM Calibration Record`
        SET imm_status = 'Expired'
        WHERE certificate_expiry < %s AND imm_status = 'Completed' AND docstatus = 1
    """, today())
    
    frappe.db.commit()


def escalate_overdue_wo():
    """Daily job: Escalate WO PM quá hạn."""
    overdue_threshold = 3  # ngày
    
    overdue_wos = frappe.db.sql("""
        SELECT name, asset, asset_name, scheduled_date, assigned_technician
        FROM `tabIMM PM Work Order`
        WHERE scheduled_date < %s
          AND imm_status IN ('Scheduled', 'Assigned')
          AND is_overdue = 0
          AND docstatus != 2
    """, add_days(today(), -overdue_threshold), as_dict=True)
    
    for wo in overdue_wos:
        overdue_days = date_diff(today(), wo.scheduled_date)
        frappe.db.set_value("IMM PM Work Order", wo.name, {
            "is_overdue": 1,
            "overdue_days": overdue_days
        })
        _send_escalation_notification(wo)
    
    frappe.db.commit()


def sync_asset_lifecycle_status():
    """Hourly: Sync lifecycle status từ IMM về Asset."""
    pass  # Placeholder


def _send_pm_notification(asset, wo_name):
    """Gửi notification tạo WO PM mới."""
    try:
        workshop_leads = frappe.get_all("User",
            filters={"role": "IMM Workshop Lead", "enabled": 1},
            fields=["name", "email"])
        
        for lead in workshop_leads:
            frappe.sendmail(
                recipients=[lead.email],
                subject=_(f"PM Work Order tạo mới: {wo_name}"),
                message=_(f"Tài sản {asset.asset_name} cần bảo trì định kỳ. WO: {wo_name}"),
                now=False
            )
    except Exception as e:
        frappe.log_error(str(e), "IMM PM Notification Error")


def _send_calibration_alert(record, days_left):
    """Gửi alert hiệu chuẩn sắp hết hạn."""
    pass


def _send_escalation_notification(wo):
    """Gửi notification escalation WO overdue."""
    pass
```

---

## TASK 12 — FIXTURES VÀ DEMO DATA

Tạo `assetcore/fixtures/demo_data.py` — script tạo demo data:

```python
import frappe

def create_demo_data():
    """
    Tạo demo data cho môi trường dev/staging.
    Chạy: bench execute assetcore.fixtures.demo_data.create_demo_data
    """
    
    # 1. Tạo Device Models
    models = [
        {
            "doctype": "IMM Device Model",
            "model_name": "CARESCAPE R860",
            "manufacturer": "GE Healthcare",
            "medical_device_class": "Class II",
            "recommended_pm_frequency": "Quarterly",
            "recommended_calibration_frequency": "Annual",
            "expected_lifespan_years": 10,
            "risk_classification": "High",
        },
        {
            "doctype": "IMM Device Model",
            "model_name": "Mindray BeneView T8",
            "manufacturer": "Mindray",
            "medical_device_class": "Class II",
            "recommended_pm_frequency": "Quarterly",
            "recommended_calibration_frequency": "Annual",
            "expected_lifespan_years": 8,
            "risk_classification": "High",
        },
        {
            "doctype": "IMM Device Model",
            "model_name": "Syringe Pump SP-500",
            "manufacturer": "JMS",
            "medical_device_class": "Class III",
            "recommended_pm_frequency": "Semi-annual",
            "recommended_calibration_frequency": "6 months",
            "expected_lifespan_years": 7,
            "risk_classification": "Critical",
        },
    ]
    
    for m in models:
        if not frappe.db.exists("IMM Device Model", {"model_name": m["model_name"]}):
            doc = frappe.get_doc(m)
            doc.insert(ignore_permissions=True)
    
    print("✅ Demo Device Models created")
    frappe.db.commit()
```

---

## TASK 13 — KIỂM TRA VÀ MIGRATE

Sau khi hoàn thành tất cả tasks trên, chạy:

```bash
# 1. Install app vào site
bench --site [site_name] install-app assetcore

# 2. Chạy migrate
bench --site [site_name] migrate

# 3. Load fixtures
bench --site [site_name] execute frappe.utils.fixtures.export_fixtures
bench --site [site_name] reload-fixtures assetcore

# 4. Chạy tests
bench --site [site_name] run-tests --app assetcore

# 5. Tạo demo data
bench --site [site_name] execute assetcore.fixtures.demo_data.create_demo_data

# 6. Build assets
bench build --app assetcore
```

**Báo cáo kết quả:**
Sau khi hoàn tất, liệt kê:
1. Danh sách DocTypes đã tạo thành công
2. Danh sách Custom Fields đã thêm vào Asset
3. Danh sách Roles đã tạo
4. Danh sách Workflows đã tạo
5. Bất kỳ lỗi hoặc warning nào cần xử lý
6. Các bước tiếp theo để build Đợt 1 đầy đủ

---

## GHI CHÚ CUỐI

- Mọi file JSON DocType phải valid theo Frappe schema
- Mọi controller Python phải import đúng: `from assetcore.imm_master.utils import log_audit_trail`
- Kiểm tra không có circular import
- Mọi Link field phải trỏ đến DocType đã tồn tại
- Frappe workflow phải có ít nhất 1 state là "default" (Initial State)
- Nếu có lỗi `bench migrate`, đọc error log tại `/home/frappe/frappe-bench/logs/`
