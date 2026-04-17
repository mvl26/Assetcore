# IMM-09 — API Interface
## Endpoints, Payloads & Integration Contracts

**Module:** IMM-09  
**Version:** 1.0  
**Ngày:** 2026-04-17  
**Trạng thái:** Draft

---

## 1. Sequence Diagrams

### 1.1 Tạo Repair WO và Phân công KTV

```
Frontend          API (imm09)           Service (imm09.py)      Frappe DB
   │                  │                        │                    │
   │ POST create_repair_wo                     │                    │
   │─────────────────►│                        │                    │
   │                  │ validate_repair_source()│                    │
   │                  │───────────────────────►│                    │
   │                  │                        │ SELECT Asset Repair │
   │                  │                        │ (check duplicate)  │
   │                  │                        │───────────────────►│
   │                  │                        │◄───────────────────│
   │                  │ validate_asset_not_under_repair()           │
   │                  │───────────────────────►│                    │
   │                  │                        │ SELECT Asset.status│
   │                  │                        │───────────────────►│
   │                  │                        │◄───────────────────│
   │                  │ check_repeat_failure() │                    │
   │                  │───────────────────────►│                    │
   │                  │                        │ SELECT last 30d WO │
   │                  │                        │───────────────────►│
   │                  │                        │◄───────────────────│
   │                  │ INSERT Asset Repair    │                    │
   │                  │────────────────────────────────────────────►│
   │                  │ INSERT Asset Lifecycle Event (repair_opened)│
   │                  │────────────────────────────────────────────►│
   │                  │ UPDATE Asset.status = Under Repair          │
   │                  │────────────────────────────────────────────►│
   │◄─────────────────│                        │                    │
   │ 200 {wo_name, status: Open}               │                    │
   │                  │                        │                    │
   │ POST assign_technician                    │                    │
   │─────────────────►│                        │                    │
   │                  │ UPDATE WO.status=Assigned, assigned_to      │
   │                  │────────────────────────────────────────────►│
   │                  │ INSERT Lifecycle Event (repair_assigned)    │
   │                  │────────────────────────────────────────────►│
   │◄─────────────────│                        │                    │
   │ 200 {status: Assigned}                    │                    │
```

---

### 1.2 Spare Parts Flow (Yêu cầu và xác nhận vật tư)

```
KTV Frontend      API (imm09)         Kho Frontend      API (imm09)      Stock Module
     │                 │                    │                 │                │
     │ POST submit_diagnosis               │                 │                │
     │ (needs_parts=true)                  │                 │                │
     │────────────────►│                   │                 │                │
     │                 │ UPDATE WO status=Pending Parts      │                │
     │                 │─────────────────────────────────────────────────────►│
     │                 │ INSERT Lifecycle Event (parts_requested)             │
     │                 │──────────────────────────────────────►               │
     │◄────────────────│                   │                 │                │
     │ 200 {status: Pending Parts}         │                 │                │
     │                 │                   │                 │                │
     │                 │ NOTIFICATION →    │                 │                │
     │                 │───────────────────►                 │                │
     │                 │ "WO-CM-2026-00042 cần vật tư"       │                │
     │                 │                   │                 │                │
     │                 │                   │ POST request_spare_parts         │
     │                 │                   │─────────────────►│               │
     │                 │                   │                 │ Create Stock   │
     │                 │                   │                 │ Entry (Issue)  │
     │                 │                   │                 │───────────────►│
     │                 │                   │                 │◄───────────────│
     │                 │                   │                 │ STE-2026-00456 │
     │                 │                   │◄────────────────│               │
     │                 │                   │ 200 {stock_entry_ref}           │
     │                 │                   │                 │                │
     │ NOTIFICATION ◄──│                   │                 │                │
     │ "Vật tư đã sẵn sàng"                │                 │                │
     │                 │                   │                 │                │
     │ POST submit_repair_result           │                 │                │
     │ (spare_parts_used với stock_entry)  │                 │                │
     │────────────────►│                   │                 │                │
     │                 │ validate_spare_parts_stock_entries()│                │
     │                 │ UPDATE WO.status = In Repair        │                │
     │◄────────────────│                   │                 │                │
     │ 200 {status: In Repair}             │                 │                │
```

---

### 1.3 Complete Repair + MTTR Calculation

