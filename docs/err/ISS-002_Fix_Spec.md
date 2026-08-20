# Spec: ISS-002 — Fix email chào mừng khi tạo user mới (+ thiết lập Email Account cho AssetCore)

> Module: **IMM-00 (User Management)** · Actor: **Quản trị hệ thống** · Nguồn lỗi: `docs/err/ISS-002_Khong_gui_email_chao_mung_AssetCore.docx`

## Objective

Khi admin tạo user mới qua **Hệ thống > Người dùng > Thêm người dùng mới** và tick **"Gửi email chào mừng"**, hệ thống phải **thực sự gửi đúng 01 email** tới địa chỉ đã khai báo, nội dung tiếng Việt gồm: tên hệ thống, URL đăng nhập (Vue `/login`), tên đăng nhập, và **link tự đặt mật khẩu** (không gửi mật khẩu thô). Nếu gửi lỗi → **ghi log + trạng thái** để admin truy vết. Đồng thời **thiết lập tài khoản gửi (SMTP) cho AssetCore** để email thoát ra ngoài.

Success = tick → nhận đúng 1 email đúng nội dung; không tick → không email; lỗi → có log + cảnh báo; không trùng lặp.

## Root cause (đã verify trên site `miyano`)

1. **[CHÍNH] Scheduler TẮT** (`is_scheduler_disabled()=true`) → Email Queue không flush → welcome mail (enqueue `now=False`) kẹt vĩnh viễn. Bằng chứng: 8 email gần nhất đều `status="Not Sent"`.
2. **Không có Email Account `default_outgoing`** (chỉ "Jobs" disabled) → chỉ fallback site_config `miyanovietnam`. AssetCore cần tài khoản gửi riêng `snonamevx@gmail.com`.
3. `_safe_sendmail` (`utils/helpers.py:59`) **nuốt lỗi bằng `pass`, không log** → vi phạm yêu cầu truy vết.
4. Welcome mail mặc định Frappe trỏ `/update-password` desk-route, tiếng Anh — không đúng nội dung/URL yêu cầu.

## Tech Stack

Frappe/ERPNext v15 · Python · MariaDB · Vue 3 FE (`apps/assetcore/frontend`). SMTP: `smtp.gmail.com:587 TLS` + Gmail **app password**.

## Commands

```
Cấu hình email (đọc .env → Email Account, bật scheduler, dọn queue cũ):
  bench --site miyano execute assetcore.setup.email.setup_assetcore_email
Test (module-isolated):
  bench --site miyano run-tests --module assetcore.tests.imm00.test_imm00_welcome_email
  bench --site miyano run-tests --module assetcore.tests.integration.test_setup_email
Reload live (USER làm — gunicorn --preload):
  <lệnh reload gunicorn của bạn>   # bắt buộc để api/user.py + helpers.py phản ánh trên HTTP
```

## Project Structure (files chạm)

```
apps/assetcore/.env                              → THÊM ASSETCORE_SMTP_* (gitignored ✓)
assetcore/setup/email.py                         → NEW: _load_env + configure_outgoing_email + enable + setup_assetcore_email
assetcore/setup/install.py                       → after_migrate gọi configure_outgoing_email (env-guarded, idempotent, no-op nếu thiếu .env)
assetcore/api/user.py                            → _build_new_user_doc (no_welcome_mail) + _send_welcome_email (NEW) + create_system_user (gọi + trả status) + _send_activation_email (now=True)
assetcore/utils/helpers.py                       → _safe_sendmail: log_error thay vì pass; hỗ trợ now passthrough
assetcore/tests/imm00/test_imm00_welcome_email.py      → NEW
assetcore/tests/integration/test_setup_email.py              → NEW
frontend/src/views/auth/UserProfileFormView.vue  → surface welcome_email_sent/failed toast (nhẹ, optional)
```

## Design

### A. SMTP config (`.env` → Email Account) — honor "cho vào .env"

`.env` thêm (password lưu nguyên, strip space khi ghi vào Email Account):
```
ASSETCORE_SMTP_SERVER=smtp.gmail.com
ASSETCORE_SMTP_PORT=587
ASSETCORE_SMTP_USE_TLS=1
ASSETCORE_SMTP_LOGIN=snonamevx@gmail.com
ASSETCORE_SMTP_PASSWORD=oomk kfdp zdnl coyj
ASSETCORE_SMTP_SENDER=snonamevx@gmail.com
```
`configure_outgoing_email()`: parser `.env` tối giản (không phụ thuộc python-dotenv — không cài); **upsert** Email Account `"AssetCore Notifications"` (`default_outgoing=1, enable_outgoing=1`, smtp_server/port/use_tls/login/password); **hạ `default_outgoing=0`** mọi account khác (Frappe chỉ cho 1 default). Idempotent. Env thiếu → return `{"skipped": True}` (an toàn cho env khác/CI).

