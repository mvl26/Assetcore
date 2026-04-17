# IMM-11 — API Interface
## Endpoints, Payloads & Sequence Diagrams

**Module:** IMM-11
**Version:** 1.0
**Ngày:** 2026-04-17
**Trạng thái:** Draft

---

## 1. Sequence Diagrams

### 1.1 Schedule Calibration & Send to Lab

```
Frontend (Vue)          API (imm11.py)          Service (imm11.py)         DB (MariaDB)
     │                       │                        │                        │
     │─ POST create_cal ─────►│                        │                        │
     │  {asset_ref, type..}  │─ validate_asset() ─────►│                        │
     │                       │                        │─ get Asset info ────────►│
     │                       │                        │◄── device_model, interval┤
     │                       │◄── validation OK ───────│                        │
     │                       │─ frappe.get_doc() ─────────────────────────────►│
     │                       │  insert() ─────────────────────────────────────►│
     │                       │◄─── CAL-2026-00001 ─────────────────────────────│
     │◄─ {success, data} ─────│                        │                        │
     │                       │                        │                        │
     │─ POST send_to_lab ─────►│                        │                        │
     │  {name, lab_name,     │─ validate_lab_info() ──►│                        │
     │   accreditation_no,   │◄── OK ──────────────────│                        │
     │   sent_date}          │─ update status ──────────────────────────────►│
     │                       │  → "Sent to Lab"        │                        │
     │                       │─ create_lifecycle_event()►│                       │
     │                       │                        │─ insert Event ──────────►│
     │◄─ {success, status}────│                        │                        │
     │                       │                        │                        │
```

---

### 1.2 Submit Calibration Results — Pass Path

```
Frontend (Vue)          API (imm11.py)          Service (imm11.py)         DB (MariaDB)
     │                       │                        │                        │
     │─ POST submit_results ─►│                        │                        │
     │  {name,               │─ validate_external() ──►│                        │
     │   measurements:[..],  │◄── OK (cert. uploaded) ─│                        │
     │   certificate_date,   │─ compute_measurements()►│                        │
     │   certificate_file}   │◄── overall="Passed" ────│                        │
     │                       │─ doc.submit() ──────────────────────────────────►│
     │                       │    on_submit() ─────────►│                       │
     │                       │                        │─ update_asset_dates() ──►│
     │                       │                        │  next_cal = cert + 365  │
     │                       │                        │─ create_lifecycle_event()►│
     │                       │                        │  event="cal_completed"  │
     │◄─ {success,            │                        │                        │
     │    result:"Passed",   │                        │                        │
     │    next_cal_date}     │                        │                        │
     │                       │                        │                        │
```

---

### 1.3 Submit Calibration Results — Fail Path (với CAPA & Lookback)

```
Frontend (Vue)          API (imm11.py)          Service (imm11.py)         DB (MariaDB)
     │                       │                        │                        │
     │─ POST submit_results ─►│                        │                        │
     │  {measurements with   │─ compute_results() ────►│                        │
     │   1 out_of_tolerance} │◄── overall="Failed" ────│                        │
     │                       │─ doc.submit() ──────────────────────────────────►│
     │                       │   on_submit() ──────────►│                       │
     │                       │                        │─ SET asset OOS ─────────►│
     │                       │                        │  (BR-11-02)             │
     │                       │                        │─ INSERT CAPA Record ────►│
     │                       │                        │  status="Open"          │
     │                       │                        │─ GET assets same model──►│
     │                       │                        │◄── [ACC-104, ACC-105]───┤
     │                       │                        │─ UPDATE CAPA lookback───►│
     │                       │                        │  lookback_assets=[..]   │
     │                       │                        │─ INSERT LifecycleEvent──►│
     │                       │                        │  event="cal_failed"     │
     │                       │                        │─ sendmail() ────────────►│
     │                       │                        │  → QA + PTP             │
     │◄─ {success,           │◄── done ───────────────│                        │
     │    result:"Failed",   │                        │                        │
     │    capa_created,      │                        │                        │
     │    asset_status:"OOS"}│                        │                        │
     │                       │                        │                        │
     │  [User sees CAPA Modal]│                       │                        │
     │─ GET capa_detail ─────►│                        │                        │
     │◄─ {capa, lookback_list}│                        │                        │
```

---

### 1.4 CAPA Resolution & Asset Restore

