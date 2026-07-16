# ADR-MOBILE-028 — `listAssetCategories` (**REF-DATA / CR-10c** — curate 1 path GET danh-mục Nhóm/Loại thiết bị vào mobile contract, nguồn dropdown "Nhóm/Loại thiết bị" cho lọc Asset List; **hoàn tất bộ-ba ref-data** sau `listDepartments` CR-10a + `listLocations` CR-10b)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-028 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-11 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-025** (`listDepartments` REF-DATA/CR-10a) + **ADR-MOBILE-026** (`listLocations` REF-DATA/CR-10b — cùng single-list-family ref-data, ADR này ĐỐI XỨNG hoàn-tất bộ-ba cho Nhóm/Loại thiết bị) · **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **ADR-MOBILE-021** (`listTransfers` SINGLE-shape — handler LUÔN `_ok`, 0 `_err` in-handler ⇒ KHÔNG `oneOf [Env,Error]`) · **ADR-MOBILE-023** (`getAssetPmHistory` — int-vs-bool trap Check→`integer enum[0,1]` + Select bounded no-blank → enum) · Core Doc IMM-00 [`05_API_Specification.md`](../imm-00/05_API_Specification.md) (§III.3 `list_asset_categories`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm00.py` `list_asset_categories` def@**1391** (decorator `@frappe.whitelist()` @1390) vùng ~1390-1404, `_DT_ASSET_CATEGORY = "AC Asset Category"` @`:200`; `assetcore/assetcore/doctype/ac_asset_category/ac_asset_category.json` — 4 `Check` + 3 `Int` + 1 `Percent` + `default_depreciation_method`/`depreciation_frequency` = `Select`; `assetcore/utils/response.py` `_ok`; `assetcore/tests/test_mobile_oas.py`; `assetcore/tests/test_mobile_docset.py`). **DB-VERIFY** (site `miyano`, `tabAC Asset Category` 131 rows): `depreciation_frequency` = `Monthly` × 131/131 (0 `''`/NULL) ⇒ enum-bound; `default_depreciation_method` = `''` × 105/131 + `Straight Line` × 26 ⇒ `''` phát-emit hợp-lệ. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.34 `listAssetCategories`).

---

## Context

App mobile field-tech màn **Asset List** cần lọc theo **Nhóm/Loại thiết bị** (song song 2 bộ lọc **Khoa/Phòng** §CR-10a + **Vị trí** §CR-10b đã đóng). Hiện dropdown "Nhóm/Loại thiết bị" chưa có nguồn danh-mục → filter hiển thị **chip raw Link-id** `CAT-####` (mã kỹ-thuật, người dùng không đọc được), thay vì tên nhóm/loại thiết bị tiếng Việt. Endpoint ref-data `imm00.list_asset_categories` **ĐÃ LIVE** (bare `@frappe.whitelist()`) nhưng **CHƯA có trong OAS mirror** → codegen client mobile không sinh được method `listAssetCategories` → app phải hardcode URL/parse tay. Đây là **CR-10c** (mobile Trục B — ref-data), backlog cuối của bộ-ba sau ADR-MOBILE-025/026.

Vòng này **curate 1 path GET** `list_asset_categories` vào `assetcore-mobile.openapi.yaml`, đóng contract closed-schema → codegen sinh method type-safe. **CONTRACT-ONLY**: `list_asset_categories` ĐÃ LIVE @source (whitelisted, sig **0-param** nguyên), KHÔNG đụng `.py` ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

**Cơ-chế hiện hữu (đã VERIFY @source `api/imm00.py` def@1391):**

