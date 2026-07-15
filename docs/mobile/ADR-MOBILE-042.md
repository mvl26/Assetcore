# ADR-MOBILE-042 — `getAssetDepreciationSchedule` (`imm00.get_depreciation_schedule`) curate vào OAS mirror (**CR-11e · asset-detail sub-tab #5 "Khấu hao"** — bồi ĐÚNG 1 GET-read path trả lịch khấu hao (child `AC Asset Depreciation Schedule`) + tổng-hợp + thông-tin khấu hao của 1 asset; sub-tab THỨ NĂM (CUỐI) của CR-11 sau `getAssetKpi` (ADR-038) + `getAssetDowntimeMetrics` (ADR-039) + `getAssetVerifyChain` (ADR-040) + `getAssetCommissioningOrigin` (ADR-041); **HOÀN TẤT bộ-năm CR-11**; **LẦN ĐẦU success-data = WRAPPER 4-key với 3 nested-schema** — `{asset, asset_info:object|null, rows[], summary}`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-042 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-13 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến trên HTTP-200 body `Error`, route theo `body.success`/`body.http_status`; KHÔNG discriminator, closed-schema oneOf) · **sibling trực-tiếp**: **ADR-MOBILE-041** (`getAssetCommissioningOrigin` — CÙNG asset-detail sub-tab flow-2 CR-11, GET bare `@whitelist`, asset∄ → HTTP-200 nhánh Error, 200 = oneOf `[Envelope, Error]`; **nguồn idiom nullable-ref wrapper** `{type:object, nullable:true, allOf:[$ref]}` cho `asset_info`) + **ADR-MOBILE-038** (`getAssetKpi` — required = subset always-non-null, nullable-value ∉ required; FINANCIAL curate-verbatim precedent `total_repair_cost`) + **ADR-MOBILE-028** (`listAssetCategories` — sub-case Select bounded no-blank → `enum` DB-verified vs Select leading-blank → string nullable no-enum) · Core Doc IMM-00 [`04-api-contract.md`](./04-api-contract.md) §8.44 (getAssetDepreciationSchedule) + [`docs/imm-00/05_API_Specification.md`](../imm-00/05_API_Specification.md) §mobile-depreciation-schedule |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (@2026-07-13). **1 tầng handler** `get_depreciation_schedule(asset_name: str) -> dict` def@`assetcore/api/imm00.py:2961-2989` — bare `@frappe.whitelist()` (GET-ok, no `allow_guest` → guest dispatcher-403); thân **tự-chứa** (KHÔNG `_handle`/service): `if not frappe.db.exists("AC Asset", asset_name): return _err(_("Asset not found"), 404)` @`:2964-2965` (asset∄ → Error envelope HTTP-200 Decision-B); `rows = frappe.get_all("AC Asset Depreciation Schedule", filters={parent,parenttype}, fields=[9], order_by="period_number asc", limit_page_length=500)` @`:2966-2974`; `summary = {total_periods:len(rows), executed_periods:sum(status==Executed), pending_periods:sum(status==Pending), total_depreciated:sum(depreciation_amount cho Executed)}` @`:2975-2981`; `asset = frappe.db.get_value("AC Asset", asset_name, [9 field], as_dict=True) or {}` @`:2982-2988` (`or {}` coalesce); `return _ok({"asset": asset_name, "asset_info": asset, "rows": rows, "summary": summary})` @`:2989`. `git diff HEAD` `api/imm00.py` (hàm `get_depreciation_schedule`, AST byte-identical HEAD↔working) = TRỐNG round NÀY ⇒ backend ĐÃ LIVE, thay đổi CHỈ ở OAS mirror + test + doc. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Nguồn yêu cầu: `assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` CR-11e.

---

## ⚠️ Reconciliation đánh-số (đa-phiên) — BE Bước-4 ĐỌC TRƯỚC

Đề mục Bước-2 (vòng 31) ghi baseline: `path/opId 69→70`, `_EXPECTED_TEST_COUNT 656→664`, `3 docset counter +8`. **VERIFY @source @2026-07-13** (grep-verify TRƯỚC bump — đa-phiên race dời số; ĐỌC giá trị HIỆN TẠI lúc build, KHÔNG hardcode từ brief):

