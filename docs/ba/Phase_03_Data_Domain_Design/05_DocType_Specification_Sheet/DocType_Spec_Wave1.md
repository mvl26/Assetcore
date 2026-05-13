# DOCTYPE SPECIFICATION — WAVE 1 + WAVE 2 (CONSOLIDATED, v3)

> **Reconciled to v3 codebase — 2026-05-07.** File này thay thế hoàn toàn bản BA gốc (vốn dùng prefix `AC ` cho mọi DocType và giả định ERPNext sync — không khớp thực tế). Tham chiếu: `docs/ba/00_RECONCILIATION_v3.md`.

**Phiên bản:** 3.0
**Owner:** Tech Lead + BA Lead

> Tài liệu này là spec rút gọn cho các DocType **đã ship**. Mỗi DocType ghi: prefix nhóm, label thực tế, naming, submit, workflow, role chính. Field chi tiết → đọc JSON trực tiếp tại `assetcore/assetcore/doctype/<dt_snake>/<dt_snake>.json`.

---

## A. FOUNDATION / AUDIT / LIFECYCLE

### A.1 `Asset Lifecycle Event` (no-prefix, cross)
- **Mục đích:** Sự kiện vòng đời tài sản (cradle-to-grave): installed, commissioned, released, pm_completed, repaired, calibrated, decommissioned, ...
- **Submit:** No · **Naming:** `naming_series:` · **Module:** AssetCore
- **API:** chỉ tạo qua `assetcore.utils.lifecycle.create_lifecycle_event(...)`
- **Liên kết:** `asset` (Link `AC Asset`), `event_type` (Data), `from_status`/`to_status`, `root_doctype`/`root_record`, `actor`, `notes`.

### A.2 `IMM Audit Trail` (IMM, immutable)
- **Mục đích:** Hash chain SHA-256 cho mọi action có ý nghĩa pháp lý.
- **Submit:** No · **Naming:** `naming_series:` · **Immutable** (không update/delete sau insert)
- **API:** `assetcore.utils.lifecycle.log_audit_event(...)`; verify `verify_audit_chain(asset)`
- **Field chính:** `asset`, `event_type`, `timestamp`, `actor`, `ref_doctype`, `ref_name`, `change_summary`, `from_status`, `to_status`, `ip_address`, `hash_sha256`, `prev_hash`.

### A.3 `IMM SLA Policy` (IMM)
- **Mục đích:** Cấu hình SLA + thời gian eskalat theo module/severity.
- **Submit:** No · **Naming:** `field:policy_name` · **Fixture:** export qua `fixtures` trong `hooks.py`.

---

## B. MASTER DATA — `AC ` prefix

### B.1 `AC Asset`
- **Mục đích:** Bản thể tài sản y tế (thay thế `AC Medical Asset` trong BA gốc).
- **Submit:** Yes · **Naming:** `naming_series:` · **Workflow:** `AC Asset Lifecycle` (8 states)
- **States:** Draft → Commissioned → Active → (Under Maintenance / Under Repair / Calibrating / Out of Service) → Decommissioned
- **Field chính:** `asset_code`, `device_model` (Link `IMM Device Model`), `serial_no`, `manufacturer_serial`, `location` (Link `AC Location`), `department` (Link `AC Department`), `custodian_user` (Link User), `criticality` (A/B/C/D), `risk_class` (1/2a/2b/3 — NĐ 98/2021), `commission_date`, `released_at`, `warranty_expiry`, `qr_code`, `rfid_tag`, `last_pm_date`, `next_pm_due`, `last_calibration_date`, `next_calibration_due`.
- **Permission Query:** `assetcore.permissions.ac_asset_query` (filter theo department & vendor scope).

### B.2 `AC Asset Category`
- **Mục đích:** Phân loại thiết bị (CT, MRI, Monitor, Defib, …)
- **Submit:** No · **Naming:** `field:category_name`

### B.3 `AC Asset Depreciation Schedule`
- **Mục đích:** Lịch khấu hao (tự sinh từ Asset). Run qua `services/depreciation.py` mỗi tháng.

### B.4 `AC Asset Downtime Log`
- **Mục đích:** Ghi nhận downtime để tính uptime KPI.

### B.5 `AC Authorized Technician`
- **Mục đích:** Whitelist KTV được ủy quyền với Device Model cụ thể.

### B.6 `AC Department`, `AC Location`
- **Mục đích:** Phân cấp tổ chức (Khoa) và địa điểm (Cơ sở/Tòa/Phòng).

