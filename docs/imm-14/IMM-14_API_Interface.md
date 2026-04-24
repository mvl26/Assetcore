# IMM-14 — Giải nhiệm Thiết bị: Đóng Hồ sơ & Lưu trữ Vĩnh viễn
## API Interface — OpenAPI 3.0

| Thuộc tính    | Giá trị                                                             |
|---------------|---------------------------------------------------------------------|
| Module        | IMM-14 — API Interface                                              |
| Phiên bản     | 2.0.0                                                               |
| Ngày cập nhật | 2026-04-24                                                          |
| Base URL      | `/api/method/assetcore.api.imm14.`                                  |
| Auth          | Bearer Token (Frappe API Key) hoặc Session Cookie                  |
| Response      | `_ok(data)` / `_err(message, code)` — AssetCore standard pattern   |

---

## Tổng quan 10 Endpoints

| #  | Method | Path                           | Mô tả                                       |
|----|--------|--------------------------------|---------------------------------------------|
| 1  | POST   | `create_archive_record`        | Tạo Archive Record thủ công                 |
| 2  | GET    | `get_archive_record`           | Lấy chi tiết 1 AAR                          |
| 3  | POST   | `compile_asset_history`        | Biên soạn lịch sử thiết bị tự động         |
| 4  | POST   | `verify_documents`             | QA xác minh tính đầy đủ                    |
| 5  | POST   | `submit_for_approval`          | Gửi lên HTM Manager phê duyệt              |
| 6  | POST   | `approve_archive`              | HTM Manager phê duyệt cuối                 |
| 7  | POST   | `finalize_archive`             | Submit & khóa hồ sơ vĩnh viễn             |
| 8  | GET    | `get_lifecycle_timeline`       | Timeline vòng đời đầy đủ của thiết bị      |
| 9  | GET    | `search_archived_assets`       | Tìm kiếm hồ sơ lưu trữ dài hạn            |
| 10 | GET    | `get_dashboard_metrics`        | KPI Dashboard IMM-14                        |

---

## 1. create_archive_record

Tạo Asset Archive Record thủ công (không phải auto từ IMM-13).

**Method:** `POST`
**Path:** `/api/method/assetcore.api.imm14.create_archive_record`
**Auth:** Required — Role: IMM CMMS Admin, System Manager
**Content-Type:** `application/json`

### Request Body

```json
{
  "asset": "MRI-2024-001",
  "decommission_request": "DR-26-04-00001",
  "archive_date": "2026-04-25",
  "storage_location": "Server DMS / Tủ văn thư P.TBYT Kệ A3",
  "retention_years": 10,
  "archive_notes": "Lưu trữ sau khi hoàn tất giải nhiệm MRI 1.5T"
}
```

| Field                  | Type   | Required | Mô tả                                    |
|------------------------|--------|----------|------------------------------------------|
| `asset`                | string | Yes      | Link đến AC Asset                        |
| `decommission_request` | string | No       | Link đến Decommission Request (IMM-13)   |
| `archive_date`         | date   | Yes      | Ngày lưu trữ (YYYY-MM-DD)               |
| `storage_location`     | string | No       | Vị trí lưu trữ vật lý hoặc digital      |
| `retention_years`      | int    | No       | Số năm lưu trữ, mặc định 10             |
| `archive_notes`        | string | No       | Ghi chú lưu trữ                          |

### Response 200 — Success

```json
{
  "success": true,
  "data": {
    "name": "AAR-26-00001",
    "asset": "MRI-2024-001",
    "asset_name": "MRI 1.5T Siemens Magnetom",
    "decommission_request": "DR-26-04-00001",
    "archive_date": "2026-04-25",
    "release_date": "2036-04-25",
    "retention_years": 10,
    "status": "Draft",
    "docstatus": 0
  }
}
```

### Response 400 — Validation Error

```json
{
  "success": false,
  "error": "Asset Archive Record đã tồn tại cho MRI-2024-001: AAR-26-00001.",
  "code": "DUPLICATE_ARCHIVE"
}
```

### Response 403 — Unauthorized

```json
{
  "success": false,
  "error": "Không có quyền tạo Asset Archive Record.",
  "code": "PERMISSION_DENIED"
}
```

---

## 2. get_archive_record

