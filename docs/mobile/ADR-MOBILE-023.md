# ADR-MOBILE-023 — `getAssetPmHistory` (FLOW-2 DEVICE-PROFILE / IMM-08 — bồi 1 path GET lịch-sử BẢO-TRÌ PM của asset vào mobile contract) — contract GROUNDED 1:1 endpoint LIVE `imm08.get_asset_pm_history`

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-023 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-29 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-022** (`getAssetRepairHistory` SINGLE-shape device-profile read-history: rows-key `history` + asset-key `asset_ref`, 200 = single `$ref` KHÔNG `oneOf [Env,Error]`) · **ADR-MOBILE-021** (`listTransfers` SINGLE-shape: handler 0 `_err` ⇒ 200 single `$ref`) · **getAssetIncidentHistory (R28)** (FLOW-2 read-history precedent — envelope KHÔNG pagination + element grounded `fields`) · **ADR-MOBILE-008 / Open#1 int-vs-bool** (Frappe Check 0/1 → `integer` KHÔNG `boolean`) · Core Doc IMM-08 [`04_Backend_Design.md`](../imm-08/04_Backend_Design.md) + [`05_API_Specification.md §9`](../imm-08/05_API_Specification.md) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm08.py:124-126`, `assetcore/services/imm08.py:1012-1021`, `assetcore/assetcore/doctype/pm_task_log/pm_task_log.json`, `assetcore/utils/api_handler.py:33-51`, `assetcore/tests/test_mobile_oas.py`, `assetcore/tests/test_mobile_docset.py`). Contract narrative: [`04-api-contract.md`](./04-api-contract.md) (FLOW-2 device-profile pm-history). Narrative roadmap: [`13-be-completion-roadmap.md`](./13-be-completion-roadmap.md).

---

## Context

Mobile MVP (field-tech) "quét QR → hồ-sơ thiết bị" (flow-2) đã ĐÓNG **bộ-ba** read-history sau ADR-MOBILE-022: `getAssetIncidentHistory` (lịch-sử **sự-cố** — Incident Report, R28) + `getAssetTimeline` (dòng-thời-gian **vòng-đời** — Asset Lifecycle Event, R32) + `getAssetRepairHistory` (lịch-sử **sửa-chữa CM** — Asset Repair, R42/ADR-022). **Còn THIẾU mắt-xích CUỐI** mà KTV cần khi đứng trước máy: **lịch-sử BẢO-TRÌ ĐỊNH-KỲ (PM)** của asset — "máy này PM lần cuối khi nào, kết quả Pass/Fail, có trễ hạn không, lần PM tới khi nào?". Đây là dữ-liệu DocType **`PM Task Log`** (KHÁC `Asset Repair`/`Incident Report`), surface ở tab **"Lịch sử bảo trì"** màn hồ-sơ-thiết-bị flow-2 — **ĐÓNG triad→quartet** incident + repair + **PM**.

Endpoint nguồn **ĐÃ LIVE** (CONTRACT-ONLY): `imm08.get_asset_pm_history` (`api/imm08.py:124-126`) → `svc.get_asset_history` (`services/imm08.py:1012-1021`). Vòng này **bồi 1 path GET** vào mobile yaml để codegen sinh client; **KHÔNG đụng `.py`** (KHÔNG reload gunicorn, KHÔNG migrate).

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `get_asset_pm_history` (`api/imm08.py:124-126`)
- `@frappe.whitelist()` @`:124` — **bare** (KHÔNG `allow_guest`) ⇒ guest/no-token → **dispatcher-403** (`PermissionError`, `is_whitelisted`); bearer hết-hạn → **401** (`AuthenticationError`). ⇒ response slot `{200,401,403}` (mirror `getAssetRepairHistory`/`listTransfers`, KHÁC `getUserContext` allow_guest `{200,401}`).
- `def get_asset_pm_history(asset_ref: str, limit: int = 10)` @`:125` — **2 param**: `asset_ref` (positional, no-default ⇒ required) + `limit` (typed `int` default `10`). ⚠️ Param tên **`asset_ref`** (KHÁC `getAssetIncidentHistory` dùng `asset`; PARITY `getAssetRepairHistory`). ⚠️ KHÁC `get_asset_repair_history` (`limit: str = "10"`): ở đây `limit: int = 10` (typed int, handler vẫn ép `int(limit)` @`:126` an-toàn cả khi query-string). Live-sig parity: `inspect.signature(imm08.get_asset_pm_history).parameters == {asset_ref, limit}`.
- Handler @`:126` = **`return handle(svc.get_asset_history, asset_ref, limit=int(limit))`** — **0 nhánh `_err` in-handler** (KHÔNG `try/except`; chỉ `handle()` wrap).

