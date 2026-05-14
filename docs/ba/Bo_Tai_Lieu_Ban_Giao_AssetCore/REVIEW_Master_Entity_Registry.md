> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ASSETCORE — MASTER ENTITY REGISTRY
## Review toàn diện bộ tài liệu bàn giao v1.0

**Ngày review:** 2026-05-06  
**Reviewer:** Claude — Solution Architect / Technical Lead  
**Phiên bản tài liệu được review:** 1.0 (Final draft, 2026-05-05)  
**Phạm vi:** Tap_0 → Tap_8 + Phu_Luc_Annexes (10 file .docx)

---

## 1. CUSTOM DOCTYPE — DANH SÁCH ĐẦY ĐỦ

### 1.1 DocType chính (có spec đầy đủ trong Tập 3 mục 3.4)

| # | DocType Name | Module (folder) | Is Submittable | Naming Rule | Defined In (Tập) | Ghi chú |
|---|---|---|---|---|---|---|
| 1 | Medical Asset | asset_registry | No | MA-.YYYY.-.##### | T3 §3.4.1 | Parent của toàn bộ lifecycle |
| 2 | Device Model | asset_registry | No | DM-{model_code} | T3 §3.4.2 | Template cho asset |
| 3 | Asset Identifier | asset_registry | No | AID-.YYYY.-.##### | T3 §3.4.3 | Đa lớp QR/serial/tag |
| 4 | AC Work Order | work_order | Yes | WO-{wo_type_short}-.YYYY.-.##### | T3 §3.4.4 | Unified engine: PM/CM/CAL/INSP/RECALL/RETIRE/INSTALL |
| 5 | Maintenance Plan | maintenance_plan | Yes | MP-.YYYY.-.##### | T3 §3.4.5 | ⚠️ Xem ISSUE-004, ISSUE-005 |
| 6 | Calibration Plan | calibration | Yes | CP-.YYYY.-.##### | T3 §3.4.6 | ⚠️ Xem ISSUE-005, ISSUE-011 |
| 7 | Failure Report | corrective | Yes | FR-.YYYY.-.##### | T3 §3.4.7 | ⚠️ Module "corrective" không có trong folder structure T2 |
| 8 | Initial Inspection | asset_registry | Yes | II-.YYYY.-.##### | T3 §3.4.8 | ⚠️ Thiếu workflow state table, xem ISSUE-010 |
| 9 | Document Record | document_qms | Yes | DOC-.YYYY.-.##### | T3 §3.4.9 | ⚠️ Thiếu state "approved", xem ISSUE-001 |
| 10 | QMS Artifact | document_qms | Yes | QMS-.YYYY.-.##### | T3 §3.4.10 | ⚠️ qms_tier trùng với Document Record, xem ISSUE-009 |
| 11 | Lifecycle Event | lifecycle | No | LCE-.YYYY.-.###### | T3 §3.4.11 | Append-only; ⚠️ event_type ref sai, xem ISSUE-007 |
| 12 | Compliance Record | compliance | No | CR-.YYYY.-.##### | T3 §3.4.12 | Scheduler-managed status; No audit trail |
| 13 | Compliance Case | compliance | Yes | CC-.YYYY.-.##### | T3 §3.4.13 | ⚠️ Thiếu workflow state table |
| 14 | CAPA Case | capa | Yes | CAPA-.YYYY.-.##### | T3 §3.4.14 | ⚠️ "reopened" sau close cần hướng dẫn Frappe |
| 15 | Asset Audit Log | audit | No | AAL-.YYYY.-.####### | T3 §3.4.15 | Append-only; hash chain |
| 16 | Metric Definition | metric | No | MET-{metric_code} | T3 §3.4.16 | — |
| 17 | Metric Snapshot | metric | No | SNP-.YYYY.-.###### | T3 §3.4.17 | — |

### 1.2 DocType phụ / bổ trợ (spec tóm tắt trong Tập 3 §3.4.18)

