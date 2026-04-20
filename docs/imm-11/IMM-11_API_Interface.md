# IMM-11 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-11 — Calibration / Hiệu chuẩn |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | DRAFT — chưa implement code (`assetcore/api/imm11.py` chưa tồn tại) |
| Base URL | `/api/method/assetcore.api.imm11` |
| Tác giả | AssetCore Team |

> ⚠️ **Pending implementation:** Toàn bộ endpoint dưới đây là đặc tả ahead-of-code. File `assetcore/api/imm11.py` và `assetcore/services/imm11.py` chưa tồn tại. Mọi sample request/response chỉ minh hoạ contract mong muốn.

---

## 1. Authentication

Theo chuẩn IMM-00. Hai phương thức:

```http
# API Token (server-to-server)
Authorization: token <api_key>:<api_secret>

# Session cookie (Frappe UI / SPA)
Cookie: sid=<session_id>
```

- Thiếu / sai credential → HTTP 401.
- Không có Role hợp lệ → HTTP 403.

---

## 2. Response Format

Tái sử dụng helper `assetcore/utils/response.py` của IMM-00. Mọi response gói trong `message`.

**Success (HTTP 200):**

```json
{
  "message": {
    "success": true,
    "data": { /* ... */ }
  }
}
```

**Error:**

```json
{
  "message": {
    "success": false,
    "error": "Thông báo lỗi tiếng Việt",
    "code": "ERR-11-XXX"
  }
}
```

---

## 3. Endpoints (đề xuất)

⚠️ Pending implementation — không endpoint nào đang chạy.

### 3.1 Bảng tổng quan

| # | Method | Endpoint | Actor | Mô tả |
|---|---|---|---|---|
| 1 | POST | `assetcore.api.imm11.create_calibration` | Workshop Lead, Technician | Tạo `IMM Asset Calibration` (Draft) |
| 2 | POST | `assetcore.api.imm11.send_to_lab` | Technician | External: status → Sent to Lab |
| 3 | POST | `assetcore.api.imm11.receive_certificate` | Technician | External: status → Certificate Received |
| 4 | POST | `assetcore.api.imm11.submit_calibration_results` | Technician | Submit + trigger Pass/Fail automation |
| 5 | POST | `assetcore.api.imm11.cancel_calibration` | Workshop Lead | Cancel khi `docstatus=0` (BR-11-05 block sau Submit) |
| 6 | POST | `assetcore.api.imm11.amend_calibration` | Workshop Lead | Amend với `amendment_reason` bắt buộc |
| 7 | GET | `assetcore.api.imm11.get_calibration_list` | All | Danh sách (pagination + filters) |
| 8 | GET | `assetcore.api.imm11.get_calibration_detail` | All | Chi tiết 1 record |
| 9 | GET | `assetcore.api.imm11.get_due_calibrations` | Workshop Lead, Manager | Thiết bị due trong N ngày |
| 10 | GET | `assetcore.api.imm11.get_asset_calibration_history` | All | Lịch sử cal của 1 asset |
| 11 | GET | `assetcore.api.imm11.get_calibration_compliance_report` | Manager, Department Head | KPI report theo tháng |
| 12 | POST | `assetcore.api.imm11.resolve_capa_lookback` | QA Officer | Cập nhật `lookback_status` + findings (proxy IMM-00 CAPA) |
| 13 | POST | `assetcore.api.imm11.close_capa` | QA Officer | Đóng CAPA (delegate `close_capa()` IMM-00 + restore Active) |
| 14 | POST | `assetcore.api.imm11.create_calibration_schedule` | Workshop Lead, Admin | Tạo Schedule manual (ngoài auto từ IMM-04) |
| 15 | PUT | `assetcore.api.imm11.update_calibration_schedule` | Workshop Lead | Cập nhật `interval_days`, `preferred_lab`, `is_active` |

### 3.2 Endpoint chi tiết

#### 3.2.1 POST `create_calibration`

⚠️ Pending implementation.

**Request:**

```json
{
  "asset": "AC-ASSET-2026-00101",
  "calibration_type": "External",
  "lab_supplier": "AC-SUP-2026-0010",
  "lab_accreditation_number": "VLAS-T-028",
  "scheduled_date": "2026-05-01",
  "technician": "ktv.a@hospital.vn",
  "is_recalibration": 0,
  "pm_work_order": null,
  "notes": ""
}
```