### `list_asset_categories()` — bare whitelist, ZERO param, single-shape
- `@frappe.whitelist()` — **bare** (KHÔNG `allow_guest`, KHÔNG `methods=["POST"]`) ⇒ verb GET; guest/no-token → **dispatcher-403** (`is_whitelisted` raise `PermissionError` HTTP-403 status-line THẬT TRƯỚC handler).
- **⚠️ ZERO param** — signature `list_asset_categories()` KHÔNG có `parent` (KHÁC `list_departments(parent=None)` / `list_locations(parent=None)`). AC Asset Category **KHÔNG phải tree** (danh-mục PHẲNG) ⇒ KHÔNG lọc con theo cha, KHÔNG `AssetCategoryParent` param. `order_by="category_name asc"` (KHÁC `lft asc` của 2 sibling tree).
- Body: `frappe.get_list(_DT_ASSET_CATEGORY, fields=[16 field], order_by="category_name asc")`; **KHÔNG `_enrich`** (danh-mục phẳng, 0 Link cần resolve-tên); `return _ok(items)`.
- **KHÔNG `handle()` wrapper · KHÔNG `try/except` · KHÔNG nhánh `_err` in-handler** ⇒ handler LUÔN `_ok(items)` ⇒ **200 = SINGLE-shape** (KHÁC `searchSpareParts` `handle(svc,…)` có thể `_err` → `oneOf [Env,Error]`; giống `listTransfers`/`getAssetPmHistory`/`listDepartments`/`listLocations` LUÔN `_ok`).
- `_ok(items)` → `{success:true, data: items}` với `data` = **MẢNG TRỰC TIẾP** `list[dict]` (KHÔNG bọc `{pagination, items}`/`{asset_ref, history}` — flat raw array, mirror `listDepartments`/`listLocations` data-shape).

### Field emit — GROUNDED `fields=[...]` (VERBATIM 16 key, KHÔNG enrich)
`get_list` fields (16, không enrich): `name`, `category_name`, `category_code`, `description`, `gmdn_code`, `gmdn_term`, `default_pm_required`, `default_pm_interval_days`, `default_calibration_required`, `default_calibration_interval_days`, `default_depreciation_method`, `total_depreciation_months`, `depreciation_frequency`, `default_residual_value_pct`, `has_radiation`, `is_active`.
⇒ tổng **16 key** mỗi item (KHÁC 11-key Department/13-key Location: 0 enrich, +nhiều field khấu-hao/GMDN/compliance).

### Int-vs-bool trap (Open#1 / CR-01) — 4 `Check` field
`ac_asset_category.json`: `default_pm_required`, `default_calibration_required`, `has_radiation`, `is_active` = **`Check`**. Frappe `Check` = SQL `int` 0/1 → BE emit `0`/`1` integer, **KHÔNG** Python `bool`. ⚠️ `list_asset_categories` dùng `get_list` (KHÔNG `as_dict()`) ⇒ Check trả `0`/`1` int SẴN, **KHÔNG cần `_norm_check`** (KHÁC `get_asset_category` `as_dict()`+`_norm_check(["default_pm_required","default_calibration_required","has_radiation","is_active"])`). ⇒ contract khai `type: integer` + `enum: [0, 1]` (KHÔNG `type: boolean` — strict-codegen Dart/Kotlin deser `0`/`1` vào `bool` sẽ CRASH). Mirror `is_group`/`is_active` (ADR-025/026).

### Số nguyên/thập-phân THẬT (KHÔNG int-enum) — 3 `Int` + 1 `Percent`
`default_pm_interval_days`, `default_calibration_interval_days`, `total_depreciation_months` = **`Int`** (số ngày/tháng, đếm THẬT `0..N` — KHÔNG cờ 0/1) ⇒ `type: integer` **nullable** (KHÔNG `enum` — mirror `days_late` ADR-023 / `measurement_count` ADR R34). `default_residual_value_pct` = **`Percent`** (giá-trị còn-lại %, thập-phân) ⇒ `type: number` **nullable**. Cả 4 field không `reqd`/không default ⇒ có thể `NULL` ⇒ nullable.

