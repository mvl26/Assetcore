# IMM-11 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-11 — Hiệu chuẩn (Calibration)** |
| Wave | 1 |
| Trạng thái | ✅ Live — Code deployed (BE + FE + DocTypes) |
| Số file | 8 (5 template chuẩn + 3 deployment docs) |
| Cập nhật cuối | 2026-07-28 (AC-CR-86 **✅ BE Bước-4 LANDED** — handler `api/imm11.py:131` POST-only → `services/imm11.py:1217 reschedule_calibration`; 6 message_code vào registry; guard OAS lật khỏi PENDING-BE, cite refresh; `test_mobile_oas` 1024/1024 XANH) · 2026-07-27 (AC-CR-86 [BA spec] — **dời lịch hiệu chuẩn KHÔNG có đường hợp lệ nào**: `_UPDATE_ALLOWED` (`services/imm11.py:1298`) thiếu `scheduled_date` ⇒ `update_calibration` **NUỐT IM LẶNG** (success + 0 thay đổi) ⇒ buộc hủy+tạo lại → phiếu `Cancelled` rác vào hồ sơ NĐ98 + mất lịch sử. Chốt op riêng `reschedule_calibration(name,new_date,reason)`: guard SSoT `RESCHEDULE_CAL_STATES` · **KHÔNG flip trạng thái** (khác `reschedule_pm` IMM-08) · lý do ≥5 ký tự · `new_date ≥ today` · **ĐÚNG 1 vết audit** + append `amendment_reason` · cap-gate ở **service** (403 in-envelope) · **KHÔNG đụng** `AC Asset.next_calibration_date` + `IMM Calibration Schedule.next_due_date`; kèm BR-11-20 bịt nhánh nuốt-im-lặng ở `update_calibration`. 0 DocType/DocField/cap mới ⇒ **KHÔNG `bench migrate`**. **BA slice ĐÓNG (CONTRACT-ONLY):** OAS +1 path `rescheduleCalibration` (109→110) +3 schema (287→290) + `CalibrationDetail.can_reschedule`; guard `test_mobile_oas` **1024 OK** (+9 `cr86_a..i`) · `test_mobile_docset` **9 OK** · `test_imm11` **120 OK** (baseline). File: 02 §BR-11-19/20 + US-11-04 (AC-11-49…60) · 04 §4.1.12/13 + ADR-IMM11-10..13 · 05 §0.1.11 + §2 #13 + §11.2 · 06 §3.3-ter · 07 §IX · README. Handoff → [BE] Bước-4 (service+api+5 MSG code + `gen_fe_messages.py` + TC-CAL-RS-01..15 + LẬT `cr86_h`/chuyển path khỏi `_PENDING_BE_PATHS`), [FE] nút «Dời lịch hiệu chuẩn» theo cờ `can_reschedule`) · Trước đó 2026-07-25 (CR-74 read-gate `get_calibration`) |
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

*Round 18 (2026-07-13, CR-WF-11-CAL): thêm ADR-IMM11-06 dual-track lockstep `workflow_state ⇄ status` (đóng desync workflow_state đọng state khởi tạo) — spec ở `04_Backend_Design.md §3.2`, state-note `02_Analysis_Design.md §IV.3`, test `07_Testing_QA.md §III.4b`, API-note `05 §0`, FE-no-change `06 §4`. BE-only, 0 migrate, 0 đổi FE.*
