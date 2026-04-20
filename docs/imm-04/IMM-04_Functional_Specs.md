# IMM-04 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE — 31/32 UAT PASS |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | WHO HTM 2025, NĐ 98/2021, NĐ 142/2020, ISO 13485:2016, TT 46/2017/TT-BYT |

---

## 1. Scope

### 1.1 In Scope

| # | Hạng mục | Ghi chú |
|---|---|---|
| 1 | DocType `Asset Commissioning` + 3 child + NC độc lập | Schema theo `asset_commissioning.json` |
| 2 | Workflow 11 states + 22 transitions | `IMM-04 Workflow` (Frappe Workflow Engine) |
| 3 | 6 Gate (G01–G06) + 7 Validation Rules (VR-01 → VR-07) | Backend enforce trong service + controller |
| 4 | 17 REST endpoint | `assetcore/api/imm04.py` |
| 5 | Auto-mint ERPNext Asset on Submit | `mint_core_asset()` |
| 6 | Auto-import sang IMM-05 | `create_initial_document_set()` |
| 7 | GW-2 compliance gate | `_gw2_check_document_compliance()` (BR-07) |
| 8 | Generate QR data + barcode lookup | `generate_qr_label()`, `get_barcode_lookup()` |
| 9 | Dashboard KPIs | `get_dashboard_stats()` |
| 10 | Scheduler cảnh báo phiếu mở > 30 ngày | `check_commissioning_overdue` (daily) |

### 1.2 Out of Scope

| # | Hạng mục | Lý do defer |
|---|---|---|
| 1 | PM Schedule auto-create | Sang IMM-08 (`fire_release_event` đã bắn, cần listener) |
| 2 | PDF Print Format Biên bản Bàn giao | Cần config Print Format trong Frappe UI |
| 3 | QR label PDF template (server-side) | Hiện chỉ render trên FE |
| 4 | Auto-detect Clinical Hold sau Initial Inspection | QA Officer hiện trigger thủ công |
| 5 | SLA auto-escalation | Dashboard show overdue, chưa email tự động |

---

## 2. Actors

| Actor | Role hệ thống | Trách nhiệm chính |
|---|---|---|
| HTM Technician | `HTM Technician` | Tạo phiếu Commissioning từ PO, ghi nhận nhận hàng |
| Biomed Engineer | `Biomed Engineer` | Edit phiếu, gán SN+QR, đo baseline, trigger transition lắp đặt/kiểm tra |
| Vendor Engineer | `Vendor Engineer` | Xác nhận lắp đặt hoàn thành, báo DOA |
| QA Officer | `QA Officer` | Trigger Clinical Hold, upload giấy phép BYT, gỡ Hold |
| Workshop Head | `Workshop Head` | Submit/Cancel/Amend phiếu (permlevel 1) |
| VP Block2 | `VP Block2` | Submit/Cancel cuối cùng (board approver) |
| CMMS Admin | `CMMS Admin` | Override workflow transition khi cần |
| QA Risk Team | `QA Risk Team` | Read/Write — review hồ sơ chất lượng |
| Purchase User | `Purchase User` | Nhận realtime notification khi Asset released (kích hoạt khấu hao) |

---

## 3. User Stories (Gherkin)

### 3.1 Tạo phiếu từ PO

```gherkin
Scenario: US-04-01 — Tạo Commissioning từ PO hợp lệ
  Given tôi có role "HTM Technician" hoặc "Biomed Engineer"
    And PO "PO-2026-00023" tồn tại với supplier và item hợp lệ
  When tôi POST /api/method/assetcore.api.imm04.create_commissioning
    với {po_reference, master_item, vendor, clinical_dept, expected_installation_date}
  Then response.success = true
    And data.name khớp regex "^IMM04-\d{2}-\d{2}-\d{5}$"
    And workflow_state = "Draft"
    And mandatory documents (CO, CQ, Manual) được populate sẵn với status = Pending
    And nếu risk_class ∈ {C,D,Radiation} → thêm row "License" mandatory
```

