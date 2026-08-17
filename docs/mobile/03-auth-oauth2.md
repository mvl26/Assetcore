# 03 — Mobile BE: Auth deep-dive — OAuth2 Authorization Code + PKCE (S256) + refresh

| Mục | Giá trị |
|---|---|
| Initiative | AssetCore Mobile — backend-for-mobile |
| Phase | **A — Kiến trúc & Feasibility** (vòng 2 / PHASE A · A2 Auth deep-dive) |
| Bám quyết định | **D-AUTH** (OAuth2 + refresh) · D-MVP (field-tech) · D-STACK (native) — `00-overview.md §2` |
| Owner | BA Lead + System Architect (mobile) |
| Trạng thái | In Progress (Phase A) |
| Cập nhật | 2026-06-09 |

> **Mục đích:** đặc tả ĐẦY ĐỦ luồng xác thực native end-to-end (Authorization Code + PKCE S256 + refresh + revoke), vòng đời token, ánh xạ scope↔capability (1 SSoT), và checklist đăng ký OAuth Client. **KHÔNG impl** — chỉ chốt hợp đồng để Phase B (provision) + repo native (Phase D) bám theo.
> Mọi claim kỹ thuật trích **evidence `file:line` đã VERIFY read-only** tại **Frappe v15.107.2** (oauthlib 3.3.1, site `miyano`). KHÔNG có claim bịa.
> **Đặt tên:** giữ dãy dewey-decimal liền — `02` đã dùng cho `02-deploy-feasibility.md` (A1) ⇒ doc này là **`03-auth-oauth2.md`** (convention `00-overview.md §6`: "Số kế tiếp cấp khi có doc mới"). KHÔNG đè file A1.
> **Chỉ mục docset:** [`00-overview.md`](./00-overview.md) · [`01-architecture.md`](./01-architecture.md) · [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) · [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)

---

## 0. Context / Scope / Actor

### 0.1 D-AUTH — quyết định nền (in nguyên, KHÔNG re-litigate)

> **Xác thực mobile dùng OAuth2 (Authorization Code + PKCE) với access-token ngắn hạn + refresh token + revoke.** WIRE provider OAuth2 có sẵn của Frappe — KHÔNG tự viết OAuth. Bearer token → `set_user` → RBAC capability hiện hữu áp dụng nguyên vẹn (1 SSoT, không hệ quyền thứ 2). Session-cookie web KHÔNG tái dùng cho native. (`00-overview.md §2 D-AUTH`)

### 0.2 Scope tài liệu này

| Trong scope (Phase A — đặc tả) | Ngoài scope |
|---|---|
| Sequence Authorization Code + PKCE S256 end-to-end (6 bước) | Tạo OAuth Client record (Phase B — HARD-STOP USER) |
| Vòng đời token (TTL, refresh, revoke, storage) | Set `allow_cors` / public HTTPS host (Phase B deploy) |
| Scope↔capability invariant (1 SSoT) | Map scope→capability THỰC THI (Phase C cân nhắc) |
| Spec field OAuth Client (checklist Phase B) | Push/offline (Phase E) · token-TTL knob (Phase F) |
| Bồi auth-section OpenAPI (3 path auth) | Bồi 6 path nghiệp vụ schema chi tiết (Phase C) |

### 0.3 Actor

| Actor | Vai trò trong auth flow |
|---|---|
| **App native** (Flutter/RN, repo riêng — D-STACK) | OAuth client công khai (public client): sinh `code_verifier`/`code_challenge`, mở `/authorize`, đổi `code`→token tại `/get_token`, lưu token Keychain/Keystore, gắn bearer mọi request, refresh khi 401, revoke khi logout. KHÔNG nhúng `client_secret`. |
| **Frappe BE** (provider) | `frappe.integrations.oauth2.*` — authorize / get_token / revoke / introspect / openid_configuration. KHÔNG viết code (chỉ cấu hình). |
| **Field-technician** (người dùng) | Đăng nhập 1 lần trong WebView OAuth (màn `/authorize` → login Frappe), sau đó app dùng refresh-token im lặng. |
| **USER / Admin** (HARD-STOP) | Tạo OAuth Client record (Phase B), set site_config, reload gunicorn. KHÔNG thuộc BA. |

---

## 1. Sequence: Authorization Code + PKCE (S256) end-to-end

> Luồng chuẩn cho **public client** (native app không giữ bí mật). PKCE (RFC 7636) thay vai trò `client_secret`: app chứng minh chính nó là bên đã khởi tạo request bằng cặp `code_verifier`/`code_challenge`.

### 1.1 Sơ đồ 6 bước