### Select — 2 sub-case KHÁC NHAU (grounded @options + DB-VERIFY)
`ac_asset_category.json` có **2 field `Select`**, quyết-định enum-vs-open bằng **options leading-blank + DB-emit thực-tế** (KHÔNG đoán):

| field | options @json | leading-blank? | DB-emit (131 rows) | ⇒ contract |
|---|---|---|---|---|
| `default_depreciation_method` | `"\nStraight Line\nDouble Declining\nUnits of Production"` | **CÓ** (`\n` đầu ⇒ `''` là option hợp-lệ) | `''` × 105 + `Straight Line` × 26 (`''` phát-emit THẬT) | **`string nullable` KHÔNG `enum`** (Select-leading-blank sub-case ADR-026) |
| `depreciation_frequency` | `"Monthly\nQuarterly\nYearly"` (default `Monthly`) | **KHÔNG** (bounded 3 giá-trị) | `Monthly` × 131 (0 `''`/NULL) | **`string enum [Monthly, Quarterly, Yearly]`** (Select-bounded no-blank, mirror `overall_result` ADR-023) |

⚠️ **BA VERIFY chốt (acceptance-required):** `depreciation_frequency` KHÔNG blank-leading NHƯNG field không `reqd` → về lý-thuyết có-thể `''`. Đã query DB `tabAC Asset Category` → **131/131 = `Monthly`, 0 `''`/NULL** ⇒ AN TOÀN khai `enum`. Nếu DB về sau phát-emit `''` (record clear tay) ⇒ Self-Correction hạ về `string nullable no-enum` (như `default_depreciation_method`). Grounding-guard đã ghi ở khối evidence đầu ADR.

### Envelope + Error (`utils/response.py`)
Decision-B (ADR-MOBILE-001): lỗi nghiệp vụ = **HTTP-200 + Error envelope**. NHƯNG `list_asset_categories` **0 nhánh `_err`** ⇒ KHÔNG có Error-branch nghiệp-vụ ⇒ 200 SINGLE-shape (KHÔNG `oneOf`). Guest/no-token bị chặn ở **dispatcher** (403 status-line THẬT), KHÔNG vào handler.

## Decision

**Curate 1 path GROUNDED 1:1 `imm00.list_asset_categories`, +2 schema RIÊNG (KHÔNG param — 0-arg), 200 = SINGLE-shape `AssetCategoryListEnvelope` (KHÔNG `oneOf`), slot `{200,401,403}`.** Tag `asset` (đối xứng `listDepartments`/`listLocations` — cùng nhóm ref-data nguồn dropdown lọc màn Asset List). Path-count **59→60**, opId **59→60** (đếm thật = 60, DUY NHẤT, camelCase). CONTRACT-ONLY (pure-yaml).

1. **`listAssetCategories`** — `GET /api/method/assetcore.api.imm00.list_asset_categories` › `operationId: listAssetCategories` (dotted-path tail §8.1, camelCase, UNIQUE). Tag `asset`. **KHÔNG `requestBody`** (GET). **KHÔNG parameters** (0-arg). live-sig parity `inspect.signature(imm00.list_asset_categories).parameters == {}` (RỖNG — KHÁC `{parent}` của 2 sibling). 200 = SINGLE `$ref AssetCategoryListEnvelope` (**KHÔNG `oneOf [Env, Error]`** — handler 0 `_err`). slot `{200,401,403}`.

2. **KHÔNG param component** — `list_asset_categories` 0-arg ⇒ KHÔNG `AssetCategoryParent`/bất kỳ query param nào. (KHÁC ADR-025/026 mỗi cái +1 param `DepartmentParent`/`LocationParent`.) ⇒ blast-radius nhỏ hơn: +2 schema, +0 param.

