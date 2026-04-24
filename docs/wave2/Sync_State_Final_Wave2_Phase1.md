# Sync State — FINAL (Wave 2 Phase 1 Complete)
# Master Index — IMM-01 / IMM-02 / IMM-03 Design System

| Phiên bản | 1.0.0 |
|---|---|
| Ngày | 2026-04-22 |
| Tạo bởi | Wave 2 Phase 1 Design Session |
| Trạng thái | **DESIGN COMPLETE — Ready for Sprint Planning** |
| Nguồn tổng hợp | BA_Business_Analysis · ERPNext_Mapping_Strategy · Technical_Design |

---

## MASTER INDEX

---

### A. DOCTYPES

| # | DocType | Naming | Status | Module path | Submittable |
|---|---|---|---|---|---|
| 1 | `Needs Assessment` | `NA-.YY.-.MM.-.#####` | EXISTS (JSON+py) | `assetcore/doctype/needs_assessment/` | Yes |
| 2 | `Procurement Plan` | `PP-.YY.-.#####` | EXISTS (JSON) | `assetcore/doctype/procurement_plan/` | Yes |
| 3 | `Procurement Plan Item` | child | EXISTS (JSON) — **PATCH: add "Ordered" status** | `assetcore/doctype/procurement_plan_item/` | No |
| 4 | `Purchase Order Request` | `POR-.YY.-.#####` | STUB (dir empty) — **CREATE** | `assetcore/doctype/purchase_order_request/` | Yes |
| 5 | `Technical Specification` | `TS-.YY.-.#####` | MISSING — **CREATE** | `assetcore/imm_planning/doctype/technical_specification/` | Yes |
| 6 | `Vendor Evaluation` | `VE-.YY.-.#####` | MISSING — **CREATE** | `assetcore/imm_planning/doctype/vendor_evaluation/` | Yes |
| 7 | `Vendor Evaluation Item` | child | MISSING — **CREATE** | `assetcore/imm_planning/doctype/vendor_evaluation_item/` | No |
| 8 | `IMM Planning Device Snapshot` | child | MISSING — **CREATE** | `assetcore/imm_planning/doctype/imm_planning_device_snapshot/` | No |

**Custom Field injections (Wave 1 DocTypes):**
- `Asset Lifecycle Event` ← `event_domain` (Select)
- `IMM Device Model` ← `nd98_class` (Select, NĐ98 A/B/C/D)
- `IMM Device Model` ← `vn_registration_number` (Data)

---

### B. API ENDPOINTS

| # | File | Endpoint | Method | Module |
|---|---|---|---|---|
| 1 | `api/imm01.py` | `create_needs_assessment` | POST | IMM-01 |
| 2 | `api/imm01.py` | `get_needs_assessment` | GET | IMM-01 |
| 3 | `api/imm01.py` | `list_needs_assessments` | GET | IMM-01 |
| 4 | `api/imm01.py` | `submit_for_review` | POST | IMM-01 |
| 5 | `api/imm01.py` | `begin_technical_review` | POST | IMM-01 — **VERIFY exists** |
| 6 | `api/imm01.py` | `approve_needs_assessment` | POST | IMM-01 |
| 7 | `api/imm01.py` | `reject_needs_assessment` | POST | IMM-01 |
| 8 | `api/imm02.py` | `create_procurement_plan` | POST | IMM-02 — **CREATE** |
| 9 | `api/imm02.py` | `add_plan_item` | POST | IMM-02 — **CREATE** |
| 10 | `api/imm02.py` | `get_procurement_plan` | GET | IMM-02 — **CREATE** |
| 11 | `api/imm02.py` | `list_procurement_plans` | GET | IMM-02 — **CREATE** |
| 12 | `api/imm02.py` | `submit_plan_for_review` | POST | IMM-02 — **CREATE** |
| 13 | `api/imm02.py` | `approve_plan` | POST | IMM-02 — **CREATE** |
| 14 | `api/imm02.py` | `lock_budget` | POST | IMM-02 — **CREATE** |
| 15 | `api/imm03.py` | `create_technical_spec` | POST | IMM-03 — **CREATE** |
| 16 | `api/imm03.py` | `approve_technical_spec` | POST | IMM-03 — **CREATE** |
| 17 | `api/imm03.py` | `create_vendor_evaluation` | POST | IMM-03 — **CREATE** |
| 18 | `api/imm03.py` | `add_vendor_to_evaluation` | POST | IMM-03 — **CREATE** |
| 19 | `api/imm03.py` | `approve_vendor_evaluation` | POST | IMM-03 — **CREATE** |
| 20 | `api/imm03.py` | `create_purchase_order_request` | POST | IMM-03 — **CREATE** |
| 21 | `api/imm03.py` | `approve_por` | POST | IMM-03 — **CREATE** |
| 22 | `api/imm03.py` | `release_por` | POST | IMM-03 — **CREATE** |
| 23 | `api/imm03.py` | `get_planning_dashboard_data` | GET | IMM-03 — **CREATE** |