| Hạng mục | LIVE baseline @source (đã grep) | CR-11e target |
|---|---|---|
| ADR số | **041 = getAssetCommissioningOrigin** (đã tồn tại đĩa + README) | **042** (NEW) |
| path/opId | **69** (`grep -c operationId yaml` = 69) | **69→70** |
| c5 (`_MVP_READ_ENVELOPE`/map) | **58** (getAssetCommissioningOrigin đã 57→58) | **58→59** |
| `_EXPECTED_TEST_COUNT` | **656** (@`test_mobile_oas.py:212`) | **656→664** (+8 TC) |
| `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` | **656** | **656→664** |
| `_GUARD_SUITE_SUM` | **799** | **799→807** |
| `_MOBILE_OAS_TOTAL` | **825** | **825→833** |
| README ADR balance | **41 file / 41 index-row** | **42==42** |

> Grounded @2026-07-13: 2 inline literal `_EXPECTED_TEST_COUNT == 656` @`test_mobile_oas.py` (receivecert/cancelcal meta) bump 656→664; **139 literal** path/opId `69` (token `, 69,`/`, 69)` — `len(paths)`/`len(ids)`/`len(set(ids))`/`len(spec.get("paths"))`/`len(ops)`/`actual_paths`/`len(op_ids)`) bulk-bump 69→70; 3 c5 `58` + 1 parity-business `58` bump 58→59; 4 backward-compat opId-set-minus (`getAssetPmHistory`/`listDepartments`/`listLocations` = `68→69`, `{listTransfers,getTransfer}` = `67→68`); **opId convention-map SSoT (`_EXPECTED` @`:219`) THÊM** `get_depreciation_schedule → getAssetDepreciationSchedule` (fix push component-only path-guard `len(paths)==len(_EXPECTED)` + `test_mob_oas_05_operation_id_matches_convention`). Full test-run bắt sót (10 secondary guard KHÔNG dùng token `, 69,` — buộc chạy suite thật, KHÔNG grep-replace mù).

---

## Context

Màn **hồ-sơ-thiết-bị** mobile (flow-2) có nhiều sub-tab; **5 sub-tab phân-tích/truy-vết backend ĐÃ LIVE**: `kpi` (curated CR-11a/ADR-038), `downtime` (curated CR-11b/ADR-039), `verify_chain` (curated CR-11c/ADR-040), `commissioning` (curated CR-11d/ADR-041), **`depreciation`** (khấu hao — sub-tab THỨ NĂM & CUỐI được curate). Codegen client mobile KHÔNG có model typed cho tab "Khấu hao" ⇒ dead-end contract (client parse free-form `data` Map, mất type-safety cho `asset`/`asset_info`/`rows[]`/`summary`).

CR-11e = curate sub-tab CUỐI của CR-11, chọn `getAssetDepreciationSchedule` — **truy-vết tài-chính/kế-toán tài-sản**. Mỗi asset (nếu đã cấu-hình khấu hao) sinh 1 lịch `AC Asset Depreciation Schedule` (child-table): mỗi chu-kỳ ghi số tiền khấu hao, khấu hao luỹ-kế, giá-trị còn lại, trạng-thái (Pending/Executed/Cancelled), ngày thực-hiện, bút-toán. Kèm `asset_info` (nguyên-giá, giá-trị thu-hồi, khấu hao luỹ-kế, giá-trị sổ hiện-tại, phương-pháp, số tháng, tần-suất, ngày bắt-đầu, ngày sử-dụng) + `summary` (tổng chu-kỳ / đã-thực-hiện / chờ / tổng đã-khấu-hao). Đây là dữ-liệu quản-trị **giá-trị tài-sản** thiết-bị y-tế (kế-toán + WHO HTM lifecycle end-of-life planning).

