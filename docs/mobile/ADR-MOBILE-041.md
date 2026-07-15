# ADR-MOBILE-041 — `getAssetCommissioningOrigin` (`imm04.get_commissioning_origin`) curate vào OAS mirror (**CR-11d · asset-detail sub-tab #4 "Nguồn gốc thiết bị"** — bồi ĐÚNG 1 GET-read path trả bản-ghi tiếp-nhận/lắp-đặt (Asset Commissioning) + PO gốc của 1 asset (truy-vết provenance NĐ98); sub-tab THỨ TƯ của CR-11 sau `getAssetKpi` (ADR-038) + `getAssetDowntimeMetrics` (ADR-039) + `getAssetVerifyChain` (ADR-040); **LẦN ĐẦU success-data = WRAPPER 2 tầng** — `{asset, commissioning:object|null}` + nested `CommissioningOriginRecord` — `commissioning` nullable-ref idiom mirror `current_open` ADR-039)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-041 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-13 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến trên HTTP-200 body `Error`, route theo `body.success`/`body.http_status`; KHÔNG discriminator, closed-schema oneOf) · **sibling trực-tiếp**: **ADR-MOBILE-040** (`getAssetVerifyChain` — CÙNG asset-detail sub-tab flow-2 CR-11, GET bare `@whitelist`, asset∄ → HTTP-200 nhánh Error, 200 = oneOf `[Envelope, Error]`) + **ADR-MOBILE-039** (`getAssetDowntimeMetrics` — **nguồn idiom nullable-ref** `{type:object, nullable:true, allOf:[$ref]}` cho `current_open`) + **ADR-MOBILE-038** (`getAssetKpi` — required = subset always-non-null, nullable-value ∉ required; `total_repair_cost` FINANCIAL-curate-verbatim precedent) · Core Doc IMM-04 [`04-api-contract.md`](./04-api-contract.md) §8.43 (getAssetCommissioningOrigin) + [`docs/imm-04/05_API_Specification.md`](../imm-04/05_API_Specification.md) §mobile-commissioning-origin |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (@2026-07-13). **HAI tầng cùng tên `get_commissioning_origin`** (handler + service — KHÁC ADR-040 handler+builder khác-tên): (1) **handler** `get_commissioning_origin(asset_name: str) -> dict` def@`assetcore/api/imm04.py:314-316` — bare `@frappe.whitelist()` (GET-ok, no `allow_guest` → guest dispatcher-403); thân = `return _handle(svc.get_commissioning_origin, asset_name)` (tier-1 mỏng, `_handle` = `assetcore/utils/api_handler.py:33` bắt `ServiceError → _err` HTTP-200 Decision-B; **KHÔNG `rbac.require`** ⇒ 0 in-handler cap-403). (2) **service** `get_commissioning_origin(asset_name: str) -> dict` def@`assetcore/services/imm04.py:1972-1997` — SoT payload: `if not frappe.db.exists(_DT_ASSET, asset_name): raise ServiceError(ErrorCode.NOT_FOUND, ...)` @`:1974-1975` (asset∄ → Error envelope HTTP-200); `commissioning_ref = frappe.db.get_value(_DT_ASSET, asset_name, "commissioning_ref")` @`:1977`; `if not commissioning_ref: return {"asset": asset_name, "commissioning": None}` @`:1978-1979` (early-return #1); `comm = frappe.db.get_value(_DT, commissioning_ref, [11 field], as_dict=True)` @`:1981-1987`; `if not comm: return {"asset": asset_name, "commissioning": None}` @`:1988-1989` (early-return #2); `comm["transferred_doc_count"] = frappe.db.count("Asset Document", {...})` @`:1992-1996`; `return {"asset": asset_name, "commissioning": comm}` @`:1997`. `git diff HEAD` `api/imm04.py` + `services/imm04.py` (vùng `get_commissioning_origin`) = TRỐNG round NÀY ⇒ backend ĐÃ LIVE, thay đổi CHỈ ở OAS mirror + test + doc. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Nguồn yêu cầu: `assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` CR-11d.

---

## ⚠️ Reconciliation đánh-số (đa-phiên) — BE Bước-4 ĐỌC TRƯỚC

Đề mục Bước-2 (vòng 29) ghi baseline: `path/opId 68→69`, `_EXPECTED_TEST_COUNT 648→656`, `3 docset counter +8`. **VERIFY @source @2026-07-13** (grep-verify TRƯỚC bump — đa-phiên race dời số; ĐỌC giá trị HIỆN TẠI lúc build, KHÔNG hardcode từ brief):

