# IMM-06 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — Bàn giao & Đào tạo |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |
| Trạng thái | DESIGN — Wave 2 |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | WHO HTM 2025, ISO 13485:2016 §6.2, §7.3, NĐ 98/2021 |

---

## 1. Scope

### 1.1 In Scope

| # | Hạng mục | Ghi chú |
|---|---|---|
| 1 | DocType `Handover Record` + child | Schema theo `handover_record.json` |
| 2 | DocType `Training Session` + `Training Trainee` child | Schema theo `training_session.json` |
| 3 | Workflow 5 states + 7 transitions | `IMM-06 Workflow` (Frappe Workflow Engine) |
| 4 | 4 Validation Rules (VR-01 → VR-04) + 3 Gates | Backend enforce trong service + controller |
| 5 | 8 REST endpoint | `assetcore/api/imm06.py` |
| 6 | Lifecycle Event ghi nhận trên Submit | `log_lifecycle_event()` |
| 7 | Dashboard KPIs | `get_dashboard_stats()` |
| 8 | Training history per asset | `get_asset_training_history()` |

### 1.2 Out of Scope

| # | Hạng mục | Lý do defer |
|---|---|---|
| 1 | Tự động tạo training schedule từ Device Model | Wave 3 |
| 2 | E-learning / digital training materials | Ngoài phạm vi HTM core |
| 3 | Certificate PDF generation | Cần config Print Format |
| 4 | SMS/email nhắc lịch đào tạo | Wave 3 notification system |

---

## 2. Actors

| Actor | Role hệ thống | Trách nhiệm chính |
|---|---|---|
| HTM Technician | `HTM Technician` | Tạo phiếu bàn giao, liên kết commissioning |
| Biomed Engineer | `Biomed Engineer` | Lên lịch và dẫn đào tạo kỹ thuật |
| Vendor Trainer | `Vendor Engineer` | Đào tạo do nhà cung cấp thực hiện |
| Clinical Dept Head | `Department Head` | Ký xác nhận nhận bàn giao khoa |
| QA Officer | `QA Officer` | Xác nhận đủ năng lực, phê duyệt bàn giao |
| CMMS Admin | `CMMS Admin` | Override workflow transition khi cần |

---

## 3. User Stories (Gherkin)

### 3.1 Tạo phiếu bàn giao từ Commissioning

```gherkin
Scenario: US-06-01 — Tạo Handover Record từ Commissioning hợp lệ
  Given tôi có role "HTM Technician" hoặc "Biomed Engineer"
    And commissioning "IMM04-26-04-00001" có workflow_state = "Clinical Release"
    And docstatus = 1
  When tôi POST /api/method/assetcore.api.imm06.create_handover_record
    với {commissioning_ref, clinical_dept, handover_date, received_by, handover_type}
  Then response.success = true
    And data.name khớp regex "^HR-\d{2}-\d{2}-\d{5}$"
    And workflow_state = "Draft"
    And data.asset được fetch tự động từ commissioning
```

### 3.2 VR-01 — Block commissioning chưa Clinical Release

```gherkin
Scenario: US-06-02 — Block tạo Handover khi commissioning chưa Released
  Given commissioning "IMM04-26-04-00002" có workflow_state = "Initial Inspection"
  When tôi gọi create_handover_record(commissioning_ref="IMM04-26-04-00002", ...)
  Then response.success = false
    And error.code = "VALIDATION_ERROR"
    And message chứa "VR-01: Commissioning chưa đạt Clinical Release"
```

### 3.3 Lên lịch đào tạo

```gherkin
Scenario: US-06-03 — Lên lịch Training Session thành công
  Given handover "HR-26-04-00001" ở trạng thái "Draft"
    And trainer "biomed@benhvien.vn" tồn tại
  When tôi POST /api/method/assetcore.api.imm06.schedule_training
    với {handover_name, training_type="Operation", trainer, training_date, duration_hours=2}
  Then response.success = true
    And data.name khớp regex "^TS-\d{2}-\d{2}-\d{5}$"
    And handover workflow_state chuyển sang "Training Scheduled"
```

### 3.4 Hoàn thành đào tạo với điểm số

```gherkin
Scenario: US-06-04 — Ghi nhận kết quả đào tạo
  Given training_session "TS-26-04-00001" có 3 trainees chưa có điểm
  When tôi POST complete_training
    với scores = [{trainee_user, score: 85, passed: true}, ...]
  Then response.success = true
    And tất cả trainee rows được cập nhật điểm
    And competency_confirmed = true (nếu tất cả passed)
```

### 3.5 Gate G01 — Bàn giao không có đào tạo

```gherkin
Scenario: US-06-05 — Block Handover Pending khi chưa có đào tạo
  Given handover "HR-26-04-00002" ở "Draft"
    And không có Training Session nào linked
  When transition sang "Handover Pending"
  Then throw ValidationError
    And message chứa "VR-03: Phải hoàn thành ít nhất 1 buổi đào tạo trước khi bàn giao"
```

### 3.6 Xác nhận bàn giao và Submit