Ràng buộc quyết định:
1. **CONTRACT-ONLY** — handler `get_depreciation_schedule` ĐÃ LIVE @`api/imm00.py:2962` (Phase 2). Thay đổi CHỈ ở OAS mirror + test + doc; **KHÔNG đụng `.py`, KHÔNG reload worker, KHÔNG migrate**.
2. **200 = oneOf `[AssetDepreciationScheduleEnvelope, Error]`** (Decision-B) — handler `return _err(_("Asset not found"), 404)` asset∄ @`:2964-2965` → Error envelope HTTP-200 `http_status ⊇ {404}`. **⚠️ KHÁC ADR-041** (`raise ServiceError → _handle`): CR-11e dùng `_err(...)` **in-handler trực-tiếp** (self-contained, KHÔNG service) — CÙNG kết-quả Error-envelope-HTTP-200, mirror `getAssetKpi`/`getAssetDowntimeMetrics` (`_err` in-handler ADR-038/039).
3. **`AssetDepreciationSchedule` = WRAPPER 4-key với 3 nested-schema** (ĐIỂM KHÁC CỐT-LÕI vs mọi sibling): `data = $ref AssetDepreciationSchedule` = `{asset:string, asset_info:object|null, rows:array<DepreciationScheduleRow>, summary:$ref DepreciationScheduleSummary}`. ⇒ **5 schema** (wrapper + Row + Summary + Info + envelope), NHIỀU-nhất bộ CR-11 (ADR-041 = 3 schema, ADR-038/039/040 = 2 schema).
4. **`asset_info` = nullable-ref idiom** — handler `asset = frappe.db.get_value(...) or {}` @`:2988`. Trong happy-path (asset tồn-tại, đã qua guard @`:2964`) get_value trả dict 9-key (value có-thể null); `or {}` là defensive-coalesce khi get_value falsy. ⇒ key `asset_info` **LUÔN present** (∈ `required`), value = object hoặc `{}`. Model = `{type:object, nullable:true, allOf:[$ref AssetDepreciationInfo]}` — **mirror `commissioning` ADR-041 / `current_open` ADR-039** (nullable-ref, `type:object` sibling BẮT BUỘC — redocly `nullable-type-sibling`). `{}` empty-object hợp-lệ với `AssetDepreciationInfo` (0-required).
5. **`DepreciationScheduleRow` = 9-prop VERBATIM get_all** — field-list literal `frappe.get_all("AC Asset Depreciation Schedule", fields=[...])` @`:2969-2971`. `name` = child docname PK always-non-null → `required[name]` (convention list-item `RepairWorkOrderListItem`/`CommissioningOriginRecord`); 8 field còn lại ∉ required. **3 FINANCIAL Currency** (`depreciation_amount`/`accumulated_amount`/`remaining_value`) → `number` nullable curate VERBATIM. **`status` = Select bounded no-blank `enum[Pending, Executed, Cancelled]`** (default `'Pending'`, **DB-verified 413 Pending / 79 Executed / 42 Cancelled, 0 blank / 534 rows** — `bench console`) — bám precedent **ADR-028** `listAssetCategories.depreciation_frequency` (Select bounded no-blank → enum). 2 Date (`scheduled_date`/`executed_on`) → `format:date`.
6. **`DepreciationScheduleSummary` = 4-prop compute** — `{total_periods, executed_periods, pending_periods, total_depreciated}` dict-literal @`:2975-2981`, compute vô-điều-kiện ⇒ CẢ 4 always-non-null → `required` đủ 4. 3 count `integer`; `total_depreciated` = **FINANCIAL** `number` (sum depreciation_amount cho Executed) curate VERBATIM.
7. **`AssetDepreciationInfo` = 9-prop VERBATIM get_value** — field-list literal `frappe.db.get_value("AC Asset", asset_name, [...])` @`:2984-2986`. **TOÀN-BỘ 9 value-nullable** (Currency/Select/Int/Date trống → get_value None; + `{}` coalesce) ⇒ **`required` KHÔNG khai** (0 anchor always-non-null — KHÁC `CommissioningOriginRecord` có `name`+`transferred_doc_count`). 4 FINANCIAL Currency → `number` nullable. **2 Select LEADING-BLANK** (`depreciation_method` `[/Straight Line/Double Declining/Units of Production/None]`, `depreciation_frequency` `[/Monthly/Quarterly/Yearly]`) → `string` nullable **NO-enum** (`''` hợp-lệ — bám **ADR-028** sub-case Select leading-blank → string nullable no-enum, KHÁC `DepreciationScheduleRow.status` no-blank → enum). 2 Date → `format:date`. 1 Int (`total_depreciation_months`) → integer nullable.
8. **`asset_name` REQUIRED** — chữ-ký LIVE `get_depreciation_schedule(asset_name: str)` @`:2962` positional no-default ⇒ `required:true`, `type:string`. **⚠️ Tên `asset_name` (KHÔNG `name`); REQUIRED** — mirror `getAssetCommissioningOrigin` (ADR-041), KHÁC `getAssetKpi(name)`/`getAssetDowntimeMetrics(asset_name, year='')` year OPTIONAL. Handler `_err(404)` khi asset∄ @`:2965` ⇒ required source-faithful.
9. **FINANCIAL curate VERBATIM (8 field)** — `gross_purchase_amount`, `depreciation_amount`, `accumulated_amount`, `remaining_value`, `current_book_value`, `accumulated_depreciation`, `residual_value`, `total_depreciated` = Currency/sum-Currency → `number` nullable; curate nguyên theo return-dict, **UI-render deferred** mobile client (persona-gate FE) per LL-BE-57 + precedent `total_repair_cost` ADR-038 / `purchase_price` ADR-041 (KHÔNG strip khỏi contract).
10. **KHÔNG discriminator, KHÔNG split** — read-path closed-schema oneOf route-by-VALUE `body.success` (Decision-B). Nullable `asset_info` mã-hoá bằng `nullable:true` (né discriminator — object-ref, discriminator OAS 3.x chỉ string).
11. **Read-only — KHÔNG audit** — endpoint ĐỌC (get_all + get_value + compute), KHÔNG mutate → KHÔNG sinh Lifecycle Event / IMM Audit Trail record mới. (Sinh-lịch `regenerate_depreciation_schedule` @`:2992` là POST RIÊNG, KHÔNG thuộc CR-11e.)

