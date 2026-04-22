# IMM-00 — Setup Guide (v3)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-00 Foundation |
| Phiên bản | 3.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Đối tượng | IMM System Admin / IT Admin bệnh viện / DevOps |
| Trạng thái | **DRAFT** — Kiến trúc tự chứa, không phụ thuộc ERPNext |

---

## 0. Tổng quan thay đổi so với v2

| Hạng mục | v2 (cũ) | v3 (mới) |
|---|---|---|
| Nền tảng | ERPNext v15 bắt buộc | **Chỉ cần Frappe v15** |
| Cấu trúc dữ liệu | IMM Asset Profile + Custom Fields trên `tabAsset` | **13 DocType tự chứa** (prefix `AC` + `IMM`) |
| Sidecar DocTypes | IMM Asset Profile, IMM Vendor Profile, IMM Location Ext | **Bỏ hết** — HTM fields là first-class trên `AC Asset` |
| Custom Fields trên tabAsset | 16 cột `custom_imm_*` | **Bỏ hết** |
| Scheduler | 5 jobs (có `sync_asset_profile_status`) | 4 jobs (bỏ sync) |

Guide này áp dụng cho hai kịch bản:

1. **Fresh install** (site mới, chưa có data v2).
2. **Migration** (site `miyano` đã có data v2 cần nâng cấp).

---

## 1. Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu | Ghi chú |
|---|---|---|
| OS | Ubuntu 22.04 / Debian 12 | Khuyến nghị LTS |
| Python | 3.10+ | Frappe v15 yêu cầu |
| MariaDB | 10.6+ | Hoặc MySQL 8.0+ |
| Redis | 6.0+ | Queue + cache + socketio |
| Node.js | 18.x | Cho FE build (Vite) |
| Yarn | 1.22+ | Frappe asset build |
| pnpm | 8+ | Cho FE AssetCore (Vue 3 + Vite) |
| Bench CLI | Frappe v15 compatible | `pip install frappe-bench` |
| Frappe Framework | **v15+** | Dependency DUY NHẤT |

**Lưu ý:** KHÔNG cần install ERPNext. AssetCore v3 là app tự chứa.

Kiểm tra nhanh:

```bash
python3 --version           # >= 3.10
mariadb --version           # >= 10.6
redis-cli --version         # >= 6.0
node --version              # >= 18
bench --version             # Frappe v15
```

---

## 2. Cài đặt AssetCore — Fresh site (chưa có v2)

### 2.1 Tạo site mới

```bash
cd ~/frappe-bench

# Tạo site (KHÔNG install ERPNext)
bench new-site assetcore.local \
  --mariadb-root-password <root-pw> \
  --admin-password <admin-pw> \
  --no-mariadb-socket
```

### 2.2 Get app AssetCore

```bash
bench get-app https://github.com/<org>/assetcore.git --branch master
```

### 2.3 Install app lên site

```bash
bench --site assetcore.local install-app assetcore
bench --site assetcore.local migrate
```

### 2.4 Verify schema

```bash
bench --site assetcore.local mariadb --execute "SHOW TABLES LIKE 'tabAC%';"
```

Kết quả đúng (5 bảng core):

```
tabAC Asset
tabAC Asset Category
tabAC Department
tabAC Location
tabAC Supplier
```

```bash
bench --site assetcore.local mariadb --execute "SHOW TABLES LIKE 'tabIMM%';"
```

Kết quả đúng (6 bảng governance + 2 child):

```
tabIMM Audit Trail
tabIMM CAPA Record
tabIMM Device Model
tabIMM Device Spare Part
tabIMM SLA Policy
tabAsset Lifecycle Event
tabIncident Report
tabAC Authorized Technician
```

### 2.5 Bỏ qua sang §4 — Load fixtures

---

## 3. Migration từ v2 (site `miyano` đã có data sidecar cũ)

Áp dụng cho site đã chạy AssetCore v2 (có `IMM Asset Profile`, `IMM Vendor Profile`, `IMM Location Ext`, 16 custom fields trên `tabAsset`).

### 3.1 Pre-flight checklist

- [ ] Đang ở branch release v3 (`git log --oneline -1` phải trỏ đúng tag `v3.0.0`).
- [ ] Có quyền sudo trên server.
- [ ] Không có user đang thao tác trên site (nên set maintenance mode).
- [ ] Đã thông báo downtime window cho stakeholder.

### 3.2 Backup toàn bộ site