| # | DocType Name | Loại | Parent DocType | Field chính | Wave | Ghi chú |
|---|---|---|---|---|---|---|
| 18 | AC Work Order Task | Child Table | AC Work Order | task_text, completed, completed_by, result_pass_fail, notes | 1 | — |
| 19 | AC Spare Consumption | Child Table | AC Work Order | item, qty, warehouse, stock_entry, unit_cost, total_cost | 1 | — |
| 20 | Document Record Link | Child Table | AC Work Order, nhiều DocType | document_record (Link), evidence_type, notes | 1 | ⚠️ Không có tiền tố "AC " |
| 21 | Document File | Child Table | Document Record | file (Attach), file_type, capture_date, language | 1 | — |
| 22 | Document Distribution | Child Table | Document Record | user, role, group, acknowledged_at | 1 | — |
| 23 | Maintenance Plan Task | Child Table | Maintenance Plan | task_text, default_duration, required_skill, sop_reference | 1 | — |
| 24 | Maintenance Plan Spare | Child Table | Maintenance Plan | item, default_qty, optional | 1 | — |
| 25 | Calibration Plan Test Point | Child Table | Calibration Plan | point_label, expected_value, tolerance, unit | 1 | — |
| 26 | Initial Inspection Item | Child Table | Initial Inspection | item_text, expected, observed, result_pass_fail, notes | 1 | — |
| 27 | CAPA Action | Child Table | CAPA Case | action_text, action_type, owner, due_date, completed_at, evidence | 1 | — |
| 28 | CAPA Effectiveness Check | Doc | — | capa, check_date, method, conclusion, notes | 1 | — |
| 29 | Root Cause Analysis | Doc | — | compliance_case, technique, conclusion_md, evidence_table | 1 | ⚠️ Spec tóm tắt, cần đầy đủ cho Wave 1 |
| 30 | Adverse Event Report | Doc | — | medical_asset, reported_at, severity_clinical, patient_outcome, narrative, reported_to_authority | 1 | ⚠️ Spec tóm tắt |
| 31 | Recall Notice | Doc | — | vendor, device_model, scope_assets (table), severity, deadline | 1 | ⚠️ Spec tóm tắt, cần cho IMM-09 |
| 32 | Software Update Record | Doc | — | medical_asset, from_version, to_version, applied_at | 1 | Spec tóm tắt |
| 33 | Service Contract | Doc | — | vendor, scope_assets, sla_terms, start_date, end_date, value | 1 | ⚠️ Spec tóm tắt; referenced từ Medical Asset |
| 34 | Decommission Record | Doc | — | medical_asset, decision_date, method, recipient, evidence, sponsor_signoff | 2 | Wave 2 |
| 35 | Decision Record | Doc | — | decision_id, title, context, decision_md, alternatives, owner | All | — |
| 36 | Management Review | Doc | — | review_date, period, attendees, kpi_snapshot_table | All | — |
| 37 | Change Control | Doc | — | title, change_type, scope, risk_assessment, plan_md, approver | All | — |
| 38 | QMS Mandatory Role | Child Table | QMS Artifact | role, mandatory (xem T3 §3.4.10) | 1 | — |
| 39 | Work Order Type | Master Data | — | code, name (PM/CM/INSPECTION/CALIBRATION/RECALL/RETIREMENT/INSTALLATION) | 1 | ⚠️ Chưa có full spec |
| 40 | Risk Class | Master Data | — | code (A/B/C/D), name, description, legal_docs_required | 1 | Seed qua fixtures |
| 41 | Criticality | Master Data | — | code (CRITICAL/MAJOR/MINOR/NONE), description, sla_impact | 1 | Seed qua fixtures |
| 42 | Asset Category | Master Data | — | code (IMG/LAB/SUR/ICU/EMG/etc.), name | 1 | Seed qua fixtures |
| 43 | Document Type | Master Data | — | code (LIC-MOH-REG/CERT-CAL/etc.), name, retention_years, required_for_risk_class | 1 | Seed qua fixtures |
| 44 | QMS Tier | Master Data | — | code (QC/PR-SOP/WI-JD/BM-HS-KPI), name | 1 | Seed qua fixtures |
| 45 | Maintenance Plan Template | Master Data | — | ⚠️ CHƯA CÓ SPEC | 1 | Referenced từ Device Model + Maintenance Plan |
| 46 | Calibration Plan Template | Master Data | — | ⚠️ CHƯA CÓ SPEC | 1 | Referenced từ Device Model + Calibration Plan |
| 47 | Initial Inspection Template | Master Data | — | ⚠️ CHƯA CÓ SPEC | 1 | Referenced từ Initial Inspection |

### 1.3 Custom Field trên DocType core ERPNext

