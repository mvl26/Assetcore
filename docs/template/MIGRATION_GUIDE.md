# Migration Guide — Chuẩn hóa tài liệu module theo template

| Mục | Giá trị |
|---|---|
| Phạm vi | 13 module IMM hiện có (`docs/imm-00` → `docs/imm-16`) |
| Strategy | **Light-touch** — KHÔNG rewrite content cũ. Map sang template + bổ sung file thiếu |
| Owner | BA Lead + Tech Lead |

> **Mục đích**: Hướng dẫn chuyển bộ tài liệu hiện tại (6 file/module: Module_Overview, Functional_Specs, Technical_Design, API_Interface, UI_UX_Guide, UAT_Script) sang cấu trúc template chuẩn (8 file per-module: 02-09).

---

## 1. Hiện trạng vs Template

### 1.1. Format cũ — 6 file/module

| File hiện có | Nội dung |
|---|---|
| `IMM-XX_Module_Overview.md` | Pitch + scope + KPI + stakeholders |
| `IMM-XX_Functional_Specs.md` | User stories + business rules + state machine |
| `IMM-XX_Technical_Design.md` | DocType + workflow + service + diagrams (gộp) |
| `IMM-XX_API_Interface.md` | Endpoint + request/response |
| `IMM-XX_UI_UX_Guide.md` | Sitemap + screens + components |
| `IMM-XX_UAT_Script.md` | Kịch bản UAT |

### 1.2. Format mới — 8 file/module (theo template)

| File template | Nội dung |
|---|---|
| `02_Analysis_Design.md` | Khảo sát + Module Overview + BPMN + Use Case + Functional + NFR |
| `03_Diagrams.md` | ERD + Class + Sequence + Communication + Package (riêng) |
| `04_Backend_Design.md` | DocType + Workflow + Service + Hooks (BE thuần) |
| `05_API_Specification.md` | API Catalog + Type + Error/Success format chuẩn |
| `06_Frontend_Design.md` | UI/UX + Cascade + Tight validation + Mockup/Screenshot |
| `07_Testing_QA.md` | Test plan + UAT + Security + Code quality |
| `08_Deployment.md` | Deploy + QMS Mapping + Cấu hình môi trường |
| `09_Release.md` | User guide + Release notes + Traceability + Statistics |

> File 00, 01, 10 là project-wide (1 lần), không per-module.

---

## 2. Mapping cũ → mới

| File cũ | Maps sang template | Note |
|---|---|---|
| `Module_Overview.md` | **02 §I** (Module Overview) | Move 1-1, không split |
| `Functional_Specs.md` | **02 §IV** (Functional Specs) + **02 §V** (NFR) | Có thể tách NFR ra section riêng |
| `Functional_Specs.md` § Use Case | **02 §III** (Use Case Spec) | Có thể tách thành sub-section |
| `Functional_Specs.md` § Workflow | **02 §IV.3** (State Machine) HOẶC **04 §3** (Workflow) | Logic ↔ Implementation |
| `Technical_Design.md` § DocType | **04 §2** (Domain Model) | Move 1-1 |
| `Technical_Design.md` § Workflow | **04 §3** | Move 1-1 |
| `Technical_Design.md` § Service | **04 §4** | Pattern thực tế: function-based + ServiceError |
| `Technical_Design.md` § ERD | **03 §I** (ERD + Data dictionary) | Tách ra file riêng |
| `Technical_Design.md` § Class diagram | **03 §II** | Tách ra |
| `Technical_Design.md` § Sequence | **03 §III** | Tách ra |
| `Technical_Design.md` § Audit chain | **04 §6** + **03 §II.b** (HashUtil class) | Bám impl thực tế |
| `API_Interface.md` § Endpoint table | **05 §0** (API Catalog) | Refactor format có thêm cột Type |
| `API_Interface.md` § Per-endpoint | **05 §99** template | Update envelope `{success, data}` thực tế |
| `UI_UX_Guide.md` § Sitemap | **06 §1** | Move |
| `UI_UX_Guide.md` § Screens | **06 §3** archetype | Move |
| `UI_UX_Guide.md` § Components | **06 §4** | Move |
| `UAT_Script.md` | **07 §II** (UAT Script) | Move 1-1 |

### 2.1. Phần MỚI cần bổ sung (không có trong format cũ)

| Template section | Lý do thiếu |
|---|---|
| **03 §IV** Communication Diagram | Format cũ chưa làm |
| **03 §V** Package Diagram | Format cũ chưa làm |
| **07 §I** Test Plan (unit + integration + coverage) | Format cũ chỉ có UAT |
| **07 §III** Security Review | Format cũ chưa formal |
| **07 §IV** Code quality (Sonarqube/Lighthouse) | Format cũ chưa có |
| **08** Deployment Plan + QMS Mapping | Format cũ chưa có per-module |
| **09 §I** User Guide tiếng Việt cho end-user | Format cũ chưa có |
| **09 §II** Release Notes per module | Format cũ chưa có |
| **09 §III** Traceability Matrix | Format cũ chưa có |

