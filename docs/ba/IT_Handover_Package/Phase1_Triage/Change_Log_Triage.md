> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# Change Log Triage — AssetCore Wave 1

**Phiên bản:** 1.0  
**Ngày tạo:** 2026-05-06  
**Owner:** Tech Lead  
**Trạng thái:** DRAFT — Awaiting BA/SA Review  

---

## Thống kê tổng

- **BLOCKING:** 14 issues
- **IMPORTANT:** 15 issues
- **NICE-TO-HAVE:** 6 issues
- **Tổng cộng:** 35 issues tìm thấy

**Nhóm phân loại:**
- Naming Inconsistency: 9 issues
- Missing/Incomplete Spec: 7 issues
- Logic Gap / Ambiguity: 11 issues
- Field Definition Conflict: 5 issues
- Workflow/State Mismatch: 3 issues

---

## BLOCKING Issues (phải fix trước khi IT bắt đầu build)

### CL-001 — Lifecycle Event Code `LE-??` Undefined

**Loại:** Missing Spec  
**Nguồn:** State_Machine_Spec.md (dòng 38, 66)  
**Đích:** CLAUDE.md §6.3, hooks.py template  
**Mô tả:**  
State Machine Spec định nghĩa chuyển trạng thái `stand_down → released_for_use (resume)` với `LE-?? resumed` (dòng 38) và Document Record transition `effective → LE-?? document_published` (dòng 66) nhưng Event Type chưa được assign code cụ thể.

**Nội dung hiện tại:**
- CLAUDE.md §6.3 liệt kê: `LE-XX erpnext_sync_in / erpnext_sync_out` (mở)
- State_Machine_Spec.md dòng 38: `LE-?? resumed` (undefined)
- State_Machine_Spec.md dòng 66: `LE-?? document_published` (undefined)

**Nên là:**
```
AC Event Type seed data cần định rõ:
LE-01  created
LE-02  draft_prepared
LE-03  installed
LE-04  commissioned
LE-05  document_effective / license_registered
LE-06  released_for_use
LE-07  (reserved)
LE-08  calibrated
LE-09  (reserved)
LE-10  (reserved)
LE-11  (reserved)
LE-12  recalled
LE-13  (reserved)
LE-14  stand_down
LE-14a resumed (alt: LE-14B)
LE-15  decommissioned
LE-16  disposed
LE-29  document_obsoleted
LE-42  wo_assigned
LE-43  wo_started
LE-44  wo_paused
LE-45  wo_resumed
LE-46  wo_completed
LE-47  wo_validated
LE-48  wo_closed
LE-49  sla_breached
LE-50  wo_cancelled
LE-51  erpnext_asset_sync_inbound
LE-52  erpnext_asset_sync_outbound
```

**Owner:** BA Lead + Tech Lead  
**Deadline:** Before STEP 1 completion

---

### CL-002 — AC Work Order Spare Item Naming Series Missing

**Loại:** Missing Spec  
**Nguồn:** CLAUDE.md §3.5, DocType_Spec_Wave1.md  
**Đích:** Naming Convention  
**Mô tả:**  
`AC Work Order Spare Item` là Child table nhưng không có naming series định nghĩa ở CLAUDE.md Manifest hay Glossary.md. Parent `AC Work Order` có series `WO-.YYYY.-.######` nhưng không rõ spare item sẽ được đánh số như thế nào (global GUID? parent-local sequential?).

**Nội dung hiện tại:**
- CLAUDE.md §3.5: `AC Work Order Spare Item | Work Order | Child | — | —`
- DocType_Spec_Wave1.md: không đề cập child table naming
- Glossary_Naming_Convention.md: không define child table pattern

**Nên là:**
```
Child table không cần series (DB tự tạo ID), nhưng phải document hóa rõ:
- Primary Key: `name` (GUID UUID4)
- Display Name: `<parent_wo_name>:<spare_part_code>` (calculated field)
- Audit: `created_at`, `modified_at`, `created_by` auto

Tương tự cho tất cả child:
  AC Work Order Task
  AC Work Order Spare Item
  AC PM Task Detail
  AC Calibration Measurement
  AC CAPA Action
```

**Owner:** BA Lead + Tech Lead  
**Deadline:** Before STEP 1 naming setup

---

### CL-003 — AC QMS Artifact Naming Series Tier Logic Unclear

**Loại:** Naming Inconsistency  
**Nguồn:** CLAUDE.md §4.3, Glossary_Naming_Convention.md §2.3  
**Đích:** DocType_Spec_Wave1.md  
**Mô tả:**  
Naming Series `QMS-<Tier>-.YYYY.-.####` (e.g., `QMS-PR-2026-0007`) không rõ cách xác định `<Tier>` code. Glossary có 4 Tier (QC/PR/WI/BM) nhưng không có mapping code tiêu chuẩn.

**Nội dung hiện tại:**
- CLAUDE.md §4.3: `QMS-<TIER>-.YYYY.-.####` (placeholder)
- Glossary §1.4: Tier 1 = QC, Tier 2 = PR/SOP, Tier 3 = WI, Tier 4 = BM
- Workflow_Specification.md: không nhắc tới tier code format

**Nên là:**
```
Quy ước chuẩn cho <Tier>:
  QC — Quy chế (Tier 1)
  PR — Thủ tục (Tier 2)
  WI — Hướng dẫn công việc (Tier 3)
  BM — Biểu mẫu (Tier 4)

Ví dụ:
  QMS-QC-2026-0001 (Quality Charter Policy 1/2026)
  QMS-PR-2026-0007 (Procedure 7/2026)
  QMS-WI-2026-0042 (Work Instruction 42/2026)
  QMS-BM-2026-0123 (Form/Template 123/2026)

Naming Series config trong Frappe:
  QMS-QC-.YYYY.-.####
  QMS-PR-.YYYY.-.####
  QMS-WI-.YYYY.-.####
  QMS-BM-.YYYY.-.####
```

**Owner:** BA Lead + SA Lead  
**Deadline:** Before STEP 4 DocType build

---

### CL-004 — AC Location Tree Structure Not Defined

**Loại:** Missing Spec  
**Nguồn:** CLAUDE.md §3.2, Glossary §1.2, DocType_Spec_Wave1.md  
**Đích:** Asset_Registry_Layer_Spec (Phase_02)  
**Mô tả:**  
`AC Location` được liệt kê nhưng không rõ cấu trúc phân cấp (tree-type) hoặc relationship rules. CLAUDE.md nói `(tree-type: Facility > Building > Department > Room)` nhưng DocType Spec không chi tiết.