### B. Welcome email đúng nội dung + đúng 01 email + truy vết

- `_build_new_user_doc`: set `user_doc.flags.no_welcome_mail = True` → **chặn** welcome mail mặc định của Frappe (chống trùng + chống nội dung EN sai). Ta tự gửi.
- `_send_welcome_email(user_name)` (sau commit): tạo reset key (như Frappe `_reset_password`: `generate_hash` → `sha256_hash` → set `reset_password_key`), link `= {get_url()}/update-password?key=...`. `frappe.sendmail(recipients=[email], now=True, ...)` nội dung VI: chào theo full_name, "AssetCore", URL đăng nhập `{get_url()}/login`, tên đăng nhập = email, nút **"Đặt mật khẩu"** → link, KHÔNG plaintext password. Wrap try/except → `log_error` khi lỗi.
- `create_system_user`: nếu welcome requested → gọi `_send_welcome_email`, gắn `welcome_email_sent: bool` (+ `welcome_email_error` nếu có) vào `_ok(...)`. Không-tick → không gọi.
- Đúng-01: một insert = một lần gửi; double-submit đã bị chặn 409 (không phát sinh email thứ 2).
- `_send_activation_email` (approve flow): thêm `now=True`.

### C. Traceability — `_safe_sendmail`

Thay `except: pass` → `except Exception: frappe.log_error(frappe.get_traceback(), "_safe_sendmail failed")`. Vẫn không raise (không phá transaction). Status Sent/Error đã có sẵn trong **Email Queue** doctype (admin xem được).

### D. Delivery — now=True + scheduler

Welcome/activation gửi `now=True` (không phụ thuộc queue → lỗi SMTP hiện tức thì). `enable_email_delivery()` bật scheduler cho các notification khác. `setup_assetcore_email()` = configure + **dọn/kiểm các Email Queue `Not Sent` cũ** (tránh flush 8 email test tới người thật) rồi enable.

## Testing Strategy

`unittest` (Frappe), service/API-layer, monkeypatch `frappe.sendmail` để đếm. Coverage bắt buộc:
- `test_imm00_welcome_email`: tick=1 → sendmail gọi **đúng 1 lần**, `now=True`, recipients=[email], body chứa `/login` + link `/update-password?key=`, **KHÔNG** chứa plaintext password. tick=0 → **0 lần**. Duplicate create (409) → không email thứ 2. `_send_welcome_email` raise → được `log_error`, API vẫn `_ok` với `welcome_email_sent=False`.
- `test_setup_email`: env đủ → tạo/cập nhật Email Account default_outgoing duy nhất; env thiếu → `skipped`; strip space trong password.

## Boundaries

- **Always**: chạy `bench run-tests` module-isolated trước khi tuyên bố xong; giữ audit/log; VI cho UI copy; type hints + docstring (CLAUDE.md §15).
- **Ask first**: đã hỏi (link-set-password + now=True/scheduler ✓). Bật scheduler = thay đổi hệ thống → dọn queue cũ trước.
- **Never**: commit (chờ `/assetcore-commit`); `bench migrate`; log/secret vào repo (`.env` gitignored, KHÔNG hardcode password trong .py); modify ERPNext core.

## Success Criteria (testable)

1. tick "Gửi email chào mừng" + tạo thành công → nhận **đúng 1** email VI đúng địa chỉ.
2. Email có: tên user, "AssetCore", URL `/login`, tên đăng nhập, **link đặt mật khẩu** (không plaintext).
3. Không tick → không email.
4. Lỗi gửi → `log_error` + `welcome_email_sent=False` trả về FE.
5. Không trùng email khi tạo 1 lần / reload.
6. `bench run-tests` 2 module NEW → xanh.
7. Sau setup: có Email Account `default_outgoing` snonamevx; scheduler enabled.

## Open Questions / Đã chốt

- [CHỐT] Cấp mật khẩu = **link tự đặt** (không plaintext).
- [CHỐT] **now=True + bật scheduler** (dọn 8 queue `Not Sent` cũ trước khi bật).
- [NOTE] `api/user.py` + `helpers.py` = production dưới gunicorn `--preload` → **USER reload** sau khi land; DoD tôi dùng = tests xanh, không phải curl.
```
