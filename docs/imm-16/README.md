# IMM-16 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-16 — Giám sát Tuân thủ & CAPA** |
| Wave | 2 — IMPLEMENTED (feature/hieuc/wave-2) |
| Trạng thái | ✅ Stable — BE + FE đã merge; chờ UAT |
| Số file | 9 (README + 02-09; nguồn gốc đã archive) |
| Cập nhật cuối | 2026-07-15 (CR-27b — curate `getInternalAudit` mobile OAS detail-sibling, [ADR-MOBILE-052](../mobile/ADR-MOBILE-052.md); PREV CR-27a `listInternalAudits`, ADR-MOBILE-051) |
| Khối kiến trúc | C. KHỐI 3 |
| Đợt triển khai | 2 |
| Owner | Tổ HC-QLCL & Risk |

> ✅ Module đã triển khai trên branch `feature/hieuc/wave-2` — `assetcore/services/imm16.py` (~2076 dòng), `assetcore/api/imm16.py` (~423 dòng / 52 whitelist functions), 11 DocType (`imm_compliance_rule`, `imm_compliance_finding`, `imm_internal_audit`, `imm_compliance_scorecard`, `imm_management_review`, `imm_capa_record`, `imm_capa_action_step`, `imm_audit_checklist_item`, …) + 10 view tại `frontend/src/views/compliance/`. Banners PLANNED trong file 02–09 đã được gỡ (Wave-2 Sync Pass 2026-05-14).

---

## Map Template Chuẩn (v4.1+)

| Template | File chuẩn hóa | Trạng thái |
|---|---|:---:|
| 02 Analysis & Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | ✅ |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | ✅ |
| 04 Backend Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | ✅ |
| 05 API Specification | [`05_API_Specification.md`](./05_API_Specification.md) | ✅ |
| 06 Frontend Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | ✅ |
| 07 Testing & QA | [`07_Testing_QA.md`](./07_Testing_QA.md) | ✅ |
| 08 Deployment & QMS | [`08_Deployment.md`](./08_Deployment.md) | ✅ |
| 09 Release Notes & User Guide | [`09_Release.md`](./09_Release.md) | ✅ |

---

## Source Docs (Archived)

> Source docs (cũ) đã archive tại [`docs/architecture/archive/imm-16/`](../../architecture/archive/imm-16/).  
> Không tham chiếu trực tiếp — dùng các file template chuẩn `02_`…`09_` ở trên.

| File (archive) | Nội dung |
|---|---|
| `IMM-16_Module_Overview.md` | Tổng quan module, DocTypes, roles, BRs, dependencies |
| `IMM-16_Functional_Specs.md` | Scope, actors, 10 user stories (Gherkin), 10 BRs, 12 VRs, NFRs |
| `IMM-16_Technical_Design.md` | DocType schemas, service layer, hooks, schedulers, workflow JSON, fixtures, ERD |
| `IMM-16_API_Interface.md` | ~30 endpoints (BA draft — envelope cũ; dùng `05_API_Specification.md` cho envelope chuẩn) |
| `IMM-16_UI_UX_Guide.md` | 15 screens/routes, wireframes, permission-driven UI, UX patterns |
| `IMM-16_UAT_Script.md` | 18 test cases TC-01..TC-18 (nguồn cho UAT-IMM16-01..12 trong 07_Testing_QA) |

---

## Tổng quan Module

**IMM-16** là module Giám sát Tuân thủ & CAPA — trục QMS trung tâm của AssetCore. Module:

- **Tự động phát hiện** vi phạm tuân thủ qua Rule Engine (monthly/daily scheduler)
- **Quản lý Finding lifecycle**: Open → Under Review → Confirmed NC / False Positive / Waived
- **CAPA full lifecycle** (6 states) với kiểm tra hiệu quả bắt buộc
- **Cross-module gate** (BR-16-09): block IMM-08/09 WO Submit khi asset có CAPA Critical chưa đóng
- **Internal Audit** cycle với auto-create Finding từ checklist
- **Compliance Scorecard** hàng tháng tự động + immutable sau publish
- **Management Review** quý với gate: không có MR Closed → không publish Scorecard

### DocType Summary

