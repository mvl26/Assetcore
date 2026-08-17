# EPIC-G — Go-live & Hardening (Mobile BE)

> **Bộ tài liệu "BE COMPLETION"** — lớp AssetCore = backend-for-mobile. Mục tiêu chung:
> repo UI mobile **native** (Flutter/RN, project KHÁC) gọi API chạy app field-tech MVP
> 6-flow END-TO-END THẬT trên cloud. EPIC-G = **đưa code lên cloud + siết bảo mật prod**.
>
> **Vị trí trong chuỗi 5 EPIC:** `C` (contract, độc lập) → `B` ∥ thiết kế `D` → **`G`
> (cần USER: cloud + site_config)** → `D` (cần B + FCM creds) → `V` (chốt cuối).
> EPIC-G phụ thuộc **C** (yaml/contract đã codegen-ready) + **B** (OAuth Client provisioned).
> EPIC-G mở đường cho **D** (push) + **V** (codegen verify + handoff) chạy THẬT trên public host.
>
> **3 quyết định AUTHORITATIVE (user duyệt 2026-06-11):** OAuth2+refresh (Frappe provider,
> Auth Code + PKCE, scope↔capability SSoT) · field-tech MVP · native repo riêng.
> Native APK **KHÔNG cần CORS** (không browser engine) — CORS trong EPIC-G CHỈ áp khi có
> UI web/PWA/Swagger-UI/WebView-OAuth.

---

## 1. Scope & Mục tiêu

### 1.1 Trong scope (EPIC-G)
Đưa lớp mobile-BE (đã viết, hiện UNCOMMITTED + chưa-live-HTTP) lên cloud và siết cấu hình
bảo mật prod, để 6-flow field-tech MVP **reachable + an toàn** từ ngoài internet:

1. **G1** — Deploy code lên cloud (commit + `bench migrate` + `bench restart` + FE build nếu cần).
2. **G2** — `site_config`: `host_name` / HTTPS / reverse-proxy (CORS CHỈ nếu web — native bỏ qua).
3. **G3** — Tắt `allow_error_traceback` prod (chống leak traceback/SQL) + rate-limit headers (`conf.rate_limit` hoặc nginx `limit_req`).
4. **G4** — Security gate verify (no-traceback-leak · CORS no-wildcard · no token-leak · rate-limit header).

### 1.2 Ngoài scope (post-MVP — ghi rõ, KHÔNG làm trong EPIC-G)
- Offline-sync (chương `07-offline-sync.md`) — KHÔNG go-live cho MVP.
- Manager/duyệt, mở rộng đa-module — post-MVP.
- Pentest đầy đủ + scan bề mặt OAuth2/token (Phase F hardening) — chỉ liệt kê làm DoD tương lai, KHÔNG đóng trong EPIC-G.
- Phần **provisioning OAuth Client** (tạo client, 7 điều kiện preflight) = **EPIC-B** (phụ thuộc B2/B-preflight). EPIC-G chỉ *consume* client đã có.

### 1.3 Mục tiêu kiểm-được (DoD TỔNG EPIC-G)
**HTTPS reachable ngoài** · **security gate PASS:** (a) no traceback/SQL leak ở 401/403/429;
(b) CORS no-wildcard (hoặc CORS OFF nếu thuần native); (c) no token-leak trong response/log;
(d) rate-limit headers (`Retry-After`/`X-RateLimit-*`) phát ra ở 429 **CHỈ KHI `conf.rate_limit`/nginx
`limit_req` set** (KHÔNG do `@rate_limit` decorator một mình — xem §3.3 knob `rate_limit`, G3/G4(d)).
Mỗi điều kiện gắn lệnh verify ở `G4`.

---

## 2. Actor

| Actor | Vai trò trong EPIC-G |
|---|---|
| **USER / DevOps** | Chủ thể HARD-STOP: chạy `git commit/push`, `bench migrate`, `bench restart`, sửa `sites/<site>/site_config.json`, đổi System Setting `allow_error_traceback`, cấu hình nginx/TLS. Agent KHÔNG tự thực thi. |
| **[BA]** | Bồi đặc tả checklist vào `08 §4` / `10 §6` / ADR-004 Consequences; CI-guard placeholder host. |
| **[BE]** | Cung cấp helper verify đọc-only (preflight/security-gate); KHÔNG sửa `api/*.py` business logic trong EPIC-G. |
| **[QA]** | Chạy security-gate smoke (curl + `bench execute`) sau khi USER deploy; xác nhận DoD. |
| **App native (Flutter/RN)** | Consumer cuối — gọi public HTTPS host bằng bearer token sau khi G1–G4 PASS. |

