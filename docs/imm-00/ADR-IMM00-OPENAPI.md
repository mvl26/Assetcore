# ADR-IMM00-OPENAPI — OpenAPI 3.1 auto-gen từ `@frappe.whitelist` + envelope component SSoT + serve spec + Swagger/Redoc + enrich plan + servers (get_url SSoT) / info-meta / externalDocs (D16: doc-base = hooks `app_docs_url`, graceful-omit)

| Mục | Giá trị |
|---|---|
| Trạng thái | **Accepted** ([R1-GATE Phase A] — Gate THIẾT KẾ Vòng 1, PHÂN TÍCH). Thực thi từ Vòng 2+ (implement). |
| Ngày | 2026-06-09 |
| Phạm vi | IMM-00 (cross-cutting — API platform). Introspect `assetcore.api.*` (485 endpoint / 22 module-file). KHÔNG re-architect BE/DocType, KHÔNG modify ERPNext core. |
| Owner | BA Lead + System Architect |
| Liên quan | `./ADR-IMM00-QR-SCAN-ACTION.md` (contract `available_actions`), `./ADR-IMM00-LIST-SCOPE.md` (envelope `{success,data}`), `05_API_Specification.md` (spec thủ công hiện hành — ADR này biến nó thành auto-gen), `utils/response.py` (envelope SSoT) |
| Supersedes | Không — **bổ sung** cơ chế tự sinh + serve cho spec mà `05_API_Specification.md` đang viết tay. |

> ADR này là **quyết định cuối** cho cơ chế auto-gen OpenAPI 3.1, cấu trúc `openapi.json`, route serve, trang docs, kế hoạch enrich, và cách giữ đồng bộ code↔doc. Mọi task BE/FE/QA Vòng 2+ phải nhất quán với ADR này. Khi mâu thuẫn → ADR thắng.
>
> **Bản chất GATE:** đây là gate PHÂN TÍCH — Vòng 1 **KHÔNG đụng code** (`.py`/`.vue`/`.ts`/`.html`). Chỉ chốt cơ chế + cấu trúc + contract để Vòng 2+ thực thi mà KHÔNG phải hỏi lại. Mỗi quyết định D1–D9 **đo được**; mỗi task xuống dòng map tới đúng 1 quyết định.

---

## Bối cảnh (vì sao cần GATE này)

AssetCore phơi **485 endpoint whitelisted** trên **22 module-file** (`assetcore/api/*.py`). Hiện chỉ có spec **viết tay** ở `05_API_Specification.md` (107 endpoint của riêng IMM-00) — drift liên tục với code, không có máy đọc được, không có trang thử nghiệm cho tích hợp HIS/EMR/LIS/RIS/PACS (CLAUDE.md §14). Customer doc nhiều lần claim "OpenAPI spec" nhưng **chưa có code** (`assetcore-doc` Phần 4 ghi rõ phải mark `[ROADMAP]`). Gate này biến claim đó thành hiện thực: spec sinh **từ chính chữ ký hàm + decorator**, không tay.

**Nguy cơ nếu KHÔNG chốt:**
- (a) Sinh spec bằng cách hardcode path/verb/param → drift với code ngay lần sửa kế → spec dối.
- (b) Suy `method` GET/POST sai → integrator gọi sai verb → 404/405 hàng loạt.
- (c) Định nghĩa `SuccessEnvelope`/`ErrorEnvelope` ở nơi thứ 2 (trong spec) ≠ `utils/response.py` → 2 nguồn sự thật, lệch khi thêm ErrorCode.
- (d) Bỏ qua 42 endpoint nhận body qua `form_dict` (`create_*`/`update_*` lấy `frappe.local.form_dict`) → spec không mô tả request body → integrator không biết gửi field gì.
- (e) 9 chữ ký `X | None = None` (union 3.10) khiến `inspect.signature` / type-hint→JSON-type map ra `anyOf` rối hoặc fail introspect → phải đổi sang default rõ ràng TRƯỚC khi generate.
- (f) Serve spec không gate session → lộ toàn bộ bề mặt API (485 endpoint) cho khách vãng lai → trinh sát tấn công.

**5 câu hỏi domain (assetcore-doc Phần 2):**
1. **WHO HTM stage:** Cross-cutting (IMM-00 foundation) — API platform phục vụ MỌI stage (integration outbound FHIR/OpenAPI, CLAUDE.md §14).
2. **NĐ98:** Không mandate trực tiếp; nhưng spec auto-gen củng cố **truy xuất nguồn gốc** (mọi tích hợp HIS/EMR có hợp đồng máy-đọc-được) + minh bạch bề mặt cho audit bảo mật.
3. **Stakeholder:** Integrator (đội HIS/EMR/LIS), System Architect, đối tác đấu thầu (đọc spec để chấm), QA (contract test). Spec gate session → chỉ user đã đăng nhập đọc.
4. **Lifecycle event:** auto-gen KHÔNG phát sinh lifecycle event — đây là introspection read-only của codebase.
5. **Hậu quả nếu data sai:** spec sai verb/param → integrator code sai → tích hợp gãy ở production HIS; envelope lệch → FE/integrator parse sai lỗi → UX gãy; lộ spec cho guest → bề mặt tấn công.

---

## FACTS đã verify tại source (cơ sở quyết định — KHÔNG phỏng đoán)

| # | FACT | Evidence (`file:line` / lệnh) |
|---|---|---|
| F1 | **485 endpoint whitelisted / 22 module-file.** Đếm `grep -c '^@frappe.whitelist' assetcore/api/*.py` rồi sum = **485**; file (trừ `__init__.py`) = **22**. Phân bố: imm00=111, imm16=52, inventory=36, imm04=34, imm06=25, imm08=24, imm03=24, imm15=22, imm01=22, imm11=18, imm12=16, imm05=16, imm02=16, user=14, purchase=13, imm09=13, layout=7, auth=7, import_data=6, notifications=3, imm14=3, dashboard=3. | `grep -c '^@frappe.whitelist' assetcore/api/*.py` (2026-06-09) |
| F2 | **`ErrorCode` SSoT = `utils/response.py:37`** (class `ErrorCode`, 15 hằng: VALIDATION, VALIDATION_ERROR, BUSINESS_RULE, UNAUTHORIZED, FORBIDDEN, NOT_FOUND, CONFLICT, BAD_STATE, DUPLICATE, INVALID_PARAMS, PAYLOAD_TOO_LARGE, RATE_LIMITED, COMPLIANCE_BLOCKED, INTERNAL, INTERNAL_ERROR). Docstring tự khẳng định "SOURCE OF TRUTH"; `services/shared/constants.py:ErrorCode` re-export từ đây; FE mirror `frontend/src/api/errors.ts`. | `utils/response.py:37-57` |
| F3 | **`_HTTP_FOR_CODE` map (code→HTTP) = `utils/response.py:60`** (15 entry: VALIDATION→422, VALIDATION_ERROR→400, BUSINESS_RULE→422, UNAUTHORIZED→401, FORBIDDEN→403, NOT_FOUND→404, CONFLICT→409, BAD_STATE→409, DUPLICATE→409, INVALID_PARAMS→400, PAYLOAD_TOO_LARGE→413, RATE_LIMITED→429, COMPLIANCE_BLOCKED→422, INTERNAL→500, INTERNAL_ERROR→500). | `utils/response.py:60-76` |
| F4 | **Success envelope shape = `_ok(data)` → `{"success": True, "data": <payload>}`** (`utils/response.py:79,92`). **Error envelope shape = `_err(...)` → `{"success": False, "error": <msg>, "code": <ErrorCode>, "http_status": <int>}`** + optional `fields`/`message_code`/`context`/`action_hint`/`severity`/`title`/`extra` (`utils/response.py:133-153`). | `utils/response.py:79-154` |
| F5 | **9 chữ ký `X | None = None` (union PEP 604) tồn tại đúng tại các dòng cited:** imm01:543 (`get_demand_forecast(... device_category: str | None = None)`), imm01:559 (`dashboard_kpis(period: str | None = None)`), imm04:106 (`save_commissioning(name, fields: str | dict | None = None)`), imm04:116 (`create_commissioning(data: str | dict | None = None)`), imm04:126 (`report_nonconformance(... nc_data: str | dict | None = None)`), imm04:156 (`submit_baseline_checklist(... results: str | list | None = None)`), imm14:39 (`... responsible: str | None = None`), dashboard:890 (`get_persona_dashboard(persona: str | None = None)`). *(imm04 còn `str|dict`/`str|list` union — đây ĐỒNG THỜI là form_dict/JSON-string body, xem F6/F7.)* | `assetcore/api/imm01.py:543,559`; `imm04.py:106,116,126,156`; `imm14.py:39`; `dashboard.py:890` |
| F6 | **`create_*`/`update_*` (body qua form_dict):** `grep '^def create_\|^def update_'` = **85 def** trong `api/*.py` (mix whitelist wrapper + private `_impl`). Nhóm này nhận payload tạo/sửa record → cần **body-schema bridge** sang `frappe.get_meta(<DocType>).fields`. Chốt con số introspect-được = số endpoint whitelist `create_*`/`update_*` (đo lại lúc generate, ghi vào registry — KHÔNG hardcode 42). | `grep -n '^def create_\|^def update_' assetcore/api/*.py` |
| F7 | **JSON-string param (param nhận chuỗi JSON rồi `json.loads`/`frappe.parse_json`):** `grep 'json.loads\|frappe.parse_json' api/*.py` = **11 site** (Frappe HTTP truyền mọi arg dạng string → list/dict phải parse). Cộng các union `str|dict|list` (F5: imm04×4) = param "string-mã-hoá-cấu-trúc". Cần **override registry** ghi `type:string` + `format: json` + `x-decoded-schema`. | `grep -n 'json.loads\|frappe.parse_json' api/*.py` |
| F8 | **`list_*`/`get_*` (data payload):** `grep '^def list_\|^def get_'` = **189 def**. Nhóm này trả danh sách/chi tiết — `data` envelope là `{items:[...], pagination:{...}}` (list) hoặc object (get). Cần **override registry** mô tả response `data` shape (không suy được từ chữ ký return `-> dict`). | `grep -n '^def list_\|^def get_' assetcore/api/*.py` |
| F9 | **`www/` đã có precedent serve trang web tĩnh trong app:** `assetcore/www/assetcore.html` + `assetcore/www/assetcore.py` (Frappe web page controller). ⟹ `www/api-docs.html` (+ optional `api-docs.py` để gate) là pattern HỢP LỆ, KHÔNG cần hạ tầng mới. | `ls assetcore/www/` = `assetcore.html`, `assetcore.py` |
| F10 | **KHÔNG có `openapi.py` / module sinh spec nào tồn tại** — greenfield hoàn toàn (`find . -name 'openapi*.py'` = 0; `grep -rln 'swagger\|redoc\|openapi' assetcore/*.py` = 0). | `find` + `grep` toàn repo (2026-06-09) |
| F11 | **`POST` whitelist count = 252 site.** ⚠️ **Codebase dùng dấu nháy ĐÔI:** `@frappe.whitelist(methods=["POST"])` (252 site, double-quote) — KHÔNG single-quote. Lệnh đo ĐÚNG: `grep -rc '"POST"' api/*.py` (= 252); lệnh `grep "methods=\['POST'\]"` (single-quote) = **0** (sai do quote style). ⟹ default verb = **GET**, chỉ endpoint khai báo `methods=["POST"]` → POST (quy tắc Frappe). **Hệ quả thiết kế:** generator D1/D2 đọc verb qua `ast` (chuẩn hoá nháy → bất biến quote style), KHÔNG dựa grep chuỗi-văn-bản — nên defect quote-style này KHÔNG ảnh hưởng generator, chỉ ảnh hưởng evidence-command thủ công (QA dùng pattern double-quote). | `grep -rc '"POST"' assetcore/api/*.py \| awk -F: '{s+=$2}END{print s}'` = 252 (2026-06-09) |

> **Đính chính số liệu PM giao:** PM ước lượng "42 form_dict / 99 JSON-string / 147 list_*-get_*". Đếm-thật tại source (2026-06-09) cho **85 create/update def, 11 json.loads site, 189 list/get def**. Chênh do PM dùng tiêu chí grep khác (vd chỉ whitelist wrapper, hoặc gộp param). **Quyết định: con số ground-truth = đo lại tại generate-time và in vào `x-assetcore-stats` của spec** (D8) — KHÔNG hardcode số nào trong code; số trong ADR chỉ để định cỡ công việc.

---

## Quyết định (9 quyết định — DỨT KHOÁT, mỗi quyết định đo được)

### D1 — CƠ CHẾ INTROSPECT: `importlib` + `inspect.signature` + `ast` walk `assetcore.api.*`

**Quyết định (1 dòng):** sinh spec bằng **introspection runtime + tĩnh**, KHÔNG hardcode danh mục endpoint.

Pipeline (chốt 3 bước, mỗi bước 1 thư viện chuẩn Python — KHÔNG dependency ngoài):
1. **`importlib.import_module(f"assetcore.api.{mod}")`** cho 22 module-file → object module.
2. **`inspect.signature(fn)`** cho mỗi hàm có `getattr(fn, "whitelist", ...)` (hoặc cờ Frappe gắn bởi `@frappe.whitelist`) → tên param, default, annotation. **`inspect.getdoc(fn)`** → `summary`/`description`.
3. **`ast`** parse source file → đọc đối số decorator (`@frappe.whitelist(methods=["POST"], allow_guest=True)` — codebase dùng nháy đôi; `ast` chuẩn hoá nháy nên introspect bất biến với quote style) mà runtime introspection không lộ trực tiếp → suy `method` + `allow_guest` (D2). `ast` cũng phát hiện `json.loads(<param>)`/`frappe.parse_json(<param>)` trong body → đánh dấu JSON-string param (D5). **`allow_guest=True` = 6 site** (đo 2026-06-09) → 6 endpoint này map `security: []`; 479 còn lại → `cookieSession`.

> Đo được: chạy generator → spec liệt kê **đúng N endpoint** với N = `grep -c '^@frappe.whitelist'` (hiện 485). Sai-số = 0. Mỗi endpoint có `operationId = assetcore.api.<mod>.<fn>`.

### D2 — ÁNH XẠ endpoint → path/method/param (quy tắc Frappe HTTP)

**Quyết định (1 dòng):** ánh xạ **xác định** theo quy tắc Frappe, suy từ decorator + chữ ký:

| Thuộc tính OpenAPI | Quy tắc dẫn xuất | Nguồn |
|---|---|---|
| `path` | `/api/method/assetcore.api.<mod>.<fn>` | tên module + tên hàm |
| `method` | **GET** mặc định; **POST** nếu `@frappe.whitelist(methods=["POST"])` (double-quote — codebase quy ước, F11) | F11 (ast đọc decorator — bất biến quote style) |
| `parameters[].required` | `True` nếu param **không có default** trong `inspect.signature` | F5 (signature) |
| `parameters[].schema.type` | type-hint → JSON type: `str→string`, `int→integer`, `float→number`, `bool→boolean`, `dict→object`, `list→array`, no-hint→`string` | `inspect` annotation |
| `parameters[].in` | `query` cho GET-scalar; body cho POST/form_dict (D4) | method + D4 |
| `security` | `[]` (none) nếu `allow_guest=True`; ngược lại `cookieSession` | ast đọc `allow_guest` |

> Đo được: với endpoint mẫu `assetcore.api.imm00.get_asset_scan_info` → spec ghi `GET /api/method/assetcore.api.imm00.get_asset_scan_info`, param `token`/`name` (required tùy default), security `cookieSession`. QA assert path/method/required khớp chữ ký thật.

### D3 — 2 COMPONENT DÙNG-CHUNG: `SuccessEnvelope` + `ErrorEnvelope`, nguồn DUY NHẤT = `utils/response.py`

**Quyết định (1 dòng):** mọi response wrap trong **đúng 2 component schema** sinh **từ `utils/response.py`** (KHÔNG viết tay trong spec):

```yaml
components:
  schemas:
    SuccessEnvelope:        # nguồn: utils/response.py:79 _ok
      type: object
      required: [success, data]
      properties:
        success: { type: boolean, enum: [true] }
        data: {}            # payload tuỳ endpoint (allOf override khi enrich — D6)
    ErrorEnvelope:          # nguồn: utils/response.py:95 _err
      type: object
      required: [success, error, code, http_status]
      properties:
        success: { type: boolean, enum: [false] }
        error:   { type: string }
        code:    { type: string, enum: [<sinh từ ErrorCode utils/response.py:37>] }
        http_status: { type: integer, enum: [<sinh từ _HTTP_FOR_CODE utils/response.py:60 values>] }
        fields:  { type: object, additionalProperties: { type: string } }
        # optional notification-framework fields (response.py:142-151)
        message_code: { type: string }
        context: { type: object }
        action_hint: { type: string }
        severity: { type: string, enum: [error, warning, info, success, critical] }
        title: { type: string }
```

**Chốt nguồn DUY NHẤT:** generator **đọc `ErrorCode.__dict__`** (`utils/response.py:37`) cho `code.enum` và **`_HTTP_FOR_CODE.values()`** (`:60`) cho `http_status.enum`. Thêm ErrorCode mới ở `response.py` → spec tự cập nhật enum lần generate kế. KHÔNG có danh sách code thứ 2.

> Đo được: thêm hằng vào `ErrorCode` → regenerate → enum trong `ErrorEnvelope.code` tăng đúng 1. QA test: `set(spec.code.enum) == set(ErrorCode values)` và `set(spec.http_status.enum) == set(_HTTP_FOR_CODE.values())`.

### D4 — BODY-SCHEMA BRIDGE cho endpoint `create_*`/`update_*` (form_dict → DocType meta)

**Quyết định (1 dòng):** endpoint tạo/sửa record nhận body → `requestBody` schema **bắc cầu** sang `frappe.get_meta(<DocType>).fields` (KHÔNG để body trống/`object` mơ hồ).

- Map `create_<X>`/`update_<X>` → DocType qua **bảng ánh xạ tường minh** trong override registry (D5): `{ "create_asset": "AC Asset", "update_supplier": "Supplier", "create_commissioning": "Asset Commissioning", ... }`. KHÔNG suy heuristic tên (dễ sai).
- Với mỗi DocType → `frappe.get_meta(dt).fields` → sinh property cho field không-system (loại `Section Break`/`Column Break`/`HTML`), `required` từ `reqd=1`, type-hint từ `fieldtype` (Data→string, Int→integer, Float/Currency→number, Check→boolean, Link/Select→string+enum, Table→array).
- Endpoint POST không-DocType (vd `transition_status`, `open_capa`) → body schema từ chữ ký param (D2) gói trong `requestBody.application/x-www-form-urlencoded`.

> Đo được: spec của `create_asset` có `requestBody` liệt field từ `AC Asset` meta (asset_code, device_model, location, ...) với `reqd` field marked required. Con số endpoint áp bridge = đếm tại generate-time, in vào `x-assetcore-stats.form_dict_endpoints` (KHÔNG hardcode 42).

### D5 — OVERRIDE REGISTRY cho JSON-string param + `list_*`/`get_*` data payload

**Quyết định (1 dòng):** 1 file registry tĩnh **`assetcore/api/openapi_overrides.py`** (dict thuần) là nơi DUY NHẤT chứa thông tin introspection KHÔNG suy được từ chữ ký — KHÔNG rải rác trong từng endpoint.