Lấy chi tiết đầy đủ một Asset Archive Record bao gồm documents và metadata.

**Method:** `GET`
**Path:** `/api/method/assetcore.api.imm14.get_archive_record`
**Auth:** Required — Role: IMM HTM Manager, IMM CMMS Admin, IMM QA Officer
**Content-Type:** `application/json`

### Query Parameters

| Param  | Type   | Required | Mô tả                              |
|--------|--------|----------|------------------------------------|
| `name` | string | Yes      | Mã AAR, ví dụ: `AAR-26-00001`     |

### Request Example

```
GET /api/method/assetcore.api.imm14.get_archive_record?name=AAR-26-00001
```

### Response 200 — Success

```json
{
  "success": true,
  "data": {
    "name": "AAR-26-00001",
    "asset": "MRI-2024-001",
    "asset_name": "MRI 1.5T Siemens Magnetom",
    "asset_serial_no": "SN-SIEM-MRI-2011-0432",
    "device_model": "Siemens Magnetom Avanto 1.5T",
    "department": "Khoa Chẩn đoán Hình ảnh",
    "decommission_request": "DR-26-04-00001",
    "archive_date": "2026-04-25",
    "release_date": "2036-04-25",
    "retention_years": 10,
    "storage_location": "Server DMS / Tủ văn thư P.TBYT Kệ A3",
    "status": "Compiling",
    "docstatus": 0,
    "total_documents_archived": 36,
    "reconcile_cmms": 1,
    "reconcile_inventory": 0,
    "reconcile_finance": 0,
    "reconcile_legal": 0,
    "qa_verified_by": null,
    "approved_by": null,
    "documents": [
      {
        "document_type": "Commissioning",
        "source_module": "IMM-04",
        "document_name": "IMM04-11-03-00001",
        "document_date": "2011-03-15",
        "archive_status": "Included",
        "is_required": 1,
        "document_ref_url": null,
        "notes": ""
      },
      {
        "document_type": "Calibration",
        "source_module": "IMM-11",
        "document_name": null,
        "document_date": null,
        "archive_status": "Missing",
        "is_required": 0,
        "document_ref_url": null,
        "notes": "Không tìm thấy hồ sơ Calibration"
      }
    ],
    "archive_notes": "Lưu trữ sau khi hoàn tất giải nhiệm MRI 1.5T"
  }
}
```

### Response 404 — Not Found

```json
{
  "success": false,
  "error": "Asset Archive Record AAR-26-99999 không tồn tại.",
  "code": "NOT_FOUND"
}
```

---

## 3. compile_asset_history

Tự động biên soạn lịch sử thiết bị từ tất cả module (IMM-04/05/08/09/11/12/13). Ghi đè documents table.

**Method:** `POST`
**Path:** `/api/method/assetcore.api.imm14.compile_asset_history`
**Auth:** Required — Role: IMM CMMS Admin
**Content-Type:** `application/json`

### Request Body

```json
{
  "archive_name": "AAR-26-00001"
}
```

### Response 200 — Success

```json
{
  "success": true,
  "data": {
    "archive_name": "AAR-26-00001",
    "compiled": 36,
    "breakdown": {
      "Commissioning":        1,
      "Registration":         1,
      "PM Record":            24,
      "Repair Record":        3,
      "Calibration":          5,
      "Incident":             2,
      "Decommission Request": 1,
      "Service Contract":     0
    },
    "missing_count": 1,
    "status": "Compiling",
    "warnings": ["Không tìm thấy Service Contract cho thiết bị MRI-2024-001"]
  }
}
```

### Response 400 — Wrong State

```json
{
  "success": false,
  "error": "Không thể biên soạn khi hồ sơ đã Archived.",
  "code": "INVALID_STATE"
}
```

---

## 4. verify_documents

QA Officer xác minh tính đầy đủ hồ sơ. Chuyển trạng thái: Pending Verification → Pending Approval.

**Method:** `POST`
**Path:** `/api/method/assetcore.api.imm14.verify_documents`
**Auth:** Required — Role: IMM QA Officer
**Content-Type:** `application/json`

### Request Body

