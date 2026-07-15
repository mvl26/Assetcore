# ADR-MOBILE-031 — `sendToLab` (**ACTION / CR-CAL-EXT-01 · C8-ACTION forward-reserve** — curate 1 path POST dispatch phiếu hiệu chuẩn NGOẠI KIỂM (External) đi lab vào OAS mirror; **mở nhánh External-calibration** còn thiếu (in-house `submitCalibration`+`addMeasurement` đã curate); **write-ACTION json+form body — KHÁC 3 path multipart trước**; 403 SINGLE `Forbidden` qua `rbac.require` same-shape collapse — KHÔNG dual-403)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-031 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-11 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **§8.6 `createCalibration`** + **§8.15 `submitCalibration`** (**template same-module `rbac.require(cap)` → 403 SINGLE-SHAPE `Forbidden` qua same-shape collapse — KHÔNG dual-403**; write-action json+form body §9 Frappe form_dict) · **ADR-MOBILE-011 §8.24 `addMeasurement`** (họ action IMM-11 tag `calibration`) · Core Doc IMM-11 [`05_API_Specification.md`](../imm-11/05_API_Specification.md) §0.1 mobile-binding + ADR-IMM11-SENDLAB |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source: handler `assetcore/api/imm11.py` `send_to_lab` def@**169-170** (`@frappe.whitelist(methods=["POST"])` @**168** no-`allow_guest`; **signature `send_to_lab(name, sent_date=None, lab_supplier=None, lab_contract_ref=None)`** — CHỈ `name` bắt buộc, 3 param optional default `None`; `rbac.require("cal.send_lab")` @**171**; `handle(svc.send_to_lab, name, sent_date=…, lab_supplier=…, lab_contract_ref=…)` @**172-176**); cap `cal.send_lab` → `("IMM Asset Calibration", "write")` `services/shared/rbac.py:109`; service `assetcore/services/imm11.py` `send_to_lab` def@**1270** (`CalibrationRepo.get`→NOT_FOUND @**1276**, `docstatus==1`→ALREADY_SUBMITTED @**1278**, `calibration_type != "External"`→NOT_EXTERNAL @**1280**, `status ∉ {Scheduled, In Progress}`→SEND_LAB_BAD_STATE @**1282**; patch `status = CalibrationResult.SENT_TO_LAB` @**1285** + `sent_date = sent_date or nowdate()` + `sent_by = session.user`; side-effect asset ACTIVE→CALIBRATING `_transition_asset` + `log_audit_event("Calibration Sent To Lab")`; **`return {"name": name, "status": patch["status"], "sent_date": patch["sent_date"]}` @1304** — EXACT **3-key**); enum `CalibrationResult.SENT_TO_LAB = "Sent to Lab"` `services/shared/constants.py:123`; status Select 8-canonical `imm_asset_calibration.json` (`Scheduled\nSent to Lab\nIn Progress\nCertificate Received\nPassed\nFailed\nConditionally Passed\nCancelled`); msg http_status `utils/messages.py`: IMM11_CAL_NOT_FOUND=**404** @904, IMM11_ALREADY_SUBMITTED=**409** @939, IMM11_NOT_EXTERNAL=**422** @953, IMM11_SEND_LAB_BAD_STATE=**409** @960. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.37 `sendToLab`).

---

## Context

Module Hiệu chuẩn (IMM-11) có **2 nhánh vòng-đời** theo `calibration_type`:
- **In-House** (tự hiệu chuẩn tại chỗ): `createCalibration` → `addMeasurement`×N → `submitCalibration` (verdict). **ĐÃ curate đủ** (§8.6 / §8.24 / §8.15).
- **External / NGOẠI KIỂM** (gửi tổ chức/lab bên ngoài): `createCalibration(type=External)` → **`sendToLab`** → `receiveCertificate` (nhận chứng chỉ) → `submitCalibration` (chốt). Nhánh này **CHƯA có action nào** trên mobile contract → tab Calibration External **cụt** sau khi tạo phiếu.

`sendToLab` là **mắt-xích ĐẦU** của nhánh External — dispatch phiếu đi lab: `Scheduled` **HOẶC** `In Progress` → **`Sent to Lab`**. Endpoint `imm11.send_to_lab` **ĐÃ LIVE** @`api/imm11.py:169` (`@whitelist(methods=["POST"])`, `rbac.require("cal.send_lab")`, `handle(svc.send_to_lab, …)`) + service @`services/imm11.py:1270` (return EXACT 3-key `{name, status, sent_date}` @1304) nhưng **CHƯA có trong OAS mirror** → codegen client mobile không sinh method `sendToLab`.