## Decision

Bồi ĐÚNG 1 GET-read path + 5 schema vào OAS mirror:

### Path `/api/method/assetcore.api.imm00.get_depreciation_schedule`
- `get:` (GET-only, bare `@whitelist`), `operationId: getAssetDepreciationSchedule`, `tags: [asset]`.
- **1 query param:** `asset_name` (`in:query`, **`required:true`**, `type:string`) — grounded chữ-ký `get_depreciation_schedule(asset_name)` positional no-default @`imm00.py:2962`. **⚠️ Tên `asset_name` (KHÔNG `name`); REQUIRED (KHÁC `getAssetKpi`/`getAssetDowntimeMetrics` year OPTIONAL).**
- **200 = oneOf `[AssetDepreciationScheduleEnvelope, Error]`** closed-schema, KHÔNG discriminator (route-by-VALUE `body.success`); `Error.http_status ⊇ {404}` (asset∄ `_err` @`:2965`).
- **Response slot** `{200, 401, 403}` — 401 `Unauthorized401` SINGLE-SHAPE (bearer hết hạn), **403 `Forbidden` SINGLE-SHAPE** (bare `@whitelist` no-`allow_guest` → guest dispatcher-403; KHÔNG in-handler cap-403 — handler KHÔNG `rbac.require`).

### Schema `AssetDepreciationSchedule` (WRAPPER 4-key) — closed
| Property | Type | required / nullable | Grounding @source |
|---|---|---|---|
| `asset` | string | **required** | echo `asset_name` @`:2989` — LUÔN present |
| `asset_info` | object (nullable-ref) | **required** · **nullable** | `{type:object, nullable:true, allOf:[$ref AssetDepreciationInfo]}` — `get_value(...) or {}` @`:2988`; key LUÔN emit |
| `rows` | array `<DepreciationScheduleRow>` | **required** | `get_all` @`:2966-2974`; `[]` khi chưa sinh lịch |
| `summary` | `$ref DepreciationScheduleSummary` | **required** | compute @`:2975-2981` |

- `properties[]` = EXACT 4; `required[]` = EXACT 4 (MỌI key LUÔN emit `_ok` dict-literal @`:2989`); `additionalProperties:false`.