| Hạng mục | LIVE baseline @source (đã grep) | CR-11d target |
|---|---|---|
| ADR số | **040 = getAssetVerifyChain** (đã tồn tại đĩa + README) | **041** (NEW) |
| path/opId | **68** (`grep -c '^  /api/method' yaml` = 68) | **68→69** |
| c5 (`_MVP_READ_ENVELOPE`/map) | **57** (getAssetVerifyChain đã 56→57) | **57→58** |
| `_EXPECTED_TEST_COUNT` | **648** (@`test_mobile_oas.py:212`) | **648→656** (+8 TC) |
| `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` | **648** | **648→656** |
| `_GUARD_SUITE_SUM` | **791** | **791→799** |
| `_MOBILE_OAS_TOTAL` | **817** | **817→825** |
| README ADR balance | **40 file / 40 index-row** | **41==41** |

> Grounded @2026-07-13 (concurrent session ĐÃ dời 622→648 qua CR-11a/b/c): 2 inline literal `_EXPECTED_TEST_COUNT == 648` @`test_mobile_oas.py` (receivecert/cancelcal meta) bump 648→656; ~40+ literal path/opId `68` (`len(paths)`/`len(ids)`/`len(set(ids))`/`len(spec.get("paths"))`/`len(ops)`/`actual_paths`/`len(op_ids)`) + 3 c5 `57` + 1 parity-business `57` + 4 backward-compat opId-set-minus (`66`/`67`) rải toàn file PHẢI bump; opId convention-map SSoT (§8.1) THÊM `get_commissioning_origin → getAssetCommissioningOrigin`. Full test-run bắt sót.

---

## Context

Màn **hồ-sơ-thiết-bị** mobile (flow-2) có nhiều sub-tab; **5 sub-tab phân-tích/truy-vết backend ĐÃ LIVE**: `kpi` (curated CR-11a/ADR-038), `downtime` (curated CR-11b/ADR-039), `verify_chain` (curated CR-11c/ADR-040), **`commissioning`** (nguồn-gốc tiếp-nhận/lắp-đặt — sub-tab THỨ TƯ được curate), `depreciation`. Codegen client mobile KHÔNG có model typed cho tab "Nguồn gốc thiết bị" ⇒ dead-end contract (client parse free-form `data` Map, mất type-safety cho `asset`/`commissioning{...}`).

CR-11d = curate sub-tab THỨ TƯ của CR-11, chọn `getAssetCommissioningOrigin` — **truy-vết provenance NĐ98**. Mỗi asset (nếu đã nghiệm-thu) gắn 1 bản-ghi `Asset Commissioning` (`commissioning_ref`) ghi: PO gốc mua-sắm, NCC, model, ngày tiếp-nhận/lắp-đặt, serial NCC, giá mua, hạn bảo-hành, người nghiệm-thu, + số tài-liệu chuyển-giao. Đây là bằng-chứng **nguồn-gốc/xuất-xứ** thiết-bị y-tế (truy-xuất PO → NCC → model), yêu-cầu **NĐ98/2021** + WHO HTM procurement/installation lifecycle.

