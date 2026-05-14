# IMM-11 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-11 — Calibration / Hiệu chuẩn |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | DRAFT — chưa implement code |
| Chuẩn tham chiếu | WHO HTM 2025, NĐ 98/2021/NĐ-CP, ISO 13485:2016, ISO/IEC 17025 |
| Dependency | IMM-00 Foundation (services + DocTypes) |
| Tác giả | AssetCore Team |

---

## 1. Scope

### 1.1 In Scope

| # | Hạng mục | Ghi chú |
|---|---|---|
| 1 | Lập lịch hiệu chuẩn theo `Device Model.calibration_interval_days` | Auto từ IMM-04 commissioning |
| 2 | Track External (lab ISO/IEC 17025) — bàn giao, nhận chứng chỉ, nhập số liệu | BR-11-01 |
| 3 | Track In-House (KTV nội bộ + reference standard) | Không cần certificate file |
| 4 | Auto-tính Pass/Fail theo tolerance từng tham số | Computed in `before_submit` |
| 5 | Auto-CAPA + Asset Out of Service khi Fail | BR-11-02 (gọi `transition_asset_status` + `create_capa`) |
| 6 | Lookback assessment cùng `device_model` | BR-11-03 |
| 7 | Update `next_calibration_date` trên AC Asset | BR-11-04 |
| 8 | Immutable record + Amend với lý do | BR-11-05 |
| 9 | Scheduler: tạo WO 30 ngày trước due_date; alert overdue | Daily |
| 10 | Compliance dashboard + KPI report | Reuse IMM-00 KPI snapshot |

### 1.2 Out of Scope

| # | Hạng mục | Lý do |
|---|---|---|
| 1 | Tự động tích hợp API với lab bên ngoài | Workflow email/manual; defer IMM-15 |
| 2 | Tự động OCR certificate PDF | Future enhancement |
| 3 | Quản lý reference standard catalog | Defer; hiện ghi tự do bằng text |
| 4 | Validation Metrology MRA cross-border | NĐ 130/2016 chỉ tham chiếu, chưa enforce |

⚠️ Pending implementation cho toàn bộ scope mục 1.1.

---

## 2. Actors

Tái sử dụng 8 role IMM-00.

| Role | Trách nhiệm trong IMM-11 |
|---|---|
| IMM Workshop Lead | Lập lịch, chọn lab, phân công KTV, monitor trạng thái, Submit Cancel trước Submit |
| IMM Technician | Bàn giao thiết bị, upload certificate, nhập measurement, trigger Submit |
| IMM QA Officer | Review CAPA, lookback findings, RCA, Close CAPA |
| IMM Operations Manager | Xem dashboard, KPI, compliance report |
| IMM Department Head | Nhận escalation overdue, xem trend |
| IMM System Admin | Quản lý DocType, scheduler config, fixtures lab |
| IMM Storekeeper | Cập nhật `AC Supplier` (Calibration Lab) — chứng chỉ ISO 17025 |
| IMM Document Officer | Read-only audit trail, certificate archive |

---

## 3. User Stories

| ID | As a | I want | So that |
|---|---|---|---|
| US-11-01 | Workshop Lead | Xem danh sách thiết bị đến hạn calibration trong 30 ngày | Lên kế hoạch không bỏ sót |
| US-11-02 | KTV HTM | Nhập tham số đo (nominal, tolerance, measured) và hệ thống auto Pass/Fail | Loại bỏ tính toán thủ công |
| US-11-03 | KTV HTM | Upload certificate PDF trực tiếp vào record | Lưu trữ an toàn, tra cứu dễ |
| US-11-04 | QA Officer | Hệ thống tự tạo CAPA + Out of Service khi Fail | Đảm bảo không thiết bị nào fail vẫn được dùng |
| US-11-05 | Operations Manager | Xem Compliance Rate và OOT Rate theo loại thiết bị | Báo cáo BGĐ và ưu tiên nguồn lực |
| US-11-06 | QA Officer | Hệ thống tự lookback các thiết bị cùng model khi 1 thiết bị Fail | Đánh giá nhanh nguy cơ lan rộng |
| US-11-07 | KTV HTM | Xem lịch sử calibration đầy đủ của 1 thiết bị | Chuẩn bị hồ sơ thanh tra |
| US-11-08 | Workshop Lead | Hệ thống chặn tạo CAL WO khi asset Out of Service (trừ recalibration) | Tránh tạo WO sai |
| US-11-09 | Department Head | Nhận email khi có CAL overdue > 30 ngày | Escalate kịp thời |

---

## 4. Functional Requirements