| DocType Core | Fieldname | Type | Mục đích | Defined In |
|---|---|---|---|---|
| Asset | ac_medical_asset | Link → Medical Asset | Reverse link | T3 §3.3.3 |
| Asset | ac_is_medical | Check | Cờ phân biệt medical | T3 §3.3.3 |
| Item | ac_is_medical_device | Check | Cờ phân biệt device | T3 §3.3.3 |
| Item | ac_default_risk_class | Link → Risk Class | Default risk | T3 §3.3.3 |
| Item | ac_default_calibration_required | Check | Default cal flag | T3 §3.3.3 |
| Supplier | ac_legal_license_no | Data | Số ĐKDN/giấy phép | T3 §3.3.3 |
| Supplier | ac_iso_cert | Data | Chứng chỉ ISO | T3 §3.3.3 |
| Supplier | ac_service_scope | Small Text | Phạm vi dịch vụ | T3 §3.3.3 |
| Asset Movement | ac_movement_reason | Select | Lý do điều chuyển | T3 §3.3.3 |
| Asset Movement | ac_doc_evidence | Attach | Bằng chứng | T3 §3.3.3 |
| Purchase Receipt | ac_create_medical_asset | Check | Trigger auto-create | T3 §3.3.3 |
| Department | ac_dept_type | Select | Lâm sàng/CLS/HC | T3 §3.3.3 |
| User | ac_role_profile_assetcore | Link → Role Profile | HTM role profile | T3 §3.3.3 |

---

## 2. WORKFLOW STATES — ĐẦY ĐỦ

### 2.1 Medical Asset — State Machine

| State | Mô tả | Doc Status | Nguồn định nghĩa |
|---|---|---|---|
| need_registered | Nhu cầu đầu tư được ghi nhận | 0 | T1 §1.7, T4 §4.1.1 |
| specs_approved | Thông số kỹ thuật được duyệt | 0 | T1 §1.7, T4 §4.1.1 |
| procurement_approved | Quyết định mua sắm được phê duyệt | 0 | T1 §1.7, T4 §4.1.1 |
| received | Purchase Receipt đã submit | 0 | T1 §1.7, T4 §4.1.1 |
| installed_pending | Chờ lắp đặt | 0 | T1 §1.7, T4 §4.1.1 |
| installed | Đã lắp đặt, chờ kiểm tra | 0 | T1 §1.7, T4 §4.1.1 |
| **installed_failed** | **Kiểm tra ban đầu không đạt** | **0** | **T4 §4.1.1 ONLY — thiếu T1, T3** |
| commissioned | Đã commissioning (inspection pass) | 0 | T1 §1.7, T4 §4.1.1 |
| released_for_use | Đã cấp phép sử dụng | 1 | T1 §1.7, T4 §4.1.1 |
| in_use | Đang trong sử dụng | 1 | T1 §1.7 |
| in_repair | Đang sửa chữa | 1 | T1 §1.7 |
| out_of_service | Tạm ngừng sử dụng | 1 | T1 §1.7 |
| idle | Không sử dụng tạm thời | 1 | T1 §1.7 |
| transferred | Đang điều chuyển | 1 | T1 §1.7 |
| retired | Đã giải nhiệm | 2 | T1 §1.7 |
| disposed | Đã thanh lý | 2 | T1 §1.7 |
| donated | Đã tặng | 2 | T1 §1.7 |
| stored_long_term | Lưu kho dài hạn | 2 | T1 §1.7 |

> ⚠️ **ISSUE-002**: State `installed_failed` CHỈ có trong Tập 4 §4.1.1, THIẾU hoàn toàn trong Tập 1 §1.7.1 (state diagram) và Tập 3 Table 7 (workflow states table). Developer đọc Tập 1 và Tập 3 sẽ không biết state này tồn tại.

### 2.2 AC Work Order — States

| State | Doc Status | Defined In |
|---|---|---|
| planned | 0 | T3 Table 15, T4 §4.1.2 |
| scheduled | 0 | T3 Table 15, T4 §4.1.2 |
| in_progress | 0 | T3 Table 15, T4 §4.1.2 |
| paused | 0 | T3 Table 15, T4 §4.1.2 |
| completed | 1 | T3 Table 15, T4 §4.1.2 |
| closed | 1 | T3 Table 15, T4 §4.1.2 |
| overdue | 0 | T3 Table 15, T4 §4.1.2 (auto) |
| cancelled | 2 | T3 Table 15, T4 §4.1.2 |