Ràng buộc quyết định:
1. **CONTRACT-ONLY** — handler `get_commissioning_origin` ĐÃ LIVE @`api/imm04.py:315`, service ĐÃ LIVE @`services/imm04.py:1972`. Thay đổi CHỈ ở OAS mirror + test + doc; **KHÔNG đụng `.py`, KHÔNG reload worker, KHÔNG migrate**.
2. **200 = oneOf `[AssetCommissioningOriginEnvelope, Error]`** (Decision-B) — service `raise ServiceError(ErrorCode.NOT_FOUND, ...)` asset∄ @`:1975` → `_handle` → `_err` HTTP-200 body Error; mirror sibling. **⚠️ KHÁC sibling**: siblings dùng `_err(...)` in-handler; CR-11d dùng `raise ServiceError → _handle` — CÙNG kết-quả (Error envelope HTTP-200 `http_status ⊇ {404}`), khác cơ-chế.
3. **`AssetCommissioningOrigin` = WRAPPER 2-tầng** (ĐIỂM KHÁC CỐT-LÕI vs 3 sibling OBJECT PHẲNG): `data = $ref AssetCommissioningOrigin` = `{asset:string, commissioning:object|null}`; `commissioning` khi non-null = `$ref CommissioningOriginRecord` (12-prop). ⇒ **3 schema** (wrapper + record + envelope), KHÁC sibling 2-schema.
4. **`commissioning` = nullable-ref idiom** — service có **2 early-return** `{"asset":..., "commissioning":None}` @`:1979` (asset chưa gắn `commissioning_ref`) + @`:1989` (commissioning-doc biến-mất). ⇒ key `commissioning` **LUÔN present** (∈ `required`), **value null** khi chưa có. OpenAPI 3.0.3 nullable-ref = `{type:object, nullable:true, allOf:[$ref CommissioningOriginRecord]}` — `type:object` BẮT BUỘC làm sibling của `nullable` (redocly lint `nullable-type-sibling`; KHÔNG `type:null` = 3.1-only). **Mirror `AssetDowntimeMetrics.current_open` ADR-039** (nullable-ref, KHÁC `broken_at`/`index` ADR-040 scalar-nullable).
5. **`CommissioningOriginRecord` = 12-prop VERBATIM get_value** — 11 field list-literal `frappe.db.get_value(_DT, commissioning_ref, [...], as_dict=True)` @`:1983-1985` (thứ-tự khớp) + `transferred_doc_count` @`:1996`. `get_value(as_dict=True)` LUÔN trả đủ 11 key (value None nếu column trống) ⇒ key luôn present, nhưng **required = {name, transferred_doc_count}** (2 anchor always-non-null: `name`=docname PK; `transferred_doc_count`=`frappe.db.count` int); 9 field value-nullable **∉ required** (convention `getAssetKpi` ADR-038 nullable-value ∉ required — KHÁC `getAssetDowntimeMetrics` required==props). `workflow_state` = `type:string` KHÔNG nullable (Link default `''` KHÔNG NULL) NHƯNG ∉ required (minimal-commitment — brief KHÔNG tag req).
6. **`asset_name` REQUIRED** — chữ-ký LIVE `get_commissioning_origin(asset_name: str)` @`:1972` positional no-default ⇒ `required:true`, `type:string`. **⚠️ KHÁC sibling `getAssetKpi(name)`/`getAssetDowntimeMetrics(asset_name, year='')`/`getAssetVerifyChain(asset)`** — param tên `asset_name` VÀ REQUIRED (KHÁC `year` OPTIONAL @CR-11b). Service `raise NOT_FOUND` khi asset∄ @`:1975` ⇒ required là source-faithful.
7. **`purchase_price` = FINANCIAL curate VERBATIM** — Currency field → `number` nullable; curate nguyên theo get_value, **UI-render deferred** mobile client (persona-gate FE) per LL-BE-57 + precedent `total_repair_cost` ADR-038 (KHÔNG strip khỏi contract).
8. **KHÔNG discriminator, KHÔNG split HasCommissioning|NoCommissioning** — coupling `commissioning present-as-null ⟺ asset chưa gắn ref` mã-hoá bằng `nullable:true` (né discriminator: `commissioning` là object-ref, discriminator OAS 3.x chỉ string). Client đọc `commissioning != null` TRƯỚC khi truy field record.
9. **Read-only — KHÔNG audit** — endpoint ĐỌC (get_value + count), KHÔNG mutate → KHÔNG sinh Lifecycle Event / IMM Audit Trail record mới.

## Decision

Bồi ĐÚNG 1 GET-read path + 3 schema vào OAS mirror:

### Path `/api/method/assetcore.api.imm04.get_commissioning_origin`
- `get:` (GET-only, bare `@whitelist`), `operationId: getAssetCommissioningOrigin`, `tags: [asset]`.
- **1 query param:** `asset_name` (`in:query`, **`required:true`**, `type:string`) — grounded chữ-ký `get_commissioning_origin(asset_name)` positional no-default @`services/imm04.py:1972`. **⚠️ Tên `asset_name` (KHÔNG `name`, KHÔNG `asset`); REQUIRED (KHÁC sibling `year` OPTIONAL).**
- **200 = oneOf `[AssetCommissioningOriginEnvelope, Error]`** closed-schema, KHÔNG discriminator (route-by-VALUE `body.success`); `Error.http_status ⊇ {404}` (asset∄ raise NOT_FOUND @`:1975` → `_handle`).
- **Response slot** `{200, 401, 403}` — 401 `Unauthorized401` SINGLE-SHAPE (bearer hết hạn), **403 `Forbidden` SINGLE-SHAPE** (bare `@whitelist` no-`allow_guest` → guest dispatcher-403; KHÔNG in-handler cap-403 — `_handle` KHÔNG `rbac.require`).