### 4.1 Nhóm Calibration Schedule (FR-11-01 → FR-11-04)

| FR ID | Mô tả | Actor | DocType | Phương thức |
|---|---|---|---|---|
| FR-11-01 | Auto-tạo `IMM Calibration Schedule` khi `IMM-04 Commissioning` Submit, dựa trên `Device Model.calibration_required = 1` | System | IMM Calibration Schedule | `create_calibration_schedule_from_commissioning()` |
| FR-11-02 | Cho phép Workshop Lead update `preferred_lab`, `is_active`, `interval_days` (override) | Workshop Lead | IMM Calibration Schedule | PUT |
| FR-11-03 | Auto-suspend Schedule khi asset chuyển Decommissioned (BR-00-04 cascade) | System | IMM Calibration Schedule | `transition_asset_status()` callback |
| FR-11-04 | Daily scheduler tạo draft `IMM Asset Calibration` cho Schedule có `next_due_date <= today + 30` | System | IMM Asset Calibration | `create_due_calibration_wos()` |

### 4.2 Nhóm Asset Calibration Track External (FR-11-05 → FR-11-10)

| FR ID | Mô tả | Actor | DocType | Phương thức |
|---|---|---|---|---|
| FR-11-05 | Tạo `IMM Asset Calibration` (Draft) với `calibration_type = External`, set `lab_supplier` | KTV / Workshop Lead | IMM Asset Calibration | POST `create_calibration` |
| FR-11-06 | Validate `lab_supplier.iso_17025_certified = 1` (BR-11-01, BR-00-06) | System | IMM Asset Calibration | `validate()` |
| FR-11-07 | Chuyển status → `Sent to Lab` với `sent_date`, `sent_by` | KTV | IMM Asset Calibration | POST `send_to_lab` |
| FR-11-08 | Chuyển status → `Certificate Received` với `certificate_file`, `certificate_date`, `certificate_number` | KTV | IMM Asset Calibration | POST `receive_certificate` |
| FR-11-09 | Submit với measurements; auto compute `overall_result` | KTV | IMM Asset Calibration | POST `submit_calibration_results` |
| FR-11-10 | Block Submit nếu thiếu certificate hoặc accreditation number (BR-11-01) | System | IMM Asset Calibration | `validate()` |

### 4.3 Nhóm Asset Calibration Track In-House (FR-11-11 → FR-11-13)

| FR ID | Mô tả | Actor | DocType | Phương thức |
|---|---|---|---|---|
| FR-11-11 | Tạo `IMM Asset Calibration` với `calibration_type = In-House` | KTV | IMM Asset Calibration | POST `create_calibration` |
| FR-11-12 | Validate `reference_standard_serial`, `traceability_reference` bắt buộc | System | IMM Asset Calibration | `validate()` |
| FR-11-13 | Submit không yêu cầu certificate file (BR-11-01 chỉ áp dụng External) | KTV | IMM Asset Calibration | POST `submit_calibration_results` |

### 4.4 Nhóm Pass / Fail Handling (FR-11-14 → FR-11-18)

| FR ID | Mô tả | Actor | DocType | Phương thức |
|---|---|---|---|---|
| FR-11-14 | On Submit Pass: cập nhật `AC Asset.last_calibration_date`, `next_calibration_date = certificate_date + interval` (BR-11-04) | System | AC Asset | `handle_calibration_pass()` |
| FR-11-15 | On Submit Pass: tạo Asset Lifecycle Event `calibration_completed` | System | Asset Lifecycle Event | `create_lifecycle_event()` IMM-00 |
| FR-11-16 | On Submit Fail: `transition_asset_status(Active → Out of Service)` (BR-11-02) | System | AC Asset | `transition_asset_status()` IMM-00 |
| FR-11-17 | On Submit Fail: `create_capa(asset, source_type="IMM Asset Calibration", ...)` (BR-11-02) | System | IMM CAPA Record | `create_capa()` IMM-00 |
| FR-11-18 | On Submit Fail: `perform_lookback_assessment(device_model)` → ghi `lookback_assets` vào CAPA (BR-11-03) | System | IMM CAPA Record | `perform_lookback_assessment()` |

### 4.5 Nhóm CAPA Resolution (FR-11-19 → FR-11-21)

| FR ID | Mô tả | Actor | DocType | Phương thức |
|---|---|---|---|---|
| FR-11-19 | QA Officer nhập `lookback_status` (Cleared / Action Required) + findings | QA Officer | IMM CAPA Record | POST `resolve_capa_lookback` |
| FR-11-20 | Block `close_capa()` nếu `lookback_status = Pending` (BR-11-03) | System | IMM CAPA Record | `before_submit()` |
| FR-11-21 | Sau CAPA Closed + recalibration Pass: `transition_asset_status(Out of Service → Active)` + lifecycle event `calibration_conditionally_passed` | System | AC Asset + ALE | `handle_calibration_pass()` (re-cal flag) |

