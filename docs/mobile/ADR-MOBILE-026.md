# ADR-MOBILE-026 — `listLocations` (**REF-DATA / CR-10b** — curate 1 path GET danh-mục Vị trí vào mobile contract, nguồn dropdown "Vị trí" cho lọc Asset List; đối xứng CR-10a `listDepartments`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-026 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-11 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-025** (`listDepartments` REF-DATA/CR-10a — cùng single-list-family, curate ref-data GET; ADR này ĐỐI XỨNG cho Vị trí) · **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **ADR-MOBILE-021** (`listTransfers` SINGLE-shape — handler LUÔN `_ok`, 0 `_err` in-handler ⇒ KHÔNG `oneOf [Env,Error]`) · **ADR-MOBILE-023** (`getAssetPmHistory` — int-vs-bool trap Check→`integer enum[0,1]`) · Core Doc IMM-00 [`05_API_Specification.md`](../imm-00/05_API_Specification.md) (§III.3 `list_locations`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm00.py` `list_locations` @def line **1354** vùng ~1354-1368, `assetcore/assetcore/doctype/ac_location/ac_location.json` — `is_group`/`power_backup_available` = `Check`; `clinical_area_type`/`infection_control_level` = `Select` LEADING-BLANK; `assetcore/utils/response.py` `_ok`, `assetcore/api/imm00.py` `_enrich`:227-256, `assetcore/tests/guards/test_mobile_oas.py`, `assetcore/tests/guards/test_mobile_docset.py`). Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.32 `listLocations`).

---

## Context

App mobile field-tech màn **Asset List** cần lọc theo **Vị trí** (song song bộ lọc **Khoa/Phòng** đã đóng CR-10a). Hiện dropdown "Vị trí" chưa có nguồn danh-mục → filter hiển thị **chip raw Link-id** `AC-LOC-xxxx` (mã kỹ thuật, người dùng không đọc được), thay vì tên vị trí tiếng Việt. Endpoint ref-data `imm00.list_locations` **ĐÃ LIVE** (bare `@frappe.whitelist()`) nhưng **CHƯA có trong OAS mirror** → codegen client mobile không sinh được method `listLocations` → app phải hardcode URL/parse tay. Đây là **CR-10b** (mobile Trục B — ref-data), backlog kế của ADR-MOBILE-025 (`listDepartments`).

Vòng này **curate 1 path GET** `list_locations` vào `assetcore-mobile.openapi.yaml`, đóng contract closed-schema → codegen sinh method type-safe. **CONTRACT-ONLY**: `list_locations` ĐÃ LIVE @source (whitelisted, sig `{parent}` nguyên), KHÔNG đụng `.py` ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

**Cơ-chế hiện hữu (đã VERIFY @source `api/imm00.py` def@1354):**

### `list_locations(parent: str = None)` — bare whitelist, single-shape
- `@frappe.whitelist()` — **bare** (KHÔNG `allow_guest`, KHÔNG `methods=["POST"]`) ⇒ verb GET; guest/no-token → **dispatcher-403** (`is_whitelisted` raise `PermissionError` HTTP-403 status-line THẬT TRƯỚC handler).
- Body: `filters = {"parent_location": parent}` nếu `parent`; `frappe.get_list(_DT_LOCATION, filters=..., fields=[11 field], order_by="lft asc")`; 2× `_enrich`; `return _ok(items)`.
- **KHÔNG `handle()` wrapper · KHÔNG `try/except` · KHÔNG nhánh `_err` in-handler** ⇒ handler LUÔN `_ok(items)` ⇒ **200 = SINGLE-shape** (KHÁC `searchSpareParts` `handle(svc,…)` có thể `_err` → `oneOf [Env,Error]`; giống `listTransfers`/`getAssetPmHistory`/`listDepartments` LUÔN `_ok`).
- `_ok(items)` `utils/response.py:79` → `{success:true, data: items}` với `data` = **MẢNG TRỰC TIẾP** `list[dict]` (KHÔNG bọc `{pagination, items}`, KHÔNG bọc `{asset_ref, history}` — flat raw array như `searchSpareParts`/`listDepartments` data-shape NHƯNG single-shape response).

