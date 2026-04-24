# IMM-07 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-07 — Vận hành hàng ngày |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Trạng thái | DESIGN — Wave 2 |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | WHO HTM 2025, ISO 13485:2016 §8.3, NĐ 98/2021 |

---

## 1. Scope

### 1.1 In Scope

| # | Hạng mục | Ghi chú |
|---|---|---|
| 1 | DocType `Daily Operation Log` | Schema theo `daily_operation_log.json` |
| 2 | Workflow 3 states + 4 transitions | `IMM-07 Workflow` |
| 3 | 3 Validation Rules + 2 Gates | Backend enforce |
| 4 | 8 REST endpoint | `assetcore/api/imm07.py` |
| 5 | Auto-create Incident Report khi anomaly Critical/Major | `on_submit` |
| 6 | Operation summary per asset | `get_asset_operation_summary()` |
| 7 | Dashboard KPIs today | `get_dashboard_stats()` |

### 1.2 Out of Scope

| # | Hạng mục | Lý do defer |
|---|---|---|
| 1 | Barcode scan để điền asset tự động | Wave 3 mobile |
| 2 | IoT integration tự động ghi meter hours | Phase 2 IoT |
| 3 | Predictive analytics từ runtime data | Wave 4 analytics |
| 4 | SMS alert khi Fault | Wave 3 notification |

---

## 2. Actors

| Actor | Role hệ thống | Trách nhiệm chính |
|---|---|---|
| Clinical Operator | `Clinical Operator` | Tạo log ca, ghi trạng thái, báo bất thường |
| Nurse | `Nurse` | Ghi log ca, xác nhận trạng thái |
| Department Head | `Department Head` | Review và phê duyệt log ca trực |
| HTM Technician | `HTM Technician` | Đọc log để lên lịch bảo trì, xử lý fault |

---

## 3. User Stories (Gherkin)

### 3.1 Tạo nhật ký ca trực

```gherkin
Scenario: US-07-01 — Tạo Daily Operation Log thành công
  Given tôi có role "Clinical Operator" hoặc "Nurse"
    And asset "ACC-26-04-00001" tồn tại và đã Handed Over (IMM-06)
    And chưa có log nào cho asset này trong ca "Morning" ngày "2026-04-21"
  When tôi POST /api/method/assetcore.api.imm07.create_daily_log
    với {asset, log_date="2026-04-21", shift="Morning 06-14",
         operated_by, operational_status="Running",
         start_meter_hours=1500, end_meter_hours=1508}
  Then response.success = true
    And data.name khớp regex "^DOL-\d{2}-\d{2}-\d{2}-\d{5}$"
    And data.runtime_hours = 8.0
    And workflow_state = "Open"
```

### 3.2 VR-01 — Block log trùng ca

```gherkin
Scenario: US-07-02 — Block tạo log trùng ca
  Given đã có log "DOL-26-04-21-00001" cho asset "ACC-26-04-00001"
    ca "Morning 06-14" ngày "2026-04-21"
  When tôi tạo thêm log cho cùng asset/ca/ngày
  Then response.success = false
    And error.code = "VALIDATION_ERROR"
    And message chứa "VR-01: Đã tồn tại nhật ký ca Morning cho thiết bị này ngày 2026-04-21"
```

### 3.3 VR-02 — Kiểm tra meter hours

```gherkin
Scenario: US-07-03 — Block end_meter < start_meter
  Given tôi tạo log với start_meter_hours=1508, end_meter_hours=1500
  When validate chạy
  Then frappe.throw với message "VR-02: Giờ kết thúc (1500) không thể nhỏ hơn giờ bắt đầu (1508)"
```

### 3.4 Báo bất thường kèm mô tả

```gherkin
Scenario: US-07-04 — Bắt buộc mô tả khi anomaly_detected=1
  Given tôi tạo log với anomaly_detected=1, anomaly_description=""
  When validate chạy
  Then frappe.throw với message "VR-03: Vui lòng mô tả chi tiết bất thường phát hiện"
```

### 3.5 Submit log và auto-create Incident

```gherkin
Scenario: US-07-05 — Submit log với anomaly Critical tạo Incident Report
  Given log "DOL-26-04-21-00001" có anomaly_type="Critical"
    And anomaly_description="Màn hình tắt đột ngột"
  When submit_log(name)
  Then docstatus = 1
    And Incident Report mới được tạo với severity="Critical"
    And linked_incident = new_incident.name
    And Asset Lifecycle Event "operation_logged" được ghi
```

### 3.6 Review log

