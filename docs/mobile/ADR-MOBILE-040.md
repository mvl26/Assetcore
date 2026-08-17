# ADR-MOBILE-040 — `getAssetVerifyChain` (`imm00.verify_chain`) curate vào OAS mirror (**CR-11c · asset-detail sub-tab #3 "Chuỗi kiểm toán bất biến"** — bồi ĐÚNG 1 GET-read path kiểm-tra tính-toàn-vẹn hash-chain SHA-256 của IMM Audit Trail 1 asset; sub-tab THỨ BA của CR-11 sau `getAssetKpi` (ADR-038) + `getAssetDowntimeMetrics` (ADR-039); **LẦN ĐẦU success-data schema có property OPTIONAL** — 2 field `broken_at`/`index` chỉ emit khi `valid=false` — documented pattern)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-040 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-13 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến trên HTTP-200 body `Error`, route theo `body.success`/`body.http_status`; KHÔNG discriminator, closed-schema oneOf) · **sibling trực-tiếp**: **ADR-MOBILE-039** (`getAssetDowntimeMetrics` — CÙNG asset-detail sub-tab flow-2 CR-11, GET bare `@whitelist`, `_err(404)` asset∄ → HTTP-200 nhánh Error, 200 = oneOf `[Envelope, Error]`, `data=$ref` OBJECT PHẲNG) + **ADR-MOBILE-038** (`getAssetKpi` — 1 param `name` single-read) · **precedent optional-emit**: **ADR-MOBILE-036** (CR-21 — property OPTIONAL ∉ `required` khi BE emit có-điều-kiện, pattern `allowed_transitions`/`scene_photos`) · Core Doc IMM-00 [`04-api-contract.md`](./04-api-contract.md) §8.42 (getAssetVerifyChain) + [`docs/imm-00/05_API_Specification.md`](../imm-00/05_API_Specification.md) §III.20 |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (@2026-07-13). **HAI hàm nguồn** (KHÁC siblings 1-hàm): (1) **handler** `verify_chain(asset)` def@`assetcore/api/imm00.py:1768-1774` — bare `@frappe.whitelist()` (GET-ok, no `allow_guest` → guest dispatcher-403); `if not frappe.db.exists(_DT_ASSET, asset): return _err(_(_ERR_ASSET_NOT_FOUND), 404)` @`:1771-1772` (asset∄ → HTTP-200 nhánh Error, Decision-B); `result = verify_audit_chain(asset); return _ok(result)` @`:1773-1774`. (2) **builder** `verify_audit_chain(asset) -> dict` def@`assetcore/utils/lifecycle.py:97-114` — nơi **SoT return-shape**: đọc `tabIMM Audit Trail WHERE asset=%s ORDER BY timestamp ASC, creation ASC` @`:98-107`, recompute `_compute_hash(r, prev)` từng hàng @`:110`, so `expected != r.hash_sha256 or (prev and r.prev_hash != prev)` @`:111` → **2 return-shape**: FAIL `return {"valid": False, "broken_at": r.name, "index": idx, "count": len(rows)}` @`:112` / PASS `return {"valid": True, "count": len(rows)}` @`:114`. `git diff` `api/imm00.py` (vùng `verify_chain`) + `utils/lifecycle.py` (vùng `verify_audit_chain`) = TRỐNG round NÀY ⇒ backend ĐÃ LIVE, thay đổi CHỈ ở OAS mirror + test + doc. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Nguồn yêu cầu: `assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` CR-11c.

---

## ⚠️ Reconciliation đánh-số (đa-phiên) — BE Bước-4 ĐỌC TRƯỚC

Đề mục Bước-2 (vòng 27) ghi baseline: `path/opId 67→68`, `_EXPECTED_TEST_COUNT 640→640+N`, `3 docset counter +N`. **VERIFY @source @2026-07-13** (grep-verify TRƯỚC bump — đa-phiên race, giống cảnh-báo ADR-039):

