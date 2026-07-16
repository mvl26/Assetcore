# ADR-MOBILE-039 — `getAssetDowntimeMetrics` curate vào OAS mirror (**CR-11b · asset-detail sub-tab #2 "Dừng máy"** — bồi ĐÚNG 1 GET-read path `getAssetDowntimeMetrics` (thống-kê dừng máy của 1 asset) vào OAS mirror; sub-tab THỨ HAI của CR-11 sau `getAssetKpi` (ADR-038); **LẦN ĐẦU open-map `by_reason` trong success-data schema** — documented exception)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-039 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-13 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến trên HTTP-200 body `Error`, route theo `body.success`/`body.http_status`; KHÔNG discriminator, closed-schema oneOf) · **sibling trực-tiếp**: **ADR-MOBILE-038** (`getAssetKpi` — CÙNG asset-detail sub-tab flow-2, GET bare `@whitelist`, `_err(404)` asset∄ → HTTP-200 nhánh Error, 200 = oneOf `[Envelope, Error]`, `data=$ref` OBJECT PHẲNG) · **precedent typed-query-param**: **ADR-MOBILE-034** (CR-05 — `?token=/?name=` khai `parameters:` TYPED thay prose-only) · Core Doc IMM-00 [`04-api-contract.md`](./04-api-contract.md) §8.41 (getAssetDowntimeMetrics) + [`docs/imm-00/05_API_Specification.md`](../imm-00/05_API_Specification.md) §III.19 |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (@2026-07-13): handler `get_asset_downtime_metrics(asset_name, year="")` def@`assetcore/api/imm00.py:2892-2893` (bare `@frappe.whitelist()` — GET-ok, no `allow_guest` → guest dispatcher-403). `_err(_("Không tìm thấy thiết bị"), 404)` khi asset∄ @`imm00.py:2901-2902` → HTTP-200 nhánh Error (Decision-B). `_ok({8-key})` @`imm00.py:2936-2944` (compute on-the-fly cửa-sổ năm `year`: đọc `AC Asset Downtime Log` filter `asset` + `start_time between [year-01-01, year-12-31]` @`:2909-2919`; tổng giờ + phân-loại theo reason + log đang-mở). `git diff` `api/imm00.py` vùng `get_asset_downtime_metrics` = TRỐNG round NÀY ⇒ backend ĐÃ LIVE @whitelist, thay đổi CHỈ ở OAS mirror + test + doc. Doctype `AC Asset Downtime Log` field-type @`assetcore/assetcore/doctype/ac_asset_downtime_log/ac_asset_downtime_log.json`. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Nguồn yêu cầu: `assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` CR-11b.

---

## ⚠️ Reconciliation đánh-số (đa-phiên) — BE Bước-4 ĐỌC TRƯỚC

Đề mục Bước-2 (vòng 25) ghi baseline STALE: `path/opId 65→66`, `ADR-MOBILE-038 (NEW)`, `balance 38==38`. **SAI** — sibling `getAssetKpi` (CR-11a) ĐÃ LAND trong working tree TRƯỚC round NÀY và đã tiêu:

| Hạng mục | Đề mục (STALE) | LIVE baseline @source | CR-11b target (ĐÚNG) |
|---|---|---|---|
| ADR số | 038 (NEW) | **038 = getAssetKpi** (đã tồn tại đĩa + README) | **039** (NEW) |
| path/opId | 65→66 | **66** (getAssetKpi đã 65→66) | **66→67** |
| c5 | (đồng bộ) | **55** (getAssetKpi đã 54→55) | **55→56** |
| `_EXPECTED_TEST_COUNT` | 632→640 | **632** | **632→640** ✅ đề mục ĐÚNG (base 632 = post-getAssetKpi) |
| `_GUARD_SUITE_SUM` | — | **775** | **775→783** |
| `_MOBILE_OAS_TOTAL` | — | **801** | **801→809** |
| README ADR balance | 38==38 | **38 file / 38 row** | **39==39** |

> Grounded: `ADR-MOBILE-038.md` header = "`getAssetKpi` curate" (verify @2026-07-13); `grep -c '^  /api/method' yaml` = 66; `_EXPECTED_TEST_COUNT = 632` @`test_mobile_oas.py:212`; `_MOBILE_OAS_TOTAL = 801` @`test_mobile_docset.py:1116`; `ls docs/mobile/ADR-MOBILE-*.md | wc -l` = 38. Đề mục CHỈ lệch path/ADR/c5 base (vì viết trước khi getAssetKpi land); test-count base 632 ĐÚNG.

