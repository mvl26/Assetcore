# IMM-07 — UAT Script

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-07 — Vận hành hàng ngày |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Tester | HTM Technician |

---

## Pre-conditions

- Asset `ACC-TEST-00001` tồn tại và có Handover Record "Handed Over"
- User `operator@test.vn` có role `Clinical Operator`
- User `depthead@test.vn` có role `Department Head`
- Ngày test: `2026-04-21`

---

## TC-07-01 — Tạo Daily Operation Log thành công

| | |
|---|---|
| **ID** | TC-07-01 |
| **Mục tiêu** | Tạo log ca trực thành công với runtime tự động tính |

**Steps:**
1. POST `create_daily_log` với: `asset="ACC-TEST-00001"`, `log_date="2026-04-21"`, `shift="Morning 06-14"`, `operated_by="operator@test.vn"`, `operational_status="Running"`, `start_meter_hours=1500`, `end_meter_hours=1508`

**Expected:**
- `success = true`
- `data.name` khớp `^DOL-\d{2}-\d{2}-\d{2}-\d{5}$`
- `data.runtime_hours = 8.0`
- `data.workflow_state = "Open"`

---

## TC-07-02 — VR-01: Block log trùng ca

| | |
|---|---|
| **ID** | TC-07-02 |
| **Mục tiêu** | Không cho phép tạo log trùng ca/asset/ngày |

**Steps:**
1. Tạo log từ TC-07-01 thành công
2. POST `create_daily_log` với cùng `asset`, `log_date`, `shift`

**Expected:**
- `success = false`
- `code = "VALIDATION_ERROR"`
- `error` chứa "VR-01: Đã tồn tại nhật ký ca Morning"

---

## TC-07-03 — VR-02: Block end_meter < start_meter

| | |
|---|---|
| **ID** | TC-07-03 |
| **Mục tiêu** | Không cho phép nhập giờ cuối < giờ đầu |

**Steps:**
1. POST `create_daily_log` với `start_meter_hours=1508`, `end_meter_hours=1500`

**Expected:**
- `success = false`
- `error` chứa "VR-02: Giờ kết thúc (1500) không thể nhỏ hơn giờ bắt đầu (1508)"

---

## TC-07-04 — VR-03: Bắt buộc mô tả anomaly

| | |
|---|---|
| **ID** | TC-07-04 |
| **Mục tiêu** | Block khi anomaly_detected=1 mà không có mô tả |

**Steps:**
1. POST `create_daily_log` với `anomaly_detected=1`, `anomaly_description=""`

**Expected:**
- `success = false`
- `error` chứa "VR-03: Vui lòng mô tả chi tiết bất thường"

---

## TC-07-05 — Submit log thành công

| | |
|---|---|
| **ID** | TC-07-05 |
| **Mục tiêu** | Nộp log, chuyển Open → Logged |

**Steps:**
1. Lấy log name từ TC-07-01
2. POST `submit_log` với `name`

**Expected:**
- `success = true`
- `data.workflow_state = "Logged"`
- `data.linked_incident = null` (vì không có anomaly)

---

## TC-07-06 — Submit log với anomaly Critical tạo Incident

| | |
|---|---|
| **ID** | TC-07-06 |
| **Mục tiêu** | Submit tạo Incident Report tự động khi anomaly Critical |

**Steps:**
1. POST `create_daily_log` với `shift="Afternoon 14-22"`, `anomaly_detected=1`, `anomaly_type="Critical"`, `anomaly_description="Màn hình tắt đột ngột khi đang thở máy"`, `operational_status="Fault"`
2. POST `submit_log`

**Expected:**
- `success = true`
- `data.linked_incident` khác null
- Incident Report được tạo với `severity="Critical"`
- Asset Lifecycle Event "operation_logged" được ghi

---

## TC-07-07 — Review log bởi Dept Head

| | |
|---|---|
| **ID** | TC-07-07 |
| **Mục tiêu** | Dept Head review log, chuyển Logged → Reviewed |

**Pre:** Log ở trạng thái "Logged"

**Steps:**
1. POST `review_log` với `name`, `reviewer_notes="Đã xem xét OK"`

**Expected:**
- `success = true`
- `data.workflow_state = "Reviewed"`
- `data.reviewed_by = "depthead@test.vn"`
- `data.review_date = "2026-04-21"`

---

## TC-07-08 — Tổng hợp vận hành 30 ngày

| | |
|---|---|
| **ID** | TC-07-08 |
| **Mục tiêu** | API trả về tổng hợp đúng |

**Steps:**
1. Tạo 10+ logs trong 30 ngày qua
2. GET `get_asset_operation_summary?asset_name=ACC-TEST-00001&days=30`

**Expected:**
- `success = true`
- `data.total_runtime_hours >= 0`
- `data.uptime_pct` là số 0-100
- `data.anomaly_count >= 0`
- `data.status_breakdown` là dict

---

## TC-07-09 — Dashboard hôm nay

| | |
|---|---|
| **ID** | TC-07-09 |
| **Mục tiêu** | Dashboard trả về trạng thái thiết bị hôm nay |

**Steps:**
1. Tạo log cho nhiều thiết bị hôm nay với các operational_status khác nhau
2. GET `get_dashboard_stats`

**Expected:**
- `success = true`
- `data.running + data.standby + data.fault + data.under_maintenance + data.not_used = total logs hôm nay`
- `data.assets_by_status` là array

---

## TC-07-10 — Báo bất thường từ log

| | |
|---|---|
| **ID** | TC-07-10 |
| **Mục tiêu** | report_anomaly_from_log tạo Incident Report |

**Steps:**
1. POST `report_anomaly_from_log` với `log_name`, `severity="Major"`, `description="Rò điện vỏ máy"`

**Expected:**
- `success = true`
- `data.incident` khác null
- Incident Report có `severity="Major"`

---

## TC-07-11 — Danh sách log với filter

| | |
|---|---|
| **ID** | TC-07-11 |
| **Mục tiêu** | Filter list theo asset và date range |

**Steps:**
1. GET `list_daily_logs?asset=ACC-TEST-00001&date_from=2026-04-01&date_to=2026-04-21`

**Expected:**
- `success = true`
- Tất cả items có `asset = "ACC-TEST-00001"`
- Tất cả items có `log_date` trong range

---

## Test Summary

| TC ID | Tên | Priority | Expected |
|---|---|---|---|
| TC-07-01 | Tạo log thành công | P0 | PASS |
| TC-07-02 | VR-01 block trùng ca | P0 | PASS |
| TC-07-03 | VR-02 end < start | P0 | PASS |
| TC-07-04 | VR-03 anomaly mô tả | P0 | PASS |
| TC-07-05 | Submit log | P0 | PASS |
| TC-07-06 | Incident auto-create | P0 | PASS |
| TC-07-07 | Review log | P1 | PASS |
| TC-07-08 | Tổng hợp 30 ngày | P1 | PASS |
| TC-07-09 | Dashboard hôm nay | P1 | PASS |
| TC-07-10 | Report anomaly | P1 | PASS |
| TC-07-11 | Filter list | P2 | PASS |

*End of UAT Script v1.0.0 — IMM-07*
