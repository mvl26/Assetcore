# ADR-MOBILE-027 — `attachIncidentPhoto` (**MULTIPART / CR-17 · G6** — curate 1 path POST đính ảnh bằng chứng hiện trường (NĐ98) vào Phiếu sự cố F2; **path `multipart/form-data` ĐẦU TIÊN của mirror**, nền cho CR-14/CR-15 ảnh checklist PM/CM)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-027 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-11 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **ADR-MOBILE-006** (`acknowledgeIncident` — POST-action route-by-VALUE, **403 SINGLE-SHAPE `Forbidden`** khi in-handler cap-403 đã phủ bởi nhánh Error 200-oneOf; KHÁC `reportIncident` dual-403) · Core Doc IMM-12 [`05_API_Specification.md`](../imm-12/05_API_Specification.md) §15 `attach_incident_photo` + ADR-IMM12-06 (File private + derive `scene_photos`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source: handler `assetcore/api/imm12.py` `attach_incident_photo` def@**273** (guest `_err` 401 @288, `handle(svc_attach_photo, …)` @298); service `assetcore/services/imm12.py` `attach_incident_photo` def@**995** (`_get_incident`→NOT_FOUND @1018, `_assert_can_attach_photo`→FORBIDDEN @1019/987, ladder VALIDATION @1020-1028, corrupt-guard `UnidentifiedImageError|OSError`→422 @1040-1051, `return {file_url, file_name}` @1064); hằng `MAX_INCIDENT_PHOTOS = 5` @47, `MAX_INCIDENT_PHOTO_BYTES = 10*1024*1024` @48, `_INCIDENT_PHOTO_CONTENT_TYPES = ("image/jpeg","image/jpg","image/png")` @49; msg @55-62. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.33 `attachIncidentPhoto`).

---

## Context

Field-tech mobile màn **Chi tiết sự cố** (F2 `IncidentDetailView`) cần **đính ảnh bằng chứng hiện trường** (thiết bị hỏng, hiện trạng phòng máy) trực-tiếp vào Phiếu sự cố làm **bằng chứng NĐ98** (evidence trail điều tra sự cố TTBYT). Endpoint `imm12.attach_incident_photo` **ĐÃ LIVE** @`api/imm12.py:273` (single-step multipart: server đọc `frappe.request.files["file"]`, tự validate + tạo `File` private + link, robust KHÔNG orphan như 2-bước `upload→file_url`) nhưng **CHƯA có trong OAS mirror** → codegen client mobile không sinh được method `attachIncidentPhoto` → app phải hardcode URL + tự build multipart body. Đây là **CR-17/G6** (mobile Trục B), và là endpoint **write-path multipart ĐẦU TIÊN** của cả mirror.

Vòng này **curate 1 path POST** `attach_incident_photo` vào `assetcore-mobile.openapi.yaml` với requestBody **`multipart/form-data` DUY NHẤT** (path multipart đầu tiên) → codegen sinh method upload type-safe. **CONTRACT-ONLY**: `attach_incident_photo` ĐÃ LIVE @source (handler+service+hằng nguyên trên đĩa, thêm ở vòng trước cùng branch uncommitted), KHÔNG đụng `.py` vòng này ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

