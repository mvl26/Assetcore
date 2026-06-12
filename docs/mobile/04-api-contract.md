# 04 — Hợp đồng API (Response Envelope · ErrorCode · Pagination · Versioning)

> **Loại:** BA / System-Architect — Hợp đồng API mức ĐỊNH HƯỚNG cho mobile-BE (Phase A · A3).
> **Phạm vi A3:** chuẩn hoá envelope/error/pagination/versioning + param convention. KHÔNG impl, KHÔNG sửa code BE. KHÔNG bồi 6 path nghiệp vụ field-tech (để Phase C).
> **Bám 3 quyết định CHỐT:** D-AUTH (OAuth2+refresh) · D-MVP (field-tech) · D-STACK (native) — `00-overview.md §2`.
> **Verify:** mọi claim `file:line` đã đối chiếu source thật tại Frappe v15.107.2 (site `miyano`). KHÔNG bịa field.

---

## 1. Phạm vi & nguyên tắc hợp đồng

Tài liệu này là **hợp đồng dữ liệu** (data contract) giữa Frappe BE và repo native (D-STACK). Repo native dùng nó để (a) sinh API client (Flutter `openapi-generator` / RN), (b) viết lớp deserialize + xử lý lỗi đồng nhất, (c) tránh drift khi BE đổi shape.

**Nguyên tắc nền:**

1. **Tái dùng endpoint nghiệp vụ** qua RPC `/api/method/<dotted>` — KHÔNG sửa code nghiệp vụ ở Phase A (ADR-MOBILE-001 quyết định c).
2. **1 envelope chuẩn** cho mọi endpoint AssetCore: success `{success, data}` / error `{success, error, code, http_status, …}`. Verify nguồn `utils/response.py`.
3. **HTTP-200 wrapper quirk** (chương 5): `/api/method` trả HTTP 200 + envelope cho lỗi NGHIỆP VỤ; client native PHẢI đọc `body.success` + `body.code`/`body.http_status`, KHÔNG chỉ dựa HTTP status line.
4. **Capability = SSoT phân quyền** (`rbac.py`, 97 cap) — envelope KHÔNG lộ raw cap; lỗi quyền trả `code=FORBIDDEN` + message VI sạch.
5. **Audit trail (NĐ98)** áp dụng tự nhiên: bearer→`set_user`→mọi action sinh record đúng actor (`utils/lifecycle.py` SHA-256 chain). Hợp đồng API KHÔNG phá audit.

> Hợp đồng này KHÁC implementation: Phase A document SHAPE; Phase C bồi request/response schema thật cho 6 path nghiệp vụ.

---

## 2. Success envelope `{success, data}`

VERIFIED tại `assetcore/utils/response.py:79` (`_ok`) + `:92` (return shape).

```jsonc
{
  "success": true,
  "data": <payload>          // dict | list | scalar | null — tuỳ endpoint
}
```

| Field | Bắt buộc | Kiểu | Ý nghĩa |
|---|---|---|---|
| `success` | ✅ | `true` | Luôn `true` cho success envelope. |
| `data` | ✅ (có thể `null`) | any | Payload nghiệp vụ. Shape cụ thể từng endpoint = Phase C. |

**Notification-extension (optional, trong `data`):** caller có thể nhét `data.notify = {code, context}` để ép FE hiển thị message cụ thể (`response.py:85-90`; FE `useNotify.fromOk`). Native MVP có thể bỏ qua key `notify` nếu không render in-app message.

---

## 3. Error envelope `{success:false, error, code, http_status, …}`

VERIFIED tại `assetcore/utils/response.py:95` (`_err`) + `:133-153` (payload build).

```jsonc
{
  "success": false,
  "error": "<thông điệp tiếng Việt cho user>",   // đã render template với context
  "code": "<ErrorCode>",                          // enum bucket, xem chương 4
  "http_status": <int>,                           // HTTP status THẬT (xem chương 5)

  // ─── OPTIONAL ── chỉ xuất hiện khi có giá trị (giảm noise, response.py:139-153) ───
  "fields":       { "<field>": "<msg>", ... },    // form validation field-level
  "message_code": "MSG-XXX-001",                  // khoá lookup registry (utils/messages.py)
  "context":      { "<key>": <value>, ... },      // biến render template (i18n / live-edit)
  "action_hint":  "<gợi ý hành động kế tiếp>",
  "severity":     "error|warning|info|success|critical",
  "title":        "<tiêu đề ngắn cho dialog/toast>"
  // + bất kỳ key nào từ `extra` (vd existing_user khi 409) — response.py:152
}
```

| Field | Bắt buộc | Nguồn |
|---|---|---|
| `success` | ✅ (luôn `false`) | `response.py:134` |
| `error` | ✅ (string VI) | `response.py:135` |
| `code` | ✅ (ErrorCode enum) | `response.py:136` |
| `http_status` | ✅ (int) | `response.py:137` |
| `fields` | ⬜ optional | `response.py:139-140` (chỉ khi truyền) |
| `message_code` | ⬜ optional | `response.py:142-143` (notification framework) |
| `context` | ⬜ optional | `response.py:144-145` |
| `action_hint` | ⬜ optional | `response.py:146-147` |
| `severity` | ⬜ optional | `response.py:148-149` |
| `title` | ⬜ optional | `response.py:150-151` |

**Hợp đồng tối thiểu cho client native:** parse 4 field BẮT BUỘC (`success`/`error`/`code`/`http_status`). 6 field còn lại là **notification-extension** — client MVP có thể bỏ qua, nhưng KHÔNG được fail-deser khi chúng vắng mặt (đều optional).

> ⚠️ **Drift lịch sử (đã sửa ở doc này):** `01-architecture.md §5` + OpenAPI stub cũ mô tả error nested `{success:false, error:{code, message}}`. Đó là SAI so với source. Shape THẬT là **flat**: `error` là STRING, `code`/`http_status` ở TOP-LEVEL. OpenAPI A3 đã thay stub bằng shape thật; `01-architecture.md §5` nên đọc kèm chương này (hợp đồng chi tiết = ở đây).

---

## 4. ErrorCode catalog — 15 mã + HTTP map

SSoT = `assetcore/utils/response.py:37-57` (class `ErrorCode`) + `:60-76` (`_HTTP_FOR_CODE`). Re-export ở `services/shared/constants.py`; mirror FE `frontend/src/api/errors.ts`.