Vòng này **curate 1 path POST** `send_to_lab` vào `assetcore-mobile.openapi.yaml`, **mở nhánh External-calibration**; đóng CR-CAL-EXT-01. `receiveCertificate` + `cancelCalibration` **forward-reserve** cho vòng kế (§Backlog). **CONTRACT-ONLY**: handler+service đã LIVE @source (uncommitted, phiên BE song song), KHÔNG đụng `.py` vòng này ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

**⚠️ KHÁC-BIỆT vs 3 path trước (multipart CR-17/14/15):** đây là **write-ACTION với json+form body** (KHÔNG phải multipart file-upload). requestBody có **2 media-type** `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict` §9) — **KHÔNG** exempt khỏi sweep `_RPC_FORM_JSON_MEDIA` (KHÁC 3 hằng `_ATTACH_*_BODY_MEDIA_TYPES` multipart-only). Bồi theo template **same-module `submitCalibration` §8.15 / `createCalibration` §8.6** (action-on-existing, `rbac.require` → 403 single-shape), KHÔNG theo template multipart.

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `send_to_lab(name, sent_date=None, lab_supplier=None, lab_contract_ref=None)` — POST-only whitelist, cap-gate, Decision-B oneOf
- `@frappe.whitelist(methods=["POST"])` @168 — **POST-only**, **KHÔNG `allow_guest`** ⇒ guest/no-token → **dispatcher-403** (`PermissionError` HTTP-403 status-line THẬT TRƯỚC handler).
- `rbac.require("cal.send_lab")` @171 — cap-gate **NGAY đầu handler, TRƯỚC `handle()`**. Thiếu cap → `frappe.throw(…, PermissionError)` → **HTTP-403 status-line THẬT** (`FrappeRawError`, `exceptions.py`) — **KHÔNG** qua `handle()`/`_err`/HTTP-200. Cap `cal.send_lab` map `("IMM Asset Calibration","write")` `rbac.py:109`.
- Rồi `handle(svc.send_to_lab, name, sent_date=…, lab_supplier=…, lab_contract_ref=…)` @172-176 ⇒ lỗi nghiệp vụ service (`nthrow` ServiceError) → **Decision-B HTTP-200 + Error envelope** (KHÔNG raise→4xx).
- Service @`imm11.py:1270` `return {"name","status","sent_date"}` @1304 (EXACT **3-key**) → `handle()`/`_ok` → `{"success":true,"data":{name,status,sent_date}}`. ⇒ 200 = **oneOf [`SendToLabResponseEnvelope`, `Error`]** (handler QUA `handle()` + service raise ServiceError ⇒ CÓ nhánh Error — mirror `submitCalibration`/`createCalibration`, KHÁC `listCalibrations`/`listDepartments` single-shape).

### Ladder lỗi nghiệp vụ in-handler (4 nhánh — thứ tự BẮT BUỘC, tất cả qua `handle()` → HTTP-200 + Error)
`exists(doc)` → `docstatus≠1` → `type==External` → `status ∈ {Scheduled, In Progress}` → (patch + asset-transition + audit + commit). `Error.http_status` phủ:

| # | Nhánh @source (`services/imm11.py`) | code (MSG) | http_status |
|---|---|---|---|
| 1 | `CalibrationRepo.get` doc∄ @1276 (`nthrow IMM11_CAL_NOT_FOUND`, name) | NOT_FOUND | **404** (@messages.py:904) |
| 2 | `doc.docstatus == 1` @1278 (`nthrow IMM11_ALREADY_SUBMITTED`) — phiếu ĐÃ chốt | CONFLICT | **409** (@messages.py:939) |
| 3 | `(doc.calibration_type or "") != "External"` @1280 (`nthrow IMM11_NOT_EXTERNAL`) — chỉ External gửi lab | VALIDATION | **422** (@messages.py:953) |
| 4 | `doc.status ∉ {Scheduled, In Progress}` @1282 (`nthrow IMM11_SEND_LAB_BAD_STATE`, state) | CONFLICT | **409** (@messages.py:960) |

⇒ `Error.http_status` ⊇ **{404, 409, 422}** (4 nhánh, tất cả ARRIVE HTTP-200 body qua `handle()` — route theo `body.http_status`, KHÔNG status-line). **KHÁC 3 path multipart:** ladder KHÔNG có nhánh file/size/corrupt (đây action state-machine, KHÔNG upload).

