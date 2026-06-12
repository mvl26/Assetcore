# 08 — AssetCore Mobile BE: Bảo mật & Tuân thủ (Security & Compliance)

| Mục | Giá trị |
|---|---|
| Initiative | AssetCore Mobile — backend-for-mobile (BE-only) + APK native (repo riêng) |
| Phase | **PHASE A — Kiến trúc & Feasibility** (vòng 1 / A7) |
| Vai trò doc | **SSoT bảo mật mobile** — hợp nhất ghi chú rải rác (`06-push-fcm §5.3`, `ADR-MOBILE-001`, `03-auth-oauth2`) thành 1 chương threat-model + NĐ98 audit-from-mobile |
| Owner | BA Lead + System Architect (mobile) + Security reviewer |
| Trạng thái docs | In Progress (Phase A) |
| Cập nhật | 2026-06-09 |

> **Mục đích:** chốt **mô hình bảo mật** cho bề mặt mobile (threat model ≥7 mối đe doạ, mỗi dòng có evidence `file:line`) + chứng minh **action từ mobile sinh audit NĐ98 ĐÚNG actor** (bearer→`set_user`→hash-chain `utils/lifecycle.py`) + **phân loại mitigation 3 nhóm** (đã-có / config-HARD-STOP-USER / repo-native). **KHÔNG impl** — đặc tả + checklist. Mọi claim verify tại source **Frappe v15.107.2** (read-only).
>
> **KHÔNG trùng nội dung** `02-deploy-feasibility` (gaps deploy) / `03-auth-oauth2` (sequence OAuth) / `06-push-fcm` (cơ chế push): chương này là **góc nhìn bảo mật hợp nhất** — tham chiếu chéo, KHÔNG sao chép.

---

## 0. Context · Scope · Actor

### 0.1 Context

Initiative mobile mở **bề mặt tấn công mới**: endpoint OAuth2 public-facing + bearer token trên thiết bị di động (mất/trộm máy) + native HTTP-client gọi thẳng API (không qua browser CORS) + token lưu trên thiết bị người dùng. Web SPA cũ dựa session-cookie + CSRF + same-origin; mobile **đổi mô hình tin cậy** sang bearer-over-HTTPS. Chương này định danh bề mặt + mitigation **TRƯỚC** khi Phase B provision public host.

Nguyên tắc nền (bám 3 quyết định `00-overview §2` + `ADR-MOBILE-001`):

- **1 SSoT quyền — KHÔNG hệ quyền thứ 2.** Bearer→`set_user`→`rbac.py` capability + DocPerm áp nguyên vẹn (`ADR-MOBILE-001` decision b). Mobile KHÔNG dựng lớp quyền song song.
- **KHÔNG sửa Frappe core.** Thiếu sót core (rate-limit oauth2, CORS wildcard) chặn ở **tầng ngoài** (nginx/reverse-proxy + `site_config`), KHÔNG patch `frappe/`.
- **Audit NĐ98 bất biến.** SHA-256 lifecycle chain (`utils/lifecycle.py`) áp tự nhiên qua `set_user` — actor = KTV thật, KHÔNG service-account. KHÔNG thêm field/đường audit mới cho mobile.

### 0.2 Scope tài liệu này

| Trong scope (Phase A — đặc tả) | Ngoài scope |
|---|---|
| Threat model bề mặt mobile (T1–T7) + evidence `file:line` | Pentest thực tế / scan tự động (Phase F hardening) |
| NĐ98 audit-from-mobile (chứng minh actor đúng) | Thêm field/đường audit mới (KHÔNG cần) |
| Phân loại mitigation 3 nhóm | Thực thi config go-live (HARD-STOP USER — Phase B) |
| Checklist security go-live (đặc tả) | Patch Frappe core (CẤM) |
| KPI / acceptance bảo mật | Token TTL knob (đã chốt 3600s cố định — `03-auth §2` + `ADR-001 A7`) |

### 0.3 Actor (mặt bảo mật)