```
KTV Frontend      API (imm09)           Service Layer           DB
     │                 │                      │                  │
     │ POST complete_repair                   │                  │
     │ {repair_checklist: [...all Pass],      │                  │
     │  dept_head_name: "BS. Hùng"}           │                  │
     │────────────────►│                      │                  │
     │                 │ validate_repair_checklist_complete()    │
     │                 │──────────────────────►                  │
     │                 │◄─────────────────────│                  │
     │                 │ OK — all Pass         │                  │
     │                 │                      │                  │
     │                 │ validate_firmware_change_request()      │
     │                 │──────────────────────►                  │
     │                 │◄─────────────────────│                  │
     │                 │ OK — no firmware update                 │
     │                 │                      │                  │
     │                 │ complete_repair(doc) │                  │
     │                 │──────────────────────►                  │
     │                 │                      │ calculate_mttr() │
     │                 │                      │ open→now in      │
     │                 │                      │ working hours    │
     │                 │                      │ = 18.5h          │
     │                 │                      │                  │
     │                 │                      │ get_sla_target() │
     │                 │                      │ (ClassIII, Urgent│
     │                 │                      │ → 24h)           │
     │                 │                      │                  │
     │                 │                      │ sla_breached=F   │
     │                 │                      │                  │
     │                 │                      │ UPDATE Asset.status=Active    │
     │                 │                      │─────────────────►│
     │                 │                      │ UPDATE Asset.custom_last_repair_date│
     │                 │                      │─────────────────►│
     │                 │                      │ INSERT Lifecycle Event         │
     │                 │                      │ (repair_completed, MTTR=18.5h)│
     │                 │                      │─────────────────►│
     │                 │                      │ SUBMIT WO docstatus=1         │
     │                 │                      │─────────────────►│
     │◄────────────────│                      │                  │
     │ 200 {           │                      │                  │
     │   status: Completed,                   │                  │
     │   mttr_hours: 18.5,                    │                  │
     │   sla_breached: false,                 │                  │
     │   asset_status: Active,               │                  │
     │ }               │                      │                  │
```

---

## 2. Endpoints Table

| Method | Endpoint | Actor | Mô tả |
|---|---|---|---|
| `POST` | `assetcore.api.imm09.create_repair_wo` | Workshop Manager | Tạo Asset Repair WO mới |
| `POST` | `assetcore.api.imm09.assign_technician` | Workshop Manager | Phân công KTV thực hiện |
| `POST` | `assetcore.api.imm09.submit_diagnosis` | KTV HTM | Lưu kết quả chẩn đoán |
| `POST` | `assetcore.api.imm09.request_spare_parts` | KTV HTM / Kho | Yêu cầu xuất kho vật tư |
| `POST` | `assetcore.api.imm09.submit_repair_result` | KTV HTM | Ghi nhận vật tư và kết quả sửa chữa |
| `POST` | `assetcore.api.imm09.complete_repair` | KTV HTM | Hoàn thành WO + tính MTTR |
| `POST` | `assetcore.api.imm09.mark_cannot_repair` | KTV HTM / Workshop Manager | Đánh dấu không thể sửa |
| `GET`  | `assetcore.api.imm09.get_repair_wo` | All | Lấy chi tiết một Repair WO |
| `GET`  | `assetcore.api.imm09.get_repair_list` | All | Danh sách WO với filter |
| `GET`  | `assetcore.api.imm09.get_mttr_report` | Workshop Manager, PTP | MTTR report theo tháng |
| `GET`  | `assetcore.api.imm09.get_repair_backlog` | Workshop Manager, PTP | Danh sách WO đang mở |
| `GET`  | `assetcore.api.imm09.search_spare_parts` | KTV HTM | Tìm kiếm Item vật tư |
| `POST` | `assetcore.api.imm09.create_firmware_fcr` | KTV HTM | Tạo Firmware Change Request |
| `POST` | `assetcore.api.imm09.approve_firmware_fcr` | Workshop Manager | Phê duyệt FCR |

---

## 3. JSON Payloads — Chi tiết

### 3.1 `create_repair_wo`

**Request:**
```json
{
  "asset_ref": "ACC-ASS-2026-00042",
  "incident_report": "IR-2026-00123",
  "source_pm_wo": null,
  "repair_type": "Corrective",
  "priority": "Urgent",
  "initial_description": "Máy thở không tạo được áp suất, báo alarm E-04",
  "reported_by": "bs.hung@hospital.vn"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "asset_ref": "ACC-ASS-2026-00042",
    "asset_name": "Máy thở Drager Evita V800",
    "risk_class": "Class III",
    "serial_no": "DRG-2024-001234",
    "status": "Open",
    "priority": "Urgent",
    "sla_target_hours": 24.0,
    "open_datetime": "2026-04-14T07:15:00+07:00",
    "is_repeat_failure": false,
    "is_warranty_claim": false
  }
}
```

