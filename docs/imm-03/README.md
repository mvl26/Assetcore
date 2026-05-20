# IMM-03 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-03 — Đánh giá Nhà cung cấp & Quyết định Mua sắm (Procurement)** |
| Wave | 2 — Live ✅ |
| Trạng thái | ✅ Đã triển khai — BE + FE LIVE |
| Số file | 8 template chuẩn (nguồn gốc đã archive) |
| Cập nhật cuối | 2026-05-18 |
| Khối kiến trúc | A. KHỐI 1 — Planning & Procurement |
| Đợt triển khai | 2 |
| Owner | PTP Khối 1 · Nhóm ĐT-HĐ-NCC |

> ✅ Module LIVE — Wave 2. Backend (`assetcore/services/imm03.py` 559 LOC, `assetcore/api/imm03.py` 730 LOC) và Frontend (`frontend/src/views/procurement/{VendorProfile,VendorEval,Avl,Decision}*View.vue` + `stores/imm03.ts`, `api/imm03.ts`, `types/imm03.ts`) đã implement. Source docs cũ đã archive vào `docs/architecture/archive/imm-03/`.

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | ✅ Đã tạo |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | ✅ Đã tạo |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | ✅ Đã tạo |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | ✅ Đã tạo |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | ✅ Đã tạo |
| 07 Testing_QA | [`07_Testing_QA.md`](./07_Testing_QA.md) | ✅ Đã tạo |
| 08 Deployment | [`08_Deployment.md`](./08_Deployment.md) | ✅ Đã tạo |
| 09 Release | [`09_Release.md`](./09_Release.md) | ✅ Đã tạo |

## Source docs cũ (đã archive)

Files nguồn gốc đã được move sang `docs/architecture/archive/imm-03/`:

- `IMM-03_API_Interface.md` — API gốc (18 endpoints)
- `IMM-03_Functional_Specs.md` — FR/NFR/User Stories
- `IMM-03_Module_Overview.md` — Architecture/DocTypes/BRs
- `IMM-03_Technical_Design.md` — Schemas/Algorithms/Hooks
- `IMM-03_UAT_Script.md` — 36 test cases
- `IMM-03_UI_UX_Guide.md` — 11 routes/wireframes

## Roadmap chuẩn hóa

- [x] Tạo `02_Analysis_Design.md`
- [x] Tạo `03_Diagrams.md`
- [x] Tạo `04_Backend_Design.md`
- [x] Tạo `05_API_Specification.md` (với AssetCore envelope `{success, data}`)
- [x] Tạo `06_Frontend_Design.md`
- [x] Tạo `07_Testing_QA.md`
- [x] Tạo `08_Deployment.md`
- [x] Tạo `09_Release.md`

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm03.py` · `assetcore/api/imm03.py`
- Codebase ground truth (FE): `frontend/src/types/imm03.ts` · `frontend/src/api/imm03.ts`

---

*Module IMM-03 — Wave 2 LIVE. Cập nhật 2026-05-18.*