| Actor | Vai trò bảo mật |
|---|---|
| **KTV hiện trường** | Chủ thể hợp pháp; bearer token = danh tính. Mất máy ⇒ revoke (T4). |
| **Kẻ tấn công mạng** | Brute-force oauth2 (T1), MITM (T7), replay (T6). |
| **Kẻ tấn công có token rò** | IDOR (T2), scope abuse (T5), token leak (T4). |
| **Trình duyệt độc hại (CORS)** | Lợi dụng `allow_cors` cấu hình sai (T3). |
| **USER (admin go-live)** | Chịu trách nhiệm config nhóm (b): `allow_cors` list-origin, TLS, rate-limit nginx, `site_config` creds (HARD-STOP). |
| **Repo native (đội mobile)** | Chịu trách nhiệm nhóm (c): token storage Keychain/Keystore, cert-pinning, không log token. |

---

## 1. Threat Model — bề mặt mobile (≥7 mối đe doạ)

> Quy ước cột **Mitigation**: `[ĐÃ-CÓ]` = có sẵn ở core/AssetCore tự nhiên · `[CONFIG]` = config go-live HARD-STOP USER (nhóm b §3) · `[NATIVE]` = trách nhiệm repo native (nhóm c §3). Evidence = `file:line` verify tại source Frappe v15.107.2 (read-only).

