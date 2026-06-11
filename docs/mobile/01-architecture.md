# 01 — AssetCore Mobile BE: Kiến trúc (Phase A)

| Mục | Giá trị |
|---|---|
| Module | Mobile BE (cross-cutting) |
| Phase | A — Kiến trúc & Feasibility |
| Actor chính | Kỹ thuật viên hiện trường (field-tech) qua APK native |
| Trạng thái | In Progress (vòng 1) |
| Cập nhật | 2026-06-09 |

> Tài liệu kiến trúc MỨC ĐỊNH HƯỚNG (KHÔNG impl). Mọi quyết định bám 3 chốt D-AUTH / D-MVP / D-STACK (`00-overview.md §2`). Evidence `file:line` đã verify tại Frappe v15.107.2 (`ADR-MOBILE-001.md`).
> Chỉ mục: [`00-overview`](./00-overview.md) · [`ADR-MOBILE-001`](./ADR-MOBILE-001.md) · [`02-deploy-feasibility`](./02-deploy-feasibility.md) · [`03-auth-oauth2`](./03-auth-oauth2.md) · [`04-api-contract`](./04-api-contract.md) · [`openapi/`](./openapi/assetcore-mobile.openapi.yaml)

---

## 1. Topology (sơ đồ triển khai)

```
┌──────────────────────────┐
│   APK NATIVE (repo riêng) │   D-STACK: Flutter / React Native
│  - UI field-tech          │   - HTTP client native (Dio/http/OkHttp) → KHÔNG chịu CORS browser
│  - QR scanner (camera)    │   - PKCE (code_verifier/S256), KHÔNG nhúng client_secret
│  - Offline cache + sync   │   - Lưu token an toàn (Keychain/Keystore)
│  - Push receiver (FCM)    │
└────────────┬─────────────┘
             │  HTTPS (bearer token / Authorization Code + PKCE)
             ▼
┌──────────────────────────────────────────────┐
│  PUBLIC HTTPS HOST  (reverse-proxy + TLS)      │   ❌ Phase B: chưa có (nginx dev HTTP:80, server_name rỗng)
│  nginx/Caddy → TLS termination + domain        │   - allow_cors set tường minh (browser/Swagger dev)
└────────────┬─────────────────────────────────┘
             │  proxy_pass (HTTP nội bộ)
             ▼
┌──────────────────────────────────────────────┐
│  FRAPPE BE  :8000  (site `miyano`, gunicorn)   │   - validate_oauth → set_user (auth.py:633/667)
│  ┌────────────────────────────────────────┐   │   - RBAC capability (rbac.py:156) = 1 SSoT
│  │ OAuth2 provider (frappe.integrations)   │   │   - Service layer 3-tier (IMM-00/08/09/11/12)
│  │ api/method/<dotted> RPC · api/v1 · v2   │   │   - notifications._dispatch (2 kênh → +#3 push)
│  └────────────────────────────────────────┘   │
└────────────┬─────────────────────────────────┘
             │
       ┌─────┴──────┐
       ▼            ▼
┌────────────┐ ┌────────────┐
│  MariaDB   │ │   Redis    │   (cache / queue / realtime — Frappe core)
└────────────┘ └────────────┘
```

Ghi chú topology:
- **Public HTTPS host** là blocker Phase B (hiện dev là HTTP:80, `server_name` rỗng, `host_name=None`). Cần cho: (a) OAuth redirect, (b) bearer-over-HTTPS, (c) QR deep-link (`assetcore_qr_base_url`).
- Native HTTP-client KHÔNG gửi preflight ⇒ kỹ thuật chạy được KHÔNG cần `allow_cors`; vẫn nên set `allow_cors` LIST origin tường minh cho dev tooling/WebView (KHÔNG `"*"` vì Frappe luôn echo `Allow-Credentials: true`, `app.py:282`).

---

## 2. Ba lằn ranh trách nhiệm (separation of concerns)

| Lằn ranh | Thuộc về | Nội dung | KHÔNG được |
|---|---|---|---|
| **① UI native** | Repo mobile riêng (D-STACK) | Màn hình, navigation, camera/QR decode, offline cache, push UI, lưu token an toàn | Nhúng business rule; tự dựng hệ quyền; tự decode/verify token quyền |
| **② API contract** | Repo `assetcore` — `openapi/assetcore-mobile.openapi.yaml` | HỢP ĐỒNG: endpoint, param, response envelope, error code, security scheme. Sinh API client từ đây. | Drift so với endpoint thật; thêm field không có ở BE |
| **③ Business logic (reuse)** | Repo `assetcore` — service layer 3-tier hiện có | Toàn bộ nghiệp vụ (validate, transition, lifecycle event, SLA, audit). Bearer→set_user→RBAC nguyên vẹn. | Bị fork/clone cho mobile; bị bypass quyền |

**Nguyên tắc:** lớp mobile chỉ **BỌC** (OAuth + CORS + OpenAPI + push) quanh ③. KHÔNG viết lại nghiệp vụ. Quyền = ③ (capability/DocPerm theo user), KHÔNG ở ① hay ② (xem ADR-MOBILE-001 quyết định (b)).

