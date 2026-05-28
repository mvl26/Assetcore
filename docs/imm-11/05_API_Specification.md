# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-11 — Hiệu chuẩn (Calibration) |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm11.<function>` |
| Auth | Frappe session HOẶC `Authorization: token <key>:<secret>` |
| Cập nhật | 2026-05-27 |
| Trạng thái | ✅ Live — `assetcore/api/imm11.py` deployed (18 endpoint) |

---

## 0. API Catalog

✅ Tất cả endpoint dưới đây đã implement trong `assetcore/api/imm11.py`.

| # | Endpoint (actual @frappe.whitelist name) | Method | Mô tả | Role | Idempotent | US |
|---|---|---|---|---|---|---|
| 1 | `assetcore.api.imm11.list_calibration_schedules` | GET | List IMM Calibration Schedule + pagination | All | ✓ | US-11-01 |
| 2 | `assetcore.api.imm11.get_calibration_schedule` | GET | Chi tiết 1 Schedule | All | ✓ | US-11-01 |
| 3 | `assetcore.api.imm11.create_calibration_schedule` | POST | Tạo Schedule mới | Workshop Lead | ✗ | US-11-01 |
| 4 | `assetcore.api.imm11.update_calibration_schedule` | POST | Patch Schedule fields | Workshop Lead | ✓ | US-11-01 |
| 5 | `assetcore.api.imm11.delete_calibration_schedule` | POST | Xóa Schedule (nếu chưa có Submitted) | Workshop Lead | ✗ | US-11-01 |
| 6 | `assetcore.api.imm11.list_calibrations` | GET | List IMM Asset Calibration + pagination | All | ✓ | US-11-07 |
| 7 | `assetcore.api.imm11.get_calibration` | GET | Chi tiết 1 Calibration | All | ✓ | US-11-07 |
| 8 | `assetcore.api.imm11.create_calibration` | POST | Tạo Calibration WO | Workshop Lead, Technician | ✗ | US-11-02 |
| 9 | `assetcore.api.imm11.update_calibration` | POST | Update fields (allowed list) | Technician | ✓ | US-11-02 |
| 10 | `assetcore.api.imm11.submit_calibration` | POST | Submit → trigger Pass/Fail handler | Technician | ✗ | US-11-02 |
| 11 | `assetcore.api.imm11.add_measurement` | POST | Thêm tham số đo vào child table | Technician | ✗ | US-11-02 |
| 12 | `assetcore.api.imm11.get_calibration_kpis` | GET | KPI theo tháng | Ops Manager+ | ✓ | US-11-05 |
| 13 | `assetcore.api.imm11.get_calibration_dashboard` | GET | Dashboard đầy đủ (KPIs + lists) | All | ✓ | US-11-05 |
| 14 | `assetcore.api.imm11.get_asset_calibration_history` | GET | Lịch sử cal của 1 asset | All | ✓ | US-11-07 |
| 15 | `assetcore.api.imm11.send_to_lab` | POST | External: → Sent To Lab | Technician | ✓ | US-11-03 |
| 16 | `assetcore.api.imm11.receive_certificate` | POST | External: → In Progress (cert received) | Technician | ✓ | US-11-03 |
| 17 | `assetcore.api.imm11.cancel_calibration` | POST | Hủy phiếu chưa submit | Workshop Lead | ✗ | US-11-08 |
| 18 | `assetcore.api.imm11.get_due_calibrations` | GET | Thiết bị due ≤ N ngày | All | ✓ | US-11-01 |

---

## 1. Quy ước chung

### 1.1. Response success — format chuẩn AssetCore

```jsonc
{
  "success": true,
  "data": <payload — object / array / null>
}
```

FE đọc `response.data.data` (axios + Frappe lớp ngoài đã wrap).

**HTTP status:** Frappe luôn trả **HTTP 200** khi không có unhandled exception. Phân biệt success/error qua field `success`, KHÔNG qua HTTP code.

### 1.2. Response error — format chuẩn

```jsonc
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt",
  "code": "BUSINESS_RULE",
  "fields": {
    "lab_supplier": "Vui lòng chọn lab có chứng chỉ ISO/IEC 17025"
  }
}
```