| T-ID | Mô tả mối đe doạ | Bề mặt | Mitigation (đã-có / cần) | Evidence `file:line` |
|---|---|---|---|---|
| **T1** | **Brute-force / DoS endpoint OAuth2.** 4 endpoint `authorize`/`get_token`/`revoke_token`/`introspect_token` đều `allow_guest=True` và **KHÔNG có `@rate_limit`** ⇒ kẻ tấn công có thể spam đoán code/credential hoặc làm cạn tài nguyên. | Public OAuth2 endpoint (Phase B mở ra Internet) | `[CONFIG]` **Rate-limit tầng nginx/reverse-proxy** cho `/api/method/frappe.integrations.oauth2.*` (req/IP + burst). **KHÔNG sửa frappe core.** PKCE + short-code-TTL giảm giá trị đoán code. | `oauth2.py:74` (authorize `allow_guest`), `:123` (get_token), `:144` (revoke_token), `:205` (introspect_token); grep `rate_limit` trong `oauth2.py` = **0 match** (xác nhận thiếu rate-limit ở core) |
| **T2** | **IDOR qua bearer.** Token bị lộ → BE `set_user(token.user)` → request chạy DƯỚI user đó. Nếu RBAC/row-level yếu, kẻ có token user A đọc/ghi data ngoài phạm vi. | Mọi endpoint nghiệp vụ gọi qua bearer | `[ĐÃ-CÓ]` Bearer→`set_user` ⇒ **DocPerm + `permission_query_conditions` + `has_permission` áp nguyên vẹn** = chính lớp đã bảo vệ web. Vendor isolation row-level (`_VENDOR_ROLE` scoped `responsible_technician`). **KHÔNG hệ quyền thứ 2** — token chỉ là cách xác thực, không nới quyền. | `auth.py:633` (validate_oauth), `:667` (`set_user(token.user)`); `permissions.py:46` (`_VENDOR_ROLE`), `:90`/`:193`/`:209` (vendor scoped + `ac_asset_has_permission` IDOR-guard); `rbac.py:156-168` (`can`→`has_permission`) |
| **T3** | **CORS misconfig — credential echo.** Khi `frappe.conf.allow_cors` set, BE LUÔN trả `Access-Control-Allow-Credentials: true` + echo `Origin` của request. Nếu set `allow_cors='*'` ở prod ⇒ MỌI origin gửi credential được phép (CSRF/credential-theft từ web). | Web origin độc hại (native HTTP-client KHÔNG dính CORS — D-STACK; rủi ro là cho cookie-web cùng host) | `[CONFIG]` **CẤM `allow_cors='*'` ở prod** — dùng **list origin tường minh** (chỉ host hợp pháp). Native app KHÔNG cần CORS (không browser) ⇒ tốt nhất KHÔNG bật wildcard chỉ vì mobile. | `app.py:269` (đọc `frappe.conf.allow_cors`), `:275` (nhánh `!= "*"` mới lọc list — wildcard BỎ QUA lọc), `:283` (`Access-Control-Allow-Credentials: "true"`), `:284` (echo `Origin`) |
| **T4** | **Token leak / storage không an toàn.** Access/refresh token nằm trên thiết bị; lưu sai chỗ (plaintext file, log, SharedPreferences thường) → trộm máy/root/log-scrape lấy được, mạo danh. | Thiết bị di động (mất/trộm/root) + log app | `[NATIVE]` Token lưu **Keychain (iOS) / Keystore (Android)**, **KHÔNG cookie/plaintext/log**. `[ĐÃ-CÓ]` Refresh-rotation + access ngắn hạn (TTL 3600s) thu hẹp cửa sổ. `[ĐÃ-CÓ+CONFIG]` **Revoke khi mất máy** qua `revoke_token` (RFC 7009) — vô hiệu token tức thì server-side. | `oauth2.py:144` (revoke_token, RFC 7009); `oauth.py:187` (grant `refresh_token` — rotation); access TTL 3600s (`03-auth §2` + `oauth_bearer_token.py`) |
| **T5** | **Scope leo quyền.** OAuth scope mặc định thô (`all openid`) ⊄ `CAPABILITY_MAP`; nếu coi scope = quyền thực ⇒ ngộ nhận "có scope all = làm mọi thứ". | Tầng OAuth client / hiểu sai mô hình quyền | `[ĐÃ-CÓ]` Scope chỉ là **gate THÔ on/off** ở oauthlib; **RBAC capability + DocPerm là gate CUỐI** (deny-on-unknown-cap, stale-safe). `[CONFIG]` Least-privilege: cấp **scope-set tối thiểu** cho OAuth Client mobile (Phase B), KHÔNG mặc định nới rộng. 1 SSoT — bearer→`set_user` nên quyền thực luôn theo user×DocPerm. | `oauth.py:56` (get_default_scopes), `:51-54` (validate_scopes coarse); `rbac.py:156-168` (capability gate cuối); `auth.py:667` (set_user ⇒ DocPerm áp) |
| **T6** | **Replay / duplicate write.** Mạng field-tech chập chờn → app retry → BE tạo bản ghi nghiệp vụ TRÙNG (báo hỏng/WO/asset ×2) ⇒ data sai + audit nhiễu. | Đường ghi (POST nghiệp vụ) qua mạng yếu | `[ĐÃ-CÓ-SPEC / Phase E]` **Idempotency-key** client-gen (UUID/ULID header `Idempotency-Key`) — BE dedupe key→first-response, replay trả response gốc (KHÔNG tạo record thứ 2). Conflict = optimistic-lock qua `modified`→409. Đặc tả đầy đủ ở `ADR-MOBILE-003` + `07-offline-sync §3-4`. | `07-offline-sync.md §3` (idempotency contract); `ADR-MOBILE-003`; component yaml `IdempotencyKey`/`IfMatch` (đã có) |
| **T7** | **MITM / nghe lén đường truyền.** Bearer token + payload nghiệp vụ qua HTTP không mã hoá hoặc TLS giả mạo (MITM proxy, Wi-Fi công cộng bệnh viện) ⇒ lộ token + sửa request. | Đường truyền mạng (dev hiện HTTP:80) | `[CONFIG]` **HTTPS/TLS BẮT BUỘC** ở public host (Phase B reverse-proxy + cert hợp lệ); dev HTTP:80 server_name rỗng **KHÔNG dùng prod**. `[NATIVE]` **Khuyến nghị cert-pinning** (pin cert/public-key của host) ở repo native để chặn MITM bằng cert giả. | `app.py` (CORS chỉ ý nghĩa khi public); `02-deploy-feasibility §servers` (dev HTTP:80 — KHÔNG prod); `00-overview §2 D-STACK` (native HTTP-client) |

**Phủ bề mặt:** T1 (endpoint public) · T2 (quyền/IDOR) · T3 (CORS) · T4 (token/storage) · T5 (scope) · T6 (replay/ghi) · T7 (đường truyền). 7 mối đe doạ phủ đủ 4 lớp: **mạng** (T1/T3/T7), **xác thực/token** (T4/T5), **uỷ quyền/quyền** (T2/T5), **toàn vẹn dữ liệu/ghi** (T6).

