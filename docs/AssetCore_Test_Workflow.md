# AssetCore Wave 1 — Data Seeding Matrix & Integration Test Suite

> **Scope:** IMM-04 (Installation) · IMM-05 (Registration) · IMM-08 (PM) · IMM-09 (Repair) · IMM-11 (Calibration) · IMM-12 (CAPA/Corrective)
> **Date:** 2026-04-20 · **Version:** 1.0 · **Author:** Senior BA / QA Lead

---

## PHẦN 1 — MA TRẬN DỮ LIỆU MẪU (DATA SEEDING MATRIX)

### 1.1 Master Records — Dữ liệu nền (Prerequisites)

Tất cả Asset mẫu dùng chung bộ master records sau:

#### Suppliers (AC Supplier)

| Mã | Tên | vendor_type | iso_17025_cert | iso_17025_expiry |
|----|-----|-------------|----------------|-----------------|
| SUP-001 | MedEquip Vietnam JSC | Manufacturer | — | — |
| SUP-002 | BioService Co. | Service Provider | — | — |
| SUP-003 | VietCal Lab | Calibration Lab | VILAS-234 | 2027-06-30 |

#### Departments (AC Department)

| Mã | Tên | Loại |
|----|-----|------|
| DEPT-ICU | Khoa ICU | Clinical |
| DEPT-RAD | Khoa Chẩn đoán hình ảnh | Clinical |
| DEPT-CCU | Khoa Tim mạch | Clinical |
| DEPT-OPD | Phòng khám ngoại trú | Clinical |
| DEPT-OR | Phòng mổ | Clinical |

#### Locations (AC Location)

| Mã | Tên | Dept |
|----|-----|------|
| LOC-ICU-01 | ICU Phòng 101 | DEPT-ICU |
| LOC-RAD-01 | Phòng X-quang 1 | DEPT-RAD |
| LOC-CCU-01 | CCU Phòng 201 | DEPT-CCU |
| LOC-OPD-01 | Phòng khám 05 | DEPT-OPD |
| LOC-OR-01 | Phòng mổ 3 | DEPT-OR |

#### Device Models (IMM Device Model)

| Mã Model | Tên | medical_device_class | risk_classification | is_radiation | pm_interval_days | cal_required | cal_interval_days |
|----------|-----|---------------------|--------------------|--------------|-----------------|--------------|--------------------|
| MDL-VENT-001 | Hamilton-C6 Ventilator | Class III | Critical | No | 90 | Yes | 365 |
| MDL-XRAY-001 | Shimadzu MobileArt | Class III | Critical | Yes | 180 | No | — |
| MDL-MON-001 | Philips IntelliVue MX800 | Class II | High | No | 180 | Yes | 365 |
| MDL-BP-001 | Omron HBP-9030 | Class II | Medium | No | 365 | Yes | 180 |
| MDL-SP-001 | B.Braun Perfusor Space | Class III | Critical | No | 180 | Yes | 365 |

#### Users & Roles

| Username | Họ tên | Role |
|----------|--------|------|
| eng.nam | Nguyễn Văn Nam | Biomed Engineer |
| eng.lan | Trần Thị Lan | Biomed Engineer |
| head.minh | Phạm Văn Minh | Workshop Head |
| qa.hoa | Lê Thị Hoa | QA Risk Team / Tổ HC-QLCL |
| admin.sys | CMMS Admin | CMMS Admin |
| tech.duc | Đỗ Văn Đức | HTM Technician |

---

### 1.2 Asset Seeding Matrix — 5 Bộ Dữ Liệu Mẫu

---

#### ASSET-01: Máy giúp thở Hamilton-C6 — Luồng "Happy Path"

> **Kịch bản:** Thiết bị Nhóm C đi qua đầy đủ tất cả thủ tục từ lắp đặt đến bảo trì và hiệu chuẩn thành công.

| Thuộc tính | Giá trị |
|-----------|---------|
| **asset_ref (sau mint)** | ACC-2026-00001 |
| **vendor_serial_no** | HAM-C6-SN-001234 |
| **internal_tag_qr** | QR-IMM04-26.04.00001 |
| **master_item** | MDL-VENT-001 (Hamilton-C6) |
| **vendor** | SUP-001 (MedEquip Vietnam) |
| **clinical_dept** | DEPT-ICU |
| **installation_location** | LOC-ICU-01 |
| **risk_class** | C (Critical) |
| **is_radiation_device** | No |
| **po_reference** | PO-2026-0042 |
| **reception_date** | 2026-04-01 |
| **expected_installation_date** | 2026-04-05 |
| **installation_date** | 2026-04-05 |

**IMM-04 Documents (commissioning_documents):**

| doc_type | doc_number | is_mandatory | status |
|----------|-----------|--------------|--------|
| CO | CO-2026-042 | Yes | Received |
| CQ | CQ-MED-2026-001 | Yes | Received |
| Manual | MAN-HAM-C6-EN | Yes | Received |
| Warranty | WR-2026-042-24M | Yes | Received |
| Training | TR-ICU-2026-01 | No | Received |

**IMM-05 Asset Document (sau auto-import):**

| doc_type_detail | doc_category | doc_number | expiry_date | status |
|----------------|-------------|-----------|-------------|--------|
| Chứng nhận đăng ký lưu hành | Legal | ĐKLH-HAM-C6-2024 | 2029-06-30 | Active |
| Certificate of Origin | Technical | CO-2026-042 | — | Active |
| Certificate of Quality | Certification | CQ-MED-2026-001 | — | Active |
| Manual kỹ thuật | Technical | MAN-HAM-C6-EN | — | Active |
| Phiếu bảo hành | Technical | WR-2026-042-24M | 2028-04-05 | Active |

**IMM-08 PM Work Order:**

| pm_wo_ref | pm_type | due_date | overall_result | status |
|-----------|---------|----------|---------------|--------|
| PM-WO-2026-00001 | Preventive | 2026-07-04 | Pass | Completed |

**IMM-11 Calibration:**

| cal_ref | calibration_type | scheduled_date | overall_result | status |
|---------|-----------------|---------------|---------------|--------|
| CAL-2026-00001 | External | 2027-04-05 | Passed | Passed |

**Lifecycle Events (Traceability):**

```
[2026-04-01] asset_received          → IMM04-26.04.00001
[2026-04-05] installed               → IMM04-26.04.00001
[2026-04-05] commissioned            → ACC-2026-00001 (mint từ IMM-04)
[2026-07-04] pm_completed            → PM-WO-2026-00001 / ACC-2026-00001
[2027-04-05] calibration_passed      → CAL-2026-00001 / ACC-2026-00001
```

---

#### ASSET-02: Máy X-quang di động Shimadzu — Luồng "Exception" (Block tại GW-2)

> **Kịch bản:** Thiết bị bức xạ thiếu "Chứng nhận đăng ký lưu hành" trong IMM-05 → bị block ở GW-2 của IMM-04 khi cố submit lên Clinical Release.

| Thuộc tính | Giá trị |
|-----------|---------|
| **asset_ref (dự kiến)** | ACC-2026-00002 (KHÔNG được tạo) |
| **vendor_serial_no** | SHI-MART-SN-5678 |
| **master_item** | MDL-XRAY-001 (Shimadzu MobileArt) |
| **vendor** | SUP-001 |
| **clinical_dept** | DEPT-RAD |
| **risk_class** | C (Critical) |
| **is_radiation_device** | Yes |
| **po_reference** | PO-2026-0043 |
| **commissioning_ref** | IMM04-26.04.00002 |

**Tình trạng tài liệu (commissioning_documents):**

| doc_type | status | Ghi chú |
|----------|--------|---------|
| CO | Received | OK |
| CQ | Received | OK |
| Manual | Received | OK |
| Warranty | Missing | **Block tại VR-02** |

