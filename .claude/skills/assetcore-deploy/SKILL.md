---
name: assetcore-deploy
description: >
  Triển khai và vận hành AssetCore — bao gồm bench operations hàng ngày, migration,
  patches, fixtures, troubleshoot site, provisioning production/staging, FE build,
  supervisor/nginx, backup/rollback, release versioning.
  Dùng khi user nói "bench", "migrate", "deploy", "lên prod", "release", "rollback",
  "go-live", "site bị lỗi", "rebuild assets", "clear cache", "reset DB", "scheduler",
  "log không thấy", "install-app", "fixture export", "patch", "supervisor", "nginx",
  "config server", "khi triển khai cho khách hàng", "site mới cho bệnh viện X",
  "email không gửi", "SMTP", "Email Queue", "flush email", "chuông không có thông báo",
  "không nhận thông báo", "set password user".
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
| `AttributeError: ... no attribute '<method>'` sau khi thêm `@frappe.whitelist()` | gunicorn `--preload` workers cũ chưa nạp code Python mới (2026-06-01 audit AUTH) | `bench restart` (prod) / HUP reload gunicorn; verify `bench execute assetcore.api.X.method` chạy được TRƯỚC khi test qua HTTP/Playwright |
| `bench migrate` fail | Patch không idempotent | Read patch file; add guards (`has_column`, `exists`) |
| Permission denied sau install | `after_install` không chạy | `bench --site <site> execute assetcore.setup.install.after_install` |
| Chuông trống / không có thông báo | DATA: record toàn do `Administrator` tự tạo+tự gán → self-notify chặn đúng (KHÔNG phải bug) | Cần data đa-user (actor ≠ assignee). Xem LL-BE-34 decision tree TRƯỚC khi sửa code |
| Email enqueue nhưng không gửi | Queue `status="Not Sent"` chờ scheduler flush | `Email Queue.send()` trực tiếp (xem dưới) — `bench flush-email-queue` KHÔNG tồn tại trong build này |
| 1 user không nhận email | `Notification Settings.enable_email_notifications=0` hoặc user là `Administrator` | Bật cờ trong Notification Settings của user; `_user_wants_email` luôn chặn Administrator |

### Email / Notification — SMTP infra & flush (gặp 2026-06-01)

**Site này KHÔNG có `Email Account` DocType** (cả outgoing lẫn default). SMTP chạy qua **fallback ở `site_config.json`** và hoạt động thật:
```
mail_server=smtp.gmail.com  mail_port=587  use_tls=1
mail_login=<app-account>@gmail.com  auto_email_id=<app-account>@gmail.com
```
Frappe core dùng config này khi không tìm thấy `Email Account`. → Đừng giả định "user đã set Email Account DocType"; verify `site_config` trước. Muốn quản lý qua UI / đổi sender → tạo `Email Account` outgoing (quyết định của user, đừng tự thêm).

**Gửi/flush email THẬT (verify, không chỉ enqueue):**
```bash
# bench flush-email-queue KHÔNG tồn tại trong build này — gửi trực tiếp:
bench --site <site> execute frappe.email.queue.flush          # nếu có
# hoặc loop Email Queue.send() qua _<task>.py rồi execute (xem maintenance scripts)
```
Sau khi gửi: verify `Email Queue` entry → `status="Sent"`. **`Sent` ≠ đã vào inbox** — sender = SMTP account của site, khác địa chỉ người nhận → có thể vào spam. Báo user "kiểm tra inbox/spam", đừng tuyên bố "đã nhận".

**Set password cho user test** (để login kiểm chứng chuông): dùng `update_password` / `bench --site <site> set-user-password <user> <pwd>`, **KHÔNG** save full User doc — save full doc có thể fail trên orphan link cũ (đã gặp `LinkExistsError` với `Khoa-NGTH`).

### Maintenance scripts — dọn data / fix ad-hoc / migrate one-shot

Bug recurring 2026-05-27 (data cleanup session): script tạm chạy sai pattern, leak hoặc xoá nhầm. Tuân thủ checklist:

**Pattern chuẩn (CONVENTIONS §27, §32, §33, §39):**

| ❌ Không dùng | ✅ Dùng | Lý do |
|---|---|---|
| `cat /tmp/script.py \| bench --site X console` | Tạo file `assetcore/_<task>.py` rồi `bench --site X execute assetcore._<task>.func` | IPython interactive không giữ scope giữa cell — function defs không persist, `NameError` ngẫu nhiên |
| `frappe.get_all(..., filters={"name": ("like", r"\_Test%")})` cho maintenance | `frappe.db.sql_list("SELECT name FROM ... WHERE name LIKE %s", (r"\_Test%",))` | `get_all` áp User Permission filter → trả 0 dù DB có 12 |
| `frappe.db.sql_list("... LIKE '\_Test%'")` literal | Parameterized: `("... LIKE %s", (r"\_Test%",))` | Literal `%` trong query → `TypeError: not enough arguments for format string` |
| `frappe.delete_doc("AC Asset", ...)` khi audit còn rows | Purge `tabIMM Audit Trail` (raw SQL) trước → ORM delete asset | AC Asset `on_trash` check 5 tables → `LinkExistsError WR-03` |
| `frappe.delete_doc("IMM Audit Trail", ...)` | Raw SQL `DELETE FROM` (CHỈ cho leaked test fixtures, user-approved) | Audit `on_trash` cố tình throw ISO 13485:7.5.9 chống tampering |

**Workflow chuẩn**:
1. `bench --site <site> backup` (verify `.sql.gz` tồn tại)
2. Tạo `assetcore/_<task>_cleanup.py` với:
   - `def run_safe()`: ORM cleanup (cascade đúng thứ tự)
   - `def run_audit_purge()`: raw SQL purge audit trail (CHỈ nếu cần, AskUserQuestion trước)
3. Dry-run: viết `def run_scan()` in count + sample tên — present cho user
4. User approve → `bench --site <site> execute assetcore._<task>_cleanup.run_safe`
5. Verify bằng SQL count = 0
6. `rm assetcore/_<task>_cleanup.py` — KHÔNG commit script tạm

**IMM Audit Trail tampering policy** (ISO 13485:7.5.9): bypass `on_trash` CHỈ được phép khi:
- Target rows là leaked test fixtures (`_Test*`, `TEST-*`) — không bao giờ production audit thật
- User confirm bypass via AskUserQuestion (auto-mode classifier sẽ chặn raw DELETE Audit Trail nếu không có context approve)
- DB backup chạy xong trước
- Raw SQL CHỈ ở maintenance script — KHÔNG ở production code path / scheduler / API endpoint

Reference: CONVENTIONS §27, §32, §33, §37, §38, §39.

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

---

## Phần 3 — Destructive DB Operations (cleanup / mass-delete / restore)

Áp dụng khi user yêu cầu:
- "Dọn data rác", "xoá test data", "clean up junk"
- "Reset bảng X", "xoá hết record Y"
- "Restore từ backup", "rollback DB"
- Bất kỳ ALTER TABLE, UPDATE bulk

### Checklist BẮT BUỘC (không skip step nào)

```
[1] Backup DB + xác nhận file (size > 0)
[2] Viết dry-run script (_scan_xxx.py) — KHÔNG delete, chỉ in count+samples
[3] Present qua AskUserQuestion — chờ user duyệt scope
[4] Cascade-delete theo thứ tự FK (children → parents)
[5] Orphan sweep sau khi xoá masters
[6] Re-run scan để verify 0 junk còn lại
[7] Xoá script tạm `assetcore/_xxx.py`
```

### Step 1: Backup
```bash
bench --site <site> backup --with-files
ls -la sites/<site>/private/backups/ | tail -3
# Confirm: file .sql.gz size > 0
```

### Step 2-3: Dry-run pattern

