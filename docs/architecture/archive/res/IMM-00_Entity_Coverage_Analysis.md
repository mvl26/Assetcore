# IMM-00 — Phân tích Đáp ứng Thực thể Dữ liệu HTM

**Ngày:** 2026-04-18  
**Scope:** AssetCore v3 — IMM-00 Foundation + toàn bộ DocType hiện có  
**Chuẩn tham chiếu:** WHO HTM 2025 · NĐ 98/2021/NĐ-CP · ISO 13485:2016 · ISO/IEC 17025 · ERPNext Asset Module  
**Kết luận nhanh:** IMM-00 đáp ứng ~78% thực thể cốt lõi HTM. Còn 7 thực thể quan trọng cần bổ sung.

---

## 1. Bản đồ thực thể HTM theo WHO Lifecycle

WHO HTM chia vòng đời thiết bị y tế thành 7 giai đoạn. AssetCore cần đủ thực thể dữ liệu cho từng giai đoạn:

```
Needs Assessment → Procurement → Installation → Operation → Maintenance → Calibration → End-of-Life
```

Phân tích dưới đây ánh xạ từng thực thể HTM → DocType AssetCore hiện có, đối chiếu với ERPNext Asset module.

---

## 2. Inventory DocTypes AssetCore (31 DocTypes tổng)

### 2.1 IMM-00 Foundation (13 DocTypes)

| DocType | Prefix | Loại | Vai trò HTM |
|---|---|---|---|
| AC Asset | AC | Core | Registry thiết bị — master record |
| AC Supplier | AC | Core | Nhà cung cấp / Lab hiệu chuẩn |
| AC Location | AC | Core | Vị trí vật lý (tree) |
| AC Department | AC | Core | Khoa / đơn vị quản lý (tree) |
| AC Asset Category | AC | Core | Phân loại thiết bị + PM/Cal defaults |
| IMM Device Model | IMM | Governance | Catalog model — template dữ liệu kỹ thuật |
| IMM SLA Policy | IMM | Governance | Ma trận SLA priority × risk class |
| IMM Audit Trail | IMM | Governance | Log bất biến SHA-256 (ISO 13485:7.5.9) |
| IMM CAPA Record | IMM | Governance | CAPA lifecycle (ISO 13485:8.5) |
| Asset Lifecycle Event | — | Governance | Sự kiện vòng đời chuẩn hoá |
| Incident Report | — | Standalone | Báo cáo sự cố / near miss |
| IMM Device Spare Part | — | Child | Danh mục phụ tùng theo model |
| AC Authorized Technician | AC | Child | KTV ủy quyền của NCC |

### 2.2 Các module đã có (18 DocTypes bổ sung)

| DocType | Module | Vai trò HTM |
|---|---|---|
| Asset Commissioning | IMM-04 | Phiếu nghiệm thu, kiểm thử baseline |
| Commissioning Checklist | IMM-04 | Child: danh mục nghiệm thu |
| Commissioning Document Record | IMM-04 | Child: hồ sơ tài liệu nghiệm thu |
| Asset QA Non Conformance | IMM-04 | Ghi nhận NC trong quá trình lắp đặt |
| Asset Document | IMM-05 | Quản lý hồ sơ kỹ thuật thiết bị |
| Document Request | IMM-05 | Yêu cầu cung cấp tài liệu |
| Required Document Type | IMM-05 | Child: loại tài liệu bắt buộc |
| Expiry Alert Log | IMM-05 | Log cảnh báo hết hạn tài liệu |
| PM Work Order | IMM-08 | Lệnh bảo trì định kỳ |
| PM Schedule | IMM-08 | Lịch PM (generated từ interval) |
| PM Task Log | IMM-08 | Child: log thực hiện từng task PM |
| PM Checklist Template | IMM-08 | Template kiểm tra PM theo model |
| PM Checklist Item | IMM-08 | Child: item trong template |
| PM Checklist Result | IMM-08 | Kết quả kiểm tra từng item |
| Asset Repair | IMM-09 | Work Order sửa chữa (CM) |
| Spare Parts Used | IMM-09 | Child: vật tư sử dụng trong sửa chữa |
| Repair Checklist | IMM-09 | Child: kiểm tra sau sửa chữa |
| Firmware Change Request | IMM-09 | Kiểm soát thay đổi firmware |