### Schema `AssetCommissioningOrigin` (WRAPPER) — closed
| Property | Type | required / nullable | Grounding @source |
|---|---|---|---|
| `asset` | string | **required** | echo `asset_name` @`:1979/1989/1997` — LUÔN present |
| `commissioning` | object (nullable-ref) | **required** · **nullable** | `{type:object, nullable:true, allOf:[$ref CommissioningOriginRecord]}` — null khi 2 early-return @`:1979/1989`; key LUÔN emit |

- `properties[]` = EXACT 2 `{asset, commissioning}`; `required[]` = EXACT 2 (commissioning LUÔN emit value-null); `additionalProperties:false`.

### Schema `CommissioningOriginRecord` (12-prop VERBATIM) — closed
| Property | Type | required / nullable | Grounding @source |
|---|---|---|---|
| `name` | string | **required** | docname Asset Commissioning (get_value đầu list @`:1983`, PK non-null) |
| `workflow_state` | string | (∉ required, non-nullable) | Link Workflow State @`:1983`; Link default `''` KHÔNG NULL ⇒ non-null value |
| `po_reference` | string | nullable | Link AC Purchase @`:1983` — PO gốc; null khi không gắn |
| `vendor` | string | nullable | Link AC Supplier @`:1983` |
| `master_item` | string | nullable | Link IMM Device Model @`:1983` |
| `reception_date` | string (format:date) | nullable | Date @`:1984` |
| `commissioning_date` | string (format:date) | nullable | Date @`:1984` |
| `vendor_serial_no` | string | nullable | Data @`:1984` |
| `purchase_price` | number | nullable · **FINANCIAL** | Currency @`:1985` — curate VERBATIM, UI-render deferred |
| `warranty_expiry_date` | string (format:date) | nullable | Date @`:1985` |
| `commissioned_by` | string | nullable | Link User @`:1985` |
| `transferred_doc_count` | integer | **required** | `frappe.db.count(Asset Document, {asset_ref, source_commissioning})` @`:1992-1996` — LUÔN set (int non-null) |

- `properties[]` = EXACT 12 (thứ-tự VERBATIM get_value list @`:1983-1985` + `transferred_doc_count` @`:1996`); `required[]` = EXACT 2 `{name, transferred_doc_count}`; 9 field value-nullable ∈ nullable-set ∉ required; 3 Date field `format:date`; `additionalProperties:false`.

### Schema `AssetCommissioningOriginEnvelope` — closed
- `additionalProperties:false`, `required:[success, data]`, `success` `type:boolean` `enum:[true]`, `data = $ref AssetCommissioningOrigin`.