**Tình trạng IMM-05:**

| doc_type_detail | status | Vấn đề |
|----------------|--------|--------|
| Chứng nhận đăng ký lưu hành | Draft | **Chưa được Approve → GW-2 FAIL** |
| Giấy phép thiết bị bức xạ | — | **Không tồn tại → VR-07 FAIL** |

**Kết quả mong đợi:**
- `on_submit` của IMM-04 raise `frappe.ValidationError`: _"Thiết bị chưa có Chứng nhận đăng ký lưu hành hợp lệ (IMM-05). Không thể phát hành lâm sàng."_
- Workflow state: Bị giữ ở "Initial Inspection", KHÔNG chuyển sang "Clinical Release"
- AC Asset KHÔNG được tạo (final_asset = null)

---

#### ASSET-03: Monitor theo dõi bệnh nhân Philips — Luồng "Maintenance Fail"

> **Kịch bản:** PM IMM-08 phát hiện lỗi minor → tự động tạo CM Work Order IMM-09.

| Thuộc tính | Giá trị |
|-----------|---------|
| **asset_ref** | ACC-2026-00003 |
| **vendor_serial_no** | PHI-MX800-SN-9012 |
| **master_item** | MDL-MON-001 (Philips MX800) |
| **clinical_dept** | DEPT-CCU |
| **risk_class** | B (High) |
| **commissioning_ref** | IMM04-26.04.00003 |

**IMM-08 PM Work Order (Fail scenario):**

| Field | Giá trị |
|-------|---------|
| pm_wo_ref | PM-WO-2026-00003 |
| status | Halted–Major Failure |
| overall_result | Fail |
| due_date | 2026-07-05 |

**PM Checklist Results (checklist_results):**

| description | result | notes |
|-------------|--------|-------|
| Kiểm tra nguồn điện | Pass | — |
| Kiểm tra màn hình hiển thị | Pass | — |
| Kiểm tra đầu đo SpO2 | **Fail–Major** | "Đầu đo không nhận tín hiệu, lỗi E-047" |
| Kiểm tra ECG lead | Pass | — |
| Kiểm tra alarm | Pass | — |

**IMM-09 Auto-Created Corrective WO:**

| Field | Giá trị |
|-------|---------|
| cm_wo_ref | WO-CM-2026-00003 |
| repair_type | Corrective |
| priority | Urgent |
| source_pm_wo | PM-WO-2026-00003 |
| asset_ref | ACC-2026-00003 |
| status | Open (auto-created) |
| sla_target_hours | 48 (Class II + Urgent) |

**Kết quả mong đợi:**
- PM WO → status = "Halted–Major Failure"
- Asset status → "Out of Service"
- Auto-created: WO-CM-2026-00003 (source_pm_wo = PM-WO-2026-00003)
- Lifecycle Event: `pm_major_failure` logged

---

#### ASSET-04: Máy đo huyết áp điện tử Omron — Luồng "Calibration Fail"

> **Kịch bản:** Hiệu chuẩn IMM-11 thất bại → tự động tạo CAPA Record IMM-12 (RCA required).

| Thuộc tính | Giá trị |
|-----------|---------|
| **asset_ref** | ACC-2026-00004 |
| **vendor_serial_no** | OMR-HBP-SN-3456 |
| **master_item** | MDL-BP-001 (Omron HBP-9030) |
| **clinical_dept** | DEPT-OPD |
| **risk_class** | B (Medium) |
| **commissioning_ref** | IMM04-26.04.00004 |

**IMM-11 Calibration (Fail scenario):**

| Field | Giá trị |
|-------|---------|
| cal_ref | CAL-2026-00004 |
| calibration_type | External |
| lab_supplier | SUP-003 (VietCal Lab) |
| lab_accreditation_number | VILAS-234 |
| scheduled_date | 2026-07-01 |
| actual_date | 2026-07-03 |
| status | Failed |
| overall_result | Failed |

**IMM Calibration Measurements (measurements):**

| parameter_name | unit | nominal_value | tolerance_pos | tolerance_neg | measured_value | out_of_tolerance | pass_fail |
|---------------|------|--------------|--------------|--------------|---------------|-----------------|---------|
| Systolic BP accuracy | mmHg | 120.0 | 3.0 | 3.0 | 127.5 | **Yes** | **Fail** |
| Diastolic BP accuracy | mmHg | 80.0 | 3.0 | 3.0 | 85.2 | **Yes** | **Fail** |
| Heart rate accuracy | bpm | 75.0 | 5.0 | 5.0 | 76.0 | No | Pass |

**IMM-12 Auto-Created CAPA:**

| Field | Giá trị |
|-------|---------|
| capa_ref | CAPA-2026-00004 |
| asset | ACC-2026-00004 |
| severity | Major |
| source_type | Calibration Failure |
| source_ref | CAL-2026-00004 |
| status | Open |
| lookback_required | Yes (Major severity) |

**Kết quả mong đợi:**
- overall_result = "Failed" (tự động tính từ measurements)
- Asset status → "Maintenance Hold"
- Auto-created: CAPA-2026-00004 (source_ref = CAL-2026-00004, asset = ACC-2026-00004)
- Lifecycle Event: `calibration_failed` logged
- next_calibration_date: KHÔNG được cập nhật khi Fail

---

#### ASSET-05: Bơm tiêm điện B.Braun — Luồng "Emergency" (SLA Breach)

> **Kịch bản:** Sự cố P1 xảy ra → Repair Work Order khẩn cấp IMM-09 → SLA bị vi phạm → CAPA Critical IMM-12.

| Thuộc tính | Giá trị |
|-----------|---------|
| **asset_ref** | ACC-2026-00005 |
| **vendor_serial_no** | BB-PERF-SN-7890 |
| **master_item** | MDL-SP-001 (B.Braun Perfusor) |
| **clinical_dept** | DEPT-OR |
| **risk_class** | C (Critical) |
| **commissioning_ref** | IMM04-26.04.00005 |

**Incident Report (Trigger):**

| Field | Giá trị |
|-------|---------|
| incident_ref | IR-2026-00005 |
| asset | ACC-2026-00005 |
| severity | Critical (P1) |
| description | "Bơm dừng đột ngột giữa ca mổ, alarm E-999" |
| reported_at | 2026-07-10 08:30 |

**IMM-09 Asset Repair (Emergency):**

| Field | Giá trị |
|-------|---------|
| cm_wo_ref | WO-CM-2026-00005 |
| repair_type | Emergency |
| priority | Emergency |
| incident_report | IR-2026-00005 |
| asset_ref | ACC-2026-00005 |
| risk_class | Class III |
| sla_target_hours | 4 (Class III + Emergency) |
| open_datetime | 2026-07-10 08:35 |
| completion_datetime | 2026-07-10 14:20 |
| mttr_hours | 5.75 |
| **sla_breached** | **Yes** (5.75h > 4h) |

**IMM-12 CAPA (Critical — SLA Breach):**

| Field | Giá trị |
|-------|---------|
| capa_ref | CAPA-2026-00005 |
| asset | ACC-2026-00005 |
| severity | Critical |
| source_type | Repair |
| source_ref | WO-CM-2026-00005 |
| linked_incident | IR-2026-00005 |
| status | Open |
| lookback_required | Yes |
| lookback_status | Pending |

**Kết quả mong đợi:**
- sla_breached = True (tự động tính: mttr_hours > sla_target_hours)
- CAPA severity = Critical (vì repair từ Critical P1 incident)
- lookback_required = Yes (Critical severity)
- Lifecycle events: `emergency_repair_opened`, `sla_breached`, `repair_completed`, `capa_created`

---

## PHẦN 2 — BỘ TEST CASES TOÀN DIỆN

---

### MODULE IMM-04: Asset Commissioning (Installation)

