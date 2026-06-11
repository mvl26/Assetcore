# 10 — Mobile BE: Deploy / Ops Go-live RUNBOOK (quy trình thực thi có thứ tự)

| Mục | Giá trị |
|---|---|
| Initiative | AssetCore Mobile — backend-for-mobile |
| Phase | **B — Provisioning & Auth wiring** (runbook go-live) · liên quan F (hardening) |
| Bám quyết định | **D-AUTH** (OAuth2+refresh) · **D-MVP** (field-tech) · **D-STACK** (native) — `00-overview.md §2` · ADR-MOBILE-001/002/004 |
| Owner | BA Lead đặc tả quy trình · **USER/Admin THỰC THI** (mọi bước = HARD-STOP) |
| Trạng thái | In Progress (Phase A đặc tả · thực thi Phase B) |
| Cập nhật | 2026-06-09 |

> **Mục đích:** gom các fragment deploy/ops rải rác (OAuth2 · CORS · public host · QR deep-link · FCM creds · versioning) thành **MỘT quy trình admin CÓ THỨ TỰ** (numbered steps) + checklist tick-box đo được, để go-live mobile-BE.
> **Đây là ĐẶC TẢ quy trình, KHÔNG thực thi.** Mọi lệnh deploy (`bench restart`/`migrate`/`supervisorctl`/reload gunicorn/ghi `site_config`/sửa nginx) là **HARD-STOP — thuộc quyền USER**. BA/agent KHÔNG chạy. Mọi config knob trích **evidence `file:line`** verify tại **Frappe v15.107.2** (read-only).
> **Chỉ mục docset:** [`00-overview.md`](./00-overview.md) · [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`06-push-fcm.md`](./06-push-fcm.md) · [`08-security-compliance.md`](./08-security-compliance.md) · [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)

---

## 0. Scope — RUNBOOK (10) khác KHẢO SÁT FEASIBILITY (02)

> **Phân biệt rõ — 2 tài liệu, 2 bản chất KHÁC nhau (KHÔNG nhân đôi nội dung):**

| | [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) | **`10-deploy-ops.md` (file này)** |
|---|---|---|
| **Bản chất** | KHẢO SÁT / SURVEY — "có khả thi không, thiếu gì" | **QUY TRÌNH THỰC THI / EXECUTE** — "làm theo thứ tự nào để go-live" |
| **Câu hỏi trả lời** | *Có gì sẵn? Gap ở đâu? Blocker nào?* (read-only tại source) | *Admin chạy bước nào, theo thứ tự nào, verify ra sao?* |
| **Đầu ra** | Bảng TL;DR feasibility + gaps (§7) + recommendations (§8) | Numbered steps (§1–§5) + checklist tick-box (§6) + rollback (§7) |
| **Trạng thái** | Hoàn tất (đã khảo sát xong) | Thực thi ở Phase B (HARD-STOP USER) |
| **Dùng khi** | Quyết định "đi tiếp hay không" | Tay đặt lên bàn phím để go-live |

- **02 = khảo sát feasibility** (đã trả lời: *D-AUTH khả thi bằng CẤU HÌNH, không cần code; 2 blocker = CORS chưa bật + chưa có public HTTPS host*). **10 = quy trình thực thi go-live** (biến các recommendation `02 §8` thành numbered steps + checklist).
- **Link 2 chiều:** `02 §0/§8` → `10` (survey → runbook); `10 §0/§8` → `02` (runbook bám gap đã khảo sát). KHÔNG copy nội dung khảo sát sang đây — chỉ THAM CHIẾU.
- **5 hạng mục deploy/ops** runbook này phủ (theo plan Phase A): (1) bật OAuth2 · (2) CORS `site_config` · (3) public host + QR deep-link host · (4) FCM creds · (5) versioning/deprecation (`Sunset`/`Deprecation`).

### 0.1 Actor + ranh giới HARD-STOP

