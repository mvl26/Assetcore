# Production Deployment (Phần 2)

> Heavy reference moved from `SKILL.md`. Environment topology, first-install runbook, pre-deploy checklist, update runbook, smoke validation, fixtures import, backup & rollback, supervisor/nginx, release versioning. Mọi runbook step PRESERVED verbatim — không bỏ bước.

## Environment topology
```
Dev:       miyano (local, developer_mode=1)
Staging:   multi-site, 1 site per hospital (QA/UAT)
Prod:      1 bench per customer, 1 site per hospital tenant
```

## Setup lần đầu — cài app lên site (runbook THẬT, đã verify)
```bash
# 1. Clone vào thư mục apps (KHÔNG dùng bench get-app nếu muốn kiểm soát remote)
cd ~/frappe-bench
git clone <repo-url> apps/assetcore

# 2. Editable install vào virtualenv của bench — BƯỚC HAY BỊ QUÊN, thiếu nó
#    Python không import được app khi bench start.
./env/bin/pip install -e apps/assetcore

# 3. Đăng ký app: thêm dòng `assetcore` vào sites/apps.txt
#    (echo assetcore >> sites/apps.txt  — nếu chưa có)

# 4. Install lên site + migrate + build + clear cache
bench --site <site> install-app assetcore
bench --site <site> migrate
bench build
bench --site <site> clear-cache

# 5. nginx (chỉ production — symlink config bench tự sinh vào nginx)
sudo ln -sbf ~/frappe-bench/config/nginx.conf /etc/nginx/conf.d/frappe-bench.conf
sudo systemctl restart nginx

# 6. Restart processes
bench restart

# 7. FE SPA build (KHÁC bench build — xem ⚠️ dưới)
cd ~/frappe-bench/apps/assetcore/frontend && npm install && npm run build
```
> `bench get-app <repo-url>` làm gộp bước 1+2 (clone + pip install). Runbook trên
> tách tay để kiểm soát remote/branch — cả hai đều hợp lệ.

## Pre-deployment checklist (KHÔNG skip bất kỳ item nào)
- [ ] Code trên release branch (vd: `release/wave-2`), tagged `v3.x.y`
- [ ] Tests green: `bench --site <staging> run-tests --app assetcore`
- [ ] Workflow smoke test green: `--module assetcore.tests.test_workflows`
- [ ] FE typecheck: `cd frontend && npm run typecheck && npm run lint`
- [ ] FE build: `npm run build` exit 0
- [ ] Không có whitelist endpoint mới thiếu permission gate
- [ ] Patches mới đã thêm vào `patches.txt` và test trên fresh site
- [ ] DB backup confirmed xong trước khi chạy migrate prod

## Update app — deploy bản mới (runbook THẬT, đã verify)
```bash
cd ~/frappe-bench

# 0. BẮT BUỘC backup trước (release đổi schema/field) + maintenance mode
bench --site <site> backup --with-files          # verify .sql.gz size > 0
bench --site <site> set-maintenance-mode on

# 1. Pull code app (CHỈ assetcore, không kéo theo frappe/erpnext)
bench update --pull --apps assetcore

# 2. bench build (gói asset Frappe desk — KHÔNG bắt buộc nếu không lỗi)
bench build

# 3. Migrate (patches + reload DocType/workflow/field JSON)
bench --site <site> migrate

# 4. Restart (nạp code Python + scheduler mới — gunicorn --preload không tự nạp)
bench restart

# 5. FE SPA build — BƯỚC RIÊNG, KHÁC bench build (xem ⚠️)
cd ~/frappe-bench/apps/assetcore/frontend && npm run build

# 6. Tắt maintenance mode
cd ~/frappe-bench && bench --site <site> set-maintenance-mode off
```

