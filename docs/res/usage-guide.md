# AssetCore — Hướng dẫn sử dụng (User Flow Guide)

> Tóm tắt luồng xử lý + cách dùng tất cả module Wave 1 + Wave 2 + IMM-00.
> Ngày: 2026-05-11 · Phạm vi: 13 module READY · 110+ route FE
> Mục đích: người vận hành biết bấm vào đâu, người dev biết flow nào gọi service nào.

---

## 0. Bố cục chung

```
Login (/login)
    ↓
Launcher (/launcher)        ← Hub trung tâm, 6 nhóm module
    ↓ click tile
Module Sidebar              ← Sidebar context-aware theo route.meta.moduleId
    ↓ click nav item
List View                   ← /xxx-list (table + filter + pagination)
    ↓ click row             ↓ click "Tạo mới"
Detail View                 New Form
/xxx/:id                    /xxx/new
```

**Quy ước URL:**
- Mọi route đều dùng **domain folder** (`/cm/`, `/pm/`, `/needs-requests/`...) — không bao giờ `/imm09/`
- Exception duy nhất: `/imm06/*` (đào tạo) — giữ IMM-coded theo Decision B
- Detail: `/<domain>/:id` · New: `/<domain>/new` · Sub-action: `/<domain>/:id/<action>`

---

## 1. Master Data Setup (BẮT BUỘC chạy trước khi tạo asset)

Trật tự dependency: **Department → Location → Supplier → Device Model → Asset**.

### 1.1 Dữ liệu tham chiếu (Khoa/Phòng/Vị trí/UOM/Danh mục)
**URL**: `/reference-data`
**Sidebar**: System → "Dữ liệu tham chiếu"
**Role**: `IMM System Admin` only

| Tab | DocType | Mục đích |
|-----|---------|----------|
| Khoa/Phòng | `AC Department` | Cây khoa-phòng. Mỗi dept có `dept_head` (Link User) |
| Vị trí | `AC Location` | Cây vị trí vật lý (Block A → Floor 2 → Room 201). `parent_location` Link |
| UOM | `AC UOM` + `AC UOM Conversion` | Đơn vị tính + factor chuyển đổi |
| Danh mục tài sản | `AC Asset Category` | GMDN-aligned categories |

**Flow tạo Khoa**: `/reference-data` → tab Khoa/Phòng → "Thêm khoa" → nhập `dept_name`, `parent_department`, `dept_head` → Lưu.

### 1.2 Nhà cung cấp (`AC Supplier`)
**URL**: `/suppliers` · Detail `/suppliers/:id` · New `/suppliers/new` · Edit `/suppliers/:id/edit`
**Sidebar**: Master → "Nhà cung cấp"
**Role**: `IMM Procurement`, `IMM System Admin`

**Flow tạo Supplier**:
1. `/suppliers/new`
2. Nhập: `supplier_name`, `tax_code` (MST), `address`, `contact_person`, `email`, `phone`
3. Tab "Chứng chỉ" → upload ISO/CE certs (link đến `AC Document`)
4. Lưu → tự sinh code `SUP-2026-00001`

### 1.3 Model thiết bị (`IMM Device Model`)
**URL**: `/device-models` · Detail `/device-models/:id` · New `/device-models/new`
**Sidebar**: Master → "Model thiết bị"

**Flow tạo Model**:
1. `/device-models/new`
2. Nhập: `model_name`, `manufacturer`, `gmdn_code`, `asset_category`, `risk_class` (Class I/II/III)
3. Cấu hình bảo trì:
   - `is_pm_required: 1`
   - `pm_interval_days: 90` (mặc định)
   - `maintenance_plan_template`: link sang `IMM PM Template`
4. Cấu hình hiệu chuẩn:
   - `is_calibration_required: 1`
   - `calibration_interval_days: 365`
5. Lưu → Model sẵn sàng tạo asset từ commissioning.

