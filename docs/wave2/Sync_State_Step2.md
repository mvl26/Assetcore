# Sync State — Step 2 Complete
# (Feed file for Step 3: Technical Design — UI, Routing, Event Hooks)

| Phiên bản | 1.0.0 |
|---|---|
| Ngày | 2026-04-22 |
| Nguồn | IMM-01_02_03_ERPNext_Mapping_Strategy.md |
| Dùng cho | Step 3 — IMM-01_02_03_Technical_Design.md |

---

## 1. DOCTYPE MAP → PRIMARY KEYS & CRITICAL FIELDS

```json
{
  "Needs Assessment": {
    "naming": "NA-.YY.-.MM.-.#####",
    "status": "exists",
    "primary_key": "name",
    "status_field": "status",
    "states": ["Draft","Submitted","Under Review","Approved","Rejected","Planned"],
    "key_fields": ["requesting_dept","equipment_type","quantity","estimated_budget",
                   "approved_budget","priority","status","request_date"],
    "child_tables": ["lifecycle_events", "planning_snapshot"],
    "module_path": "assetcore/doctype/needs_assessment/",
    "api_file": "assetcore/api/imm01.py"
  },
  "Procurement Plan": {
    "naming": "PP-.YY.-.#####",
    "status": "exists",
    "primary_key": "name",
    "status_field": "status",
    "states": ["Draft","Under Review","Approved","Budget Locked"],
    "key_fields": ["plan_year","approved_budget","allocated_budget",
                   "remaining_budget","status","approved_by"],
    "child_tables": ["items (→ Procurement Plan Item)", "lifecycle_events"],
    "module_path": "assetcore/doctype/procurement_plan/",
    "api_file": "assetcore/api/imm02.py [TO CREATE]"
  },
  "Procurement Plan Item": {
    "naming": "child-table (no series)",
    "status": "exists - PATCH needed: add 'Ordered' to status options",
    "primary_key": "name (auto)",
    "key_fields": ["needs_assessment","equipment_description","quantity",
                   "estimated_unit_cost","total_cost","priority","status","por_reference"],
    "module_path": "assetcore/doctype/procurement_plan_item/"
  },
  "Technical Specification": {
    "naming": "TS-.YY.-.#####",
    "status": "MISSING - create new",
    "primary_key": "name",
    "status_field": "status",
    "states": ["Draft","Under Review","Approved","Revised"],
    "key_fields": ["linked_plan_item","procurement_plan","regulatory_class",
                   "performance_requirements","safety_standards","status"],
    "child_tables": ["lifecycle_events"],
    "module_path": "assetcore/imm_planning/doctype/technical_specification/"
  },
  "Vendor Evaluation": {
    "naming": "VE-.YY.-.#####",
    "status": "MISSING - create new",
    "primary_key": "name",
    "status_field": "status",
    "states": ["Draft","In Progress","Approved","Cancelled"],
    "key_fields": ["linked_technical_spec","linked_plan_item","evaluation_method",
                   "recommended_vendor","selection_justification","status"],
    "child_tables": ["items (→ Vendor Evaluation Item)", "lifecycle_events"],
    "module_path": "assetcore/imm_planning/doctype/vendor_evaluation/"
  },
  "Vendor Evaluation Item": {
    "naming": "child-table (no series)",
    "status": "MISSING - create new",
    "key_fields": ["vendor","technical_score","financial_score","profile_score",
                   "risk_score","total_score","score_band","compliant_with_ts",
                   "has_nd98_registration","is_recommended"],
    "computed": ["total_score = tech×0.4 + fin×0.3 + profile×0.2 + risk×0.1",
                 "score_band = A/B/C/D derived from total_score"]
  },
  "Purchase Order Request": {
    "naming": "POR-.YY.-.#####",
    "status": "STUB - dir exists, no JSON. Create full JSON + py",
    "primary_key": "name",
    "status_field": "status",
    "states": ["Draft","Under Review","Approved","Released","Fulfilled","Cancelled"],
    "key_fields": ["linked_plan_item","linked_evaluation","linked_technical_spec",
                   "vendor","quantity","unit_price","total_amount",
                   "requires_director_approval","status","approved_by","release_date"],
    "child_tables": ["lifecycle_events"],
    "module_path": "assetcore/doctype/purchase_order_request/",
    "director_threshold": 500000000
  }
}
```

---

## 2. CUSTOM FIELDS INJECTED → WAVE 1

```json
[
  {
    "dt": "Asset Lifecycle Event",
    "fieldname": "event_domain",
    "fieldtype": "Select",
    "options": "imm_master|imm_deployment|imm_operations|imm_planning|imm_eol",
    "insert_after": "event_type"
  },
  {
    "dt": "IMM Device Model",
    "fieldname": "nd98_class",
    "fieldtype": "Select",
    "options": "|Class A|Class B|Class C|Class D"
  },
  {
    "dt": "IMM Device Model",
    "fieldname": "vn_registration_number",
    "fieldtype": "Data"
  }
]
```

---

## 3. API ENDPOINTS EXPECTED (cho Frontend)