### `svc.get_asset_history` (`services/imm08.py:1012-1021`)
- `PMTaskLogRepo.list(filters={"asset_ref": asset_ref}, fields=[10], order_by="completion_date desc", page_size=int(limit))` @`:1013-1020`. ⚠️ **KHÁC repair**: filter CHỈ `{asset_ref}` — **KHÔNG `docstatus:1`** (PM Task Log `is_submittable=None` @`pm_task_log.json`, KHÔNG có docstatus-gate; mọi log đều là record hoàn-tất). KHÔNG pagination (chỉ `page_size` = limit cap).
- `return {"asset_ref": asset_ref, "history": logs}` @`:1021` — **rows-key `history`** + **asset-key `asset_ref`** (PARITY repair; KHÁC incident `{asset, items}`). Svc **KHÔNG raise `ServiceError`** (0 validate-guard; asset∄/chưa-PM → `history=[]`, KHÔNG lỗi).
- **10 field** GROUNDED `fields=[...]` @`:1015-1017`: `name`, `pm_work_order`, `pm_type`, `completion_date`, `technician`, `overall_result`, `is_late`, `days_late`, `next_pm_date`, `summary`.

### `handle()` envelope (`utils/api_handler.py:33-51`)
- `handle(fn, ...)` = `try: return _ok(fn(...)) except ServiceError: return _err(...)` @`:48-51`. **CHỈ bắt `ServiceError`**. Vì `get_asset_history` **0 raise `ServiceError`** ⇒ `handle` **LUÔN `_ok`** ⇒ **200 = SINGLE success envelope** (KHÔNG có Error branch trên HTTP-200).

### DocType `PM Task Log` (`pm_task_log.json`) — type-trap @source
| Field | Fieldtype | Wire type | Ghi chú |
|---|---|---|---|
| `name` | (PK autoname) | `string` | **required** (PK naming-series, vd PMTL-2026-04-00012) |
| `pm_work_order` | **Link** `PM Work Order` | `string` | KHÔNG enum |
| `pm_type` | **Data** | `string` | tự-do (vd Quarterly) — KHÔNG enum (KHÁC overall_result) |
| `completion_date` | **Date** | `string` | **date-trap** — KHÔNG `format:date-time` (Frappe Date `'yyyy-MM-dd'`) |
| `technician` | **Link** `User` | `string` | KHÔNG enum |
| `overall_result` | **Select** | `string` **enum** `[Pass, Pass with Minor Issues, Fail]` | options `Pass\nPass with Minor Issues\nFail` @json — KHÁC repair (repair 0 Select-enum field) |
| `is_late` | **Check** (0/1) | **`integer`** | **int-vs-bool trap** — KHÔNG `boolean`/`enum[0,1]` (mirror repair `sla_breached`) |
| `days_late` | **Int** | **`integer`** | genuine int count (≥0) |
| `next_pm_date` | **Date** | `string` | **date-trap** — KHÔNG `format:date-time` |
| `summary` | **Text** | `string` | "" nếu trống |

## Decision

**Bồi 1 path GET (`getAssetPmHistory`) GROUNDED 1:1 `imm08.get_asset_pm_history`, +2 schema RIÊNG, response slot `{200,401,403}`, 200 = SINGLE-shape.** Tag `pm` (domain IMM-08 read-history, mirror `getPmWorkOrder` tag `pm` + repair `getAssetRepairHistory` tag `repair`). Path-count **52→53**, opId **52→53** (đếm thật `grep -cE '^\s{2}/'` = 53). CONTRACT-ONLY (pure-yaml).