---

## 3. So sánh với ERPNext Asset Module

ERPNext quản lý tài sản **từ góc độ kế toán / ERP**. AssetCore quản lý thiết bị **từ góc độ HTM / lâm sàng**. Hai hệ thống có overlap và gap như sau:

### 3.1 ERPNext Asset Module (16 DocTypes)

| ERPNext DocType | Mục đích | AssetCore tương đương | Trạng thái |
|---|---|---|---|
| Asset | Registry tài sản (kế toán) | **AC Asset** | ✅ Thay thế đầy đủ + HTM fields |
| Asset Category | Phân loại tài sản | **AC Asset Category** | ✅ Thay thế + PM/Cal defaults |
| Asset Repair | Sửa chữa tài sản | **Asset Repair (IMM-09)** | ✅ Thay thế đầy đủ hơn |
| Asset Maintenance | Bảo trì (task-based) | **PM Work Order (IMM-08)** | ✅ Thay thế đầy đủ hơn |
| Asset Maintenance Log | Log bảo trì | **PM Task Log** | ✅ |
| Asset Maintenance Task | Task bảo trì | **PM Checklist Item/Result** | ✅ |
| Asset Maintenance Team | Nhóm bảo trì | Role + AC Authorized Technician | ⚠️ Partial — không có DocType riêng |
| Asset Movement | Di chuyển tài sản giữa locations | **KHÔNG CÓ** | 🔴 Gap |
| Asset Activity | Log hoạt động tài sản | Asset Lifecycle Event | ⚠️ Partial — ALE đầy đủ hơn |
| Asset Value Adjustment | Điều chỉnh giá trị | **KHÔNG CÓ** | 🟡 Low priority (kế toán) |
| Asset Depreciation Schedule | Khấu hao | **KHÔNG CÓ** | 🟡 Low priority (kế toán) |
| Asset Capitalization | Vốn hóa tài sản | **KHÔNG CÓ** | 🟡 Low priority (kế toán) |
| Asset Shift Allocation | Phân bổ theo ca | **KHÔNG CÓ** | 🟡 Low priority |
| Location | Vị trí (phẳng) | **AC Location** (tree) | ✅ Đầy đủ hơn |
| Asset Finance Book | Sổ kế toán | **KHÔNG CÓ** | 🟡 Low priority |

### 3.2 Fields ERPNext Asset KHÔNG có trong AC Asset

| Field ERPNext | Loại | Ý nghĩa | Quyết định |
|---|---|---|---|
| calculate_depreciation | Check | Tính khấu hao | 🟡 Bỏ — domain khác |
| finance_books | Table | Sổ kế toán khấu hao | 🟡 Bỏ — domain khác |
| is_composite_asset | Check | Tài sản ghép | 🟡 Bỏ |
| insurance_start_date | Date | Bảo hiểm thiết bị | 🟠 Thiếu — cần bổ sung |
| insurance_end_date | Date | Bảo hiểm thiết bị | 🟠 Thiếu — cần bổ sung |
| insurer / policy_number | Data | Bảo hiểm thiết bị | 🟠 Thiếu — cần bổ sung |
| cost_center | Link | Trung tâm chi phí | 🟡 Nice-to-have |
| purchase_receipt / invoice | Link | Chứng từ mua | 🟡 Có thể link IMM-02/03 |
| split_from | Link | Tách từ tài sản khác | 🟡 Bỏ |

### 3.3 Fields AC Asset có mà ERPNext KHÔNG có

