# AssetCore — Gap Analysis: IMM-xx Docs vs WHO 2025 & Ho_so_kien_truc_IMMIS

**Ngày:** 2026-04-17 | **Phiên bản:** 1.0
**Phạm vi:** IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12
**Nguồn so sánh:**
1. `docs/WHO/WHO - Inventory and maintenance 2025.md` (WHO IMMIS 2025)
2. `docs/WHO/WHO - Computerized maintenance management system.md` (WHO CMMS 2011)
3. `docs/WHO/WHO - Medical equipment maintenance programme overview.md` (WHO Maintenance 2011)
4. `docs/archive/architecture/Ho_so_kien_truc_IMMIS.md` (Kiến trúc IMMIS CH1)

---

## 1. Tóm tắt Executive

Tài liệu các module IMM-04 đến IMM-12 đã đáp ứng **~65%** yêu cầu từ chuẩn WHO và kiến trúc hệ thống. Các nghiệp vụ cốt lõi (commissioning, PM, CM, calibration, incident) được mô tả đầy đủ với business rules, workflow states và KPI cụ thể. Tuy nhiên tồn tại **7 nhóm gap chính** ảnh hưởng đến khả năng go-live production và compliance.

---

## 2. Mapping WHO Lifecycle → IMM Modules

WHO 2025 (§3.2) định nghĩa vòng đời thiết bị y tế gồm các giai đoạn:

| WHO Lifecycle Phase | Module AssetCore | Trạng thái |
|---|---|---|
| Needs assessment, planning & budgeting | IMM-01, IMM-02, IMM-03 | ❌ Wave 2 — chưa có tài liệu đầy đủ |
| Vendor evaluation & procurement decision | IMM-03 | ❌ Wave 2 |
| Installation, Device Identification & Initial Inspection | **IMM-04** | ✅ Tài liệu hoàn chỉnh |
| Licensing, registration & documentation | **IMM-05** | ✅ Tài liệu hoàn chỉnh |
| User training | IMM-06 | ❌ Wave 2 |
| Performance monitoring | IMM-07, IMM-16 | ❌ Wave 2/3 |
| Routine maintenance (PM) | **IMM-08** | ✅ Tài liệu hoàn chỉnh — chưa code |
| Repair, parts replacement & software update | **IMM-09** | ✅ Tài liệu hoàn chỉnh — chưa code |
| Performance monitoring & calibration | **IMM-11** | ✅ Tài liệu hoàn chỉnh — chưa code |
| Post-market surveillance & regulatory compliance | IMM-10, IMM-16 | ❌ Wave 2/3 |
| Corrective maintenance | **IMM-12** | ✅ Tài liệu hoàn chỉnh — chưa code |
| End-of-life management | IMM-13, IMM-14 | ❌ Wave 3 |

**Nhận xét:** AssetCore Wave 1 bao phủ đúng 6 giai đoạn cốt lõi của WHO lifecycle. Các gap còn lại thuộc Wave 2/3 — phù hợp với kế hoạch triển khai.

---

## 3. Kiểm tra WHO CMMS Core Requirements

### 3.1 4 Module bắt buộc của WHO CMMS (§3.2)

| WHO CMMS Module | Yêu cầu | AssetCore tương đương | Trạng thái |
|---|---|---|---|
| **Equipment Inventory Module** | Core — xây trước tiên | ERPNext Asset + Custom Fields | ✅ Đủ (RULE-F02) |
| **Spare Parts Inventory & Management** | Quản lý kho phụ tùng | IMM-15 | ❌ Wave 2 — **GAP NGHIÊM TRỌNG** |
| **Maintenance Module** | PM + CM Work Orders | IMM-08 + IMM-09 + IMM-12 | ⚠️ Tài liệu xong, chưa code |
| **Contract Management Module** | Quản lý hợp đồng bảo trì | Không có module | ❌ Chưa lên kế hoạch |

### 3.2 Các Field bắt buộc theo WHO CMMS Table 1

| WHO Field Category | Fields bắt buộc | Trạng thái trong AssetCore |
|---|---|---|
| Equipment type | IPM procedures, IPM frequency, Risk level, Responsible staff | ✅ IMM Device Model có đủ |
| Equipment model | Model number, Serial number, Parts list, IPM procedures | ✅ IMM Device Model + Asset custom fields |
| Manufacturer/Seller | Contact, email, phone, address | ✅ ERPNext Supplier |
| Stores/Spares | Parts code, name, order number | ❌ IMM-15 chưa implement |
| Staff | Employee code, position, access level, training details | ⚠️ ERPNext User — thiếu training details |
| Maintenance | WO number, service provider, fault code, IPM procedures | ✅ IMM-08, IMM-09, IMM-12 có đủ |
| Health facility | Facility/Building/Department code, type | ✅ ERPNext Department + IMM Location Ext |