---

### C. FRONTEND ROUTES

| # | Path | Name | View file | Required Roles |
|---|---|---|---|---|
| 1 | `/planning/dashboard` | `PlanningDashboard` | `PlanningDashboardView.vue` | All (auth) |
| 2 | `/planning/needs-assessments` | `NAList` | `NAListView.vue` | All (auth) |
| 3 | `/planning/needs-assessments/new` | `NACreate` | `NACreateView.vue` | ROLES_PLANNING_CREATE |
| 4 | `/planning/needs-assessments/:id` | `NADetail` | `NADetailView.vue` | All (auth) |
| 5 | `/planning/procurement-plans` | `PPList` | `PPListView.vue` | ROLES_PLANNING_VIEW |
| 6 | `/planning/procurement-plans/new` | `PPCreate` | `PPCreateView.vue` | ROLES_PLANNING_MANAGE |
| 7 | `/planning/procurement-plans/:id` | `PPDetail` | `PPDetailView.vue` | All (auth) |
| 8 | `/planning/technical-specs` | `TSList` | `TSListView.vue` | ROLES_PLANNING_VIEW |
| 9 | `/planning/technical-specs/new` | `TSCreate` | `TSCreateView.vue` | ROLES_PLANNING_MANAGE |
| 10 | `/planning/technical-specs/:id` | `TSDetail` | `TSDetailView.vue` | All (auth) |
| 11 | `/planning/vendor-evaluations` | `VEList` | `VEListView.vue` | ROLES_PLANNING_VIEW |
| 12 | `/planning/vendor-evaluations/:id` | `VEDetail` | `VEDetailView.vue` | ROLES_PLANNING_VIEW |
| 13 | `/planning/purchase-order-requests` | `PORList` | `PORListView.vue` | ROLES_PLANNING_VIEW |
| 14 | `/planning/purchase-order-requests/new` | `PORCreate` | `PORCreateView.vue` | ROLES_PLANNING_MANAGE |
| 15 | `/planning/purchase-order-requests/:id` | `PORDetail` | `PORDetailView.vue` | All (auth) |

**Files cần sửa (Wave 1):**
- `frontend/src/router/index.ts` — append 15 routes + redirect `/planning`
- `frontend/src/constants/roles.ts` — append 4 role groups Wave 2
- `frontend/src/components/layout/AppSidebar.vue` — append 1 navGroup

---

### D. FRONTEND VIEWS (cần tạo mới)

| # | File | Pattern nguồn (Wave 1) | Status |
|---|---|---|---|
| 1 | `views/PlanningDashboardView.vue` | `CMDashboardView.vue` | CREATE |
| 2 | `views/NAListView.vue` | `CMWorkOrderListView.vue` | CREATE |
| 3 | `views/NACreateView.vue` | `CommissioningCreateView.vue` | CREATE |
| 4 | `views/NADetailView.vue` | `CommissioningDetailView.vue` | CREATE |
| 5 | `views/PPListView.vue` | `CMWorkOrderListView.vue` | CREATE |
| 6 | `views/PPCreateView.vue` | `CommissioningCreateView.vue` | CREATE |
| 7 | `views/PPDetailView.vue` | `CommissioningDetailView.vue` | CREATE |
| 8 | `views/TSListView.vue` | `CMWorkOrderListView.vue` | CREATE |
| 9 | `views/TSCreateView.vue` | `CommissioningCreateView.vue` | CREATE |
| 10 | `views/TSDetailView.vue` | `CommissioningDetailView.vue` | CREATE |
| 11 | `views/VEListView.vue` | `CMWorkOrderListView.vue` | CREATE |
| 12 | `views/VEDetailView.vue` | `CommissioningDetailView.vue` | CREATE |
| 13 | `views/PORListView.vue` | `CMWorkOrderListView.vue` | CREATE |
| 14 | `views/PORCreateView.vue` | `CommissioningCreateView.vue` | CREATE |
| 15 | `views/PORDetailView.vue` | `CommissioningDetailView.vue` | CREATE |

