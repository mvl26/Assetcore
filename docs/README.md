# AssetCore — Tài liệu (docs/)

| Mục | Giá trị |
|---|---|
| Phạm vi | Tổng index cho toàn bộ tài liệu AssetCore |
| Cập nhật | 2026-05-08 (v5 — full chuẩn hóa 13 module) |

---

## 1. Cấu trúc thư mục

```
docs/
├── README.md                       (file này — tổng index)
├── template/                       Bộ template chuẩn (11 file + Migration Guide)
│   ├── 00_README.md
│   ├── 01_Architecture.md          (project-wide)
│   ├── 02_Analysis_Design.md       (per-module)
│   ├── 03_Diagrams.md              (per-module)
│   ├── 04_Backend_Design.md        (per-module)
│   ├── 05_API_Specification.md     (per-module)
│   ├── 06_Frontend_Design.md       (per-module)
│   ├── 07_Testing_QA.md            (per-module)
│   ├── 08_Deployment.md            (per-module)
│   ├── 09_Release.md               (per-module)
│   ├── 10_Project_Management.md    (cross-cutting)
│   └── MIGRATION_GUIDE.md          Hướng dẫn chuẩn hóa module cũ → template
│
├── imm-00/ → imm-16/               13 module IMM (mỗi module có README.md index)
│
├── architecture/                   Kiến trúc dự án (snapshot)
├── ba/                             BA phase docs (waterfall reference) + handover package
├── res/                            Tài liệu nội bộ (design system FE, router map, etc.)
├── adr/                            Architecture Decision Records (chưa setup)
├── agile/                          Sprint plans + Product backlog (chưa setup)
├── gmdn/                           GMDN nomenclature reference
└── WHO/                            WHO HTM Series reference
```

---

## 2. Modules (per-module docs)

Mỗi module có `README.md` index map cũ ↔ template chuẩn.

| Module | Tên | Wave | Trạng thái | Index |
|---|---|---|---|---|
| **IMM-00** | **Master / Cross-cutting** | **Master** | **Live ✅ — docs reviewed vs code** | [README](imm-00/README.md) |
| IMM-01 | Nhu cầu (Needs Request) | 2 | **Live ✅** — docs reviewed vs code | [README](imm-01/README.md) |
| IMM-02 | Tech Specifications | 2 | **Live ✅** — docs reviewed vs code | [README](imm-02/README.md) |
| IMM-03 | Mua sắm (Procurement) | 2 | **Live ✅** — docs reviewed vs code | [README](imm-03/README.md) |
| IMM-04 | Lắp đặt (Installation) | 1 | **Live ✅** — docs reviewed vs code | [README](imm-04/README.md) |
| IMM-05 | Hồ sơ thiết bị | 1 | **Live ✅** — docs reviewed vs code | [README](imm-05/README.md) |
| IMM-06 | Đào tạo (Training) | 1+ | ⚠️ PLANNED — spec only, no code yet | [README](imm-06/README.md) |
| IMM-08 | Bảo trì định kỳ (PM) | 1 | **Live ✅** — docs reviewed vs code | [README](imm-08/README.md) |
| **IMM-09** | **Sửa chữa (CM)** | **1** | **Live ⭐ — reference module, docs reviewed** | [README](imm-09/README.md) |
| IMM-11 | Hiệu chuẩn (Calibration) | 1 | **Live ✅** — docs reviewed vs code | [README](imm-11/README.md) |
| IMM-12 | Sự cố (Incident / RCA) | 1 | **Live ✅** — docs reviewed vs code | [README](imm-12/README.md) |
| IMM-15 | Decommission | 3 | ⚠️ PLANNED — spec reviewed vs old docs | [README](imm-15/README.md) |
| IMM-16 | Tài chính / Khấu hao | 3 | ⚠️ PLANNED — spec reviewed vs old docs | [README](imm-16/README.md) |

---

## 3. Quy ước tài liệu

### 3.1. Format hiện hành (template v4.1+)
- **Tài liệu mới**: viết theo `template/` — 11 file numbered (00-10).
- **Tài liệu cũ** (6-doc per module): giữ nguyên + thêm `README.md` index map.
- **Migration light-touch** — KHÔNG xóa content cũ, chỉ bổ sung file thiếu (07/08/09).

### 3.2. Khi build module mới
1. Copy `template/0{2..9}_*.md` vào `imm-XX/`
2. Tạo `imm-XX/README.md` từ pattern README các module có sẵn
3. KHÔNG dùng format 6-doc cũ cho module mới

### 3.3. Khi update module cũ
1. Đọc `imm-XX/README.md` xem map cũ ↔ template
2. Sửa file cũ phù hợp section nào trong template
3. Update README index nếu thêm/bớt file
4. Khi đến milestone (handover/audit) → bổ sung 07/08/09 thiếu

---

## 4. Tham chiếu nhanh

- **Template chuẩn**: [`template/00_README.md`](template/00_README.md)
- **Migration guide**: [`template/MIGRATION_GUIDE.md`](template/MIGRATION_GUIDE.md)
- **Design system FE**: [`res/design-frontend.md`](res/design-frontend.md)
- **Architecture refactor 3-tier**: [`res/Architecture_3Tier_Refactor_2026-04-20.md`](res/Architecture_3Tier_Refactor_2026-04-20.md)
- **Codebase ground truth**:
  - BE ErrorCode: `assetcore/services/shared/constants.py:ErrorCode`
  - BE response helpers: `assetcore/api/imm<XX>.py:_handle/_ok/_err`
  - BE service pattern: `assetcore/services/imm09.py` (reference)
  - FE types folder: `frontend/src/types/`
  - FE API errors: `frontend/src/api/errors.ts`

---

## 5. Roadmap chuẩn hóa toàn bộ docs/

- [x] v1: Folder `template/` 11 file + MIGRATION_GUIDE
- [x] v2: README.md index per module (13 module)
- [x] v3: README.md tổng (file này)
- [x] v4: Bổ sung 07/08/09 cho mỗi Wave 1 module (mature) trước handover bệnh viện đầu
- [x] v5: Chuẩn hóa đầy đủ 02–09 cho **tất cả 13 module** (Wave 1/2/3 + IMM-00)
- [x] v6: Review + revise docs theo codebase thực tế (Wave 1 + Wave 2 live modules); archive tài liệu cũ → `docs/architecture/archive/imm-XX/`
- [ ] v7: Setup `adr/` + `agile/` folders với template files
- [ ] v8: Sync docs Wave 3 (IMM-15/16) + IMM-06 khi go-live

---

*Khi cập nhật bất kỳ file nào trong docs/, sync README liên quan trong cùng PR.*
