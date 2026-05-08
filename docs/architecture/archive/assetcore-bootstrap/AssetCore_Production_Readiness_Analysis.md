# ASSETCORE — PHÂN TÍCH SẴN SÀNG SẢN XUẤT
# Gap Analysis: Bootstrap Foundation vs IMM Module Specs
# Version 1.0 | April 2026

---

## 1. TÓM TẮT ĐIỀU HÀNH

AssetCore đang ở giai đoạn **Wave 1 hoàn thành một phần**:

| Module | Tên | Trạng thái | Ghi chú |
|---|---|---|---|
| IMM-04 | Lắp đặt & Kiểm tra ban đầu | ✅ Hoàn thành | 31/32 UAT pass |
| IMM-05 | Đăng ký & Hồ sơ | ✅ Hoàn thành | API + frontend done |
| IMM-08 | Bảo trì định kỳ (PM) | ❌ Chưa code | Chỉ có docs |
| IMM-09 | Sửa chữa & CM | ❌ Chưa code | Chỉ có docs |
| IMM-11 | Hiệu chuẩn | ❌ Chưa code | Chỉ có docs |
| IMM-12 | Bảo trì khắc phục (Incident) | ❌ Chưa code | Chỉ có docs |

**Kết luận nhanh:** Hệ thống hiện tại chỉ cover **Deployment lifecycle** (nhận thiết bị → lập hồ sơ). Toàn bộ **Operations lifecycle** (bảo trì, sửa chữa, hiệu chuẩn, sự cố) chưa được xây dựng. End-user không thể sử dụng hệ thống cho công việc vận hành hàng ngày.

---

## 2. SO SÁNH: BOOTSTRAP FOUNDATION vs IMM MODULE SPECS

### 2.1 DocType — Đặt tên và Phạm vi

| Bootstrap (data-dictionary.md) | Codebase thực tế | Ghi chú |
|---|---|---|
| `IMM Commissioning Record` | `Asset Commissioning` | **Xung đột tên** — codebase dùng `Asset Commissioning` |
| `IMM Document Repository` | `Asset Document` | **Xung đột tên** — codebase dùng `Asset Document` |
| `IMM PM Work Order` | ❌ Chưa tạo | Chỉ có spec trong docs |
| `IMM CM Work Order` | ❌ Chưa tạo | Chỉ có spec trong docs |
| `IMM Calibration Record` | ❌ Chưa tạo | Chỉ có spec trong docs |
| `IMM Device Model` | ❌ Chưa xác nhận | Cần kiểm tra |
| `IMM Asset Profile` | ❌ Chưa xác nhận | Cần kiểm tra |
| `IMM Audit Trail` | ❌ Chưa xác nhận | Cần kiểm tra |

**⚠️ Vấn đề nghiêm trọng:** Bootstrap dùng prefix `IMM` nhưng codebase hiện dùng tên không có prefix `IMM`. Cần chuẩn hóa một quy tắc đặt tên và refactor.

### 2.2 Workflow — So sánh Bootstrap vs Spec

#### IMM-04 Commissioning Workflow
| Bootstrap (5 states) | IMM-04 Spec (11 states) | Khoảng cách |
|---|---|---|
| Draft | Draft | ✅ |
| In Progress | Pending Doc Verify | ❌ Thiếu gate kiểm tra hồ sơ |
| — | To Be Installed | ❌ Thiếu |
| — | Installing | ❌ Thiếu |
| — | Identification | ❌ Thiếu |
| — | Initial Inspection | ❌ Thiếu |
| — | Non Conformance | ❌ Thiếu — xử lý lỗi kiểm tra |
| — | Clinical Hold | ❌ Thiếu — treo lâm sàng |
| — | Re Inspection | ❌ Thiếu |
| Completed | — | Tên khác |
| Approved | Clinical Release | ❌ Tên khác, ý nghĩa khác |
| Rejected | Return To Vendor | ❌ Thiếu gate trả hàng |