---

## 3. Luồng xác thực — Authorization Code + PKCE + refresh (mức kiến trúc)

```
APK                          BE (Frappe OAuth2 provider có sẵn)
 │  1. sinh code_verifier → code_challenge (S256)
 │ ───── GET /api/method/frappe.integrations.oauth2.authorize ─────▶
 │        (client_id, redirect_uri=assetcore://oauth/callback,
 │         response_type=code, scope, code_challenge, S256)
 │                                            │ Guest? → redirect /login (oauth2.py:79-82)
 │ ◀──── redirect: assetcore://oauth/callback?code=… ───────────────
 │
 │ ───── POST /api/method/frappe.integrations.oauth2.get_token ────▶
 │        (grant_type=authorization_code, code, code_verifier,
 │         client_id, redirect_uri)          │ verify code_verifier S256 (oauth.py:146-160)
 │ ◀──── { access_token, refresh_token, expires_in=3600, … } ──────  (oauth2.py:123-138)
 │
 │ ===== mọi request nghiệp vụ: Authorization: Bearer <access> =====▶
 │                                            │ validate_oauth → set_user (auth.py:633/667)
 │                                            │ rbac.can(cap) trên session.user (rbac.py:156)
 │ ◀──── { success, data } / 403 VI sạch ──────────────────────────
 │
 │  (access hết hạn 1h)
 │ ───── POST get_token (grant_type=refresh_token, refresh_token) ─▶  (oauth.py:187,244-296)
 │ ◀──── { access_token mới, … } ───────────────────────────────────
 │
 │  (đăng xuất / mất máy)
 │ ───── POST revoke_token ────────────────────────────────────────▶  (oauth2.py:144, RFC 7009)
```

Tính chất kiến trúc:
- **PKCE bắt buộc (D-STACK native):** không nhúng client_secret trong APK → S256 thay thế bí mật. Frappe lưu `code_challenge`/`method` (`oauth.py:89-91`), verify `code_verifier` (`oauth.py:146-160`).
- **Access ngắn hạn + refresh + revoke (D-AUTH):** access default **3600s** (oauthlib `BearerToken.expires_in`, Frappe không override). Đổi TTL cần wrap `get_oauth_server` (KHÔNG có site_config knob) — backlog, không MVP.
- **id_token alg = HS256** (OIDC discovery `oauth2.py` `id_token_signing_alg_values_supported:["HS256"]`).
- **Bearer → 1 SSoT quyền:** sau `set_user`, MỌI capability gate (asset.read/print, corrective.create, pm/repair/calibration.create…) áp dụng y nguyên. KHÔNG hệ quyền thứ 2.
- **Native KHÔNG dùng session-cookie web:** bearer auth không tạo cookie-session ⇒ CSRF check SKIP tự nhiên (`auth.py:83-98`) — native KHÔNG cần CSRF token (khác FE web cookie+CSRF).
- **Discovery doc:** `openid_configuration` (`oauth2.py:180`, allow_guest) trả issuer + 5 endpoint → app cấu hình tự động.

---

## 4. API versioning strategy

Frappe routing (verified `apps/frappe/frappe/api/__init__.py`):

| Đường | Mục đích | Mobile dùng? |
|---|---|---|
| `/api/method/<dotted.path>` | RPC tới whitelisted method (vd `assetcore.api.imm12.report_incident`) | ✅ ĐƯỜNG CHÍNH — đúng cái FE web đang gọi (BE↔FE naming contract) |
| `/api/resource/{DocType}[/{name}]` | CRUD doctype generic | ⚠️ chỉ nếu cần REST chuẩn cho generic doctype |
| `/api/v1` (= legacy `/api`) · `/api/v2` | Submount version (`get_api_version` chọn theo path) | ⬜ không cần ở MVP |

**Convention chốt cho mobile:**
- **Phase A/C document endpoint nghiệp vụ qua `/api/method/<dotted>`** (RPC, tái dùng nguyên endpoint — KHÔNG đổi đường gọi).
- Nếu Phase C cần lớp BỌC riêng cho mobile (vd gộp/đổi shape response cho field-tech), đặt namespace **`api/mobile/v1`** trong app (`assetcore/api/mobile/v1/…` → gọi qua `/api/method/assetcore.api.mobile.v1.<fn>`). Lớp này CHỈ bọc/adapt, gọi xuống service layer hiện có — KHÔNG nghiệp vụ mới (ADR-MOBILE-001 quyết định (c)).
- Version mobile contract qua `info.version` của OpenAPI + thư mục namespace, KHÔNG ép dùng `/api/v2` của Frappe.

---

## 5. OpenAPI = HỢP ĐỒNG