**Error (400 — BR-09-01):**
```json
{
  "success": false,
  "error": {
    "code": "CM-001",
    "message": "Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc"
  }
}
```

**Error (409 — Duplicate WO):**
```json
{
  "success": false,
  "error": {
    "code": "CM-002",
    "message": "Thiết bị đang có phiếu sửa chữa đang mở: WO-CM-2026-00041"
  }
}
```

---

### 3.2 `assign_technician`

**Request:**
```json
{
  "name": "WO-CM-2026-00042",
  "assigned_to": "ktv.anha@hospital.vn",
  "notes": "Ưu tiên do máy thở ICU"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Assigned",
    "assigned_to": "ktv.anha@hospital.vn",
    "assigned_to_name": "Nguyễn Văn A",
    "assigned_datetime": "2026-04-14T08:30:00+07:00"
  }
}
```

---

### 3.3 `submit_diagnosis`

**Request:**
```json
{
  "name": "WO-CM-2026-00042",
  "diagnosis_notes": "Tụ điện C12 trên board nguồn bị phồng và cháy, gây mất điện cho compressor. Model tương đương: CAP-100UF-25V.",
  "root_cause_category": "Electrical",
  "needs_parts": true,
  "firmware_update_needed": false,
  "estimated_completion": "2026-04-15T14:00:00+07:00"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Pending Parts",
    "diagnosis_notes": "Tụ điện C12 trên board nguồn bị phồng và cháy...",
    "root_cause_category": "Electrical",
    "needs_parts": true,
    "notification_sent_to": ["kho.vt@hospital.vn", "manager.ws@hospital.vn"]
  }
}
```

---

### 3.4 `request_spare_parts`

**Request:**
```json
{
  "name": "WO-CM-2026-00042",
  "parts": [
    {
      "item_code": "CAP-100UF-25V",
      "qty": 2,
      "uom": "Cái",
      "notes": "Thay thế C12 board nguồn"
    },
    {
      "item_code": "FUSE-5A-250V",
      "qty": 1,
      "uom": "Cái",
      "notes": "Cầu chì dự phòng"
    }
  ],
  "urgency": "Urgent",
  "requested_by": "ktv.anha@hospital.vn"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "parts_request_ref": "PR-2026-00089",
    "status": "Pending Parts",
    "parts": [
      {
        "item_code": "CAP-100UF-25V",
        "item_name": "Tụ điện 100uF 25V",
        "qty_requested": 2,
        "qty_in_stock": 5,
        "available": true
      },
      {
        "item_code": "FUSE-5A-250V",
        "item_name": "Cầu chì 5A 250V",
        "qty_requested": 1,
        "qty_in_stock": 3,
        "available": true
      }
    ],
    "notification_sent_to": ["kho.vt@hospital.vn"]
  }
}
```

---

### 3.5 `submit_repair_result`

**Request:**
```json
{
  "name": "WO-CM-2026-00042",
  "spare_parts_used": [
    {
      "item_code": "CAP-100UF-25V",
      "item_name": "Tụ điện 100uF 25V",
      "qty": 2,
      "uom": "Cái",
      "unit_cost": 25000,
      "total_cost": 50000,
      "stock_entry_ref": "STE-2026-00456",
      "notes": "Thay thế C12 board nguồn chính"
    }
  ],
  "firmware_updated": false,
  "firmware_change_request": null,
  "repair_summary": "Đã thay tụ điện C12 100uF/25V bị cháy trên board nguồn. Kiểm tra các tụ xung quanh OK. Đo điện áp đầu ra board nguồn: 24V DC ± 0.5V — đạt yêu cầu."
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Pending Inspection",
    "total_parts_cost": 50000,
    "repair_summary": "Đã thay tụ điện C12...",
    "checklist_template": "RCT-VENTILATOR-STANDARD",
    "checklist_items_count": 5
  }
}
```

