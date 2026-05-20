# IMM-05 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-05 — Hồ sơ thiết bị (Asset Documents)** |
| Wave | 1 |
| Trạng thái | Mature |
| Số file hiện có | 8 |
| Cập nhật cuối | 2026-05-18 |
| Khối kiến trúc | B. KHỐI 2 |
| Đợt triển khai | 1 |
| Owner | PTP Khối 2 · Tổ HC-QLCL |

> File index của module IMM-05. Map cũ ↔ template chuẩn theo `docs/template/` (v4.1+).
> **Strategy: light-touch** — file 6-doc cũ giữ nguyên làm reference; bổ sung file mới theo template khi cần (xem `docs/template/MIGRATION_GUIDE.md`).

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File hiện có | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) + `IMM-05_Module_Overview.md` + `IMM-05_Functional_Specs.md` | ✅ Có (file mới chuẩn template) |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) + `IMM-05_Technical_Design.md` § Diagrams | ✅ Có (file mới chuẩn template) |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) + `IMM-05_Technical_Design.md` | ✅ Có (file mới chuẩn template) |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) + `IMM-05_API_Interface.md` | ✅ Có (envelope chuẩn `{success, data}`) |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) + `IMM-05_UI_UX_Guide.md` | ✅ Có (file mới chuẩn template) |
| 07 §I Test Plan + §III Security + §IV Code quality | `07_Testing_QA.md` | ✅ Có |
| 07 §II UAT Script | `IMM-05_UAT_Script.md` | ✅ Có |
| 08 Deployment + QMS Mapping | `08_Deployment.md` | ✅ Có |
| 09 User Guide + Release Notes + Traceability | `09_Release.md` | ✅ Có |

## Files hiện có

### Files chuẩn template mới (v4.1+)
- [`02_Analysis_Design.md`](./02_Analysis_Design.md) — Phân tích nghiệp vụ + Use Case + Functional Specs + NFR
- [`03_Diagrams.md`](./03_Diagrams.md) — ERD + Class Diagram + Sequence Diagram + Package Diagram
- [`04_Backend_Design.md`](./04_Backend_Design.md) — DocType + Workflow + Service + API + Scheduler
- [`05_API_Specification.md`](./05_API_Specification.md) — API Catalog + 16 endpoints + Envelope chuẩn
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — Sitemap + Mockup + Components + Pinia + UX rules

### Files tham chiếu (giữ trong module)
- [`07_Testing_QA.md`](./07_Testing_QA.md) — Test plan + UAT script + Security review
- [`08_Deployment.md`](./08_Deployment.md) — Deployment plan + QMS compliance mapping
- [`09_Release.md`](./09_Release.md) — User guide (VI) + Release notes + Traceability matrix

### Source docs (cũ) đã archive
Source docs (cũ) đã archive tại `docs/architecture/archive/imm-05/`:
- `IMM-05_API_Interface.md`
- `IMM-05_Functional_Specs.md`
- `IMM-05_Module_Overview.md`
- `IMM-05_Technical_Design.md`
- `IMM-05_UAT_Script.md`
- `IMM-05_UI_UX_Guide.md`

## Roadmap chuẩn hóa

- [x] Tạo **`02_Analysis_Design.md`** — theo template chuẩn v4.1+
- [x] Tạo **`03_Diagrams.md`** — ERD, Class, Sequence, Communication, Package diagrams
- [x] Tạo **`04_Backend_Design.md`** — Backend design chuẩn 3-tier
- [x] Tạo **`05_API_Specification.md`** — API Catalog với envelope `{success, data}` chuẩn AssetCore
- [x] Tạo **`06_Frontend_Design.md`** — Frontend design chuẩn Vue 3 + Pinia
- [x] Bổ sung **`07_Testing_QA.md`** — Test plan (unit/integration/coverage) + Security review + Code quality
- [x] Bổ sung **`08_Deployment.md`** — Deployment plan + QMS Mapping (NĐ98/WHO HTM) + Cấu hình môi trường thực nghiệm
- [x] Bổ sung **`09_Release.md`** — User guide tiếng Việt + Release notes + Traceability matrix
- [ ] Refactor `services/imm05.py` — tách `archive_old_versions`, `update_asset_completeness`, `_compute_document_status` ra service layer (Sprint 7)
- [ ] Thêm DB UNIQUE constraint cho `(asset_ref, doc_type_detail, doc_number)` (Sprint 7)
- [ ] Realtime push qua Socket.IO cho dashboard live update (Sprint 8)

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm05.py` (587 LOC) · `assetcore/api/imm05.py` (156 LOC, **16** `@frappe.whitelist()` endpoints)
- Codebase ground truth (FE): `frontend/src/types/imm05.ts` · `frontend/src/api/imm05.ts`

---

*Module index — auto-generated khi migration. Khi update file thực tế, manual sync README này.*