---

#### TC-IMM-04-01: Happy Path — Luồng hoàn chỉnh từ Draft đến Clinical Release

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-01 |
| **Module** | IMM-04 |
| **Loại** | Happy Path / Integration |
| **Mức độ** | Critical |
| **Actor** | Biomed Engineer (eng.nam), Workshop Head (head.minh) |
| **Kịch bản** | Tạo mới Asset Commissioning cho ASSET-01, đi qua tất cả các bước đến Clinical Release và xác nhận AC Asset được tạo. |

**Pre-conditions:**
- Tất cả master records (MDL-VENT-001, SUP-001, DEPT-ICU, LOC-ICU-01) đã tồn tại
- eng.nam đã login với role Biomed Engineer

**Các bước thực hiện:**

| Bước | Thao tác | DocType / Field |
|------|---------|-----------------|
| 1 | Tạo mới `Asset Commissioning` | New → Asset Commissioning |
| 2 | Điền: po_reference = "PO-2026-0042", master_item = MDL-VENT-001, vendor = SUP-001, clinical_dept = DEPT-ICU, expected_installation_date = 2026-04-05, vendor_serial_no = "HAM-C6-SN-001234" | Form fields |
| 3 | Thêm 4 commissioning_documents (CO, CQ, Manual, Warranty với status = "Received") | commissioning_documents table |
| 4 | Save → xác nhận naming series "IMM04-26.04.00001" được gán | Save |
| 5 | Click action "Gửi kiểm tra tài liệu" → workflow chuyển sang "Pending Doc Verify" | Workflow action button |
| 6 | Login head.minh → Click "Xác nhận đủ tài liệu" → "To Be Installed" | Workflow action |
| 7 | Click "Bắt đầu lắp đặt" → "Installing"; xác nhận installation_date được set tự động | Workflow action |
| 8 | Click "Lắp đặt hoàn thành" → "Identification"; xác nhận internal_tag_qr được generate | Workflow action |
| 9 | Click "Bắt đầu kiểm tra" → "Initial Inspection" | Workflow action |
| 10 | Thêm dữ liệu baseline_tests (5 items, tất cả Pass) | baseline_tests table |
| 11 | Click "Phê duyệt phát hành" → Submit → workflow = "Clinical Release", docstatus = 1 | Submit |
| 12 | Xác nhận final_asset field được populate với mã ACC-XXXX | Verify final_asset |
| 13 | Navigate sang AC Asset vừa tạo, xác nhận lifecycle_status = "Active" | AC Asset |

**Control Points:**

| CP | Quy định | Kiểm tra |
|----|---------|---------|
| CP-01 | NĐ 98/2021 Điều 5 — Thiết bị phải có hồ sơ lắp đặt | commissioning_documents không rỗng |
| CP-02 | ISO 9001:2015 §8.5.2 — Traceability bắt buộc | vendor_serial_no unique (VR-01) |
| CP-03 | NĐ 98/2021 — Biên bản nghiệm thu | baseline_tests 100% Pass trước Release |
| CP-04 | WHO HTM 2011.05 — Asset Registration | AC Asset được mint với đầy đủ thông tin |

**Kết quả mong đợi:**

| # | Expected |
|---|---------|
| E1 | Asset Commissioning được tạo với naming: `IMM04-26.04.00001` |
| E2 | Mỗi transition workflow thành công, lifecycle_events được append |
| E3 | internal_tag_qr được generate tại bước "Identification" |
| E4 | Sau Submit: final_asset = "ACC-2026-00001" |
| E5 | AC Asset có manufacturer_sn = "HAM-C6-SN-001234", lifecycle_status = "Active" |
| E6 | PM Schedule được tạo tự động (IMM-08 hook) |
| E7 | Calibration Schedule được tạo tự động (IMM-11 hook) |
| E8 | Asset Document draft được auto-import từ commissioning_documents |

---

#### TC-IMM-04-02: VR-01 — Unique Serial Number Validation

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-02 |
| **Module** | IMM-04 |
| **Loại** | Validation / Negative |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Đảm bảo ASSET-01 (vendor_serial_no = "HAM-C6-SN-001234") đã tồn tại |
| 2 | Tạo mới Asset Commissioning thứ hai với vendor_serial_no = "HAM-C6-SN-001234" |
| 3 | Save |

**Kết quả mong đợi:**
- `frappe.ValidationError` raised: _"Số seri 'HAM-C6-SN-001234' đã tồn tại trong hệ thống. Vui lòng kiểm tra lại."_
- Document KHÔNG được lưu

---

#### TC-IMM-04-03: VR-02 — Document Gateway G01 (Tài liệu bắt buộc chưa đủ)

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-03 |
| **Module** | IMM-04 |
| **Loại** | Validation / Negative |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Asset Commissioning với commissioning_documents: CO=Received, CQ=Missing, Manual=Received, Warranty=Missing |
| 2 | Attempt action "Gửi kiểm tra tài liệu" → "Xác nhận đủ tài liệu" |

**Kết quả mong đợi:**
- Workflow transition BITMK tại "Xác nhận đủ tài liệu": _"Các tài liệu bắt buộc chưa đủ: CQ, Warranty. Không thể chuyển sang 'To Be Installed'."_
- Trạng thái vẫn là "Pending Doc Verify"

---

#### TC-IMM-04-04: VR-03 — Baseline Test Incomplete (Fail row without note)

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-04 |
| **Module** | IMM-04 |
| **Loại** | Validation / Negative |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Đưa commissioning đến trạng thái "Initial Inspection" |
| 2 | Thêm baseline_tests row: test_result = "Fail", fail_note = "" (trống) |
| 3 | Attempt Submit |

**Kết quả mong đợi:**
- Error: _"Kết quả kiểm tra 'Fail' tại dòng X phải có ghi chú lý do. (VR-03a)"_

---

#### TC-IMM-04-05: VR-03b — Không thể Release nếu có Fail trong baseline

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-05 |
| **Module** | IMM-04 |
| **Loại** | Validation / Negative |
| **Mức độ** | Critical |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Đưa đến "Initial Inspection" với baseline có 1 row = Fail (có fail_note) |
| 2 | Attempt action "Phê duyệt phát hành" → Submit |

**Kết quả mong đợi:**
- Error: _"Không thể phát hành lâm sàng khi còn kết quả kiểm tra 'Fail'. Vui lòng xử lý NC trước. (VR-03b)"_

---

#### TC-IMM-04-06: GW-2 — IMM-05 Compliance Gate (ASSET-02 scenario)

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-06 |
| **Module** | IMM-04 · IMM-05 |
| **Loại** | Integration / Negative |
| **Mức độ** | Critical |
| **Kịch bản** | ASSET-02 X-quang, thiếu "Chứng nhận đăng ký lưu hành" ở trạng thái Active |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Asset Commissioning cho MDL-XRAY-001 (Radiation device) |
| 2 | Hoàn tất tất cả bước đến "Initial Inspection" |
| 3 | Asset Document (IMM-05) cho "ĐKLH" vẫn ở trạng thái "Draft" (chưa Approve) |
| 4 | Attempt Submit / "Phê duyệt phát hành" |

**Control Points:**
- CP: NĐ 98/2021 Điều 7 — Thiết bị phải có ĐKLH hợp lệ trước khi đưa vào sử dụng

**Kết quả mong đợi:**
- Error: _"Thiết bị chưa có Chứng nhận đăng ký lưu hành hợp lệ (IMM-05). Không thể phát hành lâm sàng. (GW-2)"_
- final_asset = null
- AC Asset KHÔNG được tạo

---