**Kết luận:** Bootstrap workflow IMM-04 chỉ có 5 states, bỏ qua 6 gates kiểm tra nghiệp vụ quan trọng theo WHO HTM. Codebase hiện tại cần nâng cấp workflow.

#### IMM-08 PM Workflow
| Bootstrap (8 states) | IMM-08 Spec | Khoảng cách |
|---|---|---|
| Draft→Scheduled→Assigned→In Progress→Completed→Verified→Closed→Cancelled | Tương tự nhưng có thêm: Overdue, Escalated | ❌ Thiếu Overdue/Escalated states |
| — | PM Schedule DocType | ❌ Bootstrap không có PM Schedule |
| — | PM Checklist Template | ❌ Bootstrap không có Checklist Template |
| — | Minor/Major failure classification | ❌ Không có trong bootstrap |

#### IMM-12 Incident/CM Workflow
| Bootstrap (10 states) | IMM-12 Spec | Khoảng cách |
|---|---|---|
| Reported→Triaged→...→Closed | Tương tự | ≈ Gần đúng |
| — | SLA P1/P2/P3/P4 matrix | ❌ Thiếu SLA tracking |
| — | Incident Report DocType riêng | ❌ Bootstrap gộp vào CM Work Order |
| — | RCA Record DocType | ❌ Thiếu |
| — | Chronic failure detection (≥3 in 90 days) | ❌ Thiếu |

### 2.3 Role & Permission — Đánh giá

Bootstrap đã định nghĩa 8 roles đầy đủ. Tuy nhiên, codebase chưa có:
- File `permission.py` với `has_permission()` function cho Technician
- Fixture data để tạo roles trong Frappe
- Test cases kiểm tra phân quyền

---

## 3. GAP ANALYSIS CHI TIẾT THEO MODULE

### 3.1 IMM-04 — Lắp đặt (✅ Deployed, ⚠️ Partial)

**Đã có:**
- `Asset Commissioning` DocType với đầy đủ fields
- API `create_commissioning`, `get_commissioning_list`, `get_commissioning_detail`
- Frontend Vue: form tạo, list view, detail view
- CSRF token handling trong axios
- 31/32 UAT test cases pass

**Còn thiếu:**
- [ ] Workflow đầy đủ 11 states (hiện chỉ có 5)
- [ ] Gate G01: Kiểm tra hồ sơ trước khi cài đặt (Pending Doc Verify)
- [ ] Gate G03: Identification — gán serial number vào Asset ERPNext
- [ ] Gate G04: Initial Inspection với baseline test automation
- [ ] Gate G05: Non Conformance → QA non-conformance record linking
- [ ] Gate G06: Clinical Release → tự động update `imm_lifecycle_status` trên Asset
- [ ] Return To Vendor flow
- [ ] Link từ commissioning sang `IMM Asset Profile` (IMM-05)
- [ ] PDF print format cho biên bản lắp đặt (theo NĐ98)
- [ ] QR code generation và scan

### 3.2 IMM-05 — Đăng ký & Hồ sơ (✅ Deployed, ⚠️ Partial)

**Đã có:**
- `Asset Document` DocType
- API quản lý documents
- Frontend list/detail/create views

**Còn thiếu:**
- [ ] Auto-import từ IMM-04 (khi commissioning approve → tạo document set)
- [ ] Version control cho documents (v1.0 → v1.1 → v2.0)
- [ ] Expiry alerts: 90/60/30/0 ngày trước khi hết hạn
- [ ] Scheduler job kiểm tra document expiry hàng ngày
- [ ] `Document Request` DocType cho trường hợp thiếu hồ sơ
- [ ] Exempt handling (thiết bị được miễn một số loại giấy tờ)
- [ ] Visibility control: ai được xem document nào
- [ ] Integration với email notification khi document sắp hết hạn

