# IMM-00 — Tài liệu module

| Mục | Giá trị |
|---|---|
| Module | **IMM-00 — Master / Cross-cutting** |
| Wave | Master |
| Trạng thái | **Live ✅ — docs synced vs code 2026-05-27** · Notification Framework Wave N1 spec'd 2026-05-29 · RC-03 kế thừa luật khấu hao Category→Asset spec'd 2026-06-03 (FR-00-47..52 / BR-00-18..21) · RC-04 per-asset self-heal `regenerate_depreciation_schedule` (FR-00-53..55 / BR-00-22) · RC-05 `bulk_regenerate_by_category` về SoT (FR-00-56..58 / BR-00-23) · RC-06 SoT `effective_book_value` (BR-05-13) · **RC-07 thanh lý hủy kỳ Pending khấu hao spec'd 2026-06-03 Vòng 8 (FR-00-59..62 / BR-00-24 — schema-delta `event_type+=depreciation_stopped`)** · RC-08 Out of Service PAUSE + RESCHEDULE khấu hao Vòng 9 (FR-00-63..68 / BR-00-25 — no schema-delta) · RC-CAPA-EFF cổng hiệu quả CAPA SoT đơn Vòng 12 (FR-00-59 / BR-00-26) · **RC-09 nhãn sự kiện khôi phục `restored` ĐÚNG 1 — kill double-emit Vòng 14 (FR-00-69 / BR-00-27 — `_lifecycle_event_for(to,from)`, no schema-delta)** |
| Số file hiện có | 8 (numbered 02–09) |
| Cập nhật cuối | 2026-06-05 (Vòng 28 / B — A6-hardening chiều HIỆU CHUẨN: cờ `calibration_overdue` + `next_calibration_date` server-side trên màn quét QR `get_asset_scan_info` — derive `True ⟺ next_calibration_date<nowdate() (strict) ∧ status∉{Out of Service,Decommissioned}`, mirror `_is_pm_overdue`, timezone-safe SSoT ở BE, FE dòng "Hiệu chuẩn kế tiếp" + badge VI "Quá hạn hiệu chuẩn" render-only + a11y; payload +2 field DISTINCT giữ 9 field cũ, `next_calibration_date` là field AC Asset đã có, 0 cap/schema/field/endpoint/enum/patch delta, `CAP_SET_VERSION` v95.3388ee5629c1; FR-00-86 / BR-00-37) · Vòng 27 / B — A6-hardening: cờ `pm_overdue` server-side trên màn quét QR (FR-00-85 / BR-00-36) · Vòng 26 / B — Self-Correction RC-LIST-VENDORCLOBBER: vá HIGH vendor-isolation regression ở `list_assets` (compose AND filter-list form; BR-00-35 mục 6 / FR-00-84) |
| Khối kiến trúc | Cross-cutting (foundation cho A/B/C/D) |
| Owner | — (Cross-cutting — System Architect + BA Lead) |

> File index của module IMM-00. Tài liệu theo template chuẩn `docs/template/` (v4.1+).
> **Source docs (cũ) đã archive tại `docs/architecture/archive/imm-00/`** (7 files).

## Files hiện có (numbered 02–09)

| File | Nội dung | Trạng thái |
|---|---|---|
| [`02_Analysis_Design.md`](./02_Analysis_Design.md) | Phân tích & thiết kế: Module Overview, Architecture Position, Feature Inventory, FR, NFR, BR-00-01→12 | ✅ Live |
| [`03_Diagrams.md`](./03_Diagrams.md) | Sơ đồ: ERD (foundation + inventory), Class diagram, Sequence (SHA-256 chain, transition, scheduler) | ✅ Live |
| [`04_Backend_Design.md`](./04_Backend_Design.md) | Thiết kế backend: 27 DocType schemas (verified), Service layer 22 functions (verified), shared utilities; 20 roles, state machine đầy đủ incl. Draft + Under Maintenance | ✅ Live — synced vs code 2026-05-18 |
| [`05_API_Specification.md`](./05_API_Specification.md) | API spec: 107 whitelisted endpoints (verified), envelope `{success, data}`, permission matrix | ✅ Live — reviewed vs code |
| [`06_Frontend_Design.md`](./06_Frontend_Design.md) | Thiết kế frontend: Design tokens, Sitemap ([BUILT]/[SPEC] labeled); 10+ views built (asset/, master-data/, audit/), 4 Pinia stores (verified) | ✅ Partial — multiple views built |
| [`07_Testing_QA.md`](./07_Testing_QA.md) | Testing & QA: 13 unit tests (TC-S-001→013, corrected), UAT scenarios, STRIDE security, code quality | Live (BE) / Planned (tests) |
| [`08_Deployment.md`](./08_Deployment.md) | Deployment: Thứ tự deploy (IMM-00 first), env config, migration patches, QMS mapping, rollback | ✅ Live |
| [`09_Release.md`](./09_Release.md) | Release: User guide (System Admin), Release Notes v4.0.0, Traceability matrix, Bảng thống kê | ✅ Live |