#### TC-IMM-04-07: VR-07 — Radiation Device without QA License

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-07 |
| **Module** | IMM-04 |
| **Loại** | Validation / Negative |
| **Mức độ** | Critical |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Commissioning cho MDL-XRAY-001 (is_radiation_device=Yes) |
| 2 | Không upload qa_license_doc |
| 3 | Đưa đến bước "Initial Inspection" → Attempt Submit |

**Kết quả mong đợi:**
- Error: _"Thiết bị bức xạ phải có Giấy phép thiết bị bức xạ từ Cục ATBXHN. (VR-07)"_

---

#### TC-IMM-04-08: Non-Conformance Flow — NC tạo và đóng

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-08 |
| **Module** | IMM-04 |
| **Loại** | Business Flow |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Từ "Initial Inspection", click nút "Báo cáo lỗi baseline" → "Re Inspection" |
| 2 | Từ "Re Inspection", click "Tạo NC" → create Asset QA Non Conformance |
| 3 | NC record được tạo, ref_commissioning = current commissioning |
| 4 | Attempt Submit khi NC vẫn Open → Error (VR-04) |
| 5 | Đóng NC (resolution_status = Closed) |
| 6 | Submit lại → Thành công |

**Kết quả mong đợi:**
- Khi NC Open: Error _"Còn Non-Conformance chưa xử lý. Không thể phát hành. (VR-04)"_
- Sau khi NC Closed: Submit thành công

---

#### TC-IMM-04-09: VR-Backdate — Installation date trước Reception date

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-09 |
| **Module** | IMM-04 |
| **Loại** | Validation / Negative |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Commissioning với reception_date = 2026-04-05 |
| 2 | Set installation_date = 2026-04-04 (trước reception_date) |
| 3 | Save |

**Kết quả mong đợi:**
- Error: _"Ngày lắp đặt không thể trước ngày nhận thiết bị. (VR-Backdate)"_

---

#### TC-IMM-04-10: Permission — HTM Technician không Submit được

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-04-10 |
| **Module** | IMM-04 |
| **Loại** | Permission |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Login tech.duc (HTM Technician) |
| 2 | Attempt Submit một Asset Commissioning ở trạng thái "Initial Inspection" |

**Kết quả mong đợi:**
- Permission denied: _"Bạn không có quyền Submit tài liệu này."_

---

### MODULE IMM-05: Asset Document (Registration)

---

#### TC-IMM-05-01: Happy Path — Tạo và Approve Asset Document

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-05-01 |
| **Module** | IMM-05 |
| **Loại** | Happy Path |
| **Mức độ** | Critical |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo mới `Asset Document` với asset_ref = ACC-2026-00001 |
| 2 | Điền: doc_category = "Legal", doc_type_detail = "Chứng nhận đăng ký lưu hành", doc_number = "ĐKLH-HAM-C6-2024", version = "1.0", issued_date = 2024-07-01, expiry_date = 2029-06-30, file_attachment = upload file |
| 3 | Save → naming DOC-ACC-2026-00001-2026-00001 |
| 4 | Click "Gửi duyệt" → "Pending Review" |
| 5 | Login qa.hoa → Click "Phê duyệt" → "Active" |
| 6 | Xác nhận approved_by = qa.hoa, approval_date = today |

**Control Points:**

| CP | Quy định |
|----|---------|
| CP-01 | NĐ 98/2021 — ĐKLH bắt buộc cho tất cả trang thiết bị y tế loại B, C, D |
| CP-02 | ISO 9001:2015 §7.5 — Document control |

**Kết quả mong đợi:**
- Status = "Active", docstatus = 1
- approved_by, approval_date được populate
- is_expired = False (expiry 2029, current 2026)
- days_until_expiry được tính đúng

---

#### TC-IMM-05-02: Auto-Import từ IMM-04 Clinical Release

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-05-02 |
| **Module** | IMM-04 · IMM-05 |
| **Loại** | Integration / Auto-Import |
| **Mức độ** | Critical |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Hoàn tất ASSET-01 đến Clinical Release (TC-IMM-04-01) |
| 2 | Navigate sang Asset Document list, filter by asset_ref = ACC-2026-00001 |
| 3 | Xác nhận số lượng docs = số commissioning_documents có status="Received" |
| 4 | Xác nhận source_commissioning = IMM04-26.04.00001 |
| 5 | Xác nhận source_module = "IMM-04" |

**Kết quả mong đợi:**
- 4 Asset Documents được auto-tạo (CO, CQ, Manual, Warranty) ở trạng thái "Draft"
- Mỗi doc có source_commissioning = "IMM04-26.04.00001"
- Các doc cần được Approve thủ công (workflow: Draft → Pending Review → Active)

---

#### TC-IMM-05-03: Document Expiry Alert

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-05-03 |
| **Module** | IMM-05 |
| **Loại** | Alert / Scheduler |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Asset Document với expiry_date = today + 25 days (trong vùng "Critical" 30 ngày) |
| 2 | Chạy scheduler job expiry alert |
| 3 | Kiểm tra notification |

**Kết quả mong đợi:**
- days_until_expiry = 25
- Alert level = "Critical" (< 30 days)
- Notification gửi đến responsible user

---

#### TC-IMM-05-04: Version Control — Supersede Document

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-05-04 |
| **Module** | IMM-05 |
| **Loại** | Business Flow |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Có Asset Document v1.0 ở trạng thái "Active" |
| 2 | Tạo mới Asset Document với version = "2.0", change_summary = "Gia hạn ĐKLH" |
| 3 | Approve version 2.0 |
| 4 | Archive version 1.0, set superseded_by = version 2.0 |

**Kết quả mong đợi:**
- Version 1.0: status = "Archived", superseded_by = new doc ID
- Version 2.0: status = "Active"
- change_summary required khi version != "1.0" (VR-09)

---

#### TC-IMM-05-05: Visibility Control — Internal Document

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-05-05 |
| **Module** | IMM-05 |
| **Loại** | Permission / Access Control |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Asset Document với visibility = "Internal_Only" |
| 2 | Login user có role "Clinical Head" (read-only external) |
| 3 | Attempt to view document |

**Kết quả mong đợi:**
- Document không hiển thị trong list view cho Clinical Head
- Direct URL access: Permission denied

---

#### TC-IMM-05-06: Exempt Document — Bypass GW-2

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-05-06 |
| **Module** | IMM-05 · IMM-04 |
| **Loại** | Exception / Business Rule |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Asset Document với is_exempt = True, exempt_reason = "Thiết bị nhập khẩu cấp cứu", upload exempt_proof |
| 2 | Approve document (status = Active) |
| 3 | Submit IMM-04 cho cùng asset khi không có ĐKLH (nhưng có exempt doc) |

**Kết quả mong đợi:**
- GW-2 bypass (BR-08: exempt documents bypass compliance checks)
- Submit IMM-04 thành công dù không có ĐKLH thông thường

---

### MODULE IMM-08: PM Work Order (Preventive Maintenance)

---

#### TC-IMM-08-01: Happy Path — PM Hoàn tất (Pass)

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-08-01 |
| **Module** | IMM-08 |
| **Loại** | Happy Path |
| **Mức độ** | Critical |
| **Kịch bản** | PM cho ASSET-01 (Ventilator) đi qua đầy đủ và Pass |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Từ PM Schedule của ACC-2026-00001, scheduler tạo PM-WO-2026-00001 (do_date = 2026-07-04) |
| 2 | Login eng.nam, mở PM Work Order PM-WO-2026-00001 |
| 3 | Update status = "In Progress" |
| 4 | Điền tất cả checklist_results (5 items, tất cả Pass) |
| 5 | Điền: technician_notes, duration_minutes = 90, pm_sticker_attached = True |
| 6 | Upload attachments (photos) |
| 7 | Submit |

**Control Points:**

| CP | Quy định |
|----|---------|
| CP-01 | ISO 9001:2015 §8.5.1 — Preventive maintenance records |
| CP-02 | NĐ 98/2021 — Lịch bảo trì thiết bị y tế |

