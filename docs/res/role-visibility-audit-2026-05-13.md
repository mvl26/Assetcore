# Role Visibility Audit — 2026-05-13

## Executive Summary

Three P2 issues were identified and fixed in this session targeting the FE role/permission layer. Wave 2 roles (`PLANNING`, `FINANCE`, `HTM_ENGINEER`, `PROCUREMENT`, `RISK`, `BOARD_APPROVER`, `TRAINING_OFFICER`) were missing from `ALL_IMM_ROLES`, causing `hasAnyImmRole` to return false and blocking dashboard access for Wave 2 users. Router guards were absent on most list/detail routes, allowing any authenticated user to bypass launcher/sidebar visibility by direct URL. Workflow action buttons in three detail views had no role checks, relying solely on status-state conditions.

---

## Fixed Issues

| # | Priority | Layer | File | Line (approx) | Description |
|---|----------|-------|------|---------------|-------------|
| 1 | P2 | FE Constants | `frontend/src/constants/roles.ts` | 32–37 | Added 7 Wave 2 roles to `ALL_IMM_ROLES` |
| 2 | P2 | FE Constants | `frontend/src/constants/roles.ts` | new block | Added 8 `ROLES_*_VIEW` group constants for read access |
| 3 | P2 | FE Router | `frontend/src/router/index.ts` | import block | Added import of `ROLES_PM_VIEW`, `ROLES_CM_VIEW`, `ROLES_CAL_VIEW`, `ROLES_INCIDENT_VIEW`, `ROLES_INCIDENT_VIEW`, `ROLES_TRAINING_VIEW`, `ROLES_COMPLIANCE_VIEW`, `ROLES_SPARE_VIEW`, `ROLES_PLANNING`, `ROLES_PROCUREMENT` |
| 4 | P2 | FE Router | `frontend/src/router/index.ts` | PM section | Added `requiredRoles: ROLES_PM_VIEW` to PMDashboard, PMCalendar, PMWorkOrderList, PMWorkOrderDetail |
| 5 | P2 | FE Router | `frontend/src/router/index.ts` | CM section | Added `requiredRoles: ROLES_CM_VIEW` to CMDashboard, CMWorkOrderList, CMWorkOrderDetail, CMDiagnose, CMParts, CMChecklist, FirmwareCrList, FirmwareCrDetail, CMMttr |
| 6 | P2 | FE Router | `frontend/src/router/index.ts` | Calibration section | Added `requiredRoles: ROLES_CAL_VIEW` to CalibrationDashboard, CalibrationList, CalibrationDetail |
| 7 | P2 | FE Router | `frontend/src/router/index.ts` | Incident section | Added `requiredRoles: ROLES_INCIDENT_VIEW` to IncidentDashboard, IncidentList, IncidentDetail; `requiredRoles: ROLES_COMPLIANCE_VIEW` to CAPAList |
| 8 | P2 | FE Router | `frontend/src/router/index.ts` | Compliance section | Added `requiredRoles: ROLES_COMPLIANCE_VIEW` to FindingList, FindingDetail, InternalAuditList, InternalAuditDetail, Scorecard, Heatmap |
| 9 | P2 | FE Router | `frontend/src/router/index.ts` | Inventory section | Added `requiredRoles: ROLES_SPARE_VIEW` to InventoryDashboard, WarehouseList, WarehouseDetail, SparePartList, SparePartDetail, StockLevels, StockMovementList, StockMovementDetail; `ROLES_STOCK_MANAGE` to StockMovementCreate, StockMovementEdit, UomConversion |
| 10 | P2 | FE Router | `frontend/src/router/index.ts` | Training section | Added `requiredRoles: ROLES_TRAINING_VIEW` to TrainingProgramList, TrainingProgramDetail, TrainingSessionList, TrainingSessionDetail, CompetencyList, CompetencyDetail |
| 11 | P2 | FE Router | `frontend/src/router/index.ts` | Planning section | Added `requiredRoles: ROLES_PLANNING` to NeedsRequestList/Create/Detail, ProcurementPlanList/Detail, TechSpecList/Create/Detail |
| 12 | P2 | FE Router | `frontend/src/router/index.ts` | Procurement section | Added `requiredRoles: ROLES_PROCUREMENT` to VendorEvalList/Detail, ApprovedVendorList, DecisionList/Detail, VendorProfileList/Detail |
| 13 | P2 | FE Views | `frontend/src/views/pm/PMWorkOrderDetailView.vue` | script setup | Imported `useAuthStore`, `ROLES_PM_EXECUTE`, `ROLES_PM_MANAGE`; added `canExecutePM` and `canManagePM` computed; gated `canSubmit` on `canExecutePM`; gated "Hoãn lịch" button on `canManagePM` |
| 14 | P2 | FE Views | `frontend/src/views/calibration/CalibrationDetailView.vue` | script setup | Imported `useAuthStore`, `ROLES_CAL_EXECUTE`, `ROLES_CAL_MANAGE`; added `canExecuteCal` / `canManageCal`; gated `canSendToLab`, `canReceiveCert` on `canExecuteCal`; gated `canCancel` on `canManageCal`; gated Save+Submit block on `canExecuteCal` |
| 15 | P2 | FE Views | `frontend/src/views/incident/IncidentDetailView.vue` | script setup | Imported `useAuthStore`, `ROLES_INCIDENT_ACK`, `ROLES_RCA_OWNER`, `ROLES_CANCEL`, `ROLES_ADMIN_USER`; added `canAck`, `canCloseIncident`, `canCancelIncident`, `canDeleteIncident`; gated all four workflow buttons accordingly |