```
Frontend (Vue)          API (imm11.py)          Service (imm11.py)         DB (MariaDB)
     │                       │                        │                        │
     │─ POST resolve_lookback►│                        │                        │
     │  {capa_name,          │─ validate CAPA status──►│                        │
     │   lookback_status,    │◄── OK ──────────────────│                        │
     │   lookback_findings}  │─ UPDATE CAPA ────────────────────────────────►│
     │◄─ {success}────────────│                        │                        │
     │                       │                        │                        │
     │─ POST close_capa ─────►│                        │                        │
     │  {capa_name, rca,     │─ validate_lookback ────►│                        │
     │   corrective_action,  │◄── lookback_status OK───│                        │
     │   preventive_action}  │─ CLOSE CAPA ─────────────────────────────────►│
     │                       │    actual_close_date=today                     │
     │                       │─ check_recalibration ──►│                       │
     │                       │◄── new_cal_passed ───────│                       │
     │                       │─ SET asset Active ───────────────────────────►│
     │                       │─ create_lifecycle_event()►│                      │
     │                       │  event="cal_conditionally_passed"               │
     │◄─ {success,           │                        │                        │
     │    asset_status:"Active"}│                      │                        │
```

---

## 2. Endpoints Table

| # | Method | Endpoint | Actor | Mô tả |
|---|---|---|---|---|
| 1 | POST | `assetcore.api.imm11.create_calibration` | KTV, Manager | Tạo Asset Calibration record mới |
| 2 | POST | `assetcore.api.imm11.send_to_lab` | KTV | Cập nhật status → "Sent to Lab", ghi ngày gửi |
| 3 | POST | `assetcore.api.imm11.receive_certificate` | KTV | Cập nhật status → "Certificate Received", ghi ngày nhận |
| 4 | POST | `assetcore.api.imm11.submit_calibration_results` | KTV | Submit kết quả, trigger Pass/Fail automation |
| 5 | POST | `assetcore.api.imm11.create_capa` | System/QA | Tạo CAPA record thủ công (ngoài auto-create) |
| 6 | POST | `assetcore.api.imm11.resolve_capa_lookback` | QA Officer | Cập nhật lookback_status + findings |
| 7 | POST | `assetcore.api.imm11.close_capa` | QA Officer | Đóng CAPA sau khi RCA + action hoàn thành |
| 8 | GET | `assetcore.api.imm11.get_calibration_list` | All | Danh sách calibration records với filter |
| 9 | GET | `assetcore.api.imm11.get_calibration_detail` | All | Chi tiết 1 calibration record |
| 10 | GET | `assetcore.api.imm11.get_capa_list` | All | Danh sách CAPA records |
| 11 | GET | `assetcore.api.imm11.get_calibration_compliance_report` | Manager, PTP | KPI compliance report theo tháng/năm |
| 12 | GET | `assetcore.api.imm11.get_asset_calibration_history` | All | Lịch sử calibration của 1 thiết bị |
| 13 | GET | `assetcore.api.imm11.get_due_calibrations` | Manager, PTP | Thiết bị đến hạn trong N ngày tới |

---

## 3. JSON Payloads

### 3.1 `create_calibration` — Request

```json
{
  "asset_ref": "ACC-ASS-2026-00101",
  "calibration_type": "External",
  "lab_name": "Trung tâm Đo lường Chất lượng 3",
  "lab_accreditation_number": "VLAS-T-028",
  "lab_contract_ref": "HĐ-2026-KĐ-015",
  "technician": "ktv.a@hospital.vn",
  "assigned_by": "manager@hospital.vn",
  "pm_work_order": null,
  "technician_notes": ""
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "CAL-2026-00001",
    "asset_ref": "ACC-ASS-2026-00101",
    "asset_name": "Máy phân tích huyết học Sysmex XN-1000",
    "device_model": "Sysmex XN-1000",
    "calibration_type": "External",
    "status": "Scheduled",
    "calibration_interval_days": 365,
    "due_date": "2026-05-01",
    "is_overdue": false
  }
}
```

---

### 3.2 `send_to_lab` — Request

```json
{
  "name": "CAL-2026-00001",
  "lab_name": "Trung tâm Đo lường Chất lượng 3",
  "lab_accreditation_number": "VLAS-T-028",
  "sent_date": "2026-04-20",
  "sent_by": "ktv.a@hospital.vn"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "CAL-2026-00001",
    "status": "Sent to Lab",
    "sent_date": "2026-04-20",
    "lifecycle_event": "ALE-2026-00087"
  }
}
```

