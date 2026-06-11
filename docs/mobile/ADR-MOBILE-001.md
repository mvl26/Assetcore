# ADR-MOBILE-001 — Kiến trúc backend cho ứng dụng di động native

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-001 |
| Phase | A — Kiến trúc & Feasibility |
| Ngày | 2026-06-09 |
| Tác giả | BA Lead + System Architect (mobile) |
| **Status** | **Accepted** |
| Bám quyết định | D-AUTH · D-MVP · D-STACK (`00-overview.md §2`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source **Frappe v15.107.2** (+ oauthlib 3.3.1, site `miyano`). Chi tiết khảo sát: [`02-deploy-feasibility.md`](./02-deploy-feasibility.md).

---

## Context

USER chốt initiative AssetCore Mobile (2026-06-09): cung cấp ứng dụng di động **native** cho kỹ thuật viên hiện trường, UI ở **repo riêng**, AssetCore (repo này) đóng vai **backend + hợp đồng API**. Ba quyết định nền đã chốt: **D-AUTH** (OAuth2 + refresh), **D-MVP** (field-tech), **D-STACK** (native).

Cần chốt 5 quyết định KIẾN TRÚC để Phase B/C không đi sai hướng (đặc biệt: KHÔNG tự viết OAuth, KHÔNG dựng hệ quyền thứ 2, KHÔNG fork nghiệp vụ). Đã khảo sát read-only tại source và xác nhận khả thi:

- Frappe có sẵn OAuth2 provider (Authorization Code + PKCE + refresh + revoke + OIDC discovery) — whitelisted, allow_guest cho flow endpoint.
- Bearer token → `frappe.set_user` ⇒ RBAC capability (`rbac.py`) áp dụng nguyên vẹn cho request mobile.
- CORS tắt mặc định; OAuth Client chưa tồn tại (đếm = 0); không có OpenAPI generator.

---

## Decision

### (a) WIRE provider OAuth2 có sẵn của Frappe — KHÔNG tự viết OAuth
Dùng `frappe.integrations.oauth2.*` làm provider. Phase B chỉ **CẤU HÌNH** (tạo 1 record `OAuth Client`: Authorization Code + PKCE + redirect native-scheme + allowed_roles). KHÔNG viết code OAuth.

- Evidence: `authorize` whitelisted allow_guest — `oauth2.py:74`; `get_token` (trả `access_token`+`refresh_token`) — `oauth2.py:123`; `revoke_token` (RFC 7009) — `oauth2.py:144`; PKCE verify S256 — `frappe/oauth.py:146-160`; refresh grant — `frappe/oauth.py:187`; OIDC discovery `id_token_signing_alg=["HS256"]` — `oauth2.py:180` (`openid_configuration`).
- Verified DB: `OAuth Client` count = **0**, `Social Login Key` = **0** (site `miyano`) ⇒ Phase B phải TẠO client; không cần Social Login Key cho vai trò provider.

### (b) Bearer → `set_user` ⇒ RBAC capability (`rbac.py`) là 1 SSoT — KHÔNG dựng hệ quyền thứ 2
Chuỗi auth mỗi request: `validate_auth` đọc header `Authorization` → `validate_oauth` verify bearer → `frappe.set_user(<token.user>)`. Sau đó `rbac.can(cap)` → `frappe.has_permission(DocType, ptype)` trên `frappe.session.user`. Vì vậy mọi capability gate web áp dụng y nguyên cho mobile. OAuth scope chỉ là gate THÔ (coarse on/off, default `all openid`) — KHÔNG là quyền thực.

- Evidence: `validate_oauth` def — `auth.py:633`; `frappe.set_user(...)` từ bearer — `auth.py:667`; `rbac.can` → `has_permission` — `services/shared/rbac.py:156`; `can()` deny-on-unknown-cap (stale-safe) — `rbac.py:155-168`.
- Hệ quả: KHÔNG dựng RBAC riêng cho mobile. Scope↔capability nếu cần chỉ map ở mức nhóm coarse; quyền chi tiết vẫn do DocPerm/capability theo user.

### (c) Tái dùng NGUYÊN endpoint nghiệp vụ — lớp mobile chỉ BỌC (wrap)
6 luồng D-MVP gọi endpoint nghiệp vụ đã có (imm00 QR/asset, imm12 báo hỏng, imm08/09/11 WO create, list "phiếu của tôi"), tất cả permission-aware. Nếu Phase C cần lớp riêng cho mobile thì đặt namespace `assetcore.api.mobile.v1.*` CHỈ để bọc/adapt response — gọi xuống service layer hiện có, KHÔNG nghiệp vụ mới, KHÔNG fork.

- Evidence: endpoint nghiệp vụ KHÔNG `allow_guest` ⇒ bắt buộc bearer trước (mapping đầy đủ `02-deploy-feasibility.md §6`); RPC qua `/api/method/<dotted>` — `frappe/api/__init__.py` (versioning `02-deploy-feasibility.md §4.3`); push engine 2-kênh tái dùng được — `services/notifications.py::_dispatch:366` (channel #3 chèn tại đây — `app.py` không liên quan; push thuộc Phase E).
- Hệ quả: KHÔNG sửa code nghiệp vụ ở Phase A. Mobile = OAuth + CORS + OpenAPI + push BỌC quanh service layer.

### (d) OpenAPI viết tay là HỢP ĐỒNG
Frappe KHÔNG auto-gen OpenAPI cho `/api/method`. Viết tay YAML (nguồn = type-hints/docstring sẵn có) làm hợp đồng BE↔repo-native để sinh API client + chống drift. Phase A = **skeleton**; Phase C bồi từng endpoint. Param dùng `str=""` (KHÔNG `str|None` — tránh pydantic 417, rule dự án).

- Evidence: không có generator/yaml trong repo (grep `openapi|swagger` rỗng — `02-deploy-feasibility.md §5`); skeleton tạo tại `openapi/assetcore-mobile.openapi.yaml`.

### (e) Native KHÔNG tái dùng session-cookie web
App native dùng bearer-over-HTTPS, KHÔNG cookie. Bearer auth không tạo cookie-session ⇒ CSRF check SKIP tự nhiên (native không cần CSRF token). Token lưu Keychain/Keystore; PKCE thay client_secret.

- Evidence: CSRF chỉ enforce khi có `frappe.session.data.csrf_token` (cookie-session) — `auth.py:83-98`; CORS gate `frappe.conf.allow_cors` (tắt mặc định = `None`) — `app.py:269`; bearer path tách hẳn cookie path — `auth.py:619-630`.

### (f) Pre-handler error (401/403/429) = PASSTHROUGH raw Frappe ở Phase A — KHÔNG normalize về Error envelope (A16)

Lỗi **trip TRƯỚC** `handle()` (`api_handler.py:33`) — 401 bearer-hết-hạn, 403 guest/no-token/thiếu-cap, 429 vượt `@rate_limit` — KHÔNG đi qua `_ok`/`_err` AssetCore ⇒ body THẬT = **raw Frappe** (`FrappeRawError` `{exc_type*, exception?, exc?, _server_messages?}`), HTTP status **LINE** THẬT. Quyết định Phase A: **giữ nguyên (passthrough) + khai schema `FrappeRawError` cho khớp body runtime** (codegen KHÔNG deser-fail), KHÔNG sửa Frappe core, KHÔNG dựng đường wrap. Status-class tách rõ: **401** = `AuthenticationError` (Authorization header CÓ nhưng bearer invalid + session=Guest); **403** = `PermissionError` (guest/no-token HOẶC thiếu permission/cap). Khác lỗi **IN-HANDLER** nghiệp vụ (Error envelope, HTTP-200 quirk — `04-api-contract.md §5`).

- Evidence: `AuthenticationError.http_status_code=401` `frappe/exceptions.py:26-27` (raise `auth.py:630`); `PermissionError.http_status_code=403` `:34-35` (raise `is_whitelisted` `frappe/__init__.py:876`); `TooManyRequestsError.http_status_code=429` `:80`; body-field source-char `frappe/utils/response.py` API V1 (`exc_type` `:46` LUÔN có; `exception` `:43-45` gated; `exc` `_make_logs_v1 :185`; `_server_messages` `:188` — 3 field optional). Hợp đồng + 3-shape phân biệt: [`04-api-contract.md §5 + §5b`](./04-api-contract.md).
- **OPTION Phase B (decision DEFERRED — KHÔNG impl ở A16):** normalize pre-handler raw → Error envelope thống nhất (qua `after_request`/error-hook hoặc lớp bọc `api/mobile/v1`) để client dùng **1 parser** cho mọi lỗi business. Đánh đổi: thêm đường wrap + che HTTP-line semantics. A16 chọn **passthrough + schema raw** (rủi ro thấp, KHÔNG đụng core); normalize chỉ mở nếu Phase B/C thấy chi phí 2-parser ở client native quá cao. Ghi `open_issues` cho USER.

- **🔧 SELF-CORRECTION (G-REQBODY) — 403 có HAI loại KHÁC NHAU, KHÔNG gộp 1:** câu trên ("403 = `PermissionError` guest/no-token **HOẶC** thiếu permission/cap") gộp nhập nhằng. Tách đúng @source: **(a) dispatcher-403** (guest/no-token) = `PermissionError` raw @HTTP-line **403** (pre-handler, `is_whitelisted` `__init__.py:876`) → `FrappeRawError`; **(b) in-handler cap-403** (bearer hợp lệ NHƯNG thiếu capability, vd `corrective.read-only` gọi `report_incident`) = `_err(_MSG_FORBIDDEN, 403)` qua `handle()` @HTTP-line **200** (quirk) + **Error envelope** `{code:'FORBIDDEN', http_status:403}` (`api/imm12.py:95-96`). Loại (b) là 403 PHỔ BIẾN NHẤT của field-tech (KHÔNG phải pre-handler raw). ⇒ path `report_incident` declare `403` = component `ReportIncidentForbidden` `oneOf [Error, FrappeRawError]` (BOTH shape — KHÁC `Forbidden` đơn của 11 path còn lại). **`in-handler cap-403 ≠ Forbidden response component`.** Client route theo HTTP status-line (200→Error, 403→FrappeRawError). Hợp đồng: [`04-api-contract.md §4 row5 / §5a / §5b`](./04-api-contract.md).

- **🔧 SELF-CORRECTION (G-REQBODY) — Frappe RPC đọc `form_dict`, KHÔNG body JSON mặc định:** requestBody của path RPC `/api/method` PHẢI khai content **oneOf `application/json` + `application/x-www-form-urlencoded`** (CÙNG schema). Frappe dispatcher đọc `frappe.form_dict` (query / form-encoded); body JSON chỉ vào `form_dict` khi client set `Content-Type: application/json` tường minh. Codegen JSON-only client (mặc định) KHÔNG set header → 4 field tới handler RỖNG → 'thiếu field' (sai-âm-thầm). Áp dụng cho `ReportIncidentBody` (§8.3) + mọi requestBody Phase-C kế. Hợp đồng + vd: [`04-api-contract.md §9 (b/d)`](./04-api-contract.md).

- **🔧 GENERALIZATION (C-REQBODY-CREATEREPAIR) — pattern business-create rời STUB + 1 CAVEAT 403-shape phụ-thuộc-handler:** template rời-STUB cho mọi business-create = **(requestBody oneOf json+form) + (200 typed grounded service return) + (404 asset∄) + (4xx business-block)**. Áp lần 2 cho `createRepairWorkOrder` (§8.5) sau `report_incident` (§8.3). **NHƯNG 2 ĐIỂM KHÔNG copy mù pattern report_incident:**
  - **(403-shape) phụ thuộc CÁCH handler check cap, KHÔNG cố định:** handler dùng `rbac.can + _err(403)` (vd `report_incident` `imm12.py:95-96`) → in-handler **HTTP-200 + Error** envelope ⇒ 403 **dual-shape** (`oneOf [Error, FrappeRawError]`, component riêng). Handler dùng `rbac.require(cap)` (vd `createRepairWorkOrder` `imm09.py:40`) → `frappe.throw(PermissionError)` @HTTP-line **403 THẬT** (raw `FrappeRawError`) ⇒ 403 **single-shape** = component `Forbidden` chuẩn. ⇒ BA PHẢI đọc handler TRƯỚC khi chọn component 403, KHÔNG mặc định dual-shape.
  - **(business-block code) phụ thuộc `http_status` của message-code @source, KHÔNG đoán 422:** `report_incident` block = BR-12-01 `IMM12_CLINICAL_IMPACT_REQUIRED` → `422` (BUSINESS_RULE). `createRepairWorkOrder` block = `IMM09_ASSET_HAS_OPEN_WO` → **`409`** (CONFLICT, `messages.py:667` + `_HTTP_TO_BUCKET[409]` `notify.py:42`). ⇒ BA PHẢI tra `messages.py` `http_status` thật, KHÔNG giả định "business-block = 422".
  - **🔧 SELF-CORRECTION (C-REQBODY-CREATECAL) — áp lần 3 cho `createCalibration` (§8.6), bộ-ba create HOÀN TẤT; re-check 2 caveat XÁC NHẬN delta vs đề mục:**
    - **(403-shape) = SINGLE-SHAPE `Forbidden`** — `create_calibration` dùng `rbac.require('calibration.create')` `imm11.py:95` (KHÔNG `rbac.can + _err`) → `frappe.throw(PermissionError)` @HTTP-line **403 THẬT** + `FrappeRawError`. ⇒ ĐỒNG shape dispatcher-403 = `Forbidden`, KHÔNG dual-shape như `report_incident`. (Đề mục ĐÚNG ở điểm này — xác nhận @handler.)
    - **(business-block code) = `409` CONFLICT, KHÔNG `422`** — `IMM11_ASSET_BLOCKED` (asset lifecycle ∈ `BLOCKED_FOR_WO` ∧ NOT `is_recalibration`, CAL-008 `imm11.py:1002`) map `http_status=409` (`messages.py:860` + `_HTTP_TO_BUCKET[409]=CONFLICT` `notify.py:42`). **Đề mục viết "422→Unprocessable422 + KHÔNG wire Conflict409 (calibration KHÔNG có open-WO gate)" — SAI @source.** Lập luận "không-open-WO-gate → không-409" nhầm *cơ-chế* (open-WO vs lifecycle-block) với *HTTP-status* (do message-code quyết định = 409). Calibration-409 KHÁC NGUYÊN-NHÂN createRepair-409 (open-WO) nhưng **CÙNG HTTP-409** ⇒ tái dùng `Conflict409`. ⇒ status-set = `[200,401,403,404,409]` (mirror createRepair), KHÔNG 422.
    - **(404 vs 409 — phân biệt asset-existence vs business-rule):** **404 = `IMM11_ASSET_NOT_FOUND`** (asset KHÔNG tồn tại `imm11.py:999`) vs **409 = `IMM11_ASSET_BLOCKED`** (asset TỒN TẠI nhưng lifecycle blocked ∧ không-recalibration `imm11.py:1002`). Client phân biệt theo `message_code`/`http_status` trong body (HTTP-line=200 quirk §5). Bài học chung: **business-block KHÔNG mặc-định-422 — tra `messages.py` http_status THẬT** (report=422 clinical-impact, repair=409 open-WO, calibration=409 lifecycle-block).
  - **🔧 SELF-CORRECTION (G-OAS-STATUSLINE) — in-handler business error 404/422/409 KHÔNG keyed dưới HTTP-code status-line; `200`-oneOf-discriminator là pattern ĐÚNG:** lần đầu (G-REQBODY/C-REQBODY-CREATEREPAIR/CREATECAL) wire 404/422/409 dưới **HTTP-code response-key** (`'404'`/`'422'`/`'409'`). **SAI hợp đồng máy-đọc** — các lỗi này arrive **HTTP status-line 200 + Error body** (in-handler qua `_err` `response.py:95-154` + `handle()` return dict `api_handler.py:48`; `hooks.py:405` KHÔNG có `after_request` ⇒ status-line KHÔNG BAO GIỜ set cho in-handler error). Codegen route-by-status-line KHÔNG bao giờ thấy HTTP 404/422/409 → response-key đó = **dead-deser branch**. **PATTERN ĐÚNG (route-by-body-discriminator):** `'200'` = `oneOf [<X>CreatedEnvelope, Error]` + `discriminator {propertyName: success, mapping: {'true': <created>, 'false': schemas/Error}}` — client route theo `body.success` (Created `success.enum:[true]` ≠ Error `success.enum:[false]`, phân biệt MÁY-ĐỌC) + `body.http_status`. In-handler 404/422/409 gom vào nhánh `Error` của 200-oneOf (demote response-key → doc-only note; `NotFound404`/`Unprocessable422`/`Conflict409` trở lại RESERVED §8.2, orphan 6→9). **Pre-handler 401/403 GIỮ status-line key** (dispatcher trip TRƯỚC `handle()` → HTTP status-line THẬT) ⇒ symmetry 401/403 (12==12) BẤT BIẾN. Bài học chung: **chỉ pre-handler error (401/403/429/500) mới mang HTTP status-line; in-handler business error (qua `handle()`/`_err`) LUÔN HTTP-200 → KHÔNG keyed dưới HTTP-code response-key.** Hợp đồng + bảng 3 path: [`04-api-contract.md §5c`](./04-api-contract.md).
  - **🔴🔧 SELF-CORRECTION R1→R4 (G-OAS-NO-BOOL-DISC, P1 codegen-illegal) — BỎ `discriminator` boolean, thay bằng closed-schema + disjoint required-set:** SELF-CORRECTION G-OAS-STATUSLINE ở trên (R1) chốt `'200'`-oneOf + `discriminator {propertyName: success}`. **`assetcore-ba` tự bắt ở R4: SAI codegen-legal.** OAS 3.x yêu cầu `discriminator.propertyName` trỏ property kiểu **STRING**; `success` là **BOOLEAN** ⇒ discriminator illegal: `openapi-generator` (Dart/Kotlin/Java) **drop** discriminator + fallback try-each-branch HOẶC sinh `switch(string)` so boolean → **deser-fail**; mapping keys `'true'`/`'false'` (string) KHÔNG khớp value boolean. **QUYẾT ĐỊNH BA = CÁCH B** (mirror fix-403 ở (f) — closed-schema disambiguation): **BỎ block `discriminator` ở CẢ create path** (report/repair/cal + R4 thêm `createPmWorkOrder`), GIỮ `oneOf [<X>CreatedEnvelope, Error]`, đặt **`additionalProperties:false` trên CẢ `<X>CreatedEnvelope` VÀ `Error`** ⇒ 2 nhánh máy-phân-biệt bằng **closed-schema + disjoint required-set** (`[success,data]` vs `[success,error,code,http_status]`, giao=`{success}`) + `success.enum` đối lập. **CÁCH A BỊ LOẠI** (thêm field STRING `result_type` enum[created,error] làm propertyName, giữ `success` boolean): `_ok`/`_err` (`response.py:79/95`) KHÔNG emit `result_type` ⇒ phải bịa wire-field BE không sản sinh → vi phạm gate BA "KHÔNG bịa field". **Đóng `Error` an toàn** (mọi notification-extension field đã khai property → không drop gì) và **MẠNH thêm 403-oneOf** ở (f): nay cả `Error` + `FrappeRawError` đều closed ⇒ `ReportIncidentForbidden` strictly mutual-exclusive theo shape (sample-proof TC-MOB-OAS-19d KHÔNG đổi). **Bài học chung (cập nhật (f)):** với `oneOf` 2 nhánh object KHÔNG có discriminator, **đóng CẢ HAI nhánh** (`additionalProperties:false`) + giữ required-set disjoint = cách máy-phân-biệt vững nhất; `discriminator` CHỈ hợp lệ khi propertyName là property **STRING** với `enum`/`const` per-branch — KHÔNG dùng cho boolean flag. Guard đổi: `TC-MOB-OAS-18b` assert KHÔNG `discriminator`; `18c` assert closed-schema + disjoint required-set; `19a` assert `Error` nay closed. Hợp đồng: [`04-api-contract.md §5c`](./04-api-contract.md).
  - **🔧 SELF-CORRECTION (G-OAS-403-DISAMBIG, P1 contract-correctness) — `oneOf [Error, FrappeRawError]` cần MÁY-PHÂN-BIỆT + gỡ `$ref`-with-sibling:** lần đầu (G-REQBODY) khai `ReportIncidentForbidden = oneOf [Error, FrappeRawError]` **KHÔNG có discriminator** và để `schemas/Error` + `schemas/FrappeRawError` đều open (`additionalProperties` mặc-định-true). **2 GAP chặn codegen:**
    - **(1) 2 nhánh oneOf KHÔNG máy-phân-biệt:** vì cả 2 type:object + Error open ⇒ body dispatcher-403 raw `{exc_type:PermissionError}` VẪN validate-pass `Error` (chỉ thiếu required `success/error/code/http_status` — nhưng Error open KHÔNG cấm thiếu khi không có discriminator gating). Dart/Kotlin generator sinh deser 'thử-từng-schema' = ambiguity, có thể deser NHẦM nhánh. **FIX:** đặt **`additionalProperties: false`** trên `schemas/FrappeRawError` (closed-shape) ⇒ `Error` envelope (mang key NGOÀI 4 raw-key) KHÔNG validate-pass FrappeRawError; raw KHÔNG validate-pass Error (thiếu required). 2 shape LOẠI TRỪ nhau → route đúng nhánh. **KHÔNG đóng `schemas/Error`** — notification-extension fields/context/message_code/action_hint/severity/title optional; disambiguation đến TỪ `FrappeRawError` closed-shape, KHÔNG từ đóng `Error`. **ROUTING CHÍNH VẪN theo HTTP status-line** (403-line=raw re-auth / 200-line=Error show-message); `additionalProperties:false` là tầng phân biệt PHỤ khi cùng status — client **KHÔNG `anyMatch` oneOf**.
    - **(2) `$ref`-with-sibling (OAS 3.0.3 codegen `--strict`):** 3 create path requestBody khai `$ref: requestBodies/*Body` ĐỒNG THỜI sibling `required: true`. OAS 3.0.3 **BỎ QUA** mọi sibling cạnh `$ref` → spectral / `openapi-generator --strict` emit warning, CI codegen strict-mode CÓ THỂ FAIL (vô hại runtime nhưng noise). **FIX:** gỡ `required: true` ở path-level (`requestBody` = `$ref`-ONLY); `required: true` GIỮ trong `components/requestBodies/*Body` (đã set nội bộ — KHÔNG mất ràng buộc). Guard `TC-MOB-OAS-19b` walk toàn spec assert **0 node** vừa có `$ref` vừa có sibling-key.
    - **Bài học chung:** với `oneOf` 2 nhánh object KHÔNG có discriminator, ít nhất 1 nhánh PHẢI `additionalProperties:false` (closed) để codegen route được theo shape; routing chính theo HTTP status-line khi 2 nhánh khác status. `$ref` thay-thế-toàn-bộ-node → KHÔNG bao giờ đặt sibling-key cạnh `$ref` (required/description… đặt trong node đích). Verify THẬT: `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` (TC-MOB-OAS-19a/b/c/d). Hợp đồng: [`04-api-contract.md §5a / §5b`](./04-api-contract.md).
  - **✅ ĐÃ ĐÓNG (R4 §8.7):** `createPmWorkOrder` (`imm08.py:91`) + 2 QR + `getAsset` ĐÃ rời STUB với typed `data` GROUNDED chữ-ký service THẬT (`QrResolveResult` `imm00.py:303` / `AssetScanInfo`+`available_actions[]`+overdue `imm00.py:567` / `AssetDetail` `imm00.py:288` / `CreatePmWorkOrderResponse {name,status,checklist_items_count}` `imm08.py:836`). `createPmWorkOrder` 200 = oneOf `[Created|Error]` closed-schema §5c (re-check 2 caveat: 403 single-shape `rbac.require('pm.create')` `imm08.py:92`; in-handler 422/404/409 `imm08.py:791/800/815`). Guard `TC-MOB-OAS-20`. Hợp đồng + vd: [`04-api-contract.md §8.7`](./04-api-contract.md).

### (h) Device-token (register/unregister) = `[ROADMAP]` BE-PENDING — GIỮ STUB, KHÔNG type `data` (R4 BA gate)

`mobile.v1.register_device_token` + `mobile.v1.unregister_device_token` (FCM push, MVP-6) **chưa có handler @source**: `api/mobile/` CHỈ có `__init__.py` + `preflight.py` — KHÔNG có hàm register/unregister, KHÔNG có doctype `AC Mobile Device Token`. (Verify R4: `grep -rn "def register_device_token" assetcore/` = 0 hit ngoài test/yaml.)

**Quyết định (R4 BA gate):** **KHÔNG type `data`** cho endpoint chưa có code — đây là ranh giới **R-CD-4 (cam-kết-Roadmap-không-cam-kết-hiện-trạng)** của BA: type-một-endpoint-không-tồn-tại = bịa hợp đồng (client native sinh model cho API không serve được → false-contract). GIỮ STUB (200→`responses/Stub` + 401/403 symmetry), summary đánh dấu `[ROADMAP Phase E]` + description ghi hợp đồng **DỰ KIẾN** khi BE implement (ack `{success, device_token_id?}` cho register / `{success}` cho unregister; user ÉP = `frappe.session.user`, row-level self-scope, audit NĐ98 §5.4 — `06-push-fcm.md §2.3/2.5`). Khi BE implement (Phase E): rời `_STUB_PATHS`, type response như 4 read/create R4, re-check 2 caveat (f).

- **Bài học chung:** BA spec phản ánh SỰ-THẬT-HIỆN-TẠI của source. Endpoint trong yaml mà handler chưa tồn tại = STUB + `[ROADMAP]` rõ ràng, KHÔNG type giả. "Type 6 STUB path" trong đề mục = **type 4 path CÓ handler** (§8.7) + **giữ-roadmap 2 path KHÔNG handler** (mục này) — KHÔNG đồng-nhất "có trong yaml" với "có code".

### (g) List-read envelope = 2 ENVELOPE PHÂN BIỆT theo rows-key THẬT @source — KHÔNG ép 1 key (C-LISTREAD)

3 list "phiếu của tôi" trả rows dưới **2 key khác nhau** ở runtime (verify @source, read-only): `imm08.list_pm_work_orders` (`imm08.py:569`) + `imm09.list_repair_work_orders` (`imm09.py:697`) trả `{"data": rows, "pagination": pg}` ⇒ sau `handle()`/`_ok` rows ở **`data.data[]`**; `imm12.list_incidents` (`imm12.py:764-770`) trả `{"items": rows, "pagination": pg}` ⇒ rows ở **`data.items[]`**. Orphan `PaginatedListEnvelope` cũ chỉ khai `data.{pagination, items}` ⇒ KHỚP imm12, **MÂU THUẪN** imm08/09.

**Quyết định (Phase C):** khai **2 envelope phân biệt** — `WorkOrderListEnvelope` (`data.data[]`) cho imm08/09 + `IncidentListEnvelope` (`data.items[]`) cho imm12; `Pagination` sub-schema DÙNG CHUNG. Lý do: OpenAPI là hợp đồng codegen máy đọc; khai 1 rows-key chung trong khi runtime trả key khác → model native deser **sai key** → rows về **rỗng** (lỗi câm khó debug). 2 envelope = nói ĐÚNG wire-shape THẬT cho repo native ⇒ codegen-consistency.

- **KHÔNG sửa service `.py` round này** (ràng buộc C-LISTREAD): hợp nhất rows-key về 1 key chung đụng service layer + test BE.
- **KNOWN-GAP → Phase-E normalize:** thống nhất `data` vs `items` về **1 rows-key chung** = việc Phase-E (chuẩn hoá envelope service `imm08|09|12.py` + test); tới khi đó contract phản ánh ĐÚNG di sản 2 service. Cùng Phase-E xét thống nhất scope `reported_by` vs `assigned_to` (A2 finding — hành vi, không đổi shape).
- Hợp đồng chi tiết + bảng rows-key: [`04-api-contract.md §6.1/§6.2 + §8.4`](./04-api-contract.md). Trạng thái path: [`11-phase-a-exit.md §1`](./11-phase-a-exit.md).

---

## Alternatives considered

| # | Phương án | Vì sao LOẠI |
|---|---|---|
| A1 | **Tự viết OAuth / JWT riêng cho mobile** | Frappe đã có OAuth2 provider chuẩn (Auth Code + PKCE + refresh + revoke + OIDC). Tự viết = tái phát minh + bề mặt tấn công + lệch khỏi `set_user`/RBAC. ⇒ chọn (a) wire. |
| A2 | **Dựng hệ quyền/scope-map thứ 2 cho mobile** | Vi phạm SSoT; bearer→set_user đã cho RBAC capability nguyên vẹn. Hai hệ quyền = drift + lỗ leo quyền. ⇒ chọn (b). |
| A3 | **Fork endpoint nghiệp vụ thành "mobile service"** | Trùng lặp logic + lệch validate/audit/SLA. ⇒ chọn (c) reuse + wrap-only. |
| A4 | **WebView / PWA-wrapper thay native** | Trái D-STACK; kéo theo CORS browser + UX kém + camera/offline yếu. ⇒ giữ native. |
| A5 | **Dùng session-cookie web cho app** | Cookie + CSRF không hợp mô hình native; token-based an toàn + revoke được. ⇒ chọn (e) bearer. |
| A6 | **OpenAPI auto-gen từ introspection ngay Phase A** | Frappe form_dict coercion → schema dễ lệch; tốn công. ⇒ viết tay skeleton trước (d), auto-gen để roadmap. |
| A7 | **Đổi access-token TTL ngay (knob)** | Không có site_config knob; default 3600s đã đủ cho "access ngắn + refresh". Đổi cần wrap `get_oauth_server` ⇒ backlog Phase F, không chặn MVP. *(Chi tiết vòng đời token: [`03-auth-oauth2.md §2`](./03-auth-oauth2.md).)* |
| A8 | **Normalize pre-handler 401/403/429 raw → Error envelope ngay Phase A** | Cần thêm đường wrap (`after_request`/error-hook) HOẶC lớp bọc — đụng nhiều bề mặt + che HTTP-line semantics; passthrough + khai schema `FrappeRawError` đã đủ cho codegen-khớp + rủi ro thấp. ⇒ chọn (f) passthrough; normalize = **option DEFERRED Phase B**. |
| A9 | **Khai 1 list-envelope chung (1 rows-key) cho cả 3 list** | imm08/09 trả rows ở `data.data[]`, imm12 ở `data.items[]` (KHÁC @source); ép 1 key chung → codegen native deser SAI key → rows rỗng (lỗi câm). Hợp nhất rows-key đúng cách cần sửa service `.py` — vượt ràng buộc C-LISTREAD. ⇒ chọn (g) **2 envelope phân biệt**; normalize 1-key = **Phase-E**. |

---

## Consequences

**Tích cực:**
- Auth khả thi bằng CẤU HÌNH (Phase B), không code OAuth → rủi ro thấp.
- Quyền 1 SSoT: mọi gate web áp dụng cho mobile, audit NĐ98 (SHA-256 chain) giữ đúng actor.
- Tái dùng nghiệp vụ ⇒ không drift validate/SLA/lifecycle; Phase A KHÔNG đụng code nghiệp vụ.
- OpenAPI hợp đồng ⇒ repo native sinh client + verify contract độc lập.
- Push tái dùng `_dispatch` (channel #3) ⇒ mọi event tự có push không sửa call-site.

**Đánh đổi / việc phải làm (carry sang Phase B+):**
- **Blocker triển khai (Phase B, HARD-STOP USER):** (1) chưa public HTTPS host (dev HTTP:80, `server_name` rỗng); (2) `allow_cors=None`; (3) `assetcore_qr_base_url=None` (QR trỏ host nội bộ); (4) `OAuth Client`=0 phải tạo. Đổi site_config/migrate/reload thuộc USER.
- **Scope coarse:** quyết định giữ scope `all openid` (quyền vẫn đúng nhờ RBAC) HAY map scope→capability-group — chốt ở Phase C.
- **Token TTL cố định 3600s** (không knob) — đổi cần wrap server, backlog Phase F.
- **Native KHÔNG dùng deep-link `/a/<token>`** (SPA-only, không server route — `hooks.py` website_route_rules chỉ `/assetcore/<path>`): app tự decode QR → parse token → gọi `resolve_qr_token`/`get_asset_scan_info`. Ghi rõ trong API client guide (Phase C).
- **Push/offline/sync** chỉ kiến trúc ở Phase A — device-token registry + idempotency + conflict policy ở Phase E.
- **Pre-handler error normalize (decision f):** Phase A passthrough raw + schema `FrappeRawError`; chuẩn hoá raw→Error envelope = **option DEFERRED Phase B** (chỉ mở nếu chi phí 2-parser ở client native quá cao). Ghi `open_issues`. Typed backoff header `Retry-After`/`X-RateLimit-*` cho 429 = Phase-B-conditional (cần `conf.rate_limit` HOẶC `nginx limit_req` — hiện `conf.rate_limit=null` ⇒ 0 header).
- **List-read rows-key divergence (decision g):** C-LISTREAD khai 2 envelope phân biệt (`WorkOrderListEnvelope` `data.data[]` / `IncidentListEnvelope` `data.items[]`) phản ánh ĐÚNG @source. **KNOWN-GAP Phase-E:** chuẩn-hoá về 1 rows-key chung (đụng service `imm08|09|12.py` + test BE) + thống nhất scope `reported_by` vs `assigned_to`. Ghi `open_issues`. Client native Phase C: dùng đúng envelope theo path (codegen sinh 2 model — KHÔNG share generic).

---

## Tham chiếu chéo

- Tổng quan + 3 quyết định + glossary: [`00-overview.md`](./00-overview.md)
- Kiến trúc (topology/auth-flow/versioning/push): [`01-architecture.md`](./01-architecture.md)
- Feasibility read-only tại source (gaps/blocker): [`02-deploy-feasibility.md`](./02-deploy-feasibility.md)
- **Auth deep-dive (đặc tả decision a/b/e + alternative A7 token-TTL):** [`03-auth-oauth2.md`](./03-auth-oauth2.md)
- **Mô hình bảo mật mobile (A7 — kế thừa decision b/c/e, threat T1–T7, NĐ98 audit-from-mobile):** [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md) · đặc tả: [`08-security-compliance.md`](./08-security-compliance.md)
- OpenAPI (auth-section bồi — hợp đồng): [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)