### 2.3 Document Record — States

| State | Doc Status | T3 Table 27 | T4 §4.1.3 | Status |
|---|---|---|---|---|
| draft | 0 | ✓ | ✓ | OK |
| in_review | 0 | ✓ | ✓ | OK |
| **approved** | **0** | **✗ THIẾU** | **✓ CÓ** | **⚠️ CONFLICT — ISSUE-001** |
| effective | 1 | ✓ | ✓ | OK |
| superseded | 1 | ✓ | ✓ | OK |
| retired | 1 | ✓ | ✓ | OK |
| expired | 1 | ✓ (auto) | ✓ (auto) | OK |

> ⚠️ **ISSUE-001 BLOCKING**: State "approved" được định nghĩa trong Tập 4 workflow nhưng KHÔNG có trong `status` Select field options của Tập 3. Frappe sẽ báo lỗi khi workflow transition đến state này.

### 2.4 CAPA Case — States

| State | Defined In | Ghi chú |
|---|---|---|
| open | T3 Table 37, T4 §4.1.4 | Initial state |
| in_action | T3 Table 37, T4 §4.1.4 | — |
| awaiting_eff_check | T3 Table 37, T4 §4.1.4 | — |
| closed | T3 Table 37, T4 §4.1.4 | docstatus=1 |
| reopened | T3 Table 37, T4 §4.1.4 | ⚠️ Sau closed=docstatus=1, cần amend |

### 2.5 Compliance Case — States

| State | Defined In |
|---|---|
| open | T3 Table 35, T4 §4.1.5 |
| investigating | T3 Table 35, T4 §4.1.5 |
| awaiting_capa | T3 Table 35, T4 §4.1.5 |
| resolved | T3 Table 35, T4 §4.1.5 |
| closed | T3 Table 35, T4 §4.1.5 |

### 2.6 Initial Inspection — States

| State | Defined In | Ghi chú |
|---|---|---|
| draft | T4 §4.1.6 ONLY | ⚠️ Không có trong T3 spec |
| submitted | T4 §4.1.6 ONLY | ⚠️ Không có trong T3 spec |
| approved | T4 §4.1.6 ONLY | ⚠️ Không có trong T3 spec |
| rejected | T4 §4.1.6 ONLY | ⚠️ Không có trong T3 spec |

### 2.7 Failure Report — States

| State | Defined In |
|---|---|
| open | T3 Table 22, T4 §4.1.7 |
| in_triage | T3 Table 22, T4 §4.1.7 |
| wo_created | T3 Table 22, T4 §4.1.7 |
| closed | T3 Table 22, T4 §4.1.7 |

### 2.8 Maintenance Plan / Calibration Plan — States

| State | Defined In | Ghi chú |
|---|---|---|
| draft | T4 §4.1.8 | ⚠️ Không có trong T3 spec (T3 chỉ có `active (Check)`) |
| submitted | T4 §4.1.8 | ⚠️ Mâu thuẫn với `active (Check)` |
| active | T4 §4.1.8 | ⚠️ Mâu thuẫn với `active (Check)` field |
| retired | T4 §4.1.8 | — |
| superseded | T4 §4.1.8 | — |

---

## 3. ROLES — DANH SÁCH ĐẦY ĐỦ

| Role Name | Viết tắt (T3/T4) | Mô tả | Phạm vi ABAC | Defined In |
|---|---|---|---|---|
| AssetCore HTM Manager | HM | Quản lý vận hành HTM toàn bệnh viện | Toàn bộ asset | T4 §4.2.1 |
| AssetCore Biomed Engineer | BE | Kỹ sư y sinh PM/CM | Department assigned | T4 §4.2.1 |
| AssetCore Technician | Tech | Hỗ trợ PM/CM | Department assigned | T4 §4.2.1 |
| AssetCore Department Head | DH | Trưởng khoa | Department của mình | T4 §4.2.1 |
| AssetCore Operator | Op | Điều dưỡng/KTV vận hành | Department của mình, state hẹp | T4 §4.2.1 |
| AssetCore Doctor | Doc | Bác sĩ, báo cáo AE | Department của mình (read) | T4 §4.2.1 |
| AssetCore QMS Officer | QMS | Phê duyệt SOP, CAPA | Toàn bộ | T4 §4.2.1 |
| AssetCore Procurement | Proc | Tạo PO, vendor evaluation | Toàn bộ (buying scope) | T4 §4.2.1 |
| AssetCore Finance | Fin | Theo dõi chi phí | Toàn bộ (read) | T4 §4.2.1 |
| AssetCore IT Admin | IT | Vận hành hệ thống | System level | T4 §4.2.1 |
| AssetCore Auditor | Aud | Read-only, audit log | Toàn bộ read-only | T4 §4.2.1 |