| Field AssetCore | Ý nghĩa | Chuẩn |
|---|---|---|
| lifecycle_status | State machine vòng đời | WHO HTM |
| risk_classification | Phân loại nguy cơ | NĐ 98/2021 |
| medical_device_class | Lớp thiết bị y tế | NĐ 98/2021 |
| udi_code | Unique Device Identifier | FDA UDI / EU MDR |
| gmdn_code | Global Medical Device Nomenclature | WHO GMDN |
| byt_reg_no | Số đăng ký Bộ Y tế | NĐ 98/2021 |
| byt_reg_expiry | Hạn đăng ký BYT | NĐ 98/2021 |
| device_model | Link → IMM Device Model | HTM |
| responsible_technician | KTV phụ trách (per asset) | HTM |
| is_pm_required | Bảo trì định kỳ | WHO HTM |
| is_calibration_required | Hiệu chuẩn | ISO 17025 |
| calibration_status | Trạng thái hiệu chuẩn | ISO 17025 |
| commissioning_date / ref | Nghiệm thu + phiếu | HTM |
| next_pm_date / next_calibration_date | Lịch kế tiếp | HTM |

---

## 4. Phân tích Gap — Thực thể HTM còn thiếu

### 4.1 Gap theo WHO HTM Lifecycle

| Giai đoạn HTM | Thực thể cần | AssetCore có | Gap |
|---|---|---|---|
| **Needs Assessment** | Budget request, HTA report | ❌ | IMM-01/02/03 chưa build |
| **Procurement** | Purchase Order, Tender, Contract | ❌ | IMM-02/03 chưa build |
| **Installation** | Asset Commissioning | ✅ IMM-04 | — |
| **Documentation** | Asset Document, Document Request | ✅ IMM-05 | — |
| **Operation** | AC Asset, Incident Report, lifecycle_status | ✅ IMM-00 | — |
| **PM Maintenance** | PM Work Order, PM Schedule, PM Checklist | ✅ IMM-08 | — |
| **Corrective Maintenance** | Asset Repair (CM), Firmware Change | ✅ IMM-09 | — |
| **Calibration** | Calibration WO, Calibration Certificate | ⚠️ IMM-11 chưa build | Gap lớn |
| **Transfer/Movement** | Asset Movement | ❌ | Không có DocType |
| **Insurance** | Insurance policy tracking | ❌ | Chỉ có fields trên Supplier |
| **Spare Parts Inventory** | Stock Entry, Spare Parts Stock Level | ⚠️ Partial | Chỉ có catalog, không có tồn kho |
| **Training** | Operator Training Record | ❌ | WHO HTM yêu cầu |
| **Risk Assessment** | Risk Register | ⚠️ Partial | Chỉ có risk_classification static |
| **End-of-Life** | Disposal Record, Trade-in | ❌ | IMM-13/14 chưa build |
| **CAPA / QMS** | IMM CAPA Record, Audit Trail | ✅ IMM-00 | — |
| **Regulatory** | BYT Registration, Incident Report | ✅ IMM-00/05 | — |

### 4.2 Gap cụ thể theo mức độ ưu tiên

#### 🔴 HIGH — Ảnh hưởng trực tiếp đến vận hành

**G-01: Không có DocType Asset Movement / Transfer**

ERPNext có `Asset Movement` để ghi lại việc di chuyển tài sản giữa location/department/custodian. AssetCore hoàn toàn thiếu thực thể này.

- **Impact:** Không thể audit trail việc thiết bị bị chuyển phòng, điều chuyển khoa. lifecycle_status không phản ánh việc "đang vận chuyển".
- **Cần tạo:** DocType `Asset Transfer` với fields: `from_location`, `to_location`, `from_department`, `to_department`, `transfer_date`, `reason`, `approved_by`, `transfer_type` (Internal/External/Loan), và tự động tạo Asset Lifecycle Event "transferred".
- **Chuẩn:** WHO HTM 3.3 — traceability of device location

**G-02: Không có Calibration Work Order (IMM-11)**

