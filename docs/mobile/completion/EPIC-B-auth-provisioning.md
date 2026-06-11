# EPIC-B — Auth & Provisioning (BE Completion)

| Mục | Giá trị |
|---|---|
| EPIC | **B** — Auth & Provisioning (ID khoá — KHÔNG đổi) |
| Initiative | Mobile Backend (AssetCore = BE cho app mobile native; repo UI riêng) |
| Bám quyết định | **D-AUTH** (OAuth2 + PKCE S256 + refresh + revoke · WIRE provider Frappe) · **D-MVP** (field-tech) · **D-STACK** (native) — [`00-overview.md §2`](../00-overview.md) |
| Phụ thuộc | Song song **EPIC-C** (∥ C, độc lập); MỞ ĐƯỜNG cho **EPIC-G** (go-live HARD-STOP) → **EPIC-D** (push, cần B2 bearer + device-token B3) |
| Owner | BA Lead đặc tả · **USER/Admin** thực thi mọi bước cloud/migrate/site_config |
| Phạm vi file | **doc-only** — KHÔNG sửa `api/*.py` / `services/*.py` / yaml-path / operationId; KHÔNG git commit/push/migrate/reload/restart |
| Cập nhật | 2026-06-11 |

> **Nguồn chân lý** = [`13-be-completion-roadmap.md §4`](../13-be-completion-roadmap.md) (MASTER EPIC-B) + [`03-auth-oauth2.md`](../03-auth-oauth2.md) (auth deep-dive) + [`10-deploy-ops.md §1`](../10-deploy-ops.md) (runbook) + [`12-phase-b-preflight.md`](../12-phase-b-preflight.md) (preflight) + [`ADR-MOBILE-001.md`](../ADR-MOBILE-001.md) (WIRE-not-write · 1 SSoT). File này KHÔNG re-litigate 3 quyết định nền — chỉ tổ chức việc còn lại của EPIC-B thành task khoá-ID B1..B4 + DoD + AUTO/HARD-STOP.
> **Mọi claim** có `file:line` verify tại **Frappe v15.107.2** (oauthlib 3.3.1, site `miyano`, branch `feature/hieuc/core-refinement`, ground 2026-06-11). Việc CHƯA verify → `[ROADMAP]`.

---

## 1. Scope & Mục tiêu

### 1.1 Trong scope EPIC-B

| Hạng mục | Bản chất |
|---|---|
| Runbook + helper preflight tạo OAuth Client (7 điều kiện B-1, Authorization Code + PKCE S256, redirect `assetcore://oauth/callback`) | provisioning gate (B1, B4) |
| Refresh-token flow + token lifetime (3600s hard-coded — KNOWN-LIMIT) khẳng định ĐÃ hỗ trợ ở provider | wire-not-write (B2) |
| Device-token DocType + service + endpoint `register/unregister_device_token` (nếu cần cho FCM — chặn EPIC-D) | impl chờ migrate (B3) |
| `preflight.verify_oauth_client()` → `ready=True` trên cloud | DoD-gate (B4) |

### 1.2 Mục tiêu (DoD EPIC-B)

| # | Tiêu chí DoD | Đo bằng (lệnh kiểm-được) | Task | Ai chạy |
|---|---|---|---|---|
| 1 | `preflight.verify_oauth_client()` `ready=True` | `bench --site miyano execute assetcore.api.mobile.preflight.verify_oauth_client` → `ready=true` | B1+B4 | **[HARD-STOP USER]** tạo record |
| 2 | authorize→token→refresh→revoke + PKCE chạy trên cloud | smoke curl/httpie 6 bước ([`03 §1.3`](../03-auth-oauth2.md)) trên public HTTPS host | B2 | **[HARD-STOP USER]** reload+host |
| 3 | device-token doctype tồn tại + self-scope | `bench --site miyano run-tests --module assetcore.tests.test_mobile_device_token` | B3 | **[AUTO impl]** + **[HARD-STOP USER]** migrate |

### 1.3 Out-of-scope EPIC-B (đẩy sang EPIC khác — ghi RÕ)

| Hạng mục | EPIC chủ |
|---|---|
| Set `allow_cors` / public HTTPS host / nginx rate-limit / tắt `allow_error_traceback` | **EPIC-G** (go-live & hardening) |
| Impl kênh #3 push `_dispatch` + FCM sender + RBAC wiring device-token | **EPIC-D** (push — B3 chỉ tạo DocType+endpoint+self-scope, KHÔNG gửi push) |
| userinfo/whoami OIDC path trong yaml + 4 STUB typed | **EPIC-C** (B chỉ khẳng định `openid_profile` cần bearer — không viết yaml path) |
| Codegen client Dart/Kotlin smoke + E2E runbook | **EPIC-V** (chốt cuối) |
| Token TTL knob (đổi 3600s) | **[ROADMAP]** Phase F — ADR-MOBILE-001 alt A7 (wrap/fork `get_oauth_server`) — KHÔNG chặn MVP |