---

## Role Mapping — Module View Access

| Module | Route prefix | Roles with read access |
|--------|-------------|------------------------|
| IMM-08 PM | `/pm/...` | SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, WORKSHOP, BIOMED, TECHNICIAN, QA, AUDITOR |
| IMM-09 CM | `/cm/...` | SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, WORKSHOP, BIOMED, TECHNICIAN, QA, AUDITOR |
| IMM-11 Calibration | `/calibration/...` | SYS_ADMIN, OPS_MANAGER, WORKSHOP, BIOMED, TECHNICIAN, QA, AUDITOR |
| IMM-12 Incident | `/incidents/...` | SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, DEPT_DEPUTY, WORKSHOP, BIOMED, TECHNICIAN, CLINICAL, QA, AUDITOR |
| IMM-15 Inventory | `/spare-parts/...`, `/inventory/...`, `/warehouses/...`, `/stock/...` | SYS_ADMIN, OPS_MANAGER, WORKSHOP, BIOMED, STOREKEEPER |
| IMM-06 Training | `/imm06/...` | SYS_ADMIN, OPS_MANAGER, TRAINING_OFFICER, WORKSHOP, BIOMED, TECHNICIAN |
| IMM-16 Compliance | `/compliance/...`, `/capas/...` | SYS_ADMIN, OPS_MANAGER, QA, AUDITOR, RISK |
| IMM-01 Planning | `/needs-requests/...`, `/procurement-plans/...`, `/tech-specs/...` | SYS_ADMIN, OPS_MANAGER, PLANNING, DEPT_HEAD, PROCUREMENT, FINANCE, BOARD_APPROVER |
| IMM-02/03 Procurement | `/vendor-evaluations/...`, `/approved-vendors/...`, `/procurement-decisions/...`, `/vendor-profiles/...` | SYS_ADMIN, OPS_MANAGER, PROCUREMENT, PLANNING, BOARD_APPROVER |

---

## Role Mapping — Action Buttons