```
   App native (public client)                    Frappe BE (provider)
   ──────────────────────────                    ────────────────────
(a) sinh code_verifier (random 43-128 ký tự)
    code_challenge = BASE64URL(SHA256(verifier))
    code_challenge_method = S256
            │
(b)  GET /api/method/frappe.integrations.oauth2.authorize
         ?client_id&redirect_uri&response_type=code
         &scope=all openid&code_challenge&code_challenge_method=S256
            │ ───────────────────────────────────────────────►  authorize() [oauth2.py:75, allow_guest]
            │                                                    Guest? → 302 /login (oauth2.py:79-82)
            │                                                    user login → lưu code_challenge(+method)
            │                                                       vào "OAuth Authorization Code" (oauth.py:89-91)
            │ ◄─────────────────────────────────────────────── 302 redirect_uri?code=<authcode>
   app bắt redirect (custom-scheme assetcore://oauth/callback)
            │
(c)  POST /api/method/frappe.integrations.oauth2.get_token
         grant_type=authorization_code & code=<authcode>
         & redirect_uri & client_id & code_verifier=<verifier>
            │ ───────────────────────────────────────────────►  get_token() [oauth2.py:124, allow_guest]
            │                                                    validate_grant_type ⊇ authorization_code (oauth.py:187)
            │                                                    PKCE S256: BASE64URL(SHA256(verifier)) == code_challenge?
            │                                                       (oauth.py:157-164) — sai → False → reject
            │ ◄─────────────────────────────────────────────── 200 {access_token, refresh_token, expires_in, token_type=Bearer}
   lưu access+refresh vào Keychain/Keystore
            │
(d)  GET/POST /api/method/assetcore.api.<imm>.<fn>
         Authorization: Bearer <access_token>
            │ ───────────────────────────────────────────────►  validate_oauth() [auth.py:633]
            │                                                    verify bearer → frappe.set_user(token.user) [auth.py:667]
            │                                                    rbac.can(cap) → has_permission (rbac.py:156-168)
            │ ◄─────────────────────────────────────────────── 200 envelope nghiệp vụ (hoặc 403 thiếu cap)
            │
(e)  (khi access hết hạn / nhận 401)
     POST /api/method/frappe.integrations.oauth2.get_token
         grant_type=refresh_token & refresh_token=<refresh>
            │ ───────────────────────────────────────────────►  get_token() [oauth2.py:124]
            │                                                    validate_grant_type ⊇ refresh_token (oauth.py:187)
            │                                                    validate_refresh_token status=Active (oauth.py:270-296)
            │ ◄─────────────────────────────────────────────── 200 {access_token mới, refresh_token, expires_in}
            │
(f)  (logout / mất máy)
     POST /api/method/frappe.integrations.oauth2.revoke_token
         token=<access_or_refresh> [& token_type_hint]
            │ ───────────────────────────────────────────────►  revoke_token() [oauth2.py:145, allow_guest]
            │                                                    RFC 7009 → status="Revoked" (oauth.py:262-268)
            │ ◄─────────────────────────────────────────────── 200
```

### 1.2 Chi tiết từng bước + evidence

| Bước | Mô tả | Tham số chính | Evidence (Frappe v15.107.2) |
|---|---|---|---|
| **(a)** | App sinh `code_verifier` (chuỗi ngẫu nhiên 43-128 ký tự unreserved) → `code_challenge = BASE64URL-no-pad( SHA256(code_verifier) )` (chuẩn S256). | `code_verifier`, `code_challenge`, `code_challenge_method=S256` | Client-side (RFC 7636). BE verify đúng công thức S256: `oauth.py:157-164` (sha256 → b64 → `+`→`-`, `/`→`_`, bỏ `=`). |
| **(b)** | App mở `/authorize` (WebView/Custom Tab). Nếu Guest → 302 `/login`; sau login BE lưu `code_challenge` + method vào `OAuth Authorization Code`, rồi 302 về `redirect_uri?code=...`. | `client_id`, `redirect_uri`, `response_type=code`, `scope` (`all openid`), `code_challenge`, `code_challenge_method=S256` | `authorize` whitelisted `allow_guest=True` — `oauth2.py:74-75`; redirect login khi Guest — `oauth2.py:79-82`; lưu challenge — `oauth.py:89-91`. |
| **(c)** | App đổi `code`→token. BE: validate grant_type, **PKCE check** (tính lại challenge từ `code_verifier` so với cái đã lưu), trả token. | `grant_type=authorization_code`, `code`, `redirect_uri`, `client_id`, **`code_verifier`** | `get_token` whitelisted `allow_guest=True` — `oauth2.py:123-124`; grant hợp lệ — `oauth.py:187`; PKCE S256 verify — `oauth.py:146-164`; thiếu `code_verifier` khi có challenge → xoá code + reject — `oauth.py:151-155`. |
| **(d)** | App gắn `Authorization: Bearer <access_token>` mọi request nghiệp vụ. BE verify → `set_user` → RBAC capability áp nguyên vẹn. | header `Authorization: Bearer <token>` | `validate_oauth` — `auth.py:633`; `frappe.set_user(token.user)` — `auth.py:667`; `rbac.can` → `has_permission` — `rbac.py:156-168`. |
| **(e)** | Khi access hết hạn (hoặc nhận 401), app đổi `refresh_token`→access mới (KHÔNG bắt user login lại). | `grant_type=refresh_token`, `refresh_token` | grant hợp lệ — `oauth.py:187`; `get_original_scopes`/`validate_refresh_token` (status=Active) — `oauth.py:244-296`. |
| **(e2) userinfo / whoami** | Sau khi có access token, app GET `openid_profile` → lấy **danh tính** (tên + role) hiển thị màn KTV (đóng mảnh flow-1). RAW claims, KHÔNG envelope. | header `Authorization: Bearer <token>` (scope `openid`) | `openid_profile` whitelisted **KHÔNG `allow_guest`** (bearer bắt buộc) — `oauth2.py:163`; claims `get_userinfo` — `oauth.py:530-555`; set `frappe.local.response = body` (passthrough RAW) — `oauth2.py:172-174`. |
| **(f)** | Logout / mất máy: thu hồi token (RFC 7009). | `token`, `token_type_hint` (`access_token`/`refresh_token`) | `revoke_token` whitelisted `allow_guest=True` — `oauth2.py:144-145`; set `status="Revoked"` — `oauth.py:262-268` (method `revoke_token` def `oauth.py:252`). |

