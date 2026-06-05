# IMM-04 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-04 — Lắp đặt, định danh và kiểm tra ban đầu** |
| Wave | 1 |
| Trạng thái | Mature — có v2 UAT |
| Số file hiện có | 8 |
| Cập nhật cuối | 2026-06-04 |
| Khối kiến trúc | B. KHỐI 2 |
| Đợt triển khai | 1 |
| Owner | PTP Khối 2 · Workshop / Nhóm TBYT · Mạng lưới TBYT nội viện |

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
- [`05_API_Specification.md`](./05_API_Specification.md) — API Catalog + 34 endpoints + Envelope chuẩn
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — Sitemap + Mockup + Components + Pinia + UX rules

### Files tham chiếu (giữ trong module)
- [`07_Testing_QA.md`](./07_Testing_QA.md) — Test plan + UAT script + Security review
- [`08_Deployment.md`](./08_Deployment.md) — Deployment plan + QMS compliance mapping
- [`09_Release.md`](./09_Release.md) — User guide (VI) + Release notes + Traceability matrix

### Architecture Decision Records (ADR)
- [`ADR-001-asset-qr.md`](./ADR-001-asset-qr.md) — **QR cấp tài sản** (factory QR vòng 1): 6 quyết định kiến trúc (payload `qr_token`, deep-link `/a/<token>`, lifecycle `qr_generated`/`label_printed`, RBAC `asset.read`, backfill, tương thích ngược `internal_tag_qr`) + roadmap A1→A6+B. Schema chi tiết ở `imm-00` §II.1.8 + IMM-04 §8.1.

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
- [x] Chuẩn hóa naming `Clinical Release` vs `Clinical_Release` trong code (DONE — workflow/services/types đều dùng space)
- [x] Rename Pinia store `stores/commissioning.ts` → `stores/imm04.ts` (DONE — align convention `immXX.ts`)
- [ ] Thêm DB UNIQUE constraint cho `vendor_serial_no` (Sprint 7)
- [ ] Config Print Format Biên bản Bàn giao (Sprint 7)
- [ ] IMM-08 listener cho `imm04_asset_released` (Sprint 8)

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm04.py` (1697 LOC) · `assetcore/api/imm04.py` (**34** `@frappe.whitelist()` endpoints)
- Codebase ground truth (FE): `frontend/src/types/imm04.ts` · `frontend/src/api/imm04.ts`

---

*Module index — auto-generated khi migration. Khi update file thực tế, manual sync README này.*