1. **`getAssetPmHistory`** — `GET /api/method/assetcore.api.imm08.get_asset_pm_history` › `operationId: getAssetPmHistory` (dotted-tail == opId, camelCase, UNIQUE). 2 param: `asset_ref` (query, **required**, string, **NO default** — khớp `imm08.py:125`) + `limit` (query, optional, integer, default 10, minimum 1). KHÔNG `requestBody` (GET). KHÔNG `page`/`page_size` (svc chỉ limit cap). **200 = `$ref AssetPmHistoryEnvelope` SINGLE** (KHÔNG `oneOf [Env, Error]` — handler 0 `_err`, svc 0 `ServiceError`; mirror `getAssetRepairHistory`/`listTransfers`). slot `{200,401,403}`: `401 = Unauthorized401` · `403 = Forbidden` SINGLE-SHAPE (dispatcher-403 guest/no-token — bare `@whitelist` `api/imm08.py:124` KHÔNG `allow_guest`). KHÔNG `404` (`history[]` rỗng hợp-lệ nếu asset chưa-từng-PM).

2. **`AssetPmHistoryEnvelope`** — closed (`additionalProperties:false`), `required [success, data]`; `success.enum [true]`; `data` = closed object `required [asset_ref, history]` — **rows-key `history`** + **asset-key `asset_ref`** (PARITY `AssetRepairHistoryEnvelope`; KHÁC `AssetIncidentHistoryEnvelope.data.required[asset, items]`). KHÔNG `pagination` (svc chỉ limit cap). `history` = array of `$ref AssetPmHistoryItem`.

3. **`AssetPmHistoryItem`** — closed (`additionalProperties:false`), `required` EXACT `[name]` (PK; field khác optional). **EXACT 10 field GROUNDED** `PMTaskLogRepo.list fields` @`:1015-1017` (xem bảng type-trap §Context). **3 KHÁC-BIỆT vs `AssetRepairHistoryItem`:** (a) **10 prop** (KHÔNG 9); (b) `overall_result` = **`string` enum `[Pass, Pass with Minor Issues, Fail]`** (Select bounded @json — repair có 0 Select-enum); (c) **2 integer field** `is_late` (Check 0/1) + `days_late` (Int) — KHÔNG `boolean` (repair có 1 Check `sla_breached`). Dates `completion_date`/`next_pm_date` = `string` KHÔNG `format:date-time` (Date `'yyyy-MM-dd'`).