```json
{
  "name": "AAR-26-00001",
  "verified_by": "qa.officer@benhviennd1.vn",
  "notes": "Đã kiểm tra đủ 36 tài liệu theo checklist BM-IMMIS-14-01. Tất cả reconciliation đã xác nhận."
}
```

| Field         | Type   | Required | Mô tả                            |
|---------------|--------|----------|----------------------------------|
| `name`        | string | Yes      | Mã AAR                           |
| `verified_by` | string | Yes      | Email QA Officer                 |
| `notes`       | string | Yes      | Ghi chú xác minh (mandatory)     |

### Response 200 — Success

```json
{
  "success": true,
  "data": {
    "name": "AAR-26-00001",
    "status": "Pending Approval",
    "qa_verified_by": "qa.officer@benhviennd1.vn",
    "qa_verification_date": "2026-04-26",
    "notification_sent_to": "htm.manager@benhviennd1.vn"
  }
}
```

### Response 422 — Verification Failed

```json
{
  "success": false,
  "error": "Chưa đủ điều kiện xác minh:\n- Tài liệu bắt buộc chưa có: Commissioning\n- Chưa đối soát: Kế toán, Hồ sơ pháp lý",
  "code": "VERIFICATION_FAILED",
  "issues": [
    "Tài liệu bắt buộc chưa có: Commissioning",
    "Chưa đối soát: Kế toán, Hồ sơ pháp lý"
  ]
}
```

---

## 5. submit_for_approval

CMMS Admin gửi hồ sơ cho HTM Manager phê duyệt. Chuyển trạng thái: Compiling → Pending Verification.

**Method:** `POST`
**Path:** `/api/method/assetcore.api.imm14.submit_for_approval`
**Auth:** Required — Role: IMM CMMS Admin
**Content-Type:** `application/json`

### Request Body

```json
{
  "name": "AAR-26-00001",
  "submitted_by": "cmms.admin@benhviennd1.vn",
  "notes": "Đã compile đủ 36 tài liệu và đối soát kho, CMMS."
}
```

### Response 200 — Success

```json
{
  "success": true,
  "data": {
    "name": "AAR-26-00001",
    "status": "Pending Verification",
    "notification_sent_to": ["qa.officer1@benhviennd1.vn", "qa.officer2@benhviennd1.vn"]
  }
}
```

### Response 400 — Missing Reconciliation

```json
{
  "success": false,
  "error": "Chưa hoàn tất đối soát: thiếu xác nhận Kho, Kế toán.",
  "code": "RECONCILIATION_INCOMPLETE"
}
```

---

## 6. approve_archive

HTM Manager phê duyệt cuối. Chuyển trạng thái: Pending Approval → Finalized.

**Method:** `POST`
**Path:** `/api/method/assetcore.api.imm14.approve_archive`
**Auth:** Required — Role: IMM HTM Manager
**Content-Type:** `application/json`

### Request Body

```json
{
  "name": "AAR-26-00001",
  "approved_by": "htm.manager@benhviennd1.vn",
  "approved": true,
  "notes": "Đã review đủ. Hồ sơ đạt yêu cầu theo NĐ98/2021 §17."
}
```

| Field       | Type    | Required | Mô tả                                    |
|-------------|---------|----------|------------------------------------------|
| `name`      | string  | Yes      | Mã AAR                                   |
| `approved_by`| string | Yes      | Email HTM Manager                        |
| `approved`  | boolean | Yes      | `true` = phê duyệt, `false` = trả lại   |
| `notes`     | string  | Yes      | Ghi chú phê duyệt/trả lại               |

### Response 200 — Approved

```json
{
  "success": true,
  "data": {
    "name": "AAR-26-00001",
    "status": "Finalized",
    "approved_by": "htm.manager@benhviennd1.vn",
    "approval_date": "2026-04-27"
  }
}
```

### Response 200 — Rejected (returned to CMMS)

```json
{
  "success": true,
  "data": {
    "name": "AAR-26-00001",
    "status": "Compiling",
    "returned_reason": "Thiếu báo cáo tóm tắt vòng đời (Device Life Summary Report).",
    "notification_sent_to": "cmms.admin@benhviennd1.vn"
  }
}
```

---

## 7. finalize_archive

CMMS Admin Submit hồ sơ — khóa vĩnh viễn. Chuyển trạng thái: Finalized → Archived (docstatus=1).