| Actor | Vai trò | Được làm | HARD-STOP (KHÔNG được làm) |
|---|---|---|---|
| **BA Lead** (file này) | Đặc tả quy trình + checklist | Viết runbook, đánh dấu evidence | Chạy bất kỳ lệnh deploy nào |
| **USER / Admin** | THỰC THI go-live | Tạo OAuth Client · ghi `site_config` · sửa nginx · reload/restart/migrate | (chính là người được phép — chịu trách nhiệm) |
| **Agent (Claude)** | Hỗ trợ đặc tả | Sửa file doc · chạy test read-only | `bench restart`/`migrate`/`supervisorctl`/reload gunicorn/ghi `site_config`/sửa nginx — TẤT CẢ là HARD-STOP |

> **Vì sao mỗi bước là HARD-STOP:** các bước ghi `site_config`, sửa nginx, reload gunicorn/supervisor, `bench migrate` đều thay đổi **trạng thái runtime production** — sai = downtime / lộ quyền / rò creds. Quyết định + thực thi thuộc USER (CLAUDE.md §5, §19; memory `mobile_backend_initiative` HARD-STOP).
> **Lưu ý gunicorn `--preload`:** BE boot import đông cứng lúc khởi động ⇒ thay đổi `site_config` (allow_cors / creds) hoặc cap-set **chỉ LIVE ở HTTP sau khi USER reload gunicorn** (+ bust cache cap nếu đổi capability). Đây là lý do bước verify (§6) phải chạy SAU reload.

---

## 1. §1 — Bật OAuth2 (tạo OAuth Client native, least-privilege)

> **Mục tiêu:** có 1 record `OAuth Client` để app native lấy token (Authorization Code + PKCE + refresh). **Provider Frappe đã có sẵn — KHÔNG viết code OAuth** (chỉ tạo record). Field checklist chi tiết KHÔNG nhân đôi ở đây → **dùng [`03-auth-oauth2.md §4`](./03-auth-oauth2.md)** (bảng field thật doctype `OAuth Client`).
> **Verified:** `OAuth Client` count = **0**, `Social Login Key` count = **0** (site `miyano`) ⇒ Phase B PHẢI tạo client; KHÔNG cần Social Login Key cho vai trò provider (`02-deploy-feasibility.md §1.4`).

**Provider endpoint (đã có sẵn, allow_guest — KHÔNG tạo, chỉ dùng):**

| Endpoint `/api/method/frappe.integrations.oauth2.<fn>` | allow_guest | Evidence |
|---|---|---|
| `authorize` | ✅ | `oauth2.py:74` |
| `get_token` | ✅ | `oauth2.py:123` |
| `revoke_token` | ✅ | `oauth2.py:144` |
| `openid_configuration` (discovery, tuỳ chọn) | ✅ | `oauth2.py:180` |
| `introspect_token` (server-to-server, tuỳ chọn) | ✅ | `oauth2.py:205` |

### Numbered steps (USER chạy — HARD-STOP)

1. **[USER]** Mở Desk → New `OAuth Client`. Điền field theo **checklist [`03-auth-oauth2.md §4`](./03-auth-oauth2.md)** (KHÔNG nhân đôi field ở đây). Tối thiểu:
   - `grant_type = Authorization Code`, `response_type = Code` (Implicit deprecated — KHÔNG dùng).
   - `redirect_uris` + `default_redirect_uri` = custom-scheme native `assetcore://oauth/callback` (phải KHỚP redirect app gửi — sai → reject).
   - `scopes = all openid` (coarse — quyền thực = RBAC capability theo user, `03 §3`).
   - `allowed_roles` (Table MultiSelect `OAuth Client Role`) = **CHỈ role field-tech (KTV)** — least-privilege, giảm bề mặt (T5, `08 §3b`).
   - `skip_authorization = 0` (hiện màn Allow/Deny lần đầu; `1` chỉ nếu first-party trusted muốn bỏ consent).
   - `client_secret` auto-gen — **KHÔNG nhúng APK** (native = public client; PKCE thay thế).