---

### E. FRONTEND COMPONENTS

| # | File | Type | Status |
|---|---|---|---|
| 1 | `components/common/StatusBadge.vue` | REUSE | Cần thêm Planning states vào color map |
| 2 | `components/common/BaseModal.vue` | REUSE | Không sửa |
| 3 | `components/common/BasePagination.vue` | REUSE | Không sửa |
| 4 | `components/common/SmartSelect.vue` | REUSE | Không sửa |
| 5 | `components/common/LinkSearch.vue` | REUSE | Không sửa |
| 6 | `components/imm04/WorkflowActions.vue` | REUSE | Truyền actions[] prop mới |
| 7 | `components/imm-planning/BudgetProgressBar.vue` | **NEW** | CREATE |
| 8 | `components/imm-planning/VendorScoringTable.vue` | **NEW** | CREATE (inspired by BaselineTestTable) |
| 9 | `components/imm-planning/PORApprovalBadge.vue` | **NEW** | CREATE |
| 10 | `components/imm-planning/PPItemsTable.vue` | **NEW** | CREATE (inspired by DocumentChecklist pattern) |

**Tổng: 6 reuse + 4 new components**

---

### F. ROLES & PERMISSIONS

| # | Role | Type | Status |
|---|---|---|---|
| 1 | `IMM Clinical User` | EXISTING | Thêm User Permission filter trên `requesting_dept` |
| 2 | `IMM Department Head` | EXISTING | Thêm quyền trên Wave 2 DocTypes |
| 3 | `IMM Operations Manager` | EXISTING | Thêm quyền trên Wave 2 DocTypes |
| 4 | `IMM Finance Officer` | **NEW** | CREATE via fixtures |
| 5 | `IMM Technical Reviewer` | **NEW** | CREATE via fixtures |

---

### G. WORKFLOWS

| # | Workflow | DocType | States | Status |
|---|---|---|---|---|
| 1 | Needs Assessment Workflow | Needs Assessment | 6 states | **CREATE** |
| 2 | Procurement Plan Workflow | Procurement Plan | 4 states | **CREATE** |
| 3 | Technical Specification Workflow | Technical Specification | 4 states | **CREATE** |
| 4 | Vendor Evaluation Workflow | Vendor Evaluation | 4 states | **CREATE** |
| 5 | Purchase Order Request Workflow | Purchase Order Request | 6 states | **CREATE** |

---

### H. EVENT HOOKS & BACKGROUND JOBS

| # | Trigger | Event | Type | Effect |
|---|---|---|---|---|
| 1 | `NeedsAssessment.on_update_after_submit` (Approved) | `needs_assessment_approved` | Sync notify | Notify Ops Manager |
| 2 | `ProcurementPlan.on_update_after_submit` (Budget Locked) | `budget_locked` | Sync | Set PP Items → PO Raised |
| 3 | `PurchaseOrderRequest.on_update_after_submit` (Released) | `por_released` | Sync + Enqueue | Set PP Item → Ordered; async notify |
| 4 | `notify_imm04_readiness` | — | **Background Job** | Notify Storekeeper + Ops + Dept Head |
| 5 | `imm_planning.scheduler.check_planning_sla` | — | **Daily Scheduler** | Flag overdue NAs (>14 ngày) & PPs (>30 ngày) |

---

## FINAL UNRESOLVED DEPENDENCIES (Sprint Planning Checklist)

> Đây là 5 điểm bắt buộc Dev/Tech Lead phải quyết định trước Sprint 1 ngày 1.