### Field emit — GROUNDED `fields=[...]` + 2 enrich (VERBATIM 13 key)
`get_list` fields (11): `name`, `location_name`, `location_code`, `parent_location`, `is_group`, `clinical_area_type`, `infection_control_level`, `power_backup_available`, `dept_head`, `contact_phone`, `notes`.
`_enrich(items, "parent_location", _DT_LOCATION, "location_name")` → key **`parent_location_name`** (default `out_field = "{field}_name"` @`_enrich:240`).
`_enrich(items, "dept_head", "User", "full_name", out_field="dept_head_name")` → key **`dept_head_name`**.
⇒ tổng **13 key** mỗi item (2 nhiều hơn `listDepartments` 11-key: Location có thêm 2 Select clinical/infection + Check `power_backup_available`, KHÔNG có `is_active`).

### Int-vs-bool trap (Open#1 / CR-01) — `is_group` + `power_backup_available`
`ac_location.json`: `is_group` = **`Check`** (tree group node, `is_tree`), `power_backup_available` = **`Check`** ("Có nguồn điện dự phòng" — hạ-tầng đặt thiết bị y tế trọng-yếu). Frappe `Check` = SQL `int` 0/1 → BE emit `0`/`1` integer, **KHÔNG** Python `bool`. ⚠️ `list_locations` dùng `get_list` (KHÔNG `as_dict()`) ⇒ Check trả `0`/`1` int SẴN, KHÔNG cần `_norm_check` (khác `get_location` `as_dict()`+`_norm_check`). ⇒ contract khai `type: integer` + `enum: [0, 1]` (KHÔNG `type: boolean` — strict-codegen Dart/Kotlin deser `0`/`1` vào `bool` sẽ CRASH). Mirror `is_group`/`is_active` (ADR-025) / `sla_breached` (ADR-022) / `is_late` (ADR-023).

### Select LEADING-BLANK — `clinical_area_type` + `infection_control_level` (KHÔNG khai enum)
`ac_location.json`: `clinical_area_type` = **`Select`** options `"\nICU\nOR\nLab\nImaging\nGeneral Ward\nStorage\nOffice"` (leading `\n` ⇒ `''` là option HỢP LỆ đầu danh sách); `infection_control_level` = **`Select`** options `"\nStandard\nEnhanced\nIsolation"` (leading blank). Vì Select có **blank leading** → giá trị wire có thể là `''` (chưa phân-loại) HỢP LỆ. ⇒ contract khai **`type: string` + `nullable: true`, KHÔNG `enum`** (KHÁC `overall_result` ADR-023 khai enum `[Pass,…]` vì Select đó KHÔNG có blank leading — bounded). Nếu khai `enum: [ICU,OR,…]` thì `''` sẽ validate-FAIL ở strict-codegen. Đây là **sub-case mới** của int/enum-fidelity: *Select-with-leading-blank ⇒ open string, KHÔNG enum-bound*.

### Envelope + Error (`utils/response.py`)
Decision-B (ADR-MOBILE-001): lỗi nghiệp vụ = **HTTP-200 + Error envelope**. NHƯNG `list_locations` **0 nhánh `_err`** ⇒ KHÔNG có Error-branch nghiệp-vụ ⇒ 200 SINGLE-shape (KHÔNG `oneOf`). Guest/no-token bị chặn ở **dispatcher** (403 status-line THẬT), KHÔNG vào handler.

## Decision

**Curate 1 path GROUNDED 1:1 `imm00.list_locations`, +2 schema RIÊNG + 1 param component, 200 = SINGLE-shape `LocationListEnvelope` (KHÔNG `oneOf`), slot `{200,401,403}`.** Tag `ref-data` (đối xứng `listDepartments` ADR-025 — nguồn dropdown lọc màn Asset List). Path-count **57→58**, opId **57→58** (đếm thật = 58, DUY NHẤT, camelCase). CONTRACT-ONLY (pure-yaml).