---

## 3. Hiện trạng (grounded — file:line CHÍNH XÁC, read-only verified 2026-06-11)

### 3.1 Code mobile-BE — UNCOMMITTED + chưa-live-HTTP
| Hạng mục | Vị trí | Trạng thái |
|---|---|---|
| Lớp openapi serve + overrides | `assetcore/api/openapi.py` · `assetcore/api/openapi_overrides.py` · `assetcore/www/api-docs.{html,py}` · `assetcore/public/swagger-ui/` | `??` UNCOMMITTED |
| Lớp mobile API | `assetcore/api/mobile/` (gồm `preflight.py`) | `??` UNCOMMITTED |
| Docset mobile + ADR + yaml | `docs/mobile/` (13 chương + 4 ADR + `openapi/assetcore-mobile.openapi.yaml`) | `??` UNCOMMITTED |
| Test mobile/oas | `assetcore/tests/test_mobile_*.py` (4) + `test_oas_*.py` (≥13) | `??` UNCOMMITTED |
| Sửa khác | `M`: `api/dashboard.py·imm01·imm02·imm04·imm14·imm16` · `hooks.py` · `tests/test_dashboard.py` · `docs/imm-00/README.md` · `frontend/vite.config.ts` | `M` UNCOMMITTED |

### 3.2 Cơ chế "in-handler-error đến trên HTTP-200" (ảnh hưởng security-gate, đã xác minh @source)
- Service nghiệp vụ raise `ServiceError(http_status=…)` — `assetcore/services/shared/errors.py:36-42` (factory: `not_found`→404 `:50`, `forbidden`→403 `:54`, `unauthorized`→401 `:58`, `validation`→422 `:62`, `conflict`→409 `:66`).
- `handle()` bắt `ServiceError` → `_service_error_to_envelope` — `assetcore/utils/api_handler.py:50-54`.
- `_err(...)` build body chứa `code` + `http_status` — `assetcore/utils/response.py:95-160`; body field `http_status` set ở `:127/:131/:137`. **KHÔNG** set `frappe.local.response.http_status_code` ⇒ **HTTP status-line VẪN 200**; mã thật chỉ nằm trong body `http_status`.
- Bằng chứng không có `after_request` đổi status-line: `assetcore/hooks.py` chỉ có `website_route_rules` (`hooks.py:406`); KHÔNG hook `after_request`. → in-handler 401/403/404/409/422 → HTTP-200 + Error body (ADR contract EPIC-C; cross-ref C task contract).
- Hệ quả cho EPIC-G G4: security-gate phân biệt **dispatcher-403** (status-line 403 THẬT, guest/no-token, `frappe/__init__.py ~876`) vs **in-handler cap-403** (HTTP-200 + `{code:FORBIDDEN, http_status:403}`). Xem LL-DEPLOY-06.

### 3.3 5 site_config / System-Setting knob — hiện ABSENT (state cloud chưa go-live)
| Knob | Vị trí gate THẬT (grounded) | Hiện trạng (dev `miyano`) | Cần (prod) |
|---|---|---|---|
| `host_name` | `frappe/utils/data.py:1599` (`def get_url`) · `:1605` (`host_name = ...conf.host_name or ...conf.hostname`); vắng ⇒ fallback Host header `:1611-1614` → `protocol + ...site` `:1631` = `http://miyano` nội bộ ⇒ `get_url()`/OIDC issuer sai (KHÔNG public host). **GUARD-9 machine-check** (`TestSecGateHostNameIssuerDoc`): source-grounded @source + prose-invariant `08 §5.1(f)`/`10 §3`+§6.2(3c0)+§6.3, phủ-định `KHÔNG http://miyano` | `None` | public HTTPS host (`get_url()`/`openid_configuration issuer == public host`) |
| `allow_cors` | `frappe/app.py:275` lọc list-origin BỎ QUA khi value=`'*'`; `:283-284` echo `Access-Control-Allow-Credentials:true`+`Origin` khi set (ADR-004 §c) | `None` (= CORS OFF) | LIST origin tường minh (CHỈ nếu web) / GIỮ `None` nếu thuần native |
| `allow_error_traceback` | **System Setting (KHÔNG site_config), default=1 (ON)** — `system_settings.json:262-265`; gate `frappe/utils/response.py:60-65` `is_traceback_allowed()`, dùng `:36/:182/:190/:203` | mặc định 1 ⇒ prod LEAK traceback/SQL ở 401/403/429 raw | System Setting → **0** |
| `rate_limit` (conf) | `@rate_limit` dùng `frappe.rate_limiter`; thiếu key `conf.rate_limit` ⇒ `frappe.local.rate_limiter` không instantiate ⇒ 429 KHÔNG có `Retry-After`/`X-RateLimit-*` (LL-DEPLOY-04) | `None` | `conf.rate_limit` HOẶC nginx `limit_req` |
| `assetcore_qr_base_url` | QR deep-link host (`06 §5.2` / `10 §3`) — không thuộc G4 gate nhưng cần cho flow-2 (quét QR) | `None` | public HTTPS host (set ở B/G2) |

