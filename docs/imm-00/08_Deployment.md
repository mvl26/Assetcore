# 08 — Deployment — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — phải deploy trước tất cả module khác |
| Owner | DevOps / IMM System Admin |
| Liên kết | [07 Testing & QA](./07_Testing_QA.md) · [09 Release](./09_Release.md) |
| Nguồn tham chiếu | `docs/imm-00/IMM-00_Setup_Guide.md` (Setup Guide đầy đủ) |
| Phiên bản | 1.0.0 |
| Trạng thái | **Planned** |

---

# Phần I — Foundation Deployment Order

## I.1. Nguyên tắc quan trọng

> **IMM-00 PHẢI được deploy và migrate thành công TRƯỚC KHI install bất kỳ module IMM-xx nào.**

Thứ tự bắt buộc:

```
1. Frappe Framework v15 site
2. Install AssetCore app
3. bench migrate  ← tạo tất cả IMM-00 DocTypes + fixtures
4. Seed SLA policies + sample device models
5. Cấu hình scheduler + email
6. Verify smoke test (S-01 → S-13)
7. → Deploy IMM-04 (Installation)
8. → Deploy IMM-05 (Registration)
9. → Deploy IMM-08 (PM)
10. → Deploy IMM-09 (Repair)
11. → Deploy IMM-11 (Calibration)
12. → Deploy IMM-12 (Corrective)
```

Module IMM-xx KHÔNG thể hoạt động nếu IMM-00 chưa sẵn sàng:
- `transition_asset_status()` chưa tồn tại → IMM-09 không tạo được Work Order
- `get_sla_policy()` chưa có data → IMM-08 không tính được SLA
- AC Asset chưa có record → mọi module đều không có dữ liệu để xử lý

## I.2. Kiến trúc deploy

```
┌──────────────────────────────────────────────────────────────┐
│  Server (Ubuntu 22.04 LTS)                                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Nginx (reverse proxy + HTTPS)                         │  │
│  └────────────────────────────┬───────────────────────────┘  │
│                               │                              │
│  ┌────────────────────────────▼───────────────────────────┐  │
│  │  Frappe Bench                                          │  │
│  │  ├─ gunicorn (web workers × 2-4)                       │  │
│  │  ├─ frappe-worker (background queue)                   │  │
│  │  ├─ frappe-schedule (daily scheduler jobs)             │  │
│  │  └─ frappe-socketio (realtime)                         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌───────────┐  ┌───────────────────────┐  │
│  │  MariaDB 10.6│  │  Redis 6  │  │  Node.js 18 (FE build)│  │
│  └──────────────┘  └───────────┘  └───────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

# Phần II — Environment Configuration

## II.1. Yêu cầu hệ thống

| Thành phần | Version | Ghi chú |
|---|---|---|
| OS | Ubuntu 22.04 LTS / Debian 12 | Khuyến nghị LTS |
| Python | 3.10+ | Frappe v15 yêu cầu |
| MariaDB | 10.6+ | hoặc MySQL 8.0+ |
| Redis | 6.0+ | Queue + cache + socketio |
| Node.js | 18.x LTS | FE Vite build |
| pnpm | 8+ | FE package manager |
| Bench CLI | Frappe v15 compat | `pip install frappe-bench` |
| Frappe Framework | **v15+** | **Dependency DUY NHẤT** (không cần ERPNext) |

**RAM khuyến nghị:** 8GB minimum (production), 4GB (staging/dev).

## II.2. Site Config — `site_config.json`

```json
{
  "db_name": "_<site_hash>",
  "db_password": "<db_pw>",
  "encryption_key": "<32-byte-base64>",
  "session_expiry": "06:00:00",
  "developer_mode": 0,
  "mail_server": "smtp.example.vn",
  "mail_port": 587,
  "use_tls": 1,
  "mail_login": "noreply@hospital.vn",
  "mail_password": "<app-password>",
  "allow_cors": "https://assetcore.hospital.vn"
}
```

> Dev only: `"allow_cors": "*"` — không dùng production.

## II.3. Common Site Config — `common_site_config.json`

```json
{
  "bench_id": "frappe-bench",
  "webserver_port": 8000,
  "socketio_port": 9000,
  "redis_cache": "redis://localhost:13000",
  "redis_queue": "redis://localhost:11000",
  "redis_socketio": "redis://localhost:12000",
  "restart_supervisor_on_update": true,
  "serve_default_site": true,
  "rate_limit": {
    "window": 60,
    "limit": 300
  }
}
```

## II.4. Frontend Environment — `frontend/.env`

```env
VITE_API_BASE=https://assetcore.hospital.vn
VITE_APP_NAME=AssetCore
VITE_API_PREFIX=/api/method/assetcore
VITE_SENTRY_DSN=<sentry-dsn>
```

---

# Phần III — Migration Patches

## III.1. Patch Registry — `assetcore/patches.txt`

```
assetcore.patches.v3_0.001_migrate_from_v2
assetcore.patches.v3_2.001_add_gmdn_status_field
assetcore.patches.v3_2.002_add_inventory_doctypes
assetcore.patches.v4_0.001_add_inventory_tables
```

## III.2. Patch: `v3_0/001_migrate_from_v2`

**Mục đích:** Migrate data từ AssetCore v2 (ERPNext sidecar) sang v3 native DocTypes.

**Actions:**
1. Kiểm tra `frappe.db.table_exists("IMM Asset Profile")` — nếu không có, skip.
2. Copy `IMM Asset Profile` → `AC Asset` (field mapping FIELDS_V2_TO_V3_ASSET).
3. Copy `IMM Vendor Profile` → `AC Supplier`.
4. Copy `IMM Location Ext` → `AC Location`.
5. Drop 3 bảng sidecar: `tabIMM Asset Profile`, `tabIMM Vendor Profile`, `tabIMM Location Ext`.
6. Xóa 16 Custom Fields `custom_imm_*` trên `tabAsset` ERPNext.

**Rollback:** Restore từ backup trước khi chạy patch.

**Estimated time:** 5–30 phút tùy số lượng record.

## III.3. Patch: `v3_2/001_add_gmdn_status_field`

**Mục đích:** Thêm field `gmdn_status` và `gmdn_status_reason` vào `tabAC Asset`.

```python
# assetcore/patches/v3_2/001_add_gmdn_status_field.py
def execute():
    if not frappe.db.has_column("AC Asset", "gmdn_status"):
        frappe.db.sql("""
            ALTER TABLE `tabAC Asset`
            ADD COLUMN `gmdn_status` varchar(50) DEFAULT 'Không sử dụng'
        """)
    frappe.db.commit()