**Error (400 — BR-09-02):**
```json
{
  "success": false,
  "error": {
    "code": "CM-003",
    "message": "Vật tư 'Cầu chì 5A 250V' (dòng 2) thiếu phiếu xuất kho (Stock Entry Reference)"
  }
}
```

---

### 3.6 `complete_repair`

**Request:**
```json
{
  "name": "WO-CM-2026-00042",
  "repair_checklist": [
    {
      "idx": 1,
      "test_description": "Kiểm tra điện áp đầu vào",
      "test_category": "Electrical",
      "expected_value": "220V ± 5%",
      "measured_value": "218V",
      "result": "Pass",
      "notes": ""
    },
    {
      "idx": 2,
      "test_description": "Kiểm tra rò điện vỏ thiết bị",
      "test_category": "Safety",
      "expected_value": "< 0.1mA",
      "measured_value": "0.05mA",
      "result": "Pass",
      "notes": ""
    },
    {
      "idx": 3,
      "test_description": "Test chức năng tạo áp",
      "test_category": "Performance",
      "expected_value": "Tạo áp theo setting",
      "measured_value": "Pass khi test ở 10, 15, 20 cmH2O",
      "result": "Pass",
      "notes": ""
    },
    {
      "idx": 4,
      "test_description": "Test alarm áp suất thấp",
      "test_category": "Safety",
      "expected_value": "Báo alarm khi áp < threshold",
      "measured_value": "Alarm kích hoạt đúng",
      "result": "Pass",
      "notes": ""
    },
    {
      "idx": 5,
      "test_description": "Test pin backup",
      "test_category": "Electrical",
      "expected_value": "> 30 phút",
      "measured_value": "45 phút",
      "result": "Pass",
      "notes": ""
    }
  ],
  "dept_head_name": "BS. CK2 Nguyễn Văn Hùng",
  "dept_head_confirmation_datetime": "2026-04-15T14:30:00+07:00"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Completed",
    "mttr_hours": 18.5,
    "sla_target_hours": 24.0,
    "sla_breached": false,
    "open_datetime": "2026-04-14T07:15:00+07:00",
    "completion_datetime": "2026-04-15T14:30:00+07:00",
    "asset_ref": "ACC-ASS-2026-00042",
    "asset_status": "Active",
    "total_parts_cost": 50000,
    "is_repeat_failure": false,
    "lifecycle_event": "repair_completed"
  }
}
```

**Error (400 — BR-09-04 checklist fail):**
```json
{
  "success": false,
  "error": {
    "code": "CM-008",
    "message": "Mục kiểm tra #2 'Kiểm tra rò điện vỏ thiết bị' chưa Pass — không thể hoàn thành"
  }
}
```

---

### 3.7 `get_repair_list`

**Request (GET params):**
```
status=In Repair,Pending Parts
priority=Urgent,Emergency
asset_category=Ventilator
assigned_to=ktv.anha@hospital.vn
page=1
page_size=20
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "WO-CM-2026-00042",
        "asset_ref": "ACC-ASS-2026-00042",
        "asset_name": "Máy thở Drager Evita V800",
        "asset_category": "Ventilator",
        "risk_class": "Class III",
        "status": "In Repair",
        "priority": "Urgent",
        "assigned_to": "ktv.anha@hospital.vn",
        "assigned_to_name": "Nguyễn Văn A",
        "open_datetime": "2026-04-14T07:15:00+07:00",
        "sla_target_hours": 24.0,
        "elapsed_hours": 18.5,
        "sla_percent": 77,
        "is_repeat_failure": false,
        "incident_report": "IR-2026-00123",
        "source_pm_wo": null,
        "location": "ICU - Phòng 3"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

### 3.8 `get_mttr_report`

**Request (GET params):**
```
year=2026
month=4
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "period": "2026-04",
    "kpis": {
      "mttr_avg_hours": 18.5,
      "mttr_median_hours": 16.0,
      "total_completed": 14,
      "total_sla_breached": 2,
      "sla_compliance_pct": 85.7,
      "first_time_fix_rate_pct": 87.5,
      "total_parts_cost": 6300000,
      "avg_parts_cost_per_repair": 450000,
      "repair_backlog": 12
    },
    "by_asset_category": [
      { "category": "Ventilator", "count": 4, "avg_mttr": 22.1, "ftfr_pct": 75.0 },
      { "category": "Infusion Pump", "count": 6, "avg_mttr": 14.3, "ftfr_pct": 100.0 },
      { "category": "Monitor", "count": 4, "avg_mttr": 18.8, "ftfr_pct": 83.3 }
    ],
    "by_root_cause": [
      { "category": "Electrical", "count": 7, "pct": 50.0 },
      { "category": "Mechanical", "count": 4, "pct": 28.6 },
      { "category": "Software", "count": 2, "pct": 14.3 },
      { "category": "User Error", "count": 1, "pct": 7.1 }
    ],
    "trend_6months": [
      { "month": "2025-11", "mttr_avg": 22.0, "ftfr_pct": 82.0 },
      { "month": "2025-12", "mttr_avg": 19.5, "ftfr_pct": 85.0 },
      { "month": "2026-01", "mttr_avg": 25.1, "ftfr_pct": 78.0 },
      { "month": "2026-02", "mttr_avg": 21.0, "ftfr_pct": 84.0 },
      { "month": "2026-03", "mttr_avg": 20.6, "ftfr_pct": 86.0 },
      { "month": "2026-04", "mttr_avg": 18.5, "ftfr_pct": 87.5 }
    ]
  }
}
```

---

## 4. Backend API Implementation

```python
# assetcore/api/imm09.py
import frappe
from frappe import _
from assetcore.utils.response import _ok, _err
from assetcore.services.imm09 import (
    validate_repair_source,
    validate_asset_not_under_repair,
    check_repeat_failure,
)


