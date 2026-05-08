# ROLE PERMISSION MATRIX — ASSETCORE
# Version 0.1 | April 2026
# C=Create, R=Read, W=Write (Edit), D=Delete, S=Submit, Ca=Cancel, A=Amend

---

## LEGEND

| Symbol | Meaning |
|---|---|
| C | Create (tạo mới) |
| R | Read (xem) |
| W | Write/Edit (chỉnh sửa) |
| D | Delete (xóa) |
| S | Submit (nộp/xác nhận) |
| Ca | Cancel (hủy) |
| — | Không có quyền |
| * | Chỉ record của mình |

---

## MATRIX CHÍNH

| DocType | Dept Head | Ops Manager | Workshop Lead | Technician | Doc Officer | Storekeeper | QA Officer | Sys Admin |
|---|---|---|---|---|---|---|---|---|
| **MASTER DATA** | | | | | | | | |
| IMM Device Model | CRWD | R | R | R | CRWD | — | R | All |
| IMM Asset Profile | CRWD | RW | RW | R | CRWD | — | R | All |
| IMM Audit Trail | R | R | R | R* | R | — | R | All |
| **DEPLOYMENT** | | | | | | | | |
| IMM Commissioning Record | CRWSCa | CRW | CRWS | CRW* | CR | — | R | All |
| IMM Document Repository | CRWSCa | RW | R | R | CRWSCa | — | CRW | All |
| **OPERATIONS** | | | | | | | | |
| IMM PM Work Order | CRWSCa | CRWSCa | CRWSCa | CRW*S* | R | — | R | All |
| IMM CM Work Order | CRWSCa | CRWSCa | CRWSCa | CRW*S* | R | R | R | All |
| IMM Calibration Record | CRWSCa | CRWS | CRWS | CRWS* | R | — | CRW | All |
| **ASSET (Core ERPNext)** | | | | | | | | |
| Asset | CRWSCa | RW | RW | R | R | R | R | All |
| Asset Repair | CRWS | CRWS | CRWS | CRW*S* | R | R | R | All |
| Asset Maintenance | CRWS | CRWS | CRWS | R | R | — | R | All |
| Asset Maintenance Log | CR | CR | CR | CR* | R | — | R | All |
| Asset Movement | CRWS | CRWS | CRWS | R | R | — | R | All |
| **REPORT & DASHBOARD** | | | | | | | | |
| PM Dashboard | R | R | R | R | — | — | R | All |
| CM Dashboard | R | R | R | R | — | — | R | All |
| Asset Status Report | R | R | R | R | — | — | R | All |

---

## CHI TIẾT THEO ROLE

### IMM Department Head (Trưởng phòng VT,TBYT)
- Full access hầu hết DocType
- Quyền approve ở các workflow cuối (Commissioning, Document)
- Có thể xem toàn bộ dashboard và report

### IMM Operations Manager (PTP Khối 2)
- Quản lý toàn bộ operations (PM, CM, Calibration)
- Approve WO ở bước cuối (Verified → Closed)
- Xem tất cả dashboard

### IMM Workshop Lead (Trưởng workshop)
- Tạo, phân công, xử lý WO PM và WO CM
- Approve commissioning bước đầu
- Không có quyền xóa record

### IMM Technician (Kỹ thuật viên TBYT)
- Tạo và cập nhật WO của mình (*)
- Không có quyền cancel WO
- Xem Asset nhưng không edit field tài chính

### IMM Document Officer (Nhân viên hồ sơ)
- Toàn quyền với Document Repository
- Tạo và chỉnh sửa Asset Profile
- Không liên quan đến WO vận hành

### IMM Storekeeper (Nhân viên kho)
- Xem WO CM để biết yêu cầu phụ tùng
- Không tạo/sửa WO
- Tương lai: quản lý IMM Spare Part Inventory

### IMM QA Officer (Nhân viên QLCL)
- Xem và tạo Document Repository (CAPA, audit)
- Xem toàn bộ record để audit
- Không được sửa operational record

### IMM System Admin (Admin CNTT)
- Full access toàn bộ
- Chỉ dùng cho cấu hình hệ thống, không dùng cho nghiệp vụ hàng ngày

---

## CẤU HÌNH FRAPPE PERMISSION

```python
# Ví dụ cấu hình permission cho IMM PM Work Order
# Trong DocType JSON hoặc qua UI

permissions = [
    {
        "role": "IMM Department Head",
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 1, "cancel": 1, "amend": 1
    },
    {
        "role": "IMM Operations Manager",
        "read": 1, "write": 1, "create": 1,
        "submit": 1, "cancel": 1
    },
    {
        "role": "IMM Workshop Lead",
        "read": 1, "write": 1, "create": 1,
        "submit": 1, "cancel": 1
    },
    {
        "role": "IMM Technician",
        "read": 1, "write": 1, "create": 1,
        "submit": 1,
        # Có thể dùng permission.py để giới hạn chỉ record của mình
    },
    {
        "role": "IMM Document Officer",
        "read": 1
    },
    {
        "role": "IMM QA Officer",
        "read": 1
    },
]
```

---

## HAS_PERMISSION FUNCTION

```python
# assetcore/imm_operations/permission.py

import frappe

def has_permission(doc, ptype, user):
    """
    Custom permission check cho IMM WO DocTypes.
    IMM Technician chỉ được edit WO của mình.
    """
    if not user:
        user = frappe.session.user
    
    # System Admin và Manager có full access
    user_roles = frappe.get_roles(user)
    if any(r in user_roles for r in ["IMM Department Head", "IMM Operations Manager", 
                                      "IMM Workshop Lead", "IMM System Admin"]):
        return True
    
    # IMM Technician chỉ được edit WO được phân công cho mình
    if "IMM Technician" in user_roles:
        if ptype in ["write", "submit", "cancel"]:
            return doc.assigned_technician == user
        return True  # Read all
    
    # Các role khác chỉ được read
    if ptype == "read":
        return True
    
    return False
```
