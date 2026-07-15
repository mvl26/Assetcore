# ADR-MOBILE-038 — `getAssetKpi` curate vào OAS mirror (**CR-11a · asset-detail sub-tab KPI** — bồi ĐÚNG 1 GET-read path `getAssetKpi` (KPI vận-hành 12-key OBJECT PHẲNG của 1 asset) vào OAS mirror; **MỞ NHÁNH asset-detail sub-tab** — curate ĐẦU TIÊN của CR-11 (5 sub-tab backend LIVE, 0 curated: `kpi`/`verify_chain`/`depreciation`/`commissioning`/`downtime`))

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-038 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-13 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến trên HTTP-200 body `Error`, route theo `body.success`/`body.http_status`; KHÔNG discriminator, closed-schema oneOf) · **precedent read-path single-object**: `getAssetScanInfo` (`yaml` §5c — flat object closed-schema + oneOf `[Envelope, Error]`) · **precedent asset-detail flow-2**: `getAssetTimeline` (ADR-embed — GET bare `@whitelist`, param `name` required, `_err(404)` asset∄ → HTTP-200 nhánh Error) · Core Doc IMM-00 narrative [`04-api-contract.md`](./04-api-contract.md) §8 (getAssetKpi) + `docs/imm-00/05_API_Specification.md` |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (@2026-07-13): handler `get_asset_kpi(name)` def@`assetcore/api/imm00.py:1174-1175` (bare `@frappe.whitelist()` — GET-ok, no `allow_guest` → guest dispatcher-403). Trả `_ok({12-key})` @`imm00.py:1250-1263` (compute on-the-fly cửa-sổ 12 tháng: uptime/downtime từ `AC Asset Downtime Log`, MTTR/MTBF/`total_repair_cost` từ `Asset Repair docstatus=1`, `pm_compliance_pct` từ `PM Work Order`). `_err(404)` asset∄ @`imm00.py:1185-1186` → HTTP-200 nhánh Error (Decision-B). `git diff` `api/imm00.py` vùng `get_asset_kpi` = TRỐNG round NÀY ⇒ backend ĐÃ LIVE, thay đổi CHỈ ở OAS mirror + test + doc. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (path `/api/method/assetcore.api.imm00.get_asset_kpi` + schema `AssetKpi`/`AssetKpiEnvelope`). Nguồn yêu cầu: `assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` CR-11a.

---

## Context

Màn **hồ-sơ-thiết-bị** mobile (sau quét QR / điều-hướng từ danh-sách) có nhiều **sub-tab**: hồ-sơ (getAssetScanInfo/getAsset), Lịch sử (getAssetTimeline), Lịch sử sự-cố/sửa-chữa/bảo-trì (getAsset*History), và **5 sub-tab phân-tích backend ĐÃ LIVE nhưng CHƯA curate vào mirror**: `kpi` (KPI vận-hành), `verify_chain` (chuỗi xác-minh), `depreciation` (khấu-hao), `commissioning` (nghiệm-thu), `downtime` (nhật-ký ngừng). Codegen client mobile KHÔNG có model typed cho các sub-tab này ⇒ dead-end contract.

CR-11a = curate **ĐẦU TIÊN** của CR-11 (mở nhánh asset-detail sub-tab), chọn `getAssetKpi` — sub-tab "KPI" quan-trọng nhất cho KTV/quản-lý (uptime%, MTBF, MTTR, tuân-thủ PM, số lần hỏng, tổng giờ ngừng + 3 date-mốc + tổng chi-phí sửa).

Ràng buộc quyết định:
1. **CONTRACT-ONLY** — handler `get_asset_kpi` ĐÃ LIVE @`imm00.py:1174`, trả 12-key VERBATIM @`:1250-1263`. Thay đổi CHỈ ở OAS mirror + test + doc; **KHÔNG đụng `.py`, KHÔNG reload worker, KHÔNG migrate**.
2. **200 = oneOf `[AssetKpiEnvelope, Error]`** (Decision-B) — handler có `_err(404)` asset∄ @`:1185-1186` đến trên HTTP-200 body Error; KHÁC single-shape (mirror getAssetScanInfo/getAssetTimeline).
3. **AssetKpi = OBJECT PHẲNG single** (`data = $ref AssetKpi` trực-tiếp) — KHÁC getAssetTimeline (list + `{items, pagination}`). Handler trả flat dict, KHÔNG paginate.
4. **12 key VERBATIM return-dict** — closed `additionalProperties:false`; 5 always-present ∈ `required`, 7 nullable (return `None` hợp-lệ @source).
5. **`total_repair_cost` = FINANCIAL** — curate VERBATIM theo return-dict (KHÔNG strip khỏi contract); UI-render deferred mobile client (persona-gate FE, KHÔNG hiển-thị chi-phí cho persona không có quyền tài-chính).

## Decision

Bồi ĐÚNG 1 GET-read path + 2 schema vào OAS mirror:

