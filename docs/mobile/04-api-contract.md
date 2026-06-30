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

### 4.1 ADR — `Error.http_status` = integer enum **bounded** (vòng 11, 2026-06-16)

- **Context:** schema `components.schemas.Error.code` ĐÃ typed-enum 15-value (§4), nhưng `http_status` còn **free integer**. Codegen mobile (Dart/Kotlin/TS) KHÔNG sinh được **exhaustive switch** trên `http_status` ⇒ **route-by-VALUE asymmetry**: client route theo `body.success` rồi `body.code` exhaustive, nhưng `body.http_status` mở-vô-biên → fallback `default` câm.
- **Decision:** constrain `http_status` thành `integer enum` **bounded** = đúng tập **distinct value BE phát ở body**, GIỮ `type:integer` + `example:403` + description. Tập = **{400,401,403,404,409,413,422,429,500}** (9 giá trị, sorted).
- **Vì sao 9 chứ KHÔNG 10 (loại 417):** SSoT runtime `utils/response.py`. `union(_HTTP_FOR_CODE.values()) ∪ keys(_HTTP_TO_CODE)` = candidate thô **gồm 417**. NHƯNG 417 chỉ là **KEY của `_HTTP_TO_CODE`** (reverse-map legacy) trỏ `BUSINESS_RULE`; body resolve qua `_HTTP_FOR_CODE[BUSINESS_RULE]=422` (`response.py:131`) ⇒ **417 KHÔNG bao giờ surface ở `body.http_status`**. Body-set THẬT = `set(_HTTP_FOR_CODE.values())` → loại 417.
- **Boundaries:**
  - **Always:** enum = body-set DERIVE TỪ `utils/response.py` runtime (guard `TestMobileErrorHttpStatusEnumBounded` import `_HTTP_FOR_CODE`+`_HTTP_TO_CODE`, KHÔNG hardcode 9 literal). BE thêm/bớt status tương lai mà yaml chưa cập ⇒ test ĐỎ.
  - **Never:** đưa **417** vào enum (guard `test_red_before_inject_417_raises`); đổi `http_status` sang string; bỏ `type:integer`/`example:403`.
- **Consequences:** codegen sinh enum-typed `http_status` ⇒ client exhaustive switch không-câm; coupling chặt yaml↔`response.py` (cố ý — drift = RED). Guard 5 TC RED-before/GREEN-after PROVEN (deepcopy in-memory drop/inject-417).
- **Alternatives bị loại:** *(A)* giữ free integer + chỉ doc-prose — codegen KHÔNG exhaustive, asymmetry không đóng. *(B)* enum = 10 value (gồm 417) — SAI: 417 không bao giờ ở body ⇒ dead-branch codegen, lừa người đọc rằng body có thể phát 417.

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