### 1.4 SLA Policy (`IMM SLA Policy`)
**URL**: `/sla-policies` · Sidebar: Master → "Chính sách SLA"
**Role**: `IMM Quality Assurance`, `IMM System Admin`

Định nghĩa SLA theo `(risk_class, priority)` → `response_hours`, `resolution_hours`. Áp dụng cho IMM-09 (CM) + IMM-11 (Calibration).

### 1.5 Hợp đồng dịch vụ (`AC Service Contract`)
**URL**: `/service-contracts` · Detail `/service-contracts/:id` · New `/service-contracts/new`

Link asset → supplier → coverage (PM/CM/Calibration) → start/end date. Khi asset có incident, hệ thống auto-check covered contract.

---

## 2. IMM-00 — Foundation (Asset Registry, Audit Trail, CAPA)

### 2.1 Tài sản (AC Asset)
**URL**: `/assets` · Detail `/assets/:id` · New `/assets/new` · Edit `/assets/:id/edit` · QR scan `/qr-scan`
**Role**: tất cả (filter theo dept của user)

**Flow tạo asset thủ công** (cho asset legacy nhập từ excel):
1. `/assets/new`
2. Nhập `asset_name`, link `device_model`, `supplier`, `serial_number`, `location`, `department`
3. Cài đặt giá trị tài sản: `purchase_value`, `purchase_date`, `useful_life_years`
4. Lưu → tự sinh code `ACC-ASS-2026-00001` + dispatch lifecycle event `asset_created`

**Cách thông thường**: asset được sinh tự động qua Commissioning (xem §4.1).

**Detail asset có 6 tab**:
- Tổng quan (lifecycle_status, location, dept, value)
- Lịch sử (timeline lifecycle events)
- Bảo trì (PM schedule + WO history)
- Hiệu chuẩn (cal schedule + cert history)
- Sự cố (incidents linked)
- Tài liệu (documents linked qua IMM-05)

### 2.2 Audit Trail
**URL**: `/audit-trail`
**Role**: `IMM Auditor`, `IMM Quality Assurance`, `IMM System Admin`

Read-only log SHA-256 chained. Filter theo `asset_ref`, `action`, `actor`, date range. Click row → expand JSON diff (`before` vs `after`).

### 2.3 CAPA Management
**URL**: `/capas` · Detail `/capas/:id`
**Role**: `IMM Quality Assurance`, `IMM Workshop Lead`

Tạo CAPA thủ công hoặc auto-trigger từ:
- IMM-11 Calibration Fail
- IMM-12 RCA submit
- IMM-15 Cycle Count variance > 5%
- IMM-16 Finding → Create CAPA from Finding

**Flow CAPA**: Open → Action Plan → In Progress → Effectiveness Check → Closed (hoặc Reopened nếu fail check).

### 2.4 Dashboard tổng quan
**URL**: `/dashboard` · Sidebar: System → "Dashboard tổng quan"

KPI 360°: assets active, PM upcoming, CM open, calibration due, CAPA overdue, audit pending. Click bất kỳ widget → drill-down sang module tương ứng.

---

## 3. IMM-01/02/03 — Wave 2 Khối 1: Hoạch định & Mua sắm

### 3.1 IMM-01 — Đề xuất nhu cầu + Kế hoạch
**Sidebar**: "Nhu cầu & Dự toán"
- List nhu cầu: `/needs-requests`
- Tạo: `/needs-requests/new`
- Detail: `/needs-requests/:id` (4 tab: Tổng quan / Chấm điểm / Dự toán / Lịch sử)
- List kế hoạch mua sắm: `/procurement-plans`
- Detail plan: `/procurement-plans/:id`

**Role**: `IMM Procurement`, `IMM Storekeeper`, `IMM Doc Officer`, `IMM Ops Manager`