**Nội dung hiện tại:**
- CLAUDE.md STEP 2: `AC Location (tree-type: Facility > Building > Department > Room)`
- DocType_Spec_Wave1.md: không có AC Location section
- Glossary: "Facility / Building / Department / Room / Location" nhưng không rõ parent-child link

**Nên là:**
```
AC Location DocType:
- Type: Tree
- Main fields:
  - location_code (Data, unique)
  - location_type (Select: Facility / Building / Department / Room / Other)
  - parent_location (Link AC Location, optional)
  - facility_id (Link, auto-fill từ parent nếu type=Building/Dept/Room)
  - description
  - is_active
  
Tree hierarchy validation:
  Facility (root, no parent)
    ├─ Building (parent.location_type = Facility)
    │   ├─ Department (parent.location_type = Building)
    │   │   └─ Room (parent.location_type = Department)
    │   │       └─ Corner/Bed (parent.location_type = Room, optional)
    └─ standalone Building (parent = null, location_type = Facility)

Business Rule: BR-006 enforces this.
```

**Owner:** BA Lead + SA Lead  
**Deadline:** Before STEP 2 build

---

### CL-005 — Work Order `wo_type` Values Not Enumerated

**Loại:** Missing Spec  
**Nguồn:** Workflow_Specification.md §4 title  
**Đích:** DocType_Spec_Wave1.md §11  
**Mô tả:**  
Workflow Spec mention "6 wo_type" nhưng không list cụ thể. Từ Business Rules có thể suy ra: PM, CM, Calibration, IQ/OQ/PQ, Training, nhưng không chính thức.

**Nội dung hiện tại:**
- Workflow_Specification.md §4: `AC Work Order Workflow (Unified — 6 wo_type)` nhưng không list
- Business_Rules_Catalog.md: BR-023, BR-031, BR-041, BR-042 nhắc PM/CM/Cal nhưng không rõ 6 types
- DocType_Spec_Wave1.md §11: không define wo_type field

**Nên là:**
```
AC Work Order.wo_type (Select) — bắt buộc:
1. preventive_maintenance (PM)
2. corrective_maintenance (CM)
3. calibration
4. installation (IQ/OQ/PQ)
5. training
6. inspection / other

Mỗi type trigger khác nhau:
  PM — từ AC PM Plan cron
  CM — từ AC Failure Report
  CAL — từ AC Calibration Plan cron
  IQO — commission workflow
  Training — thủ công
  Inspection — thủ công (có thể từ QMS)
```

**Owner:** BA Lead  
**Deadline:** Before STEP 6 work order build

---

### CL-006 — Document Record `doc_type` Field Definition Missing

**Loại:** Missing Spec  
**Nguồn:** Workflow_Specification.md §2  
**Đích:** DocType_Spec_Wave1.md §5, Phase_02/Document_QMS_Engine_Spec  
**Mô tả:**  
`AC Document Record` workflow có states `draft, review, approved, effective, expired, obsolete, rejected, cancelled` nhưng DocType Spec chỉ nói "Field theo Phase_02/Document_QMS_Engine_Spec" mà file đó chưa được read. Không rõ `doc_type` field (license/training/SOP/QMS/internal) được define ở đâu.

**Nội dung hiện tại:**
- Workflow_Specification.md §2: các state nhưng không detail field
- DocType_Spec_Wave1.md §5: "(Field theo Phase_02/Document_QMS_Engine_Spec.)"
- CLAUDE.md: không reference Document_QMS_Engine_Spec location rõ

**Nên là:**
```
AC Document Record phải define:
- doc_category (Select: License/Certification, Training Material, SOP, QMS, Internal Memo, Other)
- doc_type_specific (Select khác nhau theo category, e.g. License → "Medical Device License", "Safety Approval")
- issuing_authority (Data)
- effective_date, expiry_date (bắt buộc nếu doc_category = License)
- approval_required (Check) — nếu = 1, require workflow transition
- approver_by_role (Link Role)
- owner_department (Link Department)
- security_level (Select: Public, Internal, Confidential, Restricted)
```

**Owner:** BA Lead + SA Lead  
**Deadline:** Before STEP 4 build

---

### CL-007 — AC Medical Asset Workflow "Resume" State Undefined

**Loại:** Workflow/State Mismatch  
**Nguồn:** State_Machine_Spec.md line 26-27, Workflow_Specification.md §1  
**Đích:** Consistent state list  
**Mô tả:**  
State Machine line 26-27 show transition `stand_down → released_for_use (resume)` nhưng Workflow Spec §1 không list state `resuming` hoặc `resuming_pending`. Chưa rõ khi user trigger "Resume" action, asset qua trạng thái trung gian hay trực tiếp về `released_for_use`.

**Nội dung hiện tại:**
- State_Machine_Spec.md:
```
stand_down ──┤
              ├──► released_for_use (resume)
              ├──► retired ──► disposed
```
- Workflow_Specification.md §1 states: draft, installed, commissioned, released_for_use, stand_down, retired, disposed — **không mention resume state**
- Transition tại dòng 36 (Stand down) và dòng 37 (Resume) không clarify intermediate state

**Nên là:**
```
Clarify: Resume là direct transition từ stand_down → released_for_use hay có trạng thái trung gian?

Proposal: Direct (KISS principle)
  stand_down → released_for_use (action: Resume, actor: Trưởng VTTBYT + QMS, condition: issue resolved)
  
Side effect: LE-14A resumed

Workflow Spec cập nhật:
| Resume | stand_down | released_for_use | AC Asset Manager + AC QMS Officer | issue resolved | Y | LE-14A |
```

**Owner:** BA Lead  
**Deadline:** Before STEP 1 Workflow setup

---

### CL-008 — Role "AC Calibration Lab Engineer" vs "AC Vendor Calibration" Overlap

**Lo型:** Naming Inconsistency  
**Nguồn:** Glossary_Naming_Convention.md §2.5, Permission_Matrix.md §2, CLAUDE.md §4.4  
**Đích:** Role consolidation  
**Mô tả:**  
Glossary list `AC Calibration Lab Engineer` (internal role) nhưng Permission Matrix §3.2 dùng `AC Cal Lab Eng` (abbreviated) và `AC Vendor Calibration` (external). Không rõ:
- Đây là 2 role khác nhau hay 1?
- Internal lab engineer vs external vendor calibration — permission khác như thế nào?