### 3.4 Helper verify-only đã có (consume trong G4)
- `assetcore/api/mobile/preflight.py::verify_oauth_client()` — READ-ONLY, `:147`; trả `ready: bool`+`checks`+`blockers` VI, **KHÔNG raise**, **KHÔNG leak traceback** (`:23/:151`); 7 điều kiện B-1 (`client_count` + 6 cấp-record `:179-213`). Test: `assetcore/tests/guards/test_mobile_preflight.py` (TC 01–09).
- CI-guard placeholder host: `openapi/assetcore-mobile.openapi.yaml` servers placeholder `REPLACE-WITH-PUBLIC-HOST` (yaml:107) + version skeleton `0.1.0-skeleton` (yaml:89) — guard chặn lọt prod build.

### 3.5 Runbook nền đã có (EPIC-G chỉ *tham chiếu* — KHÔNG nhân đôi)
- `docs/mobile/10-deploy-ops.md` — RUNBOOK numbered: §1 OAuth2 · §2 CORS · §3 public host · §4 FCM · §5 versioning (`Sunset`/`Deprecation` header) · §6 checklist pre-flight/execute/smoke curl.
- `docs/mobile/08-security-compliance.md §4` — checklist Security Go-live (T1–T7).
- `docs/mobile/ADR-MOBILE-004.md` — mô hình bảo mật (rate-limit tầng ngoài · 1 SSoT quyền · CORS list-origin · audit NĐ98).

---

## 4. Tasks

> Mỗi task: mô tả · Files (Create/Modify exact path) · Acceptance (lệnh kiểm-được) ·
> owner · tag `[AUTO]` (factory tự đóng = doc/checklist/test introspection-only) hoặc
> `[HARD-STOP USER]` (cloud/commit/migrate/restart/site_config/System-Setting) · Dependencies.

---

### G1 — Deploy code mobile-BE lên cloud (commit + migrate + restart)

**Mô tả.** Đưa toàn bộ batch mobile-BE UNCOMMITTED (§3.1) lên cloud: commit + push → `bench
migrate` (tạo doctype OAuth Client/Bearer Token + device-token EPIC-D, TỰ bust `ac_caps::*`
qua `after_migrate→_bust_capability_cache`, cap-set bump) → `bench restart` (gunicorn
`--preload` worker cũ giữ `CAPABILITY_MAP`/imports cũ trong RAM — thiếu restart ⇒ endpoint
mobile deny cap mới hoặc 417 AttributeError) → FE build riêng nếu deploy kèm SPA. **Đây là
điều kiện tiên quyết để 6-flow live HTTP** — toàn bộ EPIC-C yaml/handler + EPIC-B OAuth +
EPIC-D push CHỈ live HTTP sau bước này (LL-DEPLOY-01/03).

- **Files (Modify — USER thao tác qua git/bench, KHÔNG agent):** working tree `??/M` ở §3.1 (commit theo nhóm logic — KHÔNG 1 commit khổng lồ); `assetcore/__version__.py` (bump release nếu phát hành tag).
- **Acceptance:**
  - `bench --site <site> migrate` exit 0; verify doctype: `bench --site <site> execute "frappe.db.exists('DocType','OAuth Client')"` trả tên (KHÔNG None).
  - `bench --site <site> execute assetcore.api.mobile.preflight.verify_oauth_client` chạy được (fresh import OK) — chứng minh module mobile import sạch.
  - Sau `bench restart`: hit endpoint authenticated KHÔNG trả HTTP-417 `AttributeError ... no attribute` (stale-worker gone — LL-DEPLOY-01).
  - Cap-set busted: log `[AssetCore] ac_caps::* busted (cap-set vN.<hash>)` xuất hiện sau migrate.