---

## Context

Màn **hồ-sơ-thiết-bị** mobile (flow-2) có nhiều sub-tab; **5 sub-tab phân-tích backend ĐÃ LIVE**: `kpi` (curated CR-11a/ADR-038), `verify_chain`, `depreciation`, `commissioning`, **`downtime`** (nhật-ký + thống-kê ngừng máy — sub-tab THỨ HAI được curate). Codegen client mobile KHÔNG có model typed cho tab "Dừng máy" ⇒ dead-end contract (client parse free-form `data` Map, mất type-safety cho các số-liệu MTTR/tổng-giờ/phân-loại-lý-do).

CR-11b = curate sub-tab THỨ HAI của CR-11, chọn `getAssetDowntimeMetrics` — thống-kê dừng máy quan-trọng cho KTV/quản-lý (tổng giờ dừng, số lần dừng, MTTR = giờ/lần, phân-loại giờ theo lý-do, log đang-mở tính đến hiện-tại, 10 log gần nhất).

Ràng buộc quyết định:
1. **CONTRACT-ONLY** — handler `get_asset_downtime_metrics` ĐÃ LIVE @`imm00.py:2892`, trả 8-key VERBATIM @`:2936-2944`. Thay đổi CHỈ ở OAS mirror + test + doc; **KHÔNG đụng `.py`, KHÔNG reload worker, KHÔNG migrate**.
2. **200 = oneOf `[AssetDowntimeMetricsEnvelope, Error]`** (Decision-B) — handler có `_err(404)` asset∄ @`:2901-2902` đến trên HTTP-200 body Error; mirror `getAssetKpi` (ADR-038).
3. **`AssetDowntimeMetrics` = OBJECT PHẲNG single** (`data = $ref` trực-tiếp) — KHÁC list-read (`{items, pagination}`). Handler trả flat dict 8-key, KHÔNG paginate (`logs` là mảng CON bị cap `rows[:10]`, KHÔNG phải list-envelope top-level).
4. **8 key VERBATIM return-dict** — closed `additionalProperties:false`; **cả 8 always-present ∈ `required`** (return-dict cố-định @`:2936-2944` — mọi key LUÔN emit). `current_open` LUÔN present nhưng VALUE nullable (`None` khi 0 log đang-mở @`:2923`).
5. **`by_reason` = open-map** (`additionalProperties:{type:number}`) — dict động `reason → giờ` @`:2922/2931`. KEY = giá-trị Select `reason` (6 option @doctype:52) nhưng OpenAPI 3.0 KHÔNG enumerate KEY của map ⇒ mô-hình open-map. **Đây là ADR EXCEPTION** — schema DUY-NHẤT không-đóng của curate NÀY (mọi schema khác `additionalProperties:false`). ⚠️ **Precision:** KHÔNG phải open-map ĐẦU-TIÊN toàn yaml (`Error.fields` @`yaml:730-734` đã có `additionalProperties:{type:string}` — error-extension optional); `by_reason` là open-map **`{type:number}` ĐẦU-TIÊN** VÀ **open-map ĐẦU-TIÊN trong schema success-data payload**.
6. **`reason` = plain `string` (KHÔNG enum)** — đối-xứng open-map `by_reason` (cùng domain reason). Dù `reason` là Select bounded no-blank 6-option (đủ điều-kiện enum theo precedent ADR-023/028), giữ plain string để (a) đối-xứng by_reason KHÔNG-enumerate reason-domain trong contract NÀY, (b) tránh over-constrain deser nếu log legacy có reason ngoài 6 option. Xem Alternatives-F.
7. **`asset_name` KHÔNG `name`** — chữ-ký LIVE `get_asset_downtime_metrics(asset_name, year="")` @`:2893` dùng `asset_name` (KHÁC `getAssetKpi(name)`). Param `asset_name` PHẢI đúng tên (chống drift codegen sai param).
8. **`year` = typed query param optional** — `year:str=""` @`:2893` (default "" → optional; handler `int(year) if year else <năm hiện-tại>` @`:2905`). Khai `parameters:` TYPED (mirror CR-05/ADR-034), KHÔNG prose-only.

## Decision

Bồi ĐÚNG 1 GET-read path + 4 schema vào OAS mirror:

### Path `/api/method/assetcore.api.imm00.get_asset_downtime_metrics`
- `get:` (GET-only, bare `@whitelist`), `operationId: getAssetDowntimeMetrics`, `tags: [asset]`.
- **2 query param:**
  - `asset_name` (`in:query`, **`required:true`**, `type:string`) — grounded chữ-ký `get_asset_downtime_metrics(asset_name, …)` positional no-default @`imm00.py:2893`. **⚠️ Tên `asset_name` KHÔNG `name`.**
  - `year` (`in:query`, **`required:false`**, `type:string`) — `year:str=""` default @`:2893` (rỗng → năm hiện-tại @`:2905`). Typed-query parity CR-05.
- **200 = oneOf `[AssetDowntimeMetricsEnvelope, Error]`** closed-schema, KHÔNG discriminator (route-by-VALUE `body.success`); `Error.http_status ⊇ {404}` (asset∄ in-handler @`:2901-2902`).
- **Response slot** `{200, 401, 403}` — 401 `Unauthorized401` SINGLE-SHAPE (bearer hết hạn), 403 `Forbidden` SINGLE-SHAPE (bare `@whitelist` no-allow_guest → guest dispatcher-403; KHÔNG in-handler cap-403).

### Schema `AssetDowntimeMetrics` (8 key VERBATIM @`imm00.py:2936-2944`) — closed
| Property | Type | required / nullable | Grounding @source |
|---|---|---|---|
| `asset` | string | **required** | echo `asset_name` @`:2937` |
| `year` | integer | **required** | `int(y)` @`:2905/2938` |
| `total_hours` | number | **required** | `round(total_hours, 2)` @`:2939` |
| `breakdown_count` | integer | **required** | `count = len(rows)` @`:2933/2940` |
| `mttr_hours` | number | **required** | `round(total_hours/count, 2)` else `0.0` @`:2934/2941` |
| `by_reason` | object (**open-map** `additionalProperties:{type:number}`) | **required** | `dict[str,float]` reason→giờ @`:2922/2931/2942` — **ADR EXCEPTION** |
| `current_open` | **nullable** `$ref AssetDowntimeLogOpen` (oneOf `[AssetDowntimeLogOpen]` + `nullable:true`) | **required** (key LUÔN present; value `null` khi 0 log-mở) | `None` else `{**r, downtime_hours_so_far}` @`:2923/2927/2943` |
| `logs` | array `items: $ref AssetDowntimeLog` | **required** | `rows[:10]` (≤10 log gần nhất, `order_by start_time desc`) @`:2917/2944` |

- `required[]` = **EXACT 8** (mọi key LUÔN emit @return-dict cố-định). `additionalProperties:false`.
- **⚠️ OpenAPI 3.0.3** (`yaml:1`): `current_open` nullable-ref = `{nullable: true, allOf: [{$ref: '#/components/schemas/AssetDowntimeLogOpen'}]}` (KHÔNG `type: null` — chỉ hợp-lệ 3.1). Acceptance ghi "oneOf[Log-Open|null]" = intent; BE encode bằng `nullable+allOf` (3.0.3-legal).

### Sub-schema `AssetDowntimeLog` (8 field @`imm00.py:2915-2916`, grounded doctype) — closed
| Property | Type | required / nullable | Grounding |
|---|---|---|---|
| `name` | string | **required** | naming series `DTL-.YYYY.-.######` @doctype:36 |
| `reason` | string | **required** | Select `reqd:1` 6-option @doctype:49-53 (plain string — xem Decision-6) |
| `start_time` | string | **required** | Datetime `reqd:1` @doctype:62 (plain string, **NOT** `format:date-time` — Frappe `'YYYY-MM-DD HH:MM:SS'` space-sep ≠ RFC3339) |
| `end_time` | string | **required** · **nullable** | Datetime @doctype:69 (`null` khi log đang-mở/chưa đóng) |
| `downtime_hours` | number | **required** · **nullable** | Float `read_only` @doctype:75 (`null`/0 khi open — handler `float(r["downtime_hours"] or 0)` @`:2929`) |
| `is_open` | integer **enum `[0,1]`** | **required** | Check @doctype:83 — **int-vs-bool trap** (`get_all` trả int 0/1, KHÔNG boolean) |
| `reference_doctype` | string | **required** · **nullable** | Link `DocType` @doctype:95 |
| `reference_name` | string | **required** · **nullable** | Dynamic Link @doctype:101 |

