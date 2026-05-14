---
name: assetcore-deploy
description: >
  Triển khai và vận hành AssetCore — bao gồm bench operations hàng ngày, migration,
  patches, fixtures, troubleshoot site, provisioning production/staging, FE build,
  supervisor/nginx, backup/rollback, release versioning.
  Dùng khi user nói "bench", "migrate", "deploy", "lên prod", "release", "rollback",
  "go-live", "site bị lỗi", "rebuild assets", "clear cache", "reset DB", "scheduler",
  "log không thấy", "install-app", "fixture export", "patch", "supervisor", "nginx",
  "config server", "khi triển khai cho khách hàng", "site mới cho bệnh viện X".
  Ưu tiên skill này trước bất kỳ lệnh destructive nào.
---

# AssetCore Deploy & DevOps

Skill này bao 2 phạm vi: **DevOps hàng ngày (bench operations)** + **Production Deployment**.

---

## Phần 1 — DevOps (Bench Operations)

### Cheat sheet — lệnh hàng ngày
```bash
# Working directory: bench root
cd /home/miyano/frappe-bench

bench start                              # chạy tất cả services
bench --site miyano console              # Python REPL với Frappe context
bench --site miyano migrate              # chạy patches + reload DocType/workflow JSON
bench --site miyano clear-cache          # clear Redis cache
bench --site miyano reload-doctype "Asset Repair"
bench --site miyano reload-doc assetcore workflow imm_09_repair_workflow
bench --site miyano execute assetcore.setup.install.after_install
bench restart                            # restart supervisor (production)
bench build --app assetcore              # rebuild JS/CSS bundles
```

### Migration model
```
assetcore/patches/
├── v3_0/
│   ├── 001_migrate_from_v2.py          # breaking: remove Custom Fields
│   ├── 002_backfill_asset_status.py    # data migration
│   └── 003_add_audit_trail_hash.py     # schema + data
└── v3_1/
    └── 001_add_lifecycle_event_index.py
```

```python
# patches/vX_Y/NNN_description.py
from __future__ import annotations
import frappe

def execute() -> None:
    """One-line: what and why."""
    if frappe.db.exists("DocType", "AC Asset") and \
       frappe.db.has_column("AC Asset", "lifecycle_status"):
        frappe.db.sql("ALTER TABLE `tabAC Asset` RENAME COLUMN ...")
        frappe.db.commit()
```

**Convention:**
- Patch phải idempotent: chạy 2 lần không vỡ.
- Check `frappe.db.has_column(...)` trước khi alter.
- Commit trong patch (`frappe.db.commit()`); mỗi patch là transaction riêng.
- Thêm vào `assetcore/patches.txt`: `assetcore.patches.v3_1.001_xxx`.

### Fixtures — 3-list rule (MANDATORY)

```bash
# Sau khi thêm/sửa workflow JSON, cập nhật CẢ 3 list trong hooks.py:
# 1. "dt": "Workflow"           — tên workflow
# 2. "dt": "Workflow State"     — TẤT CẢ state names từ workflow JSON
# 3. "dt": "Workflow Action Master" — TẤT CẢ action labels từ workflow JSON

# Lấy danh sách states + actions từ JSON để copy vào hooks.py:
python3 -c "import json; d=json.load(open('assetcore/assetcore/workflow/imm_XX_<name>_workflow.json')); print('States:', [s['state'] for s in d['states']]); print('Actions:', list({t['action'] for t in d['transitions']}))"

# Sau khi sửa hooks.py, export fixtures:
bench --site miyano export-fixtures --app assetcore
# Commit cả hooks.py + fixture JSON files cùng lúc
```

Thiếu bất kỳ list nào → `bench --site <new-site> migrate` sẽ fail khi load workflow trên fresh site. Xem `CONVENTIONS.md §1b` cho full checklist.