@frappe.whitelist()
def create_repair_wo(
    asset_ref: str,
    repair_type: str,
    priority: str,
    initial_description: str,
    incident_report: str = None,
    source_pm_wo: str = None,
    reported_by: str = None,
) -> dict:
    """
    Tạo Asset Repair Work Order mới.
    Validate BR-09-01: phải có ít nhất một nguồn (incident_report HOẶC source_pm_wo).
    """
    try:
        if not incident_report and not source_pm_wo:
            return _err("Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc", "CM-001")

        validate_asset_not_under_repair(asset_ref)

        is_repeat = check_repeat_failure(asset_ref)

        asset = frappe.get_doc("Asset", asset_ref)
        risk_class = asset.get("custom_risk_class", "Class II")

        from assetcore.services.imm09 import get_sla_target
        sla_target = get_sla_target(risk_class, priority)

        doc = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": asset_ref,
            "incident_report": incident_report,
            "source_pm_wo": source_pm_wo,
            "repair_type": repair_type,
            "priority": priority,
            "initial_description": initial_description,
            "reported_by": reported_by,
            "status": "Open",
            "sla_target_hours": sla_target,
            "is_repeat_failure": is_repeat,
        })
        doc.insert(ignore_permissions=False)
        frappe.db.commit()

        return _ok({
            "name": doc.name,
            "asset_ref": doc.asset_ref,
            "asset_name": asset.asset_name,
            "risk_class": risk_class,
            "serial_no": asset.serial_no,
            "status": doc.status,
            "priority": doc.priority,
            "sla_target_hours": sla_target,
            "open_datetime": str(doc.open_datetime),
            "is_repeat_failure": doc.is_repeat_failure,
            "is_warranty_claim": doc.is_warranty_claim,
        })

    except frappe.ValidationError as e:
        return _err(str(e), "CM-001")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "IMM-09 create_repair_wo")
        return _err("Lỗi hệ thống khi tạo phiếu sửa chữa", "SYSTEM")


@frappe.whitelist()
def assign_technician(name: str, assigned_to: str, notes: str = None) -> dict:
    """Phân công KTV thực hiện sửa chữa."""
    try:
        doc = frappe.get_doc("Asset Repair", name)
        if doc.status != "Open":
            return _err(f"Không thể phân công — WO đang ở trạng thái {doc.status}", "CM-012")

        doc.assigned_to = assigned_to
        doc.assigned_by = frappe.session.user
        doc.assigned_datetime = frappe.utils.now_datetime()
        doc.status = "Assigned"
        if notes:
            doc.technician_notes = notes
        doc.save(ignore_permissions=False)

        from assetcore.utils.lifecycle import create_lifecycle_event
        create_lifecycle_event(
            asset=doc.asset_ref,
            event_type="repair_assigned",
            from_status="Open",
            to_status="Assigned",
            root_record=name,
            actor=frappe.session.user,
        )
        frappe.db.commit()

        assigned_name = frappe.db.get_value("User", assigned_to, "full_name")
        return _ok({
            "name": name,
            "status": "Assigned",
            "assigned_to": assigned_to,
            "assigned_to_name": assigned_name,
            "assigned_datetime": str(doc.assigned_datetime),
        })
    except frappe.DoesNotExistError:
        return _err(f"Phiếu sửa chữa '{name}' không tồn tại", "CM-011")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "IMM-09 assign_technician")
        return _err("Lỗi hệ thống khi phân công KTV", "SYSTEM")


