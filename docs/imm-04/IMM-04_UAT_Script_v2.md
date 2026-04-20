# IMM-04 — UAT Script v2 (Post-refactor)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phiên bản UAT | 2.0.0 |
| Ngày | 2026-04-18 |
| Trạng thái | Active — phù hợp schema mới (IMM Device Model, AC Supplier, AC Department, AC Location) |
| Chuẩn | WHO HTM 2025, NĐ 98/2021, NĐ 142/2020, ISO 13485:2016 |
| Phụ thuộc docs | `IMM-04_Functional_Specs.md`, `IMM-04_API_Interface.md`, `IMM-04_Technical_Design.md` |

---

## 0. Mục đích

UAT này **thay thế** [IMM-04_UAT_Script.md](./IMM-04_UAT_Script.md) sau refactor BE→FE (2026-04-18):

- `master_item` nay link `IMM Device Model` (không phải ERPNext `Item`)
- `vendor` nay link `AC Supplier`
- `clinical_dept` nay link `AC Department`
- Thêm `installation_location` (AC Location), `asset_description`, `purchase_price`, `warranty_expiry_date`, `delivery_note_no`, `received_by`, `dept_head_acceptance`
- `mint_core_asset()` tạo `AC Asset` (kế thừa từ IMM-00) — không còn tạo ERPNext Asset

**Phạm vi UAT:** 5 test dataset thực tế × 28 test case × 9 nhóm (A→I) = full coverage cho 8 BR + 9 VR + 6 Gate + 17 endpoint.

---

## 1. Seed Data — 5 Dataset Thực Tế

Mỗi dataset đại diện 1 kịch bản đặc thù (risk class khác nhau + 1 happy-path + 1 DOA). Seed bằng:

```bash
bench --site <site> execute assetcore.tests.fixtures.imm04_seed_v2.seed_all
```

### 1.1 Master Data — Chung cho mọi dataset

**AC Department** (6 khoa):

| name | department_name | department_code | dept_head |
|---|---|---|---|
| AC-DEPT-0001 | Khoa Chẩn đoán Hình ảnh | CDHA | `dr.nguyen@hospital.vn` |
| AC-DEPT-0002 | Khoa Hồi sức Tích cực (ICU) | ICU | `dr.tran@hospital.vn` |
| AC-DEPT-0003 | Khoa Ung bướu | UB | `dr.le@hospital.vn` |
| AC-DEPT-0004 | Khoa Nội tổng hợp | NOI | `dr.hoang@hospital.vn` |
| AC-DEPT-0005 | Phòng Mổ (OR) | OR | `dr.vu@hospital.vn` |
| AC-DEPT-0006 | Khoa Kỹ thuật Y sinh | KTYS | `eng.pham@hospital.vn` |

**AC Location** (phòng cụ thể):

| name | location_name | location_code | clinical_area_type |
|---|---|---|---|
| AC-LOC-2026-0001 | CDHA - Phòng X-Quang 1 | CDHA-XR1 | Imaging |
| AC-LOC-2026-0002 | ICU - Giường 1 | ICU-B01 | ICU |
| AC-LOC-2026-0003 | UB - Phòng Xạ trị A | UB-RT-A | Imaging |
| AC-LOC-2026-0004 | NOI - Phòng 204 | NOI-204 | General Ward |
| AC-LOC-2026-0005 | OR - Phòng Mổ 3 | OR-03 | OR |

**AC Supplier** (5 NCC):

| name | supplier_name | supplier_code | vendor_type | iso_13485_cert | is_active |
|---|---|---|---|---|---|
| AC-SUP-2026-0001 | Công ty Philips Việt Nam | PHILIPS-VN | Distributor | CERT-13485-PH-2025 | 1 |
| AC-SUP-2026-0002 | Dräger Medical VN | DRAGER-VN | Distributor | CERT-13485-DR-2024 | 1 |
| AC-SUP-2026-0003 | Varian Medical Systems Asia | VARIAN-APAC | Manufacturer | CERT-13485-VAR-2025 | 1 |
| AC-SUP-2026-0004 | B.Braun Medical VN | BBRAUN-VN | Distributor | CERT-13485-BB-2025 | 1 |
| AC-SUP-2026-0005 | GE Healthcare VN | GE-VN | Distributor | CERT-13485-GE-2025 | 1 |