> ⚠️ **ISSUE-014**: "AssetCore Doctor" được định nghĩa trong T4 Table 4 nhưng không xuất hiện trong permission matrix của Medical Asset (T3 Table 8). T4 Table 5 dùng abbreviation "Doc" mà không có full name trong header.

---

## 4. LIFECYCLE EVENTS — DANH SÁCH ĐẦY ĐỦ

| Event Type | Source DocType | Trigger | Wave | Defined In |
|---|---|---|---|---|
| need_registered | Need Request | submit | 2 | T4 Table 7 |
| specs_approved | Spec Sheet | approve | 2 | T4 Table 7 |
| procurement_approved | Purchase Order | submit | 2 | T4 Table 7 |
| received | Purchase Receipt | submit | 1 | T4 Table 7 |
| installed_pending | AC Work Order (Installation) | create | 1 | T4 Table 7 |
| installed | AC Work Order (Installation) | submit completed | 1 | T4 Table 7 |
| initial_inspection_passed | Initial Inspection | approve | 1 | T4 Table 7 |
| initial_inspection_failed | Initial Inspection | reject | 1 | T4 Table 7 |
| commissioned | Medical Asset | transition | 1 | T4 Table 7 |
| released_for_use | Medical Asset | transition | 1 | T4 Table 7 |
| first_use | Medical Asset | first usage | 1 | T4 Table 7 |
| pm_due | Maintenance Plan | scheduler | 1 | T4 Table 7 |
| pm_completed | AC Work Order (PM) | submit completed | 1 | T4 Table 7 |
| pm_overdue | AC Work Order (PM) | scheduler | 1 | T4 Table 7 |
| calibration_due | Calibration Plan | scheduler | 1 | T4 Table 7 |
| calibration_completed | AC Work Order (Calibration) | submit | 1 | T4 Table 7 |
| calibration_failed | Calibration Result | fail | 1 | T4 Table 7 |
| failure_reported | Failure Report | submit | 1 | T4 Table 7 |
| repaired | AC Work Order (CM) | close | 1 | T4 Table 7 |
| recall_received | Recall Notice | submit | 1 | T4 Table 7 |
| recall_initiated | Recall Notice | apply | 1 | T4 Table 7 |
| adverse_event_reported | Adverse Event Report | submit | 1 | T4 Table 7 |
| compliance_case_opened | Compliance Case | submit | 1 | T4 Table 7 |
| capa_opened | CAPA Case | submit | 1 | T4 Table 7 |
| capa_closed | CAPA Case | close | 1 | T4 Table 7 |
| document_effective | Document Record | transition effective | 1 | T4 Table 7 |
| document_superseded | Document Record | supersede | 1 | T4 Table 7 |
| license_expiring_soon | Compliance Record | scheduler | 1 | T4 Table 7 |
| license_expired | Compliance Record | scheduler | 1 | T4 Table 7 |
| transferred | Asset Movement | submit | 1 | T4 Table 7 |
| placed_idle | Medical Asset | transition idle | 1 | T4 Table 7 |
| returned_to_use | Medical Asset | transition in_use | 1 | T4 Table 7 |
| retired | Decommission Record | submit | 2 | T4 Table 7 |
| disposed | Disposal Record | submit | 2 | T4 Table 7 |
| donated | Donation Record | submit | 2 | T4 Table 7 |
| stored_long_term | Storage Record | submit | 2 | T4 Table 7 |
| replacement_signal_emitted | Predictive Job | scheduler | 3 | T4 Table 7 |
| imported_legacy | Migration job | import | 1 | T4 Table 7 |

> ⚠️ **ISSUE-007**: Tập 3 Table 31 — field `event_type` reference "(theo 8.x)" là broken. Section "8.x" không tồn tại. Đúng ra phải reference Tập 4 §4.3.1 (Table 7 trên đây).

---

## 5. BACKGROUND JOBS — DANH SÁCH

