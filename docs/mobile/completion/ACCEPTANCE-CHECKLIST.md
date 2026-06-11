# Mobile BE Completion — ACCEPTANCE CHECKLIST (nghiệm thu 5 EPIC + GO-LIVE GATE)

> **Phạm vi:** bộ tài liệu "BE COMPLETION" cho app mobile (AssetCore = backend-for-mobile). Repo UI mobile native (Flutter/RN, project KHÁC) gọi API để chạy app.
> **DoD TỔNG (MVP field-tech, 6 flow E2E THẬT trên cloud):** (1) đăng nhập OAuth2+refresh · (2) quét QR → hồ sơ thiết bị · (3) báo hỏng (Incident IMM-12) · (4) yêu cầu WO PM/CM/Cal (IMM-08/09/11) · (5) "phiếu của tôi" · (6) push FCM.
> **KHÔNG gồm (post-MVP, ghi rõ):** offline-sync (ch.07), manager/duyệt, mở rộng đa-module.
> **3 quyết định AUTHORITATIVE (USER, 2026-06-11):** OAuth2+refresh (Frappe provider, Authorization Code + PKCE, scope↔capability SSoT) · field-tech MVP · native repo riêng. Lớp mobile = **BỌC + TÁI DÙNG** endpoint+capability có sẵn — KHÔNG viết lại logic.

**Cách đọc bảng:** mỗi dòng = 1 tiêu chí nghiệm thu kiểm-được. Cột `Lệnh / cách kiểm` chạy được THẬT. Cột `Tag`: `[AUTO]` = factory tự đóng được (doc/yaml/test/introspection) · `[HARD-STOP USER]` = cần cloud/migrate/site_config/FCM creds/toolchain. Cột `TT` (trạng thái) tick khi factory/user đóng: `[ ]` chưa · `[~]` đang dở · `[x]` xong+verify.

**Quy ước owner:** `[BA]` doc/yaml/spec · `[BE]` code api/services · `[QA]` test/audit · `[USER]` thao tác cloud/creds.

**Nguồn (grounded — file:line đã verify @working-tree 2026-06-11):** xem từng dòng. Các EPIC chi tiết task ở 5 file `<EPIC>-*.md` cùng thư mục (cross-ref bằng ID task vd C1, B2, D3).

---

## 0. Tổng quan dependency + thứ tự đóng gate

```
C (độc lập: doc/yaml/test — đóng NGAY)
   │
   ├──► B  (∥ thiết kế D)            ── cần USER: bench migrate (OAuth Client/device-token)
   │       │
   │       ▼
   └──►   G (go-live)               ── cần USER: cloud commit+migrate + site_config + HTTPS/nginx
           │
           ▼
          D (push FCM)              ── cần B + FCM creds (USER)
           │
           ▼
          V (codegen verify + handoff)   ── chốt cuối: gen client THẬT + 6-flow smoke + handoff
```

- **EPIC-C** không phụ thuộc gì → đóng được hoàn toàn bằng `[AUTO]` (trừ codegen THẬT cần toolchain → V).
- **EPIC-B/D/G/V** có ≥1 dòng `[HARD-STOP USER]` → KHÔNG thể tuyên bố DONE chỉ bằng factory.
- **Quy tắc gate:** một EPIC = PASS chỉ khi **mọi dòng bắt buộc của EPIC đó = `[x]`**. GO-LIVE = PASS chỉ khi **C+B+D+G+V đều PASS** và **GO-LIVE GATE tổng (§6)** xanh.

---

## 1. EPIC-C — API Contract (codegen-ready)

> Mục tiêu: YAML `docs/mobile/openapi/assetcore-mobile.openapi.yaml` codegen-clean (Dart/Kotlin), 0 dangling `$ref`, mọi path MVP typed. Tham chiếu task: `EPIC-C-api-contract.md` (C1..Cn).