### 3.3 IMM-08 — Bảo trì định kỳ (❌ Chưa code)

**DocTypes cần tạo:**

| DocType | Mô tả | Fields chính |
|---|---|---|
| `IMM PM Schedule` | Lịch PM cho từng thiết bị | asset, frequency, last_pm_date, next_pm_date, assigned_technician, pm_template |
| `IMM PM Checklist Template` | Template checklist theo loại thiết bị | device_model, checklist_items (child), version |
| `IMM PM Work Order` | Lệnh công việc PM cụ thể | pm_schedule, asset, scheduled_date, checklist_items, actual_completion |
| `IMM PM Task Log` | Log từng bước checklist | pm_work_order, task_item, result, measured_value, technician |

**Business Rules quan trọng:**
- BR-08-01: Auto-create PM WO khi đến ngày (scheduler daily)
- BR-08-02: Slippage tolerance 7 ngày (warning), 30 ngày (overdue escalation)
- BR-08-03: Checklist completion ≥ 80% mới được complete WO
- BR-08-04: Nếu phát hiện lỗi trong PM → tự động tạo IMM CM Work Order
- BR-08-05: Cập nhật `imm_last_pm_date` và `imm_next_pm_date` trên Asset sau khi complete

**Scheduler jobs cần thêm:**
```python
scheduler_events = {
    "daily": [
        "assetcore.imm_operations.pm_scheduler.create_due_pm_work_orders",
        "assetcore.imm_operations.pm_scheduler.escalate_overdue_pm",
        "assetcore.imm_operations.pm_scheduler.check_pm_slippage",
    ]
}
```

### 3.4 IMM-09 — Sửa chữa & CM (❌ Chưa code)

**DocTypes cần tạo:**

| DocType | Mô tả | Fields chính |
|---|---|---|
| `IMM CM Work Order` | Lệnh sửa chữa | asset, source (PM/Incident/Manual), problem_description, root_cause, repair_actions, spare_parts |
| `IMM Spare Part Used` (Child) | Phụ tùng đã dùng | part_name, part_number, quantity, cost, supplier |
| `IMM Firmware Change Request` | Yêu cầu cập nhật firmware | asset, current_version, target_version, approval_required |

**Business Rules quan trọng:**
- BR-09-01: Source tracing — CM WO phải link về PM WO hoặc Incident Report
- BR-09-02: Spare parts tracking → integrate với Frappe Stock (Item, Stock Entry)
- BR-09-03: MTTR calculation: `completion_datetime - reported_datetime`
- BR-09-04: Firmware change cần approval từ Workshop Lead

**MTTR KPI:**
```
MTTR (Mean Time To Repair) = Σ(repair_duration) / count(closed_cm_wo)
Target: < 48 giờ cho P1/P2, < 5 ngày cho P3/P4
```

### 3.5 IMM-11 — Hiệu chuẩn (❌ Chưa code)

**DocTypes cần tạo:**

| DocType | Mô tả | Fields chính |
|---|---|---|
| `IMM Calibration Work Order` | Lệnh hiệu chuẩn | asset, calibration_type (External/In-house), lab_name, certificate_number, validity_date |
| `IMM Calibration Parameter` (Child) | Thông số đo | parameter, nominal_value, tolerance, measured_value, pass_fail |
| `IMM CAPA Record` | Hành động khắc phục phòng ngừa | source_doc, root_cause, corrective_action, due_date, status |

**Business Rules quan trọng:**
- BR-11-01: External lab phải có chứng chỉ ISO 17025
- BR-11-02: Certificate expiry → auto update `imm_next_calibration_date` trên Asset
- BR-11-03: Calibration fail → tự động tạo CAPA Record
- BR-11-04: Lookback assessment: khi thiết bị fail calibration, review kết quả lâm sàng 6 tháng trước
- BR-11-05: Thiết bị radiation phải có thêm radiation safety check