**Flow đề xuất**:
1. Trưởng khoa vào `/needs-requests/new`
2. Nhập: justification, `target_asset` (replacement) hoặc trống (mới), `requested_qty`, `urgency`, `clinical_impact`
3. Submit → state `Submitted`
4. QA mở detail → tab "Chấm điểm" → nhập weights (Clinical 0.4, Financial 0.3, Risk 0.3) → state `Scored`
5. Ops Manager → tab "Dự toán" → click "Chỉnh sửa" → thêm CAPEX/OPEX rows → Lưu → state `BudgetEstimated`
6. Approval → state `Approved`
7. Click "Đưa vào kế hoạch" → chọn Procurement Plan year 2027 → `roll_into_plan` API → plan có thêm needs này

### 3.2 IMM-02 — Hồ sơ kỹ thuật + Phân tích thị trường
**Sidebar**: "Thông số kỹ thuật"
- List: `/tech-specs`
- Tạo từ plan: `/tech-specs/new` (chọn Plan source)
- Detail: `/tech-specs/:id` (5 tab: Tổng quan / Yêu cầu kỹ thuật / Benchmark / Đánh giá rủi ro / Lock-in)

**Flow soạn spec**:
1. `/tech-specs/new` → chọn `plan_ref` → BE auto-copy template requirements
2. Detail → tab "Yêu cầu kỹ thuật" → CRUD inline rows hoặc upload CSV bulk import
3. Tab "Benchmark" → nhập ≥3 vendor candidates với specs + price → `submit_benchmark`
4. Tab "Đánh giá rủi ro" → 5 chiều lock-in (vendor lock, format, training, parts, software) → score 1-5 + mitigation → `submit_lock_in_assessment`
5. Submit spec → state `Locked` (không edit được nữa, BR-02-09)

### 3.3 IMM-03 — Đánh giá NCC + Quyết định mua + Đơn hàng
**Sidebar**: "Đánh giá NCC & Mua sắm"
- Đánh giá NCC: `/vendor-evaluations` · Detail `/vendor-evaluations/:id`
- AVL (Approved Vendor List): `/approved-vendors`
- Hồ sơ NCC (Vendor Profile): `/vendor-profiles` · Detail `/vendor-profiles/:id`
- Quyết định mua: `/procurement-decisions` · Detail `/procurement-decisions/:id`
- Đơn hàng: `/purchases` · Detail `/purchases/:name` · New `/purchases/new` · Edit `/purchases/:name/edit`

**Flow procurement**:
1. `/vendor-profiles/new` (nếu vendor mới) → nhập legal info + tải chứng chỉ
2. `/vendor-evaluations` → tạo evaluation cho 3 vendor → chấm điểm 5 chiều (Quality/Price/Delivery/Service/Compliance) với weight → BE tính `overall_score`
3. Tab "Scorecard NCC" → xem ranking
4. `/approved-vendors` → vendor đạt threshold tự vào AVL
5. `/procurement-decisions/new` → chọn winning vendor → submit → BE auto-tạo `AC Purchase Order`
6. `/purchases/:name` → Edit để cập nhật ETA, tracking; khi nhận hàng → auto trigger commissioning (IMM-04)

---

## 4. IMM-04/05/06 — Wave 1+2 Khối 2: Triển khai

### 4.1 IMM-04 — Lắp đặt & Nghiệm thu (Commissioning)
**Sidebar**: "Lắp đặt & Nghiệm thu"
- List: `/commissioning`
- Tạo: `/commissioning/new`
- Detail: `/commissioning/:id` (tab Tổng quan)
- Timeline: `/commissioning/:id/timeline`
- NC (Non-Conformance): `/commissioning/:id/nc`

**Flow commissioning**:
1. `/commissioning/new` → chọn `po_ref` (từ IMM-03) → BE auto-fill `device_model`, `supplier`, `master_item`
2. Nhập `serial_number`, `location`, `department`, `responsible_technician`
3. Submit → BE pre-submit gates:
   - G01: tài liệu bắt buộc đủ (link IMM-05)
   - G05/G06: vendor cert valid + risk class consistent
   - Compliance gate IMM-16: `check_asset_compliance_status` → nếu có blocking finding → reject
   - VR-05/06 từ `validate_commissioning`