> **Không trùng `06-push-fcm §5.3`:** §5.3 chỉ liệt kê threat của **device-token push** (spoof-register, server-key leak, dead-token spam). Chương 08 phủ **toàn bề mặt mobile** (auth/token/CORS/IDOR/replay/MITM). Threat push của §5.3 GIỮ NGUYÊN ở 06; 08 tham chiếu, KHÔNG lặp.

---

## 2. NĐ98 — Audit-from-mobile (action sinh audit ĐÚNG actor)

> **Khẳng định:** action thực hiện TỪ mobile sinh **audit trail NĐ98 với actor = KTV thật** (KHÔNG service-account / KHÔNG ẩn danh), **KHÔNG cần thêm field hay đường audit mới**. Cơ chế = chuỗi bearer→`set_user`→hash-chain hiện hữu áp NGUYÊN VẸN.

### 2.1 Chuỗi đảm bảo actor đúng

```
APK gửi Authorization: Bearer <token>
        │
        ▼  validate_oauth (auth.py:633) — token còn hạn + không Revoked
frappe.set_user( OAuth Bearer Token.user )   ── auth.py:667
        │   ⇒ frappe.session.user = chính KTV (KHÔNG Administrator/service-account)
        ▼
service nghiệp vụ (báo hỏng / WO / commission…) chạy DƯỚI user đó
        │
        ▼  log_audit_event(asset, event, actor=session.user, …)   ── utils/lifecycle.py:33
SHA-256 hash-chain (prev_hash → hash)        ── lifecycle.py:9 (_compute_hash) / :18 (sha256)
        │
        ▼  verify_audit_chain(asset)          ── lifecycle.py:97 / :110-113 (kiểm tra liên tục)
bản ghi NĐ98 bất biến, actor = KTV thật, truy xuất ai-làm-gì-khi-nào
```

### 2.2 Vì sao đủ — KHÔNG cần audit mới cho mobile

| Yêu cầu NĐ98 | Cơ chế hiện hữu áp cho mobile | Evidence |
|---|---|---|
| Truy xuất **đúng actor** (ai thao tác) | `set_user(token.user)` đặt `frappe.session.user` = KTV thật ⇒ `frappe.session.user` mà `log_audit_event` ghi LÀ KTV (không phải gateway/service) | `auth.py:667`; `lifecycle.py:33` |
| **Bất biến** (không sửa lén) | hash-chain SHA-256: mỗi record gắn `prev_hash`→`hash_sha256`; sửa giữa chuỗi ⇒ `verify_audit_chain` phát hiện | `lifecycle.py:9`/`:18`/`:110-113` |
| **Liên tục** (không xoá khoảng giữa) | `verify_audit_chain` kiểm `expected == hash` AND `prev == prev_hash` tuần tự | `lifecycle.py:97`/`:110-113` |
| Cùng đường web | Mobile tái dùng NGUYÊN service nghiệp vụ ⇒ cùng `log_audit_event` web đang gọi (không nhánh riêng) | `ADR-MOBILE-001` decision c (reuse-endpoint) |

**Kết luận:** mobile **KHÔNG** thêm field audit, **KHÔNG** đường audit song song, **KHÔNG** service-account chung. Bằng chứng NĐ98 cho action-từ-mobile = bằng chứng action-từ-web, chỉ khác kênh xác thực (bearer thay cookie). Điều kiện duy nhất: **token phải map đúng 1 user thật** (đảm bảo bởi OAuth Client allowed_roles + KHÔNG cấp token cho tài khoản dùng-chung — checklist §4).

---

## 3. Phân loại Mitigation — 3 nhóm trách nhiệm

> Mỗi mitigation ở §1 thuộc đúng 1 nhóm. Phân loại này quyết định **AI làm + KHI NÀO** + ranh giới HARD-STOP.

### (a) ĐÃ-CÓ tự nhiên — không cần làm gì thêm ở mobile