---

### 3.3 `submit_calibration_results` — Request (Pass Case)

```json
{
  "name": "CAL-2026-00001",
  "certificate_date": "2026-04-24",
  "certificate_number": "2026-KĐ-01234",
  "certificate_file": "/files/2026-KĐ-01234_Sysmex-XN.pdf",
  "measurements": [
    {
      "parameter_name": "WBC Count",
      "unit": "10³/µL",
      "nominal_value": 7.5,
      "tolerance_plus": 3.0,
      "tolerance_minus": 3.0,
      "measured_value": 7.6,
      "notes": ""
    },
    {
      "parameter_name": "PLT Count",
      "unit": "10³/µL",
      "nominal_value": 250.0,
      "tolerance_plus": 5.0,
      "tolerance_minus": 5.0,
      "measured_value": 245.0,
      "notes": ""
    },
    {
      "parameter_name": "HGB",
      "unit": "g/dL",
      "nominal_value": 14.0,
      "tolerance_plus": 3.0,
      "tolerance_minus": 3.0,
      "measured_value": 14.2,
      "notes": ""
    }
  ],
  "calibration_sticker_attached": true,
  "sticker_photo": "/files/sticker-ACC-101-2026-04-24.jpg",
  "technician_notes": "Tất cả thông số trong giới hạn. Lab chứng nhận ngày 24/04/2026."
}
```

**Response (Pass):**
```json
{
  "success": true,
  "data": {
    "name": "CAL-2026-00001",
    "status": "Passed",
    "overall_result": "Passed",
    "certificate_date": "2026-04-24",
    "next_calibration_date": "2027-04-24",
    "asset_ref": "ACC-ASS-2026-00101",
    "asset_status": "Active",
    "capa_created": null,
    "lifecycle_event": "ALE-2026-00088",
    "measurements_summary": {
      "total": 3,
      "passed": 3,
      "failed": 0
    }
  }
}
```

---

### 3.4 `submit_calibration_results` — Response (Fail Case)

```json
{
  "success": true,
  "data": {
    "name": "CAL-2026-00002",
    "status": "Failed",
    "overall_result": "Failed",
    "asset_ref": "ACC-ASS-2026-00102",
    "asset_status": "Out of Service",
    "capa_created": "CAPA-2026-00015",
    "lookback_assets": [
      "ACC-ASS-2026-00104",
      "ACC-ASS-2026-00105",
      "ACC-ASS-2026-00106"
    ],
    "notifications_sent": ["qa.officer@hospital.vn", "ptp@hospital.vn"],
    "lifecycle_event": "ALE-2026-00089",
    "measurements_summary": {
      "total": 3,
      "passed": 2,
      "failed": 1,
      "failed_parameters": ["HGB"]
    }
  }
}
```

---

### 3.5 `create_capa` — Request (thủ công)

```json
{
  "asset_ref": "ACC-ASS-2026-00102",
  "calibration_ref": "CAL-2026-00002",
  "capa_type": "Calibration Failure",
  "description": "HGB measurement out of tolerance by 5.7%. Possible detector drift.",
  "assigned_to": "qa.officer@hospital.vn",
  "target_close_date": "2026-05-17"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00015",
    "status": "Open",
    "lookback_required": true,
    "lookback_status": "Pending",
    "lookback_assets": ["ACC-ASS-2026-00104", "ACC-ASS-2026-00105", "ACC-ASS-2026-00106"],
    "opened_date": "2026-04-17",
    "target_close_date": "2026-05-17"
  }
}
```

---

### 3.6 `resolve_capa_lookback` — Request

```json
{
  "name": "CAPA-2026-00015",
  "lookback_status": "Cleared",
  "lookback_findings": "Đã kiểm tra 3 thiết bị Sysmex XN-1000 cùng series. Không phát hiện drift tương tự. Có thể do môi trường lưu mẫu tại phòng XN Máu ACC-102."
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00015",
    "lookback_status": "Cleared",
    "status": "In Review"
  }
}
```

---

### 3.7 `close_capa` — Request

