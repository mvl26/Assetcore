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
| 18 | `assetcore.api.imm11.get_due_calibrations` | GET | Thiết bị due ≤ N ngày (filter `AC Asset.next_calibration_date` = MIN-lịch, BR-11-13 → asset multi-schedule KHÔNG rớt) | All | ✓ | US-11-01, AC-11-21 |

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

> Từ Sprint Notification 2026-05-29 vòng 4, error envelope IMM-11 hydrate thêm
> `message_code`, `severity`, `title`, `action_hint`, `context` qua
> `api_handler.handle()`. Xem **§11 — Notification Contract**.

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
    "next_calibration_date": "2027-04-24",   // = next_due của PHIẾU/lịch vừa Pass (basis+interval) — KHÔNG đổi (BR-11-04)
    "asset": "AC-ASSET-2026-00101",
    "asset_lifecycle_status": "Active",
    "capa_created": null,
    "lifecycle_event": "ALE-2026-00088",
    "measurements_summary": {"total": 1, "passed": 1, "failed": 0}
  }
}
```

> ⚠️ **Phân biệt 2 `next_calibration_date` (BR-11-13):** field `next_calibration_date` trong response NÀY = hạn của **chính phiếu/lịch vừa Pass** (`basis + interval`) — giữ nguyên cho backward-compat. KHÁC với `AC Asset.next_calibration_date` (CACHE thiết bị) mà `handle_calibration_pass` ghi = **`MIN(next_due_date)` trên MỌI active schedule** (rollup đa-lịch). Với asset multi-schedule, 2 giá trị này có thể KHÁC nhau (response = lịch vừa Pass; asset-cache = lịch sớm nhất). `get_due_calibrations` (endpoint 18) filter theo asset-cache → asset multi-schedule còn lịch sớm hơn KHÔNG bị rớt khỏi list.

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
- **Schedule due-now (BR-11-08b):** hạ `next_due_date = basis` (`certificate_date \| actual_date \| nowdate()`) cho MỌI `IMM Calibration Schedule` `{asset, is_active=1}` → `next_due_date <= today` → asset xuất hiện trong overdue/due-soon SoT (`get_calibration_kpis`/dashboard hết mask ON_SCHEDULE). Null-safe: 0 active schedule → no-op. Không đổi field response (shape bất biến — schedule là side-effect DB, không trả trong envelope submit).
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

## 6.1 Canonical-value rule — KPI calibration due/overdue == drill (BR-11-08/09)

Số trên KPI card PHẢI bằng số dòng khi click drill (cùng SoT, không lệch). 1 nguồn predicate (`services/imm11.py §4.1`), dùng chung dashboard + module.

| KPI / field | Predicate (SoT) | Drill route + query | Quan hệ |
|---|---|---|---|
| `get_calibration_kpis().overdue_assets` | `len(_overdue_asset_ids())` — DISTINCT asset, active schedule, `next_due < today`, không decommissioned | `/calibration/schedules?overdue=1` | card == `len(drill)` (de-dup theo asset) |
| `get_calibration_kpis().due_soon_assets` | `len(_due_soon_asset_ids())` — DISTINCT asset, `today <= next_due <= today+30`, loại overdue, không decommissioned | `/calibration/schedules?due_soon=1` (cửa-sổ-2-biên `next_due BETWEEN [today, today+30]` + `asset IN _due_soon_asset_ids()`) | card == `len(drill)` (de-dup theo asset, KHÔNG cần post-filter `next_due >= today`) |
| Dashboard `calibration.overdue` (`api/dashboard.py`) | `len(_overdue_asset_ids())` (import từ `services.imm11`) | giống trên | == module `overdue_assets` (CÙNG SoT) |
| Dashboard `calibration.due_30d` | `len(_due_soon_asset_ids())` | giống trên | == module `due_soon_assets` |

**Boundary (chốt):** OVERDUE ⟺ `next_due < today` (strict `<`); DUE_SOON ⟺ `today <= next_due <= today+30` (2 biên inclusive); `next_due == today` → DUE_SOON; `next_due == today+30` → DUE_SOON; `next_due == today+31` → ON_SCHEDULE.

**FAIL → due-now nằm trong tập (BR-11-08b):** asset vừa `overall_result=Fail` được `handle_calibration_fail` hạ `next_due = basis` (`<= today`). `basis < today` (cert/actual quá khứ) → asset vào `overdue_assets`; `basis == today` (nowdate) → vào `due_soon_assets` (due-now). Hai trường hợp đều khiến card overdue-or-due TĂNG +1 asset và drill `?overdue=1` HOẶC `?due_soon=1` chứa asset đó → count == drill bất biến, KHÔNG undercount asset FAIL. Asset FAIL KHÔNG còn ON_SCHEDULE.

**Phân biệt drill param (`_normalize_schedule_filters`, 3 nhánh — ưu tiên `overdue` > `due_soon` > `due_before`):**

- `?overdue=1` — card `calib_overdue`: `next_due < today` + `is_active=1` + `asset IN _overdue_asset_ids()`.
- `?due_soon=1` — card `calib_due` "Hiệu chuẩn đến hạn": **cửa-sổ-2-biên** `next_due BETWEEN [today, today+30]` + `is_active=1` + `asset IN _due_soon_asset_ids()` (đã LOẠI overdue). Drill tái lập CHÍNH XÁC tập KPI — số asset distinct == `calib_due`. Overdue rows KHÔNG lẫn (thuộc `?overdue=1`).
- `?due_before=<X>` — **cutoff-tùy-ý LEGACY (tập-BAO)**: `next_due <= X` + `is_active=1`, chỉ loại asset thanh lý. GỒM cả overdue (`<= X`). KHÔNG dùng cho card due-soon (sẽ lệch count). Giữ riêng cho caller cũ cần cutoff bất kỳ.

**Vendor-scope an toàn:** khi `apply_vendor_scope` đã inject `asset IN [allowed]`, cả 3 nhánh GIAO (intersect) caller-scope với tập SoT/decom — KHÔNG clobber → vendor KHÔNG thấy asset ngoài phạm vi khi drill.

**Drill `overdue=1` vs `due_before`:** `_normalize_schedule_filters` đã dịch `overdue=1` → `next_due_date < today` và `due_before=X` → `next_due_date <= X` trên `IMM Calibration Schedule` (is_active=1). Drill list trả theo SCHEDULE ROW; KPI card đếm theo ASSET (de-dup) → khi 1 asset có >1 schedule overdue, FE hiển thị nhiều row drill nhưng KPI đếm 1; doc-of-record: **KPI = #asset, drill list có thể >#asset nhưng tập asset của drill == tập KPI**. FE render BE count/list verbatim (KHÔNG inline compute).

**Mint-gap:** asset tạo trực tiếp với `is_calibration_required` (`create_calibration_schedule_from_asset`) set `Schedule.next_due_date` → xuất hiện đồng nhất ở CẢ dashboard VÀ module (trước fix: chỉ dashboard thấy).

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

## 11. Notification Contract (Sprint Notification 2026-05-29 vòng 4) — SINGLE SOURCE OF TRUTH

Mọi tương tác IMM-11 trả về **envelope chuẩn** đã chuẩn hoá BE → FE. FE KHÔNG
hardcode câu chữ — chỉ đọc `message_code` rồi render qua `useNotify`. Contract đã
chốt vòng 1 (IMM-09), vòng 2 (IMM-12), vòng 3 (IMM-08) — vòng 4 áp dụng cho IMM-11.

### 11.1 Envelope shape

Success (`_ok`):
```json
{ "success": true, "data": { ... } }
```
Lỗi (`_err`, hydrate từ registry qua `api_handler.handle()`):
```json
{
  "success": false,
  "error": "Phiếu hiệu chuẩn này đã được chốt — không thể thao tác lại.",
  "code": "CONFLICT",
  "message_code": "IMM11-ALREADY-SUBMITTED",
  "severity": "warning",
  "title": "Phiếu hiệu chuẩn đã chốt",
  "action_hint": "Không cần thao tác lại — dùng Amend nếu cần điều chỉnh.",
  "context": {},
  "http_status": 409
}
```

**Bất biến (contract):** mọi error envelope nghiệp vụ IMM-11 PHẢI có `message_code`,
`severity`, `title`. Không còn `frappe.throw(_("..."))` leak message Frappe ra FE, và
không còn `ServiceError(ErrorCode.*, "...")` thô (rớt message_code/severity). Service
raise qua `nthrow(MSG.IMM11_*)`; DocType `validate`/`before_submit`/`on_cancel`/`on_trash`
hook (BR-11-*/VR-11-*/CAL-*) raise qua `nthrow_in_hook(MSG.IMM11_*)`.

### 11.2 Danh mục MSG cần bổ sung vào `utils/messages.py`

Severity tuân quy tắc §11.5. Tái dùng mã hệ thống (`AUTH_FORBIDDEN`,
`VAL_INVALID_PARAMS`, `SYS_500`) khi phù hợp.

| MSG.* | code (kebab) | severity | http | title | template (VI) | action_hint |
|---|---|---|---|---|---|---|
| `IMM11_CAL_NOT_FOUND` | `IMM11-CAL-NOT-FOUND` | warning | 404 | Không tìm thấy phiếu hiệu chuẩn | Không tìm thấy phiếu hiệu chuẩn: {name}. | Kiểm tra lại mã phiếu trong danh sách hiệu chuẩn. |
| `IMM11_SCHEDULE_NOT_FOUND` | `IMM11-SCHEDULE-NOT-FOUND` | warning | 404 | Không tìm thấy lịch hiệu chuẩn | Không tìm thấy lịch hiệu chuẩn: {name}. | Kiểm tra lại mã lịch trong danh sách. |
| `IMM11_ASSET_NOT_FOUND` | `IMM11-ASSET-NOT-FOUND` | warning | 404 | Không tìm thấy thiết bị | Thiết bị không tồn tại trong danh mục tài sản. | Kiểm tra lại mã thiết bị. |
| `IMM11_ASSET_BLOCKED` | `IMM11-ASSET-BLOCKED` | warning | 409 | Thiết bị không thể hiệu chuẩn | Thiết bị đang ở trạng thái không cho phép tạo phiếu hiệu chuẩn (CAL-008). | Chuyển thiết bị về trạng thái hoạt động hoặc dùng tái hiệu chuẩn. |
| `IMM11_NO_FIELDS` | `IMM11-NO-FIELDS` | warning | 400 | Không có thay đổi | Không có trường hợp lệ nào để cập nhật. | Chọn ít nhất một trường để cập nhật rồi thử lại. |
| `IMM11_ALREADY_SUBMITTED` | `IMM11-ALREADY-SUBMITTED` | warning | 409 | Phiếu hiệu chuẩn đã chốt | Phiếu hiệu chuẩn này đã được chốt — không thể thao tác lại. | Không cần thao tác lại — dùng Amend nếu cần điều chỉnh. |
| `IMM11_SCHEDULE_HAS_SUBMITTED` | `IMM11-SCHEDULE-HAS-SUBMITTED` | warning | 409 | Lịch còn phiếu đã chốt | Không thể xoá lịch hiệu chuẩn đang có phiếu đã chốt. | Huỷ hoặc lưu trữ các phiếu liên quan trước khi xoá lịch. |
| `IMM11_NOT_EXTERNAL` | `IMM11-NOT-EXTERNAL` | warning | 422 | Chỉ áp dụng cho hiệu chuẩn ngoài | Thao tác này chỉ áp dụng cho phiếu hiệu chuẩn External (gửi lab). | Chọn phiếu có loại hiệu chuẩn External rồi thử lại. |
| `IMM11_SEND_LAB_BAD_STATE` | `IMM11-SEND-LAB-BAD-STATE` | warning | 409 | Không thể gửi lab | Không thể gửi lab khi phiếu đang ở trạng thái '{state}'. | Chỉ gửi lab khi phiếu ở trạng thái Đã lên lịch hoặc Đang xử lý. |
| `IMM11_RECEIVE_CERT_BAD_STATE` | `IMM11-RECEIVE-CERT-BAD-STATE` | warning | 409 | Không thể nhận chứng chỉ | Chỉ nhận chứng chỉ khi phiếu ở trạng thái Đã gửi lab. | Gửi phiếu cho lab trước khi nhận chứng chỉ. |
| `IMM11_CERT_FIELDS_REQUIRED` | `IMM11-CERT-FIELDS-REQUIRED` | warning | 422 | Thiếu thông tin chứng chỉ | Cần đủ tệp chứng chỉ, số chứng chỉ và ngày cấp. | Điền đủ ba thông tin chứng chỉ rồi thử lại. |
| `IMM11_CANCEL_REASON_REQUIRED` | `IMM11-CANCEL-REASON-REQUIRED` | warning | 422 | Thiếu lý do huỷ | Bắt buộc nhập lý do khi huỷ phiếu hiệu chuẩn. | Nhập lý do huỷ rồi thử lại. |
| `IMM11_CANCEL_SUBMITTED` | `IMM11-CANCEL-SUBMITTED` | warning | 409 | Không thể huỷ phiếu đã chốt | Phiếu hiệu chuẩn đã chốt — không thể huỷ (BR-11-05). | Dùng chức năng Amend để điều chỉnh phiếu đã chốt. |
| `IMM11_ALREADY_CANCELLED` | `IMM11-ALREADY-CANCELLED` | warning | 409 | Phiếu đã huỷ | Phiếu hiệu chuẩn này đã được huỷ trước đó. | Không cần thao tác lại. |
| `IMM11_NO_MEASUREMENTS` | `IMM11-NO-MEASUREMENTS` | warning | 422 | Thiếu tham số đo | Phải nhập ít nhất một tham số đo trước khi gửi duyệt (CAL-005). | Thêm tham số đo rồi gửi duyệt lại. |
| `IMM11_MEASUREMENT_VALUE_REQUIRED` | `IMM11-MEASUREMENT-VALUE-REQUIRED` | warning | 422 | Thiếu giá trị đo | Tham số '{parameter}' chưa có giá trị đo (CAL-004). | Nhập giá trị đo cho mọi tham số rồi thử lại. |
| `IMM11_RESULT_REQUIRED` | `IMM11-RESULT-REQUIRED` | warning | 422 | Thiếu kết quả tổng | Phiếu hiệu chuẩn phải có kết quả tổng trước khi gửi duyệt (CAL-006). | Hoàn tất nhập đo để hệ thống tính kết quả rồi thử lại. |
| `IMM11_LAB_REQUIRED` | `IMM11-LAB-REQUIRED` | warning | 422 | Chưa chọn lab hiệu chuẩn | Hiệu chuẩn ngoài bắt buộc chọn lab hiệu chuẩn (VR-11-01). | Chọn lab hiệu chuẩn rồi thử lại. |
| `IMM11_LAB_NOT_ACCREDITED` | `IMM11-LAB-NOT-ACCREDITED` | warning | 422 | Lab chưa đủ điều kiện | Lab phải có loại 'Calibration Lab' và chứng chỉ ISO/IEC 17025 còn hạn (VR-11-02). | Chọn lab khác hoặc cập nhật chứng chỉ ISO/IEC 17025. |
| `IMM11_CERT_FILE_REQUIRED` | `IMM11-CERT-FILE-REQUIRED` | warning | 422 | Thiếu tệp chứng chỉ | Vui lòng tải lên chứng chỉ hiệu chuẩn (VR-11-03). | Đính kèm tệp chứng chỉ rồi thử lại. |
| `IMM11_LAB_ACCRED_NUMBER_REQUIRED` | `IMM11-LAB-ACCRED-NUMBER-REQUIRED` | warning | 422 | Thiếu số công nhận | Vui lòng nhập số công nhận ISO/IEC 17025 (VR-11-04). | Nhập số công nhận của lab rồi thử lại. |
| `IMM11_REF_STANDARD_REQUIRED` | `IMM11-REF-STANDARD-REQUIRED` | warning | 422 | Thiếu thiết bị chuẩn | Hiệu chuẩn nội bộ bắt buộc nhập serial thiết bị chuẩn (VR-11-06). | Nhập serial thiết bị chuẩn rồi thử lại. |
| `IMM11_CERT_DATE_FUTURE` | `IMM11-CERT-DATE-FUTURE` | warning | 422 | Ngày chứng chỉ không hợp lệ | Ngày cấp chứng chỉ không thể nằm trong tương lai (VR-11-07). | Chọn lại ngày cấp chứng chỉ. |
| _(success)_ `IMM11_CREATE_SUCCESS` | `IMM11-CREATE-SUCCESS` | success | 200 | Đã tạo phiếu hiệu chuẩn | Đã tạo phiếu hiệu chuẩn {name} cho thiết bị {asset}. | — |
| _(success)_ `IMM11_SUBMIT_SUCCESS` | `IMM11-SUBMIT-SUCCESS` | success | 200 | Đã chốt phiếu hiệu chuẩn | Đã ghi nhận kết quả hiệu chuẩn {name}. | — |
| _(success)_ `IMM11_SCHEDULE_CREATE_SUCCESS` | `IMM11-SCHEDULE-CREATE-SUCCESS` | success | 200 | Đã tạo lịch hiệu chuẩn | Đã tạo lịch hiệu chuẩn cho thiết bị, đến hạn {next_due_date}. | — |
| _(success)_ `IMM11_SEND_LAB_SUCCESS` | `IMM11-SEND-LAB-SUCCESS` | success | 200 | Đã gửi lab | Đã gửi phiếu {name} tới lab hiệu chuẩn. | — |
| _(success)_ `IMM11_CERT_RECEIVED_SUCCESS` | `IMM11-CERT-RECEIVED-SUCCESS` | success | 200 | Đã nhận chứng chỉ | Đã nhận chứng chỉ #{certificate_number} cho phiếu {name}. | — |
| _(success)_ `IMM11_CANCEL_SUCCESS` | `IMM11-CANCEL-SUCCESS` | success | 200 | Đã huỷ phiếu | Đã huỷ phiếu hiệu chuẩn {name}. | — |

> Content tuân `messages.py` §quy chuẩn — Chủ thể + Hậu quả + Hành động, không từ
> kỹ thuật, không đổ lỗi user. Sau khi thêm vào `messages.py`, chạy
> `python scripts/gen_fe_messages.py` để regen `frontend/src/i18n/messages.ts`.

### 11.3 BE migration checklist (cho assetcore-be)

- `services/imm11.py` service layer: thay TẤT CẢ `raise ServiceError(ErrorCode.*, "...")`
  thô bằng `nthrow(MSG.IMM11_*)` tương ứng (xem bảng §11.2). `ServiceError` thô làm rớt
  `message_code`/`severity` → envelope không hydrate được. Đây chính là backlog vòng 3.
- `assetcore/doctype/imm_asset_calibration/imm_asset_calibration.py` hook
  `validate`/`before_submit`/`on_cancel`/`on_trash`: 11 `frappe.throw(_(...))` (CAL-004/005/006,
  VR-11-01/02/03/04/06/07, BR-11-05) → `nthrow_in_hook(MSG.IMM11_*)`. DocType hook BẮT BUỘC
  dùng `nthrow_in_hook` (không phải `nthrow`).
- `api/imm11.py`: bỏ `_parse_filters`/`_handle` cục bộ + `from utils.helpers import _err,_ok`
  → dùng `from assetcore.utils.api_handler import handle, parse_json` +
  `from assetcore.utils.response import _ok, _err`. Giữ guard rbac/vendor-scope trước `handle`.
- Audit trail (`log_audit_event`, `create_lifecycle_event`), CAPA/lookback side-effect
  (`handle_calibration_fail`), cross-module IMM-12 incident KHÔNG đổi — framework chỉ
  chuẩn hoá phản hồi user.
- KHÔNG chạm Wave N1 treo: `services/notifications.py`, `notify_calibration_due` call site
  (chỉ giữ nguyên).

### 11.4 FE migration checklist (cho assetcore-fe)

- Store `stores/imm11.ts`: expose `lastApiError` (`ApiError | null`) + helper `_captureError`;
  mọi action catch → `_captureError(e)` (giống `stores/imm08.ts`).
- Views `calibration/*` (CalibrationDetailView, CalibrationCreateView, CalibrationListView,
  CalibrationScheduleListView, CalibrationDashboard): success → `notify.show(MSG.IMM11_*)`;
  fail → `notify.fromError(store.lastApiError)`. Bỏ try/catch tự build string từ `e.message` BE.
- Thêm test store `stores/imm11.test.ts` nếu store có action mutate (capture error path).

### 11.5 Quy tắc severity (chốt cho IMM-11)

- `warning` = lỗi nghiệp vụ user tự sửa được (validation CAL-*/VR-11-*, bad-state, not-found,
  conflict) → toast vàng, GIỮ form, không reload.
- `error` = lỗi hệ thống (`SYS-*`) → toast đỏ.
- `success` = thao tác thành công → toast xanh.

> Lưu ý: VR-11-02 (lab ISO/IEC 17025) là validation nghiệp vụ user sửa được (chọn lab khác),
> KHÔNG phải compliance-blocking như BR-12 clinical impact. Do đó severity = `warning`,
> không `critical`. Calibration Fail → CAPA/lookback là side-effect tự động của `on_submit`
> (submit vẫn THÀNH CÔNG, severity success), không phải lỗi chặn user.

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