| Mitigation | Phủ threat | Cơ chế | Evidence |
|---|---|---|---|
| Bearer→`set_user`→DocPerm/RBAC (1 SSoT) | T2, T5 | Quyền web áp nguyên vẹn cho mobile; deny-on-unknown-cap | `auth.py:667`; `rbac.py:156-168`; `permissions.py` vendor isolation |
| CSRF-skip cho bearer (không cần CSRF token) | (mô hình) | `validate_csrf_token` chỉ throw khi có session csrf-token (cookie); bearer-only KHÔNG có session csrf ⇒ bỏ qua an toàn (không phải lỗ hổng — bearer thay vai trò chống-CSRF của cookie) | `auth.py:83-98` |
| Audit-chain SHA-256 đúng actor | (NĐ98) | `set_user`→`log_audit_event`→hash-chain, bất biến | `lifecycle.py:9/18/33/97/110-113`; `auth.py:667` |
| Access-token ngắn hạn + refresh-rotation | T4 | TTL 3600s cố định; refresh-token đổi access | `oauth.py:187`; `03-auth §2` |
| Revoke token (RFC 7009) | T4 | Vô hiệu token tức thì (mất máy/logout) | `oauth2.py:144` |
| PKCE S256 (public client) | T1, T4 | Code không đổi được token nếu thiếu `code_verifier` | `oauth.py:89-91`/`:146-164` |
| Idempotency-key + optimistic-lock (SPEC) | T6 | Dedupe ghi + conflict 409 (đặc tả Phase E) | `07-offline-sync §3-4`; `ADR-MOBILE-003` |

### (b) CONFIG go-live — HARD-STOP USER (KHÔNG agent tự làm)

> Các mục này **thuộc quyền USER** (Phase B). Doc CHỈ đặc tả checklist; agent KHÔNG `set_config`/`bench restart`/sửa nginx. Cùng nhóm `assetcore_qr_base_url`/FCM creds ở `02-deploy-feasibility §7` + `06-push-fcm §5.2`.

| Config | Phủ threat | Đặc tả (USER thực hiện go-live) |
|---|---|---|
| **Rate-limit nginx cho `oauth2.*`** | T1 | Thêm `limit_req` cho location `/api/method/frappe.integrations.oauth2.*` (req/IP + burst). **TẦNG NGOÀI — KHÔNG sửa frappe core.** |
| **`allow_cors` = list origin tường minh** | T3 | Set `frappe.conf.allow_cors` = `["https://<host-hợp-pháp>"]`. **CẤM `'*'` ở prod.** Native KHÔNG cần CORS ⇒ cân nhắc KHÔNG bật wildcard. |
| **HTTPS/TLS public host** | T7 | Reverse-proxy (nginx) + cert hợp lệ + redirect HTTP→HTTPS. Dev HTTP:80 KHÔNG dùng prod. |
| **FCM / QR creds trong `site_config`** | (vận hành) | `fcm_service_account_path`/`fcm_project_id` + `assetcore_qr_base_url` — KHÔNG commit, KHÔNG trả qua API (`06 §5.2`). |
| **Least-privilege OAuth Client scope-set** | T5 | Cấp scope tối thiểu cho client mobile; allowed_roles = chỉ role field-tech (KHÔNG cấp token cho tài khoản dùng-chung — giữ audit đúng actor §2). |

### (c) Repo-native — trách nhiệm đội mobile (ngoài repo `assetcore`)

| Trách nhiệm | Phủ threat | Đặc tả (đội native impl ở repo riêng) |
|---|---|---|
| **Token storage Keychain/Keystore** | T4 | Lưu access+refresh trong secure storage OS; KHÔNG plaintext/SharedPreferences thường/cookie. |
| **Cert-pinning** | T7 | Pin cert/public-key host trong HTTP-client (Dio/OkHttp); chặn MITM cert giả. |
| **KHÔNG log token** | T4 | Không in token/Authorization header ra log/crash-report/analytics. |
| **PKCE generation** | T1, T4 | Client sinh `code_verifier`/`code_challenge` (S256) đúng RFC 7636 (BE verify `oauth.py:146-164`). |

---

## 4. Checklist Security Go-live (đặc tả — Phase B/F)

