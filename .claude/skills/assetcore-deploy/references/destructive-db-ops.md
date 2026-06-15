# Destructive DB Operations (Phần 3) — cleanup / mass-delete / restore

> Heavy reference moved from `SKILL.md`. Full checklist, backup, dry-run, cascade-delete order, orphan sweep, restore, pause scheduler, fixtures-vs-real-data, cleanup helpers, anti-patterns. **Mọi step PRESERVED verbatim — đây là destructive-op runbook, mất 1 bước = nguy hiểm.**

Áp dụng khi user yêu cầu:
- "Dọn data rác", "xoá test data", "clean up junk"
- "Reset bảng X", "xoá hết record Y"
- "Restore từ backup", "rollback DB"
- Bất kỳ ALTER TABLE, UPDATE bulk

## Checklist BẮT BUỘC (không skip step nào)

```
[1] Backup DB + xác nhận file (size > 0)
[2] Viết dry-run script (_scan_xxx.py) — KHÔNG delete, chỉ in count+samples
[3] Present qua AskUserQuestion — chờ user duyệt scope
[4] Cascade-delete theo thứ tự FK (children → parents)
[5] Orphan sweep sau khi xoá masters
[6] Re-run scan để verify 0 junk còn lại
[7] Xoá script tạm `assetcore/_xxx.py`
```

## Step 1: Backup
```bash
bench --site <site> backup --with-files
ls -la sites/<site>/private/backups/ | tail -3
# Confirm: file .sql.gz size > 0
```

## Step 2-3: Dry-run pattern

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

## Step 4: Cascade-delete đúng thứ tự FK

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

## Step 5: Orphan sweep sau khi xoá masters

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

## Restore — KHÔNG cần mariadb root pw

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

## Pause scheduler/tests TRƯỚC khi xoá hàng loạt

Bug đã gặp: trong lúc cleanup 13:55, `bench run-tests` chạy song song tạo data mới tại 14:31 → phải cleanup vòng 2.

```bash
# Maintenance mode chặn UI/API
bench --site <site> set-maintenance-mode on

# Sau khi xong:
bench --site <site> set-maintenance-mode off
```

Tối thiểu: không kick `bench run-tests` ở terminal khác trong lúc cleanup.

## Distinguishing test fixtures vs real data

Patterns KHÔNG match generic 'test' nhưng vẫn là test fixture — phải hỏi user trước khi xoá:

| Pattern | Nguồn gốc | VD |
|---|---|---|
| `_Diag Asset N` | Frappe diagnostic tests (`_` prefix) | `_Diag Asset 1..6` |
| `Foo — ICU-decom/-pm/-event/-trans` | Workflow scenario tests | `Dräger Evita V500 — ICU-decom` |
| `InhAsset {hex}` / `OvrAsset {hex}` | Inheritance/cascade test | `InhAsset b33459` |
| `Foo (Import {N})` | Import wizard test | `Asset (Import 61525)` |

→ `AskUserQuestion` với 3 options: xoá / xoá một phần / giữ lại.

## Step 7: Cleanup helper scripts

```bash
rm assetcore/_scan_*.py assetcore/_delete_*.py
```
KHÔNG commit script tạm. Prefix `_` đảm bảo `git status` thấy ngay.

## Anti-patterns đã gặp (KHÔNG lặp lại)

1. **LIKE wildcard không escape** — `'_%'` match toàn bảng.
2. **Đoán tên cột** — `WHERE serial_no=...` khi cột thật là `gmdn_code`. → Phải DESCRIBE trước.
3. **Xoá master trước child** — FK orphan, broken refs. → Theo thứ tự ở table trên.
4. **Restore khi không có root pw** → site DB user + extract table.
5. **Xoá vòng 1 khi tests đang chạy** → maintenance-mode trước.

Reference: `assetcore-be` LL-BE-21, LL-BE-22.