**Method:** `POST`
**Path:** `/api/method/assetcore.api.imm14.finalize_archive`
**Auth:** Required — Role: IMM CMMS Admin
**Content-Type:** `application/json`

### Request Body

```json
{
  "name": "AAR-26-00001"
}
```

### Response 200 — Success

```json
{
  "success": true,
  "data": {
    "name": "AAR-26-00001",
    "status": "Archived",
    "docstatus": 1,
    "asset": "MRI-2024-001",
    "asset_status_updated": "Archived",
    "release_date": "2036-04-25",
    "lifecycle_event": "archived",
    "message": "Hồ sơ AAR-26-00001 đã được khóa vĩnh viễn. Hết hạn lưu trữ: 25/04/2036."
  }
}
```

### Response 400 — Not Finalized

```json
{
  "success": false,
  "error": "Không thể hoàn tất: Hồ sơ chưa được HTM Manager phê duyệt. Trạng thái hiện tại: Compiling.",
  "code": "NOT_FINALIZED"
}
```

---

## 8. get_lifecycle_timeline

Lấy toàn bộ timeline vòng đời của một thiết bị từ tất cả module, theo thứ tự thời gian.

**Method:** `GET`
**Path:** `/api/method/assetcore.api.imm14.get_lifecycle_timeline`
**Auth:** Required — Role: Any IMM role
**Content-Type:** `application/json`

### Query Parameters

| Param        | Type   | Required | Mô tả                              |
|--------------|--------|----------|------------------------------------|
| `asset_name` | string | Yes      | Mã AC Asset                        |

### Request Example

```
GET /api/method/assetcore.api.imm14.get_lifecycle_timeline?asset_name=MRI-2024-001
```

### Response 200 — Success

```json
{
  "success": true,
  "data": {
    "asset": "MRI-2024-001",
    "asset_name": "MRI 1.5T Siemens Magnetom",
    "serial_no": "SN-SIEM-MRI-2011-0432",
    "lifecycle_years": 15.1,
    "total_events": 87,
    "timeline": [
      {
        "date": "2011-03-15",
        "event_type": "commissioned",
        "module": "IMM-04",
        "record": "IMM04-11-03-00001",
        "actor": "engineer@benhviennd1.vn",
        "notes": "Lắp đặt tại Khoa Chẩn đoán Hình ảnh, tầng 3"
      },
      {
        "date": "2011-06-15",
        "event_type": "pm_completed",
        "module": "IMM-08",
        "record": "WO-PM-2011-00001",
        "actor": "technician@benhviennd1.vn",
        "notes": "PM quý 1/2011"
      },
      {
        "date": "2018-07-22",
        "event_type": "incident_reported",
        "module": "IMM-12",
        "record": "IR-18-07-00032",
        "actor": "nurse@benhviennd1.vn",
        "notes": "Lỗi gradient coil"
      },
      {
        "date": "2018-07-25",
        "event_type": "repaired",
        "module": "IMM-09",
        "record": "REP-18-07-00015",
        "actor": "technician@benhviennd1.vn",
        "notes": "Thay gradient coil"
      },
      {
        "date": "2026-04-21",
        "event_type": "decommissioned",
        "module": "IMM-13",
        "record": "DR-26-04-00001",
        "actor": "htm.manager@benhviennd1.vn",
        "notes": "Thanh lý EOL - hết khấu hao"
      },
      {
        "date": "2026-04-25",
        "event_type": "archived",
        "module": "IMM-14",
        "record": "AAR-26-00001",
        "actor": "cmms.admin@benhviennd1.vn",
        "notes": "Hồ sơ đã khóa vĩnh viễn"
      }
    ]
  }
}
```

---

## 9. search_archived_assets

Tìm kiếm và phân trang hồ sơ lưu trữ dài hạn với nhiều bộ lọc.

**Method:** `GET`
**Path:** `/api/method/assetcore.api.imm14.search_archived_assets`
**Auth:** Required — Role: Any IMM role
**Content-Type:** `application/json`

### Query Parameters

