# IMM-04 — Lắp đặt, định danh và kiểm tra ban đầu

| Mục | Giá trị |
|---|---|
| Khối kiến trúc | B. KHỐI 2 — Deployment |
| Đợt triển khai | 1 |
| Owner | PTP Khối 2 · Workshop / Nhóm TBYT · Mạng lưới TBYT nội viện |
| Trạng thái docs | Mature — có v2 UAT |
| Cập nhật | 2026-05-10 |

> Module **deployment gateway** bắt buộc trong vòng đời thiết bị y tế: tiếp nhận → kiểm tra hồ sơ → lắp đặt → định danh (QR + serial) → đo kiểm baseline → phê duyệt → mint Asset. Khóa chất lượng tiếp nhận, định danh đa lớp, baseline kỹ thuật, initial inspection và release gate trước khi đưa thiết bị vào sử dụng.

## Tài liệu

- [02 Analysis & Design](./02_Analysis_Design.md) — BA + BPMN + Use Case + Functional Specs + NFR
- [03 Diagrams](./03_Diagrams.md) — ERD + Class + Sequence + Communication + Package
- [04 Backend Design](./04_Backend_Design.md) — DocType + Workflow + Service + 3-tier + Hooks
- [05 API Specification](./05_API_Specification.md) — Endpoint catalog + Envelope `{success, data}` + ErrorCode
- [06 Frontend Design](./06_Frontend_Design.md) — Sitemap + Mockup + Pinia + Cascade + UX rules
- [07 Testing & QA](./07_Testing_QA.md) — Test plan + UAT script (v1+v2) + Security review
- [08 Deployment](./08_Deployment.md) — Deploy + QMS Mapping (NĐ98 / WHO HTM / ISO 13485)
- [09 Release](./09_Release.md) — User guide (VI) + Release notes + Traceability matrix

## Tham chiếu chéo

- **Architecture**: [`../architecture/Ho_so_kien_truc_IMMIS.md`](../architecture/Ho_so_kien_truc_IMMIS.md) §"Khối 2 — Deployment", §"Đợt triển khai 1"
- **WHO HTM**:
  - `../WHO/Inventory and maintenance 2025.md` — inventory & commissioning pattern
  - `../WHO/Introduction to medical equipment inventory management.md` — định danh & baseline
- **GMDN / NĐ98**:
  - `../gmdn/Quyết định 3107_QĐ-BYT.md` — phân loại thiết bị A/B/C/D
  - `../gmdn/Quyết định 69_QĐ-BYT.md` · `../gmdn/Quyết định 847_QĐ-BYT.md` — danh mục TTBYT
  - NĐ 98/2021/NĐ-CP (Điều 28-32) — Chứng nhận ĐK lưu hành trước khi sử dụng (gate GW-2)
  - NĐ 142/2020/NĐ-CP (Điều 25-27) — Giấy phép thiết bị bức xạ (Clinical Hold, VR-07)
- **Skill build**:
  - `.claude/skills/assetcore-be-module/SKILL.md` — pattern 3-tier BE
  - `.claude/skills/assetcore-fe-module/SKILL.md` — Vue 3 + Pinia + TanStack Query
  - `.claude/skills/assetcore-doctype-designer/SKILL.md` — DocType `Asset Commissioning`
  - `.claude/skills/assetcore-workflow-builder/SKILL.md` — workflow 11 states / 22 transitions
- **Codebase ground truth**:
  - BE: `assetcore/services/imm04.py` · `assetcore/api/imm04.py` · `assetcore/repositories/imm04_repo.py`
  - FE: `frontend/src/types/imm04.ts` · `frontend/src/api/imm04.ts`

## Liên kết module

| Hướng | Module | Mục đích |
|---|---|---|
| INPUT | [IMM-03](../imm-03/README.md) | Nhận `po_reference` từ Procurement |
| OUTPUT | [IMM-05](../imm-05/README.md) | Auto-import document set; gate GW-2 |
| OUTPUT | [IMM-08](../imm-08/README.md) | Realtime event `imm04_asset_released` → trigger PM schedule |
| OUTPUT | IMM-11, IMM-12 | Asset record là input cho calibration & corrective |

## Map cũ → Template chuẩn

| Template (chuẩn mới) | File hiện có | Trạng thái |
|---|---|---|
| 02 Analysis_Design | [`02_Analysis_Design.md`](./02_Analysis_Design.md) | ✅ Stable |
| 03 Diagrams | [`03_Diagrams.md`](./03_Diagrams.md) | ✅ Stable |
| 04 Backend_Design | [`04_Backend_Design.md`](./04_Backend_Design.md) | ✅ Stable |
| 05 API_Specification | [`05_API_Specification.md`](./05_API_Specification.md) | ✅ Stable |
| 06 Frontend_Design | [`06_Frontend_Design.md`](./06_Frontend_Design.md) | ✅ Stable |
| 07 Testing & QA + UAT | [`07_Testing_QA.md`](./07_Testing_QA.md) | ✅ Stable (v1 + v2 UAT inline) |
| 08 Deployment + QMS | [`08_Deployment.md`](./08_Deployment.md) | ✅ Stable |
| 09 Release + Traceability | [`09_Release.md`](./09_Release.md) | ✅ Stable |

Source docs (cũ) đã archive tại `docs/architecture/archive/imm-04/`:
`IMM-04_API_Interface.md`, `IMM-04_Functional_Specs.md`, `IMM-04_Module_Overview.md`, `IMM-04_Technical_Design.md`, `IMM-04_UAT_Script.md`, `IMM-04_UAT_Script_v2.md`, `IMM-04_UI_UX_Guide.md`.

## Roadmap còn lại (tech-debt)

- [ ] Chuẩn hóa naming `Clinical Release` vs `Clinical_Release` (Sprint 7)
- [ ] Thêm DB UNIQUE constraint cho `vendor_serial_no` (Sprint 7)
- [ ] Config Print Format Biên bản Bàn giao (Sprint 7)
- [ ] IMM-08 listener cho `imm04_asset_released` (Sprint 8)
- [ ] Rollback transaction `mint_core_asset` khi IMM-05 import fail (Sprint 9)

---

*Module index — manual sync khi update file thực tế.*