> **OIDC discovery (tuỳ chọn, hỗ trợ tự-cấu-hình app):** `openid_configuration` (whitelisted `allow_guest=True` — `oauth2.py:180-181`) trả issuer + endpoint URLs (`id_token_signing_alg_values_supported=["HS256"]`). App có thể đọc để lấy `authorization_endpoint`/`token_endpoint` thay vì hard-code.
> **Introspection (tuỳ chọn, server-to-server):** `introspect_token` (whitelisted `allow_guest=True` — `oauth2.py:205-206`, RFC 7662) cho biết token còn `active` + `exp`/`scope`. Native app KHÔNG cần (app tự biết hạn qua `expires_in`); hữu ích cho gateway/diagnostic.

### 1.3 Ví dụ curl / httpie (minh hoạ — host = public HTTPS Phase B)

> Thay `$HOST` = public HTTPS host (Phase B), `$CLIENT_ID` = `client_id` của OAuth Client record (Phase B tạo). `redirect_uri` native = custom-scheme `assetcore://oauth/callback`.

**(a) Sinh PKCE (ví dụ shell — app native dùng crypto lib tương đương):**
```bash
# code_verifier: 43-128 ký tự unreserved
code_verifier=$(openssl rand -base64 60 | tr -d '\n=+/' | cut -c1-64)
# code_challenge = BASE64URL-no-pad(SHA256(verifier))  [khớp oauth.py:157-164]
code_challenge=$(printf '%s' "$code_verifier" \
  | openssl dgst -binary -sha256 \
  | openssl base64 | tr '+/' '-_' | tr -d '=')
```

**(b) Authorize (mở trong WebView/Custom Tab — không phải curl thuần vì cần user login):**
```
GET https://$HOST/api/method/frappe.integrations.oauth2.authorize
      ?client_id=$CLIENT_ID
      &response_type=code
      &redirect_uri=assetcore://oauth/callback
      &scope=all%20openid
      &code_challenge=$code_challenge
      &code_challenge_method=S256
# → sau login → 302 assetcore://oauth/callback?code=<AUTHCODE>
```

**(c) Đổi code → token (httpie):**
```bash
http --form POST https://$HOST/api/method/frappe.integrations.oauth2.get_token \
  grant_type=authorization_code \
  code=$AUTHCODE \
  redirect_uri=assetcore://oauth/callback \
  client_id=$CLIENT_ID \
  code_verifier=$code_verifier
# → 200 {"access_token":"...","refresh_token":"...","expires_in":3600,"token_type":"Bearer","scope":"all openid"}
```

**(d) Gọi nghiệp vụ với bearer:**
```bash
http GET "https://$HOST/api/method/assetcore.api.imm00.get_asset_scan_info?token=<qr_token>" \
  "Authorization: Bearer $ACCESS_TOKEN"
```

**(e) Refresh:**
```bash
http --form POST https://$HOST/api/method/frappe.integrations.oauth2.get_token \
  grant_type=refresh_token \
  refresh_token=$REFRESH_TOKEN
# → 200 {"access_token":"...(mới)","refresh_token":"...","expires_in":3600,...}
```

**(f) Revoke:**
```bash
http --form POST https://$HOST/api/method/frappe.integrations.oauth2.revoke_token \
  token=$ACCESS_TOKEN \
  token_type_hint=access_token
# → 200
```

> ⚠️ Native dùng **custom-scheme** `assetcore://oauth/callback` (không phải `http(s)://`). App đăng ký scheme này ở OS (Android intent-filter / iOS URL Type) để bắt redirect. `redirect_uri` phải KHỚP `redirect_uris`/`default_redirect_uri` đã đăng ký trong OAuth Client (Phase B) — sai → reject.

---

## 2. Vòng đời token (TTL · refresh · revoke · storage)

