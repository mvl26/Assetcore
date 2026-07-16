# IMM-03 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-03 — Đánh giá Nhà cung cấp & Quyết định Mua sắm (Procurement)** |
| Wave | 2 — Live ✅ |
| Trạng thái | ✅ Đã triển khai — BE + FE LIVE |
| Số file | 8 template chuẩn (nguồn gốc đã archive) |
| Cập nhật cuối | 2026-07-14 (CR-WF-03-AVL-COND: `set_avl_conditional` + INV-AVL-ENDPOINT-MAP + Self-Correction cơ chế AVL doc↔code) |
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

*Module IMM-03 — Wave 2 LIVE. Cập nhật 2026-06-04 (vòng 22: hợp nhất cổng eligibility AVL về 1 SoT `_avl_is_live` — INV-AVL-LIVE, 02 §IV.6; vòng 26: cổng tie-break chấm điểm NCC — KHÔNG auto-award khi đỉnh hòa, INV-VE-TIE, 02 §IV.7; vòng drilldown: KPI tile "Quyết định mua sắm" drillable + bảo toàn INVARIANT card==drill bằng predicate `docstatus<2` đồng nhất count/list — INV-DEC-DRILL, 02 §IV.8; vòng 18 (2026-07-10): đóng workflow AVL thứ 3/3 — CTA server-driven `allowed_transitions` role-filtered + enforce transition qua `apply_workflow` (BỎ set `workflow_state` thô LL-BE-62 + BỎ approver client-spoof), ADR-IMM-03-03/04, INV-CTA-05, 02 §IV.11 / 04 §VII.3.a; vòng 19 (2026-07-10): bịt RBAC bypass AC Purchase (Đơn mua hàng) — thêm cap `purchase.{read,write,create,delete,submit,cancel}` bind DocPerm AC Purchase (cap-count 98→104), `rbac.require` ở 6 endpoint đổi-trạng-thái + gate `inventory.create` cho phiếu nhập kho, `mark_received` qua `doc.save()`+allow_on_submit (BỎ `db_set`/`ignore_permissions`), `get_purchase` phát 6 cờ `can_*` server-driven, PurchaseDetailView gate CTA theo cờ (GATE-8/LL-FE-51), ADR-IMM-03-05/06, INV-PUR-RBAC, 02 §IV.12 / 04 §VII.4 / 05 §3.A / 06 §II.9 / 07 §III.A).*