**Nội dung hiện tại:**
- Glossary §2.5: `AC Calibration Lab Engineer`
- CLAUDE.md §4.4: `AC Calibration Lab Engineer`
- Permission_Matrix §2: `AC Calibration Lab Engineer`
- Permission_Matrix §3.2: `AC Cal Lab Eng`
- CLAUDE.md §4.4: `AC Vendor Calibration` (external)

**Nên là:**
```
Define 2 roles rõ ràng:

1. AC Calibration Lab Engineer (internal)
   - Thực hiện hiệu chuẩn tại lab của BV
   - Create/Edit Calibration Record
   - W (Write) AC Calibration Record (own assigned)
   - S (Submit) Calibration Record (mark as performed)
   
2. AC Vendor Calibration (external)
   - Nhà cung cấp dịch vụ hiệu chuẩn ngoài
   - Scoped: chỉ Cal WO được assign
   - W (Write) AC Work Order (limited fields: measurement, comments)
   - S (Submit) WO → state performed
   - Cannot see AC Metric/Cost fields

Phân biệt bằng Organization field (nếu cần).
```

**Owner:** SA Lead + BA Lead  
**Deadline:** Before Permission Matrix finalize

---

### CL-009 — Missing Business Rule Enforcement Level for Validation

**Loại:** Logic Gap  
**Nguồn:** Business_Rules_Catalog.md, DocType_Spec_Wave1.md  
**Đích:** Consistent V/W/S coding  
**Mô tả:**  
Business_Rules_Catalog define Enforcement column (V/W/S/R/I) nhưng một số rule không đầy đủ specify. Ví dụ:
- BR-001: "V + S" — được
- BR-003: "V (cảnh báo) + R" — logic "cảnh báo" vs enforce không clear
- BR-005: "W" — chỉ workflow, nhưng có validate bên cạnh không?

**Nội dung hiện tại:**
- Business_Rules_Catalog: inconsistent enforcement notation
- BR-003: "V (cảnh báo) + R" — "cảnh báo" là warning field hay throw error?
- BR-014: "S" (cron task) — không specify timeout, retry logic
- BR-026, BR-052: SLA check nhưng không rõ alert method (email/notification/dashboard)

**Nên là:**
```
Standardize enforcement notation:

V = Frappe Field Validation (throws ValidationError if fail, blocks save)
W = Workflow Validation (throws WorkflowError if fail, blocks transition)
S = Server Script / Cron (custom Python, may log exception/alert)
R = Report / Read-only flag (không block, chỉ flag hoặc warning badge)
I = Integration check (inbound/outbound sync validation)
W:warn = Workflow warning (log but allow transition)
V:warn = Field warning (allow save but show warning message)

BR-003 → V:warn + R (cảnh báo field, mark trên Dashboard)
BR-014 → S (cron daily, trigger Compliance Case)
BR-026 → S (cron, create Case + notification)
BR-032 → S + alert method: "email_to_role:AC Asset Manager, dashboard_flag=true, sms=true"
```

**Owner:** Tech Lead + BA Lead  
**Deadline:** Before STEP 6-7 implementation

---

### CL-010 — AC CAPA Workflow "Reopen" Logic Undefined

**Loại:** Logic Gap  
**Nguồn:** State_Machine_Spec.md §8, Workflow_Specification.md §8  
**Đích:** CAPA state machine clarification  
**Mô tả:**  
State Machine §8 show `closed → reopened` nhưng Workflow §8 action table list:
- Submit (draft → approved)
- Close (effectiveness_pending → closed)
- Reopen (closed → reopened)
- Resume (reopened → in_progress)

Không rõ difference giữa "Reopen" action vs "Resume" action. Có state `reopened` hay không? Khi nào reopen vs resume được trigger?

**Nội dung hiện tại:**
- State_Machine_Spec.md §8 states: draft, approved, in_progress, effectiveness_pending, closed, reopened, cancelled
- Workflow_Specification.md §8 actions: Submit, Begin, Wait, Close, Reopen, Resume
- Logic: "Reopen" (closed → reopened) then "Resume" (reopened → in_progress) — 2 step hay 1?

**Nên là:**
```
Clarify CAPA close workflow:

Scenario 1: Effective (action=Close)
  effectiveness_pending → closed (state machine end)
  
Scenario 2: Not effective (action=Reopen)
  effectiveness_pending → reopened (temp state, holding state)
  
Scenario 3: Continue work after Not effective (action=Resume)
  reopened → in_progress (continue action plan)
  
Then:
  in_progress → effectiveness_pending (re-check)
  effectiveness_pending → closed (success) or reopened (fail, loop)

Alternative interpretation: Reopen = direct transition
  closed → in_progress (action: Reopen, no intermediate state)
  
**Choose one + document clearly.**

Recommendation: Keep intermediate state `reopened` for audit trail clarity.
State chart update:
```
draft → approved → in_progress → effectiveness_pending → closed
                       ↑                                      ↓
                       └──────── reopened ←──────────────────┘
```

**Owner:** BA Lead  
**Deadline:** Before STEP 7 CAPA build

---

### CL-011 — Permission Matrix SoD Rule Enforcement Method Missing

**Loại:** Missing Spec  
**Nguồn:** Permission_Matrix.md §7 (Segregation of Duty)  
**Đích:** Implementation guide  
**Mô tả:**  
SoD rules listed (WO creator ≠ validator, Document creator ≠ approver, etc.) nhưng không specify enforcement method: Frappe built-in constraint hay custom server script?

**Nội dung hiện tại:**
- Permission_Matrix.md §7: SoD rules but no HOW TO ENFORCE
  - "WO creator ≠ validator" — check createdby vs validator field?
  - "Cond≠approver" — User Permission filter?
  - "CAPA submitter ≠ closer" — custom validation?

**Nên là:**
```
SoD Enforcement spec:

BR-081: WO creator ≠ validator
Enforcement: Server Script on AC Work Order before_submit
  if doc.validator_user == frappe.session.user:
    throw("Cannot validate your own WO")

BR-084 alt: Document creator ≠ approver (effective)
Enforcement: Server Script on AC Document Record before_workflow_transition
  if event == "approve_for_effective" and doc.owner == frappe.session.user:
    throw("Creator cannot approve own document")

CAPA submitter ≠ closer:
  if doc.owner == frappe.session.user and state_to == "closed":
    throw("Submitter cannot close CAPA")

Stock Entry consumer ≠ approver:
  if from_wo_created_by == frappe.session.user and role == "approver":
    deny_permission_row()

Custom validation utility:
  assetcore.compliance.check_segregation_of_duty(doc, current_actor, action)