### 1.3. Error code catalog

| Code | Khi nào |
|---|---|
| `NOT_FOUND` | IMM Asset Calibration / Asset / CAPA không tồn tại |
| `FORBIDDEN` | Không có quyền (role / Permission Query) |
| `VALIDATION` | Input validation fail (format, type, field thiếu) |
| `BUSINESS_RULE` | Vi phạm BR-11-xx (lab không ISO, lookback pending) |
| `CONFLICT` | Concurrent modify hoặc đã có CAL đang xử lý |
| `BAD_STATE` | State machine fail (Cancel sau Submit, OOS asset) |
| `INTERNAL` | Lỗi hệ thống unexpected |

### 1.4. Mapping FE ↔ BE error code

| BE (`ErrorCode`) | FE (`ErrorCode`) |
|---|---|
| `VALIDATION` | `VALIDATION_ERROR` |
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` |
| `NOT_FOUND` | `NOT_FOUND` |
| `FORBIDDEN` | `FORBIDDEN` |
| `CONFLICT` | `CONFLICT` |
| `BAD_STATE` | `BAD_STATE` |
| `INTERNAL` | `INTERNAL_ERROR` |

### 1.5. Pagination convention

```jsonc
{
  "success": true,
  "data": {
    "data": [...],
    "page": 1,
    "page_size": 20,
    "total": 145,
    "total_pages": 8
  }
}
```

---

## 2. Endpoint chi tiết

### 8. create_calibration — Tạo IMM Asset Calibration ✅ LIVE

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm11.create_calibration` |
| Role | Workshop Lead, IMM Technician |
| Idempotent | No |

**Request:**
```jsonc
{
  "asset": "AC-ASSET-2026-00101",       // required
  "calibration_type": "External",       // External | In-House
  "lab_supplier": "AC-SUP-2026-0010",   // required if External
  "scheduled_date": "2026-05-01",       // required
  "technician": "ktv.a@hospital.vn",   // required
  "is_recalibration": 0,               // default 0
  "pm_work_order": null
}
```

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "CAL-2026-00001",
    "asset": "AC-ASSET-2026-00101",
    "calibration_type": "External",
    "status": "Scheduled",
    "scheduled_date": "2026-05-01",
    "lab_supplier": "AC-SUP-2026-0010"
  }
}
```

**Errors:**
| Code (BE) | Code (FE) | Khi nào |
|---|---|---|
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` | lab không ISO 17025 (BR-11-01) |
| `BAD_STATE` | `BAD_STATE` | Asset Out of Service (không phải recal) |
| `CONFLICT` | `CONFLICT` | Đã có CAL đang xử lý cho asset này |

---

### 10. submit_calibration — Submit kết quả (quan trọng nhất) ✅ LIVE

> **Tên thực tế là `submit_calibration` (không phải `submit_calibration_results`).** Kết quả Pass/Fail được xác định bởi `overall_result` field trên DocType — tính từ measurements trước khi submit.

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm11.submit_calibration` |
| Role | IMM Technician |
| Idempotent | No |

**Request:**
```jsonc
{
  "name": "CAL-2026-00001"   // required — measurements đã add trước via add_measurement endpoint
}
```

> Measurements được nhập trước qua `add_measurement`. Sau đó `submit_calibration` submit DocType → controller on_submit → service `handle_calibration_pass` hoặc `handle_calibration_fail`.

**Response success (Pass):**
```jsonc
{
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
    "measurements_summary": {"total": 1, "passed": 1, "failed": 0}
  }
}
```

**Response success (Fail):**
```jsonc
{
  "success": true,
  "data": {
    "name": "CAL-2026-00002",
    "status": "Failed",
    "overall_result": "Failed",
    "asset": "AC-ASSET-2026-00102",
    "asset_lifecycle_status": "Out of Service",
    "capa_created": "CAPA-2026-00015",
    "lookback_assets": ["AC-ASSET-2026-00104", "AC-ASSET-2026-00105"],
    "lifecycle_event": "ALE-2026-00089",
    "measurements_summary": {"total": 3, "passed": 2, "failed": 1, "failed_parameters": ["HGB"]}
  }
}
```

**Errors:**
| Code (BE) | Code (FE) | Khi nào |
|---|---|---|
| `VALIDATION` | `VALIDATION_ERROR` | Thiếu measured_value cho tham số |
| `VALIDATION` | `VALIDATION_ERROR` | External thiếu certificate_file hoặc accreditation (BR-11-01) |
| `VALIDATION` | `VALIDATION_ERROR` | certificate_date > today (BR-11-04) |
| `BAD_STATE` | `BAD_STATE` | Cancel record đã Submit (BR-11-05) |

**Side effects (Fail):**
- `transition_asset_status(asset, "Out of Service")` (IMM-00)
- `create_capa(asset, "IMM Asset Calibration", name, "Major")` (IMM-00)
- `perform_lookback_assessment(device_model, exclude=asset)` → ghi lookback_assets vào CAPA
- `create_lifecycle_event(asset, "calibration_failed")` (IMM-00)
- Email QA Officer + Operations Manager

**Curl ví dụ:**
```bash
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.submit_calibration' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "CAL-2026-00001"}'