1. **`listLocations`** — `GET /api/method/assetcore.api.imm00.list_locations` › `operationId: listLocations` (dotted-path tail §8.1, camelCase, UNIQUE). Tag `ref-data`. **KHÔNG `requestBody`** (GET). live-sig parity `inspect.signature(imm00.list_locations) == {parent}`. 200 = SINGLE `$ref LocationListEnvelope` (**KHÔNG `oneOf [Env, Error]`** — handler 0 `_err`). slot `{200,401,403}`.

2. **Param `LocationParent`** (component `#/components/parameters/LocationParent`) — `in: query`, `required: false`, `schema: {type: string}`, **KHÔNG `default`** (signature default = `None`, KHÔNG `''`; filter chỉ áp khi truthy → `if parent:`). Description: lọc con trực-tiếp theo `parent_location` (cây vị trí); vắng → toàn bộ danh-mục phẳng order `lft asc`.

3. **`LocationListItem`** — CLOSED (`additionalProperties: false`). EXACT **13 prop** VERBATIM field emit:

   | prop | type | ground |
   |---|---|---|
   | `name` | string | PK Link AC Location (`AC-LOC-####`). **required** |
   | `location_name` | string | Data — tên vị trí (VI) |
   | `location_code` | string | Data — mã vị trí |
   | `parent_location` | string | Link AC Location (`""`/absent nếu gốc; tree) |
   | `is_group` | **integer `enum [0,1]`** | **Check** (tree group node) — KHÔNG boolean |
   | `clinical_area_type` | **string nullable (KHÔNG enum)** | **Select LEADING-BLANK** (ICU/OR/Lab/Imaging/General Ward/Storage/Office; `''` hợp lệ) |
   | `infection_control_level` | **string nullable (KHÔNG enum)** | **Select LEADING-BLANK** (Standard/Enhanced/Isolation; `''` hợp lệ) |
   | `power_backup_available` | **integer `enum [0,1]`** | **Check** (có nguồn điện dự phòng) — KHÔNG boolean |
   | `dept_head` | string | Link User (người phụ trách) |
   | `contact_phone` | string | Data (`fetch_from: dept_head.phone`) |
   | `notes` | string | Small Text |
   | `parent_location_name` | string | **enrich** AC Location.location_name (`_enrich` default `out_field` — có thể VẮNG khi cả trang không có `parent_location`, blank_missing=False early-return) |
   | `dept_head_name` | string | **enrich** User.full_name (`_enrich out_field`) |

   `required: [name]` (chỉ PK bảo-đảm non-null; enrich keys optional — `_enrich` có thể omit khi trang không có field-nguồn). 11 field còn lại nullable string / integer.

4. **`LocationListEnvelope`** — CLOSED (`additionalProperties: false`). `required [success, data]`; `success.enum [true]`; **`data` = array `<LocationListItem>` TRẦN** (KHÔNG object-wrapper/pagination — `_ok(list)`; svc trả `list[dict]` order `lft asc`, KHÔNG cap/paginate). `data` RỖNG `[]` hợp lệ (chưa có vị trí / `parent` không có con) — **KHÔNG 404**. **SINGLE-shape** (KHÔNG `oneOf` — mirror `DepartmentListEnvelope` ADR-025 / `TransferListEnvelope` ADR-021 / `AssetPmHistoryEnvelope` ADR-023).

5. **Slot `{200,401,403}`** — bare `@whitelist` no-`allow_guest` → guest/no-token **dispatcher-403** (`403 Forbidden` SINGLE-SHAPE `FrappeRawError`); `401 Unauthorized401` (bearer hết hạn). **2 loại 403** (mobile-BE contract gotcha): OAS khai **dispatcher-403** (guest); **in-handler cap-403 KHÔNG áp** — `list_locations` KHÔNG `rbac.require`/`rbac.can` trong handler (ref-data đọc mở cho mọi user đã-đăng-nhập) ⇒ 403-slot single-shape (KHÁC `reportIncident` dual-shape).