| DocType | Status | Naming |
|---|:---:|---|
| IMM CAPA Record | LIVE (shared với **IMM-12**) | CAPA-.YYYY.-.##### |
| IMM CAPA Action Step | LIVE (shared với **IMM-12**) | child |
| Audit Finding | LIVE (reuse) | — |
| IMM Audit Trail | LIVE | IMM-AUD-.YYYY.-.####### |
| IMM RCA Record | LIVE (reuse) | IMM-RCA-.YYYY.-.##### |
| IMM Compliance Rule | LIVE | rule_code (autoname) |
| IMM Compliance Finding | LIVE | FND-.YYYY.-.##### |
| IMM Internal Audit | LIVE | AUD-INT-.YYYY.-.##### |
| IMM Audit Checklist Item | LIVE | child |
| IMM Compliance Scorecard | LIVE | SCR-.YYYY.-.MM.-.##### |
| IMM Management Review | LIVE | MR-.YYYY.-.##### |

### Roles (30-role catalog — `assetcore/fixtures/role.json`)

| Role hệ thống | Persona thực địa | Quyền chính |
|---|---|---|
| Compliance Manager | Tổ HC-QLCL / VP Block2 / QA Lead | Quản lý Rule, Finding triage, CAPA oversight, Scorecard publish, Waive, Close Audit, Finalize MR |
| Compliance User | Internal Auditor / khoa phòng | Internal Audit, Finding review, tạo CAPA cấp khoa |
| Corrective Manager (IMM-09) | Workshop Head | CAPA action owner cấp xưởng |
| Corrective User / PM User | Biomed Engineer / KTV PM | Thực hiện action step; biết gate block (BR-16-09) |
| AssetCore Auditor | Auditor QMS | Read-only audit trail + immutability |
| AssetCore Super Admin | CMMS Admin | Full access, override |
| AssetCore System User | All authenticated | Read Dashboard / Heatmap |

> Persona cũ (Tổ HC-QLCL, VP Block2, Workshop Head, Internal Auditor, CMMS Admin) đã được ánh xạ vào 30-role catalog post-patch `v3_2.001_module_role_redesign`.

---

## Roadmap

- [x] Bổ sung **`02_Analysis_Design.md`** — Module overview, BPMN, use cases, BRs/VRs, NFR
- [x] Bổ sung **`03_Diagrams.md`** — ERD, Class, Sequence (3 flows), Communication, Package
- [x] Bổ sung **`04_Backend_Design.md`** — DocType schemas, service layer, workflows, schedulers, DB indexes
- [x] Bổ sung **`05_API_Specification.md`** — AssetCore envelope chuẩn; 30 endpoints; error catalog; TypeScript types
- [x] Bổ sung **`06_Frontend_Design.md`** — Sitemap, components + wireframes, Pinia store, i18n
- [x] Bổ sung **`07_Testing_QA.md`** — Test pyramid, unit stubs, workflow transitions, UAT-IMM16-01..12, STRIDE, DocPerm, code quality
- [x] Bổ sung **`08_Deployment.md`** — Pre-deploy checklist, patches, deploy sequence, smoke test, rollback, QMS mapping
- [x] Bổ sung **`09_Release.md`** — User guide tiếng Việt, FAQ, Release Notes v0.0.2 (đồng bộ app), Traceability matrix

---

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Pattern reference (BE): `docs/imm-09/04_Backend_Design.md`
- Pattern reference (API): `docs/imm-09/05_API_Specification.md`
- Pattern reference (Test): `docs/imm-09/07_Testing_QA.md`
- Codebase LIVE (BE): `assetcore/services/imm00.py` · `assetcore/doctype/imm_capa_record/`
- Codebase LIVE (BE): `assetcore/services/imm16.py` · `assetcore/api/imm16.py`
- Codebase LIVE (FE): `frontend/src/views/compliance/` · `frontend/src/api/imm16.ts` · `frontend/src/stores/imm16.ts`

---

*Cập nhật: 2026-05-27. Module IMM-16 — Wave 2 LIVE. Audit pass 2026-05-27: version → `0.0.2`, persona roles → 30-role catalog, cross-module note: `IMM CAPA Record` + `IMM CAPA Action Step` shared với IMM-12.*