| # | Tiêu chí nghiệm thu | Lệnh / cách kiểm (THẬT) | PASS khi | Owner | Tag | TT |
|---|---|---|---|---|---|---|
| C-A1 | Lint YAML + meta đông cứng (openapi 3.0.3) | `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` | `Ran 57 tests ... OK`; `test_mob_oas_01` xanh (safe_load OK, openapi==3.0.3) | BA | [AUTO] | [ ] |
| C-A2 | 0 dangling `$ref` toàn spec | cùng lệnh trên — `test_mob_oas_09_no_dangling_refs` | test xanh (walk STDLIB resolve mọi pointer) | BA | [AUTO] | [ ] |
| C-A3 | 4 STUB path còn lại RỜI STUB + typed | sửa `_STUB_PATHS` (test_mobile_oas.py:152-157) → 0 phần tử; `test_mob_oas_07` xanh | `_STUB_PATHS` rỗng; 4 path (`resolve_qr_token`/`get_asset_scan_info`/`get_asset`/`create_pm_work_order`) có response `data` typed | BA | [AUTO] | [ ] |
| C-A4 | P1 in-handler-error-on-HTTP-200 đóng theo ADR (response "200" oneOf[Created\|Error] + discriminator STRING) | grep yaml 3 create path; `test_mob_oas` guard discriminator | mỗi 200 oneOf 2 nhánh; `discriminator.propertyName` trỏ property **type=string** (KHÔNG boolean — xem 🔴 self-correction); mapping keys khớp enum VALUE | BA | [AUTO] | [ ] |
| C-A5 | list-element schema cho "phiếu của tôi" | grep `WorkOrderListItem`/`IncidentListItem` trong yaml; `test_mob_oas_14` (TestMobileListReadContract) | 2 list-item schema defined + referenced; 3 list path dùng | BA | [AUTO] | [ ] |
| C-A6 | userinfo/whoami OIDC wire vào spec | grep `userinfo`/`whoami` trong yaml; test surface | path khai báo (OIDC openid_profile) → app hiện tên+role KTV sau login | BA | [AUTO] | [ ] |
| C-A7 | requestBody oneOf json+form mọi RPC path | `test_mob_oas_13/16/17` (Body classes) + guard cho 4 STUB rời | mỗi RPC requestBody = oneOf `application/json` + `application/x-www-form-urlencoded` | BA | [AUTO] | [ ] |
| C-A8 | 0 `$ref`-with-sibling (codegen `--strict` clean) | `test_mob_oas_19` (TC-MOB-OAS-19) | KHÔNG `$ref` nào kèm sibling-key toàn spec | BA | [AUTO] | [ ] |
| C-A9 | 401/403 symmetry 12 path MVP | `test_mob_oas_12_error_status_class_401_403_split` | 12 path declare 401 == 12 declare 403 (mirror `_PATHS_REQUIRE_401`/`_403`) | BA | [AUTO] | [ ] |
| C-A10 | orphan-component ⊆ allow-list RESERVED | `test_mob_oas_10_orphan_components_within_reserved_allow_list` | orphan ⊆ `_RESERVED_ORPHANS`; KHÔNG stale | BA | [AUTO] | [ ] |
| **C-DoD** | **openapi-generator chạy sạch (Dart/Kotlin)** | `openapi-generator generate -i docs/mobile/openapi/assetcore-mobile.openapi.yaml -g dart -o /tmp/gen-dart` (+`-g kotlin`) | exit 0, 0 ERROR, 0 dangling `$ref`, mọi path MVP sinh method | QA | **[HARD-STOP USER]** (cần `java`/`npx` — môi trường thiếu) | [ ] |

**Baseline THẬT đã chạy 2026-06-11 (proxy cho C-DoD khi chưa có toolchain):**
`test_mobile_oas` = **Ran 57 OK** · `test_oas_generator` = **49 OK** · `test_oas_serve` = **9 OK** · `test_oas_signatures` = **11 OK** · `test_mobile_docset` = **5 OK** · `test_mobile_capability_map` = **6 OK**. STDLIB PyYAML introspection PASS làm proxy cho codegen THẬT (Dart/Kotlin) tới khi USER cấp toolchain → chuyển sang **EPIC-V**.