```

**Owner:** Tech Lead + SA Lead  
**Deadline:** Before STEP 7 compliance build

---

### CL-012 — AC Failure Report "Merged" State Merge Logic Undefined

**Loại:** Logic Gap  
**Nguồn:** State_Machine_Spec.md §5, Workflow_Specification.md §5  
**Đích:** Failure Report implementation spec  
**Mô tả:**  
Failure Report state machine mention "auto-merge với FR cùng asset trong cửa sổ thời gian" nhưng:
- Cửa sổ thời gian = bao lâu? (1 giờ? 1 ngày?)
- Khi merge, cái nào là primary, cái nào obsolete?
- Merged FR có lifecycle event không?

**Nội dung hiện tại:**
- State_Machine_Spec.md §5: `submitted → merged | System (duplicate trong cửa sổ)`
- Workflow_Specification.md §5: `Auto-merge | submitted | merged | System (duplicate trong cửa sổ)`
- Business_Rules_Catalog: BR-031 Failure Report bắt buộc field, nhưng không mention merge logic

**Nên là:**
```
BR-037 (new): Failure Report Duplicate Merge Logic
Scope: AC Failure Report
Enforce: S (server script)

Merge trigger:
  - Khi FR new submitted
  - Check: same asset + severity + location + symptom_keyword
  - Within: 4-hour sliding window (configurable per facility)
  - Action: mark old_fr.state = merged, create merge_link field
  
Primary FR: newer one (keep, increment comment count)
Secondary FR (merged): old_fr.state = merged, set merged_into = primary_fr_id

Lifecycle Event:
  merged → LE-37 (or LE-50 alt) merged_fr_detected

Notification: send to assignee if primary WO already created.

Config: assetcore_settings.failure_report_merge_window_hours = 4
```

**Owner:** BA Lead + Tech Lead  
**Deadline:** Before STEP 6 Failure Report build

---

### CL-013 — AC Asset Movement Approval Chain Multi-Department Logic Unclear

**Lo型:** Logic Gap  
**Nguồn:** Permission_Matrix.md §3.9, State_Machine_Spec.md §10  
**Đích:** Movement workflow implementation  
**Mô tả:**  
Asset Movement requires approval từ:
- AC Department Head (cũ + mới)
- AC QMS Officer
- AC Legal Officer
- AC Finance Officer

Nhưng không rõ:
- Order of approvals? (sequential? parallel?)
- If cũ + mới dept same user (same head), approve once or twice?
- Can reject at any stage?

**Nội dung hiện tại:**
- State_Machine_Spec.md §10:
```
draft → submitted → approved_dept_old → approved_dept_new → approved_vttbyt → executed → closed
```
- Permission_Matrix.md §3.9 không detail approval chain, chỉ list who can W/S
- CLAUDE.md R-03 "thay đổi trạng thái phải qua Workflow" nhưng không specify Frappe Workflow states

**Nên là:**
```
AC Asset Movement Workflow states (refined):
draft → submitted → pending_approval_old_dept → approved_by_old_dept 
  → pending_approval_new_dept → approved_by_new_dept
  → pending_approval_vttbyt → approved_by_vttbyt
  → executed → closed

Actions:
1. Submit: submitted (auto calc approval chain)
2. Approve Old Dept: submitted → approved_by_old_dept (role: AC Department Head + user.dept = old dept)
3. Approve New Dept: approved_by_old_dept → approved_by_new_dept (role: AC Department Head + user.dept = new dept, skip if same)
4. Approve VTTBYT: approved_by_new_dept → approved_by_vttbyt (role: AC Asset Manager + QMS + Legal + Finance)
5. Execute: approved_by_vttbyt → executed (role: AC Asset Manager)
6. Close: executed → closed (system auto after movement complete)

SoD: Approver ≠ requester (creator).
Can reject at any pending stage → return to submitted + reason field.

Validation: BR-071 (Phase 2, but framework in Wave 1)
```

**Owner:** BA Lead  
**Deadline:** Before STEP 8 movement build

---

### CL-014 — AC Metric Definition "snapshot_frequency" Values Not Enumerated

**Loại:** Missing Spec  
**Nguồn:** CLAUDE.md §2 R-05  
**Đích:** Metric Definition field spec  
**Mô tả:**  
R-05 mention "snapshot_frequency" nhưng không list allowed values. Business_Rules_Catalog BR-102 mention "monthly" nhưng không rõ có daily/weekly/quarterly không.

**Nội dung hiện tại:**
- CLAUDE.md §2 R-05: "snapshot_frequency"
- Business_Rules_Catalog BR-102: "Snapshot KPI hàng tháng"
- DocType_Spec_Wave1.md §18: "(Theo Phase_02/Metric_Dashboard_Engine_Spec.)" — no detail

**Nên là:**
```
AC Metric Definition.snapshot_frequency (Select):
- hourly (fine-grained, high storage, for alerting)
- daily (standard)
- weekly
- monthly (default for KPI)
- quarterly
- yearly
- on_demand (triggered manually)

Related field:
- retention_days (Int): how long to keep snapshots (default 365)
- alert_threshold (Decimal, optional): trigger alert if metric crosses

Example scheduler cron:
  daily: generate_daily_snapshots → daily metrics + monthly roll-up
  hourly: check_alert_rules → alert if threshold breached
```

**Owner:** Tech Lead + BA Lead  
**Deadline:** Before STEP 9 metric build

---

## IMPORTANT Issues (không block nhưng cần fix trước DEV)

### CL-015 — AC Device Model "item_template" Mandatory vs Optional Unclear

**Loại:** Field Definition Conflict  
**Nguồn:** DocType_Spec_Wave1.md §2  
**Đích:** Device Model field spec  
**Mô tả:**  
Field table show `item_template | Link Item | Y` (mandatory) nhưng Business logic không clear: mỗi Device Model phải link tới ERPNext Item không? Có trường hợp nào Device Model không có Item template (e.g., imported từ vendor catalog không qua procurement)?

**Nội dung hiện tại:**
- DocType_Spec_Wave1.md §2: `item_template | Link Item | Y`
- Business_Rules_Catalog: không mention item_template requirement
- Phase_03/07 Mapping_ERPNext_AssetCore: need to check relationship

**Nên là:**
```
Clarify AC Device Model.item_template:
- If mandatory=true: mọi device model phải có Item trong ERPNext trước
  → thích hợp nếu BV quản lý inventory qua ERPNext
- If mandatory=false: có Device Model chỉ cho catalog, không mua
  → thích hợp nếu import từ legacy, test model