3. **`AssetCategoryListItem`** — CLOSED (`additionalProperties: false`). EXACT **16 prop** VERBATIM field emit:

   | prop | type | ground |
   |---|---|---|
   | `name` | string | PK Link AC Category (autoname `CAT-####`). **required** |
   | `category_name` | string | Data — tên nhóm/loại thiết bị (VI); `reqd`@DocType nhưng `required==[name]` only (nhất-quán precedent) |
   | `category_code` | string | Data — mã nhóm/loại |
   | `description` | string | Small Text — mô-tả |
   | `gmdn_code` | string | Data — mã GMDN (nguồn kế-thừa Device Model, BR-00-13) |
   | `gmdn_term` | string | Data — thuật-ngữ GMDN |
   | `default_pm_required` | **integer `enum [0,1]`** | **Check** — mặc-định cần PM. KHÔNG boolean |
   | `default_pm_interval_days` | **integer** (nullable) | **Int** — chu-kỳ PM (ngày). KHÔNG enum |
   | `default_calibration_required` | **integer `enum [0,1]`** | **Check** — mặc-định cần hiệu-chuẩn. KHÔNG boolean |
   | `default_calibration_interval_days` | **integer** (nullable) | **Int** — chu-kỳ hiệu-chuẩn (ngày). KHÔNG enum |
   | `default_depreciation_method` | **string nullable (KHÔNG enum)** | **Select LEADING-BLANK** (`''`/Straight Line/Double Declining/Units of Production; DB emit `''` × 105/131 ⇒ `''` hợp-lệ) |
   | `total_depreciation_months` | **integer** (nullable) | **Int** — tổng kỳ khấu-hao (tháng). KHÔNG enum |
   | `depreciation_frequency` | **string `enum [Monthly, Quarterly, Yearly]`** | **Select bounded no-blank** (DB 131/131 `Monthly`, 0 `''`) |
   | `default_residual_value_pct` | **number** (nullable) | **Percent** — giá-trị còn-lại (%). KHÔNG integer |
   | `has_radiation` | **integer `enum [0,1]`** | **Check** — có bức-xạ (compliance). KHÔNG boolean |
   | `is_active` | **integer `enum [0,1]`** | **Check** — đang hoạt-động. KHÔNG boolean |

   `required: [name]` (chỉ PK bảo-đảm non-null; 15 field còn lại nullable — `get_list` field có thể `None`/`''`). **KHÔNG enrich key** (danh-mục phẳng, 0 Link resolve-tên).

4. **`AssetCategoryListEnvelope`** — CLOSED (`additionalProperties: false`). `required [success, data]`; `success.enum [true]`; **`data` = array `<AssetCategoryListItem>` TRẦN** (KHÔNG object-wrapper/pagination — `_ok(list)`; svc trả `list[dict]` order `category_name asc`, KHÔNG cap/paginate). `data` RỖNG `[]` hợp lệ (chưa có danh-mục) — **KHÔNG 404**. **SINGLE-shape** (KHÔNG `oneOf` — mirror `DepartmentListEnvelope` ADR-025 / `LocationListEnvelope` ADR-026).

5. **Naming guard (enum-trùng-tên ≠ domain)** — 2 schema mới `AssetCategoryListItem`/`AssetCategoryListEnvelope` (trong `#/components/schemas/`) **KHÔNG đụng** component `AssetCategory` ĐÃ tồn tại @`yaml:399` — cái đó là **`#/components/parameters/AssetCategory`** (namespace `parameters`, KHÁC namespace `schemas`; là query-filter cho `listAssets` lọc asset theo category @`yaml:9581`, KHÁC domain). Tên khác (`…ListItem`/`…ListEnvelope`) + section khác ⇒ 0 collision. Grounded LL-BE (enum-trùng-tên ≠ domain).

6. **Slot `{200,401,403}`** — bare `@whitelist` no-`allow_guest` → guest/no-token **dispatcher-403** (`403 Forbidden` SINGLE-SHAPE `FrappeRawError`); `401 Unauthorized401` (bearer hết hạn). **2 loại 403** (mobile-BE contract gotcha): OAS khai **dispatcher-403** (guest); **in-handler cap-403 KHÔNG áp** — `list_asset_categories` KHÔNG `rbac.require`/`rbac.can` trong handler (ref-data đọc mở cho mọi user đã-đăng-nhập) ⇒ 403-slot single-shape (KHÁC `reportIncident` dual-shape).