**Grounded source (4 STUB còn lại — verify @working-tree):**
- `resolve_qr_token` — `api/imm00.py:329` (`@rate_limit` :328 → 429), `rbac.require("asset.read")` :356, 404 `_ERR_ASSET_NOT_FOUND` :360, vendor-IDOR `assert_vendor_can_access` :363.
- `get_asset_scan_info` — `api/imm00.py:372` (`@rate_limit` :371 → 429); build qua `services/imm00.py::build_asset_scan_info` → trả `{name,asset_code,...,available_actions,pm_overdue,calibration_overdue}`.
- `get_asset` — `api/imm00.py:288`, 404 :291, vendor-IDOR :294, `return _ok(_strip_qr_token(doc))` :324 + enrich `pm_overdue`/`calibration_overdue` :318-319.
- `create_pm_work_order` — `api/imm08.py:91` (untyped `_form_dict` :17 + `rbac.require("pm.create")` :92) → `svc.create_adhoc_work_order` return `{name,status,checklist_items_count}` (`services/imm08.py:836-840`). **Lý do giữ STUB lâu nhất:** signature untyped `_form_dict` → cần định nghĩa typed requestBody (required `asset_ref`/`pm_schedule`/`due_date`).

**Grounded P1 (in-handler-error-on-HTTP-200, verify @source):** cơ chế `service nthrow(MSG.X)` (`notify.py`) → `ServiceError(http_status)` (`errors.py`) → `handle()` bắt → `_service_error_to_envelope` → `_err(...,http_status)` (`response.py`). Body chứa `code`+`http_status` NHƯNG status-line VẪN 200 (handle return dict; `hooks.py` no after_request). Bằng chứng/path:
- `imm12.report_incident` (`api/imm12.py:71`): guest `_err(401)` :92 = **dead-code over HTTP** (dispatcher-403 trip trước); cap-403 `_err(_MSG_FORBIDDEN,403)` :96 = in-handler HTTP-200+Error (DUAL-SHAPE 403); svc 422 clinical_impact / 404 asset∄; return `{name,status,severity}` (`services/imm12.py:410`).
- `imm09.create_repair_work_order`: `rbac.require('repair.create')` (`api/imm09.py:40`) → PermissionError HTTP-403 THẬT (SINGLE-shape); svc 404 / 409 HAS_OPEN_WO; return `{name,status,sla_target_hours}` (`services/imm09.py:435`).
- `imm11.create_calibration`: `rbac.require('calibration.create')` (`api/imm11.py:95`) → HTTP-403 THẬT (SINGLE-shape); svc 404 / 409 ASSET_BLOCKED (CAL-008); return `{name,status}` status init `Scheduled` (`services/imm11.py:332`).

> 🔴 **SELF-CORRECTION P1 (BACKLOG ưu tiên cao nhất — `assetcore-doc`):** discriminator `propertyName: success` = **boolean** → codegen-illegal (OAS discriminator propertyName PHẢI trỏ property **STRING**). Sửa: **(A, khuyến nghị)** thêm field STRING `result_type` enum[created,error] (const mỗi nhánh) làm propertyName, GIỮ `success` boolean cho FE logic; **(B)** BỎ discriminator + prose 'route theo body.success/http_status'. Áp 3 path + `04 §5c` + `ADR-MOBILE-001(f)`. **Test guard đi kèm:** `_assert_200_oneof_discriminator` assert `discriminator.propertyName` có `type=='string'` + mapping keys khớp enum VALUE → RED trước fix, GREEN sau (RED→GREEN gate). C-A4 KHÔNG được tick `[x]` tới khi guard này xanh.

---

## 2. EPIC-B — Auth & Provisioning (OAuth2 + refresh)

> Mục tiêu: runbook + helper idempotent tạo OAuth Client; refresh-token flow; device-token doctype (nếu cần cho FCM). Tham chiếu task: `EPIC-B-auth-provisioning.md` (B1..Bn). DoD: `preflight.verify_oauth_client()` ready=True; authorize→token→refresh→revoke + PKCE chạy trên cloud.