| Hạng mục | LIVE baseline @source (đã grep) | CR-11c target |
|---|---|---|
| ADR số | **039 = getAssetDowntimeMetrics** (đã tồn tại đĩa + README) | **040** (NEW) |
| path/opId | **67** (`grep -c '^  /api/method' yaml` = 67) | **67→68** |
| c5 (`_MVP_READ_ENVELOPE`/map) | **56** (getAssetDowntimeMetrics đã 55→56) | **56→57** |
| `_EXPECTED_TEST_COUNT` | **640** (@`test_mobile_oas.py:212`) | **640→648** (+8 TC) |
| `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` | **640** | **640→648** |
| `_GUARD_SUITE_SUM` | **783** | **783→791** |
| `_MOBILE_OAS_TOTAL` | **809** | **809→817** |
| README ADR balance | **39 file / 39 index-row** | **40==40** |

> Grounded @2026-07-13: `ls docs/mobile/ADR-MOBILE-*.md | wc -l` = 39; `grep -c '^  /api/method' yaml` = 67; `_EXPECTED_TEST_COUNT = 640` @`test_mobile_oas.py:212`; `_GUARD_SUITE_SUM = 783` / `_MOBILE_OAS_TOTAL = 809` @`test_mobile_docset.py`. **⚠️ README index-row count**: `grep -cE 'ADR-MOBILE-0[0-9][0-9]' README.md` = 42 nhưng đó ĐẾM CẢ tham-chiếu inline trong body row (vd "sau `getAssetKpi` (ADR-038)"); **index-row THẬT = 39** (== số file). BE grep-verify row thật TRƯỚC bump 39→40.

---

## Context

Màn **hồ-sơ-thiết-bị** mobile (flow-2) có nhiều sub-tab; **5 sub-tab phân-tích backend ĐÃ LIVE**: `kpi` (curated CR-11a/ADR-038), `downtime` (curated CR-11b/ADR-039), **`verify_chain`** (kiểm-tra toàn-vẹn chuỗi kiểm-toán — sub-tab THỨ BA được curate), `depreciation`, `commissioning`. Codegen client mobile KHÔNG có model typed cho tab "Chuỗi kiểm toán bất biến" ⇒ dead-end contract (client parse free-form `data` Map, mất type-safety cho cờ `valid`/`count`/`broken_at`/`index`).

CR-11c = curate sub-tab THỨ BA của CR-11, chọn `getAssetVerifyChain` — **truy-vết tính-toàn-vẹn NĐ98**. Mọi hành-động vòng-đời thiết bị sinh 1 record `IMM Audit Trail` với `hash_sha256` = SHA-256 của nội-dung record + `prev_hash` (hash record trước) → **hash-chain bất-biến** (tamper-evident). Endpoint duyệt lại toàn chuỗi theo `asset`, recompute từng hash, phát-hiện điểm gãy (record bị sửa/xoá/chèn) → trả `valid:true/false` (+ vị-trí gãy nếu có). Đây là bằng-chứng tuân-thủ **NĐ98/2021** (truy-xuất-nguồn-gốc lịch-sử thiết-bị y-tế) + WHO HTM traceability.