- Frappe KHÔNG tự sinh OpenAPI cho `/api/method` (whitelisted RPC). `/api/resource` có schema doctype nhưng không phải cái MVP cần.
- **Quyết định:** viết tay YAML là **hợp đồng** giữa BE và repo native. Nguồn = type-hints + docstring sẵn có trong `api/imm00.py`/`imm12.py`/… Đủ để repo native sinh API client (Flutter `openapi-generator` / RN) + tránh drift.
- **Phase A = skeleton** (`openapi/assetcore-mobile.openapi.yaml`): `openapi:3.0.3` + info/version + servers placeholder + securitySchemes OAuth2 (authorizationCode + PKCE + refresh) + paths STUB cho 6 luồng MVP (chưa schema chi tiết).
- **Phase C = bồi từng endpoint:** request/response schema thật. Envelope chuẩn (A3 đã đặc tả shape THẬT tại [`04-api-contract.md`](./04-api-contract.md)): success `{success, data}` · error FLAT `{success:false, error:<string VI>, code:<ErrorCode>, http_status:<int>, …optional}` (KHÔNG nested `error:{code,message}` — đó là mô tả cũ SAI, đã sửa ở A3). Param `str=""` (KHÔNG `str|None` — tránh pydantic 417, rule dự án).

---

## 6. Điểm chèn Push / Offline / Security (MỨC KIẾN TRÚC — KHÔNG impl)

### 6.1 Push (FCM) — channel #3 tại `_dispatch`
- Engine thông báo hiện có **2 kênh** trong `services/notifications.py::_dispatch` (`:366`): Kênh 1 in-app (Notification Log, `:384`), Kênh 2 email (`:397`).
- **Điểm chèn:** thêm **Kênh 3 — push (FCM)** NGAY trong `_dispatch` (sau kênh 1/2), cùng danh sách `users` đã dedupe + cùng `doc` reference. Mọi event hiện gọi `_dispatch` (7 call-site: `:452/:498/:562/:627/:791/:931/:1116`) sẽ tự có push — KHÔNG sửa từng call-site.
- **Cơ chế push CHỐT (A5):** FCM Admin SDK **trực tiếp** (credentials `site_config`), **KHÔNG** relay Frappe Cloud (`frappe/push_notification.py` chỉ proxy `notification_relay.api.*` ⇒ không air-gapped NĐ98). Đặc tả: [`06-push-fcm.md`](./06-push-fcm.md) · quyết định: [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md).
- **Cần (Phase E):** device-token registry (DocType **AC Mobile Device Token** map user→FCM token, dedup/RBAC/invalidate-on-401 — spec `06-push-fcm.md §2`), gửi qua FCM HTTP v1, fail-safe (lỗi push KHÔNG vỡ in-app/email — giữ pattern `_safe_sendmail`).

### 6.2 Offline / Sync
- App native cache hồ sơ thiết bị + "phiếu của tôi" để xem offline (D-STACK offline-first).
- Ghi offline (báo hỏng/yêu cầu WO khi mất mạng) → hàng đợi local, sync khi online. **Cần idempotency key** (tránh tạo trùng record khi retry) + conflict policy. Mức kiến trúc Phase A; impl Phase E.
- Audit trail (NĐ98 SHA-256 chain) chỉ sinh khi record THẬT ghi ở BE — offline queue KHÔNG sinh audit cho tới khi sync thành công.

### 6.3 Security (mức kiến trúc)
- **Transport:** bắt buộc HTTPS (Phase B public host + TLS). Bearer KHÔNG được gửi qua HTTP.
- **Token storage:** Keychain (iOS) / Keystore (Android); KHÔNG lưu plaintext/SharedPrefs.
- **Quyền = 1 SSoT:** capability/DocPerm theo user (set_user). Scope OAuth chỉ coarse on/off — KHÔNG là quyền thực (ADR-MOBILE-001 (b)).
- **CORS:** set `allow_cors` LIST origin tường minh (KHÔNG `"*"` + credentials ở prod).
- **Rate-limit:** endpoint nhạy cảm đã có `@rate_limit` (vd rotate QR); login/token nên thêm ở Phase F. (KHÔNG claim "rate-limit toàn API".)
- **Revoke:** logout/mất máy → `revoke_token`. Access TTL 3600s giới hạn cửa sổ rủi ro.
- **Audit NĐ98:** mọi action mobile sinh lifecycle event với đúng actor (bearer→set_user) — traceability giữ nguyên. Không có đường bypass audit cho mobile.

---

## 7. Audit / Compliance note (NĐ98)

- Bearer auth `set_user(<token.user>)` ⇒ actor trong audit trail = đúng người (KHÔNG phải service account). SHA-256 lifecycle chain (`utils/lifecycle.py`) áp dụng nguyên vẹn cho action mobile.
- Báo hỏng (IMM-12) qua mobile vẫn emit `incident_reported` + provenance + change_summary như web — đáp ứng yêu cầu incident reporting (NĐ98 Art. 67) bất kể kênh.
- KHÔNG có "fast-path" mobile bỏ qua workflow/SLA/gate — mobile gọi cùng service ⇒ cùng ràng buộc.

---

## Tham chiếu chéo

- Quyết định nền + glossary: [`00-overview.md`](./00-overview.md)
- ADR + evidence `file:line`: [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- Feasibility (OAuth Client=0, allow_cors=None, gaps): [`02-deploy-feasibility.md`](./02-deploy-feasibility.md)
- OpenAPI skeleton: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)