### Path `/api/method/assetcore.api.imm00.get_asset_kpi`
- `get:` (GET-only, bare `@whitelist`), `operationId: getAssetKpi`, `tags: [asset]`.
- **1 query param** `name` (`in:query`, **`required:true`**, `type:string`) — grounded chữ-ký LIVE `get_asset_kpi(name)` positional no-default @`imm00.py:1174`.
- **200 = oneOf `[AssetKpiEnvelope, Error]`** closed-schema, KHÔNG discriminator (route-by-VALUE `body.success`); `Error.http_status ⊇ {404}` (asset∄ in-handler @`:1185-1186`).
- **Response slot** `{200, 401, 403}` — 401 `Unauthorized401` SINGLE-SHAPE (bearer hết hạn), 403 `Forbidden` SINGLE-SHAPE (bare `@whitelist` no-allow_guest → guest dispatcher-403).

### Schema `AssetKpi` (12 key VERBATIM @`imm00.py:1250-1263`) — closed
| Property | Type | required / nullable | Grounding @source |
|---|---|---|---|
| `name` | string | **required** | echo param @`:1251` |
| `lifecycle_status` | string | **required** | `doc.lifecycle_status` @`:1252` |
| `uptime_pct` | number | **required** | round vô-điều-kiện @`:1209` |
| `mtbf_days` | number | nullable | return None @`:1228-1238` (0/thiếu lần hỏng) |
| `mttr_hours` | number | nullable | None khi 0 repair @`:1217-1219` |
| `pm_compliance_pct` | number | nullable | None khi 0 PM đến-hạn @`:1248` |
| `total_repair_cost` | number | nullable · **FINANCIAL** | `sum(...) or None` @`:1221` |
| `next_pm_date` | string (date) | nullable | `doc.next_pm_date` @`:1258` |
| `next_calibration_date` | string (date) | nullable | @`:1259` |
| `byt_reg_expiry` | string (date) | nullable | @`:1260` |
| `breakdown_count` | integer | **required** | `len(dt_rows)` @`:1203/1261` |
| `total_downtime_hours` | number | **required** | round vô-điều-kiện @`:1262` |