**Kết quả mong đợi:**
- status = "Completed", overall_result = "Pass"
- completion_date = today
- PM Schedule: last_pm_date = today, next_due_date = today + pm_interval_days
- AC Asset: last_pm_date = today, next_pm_date được cập nhật
- PM Task Log được tạo (immutable)
- Lifecycle Event: `pm_completed` logged
- Không tạo Corrective WO

---

#### TC-IMM-08-02: PM Fail-Minor → Auto-Create Corrective WO

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-08-02 |
| **Module** | IMM-08 · IMM-09 |
| **Loại** | Integration / Failure Flow |
| **Mức độ** | Critical |
| **Kịch bản** | ASSET-03 (Monitor) PM có Fail-Minor → auto-create CM WO |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Mở PM-WO-2026-00003 (ACC-2026-00003) |
| 2 | Điền checklist: "Kiểm tra đầu đo SpO2" = "Fail–Minor", notes = "Đầu đo chập chờn" |
| 3 | overall_result = "Pass with Minor Issues" |
| 4 | Submit |

**Kết quả mong đợi:**
- PM WO status = "Completed"
- Auto-created: Asset Repair WO với repair_type = "Corrective", source_pm_wo = PM-WO-2026-00003
- New CM WO status = "Open"
- Lifecycle Event: `pm_completed_with_minor_issue` logged

---

#### TC-IMM-08-03: PM Fail-Major → Halt + Asset Out of Service

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-08-03 |
| **Module** | IMM-08 · IMM-09 |
| **Loại** | Integration / Major Failure |
| **Mức độ** | Critical |
| **Kịch bản** | ASSET-03 PM có Fail-Major → Halt WO + Asset Out of Service |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Mở PM-WO-2026-00003 |
| 2 | Set checklist: "Kiểm tra đầu đo SpO2" = "Fail–Major", notes = "Lỗi E-047, không thể phục hồi" |
| 3 | Set overall_result = "Fail" |
| 4 | Submit |

**Kết quả mong đợi:**
- PM WO status = "Halted–Major Failure"
- Asset ACC-2026-00003: lifecycle_status = "Out of Service"
- Auto-created: Asset Repair WO (repair_type = Corrective, priority = Urgent)
- Lifecycle Event: `pm_major_failure` + `asset_out_of_service` logged

---

#### TC-IMM-08-04: BR-08-06 — High-Risk Device cần Photo

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-08-04 |
| **Module** | IMM-08 |
| **Loại** | Validation / Business Rule |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | PM Work Order cho ACC-2026-00001 (risk_class = Critical) |
| 2 | Điền tất cả checklist nhưng KHÔNG upload attachments (photos) |
| 3 | Attempt Submit |

**Kết quả mong đợi:**
- Error: _"Thiết bị rủi ro cao/critical bắt buộc phải đính kèm ảnh kiểm tra. (BR-08-06)"_

---

#### TC-IMM-08-05: BR-08-08 — Checklist Incomplete

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-08-05 |
| **Module** | IMM-08 |
| **Loại** | Validation |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | PM Work Order với 5 checklist items |
| 2 | Chỉ điền 4/5 items (bỏ result cho item 5) |
| 3 | Attempt Submit |

**Kết quả mong đợi:**
- Error: _"Tất cả hạng mục kiểm tra phải có kết quả trước khi hoàn tất. Còn 1 hạng mục chưa điền. (BR-08-08)"_

---

#### TC-IMM-08-06: Overdue PM — SLA và is_late Flag

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-08-06 |
| **Module** | IMM-08 |
| **Loại** | SLA / Scheduler |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | PM Work Order với due_date = 2026-04-10 (đã qua) |
| 2 | Scheduler chạy hàng ngày |
| 3 | Kiểm tra PM WO |

**Kết quả mong đợi:**
- status = "Overdue"
- is_late = True
- Notification gửi đến assigned_to và Workshop Head

---

### MODULE IMM-09: Asset Repair (Corrective Maintenance)

---

#### TC-IMM-09-01: Happy Path — Repair Hoàn tất

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-09-01 |
| **Module** | IMM-09 |
| **Loại** | Happy Path |
| **Mức độ** | Critical |
| **Kịch bản** | CM WO auto-created từ PM fail (ASSET-03) được hoàn tất thành công |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Mở Asset Repair WO-CM-2026-00003 (từ TC-IMM-08-02) |
| 2 | Assign to eng.nam, update status = "Assigned" |
| 3 | Update status = "Diagnosing", điền diagnosis_notes, root_cause_category = "Electrical" |
| 4 | Update status = "In Repair" |
| 5 | Thêm spare_parts_used (1 item: SpO2 sensor replacement) |
| 6 | Điền repair_checklist (tất cả Pass) |
| 7 | Update status = "Pending Inspection" |
| 8 | Submit |

**Control Points:**

| CP | Quy định |
|----|---------|
| CP-01 | WHO HTM — MTTR tracking bắt buộc |
| CP-02 | ISO 9001:2015 §8.5.3 — Property belonging to customers |

**Kết quả mong đợi:**
- status = "Completed"
- completion_datetime = auto-set
- mttr_hours = (completion_datetime - open_datetime) trong giờ
- Asset lifecycle_status trở lại "Active"
- Lifecycle Event: `repair_completed` logged
- Post-repair Calibration WO auto-created (nếu calibration_required)

---

#### TC-IMM-09-02: BR-09-01 — Repair Source Validation

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-09-02 |
| **Module** | IMM-09 |
| **Loại** | Validation / Negative |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Asset Repair mới mà KHÔNG set incident_report VÀ KHÔNG set source_pm_wo |
| 2 | Save |

**Kết quả mong đợi:**
- Error: _"Lệnh sửa chữa phải có nguồn gốc: Báo cáo sự cố (Incident Report) hoặc PM Work Order. (BR-09-01)"_

---

#### TC-IMM-09-03: SLA Matrix — Class III + Emergency = 4h

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-09-03 |
| **Module** | IMM-09 |
| **Loại** | SLA / Business Rule |
| **Mức độ** | Critical |
| **Kịch bản** | ASSET-05 Emergency repair, test SLA 4h |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Asset Repair cho ACC-2026-00005 (Class III), repair_type = "Emergency", priority = "Emergency" |
| 2 | Save → kiểm tra sla_target_hours |
| 3 | Hoàn thành repair sau 5.75h |
| 4 | Submit |

**Kết quả mong đợi:**
- sla_target_hours = 4 (Class III + Emergency)
- mttr_hours = 5.75
- sla_breached = True
- CAPA auto-created với severity = Critical

---

#### TC-IMM-09-04: SLA Matrix — 8 Combinations (Negative Test)

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-09-04 |
| **Module** | IMM-09 |
| **Loại** | SLA Parametric |
| **Mức độ** | Medium |

**Bảng kiểm tra SLA Matrix:**

| risk_class | priority | sla_target (expected) | Test |
|-----------|---------|----------------------|------|
| Class III | Emergency | 4h | TC-IMM-09-04-A |
| Class III | Urgent | 24h | TC-IMM-09-04-B |
| Class III | Normal | 120h | TC-IMM-09-04-C |
| Class II | Emergency | 8h | TC-IMM-09-04-D |
| Class II | Urgent | 48h | TC-IMM-09-04-E |
| Class II | Normal | 72h | TC-IMM-09-04-F |
| Class I | Emergency | 24h | TC-IMM-09-04-G |
| Class I | Normal | 480h | TC-IMM-09-04-H |

**Kết quả mong đợi:** Mỗi combination tạo đúng sla_target_hours theo bảng trên.

---

