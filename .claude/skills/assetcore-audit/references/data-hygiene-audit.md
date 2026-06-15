# assetcore-audit — Data Hygiene Audit (heavy reference)

> Phần 3 — Data Hygiene Audit (DH-1..DH-4): pre-release MUST-CHECK. `SKILL.md` trỏ tới đây + đưa DH-1..4 vào Verification gate. Áp dụng trước mỗi release tag, deploy lên staging/prod, hoặc khi user nói "data có sạch không".

## DH-1: 0 record chứa pattern test trong production-bound site

```bash
bench --site <site> mariadb -e "
SELECT 'AC Asset' AS dt, COUNT(*) FROM \`tabAC Asset\`
  WHERE LOWER(name) LIKE '%test%' OR LOWER(asset_name) LIKE '%test%'
UNION ALL SELECT 'AC Warehouse', COUNT(*) FROM \`tabAC Warehouse\`
  WHERE LOWER(name) LIKE '%test%' OR LOWER(warehouse_name) LIKE '%test%'
UNION ALL SELECT 'AC Spare Part', COUNT(*) FROM \`tabAC Spare Part\`
  WHERE LOWER(name) LIKE '%test%' OR LOWER(part_name) LIKE '%test%'
UNION ALL SELECT 'IMM Training Session', COUNT(*) FROM \`tabIMM Training Session\`
  WHERE training_program LIKE '\\_TEST-%'
UNION ALL SELECT 'IMM Training Program', COUNT(*) FROM \`tabIMM Training Program\`
  WHERE name LIKE '\\_TEST-%' OR LOWER(program_name) LIKE '%test%'
UNION ALL SELECT 'IMM CAPA Record', COUNT(*) FROM \`tabIMM CAPA Record\`
  WHERE LOWER(_comments) LIKE '%test%' OR LOWER(_comments) LIKE '%_test%';"
```

Tất cả phải = 0. Nếu > 0 → `assetcore-deploy` Phần 3 cleanup checklist.

## DH-2: 0 orphan FK reference

Sau cleanup, masters bị xoá có thể để lại dependents trỏ NULL:

```sql
SELECT 'ALE orphan asset' AS chk, COUNT(*) FROM `tabAsset Lifecycle Event`
WHERE asset IS NOT NULL AND asset != '' AND asset NOT IN (SELECT name FROM (SELECT name FROM `tabAC Asset`) x)
UNION ALL SELECT 'Audit Trail orphan asset', COUNT(*) FROM `tabIMM Audit Trail`
WHERE asset IS NOT NULL AND asset != '' AND asset NOT IN (SELECT name FROM (SELECT name FROM `tabAC Asset`) x)
UNION ALL SELECT 'Spare Stock orphan part', COUNT(*) FROM `tabAC Spare Part Stock`
WHERE spare_part IS NOT NULL AND spare_part != '' AND spare_part NOT IN (SELECT name FROM (SELECT name FROM `tabAC Spare Part`) x)
UNION ALL SELECT 'Asset orphan category', COUNT(*) FROM `tabAC Asset`
WHERE asset_category IS NOT NULL AND asset_category != '' AND asset_category NOT IN (SELECT name FROM (SELECT name FROM `tabAC Asset Category`) x);
```

Tất cả phải = 0.

## DH-3: 0 record vi phạm required-field constraint

```python
# assetcore/_scan_incomplete.py
import frappe

def run():
    modules = frappe.get_all("Module Def", filters={"app_name": "assetcore"}, pluck="name")
    doctypes = [d.name for d in frappe.get_all("DocType",
                filters={"module": ["in", modules]},
                fields=["name", "istable", "issingle"])
                if not d.istable and not d.issingle]
    skip = {"naming_series", "amended_from"}
    for dt in doctypes:
        meta = frappe.get_meta(dt)
        reqd = [f.fieldname for f in meta.fields
                if f.reqd == 1 and f.fieldname not in skip
                and frappe.db.has_column(dt, f.fieldname)
                and f.fieldtype not in ("Table", "Table MultiSelect",
                                         "Section Break", "Column Break", "HTML")]
        for f in reqd:
            cnt = frappe.db.sql(
                f"SELECT COUNT(*) FROM `tab{dt}` WHERE `{f}` IS NULL OR `{f}` = ''"
            )[0][0]
            if cnt:
                print(f"  {dt}.{f}: {cnt} empty")
```

```bash
bench --site <site> execute assetcore._scan_incomplete.run
```

Pre-release: phải = 0 cho field reqd=1.

## DH-4: 0 record có docstatus mismatch với workflow_state

```sql
-- Submitted nhưng còn ở Draft, Cancelled mà chưa Cancel
SELECT name, docstatus, workflow_state
FROM `tabAsset Repair`
WHERE (docstatus = 1 AND workflow_state IN ('Draft', 'Open'))
   OR (docstatus = 2 AND workflow_state NOT IN ('Cancelled'));
```

## Audit verdict — thêm row Data Hygiene

| Item                                       | Check            | Tool              |
| ------------------------------------------ | ---------------- | ----------------- |
| DH-1: zero test records                    | DH-1 SQL above   | `bench mariadb` |
| DH-2: zero orphan FK                       | DH-2 SQL above   | `bench mariadb` |
| DH-3: zero empty required fields           | DH-3 Python scan | `bench execute` |
| DH-4: docstatus ↔ workflow_state coherent | DH-4 SQL above   | `bench mariadb` |

## Cross-reference (mở rộng bảng E)

| Pattern phát hiện                        | Skill fix                                 | Reference         |
| ------------------------------------------ | ----------------------------------------- | ----------------- |
| `Unknown column 1054` raw SQL            | `assetcore-be`                          | LL-BE-22          |
| `not enough arguments for format string` | `assetcore-be`                          | LL-BE-21          |
| Xoá nhầm > scope dự kiến (LIKE bug)    | `assetcore-be` + `assetcore-deploy`   | LL-BE-21, Phần 3 |
| Test data tích luỹ trong DB              | `assetcore-test` + `assetcore-deploy` | R-9 + Phần 3     |
| Orphan FK sau cleanup                      | `assetcore-deploy`                      | Phần 3 step 5    |
| `bench restore` blocked (no root pw)     | `assetcore-deploy`                      | Phần 3 "Restore" |
| Empty required field trên real data       | `assetcore-be` LL-BE-9                  | Completion gate   |

Reference: `assetcore-deploy` Phần 3; `assetcore-test` R-9, R-10.