```json
{
  "name": "CAPA-2026-00015",
  "root_cause_analysis": "Detector drift do nhiệt độ bảo quản mẫu ngoài khoảng 18-22°C. Mẫu kiểm soát bảo quản sai quy trình trong 3 ngày.",
  "corrective_action": "Tái hiệu chuẩn thiết bị ACC-102 sau khi kiểm tra detector. Nhận chứng chỉ mới CAL-2026-00009.",
  "preventive_action": "Cài đặt cảm biến nhiệt độ tủ bảo quản mẫu. Đào tạo lại quy trình bảo quản mẫu cho KTV phòng XN Máu."
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00015",
    "status": "Closed",
    "actual_close_date": "2026-05-10",
    "asset_ref": "ACC-ASS-2026-00102",
    "asset_status": "Active",
    "days_to_close": 23
  }
}
```

---

### 3.8 `get_calibration_list` — Request & Response

**Request params:**
```
GET /api/method/assetcore.api.imm11.get_calibration_list
?status=Scheduled,Sent to Lab
&asset_ref=ACC-ASS-2026-00101
&calibration_type=External
&page=1
&page_size=20
&overdue_only=false
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total": 45,
    "page": 1,
    "page_size": 20,
    "records": [
      {
        "name": "CAL-2026-00001",
        "asset_ref": "ACC-ASS-2026-00101",
        "asset_name": "Máy phân tích huyết học Sysmex XN-1000",
        "calibration_type": "External",
        "status": "Scheduled",
        "lab_name": "Trung tâm Đo lường Chất lượng 3",
        "due_date": "2026-05-01",
        "is_overdue": false,
        "days_until_due": 14,
        "technician": "ktv.a@hospital.vn",
        "overall_result": null
      }
    ]
  }
}
```

---

### 3.9 `get_calibration_compliance_report` — Response

**Request params:**
```
GET /api/method/assetcore.api.imm11.get_calibration_compliance_report
?year=2026&month=4
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "2026-04",
    "kpis": {
      "compliance_rate_pct": 87.5,
      "total_scheduled": 16,
      "completed_on_time": 14,
      "completed_late": 1,
      "not_done": 1,
      "out_of_tolerance_rate_pct": 4.2,
      "total_measurements": 48,
      "failed_measurements": 2,
      "capa_open_count": 3,
      "capa_closed_within_30d": 2,
      "capa_closure_rate_pct": 66.7,
      "avg_days_to_calibration": 12.3
    },
    "by_asset_category": [
      {
        "category": "Huyết học",
        "total": 6,
        "completed": 6,
        "oot_count": 1,
        "compliance_pct": 100.0
      },
      {
        "category": "Hô hấp",
        "total": 5,
        "completed": 4,
        "oot_count": 0,
        "compliance_pct": 80.0
      }
    ],
    "trend_6months": [
      { "month": "2025-11", "compliance_pct": 82.0 },
      { "month": "2025-12", "compliance_pct": 85.0 },
      { "month": "2026-01", "compliance_pct": 90.0 },
      { "month": "2026-02", "compliance_pct": 88.0 },
      { "month": "2026-03", "compliance_pct": 91.0 },
      { "month": "2026-04", "compliance_pct": 87.5 }
    ],
    "overdue_assets": [
      {
        "asset_ref": "ACC-ASS-2026-00201",
        "asset_name": "Monitor BP Mindray MEC-1200",
        "days_overdue": 15,
        "last_cal_date": "2025-04-01"
      }
    ]
  }
}
```

---

## 4. Error Code Table

