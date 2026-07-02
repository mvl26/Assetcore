# IMM-01 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-01 — Nhu cầu (Needs Assessment & Budget Estimation)** |
| Wave | 2 |
| Trạng thái | Wave 2 — Live ✅ |
| Số file hiện có | 8 (template chuẩn) |
| Cập nhật cuối | 2026-07-02 |
| Khối kiến trúc | A. KHỐI 1 |
| Đợt triển khai | 2 |
| Owner | PTP Khối 1 · Nhóm KH-TC |

> File index của module IMM-01. Module đã có code BE (service + API) và FE (Vue + Pinia + TypeScript) đầy đủ.
> File cũ (`IMM-01_*.md`) đã archive vào `docs/architecture/archive/imm-01/` — không còn trong thư mục này.

## Map Template Chuẩn

| Template (chuẩn mới) | File mới | File cũ (reference) | Trạng thái |
|---|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | `IMM-01_Module_Overview.md` + `IMM-01_Functional_Specs.md` | ✅ Chuẩn hóa |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | (rút từ `IMM-01_Technical_Design.md`) | ✅ Chuẩn hóa |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | (archived) | ✅ Cập nhật — phản ánh code thực tế |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | (archived) | ✅ Cập nhật 2026-05-18 — 22 endpoints thực tế, response shapes đúng |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | (archived) | ✅ Cập nhật — 5 Vue files thực tế, store actions thực tế |
| 07 Testing QA (Test Plan + UAT + Security + Code quality) | [`07_Testing_QA.md`](./07_Testing_QA.md) | `IMM-01_UAT_Script.md` | ✅ Chuẩn hóa |
| 08 Deployment + QMS Mapping | [`08_Deployment.md`](./08_Deployment.md) | — | ✅ Mới |
| 09 User Guide + Release Notes + Traceability | [`09_Release.md`](./09_Release.md) | — | ✅ Mới |

## Files Template Chuẩn (hiện có trong thư mục này)

- [`02_Analysis_Design.md`](./02_Analysis_Design.md) — Module overview, BPMN, Use Cases, BRs, NFRs
- [`03_Diagrams.md`](./03_Diagrams.md) — ERD Mermaid, Class Diagram, Sequence Diagrams
- [`04_Backend_Design.md`](./04_Backend_Design.md) — DocType catalog, Service layer (đã implement), Workflow, Schedulers, DB indexes
- [`05_API_Specification.md`](./05_API_Specification.md) — 22 endpoints thực tế (incl. `get_allowed_transitions`), response shapes đúng với code
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — Routes (5 Vue files thực tế), Pinia store actions thực tế, i18n
- [`07_Testing_QA.md`](./07_Testing_QA.md) — Test pyramid, UAT scenarios, STRIDE, DocPerm matrix
- [`08_Deployment.md`](./08_Deployment.md) — Pre-deploy checklist, migration patches, QMS mapping, KPIs, Risk register
- [`09_Release.md`](./09_Release.md) — User guide tiếng Việt, FAQ, Release Notes, Traceability matrix

## Files Đã Archive

File cũ (`IMM-01_*.md`) đã được move sang `docs/architecture/archive/imm-01/` (6 files):
- `IMM-01_Module_Overview.md`, `IMM-01_Functional_Specs.md`, `IMM-01_Technical_Design.md`
- `IMM-01_API_Interface.md`, `IMM-01_UI_UX_Guide.md`, `IMM-01_UAT_Script.md`

## Key Design Decisions

| Quyết định | Giá trị |
|---|---|
| Audit trail | `IMM Audit Trail` (Wave 1 shared) — không dùng child table riêng |
| API envelope | `{"success": true, "data": {...}}` — HTTP 200 always |
| Workflow states | Title Case (`Draft`, `Pending Approval`, `Approved`) |
| Workflow actions | Tiếng Việt (`Gửi yêu cầu`, `Phê duyệt`, `Từ chối`) |
| Priority scoring | 6 tiêu chí weighted; P1≥4.0, P2 3.0-3.99, P3 2.0-2.99, P4<2.0 |
| Error handling | `raise ServiceError(ErrorCode.VALIDATION, "msg tiếng Việt")` |

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm01.py` · `assetcore/api/imm01.py`
- Codebase ground truth (FE): `frontend/src/types/imm01.ts` · `frontend/src/api/imm01.ts`
- Module tiếp theo: [IMM-02 Tech Spec](../imm-02/README.md)

---

*Module index — Wave 2 docs chuẩn hóa hoàn chỉnh 2026-05-14 (deep doc-sync pass).*