| # | `code` | HTTP | Ý nghĩa (VI) | Khi field-tech gặp |
|---|---|---|---|---|
| 1 | `VALIDATION` | **422** | Input không hợp lệ ở mức field. | Form báo hỏng/PM thiếu/sai field → `fields{}` chỉ field lỗi. |
| 2 | `VALIDATION_ERROR` | **400** | Lỗi format/parse input (mức request). | Body/JSON sai cấu trúc tổng thể. |
| 3 | `BUSINESS_RULE` | **422** | Vi phạm nghiệp vụ (workflow/state/SLA). | Tạo WO khi asset sai trạng thái; transition không hợp lệ. |
| 4 | `UNAUTHORIZED` | **401** | Bearer hết-hạn/invalid (Authorization header CÓ nhưng token sai). | Bearer hết hạn → app refresh (D-AUTH); refresh fail → re-auth. *(Pre-handler raw = `AuthenticationError`, body `FrappeRawError` §5b; in-handler `code=UNAUTHORIZED` hiếm.)* |
| 5 | `FORBIDDEN` | **403** | **HAI nhánh KHÁC NHAU** (G-REQBODY tách rõ): **(a) dispatcher-403** = guest/no-token → `PermissionError` raw @HTTP-line **403** (body `FrappeRawError`, §5b shape #3) → client **RE-AUTH**. **(b) in-handler cap-403** = đã-login-nhưng-thiếu-cap → `_err(_MSG_FORBIDDEN, 403)` qua `handle()` @HTTP-line **200** (quirk §5) + Error envelope `{code:'FORBIDDEN', http_status:403}` → client **SHOW-MESSAGE** (KHÔNG re-auth). **⚠️ Nhánh (b) CHỈ áp khi handler dùng `rbac.can + _err(403)` (vd `report_incident` `imm12.py:95-96`). Handler dùng `rbac.require(cap)` (vd `create_repair_work_order` `imm09.py:40`) → `frappe.throw(PermissionError)` @HTTP-line **403 THẬT** (raw `FrappeRawError`, exceptions.py:35) = ĐỒNG shape với (a) ⇒ 403 single-shape `Forbidden` component, KHÔNG dual-shape.** | (a) Guest gọi business endpoint → **403 status-line**. (b) persona `corrective.read-only` quét QR → 'Báo hỏng' (`report_incident`) → **HTTP-200 + Error{FORBIDDEN}** (`imm12.py:95-96`), KHÔNG lộ raw cap. Cùng persona bấm 'Yêu cầu sửa chữa' (`create_repair_work_order`) → **403 status-line + FrappeRawError** (`rbac.require` `imm09.py:40`); 'Yêu cầu hiệu chuẩn' (`create_calibration`) cũng **403 status-line** (`rbac.require('calibration.create')` `imm11.py:95` — single-shape, KHÁC report dual-shape). **⚠️ in-handler cap-403 ≠ `Forbidden` component CHỈ với `report_incident`** (xem §5/§5b/§8.5/§8.6). |
| 6 | `NOT_FOUND` | **404** | Tài nguyên không tồn tại. | Quét QR/`get_asset` với name không có. |
| 7 | `CONFLICT` | **409** | Trùng lặp / xung đột trạng thái. | Tạo bản ghi đụng unique; concurrent edit; tạo CM khi asset đã có WO mở (`createRepairWorkOrder`); tạo hiệu chuẩn khi asset lifecycle blocked ∧ không-recalibration (`createCalibration` CAL-008 — §8.6 delta c2). |
| 8 | `BAD_STATE` | **409** | Sai trạng thái workflow để thực hiện hành động. | Action không khả dụng cho lifecycle hiện tại của asset. |
| 9 | `DUPLICATE` | **409** | Riêng case trùng khoá (duplicate key). | Báo hỏng/serial/asset_code đã tồn tại. |
| 10 | `INVALID_PARAMS` | **400** | Params malformed (JSON parse, …). | `filters` truyền string KHÔNG phải JSON hợp lệ (chương 8). |
| 11 | `PAYLOAD_TOO_LARGE` | **413** | Payload vượt cap. | Batch in nhãn QR quá ngưỡng / upload ảnh quá lớn. |
| 12 | `RATE_LIMITED` | **429** | Quá ngưỡng request. | Quét/`resolve_qr_token` hoặc `rotate` > rate-limit/IP (chương 5). |
| 13 | `COMPLIANCE_BLOCKED` | **422** | IMM-16 gate: critical CAPA/finding mở chặn hành động. | Tạo WO khi còn Critical CAPA mở (NĐ98 / ISO 13485). |
| 14 | `INTERNAL` | **500** | Lỗi server không lường trước. | Hiếm — app hiển thị "lỗi hệ thống, thử lại". |
| 15 | `INTERNAL_ERROR` | **500** | Alias của `INTERNAL` (giữ legacy). | Như #14; client xử lý giống `INTERNAL`. |

> **Hợp đồng client:** nhánh UX theo `code` (coarse-grained), KHÔNG parse string `error`. `code` ổn định; `error` là text VI có thể đổi/i18n. `http_status` trong body = nguồn chân lý HTTP (xem chương 5), KHÔNG dựa HTTP line.
>
> Lưu ý: `_HTTP_TO_CODE` (`response.py:157-168`) là path NGƯỢC cho legacy `_err(msg, http_int)` — map 417→`BUSINESS_RULE`, 422→`BUSINESS_RULE`. Đây là backward-compat khi caller truyền HTTP int thay vì ErrorCode; client KHÔNG cần xử lý 417 (rule dự án tránh 417, chương 8).

---

## 5. Quirk HTTP-200 wrapper (BẮT BUỘC client native đọc kỹ)

**Quy tắc gốc:** endpoint nghiệp vụ qua `/api/method/<dotted>` được bọc bởi `handle()` (`utils/api_handler.py:33`) hoặc `_handle` legacy. Khi service raise `ServiceError`, handler bắt nó và trả **dict envelope** (`api_handler.py:48-51` → `_service_error_to_envelope` → `_err`). Frappe serialize dict đó với **HTTP 200** (đây là lỗi NGHIỆP VỤ, không phải lỗi transport).

⇒ **`http_status` THẬT nằm TRONG body** (`response.py:137`), KHÔNG ở HTTP status line.

```
Ví dụ: persona thiếu quyền gọi report_incident
HTTP/1.1 200 OK                      ← HTTP line = 200 (wrapper)
{
  "success": false,
  "error": "Bạn không có quyền thực hiện thao tác này.",
  "code": "FORBIDDEN",
  "http_status": 403                  ← status THẬT ở ĐÂY
}
```

> **HỢP ĐỒNG CLIENT NATIVE (non-negotiable):**
> Quyết định success/fail = `body.success`. Map lỗi theo `body.code` + `body.http_status`. **KHÔNG** chỉ kiểm tra HTTP status line — phần lớn lỗi nghiệp vụ trả HTTP 200.

### Ngoại lệ — trả HTTP status THẬT (trip TRƯỚC handler, KHÔNG qua envelope)

Các trường hợp này KHÔNG đi qua `handle()` → HTTP status line đúng + body có thể KHÔNG phải envelope chuẩn:

Các ngoại lệ này KHÔNG đi qua `_ok`/`_err` AssetCore ⇒ body THẬT = **raw Frappe** (`FrappeRawError`, §5b shape #3), KHÔNG phải Error envelope. **A16 đã TÁCH rõ status-class** (semantics theo `frappe/exceptions.py`):

| Tình huống | HTTP line | Body | Nguồn (`file:line`) |
|---|---|---|---|
| **401 — bearer hết-hạn/invalid:** Authorization header **CÓ** nhưng bearer hết hạn/sai ⇒ session resolve = `Guest` | **401** | Frappe `AuthenticationError` raw (`FrappeRawError`) | `AuthenticationError.http_status_code=401` `frappe/exceptions.py:26-27`; raise `auth.py:630` (header len==2 ∧ user∈{"","Guest"}). |
| **403 — guest/no-token HOẶC thiếu cap:** KHÔNG gửi bearer (guest), HOẶC method không-whitelisted-cho-guest / thiếu permission ở dispatcher | **403** | Frappe `PermissionError` raw (`FrappeRawError`) | `PermissionError.http_status_code=403` `frappe/exceptions.py:34-35`; raise `is_whitelisted` `frappe/__init__.py:876` (`throw(msg, PermissionError)`). |
| **429 — vượt `@rate_limit`** | **429** | Frappe `TooManyRequestsError` raw (`FrappeRawError`) | `TooManyRequestsError.http_status_code=429` `frappe/exceptions.py:80`; `@rate_limit` đặt NGOÀI handler, trip TRƯỚC (`imm00.py:311,354` — resolve/scan QR). **A13 wire `429`→`RateLimited429` vào ĐÚNG 2 path này** (§8.2). |
| Exception KHÔNG phải ServiceError | **500** | Frappe global handler (log + 500) | `api_handler.py:43-46` (non-ServiceError bubble lên — design intent) |

> ⚠️ **Phân biệt 401 vs 403 (A16 — KHÔNG còn nhập nhằng):**
> - **401** chỉ xảy ra khi client **CÓ gửi** `Authorization` header nhưng bearer **hết-hạn/invalid** (`auth.py:630` chỉ raise `AuthenticationError` khi `len(authorization_header)==2`). ⇒ app **refresh token**; refresh fail → re-auth.
> - **403** xảy ra khi **guest/no-token** (KHÔNG gửi bearer → endpoint nghiệp vụ không-allow_guest → `is_whitelisted` `throw(PermissionError)` `__init__.py:876`) HOẶC đã-login-nhưng-thiếu-capability. ⇒ app **không tự refresh** (không có token để refresh) → đăng nhập lại / báo thiếu quyền.
> - **Hệ quả:** guest gọi business endpoint trả **403** (KHÔNG 401) — đã LIVE-proven. OpenAPI A16 declare `403`→`Forbidden` lên TẤT CẢ 12 path MVP, ĐỐI XỨNG với 401.

> ⚠️ **Hệ quả cho client:** 4 ngoại lệ trên KHÔNG có Error envelope `{success, code, …}`. Body = `FrappeRawError` `{exc_type, exception?, exc?, _server_messages?}` (§5b shape #3). Client PHẢI dùng **HTTP status line** để phân nhánh (401→refresh, 403→re-auth/thiếu-quyền, 429→backoff, 500→retry/báo lỗi hệ thống) + đọc `exc_type` nếu cần phân loại (KHÔNG parse như Error envelope).
> 📌 **A16 — schema body THẬT (codegen-khớp):** OpenAPI `Unauthorized401`/`Forbidden`/`RateLimited429` nay `$ref` `schemas/FrappeRawError` (KHÔNG `schemas/Error`) ⇒ generated client sinh model KHỚP body runtime, **KHÔNG deser-fail** (sửa GAP A2 live-finding bên dưới). Error envelope CHỈ áp lỗi **IN-HANDLER** nghiệp vụ (HTTP-200 quirk trên).
> 📌 **A13 — coverage máy-đọc:** OpenAPI declare tường minh `401` (bearer hết hạn → refresh/re-auth — decision (e) [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)) + (A16) `403` lên **toàn bộ 12 path MVP**; `429` lên **ĐÚNG 2 path `@rate_limit`** (`imm00.resolve_qr_token`/`get_asset_scan_info`). 404/422 GIỮ ở **Phase C** (phụ thuộc requestBody/asset-lookup).
> 📌 **A2 live-finding (đã XỬ LÝ ở A16):** 401/403/429 trả raw Frappe traceback (KHÔNG Error envelope sạch). A16 KHÔNG normalize raw→envelope (chỉ GHI là option Phase B) mà **khai schema `FrappeRawError` cho khớp body raw** → generated client KHÔNG còn deser-fail. Chuẩn hoá raw→envelope (sau_request/error hook) = **decision deferred Phase B** (KHÔNG impl ở A16 — xem `ADR-MOBILE-001` Consequences).
> 📌 **Retry-After / X-RateLimit-* = Phase-B-conditional (P2 DEFER — KHÔNG guaranteed):** `RateLimited429` **KHÔNG** khai `Retry-After`/`X-RateLimit-*` là header guaranteed. Source-verified: `site_config` KHÔNG có key `rate_limit` ⇒ `frappe.local.rate_limiter` **KHÔNG** instantiate (`rate_limiter.py:82-92` chỉ chạy khi `conf.rate_limit` set) ⇒ `@rate_limit` decorator (`imm00.py:311/354`) emit **ZERO** backoff-header. Typed backoff headers cần set `conf.rate_limit` HOẶC `nginx limit_req` inject `Retry-After` (Phase B) → ghi `open_issues` cho USER. Client MVP fallback exponential-backoff khi gặp 429.

### 5a. HAI loại 403 KHÁC NHAU (G-REQBODY — dispatcher-403 vs in-handler cap-403)

> ⚠️ **403 KHÔNG đồng-shape.** Trước G-REQBODY, spec gộp cả hai vào 1 `Forbidden`→`FrappeRawError` ⇒ client branch theo HTTP status-line XỬ LÝ SAI nhánh (b). Tách rõ:

| Loại 403 | Khi nào | HTTP status-line | Body | Nguồn (`file:line`) | Client làm gì |
|---|---|---|---|---|---|
| **(a) dispatcher-403** | Guest/no-token gọi endpoint nghiệp vụ (KHÔNG allow_guest) | **403 THẬT** (trip TRƯỚC `handle()`) | `FrappeRawError` raw (`exc_type=PermissionError`, message HTML `<details>` 'Login to access') | `PermissionError.http_status_code=403` `frappe/exceptions.py:34-35`; raise `is_whitelisted` `frappe/__init__.py:876` | **RE-AUTH** (không có bearer để refresh) |
| **(b) in-handler cap-403** | Bearer **hợp lệ** nhưng thiếu capability (vd persona `corrective.read-only` gọi `report_incident`) | **200** (quirk wrapper §5 — qua `_err`) | **Error envelope** `{success:false, error:'Bạn không có quyền…', code:'FORBIDDEN', http_status:403}` | `imm12.py:95-96` `_err(_(_MSG_FORBIDDEN), 403)` → `handle()`/`_err` `response.py` | **SHOW-MESSAGE** (KHÔNG re-auth — token còn tốt) |

> **TÁI HIỆN nhánh (b):** persona `corrective.read-only` quét QR → bấm 'Báo hỏng' → BE trả **HTTP-200 + Error{code:FORBIDDEN}** (KHÔNG 403-status-line). Đây là 403 PHỔ BIẾN NHẤT của field-tech. Client KHÔNG được branch chỉ theo HTTP status-line cho 403 — phải đọc CẢ `body.success`+`body.code`.
>
> 📌 **`in-handler cap-403 ≠ Forbidden response component`:** OpenAPI component `Forbidden` (`$ref schemas/FrappeRawError`) chỉ model nhánh **(a)** — áp 11 path MVP còn lại. Path `report_incident` (gặp nhánh (b) phổ biến) declare 403 = component **`ReportIncidentForbidden`** = `oneOf [Error, FrappeRawError]` (BOTH shape) ⇒ codegen deser được CẢ HAI (route theo HTTP status-line: 200→Error, 403→FrappeRawError). Wire chỗ khác sang `Forbidden` đơn-shape ⇒ client cap-deny báo-hỏng deser-fail.
>
> 📌 **G-OAS-403-DISAMBIG (P1) — 2 nhánh oneOf MÁY-PHÂN-BIỆT, ROUTE theo status-line TRƯỚC:** `ReportIncidentForbidden.oneOf [Error, FrappeRawError]` KHÔNG có `discriminator` (2 type:object). Client native PHẢI route theo **HTTP STATUS-LINE THẬT** (non-negotiable): **403-line** ⇒ dispatcher raw → deser `FrappeRawError` → **RE-AUTH**; **200-line** ⇒ in-handler cap-403 → deser `Error` → **SHOW-MESSAGE**. **KHÔNG `anyMatch` oneOf** (thử-từng-schema = ambiguity). Tầng phân biệt PHỤ (khi 2 schema cùng status): `schemas/FrappeRawError` đặt **`additionalProperties: false`** (closed-shape) ⇒ `Error` envelope `{success,error,code,http_status,…}` (mang key NGOÀI 4 raw-key `exc_type/exception/exc/_server_messages`) **KHÔNG** validate-pass `FrappeRawError`; raw `{exc_type,…}` **KHÔNG** validate-pass `Error` (thiếu required `success/error/code/http_status`). 2 shape LOẠI TRỪ nhau → codegen Dart/Kotlin deser route ĐÚNG nhánh theo shape. **`schemas/Error` GIỮ OPEN** (KHÔNG `additionalProperties:false`) — notification-extension fields/context/message_code/action_hint/severity/title đều optional; disambiguation đến TỪ `FrappeRawError` closed-shape, KHÔNG từ đóng `Error`.
>
> 📌 **`_err(401)` dead-code:** `imm12.py:91-92` có nhánh `if frappe.session.user == "Guest": return _err(_MSG_UNAUTHENTICATED, 401)` — **KHÔNG bao giờ chạy over HTTP**: guest gọi `report_incident` (KHÔNG allow_guest) trip `is_whitelisted` `PermissionError` **403** ở dispatcher TRƯỚC khi handler thực thi (xem §9 vd d). `_err(401)` chỉ reachable khi gọi in-process (test/bench execute set user='Guest' thủ công). ⇒ vd Guest = **403** (KHÔNG 401).

---

## 5b. Hai LỚP error — AUTH-section vs BUSINESS-section (B1)

> **Hợp đồng B1 (Phase B):** mobile có **2 lớp error tách bạch** — client native PHẢI phân nhánh theo **đường gọi**, KHÔNG dùng 1 parser chung. Quyết định passthrough auth-section in nguyên tại [`03-auth-oauth2.md §2`](./03-auth-oauth2.md); section này là bảng đối chiếu cho repo native.

| Khía cạnh | **AUTH-section** (`get_token` / `revoke_token`) | **BUSINESS-section** (endpoint nghiệp vụ `/api/method/assetcore.api.*`) |
|---|---|---|
| Provider | **Frappe core / oauthlib** (SSoT — KHÔNG viết lại) | AssetCore service qua `handle()` (`api_handler.py:33`) |
| Body khi LỖI | **PASSTHROUGH OAuth body** — `OAuthError400` `{error, error_description?, error_uri?, description?, status_code?}` | **Error envelope** `{success:false, error, code, http_status, …}` (§3) |
| Key client phân nhánh | **`error`** (mã OAuth RFC 6749 §5.2 — vd `invalid_grant`) | **`code`** (ErrorCode bucket §4) + **`http_status`** trong body |
| HTTP line khi lỗi | **THẬT** (400 grant-fail; oauth2.py:132-135) | **200** cho lỗi IN-HANDLER (quirk wrapper §5); **THẬT** 401/403/429/500 cho lỗi PRE-HANDLER (trip TRƯỚC `handle()`) |
| Envelope wrap? | **KHÔNG** (Frappe core SSoT, tái dùng provider) | **CÓ** cho in-handler (`_ok`/`_err` — `response.py`); **KHÔNG** cho pre-handler (raw Frappe) |
| Component OpenAPI | **`OAuthError400`** (200 = OAuthlib token-body) — wire CHỈ `getOAuthToken` | in-handler = `Error` envelope; pre-handler 401/403/429 = **`FrappeRawError`** (`Unauthorized401`/`Forbidden`/`RateLimited429` $ref `schemas/FrappeRawError`) |
| Pre-handler raw (401/403/429) | — | **`FrappeRawError`** raw `{exc_type*, exception?, exc?, _server_messages?}` — **A16 đã khai schema THẬT** + repoint 3 response (KHÔNG còn trỏ `Error`). Source-char @`frappe/utils/response.py` V1. |

> **3 shape error PHÂN BIỆT RÕ (KHÔNG trộn) — client native dùng 3 parser theo đường gọi:**
> 1. **`OAuthError400`** (AUTH-section, `get_token`) — passthrough OAuthlib `{error, …}`. SOURCE-CHARACTERIZED: oauthlib twotuples (`errors.py:80-88`) ∪ `generate_json_error_response` (`oauth.py:567-573`); set tại `oauth2.py:132-135`. `error` = required. HTTP line THẬT.
> 2. **`Error` envelope** (BUSINESS-section, lỗi nghiệp vụ **IN-HANDLER** qua `handle()`) — `{success:false, error, code, http_status, …}` (§3). HTTP-line **200** (quirk). **CHỈ** shape này dùng Error envelope.
> 3. **`FrappeRawError`** (BUSINESS-section, **PRE-HANDLER** 401/403/429 trip TRƯỚC `handle()`) — raw Frappe `{exc_type*, exception?, exc?, _server_messages?}`, **`additionalProperties: false`** (closed-shape — G-OAS-403-DISAMBIG, cho phép disambiguation oneOf 403 §5a). **A16 (đã làm, KHÔNG còn backlog):** tách rõ 401 (bearer hết-hạn/invalid — `AuthenticationError` `frappe/exceptions.py:26-27`) vs 403 (guest/no-token/thiếu-cap — `PermissionError` `:34-35`) + khai schema raw cho khớp body thật + repoint `Unauthorized401`/`Forbidden`/`RateLimited429` `$ref` từ `schemas/Error` → `schemas/FrappeRawError`. SOURCE-CHARACTERIZED @`frappe/utils/response.py` API V1: `exc_type`=`exc_type.__name__` LUÔN có (`:46`, required); `exception` dòng-cuối-traceback gated `is_traceback_allowed` (`:43-45`, optional); `exc` JSON-encoded-list gated traceback (`_make_logs_v1 :185`, optional); `_server_messages` JSON-encoded-list gated `message_log` (`:188`, optional). 500 = Frappe global handler (ngoài 3 shape — client retry/báo lỗi hệ thống).

> 📌 **G-REQBODY — 403 báo hỏng = DUAL-SHAPE (shape #2 ∪ #3):** path `report_incident` gặp **CẢ HAI** loại 403 (§5a): **(a)** dispatcher-403 (guest) = `FrappeRawError` @HTTP-403 (shape #3) ∧ **(b)** in-handler cap-403 (thiếu cap) = `Error` envelope @HTTP-200 (shape #2). ⇒ OpenAPI component `ReportIncidentForbidden` = `oneOf [Error, FrappeRawError]` (KHÁC `Forbidden` đơn-shape của 11 path còn lại). Client route theo HTTP status-line: **200** ⇒ deser `Error`+đọc `body.code`; **403** ⇒ deser `FrappeRawError`+đọc status-line. **`in-handler cap-403 ≠ Forbidden response component`** — KHÔNG dùng parser `Forbidden`/`FrappeRawError` đơn cho 403 của `report_incident`.

> 📌 **G-OAS-403-DISAMBIG (P1) — `additionalProperties:false` = cơ chế disambiguation máy-đọc:** `schemas/FrappeRawError` đặt `additionalProperties: false` (sau `required:[exc_type]`) ⇒ 2 nhánh `ReportIncidentForbidden.oneOf` LOẠI TRỪ nhau theo shape (chi tiết §5a note G-OAS-403-DISAMBIG). `schemas/Error` GIỮ open. Đây là tầng phân biệt PHỤ — routing chính VẪN theo **HTTP status-line** (403-line=raw re-auth / 200-line=Error show-message), client **KHÔNG `anyMatch` oneOf**.

> 📌 **G-OAS-403-DISAMBIG (P1) — `$ref`-with-sibling (OAS 3.0.3 codegen `--strict`):** OAS 3.0.3 **BỎ QUA** mọi sibling-key cạnh `$ref` (`$ref` thay-thế-toàn-bộ-node) ⇒ spectral / `openapi-generator --strict` emit warning, CI codegen strict-mode CÓ THỂ FAIL. 3 create path requestBody (`reportIncident`/`createRepairWorkOrder`/`createCalibration`) trước có sibling `required: true` cạnh `$ref` → nay **GỠ ở path-level** (`requestBody: { $ref: '#/components/requestBodies/*Body' }` — `$ref`-ONLY). `required: true` GIỮ NGUYÊN trong `components/requestBodies/*Body` (đã set nội bộ component — KHÔNG mất ràng buộc body-bắt-buộc). Guard `TC-MOB-OAS-19b` walk toàn spec assert **0 node** vừa có `$ref` vừa có sibling-key (chống tái phát).

> 📌 **`FrappeRawError` 4 field đều STRING** (KHÔNG array): `exc`/`_server_messages` là `json.dumps(list)` (string-of-list), client cần `JSON.parse` 2 lớp nếu muốn đọc. Client MVP CHỈ cần `exc_type` (LUÔN có) + HTTP status line; 3 field còn lại vắng ở prod no-traceback ⇒ KHÔNG được fail-deser khi vắng (đều optional).

> **Hợp đồng client native (non-negotiable):**
> - Gọi `get_token`/`revoke_token` → đọc **HTTP status line** + key **`error`** (OAuth chuẩn). `invalid_grant` ⇒ **re-auth** (chi tiết failure-modes: [`03-auth-oauth2.md §2.3.1`](./03-auth-oauth2.md)).
> - Gọi endpoint nghiệp vụ → đọc `body.success` + `body.code` + `body.http_status` (§5). KHÔNG áp parser auth lên business path & ngược lại.

**Đường error `get_token` (B1 — đã wire OpenAPI):**

```jsonc
// POST get_token grant_type=refresh_token (refresh đã hết hạn/revoked)
// HTTP/1.1 400 Bad Request          ← HTTP line THẬT (oauth2.py:134)
{
  "error": "invalid_grant"           // ← key OAuth chuẩn (oauthlib errors.py:301)
  // "error_description": "..."       // optional (oauthlib twotuples errors.py:82-83)
}
```

---

## 5c. Status-line-correctness cho create path + read path — route-by-body + closed-schema (G-OAS-NO-BOOL-DISC)

> ⚠️ **P1 contract-correctness.** In-handler business error của create path (`reportIncident` 404/422; `createRepairWorkOrder`/`createCalibration`/`createPmWorkOrder` 404/409/422) **KHÔNG arrive trên HTTP status-line** — chúng đi qua `_err` (`response.py:95-154`) + `handle()` return **dict** (`api_handler.py:48`) → Frappe serialize **HTTP-200** (`hooks.py:405` KHÔNG có `after_request` hook đổi status-line ⇒ status-line **KHÔNG BAO GIỜ** set cho in-handler error). Codegen route-by-status-line **không bao giờ** thấy HTTP 404/422/409 → response-key đó = **dead-deser branch**.

> 🔵 **C6 — read-path P1 closure (2026-06-11): cùng quirk áp cho 3 GET read.** `resolveQrToken`/`getAssetScanInfo`/`getAsset` cũng phát in-handler error qua `_err` → **HTTP-200 + Error body**: **404** (`_err(…,404)`) + **vendor-IDOR-403** (`assert_vendor_can_access` raise `ServiceError(FORBIDDEN)` **caught** → `_err(e.message, e.code)`, KHÔNG `frappe.throw`). Vì 3 read KHÔNG có `requestBody`, P1 read-path TRƯỚC ĐÂY bị bỏ sót (200 = single `$ref <ReadEnvelope>`, KHÔNG nhánh Error → in-handler 404/403 dead-deser cho native client). C6 áp **CÙNG quyết-định Decision-B** dưới đây cho read: 200 = `oneOf [<ReadEnvelope>, Error]` closed-schema KHÔNG discriminator. Chỉ **dispatcher-403** (guest/no-token; `resolve`/`scan-info` có thêm `rbac.require('asset.read')`) GIỮ status-line key `403`.

> 🔴 **SELF-CORRECTION R1 (factory-run3-apidocs → R4) — BỎ boolean-discriminator illegal.** Vòng R1 đặt `'200'` = oneOf [Created|Error] + `discriminator {propertyName: success}`. **SAI codegen-legal:** OAS 3.x yêu cầu `discriminator.propertyName` trỏ property kiểu **STRING**; `success` là **BOOLEAN** → `openapi-generator` (Dart/Kotlin/Java) **drop** discriminator + fallback try-each-branch HOẶC sinh `switch(string)` so boolean → **deser-fail**. mapping keys `'true'`/`'false'` (string) KHÔNG khớp value boolean. **QUYẾT ĐỊNH BA = CÁCH B** (mirror R2 fix-403 `FrappeRawError` closed): **BỎ block `discriminator`**, GIỮ `oneOf`, đặt `additionalProperties:false` trên CẢ `<X>CreatedEnvelope` + `Error` → 2 nhánh máy-phân-biệt bằng **closed-schema + disjoint required-set**. *(Cách A — thêm field STRING `result_type` enum[created,error] làm propertyName — BỊ LOẠI: `_ok`/`_err` KHÔNG emit `result_type` ⇒ phải bịa wire-field BE không sản sinh → vi phạm gate "KHÔNG bịa field".)*

**Quyết định (route-by-body + closed-schema, KHÔNG discriminator, KHÔNG route-by-status-line):**
- `'200'` của create path = **`oneOf [<X>CreatedEnvelope, Error]`** — **KHÔNG `discriminator`**. 2 nhánh máy-phân-biệt bằng:
  - **closed-schema**: `additionalProperties:false` trên CẢ `<X>CreatedEnvelope` VÀ `Error` (mọi notification-extension field của `Error` đã khai property → đóng không drop gì);
  - **disjoint required-set**: Created `required:[success,data]` vs Error `required:[success,error,code,http_status]` (giao = `{success}`, phần còn lại loại trừ);
  - **`success` enum đối lập** (`[true]` vs `[false]`) làm tầng disambiguation theo VALUE.
- Codegen route theo **`body.success`** (true → `…CreatedEnvelope`; false → `Error` → đọc tiếp `body.http_status`, 404/422/409 nằm TRONG body §5).
- In-handler 404/422/409 **DEMOTE thành doc-only note** (KHÔNG còn status-line response-key) — gom vào nhánh `Error` của `200`-oneOf. `responses/NotFound404`/`Unprocessable422`/`Conflict409` = **RESERVED** (§8.2, forward-reserve doc-intent).
- **Pre-handler 401/403 GIỮ status-line key** — dispatcher (`is_whitelisted`/auth) trip **TRƯỚC** `handle()` ⇒ HTTP status-line **THẬT** (§5 ngoại lệ). `report` `'403'` = `ReportIncidentForbidden` dual-shape (§5a/§5b); `repair`/`cal`/`createPm` `'403'` = `Forbidden` single-shape (`rbac.require` dispatcher-403). ⇒ **symmetry 401/403 (12==12) BẤT BIẾN.**

| Path | `'200'` oneOf (success:true) | `'200'` oneOf (success:false) | status-set | In-handler error (gom nhánh Error) |
|---|---|---|---|---|
| `reportIncident` | `ReportIncidentCreatedEnvelope` `{name,status,severity}` (`imm12.py:410`) | `Error` | `[200,401,403]` | 404 asset∄ `imm12.py:361` · 422 BR-12-01 `imm12.py:359` · cap-403 `imm12.py:96` |
| `createRepairWorkOrder` | `CreateRepairWorkOrderCreatedEnvelope` `{name,status,sla_target_hours}` (`imm09.py:786`) | `Error` | `[200,401,403]` | 404 asset∄ `imm09.py:746` · 409 HAS_OPEN_WO `imm09.py:753` (`messages.py:667`) |
| `createCalibration` | `CreateCalibrationCreatedEnvelope` `{name,status}` (`imm11.py:1015`) | `Error` | `[200,401,403]` | 404 asset∄ `imm11.py:999` · 409 ASSET_BLOCKED CAL-008 `imm11.py:1002` (`messages.py:860`) |
| `createPmWorkOrder` | `CreatePmWorkOrderCreatedEnvelope` `{name,status,checklist_items_count}` (`imm08.py:836-840`) | `Error` | `[200,401,403]` | 422 thiếu field/schedule-mismatch `imm08.py:791,802` · 404 PM Schedule∄ `imm08.py:800` · 409 asset BAD_STATE `imm08.py:815` |

**🔵 C6 — read-path (3 GET read áp CÙNG bảng route-by-body + closed-schema):**

| Path | `'200'` oneOf (success:true) | `'200'` oneOf (success:false) | status-set | In-handler error (gom nhánh Error) |
|---|---|---|---|---|
| `resolveQrToken` | `QrResolveEnvelope` `{data: QrResolveResult}` (`imm00.py:303`) | `Error` | `[200,401,403,429]` | 404 token∄/leak-safe `imm00.py:366` · vendor-IDOR-403 `imm00.py:371` |
| `getAssetScanInfo` | `AssetScanInfoEnvelope` `{data: AssetScanInfo}` (`imm00.py:567`) | `Error` | `[200,401,403,429]` | 404 token/name∄ `imm00.py:416,425` · vendor-IDOR-403 `imm00.py:421` |
| `getAsset` | `AssetDetailEnvelope` `{data: AssetDetail}` (`imm00.py:324`) | `Error` | `[200,401,403]` | 404 asset∄ `imm00.py:297` · vendor-IDOR-403 `imm00.py:302` |

> **Hợp đồng client native (non-negotiable):** với create path **VÀ read path (C6)**, **KHÔNG branch theo HTTP status-line** cho business outcome — đọc `body.success` trước (KHÔNG cần discriminator — generator sinh oneOf-deserializer dựa closed-schema/required-set); nếu `false` đọc `body.code` + `body.http_status` (read: 404 NOT_FOUND / vendor-IDOR FORBIDDEN nằm TRONG body). Chỉ 401/dispatcher-403 (pre-handler) mới mang HTTP status-line THẬT (read: vendor-IDOR-403 KHÔNG status-line — nó đi nhánh Error 200). Root-fact verified @source: `_err` `response.py:95-154` + `handle()` return dict `api_handler.py:48` + `hooks.py:405` no `after_request`. Guard create: `TC-MOB-OAS-18a/b/c`; guard read (C6): `TC-MOB-OAS-24a..d` (assert oneOf + KHÔNG discriminator + closed-schema + disjoint required-set + status-set pre-handler-only).

---

## 6. Pagination contract

VERIFIED tại `assetcore/utils/pagination.py:6` (`paginate`) + consumer `api/imm00.py:267` (`list_assets` return).

```jsonc
{
  "success": true,
  "data": {
    "pagination": {
      "page":        1,        // trang hiện tại (>=1)
      "page_size":   20,       // số item/trang (clamp 1..100)
      "total":       1430,     // TỔNG bản ghi (permission-aware)
      "total_pages": 72,       // ceil(total/page_size); =0 khi total=0
      "offset":      0         // (page-1)*page_size
    },
    "items": [ ... ]           // mảng bản ghi của trang hiện tại
  }
}
```

| Field `pagination.*` | Kiểu | Quy tắc (`pagination.py`) |
|---|---|---|
| `page` | int | default **1**; `max(page, 1)` (`:7`). |
| `page_size` | int | default **20**; clamp **1..100** `min(max(size,1),100)` (`:8`). |
| `total` | int | tổng bản ghi sau permission filter. |
| `total_pages` | int | `ceil(total/page_size)` nếu total>0, ngược lại **0** (`:9`). |
| `offset` | int | `(page-1)*page_size` (`:15`) — derived, client KHÔNG cần gửi. |

**Param request:** tên `page` / `page_size` (KHÔNG `limit` / `offset` ở RPC layer — `list_assets(page=1, page_size=20, …)` `imm00.py:159-161`).

**INVARIANT (ENFORCED, ADR-IMM00-LIST-SCOPE):** `pagination.total == Σ len(items)` cộng dồn qua các trang, **permission-aware** — count (`count_with_or`) và items (`frappe.get_list`) dùng CÙNG filters/or_filters VÀ CÙNG `permission_query_conditions`. ⇒ KHÔNG có cảnh "header total=1430 nhưng bảng rỗng" cho bất kỳ persona nào (vendor isolated giữ nguyên).

> **Hợp đồng client:** lặp trang tới khi `page > total_pages` HOẶC `len(rows) == 0`. `total` đáng tin để hiển thị "X kết quả". KHÔNG suy `total` từ `len(rows)` một trang. (`rows` = `data.data[]` cho Work Order, `data.items[]` cho Incident — xem §6.2.)

### 6.1 Param phân trang — query-param đúng signature LIVE (C-LISTREAD)

VERIFIED qua AST introspect 3 hàm whitelist (read-only): `imm08.list_pm_work_orders:28` · `imm09.list_repair_work_orders:21` · `imm12.list_incidents:197`.

| Param (query) | Áp path | Kiểu | Default | Ràng buộc | Source |
|---|---|---|---|---|---|
| `page` | cả 3 | int | **1** | `minimum 1` (`max(page,1)` `pagination.py:7`) | component `Page` |
| `page_size` | cả 3 | int | **20** | `minimum 1` · `maximum 100` (clamp `pagination.py:8`) | component `PageSize` |
| `filters` | imm08 · imm09 | string (JSON-encoded) | `'{}'` | `parse_json` (`api_handler.py:77`); malformed → 400 `INVALID_PARAMS` | component `WorkOrderFilters` |
| `status` | imm12 | string | `''` | lọc Select trạng thái incident (`imm12.py:198`) | component `IncidentStatus` |
| `severity` | imm12 | string | `''` | Low/Medium/High/Critical (`imm12.py:199`) | component `IncidentSeverity` |
| `asset` | imm12 | string | `''` | Link AC Asset name (`imm12.py:200`) | component `IncidentAsset` |
| `open` | imm12 | int | `0` | `enum [0,1]`; `open=1` áp `open_incident_filter()` SoT drill dashboard (`imm12.py:201,206-208`); `status` đơn lẻ ưu tiên hơn | component `IncidentOpen` |

> `page`/`page_size` tách component tái dùng (`Page`/`PageSize`) cho cả 3 path. `filters` (imm08/09) là **JSON-string gói**, KHÁC filter rời của imm12 (`status`/`severity`/`asset`/`open`) — đúng signature 2 lớp service khác nhau. KHÔNG path/operationId/verb mới (giữ 15 path).

### 6.2 RECONCILE rows-key (`data` vs `items`) — QUYẾT ĐỊNH BA + known-gap

**Mâu thuẫn gốc (verify @source, read-only):** 2 service layer trả rows dưới **2 key khác nhau** — orphan `PaginatedListEnvelope` cũ chỉ khai `data.{pagination, items}` ⇒ KHỚP imm12, MÂU THUẪN imm08/09.

| List endpoint | Service trả | rows-key (sau `handle()`/`_ok`) | Envelope wire | Param query |
|---|---|---|---|---|
| `imm08.list_pm_work_orders` | `{"data": rows, "pagination": pg}` (`imm08.py:569`) | **`data.data[]`** | `PmWorkOrderListEnvelope` (200→`PmWorkOrderList`; item `PmWorkOrderListItem` — C3-split) | `filters`/`page`/`page_size` |
| `imm09.list_repair_work_orders` | `{"data": rows, "pagination": pg}` (`imm09.py:697`) | **`data.data[]`** | `RepairWorkOrderListEnvelope` (200→`RepairWorkOrderList`; item `RepairWorkOrderListItem` — C3-split) | `filters`/`page`/`page_size` |
| `imm12.list_incidents` | `{"items": rows, "pagination": pg}` (`imm12.py:764-770`) | **`data.items[]`** | `IncidentListEnvelope` (200→`IncidentList`) | `status`/`severity`/`asset`/`open`/`page`/`page_size` |

**QUYẾT ĐỊNH BA = Option (A) — khai 2 envelope PHÂN BIỆT** (KHÔNG chuẩn-hoá 1 key round này):

- **Lý do (codegen consistency cho repo native):** OpenAPI là hợp đồng máy đọc; nếu khai 1 rows-key chung trong khi runtime trả key khác → model codegen deser **sai key** → rows về **rỗng** (lỗi câm). Khai 2 envelope = nói ĐÚNG wire-shape THẬT cho từng path ⇒ client native parse đúng.
- **KHÔNG sửa service `.py`** (ràng buộc round): chuẩn-hoá rows-key về 1 key chung = đụng service layer + test BE ⇒ hoãn.
- `Pagination` sub-schema **DÙNG CHUNG** cho cả 2 envelope (không đổi).
- **KNOWN-GAP → Phase-E normalize:** thống nhất 2 rows-key (`data` vs `items`) về 1 key chung là việc **Phase-E** (chuẩn hoá envelope, đụng `services/imm08|09|12.py` + test). Tới khi đó, contract phản ánh ĐÚNG di sản 2 service. Quyết định kiến trúc: [`ADR-MOBILE-001.md` (g)](./ADR-MOBILE-001.md).

> **Cross-ref:** quyết định envelope list-read ↔ [ADR-MOBILE-001 (g)](./ADR-MOBILE-001.md) ↔ [11 §1 traceability](./11-phase-a-exit.md). Scope `reported_by` vs `assigned_to` (A2 finding) vẫn là known-gap hành vi (không đổi shape) — Phase-C kế.

### 6.3 List-ELEMENT schema (`PmWorkOrderListItem` / `RepairWorkOrderListItem` / `IncidentListItem`) — C3-split (đóng KNOWN-GAP "KHÔNG ép chung")

Phần tử (`data.data[].items` / `data.items[].items`) từng generic `{type: object}` ⇒ integrator KHÔNG bind được model "phiếu của tôi". C3 ban đầu khai 1 UNION `WorkOrderListItem` (PM∪CM). **C3-split (round này)** tách thành **2 item-schema field-disjoint per-endpoint** (PM ≠ CM field-set), mỗi list path có envelope + item RIÊNG (re-verify @source D4 — mở file, tìm symbol, KHÔNG tin số dòng):

| Element schema | Wire vào | Grounded @source | `required` |
|---|---|---|---|
| `PmWorkOrderListItem` | `PmWorkOrderListEnvelope.data.data[].items` | CHỈ `services/imm08.py::list_work_orders` (PM) — 12 repo-field + enrich `asset_name`/`location_name`/`assigned_to_name`/`supervisor_name` = 16 field | `[name]` |
| `RepairWorkOrderListItem` | `RepairWorkOrderListEnvelope.data.data[].items` | CHỈ `services/imm09.py::list_work_orders` (CM) — 16 repo-field (`parts_hold_started` bị `r.pop()`) + enrich `department_name`/`location_name`/`assigned_to_name` + derived `is_sla_breached`/`sla_paused` = 21 field | `[name]` |
| `IncidentListItem` | `IncidentListEnvelope.data.items[].items` | `services/imm12.py::list_incidents` (23 repo-field) + `_enrich_asset_names` (asset_name/reporter_name/assigned_to_name) + `_enrich_sla_breach` (is_response_breached/is_resolution_breached) | `[name]` |

**QUYẾT ĐỊNH BA = Option (A) — schema all-optional trừ `name` REQUIRED (closed-schema, KHÔNG discriminator = Decision-B):**

- `name` là **PK chung** mỗi doctype (AC PM Work Order / AC Asset Repair / Incident Report) ⇒ field duy nhất luôn có. Mọi field khác **optional** (service có thể trả `""`).
- `additionalProperties: false` (đóng) ⇒ codegen native sinh model tường minh; thừa key = lỗi spec, KHÔNG nuốt câm.
- **PM ≠ CM field-set ⇒ 2 item-schema RIÊNG (field-disjoint).** PM(imm08)/CM(imm09) projection KHÁC nhau (16 vs 21 field) ⇒ KHÔNG ép 1 union. Mỗi path (`list_pm_work_orders` / `list_repair_work_orders`) trỏ envelope + item của nó; rows-key `data` GIỮ nguyên cả 2. Codegen sinh 2 model tường minh, integrator KHÔNG còn đoán field nào thuộc PM, field nào thuộc CM.

**Field RIÊNG mỗi loại (DISJOINT — chứng cứ "KHÔNG ép chung"):**

| Nhóm | Field |
|---|---|
| Overlap-key (cả 2 doctype cùng trả) | `name`, `asset_ref`, `asset_name`, `status`, `assigned_to`, `assigned_to_name`, `location_name` |
| PM-only (`PmWorkOrderListItem`) | `pm_type`, `wo_type`, `due_date`, `completion_date`, `supervisor`, `supervisor_name`, `overall_result`, `is_late`, `source_pm_wo` |
| CM-only (`RepairWorkOrderListItem`) | `repair_type`, `priority`, `open_datetime`, `completion_datetime`, `mttr_hours`, `sla_breached`, `sla_target_hours`, `is_repeat_failure`, `root_cause_category`, `risk_class`, `parts_hold_hours`, `department_name`, `is_sla_breached` (derived), `sla_paused` (derived) |

PM-only ∩ CM-only = ∅. `PmWorkOrderListItem` = overlap ∪ PM-only (16); `RepairWorkOrderListItem` = overlap ∪ CM-only (21). Guard `test_mob_oas_21g_pm_cm_field_sets_disjoint` đóng băng.

> ⚠️ **Re-verify @source corrections (D4):** (1) `parts_hold_started` **KHÔNG khai** ở CM — imm09 `list_work_orders` gọi `r.pop("parts_hold_started", None)` trước khi trả ⇒ KHÔNG ra wire. (2) imm08 enrich `assigned_to_name`/`supervisor_name`; imm09 enrich `assigned_to_name`/`department_name`/`location_name`. (3) `IncidentListItem` dùng key **`asset`** (KHÔNG `asset_ref` như Work Order).

> ✅ **KNOWN-GAP normalize element ĐÓNG (C3-split):** tách 2 item-schema per-endpoint **KHÔNG đụng service `.py`** (chỉ thêm 2 envelope + 2 response + 2 item-schema trong yaml + wire 2 path) ⇒ đóng NGAY round này, KHÔNG defer Phase-E. Phase-E CÒN LẠI chỉ lo normalize **rows-key** `data` vs `items` (§6.2 — việc đó MỚI đụng service). Quyết định: [ADR-MOBILE-001 (g)](./ADR-MOBILE-001.md).

---

## 7. Versioning & deprecation

VERIFIED định hướng tại `01-architecture.md §4`.

- **Contract version** = `info.version` của OpenAPI (`assetcore-mobile.openapi.yaml`) + thư mục namespace — KHÔNG ép dùng `/api/v2` của Frappe.
- **Đường nghiệp vụ** = `/api/method/<dotted>` (RPC, đúng đường FE web đang gọi — BE↔FE naming contract). MVP KHÔNG cần `/api/resource` hay `/api/v2`.
- **Lớp bọc mobile (nếu Phase C cần)** = namespace **`api/mobile/v1`** trong app (`assetcore/api/mobile/v1/…` → gọi `/api/method/assetcore.api.mobile.v1.<fn>`). CHỈ bọc/adapt shape, gọi xuống service hiện có — KHÔNG nghiệp vụ mới.

**Chính sách deprecation (đặt nền Phase C/F — KHÔNG impl ở A3):**

1. **Additive-only:** thêm field/endpoint mới KHÔNG phá đường cũ. Client cũ vẫn chạy.
2. **Không phá đường cũ:** giữ endpoint cũ tới hết deprecation window đã công bố.
3. **Đánh dấu `deprecated: true`** trong OpenAPI (path/operation/schema) khi loại bỏ dần; kèm note thay thế.
4. **Bump `info.version`** khi có breaking change ở lớp bọc `api/mobile/v1` → cân nhắc `…/v2`.

---

## 8. Param convention (rule dự án)

1. **Whitelist signature dùng `str = ""`, KHÔNG `str | None`** — `str | None` gây pydantic coercion → **HTTP 417** ở prod. Rule dự án (ADR-MOBILE decision d; `01-architecture.md §5`).
   > ⚠️ **Drift đã phát hiện (document, KHÔNG sửa code ở A3):** một số endpoint hiện trộn `str = None` cho filter tuỳ chọn — vd `list_assets(…, lifecycle_status: str = None, …)` `imm00.py:162-168`; `create_calibration` 6 param `str=None` (ghi nhận A2, `imm11.py`). Đây là nợ kỹ thuật cần dọn ở Phase C (đổi `str=None`→`str=""`) để loại nguy cơ 417. A3 chỉ document; KHÔNG đụng code.
2. **JSON param qua `filters` string + `parse_json`** (`api_handler.py:77`): khi `filters` là string KHÔNG parse được JSON → raise `INVALID_PARAMS` (400) với message VI "Tham số filters không phải JSON hợp lệ" (`api_handler.py:94-99`). Client gửi `filters` = JSON-encoded string.
3. **`page`/`page_size`** là int param riêng (KHÔNG nhét trong `filters`), default 1/20 (chương 6).

### 8.1 Convention `operationId` (SSoT — Phase C bồi path mới theo CÙNG luật)

`operationId` là **khoá ổn định** mà `openapi-generator` dùng để đặt **tên method client** (Dart/dio, TS-axios — `09-native-repo-guide.md §2`). Đổi `operationId` = **đổi tên method** ở mọi client đã sinh ⇒ breaking. Vì vậy `operationId` phải **ổn định + duy nhất + theo luật cố định**.

**Quy tắc sinh (áp cho `assetcore-mobile.openapi.yaml`):**

1. **Gốc = tail-của-dotted-path** (phần cuối sau dấu `.` của RPC `/api/method/<dotted>`), KHÔNG lấy cả module-prefix. VD `assetcore.api.imm00.get_asset` → gốc `get_asset`; `assetcore.api.imm12.report_incident` → gốc `report_incident`.
2. **snake_case → camelCase verbNoun:** verb đứng đầu (chữ thường), các từ sau viết hoa chữ cái đầu, bỏ gạch dưới. Regex hợp lệ: `^[a-z][a-zA-Z0-9]*$`.
3. **GET-list → `listX`:** `list_pm_work_orders` → `listPmWorkOrders`; `list_repair_work_orders` → `listRepairWorkOrders`; `list_incidents` → `listIncidents`.
4. **`create_X` → `createX`:** `create_pm_work_order` → `createPmWorkOrder`; `create_repair_work_order` → `createRepairWorkOrder`; `create_calibration` → `createCalibration`.
5. **`get_X` → `getX`:** `get_asset` → `getAsset`; `get_asset_scan_info` → `getAssetScanInfo`.
6. **`report_X` → `reportX`:** `report_incident` → `reportIncident`.
7. **`resolve_qr_token` → `resolveQrToken`** (token/QR viết liền theo CamelCase từng từ snake).
8. **OAuth = verb-first** (provider Frappe `frappe.integrations.oauth2.*`): vì gốc-tail (`authorize`/`get_token`/`revoke_token`) KHÔNG mang ngữ cảnh "OAuth", thêm hậu tố `OAuth` để rõ + tránh va tên: `authorize` → `authorizeOAuth`; `get_token` → `getOAuthToken`; `revoke_token` → `revokeOAuthToken`. **(C4)** `openid_profile` (userinfo/whoami) → **`getUserInfo`** — verb-first nhóm auth, NHÃN ngữ-nghĩa "userinfo" rõ hơn tail thô `openidProfile`.
9. **2 device-token GIỮ NGUYÊN TÊN** (chốt **A5**, KHÔNG đổi để tránh drift client đã sinh): `register_device_token` → **`registerDeviceToken`**; `unregister_device_token` → **`unregisterDeviceToken`** (theo đúng luật 4/2, đã đặt sẵn từ A5).

**Bảng 16/16 operationId (A10 + C4 — codegen-able):**

| `operationId` | Verb | RPC path (`/api/method/...`) |
|---|---|---|
| `authorizeOAuth` | GET | `frappe.integrations.oauth2.authorize` |
| `getOAuthToken` | POST | `frappe.integrations.oauth2.get_token` |
| `revokeOAuthToken` | POST | `frappe.integrations.oauth2.revoke_token` |
| `getUserInfo` | GET | `frappe.integrations.oauth2.openid_profile` *(C4 — OIDC userinfo/whoami)* |
| `resolveQrToken` | GET | `assetcore.api.imm00.resolve_qr_token` |
| `getAssetScanInfo` | GET | `assetcore.api.imm00.get_asset_scan_info` |
| `getAsset` | GET | `assetcore.api.imm00.get_asset` |
| `reportIncident` | POST | `assetcore.api.imm12.report_incident` |
| `createPmWorkOrder` | POST | `assetcore.api.imm08.create_pm_work_order` |
| `createRepairWorkOrder` | POST | `assetcore.api.imm09.create_repair_work_order` |
| `createCalibration` | POST | `assetcore.api.imm11.create_calibration` |
| `listPmWorkOrders` | GET | `assetcore.api.imm08.list_pm_work_orders` |
| `listRepairWorkOrders` | GET | `assetcore.api.imm09.list_repair_work_orders` |
| `listIncidents` | GET | `assetcore.api.imm12.list_incidents` |
| `registerDeviceToken` | POST | `assetcore.api.mobile.v1.register_device_token` *(A5 — giữ nguyên)* |
| `unregisterDeviceToken` | POST | `assetcore.api.mobile.v1.unregister_device_token` *(A5 — giữ nguyên)* |

**Invariant (guard test):** mọi path-operation CÓ `operationId`; `operationId` **duy nhất** toàn file (`len(set)==len(list)==16` — C4 +`getUserInfo`); khớp regex camelCase; 2 device-token tên đóng băng; **sau EPIC-D D4 (§8.9): `_STUB_PATHS = ∅` (0 STUB-on-MVP)** — 2 device-token (`register`/`unregister`) ĐÃ rời STUB với typed `requestBody DeviceTokenRequest` + 200 oneOf `[<Created>, Error]` (service D2 `mobile_device_token.py` tồn tại @source). 4 read/create cũ (2 QR + `get_asset` + `createPmWorkOrder`) ĐÃ rời STUB ở R4 §8.7 (cùng `report_incident` §8.3, 3 list §8.4, `createRepairWorkOrder` §8.5, `createCalibration` §8.6). `responses/Stub` HẾT referenced → forward-reserve (§8.2 RESERVED + `_RESERVED_ORPHANS`). Guard = `assetcore/tests/test_mobile_oas.py` (TC-MOB-OAS-01..07 + 20 + **22** device-token typed, read-only yaml — KHÔNG đọc auto-gen AssetCore spec). **Phase C/R4/D4** khi bồi path PHẢI: (a) đặt `operationId` theo luật trên, (b) thêm dòng vào map `_EXPECTED` của guard test, (c) GROUNDED chữ-ký service THẬT KHÔNG đổi `operationId`, (d) gỡ path tương ứng khỏi `_STUB_PATHS` của guard khi bồi schema thật (NHƯNG giữ symmetry trong `_MVP_BUSINESS_PATHS`/`_DEVICE_TOKEN_FROZEN` để 401/403 KHÔNG vỡ — xem §8.3/§8.4/§8.6/§8.7/§8.9).

> ⚠️ **A10 chỉ thêm contract-identity** (`operationId`) — KHÔNG bồi `requestBody`/`response` schema chi tiết. Phase-C đã bồi **requestBody** cho `report_incident` (§8.3) + **list-read** cho 3 list path (§8.4) + **requestBody** cho `createRepairWorkOrder` (§8.5) + **requestBody** cho `createCalibration` (§8.6); **R4 §8.7** type tiếp **`data`** cho 4 read/create (2 QR + `get_asset` + `createPmWorkOrder`) GROUNDED chữ-ký service THẬT ⇒ **chỉ CÒN 2 device-token STUB** (`[ROADMAP]` BE chưa impl).

### 8.2 Contract integrity & codegen-validity (SSoT allow-list orphan — A12)

> KHÁC §8.1 (đặt **tên** `operationId`). §8.2 bảo đảm yaml **resolve được** để `openapi-generator` chạy KHÔNG crash + KHÔNG để **dead contract-surface** (component thừa lén tích tụ). Đây là **anti-regression guard** — yaml hiện tại đã đạt (verify @source 2026-06-09).

**Vì sao quan trọng (codegen-validity):** `openapi-generator` (Dart/dio, TS-axios — [`09-native-repo-guide.md §2`](./09-native-repo-guide.md)) **resolve mọi `$ref` trước khi sinh model**. Một `$ref` trỏ tới component KHÔNG tồn tại (**dangling**) ⇒ generator **crash hoặc sinh model rỗng** (codegen-invalid). Một component **defined-nhưng-không-`$ref`'d** (**orphan**) thì codegen vẫn chạy NHƯNG là **dead surface** — nếu thừa lén tích tụ sẽ phình client sinh ra bằng model không ai dùng + che giấu hợp đồng đã chết. Vì vậy 2 ràng buộc CHỐT:

1. **0 dangling `$ref`** — MỌI `$ref: '#/components/...'` (và mọi pointer cục bộ `#/...`) trỏ tới node **TỒN TẠI** (hard-fail; dangling = codegen crash).
2. **Orphan ⊆ allow-list RESERVED** — tập component defined-không-`$ref`'d PHẢI nằm trong allow-list cố định **6 mục** dưới (lịch sử: A13 10 → C-LISTREAD 9 → G-REQBODY 7 → C-REQBODY-CREATEREPAIR 6 → **C-REQBODY-CREATECAL 6 (KHÔNG đổi — `Conflict409`/`NotFound404` đã referenced; 4 component calibration mới `$ref`'d ngay)**). Orphan **NGOÀI** allow-list = FAIL (chống dead surface lén lút). Mỗi mục allow-list là **forward-reserve có chủ ý** (Phase E sẽ wire) HOẶC **false-orphan** (dùng qua keyword khác `$ref`).

> **A13 — coverage 401/429 đã wire (orphan 11→10):** vòng A13 wire `Unauthorized401` lên **10 path nghiệp vụ STUB** (cùng 2 device-token đã có 401 từ A5 ⇒ **toàn bộ 12 path MVP declare 401**; bearer hết hạn → refresh/re-auth — §4 row `UNAUTHORIZED` + §5 ngoại lệ 401 + [`ADR-MOBILE-001.md (e)`](./ADR-MOBILE-001.md)) và wire `RateLimited429` lên **ĐÚNG 2 path có `@rate_limit` THẬT** (`imm00.resolve_qr_token` `imm00.py:311` + `imm00.get_asset_scan_info` `imm00.py:354` — §5 row 429). ⇒ `RateLimited429` **HẾT orphan** → đã **gỡ khỏi bảng RESERVED dưới + `_RESERVED_ORPHANS`** (đồng bộ 1 nhịp, nếu không `TC-MOB-OAS-10` stale-check ĐỎ). `Unauthorized401` từ trước **KHÔNG** ở RESERVED (device-token đã dùng) → allow-list 401 KHÔNG đổi. `NotFound404`/`Unprocessable422` **VẪN reserve** (404/422 phụ thuộc requestBody/asset-lookup → **Phase C**, chống scope-creep). 3 auth path GIỮ NGUYÊN (302/200 — Frappe core).

> **A16 — ERROR-STATUS contract fix (tách 401 vs 403 + body raw THẬT; orphan VẪN 10):** vòng A16 (1) wire `'403'`→`Forbidden` lên **TẤT CẢ 12 path MVP** (10 business STUB **đã** có 403 từ A13-wiring + **bổ sung 2 device-token** `register/unregister_device_token` hiện thiếu — bearer-gated self-service [`06-push-fcm.md §2.3`](./06-push-fcm.md), guest/no-token cũng `PermissionError` 403 `__init__.py:876`) ⇒ **tập path-403 == tập path-401 (12==12, đối xứng)**. `Forbidden` **KHÔNG** ở RESERVED (đã referenced từ A13 — wire thêm 2 device-token KHÔNG đổi orphan). (2) **+component `schemas/FrappeRawError`** {`exc_type`* req · `exception?`/`exc?`/`_server_messages?` opt} source-char @`frappe/utils/response.py` V1 (`exc_type` `:46`; `exception` `:43-45` gated; `exc` `:185`; `_server_messages` `:188`) + **repoint** `Unauthorized401`/`Forbidden`/`RateLimited429` `$ref` từ `schemas/Error` → `schemas/FrappeRawError` (3 response pre-handler raw — KHÔNG Error envelope) ⇒ codegen sinh model KHỚP body runtime (KHÔNG deser-fail). `FrappeRawError` được `$ref` **NGAY** bởi 3 response ⇒ **KHÔNG orphan** → KHÔNG vào allow-list. (3) `RateLimited429` **KHÔNG** thêm `Retry-After`/`X-RateLimit-*` (P2 DEFER — `conf.rate_limit=null` ⇒ 0 backoff-header, §5). 3 auth path GIỮ NGUYÊN (302/200/400 — KHÔNG declare 403). **DIFF A16** = +1 schema (`FrappeRawError`) + repoint 3 `$ref` + wire `'403'` lên 2 device-token. `operationId` FROZEN, 0 path mới.

**Bảng RESERVED — 10 orphan-component hợp lệ (SSoT của allow-list; guard `TC-MOB-OAS-10` phản chiếu bảng này):**

> **EPIC-D D4 (Vòng 17, orphan 9→10):** `responses/Stub` **VÀO RESERVED** — 2 device-token RỜI Stub (typed `requestBody` + 200 oneOf `[<Created>, Error]`, §8.9) ⇒ `responses/Stub` HẾT referenced (0 path MVP còn dùng). GIỮ component làm **forward-reserve**: 2 negative-injection guard (`TC-MOB-OAS-23d`/`24e`) inject `$ref Stub` vào deepcopy để chứng RED-before — gỡ component = phá precondition test. ⇒ orphan **9→10**.

> **G-OAS-STATUSLINE (P1 contract-correctness, orphan 6→9):** `responses/NotFound404` + `responses/Unprocessable422` + `responses/Conflict409` **TRỞ LẠI RESERVED** — chúng KHÔNG còn được `$ref` từ 3 create path vì in-handler business error (404/422 report; 404/409 repair/cal) **arrive HTTP status-line 200 + Error body** (quirk §5: `_err` `response.py:95-154` + `handle()` return dict `api_handler.py:48` + `hooks.py:405` no `after_request` ⇒ status-line KHÔNG BAO GIỜ set cho in-handler error). Keying chúng dưới HTTP-code response-key = **DEAD-DESER branch** (codegen route-by-status-line KHÔNG bao giờ khớp). ⇒ gom vào nhánh `Error` của `200`-oneOf [Created, Error] closed-schema route-by-VALUE `body.success` (Decision-B §5c — KHÔNG discriminator) + giữ 3 component làm **forward-reserve doc-intent** (Phase-E nếu `after_request` hook đổi status-line thật).

| Pointer (`#/components/...`) | Nhóm | Vì sao GIỮ (forward-reserve / false-orphan) | Nguồn chân lý / forward-phase |
|---|---|---|---|
| `parameters/IdempotencyKey` | Offline write-queue | Header `Idempotency-Key` cho thao tác GHI (dedupe replay). CHƯA wire vào path write. | [`07-offline-sync.md §3`](./07-offline-sync.md) → **Phase E** wire vào 4 path write + asset-create |
| `parameters/IfMatch` | Offline conflict | Optimistic-lock `If-Match` (`modified`) → 409 server-wins. CHƯA wire path UPDATE. | [`07-offline-sync.md §4`](./07-offline-sync.md) → **Phase E** wire vào path UPDATE |
| `parameters/IfNoneMatch` | Offline read-cache | Conditional-GET ETag → 304. CHƯA wire path read. | [`07-offline-sync.md §2`](./07-offline-sync.md) → **Phase E** wire vào path read |
| `parameters/IfModifiedSince` | Offline read-cache | Fallback validator HTTP-date → 304. CHƯA wire path read. | [`07-offline-sync.md §2`](./07-offline-sync.md) → **Phase E** wire vào path read |
| `responses/NotModified304` | Offline read-cache | 304 body-rỗng (đi kèm `IfNoneMatch`/`IfModifiedSince`). CHƯA wire path read. | [`07-offline-sync.md §2`](./07-offline-sync.md) → **Phase E** wire vào path read |
| `responses/NotFound404` | In-handler 404 → doc-only | 404 (asset∄) arrive HTTP-200 + Error body (route-by-body §5c) — KHÔNG status-line key (dead-deser). Doc-intent + Phase-E nếu `after_request` set status-line. | §5c + `services/imm12.py:361`/`imm09.py:746`/`imm11.py:999` |
| `responses/Unprocessable422` | In-handler 422 → doc-only | 422 (BR-12-01) arrive HTTP-200 + Error body — KHÔNG status-line key. Doc-intent + Phase-E. | §5c + `services/imm12.py:359` |
| `responses/Conflict409` | In-handler 409 + offline reuse → doc-only | 409 (HAS_OPEN_WO / ASSET_BLOCKED) arrive HTTP-200 + Error body — KHÔNG status-line key; + offline optimistic-lock reuse (§4). Doc-intent + Phase-E. | §5c + `services/imm09.py:753`/`imm11.py:1002` |
| `responses/Stub` | **D4 forward-reserve** | EPIC-D D4: 2 device-token rời Stub (typed §8.9) ⇒ Stub HẾT referenced. GIỮ làm forward-reserve (negative-injection guard `TC-MOB-OAS-23d`/`24e` inject ref này vào deepcopy chứng RED-before). | §8.9 + `test_mobile_oas.py::_RESERVED_ORPHANS` |
| `securitySchemes/OAuth2` | **False-orphan** | Dùng qua **top-level `security:`** keyword (KHÔNG `$ref`) + per-op `security: []` của 3 auth path → walk `$ref` naive KHÔNG thấy ⇒ **phải** allow-list, KHÔNG forbid naive. | §8.1 + [`03-auth-oauth2.md`](./03-auth-oauth2.md) — security keyword |

> **Đã GỠ khỏi RESERVED ở C-REQBODY-CREATEREPAIR** (hết orphan vì đã wire vào `create_repair_work_order.post`): `responses/Conflict409` (409 = asset đã có WO mở `IMM09_ASSET_HAS_OPEN_WO` `services/imm09.py:753`, http_status **409** `messages.py:667`). orphan **7→6**. SELF-CORRECTION: đề mục viết "422→Unprocessable422" cho HAS_OPEN_WO — **SAI @source** (message-code map 409 CONFLICT, KHÔNG 422); doc bám sự-thật `_HTTP_TO_BUCKET[409]=CONFLICT` (`notify.py:42`). `responses/NotFound404` (404 asset∄ `IMM09_ASSET_NOT_FOUND` `services/imm09.py:746`) đã GỠ khỏi RESERVED từ G-REQBODY (dùng chung, nay createRepair tái dùng — vẫn referenced).

> **C-REQBODY-CREATECAL — KHÔNG đụng allow-list (orphan GIỮ 6):** wire `createCalibration.post` tái dùng `responses/Conflict409` (409 = asset lifecycle blocked-for-WO ∧ NOT recalibration, `IMM11_ASSET_BLOCKED` `services/imm11.py:1002`, http_status **409** CAL-008 `messages.py:860`) + `responses/NotFound404` (404 asset∄ `IMM11_ASSET_NOT_FOUND` `services/imm11.py:999`) — **CẢ HAI đã referenced** (createRepair/report wire trước) ⇒ KHÔNG đổi orphan. 4 component calibration mới (`schemas/CreateCalibrationRequest`/`...Response` + `responses/CreateCalibrationCreated` + `requestBodies/CreateCalibrationBody`) **`$ref`'d NGAY** ⇒ KHÔNG orphan → KHÔNG vào allow-list. **orphan GIỮ 6.** **SELF-CORRECTION:** đề mục viết "422→Unprocessable422 + KHÔNG wire 409 (calibration KHÔNG có open-WO gate)" — **SAI @source**: `IMM11_ASSET_BLOCKED` map `http_status=409` CONFLICT (`messages.py:860`, `_HTTP_TO_BUCKET[409]=CONFLICT` `notify.py:42`), `handle()` pass-through (`api_handler.py:61`) ⇒ surface **HTTP-409 THẬT** (KHÔNG 422). Calibration-409 KHÁC nguyên-nhân createRepair-409 (lifecycle-block CAL-008 vs open-WO) nhưng CÙNG HTTP-409 ⇒ tái dùng `Conflict409`.

> **Đã GỠ khỏi RESERVED ở G-REQBODY** (hết orphan vì đã wire vào `report_incident.post`): `responses/NotFound404` (404 = asset∄ `IMM12_ASSET_NOT_FOUND` `services/imm12.py:361`) + `responses/Unprocessable422` (422 = BR-12-01 Critical→`clinical_impact` `services/imm12.py:359`). orphan **9→7**.

> **Đã GỠ khỏi RESERVED ở A13** (hết orphan vì đã wire vào path): `responses/RateLimited429` (wire vào 2 path `@rate_limit` `imm00.resolve_qr_token`/`get_asset_scan_info` — §5 row 429). `responses/Unauthorized401` **chưa từng** ở RESERVED (device-token dùng từ A5; A13 mở rộng dùng lên 10 path nghiệp vụ).

> **B1 (Phase B) — `OAuthError400` KHÔNG vào RESERVED (wired ngay):** B1 thêm component **`schemas/OAuthError400`** + **`responses/OAuthError400`** (auth-section passthrough, §5b). Cả 2 **được `$ref` ngay khi thêm** (`responses/OAuthError400` → `schemas/OAuthError400`; `getOAuthToken` `'400'` → `responses/OAuthError400`) ⇒ **KHÔNG orphan** → **KHÔNG** ghi vào allow-list. ⇒ **orphan-count GIỮ NGUYÊN 10** (bảng trên không đổi). `defined` component: 19→**21** (+2); `$ref` distinct: 9→**11** (+2). DIFF B1 = thêm `OAuthError400` schema+response + wire `'400'` lên `getOAuthToken` (CHỈ) + body-schema 200 cho `revokeOAuthToken` (empty object). KHÔNG đổi path/operationId.

> **A16 — `FrappeRawError` KHÔNG vào RESERVED (wired ngay) — orphan VẪN 10:** A16 thêm component **`schemas/FrappeRawError`** (pre-handler raw 401/403/429, §5b shape #3). Được `$ref` **NGAY** bởi 3 response `Unauthorized401`/`Forbidden`/`RateLimited429` (repoint từ `schemas/Error`) ⇒ **KHÔNG orphan** → **KHÔNG** ghi vào allow-list. Wire thêm `'403'`→`Forbidden` lên 2 device-token chỉ tăng `$ref` **occurrence** (KHÔNG đổi distinct — `responses/Forbidden` đã referenced từ A13). ⇒ **orphan-count GIỮ NGUYÊN 10** (bảng trên KHÔNG đổi; `Forbidden` chưa từng ở RESERVED). `defined` component: 21→**22** (+1 `FrappeRawError`); `$ref` distinct: 11→**12** (+1 `schemas/FrappeRawError`); `$ref` occurrence: 48→**50** (+2 device-token `'403'`). DIFF A16 = +1 schema + repoint 3 `$ref` + wire `'403'` lên 2 device-token. KHÔNG đổi path/operationId.

> **C-REQBODY-REPORTINCIDENT (Phase-C) — `ReportIncidentRequest`+`ReportIncidentBody` KHÔNG vào RESERVED (wired ngay) — orphan VẪN 10:** Phase-C thêm 2 component **`schemas/ReportIncidentRequest`** (4 field required EXACT — §8.3) + **`requestBodies/ReportIncidentBody`** (wrapper `required:true`, content `application/json`). Cả 2 **được `$ref` NGAY khi thêm** (`requestBodies/ReportIncidentBody` → `schemas/ReportIncidentRequest`; `report_incident.post.requestBody` → `requestBodies/ReportIncidentBody`) ⇒ **KHÔNG orphan** → **KHÔNG** ghi vào allow-list. ⇒ **orphan-count GIỮ NGUYÊN 10** (bảng RESERVED trên KHÔNG đổi). **KHÔNG đụng `NotFound404`/`Unprocessable422`** (404/422 vẫn reserve cho Phase-C kế — chưa wire vòng này; tránh scope-creep). `defined` component: 22→**24** (+2); `$ref` distinct: 12→**14** (+2: `requestBodies/ReportIncidentBody` + `schemas/ReportIncidentRequest`); `$ref` occurrence: 50→**52** (+2: path→requestBody + requestBody→schema). DIFF Phase-C = +1 schema + +1 requestBody + wire `requestBody` lên `report_incident` (CHỈ — KHÔNG đổi response surface 200/401/403). `operationId` FROZEN, 0 path mới. `report_incident` RỜI `_STUB_PATHS` (có requestBody) NHƯNG GIỮ `_MVP_BUSINESS_PATHS` ⇒ symmetry 401/403 (12==12) BẤT BIẾN.

> **C-LISTREAD (Phase-C list-read) — `PaginatedListEnvelope` ĐÃ tách & GỠ khỏi RESERVED (orphan 10→9):** orphan cũ `schemas/PaginatedListEnvelope` (khai `data.{pagination, items}`) chỉ KHỚP imm12, **MÂU THUẪN** imm08/09 (rows-key `data`). C-LISTREAD **tách** theo rows-key THẬT @source (§6.2); **C3-split** tách tiếp WO theo field-set → **`schemas/PmWorkOrderListEnvelope`** + **`schemas/RepairWorkOrderListEnvelope`** (`data.data[]`, imm08/imm09 RIÊNG) + **`schemas/IncidentListEnvelope`** (`data.items[]`, imm12) — kèm wrapper response **`responses/PmWorkOrderList`**/**`responses/RepairWorkOrderList`**/**`responses/IncidentList`** + 7 param pagination (`Page`/`PageSize`/`WorkOrderFilters`/`IncidentStatus`/`IncidentSeverity`/`IncidentAsset`/`IncidentOpen`). **TẤT CẢ 11 component mới `$ref`'d NGAY** (path→response→schema; path→param) ⇒ KHÔNG orphan → KHÔNG vào allow-list; `PaginatedListEnvelope` cũ **xoá** (đã thay) ⇒ **gỡ khỏi RESERVED → orphan 10→9**. **KHÔNG đụng `NotFound404`/`Unprocessable422`** (vẫn reserve Phase-C kế). `defined` component: 24→**34** (+10: −1 PaginatedListEnvelope +11 mới); `$ref` distinct: 14→**25** (+11); `$ref` occurrence: 52→**67** (+15: 3 list path × {1×200-response + 2..4 param}). DIFF C-LISTREAD = −1 orphan-schema + 2 list-envelope + 2 list-response + 7 param + wire 3 list path (param + 200). `operationId` FROZEN, 0 path/verb mới (giữ 15 path). 3 list RỜI `_STUB_PATHS` NHƯNG GIỮ `_MVP_BUSINESS_PATHS` ⇒ symmetry 401/403 (12==12) BẤT BIẾN.

> **G-REQBODY (Phase-C) — `NotFound404`+`Unprocessable422` ĐÃ wire & GỠ khỏi RESERVED (orphan 9→7); +`ReportIncidentResponse`/`ReportIncidentCreated`/`ReportIncidentForbidden` KHÔNG vào RESERVED (wired ngay):** G-REQBODY đóng 4 contract-gap codegen `report_incident`. (1) **wire `404`→`NotFound404`** (asset∄ `IMM12_ASSET_NOT_FOUND` `services/imm12.py:361`) + **`422`→`Unprocessable422`** (BR-12-01 Critical→`clinical_impact` `services/imm12.py:359`) vào `report_incident.post` ⇒ CẢ 2 hết-orphan → **gỡ khỏi RESERVED → orphan 9→7**. (2) **+schema `ReportIncidentResponse`** `{name, status, severity}` (grounded `services/imm12.py:410`; `status` enum Select-canonical 7 @`incident_report.json`) + **response `ReportIncidentCreated`** (success envelope, `data` `$ref ReportIncidentResponse`) — `report_incident.post.'200'` repoint `Stub`→`ReportIncidentCreated`. (3) **+response `ReportIncidentForbidden`** = `oneOf [Error, FrappeRawError]` (DUAL-SHAPE 403 §5a/§5b) — `report_incident.post.'403'` repoint `Forbidden`→`ReportIncidentForbidden`. (4) **`ReportIncidentBody.content`** +media-type `application/x-www-form-urlencoded` (CÙNG `$ref ReportIncidentRequest` — Frappe RPC `form_dict`, §9). 3 component mới `$ref`'d NGAY ⇒ KHÔNG orphan → KHÔNG vào allow-list. `defined` component: 34→**37** (+3: `ReportIncidentResponse`/`ReportIncidentCreated`/`ReportIncidentForbidden`); `$ref` distinct: 25→**30** (+5: 3 component mới + `NotFound404` + `Unprocessable422` — 2 cái này trước defined-mà-orphan, nay referenced); `$ref` occurrence: 67→**73** (+6: report 404+422+ form-urlencoded media-type-schema + ReportIncidentCreated→ReportIncidentResponse + 2 nhánh oneOf của ReportIncidentForbidden; repoint 200/403 thay ref cũ KHÔNG đổi tổng path-level). **orphan 9→7** (gỡ `NotFound404`/`Unprocessable422`). **Symmetry 401/403 (12==12) BẤT BIẾN** (`report_incident` VẪN declare 403, chỉ KHÁC shape). `operationId` FROZEN, 0 path mới.

> **Phân loại:** 5 mục đầu = **offline forward-reserve** (Phase E sẽ wire vào path) — đặc tả tại [`07-offline-sync.md`](./07-offline-sync.md) (offline COMPONENTS §2/§3/§4). Mục cuối `OAuth2` = **false-orphan** (security keyword). KHI Phase C/E wire 1 component vào path → component đó hết-orphan ⇒ phải **gỡ khỏi allow-list** trong guard (`TC-MOB-OAS-10`) để allow-list luôn = orphan THẬT (A13 đã làm với `RateLimited429`; C-LISTREAD với `PaginatedListEnvelope`; G-REQBODY với `NotFound404`/`Unprocessable422`; **C-REQBODY-CREATEREPAIR với `Conflict409`**).

**Invariant (guard `TC-MOB-OAS-09/10/11/12/13/14` + `TC-MOB-OAUTH-TOKEN-01..05` — THÊM, không THAY 01..08):**
- `TC-MOB-OAS-09` (referential integrity): walk toàn yaml bằng **stdlib** (tự resolve pointer `#/...`, KHÔNG cần `openapi_spec_validator`/`prance` vì 2 lib này KHÔNG cài) ⇒ **0 dangling** (mọi `$ref` resolve về node tồn tại, kể cả `#/paths` nếu có). Verify @source (C-REQBODY-CREATECAL): **85** `$ref` occurrence, **39** distinct pointer, **0 dangling** (A13 = 46/9; B1 +2 do `OAuthError400`; A16 +2 occ + +1 distinct do `schemas/FrappeRawError`; C-REQBODY +2 occ + +2 distinct; C-LISTREAD +15 occ + +11 distinct; G-REQBODY +6 occ + +5 distinct; C-REQBODY-CREATEREPAIR +6 occ + +5 distinct; **C-REQBODY-CREATECAL +6 occ + +4 distinct**: +3 component calibration (Request/Response/Created) + 1 requestBody (Body) `$ref`'d ngay; `Conflict409`/`NotFound404` đã referenced ⇒ chỉ +occ — xem §8.6).
- `TC-MOB-OAS-10` (orphan allow-list): tập component defined-không-`$ref`'d (**45 defined − 39 referenced**) PHẢI **⊆** allow-list **6 mục** bảng trên; orphan NGOÀI allow-list = FAIL; mục allow-list không-còn-orphan (đã wire) = FAIL (allow-list stale). `OAuth2` BẮT BUỘC ∈ allow-list (false-orphan — KHÔNG forbid naive). Verify @source (C-REQBODY-CREATECAL): 45 defined − 39 referenced = **6 orphan**, khớp 100% allow-list (4 component calibration mới `$ref`'d ngay — KHÔNG vào allow-list; `Conflict409`/`NotFound404` đã referenced trước ⇒ allow-list KHÔNG đổi, orphan GIỮ 6).
- `TC-MOB-OAS-16` (C-REQBODY-CREATEREPAIR — class riêng `TestMobileCreateRepairBody`, §8.5): (a) `create_repair_work_order.post` có `requestBody` = **`$ref`-ONLY** `requestBodies/CreateRepairWorkOrderBody` (**G-OAS-403-DISAMBIG**: gỡ sibling `required:true` ở path-level — OAS 3.0.3 bỏ qua sibling cạnh `$ref`); (b) component `required:true` + json `$ref` `CreateRepairWorkOrderRequest`; (c) `required` EXACT = `[asset_ref, repair_type, priority, failure_description]` (4 không-default @`imm09.py:36-38`); (d) `repair_type` enum `[Corrective, Breakdown, Warranty Repair]` + `priority` enum `[Normal, Urgent, Emergency]` (Select-canonical @`asset_repair.json`); (e) 3 optional có (string) + `requested_by` KHÔNG ở body (server gán `imm09.py:770`); (f) content oneOf json+form-urlencoded (CÙNG schema); (g) response surface `200`→`CreateRepairWorkOrderCreated`, `401`→`Unauthorized401`, `403`→`Forbidden` (**single-shape**, ≠ `ReportIncidentForbidden`), `404`→`NotFound404`, `409`→`Conflict409`; status-set `[200,401,403,404,409]` (409 NOT 422); (h) `CreateRepairWorkOrderResponse` `{name,status,sla_target_hours}` grounded `imm09.py:786` (KHÔNG `priority`), `status` enum Select-canonical 9.
- `TC-MOB-OAS-17` (C-REQBODY-CREATECAL — class riêng `TestMobileCreateCalibrationBody`, §8.6): (a) `create_calibration.post` có `requestBody` = **`$ref`-ONLY** `requestBodies/CreateCalibrationBody` (**G-OAS-403-DISAMBIG**: gỡ sibling `required:true` ở path-level); (b) component `required:true` + json `$ref` `CreateCalibrationRequest`; (c) `required` EXACT = `[asset, calibration_type, scheduled_date, technician]` (4 không-default @`imm11.py:90-91`); (d) `calibration_type` enum `[External, In-House]` (Select-canonical 1:1 @`imm_asset_calibration.json`); (e) 5 optional có + `is_recalibration` int enum `[0,1]` (Check) + KHÔNG field server-gán (`technician` là tham số THẬT — khác report `source`/repair `requested_by`); (f) content oneOf json+form-urlencoded (CÙNG schema); (g) response surface `200`→`CreateCalibrationCreated`, `401`→`Unauthorized401`, `403`→`Forbidden` (**single-shape**, ≠ `ReportIncidentForbidden`), `404`→`NotFound404`, `409`→`Conflict409`; status-set `[200,401,403,404,409]` (**409 NOT 422** — `IMM11_ASSET_BLOCKED` http_status 409 CAL-008); (h) `CreateCalibrationResponse` `{name,status}` grounded `imm11.py:1015` (**KHÔNG `sla_target_hours`** — khác createRepair), `status` enum Select-canonical 8 (create-time "Scheduled").
- `TC-MOB-OAS-11` (error-response coverage): MỌI **12 path MVP** (10 nghiệp vụ + 2 device-token) declare `401`→`Unauthorized401`; **ĐÚNG 2** path `@rate_limit` (`imm00.resolve_qr_token` `:311` + `imm00.get_asset_scan_info` `:354`) declare `429`→`RateLimited429` (KHÔNG path nào khác — wire chỗ khác = FAIL "bịa hợp đồng"); 3 auth path KHÔNG declare 429. **G-REQBODY:** `404`/`422` wire **ĐÚNG 1 path** = `report_incident` (`404`→`NotFound404` asset∄ `services/imm12.py:361`; `422`→`Unprocessable422` BR-12-01 `services/imm12.py:359`); KHÔNG path NÀO KHÁC declare 404/422 (chống scope-creep). Verify @source: `@rate_limit` ĐÚNG 2 GET QR (`grep rate_limit imm00.py` = `:311/:354` MVP + `:514` regenerate ngoài-MVP). B1: `get_token` có `'400'`→`OAuthError400` (auth status-set {200,400}; authorize=302, revoke=200 GIỮ NGUYÊN).
- `TC-MOB-OAS-12` (error-status-class 401/403 split + body raw): (a) MỌI **12 path MVP** declare `403`; **11 path** → `Forbidden` (single `FrappeRawError`), **G-REQBODY EXEMPT** `report_incident` → `403` = `ReportIncidentForbidden` (DUAL-SHAPE `oneOf [Error, FrappeRawError]` — in-handler cap-403 HTTP-200+Error `imm12.py:96` ≠ dispatcher-403 HTTP-403+FrappeRawError `__init__.py:876`); tập path-403 **==** tập path-401 (12==12 đối xứng — `report_incident` VẪN declare 403, chỉ KHÁC shape); 403 ngoài 12 path = FAIL "bịa hợp đồng". (b) 3 response pre-handler (`Unauthorized401`/`Forbidden`/`RateLimited429`) `$ref` `schemas/FrappeRawError` (KHÔNG `schemas/Error` — anti-regress repoint); `schemas/FrappeRawError` tồn tại + props = `{exc_type*, exception?, exc?, _server_messages?}` (`exc_type` required) DISTINCT vs Error envelope. `ReportIncidentForbidden.oneOf` = `[Error, FrappeRawError]` (BOTH shape). (c) 3 auth path Frappe-core KHÔNG declare 403 (302/200/400). Verify @source: `AuthenticationError` 401 `frappe/exceptions.py:26-27` (raise `auth.py:630`); `PermissionError` 403 `:34-35` (raise `__init__.py:876`); body-field `frappe/utils/response.py` V1 `:46/:43-45/:185/:188`.
- `TC-MOB-OAS-13` (Phase-C `reportIncident` requestBody + response G-REQBODY — class riêng `TestMobileReportIncidentBody`, §8.3): (a) `report_incident.post` có `requestBody` = **`$ref`-ONLY** `requestBodies/ReportIncidentBody` (**G-OAS-403-DISAMBIG**: gỡ sibling `required:true` ở path-level); (b) `requestBodies/ReportIncidentBody` `required:true` + content **oneOf `application/json` + `application/x-www-form-urlencoded`** (CÙNG `$ref` `schemas/ReportIncidentRequest` — Frappe RPC `form_dict` §9); (c) `schemas/ReportIncidentRequest.required` **EXACT** = `[asset, incident_type, severity, description]` (4 field `reqd=1` @`incident_report.json`); (d) `severity` enum = `[Low, Medium, High, Critical]` + `incident_type` enum = `[Failure, Safety Event, Near Miss, Malfunction]` (Select-canonical 1:1 @`incident_report.json`); (e) `asset`/`description` type `string`; `source` **KHÔNG** ở body (server coerce — `imm12.py:83`); (f) **G-REQBODY** response surface BỒI: `200`→`ReportIncidentCreated` (success envelope, `data` `$ref` `ReportIncidentResponse` {name,status,severity} grounded `services/imm12.py:410`; `status` enum Select-canonical 7), `401`→`Unauthorized401`, `403`→`ReportIncidentForbidden` (dual-shape), `404`→`NotFound404`, `422`→`Unprocessable422`; status-set = `[200,401,403,404,422]`.
- `TC-MOB-OAS-14` (C-LISTREAD — Phase-C list-read contract cho 3 list path, class riêng `TestMobileListReadContract`, §8.4): (a) 3 list path RỜI `_STUB_PATHS` (200 != `Stub`) NHƯNG GIỮ `_MVP_BUSINESS_PATHS` (401/403 symmetry 12==12 bất biến); (b) param query đủ + đúng `$ref`: imm08/09 = `filters`+`Page`+`PageSize`, imm12 = `status`+`severity`+`asset`+`open`+`Page`+`PageSize`; (c) `Page`/`PageSize` đúng type+default+min/max (page int default 1 min 1; page_size int default 20 min 1 max 100 — `pagination.py:7-8`); (d) `filters` JSON-string default `'{}'` (imm08/09); `open` int enum `[0,1]` default 0, `status`/`severity`/`asset` string default `''` (imm12); (e) 200 trỏ response RIÊNG (C3-split): imm08→`PmWorkOrderList`, imm09→`RepairWorkOrderList`, imm12→`IncidentList`; 401/403 GIỮ; KHÔNG `requestBody` (GET); (f) `Pm`/`RepairWorkOrderListEnvelope`=`data.{pagination, data[]}`, `IncidentListEnvelope`=`data.{pagination, items[]}`, cả 3 dùng CHUNG `Pagination`; `PaginatedListEnvelope` cũ ĐÃ gỡ; (g) **LIVE introspect** — `page`/`page_size` (+ `filters` / `status,severity,asset,open`) CÓ THẬT trong signature whitelist `imm08.list_pm_work_orders`/`imm09.list_repair_work_orders`/`imm12.list_incidents` (yaml KHÔNG bịa param so với hàm thật).
- `TC-MOB-OAUTH-TOKEN-01..05` (B1 — AUTH-section token-endpoint RESPONSE contract, class riêng `TestMobileOAuthToken`): (01) `getOAuthToken` `'400'`→`OAuthError400`; (02) `OAuthError400` wire **ĐÚNG 1 path** (`getOAuthToken`) + **0 path business** nhận (anti-leak); (03) `OAuthError400` schema-keys = `{error*, error_description?, error_uri?, description?, status_code?}` (`error` required) — DISTINCT vs Error envelope (KHÔNG `success`/`code`/`http_status`); (04) `getOAuthToken` 200-keys = `{access_token*, expires_in*, token_type*, scope?, refresh_token?}` source-characterized (tokens.py:309-326), KHÔNG bọc `{success,data}`; (05) `revoke` 200 empty-object (RFC 7009) + `authorize` 302 + cả 2 KHÔNG 400.

Guard sống ở `assetcore/tests/test_mobile_oas.py` (read-only yaml — KHÔNG đọc auto-gen AssetCore spec `openapi.py`; KHÔNG cài lib). Codegen handoff: [`09-native-repo-guide.md §2.3`](./09-native-repo-guide.md). STUB-status từng path: [`11-phase-a-exit.md §1`](./11-phase-a-exit.md).

### 8.3 Phase-C requestBody + response THẬT — `reportIncident` (path ĐẦU TIÊN rời STUB)

> **C-REQBODY-REPORTINCIDENT → G-REQBODY.** `report_incident` là path **Phase-C đầu tiên** bồi `requestBody` THẬT — rời nhóm STUB (C-REQBODY). **G-REQBODY** đóng tiếp **4 contract-gap codegen** còn sót sau C-REQBODY (USER eval PARTIAL): (1) content-type RPC `form_dict`, (2) 403 dual-shape, (3) vd Guest 401→403, (4) wire 404/422 + bồi response 200 THẬT. Vòng này chỉ đụng **ĐÚNG 1 path** (write-direction); 3 list path = **C-LISTREAD** (read-direction, §8.4); 6 path STUB còn lại (2 QR + `get_asset` + 3 create) GIỮ nguyên (0 `requestBody`, 200→`Stub`).

**Mục tiêu:** chuyển failure-mode "báo hỏng" từ STUB → body+response máy-đọc + codegen-able, KHỚP 1:1 nguồn chân lý DocType + service return (KHÔNG bịa field/enum). Mobile-dev sinh model `ReportIncidentRequest`/`ReportIncidentResponse` từ yaml, gửi đúng kiểu Frappe RPC + parse 200/403/404/422.

**Component bồi (C-REQBODY 2 + G-REQBODY 3 = 5):**
- `schemas/ReportIncidentRequest` — object, `required` EXACT = `[asset, incident_type, severity, description]`.
- `requestBodies/ReportIncidentBody` — wrapper `required:true`, content **oneOf `application/json` + `application/x-www-form-urlencoded`** (CÙNG `$ref` schema trên — Frappe RPC `form_dict`, gap-1 §9). Wire vào `report_incident.post.requestBody` = **`$ref`-ONLY** (G-OAS-403-DISAMBIG: `required` đã ở component, gỡ sibling path-level).
- `schemas/ReportIncidentResponse` (**G-REQBODY**) — object `{name, status, severity}`, `required` EXACT 3, grounded `return` `services/imm12.py:410`. `status` enum **Select-canonical 7** @`incident_report.json` (`[Open, Acknowledged, In Progress, Resolved, RCA Required, Closed, Cancelled]`; create-time = `"Open"` `imm12.py:373`).
- `responses/ReportIncidentCreated` (**G-REQBODY**) — `200` success envelope, `data` `$ref` `ReportIncidentResponse`. Wire `report_incident.post.'200'` (repoint `Stub`→cái này).
- `responses/ReportIncidentForbidden` (**G-REQBODY**) — `403` **DUAL-SHAPE** `oneOf [Error, FrappeRawError]` (§5a/§5b). Wire `report_incident.post.'403'` (repoint `Forbidden`→cái này — KHÁC 11 path còn lại). Note: **in-handler cap-403 ≠ `Forbidden` component**.
- **wire `responses/NotFound404`** (`404`, asset∄ `IMM12_ASSET_NOT_FOUND` `services/imm12.py:361`) + **`responses/Unprocessable422`** (`422`, BR-12-01 Critical→`clinical_impact` `services/imm12.py:359`) — GỠ CẢ 2 khỏi RESERVED (§8.2).

**Bảng field (nguồn chân lý = `incident_report.json` + `imm12.py:71-84`):**

| Field | Type (OpenAPI) | Required | enum (Select-canonical) | `@source` |
|---|---|---|---|---|
| `asset` | `string` | ✅ | — (Link `AC Asset`) | `incident_report.json` `asset` (`Link`, `reqd=1`) · `imm12.py:72` |
| `incident_type` | `string` | ✅ | `[Failure, Safety Event, Near Miss, Malfunction]` | `incident_report.json` `incident_type` (`Select`, options 4) · `imm12.py:73` |
| `severity` | `string` | ✅ | `[Low, Medium, High, Critical]` | `incident_report.json` `severity` (`Select`, options 4) · `imm12.py:74` |
| `description` | `string` | ✅ | — (Text Editor — HTML/text) | `incident_report.json` `description` (`Text Editor`, `reqd=1`) · `imm12.py:75` |

> **`source` KHÔNG ở requestBody** — provenance nguồn báo hỏng (`'qr-scan'`/`'manual'`) do **server gán/coerce** (`imm12.py:83` default `'manual'`; tầng mobile coerce `'qr-scan'`), client **KHÔNG gửi**. Đưa `source` vào body = leak field server-controlled ⇒ guard `TC-MOB-OAS-13(e)` chặn.
>
> **8 param optional còn lại** (`fault_code`/`workaround_applied`/`clinical_impact`/`patient_affected`/`patient_impact_description`/`immediate_action`/`linked_repair_wo` + `source`) = **Phase-C kế** — CHƯA bồi vòng này (giữ surface tối thiểu = 4 field bắt buộc). enum/required KHỚP 1:1 DocType, KHÔNG bịa.

**Response surface SAU G-REQBODY (đối chiếu `TC-MOB-OAS-13f/g/h`):**

| Status | `$ref` | Body / shape | `@source` |
|---|---|---|---|
| `200` | `responses/ReportIncidentCreated` | success envelope `{success:true, data:{name,status,severity}}` | `services/imm12.py:410` |
| `401` | `responses/Unauthorized401` | `FrappeRawError` (bearer hết-hạn) | §5 row 401 |
| `403` | `responses/ReportIncidentForbidden` | **DUAL-SHAPE** `oneOf [Error, FrappeRawError]` (in-handler cap-403 HTTP-200+Error `imm12.py:96` ∪ dispatcher-403 HTTP-403+FrappeRawError `__init__.py:876`) | §5a/§5b |
| `404` | `responses/NotFound404` | Error envelope `code=NOT_FOUND` (asset∄) | `services/imm12.py:361` |
| `422` | `responses/Unprocessable422` | Error envelope `code=VALIDATION\|BUSINESS_RULE` (BR-12-01) | `services/imm12.py:359` |

**Bất biến vòng này:**
- **Symmetry BẤT BIẾN 12==12:** `report_incident` RỜI `_STUB_PATHS` (đã có `requestBody` + 200≠Stub) NHƯNG GIỮ `_MVP_BUSINESS_PATHS` ⇒ vẫn declare 401 ∧ 403 ⇒ tập-401 == tập-403 == 12 path MVP. 403 dual-shape (`ReportIncidentForbidden`) VẪN là declare-403 ⇒ KHÔNG vỡ symmetry.
- **Orphan 9→7:** `NotFound404`/`Unprocessable422` wire vào path ⇒ hết-orphan → GỠ khỏi allow-list `_RESERVED_ORPHANS` + §8.2 (đồng bộ 1 nhịp; nếu để lại = stale → `TC-MOB-OAS-10(b)` ĐỎ). 3 component report mới (`ReportIncidentResponse`/`ReportIncidentCreated`/`ReportIncidentForbidden`) `$ref`'d NGAY ⇒ KHÔNG orphan, KHÔNG vào allow-list; 0 dangling `$ref`.
- **gap-1 form_dict:** `ReportIncidentBody.content` khai oneOf json+form-urlencoded ⇒ codegen sinh client gọi đúng kiểu Frappe RPC (KHÔNG field rỗng). **gap-3:** §9 vd (d) Guest = 403 (KHÔNG 401; `imm12.py:91-92 _err(401)` dead-code over HTTP).

### 8.4 Phase-C list-read THẬT — 3 list path (read-direction, C-LISTREAD)

> **C-LISTREAD.** Sau `report_incident` (write-direction, §8.3), 3 list path **read-direction** rời STUB: `imm08.list_pm_work_orders` · `imm09.list_repair_work_orders` · `imm12.list_incidents`. Vòng này bồi **pagination query-param** + **200→list-envelope THẬT** (rời `Stub`). KHÔNG đụng `requestBody` (list = GET). 6 path STUB còn lại (2 QR + `get_asset` + 3 create) GIỮ nguyên.

**Mục tiêu:** "phiếu của tôi" (PM/CM/Incident) trả contract phân trang máy-đọc, codegen-able — mobile-dev sinh model list + iterate trang đúng `total_pages`. KHỚP 1:1 signature LIVE (KHÔNG bịa param) + rows-key THẬT @source (KHÔNG ép 1 key giả).

**Param query bồi (§6.1):** `Page`/`PageSize` (cả 3) + `WorkOrderFilters` (imm08/09, JSON-string) + `IncidentStatus`/`IncidentSeverity`/`IncidentAsset`/`IncidentOpen` (imm12). Tái dùng component, KHÔNG inline trùng.

**Envelope bồi (§6.2 — 2 PHÂN BIỆT theo rows-key):**
- `schemas/PmWorkOrderListEnvelope` (`data.{pagination, data[]}`, item `PmWorkOrderListItem`) ← imm08 — wrapper `responses/PmWorkOrderList` (200). [C3-split]
- `schemas/RepairWorkOrderListEnvelope` (`data.{pagination, data[]}`, item `RepairWorkOrderListItem`) ← imm09 — wrapper `responses/RepairWorkOrderList` (200). [C3-split]
- `schemas/IncidentListEnvelope` (`data.{pagination, items[]}`) ← imm12 — wrapper `responses/IncidentList` (200).
- `Pagination` sub-schema DÙNG CHUNG (không đổi).

**Bất biến vòng này (đối chiếu `TC-MOB-OAS-14`):**
- 3 list path GIỮ `401→Unauthorized401` + `403→Forbidden` — **chỉ THÊM param + đổi 200**; KHÔNG `requestBody`; status-set = `[200, 401, 403]`.
- **Symmetry BẤT BIẾN 12==12:** 3 list RỜI `_STUB_PATHS` (200 != `Stub`) NHƯNG GIỮ `_MVP_BUSINESS_PATHS` ⇒ vẫn declare 401 ∧ 403 ⇒ tập-401 == tập-403 == 12 path MVP.
- **Orphan 10→9:** `PaginatedListEnvelope` cũ xoá (đã tách 2 envelope) ⇒ gỡ khỏi allow-list `_RESERVED_ORPHANS`; 11 component mới `$ref`'d NGAY ⇒ KHÔNG orphan. **KHÔNG** wire `NotFound404`/`Unprocessable422` (vẫn reserve); 0 dangling `$ref`.
- **KNOWN-GAP Phase-E:** rows-key `data` (imm08/09) vs `items` (imm12) hợp nhất về 1 key = Phase-E normalize (đụng service `.py` + test BE) — §6.2 + [ADR-MOBILE-001 (g)](./ADR-MOBILE-001.md). C-LISTREAD KHÔNG sửa service.

---

### 8.5 Phase-C requestBody + response THẬT — `createRepairWorkOrder` (write-direction, C-REQBODY-CREATEREPAIR)

> **C-REQBODY-CREATEREPAIR.** Path Phase-C **THỨ HAI** rời STUB (sau `report_incident` §8.3), tái dùng template G-REQBODY (requestBody oneOf content + typed 200 + 404/4xx). 4 path STUB còn lại sau vòng này: 2 QR + `get_asset` + `createPmWorkOrder` + `createCalibration` (backlog Phase-C kế).

**Mục tiêu:** mobile-dev gen client POST tạo CM với payload đúng (4 field bắt buộc + enum) + nhận response typed `{name, status, sla_target_hours}` + biết trước contract lỗi create-time (asset∄ → 404, asset đã có WO mở → 409). KHỚP 1:1 signature LIVE `imm09.py:36-38` (KHÔNG bịa param) + enum Select-canonical @`asset_repair.json`.

**Component bồi:**
- `schemas/CreateRepairWorkOrderRequest` — `required` **EXACT** = `[asset_ref, repair_type, priority, failure_description]` (4 tham số không-default @`imm09.py:36-38`). `repair_type` enum = `[Corrective, Breakdown, Warranty Repair]`; `priority` enum = `[Normal, Urgent, Emergency]` (Select-canonical 1:1 @`asset_repair.json`; `priority` khớp khoá `_SLA_MATRIX` `imm09` services). 3 optional `incident_report`/`source_pm_wo`/`fault_image` (default `""`). `requested_by` **KHÔNG** ở body (server gán `session.user` — `imm09.py:770`).
- `requestBodies/CreateRepairWorkOrderBody` — `required:true`, content **oneOf `application/json` + `application/x-www-form-urlencoded`** (CÙNG `$ref` `CreateRepairWorkOrderRequest` — Frappe RPC `form_dict`, §9). Mirror đúng pattern `ReportIncidentBody`.
- `schemas/CreateRepairWorkOrderResponse` — `{name, status, sla_target_hours}` grounded `services/imm09.py:786`. `status` enum Select-canonical 9 (create-time `"Open"` = `RepairStatus.OPEN`); `sla_target_hours` = giờ SLA `_SLA_MATRIX(risk_class, priority)` (`imm09.py:112`, BR-09-05).
- `responses/CreateRepairWorkOrderCreated` — success envelope (HTTP-200), `data` `$ref` `CreateRepairWorkOrderResponse`. Wire `200` (repoint `Stub`→cái này).

**Status-set `create_repair_work_order.post` = `[200, 401, 403, 404, 409]`:**

| HTTP | `$ref` | Body / shape | Nguồn |
|---|---|---|---|
| `200` | `responses/CreateRepairWorkOrderCreated` | Success envelope, `data` = `{name, status, sla_target_hours}` | `imm09.py:786` |
| `401` | `responses/Unauthorized401` | `FrappeRawError` pre-handler (bearer hết hạn) | §5b |
| `403` | `responses/Forbidden` | **SINGLE-SHAPE** `FrappeRawError` @HTTP-line **403** (`rbac.require('repair.create')` → `frappe.throw(PermissionError)` `imm09.py:40`, exceptions.py:35) | §5/§5b |
| `404` | `responses/NotFound404` | Error envelope `code=NOT_FOUND` @HTTP-200 quirk (asset∄ `IMM09_ASSET_NOT_FOUND` `services/imm09.py:746`) | §5 |
| `409` | `responses/Conflict409` | Error envelope `code=CONFLICT` @HTTP-200 quirk (asset đã có WO mở `IMM09_ASSET_HAS_OPEN_WO` `services/imm09.py:753`, http_status **409** `messages.py:667`) | §5 |

**⚠️ 3 SELF-CORRECTION delta vs đề mục (BA bám SOURCE, KHÔNG bám chữ đề mục):**
- **(d1) Response data = `{name, status, sla_target_hours}`, KHÔNG `priority`.** Đề mục viết "200→Created typed (name/status/priority @service return)" — SAI: `services/imm09.py:786` trả `sla_target_hours` (KHÔNG `priority`). Doc khai đúng return THẬT (codegen JSON-only client deser theo schema sai → field thiếu).
- **(d2) 403 = SINGLE-SHAPE `Forbidden`, KHÔNG dual-shape.** Đề mục viết "403→oneOf Error|FrappeRawError" như `report_incident`. SAI: `report_incident` dùng `rbac.can + _err(403)` (in-handler HTTP-200+Error) ⇒ dual-shape; `create_repair_work_order` dùng `rbac.require('repair.create')` `imm09.py:40` → `frappe.throw(PermissionError)` @HTTP-line **403 THẬT** (raw `FrappeRawError`) ⇒ ĐỒNG shape dispatcher-403 = `Forbidden` component (KHÔNG `ReportIncidentForbidden`). Khai dual-shape = hứa nhánh in-handler-200 KHÔNG BAO GIỜ xảy ra → codegen route sai. *(Ghi chú phụ: `rbac.require` leak raw cap-name vào message `imm09.py:40` — pre-existing, KHÔNG sửa code vòng này; cân nhắc parity với `report_incident` no-leak ở backlog BE.)*
- **(d3) Business-block = `409` Conflict, KHÔNG `422`.** Đề mục viết "422→Unprocessable422 grounded IMM09_ASSET_HAS_OPEN_WO". SAI: message-code `IMM09_ASSET_HAS_OPEN_WO` map `http_status=409` (`messages.py:667`) = state CONFLICT (`_HTTP_TO_BUCKET[409]=CONFLICT` `notify.py:42`), KHÔNG validation 422. Wire `409→Conflict409` (component đã có, gỡ khỏi RESERVED).

**Bất biến vòng này (đối chiếu `TC-MOB-OAS-16` + `TC-MOB-OAS-07/10/11/12`):**
- `create_repair_work_order` RỜI `_STUB_PATHS` (có `requestBody` + 200 != `Stub`) NHƯNG GIỮ `_MVP_BUSINESS_PATHS` ⇒ declare 401 ∧ 403 ⇒ **symmetry 12==12 BẤT BIẾN**. STUB: **5→... thực chất 9→5** (report + 3 list + createRepair đã rời).
- 403 dùng `Forbidden` (single-shape) ⇒ KHÔNG bị `TC-MOB-OAS-12` (a) exempt như `report_incident` — đi thẳng nhánh "11 path → Forbidden".
- **Orphan 7→6:** `Conflict409` wire vào path ⇒ hết-orphan → GỠ khỏi allow-list `_RESERVED_ORPHANS` + §8.2 (đồng bộ 1 nhịp; để lại = stale → `TC-MOB-OAS-10(b)` ĐỎ). 3 component mới (`CreateRepairWorkOrderRequest`/`...Response`/`...Created` + 1 requestBody `...Body`) `$ref`'d NGAY ⇒ KHÔNG orphan; `NotFound404` tái dùng từ G-REQBODY (vẫn referenced); 0 dangling `$ref`.
- **KHÔNG sửa service/api `.py`** (doc/yaml/test introspect-only). Sau vòng C-REQBODY-CREATEREPAIR, `createPmWorkOrder`/`createCalibration` + 2 QR + `getAsset` GIỮ STUB; **`createCalibration` ĐÃ rời STUB ở vòng kế (C-REQBODY-CREATECAL — §8.6)** ⇒ hiện chỉ còn 4 STUB (2 QR + `getAsset` + `createPmWorkOrder`).

### 8.6 Phase-C requestBody + response THẬT — `createCalibration` (write-direction, C-REQBODY-CREATECAL)

> **C-REQBODY-CREATECAL.** Path Phase-C **THỨ BA** rời STUB (sau `report_incident` §8.3 + `createRepairWorkOrder` §8.5) — **hoàn tất bộ-ba create** (báo hỏng → sửa chữa → hiệu chuẩn), tái dùng template C-REQBODY-CREATEREPAIR (requestBody oneOf content + typed 200 + 404/409). **4 path STUB còn lại** sau vòng này: 2 QR + `get_asset` + `createPmWorkOrder` (`createPmWorkOrder` = Self-Correction kế — untyped `_form_dict`, required `asset_ref`/`pm_schedule`/`due_date`).

**Mục tiêu:** mobile-dev gen client POST tạo phiếu hiệu chuẩn với payload đúng (4 field bắt buộc + enum) + nhận response typed `{name, status}` + biết trước contract lỗi create-time (asset∄ → 404, asset lifecycle blocked ∧ không-recalibration → 409). KHỚP 1:1 signature LIVE `imm11.py:90-94` (KHÔNG bịa param) + enum Select-canonical @`imm_asset_calibration.json`.

**Component bồi:**
- `schemas/CreateCalibrationRequest` — `required` **EXACT** = `[asset, calibration_type, scheduled_date, technician]` (4 tham số không-default @`imm11.py:90-91`). `calibration_type` enum = `[External, In-House]` (Select-canonical 1:1 @`imm_asset_calibration.json` — options nguyên văn `'External\nIn-House'`, KHÔNG bịa giá trị). 5 optional `calibration_schedule`/`lab_supplier`/`is_recalibration`/`reference_standard_serial`/`traceability_reference` (default null @`imm11.py:91-94`). `is_recalibration` = Check (int enum `[0,1]`) — `=1` ⇒ BYPASS business-block khi asset blocked (`imm11.py:1001`). **KHÔNG field server-gán** ở body (`technician` là tham số THẬT của signature — KHÁC `report_incident` `source` / `createRepair` `requested_by` bị server-coerce).
- `requestBodies/CreateCalibrationBody` — `required:true`, content **oneOf `application/json` + `application/x-www-form-urlencoded`** (CÙNG `$ref` `CreateCalibrationRequest` — Frappe RPC `form_dict`, §9). Mirror đúng pattern `CreateRepairWorkOrderBody`.
- `schemas/CreateCalibrationResponse` — `{name, status}` grounded `services/imm11.py:1015` (return `{name, status}` — **CHỈ 2 field, KHÔNG `sla_target_hours`** khác createRepair; lịch/SLA thuộc IMM Calibration Schedule riêng). `status` enum Select-canonical 8 (create-time `"Scheduled"` = `CalibrationResult.SCHEDULED` `imm11.py:1013`, = doctype default @`imm_asset_calibration.json`).
- `responses/CreateCalibrationCreated` — success envelope (HTTP-200), `data` `$ref` `CreateCalibrationResponse`. Wire `200` (repoint `Stub`→cái này).

**Status-set `create_calibration.post` = `[200, 401, 403, 404, 409]`:**

| HTTP | `$ref` | Body / shape | Nguồn |
|---|---|---|---|
| `200` | `responses/CreateCalibrationCreated` | Success envelope, `data` = `{name, status}` (status init `"Scheduled"`) | `imm11.py:1015` |
| `401` | `responses/Unauthorized401` | `FrappeRawError` pre-handler (bearer hết hạn) | §5b |
| `403` | `responses/Forbidden` | **SINGLE-SHAPE** `FrappeRawError` @HTTP-line **403** (`rbac.require('calibration.create')` → `frappe.throw(PermissionError)` `imm11.py:95`, exceptions.py:35) | §5/§5b |
| `404` | `responses/NotFound404` | Error envelope `code=NOT_FOUND` @HTTP-200 quirk (asset∄ `IMM11_ASSET_NOT_FOUND` `services/imm11.py:999`, http_status 404 `messages.py:853`) | §5 |
| `409` | `responses/Conflict409` | Error envelope `code=CONFLICT` @HTTP-200 quirk (asset lifecycle ∈ `BLOCKED_FOR_WO` ∧ NOT `is_recalibration` — `IMM11_ASSET_BLOCKED` `services/imm11.py:1002`, http_status **409** CAL-008 `messages.py:860`) | §5 |

**⚠️ 2 SELF-CORRECTION delta vs đề mục (BA bám SOURCE, KHÔNG bám chữ đề mục):**
- **(c1) 403 = SINGLE-SHAPE `Forbidden`, KHÔNG dual-shape.** Đề mục ĐÚNG ở điểm này (ghi rõ "403 = dispatcher-single-shape, KHÔNG dual như report") — xác nhận @source: `create_calibration` dùng `rbac.require('calibration.create')` `imm11.py:95` → `frappe.throw(PermissionError)` @HTTP-line **403 THẬT** (raw `FrappeRawError`, exceptions.py:35) TRƯỚC `handle()`. KHÔNG có in-handler `_err(403)` ⇒ ĐỒNG shape dispatcher-403 = `Forbidden` component (KHÔNG `ReportIncidentForbidden`). KHÁC `report_incident` (dùng `rbac.can + _err(403)` in-handler → dual-shape).
- **(c2) Business-block = `409` Conflict, KHÔNG `422`.** Đề mục viết "422→Unprocessable422 (IMM11_ASSET_BLOCKED) + KHÔNG wire Conflict409 (calibration KHÔNG có open-WO gate)". **SAI @source**: message-code `IMM11_ASSET_BLOCKED` map `http_status=409` CONFLICT (`messages.py:860`, `_HTTP_TO_BUCKET[409]=CONFLICT` `notify.py:42`); `handle()` pass-through `http_status` (`api_handler.py:61`) ⇒ surface **HTTP-409 THẬT** (KHÔNG 422). Lập luận "không-open-WO-gate → không-409" nhầm *cơ-chế* với *HTTP-status*: HTTP-409 do message-code quyết định, KHÔNG do open-WO. Calibration-409 (lifecycle-block CAL-008, business-rule) KHÁC nguyên-nhân createRepair-409 (open-WO) nhưng **CÙNG HTTP-409** ⇒ tái dùng `Conflict409`. Phân biệt rõ với 404 (asset-existence): **404 = asset KHÔNG tồn tại** (`IMM11_ASSET_NOT_FOUND`) vs **409 = asset TỒN TẠI nhưng lifecycle blocked ∧ không-recalibration** (`IMM11_ASSET_BLOCKED`).

**Bất biến vòng này (đối chiếu `TC-MOB-OAS-17` + `TC-MOB-OAS-07/10/11/12`):**
- `create_calibration` RỜI `_STUB_PATHS` (có `requestBody` + 200 != `Stub`) NHƯNG GIỮ `_MVP_BUSINESS_PATHS` ⇒ declare 401 ∧ 403 ⇒ **symmetry 12==12 BẤT BIẾN** (KHÔNG tụt 11). STUB: **5→4** (2 QR + `get_asset` + `createPmWorkOrder`).
- 403 dùng `Forbidden` (single-shape) ⇒ KHÔNG bị `TC-MOB-OAS-12` (a) exempt như `report_incident` — đi thẳng nhánh "11 path → Forbidden".
- **Orphan GIỮ 6:** `Conflict409`/`NotFound404` ĐÃ referenced (createRepair/report wire trước, nay calibration tái dùng — KHÔNG đụng allow-list `_RESERVED_ORPHANS` + §8.2). 4 component mới (`CreateCalibrationRequest`/`...Response`/`...Created` + 1 requestBody `...Body`) `$ref`'d NGAY ⇒ KHÔNG orphan; 0 dangling `$ref`.
- **KHÔNG sửa service/api `.py`** (doc/yaml/test introspect-only). `createPmWorkOrder` + 2 QR + `getAsset` GIỮ STUB (out-of-scope → Phase-C kế). **Phần LIVE HTTP (path serve) chờ USER reload gunicorn — blocker đứng, KHÔNG phải việc vòng này.**

---

### 8.7 R4 — TYPED reads/create + ROADMAP device-token (rời STUB: 4→2 device-token)

> **R4 §8.7 (factory-run3-apidocs P1-3).** Đề mục đóng 3 P1: (1) bỏ boolean-discriminator illegal (§5c), (2) **type `data` cho 4 STUB read/create GROUNDED chữ-ký service THẬT**, (3) Swagger UI dev-fallback (ADR-IMM00-OPENAPI §D18). Mục này = phần (2).

**4 path rời STUB với `data` typed — KHÔNG bịa field (đọc service return THẬT):**

| Path (operationId) | 200 (oneOf) | `data` schema GROUNDED @source | Field |
|---|---|---|---|
| `imm00.resolve_qr_token` (`resolveQrToken`) | oneOf `[QrResolveEnvelope \| Error]` (**C6** §5c read-path) | `QrResolveResult` ← `services/imm00.py:303-315` | `name, asset_code, lifecycle_status, device_model_name, location_name` |
| `imm00.get_asset_scan_info` (`getAssetScanInfo`) | oneOf `[AssetScanInfoEnvelope \| Error]` (**C6** §5c read-path) | `AssetScanInfo` ← `services/imm00.py:567-602` | `name, asset_code, asset_name, lifecycle_status, device_model_name, location_name, next_pm_date?, next_calibration_date?, pm_overdue, calibration_overdue, recent_maintenance?, available_actions[]` |
| `imm00.get_asset` (`getAsset`) | oneOf `[AssetDetailEnvelope \| Error]` (**C6** §5c read-path) | `AssetDetail` ← `api/imm00.py:288-324` (AC Asset `as_dict()` enrich + 2 overdue) | core: `name, asset_code, lifecycle_status, *_name…, next_*_date?, pm_overdue, calibration_overdue` (`additionalProperties:true` vì `as_dict()` surface field doctype denormalized) |
| `imm08.create_pm_work_order` (`createPmWorkOrder`) | oneOf `[CreatePmWorkOrderCreatedEnvelope \| Error]` (§5c) | `CreatePmWorkOrderResponse` ← `services/imm08.py:836-840` | `name, status, checklist_items_count` |

> 🔵 **C6 — read-path P1 closure (2026-06-11):** 3 GET read 200 ĐÃ ĐỔI từ single `$ref <ReadEnvelope>` → **oneOf `[<ReadEnvelope>, Error]`** CLOSED-SCHEMA Decision-B (KHÔNG discriminator, mirror create §5c). LÝ DO: in-handler business error của 3 read **arrive HTTP-200 + Error body** — y hệt create-path P1: **404** (`_err(…,404)` — `get_asset` `imm00.py:297` / `resolve_qr_token` `imm00.py:366` / `get_asset_scan_info` `imm00.py:416,425`) + **vendor-IDOR-403** (`assert_vendor_can_access` → `ServiceError(FORBIDDEN)` **caught** → `_err(e.message, e.code)` — `get_asset` `imm00.py:302` / `resolve` `imm00.py:371` / `scan-info` `imm00.py:421`). TRƯỚC C6, 200 single-`$ref` ⇒ codegen KHÔNG có deser-branch `Error` cho read → in-handler 404/403 = **dead-deser**. Sau C6, 2 nhánh máy-phân-biệt bằng `additionalProperties:false` (ENVELOPE-level) + disjoint required-set (`[success,data]` vs `[success,error,code,http_status]`) ⇒ codegen route ĐÚNG theo `body.success`/`body.http_status` (KHÔNG cần discriminator boolean — illegal OAS 3.x). **dispatcher-403** (guest/no-token; `resolve`/`scan-info` thêm `rbac.require('asset.read')`; `getAsset` whitelist-only) GIỮ status-line key `403` (trip TRƯỚC `handle()`). `getAsset.data` (`AssetDetail`) GIỮ `additionalProperties:true` (as_dict surface field) — KHÔNG ảnh hưởng disjoint vì ĐÓNG ở tầng **envelope**. Guard: `TC-MOB-OAS-24a..d` (`TestMobileRead200OneOfClosed`) + `TC-MOB-OAS-20a` cập nhật.

- **`AvailableAction`** (element của `available_actions[]`) = shape CHÍNH XÁC `{key, label, route, enabled, reason}` ← `_build_available_actions` (`services/imm00.py:528-534`); `enabled = has_cap ∩ lifecycle_allows` (SSoT). **KHÔNG chứa `qr_token`** (no-raw-token parity).
- **`pm_overdue`/`calibration_overdue`** = **SERVER-FLAG SSoT** (`_is_pm_overdue`/`_is_calibration_overdue`, tz-safe, exempt BLOCKED_FOR_WO) — FE **CHỈ render cờ**, KHÔNG so ngày client (memory: overdue-server-flag-SSoT).
- **`createPmWorkOrder`**: 200 = oneOf `[Created | Error]` (§5c) — in-handler 422 (thiếu field/schedule-mismatch `imm08.py:791,802`) + 404 (PM Schedule∄ `imm08.py:800`) + 409 (asset BAD_STATE `imm08.py:815`) arrive HTTP-200 body. 403 = single-shape `Forbidden` (`rbac.require('pm.create')` `imm08.py:92` dispatcher-403). requestBody = form_dict required `[asset_ref, pm_schedule, due_date]` (`imm08.py:788`) — typed requestBody schema = **backlog Phase-C kế** (R4 type RESPONSE trước).

**🟢 2 device-token = TYPED ở EPIC-D D4 (Vòng 17) — service D2 ĐÃ tồn tại @source ⇒ GỠ STUB. Xem §8.9 dưới.**

- `mobile.v1.register_device_token` / `mobile.v1.unregister_device_token` — **R4 còn STUB** vì handler+service CHƯA tồn tại. **EPIC-D D2** (Vòng 16) tạo `services/mobile_device_token.py` (3-tier, GROUNDED) ⇒ **D4** (Vòng 17) type `data` GROUNDED chữ-ký service THẬT (KHÔNG còn bịa). Chi tiết §8.9.

**Bất biến vòng này (đối chiếu `TC-MOB-OAS-20` + `TC-MOB-OAS-07`):**
- STUB: **4→2** (R4 còn 2 device-token; **D4 §8.9 đưa về 0**). 4 typed path rời `_STUB_PATHS` (→ hằng `_TYPED_READ_PATHS` + `_CREATE_PM_PATH`) NHƯNG GIỮ `_MVP_BUSINESS_PATHS` ⇒ **symmetry 401/403 (12==12) BẤT BIẾN**.
- 9 component mới (`QrResolveResult/QrResolveEnvelope/AvailableAction/AssetScanInfo/AssetScanInfoEnvelope/AssetDetail/AssetDetailEnvelope/CreatePmWorkOrderResponse/CreatePmWorkOrderCreatedEnvelope`) `$ref`'d NGAY ⇒ KHÔNG orphan; 0 dangling `$ref`. `responses/Stub` VẪN referenced (2 device-token) ⇒ KHÔNG orphan.
- **🔵 C6 update (2026-06-11):** R4 ban đầu khai 3 read 200 = single `$ref <ReadEnvelope>`. C6 đổi thành **oneOf `[<ReadEnvelope>, Error]`** (read-path P1 closure — xem §5c/§8.7-note). 3 `<ReadEnvelope>` GIỮ NGUYÊN (`$ref` trong oneOf, KHÔNG orphan); thêm nhánh `schemas/Error` (đã tồn tại). `TC-MOB-OAS-20a` cập nhật (single-$ref → oneOf); `_codegen_dry_introspect` read-branch cập nhật (single-$ref → oneOf chứa Env+Error) để C5 GIỮ GREEN. Symmetry 401/403 BẤT BIẾN (read GIỮ trong `_MVP_BUSINESS_PATHS`).
- **KHÔNG sửa service/api `.py`** (doc/yaml/test introspect-only). Path serve LIVE HTTP chờ USER reload gunicorn — blocker đứng.

---

### 8.8 C5 — codegen-readiness (DoD codegen-dry verify · AUTO introspection proxy)

> **C5 (EPIC-C DoD).** Chốt codegen-readiness bằng **introspection proxy PyYAML STDLIB** (KHÔNG `java`/`npx`) = proxy CHÍNH-THỨC cho codegen-DoD tới khi USER cấp toolchain. Guard sống ở `assetcore/tests/test_mobile_oas.py` class `TestMobileCodegenDryDoD` (`TC-MOB-OAS-23a..e`).

**STUB-count (đối chiếu `TC-MOB-OAS-23b/07`):**
- **10 path MVP-business = 0 Stub** (typed `data` qua `$ref` schema cụ thể): 3 typed read (`resolveQrToken`/`getAssetScanInfo`/`getAsset` — **sau C6: 200 = oneOf `[<ReadEnvelope>, Error]`**, mỗi nhánh `$ref` typed) + `createPmWorkOrder` + `reportIncident` + `createRepairWorkOrder` + `createCalibration` (4 create: 200 = oneOf `[<Created>, Error]`) + 3 list (`list_pm_work_orders`/`list_repair_work_orders`/`list_incidents`). `_codegen_dry_introspect` read-branch (`TC-MOB-OAS-23d`) nhận diện read-oneOf = typed (chứa `<ReadEnvelope>` + `Error`) — C5 GIỮ GREEN sau C6.
- **2 device-token = TYPED ở EPIC-D D4 (Vòng 17)** (`register`/`unregister_device_token`) — service D2 ĐÃ tồn tại @source ⇒ 200 = oneOf `[<Created>, Error]` (KHÔNG còn `Stub`). `_STUB_PATHS` NAY = ∅ (0 STUB-on-MVP toàn bộ 12 path). `TC-MOB-OAS-23b` cập nhật: device-token RỜI Stub. `responses/Stub` HẾT referenced → forward-reserve trong `_RESERVED_ORPHANS` (negative-injection guard 23d/24e). Xem §8.9.

**3 guard introspection (chạy KHÔNG-toolchain — `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = 108 OK, count HIỆN HÀNH @source Vòng 11 2026-06-11):**
- **(a / Guard-1)** 0 path MVP còn trỏ `responses/Stub` (KHÔNG Stub-envelope free-form).
- **(b / Guard-2)** 0 dangling `$ref` toàn spec (mọi `$ref` resolve về node tồn tại — tiền-đề codegen).
- **(c / Guard-3)** mỗi 10 path MVP có 200-`data` TYPED `$ref`: read=`*Envelope.data` $ref; create=`oneOf [<CreatedEnvelope>, Error]` mỗi nhánh $ref (closed-schema Decision-B); list=response-component→`*Envelope` $ref. KHÔNG generic `{type:object}`.

**Trạng thái toolchain THẬT (KHÔNG tuyên bố "codegen verified" khi chưa chạy generator):**

| Lớp | Cách kiểm | Trạng thái @2026-06-11 |
|---|---|---|
| **Proxy (AUTO)** | `TestMobileCodegenDryDoD` introspection PyYAML STDLIB | ✅ **XANH** (108 OK count HIỆN HÀNH @source Vòng 11) — 3 guard PASS. Đây KHÔNG phải codegen THẬT, là **proxy** cho codegen-DoD |
| **Codegen THẬT** | `npx @openapitools/openapi-generator-cli generate` (đọc `openapitools.json` 3 target) | ❌ **CHƯA chạy** — `java` **NOT FOUND** + generator chưa cài (npx canceled). `[HARD-STOP USER]` → EPIC-V V-U1/V-U2 |

> ⚠️ **Phân biệt rõ:** introspection PyYAML XANH **KHÔNG đồng nghĩa** "codegen Dart/Kotlin verified". Nó khẳng-định spec **đủ điều kiện cần** để codegen (0 Stub-on-MVP · 0 dangling · typed data). Verify **đủ điều kiện đủ** (generator sinh model deser route-by closed-schema thật) = EPIC-V THẬT khi USER cấp `java`+`npx`. `openapitools.json` nay là **runnable-config** (3 generator block: `mobile-dart`/`mobile-kotlin`/`mobile-typescript` trỏ spec) — chuẩn bị handoff V.

---

### 8.9 EPIC-D / D4 — device-token TYPED (gỡ 2 STUB cuối · wrap service D2)

> **EPIC-D D4 (Vòng 17).** Sau D2 (Vòng 16) tạo `services/mobile_device_token.py` (3-tier, GROUNDED), D4 type `data` cho 2 device-token path **GROUNDED chữ-ký service THẬT** (KHÔNG còn `[ROADMAP]` bịa). Handler `api/mobile/v1/device_token.py` (BE impl cùng round) chỉ **wrap service D2** qua `utils/api_handler.handle` — KHÔNG nhồi logic vào controller (CLAUDE.md §15). Sau D4: `_STUB_PATHS = ∅` (0 STUB-on-MVP toàn bộ 12 path).

**2 path rời STUB với `data` typed — đọc service return THẬT (`services/mobile_device_token.py`):**

| operationId | Verb | requestBody | 200 oneOf nhánh Created | `data` (GROUNDED) |
|---|---|---|---|---|
| `registerDeviceToken` | POST | `DeviceTokenBody` (`DeviceTokenRequest`) | `RegisterDeviceTokenCreatedEnvelope` | `string` = `name` (hash record, `mobile_device_token.py:153/166` → `_ok(name)`) |
| `unregisterDeviceToken` | POST | `DeviceTokenBody` (`DeviceTokenRequest`) | `UnregisterDeviceTokenAckEnvelope` | `null` (ack thuần — `unregister` trả `None` → `_ok(None)`, `mobile_device_token.py:172`) |

**`DeviceTokenRequest` (request, closed-schema `additionalProperties:false`):**

- `fcm_token` (**reqd** — khóa dedup UNIQUE, `mobile_device_token.py:94`).
- `platform` enum `[android, ios]` (**reqd khi register** — Select-canonical `_VALID_PLATFORMS` `mobile_device_token.py:56`; unregister bỏ qua).
- `device_label?` / `app_version?` (optional telemetry).
- **KHÔNG có `user`** — server **ÉP** `frappe.session.user` (signature service KHÔNG nhận `user`; `**_ignore` nuốt kwargs lạ → client KHÔNG chọn được chủ token, **chống spoof §6.2**). Client gửi `user` = no-op.
- `content` oneOf `application/json` + `application/x-www-form-urlencoded` (CÙNG `$ref` — Frappe RPC `form_dict`, §9).

**Response 200 = oneOf `[<Created>, Error]` CLOSED-SCHEMA route-by-VALUE (Decision-B §5c, KHÔNG discriminator):**

- Nhánh Created (`success.enum:[true]`, required `[success, data]`) ∩ nhánh Error (`success.enum:[false]`, required `[success, error, code, http_status]`) = ∅ → 2 nhánh disjoint required-set + closed ⇒ codegen route ĐÚNG theo **GIÁ TRỊ** `body.success` (KHÔNG cần discriminator boolean illegal).
- in-handler `422 VALIDATION` (register: `fcm_token` rỗng / `platform` ngoài enum, `mobile_device_token.py:130-137`) ARRIVE **HTTP-200** body → gom nhánh Error (KHÔNG status-line key, quirk §5).
- `401`→`Unauthorized401` (bearer hết-hạn) · `403`→`Forbidden` **single-shape** (guest/no-token = dispatcher `PermissionError` HTTP-403 status-line, `is_whitelisted __init__.py:876`). status-set = `[200, 401, 403]`.

**Bất biến (đối chiếu `TC-MOB-OAS-22` (class `TestMobileDeviceTokenTyped`, 9 TC) + `TC-MOB-OAS-07/23b`):**
- STUB: **2→0**. 2 device-token RỜI `_STUB_PATHS` (= ∅) NHƯNG GIỮ trong `_DEVICE_TOKEN_FROZEN`/`_MVP_BUSINESS_PATHS`-symmetry ⇒ **symmetry 401/403 (12==12) BẤT BIẾN**. `operationId` FROZEN (A5).
- 3 component mới (`DeviceTokenRequest` schema · `RegisterDeviceTokenCreatedEnvelope` · `UnregisterDeviceTokenAckEnvelope`) + 1 requestBody (`DeviceTokenBody`) `$ref`'d NGAY ⇒ KHÔNG orphan; 0 dangling `$ref`. `responses/Stub` HẾT referenced → forward-reserve (`_RESERVED_ORPHANS` + bảng RESERVED §8.2).
- **same-commit wiring (Pattern A):** `hooks.py` `permission_query_conditions` + `has_permission` thêm `'AC Mobile Device Token'` (self-scope `user==frappe.session.user`) wire CÙNG-COMMIT với hàm `permissions.py` (D7) — KHÔNG để hook trỏ hàm chưa tồn tại.
- **KHÔNG nhận `user` từ client** (§6.2) — handler KHÔNG forward `user`; service ÉP session.

---

## 9. Ví dụ minh hoạ (curl / httpie)

> Host placeholder `https://REPLACE-WITH-PUBLIC-HOST` (Phase B set HTTPS host). Dev local = `http://localhost:8000` (site `miyano`).

**(a) Success envelope** — chi tiết thiết bị:

```bash
curl -H "Authorization: Bearer <access_token>" \
  "https://HOST/api/method/assetcore.api.imm00.get_asset?name=AC-ASSET-2026-00001"
# HTTP/1.1 200 OK
# {"success": true, "data": {"name":"AC-ASSET-2026-00001","asset_name":"Máy siêu âm ...",
#   "lifecycle_status":"Active","pm_overdue":false,"calibration_overdue":true, ...}}
```

**(b) Error envelope** — báo hỏng khi thiếu quyền (in-handler cap-403, HTTP-200 wrapper):

```bash
# Frappe RPC /api/method đọc form_dict (form-encoded mặc định) — gửi -d k=v (KHÔNG -H JSON):
curl -H "Authorization: Bearer <token_persona_readonly>" -X POST \
  "https://HOST/api/method/assetcore.api.imm12.report_incident" \
  -d "asset=AC-ASSET-2026-00001" -d "incident_type=Failure" \
  -d "severity=High" -d "description=Máy không lên nguồn"
# HTTP/1.1 200 OK            ← 200 vì lỗi NGHIỆP VỤ (wrapper) — in-handler cap-403 (§5a nhánh b)
# {"success": false,
#  "error": "Bạn không có quyền thực hiện thao tác này.",
#  "code": "FORBIDDEN",
#  "http_status": 403}        ← status THẬT trong body (KHÔNG re-auth — token còn tốt → SHOW-MESSAGE)
```

> 📌 **G-REQBODY (gap-1) — Frappe RPC `form_dict` (BẮT BUỘC repo native đọc):** endpoint `/api/method/<dotted>` đọc tham số từ `frappe.form_dict` = **query-string / `application/x-www-form-urlencoded`** (đường MẶC ĐỊNH), **KHÔNG** tự-parse body JSON. JSON body chỉ vào `form_dict` khi client **set tường minh** `Content-Type: application/json`. ⇒ OpenAPI `ReportIncidentBody.content` khai **oneOf `application/json` + `application/x-www-form-urlencoded`** (CÙNG `$ref ReportIncidentRequest`). **Codegen JSON-only client** (mặc định nhiều generator) gửi body JSON **KHÔNG** header `application/json` ⇒ Frappe parse RỖNG ⇒ 4 field tới handler trống ⇒ 'thiếu field' (sai-âm-thầm). Repo native PHẢI: dùng form-encoded HOẶC set header `Content-Type: application/json` tường minh.

**(c) Success envelope** — báo hỏng thành công (form-encoded, response `data` TYPED — G-REQBODY):

```bash
curl -H "Authorization: Bearer <token_corrective.create>" -X POST \
  "https://HOST/api/method/assetcore.api.imm12.report_incident" \
  -d "asset=AC-ASSET-2026-00001" -d "incident_type=Failure" \
  -d "severity=High" -d "description=Máy không lên nguồn"
# HTTP/1.1 200 OK
# {"success": true, "data": {"name":"INC-2026-00001","status":"Open","severity":"High"}}
#   ← data = ReportIncidentResponse {name,status,severity} (services/imm12.py:410); status
#     create-time = "Open" (Select-canonical). Critical → asset Out of Service (BR-12-04).
```

> 📌 **404 / 422 báo hỏng (G-REQBODY gap-4):** `report_incident` khai thêm **404** (asset∄ — `services/imm12.py:361` `nthrow(IMM12_ASSET_NOT_FOUND)`, qua `handle()` ⇒ Error envelope `code=NOT_FOUND` @HTTP-200 quirk; OpenAPI `NotFound404`) + **422** (BR-12-01 Critical→`clinical_impact` bắt buộc — `services/imm12.py:359` `nthrow(IMM12_CLINICAL_IMPACT_REQUIRED)`; OpenAPI `Unprocessable422` `code=VALIDATION|BUSINESS_RULE`). Cả 2 ĐÃ **gỡ khỏi RESERVED** (§8.2) khi wire vào path.

**(d) Ngoại lệ HTTP thật** — Guest (chưa bearer) → **dispatcher-403** (KHÔNG 401):

```bash
curl "https://HOST/api/method/assetcore.api.imm12.report_incident"
# HTTP/1.1 403 Forbidden      ← HTTP line ĐÚNG 403 (dispatcher-403, trip TRƯỚC handler)
# (body = Frappe PermissionError raw — exc_type=PermissionError, message HTML 'Login to access';
#  client fallback HTTP status-line → RE-AUTH. KHÔNG envelope chuẩn — FrappeRawError §5b shape #3)
```

> 📌 **G-REQBODY (gap-3) — Guest = 403, KHÔNG 401:** `report_incident` **KHÔNG** `allow_guest` ⇒ guest trip `is_whitelisted` `throw(PermissionError)` `frappe/__init__.py:876` @HTTP **403** TRƯỚC khi handler chạy. Nhánh `imm12.py:91-92` `_err(401)` (Guest→`UNAUTHENTICATED`) là **DEAD-CODE over HTTP** (chỉ reachable in-process khi set user='Guest' thủ công — test/bench execute). ⇒ vd (d) = **403** (dispatcher-403, §5a nhánh a). Phân biệt với **401** = bearer **CÓ** nhưng hết-hạn/invalid (§5 ngoại lệ row 401 — `auth.py:630` cần header len==2).

---

### 9b. Yêu cầu sửa chữa (`createRepairWorkOrder`) — C-REQBODY-CREATEREPAIR

**(e) Tạo CM thành công** (form-encoded RPC — gửi `-d` KHÔNG `-H Content-Type:json` → `form_dict`):

```bash
curl -H "Authorization: Bearer <token_repair.create>" -X POST \
  "https://HOST/api/method/assetcore.api.imm09.create_repair_work_order" \
  -d "asset_ref=AC-ASSET-2026-00001" -d "repair_type=Corrective" \
  -d "priority=Urgent" -d "failure_description=Bơm tiêm báo lỗi áp suất"
# HTTP/1.1 200 OK
# {"success": true, "data": {"name":"AC-REPAIR-2026-00001","status":"Open","sla_target_hours":8.0}}
#   ← data = CreateRepairWorkOrderResponse {name,status,sla_target_hours} (services/imm09.py:786).
#     ⚠️ sla_target_hours (KHÔNG priority) — service trả _SLA_MATRIX(risk_class,priority) imm09.py:112.
#     Asset chuyển Under Repair (transition_asset_status imm09.py:781). status create-time = "Open".
```

> 📌 **`form_dict` áp y hệt `report_incident` (§9 gap-1):** `createRepairWorkOrder` cũng là `/api/method/<dotted>` RPC ⇒ `CreateRepairWorkOrderBody.content` = **oneOf `application/json` + `application/x-www-form-urlencoded`**. Codegen JSON-only client gửi body JSON **KHÔNG** header `application/json` → 4 field tới handler RỖNG. Repo native: form-encoded HOẶC set `Content-Type: application/json` tường minh.

**(f) Cap-deny — persona `corrective.read-only` (read-only, thiếu `repair.create`)** → **403 status-line** (KHÁC `report_incident` HTTP-200):

```bash
curl -H "Authorization: Bearer <token_corrective.read-only>" -X POST \
  "https://HOST/api/method/assetcore.api.imm09.create_repair_work_order" \
  -d "asset_ref=AC-ASSET-2026-00001" -d "repair_type=Corrective" \
  -d "priority=Normal" -d "failure_description=test"
# HTTP/1.1 403 Forbidden      ← HTTP line ĐÚNG 403 (rbac.require → frappe.throw PermissionError imm09.py:40)
# (body = FrappeRawError raw, exc_type=PermissionError — §5b shape #3). ⚠️ SINGLE-SHAPE, KHÁC
#  report_incident (HTTP-200+Error). Client branch theo HTTP status-line: 403 → SHOW "thiếu quyền"
#  (token còn tốt → KHÔNG re-auth; chỉ disable nút). KHÔNG dùng Forbidden-as-re-auth ở đây.
```

> 📌 **403 createRepair ≠ 403 report_incident (delta d2):** `report_incident` (`rbac.can + _err(403)`) = HTTP-200 + Error envelope → SHOW-MESSAGE. `createRepairWorkOrder` (`rbac.require` → `frappe.throw(PermissionError)`) = HTTP-line **403 THẬT** + FrappeRawError. Cả hai đều "thiếu quyền → SHOW-MESSAGE KHÔNG re-auth" về UX, nhưng **client branch khác** (200-line vs 403-line). Spec khai đúng: report = `ReportIncidentForbidden` (dual-shape), createRepair = `Forbidden` (single-shape).

**(g) 404 — asset không tồn tại** (`asset_ref` ∄):

```bash
# -d "asset_ref=AC-ASSET-KHONG-CO" ... → HTTP/1.1 200 OK (in-handler quirk §5)
# {"success": false, "error": "Không tìm thấy thiết bị: AC-ASSET-KHONG-CO.",
#  "code": "NOT_FOUND", "http_status": 404, "message_code": "IMM09-ASSET-NOT-FOUND"}
#   ← services/imm09.py:746 nthrow(IMM09_ASSET_NOT_FOUND); OpenAPI NotFound404. Client đọc
#     http_status TRONG body (HTTP-line=200 quirk) → SHOW "kiểm tra lại mã thiết bị".
```

**(h) 409 — asset đã có WO sửa chữa đang mở** (BR-09-08):

```bash
# asset ĐÃ có Asset Repair status NOT IN terminal → HTTP/1.1 200 OK (in-handler quirk §5)
# {"success": false, "error": "Thiết bị đang có lệnh sửa chữa đang mở: AC-REPAIR-2026-00001.",
#  "code": "CONFLICT", "http_status": 409, "message_code": "IMM09-ASSET-HAS-OPEN-WO"}
#   ← services/imm09.py:753 nthrow(IMM09_ASSET_HAS_OPEN_WO); http_status 409 messages.py:667.
#     ⚠️ delta d3: CONFLICT 409 (KHÔNG 422 — đây là xung đột TRẠNG THÁI, không validation field).
#     OpenAPI Conflict409. Client SHOW "đóng lệnh hiện tại trước" + link tới WO đang mở.
```

### 9c. Yêu cầu hiệu chuẩn (`createCalibration`) — C-REQBODY-CREATECAL

**(i) Tạo phiếu hiệu chuẩn thành công** (form-encoded RPC — gửi `-d` KHÔNG `-H Content-Type:json` → `form_dict`):

```bash
curl -H "Authorization: Bearer <token_calibration.create>" -X POST \
  "https://HOST/api/method/assetcore.api.imm11.create_calibration" \
  -d "asset=AC-ASSET-2026-00001" -d "calibration_type=External" \
  -d "scheduled_date=2026-07-01" -d "technician=ktv01@benhvien.vn"
# HTTP/1.1 200 OK
# {"success": true, "data": {"name":"CAL-2026-00001","status":"Scheduled"}}
#   ← data = CreateCalibrationResponse {name,status} (services/imm11.py:1015).
#     ⚠️ CHỈ {name,status} (KHÔNG sla_target_hours — khác createRepair). status init = "Scheduled"
#     (CalibrationResult.SCHEDULED imm11.py:1013, = doctype default).
```

**(j) Biến thể JSON** (set `Content-Type: application/json` tường minh — Frappe parse JSON body vào `form_dict`):

```bash
curl -H "Authorization: Bearer <token_calibration.create>" \
  -H "Content-Type: application/json" -X POST \
  "https://HOST/api/method/assetcore.api.imm11.create_calibration" \
  -d '{"asset":"AC-ASSET-2026-00001","calibration_type":"In-House",
       "scheduled_date":"2026-07-01","technician":"ktv01@benhvien.vn",
       "is_recalibration":1}'
# HTTP/1.1 200 OK — same shape {"success":true,"data":{"name":...,"status":"Scheduled"}}
#   ← is_recalibration=1 ⇒ BYPASS business-block (imm11.py:1001) kể cả khi asset lifecycle blocked.
```

> 📌 **`form_dict` áp y hệt `report_incident`/`createRepairWorkOrder` (§9 gap-1):** `createCalibration` cũng là `/api/method/<dotted>` RPC ⇒ `CreateCalibrationBody.content` = **oneOf `application/json` + `application/x-www-form-urlencoded`**. Codegen JSON-only client gửi body JSON **KHÔNG** header `application/json` → 4 field tới handler RỖNG. Repo native: form-encoded HOẶC set `Content-Type: application/json` tường minh.

**(k) 404 — asset không tồn tại** (`asset` ∄):

```bash
# -d "asset=AC-ASSET-KHONG-CO" ... → HTTP/1.1 200 OK (in-handler quirk §5)
# {"success": false, "error": "Thiết bị không tồn tại trong danh mục tài sản.",
#  "code": "NOT_FOUND", "http_status": 404, "message_code": "IMM11-ASSET-NOT-FOUND"}
#   ← services/imm11.py:999 nthrow(IMM11_ASSET_NOT_FOUND); http_status 404 messages.py:853.
#     OpenAPI NotFound404. Client đọc http_status TRONG body (HTTP-line=200 quirk) →
#     SHOW "kiểm tra lại mã thiết bị". (asset-EXISTENCE — KHÁC 409 asset-tồn-tại-nhưng-blocked.)
```

**(l) 409 — asset tồn tại nhưng lifecycle blocked ∧ không-recalibration** (CAL-008):

```bash
# asset lifecycle ∈ {Out of Service, Decommissioned} (BLOCKED_FOR_WO) ∧ is_recalibration=0
#   → HTTP/1.1 200 OK (in-handler quirk §5)
# {"success": false, "error": "Thiết bị đang ở trạng thái không cho phép tạo phiếu hiệu chuẩn (CAL-008).",
#  "code": "CONFLICT", "http_status": 409, "message_code": "IMM11-ASSET-BLOCKED"}
#   ← services/imm11.py:1002 nthrow(IMM11_ASSET_BLOCKED); http_status 409 messages.py:860.
#     ⚠️ delta c2: CONFLICT 409 (KHÔNG 422 — lifecycle blocked là xung đột TRẠNG THÁI, business-rule).
#     OpenAPI Conflict409. KHÁC nguyên-nhân createRepair-409 (open-WO) nhưng CÙNG HTTP-409.
#     Client SHOW "chuyển thiết bị về hoạt động HOẶC dùng tái hiệu chuẩn (is_recalibration=1)".
#   📌 404 (asset∄) vs 409 (asset∃ nhưng blocked): client phân biệt theo message_code/http_status.
```

### 9d. userinfo / whoami + refresh-on-401 (`getUserInfo`) — C4

> **PASSTHROUGH RAW — KHÔNG envelope AssetCore.** `openid_profile` set `frappe.local.response = body` (`oauth2.py:172-174`) ⇒ trả nguyên dict OIDC claims, **KHÔNG bọc `{success,data}`** (§2) và **KHÔNG `{message:}`**. Đây là **cùng pattern passthrough của OAuth token-endpoint** (`getOAuthToken`/`revokeOAuthToken` — xem §5b điểm 1 + [`03-auth-oauth2.md §2`](./03-auth-oauth2.md)): auth-section dùng shape Frappe/OIDC core, KHÔNG dùng AssetCore Error/Success envelope. Client native parse trực-tiếp dict claims.

**(m) Lấy danh tính sau đăng nhập** (bearer hợp lệ, scope `openid`):

```bash
curl -H "Authorization: Bearer <access_token>" \
  "https://HOST/api/method/frappe.integrations.oauth2.openid_profile"
# HTTP/1.1 200 OK   — RAW OIDC claims (KHÔNG envelope)
# {"sub":"a1b2...","name":"Nguyễn Văn A","given_name":"A","family_name":"Nguyễn Văn",
#  "email":"ktv01@benhvien.vn","picture":null,
#  "roles":["Technician","All","Asset User"],"iss":"https://HOST"}
#   ← get_userinfo oauth.py:530-555. App dùng name + roles hiển thị danh tính KTV (flow-1).
#     sub/picture có thể null (oauth.py:531-548). KHÔNG {success}/{message} — RAW passthrough.
```

**(n) Sequence refresh-on-401** (access hết hạn → đóng vòng OAuth2 + refresh, retry MỘT lần):

```bash
# 1) userinfo với access cũ/hết hạn → 401 (dispatcher RAW Frappe, KHÔNG envelope)
curl -i -H "Authorization: Bearer <access cũ>" \
  "https://HOST/api/method/frappe.integrations.oauth2.openid_profile"
# HTTP/1.1 401 ...

# 2) đổi refresh_token → access mới  (§9 / 03-auth §1.1 bước (e))
curl -X POST "https://HOST/api/method/frappe.integrations.oauth2.get_token" \
  -d "grant_type=refresh_token" -d "refresh_token=<refresh>" -d "client_id=<client_id>"
# HTTP/1.1 200 OK  {"access_token":"<MỚI>","refresh_token":"...","expires_in":3600,...}

# 3) retry userinfo với access MỚI → 200 RAW claims (bước (m))
curl -H "Authorization: Bearer <access MỚI>" \
  "https://HOST/api/method/frappe.integrations.oauth2.openid_profile"
# refresh fail (Revoked/hết hạn) → xoá token Keychain/Keystore → re-auth (03-auth §2.5).
```

> 📌 Quy tắc refresh-on-401 áp **mọi request** (KHÔNG riêng userinfo): refresh MỘT lần → retry → fail thì re-auth. Cross-ref [`03-auth-oauth2.md §2.5/§2.6`](./03-auth-oauth2.md) (policy app + claims grounded).

---

## 9b. Hai spec OpenAPI phân vai (2-spec-by-design — F-C2)

> Cross-ref quyết định kiến trúc: [`ADR-MOBILE-001.md (k)`](./ADR-MOBILE-001.md). Trạng thái: [`completion/EPIC-C-api-contract.md §F-C2`](./completion/EPIC-C-api-contract.md).

Repo có **HAI** artefact OpenAPI CÓ CHỦ ĐÍCH — KHÔNG hợp nhất; mỗi spec có **1 audience + 1 SSoT rõ**:

| | (A) Runtime spec `openapi.spec` | (B) YAML mobile (file này mô tả) |
|---|---|---|
| Nguồn | `api/openapi.py::generate_spec()` (`:1254`) + `openapi_overrides.py` (enrich D1–D16) — sinh ĐỘNG từ introspection chữ-ký hàm | `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — viết tay |
| OAS | **3.1.0** | **3.0.3** |
| Path | **487** (toàn bề mặt API) | **16** (4 auth + 10 MVP-business + 2 device-token STUB) |
| Served | LIVE Swagger UI `www/api-docs.html` (+ `www/api-docs.py`) | KHÔNG serve — file repo cho codegen |
| Audience / SSoT | **human-browse + integrator** (Swagger UI, full surface) | **codegen repo-native mobile** (subset MVP field-tech) |
| Decision-B `oneOf[Env,Error]` | **KHÔNG** — create/read 200 = plain `$ref SuccessEnvelope`; key 404/422 dưới HTTP-status-line (KHÔNG phản ánh HTTP-200-quirk §5) | **CÓ ĐẦY ĐỦ** — closed-schema `oneOf` (§5c create + §8.7/C6 read) + requestBody `oneOf json+form` (§9d) |

**Scope-boundary BẮT BUỘC:** codegen mobile **CHỈ** dùng (B) YAML. **KHÔNG** codegen-against-runtime (A): runtime spec create/read 200 = plain `SuccessEnvelope` (KHÔNG nhánh `Error`) ⇒ client sinh-từ-runtime **dead-deser** in-handler **404 / IDOR-403** (lỗi nghiệp vụ arrive HTTP-200 + Error body qua `_err` — §5/§5c). Swagger UI/integrator **CHỈ** dùng (A) runtime (full 487-path).

**Drift-guard [AUTO introspection-only]** — `tests/test_mobile_oas.py::TestMobileSpecParityRuntime` (TC-25a..e): import IN-PROCESS `openapi.generate_spec()` (KHÔNG HTTP/reload/migrate) cross-check 16-path YAML vs runtime. Bất biến: **10 mobile-business path** (loại 2 device-token STUB + 4 auth passthrough) PHẢI tồn tại trong runtime với **CÙNG dotted-path-tail + CÙNG security-class**. Lệch → RED (chống drift câm).

- **⚠️ KNOWN-DIVERGENCE verb `create_calibration`:** runtime suy verb=**GET** (`@frappe.whitelist()` THIẾU `methods=["POST"]` `imm11.py:89`) vs YAML khai **POST** (đúng ngữ nghĩa). Allowlist trong guard; fix @source = thêm `methods=["POST"]` (đụng `api/*.py` ⇒ HARD-STOP reload) = **Phase-F backlog**.

**HARD-STOP USER = backlog Phase-F:** (1) port Decision-B vào `openapi_overrides.py` để runtime carry `oneOf` (A2 — đụng runtime + reload); (2) codegen-against-runtime live HTTP (gate EPIC-V); (3) fix `create_calibration` decorator.

---

## 10. Tham chiếu chéo + bàn giao Phase C

**Sau R4 (§8.7): chỉ CÒN 2 path STUB** = 2 device-token (`register`/`unregister` — `[ROADMAP]` BE-PENDING, handler chưa tồn tại @source). **A10 đã thêm `operationId` cho cả 15 path** (contract-identity, codegen-able — §8.1). `report_incident` rời STUB ở Phase-C đầu (§8.3); 3 list path ở C-LISTREAD (§8.4); `createRepairWorkOrder` ở C-REQBODY-CREATEREPAIR (§8.5); `createCalibration` ở C-REQBODY-CREATECAL (§8.6); **R4 §8.7** type `data` cho 4 read/create (2 QR + `get_asset` + `createPmWorkOrder`) GROUNDED chữ-ký service THẬT ⇒ **15 path contract-complete trừ 2 device-token ROADMAP**:

| Luồng | Endpoint (RPC) | Cap | Việc Phase C |
|---|---|---|---|
| Quét QR → asset | `imm00.resolve_qr_token` · `imm00.get_asset_scan_info` · `imm00.get_asset` | `asset.read` | ✅ **R4 §8.7: typed `data` GROUNDED** — `QrResolveResult` (`imm00.py:303`) / `AssetScanInfo` + `available_actions[]` + cờ overdue server-flag (`imm00.py:567`) / `AssetDetail` (`imm00.py:288`). Rời STUB. |
| Báo hỏng | `imm12.report_incident` | `corrective.create` | ✅ **HOÀN CHỈNH (C-REQBODY + G-REQBODY):** requestBody THẬT (4 field — content oneOf json+form-urlencoded, Frappe RPC `form_dict` §9) + response 200 THẬT (`ReportIncidentResponse {name,status,severity}` `imm12.py:410`) + 403 dual-shape + 404/422 wire (§8.3). `source` server-coerce NGOÀI body (`imm12.py:83`). |
| Yêu cầu PM | `imm08.create_pm_work_order` | `pm.create` | ✅ **R4 §8.7: typed response** — 200 oneOf `[CreatePmWorkOrderCreatedEnvelope {name,status,checklist_items_count} `imm08.py:836` \| Error]` closed-schema §5c + 403 single-shape + form requestBody required `[asset_ref,pm_schedule,due_date]` (`imm08.py:788`). Rời STUB. *(Typed requestBody schema chi tiết = backlog Phase-C kế.)* |
| Yêu cầu CM | `imm09.create_repair_work_order` | `repair.create` | ✅ **HOÀN CHỈNH (C-REQBODY-CREATEREPAIR):** requestBody THẬT (4 field bắt buộc + enum `repair_type`/`priority` Select-canonical — content oneOf json+form-urlencoded, §9b) + response 200 THẬT (`CreateRepairWorkOrderResponse {name,status,sla_target_hours}` `imm09.py:786` — **KHÔNG `priority`**, delta d1) + 403 **single-shape** `Forbidden` (`rbac.require` → PermissionError HTTP-403, delta d2) + 404 (asset∄) + **409** (asset đã có WO mở — `IMM09_ASSET_HAS_OPEN_WO` 409 CONFLICT, **KHÔNG 422**, delta d3) wire (§8.5). `requested_by` server-gán NGOÀI body (`imm09.py:770`). |
| Yêu cầu hiệu chuẩn | `imm11.create_calibration` | `calibration.create` | ✅ **HOÀN CHỈNH (C-REQBODY-CREATECAL):** requestBody THẬT (4 field bắt buộc + enum `calibration_type` `[External, In-House]` Select-canonical + 5 optional incl. `is_recalibration` 0|1 — content oneOf json+form-urlencoded, §9c) + response 200 THẬT (`CreateCalibrationResponse {name,status}` `imm11.py:1015` — **KHÔNG `sla_target_hours`**, status init "Scheduled") + 403 **single-shape** `Forbidden` (`rbac.require` → PermissionError HTTP-403, delta c1) + 404 (asset∄) + **409** (asset blocked ∧ không-recalibration — `IMM11_ASSET_BLOCKED` 409 CONFLICT CAL-008, **KHÔNG 422**, delta c2) wire (§8.6). *(Nợ kỹ thuật còn lại: dọn `str=None`→`str=""` signature `imm11.py:91-94` — Phase C backlog, KHÔNG đụng code vòng này.)* |
| Phiếu của tôi | `imm08.list_pm_work_orders` · `imm09.list_repair_work_orders` · `imm12.list_incidents` | `*.read` | ✅ **C-LISTREAD: pagination param + 200 list-envelope THẬT bồi** (§6.1/§6.2 + §8.4). rows-key PHÂN BIỆT: imm08/09→`data.data[]`, imm12→`data.items[]`. **Known-gap Phase-E:** chuẩn-hoá 1 rows-key + thống nhất scope `reported_by` vs `assigned_to` (A2 finding). |

**Note canonical vs legacy handler:** envelope đồng nhất qua **`handle()` shared** (`utils/api_handler.py:33`) = **canonical**. 6 file api còn `_handle` cục bộ (imm01/02/03/15/16 + import_data — định nghĩa tại `:32/:33/:46/:26/:29/:18`) là **legacy tương đương** (cùng wrap `_ok`/`_err`); migration tới `handle()` shared là dần dần (`api_handler.py` docstring §19-21). ⇒ Hợp đồng envelope KHÔNG đổi giữa 2 path. KHÔNG sửa code ở A3.

**Cross-link:**
- Tổng quan + 3 quyết định + glossary: [`00-overview.md`](./00-overview.md) §2 · §7
- Kiến trúc (versioning §4 · OpenAPI-as-contract §5): [`01-architecture.md`](./01-architecture.md)
- Feasibility (CORS/provider/blocker): [`02-deploy-feasibility.md`](./02-deploy-feasibility.md)
- Auth deep-dive (sequence/TTL/scope↔cap): [`03-auth-oauth2.md`](./03-auth-oauth2.md)
- ADR: [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- OpenAPI (hợp đồng máy đọc): [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)
- **Source SSoT:** `utils/response.py` (envelope/ErrorCode) · `utils/pagination.py` · `utils/api_handler.py` (handle/parse_json) · `api/imm00.py:159-267` (list_assets pagination)
