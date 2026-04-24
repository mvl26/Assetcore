# IMM-06 — UAT Script

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — Bàn giao & Đào tạo |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Tester | QA Officer |

---

## Pre-conditions

- IMM-04 có phiếu `IMM04-TEST-00001` ở trạng thái `Clinical Release` (docstatus=1)
- Asset `ACC-TEST-00001` tồn tại (được tạo bởi IMM-04)
- User `biomed@test.vn` có role `Biomed Engineer`
- User `depthead@test.vn` có role `Department Head`
- User `trainee1@test.vn`, `trainee2@test.vn` tồn tại

---

## TC-06-01 — Tạo Handover Record thành công

| | |
|---|---|
| **ID** | TC-06-01 |
| **Mục tiêu** | Tạo phiếu bàn giao từ commissioning hợp lệ |
| **Actor** | HTM Technician |

**Steps:**
1. POST `create_handover_record` với `commissioning_ref="IMM04-TEST-00001"`, `clinical_dept="ICU"`, `handover_date="2026-04-21"`, `received_by="depthead@test.vn"`, `handover_type="Full"`
2. Kiểm tra response

**Expected:**
- `success = true`
- `data.name` khớp regex `^HR-\d{2}-\d{2}-\d{5}$`
- `data.workflow_state = "Draft"`
- `data.asset = "ACC-TEST-00001"` (fetched from commissioning)

---

## TC-06-02 — VR-01: Block commissioning chưa Clinical Release

| | |
|---|---|
| **ID** | TC-06-02 |
| **Mục tiêu** | Block tạo Handover khi commissioning chưa released |

**Steps:**
1. Tạo commissioning `IMM04-TEST-00002` ở trạng thái `Initial Inspection`
2. POST `create_handover_record` với `commissioning_ref="IMM04-TEST-00002"`

**Expected:**
- `success = false`
- `code = "VALIDATION_ERROR"`
- `error` chứa "VR-01: Commissioning chưa đạt Clinical Release"

---

## TC-06-03 — Lên lịch Training Session

| | |
|---|---|
| **ID** | TC-06-03 |
| **Mục tiêu** | Tạo buổi đào tạo cho phiếu bàn giao |

**Steps:**
1. Lấy `handover_name` từ TC-06-01
2. POST `schedule_training` với `training_type="Operation"`, `trainer="biomed@test.vn"`, `training_date="2026-04-20"`, `duration_hours=2`

**Expected:**
- `success = true`
- `data.name` khớp `^TS-\d{2}-\d{2}-\d{5}$`
- Handover workflow_state = "Training Scheduled"

---

## TC-06-04 — Thêm trainee vào buổi đào tạo

| | |
|---|---|
| **ID** | TC-06-04 |
| **Mục tiêu** | Thêm học viên vào Training Session |

**Steps:**
1. POST `schedule_training` với `trainees=[{trainee_user: "trainee1@test.vn", role: "Nurse"}, {trainee_user: "trainee2@test.vn", role: "Nurse"}]`
2. GET `get_handover_record` kiểm tra

**Expected:**
- Training Session có 2 trainee rows
- `attendance = "Present"` mặc định

---

## TC-06-05 — Hoàn thành đào tạo với điểm

| | |
|---|---|
| **ID** | TC-06-05 |
| **Mục tiêu** | Ghi nhận kết quả đào tạo |

**Steps:**
1. POST `complete_training` với `scores=[{trainee_user: "trainee1@test.vn", score: 85, passed: true}, {trainee_user: "trainee2@test.vn", score: 45, passed: false}]`

**Expected:**
- `success = true`
- `competency_confirmed = false` (vì có 1 người fail)
- `passed_count = 1`, `total_trainees = 2`

---

## TC-06-06 — Gate G01: Block Handover Pending khi chưa đủ đào tạo

| | |
|---|---|
| **ID** | TC-06-06 |
| **Mục tiêu** | Block chuyển sang Handover Pending khi chưa complete training |

**Steps:**
1. Tạo Handover Record mới (chưa có training session)
2. Cố gắng transition sang "Handover Pending"

**Expected:**
- Throw ValidationError
- Message chứa "VR-03: Phải hoàn thành ít nhất 1 buổi đào tạo"

---

## TC-06-07 — VR-02: Block tạo Handover trùng

| | |
|---|---|
| **ID** | TC-06-07 |
| **Mục tiêu** | Không cho phép tạo 2 Handover Handed Over cho cùng asset |

**Steps:**
1. Submit TC-06-01 thành công (Handed Over)
2. Tạo Handover Record mới cho cùng `asset = "ACC-TEST-00001"`

**Expected:**
- `success = false`
- Message chứa "VR-02: Thiết bị này đã có phiếu bàn giao hoàn thành"

---

## TC-06-08 — Xác nhận bàn giao thành công

| | |
|---|---|
| **ID** | TC-06-08 |
| **Mục tiêu** | Submit Handover Record thành công |

**Pre:** Handover ở "Handover Pending", có ≥1 Training Completed, dept_head_signoff set

**Steps:**
1. POST `confirm_handover` với `name`, `dept_head_signoff="depthead@test.vn"`

**Expected:**
- `success = true`
- `data.docstatus = 1`
- `data.status = "Handed Over"`
- Asset Lifecycle Event "handover_completed" được tạo

---

## TC-06-09 — VR-04: Block bàn giao không có chữ ký Trưởng khoa

| | |
|---|---|
| **ID** | TC-06-09 |
| **Mục tiêu** | Block khi thiếu dept_head_signoff |

**Steps:**
1. POST `confirm_handover` với `dept_head_signoff=""`

**Expected:**
- `success = false`
- Message chứa "VR-04: Bắt buộc có chữ ký Trưởng khoa"

---

## TC-06-10 — Dashboard Stats

| | |
|---|---|
| **ID** | TC-06-10 |
| **Mục tiêu** | Dashboard trả về đúng số liệu |

**Steps:**
1. GET `get_dashboard_stats`

**Expected:**
- `success = true`
- `data.total_pending_handover` >= 0
- `data.completed_this_month` >= 0
- `data.training_pass_rate` là số 0-100

---

## TC-06-11 — Training History per Asset

| | |
|---|---|
| **ID** | TC-06-11 |
| **Mục tiêu** | Lịch sử đào tạo theo thiết bị |

**Steps:**
1. GET `get_asset_training_history?asset_name=ACC-TEST-00001`

**Expected:**
- `success = true`
- `data.sessions` là array
- Mỗi session có `training_type`, `training_date`, `status`

---

## Test Summary

| TC ID | Tên | Priority | Expected Result |
|---|---|---|---|
| TC-06-01 | Tạo Handover thành công | P0 | PASS |
| TC-06-02 | VR-01 block chưa Released | P0 | PASS |
| TC-06-03 | Lên lịch đào tạo | P0 | PASS |
| TC-06-04 | Thêm trainee | P1 | PASS |
| TC-06-05 | Ghi điểm đào tạo | P1 | PASS |
| TC-06-06 | Gate G01 block | P0 | PASS |
| TC-06-07 | VR-02 block trùng | P0 | PASS |
| TC-06-08 | Xác nhận bàn giao | P0 | PASS |
| TC-06-09 | VR-04 thiếu chữ ký | P0 | PASS |
| TC-06-10 | Dashboard stats | P1 | PASS |
| TC-06-11 | Training history | P2 | PASS |

*End of UAT Script v1.0.0 — IMM-06*