| Mã lỗi | HTTP | Message (Vietnamese) | Trigger |
|---|---|---|---|
| `ERR-11-001` | 422 | "Vui lòng upload Calibration Certificate trước khi Submit (BR-11-01)" | External cal không có certificate_file |
| `ERR-11-002` | 422 | "Vui lòng nhập Số công nhận ISO/IEC 17025 của tổ chức kiểm định (BR-11-01)" | External cal không có lab_accreditation_number |
| `ERR-11-003` | 422 | "Vui lòng nhập giá trị đo cho tất cả tham số trước khi Submit" | Measurement thiếu measured_value |
| `ERR-11-004` | 403 | "Không thể hủy Phiếu Hiệu chuẩn đã Submit. Vui lòng dùng Amend (BR-11-05)" | Cancel trên submitted record |
| `ERR-11-005` | 403 | "Không thể xóa Phiếu Hiệu chuẩn đã Submit (BR-11-05)" | Delete trên submitted record |
| `ERR-11-006` | 422 | "Thiết bị không có chu kỳ hiệu chuẩn trong Device Model" | calibration_interval_days null |
| `ERR-11-007` | 422 | "Lý do sửa đổi là bắt buộc khi Amend Phiếu Hiệu chuẩn (BR-11-05)" | Amend không có amendment_reason |
| `ERR-11-008` | 422 | "CAPA Record chưa hoàn thành Lookback. Vui lòng cập nhật trước khi đóng CAPA (BR-11-03)" | Close CAPA khi lookback_status = Pending |
| `ERR-11-009` | 422 | "Phân tích nguyên nhân gốc rễ (RCA) là bắt buộc trước khi đóng CAPA" | Close CAPA không có root_cause_analysis |
| `ERR-11-010` | 404 | "Không tìm thấy Phiếu Hiệu chuẩn: {name}" | CAL record không tồn tại |
| `ERR-11-011` | 403 | "Bạn không có quyền thực hiện thao tác này" | Permission denied |
| `ERR-11-012` | 409 | "Thiết bị đã có Phiếu Hiệu chuẩn đang xử lý: {name}" | Tạo CAL khi đã có record Open/Scheduled |
| `ERR-11-013` | 422 | "Không thể Submit: Phiếu Hiệu chuẩn đang ở trạng thái {status}" | Submit từ trạng thái không hợp lệ |
| `ERR-11-014` | 500 | "Lỗi hệ thống khi tạo CAPA Record. Vui lòng liên hệ Admin." | CAPA auto-create fail |

---

## 5. curl Examples

### 5.1 Tạo Calibration Record

```bash
curl -X POST \
  'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.create_calibration' \
  -H 'Authorization: token api_key:api_secret' \
  -H 'Content-Type: application/json' \
  -d '{
    "asset_ref": "ACC-ASS-2026-00101",
    "calibration_type": "External",
    "lab_name": "Trung tâm Đo lường Chất lượng 3",
    "lab_accreditation_number": "VLAS-T-028",
    "technician": "ktv.a@hospital.vn",
    "assigned_by": "manager@hospital.vn"
  }'
```

---

### 5.2 Gửi thiết bị đến Lab

```bash
curl -X POST \
  'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.send_to_lab' \
  -H 'Authorization: token api_key:api_secret' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "CAL-2026-00001",
    "lab_name": "Trung tâm Đo lường Chất lượng 3",
    "lab_accreditation_number": "VLAS-T-028",
    "sent_date": "2026-04-20",
    "sent_by": "ktv.a@hospital.vn"
  }'
```

---

### 5.3 Submit Kết quả Calibration (Pass)

```bash
curl -X POST \
  'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.submit_calibration_results' \
  -H 'Authorization: token api_key:api_secret' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "CAL-2026-00001",
    "certificate_date": "2026-04-24",
    "certificate_number": "2026-KĐ-01234",
    "certificate_file": "/files/2026-KĐ-01234_Sysmex-XN.pdf",
    "measurements": [
      {
        "parameter_name": "WBC Count",
        "unit": "10\u00b3/\u00b5L",
        "nominal_value": 7.5,
        "tolerance_plus": 3.0,
        "tolerance_minus": 3.0,
        "measured_value": 7.6
      },
      {
        "parameter_name": "HGB",
        "unit": "g/dL",
        "nominal_value": 14.0,
        "tolerance_plus": 3.0,
        "tolerance_minus": 3.0,
        "measured_value": 14.2
      }
    ],
    "calibration_sticker_attached": true,
    "technician_notes": "Thiết bị đạt tiêu chuẩn. Đã gắn sticker."
  }'
```

---

### 5.4 Đóng CAPA sau khi khắc phục

```bash
curl -X POST \
  'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.close_capa' \
  -H 'Authorization: token api_key:api_secret' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "CAPA-2026-00015",
    "root_cause_analysis": "Detector drift do nhiệt độ bảo quản mẫu ngoài khoảng 18-22°C.",
    "corrective_action": "Tái hiệu chuẩn thiết bị. Đã nhận chứng chỉ CAL-2026-00009.",
    "preventive_action": "Cài đặt cảm biến nhiệt độ. Đào tạo lại quy trình bảo quản mẫu."
  }'
```

---

### 5.5 Lấy Compliance Report

```bash
curl -X GET \
  'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.get_calibration_compliance_report?year=2026&month=4' \
  -H 'Authorization: token api_key:api_secret'
```

---