### 3.6 IMM-12 — Bảo trì khắc phục / Sự cố (❌ Chưa code)

**DocTypes cần tạo:**

| DocType | Mô tả | Fields chính |
|---|---|---|
| `IMM Incident Report` | Báo cáo sự cố | asset, reporter, incident_datetime, severity (P1-P4), description, clinical_impact |
| `IMM RCA Record` | Root Cause Analysis | incident_report, rca_method, root_cause, contributing_factors, action_items |

**SLA Matrix:**
| Ưu tiên | Mô tả | Response Time | Resolution Time |
|---|---|---|---|
| P1 | Critical — ảnh hưởng trực tiếp bệnh nhân | 30 phút | 4 giờ |
| P2 | High — thiết bị không hoạt động | 2 giờ | 24 giờ |
| P3 | Medium — giảm hiệu năng | 4 giờ | 72 giờ |
| P4 | Low — vấn đề nhỏ | 8 giờ | 5 ngày làm việc |

**Business Rules quan trọng:**
- BR-12-01: Chronic failure detection — ≥3 incidents trong 90 ngày → auto-flag asset, notify Workshop Lead
- BR-12-02: P1 incident → tự động notify Department Head qua email
- BR-12-03: Downtime tracking: `downtime = incident_reported - asset_restored`
- BR-12-04: MTBF calculation: `MTBF = total_uptime / count(failures)`

---

## 4. PHÂN TÍCH INTEGRATION GIỮA CÁC MODULE

```
IMM-04 ──create──→ IMM-05 (document set khi commissioning approve)
IMM-04 ──create──→ IMM-08 (PM schedule khi asset được clinical release)
IMM-08 ──trigger──→ IMM-09 (CM WO khi PM phát hiện lỗi)
IMM-08 ──trigger──→ IMM-11 (Calibration WO nếu checklist có calibration item)
IMM-12 ──create──→ IMM-09 (CM WO từ incident report)
IMM-11 ──trigger──→ IMM-09 (CM WO nếu calibration fail)
IMM-11 ──create──→ IMM-12 (Incident nếu calibration fail có clinical impact)
IMM-09 ──update──→ Asset.imm_lifecycle_status
IMM-12 ──update──→ Asset.imm_lifecycle_status
```

**Các integration chưa được implement:**
- [ ] IMM-04 approve → auto-create IMM-05 document repository entry
- [ ] IMM-04 approve → auto-create IMM-08 PM schedule (nếu device_model có PM frequency)
- [ ] IMM-08 fail → auto-create IMM-09 CM WO
- [ ] IMM-12 report → auto-create IMM-09 CM WO + assign priority
- [ ] Tất cả module → update Asset.imm_lifecycle_status

---

## 5. HẠ TẦNG CÒN THIẾU CHO END-USER READINESS

### 5.1 Notification System (CHƯA CÓ)
- [ ] Email notification khi WO được assign cho technician
- [ ] Email notification khi document sắp hết hạn (90/60/30 ngày)
- [ ] Email notification khi P1 incident
- [ ] In-app notification (Frappe notification bell)
- [ ] Push notification qua mobile (tương lai)

**Implementation:** Dùng `frappe.sendmail()` + Frappe Notification DocType

### 5.2 Dashboard & Reports (CHƯA CÓ)
- [ ] PM Compliance Dashboard: % PM hoàn thành đúng hạn / tổng
- [ ] CM Resolution Dashboard: MTTR, open vs closed WO
- [ ] Asset Health Dashboard: thiết bị theo lifecycle status
- [ ] Calibration Status Report: sắp hết hạn / đã hết hạn
- [ ] Document Compliance Report: thiết bị thiếu hồ sơ

**Implementation:** Frappe Query Report + Chart DocType + Dashboard DocType