### 2 loại 403 (mobile-BE contract gotcha) — quyết định 403-slot ⇒ SINGLE-SHAPE
- **cap-403** = đã đăng nhập nhưng thiếu cap `cal.send_lab` → `rbac.require("cal.send_lab")` @171 → `frappe.throw(PermissionError)` → **HTTP-403 status-line THẬT** + `FrappeRawError` shape (**KHÔNG** qua `handle()` — raise TRƯỚC `handle()`).
- **dispatcher-403** = guest/no-token (POST `@whitelist` no `allow_guest`) → Frappe dispatcher raise `PermissionError` → **HTTP-403 status-line THẬT** + `FrappeRawError` shape.
- ⇒ **CẢ HAI CÙNG SHAPE** (`FrappeRawError` @ HTTP-403 status-line) ⇒ collapse thành **1 component `Forbidden` SINGLE-SHAPE**. 403-slot chỉ giữ `Forbidden`. Mirror `createCalibration` §8.6 / `submitCalibration` §8.15 (same-module `rbac.require`), **KHÁC `reportIncident` DUAL-403**. Xem **§Self-Correction** (rationale) + Alternatives B.

### Side-effect success (lifecycle External-cal) — contract KHÔNG khai (thuộc service)
`CalibrationRepo.update_fields(name, {status: "Sent to Lab", sent_date: sent_date or nowdate(), sent_by: session.user, [lab_supplier], [lab_contract_ref]})` @1284-1296 → nếu `asset.lifecycle_status == ACTIVE` thì `_transition_asset(asset, CALIBRATING, name, reason="Sent to lab — …")` @1298-1301 → `log_audit_event(event_type="Calibration Sent To Lab", …)` @1302-1303 → return. Contract này CHỈ khai request/response shape (KHÔNG khai side-effect).

## Decision

**Curate 1 path POST GROUNDED 1:1 `imm11.send_to_lab`, requestBody 2 media-type (json + x-www-form-urlencoded) cùng `$ref SendToLabRequest`, 200 = oneOf [`SendToLabResponseEnvelope`, `Error`] (Decision-B route-by-VALUE 0-discriminator), 403 = SINGLE-SHAPE `Forbidden`, slot `{200,401,403}`.** Tag **`calibration`**. Path-count **62→63**, opId **62→63** (đếm thật, DUY NHẤT, camelCase). CONTRACT-ONLY (pure-yaml).

1. **`sendToLab`** — `POST /api/method/assetcore.api.imm11.send_to_lab` › `operationId: sendToLab` (dotted-path tail §8.1, camelCase, UNIQUE). Tag **`calibration`** (grounded: họ action IMM-11 `submitCalibration`/`addMeasurement`/`createCalibration` đều tag `calibration`). **POST-only** (`@whitelist(methods=["POST"])` @168 — clean POST, KHÔNG verb-divergence, ∉ `_PARITY_VERB_ALLOWLIST`); live-sig parity `inspect.signature(imm11.send_to_lab) == {name, sent_date, lab_supplier, lab_contract_ref}`. 200 = `oneOf [SendToLabResponseEnvelope, Error]`. slot `{200,401,403}`.

2. **requestBody = 2 media-type** (`required: true`; **`application/json` + `application/x-www-form-urlencoded`** — CÙNG `$ref SendToLabRequest`; Frappe RPC `form_dict` §9, mirror `CreateCalibrationBody`). Inline path-level content (2 media-type, mỗi cái `schema.$ref SendToLabRequest`) — `required:true` là sibling `content` (KHÔNG sibling `$ref` ⇒ KHÔNG chạm G-OAS-403-DISAMBIG). **KHÁC 3 path multipart** (multipart-only) — path này là RPC-form chuẩn ⇒ **KHÔNG** hằng exempt media-type.

3. **`SendToLabRequest`** — CLOSED (`additionalProperties: false`), `required: [name]` (**chỉ 1 bắt buộc** — KHỚP HỆT signature @169-170: `name` positional, 3 param còn lại default `None`):

   | prop | type | ground |
   |---|---|---|
   | `name` | string | name **IMM Asset Calibration** (phiếu External đang mở). **required** |
   | `sent_date` | string, nullable | ngày gửi lab; absent/`null` ⇒ service default `nowdate()` @1285. **optional** |
   | `lab_supplier` | string, nullable | NCC/lab nhận (Link Supplier `AC-SUP-…`, mô hình hoá `string`); absent ⇒ KHÔNG patch @1289-1290. **optional** |
   | `lab_contract_ref` | string, nullable | tham chiếu hợp đồng/PO gửi lab (free-text); absent ⇒ KHÔNG patch @1291-1292. **optional** |

   *(KHÔNG thêm/bớt prop — 4 prop khớp HỆT 4 param signature; 3 optional `nullable` phản-ánh default `None`. KHÔNG `enum` field nào — 3 optional là free string; `sent_date` để `string` nullable, KHÔNG `format:date` bắt buộc — client có thể gửi date-string, BE optional `format:date` nếu generator target đòi.)*