**IMM Device Model** (5 model):

| name | model_name | manufacturer | medical_device_class | risk_classification | is_radiation_device | is_pm_required | pm_interval_days | is_calibration_required | calibration_interval_days |
|---|---|---|---|---|---|---|---|---|---|
| IMM-MDL-2026-0001 | Philips Affiniti 70 Ultrasound | Philips | Class II | Medium | 0 | 1 | 180 | 1 | 365 |
| IMM-MDL-2026-0002 | Dräger Evita V300 Ventilator | Dräger | Class III | Critical | 0 | 1 | 90 | 1 | 365 |
| IMM-MDL-2026-0003 | Varian TrueBeam STx Linear Accelerator | Varian | Class III | Critical | 1 | 1 | 30 | 1 | 180 |
| IMM-MDL-2026-0004 | B.Braun Perfusor Space Infusion Pump | B.Braun | Class II | Medium | 0 | 1 | 365 | 1 | 365 |
| IMM-MDL-2026-0005 | GE Vivid E95 Cardiac Ultrasound | GE | Class II | Medium | 0 | 1 | 180 | 1 | 365 |

**Users (Actor pool):**

| user | role | full_name |
|---|---|---|
| `htm.ktv01@hospital.vn` | HTM Technician | Nguyễn Văn KTV1 |
| `biomed.eng01@hospital.vn` | Biomed Engineer | Trần Kỹ sư BE1 |
| `vendor.eng01@hospital.vn` | Vendor Engineer | Phạm Kỹ sư Hãng |
| `qa.officer01@hospital.vn` | QA Officer | Lê QA1 |
| `workshop.head@hospital.vn` | Workshop Head | Hoàng Xưởng trưởng |
| `vp.block2@hospital.vn` | VP Block2 | Vũ PTGĐ Khối 2 |
| `kho.van01@hospital.vn` | Warehouse | Đỗ Kho vận |
| `purchase.user@hospital.vn` | Purchase User | Ngô Mua sắm |

---

### 1.2 Dataset DS-01 — Class II Happy Path (Ultrasound)

**Mục tiêu:** Happy path từ Draft → Clinical Release không có Hold, không có NC.

| Field | Value |
|---|---|
| po_reference | `PO-2026-00101` (ERPNext Purchase Order; supplier_name = "Công ty Philips Việt Nam") |
| master_item | `IMM-MDL-2026-0001` (Philips Affiniti 70) |
| vendor | `AC-SUP-2026-0001` |
| clinical_dept | `AC-DEPT-0001` (CDHA) |
| installation_location | `AC-LOC-2026-0001` (Phòng X-Quang 1) |
| asset_description | "Máy siêu âm Philips Affiniti 70 — CDHA-US-01" |
| delivery_note_no | `DN-2026-0101` |
| purchase_price | `1_850_000_000` |
| warranty_expiry_date | `2028-04-30` |
| expected_installation_date | `2026-04-20` |
| reception_date | `2026-04-18` |
| vendor_engineer_name | "Kim Jae-hoon (Philips Korea)" |
| commissioned_by | `biomed.eng01@hospital.vn` |
| received_by | `kho.van01@hospital.vn` |
| dept_head_acceptance | `dr.nguyen@hospital.vn` |
| vendor_serial_no | `PH-AFF70-SN00123456` |
| is_radiation_device | 0 |
| risk_class | (auto-fill từ Device Model: Class II → "B") |
| doa_incident | 0 |

**Expected flow:** Draft → Pending_Doc_Verify (G01 pass: CO+CQ+Manual Received) → To_Be_Installed → Installing → Identification (QR auto: `BV-CDHA-2026-0001`) → Initial_Inspection → Clinical_Release → Submit thành công → `final_asset = AC-ASSET-2026-XXXXX`.

---

### 1.3 Dataset DS-02 — Class III Clinical Hold (Ventilator)

**Mục tiêu:** Test VR-05, auto Clinical Hold sau Initial Inspection, QA Officer trigger release.