2. **[USER]** Lưu record → ghi lại `client_id` (public — app dùng ở bước authorize/get_token). KHÔNG cấp token cho tài khoản dùng-chung (giữ audit đúng actor — `08 §2`).
3. **[USER]** Nếu vừa đổi capability/Role Profile cho role field-tech → `bench migrate` HOẶC bust cache cap (`ac_caps::*`) + **reload gunicorn** để cap-set live ở HTTP (gunicorn `--preload`). **HARD-STOP.**

> **Vì sao HARD-STOP:** DB write (tạo record) + reload gunicorn. Verify token thật → §6 post-verify (smoke `get_token`).
> **Pre-flight tự động (B0-PREFLIGHT) sau khi tạo record:** chạy `bench --site miyano execute assetcore.api.mobile.preflight.verify_oauth_client` (READ-ONLY) → báo cáo có cấu trúc xác nhận 7 điều kiện B-1 (count + grant/response/redirect/scopes/skip_auth/allowed_roles) đã đúng chưa, sai ở đâu (blocker tiếng Việt). Chi tiết: [`12-phase-b-preflight.md`](./12-phase-b-preflight.md).

---

## 2. §2 — CORS: `site_config.allow_cors` = LIST origin (CẤM wildcard prod)

> **Mục tiêu:** bật CORS đúng cách cho dev-tooling / WebView OAuth, **KHÔNG mở wildcard ở prod**. Native HTTP-client KHÔNG dính CORS (cơ chế browser) — nhưng vẫn set list-origin tường minh cho an toàn + test browser/Swagger (`02 §3`). **Bám [`ADR-MOBILE-004 (c)`](./ADR-MOBILE-004.md).**

**Cơ chế Frappe (verified `file:line`):**

| Hành vi | Evidence | Hệ quả |
|---|---|---|
| CORS bật KHI `frappe.conf.allow_cors` được set | `app.py:269` (`allowed_origins := frappe.conf.allow_cors`) | `allow_cors=None` (hiện tại) ⇒ CORS TẮT |
| Nhánh lọc list-origin CHỈ chạy khi value `!= "*"` | `app.py:275` (`if allowed_origins != "*":`) | đặt `'*'` ⇒ BỎ lọc ⇒ mọi origin được chấp |
| Luôn echo `Access-Control-Allow-Credentials: true` + `Origin` | `app.py:283-284` | `'*'` + credentials echo = lỗ credential-echo (T3) |

⇒ **CẤM `allow_cors='*'` ở prod** (Frappe luôn echo `Allow-Credentials: true` — `app.py:283-284`; wildcard bỏ lọc — `app.py:275`).

### Numbered steps (USER chạy — HARD-STOP)

1. **[USER]** Xác định danh sách origin hợp pháp cần CORS: host OAuth redirect (nếu dùng WebView qua browser engine), host dev-tooling/Swagger UI. Native APK KHÔNG cần (không browser).
2. **[USER]** Ghi `site_config.json` (qua `bench set-config` HOẶC sửa file — **HARD-STOP**):
   ```jsonc
   // site_config.json — LIST tường minh, KHÔNG "*"
   "allow_cors": ["https://<host-hop-phap-1>", "https://<host-hop-phap-2>"]
   ```
   - **CẤM:** `"allow_cors": "*"` ở prod. Nếu chỉ cần 1 origin, dùng list 1 phần tử (Frappe coerce string→list — `app.py:276-277`).
3. **[USER]** **Reload gunicorn** để conf live ở HTTP (gunicorn `--preload` — conf đọc lúc xử lý request nhưng worker cần fresh). **HARD-STOP.**

> **Vì sao HARD-STOP:** ghi `site_config` + reload. Verify CORS → §6 (curl preflight OPTIONS với `Origin` hợp lệ → nhận header; `Origin` lạ → KHÔNG nhận).

---

## 3. §3 — Public host / reverse-proxy + QR deep-link host (conf key)

> **Mục tiêu:** có **public HTTPS host** (reverse-proxy + TLS + domain) cho: (a) OAuth redirect, (b) bearer-over-HTTPS, (c) QR deep-link mở được trên điện thoại. Hiện dev = nginx HTTP:80 `server_name` rỗng — KHÔNG dùng prod (`02 §4.1`).