---

## 2. Actor

| Actor | Vai trò trong EPIC-B | HARD-STOP |
|---|---|---|
| **App native** (Flutter/RN, repo riêng — D-STACK) | Public client: sinh `code_verifier`/`code_challenge` S256, mở `/authorize`, đổi `code`→token tại `/get_token`, refresh khi 401, revoke khi logout, gọi `register_device_token` khi có FCM token. KHÔNG nhúng `client_secret`. | — |
| **Field-technician (KTV)** | Đăng nhập 1 lần WebView OAuth → app dùng refresh-token im lặng. Token gắn `allowed_roles` least-priv field-tech. | — |
| **Frappe BE** (provider) | `frappe.integrations.oauth2.*` — authorize/get_token/revoke/openid_profile/openid_configuration. WIRE-not-write — KHÔNG sửa core. | — |
| **USER / Admin** | Tạo OAuth Client record (B1); `bench migrate` (B3 device-token); set site_config/host/reload (B2 cloud smoke). | ✅ mọi bước cloud/migrate/site_config |
| **BA Lead** (file này) | Đặc tả runbook + DoD + preflight gate; viết doc/test (B3 impl). | KHÔNG chạy lệnh deploy/migrate |

---

## 3. Hiện trạng (grounded — file:line verify @Frappe v15.107.2)

### 3.1 Auth provider SẴN SÀNG — WIRE-not-write (KHÔNG sửa core)

| Khía cạnh | Trạng thái @source (file:line) |
|---|---|
| authorize | `frappe/integrations/oauth2.py:74-75` (`@whitelist allow_guest=True`); Guest → 302 `/login` `:79-82`; lưu `code_challenge`+method `frappe/oauth.py:89-91` |
| get_token | `oauth2.py:123-124` (allow_guest); success body **PASSTHROUGH OAuthlib** `:137` (`frappe.local.response = body`, KHÔNG envelope); grant-fail đường thường → `http_status_code=400` `:132-135` |
| PKCE S256 verify | `frappe/oauth.py:146-164` (sha256 → b64url `+`→`-` `/`→`_` bỏ `=`); thiếu `code_verifier` khi có challenge → xoá code + reject `:151-155` |
| revoke_token | `oauth2.py:144-145` (allow_guest); **LUÔN 200** body rỗng `frappe._dict({})` `:158-159` (RFC 7009 — 200 kể cả token sai, `except…pass` `:154-155`) |
| openid_configuration (discovery) | `oauth2.py:180-181` (allow_guest) — issuer + endpoint URLs |
| userinfo (openid_profile) | `oauth2.py:163-164` (`@whitelist` **KHÔNG allow_guest** → cần bearer) → `create_userinfo_response` → OIDC claims |
| **refresh-token** | **HỖ TRỢ ĐẦY ĐỦ** — `frappe/oauth.py:184-187` `validate_grant_type ∈ [authorization_code, refresh_token, password]`; `validate_refresh_token` chỉ chấp `status="Active"` `:270-296`; `get_original_scopes` `:244-249` |
| **token lifetime** | **3600s HARD-CODED, KHÔNG site_config knob** — `get_oauth_server()` `oauth2.py:19-24` dựng `WebApplicationServer` KHÔNG truyền `token_expires_in` → oauthlib fallback `or 3600` (`oauthlib/oauth2/rfc6749/tokens.py`); `expiration_time = creation + timedelta(seconds=expires_in)` `oauth_bearer_token.py:27-31`. OAuth Provider Settings (Single) CHỈ field `skip_authorization`. **KNOWN-LIMIT** (`[ROADMAP]` Phase F — ADR-MOBILE-001 alt A7). |
| bearer → quyền | `validate_oauth` `auth.py:633` → `frappe.set_user(token.user)` `:667` → `rbac.can(cap)` → `has_permission` `rbac.py:156-168` = **1 SSoT** (KHÔNG hệ quyền thứ 2) |

> **Hệ quả:** EPIC-B KHÔNG cần viết logic OAuth — chỉ WIRE. Refresh + revoke + PKCE ĐÃ có ở provider. Việc còn lại = provision record (B1, HARD-STOP) + khẳng định contract (B2 doc) + device-token cho push (B3) + verify cloud (B4).

### 3.2 Preflight verifier ĐÃ CÓ (READ-ONLY, admin-only)

