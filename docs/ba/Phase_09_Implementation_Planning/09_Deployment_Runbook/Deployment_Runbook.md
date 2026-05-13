> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DEPLOYMENT RUNBOOK — ASSETCORE

**Phiên bản:** 1.0
**Owner:** DevOps + Tech Lead

---

## 1. Mục tiêu
Quy trình deploy code AssetCore từ DEV → UAT → STAGING → PROD; rollback rõ ràng; checklist từng bước.

## 2. Pre-deployment checklist

- [ ] PR merged và tag `v<wave>.<minor>.<patch>` trên `main`.
- [ ] CI pipeline pass.
- [ ] Release notes (CHANGELOG) updated.
- [ ] Migration scripts versioned.
- [ ] DB schema changes reviewed.
- [ ] Approval CCB (cho PROD).
- [ ] Backup taken (cho PROD).

## 3. Deploy DEV (auto)

```bash
# Trigger by push to develop
ssh dev-frappe
cd ~/frappe-bench
bench update --pull --no-backup
# Run migrations
bench --site assetcore.dev.local migrate
# Restart
bench restart
# Smoke test
curl https://assetcore.dev/api/method/ping
```

## 4. Deploy UAT (manual approval)

```bash
ssh uat-frappe
cd ~/frappe-bench
git fetch
git checkout v<tag>
bench update --pull --no-backup
bench --site assetcore.uat.local migrate
bench restart
# Smoke test + UAT participant verify
```

## 5. Deploy STAGING

```bash
ssh staging-frappe
# Refresh from PROD anonymized snapshot
bench --site assetcore.staging.local restore <snapshot-anon>
git checkout v<tag>
bench update --pull --no-backup
bench --site assetcore.staging.local migrate
bench restart
# Cutover rehearsal: chạy đầy đủ migration runbook trên staging
```

## 6. Deploy PROD

```bash
# 1. Backup
bench --site assetcore.prod backup --with-files
# 2. Notify + lock user
echo "Cutover window starting" | notify-team.sh
bench --site assetcore.prod set-config maintenance_mode 1
# 3. Pull code
git checkout v<tag>
bench update --pull --no-backup
# 4. Migrate
bench --site assetcore.prod migrate
# 5. Restart
bench restart
# 6. Smoke test
/opt/scripts/smoke-test.sh assetcore.prod
# 7. Unlock
bench --site assetcore.prod set-config maintenance_mode 0
# 8. Notify success
```

## 7. Smoke test script

```bash
# /opt/scripts/smoke-test.sh
# 1. Ping
curl -f https://assetcore.prod/api/method/ping
# 2. Login as admin
# 3. Create test asset (with cleanup)
# 4. Submit FR test → verify WO created
# 5. Run cron PM scheduler with test data
# 6. Verify Lifecycle Event publishes
# 7. Verify Dashboard widget renders
echo "Smoke test passed"
```

## 8. Rollback PROD

```bash
# 1. Notify rollback
# 2. Stop background workers
bench stop
# 3. Restore backup
bench --site assetcore.prod restore <pre-deploy-backup>
# 4. Checkout previous tag
git checkout v<previous-tag>
bench update --pull --no-backup
# 5. Migrate (reverse if needed)
bench --site assetcore.prod migrate
# 6. Restart + smoke test
bench restart
/opt/scripts/smoke-test.sh
# 7. Notify rollback complete
```

## 9. Post-deployment monitoring

- Watch Frappe error log 1h.
- Watch dashboard health (queue depth, slow queries).
- Verify backup tonight.

## 10. Hotfix flow

```bash
# 1. Branch hotfix/<ticket> từ main
# 2. Fix + test
# 3. PR fast-track review
# 4. Tag patch version
# 5. Deploy direct STAGING + smoke
# 6. Deploy PROD với CCB approval
# 7. Cherry-pick to develop
```

## 11. Tiêu chí nghiệm thu Deployment Runbook
- Runbook test trên DEV/UAT/STAGING ≥ 1 lần thành công.
- Rollback drill trên STAGING.
- Smoke test scripts working.
- Backup + restore verified.
- CCB approval flow tested.