AC Asset có đủ fields (`is_calibration_required`, `calibration_interval_days`, `next_calibration_date`, `calibration_status`) nhưng **không có DocType lệnh hiệu chuẩn**. IMM-11 chưa được build.

- **Impact:** Không thể quản lý chu trình hiệu chuẩn, không có certificate tracking, không link với AC Supplier (Calibration Lab).
- **Cần tạo:** DocType `Calibration Work Order` với: `asset`, `calibration_type` (Internal/External), `assigned_lab` (AC Supplier), `calibration_date`, `certificate_no`, `result` (Pass/Fail/Conditional), `next_calibration_date`, `calibration_parameters` (child table), và `calibration_certificate` (Attach).
- **Chuẩn:** ISO/IEC 17025 · WHO HTM 5.4

**G-03: Spare Parts — Không có Inventory Tracking**

`IMM Device Spare Part` là catalog (danh mục phụ tùng theo model) nhưng không tracking tồn kho thực tế. `Spare Parts Used` trong IMM-09 ghi xuất kho nhưng không link inventory.

- **Impact:** Không biết số lượng phụ tùng tồn kho, không cảnh báo khi stock thấp, không track cost of repair accurately.
- **Giải pháp ngắn hạn:** Tích hợp với ERPNext Stock Entry nếu dùng ERPNext. Nếu Frappe-only: tạo DocType `Spare Part Stock` đơn giản.
- **Chuẩn:** WHO HTM 4.5 — spare parts availability

#### 🟠 MEDIUM — Ảnh hưởng compliance / audit

**G-04: Không có Asset Insurance Tracking**

ERPNext Asset có 5 fields bảo hiểm. AC Asset hoàn toàn thiếu.

- **Impact:** Không audit được trạng thái bảo hiểm thiết bị đắt tiền (MRI, CT scanner). Đây là yêu cầu thực tế tại các cơ sở y tế VN.
- **Cần thêm vào AC Asset:** `insurance_policy_no`, `insurer`, `insurance_start`, `insurance_end`, `insured_value`. Hoặc tạo child table `Asset Insurance`.

**G-05: Không có Service Contract DocType**

AC Supplier có `contract_start`, `contract_end`, `service_contract_ref` nhưng chỉ có 1 contract per supplier. Thực tế: 1 supplier có thể có nhiều contract cho các thiết bị khác nhau.

- **Impact:** Không link contract cụ thể → từng thiết bị, không quản lý được scope/SLA theo từng HĐ.
- **Cần tạo:** DocType `Service Contract` với: `supplier`, `asset_list` (child), `contract_type` (Warranty/Service/Calibration), `start_date`, `end_date`, `coverage_details`, `auto_renewal`.

**G-06: Không có Operator Training Record**

WHO HTM 3.4 yêu cầu ghi nhận training cho người vận hành thiết bị y tế (đặc biệt Class III).

- **Impact:** Không có audit trail về operator competency. Không đáp ứng yêu cầu accreditation (JCI, ISO).
- **Cần tạo:** DocType `Asset Training Record` với: `asset`, `trainee` (User), `trainer`, `training_date`, `training_type` (Operator/Technical/Safety), `result` (Pass/Fail), `certificate_expiry`.

**G-07: Không có Risk Register / Risk Assessment Form**

AC Asset có `risk_classification` (Low/Medium/High/Critical) nhưng đây là giá trị tĩnh từ Device Model. Không có form đánh giá rủi ro động theo thực trạng vận hành.

- **Impact:** Thiếu evidence-based risk assessment cho accreditation, ISO 14971 compliance.
- **Giải pháp:** Tạo DocType `Asset Risk Assessment` với: `asset`, `assessment_date`, `assessor`, `risk_factors` (child table), `overall_risk_score`, `mitigation_plan`, `next_review_date`.

#### 🟡 LOW — Nice-to-have

**G-08: Không có Total Cost of Ownership (TCO) Tracking**

ERPNext có đầy đủ tích hợp kế toán (Finance Books, Depreciation). AssetCore không có.