> **🔒 QUYẾT ĐỊNH CHỐT B1 (Phase B) — AUTH-SECTION = PASSTHROUGH OAuthlib (KHÔNG AssetCore envelope):**
> `get_token` / `revoke_token` trả **NGUYÊN body của provider Frappe/oauthlib** — KHÔNG bọc `SuccessEnvelope`/`ErrorEnvelope` của AssetCore. Lý do: **tái dùng provider có sẵn, KHÔNG viết lại logic OAuth**; client field-tech parse **body OAuth chuẩn** (RFC 6749 §5). Đây là **phân biệt rõ với endpoint nghiệp vụ** (business path qua `handle()` → Error envelope `{success,error,code,http_status}`). Frappe core = **SSoT** cho auth-section body.
> **SOURCE-CHARACTERIZED @Frappe v15.107.2 (oauthlib 3.3.1) — body THẬT @file:line:**
> - **Success 200** (`get_token`): oauthlib `BearerToken.create_token` sinh `{access_token, expires_in, token_type='Bearer', scope?, refresh_token?}` (`oauthlib/oauth2/rfc6749/tokens.py:309-326`); Frappe set NGUYÊN: `frappe.local.response = body` (`oauth2.py:137`). KHÔNG wrap.
> - **Error 400** (`get_token`, grant-fail đường THƯỜNG): khi `body.error` → `http_status_code=400` (`oauth2.py:132-135`), body = oauthlib `OAuth2Error.twotuples` = `{error, error_description?, error_uri?}` (`oauthlib/.../errors.py:80-88`; `invalid_grant` = `errors.py:301` status 400).
> - **Error 4xx** (đường HIẾM, `except (FatalClientError, OAuth2Error)`): `generate_json_error_response` (`oauth.py:563-575`) → `{description, status_code, error}`.
> - **Revoke 200** (`revoke_token`): LUÔN 200 body **rỗng** `frappe._dict({})` (`oauth2.py:158-159`; RFC 7009 §2.2 — 200 kể cả token không tồn tại / lỗi nuốt `except…pass` `oauth2.py:154-155`).
>
> Hợp đồng máy-đọc: OpenAPI component **`OAuthError400`** (union 2 shape; `error` = key chung required) wire `'400'`→`OAuthError400` **CHỈ** lên `getOAuthToken`; `revokeOAuthToken` 200 = empty object. `OAuthError400` **KHÁC** Error envelope + **KHÁC** `FrappeRawError` của business pre-handler (401/403/429). Guard = `assetcore/tests/guards/test_mobile_oas.py` (`TC-MOB-OAUTH-TOKEN-01..05`). Bảng error 2-lớp: [`04-api-contract.md §5b`](./04-api-contract.md).

### 2.1 Access token — TTL cố định 3600s (không có site_config knob)

- **Default access-token lifetime = 3600s (1 giờ).** oauthlib `BearerToken` áp fallback `self.expires_in = expires_in or 3600` (oauthlib 3.3.1, `tokens.py`); Frappe KHÔNG override (`get_oauth_server` chỉ khởi tạo `WebApplicationServer(oauth_validator)` — `oauth2.py:22`, KHÔNG truyền `token_expires_in`).
- `expires_in` gán vào record từ token generator — `oauth.py:214` (`otoken.expires_in = token["expires_in"]`).
- `OAuth Bearer Token` controller tính **`expiration_time = creation + timedelta(seconds=expires_in)`** trong `validate()` — `oauth_bearer_token.py:27-31`.
- Validate mỗi request: `oauth.py:229-241` `validate_bearer_token` — pass khi `now < expiration_time` AND `status != "Revoked"` (+ scope membership).
- **KHÔNG có site_config knob đổi TTL.** Đổi 3600s → giá trị khác phải wrap/fork `get_oauth_server` ⇒ **dẫn `ADR-MOBILE-001` alternative A7** (backlog Phase F, KHÔNG chặn MVP).

### 2.2 Refresh token — gia hạn không bắt login lại

- `grant_type=refresh_token` được chấp nhận — `oauth.py:187`.
- App dùng refresh-token (dài hạn hơn access) để lấy access mới khi access hết hạn → trải nghiệm "đăng nhập 1 lần".
- BE `validate_refresh_token` chỉ chấp token `status="Active"` — `oauth.py:270-296`.

### 2.3 Revoke — thu hồi (RFC 7009)

- `revoke_token` (`oauth2.py:144-145`, `allow_guest=True`) → set record `status="Revoked"` (`oauth.py:262-268`; method def `oauth.py:252`). Dùng cho logout an toàn / mất máy → token bị từ chối ngay ở `validate_bearer_token` (check `status != "Revoked"`).
- **Body 200 = RỖNG (empty object).** `revoke_token` LUÔN trả `frappe.local.response = frappe._dict({})` + `http_status_code = status or 200` (`oauth2.py:158-159`). RFC 7009 §2.2: server trả 200 **kể cả token không tồn tại / sai** — exception bị nuốt `except (FatalClientError, OAuth2Error): pass` (`oauth2.py:154-155`) ⇒ KHÔNG có 400. PASSTHROUGH — KHÔNG envelope. Hợp đồng: `revokeOAuthToken` 200 = `{}` (`additionalProperties:false`).