Ràng buộc quyết định:
1. **CONTRACT-ONLY** — handler `verify_chain` ĐÃ LIVE @`imm00.py:1769`, builder `verify_audit_chain` ĐÃ LIVE @`lifecycle.py:97`. Thay đổi CHỈ ở OAS mirror + test + doc; **KHÔNG đụng `.py`, KHÔNG reload worker, KHÔNG migrate**.
2. **200 = oneOf `[AssetVerifyChainEnvelope, Error]`** (Decision-B) — handler có `_err(_(_ERR_ASSET_NOT_FOUND), 404)` asset∄ @`:1771-1772` đến trên HTTP-200 body Error; mirror `getAssetKpi`/`getAssetDowntimeMetrics`.
3. **`AssetVerifyChain` = OBJECT PHẲNG single** (`data = $ref` trực-tiếp) — handler `_ok(result)` với `result` = flat dict, KHÔNG paginate, KHÔNG `{items}`.
4. **VARIABLE return-dict (2 shape) → property OPTIONAL** — ĐIỂM KHÁC CỐT-LÕI vs siblings: `AssetDowntimeMetrics`/`AssetKpi` có return-dict CỐ-ĐỊNH (mọi key luôn emit → all-required hoặc nullable-present). `verify_audit_chain` có **2 shape rời**: PASS `{valid, count}` (2 key) / FAIL `{valid, broken_at, index, count}` (4 key). ⇒ `broken_at`+`index` **CHỈ present ở nhánh FAIL** (`valid=false`) → **OPTIONAL** (∉ `required`) + `nullable:true`. `required` = **giao 2 shape = EXACT `{valid, count}`** (2 key có ở MỌI response). `properties` = **hợp 2 shape = `{valid, count, broken_at, index}`** (4 key).
5. **Đơn hàm-nguồn? KHÔNG — 2 hàm** — return-shape KHÔNG ở handler `verify_chain` (chỉ wrap `_ok`) mà ở builder `verify_audit_chain` @`lifecycle.py:112/114`. ⇒ grounding (TC-g) + SCOPED-HANDLER invariant (TC-h) PHẢI đọc **CẢ HAI** `verify_chain` (imm00.py) VÀ `verify_audit_chain` (lifecycle.py).
6. **1 param `asset`** — chữ-ký LIVE `verify_chain(asset: str)` @`:1769` positional no-default ⇒ `required:true`, `type:string`. **⚠️ Tên `asset`** (KHÁC `getAssetKpi(name)` = `name`, KHÁC `getAssetDowntimeMetrics(asset_name)` = `asset_name`). PHẢI đúng tên `asset` (chống drift codegen sai param).
7. **KHÔNG discriminator, KHÔNG split ValidChain|InvalidChain** — coupling `broken_at`+`index` present ⟺ `valid=false` là **invariant runtime** (2 shape rời), KHÔNG mã-hoá bằng schema. OpenAPI 3.0.3 KHÔNG có `if/then` (3.1-only); split thành 2 sub-schema discriminated oneOf sẽ (a) phá acceptance "single closed `AssetVerifyChain`, required EXACT {valid,count}", (b) buộc codegen sinh 2 model + union phức-tạp cho payload đơn-giản. Xem Alternatives-C.
8. **Read-only — KHÔNG audit** — endpoint KIỂM-TRA (đọc + recompute hash), KHÔNG mutate → KHÔNG sinh Lifecycle Event / IMM Audit Trail record mới. (Nghịch-lý: verify chuỗi audit KHÔNG tự thêm mắt-xích audit.)

## Decision

Bồi ĐÚNG 1 GET-read path + 2 schema vào OAS mirror:

### Path `/api/method/assetcore.api.imm00.verify_chain`
- `get:` (GET-only, bare `@whitelist`), `operationId: getAssetVerifyChain`, `tags: [asset]`.
- **1 query param:**
  - `asset` (`in:query`, **`required:true`**, `type:string`) — grounded chữ-ký `verify_chain(asset: str)` positional no-default @`imm00.py:1769`. **⚠️ Tên `asset` (KHÔNG `name`, KHÔNG `asset_name`).**
- **200 = oneOf `[AssetVerifyChainEnvelope, Error]`** closed-schema, KHÔNG discriminator (route-by-VALUE `body.success`); `Error.http_status ⊇ {404}` (asset∄ in-handler @`:1771-1772`).
- **Response slot** `{200, 401, 403}` — 401 `Unauthorized401` SINGLE-SHAPE (bearer hết hạn), **403 `Forbidden` SINGLE-SHAPE** (bare `@whitelist` no-`allow_guest` → guest dispatcher-403; KHÔNG in-handler cap-403 — handler KHÔNG `rbac.require` @api-level).