- **Cần:** Aggregation view tính TCO = purchase_price + maintenance_cost + calibration_cost + repair_cost - residual_value. Có thể là computed field hoặc report.

**G-09: Không có Asset Disposal / Decommission Record**

`lifecycle_status = "Decommissioned"` nhưng không có DocType chính thức ghi lại quy trình thanh lý (disposal method, reason, approved by, salvage value).

- **Cần tạo:** `Asset Disposal Record` (IMM-13/14 scope).

**G-10: Không có KPI Snapshot Storage**

`rollup_asset_kpi()` tính MTTR/uptime nhưng kết quả ghi thẳng vào AC Asset. Không có lịch sử trend theo tháng.

- **Cần:** DocType `Asset KPI Snapshot` với: `asset`, `period`, `uptime_pct`, `mttr_hours`, `mtbf_days`, `pm_compliance_pct`, `capa_closure_rate`.

---

## 5. Ma trận Đáp ứng Tổng hợp

### 5.1 Theo thực thể HTM cốt lõi

| Thực thể HTM | DocType AssetCore | Đáp ứng | Thiếu |
|---|---|---|---|
| Thiết bị (Device Registry) | AC Asset | ✅ 100% | — |
| Model/Template kỹ thuật | IMM Device Model | ✅ 100% | — |
| Phân loại (Classification) | AC Asset Category | ✅ 95% | Insurance tracking |
| Vị trí (Location) | AC Location (tree) | ✅ 100% | — |
| Khoa (Department) | AC Department (tree) | ✅ 100% | — |
| Nhà cung cấp (Supplier) | AC Supplier + AC Authorized Tech | ✅ 90% | Service Contract |
| Nghiệm thu (Commissioning) | Asset Commissioning (IMM-04) | ✅ 100% | — |
| Hồ sơ (Documents) | Asset Document + Document Request (IMM-05) | ✅ 100% | — |
| Bảo trì PM | PM Work Order + PM Schedule (IMM-08) | ✅ 100% | — |
| Sửa chữa CM | Asset Repair + Firmware Change (IMM-09) | ✅ 100% | — |
| **Hiệu chuẩn (Calibration)** | Fields on AC Asset only | ⚠️ 30% | **Calibration WO** |
| **Di chuyển (Transfer)** | Không có | ❌ 0% | **Asset Transfer DocType** |
| Sự cố (Incident) | Incident Report | ✅ 100% | — |
| CAPA / QMS | IMM CAPA Record | ✅ 100% | — |
| Audit Trail | IMM Audit Trail + ALE | ✅ 100% | — |
| SLA | IMM SLA Policy | ✅ 100% | — |
| **Bảo hiểm (Insurance)** | Không có | ❌ 0% | **Insurance fields/DocType** |
| **Tồn kho phụ tùng** | IMM Device Spare Part (catalog only) | ⚠️ 40% | **Inventory tracking** |
| **Training** | Không có | ❌ 0% | **Asset Training Record** |
| **Risk Assessment** | risk_classification (static) | ⚠️ 20% | **Risk Assessment form** |
| **Thanh lý (Disposal)** | lifecycle_status=Decommissioned only | ⚠️ 10% | **Asset Disposal Record** |
| **TCO / Finance** | gross_purchase_amount only | ⚠️ 20% | **TCO aggregation** |

### 5.2 Theo chuẩn quốc tế

| Chuẩn | Yêu cầu | Đáp ứng | Gap |
|---|---|---|---|
| **WHO HTM 2025** | 7-phase lifecycle tracking | ⚠️ 70% | Transfer, Training, Disposal |
| **NĐ 98/2021** | UDI, BYT registration, incident reporting | ✅ 95% | — |
| **ISO 13485:2016** | Audit trail, CAPA, Document control | ✅ 100% | — |
| **ISO/IEC 17025** | Calibration traceability, lab cert | ⚠️ 40% | Calibration WO |
| **ISO 14971** | Risk management lifecycle | ⚠️ 20% | Risk Assessment form |
| **JCI / AEAM** | Maintenance program, training records | ⚠️ 50% | Training Record |