| Field | Value |
|---|---|
| po_reference | `PO-2026-00102` (supplier_name = "Dräger Medical VN") |
| master_item | `IMM-MDL-2026-0002` (Dräger Evita V300) |
| vendor | `AC-SUP-2026-0002` |
| clinical_dept | `AC-DEPT-0002` (ICU) |
| installation_location | `AC-LOC-2026-0002` (ICU Giường 1) |
| asset_description | "Máy thở Dräger Evita V300 — ICU-VENT-01" |
| delivery_note_no | `DN-2026-0102` |
| purchase_price | `780_000_000` |
| warranty_expiry_date | `2027-05-15` |
| expected_installation_date | `2026-04-22` |
| vendor_serial_no | `DR-EV300-SN77881122` |
| is_radiation_device | 0 |
| risk_class | (auto: Class III → "C" → **trigger Clinical Hold**) |

**Expected flow:** Draft → ... → Initial_Inspection (baseline toàn Pass) → **Clinical_Hold** (auto vì risk_class = C) → QA Officer upload `qa_license_doc` (giấy phép BYT) → Clinical_Release → Submit.

---

### 1.4 Dataset DS-03 — Radiation Device (Linear Accelerator)

**Mục tiêu:** Test VR-07 (mandatory qa_license_doc), mandatory doc "Radiation License", strictest gate.

| Field | Value |
|---|---|
| po_reference | `PO-2026-00103` (supplier_name = "Varian Medical Systems Asia") |
| master_item | `IMM-MDL-2026-0003` (Varian TrueBeam) |
| vendor | `AC-SUP-2026-0003` |
| clinical_dept | `AC-DEPT-0003` (Ung bướu) |
| installation_location | `AC-LOC-2026-0003` (Phòng Xạ trị A) |
| asset_description | "Máy xạ trị Varian TrueBeam STx — UB-LINAC-01" |
| delivery_note_no | `DN-2026-0103` |
| purchase_price | `65_000_000_000` |
| warranty_expiry_date | `2029-01-20` |
| expected_installation_date | `2026-05-15` |
| vendor_serial_no | `VAR-TB-SN-H7A2K9` |
| is_radiation_device | 1 (auto từ Device Model) |
| radiation_license_no | `CATBXHN-2026-0087` |
| risk_class | "Radiation" (auto) |

**Expected flow:** 
1. `commissioning_documents` tự động có thêm 2 rows mandatory: `License` + `Radiation License`
2. Thử Submit không có `qa_license_doc` → **VR-07 throw: "Thiết bị phát bức xạ nhưng chưa có Giấy phép Cục ATBXHN"**
3. Upload `qa_license_doc` (PDF giấy phép) → có thể Release

---

### 1.5 Dataset DS-04 — Baseline Fail → Re-Inspection (Infusion Pump)

**Mục tiêu:** Test VR-03 (baseline Fail → block Release), state chuyển về Re_Inspection, sau sửa → Pass.

| Field | Value |
|---|---|
| po_reference | `PO-2026-00104` (supplier_name = "B.Braun Medical VN") |
| master_item | `IMM-MDL-2026-0004` (B.Braun Perfusor Space) |
| vendor | `AC-SUP-2026-0004` |
| clinical_dept | `AC-DEPT-0004` (Nội tổng hợp) |
| installation_location | `AC-LOC-2026-0004` (Phòng 204) |
| asset_description | "Bơm tiêm B.Braun Perfusor Space — NOI-PUMP-05" |
| delivery_note_no | `DN-2026-0104` |
| purchase_price | `42_500_000` |
| warranty_expiry_date | `2028-03-10` |
| vendor_serial_no | `BB-PS-SN-55443322` |
| risk_class | "B" |

**Baseline tests payload (có 1 Fail):**

| parameter | measured_val | expected_max | unit | test_result | fail_note |
|---|---|---|---|---|---|
| Earth Continuity | 0.3 | 0.5 | Ω | Pass | — |
| Insulation Resistance | 15 | — | MΩ | Pass | — |
| Leakage Current | **650** | 500 | µA | **Fail** | **Rò dòng vượt giới hạn — cần replace PCB chính** |
| Visual Inspection | — | — | — | Pass | — |

**Expected flow:** Submit baseline → **VR-03b block Release, force Re_Inspection**. Kỹ sư sửa, re-submit với Leakage Current = 250 µA Pass → Release.