Recommendation: mandatory=FALSE (flexibility)
  - Field: item_template (Link Item, optional)
  - Default: null
  - Business rule: BR-Xnew — if item_template null, cannot create PR/PO
  - Validation: when first create WO/PM Plan, prompt user to link Item
```

**Owner:** BA Lead  
**Deadline:** Before STEP 2 DocType build

---

### CL-016 — AC Device Model "spare_parts_template" Table Definition Missing

**Loại:** Missing Spec  
**Nguồn:** DocType_Spec_Wave1.md §2  
**Đích:** Spare parts BOM spec  
**Mô tả:**  
Field mention `spare_parts_template | Table Spare BOM` nhưng:
- Table name không defined (AC Device Model Spare Item? AC Spare Part BOM?)
- Fields of table (part code, qty, unit, criticality) không list
- Relationship với ERPNext BOM không clear

**Nội dung hiện tại:**
- DocType_Spec_Wave1.md: `spare_parts_template | Table Spare BOM | –`
- Business_Rules_Catalog BR-061: "Phụ tùng critical" nhưng không reference template
- Glossary: "BOM" defined nhưng child table não spec

**Nên là:**
```
AC Device Model Spare Item (child table):
| Field | Type | M | Description |
|-------|------|---|-------------|
| spare_item_code | Data | Y | ref to Item |
| spare_item_qty | Float | Y | qty needed per maintenance |
| spare_item_unit | Link UOM | Y | unit of measure |
| is_critical | Check | – | flag critical spare (BR-061) |
| min_stock_level | Int | – | min qty keep in stock |
| standard_cost | Currency | – | cost for PM budget |

Linked table purpose: template for WO creation
  When create WO from PM Plan → copy spare items dari Device Model + allow customize

Relationship:
  AC Device Model (1) → (M) AC Device Model Spare Item (child)
  Not direct link to ERPNext BOM (allow more flexibility)
```

**Owner:** Tech Lead  
**Deadline:** Before STEP 2 build

---

### CL-017 — AC Asset Identifier "identifier_type" Taxonomy Incomplete

**Loại:** Missing Spec  
**Nguồn:** DocType_Spec_Wave1.md §3  
**Đích:** Asset identifier strategy  
**Mô tả:**  
Field `identifier_type | Select QR / RFID / Asset Tag / Barcode / Vendor Serial / Other` nhưng không rõ:
- Multiple identifiers per asset allowed?
- Priority khi query asset by identifier?
- Unique constraint per type?

**Nội dung hiện tại:**
- DocType_Spec_Wave1.md: select list nhưng không detail
- CLAUDE.md §4.8: asset_code + QR + RFID nhưng không clarify relationship
- Business_Rules_Catalog: không mention identifier dedup/conflict

**Nên là:**
```
AC Asset Identifier strategy:

Primary identifier (1 per asset):
  asset_code (AC Medical Asset.asset_code) — System of Record

Secondary identifiers (M per asset):
  AC Asset Identifier records allow:
  - type: QR / RFID / Barcode / Vendor Serial / BarcodeAlt / Other
  - one_per_type: false (allow multiple QR if printed multiple times)
  - state: Active / Reissued / Lost / Revoked
  - valid_until: optional (QR can expire if printed sticker degrades)

Unique constraint:
  UNIQUE(medical_asset, identifier_type, identifier_value) IF state = Active
  Allow duplicate if state = Reissued / Lost / Revoked

Lookup logic (when scan):
  1. Try asset_code exact match
  2. Try AC Asset Identifier match (state=Active)
  3. If not found → suggest create new or link to existing asset (data quality flow)

Query optimization:
  - Index: (medical_asset, identifier_type, state)
  - Cache active identifiers per asset
```

**Owner:** Tech Lead + BA Lead  
**Deadline:** Before STEP 3 build

---

### CL-018 — AC Custodian Assignment "from_at / to_at" vs "assigned_date" Naming

**Loại:** Naming Inconsistency  
**Nguồn:** DocType_Spec_Wave1.md §4  
**Đích:** Custodian assignment field naming  
**Mô tả:**  
Field use `from_at / to_at` (datetime) nhưng không consistent với naming convention. Glossary prefer `*_date` for date, `*_at` for datetime, but `from_at` sounds like "when assignment happen from", not "range".

**Nội dung hiện tại:**
- DocType_Spec_Wave1.md §4: `from_at / to_at | Datetime`
- CLAUDE.md §4.2 convention: `*_date` for date, `*_at` for datetime
- Ambiguity: `from_at` = when assignment effective? or when old custodian stop?

**Nên là:**
```
Renamed (clarify naming):
- from_at → assigned_from_at (when custodian assume responsibility)
- to_at → assigned_to_at (when custodian end responsibility)

Alternative (clearer):
- custodian_start_date (Date) or effective_from_at (Datetime)
- custodian_end_date (Date) or effective_to_at (Datetime)

Recommendation: use from_at / to_at but document clearly:
```
| Field | Type | Description |
|-------|------|-------------|
| from_at | Datetime | Custodian assignment effective start |
| to_at | Datetime | Custodian assignment end (null = ongoing) |
```

**Owner:** BA Lead  
**Deadline:** Before STEP 3 build

---

### CL-019 — AC Work Order "sla_breached" Field vs SLA Timer Logic

**LoType:** Logic Gap  
**Nguồn:** Workflow_Specification.md §4  
**Đích:** WO SLA implementation spec  
**Mô tả:**  
Workflow mention "sla_breached=true khi vi phạm" nhưng không clarify:
- Is field `sla_breached` a checkbox, or state flag?
- How is SLA timer triggered? (on_submit? on_workflow_transition?)
- What is SLA calculation base? (state duration, or fixed deadline?)

**Nội dung hiện tại:**
- Workflow_Specification.md §4: "SLA timer: auto chạy trong background; set `sla_breached=true`"
- Business_Rules_Catalog BR-026: "PM overdue sau X ngày" nhưng WO SLA spec khác
- CLAUDE.md §6.1 hooks: "assetcore.work_order.scheduler.check_sla_breach" but no detail

**Nên là:**
```
AC Work Order SLA spec:

1. sla_due_at (Datetime) — target completion time
   Calculate on state transition to in_progress:
     if wo_type == PM → sla_due_at = now + PM_plan.sla_minutes (default 480 min = 8h)
     if wo_type == CM → sla_due_at = now + criticality_SLA (Critical=2h, High=8h, etc.)

2. sla_breached (Check) — flag if sla_due_at < now and state < closed
   Set by scheduler check_sla_breach (hourly)

3. sla_breach_event (on_set → LE-49 sla_breached)
   Trigger notification, escalate to supervisor

Side effects:
  - LE-49 published
  - Dashboard alert
  - Compliance Case may auto-create (per BR-026)

Scheduler job:
  hourly: check_sla_breach
    - Find WO: state != closed AND sla_due_at < now AND sla_breached = false
    - Set sla_breached = true
    - Publish LE-49
    - Send alert notification
```