- `required[]` = **EXACT 8** (`get_all(fields=[8])` @`:2915-2916` LUÔN trả đủ 8 key/row, value `None` nếu trống). `nullable` = **EXACT 4** `{end_time, downtime_hours, reference_doctype, reference_name}`. `additionalProperties:false`.

### Sub-schema `AssetDowntimeLogOpen` = `AssetDowntimeLog` + `downtime_hours_so_far` (9 field @`imm00.py:2927`) — closed
- 8 field như `AssetDowntimeLog` (cùng type/nullable) **+** `downtime_hours_so_far` (number, **required**, non-null — `round(hrs,2)` giờ dừng tính đến `now` @`:2926-2927`).
- `required[]` = **EXACT 9**; `nullable` = same 4. `additionalProperties:false`. (Standalone closed schema — KHÔNG `allOf`-compose để codegen sinh model 9-field sạch.)

### Schema `AssetDowntimeMetricsEnvelope` — closed
- `additionalProperties:false`, `required:[success, data]`, `success.enum:[true]`, `data = $ref AssetDowntimeMetrics`.

### Invariant contract (guard `TestMobileAssetDowntimeMetricsCurate` a..h, `test_mobile_oas`)
- **a** yaml load; path-count **66→67**; opId-count 67 unique camelCase.
- **b** path TỒN TẠI, GET-ONLY (chỉ key `get`), opId `getAssetDowntimeMetrics`, tag `asset`.
- **c** 2 query param `{asset_name required string, year optional string}`; KHÔNG requestBody; **LIVE introspect-parity** `inspect.signature(imm00.get_asset_downtime_metrics) == {asset_name, year}` (`asset_name` no-default → required; `year` default `""` → optional). **⚠️ khoá param tên `asset_name` (KHÔNG `name`).**
- **d** 200 = oneOf `[AssetDowntimeMetricsEnvelope, Error]` route-by-VALUE, 0 discriminator; 2 branch closed; `success.enum` disjoint `[true]`/`[false]`.
- **e** Envelope closed `required[success,data]`; `data = $ref AssetDowntimeMetrics` (OBJECT PHẲNG — KHÔNG `items`/`pagination` top-level).
- **f** `AssetDowntimeMetrics` closed; props **EXACT 8** VERBATIM return-dict; required **EXACT 8**; `by_reason` = open-map `additionalProperties:{type:number}` (KHÔNG properties fixed); `current_open` = nullable ref `AssetDowntimeLogOpen`; `logs` = array items `AssetDowntimeLog`.
- **g** sub-schema typed grounded: `AssetDowntimeLog` closed EXACT 8 (nullable EXACT 4; `is_open` integer enum`[0,1]` NOT boolean; `start_time/end_time` string no-`format:date-time`); `AssetDowntimeLogOpen` = Log 8 + `downtime_hours_so_far` number non-null (9 prop, nullable 4); top-level `year/breakdown_count`=integer, `total_hours/mttr_hours`=number.
- **h** **open-map exception** — `by_reason` là schema DUY-NHẤT của curate NÀY có `additionalProperties ≠ false` (mọi schema/sub-schema khác closed); disjointness props `AssetDowntimeMetrics`/`AssetDowntimeLog`/`AssetDowntimeLogOpen` ≠ `AssetKpi` ∧ ≠ `AssetScanInfo`; 0 dangling `$ref` toàn yaml; **SCOPED-HANDLER invariant** — source AST `get_asset_downtime_metrics` (gồm `@frappe.whitelist`) BẤT BIẾN HEAD↔working `imm00.py` (CONTRACT-ONLY pure-yaml).
- **RED-before/GREEN-after**: strip path `get_asset_downtime_metrics` → RED (TC-a path-count 66≠67 + TC-b `Thiếu path`) ⇒ bồi lại → GREEN.

## Alternatives