4. Sau submit thành công:
   - BE tự tạo `AC Asset` với code mới
   - BE auto-tạo `IMM PM Schedule` (cross-module IMM-08) nếu `device_model.is_pm_required`
   - BE auto-tạo `IMM Calibration Schedule` (cross-module IMM-11) nếu cần
   - Lifecycle event `asset_commissioned`
5. Tab NC: tạo Non-Conformance nếu phát hiện hỏng hóc lắp đặt
6. Timeline: xem audit trail của commissioning

### 4.2 IMM-05 — Hồ sơ tài liệu
**Sidebar**: "Đăng ký & Hồ sơ"
- List tài liệu: `/documents`
- Tạo: `/documents/new`
- Detail: `/documents/view/:name`
- Theo asset: `/documents/asset/:assetId`
- Yêu cầu hồ sơ: `/documents/requests`

**Role**: `IMM Doc Officer`, `IMM Quality Assurance`, `IMM Ops Manager`

**Flow upload tài liệu**:
1. `/documents/new` → chọn `asset_ref`, `doc_type` (CO/CQ, ISO, Manual, Cert)
2. Upload file (max 20MB) + `expiry_date`
3. Submit → state `Pending Review`
4. QA approve → state `Approved` + asset có entry trong tab Tài liệu
5. Khi gần hết hạn 30 ngày, daily job `get_expiring_documents` gửi email QA

**Yêu cầu hồ sơ**: `/documents/requests` — chỗ team commissioning yêu cầu Doc Officer chuẩn bị tài liệu thiếu.

### 4.3 IMM-06 — Đào tạo & Năng lực
**Sidebar**: "Đào tạo người dùng"
- Chương trình: `/imm06/programs` · Detail `/imm06/programs/:name` · New `/imm06/programs/new`
- Buổi đào tạo: `/imm06/sessions` · Detail `/imm06/sessions/:name` · New `/imm06/sessions/new`
- Năng lực: `/imm06/competencies` · Detail `/imm06/competencies/:name`

**Lưu ý URL**: Module này dùng prefix `/imm06/*` (exception duy nhất, theo Decision B).

**Flow đào tạo**:
1. `/imm06/programs/new` → tạo Program cho `device_model` cụ thể (vd: "Vận hành máy MRI Siemens")
2. `/imm06/sessions/new` → lên lịch session, chọn trainer, attendees
3. Sau session → `complete_session` → mỗi attendee có competency row mới
4. `/imm06/competencies/:name` → QA sign-off → competency `Active`
5. Khi user vận hành asset → BE gọi `check_user_authorization(user, asset)`:
   - Class III asset cần ≥2 operator có competency active
   - Class I/II cần ≥1
   - Nếu thiếu → block release (gate trong IMM-04)

---

## 5. IMM-08/09/11/12 — Wave 1 Khối 3: Vận hành & Bảo trì

### 5.1 IMM-08 — Bảo trì định kỳ (PM)
**Sidebar**: "Bảo trì định kỳ (PM)"
- Dashboard: `/pm/dashboard`
- WO list: `/pm/work-orders` · Detail `/pm/work-orders/:id` · New `/pm/work-orders/new`
- Lịch: `/pm/calendar`
- Schedule list: `/pm/schedules`
- Templates: `/pm/templates`

**Role**: `IMM Workshop Lead`, `IMM Biomed Engineer`, `IMM Technician`

**Flow PM WO**:
1. `/pm/schedules` → xem lịch PM auto-generated từ commissioning. Mỗi asset có schedule riêng theo `pm_interval_days`.
2. WO tự sinh khi đến hạn (scheduler hourly). Hoặc tạo thủ công `/pm/work-orders/new`.
3. Workshop Lead → `/pm/work-orders/:id` → `assign_technician`
4. KTV thực hiện → tick checklist (link `IMM PM Template`)
5. `submit_pm_result` với result Pass/Fail:
   - Pass → asset `last_pm_date` updated, schedule advance
   - Fail major → asset status "Out of Service" + auto-tạo Repair WO (IMM-09)