| Job Name | Frequency | Cron | Wave | Defined In |
|---|---|---|---|---|
| wo_sla_check | every 15 min | */15 * * * * | 1 | T4 §4.9.1 |
| pm_due_generator | daily 02:00 | 0 2 * * * | 1 | T4 §4.9.1 |
| calibration_due_generator | daily 02:15 | 15 2 * * * | 1 | T4 §4.9.1 |
| compliance_status_updater | daily 03:00 | 0 3 * * * | 1 | T4 §4.9.1 |
| compliance_alert_dispatcher | daily 03:30 | 30 3 * * * | 1 | T4 §4.9.1 |
| metric_snapshot_daily | daily 04:00 | 0 4 * * * | 1 | T4 §4.9.1 |
| metric_snapshot_hourly | hourly :05 | 5 * * * * | 1 | T4 §4.9.1 |
| audit_chain_verify | daily 05:00 | 0 5 * * * | 1 | T4 §4.9.1 |
| dq_scanner | daily 05:30 | 30 5 * * * | 1 | T4 §4.9.1 |
| archive_lifecycle_event | monthly 1st | 0 6 1 * * | 1 | T4 §4.9.1 |
| replacement_signal_calc | weekly Sun | 0 7 * * 0 | 3 | T4 §4.9.1 |
| spare_reorder_check | daily 07:30 | 30 7 * * * | 1 | T4 §4.9.1 |
| recall_sweep | daily 08:00 | 0 8 * * * | 1 | T4 §4.9.1 |
| fhir_sync_outbound | every 5 min | */5 * * * * | 3 | T4 §4.9.1 |

---

## 6. KPI / METRIC DEFINITIONS — DANH SÁCH

| Metric Code | Đơn vị | Snapshot Freq | Source DocType | Defined In |
|---|---|---|---|---|
| uptime_30d | % | daily | Lifecycle Event + WO | T4 Table 11 |
| mtbf_90d | hours | daily | Lifecycle Event 'failure_reported' | T4 Table 11 |
| mttr_90d | hours | daily | AC Work Order CM closed | T4 Table 11 |
| pm_compliance_rate | % | daily | AC Work Order PM | T4 Table 11 |
| pm_overdue_rate | % | daily | AC Work Order PM | T4 Table 11 |
| calibration_compliance_rate | % | daily | AC Work Order Calibration | T4 Table 11 |
| license_compliance_rate | % | daily | Compliance Record | T4 Table 11 |
| capa_cycle_time | days | daily | CAPA Case | T4 Table 11 |
| capa_effectiveness_rate | % | monthly | CAPA Effectiveness Check | T4 Table 11 |
| adverse_event_rate | events/100assets/year | monthly | Adverse Event Report | T4 Table 11 |
| spare_availability_rate | % | weekly | Stock + Spare Master | T4 Table 11 |
| cost_per_asset_year | VND | monthly | AC Work Order | T4 Table 11 |
| data_quality_score | % | daily | DQ scanner | T4 Table 11 |

---

## 7. ALERT RULES — DANH SÁCH

| Rule ID | Trigger | Recipient | Channel | Defined In |
|---|---|---|---|---|
| AL-001 | WO PM overdue | BE + HM | In-app + Email | T4 Table 14 |
| AL-002 | WO CM S1 overdue 30 min | HM + PO | In-app + Email + SMS | T4 Table 14 |
| AL-003 | License expiring 60/30/7 days | Owner + HM | In-app + Email | T4 Table 14 |
| AL-004 | License expired | HM + QMS | In-app + Email | T4 Table 14 |
| AL-005 | Calibration overdue | BE + HM | In-app + Email | T4 Table 14 |
| AL-006 | Adverse event reported | QMS + HM + PO | In-app + Email + SMS | T4 Table 14 |
| AL-007 | CAPA due 7 days | CAPA Owner + QMS | In-app + Email | T4 Table 14 |
| AL-008 | CAPA overdue | Owner + QMS + PO | In-app + Email | T4 Table 14 |
| AL-009 | DQ score < 95% | QMS + HM | In-app + Email | T4 Table 14 |
| AL-010 | Audit chain verify failed | QMS + IT + Sponsor | Email + SMS | T4 Table 14 |
| AL-011 | Failure report submitted | BE + HM | In-app + Email | T4 Table 14 |
| AL-012 | Recall notice received | QMS + HM + PO | In-app + Email | T4 Table 14 |
| AL-013 | Spare critical below reorder | Procurement + HM | In-app + Email | T4 Table 14 |
| AL-014 | WO closed without evidence | HM | In-app | T4 Table 14 |
| AL-015 | Replacement signal emitted | HM + PO | In-app + Email | T4 Table 14 |