### 3.2 Validate Serial Number unique

```gherkin
Scenario: US-04-02 — VR-01 block SN trùng
  Given commissioning ACC-A đã có vendor_serial_no = "SN-12345"
  When tôi gọi assign_identification(name=ACC-B, vendor_serial_no="SN-12345")
  Then response.success = false
    And error.code = "VALIDATION_ERROR"
    And message chứa "VR-01: Serial 'SN-12345' đã được gán"
```

### 3.3 Gate G01 — mandatory documents

```gherkin
Scenario: US-04-03 — Block transition khi thiếu CO
  Given commissioning ở "Pending Doc Verify"
    And mandatory doc "CO" có status = "Pending"
  When transition_state(action="Xác nhận đủ tài liệu")
  Then throw ValidationError "VR-02 (Gate G01): Chưa đủ tài liệu bắt buộc. Còn thiếu: CO"
```

### 3.4 Gate G03 — baseline test

```gherkin
Scenario: US-04-04 — Baseline có row Fail → Re Inspection
  Given commissioning ở "Initial Inspection"
    And baseline row "Leakage Current" có test_result = "Fail"
  When submit_baseline_checklist(name, results)
  Then response.success = false
    And error chứa "BR-04-04: Thông số sau không đạt: Leakage Current"
    And phải transition về "Re Inspection"
```

### 3.5 VR-07 — Clinical Hold cho Class C/D/Radiation

```gherkin
Scenario: US-04-05 — Auto Clinical Hold
  Given commissioning có risk_class = "C" hoặc is_radiation_device = 1
    And baseline test toàn Pass
  When check_auto_clinical_hold(doc) chạy
  Then trả True
    And is_radiation_device = 1
    And QA Officer phải trigger "Giữ lâm sàng" để vào state Clinical Hold
    And Clinical Release bị block tới khi qa_license_doc được upload (VR-07)
```

### 3.6 G05+G06 — Clinical Release

```gherkin
Scenario: US-04-06 — Block release khi còn Open NC
  Given commissioning ở "Clinical Release" (chuẩn bị submit)
    And tồn tại Asset QA Non Conformance với resolution_status = "Open" liên kết phiếu
  When approve_clinical_release(commissioning, board_approver)
  Then response.error = "VR-04: Còn N NC chưa đóng. Giải quyết trước khi Release."
```

```gherkin
Scenario: US-04-07 — Submit thành công sinh Asset
  Given commissioning ở "Clinical Release", board_approver đã set
    And không còn Open NC
    And IMM-05 có Chứng nhận ĐKLH Active hoặc Exempt (BR-07/GW-2)
  When VP Block2 hoặc Workshop Head gọi submit_commissioning(name)
  Then docstatus = 1
    And final_asset = "ACC-ASS-..." (ERPNext Asset mới)
    And Asset.custom_vendor_serial = doc.vendor_serial_no
    And Asset.custom_internal_qr = doc.internal_tag_qr
    And Asset Document Draft được tạo cho mỗi Received doc (IMM-05)
    And realtime event "imm04_asset_released" được publish
```

### 3.7 Báo DOA

```gherkin
Scenario: US-04-08 — Báo DOA khi đang Installing
  Given commissioning ở "Installing"
  When report_doa(commissioning, description, evidence_file)
  Then tạo Asset QA Non Conformance với nc_type="DOA", severity="Critical", resolution_status="Open"
    And doa_incident = 1
    And user phải transition phiếu sang "Non Conformance"
```

---

## 4. Business Rules