### B.7 `AC Spare Part`, `AC Spare Part Stock`
- **Mục đích:** Master phụ tùng (`AC Spare Part`) + tồn kho theo warehouse (`AC Spare Part Stock`).

### B.8 `AC Supplier`
- **Mục đích:** Nhà cung cấp (gộp manufacturer / service provider / vendor calibration; phân loại qua field).
- **Submit:** Yes (cần kiểm soát thay đổi master)

### B.9 `AC UOM`, `AC UOM Conversion`, `AC Warehouse`
- **Mục đích:** Đơn vị đo + warehouse cho stock movement.

---

## C. PROCUREMENT / STOCK — `AC ` prefix (Wave 2)

### C.1 `AC Purchase` (+ child `AC Purchase Item`, `AC Purchase Device Item`)
- **Submit:** Yes · **Naming:** `naming_series:`
- **Validate hook:** `assetcore.services.imm03.validate_ac_purchase_imm_link` — bắt buộc link về `IMM Procurement Decision`
- **Hooks:** khi `AC Stock Movement` `on_submit` → `auto_mark_purchase_received`.

### C.2 `AC Stock Movement` (+ child `AC Stock Movement Item`)
- **Submit:** Yes · **Naming:** `naming_series:`
- **Hooks:** `on_submit` → mark purchase received; `on_cancel` → unmark.

---

## D. IMM-01 — NEEDS / PLAN / FORECAST

### D.1 `IMM Needs Request` (+ child `Needs Priority Scoring`)
- **Submit:** Yes · **Naming:** `NR-.YY.-.MM.-.#####`
- **Workflow:** `IMM-01 Needs Workflow` (8 states · 24 transitions — workflow phức tạp nhất)
- **Field chính:** `requesting_department`, `requested_device_category`, `qty`, `urgency`, `clinical_justification`, `scoring_table` (child).
- **Owner role:** `IMM Planning Officer` (R), `IMM Department Head` (R), `IMM Operations Manager` (A), `IMM Board Approver` (final approver).

### D.2 `IMM Procurement Plan` (+ child `Procurement Plan Line`, `Budget Estimate Line`)
- **Submit:** Yes · **Naming:** `PP-.YY.-.#####`
- **Workflow:** `IMM-01 Plan Workflow` (4 states)
- **Field chính:** `period_year`, `total_budget`, `lines` (child line items với device category + qty + unit_price + dept + funding_source).

### D.3 `IMM Demand Forecast` (+ child `Forecast Driver`)
- **Submit:** No · **Naming:** `DF-.YYYY.-.#####`
- **Auto-generate:** monthly cron `assetcore.services.imm01.generate_demand_forecast`.

---

## E. IMM-02 — TECH SPEC / BENCHMARK / RISK

### E.1 `IMM Tech Spec` (+ child `Tech Spec Requirement`, `Tech Spec Document`)
- **Submit:** Yes · **Naming:** `TS-.YY.-.#####`
- **Workflow:** `IMM-02 Spec Workflow` (7 states)
- **Field chính:** `device_category`, `requirements` (child với thông số kỹ thuật + must/nice-to-have), `infra_compatibility` (link `Infra Compatibility Item`).

### E.2 `IMM Market Benchmark` (+ child `Benchmark Candidate`)
- **Submit:** Yes · **Naming:** `MB-.YY.-.#####`
- **Field chính:** `device_category`, `candidates` (model + manufacturer + reference price), `freshness_alert` (cron weekly).

### E.3 `IMM Lock-in Risk Assessment` (+ child `Lock-in Risk Item`)
- **Submit:** Yes · **Naming:** `LR-.YY.-.#####`
- **Owner:** `IMM Risk Officer`

### E.4 `Infra Compatibility Item`, `Firmware Change Request`
- `Firmware Change Request` (`FCR-.YYYY.-.#####`) submit Yes — quản lý thay đổi firmware có audit.

---

## F. IMM-03 — VENDOR / AVL / DECISION

### F.1 `IMM AVL Entry` (+ child `Vendor Cert`)
- **Submit:** Yes · **Naming:** `AVL-.YYYY.-.#####`
- **Workflow:** `IMM-03 AVL Workflow` (5 states)
- **Cron:** `imm03.check_avl_expiry` daily.