# Measurements được nhập trước qua `add_measurement` (xem §7 Smoke test).
```

---

### 12. get_calibration_kpis — KPI report ✅ LIVE

> **Tên thực tế là `get_calibration_kpis` (không phải `get_calibration_compliance_report`).**

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm11.get_calibration_kpis` |
| Role | All |
| Idempotent | Yes |

**Request:**
```jsonc
{ "year": 2026, "month": 4 }
```

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "period": "2026-04",
    "kpis": {
      "compliance_rate_pct": 87.5,
      "total_scheduled": 16,
      "completed_on_time": 14,
      "out_of_tolerance_rate_pct": 4.2,
      "capa_open_count": 3,
      "capa_closure_rate_pct": 66.7,
      "avg_days_sent_to_cert": 12.3
    },
    "overdue_assets": [
      {"asset": "AC-ASSET-2026-00201", "asset_name": "Monitor BP", "days_overdue": 15}
    ]
  }
}
```

---

## 7. Smoke test playbook

```bash
# 1. Tạo Calibration record
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.create_calibration' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"asset":"AC-ASSET-2026-00101","calibration_type":"External","scheduled_date":"2026-05-01","technician":"ktv@hospital.vn"}'

# 2. Thêm measurement
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.add_measurement' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"name":"CAL-2026-00001","parameter_name":"WBC","unit":"10³/µL","nominal_value":7.5,"tolerance_positive":3,"tolerance_negative":3,"measured_value":7.6}'

# 3. Submit (triggers Pass/Fail handler)
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.submit_calibration' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"name":"CAL-2026-00001"}'

# 4. KPI report
curl 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.get_calibration_kpis?year=2026&month=4' \
  -H 'Authorization: token <key>:<secret>'

# 5. Dashboard
curl 'https://hospital.assetcore.vn/api/method/assetcore.api.imm11.get_calibration_dashboard' \
  -H 'Authorization: token <key>:<secret>'
```

---

## DoD — File 05 hoàn chỉnh

- [x] API Catalog (§0) liệt kê 18 endpoint thực tế (actual @frappe.whitelist names)
- [x] Response success format `{"success": true, "data": {...}}`
- [x] Response error format `{"success": false, "error": "...", "code": "..."}`
- [x] Error code catalog + FE mapping
- [x] Endpoint `submit_calibration` (actual name) với request schema + response Pass + Fail
- [x] Side effects nêu rõ (Fail path)
- [x] Curl ví dụ (5 commands)
- [x] Pagination convention
- [x] ✅ FE types: `frontend/src/api/imm11.ts` (interfaces CalibrationSchedule, AssetCalibration, CalibrationMeasurement, CalibrationKpis, DueCalibrationItem)
- [x] ✅ FE store: `frontend/src/stores/imm11.ts` (useImm11Store)
- [ ] Reviewed bởi BE Lead + FE Lead