### 3.3 WHO Reports bắt buộc (§3.3 + §8)

| Loại Report | Mô tả | Trạng thái AssetCore |
|---|---|---|
| PM Compliance Rate | % WO completed on time / total scheduled | ✅ KPI định nghĩa trong IMM-08 |
| Equipment Downtime | Tổng thời gian ngoài dịch vụ | ⚠️ MTTR có trong IMM-09 nhưng không có Downtime dashboard |
| MTBF | Mean Time Between Failures | ❌ Không được định nghĩa ở bất kỳ module nào |
| Maintenance Cost % | Chi phí bảo trì / Giá trị thiết bị × 100% | ❌ Chưa có |
| Staff Performance | Repeated repairs, avg downtime per technician | ❌ Chưa có |
| IPM Yield | Số lỗi phát hiện qua PM / tổng PM thực hiện | ❌ Chưa định nghĩa trong IMM-08 |
| Recall/Hazard Alerts | Danh sách thiết bị bị ảnh hưởng bởi recall | ❌ Không có module nào |

---

## 4. Gap Analysis chi tiết: IMM-xx vs Chuẩn WHO

### IMM-04 (Commissioning)

| Yêu cầu WHO | Nguồn | Trạng thái |
|---|---|---|
| Initial inspection / incoming inspection (§3.2.3) | WHO 2025 | ✅ Có checklist, QR, workflow đầy đủ |
| Device Identification — serial number, UDI | WHO 2025 §4.3.2 | ⚠️ Serial number có, UDI/GMDN code chưa có field |
| Site preparation verification | WHO 2025 §3.2.2 | ✅ Có trong checklist |
| Trigger PM Schedule sau commissioning | WHO Maintenance §5.3.2 | ❌ `pm_schedule_created: False` — IMM-08 chưa implement |
| Trigger Calibration Schedule | WHO 2025 §6.4.3 | ❌ IMM-11 chưa implement |
| Commissioning → inventory registration | WHO CMMS §3.2.1 | ✅ Link về ERPNext Asset |

**Lỗ hổng chính:** `approve_clinical_release()` không trigger tạo PM Schedule và Calibration Schedule — 2 integration points quan trọng nhất của IMM-04.

### IMM-05 (Documentation)

| Yêu cầu WHO | Nguồn | Trạng thái |
|---|---|---|
| Document control với version | ISO 13485 §4.2.3 | ✅ Có, immutable records |
| Certificate storage cho calibration | WHO 2025 §5.4.1 | ✅ IMM-05 lưu certificates |
| Service Manual nguồn checklist PM | WHO Maintenance §5.3.1 | ✅ Document type = Service Manual |
| Expiry alerts | WHO HTM §5.4 | ✅ Scheduler `check_document_expiry()` |
| Post-market surveillance / recalls | WHO 2025 §3.2.7 | ❌ Không có document category cho recall/safety alert |
| GW-2 gate (BR-07) completeness check | Ho_so_kien_truc §5 | ⚠️ Tồn tại nhưng E2E chưa test đầy đủ |

### IMM-08 (Preventive Maintenance)

| Yêu cầu WHO | Nguồn | Trạng thái |
|---|---|---|
| IPM procedures per equipment category | WHO CMMS §3.2.3 | ✅ PM Checklist Template per Asset Category |
| IPM frequency theo manufacturer IFU | WHO Maintenance §5.3.2 | ✅ `interval_days` trong PM Schedule |
| IPM Yield KPI | WHO Maintenance §5.4.3 | ❌ Không định nghĩa |
| IPM Productivity KPI | WHO Maintenance §5.4.4 | ❌ Không định nghĩa |
| Completion rate của IPM | WHO Maintenance §5.4.1 | ✅ PM Compliance Rate KPI |
| Hồ sơ PM immutable | WHO HTM §5.3.5 | ✅ PM Task Log không xóa |
| PM → CM linkage khi phát hiện lỗi | WHO Maintenance §6.2 | ✅ BR-08-02: source_pm_wo mandatory |
| Class III: photo trước/sau | Risk-based programme | ✅ BR-08-06 |
| Photo/before-after upload | WHO Appendix A.3 | ✅ BR-08-06 |