> Đánh dấu hoàn tất khi USER (b) + đội native (c) thực thi. Agent KHÔNG tick hộ — chỉ liệt kê.
> **Quy trình deploy/ops THỰC THI go-live có thứ tự** (numbered steps OAuth2/CORS/host/FCM/versioning + checklist pre-flight/execute/smoke curl + rollback): **[`10-deploy-ops.md`](./10-deploy-ops.md)**. Checklist §4 này = **bảo mật** (T1–T7); `10 §6` = **deploy/ops execute** — bổ trợ, KHÔNG nhân đôi.

- [ ] **(b)** nginx `limit_req` áp cho `/api/method/frappe.integrations.oauth2.*` (T1)
- [ ] **(b)** `allow_cors` = list origin tường minh, `'*'` KHÔNG xuất hiện ở prod `site_config` (T3)
- [ ] **(b)** Public host = HTTPS, cert hợp lệ, HTTP→HTTPS redirect; HTTP:80 KHÔNG expose mobile (T7)
- [ ] **(b)** OAuth Client (Phase B): grant=Authorization Code, PKCE bật, redirect = native-scheme, allowed_roles = field-tech, scope-set least-privilege (T5)
- [ ] **(b)** FCM creds + `assetcore_qr_base_url` trong `site_config` (KHÔNG commit) (`06 §5.2`)
- [ ] **(b)** **PROD TẮT `allow_error_traceback` (System Setting=0)** — chống leak traceback/SQL ở body 401/403/429 (T-leak). Gate THẬT = `is_traceback_allowed()` (`response.py:60-65`) đọc `get_system_settings("allow_error_traceback")` (System Setting field `system_settings.json:263`, fieldtype Check, **default 1 = ON** ⇒ prod mặc-định LEAK). Dùng ở `response.py:36/:182/:190/:203`. **GHI RÕ: gate KHÔNG phải `developer_mode` / `site_config`** — đổi qua desk hoặc `bench --site <site> execute` (verify `is_traceback_allowed → False`); LIVE HTTP chỉ SAU reload gunicorn (`--preload`).
- [ ] **(b)** KHÔNG cấp token cho tài khoản dùng-chung (giữ actor audit đúng — §2)
- [ ] **(c)** Token lưu Keychain/Keystore; KHÔNG plaintext/log (T4)
- [ ] **(c)** Cert-pinning bật trong HTTP-client native (T7)
- [ ] **(c)** PKCE S256 sinh đúng RFC 7636 (T1/T4)
- [ ] **(c)** Flow revoke khi logout/mất máy gọi `revoke_token` (T4)
- [ ] **(verify)** Action-từ-mobile xuất hiện ở audit-chain với actor = KTV thật (`verify_audit_chain` pass) (§2)
- [ ] **(F)** Pentest / scan bề mặt OAuth2 + token (Phase F hardening)

---

## 5. Security gate — Acceptance bảo mật (EPIC-G G4)

### 5.1 Lệnh gate bảo mật (DoD EPIC-G G4)

> **Gate tổng hợp** chạy SAU khi G1–G3 xong (deploy + host/HTTPS + tắt traceback). Phần `[AUTO]`
> (test guard introspection) chạy local; phần `curl` public-host = **HARD-STOP USER** (cần G2 live trên
> cloud). 6 invariant: (a) no-traceback-leak · (b) CORS no-wildcard · (c) no token-leak · (d) 429 `Retry-After`
> · **(e) audit-actor NĐ98** (chuỗi `bearer→set_user→log_audit_event(actor=session.user)→verify_audit_chain`
> ghi actor = KTV thật — §2) · **(f) host_name/issuer go-live** (`host_name` set ⇒ `get_url()` + OIDC
> `openid_configuration issuer == public host`, **KHÔNG `http://miyano`** nội bộ — flow-2 QR deep-link/issuer).
> Cơ chế "in-handler-4xx arrive HTTP-200" → smoke đọc `body.http_status`, KHÔNG status-line (xem `EPIC-G §3.2`).

