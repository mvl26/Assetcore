# IMM-15 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-15 — Spare Parts Inventory Tracking (Theo dõi tồn kho phụ tùng y tế)** |
| Wave | 3 — PLANNED |
| Trạng thái | ⚠️ Chưa triển khai — tài liệu đầy đủ |
| Số file | 8 (template chuẩn; nguồn gốc đã archive) |
| Cập nhật cuối | 2026-05-10 |
| Khối kiến trúc | C. KHỐI 3 |
| Đợt triển khai | 2 |
| Owner | Kho trung tâm & Kho vận |

> ⚠️ Module PLANNED — Wave 3. Chưa triển khai. AC Inventory Backbone (Wave 1) phải LIVE trước. Mọi file template đều có banner cảnh báo.

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | ✅ Đã tạo |
| 03 Diagrams (ERD/Class/Sequence/Communication/Package) | [`03_Diagrams.md`](./03_Diagrams.md) | ✅ Đã tạo |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | ✅ Đã tạo |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | ✅ Đã tạo (envelope `{success, data}`) |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | ✅ Đã tạo |
| 07 Testing_QA | [`07_Testing_QA.md`](./07_Testing_QA.md) | ✅ Đã tạo |
| 08 Deployment | [`08_Deployment.md`](./08_Deployment.md) | ✅ Đã tạo |
| 09 Release | [`09_Release.md`](./09_Release.md) | ✅ Đã tạo |

## Files nguồn gốc (Archived)

> Source docs (cũ) đã archive tại [`docs/architecture/archive/imm-15/`](../../architecture/archive/imm-15/).  
> Không tham chiếu trực tiếp — dùng các file template chuẩn `02_`…`09_` ở trên.

| File (archive) | Nội dung |
|---|---|
| `IMM-15_API_Interface.md` | API gốc (BA draft — envelope cũ) |
| `IMM-15_Functional_Specs.md` | FR/NFR/User Stories |
| `IMM-15_Module_Overview.md` | Architecture/DocTypes/BRs |
| `IMM-15_Technical_Design.md` | Schemas/Algorithms/Hooks |
| `IMM-15_UAT_Script.md` | 14 kịch bản UAT |
| `IMM-15_UI_UX_Guide.md` | 12 màn hình/wireframes |

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
- Codebase ground truth (BE): `assetcore/services/imm15.py` · `assetcore/api/imm15.py`
- Codebase ground truth (FE): `frontend/src/types/imm15.ts` · `frontend/src/api/imm15.ts`
- AC Backbone prerequisite: `assetcore/api/inventory.py` · `assetcore/services/inventory.py`

## Kiến trúc đặc biệt

IMM-15 xây trên **AC Inventory Backbone** (Wave 1 LIVE):

| RULE | Nội dung |
|---|---|
| RULE-F01 | KHÔNG tạo DocType phụ tùng mới — dùng `AC Spare Part` |
| RULE-F02 | KHÔNG tạo bảng tồn song song — dùng `AC Spare Part Stock` |
| RULE-F03 | Mọi movement phải sinh `AC Stock Movement` (submitted) |
| RULE-F04 | IMM DocType chỉ LINK qua `stock_movement_ref` — không ghi thẳng vào stock |

---

*Module IMM-15 — Wave 3 PLANNED. Cập nhật 2026-05-10.*
