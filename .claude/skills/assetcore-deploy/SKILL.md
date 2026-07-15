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

## Overview

Skill này bao 3 phạm vi: **DevOps hàng ngày (bench operations)** + **Production Deployment** + **Destructive DB Operations**. Nguyên tắc cốt lõi: **mọi lệnh đổi schema/data/worker là HARD-STOP user** (reload/restart/migrate/site_config/destructive — BE đề xuất, KHÔNG tự chạy) và **không bao giờ destructive mà thiếu backup + dry-run + user-approve**.

## When to Use

- Bench operations hàng ngày: migrate, clear-cache, reload-doctype, build, restart, fixtures export.
- Provisioning site mới / cài app lần đầu cho khách hàng / bệnh viện X (→ [references/production-deployment.md](references/production-deployment.md)).
- Deploy bản mới lên prod/staging, release versioning, backup/rollback, supervisor/nginx.
- Troubleshoot site lỗi: DocType không áp dụng, workflow button mất, FE chạy code cũ, scheduler không chạy, `AttributeError` sau whitelist, "417 sau khi vừa sửa code".
- Email/SMTP không gửi, Email Queue flush, "chuông trống / không nhận thông báo", set password user (→ [references/maintenance-and-email.md](references/maintenance-and-email.md)).
- Dọn data rác / mass-delete / reset bảng / restore từ backup / rollback DB (→ [references/destructive-db-ops.md](references/destructive-db-ops.md)).
- **KHÔNG dùng khi**: viết code BE/data model (→ `assetcore-be`), viết/chạy test logic (→ `assetcore-test`), tạo git commit (→ `assetcore-commit`), viết docs (→ `assetcore-doc`).

---

## Process — phân nhánh theo loại op rồi gate backup + verify

Quy trình từng bước (spine — chi tiết ở mục dưới):

1. **Xác định loại op** — bench thường / migrate / destructive / production; chọn nhánh dưới.
2. **Bench op hàng ngày** — migrate, clear-cache, reload-doctype, build, fixtures 3-list → §Phần 1 — DevOps (Bench Operations).
3. **Production deployment** — ci-cd quality gate (Shift Left) + staged rollout 1 site thí điểm → §Phần 2 — Production Deployment, §Phần 3.5 — Named principles (ci-cd · deprecation · shipping).
4. **Destructive DB op** — backup file>0 → dry-run `_scan` → AskUserQuestion → cascade-delete đúng FK → re-scan 0 → §Phần 3 — Destructive DB Operations, §Safety rules.
5. **Deprecation/migration an toàn** — additive trước → cutover → cleanup, mỗi bước 1 patch idempotent → §Phần 3.5 — Named principles (ci-cd · deprecation · shipping).
6. **Lessons LL-DEPLOY** — stale-worker 417 vs guest-403, mobile go-live 4 bước, ngrok expose → §Phần 4 — Lessons Learned (LL-DEPLOY-*).
7. **Verification + rollback-ready** — bằng chứng (backup .sql.gz, run-tests xanh, scheduler enabled) + rollback procedure đã xác định TRƯỚC deploy → §Verification.

> Cross-ref: telemetry/log/alert/health vận hành → skill **assetcore-observe** (KHÔNG ở đây). Reload/restart/migrate/site_config = HARD-STOP user.

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

Thiếu bất kỳ list nào → `bench --site <new-site> migrate` sẽ fail khi load workflow trên fresh site.

### Troubleshoot thường gặp

