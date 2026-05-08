> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DEVELOPER BRIEF — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Mục đích:** Tài liệu điều hướng "1 trang" cho Dev IT — chỉ rõ đọc gì, ở đâu, theo thứ tự nào.

---

## 1. Bối cảnh ngắn
AssetCore là custom Frappe app trên ERPNext v15, quản lý vòng đời thiết bị y tế theo khung HTM/IMMIS với QMS xuyên suốt. Wave 1 ưu tiên 6 module IMM-04, 05, 08, 09, 11, 12 + 6 engine cốt lõi.

## 2. Đọc theo thứ tự (mandatory)

1. **Phase 00 / 01_Project_Charter** — hiểu mục tiêu.
2. **Phase 00 / 03_Scope_Statement** — biết in/out scope.
3. **Phase 00 / 06_Wave_Plan** — biết Wave 1 phải build gì.
4. **Phase 00 / 07_Glossary_Naming_Convention** — quy ước đặt tên.
5. **Phase 02 / 01_Architecture_Blueprint** — hiểu kiến trúc tổng.
6. **Phase 02 / 02_Layered_Architecture_Diagram** — hiểu phân tầng.
7. **Phase 02 / 03_Engine_Specifications** — đọc cả 6 engine.
8. **Phase 02 / 04_Build_vs_Configure_Decision_Log** — quy ước build/config.
9. **Phase 03 / 01_ERD_Logical** — quan hệ dữ liệu.
10. **Phase 03 / 05_DocType_Specification_Sheet** — DocType Wave 1.
11. **Phase 03 / 06_State_Machine_Spec** — workflow state.
12. **Phase 03 / 07_Mapping_ERPNext_AssetCore** — tận dụng core.
13. **Phase 04 / 01_Workflow_Specification** — workflow chi tiết.
14. **Phase 04 / 02_Permission_Matrix** — RBAC.
15. **Phase 04 / 03_SLA_Escalation_Rule_Catalog** — SLA cài đặt.
16. **Phase 04 / 05_Audit_Trail_Specification** — audit chuẩn.
17. **Phase 06 / 02_Form_Layout_Spec** — UI form.
18. **Phase 06 / 05_KPI_KRI_Metric_Dictionary** — KPI 25 metrics.
19. **Phase 07 / 05_API_Contract_OpenAPI** — API.
20. **Phase 07 / 07_Event_Webhook_Spec** — outbox + webhook.
21. **Phase 08 / 02_Acceptance_Criteria_Catalog** — acceptance criteria.
22. **Phase 09 / 01_Sprint_Backlog_Wave1** — kế hoạch sprint.
23. **Phase 09 / 04_DevOps_Plan** — pipeline.
24. **Phase 10 / 02_Final_Consolidated_Spec_Pack** — bộ spec đóng gói.

## 3. Đọc khi cần (reference)

- Phase 01 — bối cảnh nghiệp vụ.
- Phase 03 / 11_Migration_Template — migration.
- Phase 05 — QMS engine + tài liệu Tier.
- Phase 06 — wireframes mockups.
- Phase 07 — FHIR + AuthZ.
- Phase 08 — UAT + test plan.
- Phase 09 — runbook deployment.

## 4. Không được làm (hard rules)

- ❌ Sửa core ERPNext schema trực tiếp.
- ❌ Đặt tên DocType custom không có prefix `AC `.
- ❌ Bỏ qua workflow Frappe — set state qua server script bypass.
- ❌ Tạo Lifecycle Event bằng tay; phải dùng `assetcore.lifecycle.publish()`.
- ❌ Update / Delete Lifecycle Event sau insert.
- ❌ Hardcode secret trong code.
- ❌ Fetch data ngoài tầng repository ở engine cao.
- ❌ Bỏ qua e-signature ở QMS-critical action.

## 5. Phải làm (must)

- ✅ Tuân thủ Naming Convention (Phase 00 / 07).
- ✅ ADR cho mọi quyết định kiến trúc không tầm thường.
- ✅ Unit test ≥ 70% coverage Wave 1.
- ✅ DoD per story (Phase 10 / 07).
- ✅ Code review checklist + security checklist.
- ✅ Document new APIs + hooks.

## 6. Liên hệ

| Vai trò | Người (template) |
|---------|--------|
| SA Lead | … |
| BA Lead | … |
| Tech Lead | … |
| QA Lead | … |
| QMS Lead | … |
| DevOps Lead | … |
| Frappe Partner Tech Lead | … |

## 7. Repo & branch
- Repo: `git@<host>:<org>/assetcore.git`
- Branching theo Phase 09 / 04_DevOps_Plan §1.

## 8. Tooling cần cài
- Python 3.11+, Node 18+.
- Bench Frappe.
- Postman + Schemathesis cho API.
- k6 cho perf.
- Cypress / Playwright cho E2E.

## 9. Checklist trước khi mở PR đầu tiên

- [ ] Đã đọc 24 doc trên.
- [ ] Cài bench DEV chạy được local.
- [ ] Đã hiểu DocType cần build trong story đầu tiên.
- [ ] Đã review acceptance criteria.

## 10. Sự cố — nơi escalate
- Bug Critical PROD: Tech Lead + IT Lead.
- Decision kiến trúc: ARB.
- Decision nghiệp vụ: BA Lead + Owner business.
- Security: ATTT + Tech Lead.
- QMS-related: QMS Lead.
