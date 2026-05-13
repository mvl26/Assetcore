# IMM-16 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-16 — Giám sát Tuân thủ & CAPA** |
| Wave | 3 — Docs chuẩn hóa ✅ |
| Trạng thái | Wave 3 — PLANNED (chờ implement) |
| Số file | 8 (template chuẩn; nguồn gốc đã archive) |
| Cập nhật cuối | 2026-05-10 |
| Khối kiến trúc | C. KHỐI 3 |
| Đợt triển khai | 2 |
| Owner | Tổ HC-QLCL & Risk |

> ⚠️ **Module này chưa được implement** — Wave 3. Toàn bộ tài liệu dưới đây là planning & design artifacts.

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
| IMM CAPA Record | LIVE (extended) | CAPA-.YYYY.-.##### |
| Audit Finding | LIVE (reuse) | — |
| IMM Audit Trail | LIVE (reuse) | — |
| IMM RCA Record | LIVE (reuse) | — |
| IMM Compliance Rule | PLANNED | rule_code (autoname) |
| IMM Compliance Finding | PLANNED | FND-.YYYY.-.##### |
| IMM Internal Audit | PLANNED | AUD-INT-.YYYY.-.##### |
| IMM Compliance Scorecard | PLANNED | SCR-.YYYY.-.MM.-.##### |
| IMM Management Review | PLANNED | MR-.YYYY.-.##### |

### Roles

| Role | Quyền chính |
|---|---|
| Tổ HC-QLCL | Quản lý Rule, xem xét Finding, CAPA oversight, Scorecard publish |
| Internal Auditor | Internal Audit, Finding review |
| Workshop Head | CAPA action owner |
| Biomed Engineer | Xem CAPA; biết gate block |
| VP Block2 | Waive Finding, Close Audit, Finalize MR, Dashboard |
| Trưởng phòng | Tạo CAPA cho khoa |
| CMMS Admin | Full access |

---

## Roadmap

- [x] Bổ sung **`02_Analysis_Design.md`** — Module overview, BPMN, use cases, BRs/VRs, NFR
- [x] Bổ sung **`03_Diagrams.md`** — ERD, Class, Sequence (3 flows), Communication, Package
- [x] Bổ sung **`04_Backend_Design.md`** — DocType schemas, service layer, workflows, schedulers, DB indexes
- [x] Bổ sung **`05_API_Specification.md`** — AssetCore envelope chuẩn; 30 endpoints; error catalog; TypeScript types
- [x] Bổ sung **`06_Frontend_Design.md`** — Sitemap, components + wireframes, Pinia store, i18n
- [x] Bổ sung **`07_Testing_QA.md`** — Test pyramid, unit stubs, workflow transitions, UAT-IMM16-01..12, STRIDE, DocPerm, code quality
- [x] Bổ sung **`08_Deployment.md`** — Pre-deploy checklist, patches, deploy sequence, smoke test, rollback, QMS mapping
- [x] Bổ sung **`09_Release.md`** — User guide tiếng Việt, FAQ, Release Notes v1.0.0, Traceability matrix

---

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Pattern reference (BE): `docs/imm-09/04_Backend_Design.md`
- Pattern reference (API): `docs/imm-09/05_API_Specification.md`
- Pattern reference (Test): `docs/imm-09/07_Testing_QA.md`
- Codebase LIVE (BE): `assetcore/services/imm00.py` · `assetcore/doctype/imm_capa_record/`
- Codebase PLANNED (BE): `assetcore/services/imm16_*.py` · `assetcore/api/imm16.py`
- Codebase PLANNED (FE): `frontend/src/types/imm16.ts` · `frontend/src/stores/imm16.ts`

---

*Cập nhật: 2026-05-10. Docs chuẩn hóa Wave 3 hoàn tất (8/8 files); bổ sung light-touch I.0/I.7/I.8/III.0 UC Diagram trong 02.*