> **⚠️ `bench build` ≠ FE build.** `bench build` chỉ bundle asset desk của Frappe.
> Vue SPA của AssetCore (`frontend/`) phải build RIÊNG bằng `npm run build`; output
> bị gitignore nên `bench update --pull` KHÔNG mang theo → quên bước 5 = FE chạy code cũ.
>
> **`bench update` chạy CHỌN-BƯỚC theo cờ:** truyền `--pull` thì CHỈ git pull (vì vậy
> phải `build`/`migrate`/`restart` riêng ở bước 2-4). `bench update` không cờ = làm hết
> (pull+build+migrate+restart) nhưng kéo cả frappe/erpnext — tránh trên prod.
>
> **⚠️ RBAC capability cache `ac_caps::*` (stale-safe — USER REWORK IMM-14, 2026-06-04).**
> Sau khi thêm capability mới (vd `decommission.*` trong `services/shared/rbac.py::CAPABILITY_MAP`):
> - **`bench migrate` (bước 3) TỰ bust** `ac_caps::*` — `after_migrate` → `_bust_capability_cache()`
>   → `rbac.invalidate_capabilities()` (idempotent, best-effort log_error; in `[AssetCore] ac_caps::*
>   busted (cap-set vN.<hash>)`) → cap mới có hiệu lực ngay lần `get_capabilities` đầu tiên, KHÔNG đợi
>   TTL Redis 1h. (Wired: `assetcore/setup/install.py::after_migrate` sau `_apply_core_permissions`.)
> - **`bench restart` (bước 4) BẮT BUỘC** — gunicorn `--preload` worker cũ giữ `CAPABILITY_MAP` cũ
>   trong RAM; thiếu restart → `api.imm14.create_decommission` deny `decommission.create`
>   (stale-safe: trả 403 VI, KHÔNG còn 500 KeyError sau fix AC1).
> - **Hot-add KHÔNG qua migrate** (sửa DocPerm/Role runtime ở `/app`): hook `role_hooks.invalidate_caps`
>   tự bust theo User/Has Role/Role Profile. Nếu đổi chính `CAPABILITY_MAP` (code) mà không migrate
>   → thủ công: `bench restart` (reload worker) + `bench --site <site> execute assetcore.services.shared.rbac.invalidate_capabilities`.
> - **Version-stamp (AC4):** `get_capabilities` nhúng `__cap_version` = `rbac.CAP_SET_VERSION`
>   (`vN.<sha256[:12]>` của sorted(CAPABILITY_MAP) — TỰ đổi khi thêm/đổi tên cap, KHÔNG bump tay BE).
>   FE store `auth.ts::CAP_SET_VERSION` PHẢI khớp giá trị này (SoT = BE; lấy bằng
>   `bench --site <site> execute assetcore.services.shared.rbac._compute_cap_set_version`). Khi cap-set
>   đổi → cập nhật hằng số FE cho khớp → persisted-caps cũ ở localStorage tự invalidate (init-time
>   `isCapCacheStale`), nút gate render sau reload mà KHÔNG cần xóa localStorage tay. `__cap_version` là
>   field PHỤ trong caps dict (str, không phải bool) → consumer cũ đọc `caps[x]===true` KHÔNG vỡ shape.

## Smoke validation sau deploy
```bash
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_workflows
bench --site <site> scheduler status        # phải "enabled" thì cron mới fire
```

## Fixtures import trên fresh site
```bash
bench --site <new-site> install-app assetcore
bench --site <new-site> execute assetcore.setup.install.after_install
# Verify workflows loaded:
bench --site <new-site> execute "frappe.get_all('Workflow', pluck='name')"
```

## Backup & Rollback
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

## supervisor/nginx (production only)
```bash
# Config files (auto-generated bởi bench setup nginx / bench setup supervisor)
cat ~/frappe-bench/config/supervisor.conf
cat ~/frappe-bench/config/nginx.conf

# Symlink nginx config bench-sinh vào nginx rồi restart (cách dùng thật)
sudo ln -sbf ~/frappe-bench/config/nginx.conf /etc/nginx/conf.d/frappe-bench.conf
sudo nginx -t && sudo systemctl restart nginx       # -t test config trước

# Reload sau thay đổi config (không downtime như restart)
sudo supervisorctl reload
sudo nginx -s reload
```

## Release versioning
```
v3.0.0 — Wave 1 (IMM-04,05,08,09,11,12)
v3.1.0 — Wave 2 (IMM-01,02,03,06,15,16)
v3.2.0 — Wave 3 (IMM-07,10,13,14,17)
```
Bump `assetcore/__version__.py` + git tag `vX.Y.Z` + release note.