**🔵 C6-DETAIL (open-thread #4b) — 4 GET-detail (màn detail MVP-flow-5 + push deep-link flow-6):** áp CÙNG bảng C6 cho 4 path `getX` chi tiết. Mỗi GET 1 query-param `name` (required string — **KHÔNG path-param**: `/api/method/<dotted>` không có template `{name}`, OAS 3.0.3 cấm `in:path` không khớp template ⇒ `in:query`) + bearer (global security). `*Detail` payload `additionalProperties:true` (`as_dict()` surface field doctype, mirror `AssetDetail` §3.2 — imm08 build dict tường minh); ENVELOPE đóng (`additionalProperties:false`, `required[success,data]`, `success.enum[true]`) để disjoint vs `Error`. 4 `*Detail` **field-disjoint** (named schema RIÊNG, KHÔNG share ref — C3-split analog). **int-vs-bool (Open#1 sweep):** Check fieldtype qua `as_dict()` → `integer enum[0,1]`; imm08 explicit `bool()`-coerce (`pm_sticker_attached`/`is_late`, `imm08.py:616-617`) GIỮ `boolean` (derived Python-bool).

| Path | `'200'` oneOf (success:true) | success:false | status-set | Field-set @source · in-handler error |
|---|---|---|---|---|
| `getPmWorkOrder` | `PmWorkOrderDetailEnvelope` `{data: PmWorkOrderDetail}` | `Error` | `[200,401,403]` | `services/imm08.py:572-624` (DICT tường minh + `allowed_transitions[]` server-driven CTA + `checklist_results[]` nested) · 404 WO∄ `imm08.py:575` · vendor-IDOR-403 `imm08.py:40-42` |
| `getRepairWorkOrder` | `RepairWorkOrderDetailEnvelope` `{data: RepairWorkOrderDetail}` | `Error` | `[200,401,403]` | `services/imm09.py:700-730` (`as_dict()` + `asset_info{}` nested + flatten `*_name` + `allowed_transitions[]` server-driven CTA) · 404 WO∄ `imm09.py:703` · vendor-IDOR-403 `imm09.py:30` |
| `getIncident` | `IncidentDetailEnvelope` `{data: IncidentDetail}` | `Error` | `[200,401,403]` | `services/imm12.py:773-789` (`as_dict()` + `asset_name` + `allowed_transitions[]` + `rca{}` nested optional) · **guest-401 IN-HANDLER** `imm12.py:222-223` (`_err(…,401)` → HTTP-200+Error, route `body.http_status=401`) · 404 Incident∄ · vendor-IDOR-403 `imm12.py:227` |
| `getCalibration` | `CalibrationDetailEnvelope` `{data: CalibrationDetail}` | `Error` | `[200,401,403]` | `services/imm11.py:978-989` (`as_dict()` + `asset_name` + `technician_name`) · 404 Cal∄ `imm11.py:981` · vendor-IDOR-403 `imm11.py:83-85` |

> **⚠️ getIncident guest-401 quirk:** KHÁC 3 detail kia (dispatcher-403 cho guest), `imm12.get_incident` có **in-handler** `if session.user==Guest: _err(…,401)` (`imm12.py:222-223`) ⇒ guest đi qua nhánh **Error của 200-oneOf** (`body.http_status=401`, route → refresh/re-auth) — KHÔNG status-line. `401` status-line (`Unauthorized401`) GIỮ cho **expired-bearer** (session resolve = Guest TRƯỚC handler). Client native PHÂN BIỆT: `body.success=false ∧ body.http_status=401` (in-handler) vs HTTP-401 status-line (dispatcher) → CẢ HAI → refresh→re-auth. Guard: `TC-MOB-OAS-30a..g` (`TestMobileGetDetailContract`) + 200-oneOf phủ `TC-MOB-OAS-24` (qua `_READ_PATH_ENVELOPE`) + C5 typed `TC-MOB-OAS-23`.

> **🔵 PM-DETAIL `allowed_transitions[]` — server-driven CTA (ASYMMETRY R3 ĐÓNG, 2026-06-16):** `PmWorkOrderDetail` bồi property `allowed_transitions: array<string>` = tập trạng-thái-kế hợp-lệ từ `status` hiện tại, để **màn PM-detail render nút workflow theo server** (KHÔNG hardcode `status → button` phía client — anti-pattern RBAC/lifecycle **dead-gate**, memory `factory_rounds_1_25`). **MIRROR `IncidentDetail.allowed_transitions`** (`imm12.py:778`, R3) — trước round này CHỈ Incident có; 3 detail khác (PM/Repair/Calibration) KHÔNG. SSoT = `services/imm08.py:_PM_VALID_TRANSITIONS` (`dict[str,list[str]]`) **GROUNDED chính xác** `imm_08_pm_workflow.json` (**7 state / 13 transition**): `Open→[In Progress,Overdue,Cancelled]` · `Overdue→[In Progress,Cancelled]` · `In Progress→[Completed,Halted–Major Failure,Pending–Device Busy,Cancelled]` · `Pending–Device Busy→[In Progress,Cancelled]` · `Halted–Major Failure→[In Progress,Cancelled]` · terminal `Completed`/`Cancelled→[]` (rỗng). `get_work_order` emit `allowed_transitions = _PM_VALID_TRANSITIONS.get(wo.status, [])` (`imm08.py`) — **0 đổi** signature handler `getPmWorkOrder`, **KHÔNG** đụng workflow-engine/submit/start. Schema **KHÔNG enum-bound cứng** (mirror-shape `array<string>` né drift khi workflow đổi); codomain-check ở guard **phía service** (KHÔNG schema-enum). **KHÔNG** thêm vào `required` (emit-luôn nhưng `required` GIỮ `['name']` đồng nhất IncidentDetail R3); `additionalProperties:true` GIỮ NGUYÊN. Guard: `TestMobilePmAllowedTransitionsContract` (`test_mobile_oas` +6 TC a..f — shape/required/parity-codomain⊆`PMStatus`/SSoT-divergence map↔workflow/live-emit) + BE unit `TestPMAllowedTransitions` (`test_imm08`, +2 TC — map-codomain + `get_work_order` emit theo status). **KHÔNG path mới** (33 path GIỮ). Client native (codegen) đọc `allowed_transitions[]` → render CTA `In Progress`/`Cancelled`/… theo từng status; deep-link `assetcore://wo/pm/<name>` (flow-6) cũng landing màn này.

> **🔵 REPAIR-DETAIL `allowed_transitions[]` — server-driven CTA (ASYMMETRY R3 NỬA-REPAIR ĐÓNG, 2026-06-16):** `RepairWorkOrderDetail` bồi property `allowed_transitions: array<string>` = tập trạng-thái-kế hợp-lệ từ `status` hiện tại, để **màn repair-detail render nút workflow theo server** (KHÔNG hardcode `status → button` phía client — anti-pattern **dead-gate**). **Thành viên THỨ BA** có `allowed_transitions[]` (sau Incident R3 + PM R21) — đóng **NỬA Repair** của ASYMMETRY R3. (Nửa còn lại = `CalibrationDetail` — state-machine riêng `imm_11_calibration_workflow.json` — round riêng sau, cùng pattern.) **MIRROR `IncidentDetail`/`PmWorkOrderDetail`** (`imm12.py:778` / `imm08.py:651`). SSoT = `services/imm09.py:_REPAIR_VALID_TRANSITIONS` (`dict[str,list[str]]`, keyed bằng `RepairStatus.*` constants — KHÔNG literal) **GROUNDED chính xác** `imm_09_repair_workflow.json` (**9 state / 15 transition**, edge-by-edge): `Open→[Assigned,Cancelled]` · `Assigned→[Diagnosing,Cancelled]` · `Diagnosing→[In Repair,Pending Parts,Cancelled]` · `Pending Parts→[In Repair,Cancelled]` · `In Repair→[Pending Inspection,Cannot Repair,Cancelled]` · `Pending Inspection→[Completed,In Repair,Cancelled]` · terminal `Completed`/`Cannot Repair`/`Cancelled→[]` (rỗng). `get_work_order` emit `allowed_transitions = _REPAIR_VALID_TRANSITIONS.get(doc.status, [])` (`imm09.py`) — **0 đổi** signature handler `getRepairWorkOrder` (vẫn `handle(svc.get_work_order, name)`); field mới chảy qua envelope tự động. Schema **KHÔNG enum-bound cứng** (mirror-shape `array<string>` né drift); codomain-check ở guard **phía service**. **KHÔNG** thêm vào `required` (emit-luôn nhưng `required` GIỮ `['name']`); `additionalProperties:true` GIỮ NGUYÊN. Guard: `TestMobileRepairAllowedTransitionsContract` (`test_mobile_oas` +6 TC a..f — shape/required/parity-codomain⊆`RepairStatus`/SSoT-divergence map↔workflow edge-by-edge/terminal/live-emit) + BE unit `TestRepairAllowedTransitions` (`test_imm09`, +1 TC class/2 method — map-codomain + `get_work_order` emit theo status Open/In Repair/Completed-terminal). **KHÔNG path mới** (33 path GIỮ); `_EXPECTED_TEST_COUNT` 298→304, `_GUARD_SUITE_SUM` 441→447, `_MOBILE_OAS_TOTAL` 467→473. Client native (codegen) đọc `allowed_transitions[]` → render CTA `Pending Inspection`/`Cannot Repair`/`Cancelled`/… theo từng status; deep-link `assetcore://wo/repair/<name>` cũng landing màn này.

**🔵 C7 — list-path P1 closure (2026-06-15, open-thread #5): 4 list 200 áp CÙNG Decision-B oneOf.** 4 list path (`listPmWorkOrders`/`listRepairWorkOrders`/`listIncidents` + `listPmSchedules`) cũng phát **in-handler error qua `_err` → HTTP-200 + Error body**: malformed `filters` → `parse_json` raise `ServiceError(INVALID_PARAMS)` **caught** `try/except` → `_service_error_to_envelope` ⇒ HTTP-200 + `Error{code:INVALID_PARAMS, http_status:400}`. TRƯỚC C7, 4 list 200 = **single `$ref <ListEnvelope>`** (KHÔNG nhánh Error) → codegen KHÔNG có deser-branch Error ⇒ list-envelope **deser-crash** khi runtime trả Error body (dead-deser, lỗi câm). Vì 4 list path trỏ **response-component** (`responses/<X>List`), oneOf áp **Ở TẦNG content-schema CỦA COMPONENT** (KHÔNG nhồi vào trong envelope) — khác C6 read/detail (oneOf inline path-level), giống về bản chất closed-schema. CẢ 4 `*ListEnvelope` thêm `additionalProperties:false` (trước thiếu) để disjoint vs `Error` (route-by-VALUE `body.success`, 0 discriminator). `listPmSchedules` **CŨNG retrofit** cùng pattern ⇒ 4 list path NHẤT QUÁN (KHÔNG bỏ sót như C6-GET đã sót list).

| Path | response-component `'200'` content.schema = oneOf | success:false | rows-key | in-handler error (gom nhánh Error) |
|---|---|---|---|---|
| `listPmWorkOrders` | `[PmWorkOrderListEnvelope, Error]` (`responses/PmWorkOrderList`) | `Error` | `data.data[]` | malformed `filters` → `INVALID_PARAMS` (`imm08.py:30-32` caught) |
| `listRepairWorkOrders` | `[RepairWorkOrderListEnvelope, Error]` (`responses/RepairWorkOrderList`) | `Error` | `data.data[]` | malformed `filters` → `INVALID_PARAMS` (`imm09.py` parse_json DỜI VÀO handle, mirror imm08) |
| `listIncidents` | `[IncidentListEnvelope, Error]` (`responses/IncidentList`) | `Error` | `data.items[]` | in-handler `_err` arrive HTTP-200 + Error |
| `listPmSchedules` | `[PmScheduleListEnvelope, Error]` (`responses/PmScheduleList`) | `Error` | `data.data[]` | param DISCRETE (KHÔNG `filters`); in-handler `_err` HTTP-200 + Error |
| `listCalibrations` | `[CalibrationListEnvelope, Error]` (`responses/CalibrationList`) | `Error` | `data.data[]` | malformed `filters` → `INVALID_PARAMS` (`imm11.py:72-75` parse_json-in-try ĐÃ có → `_err`; KHÁC imm09 KHÔNG cần dời) |
| `listAssets` | `[AssetListEnvelope, Error]` (`responses/AssetList`) | `Error` | **`data.items[]`** (mirror `IncidentListEnvelope`) | param **7 DISCRETE** (KHÔNG `filters`); in-handler `_err` HTTP-200 + Error. `imm00.list_assets` bare `@whitelist` nhận GET — KHÔNG `parse_json` (param discrete) ⇒ KHÔNG cần dời `.py` |
| `listUsers` | `[UserListEnvelope, Error]` (`responses/UserList`) | `Error` | **`data.items[]`** (mirror `AssetListEnvelope`/`IncidentListEnvelope`) | param **6 DISCRETE** (KHÔNG `filters`); `user.list_users` bare `@whitelist` nhận GET — KHÔNG `parse_json` ⇒ KHÔNG cần dời `.py`. ⚠️ pagination **4-key** `{page,page_size,total,total_pages}` (KHÔNG `offset`) — xem §6.3 / ADR-MOBILE-005 |

> **🔴 BE FIX (open-thread #5) — `imm09.list_repair_work_orders` parse_json DỜI VÀO `handle()`.** TRƯỚC: `parse_json(filters)` ở `imm09.py:22` **NGOÀI** `handle()`/try-except ⇒ malformed → `ServiceError` **uncaught** bubble lên Frappe global handler = **HTTP-500** (KHÁC contract). SAU: bọc `try: f = parse_json(...) except ServiceError as e: return _service_error_to_envelope(e)` — **khớp đúng** `imm08.list_pm_work_orders:30-32` ⇒ malformed cho Error-trên-HTTP-200. KHÔNG đổi signature, KHÔNG nhồi logic controller (CLAUDE.md §15). Guard BE: `TestImm09ListParseJsonInHandle` (`test_imm09.py` — behavioral malformed→Error + structural parse_json-in-try, RED-before/GREEN-after).

> **Hợp đồng client native (list, C7):** giống create/read — **KHÔNG branch theo HTTP status-line** cho list-business outcome; đọc `body.success` trước. `false` ⇒ đọc `body.code` (`INVALID_PARAMS` = filters JSON hỏng) + `body.http_status`. Chỉ 401/dispatcher-403 (pre-handler) mới mang HTTP status-line THẬT. Guard contract: `TC-MOB-OAS-31a..g` (`TestMobileListEnvelopeOneOf` — oneOf 2 nhánh + 0 discriminator + closed-disjoint + 0 dangling + sweep parity 4/4 + negative inject + control); `_codegen_dry_introspect` list-branch (TC-23) cập-nhật theo oneOf.

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
| `imm08.list_pm_work_orders` | `{"data": rows, "pagination": pg}` (`imm08.py:569`) | **`data.data[]`** | `PmWorkOrderListEnvelope` (200→`PmWorkOrderList`; item `PmWorkOrderListItem` — C3-split) | `filters`/**`mine`**/`page`/`page_size` (`mine=1` scope `assigned_to==session.user` — tab "Phiếu PM của tôi" MVP-5a; param `WorkOrderMine`; [ADR-MOBILE-016](./ADR-MOBILE-016.md)) |
| `imm09.list_repair_work_orders` | `{"data": rows, "pagination": pg}` (`imm09.py:697`) | **`data.data[]`** | `RepairWorkOrderListEnvelope` (200→`RepairWorkOrderList`; item `RepairWorkOrderListItem` — C3-split) | `filters`/`page`/`page_size` |
| `imm12.list_incidents` | `{"items": rows, "pagination": pg}` (`imm12.py:764-770`) | **`data.items[]`** | `IncidentListEnvelope` (200→`IncidentList`) | `status`/`severity`/`asset`/`open`/**`mine`**/`page`/`page_size` (`mine=1` scope `reported_by==session.user` — tab "Báo hỏng của tôi" MVP-5c; param `IncidentMine`; [ADR-MOBILE-015](./ADR-MOBILE-015.md)) |
| `imm08.list_pm_schedules` | `{"data": rows, "pagination": pg}` (`imm08.py:984` `list_schedules`) | **`data.data[]`** | `PmScheduleListEnvelope` (200→`PmScheduleList`; item `PmScheduleListItem` — C3-split) | `asset_ref`/`status`/`page`/`page_size` (**DISCRETE**, KHÔNG JSON `filters`) |
| `imm11.list_calibrations` | `{"data": rows, "pagination": pg}` (`services/imm11.py:937`) | **`data.data[]`** | `CalibrationListEnvelope` (200→`CalibrationList`; item `CalibrationListItem` — C3-split) | `filters`/`page`/`page_size` (**REUSE** `WorkOrderFilters` JSON-string) |
| `imm00.list_assets` | `{"pagination": pg, "items": rows}` (`imm00.py:450` `_ok({pagination,items})`) | **`data.items[]`** (mirror `IncidentListEnvelope`) | `AssetListEnvelope` (200→`AssetList`; item `AssetListItem` — field-disjoint, 20 field, 3 financial EXCLUDED) | `lifecycle_status`/`department`/`location`/`asset_category`/`search`/`gmdn_code`/`byt_status`/`page`/`page_size` (**7 DISCRETE**, KHÔNG JSON `filters`) |
| `user.list_users` | `{"items": rows, "pagination": pg}` (`api/user.py:367-374` `_ok({items, pagination})`) | **`data.items[]`** (mirror `AssetListEnvelope`/`IncidentListEnvelope`) | `UserListEnvelope` (200→`UserList`; item `UserListItem` — field-disjoint, 9 scalar + `imm_roles[]` object-array + `pagination`) | `search`/`department`/`role`/`approval_status`/`is_active`/`page`/`page_size` (**6 DISCRETE**, KHÔNG JSON `filters`) — ⚠️ pagination **4-key** KHÔNG `offset` ([ADR-MOBILE-005](./ADR-MOBILE-005.md)) |

> **C-LISTREAD-ASSET (open-thread #4c — đóng nốt).** Path `listAssets` bồi đóng tra-cứu thiết bị MVP-flow-5. BE sẵn `imm00.list_assets:309` (bare `@frappe.whitelist()` nhận GET — cap đọc `asset.read` mirror `getAsset`; vendor-scope `apply_vendor_scope` `imm00.py:388` → INVARIANT `count==rows` mọi persona). KHÁC `listCalibrations`/`list_pm`/`list_repair`: param **7 DISCRETE** query-string (KHÔNG JSON `filters` — mirror `listPmSchedules` discrete). rows-key **`data.items[]`** mirror `IncidentListEnvelope` (handler `imm00.py:450` trả `_ok({pagination, items})` — KHÁC `data.data[]`). Element `AssetListItem` field-disjoint = **20 field** (14 base `imm00.py:427-434` + 6 enrich `imm00.py:444-449`); **3 financial-field** (`gross_purchase_amount`/`accumulated_depreciation`/`current_book_value`) handler CÓ trả `@:433` NHƯNG **EXCLUDED** khỏi list-item (LL-BE-57 mobile-meta no-financial — KTV không cần giá); 0 Check field → 0 prop boolean (Open#1 né sẵn); `lifecycle_status` = string KHÔNG enum cứng (Select nhiều giá trị). **23 path / 23 operationId** sau round này. `imm00.list_assets` KHÔNG `parse_json` (param discrete) ⇒ KHÔNG cần dời `.py` (khác imm09 round 4). Guard = `TestMobileListAssetsContract` (+7 TC).

> **C-LISTREAD-CAL (open-thread #4c).** Path `listCalibrations` bồi đóng tab Calibration MVP-flow-5 (list+detail). BE sẵn `imm11.list_calibrations:71` (bare `@frappe.whitelist()` — cap đọc `calibration.read` + vendor-scope `'Calibration Record'` `apply_vendor_scope` `imm11.py:76`). KHÁC `listPmSchedules`: param **REUSE** `WorkOrderFilters` (JSON-string, mirror `list_pm`/`list_repair` — handler nhận `filters str`). rows-key `data.data[]` mirror `PmWorkOrderListEnvelope`. **22 path / 22 operationId** sau round này. `imm11.py:72-75` ĐÃ có `parse_json`-in-try/except → `_err` (Error-trên-HTTP-200) — KHÁC imm09 round 4 (KHÔNG cần dời `.py`). Guard = `TestMobileListCalibrationsContract` (+7 TC).

> **C-LISTREAD-SCHED (open-thread #4).** Path `listPmSchedules` bồi để form `createPmWorkOrder` không cụt field bắt buộc `pm_schedule` (`imm08.py:788` required `[asset_ref, pm_schedule, due_date]`; `pm_schedule` phải Active + khớp asset). BE sẵn `imm08.list_pm_schedules:122` (bare `@frappe.whitelist()` — cap đọc `pm.read` qua svc/permission_query; KHÔNG `rbac.require` ở handler). KHÁC 3 list path Phase-C: param `asset_ref`/`status` **rời** (component `ScheduleAssetRef`/`ScheduleStatus`), KHÔNG gói JSON `filters` (đúng chữ-ký `list_schedules(asset_ref, status, page, page_size)`). rows-key `data.data[]` mirror `PmWorkOrderListEnvelope`. **17 path / 17 operationId** sau round này (→ **21** sau C6-DETAIL open-thread #4b, §5d C6-DETAIL). Guard = `TestMobileListPmSchedulesContract` (+8 TC).

> **C-LISTREAD-USER (vòng 10 — đóng required-field CỤT của `createCalibration.technician` + `assign_technician.technician`).** Path `listUsers` bồi để 2 form mobile chọn KTV (technician/assignee picker) không cụt: `createCalibration` body có `technician` (Link User) + flow phân công `assign_technician` cần danh sách User hợp lệ. Nếu client KHÔNG có API liệt kê System User (lọc theo role/department/active) → picker rỗng → KHÔNG submit được. BE sẵn `user.list_users:268` (bare `@frappe.whitelist()` nhận GET; KHÔNG `methods=["POST"]`).
>
> - **Grounding 1:1 @source** `assetcore/api/user.py:268-377` (re-verify, KHÔNG bịa):
>   - **Query param = 6 DISCRETE** (KHÔNG JSON `filters` — đúng chữ-ký `list_users(search, department, role, is_active, approval_status, page, page_size)`): `search`/`department`/`role`/`approval_status` = string optional `default ''`; `is_active` = **integer enum [0,1]** optional (map `filters["enabled"]=int(is_active)` `:288`); `page`/`page_size` = **REUSE** `Page`/`PageSize`.
>   - **`role` param `enum` = `_IMM_ROLES` canonical SET** = `Roles.ALL` (`services/shared/constants.py:35` = `SYSTEM_ROLES (4) + DOMAIN_ROLES (26)` = **30 role**). Handler GATE `if role and role in _IMM_ROLES` (`:291`) ⇒ giá trị ngoài SET = no-op (bỏ qua). enum sinh TỪ source (guard introspect `Roles.ALL`), **KHÔNG hardcode literal** trong YAML.
>   - **Element `UserListItem` field-disjoint** (CHỈ field `list_users` emit — KHÔNG ép chung Asset/WorkOrder/Incident; C3-split): `name`(PK, required) · `full_name` · `email` · `enabled` · `user_image` · `role_profile_name` · `department_name` · `is_active` · `imm_approval_status` · `imm_roles[]` (object-array). **`additionalProperties:false`** (closed). Verified emit: base fields `:325-332`, normalize `:353-365`.
>   - **`enabled` + `is_active` = User.enabled Check-fieldtype → `integer` enum [0,1]** (Open#1 int-vs-bool sweep — KHÔNG `type:boolean`). `is_active` = alias `enabled` (`u["is_active"]=u.get("enabled",1)` `:354`). Cả 2 GIỮ vì client có thể đọc một trong hai (handler emit cả hai).
>   - **`imm_roles[]`** = array of object `{name, label, group}` (cả 3 `string`, closed): `name`=role-name (∈ `_IMM_ROLES`), `label`=`ROLE_METADATA[r].label` fallback `r.replace("IMM ","")`, `group`=`ROLE_METADATA[r].group` fallback `"Other"` (`:358-365`). Mảng RỖNG khi user không giữ IMM role.
>   - **`pagination` 4-key** `{page, page_size, total, total_pages}` — ⚠️ **KHÔNG `offset`** (handler build inline `:368-373`, KHÁC `paginate()` 5-key §6). DEDICATED sub-schema `UserListPagination` (closed, 4-key), **KHÔNG `$ref Pagination`** (sẽ buộc `offset` required → strict-codegen deser-crash). [ADR-MOBILE-005](./ADR-MOBILE-005.md).
> - **rows-key `data.items[]`** (mirror `AssetListEnvelope`/`IncidentListEnvelope`; handler `_ok({items, pagination})` `:367` — KHÁC `data.data[]`).
> - **NĐ98 / leak guard:** `list_users` KHÔNG trả financial field (LL-BE-57 mobile-meta no-financial — bản chất đã đúng); `UserListItem` `additionalProperties:false` ⇒ **KHÔNG leak** `password_hash`/`api_key`/`api_secret`/raw `Has Role` child-table (chỉ phơi `name/label/group` đã normalize). Đây là META endpoint (picker) — không phơi PII nhạy cảm ngoài tên/email/phòng/role.
> - **200 = oneOf [`UserListEnvelope`, `Error`]** closed-schema route-by-VALUE `body.success` (pattern **C7**, mirror 4 list path đã có — KHÔNG discriminator). `list_users` bare-whitelist KHÔNG `parse_json` (param discrete) ⇒ KHÔNG dời `.py`; in-handler error (nếu có) đến HTTP-200 + Error. 401→`Unauthorized401`, 403→`Forbidden`.
> - **Path/opId count: 23→24.** `listUsers` vào `_MVP_BUSINESS_PATHS` ⇒ 401∧403 symmetry tự lên. Guard = `TestMobileListUsersContract` (+ guard test chống strict-codegen deser-crash: pagination-4-key-no-offset / role-enum==`Roles.ALL` / is_active∧enabled integer-not-boolean / no-leak-sweep / oneOf-closed-disjoint). **KHÔNG đụng `.py` BE / KHÔNG reload gunicorn / KHÔNG bench migrate** (pure-yaml + guard-test). `tags: [user]` (mirror `getUserInfo`).

**QUYẾT ĐỊNH BA = Option (A) — khai 2 envelope PHÂN BIỆT** (KHÔNG chuẩn-hoá 1 key round này):

- **Lý do (codegen consistency cho repo native):** OpenAPI là hợp đồng máy đọc; nếu khai 1 rows-key chung trong khi runtime trả key khác → model codegen deser **sai key** → rows về **rỗng** (lỗi câm). Khai 2 envelope = nói ĐÚNG wire-shape THẬT cho từng path ⇒ client native parse đúng.
- **KHÔNG sửa service `.py`** (ràng buộc round): chuẩn-hoá rows-key về 1 key chung = đụng service layer + test BE ⇒ hoãn.
- `Pagination` sub-schema **DÙNG CHUNG** cho cả 2 envelope (không đổi).
- **KNOWN-GAP → Phase-E normalize:** thống nhất 2 rows-key (`data` vs `items`) về 1 key chung là việc **Phase-E** (chuẩn hoá envelope, đụng `services/imm08|09|12.py` + test). Tới khi đó, contract phản ánh ĐÚNG di sản 2 service. Quyết định kiến trúc: [`ADR-MOBILE-001.md` (g)](./ADR-MOBILE-001.md).

> **Cross-ref:** quyết định envelope list-read ↔ [ADR-MOBILE-001 (g)](./ADR-MOBILE-001.md) ↔ [11 §1 traceability](./11-phase-a-exit.md). **Scope `reported_by` (A2 finding) — ĐÓNG cho `listIncidents`** qua param opt-in `mine=1` (filter `reported_by==session.user`, tab "Báo hỏng của tôi" MVP-5c; param `IncidentMine`; [ADR-MOBILE-015](./ADR-MOBILE-015.md)); KHÔNG đổi shape (chỉ +1 query-param, path-count GIỮ). **Scope `assigned_to` cho PM — ĐÓNG cho `listPmWorkOrders`** qua param opt-in `mine=1` (filter `assigned_to==session.user`, tab "Phiếu PM của tôi" MVP-5a; param `WorkOrderMine`; [ADR-MOBILE-016](./ADR-MOBILE-016.md)). Scope `assigned_to` cho CM (`listRepairWorkOrders`) vẫn known-gap hành vi — Phase tiếp (đối xứng `mine`).

> **C-LISTREAD-MINE (A2 known-gap closure — `listIncidents` +param `mine`).** TRƯỚC vòng này contract claim "scope reported_by" mà `list_incidents` KHÔNG có cơ chế ⇒ **claim suông**. Bồi `components/parameters/IncidentMine` (`name:mine`, `in:query`, int enum `[0,1]` default `0`, mirror `IncidentOpen` — né int-vs-bool trap) + `$ref` vào `listIncidents.parameters` (set param: 5→**6**) + sửa `description` khớp cơ-chế thật. `mine=1` → `_build_incident_filters` seed `extra["reported_by"]=session.user` **TRƯỚC** quyết định nhánh ⇒ AND với `status`/`severity`/`asset`/`open` KỂ CẢ nhánh status return-sớm; `pagination.total == len(items)` (cùng `filters` dict — INV count==rows). `mine=0`/absent = filters BYTE-IDENTICAL cũ (backward-compat web-FE `IncidentListView`). KHÔNG path mới (path-count GIỮ **46**), KHÔNG component-schema mới (chỉ +1 param component, `$ref`'d ngay ⇒ KHÔNG orphan). **BE Bước-4 delta:** `services/imm12.py` (`_build_incident_filters(..., reported_by="")` seed + `list_incidents(..., mine=0)` resolve `frappe.session.user`), `api/imm12.py` (`list_incidents(..., mine: int = 0)` forward — Guest-guard `:212` **UNCHANGED**), `test_mobile_oas.py` (`_INCIDENT_PARAM_REFS` +`IncidentMine` ⇒ `TC-MOB-OAS-14b` GREEN; +assert shape `IncidentMine` trong `14d`: int default 0 enum `[0,1]`), `test_imm12.py` (mine-filter + backward-compat fence + count==rows + AND-with-status/open). Guard contract = `TC-MOB-OAS-14b/14d`; path-count `TC-MOB-OAS` (46 UNCHANGED — +param ≠ +path).

> **C-LISTREAD-MINE-PM (A2 known-gap closure ĐỐI XỨNG — `listPmWorkOrders` +param `mine`).** Gap "next" nêu đích danh ở [ADR-MOBILE-015](./ADR-MOBILE-015.md) §Consequences. TRƯỚC vòng này contract claim "Scope theo user (count==rows, permission-aware)" mà `list_pm_work_orders` KHÔNG có cơ chế `assigned_to` ⇒ **claim suông**. Bồi `components/parameters/WorkOrderMine` (`name:mine`, `in:query`, int enum `[0,1]` default `0`, mirror `IncidentMine` — né int-vs-bool trap) + `$ref` vào `listPmWorkOrders.parameters` (set param: `{WorkOrderFilters,Page,PageSize}` → **+`WorkOrderMine`**) + sửa `description` khớp cơ-chế thật. `mine=1` → `api/imm08.py::list_pm_work_orders` inject `f["assigned_to"]=session.user` **SAU `apply_vendor_scope`** (`imm08.py:33`) ⇒ AND với mọi key trong `WorkOrderFilters` JSON-blob (kể cả virtual `due_before`/`overdue`); `pagination.total == len(data.data)` (`count_with_or`+`get_all` cùng `filters` dict, `BaseRepository.list` base.py:65-71 — INV count==rows). `mine=0`/absent = filters BYTE-IDENTICAL cũ (backward-compat web-FE `PMWorkOrderListView`). KHÔNG path mới (path-count GIỮ **46**), KHÔNG component-schema mới (chỉ +1 param component, `$ref`'d ngay ⇒ KHÔNG orphan). **KHÁC `IncidentMine`:** inject @api-layer (KHÔNG seed @service) vì PM `filters` là JSON-blob đã `parse_json` @api — **KHÔNG đụng** `services/imm08.py`/repo. **BE Bước-4 delta:** `api/imm08.py` (`list_pm_work_orders(filters, mine: int = 0, page, page_size)` inject), `test_mobile_oas.py` (`_LIST_PARAM_EXPECT[_LIST_PM_PATH]` +`WorkOrderMine` ⇒ `TC-MOB-OAS-14b` GREEN; `_LIST_LIVE_FN[_LIST_PM_PATH]` +`mine`; +assert shape `WorkOrderMine` trong `14d`: int default 0 enum `[0,1]`), `test_imm08.py` (mine-filter + backward-compat fence + count==rows + AND-with-filters). Guard contract = `TC-MOB-OAS-14b/14d`; path-count `TC-MOB-OAS` (46 UNCHANGED — +param ≠ +path).

### 6.3 Pagination DIVERGENT cho `listUsers` — 4-key KHÔNG `offset` (ADR-MOBILE-005)

5/6 list path (`listPm*`/`listRepair*`/`listIncidents`/`listCalibrations`/`listAssets`) dùng `paginate()` (`utils/pagination.py:6`) → **5-key** `{page, page_size, total, total_pages, offset}` (§6). **`listUsers` KHÁC:** `user.list_users` **KHÔNG gọi `paginate()`** — build dict inline `api/user.py:368-373` chỉ **4 key** `{page, page_size, total, total_pages}` (KHÔNG `offset`, `total_pages = max(1, ceil(total/page_size))`).

| Field `pagination.*` | listUsers (`user.list_users`) | 5/6 list khác (`paginate`) |
|---|---|---|
| `page` | ✅ `:369` | ✅ |
| `page_size` | ✅ `:370` | ✅ |
| `total` | ✅ `:371` `frappe.db.count` permission-aware | ✅ |
| `total_pages` | ✅ `:372` `max(1, ceil)` — **floor 1** (KHÁC `paginate` =0 khi total=0) | ✅ `=0` khi total=0 |
| `offset` | ❌ **KHÔNG emit** | ✅ derived |

**Spec decision:** `UserListEnvelope.data.pagination` dùng **DEDICATED schema `UserListPagination`** (`type:object`, `additionalProperties:false`, `required: [page, page_size, total, total_pages]` — 4-key), **KHÔNG `$ref Pagination`**. Lý do: `Pagination` (§6) khai `required: [..., offset]` ⇒ codegen native sinh model bắt buộc `offset` non-null → khi runtime trả body 4-key, strict deserializer (Dart/Kotlin) **crash** (missing required). Khai đúng 4-key = nói SỰ THẬT wire-shape. Xem [ADR-MOBILE-005](./ADR-MOBILE-005.md). Guard: `TestMobileListUsersContract` (pagination 4-key + no-`offset` + `total_pages` floor-1).

### 6.3 List-ELEMENT schema (`PmWorkOrderListItem` / `RepairWorkOrderListItem` / `IncidentListItem`) — C3-split (đóng KNOWN-GAP "KHÔNG ép chung")

Phần tử (`data.data[].items` / `data.items[].items`) từng generic `{type: object}` ⇒ integrator KHÔNG bind được model "phiếu của tôi". C3 ban đầu khai 1 UNION `WorkOrderListItem` (PM∪CM). **C3-split (round này)** tách thành **2 item-schema field-disjoint per-endpoint** (PM ≠ CM field-set), mỗi list path có envelope + item RIÊNG (re-verify @source D4 — mở file, tìm symbol, KHÔNG tin số dòng):

| Element schema | Wire vào | Grounded @source | `required` |
|---|---|---|---|
| `PmWorkOrderListItem` | `PmWorkOrderListEnvelope.data.data[].items` | CHỈ `services/imm08.py::list_work_orders` (PM) — 12 repo-field + enrich `asset_name`/`location_name`/`assigned_to_name`/`supervisor_name` = 16 field | `[name]` |
| `RepairWorkOrderListItem` | `RepairWorkOrderListEnvelope.data.data[].items` | CHỈ `services/imm09.py::list_work_orders` (CM) — 16 repo-field (`parts_hold_started` bị `r.pop()`) + enrich `department_name`/`location_name`/`assigned_to_name` + derived `is_sla_breached`/`sla_paused` = 21 field | `[name]` |
| `IncidentListItem` | `IncidentListEnvelope.data.items[].items` | `services/imm12.py::list_incidents` (23 repo-field) + `_enrich_asset_names` (asset_name/reporter_name/assigned_to_name) + `_enrich_sla_breach` (is_response_breached/is_resolution_breached) | `[name]` |
| `PmScheduleListItem` | `PmScheduleListEnvelope.data.data[].items` | CHỈ `services/imm08.py:984 ::list_schedules` — 10 repo-field (`name`/`asset_ref`/`pm_type`/`status`/`pm_interval_days`/`checklist_template`/`responsible_technician`/`last_pm_date`/`next_due_date`/`alert_days_before`) + enrich `asset_name` = 11 field. **KHÔNG Check field** ⇒ 0 prop `type:boolean` (né int-vs-bool trap Open#1; 2 Int = `pm_interval_days`/`alert_days_before` khai `integer`). `pm_type`/`status` enum 1:1 Select `pm_schedule.json`. Field-disjoint với PM/CM-WorkOrder-only | `[name]` |
| `CalibrationListItem` | `CalibrationListEnvelope.data.data[].items` | CHỈ `services/imm11.py:937 ::list_calibrations` — 12 repo-field (`name`/`asset`/`device_model`/`calibration_type`/`status`/`scheduled_date`/`actual_date`/`technician`/`overall_result`/`next_calibration_date`/`lab_supplier`/`is_recalibration`) + 3 enrich `asset_name`/`lab_name`/`technician_name` (`imm11.py:972-974`) = **15 field**. `is_recalibration` = **Check fieldtype** @IMM Asset Calibration DocType ⇒ `integer enum[0,1]` (Open#1 int-vs-bool sweep — KHÔNG `boolean`); ĐÚNG 1 prop integer-enum (2 Check khác `capa_closed`/`calibration_sticker_attached` KHÔNG nằm trong svc fields). `calibration_type`/`status`/`overall_result` enum 1:1 Select-options DocType (`External`/`In-House` · `Scheduled`…`Cancelled` · `''`/`Passed`/`Failed`/`Conditionally Passed`). **0 financial prop** (`gross_purchase_amount`/`accumulated_depreciation`/`current_book_value`) — `list_calibrations` vốn KHÔNG trả (LL-BE-57 mobile-meta no-financial, né sẵn). Field-disjoint với WO/Incident item (KHÔNG `asset_ref`/`repair_type`/`severity` — C3-split, KHÔNG ép chung) | `[name]` |
| `AssetListItem` | `AssetListEnvelope.data.items[].items` (rows-key `items` — mirror `IncidentListEnvelope`) | `imm00.api::list_assets` — **14 base** field (`fields=[…17]` `imm00.py:427-434` TRỪ 3 financial: `name`/`asset_name`/`asset_code`/`lifecycle_status`/`asset_category`/`location`/`department`/`responsible_technician`/`supplier`/`device_model`/`next_pm_date`/`next_calibration_date`/`byt_reg_expiry`/`gmdn_code`) + **6 enrich** (`imm00.py:444-449`: `category_name`/`department_name`/`location_name`/`supplier_name`/`device_model_name`/`responsible_technician_name`) = **20 field**. **3 financial-field** (`gross_purchase_amount`/`accumulated_depreciation`/`current_book_value`) handler CÓ trả `@:433` NHƯNG **EXCLUDED** khỏi list-item (LL-BE-57 mobile-meta no-financial — KTV không cần giá; guard RED nếu ai thêm). **0 Check field** ⇒ 0 prop `type:boolean` (né int-vs-bool trap Open#1). `lifecycle_status` = `string` **KHÔNG enum cứng** (Select AC Asset nhiều giá trị, để string mô tả — tránh codegen vỡ khi thêm trạng thái). Field-disjoint với WO/Incident/Calibration item (KHÔNG `repair_type`/`severity`/`is_recalibration` — C3-split) | `[name]` |

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
3. **GET-list → `listX`:** `list_pm_work_orders` → `listPmWorkOrders`; `list_repair_work_orders` → `listRepairWorkOrders`; `list_incidents` → `listIncidents`; `list_calibrations` → `listCalibrations`.
4. **`create_X` → `createX`:** `create_pm_work_order` → `createPmWorkOrder`; `create_repair_work_order` → `createRepairWorkOrder`; `create_calibration` → `createCalibration`.
5. **`get_X` → `getX`:** `get_asset` → `getAsset`; `get_asset_scan_info` → `getAssetScanInfo`; **(C6-DETAIL)** `get_pm_work_order` → `getPmWorkOrder`; `get_repair_work_order` → `getRepairWorkOrder`; `get_incident` → `getIncident`; `get_calibration` → `getCalibration`.
6. **`report_X` → `reportX`:** `report_incident` → `reportIncident`.
7. **`resolve_qr_token` → `resolveQrToken`** (token/QR viết liền theo CamelCase từng từ snake).
8. **OAuth = verb-first** (provider Frappe `frappe.integrations.oauth2.*`): vì gốc-tail (`authorize`/`get_token`/`revoke_token`) KHÔNG mang ngữ cảnh "OAuth", thêm hậu tố `OAuth` để rõ + tránh va tên: `authorize` → `authorizeOAuth`; `get_token` → `getOAuthToken`; `revoke_token` → `revokeOAuthToken`. **(C4)** `openid_profile` (userinfo/whoami) → **`getUserInfo`** — verb-first nhóm auth, NHÃN ngữ-nghĩa "userinfo" rõ hơn tail thô `openidProfile`.
9. **2 device-token GIỮ NGUYÊN TÊN** (chốt **A5**, KHÔNG đổi để tránh drift client đã sinh): `register_device_token` → **`registerDeviceToken`**; `unregister_device_token` → **`unregisterDeviceToken`** (theo đúng luật 4/2, đã đặt sẵn từ A5).

**Bảng 21/21 operationId (A10 + C4 + C-LISTREAD-SCHED + C6-DETAIL — codegen-able):**

| `operationId` | Verb | RPC path (`/api/method/...`) |
|---|---|---|
| `authorizeOAuth` | GET | `frappe.integrations.oauth2.authorize` |
| `getOAuthToken` | POST | `frappe.integrations.oauth2.get_token` |
| `revokeOAuthToken` | POST | `frappe.integrations.oauth2.revoke_token` |
| `getUserInfo` | GET | `frappe.integrations.oauth2.openid_profile` *(C4 — OIDC userinfo/whoami)* |
| `resolveQrToken` | GET | `assetcore.api.imm00.resolve_qr_token` |
| `getAssetScanInfo` | GET | `assetcore.api.imm00.get_asset_scan_info` |
| `getAsset` | GET | `assetcore.api.imm00.get_asset` |
| `getPmWorkOrder` | GET | `assetcore.api.imm08.get_pm_work_order` *(C6-DETAIL)* |
| `getRepairWorkOrder` | GET | `assetcore.api.imm09.get_repair_work_order` *(C6-DETAIL)* |
| `getIncident` | GET | `assetcore.api.imm12.get_incident` *(C6-DETAIL)* |
| `getCalibration` | GET | `assetcore.api.imm11.get_calibration` *(C6-DETAIL)* |
| `reportIncident` | POST | `assetcore.api.imm12.report_incident` |
| `createPmWorkOrder` | POST | `assetcore.api.imm08.create_pm_work_order` |
| `createRepairWorkOrder` | POST | `assetcore.api.imm09.create_repair_work_order` |
| `createCalibration` | POST | `assetcore.api.imm11.create_calibration` |
| `listPmWorkOrders` | GET | `assetcore.api.imm08.list_pm_work_orders` |
| `listPmSchedules` | GET | `assetcore.api.imm08.list_pm_schedules` *(C-LISTREAD-SCHED)* |
| `listRepairWorkOrders` | GET | `assetcore.api.imm09.list_repair_work_orders` |
| `listIncidents` | GET | `assetcore.api.imm12.list_incidents` |
| `listCalibrations` | GET | `assetcore.api.imm11.list_calibrations` *(C-LISTREAD-CAL)* |
| `listAssets` | GET | `assetcore.api.imm00.list_assets` *(C-LISTREAD-ASSET)* |
| `listUsers` | GET | `assetcore.api.user.list_users` *(C-LISTREAD-USER — technician/assignee picker)* |
| `getAssetIncidentHistory` | GET | `assetcore.api.imm12.get_asset_incident_history` *(FLOW-2 DEVICE-PROFILE — lịch-sử sự-cố của asset, màn hồ-sơ sau quét QR)* |
| `getUserContext` | GET | `assetcore.api.layout.get_user_context` *(FLOW-1 BOOTSTRAP — session who-am-I, màn home sau login; `allow_guest=True` ⇒ slot {200,401} KHÔNG 403)* |
| `confirmInspection` | POST | `assetcore.api.imm09.confirm_inspection` *(FLOW-5 TERMINAL-THẬT — nghiệm-thu sau sửa chữa, Pending Inspection→Completed)* |
| `markNotificationAsRead` | POST | `assetcore.api.layout.mark_notification_as_read` *(FLOW-6 READ-RECEIPT — WRITE-action ĐẦU TIÊN trên Notification Log, set read=1; đóng dead-end listNotifications read-only)* |
| `markAllAsRead` | POST | `assetcore.api.layout.mark_all_as_read` *(FLOW-6 MARK-ALL-READ — BULK read-receipt, set read=1 cho MỌI Notification Log chưa-đọc của user; ĐÓNG NỐT notification-center action-set sau markNotificationAsRead single; 0-PARAM ⇒ KHÔNG requestBody)* |
| `pingSession` | GET | `assetcore.api.layout.ping_session` *(SESSION-PROBE — CSRF warm-up + app-resume who-am-I-lite, `{user, authenticated, csrf_token}`; 0-PARAM ⇒ KHÔNG requestBody; `allow_guest=True` + handler LUÔN `_ok` (0 `_err` in-handler) ⇒ **200 = SINGLE schema `PingSessionEnvelope` KHÔNG oneOf [Env, Error]** + **slot {200}-only** — KHÁC `getUserContext` {200,401} (có guest-guard `_err(401)` `layout.py:206-207`); ĐÓNG NỐT cặp session-lifecycle còn lại sau notification quartet R38-R41)* |
| `registerDeviceToken` | POST | `assetcore.api.mobile.v1.register_device_token` *(A5 — giữ nguyên)* |
| `unregisterDeviceToken` | POST | `assetcore.api.mobile.v1.unregister_device_token` *(A5 — giữ nguyên)* |

**Invariant (guard test):** mọi path-operation CÓ `operationId`; `operationId` **duy nhất** toàn file (`len(set)==len(list)==29` — C4 +`getUserInfo`, C-LISTREAD-SCHED +`listPmSchedules`, C6-DETAIL +4 GET-detail, C-LISTREAD-CAL +`listCalibrations`, C-LISTREAD-ASSET +`listAssets`, C-LISTREAD-USER +`listUsers`, **C8-ACTION +`acknowledgeIncident`/`startRepair`/`submitDiagnosis`/`assignTechnician`/`startWork`/`resolveIncident`/`closeWorkOrder`/`submitCalibration`/`closeIncident`**, **C8-ACTION-PM +`submitPmResult`**, **C-LISTREAD-NOTIF +`listNotifications`**); khớp regex camelCase; 2 device-token tên đóng băng; **sau EPIC-D D4 (§8.9): `_STUB_PATHS = ∅` (0 STUB-on-MVP)** — 2 device-token (`register`/`unregister`) ĐÃ rời STUB với typed `requestBody DeviceTokenRequest` + 200 oneOf `[<Created>, Error]` (service D2 `mobile_device_token.py` tồn tại @source). 4 read/create cũ (2 QR + `get_asset` + `createPmWorkOrder`) ĐÃ rời STUB ở R4 §8.7 (cùng `report_incident` §8.3, 3 list §8.4, `createRepairWorkOrder` §8.5, `createCalibration` §8.6). `responses/Stub` HẾT referenced → forward-reserve (§8.2 RESERVED + `_RESERVED_ORPHANS`). Guard = `assetcore/tests/test_mobile_oas.py` (TC-MOB-OAS-01..07 + 20 + **22** device-token typed, read-only yaml — KHÔNG đọc auto-gen AssetCore spec). **Phase C/R4/D4** khi bồi path PHẢI: (a) đặt `operationId` theo luật trên, (b) thêm dòng vào map `_EXPECTED` của guard test, (c) GROUNDED chữ-ký service THẬT KHÔNG đổi `operationId`, (d) gỡ path tương ứng khỏi `_STUB_PATHS` của guard khi bồi schema thật (NHƯNG giữ symmetry trong `_MVP_BUSINESS_PATHS`/`_DEVICE_TOKEN_FROZEN` để 401/403 KHÔNG vỡ — xem §8.3/§8.4/§8.6/§8.7/§8.9).

> ⚠️ **A10 chỉ thêm contract-identity** (`operationId`) — KHÔNG bồi `requestBody`/`response` schema chi tiết. Phase-C đã bồi **requestBody** cho `report_incident` (§8.3) + **list-read** cho 3 list path (§8.4) + **requestBody** cho `createRepairWorkOrder` (§8.5) + **requestBody** cho `createCalibration` (§8.6); **R4 §8.7** type tiếp **`data`** cho 4 read/create (2 QR + `get_asset` + `createPmWorkOrder`) GROUNDED chữ-ký service THẬT ⇒ **chỉ CÒN 2 device-token STUB** (`[ROADMAP]` BE chưa impl).

### 8.2 Contract integrity & codegen-validity (SSoT allow-list orphan — A12)

> KHÁC §8.1 (đặt **tên** `operationId`). §8.2 bảo đảm yaml **resolve được** để `openapi-generator` chạy KHÔNG crash + KHÔNG để **dead contract-surface** (component thừa lén tích tụ). Đây là **anti-regression guard** — yaml hiện tại đã đạt (verify @source 2026-06-09).

**Vì sao quan trọng (codegen-validity):** `openapi-generator` (Dart/dio, TS-axios — [`09-native-repo-guide.md §2`](./09-native-repo-guide.md)) **resolve mọi `$ref` trước khi sinh model**. Một `$ref` trỏ tới component KHÔNG tồn tại (**dangling**) ⇒ generator **crash hoặc sinh model rỗng** (codegen-invalid). Một component **defined-nhưng-không-`$ref`'d** (**orphan**) thì codegen vẫn chạy NHƯNG là **dead surface** — nếu thừa lén tích tụ sẽ phình client sinh ra bằng model không ai dùng + che giấu hợp đồng đã chết. Vì vậy 2 ràng buộc CHỐT:

1. **0 dangling `$ref`** — MỌI `$ref: '#/components/...'` (và mọi pointer cục bộ `#/...`) trỏ tới node **TỒN TẠI** (hard-fail; dangling = codegen crash).
2. **Orphan ⊆ allow-list RESERVED** — tập component defined-không-`$ref`'d PHẢI nằm trong allow-list cố định **11 mục** dưới (lịch sử: A13 10 → C-LISTREAD 9 → G-REQBODY 7 → C-REQBODY-CREATEREPAIR 6 → C-REQBODY-CREATECAL 6 → G-OAS-STATUSLINE 9 → D4-Stub 10 → **FLOW6-PUSH 11 (+`schemas/PushMessageData` component-only FCM transport ngoài HTTP)**). Orphan **NGOÀI** allow-list = FAIL (chống dead surface lén lút). Mỗi mục allow-list là **forward-reserve có chủ ý** (Phase E sẽ wire) HOẶC **transport-ngoài-HTTP** (FLOW6 — KHÔNG bao giờ wire path) HOẶC **false-orphan** (dùng qua keyword khác `$ref`).

> **A13 — coverage 401/429 đã wire (orphan 11→10):** vòng A13 wire `Unauthorized401` lên **10 path nghiệp vụ STUB** (cùng 2 device-token đã có 401 từ A5 ⇒ **toàn bộ 12 path MVP declare 401**; bearer hết hạn → refresh/re-auth — §4 row `UNAUTHORIZED` + §5 ngoại lệ 401 + [`ADR-MOBILE-001.md (e)`](./ADR-MOBILE-001.md)) và wire `RateLimited429` lên **ĐÚNG 2 path có `@rate_limit` THẬT** (`imm00.resolve_qr_token` `imm00.py:311` + `imm00.get_asset_scan_info` `imm00.py:354` — §5 row 429). ⇒ `RateLimited429` **HẾT orphan** → đã **gỡ khỏi bảng RESERVED dưới + `_RESERVED_ORPHANS`** (đồng bộ 1 nhịp, nếu không `TC-MOB-OAS-10` stale-check ĐỎ). `Unauthorized401` từ trước **KHÔNG** ở RESERVED (device-token đã dùng) → allow-list 401 KHÔNG đổi. `NotFound404`/`Unprocessable422` **VẪN reserve** (404/422 phụ thuộc requestBody/asset-lookup → **Phase C**, chống scope-creep). 3 auth path GIỮ NGUYÊN (302/200 — Frappe core).

> **A16 — ERROR-STATUS contract fix (tách 401 vs 403 + body raw THẬT; orphan VẪN 10):** vòng A16 (1) wire `'403'`→`Forbidden` lên **TẤT CẢ 12 path MVP** (10 business STUB **đã** có 403 từ A13-wiring + **bổ sung 2 device-token** `register/unregister_device_token` hiện thiếu — bearer-gated self-service [`06-push-fcm.md §2.3`](./06-push-fcm.md), guest/no-token cũng `PermissionError` 403 `__init__.py:876`) ⇒ **tập path-403 == tập path-401 (12==12, đối xứng)**. `Forbidden` **KHÔNG** ở RESERVED (đã referenced từ A13 — wire thêm 2 device-token KHÔNG đổi orphan). (2) **+component `schemas/FrappeRawError`** {`exc_type`* req · `exception?`/`exc?`/`_server_messages?` opt} source-char @`frappe/utils/response.py` V1 (`exc_type` `:46`; `exception` `:43-45` gated; `exc` `:185`; `_server_messages` `:188`) + **repoint** `Unauthorized401`/`Forbidden`/`RateLimited429` `$ref` từ `schemas/Error` → `schemas/FrappeRawError` (3 response pre-handler raw — KHÔNG Error envelope) ⇒ codegen sinh model KHỚP body runtime (KHÔNG deser-fail). `FrappeRawError` được `$ref` **NGAY** bởi 3 response ⇒ **KHÔNG orphan** → KHÔNG vào allow-list. (3) `RateLimited429` **KHÔNG** thêm `Retry-After`/`X-RateLimit-*` (P2 DEFER — `conf.rate_limit=null` ⇒ 0 backoff-header, §5). 3 auth path GIỮ NGUYÊN (302/200/400 — KHÔNG declare 403). **DIFF A16** = +1 schema (`FrappeRawError`) + repoint 3 `$ref` + wire `'403'` lên 2 device-token. `operationId` FROZEN, 0 path mới.

**Bảng RESERVED — 11 orphan-component hợp lệ (SSoT của allow-list; guard `TC-MOB-OAS-10` phản chiếu bảng này):**

> **FLOW6-PUSH (2026-06-15, orphan 10→11):** `schemas/PushMessageData` **VÀO RESERVED** — flow-6 push data-payload (FCM `message.data` HTTP v1) là **transport NGOÀI REST AssetCore** ⇒ schema KHÔNG được `$ref` bởi BẤT KỲ HTTP path nào (push không đi qua path). GIỮ làm **component-only forward-reserve**: codegen mobile sinh model `PushMessageData` để parse `RemoteMessage.data` (client native ĐỌC 4 key `doctype/name/event/deeplink` → route deep-link). KHÔNG-wire-path = đúng-bản-chất (KHÁC offline-reserve sẽ-wire-Phase-E; FLOW6 KHÔNG BAO GIỜ wire path vì không phải HTTP). GROUNDED `utils/fcm.py:94-98` + `services/notifications.py:443-454` + [`06-push-fcm.md §4.1a`](./06-push-fcm.md). ⇒ orphan **10→11**.

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
| `schemas/PushMessageData` | **FLOW6 transport-ngoài-HTTP** | flow-6 push = FCM data-payload (`message.data` HTTP v1), KHÔNG qua path REST AssetCore ⇒ schema **component-only** (codegen mobile sinh model parse `RemoteMessage.data` → route deep-link). KHÔNG-wire-vào-path = ĐÚNG-bản-chất (KHÔNG dead-surface lén). GROUNDED `utils/fcm.py:94-98` (4 key) + `services/notifications.py:443-454` (5 `event`). | [`06-push-fcm.md §4.1a`](./06-push-fcm.md) + `test_mobile_oas.py::_RESERVED_ORPHANS` |
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
- `TC-MOB-OAS-10` (orphan allow-list): tập component defined-không-`$ref`'d PHẢI **⊆** allow-list **11 mục** bảng RESERVED trên; orphan NGOÀI allow-list = FAIL; mục allow-list không-còn-orphan (đã wire) = FAIL (allow-list stale). `OAuth2` BẮT BUỘC ∈ allow-list (false-orphan — KHÔNG forbid naive). Số defined/referenced **runtime-derived** bởi guard (walk stdlib, KHÔNG hardcode) — allow-list-size = **11** (`_RESERVED_ORPHANS` đếm @source 2026-06-15). **FLOW6-PUSH (2026-06-15):** +`schemas/PushMessageData` (flow-6 FCM data-payload component-only, transport ngoài HTTP) ⇒ allow-list 10→11, defined +1, orphan +1 (KHÔNG `$ref` bởi path nào — đúng-bản-chất). [SUPERSEDED snapshot cũ "45 defined − 39 referenced = 6 orphan" của C-REQBODY-CREATECAL — đã drift qua C7/CAL/ASSET/ASCAN-PARITY/FLOW6; guard tự tính số THẬT, prose KHÔNG hardcode lại].
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
| `occurred_datetime` | `string` (**KHÔNG** `format`) | ⬜ optional | — (DocType `Datetime`) | `incident_report.json` `occurred_datetime` (`Datetime`) · `imm12.py:83` · svc `services/imm12.py:350,376-382` — **G1/CR-16 §8.3a** |

> **`source` KHÔNG ở requestBody** — provenance nguồn báo hỏng (`'qr-scan'`/`'manual'`) do **server gán/coerce** (`imm12.py:83` default `'manual'`; tầng mobile coerce `'qr-scan'`), client **KHÔNG gửi**. Đưa `source` vào body = leak field server-controlled ⇒ guard `TC-MOB-OAS-13(e)` chặn.
>
> **`occurred_datetime` ĐÃ wire vòng này** (G1/CR-16, **§8.3a** bên dưới) — graduate ra khỏi nhóm optional-backlog; required GIỮ EXACT 4 (occurred_datetime là optional, KHÔNG vào `required[]`).
>
> **8 param optional CÒN LẠI** (`fault_code`/`workaround_applied`/`clinical_impact`/`patient_affected`/`patient_impact_description`/`immediate_action`/`linked_repair_wo` + `source`) = **Phase-C kế** — CHƯA bồi (giữ surface tối thiểu = 4 field bắt buộc + occurred_datetime). enum/required KHỚP 1:1 DocType, KHÔNG bịa.

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

#### 8.3a G1/CR-16 — wire `occurred_datetime` vào `ReportIncidentRequest` (báo hỏng F2 · contract-only · handler ĐÃ LIVE)

> **Bản chất = đóng drift handler↔yaml (KHÔNG đụng code).** Handler `report_incident` ĐÃ nhận `occurred_datetime` tại source (`api/imm12.py:83` `occurred_datetime: str = ""` → `services/imm12.py:350,376-382`) NHƯNG `ReportIncidentRequest` trong yaml CHƯA khai prop ⇒ mobile codegen KHÔNG sinh field ⇒ app KHÔNG gửi được "thời điểm sự cố thực sự xảy ra". F2 = vòng-2 của slice báo-hỏng (F1 = §8.3 C-REQBODY/G-REQBODY). **Chỉ sửa CONTRACT + guard test** — TUYỆT ĐỐI KHÔNG đụng `api/imm12.py`/`services/imm12.py` (đã wire) ⇒ KHÔNG reload gunicorn (LL-DEPLOY-07).

**Delta yaml (đúng 1 component — `schemas/ReportIncidentRequest`):**
- `properties` **THÊM** `occurred_datetime`:
  ```yaml
  occurred_datetime:
    type: string          # KHÔNG format: date-time — xem lý do dưới
    description: >
      Thời điểm sự cố THỰC SỰ xảy ra (có thể TRƯỚC lúc báo). Frappe wire
      space-separated `yyyy-MM-dd HH:mm:ss` (KHÔNG ISO-8601 `T`). Optional —
      rỗng → server fallback `reported_at` (services/imm12.py:382). KHÔNG được
      ở tương lai → 422 `IMM12-OCCURRED-DATETIME-FUTURE` (services/imm12.py:378-379).
  ```
- `required` **GIỮ EXACT 4** = `[asset, incident_type, severity, description]` — `occurred_datetime` là **optional** (handler default `=""` `api/imm12.py:83`) ⇒ **KHÔNG** vào `required[]`. (13c GIỮ GREEN.)

**Vì sao `type: string` TRẦN — KHÔNG `format: date-time` (decision):** Frappe serialize/đọc `Datetime` ở dạng **space-separated `yyyy-MM-dd HH:mm:ss`** (vd `2026-06-27 08:15:00`), KHÔNG phải ISO-8601 RFC-3339 (`...T08:15:00`). `format: date-time` ⇒ codegen ép kiểu `DateTime`/validator RFC-3339 → client serialize `T`-form (hoặc reject space-form) → lệch wire-format Frappe `get_datetime` (`services/imm12.py:377`). Giữ `string` trần + nêu format trong `description` ⇒ mobile-dev gửi đúng chuỗi Frappe. (Cùng pattern các Datetime-prop khác trong yaml.)

**Response surface — KHÔNG đổi:** future-guard `IMM12_OCCURRED_DATETIME_FUTURE` map `http_status=422` (`utils/messages.py:801`) ⇒ là **nguồn 422 THỨ HAI** trên CÙNG path (cạnh BR-12-01 Critical→clinical_impact `services/imm12.py:359`). `422`→`Unprocessable422` ĐÃ declare (§8.3 G-REQBODY) ⇒ **KHÔNG status mới**. 200/401/403/404/422 GIỮ NGUYÊN; symmetry 401==403 (12==12) BẤT BIẾN.

**Bất biến (anti-scope-creep):** KHÔNG path mới (**43 GIỮ**) · KHÔNG verb-flip ⇒ runtime baseline `d12`/`d15`/`d17` get/post (**234/254**) KHÔNG đổi · KHÔNG đụng `requestBodies/ReportIncidentBody` (body $ref unchanged — prop mới nằm TRONG schema) · KHÔNG bồi 8 optional còn lại.

**Test contract (guard chạy được — class `TestMobileReportIncidentBody`):**
- **TC-MOB-OAS-13g** (MỚI, +1) — `occurred_datetime` optional-typed + reverse-drift parity:
  - (1) `occurred_datetime` ∈ `ReportIncidentRequest.properties`;
  - (2) `properties.occurred_datetime.type == "string"`;
  - (3) **KHÔNG** key `format` trong `occurred_datetime` (anti ISO-T — chống codegen ép RFC-3339);
  - (4) `occurred_datetime` ∉ `required` (optional — 13c vẫn EXACT 4);
  - (5) **PARITY** chống-drift-đảo: `inspect.signature(assetcore.api.imm12.report_incident).parameters` CÓ `occurred_datetime` ⇒ MỌI prop khai trong yaml ⊆ live-handler-param (contract KHÔNG được khai field handler KHÔNG nhận).
- **TC-MOB-OAS-13c** GIỮ GREEN (`required` vẫn EXACT 4).
- Đếm: `_EXPECTED_TEST_COUNT` **407→408** (`tests/test_mobile_oas.py:186`, +1 = 13g) · `_GUARD_SUITE_EXPECTED["test_mobile_oas"]` **+1** & `_MOBILE_OAS_TOTAL` **576→577** (`tests/test_mobile_docset.py:1031`) — khớp đếm thực.
- Chạy: `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` + `... test_mobile_docset` GREEN. **KHÔNG curl-live** (handler đã LIVE, verify bằng test — LL-DEPLOY-07).

**Boundaries (chốt cho BE):**
- **Always:** prop `occurred_datetime` `type:string` trần + description nêu wire-format Frappe; grounded `file:line` (KHÔNG bịa); guard reverse-drift bằng `inspect.signature` live handler; cập nhật cả 3 con-số đếm (`_EXPECTED_TEST_COUNT`/`_GUARD_SUITE_EXPECTED`/`_MOBILE_OAS_TOTAL`) cùng nhịp.
- **Never:** thêm `format: date-time` · đẩy `occurred_datetime` vào `required[]` · thêm path/verb/status-code mới · sửa `api/imm12.py`/`services/imm12.py` · reload/restart/migrate/commit · curl-live verify.

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
| `imm00.get_asset_scan_info` (`getAssetScanInfo`) | oneOf `[AssetScanInfoEnvelope \| Error]` (**C6** §5c read-path) | `AssetScanInfo` ← `services/imm00.py:764-840` (**16 field** ↑12, C-ASCAN-PARITY drift-closed) | `name, asset_code, asset_name, manufacturer_sn, risk_classification, lifecycle_status, device_model_name, location_name, next_pm_date?, next_calibration_date?, pm_overdue, calibration_overdue, warranty_expiry_date?, warranty_expired, recent_maintenance?, available_actions[]` |
| `imm00.get_asset` (`getAsset`) | oneOf `[AssetDetailEnvelope \| Error]` (**C6** §5c read-path) | `AssetDetail` ← `api/imm00.py:288-324` (AC Asset `as_dict()` enrich + 2 overdue) | core: `name, asset_code, lifecycle_status, *_name…, next_*_date?, pm_overdue, calibration_overdue` (`additionalProperties:true` vì `as_dict()` surface field doctype denormalized) |
| `imm08.create_pm_work_order` (`createPmWorkOrder`) | oneOf `[CreatePmWorkOrderCreatedEnvelope \| Error]` (§5c) | `CreatePmWorkOrderResponse` ← `services/imm08.py:836-840` | `name, status, checklist_items_count` |

> 🔵 **C6 — read-path P1 closure (2026-06-11):** 3 GET read 200 ĐÃ ĐỔI từ single `$ref <ReadEnvelope>` → **oneOf `[<ReadEnvelope>, Error]`** CLOSED-SCHEMA Decision-B (KHÔNG discriminator, mirror create §5c). LÝ DO: in-handler business error của 3 read **arrive HTTP-200 + Error body** — y hệt create-path P1: **404** (`_err(…,404)` — `get_asset` `imm00.py:297` / `resolve_qr_token` `imm00.py:366` / `get_asset_scan_info` `imm00.py:416,425`) + **vendor-IDOR-403** (`assert_vendor_can_access` → `ServiceError(FORBIDDEN)` **caught** → `_err(e.message, e.code)` — `get_asset` `imm00.py:302` / `resolve` `imm00.py:371` / `scan-info` `imm00.py:421`). TRƯỚC C6, 200 single-`$ref` ⇒ codegen KHÔNG có deser-branch `Error` cho read → in-handler 404/403 = **dead-deser**. Sau C6, 2 nhánh máy-phân-biệt bằng `additionalProperties:false` (ENVELOPE-level) + disjoint required-set (`[success,data]` vs `[success,error,code,http_status]`) ⇒ codegen route ĐÚNG theo `body.success`/`body.http_status` (KHÔNG cần discriminator boolean — illegal OAS 3.x). **dispatcher-403** (guest/no-token; `resolve`/`scan-info` thêm `rbac.require('asset.read')`; `getAsset` whitelist-only) GIỮ status-line key `403` (trip TRƯỚC `handle()`). `getAsset.data` (`AssetDetail`) GIỮ `additionalProperties:true` (as_dict surface field) — KHÔNG ảnh hưởng disjoint vì ĐÓNG ở tầng **envelope**. Guard: `TC-MOB-OAS-24a..d` (`TestMobileRead200OneOfClosed`) + `TC-MOB-OAS-20a` cập nhật.

- **`AvailableAction`** (element của `available_actions[]`) = shape CHÍNH XÁC `{key, label, route, enabled, reason}` ← `_build_available_actions` (`services/imm00.py:528-534`); `enabled = has_cap ∩ lifecycle_allows` (SSoT). **KHÔNG chứa `qr_token`** (no-raw-token parity).
- **`pm_overdue`/`calibration_overdue`** = **SERVER-FLAG SSoT** (`_is_pm_overdue`/`_is_calibration_overdue`, tz-safe, exempt BLOCKED_FOR_WO) — FE **CHỈ render cờ**, KHÔNG so ngày client (memory: overdue-server-flag-SSoT).
- **`manufacturer_sn`/`risk_classification`/`warranty_expiry_date`/`warranty_expired`** (C-ASCAN-PARITY drift-closed — 4 field BE emit thật, TRƯỚC vòng thiếu trong schema closed `additionalProperties:false` → strict codegen drop/crash): `manufacturer_sn` = số serial NSX (`AC Asset.manufacturer_sn` Data + `_str_or_blank` → **string** '' khi rỗng, KHÔNG null; định danh truy xuất NĐ98) `imm00.py:775`; `risk_classification` = phân loại rủi ro RAW-EN `[Low/Medium/High/Critical]` hoặc '' (`Select` + `_str_or_blank` → **string KHÔNG enum cứng** vì BE coalesce '' — mirror `lifecycle_status`; FE map nhãn VI; KHÔNG nhầm `risk_class` A/B/C/D) `imm00.py:782`; `warranty_expiry_date` = ngày hết bảo hành YYYY-MM-DD hoặc null (`_date_str_or_none` → **string·date·nullable**, parity `next_pm_date`; NGOÀI required) `imm00.py:827`; `warranty_expired` = **SERVER-FLAG boolean** (`_is_warranty_expired`, tz-safe STRICT `<`, no client-clock; ĐỘC LẬP `lifecycle_status` no-exempt — bảo hành = sự kiện HỢP ĐỒNG) `imm00.py:832`. NO-FINANCIAL (LL-BE-57): 4 field KHÔNG nhạy cảm (serial/rủi-ro/bảo-hành ≠ giá mua/khấu hao/book-value) — hợp lệ mobile-meta. Guard: `TestMobileAssetScanInfoFieldParity` (8 TC, RED-before/GREEN-after + forward parity-sweep service-keys ⊆ schema).
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

### 8.10 C8-ACTION — POST-action lifecycle (`acknowledgeIncident` ĐẦU TIÊN: Open→Acknowledged)

> **Quyết định kiến trúc:** [`ADR-MOBILE-006.md`](./ADR-MOBILE-006.md). Đây là **path POST-action ĐẦU TIÊN** trong contract mobile — thiết lập mẫu chung cho mọi lifecycle-transition kế tiếp (`start_work`/`resolve`/`close`/`cancel`/`create_rca` + action module khác). Mục đích: màn incident-detail (`getIncident`, §C6-DETAIL) thoát **dead-end read-only** — KTV mở chi tiết → có nút "Tiếp nhận".

**Endpoint:** `POST /api/method/assetcore.api.imm12.acknowledge_incident` — opId `acknowledgeIncident`. **POST-ONLY** (`@frappe.whitelist(methods=['POST'])` `api/imm12.py:233` — path CHỈ key `post`). Cap: `corrective.investigate` (`_can_investigate = rbac.can` `imm12.py:240`).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | INLINE `application/json` `$ref AcknowledgeIncidentRequest` (`required:true`, KHÔNG component — action 1-schema). | — |
| `AcknowledgeIncidentRequest` | closed `{name string REQUIRED, notes string opt default'', assigned_to string opt default''}` | signature `acknowledge_incident(name, notes='', assigned_to='')` `imm12.py:234` (`name` positional ⇒ required) |
| **200** | oneOf `[IncidentActionEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `IncidentActionEnvelope.data` | `IncidentActionResponse` closed `{name string, status string}` — `status` Select-canonical 7-state, post-ack = `Acknowledged`. **Tên generic** (KHÔNG `Acknowledge*`) ⇒ tái dùng cho `start_work`/`resolve`/`close`. | `svc_acknowledge` return `{'name':name,'status':doc.status}` `services/imm12.py:469`; `_STATUS_ACKNOWLEDGED` `imm12.py:451`; `incident_report.json` Select |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`, chỉ `FrappeRawError`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403** (`ReportIncidentForbidden`): in-handler cap-403 (`imm12.py:241`) trả HTTP-200 + Error ⇒ ĐÃ phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403. | `imm12.py:240-241` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409/422` (lỗi nghiệp vụ in-handler arrive HTTP-200 + Error, route theo `body.http_status`). | §5 quirk |

> 📌 **Pattern (forward-reserve):** Khi bồi action kế (`start_work`/`resolve`/`close`...): (a) đặt `operationId` theo §8.1, (b) `requestBody` INLINE schema riêng (`name` + tham số action), (c) 200 = oneOf `[IncidentActionEnvelope, Error]` (tái dùng envelope nếu data = `{name,status}`; nếu khác → schema `*ActionResponse` mới), (d) 403 = SINGLE-SHAPE `Forbidden`, (e) vào `_MVP_BUSINESS_PATHS` + `_MVP_ACTION_ENVELOPE` của guard ⇒ symmetry 401/403 tự +1. **0 đụng `.py`** (handler `imm12` sẵn) — live HTTP cần USER reload (HARD-STOP).

---

### 8.11 C8-ACTION (repair) — POST-action lifecycle (`startRepair` ĐẦU TIÊN cho Asset Repair: → In Repair)

> **Quyết định kiến trúc:** [`ADR-MOBILE-006.md`](./ADR-MOBILE-006.md) (cùng mẫu §8.10). Đây là **path POST-action ĐẦU TIÊN cho domain repair** — hiện thực mục (c)/(d) của pattern forward-reserve §8.10 sang module IMM-09. Mục đích: màn repair-detail (`getRepairWorkOrder`, §C6-DETAIL) thoát **dead-end read-only** — KTV mở chi tiết phiếu CM → có nút "Bắt đầu sửa".

**Endpoint:** `POST /api/method/assetcore.api.imm09.start_repair` — opId `startRepair`. **POST-ONLY** (`@frappe.whitelist(methods=['POST'])` `api/imm09.py:71-72` — path CHỈ key `post`). Cap: `repair.write` (`rbac.require('repair.write')` `api/imm09.py:73`).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | INLINE `application/json` `$ref StartRepairRequest` (`required:true`, KHÔNG component — action **đơn-field**, KHÔNG oneOf json+form). | mirror `AcknowledgeIncidentRequest` |
| `StartRepairRequest` | closed `{name string REQUIRED}` — **0 optional param**. | signature `start_repair(name)` `api/imm09.py:72` (`name` positional ⇒ required; đúng 1 param) |
| **200** | oneOf `[RepairActionEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `RepairActionEnvelope.data` | `RepairActionResponse` closed `{name string, status string}` — `status` RepairStatus-canonical **9-state**, post-start = `In Repair`. **Schema RIÊNG** (KHÔNG tái dùng `IncidentActionResponse` cross-domain — C3-split: repair-enum 9-state ≠ incident-enum 7-state, field-disjoint). Tên generic (KHÔNG `StartRepair*`) ⇒ forward-reserve cho action repair 2-key thuần. **⚠️ Self-Correction (đã thu hẹp):** reservation ban đầu ghi tái dùng cho `assign_technician`/`submit_diagnosis`/`request_spare_parts` — nhưng CHỈ **`submit_diagnosis`** thực sự reuse (2-key §8.11-bis). `assign_technician` trả 3-key → `AssignTechnicianResponse` RIÊNG (§3.2 file 04 IMM-09); `request_spare_parts` trả 4-key → `RequestSparePartsResponse` RIÊNG (§8.23 + ADR-MOBILE-010). Service THẬT quyết định, KHÔNG forward-reservation. | `svc.start_repair` return `{'name':name,'status':RepairStatus.IN_REPAIR}` `services/imm09.py:847`; `RepairStatus.IN_REPAIR='In Repair'` `services/imm09.py:35`; `asset_repair.json` Select |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403**: in-handler cap-403 (`repair.write` `api/imm09.py:73`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403 (mirror `acknowledgeIncident`). | `api/imm09.py:73` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409/422` (lỗi nghiệp vụ in-handler `IMM09_BAD_STATE`/`NOT_FOUND` arrive HTTP-200 + Error, route theo `body.http_status`). | §5 quirk; `services/imm09.py:835-838` |

> 📌 **Transition nghiệp vụ:** `start_repair` chấp nhận **3 trạng-thái-nguồn** (`Assigned`/`Diagnosing`/`Pending Parts`) → `In Repair` (`services/imm09.py:836,844`). Rời `Pending Parts` ⇒ EXIT hold (chốt `parts_hold_hours` + ALE `parts_hold_resumed`, BR-09-10 `services/imm09.py:842`). **0 đụng `.py`** (handler + `methods=['POST']` + cap-gate `repair.write` sẵn @source) — live HTTP cần USER reload (HARD-STOP).

### 8.11-bis C8-ACTION (repair) — POST-action lifecycle MẮT-XÍCH-GIỮA (`submitDiagnosis`: Assigned/Diagnosing → In Repair | Pending Parts)

> **Quyết định kiến trúc:** [`ADR-MOBILE-006.md`](./ADR-MOBILE-006.md) (cùng mẫu §8.10/§8.11). Đây là **mắt-xích-GIỮA** của vòng-đời Repair Work Order — lấp **dead-end CTA GIỮA** `assignTechnician` (§8.x, Open→Assigned) và `startRepair`/`closeWorkOrder`: KTV mở repair-detail (`getRepairWorkOrder`, §C6-DETAIL) đã `Assigned` → nộp kết quả chẩn đoán (nguyên nhân gốc + nhu cầu vật tư) → **rẽ nhánh** theo `needs_parts`. Chuỗi đầy-đủ: `createRepairWorkOrder → [assignTechnician] → [submitDiagnosis] → startRepair/closeWorkOrder`.

**Endpoint:** `POST /api/method/assetcore.api.imm09.submit_diagnosis` — opId `submitDiagnosis`. **POST-ONLY** (`@frappe.whitelist(methods=['POST'])` `api/imm09.py:63` — path CHỈ key `post`). Cap: `repair.write` (`rbac.require('repair.write')` `api/imm09.py:65`).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | INLINE `application/json` `$ref SubmitDiagnosisRequest` (`required:true`, KHÔNG component — action **đơn-record**, KHÔNG oneOf json+form). | mirror `StartRepairRequest`/`ResolveIncidentRequest` |
| `SubmitDiagnosisRequest` | closed `{name string REQUIRED, diagnosis_notes string REQUIRED, needs_parts integer enum[0,1] opt default 0}` — **2-required** (KHÁC `StartRepairRequest` 1-required: `diagnosis_notes` cũng no-default). `needs_parts` = **INTEGER enum[0,1]** (KHÔNG boolean: handler ép `int(needs_parts)` `api/imm09.py:68`; INT-vs-BOOL discipline Open#4 cho REQUEST body — chống strict-codegen Dart/Kotlin deser crash). | signature `submit_diagnosis(name, diagnosis_notes, needs_parts=0)` `api/imm09.py:64` (`name`+`diagnosis_notes` positional ⇒ required; `needs_parts` default ⇒ optional) |
| **200** | oneOf `[RepairActionEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `RepairActionEnvelope.data` | **REUSE `RepairActionResponse`** closed `{name string, status string}` — `status` RepairStatus-canonical **9-state**, post-diagnosis = `Pending Parts` (nếu `needs_parts=1`) hoặc `In Repair`. **KHÔNG sinh response-schema mới** (service trả EXACT `{name,status}` — mirror `startRepair`, cùng domain repair; tên schema generic đã forward-reserve cho `submit_diagnosis` ở §8.11). | `svc.submit_diagnosis` return `{'name':name,'status':doc.status}` `services/imm09.py:950`; branch `services/imm09.py:938`; `asset_repair.json` Select |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403**: in-handler cap-403 (`repair.write` `api/imm09.py:65`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403 (mirror `startRepair`/`assignTechnician`). | `api/imm09.py:65` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409/422` (lỗi nghiệp vụ in-handler arrive HTTP-200 + Error). **Error-on-HTTP-200**: `IMM09_BAD_STATE` (status ∉ Assigned/Diagnosing → code `CONFLICT` http_status `409`) / `IMM09_NOT_FOUND` (code `NOT_FOUND` http_status `404`) — route theo `body.http_status` ∈ bounded enum {400,401,403,404,409,413,422,429,500} (R11). | §5 quirk; `services/imm09.py:933,935` + `utils/messages.py:634-646` + `utils/notify.py:37-46` (`_HTTP_TO_BUCKET`) |

> 📌 **Transition nghiệp vụ + Self-Correction (SSoT = source, KHÔNG acceptance prose):** `submit_diagnosis` chấp nhận **2 trạng-thái-nguồn** (`Assigned`/`Diagnosing`) → `In Repair` | `Pending Parts` (`services/imm09.py:934,938`). Branch-logic: `needs_parts=1` ⇒ `Pending Parts` + `enter_parts_hold` stamp `parts_hold_started` + ALE (SLA tạm dừng, BR-09-10 `services/imm09.py:941-942`); else ⇒ `In Repair`. Sinh ALE `diagnosis_submitted` (`services/imm09.py:945`). **⚠️ Self-Correction**: acceptance ban đầu ghi `IMM09_BAD_STATE → http_status 422`; **source THẬT = 409/`CONFLICT`** (`utils/messages.py:641-646` http_status=409 → `_HTTP_TO_BUCKET[409]=CONFLICT`), `IMM09_NOT_FOUND` = 404/`NOT_FOUND`. Contract dùng **source** (cả 409/404 ∈ bounded `Error.http_status` enum + `CONFLICT`/`NOT_FOUND` ∈ `Error.code` enum ⇒ Error đóng sẵn biểu-diễn-được, KHÔNG mở schema). **0 đụng `.py`** (handler + `methods=['POST']` + cap-gate `repair.write` + return-shape `{name,status}` sẵn @source) — live HTTP cần USER reload (HARD-STOP).

### 8.12 C8-ACTION — POST-action lifecycle THỨ HAI cho Incident (`startWork`: Acknowledged→In Progress)

> **Quyết định kiến trúc:** [`ADR-MOBILE-006.md`](./ADR-MOBILE-006.md) (cùng mẫu §8.10). Đây là **action lifecycle THỨ HAI cho Incident** — hiện thực mục (a)/(c)/(d) của pattern forward-reserve §8.10 (case `start_work`). NỐI TIẾP `acknowledgeIncident` (§8.10, cùng domain IMM-12) để màn incident-detail (`getIncident`, §C6-DETAIL) **tiến tiếp flow xử lý** sau khi tiếp nhận — KTV mở chi tiết sự cố đã Acknowledged → có nút "Bắt đầu xử lý".

**Endpoint:** `POST /api/method/assetcore.api.imm12.start_work` — opId `startWork`. **POST-ONLY** (`@frappe.whitelist(methods=['POST'])` `api/imm12.py:245` — path CHỈ key `post`). Cap: `corrective.investigate` (`_can_investigate = rbac.can` `api/imm12.py:252` — **CÙNG cap `acknowledgeIncident`**).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | INLINE `application/json` `$ref StartWorkRequest` (`required:true`, KHÔNG component — action **đơn-record**, KHÔNG oneOf json+form). | mirror `AcknowledgeIncidentRequest` |
| `StartWorkRequest` | closed `{name string REQUIRED, notes string opt default''}` — **KHÔNG có `assigned_to`** (KHÁC `AcknowledgeIncidentRequest`: `start_work` auto-gán `doc.assigned_to=session.user` nếu trống @server-side). | signature `start_work(name, notes='')` `api/imm12.py:246` (`name` positional ⇒ required; `notes` default ⇒ optional); auto-assign `services/imm12.py:483` |
| **200** | oneOf `[IncidentActionEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `IncidentActionEnvelope.data` | **REUSE `IncidentActionResponse`** closed `{name string, status string}` — `status` Select-canonical 7-state, post-start = `In Progress`. **KHÔNG sinh schema mới** (cùng domain IMM-12 với `acknowledgeIncident`; data đồng-dạng `{name,status}`, `In Progress` ∈ enum 7-state có sẵn). KHÁC `startRepair` (có `RepairActionResponse` riêng vì repair-enum 9-state ≠ incident-enum 7-state). | `svc_start_work` return `{'name':name,'status':doc.status}` `services/imm12.py:491`; `_STATUS_INVESTIGATING='In Progress'` `services/imm12.py:43`; `incident_report.json` Select |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403**: in-handler cap-403 (`corrective.investigate` `api/imm12.py:252`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403 (mirror `acknowledgeIncident`). | `api/imm12.py:252` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409/422` (lỗi nghiệp vụ in-handler invalid-transition `Acknowledged→In Progress` arrive HTTP-200 + Error, route theo `body.http_status`). | §5 quirk; `services/imm12.py:470` `_assert_transition` |

> 📌 **Transition nghiệp vụ:** `start_work` chuyển `Acknowledged → In Progress` (`_STATUS_INVESTIGATING` `services/imm12.py:43,482`) — KTV bắt đầu thực sự can thiệp thiết bị (tách khỏi triage ở `acknowledge`). Auto-gán `doc.assigned_to=session.user` nếu trống (`services/imm12.py:483`, server-side ⇒ KHÔNG nhận `assigned_to` từ client); `notes` append `[Start]` vào `immediate_action` (`services/imm12.py:486`). **0 đụng `.py`** (handler + `methods=['POST']` + cap-gate `corrective.investigate` sẵn @source) — live HTTP cần USER reload (HARD-STOP).

---

### 8.13 C8-ACTION — POST-action lifecycle THỨ BA cho Incident (`resolveIncident`: In Progress→Resolved)

> **Quyết định kiến trúc:** [`ADR-MOBILE-006.md`](./ADR-MOBILE-006.md) (cùng mẫu §8.10). Đây là **action lifecycle THỨ BA cho Incident** — hiện thực mục (a)/(c)/(d) của pattern forward-reserve §8.10 (case `resolve`). NỐI TIẾP `acknowledgeIncident` (§8.10) + `startWork` (§8.12, cùng domain IMM-12) để màn incident-detail (`getIncident`, §C6-DETAIL) **đóng vòng xử lý** — KTV mở chi tiết sự cố đang `In Progress` → có nút "Hoàn tất xử lý" (ghi nhận `resolution_notes` + `root_cause` tuỳ chọn).
>
> **⚠️ ADR — KHÔNG reuse `IncidentActionResponse`:** Đây là **lần ĐẦU** trong domain IMM-12 mà action-success `data` **KHÔNG còn đồng-dạng `{name,status}`**. `resolve_incident` (`services/imm12.py:530`) trả thêm field thứ ba `rca_created` (RCA auto-create cho High/Critical, `null` nếu không tạo). Pattern §8.10 mục (c) đã forward-reserve case này: *"nếu khác → schema `*ActionResponse` mới"*. ⇒ Sinh **`ResolveIncidentResponse` closed `{name,status,rca_created}`** + envelope riêng **`ResolveIncidentEnvelope`** (KHÔNG nhồi field vào `IncidentActionResponse` 2-key — giữ envelope `acknowledge`/`startWork` BẤT BIẾN closed 2-key). **Consequence**: codegen mobile sinh type `ResolveIncidentResponse` riêng, client đọc `rca_created` để hiển thị "Đã tạo RCA: <name>" cho ca High/Critical. **Alternative bác**: (1) thêm `rca_created` optional vào `IncidentActionResponse` → phá `additionalProperties:false` 2-key của acknowledge/startWork (drift); (2) bỏ `rca_created` khỏi contract → mất signal nghiệp vụ NĐ98 §truy-vết RCA. Cả 2 bị loại.

**Endpoint:** `POST /api/method/assetcore.api.imm12.resolve_incident` — opId `resolveIncident`. **POST-ONLY** (`@frappe.whitelist(methods=['POST'])` `api/imm12.py:257` — path CHỈ key `post`). Cap: `corrective.investigate` (`_can_investigate = rbac.can` `api/imm12.py:264-265` — **CÙNG cap `acknowledgeIncident`/`startWork`**).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | INLINE `application/json` `$ref ResolveIncidentRequest` (`required:true`, KHÔNG component — action **đơn-record**, KHÔNG oneOf json+form). | mirror `StartWorkRequest` |
| `ResolveIncidentRequest` | closed `{name string REQUIRED, resolution_notes string REQUIRED, root_cause string opt default''}` — `additionalProperties:false`. **2 field bắt buộc** (KHÁC `StartWorkRequest` 1-required): `resolution_notes` cũng positional-no-default ⇒ required. | signature `resolve_incident(name, resolution_notes, root_cause='')` `api/imm12.py:258` (`name`+`resolution_notes` positional ⇒ required; `root_cause` default'' ⇒ optional); `resolution_notes.strip()` bắt buộc `services/imm12.py:498` |
| **200** | oneOf `[ResolveIncidentEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed (`additionalProperties:false`) + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `ResolveIncidentEnvelope.data` | **`ResolveIncidentResponse`** closed `{name string, status string, rca_created (string\|null nullable)}` — **schema RIÊNG, KHÔNG reuse `IncidentActionResponse` {name,status}** (xem ADR trên: service trả thêm `rca_created`). `status` Select-canonical 7-state, post-resolve = `Resolved`. | `svc_resolve` return `{'name':name,'status':doc.status,'rca_created':rca_name}` `services/imm12.py:530`; `_STATUS_RESOLVED='Resolved'` `services/imm12.py:44`; `rca_name: str\|None=None` `services/imm12.py:519`; `incident_report.json` Select |
| `rca_created` | `type:string, nullable:true` (OAS 3.0.3) — RCA name khi `_needs_rca(severity)` (High/Critical) auto-create thành công (`_auto_create_rca` `services/imm12.py:1083→1103 return rca.name`); `null` khi severity Low/Medium HOẶC RCA-create raise (try/except nuốt → giữ `None` `services/imm12.py:520-524`). | `services/imm12.py:519-530`; `_HIGH_SEVERITY` `services/imm12.py:164`; `_needs_rca` `services/imm12.py:278` |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403**: in-handler cap-403 (`corrective.investigate` `api/imm12.py:264-265`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403 (mirror `acknowledgeIncident`/`startWork`). | `api/imm12.py:264-265` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409/422` (lỗi nghiệp vụ in-handler invalid-transition `In Progress→Resolved` / `resolution_notes` rỗng `IMM12_RESOLUTION_NOTES_REQUIRED` arrive HTTP-200 + Error, route theo `body.http_status`). | §5 quirk; `services/imm12.py:497-499` `_assert_transition` + notes-required |

> 📌 **Transition nghiệp vụ:** `resolve_incident` chuyển `In Progress → Resolved` (`_STATUS_RESOLVED` `services/imm12.py:44,504`); ghi `resolved_by=session.user` + `resolved_at=now()` (server-side). **BR-12-08 SLA**: nếu `resolved_at > resolution_due_at` → set `resolution_breached=1` (`services/imm12.py:509`). **Auto-RCA (High/Critical)**: `_needs_rca(severity)` ∧ chưa có `rca_record` → `_auto_create_rca` (KHÔNG block — try/except log); nếu không tạo RCA mà vẫn High/Critical → fallback `_auto_create_capa`. `rca_created` = name RCA mới (hoặc `null`). `resolution_notes` REQUIRED (`.strip()` rỗng → `IMM12_RESOLUTION_NOTES_REQUIRED` Error@200); `root_cause` optional → `root_cause_summary` nếu có. **0 đụng `.py`** (handler + `methods=['POST']` `api/imm12.py:257` + cap-gate `corrective.investigate` + return-shape `{name,status,rca_created}` sẵn @source) — live HTTP cần USER reload (HARD-STOP).

---

### 8.14 C8-ACTION-PM — POST-action lifecycle ĐẦU TIÊN cho PM Work Order (`submitPmResult`: → Completed, sinh `pm_completed`)

> **Quyết định kiến trúc:** [`ADR-MOBILE-007.md`](./ADR-MOBILE-007.md) (kế thừa mẫu §8.10 cho domain PM). Đây là **path POST-action ĐẦU TIÊN cho domain PM (IMM-08)** — hiện thực mục (a)/(c)/(d) của pattern forward-reserve §8.10 sang module IMM-08. Mục đích: **ĐÓNG dead-end flow-5** — KTV mở chi tiết PM Work Order (`getPmWorkOrder`, §C6-DETAIL) nhưng KHÔNG có endpoint hoàn thành PM → có nút "Nộp kết quả PM".
>
> **⚠️ ADR — schema RIÊNG, KHÔNG reuse `Repair`/`IncidentActionResponse`:** `submit_pm_result` (`services/imm08.py:705-711`) trả **5-key** `{name, new_status, is_late, next_pm_date, cm_wo_created}` — KHÁC mọi action trước (2-key `{name,status}` hoặc 3-key resolve). Pattern §8.10 mục (c) forward-reserve case này. ⇒ Sinh **`PmSubmitResultResponse` closed 5-key** + envelope riêng **`PmSubmitResultEnvelope`**. **2 dị-biệt PM-riêng**: (1) field tên `new_status` (KHÔNG `status` như Repair/Incident — domain PM dùng tên riêng); (2) **request mang child-array** `checklist_results[]` (nested `PmChecklistResultInput`) thay vì single `name` — action ĐẦU TIÊN có nested body. **Consequence**: codegen mobile sinh `PmSubmitResultResponse` + `PmChecklistResultInput` riêng; client gửi mảng kết quả checklist, đọc `cm_wo_created` (Corrective WO auto-spawn khi PM Fail) + `is_late` (cảnh báo trễ). **Alternative bác**: (1) ép `{name,status}` chung Repair/Incident → mất 3 field PM-riêng + sai tên `status`/`new_status`; (2) bỏ `checklist_results` → KTV không gửi được kết quả từng dòng. Cả 2 bị loại.
>
> **⚠️ ADR — DIVERGENCE method-verb (contract POST ↔ BE bare `@whitelist`):** handler `submit_pm_result` `api/imm08.py:54` là **bare `@frappe.whitelist()`** (KHÔNG `methods=['POST']`) ⇒ runtime BE **nhận cả GET**. Contract **chủ đích khai POST** vì đây là write-action (mutate `docstatus`/`status`, sinh lifecycle event — **không idempotent**, KHÔNG hợp GET-semantics). ⇒ **Lệch contract↔source**. **Fix** = thêm `methods=['POST']` `api/imm08.py:54` (mirror `imm09.start_repair:71` / `imm12.start_work:245`) — đẩy **BACKLOG HARD-STOP** (fix kèm reload gunicorn, KHÔNG sửa `.py` round này). **Guard discipline**: TC-a assert path POST **tồn-tại** + opId (KHÔNG assert POST-ONLY-vì-source — anti-false-green: claim không vượt source); TC-i live-signature parity assert chữ-ký THẬT (độc lập `methods`).

**Endpoint:** `POST /api/method/assetcore.api.imm08.submit_pm_result` — opId `submitPmResult`. **POST khai trong contract** (write-action); **BE hiện bare `@frappe.whitelist()` `api/imm08.py:54` — DIVERGENCE, xem ADR trên**. Cap: `pm.submit` (`rbac.require('pm.submit')` `api/imm08.py:58`).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | INLINE `application/json` `$ref SubmitPmResultRequest` (`required:true`, KHÔNG component). `checklist_results` = **nested array** `<PmChecklistResultInput>` (action ĐẦU TIÊN có child-array; gửi JSON-array, BE `parse_json` string). | `api/imm08.py:55,60` |
| `SubmitPmResultRequest` | closed `{name string REQUIRED; checklist_results array<PmChecklistResultInput> default []; overall_result string default 'Pass'; technician_notes string default ''; pm_sticker_attached integer enum[0,1] default 0; duration_minutes integer default 0}` — `additionalProperties:false`. **1 field bắt buộc** (`name` positional). | signature `submit_pm_result(name, checklist_results='[]', overall_result='Pass', technician_notes='', pm_sticker_attached=0, duration_minutes=0)` `api/imm08.py:55` |
| `PmChecklistResultInput` | closed `{idx integer REQUIRED, result string, measured_value string nullable, notes string default ''}` — `additionalProperties:false`. `idx` = khoá `result_map` match row PM WO; `measured_value` nullable (định-tính không số đo). | `result_map = {r["idx"]: r ...}` `services/imm08.py:659`; `row.result=r.get("result")` `:662`; `row.measured_value=r.get("measured_value")` `:663`; `row.notes=r.get("notes","")` `:664` |
| **200** | oneOf `[PmSubmitResultEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed (`additionalProperties:false`) + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `PmSubmitResultEnvelope.data` | **`PmSubmitResultResponse`** closed `{name string, new_status string, is_late boolean, next_pm_date (string format date), cm_wo_created (string\|null nullable)}` — **schema RIÊNG, KHÔNG reuse `Repair`/`IncidentActionResponse`** (xem ADR trên: 5-key + `new_status`≠`status`). `new_status` PMStatus-canonical 7-state, post-submit = `Completed`. | `svc.submit_result` return `{name,new_status,is_late,next_pm_date,cm_wo_created}` `services/imm08.py:705-711`; `wo.status=PMStatus.COMPLETED` `services/imm08.py:671`; `PMStatus` `services/imm08.py:43-50`; `pm_work_order.json` Select |
| `is_late` | `type:boolean` — **GENUINE boolean** (`bool(wo.is_late)` `services/imm08.py:707`). **KHÁC** `pm_sticker_attached` (request `integer enum[0,1]` — Check `int()`-coerce `api/imm08.py:64`). Client cảnh báo "PM trễ hạn". | `services/imm08.py:707` |
| `cm_wo_created` | `type:string, nullable:true` (OAS 3.0.3) — name Corrective WO **auto-spawn khi PM Fail** (`find_one source_pm_wo+wo_type=Corrective` `services/imm08.py:703-704`); `null` khi PM Pass / không có CM WO. Client hiển thị "Đã tạo phiếu sửa chữa: <name>" nếu non-null. | `services/imm08.py:703-704,710` |
| `next_pm_date` | `type:string, format:date` — `compute_next_pm_date(wo.completion_date, sched_interval)` `services/imm08.py:702`, return `str(next_pm_date)` `:709`. == `AC Asset.next_pm_date` == `PM Schedule.next_due_date` (1 SoT, BR-08-03). | `services/imm08.py:702,709` |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403**: in-handler cap-403 (`pm.submit` `api/imm08.py:58`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403 (mirror các action trước). | `api/imm08.py:58` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409/422` (lỗi nghiệp vụ in-handler: WO∄ `IMM08_WO_NOT_FOUND` `services/imm08.py:658` / already-submitted `IMM08_ALREADY_SUBMITTED` `:660` / completion-gate `VALIDATION` BR-08-08/09/10 `:675` arrive HTTP-200 + Error, route theo `body.http_status`). | §5 quirk; `services/imm08.py:658,660,675` |

> 📌 **Transition nghiệp vụ:** `submit_pm_result` chuyển PM WO `Assigned/In Progress → Completed` (`wo.status=PMStatus.COMPLETED` `services/imm08.py:671`) + `wo.submit()` (`docstatus 0→1` `:679`) → sinh **lifecycle event `pm_completed`** (`handle_work_order_submit`) + thiết bị `→ Active` (`_transition_asset` `:686`). Ghi `overall_result`/`technician_notes`/`pm_sticker_attached`/`duration_minutes`/`completion_date=nowdate()`. **BR-08-03 next-PM**: `next_pm_date` anchor = `wo.completion_date` (1 SoT với PM Schedule/Asset). **Corrective auto-spawn**: nếu PM Fail → Corrective WO link `source_pm_wo` → `cm_wo_created` = name. `name` REQUIRED; checklist gửi từng dòng theo `idx`. **0 đụng `.py`** round này (handler + cap-gate `pm.submit` + return-shape 5-key sẵn @source); **⚠️ BE bare `@whitelist` thiếu `methods=['POST']` = BACKLOG HARD-STOP** (fix kèm reload — KHÔNG sửa round này). Live HTTP cần USER reload (HARD-STOP).

---

### 8.15 C8-ACTION — POST-action lifecycle COMPLETION/TERMINAL cho Calibration Record (`submitCalibration`: docstatus 0→1, → Passed/Failed/Conditionally Passed)

> **Quyết định kiến trúc (ADR submitCalibration):** kế thừa mẫu §8.10 (POST-action route-by-VALUE) cho domain Calibration (IMM-11). Đây là **path POST-action COMPLETION cho domain Calibration** — thành viên **THỨ BA** họ completion-action (sau `submitPmResult` §8.14 + `closeWorkOrder`), mắt xích **CUỐI** chuỗi `createCalibration→complete`. Mục đích: **ĐÓNG dead-end tab Calibration MVP-flow-5** — KTV mở chi tiết Calibration Record (`getCalibration`, §C6-DETAIL) nhưng KHÔNG có endpoint hoàn thành hiệu chuẩn → có nút "Hoàn thành hiệu chuẩn".
>
> **⚠️ ADR — schema RIÊNG, KHÔNG reuse `Pm`/`Repair`/`IncidentActionResponse`:** `submit_calibration` (`services/imm11.py:1054-1059`) trả **4-key** `{name, status, overall_result, next_calibration_date}` — `overall_result` + `next_calibration_date` là field **calibration-riêng** (KHÔNG có ở Repair/Incident/PM action-response). ⇒ Sinh **`SubmitCalibrationResponse` closed 4-key** + envelope riêng **`SubmitCalibrationEnvelope`** (C3-split cross-domain). **Alternative bác**: ép `{name,status}` chung Repair/Incident → mất `overall_result` (kết quả verdict) + `next_calibration_date` (lịch tái hiệu chuẩn). Loại.
>
> **⚠️ ADR — DIVERGENCE method-verb (contract POST ↔ BE bare `@whitelist`):** handler `submit_calibration` `api/imm11.py:114` là **bare `@frappe.whitelist()`** (KHÔNG `methods=['POST']`) ⇒ runtime BE **nhận cả GET**. Contract **chủ đích khai POST** vì đây là write-action (mutate `docstatus 0→1` — **không idempotent**, KHÔNG hợp GET-semantics). ⇒ **Lệch contract↔source**. **Fix** = thêm `methods=['POST']` `api/imm11.py:114` (mirror `imm11.send_to_lab:159` / `cancel_calibration:186` — đã POST-only) — đẩy **BACKLOG HARD-STOP** (fix kèm reload gunicorn, KHÔNG sửa `.py` round này). Track: `_PARITY_VERB_ALLOWLIST` (3rd entry — cùng `create_calibration` + `submit_pm_result`; `test_mob_oas_25c` #3 + `25f` cardinality 2→3). **Guard discipline**: TC-a assert path POST **tồn-tại** + opId (KHÔNG assert POST-ONLY-vì-source — anti-false-green); TC-i live-signature parity assert chữ-ký THẬT (độc lập `methods`).
>
> **[SELF-CORRECTION R34 — 2026-06-27] DIVERGENCE ĐÃ CLOSED (đoạn trên STALE):** R33 VERB-PARITY CLOSURE đã **flip** `submit_calibration` `api/imm11.py:114` → `@frappe.whitelist(methods=['POST'])` (cùng `create_calibration` `:89` + `submit_pm_result` `imm08.py:54`) ⇒ `_PARITY_VERB_ALLOWLIST` nay = **`set()` rỗng** (KHÔNG còn "3rd entry"/"cardinality 2→3"). `submitCalibration` nay = **CLEAN POST**, KHÔNG verb-divergence, KHÔNG vào allowlist. Đoạn "bare `@whitelist`"/"BACKLOG HARD-STOP"/"3rd entry" giữ làm lịch-sử quyết định — KHÔNG còn phản ánh source. Verb-parity gap CUỐI (`add_measurement`) đóng ở **§8.24 / ADR-MOBILE-011**.

**Endpoint:** `POST /api/method/assetcore.api.imm11.submit_calibration` — opId `submitCalibration`. **POST khai trong contract** (write-action); **BE hiện bare `@frappe.whitelist()` `api/imm11.py:114` — DIVERGENCE, xem ADR trên**. Cap: `calibration.submit` (`rbac.require('calibration.submit')` `api/imm11.py:116`).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | INLINE `application/json` `$ref SubmitCalibrationRequest` (`required:true`, KHÔNG component, KHÔNG `x-www-form` — đơn-field action mirror `StartRepairRequest`). | `api/imm11.py:115` |
| `SubmitCalibrationRequest` | closed `{name string REQUIRED}` — `additionalProperties:false`. **1 field bắt buộc, 0 optional** (`name` positional). | signature `submit_calibration(name)` `api/imm11.py:115` |
| **200** | oneOf `[SubmitCalibrationEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed (`additionalProperties:false`) + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `SubmitCalibrationEnvelope.data` | **`SubmitCalibrationResponse`** closed `{name string, status string, overall_result string, next_calibration_date string nullable}` — **schema RIÊNG, KHÔNG reuse `Pm`/`Repair`/`IncidentActionResponse`** (xem ADR trên: C3-split cross-domain). | `svc.submit_calibration` return `{name,status,overall_result,next_calibration_date}` `services/imm11.py:1054-1059` |
| `status` | `type:string, enum` 8-value `[Scheduled, Sent to Lab, In Progress, Certificate Received, Passed, Failed, Conditionally Passed, Cancelled]` — khớp Select `imm_asset_calibration.json`. Post-submit thường `Passed`/`Failed`/`Conditionally Passed`. | `doc.status` `services/imm11.py:1056`; `imm_asset_calibration.json` Select |
| `overall_result` | `type:string, enum` 4-value `['', Passed, Failed, Conditionally Passed]` — khớp Select `imm_asset_calibration.json` (gồm `''` rỗng khi chưa chấm/cancel). | `doc.overall_result` `services/imm11.py:1057`; `imm_asset_calibration.json` Select |
| `next_calibration_date` | `type:string, nullable:true` (OAS 3.0.3) — `str(doc.next_calibration_date or '')`: rỗng khi chưa có lịch tái. Client hiển thị ngày hiệu chuẩn kế nếu non-empty. | `services/imm11.py:1058` |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403**: in-handler cap-403 (`calibration.submit` `api/imm11.py:116`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403 (mirror `startRepair`/`closeWorkOrder`). | `api/imm11.py:116` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409` (lỗi nghiệp vụ in-handler: record∄ `IMM11_CAL_NOT_FOUND` `services/imm11.py:1050` / already-submitted `IMM11_ALREADY_SUBMITTED` docstatus==1 `:1052` arrive HTTP-200 + Error, route theo `body.http_status`). | §5 quirk; `services/imm11.py:1050,1052` |

> 📌 **Transition nghiệp vụ:** `submit_calibration` nâng Calibration Record `docstatus 0→1` (`CalibrationRepo.submit` `services/imm11.py:1053`) → chốt `overall_result` (verdict Passed/Failed/Conditionally Passed) + `next_calibration_date` (lịch tái hiệu chuẩn). `name` REQUIRED (0 optional). **0 đụng `.py`** round này (handler + cap-gate `calibration.submit` + return-shape 4-key sẵn @source); **⚠️ BE bare `@whitelist` thiếu `methods=['POST']` = BACKLOG HARD-STOP** (fix kèm reload, mirror `send_to_lab`/`cancel_calibration` đã POST-only — KHÔNG sửa round này). Live HTTP cần USER reload (HARD-STOP).

---

### 8.16 C8-ACTION — POST-action lifecycle TERMINAL cho Incident (`closeIncident`: Resolved→Closed)

> **Quyết định kiến trúc:** [`ADR-MOBILE-006.md`](./ADR-MOBILE-006.md) (cùng mẫu §8.10). Đây là **action lifecycle TERMINAL cho Incident** — hiện thực mục (a)/(c)/(d) của pattern forward-reserve §8.10 (case `close`), **đóng mắt xích CUỐI** chuỗi `report→ack→start→resolve→close` (cùng domain IMM-12). NỐI TIẾP `acknowledgeIncident` (§8.10) + `startWork` (§8.12) + `resolveIncident` (§8.13) để màn incident-detail (`getIncident`, §C6-DETAIL) **đóng hoàn toàn vòng-đời** — Workshop Lead / QA Officer mở chi tiết sự cố đang `Resolved` → có nút "Đóng sự cố" (ghi nhận `verification_notes` tuỳ chọn).
>
> **⚠️ ADR — KHÔNG reuse `IncidentActionResponse` NÊN KHÔNG reuse `ResolveIncidentResponse` (C3-split field-disjoint):** `close_incident` (`services/imm12.py:569`) trả **3-key** `{name, status, closed_date}`. KHÔNG đồng-dạng `IncidentActionResponse` {name,status} (2-key — service trả thêm field thứ ba). Cũng **KHÔNG** reuse `ResolveIncidentResponse` {name,status,**rca_created**} dù cùng 3-key: field thứ ba **`closed_date` ≠ `rca_created`** (semantics khác — ngày đóng vs RCA-name; **field-disjoint** ⇒ C3-split). Pattern §8.10 mục (c) đã forward-reserve: *"nếu khác → schema `*ActionResponse` mới"*. ⇒ Sinh **`CloseIncidentResponse` closed `{name,status,closed_date}`** + envelope riêng **`CloseIncidentEnvelope`** (giữ envelope `acknowledge`/`startWork` BẤT BIẾN 2-key + `resolve` BẤT BIẾN `{...,rca_created}`). **Consequence**: codegen mobile sinh type `CloseIncidentResponse` riêng, client đọc `closed_date` hiển thị "Đã đóng ngày <closed_date>". **Alternative bác**: (1) nhồi `closed_date` vào `IncidentActionResponse` → phá `additionalProperties:false` 2-key acknowledge/startWork (drift); (2) reuse `ResolveIncidentResponse` (đổi tên `rca_created`→`closed_date`) → 1 schema 2 nghĩa, codegen sai field cho 1 trong 2 action. Cả 2 bị loại.
>
> **✅ ADR — clean POST, KHÔNG verb-divergence (KHÁC §8.14/§8.15):** handler `close_incident` `api/imm12.py:270` đã có decorator **`@frappe.whitelist(methods=['POST'])`** SẴN — write-action (mutate `status`, sinh transition Resolved→Closed) khai POST đúng-semantics. ⇒ **KHÔNG lệch contract↔source** (KHÁC `submitPmResult` §8.14 / `submitCalibration` §8.15 bare-`@whitelist` cần fix `methods=['POST']` backlog). **KHÔNG** vào `_PARITY_VERB_ALLOWLIST`. **Guard discipline**: TC-a assert path **POST-ONLY** (chỉ key `post` — khớp source `methods=['POST']`, KHÔNG anti-false-green vì source THẬT đã POST-only); TC-i live-signature parity assert chữ-ký THẬT `{name,verification_notes}`.

**Endpoint:** `POST /api/method/assetcore.api.imm12.close_incident` — opId `closeIncident`. **POST-ONLY** (`@frappe.whitelist(methods=['POST'])` `api/imm12.py:270` — path CHỈ key `post`, clean POST). Cap: `incident.close` (`_can_close` `api/imm12.py:277` — **KHÁC cap `acknowledge`/`startWork`/`resolve` `corrective.investigate`**: close cần **Workshop Lead HOẶC QA Officer**).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | INLINE `application/json` `$ref CloseIncidentRequest` (`required:true`, KHÔNG component — action **đơn-record**, KHÔNG oneOf json+form). | mirror `StartWorkRequest` |
| `CloseIncidentRequest` | closed `{name string REQUIRED, verification_notes string opt default''}` — `additionalProperties:false`. **1 field bắt buộc** (`name` positional; `verification_notes` default'' ⇒ optional). | signature `close_incident(name, verification_notes='')` `api/imm12.py:271` (`name` positional ⇒ required; `verification_notes` default'' ⇒ optional → append `"[Closed] <notes>"` vào `resolution_notes` `services/imm12.py:556-557`) |
| **200** | oneOf `[CloseIncidentEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed (`additionalProperties:false`) + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `CloseIncidentEnvelope.data` | **`CloseIncidentResponse`** closed `{name string, status string, closed_date (string format date)}` — **schema RIÊNG, KHÔNG reuse `IncidentActionResponse` {name,status} NÊN KHÔNG reuse `ResolveIncidentResponse` {name,status,rca_created}** (xem ADR trên: `closed_date` ≠ `rca_created` — C3-split field-disjoint). `status` Select-canonical 7-state, post-close = `Closed`. | `svc_close` return `{'name':name,'status':doc.status,'closed_date':doc.closed_date}` `services/imm12.py:569`; `_STATUS_CLOSED='Closed'` `services/imm12.py:45`; `incident_report.json` Select |
| `closed_date` | `type:string, format:date` — **NON-nullable** (`doc.closed_date=today()` set **UNCONDITIONAL** khi close `services/imm12.py:555` ⇒ LUÔN có giá-trị). **KHÁC** `rca_created`/`next_calibration_date` (nullable của resolve/cal — close luôn ghi ngày). | `services/imm12.py:555,569`; `today()` `frappe.utils` |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403**: in-handler cap-403 (`incident.close` `_can_close` `api/imm12.py:277`, message `'Không có quyền đóng Incident (cần Workshop Lead hoặc QA Officer)'`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403 (mirror `acknowledgeIncident`/`startWork`/`resolveIncident`). | `api/imm12.py:277-278` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409/422` (lỗi nghiệp vụ in-handler invalid-transition `Resolved→Closed` / **BR-12-02 RCA chưa Completed** `IMM12_CLOSE_RCA_INCOMPLETE`/`IMM12_CLOSE_RCA_REQUIRED` arrive HTTP-200 + Error, route theo `body.http_status`). | §5 quirk; `services/imm12.py:541-550` `_assert_transition` + RCA-gate |

> 📌 **Transition nghiệp vụ:** `close_incident` chuyển `Resolved → Closed` (`_STATUS_CLOSED` `services/imm12.py:45,553`); ghi `closed_by=session.user` + `closed_date=today()` (server-side, UNCONDITIONAL). **BR-12-02 RCA-gate**: Major/Critical (`_needs_rca(severity)` ∧ `rca_required`) → phải có RCA `Completed` trước Close — RCA chưa Completed → `IMM12_CLOSE_RCA_INCOMPLETE`; thiếu RCA → `IMM12_CLOSE_RCA_REQUIRED` (Error@200, `services/imm12.py:541-550`). **Asset-restore**: nếu asset đang `Out of Service` do incident này → khôi phục về `Active` (`_try_transition_asset` `services/imm12.py:562-566`). `verification_notes` optional → append `"[Closed] <notes>"` vào `resolution_notes` nếu có. `name` REQUIRED. **0 đụng `.py`** (handler + `methods=['POST']` `api/imm12.py:270` + cap-gate `incident.close` + return-shape `{name,status,closed_date}` sẵn @source) — **clean POST, KHÔNG verb-divergence, no ADR-fix needed** (KHÁC §8.14/§8.15). Live HTTP cần USER reload (HARD-STOP).

---

### 8.17 C-LISTREAD-NOTIF — in-app notification list (`listNotifications`: tab Notifications, đóng gap đọc-lịch-sử flow-6 push)

> **Quyết định kiến trúc (C-LISTREAD-NOTIF):** flow-6 push (FCM) chỉ giao **1 deep-link/event đơn lẻ** mỗi thông báo; **tab Notifications mobile** (chuông) cần API **liệt-kê ĐẦY ĐỦ** thông báo đã-đọc + chưa-đọc để người dùng đọc-lịch-sử. Đây là path **list-read THỨ 8** (sau `listPmSchedules`/`listCalibrations`/`listAssets`/`listUsers` + 3 list WO/Incident). **KHÁC 19 đề mục mobile-BE trước:** 20 đề mục = push payload (`PushMessageData` §[push]) + device-token register/unregister (§8.9); CHƯA ai bồi **in-app notification LIST** từ `api/layout.py`.

**Endpoint:** `GET /api/method/assetcore.api.layout.list_notifications` — opId `listNotifications`. Bare `@frappe.whitelist()` (nhận GET) `api/layout.py:72` — **đã wire web FE** (AppTopBar notification center). **Cap đọc:** any-authenticated (guest → dispatcher-403 / bearer hết-hạn → in-handler 401 `api/layout.py:78-79`); server **ÉP** `for_user=frappe.session.user` `api/layout.py:82` ⇒ scope tự-thân (KHÔNG cross-user, KHÔNG cần cap nghiệp vụ).

**Param query (§6.1 — 3 DISCRETE, KHÔNG JSON `filters`):** `Page`/`PageSize` (REUSE component) + **`NotifOnlyUnread`** (`only_unread`, integer enum[0,1] **default 0** — `only_unread=1` → `filters["read"]=0`, chỉ chưa đọc; default 0 = liệt-kê ĐẦY ĐỦ). Mirror `listPmSchedules`/`listAssets`/`listUsers` discrete.

**Envelope (§6.2):** `NotificationListEnvelope` closed (`additionalProperties:false`) — rows-key **`data.items[]`** (mirror `IncidentListEnvelope`/`AssetListEnvelope`, handler `_ok({pagination, items})` `api/layout.py:96-99` — **KHÁC** Pm/Repair `data.data[]`). **`pagination` = `$ref Pagination` 5-key WITH `offset`** (handler GỌI `paginate()` `api/layout.py:87` → `{page,page_size,total,total_pages,offset}`) — **KHÁC `UserListEnvelope`** (build inline 4-key no-offset, ADR-MOBILE-005). **KHÔNG strip offset** vì runtime EMIT offset (`utils/pagination.py:30`) → mirror IncidentListEnvelope giữ khớp wire-shape (strip = ADR-MOBILE-005 trap NGƯỢC).

**Element `NotificationListItem`** closed — **ĐÚNG 9 field** `_serialize_notification` `api/layout.py:33-43`: `name` (PK, REQUIRED), `subject`, `content` (= `email_content.strip()`), `document_type`/`document_name`/`from_user` (**nullable** — Notification Log optional Link/sender), `type` (fallback `'Alert'`), `read` (**integer enum[0,1]** — `int(row.get('read'))` `api/layout.py:41`, KHÔNG boolean — Open#1 int-vs-bool né strict-codegen Dart/Kotlin deser crash), `creation` (date-time, order_by desc). **KHÔNG leak** `for_user` (server filter, FE không cần).

**200 = oneOf [`NotificationListEnvelope`, `Error`]** closed-schema route-by-VALUE `body.success` (C7, 0 discriminator); 401 = `Unauthorized401`, 403 = `Forbidden`. **0 đụng `.py`** (handler sẵn + bare whitelist nhận GET + param discrete + đã wire web FE) ⇒ **KHÔNG reload gunicorn / KHÔNG migrate**. Runtime `openapi.generate_spec()` CÓ serve path (parity 25b GREEN; verb get=get → KHÔNG vào `_PARITY_VERB_ALLOWLIST`). **Guard:** `TestMobileListNotificationsContract` (+9 TC a..i — incl. live-sig parity `inspect.signature(layout.list_notifications)=={page,page_size,only_unread}` + `_serialize_notification` live-emit key-set == contract 9-field).

---

### 8.18 FLOW-2 DEVICE-PROFILE — lịch-sử sự-cố của thiết bị (`getAssetIncidentHistory`: màn hồ-sơ sau quét QR)

> 🟦 **Lấp dead-end màn hồ-sơ-thiết-bị (flow-2).** `getAssetScanInfo` (§R4 §8.7 / read-table §6) trả profile + `available_actions` của asset sau khi KTV quét QR — NHƯNG **KHÔNG có endpoint liệt-kê lịch-sử sự-cố** của asset đó. KTV ở màn hồ-sơ cần trả lời "máy này từng hỏng gì?". `getAssetIncidentHistory` đóng dead-end này: 1 GET-read trả danh-sách sự-cố (mới→cũ, ≤`limit`) của 1 asset. **KHÁC `listIncidents`** (§6.2 — "báo hỏng của tôi", paginate, 28 enrich-field): KHÔNG pagination (chỉ `limit` cap) + element CHỈ 9 field grounded `frappe.get_all`.

**Endpoint:** `GET /api/method/assetcore.api.imm12.get_asset_incident_history` — opId `getAssetIncidentHistory`. **GET** (bare `@frappe.whitelist()` nhận GET `api/imm12.py:172`). **Cap đọc:** incident read (qua `handle()` → `svc.get_asset_incident_history` permission-aware; **KHÔNG cap-gate trong handler** — KHÁC `reportIncident` `corrective.create`); thiếu quyền = cap-403 Error-trên-HTTP-200. 401 = handler guard `frappe.session.user=='Guest'→_err 401` `api/imm12.py:175-176` (`Unauthorized401`, SINGLE-SHAPE — mirror `listIncidents`). Read-only — **KHÔNG audit**.

**Query param (KHỚP signature `get_asset_incident_history(asset, limit=10)` `api/imm12.py:173`):**

| Param | in | required | type | default | Ground |
|---|---|---|---|---|---|
| `asset` | query | ✅ true | string | — | Link AC Asset (positional no-default `api/imm12.py:173`) |
| `limit` | query | ❌ | integer | `10` | `limit_page_length=limit` `services/imm12.py:841`; handler ép `int(limit)` `api/imm12.py:177`. **KHÔNG** `page`/`page_size` (svc không paginate) |

**200 = oneOf [`AssetIncidentHistoryEnvelope`, `Error`]** closed-schema route-by-VALUE `body.success` (C7 read-path, 0 discriminator; mirror `getAssetScanInfo` §5c). 2 nhánh `additionalProperties:false` + disjoint required-set (`[success,data]` vs `[success,error,code,http_status]`) ⇒ codegen route ĐÚNG KHÔNG discriminator.

| Slot | Schema | Ground |
|---|---|---|
| `AssetIncidentHistoryEnvelope` | closed `required[success,data]`, `success enum[true]`; `data` = object **closed** `required[asset,items]` — **KHÔNG pagination** (svc trả `{asset,items}` `services/imm12.py:843`, chỉ `limit` cap — KHÁC `IncidentListEnvelope.data.required[pagination,items]`); `data.asset` echo mã thiết bị; `items[]` array `AssetIncidentHistoryItem`, RỖNG `[]` hợp lệ nếu asset chưa từng có sự-cố (**KHÔNG 404**) | `handle()/_ok` wrap `services/imm12.py:843` |
| `AssetIncidentHistoryItem` | closed (`additionalProperties:false`), **EXACT 9 prop** `{name, incident_type, severity, status, reported_at, fault_code, closed_date, linked_capa, rca_record}`, `required[name]` | `frappe.get_all(fields=[…])` `services/imm12.py:838-839` |

**Int-vs-bool trap né sẵn (Open#1):** 9 prop = 3 Select (`incident_type`/`severity`/`status`) + Datetime (`reported_at`) + Date (`closed_date`) + Data (`fault_code`) + 2 Link (`linked_capa`/`rca_record`) ⇒ **0 boolean/Check field** ⇒ 0 prop `integer enum[0,1]`. KHÁC `IncidentListItem` (28-field có `rca_required`/`chronic_failure_flag`/`patient_affected` Check→int). Response slot CHỈ `{200,401,403}` — KHÔNG status-line 404 (asset∄ → items[] RỖNG). 403 SINGLE-SHAPE `Forbidden`.

**0 đụng `.py`** (handler + service LIVE whitelisted, sig nguyên — `git diff api/imm12.py + services/imm12.py` = empty cho asset-history) ⇒ **KHÔNG reload gunicorn / KHÔNG migrate / KHÔNG commit** (pure-yaml + guard test). **Guard:** `TestMobileGetAssetIncidentHistoryContract` (+9 TC a..i — incl. TC-b query-param parity `{asset required, limit default 10}` + TC-d envelope-no-pagination + TC-e item-exact-9 + TC-f no-int-bool-trap + TC-i live-sig parity `inspect.signature(imm12.get_asset_incident_history)=={asset,limit}`, chống drift contract↔source). **SSoT:** `api/imm12.py:172-177` + `services/imm12.py:834-843` + `incident_report.json`.

---

### 8.19 FLOW-1 BOOTSTRAP — session who-am-I (`getUserContext`: persona-aware home + flow-gating sau login)

> 🟩 **Lấp dead-end POST-LOGIN (flow-1).** App home sau login hiện **hardcode "Đã đăng nhập" KHÔNG identity** — session FE chỉ giữ `{email, fullName}` parse từ login-response, KHÔNG có roles/department/persona/profile-completeness. Để render **persona-aware home** + **flow-gating** (ẩn/hiện tính năng theo role; ép hoàn-thiện-profile nếu thiếu khoa-phòng/chức-danh), app cần 1 GET-read "ai-đang-đăng-nhập". Endpoint LIVE whitelisted @`layout.py:188` (`allow_guest=True`) trả ĐỦ identity. **CHƯA vòng nào (1-28) bồi session-bootstrap/who-am-I** — đây là path **FLOW-1** đầu tiên.

**Boundaries (Always / Never):**
- **Always:** gọi `getUserContext` **ngay sau login** (và khi resume app / refresh token thành công) để hydrate persona; route home theo `roles`/`imm_roles`; gate onboarding theo `is_profile_completed`.
- **Never:** dựa vào `{email,fullName}` parse từ login-resp làm identity (thiếu roles/dept → home generic); so-sánh `roles` client-side để **cấp quyền** (RBAC là server-gate; `roles` ở đây chỉ để render UI). **Never** kỳ vọng 403 từ path này — `allow_guest=True` ⇒ Guest nhận **401 in-handler** (Error-on-HTTP-200), KHÔNG dispatcher-403.

**Endpoint:** `GET /api/method/assetcore.api.layout.get_user_context` — opId `getUserContext`. **GET 0-param** (signature `get_user_context()` — 0 positional/optional `api/layout.py:188`); KHÔNG `requestBody`. **`allow_guest=True`** (`api/layout.py:187`) — Guest VÀO handler → in-handler `_err 401` (`api/layout.py:206-207`, body Error-trên-HTTP-200; FE auth-store catch redirect `/login` KHÔNG log 403 console). **KHÔNG cap-gate / KHÔNG vendor-scope / KHÔNG audit** (read-only, identity của chính session).

**200 = oneOf [`UserContextEnvelope`, `Error`]** closed-schema route-by-VALUE `body.success` (C7 read-path, 0 discriminator; mirror `getAssetScanInfo` §5c). 2 nhánh `additionalProperties:false` + disjoint required-set (`[success,data]` vs `[success,error,code,http_status]`) ⇒ codegen route ĐÚNG KHÔNG discriminator.

| Slot | Schema | Ground |
|---|---|---|
| `UserContextEnvelope` | closed `required[success,data]`, `success enum[true]`; `data` = **`$ref UserContextData`** (object, KHÔNG list) | `_ok(payload)` `layout.py:220` |
| `UserContextData` | closed (`additionalProperties:false`), **EXACT 13 prop** (bảng dưới), `required[user]` (LUÔN có khi 200 = `frappe.session.user`; rest nullable theo **graceful-degradation**) | `_ok` payload `layout.py:220-234` |

**`UserContextData` — EXACT 13 prop GROUNDED `_ok` payload `layout.py:220-234`:**

| Prop | Type | Nullable | Ground |
|---|---|---|---|
| `user` | string | ❌ (required) | `frappe.session.user` `layout.py:221` — LUÔN có khi 200 |
| `full_name` | string | ✅ | `User.full_name` (fallback=user) `layout.py:222`/`:145` |
| `user_image` | string | ✅ | `User.user_image` `layout.py:223`/`:146` |
| `phone` | string | ✅ | `User.phone` `layout.py:224`/`:147` |
| `role_profile_name` | string | ✅ | `User.role_profile_name` (persona SSoT) `layout.py:225`/`:148` |
| `roles` | array&lt;string&gt; | — (`[]`) | `frappe.get_roles(user)` `layout.py:226`/`:149` |
| `imm_roles` | array&lt;string&gt; | — (`[]`) | subset `roles` bắt đầu `"IMM "` `layout.py:227` |
| `designation` | string | ✅ | HR `Employee.designation` (optional) `layout.py:228`/`:215` |
| `hr_docname` | string | ✅ | HR `Employee.name` (null nếu chưa link) `layout.py:229`/`:181` |
| `department` | string | ✅ | `User.ac_department` (Link AC Department) `layout.py:230`/`:157` |
| `department_name` | string | ✅ | `AC Department.department_name` (fallback erp_department) `layout.py:231`/`:214` |
| `is_profile_completed` | **integer enum[0,1]** | — | `bool(department and designation)` `layout.py:218`/`:232` — **INT-VS-BOOL TRAP** |
| `has_employee_link` | **integer enum[0,1]** | — | `emp.get("has_employee_link", False)` `layout.py:233` — **INT-VS-BOOL TRAP** |

> ⚠️ **INT-VS-BOOL TRAP (ADR-MOBILE-008 §2, Open#1 sweep):** `is_profile_completed` + `has_employee_link` BE emit **`bool()` Python** (`true`/`false`) NHƯNG contract khai **`integer enum[0,1]`** (KHÔNG `type:boolean`). Lý do: codegen strict-deser (Dart/Kotlin) cần **int-or-bool nhất quán** toàn contract — nhiều Check-field khác (vd `IncidentListItem.rca_required`/`chronic_failure_flag`/`patient_affected` `§6.3`) đã là `integer enum[0,1]` (Frappe Check→int 0/1). Giữ 2 flag này boolean = **bất nhất** trong contract ⇒ client phải xử-lý 2 kiểu cho cùng-nghĩa cờ. Guard `test_mob_oas_userctx_f` chống regress (assert `type:integer` + `enum[0,1]`, KHÔNG `boolean`). Client coerce `0/1` → bool ở app layer.

> 📌 **Graceful-degradation (`layout.py:195-204`):** handler **LUÔN trả 200** nếu đã đăng nhập, dù thiếu AC User Profile / Employee (`db.get_value`, KHÔNG `get_doc` trên DocType có thể không tồn tại). ⇒ chỉ `user` chắc-chắn có; 6 string-field (`user_image`/`phone`/`designation`/`hr_docname`/`department`/`department_name`) = **nullable** (db.get_value trả null nếu nguồn vắng); `roles`/`imm_roles` = `[]` nếu rỗng. Client PHẢI null-guard khi render.

**Response slot CHỈ `{200, 401}`** — **KHÔNG 403**. Vì `allow_guest=True` ⇒ KHÔNG dispatcher cap-403 (Guest KHÔNG bị `is_whitelisted` chặn) + KHÔNG business-403 (read-only identity của chính session). 401 = `Unauthorized401` (`$ref FrappeRawError`, SINGLE-SHAPE uniform 37-path convention — slot 401 dùng component dù body runtime là in-handler Error-on-HTTP-200; mirror `listIncidents`/`getAssetIncidentHistory`, KHÔNG drift). **MIRROR `openid_profile`/`getUserInfo`** (§C4 — bearer-gated whoami, status-set `{200,401}` Frappe-core RAW): cùng shape slot nhưng `getUserContext` là **AssetCore-handler** (KHÔNG Frappe-core oauth) ⇒ exempt 401/403 MVP-business symmetry qua tập **`_ALLOW_GUEST_PATHS`** (ADR-MOBILE-008), KHÔNG nhồi `_AUTH_PATHS`.

> 🔑 **NOT ∈ `_MVP_BUSINESS_PATHS` / `_MVP_READ_ENVELOPE` / C5-registry:** `getUserContext` là **bootstrap/session path** (allow_guest, no vendor-scope, no cap-gate) ⇒ KHÔNG phải "MVP-business path". Đưa nó vào `_MVP_BUSINESS_PATHS` sẽ **ép 403 symmetry** (vỡ — không có 403); đưa vào `_MVP_READ_ENVELOPE` sẽ phá invariant `C5 == _MVP_BUSINESS_PATHS` (23a). Typed-200 oneOf phủ **độc lập** bởi guard riêng `test_mob_oas_userctx_c`. Đây là **ranh-giới scope rõ ràng** — KHÔNG là thiếu-sót coverage.

**0 đụng `.py`** (handler + 3 helper LIVE whitelisted, sig nguyên — `git diff api/layout.py` = empty) ⇒ **KHÔNG reload gunicorn / KHÔNG migrate / KHÔNG commit** (pure-yaml + guard test). **Guard:** `TestMobileGetUserContextContract` (+9 TC a..i — incl. TC-b 0-param + TC-e data-exact-13 + TC-f int-vs-bool-trap + arrays + 6-nullable + TC-g slot-`{200,401}`-no-403 + TC-h allow_guest-exempt-symmetry + TC-i live-sig parity `inspect.signature(layout.get_user_context)=={}`, chống drift contract↔source). **SSoT:** `api/layout.py:187-234` + [`ADR-MOBILE-008.md`](./ADR-MOBILE-008.md) (allow_guest exempt symmetry).

---

### 8.20 C8-ACTION — POST-action lifecycle TERMINAL-THẬT cho Repair Work Order (`confirmInspection`: Pending Inspection→Completed, docstatus 0→1)

> 🟦 **Lấp dead-end CUỐI chuỗi Repair (flow-5 acceptance).** `closeWorkOrder` (§ path block) chỉ đưa Repair WO về **`Pending Inspection` (NON-terminal)** — chờ nghiệm thu cấp khoa; thiết bị CHƯA về `Active`, MTTR/SLA CHƯA chốt cứng, docstatus VẪN 0. `getRepairWorkOrder.allowed_transitions[]` (§C6-DETAIL, mirror Incident R3 / PM R21) ĐÃ surface CTA **`Completed`** trên màn repair-detail khi `status="Pending Inspection"` (`_REPAIR_VALID_TRANSITIONS[Pending Inspection]=[Completed, In Repair, Cancelled]` `services/imm09.py`) — **NHƯNG KHÔNG có endpoint mobile để thực thi** transition đó. `confirmInspection` đóng dead-end CUỐI: QA Officer / Trưởng khoa mở repair-detail đang `Pending Inspection` → bấm "Nghiệm thu hoàn tất" → WO `Pending Inspection → Completed` (`doc.submit()` `services/imm09.py:1108` → `on_submit → complete_repair()` chốt MTTR/SLA + restore Asset có điều kiện BR-09-09). Chuỗi đầy-đủ: `createRepairWorkOrder → [assignTechnician] → [submitDiagnosis] → startRepair → closeWorkOrder → [confirmInspection]`.

> **Quyết định kiến trúc (ADR confirmInspection):** [`ADR-MOBILE-009.md`](./ADR-MOBILE-009.md) (kế thừa mẫu §8.10 POST-action route-by-VALUE; cùng họ completion-action với `submitPmResult` §8.14 / `submitCalibration` §8.15 / `closeIncident` §8.16). Đây là **path POST-action TERMINAL-THẬT cho domain Repair (IMM-09)** — mắt xích CUỐI của vòng-đời Repair Work Order. **Cap-gate `repair.submit`** (QA/trưởng-khoa duyệt) **KHÁC `repair.create`** (KTV tạo phiếu) ⇒ **gate phê-duyệt-chất-lượng RIÊNG** (KTV đóng phiếu sang Pending Inspection bằng `closeWorkOrder`; chỉ vai duyệt mới chốt Completed bằng `confirmInspection` — phân-quyền 2 vai khác nhau, đúng kiểm-soát chất lượng).
>
> **⚠️ ADR — C3-split: KHÔNG reuse `CloseWorkOrderResponse` dù SHAPE TRÙNG 4-key:** `confirm_inspection` (`services/imm09.py:1116-1121`) trả **4-key** `{name, status, mttr_hours, sla_breached}` — **shape TRÙNG ĐÚNG** `CloseWorkOrderResponse` (cùng 4 field, cùng type). NHƯNG **semantics KHÁC**: (1) `confirmInspection.status` = **INVARIANT `Completed`** (single-value enum — terminal-thật `RepairStatus.COMPLETED` `services/imm09.py:1118` LUÔN, KHÔNG rẽ nhánh) vs `CloseWorkOrderResponse.status` = **2-value enum** `[Pending Inspection, Cannot Repair]` (rẽ theo `cannot_repair`); (2) `confirmInspection` LUÔN có `mttr_hours`/`sla_breached` (chốt sau `complete_repair()` `:1108`) trong khi `CloseWorkOrderResponse` để 2 field **nullable** (nhánh `cannot_repair` không tính MTTR). ⇒ Sinh **`ConfirmInspectionResponse` closed 4-key RIÊNG** + envelope riêng **`ConfirmInspectionEnvelope`** — **KHÔNG reuse `CloseWorkOrderResponse`** (1 schema 2 nghĩa `status` ⇒ codegen sinh enum sai cho 1 trong 2 action). **Precedent C3-split cross-action**: y hệt `ResolveIncidentResponse` vs `CloseIncidentResponse` (§8.13/§8.16 — cùng 3-key shape `{name,status,X}` nhưng `rca_created`≠`closed_date` → 2 schema riêng). **Alternative bác**: (1) reuse `CloseWorkOrderResponse` (nới `status` enum thành 3-value gộp `Completed`) → mất tín-hiệu INVARIANT-terminal của confirm + client không biết status nào hợp-lệ cho action nào; (2) nhồi `confirmInspection` vào path `closeWorkOrder` (cờ thêm) → 1 path 2 cap-gate (`repair.create` vs `repair.submit`) ⇒ phá phân-quyền 2 vai. Cả 2 bị loại.
>
> **✅ ADR — clean POST, KHÔNG verb-divergence (KHÁC §8.14/§8.15):** handler `confirm_inspection` `api/imm09.py:103` đã có decorator **`@frappe.whitelist(methods=['POST'])`** SẴN — write-action (mutate `status`, `docstatus 0→1`) khai POST đúng-semantics. ⇒ **KHÔNG lệch contract↔source** (KHÁC `submitPmResult` §8.14 / `submitCalibration` §8.15 bare-`@whitelist` cần fix backlog). **KHÔNG** vào `_PARITY_VERB_ALLOWLIST` (mirror `closeIncident` §8.16 clean-POST). **Guard discipline**: TC-a assert path **POST-ONLY** (chỉ key `post` — khớp source `methods=['POST']`); TC-i live-signature parity assert chữ-ký THẬT `inspect.signature(imm09.confirm_inspection)=={name}` (1 positional, 0 optional).

**Endpoint:** `POST /api/method/assetcore.api.imm09.confirm_inspection` — opId `confirmInspection`. **POST-ONLY** (`@frappe.whitelist(methods=['POST'])` `api/imm09.py:103` — path CHỈ key `post`, clean POST). Cap: **`repair.submit`** (`rbac.require('repair.submit')` `api/imm09.py:105` — **KHÁC `repair.create`** của `createRepairWorkOrder`: confirm cần vai **phê-duyệt-chất-lượng** QA Officer / Trưởng khoa / Workshop Manager).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | INLINE `application/json` `$ref ConfirmInspectionRequest` (`required:true`, KHÔNG component) — content **oneOf `application/json` + `application/x-www-form-urlencoded`** (Frappe RPC `/api/method` đọc `form_dict`; §4/§9 — codegen JSON-only client cần header `application/json` tường minh HOẶC form-encoded). | mirror `SubmitCalibrationRequest` (§8.15) + §9 `form_dict` |
| `ConfirmInspectionRequest` | closed `{name string REQUIRED}` — `additionalProperties:false`. **CHỈ 1 field** (`name` positional bắt buộc), **0 optional**. | signature `confirm_inspection(name)` `api/imm09.py:104` (1 positional, 0 default ⇒ 1 required, 0 optional) |
| **200** | oneOf `[ConfirmInspectionEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (**C8-ACTION**, **0 discriminator**), cả 2 closed (`additionalProperties:false`) + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `ConfirmInspectionEnvelope` | closed `required[success,data]`; `success enum[true]`; `data` = **`$ref ConfirmInspectionResponse`**. | route-by-VALUE C8-ACTION |
| `ConfirmInspectionEnvelope.data` | **`ConfirmInspectionResponse`** closed 4-key **RIÊNG, KHÔNG reuse `CloseWorkOrderResponse`** (xem ADR trên: shape-trùng nhưng `status` INVARIANT `Completed` — C3-split cross-action). | `svc.confirm_inspection` return `{name,status,mttr_hours,sla_breached}` `services/imm09.py:1116-1121` |
| `ConfirmInspectionResponse` | closed `additionalProperties:false`, **EXACT 4 prop** `{name string, status string, mttr_hours number nullable, sla_breached integer enum[0,1]}`, **`required[name, status]`**. | `services/imm09.py:1116-1121` return-dict |
| `name` | `type:string` (echo input WO id). | `name` `services/imm09.py:1117` |
| `status` | `type:string, enum: [Completed]` — **single-value INVARIANT** (terminal-thật; service trả cứng `RepairStatus.COMPLETED` `services/imm09.py:1118`, KHÔNG rẽ nhánh). KHÁC `CloseWorkOrderResponse.status` 2-value. | `RepairStatus.COMPLETED` `services/imm09.py:1118`; `asset_repair.json` Select |
| `mttr_hours` | `type:number, nullable:true` — MTTR (giờ) `doc.mttr_hours` (Float `asset_repair.json`) chốt bởi `complete_repair()` sau `submit()`; nullable phòng giá-trị chưa-set. | `doc.mttr_hours` `services/imm09.py:1119`; `asset_repair.json` Float |
| `sla_breached` | `type:integer, enum:[0,1]` — cờ SLA breach (Check 0\|1 `asset_repair.json`) — **`integer` KHÔNG `boolean`** (Open#1 int-vs-bool sweep; mirror `CloseWorkOrderResponse.sla_breached`). | `doc.sla_breached` `services/imm09.py:1120`; `asset_repair.json` Check |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = **dispatcher-403** (guest/no-token, trip TRƯỚC `handle()` → HTTP-line 403 THẬT + FrappeRawError). **KHÁC `reportIncident` DUAL-403**: in-handler **cap-403** (`rbac.require('repair.submit')` `api/imm09.py:105`) NÉM `frappe.throw(PermissionError)` ⇒ HTTP-line 403 THẬT (KHÔNG HTTP-200) → đã PHỦ bởi single-shape `Forbidden`; slot 403 KHÔNG schema mới (mirror `closeWorkOrder`/`closeIncident`). | `api/imm09.py:105` (in-handler cap) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid → HTTP-401 THẬT). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409` (lỗi nghiệp vụ in-handler arrive HTTP-200 + Error, route theo `body.http_status`, xem ô dưới). | §5 quirk |

> 📌 **2 case Error-on-HTTP-200 (in-handler, ARRIVE nhánh Error 200-oneOf — KHÔNG status-line):**
> - **`IMM09_NOT_FOUND`** — WO không tồn tại (`services/imm09.py:1101` `nthrow(MSG.IMM09_NOT_FOUND, name=name)`) ⇒ Error body `code=NOT_FOUND`, `http_status=404` (`messages.py:639`). Đến trên **HTTP-200** (quirk §5: `nthrow → handle()` return Error-dict), client route theo `body.http_status=404`.
> - **`IMM09_BAD_STATE`** — `status ≠ Pending Inspection` (`services/imm09.py:1102-1103` `nthrow(MSG.IMM09_BAD_STATE, state=doc.status, expected=Pending Inspection)`) ⇒ Error body `code=BAD_STATE`, `http_status=409` (`messages.py:646`). Đến trên **HTTP-200**, client route theo `body.http_status=409` + SHOW `error` ("Không thể thực hiện khi lệnh đang ở '<state>'… Chỉ áp dụng khi đang Pending Inspection").
> ⚠️ **Note BA acceptance-vs-source:** acceptance text gợi ý `IMM09_BAD_STATE` code `BAD_STATE/VALIDATION_ERROR` http 422; **SOURCE THẬT** (`messages.py:646`) = **`http_status=409`** (xung-đột trạng-thái, KHÔNG validation-field). Contract khai theo **source (409)** — KHÔNG bịa 422. Cả 2 case CHỈ biểu-diễn trong nhánh **`Error`** của 200-oneOf (`Error.http_status` bounded enum đã chứa `[404,409]`, `Error.code` enum chứa `NOT_FOUND`/`BAD_STATE`) ⇒ KHÔNG cần mở schema/slot mới.

> 📌 **Transition nghiệp vụ:** `confirm_inspection` chuyển Repair WO `Pending Inspection → Completed` qua `doc.submit()` (`services/imm09.py:1108`, docstatus 0→1) → `on_submit → complete_repair()` chốt `mttr_hours`/`sla_breached` + **restore Asset có điều kiện (BR-09-09)**: Asset → `Active` CHỈ khi đang `Under Repair`; `Out of Service`/`Decommissioned` (hold governance khác) giữ nguyên — WO vẫn đóng được. Set `dept_head_confirmation_datetime=now()` `:1106`. **Side-effect cross-module**: nếu `root_cause_category` chứa từ-khoá chronic → auto `imm12.detect_chronic_failures()` (`services/imm09.py:1124-1131`, non-blocking try/except — IMM-09 → IMM-12). `name` REQUIRED. **0 đụng `.py`** (handler + `methods=['POST']` `api/imm09.py:103` + cap-gate `repair.submit` + return-shape 4-key sẵn @source) — **clean POST, KHÔNG verb-divergence, no ADR-fix needed** (KHÁC §8.14/§8.15). Live HTTP cần USER reload (HARD-STOP). **Guard:** `TestMobileConfirmInspectionContract` (≥7 TC: a path-POST-only+opId · b request closed single-name+oneOf-json-form · c 200-oneOf-route-by-value · d envelope-closed-data-ref · e response-EXACT-4-prop-required[name,status]-grounded · f status-single-value-enum[Completed]+sla_breached-int-enum[0,1]-not-bool · g 403-single-shape+slot{200,401,403} · h symmetry-set+0-dangling · i live-sig-parity `{name}`).

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

### 8.21 FLOW-6 READ-RECEIPT — đánh dấu 1 thông báo đã đọc (`markNotificationAsRead`: WRITE-action ĐẦU TIÊN trên Notification Log)

**Boundaries — Always / Never:**
- **Always:** gọi `markNotificationAsRead(name)` khi user **tap/mở** 1 thông-báo (tab chuông HOẶC push deep-link flow-6) → giảm badge chưa-đọc; route theo `data.read==1` để cập-nhật UI local.
- **Never:** KHÔNG gọi qua GET (state-mutation); KHÔNG suy đoán `status` (response KHÔNG có); KHÔNG mark thông-báo của user khác (server chặn — chỉ chủ).

**Endpoint:** `POST /api/method/assetcore.api.layout.mark_notification_as_read` — opId `markNotificationAsRead`. `@frappe.whitelist(methods=['POST'])` `api/layout.py:102` — **CLEAN POST** (KHÔNG verb-divergence, KHÔNG state-mutation qua GET/CSRF). **WRITE-action ĐẦU TIÊN trên domain Notification Log** (R12-30 đều mutate WO/Incident/Calibration). **Đóng dead-end của `listNotifications` (§8.17):** tab chuông + push deep-link CHỈ-ĐỌC danh-sách — chưa có endpoint flip `read`.

**Cap + ownership:** any-authenticated; server **ÉP** ownership `for_user == session.user` `api/layout.py:111-113` ⇒ user khác → **in-handler cap-403** (Error envelope HTTP-200, KHÔNG dispatcher-403). Guest/no-token → dispatcher PermissionError HTTP-403 (status-line). Notification∄ `api/layout.py:108-109` → **404 trên HTTP-200** (Error body, route theo `Error.http_status` enum chứa 404).

**requestBody:** closed `{name}` (signature `mark_notification_as_read(name)` `api/layout.py:103` — 0 optional). content oneOf `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict`). `MarkNotificationReadRequest` `additionalProperties:false` required `[name]`.

**Response 200 = oneOf [`MarkNotificationReadEnvelope`, `Error`]** closed-schema route-by-VALUE `body.success` (0 discriminator). Slot CHỈ `{200, 401, 403}` (404 đến trên HTTP-200 qua Error). 401→`Unauthorized401`, 403→`Forbidden` SINGLE-SHAPE.

- **`MarkNotificationReadResponse` EXACT 2-prop `{name, read}`** GROUNDED `_ok({"name":name, "read":1})` `api/layout.py:117`. `read = integer enum[0,1]` (mirror `NotificationListItem.read` §8.17 SSoT int-vs-bool, **KHÔNG boolean** → né strict-codegen Dart/Kotlin deser crash). `additionalProperties:false` required `[name, read]`.
- **KHÔNG field `status`** — Notification Log KHÔNG có `workflow_state` ⇒ **C3-split cross-domain**: schema RIÊNG, KHÔNG reuse mọi `*ActionResponse` lifecycle (đều mang `status`/domain-field). Cross-ref **ADR-IMM00-OPENAPI §D-OAS-MARKNOTIFREAD** (rationale + alternatives bác).

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -d 'name=a1b2c3d4e5' \
  "https://HOST/api/method/assetcore.api.layout.mark_notification_as_read"
# HTTP/1.1 200 OK
# {"success": true, "data": {"name": "a1b2c3d4e5", "read": 1}}
#   ← _ok({name, read:1}) layout.py:117. KHÔNG status (Notification Log không workflow_state).
# Notification∄ → {"success": false, "error": "...", "code": "NOT_FOUND", "http_status": 404}  (vẫn HTTP-200)
# KHÔNG phải chủ → {"success": false, ..., "code": "FORBIDDEN", "http_status": 403}  (vẫn HTTP-200)
```

> 🔑 **∈ `_MVP_BUSINESS_PATHS`** ⇒ 401∧403 symmetry tự +1 (test so SET). **∈ `_MVP_ACTION_ENVELOPE`** (C5 32-path registry). Guard riêng = `TestMobileMarkNotificationReadContract` (a..g+i). **KHÔNG `.py`/reload/migrate** — BE handler LIVE landed, pure-yaml + guard.

---

### 8.22 FLOW-REPAIR SPARE-PARTS — picker tìm vật-tư (`searchSpareParts`: GET RAW-list, no-pagination, slot `{200,401}` no-403)

> **Quyết định kiến trúc:** [`ADR-MOBILE-010.md`](./ADR-MOBILE-010.md) (repair spare-parts sub-flow). Lấp **dead-end gắn-vật-tư** trên màn repair-detail: sau `submitDiagnosis(needs_parts=1)` (§8.11-bis → `Pending Parts`) KTV cần **tìm vật tư** rồi gắn phiếu xuất kho — nhưng chưa có endpoint picker. Đây là path **read-only picker ĐẦU** của cặp sub-flow (kế tiếp `requestSpareParts` §8.23). **KHÁC `getAssetIncidentHistory` §8.18** (no-pagination NHƯNG `data={asset,items}`): `searchSpareParts` `data` = **list TRẦN** (`_ok(list)`, KHÔNG wrapper object).

**Boundaries — Always / Never:**
- **Always:** gọi `searchSpareParts(query, limit?)` khi KTV gõ ≥2 ký-tự ở ô tìm vật-tư; render list trần cap bởi `limit`; route `[]` rỗng = "không tìm thấy" (KHÔNG lỗi).
- **Never:** KHÔNG kỳ vọng pagination (svc cap bởi `limit`, KHÔNG `page`/`total`); KHÔNG kỳ vọng 403 (read-only, no api-level cap-gate); KHÔNG gửi POST (read-only GET).

**Endpoint:** `GET /api/method/assetcore.api.imm09.search_spare_parts` — opId `searchSpareParts`. **GET** (bare `@frappe.whitelist()` nhận GET `api/imm09.py:123`). **Cap đọc:** any-authenticated read picker — **KHÔNG `rbac.require` trong handler** (`api/imm09.py:124-125` chỉ `handle(svc.search_spare_parts, query, limit=int(limit))`) ⇒ KHÔNG in-handler cap-403. Guest/no-token → dispatcher-401/403. Read-only — **KHÔNG audit**.

**Query param (KHỚP signature `search_spare_parts(query="", limit="10")` `api/imm09.py:124`):**

| Param | in | required | type | default | Ground |
|---|---|---|---|---|---|
| `query` | query | ✅ true | string | — | chuỗi tìm `part_name`/`manufacturer_part_no` LIKE; `<2` ký-tự → `[]` (`services/imm09.py:1224`). *(handler có default `""` nhưng contract khai required — picker luôn gửi)* |
| `limit` | query | ❌ | integer | `10` | SQL `LIMIT %(lim)s` `services/imm09.py:1232,1234`; handler ép `int(limit)` `api/imm09.py:125`. **KHÔNG** `page`/`page_size` (svc không paginate) |

**200 = oneOf [`SearchSparePartsEnvelope`, `Error`]** closed-schema route-by-VALUE `body.success` (C7 read-path, 0 discriminator; mirror `getAssetIncidentHistory` §5c). 2 nhánh `additionalProperties:false` + disjoint required-set (`[success,data]` vs `[success,error,code,http_status]`) ⇒ codegen route ĐÚNG KHÔNG discriminator.

| Slot | Schema | Ground |
|---|---|---|
| `SearchSparePartsEnvelope` | closed `required[success,data]`, `success enum[true]`; `data` = **array `<SearchSparePartItem>` TRẦN** (KHÔNG object-wrapper/pagination — `_ok(list)` `api/imm09.py:125`, svc trả `list[dict]` cap SQL `LIMIT`). `[]` rỗng hợp lệ (query<2 / no-match — **KHÔNG 404**) | `handle()/_ok(list)` `services/imm09.py:1237-1248` |
| `SearchSparePartItem` | closed (`additionalProperties:false`), **EXACT 10 prop** `{item_code, item_name, manufacturer_part_no, qty, uom, unit_cost, total_cost, stock_entry_ref, notes, idx}`, `required[item_code]` | `services/imm09.py:1237-1246` (dict-literal mỗi row) |

**Int-vs-bool trap né sẵn (Open#1):** 10 prop = 5 string (`item_code`/`item_name`/`manufacturer_part_no`/`uom`/`stock_entry_ref`/`notes` — 6 string) + 2 integer (`qty`=1, `idx`=0) + 2 number (`unit_cost`/`total_cost` `float()`) ⇒ **0 boolean/Check field** ⇒ 0 prop `integer enum[0,1]`. KHÁC `IncidentListItem` (28-field có Check→int). **Response slot CHỈ `{200,401}` — KHÔNG 403** (no api-level cap-gate; mirror `getUserContext` §8.19 no-403, KHÁC mọi list-read khác có 403). 401 = `Unauthorized401` SINGLE-SHAPE.

> 🔑 **NOT ∈ `_MVP_BUSINESS_PATHS` / `_MVP_READ_ENVELOPE`:** `searchSpareParts` là **read-only picker no-cap-gate** (no `rbac.require`) ⇒ KHÔNG "MVP-business path" (đưa vào sẽ ép 403 symmetry → vỡ vì no-403). Typed-200 oneOf phủ độc-lập bởi guard riêng `TestMobileSearchSparePartsContract`. Ranh-giới scope rõ ràng (mirror `getUserContext`), KHÔNG thiếu-sót coverage.

**0 đụng `.py`** (handler + service LIVE whitelisted, sig nguyên — `git diff api/imm09.py + services/imm09.py` = empty cho search) ⇒ **KHÔNG reload gunicorn / KHÔNG migrate / KHÔNG commit** (pure-yaml + guard test). **Guard:** `TestMobileSearchSparePartsContract` (+TC a..i — incl. TC-b query-param parity `{query required, limit default 10}` + TC-d envelope-RAW-list-no-pagination + TC-e item-exact-10 + TC-f no-int-bool-trap + TC-g slot-`{200,401}`-no-403 + TC-i live-sig parity `inspect.signature(imm09.search_spare_parts)=={query,limit}`, chống drift contract↔source). **SSoT:** `api/imm09.py:123-125` + `services/imm09.py:1223-1248` + `imm_device_spare_part.json`.

---

### 8.23 FLOW-REPAIR SPARE-PARTS — gắn phiếu xuất kho (`requestSpareParts`: POST CLEAN, `RequestSparePartsResponse` RIÊNG 4-key)

> **Quyết định kiến trúc:** [`ADR-MOBILE-010.md`](./ADR-MOBILE-010.md) (repair spare-parts sub-flow). Mắt-xích **WRITE** của cặp sub-flow — sau `searchSpareParts` (§8.22, picker) KTV gắn `stock_entry_ref` vào dòng `spare_parts_used`. Chuỗi đầy-đủ: `submitDiagnosis(needs_parts=1) → [searchSpareParts] → requestSpareParts → startRepair/closeWorkOrder`.
>
> **⚠️ ADR — schema RIÊNG `RequestSparePartsResponse` 4-key, KHÔNG reuse `RepairActionResponse` 2-key (Self-Correction §8.11):** §8.11 forward-reserve `RepairActionResponse {name,status}` "tái dùng cho `assign_technician`/`submit_diagnosis`/`request_spare_parts`". Đúng cho `submitDiagnosis` (2-key) nhưng **SAI cho `request_spare_parts`**: service THẬT trả **4-key** `{name, status, updated, allocation}` (`services/imm09.py:1018-1019`) — `updated` (số row gắn được `stock_entry_ref`) + `allocation` (name `IMM Spare Allocation` Gate-2 IMM-15, str\|None). ⇒ Sinh **`RequestSparePartsResponse` closed 4-key** + envelope riêng (C3-split field-disjoint; precedent `ResolveIncidentResponse` 3-key thêm `rca_created`, `AssignTechnicianResponse` 3-key thêm `assigned_to` §8.x). **Alternative bác:** reuse 2-key → DROP `updated`+`allocation`, client mất tín-hiệu gắn-mấy-dòng + allocation-nào → thừa re-fetch + lệch source. **Note:** `RepairActionResponse` chỉ còn đúng forward-reserve cho action 2-key thuần (`submitDiagnosis`).
>
> **✅ ADR — CLEAN POST, KHÔNG verb-divergence (Self-Correction premise "flip bare→POST"):** acceptance ghi "flip `request_spare_parts` bare→`methods=['POST']`" — NHƯNG `git show HEAD:assetcore/api/imm09.py` cho thấy decorator **đã là `@frappe.whitelist(methods=["POST"])`** (committed vòng trước). ⇒ `requestSpareParts` là **CLEAN POST** (mirror `closeIncident` §8.16), KHÔNG lệch contract↔source, **KHÔNG** vào `_PARITY_VERB_ALLOWLIST` (giữ `set()` rỗng). Flip round này = no-op + vi phạm PURE-YAML. **Guard discipline:** TC-a assert path **POST-ONLY** (chỉ key `post` — khớp source `methods=['POST']`, KHÔNG anti-false-green vì source THẬT đã POST-only); TC-i live-sig parity `{name,parts}`.

**Endpoint:** `POST /api/method/assetcore.api.imm09.request_spare_parts` — opId `requestSpareParts`. **POST-ONLY** (`@frappe.whitelist(methods=['POST'])` `api/imm09.py:77` — path CHỈ key `post`, CLEAN POST). **Dual cap:** api-level `repair.write` (`rbac.require('repair.write')` `api/imm09.py:79`) + service-level `repair.create` (`rbac.require('repair.create')` `services/imm09.py:973`) — đều in-handler cap-403.

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | `required:true`, content **oneOf** `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict`; `parts` gửi như JSON-array, BE `parse_json` string `api/imm09.py:80`) `$ref RequestSparePartsRequest`. | `api/imm09.py:78,80` |
| `RequestSparePartsRequest` | closed (`additionalProperties:false`) `required[name, parts]` — `name string`; `parts array<RequestSparePartItem>`. **2 field bắt buộc** (`name` positional; `parts` có default `"[]"` NHƯNG contract khai required — sub-flow luôn gửi ≥1 part). | signature `request_spare_parts(name, parts='[]')` `api/imm09.py:78` |
| `RequestSparePartItem` | object `additionalProperties:false` props `{item_code string, stock_entry_ref string opt, spare_part string opt, qty number opt}` — `required[item_code]`. (`item_code` match row `spare_parts_used`; `spare_part`/`qty` cho Gate-2 allocation IMM-15.) | `part.get('item_code')` `services/imm09.py:980`; `part.get('stock_entry_ref')` `:981`; `p.get('spare_part')`/`p.get('qty')` `:996-997` |
| **200** | oneOf `[RequestSparePartsEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `RequestSparePartsEnvelope.data` | **`RequestSparePartsResponse`** closed (`additionalProperties:false`) **4-key** `{name string, status string, updated integer, allocation (string\|null nullable)}` — `required[name,status]`. **Schema RIÊNG, KHÔNG reuse `RepairActionResponse`** (xem ADR trên). `status` RepairStatus-canonical 9-state, post-request = `In Repair` (nếu rời `Pending Parts`) hoặc giữ nguyên. | `svc.request_spare_parts` return `{'name':name,'status':doc.status,'updated':updated,'allocation':allocation_name}` `services/imm09.py:1018-1019` |
| `updated` | `type:integer` — số row `spare_parts_used` khớp `item_code` được gắn `stock_entry_ref` (`updated += 1` `services/imm09.py:982`). Client hiển thị "đã gắn N dòng". **GENUINE integer count** (KHÔNG enum[0,1]). | `services/imm09.py:977,982` |
| `allocation` | `type:string, nullable:true` (OAS 3.0.3) — name `IMM Spare Allocation` Gate-2 IMM-15 (`alloc.get('name')` `services/imm09.py:1013`); `null` khi không có item/warehouse HOẶC `create_allocation` raise (try/except nuốt → `None` `services/imm09.py:992,1014-1016`). | `services/imm09.py:992,1013,1018-1019` |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403**: in-handler cap-403 (`repair.write` `api/imm09.py:79` + `repair.create` `services/imm09.py:973`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403 (mirror `startRepair`/`closeIncident`). | `api/imm09.py:79` + `services/imm09.py:973` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404` (lỗi nghiệp vụ in-handler `IMM09_NOT_FOUND` WO∄ → code `NOT_FOUND` http_status `404` arrive HTTP-200 + Error, route theo `body.http_status` ∈ bounded enum {400,401,403,404,409,413,422,429,500} R11). | §5 quirk; `services/imm09.py:975-976` + `utils/messages.py` (IMM09_NOT_FOUND 404) |

> 📌 **Transition + Gate-2 cross-module:** `request_spare_parts` gắn `stock_entry_ref` vào row `spare_parts_used` khớp `item_code` (`services/imm09.py:978-982`); nếu `status == Pending Parts` ⇒ `exit_parts_hold(doc)` chốt `parts_hold_hours` + ALE `parts_hold_resumed` (SLA tiếp tục, BR-09-10 `services/imm09.py:983-987`) → `In Repair`. **Gate-2 IMM-09→IMM-15 (non-blocking, lazy-import Pattern B):** `imm15.create_allocation(...)` tạo `IMM Spare Allocation` `Requested` nếu có item + tìm được `warehouse` (`AC Spare Part Stock`); bọc `try/except` → fail chỉ `log_error`, KHÔNG vỡ action (`services/imm09.py:991-1016`). `allocation` = name hoặc `null`. `name`+`parts` REQUIRED. **0 đụng `.py`** (handler + `methods=['POST']` `api/imm09.py:77` + dual cap-gate + return-shape 4-key sẵn @source — **CLEAN POST, KHÔNG verb-divergence, no ADR-fix needed**). Sau USER reload gunicorn `--preload` → LIVE reject GET(405); trước reload stale worker còn nhận GET — KHÔNG curl-verify LIVE (LL-DEPLOY-07). Live HTTP cần USER reload (HARD-STOP).

> 🔑 **∈ `_MVP_BUSINESS_PATHS`** ⇒ 401∧403 symmetry tự +1 (test so SET). **∈ `_MVP_ACTION_ENVELOPE`** (C5 registry). Guard riêng = `TestMobileRequestSparePartsContract` (a..g+i — incl. TC-a POST-ONLY + TC-e data-exact-4-key + TC-f `updated` integer / `allocation` nullable + TC-i live-sig `{name,parts}`). **KHÔNG `.py`/reload/migrate** — BE handler LIVE landed (POST-only @HEAD), pure-yaml + guard.

---

### 8.24 FLOW-CALIBRATION MEASUREMENT-ENTRY — ghi điểm đo (`addMeasurement`: POST mắt-xích-GIỮA, VERB-FLIP-THIS-ROUND, `AddMeasurementResponse` 2-key `measurement_count` GENUINE integer)

> **Quyết định kiến trúc:** [`ADR-MOBILE-011.md`](./ADR-MOBILE-011.md) (calibration measurement-entry). **Mắt-xích-GIỮA** chuỗi calibration-detail: `createCalibration` (§8.6, ✅) → **`addMeasurement` (THIẾU — vòng này bồi)** → `submitCalibration` (§8.15, ✅). KTV mở `getCalibration` detail (`Scheduled`/`In Progress`) nhập N điểm-đo (`parameter_name`/`nominal_value`/`tolerance ±`/`measured_value`) vào child table `measurements` TRƯỚC khi chốt; thiếu path này ⇒ `submitCalibration` tính `overall_result` trên measurement-set **RỖNG**. Path/opId **42→43**, `info.version` GIỮ `0.1.0-skeleton`, 0 dangling `$ref`.
>
> **⚠️ ADR — schema RIÊNG `AddMeasurementResponse` 2-key, `measurement_count` GENUINE integer (KHÔNG enum[0,1]):** service THẬT trả **2-key** `{name, measurement_count}` (`services/imm11.py:1124`) — `measurement_count = len(doc.measurements)` (số row child-table sau append). ⇒ Sinh **`AddMeasurementResponse` closed 2-key** + envelope riêng (C3-split — field-set `{name,measurement_count}` ≠ `SubmitCalibrationResponse` 4-key §8.15 ≠ mọi `*ActionResponse`). `measurement_count` = `type:integer` THUẦN (có thể >1 — N điểm-đo), **KHÔNG `enum[0,1]`** (precedent `updated`/`requestSpareParts` ADR-MOBILE-010 §8.23 — số đếm thật, không phải Check-field Open#1). **Alternative bác:** reuse `{name,status}` → DROP `measurement_count` + bịa `status` không có trong return. Loại.
>
> **⚠️ ADR — VERB-FLIP-THIS-ROUND (KHÁC §8.15/§8.14 backlog):** handler `add_measurement` `api/imm11.py:120` hiện **bare `@frappe.whitelist()`** ⇒ runtime nhận cả GET — nhưng là write-action (append child-row, **KHÔNG idempotent**: N call = N row). Đây là **verb-parity gap R33 BỎ SÓT** (R33 VERB-PARITY CLOSURE đã flip `create_calibration` `api/imm11.py:89` + `submit_calibration` `api/imm11.py:114` + `submit_pm_result` `imm08.py:54` → `methods=['POST']` + làm rỗng `_PARITY_VERB_ALLOWLIST`→`set()`, NHƯNG SÓT `add_measurement`). ⇒ Vòng này **flip ĐÚNG 1 dòng decorator** `api/imm11.py:120` → `@frappe.whitelist(methods=['POST'])` **NGAY** (`git diff api/imm11.py` = đúng 1 dòng; signature/body/`rbac.require('calibration.write')` UNCHANGED) ⇒ contract POST khớp source POST-only ⇒ **KHÔNG verb-divergence** ⇒ **KHÔNG** vào `_PARITY_VERB_ALLOWLIST` (GIỮ `set()` rỗng). **Guard discipline:** TC-a assert path **POST-ONLY** (chỉ key `post` — khớp source SAU flip, KHÔNG anti-false-green); TC-i live-signature parity `inspect.signature(imm11.add_measurement)` == `{name,parameter_name,unit,nominal_value,tolerance_positive,tolerance_negative,measured_value}`. **Self-Correction:** verb-divergence language ở §8.15/§9b (submitCalibration/create_calibration "backlog HARD-STOP", "_PARITY_VERB_ALLOWLIST 2→3") nay **STALE** — đã CLOSED ở R33; xem note [SELF-CORRECTION R34] tại §8.15/§9b.

**Endpoint:** `POST /api/method/assetcore.api.imm11.add_measurement` — opId `addMeasurement`, tag `calibration`. **POST-only SAU flip** (`api/imm11.py:120` flip bare→`methods=['POST']` round này — path CHỈ key `post`). Cap: `calibration.write` (`rbac.require('calibration.write')` `api/imm11.py:124` — in-handler cap-403).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | `required:true` (đặt trong component), content **oneOf** `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict`) `$ref AddMeasurementRequest`; path-level = `$ref`-ONLY `requestBodies/AddMeasurementBody` (G-OAS-403-DISAMBIG: KHÔNG sibling cạnh `$ref`). | `api/imm11.py:121-123`; `services/imm11.py:1107` |
| `AddMeasurementRequest` | closed (`additionalProperties:false`) `required` **EXACT** `[name, parameter_name, unit, nominal_value, tolerance_positive, tolerance_negative]` (6 tham số KHÔNG default) + optional `measured_value` (`type:number, nullable:true`). `name`/`parameter_name`/`unit` = `string`; `nominal_value`/`tolerance_positive`/`tolerance_negative`/`measured_value` = `number`. | signature `add_measurement(name, parameter_name, unit, nominal_value, tolerance_positive, tolerance_negative, measured_value=None)` `api/imm11.py:121-123`; svc `services/imm11.py:1107-1109` |
| **200** | oneOf `[AddMeasurementEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed (`additionalProperties:false`) + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `AddMeasurementEnvelope.data` | **`AddMeasurementResponse`** closed (`additionalProperties:false`) **EXACT 2-key** `{name string, measurement_count integer}` — `required[name, measurement_count]` (cả 2 luôn trả). **Schema RIÊNG, KHÔNG reuse `SubmitCalibrationResponse`/`*ActionResponse`** (xem ADR trên). | `svc.add_measurement` return `{'name':doc.name, 'measurement_count':len(doc.measurements)}` `services/imm11.py:1124` |
| `measurement_count` | `type:integer` — số row `measurements` sau append (`len(doc.measurements)`). Client hiển thị "đã ghi N điểm-đo". **GENUINE integer count** (có thể >1, **KHÔNG enum[0,1]** — không phải Check-field). **0 boolean prop** ⇒ 0 prop `integer enum[0,1]` (Open#1 KHÔNG áp). | `services/imm11.py:1124` |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). **KHÁC `reportIncident` DUAL-403**: in-handler cap-403 (`calibration.write` `api/imm11.py:124`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ cần dispatcher-403 (mirror `submitCalibration`/`startRepair`). | `api/imm11.py:124` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409` (lỗi nghiệp vụ in-handler: phiếu∄ `IMM11_CAL_NOT_FOUND` `services/imm11.py:1112` → `code=NOT_FOUND http_status=404`; đã-submit `IMM11_ALREADY_SUBMITTED` `docstatus==1` `services/imm11.py:1114` → `code=CONFLICT http_status=409` — CẢ HAI arrive HTTP-200 + Error, route `body.http_status` ∈ bounded enum {400,401,403,404,409,413,422,429,500} R11, **enum ĐÃ ⊇ {404,409} KHÔNG đổi**). | §5 quirk; `services/imm11.py:1112,1114` |

> 📌 **Transition nghiệp vụ:** `add_measurement` append 1 row `{parameter_name, unit, nominal_value, tolerance_positive, tolerance_negative, measured_value}` vào child table `measurements` (`services/imm11.py:1115-1122`) rồi `CalibrationRepo.save(doc)` (`:1123`) — **KHÔNG đổi `docstatus`** (giữ draft 0; pre-condition `docstatus==0` else 409). N call = N row (KHÔNG idempotent ⇒ POST đúng-semantics). `submitCalibration` (§8.15) đọc measurement-set này để tính `overall_result`. **⚠️ ĐỤNG 1 dòng `.py`** = flip decorator `api/imm11.py:120` bare→`methods=['POST']` (handler body + cap-gate + return-shape 2-key sẵn @source; CHỈ verb-flip). Sau USER reload gunicorn `--preload` → LIVE reject GET(405); trước reload stale worker còn nhận GET — **KHÔNG curl-verify LIVE** (LL-DEPLOY-07). KHÔNG reload/migrate/commit (HARD-STOP USER).

> 🔑 **∈ `_MVP_BUSINESS_PATHS`** ⇒ 401∧403 symmetry tự +1 (test so SET). **∈ `_MVP_ACTION_ENVELOPE`** (map `→ #/components/schemas/AddMeasurementEnvelope`, C5 registry). Guard riêng = `TestMobileAddMeasurementContract` (a..j — incl. TC-a POST-ONLY-at-source-SAU-flip / TC-b opId+tag+mvp / TC-c requestBody oneOf json+form required-EXACT-6 + measured_value optional nullable / TC-d 200-oneOf closed 0-discr / TC-e data EXACT 2-key {name,measurement_count} / TC-f `measurement_count` integer GENUINE-count KHÔNG enum[0,1] / TC-g slot {200,401,403} Error.http_status ⊇ {404,409} / TC-h mvp+action-envelope+symmetry no-dangling / TC-i live-sig 7-param / TC-j git-diff imm11.py = ĐÚNG 1 dòng decorator + `_PARITY_VERB_ALLOWLIST`==set()). `_EXPECTED_TEST_COUNT` bump từ **397**; re-baseline `test_oas_d12` (`_BASELINE_GET 235→234`) + `test_oas_d17` (`get_count 235→234`/`post_count 253→254`) **@source SAU flip** (KHÔNG tin tuyệt đối số acceptance). `test_imm11`/`test_mobile_docset`/`test_mobile_security_gate` no-regress. RED-before chứng minh cho MỌI TC mới.

### 8.25 FLOW-PM DISPATCH — phân công KTV (`assignPmTechnician`: POST mắt-xích-GIỮA PM-detail, VERB-FLIP-THIS-ROUND, `AssignPmTechnicianResponse` 3-key `status`=PMStatus "In Progress" — C3-split RIÊNG ≠ repair)

> **Quyết định kiến trúc:** [`ADR-MOBILE-012.md`](./ADR-MOBILE-012.md) (PM-dispatch). **Mắt-xích-GIỮA** chuỗi PM-detail: `createPmWorkOrder` (✅) → **`assignPmTechnician` (THIẾU — vòng này bồi)** → `submitPmResult` (§8.14, ✅). Workshop Head mở `getPmWorkOrder` detail (`Open`/`Overdue`) phân công 1 KTV (+`scheduled_date` optional) ⇒ WO → "In Progress" + asset → "Under Maintenance"; thiếu path này ⇒ nút "Phân công" trên `PMWorkOrderDetailView` dead-end (phải làm trên web-FE). **Parity** repair `createRepairWorkOrder → [assignTechnician] → startRepair` (§6458/ADR-IMM09-ASSIGN). Path/opId **43→44**, `info.version` GIỮ `0.1.0-skeleton`, 0 dangling `$ref`.
>
> **⚠️ ADR — schema RIÊNG `AssignPmTechnicianResponse` 3-key, `status`=PMStatus "In Progress" (KHÔNG "Assigned" repair):** service THẬT trả **3-key** `{name, status, assigned_to}` (`services/imm08.py:679`) — `status = PMStatus.IN_PROGRESS` ("In Progress" `:676`). SHAPE 3-key **TRÙNG** repair `AssignTechnicianResponse` NHƯNG `status` enum/value KHÁC domain (PM = PMStatus 7-state, value "In Progress"; repair = RepairStatus 9-state, value "Assigned"). ⇒ Sinh **`AssignPmTechnicianResponse` closed 3-key** + envelope riêng (**C3-split RIÊNG** — precedent `confirmInspection` ADR-MOBILE-009 KHÔNG reuse `CloseWorkOrderResponse` dù shape trùng vì `status`-enum INVARIANT khác). **KHÔNG reuse repair `AssignTechnician*`** (reuse → codegen sinh PM-assign với `status.enum`=RepairStatus 9-state SAI + example "Assigned" SAI domain). **Alternative bác:** reuse repair `AssignTechnicianResponse` / literal-single `enum:[In Progress]`. Loại.
>
> **⚠️ ADR — VERB-FLIP-THIS-ROUND (sibling imm08 của `add_measurement` §8.24):** handler `assign_technician` `api/imm08.py:46` hiện **bare `@frappe.whitelist()`** ⇒ runtime nhận cả GET — nhưng là write-action DISPATCH (status Open/Overdue→In Progress + mutate `assigned_to` + asset-transition, **KHÔNG idempotent**). Đây là **verb-parity gap R33 BỎ SÓT** (R33 đã flip `submit_pm_result` `imm08.py:54` + 3 write-action imm11 → `methods=['POST']` + làm rỗng `_PARITY_VERB_ALLOWLIST`→`set()`, NHƯNG SÓT `assign_technician`). ⚠️ **Core Doc IMM-08 đã khai POST từ lâu** (`05 §0` catalog row #3 = "POST"; `04 §5` code-sketch `methods=["POST"]` `:495`) ⇒ doc đi-trước-code; flip = đưa source khớp doc-intent. ⇒ Vòng này **flip ĐÚNG 1 dòng decorator** `api/imm08.py:46` → `@frappe.whitelist(methods=['POST'])` **NGAY** (`git diff api/imm08.py` = đúng 1 dòng; signature/body/`rbac.require('pm.write')` `:49` UNCHANGED) ⇒ contract POST khớp source POST-only ⇒ **KHÔNG verb-divergence** ⇒ **KHÔNG** vào `_PARITY_VERB_ALLOWLIST` (GIỮ `set()` rỗng). **Guard discipline:** TC-a assert path **POST-ONLY** (chỉ key `post` — khớp source SAU flip); TC-i live-signature parity `inspect.signature(imm08.assign_technician)` == `{name, technician, scheduled_date}`; TC-j git-diff `api/imm08.py` = ĐÚNG 1 dòng decorator + `_PARITY_VERB_ALLOWLIST`==`set()`.

**Endpoint:** `POST /api/method/assetcore.api.imm08.assign_technician` — opId `assignPmTechnician` (UNIQUE — KHÁC repair `assignTechnician`), tag `work-order`, summary `[MVP-4] PM dispatch Open/Overdue→In Progress`. **POST-only SAU flip** (`api/imm08.py:46` flip bare→`methods=['POST']` round này — path CHỈ key `post`). Cap: `pm.write` (`rbac.require('pm.write')` `api/imm08.py:49` — in-handler cap-403).

| Khía cạnh | Hợp đồng | Grounding |
|---|---|---|
| **requestBody** | `required:true`, **INLINE** (path-level, KHÔNG component — mirror repair `assignTechnician` §6486-6496), content **`application/json` ONLY** (**KHÔNG oneOf json+form** — action đơn-record) `$ref AssignPmTechnicianRequest`. | `api/imm08.py:47`; repair §6486-6496 convention |
| `AssignPmTechnicianRequest` | closed (`additionalProperties:false`) `required` **EXACT** `[name, technician]` (2 positional KHÔNG default) + optional `scheduled_date` (`type:string`). Cả 3 prop = `type:string`. | signature `assign_technician(name, technician, scheduled_date=None)` `api/imm08.py:47` |
| **200** | oneOf `[AssignPmTechnicianEnvelope, Error]` ở response-content-schema-level — route-by-VALUE `body.success` (C6/C7, **0 discriminator**), cả 2 closed (`additionalProperties:false`) + `success` enum disjoint `[true]`/`[false]`. | §5c |
| `AssignPmTechnicianEnvelope.data` | **`AssignPmTechnicianResponse`** closed (`additionalProperties:false`) **EXACT 3-key** `{name string, status string, assigned_to string}` — `required[name, status, assigned_to]` (cả 3 luôn trả). **Schema RIÊNG, KHÔNG reuse repair `AssignTechnicianResponse`/`*ActionResponse`** (xem ADR trên). | `svc.assign_technician` return `{'name':wo.name, 'status':wo.status, 'assigned_to':wo.assigned_to}` `services/imm08.py:679` |
| `status` | `type:string`, `enum` = **PMStatus** 7-state `[Open, In Progress, Completed, Overdue, Cancelled, "Halted–Major Failure", "Pending–Device Busy"]` (`services/imm08.py:43-50` — copy en-dash byte-khớp), `example: In Progress` (`PMStatus.IN_PROGRESS` sau assign `:676,679`). **KHÔNG** RepairStatus 9-state, **KHÔNG** "Assigned". | `services/imm08.py:43-50,676,679` |
| `assigned_to` | `type:string` — email KTV được gán (echo `technician` input, `doc.assigned_to` `:672,679`). Đích tiêu thụ `listUsers` (technician-picker). | `services/imm08.py:672,679` |
| **403** | **SINGLE-SHAPE `Forbidden`** (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token, trip TRƯỚC `handle()`). in-handler cap-403 (`pm.write` `api/imm08.py:49`) đã phủ bởi nhánh `Error` của 200-oneOf → slot 403 chỉ dispatcher-403 (mirror `submitPmResult`/`assignTechnician`/`startRepair`). | `api/imm08.py:49` (in-handler) vs `__init__.py:876` (dispatcher) |
| **401** | `$ref Unauthorized401` (bearer hết-hạn/invalid). Response slot CHỈ `{200,401,403}` — KHÔNG bịa status-line `404/409/422` (lỗi nghiệp vụ in-handler: WO∄ `IMM08_WO_NOT_FOUND` `services/imm08.py:659` → `http_status=404` `messages.py:561`; status∉{Open,Overdue} `IMM08_BAD_STATE` `:661` → `http_status=409` `messages.py:582`; asset/`pm_schedule` đã xóa `ServiceError(VALIDATION)` `:663-671` → `http_status=422` — CẢ BA arrive HTTP-200 + Error, route `body.http_status` ∈ bounded enum {400,401,403,404,409,413,422,429,500} R11, **enum ĐÃ ⊇ {404,409,422} KHÔNG đổi**). | §5 quirk; `services/imm08.py:659,661,663-671` |

> 📌 **Transition nghiệp vụ:** `assign_technician` set `assigned_to=technician`, `assigned_by=session.user`, `scheduled_date` (chỉ khi truthy `:674-675`), `status=PMStatus.IN_PROGRESS` (`:676`) → `PMWorkOrderRepo.save` (`:677`) → `_transition_asset(wo.asset_ref, AssetStatus.UNDER_MAINTENANCE, wo.name)` (`:678` — asset → "Under Maintenance" + **sinh Lifecycle Event audit**, BR-08 traceability). Pre-condition `status ∈ {Open, Overdue}` (else 409 `:661`). **⚠️ ĐỤNG 1 dòng `.py`** = flip decorator `api/imm08.py:46` bare→`methods=['POST']` (handler body + cap-gate + return-shape 3-key sẵn @source; CHỈ verb-flip). Sau USER reload gunicorn `--preload` → LIVE reject GET(405); trước reload stale worker còn nhận GET — **KHÔNG curl-verify LIVE** (LL-DEPLOY-07; KHÔNG curl IP 192.168.10.101). KHÔNG reload/migrate/commit (HARD-STOP USER).

> 🔑 **∈ `_MVP_BUSINESS_PATHS`** ⇒ 401∧403 symmetry tự +1 (test so SET). **∈ `_MVP_ACTION_ENVELOPE`** (map `→ #/components/schemas/AssignPmTechnicianEnvelope`, C5 registry). Guard riêng = `TestMobileAssignPmTechnicianContract` (a..j — incl. TC-a POST-ONLY-at-source-SAU-flip / TC-b opId-UNIQUE(≠assignTechnician)+tag+mvp+summary / TC-c requestBody json-only INLINE required-EXACT-2 + scheduled_date optional / TC-d 200-oneOf closed 0-discr / TC-e data EXACT 3-key {name,status,assigned_to} / TC-f `status` enum==PMStatus 7-state example "In Progress" + assert ≠ repair `AssignTechnicianResponse` (C3-split) / TC-g slot {200,401,403} Error.http_status ⊇ {404,409,422} / TC-h mvp+action-envelope+symmetry no-dangling / TC-i live-sig {name,technician,scheduled_date} / TC-j git-diff imm08.py = ĐÚNG 1 dòng decorator + `_PARITY_VERB_ALLOWLIST`==set()). `_EXPECTED_TEST_COUNT` bump từ **408** (+10 → 418); re-baseline `test_oas_d12` (`_BASELINE_GET 234→233`) + `test_oas_d17` (`get_count 234→233`/`post_count 254→255`) **@source SAU flip** (KHÔNG tin tuyệt đối số acceptance). `test_imm08` +BE-unit (assign sinh Lifecycle Event asset→Under Maintenance `:678`), `test_mobile_docset` (path 43→44), `test_mobile_security_gate` no-regress. RED-before chứng minh cho MỌI TC mới.

---

### 8.26 FLOW-6 MARK-ALL-READ — đánh dấu TẤT CẢ thông báo đã đọc (`markAllAsRead`: BULK read-receipt, 0-PARAM no-requestBody, `MarkAllReadResponse` 1-key `updated_rows` GENUINE integer)

> **Quyết định kiến trúc:** [`ADR-MOBILE-018.md`](./ADR-MOBILE-018.md) + [`../imm-00/ADR-IMM00-OPENAPI.md` §D-OAS-MARKALLREAD](../imm-00/ADR-IMM00-OPENAPI.md). **ĐÓNG NỐT notification-center action-set:** sau `markNotificationAsRead` (single read khi user tap 1 thông-báo §8.21), tab "Thông báo" cần nút **"Đánh dấu tất cả đã đọc"** để xoá badge chưa-đọc một-phát. Path/opId **46→47**, `info.version` GIỮ, 0 dangling `$ref`. **🟢 CONTRACT-ONLY** — BE endpoint LIVE @source, KHÔNG đụng `.py`.

**Boundaries — Always / Never:**
- **Always:** gọi `markAllAsRead()` (no-arg) khi user bấm "Đánh dấu tất cả đã đọc" ở tab Thông báo → server flip `read=1` cho MỌI Notification Log chưa-đọc của chính mình; route theo `data.updated_rows` (≥0) để reset badge local.
- **Never:** KHÔNG gọi qua GET (state-mutation); KHÔNG gửi body/param (signature 0-param); KHÔNG suy đoán `status` (response KHÔNG có); KHÔNG mark thông-báo user khác (scope SQL `WHERE for_user=session.user`).

**Endpoint:** `POST /api/method/assetcore.api.layout.mark_all_as_read` — opId `markAllAsRead`. `@frappe.whitelist(methods=['POST'])` `api/layout.py:120` — **CLEAN POST** (KHÔNG verb-divergence, KHÔNG state-mutation qua GET/CSRF). **BULK read-receipt** trên domain Notification Log, mở rộng `markNotificationAsRead` single (§8.21). Service-free (CLAUDE.md §15 ngoại-lệ: thao-tác Notification-Log đơn — `UPDATE` + commit, KHÔNG nghiệp-vụ domain).

**Cap + ownership:** any-authenticated; server **ÉP** ownership qua scope `UPDATE ... WHERE for_user=session.user AND read=0` `api/layout.py:127-131` ⇒ **KHÔNG lookup-by-name** ⇒ **KHÔNG 404/409**. Guest/no-token → dispatcher PermissionError HTTP-403 (status-line, SINGLE-SHAPE `Forbidden`). in-handler guest `api/layout.py:124-125` → **401 trên HTTP-200** (Error body, route theo `Error.http_status`).

**requestBody:** **KHÔNG có** — signature `mark_all_as_read()` `api/layout.py:121` là **0-param** ⇒ codegen sinh **no-arg POST**. Live-sig parity `inspect.signature(layout.mark_all_as_read).parameters == {}` (anti-drift). Phân biệt với `markNotificationAsRead` (closed `{name}`).

**Response 200 = oneOf [`MarkAllReadEnvelope`, `Error`]** closed-schema route-by-VALUE `body.success` (0 discriminator). Slot CHỈ `{200, 401, 403}`. 401→`Unauthorized401`, 403→`Forbidden` SINGLE-SHAPE.

- **`MarkAllReadResponse` EXACT 1-prop `{updated_rows}`** GROUNDED `_ok({"updated_rows": affected})` `api/layout.py:134` (`affected = ROW_COUNT()` `:132`). `updated_rows = type:integer` **WITHOUT enum** — **GENUINE integer count 0..N** (số dòng vừa flip `read` 0→1), KHÔNG enum[0,1]. **KHÁC `read`** của `NotificationListItem` §8.17 / `MarkNotificationReadResponse` §8.21 (đó là cờ Check 2-giá-trị); mirror `AddMeasurementResponse.measurement_count` §8.24. `additionalProperties:false` required `[updated_rows]`.
- **KHÔNG field `status`** — Notification Log KHÔNG có `workflow_state` ⇒ **C3-split cross-domain**: schema RIÊNG, KHÔNG reuse mọi `*ActionResponse` lifecycle lẫn `MarkNotificationReadResponse` `{name,read}`. Cross-ref **ADR-IMM00-OPENAPI §D-OAS-MARKALLREAD** + **ADR-MOBILE-018**.

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  "https://HOST/api/method/assetcore.api.layout.mark_all_as_read"
# HTTP/1.1 200 OK
# {"success": true, "data": {"updated_rows": 7}}
#   ← _ok({updated_rows: affected}) layout.py:134. updated_rows = ĐẾM thật (ROW_COUNT :132), 0 khi không còn chưa-đọc.
# Guest in-handler → {"success": false, ..., "code": "...", "http_status": 401}  (vẫn HTTP-200)
# Guest/no-token dispatcher → HTTP/1.1 403 Forbidden (status-line, KHÔNG envelope)
```

> 🔑 **∈ `_MVP_BUSINESS_PATHS`** ⇒ 401∧403 symmetry tự +1 (test so SET). **∈ `_MVP_ACTION_ENVELOPE`** (map `→ #/components/schemas/MarkAllReadEnvelope`, C5 registry). Clean POST `:120` ⇒ **∉ `_PARITY_VERB_ALLOWLIST`** (runtime `generate_spec` introspect POST authed, khớp YAML). Guard riêng = `TestMobileMarkAllReadContract` (a..g+i, 8 TC — path/opId/tag/mvp · 0-param no-requestBody · 200-oneOf closed 0-discr · data EXACT {updated_rows} integer-NO-enum · slot {200,401,403} SINGLE-SHAPE Forbidden no-404/409 · symmetry SET +1 · 0-dangling · live-sig 0-param · PURE-YAML anti-false-green). `_EXPECTED_TEST_COUNT` 439→447. **KHÔNG `.py`/reload/migrate** — BE handler LIVE landed (`git diff` api/services/layout = TRỐNG); `generate_spec` get/post UNCHANGED ⇒ `d12/d15/d17` RE-VERIFY KHÔNG re-baseline.

### 8.27 FLOW-IMM13 TRANSFER-READ — theo dõi điều chuyển / nhận bàn giao (`listTransfers` SINGLE-shape · `getTransfer` oneOf detail · Đợt-2)

- **`listTransfers`** (GET `assetcore.api.imm00.list_transfers`, `imm00.py:2048`) — danh sách phiếu điều chuyển (Asset Transfer), permission-aware. 4 param DISCRETE query `{asset?, status?, page?, page_size?}` (mirror `listAssets`, KHÔNG JSON `filters`). **200 = SINGLE `TransferListEnvelope`** — handler KHÔNG `try/except` ⇒ 0 nhánh `_err` in-handler ⇒ **KHÔNG `oneOf [Env, Error]`** (mirror `pingSession` single-shape; malformed → 500 NGOÀI 3-shape). rows-key `data.items[]` + `data.pagination` (mirror `IncidentListEnvelope`, KHÔNG `data.data[]`). Element `TransferListItem` closed 17-field GROUNDED `fields=[...]`@`imm00.py:2062-2076` + `asset_name` enrich (`status` enum 5 `[Pending Approval,Approved,Rejected,Received,Cancelled]`@`asset_transfer.json`; `transfer_type` enum `[Internal,Loan,External,Return]`; 0 boolean → 0 int-enum trap). slot `{200,401,403}` (bare `@whitelist` no-`allow_guest` → guest dispatcher-403; 401 `Unauthorized401`, 403 `Forbidden` SINGLE-SHAPE FrappeRawError).
- **`getTransfer`** (GET `assetcore.api.imm00.get_transfer`, `imm00.py:2081`) — chi tiết 1 phiếu (màn detail + nhận bàn giao). 1 param `name` (query req). **200 = `oneOf [TransferDetailEnvelope | Error]`** closed route-by-VALUE 0-discriminator (404 `_err`@`:2084` → Error@HTTP-200 quirk, `Error.http_status ⊇ {404}`; mirror `getIncident`/`getCalibration` C6). `TransferDetail` OPEN (`additionalProperties:true`) = `doc.as_dict()` superset-by-property của `TransferListItem` (mirror `IncidentDetail`/`CalibrationDetail` §3.2 — ENVELOPE đóng + Detail mở vì `as_dict()` mang field meta Frappe ngoài DocType). slot `{200,401,403}`.

> 🔑 **CONTRACT-ONLY** — 6 endpoint điều chuyển ĐÃ LIVE @`api/imm00.py` (`list_transfers:2048` / `get_transfer:2081` + 4 write); `git diff` api/imm00.py + services/imm00.py = TRỐNG ⇒ **KHÔNG `.py`/reload/migrate** ([AUTO] thật, KHÔNG HARD-STOP USER). `getTransfer ∈ _MVP_READ_ENVELOPE`, `listTransfers ∈ _MVP_SINGLE_LIST_ENVELOPE` (bucket RIÊNG single-shape — KHÔNG `_MVP_LIST_ENVELOPE` giữ len==8, KHÔNG `_MVP_READ_ENVELOPE` inline-oneOf) ⇒ C5 41→43, 401∧403 symmetry +2 (test so SET). Guard `TestMobileTransferReadContract` (a..p, 16 TC) ⇒ `_EXPECTED_TEST_COUNT` 467→483. `d12/d15/d17` UNCHANGED (pure mobile-yaml). [ADR-MOBILE-021](./ADR-MOBILE-021.md).

---

### 8.28 FLOW-2 DEVICE-PROFILE — lịch-sử SỬA-CHỮA của thiết bị (`getAssetRepairHistory`: tab "Lịch sử sửa chữa" màn hồ-sơ sau quét QR)

> **Quyết định kiến trúc:** [`ADR-MOBILE-022.md`](./ADR-MOBILE-022.md). 🟦 **ĐÓNG bộ-ba read-history màn hồ-sơ-thiết-bị (flow-2):** `getAssetIncidentHistory` (§8.18 — lịch-sử **sự-cố**, Incident Report) + `getAssetTimeline` (vòng-đời, Asset Lifecycle Event) ĐÃ có, NHƯNG KTV đứng trước máy còn cần lịch-sử **SỬA-CHỮA (CM)** — "máy này từng sửa gì, MTTR bao lâu, có vi phạm SLA?". `getAssetRepairHistory` đóng dead-end này: 1 GET-read danh-sách phiếu `Asset Repair` (`docstatus=1`, mới→cũ, ≤`limit`) của 1 asset. **MIRROR `getAssetIncidentHistory` §8.18 NHƯNG 3 KHÁC-BIỆT có-chủ-đích** (xem ADR-MOBILE-022).

**Endpoint:** `GET /api/method/assetcore.api.imm09.get_asset_repair_history` — opId `getAssetRepairHistory`, tag `repair`. **GET** (bare `@frappe.whitelist()` `api/imm09.py:126`). **Cap đọc:** repair read (qua `handle()` → `svc.get_asset_history` permission-aware). Read-only — **KHÔNG audit**. 2 param: **`asset_ref`** (query, required, string — ⚠️ tên `asset_ref` KHÁC `getAssetIncidentHistory` dùng `asset`) + `limit` (query, optional, integer default 10 — signature `limit="10"` str, handler ép `int()` `api/imm09.py:128`). Live-sig parity `inspect.signature(imm09.get_asset_repair_history)=={asset_ref, limit}`.

- **200 = SINGLE `AssetRepairHistoryEnvelope`** (KHÔNG `oneOf [Env, Error]`) — handler `api/imm09.py:128` = `handle(svc.get_asset_history)`; `svc.get_asset_history` `services/imm09.py:1212-1220` **0 raise `ServiceError`** ⇒ `handle()` `utils/api_handler.py:48-51` LUÔN `_ok` ⇒ 0 nhánh `_err` trên HTTP-200 (mirror `listTransfers` §8.27 / `pingSession`, KHÁC `getAssetIncidentHistory` §8.18 `oneOf`). rows-key **`data.history[]`** + asset-key **`data.asset_ref`** (KHÁC incident `data.items[]`/`data.asset`) — GROUNDED svc `return {"asset_ref": asset_ref, "history": history}` `:1220`. KHÔNG pagination (svc chỉ `page_size`=limit cap). `history[]` RỖNG hợp lệ nếu asset chưa từng sửa → **KHÔNG 404**.
- **Element `AssetRepairHistoryItem`** closed (`additionalProperties:false`) `required [name]` — **EXACT 9 field** GROUNDED `RepairRepo.list fields` `services/imm09.py:1215-1216`: `name` (PK) · `repair_type` · `priority` · `open_datetime` (string, KHÔNG `format:date-time`) · `completion_datetime` (string nullable) · `mttr_hours` (number nullable) · **`sla_breached` (integer — Frappe Check 0/1, KHÔNG `boolean`/`enum[0,1]`, né int-vs-bool trap Open#1)** · `root_cause_category` · `repair_summary`.
- **Slot `{200,401,403}`** — bare `@whitelist` no-`allow_guest` `api/imm09.py:126` → guest/no-token dispatcher-403; `401 Unauthorized401` (bearer hết hạn) + `403 Forbidden` SINGLE-SHAPE (FrappeRawError, mirror `listTransfers`/`searchSpareParts`).

> 🔑 **CONTRACT-ONLY** — endpoint ĐÃ LIVE @`api/imm09.py:126-128`; `git diff` api/imm09.py + services/imm09.py phần `get_asset_repair_history`/`get_asset_history` = TRỐNG ⇒ **KHÔNG `.py`/reload/migrate** ([AUTO] thật, KHÔNG HARD-STOP USER). `getAssetRepairHistory ∈ _MVP_BUSINESS_PATHS` (401/403 symmetry +1), **∉ `_MVP_READ_ENVELOPE`** (SINGLE-shape, KHÔNG oneOf). Path/opId **51→52**. Guard `TestMobileGetAssetRepairHistoryContract` (a..i, 9 TC) ⇒ `_EXPECTED_TEST_COUNT` 483→492. `d12/d15/d17` UNCHANGED (pure mobile-yaml). [ADR-MOBILE-022](./ADR-MOBILE-022.md).

---

### 8.29 FLOW-2 DEVICE-PROFILE — lịch-sử BẢO-TRÌ PM của thiết bị (`getAssetPmHistory`: tab "Lịch sử bảo trì" màn hồ-sơ sau quét QR)

> **Quyết định kiến trúc:** [`ADR-MOBILE-023.md`](./ADR-MOBILE-023.md). 🟦 **ĐÓNG quartet read-history màn hồ-sơ-thiết-bị (flow-2):** `getAssetIncidentHistory` (§8.18 — **sự-cố**) + `getAssetTimeline` (**vòng-đời**) + `getAssetRepairHistory` (§8.28 — **sửa-chữa CM**) ĐÃ có, NHƯNG KTV đứng trước máy còn cần lịch-sử **BẢO-TRÌ ĐỊNH-KỲ (PM)** — "máy này PM lần cuối khi nào, Pass/Fail, có trễ hạn không, lần PM tới?". `getAssetPmHistory` đóng mắt-xích CUỐI: 1 GET-read danh-sách `PM Task Log` (mới→cũ, ≤`limit`) của 1 asset. **MIRROR `getAssetRepairHistory` §8.28 NHƯNG 3 KHÁC-BIỆT có-chủ-đích** (xem ADR-MOBILE-023).

**Endpoint:** `GET /api/method/assetcore.api.imm08.get_asset_pm_history` — opId `getAssetPmHistory`, tag `pm`. **GET** (bare `@frappe.whitelist()` `api/imm08.py:124`). **Cap đọc:** PM read (qua `handle()` → `svc.get_asset_history` permission-aware). Read-only — **KHÔNG audit**. 2 param: **`asset_ref`** (query, required, string, **NO default**) + `limit` (query, optional, integer default 10, minimum 1 — ⚠️ signature `limit: int = 10` **INT**, KHÁC repair `"10"` str; handler ép `int()` `api/imm08.py:126`). KHÔNG `page`/`page_size`. Live-sig parity `inspect.signature(imm08.get_asset_pm_history)=={asset_ref, limit}`.

- **200 = SINGLE `AssetPmHistoryEnvelope`** (KHÔNG `oneOf [Env, Error]`) — handler `api/imm08.py:125` = `handle(svc.get_asset_history)`; `svc.get_asset_history` `services/imm08.py:1012-1021` **0 raise `ServiceError`** ⇒ `handle()` LUÔN `_ok` ⇒ 0 nhánh `_err` trên HTTP-200 (mirror `getAssetRepairHistory` §8.28 / `listTransfers` §8.27, KHÁC `getAssetIncidentHistory` §8.18 `oneOf`). rows-key **`data.history[]`** + asset-key **`data.asset_ref`** — GROUNDED svc `return {"asset_ref": asset_ref, "history": logs}` `:1021`. ⚠️ filter CHỈ `{asset_ref}` — **KHÔNG `docstatus`** (PM Task Log `is_submittable=None`, KHÁC repair `docstatus=1`). KHÔNG pagination (svc chỉ `page_size`=limit cap). `history[]` RỖNG hợp lệ nếu asset chưa từng PM → **KHÔNG 404**.
- **Element `AssetPmHistoryItem`** closed (`additionalProperties:false`) `required [name]` — **EXACT 10 field** (KHÔNG 9) GROUNDED `PMTaskLogRepo.list fields` `services/imm08.py:1015-1017`: `name` (PK) · `pm_work_order` (Link→string) · `pm_type` (Data→string) · `completion_date` (**Date→string, KHÔNG `format:date-time`** — date-trap) · `technician` (Link→string) · **`overall_result` (string `enum [Pass, Pass with Minor Issues, Fail]`** — Select bounded @`pm_task_log.json`, repair có 0 Select-enum) · **`is_late` (integer — Frappe Check 0/1, KHÔNG `boolean`)** · **`days_late` (integer — Int)** · `next_pm_date` (**Date→string, KHÔNG `format:date-time`**) · `summary` (Text→string).
- **Slot `{200,401,403}`** — bare `@whitelist` no-`allow_guest` `api/imm08.py:124` → guest/no-token dispatcher-403; `401 Unauthorized401` (bearer hết hạn) + `403 Forbidden` SINGLE-SHAPE (mirror `getAssetRepairHistory`/`listTransfers`).

> 🔑 **CONTRACT-ONLY** — endpoint ĐÃ LIVE @`api/imm08.py:124-126`; `git diff` api/imm08.py + services/imm08.py phần `get_asset_pm_history`/`get_asset_history` = TRỐNG ⇒ **KHÔNG `.py`/reload/migrate** ([AUTO] thật, KHÔNG HARD-STOP USER). `getAssetPmHistory ∈ _MVP_BUSINESS_PATHS` (401/403 symmetry +1) + `∈ _MVP_SINGLE_LIST_ENVELOPE` (SINGLE-shape, KHÔNG oneOf — c5 == _MVP_BUSINESS_PATHS). Path/opId **52→53**. Guard `TestMobileGetAssetPmHistoryContract` (a..j, 10 TC) ⇒ `_EXPECTED_TEST_COUNT` 492→502. `d12/d15/d17` UNCHANGED (pure mobile-yaml). [ADR-MOBILE-023](./ADR-MOBILE-023.md).

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
  - **[SELF-CORRECTION R34 — 2026-06-27] STALE:** `create_calibration` `api/imm11.py:89` nay = `@frappe.whitelist(methods=["POST"])` (R33 VERB-PARITY CLOSURE); runtime suy verb=**POST**, KHỚP YAML — KHÔNG còn divergence, `_PARITY_VERB_ALLOWLIST`=`set()`. Đoạn trên giữ làm lịch-sử. Verb-parity gap CUỐI (`add_measurement` `api/imm11.py:120`) đóng ở §8.24 (flip-this-round).

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