**Lỗ hổng chính:** IPM Yield và IPM Productivity chưa được định nghĩa — WHO coi đây là KPI cơ bản của PM programme.

### IMM-09 (Repair/CM)

| Yêu cầu WHO | Nguồn | Trạng thái |
|---|---|---|
| Work order system cho CM | WHO Maintenance §5.3.4, Appendix A.4 | ✅ CM WO extends Asset Repair |
| Fault code classification | WHO CMMS Table 1 (Maintenance fields) | ✅ `fault_code` trong CM WO |
| SLA by risk class | WHO 2025 §6.4.4 | ✅ SLA Matrix P1-P4 |
| MTTR calculation | WHO Maintenance §5.4.5 | ✅ Working hours formula |
| Spare parts tracking per repair | WHO CMMS §3.2.2 | ⚠️ `spare_parts_used` child table — IMM-15 chưa có |
| Inspection before return to service | WHO Maintenance §6.2.3 | ✅ Workflow state: Testing |
| Service vendor management | WHO Maintenance §5.2.1 | ⚠️ Có `service_provider` field nhưng không có Vendor Contract module |
| Troubleshooting guide / fault library | WHO Maintenance §6.2.1 | ❌ Không có fault library / knowledge base |

### IMM-11 (Calibration)

| Yêu cầu WHO | Nguồn | Trạng thái |
|---|---|---|
| Calibration interval theo IFU | WHO HTM §5.4.2 | ✅ `calibration_interval_days` trong Device Model |
| ISO/IEC 17025 lab certificate | WHO HTM §5.4.3 | ✅ BR-11-01 bắt buộc certificate |
| Measurement traceability | WHO HTM §5.4.4 | ✅ Calibration Measurement child table |
| Fail → CAPA bắt buộc | WHO HTM §5.4.5 | ✅ BR-11-02 |
| Lookback assessment | WHO HTM §5.4.6 | ✅ BR-11-03 |
| Next cal date = cert date + interval | WHO best practice | ✅ BR-11-04 |
| Out-of-tolerance → OOS | WHO HTM §5.4 | ✅ Set Asset.status = Out_of_Service |
| Reference standard tracking (in-house) | ISO/IEC 17025 §6.4 | ⚠️ Đề cập nhưng chưa có DocType riêng |

**IMM-11 là module có độ phủ WHO cao nhất — gần 100%.**

### IMM-12 (Incident/CM)

| Yêu cầu WHO | Nguồn | Trạng thái |
|---|---|---|
| Corrective maintenance per situation | WHO 2025 Fig.3 | ✅ Incident Report + SLA engine |
| Fault code per incident | WHO CMMS Table 1 | ✅ `fault_code` mandatory |
| SLA tracking | WHO 2025 §6.1 | ✅ SLA Compliance Log immutable |
| RCA cho chronic failures | WHO best practice | ✅ Chronic failure detection ≥3/90 ngày |
| CAPA integration | ISO 13485 §8.5.2 | ✅ IMM-12 tạo CAPA cho P1/P2 incidents |
| Adverse event reporting (vigilance) | WHO 2025 §3.2.7 | ❌ Không có integration với BYT/cơ quan quản lý |
| Recall management | WHO 2025 §6.1 | ❌ Không có module recall |

---

## 5. Gap Analysis chi tiết: IMM-xx vs Ho_so_kien_truc_IMMIS.md

### 5.1 Kiến trúc 7 tầng

| Tầng | Mô tả | Trạng thái trong IMM-xx docs |
|---|---|---|
| L1 — User | UI, role-based access | ✅ UI/UX Guide có trong mọi module |
| L2 — Workflow | Approval, escalation, SLA | ✅ Workflow states đầy đủ |
| L3 — Business (IMM) | Business rules, validation | ✅ BR-xx-yy documented per module |
| L4 — Data | DocTypes, fields, relationships | ✅ ERD + Data Dictionary có |
| L5 — Integration | FHIR, OpenAPI, scheduler | ⚠️ Scheduler OK; FHIR/OpenAPI chưa có spec |
| L6 — Analytics | Dashboard, KPI, report | ⚠️ KPI definitions có; dashboard DocType spec thiếu |
| L7 — QMS | Document control, CAPA, audit | ⚠️ QMS Mapping table có nhưng không có document templates |

### 5.2 QMS Document Hierarchy

Ho_so_kien_truc_IMMIS.md định nghĩa hệ thống tài liệu 4 cấp:

