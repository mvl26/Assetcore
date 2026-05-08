> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DATA MIGRATION RUNBOOK — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** Migration Lead + IT Lead

---

## 1. Pre-conditions
- Env PROD ready + smoke test pass.
- Backup PROD đầy đủ (full + binlog).
- Validation report dry-run UAT pass.
- Sign-off Migration Lead + Asset Manager + QMS.
- Communication: thông báo BV về cửa sổ migration (≥ 7 ngày trước).

## 2. Migration window
- Cuối tuần (Saturday 22:00 → Sunday 06:00).
- Lock user write trong cửa sổ.

## 3. Steps

### Step 1: T-30 phút — Backup
```bash
# Full backup PROD
bench --site assetcore.prod backup --with-files
# Verify backup
ls -lh sites/assetcore.prod/private/backups/
# Off-site ship
/opt/scripts/ship-backup.sh
```

### Step 2: T-15 phút — Lock user write
- Bật `migration_mode=true` trong AC Settings (block submit user thường).
- Chỉ Migration team có quyền submit.

### Step 3: T0 — Master data import
```bash
# 1. Manufacturer
bench --site assetcore.prod execute assetcore.migration.import_batch --kwargs '{"sheet": "manufacturer.csv"}'
# 2. Location
... (theo migration order Phase_03/11)
```

### Step 4: T+30 phút — Item update
- Cập nhật flag `is_medical_device`, `risk_class`, `criticality`.

### Step 5: T+45 phút — Device Model
- Import.

### Step 6: T+60 phút — Supplier + Service Provider + Contract
- Import.

### Step 7: T+75 phút — Medical Asset (chính)
- Batch 500/lô.
- Verify success rate sau mỗi batch.

### Step 8: T+150 phút — Asset Identifier + Custodian
- Import.

### Step 9: T+170 phút — Document Records
- LEGAL, IQOQPQ, MANUAL, CALCERT.
- Upload file kèm.

### Step 10: T+220 phút — PM Plan + Calibration Plan
- Import.

### Step 11: T+240 phút — (Optional) WO history 24m
- Bulk insert.

### Step 12: T+300 phút — Disable migration mode
```bash
bench --site assetcore.prod execute assetcore.migration.disable_migration_mode
```

### Step 13: T+310 phút — DQ audit
```bash
bench --site assetcore.prod execute assetcore.migration.run_dq_audit
```

### Step 14: T+330 phút — Reconciliation MA ↔ ERPNext Asset
```bash
bench --site assetcore.prod execute assetcore.integration.recon_assets
```

### Step 15: T+350 phút — Smoke test
- Login Admin.
- Mở random 10 asset, verify field.
- Tạo PM Plan test.
- Sinh WO test.
- Mobile login + scan QR.

### Step 16: T+380 phút — Sign-off + bật user write
- Migration Lead + Asset Manager + QMS sign.
- Tắt `migration_mode`.
- Notify user toàn BV.

## 4. Rollback procedure (nếu cần)

```bash
# Step 1: Disable user write
# Step 2: Restore backup
bench --site assetcore.prod restore <backup-file>
# Step 3: Verify
# Step 4: Notify
```

## 5. Communication template

### Pre-migration (T-7 ngày)
```
Kính gửi toàn BV,
Hệ thống AssetCore sẽ migration cuối tuần [date].
Cửa sổ: 22:00 [Sat] → 06:00 [Sun].
Trong cửa sổ này, hệ thống KHÔNG cho phép user write.
Trân trọng.
```

### During migration
- Status updates mỗi 30 phút trong nhóm Steering.

### Post-migration
```
AssetCore migration đã hoàn tất.
[X] asset đã import.
[Y] document đã số hóa.
Hệ thống đã sẵn sàng.
```

## 6. Hypercare
- 4 tuần đầu sau migration.
- Daily DQ audit.
- Hotline support 24/7 cho 2 tuần đầu.

## 7. Tiêu chí nghiệm thu Migration Runbook
- Runbook test đầy đủ trên DEV + UAT.
- Backup + Rollback test pass.
- Sign-off matrix complete.
- Communication plan executed.