| Khía cạnh | Trạng thái @source (file:line) |
|---|---|
| Verifier | `assetcore/api/mobile/preflight.py:146-220` `verify_oauth_client()` — `@frappe.whitelist()` (KHÔNG allow_guest) + `frappe.only_for("System Manager")` `:171` |
| 7 điều kiện B-1 | `client_count>=1` `:177-179` · `grant_type=='Authorization Code'` `:88` · `response_type=='Code'` `:96` · `default_redirect_uri==assetcore://oauth/callback ∈ redirect_uris` `:105` · `scopes=='all openid'` `:121` · `skip_authorization==0` `:129` · `allowed_roles` non-empty `:136` |
| Chịu count==0 | `OAuth Client` count = **0** @site miyano → `ready=False` + blocker VI, **KHÔNG raise** `:181-190` |
| Hằng kỳ vọng | `EXPECTED_REDIRECT_URI="assetcore://oauth/callback"` `:54` · `EXPECTED_SCOPES="all openid"` `:56` · `EXPECTED_GRANT_TYPE="Authorization Code"` `:57` · `EXPECTED_RESPONSE_TYPE="Code"` `:58` |
| Drift-guard test | `assetcore/tests/test_mobile_preflight.py` TC-MOB-PRE-01..09 (`:59-191`): field exist `:59` · grant options `:68` · response options `:79` · reqd `:89` · allowed_roles child `:96` · report shape `:116` · count==0 no-raise `:131` · 7 conditions `:150` · read-only no-write `:191` |
| Ngoài hợp đồng app | Verifier KHÔNG vào `openapi/assetcore-mobile.openapi.yaml` (admin-only diagnostic — `12 §0.4`) |

### 3.3 Provisioning AUTO = KHÔNG có (runbook thủ công + preflight gate)

| Điểm | Trạng thái @source |
|---|---|
| Fixture/patch tạo OAuth Client | **KHÔNG có** — grep `hooks.py::fixtures` / `patches.txt` / `setup/` = 0 hit → BẮT BUỘC runbook thủ công [`10 §1`](../10-deploy-ops.md) |
| OAuth Client count | **0** @site miyano (`03 §4` verified) |
| Runbook tạo client | [`10-deploy-ops.md §1`](../10-deploy-ops.md) numbered steps (USER chạy — HARD-STOP) |
| Decision (chủ ý) | Giữ runbook thủ công + preflight READ-ONLY = **gate khách quan** thay helper-write (DB-write vi phạm read-only ADR-MOBILE-001 nếu auto). Xem §4 task B1. |

### 3.4 Device-token cho FCM CHƯA tồn tại (chặn EPIC-D)

| Điểm | Trạng thái @source |
|---|---|
| DocType "AC Mobile Device Token" | **CHƯA tồn tại** — grep `device_token`/`fcm_token`/`AC Mobile Device Token` toàn `assetcore/**/*.py,*.json` (trừ docs) = chỉ 5 hit, TẤT CẢ ở `tests/test_mobile_oas.py` (`:108-109` STUB path map, `:114-115` operationId, `:641` names-frozen guard) — KHÔNG có DocType/service/controller |
| `api/mobile/` hiện trạng | CHỈ `__init__.py` + `preflight.py` (KHÔNG `v1/`, KHÔNG `device_token.py`) |
| OpenAPI STUB | yaml `registerDeviceToken` + `unregisterDeviceToken` (STUB) — guard `test_mobile_oas.py:641` `test_mob_oas_06_device_token_names_frozen` |
| BA spec nguồn | [`06-push-fcm.md §2`](../06-push-fcm.md): 7 field (§2.1), `autoname=hash` (§2.2), `fcm_token` UNIQUE/UPSERT-dedup (§2.4), self-scope `permission_query_conditions`+`has_permission user==session.user` (§2.3), ÉP `user=session.user` chống spoof (§5.3), audit register/unregister NĐ98 (§5.4) |

---

## 4. Tasks (B1..B4)

> Mỗi task: mô tả + Files (Create/Modify exact path) + Acceptance (lệnh kiểm-được) + owner + tag [AUTO]/[HARD-STOP USER] + Dependencies. KHÔNG placeholder.

### B1 — Runbook + preflight helper tạo OAuth Client (7 điều kiện)