4. **`SendToLabResponse`** (data) — CLOSED (`additionalProperties: false`), `required: [name, status, sent_date]` EXACT **3 prop** (GROUNDED `return {"name","status","sent_date"}` @1304):

   | prop | type | ground |
   |---|---|---|
   | `name` | string | echo name phiếu (`name` @1304) |
   | `status` | string, **enum** = Select 8-canonical `[Scheduled, Sent to Lab, In Progress, Certificate Received, Passed, Failed, Conditionally Passed, Cancelled]` | `patch["status"]` @1304 = `CalibrationResult.SENT_TO_LAB` @1285. **Giá-trị trả LUÔN `"Sent to Lab"`** — nhưng enum khai ĐỦ 8-canonical (Select 1:1 `imm_asset_calibration.json`) để codegen sinh đúng máy-trạng-thái (mirror `submitCalibration`/`createCalibration` status enum) |
   | `sent_date` | string (date) | `patch["sent_date"]` @1304 = `sent_date or nowdate()` @1285 — LUÔN có giá-trị (resolved) |

5. **`SendToLabResponseEnvelope`** — CLOSED (`additionalProperties: false`), `required: [success, data]`; `success.enum: [true]`; **`data` = `$ref SendToLabResponse`** (object nested, KHÔNG array). Nhánh success của 200-oneOf; disjoint required-set với `Error` (`req[success,data]` vs `Error req[success,error,code,http_status]`) ⇒ máy-đọc phân-biệt bằng CLOSED-SCHEMA (KHÔNG discriminator — `success` boolean, §5c).

6. **200 = `oneOf [SendToLabResponseEnvelope, Error]`** — Decision-B route-by-VALUE (`body.success` enum[true] vs [false] + `body.http_status`), 0 discriminator. Nhánh `Error` gom **4 nhánh** service (404/409/422/409) ARRIVE HTTP-200. Mirror `submitCalibration` 200-oneOf.

7. **403 = SINGLE-SHAPE `Forbidden`** (`$ref #/components/responses/Forbidden`, `FrappeRawError`). **CẢ cap-403 (`rbac.require("cal.send_lab")` @171) LẪN dispatcher-403 (guest) đều là raw `PermissionError` @ HTTP-403 status-line = CÙNG SHAPE** ⇒ 1 component. Mirror `createCalibration`/`submitCalibration` (same-module rbac.require). **401 = `Unauthorized401`** (bearer hết-hạn/invalid → HTTP-401 THẬT).

### Self-Correction (rationale 403 — grounded, sửa chữ acceptance)

> **Acceptance ghi:** "cap-403 (cal.send_lab) + 4-nhánh error ladder service ... **đã phủ bởi nhánh Error của 200-oneOf** ⇒ KHÔNG dual-403 (mirror ADR-027 acknowledgeIncident)".
>
> **Sửa (VERIFY @source):** KẾT-LUẬN (403 SINGLE-SHAPE, KHÔNG dual-403) **ĐÚNG**, nhưng **RATIONALE gộp cap-403 vào "200-oneOf Error branch" SAI @source**:
> - **cap-403 KHÔNG đi qua 200-oneOf.** `send_to_lab` gọi `rbac.require("cal.send_lab")` @171 **TRƯỚC** `handle()` @172 → `frappe.throw(PermissionError)` → **HTTP-403 status-line THẬT** (`FrappeRawError`). Nó **KHÔNG** chạm `_err`/HTTP-200. Đây là cùng cơ-chế `createCalibration` (`rbac.require('calibration.create')` §8.6) + `submitCalibration` (`rbac.require('calibration.submit')` §8.15). Lý do 403 SINGLE = **cap-403 CÙNG SHAPE dispatcher-403** (cả 2 `FrappeRawError` @ status-line) → collapse 1 component — KHÔNG phải "cap-403 nằm trong Error branch".
> - Cơ-chế "cap-403 phủ bởi 200-oneOf Error" là của **`acknowledgeIncident`/attach-photo** (dùng `_err(403)` @ HTTP-200, cap-403 = Error body) — **KHÁC** `send_to_lab` (dùng `rbac.require` → raw-403). Mirror same-mechanism ĐÚNG = **`createCalibration` §8.6 / `submitCalibration` §8.15** (same-module), KHÔNG phải acknowledgeIncident.
> - Cái **THẬT** được nhánh Error 200-oneOf phủ = **4 nhánh service** (NOT_FOUND 404 @1276 / ALREADY_SUBMITTED 409 @1278 / NOT_EXTERNAL 422 @1280 / SEND_LAB_BAD_STATE 409 @1282) — KHÔNG có 403 trong đó. ⇒ Bảng ladder trên phủ {404,409,422}, KHÔNG {403}.

**Naming guard (∅):** `SendToLab{Request,Response,ResponseEnvelope}` ∩ mọi schema hiện có == ∅ (grep verify 0 collision) — KHÔNG đụng `SubmitCalibration*` / `CreateCalibration*` / `AddMeasurement*` (cùng module, op khác) LẪN `Attach*Photo*`. Schema RIÊNG (KHÔNG reuse `SubmitCalibrationResponse` 4-prop — khác shape 3 vs 4 prop; KHÔNG reuse `CreateCalibrationResponse` 2-prop).