### 4.6 Nhóm Scheduler Jobs (FR-11-22 → FR-11-24)

| FR ID | Mô tả | Tần suất | Đối tượng nhận |
|---|---|---|---|
| FR-11-22 | `create_due_calibration_wos` — tạo draft CAL cho Schedule due trong 30 ngày | Daily 06:00 | — |
| FR-11-23 | `check_calibration_expiry` — update `calibration_status` (On Schedule / Due Soon / Overdue); email alert 90/60/30/0 ngày | Daily 06:30 | Workshop Lead, Department Head |
| FR-11-24 | `check_capa_overdue` (reuse IMM-00) — CAPA Open > 30 ngày | Daily 02:00 | QA Officer + responsible |

### 4.7 Nhóm Reporting (FR-11-25 → FR-11-27)

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-11-25 | Compliance report theo tháng (compliance rate, OOT rate, CAPA closure) | Operations Manager, PTP | GET `get_calibration_compliance_report` |
| FR-11-26 | Lịch sử calibration của 1 thiết bị | All | GET `get_asset_calibration_history` |
| FR-11-27 | Danh sách thiết bị đến hạn trong N ngày | Workshop Lead | GET `get_due_calibrations` |

⚠️ Pending implementation — tất cả FR-11-* chưa có code.

---

## 5. Permission Matrix

| Role | IMM Calibration Schedule | IMM Asset Calibration | IMM CAPA Record | AC Asset (cal fields) |
|---|---|---|---|---|
| IMM Workshop Lead | C/R/W | C/R/W/Submit/Cancel(draft)/Amend | R | R |
| IMM Technician | R | R/W (assigned only) | R | R |
| IMM Operations Manager | R | R | R | R |
| IMM QA Officer | R | R | C/R/W/Submit/Close | R |
| IMM Department Head | R | R | R | R |
| IMM System Admin | C/R/W/D | C/R/W/D | C/R/W/D | C/R/W |
| IMM Storekeeper | R | R | R | R |
| IMM Document Officer | R | R | R | R |

Permission Query: IMM Technician chỉ thấy `IMM Asset Calibration` mà `technician = session.user`.

---

## 6. Validation Rules

| VR ID | Field | Rule | Error Message (vi) |
|---|---|---|---|
| VR-11-01 | `lab_supplier` (External) | Bắt buộc; `vendor_type = "Calibration Lab"`; `iso_17025_certified = 1` | "Vui lòng chọn lab hiệu chuẩn có chứng chỉ ISO/IEC 17025 (BR-11-01)" |
| VR-11-02 | `certificate_file` (External) | Bắt buộc trước Submit | "Vui lòng upload Calibration Certificate trước khi Submit (BR-11-01)" |
| VR-11-03 | `lab_accreditation_number` (External) | Bắt buộc trước Submit | "Vui lòng nhập Số công nhận ISO/IEC 17025 (BR-11-01)" |
| VR-11-04 | `measurements` | ≥1 row; mỗi row có `measured_value` không null | "Phải có ít nhất một tham số đo lường và tất cả phải có giá trị" |
| VR-11-05 | `certificate_date` | ≤ today; bắt buộc khi `overall_result = Passed` (External) | "Ngày cấp chứng chỉ là bắt buộc và không thể là ngày trong tương lai" |
| VR-11-06 | `reference_standard_serial` (In-House) | Bắt buộc | "Vui lòng nhập serial thiết bị chuẩn cho calibration nội bộ" |
| VR-11-07 | `traceability_reference` (In-House) | Bắt buộc | "Vui lòng nhập tham chiếu traceability" |
| VR-11-08 | `asset` | Phải pass `validate_asset_for_operations()` (trừ flag `is_recalibration=1`) | "Thiết bị ở trạng thái {status}, không thể tạo Calibration WO" |
| VR-11-09 | `amendment_reason` | Bắt buộc khi Amend | "Lý do sửa đổi là bắt buộc khi Amend Phiếu Hiệu chuẩn (BR-11-05)" |
| VR-11-10 | (record) | Block Cancel sau Submit | "Không thể hủy Phiếu Hiệu chuẩn đã Submit. Vui lòng dùng Amend (BR-11-05)" |
| VR-11-11 | CAPA `lookback_status` | Phải != Pending trước khi Close CAPA | "CAPA chưa hoàn thành Lookback. Vui lòng cập nhật trước khi đóng (BR-11-03)" |
| VR-11-12 | `Device Model.calibration_interval_days` | > 0 khi tạo Schedule | "Device Model chưa có chu kỳ hiệu chuẩn. Vui lòng cập nhật trước" |