```bash
cd ~/frappe-bench

# Backup DB + files + config
bench --site miyano backup --with-files --compress

# Path backup sẽ nằm ở:
ls -lh sites/miyano/private/backups/ | tail -5
```

Lưu backup ra ngoài server (S3 / NAS):

```bash
rsync -av sites/miyano/private/backups/ user@backup-server:/backups/miyano/$(date +%F)/
```

### 3.3 Export data v2 ra file

```bash
# Tạo folder migration artifacts
mkdir -p ~/frappe-bench/migration_artifacts/v2_to_v3

# Export 3 DocType sidecar
bench --site miyano export-doc "IMM Asset Profile" \
  --output ~/frappe-bench/migration_artifacts/v2_to_v3/imm_asset_profile.json
bench --site miyano export-doc "IMM Vendor Profile" \
  --output ~/frappe-bench/migration_artifacts/v2_to_v3/imm_vendor_profile.json
bench --site miyano export-doc "IMM Location Ext" \
  --output ~/frappe-bench/migration_artifacts/v2_to_v3/imm_location_ext.json
```

Hoặc dùng Python snippet (linh hoạt hơn):

```python
# bench --site miyano console
import frappe, json

for dt, out in [
    ("IMM Asset Profile", "/tmp/v2_asset_profile.json"),
    ("IMM Vendor Profile", "/tmp/v2_vendor_profile.json"),
    ("IMM Location Ext",   "/tmp/v2_location_ext.json"),
]:
    records = frappe.get_all(dt, fields=["*"])
    with open(out, "w") as f:
        json.dump(records, f, default=str, ensure_ascii=False, indent=2)
    print(f"{dt}: exported {len(records)} records → {out}")
```

### 3.4 Migration patch

Code đã được shipped trong app dưới đường dẫn:

```
assetcore/patches/v3_0/001_migrate_from_v2.py
```

Nội dung rút gọn (tham khảo):

```python
# assetcore/patches/v3_0/001_migrate_from_v2.py
"""
Migrate AssetCore v2 → v3.
- Copy IMM Asset Profile  → AC Asset
- Copy IMM Vendor Profile → AC Supplier
- Copy IMM Location Ext   → AC Location
- Drop 3 sidecar tables + 16 custom_imm_* fields trên tabAsset
"""
import frappe
from frappe.utils import now_datetime


FIELDS_V2_TO_V3_ASSET = {
    "asset_name": "asset_name",
    "udi_code": "udi_code",
    "gmdn_code": "gmdn_code",
    "byt_reg_no": "byt_reg_no",
    "byt_reg_expiry": "byt_reg_expiry",
    "lifecycle_status": "lifecycle_status",
    "risk_class": "risk_class",
    "medical_class": "medical_class",
    "next_pm_date": "next_pm_date",
    "last_pm_date": "last_pm_date",
    "next_calibration_date": "next_calibration_date",
    "last_calibration_date": "last_calibration_date",
    "manufacturer_sn": "manufacturer_sn",
    "device_model": "device_model",
    "department": "department",
    "responsible_technician": "responsible_technician",
}

CUSTOM_FIELDS_TO_DROP = [
    "custom_imm_device_model",
    "custom_imm_asset_profile",
    "custom_imm_medical_class",
    "custom_imm_risk_class",
    "custom_imm_lifecycle_status",
    "custom_imm_calibration_status",
    "custom_imm_department",
    "custom_imm_responsible_tech",
    "custom_imm_last_pm_date",
    "custom_imm_next_pm_date",
    "custom_imm_last_calibration_date",
    "custom_imm_next_calibration_date",
    "custom_imm_byt_reg_no",
    "custom_imm_manufacturer_sn",
    "custom_imm_udi_code",
    "custom_imm_gmdn_code",
]


def execute():
    """Entry point — Frappe gọi tự động qua patches.txt."""
    if not _has_v2_data():
        print("[v3-migrate] No v2 data detected — skipping.")
        return

    migrated = {
        "vendor": _migrate_vendor_profiles(),
        "location": _migrate_location_ext(),
        "asset": _migrate_asset_profiles(),
    }
    _drop_custom_fields()
    _drop_v2_doctypes()
    frappe.db.commit()

    print(f"[v3-migrate] DONE @ {now_datetime()} — {migrated}")


def _has_v2_data() -> bool:
    return frappe.db.table_exists("IMM Asset Profile")


def _migrate_vendor_profiles() -> int:
    profiles = frappe.get_all("IMM Vendor Profile", fields=["*"])
    for p in profiles:
        if frappe.db.exists("AC Supplier", {"supplier_name": p.supplier_name}):
            continue
        doc = frappe.new_doc("AC Supplier")
        doc.supplier_name = p.supplier_name
        doc.vendor_type = p.vendor_type
        doc.iso_17025_cert = p.get("iso_17025_cert")
        doc.contract_end = p.get("contract_end")
        doc.insert(ignore_permissions=True)
    return len(profiles)


def _migrate_location_ext() -> int:
    records = frappe.get_all("IMM Location Ext", fields=["*"])
    for r in records:
        if frappe.db.exists("AC Location", {"location_name": r.location_name}):
            continue
        doc = frappe.new_doc("AC Location")
        doc.location_name = r.location_name
        doc.clinical_area_type = r.get("clinical_area_type")
        doc.infection_control_level = r.get("infection_control_level")
        doc.insert(ignore_permissions=True)
    return len(records)


def _migrate_asset_profiles() -> int:
    profiles = frappe.get_all("IMM Asset Profile", fields=["*"])
    for p in profiles:
        if frappe.db.exists("AC Asset", {"asset_name": p.asset_name}):
            continue
        doc = frappe.new_doc("AC Asset")
        for v2_field, v3_field in FIELDS_V2_TO_V3_ASSET.items():
            value = p.get(v2_field)
            if value is not None:
                doc.set(v3_field, value)
        doc.insert(ignore_permissions=True)
    return len(profiles)


def _drop_custom_fields():
    for fieldname in CUSTOM_FIELDS_TO_DROP:
        cf = frappe.db.exists("Custom Field", {"fieldname": fieldname, "dt": "Asset"})
        if cf:
            frappe.delete_doc("Custom Field", cf, force=True, ignore_permissions=True)
    # Nếu còn sót ở DB-level (rare):
    frappe.db.sql("""
        DELETE FROM `tabCustom Field`
        WHERE dt='Asset' AND fieldname LIKE 'custom_imm%'
    """)


def _drop_v2_doctypes():
    for dt in ("IMM Asset Profile", "IMM Vendor Profile", "IMM Location Ext"):
        if frappe.db.exists("DocType", dt):
            frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)
        # Drop table nếu Frappe chưa drop
        table = f"tab{dt}"
        frappe.db.sql(f"DROP TABLE IF EXISTS `{table}`")
```