- **Owner:** USER (chạy) · [BE] đề xuất thứ tự commit + verify lệnh.
- **Tag:** `[HARD-STOP USER]` (git commit/push + migrate + restart — HARD-STOP bền vững).
- **Dependencies:** **C** (yaml + handler contract đóng — codegen-ready) · **B** (OAuth Client provisioned, B2/B-preflight). KHÔNG có C → contract chưa khoá; KHÔNG có B → migrate tạo doctype nhưng chưa có client để verify.

---

### G2 — `site_config`: public host (`host_name`) + HTTPS/reverse-proxy + CORS (CHỈ nếu web)

**Mô tả.** Set `host_name` = public HTTPS host để `get_url()`/`openid_configuration` issuer
== host công khai (KHÔNG `http://miyano` nội bộ — camera/QR deep-link mới mở được). Dựng
reverse-proxy nginx + TLS (HTTP→HTTPS redirect; HTTP:80 KHÔNG expose mobile). **CORS:** native
APK KHÔNG cần CORS (D-STACK — không browser engine) ⇒ GIỮ `allow_cors=None` (CORS OFF) nếu
thuần native; CHỈ set `allow_cors` = **LIST origin tường minh** khi có UI web/PWA/Swagger-UI/
WebView-OAuth — **TUYỆT ĐỐI KHÔNG** `'*'` (vì `app.py:275` bỏ lọc list khi `'*'`, `:283-284`
echo credentials = lỗ T3; ADR-004 §c cấm tường minh). Cũng set `assetcore_qr_base_url` = public
HTTPS host (flow-2 quét QR).

- **Files (Modify — USER):** `sites/<site>/site_config.json` (`host_name`, `assetcore_qr_base_url`, `allow_cors` CHỈ-nếu-web) · `~/frappe-bench/config/nginx.conf` (symlink + TLS) — KHÔNG commit site_config.
- **Files (Create — [BA] đặc tả, AUTO):** không tạo file mới; bồi đặc tả phân-biệt native-vs-web CORS vào `docs/mobile/10-deploy-ops.md §2` + checklist `host_name` vào `10 §6.2`.
- **Acceptance:**
  - `bench --site <site> execute "frappe.utils.get_url()"` trả `https://<public-host>` (KHÔNG `http://miyano`).
  - `bench --site <site> execute "frappe.get_website_settings"` / `openid_configuration` issuer == public HTTPS host.
  - `curl -sI https://<public-host>/api/method/ping` → `HTTP/2 200` (HTTPS reachable ngoài); `curl -sI http://<public-host>/...` → `301/308` redirect HTTPS.
  - CORS-gate (nếu web): `curl -s -H "Origin: https://evil.test" -I https://<public-host>/api/method/...` KHÔNG có `Access-Control-Allow-Origin: https://evil.test` (origin ngoài list bị từ chối); `grep -c '"\*"' sites/<site>/site_config.json` cho key `allow_cors` == 0.
- **Owner:** USER (site_config/nginx) · [BA] (đặc tả CORS native-vs-web + checklist).
- **Tag:** `[HARD-STOP USER]` cho site_config/nginx · `[AUTO]` cho phần đặc tả `10 §2/§6.2`.
- **Dependencies:** **G1** (code phải lên cloud trước) · **B** (OAuth redirect/host khớp public host).

---

### G3 — Tắt `allow_error_traceback` prod + rate-limit headers

**Mô tả.** **Tắt traceback leak prod:** `allow_error_traceback` là **System Setting** (KHÔNG
site_config, KHÔNG developer_mode), default=1 (ON) — `system_settings.json:262-265`; gate THẬT
`frappe/utils/response.py:60-65 is_traceback_allowed()` (dùng `:36/:182/:190/:203`). Khi ON,
prod LEAK traceback/SQL ở response lỗi 401/403/429 raw (dispatcher-level) ⇒ USER set System
Setting `allow_error_traceback=0` trên prod. **Rate-limit headers:** `@rate_limit` (vd
`imm00.py:328/371/531/594`) phát 429 nhưng nếu thiếu `conf.rate_limit` thì `frappe.local.
rate_limiter` không instantiate ⇒ 429 KHÔNG có `Retry-After`/`X-RateLimit-*` (backoff câm) —
LL-DEPLOY-04. USER set `conf.rate_limit` HOẶC nginx `limit_req` (ADR-004 §a: rate-limit tầng
ngoài cho OAuth2). [BA] bồi đặc tả + evidence vào `08 §4` / ADR-004 Consequences.

