# IMM-00 Foundation / Master Data — API Interface Specification

**Module:** IMM-00  
**Version:** 1.0.0  
**Date:** 2026-04-17  
**Base Path:** `assetcore.api.imm00`  
**Transport:** Frappe `frappe.call()` / HTTP POST to `/api/method/<path>`  
**Authentication:** Frappe session cookie or API key header (`Authorization: token api_key:api_secret`)

---

## Conventions

### Response Envelope

All endpoints return a consistent JSON envelope:

```json
// Success
{ "success": true, "data": <payload> }

// Error
{ "success": false, "error": "<Vietnamese message>", "code": "<ERROR_CODE>" }
```

Helper functions defined at top of `assetcore/api/imm00.py`:

```python
def _ok(data: dict | list) -> dict:
    return {"success": True, "data": data}

def _err(message: str, code: str = "GENERIC_ERROR") -> dict:
    return {"success": False, "error": message, "code": code}
```

### Pagination

List endpoints accept `page` (int, default=1) and `page_size` (int, default=20, max=100).  
Response includes `total`, `page`, `page_size`, `total_pages`.

### Roles Reference

| Role | Abbreviation | Capabilities |
|---|---|---|
| CMMS Admin | ADMIN | Full access, bulk operations, close CAPA |
| Biomed Engineer | BIOMED | Read/write all IMM records, verify CAPA |
| Workshop Head | WH | Read/write work-related records |
| HTM Technician | TECH | Read most, create CAPA, update status |
| QA Risk Team | QA | Full CAPA lifecycle, read all |
| System Manager | SYS | Unrestricted |

---

## Table of Contents

