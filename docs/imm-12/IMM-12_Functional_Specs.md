# IMM-12 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | **DRAFT** — chỉ có CAPA DocType từ IMM-00, code IMM-12 chưa implement |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | ISO 13485:2016 §8.5, WHO HTM 2025 §5.3.4, NĐ 98/2021 Điều 38, MEDDEV 2.7/1 |

---

## 1. Scope

### 1.1 In Scope

| # | Hạng mục | Ghi chú |
|---|---|---|
| 1 | Tiếp nhận Incident Report từ user / tự động từ IMM-08/09/11 | Reuse `Incident Report` IMM-00 |
| 2 | Phân loại severity Minor / Major / Critical | Custom field `severity` |
| 3 | Workflow Incident: Draft → Open → Acknowledged → In Progress → Resolved → Closed | + nhánh `RCA Required` |
| 4 | Tạo RCA Record (5-Why / Fishbone) bắt buộc với Major/Critical/Chronic | DocType riêng IMM-12 |
| 5 | Tạo CAPA tự động từ RCA Completed | Gọi `imm00.create_capa()` |
| 6 | Đóng CAPA — validate root_cause + corrective + preventive | Gọi `imm00.close_capa()` (BR-00-08) |
| 7 | Phát hiện chronic failure (≥3 incidents cùng fault_code/90 ngày) | Scheduler daily |
| 8 | Audit trail mọi state transition | Qua `imm00.log_audit_event()` |
| 9 | Auto chuyển asset → Out of Service khi Critical | Qua `imm00.transition_asset_status()` |

### 1.2 Out of Scope

| # | Hạng mục | Lý do defer |
|---|---|---|
| 1 | Thực hiện sửa chữa (Repair WO) | Thuộc IMM-09 |
| 2 | SLA Engine (response/resolution timer) | Reuse `imm00.get_sla_policy()`; SLA breach tracking sẽ làm ở IMM-12 v2 |
| 3 | Vigilance reporting tự động lên BYT | Thuộc IMM-15 (Regulatory) |
| 4 | Risk Register integration | Thuộc IMM-13 |
| 5 | SMS notification | Sprint sau (chỉ email v1) |

---

## 2. Actors

| Role | Mô tả | Trách nhiệm chính |
|---|---|---|
| Reporting User | Điều dưỡng / KTV khoa phòng | Tạo Incident Report (Draft/Open) |
| IMM Workshop Lead | Trưởng xưởng kỹ thuật | Acknowledge incident; phân công KTV; tạo RCA; gọi service tạo CAPA |
| IMM Department Head | Trưởng phòng HTM / BGĐ kỹ thuật | Nhận escalation Critical; phê duyệt CAPA cấp cao |
| IMM QA Officer | Nhân viên QA | Submit + Close CAPA; verify Audit Trail; đảm bảo BR-00-08 |
| IMM Operations Manager | Quản lý vận hành | Xem dashboard; export báo cáo compliance |
| IMM System Admin | Quản trị viên | Cấu hình fault_code dictionary; seed data |

---

## 3. User Stories (Gherkin)

### US-12-01: Reporting User báo cáo sự cố

```gherkin
Feature: Tạo Incident Report

Scenario: Điều dưỡng báo cáo máy thở hỏng tại ICU
  Given Tôi là Điều dưỡng đăng nhập với role "Reporting User"
    And AC Asset "ACC-ASSET-2026-00012" (Máy thở Drager Evita 800) đang Active
  When Tôi mở form New Incident Report
    And Chọn asset = "ACC-ASSET-2026-00012"
    And Chọn fault_code = "VENT_ALARM_HIGH"
    And Nhập fault_description = "Máy báo alarm P_HIGH liên tục"
    And Chọn severity = "Critical"
    And Nhập clinical_impact = "Bệnh nhân phụ thuộc, đã chuẩn bị bóng ambu"
    And Submit
  Then Incident Report "IR-2026-0042" được tạo (status = Open)
    And Asset "ACC-ASSET-2026-00012".lifecycle_status = "Out of Service"
    And Một Asset Lifecycle Event "incident_reported" được tạo
    And Một IMM Audit Trail entry được ghi với SHA-256 hash
```

### US-12-02: Workshop Lead Acknowledge và phân công

```gherkin
Scenario: Workshop Lead tiếp nhận incident Critical
  Given IR-2026-0042 ở trạng thái "Open"
  When Workshop Lead click "Acknowledge"
    And Phân công assigned_to = "ktv.nguyen@hospital.vn"
  Then IR.status = "Acknowledged"
    And IR.acknowledged_at = now()
    And Một Asset Lifecycle Event "incident_acknowledged" được tạo
    And Audit trail ghi nhận
```

### US-12-03: KTV Resolve incident Major → trigger RCA

```gherkin
Scenario: KTV đánh dấu Resolved cho Major incident → auto tạo RCA
  Given IR-2026-0050 với severity = "Major", status = "In Progress"
    And Repair Work Order liên kết đã Completed
  When KTV click "Resolve" với resolution_notes
  Then IR.status = "Resolved"
    And IR.rca_required = True
    And RCA Record "RCA-2026-0007" được tạo tự động (status = "RCA Required")
    And RCA.due_date = today + 7 ngày
    And IR.status chuyển sang "RCA Required"
```