| Symptom                                                                                                                                                          | Cause                                                                                                                                                                                                                              | Fix                                                                                                                                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DocType change không áp dụng                                                                                                                                  | Quên`bench migrate`                                                                                                                                                                                                             | `bench --site miyano migrate`                                                                                                                                                                                                                                                                                              |
| Workflow action button mất                                                                                                                                      | `Workflow Action Master` fixture thiếu                                                                                                                                                                                          | Thêm action label + export fixtures + migrate                                                                                                                                                                                                                                                                               |
| FE không load sau code change                                                                                                                                   | Vite cache stale                                                                                                                                                                                                                   | `npm run dev --force` hoặc clear `.vite/`                                                                                                                                                                                                                                                                               |
| Scheduler job không chạy                                                                                                                                       | `bench start` không có worker                                                                                                                                                                                                  | Check`bench start` output có `worker` process                                                                                                                                                                                                                                                                           |
| Import error sau deploy                                                                                                                                          | Missing`__init__.py` hoặc syntax error                                                                                                                                                                                          | `python -c "import assetcore.api.immXX"` để verify                                                                                                                                                                                                                                                                       |
| `AttributeError: ... no attribute '<method>'` sau khi thêm `@frappe.whitelist()`                                                                            | gunicorn`--preload` workers cũ chưa nạp code Python mới (2026-06-01 audit AUTH)                                                                                                                                              | `bench restart` (prod) / HUP reload gunicorn; verify `bench execute assetcore.api.X.method` chạy được TRƯỚC khi test qua HTTP/Playwright                                                                                                                                                                           |
| Lỗi "live" sau khi vừa sửa code (vd "Không thể tạo PDF nhãn") + định phóng factory fix                                                                 | Nghi STALE-WORKER trước khi nghi bug code (2026-06-11)                                                                                                                                                                           | `curl -X POST http://localhost:8000/api/method/<dotted.path> -H "Host: <site>" -d '{...}'` → nếu **417 "no attribute '<fn></fn>'"** = stale → **USER `bench restart`** (+ `clear-cache`), **KHÔNG factory/viết-fix** (LL-DEPLOY-07). So `ps … lstart` (boot) vs `stat -c %y *.py` (mtime). |
| `bench migrate` fail                                                                                                                                           | Patch không idempotent                                                                                                                                                                                                            | Read patch file; add guards (`has_column`, `exists`)                                                                                                                                                                                                                                                                     |
| Permission denied sau install                                                                                                                                    | `after_install` không chạy                                                                                                                                                                                                     | `bench --site <site> execute assetcore.setup.install.after_install`                                                                                                                                                                                                                                                        |
| `Field ac_department is referring to non-existing doctype AC Department…` khi mở form User trên desk (cloud)                                                | `AC Department` chưa sync (app_modules cache cũ) nhưng Custom Field `User.ac_department` orphan → see [references/maintenance-and-email.md](references/maintenance-and-email.md) (Troubleshoot — cloud install deep-dives) | → see[references/maintenance-and-email.md](references/maintenance-and-email.md)                                                                                                                                                                                                                                              |
| `install-app` báo `Workflow sync error … DocType <X> not found` cho MỌI doctype + `_seed_uoms` `No module named 'frappe.core.doctype.ac_uom'` (cloud) | `sync_for` sync 0/108 doctype: Redis `app_modules` cache cũ thiếu "assetcore" (`_rebuild_module_map` fix 3 lớp) → see [references/maintenance-and-email.md](references/maintenance-and-email.md)                          | → see[references/maintenance-and-email.md](references/maintenance-and-email.md)                                                                                                                                                                                                                                              |
| Chuông trống / không có thông báo                                                                                                                          | DATA: record toàn do`Administrator` tự tạo+tự gán → self-notify chặn đúng (KHÔNG phải bug)                                                                                                                            | Cần data đa-user (actor ≠ assignee). Xem LL-BE-34 decision tree TRƯỚC khi sửa code                                                                                                                                                                                                                                     |
| Email enqueue nhưng không gửi                                                                                                                                 | Queue`status="Not Sent"` chờ scheduler flush                                                                                                                                                                                    | `Email Queue.send()` trực tiếp (xem [references/maintenance-and-email.md](references/maintenance-and-email.md)) — `bench flush-email-queue` KHÔNG tồn tại trong build này                                                                                                                                          |
| 1 user không nhận email                                                                                                                                        | `Notification Settings.enable_email_notifications=0` hoặc user là `Administrator`                                                                                                                                            | Bật cờ trong Notification Settings của user;`_user_wants_email` luôn chặn Administrator                                                                                                                                                                                                                               |
| Orphan Custom Field trên doctype CORE/ERPNext sau khi uninstall (User, Asset) → form crash`Missing DocType`                                                  | CF tạo với`module=None` bị bỏ lại (`_remove_foreign_customizations` + `_apply_erpnext_asset_custom_fields` PATH bug) → see [references/maintenance-and-email.md](references/maintenance-and-email.md)                   | → see[references/maintenance-and-email.md](references/maintenance-and-email.md)                                                                                                                                                                                                                                              |

### Email / Notification & Maintenance scripts

> Heavy reference: see [references/maintenance-and-email.md](references/maintenance-and-email.md) — SMTP infra & flush THẬT (verify Sent ≠ inbox), set password user test (KHÔNG save full User doc → `LinkExistsError`), maintenance-script pattern chuẩn (`assetcore/_<task>.py` + `bench execute`, parameterized LIKE, cascade-delete audit trước asset), IMM Audit Trail tampering policy (ISO 13485:7.5.9).

---

## Phần 2 — Production Deployment

> Heavy reference: see [references/production-deployment.md](references/production-deployment.md) — environment topology, first-install runbook (clone → `pip install -e` → apps.txt → install-app → migrate → build → nginx → restart → FE `npm run build`), pre-deployment checklist, update-app runbook (backup → maintenance-mode → `bench update --pull` → build → migrate → restart → FE build → maintenance-off), ⚠️ `bench build` ≠ FE build, ⚠️ RBAC `ac_caps::*` cache + `__cap_version`, smoke validation, fixtures import fresh site, backup & rollback, supervisor/nginx, release versioning (v3.0/3.1/3.2).