**Response:**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "CAL-2026-00001",
      "asset": "AC-ASSET-2026-00101",
      "device_model": "IMM-MDL-2026-0001",
      "calibration_type": "External",
      "status": "Scheduled",
      "calibration_interval_days": 365,
      "scheduled_date": "2026-05-01",
      "lab_supplier": "AC-SUP-2026-0010",
      "lab_supplier_iso_17025": true
    }
  }
}
```

**Validation:**
- BR-11-01: `lab_supplier.iso_17025_certified` phải = 1 → ERR-11-002
- BR-11-07: `validate_asset_for_operations(asset)` (skip nếu `is_recalibration=1`) → ERR-11-015

---

#### 3.2.2 POST `send_to_lab`

⚠️ Pending implementation.

**Request:**

```json
{
  "name": "CAL-2026-00001",
  "sent_date": "2026-04-20",
  "sent_by": "ktv.a@hospital.vn",
  "handover_doc": "/files/bien-ban-giao-nhan.pdf"
}
```

**Response:**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "CAL-2026-00001",
      "status": "Sent to Lab",
      "sent_date": "2026-04-20",
      "lifecycle_event": "ALE-2026-00087"
    }
  }
}
```

---

#### 3.2.3 POST `submit_calibration_results`

⚠️ Pending implementation. Endpoint quan trọng nhất — trigger Pass/Fail automation.

**Request (Pass case):**

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
      "tolerance_positive": 3.0,
      "tolerance_negative": 3.0,
      "measured_value": 7.6
    },
    {
      "parameter_name": "HGB",
      "unit": "g/dL",
      "nominal_value": 14.0,
      "tolerance_positive": 3.0,
      "tolerance_negative": 3.0,
      "measured_value": 14.2
    }
  ],
  "calibration_sticker_attached": true,
  "sticker_photo": "/files/sticker.jpg",
  "technician_notes": "Tất cả tham số trong tolerance."
}
```

**Response (Pass):**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "CAL-2026-00001",
      "status": "Passed",
      "overall_result": "Passed",
      "certificate_date": "2026-04-24",
      "next_calibration_date": "2027-04-24",
      "asset": "AC-ASSET-2026-00101",
      "asset_lifecycle_status": "Active",
      "capa_created": null,
      "lifecycle_event": "ALE-2026-00088",
      "measurements_summary": {"total": 2, "passed": 2, "failed": 0}
    }
  }
}
```

**Response (Fail):**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "CAL-2026-00002",
      "status": "Failed",
      "overall_result": "Failed",
      "asset": "AC-ASSET-2026-00102",
      "asset_lifecycle_status": "Out of Service",
      "capa_created": "CAPA-2026-00015",
      "lookback_assets": ["AC-ASSET-2026-00104", "AC-ASSET-2026-00105"],
      "notifications_sent": ["qa.officer@hospital.vn", "ops@hospital.vn"],
      "lifecycle_event": "ALE-2026-00089",
      "measurements_summary": {"total": 3, "passed": 2, "failed": 1, "failed_parameters": ["HGB"]}
    }
  }
}
```

**Side effects (Fail):**
1. `transition_asset_status(asset, "Out of Service", root_doctype="IMM Asset Calibration", root_record=name)` (IMM-00)
2. `create_capa(asset, source_type="IMM Asset Calibration", source_ref=name, severity="Major", responsible="IMM QA Officer")` (IMM-00)
3. `perform_lookback_assessment(device_model, exclude=asset)` → ghi `lookback_assets` vào CAPA
4. `create_lifecycle_event(asset, "calibration_failed", ...)` (IMM-00)
5. `log_audit_event(...)` (IMM-00)
6. Email QA Officer + Operations Manager

---

#### 3.2.4 POST `close_capa`

⚠️ Pending implementation. Wraps IMM-00 `close_capa()` + asset restore.

**Request:**

```json
{
  "name": "CAPA-2026-00015",
  "root_cause": "Detector drift do nhiệt độ bảo quản mẫu ngoài 18-22°C",
  "corrective_action": "Tái hiệu chuẩn thiết bị; đã nhận chứng chỉ CAL-2026-00009",
  "preventive_action": "Cài cảm biến nhiệt tủ mẫu; đào tạo lại quy trình",
  "effectiveness_check": "Effective",
  "verification_notes": "Tái cal Pass; theo dõi 30 ngày không tái phát"
}
```

**Response:**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "CAPA-2026-00015",
      "status": "Closed",
      "closed_date": "2026-05-10",
      "asset": "AC-ASSET-2026-00102",
      "asset_lifecycle_status": "Active",
      "lifecycle_event": "ALE-2026-00099",
      "days_to_close": 23
    }
  }
}
```