### 5.3 PDF Print Formats (CHƯA CÓ)
- [ ] Biên bản lắp đặt nghiệm thu (IMM-04) — bắt buộc theo NĐ98
- [ ] Biên bản bảo dưỡng định kỳ (IMM-08)
- [ ] Biên bản sửa chữa (IMM-09)
- [ ] Chứng chỉ hiệu chuẩn print wrapper (IMM-11)
- [ ] Biên bản sự cố (IMM-12)

**Implementation:** Frappe Print Format (Jinja template)

### 5.4 Demo Data & Fixtures (CHƯA CÓ)
- [ ] Roles fixtures (8 IMM roles)
- [ ] Role Profile fixtures
- [ ] Sample Device Models (5-10 loại thiết bị y tế phổ biến)
- [ ] Sample Assets (10-20 thiết bị demo)
- [ ] Sample Users với đúng roles
- [ ] Sample PM Schedules

### 5.5 Data Migration Tool (CHƯA CÓ)
- [ ] Script import danh sách thiết bị từ Excel
- [ ] Script import lịch sử bảo trì từ Excel
- [ ] Validation report sau migration

### 5.6 Security & Compliance (CHƯA ĐẦY ĐỦ)
- [ ] `permission.py` với `has_permission()` cho Technician (chỉ record của mình)
- [ ] Audit Trail verify cho mọi transaction DocType
- [ ] Password policy cho medical system
- [ ] 2FA enforcement cho role quan trọng (Dept Head, Ops Manager)

---

## 6. PHÂN TÍCH KỸ THUẬT — CÁC VẤN ĐỀ CẦN XỬ LÝ

### 6.1 Xung đột Naming Convention (CRITICAL)

**Vấn đề:** Bootstrap spec dùng `IMM *` nhưng codebase hiện tại dùng tên không có prefix.

| Bootstrap Spec | Codebase Thực tế | Đề xuất |
|---|---|---|
| `IMM Commissioning Record` | `Asset Commissioning` | Giữ `Asset Commissioning` — đã có data |
| `IMM Document Repository` | `Asset Document` | Giữ `Asset Document` — đã có data |
| `IMM PM Work Order` | ❌ Chưa tạo | Dùng `IMM PM Work Order` cho modules mới |
| `IMM CM Work Order` | ❌ Chưa tạo | Dùng `IMM CM Work Order` |
| `IMM Calibration Record` | ❌ Chưa tạo | Dùng `IMM Calibration Work Order` |

**Quyết định:** Giữ nguyên tên đã có data (`Asset Commissioning`, `Asset Document`). Modules mới dùng prefix `IMM` theo bootstrap spec.

### 6.2 Frontend Architecture (⚠️ Cần Review)

Hiện tại frontend là Vue 3 SPA decoupled khỏi Frappe. Vấn đề:
- CSRF token phải được refresh và retry (đã fix trong axios.ts)
- Không có offline capability
- Mobile responsiveness chưa được test đầy đủ
- Component library chưa có Storybook hoặc design system docs

### 6.3 Test Coverage (THẤP)

Hiện trạng:
- Backend: không có test files (`test_*.py`) cho các DocType đã tạo
- Frontend: không có unit tests cho Vue components
- E2E: không có Playwright/Cypress tests

Mục tiêu tối thiểu để production:
- Backend: 70% coverage cho service layer
- Frontend: smoke tests cho happy path

---

## 7. LỘ TRÌNH XÂY DỰNG ĐẾN END-USER READINESS

### Sprint 1 — Nền tảng Operations (3 tuần)
**Mục tiêu:** Technician có thể tạo và xử lý PM Work Order

| Task | Effort | Priority |
|---|---|---|
| Tạo `IMM PM Schedule` DocType + migration | 2 ngày | P0 |
| Tạo `IMM PM Checklist Template` DocType | 1 ngày | P0 |
| Tạo `IMM PM Work Order` DocType + Workflow (8 states) | 3 ngày | P0 |
| Tạo `IMM PM Task Log` Child DocType | 1 ngày | P0 |
| Scheduler: auto-create PM WO daily | 2 ngày | P0 |
| Backend API: CRUD cho PM WO | 2 ngày | P0 |
| Frontend: PM WO list + create + detail views | 5 ngày | P0 |
| Permission.py cho IMM Technician | 1 ngày | P1 |
| Role fixtures | 1 ngày | P1 |