### US-12-04: QA Officer đóng CAPA

```gherkin
Scenario: QA Officer Close CAPA sau khi RCA Completed
  Given RCA-2026-0007 ở trạng thái "Completed" với root_cause đã điền
    And CAPA-2026-0023 đang ở trạng thái "Pending Verification"
  When QA Officer gọi service close_capa(
        capa_name = "CAPA-2026-0023",
        corrective_action = "Thay sensor + calibrate",
        preventive_action = "PM interval rút ngắn xuống 3 tháng",
        evidence = ["calibration_cert.pdf"]
      )
  Then CAPA.status = "Closed"
    And CAPA.closed_date = today()
    And Audit trail ghi nhận hành động
```

### US-12-05: Scheduler phát hiện chronic failure

```gherkin
Scenario: Asset có 3 incidents cùng fault_code trong 90 ngày → auto RCA
  Given Asset "ACC-ASSET-2026-00042" có:
    - IR-2026-0010 (fault_code = "PROBE_DISCONNECT", 2026-02-15)
    - IR-2026-0031 (fault_code = "PROBE_DISCONNECT", 2026-03-20)
    - IR-2026-0055 (fault_code = "PROBE_DISCONNECT", 2026-04-17)
  When Daily scheduler `detect_chronic_failures()` chạy lúc 02:00
  Then Một RCA Record được tạo với trigger_type = "Chronic Failure"
    And RCA.due_date = today + 14 ngày
    And Tất cả 3 IR được set chronic_failure_flag = True
    And Asset.chronic_failure_flag = True
    And Workshop Lead + QA Officer nhận email alert
```

### US-12-06: Block Close khi RCA chưa Completed

```gherkin
Scenario: BR-12-02 — không thể Close incident Major khi RCA chưa xong
  Given IR-2026-0050 với severity = "Major", status = "RCA Required"
    And RCA Record liên kết có status = "RCA In Progress"
  When User cố gắng chuyển IR → "Closed"
  Then Validation throw frappe.throw("Không thể đóng sự cố Major/Critical khi RCA chưa hoàn thành")
    And IR.status vẫn là "RCA Required"
```

---

## 4. Business Rules

### 4.1 Business Rules riêng IMM-12

| BR ID | Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-12-01 | Critical incident → bắt buộc `clinical_impact` không trống trước Submit | `IncidentReport.validate()` | ISO 13485:7.5 |
| BR-12-02 | Major/Critical incident → bắt buộc tạo RCA Completed trước khi Close | `IncidentReport.validate()` (status → Closed) | ISO 13485:8.5.2 |
| BR-12-03 | ≥3 incidents cùng `fault_code` trên cùng asset trong 90 ngày → auto RCA + chronic flag | Scheduler `detect_chronic_failures()` | WHO HTM §5.4 |
| BR-12-04 | Critical incident submit → auto `transition_asset_status(asset, "Out of Service")` | `services/imm12.report_incident()` | WHO HTM, NĐ98 |
| BR-12-05 | Mọi incident transition phải sinh `IMM Audit Trail` entry qua `log_audit_event()` | `services/imm12.*` | ISO 13485:7.5.9 |
| BR-12-06 | RCA Submit → bắt buộc gọi `imm00.create_capa()` (CAPA tự động link với RCA) | `services/imm12.submit_rca_and_create_capa()` | ISO 13485:8.5 |
| BR-12-07 | RCA `root_cause` không trống và `rca_method` ∈ {5Why, Fishbone, Other} trước Submit | `RCARecord.before_submit()` | ISO 13485:8.5.2 |

### 4.2 Business Rules từ IMM-00 áp dụng cho IMM-12

| BR ID | Rule | Enforce tại | Áp dụng vào IMM-12 |
|---|---|---|---|
| BR-00-08 | CAPA `before_submit` bắt buộc có `root_cause + corrective_action + preventive_action` | `IMMCAPARecord.before_submit()` | Mọi CAPA tạo từ IMM-12 phải tuân thủ |
| BR-00-09 | CAPA quá `due_date` → auto Overdue qua daily scheduler | `check_capa_overdue()` | CAPA của IMM-12 nhận escalation auto |
| BR-00-10 | Mọi thay đổi `lifecycle_status` phải sinh Asset Lifecycle Event | `transition_asset_status()` | BR-12-04 dựa vào điều này |
| BR-00-03 | IMM Audit Trail immutable (no Update/Delete) | Controller + Permission | Áp dụng cho mọi audit entry IMM-12 |

---

## 5. Permission Matrix

| Action | Reporting User | Workshop Lead | QA Officer | Department Head | Ops Manager | System Admin |
|---|---|---|---|---|---|---|
| Create Incident Report | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Read Incident Report | own dept | ✅ | ✅ | ✅ | ✅ | ✅ |
| Acknowledge Incident | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Resolve Incident | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Close Incident | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Create RCA Record | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Submit RCA | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Create CAPA (via service) | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Close CAPA | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| View Dashboard | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Export Compliance Report | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |

---

## 6. Validation Rules

| Code | Rule | Điều kiện | Thông báo (VI) | Khi nào |
|---|---|---|---|---|
| VR-12-01 | Asset tồn tại và không Decommissioned | `asset` không tồn tại hoặc `lifecycle_status = "Decommissioned"` | "Thiết bị không tồn tại hoặc đã thanh lý" | `before_insert` |
| VR-12-02 | Critical bắt buộc clinical_impact | `severity = "Critical"` AND `clinical_impact` trống | "Sự cố Critical bắt buộc mô tả tác động lâm sàng" | `validate` |
| VR-12-03 | Block Close nếu RCA chưa Completed | `status → Closed` AND `severity ∈ {Major, Critical}` AND `rca_record.status != "Completed"` | "Không thể đóng sự cố Major/Critical khi RCA chưa hoàn thành" | `validate` (BR-12-02) |
| VR-12-04 | Block Close nếu CAPA chưa Closed (đối với Critical) | `severity = "Critical"` AND `linked_capa.status != "Closed"` | "Không thể đóng sự cố Critical khi CAPA chưa được Closed bởi QA" | `validate` |
| VR-12-05 | Thứ tự timestamp hợp lệ | `acknowledged_at < resolved_at < closed_at` | "Thời gian giải quyết không thể trước thời gian tiếp nhận" | `validate` |
| VR-12-06 | RCA root_cause + rca_method bắt buộc trước Submit | `root_cause` trống OR `rca_method` không thuộc {5Why, Fishbone, Other} | "Phân tích RCA chưa đầy đủ — cần điền nguyên nhân gốc và phương pháp" | `RCARecord.before_submit` (BR-12-07) |
| VR-12-07 | CAPA fields bắt buộc trước Submit | `corrective_action` OR `preventive_action` OR `root_cause` trống | "CAPA cần đầy đủ root_cause, corrective_action, preventive_action" | `IMMCAPARecord.before_submit` (BR-00-08, IMM-00) |

---

## 7. Non-Functional Requirements

| ID | Yêu cầu | Target | Phương pháp kiểm tra |
|---|---|---|---|
| NFR-12-01 | Submit Incident Report | < 2s p95 | E2E test |
| NFR-12-02 | Chronic detection scheduler | Hoàn thành < 60s cho 10k IR | Performance test |
| NFR-12-03 | Audit trail write | Không block user request (async OK) | Load test |
| NFR-12-04 | Email notification latency | < 5 phút sau khi trigger | Integration test |
| NFR-12-05 | Dashboard load | < 3s với 1000 incidents | Performance test |
| NFR-12-06 | Mobile reporting | Form work trên mobile (responsive) | Manual test |
| NFR-12-07 | Audit trail integrity | SHA-256 chain verify pass | `verify_audit_chain()` API |

---

## 8. Acceptance Criteria

### AC-12-01: Module sẵn sàng UAT khi

- [ ] DocType `Incident Report` (IMM-00) có custom fields: `severity`, `clinical_impact`, `rca_record`, `chronic_failure_flag`, `linked_capa`
- [ ] DocType `RCA Record` + child tables tạo và migrate
- [ ] `services/imm12.py` implement: `report_incident`, `acknowledge_incident`, `resolve_incident`, `trigger_rca_if_required`, `detect_chronic_failures`, `submit_rca_and_create_capa`
- [ ] `api/imm12.py` whitelist 11+ endpoints
- [ ] Scheduler `detect_chronic_failures` cấu hình daily 02:00 trong `hooks.py`
- [ ] Email templates cho: Critical alert, Chronic detection, CAPA overdue
- [ ] Permission fixtures cho 6 roles (reuse + extend từ IMM-00)
- [ ] Test coverage `services/imm12.py` ≥ 70%
- [ ] FE routes `/imm-12/incidents`, `/imm-12/rca`, `/imm-12/dashboard` accessible

### AC-12-02: BR-12-01 → BR-12-07 và BR-00-08, BR-00-09 phải pass UAT

Reference UAT script: `IMM-12_UAT_Script.md` — TC-12-01 → TC-12-NN.

---

## 9. QMS Mapping

| Yêu cầu IMM-12 | ISO 13485:2016 | WHO HTM 2025 | NĐ 98/2021 |
|---|---|---|---|
| Incident reporting system | §8.3 Control of nonconforming product | §5.3.4 | Điều 38 |
| RCA bắt buộc Major/Critical | §8.5.2 Corrective action | §5.3.4 | Điều 38 |
| CAPA workflow + closure | §8.5.2, §8.5.3 | §5.3.4 | — |
| Chronic failure detection | §8.5.3 Preventive action | §5.4 | — |
| Audit trail immutable | §4.2.5 Control of records | §6.4 | Điều 7 |
| Asset → Out of Service khi Critical | §7.5.1 Production controls | §6.2 | Điều 36 |
| Vigilance reporting (defer IMM-15) | §8.2.3 Reporting to authorities | — | Điều 38 |