```python
# assetcore/_scan_junk.py — prefix `_` để dễ grep cleanup sau
"""Dry-run: list junk records matching explicit patterns."""
from __future__ import annotations
import frappe

# CHỌN PATTERN CỤ THỂ — đừng dùng wildcard mơ hồ như '_%'
NAME_PATTERNS = ["test", "_test", "_diag"]
TEXT_PATTERNS = ["test", "_test", "demo data", "sample data", "dummy", "fake"]

def run():
    modules = frappe.get_all("Module Def", filters={"app_name": "assetcore"}, pluck="name")
    doctypes = [d.name for d in frappe.get_all("DocType",
                filters={"module": ["in", modules]},
                fields=["name", "istable", "issingle"])
                if not d.istable and not d.issingle]

    findings = []
    for dt in doctypes:
        meta = frappe.get_meta(dt)
        text_fields = [f.fieldname for f in meta.fields
                       if f.fieldtype in ("Data", "Small Text", "Long Text", "Text Editor", "Text")
                       and frappe.db.has_column(dt, f.fieldname)]
        # Build parameterized LIKE — KHÔNG f-string giá trị
        clauses = []
        params = {}
        for i, p in enumerate(NAME_PATTERNS):
            clauses.append(f"LOWER(`name`) LIKE %(n{i})s")
            params[f"n{i}"] = f"%{p.lower()}%"
        for f in text_fields:
            for i, p in enumerate(TEXT_PATTERNS):
                key = f"t_{f}_{i}"
                clauses.append(f"LOWER(`{f}`) LIKE %({key})s")
                params[key] = f"%{p.lower()}%"
        where = " OR ".join(clauses)
        cnt = frappe.db.sql(f"SELECT COUNT(*) FROM `tab{dt}` WHERE {where}", params)[0][0]
        if cnt:
            samples = frappe.db.sql_list(
                f"SELECT name FROM `tab{dt}` WHERE {where} ORDER BY name LIMIT 8", params)
            findings.append((dt, cnt, samples))

    total = sum(c for _, c, _ in findings)
    print(f"Total junk: {total}")
    for dt, cnt, samples in sorted(findings, key=lambda x: -x[1]):
        print(f"  [{cnt:4d}] {dt}: {', '.join(samples[:4])}")
```

```bash
bench --site <site> execute assetcore._scan_junk.run
```

→ Trình bày kết quả + dùng `AskUserQuestion` để user confirm scope trước khi xoá.

### Step 4: Cascade-delete đúng thứ tự FK

Frappe KHÔNG auto-cascade. Thứ tự xoá AssetCore:

| Order | DocType | Reason |
|---|---|---|
| 1 | IMM Audit Trail | history của asset (asset col) |
| 2 | Asset Lifecycle Event | events (asset col) |
| 3 | IMM RCA Record / IMM CAPA Record | root cause của incident |
| 4 | Asset Document | docs (`asset_ref`, `model_ref`) |
| 5 | AC Spare Part Stock | child (`spare_part`, `warehouse`) |
| 6 | Incident Report (`asset`) / Asset Repair (`asset_ref`) | operational |
| 7 | AC Asset | master |
| 8 | AC Asset Category / AC Warehouse / AC Spare Part | master |
| 9 | IMM Device Model / AC Supplier / IMM Training Program | master |

```python
def _safe_delete(dt, name):
    try:
        doc = frappe.get_doc(dt, name)
        if getattr(doc, "docstatus", 0) == 1:
            doc.flags.ignore_permissions = True
            doc.cancel()
        frappe.delete_doc(dt, name, force=True, ignore_permissions=True,
                          ignore_on_trash=True, delete_permanently=True)
        return True
    except Exception as e:
        print(f"FAIL {dt}/{name}: {str(e)[:120]}")
        return False
```

### Step 5: Orphan sweep sau khi xoá masters