---

## Phần 3 — Destructive DB Operations (cleanup / mass-delete / restore)

> Heavy reference: see [references/destructive-db-ops.md](references/destructive-db-ops.md) — checklist BẮT BUỘC 7 bước ([1] backup file>0 → [2] dry-run `_scan_xxx.py` → [3] AskUserQuestion → [4] cascade-delete đúng thứ tự FK 9 bậc → [5] orphan sweep SQL → [6] re-scan verify 0 → [7] xoá script tạm), `_safe_delete` cancel-before-delete, restore KHÔNG cần root pw (site DB user + extract table), pause scheduler/maintenance-mode trước mass-delete, fixtures-vs-real-data patterns (`_Diag`/ICU-decom/InhAsset/Import), anti-patterns. LL-BE-21/22.

**Trigger khi user yêu cầu:** "dọn data rác / xoá test data", "reset bảng X / xoá hết record Y", "restore từ backup / rollback DB", bất kỳ `ALTER TABLE`/`UPDATE` bulk. **KHÔNG chạy destructive khi thiếu: backup file>0 + dry-run + user-approve scope.**

---

## Phần 3.5 — Named principles (ci-cd · deprecation · shipping)

> Hút từ agent-skills generic → tailor Frappe/HTM. Nêu tên principle tường minh; áp khi release/migrate/launch.

### CI-CD & automation — quality gate trước deploy

- **Shift Left** — bắt lỗi CÀNG SỚM trong pipeline càng rẻ: static check → test → staging → prod, KHÔNG để bug lọt tới prod. Frappe: chạy `bench --site <site> run-tests --app assetcore` + FE `npm run typecheck && npm run lint && npm run build` ở local/CI TRƯỚC khi `migrate`+`restart` lên prod (sửa schema sai trên prod = data hỏng không cứu).
- **Quality gate = `bench run-tests` xanh + FE build exit 0 trước deploy** — gate KHÔNG được skip; test fail thì SỬA code, KHÔNG `--skip` test. Đây là gate cứng trong Verification (Pre-deploy) + Common Rationalizations.
- **Feature flag qua `site_config`/setting (decouple deploy ↔ release)** — ship code rủi ro nhưng TẮT bằng cờ: đọc `frappe.conf.get("ac_feature_<x>")` hoặc một Singles setting (vd `AssetCore Settings.enable_<x>`) thay vì hard-enable. Bật/tắt KHÔNG cần redeploy = rollback nhanh; cờ có owner + ngày dọn (cờ sống mãi = nợ kỹ thuật). ⚠️ Sửa `site_config.json` là HARD-STOP USER (đề xuất, KHÔNG tự chạy).

### Deprecation & migration — code-as-liability

- **Code-as-liability** — mỗi dòng code có chi phí bảo trì (test, patch, onboard); giá trị nằm ở chức năng, KHÔNG ở code. Gỡ **zombie code** (whitelist/endpoint/DocType field không còn consumer, không owner, test fail không ai sửa) thay vì để limbo. Đo trước khi gỡ: grep FE + `frappe.get_all` log usage = 0 consumer mới xoá.
- **DocType/field deprecation AN TOÀN (giữ data, patch dần)** — KHÔNG drop column thẳng. Quy trình: (1) ngừng ghi field cũ ở service, (2) patch backfill field mới (idempotent, `has_column` guard), (3) chạy song song tới khi mọi consumer đọc field mới (Strangler), (4) chỉ alter/drop khi usage=0 + đã backup. Mỗi bước 1 **Frappe patch** trong `patches/vX_Y/NNN_*.py` + `patches.txt`, commit trong patch.
- **Frappe patch migration** = đơn vị deprecation: additive trước (thêm field/patch backfill) → cutover → cleanup, tách commit, mỗi patch idempotent (chạy 2 lần không vỡ). Xem Phần 1 "Migration model".

### Shipping & launch — staged rollout + rollback

- **Pre-launch checklist** — TRƯỚC go-live: tests xanh (quality gate), backup `.sql.gz` size>0, fixtures 3-list đủ, FE `npm run build` RIÊNG, `scheduler status=enabled`, không whitelist mới thiếu permission gate. Đã hệ thống hoá ở Verification dưới.
- **Staged rollout** — KHÔNG big-bang mọi site cùng lúc. Thí điểm 1 site/bệnh viện trước (vd bệnh viện X), theo dõi Error Log/Email Queue + smoke critical flow → ổn mới nhân ra các site còn lại. Mỗi site là 1 `--site` riêng → rollout = thứ tự cài/update từng site.
- **Rollback procedure** — mọi deploy phải reversible TRƯỚC khi chạy: (a) cờ feature → tắt cờ (<1 phút, không redeploy); (b) code → revert commit + re-deploy; (c) DB → restore `.sql.gz` (xem [references/destructive-db-ops.md](references/destructive-db-ops.md) — restore không cần root pw). Migrate fail giữa chừng = DỪNG + rollback ngay (Safety rules).