### Schema `DepreciationScheduleRow` (9-prop VERBATIM) — closed
| Property | Type | required / nullable | Grounding @source |
|---|---|---|---|
| `name` | string | **required** | child docname PK (get_all đầu field-list @`:2969`) |
| `period_number` | integer | nullable | Int @`:2969` |
| `scheduled_date` | string (format:date) | nullable | Date @`:2969` |
| `depreciation_amount` | number | nullable · **FINANCIAL** | Currency VND @`:2969` — curate VERBATIM |
| `accumulated_amount` | number | nullable · **FINANCIAL** | Currency VND @`:2970` — curate VERBATIM |
| `remaining_value` | number | nullable · **FINANCIAL** | Currency VND @`:2970` — curate VERBATIM |
| `status` | string · **enum** `[Pending, Executed, Cancelled]` | (∉ required, non-nullable) | Select bounded no-blank default `'Pending'` @`:2970` (DB 413/79/42, 0-blank) |
| `executed_on` | string (format:date) | nullable | Date @`:2971` |
| `journal_entry` | string | nullable | Data @`:2971` |

- `properties[]` = EXACT 9 (VERBATIM get_all list @`:2969-2971`); `required[]` = EXACT 1 `[name]`; 7 field value-nullable ∈ nullable-set ∉ required; `status` enum non-nullable ∉ required (minimal-commitment); 2 Date `format:date`; `additionalProperties:false`.

### Schema `DepreciationScheduleSummary` (4-prop compute) — closed
| Property | Type | required | Grounding @source |
|---|---|---|---|
| `total_periods` | integer | **required** | `len(rows)` @`:2976` |
| `executed_periods` | integer | **required** | `sum(status==Executed)` @`:2977` |
| `pending_periods` | integer | **required** | `sum(status==Pending)` @`:2978` |
| `total_depreciated` | number · **FINANCIAL** | **required** | `sum(depreciation_amount cho Executed)` @`:2979-2980` — curate VERBATIM |

- `properties[]` = EXACT 4; `required[]` = EXACT 4 (compute vô-điều-kiện always-non-null); `additionalProperties:false`.

### Schema `AssetDepreciationInfo` (9-prop VERBATIM get_value) — closed
| Property | Type | nullable | Grounding @source |
|---|---|---|---|
| `gross_purchase_amount` | number | nullable · **FINANCIAL** | Currency @`:2984` — curate VERBATIM |
| `residual_value` | number | nullable · **FINANCIAL** | Currency @`:2984` — curate VERBATIM |
| `accumulated_depreciation` | number | nullable · **FINANCIAL** | Currency @`:2984` — curate VERBATIM |
| `current_book_value` | number | nullable · **FINANCIAL** | Currency @`:2985` — curate VERBATIM |
| `depreciation_method` | string | nullable · **NO-enum** | Select LEADING-BLANK @`:2985` (`''` hợp-lệ — ADR-028 sub-case) |
| `total_depreciation_months` | integer | nullable | Int @`:2985` |
| `depreciation_frequency` | string | nullable · **NO-enum** | Select LEADING-BLANK @`:2986` (`''` hợp-lệ) |
| `depreciation_start_date` | string (format:date) | nullable | Date @`:2986` |
| `in_service_date` | string (format:date) | nullable | Date @`:2986` |

- `properties[]` = EXACT 9 (VERBATIM get_value list @`:2984-2986`); **`required[]` = ∅** (TOÀN-BỘ value-nullable — 0 anchor); 2 Select LEADING-BLANK → string nullable NO-enum; 2 Date `format:date`; `additionalProperties:false`.

### Schema `AssetDepreciationScheduleEnvelope` — closed
- `additionalProperties:false`, `required:[success, data]`, `success` `type:boolean` `enum:[true]`, `data = $ref AssetDepreciationSchedule`.