| Phương án | Vì sao LOẠI |
|---|---|
| **A. Giữ dead-end (không curate)** | Tab "Dừng máy" mất model typed — codegen client parse free-form `data` Map, mất type-safety cho `total_hours/mttr_hours/by_reason/current_open/logs`; sub-tab backend LIVE mãi không dùng được. |
| **B. 200 single-shape (KHÔNG oneOf Error)** | Sai @source — handler CÓ `_err(404)` asset∄ @`:2901-2902` đến trên HTTP-200 body Error. Single-shape → codegen không phân-biệt success/error → parse crash khi 404. Decision-B oneOf đúng (mirror getAssetKpi). |
| **C. Đóng `by_reason` (fixed 6 property theo reason Select)** | Fragile — nếu doctype thêm/đổi option `reason` (Select 6→7), contract vỡ + phải sửa. Handler build map ĐỘNG `by_reason[r["reason"]]` @`:2931` (key = giá-trị runtime). Open-map `additionalProperties:{type:number}` là đúng shape (documented ADR exception). |
| **D. `by_reason` `additionalProperties:{type:string}` (reuse Error.fields shape)** | Sai type — value là **giờ** (Float round `by_reason.get(...)+hrs` @`:2931`), KHÔNG string. Phải `{type:number}` (open-map number ĐẦU-TIÊN trong mirror). |
| **E. `current_open` = required non-null / bỏ khỏi required** | Sai @source — key LUÔN present (return-dict cố-định @`:2943`) NHƯNG value `None` hợp-lệ khi 0 log-mở @`:2923`. ⇒ ∈ required + `nullable:true`. Ép non-null → deser crash khi null; bỏ required → codegen optional sai (key luôn có). |
| **F. `reason` = enum 6-option** | Đủ điều-kiện (Select bounded no-blank) NHƯNG loại: (a) bất-đối-xứng với `by_reason` open-map (cùng domain reason KHÔNG enumerate trong contract NÀY); (b) over-constrain — log legacy/drift có reason ngoài 6 option → deser crash. Giữ plain string (an-toàn + đối-xứng). BE có thể DB-verify `tabAC Asset Downtime Log.reason ⊆ 6` nếu muốn enum sau. |
| **G. `start_time`/`end_time` `format:date-time`** | Sai — Frappe `get_all` trả `'YYYY-MM-DD HH:MM:SS'` (space-sep, no-TZ) ≠ RFC3339 mà `format:date-time` yêu-cầu → codegen parse crash. Plain string đúng (parity ADR-023 "dates string KHÔNG date-time"). |
| **H. `current_open` `type:null` (OpenAPI 3.1)** | yaml là **3.0.3** (`yaml:1`) — `type:null` illegal. Encode nullable-ref bằng `{nullable:true, allOf:[{$ref}]}`. |

## Consequences

- **(+)** Curate sub-tab THỨ HAI của CR-11 (sau `getAssetKpi`) — codegen client phơi model `AssetDowntimeMetrics`/`AssetDowntimeLog`/`AssetDowntimeLogOpen` typed ⇒ tab "Dừng máy" màn hồ-sơ render tổng-giờ/MTTR/phân-loại-lý-do/log-đang-mở/10-log typed. Còn 3 sub-tab: `verify_chain`/`depreciation`/`commissioning` (CR-11c..e).
- **(+)** Contract trung-thực @source: 8 key VERBATIM return-dict (TC-f), sub-schema Log 8-field + LogOpen 9-field grounded `get_all fields` + doctype (TC-g), oneOf Error khớp `_err(404)` (TC-d), LIVE introspect-parity chữ-ký `{asset_name, year}` (TC-c — chống drift + chống bịa param `name`).
- **(+)** `by_reason` open-map `{type:number}` — LẦN ĐẦU trong success-data schema; documented exception (TC-h khoá `by_reason` là schema DUY-NHẤT `additionalProperties≠false`), đặt precedent cho map-payload động sau này.
- **(0)** PATH ADD: path/opId **66→67**, c5 **55→56** (∈ `_MVP_READ_ENVELOPE` inline oneOf, mirror getAssetKpi; giữ `c5 == _MVP_BUSINESS_PATHS`); 4 schema mới `AssetDowntimeMetrics`/`AssetDowntimeMetricsEnvelope`/`AssetDowntimeLog`/`AssetDowntimeLogOpen` (naming guard `AssetDowntime*` ∩ schema hiện có == ∅).
- **(0)** CONTRACT-ONLY: 0 đụng `.py`, 0 reload worker, 0 migrate (TC-h SCOPED-HANDLER invariant chứng minh `get_asset_downtime_metrics` bất-biến HEAD↔working). Test: `test_mobile_oas` 632→**640** (+8 TC `TestMobileAssetDowntimeMetricsCurate` a..h) · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 632→640 / `_GUARD_SUITE_SUM` 775→**783** / `_MOBILE_OAS_TOTAL` 801→**809** + delta var `asset_downtime_metrics_curate_delta=8` (transition-baseline doc_09 giữ `pre_fc3_six==191`).
- **(0)** README ADR balance **38==38 → 39==39** (ADR-039.md đĩa + 1 README index row).

