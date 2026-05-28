# IMM-06 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-06 — Đào tạo & Năng lực (Training & Competency)** |
| Wave | 2 |
| Trạng thái | Stable (Wave 2) |
| Số file hiện có | 9 (6 source docs đã archive) |
| Cập nhật cuối | 2026-05-27 |
| Khối kiến trúc | B. KHỐI 2 |
| Đợt triển khai | 2 |
| Owner | PTP Khối 2 · Tổ HC-QLCL |

> File index của module IMM-06. Map cũ ↔ template chuẩn theo `docs/template/` (v4.1+).
> **Strategy: light-touch** — file 6-doc cũ giữ nguyên làm reference; file template mới (02–09) là spec đã align với code Wave 2 đã ship.

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File hiện có | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | ✅ Có — từ Module_Overview + Functional_Specs |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | ✅ Có — tách từ Technical_Design |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | ✅ Có — đầy đủ DocType + Workflow + Service + Scheduler |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | ✅ Có — envelope chuẩn `{success, data}` — 25 endpoints |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | ✅ Có — Sitemap + Components + Store + i18n |
| 07 §I Test Plan + §III Security + §IV Code quality | [`07_Testing_QA.md`](./07_Testing_QA.md) | ✅ Có |
| 07 §II UAT Script | `IMM-06_UAT_Script.md` | ✅ Có |
| 08 Deployment + QMS Mapping | [`08_Deployment.md`](./08_Deployment.md) | ✅ Có |
| 09 User Guide + Release Notes + Traceability | [`09_Release.md`](./09_Release.md) | ✅ Có |

## Files hiện có

**Template chuẩn (Wave 2 spec):**

- [`02_Analysis_Design.md`](./02_Analysis_Design.md) — Phân tích nghiệp vụ, 3 BPMN flows, 12 US Gherkin, BR + VR, NFR
- [`03_Diagrams.md`](./03_Diagrams.md) — ERD (6 DocTypes), Class Diagram, 3 Sequence Diagrams, Communication, Package
- [`04_Backend_Design.md`](./04_Backend_Design.md) — DocType schemas, Service layer, Workflow, Scheduler, Hooks, DB Indexes
- [`05_API_Specification.md`](./05_API_Specification.md) — 25 endpoints, envelope `{success, data}`, TypeScript types
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — 14 routes, Components + wireframes, Pinia store, i18n, Realtime

**Source docs cũ (đã archive vào `docs/architecture/archive/imm-06/`):**

- `IMM-06_API_Interface.md` — 687 dòng
- `IMM-06_Functional_Specs.md` — 470 dòng
- `IMM-06_Module_Overview.md` — 315 dòng
- `IMM-06_Technical_Design.md` — 920 dòng
- `IMM-06_UAT_Script.md` — 523 dòng
- `IMM-06_UI_UX_Guide.md` — 573 dòng

**QA / Deployment / Release:**

- [`07_Testing_QA.md`](./07_Testing_QA.md) — 744 dòng
- [`08_Deployment.md`](./08_Deployment.md) — 451 dòng
- [`09_Release.md`](./09_Release.md) — 532 dòng

## Roadmap chuẩn hóa

- [x] Bổ sung **`02_Analysis_Design.md`** — Phân tích nghiệp vụ + Use Cases + BR + NFR
- [x] Bổ sung **`03_Diagrams.md`** — ERD + Class + Sequence + Communication + Package
- [x] Bổ sung **`04_Backend_Design.md`** — DocType + Workflow + Service + Scheduler
- [x] Bổ sung **`05_API_Specification.md`** — 25 endpoints + envelope chuẩn {success,data}
- [x] Bổ sung **`06_Frontend_Design.md`** — Sitemap + Components + Store + i18n
- [x] Bổ sung **`07_Testing_QA.md`** — Test plan (unit/integration/coverage) + Security review + Code quality (Sonarqube/Lighthouse)
- [x] Bổ sung **`08_Deployment.md`** — Deployment plan + QMS Mapping (NĐ98/WHO HTM) + Cấu hình môi trường thực nghiệm
- [x] Bổ sung **`09_Release.md`** — User guide tiếng Việt + Release notes + Traceability matrix + Bảng thống kê ứng dụng
- [ ] Update **`IMM-06_API_Interface.md`** theo envelope chuẩn AssetCore (`{success, data}` / `{success, error, code}` — đã tách sang `05_API_Specification.md`)
- [ ] (Optional) Tách **`IMM-06_Technical_Design.md`** — đã tách sang `03_Diagrams.md` + `04_Backend_Design.md`; source doc giữ nguyên làm reference

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm06.py` (1533 LOC) · `assetcore/api/imm06.py` (263 LOC, **25** `@frappe.whitelist()` endpoints)
- Codebase ground truth (FE): `frontend/src/types/imm06.ts` (chưa tồn tại — không có file riêng) · `frontend/src/api/imm06.ts` · `frontend/src/stores/imm06.ts` · views `frontend/src/views/training/{Program,Session,Competency}{List,Detail}View.vue` (6 views)
- Workflows fixtures (`assetcore/fixtures/workflow.json`): `IMM-06 Session Workflow`, `IMM-06 Competency Workflow`
- DocTypes (folders trong `assetcore/assetcore/doctype/`): `imm_training_program`, `imm_training_session`, `imm_training_participant`, `imm_user_competency`, `imm_competency_gap_report`, `imm_gap_detail_row`, `imm_competency_alert_log`

---

*Module index — cập nhật thủ công khi thêm/sửa file.*