```gherkin
Scenario: US-06-06 — Xác nhận bàn giao thành công
  Given handover "HR-26-04-00003" ở "Handover Pending"
    And có ít nhất 1 Training Session completed
    And dept_head_signoff đã được set
  When Clinical Dept Head gọi confirm_handover(name, dept_head_signoff)
  Then docstatus = 1
    And workflow_state = "Handed Over"
    And Asset Lifecycle Event "handover_completed" được tạo
    And asset.current_dept được update
```

### 3.7 VR-02 — Không tạo trùng Handover

```gherkin
Scenario: US-06-07 — Block tạo Handover trùng
  Given asset "ACC-26-04-00001" đã có Handover Record "HR-26-04-00001" với trạng thái "Handed Over"
  When tôi tạo Handover Record mới cho cùng asset
  Then response.success = false
    And message chứa "VR-02: Asset này đã có phiếu bàn giao hoàn thành"
```

---

## 4. Business Rules

| BR ID | Rule | Enforce | Test ref |
|---|---|---|---|
| BR-06-01 | Commissioning phải Clinical Release (docstatus=1) trước khi tạo Handover | `before_insert` → `validate_commissioning_released()` | TC-06-01, TC-06-02 |
| BR-06-02 | Asset không được có Handover Record Handed Over khác | `validate` → `validate_no_duplicate_handover()` | TC-06-07 |
| BR-06-03 | Phải có ≥1 Training Session completed trước Handover Pending | `validate_gate_g01()` | TC-06-05, TC-06-06 |
| BR-06-04 | `dept_head_signoff` bắt buộc trước Submit | `confirm_handover()` | TC-06-10 |
| BR-06-05 | Tất cả trainees phải có điểm trước khi complete_training | service validation | TC-06-08, TC-06-09 |

---

## 5. Permission Matrix

| Endpoint / Action | HTM Tech | Biomed Eng | Vendor Eng | Dept Head | QA Officer | CMMS Admin |
|---|---|---|---|---|---|---|
| `create_handover_record` | W | W | — | — | R | W |
| `get_handover_record` | R | R | R | R | R | R |
| `list_handover_records` | R | R | — | R | R | R |
| `schedule_training` | W | W | W | — | — | W |
| `complete_training` | — | W | W | — | W | W |
| `confirm_handover` | — | — | — | W | W | W |
| `get_asset_training_history` | R | R | R | R | R | R |
| `get_dashboard_stats` | R | R | — | R | R | R |

---

## 6. Validation Rules

| VR ID | Field / Scope | Rule | Error Message (vi) | Enforce |
|---|---|---|---|---|
| VR-01 | `commissioning_ref` | commissioning.docstatus=1 AND workflow_state="Clinical Release" | "VR-01: Commissioning '{ref}' chưa đạt trạng thái Clinical Release. Không thể tạo phiếu bàn giao." | `validate_commissioning_released()` |
| VR-02 | `asset` | Không có Handover Record khác với asset này ở trạng thái Handed Over | "VR-02: Thiết bị '{asset}' đã có phiếu bàn giao hoàn thành '{record}'. Không thể tạo trùng." | `validate_no_duplicate_handover()` |
| VR-03 | `training_sessions` | Phải có ≥1 Training Session linked với status Completed trước khi Handover Pending | "VR-03: Phải hoàn thành ít nhất 1 buổi đào tạo trước khi chuyển sang chờ bàn giao." | `validate_training_gate()` |
| VR-04 | `dept_head_signoff` | Bắt buộc khác None trước Submit | "VR-04: Bắt buộc có chữ ký Trưởng khoa trước khi hoàn tất bàn giao." | `confirm_handover()` |

---

## 7. Non-Functional Requirements

| NFR ID | Loại | Yêu cầu | Target |
|---|---|---|---|
| NFR-06-01 | Performance | Tải form Handover đầy đủ | P95 < 2s |
| NFR-06-02 | Performance | `get_dashboard_stats` | < 1s |
| NFR-06-03 | Audit | Mọi state transition tạo Lifecycle Event | 100% coverage |
| NFR-06-04 | Security | Submit chỉ Dept Head / QA Officer / CMMS Admin | Permission test |
| NFR-06-05 | Localization | Mọi message bằng tiếng Việt | `frappe._()` wrap |

---

## 8. Acceptance Criteria

| Mã | Acceptance Criteria |
|---|---|
| AC-06-01 | VR-01 block tạo handover khi commissioning chưa Clinical Release |
| AC-06-02 | Training Session được tạo thành công với trainees table |
| AC-06-03 | complete_training ghi nhận điểm từng học viên |
| AC-06-04 | Gate G01 block Handover Pending khi chưa có đào tạo |
| AC-06-05 | confirm_handover chạy on_submit → Lifecycle Event `handover_completed` |
| AC-06-06 | dashboard_stats trả về đúng số pending / completed |

---

## 9. Glossary

| Thuật ngữ | Nghĩa |
|---|---|
| HR | Handover Record — mã phiếu bàn giao |
| TS | Training Session — buổi đào tạo |
| Competency | Năng lực vận hành được xác nhận qua đào tạo |
| Conditional Handover | Bàn giao có điều kiện — thiết bị có hạn chế sử dụng |

*End of Functional Specs v1.0.0 — IMM-06*