---

## 8. BUSINESS RULES CATALOG (Cross-Reference)

| Rule ID | Module | Mô tả tóm tắt | Defined In |
|---|---|---|---|
| BR-CORE-001 | Cross | Naming rule phải unique; không tái sử dụng ID | T3 §3.4.x hooks |
| BR-CORE-003 | Cross | Mọi state transition → sinh Lifecycle Event | T4 §4.1.10 |
| BR-CORE-005 | Cross | QMS Artifact phải có tier; Document Record với is_qms_artifact=1 → link QMS Artifact | T3 §3.4.10 |
| BR-CORE-006 | Cross | risk_class của Asset không thấp hơn risk_class_default của Device Model (DQ-CONS-001) | T3 §3.8.3 |
| BR-IMM04-001 | IMM-04 | primary_qr phải unique toàn site | T3 §3.4.1 hooks |
| BR-IMM04-003 | IMM-04 | Initial Inspection phải có ≥1 evidence trước submit | T3 §3.4.8 |
| BR-IMM04-004 | IMM-04 | overall_result=pass → asset state→commissioned; fail→installed_failed | T3 §3.4.8 |
| BR-IMM04-005 | IMM-04 | release_for_use bị chặn nếu thiếu hồ sơ pháp lý bắt buộc | T1 §1.5.2 |
| BR-IMM05-001 | IMM-05 | Class C/D phải có ≥1 Document Record LIC-MOH-REG effective | T3 §3.8.1 |
| BR-IMM05-002 | IMM-05 | Document Record phải có owner trước khi effective | T1 §1.8.3 |
| BR-IMM05-003 | IMM-05 | Document Record effective_from = ngày approver ký (không phải ngày upload) | T2 DEC-020 |
| BR-IMM05-004 | IMM-05 | Khi version mới effective → version cũ cùng scope tự động superseded | T3 §3.4.9 |
| BR-IMM08-001 | IMM-08 | Asset phải có ≥1 Maintenance Plan active trước released_for_use | T2 DEC-013 |
| BR-IMM08-002 | IMM-08 | Chỉ 1 plan active per asset cho cùng frequency | T3 §3.4.5 |
| BR-IMM08-003 | IMM-08 | PM WO closed phải có ≥1 evidence | T3 DQ-COMP-004 |
| BR-IMM08-004 | IMM-08 | PM overdue > 7 ngày → escalate daily | T1 §1.4.3 |
| BR-IMM09-001 | IMM-09 | Failure Report submit → auto-create CM WO + asset→in_repair | T3 §3.4.7 |
| BR-IMM09-002 | IMM-09 | description ≥ 50 ký tự | T3 §3.4.7 |
| BR-IMM11-001 | IMM-11 | calibration_required=1 → phải có ≥1 Calibration Plan active (DQ-CONS-002) | T3 §3.8.3 |
| BR-IMM11-002 | IMM-11 | External/regulatory calibration → service_provider mandatory | T3 §3.4.6 |
| BR-IMM11-004 | IMM-11 | Calibration fail → asset→out_of_service | T1 §1.4.5 |
| BR-IMM11-005 | IMM-11 | Regulatory calibration deadline = hard-stop | T4 Table 9 |
| BR-IMM12-001 | IMM-12 | clinical_impact=patient_harm → auto-create Adverse Event Report | T3 §3.4.7 |
| BR-IMM12-002 | IMM-12 | severity=high Compliance Case → RCA required trong 7 ngày | T3 §3.4.13 |
| BR-IMM12-003 | IMM-12 | CAPA Case phải có ≥1 action | T3 §3.4.14 |
| BR-IMM12-004 | IMM-12 | due_date CAPA preventive ≤ 90 ngày | T3 §3.4.14 |
| BR-IMM12-005 | IMM-12 | Effectiveness Check là bắt buộc, không bỏ qua | T4 §4.6.3 |

---

*Registry này là nguồn sự thật cho cross-reference trong quá trình build. Bất kỳ entity nào xuất hiện trong code mà không có trong registry này đều cần Change Control trước khi implement.*

*Phiên bản registry: 1.0 — 2026-05-06*
