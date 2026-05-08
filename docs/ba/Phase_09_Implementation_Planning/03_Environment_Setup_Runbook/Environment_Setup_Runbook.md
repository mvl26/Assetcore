> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ENVIRONMENT SETUP RUNBOOK — ASSETCORE

**Phiên bản:** 1.0
**Owner:** DevOps + IT Lead

---

## 1. Components per environment

| Component | DEV | UAT | STAGING | PROD | DR |
|-----------|-----|-----|---------|------|----|
| Frappe + ERPNext + assetcore app | ✓ | ✓ | ✓ | ✓ | ✓ |
| MariaDB primary | ✓ | ✓ | ✓ | ✓ | ✓ |
| MariaDB replica | – | – | ✓ | ✓ | ✓ |
| Redis | single | single | HA | HA | HA |
| Nginx + Gunicorn | ✓ | ✓ | ✓ | ✓ | ✓ |
| File storage (MinIO) | local | local | single | HA | replica |
| Backup | – | – | ✓ | ✓ | ✓ |
| Monitoring (Prometheus + Grafana) | basic | basic | full | full | full |
| Log aggregation | basic | basic | full | full | full |
| WAF | – | – | ✓ | ✓ | ✓ |

## 2. Build steps (Linux Ubuntu 22.04 LTS)

### 2.1 Prereqs
```bash
sudo apt update
sudo apt install -y python3.11 python3-venv git curl mariadb-client redis-tools nginx
```

### 2.2 Bench setup
```bash
pip install frappe-bench
bench init --frappe-branch version-15 frappe-bench
cd frappe-bench
bench get-app erpnext --branch version-15
bench get-app assetcore <git-repo-url>
```

### 2.3 Site
```bash
bench new-site assetcore.<env>.local --mariadb-root-password ... --admin-password ...
bench --site assetcore.<env>.local install-app erpnext
bench --site assetcore.<env>.local install-app assetcore
```

### 2.4 Configure SSL
- Certbot Let's Encrypt cho UAT/STAGING/PROD.
- DR site dùng wildcard cert.

### 2.5 Production deployment
- Use `bench setup production` cho Nginx + Supervisor.
- Gunicorn workers: 4-8.
- Background workers: 2 default + 1 long.

### 2.6 MariaDB tuning (PROD)
```ini
[mysqld]
innodb_buffer_pool_size = 16G
innodb_log_file_size = 1G
max_connections = 500
slow_query_log = 1
slow_query_log_file = /var/log/mariadb/slow.log
long_query_time = 0.1
```

### 2.7 Redis HA (PROD)
- Sentinel 3 nodes.
- Frappe config sentinel cluster.

### 2.8 MinIO HA
- 4 nodes erasure coding.
- Object lock on buckets `qms-critical`, `audit-trail`.

### 2.9 Backup
```bash
# Daily
0 2 * * * bench --site all backup --with-files
# Ship to off-site
0 3 * * * /opt/scripts/ship-backup.sh
```

### 2.10 Monitoring
- node_exporter + mysqld_exporter + redis_exporter.
- Frappe custom metric exporter.
- Grafana dashboards.

### 2.11 Log
- Promtail → Loki (hoặc Fluentd → ELK).
- Frappe error log + bench logs.

### 2.12 WAF (PROD/STAGING)
- Nginx + ModSecurity + OWASP Core Rule Set.

## 3. Network setup
- DMZ: Nginx + WAF.
- App VLAN: Frappe app servers.
- DB VLAN: MariaDB.
- Backup VLAN: tách riêng.
- VPN: vendor SE.
- Egress: whitelist domain.

## 4. Account setup
- bench user: deploy automation.
- IT Lead: admin Linux.
- DBA: read replica + binlog.
- DevOps: pipeline only.

## 5. Smoke test
- `curl https://assetcore.<env>/api/method/ping`.
- Login admin → home.
- Create test asset.
- Run test cron.
- Verify backup.
- Verify monitoring metrics.

## 6. Tiêu chí nghiệm thu Env Setup
- 4 môi trường + DR ready.
- SSL valid.
- Backup tested + restored.
- Monitoring + alert hoạt động.
- WAF rules tested.