| # | Tiêu chí nghiệm thu | Lệnh / cách kiểm (THẬT) | PASS khi | Owner | Tag | TT |
|---|---|---|---|---|---|---|
| B-A1 | Preflight verifier logic xanh (7 điều kiện B-1) | `bench --site miyano run-tests --module assetcore.tests.test_mobile_preflight` | `Ran 9 tests ... OK` | BE/QA | [AUTO] | [ ] |
| B-A2 | OAuth token contract trong spec (200/400 + refresh) | `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` — `TestMobileOAuthToken` (TC-MOB-OAUTH-TOKEN-01..05) | 5 test xanh; get_token 200 keys khớp source; revoke 200 empty; authorize 302 | BA | [AUTO] | [ ] |
| B-A3 | Helper provisioning idempotent (tạo lại = no-op) | `bench --site miyano execute assetcore.api.mobile.<provision_fn>` 2 lần | lần 2 không tạo Client trùng (no `UniqueValidationError`); trả tên Client cũ | BE | [AUTO] (logic) | [ ] |
| B-A4 | Refresh-token flow + token lifetime documented + ví dụ refresh-on-401 | grep `03-auth-oauth2.md` / `04 §9` sequence refresh-on-401 | có 1 ví dụ: 401 → `getOAuthToken grant_type=refresh_token` → retry | BA | [AUTO] | [ ] |
| B-A5 | device-token doctype thiết kế (nếu cần FCM) | đọc `06-push-fcm.md §2.3` + doctype JSON (nếu tạo) | bearer-gated self-service, KHÔNG allow_guest; field-set khớp 06 | BA/BE | [AUTO] (thiết kế) | [ ] |
| B-U1 | `bench migrate` cloud → OAuth Client doctype + device-token live | USER: `bench --site <cloud> migrate` | migrate OK; doctype `OAuth Client`/device-token tồn tại trên cloud DB | USER | **[HARD-STOP USER]** | [ ] |
| B-U2 | Tạo OAuth Client THẬT (grant Authorization Code + scope `all openid` + redirect `assetcore://oauth/callback` + least-priv roles) | USER chạy provision helper trên cloud; rồi `verify_oauth_client()` | xem B-U3 | USER | **[HARD-STOP USER]** | [ ] |
| **B-DoD** (B-U3) | **`preflight.verify_oauth_client()` ready=True trên cloud** | `bench --site <cloud> execute assetcore.api.mobile.preflight.verify_oauth_client` | output `"ready": True`; 0 blocker (7 check pass — preflight.py:213) | USER/QA | **[HARD-STOP USER]** | [ ] |
| **B-DoD** (B-U4) | **authorize→token→refresh→revoke + PKCE chạy THẬT trên cloud** | curl/Postman: `/api/method/frappe.integrations.oauth2.authorize` (PKCE challenge) → `/.../get_token` → refresh → revoke | đủ 4 bước trả token hợp lệ; PKCE verifier bắt buộc; refresh trả access mới | USER/QA | **[HARD-STOP USER]** | [ ] |