### 2.3.1 FAILURE-MODES `get_token` — body THẬT để repo native handle (B1)

> Token-endpoint trả **OAuth-standard body** (passthrough §2 intro) — KHÔNG Error envelope. App native parse theo key **`error`** (RFC 6749 §5.2), KHÔNG dùng `code`/`http_status` của business envelope. Mọi grant-fail dưới đi **đường THƯỜNG** (`get_token` oauth2.py:127-135 → `create_token_response` trả body có `error` → `http_status_code=400`).

| Failure-mode | grant_type | HTTP | `error` (THẬT) | Body shape (passthrough) | Hành vi app bắt buộc |
|---|---|---|---|---|---|
| **Wrong PKCE verifier** (verifier ≠ challenge đã lưu) | `authorization_code` | **400** | `invalid_grant` | `{error:"invalid_grant", error_description?:…}` | Hỏng flow → **re-auth** (chạy lại sequence từ (a) — sinh verifier/challenge mới). KHÔNG retry cùng code. |
| **Expired / đã dùng authorization code** | `authorization_code` | **400** | `invalid_grant` | `{error:"invalid_grant", error_description?:…}` | **re-auth** (code dùng-1-lần / hết hạn). |
| **Invalid / revoked / expired refresh_token** | `refresh_token` | **400** | `invalid_grant` | `{error:"invalid_grant", error_description?:…}` | Xoá token Keychain/Keystore → **re-auth** (KHÔNG loop refresh — §2.5). |
| **Thiếu/sai grant_type / param** | (bất kỳ) | **400** | `invalid_request` / `unsupported_grant_type` | `{error:"invalid_request", error_description?:…}` | Lỗi client-side (sửa request) — KHÔNG retry mù. |
| **Client/credential sai** (đường hiếm) | (bất kỳ) | **400/401** | `invalid_client` | `{description:…, status_code:4xx, error:"invalid_client"}` (generate_json_error_response oauth.py:567-573) | Kiểm cấu hình `client_id` (Phase B). |

- **Evidence shape:** `error`/`error_description`/`error_uri` = oauthlib `OAuth2Error.twotuples` (`errors.py:80-88`); mã `invalid_grant` = `errors.py:301` (status 400). Đường hiếm `{description, status_code, error}` = `generate_json_error_response` (`oauth.py:567-573`). Hai shape hợp nhất trong component **`OAuthError400`** — `error` là **key CHUNG** (luôn có) ⇒ client an toàn nhánh theo `error`.
- **Hợp đồng client (non-negotiable):** auth-section đọc **HTTP status line + key `error`** (KHÁC business path đọc `body.code`/`body.http_status` — [`04-api-contract.md §5`](./04-api-contract.md)). Mọi `invalid_grant` ⇒ **re-auth** (KHÔNG retry vô hạn).

### 2.4 Storage — Keychain/Keystore, KHÔNG cookie/CSRF

- Native lưu access+refresh trong **iOS Keychain / Android Keystore** (an toàn HĐH), **KHÔNG dùng cookie**.
- Bearer auth KHÔNG tạo cookie-session ⇒ CSRF check SKIP tự nhiên: `validate_csrf_token` chỉ enforce khi tồn tại `frappe.session.data.csrf_token` (cookie-session) — `auth.py:83-98`. ⇒ Native **KHÔNG cần CSRF token** (khác hẳn FE web cookie+CSRF). **Dẫn `ADR-MOBILE-001` decision (e).**
- PKCE thay `client_secret` ⇒ APK KHÔNG nhúng bí mật.

### 2.5 Policy app (chuẩn hoá cho repo native)

| Tình huống | Hành vi app bắt buộc |
|---|---|
| Request trả **401 / token expired** | Thử **refresh** (`grant_type=refresh_token`) MỘT lần → retry request gốc với access mới. |
| **Refresh thất bại** (refresh hết hạn / `Revoked` / lỗi) | Xoá token khỏi Keychain/Keystore → **re-auth** (chạy lại sequence từ bước (a)). KHÔNG vòng lặp refresh vô hạn. |
| **Logout chủ động / mất máy** | Gọi **revoke** (2.3) → xoá token local. |
| **Lưu token** | Keychain/Keystore. KHÔNG SharedPreferences/UserDefaults plaintext, KHÔNG log token. |

### 2.6 userinfo / whoami — danh tính KTV sau đăng nhập (C4)

> **Mục đích (flow-1):** sau khi đổi `code`→token, app cần hiển thị **danh tính người dùng** (tên + role KTV) ở màn chính / header. Endpoint OIDC userinfo của Frappe core đáp ứng việc này — KHÔNG cần endpoint AssetCore riêng.

