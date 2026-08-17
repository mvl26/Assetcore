# ADR-MOBILE-025 — `listDepartments` (**REF-DATA / CR-10a** — curate 1 path GET danh-mục Khoa/Phòng vào mobile contract, nguồn dropdown "Khoa/Phòng" cho lọc Asset List)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-025 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-11 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **ADR-MOBILE-021** (`listTransfers` SINGLE-shape — handler LUÔN `_ok`, 0 `_err` in-handler ⇒ KHÔNG `oneOf [Env,Error]`) · **ADR-MOBILE-023** (`getAssetPmHistory` single-shape list, int-vs-bool trap Check→`integer enum[0,1]`) · Core Doc IMM-00 [`05_API_Specification.md`](../imm-00/05_API_Specification.md) (§III.3 `list_departments`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm00.py` `list_departments` @vùng ~1378-1387, `assetcore/assetcore/doctype/ac_department/ac_department.json` — `is_group`/`is_active` = `Check`, `is_tree=1`, `assetcore/utils/response.py` `_ok`, `assetcore/tests/guards/test_mobile_oas.py`, `assetcore/tests/guards/test_mobile_docset.py`). Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.31 `listDepartments`).

---

## Context

App mobile field-tech màn **Asset List** cần lọc theo **Khoa/Phòng**. Hiện dropdown "Khoa/Phòng" chưa có nguồn danh-mục → filter hiển thị **chip raw Link-id** `AC-DEPT-xxxx` (mã kỹ thuật, người dùng không đọc được), thay vì tên khoa/phòng tiếng Việt. Endpoint ref-data `imm00.list_departments` **ĐÃ LIVE** (bare `@frappe.whitelist()`) nhưng **CHƯA có trong OAS mirror** → codegen client mobile không sinh được method `listDepartments` → app phải hardcode URL/parse tay. Đây là **CR-10a** (mobile Trục B — ref-data).

Vòng này **curate 1 path GET** `list_departments` vào `assetcore-mobile.openapi.yaml`, đóng contract closed-schema → codegen sinh method type-safe. **CONTRACT-ONLY**: `list_departments` ĐÃ LIVE @source, KHÔNG đụng `.py` ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

**Cơ-chế hiện hữu (đã VERIFY @source `api/imm00.py`):**

### `list_departments(parent: str = None)` — bare whitelist, single-shape
- `@frappe.whitelist()` — **bare** (KHÔNG `allow_guest`, KHÔNG `methods=["POST"]`) ⇒ verb GET; guest/no-token → **dispatcher-403** (`is_whitelisted` raise `PermissionError` HTTP-403 status-line THẬT TRƯỚC handler).
- Body: `filters = {"parent_department": parent}` nếu `parent`; `frappe.get_list(_DT_DEPARTMENT, filters=..., fields=[9 field], order_by="lft asc")`; 2× `_enrich`; `return _ok(items)`.
- **KHÔNG `handle()` wrapper · KHÔNG `try/except` · KHÔNG nhánh `_err` in-handler** ⇒ handler LUÔN `_ok(items)` ⇒ **200 = SINGLE-shape** (KHÁC `searchSpareParts` `handle(svc,…)` có thể `_err` → `oneOf [Env,Error]`; giống `listTransfers`/`getAssetPmHistory` LUÔN `_ok`).
- `_ok(items)` `utils/response.py:79` → `{success:true, data: items}` với `data` = **MẢNG TRỰC TIẾP** `list[dict]` (KHÔNG bọc `{pagination, items}` như `listTransfers`, KHÔNG bọc `{asset_ref, history}` như `getAssetPmHistory` — flat raw array như `searchSpareParts` data-shape NHƯNG single-shape response).

### Field emit — GROUNDED `fields=[...]` + 2 enrich (VERBATIM 11 key)
`get_list` fields (9): `name`, `department_name`, `department_code`, `parent_department`, `is_group`, `dept_head`, `phone`, `email`, `is_active`.
`_enrich(items, "parent_department", _DT_DEPARTMENT, "department_name")` → key **`parent_department_name`**.
`_enrich(items, "dept_head", "User", "full_name", out_field="dept_head_name")` → key **`dept_head_name`**.
⇒ tổng **11 key** mỗi item.