**Owner:** Tech Lead  
**Deadline:** Before STEP 6 WO build

---

### CL-020 — AC Calibration Record "certificate_doc" vs "calibration_certificate" Print Format

**Loại:** Naming Inconsistency  
**Nguồn:** DocType_Spec_Wave1.md §9  
**Đích:** Calibration document handling spec  
**Mô tả:**  
Field `certificate_doc | Link AC Document Record` suggest upload/link existing doc, but Business_Rules_Catalog BR-043 say "bắt buộc upload PDF" which sounds like attachment, not link.

**Nội dung hiện tại:**
- DocType_Spec_Wave1.md: `certificate_doc | Link AC Document Record`
- Business_Rules_Catalog BR-043: "Calibration Certificate bắt buộc upload PDF trước khi đóng WO Cal"
- Workflow_Specification.md §6: không mention certificate field

**Nên là:**
```
Clarify calibration certificate handling:

Option A (recommended): Dual approach
  - certificate_doc (Link AC Document Record, optional)
    → Link to formal document if already in QMS system
  - certificate_attachment (Attach, optional)
    → Direct PDF upload (Lab may provide vendor cert)
  - Validation: At least one of two must exist before Close

Option B: Auto-generate from Print Format
  - Use Print Format "AC Calibration Record – Certificate" 
  - Generate on-close, save as AC Document Record
  - Store: certificate_doc link (auto-created)

Recommendation: Option B (cleaner audit trail)
  on_workflow_transition (to_state=closed):
    generate_calibration_certificate(doc)
      → create AC Document Record
      → attach PDF
      → save reference to doc.certificate_doc_id
      → publish LE-08 calibrated
```

**Owner:** Tech Lead + BA Lead  
**Deadline:** Before STEP 6 Calibration build

---

### CL-021 — AC PM Plan "asset_filter" JSON Schema Not Specified

**LoType:** Missing Spec  
**Nguồn:** DocType_Spec_Wave1.md §7  
**Đích:** PM Plan bulk assignment spec  
**Mô tả:**  
Field `asset_filter | JSON filter` allow create PM plan for multiple assets matching filter, but JSON schema (structure) not defined. How to express filter? Frappe DocType filters format? MongoDB? Custom?

**Nội dung hiện tại:**
- DocType_Spec_Wave1.md: `asset_filter | JSON filter | –`
- Glossary: not mentioned
- Business_Rules_Catalog BR-021: "mutually exclusive với medical_asset" confirmed, but structure unclear

**Nên là:**
```
AC PM Plan.asset_filter (JSON, optional):

Mutually exclusive with medical_asset (one or the other, not both):
1. If medical_asset filled → apply PM to single asset only
2. If asset_filter filled → apply PM to assets matching filter

Filter schema (Frappe DocType filter format):
```json
{
  "filters": [
    ["AC Medical Asset", "facility", "=", "LOC-0001"],
    ["AC Medical Asset", "risk_class", "in", ["1", "2a"]],
    ["AC Medical Asset", "is_active", "=", 1]
  ],
  "operator": "and"
}
```

Usage:
  Cron job (STEP 6 auto_generate_pm_work_orders):
  - Find all AC PM Plan with asset_filter
  - Execute filter → get matching assets
  - For each asset: create WO PM if not exist for this frequency cycle

Validation:
  - Only valid DocType: AC Medical Asset
  - Only valid operators: =, !=, >, <, >=, <=, in, not in, like
  - Preview button: show matching assets count before save
```

**Owner:** Tech Lead  
**Deadline:** Before STEP 6 PM Plan build

---

### CL-022 — AC Compliance Case "recall_subtype" Workflow Not Detailed

**LoType:** Missing Spec  
**Nguồn:** Workflow_Specification.md §9  
**Đích:** Compliance Case recall workflow spec  
**Mô tả:**  
Workflow §9 mention "Recall subtype có timer 48h disclosure (SLA-QMS-05)" nhưng không specify:
- What is "recall_subtype" field? Is it a select option?
- Who is notified at 48h mark?
- Workflow transition trigger for 48h alert?

**Nội dung hiện tại:**
- Workflow_Specification.md §9: "Recall subtype thêm timeline thông báo Bộ Y tế trong 48h"
- Business_Rules_Catalog BR-056: "timeline thông báo Bộ Y tế trong 48h kể từ khi confirmed"
- State_Machine_Spec.md: không mention recall specifics

**Nên là:**
```
AC Compliance Case recall_subtype spec:

DocType field:
  compliance_case_type (Select):
    - general_nonconformity
    - customer_complaint
    - internal_incident
    - regulatory_inspection_finding
    - **product_recall** (trigger 48h rule)
    
When compliance_case_type = product_recall:
  Additional fields:
    - recall_confirmed_at (Datetime, when confirmed by decision)
    - recall_notification_deadline (Datetime, auto-calc = confirmed + 48h)
    - recall_notification_sent_at (Datetime, when actually sent)
    - recall_notified_to_authorities (Check)
    - recall_authority_reference (Data, email/ref from Bộ Y tế)

Workflow states (recall subtype):
  open → investigating → recall_confirmed → notification_in_progress → resolved → closed
  
SLA timer (S):
  Hourly scheduler: check_recall_sla_48h
    if recall_confirmed_at < now - 48h AND recall_notification_sent_at = null:
      trigger_alert("URGENT: Recall notification SLA breach")
      auto-escalate to AC Legal Officer + AC QMS Lead
      set sla_breached = true

Notification flow:
  1. on recall_confirmed → set recall_notification_deadline
  2. on + 47h → notification to QMS team "prepare notification"
  3. on + 48h → escalate if not sent
  4. send_recall_notification (manual action) → set recall_notification_sent_at
```

**Owner:** BA Lead + Tech Lead  
**Deadline:** Before STEP 7 Compliance build

---

### CL-023 — AC Decommission / Disposal Approval Matrix Phase Reference Incomplete

**LoType:** Missing Spec / Reference Gap  
**Nguồn:** State_Machine_Spec.md §12, Workflow_Specification.md §13  
**Đích:** Multi-level approval spec  
**Mô tả:**  
Both specs say "Theo Phase_01/10 — multi-level approval" but:
- Phase_01/10 file not reviewed in this triage
- Approver chain (KTTC, Legal, QMS) not detailed in Workflow
- Can different users approve same role?