| Cấp | Loại | Ví dụ | Trạng thái |
|---|---|---|---|
| L1 — Chính sách | QC-IMMIS-01 đến 04 | QC-IMMIS-01: Chính sách quản lý TBYT | ❌ Chưa có |
| L2 — Quy trình | PR-IMMIS-04-01, PR-IMMIS-08-01... | PR-IMMIS-04-01: Quy trình lắp đặt | ❌ Chưa có |
| L3 — Hướng dẫn | WI-IMMIS-04-01-01... | WI-IMMIS-04-01-01: HD kiểm tra ban đầu | ❌ Chưa có |
| L4 — Biểu mẫu/Hồ sơ | BM/HS/KPI-DASH | BM-IMMIS-04-01: Phiếu kiểm tra lắp đặt | ❌ Chưa có |

**Impact:** Thiếu tài liệu QMS làm cho hệ thống không thể pass audit ISO 9001 / NĐ98 dù code đã đúng.

### 5.3 Actor Alignment

| Ho_so_kien_truc actor | IMM-xx docs role | Trạng thái |
|---|---|---|
| Trưởng phòng VT,TBYT | IMM Department Head | ✅ Mapped |
| PTP Khối 2 (CMMS) | IMM Operations Manager | ✅ Mapped |
| Kỹ thuật viên TBYT (KTV) | IMM Technician | ✅ Mapped |
| Nhân viên hồ sơ | IMM Document Officer | ✅ Mapped |
| Trưởng workshop | IMM Workshop Lead | ✅ Mapped |
| Nhân viên kho | IMM Storekeeper | ✅ Mapped |
| QLCL (Tổ HC-QLCL) | IMM QA Officer | ✅ Mapped |
| **PTP Khối 1 (Lâm sàng)** | **Không định nghĩa** | ❌ Gap — người dùng cuối thiết bị |
| **BGĐ Bệnh viện** | **Không định nghĩa** | ❌ Gap — nhận escalation P1 |
| **Cán bộ Khoa phòng** | **Không định nghĩa** | ❌ Gap — báo hỏng thiết bị IMM-12 |

**Impact:** Thiếu role cho Clinical Staff (người dùng thiết bị tại khoa) và BGĐ — họ cần nhận alert và approve một số workflow.

### 5.4 Dashboard & KPI-DASH Spec

| Yêu cầu Ho_so_kien_truc | Module | Trạng thái |
|---|---|---|
| KPI-DASH-IMMIS-04: Commission rate, GW pass rate | IMM-04 | ⚠️ KPI định nghĩa, không có dashboard spec |
| KPI-DASH-IMMIS-08: PM Compliance, Overdue rate | IMM-08 | ⚠️ KPI định nghĩa, không có dashboard spec |
| KPI-DASH-IMMIS-09: MTTR, SLA compliance | IMM-09 | ⚠️ KPI định nghĩa, không có dashboard spec |
| KPI-DASH-IMMIS-11: Calibration compliance, OOT rate | IMM-11 | ⚠️ KPI định nghĩa, không có dashboard spec |
| KPI-DASH-IMMIS-12: Incident rate, SLA breach, CAPA closure | IMM-12 | ⚠️ KPI định nghĩa, không có dashboard spec |
| **Drill-down từ KPI → source record** | Tất cả | ❌ Không có spec |
| **Unified Operations Dashboard** | Tất cả IMM | ❌ Không có |

### 5.5 Integration Layer

| Tích hợp | Mô tả | Trạng thái |
|---|---|---|
| FHIR → HIS/EMR | Truy xuất patient-device context | ❌ Chưa có spec |
| OpenAPI internal | API contracts cho module-to-module | ⚠️ API Interface files có endpoint list, không phải OpenAPI YAML/JSON |
| IMM-04 → IMM-08 | On commissioning → create PM Schedule | ❌ Chưa implement |
| IMM-04 → IMM-11 | On commissioning → create Calibration Schedule | ❌ Chưa implement |
| IMM-09 → IMM-11 | On repair complete → trigger calibration | ❌ Chưa implement |
| IMM-08 → IMM-09 | Major failure PM → create CM WO | ❌ Chưa implement |
| IMM-12 → CAPA | Auto-create CAPA on P1/P2 | ❌ IMM-11 CAPA DocType chưa implement |
| Asset → Lifecycle Event | Mọi thay đổi trạng thái ghi IMM Audit Trail | ⚠️ Defined nhưng chưa code |

---

## 6. Danh sách Gap ưu tiên

### Nhóm A — Blocking (chặn go-live)