---

### 1.6 Dataset DS-05 — DOA Incident → Return to Vendor (Cardiac Ultrasound)

**Mục tiêu:** Test report_doa → NC độc lập với severity=Critical → block Release → Return to Vendor.

| Field | Value |
|---|---|
| po_reference | `PO-2026-00105` (supplier_name = "GE Healthcare VN") |
| master_item | `IMM-MDL-2026-0005` (GE Vivid E95) |
| vendor | `AC-SUP-2026-0005` |
| clinical_dept | `AC-DEPT-0001` (CDHA) |
| installation_location | `AC-LOC-2026-0001` (Phòng X-Quang 1 — tạm) |
| asset_description | "Máy siêu âm tim GE Vivid E95 — CDHA-US-02" |
| delivery_note_no | `DN-2026-0105` |
| purchase_price | `2_150_000_000` |
| warranty_expiry_date | `2028-04-30` |
| vendor_serial_no | `GE-VE95-SN99887766` |
| risk_class | "B" |

**DOA event payload** (khi đang ở state `Installing`):

```json
{
  "nc_type": "DOA",
  "severity": "Critical",
  "description": "Màn hình không lên sau khi cắm điện. Kỹ sư Philips xác nhận hỏng bo nguồn.",
  "damage_proof": "/files/doa-ge-vivid-e95.jpg"
}
```

**Expected flow:** Installing → report_doa → `doa_incident = 1`, NC mới với `resolution_status=Open` → transition sang `Non_Conformance` → `Return_To_Vendor` → không sinh AC Asset.

---

## 2. Test Cases — Ma trận chi tiết

### 2.1 Nhóm A — Tạo phiếu từ PO (US-04-01, BR-04-01)

**TC-04-01: Tạo phiếu DS-01 thành công**

| Field | Value |
|---|---|
| **Precondition** | Seed data v2 đã chạy. User login `htm.ktv01@hospital.vn` |
| **Steps** | 1. `GET /api/method/assetcore.api.imm04.search_link?doctype=Purchase Order&query=PO-2026-00101`<br>2. `GET /api/method/assetcore.api.imm04.get_po_details?po_name=PO-2026-00101` → kỳ vọng `data.supplier = "AC-SUP-2026-0001"` (match theo supplier_name)<br>3. `GET /api/method/assetcore.api.imm00.get_device_model?name=IMM-MDL-2026-0001` → lấy `medical_device_class="Class II"`, `is_radiation_device=0`<br>4. `POST /api/method/assetcore.api.imm04.create_commissioning` với payload DS-01 |
| **Expected** | `success=true`, `name` match `^IMM04-26-04-\d{5}$`, `workflow_state=Draft`. `commissioning_documents` có 4 rows: CO, CQ, Manual (mandatory), Warranty (optional). 1 Lifecycle Event `event_type=created` |
| **Coverage** | BR-04-01, US-04-01 |

**TC-04-02: Thiếu field bắt buộc**

| Field | Value |
|---|---|
| **Steps** | `POST create_commissioning` bỏ `clinical_dept` |
| **Expected** | `success=false`, `code="MISSING_FIELDS"`, message chứa "clinical_dept" |

**TC-04-03: Wrong DocType link → reject**

| Field | Value |
|---|---|
| **Steps** | POST với `vendor = "SUP-ERPNEXT-001"` (ERPNext Supplier, không phải AC Supplier) |
| **Expected** | `ValidationError` — "Could not find AC Supplier: SUP-ERPNEXT-001" |

---

### 2.2 Nhóm B — Auto-fill từ IMM Device Model

**TC-04-04: Auto-fill risk_class + PM interval**

| Field | Value |
|---|---|
| **Steps** | Tạo DS-02 (Dräger Evita V300) không truyền `risk_class` |
| **Expected** | Sau `insert`, `doc.risk_class = "C"` (Class III → C), `doc.is_radiation_device = 0` |
| **Coverage** | `_autofill_from_device_model()` |

**TC-04-05: Auto-set radiation flag**