@frappe.whitelist()
def submit_diagnosis(
    name: str,
    diagnosis_notes: str,
    root_cause_category: str,
    needs_parts: bool,
    firmware_update_needed: bool = False,
    estimated_completion: str = None,
) -> dict:
    """KTV lưu kết quả chẩn đoán và xác định bước tiếp theo."""
    try:
        doc = frappe.get_doc("Asset Repair", name)

        doc.diagnosis_notes = diagnosis_notes
        doc.root_cause_category = root_cause_category
        doc.firmware_update_needed = firmware_update_needed
        doc.status = "Pending Parts" if needs_parts else "In Repair"
        doc.save(ignore_permissions=False)

        from assetcore.utils.lifecycle import create_lifecycle_event
        create_lifecycle_event(
            asset=doc.asset_ref,
            event_type="diagnosis_submitted",
            from_status="Diagnosing",
            to_status=doc.status,
            root_record=name,
            actor=frappe.session.user,
            notes=f"Root cause: {root_cause_category}",
        )
        frappe.db.commit()

        notified = []
        if needs_parts:
            # Notify kho vật tư
            _notify_spare_parts_store(name, doc.asset_ref)
            notified.append("kho.vt@hospital.vn")

        return _ok({
            "name": name,
            "status": doc.status,
            "diagnosis_notes": diagnosis_notes,
            "root_cause_category": root_cause_category,
            "needs_parts": needs_parts,
            "notification_sent_to": notified,
        })
    except frappe.DoesNotExistError:
        return _err(f"Phiếu sửa chữa '{name}' không tồn tại", "CM-011")


@frappe.whitelist()
def submit_repair_result(
    name: str,
    spare_parts_used: list,
    firmware_updated: bool,
    repair_summary: str,
    firmware_change_request: str = None,
) -> dict:
    """
    KTV ghi nhận vật tư đã dùng và kết quả sửa chữa.
    Validate BR-09-02 (stock entry) và BR-09-03 (firmware FCR).
    """
    try:
        doc = frappe.get_doc("Asset Repair", name)

        # Update spare parts
        doc.set("spare_parts_used", [])
        total_cost = 0
        for part in spare_parts_used:
            if not part.get("stock_entry_ref"):
                return _err(
                    f"Vật tư '{part.get('item_name', part['item_code'])}' (dòng {part.get('idx', '?')}) thiếu phiếu xuất kho (Stock Entry Reference)",
                    "CM-003"
                )
            doc.append("spare_parts_used", part)
            total_cost += part.get("total_cost", 0)

        doc.total_parts_cost = total_cost
        doc.firmware_updated = firmware_updated
        doc.firmware_change_request = firmware_change_request
        doc.repair_summary = repair_summary
        doc.status = "Pending Inspection"
        doc.save(ignore_permissions=False)
        frappe.db.commit()

        return _ok({
            "name": name,
            "status": "Pending Inspection",
            "total_parts_cost": total_cost,
            "repair_summary": repair_summary,
        })
    except frappe.DoesNotExistError:
        return _err(f"Phiếu sửa chữa '{name}' không tồn tại", "CM-011")


@frappe.whitelist()
def complete_repair(
    name: str,
    repair_checklist: list,
    dept_head_name: str,
    dept_head_confirmation_datetime: str,
) -> dict:
    """
    Hoàn thành sửa chữa: validate checklist, tính MTTR, cập nhật Asset.
    """
    try:
        doc = frappe.get_doc("Asset Repair", name)
        doc.set("repair_checklist", repair_checklist)
        doc.dept_head_name = dept_head_name
        doc.dept_head_confirmation_datetime = dept_head_confirmation_datetime
        doc.save(ignore_permissions=False)
        doc.submit()
        frappe.db.commit()

        return _ok({
            "name": name,
            "status": "Completed",
            "mttr_hours": doc.mttr_hours,
            "sla_target_hours": doc.sla_target_hours,
            "sla_breached": doc.sla_breached,
            "open_datetime": str(doc.open_datetime),
            "completion_datetime": str(doc.completion_datetime),
            "asset_ref": doc.asset_ref,
            "asset_status": "Active",
            "total_parts_cost": doc.total_parts_cost,
            "is_repeat_failure": doc.is_repeat_failure,
            "lifecycle_event": "repair_completed",
        })
    except frappe.ValidationError as e:
        return _err(str(e), "CM-008")
    except frappe.DoesNotExistError:
        return _err(f"Phiếu sửa chữa '{name}' không tồn tại", "CM-011")


