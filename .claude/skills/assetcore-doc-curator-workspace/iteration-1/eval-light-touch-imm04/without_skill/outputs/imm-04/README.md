# IMM-04 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu (Installation / Commissioning)** |
| Wave | 1 |
| Trạng thái | Mature — có v2 UAT |
| Số file hiện có | 9 (README + 02–09) |
| Cập nhật cuối | 2026-05-10 |

> File index của module IMM-04. Map cũ ↔ template chuẩn theo `docs/template/` (v4.1+).
> **Strategy: light-touch** — file 6-doc cũ giữ nguyên làm reference; bổ sung file mới theo template khi cần (xem `docs/template/MIGRATION_GUIDE.md`).

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File hiện có | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) + `IMM-04_Module_Overview.md` + `IMM-04_Functional_Specs.md` | ✅ Có (file mới chuẩn template) |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) + `IMM-04_Technical_Design.md` § Diagrams | ✅ Có (file mới chuẩn template) |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) + `IMM-04_Technical_Design.md` | ✅ Có (file mới chuẩn template) |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) + `IMM-04_API_Interface.md` | ✅ Có (envelope chuẩn `{success, data}`) |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) + `IMM-04_UI_UX_Guide.md` | ✅ Có (file mới chuẩn template) |
| 07 §I Test Plan + §III Security + §IV Code quality | `07_Testing_QA.md` | ✅ Có |
| 07 §II UAT Script | `IMM-04_UAT_Script.md` + `IMM-04_UAT_Script_v2.md` | ✅ Có (v1 + v2) |
| 08 Deployment + QMS Mapping | `08_Deployment.md` | ✅ Có |
| 09 User Guide + Release Notes + Traceability | `09_Release.md` | ✅ Có |

## Files hiện có

### Files chuẩn template mới (v4.1+)
- [`02_Analysis_Design.md`](./02_Analysis_Design.md) — Phân tích nghiệp vụ + Use Case + Functional Specs + NFR
- [`03_Diagrams.md`](./03_Diagrams.md) — ERD + Class Diagram + Sequence Diagram + Package Diagram
- [`04_Backend_Design.md`](./04_Backend_Design.md) — DocType + Workflow + Service + API + Scheduler
- [`05_API_Specification.md`](./05_API_Specification.md) — API Catalog + 20 endpoints + Envelope chuẩn
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — Sitemap + Mockup + Components + Pinia + UX rules

### Files tham chiếu (giữ trong module)
- [`07_Testing_QA.md`](./07_Testing_QA.md) — Test plan + UAT script + Security review
- [`08_Deployment.md`](./08_Deployment.md) — Deployment plan + QMS compliance mapping
- [`09_Release.md`](./09_Release.md) — User guide (VI) + Release notes + Traceability matrix

### Source docs (cũ) đã archive
Source docs (cũ) đã archive tại `docs/architecture/archive/imm-04/`:
- `IMM-04_API_Interface.md`
- `IMM-04_Functional_Specs.md`
- `IMM-04_Module_Overview.md`
- `IMM-04_Technical_Design.md`
- `IMM-04_UAT_Script.md`
- `IMM-04_UAT_Script_v2.md`
- `IMM-04_UI_UX_Guide.md`

## Roadmap chuẩn hóa

- [x] Bổ sung **`07_Testing_QA.md`** — Test plan (unit/integration/coverage) + Security review + Code quality
- [x] Bổ sung **`08_Deployment.md`** — Deployment plan + QMS Mapping (NĐ98/WHO HTM)
- [x] Bổ sung **`09_Release.md`** — User guide tiếng Việt + Release notes + Traceability matrix
- [x] Tạo **`02_Analysis_Design.md`** — theo template chuẩn v4.1+
- [x] Tạo **`03_Diagrams.md`** — ERD, Class, Sequence, Communication, Package diagrams
- [x] Tạo **`04_Backend_Design.md`** — Backend design chuẩn 3-tier
- [x] Tạo **`05_API_Specification.md`** — API Catalog với envelope `{success, data}` chuẩn AssetCore
- [x] Tạo **`06_Frontend_Design.md`** — Frontend design chuẩn Vue 3 + Pinia
- [ ] Chuẩn hóa naming `Clinical Release` vs `Clinical_Release` trong code (Sprint 7)
- [ ] Thêm DB UNIQUE constraint cho `vendor_serial_no` (Sprint 7)
- [ ] Config Print Format Biên bản Bàn giao (Sprint 7)
- [ ] IMM-08 listener cho `imm04_asset_released` (Sprint 8)

## Tham chiếu

**Template & migration:**
- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)

**Source documents (read-only):**
- Kiến trúc tổng IMMIS: [`../architecture/Ho_so_kien_truc_IMMIS.md`](../architecture/Ho_so_kien_truc_IMMIS.md)
- WHO HTM lifecycle (Inventory & Maintenance 2025): [`../WHO/WHO - Inventory and maintenance 2025.md`](../WHO/)
- WHO Maintenance programme overview: [`../WHO/WHO - Medical equipment maintenance programme overview.md`](../WHO/)
- WHO Inventory management: [`../WHO/WHO - Introduction to medical equipment inventory management.md`](../WHO/)
- GMDN / phân loại rủi ro TBYT (QĐ 3107/QĐ-BYT, 69, 847): [`../gmdn/`](../gmdn/)

**Codebase ground truth:**
- BE: `assetcore/services/imm04.py` · `assetcore/api/imm04.py` · `assetcore/repositories/`
- FE: `frontend/src/types/imm04.ts` · `frontend/src/api/imm04.ts` · `frontend/src/views/imm-04/`
- DocType: `assetcore/assetcore/doctype/asset_commissioning/`
- Workflow: `assetcore/assetcore/workflow/imm_04_*.json`

---

*Module index — auto-generated khi migration. Khi update file thực tế, manual sync README này.*