**Tag `calibration` (grounded):** họ action IMM-11 trên applied-yaml đều tag `calibration` (`submitCalibration` §8.15 / `addMeasurement` §8.24 / `createCalibration` §8.6) ⇒ `sendToLab` = **`calibration`** (đối xứng module — KHÁC imm09/imm08 dùng `work-order`).

**Phạm vi membership-set (test_mobile_oas):** path ∈ `_MVP_BUSINESS_PATHS` (→ 401/403 symmetry auto +1) · ∈ `_MVP_ACTION_ENVELOPE` (POST-action-on-existing oneOf [<ActionEnvelope>, Error]; `name` = khoá phiếu ĐÃ tồn tại, mirror `submitCalibration`; envelope RIÊNG) · **∉ `_MVP_CREATE_ENVELOPE`** (action trên phiếu có sẵn, KHÔNG create top-level doc) · **∉ `_MVP_SINGLE_LIST_ENVELOPE`/`_MVP_LIST_ENVELOPE`/`_MVP_READ_ENVELOPE`** · **c5 envelope-map += `sendToLab → SendToLabResponseEnvelope`** (`51→52`, giữ invariant `c5 == _MVP_BUSINESS_PATHS`) · ∈ `_RATE_LIMIT_SOURCE_MAP` (KHÔNG `@rate_limit` @168 ⇒ VẮNG khỏi `_PATHS_REQUIRE_429`, chống bịa 429) · **POST-only-at-source ∉ `_PARITY_VERB_ALLOWLIST`** · **⚠️ ∈ `_REQBODY_PATHS`** (có requestBody json+form — **KHÁC** 3 path multipart trước ∉ `_REQBODY_PATHS`) · **KHÔNG hằng exempt media-type**: path RPC-form chuẩn PHẢI khai CẢ `application/json` + `application/x-www-form-urlencoded` (subject sweep `_RPC_FORM_JSON_MEDIA`, KHÁC 3 hằng `_ATTACH_*_BODY_MEDIA_TYPES` multipart-only) · `_EXPECTED_PATH_OPID` += dotted-path entry. **CONTRACT-ONLY**: `git diff -U0 api/imm11.py` + `services/imm11.py` vùng `send_to_lab` = **KHÔNG có hunk MỚI vòng này** (handler+service ĐÃ trên đĩa từ phiên BE song song) ⇒ KHÔNG reload gunicorn, KHÔNG migrate — là **[AUTO]**, KHÔNG HARD-STOP USER. 62 path hiện-hữu byte-identical; `test_oas_d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | requestBody `multipart/form-data` (copy 3 path trước) | SAI transport: `send_to_lab` đọc `form_dict` (json/form-urlencoded), KHÔNG `frappe.request.files`. Đây action state-machine KHÔNG upload file. Multipart ⇒ codegen sinh sai body shape. RPC-form json+form ĐÚNG (mirror `createCalibration`). |
| B | 403 = DUAL-SHAPE `SendToLabForbidden` (oneOf Error\|FrappeRawError, mirror `reportIncident`) | SAI @source: cap-403 đến từ `rbac.require("cal.send_lab")` @171 = `frappe.throw(PermissionError)` @ HTTP-403 status-line (`FrappeRawError`), **CÙNG SHAPE** dispatcher-403 — KHÔNG phải `_err(403)` @ HTTP-200. Dual-403 = 2 shape khác nhau; ở đây 1 shape ⇒ SINGLE `Forbidden`. (reportIncident dual VÌ dùng `rbac.can + _err(403)` → cap-403 = Error body @200 khác dispatcher raw-403.) |
| C | 200 = SINGLE `SendToLabResponseEnvelope` (mirror `listCalibrations` single-shape) | SAI error-mode: handler QUA `handle(svc.send_to_lab)` + service **4 nhánh raise ServiceError** (404/409/422/409) ⇒ HTTP-200 CÓ nhánh Error. SINGLE-shape bỏ Error = codegen KHÔNG deser được lỗi (phiếu∄/đã-chốt/không-External/sai-state) → client crash/nuốt lỗi. `oneOf [Env, Error]` ĐÚNG (mirror `submitCalibration`). |
| D | `SendToLabResponse` = reuse `SubmitCalibrationResponse` (4-prop) hoặc `CreateCalibrationResponse` (2-prop) | SAI shape: service `return {"name","status","sent_date"}` @1304 = **3-key**. reuse 4-prop → thiếu key `additionalProperties:false` validate-FAIL (`overall_result`/`next_calibration_date` KHÔNG trả); reuse 2-prop → dư `sent_date` validate-FAIL. Schema RIÊNG `SendToLabResponse` 3-prop ĐÚNG. |
| E | `status` type `string` KHÔNG enum (mirror `submitCalibration` §8.15 khai `string`) | Chấp-nhận-được nhưng LOẠI theo acceptance: acceptance chốt `enum = CalibrationResult canonical`. Enum 8-canonical (mirror `createCalibration` §8.6h + `CalibrationListItem`) → codegen sinh state-machine type-safe. Giá-trị runtime LUÔN `"Sent to Lab"` nhưng khai đủ 8 (né drift + đối xứng module). |
| F | `SendToLabRequest.required = [name, sent_date]` (coi sent_date bắt buộc) | SAI signature: `sent_date` default `None` @169 (optional) — service tự default `nowdate()` @1285 khi absent. required chỉ `[name]` (1 param positional). Thêm required = form mobile ép nhập ngày thừa. |
| G | thêm hằng exempt `_SEND_TO_LAB_BODY_MEDIA_TYPES` (copy pattern multipart) | SAI: path này KHÔNG multipart — là RPC-form chuẩn PHẢI qua sweep `_RPC_FORM_JSON_MEDIA` (json+form). Thêm hằng exempt = miễn sweep sai → path có thể thiếu 1 media-type mà guard KHÔNG bắt. KHÔNG hằng exempt. |
| H | curate luôn `receiveCertificate` + `cancelCalibration` cùng vòng | Vượt scope CR-CAL-EXT-01 (1 path/vòng, blast-radius nhỏ + naming-guard rõ). `receiveCertificate` (Sent to Lab → In Progress, 5-param, return `{name,status,certificate_number}`) + `cancelCalibration` = **forward-reserve** vòng kế (grep return-key @service TRƯỚC đặc tả). |
| ✅ I | 1 path POST json+form body, 3 schema RIÊNG (Response 3-prop), 200 oneOf [Env, Error], 403 SINGLE `Forbidden` (rbac.require same-shape), `_MVP_ACTION_ENVELOPE` + `_REQBODY_PATHS`, tag `calibration` | Grounded 1:1 source; blast-radius = +1 path +3 schema (PURE-YAML); codegen sinh 1 method dispatch-lab type-safe + response 3-prop → app gửi phiếu External đi lab; Decision-B intact; 403-slot sạch (same-shape collapse); naming-guard ∅; mở nhánh External, đóng CR-CAL-EXT-01. |

## Consequences

- **(+)** App mobile tab Calibration External có method `sendToLab` codegen-ready: KTV mở phiếu External `Scheduled`/`In Progress` → bấm "Gửi lab" (chọn NCC/lab + ngày gửi tuỳ chọn) → phiếu → `Sent to Lab` + asset ACTIVE→CALIBRATING + audit `Calibration Sent To Lab`. **Mở nhánh External-calibration** (mắt-xích ĐẦU). **CR-CAL-EXT-01 ĐÓNG.**
- **(+)** Contract GROUNDED 1:1 source — 3 schema RIÊNG VERBATIM (`SendToLabRequest` `req[name]` 4-prop khớp signature @169-170; `SendToLabResponse` EXACT **3-prop** `{name,status,sent_date}` @1304; ladder `Error.http_status` ⊇ {404,409,422} khớp 4 nhánh @1276-1282); 403-slot SINGLE `Forbidden` (rbac.require same-shape). **Naming guard:** `SendToLab*` ∩ mọi schema == ∅ (grep 0).
- **(+)** **Write-ACTION json+form** (KHÁC 3 path multipart trước) — chứng minh template `submitCalibration`/`createCalibration` (rbac.require single-403 + json+form body §9) tái-dùng đúng cho action-on-existing. **∈ `_REQBODY_PATHS`** + subject sweep `_RPC_FORM_JSON_MEDIA` (KHÔNG exempt).
- **(+)** **Self-Correction rationale 403** (grounded) — sửa chữ acceptance "cap-403 phủ bởi 200-oneOf"/"mirror acknowledgeIncident": cap-403 qua `rbac.require` = raw-403 same-shape dispatcher (mirror same-module `createCalibration`/`submitCalibration`), KHÔNG qua 200-oneOf. Kết-luận (403 SINGLE) không đổi; rationale chuẩn-hoá theo source (P-DOC-2).
- **(+)** **CONTRACT-ONLY** — vòng này KHÔNG thêm hunk `.py` mới vùng `send_to_lab` (handler+service ĐÃ trên đĩa LIVE từ phiên BE song song) ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO], KHÔNG HARD-STOP USER); `test_oas_d12/d15/d17` UNCHANGED (pure mobile-yaml). 62 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator; 2 nhánh oneOf disjoint required-set closed-schema); 0 dangling `$ref` (3 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`/`Error`).
- **(−)** **Response 3-prop RIÊNG** (KHÔNG reuse `SubmitCalibration`/`CreateCalibrationResponse`) — 3 op cùng module có 3 response-shape khác (create 2-prop / send-lab 3-prop / submit 4-prop). Người bồi action IMM-11 tiếp PHẢI grep `return {…}` @service TRƯỚC khi khai. Ground bằng SOURCE, KHÔNG copy schema anh-em.
- **(−)** `status` enum khai 8-canonical dù runtime LUÔN `"Sent to Lab"` — chủ đích (né drift + đối xứng module + codegen state-machine). Guard TC assert enum == 8-canonical (KHÔNG ép `[Sent to Lab]` đơn-trị).
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `571→581` (test_mobile_oas, +10 TC class `TestMobileSendToLabContract` a..j) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `571→581` + `_GUARD_SUITE_SUM` `714→724` + `_MOBILE_OAS_TOTAL` `740→750` (= `_GUARD_SUITE_SUM` 724 + preflight 26) + c5 `51→52` + ADR balance `30→31` (README ADR-row bắt-buộc — TC-MOB-DOC-02). ⚠️ **Số baseline (571/62/51/714/740) grounded @source 2026-07-11 SAU CR-15 (ADR-030); BE PHẢI grep-verify lại @source TRƯỚC bump** (đa-phiên race có thể dịch baseline). *(N=10 = khuyến nghị BA; BE tinh-chỉnh granularity TC miễn 3 counter di-chuyển ĐỒNG +N.)*