### Schema `AssetVerifyChain` (VERBATIM 2 return-shape @`lifecycle.py:112/114`) — closed
| Property | Type | required / nullable | Grounding @source |
|---|---|---|---|
| `valid` | boolean | **required** | `"valid": True`@`:114` / `False`@`:112` — GENUINE boolean (KHÔNG int-enum[0,1]; Python `bool` literal, KHÔNG Frappe Check-field 0/1) |
| `count` | integer | **required** | `"count": len(rows)`@`:112/114` — số record audit đã duyệt, LUÔN present cả 2 shape |
| `broken_at` | string | **OPTIONAL** (∉ required) · **nullable** | `"broken_at": r.name`@`:112` — mã record `IMM Audit Trail` tại điểm gãy; **CHỈ present khi `valid=false`** |
| `index` | integer | **OPTIONAL** (∉ required) · **nullable** | `"index": idx`@`:112` — vị-trí (0-based) record gãy trong chuỗi đã sắp `timestamp ASC`; **CHỈ present khi `valid=false`** |

- `properties[]` = **EXACT 4** = HỢP 2 shape `{valid, count} ∪ {valid, broken_at, index, count}`.
- `required[]` = **EXACT 2** `{valid, count}` = GIAO 2 shape (key có ở MỌI response). `broken_at`+`index` **∉ required** (optional-emit, mirror ADR-036 `is_*_breached`).
- `broken_at`+`index` = `nullable:true` (scalar-nullable đơn-giản `{type, nullable:true}` — KHÁC `current_open` ADR-039 nullable-**ref** cần `allOf`; đây là scalar nên KHÔNG cần `allOf`).
- `additionalProperties:false`.
- **INV-VC-1 (invariant runtime, prose-only — KHÔNG schema-enforce):** trong 1 response, `broken_at` present ⟺ `index` present ⟺ `valid == false`. OpenAPI 3.0.3 KHÔNG mã-hoá (né discriminator/if-then per Decision-7); client đọc `valid` TRƯỚC, chỉ truy `broken_at`/`index` khi `valid=false`.

### Schema `AssetVerifyChainEnvelope` — closed
- `additionalProperties:false`, `required:[success, data]`, `success` `type:boolean` `enum:[true]`, `data = $ref AssetVerifyChain`.

### Invariant contract (guard `TestMobileAssetVerifyChainCurate` a..h, `test_mobile_oas`)
- **a** yaml load; path-count **67→68**; opId-count 68 unique camelCase.
- **b** path TỒN TẠI, GET-ONLY (chỉ key `get`), opId `getAssetVerifyChain`, tag `asset`.
- **c** **ĐÚNG 1** query param `asset` (`in:query`, `required:true`, `schema.type:string`); KHÔNG requestBody; **LIVE introspect-parity** `set(inspect.signature(imm00.verify_chain).parameters) == {"asset"}` (`asset` no-default → required). **⚠️ khoá param tên `asset` (KHÔNG `name`/`asset_name`).**
- **d** 200 = oneOf `[AssetVerifyChainEnvelope, Error]` route-by-VALUE, 0 discriminator; 2 branch closed; `success.enum` disjoint `[true]`/`[false]`; `Error.http_status ⊇ {404}` (asset∄ @`:1771-1772`).
- **e** Envelope closed `required[success,data]`; `data = $ref AssetVerifyChain` (OBJECT PHẲNG — KHÔNG `items`/`pagination` top-level).
- **f** `AssetVerifyChain` closed `additionalProperties:false`; props **EXACT 4** `{valid, count, broken_at, index}`; **required EXACT 2** `{valid, count}`; `broken_at`+`index` **∉ required** + `nullable:true`; `valid`=boolean (GENUINE, KHÔNG int-enum), `count`=integer, `broken_at`=string, `index`=integer.
- **g** **GROUNDING 2-return-shape** (chống-bịa, đọc TRỰC-TIẾP source `utils/lifecycle.py`): AST/parse `verify_audit_chain` → 2 `return` dict-literal; FAIL-keys `== {"valid","broken_at","index","count"}` (@`:112`) ∧ PASS-keys `== {"valid","count"}` (@`:114`); assert `schema.required == PASS-keys` (= giao) ∧ `set(schema.properties) == FAIL-keys` (= hợp) ∧ `set(schema.properties) - schema.required == {"broken_at","index"}` (fail-only optional).
- **h** **zero-footprint** — `AssetKpi`/`AssetKpiEnvelope`/`AssetDowntimeMetrics`/`AssetScanInfo`/`AssetDetail` BẤT BIẾN (disjoint props `AssetVerifyChain` ∩ mỗi cái); naming guard `AssetVerifyChain*` ∩ mọi schema/parameter hiện có `== ∅`; 0 dangling `$ref` toàn yaml; **DUAL SCOPED-HANDLER invariant** — source AST **CẢ HAI** `verify_chain` (gồm `@frappe.whitelist`, `api/imm00.py`) VÀ `verify_audit_chain` (`utils/lifecycle.py`) BẤT BIẾN HEAD↔working (CONTRACT-ONLY pure-yaml — return-shape SoT ở builder).
- **RED-before/GREEN-after**: strip path `verify_chain` → RED (TC-a path-count 67≠68 + TC-b `Thiếu path`) ⇒ bồi lại → GREEN.

