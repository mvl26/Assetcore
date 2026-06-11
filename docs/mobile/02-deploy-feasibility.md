# 02 — Mobile BE: Deploy / OAuth2 / CORS Feasibility (read-only survey)

> Scope: VÙNG DEPLOY/FEASIBILITY cho initiative AssetCore → mobile backend (native Flutter/RN).
> **Bản chất = KHẢO SÁT / SURVEY** ("có khả thi không, thiếu gì, blocker nào") — read-only. **Quy trình THỰC THI go-live** (numbered steps + checklist + rollback) ở **[`10-deploy-ops.md`](./10-deploy-ops.md)** (runbook). 02=feasibility → 10=execute (xem phân biệt: `10 §0`).
> Khảo sát read-only tại source (Frappe v15.107.2 + site `miyano`). KHÔNG sửa code/data.
> Ngày: 2026-06-09. Quyết định D-AUTH/D-MVP/D-STACK đã CHỐT (USER 2026-06-09) — không re-litigate.
> **Đổi tên (BA, 2026-06-09):** trước là `01_Deploy_OAuth_CORS_Feasibility.md` → renumber thành `02-deploy-feasibility.md` để tránh trùng số `01` với `01-architecture.md` (convention đặt tên: xem `00-overview.md §6`). Nội dung GIỮ NGUYÊN, chỉ đổi số.
> **Chỉ mục docset:** [`00-overview.md`](./00-overview.md) · [`01-architecture.md`](./01-architecture.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`10-deploy-ops.md`](./10-deploy-ops.md) (runbook go-live) · [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)
> **Auth deep-dive:** chi tiết sequence Auth Code+PKCE, vòng đời token, scope↔capability, checklist OAuth Client → [`03-auth-oauth2.md`](./03-auth-oauth2.md) (mở rộng §1).

---

## 0. TL;DR feasibility

| Hạng mục | Trạng thái | Việc cần làm |
|----------|-----------|--------------|
| Frappe OAuth2 provider (Auth Code + PKCE + refresh) | ✅ CÓ SẴN, hoạt động | CẤU HÌNH (tạo OAuth Client) — KHÔNG viết code OAuth |
| Bearer token → RBAC capability | ✅ Transparent (set_user) | MAP scope↔capability (coarse→fine) |
| CORS | ⚠️ TẮT (chưa cấu hình) | Set `allow_cors` trong site_config |
| Public HTTPS host | ❌ CHƯA (nginx default HTTP:80, server_name rỗng) | Reverse-proxy + TLS + domain |
| OpenAPI spec | ❌ CHƯA có (no generator, no yaml) | Viết tay YAML hoặc script sinh từ whitelist |
| FCM push | ❌ CHƯA · ⚠️ relay Frappe Cloud KHÔNG air-gapped | Device-token registry + kênh push #3 — cơ chế CHỐT = **FCM Admin SDK trực tiếp** (credentials `site_config`), KHÔNG dùng relay Frappe Cloud (`push_notification.py` chỉ proxy `notification_relay.api.*`). Đặc tả: [`06-push-fcm.md`](./06-push-fcm.md) · [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md) |
| API versioning | ✅ `/api/method`, `/api/resource`, `/api/v1`, `/api/v2` đều có | Chọn convention; AssetCore endpoint hiện qua `/api/method/<dotted>` |

Kết luận: **D-AUTH khả thi bằng CẤU HÌNH**, không cần tự viết OAuth. Hai blocker triển khai thực: (1) CORS chưa bật, (2) chưa có public HTTPS host. Cả hai là việc deploy/site_config + reverse-proxy, KHÔNG phải code.

---

## 1. Frappe OAuth2 provider — có sẵn, đủ cho D-AUTH

`apps/frappe/frappe/integrations/oauth2.py` — module whitelisted, allow_guest cho các endpoint flow:

| Endpoint (path `/api/method/frappe.integrations.oauth2.<fn>`) | Dòng | allow_guest | Vai trò |
|---|---|---|---|
| `authorize` | oauth2.py:74 | ✅ | Authorization Code — redirect login nếu Guest (oauth2.py:79-82) |
| `get_token` | oauth2.py:123 | ✅ | Đổi code→token; trả `access_token`+`refresh_token` (oauth2.py:130-138) |
| `revoke_token` | oauth2.py:144 | ✅ | Thu hồi token (RFC 7009) |
| `openid_profile` | oauth2.py:163 | ❌ (cần token) | UserInfo (OIDC) |
| `openid_configuration` | oauth2.py:180 | ✅ | Discovery doc (issuer/endpoints) — oauth2.py:182-202 |
| `introspect_token` | oauth2.py:205 | ✅ | RFC 7662 introspection (active/exp/scope) |