---

## Handoff BE/Test (Bước-4 — kế-hoạch, ATOMIC pure-yaml)

> **CONTRACT-ONLY** — TUYỆT ĐỐI KHÔNG đụng `api/imm11.py`/`services/imm11.py` (`send_to_lab` @169/@1270 ĐÃ LIVE trên đĩa). Không reload/migrate/commit. **BE grep-verify baseline @source TRƯỚC bump** (571/62/51/714/740 = grounded 2026-07-11 sau ADR-030; nếu phiên khác đã dịch → tính lại delta +1 path / +10 test / +1 c5 / +10 suite-sum / +10 oas-total). DoD: `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_mobile_oas` = **'Ran N OK' THẬT** (N=count mới) · `.test_mobile_docset` = **Ran 9 OK** · `test_mobile_security_gate` GREEN · `test_oas_d12/d15/d17` UNCHANGED (đọc dòng cuối, KHÔNG false-green).

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`):
- +1 path `POST /api/method/assetcore.api.imm11.send_to_lab` (opId `sendToLab`, **tag `calibration`**); requestBody `required:true` content **2 media-type** `application/json` + `application/x-www-form-urlencoded` (CÙNG `schema.$ref SendToLabRequest`); 200 = `oneOf [SendToLabResponseEnvelope, Error]`; slot `{200,401,403}` (`401 Unauthorized401`, **`403 Forbidden` SINGLE-SHAPE** — KHÔNG dual-403).
- +3 schema (`SendToLabRequest` closed `req[name]` — `name:{type:string}` · `sent_date:{type:string,nullable:true}` · `lab_supplier:{type:string,nullable:true}` · `lab_contract_ref:{type:string,nullable:true}` · `SendToLabResponse` closed EXACT `req[name,status,sent_date]` — `name:{type:string}` · `status:{type:string,enum:[Scheduled,Sent to Lab,In Progress,Certificate Received,Passed,Failed,Conditionally Passed,Cancelled]}` · `sent_date:{type:string}` · `SendToLabResponseEnvelope` closed `req[success,data]` `success.enum[true]` `data=$ref SendToLabResponse`). Cả 3 `additionalProperties:false`. Tái-dùng `Unauthorized401`/`Forbidden`/`Error`. 0 orphan, 0 dangling. **KHÔNG đụng `SubmitCalibration*`/`CreateCalibration*`/`AddMeasurement*`/`Attach*Photo*`** (naming guard).

**(2) test_mobile_oas.py** (grep-verify baseline TRƯỚC): path/opId count `62→63`; `_EXPECTED_PATH_OPID` += `("/api/method/assetcore.api.imm11.send_to_lab": ("post","sendToLab"))`; path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_ACTION_ENVELOPE` + **∈ `_REQBODY_PATHS`** (json+form); c5 map += `sendToLab→SendToLabResponseEnvelope` (`51→52`); `_RATE_LIMIT_SOURCE_MAP` += (no-rate-limit); **KHÔNG hằng exempt media-type** (path RPC-form chuẩn — subject `_RPC_FORM_JSON_MEDIA`); +1 TC class `TestMobileSendToLabContract` (a..j, 10 TC — xem dưới); `_EXPECTED_TEST_COUNT` `571→581`.
- **TC a..j (khuyến nghị):** a) yaml path-count==63 ∧ opId-count==63. b) path POST-only + opId `sendToLab` + **tag `calibration`** + ∈ `_MVP_BUSINESS_PATHS`. c) requestBody `required:true` + content keys == **{`application/json`, `application/x-www-form-urlencoded`}** (2 media-type, CÙNG `$ref SendToLabRequest`; **NOT multipart** — anti-drift vs 3 path trước) + **∈ `_REQBODY_PATHS`** + subject `_RPC_FORM_JSON_MEDIA`. d) `SendToLabRequest` closed `additionalProperties:false` + `required==[name]` (**chỉ 1**) + `name.type==string` ∧ `sent_date`/`lab_supplier`/`lab_contract_ref` `type:string` `nullable:true` (4 prop EXACT — KHÔNG thêm/bớt, khớp signature). e) 200 = `oneOf [SendToLabResponseEnvelope, Error]` (EXACT 2 nhánh, KHÔNG discriminator; disjoint required-set). f) `SendToLabResponseEnvelope` closed `req[success,data]` `success.enum==[true]` `data.$ref==…SendToLabResponse` (object nested, KHÔNG array). g) `SendToLabResponse` closed `additionalProperties:false` EXACT **3 prop** `required==[name,status,sent_date]` — `name`/`sent_date` `type:string` ∧ `status.type==string` ∧ **`status.enum` == 8-canonical Select** (`[Scheduled,Sent to Lab,In Progress,Certificate Received,Passed,Failed,Conditionally Passed,Cancelled]` — anti-drift: KHÁC SubmitCalibrationResponse 4-prop / CreateCalibrationResponse 2-prop). h) slot `{200,401,403}`: `401 Unauthorized401` + **`403 Forbidden` SINGLE-SHAPE** (`$ref Forbidden`, KHÔNG dual) — anti-dual-403. i) membership + 401/403 symmetry + `_MVP_ACTION_ENVELOPE` + c5==_MVP_BUSINESS_PATHS + POST-only ∉ `_PARITY_VERB_ALLOWLIST` + no-`@rate_limit` (∉ `_PATHS_REQUIRE_429`) + no-dangling + **naming guard `SendToLab*` ∩ (`SubmitCalibration*` ∪ `CreateCalibration*` ∪ `AddMeasurement*`) == ∅**. j) CONTRACT-ONLY — `git diff` `api/imm11.py`+`services/imm11.py` vùng `send_to_lab` KHÔNG hunk MỚI vòng này (pure-yaml, handler+service untouched) — anti-false-green (registry-resolvability KHÔNG HEAD-diff); live-sig parity `inspect.signature(imm11.send_to_lab)=={name,sent_date,lab_supplier,lab_contract_ref}`.
- **⚠️ Media-type sweep**: path này **KHÔNG exempt** khỏi `_RPC_FORM_JSON_MEDIA` (RPC-form chuẩn — PHẢI có CẢ json+form). Nếu vô ý thêm vào exempt-set (như 3 hằng multipart) → sweep bỏ-sót path → RED âm-thầm khi thiếu 1 media-type.