### 3.5 Đăng ký patch

File `assetcore/patches.txt`:

```
assetcore.patches.v3_0.001_migrate_from_v2
```

### 3.6 Chạy migrate

```bash
bench --site miyano migrate
```

Theo dõi log realtime ở terminal khác:

```bash
tail -f sites/miyano/logs/worker.log
```

### 3.7 Verify sau migration

```bash
# 5 bảng AC phải có
bench --site miyano mariadb --execute "SHOW TABLES LIKE 'tabAC%';"

# 3 bảng v2 phải đã bị drop
bench --site miyano mariadb --execute \
  "SHOW TABLES LIKE 'tabIMM Asset Profile';"     # empty
bench --site miyano mariadb --execute \
  "SHOW TABLES LIKE 'tabIMM Vendor Profile';"    # empty
bench --site miyano mariadb --execute \
  "SHOW TABLES LIKE 'tabIMM Location Ext';"      # empty

# Không còn custom_imm_* trên tabAsset
bench --site miyano mariadb --execute \
  "SHOW COLUMNS FROM tabAsset LIKE 'custom_imm%';"   # empty
```

Count sanity check:

```bash
bench --site miyano console <<'PY'
import frappe
print("AC Asset:",    frappe.db.count("AC Asset"))
print("AC Supplier:", frappe.db.count("AC Supplier"))
print("AC Location:", frappe.db.count("AC Location"))
PY
```

Số lượng phải khớp với v2 ± các record fail (xem log).

---

## 4. Load fixtures

### 4.1 Fixtures shipped trong app

```
assetcore/fixtures/
├── imm_roles.json              # 8 roles
├── imm_workflows.json          # CAPA + Incident workflow
├── imm_sla_policies.json       # 9 SLA policy defaults
├── imm_device_models_sample.json  # 5 device models mẫu
└── imm_naming_series.json      # naming series cho AC/IMM
```

### 4.2 Apply fixtures

```bash
bench --site miyano migrate
# Frappe tự pick up fixtures từ hooks.py `fixtures` key
```

### 4.3 Verify roles