### Int-vs-bool trap (Open#1 / CR-01) — `is_group` + `is_active`
`ac_department.json`: `is_group` = **`Check`** (tree group node, `is_tree=1`), `is_active` = **`Check`** ("Đang hoạt động"). Frappe `Check` = SQL `int` 0/1 → BE emit `0`/`1` integer, **KHÔNG** Python `bool`. ⇒ contract khai `type: integer` + `enum: [0, 1]` (KHÔNG `type: boolean` — strict-codegen Dart/Kotlin deser `0`/`1` vào `bool` sẽ CRASH). Mirror `sla_breached` (ADR-022) / `is_late` (ADR-023).

### Envelope + Error (`utils/response.py`)
Decision-B (ADR-MOBILE-001): lỗi nghiệp vụ = **HTTP-200 + Error envelope**. NHƯNG `list_departments` **0 nhánh `_err`** ⇒ KHÔNG có Error-branch nghiệp-vụ ⇒ 200 SINGLE-shape (KHÔNG `oneOf`). Guest/no-token bị chặn ở **dispatcher** (403 status-line THẬT), KHÔNG vào handler.

## Decision

**Curate 1 path GROUNDED 1:1 `imm00.list_departments`, +2 schema RIÊNG + 1 param component, 200 = SINGLE-shape `DepartmentListEnvelope` (KHÔNG `oneOf`), slot `{200,401,403}`.** Tag `asset` (ref-data cho màn Asset List). Path-count **56→57**, opId **56→57** (đếm thật = 57, DUY NHẤT, camelCase). CONTRACT-ONLY (pure-yaml).

1. **`listDepartments`** — `GET /api/method/assetcore.api.imm00.list_departments` › `operationId: listDepartments` (dotted-path tail §8.1, camelCase, UNIQUE). Tag `asset`. **KHÔNG `requestBody`** (GET). live-sig parity `inspect.signature(imm00.list_departments) == {parent}`. 200 = SINGLE `$ref DepartmentListEnvelope` (**KHÔNG `oneOf [Env, Error]`** — handler 0 `_err`). slot `{200,401,403}`.

2. **Param `DepartmentParent`** (component `#/components/parameters/DepartmentParent`) — `in: query`, `required: false`, `schema: {type: string}`, **KHÔNG `default`** (signature default = `None`, KHÔNG `''`; filter chỉ áp khi truthy → `if parent:`). Description: lọc con trực-tiếp theo `parent_department` (cây khoa/phòng); vắng → toàn bộ danh-mục phẳng order `lft asc`.

3. **`DepartmentListItem`** — CLOSED (`additionalProperties: false`). EXACT **11 prop** VERBATIM field emit:

   | prop | type | ground |
   |---|---|---|
   | `name` | string | PK Link AC Department (`AC-DEPT-####`). **required** |
   | `department_name` | string | Data — tên khoa/phòng (VI) |
   | `department_code` | string | Data — mã khoa/phòng |
   | `parent_department` | string | Link AC Department (`""`/absent nếu gốc; tree) |
   | `is_group` | **integer `enum [0,1]`** | **Check** (tree group node) — KHÔNG boolean |
   | `dept_head` | string | Link User (trưởng khoa/phòng) |
   | `phone` | string | Data |
   | `email` | string | Data |
   | `is_active` | **integer `enum [0,1]`** | **Check** ("Đang hoạt động") — KHÔNG boolean |
   | `parent_department_name` | string | **enrich** AC Department.department_name (`_enrich` — có thể VẮNG khi cả trang không có `parent_department`, blank_missing=False early-return) |
   | `dept_head_name` | string | **enrich** User.full_name (`_enrich out_field`) |

   `required: [name]` (chỉ PK bảo-đảm non-null; enrich keys optional — `_enrich` có thể omit khi trang không có field-nguồn).