6. `/pm/calendar` xem lịch dạng tháng

### 5.2 IMM-09 — Sửa chữa (Corrective Maintenance)
**Sidebar**: "Sửa chữa (CM)"
- Dashboard: `/cm/dashboard` · `/cm/mttr` (MTTR report)
- WO list: `/cm/work-orders` · Detail `/cm/work-orders/:id`
- Tạo: `/cm/create`
- Sub-actions: `/cm/work-orders/:id/diagnose`, `/parts`, `/checklist`
- Firmware change: `/cm/firmware` · `/cm/firmware/:id`

**Role**: `IMM Workshop Lead`, `IMM Biomed Engineer`, `IMM Technician`, `Vendor Engineer` (filtered)

**Flow CM WO**:
1. Trigger: incident (IMM-12) hoặc PM fail (IMM-08) hoặc manual `/cm/create`
2. `/cm/work-orders/:id/diagnose` → KTV chẩn đoán → `submit_diagnosis` → state `Diagnosed`
3. `/cm/work-orders/:id/parts` → request spare parts → BE gọi `imm15.create_allocation` (cross-module gate) → state `Awaiting Parts`
4. Khi parts ready → `start_repair` → state `In Repair`
5. `/cm/work-orders/:id/checklist` → tick test sau sửa
6. `close_work_order` → asset back `In Service`, MTTR ghi nhận, SLA breach flag nếu vượt
7. `/cm/mttr` → xem report MTTR theo period

### 5.3 IMM-11 — Hiệu chuẩn (Calibration)
**Sidebar**: "Hiệu năng & Hiệu chuẩn"
- Dashboard: `/calibration/dashboard`
- List: `/calibration` · Detail `/calibration/:id` · New `/calibration/new`
- Schedule: `/calibration/schedules`

**Flow calibration**:
1. `/calibration/schedules` → xem cal auto-scheduled từ commissioning
2. `/calibration/new` (ad-hoc) hoặc WO tự sinh từ schedule
3. `send_to_lab` (nếu cal ngoài) → state `In Progress`
4. `receive_certificate` → upload cert PDF → tự link vào IMM-05
5. `submit_calibration` với `result`:
   - Pass → `last_calibration_date` updated
   - Fail/Out-of-Tolerance → asset `out_of_tolerance=1` + auto-CAPA (cross-module IMM-16) + lookback assessment

### 5.4 IMM-12 — Sự cố / Incident & RCA
**Sidebar**: "Sự cố & RCA/CAPA"
- Dashboard: `/incidents/dashboard`
- List: `/incidents/list` · Detail `/incidents/:id` · New `/incidents/new`
- RCA: `/rca/:id`

**Role**: tất cả TECH_ROLES + `IMM Clinical`, `IMM Quality Assurance`, `IMM Dept Head`

**Flow incident**:
1. Bất kỳ ai (clinical) → `/incidents/new` → nhập asset, severity (Low/Medium/High/Critical), description
2. Submit → BE:
   - Critical → asset → "Out of Service" + email escalation
   - High → auto-tạo Repair WO (IMM-09)
3. `/incidents/:id` → Workshop Lead triage → assign hoặc transfer
4. Khi đóng incident → BE auto-tạo RCA draft (`/rca/:id`)
5. RCA submit → BE auto-tạo CAPA (cross-module IMM-16) với root cause category
6. Periodic: `get_chronic_failures` (≥3 incident/12 tháng) → đề xuất replacement (IMM-14)

---

## 6. IMM-15/16 — Wave 2 Khối 3: Tồn kho & Tuân thủ