**Phạm vi membership-set (test_mobile_oas):** path ∈ `_MVP_BUSINESS_PATHS` (→ `_PATHS_REQUIRE_401` + `_PATHS_REQUIRE_403` symmetry auto +1 — slot có CẢ 401 và 403) · ∈ `_MVP_SINGLE_LIST_ENVELOPE` (single-shape marker — mirror `listDepartments`/`listLocations`/`listTransfers`) · **∉ `_MVP_LIST_ENVELOPE`** (set `oneOf`-list) · ∉ `_MVP_READ_ENVELOPE`/`_MVP_ACTION_ENVELOPE`/`_MVP_CREATE_ENVELOPE` · **c5 envelope-map += `listAssetCategories → AssetCategoryListEnvelope`** (**48→49**, giữ invariant `c5 == _MVP_BUSINESS_PATHS`) · ∈ `_RATE_LIMIT_SOURCE_MAP` (KHÔNG `@rate_limit` ⇒ VẮNG khỏi `_PATHS_REQUIRE_429`, chống bịa 429) · GET-only ∉ `_REQBODY_PATHS` + ∉ `_PARITY_VERB_ALLOWLIST` · `_EXPECTED_PATH_OPID` += dotted-path entry. **CONTRACT-ONLY**: `git diff -U0 api/imm00.py` vùng `list_asset_categories` def@1391 = **TRỐNG** (hunk diff chỉ ở `_norm_check`/version-bump, KHÔNG chạm body `list_asset_categories`) ⇒ KHÔNG reload gunicorn, KHÔNG migrate — là **[AUTO]**, KHÔNG HARD-STOP USER. 59 path hiện-hữu byte-identical; `test_oas_d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | KHÔNG curate, để endpoint LIVE nhưng thiếu contract | Codegen client KHÔNG sinh `listAssetCategories` → dropdown "Nhóm/Loại thiết bị" hardcode URL / hiển thị chip raw `CAT-####`. CR-10c treo. Endpoint LIVE @source ⇒ bồi contract = codegen-ready ngay (hoàn-tất bộ-ba). |
| B | 200 = `oneOf [AssetCategoryListEnvelope, Error]` (mirror `searchSpareParts`/account) | SAI error-mode: `list_asset_categories` **0 nhánh `_err`** (bare, KHÔNG `handle()`, KHÔNG `try/except`) ⇒ HTTP-200 CHỈ có success-shape. `oneOf` khai nhánh Error KHÔNG BAO GIỜ xảy ra = dead-branch nói dối. Mirror `listDepartments`/`listLocations` single-shape. |
| C | Thêm param `AssetCategoryParent`/`parent` (mirror ADR-025/026) | SAI signature: `inspect.signature(list_asset_categories)` = **RỖNG** (0-arg). AC Asset Category KHÔNG phải tree (danh-mục phẳng, `order_by category_name asc` KHÔNG `lft`). Khai param `parent` ⇒ codegen sinh getter gọi `?parent=` mà handler KHÔNG nhận → drift. Đây là KHÁC-BIỆT CỐT-LÕI với 2 sibling. |
| D | 4 Check = `type: boolean` | `Check` field = SQL int 0/1, `get_list` emit `0`/`1` integer (KHÔNG Python `bool`). `boolean` ⇒ strict-codegen deser `0`/`1`→`bool` CRASH (int-vs-bool trap Open#1/CR-01). `integer enum[0,1]` faithful (mirror ADR-025/026). |
| D2 | 3 Int/`total_depreciation_months` = `integer enum[0,1]` (nhầm với Check) | SAI: `Int` = số ĐẾM THẬT `0..N` (ngày/tháng), KHÔNG cờ nhị-phân. `enum[0,1]` cắt mọi giá-trị >1 = validate-FAIL. Chỉ `Check` mới int-enum[0,1]; `Int`/`Percent` = number THẬT nullable (mirror `days_late`/`measurement_count`). |
| E | `default_depreciation_method` = `enum [Straight Line, Double Declining, Units of Production]` | SAI: Select có **blank-leading** (`"\nStraight Line…"`) + **DB emit `''` × 105/131** ⇒ `''` (chưa chọn phương-pháp) là giá-trị wire HỢP-LỆ. Khai `enum` KHÔNG chứa `''` ⇒ strict-codegen validate-FAIL 105 row. ⇒ `string nullable` KHÔNG enum (Select-leading-blank sub-case ADR-026). |
| E2 | `depreciation_frequency` = `string nullable no-enum` (thận-trọng như E) | KHÔNG cần nới: Select **KHÔNG blank-leading** (`"Monthly\nQuarterly\nYearly"`, default `Monthly`) + **DB 131/131 = `Monthly`, 0 `''`** ⇒ bounded 3-giá-trị. Khai `enum` = faithful + type-safe (mirror `overall_result` ADR-023). BA đã VERIFY DB không phát `''` (nếu về sau phát → Self-Correction hạ enum, xem grounding-guard). |
| F | `data` = `{pagination, items}` (mirror `listTransfers` §8.27) | SAI shape: `list_asset_categories` `return _ok(items)` — `data` = MẢNG TRẦN, KHÔNG paginate (svc `order_by category_name asc`, KHÔNG `page`/`page_size`). `{pagination,items}` bịa khoá không có. Mirror `listDepartments`/`listLocations` data-array. |
| G | `required` = cả 16 field | `list_asset_categories` dùng `get_list` (field có thể `None`/`''` — vd `default_depreciation_method=''`, các Int có thể NULL). ⇒ chỉ `name` bảo-đảm (required[name]); 15 field còn lại optional/nullable (mirror `DepartmentListItem`/`LocationListItem` required[name]). |
| H | Tag `ref-data` (như acceptance đề-xuất) | Yaml **KHÔNG** có top-level `tags:` định-nghĩa `ref-data`; 2 sibling ĐÃ-áp-dụng (`listDepartments`@`yaml:7830` + `listLocations`@`yaml:7861`) đều `tags: [asset]`. Khai `ref-data` = lone-wolf tag lệch 2 anh-em cùng bộ-ba. ⇒ **Self-Correction:** dùng `tags: [asset]` cho đối-xứng (grounded applied-yaml precedent, KHÔNG đoán từ acceptance). |
| ✅ I | 1 path, 2 schema RIÊNG (0 param), 200 SINGLE `AssetCategoryListEnvelope` (data array trần), 4 Check int-enum[0,1] / 3 Int+1 Percent number nullable / `default_depreciation_method` string-nullable-no-enum / `depreciation_frequency` string-enum, tag `asset`, slot `{200,401,403}`, single-list-family membership | Grounded 1:1 source + DB-verify; blast-radius = +1 path +2 schema +0 param (PURE-YAML, nhỏ hơn ADR-025/026); codegen sinh 1 method đúng shape → dropdown "Nhóm/Loại thiết bị" hết chip raw id; Decision-B intact; hoàn-tất bộ-ba ref-data CR-10a/b/c. |

## Consequences

- **(+)** Dropdown "Nhóm/Loại thiết bị" lọc Asset List có nguồn danh-mục codegen-ready: `listAssetCategories` type-safe, hiển thị `category_name` (VI) thay vì chip raw `CAT-####`. **CR-10c ĐÓNG → hoàn-tất bộ-ba ref-data** (Khoa/Phòng + Vị trí + Nhóm/Loại thiết bị).
- **(+)** Contract GROUNDED 1:1 source + DB-VERIFY — `AssetCategoryListItem` 16-key VERBATIM (`fields=[16]`, 0 enrich); live-sig parity **0-param** chống drift; 4 Check `integer enum[0,1]` phản-ánh đúng `Check`; 3 Int + 1 Percent number-nullable phản-ánh đúng số THẬT; 2 Select tách đúng sub-case (leading-blank→open / bounded→enum) theo DB-emit thực-tế; SINGLE-shape phản-ánh đúng handler-0-`_err`.
- **(+)** **CONTRACT-ONLY** — `git diff -U0 api/imm00.py` vùng `list_asset_categories` = TRỐNG (hunk chỉ ở `_norm_check`/version-bump) ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO] thật, KHÔNG HARD-STOP USER); `test_oas_d12/d15/d17` UNCHANGED (pure mobile-yaml). 59 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator, SINGLE-shape hợp-lệ vì 0 `_err`); 0 dangling `$ref` (2 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`, KHÔNG cần param mới). 2 loại 403 tách rõ: OAS khai dispatcher-403 (`Forbidden` single-shape); in-handler cap-403 KHÔNG áp (ref-data đọc mở, 0 `rbac.require`).
- **(+)** **0-param** ⇒ blast-radius nhỏ hơn 2 sibling (+2 schema, KHÔNG param component). Đây là KHÁC-BIỆT cốt-lõi trong bộ-ba: người bồi ref-data kế PHẢI grep signature — tree DocType (`is_tree=1`) → có `parent`; danh-mục phẳng → 0-param `order_by <name> asc`.
- **(−)** **DB-coupling `depreciation_frequency` enum:** khai enum dựa trên DB-emit 131/131 `Monthly`. Nếu về sau có record clear field → `''`, strict-codegen validate-FAIL. Grounding-guard ghi rõ Self-Correction path (hạ về string-nullable-no-enum như `default_depreciation_method`). Guard này áp CHUNG cho mọi Select-bounded-không-reqd: enum CHỈ khi DB-verify 0-`''`.
- **(−)** `default_depreciation_method`/`depreciation_frequency` khác-shape (open-string vs enum) dù CÙNG `Select` — người bồi field Select kế PHẢI check CẢ options-leading-blank (`\n` đầu) LẪN DB-emit thực-tế, KHÔNG suy từ fieldtype đơn-thuần. Quyết-định bằng SOURCE `ac_*.json` options + DB query, KHÔNG đoán.
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `541→551` (test_mobile_oas, +10 TC class `TestMobileListAssetCategoriesContract` a..j) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `541→551` + `_GUARD_SUITE_SUM` `684→694` + `_MOBILE_OAS_TOTAL` `694+26=720` + c5 `48→49`. *(N=10 = khuyến nghị BA vì 16-field nhiều nuance typing; BE có thể tinh-chỉnh granularity TC miễn 3 counter di-chuyển ĐỒNG +N.)*

---

## Handoff BE/Test (Bước-4 — kế-hoạch, ATOMIC pure-yaml)

> **CONTRACT-ONLY** — TUYỆT ĐỐI KHÔNG đụng `api/imm00.py`/`services/imm00.py` (`list_asset_categories` ĐÃ LIVE, sig 0-param nguyên). Không reload/migrate/commit. DoD: `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_mobile_oas` + `.test_mobile_docset` = **'Ran N OK' THẬT** (guard-suite sums +10 synced).

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`):
- +1 path `GET /api/method/assetcore.api.imm00.list_asset_categories` (opId `listAssetCategories`, tag `asset`); **KHÔNG parameters**; slot `{200,401,403}` (`401 Unauthorized401`, `403 Forbidden`); 200 = SINGLE `$ref AssetCategoryListEnvelope` (**KHÔNG `oneOf`**).
- +2 schema (`AssetCategoryListItem` closed 16-prop required[name]; `AssetCategoryListEnvelope` closed `data`=array trần required[success,data]). Tái-dùng `Unauthorized401`/`Forbidden`. 0 orphan, 0 dangling. **KHÔNG** đụng component `parameters/AssetCategory` @`:399` (khác domain).