- `required[]` = **EXACT 5** `{name, lifecycle_status, uptime_pct, breakdown_count, total_downtime_hours}` (always-present @source).
- `nullable` = **EXACT 7** (còn lại — return `None` hợp-lệ). Invariant: `required ∩ nullable == ∅` ∧ `required ∪ nullable == 12 prop`.
- 0 boolean / 0 int-enum[0,1] (KHÔNG Check field trong 12 — né int-vs-bool trap Open#1).

### Schema `AssetKpiEnvelope` — closed
- `additionalProperties:false`, `required:[success, data]`, `success.enum:[true]`, `data = $ref AssetKpi`.

### Invariant contract (guard `TestMobileGetAssetKpiContract` a..j, `test_mobile_oas`)
- **a** yaml load; path-count **65→66**; opId-count 66 unique camelCase.
- **b** path TỒN TẠI, GET-ONLY, opId `getAssetKpi`, tag `asset`.
- **c** 1 param `name` required string; KHÔNG requestBody; **LIVE introspect-parity** `inspect.signature(imm00.get_asset_kpi) == {name}` (name no-default).
- **d** 200 = oneOf `[AssetKpiEnvelope, Error]` route-by-VALUE, 0 discriminator; 2 branch closed; `success.enum` disjoint `[true]`/`[false]`.
- **e** Envelope closed `required[success,data]`; `data = $ref AssetKpi` (OBJECT PHẲNG — KHÔNG `items`/`pagination`).
- **f** AssetKpi closed; props **EXACT 12** VERBATIM return-dict; required **EXACT 5**; nullable **EXACT 7**; `required ∩ nullable == ∅`, `∪ == 12`.
- **g** type grounded (breakdown_count=integer; 6 number; name/lifecycle_status/3-date string; 3 date `format:date`); `total_repair_cost` FINANCIAL nullable number; 0 boolean/int-enum[0,1].
- **h** disjointness — AssetKpi props ≠ AssetScanInfo ∧ ≠ AssetTimelineEvent ∧ ≠ AssetListItem; 0 dangling $ref toàn yaml.
- **i** ∈ `_MVP_BUSINESS_PATHS` ∧ `_PATHS_REQUIRE_401` ∧ `_PATHS_REQUIRE_403` ∧ `_MVP_READ_ENVELOPE` (symmetry so SET); slot `{200,401,403}`; `Error.http_status ⊇ {404}`.
- **j** SCOPED-HANDLER invariant — source AST `get_asset_kpi` (gồm `@frappe.whitelist`) BẤT BIẾN HEAD↔working `imm00.py` (CONTRACT-ONLY pure-yaml; edit vô-can khác trong file ĐƯỢC PHÉP).
- **RED-before/GREEN-after**: strip schema `AssetKpi` → RED (dangling `#/components/schemas/AssetKpi` + class-f missing schema `Thiếu schema AssetKpi`) ⇒ bồi lại → GREEN.

## Alternatives

| Phương án | Vì sao LOẠI |
|---|---|
| **A. Giữ dead-end (không curate)** | Không mở nhánh CR-11 — codegen mobile mất model typed cho tab KPI, client parse free-form `data` (Map) mất type-safety cho 12 KPI field; 5 sub-tab backend LIVE mãi không dùng được. |
| **B. 200 single-shape (KHÔNG oneOf Error)** | Sai @source — handler CÓ `_err(404)` asset∄ @`:1185-1186` đến trên HTTP-200 body Error. Single-shape sẽ khiến codegen không phân biệt success/error → parse crash khi 404. Decision-B oneOf là đúng. |
| **C. Bọc `data` trong `{items}`/`{pagination}`** | Sai wire-shape — handler trả flat dict 12-key @`:1250`, KHÔNG list/paginate (KHÁC getAssetTimeline). AssetKpi = OBJECT PHẲNG (TC-e khoá `data=$ref` trực-tiếp). |
| **D. Strip `total_repair_cost` (FINANCIAL) khỏi contract** | Vi phạm curate-VERBATIM — return-dict LUÔN emit key này. Strip = contract lệch payload thật → codegen thiếu field, client mất giá-trị BE trả. Đúng: curate VERBATIM + UI-render deferred (persona-gate FE), KHÔNG strip contract. |
| **E. `additionalProperties:true` (mở schema)** | Phá closed-schema sweep + int-vs-bool guard. Return-dict là EXACT 12 key cố-định (KHÔNG as_dict passthrough như AssetDetail) ⇒ đóng `false` an-toàn, codegen sinh model chính-xác 12 field. |
| **F. 5 field nullable vào `required`** | Sai @source — 7 field return `None` hợp-lệ (0 record nguồn / Date trống). Ép required = codegen non-null → deser crash khi BE trả null. Chỉ 5 always-present ∈ required (TC-f). |

## Consequences

- **(+)** MỞ NHÁNH asset-detail sub-tab — codegen client phơi model `AssetKpi` typed (12 field) ⇒ tab "KPI" màn hồ-sơ render badge/số-liệu typed; đặt nền cho 4 sub-tab còn lại (verify_chain/depreciation/commissioning/downtime — CR-11b..e).
- **(+)** Contract trung-thực @source: 12 key VERBATIM return-dict (TC-f), type/nullable grounded từng dòng return (TC-g), oneOf Error khớp `_err(404)` (TC-d/i), LIVE introspect-parity chữ-ký (TC-c) ⇒ chống drift contract↔handler.
- **(+)** `total_repair_cost` FINANCIAL curate VERBATIM — contract đầy-đủ, mobile client tự persona-gate render (KHÔNG rò chi-phí cho persona không quyền); tách concern contract (đầy-đủ) vs UI (gated).
- **(0)** PATH ADD: path/opId **65→66**, c5 **54→55** (∈ `_MVP_READ_ENVELOPE` inline oneOf); `_MVP_BUSINESS_PATHS` 54→55 (401/403 symmetry giữ `c5_paths == _MVP_BUSINESS_PATHS`); 2 schema mới `AssetKpi`/`AssetKpiEnvelope` (naming guard `AssetKpi*` ∩ schema hiện có == ∅).
- **(0)** CONTRACT-ONLY: 0 đụng `.py`, 0 reload worker, 0 migrate (TC-j SCOPED-HANDLER invariant chứng minh `get_asset_kpi` bất-biến HEAD↔working). Test: `test_mobile_oas` 622→**632** (+10 TC `TestMobileGetAssetKpiContract` a..j) · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 622→632 / `_GUARD_SUITE_SUM` 765→**775** / `_MOBILE_OAS_TOTAL` 791→**801** + delta var `asset_kpi_curate_delta=10` (transition-baseline doc_09 giữ `pre_fc3_six==191`).

### Naming guard (∅)
2 schema mới `AssetKpi` + `AssetKpiEnvelope` — `AssetKpi*` ∩ mọi schema/parameter hiện có == ∅ (grep 0; KHÁC `AssetScanInfo*`/`AssetTimeline*`/`AssetDetail*`/`AssetListItem` — khác field-set/domain). Path `getAssetKpi` opId unique camelCase.

## Handoff CORE-DEV (native repo — ngoài `assetcore`)

Sau khi regenerate client từ OAS mirror: model `AssetKpi` (12 field typed, 7 nullable) + service-method `getAssetKpi(name)`. Tab "KPI" màn hồ-sơ-thiết-bị render 6 KPI vận-hành (uptime%/MTBF/MTTR/tuân-thủ PM/số lần hỏng/tổng giờ ngừng) + 3 date-mốc (PM kế/hiệu-chuẩn kế/hết-hạn ĐK BYT). `total_repair_cost` (FINANCIAL) — **persona-gate**: CHỈ render cho persona có quyền tài-chính (KTV thường KHÔNG thấy). CR-11a → RESOLVED (contract curated, backend đã ship LIVE). Kế tiếp CR-11b..e: verify_chain/depreciation/commissioning/downtime.