> Cross-ref: **telemetry/log/alert/health vận hành** (structured logging, RED metrics, Error Log/Email Queue/Scheduled Job Log monitoring, alert symptom-based) thuộc skill **assetcore-observe** — KHÔNG ở đây. Deploy lo "đưa lên & lùi về"; observe lo "nhìn thấy & chẩn đoán" sau khi lên.

---

## Safety rules

- **KHÔNG bao giờ** deploy mà không có DB backup xác nhận.
- **KHÔNG** force-push lên main/release branch.
- **KHÔNG** chạy `drop-site` hay `reset` trên production.
- Deployment window: báo team trước ít nhất 30 phút.
- Nếu migrate fail giữa chừng: DỪNG, rollback ngay, investigate.

---

## Phần 4 — Lessons Learned (LL-DEPLOY-*)

Mỗi mục: triệu chứng → nguyên nhân → rule kiểm-được. **Reload/restart/migrate/site_config = HARD-STOP user** — BE đề xuất, KHÔNG tự chạy.

### Preload staleness & 403/417 disambiguation

- **[LL-DEPLOY-01] preload staleness = HTTP-417 AttributeError ở endpoint AUTHENTICATED, KHÔNG phải guest-403.** Sau khi sửa BẤT KỲ `assetcore/api/*.py` hoặc module nó import: code KHÔNG live ở HTTP cho tới khi USER reload gunicorn (master `--preload` import app 1 lần lúc boot rồi fork ~41 worker → worker cũ giữ code cũ trong RAM). Triệu chứng ĐÚNG của stale-worker = HTTP **417** `AttributeError ... module has no attribute '<fn>'`. KHÔNG kết luận stale từ một `403 "not whitelisted / Login to access"` của `curl` GUEST tới method auth-required — đó là auth-gate ĐÚNG (dispatcher-403, xem LL-DEPLOY-06). **Chứng minh stale (kiểm-được):** (a) so với `bench --site <site> execute assetcore.api.X.fn` (fresh import → chạy code mới = code OK, chỉ worker cũ), HOẶC (b) hit endpoint authenticated (Playwright/session cookie) phân biệt 417-AttributeError vs 200/business. Reload là HARD-STOP user-only — KHÔNG tự `bench restart`/HUP/`supervisorctl restart`. Ref: memory `gunicorn_preload_staleness.md`; troubleshoot row `AttributeError ... no attribute` ở Phần 1.
- **[LL-DEPLOY-02] 417 phantom `get_asset_kpis 'has no attribute'` = KHÔNG phải stale-worker.** Function đó KHÔNG tồn tại theo tên ấy và FE KHÔNG bao giờ gọi nó → BỎ QUA, đừng kích hoạt reload-debug. Cùng họ phantom: `curl 127.0.0.1:8000` thiếu `-H "Host: <site>"` trả 404 `'site does not exist'` (Frappe resolve site theo Host header) — KHÔNG phải endpoint bug. Ref: memory `gunicorn_preload_staleness.md` (phantom watch + Host-header 404).
- **[LL-DEPLOY-06] Hai loại 403 deploy-debug: dispatcher-403 (status-line THẬT) vs in-handler cap-403 (HTTP-200 + Error envelope).** Phân biệt nguồn TRƯỚC khi kết luận: (a) **dispatcher-403** = guest/no-token, qua `is_whitelisted` (frappe/__init__.py ~876) → HTTP status-line **403 THẬT** + body `FrappeRawError`/`exc_type=PermissionError` → auth-gate ĐÚNG (KHÔNG stale, KHÔNG cần reload/migrate); (b) **in-handler cap-403** = bearer hợp lệ nhưng thiếu capability, qua `_err(msg,403)` (vd `imm12.py:96`) → HTTP-**200** + Error envelope `{code:FORBIDDEN, http_status:403}` (status-line KHÔNG phải 403). In-handler error 404/409/422 (qua `_err`/`nthrow`→`handle()`) cũng ĐẾN TRÊN HTTP-200 (`frappe.local.response.http_status_code=NULL`, giá trị chỉ trong body `http_status`). → User báo '403 sau deploy': hỏi guest hay authenticated; guest-403 ≠ cần reload/migrate. Ref: memory `mobile_be_openapi_contract_gotchas.md`, `gunicorn_preload_staleness.md`.
- **[LL-DEPLOY-07] CHẨN ĐOÁN stale-worker TRƯỚC khi coi lỗi-live là bug code (chống phóng factory vô ích).** RED: 2026-06-11 — user báo "Không thể tạo PDF nhãn, thử lại sau" + yêu cầu chạy factory fix. THỰC TẾ: gunicorn `--preload` worker boot Jun-10 15:02 < endpoint tạo Jun-11 → endpoint KHÔNG có trong worker. Bằng chứng quyết định: `curl -X POST "http://localhost:8000/api/method/<dotted.path>" -H "Host: <site>" -d '{...}'` → **HTTP 417 "module '<mod></mod>' has no attribute '<fn></fn>'"** = STALE worker, KHÔNG phải bug code. So `ps -eo pid,lstart,cmd | grep gunicorn` (boot time) vs `stat -c '%y' <file>.py` (mtime). RULE: mọi lỗi "vừa sửa code mà live vẫn lỗi" → curl endpoint + so boot-vs-mtime TRƯỚC. Stale → FIX = USER `bench restart` (+ `bench --site <site> clear-cache` bust `ac_caps::*`); **KHÔNG phóng factory/viết-fix** (factory verify bằng `bench run-tests` fresh-import = false-green, tốn vô ích). BE KHÔNG tự reload (HARD-STOP USER). DONE-gate: trước khi điều tra "bug live" → chứng minh endpoint CÓ trong worker đang chạy (curl ≠ 417 no-attribute). Bổ sung CHẨN ĐOÁN cho LL-DEPLOY-01 (417 no-attribute = dấu hiệu stale) + LL-DEPLOY-02 (loại trừ phantom trước). Ref: memory `gunicorn_preload_staleness.md`; troubleshoot row `AttributeError ... no attribute` ở Phần 1.
- **[LL-DEPLOY-08] Stale-worker KHÔNG chỉ là 417-no-attribute — "lỗi live" có thể là code CŨ của một bug ĐÃ FIX (đừng re-fix).** RED: 2026-06-29 — user dán traceback `pymysql OperationalError (1054) "Unknown column 'asset_ref'"` ở `imm04.search_link` + yêu cầu "sửa lỗi tạo phiếu hiệu chuẩn". THỰC TẾ bug đã fix ở commit `8b1700c` (2026-06-04: config search `asset_ref`→cột thật `asset` + defense `_live` drop field-không-tồn-tại); gunicorn `--preload` restart 08:37 CÙNG ngày đã nạp fix → traceback user dán là từ TRƯỚC restart (stale). **Tell quyết định (KHÁC 417 no-attribute):** (a) **line-number trong traceback ≠ on-disk** — live báo `services/imm04.py:1022` nhưng `frappe.db.get_all` on-disk ở dòng 1068 ⇒ code đang chạy ≠ code trên đĩa; (b) `git log -1 -S '<symbol-trong-lỗi>' -- <file>` thấy symbol (vd `asset_ref`) ĐÃ bị xoá/đổi trong 1 commit là tổ tiên của HEAD ⇒ bug đã đóng; (c) `bench --site <site> execute <dotted.path>` reproduce chạy SẠCH = code hiện tại OK. RULE: trước khi "sửa lỗi live", chứng minh bug CÒN trên code HIỆN TẠI (`git log -S` + `bench execute` reproduce) — KHÔNG re-fix bug một commit đã đóng (lãng phí cả phiên điều tra); lỗi cũ = chờ worker reload (HARD-STOP user) hoặc hard-refresh browser. Mở rộng LL-DEPLOY-07: tín hiệu stale KHÔNG bó ở 417 — bất kỳ traceback có line ≠ on-disk = worker cũ. Ref: memory `gunicorn_preload_staleness.md`.

