> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# CHECKLIST HAND-OFF — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** PMO
**Mục đích:** Bảng kiểm cuối cùng trước khi BA/SA chuyển giao spec cho Dev IT.

---

## 1. Phase 00 — Project Initiation

- [x] Project Charter approved.
- [x] Stakeholder Register baseline.
- [x] Scope Statement (4 khối – 17 module) lock.
- [x] Governance Model + RACI lock.
- [x] Risk/Issue/Dependency Log baseline.
- [x] Wave Plan lock.
- [x] Glossary + Naming Convention lock.

## 2. Phase 01 — Discovery & Business Analysis

- [x] Project Context Summary.
- [x] Scope Decomposition 4 khối – 17 module.
- [x] Actor Map đầy đủ.
- [x] Process Map As-Is.
- [x] Process Map To-Be.
- [x] Event List (50+ event Wave 1).
- [x] Business Rules Catalog (80+ rule).
- [x] Exception/Edge Case Catalog.
- [x] SLA Catalog (business).
- [x] Approval Authority Matrix.
- [x] Evidence/Document Inventory.

## 3. Phase 02 — Solution Architecture

- [x] Architecture Blueprint approved.
- [x] Layered Architecture Diagram.
- [x] 6 Engine Specifications.
- [x] Build vs Configure Decision Log + ADR.
- [x] Non-Functional Requirements.
- [x] Security Architecture.
- [x] Environment Strategy.

## 4. Phase 03 — Data & Domain Design

- [x] ERD Logical.
- [x] Domain Model (aggregate, invariants).
- [x] Master Data Taxonomy.
- [x] Transactional Records List.
- [x] DocType Specification Sheet (Wave 1).
- [x] State Machine Spec.
- [x] Mapping ERPNext core ↔ AssetCore.
- [x] Data Dictionary.
- [x] Traceability Matrix.
- [x] Data Quality Rule Catalog.
- [x] Migration Template.

## 5. Phase 04 — Process & Workflow Design

- [x] Workflow Specification (22 workflow Wave 1).
- [x] Permission Matrix.
- [x] SLA & Escalation Rule Catalog (technical).
- [x] Notification Rule Catalog.
- [x] Audit Trail Specification.
- [x] Approval Routing Rules.

## 6. Phase 05 — QMS & Governance Design

- [x] QMS Artifact Matrix (4 tier).
- [x] Tier 1 QC baseline.
- [x] Tier 2 PR/SOP baseline (15 SOP).
- [x] Tier 3 WI/JD baseline.
- [x] Tier 4 BM/HS/KPI baseline.
- [x] Document Lifecycle Spec.
- [x] CAPA Workflow Spec.
- [x] NC + Compliance Case Spec.
- [x] Recall/FSCA Workflow.
- [x] Change Control Workflow.
- [x] Management Review Spec.
- [x] Risk Register Spec.
- [x] Internal Audit Plan + Checklist.

## 7. Phase 06 — UX, Screen & Dashboard Design

- [x] Actor-based Screen Inventory.
- [x] Form Layout Spec.
- [x] List View & Filter Spec.
- [x] Dashboard & Report Catalog.
- [x] KPI/KRI Metric Dictionary.
- [x] Alert Catalog.
- [x] Wireframes/Mockups.
- [x] Mobile/Tablet Use-case Spec.

## 8. Phase 07 — Integration & API Design

- [x] Integration Landscape Map.
- [x] Per-Integration Survey Result baseline.
- [x] Canonical Data Model.
- [x] FHIR Profile Outline.
- [x] API Contract OpenAPI 3.x.
- [x] Authorization Flow Spec.
- [x] Event/Webhook Spec.
- [x] Error Handling & Retry Policy.
- [x] Integration Test Harness Plan.

## 9. Phase 08 — Testing & QA Design

- [x] User Story Backlog (90+ stories).
- [x] Acceptance Criteria Catalog (200+ criteria).
- [x] Test Case Library (250+ TC).
- [x] Golden Scenarios E2E (8 GS).
- [x] UAT Skeleton.
- [x] Performance Test Plan.
- [x] Security Test Plan.
- [x] Data Migration Test Plan.

## 10. Phase 09 — Implementation Planning

- [x] Sprint Backlog Wave 1 (7 sprint).
- [x] Build Sequence & Dependency Graph.
- [x] Environment Setup Runbook.
- [x] DevOps Plan.
- [x] Data Migration Runbook.
- [x] Cutover & Rollback Plan.
- [x] Training Plan.
- [x] Hypercare Plan.
- [x] Deployment Runbook.

## 11. Phase 10 — Developer Hand-off Package

- [x] Developer Brief.
- [x] Final Consolidated Spec Pack:
  - [x] DocType Spec Index.
  - [x] Workflow & Permission Index.
  - [x] Field/Validation/Naming Index.
  - [x] Hooks & Server Script Spec.
  - [x] Report & Dashboard Index.
  - [x] API Contract Index.
  - [x] Notification & SLA Rule Index.
- [x] Configuration Workbook.
- [x] Sample Dataset & Seed Data.
- [x] Test Data Set.
- [x] Reference Architecture Documentation.
- [x] Definition of Done.
- [x] Checklist Hand-off (this file).

---

## 12. Tổng kết artifact đã đóng gói

- 11 phase × ~ 8-13 deliverable mỗi phase.
- ~ 107 thư mục, mỗi thư mục có ít nhất 1 tài liệu nội dung đầy đủ.
- Hơn 30.000 dòng đặc tả có cấu trúc.

## 13. Dev IT cần gì để bắt đầu

| Cần | Ở đâu |
|-----|-------|
| Hiểu nghiệp vụ + scope | Phase 00 + 01 |
| Hiểu kiến trúc + engine | Phase 02 |
| Build DocType + state | Phase 03 + 04 |
| Build QMS engine | Phase 05 |
| Build UI + dashboard + KPI | Phase 06 |
| Build API + webhook | Phase 07 |
| Test + acceptance criteria | Phase 08 |
| Plan sprint + deploy | Phase 09 |
| Brief + DoD + sample data | Phase 10 |

## 14. Sign-off Hand-off

| Vai trò | Họ tên | Ngày | Chữ ký |
|---------|--------|------|--------|
| BA Lead |  |  |  |
| SA Lead |  |  |  |
| QMS Lead |  |  |  |
| Tech Lead (Dev IT) |  |  |  |
| QA Lead |  |  |  |
| PMO |  |  |  |
| Sponsor (BGĐ) |  |  |  |

---

## 15. Lời chốt

Bộ tài liệu này đã đóng gói toàn bộ "operating architecture" của AssetCore từ tinh thần dự án đến chi tiết implementation. Dev IT cầm bộ này có thể build Wave 1 mà không phải ngồi hỏi lại BA về kiến trúc, DocType, workflow, permission, API hay UX.

**AssetCore Wave 1 — Hand-off Ready ✅**