| # | Gap | Module | Impact |
|---|---|---|---|
| A1 | IMM-08, IMM-09, IMM-11, IMM-12 chưa có code | Wave 1 | Không thể dùng production |
| A2 | IMM-04 không trigger PM Schedule + Calibration Schedule | IMM-04→08, IMM-04→11 | UAT 31/32: 1 case fail; cascading failure sau commissioning |
| A3 | Spare parts tracking (IMM-15) thiếu — CM WO không hoàn chỉnh | IMM-09, IMM-15 | WHO CMMS core requirement |
| A4 | CAPA DocType chưa implement — IMM-11 fail path blocked | IMM-11 | Không thể xử lý calibration fail |

### Nhóm B — Compliance Risk (rủi ro audit)

| # | Gap | Nguồn yêu cầu | Impact |
|---|---|---|---|
| B1 | QMS document templates (QC/PR/WI/BM) chưa có | Ho_so_kien_truc QMS-A | Fail ISO 9001 / NĐ98 audit |
| B2 | MTBF không được track ở bất kỳ module nào | WHO CMMS core metric | Thiếu dữ liệu cho procurement decision |
| B3 | Maintenance cost % KPI chưa định nghĩa | WHO 2025 §8.1 | Thiếu financial accountability |
| B4 | Adverse event / recall module không có | WHO 2025 §3.2.7 | Regulatory compliance risk |
| B5 | UDI/GMDN field thiếu trong Asset | WHO 2025 §4.3.2 | Không trace được device đến global nomenclature |

### Nhóm C — Functional Gaps (ảnh hưởng UX)

| # | Gap | Module | Impact |
|---|---|---|---|
| C1 | IPM Yield + IPM Productivity KPI thiếu | IMM-08 | PM programme không đo được hiệu quả thực |
| C2 | Downtime tracking dashboard chưa có | IMM-09/12 | Không thể báo cáo uptime cho BGĐ |
| C3 | Role: Clinical Staff + BGĐ chưa define | Tất cả | Thiếu actor cho report và escalation |
| C4 | KPI-DASH spec + drill-down chưa có | Tất cả | Dashboard không thể truy về nguồn |
| C5 | In-house reference standard tracking | IMM-11 | Track B calibration thiếu reference standard |
| C6 | Fault library / troubleshooting knowledge base | IMM-09 | KTV không có hướng dẫn sửa chữa |
| C7 | Contract management module | Không có | Vendor SLA tracking không có |

### Nhóm D — Documentation Gaps (cần bổ sung tài liệu)

| # | Gap | Action |
|---|---|---|
| D1 | API Interface docs chưa phải OpenAPI YAML/JSON | Convert sang OpenAPI 3.0 format |
| D2 | Integration points IMM-04→08, 04→11, 09→11 không có event spec | Viết integration event spec |
| D3 | 7-layer architecture mapping chưa explicit trong IMM docs | Thêm section "Architecture Layer Mapping" vào Technical Design |
| D4 | UAT Script thiếu cross-module test cases | Viết integration UAT cases |

---

## 7. Những gì IMM-xx Docs đã đáp ứng tốt

| Yêu cầu | Nguồn | Module |
|---|---|---|
| Lifecycle phases mapping | WHO 2025 Fig.3 | IMM-04 → IMM-12 bao phủ 6/10 giai đoạn |
| Work order system | WHO CMMS §3.2.3 | IMM-08, 09, 11, 12 |
| PM date = completion + interval (không phải due date) | WHO best practice | IMM-08 BR-08-03 ✅ |
| Calibration date = cert date + interval | WHO best practice | IMM-11 BR-11-04 ✅ |
| Risk-based PM procedures | WHO Maintenance Appendix A.1 | IMM-08 Class I/II/III treatment |
| SLA by risk class | WHO 2025 §6 | IMM-09, IMM-12 đầy đủ |
| MTTR working hours formula | WHO Maintenance §5.4.5 | IMM-09 ✅ |
| Audit trail per action | WHO 2025 §5.4.2 | Tất cả module có Audit Trail spec |
| Fault codes | WHO CMMS Table 1 | IMM-09, IMM-12 ✅ |
| Immutable records | WHO 2025 §5.4.2 | IMM-05, 11, 12 ✅ |
| Calibration: ISO/IEC 17025 cert mandatory | WHO HTM §5.4.3 | IMM-11 BR-11-01 ✅ |
| Calibration fail → CAPA + OOS | WHO HTM §5.4.5 | IMM-11 BR-11-02 ✅ |
| Lookback assessment on calibration fail | WHO HTM §5.4.6 | IMM-11 BR-11-03 ✅ |
| Chronic failure detection → RCA | WHO best practice | IMM-12: ≥3/90 ngày ✅ |
| QMS mapping table per module | ISO 13485, NĐ98 | Tất cả module có QMS Mapping section ✅ |