**(2) test_mobile_oas.py**: path/opId count `59→60`; `_EXPECTED_PATH_OPID` += `("/api/method/assetcore.api.imm00.list_asset_categories": ("get","listAssetCategories"))`; path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_SINGLE_LIST_ENVELOPE`; c5 map += `listAssetCategories→AssetCategoryListEnvelope` (`48→49`); `_RATE_LIMIT_SOURCE_MAP` += (no-rate-limit); +1 TC class `TestMobileListAssetCategoriesContract` (a..j, 10 TC — xem dưới); `_EXPECTED_TEST_COUNT` `541→551`.
- **TC a..j (khuyến nghị):** a) yaml path-count==60 ∧ opId-count==60. b) path GET-only + opId `listAssetCategories` + tag `asset` + ∈ `_MVP_BUSINESS_PATHS`. c) live-sig parity `inspect.signature(imm00.list_asset_categories).parameters=={}` (RỖNG) ∧ path **KHÔNG có `parameters`** (0-arg — anti-drift đảo). d) 200 = SINGLE `AssetCategoryListEnvelope` (KHÔNG `oneOf`) ∧ `data`=array trần (KHÔNG pagination/wrapper). e) `AssetCategoryListItem` closed `additionalProperties:false` EXACT 16 prop ∧ `required==[name]`. f) 4 Check (`default_pm_required`/`default_calibration_required`/`has_radiation`/`is_active`) = `integer enum[0,1]` (KHÔNG boolean) — int-vs-bool trap. g) 3 Int (`default_pm_interval_days`/`default_calibration_interval_days`/`total_depreciation_months`) = `integer` nullable KHÔNG enum ∧ `default_residual_value_pct` = `number` nullable (KHÔNG int-enum lẫn). h) `default_depreciation_method` = `string` nullable KHÔNG `enum` (Select-leading-blank) ∧ `depreciation_frequency` = `string enum [Monthly,Quarterly,Yearly]` (Select-bounded). i) slot `{200,401,403}` (`401 Unauthorized401` + `403 Forbidden` SINGLE-SHAPE — bare `@whitelist` no-allow_guest → guest dispatcher-403) ∧ membership + 401/403 symmetry + `_MVP_SINGLE_LIST_ENVELOPE` + c5==_MVP_BUSINESS_PATHS + no-dangling ∧ schema-name KHÔNG đụng `parameters/AssetCategory`. j) CONTRACT-ONLY — `git diff` `api/imm00.py` vùng `list_asset_categories` TRỐNG (pure-yaml, handler untouched) — anti-false-green.

**(3) test_mobile_docset.py**: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `541→551` · `_GUARD_SUITE_SUM` `684→694` · `_MOBILE_OAS_TOTAL` `710→720` (=694+26). ADR-MOBILE-028 registered README (TC-MOB-DOC-02 balance ADR-on-disk == ADR-in-README — **28==28**; README row đã thêm ở Bước-2 BA).

**(4) docs narrative** (ĐÃ XONG Bước-2 BA): `04-api-contract.md` (§8.34 `listAssetCategories`) + README ADR-row (ADR-MOBILE-028) + Core Doc [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §III.3 cross-ref `list_asset_categories` (+ Self-Correction: fix field-list stale 14→16, thêm `category_code`/`gmdn_term`).

**BỘ-BA REF-DATA HOÀN TẤT:** CR-10a `listDepartments` (ADR-025) + CR-10b `listLocations` (ADR-026) + CR-10c `listAssetCategories` (ADR-028) — 3 nguồn dropdown lọc màn Asset List mobile. Backlog kế: family multipart write-path `attachPmChecklistPhoto` (CR-14) / `attachCmChecklistPhoto` (CR-15) theo template ADR-027.