| # | Gate | Lệnh kiểm | PASS khi | Owner |
|---|---|---|---|---|
| **(a)** | **no-traceback-leak** (`allow_error_traceback` OFF) | **[AUTO]** `bench --site <site> run-tests --module assetcore.tests.test_mobile_security_gate` (GUARD-1 `verify_oauth_client()` no-raise + no-marker) · **[HARD-STOP USER]** `curl -s https://<host>/api/method/<auth-method>` (guest) | body 401/403/429 **KHÔNG chứa** `Traceback (most recent call last)` / SQL; gate THẬT = `is_traceback_allowed()` (`frappe/utils/response.py:60`, đọc System Setting `allow_error_traceback`, **default 1 = ON ⇒ prod mặc-định LEAK** → PHẢI tắt, §4) | QA/USER |
| **(b)** | **CORS no-wildcard** | **[AUTO]** GUARD-3 (docset đặc tả prod KHÔNG có literal khuyến-nghị wildcard `allow_cors='*'` ở dạng YAML config-form) · **[HARD-STOP USER]** `grep -c '*' <(python3 -c "import json;print(json.load(open('sites/<site>/site_config.json')).get('allow_cors'))")` | `== 0` (no-wildcard) HOẶC `allow_cors=None` (native OFF hợp lệ); `app.py:275` chỉ lọc list khi `!= '*'` ⇒ wildcard bỏ-lọc + credential-echo (T3) | USER |
| **(c)** | **no-token-leak** (`getAsset`/`getAssetScanInfo`) | **[HARD-STOP USER]** smoke 2 (10 §6.3): envelope 200 của `getAsset`/`getAssetScanInfo` KHÔNG chứa `qr_token` | response body KHÔNG có key `qr_token` thô (đã `_strip_qr_token` — `imm00.py:203/507`); FE chỉ nhận `qr_url` (ADR-001 §D4 rule 9) | QA/USER |
| **(d)** | **429 có `Retry-After`** | **[HARD-STOP USER]** vượt ngưỡng `@rate_limit` (`imm00.py`/device-token) → đọc response header | header `Retry-After` (+ `X-RateLimit-*`) present; **KNOWN:** header CHỈ phát khi `conf.rate_limit`/nginx `limit_req` set (rate_limiter instantiate) — decorator-429 trần = body-only no-header (`10 §6.2`, G-U5) | USER |
| **(e)** | **audit-actor NĐ98** (action-từ-mobile ghi audit actor = KTV thật) | **[AUTO]** GUARD-8 (`TestSecGateAuditActorNd98Doc`): source-grounded @source `lifecycle.py` (`log_audit_event` thân chứa `actor = actor or frappe.session.user` :44 + `verify_audit_chain` integrity-compare `expected != ...hash_sha256` + `prev_hash` mismatch :110-111) + `auth.py:667` (`set_user(OAuth Bearer Token.user)` = bearer→KTV thật) + doc-invariant `08 §2.2`/§5.1(e)/`10 §6.3 (verify-audit)` · **[HARD-STOP USER]** `verify_audit_chain(asset)` THẬT sau 1 action-từ-mobile bằng bearer token KTV (G-U?) | `actor = frappe.session.user` = KTV thật (KHÔNG service-account/Administrator — §2); `verify_audit_chain` → `valid=True`; chuỗi hash-chain bất biến + liên-tục (`lifecycle.py:9/18/110-113`) | QA/USER |
| **(f)** | **host_name/issuer go-live** (`host_name` set ⇒ `get_url()`/OIDC issuer == public host) | **[AUTO]** GUARD-9 (`TestSecGateHostNameIssuerDoc`): source-grounded @source `frappe/utils/data.py` (`def get_url` :1599; thân chứa `host_name = ...conf.host_name or ...conf.hostname` :1605 + fallback `protocol + ...site` nội bộ :1631) + doc-invariant raw-text `08 §5.1(f)` + `10 §3`/§6.2(3c0)/§6.3 (verify-host) chứa `host_name` + `get_url()`/`openid_configuration issuer == public host` + phủ-định `KHÔNG http://miyano` · **[HARD-STOP USER]** `get_url()` == public host + curl `openid_configuration issuer == public host` (G-U2/G-U6) | `get_url()` == public HTTPS host + `openid_configuration issuer == public host`, **KHÔNG `http://miyano`** nội bộ (gate `data.py:1605`; vắng ⇒ fallback `protocol+site` `:1631` = `http://miyano` ⇒ QR deep-link/issuer sai, flow-2 hỏng — `EPIC-G §8 R4`) | QA/USER |