| Param          | Type    | Required | Mô tả                                          |
|----------------|---------|----------|------------------------------------------------|
| `asset`        | string  | No       | Tìm theo asset name / asset_name (LIKE)        |
| `status`       | string  | No       | Filter theo status (mặc định: Archived)        |
| `year`         | integer | No       | Lọc theo năm archive_date                      |
| `device_model` | string  | No       | Lọc theo device_model                          |
| `department`   | string  | No       | Lọc theo department                            |
| `page`         | integer | No       | Trang hiện tại (default: 1)                    |
| `page_size`    | integer | No       | Số dòng mỗi trang (default: 20, max: 100)      |

### Request Example

```
GET /api/method/assetcore.api.imm14.search_archived_assets?asset=MRI&year=2026&page=1&page_size=10
```

### Response 200 — Success

```json
{
  "success": true,
  "data": {
    "rows": [
      {
        "name": "AAR-26-00001",
        "asset": "MRI-2024-001",
        "asset_name": "MRI 1.5T Siemens Magnetom",
        "device_model": "Siemens Magnetom Avanto 1.5T",
        "department": "Khoa Chẩn đoán Hình ảnh",
        "archive_date": "2026-04-25",
        "release_date": "2036-04-25",
        "retention_years": 10,
        "total_documents_archived": 36,
        "status": "Archived",
        "days_until_expiry": 3652
      },
      {
        "name": "AAR-26-00003",
        "asset": "MRI-2015-003",
        "asset_name": "MRI 3T Philips Ingenia",
        "device_model": "Philips Ingenia 3T",
        "department": "Khoa Chẩn đoán Hình ảnh",
        "archive_date": "2026-03-01",
        "release_date": "2036-03-01",
        "retention_years": 10,
        "total_documents_archived": 42,
        "status": "Archived",
        "days_until_expiry": 3597
      }
    ],
    "total": 2,
    "page": 1,
    "page_size": 10
  }
}
```

---

## 10. get_dashboard_metrics

Lấy KPI Dashboard IMM-14 — tất cả metrics trên một request.

**Method:** `GET`
**Path:** `/api/method/assetcore.api.imm14.get_dashboard_metrics`
**Auth:** Required — Role: IMM HTM Manager, IMM CMMS Admin, IMM QA Officer
**Content-Type:** `application/json`

### Query Parameters

| Param  | Type    | Required | Mô tả                                             |
|--------|---------|----------|---------------------------------------------------|
| `year` | integer | No       | Năm lọc cho YTD metrics (default: năm hiện tại)   |

### Request Example

```
GET /api/method/assetcore.api.imm14.get_dashboard_metrics?year=2026
```

### Response 200 — Success

```json
{
  "success": true,
  "data": {
    "year": 2026,
    "summary": {
      "archived_ytd":                8,
      "total_archived_all_time":    45,
      "pending_verification":        2,
      "pending_approval":            1,
      "in_progress":                 3,
      "expiring_within_30_days":     0,
      "expiring_within_60_days":     1
    },
    "quality": {
      "avg_documents_per_archive":   32.5,
      "document_completeness_rate":  94.4,
      "missing_document_rate":        5.6,
      "reconciliation_closure_rate": 100.0
    },
    "performance": {
      "avg_time_to_archive_days":    8.3,
      "max_time_to_archive_days":    21,
      "min_time_to_archive_days":    3
    },
    "expiring_soon": [
      {
        "name": "AAR-16-00012",
        "asset": "ECG-2010-001",
        "asset_name": "ECG 12 chuyển đạo GE",
        "release_date": "2026-05-15",
        "days_until_expiry": 21
      }
    ],
    "by_department": [
      {"department": "Khoa CĐHA", "count": 12},
      {"department": "Khoa HSTC", "count": 8},
      {"department": "Phòng Mổ", "count": 5}
    ],
    "by_year": [
      {"year": 2024, "count": 5},
      {"year": 2025, "count": 12},
      {"year": 2026, "count": 8}
    ]
  }
}
```

---

## Error Codes Reference