---

## 6. Roadmap bổ sung thực thể

### Wave 1.5 — Bổ sung trong IMM-00 (ưu tiên cao)

| Task | DocType mới/sửa | Module | Sprint |
|---|---|---|---|
| Thêm insurance fields vào AC Asset | AC Asset + Insurance child table | IMM-00 | S1 |
| Tạo Asset Transfer DocType | Asset Transfer | IMM-00 | S1 |
| Thêm Service Contract DocType | Service Contract | IMM-00 | S2 |

### Wave 2 — Modules chưa build

| Module | Thực thể chính | Priority |
|---|---|---|
| **IMM-11 Calibration** | Calibration WO, Calibration Certificate, Calibration Parameter | 🔴 HIGH |
| **IMM-13 End-of-Life** | Asset Disposal Record, Trade-in Record | 🟠 MEDIUM |
| **IMM-07 Incident Management** | Expand Incident Report, Adverse Event | 🟠 MEDIUM |
| **IMM-06 Training** | Asset Training Record, Competency Matrix | 🟡 LOW |
| **IMM-15 Risk** | Asset Risk Assessment, Risk Register | 🟡 LOW |

### Wave 3 — Tích hợp

| Tích hợp | Mục tiêu | Priority |
|---|---|---|
| ERPNext Stock → Spare Parts Inventory | Real stock tracking cho phụ tùng | 🟠 MEDIUM |
| ERPNext Accounts → TCO / Depreciation | Chi phí vòng đời | 🟡 LOW |
| FHIR → Clinical integration | Liên kết thiết bị ↔ bệnh nhân | 🟡 LOW |

---

## 7. Kết luận

### Đánh giá tổng thể

AssetCore IMM-00 v3 đã xây dựng **nền tảng dữ liệu đúng và đủ** cho phần mềm quản lý vòng đời thiết bị y tế theo WHO HTM, với các điểm mạnh:

1. **Registry thiết bị (AC Asset)** — vượt ERPNext về HTM fields (UDI, GMDN, BYT, risk class, calibration status, lifecycle state machine)
2. **Governance layer** — Audit Trail SHA-256 + CAPA + ALE đáp ứng ISO 13485 đầy đủ
3. **PM/CM Operations** — IMM-08 + IMM-09 hoàn chỉnh hơn ERPNext Asset Maintenance/Repair
4. **Regulatory compliance** — NĐ98 fields native, BYT expiry alerts, Incident reporting

**Điểm yếu chính:** 3 thực thể cốt lõi còn thiếu:
- **Asset Transfer** (di chuyển thiết bị) — không có
- **Calibration Work Order** (IMM-11) — chưa build
- **Insurance tracking** — không có

### Mức độ sẵn sàng

| Tiêu chí | Mức | Ghi chú |
|---|---|---|
| Operational HTM (PM + CM + Incident + CAPA) | ✅ 95% | Sẵn sàng production |
| Regulatory compliance (NĐ98 + ISO 13485) | ✅ 90% | Cần hoàn thiện Calibration |
| Full WHO HTM lifecycle | ⚠️ 70% | Thiếu Transfer + Calibration WO + Training |
| ERPNext parity (tính năng tương đương) | ⚠️ 75% | Thiếu Movement + Insurance + Finance |
| JCI/AEAM accreditation readiness | ⚠️ 55% | Cần Training Record + Risk Assessment |

---

*Tài liệu tham khảo chính:*
- `docs/imm-00/` — IMM-00 Module Overview, Functional Specs, Technical Design
- `assetcore/assetcore/doctype/` — 31 DocType JSONs
- `erpnext/erpnext/assets/doctype/` — 16 ERPNext Asset DocTypes
- `docs/res/IMM-00_UAT_Gap_Analysis.md` — Gap analysis và UAT test cases
- `docs/res/BE_Readiness_Audit_2026-04-18.md` — Backend readiness audit