- **Endpoint:** `GET /api/method/frappe.integrations.oauth2.openid_profile` — `operationId getUserInfo`.
- **Bearer bắt buộc:** `openid_profile` whitelisted **KHÔNG `allow_guest`** (`oauth2.py:163`) ⇒ guest/no-token/expired → **dispatcher-401** (RAW Frappe). Scope cần `openid`.
- **Claims (RAW passthrough — KHÔNG envelope AssetCore):** `openid_profile` set `frappe.local.response = body` trực tiếp (`oauth2.py:172-174`) ⇒ trả nguyên dict OIDC, **KHÔNG bọc `{success,data}` hay `{message:}`**. Claims từ `get_userinfo` (`oauth.py:530-555`):

| Claim | Kiểu | Nguồn @oauth.py | Ghi chú |
|---|---|---|---|
| `sub` | string \| **null** | `:531-535` (User Social Login.userid provider=frappe) | null nếu user chưa có social-login record |
| `name` | string | `:537` (`join(first_name,last_name)`) | App hiển thị tên KTV |
| `given_name` | string | `:538` (`first_name`) | |
| `family_name` | string | `:539` (`last_name`) | |
| `email` | string | `:540` (`user.email`) | |
| `picture` | string \| **null** | `:529-548` (`user_image` resolve URL) | null nếu không có ảnh |
| `roles` | array\<string\> | `:541` (`frappe.get_roles(user)`) | App map sang nhãn KTV / persona |
| `iss` | string | `:542` (server URL) | issuer |

- **Sequence refresh-on-401 (đóng vòng OAuth2 + refresh):**

```text
app → GET openid_profile  (Authorization: Bearer <access cũ/hết hạn>)
   ← 401 (dispatcher, RAW Frappe)
app → POST get_token  grant_type=refresh_token & refresh_token=<refresh>   [§1.1 bước (e)]
   ← 200 {access_token mới, refresh_token, expires_in}
app → GET openid_profile  (Authorization: Bearer <access MỚI>)  [retry MỘT lần]
   ← 200 {sub, name, given_name, family_name, email, picture, roles[], iss}   (RAW)
# refresh fail (refresh Revoked/hết hạn) → xoá token Keychain/Keystore → re-auth (§2.5)
```

> Quy tắc refresh-on-401 GIỐNG mọi request nghiệp vụ (§2.5): refresh MỘT lần → retry; fail → re-auth. KHÔNG vòng lặp refresh vô hạn.

---

## 3. Scope ↔ Capability — Invariant 1 SSoT

> **Khẳng định invariant (bám `ADR-MOBILE-001` decision (b)):** Frappe OAuth scope là **gate THÔ on/off** ở tầng oauthlib; **AssetCore `rbac.py` là SSoT quyền chi tiết** áp qua chuỗi bearer→`set_user`. **KHÔNG dựng hệ quyền thứ 2.**

### 3.1 Hai tầng — tách bạch rõ

| Tầng | Cơ chế | Granularity | Evidence |
|---|---|---|---|
| **OAuth scope** (coarse) | `validate_scopes` = requested scopes ⊆ client allowed scopes (`get_client_scopes`) | THÔ on/off (mức client). Default OAuth Client `scopes = "all openid"`. KHÔNG biết tới `CAPABILITY_MAP`. | `oauth.py:51-54` |
| **AssetCore capability** (fine — SSoT) | `rbac.can(cap)` → `frappe.has_permission(DocType, ptype)` trên `frappe.session.user`; deny-on-unknown-cap (stale-safe) | Chi tiết theo từng action × DocType × Role Profile/DocPerm | `rbac.py:156-168` |

- **Số liệu verified runtime (site `miyano`, 2026-06-09):** `CAPABILITY_MAP` = **97 capability**; `CAP_SET_VERSION = v97.c30c69b8974d` (hash theo nội dung sorted keys — `rbac.py:147-150`). `can()`/`require()` là 2 helper API — `rbac.py:156` / `rbac.py:171`.
- **Vì sao 1 SSoT đủ:** bearer→`set_user(token.user)` (`auth.py:667`) đặt `frappe.session.user` = chính user đó ⇒ MỌI capability gate web (`asset.read`, `corrective.create`, `pm.create`…) áp dụng NGUYÊN VẸN cho request mobile. Audit NĐ98 (SHA-256 lifecycle chain) giữ đúng actor.

### 3.2 Quyết định Phase A (chốt)