**Validation:**
- BR-11-03: block nếu `lookback_status = Pending` → ERR-11-008
- BR-00-08: `root_cause + corrective_action + preventive_action` bắt buộc → ERR-11-009

---

#### 3.2.5 GET `get_calibration_compliance_report`

⚠️ Pending implementation.

**Request:** `?year=2026&month=4`

**Response:**

```json
{
  "message": {
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
        "avg_days_sent_to_cert": 12.3
      },
      "by_asset_category": [
        {"category": "Huyết học", "total": 6, "completed": 6, "oot": 1, "compliance_pct": 100.0}
      ],
      "trend_6months": [
        {"month": "2025-11", "compliance_pct": 82.0}
      ],
      "overdue_assets": [
        {"asset": "AC-ASSET-2026-00201", "asset_name": "Monitor BP", "days_overdue": 15}
      ]
    }
  }
}
```

---

## 4. Error Codes

| Code | HTTP | Message (vi) | Trigger |
|---|---|---|---|
| ERR-11-001 | 422 | "Vui lòng upload Calibration Certificate trước khi Submit (BR-11-01)" | External thiếu `certificate_file` |
| ERR-11-002 | 422 | "Vui lòng chọn lab có chứng chỉ ISO/IEC 17025 (BR-11-01)" | `lab_supplier.iso_17025_certified=0` |
| ERR-11-003 | 422 | "Vui lòng nhập Số công nhận ISO/IEC 17025 (BR-11-01)" | Thiếu `lab_accreditation_number` |
| ERR-11-004 | 422 | "Vui lòng nhập giá trị đo cho tất cả tham số" | Measurement thiếu `measured_value` |
| ERR-11-005 | 403 | "Không thể hủy Phiếu Hiệu chuẩn đã Submit. Vui lòng dùng Amend (BR-11-05)" | Cancel record `docstatus=1` |
| ERR-11-006 | 403 | "Không thể xóa Phiếu Hiệu chuẩn đã Submit (BR-11-05)" | Delete record `docstatus=1` |
| ERR-11-007 | 422 | "Thiết bị không có chu kỳ hiệu chuẩn trong Device Model" | `calibration_interval_days` null |
| ERR-11-008 | 422 | "CAPA chưa hoàn thành Lookback. Vui lòng cập nhật trước khi đóng (BR-11-03)" | Close CAPA khi `lookback_status=Pending` |
| ERR-11-009 | 422 | "Phải nhập root_cause + corrective_action + preventive_action trước khi đóng CAPA" | BR-00-08 |
| ERR-11-010 | 404 | "Không tìm thấy Phiếu Hiệu chuẩn: {name}" | Record không tồn tại |
| ERR-11-011 | 403 | "Bạn không có quyền thực hiện thao tác này" | Permission denied |
| ERR-11-012 | 409 | "Thiết bị đã có Phiếu Hiệu chuẩn đang xử lý: {name}" | Tạo CAL khi có record đang Open |
| ERR-11-013 | 422 | "Không thể chuyển trạng thái từ {status}" | State machine vi phạm |
| ERR-11-014 | 422 | "Lý do sửa đổi là bắt buộc khi Amend (BR-11-05)" | Amend không có `amendment_reason` |
| ERR-11-015 | 422 | "Thiết bị ở trạng thái {status}, không thể tạo Calibration WO (BR-00-05)" | `validate_asset_for_operations()` block |
| ERR-11-016 | 422 | "Ngày cấp chứng chỉ không thể là ngày trong tương lai" | `certificate_date > today` |
| ERR-11-500 | 500 | "Lỗi hệ thống. Vui lòng liên hệ Admin." | Exception unhandled |

---

## 5. Webhook / Lifecycle Events

⚠️ Pending implementation. IMM-11 không expose webhook outbound; thay vào đó tạo `Asset Lifecycle Event` (IMM-00) — modules khác subscribe qua doc_events.