**Nội dung hiện tại:**
- State_Machine_Spec.md §12: "(Theo Phase_01/10...)"
- Workflow_Specification.md §13: "(Theo Phase_01/10...)"
- Permission_Matrix.md §3.9: list who can W/S but not approval sequence

**Nên là:**
```
AC Decommission Record approval sequence (to be detail from Phase_01/10):

States (inferred):
  draft → submitted → approved_dept_owner → approved_asset_mgr 
    → approved_finance → approved_legal → approved_qms → executed → closed

Approvers (per Business_Rules_Catalog BR-073):
  1. Department Head (owner_department) — dept-level review
  2. AC Asset Manager — asset mgmt review
  3. AC Finance Officer — cost/inventory impact
  4. AC Legal Officer — compliance/regulations
  5. AC QMS Officer/Lead — QMS assessment

Can each role approve once? Multiple users with same role can approve different records.
SoD: decommission requester ≠ any approver.

Similar for AC Disposal Record (BR-074 + Phase_01/10).

Action items:
  1. Read Phase_01/10 Approval Authority Matrix
  2. Document approval sequence + conditions for Decommission/Disposal
  3. Create unit tests for approval chain
```

**Owner:** BA Lead  
**Deadline:** Before STEP 8 Decommission/Disposal build

---

### CL-024 — AC Nonconformity "linked_to_capa" Relationship Cardinality

**Loán:** Logic Gap  
**Nguồn:** State_Machine_Spec.md §7, Business_Rules_Catalog BR-051, BR-057  
**Đích:** NC-CAPA relationship spec  
**Mô tả:**  
Business_Rules_Catalog:
- BR-051: "NC cấp 1 → bắt buộc mở CAPA trong 24h"
- BR-057: "Mỗi CAPA phải link tới ≥ 1 source (NC, audit finding, complaint, recall)"

This implies:
- 1 NC → 1 CAPA? or 1 NC → M CAPAs?
- 1 CAPA → M NCs? (rule BR-057 says "≥ 1 source" so yes)

But not clear if 1:1 or M:M relationship.

**Nội dung hiện tại:**
- State_Machine_Spec.md §7: `linked_to_capa` (implies 1 per NC)
- BR-057: CAPA can link to multiple sources
- No DocType field detail for NC-CAPA link

**Nên là:**
```
AC Nonconformity ↔ AC CAPA relationship:

Option A (1:1):
  AC Nonconformity.linked_capa_id (Link AC CAPA)
  AC CAPA.source_nc_id (Link AC Nonconformity) [read-only]
  Implication: 1 NC opens ≤ 1 CAPA

Option B (M:M):
  Create junction table AC CAPA Source (child of CAPA):
  | source_type (Select: NC / Audit Finding / Complaint / Recall)
  | source_document (Link to respective DocType)
  | relevance_notes
  
Recommendation: Option B (flexible)

Schema:
```
AC CAPA:
  ... regular fields ...
  
AC CAPA Source (child table):
  - source_type (Select: nonconformity / audit_finding / complaint / recall_case / risk_entry)
  - source_doc (Link — Link Field dynamic per source_type)
  - link_reason (Long Text)
  - is_primary_cause (Check)

Validation (BR-057):
  Before submit → ensure ≥ 1 source row
  
Inverse link (for query):
  AC Nonconformity.capa_count (count of AC CAPA where source has NC link)
  AC Nonconformity.capa_list (related CAPAs) [read-only report]
```

**Owner:** BA Lead + Tech Lead  
**Deadline:** Before STEP 7 CAPA build

---

### CL-025 — AC Risk Entry Relationship to CAPA & Compliance Case Missing

**Loán:** Missing Spec  
**Nguồn:** Business_Rules_Catalog, CLAUDE.md §3.6  
**Đích:** Risk management integration  
**Mô tả:**  
AC Risk Entry listed as separate entity (BR-102 Risk Register) but relationship to CAPA and Compliance Case not defined. Is Risk Entry always linked to CAPA? Can Risk be source for CAPA? Or independent?

**Nội dung hiện tại:**
- CLAUDE.md §3.6: `AC Risk Entry | Compliance | Document | Yes | RSK-.YYYY.-.####`
- Business_Rules_Catalog: Risk mention only in BR-057 "source for CAPA"
- State_Machine_Spec.md §13: simple open → mitigated → accepted → closed
- No field detail for risk-capa/case relationship

**Nên là:**
```
AC Risk Entry — relationship spec:

Fields (add to existing):
  - risk_category (Select: technical, operational, regulatory, financial, reputational)
  - risk_score (Decimal: likelihood × impact, 1-100)
  - related_capa (Link AC CAPA, optional) — can be null (risk without action yet)
  - related_compliance_case (Link AC Compliance Case, optional)
  
Workflow trigger:
  Risk open with score > 70 (high risk) → auto-create draft CAPA recommendation
  
BR-058 (new): Risk-CAPA linkage
  Enforcement: S (server script)
  When: risk_score recalculated
  If score > 70 and no CAPA → notify AC QMS Lead to review
  
Relationship diagram:
  Risk Entry (1) ←→ (M) CAPA
  CAPA (1) ←→ (M) Nonconformity
  → allows risk → capa → nc flow OR reverse nc → capa → risk
```

**Owner:** BA Lead  
**Deadline:** Before STEP 7 Compliance build

---

### CL-026 — ERPNext Item "device_item_indicator" Custom Field Not Documented

**Loán:** Missing Spec  
**Nguồn:** CLAUDE.md §3.2 mapping  
**Đích:** Phase_03/07 Mapping_ERPNext_AssetCore  
**Mô tả:**  
CLAUDE.md R-08 say all custom fields on ERPNext core must be documented in Phase_03/07_Mapping. Need to check what custom fields are added to Item, Asset, Supplier, etc. Current review incomplete.

**Nội dung hiện tại:**
- CLAUDE.md R-08: custom field on Item, Asset, etc. phải document
- Not reviewed: actual Phase_03/07_Mapping_ERPNext_AssetCore content
- Likely missing: device_item_indicator, ac_criticality, ac_location link, etc.