Registry chứa các bảng:
0. **`FORM_DICT_DOCTYPE_MAP`** ✅ **DONE (Phase A5)** — map operationId-tail (`<module>.<fn>`) của POST `create_*` đọc `frappe.local.form_dict` (no signature-param, ~21 endpoint) → tên DocType chính xác (vd `"imm00.create_asset" → "AC Asset"`). Generator (`openapi._request_body_from_doctype`) dựng object schema TỪ `frappe.get_meta(DocType)` (fieldtype data-bearing qua **`FRAPPE_FIELDTYPE_JSON_MAP`** — TÁCH khỏi `_TYPE_MAP` type-hint Python; bỏ `hidden` + bỏ API-autoset). Bảng phụ: **`API_AUTOSET_FIELDS`** (per-DocType: AC Asset = naming_series/status/lifecycle_status; global = naming_series) loại field API tự set khỏi properties+required; **`REQUIRED_OVERRIDES`** (AC Asset `required` = SSoT `_ASSET_REQD_LABELS_VI` = `['asset_category','asset_name']`, cross-ref tránh import vòng). Map tường minh, KHÔNG heuristic. **Fail-safe:** create_* CHƯA map (vd `user.create_system_user` → core User) → giữ hành vi D4 (requestBody=None). Coverage guard liệt kê unmapped. `user.create_system_user` cố tình bỏ (core DocType, body nhiễu).
1. **`JSON_PARAM_OVERRIDES`** ✅ **DONE (Phase A10 — D10)** — param nhận chuỗi JSON (F7: `json.loads`/`parse_json` site + union `str|dict|list` F5). Generator (`openapi._json_string_params`) tự **KHÁM PHÁ** tập param JSON-string qua AST (Call `parse_json`/`_parse_json`/`json.loads`/`frappe.parse_json` có arg[0]=Name(param), TRỰC TIẾP hoặc FORWARD vào private delegate `_list_xxx`, lan tới fixpoint) — **đếm động `json_param_count`, KHÔNG hardcode 109 call-site**. Mỗi param JSON-string → schema con (GET query-param / POST body property) thêm `format:json` + `x-decoded-default-type` (default literal `'{}'`→object, `'[]'`→array, else object) — type GIỮ `string` (backward-compat Swagger UI). `JSON_PARAM_OVERRIDES` (registry curated SSoT) chỉ cho param cần `x-decoded-schema` tường minh: `"imm04.create_commissioning.data"` + `"imm04.save_commissioning.fields"` → `{'doctype': 'Asset Commissioning'}` (tái dùng D5 `_request_body_from_doctype` lazy meta). `len(JSON_PARAM_OVERRIDES)` ≥ 2; **drift-guard:** mọi key resolve về param JSON-string introspect-được (entry trỏ param không-tồn-tại → test fail). **Verify @source (2026-06-09):** grep `json.loads|parse_json|_parse_json` api/*.py (trừ openapi) = 109 call-site (14 def/import + ~95 parse) → `json_param_count` = **63** (whitelisted-fn, param) DUY NHẤT. `len(paths)` GIỮ 486, `enriched_count` GIỮ 161, root tags 23 canonical GIỮ (D9). TC-OAS-D10-01..07 (25 test) GREEN.
2. **`RESPONSE_DATA_OVERRIDES`** `[ROADMAP D5+]` — shape `data` của `list_*`/`get_*` (F8: chữ ký `-> dict` không lộ). List → `{items: array<$ref>, pagination: {total,page,page_size}}`; get → `$ref` 1 object. Map tới component schema DocType-shape (tái dùng D4 meta-bridge).
3. **`OPERATION_META`** ✅ **DONE (Phase A6 — D6 enrich)** — `dict[op_tail, {summary, description, tags, examples}]`, nơi DUY NHẤT chứa metadata enrich cho 3 module trọng yếu (imm00/04/12). Generator (`openapi._enrich_operation`) DẪN XUẤT từ bảng này: ghi đè `summary`/`description` (KHÔNG còn rỗng/operationId), set `tags`, nhúng `examples` vào `requestBody` (POST) + response `200` (envelope-success) + các response lỗi VI (trỏ `ErrorEnvelope`). **Fail-safe:** op-tail KHÔNG có entry → giữ default D1-D5 (summary từ docstring, không examples). Chi tiết hợp đồng + đo lường: §D6 dưới.

> Đo được (A5): registry import-được THUẦN (no DB module-level — monkeypatch `frappe.get_meta` raise → import vẫn pass); số endpoint áp body-bridge đếm ĐỘNG qua `FORM_DICT_DOCTYPE_MAP ∩ introspected POST form_dict` (= 20 hiện tại, KHÔNG hardcode); xoá 1 entry → giảm đúng 1 (mutation test có răng). TC-OAS-06/07 + TC-OAS-DOCTYPE-MAP + TC-OAS-COVERAGE green; `test_oas_generator` 38/38 + `test_oas_signatures` 11/11.
> ✅ **`JSON_PARAM_OVERRIDES` DONE (Phase A10):** `len(JSON_PARAM_OVERRIDES)` ≥ 2 (`imm04.create_commissioning.data` + `imm04.save_commissioning.fields`); generator tự khám phá tập param JSON-string qua AST (`json_param_count`=63 đếm động). `[ROADMAP]` còn lại 1 bảng: `RESPONSE_DATA_OVERRIDES` — QA test "mọi `list_*` endpoint có `RESPONSE_DATA_OVERRIDES` hoặc fallback `items[]`".

### D6 — ENRICH PLAN: ưu tiên imm00 / imm04 / imm12 (3 module trọng yếu)

**Quyết định (1 dòng):** spec **auto-gen phủ 100% 485 endpoint** ở mức cơ bản (path/method/param/envelope); **enrich thủ công** (mô tả nghiệp vụ + ví dụ + response-data $ref đầy đủ) theo lô, **ưu tiên imm00 → imm04 → imm12**.

| Lô | Module | Lý do ưu tiên | Nội dung enrich |
|---|---|---|---|
| 1 | **IMM-00** (111 ep) | Foundation — asset registry + QR scan + RBAC + audit; integrator chạm đầu tiên | `available_actions` shape (ADR-QR-SCAN-ACTION D2), envelope ví dụ, `list_assets` pagination + invariant `count==rows` (ADR-LIST-SCOPE) |
| 2 | **IMM-04** (34 ep) | Installation/Commissioning — nhiều form_dict + JSON-string (F5: 4 union) → cần body-bridge rõ nhất | `create_commissioning`/`report_nonconformance`/`submit_baseline_checklist` JSON body schema, IQ/OQ/PQ checklist |
| 3 | **IMM-12** (16 ep) | Corrective/Incident — báo cáo sự cố NĐ98 Art.67, SLA, gate CAPA IMM-16 | incident lifecycle, severity enum, SLA field, `[ROADMAP]` cho phần report-failure (xem `../imm-12/ADR-IMM12-REPORT-FAILURE.md`) |

Mỗi lô enrich → cập nhật `OPERATION_META` (D5) + bồi mô tả vào `05_API_Specification.md` của module tương ứng (cross-link spec↔code). Lô 4+ (các module còn lại) = `[ROADMAP]`.

> Đo được: sau lô 1, mọi endpoint imm00 trong spec có `summary` + `description` non-empty + ≥1 ví dụ. QA test "imm00 operations đều có description".

#### D6-ENRICH — Hợp đồng thực thi (Phase A6 — registry-driven, đo được)

> **GATE-trùng (KHÔNG re-chốt):** ADR này đã **Accepted 2026-06-09**; D1–D5 đã DONE+GREEN trên đĩa (`test_oas_generator` 38/38 + `test_oas_signatures` 11/11). Phần D6-ENRICH dưới đây **lấp slot `[ROADMAP D6]`** của `OPERATION_META` (D5#3) thành spec thực thi — **KHÔNG đổi** path/operationId/security/verb/envelope đã chốt. Phạm vi vòng = **CHỈ D6 enrich**; D7 serve / D8 stats / Swagger UI = vòng sau.

**E0 — Nguồn DUY NHẤT = `openapi_overrides.OPERATION_META`** (KHÔNG hardcode trong `openapi.py`, KHÔNG sửa chữ ký/business code BE).

```python
# openapi_overrides.py — bảng enrich (op_tail '<module>.<fn>' → metadata).
OPERATION_META: dict[str, dict] = {
    "imm00.create_asset": {
        "summary": "Tạo tài sản (thiết bị y tế) mới",
        "description": "Đăng ký AC Asset mới vào registry. Sinh QR-token + lifecycle event. "
                       "Mã tài sản = định danh (asset_code == name).",
        "tags": ["IMM-00"],
        "examples": {
            "request": {"asset_category": "CAT-0001", "asset_name": "Máy siêu âm GE Logiq E10"},
            "response": {"name": "TS-2025-USG-001", "asset_name": "Máy siêu âm GE Logiq E10",
                          "lifecycle_status": "Đang hoạt động"},
            "errors": {
                "FORBIDDEN": "Bạn không có quyền tạo tài sản",
                "VALIDATION": "Thiếu trường bắt buộc: Tên tài sản",
            },
        },
    },
    # imm04.create_commissioning, imm12.report_incident, … (xem 05_API_Specification.md mỗi module)
}
```

| Khoá entry | Bắt buộc | Generator dùng vào |
|---|---|---|
| `summary` | ✅ | `operation['summary']` — ghi đè default docstring (đảm bảo `len>0`) |
| `description` | ✅ | `operation['description']` — ghi đè (đảm bảo `len>0`) |
| `tags` | tùy | `operation['tags']` (mặc định `[mod_short]` nếu vắng) |
| `examples.request` | ✅ với POST enriched | `requestBody.content['application/json'].example` |
| `examples.response` | ✅ | response `200` → `content['application/json'].examples['success'].value = {success:true, data:<mẫu>}` |
| `examples.errors` | ✅ | mỗi mã lỗi → 1 response (status từ `_HTTP_FOR_CODE[code]`) trỏ `ErrorEnvelope` + `example = {success:false, error:<VI>, code, http_status}` |

**E1 — DẪN XUẤT, KHÔNG hardcode (mutation-test có răng).** Generator thêm hàm `_enrich_operation(op_tail, operation, request_body)` đọc `_ovr.OPERATION_META.get(op_tail)`. Thêm 1 entry → spec phản ánh ngay; xoá entry → op quay về default D1-D5 (fail-safe). KHÔNG nhúng chuỗi enrich nào trong `openapi.py`.

**E2 — Ví dụ REQUEST khớp schema (POST).** Với mỗi POST enriched: `example` đặt trong `requestBody.content['application/json']`. Ràng buộc đo được: `set(example.keys()) ⊆ set(schema.properties.keys())` (D4/D5 schema) **VÀ** mọi field trong `schema.required` PHẢI có mặt trong `example`. Giá trị enum (vd `severity: "Critical"`, `incident_type: "Failure"`) = **giá trị Select canonical của DocType** (hợp đồng API thật) — KHÔNG phải status-pill UI, KHÔNG bị quy tắc no-EN ở E4.

**E3 — Ví dụ RESPONSE = envelope-success SSoT (KHÔNG khai lại shape).** Response `200` VẪN `$ref: '#/components/schemas/SuccessEnvelope'` (D3 SSoT — `data:{}` giữ nguyên). Enrich **chỉ THÊM** `examples.success.value = {success: true, data: <mẫu thực tế>}`. KHÔNG đổi `SuccessEnvelope`, KHÔNG sinh schema `data` thứ 2.

**E4 — ERROR-responses VI sạch (no-leak).** Mỗi op enriched khai các mã lỗi áp dụng (vd `FORBIDDEN`/`VALIDATION`/`NOT_FOUND`/`RATE_LIMITED`) → mỗi mã 1 response key = `str(_HTTP_FOR_CODE[code])` (vd `"403"`), schema `$ref ErrorEnvelope`, `example = {success:false, error:"<VI sạch>", code:"FORBIDDEN", http_status:403}`. Message VI lấy từ hằng BE thật khi có (`imm12._MSG_FORBIDDEN = "Không có quyền thực hiện hành động này"`, `_MSG_UNAUTHENTICATED = "Chưa đăng nhập"`). Cấm trong **error message** (KHÔNG áp lên request example field-enum ở E2):
- ❌ raw capability token kiểu `[a-z]+\.[a-z]+` (vd `corrective.create`, `calibration.create`) — leak quyền nội bộ.
- ❌ status tiếng Anh (`Active`/`Out of Service`/`Under Maintenance`/`Decommissioned`…).
- ❌ raw `qr_token` / email / serial / định-danh-chéo (PK asset khác).

**E5 — Mã lỗi ⊆ ErrorCode SSoT.** Mọi `code` trong `examples.errors` PHẢI ∈ `ErrorCode` enum (F2, sinh D3) và response-key PHẢI == `_HTTP_FOR_CODE[code]` (F3). KHÔNG bịa mã mới, KHÔNG bịa HTTP status.

**E6 — Import THUẦN (giữ ràng buộc D5).** `openapi_overrides.py` (gồm `OPERATION_META`) vẫn import-được không-DB ở module-level: `monkeypatch frappe.get_meta` raise → `import OPERATION_META` vẫn pass (bảng là dict tĩnh, không gọi `get_meta`/DB lúc import).

> **Đo được (acceptance Phase A6):**
> 1. Với MỌI endpoint thuộc 3 module (imm00/04/12) trong `generate_spec()`: `len(op['summary'])>0` **và** `len(op['description'])>0`.
> 2. Mutation: thêm entry `OPERATION_META[op_tail]` → spec đổi ngay; xoá → op về default (RED nếu generator hardcode).
> 3. Mỗi POST enriched: `set(example.keys()) ⊆ schema.properties` + `schema.required ⊆ example.keys()`.
> 4. Mỗi op enriched: response `200` ref `SuccessEnvelope` + có `example.success.value.ok-true` (≡ `success:true`); KHÔNG khai lại shape.
> 5. Regex quét MỌI error-message của 3 module: KHÔNG match `[a-z]+\.[a-z]+` (cap token) **và** KHÔNG chứa từ EN trạng thái (`Active|Out of Service|Under Maintenance|Decommissioned`).
> 6. Mọi `code` ∈ `ErrorEnvelope.code.enum` (D3) + http-status-key == `_HTTP_FOR_CODE[code]`.
> 7. `test_oas_generator` + `test_oas_signatures` xanh THẬT (`bench --site miyano run-tests`); KHÔNG vỡ TC-OAS-01..16 / SEC / OPID / ENV / DOCTYPE-MAP / COVERAGE hiện hữu.

**NON-GOAL D6:** KHÔNG đụng D7 serve / D8 stats / Swagger UI; KHÔNG sửa `response.py`; KHÔNG đổi path/operationId/security/verb; KHÔNG enrich module ngoài imm00/04/12 (lô 4+ = `[ROADMAP]`).

### D7 — SERVE SPEC: 1 whitelist GET `assetcore.api.openapi.spec` (session-gated, cached) + trang `www/api-docs.html`

**Quyết định (1 dòng):** spec phục vụ qua **đúng 1 endpoint** + **1 trang docs**, KHÔNG file tĩnh commit:

- **`@frappe.whitelist()` GET `assetcore.api.openapi.spec`** → trả `openapi.json` (3.1). **Session-gated** (KHÔNG `allow_guest` — F6 nguy cơ lộ bề mặt): `frappe.session.user != "Guest"` else 401. **Cached** qua `frappe.cache().get_value("ac_openapi_spec_v<hash>")` — generate 1 lần, bust khi `CAP_SET_VERSION`/app version đổi (giống pattern `ac_caps::*`). Trả **raw dict** (KHÔNG wrap envelope — đây LÀ spec, integrator/Swagger UI cần JSON OpenAPI thuần).
- **Trang `www/api-docs.html`** (precedent F9: `www/assetcore.html`) nhúng **Swagger UI** (hoặc Redoc — chốt **Swagger UI** vì có "Try it out" gọi live, hữu ích cho integrator; Redoc là tùy chọn read-only nếu cần) trỏ `url: '/api/method/assetcore.api.openapi.spec'`. Asset Swagger UI bundle **self-host** trong `assetcore/public/` (KHÔNG CDN ngoài — môi trường bệnh viện air-gapped).

> Đo được: `GET /api/method/assetcore.api.openapi.spec` (đã login) → `200` JSON `openapi: "3.1.0"`; cùng request là Guest → `401`. Trang `/api-docs` render Swagger UI list 485 operation. Lần gọi 2 hit cache (đo qua không re-introspect — log/timer).

### D8 — `openapi.json` 3.1 STRUCTURE + root `tags[]` + `x-assetcore-stats` (số liệu đo-tại-generate) ✅ **DONE (Phase A8)**

**Quyết định (1 dòng):** spec tuân OpenAPI **3.1.0**; nhúng root-level `tags[]` (mô tả VI per IMM-XX) + block `x-assetcore-stats` chứa số liệu đo-thật lúc generate (chống hardcode).

> **Trạng thái thực thi (2026-06-09 — Phase A8):** ✅ DONE+GREEN. `generate_spec()` chèn (sau `paths`):
> - **`tags`** (`openapi._root_tags(paths)`) — gom tập tag DUY NHẤT dùng ở mọi operation, map mỗi tag → mô tả VI qua **`openapi_overrides.tag_description_for`** (SSoT — KHÔNG khai lại map ở `openapi.py`), trả `list[dict]{name,description}` sort theo name. **No orphan-tag** (mọi tag dùng ở operation đều có entry) + no entry thừa. Swagger UI nhóm endpoint kèm mô tả VI.
> - **`x-assetcore-stats`** (`openapi._assetcore_stats(paths)`) — extension hợp lệ `x-*`, các khóa: `total_endpoints` (==len(paths)), `get_count`, `post_count` (get+post==total), `guest_count` (số operation trong `paths` có `security == []` — **D11**, xem chú thích dưới), `enriched_count` (số op `enrich_meta_for!=None` == op imm00/04/12), `cap_set_version` (==`rbac.CAP_SET_VERSION`, lazy-import), `generated_app_version` (==`_app_version()`). **MỌI counter của `x-assetcore-stats` đều DẪN XUẤT ĐỘNG TỪ `paths` dict đã sinh (rendered surface = SSoT) — KỂ CẢ `guest_count` (D11); KHÔNG hardcode magic number, KHÔNG đọc registry external (`frappe.guest_methods`/DB) lúc tính**, để tránh drift về sau từ nguồn ngoài.
> - **Trang `www/api-docs.html`** hiển thị banner thống kê đọc `x-assetcore-stats` từ spec ĐÃ TẢI (`window.ui.specSelectors.specJson()`, KHÔNG fetch riêng): "Tổng N endpoint · X GET · Y POST · Z công khai · M đã làm giàu tài liệu · phiên bản cap <v>". Text VI sạch, KHÔNG leak raw key EN. Fail-safe ẩn khi spec thiếu key.
> - Tests: **`tests/test_oas_d8_metadata.py`** (`TestOasD8RootTags`/`TestOasD8Stats`/`TestOasD8Validity`, TC-OAS-D8-01..06, 14/14 GREEN). Regression `test_oas_generator` 59 + `test_oas_signatures` 11 + `test_oas_serve` 9 GREEN (D1-D7 intact, _cached_spec serialize JSON OK với 2 key mới). KHÔNG đụng response.py/path/operationId/verb/security/requestBody/enrich đã chốt. **Backlog Phase A nay cạn (D1-D8 DONE).**
>
> ⚠️ Số liệu đo-thật biến thiên ĐỘNG (vd `total_endpoints=486` — KHÁC snapshot 485 cũ vì thêm endpoint `openapi.spec`/`generate_spec`). Test assert qua introspect động (`len(paths)`, đếm op `security==[]`), KHÔNG hardcode con số nào.
>
> **D11 (STATS-GUEST-SSOT, 2026-06-09):** `guest_count` TRƯỚC đây = `len(_guest_name_set())` (đọc global `frappe.guest_methods`) → registry này biến thiên theo worker-boot context / app cài kèm (trả **2/5/10** entry tuỳ context, gồm cả guest-method của Frappe core như `ping`/`web_search` không thuộc AssetCore) ⟹ `guest_count` lệch **10-vs-5** so với bề mặt guest THẬT mà spec phơi ra. Fix: `guest_count = sum(1 for item in paths.values() for op in item.values() if op.get('security') == [])` — DẪN XUẤT thuần từ `paths` đã sinh (CÙNG SSoT với `total/get/post/enriched`). Bề mặt guest = đúng **5** operation (`auth.register_user` / `auth.check_account_status` / `auth.account_state` + `layout.get_user_context` / `layout.ping_session`). `_guest_name_set()` GIỮ NGUYÊN là SSoT cho quyết định `is_guest` **per-operation** trong `_build_operation` (security==[] do đó) — CHỈ STAT counter đổi nguồn. Tests `tests/test_oas_d11_guest_stat.py` TC-OAS-D11-01..05 (6 test) GREEN; `test_oas_d8_metadata.py:194` re-point từ tautology `==len(_guest_name_set())` → đếm `security==[]`.
>
> **D12 (BASELINE-ERR-SURFACE, 2026-06-09) ✅ DONE (Phase A D12):** TRƯỚC D12, 325 op non-enriched chỉ phơi response `default` (ErrorEnvelope opaque) → integrator/Swagger UI KHÔNG biết op nào cần phiên (401) hay quyền (403); chỉ 161 op enriched (imm00/04/12) có status-coded error (curated D6). Fix: helper THUẦN `openapi._baseline_error_responses(is_guest)` DẪN XUẤT từ SSoT `_HTTP_FOR_CODE` + comment-SSoT `utils/response.py` (`ErrorCode.UNAUTHORIZED`=401 "Chưa đăng nhập hoặc phiên đã hết hạn"; `ErrorCode.FORBIDDEN`=403 "Đã đăng nhập nhưng không đủ quyền thực hiện") → trả `{'403': ErrorEnvelope-resp}` + (nếu KHÔNG guest) `{'401': ...}`. `_build_operation` MERGE baseline vào `operation['responses']` bằng **`setdefault`** (CHỈ key chưa tồn tại) NGAY TRƯỚC `_enrich_operation` ⟹ **baseline MERGE, curated WIN**: 161 op enriched giữ nguyên `examples` + status D6 (vd `report_incident` giữ 422 VALIDATION curated; `create_asset` chưa có 401 curated → baseline lấp 401 mà KHÔNG đè 403/422 đã có). Op AUTHED (`security==[{cookieSession:[]}]`) → 401+403; op GUEST (`security==[]`) → CHỈ 403 (không cần phiên → KHÔNG 401). Mô tả VI sạch (no EN-status, no cap-token `[a-z]+\.[a-z]+`, no email). `x-assetcore-stats` thêm `error_responses_typed_count` = đếm ĐỘNG số op có ≥1 response key `^[45]\d\d$` (helper `_is_4xx_5xx`). **Verify @source (2026-06-09):** 481 authed op ALL có 401+403 (trước = 2/15); 5 guest op có 0×401, 5×403; `error_responses_typed_count`=**486** (mọi op có ≥1 4xx — authed 401/403, guest 403); **0 dangling $ref**; `openapi==3.1.0`; total/get/post/guest/enriched/json_param/cap_set_version GIỮ NGUYÊN **486/236/250/5/161/63/v97**; key-order info→components→paths→tags→x-assetcore-stats giữ. Tests `tests/test_oas_d12_error_surface.py::TestOasD12ErrorSurface` TC-OAS-D12-01..06 (14 test) GREEN; regression `test_oas_generator` 49 + `test_oas_signatures` 11 + `test_oas_serve` 9 + `test_oas_d8_metadata` 14 + `test_oas_d9_tags` 14 + `test_oas_d10_json_params` 25 + `test_oas_d11_guest_stat` 6 GREEN (D1-D11 intact). KHÔNG đụng `_error_response_object`/`_enrich_operation` logic cốt lõi/`response.py`/path/operationId/verb/security/requestBody. Swagger UI (`www/api-docs.html`) render block 401/403 VI mỗi op sau USER reload (endpoint `spec` live status mới — blocker#1).
>
> **D13 (SERVERS-BLOCK, 2026-06-09) ▶️ Phase A D13 — Vòng 8 (SPEC-READY, bàn giao [BE]):** TRƯỚC D13, spec KHÔNG có root `servers[]` ⟹ Swagger UI **Try-it-out** + codegen mặc định resolve base URL từ **địa chỉ trang đang mở** (`window.location.origin`) — đúng ở dev trùng-host, NHƯNG **sai ở air-gapped / reverse-proxy / domain bệnh viện khác** (integrator gọi nhầm host, Try-it-out 404/CORS). Fix: chèn root `servers[]` **DẪN XUẤT ĐỘNG** từ SSoT `frappe.utils.get_url()` (site base) — đa-môi-trường, **KHÔNG hardcode host/URL**. **Quyết định cốt lõi (T1-T6):**
> - **T1 — Vị trí + thứ tự:** chèn key `servers` NGAY SAU `info` và TRƯỚC `components` ⟹ thứ tự root MỚI `openapi → info → **servers** → components → paths → tags → x-assetcore-stats`. `servers` là field root HỢP LỆ OpenAPI 3.1 (§4.8.5 spec) — spec vẫn valid. Mọi key D1-D12 GIỮ NGUYÊN giá trị + thứ tự tương đối.
> - **T2 — URL SSoT bare-origin:** `servers[0].url == frappe.utils.get_url()` — base site (vd `'http://miyano'` ở dev; verify @source 2026-06-09 `bench execute frappe.utils.get_url` = `"http://miyano"`). **BARE origin** (scheme://host[:port]) — **KHÔNG** kèm `'/api/method/'` (path-prefix `_PATH_PREFIX` ĐÃ nằm trong từng key của `paths` — kèm vào server URL sẽ nhân đôi tiền tố → URL sai), **KHÔNG** trailing slash thừa (get_url() không args trả host không slash cuối — §source data.py:1655 `return ... host_name` khi `uri` falsy). Đổi site/host (config Frappe / `host_name` / reverse-proxy header) → `servers[0].url` TỰ đổi lần generate kế (cache-busted theo `_spec_cache_key`).
> - **T3 — Description VI:** `servers[0].description` = chuỗi VI cố định `'Site hiện tại — dẫn xuất động từ cấu hình Frappe'` (mô tả nguồn gốc URL cho người đọc spec; KHÔNG leak EN/host literal).
> - **T4 — KHÔNG hardcode (anti-pattern P-NoHardcode):** logic `servers` CHỈ gọi `frappe.utils.get_url()` — **grep `openapi.py` KHÔNG thấy literal `http://` / `https://` / tên site cố định** trong nhánh build servers (chuỗi `"http://"` chỉ được phép XUẤT HIỆN nếu là trả về runtime của get_url(), KHÔNG viết tay). `_PATH_PREFIX` ('/api/method/') GIỮ chỉ dùng cho `paths`, KHÔNG ghép vào server URL.
> - **T5 — Fail-safe (generate_spec KHÔNG BAO GIỜ exception vì servers):** `get_url()` đọc `frappe.local.conf`/`frappe.local.site`/`frappe.db.get_single_value` (data.py:1605-1637) — ngữ cảnh **không-request / no-site / DB chưa sẵn** có thể raise HOẶC trả rỗng. Helper `_servers()` BỌC try/except: `url = get_url()`; nếu raise HOẶC `not url` (None/'') → fallback `[{'url': '/', 'description': 'fallback'}]` (URL **relative `'/'`** — hợp lệ OpenAPI 3.1 §4.8.5, resolve theo vị-trí-tài-liệu = chính origin phục vụ spec, đúng cho Swagger UI self-host `www/api-docs.html`). Đảm bảo `servers` LUÔN là list **NON-EMPTY ≥1 entry** trong MỌI ngữ cảnh (test / HTTP / bench execute). 486 endpoint vẫn sinh đủ.
> - **T6 — Bất biến stat:** `servers` KHÔNG phải operation ⟹ `x-assetcore-stats` (total/get/post/guest/enriched/error_responses_typed/json_param/cap_set_version) **KHÔNG đổi giá trị**; `enriched_count==161`, `total_endpoints==len(paths)==486` GIỮ NGUYÊN. `servers` cũng KHÔNG đụng `paths`/`components`/`tags`.
> - **Swagger UI consume native:** `www/api-docs.html` (Swagger UI self-host) đọc `servers[]` → tự hiện dropdown **'Servers'** với base URL đúng — **KHÔNG cần FE code mới** (Swagger UI native consume `servers[]`; verify-by-reasoning đủ, không cần live HTTP). Sau USER reload (blocker#1), endpoint `spec` HTTP trả spec có `servers[]` (cache-busted khi cap/app-version đổi qua `_spec_cache_key`).
> - **DELTA-BE (3 chỗ, bàn giao `assetcore-be`):** (a) helper THUẦN MỚI `openapi._servers() -> list[dict]` (try get_url() → bare-origin entry; except/falsy → fallback `'/'` entry; LUÔN ≥1 entry; docstring dẫn nguồn T2-T5). (b) `generate_spec()` return dict CHÈN `"servers": _servers()` GIỮA key `"info"` và `"components"` (Python dict giữ thứ tự chèn → key-order T1 đúng). (c) KHÔNG đụng `_build_operation`/`_assetcore_stats`/`_root_tags`/`_build_components`/`response.py`/`paths`. Tests: class MỚI `TestOasD13Servers` (TC-OAS-D13-01..06, xem D-TEST) — **THÊM**, KHÔNG đụng D1-D12.
> - **Verify @source (PM/BA read-only 2026-06-09):** `frappe.utils.get_url()` (no-args) = `"http://miyano"` (bare, no `/api/method/`, no trailing slash); `data.py:1599-1655` xác nhận trả `host_name` thuần khi `uri` falsy + có nhánh `frappe.db.get_single_value`/`frappe.local.site` ⟹ fail-safe cần thiết. `generate_spec()` hiện root-keys = `['openapi','info','components','paths','tags','x-assetcore-stats']` (chưa có `servers`); `total_endpoints=486`, `enriched_count=161`. **Acceptance đo được:** xem D-TEST TC-OAS-D13-01..06.

> **D14 (INFO-CONTACT-LICENSE, 2026-06-09) ✅ DONE (Phase A D14):** TRƯỚC D14, `info` chỉ có `title/version/description` ⟹ Swagger UI + codegen + integrator KHÔNG biết license/contact của API (OpenAPI 3.1 §4.8.2 khuyến nghị `info.license` + `info.contact`). Fix: bồi `info.contact` + `info.license` **DẪN XUẤT từ `hooks.py` app-metadata SSoT** qua `frappe.get_hooks(hook, app_name='assetcore')` (**APP-SCOPED** single-element list). **Quyết định cốt lõi (T1-T5):**
> - **T1 — APP-SCOPED SSoT bắt buộc:** derivation dùng `frappe.get_hooks(hook, app_name='assetcore')` (trả `['miyano']`/`['MIT']`/`['']` — single-element, ổn định) — **KHÔNG** dùng `get_hooks(hook)` merged (trả list gom MỌI app cài kèm, vd `app_publisher` merged = `['Frappe Technologies','miyano','MiyanoSoft']` ⟹ index `[0]` KHÔNG ổn định, lấy nhầm publisher của Frappe core). Helper `_app_meta_hook(hook)` bọc app-scoped get_hooks → `[0].strip()` non-empty hoặc None.
> - **T2 — `info.license` (SPDX 3.1):** `_info_license()` → `{'name': spdx, 'identifier': spdx}` với `spdx = _app_meta_hook('app_license')` (hiện `'MIT'`). `identifier` là field SPDX **MỚI** của OpenAPI 3.1; `identifier==name` vì hooks chỉ có 1 field license. **KHÔNG** kèm `'url'` khi thiếu — 3.1 **cấm** có CẢ `identifier` lẫn `url` (chọn `identifier`). spdx rỗng → None (KHÔNG license rỗng).
> - **T3 — `info.contact` + email fail-safe:** `_info_contact()` → `name = _app_meta_hook('app_publisher')` (hiện `'miyano'`); `email = _app_meta_hook('app_email')` (hiện `''` rỗng); url = None (chưa có hook chuẩn). Build dict CHỈ chứa key non-None: luôn `{'name':...}` + tùy chọn `'email'` **khi app_email non-empty** (app_email=='' ⟹ **OMIT** key 'email' — KHÔNG leak `'email':''`). name rỗng → None (KHÔNG contact rỗng). Nếu sau này `app_email` non-empty ⟹ `contact.email` = giá trị đó (cùng quy tắc omit cho `license.url` nếu thiếu).
> - **T4 — KHÔNG hardcode (anti-pattern P-NoHardcode):** logic build info CHỈ đọc qua `_app_meta_hook` — **grep `openapi.py` vùng build info KHÔNG có chuỗi literal `'MIT'`/`'miyano'`** (đọc qua hook). `_app_meta_hook` fail-safe: hook vắng / list rỗng / None / bất kỳ exception (ngữ cảnh không-app / test) → None (**KHÔNG raise** — giống `_servers()`/`_app_version()`); `generate_spec` chèn CÓ ĐIỀU KIỆN (helper None → bỏ qua, KHÔNG sinh dict rỗng).
> - **T5 — info giữ nguyên + bất biến:** `info` GIỮ `title=='AssetCore API'` + `version==_app_version()` + `description` ('Auto-generated...'); chỉ THÊM 2 subkey `contact`+`license` (sau `description`). Thứ tự top-level key `info→servers→components→paths→tags→x-assetcore-stats` **BẤT BIẾN** (D13 order); `x-assetcore-stats` (total/get/post/guest/enriched/error_responses_typed/json_param/cap_set_version) + `servers[]` (D13) **BẤT BIẾN** (info ≠ operation ≠ path). `contact`/`license` là **subkey của info**, KHÔNG top-level.
> - **DELTA-BE (2 chỗ):** (a) 3 helper THUẦN MỚI `openapi._app_meta_hook(hook)` / `_info_contact()` / `_info_license()` (type hint + docstring VI). (b) `generate_spec()` dựng `info` dict rồi chèn CÓ ĐIỀU KIỆN `contact` (nếu `_info_contact()` non-None) + `license` (nếu `_info_license()` non-None) sau `description`; vị trí `info` GIỮ NGUYÊN (trước `servers`). KHÔNG đụng `_build_operation`/`_assetcore_stats`/`_root_tags`/`_build_components`/`_servers`/`response.py`/`paths`. Tests: class MỚI `TestOasD14*` (TC-OAS-D14-01..07) — **THÊM**, KHÔNG đụng D1-D13.
> - **Verify @source (2026-06-09 `bench --site miyano console`):** `get_hooks('app_publisher', app_name='assetcore')` = `['miyano']`; `app_license` = `['MIT']`; `app_email` = `['']`; MERGED `app_publisher` = `['Frappe Technologies','miyano','MiyanoSoft']` (chứng minh phải app-scope). `generate_spec()['info']` = `{'title':'AssetCore API','version':'0.0.3','description':'Auto-generated...','contact':{'name':'miyano'},'license':{'name':'MIT','identifier':'MIT'}}` (contact KHÔNG có 'email'; license KHÔNG có 'url'); top-level order = `['openapi','info','servers','components','paths','tags','x-assetcore-stats']` (bất biến); `x-assetcore-stats` = `486/236/250/5/161/486/63/v97.c30c69b8974d` (bất biến vs D12/D13); `servers[0]` = `{'url':'http://miyano',...}` (bất biến); `openapi=='3.1.0'`. Tests `tests/test_oas_d14_info_meta.py::TestOasD14*` TC-OAS-D14-01..07 (10 test) GREEN; regression `test_oas_generator` + `test_oas_signatures` 11 + `test_oas_serve` 9 + `test_oas_d8_metadata` 14 + `test_oas_d9_tags` 14 + `test_oas_d10_json_params` 25 + `test_oas_d11_guest_stat` 6 + `test_oas_d12_error_surface` 14 + `test_oas_d13_servers` 15 GREEN (D1-D13 intact). Swagger UI native render block 'License'/'Contact' ở header sau USER reload (endpoint `spec` live — blocker#1). **Backlog Phase A nay cạn (D1-D14 DONE).**

> ⚠️ **SELF-CORRECTION (D16 supersedes — 2026-06-09):** **doc-base SSoT của D15 (= `frappe.utils.get_url()`) LÀ LỖI THIẾT KẾ GỐC** và đã được **§D16 (DOCBASE-FIX) bên dưới** sửa. `get_url()` trả **API origin** (vd `http://miyano`) — KHÔNG phải nơi tài liệu markdown được web-served (`docs/` chỉ tồn-tại-trong-repo, KHÔNG serve HTTP @8000) ⟹ MỌI `externalDocs.url` D15 sinh ra (root + 23 tag) là **DEAD LINK 404** ở trình duyệt bệnh viện. D16 chuyển doc-base sang hooks **`app_docs_url`** (app-scoped, cấu hình được) + **graceful-omit** khi chưa cấu hình (OMIT externalDocs HẲN thay vì fabricate link chết). **Đọc T1-T7 D15 dưới với lăng kính D16:** phần *contract/key-order/fail-safe/no-hardcode/regression* GIỮ NGUYÊN; CHỈ **nguồn doc-base** (T1) + **hành vi khi vắng cấu hình** (T2/T6) bị D16 ghi đè. T3/T4 path-mapping (`docs/imm-XX/README.md`) GIỮ NGUYÊN — chỉ đổi base-URL phía trước.
>
> **D15 (EXTERNALDOCS, 2026-06-09) ▶️ Phase A D15 — Vòng 10 (SPEC-READY, bàn giao [BE]):** TRƯỚC D15, spec KHÔNG có `externalDocs` ở **root** lẫn **per-tag** ⟹ Swagger UI/Redoc + integrator KHÔNG có liên kết "đọc thêm tài liệu" từ API doc về tài liệu module người-đọc (`docs/imm-XX/README`). OpenAPI 3.1 §4.8.11 (`externalDocs` = `{url, description}`) cho phép field này ở **root spec** (1 link tổng quát) **và** ở **mỗi tag** (`tags[].externalDocs` §4.8.22) → Swagger UI hiển thị icon "📖" cạnh tên tag, mở doc module tương ứng. Fix: bồi (a) root `externalDocs` + (b) per-tag `externalDocs` cho cả 23 tag, **DẪN XUẤT động từ doc-base-URL** từ SSoT `frappe.utils.get_url()` (CÙNG pattern D13 servers) — KHÔNG hardcode host/URL literal. **Quyết định cốt lõi (T1-T7):**
>
> - **T1 — Doc-base-URL SSoT (CÙNG nguồn D13):** base = `frappe.utils.get_url()` (bare-origin site, vd `'http://miyano'`). KHÔNG hardcode host. **Fail-safe (T6):** get_url() raise/rỗng → fallback **relative** (KHÔNG có host) ⟹ root `externalDocs.url` = `'/'` (hoặc relative doc-path), per-tag `externalDocs.url` = relative doc-path (vd `'docs/imm-00/README.md'` không leading-host) — generate_spec() **KHÔNG bao giờ raise vì externalDocs** (giống `_servers()`/`_app_meta_hook()`). Một helper THUẦN `_doc_base()` trả `(base_or_None)`: `try get_url() → rstrip('/')`; except/falsy → None ⟹ caller dùng relative.
>
> - **T2 — Root `externalDocs`:** `{url, description}` với `description` = chuỗi VI cố định non-empty `'Tài liệu phát triển AssetCore (docs/) — kiến trúc, module IMM, tuân thủ NĐ98/WHO HTM'`; `url` **DẪN XUẤT động**: nếu base có → `f"{base}/{_DOC_ROOT_PATH}"` (vd `'http://miyano/docs/imm-00/README.md'` trỏ README nền tảng IMM-00 = entry-point doc — KHÔNG file ngoài site, KHÔNG CDN); nếu base None → relative `_DOC_ROOT_PATH` (vd `'docs/imm-00/README.md'`). `_DOC_ROOT_PATH = "docs/imm-00/README.md"` (IMM-00 là foundation doc — landing tài liệu). url LUÔN NON-EMPTY (pattern path hợp lệ ở mọi ngữ cảnh).
>
> - **T3 — Per-tag `externalDocs` — 13 tag IMM-XX → `docs/imm-XX/README`:** mỗi tag canonical `"IMM-XX"` → doc-slug `imm-XX` (lower-case mã + dấu gạch: `"IMM-00"→"imm-00"`, `"IMM-16"→"imm-16"`). DẪN XUẤT path `f"docs/{slug}/README.md"`; url = `f"{base}/{path}"` (base có) hoặc relative `path` (base None). **14/14 README đã tồn tại** cho imm00..imm16 (verify @source 2026-06-09 — kể cả imm07/10/13 ngoài 13 tag có-endpoint, README VẪN có → an toàn). `description` = `f"Tài liệu module {tag}"` (vd `'Tài liệu module IMM-00'`) — VI non-empty, KHÔNG leak slug raw lowercase. Helper SSoT `tag_doc_path(tag) -> str` trong `openapi_overrides.py` (mapping canonical-tag → relative doc-path, CÙNG nơi `canonical_tag`/`tag_description_for`).
>
> - **T4 — Per-tag `externalDocs` — 9 tag cross-cut → doc chung:** 9 domain-VI tag ('Xác thực','Bảng điều khiển','Nhập liệu','Kho','Bố cục','Thông báo','Mua sắm','Người dùng','Tài liệu API') KHÔNG có module `docs/imm-XX/` riêng ⟹ TRỎ **doc chung** `_DOC_ROOT_PATH` (`docs/imm-00/README.md` — README IMM-00 nền tảng/cross-cutting, mô tả cả layer cross-cut). `tag_doc_path(<cross-cut-tag>)` trả `_DOC_ROOT_PATH`. `description` = `f"Tài liệu chung — {tag}"` (vd `'Tài liệu chung — Xác thực'`). ⟹ **0 tag thiếu externalDocs** (cả 23 tag có `{url, description}`), mọi url resolve được (đúng pattern path). `tag_doc_path` cho tag lạ → fallback `_DOC_ROOT_PATH` (KHÔNG vỡ, KHÔNG leak).
>
> - **T5 — Vị trí chèn (key-order canonical):** root `externalDocs` chèn **SAU `tags` và TRƯỚC `x-assetcore-stats`** ⟹ thứ tự root MỚI `openapi → info → servers → components → paths → tags → **externalDocs** → x-assetcore-stats`. *(Lý do: OpenAPI 3.1 §4.8 KHÔNG ép thứ tự root key; đặt `externalDocs` cạnh `tags` vì ngữ nghĩa gần — cùng là metadata-điều-hướng; giữ `x-assetcore-stats` cuối cùng như mọi bản trước.)* Per-tag `externalDocs` là **subkey của mỗi phần tử `tags[]`** (sau `description`): `{name, description, externalDocs}` — `_root_tags` bồi key thứ 3 cho mỗi tag.
>
> - **T6 — Fail-safe (generate_spec KHÔNG BAO GIỜ raise vì externalDocs):** mọi đường dẫn dùng `_doc_base()` (try get_url → except/falsy → None). base None ⟹ url relative (vẫn NON-EMPTY, pattern path hợp lệ §4.8.11). Helper `_doc_url(rel_path)` ghép `f"{base}/{rel}"` khi base có, else trả `rel`. KHÔNG nhánh nào raise. Root + 23 tag LUÔN có `externalDocs` ≥1 cách (host-based hoặc relative) trong MỌI ngữ cảnh (test/HTTP/bench execute). 486 endpoint sinh đủ.
>
> - **T7 — Bất biến D1-D14 (regression):** `externalDocs` là field **root + tag-level** — KHÔNG phải operation/path/component ⟹ `x-assetcore-stats` (total/get/post/guest/enriched/error_responses_typed/json_param/cap_set_version) **KHÔNG đổi giá trị** (486/236/250/5/161/486/63/v97 + app_version 0.0.3); `info` (title/version/description/contact/license) + `servers[]` + `components` + `paths`/operationId/verb/security/requestBody/responses + root `tags` **name+description** (D8/D9 — chỉ THÊM subkey `externalDocs`, KHÔNG đổi name/description) BẤT BIẾN; `openapi=='3.1.0'`; 0 dangling $ref. `enriched_count==161`, `total_endpoints==len(paths)==486` GIỮ.
>
> - **No-hardcode guard (P-NoHardcode):** logic externalDocs CHỈ gọi `_doc_base()` (= get_url()) cho host — **grep vùng build externalDocs (`_doc_base`/`_doc_url`/root externalDocs/per-tag) KHÔNG có literal `http://`/`https://`/tên-site-cố-định** (host chỉ đến từ runtime get_url()). Relative doc-path (`docs/imm-XX/README.md`) là path-segment hợp lệ — KHÔNG phải host literal. Mutation: mock get_url trả host khác → MỌI externalDocs.url đổi theo host (chứng minh dẫn-xuất-động).
>
> - **Swagger UI/Redoc consume native:** cả 2 renderer đọc root `externalDocs` (link "📖 …" dưới info) + tag-level `externalDocs` (icon cạnh tên nhóm tag) → **KHÔNG cần FE code mới** (native consume; verify-by-reasoning đủ). Sau USER reload (blocker#1), endpoint `spec` HTTP trả spec có externalDocs.
>
> - **DELTA-BE (bàn giao `assetcore-be` — bám file hiện tại):**
>   - **(a) `openapi_overrides.py` — helper SSoT MỚI `tag_doc_path(tag: str) -> str`:** trả **relative doc-path** cho 1 canonical tag. `"IMM-XX"` → `f"docs/imm-{tag.split('-',1)[1].strip().lower()}/README.md"` (vd `"IMM-00"→"docs/imm-00/README.md"`); tag ∈ `_CROSSCUT_TAG_MAP.values()` (9 domain-VI) → `_DOC_ROOT_PATH` (`"docs/imm-00/README.md"`); tag lạ → `_DOC_ROOT_PATH` (fallback, KHÔNG vỡ). Hằng `_DOC_ROOT_PATH = "docs/imm-00/README.md"` (module-level). Type hint + docstring VI dẫn nguồn T3/T4. **KHÔNG** chứa host literal (relative thuần).
>   - **(b) `openapi.py` — 2 helper THUẦN MỚI:** `_doc_base() -> str | None` (try `frappe.utils.get_url().rstrip('/')`; except/falsy → None — CÙNG khuôn `_servers()`); `_doc_url(rel_path: str) -> str` (`base=_doc_base()`; `return f"{base}/{rel_path}" if base else rel_path` — LUÔN non-empty). Hằng VI module-level: `_EXTERNALDOCS_ROOT_DESC_VI` (T2), helper `_external_docs_root() -> dict` trả `{'url': _doc_url(_ovr._DOC_ROOT_PATH or "docs/imm-00/README.md"), 'description': _EXTERNALDOCS_ROOT_DESC_VI}`. *(Lưu ý: `_DOC_ROOT_PATH` ở overrides — generator import `_ovr` sẵn; hoặc nhân bản hằng path ở openapi.py với comment SSoT-tại-overrides để tránh import-cycle — chọn 1, miễn 1 SSoT path.)*
>   - **(c) `openapi.py:_root_tags` — bồi subkey `externalDocs` cho mỗi tag entry:** đổi dict-comprehension `{'name':tag,'description':...}` → thêm `'externalDocs': {'url': _doc_url(_ovr.tag_doc_path(tag)), 'description': _tag_external_desc_vi(tag)}`. Helper `_tag_external_desc_vi(tag)`: IMM-XX → `f"Tài liệu module {tag}"`; cross-cut → `f"Tài liệu chung — {tag}"`. (Hoặc đặt description-builder ở overrides cạnh `tag_doc_path` — 1 SSoT.) Sort theo `name` GIỮ NGUYÊN (externalDocs là subkey, KHÔNG đổi name/description/sort order ⟹ T7).
>   - **(d) `openapi.py:generate_spec` — chèn root `"externalDocs": _external_docs_root()` GIỮA key `"tags"` và `"x-assetcore-stats"`** (Python dict giữ thứ tự chèn → key-order T5 đúng). KHÔNG đụng `_build_operation`/`_assetcore_stats`/`_servers`/`_build_components`/`_info_*`/`response.py`/`paths`/`components`.
>   - Tests: class MỚI `TestOasD15ExternalDocs` (file mới `tests/test_oas_d15_external_docs.py`, TC-OAS-D15-01..07, xem D-TEST) — **THÊM**, KHÔNG đụng D1-D14.
>
> - **Verify @source (PM/BA read-only 2026-06-09):** `frappe.utils.get_url()` = `"http://miyano"` (bare); `generate_spec()` root-keys hiện = `['openapi','info','servers','components','paths','tags','x-assetcore-stats']` (CHƯA có `externalDocs`); 23 root tag (14 `IMM-XX` + 9 domain-VI) — **0 tag có externalDocs**; 14/14 README `docs/imm-00..16/README.md` TỒN TẠI (kể cả imm07/10/13); `x-assetcore-stats` = `486/236/250/5/161/486/63/v97.c30c69b8974d` + app_version `0.0.3`. **Acceptance đo được:** xem D-TEST TC-OAS-D15-01..07. Sau impl: root `externalDocs.url`=`'http://miyano/docs/imm-00/README.md'`, 23 tag mỗi tag có `externalDocs` (IMM-XX trỏ doc tương ứng, cross-cut trỏ `docs/imm-00/README.md`); key-order MỚI `...→tags→externalDocs→x-assetcore-stats`. **Backlog Phase A: D1-D15 (D15 thêm externalDocs).**

```json
{
  "openapi": "3.1.0",
  "info": { "title": "AssetCore API", "version": "<app version>",
            "description": "Auto-generated từ @frappe.whitelist — KHÔNG sửa tay",
            "contact": { "name": "<app_publisher hook>" },
            "license": { "name": "<app_license hook>", "identifier": "<app_license hook>" } },
  "servers": [ { "url": "<frappe.utils.get_url()>",
                 "description": "Site hiện tại — dẫn xuất động từ cấu hình Frappe" } ],
  "components": { "schemas": { "SuccessEnvelope": {...}, "ErrorEnvelope": {...}, "<DocType-shapes>": {...} },
                  "securitySchemes": { "cookieSession": { "type": "apiKey", "in": "cookie", "name": "sid" } } },
  "paths": { "/api/method/assetcore.api.<mod>.<fn>": { "get|post": {...} } },
  "tags": [ { "name": "IMM-00", "description": "...",
              "externalDocs": { "url": "<base>/docs/imm-00/README.md", "description": "Tài liệu module IMM-00" } },
            { "name": "Xác thực", "description": "...",
              "externalDocs": { "url": "<base>/docs/imm-00/README.md", "description": "Tài liệu chung — Xác thực" } }, ... ],
  "externalDocs": { "url": "<base>/docs/imm-00/README.md (D15 — get_url() SSoT, fail-safe relative)",
                     "description": "Tài liệu phát triển AssetCore (docs/) — kiến trúc, module IMM, tuân thủ NĐ98/WHO HTM" },
  "x-assetcore-stats": { "total_endpoints": 486, "get_count": 236, "post_count": 250,
                          "guest_count": 5, "enriched_count": 161,
                          "error_responses_typed_count": 486, "json_param_count": 63,
                          "cap_set_version": "<vNN.hash>", "generated_app_version": "<app version>" }
}
```

> **Thứ tự key root (D15):** `openapi → info → servers → components → paths → tags → externalDocs → x-assetcore-stats` (D15 chèn `externalDocs` SAU `tags`, TRƯỚC `x-assetcore-stats` — T5; D13 servers chèn SAU info, TRƯỚC components). Skeleton trên đã sắp đúng thứ tự thực thi; các giá trị `x-assetcore-stats` là số đo-thật 2026-06-09 (biến thiên động — test KHÔNG hardcode). Root `externalDocs` + per-tag `externalDocs` đều dẫn xuất `frappe.utils.get_url()` (fail-safe relative khi lỗi).
>
> Đo được: `x-assetcore-stats.total_endpoints == grep -c '@frappe.whitelist'`. `servers` non-empty ≥1 entry; `servers[0].url == frappe.utils.get_url()` (bare origin, no `/api/method/`, no trailing slash). Spec valid theo openapi-spec-validator 3.1 (QA chạy validator → 0 error).

---

### D16 — DOCBASE-FIX: doc-base SSoT chuyển `get_url()` → hooks `app_docs_url` (cấu hình được) + GRACEFUL-OMIT khi chưa cấu hình ▶️ **Phase A D16 — Vòng 11 (SPEC-READY, bàn giao [BE])**

> **Bản chất:** **Self-Correction** sửa lỗi-thiết-kế-gốc của §D15 (doc-base lấy nhầm từ `get_url()` = API origin → dead link). KHÁC D15: D15 **THÊM** externalDocs (link tài liệu) — đúng ý tưởng; D16 **SỬA nguồn doc-base** + **graceful omit** (link chết tệ hơn không link). **KHÔNG đụng** path/operationId/verb/security/responses/requestBody/servers/info/x-assetcore-stats/per-tag-path-mapping (`docs/imm-XX/README.md`) — **CHỈ** đổi base-URL phía trước externalDocs + thêm nhánh OMIT.

**ROOT-CAUSE BUG (USER eval Vòng 10 P1, verified live `bench --site miyano execute generate_spec` 2026-06-09):**
- Root `externalDocs.url` = `"http://miyano/docs/imm-00/README.md"` + **23/23 tag** cùng base `http://miyano/docs/imm-XX/README.md` ⟹ **TẤT CẢ là DEAD LINK 404**.
- **Vì sao chết:** `frappe.utils.get_url()` trả **API/site origin** (`http://miyano` = nơi serve `/api/method/...`, Frappe web @8000). Tài liệu markdown `docs/imm-XX/README.md` **CHỈ tồn tại trong repo Git** — KHÔNG được web-served bởi Frappe (KHÔNG route `www/`, KHÔNG static-serve). Trình duyệt integrator/bệnh viện mở link → **404**. Doc-base ≠ API-base về bản chất ngữ nghĩa (D15 T1 nhầm khi tái dùng SSoT D13 servers).
- **Hệ quả:** spec hứa "đọc thêm tài liệu" nhưng mọi liên kết gãy → tệ hơn không có externalDocs (Swagger UI render icon 📖 dẫn tới 404 = mất niềm tin integrator + lộ host nội bộ trong URL chết).

**5 câu hỏi domain (assetcore-doc Phần 2):** (1) **WHO HTM stage:** cross-cutting IMM-00 (API platform). (2) **NĐ98:** không mandate trực tiếp; externalDocs đúng củng cố truy xuất tài liệu cho audit/đấu thầu — link chết phản tác dụng. (3) **Stakeholder:** integrator HIS/EMR, đối tác đấu thầu đọc spec, QA. (4) **Lifecycle event:** không (introspection read-only). (5) **Hậu quả nếu data sai:** link 404 → integrator mất niềm tin + lộ host nội bộ → D16 thà OMIT còn hơn fabricate.

#### Quyết định cốt lõi (T1-T7 — DỨT KHOÁT, đo được)

> - **T1 — Doc-base SSoT MỚI = hooks `app_docs_url` (app-scoped, KHÔNG `get_url()`):** doc-base DẪN XUẤT từ `frappe.get_hooks('app_docs_url', app_name='assetcore')` — **CÙNG pattern D14** (`app_publisher`/`app_license`/`app_email` app-scoped single-element, qua `_app_meta_hook`). `app_docs_url` trỏ nơi tài liệu **THỰC SỰ web-served**: published docs site (vd `https://docs.assetcore.vn`) HOẶC Git browse base (vd `https://github.com/<org>/assetcore/tree/master`). **TUYỆT ĐỐI KHÔNG dùng `frappe.utils.get_url()` cho doc-base nữa** (đó là API origin — chỉ đúng cho D13 `servers[]`, KHÔNG cho doc-base). `_doc_base()` đổi nguồn: `_app_meta_hook('app_docs_url')` (strip, non-empty hoặc None) — KHÔNG còn gọi `get_url()`.
>
> - **T2 — Khi `app_docs_url` ĐƯỢC cấu hình (non-empty):** ghép base-URL ĐÚNG nơi docs sống:
>   - Root `externalDocs.url` == `<docs_base>/docs/imm-00/README.md`.
>   - Mỗi tag `IMM-XX` → `<docs_base>/docs/imm-XX/README.md` (path-mapping D15 T3 GIỮ NGUYÊN).
>   - 9 tag cross-cut → `<docs_base>/docs/imm-00/README.md` (D15 T4 GIỮ NGUYÊN).
>   - `<docs_base>` = `app_docs_url` đã `.rstrip('/')`. **KHÔNG còn literal `'http://miyano'` / `get_url()` origin** trong BẤT KỲ `externalDocs.url` nào. Key-order present = §D15 T5 (`...→tags→externalDocs→x-assetcore-stats`).
>
> - **T3 — Khi `app_docs_url` VẮNG / rỗng / None (MẶC ĐỊNH HIỆN TẠI — hooks chưa khai `app_docs_url`): GRACEFUL-OMIT externalDocs HẲN.**
>   - **Root** `externalDocs` key **VẮNG HẲN** khỏi spec (KHÔNG `externalDocs: None`, KHÔNG `externalDocs` rỗng, KHÔNG fabricate URL relative/404).
>   - **MỌI tag (0/23)** KHÔNG có subkey `externalDocs` — `tags[]` entry = `{name, description}` (như TRƯỚC D15).
>   - **Lý do (anti-pattern):** link chết tệ hơn không link. Swagger UI/Redoc render **sạch không externalDocs** (không icon 📖 dẫn 404). KHÔNG fabricate URL relative (`docs/imm-XX/README.md` relative cũng 404 ở browser vì Frappe không serve `docs/`).
>   - ⚠️ **D16 ghi đè D15 T6 fail-safe-relative:** D15 fallback "url relative khi base lỗi" — D16 BỎ nhánh relative-fallback đó, thay bằng **OMIT** (vì relative cũng dead). Fail-safe MỚI = vắng-base → omit key (vẫn KHÔNG raise).
>
> - **T4 — Key-order BẤT BIẾN (2 nhánh):**
>   - **Present** (`app_docs_url` non-empty): `openapi → info → servers → components → paths → tags → externalDocs → x-assetcore-stats` (== D15 T5).
>   - **Omit** (mặc định): `openapi → info → servers → components → paths → tags → x-assetcore-stats` LIỀN (KHÔNG lỗ trống, KHÔNG key `externalDocs: None`). `generate_spec()` **KHÔNG raise** ở CẢ 2 nhánh.
>
> - **T5 — Bất biến tuyệt đối (anti-regression — CHỈ externalDocs đổi):**
>   - `servers[]` (D13) **VẪN dùng `get_url()`** — **ĐÚNG** vì là API base (Try-it-out/codegen gọi API origin). D16 KHÔNG đụng `_servers()`.
>   - `info.contact`/`info.license` (D14) BẤT BIẾN.
>   - `x-assetcore-stats` BẤT BIẾN: `486/236/250/5/161/486/63` + `cap_set_version v97.c30c69b8974d` + `generated_app_version 0.0.3`.
>   - root `tags` (D8) + canonical-tag (D9) name+description BẤT BIẾN (omit = bỏ subkey externalDocs; present = thêm subkey externalDocs với base đúng).
>   - `paths`/`operationId`/`security`/`responses`/`components`/`openapi=='3.1.0'`/0-dangling-$ref BẤT BIẾN.
>
> - **T6 — Fail-safe (generate_spec KHÔNG BAO GIỜ raise vì externalDocs):** `_doc_base()` bọc `_app_meta_hook('app_docs_url')` (đã fail-safe → None khi hook vắng/rỗng/exception, giống D14). base None → **OMIT** (T3) ⟹ KHÔNG nhánh nào raise. base non-empty → ghép URL (T2). 486 endpoint sinh đủ ở cả 2 nhánh.
>
> - **T7 — No-hardcode guard (P-NoHardcode):** logic externalDocs CHỈ đọc qua `_app_meta_hook('app_docs_url')` cho doc-base — **grep vùng build externalDocs KHÔNG có literal `http://`/`https://`/tên-site/'miyano'/`get_url`** (doc-base CHỈ đến từ hook `app_docs_url`). Mutation: set hook `app_docs_url='https://docs.example/'` → MỌI `externalDocs.url` đổi theo base mới + có mặt; gỡ hook → externalDocs OMIT hoàn toàn (chứng minh dẫn-xuất-động + graceful-omit).

#### DELTA-BE — đặc tả thay đổi chính xác cho [BE] (bám file hiện tại, KHÔNG để dev đoán)

> - **(a) `assetcore/api/openapi.py:_doc_base()` — ĐỔI NGUỒN từ `get_url()` → `_app_meta_hook('app_docs_url')`:**
>   - HIỆN TẠI (D15): `try: base = frappe.utils.get_url() except: base=None; return (base or '').rstrip('/')`.
>   - MỚI (D16): `base = _app_meta_hook('app_docs_url'); return base.rstrip('/') if base else ''` (hoặc trả `None`/`''` thống nhất — caller `_doc_url`/`_external_docs_root`/`_tag_external_docs` đọc rỗng = vắng cấu hình). `_app_meta_hook` đã fail-safe (D14) → KHÔNG cần try/except riêng. **Bỏ HẲN** `frappe.utils.get_url()` khỏi `_doc_base`. Docstring đổi: "doc-base từ hooks `app_docs_url` (web-served docs HOẶC Git browse base), KHÔNG `get_url()` (= API origin → dead link)".
>
> - **(b) `_doc_url(rel_path)` — BỎ relative-fallback, đổi semantic "base vắng → OMIT-signal":**
>   - HIỆN TẠI: `base = _doc_base(); return f"{base}/{rel}" if base else rel_path` (relative fallback — D15 T6).
>   - MỚI: caller QUYẾT ĐỊNH omit; `_doc_url` CHỈ ghép khi base có. Đề xuất: `_doc_url(rel_path) -> str | None`: `base=_doc_base(); return f"{base}/{rel_path}" if base else None`. (`None` = signal cho caller OMIT — KHÔNG còn trả relative path.)
>
> - **(c) `_external_docs_root() -> dict | None`:** `base có` → `{'url': _doc_url(_ovr._DOC_ROOT_PATH), 'description': _ROOT_EXTERNAL_DOCS_DESC_VI}`; `base vắng` (`_doc_url` trả None) → **return None**. Generator chèn CÓ ĐIỀU KIỆN (như D14 contact/license): `ed=_external_docs_root(); if ed is not None: spec['externalDocs']=ed` — đặt GIỮA `tags`↔`x-assetcore-stats` khi present; bỏ qua khi None (key VẮNG, key-order liền).
>
> - **(d) `_tag_external_docs(tag) -> dict | None`** + `openapi.py:_root_tags`: `base vắng` → mỗi tag entry = `{name, description}` (KHÔNG subkey externalDocs); `base có` → thêm `'externalDocs': {'url': _doc_url(_ovr.tag_doc_path(tag)), 'description': _ovr.tag_external_desc_for(tag)}`. Sửa `_root_tags`: build subkey externalDocs CÓ ĐIỀU KIỆN (`ed=_tag_external_docs(tag); if ed: entry['externalDocs']=ed`). `tag_doc_path`/`tag_external_desc_for` (overrides) GIỮ NGUYÊN (path-mapping D15 đúng).
>
> - **(e) `assetcore/api/generate_spec()`:** đổi `"externalDocs": _external_docs_root()` (vô điều kiện) → chèn CÓ ĐIỀU KIỆN GIỮA `tags` và `x-assetcore-stats` (Python dict giữ thứ tự chèn → key-order T4). **KHÔNG** đụng `_servers`/`_info_*`/`_assetcore_stats`/`_build_operation`/`_build_components`/`response.py`/`paths`.
>
> - **(f) `assetcore/hooks.py` — `app_docs_url` MẶC ĐỊNH KHÔNG khai (để OMIT là default):** D16 **KHÔNG thêm** `app_docs_url` vào hooks.py (giữ default omit — verify @source 2026-06-09: `get_hooks('app_docs_url', app_name='assetcore')` = `[]` rỗng). Khi triển khai có published-docs/Git-browse → USER/deploy thêm dòng `app_docs_url = "https://github.com/<org>/assetcore/tree/master"` (HOẶC site-config override nếu hook hỗ trợ) ⟹ externalDocs tự xuất hiện đúng base lần generate kế. *(Đây là điểm cấu hình triển khai — KHÔNG hardcode trong code.)*

#### Test-case TDD D16 (cập nhật `test_oas_d15_external_docs.py` cho omit-default + config-base)

> File `tests/test_oas_d15_external_docs.py` (D15) **CẬP NHẬT** (KHÔNG xoá — đổi semantic theo D16):
> - **TC-OAS-D16-01 (DEFAULT OMIT):** với hooks hiện tại (`app_docs_url` vắng) → `generate_spec()` **KHÔNG có key `'externalDocs'`** ở root; **MỌI tag (0/23) KHÔNG có subkey `externalDocs`**; key-order root == `[openapi,info,servers,components,paths,tags,x-assetcore-stats]` (externalDocs VẮNG, liền mạch). `generate_spec()` KHÔNG raise.
> - **TC-OAS-D16-02 (CONFIG-BASE present):** `mock`/monkeypatch `_app_meta_hook` (hoặc `frappe.get_hooks`) trả `app_docs_url='https://docs.example/'` → root `externalDocs.url == 'https://docs.example/docs/imm-00/README.md'`; tag `IMM-04` → `'https://docs.example/docs/imm-04/README.md'`; 9 cross-cut → `.../docs/imm-00/README.md`; **0/23 tag thiếu externalDocs**; key-order == `[...,tags,externalDocs,x-assetcore-stats]`.
> - **TC-OAS-D16-03 (NO get_url leak):** với config-base mock, **KHÔNG `externalDocs.url` nào** chứa `'http://miyano'` / kết quả `get_url()`; mutation `get_url` → host khác KHÔNG đổi externalDocs (chứng minh doc-base TÁCH khỏi API-base).
> - **TC-OAS-D16-04 (NO-HARDCODE):** source `_doc_base`/`_doc_url`/`_external_docs_root`/`_tag_external_docs`/`_root_tags` KHÔNG literal `http://`/`https://`/`'miyano'`/`get_url`; `_doc_base` reference `app_docs_url` (qua `_app_meta_hook`).
> - **TC-OAS-D16-05 (FAIL-SAFE):** `_app_meta_hook('app_docs_url')` raise/'' /None → OMIT (KHÔNG raise, KHÔNG fabricate); `len(paths)==486` (externalDocs vắng KHÔNG hụt endpoint).
> - **TC-OAS-D16-06 (INVARIANT D1-D15):** `x-assetcore-stats` == `486/236/250/5/161/486/63` + v97 + 0.0.3 BẤT BIẾN; `servers[0].url == frappe.utils.get_url()` (servers VẪN get_url — KHÔNG đổi); `info.contact/license` còn; `openapi=='3.1.0'`; 0 dangling $ref; root tags name+description == `tag_description_for` (bất biến). Test cũ assert "externalDocs always present" (D15 TC-OAS-D15-01..03/07) **đổi** thành conditional (present CHỈ khi config-base mock; default = omit). Fail-safe test D15 cũ ("relative fallback") **đổi** thành "omit fallback".
>
> **REGRESSION GREEN (BẮT BUỘC):** `test_oas_d15_external_docs` (cập nhật) + `test_oas_generator` 49 + `test_oas_signatures` 11 + `test_oas_d8_metadata..d14` + `test_oas_serve`. **Mobile suite KHÔNG đụng** (`test_mobile_oas`/`test_mobile_*` đọc `docs/mobile/openapi/*.yaml` thủ-công, KHÔNG đọc generator AssetCore → no-regress).

> **Verify @source (BA read-only 2026-06-09):** `bench execute generate_spec` → root `externalDocs.url` HIỆN TẠI = `"http://miyano/docs/imm-00/README.md"` (BUG — get_url origin) + 23 tag cùng base (DEAD); `bench execute frappe.get_hooks --kwargs '{"hook":"app_docs_url","app_name":"assetcore"}'` = `[]` (rỗng — hooks chưa khai `app_docs_url` ⟹ default sau D16 = OMIT); `hooks.py:8-11` có `app_publisher='miyano'`/`app_email=''`/`app_license='MIT'` (D14 pattern app-scoped) — KHÔNG có `app_docs_url`. **Sau impl D16:** mặc định root + 23 tag KHÔNG externalDocs (sạch); khi USER khai `app_docs_url` → externalDocs xuất hiện đúng base web-served. Swagger UI render sạch (không 📖 dead) cho tới khi cấu hình. **Backlog Phase A: D1-D16 (D16 sửa doc-base SSoT + graceful-omit).**

### D9-SYNC — ĐỒNG BỘ code↔doc: spec là DẪN XUẤT, không nguồn — guard test chống drift

> ⚠️ **ĐÍNH CHÍNH ĐÁNH SỐ (2026-06-09):** số "D9" ban đầu (Vòng 1 gate) thuộc về quyết định **ĐỒNG BỘ code↔doc** dưới đây, NAY đặt lại tên **D9-SYNC** để tránh đụng với đề mục Vòng 4 **D9-TAGS — Canonicalize operation tags** (mục riêng phía dưới). Hai mục KHÁC NHAU; mọi tham chiếu "D9" trước ngày này = D9-SYNC.

**Quyết định (1 dòng):** spec **luôn sinh lại từ code** (không commit file `openapi.json` như nguồn); **guard test CI** đảm bảo introspect không vỡ + envelope enum khớp.

- **KHÔNG** commit `openapi.json` tĩnh làm SSoT (sẽ stale). Nếu cần artifact để integrator tải offline → sinh trong build/release, đánh dấu "generated".
- **9 union `X|None=None` (F5) phải đổi TRƯỚC khi generate** (D-PRECOND dưới) để type-hint→JSON-type không ra `anyOf` rối / introspect lỗi.
- **Guard test (TDD Vòng 2):** (a) generator chạy không exception trên cả 485 endpoint; (b) `code.enum == ErrorCode values`, `http_status.enum == _HTTP_FOR_CODE.values()`; (c) mọi endpoint có `operationId` duy nhất; (d) spec pass openapi-spec-validator 3.1.

> Đo được: thêm 1 endpoint mới + chạy guard test → spec count +1 tự động, không sửa doc tay. Thêm ErrorCode → enum test bắt drift nếu generator không re-read.

---

### D9-TAGS — CANONICALIZE operation tags qua 1 SSoT map module→tag (gỡ leak raw lowercase module-slug ra public API doc) ▶️ **Phase A D9 — Vòng 4 (2026-06-09)**

> **Bản chất:** mục thực thi (KHÔNG re-chốt ADR Accepted). Lấp lỗ-thiết-kế còn lại của D8: tag NAME ở operation hiện vẫn là raw `[mod_short]` cho 20/23 module → leak slug nội bộ ('imm01'..'imm16','auth','dashboard'…) ra public API doc + Swagger UI nhóm endpoint bằng tên-file thường. D9-TAGS chuẩn hoá **TÊN tag** (NAME, không chỉ description) qua 1 SSoT. **KHÔNG đụng** path/operationId/verb/security/responses/requestBody/enrich đã chốt D1-D8.

**ROOT-CAUSE (verify @source 2026-06-09, `bench execute generate_spec`):** spec có **23 root tag**; chỉ **3** clean uppercase `IMM-00/04/12` (do `enrich_meta_for` set `tags:["IMM-XX"]`). **20 tag còn lại = raw lowercase module-slug** vì `openapi.py:429` gán `"tags": [mod_short]` cho mọi op KHÔNG-enrich. Cụ thể (đếm-thật): `imm01,imm02,imm03,imm05,imm06,imm08,imm09,imm11,imm14,imm15,imm16` (11 imm-slug thường) + `auth,dashboard,import_data,inventory,layout,notifications,openapi,purchase,user` (9 cross-cut/openapi). `_TAG_LABEL_VI` ĐÃ có VI-description keyed-by-slug (root-desc resolve được), NHƯNG tag **NAME** vẫn raw mixed-case → leak.

#### Quyết định (DỨT KHOÁT, đo được)

**T1 — 1 SSoT map module→tag: helper `_canonical_tag(module_short: str) -> str` trong `openapi_overrides.py`.** Map TƯỜNG MINH cho cả 23 module-file (KHÔNG heuristic):
- **13 module imm-named** (`imm00`…`imm16`, có endpoint) → `"IMM-XX"` uppercase (`"imm00"→"IMM-00"`, `"imm04"→"IMM-04"`, …, `"imm16"→"IMM-16"`). Dẫn xuất bằng quy tắc `f"IMM-{slug[-2:]}"` — KHỚP với `enrich_meta_for` (3 module enrich đã trả đúng dạng này ⟹ KHÔNG sinh double-tag, KHÔNG đổi `enriched_count`).
- **9 cross-cut + openapi** → **domain-tag VI canonical** (bảng D9-MAP dưới): `auth→"Xác thực"`, `dashboard→"Bảng điều khiển"`, `import_data→"Nhập liệu"`, `inventory→"Kho"`, `layout→"Bố cục"`, `notifications→"Thông báo"`, `purchase→"Mua sắm"`, `user→"Người dùng"`, `openapi→"Tài liệu API"`.

**T2 — generator đọc SSoT, KHÔNG `mod_short` trực tiếp.** `openapi.py:429` đổi `"tags": [mod_short]` → `"tags": [_ovr.canonical_tag(mod_short)]`. Op-enriched (imm00/04/12) đi qua `_enrich_operation` GHI ĐÈ `operation["tags"]=meta["tags"]` (line ~391) SAU `_build_operation` ⟹ vẫn `"IMM-XX"` (idempotent: `_canonical_tag("imm00")=="IMM-00"==meta["tags"][0]` ⟹ KHÔNG double, KHÔNG đổi enrich-count). 3 module này GIỮ tag `IMM-XX` (đã đúng).

**T3 — `tag_description_for` đọc CÙNG SSoT (no orphan / no thừa).** Sau T2, tag NAME ở operation = tập canonical (13 `IMM-XX` + 9 domain-VI). `tag_description_for(tag)` PHẢI trả VI-description non-empty cho MỌI tag canonical (key đổi từ slug → canonical-tag). `_root_tags` (D8, KHÔNG đổi) gom tập tag DUY NHẤT từ operation ⟹ root `tags[]` == tập canonical ⟹ **no orphan-tag** (mọi tag dùng có description) + **no tag thừa** (chỉ tag thực xuất hiện). SSoT description vẫn ở `openapi_overrides` — generator KHÔNG khai lại map.

**T4 — fail-fast khi thêm module chưa-map (mutation-guard).** `_canonical_tag` với module CHƯA trong map → **KHÔNG fallback im lặng raw-slug**. Hai tầng bảo vệ:
- (a) imm-named bắt được tự động (`f"IMM-{slug[-2:]}"` cho mọi `immXX`) → thêm imm07/10/13 sau này tự canonical.
- (b) module cross-cut MỚI chưa trong `_CROSSCUT_TAG_MAP` → guard test `test_oas_d9_tags` quét MỌI tag trong spec: KHÔNG tag nào match regex `^imm[0-9]{2}$` (slug imm thường) HOẶC tên-file-thường (`^[a-z][a-z_]*$` mà KHÔNG ∈ tập domain-VI hợp lệ) → fail-fast (no silent raw-slug leak). (Tùy chọn impl mạnh hơn: `_canonical_tag` raise `KeyError`/log cho cross-cut-chưa-map; tối thiểu BẮT BUỘC = guard test bắt.)

#### D9-MAP — Bảng SSoT 23 dòng (module-file → canonical tag → VI-description)

| # | module-file | endpoints | canonical tag (NAME) | nguồn NAME | VI-description (qua `tag_description_for`) |
|---|---|---|---|---|---|
| 1 | `imm00` | 111 | `IMM-00` | `f"IMM-{[-2:]}"` | Nền tảng tài sản (IMM-00) |
| 2 | `imm01` | 22 | `IMM-01` | `f"IMM-{[-2:]}"` | Nhu cầu & kế hoạch mua sắm (IMM-01) |
| 3 | `imm02` | 16 | `IMM-02` | idem | Yêu cầu kỹ thuật (IMM-02) |
| 4 | `imm03` | 24 | `IMM-03` | idem | Đánh giá NCC & quyết định mua (IMM-03) |
| 5 | `imm04` | 34 | `IMM-04` | idem (enrich khớp) | Lắp đặt & nghiệm thu (IMM-04) |
| 6 | `imm05` | 16 | `IMM-05` | idem | Kho tài liệu thiết bị (IMM-05) |
| 7 | `imm06` | 25 | `IMM-06` | idem | Đào tạo & chuyển giao (IMM-06) |
| 8 | `imm08` | 24 | `IMM-08` | idem | Bảo trì định kỳ (IMM-08) |
| 9 | `imm09` | 13 | `IMM-09` | idem | Sửa chữa khắc phục (IMM-09) |
| 10 | `imm11` | 18 | `IMM-11` | idem | Hiệu chuẩn (IMM-11) |
| 11 | `imm12` | 16 | `IMM-12` | idem (enrich khớp) | Sự cố & khắc phục (IMM-12) |
| 12 | `imm14` | 3 | `IMM-14` | idem | Thanh lý & kết thúc vòng đời (IMM-14) |
| 13 | `imm15` | 22 | `IMM-15` | idem | Phụ tùng & tồn kho (IMM-15) |
| 14 | `imm16` | 52 | `IMM-16` | idem | Tuân thủ & dấu vết kiểm toán (IMM-16) |
| 15 | `auth` | 7 | **Xác thực** | `_CROSSCUT_TAG_MAP` | Xác thực & tài khoản người dùng |
| 16 | `dashboard` | 3 | **Bảng điều khiển** | idem | Bảng điều khiển & chỉ số |
| 17 | `import_data` | 6 | **Nhập liệu** | idem | Nhập dữ liệu hàng loạt |
| 18 | `inventory` | 36 | **Kho** | idem | Kho & vật tư (nền tảng) |
| 19 | `layout` | 7 | **Bố cục** | idem | Bố cục & phiên người dùng |
| 20 | `notifications` | 3 | **Thông báo** | idem | Thông báo & cảnh báo |
| 21 | `purchase` | 13 | **Mua sắm** | idem | Mua hàng & đơn đặt hàng |
| 22 | `user` | 14 | **Người dùng** | idem | Quản trị người dùng & phân quyền |
| 23 | `openapi` | (serve) | **Tài liệu API** | idem | Tài liệu OpenAPI (tự sinh) |

> **Lưu ý SSoT (chống drift):** TÊN tag (cột 4) là SSoT MỚI trong `_canonical_tag`/`_CROSSCUT_TAG_MAP`. VI-description (cột 6) GIỮ ở `tag_description_for` nhưng **key đổi** từ slug → canonical-tag. Generator (`openapi.py`) KHÔNG khai lại bất kỳ map nào — chỉ gọi `_ovr.canonical_tag` + `_ovr.tag_description_for`.

#### DELTA-BE — đặc tả thay đổi chính xác cho [BE] (bám file hiện tại, KHÔNG để dev đoán)

> **Self-Correction (lỗi-thiết-kế-gốc tránh trước):** hiện `tag_description_for` (`openapi_overrides.py:227`) chỉ resolve `IMM-XX` qua `_MODULE_LABEL_VI` — map này CHỈ có 3 key `imm00/04/12` (`:185-189`). Sau D9-TAGS, **11 imm-slug khác** (`imm01/02/03/05/06/08/09/11/14/15/16`) trở thành tag `IMM-01`…`IMM-16` ⟹ nhánh `IMM-` ở `:244-248` tra `_MODULE_LABEL_VI` MISS → rơi xuống `_TAG_LABEL_VI[tag]` nhưng key cũ là slug thường (`"imm01"`) ⟹ MISS LẦN 2 → fallback `"Nhóm chức năng AssetCore"` ⟹ **description thường (acceptance #4 fail)**. Vì vậy DELTA-BE PHẢI sửa cả 3 chỗ:

| Chỗ | File:line hiện tại | Đổi thành |
|---|---|---|
| **(a) thêm helper SSoT** | `openapi_overrides.py` (mới) | `_CANONICAL_IMM = lambda s: f"IMM-{s[-2:]}"` (mọi `immXX`) + dict `_CROSSCUT_TAG_MAP = {"auth":"Xác thực","dashboard":"Bảng điều khiển","import_data":"Nhập liệu","inventory":"Kho","layout":"Bố cục","notifications":"Thông báo","purchase":"Mua sắm","user":"Người dùng","openapi":"Tài liệu API"}`. `def canonical_tag(mod_short)`: nếu `re.fullmatch(r"imm[0-9]{2}", mod_short)` → `_CANONICAL_IMM`; elif mod ∈ `_CROSSCUT_TAG_MAP` → giá trị; **else raise `KeyError(mod_short)`** (fail-fast T4 — KHÔNG fallback raw-slug). |
| **(b) re-key VI-description** | `openapi_overrides.py:200-223` `_TAG_LABEL_VI` | đổi key 11 imm-slug `"imm01"…"imm16"` → `"IMM-01"…"IMM-16"`; đổi 9 cross-cut key slug → **canonical-VI-NAME** (`"auth"→"Xác thực"`, `"dashboard"→"Bảng điều khiển"`, …) ĐỂ `tag_description_for(<canonical>)` hit. (HOẶC: mở rộng `_MODULE_LABEL_VI` đủ 13 imm-key cho nhánh `IMM-` + đổi 9 cross-cut key — chọn 1 cách, miễn `tag_description_for(canonical)` non-empty.) |
| **(c) generator đọc SSoT** | `openapi.py:429` `"tags": [mod_short]` | `"tags": [_ovr.canonical_tag(mod_short)]`. KHÔNG đụng `_enrich_operation:391` (ghi đè CÙNG `"IMM-XX"` cho imm00/04/12 — idempotent) / `_root_tags:540` (đã gom-unique đúng) / `_assetcore_stats` (enriched_count bất biến). |

> **Bất biến verify-after:** `canonical_tag("imm00")=="IMM-00"==enrich_meta_for("imm00.create_asset")["tags"][0]` ⟹ no double-tag. `_root_tags` sort theo NAME ⟹ Swagger UI nhóm 13 `IMM-XX` + 9 domain-VI (KHÔNG slug thường). `enriched_count` đọc `enrich_meta_for` (KHÔNG đụng) ⟹ GIỮ 161.

#### Bất biến BẮT BUỘC (regression — D1-D8 intact)

- `openapi == "3.1.0"`; `len(paths)` KHÔNG đổi; mỗi op GIỮ NGUYÊN `operationId`/`verb`/`security`/`responses`/`requestBody`.
- `x-assetcore-stats.enriched_count` **GIỮ NGUYÊN trước/sau** (rename tag KHÔNG đụng `enrich_meta_for` ⟹ count bất biến — verify @source hiện = 161, phải == sau D9-TAGS).
- `enrich_meta_for` 3 module imm00/04/12 GIỮ tag `IMM-XX` (KHÔNG double-tag: `_canonical_tag` cho imm00/04/12 trả CÙNG `"IMM-XX"` ⟹ `_build_operation` set `["IMM-00"]` rồi `_enrich_operation` ghi đè CÙNG giá trị — idempotent).
- `test_oas_generator` + `test_oas_signatures` + `test_oas_serve` + `test_oas_d8_metadata` ĐỀU GREEN.

> **Đo được (acceptance Phase A D9-TAGS):**
> 1. MỌI `operation.tags` ∈ tập canonical (13 `IMM-XX` uppercase + 9 domain-VI); **0 tag raw lowercase module-slug**.
> 2. Regex no-raw-slug: KHÔNG tag nào match `^imm[0-9]{2}$` (slug imm thường) HOẶC tên-file-thường ('auth','dashboard','openapi','import_data','inventory','layout','notifications','purchase','user' dạng raw).
> 3. Root `tags[]` == tập tag DUY NHẤT dùng ở operation (no orphan, no thừa) — `_root_tags` đã đảm bảo, test re-assert sau đổi NAME.
> 4. MỌI canonical tag có VI-description non-empty qua `tag_description_for` (SSoT chung — generator KHÔNG khai lại map).
> 5. `enrich_meta_for` 3 module GIỮ tag `IMM-XX`; `x-assetcore-stats.enriched_count` GIỮ NGUYÊN (161) trước/sau.
> 6. Mutation-guard: thêm 1 endpoint vào module bất kỳ → tag op mới TỰ canonical (đọc SSoT, KHÔNG sửa generator); thêm module-file MỚI chưa-map → guard test bắt (fail-fast, no silent raw-slug leak).
> 7. Regression: `test_oas_generator` + `test_oas_signatures` + `test_oas_serve` + `test_oas_d8_metadata` ĐỀU GREEN; `openapi==3.1.0`; `len(paths)` không đổi; path/operationId/verb/security/responses BẤT BIẾN.

**NON-GOAL D9-TAGS:** KHÔNG curate examples module ngoài imm00/04/12; KHÔNG đụng path/opId/verb/security/`response.py`; KHÔNG download/Postman export (backlog Phase A); KHÔNG re-style Swagger UI; KHÔNG reload/commit (HARD-STOP user).

#### Test-case TDD D9-TAGS (THÊM, không THAY — guard đặt-tên §D-TEST)

| ID | Mức | Khẳng định |
|---|---|---|
| TC-OAS-D9-01 | unit | MỌI `operation.tags` ∈ tập canonical; 0 tag match `^imm[0-9]{2}$`; 0 tag ∈ raw-crosscut-slug-set. |
| TC-OAS-D9-02 | unit | Root `tags[]` (`_root_tags`) == tập tag DUY NHẤT của operation (no orphan / no thừa); mỗi entry `description` non-empty. |
| TC-OAS-D9-03 | unit | `_canonical_tag("imm00".."imm16")=="IMM-XX"`; `_canonical_tag("auth")=="Xác thực"` … (sample 23 dòng D9-MAP); idempotent với enrich (imm00/04/12 → "IMM-XX" khớp `enrich_meta_for`). |
| TC-OAS-D9-04 | unit | `enriched_count` (x-assetcore-stats) GIỮ NGUYÊN trước/sau (snapshot == 161); `len(paths)` không đổi; `openapi=="3.1.0"`. |
| TC-OAS-D9-05 | guard | Mutation: monkeypatch thêm module-file giả chưa-map vào pipeline → guard bắt (raise HOẶC test fail) — KHÔNG silent raw-slug. Thêm endpoint vào module đã-map → tag op mới TỰ canonical (no generator edit). |

> ⚠️ **GUARD ĐẶT-TÊN-TEST:** D9-TAGS dùng hậu tố `*_D9_*` / class `TestOasD9Tags` — KHÔNG đụng `TestOasD8*` (D8 metadata) / `test_oas_06*`/`07*` (D5/D6). "THÊM TC-OAS-D9-*" = THÊM, không THAY 59+11+9+14 test D1-D8 hiện xanh.

---

## D-PRECOND — Tiền điều kiện BẮT BUỘC trước generate: đổi 9 union `X | None = None`

Liệt **9 chữ ký** (F5) phải đổi từ `X | None = None` sang **default rõ ràng cùng kiểu** để introspection ra type đơn (KHÔNG `anyOf [type, null]` gây rối cho integrator) và để default-introspect ổn định:

| # | File:line | Hiện tại | Đổi thành (chốt) |
|---|---|---|---|
| 1 | `api/imm01.py:543` | `device_category: str \| None = None` | `device_category: str = ""` |
| 2 | `api/imm01.py:559` | `period: str \| None = None` | `period: str = ""` |
| 3 | `api/imm04.py:106` | `fields: str \| dict \| None = None` | giữ union (LÀ JSON-string body) → registry D5 `format:json`; nếu chuẩn hoá: `fields: str = ""` + parse |
| 4 | `api/imm04.py:116` | `data: str \| dict \| None = None` | giữ union (JSON-string body) → registry D5; hoặc `data: str = ""` |
| 5 | `api/imm04.py:126` | `nc_data: str \| dict \| None = None` | giữ union (JSON-string body) → registry D5; hoặc `nc_data: str = ""` |
| 6 | `api/imm04.py:156` | `results: str \| list \| None = None` | giữ union (JSON-string body) → registry D5; hoặc `results: str = ""` |
| 7 | `api/imm14.py:39` | `responsible: str \| None = None` | `responsible: str = ""` |
| 8 | `api/dashboard.py:890` | `persona: str \| None = None` | `persona: str = ""` |
| 9 | `api/imm01.py:284-285` | `funding_source`/`funding_evidence: str \| None = None` | `str = ""` (cùng class) |
| 10 | `api/imm02.py:377` | `threshold: float \| None = None` | `threshold: float = 0` (hoặc sentinel nếu 0 hợp lệ — Vòng 2 xét) |
| 11 | `api/imm16.py:410-411` | `period_year`/`period_month: int \| None = None` | `int = 0` |
| 12 | `api/dashboard.py:473` | `drill: dict \| None = None` | JSON-string body → registry D5 `format:json` (giống imm04) HOẶC `str = ""` + parse |

**Nguyên tắc chốt:** (a) param **scalar optional** (str/int/float) → đổi sang default-rỗng cùng kiểu (`str=""`, `int=0`, `float=0`) — KHÔNG None-union. (b) param **JSON-string body** (union `str|dict|list`, hoặc `dict|None` như dashboard:473) → **GIỮ** semantics nhận-chuỗi nhưng khai `str=""` ở chữ ký + parse trong body, và registry D5 mô tả `format:json` + `x-decoded-schema`. **Đây là code-change Vòng 2** (không phải Vòng 1 gate) — gắn test ở D-TEST.

> ⚠️ **Đo lại tại source 2026-06-09 (QA re-verify):** `grep -rnE '\| *None *= *None' api/*.py` = **16 dòng** (KHÔNG phải 9 PM liệt ban đầu). **14 dòng** là param của hàm **whitelisted** phải đổi — tương ứng bảng trên #1-12 (trong đó row #9 `imm01:284-285` và row #11 `imm16:410-411` mỗi cái trải **2 dòng nguồn**, nên 12 row = 14 dòng). **2 dòng còn lại KHÔNG cần đổi:** `auth.py:31` (`_dummy_pwhash_cache` — biến module-level, không phải param) + `auth.py:365` (`_compute_permissions(role_set)` — hàm **private** `_`-prefix, không whitelist → không vào spec). **Quy tắc Vòng 2:** chỉ đổi param của hàm **whitelisted** (vào spec); private `_impl`/biến module giữ nguyên union là OK (không ảnh hưởng introspect spec). Test TC-OAS-09 phải lọc theo "whitelist param" chứ không grep mù `| None = None` toàn file.

---

### D18 — SWAGGER UI DEV-PREVIEW FALLBACK: local-first + CDN onerror-fallback (CHỈ khi /assets/ 404) ▶️ **Phase A D18 (R4 — DONE+GREEN, BA spec + test)**

> **BỆNH (dev):** `www/api-docs.html` ref `/assets/assetcore/swagger-ui/swagger-ui-bundle.js` + `-standalone-preset.js` + `swagger-ui.css`. Ở **werkzeug dev `:8000`** Frappe **KHÔNG serve `/assets/`** (chỉ **nginx prod** serve qua symlink `public/`) ⇒ 3 asset **404** → Swagger UI KHÔNG init (trang trắng/lỗi). `:3000` vite-proxy load được TRANG nhưng bundle vẫn 404. Files **ON DISK OK** (`public/swagger-ui/`, ~1.9MB — verify `test_oas_d18_01`).

**Quyết định (T1-T4 — local-first, KHÔNG ép phụ thuộc CDN):**

- **T1 — LOCAL-FIRST (prod air-gapped giữ nguyên):** `api-docs.html` VẪN ref `/assets/assetcore/swagger-ui/*` TRƯỚC. Prod (nginx) serve được → local LUÔN resolve → **KHÔNG BAO GIỜ chạm CDN** (D-anti-pattern "CDN ngoài cho air-gapped" GIỮ nguyên cho prod). Bệnh viện OFFLINE KHÔNG bị ép phụ thuộc mạng ngoài.
- **T2 — CDN FALLBACK CHỈ khi local 404 (dev-only):** loader JS programmatic (`acLoadScript`) nạp local `<script>`; nếu `onerror` (local 404 — CHỈ xảy ra ở dev `:8000`) → nạp lại từ **CDN jsdelivr `swagger-ui-dist@5.17.14`** + `crossOrigin='anonymous'`. CSS `<link onerror>` fallback CDN tương tự. Bootstrap `SwaggerUIBundle` CHỜ `window.acSwaggerReady` (Promise resolve khi bundle sẵn sàng — local HOẶC CDN); cả 2 nguồn fail → khối lỗi (KHÔNG vỡ trang trắng).
- **T3 — SRI để TRỐNG có chủ đích (KHÔNG bịa hash):** local files trên đĩa **KHÔNG có version-marker** (`package.json`/version comment) để verify parity với CDN `5.17.14` ⇒ **KHÔNG hardcode SRI hash KHÔNG-kiểm-chứng** (BA gate KHÔNG bịa). `AC_SWAGGER_SRI = {}` (rỗng) + comment hướng dẫn ĐIỀN hash THẬT (`npm view swagger-ui-dist@5.17.14 dist.integrity` HOẶC `openssl dgst -sha384`) TRƯỚC khi cho dev dùng CDN trên mạng-không-tin-cậy. **Prod air-gapped KHÔNG chạm CDN ⇒ thiếu SRI KHÔNG ảnh hưởng prod.**
- **T4 — gate trang GIỮ:** `www/api-docs.py::get_context` (Guest→redirect login) + endpoint `spec` session-gated KHÔNG đổi.

> **Verify @source (R4):** Tests `tests/test_oas_serve.py::TestOasD18SwaggerAssets` TC-OAS-D18-01..03 (3 test) GREEN — (01) 3 asset local TỒN TẠI trên đĩa + non-empty; (02) HTML ref local-first 3 path; (03) HTML có onerror fallback + `swagger-ui-dist@` + `crossOrigin` + gate `acSwaggerReady`. Regression `test_oas_serve` D7 (9) GREEN → 12 total. **KHÔNG sửa `api/openapi.py`/`response.py`/path/operationId.** LIVE Swagger UI `:8000` chờ USER reload gunicorn (blocker#1) — nhưng test introspect HTML/disk THẬT, KHÔNG cần reload.

---

### D-OAS-DEVTOK — DEVICE-TOKEN (EPIC-D D4) TYPED theo Decision-B closed-schema route-by-VALUE (KHÔNG discriminator) ▶️ **Vòng 17 (DONE+GREEN, BA spec + test)**

> **Phạm vi:** quyết định này thuộc **spec MOBILE thứ-2** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`, OpenAPI 3.0.3 — codegen Dart/Kotlin/TS), KHÔNG phải spec runtime auto-gen (D1-D18). Theo **ADR-MOBILE-001 A1 "2-spec-by-design"**: runtime spec (`api/openapi.py`, 3.1.0, ~487 path) = SSoT human-browse/integrator; mobile yaml (16 path) = SSoT codegen mobile MANG Decision-B. ADR này ghi quyết-định device-token để IMM-00 OpenAPI-record đầy đủ + cross-link.

**Bối cảnh:** R4 (§8.7 04-api-contract) GIỮ 2 device-token path (`mobile.v1.register/unregister_device_token`) ở STUB vì service+handler CHƯA tồn tại (BA gate R-CD-4 KHÔNG bịa endpoint). **EPIC-D D2** (Vòng 16) tạo `services/mobile_device_token.py` (3-tier, GROUNDED) ⇒ **D4** (Vòng 17) GỠ 2 STUB cuối: type `data` GROUNDED chữ-ký service THẬT.

**5 câu hỏi domain (assetcore-doc Phần 2):** (1) **WHO HTM stage:** cross-cutting IMM-00 (mobile-BE platform) — kênh push FCM phục vụ Maintenance (PM/CM/Calibration overdue). (2) **NĐ98:** không mandate trực tiếp; register/unregister sinh audit IMM Audit Trail SHA-256 (NĐ98 §6.3 truy xuất ai-đăng-ký-token-nào-khi-nào). (3) **Stakeholder:** field-tech (self-service đăng ký token thiết bị của chính mình); mobile-dev (codegen client). (4) **Lifecycle event:** không (token registry ≠ asset lifecycle); audit-only. (5) **Hậu quả nếu data sai:** spoof token (client gửi `user=<nạn nhân>` → push sai người) — chặn bằng server-ÉP `frappe.session.user` (§6.2).

**Quyết định cốt lõi (DT1-DT5 — đo được):**

- **DT1 — Decision-B closed-schema route-by-VALUE (KHÔNG discriminator boolean):** 2 path 200 = inline `oneOf [<Created>, Error]`. Nhánh Created (`additionalProperties:false`, `success.enum:[true]`, required `[success, data]`) ∩ Error (`additionalProperties:false`, `success.enum:[false]`, required `[success, error, code, http_status]`) = ∅ → disjoint required-set + closed ⇒ codegen route ĐÚNG theo **GIÁ TRỊ** `body.success` (KHÔNG cần `discriminator` — `success` là BOOLEAN, OAS 3.x discriminator.propertyName yêu cầu property STRING → illegal/deser-fail). **0 discriminator-key** toàn spec (đồng pattern 3 create-triad §5c). Đây là **đóng băng Decision-B** cho device-token (KHÔNG mở lại boolean-discriminator).

- **DT2 — `data` GROUNDED service return THẬT (KHÔNG bịa wrap):** `register_device_token` trả `name` (str = hash record, `mobile_device_token.py:153/166`) → `handle()`/`_ok(name)` ⇒ `RegisterDeviceTokenCreatedEnvelope.data` = `string` (KHÔNG object `{device_token_id}`). `unregister_device_token` trả `None` → `_ok(None)` ⇒ `UnregisterDeviceTokenAckEnvelope.data` = `null` (nullable string, ack thuần). BA gate: handler chỉ wrap service — KHÔNG ép wrap object divergent với D2.

- **DT3 — request `DeviceTokenRequest` closed + anti-spoof:** `fcm_token` reqd (khóa dedup UNIQUE), `platform` enum `[android, ios]` (Select-canonical `_VALID_PLATFORMS` `mobile_device_token.py:56`), `device_label?`/`app_version?` optional. `additionalProperties:false`. **KHÔNG khai `user`** — server ÉP `frappe.session.user` (signature service KHÔNG nhận `user`; `**_ignore` nuốt kwargs lạ, §6.2). content oneOf `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict`).

- **DT4 — 2 loại 403 + symmetry 12:** `403` = **single-shape** `Forbidden` (FrappeRawError) = dispatcher-403 (guest/no-token = `PermissionError` HTTP-403 status-line, `is_whitelisted __init__.py:876`) — bearer-gated self-service KHÔNG allow_guest (06 §2.3). `401` = `Unauthorized401` (bearer hết-hạn). in-handler `422 VALIDATION` (register: fcm_token rỗng/platform ngoài enum, `mobile_device_token.py:130-137`) ARRIVE HTTP-200 body → gom nhánh Error (KHÔNG status-line key, quirk §5). 2 device-token GIỮ symmetry 401/403 (12==12 path MVP). `_STUB_PATHS = ∅` (0 STUB-on-MVP).

- **DT5 — same-commit wiring (Pattern A):** `hooks.py` `permission_query_conditions` + `has_permission` thêm `'AC Mobile Device Token'` (self-scope `user==frappe.session.user`, D7) wire CÙNG-COMMIT với hàm `permissions.py` — KHÔNG để hook trỏ hàm chưa tồn tại.

> **Verify @source (Vòng 17, BA doc+test-only):** yaml 16 path / 3.0.3 / **0 dangling $ref** / **0 discriminator-key** (PyYAML probe); 2 device-token: `requestBody $ref DeviceTokenBody` + 200 oneOf `[<Created>, Error]` (KHÔNG `responses/Stub`); 3 schema mới (`DeviceTokenRequest`/`RegisterDeviceTokenCreatedEnvelope`/`UnregisterDeviceTokenAckEnvelope`) + 1 requestBody (`DeviceTokenBody`) `$ref`'d ngay (KHÔNG orphan); `responses/Stub` HẾT ref → forward-reserve (`_RESERVED_ORPHANS`). Tests `tests/test_mobile_oas.py::TestMobileDeviceTokenTyped` TC-MOB-OAS-22a..i (**9 TC**) GREEN; `test_mobile_oas` **131 OK** (122→131); guard-suite 6-module **219 OK** (210→219); `test_mobile_docset` 9 OK (count-parity). **KHÔNG sửa service/api `.py` vòng này** (BA doc+yaml+test introspect-only — handler `api/mobile/v1/device_token.py` = BE impl cùng EPIC-D D4); LIVE HTTP chờ USER reload gunicorn. Chi tiết: `docs/mobile/04-api-contract.md §8.9` + `completion/EPIC-D-push-fcm.md §D4` + ADR-MOBILE-001.

### D-OAS-LISTUSERS — mobile spec `listUsers` (IMM-00 `user.list_users`) technician/assignee picker (Vòng 10)

> **Phạm vi:** thuộc **spec MOBILE thứ-2** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`, 3.0.3 — codegen). Ghi ở IMM-00 vì endpoint nguồn = `assetcore/api/user.py:268` (User Management, IMM-00). Mobile yaml path/opId **23→24**; runtime auto-gen spec (D1-D15) KHÔNG đụng (mobile suite đọc yaml thủ-công).

**5 câu hỏi domain (assetcore-doc Phần 2):** (1) **WHO HTM stage:** cross-cutting IMM-00 (master data — danh mục người dùng) phục vụ Maintenance (chọn KTV cho Calibration/PM/CM). (2) **NĐ98:** không mandate trực tiếp; META endpoint picker — phơi tên/email/phòng/role để gán trách-nhiệm-thiết-bị (NĐ98 §6 truy xuất ai-thực-hiện). (3) **Stakeholder:** quản lý PM/Calibration (chọn assignee), field-tech (xem ai phụ trách). (4) **Lifecycle event:** không (danh bạ ≠ asset lifecycle). (5) **Hậu quả nếu data sai:** picker rỗng → form `createCalibration`/`assign_technician` cụt required `technician` → KHÔNG submit; HOẶC leak `password_hash`/`api_secret` nếu element không closed → vi phạm bảo mật.

- **DU1 — grounding 1:1 `user.list_users:268-377`** (KHÔNG bịa): 6 query-param DISCRETE (`search`/`department`/`role`/`approval_status` string `default ''` + `is_active` integer enum [0,1] + `page`/`page_size` reuse). `role.enum` = `_IMM_ROLES` = `Roles.ALL` (`constants.py:35`, **30 role** = 4 System + 26 Domain) — sinh TỪ source, KHÔNG hardcode literal.
- **DU2 — element `UserListItem` field-disjoint + closed:** 9 scalar (`name` reqd + `full_name`/`email`/`enabled`/`user_image`/`role_profile_name`/`department_name`/`is_active`/`imm_approval_status`) + `imm_roles[]` object-array `{name,label,group}`; `additionalProperties:false` ⇒ **KHÔNG leak** `password_hash`/`api_key`/`api_secret`/raw Has-Role child-table.
- **DU3 — `enabled`+`is_active` = User.enabled Check → integer enum [0,1]** (Open#1 int-vs-bool sweep, KHÔNG `type:boolean`). `is_active` = alias `enabled` (`:354`).
- **DU4 — pagination 4-key KHÔNG `offset`:** dedicated `UserListPagination` (KHÔNG `$ref Pagination` 5-key) — chống strict-codegen deser-crash. Xem [ADR-MOBILE-005](../mobile/ADR-MOBILE-005.md).
- **DU5 — 200 = oneOf [`UserListEnvelope`, `Error`]** closed-schema route-by-VALUE `body.success` (C7, 0 discriminator). rows-key `data.items[]` (mirror Asset/Incident). 401→`Unauthorized401`, 403→`Forbidden`. **KHÔNG financial** (LL-BE-57). Guard `TestMobileListUsersContract`. **KHÔNG `.py`/reload/migrate** (pure-yaml + guard). Chi tiết: `docs/mobile/04-api-contract.md §6.3` + ADR-MOBILE-005.

---

### D-OAS-MARKNOTIFREAD — mobile spec `markNotificationAsRead` (IMM-00 `layout.mark_notification_as_read`) read-receipt FLOW-6 (Vòng 31)

> **Phạm vi:** thuộc **spec MOBILE thứ-2** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`, 3.0.3 — codegen). Ghi ở IMM-00 vì endpoint nguồn = `assetcore/api/layout.py:102-117` (Notification Center, IMM-00). Mobile yaml path/opId **38→39**; runtime auto-gen spec (D1-D15) KHÔNG đụng (mobile suite đọc yaml thủ-công). **WRITE-action ĐẦU TIÊN trên domain Notification Log** (R12-30 đều mutate WO/Incident/Calibration).

**5 câu hỏi domain (assetcore-doc Phần 2):** (1) **WHO HTM stage:** cross-cutting IMM-00 (Notification Center) — không buộc 1 stage; phục vụ mọi lifecycle (PM/CM/Calibration/Incident notify). (2) **NĐ98:** không mandate trực tiếp; META-action (đánh-dấu đã-đọc) — KHÔNG sinh Lifecycle Event nghiệp-vụ (read-receipt ≠ asset event). (3) **Stakeholder:** mọi user nhận thông-báo (field-tech, manager, QA) — tab chuông + push deep-link. (4) **Lifecycle event:** KHÔNG (Notification Log không thuộc asset lifecycle; chỉ flip cờ `read`). (5) **Hậu quả nếu data sai:** thiếu endpoint → tab chuông + push CHỈ-ĐỌC (dead-end, badge chưa-đọc không bao giờ giảm); nếu response sai shape (codegen sinh `bool` cho `read`) → strict-deser crash Dart/Kotlin; nếu ownership-guard sai → user A mark thông-báo của user B (rò-rỉ + sai trạng-thái).

- **DN1 — grounding 1:1 `layout.mark_notification_as_read:102-117`** (KHÔNG bịa): `@frappe.whitelist(methods=['POST'])` — **CLEAN POST** (KHÔNG verb-divergence, KHÔNG state-mutation qua GET/CSRF). Signature `(name)` — 0 optional ⇒ `MarkNotificationReadRequest` closed `{name}` required (oneOf json+form, Frappe RPC `form_dict`).
- **DN2 — ownership-guard + error-flow:** `for_user == session.user` @`:111-113` ⇒ user khác → in-handler cap-403 (Error envelope HTTP-200, KHÔNG dispatcher-403). Notification∄ @`:108-109` → 404 (Error envelope HTTP-200). Guest/no-token → dispatcher PermissionError HTTP-403 status-line. **2 loại 403** (dispatcher guest + in-handler cap) — slot khai `Forbidden` SINGLE-SHAPE; in-handler 403/404 đến qua `Error.http_status` (enum bounded chứa 403/404, R11).
- **DN3 — `MarkNotificationReadResponse` EXACT 2-prop `{name, read}`** GROUNDED `_ok({"name":name, "read":1})` @`:117`. `read = integer enum[0,1]` (mirror `NotificationListItem.read` SSoT int-vs-bool, KHÔNG `type:boolean` → né strict-codegen deser crash). `additionalProperties:false` required `[name, read]`.
- **DN4 (ADR-core) — KHÔNG field `status` ⇒ C3-split cross-domain (KHÔNG reuse `*ActionResponse`):**
  - **Context:** 19 lifecycle-action trước (R12-30: `confirmInspection`/`closeWorkOrder`/`resolveIncident`/…) đều trả `status` (workflow_state của WO/Incident/Calibration). Cám-dỗ: reuse 1 envelope action chung.
  - **Decision:** `markNotificationAsRead` dùng **schema RIÊNG** (`MarkNotificationReadEnvelope`/`MarkNotificationReadResponse`), KHÔNG `$ref` tới bất kỳ `*ActionResponse` nào.
  - **Vì sao (rationale):** Notification Log **KHÔNG có `workflow_state`** — KHÔNG có `status` để trả. Ép field `status` vào = bịa data source KHÔNG phát (vi phạm grounding). Object-identity distinct (guard `test_..._f` assert `≠ CloseWorkOrder/ConfirmInspection/AssignTech/SubmitCal Response`).
  - **Consequences:** +3 schema mới (Request/Envelope/Response); codegen sinh model `read:int` (KHÔNG `status`). Mỗi domain-action mới CHỈ reuse envelope khi field-set THẬT trùng — quy tắc C3-split (precedent ResolveIncident/CloseIncident split).
  - **Alternatives bác:** (a) reuse `RepairActionEnvelope {name,status}` → phải nhồi `status` giả; (b) thêm `status:null` nullable → codegen vẫn sinh field rác + sai semantics; (c) trả raw bool `read` → strict-deser crash. Cả 3 bác.
- **DN5 — Boundaries (Always/Never):** **Always:** POST-only · ownership-guard server-side (`for_user==session.user`) · `read` integer enum[0,1] · in-handler 403/404 đến trên HTTP-200 Error body. **Never:** KHÔNG GET-variant (state-mutation qua GET/CSRF) · KHÔNG field `status` · KHÔNG `type:boolean` cho `read` · KHÔNG để client chọn `for_user` (server ÉP session.user) · KHÔNG đụng `.py`/reload/migrate (pure-yaml + guard `TestMobileMarkNotificationReadContract`, BE handler LIVE landed).

---

### D-OAS-MARKALLREAD — mobile spec `markAllAsRead` (IMM-00 `layout.mark_all_as_read`) BULK read-receipt FLOW-6 (Vòng 40)

> **Phạm vi:** thuộc **spec MOBILE** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`, 3.0.3 — codegen). Ghi ở IMM-00 vì endpoint nguồn = `assetcore/api/layout.py:120-134` (Notification Center, IMM-00). Mobile yaml path/opId **46→47**; runtime auto-gen spec (D1-D15) KHÔNG đụng (mobile suite đọc yaml thủ-công; runtime `generate_spec` ĐÃ introspect `mark_all_as_read` từ trước — yaml mobile catch-up). **ĐÓNG NỐT notification-center action-set** (sau `markNotificationAsRead` single §D-OAS-MARKNOTIFREAD). Bám **ADR-MOBILE-018** + **ADR-MOBILE-009** (C3-split).

**5 câu hỏi domain (assetcore-doc Phần 2):** (1) **WHO HTM stage:** cross-cutting IMM-00 (Notification Center) — không buộc 1 stage. (2) **NĐ98:** không mandate trực tiếp; META-action (đánh-dấu tất-cả đã-đọc) — **KHÔNG sinh Lifecycle Event** nghiệp-vụ (read-receipt ≠ asset event). (3) **Stakeholder:** mọi user nhận thông-báo (field-tech, manager, QA) — nút "Đánh dấu tất cả đã đọc" tab Thông báo. (4) **Lifecycle event:** KHÔNG (Notification Log không thuộc asset lifecycle; chỉ flip cờ `read` hàng-loạt). (5) **Hậu quả nếu data sai:** thiếu endpoint → user phải tap từng thông-báo (UX kém, badge không về 0 một-phát); nếu `updated_rows` khai enum[0,1] → strict-deser crash khi N≥2; nếu khai requestBody → codegen sinh body rác sai live-sig.

- **DA1 — grounding 1:1 `layout.mark_all_as_read:120-134`** (KHÔNG bịa): `@frappe.whitelist(methods=['POST'])` @`:120` — **CLEAN POST**. Signature `()` @`:121` — **0-PARAM** ⇒ **KHÔNG requestBody** (codegen no-arg POST). Live-sig parity `inspect.signature(layout.mark_all_as_read).parameters == {}` (anti-drift). `UPDATE tabNotification Log SET read=1 WHERE for_user=%s AND read=0` @`:127-131` → `affected = ROW_COUNT()` @`:132` → `_ok({"updated_rows": affected})` @`:134`.
- **DA2 — error-flow + slot `{200,401,403}`:** scope SQL `WHERE for_user=session.user` ⇒ **KHÔNG lookup-by-name** ⇒ **KHÔNG 404/409** (KHÁC `markNotificationAsRead` có 404 Notification∄ + cap-403 owner-guard). Guest/no-token → dispatcher `PermissionError` HTTP-403 status-line (`Forbidden` SINGLE-SHAPE). In-handler guest @`:124-125` → `_err(401)` đến **HTTP-200** body nhánh Error (route theo `Error.http_status` enum chứa 401). `401`-slot = `Unauthorized401` (FrappeRawError bearer-expired).
- **DA3 — `MarkAllReadResponse` EXACT 1-prop `{updated_rows}`** GROUNDED `_ok({"updated_rows": affected})` @`:134`. `updated_rows = integer` **GENUINE count (0..N)** — **KHÔNG enum[0,1]** (KHÁC `read` của `NotificationListItem`/`MarkNotificationReadResponse` = cờ Check 2-giá-trị; `updated_rows` là ĐẾM `ROW_COUNT()` @`:132`, mirror `AddMeasurementResponse.measurement_count` R34). `additionalProperties:false` required `[updated_rows]`.
- **DA4 (ADR-core) — KHÔNG field `status` ⇒ C3-split cross-domain (KHÔNG reuse `*ActionResponse`):**
  - **Context:** cám-dỗ reuse `MarkNotificationReadResponse` (cùng domain Notification Log) hoặc 1 `*ActionResponse` lifecycle.
  - **Decision:** `markAllAsRead` dùng **schema RIÊNG** (`MarkAllReadEnvelope`/`MarkAllReadResponse`), KHÔNG `$ref` tới `MarkNotificationReadResponse` lẫn bất kỳ `*ActionResponse`.
  - **Vì sao (rationale):** field-set THẬT KHÁC — bulk trả `{updated_rows}` (đếm), single trả `{name, read}` (echo 1 record); Notification Log KHÔNG có `workflow_state` ⇒ KHÔNG `status`. Ép chung = nhồi field giả (vi phạm grounding).
  - **Consequences:** +2 schema mới (Envelope/Response, 0 Request); codegen sinh model `updated_rows:int` GENUINE count. Mỗi domain-action CHỈ reuse envelope khi field-set THẬT trùng — quy tắc C3-split (ADR-MOBILE-009).
  - **Alternatives bác:** (a) reuse `MarkNotificationReadResponse {name,read}` → phải nhồi `name`/`read` giả cho bulk; (b) `updated_rows` enum[0,1] → cắt cụt giá-trị ≥2, deser crash; (c) requestBody `{}` → field rác sai live-sig. Cả 3 bác.
- **DA5 — Boundaries (Always/Never):** **Always:** POST-only · 0-PARAM (KHÔNG requestBody) · `updated_rows` GENUINE integer (no enum) · scope SQL server-side `for_user=session.user` · in-handler 401 đến trên HTTP-200 Error body. **Never:** KHÔNG GET-variant · KHÔNG field `status` · KHÔNG enum[0,1] cho `updated_rows` · KHÔNG slot 404/409 (no name lookup) · KHÔNG để client chọn `for_user` (server ÉP session.user) · KHÔNG đụng `.py`/reload/migrate (CONTRACT-ONLY pure-yaml + guard `TestMobileMarkAllReadContract`, BE handler LIVE landed).

---

## Anti-pattern PHẢI tránh (rút từ memory + customer-doc rules)

- ❌ **Hardcode danh mục endpoint** trong spec → drift. Luôn introspect (D1).
- ❌ **Định nghĩa ErrorCode/HTTP map lần 2** trong spec → 2 nguồn. Đọc từ `response.py` (D3).
- ❌ **`allow_guest` cho endpoint spec** → lộ 485-endpoint bề mặt cho khách (F6 nguy cơ). Session-gate (D7).
- ❌ **CDN ngoài cho Swagger UI Ở PROD** → môi trường bệnh viện air-gapped. Self-host `public/` (D7). *(Ngoại lệ D18: CDN CHỈ là fallback **dev-preview** khi `/assets/` 404 ở werkzeug `:8000` — prod nginx serve local ⇒ KHÔNG BAO GIỜ chạm CDN. Local-first BẤT BIẾN.)*
- ❌ **Commit `openapi.json` làm SSoT** → stale. Sinh-tại-runtime + guard test (D9).
- ❌ **Customer-doc claim "OpenAPI" khi chưa generate** → `assetcore-doc` Phần 4 R-CD-1: mark `[ROADMAP]` cho tới khi D7 live.

---

## Test-case TDD sẽ viết ở Vòng implement (D-TEST)

| ID | Mức | Khẳng định |
|---|---|---|
| TC-OAS-01 | unit | `generate_spec()` chạy không exception trên cả 485 endpoint; `len(paths) == grep -c '@frappe.whitelist'`. |
| TC-OAS-02 | unit | `spec.components.schemas.ErrorEnvelope.properties.code.enum == set(ErrorCode values)` (đọc `utils/response.py:37`). |
| TC-OAS-03 | unit | `...http_status.enum == set(_HTTP_FOR_CODE.values())` (`response.py:60`). |
| TC-OAS-04 | unit | endpoint không-`methods=['POST']` → method GET; có `methods=['POST']` → POST (sample 10 endpoint mỗi loại). |
| TC-OAS-05 | unit | param không default → `required:true`; param có default → `required:false` (sample). |
| TC-OAS-06 | unit | `create_asset` có `requestBody` field từ `frappe.get_meta('AC Asset')`, `reqd=1` field → required (D4). |
| TC-OAS-07 | unit | mọi JSON-string param (F7) có entry `JSON_PARAM_OVERRIDES` + `format:json` (D5). |
| TC-OAS-08 | unit | spec pass `openapi-spec-validator` 3.1 → 0 error (D8). |
| TC-OAS-09 | unit | mọi **param của hàm whitelisted** không còn `X \| None = None` sau khi đổi (D-PRECOND #1-12); optional scalar có default cùng-kiểu. **KHÔNG** grep mù `\| None = None` toàn file (private `_impl`/biến module-level như `auth.py:31,365` được phép giữ union — không vào spec). Assert qua introspect: với mỗi whitelist fn, không annotation param nào là `Optional`/union-None. |
| TC-OAS-10 | api/integration | `GET assetcore.api.openapi.spec` Guest → 401; logged-in → 200 `openapi:"3.1.0"` (D7). |
| TC-OAS-11 | api/integration | gọi spec 2 lần → lần 2 hit cache (không re-introspect — đo qua marker/timer) (D7). |
| TC-OAS-12 | guard | thêm endpoint giả → count spec +1 tự động (chống hardcode) (D9). |
| TC-OAS-06-enrich | unit (D6) | MỌI op của imm00/04/12 có `len(summary)>0` + `len(description)>0`; mutation `OPERATION_META` (+entry→spec đổi, −entry→default); import THUẦN khi `frappe.get_meta` raise. **Class/fn MỚI `TestOasD6Enrich::test_oas_06e_*` — KHÔNG đụng `TestOasD5FormDictBodyBridge::test_oas_06_*` (D5 DocType-map) hiện hữu.** |
| TC-OAS-07-enrich | unit (D6) | mỗi POST enriched: `set(req-example.keys()) ⊆ schema.properties` + `schema.required ⊆ example`; response `200` ref `SuccessEnvelope` + `example.success.value.success==True`; error-responses VI sạch (regex KHÔNG cap-token `[a-z]+\.[a-z]+`, KHÔNG EN-status) + mọi `code ∈ ErrorCode` + status-key `==_HTTP_FOR_CODE[code]`. **Class/fn MỚI `test_oas_07e_*` — KHÔNG đụng `TestOasD5CreateAssetSchema::test_oas_07_*` (D5 create_asset).** |
| TC-OAS-D13-01 | unit (D13) | `generate_spec()` có root key `servers`; là `list` NON-EMPTY (`len(servers)>=1`); mỗi entry là dict có key `url` (str) + `description` (str). |
| TC-OAS-D13-02 | unit (D13) | **Key-order:** `list(spec.keys())` == `['openapi','info','servers','components','paths','tags','x-assetcore-stats']` — `servers` chèn ĐÚNG SAU `info` + TRƯỚC `components` (assert qua `.index('servers')` ngay sau `.index('info')` + trước `.index('components')`). |
| TC-OAS-D13-03 | unit (D13) | `servers[0]['url'] == frappe.utils.get_url()`; URL **KHÔNG** chứa substring `'/api/method/'`; **KHÔNG** kết thúc bằng `'/'` (trừ trường hợp fallback `'/'` — test happy-path mock get_url trả host bare). `servers[0]['description'] == 'Site hiện tại — dẫn xuất động từ cấu hình Frappe'`. |
| TC-OAS-D13-04 | unit (D13) | **Fail-safe:** monkeypatch `frappe.utils.get_url` → raise `Exception` ⟹ `generate_spec()` KHÔNG raise + `servers == [{'url':'/','description':'fallback'}]`. Lặp với `get_url` trả `''`/`None` → cùng fallback. `len(paths)` vẫn `==486` (486 endpoint sinh đủ — không vỡ vì servers). |
| TC-OAS-D13-05 | guard (D13) | **No-hardcode:** đọc source `openapi.py`, hàm/nhánh build servers (`_servers`) KHÔNG chứa literal `http://`/`https://`/tên-site-cố-định (chỉ gọi `get_url()`); `_PATH_PREFIX` KHÔNG xuất hiện trong `_servers`. (Mutation: mock get_url trả host khác → `servers[0].url` đổi theo, chứng minh dẫn-xuất-động.) |
| TC-OAS-D13-06 | guard (D13) | **Bất biến stat + spec valid:** `x-assetcore-stats` (total/get/post/guest/enriched/error_responses_typed/json_param/cap_set_version) GIỮ NGUYÊN so với snapshot trước-servers (`enriched_count==161`, `total_endpoints==len(paths)`); `openapi=='3.1.0'`; spec PASS validate OpenAPI 3.1 (`servers` field root hợp lệ). Regression D1-D12 (`test_oas_generator`/`signatures`/`serve`/`d8`/`d9_tags`/`d10`/`d11`/`d12`) GREEN. |
| TC-OAS-D14-01 | unit (D14) | `info.license == {'name':'MIT','identifier':'MIT'}`; có key `identifier` (SPDX 3.1), **KHÔNG** có key `url`. |
| TC-OAS-D14-02 | unit (D14) | `info.contact == {'name':'miyano'}`; `'email' NOT IN contact` (app_email==''); KHÔNG leak `'email':''`. |
| TC-OAS-D14-03 | guard (D14) | **SSoT no-hardcode:** stub `_app_meta_hook` → `app_license`→'Apache-2.0', `app_publisher`→'ACME' ⟹ `info.license.identifier=='Apache-2.0'` + `contact.name=='ACME'`. Grep source 4 vùng build info: KHÔNG literal `'MIT'`/`'miyano'`. |
| TC-OAS-D14-04 | unit (D14) | **email non-empty:** stub `app_email`→'ops@x.vn' ⟹ `contact == {'name':'miyano','email':'ops@x.vn'}` (nhánh non-empty thêm key đúng). |
| TC-OAS-D14-05 | unit (D14) | **fail-safe rỗng/missing:** stub `_app_meta_hook` trả None mọi hook ⟹ info **KHÔNG** có `contact` lẫn `license` (KHÔNG dict rỗng); `generate_spec` KHÔNG raise; info vẫn có title/version/description. |
| TC-OAS-D14-06 | unit (D14) | **info giữ + order bất biến:** `info.title=='AssetCore API'`, version truthy, `'Auto-generated' in description`; `list(spec.keys()) == ['openapi','info','servers','components','paths','tags','x-assetcore-stats']` (D13 order); `contact`/`license` là subkey `info` KHÔNG top-level. |
| TC-OAS-D14-07 | guard (D14) | **stats + servers bất biến:** `x-assetcore-stats` == snapshot khi info-meta vắng (stub None); `servers` không đổi (info ≠ operation). |
| TC-OAS-D15-01 | unit (D15) | **Root externalDocs:** `spec['externalDocs']` là dict có key `url` (str NON-EMPTY) + `description` (str VI non-empty). Happy-path (get_url='http://miyano'): `url` chứa substring `'docs/imm-00/README'` + bắt đầu bằng `'http://miyano/'` (host từ get_url). `description` == chuỗi VI T2. |
| TC-OAS-D15-02 | unit (D15) | **Per-tag externalDocs — 13 IMM-XX:** MỌI tag canonical `"IMM-XX"` (14 tag có-endpoint) có `externalDocs={url,description}`; `url` chứa `f"docs/imm-{NN}/README"` ĐÚNG mã module (IMM-00→imm-00, IMM-16→imm-16); `description` non-empty chứa tên tag. 0/14 IMM-tag thiếu externalDocs. |
| TC-OAS-D15-03 | unit (D15) | **Per-tag externalDocs — 9 cross-cut:** MỌI tag domain-VI (9 tag: 'Xác thực'…'Tài liệu API') có `externalDocs={url,description}`; `url` trỏ doc chung (chứa `'docs/imm-00/README'`); `description` non-empty (no leak slug raw). **TỔNG: 0/23 tag thiếu externalDocs**; mọi `externalDocs.url` non-empty + đúng pattern path (`re.search(r'docs/imm-[0-9]{2}/README', url)`). |
| TC-OAS-D15-04 | unit (D15) | **Key-order:** `list(spec.keys()) == ['openapi','info','servers','components','paths','tags','externalDocs','x-assetcore-stats']` — `externalDocs` chèn ĐÚNG SAU `tags` + TRƯỚC `x-assetcore-stats` (assert `.index('externalDocs')` == `.index('tags')+1` và `< .index('x-assetcore-stats')`). |
| TC-OAS-D15-05 | unit (D15) | **Fail-safe relative:** monkeypatch `frappe.utils.get_url` → raise `Exception` ⟹ `generate_spec()` KHÔNG raise; root `externalDocs.url` = relative (KHÔNG chứa `'http://'`/`'https://'`, chứa `'docs/imm-00/README'`); MỌI per-tag `externalDocs.url` relative + NON-EMPTY. Lặp với get_url trả `''`/`None` → cùng fallback relative. `len(paths)` vẫn `==486`. |
| TC-OAS-D15-06 | guard (D15) | **No-hardcode + dẫn-xuất-động:** đọc source `openapi.py`, vùng build externalDocs (`_doc_base`/`_doc_url`/`_external_docs_root`/`_root_tags`) KHÔNG chứa literal `http://`/`https://`/tên-site-cố-định (host chỉ từ get_url). Mutation: mock get_url trả `'http://other-host'` → root + 23 tag externalDocs.url ĐỀU đổi sang host mới (chứng minh dẫn-xuất-động, KHÔNG hardcode). |
| TC-OAS-D15-07 | guard (D15) | **Bất biến D1-D14 + spec valid:** `x-assetcore-stats` (total/get/post/guest/enriched/error_responses_typed/json_param/cap_set_version) GIỮ NGUYÊN snapshot trước-externalDocs (`enriched_count==161`, `total_endpoints==len(paths)==486`); `info`(title/version/description/contact/license) + `servers[]` + root tags **name+description** không đổi (chỉ THÊM subkey externalDocs); `openapi=='3.1.0'`; 0 dangling $ref. Regression D1-D14 (`test_oas_generator`/`signatures`/`serve`/`d8`/`d9_tags`/`d10`/`d11`/`d12`/`d13`/`d14`) GREEN. |

> ⚠️ **GUARD ĐẶT-TÊN-TEST (BẮT BUỘC):** D5 ĐÃ chiếm `test_oas_06_*` (DocType-map) + `test_oas_07_*` (create_asset schema). D6 PHẢI dùng hậu tố riêng (`*_06e_*`/`*_07e_*` hoặc class `TestOasD6Enrich`) để KHÔNG ghi đè và KHÔNG làm vỡ 38 test D1-D5 hiện xanh. Acceptance "thêm TC-OAS-06/07-enrich" = **THÊM**, không **THAY**. **D13: class MỚI `TestOasD13Servers` (file mới `tests/test_oas_d13_servers.py` HOẶC trong `test_oas_generator.py`) — THÊM, KHÔNG đụng D1-D12. D15: class MỚI `TestOasD15ExternalDocs` (file mới `tests/test_oas_d15_external_docs.py`) — THÊM, KHÔNG đụng D1-D14.**

---

## Tác động & non-goals

**Đụng (Vòng 2+ implement):** `assetcore/api/openapi.py` (generator + D6 `_enrich_operation` + `[ROADMAP]` `spec` endpoint + **D9-TAGS: `:429` đọc `_ovr.canonical_tag(mod_short)`** + **D13: helper `_servers()` + `generate_spec()` chèn `servers` giữa info↔components** + **D15: helper `_doc_base()`/`_doc_url()`/`_external_docs_root()` + `_root_tags` bồi subkey `externalDocs` + `generate_spec()` chèn root `externalDocs` giữa tags↔x-assetcore-stats**), `assetcore/api/openapi_overrides.py` (registry D5 `FORM_DICT_DOCTYPE_MAP` + D6 `OPERATION_META` + **D9-TAGS: `_canonical_tag`/`canonical_tag` + `_CROSSCUT_TAG_MAP` + `tag_description_for` re-key canonical** + **D15: `tag_doc_path(tag)` + `_DOC_ROOT_PATH`**), `assetcore/tests/test_oas_generator.py` (+TC-OAS-06/07-enrich class mới) / `test_oas_d8_metadata.py` hoặc file mới (+`TestOasD9Tags` TC-OAS-D9-01..05) / **`test_oas_d13_servers.py` (+`TestOasD13Servers` TC-OAS-D13-01..06)** / **`test_oas_d15_external_docs.py` (+`TestOasD15ExternalDocs` TC-OAS-D15-01..07)**, `[ROADMAP]` `assetcore/www/api-docs.html` (Swagger UI — D13 native consume `servers[]` + D15 native consume root/per-tag `externalDocs`, KHÔNG cần FE code mới) + `assetcore/public/swagger-ui/*` (self-host bundle), đã sửa 14 chữ ký union (D-PRECOND DONE), bồi `05_API_Specification.md` (enrich imm00/04/12).

**Trạng thái thực thi (2026-06-09):** D-PRECOND ✅ · D1-D3 ✅ · D4 body-bridge ✅ · D5 form_dict registry ✅ · D6 enrich ✅ · D7 serve + Swagger UI ✅ · **D8 root tags + x-assetcore-stats ✅ DONE (Phase A8)** · **D9-TAGS canonicalize operation tags ✅ DONE (Phase A Vòng 4)** — `openapi_overrides.canonical_tag(mod_short)` (SSoT: imm-named→`f"IMM-{slug[-2:]}"`, 9 cross-cut/openapi→`_CROSSCUT_TAG_MAP` domain-VI, module chưa-map→`raise KeyError` fail-fast); `_TAG_LABEL_VI` re-key sang canonical NAME + `_MODULE_LABEL_VI` mở rộng đủ 14 imm-key cho nhánh `IMM-` trong `tag_description_for`; `openapi.py:_build_operation` đọc `_ovr.canonical_tag(mod_short)` thay raw `[mod_short]`. **Verify @source:** root tags = 23 canonical (14 `IMM-XX` + 9 domain-VI), **0 raw-slug leak**, root==operation, `enriched_count` GIỮ 161, `len(paths)` GIỮ 486, `openapi==3.1.0`. Tests `tests/test_oas_d9_tags.py::TestOasD9Tags` TC-OAS-D9-01..06 (14 test) GREEN; regression `test_oas_generator` 49 + `test_oas_signatures` 11 + `test_oas_serve` 9 + `test_oas_d8_metadata` 14 GREEN. **D10 JSON-string param annotate ✅ DONE (Phase A10)** — `openapi._json_string_params(fn)` khám phá tập param JSON-string qua AST (parse_json/_parse_json/json.loads/frappe.parse_json arg[0]=Name(param), trực-tiếp hoặc forward-vào-delegate, fixpoint; cache theo module; defensive set()); wire vào `_parameters_for`/`_request_body_for` → `format:json` + `x-decoded-default-type` (type GIỮ string); `openapi_overrides.JSON_PARAM_OVERRIDES` (≥2 entry, `{'doctype': 'Asset Commissioning'}` tái dùng D5 meta-bridge) + `json_param_override_for`; `x-assetcore-stats.json_param_count`=63 (đếm động, KHÔNG hardcode 109). **Verify @source:** `len(paths)` GIỮ 486, `enriched_count` GIỮ 161, root tags 23 canonical GIỮ, `openapi==3.1.0`, format:json chỉ THÊM khoá (type vẫn string). Tests `tests/test_oas_d10_json_params.py` TC-OAS-D10-01..07 (25 test) GREEN; regression `test_oas_generator` + `test_oas_signatures` 11 + `test_oas_serve` 9 + `test_oas_d8_metadata` 14 + `test_oas_d9_tags` 14 GREEN. **D12 BASELINE-ERR-SURFACE ✅ DONE (Phase A D12)** — `openapi._baseline_error_responses(is_guest)` (THUẦN, DẪN XUẤT `_HTTP_FOR_CODE`+comment-SSoT response.py: UNAUTHORIZED 401 / FORBIDDEN 403, VI sạch) → `_build_operation` MERGE bằng `setdefault` NGAY TRƯỚC `_enrich_operation` ⟹ **baseline merge, curated WIN** (161 op enriched giữ examples+status D6); op AUTHED → 401+403, op GUEST → CHỈ 403 (không 401). `x-assetcore-stats.error_responses_typed_count` = đếm động op có ≥1 response `^[45]\d\d$` (`_is_4xx_5xx`). **Verify @source:** 481 authed op ALL 401+403 (trước 2/15); 5 guest op 0×401/5×403; `error_responses_typed_count`=486; 0 dangling $ref; `openapi==3.1.0`; total/get/post/guest/enriched/json_param GIỮ 486/236/250/5/161/63. Tests `tests/test_oas_d12_error_surface.py::TestOasD12ErrorSurface` TC-OAS-D12-01..06 (14 test) GREEN; regression D1-D11 (`test_oas_generator` 49 + `signatures` 11 + `serve` 9 + `d8` 14 + `d9_tags` 14 + `d10` 25 + `d11` 6) GREEN. **D13 SERVERS-BLOCK ✅ DONE (Phase A D13 — Vòng 8)** — root `servers[]` DẪN XUẤT động từ SSoT `frappe.utils.get_url()` (bare-origin, KHÔNG `/api/method/`, KHÔNG trailing slash), chèn GIỮA `info`↔`components` (thứ tự root MỚI `openapi→info→servers→components→paths→tags→x-assetcore-stats`); helper `_servers()` fail-safe (get_url raise/rỗng → fallback `[{'url':'/','description':'fallback'}]`, generate_spec KHÔNG exception); description VI `'Site hiện tại — dẫn xuất động từ cấu hình Frappe'`; KHÔNG hardcode host (grep `_servers` 0 literal http(s)://); `x-assetcore-stats` (total/get/post/guest/enriched/error_responses_typed/json_param) BẤT BIẾN, `enriched_count==161`, `total_endpoints==len(paths)==486` giữ; Swagger UI native consume `servers[]` (dropdown 'Servers' — KHÔNG cần FE code mới). **Verify @source:** `servers[0].url = "http://miyano"`. Tests `tests/test_oas_d13_servers.py::TestOasD13*` TC-OAS-D13-01..06 (15 test) GREEN. **D14 INFO-CONTACT-LICENSE ✅ DONE (Phase A D14)** — `info.contact` + `info.license` DẪN XUẤT từ `hooks.py` app-metadata SSoT qua `frappe.get_hooks(hook, app_name='assetcore')` (APP-SCOPED single-element list — KHÔNG merged nhiều-app); helper `_app_meta_hook` (fail-safe → None), `_info_contact` (name=app_publisher + email tùy chọn khi non-empty; app_email=='' → OMIT 'email'), `_info_license` ({name,identifier}=app_license SPDX, KHÔNG 'url'); chèn CÓ ĐIỀU KIỆN sau `description` (helper None → bỏ qua, KHÔNG dict rỗng, KHÔNG raise); KHÔNG hardcode `'MIT'`/`'miyano'` (đọc qua hook). **Verify @source:** `info.contact=={'name':'miyano'}` (no 'email'), `info.license=={'name':'MIT','identifier':'MIT'}` (no 'url'); info giữ title/version/description; top-level order + `servers[]` + `x-assetcore-stats` (486/236/250/5/161/486/63/v97) BẤT BIẾN. Tests `tests/test_oas_d14_info_meta.py::TestOasD14*` TC-OAS-D14-01..07 (10 test) GREEN; regression D1-D13 GREEN. **D15 EXTERNALDOCS ▶️ Phase A D15 — Vòng 10 (SPEC-READY, bàn giao [BE])** — bồi root `externalDocs` + per-tag `externalDocs` (OpenAPI 3.1 §4.8.11/§4.8.22) DẪN XUẤT doc-base-URL từ `frappe.utils.get_url()` SSoT (CÙNG pattern D13); root trỏ doc nền tảng (`docs/imm-00/README.md`), 13 tag IMM-XX trỏ `docs/imm-XX/README` tương ứng (14/14 README tồn tại), 9 tag cross-cut trỏ doc chung → **0/23 tag thiếu externalDocs**; chèn root `externalDocs` GIỮA `tags`↔`x-assetcore-stats` (key-order MỚI `...→tags→externalDocs→x-assetcore-stats`); fail-safe relative khi get_url() lỗi (generate_spec KHÔNG raise); helper `_doc_base()`/`_doc_url()`/`_external_docs_root()` (openapi.py) + `tag_doc_path(tag)`/`_DOC_ROOT_PATH` (openapi_overrides.py); `x-assetcore-stats` (486/236/250/5/161/486/63/v97 + app_version 0.0.3) + info/servers/components/paths + root tags name+description BẤT BIẾN (externalDocs = field root + tag-level, KHÔNG đụng count). Tests class MỚI `tests/test_oas_d15_external_docs.py::TestOasD15ExternalDocs` TC-OAS-D15-01..07 — THÊM, KHÔNG đụng D1-D14. **Backlog Phase A: D1-D15 (D15 thêm externalDocs).** Lô enrich 4+ (module ngoài imm00/04/12) + bảng registry `RESPONSE_DATA_OVERRIDES` vẫn `[ROADMAP]`.

**NON-GOAL (KHÔNG làm ADR này):** KHÔNG re-architect 3-tier (API→Service→Repo) ; KHÔNG modify ERPNext core; KHÔNG đổi envelope shape (`utils/response.py` giữ nguyên — chỉ ĐỌC); KHÔNG FHIR (one-way outbound riêng, CLAUDE.md §14); KHÔNG generate client SDK (roadmap).

---

*Gate THIẾT KẾ Vòng 1 — PHÂN TÍCH. KHÔNG đụng code. Thực thi D1–D8 + D9-SYNC + D-PRECOND từ Vòng 2; **D9-TAGS bồi Vòng 4 (canonicalize operation tags)**; **D10 JSON-string param Vòng 5+**; **D11 guest-stat SSoT**; **D12 baseline error-surface**; **D13 SERVERS-BLOCK bồi Vòng 8 (root `servers[]` dẫn xuất get_url())**; **D14 INFO-CONTACT-LICENSE bồi Phase A D14 (info.contact + info.license SPDX dẫn xuất app-scoped hooks)**; **D15 EXTERNALDOCS bồi Vòng 10 (root + per-tag `externalDocs` dẫn xuất doc-base-URL từ get_url(), map per-tag→docs/imm-XX/README, fail-safe relative)**. Mọi spec module phải cross-link ADR này khi nói về OpenAPI.*
