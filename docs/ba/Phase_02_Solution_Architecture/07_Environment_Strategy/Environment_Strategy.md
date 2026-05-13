> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ENVIRONMENT STRATEGY — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + IT Lead

---

## 1. Mục tiêu
- 4 môi trường chính + 1 DR.
- Tách biệt rõ; cấm đụng PROD trực tiếp; mọi thay đổi đi qua promote pipeline.
- Anonymize dữ liệu khi đẩy về DEV/UAT.

## 2. Danh mục môi trường

| Môi trường | Mục đích | Ai sử dụng | Dữ liệu |
|-----------|---------|------------|---------|
| **DEV** | Phát triển | Dev, BA dev | Synthetic / anonymized snapshot |
| **UAT** | User Acceptance Test | Người dùng key, QA, BA | Anonymized snapshot từ PROD (refresh theo wave) |
| **STAGING** | Pre-production: rehearse cutover, perf test | DevOps, QA | Snapshot mới nhất của PROD (anonymized) |
| **PROD** | Vận hành thực | End user | Live |
| **DR** | Disaster recovery | Auto-failover | Replica của PROD |

(Optional) **TRAINING** — môi trường đào tạo, refresh từ UAT, dùng dữ liệu mẫu.

## 3. Topology mỗi môi trường

| Resource | DEV | UAT | STAGING | PROD | DR |
|----------|-----|-----|---------|------|----|
| App nodes | 1×4 vCPU/8 GB | 2×4 vCPU/8 GB | 2×8 vCPU/16 GB | 2×8 vCPU/16 GB | 2×8 vCPU/16 GB warm |
| DB | 1×4 vCPU/8 GB | 1×4 vCPU/16 GB | 1×8 vCPU/32 GB | Primary 1×8/32, Replica 1×8/32 | Replica của PROD |
| Redis | 1 node | 1 node | HA 2 node | HA 2 node | HA |
| File storage | local | local | MinIO single | MinIO HA | replica MinIO |
| Backup | – | – | có | đầy đủ | có |
| Monitoring | basic | basic | full | full | full |

## 4. Quy trình promote (CI/CD)

```
Dev branch ──► PR ──► review ──► merge to main
                                   │
                          ┌────────┴────────┐
                          ▼                 ▼
                    Build CI            Lint/Test
                          │
                          ▼
                Deploy to DEV (auto)
                          │
                          ▼
                Smoke test pass?
                          │
                          ▼
                Deploy to UAT (manual approval)
                          │
                          ▼
                Wave UAT pass + sign-off?
                          │
                          ▼
                Deploy to STAGING (manual)
                          │
                          ▼
                Cutover rehearsal pass?
                          │
                          ▼
                Deploy to PROD (CCB approval)
                          │
                          ▼
                Smoke test PROD + monitor
```

## 5. Branching strategy

- `main` — production-ready.
- `develop` — integration.
- `feature/<wave>-<module>-<short>` — feature branch.
- `hotfix/<ticket>` — fix urgent PROD.
- `release/<wave>-x.y.z` — chuẩn bị release.

Tag: `v<wave>.<minor>.<patch>` ví dụ `v1.0.0` Wave 1 GA.

## 6. Secret & config per env

- Dùng `.env` không commit.
- Secret store trong Vault (PROD/STAGING) hoặc Frappe encrypted (DEV/UAT).
- Tên config bắt buộc prefix theo môi trường: `ASSETCORE_PROD_*`, `ASSETCORE_UAT_*`…

## 7. Data refresh policy

- **DEV** refresh khi cần — synthetic dataset.
- **UAT** refresh đầu mỗi sprint UAT (≤ 1 lần/2 tuần) — anonymized snapshot PROD.
- **STAGING** refresh trước cutover rehearsal.
- **TRAINING** refresh trước session lớn.

### Anonymization rules
- User: thay name/email/phone bằng pattern test.
- File LEGAL/CALCERT: thay bằng PDF mẫu.
- Asset Code: giữ nguyên (cần để training).
- Lifecycle Event payload: scrub PHI/PII fields.
- Audit log: giữ nguyên cấu trúc, scrub user identity.

## 8. Backup & Restore

- PROD: full daily 02:00; binlog continuous.
- Lưu giữ: 30 ngày on-site + 90 ngày off-site cold.
- File storage: snapshot daily.
- Restore drill: quý.
- Định nghĩa "restore success": tạo môi trường temporary, load backup, smoke test pass.

## 9. Monitoring & Logging

| Loại | Hệ thống | DEV/UAT | STAGING | PROD/DR |
|------|----------|---------|---------|---------|
| Infra metrics | Prometheus + Grafana | basic | full | full |
| Log aggregation | ELK / Loki | basic | full | full |
| App error | Frappe error log → Slack | có | có | có |
| Synthetic monitoring | k6 | – | có | có |
| Real user monitoring | – | – | – | có |

## 10. Access & Approval per env

| Action | DEV | UAT | STAGING | PROD |
|--------|-----|-----|---------|------|
| Deploy | Dev tự | Manual approval | Manual approval | CCB |
| DB direct query | Dev (read) | Read by IT | Read by IT | Chỉ IT Lead khẩn cấp + audit |
| Restore backup | – | – | DevOps + Frappe Tech | DevOps + Frappe Tech + Trưởng CNTT |
| Add user | Dev | IT | IT | IT + ai cấp role tương ứng |
| Change config | Dev | DevOps | DevOps | CCB approval |

## 11. Patch management

- Frappe / ERPNext patch minor: kiểm thử STAGING ≥ 2 tuần trước PROD.
- Major version: phải có roadmap riêng + UAT đầy đủ.
- OS patch: tháng; security patch HIGH: 5 ngày; CRITICAL: 24h.

## 12. Disaster Recovery

- **DR site warm standby.**
- Replication: DB binlog ship + file storage async replication.
- DNS failover: quản lý qua DNS provider/IP swap.
- Drill: quý — tài liệu hóa runbook.

## 13. Tiêu chí nghiệm thu Environment
- 4 môi trường + DR sẵn sàng trước Phase 09.
- Pipeline CI/CD chạy được DEV→UAT→STAGING→PROD.
- Backup/restore drill thành công ≥ 1 lần.
- DR drill thành công ≥ 1 lần.
- Anonymization tool hoạt động khi refresh UAT.