```sql
-- MariaDB không cho subquery trên cùng bảng đang delete → wrap alias
DELETE FROM `tabAsset Lifecycle Event`
WHERE asset IS NOT NULL AND asset != ''
  AND asset NOT IN (SELECT name FROM (SELECT name FROM `tabAC Asset`) x);

DELETE FROM `tabIMM Audit Trail`
WHERE asset IS NOT NULL AND asset != ''
  AND asset NOT IN (SELECT name FROM (SELECT name FROM `tabAC Asset`) x);

-- Records vi phạm required field sau khi reference bị xoá
DELETE FROM `tabAsset Lifecycle Event` WHERE asset IS NULL OR asset = '';
```

### Restore — KHÔNG cần mariadb root pw

`bench restore` prompt root password. Workaround dùng site DB user (luôn có CRUD trên DB của mình):

```bash
DBNAME=$(python3 -c "import json; print(json.load(open('sites/<site>/site_config.json'))['db_name'])")
DBPW=$(python3 -c "import json; print(json.load(open('sites/<site>/site_config.json'))['db_password'])")

# Option A: Restore full backup (cần CREATE TABLE → site user thường KHÔNG có quyền)
# → vẫn cần `bench restore` với root pw

# Option B: Restore CHỈ table cần thiết (table phải đã tồn tại)
BAK=sites/<site>/private/backups/<timestamp>-database.sql.gz
for tbl in "AC Asset" "AC Asset Category" "Asset Repair" "Asset Lifecycle Event"; do
  TMP=/tmp/restore_${tbl// /_}.sql
  zcat "$BAK" | awk "/^LOCK TABLES \`tab${tbl}\` WRITE/,/^UNLOCK TABLES/" > "$TMP"
  mysql -u "$DBNAME" -p"$DBPW" "$DBNAME" < "$TMP"
  cnt=$(mysql -u "$DBNAME" -p"$DBPW" "$DBNAME" -sN -e "SELECT COUNT(*) FROM \`tab${tbl}\`")
  echo "${tbl}: ${cnt} rows restored"
  rm "$TMP"
done
```

### Pause scheduler/tests TRƯỚC khi xoá hàng loạt

Bug đã gặp: trong lúc cleanup 13:55, `bench run-tests` chạy song song tạo data mới tại 14:31 → phải cleanup vòng 2.

```bash
# Maintenance mode chặn UI/API
bench --site <site> set-maintenance-mode on

# Sau khi xong:
bench --site <site> set-maintenance-mode off
```

Tối thiểu: không kick `bench run-tests` ở terminal khác trong lúc cleanup.

### Distinguishing test fixtures vs real data

Patterns KHÔNG match generic 'test' nhưng vẫn là test fixture — phải hỏi user trước khi xoá:

| Pattern | Nguồn gốc | VD |
|---|---|---|
| `_Diag Asset N` | Frappe diagnostic tests (`_` prefix) | `_Diag Asset 1..6` |
| `Foo — ICU-decom/-pm/-event/-trans` | Workflow scenario tests | `Dräger Evita V500 — ICU-decom` |
| `InhAsset {hex}` / `OvrAsset {hex}` | Inheritance/cascade test | `InhAsset b33459` |
| `Foo (Import {N})` | Import wizard test | `Asset (Import 61525)` |

→ `AskUserQuestion` với 3 options: xoá / xoá một phần / giữ lại.

### Step 7: Cleanup helper scripts

```bash
rm assetcore/_scan_*.py assetcore/_delete_*.py
```
KHÔNG commit script tạm. Prefix `_` đảm bảo `git status` thấy ngay.

### Anti-patterns đã gặp (KHÔNG lặp lại)

1. **LIKE wildcard không escape** — `'_%'` match toàn bảng. → §32 trong CONVENTIONS.
2. **Đoán tên cột** — `WHERE serial_no=...` khi cột thật là `gmdn_code`. → Phải DESCRIBE trước.
3. **Xoá master trước child** — FK orphan, broken refs. → Theo thứ tự ở table trên.
4. **Restore khi không có root pw** → site DB user + extract table.
5. **Xoá vòng 1 khi tests đang chạy** → maintenance-mode trước.

Reference: `CONVENTIONS.md §32`, `§33`; `assetcore-be` LL-BE-21, LL-BE-22.