OAuth server = oauthlib `WebApplicationServer` (OIDC pre_configured), `oauth2.py:5,22`. oauthlib **3.3.1** (verified runtime).

### 1.1 PKCE — ✅ hỗ trợ (bắt buộc cho native app, D-STACK)
`apps/frappe/frappe/oauth.py:89-91` lưu `code_challenge`+`code_challenge_method`; `oauth.py:146-160` verify `code_verifier` với S256 (sha256→base64). ⇒ Authorization Code + PKCE (S256) chạy được cho app native (không cần client_secret nhúng app).

### 1.2 Refresh token — ✅
- `grant_type` hỗ trợ: `authorization_code`, `refresh_token`, `password` (`oauth.py:187`).
- Refresh flow: `oauth.py:244-296` (`get_original_scopes`, `validate_refresh_token`).
- Token lưu ở doctype **OAuth Bearer Token** (autoname = field `access_token` ⇒ token CHÍNH là PK), fields: `client, user, scopes, access_token, refresh_token, expiration_time, expires_in, status`.

### 1.3 Token lifetime
- `expires_in` set từ oauthlib token generator: `oauth.py:214` (`otoken.expires_in = token["expires_in"]`).
- `OAuth Bearer Token` controller tính `expiration_time = creation + expires_in` (oauth_bearer_token.py:28-31).
- **Default access-token lifetime = 3600s (1h)** — oauthlib `BearerToken.__init__(expires_in=None)` áp fallback `self.expires_in = expires_in or 3600` (verified oauthlib 3.3.1, `tokens.py`). Frappe KHÔNG override (`get_oauth_server` chỉ gọi `WebApplicationServer(oauth_validator)`, KHÔNG truyền `token_expires_in` — `oauth2.py:22`) ⇒ hiệu lực 3600s.
- Validate token mỗi request: `oauth.py:229-241` `validate_bearer_token` check `now < expiration_time AND status != "Revoked"` + scope membership.
- ⇒ "access ngắn hạn + refresh + revoke được" (D-AUTH) ĐÚNG với mặc định. Muốn đổi 1h → giá trị khác cần fork/wrap server init (KHÔNG có site_config knob).

### 1.4 Cấu hình bật OAuth2 (CHƯA có gì — DB trống)
Verified qua `bench --site miyano console`:
- `OAuth Client` = **[]** (rỗng)
- `Social Login Key` = **[]** (rỗng)
- Doctype config provider: **OAuth Provider Settings** (single) — chỉ 1 field `skip_authorization` (Select: Force/Auto). Không có knob token-expiry.

**Để bật:** tạo 1 record **OAuth Client**:
- `app_name` (tên app native), `client_id`/`client_secret` (auto), `scopes` (default `"all openid"`),
- `redirect_uris` + `default_redirect_uri` (custom-scheme cho native, vd `assetcore://oauth/callback`),
- `grant_type = Authorization Code`, `response_type = Code`,
- `skip_authorization` = 1 nếu muốn bỏ màn Allow/Deny (first-party app),
- `allowed_roles` (Table MultiSelect OAuth Client Role) — giới hạn role được cấp token.

⚠️ **Không cần Social Login Key** cho việc app native LẤY token từ Frappe (đó là provider role). Social Login Key chỉ cần khi Frappe ĐI login NGƯỜI DÙNG qua provider ngoài, hoặc để set `base_url` cho `get_server_url` (oauth.py:578-581: fallback = `frappe.request.url` netloc nếu Social Login Key "frappe".base_url rỗng → discovery doc trả host theo request, OK nếu sau reverse-proxy).

---

## 2. Bearer token → AssetCore RBAC: transparent (điểm mạnh kiến trúc)

Chuỗi auth mỗi request: `apps/frappe/frappe/auth.py:615-630` `validate_auth()`:
1. Đọc header `Authorization: <type> <token>` (auth.py:619).
2. `validate_oauth(header)` (auth.py:633-670): nếu prefix `bearer` → verify_request → **`frappe.set_user(<token.user>)`** (auth.py:667).
3. Fallback `validate_auth_via_api_keys` cho `Basic`/`Token` (api_key:api_secret) — D-AUTH coi là FALLBACK, không chính.
4. Nếu có header nhưng user vẫn Guest → `AuthenticationError` (auth.py:629-630).

**Hệ quả then chốt:** AssetCore RBAC = `services/shared/rbac.py:156-168` `can(cap)` → `frappe.has_permission(DocType, ptype)` **trên `frappe.session.user`**. Bearer auth đã `set_user` ⇒ TOÀN BỘ capability gate (asset.read/print, corrective.create, pm.create…) áp dụng NGUYÊN VẸN cho request mobile. **KHÔNG cần hệ quyền thứ 2.**