---

## 3. Strategy — Light-touch migration

### 3.1. Nguyên tắc
- **KHÔNG xóa content cũ** — file 6-doc giữ nguyên làm reference.
- **THÊM mới** các file template thiếu (07, 08, 09) khi cần (theo wave/sprint).
- **Refactor incremental** — module nào active, mới làm. Module mature stable, KHÔNG đụng.
- Mỗi module có `README.md` index map cũ ↔ template.

### 3.2. Khi nào migrate?
| Tình huống | Action |
|---|---|
| Module mới (vd IMM-13/14) chưa có doc | Dùng template trực tiếp 02-09, KHÔNG dùng format 6-doc |
| Module đang active development | Bổ sung 07/08/09 + giữ 6-doc cũ |
| Module mature nhưng chuẩn bị handover/audit | Compile 6-doc + 07/08/09 → file `Final_Report.md` riêng |
| Module stable không thay đổi | Giữ nguyên 6-doc, chỉ thêm `README.md` index |

### 3.3. Per-module README pattern

Mỗi `docs/imm-XX/` có 1 `README.md` index theo template dưới (file `MIGRATION_GUIDE.md` đã include sample).

---

## 4. README per-module template

Copy + sửa cho mỗi imm-xx/:

```markdown
# IMM-XX — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | IMM-XX — <tên> |
| Wave | <1/2/3> |
| Trạng thái | <Active / Mature / Stub> |
| Owner | <…> |
| Cập nhật cuối | <YYYY-MM-DD> |

> Tài liệu module dùng song song format cũ (6 file) + bổ sung mới theo `docs/template/`.

## Map theo template

| Template | File hiện có (cũ) | Trạng thái |
|---|---|---|
| 02 Analysis_Design | IMM-XX_Module_Overview.md + IMM-XX_Functional_Specs.md | ✅ Có (gộp 2) |
| 03 Diagrams | (rút từ IMM-XX_Technical_Design.md §ERD/Class/Sequence) | ⚠️ Phân tán |
| 04 Backend_Design | IMM-XX_Technical_Design.md | ✅ Có |
| 05 API_Specification | IMM-XX_API_Interface.md | ✅ Có |
| 06 Frontend_Design | IMM-XX_UI_UX_Guide.md | ✅ Có |
| 07 §I Test Plan + §III Security + §IV Code quality | — | ❌ Thiếu |
| 07 §II UAT Script | IMM-XX_UAT_Script.md | ✅ Có |
| 08 Deployment + QMS | — | ❌ Thiếu |
| 09 User Guide + Release + Traceability | — | ❌ Thiếu |

## Files

(auto-generated list of *.md trong folder)

## Roadmap chuẩn hóa
- [ ] Bổ sung 07_Testing_QA (Test Plan + Security)
- [ ] Bổ sung 08_Deployment (DevOps + QMS)
- [ ] Bổ sung 09_Release (User Guide + Notes + Trace)
- [ ] (Optional) Refactor Technical_Design → tách 03 Diagrams + 04 Backend
```

---

## 5. Module status hiện tại (tổng quan)

| Module | Wave | Files | Lines | Status migration |
|---|---|---|---|---|
| IMM-00 | Master | 7 | 6,272 | Đặc biệt — có Setup_Guide + Inventory_Design |
| IMM-01 | 2 | 6 | 1,547 | Stub Wave 2 |
| IMM-02 | 2 | 6 | 1,296 | Stub Wave 2 |
| IMM-03 | 2 | 6 | 1,649 | Stub Wave 2 |
| IMM-04 | 1 | 7 | 3,380 | Mature — có UAT_Script_v2 |
| IMM-05 | 1 | 6 | 2,221 | Mature |
| IMM-06 | 1+ | 6 | 3,488 | Mature |
| IMM-08 | 1 | 6 | 2,032 | Mature |
| IMM-09 | 1 | 6 | 2,905 | Mature ⭐ (reference module) |
| IMM-11 | 1 | 6 | 2,915 | Mature |
| IMM-12 | 1 | 6 | 2,637 | Mature |
| IMM-15 | 3 | 6 | 3,246 | Stub Wave 3 |
| IMM-16 | 3 | 6 | 3,457 | Stub Wave 3 |

---

## 6. DoD — Migration mỗi module

- [ ] `README.md` index trong folder module (map cũ → template)
- [ ] File cũ giữ nguyên (làm reference)
- [ ] Bổ sung 07/08/09 nếu module sẽ go-live
- [ ] (Optional) Tách Technical_Design → 03 Diagrams + 04 Backend khi cần
- [ ] Update API_Interface theo envelope mới (05 §1) khi có endpoint mới
- [ ] Reviewed bởi BA Lead + Tech Lead module

---

*Migration KHÔNG bắt buộc với module stable. Áp dụng dần — module nào active sửa nội dung, mới refactor sang format mới.*