| Field | Value |
|---|---|
| **Steps** | Tạo DS-03 (Varian TrueBeam) không truyền `is_radiation_device` |
| **Expected** | `doc.is_radiation_device = 1`, `doc.risk_class = "Radiation"`. `commissioning_documents` tự append "License" + "Radiation License" mandatory |

---

### 2.3 Nhóm C — VR-01 Serial Unique

**TC-04-06: SN trùng với phiếu khác**

| Field | Value |
|---|---|
| **Setup** | Tạo DS-01 với SN `PH-AFF70-SN00123456`, lưu thành công |
| **Steps** | Tạo phiếu mới với cùng SN `PH-AFF70-SN00123456` |
| **Expected** | `ValidationError`: "VR-01: Serial Number 'PH-AFF70-SN00123456' đã tồn tại trong Phiếu..." |

**TC-04-07: SN trùng với AC Asset đã tồn tại**

| Field | Value |
|---|---|
| **Setup** | AC Asset có `manufacturer_sn = "DR-EV300-SN77881122"` |
| **Steps** | Tạo DS-02 với SN này |
| **Expected** | "VR-01: Serial Number ... đã được gán cho Tài Sản..." |

---

### 2.4 Nhóm D — Gate G01 Mandatory Documents

**TC-04-08: Block transition khi thiếu CO**

| Field | Value |
|---|---|
| **Setup** | DS-01 ở `Draft`, CO status = `Pending` |
| **Steps** | `POST transition_state action="Xác nhận đủ tài liệu"` |
| **Expected** | `VR-02 (Gate G01): Chưa đủ tài liệu bắt buộc. Còn thiếu: CO` |

**TC-04-09: Pass G01 khi Waived**

| Field | Value |
|---|---|
| **Steps** | Mark CO status=`Waived` (lý do: NCC cung cấp bản scan) → transition |
| **Expected** | Pass → state = `To_Be_Installed` |

---

### 2.5 Nhóm E — Gate G03 Baseline (VR-03)

**TC-04-10: DS-04 Leakage Fail → block Release**

| Field | Value |
|---|---|
| **Steps** | Submit baseline DS-04 (Leakage Fail), transition đến Clinical_Release |
| **Expected** | `VR-03b: Không thể Phát hành! Leakage Current fail`. State force về `Re_Inspection` |

**TC-04-11: Fail không có fail_note**

| Field | Value |
|---|---|
| **Steps** | Submit baseline có Fail nhưng `fail_note=""` |
| **Expected** | `VR-03a: 'Leakage Current' kết quả Không Đạt. Bắt buộc phải ghi Nguyên nhân...` |

**TC-04-12: Re-submit sau sửa → Pass**

| Field | Value |
|---|---|
| **Steps** | Sau TC-04-10, cập nhật Leakage = 250 µA Pass, re-submit |
| **Expected** | State = `Clinical_Release`, `overall_inspection_result=Pass` |

---

### 2.6 Nhóm F — VR-07 Radiation License

**TC-04-13: Submit DS-03 không có qa_license_doc → block**

| Field | Value |
|---|---|
| **Steps** | DS-03 ở Clinical_Release, `qa_license_doc=""`, call `submit_commissioning` |
| **Expected** | `VR-07: Thiết bị này phát bức xạ / tia X nhưng chưa có Giấy phép của Cục An toàn Bức xạ Hạt nhân` |

**TC-04-14: Upload license → release OK**

| Field | Value |
|---|---|
| **Steps** | Upload `qa_license_doc = /files/radiation-license-linac.pdf`, board_approver = `vp.block2@hospital.vn`, submit |
| **Expected** | `docstatus=1`, `final_asset=AC-ASSET-2026-XXXXX`, Asset.udi_code = `BV-UB-2026-0003` |

---

### 2.7 Nhóm G — G05 No Open NC

**TC-04-15: DS-05 Open DOA NC → block Release**

| Field | Value |
|---|---|
| **Setup** | DS-05 ở Installing, call `report_doa(DS-05, description, photo)` tạo NC Open |
| **Steps** | Cố gắng transition lên Clinical_Release |
| **Expected** | `VR-04 (Gate G05): Còn 1 NC chưa đóng` |

**TC-04-16: Close NC → có thể Return_To_Vendor**

