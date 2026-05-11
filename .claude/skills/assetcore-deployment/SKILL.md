---
name: assetcore-deployment
description: Plan and execute production / staging deployment of AssetCore — site provisioning, install order, FE build, fixtures import, supervisor / nginx, backup & rollback, smoke validation, release versioning. Use when the user says "deploy", "lên prod", "release", "rollback", "go-live", "production", "staging", "khi triển khai cho khách hàng", "site mới cho bệnh viện X", "supervisor", "nginx", "config server". Strongly prefer this skill before suggesting any production-impacting command.
---

# AssetCore Deployment Engineer

Deployments to production sites (hospitals) must be reproducible, reversible, and validated. Every step is explicit; no clever automation that hides what's happening.

## Environment topology

```
Dev:       miyano (local site, developer_mode=1)
Staging:   one bench, multiple sites for QA/UAT (one per upcoming hospital)
Prod:      one bench per customer, one site per hospital tenant
```

Every site has its own DB and `site_config.json`. Deployment never copies prod data sideways.

## Pre-deployment checklist

Before triggering anything against staging or prod:

- [ ] Code is on the release branch (e.g., `release/wave-2`), tagged `v3.x.y`.
- [ ] All tests green: `bench --site <staging> run-tests --app assetcore`
- [ ] All workflows green: `bench --site <staging> run-tests --app assetcore --module assetcore.tests.test_workflows`
- [ ] FE typecheck clean: `cd frontend && npm run typecheck && npm run lint`
- [ ] FE production bundle builds: `npm run build` exits 0
- [ ] No new whitelisted endpoint without permission gate (run security skill)
- [ ] New patches added to `patches.txt` and tested on a fresh site
- [ ] Fixtures exported and committed: `bench --site <site> export-fixtures --app assetcore`
- [ ] Release notes drafted (see template below)
- [ ] User authorization recorded for the deploy window

## Deploying to an existing site

```bash
cd /home/miyano/frappe-bench

# 1. Take backup BEFORE any change (mandatory)
bench --site <site> backup --with-files
# Verify backup landed in sites/<site>/private/backups/

# 2. Pull code
cd apps/assetcore
git fetch origin
git checkout v3.x.y     # use tag, not branch, in prod
cd ../..

# 3. Install dependencies (Python only changes)
bench setup requirements --python

# 4. Build FE if frontend changed
cd apps/assetcore/frontend
npm ci                  # not `npm install` — use lockfile
npm run build
cd ../../..

# 5. Migrate (runs patches + reloads JSON + reapplies fixtures)
bench --site <site> migrate

# 6. Clear cache + restart workers
bench --site <site> clear-cache
bench restart

# 7. Smoke check (workflow + role + fixture sanity)
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_workflows
```

**Stop and rollback if any step fails.** Don't proceed past a red error.

## Provisioning a new site (new hospital tenant)

```bash
cd /home/miyano/frappe-bench

# 1. Create site
bench new-site <hospital>.example.vn \
    --db-name <hospital>_db \
    --admin-password <password>     # store in vault, not chat

# 2. Install ERPNext FIRST (hard dep)
bench --site <hospital>.example.vn install-app erpnext

# 3. Install AssetCore (this triggers after_install + fixtures)
bench --site <hospital>.example.vn install-app assetcore

# 4. Run migrate to apply all patches
bench --site <hospital>.example.vn migrate

# 5. Configure scheduler
bench --site <hospital>.example.vn scheduler enable
bench --site <hospital>.example.vn scheduler resume

# 6. Apply per-site config
bench --site <hospital>.example.vn set-config developer_mode 0
bench --site <hospital>.example.vn set-config server_script_enabled 0
bench --site <hospital>.example.vn set-config encryption_key '<base64>'   # for sensitive stored fields

# 7. Add to nginx
bench setup nginx
sudo systemctl reload nginx

# 8. Smoke
bench --site <hospital>.example.vn console
>>> import frappe
>>> frappe.get_all("Workflow", filters={"is_active": 1})
# Expect 8 workflows for Wave 1 (more once Wave 2 ships). If short, fixtures didn't import.
>>> frappe.db.count("Role", {"name": ("like", "IMM%")})
# Expect 19 (13 Wave 1 + 6 Wave 2). If short, role fixture missing.
```

## Install order matters

`hooks.py` `after_install` runs:
1. Roles + Role Profiles fixtures (auto from fixtures list).
2. `setup_permissions.run()` — DocPerm matrix.
3. `setup_core_permissions.run()` — ERPNext core overlays.
4. `setup_role_profiles.run()`, `setup_module_profiles.run()`.
5. SLA policies, default workspaces.

If you add a new step, insert it in `assetcore/setup/install.py:after_install` in the right place — don't re-order existing.

## Supervisor / nginx

Production uses supervisor for processes and nginx for HTTP. Bench manages config:

```bash
sudo bench setup production frappe   # one-time bootstrap
bench setup supervisor               # regenerate supervisor.conf
bench setup nginx                    # regenerate nginx config
sudo supervisorctl reload
sudo systemctl reload nginx
```

Process units:
- `frappe-bench-frappe-web` (gunicorn)
- `frappe-bench-frappe-schedule` (one per bench)
- `frappe-bench-frappe-default-worker-N`
- `frappe-bench-frappe-short-worker-N`
- `frappe-bench-frappe-long-worker-N`
- `frappe-bench-redis-cache`, `redis-queue`, `redis-socketio`

If a worker is OOM-killed, `supervisorctl restart frappe-bench:` to revive.

## Rollback procedure