### FE build = deploy live (Vue SPA — KHÔNG chỉ là "bundle")

- **[LL-DEPLOY-09] `npm run build` FE = DEPLOY LIVE + ship TOÀN BỘ working tree — KHÔNG build cây bẩn đa-phiên.** `frontend/vite.config` đặt `outDir: '../assetcore/public/frontend'` + `emptyOutDir: true` → `npm run build` (a) **ghi đè thẳng thư mục prod đang serve** (`/assets/assetcore/frontend/`) — KHÔNG phải bước "bundle vô hại"; (b) **bundle MỌI file FE on-disk**, gồm thay đổi uncommitted của các phiên khác. RED: 2026-06-29 — định `npm run build` để "đưa fix hiệu chuẩn lên", phát hiện cây có ~30 file FE uncommitted của phiên song song (CurrencyInput rollout chưa xong, test fail 32/32) ⇒ build = ship luôn cả phần dở lên prod bệnh viện; dist live khi đó từ 2026-06-15. RULE: chỉ `npm run build` đè `public/frontend` khi cây FE SẠCH / đến-release (không lẫn WIP phiên khác). Verify build mà KHÔNG deploy: `npx vite build --outDir <scratch-ngoài-repo> --emptyOutDir` + component test (vitest) — KHÔNG đụng dist live. Deploy = HARD-STOP user. (Đính chính row "bench build ≠ npm run build" Phần 2: output FE tuy gitignored NHƯNG LÀ dir prod serve, không vô hại.)