### Invariant contract (guard `TestMobileAssetDepreciationScheduleCurate` a..h, `test_mobile_oas`)
- **a** yaml load; path-count **69→70**; opId-count 70 unique camelCase; path GET-ONLY opId `getAssetDepreciationSchedule` tag `asset`.
- **b** ĐÚNG 1 query param `asset_name` (`required:true`, string); KHÔNG requestBody; **LIVE introspect-parity** `set(inspect.signature(imm00.get_depreciation_schedule).parameters) == {"asset_name"}` (`asset_name` no-default → required). **⚠️ khoá tên `asset_name` (KHÔNG `name`); REQUIRED KHÁC sibling year OPTIONAL.**
- **c** 200 = oneOf `[AssetDepreciationScheduleEnvelope, Error]` route-by-VALUE, 0 discriminator; 2 branch closed; `success.enum` disjoint `[true]`/`[false]`; `Error.http_status ⊇ {404}` (asset∄ `_err` @`:2965`); slot `{200,401,403}`.
- **d** `AssetDepreciationSchedule` WRAPPER closed; props EXACT `{asset, asset_info, rows, summary}`; required EXACT 4; `asset`=string; `asset_info` = nullable-ref idiom `{type:object, nullable:true, allOf:[$ref AssetDepreciationInfo]}`; `rows`=array items `$ref DepreciationScheduleRow`; `summary`=`$ref DepreciationScheduleSummary`.
- **e** `DepreciationScheduleRow` closed; props EXACT 9; required EXACT `[name]`; 7 value-nullable ∈ nullable ∉ required; 3 FINANCIAL number; 2 Date `format:date`; `status` enum `[Pending,Executed,Cancelled]` non-nullable + **GROUNDING** đọc TRỰC-TIẾP `ac_asset_depreciation_schedule.json` Select options (chống-bịa enum); types VERBATIM; **GROUNDING per-doctype** — AST/parse `get_depreciation_schedule` → `get_all` field-list `AC Asset Depreciation Schedule` @`:2969-2971` == 9 prop Row.
- **f** `DepreciationScheduleSummary` closed 4-prop required-4 (3 integer + `total_depreciated` number FINANCIAL); `AssetDepreciationInfo` closed 9-prop **0-required** TOÀN value-nullable (4 FINANCIAL + 2 Select-leading-blank string NO-enum + 2 Date + 1 Int); types VERBATIM; **GROUNDING per-doctype** — `get_value` field-list `AC Asset` @`:2984-2986` == 9 prop Info + `summary`/`wrapper` key-set khớp dict-literal @`:2975-2989` (chống-bịa).
- **g** `AssetDepreciationScheduleEnvelope` closed `required[success,data]`; `data = $ref AssetDepreciationSchedule`; ∈ `_MVP_BUSINESS_PATHS`/`_PATHS_REQUIRE_401`/`_PATHS_REQUIRE_403`/`_MVP_READ_ENVELOPE`; 403 SINGLE `$ref` Forbidden (dispatcher-only, bare `@whitelist`).
- **h** **zero-footprint** — 5 schema mới ∩ existing == chỉ 5 tên mới (naming-guard prefix `AssetDepreciation*` == 3 `{Schedule, Envelope, Info}`, `DepreciationSchedule*` == 2 `{Row, Summary}`); `getAssetKpi`/`getAssetDowntimeMetrics`/`getAssetVerifyChain`/`getAssetCommissioningOrigin` BẤT BIẾN; 0 dangling `$ref`; **SCOPED-HANDLER invariant** — source AST `get_depreciation_schedule` @`api/imm00.py:2962` BẤT BIẾN HEAD↔working (CONTRACT-ONLY pure-yaml).
- **RED-before/GREEN-after**: strip path block → path-count 69≠70 + `Thiếu path` ⇒ FAIL `depsched_a/b/c/g` (+cascade 93 suite path-count guard); khôi phục → GREEN. (Đã demo @2026-07-13: strip → 93 FAIL → restore → **Ran 664 OK**.)

## Alternatives