- **Files (Modify — USER):** System Setting `allow_error_traceback`=0 (qua desk hoặc `bench execute`) · `sites/<site>/site_config.json` key `rate_limit` HOẶC `config/nginx.conf` `limit_req`.
- **Files (Modify — [BA], AUTO):** `docs/mobile/08-security-compliance.md §4` (thêm item "(b) PROD TẮT `allow_error_traceback` System-Setting=0", evidence `response.py:60-65`, ghi RÕ KHÔNG phải developer_mode/site_config) · `docs/mobile/ADR-MOBILE-004.md` Consequences (cùng item) · `docs/mobile/10-deploy-ops.md §6.2` (rate-limit header note).
- **Acceptance:**
  - `bench --site <site> execute frappe.utils.response.is_traceback_allowed` trả `False` trên prod/staging (gate đóng).
  - Response lỗi raw KHÔNG chứa traceback: `curl -s https://<host>/api/method/<auth-required-method>` (guest) → body KHÔNG có `"exc"`/`Traceback (most recent call last)` (chỉ `exc_type`/message ngắn).
  - 429 có header **CHỈ KHI `conf.rate_limit`/nginx `limit_req` set** (HARD-STOP USER): gọi vượt ngưỡng `@rate_limit` (vd resolve QR) → response 429 chứa `Retry-After` + `X-RateLimit-*` (verify `curl -sI`). **KHÔNG do `@rate_limit` decorator một mình** — decorator throw-path `frappe.throw(..., RateLimitExceededError)` (`rate_limiter.py:162-166`) KHÔNG gọi `RateLimiter.headers()`; chỉ middleware `conf.rate_limit` (`rate_limiter.apply` → `RateLimiter.headers()` `:82-92`) HOẶC nginx `limit_req` mới emit header. Thiếu `conf.rate_limit` ⇒ 429 trần body-only (status-line 429 ĐÚNG nhờ `RateLimitExceededError(ValidationError).http_status_code=429` @`exceptions.py:128-130`, nhưng KHÔNG header) — khớp §3.3 knob `rate_limit`, §6 T1, R5.
  - Doc check: `grep -n "allow_error_traceback" docs/mobile/08-security-compliance.md` trả item mới (evidence `response.py:60-65`).
- **Owner:** USER (System Setting + rate_limit/nginx) · [BA] (đặc tả + evidence).
- **Tag:** `[HARD-STOP USER]` cho System Setting + conf/nginx · `[AUTO]` cho phần đặc tả 08/ADR-004/10.
- **Dependencies:** **G1** (code lên cloud) · không phụ thuộc G2.

---

### G4 — Security gate verify (DoD EPIC-G)

**Mô tả.** Chạy gate tổng hợp xác nhận 4 điều kiện DoD sau khi G1–G3 xong: (a) no-traceback-
leak; (b) CORS no-wildcard (hoặc CORS OFF nếu native); (c) no token-leak (token KHÔNG xuất hiện
trong response body/log của endpoint khác); (d) rate-limit header phát ở 429. Đồng thời CI-guard
chặn placeholder host (`REPLACE-WITH-PUBLIC-HOST` yaml:107) + version skeleton
(`0.1.0-skeleton` yaml:89) lọt prod build. [BE] cung cấp test guard read-only; [QA] chạy smoke
curl trên public host.