```bash
bench --site miyano console <<'PY'
import frappe
roles = [
    "IMM System Admin", "IMM Department Head", "IMM Operations Manager",
    "IMM Workshop Lead", "IMM Technician", "IMM Document Officer",
    "IMM Storekeeper", "IMM QA Officer",
]
for r in roles:
    print(r, "→", "OK" if frappe.db.exists("Role", r) else "MISSING")
PY
```

### 4.4 Seed SLA policies

9 policies theo ma trận `{P1,P2,P3} × {Low,Medium,High,Critical}` + 1 default.

```bash
bench --site miyano execute assetcore.fixtures.seed.seed_sla_policies
```

### 4.5 Seed sample device models

5 mẫu: Monitor bệnh nhân, máy thở, X-ray di động, máy siêu âm, máy truyền dịch.

```bash
bench --site miyano execute assetcore.fixtures.seed.seed_sample_device_models
```

---

## 5. Scheduler setup

### 5.1 Kiểm tra hooks.py

4 jobs phải được khai báo trong `assetcore/hooks.py`:

```python
scheduler_events = {
    "daily": [
        "assetcore.services.imm00.check_capa_overdue",
        "assetcore.services.imm00.check_vendor_contract_expiry",
        "assetcore.services.imm00.check_registration_expiry",
        "assetcore.services.imm00.rollup_asset_kpi",
    ],
}
```

### 5.2 Enable scheduler

```bash
bench --site miyano enable-scheduler
bench --site miyano scheduler resume
```

### 5.3 Test manual một job

```bash
bench --site miyano execute assetcore.services.imm00.check_capa_overdue
bench --site miyano execute assetcore.services.imm00.check_vendor_contract_expiry
bench --site miyano execute assetcore.services.imm00.check_registration_expiry
bench --site miyano execute assetcore.services.imm00.rollup_asset_kpi
```

Nếu lỗi, xem log:

```bash
tail -100 sites/miyano/logs/scheduler.log
```

---

## 6. Permission setup

### 6.1 Role permissions

Đã được apply qua fixtures (`imm_roles.json` + DocType-level `permissions`).

### 6.2 Permission Query Condition

File `assetcore/permission.py`:

```python
# IMM Technician chỉ thấy AC Asset của mình
def get_ac_asset_permission_query(user):
    roles = frappe.get_roles(user)
    if "IMM Technician" in roles and "IMM System Admin" not in roles:
        return f"(`tabAC Asset`.responsible_technician = '{user}')"
    return ""
```

Đăng ký trong `hooks.py`:

```python
permission_query_conditions = {
    "AC Asset": "assetcore.permission.get_ac_asset_permission_query",
}
```

### 6.3 Tạo user test

```bash
bench --site miyano add-user technician@test.com \
  --first-name "Test" --last-name "Tech" \
  --password "Test@1234" \
  --add-role "IMM Technician"

bench --site miyano add-user qa@test.com \
  --first-name "QA" --last-name "Officer" \
  --password "Test@1234" \
  --add-role "IMM QA Officer"
```

### 6.4 Test quyền trong console

```bash
bench --site miyano console <<'PY'
import frappe
frappe.set_user("technician@test.com")
assets = frappe.get_list("AC Asset", fields=["name", "responsible_technician"])
print(f"Technician sees {len(assets)} assets (phải chỉ thấy assets của mình)")
PY
```

---

## 7. Cấu hình email

### 7.1 SMTP config

```bash
bench --site miyano set-config mail_server "smtp.gmail.com"
bench --site miyano set-config mail_port 587
bench --site miyano set-config use_tls 1
bench --site miyano set-config mail_login "noreply@hospital.vn"
bench --site miyano set-config mail_password "<app-password>"
```

### 7.2 Email templates

Tạo 3 template trong UI (`/app/email-template`) hoặc import fixture:

| Tên template | Subject | Trigger |
|---|---|---|
| `CAPA_Overdue` | `[CAPA Overdue] {capa_id} — {asset_name}` | `check_capa_overdue` |
| `Contract_Expiry_30d` | `[Hợp đồng sắp hết hạn] {supplier_name}` | `check_vendor_contract_expiry` |
| `BYT_Registration_Expiry` | `[Đăng ký BYT sắp hết hạn] {asset_name}` | `check_registration_expiry` |

### 7.3 Test send mail

```bash
bench --site miyano execute frappe.sendmail \
  --args '["admin@hospital.vn", "AssetCore Test", "Setup email OK"]'
```

---