### 6.1 IMM-15 — Tồn kho phụ tùng
**Sidebar**: "Tồn kho phụ tùng"
- Dashboard: `/inventory`
- Phụ tùng: `/spare-parts` · Detail `/spare-parts/:name`
- Kho hàng: `/warehouses` · Detail `/warehouses/:name`
- Tồn kho: `/stock`
- Phiếu kho: `/stock-movements` · Detail `/stock-movements/:name` · New `/stock-movements/new` · Edit `/stock-movements/:name/edit`
- Forecast: `/inventory/forecasts` (mới Sprint 2)
- Watchlist: `/inventory/watchlist` (mới Sprint 2)
- UOM: `/inventory/uom`

**Role**: `IMM Storekeeper`, `IMM Workshop Lead`, `IMM Biomed Engineer`, `IMM Technician`

**Flow allocation (cấp phát cho repair)**:
1. WO repair `/cm/work-orders/:id/parts` → click "Yêu cầu phụ tùng" → BE tạo `IMM Spare Allocation`
2. Storekeeper `/inventory` → xem pending allocations → `approve_allocation`
3. Khi xuất kho → `issue_allocation` → stock giảm + lifecycle event `parts_issued`
4. Nếu thừa → `return_items(allocation, items)` → stock tăng lại

**Flow cycle count**:
1. `/stock-movements/new` → loại "Cycle Count" hoặc dùng endpoint riêng
2. Nhập số đếm thực tế
3. `post_cycle_count` → BE so sánh với book → variance > 5% → auto-tạo Compliance Finding (cross-module IMM-16)

**Flow forecast (mới)**:
1. `/inventory/forecasts` → click "Sinh dự báo"
2. `generate_spare_forecast(horizon_months=12)` → BE đọc consumption history 12 tháng, tính avg × horizon + safety stock + reorder point
3. Storekeeper review → `approve_forecast`
4. Output: list `{part, predicted_demand, current_stock, reorder_qty, recommended_action}`

**Watchlist** (mới):
1. `/inventory/watchlist` → "Thêm vào watchlist"
2. Chọn critical part → BE tag → daily alert nếu stock thấp

### 6.2 IMM-16 — Tuân thủ (Compliance Monitoring)
**Sidebar**: "Theo dõi tuân thủ"
- Quy tắc: `/compliance/rules`
- Phát hiện (Findings): `/compliance/findings` · Detail `/compliance/findings/:id`
- Kiểm toán nội bộ: `/compliance/audits` · Detail `/compliance/audits/:id`
- Bảng điểm: `/compliance/scorecard`
- Soát xét quản lý: `/compliance/mr`
- Bản đồ nhiệt: `/compliance/heatmap`
- Nhật ký audit: `/audit-trail` (chia sẻ với IMM-00)

**Role**: `IMM Quality Assurance`, `IMM Auditor`, `IMM Dept Head`, `IMM Ops Manager`

**Flow rule → finding**:
1. `/compliance/rules` → tạo rule (vd: "PM phải hoàn thành đúng hạn", category "Maintenance Compliance", severity Major)
2. Daily scheduler → `run_compliance_evaluation` → check mọi rule → tạo Finding cho violations
3. `/compliance/findings` → list findings → filter severity/state
4. Detail finding `/compliance/findings/:id`:
   - Confirm NC (Non-Conformance)
   - Mark False Positive (với reason)
   - **Waive** (≥50 ký tự reason, VR-04)
   - **Link to CAPA** (chọn CAPA hiện có)
   - **Create CAPA from Finding** (tạo CAPA mới với 4 method: 5Why/Fishbone/FTA/Pareto)

**Flow internal audit**:
1. `/compliance/audits/new` → tạo audit, chọn period, lead auditor
2. Start Audit → state `In Progress`
3. Tab "Bảng kiểm" → tick từng checklist item
4. Close Audit → blocked nếu còn pending findings (BR-16-12)

**Flow scorecard**:
1. `/compliance/scorecard` → chọn period (year + quarter)
2. BE tính KPI: compliance_rate, open_findings, capa_overdue, audit_completion
3. `publish_scorecard` → state immutable (docstatus=1)
4. VR-10: chỉ publish khi quarter trước đã có Management Review approved

