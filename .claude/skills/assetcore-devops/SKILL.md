---
name: assetcore-devops
description: Run bench operations, manage migrations, write patches, configure fixtures, troubleshoot site state for AssetCore. Use whenever the user mentions "bench", "migrate", "install-app", "fixture export", "patch", "phiên bản v3.x", "site bị lỗi", "rebuild assets", "clear cache", "reset DB", "scheduler", "log không thấy", or anything that's an operational concern rather than a feature change. Strongly prefer this skill before suggesting destructive commands like drop-site, reset, or force-pushing fixtures.
---

# AssetCore DevOps

Bench is the command surface for everything outside the codebase. AssetCore lives at `/home/miyano/frappe-bench/apps/assetcore/`. The default site (referenced in CLAUDE.md examples) is `miyano`.

## Cheat sheet — daily commands

```bash
# Working directory: bench root (NOT app root)
cd /home/miyano/frappe-bench

bench start                              # run all services (web, worker, scheduler, redis)
bench --site miyano console              # interactive Python with frappe context
bench --site miyano migrate              # run pending patches + reload DocType/workflow JSON
bench --site miyano clear-cache          # clear Redis cache (after JSON edit if migrate skipped)
bench --site miyano reload-doctype "Asset Repair"   # reload a single DocType
bench --site miyano reload-doc assetcore workflow imm_09_repair_workflow   # reload a workflow
bench --site miyano execute assetcore.setup.install.after_install
bench --site miyano list-apps
bench restart                            # restart supervisor processes (production)
bench build --app assetcore              # rebuild JS/CSS bundles (FE owned by app)
```

## Migration model

The codebase uses **versioned patches** in `assetcore/patches/`. Real layout (May 2026):

```
assetcore/patches/
├── __init__.py
├── v3_0/
│   └── 001_migrate_from_v2.py    # drop v2 sidecars + custom_imm_* fields
└── v3_1/
    └── ...                       # subsequent migrations
```

And a manifest at `assetcore/patches.txt`:

```
[pre_model_sync]
# patches that run before model schema is synced

[post_model_sync]
assetcore.patches.v3_0.001_migrate_from_v2
# add new patch entries here, in chronological order
```

**Rules:**
- One patch = one cohesive change. Never edit a shipped patch — write a new one.
- The patch must be idempotent: running twice is a no-op.
- `frappe.db.commit()` at the end if you do raw SQL.
- Append to `patches.txt`; never reorder existing entries.

### Patch template

```python
"""v3_1.002_add_workshop_lead_to_imm_repair: backfill assigned_to from old field."""
import frappe


def execute():
    if not frappe.db.has_column("tabAsset Repair", "legacy_assigned_user"):
        return  # already migrated; idempotent

    frappe.db.sql("""
        UPDATE `tabAsset Repair`
        SET assigned_to = legacy_assigned_user
        WHERE assigned_to IS NULL AND legacy_assigned_user IS NOT NULL
    """)
    frappe.db.commit()
```

## Fixtures

Defined in `assetcore/hooks.py` under `fixtures = [...]`. They're **exported** with:

```bash
bench --site miyano export-fixtures --app assetcore
```

This writes JSON into `assetcore/fixtures/<doctype>.json`. **Always commit the diff** — fixtures are the source of truth on fresh sites.

**Real fixtures list (from `hooks.py`):**
- `Role` — 19 IMM roles (Wave 1 + Wave 2)
- `Role Profile` — 19 named bundles
- `Has Role` — bundle membership rows tied to Role Profiles
- `Module Profile` — 3 (`IMM - Standard`, `IMM - Admin`, `IMM - Vendor`)
- `IMM SLA Policy`
- `Workspace` — `IMM Operations`
- `Workflow` — 8 wave-1 workflows (`AC Asset Lifecycle`, `IMM-04`, `IMM-05`, `IMM-08 PM`, `IMM-09 Repair`, `IMM-11 Calibration`, `IMM-12 Incident`, `IMM-12 RCA`)
- `Workflow State` — every unique state name across all workflows (Open, Assigned, Diagnosing, Pending Parts, In Repair, …)
- `Workflow Action Master` — every Vietnamese button label

**Fixture rules:**
- Exclude transactional / per-site data. Only seed data goes in fixtures.
- Filter by name to avoid hoovering the whole DocType:
  ```python
  {"dt": "Workflow", "filters": [["name", "in", [...]]]}
  ```
- After editing fixtures → run migrate on every dev site to import.
- **Adding a new workflow** means updating THREE filter lists: `Workflow`, `Workflow State` (every new state name), and `Workflow Action Master` (every new action label). Forgetting any of the three breaks fresh-site provisioning.

## Hooks dispatch order

`assetcore/hooks.py` wires into Frappe lifecycle:

```python
after_install = "assetcore.setup.install.after_install"   # one-time
after_migrate = "assetcore.setup.install.after_migrate"   # every migrate
doc_events = {"<DocType>": {"before_save": "..."}}
scheduler_events = {"hourly": [...], "daily": [...]}
fixtures = [...]
permission_query_conditions = {"<DocType>": "module.fn"}
has_permission = {"<DocType>": "module.fn"}
```

`after_install` runs **once** when the app is installed; it should be idempotent (in case someone reinstalls). `after_migrate` runs every `bench migrate`; keep it cheap and idempotent.

## Site lifecycle commands

```bash
# Fresh dev site
bench new-site mysite --db-name mysite_db --admin-password admin
bench --site mysite install-app erpnext        # ERPNext is a hard dep
bench --site mysite install-app assetcore
bench --site mysite migrate                    # apply patches
bench --site mysite set-config developer_mode 1   # for hot reload of JSON

# Reset (destructive — confirm with user)
bench --site mysite drop-site --root-password X --db-root-username root

# Backup before risky operation
bench --site mysite backup --with-files
```

**Never run `drop-site` without explicit user authorization.** Auto mode does not authorize destructive actions.

## Scheduler

```bash
bench --site miyano scheduler enable
bench --site miyano scheduler resume
bench --site miyano enable-scheduler-events
bench doctor                          # check scheduler + worker health
```

Scheduled jobs are wired in `hooks.py`:
```python
scheduler_events = {
    "hourly": ["assetcore.services.imm09.update_overdue_status"],
    "daily": ["assetcore.services.imm08.generate_pm_work_orders"],
}
```

For one-off async work, use `frappe.enqueue("module.fn", queue="default", timeout=600, **kwargs)`.

## Logs

```bash
tail -f /home/miyano/frappe-bench/logs/web.log
tail -f /home/miyano/frappe-bench/logs/worker.log
tail -f /home/miyano/frappe-bench/logs/scheduler.log
bench --site miyano show-config            # site config (DB host, redis URLs)
```

In code, log with:
```python
frappe.logger().info({"event": "wo.assigned", "wo": doc.name})
frappe.log_error("Repair close failed", reference_doctype="Asset Repair", reference_name=doc.name)
```

`frappe.log_error` writes to the `Error Log` DocType — visible in desk for non-dev users.

## Frontend build pipeline

```bash
cd /home/miyano/frappe-bench/apps/assetcore/frontend
npm install            # only on first checkout / package.json change
npm run dev            # vite dev server with HMR; proxies /api to bench
npm run typecheck      # vue-tsc --noEmit
npm run lint           # eslint
npm run build          # production bundle (dist/) — for prod sites
```

The Vite dev server expects `bench start` running for `/api/method` proxy to work. Don't start them in series — run `bench start` in one terminal and `npm run dev` in another.

## Common operations

### "I edited a DocType JSON, why isn't it visible?"
Either run `bench --site miyano migrate` or for a single one `bench --site miyano reload-doctype "Asset Repair"` then `bench --site miyano clear-cache`.

### "I edited a Workflow JSON, the badge didn't update"
`bench --site miyano migrate` reimports the workflow JSON. If the state name was renamed, also update `Workflow State` fixtures in hooks.py and re-export.

### "Fixtures don't import on a fresh site"
Check `assetcore/fixtures/` actually has the JSON. If it doesn't, you forgot to run `bench export-fixtures`.

### "Test data leaks into desk"
You forgot `_Test` prefix on test records, or `tearDown` doesn't clean them up. Search desk for `_Test` and bulk delete; fix the test.

### "Scheduler events aren't firing"
- Run `bench --site miyano scheduler enable && bench --site miyano scheduler resume`.
- Confirm `developer_mode` is on (it skips scheduling otherwise on some configs).
- Check `logs/scheduler.log` for tracebacks.

### "Server returns stale code after edit"
Python: bench reloads on file change in dev mode. If not, `bench restart` or `kill -HUP` the gunicorn workers. Production needs `bench restart` always.

## Safety rules (from CLAUDE.md and Auto mode)

- **Never** run `drop-site`, `reset --hard`, `force-push`, or `migrate --force` without explicit user OK.
- **Always** `bench --site <site> backup` before destructive operation if user authorizes one.
- **Never** edit fixtures by hand — go through desk + `export-fixtures` so the dev site state matches the file.
- **Never** modify ERPNext/Frappe core (CLAUDE.md §19). If you find yourself wanting to, write a patch instead.

## Where to look

- `assetcore/hooks.py` — fixtures list, hooks, scheduler
- `assetcore/patches.txt` + `assetcore/patches/` — migration history
- `assetcore/setup/install.py` — `after_install` and `after_migrate` orchestration
- `assetcore/setup/setup_permissions.py` — runtime permission setup (idempotent)
- `frappe-bench/sites/<site>/site_config.json` — per-site config (DB, Redis, etc.)
- `frappe-bench/common_site_config.json` — shared config