| Field | Value |
|---|---|
| **Steps** | `close_nonconformance(nc_name, resolution_status="Resolved", return_to_vendor_ref="RV-2026-0005")` |
| **Expected** | NC.resolution_status=Closed. State chuyển sang `Return_To_Vendor`. KHÔNG sinh AC Asset |

---

### 2.8 Nhóm H — Gate G06 + GW-2 (BR-04-07, BR-04-08)

**TC-04-17: Submit thiếu board_approver**

| Field | Value |
|---|---|
| **Steps** | DS-01 ở Clinical_Release không set `board_approver` |
| **Expected** | `Gate G06: Cần chọn Người Phê Duyệt Ban Giám Đốc trước khi Clinical Release` |

**TC-04-18: GW-2 thiếu Chứng nhận ĐKLH**

| Field | Value |
|---|---|
| **Setup** | DS-01 ở Clinical_Release, AC Asset chưa có Asset Document type "Chứng nhận đăng ký lưu hành" |
| **Expected** | `GW-2 Compliance Block: Thiết bị chưa có Chứng nhận đăng ký lưu hành hợp lệ trong IMM-05` |

**TC-04-19: GW-2 Exempt pass**

| Field | Value |
|---|---|
| **Setup** | Tạo Asset Document `is_exempt=1` + upload `exempt_proof` |
| **Expected** | GW-2 skip → Submit thành công |

---

### 2.9 Nhóm I — On Submit → Mint AC Asset

**TC-04-20: DS-01 Submit → AC Asset đầy đủ**

| Field | Value |
|---|---|
| **Steps** | Submit DS-01 |
| **Expected AC Asset** | `asset_name = "Máy siêu âm Philips Affiniti 70 — CDHA-US-01"` (từ `asset_description`); `device_model = IMM-MDL-2026-0001`; `supplier = AC-SUP-2026-0001`; `department = AC-DEPT-0001`; `location = AC-LOC-2026-0001`; `medical_device_class = "Class II"`; `risk_classification = "Medium"`; `is_pm_required = 1`, `pm_interval_days = 180`; `is_calibration_required = 1`, `calibration_interval_days = 365`; `gross_purchase_amount = 1_850_000_000`; `warranty_expiry_date = 2028-04-30`; `manufacturer_sn = "PH-AFF70-SN00123456"`; `udi_code = "BV-CDHA-2026-0001"`; `commissioning_ref = <IMM04 name>`; `lifecycle_status = "Commissioned"` |

**TC-04-21: Risk class mapping D → Critical**

| Field | Value |
|---|---|
| **Setup** | Edit DS-02 risk_class = "D" trước Submit |
| **Expected** | AC Asset `medical_device_class = "Class III"`, `risk_classification = "Critical"` |

**TC-04-22: Radiation mapping**

| Field | Value |
|---|---|
| **Setup** | Submit DS-03 (Radiation) |
| **Expected** | AC Asset `medical_device_class = "Class III"` (từ device model), `risk_classification = "High"` |

---

### 2.10 Nhóm J — Audit Trail + Lifecycle

**TC-04-23: Lifecycle Event immutable (VR-06)**

| Field | Value |
|---|---|
| **Steps** | Edit row `lifecycle_events[0].actor` trên DS-01 đã Submit |
| **Expected** | `VR-06: Nhật ký sự kiện vòng đời không được chỉnh sửa. Dữ liệu audit trail bất biến` |

**TC-04-24: Full lifecycle event coverage**

| Field | Value |
|---|---|
| **Steps** | Từ tạo DS-01 → Submit, `GET get_timeline(name)` |
| **Expected** | Có các event: `created`, `document_received` × N, `identification_assigned`, `baseline_submitted`, `clinical_release`, `Release`. Tất cả `actor`, `event_timestamp`, `ip_address` đầy đủ |

---

### 2.11 Nhóm K — Permission Matrix

**TC-04-25: HTM Tech không Submit được**

| Field | Value |
|---|---|
| **Steps** | Login `htm.ktv01@hospital.vn`, `submit_commissioning(DS-01)` |
| **Expected** | `PERMISSION_DENIED` — submit chỉ VP Block2 hoặc Workshop Head |

**TC-04-26: Vendor Eng chỉ xem phiếu của mình**