⇒ MVP field-tech TÁI DÙNG y nguyên endpoint nghiệp vụ (imm00 QR, imm12 báo hỏng, imm08/09/11 WO) — lớp mobile chỉ là OAuth+CORS+OpenAPI+push bọc quanh.

### 2.1 OAuth scope ≠ AssetCore capability (GAP cần map)
- OAuth scope là gate THÔ ở tầng oauthlib: `oauth.py:51-54` `validate_scopes` = client request scopes ⊆ client allowed scopes; default OAuth Client `scopes = "all openid"`.
- Scope KHÔNG biết tới `CAPABILITY_MAP`. Token user vẫn bị chặn ở từng endpoint qua `rbac.require`/`can` (DocPerm theo Role Profile).
- D-AUTH "scope map tới capability": HIỆN scope chỉ là coarse on/off. Quyền THỰC = capability/DocPerm theo user. Khuyến nghị §5.

### 2.2 CSRF — bearer auth bỏ qua sạch (tốt cho native)
`auth.py:83-98` `validate_csrf_token` chỉ fail khi CÓ `frappe.session.data.csrf_token`. Bearer auth không tạo cookie-session ⇒ không có csrf_token ⇒ CSRF check SKIP tự nhiên. Native app KHÔNG cần CSRF token (khác hẳn FE web cookie+CSRF hiện tại).

---

## 3. CORS — chưa bật, bật bằng 1 dòng site_config

Frappe xử lý CORS ở `apps/frappe/frappe/app.py:262-299` `set_cors_headers`:
- Bật KHI `frappe.conf.allow_cors` set (app.py:269). **Verified: `allow_cors = None`** trên site `miyano` ⇒ CORS TẮT.
- `allow_cors = "*"` → cho mọi origin; hoặc list/string origin cụ thể (app.py:275-280, chỉ echo Origin nếu khớp).
- Luôn set `Access-Control-Allow-Credentials: true` + echo `Origin` + `Vary: Origin` (app.py:282-286).
- Preflight OPTIONS: echo `Access-Control-Request-Method`/`-Headers`, cache 86400s nếu KHÔNG developer_mode (app.py:288-297).
- OPTIONS request được short-circuit trả `Response()` rỗng SAU validate_auth (app.py:109-110) → header CORS gắn ở after_request ⇒ preflight hoạt động khi `allow_cors` đã set.

**Lưu ý native:** app từ APK gọi cross-origin KHÔNG bị CORS chặn ở tầng HTTP-client native (CORS là cơ chế BROWSER). Nhưng:
- Nếu mobile dùng WebView/PWA-wrapper → CẦN CORS.
- Native HTTP (Dio/http/OkHttp) KHÔNG gửi preflight, KHÔNG enforce CORS → về kỹ thuật chạy được KHÔNG cần `allow_cors`. **Tuy nhiên** vẫn nên set `allow_cors` = danh sách origin (vd OAuth redirect host) cho an toàn + cho phép test bằng browser/Swagger UI cross-origin trong dev. KHÔNG nên để `"*"` cùng `Allow-Credentials: true` (Frappe vẫn echo true) ở prod — dùng list origin tường minh.

---

## 4. Public host / reverse-proxy / API routing

### 4.1 Host hiện tại (dev) — KHÔNG dùng được cho mobile prod
- `config/nginx.conf` = bench-generated mặc định: `listen 80` (HTTP), `server_name` RỖNG. KHÔNG TLS, KHÔNG domain. (Đây là file bench tạo, không phải prod config đang phục vụ.)
- Backend dev `:8000` (gunicorn --preload), FE web dev `:3000`. Site = `miyano` (host-name nội bộ).
- `frappe.conf.host_name` = None.

### 4.2 QR deep-link host (đã có cơ chế config public host)
- `services/imm00.py:685-699` `_build_qr_url`: ưu tiên site_config key **`assetcore_qr_base_url`** (host công khai, validate scheme http/https, no path/query — imm00.py:639-682) → fallback `frappe.utils.get_url('/a/<token>')`.
- **Verified: `assetcore_qr_base_url = None`** ⇒ hiện fallback `get_url` (host nội bộ `http://miyano`) → camera điện thoại KHÔNG mở được. Đây là blocker đã biết cho QR; go-live phải set key này = host HTTPS công khai.
- QR web route `/a/<token>` KHÔNG có server route (`hooks.py:400` website_route_rules chỉ có `/assetcore/<path>`). `/a/<token>` resolve qua FE SPA. ⇒ **App native KHÔNG dùng URL `/a/<token>`** — phải gọi thẳng `resolve_qr_token`/`get_asset_scan_info` (xem §6) sau khi tự decode QR. QR payload đang là URL `<base>/a/<token>` ⇒ native cần PARSE token ra khỏi URL rồi gọi API.