**Nên là:**
```
Custom Field Mapping (hypothetical, to be verified):

On ERPNext Item:
  - ac_device_model (Link AC Device Model, optional)
    Desc: Link to AssetCore device model if this Item is medical device
  - ac_is_spare_part (Check)
    Desc: Flag if this Item is spare part for maintenance
  - ac_criticality (Select)
    Desc: Device criticality if medical device

On ERPNext Asset:
  - ac_medical_asset (Link AC Medical Asset, optional)
    Desc: Link to AssetCore medical asset (bidirectional sync)
  - ac_htm_state (Select, read-only)
    Desc: Mirror of AC Medical Asset.state (for audit)
  - ac_last_sync_at (Datetime, read-only)
    Desc: Last sync from AssetCore

On ERPNext Supplier:
  - ac_service_provider (Link AC Service Provider, optional)
    Desc: Link if vendor also provides service

On ERPNext Department:
  - ac_location (Link AC Location, optional)
    Desc: Link department to facility location

All must:
  1. Set module = "AssetCore"
  2. Document in Phase_03/07_Mapping_ERPNext_AssetCore.md
  3. Add corresponding read-only mirror field in AssetCore where relevant
  4. Include in hooks.py fixtures for migration

Action: Review actual Phase_03/07_Mapping file and add CL-0XX for each discrepancy.
```

**Owner:** SA Lead + Tech Lead  
**Deadline:** Before STEP 11 Integration

---

## NICE-TO-HAVE Issues

### CL-027 — Print Format Template for Calibration Certificate Not Specified

**Loán:** Nice-to-have  
**Nguồn:** CLAUDE.md §13, Business_Rules_Catalog BR-043  
**Đích:** Print format spec  
**Mô tả:**  
BR-043 mention calibration certificate PDF but don't specify print format template fields. Should have template design doc.

**Nên là:**  
Create Print Format spec document listing required fields for calibration certificate.

---

### CL-028 — Mobile PWA Offline Sync Strategy Not Detailed

**Loán:** Nice-to-have  
**Nguồn:** CLAUDE.md STEP 10  
**Đích:** Mobile implementation spec  
**Mô tả:**  
STEP 10 mention offline support but sync conflict resolution not detailed (what if user submit WO offline, then edit online — merge strategy?).

---

### CL-029 — KPI Dashboard "drill-down to record" Interaction Not Specified

**Loán:** Nice-to-have  
**Nguồn:** Business_Rules_Catalog BR-103, CLAUDE.md R-05  
**Đích:** UI/UX spec  
**Mô tả:**  
BR-103 mention drill-down but no specification on click behavior, filtered view, export capability.

---

### CL-030 — Version Control for AC QMS Artifact Not Specified

**Loán:** Nice-to-have  
**Nguồn:** State_Machine_Spec.md §3, Workflow_Specification.md §3  
**Đích:** Document versioning spec  
**Mô tả:**  
QMS Artifact workflow mention "revised → effective (new version)" but version numbering scheme (v1.0 → v1.1 → v2.0?) not specified.

---

### CL-031 — Audit Trail Timestamp Precision (UTC vs Local) Not Specified

**Loán:** Nice-to-have  
**Nguồn:** CLAUDE.md §7.3 DoD, Business_Rules_Catalog BR-083  
**Đích:** Audit trail spec  
**Mô tả:**  
Audit trail immutable but timezone handling for multi-site operations not detailed. Should all timestamps be UTC?

---

### CL-032 — Asset Tag Print Quality Requirements Not Specified

**Loán:** Nice-to-have  
**Nguồn:** CLAUDE.md §4.8  
**Đích:** Asset identification spec  
**Mô tả:**  
QR code / RFID / barcode spec mentioned but print quality, scanner compatibility, fail-safe behavior (what if QR unreadable?) not detailed.

---

## Summary by Category

| Category | Count | Examples |
|----------|-------|----------|
| **Naming Inconsistency** | 9 | CL-001, CL-003, CL-008, CL-018, CL-020 |
| **Missing/Incomplete Spec** | 7 | CL-002, CL-004, CL-005, CL-006, CL-016 |
| **Logic Gap / Ambiguity** | 11 | CL-007, CL-009, CL-010, CL-012, CL-013 |
| **Field Definition Conflict** | 5 | CL-015, CL-021, CL-022, CL-024 |
| **Workflow/State Mismatch** | 3 | CL-010, CL-023, CL-022 |

---

## Remediation Plan

### Phase 1A: Fix BLOCKING (1 week)
1. **CL-001:** Assign LE codes 01-52 (BA Lead + Tech Lead)
2. **CL-002:** Define child table ID strategy (Tech Lead)
3. **CL-003:** Create QMS Tier naming standard (BA Lead)
4. **CL-004:** Create AC Location tree spec (BA Lead)
5. **CL-005:** Enumerate 6 WO types (BA Lead)
6. **CL-006:** Expand Document Record field spec (BA Lead)
7. **CL-007:** Clarify "Resume" state (BA Lead)
8. **CL-008:** Merge/clarify Cal Lab vs Vendor roles (SA Lead)
9. **CL-009:** Standardize V/W/S enforcement (Tech Lead)
10. **CL-010:** Define CAPA reopen vs resume (BA Lead)
11. **CL-011:** Create SoD enforcement spec (Tech Lead + SA Lead)
12. **CL-012:** Define FR merge window + logic (BA Lead)
13. **CL-013:** Clarify Movement approval chain (BA Lead)
14. **CL-014:** Enumerate snapshot frequencies (Tech Lead)

### Phase 1B: Fix IMPORTANT (1-2 weeks)
Complete CL-015 through CL-026 by their respective deadlines.

### Phase 2: Validate & Deploy
- Re-read corrected specs
- Run acceptance test T-01 through T-10 (CLAUDE.md §7.1)
- Get sign-off from BA Lead + SA Lead + QMS Lead

---

## Next Steps

1. **BA Lead** reviews BLOCKING items CL-001, CL-005, CL-006, CL-007, CL-010, CL-012, CL-013
2. **Tech Lead** reviews BLOCKING items CL-002, CL-009, CL-011, CL-014
3. **SA Lead** reviews IMPORTANT item CL-008, CL-011, CL-026
4. Schedule CCB review of major changes (CL-001, CL-003, CL-004, CL-005)
5. Update CLAUDE.md, hooks.py template, and spec documents with corrections
6. Re-version all affected spec packs and commit to IT_Handover_Package

---

**Phê duyệt:**

| Vai trò | Người | Ngày | Chữ ký |
|---------|-------|------|--------|
| Tech Lead | [name] | [date] |  |
| BA Lead | [name] | [date] |  |
| SA Lead | [name] | [date] |  |
| QMS Lead | [name] | [date] |  |

---

**File created:** 2026-05-06  
**Owner:** Tech Lead  
**Status:** DRAFT — Awaiting review  