## Architecture Decision Records (cross-cutting, chạm registry)

- [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) — **QR cấp tài sản**: chốt `AC Asset.qr_token` (schema-delta §II.1.8 trong `04_Backend_Design.md`) + `Asset Lifecycle Event.event_type += qr_generated, label_printed` (§II.6) + patch backfill `v3_2.008` (§IV.3a). RBAC: read-only QR (`resolve_qr_token`/`get_asset_scan_info`/`get_asset`) = `asset.read`; **in nhãn (`get_asset_label_data[_batch]`/`mark_label_printed`) = `asset.write` (vòng B, least-privilege — KHÔNG cap mới, `CAP_SET_VERSION` GIỮ v95.3388ee5629c1)**; deep-link `/a/<token>`.

## Source docs (cũ) — đã archive

Source docs gốc (7 files) đã được move sang `docs/architecture/archive/imm-00/` sau khi review code 2026-05-08:

- `IMM-00_API_Interface.md` — API spec gốc (envelope cũ)
- `IMM-00_Functional_Specs.md` — FR/NFR gốc
- `IMM-00_Inventory_Design.md` — Inventory sub-domain v4 gốc
- `IMM-00_Module_Overview.md` — Module overview gốc
- `IMM-00_Setup_Guide.md` — Setup guide gốc
- `IMM-00_Technical_Design.md` — Technical design gốc (1937 dòng)
- `IMM-00_UI_UX_Guide.md` — UI/UX guide gốc

## Những thay đổi trong review 2026-05-08

Các discrepancy chính được sửa trong lần review này:

**04_Backend_Design.md:**
- DocType catalog: cập nhật từ 18 → 27 DocType (verified vs `assetcore/assetcore/doctype/`)
- DocType path: sửa từ `assetcore/doctype/` → `assetcore/assetcore/doctype/`
- Service functions: cập nhật 10 → 22 functions (thêm transfer, GMDN, scheduler, KPI rollup)
- `transition_asset_status()` return type: sửa từ dict → None
- `services/inventory.py`: xóa section (file không tồn tại trong shared/)
- Import path ServiceError: sửa từ `assetcore.services.exceptions` → `assetcore.services.shared.errors`
- ErrorCode: sửa từ `AC-E001..E012` → string constants (`NOT_FOUND`, `FORBIDDEN`, ...)

**05_API_Specification.md:**
- `transition_asset_status` → `transition_status`
- `get_asset_lifecycle_history` → `get_asset_timeline`
- `search_assets_by_udi`, `get_assets_due_pm` → không tồn tại (removed)
- `get_sla_for` → `resolve_sla_policy`
- `list_audit_events` → `list_audit_trail`
- `get_audit_event` → `get_audit_entry`
- `verify_audit_chain` → `verify_chain`
- `create_capa` → `open_capa`
- `close_capa` → `close_capa_record`
- `list_departments_tree`, `list_locations_tree` → `list_departments`, `list_locations`
- Trigger endpoints: `trigger_check_*` → `trigger_*_check` pattern + GET (không phải POST)
- `update_asset`, `update_supplier`: PUT → POST
- Thêm 8 endpoint groups mới không có trong spec cũ
- `close_incident` → không tồn tại (removed)

**06_Frontend_Design.md:**
- Vue views: chỉ 2 views built (`ReferenceDataView.vue`, `SlaPolicyListView.vue`); sitemap labeled [BUILT]/[SPEC]
- Pinia stores: sửa từ pattern chung → 4 stores thực tế (`useAssetStore`, `useRefDataStore`, `useCapaStore`, `useIncidentStore`)
- API client: sửa từ object-style `imm00Api{}` → named exports; sửa endpoint names
- lifecycle_status colors: thêm đúng values (Commissioned, Calibrating, Under Maintenance)

**07_Testing_QA.md:**
- TC-S-003: `transition_asset_status` return → None (không phải dict); thêm verify downtime log
- TC-S-006: exception type → `frappe.exceptions.ValidationError` (không phải ServiceError)
- TC-S-009: CAPA signature → `due_days: int` (không phải `due_date: str`); xóa `linked_incident`

## Roadmap tiếp theo

- [ ] (Optional) Pentest report upload tại `docs/security/imm00-pentest.md`
- [ ] (Optional) Screenshot UI thực tế trên staging → đính kèm vào `09_Release.md §I`
- [ ] Build còn thiếu: các views [SPEC] trong sitemap

## Tham chiếu

- Template chuẩn: [`../template/`](../template/)
- Codebase ground truth (BE): `assetcore/services/imm00.py` · `assetcore/api/imm00.py` · `assetcore/services/shared/`
- Codebase ground truth (FE): `frontend/src/types/imm00.ts` · `frontend/src/api/imm00.ts` · `frontend/src/stores/imm00.ts`
- Source docs (cũ): `docs/architecture/archive/imm-00/`

---

*IMM-00 là foundation layer — deploy trước mọi module IMM-01→IMM-17.*