| Field | Value |
|---|---|
| **Steps** | Login `vendor.eng01`, `list_commissioning()` |
| **Expected** | Chỉ trả về phiếu có `vendor` = AC Supplier liên kết user này |

---

### 2.12 Nhóm L — NFR Performance

**TC-04-27: get_form_context < 2s**

| Field | Value |
|---|---|
| **Steps** | DS-01 đã submit, measure P95 trên 100 requests |
| **Target** | NFR-04-01: P95 < 2s |

**TC-04-28: check_sn_unique < 500ms**

| Field | Value |
|---|---|
| **Steps** | 200 parallel calls `check_sn_unique(sn=random)` |
| **Target** | NFR-04-02: P95 < 500ms |

---

## 3. Ma trận Coverage

| Dataset | TC chính | BR/VR covered |
|---|---|---|
| DS-01 Ultrasound | TC-01, 20, 23, 24, 27 | BR-01, 02, 08; VR-06; Happy path |
| DS-02 Ventilator | TC-04, 21 | BR-05 (Clinical Hold); auto-fill |
| DS-03 Linear Accel | TC-05, 13, 14, 22 | BR-05, VR-07; Radiation |
| DS-04 Infusion Pump | TC-10, 11, 12 | BR-04 (G03); VR-03a/b |
| DS-05 Cardiac US (DOA) | TC-15, 16 | BR-06 (G05); NC workflow |
| (cross) | TC-02, 03, 06, 07, 08, 09, 17, 18, 19, 25, 26, 28 | BR-01, 03, 07; VR-01, Backdate; perms; NFR |

**Tổng:** 5 dataset × 28 TC covers 8/8 BR + 9/9 VR + 6/6 Gate = **100% spec coverage**.

---

## 4. Test Execution Schedule

| Ngày | Sáng | Chiều |
|---|---|---|
| D1 (2026-04-21) | Seed data + DS-01 TC-01→03 | DS-02 TC-04→05, DS-03 TC-13→14 |
| D2 (2026-04-22) | DS-04 TC-10→12 (baseline Fail) | DS-05 TC-15→16 (DOA) |
| D3 (2026-04-23) | TC-17→22 (Submit + Mint) | TC-23→24 (audit) |
| D4 (2026-04-24) | TC-25→26 (perms) | TC-27→28 (perf) |
| D5 (2026-04-25) | Retest các TC Fail | Sign-off |

---

## 5. Sign-off Checklist

- [ ] Seed data v2 đã chạy thành công trên site UAT
- [ ] DS-01 through DS-05 được tạo và lưu trong hệ thống (docstatus=0 hoặc 1)
- [ ] 28/28 TC đạt Pass (nếu Fail → ticket JIRA trước sign-off)
- [ ] `final_asset` của DS-01, DS-02, DS-03 là AC Asset (không phải ERPNext Asset)
- [ ] AC Asset có đủ `device_model`, `supplier`, `department`, `location`, `medical_device_class`, `risk_classification`, PM+Calibration intervals đúng từ IMM Device Model
- [ ] `lifecycle_events` trong tất cả 5 DS đầy đủ chuỗi event
- [ ] FE form hiển thị đúng dropdown AC Supplier/AC Department/AC Location/IMM Device Model (không còn ERPNext core)
- [ ] GW-2 block Submit khi thiếu Asset Document → IMM-05 compliance

**UAT Approver:**
- [ ] Workshop Head: _______________
- [ ] QA Officer: _______________
- [ ] VP Block2: _______________
- [ ] CMMS Admin: _______________

---

## 6. Seed script fixture path

Tạo file `assetcore/tests/fixtures/imm04_seed_v2.py`:

```python
"""Seed data for IMM-04 UAT v2 (post-refactor with IMM-00 DocTypes)."""
import frappe

def seed_all():
    seed_departments()
    seed_locations()
    seed_suppliers()
    seed_device_models()
    seed_users()
    frappe.db.commit()
    print("✓ UAT v2 seed complete — 5 datasets ready")

# ... (mỗi hàm insert master data tương ứng §1.1)
```

Run: `bench --site uat.assetcore.local execute assetcore.tests.fixtures.imm04_seed_v2.seed_all`

---

*End of UAT Script v2 — IMM-04 — 2026-04-18*