| BR ID | Rule | Enforce | Test ref |
|---|---|---|---|
| BR-04-01 | Asset chỉ tạo qua pipeline IMM-04 | `on_submit` → `mint_core_asset()` | TC-04-02 |
| BR-04-02 (G01) | CO/CQ/Manual mandatory phải Received/Waived | `validate_gate_g01()` | TC-04-05, TC-04-06 |
| BR-04-03 (VR-01) | vendor_serial_no UNIQUE | `validate_unique_serial()` + `_vr01_unique_serial_number()` | TC-04-03, TC-04-04 |
| BR-04-04 (G03) | 100% baseline Pass/N/A trước Release; Fail → Re Inspection | `validate_checklist_completion()` | TC-04-15..18 |
| BR-04-05 (VR-07) | Bức xạ → bắt buộc qa_license_doc trước Release | `validate_radiation_hold()` | TC-04-19..21 |
| BR-04-06 (VR-04) | No Open NC trước Release | `validate_gate_g05_g06()` + `block_release_if_nc_open()` | TC-04-22..24 |
| BR-04-07 (G06) | board_approver bắt buộc | `validate_gate_g05_g06()` | TC-04-25 |
| BR-04-08 (BR-07/GW-2) | Asset có Chứng nhận ĐKLH Active hoặc Exempt | `_gw2_check_document_compliance()` | TC-04-26 |

---

## 5. Permission Matrix

| Endpoint / Action | HTM Tech | Biomed Eng | Vendor Eng | QA Officer | Workshop Head | VP Block2 | CMMS Admin |
|---|---|---|---|---|---|---|---|
| `create_commissioning` | W | W | — | — | R | R | W |
| `get_form_context` | R | R | R (own) | R | R | R | R |
| `list_commissioning` | R | R | — | R | R | R | R |
| `save_commissioning` | W (Draft) | W (≤Identification) | — | W (Hold) | — | — | W |
| `assign_identification` | — | W | — | — | — | — | W |
| `submit_baseline_checklist` | — | W | — | — | — | — | W |
| `clear_clinical_hold` | — | — | — | W | — | — | W |
| `report_nonconformance` / `report_doa` | W | W | W | — | W | — | W |
| `close_nonconformance` | — | W | — | W | W | — | W |
| `approve_clinical_release` | — | — | — | — | — | W | W |
| `submit_commissioning` | — | — | — | — | W | W | — |
| `transition_state` | role-checked theo workflow JSON | | | | | | |
| `generate_qr_label` / `get_barcode_lookup` | R | R | R | R | R | R | R |
| `get_dashboard_stats` | R | R | — | R | R | R | R |
| `generate_handover_pdf` | R | W | — | — | R | R | R |

---

## 6. Validation Rules

| VR ID | Field / Scope | Rule | Error Message (vi) | Enforce |
|---|---|---|---|---|
| VR-01 | `vendor_serial_no` | UNIQUE trên Asset (`custom_vendor_serial`) + Asset Commissioning (docstatus≠2) | "VR-01: Serial Number '{sn}' đã được đăng ký cho tài sản {asset}." | `validate_unique_serial()` + service |
| VR-02 | `commissioning_documents[is_mandatory=1]` | status ∈ {Received, Waived} trước khi rời Pending Doc Verify | "VR-02 (Gate G01): Chưa đủ tài liệu bắt buộc. Còn thiếu: {list}" | `validate_gate_g01()` |
| VR-03 | `baseline_tests` | Mọi row có `test_result`; Fail → bắt buộc `fail_note`; nếu có Fail → block Clinical Release | "VR-03b: Không thể Phát hành! Các tiêu chí sau Không Đạt: {list}" | `validate_checklist_completion()` |
| VR-04 | `Asset QA Non Conformance` | No row resolution_status="Open" linked | "VR-04 (Gate G05): Còn {n} NC chưa đóng." | `validate_gate_g05_g06()` |
| VR-05 | `risk_class` | Cảnh báo (msgprint) nếu đổi sau Initial Inspection | "VR-05: Phân loại rủi ro thay đổi từ '{old}' → '{new}'." | `_vr05_risk_class_change_warning()` |
| VR-06 | `lifecycle_events` | Block edit row đã insert (immutable) | "VR-06: Nhật ký sự kiện vòng đời không được chỉnh sửa." | `_vr06_immutable_lifecycle_events()` |
| VR-07 | `qa_license_doc` | Bắt buộc nếu `is_radiation_device=1` và workflow_state=Clinical_Release | "VR-07: Thiết bị này phát bức xạ nhưng chưa có Giấy phép." | `validate_radiation_hold()` |
| VR-Backdate | `installation_date` | ≥ PO `transaction_date` | "Lỗi Back-date: Ngày lắp đặt ({d1}) không thể trước Ngày đặt hàng PO ({d2})." | `validate_backdate()` |
| VR-DocExpiry | `commissioning_documents[].expiry_date` | Throw nếu < today; warning nếu < 30 ngày | "Tài liệu '{type}' đã hết hạn vào {date}." | `_validate_document_expiry()` |