## Alternatives

| Phương án | Vì sao LOẠI |
|---|---|
| **A. Giữ dead-end (không curate)** | Tab "Chuỗi kiểm toán bất biến" mất model typed — codegen client parse free-form `data` Map, mất type-safety cho `valid`/`count`/`broken_at`/`index`; sub-tab backend LIVE mãi không dùng được; mất kênh phơi bằng-chứng toàn-vẹn NĐ98 lên mobile. |
| **B. 200 single-shape (KHÔNG oneOf Error)** | Sai @source — handler CÓ `_err(_(_ERR_ASSET_NOT_FOUND), 404)` asset∄ @`:1771-1772` đến trên HTTP-200 body Error. Single-shape → codegen không phân-biệt success/error → parse crash khi 404. Decision-B oneOf đúng (mirror getAssetKpi/getAssetDowntimeMetrics). |
| **C. Split `ValidChain{valid:true,count}` \| `InvalidChain{valid:false,broken_at,index,count}` discriminated oneOf** | (1) Phá acceptance "single closed `AssetVerifyChain`, required EXACT {valid,count}". (2) `valid` = boolean → discriminator OpenAPI 3.x illegal (chỉ string discriminator). (3) Codegen sinh 2 model + union cho payload đơn-giản 4-field — over-engineer. Single closed schema + 2 optional-nullable + INV-VC-1 prose là đủ (mirror ADR-036 optional-emit). |
| **D. `broken_at`+`index` vào `required` (all-4-required như AssetDowntimeMetrics)** | Sai @source — nhánh PASS `{valid, count}` @`:114` KHÔNG có 2 key này ⇒ ép required → **strict codegen deser CRASH** khi `valid=true` (thiếu required field). return-dict verify_audit_chain KHÔNG cố-định (2 shape rời) ⇒ 2 key PHẢI optional. |
| **E. `broken_at`+`index` KHÔNG `nullable`** | Acceptance ghi rõ `nullable`. Dù nhánh FAIL value non-null (`r.name`/`idx`), giữ `nullable:true` để codegen an-toàn (client biểu-diễn "absent" = null khi round-trip; parity intent acceptance). Non-nullable + optional cũng hợp-lệ wire NHƯNG acceptance chốt nullable. |
| **F. `valid` = integer enum `[0,1]`** | Sai type — `verify_audit_chain` trả Python `bool` literal (`True`/`False` @`:112/114`), KHÔNG Frappe Check-field 0/1 (KHÁC `is_open` ADR-039 / `sla_breached`). `_ok` serialize `bool` → JSON `true`/`false`. GENUINE boolean (mirror `reauth_required` ADR-024). |
| **G. Grounding chỉ đọc handler `verify_chain` (imm00.py)** | Sai — handler chỉ `_ok(verify_audit_chain(asset))`, return-shape KHÔNG ở đó. SoT 2-shape ở builder `verify_audit_chain` @`lifecycle.py:112/114`. TC-g + SCOPED-HANDLER PHẢI đọc `utils/lifecycle.py`. |
| **H. Sinh audit event khi verify** | Sai — read-only integrity check KHÔNG mutate; thêm record audit sẽ (a) tự-thay-đổi chuỗi đang kiểm, (b) vô-hạn phình audit mỗi lần đọc. Handler 0 `insert`/`_log`. |