**Grounded:** `verify_oauth_client()` (`api/mobile/preflight.py:147`) — admin-only, KHÔNG raise/KHÔNG leak traceback (preflight.py:23), trả `ready = all(c["pass"] for c in checks)` (preflight.py:213). 7 điều kiện B-1 = `client_count` + 6 cấp-record (`_evaluate_client`, preflight.py:25). **Phụ thuộc:** B-U1 cần USER `bench migrate` (HARD-STOP — xem Blocker #1). Cross-ref: EPIC-G G-U2 (site_config OAuth Client).

---

## 3. EPIC-D — Push FCM

> Mục tiêu: endpoint đăng ký FCM token/device; wire `notifications.py` (6-event) → kênh push; FCM creds site_config (user). Tham chiếu task: `EPIC-D-push-fcm.md` (D1..Dn). DoD: báo hỏng → KTV được giao nhận push; test.

| # | Tiêu chí nghiệm thu | Lệnh / cách kiểm (THẬT) | PASS khi | Owner | Tag | TT |
|---|---|---|---|---|---|---|
| D-A1 | Endpoint registerDeviceToken/unregisterDeviceToken giữ tên (frozen) | `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` — `test_mob_oas_06_device_token_names_frozen` | test xanh (2 tên đông cứng) | BA | [AUTO] | [ ] |
| D-A2 | device-token endpoint bearer-gated (KHÔNG allow_guest) + 401/403 | `test_mob_oas_12` (device-token ∈ 12 path declare 401==403) | device-token trong cả `_PATHS_REQUIRE_401` và `_403` | BA/BE | [AUTO] | [ ] |
| D-A3 | Wire `notifications.py` (6-event) → kênh push — side-effect THẬT | viết test `test_mobile_push.py`: gọi report_incident → assert có push-dispatch row cho KTV được giao (KHÔNG chỉ return) | test xanh; assert side-effect (Notification Log + push payload), anti-spam chạy 2 lần không nhân đôi (LL-TEST-18 / Phần 1 §Event-driven) | BE/QA | [AUTO] (logic + test) | [ ] |
| D-A4 | Audit trail NĐ98 cho đăng ký/thu hồi device-token | test assert IMM Audit Trail row sau register/unregister | mỗi mutate sinh audit record (CLAUDE.md §5 mọi nghiệp vụ có record) | BE/QA | [AUTO] | [ ] |
| D-U1 | FCM credentials nạp vào `site_config` cloud | USER set `fcm_*` keys trong `site_config.json` cloud | key tồn tại; service đọc được (KHÔNG hardcode) | USER | **[HARD-STOP USER]** | [ ] |
| **D-DoD** (D-U2) | **báo hỏng → KTV được giao NHẬN push THẬT trên thiết bị** | USER: device đăng ký token → tạo Incident gán KTV → quan sát push tới app | push notification hiện trên thiết bị KTV; payload đúng (asset + incident) | USER/QA | **[HARD-STOP USER]** | [ ] |

**Phụ thuộc:** D cần **B** (auth để device đăng ký token) + **FCM creds** (D-U1, USER). Cross-ref: B-A5 (device-token doctype), G (cloud reachable). **Anti-false-green (BẮT BUỘC):** D-A3 PHẢI assert side-effect THẬT (push-dispatch/Notification Log), KHÔNG chỉ "hàm return không lỗi" — pass-ngay-lần-đầu = nghi false-green (LL-TEST-21 / Phần 1 §Event-driven rule #4).

---

## 4. EPIC-G — Go-live & Hardening

> Mục tiêu: deploy code lên cloud (commit+migrate); site_config host_name/HTTPS/nginx; tắt allow_error_traceback prod; rate-limit headers. Tham chiếu task: `EPIC-G-golive-hardening.md` (G1..Gn). DoD: HTTPS reachable ngoài; security gate.

| # | Tiêu chí nghiệm thu | Lệnh / cách kiểm (THẬT) | PASS khi | Owner | Tag | TT |
|---|---|---|---|---|---|---|
| G-A1 | servers placeholder KHÔNG lọt prod build (CI-guard) | `bench --site miyano run-tests --module assetcore.tests.test_oas_d13_servers` | test xanh; guard chặn `REPLACE-WITH-PUBLIC-HOST` | BA | [AUTO] | [ ] |
| G-A2 | Hardening checklist prod tài liệu hoá (tắt traceback đúng cơ chế) | đọc `08-security-compliance.md`: gate = System Setting `allow_error_traceback` (KHÔNG `developer_mode`) | prose đúng: prod PHẢI tắt `allow_error_traceback` để 401/403/429 không leak traceback (response.py `is_traceback_allowed`) | BA | [AUTO] | [ ] |
| G-A3 | OAS serve endpoint healthy (spec phục vụ được) | `bench --site miyano run-tests --module assetcore.tests.test_oas_serve` | `Ran 9 tests ... OK` | QA | [AUTO] | [ ] |
| G-U1 | Deploy code lên cloud (commit + migrate) | USER: `git commit`/`push` + `bench --site <cloud> migrate` | working tree `??`/`M` đã commit; migrate OK trên cloud | USER | **[HARD-STOP USER]** | [ ] |
| G-U2 | site_config: host_name/HTTPS/nginx | USER set `host_name` + cert HTTPS + nginx `limit_req` | site phục vụ HTTPS; host_name đúng | USER | **[HARD-STOP USER]** | [ ] |
| G-U3 | CORS: **CHỈ nếu UI web** — native APK KHÔNG cần CORS | USER: nếu cần web → `allow_cors` = list-origin (KHÔNG wildcard `*`+credentials) | nếu set: no-wildcard; nếu native-only: `allow_cors` off (None) hợp lệ | USER | **[HARD-STOP USER]** | [ ] |
| G-U4 | Tắt `allow_error_traceback` prod | USER: System Setting OFF; verify `is_traceback_allowed()` False | gọi endpoint lỗi → body KHÔNG chứa traceback | USER/QA | **[HARD-STOP USER]** | [ ] |
| G-U5 | rate-limit headers (Retry-After / X-RateLimit-*) | USER set `conf.rate_limit` HOẶC nginx `limit_req` inject Retry-After | 429 trả backoff header (hiện `site_config` thiếu `rate_limit` → rate_limiter never instantiates) | USER | **[HARD-STOP USER]** | [ ] |
| **G-DoD** (G-U6) | **HTTPS reachable từ ngoài + security gate** | từ máy ngoài: `curl -sI https://<host>/api/method/frappe.ping` + audit | 200 reachable; **no traceback leak · CORS no-wildcard · no token-leak** | USER/QA | **[HARD-STOP USER]** | [ ] |

**Grounded:** gate traceback ĐÚNG = System Setting `allow_error_traceback` (default ON, `response.py`) — KHÔNG `developer_mode`. Rate-limit: `site_config` không có key `rate_limit` → `frappe.local.rate_limiter` never instantiates (`rate_limiter.py:82-92`) → `@rate_limit` (`imm00.py:328/371`) emit ZERO backoff header tới khi USER set `conf.rate_limit` hoặc nginx. **Phụ thuộc:** G cần B (auth provisioned). Cross-ref: Blocker #1 (reload gunicorn `--preload` + migrate), #3 (Phase B provisioning site_config).

---

## 5. EPIC-V — Codegen Verify + Handoff

> Mục tiêu: gen client Dart/Kotlin THẬT smoke cloud; E2E runbook field-tech; gói handoff repo mobile (yaml+auth+base-url). Tham chiếu task: `EPIC-V-codegen-verification.md` (V1..V4). DoD: 1 client gen-ra gọi được cả 6 flow trên cloud; runbook validated.

| # | Tiêu chí nghiệm thu | Lệnh / cách kiểm (THẬT) | PASS khi | Owner | Tag | TT |
|---|---|---|---|---|---|---|
| V-A1 | E2E runbook field-tech (6 flow) viết đủ, KHÔNG placeholder | đọc `EPIC-V-codegen-verification.md` runbook section (V3) | 6 flow có bước cụ thể + lệnh/endpoint thật; 0 TBD/TODO | BA | [AUTO] | [ ] |
| V-A2 | Gói handoff repo mobile (yaml + auth + base-url) liệt kê đủ | grep handoff manifest: yaml path + OAuth client config + base-url template | manifest đủ 3 artifact; trỏ `09-native-repo-guide.md` | BA | [AUTO] | [ ] |
| V-U1 | Gen client Dart THẬT từ spec | USER (sau cấp `java`/`npx`): `openapi-generator generate -g dart -i <yaml> -o <out>` | exit 0; client compile được | USER/QA | **[HARD-STOP USER]** (toolchain) | [ ] |
| V-U2 | Gen client Kotlin THẬT từ spec | `openapi-generator generate -g kotlin -i <yaml> -o <out>` | exit 0; client compile được | USER/QA | **[HARD-STOP USER]** (toolchain) | [ ] |
| V-U3 | Deser route-by-discriminator đúng (3 create path) | client gen → assert 200-oneOf route Created vs Error theo body discriminator STRING (KHÔNG status-line) | deser chọn đúng nhánh; KHÔNG anyMatch ambiguity | QA | **[HARD-STOP USER]** | [ ] |
| **V-DoD** (V-U4) | **1 client gen-ra gọi được cả 6 flow trên cloud** | USER: client → login OAuth → scan QR → report incident → create WO → "phiếu của tôi" → nhận push | đủ 6 flow trả 2xx/envelope success=true (hoặc Error đúng nhánh); push tới | USER/QA | **[HARD-STOP USER]** | [ ] |
| **V-DoD** (V-U5) | **Runbook validated (chạy theo runbook ra kết quả)** | USER chạy runbook V-A1 từ đầu trên cloud | mỗi bước reproduce được; 0 bước thiếu | USER/QA | **[HARD-STOP USER]** | [ ] |

**Phụ thuộc:** V = chốt cuối — cần **C+B+D+G** đã PASS. Cross-ref: C-DoD (codegen sạch là tiền đề), G-U6 (cloud reachable), D-U2 (push). Proxy hiện tại: STDLIB PyYAML introspection (`test_oas_*`) PASS thay codegen THẬT tới khi có toolchain.

---

## 6. 🚦 GO-LIVE GATE TỔNG (chốt MVP field-tech production-ready)

> **Quy tắc:** GO-LIVE = PASS chỉ khi **TẤT CẢ** dòng dưới = `[x]`. Một dòng `[ ]`/`[~]` → **BLOCK go-live**. QA KHÔNG tuyên bố pass khi chưa thấy output xanh THẬT.

| # | Gate | Lệnh / cách kiểm (THẬT) | PASS khi | Tag | TT |
|---|---|---|---|---|---|
| GO-1 | **Codegen sạch** (Dart+Kotlin, 0 dangling `$ref`) | `openapi-generator generate -g dart` + `-g kotlin` (V-U1/U2) | exit 0 cả 2; 0 ERROR | **[HARD-STOP USER]** | [ ] |
| GO-2 | **Test suite mobile/OAS xanh THẬT** | `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` (+`test_mobile_preflight`/`test_mobile_docset`/`test_mobile_capability_map`/`test_oas_generator`/`test_oas_serve`/`test_oas_signatures`) | tổng OK, 0 failure/error (baseline 2026-06-11: 57+9+5+6+49+9+11 = **146 OK**) | [AUTO] | [ ] |
| GO-3 | **preflight ready=True trên cloud** | `bench --site <cloud> execute assetcore.api.mobile.preflight.verify_oauth_client` (B-U3) | `"ready": True`, 0 blocker | **[HARD-STOP USER]** | [ ] |
| GO-4 | **6-flow smoke THẬT trên cloud** (1 client gen-ra) | V-U4 runbook | đủ 6 flow (login/scan/report/WO/phiếu/push) chạy được | **[HARD-STOP USER]** | [ ] |
| GO-5 | **Security: no traceback leak** | G-U4: endpoint lỗi → body | KHÔNG có traceback trong 401/403/429 (allow_error_traceback OFF) | **[HARD-STOP USER]** | [ ] |
| GO-6 | **Security: CORS no-wildcard** | G-U3: đọc `allow_cors` | không `*`+credentials (native APK: off hợp lệ) | **[HARD-STOP USER]** | [ ] |
| GO-7 | **Security: no token-leak** | audit response bodies + log: QR payload/token KHÔNG leak (vendor-IDOR 403, `_strip_qr_token`) | 0 token/qr_token trong response cho user ngoài scope | **[HARD-STOP USER]** | [ ] |
| GO-8 | **Audit trail NĐ98** | mỗi nghiệp vụ mobile (report/WO/cal/device-token) sinh IMM Audit Trail row | 0 mutate thiếu audit record | [AUTO]+[USER] | [ ] |
| GO-9 | **HTTPS reachable ngoài** | `curl -sI https://<host>/api/method/frappe.ping` từ máy ngoài (G-U6) | 200 OK qua HTTPS | **[HARD-STOP USER]** | [ ] |

**VERDICT GO-LIVE:** `[ ] GO` / `[ ] BLOCK` — chỉ tick GO khi GO-1..GO-9 đều `[x]`.

---

## 7. Tham chiếu

- **Chương docset BE-completion:** `00-overview.md` · `01-architecture.md` · `02-deploy-feasibility.md` · `03-auth-oauth2.md` · `04-api-contract.md` · `05-personas-mvp.md` · `06-push-fcm.md` · `07-offline-sync.md` (post-MVP) · `08-security-compliance.md` · `09-native-repo-guide.md` · `10-deploy-ops.md` · `11-phase-a-exit.md` · `12-phase-b-preflight.md`.
- **ADR:** `ADR-MOBILE-001.md` (OpenAPI contract, §f Self-Correction discriminator/form_dict) · `ADR-MOBILE-002/003/004.md`.
- **EPIC chi tiết task:** `EPIC-C-api-contract.md` · `EPIC-B-auth-provisioning.md` · `EPIC-D-push-fcm.md` · `EPIC-G-golive-hardening.md` · `EPIC-V-codegen-verification.md` (cùng thư mục `completion/`).
- **Spec + guard:** `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (15 path, openapi 3.0.3) · `assetcore/tests/test_mobile_oas.py` (`_STUB_PATHS` :152-157, `_MVP_BUSINESS_PATHS`, `_PATHS_REQUIRE_401/403`).
- **LL skill (assetcore-test):** LL-TEST-18 (hook-chain side-effect), LL-TEST-19 (permission gate mọi mutating endpoint), LL-TEST-21 (chống false-green — đọc output THẬT), LL-TEST-25 (reload gunicorn `--preload` trước Playwright/HTTP live), Phần 1 §Event-driven (assert side-effect THẬT).

---

## 8. Rủi ro

| Rủi ro | Tác động | Giảm thiểu |
|---|---|---|
| discriminator boolean (🔴 C-A4) lọt → codegen drop mapping | client deser sai nhánh Created/Error | Self-Correction A (`result_type` STRING) + guard test RED→GREEN; KHÔNG tick C-A4 tới khi guard xanh |
| Stale gunicorn `--preload` (Blocker #1) | sửa `api/*.py` không live HTTP → false-fail Playwright | USER reload TRƯỚC khi soi `api/*.py` mới (LL-TEST-25); reload KHÔNG bắt buộc cho round doc/yaml/test |
| Toolchain thiếu (`java`/`npx`) | C-DoD/V-U1..U5 không tự đóng được | STDLIB PyYAML introspection làm proxy; gate THẬT defer sang EPIC-V khi USER cấp |
| `bench migrate` cloud (B-U1) chưa chạy | OAuth Client/device-token doctype không tồn tại → preflight fail | HARD-STOP USER; B-U1 là tiền đề B-U3/B-DoD |
| FCM creds chưa nạp (D-U1) | push không gửi được → flow 6 fail | HARD-STOP USER site_config; D-A3 assert side-effect logic trước, D-DoD verify thiết bị sau |
| rate-limit headers thiếu (G-U5) | client không backoff đúng khi 429 | USER set `conf.rate_limit`/nginx `limit_req`; Phase-B-conditional |
| Test false-green side-effect (D-A3) | feature push "chết" nhưng test xanh | assert side-effect THẬT (Notification Log/push-dispatch), anti-spam 2-lần (Phần 1 §Event-driven) |
| CORS wildcard nếu thêm web sau | leo quyền cross-origin | G-U3 no-wildcard; native APK KHÔNG cần CORS (ADR-MOBILE-004) |

---

*Checklist này là CỔNG nghiệm thu — KHÔNG tuyên bố EPIC/GO-LIVE pass khi chưa thấy output xanh THẬT. Mọi dòng `[HARD-STOP USER]` thuộc orchestrator + user, KHÔNG tự đóng. Cập nhật cột `TT` mỗi khi factory/user đóng 1 dòng.*