---

## 7. Non-Functional Requirements

| NFR ID | Loại | Yêu cầu | Target |
|---|---|---|---|
| NFR-04-01 | Performance | Tải form Commissioning đầy đủ (50+ field, 3 child) | P95 < 2s |
| NFR-04-02 | Performance | `check_sn_unique` (on-blur) | < 500ms |
| NFR-04-03 | Performance | `get_dashboard_stats` | < 1s |
| NFR-04-04 | Reliability | Scheduler `check_commissioning_overdue` chạy 02:00 daily | Độ trễ < 5 phút |
| NFR-04-05 | Security | Submit chỉ VP Block2 / Workshop Head (whitelist trong API) | Permission test |
| NFR-04-06 | Audit | Mọi state transition tạo 1 Lifecycle Event | 100% coverage; VR-06 immutable |
| NFR-04-07 | Usability | Form responsive trên tablet 768px | Manual test |
| NFR-04-08 | Data integrity | vendor_serial_no UNIQUE cross-table | Integration test TC-04-03 |
| NFR-04-09 | Compliance | Lifecycle event không thể xoá/sửa sau Submit | DB + perm + VR-06 |
| NFR-04-10 | Localization | Mọi user-facing message bằng tiếng Việt | `frappe._()` wrap |
| NFR-04-11 | Realtime | `imm04_asset_released` publish < 1s sau on_submit | `frappe.publish_realtime` |

---

## 8. Acceptance Criteria — Global

| Mã | Acceptance Criteria |
|---|---|
| AC-04-01 | 31/32 UAT case PASS; TC-32 (PM auto-create) FAIL được track trong Known Gaps |
| AC-04-02 | Mọi VR/Gate enforce ở backend; FE chỉ pre-validate UX |
| AC-04-03 | Mọi error trả về `_err(message_vi, code)` envelope |
| AC-04-04 | Mọi success trả về `_ok({...})` envelope |
| AC-04-05 | Audit trail (`lifecycle_events`) ghi mọi: insert, doc upload, identification, baseline submit, hold, release, cancel |
| AC-04-06 | `final_asset` được set trước khi `on_submit` kết thúc; rollback nếu mint thất bại |

---

## 9. Glossary

| Thuật ngữ | Nghĩa |
|---|---|
| ACC / IMM04 | Mã phiếu nghiệm thu (Asset Commissioning) |
| Gate G01–G06 | 6 checkpoint nghiệp vụ trong workflow (xem §4) |
| GW-2 | Gateway 2 — kiểm tra hồ sơ pháp lý IMM-05 trước Submit |
| DOA | Dead-on-Arrival (hỏng ngay khi khui hộp) |
| NC | Non-Conformance — phiếu báo lỗi |
| BV-{DEPT}-{YYYY}-{SEQ} | Format internal QR (auto-sinh khi vào state Identification) |

*End of Functional Specs v2.0.0 — IMM-04*