### F.2 `IMM Vendor Evaluation` (+ child `Vendor Eval Candidate`, `Vendor Eval Criterion`, `Vendor Quotation Line`)
- **Submit:** Yes · **Naming:** `VE-.YY.-.#####`
- **Workflow:** `IMM-03 Vendor Eval Workflow` (5 states)

### F.3 `IMM Supplier Audit` (+ child `Audit Finding`)
- **Submit:** Yes · **Naming:** `SA-.YY.-.#####`
- **Cron:** `imm03.check_audit_due` daily.

### F.4 `IMM Vendor Scorecard` (+ child `Scorecard KPI Row`)
- **Submit:** No · **Naming:** `format:VS-{period_year}-Q{period_q}-{supplier}`
- **Cron:** quarterly Q1/Q2/Q3/Q4 `imm03.update_vendor_scorecard`.

### F.5 `IMM Procurement Decision`
- **Submit:** Yes · **Naming:** `PD-.YY.-.#####`
- **Workflow:** `IMM-03 Decision Workflow` (9 states)
- **Cron:** `imm03.check_decision_overdue` daily.

---

## G. IMM-04 — COMMISSIONING

### G.1 `Asset Commissioning` (+ child `Commissioning Checklist`, `Commissioning Document Record`)
- **Submit:** Yes · **Naming:** `ACC-.YY.-.MM.-.#####`
- **Workflow:** `IMM-04 Workflow` (11 states · 23 transitions — workflow nhiều nhánh nhất)
- **States:** Draft → Pending Doc Verify → To Be Installed → Installing → Identification → Initial Inspection → (Non Conformance / Clinical Hold / Re Inspection / Clinical Release / Return To Vendor)
- **Hooks:** `on_submit` → tự sinh `PM Schedule` + `IMM Calibration Schedule` qua `services/imm08.create_pm_schedule_from_commissioning` và `services/imm11.create_calibration_schedule_from_commissioning`.

---

## H. IMM-05 — DOCUMENT MANAGEMENT

### H.1 `Asset Document`
- **Submit:** No · **Naming:** `format:DOC-{asset_ref}-{YYYY}-{####}`
- **Workflow:** `IMM-05 Document Workflow` (6 states: Draft, Pending Review, Rejected, Active, Archived, Expired)
- **Cron:** `imm05.check_document_expiry` daily.

### H.2 `Document Request`, `Required Document Type`, `Expiry Alert Log`
- `Document Request` (`format:DOCREQ-{YYYY}-{MM}-{####}`) — yêu cầu bổ sung tài liệu thiếu.
- `Required Document Type` (`field:type_name`) — danh mục loại tài liệu yêu cầu.
- `Expiry Alert Log` (`format:EAL-{YYYY}-{MM}-{#####}`) — log alert đã gửi (chống duplicate).

---

## I. IMM-08 — PREVENTIVE MAINTENANCE

### I.1 `PM Work Order`
- **Submit:** Yes · **Naming:** `PM-WO-.YYYY.-.#####`
- **Workflow:** `IMM-08 PM Workflow` (7 states: Open, In Progress, Pending–Device Busy, Overdue, Halted–Major Failure, Completed, Cancelled)
- **Auto-generate:** daily cron `imm08.generate_pm_work_orders_from_schedule`.
- **Permission Query:** `assetcore.permissions.pm_work_order_query`.

### I.2 `PM Schedule`
- **Submit:** No · **Naming:** `format:PMS-{asset_ref}-{pm_type}-{####}`
- **Auto-create:** từ `Asset Commissioning.on_submit`.

### I.3 `PM Checklist Template` (+ `PM Checklist Item` child) → `PM Checklist Result` (per WO) + `PM Task Log`
- Template gắn theo `asset_category`, instantiate vào WO khi sinh.

---

## J. IMM-09 — REPAIR (Corrective Maintenance)

### J.1 `Asset Repair` (+ child `Repair Checklist`, `Spare Parts Used`)
- **Submit:** Yes · **Naming:** `WO-CM-.YYYY.-.#####`
- **Workflow:** `IMM-09 Repair Workflow` (9 states: Open, Assigned, Diagnosing, Pending Parts, In Repair, Completed, Pending Inspection, Cannot Repair, Cancelled)
- **Permission Query:** `assetcore.permissions.asset_repair_query`.
- **Hooks:** trigger từ `Incident Report` qua `services/imm12.py` → `services/imm09.create_repair_from_incident`.