**Phạm vi membership-set (test_mobile_oas):** 1 path **∈ `_MVP_BUSINESS_PATHS`** (bare `@whitelist` ⇒ 401/403 symmetry +1) · **∉ `_MVP_READ_ENVELOPE`** (SINGLE-shape, KHÔNG oneOf read-envelope) · **∉ `_DETAIL_OPID`** (list-history, KHÔNG single-detail) · **∉ `_AUTH_PATHS` / `_ALLOW_GUEST_PATHS`**. **CONTRACT-ONLY**: `git diff HEAD -- api/imm08.py + services/imm08.py` phần `get_asset_pm_history`/`get_asset_history` = **TRỐNG** ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO] thật, né HARD-STOP USER). 52 path hiện-hữu **byte-identical**; `d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | KHÔNG wire, app dùng `getAssetRepairHistory` cho cả PM | SAI domain — repair đọc `Asset Repair` (CM), KHÔNG phải `PM Task Log` (bảo-trì định-kỳ). Tab "Lịch sử bảo trì" đứt mạch. Endpoint LIVE @source, bồi contract = codegen-ready ngay. |
| B | Reuse `AssetRepairHistoryEnvelope`/`AssetRepairHistoryItem` | Field-set THẬT KHÁC (PM Task Log 10-field ≠ Asset Repair 9-field; `overall_result` enum + `is_late`/`days_late`/`next_pm_date`/`pm_type` PM-riêng). Reuse = contract nói dối shape → strict-codegen deser drop/CRASH. C3-split: `*Envelope`/`*Item` RIÊNG (precedent ADR-MOBILE-009/022). |
| C | 200 = `oneOf [AssetPmHistoryEnvelope, Error]` (mirror `getAssetIncidentHistory` R28) | Handler `get_asset_pm_history` @`:126` = `handle(svc.get_asset_history)`; svc @`:1012-1021` **0 raise `ServiceError`** ⇒ `handle` LUÔN `_ok` ⇒ 0 Error branch trên HTTP-200. Khai `oneOf` = claim error-mode không tồn tại. SINGLE-shape source-faithful (mirror `getAssetRepairHistory` ADR-022 / `listTransfers` ADR-021). |
| D | `is_late` = `boolean` (đọc tự-nhiên "đã trễ?") | Frappe Check wire **0/1 (int)** KHÔNG `true/false`. Strict-codegen Dart/Kotlin deser `bool` từ `0`/`1` → CRASH (Open#1). `integer` faithful; KHÔNG `enum[0,1]` (GENUINE Check int, mirror repair `sla_breached`). |
| E | `completion_date`/`next_pm_date` = `string format:date-time` | Frappe **Date** wire `'yyyy-MM-dd'` (KHÔNG datetime, KHÔNG ISO-8601 offset). `format:date-time` ⇒ strict parser reject → deser fail. `string` no-format faithful (mirror repair dates R35/ADR-022, `occurred_datetime`). |
| F | Param tên `asset` (mirror `getAssetIncidentHistory`) | Signature THẬT `get_asset_pm_history(asset_ref, ...)` @`:125` dùng **`asset_ref`**. Khai `asset` = drift contract↔source → codegen query-key sai → handler nhận `asset_ref=None` → empty. `asset_ref` live-sig parity. |
| G | Bỏ enum cho `overall_result` (string tự-do như repair `root_cause_category`) | `overall_result` là **Select bounded** `[Pass, Pass with Minor Issues, Fail]` @`pm_task_log.json` (KHÁC repair `root_cause_category` Data/Select tự-do). Khai enum = codegen sinh sealed-class/enum đúng + chống giá-trị-lạ. |
| ✅ H | 1 path GET, 2 schema RIÊNG, SINGLE-200, rows-key `history`/asset-key `asset_ref`, `is_late`+`days_late` integer, `overall_result` enum, dates string no-format, slot `{200,401,403}` | Grounded 1:1 source; blast-radius = +1 path +2 schema (PURE-YAML); codegen sinh `getAssetPmHistory()` đúng shape; SINGLE vs oneOf phản-ánh đúng KHÔNG có `_err` in-handler; 3 khác-biệt vs repair (10-field, enum, 2-int) đều có source-evidence. ĐÓNG quartet device-profile read-history (sự-cố + vòng-đời + CM + **PM**). |

## Consequences

- **(+)** Hành-trình field-tech "quét QR → hồ-sơ thiết bị" ĐÓNG **bộ-tứ** read-history: sự-cố (`getAssetIncidentHistory`) + vòng-đời (`getAssetTimeline`) + sửa-chữa CM (`getAssetRepairHistory`) + **bảo-trì PM (`getAssetPmHistory`)**. KTV thấy kết-quả PM gần nhất / trễ-hạn / lịch PM tới ngay tại máy.
- **(+)** Contract GROUNDED 1:1 source — SINGLE-200 (handler 0 `_err`, svc 0 `ServiceError`) mirror `getAssetRepairHistory`; live-sig parity `{asset_ref, limit}` chống drift; 10 field grounded `PMTaskLogRepo.list`; `is_late`/`days_late integer` + `overall_result enum` + dates `string` no-date-time né mọi codegen-deser trap.
- **(+)** **CONTRACT-ONLY** — `git diff` api/imm08.py + services/imm08.py phần `get_asset_pm_history`/`get_asset_history` = TRỐNG ⇒ KHÔNG reload gunicorn, KHÔNG migrate; `test_oas_generator`/`d12`/`d15`/`d17` UNCHANGED (pure mobile-yaml). 52 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator); 0 dangling `$ref` (2 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`). `history[]` RỖNG hợp lệ (asset chưa-PM) → KHÔNG 404.
- **(−)** **3 KHÁC-BIỆT có-chủ-đích vs `getAssetRepairHistory`** (10-field vs 9, `overall_result` enum, 2 integer-field vs 1) — codegen sinh model riêng (KHÔNG share `AssetRepairHistoryItem`); phản-ánh ĐÚNG source shape, KHÔNG duplication thừa.
- **(−)** `getAssetPmHistory` là META-read (lịch-sử PM), **KHÔNG tự sinh Lifecycle Event** (read-only — event sinh ở mutation `submitPmResult` → `pm_completed`, KHÔNG ở read; CLAUDE.md §10).
- **(−)** Đồng-bộ counter (BE confirm số TC THẬT @source): `_EXPECTED_TEST_COUNT` `492→~502` (test_mobile_oas, +TC class `TestMobileGetAssetPmHistoryContract` a..j) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `492→~502` + `_GUARD_SUITE_SUM` + `_MOBILE_OAS_TOTAL` (test_mobile_docset, +cùng N) + ~site path/opId `52→53` — ĐỒNG-BỘ trong Bước-4.