- **Client scope = `all openid`** (coarse) — quyền THỰC vẫn đúng nhờ RBAC capability/DocPerm theo user. Scope KHÔNG phải là quyền thực.
- **Map scope→capability-group:** chỉ ở mức Ý TƯỞNG để **Phase C cân nhắc** (vd scope `field-tech` ↔ nhóm cap `{asset.read, corrective.create, pm/repair/calibration.create, *.read}`), **KHÔNG thực thi vòng này**. Nếu Phase C chọn map → vẫn là lớp coarse PHỤ, KHÔNG thay RBAC. **Dẫn `ADR-MOBILE-001` decision (b)** + Consequences "Scope coarse".
- **Anti-pattern (cấm):** KHÔNG đọc/parse scope rồi tự gate quyền ở lớp mobile → đó là "hệ quyền thứ 2" → drift + lỗ leo quyền (loại A2 trong ADR Alternatives).
- **Invariant `scope-coarse → RBAC-capability-là-gate-thực` nay CÓ GUARD máy-đọc (A14):** quyết định "RBAC capability là gate THỰC, scope chỉ THÔ" được củng cố bằng test `assetcore/tests/integration/test_mobile_capability_map.py` (`TC-MOB-CAP-01..06`). Guard introspect `CAPABILITY_MAP` (SSoT `rbac.py`) và khẳng định 10 endpoint MVP ↔ matrix [`11-phase-a-exit.md §1`](./11-phase-a-exit.md) ánh xạ đúng capability + binding `(DocType, ptype)`; đồng thời chặn cap-creep (`len(CAPABILITY_MAP)==97`, version đóng băng `v97.c30c69b8974d`) ⇒ KHÔNG thể lén dựng "hệ quyền thứ 2" cho mobile (drift = test ĐỎ). Củng cố trực tiếp `ADR-MOBILE-001` decision (b).

> **Áp dụng per-màn (A4):** map QUYỀN/capability cho từng màn MVP (asset.read / corrective.create / pm/repair/calibration.create + `*.read`) bám SSoT này → [`05-personas-mvp.md §5`](./05-personas-mvp.md); persona `corrective.read-only` KHÔNG vào được màn báo-hỏng (parity 3-tầng, `05 §1.3`). **Hợp đồng cap↔endpoint của các màn này được GUARD `TC-MOB-CAP-*` (`test_mobile_capability_map.py`) chốt vào SSoT `rbac.py` — xem [`11-phase-a-exit.md §1`](./11-phase-a-exit.md) (matrix + cross-link guard).**

---

## 4. Spec đăng ký OAuth Client — CHECKLIST Phase B (HARD-STOP USER)

> ⚠️ **KHÔNG tạo record vòng này.** Tạo `OAuth Client` thuộc Phase B — **HARD-STOP USER** (DB write). Đây là CHECKLIST field thật (verified tại doctype `OAuth Client`, Frappe v15.107.2) để USER cấu hình.
> **Verified runtime:** `OAuth Client` count = **0**, `Social Login Key` count = **0** (site `miyano`) ⇒ Phase B PHẢI tạo client; KHÔNG cần Social Login Key cho vai trò provider.

| Field (fieldname thật) | Fieldtype | Giá trị cho app native | reqd | Ghi chú |
|---|---|---|---|---|
| `app_name` | Data | vd `AssetCore Mobile (field-tech)` | ✅ | Tên hiển thị app. |
| `client_id` | Data | (auto-gen) | — | Public client id → app dùng ở (b)/(c). |
| `client_secret` | Data | (auto-gen — **KHÔNG nhúng APK**) | — | Native = public client → KHÔNG dùng secret; PKCE thay thế. |
| `scopes` | Text | `all openid` (default) | ✅ | Coarse (xem §3). |
| `grant_type` | Select (`Authorization Code`/`Implicit`) | **`Authorization Code`** | — | BẮT BUỘC Authorization Code (không Implicit — đã deprecated/không PKCE). |
| `response_type` | Select (`Code`/`Token`) | **`Code`** (default) | — | Khớp `response_type=code` ở bước (b). |
| `redirect_uris` | Text | `assetcore://oauth/callback` | — | Custom-scheme native (mỗi dòng 1 URI nếu nhiều). |
| `default_redirect_uri` | Data | `assetcore://oauth/callback` | ✅ | Phải KHỚP `redirect_uri` app gửi — sai → reject. |
| `allowed_roles` | Table MultiSelect (`OAuth Client Role`) | giới hạn role KTV (field-tech) | — | Chỉ user có role này được cấp token → giảm bề mặt. |
| `skip_authorization` | Check | `0` | — | `0` = hiện màn Allow/Deny lần đầu; đặt `1` chỉ khi first-party trusted muốn bỏ màn consent. |

> Sau khi tạo record (Phase B): vẫn cần (a) public HTTPS host + (b) `allow_cors` (nếu test browser/Swagger) + (c) reload gunicorn → các blocker này ở `02-deploy-feasibility.md §7`. **Tất cả HARD-STOP USER.**
> **Quy trình THỰC THI go-live có thứ tự (runbook)** — biến checklist field này thành numbered steps tạo OAuth Client + CORS + host + FCM + smoke curl: **[`10-deploy-ops.md §1`](./10-deploy-ops.md)** (`10` = execute; `03 §4` = field-spec). KHÔNG nhân đôi field — `10` TRỎ về bảng này.

---

## 5. Security & Audit