4. **`DepartmentListEnvelope`** — CLOSED (`additionalProperties: false`). `required [success, data]`; `success.enum [true]`; **`data` = array `<DepartmentListItem>` TRẦN** (KHÔNG object-wrapper/pagination — `_ok(list)`; svc trả `list[dict]` order `lft asc`, KHÔNG cap/paginate). `data` RỖNG `[]` hợp lệ (chưa có khoa/phòng / `parent` không có con) — **KHÔNG 404**. **SINGLE-shape** (KHÔNG `oneOf` — mirror `TransferListEnvelope` ADR-021 / `AssetPmHistoryEnvelope` ADR-023).

5. **Slot `{200,401,403}`** — bare `@whitelist` no-`allow_guest` → guest/no-token **dispatcher-403** (`403 Forbidden` SINGLE-SHAPE `FrappeRawError`); `401 Unauthorized401` (bearer hết hạn). **2 loại 403** (mobile-BE contract gotcha): OAS khai **dispatcher-403** (guest); **in-handler cap-403 KHÔNG áp** — `list_departments` KHÔNG `rbac.require`/`rbac.can` trong handler (ref-data đọc mở cho mọi user đã-đăng-nhập) ⇒ 403-slot single-shape (KHÁC `reportIncident` dual-shape).

**Phạm vi membership-set (test_mobile_oas):** path ∈ `_MVP_BUSINESS_PATHS` (→ `_PATHS_REQUIRE_401` + `_PATHS_REQUIRE_403` symmetry auto +1 — slot có CẢ 401 và 403) · ∈ `_MVP_SINGLE_LIST_ENVELOPE` (single-shape marker — mirror `listTransfers`/`getAssetPmHistory`) · **∉ `_MVP_LIST_ENVELOPE`** (đó là set `oneOf`-list, `listDepartments` KHÔNG oneOf) · ∉ `_MVP_READ_ENVELOPE`/`_MVP_ACTION_ENVELOPE` · **c5 envelope-map += `listDepartments → DepartmentListEnvelope`** (giữ invariant `c5 == _MVP_BUSINESS_PATHS`) · ∈ `_RATE_LIMIT_SOURCE_MAP` (KHÔNG `@rate_limit` ⇒ VẮNG khỏi `_PATHS_REQUIRE_429`, chống bịa 429) · `_EXPECTED_PATH_OPID` += dotted-path entry. **CONTRACT-ONLY**: `git diff -U0 api/imm00.py` vùng `list_departments` = **TRỐNG** (hunk diff chỉ ở `_enrich`/version-bump, KHÔNG chạm body `list_departments`) ⇒ KHÔNG reload gunicorn, KHÔNG migrate — là **[AUTO]**, KHÔNG HARD-STOP USER. 56 path hiện-hữu byte-identical; `test_oas_d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | KHÔNG curate, để endpoint LIVE nhưng thiếu contract | Codegen client KHÔNG sinh `listDepartments` → dropdown "Khoa/Phòng" hardcode URL / hiển thị chip raw `AC-DEPT-xxxx`. CR-10a treo. Endpoint LIVE @source ⇒ bồi contract = codegen-ready ngay. |
| B | 200 = `oneOf [DepartmentListEnvelope, Error]` (mirror `searchSpareParts`/account) | SAI error-mode: `list_departments` **0 nhánh `_err`** (bare, KHÔNG `handle()`, KHÔNG `try/except`) ⇒ HTTP-200 CHỈ có success-shape. `oneOf` khai nhánh Error KHÔNG BAO GIỜ xảy ra = dead-branch nói dối. `searchSpareParts` oneOf VÌ `handle(svc,…)` có thể `_err`; `list_departments` KHÔNG. Mirror `listTransfers`/`getAssetPmHistory` single-shape. |
| C | `is_group`/`is_active` = `type: boolean` | `Check` field = SQL int 0/1, BE emit `0`/`1` integer (KHÔNG Python `bool`). `boolean` ⇒ strict-codegen Dart/Kotlin deser `0`/`1`→`bool` CRASH (int-vs-bool trap Open#1/CR-01). `integer enum[0,1]` faithful (mirror `sla_breached` ADR-022 / `is_late` ADR-023). |
| D | `data` = `{pagination, items}` (mirror `listTransfers`) | SAI shape: `list_departments` `return _ok(items)` — `data` = MẢNG TRẦN, KHÔNG paginate (svc `order_by lft asc`, KHÔNG `page`/`page_size`; tree ref-data trả đủ). `{pagination,items}` bịa khoá không có. Mirror `searchSpareParts` data-array. |
| E | Đưa vào `_ACCOUNT_PATHS`/bucket riêng ref-data (mirror ADR-024) | KHÔNG cần bucket mới: `listDepartments` là read business ref-data có slot `{200,401,403}` + single-shape envelope ⇒ family HỆT `listTransfers`/`getAssetPmHistory` (∈ `_MVP_BUSINESS_PATHS` + `_MVP_SINGLE_LIST_ENVELOPE`). `_ACCOUNT_PATHS` sinh ra VÌ account là `oneOf` self-service ∉ single-list-family. Tái dùng set sẵn = ít blast-radius, giữ `c5 == _MVP_BUSINESS_PATHS`. |
| F | `required` = cả 11 field (mirror `SearchSparePartItem` required-10) | `SearchSparePartItem` required đủ vì mỗi row = dict-literal vô-điều-kiện. `list_departments` dùng `get_list` (field có thể `None`/`""`) + `_enrich` (parent_department_name/dept_head_name có thể VẮNG khi trang không có field-nguồn, blank_missing=False early-return). ⇒ chỉ `name` bảo-đảm (required[name]); phần còn lại optional (mirror `TransferListItem` required[name]). |
| ✅ G | 1 path, 2 schema RIÊNG + 1 param, 200 SINGLE `DepartmentListEnvelope` (data array trần), `is_group`/`is_active` int-enum[0,1], slot `{200,401,403}`, single-list-family membership | Grounded 1:1 source; blast-radius = +1 path +2 schema +1 param (PURE-YAML); codegen sinh 1 method đúng shape → dropdown "Khoa/Phòng" hết chip raw id; Decision-B intact; đóng CR-10a. |

## Consequences

- **(+)** Dropdown "Khoa/Phòng" lọc Asset List có nguồn danh-mục codegen-ready: `listDepartments` type-safe, hiển thị `department_name` (VI) thay vì chip raw `AC-DEPT-xxxx`. CR-10a ĐÓNG.
- **(+)** Contract GROUNDED 1:1 source — `DepartmentListItem` 11-key VERBATIM (`fields=[9]` + 2 enrich); live-sig parity `{parent}` chống drift; `is_group`/`is_active` `integer enum[0,1]` phản-ánh đúng `Check`; SINGLE-shape phản-ánh đúng handler-0-`_err`.
- **(+)** **CONTRACT-ONLY** — `git diff -U0 api/imm00.py` vùng `list_departments` = TRỐNG (hunk chỉ ở `_enrich`/version-bump) ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO] thật, KHÔNG HARD-STOP USER); `test_oas_d12/d15/d17` UNCHANGED (pure mobile-yaml). 56 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator, SINGLE-shape hợp-lệ vì 0 `_err`); 0 dangling `$ref` (2 schema + 1 param mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`). 2 loại 403 tách rõ: OAS khai dispatcher-403 (`Forbidden` single-shape); in-handler cap-403 KHÔNG áp (ref-data đọc mở, 0 `rbac.require`).
- **(−)** `listDepartments` vào `_MVP_SINGLE_LIST_ENVELOPE` (KHÔNG `_MVP_LIST_ENVELOPE` oneOf) — người bồi list-endpoint kế PHẢI phân biệt: handler `handle()`/`try-except` (có `_err`) → oneOf `_MVP_LIST_ENVELOPE`; handler LUÔN `_ok` (0 `_err`) → SINGLE `_MVP_SINGLE_LIST_ENVELOPE`. Quyết-định bằng SOURCE (grep `_err`/`handle`/`try`), KHÔNG đoán.
- **(−)** `parent_department_name`/`dept_head_name` optional (không `required`) — codegen sinh nullable/optional getter; client PHẢI null-safe (mirror `TransferListItem` enrich fields). Đây là hệ-quả `_enrich` blank_missing=False (early-return omit key khi trang không có field-nguồn) — KHÔNG bug.
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `513→522` (test_mobile_oas, +9 TC class `TestMobileListDepartmentsContract` a..i) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `513→522` + `_GUARD_SUITE_SUM` `656→665` + `_MOBILE_OAS_TOTAL` `682→691` (= `_GUARD_SUITE_SUM` 665 + preflight 26). *(N=9 = khuyến nghị BA; BE có thể tinh-chỉnh granularity TC miễn 3 counter di-chuyển ĐỒNG +N.)*