| Phương án | Vì sao LOẠI |
|---|---|
| **A. Giữ dead-end (không curate)** | Tab "Khấu hao" mất model typed — codegen parse free-form `data` Map; sub-tab backend LIVE mãi không dùng; mất kênh phơi giá-trị tài-sản (khấu hao/giá-trị sổ) lên mobile; CR-11 KHÔNG hoàn-tất bộ-năm. |
| **B. Flatten (bỏ 3 nested-schema, gộp mọi field vào 1 object)** | Sai @source — handler trả `{asset, asset_info, rows, summary}` 4 tầng khác nhau (scalar / nullable-object / array / object). Flat → mất cấu-trúc `rows[]` (array chu-kỳ) + `asset_info` nullable + `summary`. Wrapper 3-nested trung-thực. |
| **C. `asset_info` scalar-nullable `{type:object, nullable:true}` KHÔNG allOf** | KHÔNG type-safe — codegen sinh `Map` thay model `AssetDepreciationInfo`. Nullable-ref idiom `allOf:[$ref]` giữ typed model + nullable (mirror `commissioning` ADR-041 / `current_open` ADR-039). |
| **D. `asset_info` ∉ required (optional)** | Sai @source — key `asset_info` LUÔN emit (`_ok` dict-literal @`:2989`, value = dict hoặc `{}`). Optional → codegen coi absent hợp-lệ, sai contract. ∈ required + nullable = present-as-null/`{}` đúng. |
| **E. `DepreciationScheduleRow.status` = string plain (KHÔNG enum)** | Mất type-safety badge trạng-thái + KHÔNG bám precedent. Select **bounded no-blank** `[Pending,Executed,Cancelled]` default `'Pending'`, **DB-verified 0-blank/534** → enum (ADR-028 `depreciation_frequency` DB-verified). Codegen sinh `DepreciationStatusEnum` typed. |
| **F. `AssetDepreciationInfo.depreciation_method`/`depreciation_frequency` = enum** | Sai — 2 Select có **LEADING-BLANK** (`''` = option đầu, hợp-lệ khi asset chưa cấu-hình). Enum → strict codegen reject `''`. String nullable no-enum đúng (ADR-028 `default_depreciation_method` leading-blank sub-case — KHÁC `status` no-blank). |
| **G. `AssetDepreciationInfo` required = 9 (all)** | Sai — 9 field từ `get_value` value-nullable (Currency/Select/Int/Date trống → None) + `{}` coalesce. Ép required → strict codegen deser CRASH khi field trống / `asset_info={}`. 0-required đúng (convention `getAssetKpi` nullable-value ∉ required). |
| **H. Strip 8 FINANCIAL khỏi contract** | Sai — return-dict trả VERBATIM (Currency + sum-Currency). Curate nguyên (LL-BE-57 + `total_repair_cost` ADR-038 / `purchase_price` ADR-041). Persona-gate/UI-render là việc FE client, KHÔNG cắt khỏi contract. |
| **I. param `asset_name` OPTIONAL (như `year` CR-11b)** | Sai @source — chữ-ký positional no-default @`:2962` + `_err(404)` khi asset∄ @`:2965`. REQUIRED source-faithful (mirror ADR-041). |
| **J. 200 single-shape (KHÔNG oneOf Error)** | Sai @source — `_err(_("Asset not found"), 404)` asset∄ @`:2965` → Error envelope HTTP-200. Single-shape → codegen không phân-biệt success/error → crash khi 404. Decision-B oneOf đúng. |
| **K. Grounding chỉ đọc get_all list (bỏ get_value + dict-literal)** | Sai — 3 nested-schema có 3 nguồn khác: `rows` = get_all list @`:2969-2971`, `asset_info` = get_value list @`:2984-2986`, `summary`+`wrapper` = dict-literal @`:2975-2989`. TC-e/f GROUNDING per-doctype + per-dict-literal PHẢI đọc CẢ 3 (chống bịa field từng schema). |

## Consequences