### Mobile-BE go-live (OAuth2 / device-token / openapi / cap-set)

- **[LL-DEPLOY-03] Mobile-BE go-live checklist — 4 bước THỨ TỰ bắt buộc, HARD-STOP user.** Để mobile-BE (device-token endpoints, OAuth2, openapi serve, cap-set mới) live HTTP cần USER chạy ĐỦ (BE KHÔNG tự — HARD-STOP thêm ngoài no-commit/no-reload): (1) `bench --site <site> migrate` — tạo doctype OAuth Client/Bearer Token + device-token + TỰ bust `ac_caps::*` qua `after_migrate→_bust_capability_cache` (cap-set bump vd v95→v97: `asset.print`/`asset.qr.rotate`); (2) `bench restart` — gunicorn `--preload` worker cũ giữ `CAPABILITY_MAP`/imports cũ trong RAM, thiếu restart → endpoint deny cap mới hoặc 417; (3) cấu hình `site_config.json` (xem LL-DEPLOY-04); (4) verify pre-flight admin-only `bench --site <site> execute assetcore.api.mobile.preflight.verify_oauth_client`. **Rule kiểm-được:** mọi BE round đụng mobile PHẢI ghi 4 bước này vào `open_issues`. Round chỉ-sửa-doc/yaml/test (introspection-only, KHÔNG sửa `api/*.py`) thì reload KHÔNG bắt buộc CHO round đó nhưng blocker go-live vẫn đứng. Ref: memory `mobile_backend_initiative_20260609.md`.
- **[LL-DEPLOY-04] site_config mobile go-live: allow_cors=LIST-origin (KHÔNG wildcard+credentials) + OAuth Client + FCM + public HTTPS host.** Phase B provisioning (HARD-STOP USER) set trong `sites/<site>/site_config.json`: (a) `allow_cors` = LIST origin tường minh (vd `["https://app.hospital.vn"]`) — TUYỆT ĐỐI KHÔNG wildcard `"*"` đi kèm credentials (ADR-MOBILE-004 cấm; `allow_cors=None` = CORS OFF → native fetch fail); (b) OAuth Client = grant Authorization Code + scope `'all openid'` + redirect `assetcore://oauth/callback` + least-priv roles; (c) `assetcore_qr_base_url` = public HTTPS host (QR deep-link); (d) FCM credentials (push); (e) rate-limit qua nginx `limit_req` HOẶC `conf.rate_limit` — thiếu key `rate_limit` thì `frappe.local.rate_limiter` không instantiate → `@rate_limit` emit ZERO `Retry-After`/`X-RateLimit-*` header (429 không backoff). KHÔNG tự sửa site_config — quyết định + chạy của user. Ref: memory `mobile_backend_initiative_20260609.md`; ADR-MOBILE-004.
- **[LL-DEPLOY-05] Ngrok mobile-expose: expose BE local cho APK test qua HTTPS — set allow_cors=[ngrok-origin] + OAuth redirect/host=ngrok, TẮT khi xong.** gunicorn `127.0.0.1:8000` không TLS/không public → APK native không tới. EXPOSE qua ngrok HTTPS rồi đồng bộ: (1) `ngrok http 8000` → lấy `https://<sub>.ngrok-free.app`; (2) `site_config.json`: `allow_cors=["https://<sub>.ngrok-free.app"]` (LIST 1-origin, KHÔNG wildcard+credentials — cùng quy tắc LL-DEPLOY-04) + `host_name`/public host = ngrok origin để Frappe resolve Host header (tránh 404 'site does not exist'); (3) OAuth Client redirect + `assetcore_qr_base_url` trỏ ngrok origin; (4) APK base-url = ngrok HTTPS. Sau đổi site_config → USER `bench restart` (HARD-STOP). **TẮT ngrok + revert site_config về host gốc khi xong** (ngrok origin ephemeral — CI-guard chặn placeholder host lọt prod build). KHÔNG tự khởi ngrok/sửa site_config — đề xuất cho user. Ref: memory `mobile_backend_initiative_20260609.md`.

---

## Common Rationalizations