**Cơ chế QR host (verified — KHÔNG bịa key):**

| Knob | Giá trị thật | Evidence | Hiện trạng |
|---|---|---|---|
| `site_config.assetcore_qr_base_url` | host công khai cho QR deep-link (validate scheme http/https, no path/query) | `services/imm00.py:635` (`_QR_BASE_URL_CONF_KEY = "assetcore_qr_base_url"`) · `:685` (`_build_qr_url`) | `None` ⇒ fallback host nội bộ `http://miyano` (camera điện thoại KHÔNG mở được — blocker đã biết `02 §4.2`) |

> ⚠️ **App native KHÔNG dùng URL `/a/<token>`** (không server route — là SPA-only; `hooks.py:400` website_route_rules chỉ có `/assetcore/<path>`). App tự decode QR → **parse token khỏi URL** → gọi thẳng `resolve_qr_token`/`get_asset_scan_info` (`02 §4.2`, `06`/`05`). `assetcore_qr_base_url` vẫn cần set để QR payload trỏ host công khai (web/cross-channel).

### Numbered steps (USER chạy — HARD-STOP)

1. **[USER]** Provision domain + TLS cert hợp lệ cho host công khai (vd `https://mobile.<benh-vien>.vn`).
2. **[USER]** Cấu hình reverse-proxy nginx: `server_name` = domain, `listen 443 ssl`, redirect HTTP→HTTPS, proxy_pass tới gunicorn backend. (KHÔNG dùng bench-generated dev nginx HTTP:80.) **HARD-STOP** (sửa nginx).
3. **[USER]** (Bảo mật go-live) Thêm `limit_req` cho location `/api/method/frappe.integrations.oauth2.*` (rate-limit oauth2 ở TẦNG NGOÀI — KHÔNG sửa frappe core; T1, `ADR-MOBILE-004 (a)` · `08 §3b`). **HARD-STOP.**
4. **[USER]** Ghi `site_config.assetcore_qr_base_url` = host HTTPS công khai (key thật `services/imm00.py:635`):
   ```jsonc
   "assetcore_qr_base_url": "https://mobile.<benh-vien>.vn"
   ```
5. **[USER]** `nginx -t` + reload nginx + **reload gunicorn**. **HARD-STOP.**

> **Vì sao HARD-STOP:** sửa nginx + TLS + ghi `site_config` + reload. Verify → §6 (curl HTTPS host → 200/302; QR payload chứa host công khai).

---

## 4. §4 — FCM server credentials trong `site_config` (bảo mật key)

> **Mục tiêu:** đặt FCM service-account credentials để Phase E gửi push (FCM Admin SDK trực tiếp — KHÔNG relay Frappe Cloud). **Bám [`06-push-fcm.md §5.2`](./06-push-fcm.md) + [`ADR-MOBILE-002`](./ADR-MOBILE-002.md).** Đây là chuẩn bị creds (impl gửi push = Phase E); đặt ở Phase B cùng nhóm `allow_cors`/host để 1 lần go-live.
> ⚠️ **KHÔNG IN GIÁ TRỊ THẬT** của credentials trong tài liệu / commit / log / API. Key name dưới là **ví dụ minh hoạ** (`06 §5.2` dùng `vd`) — Phase E chốt tên cuối khi impl.

**Cơ chế (verified — lý do KHÔNG relay):**

| Điểm | Evidence | Hệ quả |
|---|---|---|
| Frappe `push_notification.py` chỉ PROXY tới relay Frappe Cloud (`notification_relay.api.*`) | `06 §1.1` · `push_notification.py:240-241` (disable relay → raise) | KHÔNG air-gapped ⇒ KHÔNG dùng cho self-host NĐ98 ⇒ chốt FCM direct (`ADR-MOBILE-002`) |
| Creds đọc qua `site_config`, KHÔNG lộ qua API | kỷ luật `get_password` (`push_notification.py:202`) | BE đọc lúc gửi (Phase E); APK KHÔNG biết server-key |