### 4.3 API routing (versioning)
`apps/frappe/frappe/api/__init__.py`:
- `/api/method/{dotted.path}` → whitelisted method (AssetCore endpoint dùng đường này, vd `/api/method/assetcore.api.imm12.report_incident`).
- `/api/resource/{DocType}[/{name}]` → CRUD doctype generic.
- Versioned: `Submount("/api", v1)`, `/api/v1` (= legacy `/api`), `/api/v2` (api/__init__.py:80-89). `get_api_version` (:92-98): path bắt đầu `/api/v2` → V2, còn lại V1.
- **Khuyến nghị cho OpenAPI:** document `/api/method/<dotted>` (RPC) cho endpoint nghiệp vụ AssetCore (đó là cái FE đang gọi, BE-FE naming contract). KHÔNG cần `/api/v2` trừ khi muốn REST chuẩn cho generic doctype.

---

## 5. OpenAPI feasibility

- ❌ CHƯA có generator/yaml nào (grep `openapi|swagger` trong app → rỗng; không file `*openapi*`).
- Frappe KHÔNG tự sinh OpenAPI cho whitelisted method (`/api/method`). `/api/resource` có schema doctype nhưng không phải cái MVP cần.
- **2 lựa chọn:**
  1. **Viết tay YAML** (khuyến nghị MVP): chỉ ~12-15 endpoint field-tech (OAuth 5 + QR 3 + báo hỏng 1 + WO create 3 + "phiếu của tôi" list/detail). Type hints + docstring đã có sẵn trong `api/imm00.py`/`imm12.py`/… làm nguồn. Đủ để user sinh API client (Flutter `openapi-generator`/RN).
  2. **Script sinh từ introspection** (về sau): duyệt `@frappe.whitelist` + `inspect.signature` → khung OpenAPI. Tốn công + dễ lệch (Frappe form_dict coercion). Để roadmap.
- Lưu ý schema: whitelist signature dùng `str = ""` (KHÔNG `str | None`) để tránh pydantic 417 (đã là rule dự án) — OpenAPI phải phản ánh tham số string/optional cho đúng.

---

## 6. Mapping flow field-tech MVP → endpoint BE đã có (tái dùng)

| MVP feature (D-MVP) | Endpoint BE (đã có, session-gated, capability RBAC) | Method | Cap |
|---|---|---|---|
| (1) Đăng nhập OAuth2 | `frappe.integrations.oauth2.authorize` → `get_token` | redirect+POST | — |
| (2) Quét QR → hồ sơ | `assetcore.api.imm00.resolve_qr_token` / `get_asset_scan_info` (imm00.py:312/355) | GET | asset.read |
| (2b) Chi tiết thiết bị | `assetcore.api.imm00.get_asset` (imm00.py:271) | GET | asset.read |
| (3) Báo hỏng | `assetcore.api.imm12.report_incident` (imm12.py:71) | POST | corrective.create |
| (4) Yêu cầu PM/CM/Cal | imm08 PM / imm09 CM / imm11 calibration create | POST | pm/repair/calibration.create |
| (5) "Phiếu của tôi" | list endpoint WO/Incident (đã permission-aware, scope `reported_by`/`assigned_to`) | GET | *.read |
| (6) Push (FCM) | ❌ CHƯA — thêm device-token registry + kênh 3 (notifications.py mới có in-app+email) | — | — |

⚠️ Tất cả endpoint nghiệp vụ KHÔNG `allow_guest` ⇒ PHẢI có bearer token hợp lệ trước. `report_incident` + các create là POST-only ⇒ nếu gọi từ browser/WebView sẽ có CORS preflight (cần `allow_cors`). Native HTTP-client KHÔNG preflight.

> **Bồi chi tiết (A4):** bảng MÀN↔API grounded `file:line` đầy đủ + hành trình end-to-end ≥5 bước + phân loại OFFLINE per-màn + map QUYỀN/cap per-màn → [`05-personas-mvp.md`](./05-personas-mvp.md) (§3 bảng · §2 hành trình · §4 offline · §5 quyền). Mapping thô ở đây (§6) là NGUỒN; `05` bồi chi tiết, KHÔNG mâu thuẫn.

---

## 7. Gaps (tổng hợp) & blocker triển khai

