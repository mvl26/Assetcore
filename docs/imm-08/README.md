# IMM-08 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-08 — Bảo trì định kỳ (PM)** |
| Wave | 1 |
| Trạng thái | Mature |
| Số file hiện có | 14 |
| Cập nhật cuối | 2026-06-03 |
| Khối kiến trúc | C. KHỐI 3 |
| Đợt triển khai | 1 |
| Owner | PTP Khối 2 · Workshop / Nhóm TBYT |

> File index của module IMM-08. Map cũ ↔ template chuẩn theo `docs/template/` (v4.1+).
> **Source docs đã archive tại `docs/architecture/archive/imm-08/`** — 6 file format cũ (IMM-08_*.md) đã được chuyển vào archive sau khi template chuẩn 02–09 được bổ sung đầy đủ.

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File hiện có | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | ✅ Template chuẩn |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | ✅ Template chuẩn |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | ✅ Template chuẩn |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | ✅ Template chuẩn (envelope `{success,data}`, 23 endpoints) |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | ✅ Template chuẩn (8 routes, store actions đồng bộ code) |
| 07 §I Test Plan + §III Security + §IV Code quality | [`07_Testing_QA.md`](./07_Testing_QA.md) | ✅ Có |
| 07 §II UAT Script | Archive: `docs/architecture/archive/imm-08/IMM-08_UAT_Script.md` | ✅ Archived |
| 08 Deployment + QMS Mapping | [`08_Deployment.md`](./08_Deployment.md) | ✅ Có |
| 09 User Guide + Release Notes + Traceability | [`09_Release.md`](./09_Release.md) | ✅ Có |

## Files hiện có

**Template chuẩn mới (02–06):**
- [`02_Analysis_Design.md`](./02_Analysis_Design.md) — Phân tích nghiệp vụ + Use Cases + BR + NFR
- [`03_Diagrams.md`](./03_Diagrams.md) — ERD + Class + Sequence + Communication + Package
- [`04_Backend_Design.md`](./04_Backend_Design.md) — DocType + Workflow + Service + API + Scheduler
- [`05_API_Specification.md`](./05_API_Specification.md) — Catalog 23 endpoints + envelope chuẩn `{success,data}`
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — Sitemap 8 routes + Components + Store (đồng bộ code) + i18n

**Template chuẩn mới (07–09):**
- [`07_Testing_QA.md`](./07_Testing_QA.md)
- [`08_Deployment.md`](./08_Deployment.md)
- [`09_Release.md`](./09_Release.md)

**Format cũ (đã archive — xem `docs/architecture/archive/imm-08/`):**
- `IMM-08_API_Interface.md`
- `IMM-08_Functional_Specs.md`
- `IMM-08_Module_Overview.md`
- `IMM-08_Technical_Design.md`
- `IMM-08_UAT_Script.md`
- `IMM-08_UI_UX_Guide.md`

## Roadmap chuẩn hóa

- [x] Bổ sung **`02_Analysis_Design.md`** — Phân tích nghiệp vụ + Use Cases + BR + NFR (template chuẩn)
- [x] Bổ sung **`03_Diagrams.md`** — ERD + Class + Sequence + Communication + Package (template chuẩn)
- [x] Bổ sung **`04_Backend_Design.md`** — DocType + Workflow + Service + Scheduler + Migration (template chuẩn)
- [x] Bổ sung **`05_API_Specification.md`** — API Catalog 23 endpoints + envelope `{success,data}` chuẩn AssetCore
- [x] Bổ sung **`06_Frontend_Design.md`** — Sitemap 8 routes + Mockup + Components + Store (đồng bộ code) + i18n (template chuẩn)
- [x] Bổ sung **`07_Testing_QA.md`** — Test plan (unit/integration/coverage) + Security review + Code quality
- [x] Bổ sung **`08_Deployment.md`** — Deployment plan + QMS Mapping (NĐ98/WHO HTM) + Cấu hình môi trường
- [x] Bổ sung **`09_Release.md`** — User guide tiếng Việt + Release notes + Traceability matrix

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm08.py` · `assetcore/api/imm08.py`
- Codebase ground truth (FE): `frontend/src/types/imm08.ts` · `frontend/src/api/imm08.ts`

---

*Module index — auto-generated khi migration. Khi update file thực tế, manual sync README này.*