@frappe.whitelist()
def get_repair_wo(name: str) -> dict:
    """Lấy chi tiết một Asset Repair WO."""
    try:
        doc = frappe.get_doc("Asset Repair", name)
        return _ok(doc.as_dict())
    except frappe.DoesNotExistError:
        return _err(f"Phiếu sửa chữa '{name}' không tồn tại", "CM-011")


@frappe.whitelist()
def get_repair_list(
    status: str = None,
    priority: str = None,
    asset_category: str = None,
    assigned_to: str = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Danh sách Asset Repair WO với filter và pagination."""
    filters = {"docstatus": ("!=", 2)}
    if status:
        filters["status"] = ("in", status.split(","))
    if priority:
        filters["priority"] = ("in", priority.split(","))
    if assigned_to:
        filters["assigned_to"] = assigned_to

    items = frappe.get_all(
        "Asset Repair",
        filters=filters,
        fields=["name", "asset_ref", "asset_name", "status", "priority",
                "assigned_to", "open_datetime", "sla_target_hours", "mttr_hours",
                "is_repeat_failure", "incident_report", "source_pm_wo"],
        order_by="open_datetime desc",
        limit=page_size,
        start=(page - 1) * page_size,
    )
    total = frappe.db.count("Asset Repair", filters=filters)

    return _ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": -(-total // page_size),
    })


@frappe.whitelist()
def get_mttr_report(year: int, month: int) -> dict:
    """MTTR KPI report cho tháng chỉ định."""
    from frappe.utils import get_first_day, get_last_day
    import datetime

    period_start = datetime.date(int(year), int(month), 1)
    period_end = get_last_day(period_start)

    completed = frappe.get_all("Asset Repair",
        filters={
            "status": "Completed",
            "docstatus": 1,
            "completion_datetime": ("between", [str(period_start), str(period_end)]),
        },
        fields=["name", "mttr_hours", "sla_breached", "is_repeat_failure",
                "total_parts_cost", "root_cause_category", "asset_category"])

    if not completed:
        return _ok({"period": f"{year}-{month:02d}", "kpis": {}, "message": "Không có dữ liệu"})

    total = len(completed)
    sla_breached = sum(1 for w in completed if w.sla_breached)
    repeat = sum(1 for w in completed if w.is_repeat_failure)
    mttr_avg = sum(w.mttr_hours for w in completed) / total
    parts_total = sum(w.total_parts_cost or 0 for w in completed)

    return _ok({
        "period": f"{year}-{month:02d}",
        "kpis": {
            "mttr_avg_hours": round(mttr_avg, 1),
            "total_completed": total,
            "total_sla_breached": sla_breached,
            "sla_compliance_pct": round((total - sla_breached) / total * 100, 1),
            "first_time_fix_rate_pct": round((total - repeat) / total * 100, 1),
            "total_parts_cost": parts_total,
            "avg_parts_cost_per_repair": round(parts_total / total) if total else 0,
        }
    })


@frappe.whitelist()
def search_spare_parts(query: str, filters: dict = None) -> dict:
    """Tìm kiếm Item vật tư với tồn kho hiện tại."""
    items = frappe.get_all("Item",
        filters={"item_name": ("like", f"%{query}%"), "disabled": 0},
        fields=["item_code", "item_name", "stock_uom", "item_group"],
        limit=20)
    return _ok(items)


def _notify_spare_parts_store(wo_name: str, asset_ref: str) -> None:
    """Gửi notification đến kho vật tư khi cần xuất linh kiện."""
    frappe.sendmail(
        recipients=["kho.vt@hospital.vn"],
        subject=f"[AssetCore] Yêu cầu xuất vật tư — {wo_name}",
        message=f"Phiếu sửa chữa {wo_name} (Thiết bị: {asset_ref}) cần vật tư. Vui lòng kiểm tra và xuất kho.",
    )
```

---

## 5. Error Code Table

| Code | HTTP Status | Điều kiện | Thông báo (VI) |
|---|---|---|---|
| `CM-001` | 400 | Thiếu cả incident_report và source_pm_wo | "Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc" |
| `CM-002` | 409 | Thiết bị đang có WO đang mở | "Thiết bị đang có phiếu sửa chữa đang mở: {wo_name}" |
| `CM-003` | 400 | Spare part row thiếu stock_entry_ref | "Vật tư '{item}' (dòng {idx}) thiếu phiếu xuất kho" |
| `CM-004` | 400 | stock_entry_ref không tồn tại trong DB | "Phiếu xuất kho '{ref}' không tồn tại trong hệ thống" |
| `CM-005` | 400 | firmware_updated=True nhưng không có FCR | "Cập nhật firmware yêu cầu phải có Firmware Change Request được phê duyệt" |
| `CM-006` | 400 | FCR linked chưa được approve | "Firmware Change Request '{fcr}' chưa được phê duyệt (status: {status})" |
| `CM-007` | 400 | Checklist có mục chưa điền result | "Mục kiểm tra #{idx} '{desc}' chưa được điền kết quả" |
| `CM-008` | 400 | Checklist có mục result = Fail | "Mục kiểm tra #{idx} '{desc}' chưa Pass — không thể hoàn thành" |
| `CM-009` | 404 | asset_ref không tồn tại | "Thiết bị '{asset_ref}' không tìm thấy trong hệ thống" |
| `CM-010` | 403 | Người dùng không có quyền thực hiện | "Bạn không có quyền thực hiện thao tác này trên phiếu sửa chữa" |
| `CM-011` | 404 | WO name không tồn tại | "Phiếu sửa chữa '{name}' không tồn tại" |
| `CM-012` | 422 | Chuyển status không hợp lệ theo state machine | "Không thể chuyển từ '{from_status}' sang '{to_status}'" |
| `CM-013` | 400 | Thiếu dept_head_name khi Complete | "Phải có xác nhận của Trưởng khoa phòng trước khi hoàn thành" |
| `CM-014` | 409 | FCR version_before = version_after | "Firmware version trước và sau không thể giống nhau" |

---

## 6. curl Examples

### Tạo Repair WO

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm09.create_repair_wo" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_ref": "ACC-ASS-2026-00042",
    "incident_report": "IR-2026-00123",
    "repair_type": "Corrective",
    "priority": "Urgent",
    "initial_description": "Máy thở không tạo được áp suất, báo alarm E-04"
  }'
```

### Phân công KTV

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm09.assign_technician" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "WO-CM-2026-00042",
    "assigned_to": "ktv.anha@hospital.vn",
    "notes": "Ưu tiên do máy thở ICU"
  }'
```

### Nộp chẩn đoán

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm09.submit_diagnosis" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "WO-CM-2026-00042",
    "diagnosis_notes": "Tụ điện C12 trên board nguồn bị phồng và cháy",
    "root_cause_category": "Electrical",
    "needs_parts": true,
    "firmware_update_needed": false
  }'
```

### Hoàn thành sửa chữa

```bash
curl -X POST \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm09.complete_repair" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "WO-CM-2026-00042",
    "repair_checklist": [
      {"idx": 1, "test_description": "Kiểm tra điện áp", "test_category": "Electrical",
       "expected_value": "220V±5%", "measured_value": "218V", "result": "Pass"},
      {"idx": 2, "test_description": "Test chức năng", "test_category": "Performance",
       "expected_value": "Pass", "measured_value": "OK", "result": "Pass"}
    ],
    "dept_head_name": "BS. CK2 Nguyễn Văn Hùng",
    "dept_head_confirmation_datetime": "2026-04-15T14:30:00+07:00"
  }'
```

### Lấy MTTR Report tháng 4/2026

```bash
curl -G \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm09.get_mttr_report" \
  -H "Authorization: token api_key:api_secret" \
  --data-urlencode "year=2026" \
  --data-urlencode "month=4"
```

### Danh sách WO đang mở — khẩn cấp

```bash
curl -G \
  "https://hospital.assetcore.vn/api/method/assetcore.api.imm09.get_repair_list" \
  -H "Authorization: token api_key:api_secret" \
  --data-urlencode "status=Open,Assigned,Pending Parts" \
  --data-urlencode "priority=Emergency,Urgent" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=10"
```