### Invariant contract (guard `TestMobileAssetCommissioningOriginCurate` a..h, `test_mobile_oas`)
- **a** yaml load; path-count **68→69**; opId-count 69 unique camelCase; path GET-ONLY opId `getAssetCommissioningOrigin` tag `asset`.
- **b** ĐÚNG 1 query param `asset_name` (`required:true`, string); KHÔNG requestBody; **LIVE introspect-parity** `set(inspect.signature(imm04.get_commissioning_origin).parameters) == {"asset_name"}` (`asset_name` no-default → required). **⚠️ khoá tên `asset_name` (KHÔNG `name`/`asset`); REQUIRED KHÁC sibling year OPTIONAL.**
- **c** 200 = oneOf `[AssetCommissioningOriginEnvelope, Error]` route-by-VALUE, 0 discriminator; 2 branch closed; `success.enum` disjoint `[true]`/`[false]`; `Error.http_status ⊇ {404}` (asset∄ @`:1975`); slot `{200,401,403}`.
- **d** `AssetCommissioningOrigin` WRAPPER closed; props EXACT `{asset, commissioning}`; required EXACT `[asset, commissioning]`; `asset`=string; `commissioning` = nullable-ref idiom `{type:object, nullable:true, allOf:[$ref CommissioningOriginRecord]}`.
- **e** `CommissioningOriginRecord` closed; props EXACT 12; required EXACT `{name, transferred_doc_count}`; 9 value-nullable ∈ nullable ∉ required; 3 Date `format:date`; types VERBATIM grounded doctype; `purchase_price`=number FINANCIAL. **GROUNDING** (chống-bịa, đọc TRỰC-TIẾP `services/imm04.py`): AST/parse `get_commissioning_origin` → get_value field-list (11) + subscript `transferred_doc_count` (1) == 12 prop record.
- **f** slot `{200,401,403}`; 403 SINGLE `$ref` Forbidden (dispatcher-only, `_handle` KHÔNG `rbac.require`); ∈ `_MVP_BUSINESS_PATHS`/`_PATHS_REQUIRE_401`/`_PATHS_REQUIRE_403`/`_MVP_READ_ENVELOPE`.
- **g** `AssetCommissioningOriginEnvelope` closed `required[success,data]`; `data = $ref AssetCommissioningOrigin`.
- **h** **zero-footprint** — 3 schema mới ∩ existing == chỉ 3 tên mới (naming-guard prefix `AssetCommissioningOrigin*` == 2, `CommissioningOrigin*` == 1); `getAssetKpi`/`getAssetDowntimeMetrics`/`getAssetVerifyChain` BẤT BIẾN; 0 dangling `$ref`; **DUAL SCOPED-HANDLER invariant** — source AST CẢ HAI `get_commissioning_origin` (api/imm04.py handler + services/imm04.py service) BẤT BIẾN HEAD↔working (CONTRACT-ONLY pure-yaml — payload SoT ở service).
- **RED-before/GREEN-after**: đổi `transferred_doc_count` type integer→string → RED (TC-e type + grounding) ⇒ khôi phục → GREEN. (Đã demo @2026-07-13: 1 FAIL `commorigin_e` → restore → Ran 656 OK.)

## Alternatives

| Phương án | Vì sao LOẠI |
|---|---|
| **A. Giữ dead-end (không curate)** | Tab "Nguồn gốc thiết bị" mất model typed — codegen parse free-form `data` Map; sub-tab backend LIVE mãi không dùng; mất kênh phơi provenance NĐ98 (PO→NCC→model) lên mobile. |
| **B. Flat 12-prop (bỏ wrapper, gộp `asset` + 11 field vào 1 object)** | Sai @source — service trả `{asset, commissioning}` 2-tầng; `commissioning=null` khi chưa nghiệm-thu (2 early-return). Flat → mất khả-năng biểu-diễn "asset tồn-tại nhưng chưa có commissioning" (null-object). Wrapper trung-thực. |
| **C. `commissioning` scalar-nullable `{type:object, nullable:true}` KHÔNG allOf** | KHÔNG type-safe — codegen sinh `Map` thay model `CommissioningOriginRecord`. Nullable-ref idiom `allOf:[$ref]` giữ typed model + nullable (mirror `current_open` ADR-039). |
| **D. `commissioning` ∉ required (optional)** | Sai @source — key `commissioning` LUÔN emit (cả 2 early-return + happy-path). Optional → codegen coi absent hợp-lệ, sai contract. ∈ required + nullable = present-as-null đúng. |
| **E. required = all 12 (như AssetDowntimeMetrics)** | Sai — 9 field value-nullable (Link/Date/Currency trống → get_value None). Ép required → strict codegen deser CRASH khi field trống. Convention `getAssetKpi` (nullable-value ∉ required) đúng cho payload có field trống hợp-lệ. |
| **F. Strip `purchase_price` (FINANCIAL) khỏi contract** | Sai — get_value trả `purchase_price` @`:1985`; curate VERBATIM theo return-dict (LL-BE-57 + `total_repair_cost` ADR-038). Persona-gate/UI-render là việc FE client, KHÔNG cắt khỏi contract. |
| **G. param `asset_name` OPTIONAL (như `year` CR-11b)** | Sai @source — chữ-ký positional no-default @`:1972` + service `raise NOT_FOUND` khi asset∄ @`:1975`. REQUIRED source-faithful. |
| **H. 200 single-shape (KHÔNG oneOf Error)** | Sai @source — service `raise ServiceError NOT_FOUND` @`:1975` → `_handle` → Error envelope HTTP-200. Single-shape → codegen không phân-biệt success/error → crash khi 404. Decision-B oneOf đúng. |
| **I. Grounding chỉ đọc handler `api/imm04.py`** | Sai — handler `_handle(svc.get_commissioning_origin, asset_name)` chỉ wrap; payload SoT + get_value field-list ở service @`:1983-1996`. TC-e + SCOPED-HANDLER PHẢI đọc `services/imm04.py`. |

