> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DATA MIGRATION TEST PLAN — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QA Lead + Migration Lead

---

## 1. Mục tiêu
Bảo đảm migration legacy → AssetCore đạt sign-off (Phase_03/11).

## 2. Test phases

### 2.1 Pre-validate
- Chạy validator trên Excel template input.
- Kiểm tra schema columns, type, uniqueness, FK, allowed values, naming pattern, cross-sheet consistency.
- Output: `migration_validation_report.xlsx` (Errors / Warnings / Stats).
- **Pass criteria:** 0 error trong scope; warning ≤ 5%.

### 2.2 Dry-run DEV
- Import vào DEV (môi trường sạch hoặc reset trước).
- Chạy DQ rule audit toàn site sau import.
- Test scenario:
  - Tạo Asset từ legacy.
  - Verify business key uniqueness.
  - Tạo Document Record (LEGAL, CALCERT, MANUAL) gắn asset.
  - Sample 20 asset random → verify field-level chính xác.
  - Test scenario "tạo PM Plan + sinh WO" trên asset migration.
- Rollback test.

### 2.3 Dry-run UAT
- Anonymized snapshot từ DEV.
- Đại diện người dùng key (Asset Manager + QMS) review sample 50 asset.
- Sign-off baseline.

### 2.4 Production import
- Cửa sổ migration cuối tuần.
- Pre: backup PROD đầy đủ; lock user write.
- Run import qua tool chính thức.
- Post: chạy DQ audit; xử lý issue.
- Sign-off.

### 2.5 Post-go-live monitoring
- Monitor 4 tuần đầu adoption + DQ issue.
- Issue critical → patch import bổ sung.

## 3. Test cases chính

### TC-MIG-001 — Pre-validate
- Input: Excel với 1 row asset có asset_code không hợp lệ.
- Expected: validator báo error.

### TC-MIG-002 — FK integrity
- Input: asset trỏ đến facility không tồn tại.
- Expected: error.

### TC-MIG-003 — Uniqueness
- Input: 2 asset cùng asset_code.
- Expected: validator báo duplicate.

### TC-MIG-004 — Date format
- Input: commission_date sai format.
- Expected: warning, normalize hoặc reject.

### TC-MIG-005 — Bulk import 5k asset
- Expected: hoàn tất < 30 phút; success ≥ 95%.

### TC-MIG-006 — Document attachment migration
- Pre: 1k file PDF/Image.
- Expected: tất cả file upload + link đúng asset.

### TC-MIG-007 — Rollback
- Pre: import 1 batch 100 asset.
- Steps: trigger rollback batch.
- Expected: 100 asset xóa (nhưng Lifecycle Event "data_migration_batch_loaded" giữ).

### TC-MIG-008 — DQ audit post-import
- Steps: chạy cron audit DQ rule.
- Expected: identify issue; ≤ 5% record có warning; 0 critical issue trong scope.

### TC-MIG-009 — ERPNext Asset reconciliation
- Steps: chạy reconciliation cron.
- Expected: 0 lệch field critical (location, custodian).

### TC-MIG-010 — Production cutover
- Pre: backup taken.
- Steps: full import.
- Expected: complete trong cửa sổ; KPI dashboard có dữ liệu trong 4 tuần.

## 4. DQ check categories

- Uniqueness (asset_code, document_no).
- Completeness (mandatory fields).
- Validity (regex, allowed values).
- Referential integrity.
- Cross-sheet consistency.
- Migration flag (`imported_from_legacy=1` set).

## 5. Defect taxonomy

| Severity | Định nghĩa |
|----------|------------|
| Critical | Block import / mất dữ liệu / sai field critical |
| High | Tỉ lệ lỗi > 5% trên scope |
| Medium | Tỉ lệ lỗi 1-5% |
| Low | Cosmetic |

## 6. Tiêu chí Pass Migration Sign-off

- Pre-validate report sạch.
- Dry-run DEV pass.
- Dry-run UAT sign-off.
- Production import:
  - ≥ 95% asset Wave 1 in scope.
  - ≥ 90% LEGAL document số hóa.
  - ≥ 80% Device Model có manual.
  - ≥ 70% PM Plan / Cal Plan critical asset.
- DQ audit ≤ 5% warning, 0 critical.
- Reconciliation MA ↔ Asset 0 lệch.

## 7. Tools
- Custom migration tool (Python + Frappe API).
- Pre-validate spreadsheet macro.
- DQ audit cron.

## 8. Tiêu chí nghiệm thu
- 10+ TC migration tested.
- Sign-off matrix complete.
- Rollback drill thành công.
- Post-go-live monitoring 4 tuần trong scope.