**(3) test_mobile_docset.py** (grep-verify baseline TRƯỚC): `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `571→581` · `_GUARD_SUITE_SUM` `714→724` · `_MOBILE_OAS_TOTAL` `740→750` (=724+26) + transition-baseline delta-var `send_to_lab_action_delta=10` (nếu suite có transition-baseline). ADR-MOBILE-031 registered README (TC-MOB-DOC-02 glob động — README row bắt-buộc, ĐÃ thêm ở Bước-2 BA; balance ADR-on-disk 31 == README-index 31).

**(4) docs narrative** (ĐÃ XONG Bước-2 BA): `04-api-contract.md` (§8.37 `sendToLab`) + README ADR-row (ADR-MOBILE-031, balance 30→31) + Core Doc [`05_API_Specification.md`](../imm-11/05_API_Specification.md) §0.1 mobile-binding `sendToLab` + ADR-IMM11-SENDLAB + Self-Correction (rationale 403).

**BACKLOG (nhánh External-calibration — vòng kế):** `receiveCertificate` (Sent to Lab → In Progress; handler @`imm11.py:179`, 5-param `name`+`certificate_file`+`certificate_number`+`certificate_date`+2 optional; service @`imm11.py:1308`, return `{name,status,certificate_number}` — grep-verify TRƯỚC đặc tả) + `cancelCalibration` (handler @`imm11.py:196`, `rbac.require("calibration.cancel")`, 2-param `name`+`reason`). Đặc tả từng path 1 vòng — grep return-key @service + đếm ladder TRƯỚC.