## 8. Frontend setup (Vue 3 + Vite)

### 8.1 Install dependencies

```bash
cd ~/frappe-bench/apps/assetcore/frontend
pnpm install
```

### 8.2 Config `.env`

File `frontend/.env`:

```env
VITE_API_BASE=http://localhost:8000
VITE_APP_NAME=AssetCore
VITE_API_PREFIX=/api/method/assetcore
```

### 8.3 Dev server

```bash
pnpm dev
# http://localhost:5173
```

### 8.4 Build production

```bash
pnpm build
# Output: frontend/dist/

# Copy vào public/ để Frappe serve
cp -r dist/* ../assetcore/public/frontend/
bench --site miyano clear-cache
```

---

## 9. Smoke test checklist

Chạy tuần tự từ trên xuống. Mỗi bước pass mới sang bước tiếp.

- [ ] **S-01** Tạo 1 `AC Asset Category` (VD: "Thiết bị chẩn đoán hình ảnh").
- [ ] **S-02** Tạo 1 `AC Department` (VD: "Khoa Chẩn đoán hình ảnh").
- [ ] **S-03** Tạo 1 `AC Location` (VD: "Phòng X-ray 1, Tầng 2").
- [ ] **S-04** Tạo 1 `IMM Device Model` (Class II, PM interval 180 ngày, risk Medium).
- [ ] **S-05** Tạo 1 `AC Asset` link với Device Model ở S-04 → verify auto-fill `medical_class`, `risk_class`.
- [ ] **S-06** Submit AC Asset → verify `lifecycle_status = Commissioned` + 1 `Asset Lifecycle Event` được tạo.
- [ ] **S-07** Transition Active → Under Repair qua API `transition_asset_status` → kiểm tra sinh ALE + Audit Trail entry.
- [ ] **S-08** Tạo 1 `IMM CAPA Record` (thiếu root_cause) → submit → expect `ValidationError`.
- [ ] **S-09** Update CAPA với `root_cause` + `corrective_action` → submit thành công.
- [ ] **S-10** Tạo 1 `Incident Report` severity Critical + `patient_affected = 1` → verify warning "báo cáo BYT".
- [ ] **S-11** Chạy `check_capa_overdue` manual → verify email gửi tới QA Officer.
- [ ] **S-12** Verify SHA-256 chain: gọi API `assetcore.api.imm00.verify_audit_chain` cho AC Asset ở S-05 → return `{"valid": true}`.
- [ ] **S-13** Query permission: login technician không phải responsible → không thấy asset (list count = 0).

Lệnh gọi API mẫu (S-12):

```bash
curl -X POST http://localhost:8000/api/method/assetcore.api.imm00.verify_audit_chain \
  -H "X-Frappe-CSRF-Token: $CSRF" \
  -H "Cookie: sid=$SID" \
  -d '{"asset": "AC-ASSET-2026-00001"}'
```

---

## 10. Troubleshooting

| Triệu chứng | Nguyên nhân | Giải pháp |
|---|---|---|
| `bench migrate` fail giữa patch v3 | Data v2 có record lỗi format | Check `sites/miyano/logs/worker.log` → fix record → rerun `bench migrate` |
| Scheduler không chạy | Scheduler đang paused / Redis lỗi | `bench --site miyano doctor` + `bench --site miyano scheduler resume` |
| Permission Query không áp dụng | Cache | `bench --site miyano clear-cache && bench restart` |
| Custom Fields `custom_imm_*` còn sót | Patch bỏ sót | `DELETE FROM \`tabCustom Field\` WHERE dt='Asset' AND fieldname LIKE 'custom_imm%';` |
| FE dev không connect được BE | CORS | Set `allow_cors = "*"` trong `site_config.json` (chỉ DEV) |
| Email không gửi | SMTP sai credential | `bench --site miyano execute frappe.email.queue.flush` + check log |
| Audit chain invalid | Record bị tamper manual | Không fix được — phải điều tra forensic, restore từ backup |

SQL thủ công dọn sót:

```sql
-- Chạy trong mariadb console
USE `_<site_hash>`;

-- Verify không còn custom_imm_*
SELECT fieldname FROM `tabCustom Field`
WHERE dt='Asset' AND fieldname LIKE 'custom_imm%';

-- Nếu còn:
DELETE FROM `tabCustom Field`
WHERE dt='Asset' AND fieldname LIKE 'custom_imm%';

-- Verify 3 sidecar table đã drop:
SHOW TABLES LIKE 'tabIMM Asset Profile';
SHOW TABLES LIKE 'tabIMM Vendor Profile';
SHOW TABLES LIKE 'tabIMM Location Ext';

-- Nếu còn:
DROP TABLE IF EXISTS `tabIMM Asset Profile`;
DROP TABLE IF EXISTS `tabIMM Vendor Profile`;
DROP TABLE IF EXISTS `tabIMM Location Ext`;
```