- **Files (Create — [BE]/[QA], AUTO):** `assetcore/tests/guards/test_mobile_security_gate.py` — guard introspection-only: assert (1) `verify_oauth_client()` không leak traceback (re-use preflight); (2) yaml servers KHÔNG còn placeholder `REPLACE-WITH-PUBLIC-HOST` + version KHÔNG `*-skeleton` khi build prod-flagged; (3) không có `allow_cors:'*'` literal trong docset đặc tả prod; (4) `_err` body luôn có `http_status` (status-line-vs-body invariant — phản ánh §3.2). KHÔNG sửa `api/*.py`.
- **Files (Modify — [BA], AUTO):** `docs/mobile/08-security-compliance.md §5` (Acceptance bảo mật: thêm 4 lệnh gate) · `docs/mobile/10-deploy-ops.md §6.3` (post-verify smoke).
- **Acceptance:**
  - `bench --site <site> run-tests --app assetcore --module assetcore.tests.guards.test_mobile_security_gate` → exit 0.
  - `bench --site <site> run-tests --app assetcore --module assetcore.tests.guards.test_mobile_preflight` → exit 0 (verifier read-only + no-raise).
  - (a) no-traceback: `curl -s https://<host>/api/method/<auth-method>` (guest) body KHÔNG có `Traceback`.
  - (b) CORS: `grep -c '\*' <(python3 -c "import json;print(json.load(open('sites/<site>/site_config.json')).get('allow_cors'))")` == 0 (no-wildcard) HOẶC `allow_cors=None` (native OFF).
  - (c) no token-leak: response 200 envelope của `getAsset`/`getAssetScanInfo` KHÔNG chứa `qr_token` (đã `_strip_qr_token` — imm00.py:307; cross-ref EPIC-C getAsset stub).
  - (d) 429 header: vượt ngưỡng `@rate_limit` → `Retry-After` + `X-RateLimit-*` present **CHỈ KHI `conf.rate_limit`/nginx `limit_req` set** (HARD-STOP USER) — header do middleware `conf.rate_limit` (`RateLimiter.headers()` `rate_limiter.py:82-92`)/nginx `limit_req` phát, **KHÔNG do `@rate_limit` decorator một mình** (throw-path `:162-166` KHÔNG gọi `RateLimiter.headers()`). Thiếu `conf.rate_limit` ⇒ 429 body-only no-header (status-line 429 vẫn ĐÚNG). Xem §3.3 knob `rate_limit`, R5.
  - CI-guard: `grep -rn "REPLACE-WITH-PUBLIC-HOST\|0.1.0-skeleton" docs/mobile/openapi/assetcore-mobile.openapi.yaml` — nếu build gắn cờ prod thì gate FAIL khi còn placeholder.
- **Owner:** [QA] (chạy gate + smoke) · [BE] (test guard) · [BA] (đặc tả Acceptance 08/10).
- **Tag:** `[AUTO]` cho test guard + đặc tả + smoke command (introspection/local) · phần curl public-host cần G2 live nên **[HARD-STOP USER]** cho lần chạy THẬT trên cloud.
- **Dependencies:** **G1 + G2 + G3** (gate verify sau khi cả 3 xong) · cross-ref **EPIC-C** (`getAsset`/`getAssetScanInfo` strip token) · feed vào **EPIC-V** (codegen verify trên host đã hardened).

---

## 5. Data model / Schema

EPIC-G **KHÔNG thêm field / DocType / schema mới**. Toàn bộ là cấu hình runtime (site_config,
System Setting, nginx) + verify guard. DocType `OAuth Client` / `OAuth Bearer Token` /
device-token (EPIC-D) được tạo qua `bench migrate` ở **G1** nhưng định nghĩa schema thuộc
EPIC-B (OAuth Client) + EPIC-D (device-token) — KHÔNG khai trong EPIC-G. Knob cấu hình:

| Knob | Loại | Nơi đặt | Gate file:line |
|---|---|---|---|
| `host_name` | site_config | `sites/<site>/site_config.json` | `frappe/utils/data.py:1605/1611-1614/1631` |
| `allow_cors` | site_config | `sites/<site>/site_config.json` | `frappe/app.py:275/283-284` |
| `assetcore_qr_base_url` | site_config | `sites/<site>/site_config.json` | `06 §5.2` / `10 §3` |
| `rate_limit` | conf | `site_config.json` (key `rate_limit`) hoặc nginx `limit_req` | `frappe.rate_limiter` (LL-DEPLOY-04) |
| `allow_error_traceback` | **System Setting** | desk / `bench execute` (KHÔNG site_config) | `system_settings.json:262-265` · `frappe/utils/response.py:60-65` |

---

## 6. Security & Audit

- **RBAC / cap-SSoT:** EPIC-G KHÔNG thêm capability. `bench migrate` (G1) TỰ bust `ac_caps::*`
  (`after_migrate→_bust_capability_cache`); `bench restart` (G1) bắt buộc để worker `--preload`
  nạp `CAPABILITY_MAP` mới. SSoT quyền giữ 1 (ADR-001 b / ADR-004 §b — KHÔNG hệ quyền-2 cho mobile).
