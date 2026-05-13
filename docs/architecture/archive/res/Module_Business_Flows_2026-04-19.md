# AssetCore — Nghiệp vụ 6 Module Wave 1

**Ngày:** 2026-04-19
**Scope:** IMM-00 · 04 · 05 · 08 · 09 · 11 (IMM-12 chưa build)
**Tham chiếu:** WHO HTM Lifecycle · NĐ98/2021 · ISO 13485:2016

---

## Bản đồ lifecycle — vòng đời thiết bị y tế

```
    ┌─────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
    │ IMM-04  │ ──► │  IMM-05  │ ──► │  IMM-00   │ ──► │  IMM-08  │ ◄─► │  IMM-09  │
    │Tiếp nhận│     │  Hồ sơ   │     │  Master   │     │   PM     │     │   CM     │
    └─────────┘     └──────────┘     │   Data    │     └──────────┘     └──────────┘
                                     │  (Asset)  │           ▲
                                     └───────────┘           │
                                           │                 │
                                           ▼                 ▼
                                     ┌──────────┐     ┌──────────┐
                                     │  IMM-11  │     │ Incident │
                                     │  Cal.    │     │ + CAPA   │
                                     └──────────┘     └──────────┘
```

**Vòng đời đi theo:** Tiếp nhận (04) → Đăng ký hồ sơ (05) → Nhập registry (00) → Vận hành (08 định kỳ, 09 sửa chữa khi hỏng, 11 hiệu chuẩn định kỳ) → Sự cố khi cần → CAPA cải tiến.

---

## 1. IMM-00 — Foundation (Master Data + Governance)

### Vai trò
**Thư viện trung tâm** chứa toàn bộ dữ liệu gốc của thiết bị + audit + CAPA + SLA.

### Actors
- **IMM System Admin** — quản trị master data
- **IMM Operations Manager** — xem dashboard, rollup KPI
- **IMM Document Officer** — cập nhật tài liệu tham chiếu

