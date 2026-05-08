> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# FIELD / VALIDATION / NAMING INDEX — WAVE 1

**Tham chiếu:**
- Naming Convention: Phase_00/07.
- Data Dictionary: Phase_03/08.
- DQ Rules: Phase_03/10.
- Business Rules: Phase_01/07.

---

## 1. Field naming convention (recap)
- Snake_case.
- Boolean: `is_*` / `has_*` / `requires_*`.
- Date: `*_date`.
- Datetime: `*_at`.
- FK link: `<entity>` (ví dụ `medical_asset`, `device_model`).
- Computed: `auto_*`.
- Migration: `imported_from_legacy`, `legacy_ref`.

## 2. Common validation hooks pattern

### 2.1 `before_save`
- Validate naming pattern.
- Validate FK existence.
- Validate criticality + risk_class consistency.
- Compute auto fields.

### 2.2 `before_submit`
- Validate state transition allowed.
- Validate required documents (DI-1 cho release_for_use).
- Validate validator ≠ executor.
- Trigger e-signature.

### 2.3 `on_submit`
- Publish Lifecycle Event.
- Sync ERPNext (if applicable).
- Trigger notification.

### 2.4 `on_cancel`
- Block if state ≥ commissioned (cho MA).
- Block if any linked record locks cancellation.

## 3. Validation rules samples (linkage to BR)

### AC Medical Asset
- BR-001: asset_code unique + regex.
- BR-002: 1 device_model.
- BR-005: release_for_use điều kiện.
- BR-008: asset_code immutable post-commission.

### AC Document Record
- BR-011: LEGAL/CALCERT có expiry.
- BR-012: auto-expire cron.
- BR-013: block release_for_use khi license expired.

### AC PM Plan
- BR-021: plan gắn 1 asset hoặc filter.
- BR-022: frequency tối thiểu 1/năm.

### AC Work Order
- BR-024: ≥ 1 task.
- BR-025: WO PM closed → cập nhật next_pm_due.
- BR-033: root_cause khi severity High.
- BR-081: Validator ≠ Executor.

### AC CAPA
- BR-051: NC sev1 → CAPA trong 24h.
- BR-053: effectiveness fail → reopen.
- BR-057: ≥ 1 source.

## 4. Naming series (recap)

| DocType | Series |
|---------|--------|
| AC Medical Asset | `MA-.YYYY.-.####` |
| AC Work Order | `WO-.YYYY.-.######` |
| AC Failure Report | `FR-.YYYY.-.######` |
| AC PM Plan | `PMP-.YYYY.-.####` |
| AC Calibration Plan | `CPL-.YYYY.-.####` |
| AC Calibration Record | `CAL-.YYYY.-.######` |
| AC Document Record | `DOC-.YYYY.-.######` |
| AC QMS Artifact | `QMS-<TIER>-.YYYY.-.####` |
| AC CAPA | `CAPA-.YYYY.-.####` |
| AC Compliance Case | `CMP-.YYYY.-.####` |
| AC Lifecycle Event | `LCE-.YYYY.-.########` |
| AC Risk Entry | `RSK-.YYYY.-.####` |
| AC Change Control | `CR-.YYYY.-.####` |
| AC Asset Movement | `MOV-.YYYY.-.####` |
| AC Stand-Down | `SD-.YYYY.-.####` |
| AC Decommission | `DEC-.YYYY.-.####` |
| AC Disposal | `DIS-.YYYY.-.####` |

## 5. Audit fields chuẩn

Mỗi DocType chính có:
- `created_by`, `created_at` (Frappe `owner`/`creation`).
- `modified_by`, `modified_at`.
- `docstatus` (cho submittable).
- `imported_from_legacy`, `legacy_ref` (nơi áp dụng).
- `correlation_id` (event-driven).

## 6. File attachment policy

- Frappe File mặc định cho file thường.
- File QMS-critical (LEGAL, CALCERT, IQOQPQ, CAPA evidence): bucket immutable WORM.
- Hash SHA-256 lưu trên Document Record để verify integrity.
- Anti-virus scan trước khi accept upload.

## 7. Tiêu chí nghiệm thu
- 100% field Wave 1 validate.
- Naming series test no collision.
- Linter custom kiểm naming convention.
- Hooks chuẩn áp dụng đúng.