### Sprint 2 — Incident & Repair (3 tuần)
**Mục tiêu:** Workshop Lead có thể quản lý sự cố và sửa chữa

| Task | Effort | Priority |
|---|---|---|
| Tạo `IMM Incident Report` DocType + Workflow | 2 ngày | P0 |
| Tạo `IMM CM Work Order` DocType + Workflow | 3 ngày | P0 |
| Tạo `IMM RCA Record` DocType | 1 ngày | P1 |
| SLA timer và escalation logic | 2 ngày | P0 |
| Integration: Incident → CM WO auto-create | 2 ngày | P0 |
| Integration: PM fail → CM WO auto-create | 1 ngày | P1 |
| Backend API: Incident + CM WO CRUD | 3 ngày | P0 |
| Frontend: Incident form + CM WO views | 5 ngày | P0 |
| Email notification P1 incidents | 1 ngày | P1 |

### Sprint 3 — Calibration & Compliance (2 tuần)
**Mục tiêu:** Technician có thể lập lịch và track hiệu chuẩn

| Task | Effort | Priority |
|---|---|---|
| Tạo `IMM Calibration Work Order` DocType | 2 ngày | P0 |
| Tạo `IMM CAPA Record` DocType | 1 ngày | P1 |
| Scheduler: calibration expiry alerts | 1 ngày | P0 |
| Backend API: Calibration WO CRUD | 2 ngày | P0 |
| Frontend: Calibration views | 3 ngày | P0 |
| Integration: Calibration fail → CAPA | 1 ngày | P1 |

### Sprint 4 — Dashboards & Reports (2 tuần)
**Mục tiêu:** Manager có dashboard để theo dõi

| Task | Effort | Priority |
|---|---|---|
| PM Compliance Dashboard | 2 ngày | P0 |
| Asset Health Dashboard | 2 ngày | P0 |
| CM Resolution (MTTR) Dashboard | 2 ngày | P1 |
| Calibration Status Report | 1 ngày | P1 |
| Document Expiry Report | 1 ngày | P1 |

### Sprint 5 — Production Hardening (2 tuần)
**Mục tiêu:** Hệ thống sẵn sàng cho user thật

| Task | Effort | Priority |
|---|---|---|
| PDF print formats (5 types) | 3 ngày | P0 |
| Demo data fixtures + seed script | 2 ngày | P0 |
| Data migration tool (Excel import) | 3 ngày | P1 |
| Audit trail verify cho tất cả DocTypes | 2 ngày | P0 |
| E2E tests cho happy paths | 3 ngày | P1 |
| Load testing | 1 ngày | P2 |
| Security review | 2 ngày | P0 |
| User training documentation | 2 ngày | P1 |

---

## 8. BẢNG TỔNG HỢP DOCTYPE CẦN TẠO

### 8.1 DocTypes Operations (Wave 1 còn thiếu)

| DocType | Module | Parent/Child | Priority |
|---|---|---|---|
| `IMM PM Schedule` | IMM-08 | Document | P0 |
| `IMM PM Checklist Template` | IMM-08 | Document | P0 |
| `IMM PM Checklist Item` | IMM-08 | Child of Template | P0 |
| `IMM PM Work Order` | IMM-08 | Document | P0 |
| `IMM PM Task Log` | IMM-08 | Child of WO | P0 |
| `IMM CM Work Order` | IMM-09 | Document | P0 |
| `IMM Spare Part Used` | IMM-09 | Child of CM WO | P0 |
| `IMM Firmware Change Request` | IMM-09 | Document | P1 |
| `IMM Calibration Work Order` | IMM-11 | Document | P0 |
| `IMM Calibration Parameter` | IMM-11 | Child of Cal WO | P0 |
| `IMM CAPA Record` | IMM-11 | Document | P1 |
| `IMM Incident Report` | IMM-12 | Document | P0 |
| `IMM RCA Record` | IMM-12 | Document | P1 |