---

**[RISK-01] — HIGH | `begin_technical_review()` trong `imm01.py`**
- Chỉ đọc được 80 dòng đầu — chưa xác nhận endpoint này có hay không.
- **Action:** Tech Lead đọc toàn bộ `assetcore/api/imm01.py` trước sprint.
- **If missing:** Thêm function vào file hiện có — không tạo file mới.

**[RISK-02] — HIGH | Pinia Store pattern cho Wave 2**
- Wave 1 dùng `useImm09Store`, `useImm08Store`, v.v. (Pinia).
- Wave 2 cần tạo: `usePlanningStore` (hoặc tách: `useNAStore`, `usePPStore`, `usePORStore`).
- **Decision needed:** 1 store chung cho toàn Planning block hay tách per-module?
- **Recommendation:** 1 `usePlanningStore` với namespaced getters — giảm boilerplate.

**[RISK-03] — MEDIUM | `StatusBadge.vue` color map**
- Wave 1 color map chỉ có states của WO/Commissioning.
- Planning states (Budget Locked, PO Raised, Ordered, Released...) cần màu mới.
- **Action:** Đọc `StatusBadge.vue`, thêm Planning state-to-color mapping vào config object — không phá Wave 1 mappings.

**[RISK-04] — MEDIUM | AC Department `head_of_dept` field**
- `notify_imm04_readiness.py` gọi `frappe.db.get_value("AC Department", na.requesting_dept, "head_of_dept")`.
- Chưa xác nhận `AC Department` DocType có field `head_of_dept` hay tên khác.
- **Action:** `cat assetcore/assetcore/doctype/ac_department/ac_department.json` để xác nhận field name.
- **Fallback:** Nếu không có → notify Dept Head role chung thay vì per-dept.

**[RISK-05] — LOW | `imm02.py` path convention**
- `Needs Assessment` và `Procurement Plan` nằm ở `assetcore/doctype/` (không phải `imm_planning/`).
- `imm02.py` nên đặt ở `assetcore/api/imm02.py` (consistent với `imm01.py`) hay `imm_planning/api/imm02.py`?
- **Recommendation:** `assetcore/api/imm02.py` — consistent với pattern Wave 1 hiện có.
- **Decision:** Tech Lead confirm trước khi tạo file.

---

## DESIGN SCORECARD

| Hạng mục | Quyết định | Tuân thủ nguyên tắc |
|---|---|---|
| DocTypes tạo mới | 4 (TS, VE, VE Item, Snapshot) | ✅ Extend only |
| DocTypes Wave 1 inject | 2 (ALE, Device Model) via Custom Field fixture | ✅ Không sửa JSON Wave 1 |
| Frontend components mới | 4 | ✅ Minimum necessary |
| Frontend components tái dụng | 6 | ✅ Reuse maximum |
| Background jobs | 1 (`frappe.enqueue`) | ✅ Async, không blocking |
| Vendor scoring | Float + weighted calc in Python | ✅ D4 |
| Permission isolation | Frappe User Permission | ✅ F4 — không hardcode API |
| IMM-04 trigger | Notify only, no ghost record | ✅ D7 |
| Audit trail | `event_domain` injected | ✅ D2 |
| NĐ98 compliance | `nd98_class` custom field | ✅ D5 |

---

## TÓM TẮT DELIVERABLES WAVE 2 PHASE 1

```
docs/wave2/
├── IMM-01_02_03_BA_Business_Analysis.md       ← Step 1 ✅
├── Sync_State_Step1.md                        ← Step 1 checkpoint ✅
├── IMM-01_02_03_ERPNext_Mapping_Strategy.md   ← Step 2 ✅
├── Sync_State_Step2.md                        ← Step 2 checkpoint ✅
├── IMM-01_02_03_Technical_Design.md           ← Step 3 ✅
└── Sync_State_Final_Wave2_Phase1.md           ← This file ✅

Tổng: 6 files · ~100KB tài liệu thiết kế
```

---

**PHASE 1 STATUS: COMPLETE**
**Next action: Sprint Planning — Tech Lead review RISK-01 → RISK-05 → Confirm → Sprint 1 kickoff**