Đây cũng là **template cho CR-14/CR-15** (ảnh checklist PM `imm08`/CM `imm09`) — mọi write-path multipart kế bồi theo shape media-type + oneOf + ladder của path này.

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `attach_incident_photo(incident_name="", **_ignore)` — POST-only whitelist, multipart, Decision-B oneOf
- `@frappe.whitelist(methods=["POST"])` @`imm12.py:273` — **POST-only** (KHÔNG GET), **KHÔNG `allow_guest`** ⇒ guest/no-token → **dispatcher-403** (`PermissionError` HTTP-403 status-line THẬT TRƯỚC handler). `**_ignore` nuốt kwargs spoof (đối xứng `register_device_token`).
- Guest-guard in-handler @`imm12.py:286-287`: `if session.user == "Guest": return _err(_MSG_UNAUTHENTICATED, 401)` — **401** (defensive; thực tế dispatcher chặn guest-no-token bằng 403 TRƯỚC; slot 401 map bearer hết-hạn/invalid).
- Handler đọc `frappe.request.files["file"]` @288-297 (bytes/filename/content_type; `None` khi thiếu → service raise VALIDATION) rồi `handle(svc_attach_photo, incident_name, filedata=…, filename=…, content_type=…)` @298 ⇒ lỗi nghiệp vụ ServiceError → **Decision-B HTTP-200 + Error envelope** (KHÔNG raise→4xx).
- Service `attach_incident_photo` @`imm12.py:995` `return {"file_url", "file_name"}` @1064 (EXACT 2-key) → `handle()`/`_ok` → `{"success":true,"data":{file_url,file_name}}`. ⇒ 200 = **oneOf [`AttachIncidentPhotoEnvelope`, `Error`]** (handler QUA `handle()` + service raise ServiceError ⇒ CÓ nhánh Error — KHÁC `listLocations`/`listDepartments` single-shape).

### Ladder lỗi in-handler (thứ tự BẮT BUỘC — mọi nhánh reject TRƯỚC `File.insert`)
`exists(incident)` → `permission` → `file present` → `content-type` → `size` → `max-count` → (`File.insert` → `corrupt-guard`) → `lifecycle event` → `commit`. `Error.http_status` phủ:

| # | Nhánh @source | code | http_status | fields.file |
|---|---|---|---|---|
| 1 | `_get_incident` incident∄ @1018 (`nthrow` IMM12_INCIDENT_NOT_FOUND) | NOT_FOUND | **404** | — |
| 2 | `_assert_can_attach_photo` KHÔNG reporter ∧ KHÔNG `incident.write` @1019/987 | FORBIDDEN | **403** (in-handler cap-403) | — |
| 3 | thiếu `file` @1020 (`_MSG_PHOTO_MISSING`) | VALIDATION | **422** | "Thiếu tệp ảnh" |
| 4 | content-type ∉ `_INCIDENT_PHOTO_CONTENT_TYPES` @1023 (`_MSG_PHOTO_NOT_IMAGE`) | VALIDATION | **422** | "Tệp phải là ảnh JPG hoặc PNG" |
| 5 | `len(filedata) > MAX_INCIDENT_PHOTO_BYTES` @1025 (`_MSG_PHOTO_TOO_LARGE`) | VALIDATION | **422** | "Ảnh vượt quá dung lượng cho phép (tối đa 10 MB)" |
| 6 | `len(_scene_photos) >= MAX_INCIDENT_PHOTOS` @1027 (`_MSG_PHOTO_MAX`) | VALIDATION | **422** | "Tối đa 5 ảnh" |
| 7 | ảnh hỏng/đứt-truyền `UnidentifiedImageError\|OSError` @1040-1051 (`_MSG_PHOTO_CORRUPT`) | VALIDATION | **422** | "Tệp ảnh bị lỗi hoặc không đọc được, vui lòng chụp/chọn lại." |

⇒ `Error.http_status` ⊇ **{403, 404, 422}** (7 nhánh, tất cả ARRIVE HTTP-200 body qua `handle()` — route theo `body.http_status`, KHÔNG status-line). Content-type allowlist = **3 giá trị** `image/jpeg`/`image/jpg`/`image/png` (VERIFIED @49 — KHÔNG 2 như doc cũ ghi nhầm).