**Phạm vi membership-set (test_mobile_oas):** path ∈ `_MVP_BUSINESS_PATHS` (→ `_PATHS_REQUIRE_401` + `_PATHS_REQUIRE_403` symmetry auto +1 — slot có CẢ 401 và 403) · ∈ `_MVP_SINGLE_LIST_ENVELOPE` (single-shape marker — mirror `listDepartments`/`listTransfers`/`getAssetPmHistory`) · **∉ `_MVP_LIST_ENVELOPE`** (đó là set `oneOf`-list, `listLocations` KHÔNG oneOf) · ∉ `_MVP_READ_ENVELOPE`/`_MVP_ACTION_ENVELOPE` · **c5 envelope-map += `listLocations → LocationListEnvelope`** (giữ invariant `c5 == _MVP_BUSINESS_PATHS`) · ∈ `_RATE_LIMIT_SOURCE_MAP` (KHÔNG `@rate_limit` ⇒ VẮNG khỏi `_PATHS_REQUIRE_429`, chống bịa 429) · `_EXPECTED_PATH_OPID` += dotted-path entry. **CONTRACT-ONLY**: `git diff -U0 api/imm00.py` vùng `list_locations` = **TRỐNG** (hunk diff chỉ ở `_enrich`/`_enrich_transfer`/version-bump, KHÔNG chạm body `list_locations` def@1354) ⇒ KHÔNG reload gunicorn, KHÔNG migrate — là **[AUTO]**, KHÔNG HARD-STOP USER. 57 path hiện-hữu byte-identical; `test_oas_d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | KHÔNG curate, để endpoint LIVE nhưng thiếu contract | Codegen client KHÔNG sinh `listLocations` → dropdown "Vị trí" hardcode URL / hiển thị chip raw `AC-LOC-xxxx`. CR-10b treo. Endpoint LIVE @source ⇒ bồi contract = codegen-ready ngay (đối xứng CR-10a). |
| B | 200 = `oneOf [LocationListEnvelope, Error]` (mirror `searchSpareParts`/account) | SAI error-mode: `list_locations` **0 nhánh `_err`** (bare, KHÔNG `handle()`, KHÔNG `try/except`) ⇒ HTTP-200 CHỈ có success-shape. `oneOf` khai nhánh Error KHÔNG BAO GIỜ xảy ra = dead-branch nói dối. Mirror `listDepartments`/`listTransfers` single-shape. |
| C | `is_group`/`power_backup_available` = `type: boolean` | `Check` field = SQL int 0/1, `get_list` emit `0`/`1` integer (KHÔNG Python `bool`). `boolean` ⇒ strict-codegen deser `0`/`1`→`bool` CRASH (int-vs-bool trap Open#1/CR-01). `integer enum[0,1]` faithful (mirror ADR-025). |
| **C2** | `clinical_area_type`/`infection_control_level` = `enum [ICU,OR,…]`/`[Standard,…]` (mirror `overall_result` ADR-023 Select-enum) | SAI: 2 Select này có **blank leading** (`"\nICU\n…"`) ⇒ `''` (chưa phân-loại) là giá-trị wire HỢP LỆ. Khai `enum` KHÔNG chứa `''` ⇒ strict-codegen validate-FAIL row có `''`. `overall_result` khai enum VÌ Select đó KHÔNG blank-leading (bounded). ⇒ Select-leading-blank = **`string nullable` KHÔNG enum** (sub-case mới). |
| D | `data` = `{pagination, items}` (mirror `listTransfers`) | SAI shape: `list_locations` `return _ok(items)` — `data` = MẢNG TRẦN, KHÔNG paginate (svc `order_by lft asc`, KHÔNG `page`/`page_size`; tree ref-data trả đủ). `{pagination,items}` bịa khoá không có. Mirror `listDepartments`/`searchSpareParts` data-array. |
| E | Đưa vào `_ACCOUNT_PATHS`/bucket riêng ref-data | KHÔNG cần bucket mới: `listLocations` là read business ref-data slot `{200,401,403}` + single-shape ⇒ family HỆT `listDepartments` (∈ `_MVP_BUSINESS_PATHS` + `_MVP_SINGLE_LIST_ENVELOPE`). Tái dùng set sẵn = ít blast-radius, giữ `c5 == _MVP_BUSINESS_PATHS`. |
| F | `required` = cả 13 field | `list_locations` dùng `get_list` (field có thể `None`/`""`) + `_enrich` (`parent_location_name`/`dept_head_name` có thể VẮNG khi trang không có field-nguồn, blank_missing=False early-return). ⇒ chỉ `name` bảo-đảm (required[name]); phần còn lại optional (mirror `DepartmentListItem`/`TransferListItem` required[name]). |
| ✅ G | 1 path, 2 schema RIÊNG + 1 param, 200 SINGLE `LocationListEnvelope` (data array trần), `is_group`/`power_backup_available` int-enum[0,1], 2 Select-leading-blank string-nullable-no-enum, slot `{200,401,403}`, single-list-family membership | Grounded 1:1 source; blast-radius = +1 path +2 schema +1 param (PURE-YAML); codegen sinh 1 method đúng shape → dropdown "Vị trí" hết chip raw id; Decision-B intact; đóng CR-10b đối xứng CR-10a. |

## Consequences

- **(+)** Dropdown "Vị trí" lọc Asset List có nguồn danh-mục codegen-ready: `listLocations` type-safe, hiển thị `location_name` (VI) thay vì chip raw `AC-LOC-xxxx`. CR-10b ĐÓNG, đối xứng CR-10a.
- **(+)** Contract GROUNDED 1:1 source — `LocationListItem` 13-key VERBATIM (`fields=[11]` + 2 enrich); live-sig parity `{parent}` chống drift; `is_group`/`power_backup_available` `integer enum[0,1]` phản-ánh đúng `Check`; 2 Select-leading-blank = string-nullable-no-enum phản-ánh đúng `''`-valid; SINGLE-shape phản-ánh đúng handler-0-`_err`.
- **(+)** **CONTRACT-ONLY** — `git diff -U0 api/imm00.py` vùng `list_locations` = TRỐNG (hunk chỉ ở `_enrich`/`_enrich_transfer`/version-bump) ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO] thật, KHÔNG HARD-STOP USER); `test_oas_d12/d15/d17` UNCHANGED (pure mobile-yaml). 57 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator, SINGLE-shape hợp-lệ vì 0 `_err`); 0 dangling `$ref` (2 schema + 1 param mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`). 2 loại 403 tách rõ: OAS khai dispatcher-403 (`Forbidden` single-shape); in-handler cap-403 KHÔNG áp (ref-data đọc mở, 0 `rbac.require`).
- **(−)** **Sub-case mới Select-leading-blank** (`clinical_area_type`/`infection_control_level` = string-nullable-no-enum): người bồi field Select kế PHẢI grep options — leading `\n` (blank đầu) ⇒ open string; KHÔNG blank-leading (bounded, vd `overall_result`) ⇒ enum. Quyết-định bằng SOURCE `ac_*.json` options, KHÔNG đoán.
- **(−)** `listLocations` vào `_MVP_SINGLE_LIST_ENVELOPE` (KHÔNG `_MVP_LIST_ENVELOPE` oneOf) — người bồi list-endpoint kế PHẢI phân biệt: handler `handle()`/`try-except` (có `_err`) → oneOf `_MVP_LIST_ENVELOPE`; handler LUÔN `_ok` (0 `_err`) → SINGLE `_MVP_SINGLE_LIST_ENVELOPE`. Quyết-định bằng SOURCE (grep `_err`/`handle`/`try`), KHÔNG đoán.
- **(−)** `parent_location_name`/`dept_head_name` optional (không `required`) — codegen sinh nullable/optional getter; client PHẢI null-safe (mirror `DepartmentListItem`/`TransferListItem` enrich fields). Đây là hệ-quả `_enrich` blank_missing=False (early-return omit key khi trang không có field-nguồn) — KHÔNG bug.
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `522→531` (test_mobile_oas, +9 TC class `TestMobileListLocationsContract` a..i) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `522→531` + `_GUARD_SUITE_SUM` `665→674` + `_MOBILE_OAS_TOTAL` `691→700` (= `_GUARD_SUITE_SUM` 674 + preflight 26) + c5 `46→47`. *(N=9 = khuyến nghị BA; BE có thể tinh-chỉnh granularity TC miễn 3 counter di-chuyển ĐỒNG +N.)*