| Code                       | HTTP | Mô tả                                              |
|----------------------------|------|----------------------------------------------------|
| `DUPLICATE_ARCHIVE`        | 400  | AAR đã tồn tại cho asset                           |
| `NOT_FOUND`                | 404  | AAR không tồn tại                                  |
| `INVALID_STATE`            | 400  | Action không hợp lệ với trạng thái hiện tại        |
| `VERIFICATION_FAILED`      | 422  | Chưa đủ điều kiện xác minh (documents/reconcile)  |
| `RECONCILIATION_INCOMPLETE`| 400  | Chưa đủ 4 reconciliation checkboxes               |
| `NOT_FINALIZED`            | 400  | Cố Submit khi chưa HTM Manager phê duyệt           |
| `PERMISSION_DENIED`        | 403  | Không đủ quyền thực hiện action                   |
| `ASSET_NOT_FOUND`          | 404  | AC Asset không tồn tại                             |
| `RETENTION_VIOLATION`      | 400  | retention_years < 10 (vi phạm NĐ98/2021 §17)      |
| `IMMUTABLE_RECORD`         | 400  | Cố edit AAR đã Archived (docstatus=1)              |

---

## API Implementation File

```python
# assetcore/api/imm14.py

import frappe
from assetcore.utils.response import _ok, _err
from assetcore.services import imm14 as svc


@frappe.whitelist()
def create_archive_record(**kwargs):
    try:
        data = svc.create_archive_record_manual(**kwargs)
        return _ok(data)
    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")


@frappe.whitelist()
def get_archive_record(name: str):
    try:
        doc = frappe.get_doc("Asset Archive Record", name)
        return _ok(doc.as_dict())
    except frappe.DoesNotExistError:
        return _err(f"Asset Archive Record {name} không tồn tại.", "NOT_FOUND")


@frappe.whitelist()
def compile_asset_history(archive_name: str):
    try:
        result = svc.compile_asset_history(archive_name)
        return _ok(result)
    except frappe.ValidationError as e:
        return _err(str(e), "INVALID_STATE")


@frappe.whitelist()
def verify_documents(name: str, verified_by: str, notes: str):
    try:
        svc.verify_archive(name, verified_by, notes)
        doc = frappe.get_cached_doc("Asset Archive Record", name)
        return _ok({"name": name, "status": doc.status,
                    "qa_verified_by": verified_by,
                    "qa_verification_date": str(doc.qa_verification_date)})
    except frappe.ValidationError as e:
        return _err(str(e), "VERIFICATION_FAILED")


@frappe.whitelist()
def submit_for_approval(name: str, submitted_by: str, notes: str = ""):
    try:
        result = svc.submit_for_qa_verification(name, submitted_by, notes)
        return _ok(result)
    except frappe.ValidationError as e:
        return _err(str(e), "RECONCILIATION_INCOMPLETE")


@frappe.whitelist()
def approve_archive(name: str, approved_by: str, approved: bool, notes: str):
    try:
        result = svc.approve_archive(name, approved_by, approved, notes)
        return _ok(result)
    except frappe.ValidationError as e:
        return _err(str(e), "INVALID_STATE")


@frappe.whitelist()
def finalize_archive(name: str):
    try:
        doc = frappe.get_doc("Asset Archive Record", name)
        doc.submit()  # triggers on_submit → finalize_archive_handler
        return _ok({"name": name, "status": "Archived", "docstatus": 1,
                    "release_date": str(doc.release_date)})
    except frappe.ValidationError as e:
        return _err(str(e), "NOT_FINALIZED")


@frappe.whitelist()
def get_lifecycle_timeline(asset_name: str):
    try:
        result = svc.get_lifecycle_timeline(asset_name)
        return _ok(result)
    except frappe.DoesNotExistError:
        return _err(f"AC Asset {asset_name} không tồn tại.", "ASSET_NOT_FOUND")


@frappe.whitelist()
def search_archived_assets(asset: str = None, status: str = None,
                            year: int = None, page: int = 1, page_size: int = 20):
    filters = {"asset": asset, "status": status, "year": year}
    filters = {k: v for k, v in filters.items() if v}
    result = svc.search_archived_assets(filters, page=int(page), page_size=int(page_size))
    return _ok(result)


@frappe.whitelist()
def get_dashboard_metrics(year: int = None):
    import frappe.utils
    year = int(year) if year else frappe.utils.getdate().year
    result = svc.get_dashboard_stats(year=year)
    return _ok(result)
```

---

*IMM-14 API Interface v2.0.0 — AssetCore / Bệnh viện Nhi Đồng 1*
*OpenAPI 3.0 · Frappe v15 · Pattern: _ok/_err*
