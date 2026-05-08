> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# WORKFLOW & PERMISSION INDEX — WAVE 1

**Tham chiếu:**
- Workflow chi tiết: Phase_04/01_Workflow_Specification.
- Permission Matrix: Phase_04/02_Permission_Matrix.
- Approval Routing: Phase_04/06_Approval_Routing_Rules.

---

## 1. Danh sách Workflow Wave 1

| # | Workflow | DocType |
|---|----------|---------|
| 1 | AC Medical Asset Workflow | AC Medical Asset |
| 2 | AC Document Record Workflow | AC Document Record |
| 3 | AC QMS Artifact Workflow | AC QMS Artifact |
| 4 | AC Work Order Workflow | AC Work Order |
| 5 | AC Failure Report Workflow | AC Failure Report |
| 6 | AC Calibration Record Workflow | AC Calibration Record |
| 7 | AC PM Plan Workflow | AC PM Plan |
| 8 | AC Calibration Plan Workflow | AC Calibration Plan |
| 9 | AC Nonconformity Workflow | AC Nonconformity |
| 10 | AC CAPA Workflow | AC CAPA |
| 11 | AC Compliance Case Workflow | AC Compliance Case |
| 12 | AC Risk Entry Workflow | AC Risk Entry |
| 13 | AC Change Control Request Workflow | AC Change Control Request |
| 14 | AC Audit Workflow | AC Audit |
| 15 | AC Management Review Workflow | AC Management Review |
| 16 | AC Asset Movement Workflow | AC Asset Movement |
| 17 | AC Stand-Down Record Workflow | AC Stand-Down Record |
| 18 | AC Decommission Record Workflow | AC Decommission Record |
| 19 | AC Disposal Record Workflow | AC Disposal Record |
| 20 | AC Custodian Assignment Workflow | AC Custodian Assignment |
| 21 | AC IQ-OQ-PQ Record Workflow | AC IQ-OQ-PQ Record |
| 22 | AC Training Session Workflow | AC Training Session |

## 2. Roles list (Phase_00/07 §2.5)

| Role | Description |
|------|-------------|
| AC Asset Manager | Trưởng/Phó VTTBYT |
| AC BME Engineer | KS BME |
| AC Technician | KTV thiết bị |
| AC Calibration Lab Engineer | KS Cal nội bộ |
| AC Spare Warehouse Officer | Kho phụ tùng |
| AC QMS Officer | – |
| AC QMS Lead | Trưởng QLCL |
| AC Department Head | Trưởng khoa |
| AC Clinical User | BS, ĐD, KTV CLS |
| AC Procurement Officer | Mua hàng |
| AC Finance Officer | KTTC |
| AC Legal Officer | Pháp chế |
| AC Auditor | KTNB |
| AC Vendor Service Engineer | Vendor SE |
| AC Vendor Calibration | Vendor Cal |
| AC Vendor Trainer | Vendor Trainer |
| AC Executive Viewer | BGĐ |
| AC System Admin | IT |

## 3. Permission Levels (Frappe)

- Level 0: default fields.
- Level 1: confidential (vd cost_labor, contract_value).
- Level 2: highly confidential (Migration legacy raw, audit metadata).

## 4. Quy ước transition

- Mọi action → publish Lifecycle Event đúng type.
- E-signature bắt buộc cho action QMS-critical (theo Phase_04/05).
- Validator ≠ Executor (segregation of duty).
- Approval chain theo Phase_01/10.

## 5. SLA & Notification

- SLA Engine: Phase_04/03 + Phase_07/07.
- Notification: Phase_04/04.
- Alert: Phase_06/06.

## 6. Build order

Workflow build sau khi DocType + permission cài xong.
- Dùng Frappe Workflow JSON definition.
- Custom transition logic qua hooks `before_workflow_action` / `on_workflow_action`.

## 7. Tiêu chí nghiệm thu
- 22 workflow Wave 1 build đầy đủ.
- Permission matrix test pass.
- Audit log per transition.
- E-signature integration tested.