---

## Handoff BE/Test (Bước-4 — kế-hoạch, ATOMIC pure-yaml)

> **CONTRACT-ONLY** — TUYỆT ĐỐI KHÔNG đụng `api/imm00.py`/`services/imm00.py` (`list_locations` ĐÃ LIVE, sig `{parent}` nguyên). Không reload/migrate/commit. DoD: `bench --site miyano run-tests --app assetcore --module assetcore.tests.guards.test_mobile_oas` + `.test_mobile_docset` = **'Ran N OK' THẬT** (guard-suite sums +9 synced).

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`):
- +1 path `GET /api/method/assetcore.api.imm00.list_locations` (opId `listLocations`, tag `ref-data`); slot `{200,401,403}` (`401 Unauthorized401`, `403 Forbidden`); 200 = SINGLE `$ref LocationListEnvelope` (**KHÔNG `oneOf`**); param `$ref LocationParent`.
- +2 schema (`LocationListItem` closed 13-prop required[name]; `LocationListEnvelope` closed `data`=array trần required[success,data]) + 1 param component (`LocationParent` query optional string no-default). Tái-dùng `Unauthorized401`/`Forbidden`. 0 orphan, 0 dangling.

**(2) test_mobile_oas.py**: path/opId count `57→58`; `_EXPECTED_PATH_OPID` += `("/api/method/assetcore.api.imm00.list_locations": ("get","listLocations"))`; path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_SINGLE_LIST_ENVELOPE`; c5 map += `listLocations→LocationListEnvelope` (`46→47`); `_RATE_LIMIT_SOURCE_MAP` += (no-rate-limit); +1 TC class `TestMobileListLocationsContract` (a..i, 9 TC — xem dưới); `_EXPECTED_TEST_COUNT` `522→531`.
- **TC a..i (khuyến nghị):** a) yaml path-count==58 ∧ opId-count==58. b) path GET-only + opId `listLocations` + tag `ref-data` + ∈ `_MVP_BUSINESS_PATHS`. c) live-sig parity `inspect.signature(imm00.list_locations)=={parent}` + param `LocationParent` query optional string no-default. d) 200 = SINGLE `LocationListEnvelope` (KHÔNG `oneOf`) ∧ `data`=array trần (KHÔNG pagination/wrapper). e) `LocationListItem` closed `additionalProperties:false` EXACT 13 prop ∧ `required==[name]`. f) `is_group`+`power_backup_available` = `integer enum[0,1]` (KHÔNG boolean) — int-vs-bool trap; ∧ `clinical_area_type`+`infection_control_level` = `string` (nullable) KHÔNG `enum` (Select-leading-blank). g) slot `{200,401,403}` (`401 Unauthorized401` + `403 Forbidden` SINGLE-SHAPE — bare `@whitelist` no-allow_guest → guest dispatcher-403). h) membership + 401/403 symmetry + `_MVP_SINGLE_LIST_ENVELOPE` + c5==_MVP_BUSINESS_PATHS + no-dangling. i) CONTRACT-ONLY — `git diff` `api/imm00.py` vùng `list_locations` TRỐNG (pure-yaml, handler untouched) — anti-false-green.

**(3) test_mobile_docset.py**: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `522→531` · `_GUARD_SUITE_SUM` `665→674` · `_MOBILE_OAS_TOTAL` `691→700` (=674+26). ADR-MOBILE-026 registered README (TC-MOB-DOC-02 glob động — README row bắt-buộc, đã thêm ở Bước-2 BA).

**(4) docs narrative** (ĐÃ XONG Bước-2 BA): `04-api-contract.md` (§8.32 `listLocations`) + README ADR-row (ADR-MOBILE-026) + Core Doc [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §III.3 cross-ref `list_locations`.

**BACKLOG (vòng kế):** `listAssetCategories` (`imm00.list_asset_categories` LIVE — dropdown "Danh mục" lọc Asset List) — ref-data cuối bộ-ba, cùng single-shape family. LƯU Ý: `list_asset_categories()` **0 param** (KHÔNG `parent` — flat, KHÔNG tree) + `AssetCategoryListItem` ~15 field NHIỀU Check (`default_pm_required`/`default_calibration_required`/`has_radiation`/`is_active` → int-enum[0,1]) ⇒ khác granularity, grep `fields=[…]`@`list_asset_categories` trước khi đặc tả.