---

## 7. Non-Functional Requirements

| NFR ID | Category | Yêu cầu | Target |
|---|---|---|---|
| NFR-11-01 | Performance — list | GET calibration list với filter | P95 < 300ms với 50k records |
| NFR-11-02 | Performance — submit | POST submit_calibration_results (với 10 measurements) | P95 < 1s |
| NFR-11-03 | Storage | Certificate PDF retention | ≥ 7 năm (NĐ98) |
| NFR-11-04 | Scheduler reliability | Tạo CAL WO trước due_date 30 ngày | Idempotent, retry ≤ 3 lần |
| NFR-11-05 | Alert delivery | Cảnh báo overdue 90/60/30/0 ngày | Daily, không miss |
| NFR-11-06 | Audit retention | Asset Lifecycle Event + Audit Trail không xoá | ≥ 7 năm |
| NFR-11-07 | I18n | Mọi error message qua `frappe._()` | Gói `vi.csv` |
| NFR-11-08 | Security | Permission Query enforce technician scope | Tested via UAT |
| NFR-11-09 | Concurrency | 2 user edit cùng CAL → optimistic lock | TimestampMismatchError |
| NFR-11-10 | API contract | Mọi response qua `_ok` / `_err` | Enforce `utils/response.py` |

---

## 8. Acceptance Criteria (Gherkin)

### 8.1 Track External — Pass

```gherkin
Scenario: AC-11-01 — External calibration Pass
  Given AC Asset "AC-ASSET-2026-00101" có lifecycle_status="Active"
    And Device Model.calibration_interval_days = 365
    And AC Supplier "AC-SUP-2026-0010" có vendor_type="Calibration Lab", iso_17025_certified=1
  When KTV POST submit_calibration_results với
    {name: "CAL-2026-00001", certificate_date: "2026-04-24",
     certificate_file: "/files/cert.pdf",
     measurements: [{nominal: 7.5, tol+: 3, tol-: 3, measured: 7.6}, ...]}
  Then doc.status = "Passed"
    And doc.overall_result = "Passed"
    And AC Asset.next_calibration_date = "2027-04-24"
    And có 1 Asset Lifecycle Event event_type="calibration_completed"
    And không có CAPA được tạo
```

### 8.2 Track External — Fail → Auto CAPA + OOS

```gherkin
Scenario: AC-11-02 — External calibration Fail triggers CAPA
  Given AC Asset "AC-ASSET-2026-00101" Active
    And có 2 asset khác cùng device_model "Sysmex XN-1000" Active
  When KTV submit với 1 measurement out_of_tolerance
  Then doc.status = "Failed"
    And AC Asset.lifecycle_status = "Out of Service" (qua transition_asset_status)
    And có 1 IMM CAPA Record với source_type="IMM Asset Calibration", source_ref=doc.name,
        lookback_required=1, lookback_status="In Progress",
        lookback_assets có 2 asset cùng model
    And có Asset Lifecycle Event event_type="calibration_failed"
    And email gửi tới IMM QA Officer + IMM Operations Manager
```

### 8.3 Track External — Block thiếu certificate

```gherkin
Scenario: AC-11-03 — Block Submit khi thiếu certificate
  Given IMM Asset Calibration với calibration_type="External", certificate_file=NULL
  When KTV Submit
  Then throw ValidationError "Vui lòng upload Calibration Certificate trước khi Submit (BR-11-01)"
    And docstatus vẫn = 0
```

### 8.4 Track External — Block lab không ISO 17025

```gherkin
Scenario: AC-11-04 — Block lab không có ISO/IEC 17025
  Given AC Supplier "AC-SUP-X" có vendor_type="Calibration Lab", iso_17025_certified=0
  When KTV chọn lab này cho IMM Asset Calibration
  Then throw ValidationError "Vui lòng chọn lab hiệu chuẩn có chứng chỉ ISO/IEC 17025 (BR-11-01)"
```

### 8.5 Track In-House — Pass không cần certificate

```gherkin
Scenario: AC-11-05 — In-House calibration Pass
  Given IMM Asset Calibration với calibration_type="In-House",
        reference_standard_serial="FLUKE-REF-001", traceability_reference="VLAS-T-099-REF"
    And tất cả measurements Pass
  When KTV Submit (không upload certificate)
  Then doc.status = "Passed"
    And không yêu cầu certificate_file
    And AC Asset.next_calibration_date = actual_date + interval
```