1. **CORS TẮT** (`allow_cors=None`) — set site_config (deploy). KHÔNG phải code.
2. **Không public HTTPS host** — nginx dev HTTP:80 server_name rỗng; cần reverse-proxy + TLS + domain cho: (a) OAuth redirect, (b) bearer-over-HTTPS, (c) QR deep-link.
3. **`assetcore_qr_base_url=None`** — QR trỏ host nội bộ; set = host công khai khi go-live (cơ chế đã sẵn).
4. **OAuth Client chưa tồn tại** — phải tạo record (Auth Code + PKCE + redirect_uris native scheme + allowed_roles).
5. **Scope ≠ capability** — OAuth scope coarse (`all openid`); quyền thực = DocPerm/capability theo user. Cần quyết định: giữ scope thô (quyền vẫn đúng nhờ RBAC) HAY map scope→capability-group.
6. **OpenAPI chưa có** — viết tay YAML cho ~12-15 endpoint MVP.
7. **FCM/push chưa có** — device-token registry + kênh thứ 3 (ngoài scope feasibility này; khảo sát riêng).
8. **Token lifetime cố định 3600s** — không có site_config knob; đổi cần wrap `get_oauth_server`.

---

## 8. Recommendations (deploy/feasibility)

> **Forward-link (survey → runbook):** các recommendation dưới đây được biến thành **quy trình thực thi go-live CÓ THỨ TỰ** (numbered steps §1–§5 + checklist tick-box + smoke curl + rollback) tại **[`10-deploy-ops.md`](./10-deploy-ops.md)**. Tài liệu này (02) = *khảo sát feasibility*; tài liệu 10 = *execute go-live* (HARD-STOP USER). Ranh giới: 02 trả lời "khả thi/thiếu gì", 10 trả lời "admin chạy bước nào theo thứ tự nào" (`10 §0`).

1. **Bật OAuth2 = cấu hình, không code:** tạo OAuth Client (Authorization Code, response_type Code, PKCE-ready, redirect_uris = custom-scheme native, allowed_roles giới hạn KTV). Provider endpoint dùng nguyên `frappe.integrations.oauth2.*`.
2. **Set `allow_cors`** = LIST origin tường minh (OAuth redirect host + dev tooling) trong site_config — KHÔNG `"*"` ở prod (vì Frappe luôn echo `Allow-Credentials: true`).
3. **Provision public HTTPS host** (reverse-proxy nginx + TLS + domain) trước khi mobile gọi thật; cập nhật `assetcore_qr_base_url` = host công khai (QR deep-link). HARD-STOP thuộc user — chỉ tài liệu hoá runbook.
4. **Giữ 1 nguồn quyền (SSoT):** dùng OAuth scope ở mức thô + dựa RBAC capability/DocPerm theo user cho quyền chi tiết (transparent qua set_user). KHÔNG dựng hệ quyền thứ 2 cho mobile.
5. **OpenAPI:** viết tay YAML cho ~12-15 endpoint field-tech (nguồn = type hints/docstring có sẵn). Phản ánh `/api/method/<dotted>`, tham số `str=""` (no `str|None`).
6. **Native KHÔNG dùng `/a/<token>`** (không server route, là SPA-only): app tự decode QR → parse token → gọi `resolve_qr_token`/`get_asset_scan_info`. Document rõ trong API client guide.
7. **Backlog (không MVP):** FCM device-token registry + push channel; token-lifetime knob; OpenAPI auto-gen từ introspection; `/api/v2` REST nếu cần.
8. **Verify trước go-live (cần USER reload/migrate — HARD-STOP):** sau khi tạo OAuth Client + set allow_cors, test get_token + 1 bearer call tới `get_asset_scan_info` qua HTTP thật (gunicorn --preload ⇒ thay đổi conf/cap cần reload + bust `ac_caps::*`).

> **Bảo mật (A7):** khuyến nghị CORS list-origin (#2), HTTPS host (#3), 1-SSoT-quyền (#4) ở trên được hợp nhất thành **threat model + checklist security go-live** tại [`08-security-compliance.md`](./08-security-compliance.md) (T1 brute-force oauth2 no-rate-limit · T3 CORS credential-echo · T7 MITM) + mô hình chốt ở [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md).
> **Exit gate (A11):** các gap/blocker §7 trên (CORS=None · public host · OAuth Client=0 · `assetcore_qr_base_url=None`) được GOM thành danh sách Phase-B prereqs hợp nhất (B-1..B-8, chủ thể=USER) tại [`11-phase-a-exit.md §2`](./11-phase-a-exit.md) + checklist go/no-go A→B [`§3`](./11-phase-a-exit.md).