- **Token:** bearer/refresh thuộc EPIC-B; EPIC-G đảm bảo (c) no token-leak: `getAsset`/
  `getAssetScanInfo` `_strip_qr_token` (imm00.py:307); token KHÔNG ghi log/response chéo
  (kỷ luật repo-native = ADR-004 §c, T4 — ngoài kiểm soát repo `assetcore`, review Phase D).
- **CORS (T3):** CẤM wildcard `'*'` prod (ADR-004 §c, `app.py:275/283-284`). Native APK KHÔNG
  cần CORS ⇒ KHÔNG bật wildcard chỉ vì mobile. Verify ở G2/G4.
- **Traceback leak:** `allow_error_traceback` System-Setting=0 prod (G3) — chống lộ stack/SQL
  ở 401/403/429 raw. `_err()` (utils/response.py) KHÔNG bao giờ leak stack (body chỉ
  `code`+`http_status`+message VI) — đã đúng cho in-handler; gate G3 phủ nhánh dispatcher raw.
- **Rate-limit (T1):** `conf.rate_limit` / nginx `limit_req` cho OAuth2.* + `@rate_limit`
  decorator. Header `Retry-After`/`X-RateLimit-*` (G3/G4) do **middleware `conf.rate_limit`**
  (`rate_limiter.apply`→`RateLimiter.headers()` `:82-92`) HOẶC **nginx `limit_req`** phát —
  **KHÔNG do `@rate_limit` decorator một mình** (throw-path `frappe.throw(...,
  RateLimitExceededError)` `:162-166` KHÔNG gọi `RateLimiter.headers()`; status-line 429 vẫn
  ĐÚNG nhờ `RateLimitExceededError(ValidationError).http_status_code=429` @`exceptions.py:128-130`,
  chỉ HEADER mới conditional). ADR-004 §a (tầng ngoài, KHÔNG sửa core).
- **NĐ98 / Audit:** action-từ-mobile xuất hiện ở audit-chain với actor = KTV thật (bearer token
  mang đúng `frappe.session.user`); chuỗi audit hiện hữu, KHÔNG thêm field/đường audit cho
  mobile (ADR-004 §d / `08 §2`). Verify `verify_audit_chain` pass (`08 §4 verify`).
- **host_name / OIDC issuer (G4 (f), GUARD-9):** `host_name` set ⇒ `get_url()` + OIDC
  `openid_configuration issuer == public host`, **KHÔNG `http://miyano`** nội bộ (gate
  `frappe/utils/data.py:1605`; vắng ⇒ fallback `protocol + ...site` `:1631` = `http://miyano` ⇒ QR
  deep-link/issuer sai, flow-2 hỏng — §8 R4). Machine-check prose-invariant = GUARD-9
  (`TestSecGateHostNameIssuerDoc`, source-grounded @source + raw-text `08 §5.1(f)`/`10 §3`+§6.2+§6.3);
  live `get_url()`/issuer == public host = [HARD-STOP USER] G-U2/G-U6.
- **Status-line vs body invariant:** in-handler 4xx đến trên HTTP-200 + Error body (§3.2) —
  security-gate phải đọc `body.http_status` KHÔNG status-line cho in-handler; phân biệt
  dispatcher-403 (status-line THẬT) vs in-handler cap-403 (LL-DEPLOY-06).

---

## 7. Tham chiếu