---

## Đã thực thi (Bước-4 ATOMIC — handoff BE/Test)

> CONTRACT-ONLY — KHÔNG đụng `api/*.py`/`services/*.py`. `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` + `test_mobile_docset` GREEN.

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`):
- +1 path `/api/method/assetcore.api.imm08.get_asset_pm_history` (GET, opId `getAssetPmHistory`, tag `pm`); 2 param `asset_ref` (req, no-default) + `limit` (opt int default 10, minimum 1); 200 = `$ref AssetPmHistoryEnvelope` SINGLE; slot `{200,401,403}` (`401 Unauthorized401`, `403 Forbidden`).
- +2 schema `AssetPmHistoryEnvelope` (closed, `data.{asset_ref, history[]}`, success enum[true]) + `AssetPmHistoryItem` (closed, 10 prop, req `[name]`, `is_late`/`days_late integer`, `overall_result` enum 3-value, dates `string` no-`format`).
- Tái-dùng (KHÔNG tạo mới): `Unauthorized401`, `Forbidden`. 0 orphan, 0 dangling.

**(2) test_mobile_oas.py**: path/opId count `52→53` (~site) + roadmap regex `r"52 path"→r"53 path"`; +`_ASSET_PM_HISTORY_*` constants + opId convention map + `_MVP_BUSINESS_PATHS` (+`_ASSET_PM_HISTORY_PATH`); +1 TC class `TestMobileGetAssetPmHistoryContract` (a..j, ≈10 TC: GET-only/opId/MVP/count · 2-param `asset_ref`-not-`asset` no-default · SINGLE-200-not-oneOf · envelope `history`/`asset_ref` no-pagination · item EXACT-10 · int-bool-trap `is_late`+`days_late` integer · `overall_result` enum-bound · 401 slot · 403 single-shape + symmetry + no-dangling · live-sig parity `{asset_ref,limit}`); `_EXPECTED_TEST_COUNT` `492→~502` (số THẬT = giá-trị introspect).

**(3) test_mobile_docset.py**: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `492→~502` · `_GUARD_SUITE_SUM` +N · `_MOBILE_OAS_TOTAL` +N · transition `pm_history_delta` reconcile. ADR-MOBILE-023 registered README (TC-MOB-DOC-02).

**(4) docs narrative**: `04-api-contract.md` (FLOW-2 device-profile pm-history) + `13-be-completion-roadmap.md` (52→53 path) + README ADR-row (ADR-MOBILE-023) + Core Doc [`05_API_Specification.md §9`](../imm-08/05_API_Specification.md).

**BACKLOG (vòng kế):** quartet device-profile read-history ĐÃ ĐÓNG (sự-cố + vòng-đời + CM + PM). Khả-năng kế: `getAssetCalibrationHistory` (lịch-sử HIỆU-CHUẨN IMM-11) nếu có endpoint LIVE → nâng quartet thành pentad.