### J.2 `Asset Transfer`
- **Submit:** No · **Naming:** `naming_series:`
- Quản lý điều chuyển asset (1 phần IMM-13 stand-down).

---

## K. IMM-11 — CALIBRATION

### K.1 `IMM Asset Calibration` (+ child `IMM Calibration Measurement`)
- **Submit:** Yes · **Naming:** `CAL-.YYYY.-.#####`
- **Workflow:** `IMM-11 Calibration Workflow` (8 states: Draft, Scheduled, Sent to Lab, Certificate Received, Passed, Failed, Conditionally Passed, Cancelled)
- **Auto-WO:** daily `imm11.create_due_calibration_wos`; expiry check `imm11.check_calibration_expiry`.

### K.2 `IMM Calibration Schedule`
- **Submit:** No · **Naming:** `CAL-SCH-.YYYY.-.#####`
- **Auto-create:** từ `Asset Commissioning.on_submit`.

### K.3 `IMM Device Model` (+ child `IMM Device Spare Part`)
- **Submit:** No · **Naming:** `naming_series:`
- Master device model dùng chung cho IMM-04/08/11.

---

## L. IMM-12 — INCIDENT → RCA → CAPA

### L.1 `Incident Report`
- **Submit:** Yes · **Naming:** `naming_series:`
- **Workflow:** `IMM-12 Incident Workflow` (7 states: Open, Acknowledged, In Progress, Resolved, RCA Required, Closed, Cancelled)
- **Permission Query:** `assetcore.permissions.incident_report_query`.
- **Service:** `assetcore.services.imm12.*` — orchestration tự sinh `IMM RCA Record` khi state → "RCA Required" + tạo `IMM CAPA Record` khi RCA hoàn tất.
- **Cron:** `imm12.detect_chronic_failures` — phát hiện thiết bị có incident lặp lại trong N ngày.

### L.2 `IMM RCA Record` (+ child `IMM RCA Five Why Step`, `IMM RCA Related Incident`)
- **Submit:** Yes · **Naming:** `naming_series:`
- **Workflow:** `IMM-12 RCA Workflow` (4 states: Draft, RCA In Progress, Closed, Cancelled)

### L.3 `IMM CAPA Record`
- **Submit:** Yes · **Naming:** `naming_series:`
- **Cron:** `imm00.check_capa_overdue` daily.
- (Workflow chưa tách JSON; orchestration trong service.)

### L.4 `Asset QA Non Conformance`
- **Submit:** Yes · **Naming:** `format:NC-.YY.-.MM.-.#####`
- Dùng cho IMM-04/11 khi commissioning hoặc calibration fail.

---

## M. SERVICE CONTRACT (cross)

### M.1 `Service Contract` (+ child `Service Contract Asset`)
- **Submit:** No · **Naming:** `naming_series:`
- **Cron:** `imm00.check_service_contract_expiry` + `imm00.check_vendor_contract_expiry` daily.

---

## N. COMMON FIELD CONVENTIONS

- `creation`, `modified`, `owner`, `modified_by` — Frappe chuẩn.
- `docstatus` (0/1/2) cho submittable.
- `workflow_state` — cho mọi DocType có workflow JSON gắn.
- `naming_series` — cho DocType dùng series field.
- `idempotency_key` (nếu cần — service `purchase.py` dùng để chống double-fire).

---

## O. TIÊU CHÍ NGHIỆM THU

- 100% DocType ship phải có spec đầy đủ field, workflow, permission.
- Naming Series + workflow JSON deploy được qua `bench migrate`.
- Hooks `doc_events` và `scheduler_events` test pass.
- Audit chain `verify_audit_chain` pass cho 100% asset có ít nhất 1 lifecycle event.

---

## P. ROADMAP DocType chưa ship (Wave 2 còn lại + Wave 3)

| DocType dự kiến | Module | Trạng thái |
|---|---|---|
| `IMM Training Session`, `IMM Training Attendance` | IMM-06 | chưa làm |
| `IMM Performance Snapshot`, `IMM KPI Result` | IMM-07 | chưa làm |
| `IMM Vigilance Report` | IMM-10 | chưa làm |
| `Asset Decommission Record`, `Asset Disposal Record` | IMM-13/14 | chưa làm — hiện gộp vào state `Decommissioned` của `AC Asset Lifecycle` |
| `IMM Reorder Rule` | IMM-15 | chưa làm |
| `IMM Failure Prediction` | IMM-17 | Wave 3 |