### Troubleshoot thường gặp
| Symptom | Cause | Fix |
|---|---|---|
| DocType change không áp dụng | Quên `bench migrate` | `bench --site miyano migrate` |
| Workflow action button mất | `Workflow Action Master` fixture thiếu | Thêm action label + export fixtures + migrate |
| FE không load sau code change | Vite cache stale | `npm run dev --force` hoặc clear `.vite/` |
| Scheduler job không chạy | `bench start` không có worker | Check `bench start` output có `worker` process |
| Import error sau deploy | Missing `__init__.py` hoặc syntax error | `python -c "import assetcore.api.immXX"` để verify |
| `bench migrate` fail | Patch không idempotent | Read patch file; add guards (`has_column`, `exists`) |
| Permission denied sau install | `after_install` không chạy | `bench --site <site> execute assetcore.setup.install.after_install` |

---

## Phần 2 — Production Deployment

### Environment topology
```
Dev:       miyano (local, developer_mode=1)
Staging:   multi-site, 1 site per hospital (QA/UAT)
Prod:      1 bench per customer, 1 site per hospital tenant
```

### Pre-deployment checklist (KHÔNG skip bất kỳ item nào)
- [ ] Code trên release branch (vd: `release/wave-2`), tagged `v3.x.y`
- [ ] Tests green: `bench --site <staging> run-tests --app assetcore`
- [ ] Workflow smoke test green: `--module assetcore.tests.test_workflows`
- [ ] FE typecheck: `cd frontend && npm run typecheck && npm run lint`
- [ ] FE build: `npm run build` exit 0
- [ ] Không có whitelist endpoint mới thiếu permission gate
- [ ] Patches mới đã thêm vào `patches.txt` và test trên fresh site
- [ ] DB backup confirmed xong trước khi chạy migrate prod

### Deployment sequence (staging/prod)
```bash
# 1. Pull code
cd /home/<bench>/apps/assetcore && git pull origin release/wave-2

# 2. Install Python dependencies (nếu có)
cd /home/<bench> && bench pip install -r apps/assetcore/requirements.txt

# 3. Build FE
cd apps/assetcore/frontend && npm ci && npm run build

# 4. Migrate (chạy patches + reload DocTypes/workflows)
bench --site <site> migrate

# 5. Restart processes
bench restart

# 6. Smoke validation
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_workflows
```

### Fixtures import trên fresh site
```bash
bench --site <new-site> install-app assetcore
bench --site <new-site> execute assetcore.setup.install.after_install
# Verify workflows loaded:
bench --site <new-site> execute "frappe.get_all('Workflow', pluck='name')"
```

### Backup & Rollback
```bash
# Backup trước deploy
bench --site <site> backup --with-files
# Backup location: /home/<bench>/sites/<site>/private/backups/

# Rollback code
git revert HEAD && git push
bench --site <site> migrate

# Rollback DB (nếu patch gây hỏng data)
bench --site <site> restore /path/to/backup.sql.gz
```

### supervisor/nginx (production only)
```bash
# Config files (auto-generated bởi bench)
cat /home/<bench>/config/supervisor.conf
cat /home/<bench>/config/nginx.conf

# Reload sau thay đổi config
sudo supervisorctl reload
sudo nginx -t && sudo nginx -s reload
```

### Release versioning
```
v3.0.0 — Wave 1 (IMM-04,05,08,09,11,12)
v3.1.0 — Wave 2 (IMM-01,02,03,06,15,16)
v3.2.0 — Wave 3 (IMM-07,10,13,14,17)
```
Bump `assetcore/__version__.py` + git tag `vX.Y.Z` + release note.

### Safety rules
- **KHÔNG bao giờ** deploy mà không có DB backup xác nhận.
- **KHÔNG** force-push lên main/release branch.
- **KHÔNG** chạy `drop-site` hay `reset` trên production.
- Deployment window: báo team trước ít nhất 30 phút.
- Nếu migrate fail giữa chừng: DỪNG, rollback ngay, investigate.