#### TC-IMM-09-05: Repeat Failure Detection (30-day Lookback)

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-09-05 |
| **Module** | IMM-09 |
| **Loại** | Business Rule |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Đảm bảo ACC-2026-00003 đã có Repair Completed trong 30 ngày qua |
| 2 | Tạo Repair mới cho cùng asset |
| 3 | Save |

**Kết quả mong đợi:**
- is_repeat_failure = True (auto-set)
- Warning notification: _"Thiết bị này đã được sửa chữa trong vòng 30 ngày. Đây là lỗi lặp lại."_

---

#### TC-IMM-09-06: Không tạo 2 Repair Active cùng lúc

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-09-06 |
| **Module** | IMM-09 |
| **Loại** | Validation / Concurrency |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Asset ACC-2026-00003 đang có Repair WO ở trạng thái "In Repair" |
| 2 | Attempt tạo Repair mới cho cùng asset |
| 3 | Save |

**Kết quả mong đợi:**
- Error: _"Thiết bị này đang có lệnh sửa chữa đang xử lý (WO-CM-XXXX). Không thể tạo mới."_

---

#### TC-IMM-09-07: Post-Repair Calibration Auto-Trigger

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-09-07 |
| **Module** | IMM-09 · IMM-11 |
| **Loại** | Integration |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Hoàn tất Repair cho ACC-2026-00004 (BP Monitor, calibration_required = Yes) |
| 2 | Submit Repair |
| 3 | Kiểm tra IMM Asset Calibration list |

**Kết quả mong đợi:**
- Calibration WO mới được tạo: calibration_type = default từ device model, is_recalibration = True
- Linking: calibration_schedule trỏ đúng, asset = ACC-2026-00004

---

### MODULE IMM-11: Asset Calibration

---

#### TC-IMM-11-01: Happy Path — External Calibration Pass

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-11-01 |
| **Module** | IMM-11 |
| **Loại** | Happy Path |
| **Mức độ** | Critical |
| **Kịch bản** | ASSET-01 Ventilator, External calibration tại VietCal Lab, Pass |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Từ Calibration Schedule, scheduler tạo CAL-2026-00001 (scheduled_date = 2027-04-05) |
| 2 | Set lab_supplier = SUP-003 (VietCal Lab), lab_accreditation_number = "VILAS-234" |
| 3 | Set status = "Sent to Lab", sent_date = 2027-04-01 |
| 4 | Nhận certificate: upload certificate_file, set certificate_number = "VILAS-234-2027-001", certificate_date = 2027-04-03 |
| 5 | Điền measurements (3 params, tất cả Pass) |
| 6 | Submit |

**Control Points:**

| CP | Quy định |
|----|---------|
| CP-01 | NĐ 98/2021 — Thiết bị đo lường phải hiệu chuẩn định kỳ |
| CP-02 | ISO/IEC 17025 — Phòng thí nghiệm hiệu chuẩn phải có chứng nhận |
| CP-03 | ISO 13485:2016 §7.6 — Control of monitoring and measuring equipment |

**Kết quả mong đợi:**
- overall_result = "Passed" (auto-computed từ measurements)
- next_calibration_date = actual_date + calibration_interval_days (365)
- Calibration Schedule: last_calibration_date updated, next_due_date updated
- calibration_sticker_attached = True (reminder)
- Lifecycle Event: `calibration_passed` logged

---

#### TC-IMM-11-02: Calibration Fail → Auto CAPA (ASSET-04 scenario)

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-11-02 |
| **Module** | IMM-11 · IMM-12 |
| **Loại** | Integration / Failure |
| **Mức độ** | Critical |
| **Kịch bản** | ASSET-04 BP Monitor, measurements out of tolerance → Failed → CAPA |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Mở Calibration CAL-2026-00004 cho ACC-2026-00004 |
| 2 | Điền measurements: Systolic = 127.5 (nominal=120, tol±3 → out of tolerance) |
| 3 | Submit |

**Kết quả mong đợi:**
- out_of_tolerance = True cho measurements vượt tolerance
- pass_fail = "Fail" auto-set
- overall_result = "Failed"
- Asset ACC-2026-00004: lifecycle_status = "Maintenance Hold"
- CAPA-2026-00004 auto-created: source_type = "Calibration Failure", source_ref = "CAL-2026-00004", asset = "ACC-2026-00004"
- Lifecycle Event: `calibration_failed` + `asset_maintenance_hold` logged
- next_calibration_date: KHÔNG được cập nhật

---

#### TC-IMM-11-03: VR-11-01 — Lab ISO 17025 Expired

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-11-03 |
| **Module** | IMM-11 |
| **Loại** | Validation / Negative |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Supplier với iso_17025_expiry = 2025-12-31 (đã hết hạn) |
| 2 | Tạo Calibration với lab_supplier = expired lab |
| 3 | Submit |

**Kết quả mong đợi:**
- Error: _"Phòng thí nghiệm VietCal Lab đã hết hạn chứng nhận ISO/IEC 17025 (2025-12-31). Không thể sử dụng. (VR-11-02)"_

---

#### TC-IMM-11-04: CAL-004 — Measurements Incomplete

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-11-04 |
| **Module** | IMM-11 |
| **Loại** | Validation / Negative |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Calibration với 3 measurement params |
| 2 | Chỉ điền measured_value cho 2/3 params |
| 3 | Attempt Submit |

**Kết quả mong đợi:**
- Error: _"Tất cả tham số đo phải có giá trị đo thực tế trước khi Submit. Còn 1 tham số chưa điền. (CAL-004)"_

---

#### TC-IMM-11-05: VR-11-03/04 — Certificate Required for External

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-11-05 |
| **Module** | IMM-11 |
| **Loại** | Validation |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | External Calibration, set status = "Certificate Received" |
| 2 | Không upload certificate_file VÀ không set lab_accreditation_number |
| 3 | Validate / Submit |

**Kết quả mong đợi:**
- Error (VR-11-03): _"Hiệu chuẩn bên ngoài yêu cầu đính kèm giấy chứng nhận. (VR-11-03)"_
- Error (VR-11-04): _"Phải nhập số hiệu chứng nhận ISO/IEC 17025 của phòng thí nghiệm. (VR-11-04)"_

---

#### TC-IMM-11-06: Cannot Cancel Submitted Calibration

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-11-06 |
| **Module** | IMM-11 |
| **Loại** | Business Rule / Immutability |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Submit một Calibration WO |
| 2 | Attempt Cancel |

**Kết quả mong đợi:**
- Error: _"Không thể hủy Hiệu chuẩn đã Submit. Vui lòng dùng Amend để tạo bản chỉnh sửa. (BR-11-05)"_

---

#### TC-IMM-11-07: Conditionally Passed — Phân tích kết quả hỗn hợp

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-11-07 |
| **Module** | IMM-11 |
| **Loại** | Business Rule |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Điền measurements: 2 params Pass, 1 param Fail nhưng non-critical |
| 2 | Submit |

**Kết quả mong đợi:**
- overall_result = "Conditionally Passed"
- Asset vẫn Active (không Maintenance Hold)
- Ghi chú cảnh báo được tạo

---

### MODULE IMM-12: CAPA / Corrective Actions

---

#### TC-IMM-12-01: CAPA từ Calibration Fail — Traceability Kiểm tra

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-12-01 |
| **Module** | IMM-12 · IMM-11 |
| **Loại** | Integration / Traceability |
| **Mức độ** | Critical |
| **Kịch bản** | CAPA-2026-00004 được tạo từ CAL-2026-00004, xác nhận data traceability |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | CAPA-2026-00004 đã được auto-created (từ TC-IMM-11-02) |
| 2 | Mở CAPA Record |
| 3 | Xác nhận: source_type = "Calibration Failure", source_ref = "CAL-2026-00004", asset = "ACC-2026-00004" |
| 4 | Điền: root_cause = "Hao mòn cảm biến áp lực sau 2 năm sử dụng", corrective_action = "Thay thế cảm biến áp lực mới" |
| 5 | Update status = "In Progress" |
| 6 | Điền verification_notes, effectiveness_check |
| 7 | Update status = "Pending Verification" → "Closed" |