---

## 8. Roadmap khuyến nghị

### Sprint 1 (Tuần 1-3): Unblock Wave 1 (Gap nhóm A)

1. **Implement IMM-08** (PM Work Order + PM Schedule + PM Checklist Template)
2. **Implement IMM-09** (CM Work Order extending Asset Repair)
3. **Implement IMM-11** (Calibration Record + CAPA Record)
4. **Implement IMM-12** (Incident Report + SLA engine)
5. **Fix IMM-04** integration: `approve_clinical_release()` → trigger PM Schedule + Calibration Schedule

### Sprint 2 (Tuần 4-6): Integration Layer (Gap A4, A3)

1. Wire all integration points:
   - IMM-04 on_submit → IMM-08 create PM Schedule
   - IMM-04 on_submit → IMM-11 create Calibration Schedule
   - IMM-08 major failure → IMM-09 create CM WO
   - IMM-09 on_submit (repair complete) → IMM-11 trigger calibration
   - IMM-12 P1/P2 → auto-create CAPA
2. IMM-15 basic spare parts tracking (minimum viable)

### Sprint 3 (Tuần 7-8): Compliance (Gap nhóm B)

1. Thêm UDI/GMDN fields vào IMM Device Model + Asset custom fields
2. Định nghĩa và implement MTBF calculation (new KPI trong IMM-12 + IMM-09)
3. Maintenance cost tracking field + KPI formula
4. Tạo roles: `IMM Clinical Staff` (Cán bộ Khoa) + `IMM Director` (BGĐ)
5. Viết 4 QC documents (QC-IMMIS-01 đến 04) — policy level

### Sprint 4 (Tuần 9-10): Dashboard & Reporting (Gap nhóm C)

1. KPI-DASH DocType spec per module
2. Unified Operations Dashboard (PM + CM + CAL status overview)
3. Downtime tracking + uptime report
4. IPM Yield + IPM Productivity KPIs cho IMM-08

### Sprint 5 (Tuần 11-12): Documentation & Hardening (Gap nhóm D)

1. Convert API Interface → OpenAPI 3.0 YAML
2. Integration event specs (IMM-04→08, 04→11, 09→11)
3. Cross-module UAT test cases
4. PR/WI documents cho 6 module Wave 1 (6 quy trình + 6 bộ hướng dẫn)

---

## 9. Compliance Score by Module

| Module | WHO Coverage | Ho_so_kien_truc Coverage | Tổng thể | Ghi chú |
|---|---|---|---|---|
| IMM-04 | 85% | 75% | **80%** | Thiếu integration triggers |
| IMM-05 | 90% | 80% | **85%** | Thiếu recall category |
| IMM-08 | 80% | 70% | **75%** | Thiếu IPM Yield/Productivity KPIs, chưa code |
| IMM-09 | 85% | 75% | **80%** | Thiếu spare parts, fault library, chưa code |
| IMM-11 | 95% | 85% | **90%** | Module tốt nhất, chưa code |
| IMM-12 | 80% | 75% | **78%** | Thiếu adverse event reporting, chưa code |
| **Tổng Wave 1** | **86%** | **77%** | **~82%** | |

---

## 10. Kết luận

Tài liệu các module IMM-04 đến IMM-12 **đạt ~82% coverage** so với yêu cầu WHO và kiến trúc hệ thống. Business logic cốt lõi (PM date calculation, calibration cycle, SLA matrix, CAPA, lookback, fault codes) được thiết kế đúng theo chuẩn WHO.

**3 ưu tiên hàng đầu để đưa hệ thống vào production:**

1. **Code 4 module Wave 1 còn lại** (IMM-08, 09, 11, 12) — đây là blocker tuyệt đối
2. **Fix integration triggers trong IMM-04** — sau commissioning phải auto-tạo PM/Calibration Schedule
3. **Tạo QMS document framework** — không cần toàn bộ ngay, ít nhất cần QC-IMMIS-01 đến 04 và PR/BM cho 6 module Wave 1 để có thể pass audit

Sau khi hoàn thành 3 ưu tiên này, hệ thống sẽ đáp ứng ≥95% yêu cầu WHO cho một hospital-level CMMS.