```

**Default:** `Không sử dụng` cho tất cả existing records.

## III.4. Patch: `v4_0/001_add_inventory_tables`

**Mục đích:** Tạo 5 bảng Inventory sub-domain mới (v4 expansion).

```python
# Tạo bảng cho: AC Warehouse, AC Spare Part, AC Spare Part Stock,
# AC Stock Movement, AC Stock Movement Item
def execute():
    # Frappe sẽ tự tạo bảng khi migrate nếu DocType JSON đã tồn tại
    # Patch này chỉ đảm bảo indexes được tạo đúng
    frappe.db.sql("""
        ALTER TABLE `tabAC Spare Part Stock`
        ADD UNIQUE KEY `unique_warehouse_part` (`warehouse`, `spare_part`)
    """, ignore_ddl=True)
    frappe.db.commit()
```

## III.5. Chạy migrate

```bash
# Fresh install hoặc sau khi update app
bench --site <site> migrate

# Theo dõi log
tail -f sites/<site>/logs/worker.log
```

## III.6. Verify sau migration

```bash
# Kiểm tra bảng AC đã tồn tại
bench --site <site> mariadb --execute "SHOW TABLES LIKE 'tabAC%';"
# Mong đợi: tabAC Asset, tabAC Asset Category, tabAC Department, tabAC Location, tabAC Supplier
# + tabAC Warehouse, tabAC Spare Part, tabAC Spare Part Stock, tabAC Stock Movement

# Kiểm tra bảng IMM đã tồn tại
bench --site <site> mariadb --execute "SHOW TABLES LIKE 'tabIMM%';"
# Mong đợi: tabIMM Audit Trail, tabIMM CAPA Record, tabIMM Device Model, ...

# Kiểm tra v2 sidecar đã bị drop
bench --site <site> mariadb --execute "SHOW TABLES LIKE 'tabIMM Asset Profile';"
# Mong đợi: empty