**Mô tả:** Khẳng định cơ chế provisioning = **runbook thủ công [`10 §1`](../10-deploy-ops.md) + preflight verifier READ-ONLY làm gate khách quan** (KHÔNG fixture/patch auto — §3.3). 7 điều kiện B-1: (1) `client_count>=1`; (2) `grant_type='Authorization Code'` (Implicit deprecated, không PKCE); (3) `response_type='Code'`; (4) `default_redirect_uri='assetcore://oauth/callback'` VÀ ∈ `redirect_uris` (custom-scheme native + PKCE S256); (5) `scopes='all openid'` (coarse — quyền thực = RBAC capability theo user); (6) `skip_authorization=0` (màn consent lần đầu); (7) `allowed_roles` non-empty (least-priv field-tech). "Helper idempotent" = **preflight verifier hiện hữu** (READ-ONLY, idempotent vì không ghi DB) — KHÔNG viết helper-write (DB-write = HARD-STOP, vi phạm read-only ADR-MOBILE-001). Nếu USER yêu cầu helper-write idempotent → đề xuất riêng đánh dấu `[HARD-STOP execute]`, KHÔNG mặc định.

- **Files (Modify):** `docs/mobile/completion/EPIC-B-auth-provisioning.md` (file này, §3.2/§3.3/B1) — TRỎ NGƯỢC `10 §1` + `03 §4` + `12`, KHÔNG nhân đôi bảng field.
- **Files (KHÔNG tạo):** không tạo fixture/patch/helper-write — quyết định giữ thủ công (§3.3).
- **Acceptance:**
  - `bench --site miyano run-tests --module assetcore.tests.test_mobile_preflight` → TC-MOB-PRE-01..09 xanh (drift-guard 7 điều kiện + count==0 no-raise + read-only).
  - Runbook [`10 §1`](../10-deploy-ops.md) step 1 liệt kê đủ 7 field khớp [`03 §4`](../03-auth-oauth2.md) (KHÔNG nhân đôi — TRỎ NGƯỢC).
- **Owner:** BA · **Tag:** `[AUTO]` (doc + test read-only) · phần TẠO record = **[HARD-STOP USER]** (xem B4).
- **Dependencies:** none (∥ EPIC-C). Cung cấp gate cho B4.

### B2 — Refresh-token flow + token lifetime (WIRE-not-write)

**Mô tả:** Khẳng định bằng `file:line` rằng provider Frappe ĐÃ hỗ trợ đầy đủ: refresh-token (`oauth.py:184-187` grant ⊇ `refresh_token`; `validate_refresh_token` status="Active" `:270-296`), revoke (RFC 7009, `oauth2.py:144/158-159`), PKCE S256 (`oauth.py:146-164`). Token lifetime = **3600s HARD-CODED** (oauthlib fallback, KHÔNG site_config knob — §3.1) = **KNOWN-LIMIT** `[ROADMAP]` Phase F (ADR-MOBILE-001 alt A7), KHÔNG chặn MVP. Auth-section response = **PASSTHROUGH OAuthlib** (KHÔNG AssetCore envelope) — `get_token` 200-keys `{access_token,refresh_token,expires_in,token_type=Bearer,scope?}`; grant-fail → 400 `OAuthError400` (key chung `error`); revoke → 200 empty `{}`. Client native route theo **HTTP status-line + key `error`** (KHÁC business path đọc `body.code`/`body.http_status`). Policy app: 401 → refresh 1 lần → retry; refresh-fail → re-auth (KHÔNG loop vô hạn). Đóng vòng backlog: thêm ví dụ refresh-on-401 sequence (đã có ở [`03 §1.3 (e)`](../03-auth-oauth2.md) + [`03 §2.5`](../03-auth-oauth2.md)).

- **Files (Modify):** `docs/mobile/completion/EPIC-B-auth-provisioning.md` (§3.1 + B2) — TRỎ NGƯỢC `03 §1/§2/§2.3.1`, KHÔNG re-litigate.
- **Files (KHÔNG sửa):** `frappe/integrations/oauth2.py` · `frappe/oauth.py` (core — WIRE-not-write, ADR-MOBILE-001 a).
- **Acceptance:**
  - `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` → `TC-MOB-OAUTH-TOKEN-01..05` xanh (passthrough `OAuthError400` 200-keys/400/revoke-empty guard).
  - **[HARD-STOP USER cloud]** smoke trên public HTTPS host: `http --form POST https://$HOST/api/method/frappe.integrations.oauth2.get_token grant_type=refresh_token refresh_token=$RT` → 200 `{access_token,...}` mới (KHÔNG bắt login lại) — sequence [`03 §1.3 (e)`](../03-auth-oauth2.md).
- **Owner:** BA · **Tag:** `[AUTO]` (doc + test read-only); smoke cloud = **[HARD-STOP USER]** (cần host + reload).
- **Dependencies:** Provider ready (§3.1, no-op code). Cloud smoke phụ thuộc **EPIC-G** (host/HTTPS/reload).

### B3 — Device-token DocType + service + endpoint (chặn EPIC-D)