## Consequences

- **(+)** Curate sub-tab THỨ TƯ của CR-11 — codegen client phơi model `AssetCommissioningOrigin` + `CommissioningOriginRecord` typed ⇒ tab "Nguồn gốc thiết bị" màn hồ-sơ render: PO gốc (`po_reference`) · NCC (`vendor`) · model (`master_item`) · ngày tiếp-nhận/lắp-đặt · serial NCC · hạn bảo-hành · người nghiệm-thu · số tài-liệu chuyển-giao (`transferred_doc_count`); khi `commissioning=null`: thẻ "Chưa có hồ-sơ nghiệm-thu". Còn 1 sub-tab: `depreciation` (CR-11e).
- **(+)** Contract trung-thực @source: 12 prop = get_value list + count (TC-e grounding đọc TRỰC-TIẾP service AST — chống bịa + chống ép all-required), wrapper nullable-ref khớp 2 early-return (TC-d), oneOf Error khớp `raise NOT_FOUND` (TC-c), LIVE introspect-parity chữ-ký `{asset_name}` required (TC-b — chống drift + chống bịa param `name`/`asset`).
- **(+)** **LẦN ĐẦU success-data = WRAPPER 2-tầng nested-nullable-object** (`{asset, commissioning:Record|null}`) — đặt precedent cho payload "container + optional-nested-detail"; nullable-ref idiom tái-dùng từ `current_open` ADR-039.
- **(0)** PATH ADD: path/opId **68→69**, c5 **57→58** (∈ `_MVP_BUSINESS_PATHS` + `_MVP_READ_ENVELOPE` inline oneOf, mirror sibling); 3 schema mới (naming guard `AssetCommissioningOrigin*` ∩ 2 + `CommissioningOrigin*` ∩ 1, ∩ schema hiện có == ∅).
- **(0)** CONTRACT-ONLY: 0 đụng `.py`, 0 reload worker, 0 migrate (TC-h DUAL SCOPED-HANDLER invariant chứng minh `get_commissioning_origin` @api/imm04.py + @services/imm04.py bất-biến HEAD↔working). Test: `test_mobile_oas` 648→**656** (+8 TC `TestMobileAssetCommissioningOriginCurate` a..h) · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 648→656 / `_GUARD_SUITE_SUM` 791→**799** / `_MOBILE_OAS_TOTAL` 817→**825** + delta var `asset_commissioning_origin_curate_delta=8` (transition-baseline doc_09 giữ `pre_fc3_six==191`).
- **(0)** README ADR balance **40==40 → 41==41** (ADR-041.md đĩa + 1 README index row).

### Naming guard (∅)
3 schema mới `AssetCommissioningOrigin` + `AssetCommissioningOriginEnvelope` + `CommissioningOriginRecord` — prefix `AssetCommissioningOrigin*` == 2 tên mới, `CommissioningOrigin*` == 1 tên mới, ∩ mọi schema/parameter hiện có `== ∅` (grep 0). Path `getAssetCommissioningOrigin` opId unique camelCase.

## Handoff CORE-DEV (native repo — ngoài `assetcore`)

Sau regenerate client từ OAS mirror: model `AssetCommissioningOrigin` (`asset:string, commissioning:CommissioningOriginRecord | null`) + `CommissioningOriginRecord` (12 field, `poReference?`/`vendor?`/… nullable, `transferredDocCount:integer`) + service-method `getAssetCommissioningOrigin(assetName)`. Tab "Nguồn gốc thiết bị" màn hồ-sơ-thiết-bị render: khi `commissioning != null` → card provenance (PO gốc, NCC, model, ngày tiếp-nhận/lắp-đặt, serial, hạn bảo-hành, người nghiệm-thu, số tài-liệu chuyển-giao); khi `commissioning == null` → empty-state "Chưa có hồ-sơ nghiệm-thu/lắp-đặt". ⚠️ `purchase_price` = FINANCIAL → render theo persona (gate quyền xem giá). CR-11d → RESOLVED (contract curated, backend đã ship LIVE). Kế tiếp CR-11e: `depreciation` (sub-tab #5, HOÀN TẤT bộ-5 asset-detail).