| event_type | Phát ở | Payload chính |
|---|---|---|
| `calibration_scheduled` | `create_calibration` (Draft tạo từ scheduler hoặc manual) | asset, root_record=CAL name |
| `calibration_sent_to_lab` | `send_to_lab` | asset, root_record, lab_supplier |
| `calibration_completed` | `on_submit` Pass | asset, root_record, certificate_date, next_calibration_date |
| `calibration_failed` | `on_submit` Fail | asset, root_record, capa_ref, lookback_assets |
| `calibration_conditionally_passed` | `close_capa` + recalibration Pass | asset, root_record=CAPA name |

Mọi event → `IMM Audit Trail` (SHA-256 chain) qua `log_audit_event()`.

---

## 6. Implementation Notes

⚠️ Pending implementation. Skeleton định hướng cho `assetcore/api/imm11.py`:

```python
# assetcore/api/imm11.py  -- ⚠️ FILE CHƯA TỒN TẠI
"""
IMM-11 API Layer — Calibration endpoints.
Validation và business logic ở service layer (services/imm11.py).
Mọi response qua _ok / _err.
"""
import frappe
from frappe import _
from assetcore.services.imm11 import (
    create_calibration_record,
    handle_send_to_lab,
    handle_submit_results,
    handle_close_capa,
)
from assetcore.utils.response import _ok, _err


@frappe.whitelist()
def create_calibration(**kwargs) -> dict:
    """Tạo IMM Asset Calibration (Draft). Validate qua service."""
    try:
        doc = create_calibration_record(kwargs)
        return _ok(doc.as_dict())
    except frappe.ValidationError as e:
        return _err(str(e), "ERR-11-013")


@frappe.whitelist()
def submit_calibration_results(name: str, measurements: list, **kwargs) -> dict:
    """Submit kết quả — trigger Pass/Fail automation qua service layer."""
    try:
        result = handle_submit_results(name, measurements, kwargs)
        return _ok(result)
    except frappe.ValidationError as e:
        return _err(str(e), "ERR-11-001")
```

**Bắt buộc:**
- Mọi endpoint `@frappe.whitelist()`
- Permission check qua DocType perm + Permission Query (IMM Technician scope)
- Logging qua `frappe.logger("imm11")` với request_id + actor
- Không chứa business logic — gọi `services/imm11.py`
- Sử dụng IMM-00 services: `get_sla_policy`, `validate_asset_for_operations`, `transition_asset_status`, `create_capa`, `close_capa`, `log_audit_event`, `create_lifecycle_event`

---

## 7. curl Examples

⚠️ Pending implementation — endpoints chưa tồn tại.

```bash
# 1. Tạo Calibration record
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.create_calibration' \
  -H 'Authorization: token <api_key>:<api_secret>' \
  -H 'Content-Type: application/json' \
  -d '{
    "asset": "AC-ASSET-2026-00101",
    "calibration_type": "External",
    "lab_supplier": "AC-SUP-2026-0010",
    "lab_accreditation_number": "VLAS-T-028",
    "scheduled_date": "2026-05-01"
  }'

# 2. Submit kết quả
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.submit_calibration_results' \
  -H 'Authorization: token <api_key>:<api_secret>' \
  -H 'Content-Type: application/json' \
  -d '{ "name": "CAL-2026-00001", "certificate_date": "2026-04-24", ... }'

# 3. Compliance report
curl -X GET 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.get_calibration_compliance_report?year=2026&month=4' \
  -H 'Authorization: token <api_key>:<api_secret>'
```

---

## 8. Pagination & Filter Convention

Theo IMM-00 (`utils/pagination.py`).

| Param | Default | Max |
|---|---|---|
| `page` | 1 | — |
| `page_size` | 20 | 100 |
| `sort` | `modified desc` | — |

Filter operators:
- Exact: `{"status": "Scheduled"}`
- Operator: `{"scheduled_date": ["<=", "2026-05-01"]}`
- IN: `{"status": ["in", ["Scheduled", "Sent to Lab"]]}`
- Like: `{"asset": ["like", "%AC-ASSET-2026%"]}`

---

## 9. Rate Limiting

Theo Frappe default + IMM-00 convention. Endpoint write-heavy (`submit_calibration_results`) khuyến nghị rate-limit 60/phút/user.
