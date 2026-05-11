# IMM-12 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-12 — Sự cố (Incident / RCA / CAPA)** |
| Wave | 1 |
| Trạng thái | ✅ Live — Code deployed (BE + FE + DocTypes) |
| Số file | 8 (5 template chuẩn + 3 deployment docs) |
| Cập nhật cuối | 2026-05-10 |
| Khối kiến trúc | C. KHỐI 3 |
| Đợt triển khai | 1 |
| Owner | PTP Khối 2 · Workshop / Nhóm TBYT |

> File index của module IMM-12. Template docs (`02–06`) đã được cross-check với codebase thực tế và cập nhật.
> Files cũ (`IMM-12_*.md`) đã archive vào `docs/architecture/archive/imm-12/`.

---

## Template chuẩn (v4.1+ — cross-checked vs codebase)

| File | Mô tả | Trạng thái |
|---|---|---|
| [`02_Analysis_Design.md`](./02_Analysis_Design.md) | Module overview · Business process · Use case · Functional specs · NFR | ✅ Live |
| [`03_Diagrams.md`](./03_Diagrams.md) | ERD · Class diagram · Sequence diagram · Package diagram | ✅ Live |
| [`04_Backend_Design.md`](./04_Backend_Design.md) | DocType · Workflow · Service layer · API layer · Scheduler · Integration | ✅ Live — corrected |
| [`05_API_Specification.md`](./05_API_Specification.md) | API catalog · Response envelope · Error codes · 14 actual endpoints | ✅ Live — corrected |
| [`06_Frontend_Design.md`](./06_Frontend_Design.md) | Sitemap · Actual .vue files · API client · Status states | ✅ Live — corrected |

---

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File cũ (reference) | Ghi chú |
|---|---|---|
| 02 Analysis_Design | `IMM-12_Module_Overview.md` + `IMM-12_Functional_Specs.md` | Đã gộp và chuẩn hóa vào 02 |
| 03 Diagrams | `IMM-12_Technical_Design.md` §4 ERD + §5 State Machines | Đã tách riêng vào 03 + Data Dictionary |
| 04 Backend_Design | `IMM-12_Technical_Design.md` §2–§3 (Service, Controller, hooks) | Đã chuẩn hóa vào 04 |
| 05 API_Specification | `IMM-12_API_Interface.md` | Updated envelope `{success, data}` chuẩn |
| 06 Frontend_Design | `IMM-12_UI_UX_Guide.md` | Updated theo template v4.1 |

---

## Files hiện có

### Template chuẩn (cross-checked vs codebase)
- [`02_Analysis_Design.md`](./02_Analysis_Design.md)
- [`03_Diagrams.md`](./03_Diagrams.md)
- [`04_Backend_Design.md`](./04_Backend_Design.md) — corrected DocType names, states, service functions, API layer
- [`05_API_Specification.md`](./05_API_Specification.md) — corrected: 14 actual endpoints, corrected request fields
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — corrected: actual .vue filenames, actual status states

### Deployment docs
- [`07_Testing_QA.md`](./07_Testing_QA.md) — Test plan + Security + Code quality
- [`08_Deployment.md`](./08_Deployment.md) — Deployment + QMS Mapping
- [`09_Release.md`](./09_Release.md) — User guide + Release notes + Traceability

### Archived (moved)
> Files cũ (`IMM-12_*.md`) đã được archive vào [`docs/architecture/archive/imm-12/`](../../architecture/archive/imm-12/).

---

## Roadmap chuẩn hóa

- [x] Tạo **`02_Analysis_Design.md`** — Module overview · Business process · Use case · Functional specs · NFR
- [x] Tạo **`03_Diagrams.md`** — ERD · Class · Sequence (3 diagrams) · Package
- [x] Tạo **`04_Backend_Design.md`** — DocType · Workflow · Service · API · Scheduler · Integration
- [x] Tạo **`05_API_Specification.md`** — Catalog · Envelope chuẩn `{success, data}` · Error codes
- [x] Tạo **`06_Frontend_Design.md`** — Sitemap · Mockup · Components · Store · Copy
- [x] ✅ Implement BE: `services/imm12.py` + `api/imm12.py` + DocType JSONs (incident_report, imm_rca_record, imm_capa_record, imm_rca_five_why_step, imm_rca_related_incident)
- [x] ✅ Implement FE: Vue components (7 views: IncidentList/Create/Detail, RCADetail, CAPAList/Detail, IMM12Dashboard) + API client (`api/imm12.ts`)
- [x] ✅ Cross-check docs vs codebase + corrections applied (2026-05-08)
- [x] ✅ Archive old source files → `docs/architecture/archive/imm-12/`
- [ ] UAT execution

---

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm12.py` · `assetcore/api/imm12.py` ✅
- Codebase ground truth (FE): `frontend/src/api/imm12.ts` ✅
- DocTypes: `assetcore/assetcore/doctype/incident_report/` · `imm_rca_record/` · `imm_capa_record/` · `imm_rca_five_why_step/` · `imm_rca_related_incident/`
- LIVE foundation: `assetcore/services/imm00.py` · `assetcore/api/imm00.py`
- Archive (old reference docs): `docs/architecture/archive/imm-12/`

---

*Module index — cập nhật 2026-05-08 sau khi cross-check codebase và archive files cũ.*