**Control Points:**

| CP | Quy định |
|----|---------|
| CP-01 | ISO 13485:2016 §8.5.2 — CAPA mandatory cho nonconformity |
| CP-02 | NĐ 98/2021 — Corrective action records |

**Kết quả mong đợi:**
- CAPA asset = "ACC-2026-00004" (trỏ đúng về máy đo huyết áp)
- source_ref = "CAL-2026-00004" (trỏ đúng về calibration fail)
- Sau close: IMM Asset Calibration CAL-2026-00004.capa_record = "CAPA-2026-00004"
- closed_date auto-populated

---

#### TC-IMM-12-02: Emergency SLA Breach → Critical CAPA (ASSET-05 scenario)

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-12-02 |
| **Module** | IMM-12 · IMM-09 |
| **Loại** | Integration / SLA Breach |
| **Mức độ** | Critical |
| **Kịch bản** | Bơm tiêm điện SLA breach → CAPA Critical với lookback |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | WO-CM-2026-00005 completed với mttr_hours = 5.75 > sla_target = 4h |
| 2 | Submit Asset Repair → sla_breached = True |
| 3 | CAPA-2026-00005 auto-created |
| 4 | Xác nhận severity = "Critical", lookback_required = True |
| 5 | Điền lookback_assets (kiểm tra các Syringe Pump khác trong bệnh viện) |
| 6 | Complete lookback_status = "Complete" |
| 7 | Close CAPA sau verification |

**Kết quả mong đợi:**
- severity = "Critical"
- linked_incident = IR-2026-00005
- lookback_required = True, lookback_assets có dữ liệu
- CAPA closed sau verification

---

#### TC-IMM-12-03: Incident Report → CAPA Escalation

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-12-03 |
| **Module** | IMM-12 |
| **Loại** | Business Flow |
| **Mức độ** | High |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | Tạo Incident Report cho ACC-2026-00005, severity = "Critical" |
| 2 | Submit Incident |
| 3 | Acknowledge → "Under Investigation" |
| 4 | Resolve → "Resolved" |
| 5 | Close → "Closed" |

**Kết quả mong đợi:**
- Mỗi state transition auto-log audit event via imm00
- Khi severity = Critical: CAPA được escalate (linked_incident trỏ về Incident)
- closed state là terminal (không thể reopen)

---

#### TC-IMM-12-04: CAPA Overdue

| Trường | Nội dung |
|--------|---------|
| **ID** | TC-IMM-12-04 |
| **Module** | IMM-12 |
| **Loại** | SLA / Scheduler |
| **Mức độ** | Medium |

**Các bước:**

| Bước | Thao tác |
|------|---------|
| 1 | CAPA với due_date = 2026-04-10 (đã qua) và status = "In Progress" |
| 2 | Scheduler chạy |

**Kết quả mong đợi:**
- status = "Overdue"
- Notification gửi đến responsible user và Workshop Head

---

## PHẦN 3 — WORKFLOW DESCRIPTION

### 3.1 Dependency Chain — Module Calling Matrix

```
PO / Contract
      │
      ▼
[IMM-04] Asset Commissioning
      │
      ├─── GW-1 (Gate 1): Tài liệu đủ? ────► Block nếu thiếu tài liệu bắt buộc (VR-02)
      │
      ├─── GW-2 (Gate 2): ĐKLH hợp lệ? ────► Block nếu IMM-05 chưa có Active ĐKLH
      │
      └─── Clinical Release
               │
               ├─── Auto-mint: AC Asset (final_asset)
               │         │
               │         ├──► [IMM-05] Asset Document (auto-import + approve)
               │         │
               │         ├──► [IMM-08] PM Schedule (hook on_submit)
               │         │         │
               │         │         └──► PM Work Order (scheduler daily)
               │         │                   │
               │         │                   ├─── Pass ──────────────────────────────► PM Log
               │         │                   │
               │         │                   ├─── Fail-Minor ──────────────────────► [IMM-09] Corrective WO
               │         │                   │
               │         │                   └─── Fail-Major ──► Asset Out of Service ► [IMM-09] Corrective WO
               │         │
               │         └──► [IMM-11] Calibration Schedule (hook on_submit, if cal_required)
               │                   │
               │                   └──► Calibration WO (scheduler daily)
               │                             │
               │                             ├─── Passed ─────────────────────────► Update next_cal_date
               │                             │
               │                             └─── Failed ──► Asset Maintenance Hold ► [IMM-12] CAPA

[IMM-09] Asset Repair ──────────────────────────────────────────────────────────────────────────┐
      │                                                                                          │
      ├─── Source: Incident Report (IR)                                                          │
      ├─── Source: PM Work Order (source_pm_wo)                                                  │
      │                                                                                          │
      ├─── On Submit: MTTR calculated                                                            │
      ├─── SLA Check: mttr > sla_target? ──► sla_breached = True ──► [IMM-12] Critical CAPA     │
      │                                                                                          │
      └─── Post-repair: create_post_repair_calibration (IMM-11 hook) ──────────────────────────┘

[IMM-12] CAPA / Incident ◄────────────────────────────────────────────────────────────────────────
      Sources:
      - Calibration Failure (from IMM-11 handle_calibration_fail)
      - Major Repair (from IMM-09 complete_repair, SLA breach)
      - PM Major Failure (from IMM-08 _handle_failures)
      - Non-Conformance (from IMM-04 NC escalation)
      - Direct Incident Report
```

---

### 3.2 Decision Matrix — Các Điểm Quyết Định

#### GW-1: Tài liệu bắt buộc (IMM-04 — Gate G01)

| Điều kiện | Tài liệu | Quyết định |
|----------|---------|-----------|
| Tất cả is_mandatory=True docs có status="Received" hoặc "Waived" | CO, CQ, Manual, Warranty | **PASS → To Be Installed** |
| Có bất kỳ is_mandatory=True doc nào status="Missing" hoặc "Pending" | Bất kỳ | **FAIL → Giữ tại Pending Doc Verify** |

#### GW-2: ĐKLH Compliance (IMM-04 — Clinical Release Gate)

| Điều kiện | Logic | Quyết định |
|----------|-------|-----------|
| Có ít nhất 1 Asset Document (IMM-05) với doc_type_detail="Chứng nhận ĐKLH" VÀ status="Active" | `frappe.db.exists(...)` | **PASS → Clinical Release** |
| Không có Active ĐKLH document | — | **FAIL → Block Submit** |
| is_exempt=True trên một Asset Document có file | BR-08 | **BYPASS → Clinical Release** |

#### Failure Severity → Response Matrix (IMM-08/09/11)

| Module | Failure Level | Asset Status | Auto-Action |
|--------|-------------|-------------|------------|
| IMM-08 PM | Fail-Minor | Active | Create CM WO (Corrective, Urgent) |
| IMM-08 PM | Fail-Major | Out of Service | Create CM WO (Corrective, Urgent) |
| IMM-09 Repair | SLA Breach (Emergency) | Out of Service | Create CAPA (Critical) |
| IMM-09 Repair | Repeat Failure (30d) | Under Review | Flag is_repeat_failure |
| IMM-11 Cal | Failed | Maintenance Hold | Create CAPA (Major) |
| IMM-11 Cal | Conditionally Passed | Active | Warning only |
| IMM-12 CAPA | Critical severity | Maintenance Hold | Lookback check all similar assets |

#### SLA Decision Matrix (IMM-09)