---

## 11. Production deployment checklist

### 11.1 Hardening

- [ ] Disable developer mode: `bench --site miyano set-config developer_mode 0`.
- [ ] Enable signed session cookies: `bench --site miyano set-config session_expiry "06:00:00"`.
- [ ] Disable `allow_cors = "*"` (chỉ dùng khi DEV).
- [ ] HTTPS enforced qua Nginx + Let's Encrypt: `sudo bench setup lets-encrypt miyano`.
- [ ] CORS whitelist FE origin (nếu FE deploy separate domain):

  ```json
  { "allow_cors": "https://assetcore.hospital.vn" }
  ```

- [ ] Set strong `encryption_key`: `bench --site miyano set-config encryption_key "$(openssl rand -base64 32)"`.

### 11.2 Backup

- [ ] Daily backup cron + retention 30 ngày:

  ```cron
  0 2 * * * cd /home/frappe/frappe-bench && bench --site miyano backup --with-files --compress
  0 3 * * * find /home/frappe/frappe-bench/sites/miyano/private/backups -mtime +30 -delete
  ```

- [ ] Offsite backup (S3 / rsync daily).

### 11.3 Monitoring

- [ ] Prometheus exporter Frappe: `pip install frappe-prometheus-exporter`.
- [ ] Cấu hình metrics endpoint `/metrics` (internal only).
- [ ] Alert rules: scheduler down > 15 phút, error rate > 1%, DB connection saturation > 80%.

### 11.4 Log rotation

`/etc/logrotate.d/frappe`:

```conf
/home/frappe/frappe-bench/sites/*/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

### 11.5 Performance

- [ ] Redis persistence (`appendonly yes`) cho queue.
- [ ] MariaDB `innodb_buffer_pool_size` = 50-60% RAM.
- [ ] Bench workers: `bench setup supervisor && bench setup production frappe`.

---

## 12. Rollback plan

Nếu migration v3 fail hoặc production phát hiện regression nghiêm trọng:

### 12.1 Rollback database

```bash
cd ~/frappe-bench

# Liệt kê backup mới nhất
ls -lht sites/miyano/private/backups/ | head -5

# Restore DB + files
bench --site miyano restore \
  sites/miyano/private/backups/<timestamp>-miyano-database.sql.gz \
  --with-public-files sites/miyano/private/backups/<timestamp>-miyano-files.tar \
  --with-private-files sites/miyano/private/backups/<timestamp>-miyano-private-files.tar
```

### 12.2 Rollback code

```bash
cd ~/frappe-bench/apps/assetcore

# Checkout tag v2 cuối cùng ổn định
git fetch --tags
git checkout v2.3.0   # hoặc tag v2 stable gần nhất

cd ~/frappe-bench
bench --site miyano migrate
bench restart
```

### 12.3 Verify post-rollback

- [ ] Login web thành công.
- [ ] `IMM Asset Profile` list mở được.
- [ ] Scheduler chạy lại (`bench --site miyano scheduler status`).
- [ ] Thông báo stakeholder incident + RCA.

### 12.4 RCA template

Sau mỗi rollback, ghi RCA vào `/docs/incidents/YYYY-MM-DD_rollback_v3.md`:

```markdown
# Incident: Rollback v3 migration
- Date: YYYY-MM-DD
- Trigger: <trigger>
- Root cause: <rca>
- Corrective: <fix>
- Preventive: <preventive>
- Tracked in CAPA: CAPA-YYYY-XXXXX
```

---

## 13. Liên hệ & tài liệu liên quan

| Document | Link |
| --- | --- |
| Module Overview v3 | `docs/imm-00/IMM-00_Module_Overview.md` |
| Technical Design v3 | `docs/imm-00/IMM-00_Technical_Design.md` |
| BA Requirements v3 | `docs/imm-00/IMM-00_BA_Requirements.md` |
| Test Cases v3 | `docs/imm-00/IMM-00_Test_Cases.md` |
| Runbook Operations | `docs/runbook/IMM-00_Ops_Runbook.md` |

**Kết thúc Setup Guide v3.0.0.**
