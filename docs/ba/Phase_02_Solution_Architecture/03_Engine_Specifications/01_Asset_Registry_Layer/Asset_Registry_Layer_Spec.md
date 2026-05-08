> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ASSET REGISTRY LAYER — ENGINE SPEC

**Phiên bản:** 1.0
**Owner:** SA Lead + BA Lead
**Wave:** 1

---

## 1. Mục tiêu
Là **System of Record** ở tầng HTM cho mọi thiết bị y tế: định danh duy nhất, quan hệ với device model + location + custodian + risk + warranty + replacement signal; là nguồn gốc cho mọi engine khác.

## 2. Phạm vi
- Master & instance: `AC Medical Asset`, `AC Device Model`, `AC Asset Identifier`, `AC Location` (Facility/Building/Department/Room), `AC Custodian Assignment`.
- Đồng bộ với ERPNext `Asset` cho hạch toán.

## 3. DocType chính

### 3.1 AC Medical Asset
**Mục đích:** 1 record/instance thiết bị.

**Trường chính (Phase 03 sẽ chi tiết):**
| Field | Type | Mô tả |
|-------|------|-------|
| asset_code | Data unique | Mã định danh BV |
| device_model | Link AC Device Model | Catalog model |
| serial_no | Data | Serial từ vendor |
| manufacturer_serial | Data | – |
| facility / building / department / room | Link AC Location | – |
| custodian_user | Link User | – |
| owner_department | Link Department | – |
| criticality | Select A/B/C/D | – |
| risk_class | Select 1/2a/2b/3 | Theo phân loại TBYT VN |
| commission_date | Date | – |
| released_for_use_at | Datetime | – |
| state | Select | draft/installed/commissioned/released_for_use/stand_down/retired/disposed |
| erpnext_asset | Link ERPNext Asset | Liên kết tài chính |
| warranty_expiry | Date | – |
| replacement_signal | Select OK/Watch/Replace | Tự tính theo policy |
| qr_url | Data | – |
| rfid_epc | Data | – |
| last_pm_date / next_pm_due | Date | – |
| last_calibration_date / next_calibration_due | Date | – |
| pm_compliance | Check | Tính từ policy |
| imported_from_legacy | Check | Migration flag |
| legacy_ref | Data | – |

### 3.2 AC Device Model
**Mục đích:** Catalog model + đặc tả kỹ thuật + chính sách PM/Cal mặc định.

| Field | Type | Mô tả |
|-------|------|-------|
| model_code | Data unique | – |
| manufacturer | Link AC Manufacturer | – |
| item_template | Link Item (ERPNext) | – |
| risk_class | Select | – |
| default_pm_frequency | Select | Mặc định cho PM Plan |
| default_calibration_frequency | Select | – |
| operating_manual | Link Document Record | – |
| service_manual | Link Document Record | – |
| spare_parts_template | Table (Spare BOM) | – |

### 3.3 AC Asset Identifier
**Mục đích:** Hỗ trợ nhiều identifier cho 1 asset (mã BV, serial vendor, RFID, QR, asset tag in-house).

| Field | Type |
|-------|------|
| medical_asset | Link AC Medical Asset |
| identifier_type | Select QR/RFID/Asset Tag/Barcode/Other |
| identifier_value | Data |
| issued_at | Datetime |
| valid_until | Datetime |
| state | Active/Reissued/Lost |

### 3.4 AC Location (Facility/Building/Department/Room)
- DocType phân cấp parent-child (Frappe Tree).
- Field: location_type, parent_location, code, capacity, is_active.

### 3.5 AC Custodian Assignment
- Track lịch sử người trông giữ asset.
- Field: medical_asset, custodian_user, from_at, to_at, assigned_by, reason.

## 4. Quan hệ (đơn giản hóa)

```
ERPNext Item ◄────template── AC Device Model ────uses──► AC Manufacturer
                                   │
                                   ▼
                         AC Medical Asset ─── linked ──► ERPNext Asset
                          │       │      │
                          │       │      └── AC Asset Identifier (1..n)
                          │       │
                          │       └── AC Custodian Assignment (1..n)
                          │
                          └── AC Location (Facility/Building/Department/Room)
```

## 5. State Machine MA (cốt lõi)

```
draft ──► installed ──► commissioned ──► released_for_use ──► stand_down ──► retired ──► disposed
                                                  │                  │
                                                  └─►─ recalled  ────┘
```

State `recalled` là cờ song song chứ không thay thế các state vận hành; xử lý qua Compliance Case.

## 6. Public API (whitelisted)
- `assetcore.asset_registry.create_asset(data)`
- `assetcore.asset_registry.transition_state(asset_code, new_state, reason, evidence_refs)`
- `assetcore.asset_registry.get_asset_full_profile(asset_code)` — trả về asset + identifier + custodian hiện tại + license effective + plans + due dates.
- `assetcore.asset_registry.batch_import(payload)` — for migration.

## 7. Hooks
- `before_save AC Medical Asset`: validate naming, FK, criticality consistency.
- `on_submit AC Medical Asset (state=installed)`: publish `LE-03 installed`.
- `on_state_change`: publish Lifecycle Event tương ứng.
- `before_cancel`: chặn nếu state ≥ commissioned.
- `on_update`: đồng bộ field có liên quan sang ERPNext Asset (location, custodian) qua background job.

## 8. Index & Performance
- Unique index: `asset_code`, `(serial_no, device_model)`.
- Composite index: `(facility, department, state)` cho list view.
- Cache device_model + location hierarchy ở Redis.

## 9. Migration support
- Template Excel: 1 sheet/asset_class với cột chuẩn.
- Validation pre-import (DQ rules Phase 03).
- Import qua background job + transaction log.
- Mỗi batch sinh `LE-63 data_migration_batch_loaded`.

## 10. Tiêu chí nghiệm thu (Wave 1)
- 100% asset được migration + validation pass.
- 100% asset có ít nhất 1 Asset Identifier active.
- State machine vận hành đúng theo BR-001..008.
- Truy vấn full profile < 500ms cho 95th percentile.