**Flow management review**:
1. `/compliance/mr/new` → tạo review, chairperson, period
2. Finalize → upload minutes doc + dynamic MROutputAction rows (action items)

**Heatmap**:
- `/compliance/heatmap` → Module × Department matrix màu (≥90 emerald / 80-89 yellow / 70-79 orange / <70 red)
- Click cell → drill-down sang FindingList filtered

**Cross-module gate**:
- Mọi `submit_commissioning` (IMM-04) gọi `check_asset_compliance_status` → nếu blocked finding → reject
- `gate_wo_submit` block CM WO nếu Critical CAPA still open

---

## 7. Asset Lifecycle End-of-Life (IMM-13/14 — Wave 3 partial)

- Điều chuyển: `/asset-transfers` · `/asset-transfers/:id` · `/asset-transfers/new`
- Khấu hao & giải nhiệm: `/depreciation`

(Module Wave 3 chưa hoàn thiện — UI live nhưng workflow chưa complete)

---

## 8. Admin / System Functions

### 8.1 Người dùng & Phân quyền
**URL**: `/user-profiles` · Detail `/user-profiles/:user` · New `/user-profiles/new`
**Role**: `IMM System Admin`, `IMM User Mgmt`

Tạo user, gán Role Profile (bundle các role IMM), gán Module Profile (Standard/Admin/Vendor). Vendor Engineer cần thêm `vendor_company` để filter data.

### 8.2 Phê duyệt chờ
**URL**: `/approvals/pending`
**Role**: Tất cả

Inbox phê duyệt cá nhân — gom mọi workflow action chờ user xử lý (qua mọi module). Click → đi sang detail tương ứng.

### 8.3 QR Scan
**URL**: `/qr-scan`

Quét QR/barcode trên asset → mở thẳng `/assets/:id`. Hữu ích cho KTV ngoài hiện trường.

### 8.4 Tài khoản cá nhân
- `/profile` hoặc `/account/profile` — thông tin cá nhân
- `/account/change-password` — đổi mật khẩu

---

## 9. Cross-Module Gates Summary

Bảng tổng hợp gates cross-module — quan trọng để hiểu sao 1 action ở module A có thể bị block bởi module B:

| Từ → Tới | Gate | Tác dụng |
|----------|------|----------|
| **IMM-04 → IMM-08** | `create_pm_schedule_from_commissioning` (auto) | Sau commissioning submit, PM Schedule tự sinh theo template của device_model |
| **IMM-04 → IMM-11** | `create_calibration_schedule_if_needed` (auto) | Tương tự cho Calibration Schedule |
| **IMM-04 → IMM-16** | `check_asset_compliance_status` (pre-submit) | Block commissioning nếu asset có blocking finding |
| **IMM-04 → IMM-06** | `check_user_authorization` | Class III asset cần ≥2 operator có competency |
| **IMM-08 fail → IMM-09** | `auto_create_repair_wo` | PM fail major → tự tạo Repair WO |
| **IMM-09 → IMM-15** | `request_spare_parts` → `create_allocation` | Repair WO request parts → Allocation tự tạo |
| **IMM-11 fail → IMM-16** | `handle_calibration_fail` → CAPA | Calibration fail → CAPA + lookback |
| **IMM-12 RCA → IMM-16** | `submit_rca` → CAPA | RCA submit → CAPA tự sinh |
| **IMM-15 variance → IMM-16** | `post_cycle_count` → Finding | Cycle count variance > 5% → Compliance Finding |
| **IMM-16 → IMM-04/08/09** | `gate_wo_submit` | Block submit khi có Critical CAPA open |

---

## 10. Permission Matrix tóm tắt