| Risk Class | Priority | SLA Target | Breach → Severity |
|-----------|---------|-----------|-----------------|
| Class III | Emergency | **4h** | Critical CAPA |
| Class III | Urgent | 24h | Major CAPA |
| Class III | Normal | 120h | Minor CAPA |
| Class II | Emergency | **8h** | Critical CAPA |
| Class II | Urgent | 48h | Major CAPA |
| Class II | Normal | 72h | Minor CAPA |
| Class I | Emergency | 24h | Major CAPA |
| Class I | Urgent | 72h | Minor CAPA |
| Class I | Normal | 480h | No auto-CAPA |

---

### 3.3 Data Traceability — Inheritance Map

#### Luồng dữ liệu từ PO → Asset → Work Order

```
PO / Contract
    │
    ├── po_reference ──────────────────────────────► Asset Commissioning.po_reference
    │                                                        │
    │   Device Model (IMM Device Model)                      │
    │       ├── medical_device_class ─────────────────────► .risk_class
    │       ├── is_radiation_device ──────────────────────► .is_radiation_device
    │       ├── pm_interval_days ────────────────────────► PM Schedule.interval_days (via hook)
    │       └── calibration_interval_days ──────────────► IMM Calibration Schedule.interval_days
    │
    └── [on Clinical Release] Asset Commissioning.final_asset = AC Asset
                                                        │
                                          AC Asset (master record)
                                              │
                                              ├── asset_ref ──────────────► PM Work Order.asset_ref
                                              │                          ► Asset Repair.asset_ref
                                              │                          ► IMM Asset Calibration.asset
                                              │                          ► Asset Document.asset_ref
                                              │                          ► IMM CAPA Record.asset
                                              │
                                              ├── manufacturer_sn ────────► (inherited from commissioning)
                                              ├── device_model ────────────► (inherited from commissioning)
                                              └── lifecycle_status ─────────► Updated by each module
```

#### Traceability Chain cho từng Asset mẫu

**ASSET-01 (Happy Path):**
```
IMM04-26.04.00001 ──► ACC-2026-00001 ──► PM-WO-2026-00001 ──► PM Task Log
                   └─► CAL-2026-00001 ──► Calibration Passed ──► next_cal_date updated
                   └─► DOC-ACC-2026-00001-2026-000xx (5 docs, IMM-05)
```

**ASSET-02 (Exception):**
```
IMM04-26.04.00002 ──► [BLOCKED at GW-2] ──► AC Asset NOT created
                                         └─► Asset Document.status = "Draft" (ĐKLH not Active)
```

**ASSET-03 (Maintenance Fail):**
```
IMM04-26.04.00003 ──► ACC-2026-00003 ──► PM-WO-2026-00003 [Fail-Major]
                                                 │
                                                 └──► WO-CM-2026-00003 (source_pm_wo = PM-WO-2026-00003)
                                                                │
                                                                └──► lifecycle_event: pm_major_failure
```

**ASSET-04 (Calibration Fail):**
```
IMM04-26.04.00004 ──► ACC-2026-00004 ──► CAL-2026-00004 [Failed]
                                                 │
                                                 ├──► CAPA-2026-00004 (source_ref = CAL-2026-00004)
                                                 │                    (asset = ACC-2026-00004) ✓ Traceability OK
                                                 └──► Asset.lifecycle_status = "Maintenance Hold"
```

**ASSET-05 (Emergency):**
```
IR-2026-00005 ──────────────────────────────────────────────────┐
                                                                 │
IMM04-26.04.00005 ──► ACC-2026-00005 ──► WO-CM-2026-00005 ◄─────┘
                                              │   (incident_report = IR-2026-00005)
                                              │   (sla_breached = True, mttr = 5.75h > 4h)
                                              │
                                              └──► CAPA-2026-00005
                                                       ├── source_ref = WO-CM-2026-00005
                                                       ├── linked_incident = IR-2026-00005
                                                       ├── asset = ACC-2026-00005 ✓
                                                       └── severity = Critical
```

---

### 3.4 Naming Series Reference

| Module | DocType | Pattern | Ví dụ |
|--------|---------|---------|-------|
| IMM-04 | Asset Commissioning | `IMM04-.YY.-.MM.-.#####` | IMM04-26.04.00001 |
| IMM-05 | Asset Document | `DOC-{asset_ref}-{YYYY}-{#####}` | DOC-ACC-2026-00001-2026-00001 |
| IMM-08 | PM Work Order | `PM-WO-.YYYY.-.#####` | PM-WO-2026-00001 |
| IMM-09 | Asset Repair | `WO-CM-.YYYY.-.#####` | WO-CM-2026-00001 |
| IMM-11 | IMM Asset Calibration | `CAL-.YYYY.-.#####` | CAL-2026-00001 |
| IMM-12 | IMM CAPA Record | `CAPA-.YYYY.-.#####` | CAPA-2026-00001 |
| Core | AC Asset | `ACC-.YYYY.-.#####` | ACC-2026-00001 |
| Core | Incident Report | `IR-.YYYY.-.#####` | IR-2026-00001 |

---

### 3.5 Regulatory Compliance Mapping

| Business Rule | Regulation | Module |
|--------------|-----------|--------|
| Tài liệu bắt buộc trước lắp đặt | NĐ 98/2021 Điều 5 | IMM-04 GW-1 |
| ĐKLH bắt buộc trước sử dụng | NĐ 98/2021 Điều 7 | IMM-04 GW-2 |
| Giấy phép thiết bị bức xạ | Luật NLNT 2008 | IMM-04 VR-07 |
| Unique serial traceability | ISO 9001:2015 §8.5.2 | IMM-04 VR-01 |
| Document control & version | ISO 9001:2015 §7.5 | IMM-05 |
| Calibration với lab accredited | ISO/IEC 17025 | IMM-11 VR-11-02 |
| Calibration interval bắt buộc | NĐ 98/2021 | IMM-11 Schedule |
| MTTR tracking | WHO HTM 2011.05 | IMM-09 |
| CAPA mandatory cho nonconformity | ISO 13485:2016 §8.5.2 | IMM-12 |
| Audit trail immutable | ISO 9001:2015 §7.5.3 | All modules |
| Preventive maintenance schedule | NĐ 98/2021 | IMM-08 Schedule |

---

### 3.6 Cross-Module Integration Test Matrix

| Trigger Event | Source Module | Auto-Action | Target Module | Verify Field |
|--------------|-------------|-------------|--------------|-------------|
| Clinical Release | IMM-04 | Mint AC Asset | Core | final_asset ≠ null |
| Clinical Release | IMM-04 | Auto-import docs | IMM-05 | source_commissioning |
| Clinical Release | IMM-04 | Create PM Schedule | IMM-08 | pm_schedule.asset_ref |
| Clinical Release | IMM-04 | Create Cal Schedule | IMM-11 | cal_schedule.asset |
| PM Major Failure | IMM-08 | Create CM WO | IMM-09 | source_pm_wo |
| PM Major Failure | IMM-08 | Asset Out of Service | Core | lifecycle_status |
| Repair Completed | IMM-09 | Create post-repair Cal | IMM-11 | is_recalibration=True |
| Repair SLA Breach | IMM-09 | Create CAPA | IMM-12 | source_type=Repair |
| Calibration Failed | IMM-11 | Asset Maintenance Hold | Core | lifecycle_status |
| Calibration Failed | IMM-11 | Create CAPA | IMM-12 | source_type=Cal Failure |
| CAPA Critical | IMM-12 | Lookback required | IMM-12 | lookback_required=True |

---

*Tài liệu này được tạo tự động từ AssetCore codebase bởi Claude Code.*
*Phiên bản: 1.0 | Ngày: 2026-04-20 | Scope: Wave 1 (IMM-04, 05, 08, 09, 11, 12)*