### Numbered steps (USER chạy — HARD-STOP)

1. **[USER]** Tạo FCM project ở Firebase console + tải service-account JSON. **KHÔNG commit file JSON vào repo.**
2. **[USER]** Đặt file JSON ngoài repo (vd thư mục site private) + ghi `site_config.json` đường dẫn + project id (tên key ví dụ — `06 §5.2`):
   ```jsonc
   // GIÁ TRỊ THẬT KHÔNG in ở đây / KHÔNG commit / KHÔNG log
   "fcm_service_account_path": "/đường/dẫn/ngoài/repo/service-account.json",
   "fcm_project_id": "<fcm-project-id>"
   ```
3. **[USER]** Xác nhận file JSON KHÔNG nằm trong working tree git (`.gitignore` site config dir) + KHÔNG xuất hiện trong bất kỳ API response/log nào.
4. **[USER]** **Reload gunicorn** (creds live ở Phase E khi impl kênh #3). **HARD-STOP.**

> **Vì sao HARD-STOP:** ghi creds nhạy cảm vào `site_config` + reload. Verify creds = trách nhiệm Phase E (khi impl gửi FCM thật) — go-live Phase B chỉ ĐẶT creds; KHÔNG có smoke push ở §6 (push impl = Phase E).

---

## 5. §5 — Versioning & Deprecation: header `Sunset` + `Deprecation` cho `/api/mobile/v1`

> **Mục tiêu:** quy trình quản trị vòng đời API mobile khi cần loại bỏ/đổi endpoint, dùng chuẩn HTTP `Deprecation` (draft) + `Sunset` (RFC 8594). **GAP THẬT:** hiện KHÔNG có header `Sunset`/`Deprecation` ở bất kỳ doc/endpoint nào — đây là đặc tả MỚI (versioning chưa được phủ trước đó).

### 5.1 Hiện trạng versioning (verified)

| Knob | Trạng thái | Evidence |
|---|---|---|
| Routing versioned `/api`, `/api/v1`(=legacy `/api`), `/api/v2` | ✅ CÓ ở Frappe | `02 §4.3` · `frappe/api/__init__.py:80-89` (`get_api_version`) |
| Endpoint AssetCore hiện gọi qua `/api/method/<dotted>` (RPC) | ✅ | `02 §4.3` (FE-BE naming contract) |
| Namespace BỌC `api/mobile/v1` (nếu cần lớp wrapper) | ⬜ Phase C quyết định | `00 §3 Phase C` · `06 §6` (device-token dùng `api.mobile.v1.*`) |
| Header `Sunset`/`Deprecation` | ❌ **CHƯA có** (gap) | grep `Sunset`/`Deprecation` trong app = 0 |

> **Quyết định versioning (chốt Phase A — runbook):**
> - **MVP**: endpoint nghiệp vụ giữ `/api/method/<dotted>` (RPC) — KHÔNG ép `/api/v2`. Nếu cần lớp BỌC ổn định cho mobile → namespace `api/mobile/v1` (đã dùng cho 2 path device-token: `register_device_token`/`unregister_device_token` — `openapi/*.yaml`, `06 §6`).
> - **Version trong path** (`mobile/v1`) là contract chính; header `Sunset`/`Deprecation` là cơ chế **báo trước khi loại bỏ** một version/endpoint.

### 5.2 Đặc tả header (cơ chế khi deprecate)

| Header | Chuẩn | Giá trị | Khi nào set |
|---|---|---|---|
| `Deprecation` | draft IETF `Deprecation-Header` | `true` HOẶC HTTP-date bắt đầu deprecate | Khi 1 endpoint/version `mobile/v1` được đánh dấu sẽ loại bỏ |
| `Sunset` | RFC 8594 | HTTP-date thời điểm endpoint NGỪNG phục vụ (vd `Sun, 01 Mar 2026 00:00:00 GMT`) | Cùng lúc / sau `Deprecation`, báo hạn chót |
| `Link` (tuỳ chọn) | RFC 8288 | `rel="successor-version"` trỏ endpoint thay thế | Khi có version kế (`mobile/v2`) |

> **Impl header = Phase C/E** (lớp wrap `api/mobile/v1` set response header). Runbook này chốt **cơ chế + quy trình**, KHÔNG impl. App native phải ĐỌC `Sunset`/`Deprecation` (nếu có) → cảnh báo người dùng cập nhật / log telemetry.

### 5.3 Quy trình deprecate 1 endpoint/version (numbered)

1. **[BA + BE]** Quyết định endpoint/version cần loại bỏ + endpoint thay thế (nếu có) → cập nhật `openapi/*.yaml` (`deprecated: true` cho operation; KHÔNG xoá ngay).
2. **[BE Phase C/E]** Wrapper `api/mobile/v1` set `Deprecation: true` + `Sunset: <HTTP-date>` (+ `Link` successor) cho endpoint đó. (KHÔNG impl ở Phase A.)
3. **[BA]** Thông báo repo native (đội mobile) qua docset + changelog: hạn `Sunset`, endpoint thay thế, hành động cần làm.
4. **[Đội native Phase D]** App đọc header → hiện cảnh báo "phiên bản API sẽ ngừng hỗ trợ" / ép cập nhật trước `Sunset`.
5. **[USER/Admin]** Sau `Sunset` date + xác nhận telemetry không còn client dùng version cũ → gỡ endpoint (deploy mới — **HARD-STOP**).

### 5.4 OpenAPI versioning note

- OpenAPI `info.version` hiện = `0.1.0-skeleton`; `servers` = public HTTPS host (Phase B). **KHÔNG đổi path/operationId** (giữ 15 path + 2 opId device-token nguyên).
- Bồi (nếu cần) **chỉ ở `info.description`/`servers.description`**: ghi chú cơ chế versioning + `Sunset`/`Deprecation` trỏ `10 §5`. KHÔNG đụng `paths:`.

---

## 6. §6 — Checklist go-live (pre-flight · execute theo thứ tự · post-verify smoke)

> Tick-box ĐO ĐƯỢC. USER tick khi thực thi xong. Agent KHÔNG tick hộ — chỉ đặc tả. Thứ tự execute = §1→§5.

### 6.1 Pre-flight (chuẩn bị — kiểm trước khi execute)

- [ ] **(pre)** Domain + TLS cert hợp lệ đã sẵn sàng cho public host (§3)
- [ ] **(pre)** Role field-tech (KTV) đã tồn tại + có đúng capability/Role Profile (`03 §4` allowed_roles)
- [ ] **(pre)** FCM project + service-account JSON đã tạo, đặt NGOÀI repo (§4) — KHÔNG commit
- [ ] **(pre)** Danh sách origin hợp pháp cho `allow_cors` đã xác định (KHÔNG `'*'`) (§2)
- [ ] **(pre)** Backup `site_config.json` + nginx conf hiện tại (rollback §7)

### 6.2 Execute (theo thứ tự §1→§5 — HARD-STOP USER mỗi bước)

- [ ] **(1)** Tạo `OAuth Client` (Auth Code + PKCE-ready + redirect native-scheme + allowed_roles least-priv) — §1 (`03 §4` field)
- [ ] **(2)** `site_config.allow_cors` = LIST origin tường minh, KHÔNG `'*'` — §2 (`app.py:269/275/283-284`)
- [ ] **(3a)** Reverse-proxy nginx + TLS + `server_name` domain + HTTP→HTTPS redirect — §3
- [ ] **(3b)** nginx `limit_req` cho `oauth2.*` (rate-limit tầng ngoài) — §3 (`ADR-004 a`)
- [ ] **(3c)** `site_config.assetcore_qr_base_url` = host HTTPS công khai — §3 (`imm00.py:635`)
- [ ] **(4)** FCM creds trong `site_config` (`fcm_service_account_path`/`fcm_project_id`) — §4, KHÔNG commit/log/API
- [ ] **(5)** (nếu Phase C/E) wrapper `api/mobile/v1` + cơ chế header `Sunset`/`Deprecation` sẵn sàng — §5
- [ ] **(reload)** `bench migrate` (nếu đổi cap) + **reload gunicorn** + reload nginx — **HARD-STOP USER** (gunicorn `--preload`: conf/cap live SAU reload)

### 6.3 Post-verify (smoke test — 2 lệnh curl, sau reload)

> ⚠️ Chạy SAU khi USER reload gunicorn (gunicorn `--preload` ⇒ conf/cap chỉ live ở HTTP sau reload). Thay `$HOST` = public HTTPS host, `$CLIENT_ID` = OAuth Client vừa tạo, `$AUTHCODE`/`$verifier` từ luồng PKCE (`03 §1.3`).

**Smoke 1 — lấy token (curl `get_token`):** chứng minh OAuth2 bật + client cấu hình đúng.
```bash
# Đổi code → token (sau khi authorize trong WebView/Custom Tab — 03 §1.3 bước b/c)
curl -sS -X POST "https://$HOST/api/method/frappe.integrations.oauth2.get_token" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=$AUTHCODE" \
  --data-urlencode "redirect_uri=assetcore://oauth/callback" \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "code_verifier=$verifier"
# PASS khi: 200 {"access_token":"...","refresh_token":"...","expires_in":3600,"token_type":"Bearer",...}
```

**Smoke 2 — gọi business-endpoint qua bearer (curl) → envelope chuẩn:** chứng minh bearer→set_user→RBAC→envelope hoạt động end-to-end.
```bash
ACCESS_TOKEN="<access_token từ Smoke 1>"
curl -sS "https://$HOST/api/method/assetcore.api.imm00.get_asset_scan_info?token=<qr_token>" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# PASS khi: HTTP 200, body = success envelope chuẩn {"success":true,"data":{...available_actions, pm_overdue, calibration_overdue...}}
#           (envelope shape: 04-api-contract.md §3; endpoint cap=asset.read — openapi/*.yaml)
# FAIL nếu: 401 (token sai/chưa reload) · 403 (thiếu cap — kiểm allowed_roles/Role Profile) · raw traceback (chưa reload / 03 §6 live-finding 401-Guest raw)
```

**Verify bổ sung (tick-box):**
- [ ] **(verify-oauth)** Smoke 1 trả `access_token`+`refresh_token`+`expires_in=3600` (D-AUTH OK)
- [ ] **(verify-biz)** Smoke 2 trả HTTP-200 + success envelope chuẩn (bearer→RBAC→envelope OK)
- [ ] **(verify-cors)** curl preflight `OPTIONS` với `Origin` hợp lệ → nhận `Access-Control-Allow-Origin`; `Origin` lạ → KHÔNG nhận (list-origin OK, `app.py:275`)
- [ ] **(verify-cors-neg)** grep `site_config` → `'*'` KHÔNG xuất hiện (T3)
- [ ] **(verify-host)** curl `https://$HOST/api/method/frappe.integrations.oauth2.openid_configuration` → 200, issuer = host công khai
- [ ] **(verify-qr)** QR payload mới chứa host công khai (KHÔNG `http://miyano`) — `imm00.py:_build_qr_url`
- [ ] **(verify-audit)** action từ Smoke 2 (nếu là write) xuất hiện ở audit-chain với actor = user thật (`verify_audit_chain`, `08 §2`)

> **Liên kết bảo mật go-live:** checklist security đầy đủ (T1–T7 + 3 nhóm mitigation) ở [`08-security-compliance.md §4`](./08-security-compliance.md) — runbook này gom phần **deploy/ops execute**; KHÔNG nhân đôi threat model.

---

## 7. §7 — Rollback + ai-chạy / HARD-STOP mỗi bước

> Nếu go-live lỗi (smoke FAIL / downtime / lộ creds) → rollback theo thứ tự NGƯỢC. Mọi bước = **HARD-STOP USER**.

| # | Sự cố | Rollback (USER chạy — HARD-STOP) | Ghi chú |
|---|---|---|---|
| R1 | Smoke 2 trả 403 toàn bộ | Kiểm `allowed_roles` OAuth Client + Role Profile field-tech; KHÔNG mở rộng scope bừa (giữ least-priv) | Không phải rollback — fix cap; reload gunicorn |
| R2 | Smoke 1 lỗi (token) | Xoá/sửa OAuth Client record; kiểm `redirect_uris` khớp; reload | DB write — HARD-STOP |
| R3 | CORS sai / lộ wildcard | Khôi phục `allow_cors` từ backup `site_config` (§6.1 pre); CẤM `'*'`; reload gunicorn | Ghi site_config — HARD-STOP |
| R4 | Host/nginx down | `nginx -t` rồi khôi phục nginx conf từ backup; reload nginx | Sửa nginx — HARD-STOP |
| R5 | QR trỏ sai host | Khôi phục/sửa `assetcore_qr_base_url`; reload | Ghi site_config — HARD-STOP |
| R6 | **Lộ FCM creds** | XOAY credentials ở Firebase console NGAY + thay file JSON + xoá giá trị cũ khỏi `site_config`; reload | Sự cố bảo mật — ưu tiên cao nhất (§4) |
| R7 | Cap-set không live sau đổi | `bench migrate` HOẶC bust `ac_caps::*` + reload gunicorn (gunicorn `--preload`) | HARD-STOP |

> **Nguyên tắc rollback:** luôn có backup `site_config.json` + nginx conf TRƯỚC khi execute (§6.1). Rollback creds (R6) = ưu tiên tuyệt đối (xoay key ở provider, không chỉ xoá local).

---

## 8. §8 — Tham chiếu chéo

- **Khảo sát feasibility (survey — nguồn gap/blocker mà runbook này thực thi):** [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) (§0 TL;DR · §7 gaps · §8 recommendations) — **02 = feasibility, 10 = execute** (§0).
- **OAuth Client field checklist (KHÔNG nhân đôi — §1 trỏ đây):** [`03-auth-oauth2.md §4`](./03-auth-oauth2.md) · sequence PKCE + curl mẫu: `03 §1.3`.
- **Pre-flight verifier B-1 (B0-PREFLIGHT — §1 chạy sau tạo record):** [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) (`verify_oauth_client()` READ-ONLY chấm 7 điều kiện B-1; runbook `10 §1` = execute, `12 §1` = verify).
- **FCM creds bảo mật + cơ chế push (§4 trỏ đây):** [`06-push-fcm.md §5.2`](./06-push-fcm.md) · ADR cơ chế push: [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md).
- **Bảo mật & checklist security go-live (T1–T7 · 3 nhóm mitigation — KHÔNG nhân đôi):** [`08-security-compliance.md §3-§4`](./08-security-compliance.md) · mô hình bảo mật chốt: [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md).
- **Hợp đồng envelope/error (smoke 2 envelope shape):** [`04-api-contract.md`](./04-api-contract.md) §3.
- **OpenAPI (versioning note — KHÔNG đổi path/opId):** [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (info/servers description trỏ §5).
- **Tổng quan + roadmap + 3 quyết định:** [`00-overview.md`](./00-overview.md) (§3 Phase B/C/E · §4 chỉ mục · §6 số đã cấp).
- **Exit gate (A11) — runbook numbered steps (§1–§6) gom vào Phase-B prereqs (B-1..B-7) + checklist go/no-go A→B:** [`11-phase-a-exit.md`](./11-phase-a-exit.md) §2 (prereqs trỏ runbook này) · §3 (checklist B-verify = smoke `§6.3`).
- **Frappe core (read-only, KHÔNG sửa):** `frappe/integrations/oauth2.py` (provider) · `frappe/app.py` (CORS `:269/:275/:283-284`) · `frappe/api/__init__.py` (versioning) — provider/CORS/version.
- **AssetCore source:** `assetcore/services/imm00.py:635/685` (`assetcore_qr_base_url`/`_build_qr_url`) · `assetcore/services/notifications.py::_dispatch` (kênh #3 push Phase E) · `assetcore/utils/lifecycle.py` (audit NĐ98).