| Role | Module chính được dùng | Action chính |
|------|------------------------|--------------|
| `IMM System Admin` | Tất cả | Full CRUD + admin endpoints |
| `IMM Ops Manager` | 00, 01, 02, 03, 08, 09, 11, 12, 15, 16 | Approval, KPI, planning |
| `IMM Workshop Lead` | 08, 09, 11, 12, 15 | Assign WO, approve allocation |
| `IMM Biomed Engineer` | 04, 08, 09, 11 | Diagnose, calibrate |
| `IMM Technician` | 08, 09, 15 | Execute WO, request parts |
| `IMM Quality Assurance` | 01, 04, 05, 11, 16 | Approve docs, scorecard, sign-off |
| `IMM Auditor` | 16, audit-trail | Read-only audit |
| `IMM Doc Officer` | 03, 05 | Upload docs, manage requests |
| `IMM Storekeeper` | 01, 03, 15 | Stock ops, allocation approve |
| `IMM Procurement` | 01, 02, 03 | Needs, spec, vendor eval, PO |
| `IMM Clinical` | 06, 12 | Training attend, incident report |
| `IMM Dept Head` | 01, 04, 12, 16 | Department-level approval |
| `IMM Training Officer` | 06 | Program, session, sign-off |
| `Vendor Engineer` | 09 (filtered to own vendor) | View assigned WO only |

---

## 11. Quick Reference — "Tôi muốn làm X"

| Mục đích | URL bắt đầu | Module |
|----------|-------------|--------|
| Xem 1 thiết bị bất kỳ | `/qr-scan` hoặc `/assets/:id` | IMM-00 |
| Tạo đề xuất mua thiết bị mới | `/needs-requests/new` | IMM-01 |
| Soạn hồ sơ kỹ thuật để chọn vendor | `/tech-specs/new` | IMM-02 |
| Đánh giá NCC + chọn vendor | `/vendor-evaluations/new` → `/procurement-decisions/new` | IMM-03 |
| Tiếp nhận máy mới nhập về | `/commissioning/new` | IMM-04 |
| Upload chứng chỉ ISO/CE | `/documents/new` | IMM-05 |
| Tổ chức training cho khoa | `/imm06/programs/new` | IMM-06 |
| Đến lịch bảo trì 6 tháng | `/pm/work-orders` (auto) hoặc `/pm/calendar` | IMM-08 |
| Máy hỏng cần sửa | `/incidents/new` → tự sinh `/cm/work-orders/:id` | IMM-12 → IMM-09 |
| Cần phụ tùng cho sửa chữa | `/cm/work-orders/:id/parts` → `/inventory` (Storekeeper approve) | IMM-09 → IMM-15 |
| Hiệu chuẩn định kỳ | `/calibration/schedules` → tự sinh | IMM-11 |
| Phân tích root cause sau sự cố | `/rca/:id` | IMM-12 |
| Kiểm toán nội bộ Q1 | `/compliance/audits/new` | IMM-16 |
| Báo cáo bảng điểm tuân thủ | `/compliance/scorecard` | IMM-16 |
| Xem map vi phạm theo khoa | `/compliance/heatmap` | IMM-16 |
| Quên đã làm gì tuần trước | `/audit-trail` filter theo actor | IMM-00/16 |
| Phê duyệt chờ của mình | `/approvals/pending` | System |
| Tạo user mới | `/user-profiles/new` | System Admin |
| Cấu hình SLA mới | `/sla-policies` | Master |
| Thêm Model thiết bị mới | `/device-models/new` | Master |

---

## 12. Reference

- BE rule: `CLAUDE.md`, `.claude/skills/assetcore-be-module/SKILL.md`
- FE rule: `.claude/skills/assetcore-fe-module/SKILL.md`
- Module spec: `docs/imm-XX/02..07_*.md`
- Cross-module: `docs/architecture/Ho_so_kien_truc_IMMIS.md`
- Audit history: `docs/imm-XX/_REPORT.md`
- Alignment plan: `docs/res/code-alignment-plan.md`
- DoD report: `docs/res/dod-verification-report.md`