| Khía cạnh | Trạng thái | Evidence / Ghi chú |
|---|---|---|
| Transport | bearer-over-HTTPS bắt buộc (Phase B provision TLS) | `02-deploy-feasibility.md §4` (chưa có public HTTPS host). |
| Client secret | KHÔNG nhúng APK — PKCE S256 thay thế | `oauth.py:146-164`. |
| CSRF | Không áp dụng cho native (no cookie-session) | `auth.py:83-98`; `ADR-MOBILE-001 (e)`. |
| Token at rest | Keychain/Keystore HĐH | §2.4. |
| Revocation | RFC 7009 hỗ trợ (logout/mất máy) | `oauth2.py:144`; `oauth.py:262-268`. |
| Quyền | 1 SSoT — RBAC capability/DocPerm theo user | `rbac.py:156-168`; §3. |
| Audit trail (NĐ98) | bearer→set_user ⇒ lifecycle SHA-256 chain ghi đúng actor | `utils/lifecycle.py`; `00-overview.md §5`. |
| Scope leak | scope coarse `all openid` — KHÔNG là quyền thực, KHÔNG đủ để leo quyền (RBAC chặn) | §3.2. |

---

## 6. KPI / Acceptance (Phase A)

| Tiêu chí | Đo bằng |
|---|---|
| Sequence Auth Code+PKCE end-to-end (a→f) đặc tả đủ, mỗi bước có evidence `file:line` | §1.1–1.3 |
| Vòng đời token (TTL 3600s/refresh/revoke/storage) + policy app | §2 |
| Scope↔capability invariant 1 SSoT khẳng định | §3 |
| OAuth Client field checklist (field thật doctype) | §4 |
| OpenAPI auth-section bồi (3 path + securityScheme) khớp doc, YAML parse hợp lệ | `openapi/assetcore-mobile.openapi.yaml` §auth |
| **B1 — token-endpoint RESPONSE contract đóng băng (passthrough OAuthlib)**: get_token 200-keys + 400 `OAuthError400` + revoke 200 empty, source-characterized @file:line, guard chạy được | §2 + §2.3.1 · `OAuthError400` component · `TC-MOB-OAUTH-TOKEN-01..05` |
| KHÔNG sửa code nghiệp vụ; KHÔNG tạo record; working tree để user review | git status |

---

## Tham chiếu chéo

- **Quyết định + evidence (decision a/b/e + alternative A7 token-TTL):** [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- **Tổng quan + D-AUTH + glossary OAuth2/PKCE/refresh/revoke:** [`00-overview.md`](./00-overview.md) §2 (D-AUTH) · §7
- **Kiến trúc auth-flow + versioning:** [`01-architecture.md`](./01-architecture.md)
- **Hợp đồng envelope / error (shape 401/403 · ErrorCode · quirk HTTP-200 wrapper · error 2-lớp AUTH vs BUSINESS):** [`04-api-contract.md`](./04-api-contract.md) §3 · §4 · §5 · **§5b (B1 — AUTH passthrough `OAuthError400` vs BUSINESS Error envelope)** — ⚠️ A2 live-finding: 401 Guest business-path hiện trả raw Frappe traceback, KHÔNG envelope sạch (backlog A14; client native fallback HTTP line). Auth-section (get_token/revoke) = passthrough OAuthlib (§2 / §2.3.1 — guard `TC-MOB-OAUTH-TOKEN-*`).
- **Feasibility read-only (provider/CORS/blocker triển khai):** [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) §1 · §7
- **Bảo mật & Tuân thủ (A7) — threat model token/scope/IDOR + NĐ98 audit-from-mobile:** [`08-security-compliance.md`](./08-security-compliance.md) (T1 brute-force oauth2 · T2 IDOR-qua-bearer · T4 token storage · T5 scope leo quyền) · ADR mô hình bảo mật: [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md)
- **OpenAPI auth-section (hợp đồng):** [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)
- **Exit gate (A11) — flow login trong traceability matrix + OAuth Client prereq (B-1):** [`11-phase-a-exit.md`](./11-phase-a-exit.md) §1 (Flow 1 — authorizeOAuth/getOAuthToken/revokeOAuthToken `file:line`) · §2 B-1 (checklist §4 này = nguồn).
- **Pre-flight verifier (B0-PREFLIGHT) — kiểm checklist §4 này thành hợp đồng chạy được:** [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) (verifier READ-ONLY `verify_oauth_client()` chấm 7 điều kiện B-1; §4 này = field-spec nguồn, `12` TRỎ NGƯỢC — KHÔNG nhân đôi).
- **RBAC SSoT:** `assetcore/services/shared/rbac.py` (97 cap · `can`/`require` · `CAP_SET_VERSION`)
- **Guard endpoint↔capability (A14 — củng cố invariant §3/§3.2):** `assetcore/tests/integration/test_mobile_capability_map.py` (`TC-MOB-CAP-01..06`) — 10 endpoint MVP ↔ matrix [`11-phase-a-exit.md §1`](./11-phase-a-exit.md) ↔ SSoT `rbac.py`; binding `(DocType, ptype)` + anti-cap-creep (`len==97`) + version `v97.c30c69b8974d` đóng băng (drift = test ĐỎ).
- **Provider Frappe:** `apps/frappe/frappe/integrations/oauth2.py` · `apps/frappe/frappe/oauth.py` · `apps/frappe/frappe/auth.py`