# Count sanity check
bench --site <site> console <<'PY'
import frappe
print("Roles:", frappe.db.count("Role", {"name": ["like", "IMM%"]}))
print("SLA Policies:", frappe.db.count("IMM SLA Policy"))
PY
```

---

# Phần IV — QMS Mapping & Compliance

## IV.1. Cross-cutting Compliance Controls

| IMM-00 Feature | ISO 13485 | NĐ 98/2021 | WHO HTM |
|---|---|---|---|
| IMM Audit Trail (SHA-256 chain) | §7.5.9 — Hồ sơ chất lượng bất biến | Điều 4 khoản 1 — Truy xuất nguồn gốc | §3.2 — Traceability toàn lifecycle |
| Asset Lifecycle Event (append-only) | §7.5.9 — Lịch sử thiết bị đầy đủ | Điều 28 — Hồ sơ thiết bị ≥ 5 năm | §5.4 — Lifecycle tracking |
| IMM CAPA Record | §8.5.2, §8.5.3 — CAPA mandatory | — | §8.3 — Continuous improvement |
| validate_asset_for_operations() | §7.5.4 — Control of monitoring equipment | Điều 31 — Không dùng thiết bị không đạt | §5.3 — Equipment safety |
| check_registration_expiry() scheduler | — | Điều 5 — Đăng ký lưu hành BYT hợp lệ | — |
| check_vendor_contract_expiry() scheduler | §7.4.1 — Supplier evaluation | — | §6.2 — Service contract management |
| Permission Query (Technician scoped) | §6.2.1 — Competence, awareness | — | §4.3 — Role-based access |
| IMM SLA Policy | — | — | §5.4.2 — Response time standards |
| Incident Report + BYT reporting | — | Điều 27 — Báo cáo sự cố | §7.3 — Incident reporting |
| GMDN Status tracking | — | Điều 4 — Quản lý GMDN | — |

## IV.2. Audit Trail Retention Policy

| Record | Retention | Lý do | Archive |
|---|---|---|---|
| IMM Audit Trail | ≥ 7 năm | NĐ 98/2021 Điều 28; ISO 13485 §4.2.4 | Không archive — giữ trong DB |
| Asset Lifecycle Event | ≥ 7 năm | WHO HTM lifecycle requirement | Không archive |
| IMM CAPA Record | ≥ 7 năm | ISO 13485 §8.5.3 | Không archive |
| Incident Report | ≥ 7 năm | NĐ 98/2021; WHO HTM §7.3 | Không archive |
| AC Asset | Permanent (sau Decommission giữ 7 năm) | Lý lịch thiết bị | — |

> **Không được phép xóa** bất kỳ record nào trong danh sách trên qua application layer. Đảm bảo bằng: DocType perm không có Delete + controller block.

## IV.3. Backup Strategy

| Loại backup | Tần suất | Retention | Storage |
|---|---|---|---|
| Full DB backup | Daily 02:00 | 30 ngày local, 90 ngày offsite | S3 / NAS bệnh viện |
| Binary log (binlog) | Hourly | 7 ngày | Local |
| File backup (attachments) | Daily | 30 ngày | S3 |

```bash
# Cron daily backup
0 2 * * * cd /home/frappe/frappe-bench && bench --site <site> backup --with-files --compress
0 3 * * * find sites/<site>/private/backups -mtime +30 -delete

# Offsite sync
0 4 * * * rsync -av sites/<site>/private/backups/ user@backup-server:/backups/<site>/$(date +%F)/
```

RPO ≤ 1h, RTO ≤ 4h (theo NFR-00-06).

## IV.4. Production Hardening Checklist

- [ ] `developer_mode = 0`
- [ ] `session_expiry = "06:00:00"` (6 giờ)
- [ ] `allow_cors` set đúng origin FE (không `"*"`)
- [ ] HTTPS enforced: `sudo bench setup lets-encrypt <site>`
- [ ] `encryption_key` đủ mạnh: `openssl rand -base64 32`
- [ ] Rate limit cấu hình trong `common_site_config.json`
- [ ] Scheduler enabled: `bench --site <site> enable-scheduler`
- [ ] Email SMTP configured và verified
- [ ] Supervisor + Nginx production mode: `bench setup supervisor && bench setup production frappe`
- [ ] Log rotation configured (`/etc/logrotate.d/frappe`)
- [ ] MariaDB `innodb_buffer_pool_size` = 50–60% RAM
- [ ] Redis `appendonly yes` (persistence cho queue)

---

# Phần V — Rollback Plan

## V.1. Rollback DB

```bash
# Liệt kê backup mới nhất
ls -lht sites/<site>/private/backups/ | head -5

# Restore DB + files
bench --site <site> restore \
  sites/<site>/private/backups/<timestamp>-database.sql.gz \
  --with-public-files sites/<site>/private/backups/<timestamp>-files.tar \
  --with-private-files sites/<site>/private/backups/<timestamp>-private-files.tar
```

## V.2. Rollback code

```bash
cd apps/assetcore
git fetch --tags
git checkout v2.3.0   # tag v2 ổn định gần nhất

cd ~/frappe-bench
bench --site <site> migrate
bench restart
```

## V.3. Verify post-rollback

- [ ] Login web thành công
- [ ] Scheduler chạy lại
- [ ] Smoke test S-01 → S-05 pass

## V.4. RCA template (sau mỗi rollback)

```markdown
# Incident: Rollback IMM-00 migration YYYY-MM-DD
- Trigger: <trigger>
- Root cause: <rca>
- Corrective: <fix>
- Preventive: <preventive>
- Tracked in CAPA: CAPA-YYYY-XXXXX
```

---

## DoD — File 08 hoàn chỉnh

### I. Foundation deployment order
- [x] IMM-00 phải deploy trước tất cả IMM-xx
- [x] Thứ tự deploy rõ ràng (10 bước)
- [x] Architecture diagram

### II. Environment config
- [x] System requirements (Frappe only)
- [x] site_config.json
- [x] common_site_config.json
- [x] Frontend .env

### III. Migration patches
- [x] Patch registry (patches.txt)
- [x] v3_0: migrate from v2 sidecar
- [x] v3_2: add gmdn_status field
- [x] v4_0: add inventory tables
- [x] Verify commands

### IV. QMS Mapping
- [x] Compliance cross-reference (ISO 13485 × NĐ98 × WHO HTM)
- [x] Audit Trail retention policy (7 năm)
- [x] Backup strategy (RPO ≤ 1h, RTO ≤ 4h)
- [x] Production hardening checklist

### V. Rollback plan
- [x] DB rollback command
- [x] Code rollback command
- [x] Verify post-rollback
- [x] RCA template