```bash
# 1. Restore code
cd /home/miyano/frappe-bench/apps/assetcore
git checkout v3.x.y-1     # previous tag

# 2. Restore DB from the pre-deploy backup
cd /home/miyano/frappe-bench
bench --site <site> --force restore \
    sites/<site>/private/backups/<timestamp>-*-database.sql.gz \
    --with-public-files sites/<site>/private/backups/<timestamp>-files.tar \
    --with-private-files sites/<site>/private/backups/<timestamp>-private-files.tar

# 3. Migrate (no-op if same tag)
bench --site <site> migrate

# 4. Restart
bench --site <site> clear-cache
bench restart
```

**Rollback requires explicit user authorization.** Auto mode does not authorize destructive restore.

## Release versioning

- Tag commits on `master` only. `v<major>.<minor>.<patch>`.
- `major` bumps for breaking schema changes (= patches that drop/rename columns).
- `minor` bumps for new IMM modules / waves.
- `patch` for bug fixes / non-schema changes.

Release branch lives until the version is sunset — don't delete prematurely.

## Release notes template

```markdown
## v3.X.Y — YYYY-MM-DD

### Highlights
- IMM-XX module ready for production
- ...

### Schema changes (run `bench migrate`)
- New DocType: `<name>`
- New patch: `assetcore.patches.v3_X.NNN_<name>`

### Breaking changes
- Renamed `<doctype>.<old>` → `<new>` (handled by patch NNN)

### Fixtures changed
- Added 2 new workflow states; rerun fixtures import on every site

### Migration steps
1. backup
2. pull code at v3.X.Y
3. `bench migrate`
4. `bench restart`

### Known issues
- ...

### Rollback to vN-1: `bench restore <pre-deploy backup>`
```

## Frontend deploy

The FE bundle is built into `frontend/dist/` and served by Frappe via the app-mounted directory. The build step (`npm run build`) emits hashed asset filenames so cache-busting is automatic. Important:

- **Always `npm ci`, not `npm install`**, in production builds — uses lockfile, deterministic.
- Build on a CI runner or staging box, not the prod server, when you can.
- After deploy, hard-refresh in browser (`Ctrl+Shift+R`) to confirm new bundle loads.

## Smoke validation

Two layers exist already; use them in deploy step 7:

1. **`tests/test_workflows.py`** — checks every workflow is registered, active, has expected state/transition counts, and respects Frappe docstatus rules. Run via `bench run-tests --module assetcore.tests.test_workflows`.
2. **`tests/test_imm00.py`** — checks foundation DocTypes (Category, Department, Location, Supplier) are creatable.

**If Wave 2 modules ship without their own `test_immXX.py`,** add a minimal `assetcore/scripts/uat/uat_smoke.py`:

```python
def run():
    import frappe
    assert frappe.db.count("Workflow", {"is_active": 1}) >= 8, "fewer workflows than expected"
    assert frappe.db.count("Role", {"name": ("like", "IMM%")}) >= 19, "missing IMM roles"
    print("✓ smoke ok")
```

Run via `bench --site <site> execute assetcore.scripts.uat.uat_smoke.run`. If it fails — rollback.

## Common deployment issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `bench migrate` hangs on a patch | Patch not idempotent, retrying same row | Read patch, add idempotency guard, re-run |
| Workflow missing on prod after deploy | Fixture not exported | `bench export-fixtures` on dev, commit, redeploy |
| FE shows white screen | Old `dist/` cached | Hard refresh; verify bundle filenames changed |
| 500 on every API call | Worker didn't restart | `bench restart` |
| Permission denied for normal user | DocPerm fixture not imported | Check `fixtures/has_role.json` made it; rerun setup |
| Scheduler not firing | Scheduler disabled by default on new site | `bench --site X scheduler enable && resume` |
| Backup fails out of disk | `/sites/<site>/private/backups` filled | Rotate old backups; backup writes to disk before compressing |

## Safety rules

- **Never** deploy to prod without an authorized window and a fresh backup.
- **Never** run a destructive command (`drop-site`, `restore`, `force-push`) without explicit user confirmation. Auto mode does not grant authorization.
- **Never** edit prod fixtures by hand. If something is wrong → fix on dev, export, redeploy.
- **Never** disable `developer_mode=0` in prod (it must stay 0 to prevent JSON hot-reload exploits).

## Where to look

- `assetcore/setup/install.py` — install/migrate orchestration
- `assetcore/patches.txt` + `assetcore/patches/` — version history
- `frappe-bench/config/` — supervisor, nginx, redis configs
- `frappe-bench/sites/<site>/site_config.json` — per-site config
- `frappe-bench/sites/<site>/private/backups/` — backup destination

---

## Cross-skill conventions

Read [`/.claude/skills/CONVENTIONS.md`](../CONVENTIONS.md) for project-wide rules. Especially relevant to this skill:

- §9. Wave-aware — Wave 3 (IMM-15/16) DocTypes scaffolded but workflows + fixtures need fixture export
- §7. Documentation Sync — release notes must list new DocTypes, workflows, fixtures, ErrorCodes

### Module-specific gotchas
- Pre-deploy: count workflows in `assetcore/workflow/` against test_workflows.py expectations
- Wave 1 workflows: 8 active. Wave 2 adds 7 (imm-01 needs/plan, imm-02 spec, imm-03 avl/decision/vendor_eval, imm-06 session/competency). Wave 3 adds 8 (imm-15 alloc/cycle_count, imm-16 finding/audit/capa/mr).
- Fixture import order matters: roles → role_profiles → custom fields → workflows
- Backup before migrate: `bench --site <site> backup`