### 8.6 BR-11-04 — next_calibration_date từ certificate_date

```gherkin
Scenario: AC-11-06 — next_calibration_date tính từ certificate_date
  Given AC Asset có next_calibration_date = "2026-05-01"
    And Device Model.calibration_interval_days = 365
  When KTV submit với certificate_date = "2026-04-24" (Pass)
  Then AC Asset.next_calibration_date = "2027-04-24" (KHÔNG phải 2027-05-01)
```

### 8.7 Lookback assessment

```gherkin
Scenario: AC-11-07 — Lookback list assets cùng model
  Given AC Asset A,B,C,D cùng device_model "Sysmex XN-1000", lifecycle_status=Active
    And AC Asset E cùng model nhưng lifecycle_status=Decommissioned
  When IMM Asset Calibration của asset A submit Failed
  Then CAPA record có lookback_assets = [B, C, D] (loại trừ A và E)
    And lookback_status = "In Progress"
```

### 8.8 CAPA Closed → Asset Active

```gherkin
Scenario: AC-11-08 — CAPA Closed + recalibration Pass restore Asset
  Given CAPA "CAPA-2026-00015" linked CAL Failed, lookback_status="Cleared",
        có root_cause + corrective + preventive
    And AC Asset Out of Service
    And IMM Asset Calibration mới (recalibration) cho cùng asset đã Pass
  When QA Officer close_capa
  Then CAPA.status = "Closed"
    And AC Asset.lifecycle_status = "Active" (qua transition_asset_status)
    And có Asset Lifecycle Event event_type="calibration_conditionally_passed"
```

### 8.9 BR-11-05 — Immutable

```gherkin
Scenario: AC-11-09 — Block Cancel/Delete sau Submit
  Given IMM Asset Calibration "CAL-2026-00001" docstatus=1
  When user thử Cancel hoặc Delete
  Then throw ValidationError "Không thể hủy Phiếu Hiệu chuẩn đã Submit. Vui lòng dùng Amend (BR-11-05)"
```

### 8.10 Scheduler tạo WO 30 ngày trước hạn

```gherkin
Scenario: AC-11-10 — Daily scheduler tạo CAL WO
  Given IMM Calibration Schedule có next_due_date = today + 25 ngày, is_active=1
    And chưa có IMM Asset Calibration đang xử lý cho cùng asset
  When scheduler create_due_calibration_wos chạy
  Then có 1 IMM Asset Calibration mới với status="Scheduled", scheduled_date=next_due_date
```

---

## 9. Business Rules (consolidated)

| BR ID | Rule | Enforce | Chuẩn |
|---|---|---|---|
| BR-11-01 | External: lab ISO 17025 + certificate + accreditation number bắt buộc | `validate()` | ISO/IEC 17025 |
| BR-11-02 | Fail → Out of Service + CAPA bắt buộc | `on_submit` Fail path | ISO 13485:8.5.2 |
| BR-11-03 | Lookback bắt buộc cùng `device_model` | `perform_lookback_assessment()` | WHO HTM §5.4.6 |
| BR-11-04 | `next_cal = certificate_date + interval` | `handle_calibration_pass()` | Internal |
| BR-11-05 | Immutable sau Submit; chỉ Amend với reason | Submittable + `on_cancel` | ISO 13485:4.2.5 |
| BR-11-06 | Decommissioned → suspend Schedule | `transition_asset_status()` cascade | WHO HTM |
| BR-11-07 | `validate_asset_for_operations()` gate (trừ recalibration) | service entry | BR-00-05 |

Inherits: BR-00-02, BR-00-03, BR-00-04, BR-00-05, BR-00-06, BR-00-08, BR-00-09, BR-00-10.

---

## 10. Glossary

| Thuật ngữ | Nghĩa |
|---|---|
| Calibration | Hiệu chuẩn — so sánh thiết bị đo với chuẩn |
| Tolerance | Dung sai cho phép (+/- around nominal) |
| Out of Tolerance (OOT) | Giá trị đo nằm ngoài dung sai |
| ISO/IEC 17025 | Tiêu chuẩn năng lực phòng thử nghiệm và hiệu chuẩn |
| Lookback Assessment | Đánh giá hồi cứu các thiết bị cùng model khi 1 thiết bị Fail |
| Certificate | Chứng chỉ hiệu chuẩn cấp bởi lab |
| Recalibration | Hiệu chuẩn lại sau CAPA |
| NĐ 130/2016 | Nghị định 130/2016/NĐ-CP về đo lường |