- **(+)** Curate sub-tab THỨ NĂM & CUỐI của CR-11 — **HOÀN TẤT bộ-năm asset-detail** (kpi/downtime/verify_chain/commissioning + depreciation). Codegen client phơi model `AssetDepreciationSchedule` + `DepreciationScheduleRow` + `DepreciationScheduleSummary` + `AssetDepreciationInfo` typed ⇒ tab "Khấu hao" màn hồ-sơ render: bảng chu-kỳ (số tiền / luỹ-kế / còn-lại / trạng-thái badge / ngày thực-hiện) + card tổng-hợp (tổng chu-kỳ / đã / chờ / tổng đã-khấu-hao) + thông-tin khấu hao (nguyên-giá / giá-trị sổ / phương-pháp / tần-suất); khi `rows=[]`: empty-state "Chưa sinh lịch khấu hao".
- **(+)** Contract trung-thực @source: 9+4+9 prop = get_all + dict + get_value (TC-e/f grounding per-doctype + dict-literal đọc TRỰC-TIẾP handler AST — chống bịa từng nested-schema + chống ép all-required), wrapper nullable-ref khớp `or {}` (TC-d), oneOf Error khớp `_err(404)` (TC-c), LIVE introspect-parity chữ-ký `{asset_name}` required (TC-b — chống drift + chống bịa param `name`), status enum DB-verified (TC-e grounding doctype Select — chống bịa enum).
- **(+)** **LẦN ĐẦU success-data = WRAPPER 4-key với 3 nested-schema** (scalar + nullable-object + array-of-object + object) — payload phức-nhất bộ CR-11; đặt precedent cho "container multi-shape" (mix nullable-ref idiom ADR-041 + list-item Row + computed Summary). FINANCIAL-family 8 field.
- **(0)** PATH ADD: path/opId **69→70**, c5 **58→59** (∈ `_MVP_BUSINESS_PATHS` + `_MVP_READ_ENVELOPE` inline oneOf, mirror sibling); 5 schema mới (naming guard `AssetDepreciation*` ∩ 3 + `DepreciationSchedule*` ∩ 2, ∩ schema hiện có == ∅); opId convention-map (`_EXPECTED`) += `get_depreciation_schedule → getAssetDepreciationSchedule`.
- **(0)** CONTRACT-ONLY: 0 đụng `.py`, 0 reload worker, 0 migrate (TC-h SCOPED-HANDLER invariant chứng minh `get_depreciation_schedule` @`api/imm00.py:2962` AST bất-biến HEAD↔working). Test: `test_mobile_oas` 656→**664** (+8 TC `TestMobileAssetDepreciationScheduleCurate` a..h) · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 656→664 / `_GUARD_SUITE_SUM` 799→**807** / `_MOBILE_OAS_TOTAL` 825→**833** + delta var `asset_depreciation_schedule_curate_delta=8` (transition-baseline doc_09 giữ `pre_fc3_six==191`).
- **(0)** README ADR balance **41==41 → 42==42** (ADR-042.md đĩa + 1 README index row).
- **(⚠️)** **10 secondary count-guard** (3 c5 `58→59` + 1 parity `58→59` + 3 backward-compat opId-set-minus `68→69` + 1 `{listTransfers,getTransfer}` `67→68` + push `len(paths)==len(_EXPECTED)` + `test_05_operation_id_matches_convention`) KHÔNG dùng token `, 69,` ⇒ grep-replace mù KHÔNG bắt được — **BUỘC chạy full-suite THẬT** (RED-before demo bắt 93 FAIL, KHÔNG false-green). Fix push/convention = THÊM entry `_EXPECTED` (KHÔNG bump literal).

### Naming guard (∅)
5 schema mới `AssetDepreciationSchedule` + `AssetDepreciationScheduleEnvelope` + `AssetDepreciationInfo` + `DepreciationScheduleRow` + `DepreciationScheduleSummary` — prefix `AssetDepreciation*` == 3 tên mới, `DepreciationSchedule*` == 2 tên mới, ∩ mọi schema/parameter hiện có `== ∅` (grep 0). Path `getAssetDepreciationSchedule` opId unique camelCase.

## Handoff CORE-DEV (native repo — ngoài `assetcore`)

Sau regenerate client từ OAS mirror: model `AssetDepreciationSchedule` (`asset:string, assetInfo:AssetDepreciationInfo | null, rows:DepreciationScheduleRow[], summary:DepreciationScheduleSummary`) + `DepreciationScheduleRow` (9 field, `status:DepreciationStatusEnum` typed) + `DepreciationScheduleSummary` (4 field) + `AssetDepreciationInfo` (9 field nullable) + service-method `getAssetDepreciationSchedule(assetName)`. Tab "Khấu hao" màn hồ-sơ-thiết-bị render: bảng `rows[]` (chu-kỳ · số tiền khấu hao · luỹ-kế · giá-trị còn-lại · badge `status` · ngày thực-hiện) + card `summary` (tổng / đã / chờ / tổng đã-khấu-hao) + panel `asset_info` (nguyên-giá · giá-trị sổ hiện-tại · phương-pháp · tần-suất · ngày bắt-đầu); khi `rows == []` → empty-state "Chưa sinh lịch khấu hao"; khi `assetInfo == null`/`{}` → ẩn panel thông-tin. ⚠️ **8 FINANCIAL field** = render theo persona (gate quyền xem giá-trị tài-sản). CR-11e → RESOLVED (contract curated, backend đã ship LIVE). **CR-11 HOÀN TẤT** (bộ-năm asset-detail sub-tab: kpi/downtime/verify_chain/commissioning/depreciation).