- **Chương docset:** `docs/mobile/10-deploy-ops.md` (RUNBOOK §1–§6, KHÔNG nhân đôi) · `docs/mobile/08-security-compliance.md §1–§5` (threat-model T1–T7 + checklist + KPI) · `docs/mobile/02-deploy-feasibility.md` (khảo sát) · `docs/mobile/03-auth-oauth2.md` (OAuth/PKCE — EPIC-B) · `docs/mobile/06-push-fcm.md §5.2` (FCM creds/qr_base_url — EPIC-D) · `docs/mobile/13-be-completion-roadmap.md §5` (EPIC-G knob table — nguồn grounded §3.3).
- **ADR:** `docs/mobile/ADR-MOBILE-004.md` (mô hình bảo mật: rate-limit tầng ngoài · 1-SSoT-quyền · CORS list-origin · audit NĐ98; evidence `app.py:275/283-284`) · `docs/mobile/ADR-MOBILE-001.md` (response/error contract — EPIC-C nền).
- **Cross-EPIC (ID + task):** phụ thuộc **C** (contract codegen-ready: `getAsset`/`getAssetScanInfo` strip-token, response-200-oneOf) · phụ thuộc **B** (B2/B-preflight OAuth Client → G1 verify, G2 redirect/host) · mở đường **D** (device-token migrate ở G1, push trên public host) · feed **V** (V codegen verify + E2E runbook chạy trên host đã hardened G1–G4).
- **Lessons learned (skill `assetcore-deploy`):** **LL-DEPLOY-01** (preload staleness = 417 AttributeError, KHÔNG guest-403) · **LL-DEPLOY-03** (mobile-BE go-live 4 bước thứ tự: migrate→restart→site_config→preflight) · **LL-DEPLOY-04** (site_config: allow_cors list-origin no-wildcard + rate_limit header) · **LL-DEPLOY-05** (ngrok expose tạm cho APK test) · **LL-DEPLOY-06** (dispatcher-403 vs in-handler cap-403).

---

## 8. Rủi ro

| # | Rủi ro | Mức | Mitigation (kiểm-được) |
|---|---|---|---|
| R1 | Deploy G1 nhưng QUÊN `bench restart` → worker `--preload` cũ giữ code/cap-set cũ ⇒ endpoint mobile 417 AttributeError hoặc deny cap mới | Cao | G1 Acceptance bắt buộc hit authenticated endpoint xác nhận KHÔNG 417; LL-DEPLOY-01/03 ghi 4-bước. |
| R2 | Set `allow_cors='*'` "cho tiện" (web+native chung) → mọi origin credential-echo (T3) | Cao | G2/G4 gate `grep -c '\*'` == 0; ADR-004 §c cấm tường minh; native KHÔNG cần CORS. |
| R3 | Quên tắt `allow_error_traceback` (default ON) → prod leak stack/SQL ở 401/403/429 raw | Cao | G3 Acceptance `is_traceback_allowed → False`; G4 curl-guest body KHÔNG `Traceback`. |
| R4 | `host_name` vắng → `get_url()` = `http://miyano` nội bộ → QR deep-link/issuer sai, app KHÔNG mở được hồ sơ (flow-2) | Cao | G2 Acceptance `get_url()` == public HTTPS host (KHÔNG `http://miyano`) + `openid_configuration issuer == public host`. **GUARD-9 machine-check** (`TestSecGateHostNameIssuerDoc`): source-grounded @source `data.py:1605`/`:1631` + prose-invariant `08 §5.1(f)`/`10 §3`+§6.2+§6.3 (analog GUARD-5/7/8); live curl `get_url()`/issuer == public host = [HARD-STOP USER] G-U2/G-U6. |
| R5 | Thiếu `conf.rate_limit`/nginx `limit_req` → 429 không `Retry-After` (backoff câm, app retry-storm) | Trung | G3/G4 verify 429 có `Retry-After`; ADR-004 §a tầng ngoài. |
| R6 | Placeholder host `REPLACE-WITH-PUBLIC-HOST` (yaml:107) / version `*-skeleton` (yaml:89) lọt prod build → client codegen trỏ host sai | Trung | G4 CI-guard `grep` chặn placeholder khi build prod-flagged. |
| R7 | Deploy G1 trước khi EPIC-C contract khoá / EPIC-B client provisioned → migrate tạo doctype nhưng app native gọi contract chưa-ổn-định / không có client verify | Trung | Dependency gate: G1 chỉ chạy sau C đóng (codegen-ready) + B (preflight `ready=True`). |
| R8 | Token-leak qua log/response chéo (repo-native discipline) — ngoài kiểm soát repo `assetcore` | Trung | G4 (c) verify strip-token tại BE; phần native = review code Phase D (ADR-004 §c, T4). |

---

> **Tổng kết EPIC-G (kiểm-được):** HTTPS reachable ngoài (G2) · security gate PASS — no
> traceback leak (G3) · CORS no-wildcard / OFF native (G2) · no token-leak (G4c) · rate-limit
> header (G3/G4d). Mọi task HARD-STOP (commit/migrate/restart/site_config/System-Setting) =
> USER thực thi; phần `[AUTO]` (doc/checklist/test guard introspection-only) = factory tự đóng.
> Cross-ref: C (contract) · B (OAuth) · D (push) · V (codegen verify final).