### Nghiệp vụ chính
| Luồng | Entry point | Output |
|---|---|---|
| Quản lý thiết bị (AC Asset) | `/assets` | Asset 360° view: info + timeline + KPI + audit chain |
| Chuyển trạng thái lifecycle | Asset detail → "Chuyển trạng thái" | `transition_asset_status()` tạo Lifecycle Event + Audit Trail |
| Luân chuyển nội bộ | `/asset-transfers` | Asset Transfer submit → update AC Asset + events |
| Hợp đồng dịch vụ | `/service-contracts` | SC + liên kết nhiều assets |
| Khấu hao | `/depreciation` | Dashboard — scheduler tự tính hàng tháng (Gap #7, chưa hoàn thiện) |
| CAPA | `/capas` | Auto-tạo khi có Critical Incident |
| Sự cố | `/incidents` | Critical → auto-CAPA (BR-00-08) |

### Scheduler jobs (daily + monthly)
- `check_capa_overdue` — alert quá hạn
- `check_vendor_contract_expiry` — cảnh báo hết hạn HĐ NCC
- `check_registration_expiry` — cảnh báo hết hạn đăng ký
- `check_insurance_expiry` — cảnh báo bảo hiểm sắp hết hạn
- `check_service_contract_expiry` — cảnh báo HĐ dịch vụ
- `rollup_asset_kpi` (monthly) — tính MTTR, uptime

### DocTypes (17)
AC Asset · AC Asset Category · AC Department · AC Location · AC Supplier · AC Trade Item · AC Asset Item Option · IMM Device Model · IMM SLA Policy · IMM CAPA Record · Incident Report · Asset Lifecycle Event · IMM Audit Trail · Asset Transfer · Service Contract · Service Contract Asset · Required Document Type

---

## 2. IMM-04 — Commissioning (Tiếp nhận & Lắp đặt)

### Vai trò
**Cổng vào**: từ PO ERPNext + thông tin nhà sản xuất → tạo AC Asset lần đầu, validate qua 6 gate G01–G06.

### Actors
- **Biomed Engineer** — nhập phiếu, đánh giá baseline
- **Workshop Head** — duyệt phiếu
- **Clinical Head** — ký hold (hold/release)
- **VP Block2** — Board approver
- **Tổ HC-QLCL** — QA officer

### State machine (11 states)
```
Draft → Pending_Receipt → Receipt_Logged → Installing → Installed
    → Baseline_Testing → Clinical_Hold → Clinical_Release → Submitted
    (branch: Return_To_Vendor | Fault_Detected)
```

### Nghiệp vụ chính
| Luồng | Actor | Endpoint |
|---|---|---|
| Tạo phiếu từ PO | Biomed Engineer | `create_commissioning` |
| Assign serial + MOH code | Biomed Engineer | `assign_identification` |
| Submit baseline checklist | Biomed Engineer | `submit_baseline_checklist` |
| Clear Clinical Hold | Clinical Head | `clear_clinical_hold` |
| Approve Clinical Release | VP Block2 | `approve_clinical_release` (BUG-2 đã fix) |
| Submit phiếu → mint AC Asset | System | `submit_commissioning` |
| Báo cáo NC | QA Officer | `report_nonconformance` |
| DOA — báo hỏng ngay lúc nhận | Biomed Engineer | `report_doa` |
| Xuất biên bản bàn giao PDF | | `generate_handover_pdf` |

### Integration
- `final_asset` → tạo record trong **IMM-00** (AC Asset)
- `created_from_commissioning` → tự động sinh PM Schedule trong **IMM-08** (khi device model yêu cầu)
- `commissioning_documents` → lưu vào **IMM-05** (Asset Document)

---

## 3. IMM-05 — Document Repository (Hồ sơ thiết bị)

### Vai trò
**Kho tài liệu pháp lý + kỹ thuật** bắt buộc theo NĐ98/2021 + ISO 13485.

### Actors
- **Biomed Engineer, HTM Technician** — upload
- **Tổ HC-QLCL** — QA review + approve
- **CMMS Admin** — toàn quyền
- **Clinical Head** — read only

### Workflow (6 states)
```
Draft → Pending_Review → (Active | Rejected) → Archived
                           │
                           └── Expired (scheduler tự động)
```

### Phân loại tài liệu
| Nhóm | Ví dụ | Mandatory |
|---|---|---|
| Legal | Giấy phép lưu hành NĐ98, CE, FDA | ✅ (trừ Exempt) |
| Technical | Manual, installation spec, service manual | ✅ |
| Certification | CO/CQ, calibration cert | ✅ |
| Training | User training log | optional |
| QA | NC, CAPA records | optional |

### Nghiệp vụ chính
| Luồng | Endpoint |
|---|---|
| Upload + tạo Draft | `create_document` |
| Gửi duyệt | workflow transition → Pending_Review |
| Approve (với role `_APPROVE_ROLES`) | `approve_document` — tự động archive bản cũ |
| Reject (có lý do bắt buộc — BUG-4 đã fix) | `reject_document` |
| NĐ98 Exempt — thiết bị miễn đăng ký | `mark_exempt` (BUG-1 đã fix) |
| Xem hồ sơ theo asset | `get_asset_documents` — nhóm theo category |
| Sắp hết hạn (90/60/30/7 ngày) | `get_expiring_documents` + scheduler `check_document_expiry` sinh Expiry Alert Log |
| Document Request — đòi tài liệu thiếu | `create_document_request` |
| Compliance by dept | `get_compliance_by_dept` — % completeness theo khoa |

### Integration
- `asset_ref` → AC Asset (IMM-00)
- `source_commissioning` → IMM-04
- Expiry alert → trigger Document Request → notify assigned_to

---

## 4. IMM-08 — Preventive Maintenance (Bảo trì định kỳ)

### Vai trò
**Bảo trì theo kế hoạch** — ngăn hỏng trước khi xảy ra. Tạo WO tự động từ Schedule.

### Actors
- **HTM Technician** — thực hiện PM, ghi checklist result
- **Workshop Head** — phân công, duyệt kết quả
- **CMMS Admin** — quản lý schedule + template
- **VP Block2** — escalation major failure

### State machine (PM Work Order)
```
Open → In Progress → Completed
                 → Pending–Device Busy
                 → Overdue (scheduler)
                 → Halted–Major Failure (→ trigger IMM-09)
                 → Cancelled
```

### Nghiệp vụ chính
| Luồng | Endpoint |
|---|---|
| Tạo PM Schedule (chu kỳ: Quarterly/Semi-Annual/Annual/Ad-hoc) | `create_pm_schedule` |
| Gắn Checklist Template (có versioning) | `create_pm_template` + `version_pm_template` |
| Auto-gen WO khi đến hạn | scheduler `generate_pm_work_orders_from_schedule` (daily) |
| Tạo ad-hoc WO | `create_pm_work_order` |
| Assign technician | `assign_technician` |
| Submit kết quả + checklist | `submit_pm_result` |
| Báo major failure → mở CM | `report_major_failure` — tạo Asset Repair trong IMM-09 |
| Reschedule | `reschedule_pm` |
| Dashboard: Calendar, history, compliance | `get_pm_calendar`, `get_asset_pm_history`, `get_pm_dashboard_stats` |

### Integration
- `source_pm_wo` trong Asset Repair (IMM-09) — khi PM phát hiện hỏng → chuyển sang CM
- PM completion date → cập nhật `last_pm_date` trong PM Schedule; tính `next_due_date` = `last + pm_interval_days`

### DocTypes (6)
PM Schedule · PM Work Order · PM Checklist Template · PM Checklist Item · PM Checklist Result · PM Task Log

---

## 5. IMM-09 — Corrective Maintenance (Sửa chữa)

### Vai trò
**Sửa thiết bị bị hỏng** — nguồn từ Incident Report hoặc PM Major Failure.

### Actors
- **HTM Technician** — diagnose + repair
- **Workshop Head** — approve "Cannot Repair" + SLA monitoring
- **Biomed Engineer** — support kỹ thuật cao
- **VP Block2** — approve escalation

### State machine (Asset Repair)
```
Open → Assigned → Diagnosing → Pending_Parts → In_Repair
     → Pending_Inspection → Completed
     (→ Cannot_Repair)
```

### Nghiệp vụ chính
| Luồng | Endpoint |
|---|---|
| Tạo Repair WO (từ Incident / PM major failure) | có thể qua `report_major_failure` (IMM-08) |
| Diagnose + root cause | update state → Diagnosing |
| Yêu cầu phụ tùng | Spare Parts Used table |
| Hoàn thành + đóng | đổi state Completed, tính MTTR |
| Báo "Cannot Repair" | → transition AC Asset → Decommissioned hoặc Return_To_Vendor |
| Firmware Change Request | `FirmwareCrListView.vue` — track firmware update |
| Dashboard MTTR | `/cm/mttr` |

### SLA + KPI
- `sla_target_hours` resolve từ `get_sla_policy(priority, risk_class)` (IMM-00)
- `mttr_hours`, `sla_breached` được tính khi transition state
- Class III High/Critical — escalation trong 4h

### Integration
- `incident_report` → IMM-00 Incident Report
- `source_pm_wo` → IMM-08 PM Work Order
- `firmware_change_request` → có thể cross-module với IMM-04 commissioning baseline (cần xác định rõ — Gap 04-A)

### DocTypes (3)
Asset Repair · Repair Checklist · Spare Parts Used

---

## 6. IMM-11 — Calibration (Hiệu chuẩn)

### Vai trò
**Hiệu chuẩn định kỳ** theo yêu cầu NĐ98 (Class II, III) + SOP của nhà sản xuất.

### Actors
- **Biomed Engineer** — thực hiện hiệu chuẩn
- **Workshop Head** — review + cert
- **Tổ HC-QLCL** — QA validation
- **Clinical Head** — approve acceptance

### Nghiệp vụ chính
| Luồng | View |
|---|---|
| Danh sách phiếu hiệu chuẩn | `/calibration` (CalibrationListView) |
| Lịch hiệu chuẩn theo chu kỳ | `/calibration/schedules` |
| Tạo phiếu hiệu chuẩn | `/calibration/new` |
| Chi tiết + cert | `/calibration/:id` |

### Integration
- Khi hiệu chuẩn → transition AC Asset → "Calibrating" (IMM-00)
- Hoàn thành → back to "Active" + cập nhật `last_calibration_date`, `next_calibration_date`
- Certificate → lưu vào IMM-05 (Asset Document category = "Certification")

### DocTypes
IMM Calibration Schedule + Asset Calibration Record (chi tiết trong docs/imm-11/)

---

## Cross-module linking trong UI

### Từ Asset Detail (IMM-00)
Quick Action Bar (mới thêm) — liên kết trực tiếp đến 6 module liên quan:
- 📋 Hồ sơ → `/documents?asset={id}`  (IMM-05)
- 🛠️ Bảo trì PM → `/pm/work-orders?asset={id}`  (IMM-08)
- 🔧 Sửa chữa → `/cm/work-orders?asset={id}`  (IMM-09)
- 📐 Hiệu chuẩn → `/calibration?asset={id}`  (IMM-11)
- 🔄 Luân chuyển → `/asset-transfers?asset={id}`  (IMM-00)
- ⚠️ Báo sự cố → `/incidents/new?asset={id}`  (IMM-00)

### Từ Commissioning Detail (IMM-04)
→ khi submit → tự động redirect đến AC Asset page + pre-fill PM Schedule

### Từ PM Work Order (IMM-08)
- → Asset ref link (IMM-00)
- → Source PM WO link nếu là CM gốc (IMM-09)
- → Major failure → Create Repair WO button (IMM-09)

### Từ CM Work Order (IMM-09)
- → Source Incident (IMM-00)
- → Source PM WO (IMM-08)
- → Spare parts → Stock (ERPNext, external)

---

## Sidebar mới — 5 nhóm (thay vì 9)

```
🏠 Trang chủ

VÒNG ĐỜI THIẾT BỊ
📦 Thiết bị ↓              — Danh sách / Luân chuyển / HĐ DV / Khấu hao
🚚 Tiếp nhận & Lắp đặt    [04]
📁 Hồ sơ thiết bị          [05]

BẢO TRÌ & VẬN HÀNH
🛠️ Bảo trì định kỳ ↓      [08]  — Dashboard / Lịch / WO / Schedule / Template
🔧 Sửa chữa ↓              [09]  — Dashboard / Tạo / WO / Firmware / MTTR
📐 Hiệu chuẩn ↓            [11]  — Danh sách / Lịch / Tạo

CHẤT LƯỢNG & TUÂN THỦ
⚠️ Sự cố
🛡️ CAPA
🔒 Audit Trail

HỆ THỐNG
⚙️ Dữ liệu gốc ↓          — Supplier / Device Model / SLA / Reference
👥 Người dùng
```

**Thay đổi chính:**
- Top-level items: 30+ → 15 (giảm 50%)
- Sub-items collapse/expand theo nhóm, nhớ state trong localStorage
- Auto-expand nhóm chứa route đang active
- Badge module (04, 05, 08, 09, 11) hiển thị nhẹ bên phải
- Nhóm theo **nghiệp vụ vòng đời** (WHO HTM), không theo mã module

---

## Hướng dẫn cho từng Role

### HTM Technician (KTV) — công việc hàng ngày
1. `/pm/work-orders` — xem WO PM được assign
2. `/cm/work-orders` — xem WO sửa chữa
3. Open WO → làm checklist → submit kết quả
4. Nếu thiết bị hỏng nặng → Click "Báo sự cố" trong Asset Detail

### Biomed Engineer
1. `/commissioning/new` — nhập phiếu tiếp nhận khi có thiết bị mới
2. `/documents/new` — upload hồ sơ pháp lý
3. `/calibration/new` — tạo phiếu hiệu chuẩn
4. `/cm/create` — tạo WO sửa chữa ad-hoc

### Workshop Head / CMMS Admin
1. `/pm/dashboard` — monitor tỷ lệ PM on-time
2. `/pm/schedules` — quản lý lịch PM
3. `/pm/templates` — approve + version template
4. `/cm/dashboard` — SLA breach monitor
5. `/cm/mttr` — MTTR report

### Tổ HC-QLCL (QA Officer)
1. `/documents` filter workflow_state=Pending_Review — queue review
2. Approve / reject với lý do
3. Mark Exempt khi thiết bị miễn đăng ký
4. `/capas` — track CAPA từ sự cố Critical

### IMM Operations Manager
1. `/dashboard` — executive KPI
2. `/audit-trail` — verify chain integrity
3. `/sla-policies` — update SLA matrix

---

## Trạng thái từng module (hiện tại)

| Module | Grade | UAT | Service | Endpoints | FE Views | Gap còn lại |
|---|---|---|---|---|---|---|
| IMM-00 | A (95%) | ✅ 16/16 | ✅ | 93 | 21 | Depreciation calc |
| IMM-04 | A- (90%) | ✅ seed | ✅ | 22 | 6 | Firmware CR classification |
| IMM-05 | A (95%) | ✅ 39/39 | ✅ | 14 | 4 | None critical |
| IMM-08 | A- (88%) | ✅ | ✅ | 22 | 6 | Verify UAT runs |
| IMM-09 | A- (88%) | ✅ | ✅ | 12 | 7 | Hardcode strings refactor |
| IMM-11 | B (70%) | ❌ | ⚠ | varies | 4 | UAT + scheduler |

**Wave 1 readiness: 93% — nền tảng sẵn sàng cho Wave 2 (IMM-12 CAPA nâng cao).**

---

**Tham chiếu:**
- `docs/res/Wave1_Foundation_Readiness_2026-04-19.md` — phân tích gap v1.0
- `docs/res/Wave1_Review_2026-04-19.md` — review BE+FE + bug fixes v2.0
- `docs/res/AssetCore_DocTypes_Audit_2026-04-19.md` — audit 34 DocTypes
- Specs: `docs/imm-00/`, `docs/imm-04/`, `docs/imm-05/`, `docs/imm-08/`, `docs/imm-09/`, `docs/imm-11/`