| Lý do hay viện để skip                                  | Sự thật                                                                                                                                                                                                                                                                      |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| "Deploy nhanh thôi, backup sau cũng được"              | Release đổi schema/field; migrate fail = data hỏng không cứu được.`bench backup --with-files` + verify `.sql.gz` size>0 TRƯỚC migrate (Safety rules; pre-deploy checklist).                                                                                      |
| "Xoá data rác có gì đâu, chạy DELETE luôn"          | Frappe KHÔNG auto-cascade; xoá master trước child = orphan/broken refs. Bắt buộc backup → dry-run`_scan` → AskUserQuestion → cascade-delete đúng thứ tự FK ([references/destructive-db-ops.md](references/destructive-db-ops.md)).                               |
| "Dry-run thừa, tôi biết chính xác xoá gì"            | LIKE wildcard`'_%'` match toàn bảng; đoán tên cột = xoá nhầm. Dry-run in count+samples + user duyệt scope (anti-pattern #1/#2 Phần 3).                                                                                                                             |
| "Vừa sửa`api/*.py` rồi, test live luôn"               | gunicorn`--preload` worker cũ giữ code cũ trong RAM → 417 `no attribute`. Reload là HARD-STOP USER; verify `bench execute` chạy được TRƯỚC (LL-DEPLOY-01).                                                                                                    |
| "Live lỗi sau khi sửa code → phóng factory fix"         | Thường là STALE-WORKER, không phải bug.`curl` endpoint → 417 no-attribute = stale → USER `bench restart`, KHÔNG factory (factory verify fresh-import = false-green) (LL-DEPLOY-07).                                                                                |
| "403 sau deploy = stale, reload đi"                        | Guest/no-token 403 (dispatcher) = auth-gate ĐÚNG, KHÔNG cần reload. Hỏi guest hay authenticated; in-handler cap-403 đến TRÊN HTTP-200 (LL-DEPLOY-06).                                                                                                                  |
| "`bench build` xong là FE mới rồi"                     | `bench build` chỉ bundle desk Frappe; Vue SPA phải `npm run build` RIÊNG (output gitignored) — quên = FE chạy code cũ (Phần 2 ⚠️).                                                                                                                               |
| "Build FE để xem fix trên giao diện thôi mà"          | `npm run build` = `emptyOutDir` → ghi đè dist prod ĐANG serve + ship CẢ WIP uncommitted của phiên khác. Cây bẩn đa-phiên → build = deploy phần dở lên prod. Verify bằng `vite build --outDir <scratch>` + vitest, KHÔNG đè dist live (LL-DEPLOY-09). |
| "Lỗi live = bug, sửa ngay"                                | Có thể là code CŨ của bug ĐÃ fix (worker stale).`git log -S '<symbol>'` + line-traceback-≠-on-disk + `bench execute` reproduce TRƯỚC khi re-fix — đừng phí cả phiên fix bug commit đã đóng (LL-DEPLOY-08).                                             |
| "Thêm workflow chỉ cần khai Workflow fixture"            | Thiếu Workflow State / Action Master → fresh-site migrate fail. Update CẢ 3 list cùng commit (Fixtures 3-list rule).                                                                                                                                                       |
| "Chuông trống → vá engine notification"                 | Thường là DATA (Administrator tự gán → self-notify chặn đúng), KHÔNG phải bug. Chạy LL-BE-34 decision tree TRƯỚC.                                                                                                                                                |
| "Mobile endpoint code xong là live HTTP"                   | Cần migrate (tạo doctype + bust cap) + restart + site_config + preflight (4 bước, HARD-STOP user). Thiếu = deny cap mới / 417 (LL-DEPLOY-03/04).                                                                                                                         |
| "Deploy thẳng prod rồi test sau cho nhanh"                | Vi phạm Shift Left — quality gate (`bench run-tests` xanh + FE build) phải qua TRƯỚC `migrate`/`restart`. Lỗi bắt ở local = phút; bắt ở prod = data hỏng (Phần 3.5).                                                                                        |
| "Field cũ bỏ rồi, drop column luôn cho sạch"           | Code-as-liability KHÔNG = drop ẩu. Deprecate field theo bước (ngừng-ghi → patch backfill → song song → drop khi usage=0+backup); drop thẳng = mất data (Phần 3.5 deprecation).                                                                                      |
| "Bản mới ổn, roll hết mọi site bệnh viện cùng lúc" | Big-bang = nổ đồng loạt. Staged rollout: 1 site/bệnh viện thí điểm → theo dõi → nhân ra (Phần 3.5 shipping).                                                                                                                                                     |

## Red Flags — STOP

- Chuẩn bị `migrate`/`restore`/mass-delete mà CHƯA có `.sql.gz` backup verify size>0.
- Chạy DELETE/`drop-site`/`reset`/`ALTER TABLE` bulk mà chưa dry-run + chưa AskUserQuestion scope.
- LIKE wildcard chưa escape (`'_%'`), đoán tên cột, xoá master trước child (orphan).
- Tự `bench restart`/HUP/`supervisorctl restart`/`migrate`/sửa `site_config.json` (đây là HARD-STOP USER — chỉ đề xuất).
- Kết luận "stale-worker" / "bug live" mà chưa `curl` endpoint phân biệt 417-no-attribute vs 200; chưa so boot-time vs mtime.
- Kết luận "403 = stale → reload" mà chưa phân biệt dispatcher-403 (guest, auth-gate đúng) vs in-handler cap-403 (HTTP-200).
- Phóng factory để "fix bug live" trước khi loại trừ stale-worker (factory fresh-import = false-green).
- Deploy bản mới mà quên FE `npm run build` (bước RIÊNG, ≠ `bench build`).
- `npm run build` đè `public/frontend` khi cây FE còn lẫn WIP uncommitted của phiên khác (= deploy phần dở lên prod, LL-DEPLOY-09) — verify bằng `--outDir <scratch>`, đừng đè dist live.
- "Sửa lỗi live" mà chưa `git log -S '<symbol>'` / chưa so line-traceback-vs-on-disk để loại trừ bug-đã-fix-worker-cũ (re-fix vô ích, LL-DEPLOY-08).
- Thêm workflow mà chỉ update 1/3 fixture list; raw `DELETE FROM tabIMM Audit Trail` không có user-approve + không phải leaked test fixture (ISO 13485:7.5.9).
- Mobile round đụng `api/*.py` mà không ghi 4-bước go-live (migrate/restart/site_config/preflight) vào `open_issues`.
- Bỏ qua quality gate (deploy khi `bench run-tests`/FE build CHƯA xanh) — vi phạm Shift Left.
- Drop DocType field/column hoặc xoá whitelist mà chưa đo usage=0 + chưa patch backfill + chưa backup (zombie-code sai cách).
- Big-bang roll mọi site cùng lúc thay vì staged rollout 1 site thí điểm trước; deploy mà chưa có rollback procedure (cờ/revert/restore) sẵn.

## Verification

Trước khi tuyên bố deploy/cleanup/troubleshoot "xong" — phải có BẰNG CHỨNG (không "có vẻ đúng"):

- [ ] **Backup:** `bench --site <site> backup --with-files` chạy + `ls -la sites/<site>/private/backups/` thấy `.sql.gz` size>0 (TRƯỚC mọi migrate/destructive).
- [ ] **Pre-deploy:** tests xanh (`run-tests --app assetcore`), `test_workflows` xanh, FE `npm run typecheck && npm run lint` + `npm run build` exit 0, không whitelist mới thiếu permission gate, patches mới trong `patches.txt` test fresh-site.
- [ ] **Deploy:** sau update đã chạy ĐỦ migrate → `bench restart` (HARD-STOP user) → FE `npm run build` RIÊNG → maintenance-mode off; `bench --site <site> scheduler status` = "enabled".
- [ ] **Fixtures:** thêm/sửa workflow → cập nhật CẢ 3 list (Workflow + State + Action Master) + `export-fixtures` + verify fresh-site `frappe.get_all('Workflow', pluck='name')` đủ.
- [ ] **Stale-worker disambiguation:** "bug live" → `curl -X POST .../api/method/<path> -H "Host: <site>"` phân biệt 417-no-attribute (stale → USER restart, KHÔNG factory) vs 200/business; so `ps … lstart` vs `stat -c %y *.py`.
- [ ] **Destructive:** đã backup → dry-run `_scan` in count+samples → AskUserQuestion duyệt scope → cascade-delete đúng thứ tự FK → orphan sweep → re-scan = 0 → `rm assetcore/_scan_*.py _delete_*.py` (KHÔNG commit script tạm).
- [ ] **Email:** sau flush verify `Email Queue` `status="Sent"`; báo user "kiểm tra inbox/spam" (Sent ≠ đã nhận).
- [ ] **Mobile go-live (nếu đụng):** 4 bước (migrate / restart / site_config allow_cors LIST-origin + OAuth + FCM / preflight `verify_oauth_client`) ghi vào `open_issues`.
- [ ] **Quality gate (Shift Left):** `bench run-tests` xanh + FE `npm run typecheck && lint && build` exit 0 ĐÃ chạy ở local/CI TRƯỚC khi đẩy lên prod.
- [ ] **Deprecation an toàn (nếu gỡ field/endpoint):** đo usage=0 (grep FE + log) → patch backfill idempotent → song song → chỉ drop khi đã backup; không drop thẳng (code-as-liability đúng cách).
- [ ] **Staged rollout + rollback:** rollout 1 site/bệnh viện thí điểm trước (không big-bang); rollback procedure (tắt cờ / revert+redeploy / restore `.sql.gz`) đã xác định TRƯỚC khi deploy.

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE + file phiên mới nhất (curated; cần truy gốc chi tiết → đọc mục 🪞 Mirror của file phiên) — "đang dở ở đâu"; dữ liệu trong `.claude/contexts/` — gitignored; file phiên ở `sessions/<ngày>/`). Main session: hook tự nạp mỗi prompt + tự **mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào file phiên qua hook `Stop`; subagent phải TỰ chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY: `STATE.md`(ghi đè) + bồi **semantic** vào file phiên (`session-log.sh current` → path; **KHÔNG còn LOG.md**). Hook `Stop` đã mirror nguyên văn → bạn CHỈ cần tóm Làm/Quyết-định/Để-lại. KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `.claude/contexts/` (STATE.md + sessions/<ngày>/); fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
