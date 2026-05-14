# IMM-02 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường (Tech Spec & Market Analysis)** |
| Wave | 2 |
| Trạng thái | Wave 2 — Live ✅ |
| Số file hiện có | 8 file template chuẩn (README + 02–09) + 1 file `_REPORT.md` audit log = 9 file tổng cộng |
| Cập nhật cuối | 2026-05-14 |
| Khối kiến trúc | A. KHỐI 1 |
| Đợt triển khai | 2 |
| Owner | PTP Khối 1 · Nhóm KH-TC |

> File index của module IMM-02. Module đã có code BE (service + API) và FE (Vue + Pinia + TypeScript) đầy đủ.
> File cũ (`IMM-02_*.md`) đã archive vào `docs/architecture/archive/imm-02/` — không còn trong thư mục này.

## Map Template Chuẩn

| Template (chuẩn mới) | File mới | File cũ (reference) | Trạng thái |
|---|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | `IMM-02_Module_Overview.md` + `IMM-02_Functional_Specs.md` | ✅ Chuẩn hóa |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | (rút từ `IMM-02_Technical_Design.md`) | ✅ Chuẩn hóa |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | (archived) | ✅ Cập nhật — service functions thực tế, DocType folders thực tế |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | (archived) | ✅ Cập nhật — 16 endpoints thực tế, params/response shapes đúng |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | (archived) | ✅ Cập nhật — 3 Vue files thực tế, store actions thực tế |
| 07 Testing QA (Test Plan + UAT + Security + Code quality) | [`07_Testing_QA.md`](./07_Testing_QA.md) | `IMM-02_UAT_Script.md` | ✅ Chuẩn hóa |
| 08 Deployment + QMS Mapping | [`08_Deployment.md`](./08_Deployment.md) | — | ✅ Mới |
| 09 User Guide + Release Notes + Traceability | [`09_Release.md`](./09_Release.md) | — | ✅ Mới |

## Files Template Chuẩn (hiện có trong thư mục này)

- [`02_Analysis_Design.md`](./02_Analysis_Design.md) — Module overview, BPMN, Use Cases (6 UC), 7 BRs, 10 NFRs
- [`03_Diagrams.md`](./03_Diagrams.md) — ERD Mermaid (10 entities), Class Diagram, Sequence Diagrams
- [`04_Backend_Design.md`](./04_Backend_Design.md) — DocType catalog, Service layer thực tế, Workflow 7 states, Schedulers (2 jobs thực tế), DB indexes
- [`05_API_Specification.md`](./05_API_Specification.md) — 16 endpoints thực tế, params/response đúng với code, note rõ endpoints KHÔNG tồn tại
- [`06_Frontend_Design.md`](./06_Frontend_Design.md) — 3 Vue files thực tế, Pinia store actions thực tế, note components TODO
- [`07_Testing_QA.md`](./07_Testing_QA.md) — Test pyramid, UAT scenarios, STRIDE, DocPerm matrix
- [`08_Deployment.md`](./08_Deployment.md) — Pre-deploy checklist, migration patches, QMS mapping, 6 KPIs
- [`09_Release.md`](./09_Release.md) — User guide tiếng Việt, FAQ, Release Notes, Traceability matrix

## Files Đã Archive

File cũ (`IMM-02_*.md`) đã được move sang `docs/architecture/archive/imm-02/` (6 files):
- `IMM-02_Module_Overview.md`, `IMM-02_Functional_Specs.md`, `IMM-02_Technical_Design.md`
- `IMM-02_API_Interface.md`, `IMM-02_UI_UX_Guide.md`, `IMM-02_UAT_Script.md`

## Key Design Decisions

| Quyết định | Giá trị |
|---|---|
| Audit trail | `IMM Audit Trail` (Wave 1 shared) — KHÔNG tạo `Tech Spec Lifecycle Event` riêng |
| API envelope | `{"success": true, "data": {...}}` — HTTP 200 always |
| Workflow states | Title Case (`Draft`, `Reviewing`, `Benchmarked`, `Risk Assessed`, `Pending Approval`, `Locked`, `Withdrawn`) |
| Workflow actions | Tiếng Việt (`Gửi rà soát`, `Hoàn tất benchmark`, `Phê duyệt`, `Rút hồ sơ`) |
| Lock-in weights | Protocol 30%, Consumable 20%, Software 20%, Parts 15%, Service 15% |
| Permlevel | `lock_in_score` và `mitigation_plan` permlevel=1 — chỉ QA Risk / VP Block1 / Admin xem |
| Versioning | Withdraw + Reissue (copy_doc + parent_spec + version bump "1.0"→"2.0") |
| Error handling | `raise ServiceError(ErrorCode.BUSINESS_RULE, "G01: msg tiếng Việt")` |
| Quarterly scheduler | Frappe v15 không có "quarterly" → dùng `cron: "0 3 1 1,4,7,10 *"` |

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Migration guide: [`../template/MIGRATION_GUIDE.md`](../template/MIGRATION_GUIDE.md)
- Codebase ground truth (BE): `assetcore/services/imm02.py` · `assetcore/api/imm02.py`
- Codebase ground truth (FE): `frontend/src/types/imm02.ts` · `frontend/src/api/imm02.ts`
- Module trước: [IMM-01 Needs Assessment](../imm-01/README.md)
- Module tiếp theo: [IMM-03 Vendor Evaluation](../imm-03/README.md)

---

*Module index — Wave 2 docs chuẩn hóa hoàn chỉnh 2026-05-08.*