1. [get_device_models](#1-get_device_models)
2. [get_device_model](#2-get_device_model)
3. [create_device_model](#3-create_device_model)
4. [get_asset_profile](#4-get_asset_profile)
5. [update_asset_lifecycle_status](#5-update_asset_lifecycle_status)
6. [get_vendor_profile](#6-get_vendor_profile)
7. [get_sla_policy](#7-get_sla_policy)
8. [create_capa](#8-create_capa)
9. [close_capa](#9-close_capa)
10. [get_asset_audit_trail](#10-get_asset_audit_trail)
11. [get_capa_list](#11-get_capa_list)
12. [get_asset_kpi_summary](#12-get_asset_kpi_summary)
13. [bulk_update_device_model](#13-bulk_update_device_model)
14. [validate_asset_for_operations](#14-validate_asset_for_operations)

---

## 1. `get_device_models`

### Signature

```python
@frappe.whitelist()
def get_device_models(
    filters: str = "{}",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Danh sách IMM Device Model với phân trang và bộ lọc."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.get_device_models
```

### Permission Required

| Role | Access |
|---|---|
| All authenticated users | Read |

### Request Payload

```json
{
  "filters": "{\"manufacturer\": \"Philips\", \"risk_class\": \"High\", \"is_active\": 1}",
  "page": 1,
  "page_size": 20
}
```

**Filter keys supported:** `manufacturer`, `device_category`, `medical_class`, `risk_class`, `is_active`, `requires_calibration`

### Response — Success

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "IMM-MDL-2026-0001",
        "model_name": "Intellivue MX500",
        "manufacturer": "Philips",
        "device_category": "Patient Monitor",
        "medical_class": "Class II",
        "risk_class": "High",
        "gmdn_code": "35022",
        "requires_calibration": 1,
        "pm_interval_months": 6,
        "calibration_interval_months": 12,
        "byt_reg_no": "QLSP-04685/19",
        "byt_reg_expiry": "2027-12-31",
        "is_active": 1
      }
    ],
    "total": 48,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

### Response — Error

```json
{
  "success": false,
  "error": "filters không phải JSON hợp lệ",
  "code": "INVALID_FILTERS"
}
```

### Example

```javascript
// frappe.call
frappe.call({
  method: "assetcore.api.imm00.get_device_models",
  args: {
    filters: JSON.stringify({ manufacturer: "Philips", is_active: 1 }),
    page: 1,
    page_size: 20,
  },
  callback(r) {
    if (r.message.success) {
      console.log(r.message.data.items);
    }
  },
});
```

```bash
# curl
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.get_device_models" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'filters={"manufacturer":"Philips","is_active":1}' \
  --data-urlencode 'page=1' \
  --data-urlencode 'page_size=20'
```

---

## 2. `get_device_model`

### Signature

```python
@frappe.whitelist()
def get_device_model(name: str) -> dict:
    """Trả về chi tiết một IMM Device Model kèm danh sách spare parts."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.get_device_model
```

### Permission Required

| Role | Access |
|---|---|
| All authenticated users | Read |

### Request Payload

```json
{
  "name": "IMM-MDL-2026-0001"
}
```

### Response — Success

```json
{
  "success": true,
  "data": {
    "name": "IMM-MDL-2026-0001",
    "model_name": "Intellivue MX500",
    "manufacturer": "Philips",
    "device_category": "Patient Monitor",
    "medical_class": "Class II",
    "risk_class": "High",
    "gmdn_code": "35022",
    "byt_reg_no": "QLSP-04685/19",
    "byt_reg_expiry": "2027-12-31",
    "life_expectancy_years": 10,
    "pm_interval_months": 6,
    "calibration_interval_months": 12,
    "requires_calibration": 1,
    "default_vendor": "SUP-Philips-VN",
    "default_sla_policy": "sla-critical-24h",
    "is_active": 1,
    "spare_parts": [
      {
        "item_code": "SP-MX500-BAT",
        "part_name": "Pin dự phòng MX500",
        "part_number": "989803135231",
        "category": "Consumable",
        "pm_replacement": 1,
        "replacement_interval_months": 24,
        "unit_of_measure": "Nos",
        "estimated_cost": 850000
      }
    ]
  }
}
```

### Response — Error

```json
{
  "success": false,
  "error": "Không tìm thấy Device Model: IMM-MDL-2026-9999",
  "code": "NOT_FOUND"
}
```

### Example

```bash
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.get_device_model" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'name=IMM-MDL-2026-0001'
```

---

## 3. `create_device_model`

### Signature

```python
@frappe.whitelist()
def create_device_model(data: str) -> dict:
    """Tạo mới IMM Device Model; kiểm tra trùng tên + nhà sản xuất."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.create_device_model
```

### Permission Required

| Role | Access |
|---|---|
| CMMS Admin, Biomed Engineer | Create |

### Request Payload

```json
{
  "data": {
    "model_name": "Intellivue MX550",
    "manufacturer": "Philips",
    "device_category": "Patient Monitor",
    "medical_class": "Class II",
    "risk_class": "High",
    "gmdn_code": "35022",
    "byt_reg_no": "QLSP-05001/22",
    "byt_reg_expiry": "2027-06-30",
    "life_expectancy_years": 10,
    "pm_interval_months": 6,
    "requires_calibration": 1,
    "calibration_interval_months": 12,
    "is_active": 1
  }
}
```

**Required fields:** `model_name`, `manufacturer`, `medical_class`, `risk_class`

### Response — Success

```json
{
  "success": true,
  "data": {
    "name": "IMM-MDL-2026-0002",
    "model_name": "Intellivue MX550",
    "manufacturer": "Philips"
  }
}
```

### Response — Error (Duplicate)

```json
{
  "success": false,
  "error": "Tên model đã tồn tại cho nhà sản xuất này",
  "code": "MDL-001"
}
```

### Response — Error (Validation)

```json
{
  "success": false,
  "error": "data không phải JSON hợp lệ",
  "code": "INVALID_DATA"
}
```

### Example

```bash
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.create_device_model" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'data={"model_name":"Intellivue MX550","manufacturer":"Philips","medical_class":"Class II","risk_class":"High"}'
```

---

## 4. `get_asset_profile`

### Signature

```python
@frappe.whitelist()
def get_asset_profile(asset_name: str) -> dict:
    """Trả về IMM Asset Profile đầy đủ theo tên Asset."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.get_asset_profile
```

### Permission Required

| Role | Access |
|---|---|
| All authenticated users | Read |

### Request Payload

```json
{
  "asset_name": "ACC-ICU-2026-0001"
}
```

### Response — Success

```json
{
  "success": true,
  "data": {
    "name": "IMM-ASP-2026-0001",
    "asset": "ACC-ICU-2026-0001",
    "device_model": "IMM-MDL-2026-0001",
    "device_model_name": "Intellivue MX500",
    "manufacturer": "Philips",
    "lifecycle_status": "Active",
    "calibration_status": "In Tolerance",
    "medical_class": "Class II",
    "risk_class": "High",
    "manufacturer_sn": "SN-US-29847123",
    "udi_code": "00888793000014",
    "gmdn_code": "35022",
    "byt_reg_no": "QLSP-04685/19",
    "byt_reg_expiry": "2027-12-31",
    "installation_date": "2026-01-15",
    "commissioning_date": "2026-01-20",
    "warranty_expiry_date": "2028-01-20",
    "last_pm_date": "2026-03-01",
    "next_pm_date": "2026-09-01",
    "last_calibration_date": "2026-01-20",
    "next_calibration_date": "2027-01-20",
    "responsible_tech": "tech.nguyen@hospital.vn",
    "department": "ICU",
    "vendor": "SUP-Philips-VN"
  }
}
```

### Response — Error

```json
{
  "success": false,
  "error": "Không tìm thấy hồ sơ IMM cho tài sản: ACC-ICU-2026-9999",
  "code": "ASP-002"
}
```

### Example

```javascript
frappe.call({
  method: "assetcore.api.imm00.get_asset_profile",
  args: { asset_name: cur_frm.doc.name },
  callback(r) {
    if (r.message.success) {
      const profile = r.message.data;
      cur_frm.set_value("custom_lifecycle_status", profile.lifecycle_status);
    }
  },
});
```

---

## 5. `update_asset_lifecycle_status`

### Signature

```python
@frappe.whitelist()
def update_asset_lifecycle_status(
    asset_name: str,
    new_status: str,
    reason: str,
) -> dict:
    """Thay đổi lifecycle_status của Asset kèm Audit Trail tự động."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.update_asset_lifecycle_status
```

### Permission Required

| Role | Access |
|---|---|
| CMMS Admin, Biomed Engineer, Workshop Head | Write |
| HTM Technician | Write (limited: cannot set Decommissioned) |

### Request Payload

```json
{
  "asset_name": "ACC-ICU-2026-0001",
  "new_status": "Under Repair",
  "reason": "Màn hình hiển thị lỗi, gửi xưởng sửa chữa"
}
```

**Valid `new_status` values:** `Active` | `Under Repair` | `Calibrating` | `Out of Service` | `Decommissioned`

### Response — Success

```json
{
  "success": true,
  "data": {
    "asset": "ACC-ICU-2026-0001",
    "from_status": "Active",
    "to_status": "Under Repair",
    "audit_trail_id": "IMM-AUD-2026-00123",
    "actor": "tech.nguyen@hospital.vn",
    "timestamp": "2026-04-17T09:23:11.000000"
  }
}
```

### Response — Error (Invalid Status)

```json
{
  "success": false,
  "error": "Trạng thái không hợp lệ: Broken",
  "code": "STS-001"
}
```

### Response — Error (Asset Not Found)

```json
{
  "success": false,
  "error": "Không tìm thấy hồ sơ IMM cho tài sản: ACC-ICU-2026-9999",
  "code": "ASP-002"
}
```

### Example

```bash
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.update_asset_lifecycle_status" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'asset_name=ACC-ICU-2026-0001' \
  --data-urlencode 'new_status=Under Repair' \
  --data-urlencode 'reason=Màn hình hiển thị lỗi'
```

---

## 6. `get_vendor_profile`

### Signature

```python
@frappe.whitelist()
def get_vendor_profile(supplier_name: str) -> dict:
    """Trả về IMM Vendor Profile kèm danh sách KTV được uỷ quyền."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.get_vendor_profile
```

### Permission Required

| Role | Access |
|---|---|
| All authenticated users | Read |

### Request Payload

```json
{
  "supplier_name": "SUP-Philips-VN"
}
```

### Response — Success

```json
{
  "success": true,
  "data": {
    "name": "IMM-VND-2026-0001",
    "supplier": "SUP-Philips-VN",
    "company_name": "Philips Việt Nam Co., Ltd.",
    "short_name": "Philips VN",
    "vendor_type": "OEM",
    "country": "Vietnam",
    "primary_contact_name": "Nguyễn Văn A",
    "primary_contact_phone": "0901234567",
    "primary_contact_email": "support.vn@philips.com",
    "support_hotline": "1800 599 941",
    "contract_no": "HĐ-PHILIPS-2024-001",
    "contract_start": "2024-01-01",
    "contract_expiry": "2026-12-31",
    "response_sla_hours": 4,
    "resolution_sla_hours": 48,
    "rating": 4.5,
    "is_active": 1,
    "days_until_contract_expiry": 258,
    "authorized_technicians": [
      {
        "tech_name": "Trần Văn B",
        "tech_phone": "0912345678",
        "tech_email": "b.tran@philips.com",
        "certification_no": "CERT-PHI-2023-088",
        "certification_expiry": "2027-06-30",
        "specialization": "Patient Monitoring, Anesthesia",
        "is_active": 1
      }
    ]
  }
}
```

### Response — Error

```json
{
  "success": false,
  "error": "Không tìm thấy hồ sơ nhà cung cấp IMM cho: SUP-Unknown",
  "code": "VND-001"
}
```

### Example

```bash
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.get_vendor_profile" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'supplier_name=SUP-Philips-VN'
```

---

## 7. `get_sla_policy`

### Signature

```python
@frappe.whitelist()
def get_sla_policy(priority: str, risk_class: str) -> dict:
    """Tra cứu IMM SLA Policy theo priority và risk_class; fallback về priority only."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.get_sla_policy
```

### Permission Required

| Role | Access |
|---|---|
| All authenticated users | Read |

### Request Payload

```json
{
  "priority": "Critical",
  "risk_class": "High"
}
```

**Valid `priority` values:** `Critical` | `High` | `Medium` | `Low`  
**Valid `risk_class` values:** `Low` | `Medium` | `High` | `Critical`

### Response — Success (Exact Match)

```json
{
  "success": true,
  "data": {
    "name": "sla-critical-high-4h",
    "policy_name": "sla-critical-high-4h",
    "priority": "Critical",
    "risk_class": "High",
    "response_hours": 4.0,
    "resolution_hours": 24.0,
    "escalation_hours": 48.0,
    "business_hours_only": 0,
    "escalate_to": "biomed.head@hospital.vn",
    "notify_roles": "[\"CMMS Admin\", \"Biomed Engineer\", \"QA Risk Team\"]",
    "match_type": "exact"
  }
}
```

### Response — Success (Fallback Match)

```json
{
  "success": true,
  "data": {
    "name": "sla-critical-default",
    "policy_name": "sla-critical-default",
    "priority": "Critical",
    "risk_class": null,
    "response_hours": 4.0,
    "resolution_hours": 24.0,
    "escalation_hours": 48.0,
    "business_hours_only": 0,
    "match_type": "fallback_priority_only"
  }
}
```

### Response — Error (Not Found)

```json
{
  "success": false,
  "error": "Không tìm thấy SLA Policy phù hợp với priority và risk_class",
  "code": "SLA-001"
}
```

### Example

```javascript
frappe.call({
  method: "assetcore.api.imm00.get_sla_policy",
  args: { priority: "Critical", risk_class: "High" },
  callback(r) {
    if (r.message.success) {
      const sla = r.message.data;
      console.log(`Response SLA: ${sla.response_hours}h`);
    }
  },
});
```

---

## 8. `create_capa`

### Signature

```python
@frappe.whitelist()
def create_capa(
    asset: str,
    source_doctype: str,
    source_name: str,
    severity: str,
    description: str,
    title: str = "",
    assigned_to: str = "",
    due_date: str = "",
) -> dict:
    """Tạo IMM CAPA Record mới và ghi Audit Trail capa_opened."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.create_capa
```

### Permission Required

| Role | Access |
|---|---|
| CMMS Admin, Biomed Engineer, QA Risk Team, HTM Technician | Create |

### Request Payload

```json
{
  "asset": "ACC-ICU-2026-0001",
  "source_doctype": "PM Work Order",
  "source_name": "WO-PM-2026-0088",
  "severity": "High",
  "description": "Phát hiện rò điện bất thường tại đầu đo SpO2 trong quá trình PM định kỳ. Cần kiểm tra toàn bộ cáp kết nối và hệ thống cách điện.",
  "title": "Rò điện tại đầu đo SpO2 — Intellivue MX500 ICU",
  "assigned_to": "biomed.nguyen@hospital.vn",
  "due_date": "2026-04-24"
}
```

**Required fields:** `asset`, `source_doctype`, `source_name`, `severity`, `description`  
**`severity` values:** `Critical` | `High` | `Medium` | `Low`  
**Auto-computed `due_date` if not provided:** Critical=7d, High=14d, Medium=30d, Low=60d from today

### Response — Success

```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00001",
    "asset": "ACC-ICU-2026-0001",
    "status": "Open",
    "severity": "High",
    "due_date": "2026-04-24",
    "assigned_to": "biomed.nguyen@hospital.vn",
    "audit_trail_id": "IMM-AUD-2026-00124"
  }
}
```

### Response — Error (Invalid Severity)

```json
{
  "success": false,
  "error": "Mức độ nghiêm trọng không hợp lệ: Extreme",
  "code": "CAPA-001"
}
```

### Response — Error (Asset Not Found)

```json
{
  "success": false,
  "error": "Không tìm thấy hồ sơ IMM cho tài sản: ACC-ICU-9999",
  "code": "ASP-002"
}
```

### Example

```bash
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.create_capa" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'asset=ACC-ICU-2026-0001' \
  --data-urlencode 'source_doctype=PM Work Order' \
  --data-urlencode 'source_name=WO-PM-2026-0088' \
  --data-urlencode 'severity=High' \
  --data-urlencode 'description=Phát hiện rò điện bất thường tại đầu đo SpO2'
```

---

## 9. `close_capa`

### Signature

```python
@frappe.whitelist()
def close_capa(
    capa_name: str,
    verification_result: str,
    remarks: str,
) -> dict:
    """Đóng CAPA: set Closed, ghi closed_at/closed_by, Submit, Audit Trail."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.close_capa
```

### Permission Required

| Role | Access |
|---|---|
| CMMS Admin, Biomed Engineer, QA Risk Team | Write (close) |

### Request Payload

```json
{
  "capa_name": "CAPA-2026-00001",
  "verification_result": "Effective",
  "remarks": "Đã thay thế toàn bộ cáp SpO2 và kiểm tra cách điện. Kết quả đo rò điện dưới ngưỡng IEC 60601 (< 100μA). Thiết bị đã được trả về vận hành bình thường."
}
```

**Valid `verification_result` values:** `Effective` | `Not Effective` | `Partially Effective`

### Response — Success

```json
{
  "success": true,
  "data": {
    "capa_name": "CAPA-2026-00001",
    "status": "Closed",
    "verification_result": "Effective",
    "closed_at": "2026-04-17T14:35:22.000000",
    "closed_by": "biomed.nguyen@hospital.vn",
    "audit_trail_id": "IMM-AUD-2026-00125"
  }
}
```

### Response — Error (Already Closed)

```json
{
  "success": false,
  "error": "CAPA đã được đóng hoặc huỷ, không thể thao tác thêm.",
  "code": "CAPA-002"
}
```

### Response — Error (Invalid Result)

```json
{
  "success": false,
  "error": "Kết quả xác minh không hợp lệ: Resolved",
  "code": "CAPA-006"
}
```

### Example

```bash
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.close_capa" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'capa_name=CAPA-2026-00001' \
  --data-urlencode 'verification_result=Effective' \
  --data-urlencode 'remarks=Đã thay thế cáp và xác minh an toàn điện'
```

---

## 10. `get_asset_audit_trail`

### Signature

```python
@frappe.whitelist()
def get_asset_audit_trail(
    asset_name: str,
    limit: int = 50,
    offset: int = 0,
    event_type: str = "",
) -> dict:
    """Lấy lịch sử Audit Trail phân trang cho một tài sản; mới nhất trước."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.get_asset_audit_trail
```

### Permission Required

| Role | Access |
|---|---|
| All authenticated users | Read |

### Request Payload

```json
{
  "asset_name": "ACC-ICU-2026-0001",
  "limit": 20,
  "offset": 0,
  "event_type": ""
}
```

**Optional `event_type` filter:** `installed` | `commissioned` | `pm_completed` | `repaired` | `failure_reported` | `status_changed` | `capa_opened` | `capa_closed` | `retired` | `profile_created`

### Response — Success

```json
{
  "success": true,
  "data": {
    "asset": "ACC-ICU-2026-0001",
    "total": 47,
    "limit": 20,
    "offset": 0,
    "events": [
      {
        "name": "IMM-AUD-2026-00125",
        "event_type": "capa_closed",
        "from_status": "Open",
        "to_status": "Closed",
        "actor": "biomed.nguyen@hospital.vn",
        "actor_full_name": "Nguyễn Văn Biomed",
        "source_doctype": "IMM CAPA Record",
        "source_name": "CAPA-2026-00001",
        "event_timestamp": "2026-04-17T14:35:22.000000",
        "remarks": "Result: Effective | Đã thay thế cáp SpO2"
      },
      {
        "name": "IMM-AUD-2026-00124",
        "event_type": "capa_opened",
        "from_status": "",
        "to_status": "Open",
        "actor": "tech.nguyen@hospital.vn",
        "actor_full_name": "Nguyễn Kỹ thuật viên",
        "source_doctype": "IMM CAPA Record",
        "source_name": "CAPA-2026-00001",
        "event_timestamp": "2026-04-17T09:10:05.000000",
        "remarks": "Severity: High"
      }
    ]
  }
}
```

### Response — Error

```json
{
  "success": false,
  "error": "Không tìm thấy hồ sơ IMM cho tài sản: ACC-ICU-9999",
  "code": "ASP-002"
}
```

### Example

```javascript
frappe.call({
  method: "assetcore.api.imm00.get_asset_audit_trail",
  args: {
    asset_name: "ACC-ICU-2026-0001",
    limit: 20,
    offset: 0,
    event_type: "status_changed",
  },
  callback(r) {
    if (r.message.success) {
      r.message.data.events.forEach((e) => {
        console.log(`${e.event_timestamp}: ${e.event_type} by ${e.actor}`);
      });
    }
  },
});
```

---

## 11. `get_capa_list`

### Signature

```python
@frappe.whitelist()
def get_capa_list(
    filters: str = "{}",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Danh sách IMM CAPA Record với filters, phân trang, thống kê tóm tắt."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.get_capa_list
```

### Permission Required

| Role | Access |
|---|---|
| All authenticated HTM roles | Read |

### Request Payload

```json
{
  "filters": "{\"status\": \"Open\", \"severity\": \"High\", \"assigned_to\": \"biomed.nguyen@hospital.vn\"}",
  "page": 1,
  "page_size": 20
}
```

**Filter keys supported:** `asset`, `status`, `severity`, `assigned_to`, `is_overdue`, `source_doctype`, `due_date` (supports `["<", "date"]` syntax as JSON)

### Response — Success

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "CAPA-2026-00001",
        "asset": "ACC-ICU-2026-0001",
        "title": "Rò điện tại đầu đo SpO2",
        "severity": "High",
        "status": "Open",
        "assigned_to": "biomed.nguyen@hospital.vn",
        "due_date": "2026-04-24",
        "is_overdue": 0,
        "source_doctype": "PM Work Order",
        "source_name": "WO-PM-2026-0088",
        "creation": "2026-04-17T09:10:05.000000"
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "summary": {
      "open": 8,
      "in_progress": 3,
      "pending_verification": 1,
      "overdue": 2,
      "critical_open": 1
    }
  }
}
```

### Response — Error

```json
{
  "success": false,
  "error": "filters không phải JSON hợp lệ",
  "code": "INVALID_FILTERS"
}
```

### Example

```bash
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.get_capa_list" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'filters={"status":["in",["Open","In Progress"]],"is_overdue":1}' \
  --data-urlencode 'page=1' \
  --data-urlencode 'page_size=20'
```

---

## 12. `get_asset_kpi_summary`

### Signature

```python
@frappe.whitelist()
def get_asset_kpi_summary(asset_name: str) -> dict:
    """KPI tổng hợp MTD cho một tài sản: WO, CAPA, ngày PM/calibration."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.get_asset_kpi_summary
```

### Permission Required

| Role | Access |
|---|---|
| All authenticated users | Read |

### Request Payload

```json
{
  "asset_name": "ACC-ICU-2026-0001"
}
```

### Response — Success

```json
{
  "success": true,
  "data": {
    "asset": "ACC-ICU-2026-0001",
    "lifecycle_status": "Active",
    "calibration_status": "In Tolerance",
    "mtd_work_orders": 2,
    "open_capa_count": 1,
    "next_pm_date": "2026-09-01",
    "next_calibration_date": "2027-01-20",
    "last_pm_date": "2026-03-01",
    "last_calibration_date": "2026-01-20",
    "days_until_next_pm": 137,
    "days_until_next_calibration": 278,
    "pm_overdue": false,
    "calibration_overdue": false,
    "warranty_status": "Active",
    "warranty_expiry_date": "2028-01-20"
  }
}
```

### Response — Error

```json
{
  "success": false,
  "error": "Không tìm thấy hồ sơ IMM cho tài sản: ACC-ICU-9999",
  "code": "ASP-002"
}
```

### Example

```javascript
// Typical use: load KPI panel when opening Asset form
frappe.call({
  method: "assetcore.api.imm00.get_asset_kpi_summary",
  args: { asset_name: cur_frm.doc.name },
  callback(r) {
    if (r.message.success) {
      const kpi = r.message.data;
      // Render KPI widget
      cur_frm.dashboard.add_indicator(
        `PM tiếp theo: ${kpi.next_pm_date}`,
        kpi.pm_overdue ? "red" : "green"
      );
    }
  },
});
```

---

## 13. `bulk_update_device_model`

### Signature

```python
@frappe.whitelist()
def bulk_update_device_model(items: str) -> dict:
    """Import/upsert nhiều IMM Device Model cùng lúc; tối đa 500 bản ghi."""
```

### HTTP

```
POST /api/method/assetcore.api.imm00.bulk_update_device_model
```

### Permission Required

| Role | Access |
|---|---|
| CMMS Admin | Write |

### Request Payload

```json
{
  "items": [
    {
      "model_name": "LOGIQ E9",
      "manufacturer": "GE Healthcare",
      "device_category": "Ultrasound",
      "medical_class": "Class II",
      "risk_class": "Medium",
      "gmdn_code": "40697",
      "pm_interval_months": 12,
      "requires_calibration": 0,
      "is_active": 1
    },
    {
      "model_name": "Venue 50",
      "manufacturer": "GE Healthcare",
      "device_category": "Ultrasound",
      "medical_class": "Class II",
      "risk_class": "Medium",
      "gmdn_code": "40697",
      "pm_interval_months": 12,
      "requires_calibration": 0,
      "is_active": 1
    }
  ]
}
```

**Constraints:**
- Maximum 500 items per request (BULK-002)
- Items list must not be empty (BULK-001)
- Each item must have `model_name` and `manufacturer`
- Upsert logic: insert if not exists, update if exists (match on `model_name` + `manufacturer`)

### Response — Success

```json
{
  "success": true,
  "data": {
    "total_submitted": 2,
    "created": 1,
    "updated": 1,
    "failed": 0,
    "results": [
      {
        "model_name": "LOGIQ E9",
        "manufacturer": "GE Healthcare",
        "action": "created",
        "name": "IMM-MDL-2026-0003"
      },
      {
        "model_name": "Venue 50",
        "manufacturer": "GE Healthcare",
        "action": "updated",
        "name": "IMM-MDL-2025-0047"
      }
    ]
  }
}
```

### Response — Partial Failure

```json
{
  "success": true,
  "data": {
    "total_submitted": 3,
    "created": 1,
    "updated": 1,
    "failed": 1,
    "results": [
      {
        "model_name": "LOGIQ E9",
        "manufacturer": "GE Healthcare",
        "action": "created",
        "name": "IMM-MDL-2026-0003"
      },
      {
        "model_name": "",
        "manufacturer": "GE Healthcare",
        "action": "failed",
        "error": "model_name là bắt buộc",
        "code": "VALIDATION_ERROR"
      }
    ]
  }
}
```

### Response — Error (Empty List)

```json
{
  "success": false,
  "error": "Danh sách import không được rỗng",
  "code": "BULK-001"
}
```

### Response — Error (Exceeds Limit)

```json
{
  "success": false,
  "error": "Vượt quá giới hạn import (tối đa 500 bản ghi mỗi lần)",
  "code": "BULK-002"
}
```

### Example

```bash
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.bulk_update_device_model" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'items=[{"model_name":"LOGIQ E9","manufacturer":"GE Healthcare","medical_class":"Class II","risk_class":"Medium"}]'
```

---

## 14. `validate_asset_for_operations`

### Signature

```python
@frappe.whitelist()
def validate_asset_for_operations(asset_name: str) -> dict:
    """
    Kiểm tra xem tài sản có thể tạo lệnh công việc mới không.
    Trả về is_valid=True/False và danh sách lý do blocking.
    """
```

### HTTP

```
POST /api/method/assetcore.api.imm00.validate_asset_for_operations
```

### Permission Required

| Role | Access |
|---|---|
| All authenticated users | Read |

### Request Payload

```json
{
  "asset_name": "ACC-ICU-2026-0001"
}
```

### Business Rules Checked

| Rule Code | Condition | Blocking |
|---|---|---|
| VAL-01 | `lifecycle_status == "Decommissioned"` | Yes — hard block |
| VAL-02 | `lifecycle_status == "Out of Service"` | Yes — soft block (warning, requires override) |
| VAL-03 | `calibration_status == "Out of Tolerance"` | Warning only — non-blocking |
| VAL-04 | `imm_asset_profile` does not exist | Yes — hard block (IMM-00 not initialized) |
| VAL-05 | Active CAPA with `severity == "Critical"` | Warning — requires acknowledgement |

### Response — Valid (Can Create WO)

```json
{
  "success": true,
  "data": {
    "asset": "ACC-ICU-2026-0001",
    "is_valid": true,
    "lifecycle_status": "Active",
    "calibration_status": "In Tolerance",
    "blocking_reasons": [],
    "warnings": [],
    "can_create_work_order": true
  }
}
```

### Response — Blocked (Decommissioned)

```json
{
  "success": true,
  "data": {
    "asset": "ACC-ICU-2026-0001",
    "is_valid": false,
    "lifecycle_status": "Decommissioned",
    "calibration_status": "Not Required",
    "blocking_reasons": [
      {
        "code": "ASP-005",
        "message": "Tài sản đang Decommissioned — không thể tạo lệnh công việc",
        "severity": "error"
      }
    ],
    "warnings": [],
    "can_create_work_order": false
  }
}
```

### Response — Soft Block (Out of Service) with Warnings

```json
{
  "success": true,
  "data": {
    "asset": "ACC-ICU-2026-0001",
    "is_valid": false,
    "lifecycle_status": "Out of Service",
    "calibration_status": "Overdue",
    "blocking_reasons": [
      {
        "code": "ASP-006",
        "message": "Tài sản đang Out of Service — cần phê duyệt đặc biệt",
        "severity": "error"
      }
    ],
    "warnings": [
      {
        "code": "CAL-001",
        "message": "Hiệu chuẩn đã quá hạn — cần lên lịch hiệu chuẩn trước khi vận hành",
        "severity": "warning"
      },
      {
        "code": "CAPA-ACTIVE",
        "message": "Có 1 CAPA mức Critical đang mở cho tài sản này",
        "severity": "warning",
        "reference": "CAPA-2026-00001"
      }
    ],
    "can_create_work_order": false
  }
}
```

### Response — Error (Profile Not Initialized)

```json
{
  "success": false,
  "error": "Không tìm thấy hồ sơ IMM cho tài sản: ACC-ICU-9999. Vui lòng khởi tạo IMM Asset Profile trước.",
  "code": "ASP-002"
}
```

### Example

```javascript
// Typical use: called before opening Work Order creation form
frappe.call({
  method: "assetcore.api.imm00.validate_asset_for_operations",
  args: { asset_name: "ACC-ICU-2026-0001" },
  callback(r) {
    if (!r.message.success) {
      frappe.msgprint(r.message.error);
      return;
    }
    const result = r.message.data;
    if (!result.can_create_work_order) {
      const reasons = result.blocking_reasons.map((b) => b.message).join("\n");
      frappe.msgprint({
        title: "Không thể tạo Lệnh công việc",
        message: reasons,
        indicator: "red",
      });
      return;
    }
    if (result.warnings.length > 0) {
      const warns = result.warnings.map((w) => w.message).join("\n");
      frappe.confirm(
        `Cảnh báo:\n${warns}\n\nBạn có muốn tiếp tục không?`,
        () => open_work_order_form(result.asset)
      );
    } else {
      open_work_order_form(result.asset);
    }
  },
});
```

```bash
curl -X POST "https://hospital.example.com/api/method/assetcore.api.imm00.validate_asset_for_operations" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode 'asset_name=ACC-ICU-2026-0001'
```

---

## Summary Table

| # | Endpoint | Method Path | HTTP | Min Role | Purpose |
|---|---|---|---|---|---|
| 1 | `get_device_models` | `assetcore.api.imm00.get_device_models` | POST | Any | Paginated device model list |
| 2 | `get_device_model` | `assetcore.api.imm00.get_device_model` | POST | Any | Single device model + spare parts |
| 3 | `create_device_model` | `assetcore.api.imm00.create_device_model` | POST | Biomed/Admin | Create device model |
| 4 | `get_asset_profile` | `assetcore.api.imm00.get_asset_profile` | POST | Any | Get asset HTM profile |
| 5 | `update_asset_lifecycle_status` | `assetcore.api.imm00.update_asset_lifecycle_status` | POST | TECH+ | Change lifecycle status + audit |
| 6 | `get_vendor_profile` | `assetcore.api.imm00.get_vendor_profile` | POST | Any | Vendor HTM profile + technicians |
| 7 | `get_sla_policy` | `assetcore.api.imm00.get_sla_policy` | POST | Any | SLA policy lookup |
| 8 | `create_capa` | `assetcore.api.imm00.create_capa` | POST | TECH+ | Create CAPA record |
| 9 | `close_capa` | `assetcore.api.imm00.close_capa` | POST | BIOMED/QA/ADMIN | Close + submit CAPA |
| 10 | `get_asset_audit_trail` | `assetcore.api.imm00.get_asset_audit_trail` | POST | Any | Paginated audit timeline |
| 11 | `get_capa_list` | `assetcore.api.imm00.get_capa_list` | POST | Any HTM | CAPA list + summary stats |
| 12 | `get_asset_kpi_summary` | `assetcore.api.imm00.get_asset_kpi_summary` | POST | Any | MTD KPI for one asset |
| 13 | `bulk_update_device_model` | `assetcore.api.imm00.bulk_update_device_model` | POST | ADMIN | Bulk import device models |
| 14 | `validate_asset_for_operations` | `assetcore.api.imm00.validate_asset_for_operations` | POST | Any | Pre-WO creation gate check |

---

## Error Code Reference (IMM-00 API)

| Code | HTTP Equiv | Endpoint(s) | Vietnamese Message |
|---|---|---|---|
| MDL-001 | 400 | create_device_model, bulk_update_device_model | Tên model đã tồn tại cho nhà sản xuất này |
| ASP-002 | 404 | get_asset_profile, update_asset_lifecycle_status, create_capa, get_asset_audit_trail, get_asset_kpi_summary, validate_asset_for_operations | Không tìm thấy hồ sơ IMM cho tài sản |
| ASP-005 | 400 | validate_asset_for_operations | Tài sản đang Decommissioned — không thể tạo lệnh công việc |
| ASP-006 | 400 | validate_asset_for_operations | Tài sản đang Out of Service — cần phê duyệt đặc biệt |
| VND-001 | 404 | get_vendor_profile | Không tìm thấy hồ sơ nhà cung cấp IMM |
| SLA-001 | 404 | get_sla_policy | Không tìm thấy SLA Policy phù hợp |
| CAPA-001 | 400 | create_capa | Mức độ nghiêm trọng không hợp lệ |
| CAPA-002 | 400 | close_capa | CAPA đã được đóng hoặc huỷ |
| CAPA-006 | 400 | close_capa | Kết quả xác minh không hợp lệ |
| STS-001 | 400 | update_asset_lifecycle_status | Trạng thái không hợp lệ |
| BULK-001 | 400 | bulk_update_device_model | Danh sách import không được rỗng |
| BULK-002 | 400 | bulk_update_device_model | Vượt quá giới hạn import (tối đa 500 bản ghi) |
| INVALID_FILTERS | 400 | get_device_models, get_capa_list | filters không phải JSON hợp lệ |
| INVALID_DATA | 400 | create_device_model | data không phải JSON hợp lệ |
| NOT_FOUND | 404 | get_device_model | Không tìm thấy bản ghi |
| FORBIDDEN | 403 | Any | Không có quyền thực hiện thao tác này |
| GENERIC_ERROR | 500 | Any | Lỗi hệ thống — vui lòng liên hệ CMMS Admin |