### 2 loại 403 (mobile-BE contract gotcha) — quyết định 403-slot
- **in-handler cap-403** (nhánh #2 trên) = đã đăng nhập nhưng ngoài quyền → ServiceError(FORBIDDEN, http_status=403) qua `handle()` → **HTTP-200 + Error envelope** ⇒ ĐÃ nằm trong nhánh `Error` của 200-oneOf (route-by `body.http_status=403`).
- **dispatcher-403** = guest/no-token (POST `@whitelist` no `allow_guest`) → Frappe dispatcher raise `PermissionError` → **HTTP-403 status-line THẬT** + `FrappeRawError` shape.
- ⇒ 403-slot chỉ giữ **dispatcher-403 SINGLE-SHAPE `Forbidden`** (in-handler cap-403 đã phủ bởi 200-Error, KHÔNG lặp) — mirror `acknowledgeIncident` (ADR-MOBILE-006), **KHÁC `reportIncident` DUAL-403** (`ReportIncidentForbidden` oneOf Error|FrappeRawError). Xem Decision + Alternatives B.

### Side-effect success (BR-12-17/18, ADR-IMM12-06/07)
`File.insert(is_private=1)` @1031-1039 (NĐ98 — ảnh KHÔNG public) → `create_lifecycle_event(incident_photo_attached)` @1055-1062 (hard-requirement, KHÔNG try/except-swallow; event throw → File.insert rollback chưa-commit ⇒ không orphan) → `frappe.db.commit()` @1063. `scene_photos` (màn detail) derive read-time từ CÙNG `_scene_photos()` → invariant **count==rows** (số chặn ảnh-thứ-6 == số liệt kê). Contract này KHÔNG khai side-effect (thuộc service) — chỉ khai request/response shape.

## Decision

**Curate 1 path POST GROUNDED 1:1 `imm12.attach_incident_photo`, requestBody `multipart/form-data` DUY NHẤT + 3 schema RIÊNG, 200 = oneOf [`AttachIncidentPhotoEnvelope`, `Error`] (Decision-B route-by-VALUE 0-discriminator), 403 = SINGLE-SHAPE `Forbidden`, slot `{200,401,403}`.** Tag `incident`. Path-count **58→59**, opId **58→59** (đếm thật = 59, DUY NHẤT, camelCase). CONTRACT-ONLY (pure-yaml).

1. **`attachIncidentPhoto`** — `POST /api/method/assetcore.api.imm12.attach_incident_photo` › `operationId: attachIncidentPhoto` (dotted-path tail §8.1, camelCase, UNIQUE). Tag `incident`. **POST-only** (`@whitelist(methods=["POST"])` @273); live-sig parity `inspect.signature(imm12.attach_incident_photo) == {incident_name, _ignore}` (chỉ khai `incident_name` ở body; `**_ignore` KHÔNG là param contract). 200 = `oneOf [AttachIncidentPhotoEnvelope, Error]`. slot `{200,401,403}`.

2. **requestBody = `multipart/form-data` DUY NHẤT** (path multipart ĐẦU TIÊN của mirror — **KHÔNG `application/json`, KHÔNG `application/x-www-form-urlencoded`**: file-upload đọc `frappe.request.files["file"]`, KHÔNG form_dict/JSON body). `required: true` (sibling `content`, hợp lệ — KHÔNG dùng requestBodies-component nên KHÔNG dính bẫy G-OAS-403-DISAMBIG sibling-cạnh-`$ref`). Content schema `$ref AttachIncidentPhotoRequest`.

3. **`AttachIncidentPhotoRequest`** — CLOSED (`additionalProperties: false`), `required: [incident_name, file]`:

   | prop | type | ground |
   |---|---|---|
   | `incident_name` | string | name **Incident Report** đang mở (naming-series, vd `INC-2026-00001`) — **KHÔNG phải asset** (đọc `frappe.form_dict`, `incident_name=""` @274). **required** |
   | `file` | **string, `format: binary`** | ảnh bằng chứng (JPG/PNG, ≤10 MB) — server đọc `frappe.request.files["file"].stream.read()` @293. **required** |

   *(Optional cho BE:* `encoding.file.contentType: image/jpeg, image/png, image/jpg` nếu generator target đòi — KHÔNG bắt buộc cho contract; allowlist thực-thi ở service @1023, KHÔNG khai `enum` content-type trong schema.)*

4. **`AttachIncidentPhotoResponse`** — CLOSED (`additionalProperties: false`), `required: [file_url, file_name]` EXACT **2 prop** (GROUNDED `return {"file_url", "file_name"}` @1064), cả 2 `type: string`:

   | prop | type | ground |
   |---|---|---|
   | `file_url` | string | `file_doc.file_url` (`/private/files/…` — File `is_private=1`) |
   | `file_name` | string | `file_doc.file_name` (tên tệp gốc client gửi) |

5. **`AttachIncidentPhotoEnvelope`** — CLOSED (`additionalProperties: false`), `required: [success, data]`; `success.enum: [true]`; **`data` = `$ref AttachIncidentPhotoResponse`** (object nested, KHÔNG array — KHÁC `*ListEnvelope` data-array). Nhánh success của 200-oneOf; disjoint required-set với `Error` (`req[success,data]` vs `Error req[success,error,code,http_status]`) ⇒ máy-đọc phân-biệt bằng CLOSED-SCHEMA (KHÔNG discriminator — `success` là boolean, §5c).

6. **200 = `oneOf [AttachIncidentPhotoEnvelope, Error]`** — Decision-B route-by-VALUE (`body.success` enum[true] vs [false] + `body.http_status`), 0 discriminator. Nhánh `Error` gom **7 nhánh** in-handler (403 cap / 404 / 5×422) ARRIVE HTTP-200 (KHÔNG status-line key riêng cho 404/422 — quirk `handle()` return dict). Mirror `reportIncident`/`acknowledgeIncident` 200-oneOf.

7. **403 = SINGLE-SHAPE `Forbidden`** (`$ref #/components/responses/Forbidden`, `FrappeRawError` dispatcher-403 guest/no-token). **KHÁC `reportIncident` DUAL-403** — in-handler cap-403 (nhánh #2) đã phủ bởi nhánh Error của 200-oneOf ⇒ 403-slot chỉ giữ dispatcher-403 (sạch hơn, route-by-status-line đơn nhánh). Mirror `acknowledgeIncident`/`startRepair` (ADR-MOBILE-006). **401 = `Unauthorized401`** (bearer hết-hạn/invalid → HTTP-401 THẬT; đồng thời guest-guard in-handler @288).

**Phạm vi membership-set (test_mobile_oas):** path ∈ `_MVP_BUSINESS_PATHS` (→ 401/403 symmetry auto +1 — slot có CẢ 401 và 403) · ∈ `_MVP_ACTION_ENVELOPE` (POST-action-on-existing oneOf [<ActionEnvelope>, Error]; `incident_name` = khoá resource ĐÃ tồn tại, mirror `acknowledgeIncident`/`resolveIncident` — mỗi path envelope RIÊNG) · **∉ `_MVP_CREATE_ENVELOPE`** (đó là create top-level doc; đây attach sub-resource vào incident có sẵn) · **∉ `_MVP_SINGLE_LIST_ENVELOPE`/`_MVP_LIST_ENVELOPE`/`_MVP_READ_ENVELOPE`** · **c5 envelope-map += `attachIncidentPhoto → AttachIncidentPhotoEnvelope`** (`47→48`, giữ invariant `c5 == _MVP_BUSINESS_PATHS`) · ∈ `_RATE_LIMIT_SOURCE_MAP` (KHÔNG `@rate_limit` @273 ⇒ VẮNG khỏi `_PATHS_REQUIRE_429`, chống bịa 429) · **POST-only-at-source ∉ `_PARITY_VERB_ALLOWLIST`** (source đã POST — KHÔNG cần verb-flip parity exemption) · **∉ `_REQBODY_PATHS`** (KHÔNG dùng requestBodies-component — requestBody inline multipart) · **media-type guard mở-rộng**: hằng RIÊNG `_ATTACH_INCIDENT_PHOTO_BODY_MEDIA_TYPES = {"multipart/form-data"}` (path multipart-only ĐẦU TIÊN — EXEMPT khỏi sweep `_RPC_FORM_JSON_MEDIA` json+form) · `_EXPECTED_PATH_OPID` += dotted-path entry. **CONTRACT-ONLY**: `git diff -U0 api/imm12.py` + `services/imm12.py` vùng `attach_incident_photo`/`svc_attach_photo`/hằng photo = **KHÔNG có hunk MỚI vòng này** (handler+service ĐÃ trên đĩa từ vòng trước) ⇒ KHÔNG reload gunicorn, KHÔNG migrate — là **[AUTO]**, KHÔNG HARD-STOP USER. 58 path hiện-hữu byte-identical; `test_oas_d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | requestBody `application/json` (mirror `reportIncident`/`acknowledgeIncident` RPC form_dict) | SAI transport: `attach_incident_photo` đọc `frappe.request.files["file"]` (multipart file part), KHÔNG `form_dict`/JSON body. Khai json/form ⇒ codegen sinh client gửi JSON → server `files.get("file")` = None → 422 "Thiếu tệp ảnh" MỌI lần. File-upload BẮT BUỘC `multipart/form-data`. |
| B | 403 = DUAL-SHAPE `AttachIncidentPhotoForbidden` (oneOf Error\|FrappeRawError, mirror `reportIncident`) | KHÔNG cần: in-handler cap-403 (`_assert_can_attach_photo` @987) qua `handle()` → HTTP-200 + Error ⇒ ĐÃ nằm trong nhánh `Error` của 200-oneOf. Lặp lại ở 403-slot = 2 chỗ khai cùng shape (dead-branch nói-dối HTTP-403+Error KHÔNG BAO GIỜ xảy ra — cap-403 KHÔNG set status-line). 403-slot SINGLE `Forbidden` (chỉ dispatcher-403) = convention MỚI post-ADR-006 (`acknowledgeIncident`/`startRepair`), sạch hơn `reportIncident` outlier. |
| C | 200 = SINGLE `AttachIncidentPhotoEnvelope` (mirror `listLocations`/`listDepartments`) | SAI error-mode: handler QUA `handle(svc_attach_photo)` + service **7 nhánh raise ServiceError** (404/403/5×422) ⇒ HTTP-200 CÓ nhánh Error. SINGLE-shape bỏ nhánh Error = codegen KHÔNG deser được lỗi validation (ảnh sai/quá-lớn/đủ-5) → client crash/nuốt lỗi. `oneOf [Env, Error]` phản-ánh đúng (mirror `reportIncident`/`acknowledgeIncident`). |
| D | `data` = array (mirror `*ListEnvelope`) HOẶC thêm field ngoài `{file_url,file_name}` | SAI shape: service `return {"file_url", "file_name"}` @1064 = object 2-key ĐÚNG, KHÔNG array (attach 1 ảnh/lần). Thêm `incident_name`/`lifecycle_event_id`/… = bịa khoá KHÔNG có ⇒ `additionalProperties:false` chặn nhưng codegen sinh field null-vĩnh-viễn. EXACT 2-prop required. |
| E | Khai `enum` content-type / `maxLength` cho `file` trong schema | KHÔNG faithful: allowlist (`image/jpeg`/`jpg`/`png`) + cap 10 MB + max-5 thực-thi ở **service** @1023-1028 (Decision-B 422), KHÔNG ở JSON-schema wire. `file: {format: binary}` = đủ cho codegen sinh multipart part; ràng buộc nghiệp-vụ đến qua Error envelope (route-by body). Khai enum content-type trong schema-string vô-nghĩa (binary KHÔNG có enum giá-trị). |
| F | 2-bước `upload → file_url` rồi POST `file_url` (JSON) | LOẠI ở tầng SERVICE (ADR-IMM12-06/07 đã chốt single-step): 2-bước risk orphan File (upload xong nhưng attach fail) + không atomic với lifecycle event. Backend ĐÃ chọn single-step multipart (robust). Contract PHẢI mirror source thực-thi, KHÔNG re-design. |
| G | `attachIncidentPhoto → _MVP_CREATE_ENVELOPE` (vì tạo `File`) | Semantics KHÔNG khớp: `_MVP_CREATE_ENVELOPE` = create top-level doc (PM WO/Incident/Repair WO/Calibration). Đây attach sub-resource vào **incident có sẵn** (`incident_name` = khoá resource tồn tại, mirror `acknowledgeIncident` action-on-existing). ⇒ `_MVP_ACTION_ENVELOPE` (POST-action-on-existing). Envelope RIÊNG (data `{file_url,file_name}` ≠ mọi ActionEnvelope hiện có). |
| ✅ H | 1 path POST multipart-only, 3 schema RIÊNG, 200 oneOf [Env, Error], 403 SINGLE `Forbidden`, `_MVP_ACTION_ENVELOPE`, media-type-guard-multipart | Grounded 1:1 source; blast-radius = +1 path +3 schema (PURE-YAML); codegen sinh 1 method upload đúng multipart shape → app đính ảnh bằng-chứng type-safe; Decision-B intact; 403-slot sạch (dispatcher-only); mở đường CR-14/CR-15 (path multipart đầu tiên = template). |

## Consequences

- **(+)** App mobile màn Chi tiết sự cố có method `attachIncidentPhoto` codegen-ready: KTV chụp → upload multipart type-safe → File private NĐ98 + lifecycle `incident_photo_attached`. CR-17/G6 ĐÓNG.
- **(+)** **Path `multipart/form-data` ĐẦU TIÊN của mirror** = template chuẩn cho CR-14/CR-15 (ảnh checklist PM `imm08`/CM `imm09`): media-type multipart-only + `file: {format: binary}` + 200-oneOf + ladder 422 → mọi write-path multipart kế bồi theo.
- **(+)** Contract GROUNDED 1:1 source — 3 schema VERBATIM (`AttachIncidentPhotoResponse` EXACT `{file_url,file_name}` @1064; ladder `Error.http_status` ⊇ {403,404,422} khớp 7 nhánh @1018-1051 gồm CẢ corrupt-guard); 403-slot SINGLE `Forbidden` phản-ánh đúng "cap-403 đã phủ bởi 200-Error" (mirror `acknowledgeIncident`).
- **(+)** **CONTRACT-ONLY** — vòng này KHÔNG thêm hunk `.py` mới vùng `attach_incident_photo`/`svc_attach_photo`/hằng photo (handler+service ĐÃ trên đĩa LIVE từ vòng trước) ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO], KHÔNG HARD-STOP USER); `test_oas_d12/d15/d17` UNCHANGED (pure mobile-yaml). 58 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator; 2 nhánh oneOf disjoint required-set closed-schema); 0 dangling `$ref` (3 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`).
- **(−)** **Media-type guard phân-nhánh MỚI**: `_ATTACH_INCIDENT_PHOTO_BODY_MEDIA_TYPES = {"multipart/form-data"}` — path multipart-only đầu tiên EXEMPT khỏi sweep `_RPC_FORM_JSON_MEDIA` (json+form). Người bồi write-path kế PHẢI phân-biệt: RPC form_dict (đọc `form_dict`) → json+form; file-upload (đọc `request.files`) → multipart-only. Quyết-định bằng SOURCE (grep `request.files` vs `form_dict`), KHÔNG đoán.
- **(−)** 403-slot SINGLE `Forbidden` (KHÔNG dual-403 như `reportIncident`) — người bồi POST-action kế PHẢI theo convention post-ADR-006: có in-handler cap-403 QUA `handle()` (→ HTTP-200 Error) ⇒ 403-slot chỉ dispatcher-403 SINGLE; CHỈ dùng dual-403 khi cap-403 KHÔNG qua `handle()` (raw `_err` trước `handle`, hiếm). `attach_incident_photo` cap-403 qua service ServiceError → `handle()` ⇒ SINGLE.
- **(−)** `attachIncidentPhoto` vào `_MVP_ACTION_ENVELOPE` (KHÔNG `_MVP_CREATE_ENVELOPE`) — dù tạo `File`. Người bồi kế phân-biệt bằng KHOÁ: `incident_name`/`name` = resource ĐÃ tồn tại → action-on-existing; KHÔNG khoá + insert doc mới top-level → create.
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `531→541` (test_mobile_oas, +10 TC class `TestMobileAttachIncidentPhotoContract` a..j) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `531→541` + `_GUARD_SUITE_SUM` `674→684` + `_MOBILE_OAS_TOTAL` `700→710` (= `_GUARD_SUITE_SUM` 684 + preflight 26) + c5 `47→48`. *(N=10 = khuyến nghị BA; BE có thể tinh-chỉnh granularity TC miễn 3 counter di-chuyển ĐỒNG +N.)*

---

## Handoff BE/Test (Bước-4 — kế-hoạch, ATOMIC pure-yaml)

> **CONTRACT-ONLY** — TUYỆT ĐỐI KHÔNG đụng `api/imm12.py`/`services/imm12.py` (`attach_incident_photo`+`svc_attach_photo`+hằng photo ĐÃ LIVE trên đĩa). Không reload/migrate/commit. DoD: `bench --site miyano run-tests --app assetcore --module assetcore.tests.guards.test_mobile_oas` + `.test_mobile_docset` = **'Ran N OK' THẬT** (guard-suite sums +10 synced).

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`):
- +1 path `POST /api/method/assetcore.api.imm12.attach_incident_photo` (opId `attachIncidentPhoto`, tag `incident`); requestBody `multipart/form-data` DUY NHẤT (`required:true`, schema `$ref AttachIncidentPhotoRequest`); 200 = `oneOf [AttachIncidentPhotoEnvelope, Error]`; slot `{200,401,403}` (`401 Unauthorized401`, **`403 Forbidden` SINGLE-SHAPE** — KHÔNG dual-403).
- +3 schema (`AttachIncidentPhotoRequest` closed req[incident_name,file] · `file:{type:string,format:binary}` · `AttachIncidentPhotoResponse` closed EXACT req[file_url,file_name] cả 2 string · `AttachIncidentPhotoEnvelope` closed req[success,data] `success.enum[true]` `data=$ref AttachIncidentPhotoResponse`). Cả 3 `additionalProperties:false`. Tái-dùng `Unauthorized401`/`Forbidden`. 0 orphan, 0 dangling.

**(2) test_mobile_oas.py**: path/opId count `58→59`; `_EXPECTED_PATH_OPID` += `("/api/method/assetcore.api.imm12.attach_incident_photo": ("post","attachIncidentPhoto"))`; path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_ACTION_ENVELOPE`; c5 map += `attachIncidentPhoto→AttachIncidentPhotoEnvelope` (`47→48`); `_RATE_LIMIT_SOURCE_MAP` += (no-rate-limit); hằng RIÊNG `_ATTACH_INCIDENT_PHOTO_BODY_MEDIA_TYPES = {"multipart/form-data"}`; +1 TC class `TestMobileAttachIncidentPhotoContract` (a..j, 10 TC — xem dưới); `_EXPECTED_TEST_COUNT` `531→541`.
- **TC a..j (khuyến nghị):** a) yaml path-count==59 ∧ opId-count==59. b) path POST-only + opId `attachIncidentPhoto` + tag `incident` + ∈ `_MVP_BUSINESS_PATHS`. c) requestBody = **`multipart/form-data` DUY NHẤT** (`content` keys == {"multipart/form-data"}, KHÔNG json/form-urlencoded) + `required:true` — dùng `_ATTACH_INCIDENT_PHOTO_BODY_MEDIA_TYPES`; ∉ `_REQBODY_PATHS`. d) `AttachIncidentPhotoRequest` closed `additionalProperties:false` + `required==[incident_name,file]` + `file.type==string` ∧ `file.format==binary` ∧ `incident_name.type==string`. e) 200 = `oneOf [AttachIncidentPhotoEnvelope, Error]` (EXACT 2 nhánh, KHÔNG discriminator; disjoint required-set). f) `AttachIncidentPhotoEnvelope` closed req[success,data] `success.enum==[true]` `data.$ref==…AttachIncidentPhotoResponse` (object nested, KHÔNG array). g) `AttachIncidentPhotoResponse` closed `additionalProperties:false` EXACT 2 prop `required==[file_url,file_name]` cả 2 `type:string`. h) slot `{200,401,403}`: `401 Unauthorized401` + **`403 Forbidden` SINGLE-SHAPE** (`$ref Forbidden`, KHÔNG `ReportIncidentForbidden`/dual) — anti-dual-403. i) membership + 401/403 symmetry + `_MVP_ACTION_ENVELOPE` + c5==_MVP_BUSINESS_PATHS + POST-only ∉ `_PARITY_VERB_ALLOWLIST` + no-`@rate_limit` (∉ `_PATHS_REQUIRE_429`) + no-dangling. j) CONTRACT-ONLY — `git diff` `api/imm12.py`+`services/imm12.py` vùng `attach_incident_photo`/`svc_attach_photo` KHÔNG hunk MỚI vòng này (pure-yaml, handler+service untouched) — anti-false-green.
- **⚠️ Media-type sweep**: nếu suite có test sweep "mọi path POST có requestBody PHẢI khai json+form" (`_RPC_FORM_JSON_MEDIA`), PHẢI EXEMPT `_ATTACH_INCIDENT_PHOTO_PATH` (multipart-only, đọc `request.files` KHÔNG `form_dict`) — nếu không sweep sẽ RED sai.