### 5.6 Lấy Lịch sử Calibration của 1 thiết bị

```bash
curl -X GET \
  'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.get_asset_calibration_history?asset_ref=ACC-ASS-2026-00101&limit=10' \
  -H 'Authorization: token api_key:api_secret'
```

---

## 6. API Implementation — `assetcore/api/imm11.py`

```python
"""
IMM-11 API Layer — Calibration endpoints.
Tất cả validation và business logic ở service layer.
"""

import frappe
from frappe import _
from assetcore.services.imm11 import (
    handle_calibration_pass,
    handle_calibration_fail,
    validate_external_calibration,
    compute_measurement_results,
)
from assetcore.utils.response import _ok, _err


@frappe.whitelist()
def create_calibration(**kwargs) -> dict:
    """
    Tạo Asset Calibration record mới.

    Args:
        asset_ref (str): Asset name — bắt buộc
        calibration_type (str): External hoặc In-House
        lab_name (str): Tên lab (bắt buộc nếu External)
        lab_accreditation_number (str): Số công nhận ISO/IEC 17025
        technician (str): User email/name
        assigned_by (str): User email/name

    Returns:
        dict: _ok(data) hoặc _err(message, code)
    """
    try:
        asset_ref = kwargs.get("asset_ref")
        if not asset_ref:
            return _err("asset_ref là bắt buộc", "ERR-11-010")

        # Kiểm tra duplicate active CAL (ERR-11-012)
        existing = frappe.db.exists("Asset Calibration", {
            "asset_ref": asset_ref,
            "status": ("in", ["Scheduled", "Sent to Lab", "In Progress", "Certificate Received"]),
        })
        if existing:
            return _err(f"Thiết bị đã có Phiếu Hiệu chuẩn đang xử lý: {existing}", "ERR-11-012")

        doc = frappe.get_doc({
            "doctype": "Asset Calibration",
            "asset_ref": asset_ref,
            "calibration_type": kwargs.get("calibration_type", "External"),
            "lab_name": kwargs.get("lab_name"),
            "lab_accreditation_number": kwargs.get("lab_accreditation_number"),
            "lab_contract_ref": kwargs.get("lab_contract_ref"),
            "technician": kwargs.get("technician", frappe.session.user),
            "assigned_by": kwargs.get("assigned_by", frappe.session.user),
            "pm_work_order": kwargs.get("pm_work_order"),
            "technician_notes": kwargs.get("technician_notes"),
            "status": "Scheduled",
        })
        doc.insert()
        return _ok(doc.as_dict())

    except frappe.ValidationError as e:
        return _err(str(e), "ERR-11-013")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "IMM-11 create_calibration error")
        return _err(str(e), "ERR-11-014")


@frappe.whitelist()
def send_to_lab(name: str, lab_name: str, lab_accreditation_number: str,
                sent_date: str, sent_by: str = None) -> dict:
    """Cập nhật status → Sent to Lab."""
    try:
        doc = frappe.get_doc("Asset Calibration", name)
        if doc.status != "Scheduled":
            return _err(f"Không thể chuyển trạng thái từ {doc.status}", "ERR-11-013")

        doc.status = "Sent to Lab"
        doc.lab_name = lab_name
        doc.lab_accreditation_number = lab_accreditation_number
        doc.sent_date = sent_date
        doc.sent_by = sent_by or frappe.session.user
        doc.save()

        from assetcore.services.imm11 import _create_lifecycle_event
        _create_lifecycle_event(
            asset=doc.asset_ref,
            event_type="calibration_sent_to_lab",
            from_status="Scheduled",
            to_status="Sent to Lab",
            root_record=name,
            actor=frappe.session.user,
        )
        return _ok({"name": name, "status": "Sent to Lab", "sent_date": sent_date})

    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy Phiếu Hiệu chuẩn: {name}", "ERR-11-010")


@frappe.whitelist()
def submit_calibration_results(name: str, measurements: list,
                                certificate_date: str = None,
                                certificate_number: str = None,
                                certificate_file: str = None,
                                calibration_sticker_attached: bool = False,
                                sticker_photo: str = None,
                                technician_notes: str = None) -> dict:
    """
    Submit kết quả calibration — trigger Pass/Fail automation.
    Đây là endpoint quan trọng nhất của IMM-11.
    """
    try:
        doc = frappe.get_doc("Asset Calibration", name)

        # Cập nhật measurements
        doc.measurements = []
        for m in measurements:
            doc.append("measurements", m)

        doc.certificate_date = certificate_date
        doc.certificate_number = certificate_number
        doc.certificate_file = certificate_file
        doc.calibration_sticker_attached = calibration_sticker_attached
        doc.sticker_photo = sticker_photo
        doc.technician_notes = technician_notes
        doc.status = "Certificate Received" if doc.calibration_type == "External" else "In Progress"
        doc.save()

        # Submit (triggers on_submit hook → business logic)
        doc.submit()

        return _ok({
            "name": doc.name,
            "status": doc.status,
            "overall_result": doc.overall_result,
            "next_calibration_date": doc.next_calibration_date,
            "asset_status": frappe.db.get_value("Asset", doc.asset_ref, "status"),
            "capa_created": frappe.db.get_value("CAPA Record", {"calibration_ref": name}, "name"),
        })

    except frappe.ValidationError as e:
        return _err(str(e), "ERR-11-001")


@frappe.whitelist()
def close_capa(name: str, root_cause_analysis: str,
               corrective_action: str, preventive_action: str) -> dict:
    """Đóng CAPA Record sau khi hoàn thành RCA và actions."""
    try:
        capa = frappe.get_doc("CAPA Record", name)

        if capa.lookback_required and capa.lookback_status == "Pending":
            return _err(
                "CAPA Record chưa hoàn thành Lookback. Vui lòng cập nhật trước khi đóng CAPA (BR-11-03)",
                "ERR-11-008"
            )

        if not root_cause_analysis:
            return _err("Phân tích nguyên nhân gốc rễ (RCA) là bắt buộc trước khi đóng CAPA", "ERR-11-009")

        capa.root_cause_analysis = root_cause_analysis
        capa.corrective_action = corrective_action
        capa.preventive_action = preventive_action
        capa.status = "Closed"
        capa.actual_close_date = frappe.utils.nowdate()
        capa.reviewed_by = frappe.session.user
        capa.save()

        # Kiểm tra nếu có recalibration pass → restore asset Active
        new_cal = frappe.db.get_value("Asset Calibration", {
            "asset_ref": capa.asset_ref,
            "overall_result": "Passed",
            "creation": (">", capa.opened_date),
        }, "name")

        if new_cal:
            frappe.db.set_value("Asset", capa.asset_ref, "status", "Active")
            from assetcore.services.imm11 import _create_lifecycle_event
            _create_lifecycle_event(
                asset=capa.asset_ref,
                event_type="calibration_conditionally_passed",
                from_status="Out of Service",
                to_status="Active",
                root_record=capa.name,
                actor=frappe.session.user,
                notes=f"CAPA {name} closed. Asset restored to Active.",
            )

        days_to_close = frappe.utils.date_diff(capa.actual_close_date, capa.opened_date)
        return _ok({
            "name": name,
            "status": "Closed",
            "actual_close_date": capa.actual_close_date,
            "asset_status": frappe.db.get_value("Asset", capa.asset_ref, "status"),
            "days_to_close": days_to_close,
        })

    except frappe.DoesNotExistError:
        return _err(f"Không tìm thấy CAPA Record: {name}", "ERR-11-010")


@frappe.whitelist()
def get_calibration_compliance_report(year: int, month: int) -> dict:
    """KPI compliance report cho IMM-11 dashboard."""
    from frappe.utils import get_first_day, get_last_day
    import datetime

    period_start = datetime.date(int(year), int(month), 1)
    period_end = get_last_day(period_start)

    total = frappe.db.count("Asset Calibration", {
        "due_date": ("between", [period_start, period_end]),
        "status": ("!=", "Cancelled"),
    })

    completed = frappe.db.count("Asset Calibration", {
        "due_date": ("between", [period_start, period_end]),
        "status": ("in", ["Passed", "Conditionally Passed", "Failed"]),
        "is_overdue": 0,
    })

    failed_cal = frappe.db.count("Asset Calibration", {
        "due_date": ("between", [period_start, period_end]),
        "overall_result": "Failed",
    })

    compliance_pct = round((completed / total * 100) if total > 0 else 0, 1)

    return _ok({
        "period": f"{year}-{month:02d}",
        "kpis": {
            "compliance_rate_pct": compliance_pct,
            "total_scheduled": total,
            "completed_on_time": completed,
            "failed_calibrations": failed_cal,
        }
    })
```