---

## Handoff BE/Test (Bước-4 — kế-hoạch, ATOMIC pure-yaml)

> **CONTRACT-ONLY** — TUYỆT ĐỐI KHÔNG đụng `api/imm00.py`/`services/imm00.py` (`list_departments` ĐÃ LIVE). Không reload/migrate/commit. DoD: `bench --site miyano run-tests --app assetcore --module assetcore.tests.guards.test_mobile_oas` + `.test_mobile_docset` = **'Ran N OK' THẬT** (guard-suite sums +9 synced).

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`):
- +1 path `GET /api/method/assetcore.api.imm00.list_departments` (opId `listDepartments`, tag `asset`); slot `{200,401,403}` (`401 Unauthorized401`, `403 Forbidden`); 200 = SINGLE `$ref DepartmentListEnvelope` (**KHÔNG `oneOf`**); param `$ref DepartmentParent`.
- +2 schema (`DepartmentListItem` closed 11-prop required[name]; `DepartmentListEnvelope` closed `data`=array trần required[success,data]) + 1 param component (`DepartmentParent` query optional string no-default). Tái-dùng `Unauthorized401`/`Forbidden`. 0 orphan, 0 dangling.

**(2) test_mobile_oas.py**: path/opId count `56→57`; `_EXPECTED_PATH_OPID` += `("/api/method/assetcore.api.imm00.list_departments": ("get","listDepartments"))`; path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_SINGLE_LIST_ENVELOPE`; c5 map += `listDepartments→DepartmentListEnvelope`; `_RATE_LIMIT_SOURCE_MAP` += (no-rate-limit); +1 TC class `TestMobileListDepartmentsContract` (a..i, 9 TC — xem dưới); `_EXPECTED_TEST_COUNT` `513→522`.
- **TC a..i (khuyến nghị):** a) yaml path-count==57 ∧ opId-count==57. b) path GET-only + opId `listDepartments` + tag `asset` + ∈ `_MVP_BUSINESS_PATHS`. c) live-sig parity `inspect.signature(imm00.list_departments)=={parent}` + param `DepartmentParent` query optional string no-default. d) 200 = SINGLE `DepartmentListEnvelope` (KHÔNG `oneOf`) ∧ `data`=array trần (KHÔNG pagination/wrapper). e) `DepartmentListItem` closed `additionalProperties:false` EXACT 11 prop ∧ `required==[name]`. f) `is_group`+`is_active` = `integer enum[0,1]` (KHÔNG boolean) — int-vs-bool trap. g) slot `{200,401,403}` (`401 Unauthorized401` + `403 Forbidden` SINGLE-SHAPE — bare `@whitelist` no-allow_guest → guest dispatcher-403). h) membership + 401/403 symmetry + `_MVP_SINGLE_LIST_ENVELOPE` + c5==_MVP_BUSINESS_PATHS + no-dangling. i) CONTRACT-ONLY — `git diff` `api/imm00.py` vùng `list_departments` TRỐNG (pure-yaml, handler untouched) — anti-false-green.

**(3) test_mobile_docset.py**: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `513→522` · `_GUARD_SUITE_SUM` `656→665` · `_MOBILE_OAS_TOTAL` `682→691` (=665+26). ADR-MOBILE-025 registered README (TC-MOB-DOC-02).

**(4) docs narrative**: `04-api-contract.md` (§8.31 `listDepartments`) + README ADR-row (ADR-MOBILE-025) + Core Doc [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §III.3 cross-ref.

**BACKLOG (vòng kế):** `listLocations` (`imm00.list_locations` LIVE, cùng pattern ref-data — nguồn dropdown "Vị trí" lọc Asset List) + `listAssetCategories` (`imm00.list_asset_categories` LIVE — dropdown "Danh mục") — đối xứng ref-data, cùng single-shape family.