### 8.2 DocTypes Master Data (cần xác nhận tồn tại)

| DocType | Module | Cần kiểm tra |
|---|---|---|
| `IMM Device Model` | imm_master | Có file DocType JSON chưa? |
| `IMM Asset Profile` | imm_master | Có file DocType JSON chưa? |
| `IMM Audit Trail` | imm_master | Có file DocType JSON chưa? |
| `IMM Location Ext` | imm_master | Có file DocType JSON chưa? |

---

## 9. CÁC RỦI RO VÀ ĐIỂM CHÚ Ý

### Rủi ro kỹ thuật

| Rủi ro | Mức độ | Biện pháp |
|---|---|---|
| Naming convention không nhất quán giữa codebase và spec | HIGH | Quyết định ngay từ Sprint 1, ghi vào CLAUDE.md |
| Frappe workflow state không khớp với business logic | HIGH | Test mỗi workflow transition với real data |
| CSRF token trong SPA decoupled | MEDIUM | Đã fix, monitor tiếp |
| Performance khi fetch nhiều assets | MEDIUM | Index đúng fields, paginate API |
| Frappe scheduler không chạy đúng giờ | LOW | Monitor + alerting |

### Rủi ro nghiệp vụ

| Rủi ro | Mức độ | Biện pháp |
|---|---|---|
| User không follow workflow → dữ liệu inconsistent | HIGH | Training + validation rule nghiêm ngặt |
| Document compliance bị bỏ qua vì complex | MEDIUM | Simplify UI, auto-populate từ IMM-04 |
| PM schedule không chạy auto → bảo trì bị bỏ lỡ | HIGH | Monitor scheduler daily + fallback alert |

---

## 10. CHECKLIST TRƯỚC KHI GO-LIVE

### Backend
- [ ] Tất cả 13 DocTypes mới được tạo và migrate
- [ ] Tất cả Workflows được tạo và assign
- [ ] Scheduler jobs register trong hooks.py
- [ ] permission.py với has_permission() cho Technician
- [ ] Tất cả Role fixtures tạo 8 roles
- [ ] Audit trail ghi cho mọi transaction
- [ ] Test coverage ≥ 70% cho service layer

### Frontend
- [ ] Tất cả views cho 6 modules hoàn thành
- [ ] Mobile responsive (min 768px)
- [ ] Error handling đầy đủ (CSRF, 404, 500, offline)
- [ ] Form validation với Vietnamese error messages
- [ ] Loading states cho tất cả API calls

### Integration
- [ ] IMM-04 → IMM-05 auto-create document set
- [ ] IMM-04 → IMM-08 auto-create PM schedule
- [ ] IMM-08 fail → IMM-09 auto-create CM WO
- [ ] IMM-12 report → IMM-09 auto-create CM WO
- [ ] Tất cả modules update Asset.imm_lifecycle_status

### Compliance
- [ ] PDF print format cho 5 loại biên bản
- [ ] Audit trail verify cho tất cả DocTypes
- [ ] NĐ98 requirement mapping complete
- [ ] WHO HTM requirement mapping complete

### Data & Infrastructure
- [ ] Demo data seed script
- [ ] Excel import tool cho danh sách thiết bị
- [ ] Backup policy configured
- [ ] Monitoring configured (Frappe error logs)

---

*Tài liệu này được tổng hợp từ: bootstrap/data-dictionary.md, bootstrap/workflow-map.md, bootstrap/role-permission-matrix.md, docs/imm-04..12/*.md và trạng thái codebase thực tế tại April 2026.*