> **CI-guard placeholder (cùng gate — GUARD-2):** khi build gắn cờ prod → spec yaml KHÔNG còn
> `REPLACE-WITH-PUBLIC-HOST` (yaml:108) + version KHÔNG `*-skeleton` (yaml:90). Hiện skeleton-Phase-A
> (cờ off) = control GREEN. Bảo vệ R6 (`EPIC-G §8`): placeholder lọt prod → client codegen trỏ host sai.
> Guard THẬT: `test_mobile_security_gate.py::TestSecGateCiPlaceholderGuard` (RED-before inject + prod-flag ON).

> **Status-line-vs-body invariant (GUARD-4, §3.2):** `_err(...)` (`utils/response.py:95`) body LUÔN có key
> `http_status` (CẢ nhánh int-code `:127` LẪN chuỗi ErrorCode `:131`) ⇒ in-handler-4xx ARRIVE trên HTTP-200,
> smoke/client route theo `body.http_status` KHÔNG status-line. Phân biệt 2 loại 403: **dispatcher-403**
> (guest/no-token, status-line 403 THẬT) vs **in-handler cap-403** (HTTP-200 + `{code:FORBIDDEN, http_status:403}`).

### 5.2 KPI · Acceptance bảo mật

| KPI / Acceptance | Đo | Mục tiêu | Nguồn |
|---|---|---|---|
| Endpoint OAuth2 có rate-limit tầng ngoài | nginx config review | 4/4 endpoint (T1) | Phase B review |
| `allow_cors` không wildcard ở prod | grep `site_config` | 0 lần `'*'` (T3) | Phase B audit |
| Public host = HTTPS | TLS scan | 100% (T7) | Phase B |
| Token storage secure | code review repo native | Keychain/Keystore (T4) | Phase D review |
| Audit-chain integrity action-từ-mobile | `verify_audit_chain(asset)` sau action mobile | `valid=True`, actor=KTV thật | §2 — *(verify khi có token thật Phase D)* |
| Quyền mobile == quyền web (no privilege drift) | so DocPerm web vs mobile cùng user | KHỚP 100% (1 SSoT) | `rbac.py` SSoT |
| Số hệ quyền song song | đếm | **0** (chỉ DocPerm/capability) | `ADR-MOBILE-001` b |

> **KHÔNG bịa baseline:** chỉ số "tỉ lệ token rò bị revoke trong X phút", "số attempt brute-force chặn" *(Cần khảo sát baseline khi có traffic thật — Phase F)*.

---

## Tham chiếu chéo

- Tổng quan + 3 quyết định + glossary: [`00-overview.md`](./00-overview.md) (§4 chỉ mục · §6 số đã cấp)
- ADR mô hình bảo mật mobile (chương này chốt): [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md)
- ADR kiến trúc nền (1 SSoT quyền · reuse-endpoint · no session-cookie): [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- Auth deep-dive (sequence OAuth · TTL · scope↔capability — KHÔNG lặp ở đây): [`03-auth-oauth2.md`](./03-auth-oauth2.md)
- Push security (device-token threat §5.3 — KHÔNG lặp ở đây): [`06-push-fcm.md`](./06-push-fcm.md)
- Offline/replay (idempotency-key T6 · conflict 409): [`07-offline-sync.md`](./07-offline-sync.md) · [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md)
- OpenAPI (securityScheme OAuth2 + ghi chú scope-coarse/RBAC-gate-cuối): [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)
- Exit gate (A11) — checklist security go-live (§4 này) gom vào Phase-B prereqs (B-5 rate-limit oauth2 tầng nginx): [`11-phase-a-exit.md`](./11-phase-a-exit.md) §2 B-5 · §3 checklist go/no-go.
- RBAC SSoT: `assetcore/services/shared/rbac.py` · Vendor isolation: `assetcore/permissions.py` · Audit-chain: `assetcore/utils/lifecycle.py`
- Frappe core (read-only, KHÔNG sửa): `frappe/integrations/oauth2.py` · `frappe/auth.py` · `frappe/oauth.py` · `frappe/app.py`