**(3) test_mobile_docset.py**: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `531→541` · `_GUARD_SUITE_SUM` `674→684` · `_MOBILE_OAS_TOTAL` `700→710` (=684+26). ADR-MOBILE-027 registered README (TC-MOB-DOC-02 glob động — README row bắt-buộc, ĐÃ thêm ở Bước-2 BA; balance ADR-on-disk 27 == README-index 27).

**(4) docs narrative** (ĐÃ XONG Bước-2 BA): `04-api-contract.md` (§8.33 `attachIncidentPhoto`) + README ADR-row (ADR-MOBILE-027) + Core Doc [`05_API_Specification.md`](../imm-12/05_API_Specification.md) §15 mobile-mirror cross-ref + Self-Correction (thêm nhánh corrupt vào bảng lỗi, sửa grounding content-type 2→3 giá-trị @49, bỏ hedge "đề xuất" cap 10 MB đã LIVE @48).

**BACKLOG (vòng kế):** `attachPmChecklistPhoto` (CR-14 `imm08`) + `attachCmChecklistPhoto` (CR-15 `imm09`) — ảnh checklist PM/CM, cùng family multipart write-path. Bồi theo template path này (media-type multipart-only + 200-oneOf + ladder 422 + 403 SINGLE `Forbidden`); LƯU Ý: PM/CM MAX=1 per-item (KHÁC incident MAX=5 scene-photo cả phiếu — HEIC policy CHUNG, MAX policy RIÊNG theo domain, xem imm-12 §15 + imm-08 ADR-IMM08-PHOTO-04). Grep `request.files`/`MAX_*_PHOTO*`@source TRƯỚC khi đặc tả.
