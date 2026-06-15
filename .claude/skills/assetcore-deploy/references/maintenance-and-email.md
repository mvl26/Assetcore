# Maintenance scripts & Email/SMTP (Phần 1 deep-dive)

> Heavy reference moved from `SKILL.md` Phần 1. Email / Notification SMTP infra & flush + Maintenance scripts (dọn data / fix ad-hoc / migrate one-shot). PRESERVED verbatim.

## Email / Notification — SMTP infra & flush (gặp 2026-06-01)

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

## Maintenance scripts — dọn data / fix ad-hoc / migrate one-shot

Bug recurring 2026-05-27 (data cleanup session): script tạm chạy sai pattern, leak hoặc xoá nhầm. Tuân thủ checklist:

**Pattern chuẩn:**

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

## Troubleshoot — cloud install deep-dives

> Moved from `SKILL.md` Phần 1 troubleshoot table (giant narrative root-cause + multi-layer fix). Symptom rows ở SKILL.md trỏ về đây. PRESERVED verbatim — mỗi step/PATH/`bench` command là một phần của recovery runbook cloud-install, mất 1 bước = nguy hiểm.

### `ac_department` orphan — form User crash trên desk (cloud, 2026-06-05)

**Symptom:** `Field ac_department is referring to non-existing doctype AC Department. Please delete the field…` khi mở form User trên desk (cloud).

**Cause:** Cùng gốc với row `_rebuild_module_map` dưới: DocType `AC Department` chưa sync (app_modules cache cũ) NHƯNG Custom Field `User.ac_department` đã tồn tại từ lần cài trước → orphan. Raise ở `frappe/desk/form/meta.py::add_search_fields` (FormMeta desk, KHÔNG chặn `bench migrate` vì migrate dùng base meta).

**Fix:**
- **Root fix:** sync doctype (fix 3-lớp `_rebuild_module_map` dưới) → AC Department có → field hợp lệ.
- **Self-heal:** `create_user_custom_fields` gọi `_drop_orphan_user_link_fields()` gỡ field Link trỏ doctype đã mất (chỉ khi target thực sự thiếu; tạo lại ở migrate sau).
- **Recovery thủ công ngay:** `bench --site <site> execute "frappe.db.delete('Custom Field', {'dt':'User','fieldname':'ac_department'})"` + `clear-cache` + `bench restart` + `migrate`.

### `_rebuild_module_map` — `install-app` sync 0/108 doctype (cloud, 2026-06-05)

**Symptom:** `install-app` báo `Workflow sync error … DocType <X> not found` cho MỌI doctype + `_seed_uoms` `No module named 'frappe.core.doctype.ac_uom'` (cloud).

**Cause:** `sync_for` sync 0/108 doctype: Redis cache `app_modules` cũ (set bởi web worker/scheduler đang chạy TRƯỚC khi assetcore vào bench) thiếu "assetcore"; `setup_module_map` dùng cache cũ (truthy→no rebuild), `clear_cache` của install KHÔNG reset `local.app_modules` in-memory → `sync_for` lặp 0 module. Log KHÔNG có progress bar `Updating DocTypes for assetcore` = dấu hiệu 0 file.

**Fix (vĩnh viễn, 3 lớp, `setup/install.py` — helper `_rebuild_module_map` bust `app_modules`/`all_apps`/… + `frappe.setup_module_map()`):**
- (1) `before_install` rebuild map ngay trước `sync_for` native;
- (2) `after_install._ensure_app_doctypes_synced()` self-heal: nếu "AC Asset" vẫn thiếu → `sync_for(force=True)` thủ công (chạy TRƯỚC `sync_fixtures` nên xoá luôn "Skipping fixture syncing");
- (3) `before_migrate` rebuild map trước `sync_all` → đường `bench migrate` cũng sạch.

**Recovery site đã lỡ cài hỏng:** `bench --site <site> migrate` (plain `install-app` sẽ báo "already installed" → KHÔNG re-sync; phải `migrate` hoặc `install-app --force`/uninstall trước). Verify: `frappe.db.count('Workflow')==21`, `frappe.db.exists('DocType','AC UOM')`. npm noise → `npm ci --no-fund --no-audit --loglevel=error` trong `setup_frontend.py`.

### `_remove_foreign_customizations` + `_apply_erpnext_asset_custom_fields` PATH bug — orphan Custom Field trên doctype CORE/ERPNext sau uninstall (2026-06-05 audit)

**Symptom:** Orphan Custom Field trên doctype CORE/ERPNext sau khi uninstall (User, Asset) → form crash `Missing DocType`.

**Cause:** AssetCore thêm Custom Field vào doctype KHÔNG thuộc app (User của Frappe = 6 field; ERPNext Asset = ~28 field `custom_imm_*`). Cũ tạo với `module=None` → `uninstall-app` (chỉ drop doctype thuộc module app) bỏ lại field orphan. **UOM KHÔNG dính** (AssetCore dùng doctype riêng "AC UOM", không đụng core UOM). Không có Property Setter foreign.

**Fix:**
- (1) tạo field gắn `module="AssetCore"` (`_ensure_custom_field` + inject vào `asset_custom_fields.json` import) → Frappe track theo app;
- (2) hook `before_uninstall` (`setup/install.py::_remove_foreign_customizations`) xóa tường minh CF trên User+Asset (phủ field cũ module=None) + Property Setter module=AssetCore.
- ⚠️ **PATH bug đã sửa:** `_apply_erpnext_asset_custom_fields` dùng `get_app_path('assetcore','config',…)` — KHÔNG `('assetcore','assetcore','config',…)` (file ở dưới python package, không dưới module folder; path thừa 'assetcore' → silent no-op → Asset HTM fields chưa từng áp trên site ERPNext).