### Naming guard (∅)
4 schema mới `AssetDowntimeMetrics` + `AssetDowntimeMetricsEnvelope` + `AssetDowntimeLog` + `AssetDowntimeLogOpen` — `AssetDowntime*` ∩ mọi schema/parameter hiện có == ∅ (grep 0; KHÁC `AssetKpi*`/`AssetScanInfo*`/`AssetDetail*`/`AssetListItem` — khác field-set/domain). Path `getAssetDowntimeMetrics` opId unique camelCase.

## Handoff BE Bước-4 (implement yaml + test — pure-yaml, [AUTO])

CONTRACT-ONLY. Áp CHÍNH XÁC (grep-verify baseline @source TRƯỚC bump — đa-phiên race):

1. **yaml** `docs/mobile/openapi/assetcore-mobile.openapi.yaml`:
   - +1 path `/api/method/assetcore.api.imm00.get_asset_downtime_metrics` (GET, opId `getAssetDowntimeMetrics`, tag `[asset]`, 2 param `asset_name`+`year`, 200 oneOf `[AssetDowntimeMetricsEnvelope, Error]`, slot `{200,401,403}`) — chèn CẠNH `getAssetKpi` path (@`yaml:8099`) hoặc cụm asset-detail flow-2.
   - +4 schema `AssetDowntimeMetrics`/`AssetDowntimeMetricsEnvelope`/`AssetDowntimeLog`/`AssetDowntimeLogOpen` — chèn CẠNH `AssetKpi`/`AssetKpiEnvelope` (@`yaml:5678-5765`). `current_open` = `{nullable:true, allOf:[{$ref: AssetDowntimeLogOpen}]}`.
2. **test** `assetcore/tests/test_mobile_oas.py`:
   - +class `TestMobileAssetDowntimeMetricsCurate` a..h (8 TC — xem Invariant contract). Hằng path/schema-ref mới (`_ASSET_DOWNTIME_METRICS_PATH`, `_ASSET_DOWNTIME_METRICS_ENVELOPE_SCHEMA`/`_REF`, `_ASSET_DOWNTIME_METRICS_SCHEMA_REF`) mirror `_ASSET_KPI_*`.
   - `_EXPECTED_TEST_COUNT` **632→640**; + membership: thêm path vào `_MVP_BUSINESS_PATHS` + `_MVP_READ_ENVELOPE` + c5 map `getAssetDowntimeMetrics → AssetDowntimeMetricsEnvelope` (**55→56**).
   - **⚠️ path-count assertion 66→67:** ~40+ literal `66` (`len(paths)`/`len(ids)`/`len(set(ids))`/`len(ops)`) rải toàn file (chèn theo getAssetKpi 65→66) PHẢI bump **66→67**. Full test-run bắt sót.
3. **docset** `assetcore/tests/test_mobile_docset.py`:
   - `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` **632→640** · `_GUARD_SUITE_SUM` **775→783** · `_MOBILE_OAS_TOTAL` **801→809**.
   - `test_tc_mob_doc_09`: +`asset_downtime_metrics_curate_delta = 8` (cạnh `asset_kpi_curate_delta`) + `- asset_downtime_metrics_curate_delta` vào chuỗi trừ `pre_fc3_six` (giữ `==191`).
4. **DoD:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` → **Ran 640 OK** · `…test_mobile_docset` → **Ran 9 OK**; RED-before (strip path) → FAIL → restore → GREEN.

## Handoff CORE-DEV (native repo — ngoài `assetcore`)

Sau regenerate client từ OAS mirror: model `AssetDowntimeMetrics` (8 field) + `AssetDowntimeLog`/`AssetDowntimeLogOpen` + service-method `getAssetDowntimeMetrics(assetName, year?)`. Tab "Dừng máy" màn hồ-sơ-thiết-bị render: tổng giờ dừng · số lần dừng (breakdown_count) · MTTR (giờ/lần) · biểu-đồ phân-loại giờ theo lý-do (`by_reason` map) · thẻ log đang-mở (`current_open` — nếu có, kèm `downtime_hours_so_far`) · danh-sách 10 log gần nhất (`logs`). CR-11b → RESOLVED (contract curated, backend đã ship LIVE). Kế tiếp CR-11c..e: `verify_chain`/`depreciation`/`commissioning`.