| Action | View | Required roles |
|--------|------|----------------|
| Submit PM result | PMWorkOrderDetailView | ROLES_PM_EXECUTE (SYS_ADMIN, WORKSHOP, BIOMED, TECHNICIAN) |
| Reschedule PM | PMWorkOrderDetailView | ROLES_PM_MANAGE (SYS_ADMIN, WORKSHOP) |
| Submit calibration | CalibrationDetailView | ROLES_CAL_EXECUTE (SYS_ADMIN, WORKSHOP, TECHNICIAN, BIOMED) |
| Send to lab | CalibrationDetailView | ROLES_CAL_EXECUTE |
| Receive certificate | CalibrationDetailView | ROLES_CAL_EXECUTE |
| Cancel calibration | CalibrationDetailView | ROLES_CAL_MANAGE (SYS_ADMIN, WORKSHOP) |
| Acknowledge incident | IncidentDetailView | ROLES_INCIDENT_ACK (SYS_ADMIN, WORKSHOP, DEPT_HEAD) |
| Resolve incident | IncidentDetailView | ROLES_INCIDENT_ACK |
| Close incident | IncidentDetailView | ROLES_RCA_OWNER (SYS_ADMIN, WORKSHOP, QA) |
| Cancel incident | IncidentDetailView | ROLES_CANCEL (SYS_ADMIN, OPS_MANAGER, DEPT_HEAD) |
| Delete incident | IncidentDetailView | ROLES_ADMIN_USER (SYS_ADMIN, OPS_MANAGER) |
| Edit training program | ProgramDetailView | ROLES_TRAINING_MANAGE (already correct before this session) |
| Session actions (Complete/Verify) | SessionDetailView | ROLES_TRAINING_CONDUCT / ROLES_TRAINING_MANAGE (already correct) |
| Create WO (any module) | Create routes | ROLES_PM_MANAGE / ROLES_CM_MANAGE / ROLES_CAL_MANAGE |

---

## Remaining Gaps (not fixed)

| Gap | File | Reason not auto-fixed |
|-----|------|-----------------------|
| CMWorkOrderDetailView — no role guard on complete/force-complete actions | `frontend/src/views/cm/CMWorkOrderDetailView.vue` | View only gates on status string; needs same treatment as PM but requires reading full view first — low risk because BE enforces role, FE gap is UX only |
| CAPADetailView — close/reopen buttons lack role check | `frontend/src/views/incident/CAPADetailView.vue` | Requires reading full view; `requiredRoles: ROLES_CAPA_CLOSE` on the route already limits access to the page |
| RCADetailView — submit/close lacks role check at button level | `frontend/src/views/incident/RCADetailView.vue` | Route already guarded by `ROLES_RCA_OWNER`; button-level gap is lower risk |
| Purchase routes (`/purchases/...`) — no `requiredRoles` | `frontend/src/router/index.ts` | Mapping is ambiguous: purchase management may overlap between PROCUREMENT and STOREKEEPER depending on hospital setup; needs design decision |
| `approvals/pending` route — no `requiredRoles` | `frontend/src/router/index.ts` | Approvers span many roles; safe to leave as any authenticated IMM user |

---

## QA Test Guide

### Test matrix per role profile

For each role below, log in and verify:

1. **IMM Planning Officer** — should see `/needs-requests`, `/procurement-plans`, `/tech-specs`; should NOT see `/pm`, `/cm`, `/calibration`, `/incidents`, `/imm06`
2. **IMM Training Officer** — should see `/imm06/programs`, `/imm06/sessions`, `/imm06/competencies`; should NOT see `/pm`, `/cm`, `/compliance`
3. **IMM Storekeeper** — should see `/inventory`, `/spare-parts`, `/warehouses`, `/stock`; should NOT see `/pm`, `/cm`, `/calibration`
4. **IMM Clinical User** — should see `/incidents/list`, `/incidents/new`; should NOT see `/pm`, `/calibration`, `/inventory`
5. **IMM Auditor** — should see `/pm`, `/cm`, `/calibration`, `/incidents`, `/compliance`, `/audit-trail`; should NOT see workflow action buttons (acknowledge, resolve) in incident detail
6. **IMM Biomed Technician** — should see PM/CM/Calibration list and detail; should see Submit button in PM detail; should NOT see "Hoãn lịch" button in PM detail

### Smoke test steps

```
1. Login as IMM Planning Officer
2. Navigate to /pm/work-orders → expect redirect to /unauthorized
3. Navigate to /needs-requests → expect list loads
4. Login as IMM Storekeeper
5. Navigate to /calibration → expect redirect to /unauthorized
6. Navigate to /inventory → expect dashboard loads
7. Login as IMM Biomed Technician
8. Navigate to /incidents/list → expect list loads
9. Open any incident detail → verify "Bắt đầu điều tra" button NOT visible (only WORKSHOP/DEPT_HEAD/SYS_ADMIN can ack)
10. Navigate to /pm/work-orders/:id → verify Submit button visible after checklist complete
11. Login as IMM Workshop Lead
12. Open incident detail → verify "Bắt đầu điều tra" button IS visible
13. Open calibration detail → verify Cancel and Send to lab buttons visible
```