**Mô tả:** Tạo DocType `AC Mobile Device Token` + service 3-tier + endpoint `register/unregister_device_token` để app native đăng ký FCM token (tiền-đề flow-6 push). Lớp này **CHỈ tạo registry + self-scope** — KHÔNG gửi push (kênh #3 `_dispatch` + FCM sender = **EPIC-D** task riêng). Bám spec BA [`06 §2`](../06-push-fcm.md): 7 field (§2.1) `user` Link reqd / `fcm_token` UNIQUE reqd / `platform` Select android·ios reqd / `device_label` / `app_version` / `last_seen` Datetime / `enabled` Check default 1; `autoname=hash` (§2.2); UPSERT dedup theo `fcm_token` (§2.4); service ÉP `user=frappe.session.user` chống spoof (§5.3); endpoint `@whitelist methods=[POST]` KHÔNG allow_guest (cần bearer §2.3); self-scope `permission_query_conditions`+`has_permission user==session.user` (§2.3 — pattern `permissions.py`); audit register/unregister NĐ98 (§5.4). KHÔNG thêm capability vào `CAPABILITY_MAP` (self-service gate bằng bearer + row-level §2.3). Gỡ 2 STUB khỏi `_STUB_PATHS` + bồi requestBody/response typed yaml (đồng pattern EPIC-C create path).

- **Files (Create):**
  - `assetcore/assetcore/doctype/ac_mobile_device_token/__init__.py`
  - `assetcore/assetcore/doctype/ac_mobile_device_token/ac_mobile_device_token.json` (7 field §2.1, autoname=hash, track_changes=1, perm: System Manager read-all + field-tech self)
  - `assetcore/assetcore/doctype/ac_mobile_device_token/ac_mobile_device_token.py` (controller delegate)
  - `assetcore/services/mobile_device_token.py` (`register_device_token(*, fcm_token, platform, device_label='', app_version='')` ÉP `user=session.user`, UPSERT dedup; `unregister_device_token(fcm_token)` set enabled=0 giữ audit; `invalidate_token(fcm_token)`; gọi `log_audit_event`)
  - `assetcore/api/mobile/v1/__init__.py` (handler `register/unregister_device_token`, `@whitelist methods=[POST]` KHÔNG allow_guest, function-name = operationId)
  - `assetcore/tests/test_mobile_device_token.py` (upsert dedup · ÉP user=session spoof-chặn · self-scope · unregister enabled=0 · invalidate)
- **Files (Modify):**
  - `assetcore/hooks.py` — thêm `AC Mobile Device Token` vào `permission_query_conditions` (self-scope) + `has_permission` (vendor isolation `_VENDOR_ROLE` pattern `permissions.py:46/90/188`). **Same-commit wiring gate** (định nghĩa gate → cùng commit wire hooks).
  - `assetcore/tests/test_mobile_oas.py` — gỡ 2 path `register/unregister_device_token` khỏi `_STUB_PATHS` (`:108-109`); update `_EXPECTED`/names-frozen (`:641`); assert requestBody `DeviceTokenRequest` typed.
  - `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — bồi `DeviceTokenRequest{fcm_token,platform,device_label?,app_version?}` requestBody (oneOf json+form) + response 200 typed cho 2 path (gỡ STUB).
- **Acceptance:**
  - `bench --site miyano run-tests --module assetcore.tests.test_mobile_device_token` → xanh (upsert dedup + spoof-chặn + self-scope + unregister enabled=0 + invalidate).
  - `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` → xanh (2 STUB rời, `DeviceTokenRequest` typed, names-frozen INTACT).
  - **[HARD-STOP USER]** `bench migrate` (tạo DocType) — SAU đó endpoint live HTTP cần `bench restart`/reload (gunicorn --preload).
- **Owner:** BA chốt spec/yaml + BE impl DocType/service/api/test · **Tag:** `[AUTO impl]` (code chờ deploy) + **[HARD-STOP USER]** (`bench migrate` tạo DocType + reload).
- **Dependencies:** B2 (register cần bearer→set_user — chưa e2e xác nhận OAuth bearer reach `api/mobile/v1`). CHẶN **EPIC-D** (kênh #3 push cần device-token registry). Impl chi tiết kênh #3/FCM sender = EPIC-D (KHÔNG thuộc B3).

### B4 — Preflight `ready=True` trên cloud (DoD-gate)

**Mô tả:** Sau khi USER tạo OAuth Client record (B1 runbook [`10 §1`](../10-deploy-ops.md)) → chạy preflight verifier xác nhận 7 điều kiện B-1 đạt → `ready=True`. Đây là **gate go/no-go A→B** ([`11-phase-a-exit.md §3`](../11-phase-a-exit.md)). count==0 hiện tại → `ready=False` + blocker "Chưa có OAuth Client — Phase B chưa provision" (`preflight.py:183`). Nếu `ready=False` + count>=1 → đọc `blockers` (VI) sửa record theo field-spec `03 §4` ([`12 §3.3`](../12-phase-b-preflight.md)). Lưu ý: nếu vừa đổi capability/Role Profile cho role field-tech → cần `bench migrate` HOẶC bust `ac_caps::*` + reload gunicorn để cap-set live HTTP (verifier chỉ chấm config OAuth Client, KHÔNG kiểm cap-set live — `12 §3.3`).

- **Files (KHÔNG tạo):** verifier ĐÃ CÓ (`preflight.py:146-220`) — B4 = thực thi + verify, KHÔNG viết code mới.
- **Acceptance:**
  - **[HARD-STOP USER]** tạo OAuth Client record (Desk → New `OAuth Client`, 7 field §3.2).
  - `bench --site miyano execute assetcore.api.mobile.preflight.verify_oauth_client` → `{"ready": true, "client_count": >=1, "blockers": []}`.
  - (Hiện trạng — chưa provision) cùng lệnh trên count==0 → `{"ready": false, "client_count": 0, "blockers": ["Chưa có OAuth Client — Phase B chưa provision."]}` (chạy được KHÔNG raise — chứng minh gate hoạt động).
- **Owner:** BA đặc tả gate · **USER** thực thi (tạo record) · **Tag:** **[HARD-STOP USER]** (DB-write tạo record).
- **Dependencies:** B1 (runbook+preflight). MỞ ĐƯỜNG **EPIC-G** (B-1 đạt là 1 trong B-1..B-8 prereq go-live, [`11 §2`](../11-phase-a-exit.md)).

---

## 5. Data model / Schema

> CHỈ task B3 thêm DocType. B1/B2/B4 = wire/doc/verify — KHÔNG thêm field/doctype. OAuth Client/Bearer Token = doctype core Frappe (KHÔNG sửa).

### 5.1 DocType `AC Mobile Device Token` (B3 — bám [`06 §2.1`](../06-push-fcm.md), KHÔNG bịa thêm field)

| Field | Fieldtype | reqd | Mô tả |
|---|---|---|---|
| `user` | Link → User | ✔ | Chủ sở hữu token. Mặc định = `frappe.session.user` lúc register (server ÉP — KHÔNG nhận từ client, §5.3 threat). |
| `fcm_token` | Data (Long Text nếu >140) | ✔ | FCM registration token do SDK cấp. **UNIQUE** (dedup §2.4). |
| `platform` | Select: `android` / `ios` | ✔ | Nền tảng thiết bị (MVP android trước). |
| `device_label` | Data | ✘ | Nhãn thiết bị do user/SDK đặt. |
| `app_version` | Data | ✘ | Phiên bản APK (debug/migration payload). |
| `last_seen` | Datetime | ✘ | Lần cuối token còn sống (cập nhật mỗi register/refresh/push-OK). |
| `enabled` | Check (default 1) | ✔ | Cờ opt-in/opt-out + invalidate. `0` ⇒ KHÔNG gửi push. |

- **autoname:** `hash` (system PK — token KHÔNG làm PK: dài + rotate; `fcm_token` UNIQUE lo dedup, §2.2).
- **track_changes:** 1 (audit register/modify, §5.4).
- **State:** không workflow_state (registry kỹ thuật — lifecycle qua `enabled` 1/0, §2.5). KHÔNG submittable.

### 5.2 OAuth Client (B1 — core Frappe, CHỈ ĐỌC/cấu hình, KHÔNG sửa schema)

Field checklist = [`03 §4`](../03-auth-oauth2.md) (10 field thật doctype `OAuth Client` @v15.107.2). 7 điều kiện B-1 verifier chấm = §3.2. KHÔNG nhân đôi bảng field — TRỎ NGƯỢC `03 §4`.

---

## 6. Security & Audit (RBAC · token · CORS · NĐ98)

| Khía cạnh | Trạng thái / Quyết định | Evidence |
|---|---|---|
| Quyền (1 SSoT) | bearer → `set_user(token.user)` → RBAC capability/DocPerm theo user. KHÔNG hệ quyền thứ 2 (scope coarse `all openid` KHÔNG là quyền thực). | `auth.py:667` · `rbac.py:156-168` · ADR-MOBILE-001 (b) |
| Scope leak | scope coarse KHÔNG đủ leo quyền (RBAC chặn); GUARD `test_mobile_capability_map.py` TC-MOB-CAP-01..06 (`len(CAPABILITY_MAP)==97`, version `v97.c30c69b8974d` đóng băng). | `03 §3.2` |
| Client secret | KHÔNG nhúng APK — PKCE S256 thay thế (public client). | `oauth.py:146-164` · `03 §2.4` |
| CSRF | Không áp dụng native (no cookie-session) — `validate_csrf_token` chỉ enforce khi có `csrf_token` cookie. | `auth.py:83-98` · ADR-MOBILE-001 (e) |
| Token at rest | Keychain/Keystore HĐH (KHÔNG SharedPreferences plaintext, KHÔNG log token). | `03 §2.4` |
| Revocation | RFC 7009 (logout/mất máy) → status="Revoked" → từ chối ngay `validate_bearer_token`. | `oauth2.py:144` · `oauth.py:262-268` |
| Preflight gate quyền | `frappe.only_for("System Manager")` (DocPerm `OAuth Client` read = System Manager); KHÔNG allow_guest; READ-ONLY (KHÔNG ghi DB, count bất biến). | `preflight.py:171` · TC-MOB-PRE-09 |
| `allowed_roles` least-priv | OAuth Client `allowed_roles` = CHỈ role field-tech (KTV) — giảm bề mặt (T5). | `03 §4` · `10 §1` step 1 |
| Device-token spoof (B3) | server ÉP `user=session.user` (KHÔNG nhận từ client) + row-level self-scope `permission_query_conditions`+`has_permission` ⇒ KHÔNG tạo/sửa token cho user khác. | `06 §5.3` · `permissions.py:46/90/188` pattern |
| Device-token audit (B3, NĐ98) | register/unregister sinh record + audit trail (`log_audit_event`) — truy xuất ai-đăng-ký-thiết-bị-nào-khi-nào (NĐ98 §5.4). `enabled=0` giữ audit (KHÔNG xoá cứng). | `06 §5.4` |
| CORS | **NGOÀI EPIC-B** → EPIC-G. Native APK MVP KHÔNG cần CORS (no browser engine, D-STACK). CẤM wildcard `*` prod (Frappe luôn echo `Allow-Credentials:true` — credential-echo T3). | ADR-MOBILE-004 (c) · `frappe/app.py:283-284` |
| Transport | bearer-over-HTTPS bắt buộc — public HTTPS host = **EPIC-G** (hiện chưa có, `02 §4`). | `02 §4` |

---

## 7. Tham chiếu

### 7.1 Chương docset (00–13)

- **MASTER EPIC-B:** [`13-be-completion-roadmap.md §4`](../13-be-completion-roadmap.md) — DoD/dependency/AUTO-HARD-STOP gốc.
- **Auth deep-dive:** [`03-auth-oauth2.md`](../03-auth-oauth2.md) — §1 sequence PKCE · §2 token lifecycle/passthrough · §2.3.1 failure-modes · §3 scope↔capability 1 SSoT · §4 OAuth Client field checklist.
- **Runbook go-live:** [`10-deploy-ops.md §1`](../10-deploy-ops.md) — numbered steps tạo OAuth Client (USER · HARD-STOP).
- **Preflight:** [`12-phase-b-preflight.md`](../12-phase-b-preflight.md) — verifier READ-ONLY 7 điều kiện B-1 + cách đọc report.
- **Push design (B3 spec nguồn):** [`06-push-fcm.md §2/§5`](../06-push-fcm.md) — DocType device-token 7 field, RBAC self-scope, audit NĐ98.
- **Exit gate Phase A:** [`11-phase-a-exit.md §1/§2/§3`](../11-phase-a-exit.md) — traceability matrix 6 flow + B-1 prereq + go/no-go.
- **Feasibility:** [`02-deploy-feasibility.md §1/§4/§7`](../02-deploy-feasibility.md) — provider sẵn sàng + blocker host/CORS.
- **Cross-EPIC:** EPIC-C [`04-api-contract.md`](../04-api-contract.md) (userinfo/whoami path); EPIC-G [`08-security-compliance.md`](../08-security-compliance.md) + [`10 §2-§5`](../10-deploy-ops.md); EPIC-D [`06-push-fcm.md`](../06-push-fcm.md) (kênh #3 impl).

### 7.2 ADR

- [`ADR-MOBILE-001.md`](../ADR-MOBILE-001.md) — (a) WIRE-not-write · (b) 1 SSoT quyền (scope coarse) · (e) no-CSRF native · alt A7 token-TTL `[ROADMAP]` Phase F.
- [`ADR-MOBILE-002.md`](../ADR-MOBILE-002.md) — FCM Admin SDK HTTP v1 trực tiếp (KHÔNG relay) — liên quan B3→EPIC-D.
- [`ADR-MOBILE-004.md`](../ADR-MOBILE-004.md) — (a) rate-limit ngoài core · (c) CORS list-origin (EPIC-G).

### 7.3 Lessons-learned / DONE-gate spec-contract

- **LL-DEPLOY-01:** gunicorn `--preload` (boot Mon Jun 8 08:32) — sửa `api/*.py`/`services/*.py` SAU 08:32 + DocType mới (B3) chỉ live `run-tests`/`execute` fresh-import, CHƯA live HTTP tới khi USER `bench restart`/reload.
- **LL-DEPLOY-03:** 4-bước go-live HARD-STOP: `bench migrate` (OAuth Client/Bearer Token native + device-token + bust `ac_caps`) → `bench restart` → `site_config` → verify preflight.
- **DONE-gate spec-contract:** lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope (KHÔNG raise→HTTP-4xx); 2 loại 403 (dispatcher-403 guest/no-token vs in-handler cap-403 thiếu quyền). **B2 ngoại lệ:** auth-section = PASSTHROUGH OAuthlib (KHÔNG envelope) — route theo HTTP status-line + `error`, KHÁC business path.
- **Same-commit wiring rule (B3):** định nghĩa gate `permission_query_conditions`/`has_permission` → CÙNG commit wire vào `hooks.py`.

### 7.4 Provider Frappe (CHỈ ĐỌC — KHÔNG sửa)

- `apps/frappe/frappe/integrations/oauth2.py` · `apps/frappe/frappe/oauth.py` · `apps/frappe/frappe/auth.py` · `apps/frappe/frappe/integrations/doctype/oauth_bearer_token/oauth_bearer_token.py`.
- AssetCore: `assetcore/api/mobile/preflight.py` · `assetcore/services/shared/rbac.py` · `assetcore/permissions.py`.

---

## 8. Rủi ro

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | USER tạo OAuth Client sai 1/7 điều kiện (vd `default_redirect_uri` không ∈ `redirect_uris`, hoặc `grant_type=Implicit`) → provider reject ở authorize/get_token | Cao | Preflight verifier (B4) chấm 7 điều kiện trả blocker VI cụ thể field sai + giá trị hiện tại; chạy SAU mỗi sửa record ([`12 §3.3`](../12-phase-b-preflight.md)). |
| R2 | Quên reload gunicorn sau đổi capability/Role Profile cho field-tech → cap-set stale, token cấp nhưng RBAC deny (LL-DEPLOY-01) | Cao | B4 note: đổi cap → `bench migrate` HOẶC bust `ac_caps::*` + reload (HARD-STOP USER); verifier KHÔNG kiểm cap-set live → smoke nghiệp vụ thật (EPIC-V) mới phát hiện. |
| R3 | Token TTL 3600s hard-coded không đủ/quá dài cho field-tech ngoài hiện trường (mất sóng) | Trung bình | Refresh-token (B2) bù: 401 → refresh im lặng (KHÔNG login lại). Đổi TTL = `[ROADMAP]` Phase F (ADR alt A7) — KHÔNG chặn MVP. |
| R4 | B3 device-token quên ÉP `user=session.user` → spoof register cho user khác (leo quyền nhận push) | Cao | Service ÉP `user=frappe.session.user` (KHÔNG nhận từ client) + row-level self-scope; test `test_mobile_device_token.py` assert spoof-chặn (B3 Acceptance). |
| R5 | B3 quên wire `hooks.py` cùng commit (gate định nghĩa nhưng không active) → self-scope dead-gate (token user A đọc được token user B) | Cao | Same-commit wiring rule (§7.3); test self-scope assert cross-user isolation. |
| R6 | `fcm_token` không UNIQUE → trùng record → push 2 lần cùng thiết bị | Trung bình | UNIQUE constraint DB + UPSERT dedup theo `fcm_token` (§5.1, `06 §2.4`); test upsert-dedup. |
| R7 | Helper-write idempotent tạo OAuth Client tự động (nếu làm) vi phạm read-only ADR-MOBILE-001 + DB-write HARD-STOP | Trung bình | Quyết định giữ runbook thủ công + preflight READ-ONLY gate (§3.3, B1); helper-write CHỈ làm khi USER yêu cầu rõ + tag `[HARD-STOP execute]`. |
| R8 | Cloud smoke B2 (refresh/revoke) chạy trước khi EPIC-G provision host/HTTPS → không có endpoint reachable | Trung bình | B2 cloud smoke phụ thuộc EPIC-G (dependency rõ ở §4 B2); test read-only `TC-MOB-OAUTH-TOKEN-*` làm proxy cho tới khi host sẵn sàng. |