```
IMM-01 — assetcore/api/imm01.py (EXISTS - verify completeness)
  POST  create_needs_assessment(...)         → {name, status}
  GET   get_needs_assessment(name)           → full doc dict
  GET   list_needs_assessments(filters...)   → {total, items[]}
  POST  submit_for_review(name)              → {status: Submitted}
  POST  begin_technical_review(name)        → {status: Under Review}
  POST  approve_needs_assessment(name, approved_budget, notes)  → {status: Approved}
  POST  reject_needs_assessment(name, reason) → {status: Rejected}

IMM-02 — assetcore/api/imm02.py (TO CREATE)
  POST  create_procurement_plan(plan_year, approved_budget)
  POST  add_plan_item(plan_name, item_data)  → recalc remaining_budget
  GET   get_procurement_plan(name)
  GET   list_procurement_plans(year, status)
  POST  submit_plan_for_review(name)
  POST  approve_plan(name, notes)
  POST  lock_budget(name)                   → status: Budget Locked
  POST  raise_po_request(plan_name, item_idx) → creates POR stub

IMM-03 — assetcore/api/imm03.py (TO CREATE)
  POST  create_technical_spec(linked_plan_item, data...)
  POST  approve_technical_spec(name, notes)
  POST  create_vendor_evaluation(linked_ts, evaluation_method)
  POST  add_vendor_to_evaluation(ve_name, vendor_data_with_scores)
  POST  approve_vendor_evaluation(name, recommended_vendor, justification)
  POST  create_purchase_order_request(linked_plan_item, linked_ve, data...)
  POST  approve_por(name, notes)
  POST  release_por(name)                   → async enqueue IMM-04 notify
  GET   get_planning_dashboard_data()       → KPI aggregates
```

---

## 4. FRONTEND ROUTES CẦN THÊM (cho Step 3)

```
Planning Group (Khối Kế Hoạch):

  /planning/needs-assessments         → list view
  /planning/needs-assessments/new     → create form
  /planning/needs-assessments/:name   → detail/edit

  /planning/procurement-plans         → list view (theo năm)
  /planning/procurement-plans/new     → create form
  /planning/procurement-plans/:name   → detail + items table

  /planning/technical-specs           → list view
  /planning/technical-specs/new       → create form
  /planning/technical-specs/:name     → detail

  /planning/vendor-evaluations        → list view
  /planning/vendor-evaluations/:name  → detail + scoring table

  /planning/purchase-order-requests   → list view
  /planning/purchase-order-requests/:name → detail + approval flow

  /planning/dashboard                 → KPI dashboard (budget, timelines)
```

---

## 5. CONTROLLER HOOKS → DOWNSTREAM TRIGGERS

```
Needs Assessment.on_submit (Approved):
  → auto notify Ops Manager to add to PP
  → log event: needs_assessment_approved / domain: imm_planning

Procurement Plan.on_submit (Budget Locked):
  → set all PP Items: status = PO Raised (if status = Pending)
  → notify Ops Manager to create TS for each item

Technical Specification.on_submit (Approved):
  → notify: TS ready for vendor evaluation

Vendor Evaluation.on_submit (Approved):
  → auto-populate POR.vendor = recommended_vendor (if POR exists)

Purchase Order Request.on_submit (Released):
  → set PP Item.status = Ordered
  → frappe.enqueue("...notify_imm04_readiness", por_name=self.name)
  → log event: por_released / domain: imm_planning
```

---

## 6. WAVE 1 REUSABLE COMPONENTS (cho Step 3 Frontend)

```
Có thể tái sử dụng từ Wave 1:
  - StatusBadge component (WorkOrderStatus → map sang Planning states)
  - LifecycleEventTimeline component (đã có cho IMM-04/08/09)
  - FilterBar / SearchPanel component
  - DocumentAttachmentPanel
  - AuditTrailSection (inline lifecycle_events table view)
  - ConfirmActionModal (approve/reject với notes field)

Cần tạo mới cho Wave 2:
  - BudgetProgressBar (allocated vs approved — PP module)
  - VendorScoringTable (float inputs + auto-calculated total)
  - PriorityPlanningMatrix (items grouped by priority + quarter)
  - PORApprovalFlow (conditional: hiện Director step nếu >500M)
```

---

## 7. UNRESOLVED DEPENDENCIES → STEP 3

```
- [ ] Xác nhận Wave 1 router (frontend/src/router/index.ts) có navigation
      group "Planning" chưa hay phải thêm mới vào sidebar
- [ ] IMM-01 API (imm01.py) đã có begin_technical_review() endpoint chưa?
      (file đã tồn tại nhưng chỉ đọc được 80 dòng đầu)
- [ ] AC Supplier vs ERPNext Supplier: VE Item dùng AC Supplier hay Supplier?
      Cần consistent với cách IMM-04 chọn vendor
- [ ] Permission filter: Clinical User chỉ xem NA của khoa mình →
      cần User Permission filter trên field requesting_dept
- [ ] imm_planning module có trong modules.txt chưa? Cần đăng ký trước migrate
```