## Consequences

- **(+)** Curate sub-tab THỨ BA của CR-11 (sau `getAssetKpi`/`getAssetDowntimeMetrics`) — codegen client phơi model `AssetVerifyChain` typed ⇒ tab "Chuỗi kiểm toán bất biến" màn hồ-sơ render badge `valid` (xanh "Toàn vẹn" / đỏ "Phát hiện sai lệch") + `count` (số record đã duyệt) + khi FAIL: `broken_at` (record gãy) + `index` (vị-trí). Còn 2 sub-tab: `depreciation`/`commissioning` (CR-11d..e).
- **(+)** Contract trung-thực @source: 4 prop = HỢP 2 shape, required 2 = GIAO 2 shape (TC-f), grounding đọc TRỰC-TIẾP `verify_audit_chain` 2 return-dict (TC-g — chống bịa + chống ép all-required), oneOf Error khớp `_err(404)` (TC-d), LIVE introspect-parity chữ-ký `{asset}` (TC-c — chống drift + chống bịa param `name`/`asset_name`).
- **(+)** **LẦN ĐẦU success-data schema có property OPTIONAL genuine-absent** (`broken_at`/`index` VẮNG ở nhánh pass, KHÁC AssetKpi nullable-nhưng-present-as-null) — đặt precedent optional-emit cho payload đa-shape sau này; INV-VC-1 (coupling prose-only) documented.
- **(0)** PATH ADD: path/opId **67→68**, c5 **56→57** (∈ `_MVP_BUSINESS_PATHS` + `_MVP_READ_ENVELOPE` inline oneOf, mirror getAssetKpi/getAssetDowntimeMetrics; giữ `c5 == _MVP_BUSINESS_PATHS`); 2 schema mới `AssetVerifyChain`/`AssetVerifyChainEnvelope` (naming guard `AssetVerifyChain*` ∩ schema hiện có == ∅).
- **(0)** CONTRACT-ONLY: 0 đụng `.py`, 0 reload worker, 0 migrate (TC-h DUAL SCOPED-HANDLER invariant chứng minh `verify_chain` @imm00.py + `verify_audit_chain` @lifecycle.py bất-biến HEAD↔working). Test: `test_mobile_oas` 640→**648** (+8 TC `TestMobileAssetVerifyChainCurate` a..h) · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 640→648 / `_GUARD_SUITE_SUM` 783→**791** / `_MOBILE_OAS_TOTAL` 809→**817** + delta var `asset_verify_chain_curate_delta=8` (transition-baseline doc_09 giữ `pre_fc3_six==191`).
- **(0)** README ADR balance **39==39 → 40==40** (ADR-040.md đĩa + 1 README index row).

### Naming guard (∅)
2 schema mới `AssetVerifyChain` + `AssetVerifyChainEnvelope` — `AssetVerifyChain*` ∩ mọi schema/parameter hiện có `== ∅` (grep 0; KHÁC `AssetKpi*`/`AssetDowntime*`/`AssetScanInfo*`/`AssetDetail*`/`AssetListItem` — khác field-set/domain). Path `getAssetVerifyChain` opId unique camelCase.

## Handoff BE Bước-4 (implement yaml + test — pure-yaml, [AUTO])

CONTRACT-ONLY. Áp CHÍNH XÁC (grep-verify baseline @source TRƯỚC bump — đa-phiên race):

