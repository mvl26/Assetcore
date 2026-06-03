# IMM-11 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-11 — Hiệu chuẩn (Calibration)** |
| Wave | 1 |
| Trạng thái | ✅ Live — Code deployed (BE + FE + DocTypes) |
| Số file | 8 (5 template chuẩn + 3 deployment docs) |
| Cập nhật cuối | 2026-06-03 |
| Khối kiến trúc | C. KHỐI 3 |
| Đợt triển khai | 1 |
| Owner | PTP Khối 2 · Workshop / Nhóm TBYT |
| Tên đầy đủ | Hiệu năng và hiệu chuẩn |

> File index của module IMM-11. Template docs (`02–06`) đã được cross-check với codebase thực tế và cập nhật.
> Files cũ (`IMM-11_*.md`) đã archive vào `docs/architecture/archive/imm-11/`.

---

## Template chuẩn (v4.1+ — cross-checked vs codebase)

| File | Mô tả | Trạng thái |
|---|---|---|
| [`02_Analysis_Design.md`](./02_Analysis_Design.md) | Module overview · Business process · Use case · Functional specs · NFR | ✅ Live |
| [`03_Diagrams.md`](./03_Diagrams.md) | ERD · Class diagram · Sequence diagram · Package diagram | ✅ Live |
| [`04_Backend_Design.md`](./04_Backend_Design.md) | DocType · Workflow · Service layer · API layer · Scheduler · Integration | ✅ Live — corrected |
| [`05_API_Specification.md`](./05_API_Specification.md) | API catalog · Response envelope · Error codes · 18 actual endpoints | ✅ Live — corrected |
| [`06_Frontend_Design.md`](./06_Frontend_Design.md) | Sitemap · Actual .vue files · Pinia store · API client · Copy | ✅ Live — corrected |

---

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File cũ (reference) | Ghi chú |
|---|---|---|
| 02 Analysis_Design | `IMM-11_Module_Overview.md` + `IMM-11_Functional_Specs.md` | Đã gộp và chuẩn hóa vào 02 |
| 03 Diagrams | `IMM-11_Technical_Design.md` §2–§4 (ERD, State Machine) | Đã tách riêng vào 03 |
| 04 Backend_Design | `IMM-11_Technical_Design.md` §5 (Service, Controller, hooks) | Đã chuẩn hóa vào 04 |
| 05 API_Specification | `IMM-11_API_Interface.md` | Cập nhật envelope `{success, data}` chuẩn |
| 06 Frontend_Design | `IMM-11_UI_UX_Guide.md` | Cập nhật theo template v4.1 |

---

## Files hiện có

### Template chuẩn (cross-checked vs codebase)
- [`02_Analysis_Design.md`](./02_Analysis_Design.md)
- [`03_Diagrams.md`](./03_Diagrams.md)
- [`04_Backend_Design.md`](./04_Backend_Design.md) — corrected DocType names, service functions, API names
- [`05_API_Specification.md`](./05_API_Specification.md) — corrected: 18 actual endpoints, correct function names
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — corrected: actual .vue filenames, actual store state

### Deployment docs
- [`07_Testing_QA.md`](./07_Testing_QA.md) — Test plan + Security + Code quality
- [`08_Deployment.md`](./08_Deployment.md) — Deployment + QMS Mapping
- [`09_Release.md`](./09_Release.md) — User guide + Release notes + Traceability

### Archived (moved)
> Files cũ (`IMM-11_*.md`) đã được archive vào [`docs/architecture/archive/imm-11/`](../../architecture/archive/imm-11/).

---

## Roadmap chuẩn hóa

- [x] Tạo **`02_Analysis_Design.md`** — Module overview · Business process · Use case · Functional specs · NFR
- [x] Tạo **`03_Diagrams.md`** — ERD · Class · Sequence · Package
- [x] Tạo **`04_Backend_Design.md`** — DocType · Workflow · Service · API · Scheduler · Integration
- [x] Tạo **`05_API_Specification.md`** — Catalog · Envelope chuẩn `{success, data}` · Error codes
- [x] Tạo **`06_Frontend_Design.md`** — Sitemap · Mockup · Components · Store · Copy
- [x] ✅ Implement BE: `services/imm11.py` + `api/imm11.py` + DocType JSONs (imm_asset_calibration, imm_calibration_schedule, imm_calibration_measurement)
- [x] ✅ Implement FE: Vue components (7 views) + Pinia store (`stores/imm11.ts`) + API client (`api/imm11.ts`)
- [x] ✅ Cross-check docs vs codebase + corrections applied (2026-05-08)
- [x] ✅ Archive old source files → `docs/architecture/archive/imm-11/`
- [ ] UAT execution

---

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm11.py` · `assetcore/api/imm11.py` ✅
- Codebase ground truth (FE): `frontend/src/api/imm11.ts` · `frontend/src/stores/imm11.ts` ✅
- DocTypes: `assetcore/assetcore/doctype/imm_asset_calibration/` · `imm_calibration_schedule/` · `imm_calibration_measurement/`
- Archive (old reference docs): `docs/architecture/archive/imm-11/`

---

*Module index — cập nhật 2026-05-08 sau khi cross-check codebase và archive files cũ.*