```gherkin
Scenario: US-07-06 — Department Head review log
  Given log "DOL-26-04-21-00001" ở trạng thái "Logged"
    And tôi có role "Department Head"
  When gọi review_log(name, reviewer_notes="Đã xem xét, không có vấn đề")
  Then workflow_state = "Reviewed"
    And reviewed_by = session_user
    And review_date = today
```

### 3.7 Tổng hợp vận hành theo thiết bị

```gherkin
Scenario: US-07-07 — Xem tổng hợp 30 ngày qua
  Given asset "ACC-26-04-00001" có 45 logs trong 30 ngày
  When gọi get_asset_operation_summary(asset_name, days=30)
  Then response.data.total_runtime_hours = tổng runtime_hours
    And response.data.uptime_pct = (ngày Running / 30) * 100
    And response.data.anomaly_count = số log có anomaly_detected=1
    And response.data.fault_days = số ngày operational_status="Fault"
```

### 3.8 Dashboard hôm nay

```gherkin
Scenario: US-07-08 — Xem dashboard trạng thái thiết bị hôm nay
  Given hôm nay có 12 thiết bị trong khoa "ICU"
    And 10 Running, 1 Standby, 1 Fault
  When gọi get_dashboard_stats(dept="ICU")
  Then response.data.running = 10
    And response.data.standby = 1
    And response.data.fault = 1
    And response.data.total_runtime_hours > 0
```

---

## 4. Business Rules

| BR ID | Rule | Enforce | Test ref |
|---|---|---|---|
| BR-07-01 | 1 log/ca/asset/ngày | `validate_single_log_per_shift()` | TC-07-02 |
| BR-07-02 | end_meter ≥ start_meter | `validate_meter_hours()` | TC-07-03 |
| BR-07-03 | anomaly_detected=1 → anomaly_description bắt buộc | `validate()` | TC-07-04 |
| BR-07-04 | anomaly Major/Critical → tự động tạo Incident Report khi Submit | `on_submit` | TC-07-05 |

---

## 5. Permission Matrix

| Endpoint / Action | Clinical Op | Nurse | Dept Head | HTM Tech |
|---|---|---|---|---|
| `create_daily_log` | W | W | — | — |
| `get_daily_log` | R | R | R | R |
| `list_daily_logs` | R (own dept) | R (own dept) | R | R |
| `submit_log` | W | W | — | — |
| `review_log` | — | — | W | W |
| `get_asset_operation_summary` | R | — | R | R |
| `get_dashboard_stats` | R | R | R | R |
| `report_anomaly_from_log` | W | W | — | W |

---

## 6. Validation Rules

| VR ID | Field / Scope | Rule | Error Message (vi) | Enforce |
|---|---|---|---|---|
| VR-01 | `asset + log_date + shift` | Duy nhất: 1 log/ca/asset/ngày | "VR-01: Đã tồn tại nhật ký ca '{shift}' cho thiết bị '{asset}' ngày '{date}'." | `validate_single_log_per_shift()` |
| VR-02 | `end_meter_hours >= start_meter_hours` | Không được âm runtime | "VR-02: Giờ kết thúc ({end}) không thể nhỏ hơn giờ bắt đầu ({start})." | `validate_meter_hours()` |
| VR-03 | `anomaly_description` | Bắt buộc nếu anomaly_detected=1 | "VR-03: Vui lòng mô tả chi tiết bất thường đã phát hiện trong ca." | controller `validate()` |

---

## 7. Non-Functional Requirements

| NFR ID | Loại | Yêu cầu | Target |
|---|---|---|---|
| NFR-07-01 | Performance | Tải dashboard hôm nay | P95 < 1.5s |
| NFR-07-02 | Performance | Tạo log | < 500ms |
| NFR-07-03 | Audit | Submit tạo Lifecycle Event | 100% coverage |
| NFR-07-04 | Reliability | Scheduler tổng hợp runtime daily | Độ trễ < 5 phút |
| NFR-07-05 | Localization | Mọi message tiếng Việt | `frappe._()` wrap |

---

## 8. Acceptance Criteria

| Mã | Acceptance Criteria |
|---|---|
| AC-07-01 | VR-01 block log trùng ca/asset/ngày |
| AC-07-02 | runtime_hours được tính tự động |
| AC-07-03 | Anomaly Critical/Major → Incident Report auto-created khi Submit |
| AC-07-04 | review_log cập nhật reviewed_by và review_date |
| AC-07-05 | get_dashboard_stats trả về đúng groupby operational_status |
| AC-07-06 | get_asset_operation_summary trả về uptime_pct, anomaly_count chính xác |

*End of Functional Specs v1.0.0 — IMM-07*