1. **yaml** `docs/mobile/openapi/assetcore-mobile.openapi.yaml`:
   - +1 path `/api/method/assetcore.api.imm00.verify_chain` (GET, opId `getAssetVerifyChain`, tag `[asset]`, **1 param** `asset` required string, 200 oneOf `[AssetVerifyChainEnvelope, Error]`, slot `{200,401,403}`) — chèn CẠNH `getAssetDowntimeMetrics` path (@`yaml:8353`) / cụm asset-detail flow-2 (sau §8.41 comment block).
   - +2 schema `AssetVerifyChain`/`AssetVerifyChainEnvelope` — chèn CẠNH `AssetDowntimeMetrics`/`AssetKpi` schema (@`yaml:5678-5765` vùng). `broken_at`/`index` = `{type, nullable:true}` scalar-nullable đơn-giản (KHÔNG `allOf` — KHÁC `current_open` nullable-ref). `required:[valid, count]` (KHÔNG gồm broken_at/index).
2. **test** `assetcore/tests/guards/test_mobile_oas.py`:
   - +class `TestMobileAssetVerifyChainCurate` a..h (8 TC — xem Invariant contract). Hằng path/schema-ref mới (`_ASSET_VERIFY_CHAIN_PATH`, `_ASSET_VERIFY_CHAIN_ENVELOPE_SCHEMA`/`_REF`, `_ASSET_VERIFY_CHAIN_SCHEMA_REF`) mirror `_ASSET_DOWNTIME_METRICS_*`. **TC-g** đọc TRỰC-TIẾP `assetcore/utils/lifecycle.py` (AST/parse `verify_audit_chain` 2 return-dict) — KHÔNG hardcode key-set (grounding thật). **TC-c** `inspect.signature(imm00.verify_chain)`. **TC-h** SCOPED-HANDLER đọc CẢ `imm00.verify_chain` + `lifecycle.verify_audit_chain`.
   - `_EXPECTED_TEST_COUNT` **640→648**; + membership: thêm path vào `_MVP_BUSINESS_PATHS` + `_MVP_READ_ENVELOPE` + c5 map `getAssetVerifyChain → AssetVerifyChainEnvelope` (**56→57**).
   - **⚠️ path-count assertion 67→68:** ~40+ literal `67` (`len(paths)`/`len(ids)`/`len(set(ids))`/`len(ops)`) rải toàn file (mỗi lần path-add bump) PHẢI bump **67→68**. Full test-run bắt sót.
3. **docset** `assetcore/tests/guards/test_mobile_docset.py`:
   - `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` **640→648** · `_GUARD_SUITE_SUM` **783→791** · `_MOBILE_OAS_TOTAL` **809→817**.
   - `test_tc_mob_doc_09`: +`asset_verify_chain_curate_delta = 8` (cạnh `asset_downtime_metrics_curate_delta`) + `- asset_verify_chain_curate_delta` vào chuỗi trừ `pre_fc3_six` (giữ `==191`).
4. **README** `docs/mobile/README.md`: +1 index-row `ADR-MOBILE-040.md` (grep-verify index-row 39→40 THẬT, KHÔNG đếm inline-ref).
5. **DoD:** `bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_oas` → **Ran 648 OK** (đọc dòng cuối THẬT) · `…test_mobile_docset` → **Ran 9 OK**; RED-before (strip path) → FAIL → restore → GREEN. **0 `.py` runtime / 0 gunicorn reload / 0 bench migrate.**

## Handoff CORE-DEV (native repo — ngoài `assetcore`)

Sau regenerate client từ OAS mirror: model `AssetVerifyChain` (`valid:boolean, count:integer, brokenAt?:string, index?:integer`) + service-method `getAssetVerifyChain(asset)`. Tab "Chuỗi kiểm toán bất biến" màn hồ-sơ-thiết-bị render: badge toàn-vẹn (`valid` → xanh "Chuỗi kiểm toán toàn vẹn" / đỏ "Phát hiện sai lệch chuỗi") · số record đã duyệt (`count`) · khi `valid=false`: thẻ cảnh-báo điểm gãy (`broken_at` mã record + `index` vị-trí). ⚠️ Client đọc `valid` TRƯỚC, chỉ truy `brokenAt`/`index` khi `valid=false` (INV-VC-1). CR-11c → RESOLVED (contract curated, backend đã ship LIVE). Kế tiếp CR-11d..e: `depreciation`/`commissioning`.
