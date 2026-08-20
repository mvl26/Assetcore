# ADR-MOBILE-022 — `getAssetRepairHistory` (FLOW-2 DEVICE-PROFILE / IMM-09 — bồi 1 path GET lịch-sử SỬA-CHỮA CM của asset vào mobile contract) — contract GROUNDED 1:1 endpoint LIVE `imm09.get_asset_repair_history`

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-022 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-29 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-021** (`listTransfers` SINGLE-shape: handler 0 `_err` ⇒ 200 = single `$ref`, KHÔNG `oneOf [Env,Error]`) · **getAssetIncidentHistory (R28)** (FLOW-2 device-profile read-history precedent — envelope KHÔNG pagination + element grounded `frappe.get_all fields`) · **ADR-MOBILE-001 (d)/(f)/(g)** (OpenAPI = hợp đồng máy-đọc) · **Open#1 int-vs-bool** (Frappe Check 0/1 → `integer` KHÔNG `boolean`) · Core Doc IMM-09 [`04_Backend_Design.md`](../imm-09/04_Backend_Design.md) + [`05_API_Specification.md`](../imm-09/05_API_Specification.md) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm09.py:126-128`, `assetcore/services/imm09.py:1212-1220`, `assetcore/utils/api_handler.py:33-51`, `assetcore/tests/guards/test_mobile_oas.py`, `assetcore/tests/guards/test_mobile_docset.py`). Contract narrative: [`04-api-contract.md`](./04-api-contract.md) (FLOW-2 device-profile repair-history). Narrative roadmap: [`13-be-completion-roadmap.md`](./13-be-completion-roadmap.md).

---

## Context

Mobile MVP (field-tech) đã có chuỗi quét-QR → hồ-sơ thiết bị với **bộ-đôi** read-history: `getAssetIncidentHistory` (lịch-sử **sự-cố** — Incident Report, R28) + `getAssetTimeline` (dòng-thời-gian **vòng-đời** — Asset Lifecycle Event, R32). **Còn THIẾU** một read-surface mà KTV cần khi đứng trước máy: **lịch-sử SỬA-CHỮA (CM)** của asset — "máy này từng sửa gì, MTTR bao lâu, có vi phạm SLA?". Đây là dữ-liệu của DocType **`Asset Repair`** (KHÁC `Incident Report`), surface ở tab "Lịch sử sửa chữa" màn hồ-sơ-thiết-bị flow-2.

Endpoint nguồn **ĐÃ LIVE** (CONTRACT-ONLY): `imm09.get_asset_repair_history` (`api/imm09.py:126-128`) → `svc.get_asset_history` (`services/imm09.py:1212-1220`). Vòng này **bồi 1 path GET** vào mobile yaml để codegen sinh client; **KHÔNG đụng `.py`** (KHÔNG reload gunicorn, KHÔNG migrate).

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `get_asset_repair_history` (`api/imm09.py:126-128`)
- `@frappe.whitelist()` @`:126` — **bare** (KHÔNG `allow_guest`) ⇒ guest/no-token → **dispatcher-403** (`PermissionError`, `is_whitelisted`); bearer hết-hạn → **401** (`AuthenticationError`). ⇒ response slot `{200,401,403}` (mirror `listTransfers`/`searchSpareParts`, KHÁC `getUserContext` allow_guest `{200,401}`).
- `def get_asset_repair_history(asset_ref: str, limit: str = "10")` @`:127` — **2 param**: `asset_ref` (positional, no-default ⇒ required) + `limit` (default str `"10"` — handler ép `int(limit)` @`:128`). ⚠️ Param tên **`asset_ref`** (KHÁC `getAssetIncidentHistory` dùng `asset`). Live-sig parity: `inspect.signature(imm09.get_asset_repair_history).parameters == {asset_ref, limit}`.
- Handler @`:128` = **`return handle(svc.get_asset_history, asset_ref, limit=int(limit))`** — **0 nhánh `_err` in-handler** (KHÔNG `try/except`; chỉ `handle()` wrap).

### `svc.get_asset_history` (`services/imm09.py:1212-1220`)
- `RepairRepo.list(filters={"asset_ref": asset_ref, "docstatus": 1}, fields=[9], order_by="open_datetime desc", page_size=int(limit))` @`:1213-1218` — chỉ phiếu **submitted** (`docstatus=1`), KHÔNG pagination (chỉ `page_size` = limit cap).
- `return {"asset_ref": asset_ref, "history": history}` @`:1220` — **rows-key `history`** + **asset-key `asset_ref`** (KHÁC incident `{asset, items}`). Svc **KHÔNG raise `ServiceError`** (0 validate-guard; asset∄ → `history=[]`, KHÔNG lỗi).
- 9 field GROUNDED `fields=[...]` @`:1215-1216`: `name`, `repair_type`, `priority`, `open_datetime`, `completion_datetime`, `mttr_hours`, `sla_breached`, `root_cause_category`, `repair_summary`.

### `handle()` envelope (`utils/api_handler.py:33-51`)
- `handle(fn, ...)` = `try: return _ok(fn(...)) except ServiceError: return _err(...)` @`:48-51`. **CHỈ bắt `ServiceError`** — non-ServiceError bubble → 500 (NGOÀI 3-shape). Vì `get_asset_history` **0 raise `ServiceError`** ⇒ `handle` **LUÔN `_ok`** ⇒ **200 = SINGLE success envelope** (KHÔNG có Error branch trên HTTP-200).

### DocType `Asset Repair` (`asset_repair.json`)
- `sla_breached` = **Check** (0/1) — bit-flag vi-phạm SLA. ⇒ wire `integer` (KHÔNG `boolean`), né int-vs-bool trap Open#1.
- `mttr_hours` = **Float** ⇒ `number`. `open_datetime`/`completion_datetime` = **Datetime** ⇒ wire `string` `'yyyy-MM-dd HH:mm:ss'` (naive, KHÔNG `format:date-time`).

## Decision

**Bồi 1 path GET (`getAssetRepairHistory`) GROUNDED 1:1 `imm09.get_asset_repair_history`, +2 schema RIÊNG, response slot `{200,401,403}`, 200 = SINGLE-shape.** Tag `repair` (domain IMM-09, mirror `getRepairWorkOrder`/`listRepairWorkOrders` — KHÔNG có tag `mobile` trong spec). Path-count **51→52**, opId **51→52** (đếm thật `grep -cE '^\s{2}/'` = 52). CONTRACT-ONLY (pure-yaml).

1. **`getAssetRepairHistory`** — `GET /api/method/assetcore.api.imm09.get_asset_repair_history` › `operationId: getAssetRepairHistory` (dotted-tail == opId, camelCase, UNIQUE). 2 param: `asset_ref` (query, **required**, string) + `limit` (query, optional, integer, default 10). KHÔNG `requestBody` (GET). **200 = `$ref AssetRepairHistoryEnvelope` SINGLE** (KHÔNG `oneOf [Env, Error]` — handler 0 `_err`, svc 0 `ServiceError`; mirror `listTransfers`/`pingSession`). slot `{200,401,403}`: `401 = Unauthorized401` · `403 = Forbidden` SINGLE-SHAPE (dispatcher-403 guest/no-token — bare `@whitelist` KHÔNG `allow_guest`).

2. **`AssetRepairHistoryEnvelope`** — closed (`additionalProperties:false`), `required [success, data]`; `success.enum [true]`; `data` = closed object `required [asset_ref, history]` — **rows-key `history`** + **asset-key `asset_ref`** (KHÁC `AssetIncidentHistoryEnvelope.data.required[asset, items]`). KHÔNG `pagination` (svc chỉ limit cap). `history` = array of `$ref AssetRepairHistoryItem`.

3. **`AssetRepairHistoryItem`** — closed (`additionalProperties:false`), `required` EXACT `[name]` (PK; field khác optional). **EXACT 9 field GROUNDED** `RepairRepo.list fields` @`:1215-1216`: `name` (string PK) · `repair_type` (string Select) · `priority` (string Select) · `open_datetime` (string, KHÔNG `format:date-time`) · `completion_datetime` (string nullable, KHÔNG `format:date-time`) · `mttr_hours` (number nullable) · **`sla_breached` (integer — Check 0/1, KHÔNG boolean/enum[0,1])** · `root_cause_category` (string) · `repair_summary` (string). **1 Check field** ⇒ né int-vs-bool trap (KHÁC `AssetIncidentHistoryItem` 0 Check).

**Phạm vi membership-set (test_mobile_oas):** 1 path **∈ `_MVP_BUSINESS_PATHS`** (bare `@whitelist` ⇒ 401/403 symmetry +1) · **∉ `_MVP_READ_ENVELOPE`** (SINGLE-shape, KHÔNG oneOf read-envelope) · **∉ `_DETAIL_OPID`** (list-history, KHÔNG single-detail) · **∉ `_AUTH_PATHS` / `_ALLOW_GUEST_PATHS`**. **CONTRACT-ONLY**: `git diff HEAD -- api/imm09.py + services/imm09.py` phần `get_asset_repair_history`/`get_asset_history` = **TRỐNG** ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO] thật, né HARD-STOP USER). 51 path hiện-hữu **byte-identical**; `d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | KHÔNG wire, app dùng `getAssetIncidentHistory` cho cả CM | SAI domain — `getAssetIncidentHistory` đọc `Incident Report` (sự-cố), KHÔNG phải `Asset Repair` (phiếu CM). Tab "Lịch sử sửa chữa" đứt mạch. Endpoint LIVE @source, bồi contract = codegen-ready ngay. |
| B | Reuse `AssetIncidentHistoryEnvelope`/`AssetIncidentHistoryItem` | Field-set THẬT KHÁC (Asset Repair ≠ Incident Report) + rows-key `history`≠`items` + asset-key `asset_ref`≠`asset` + svc shape KHÁC. Reuse = contract nói dối shape → strict-codegen deser drop/CRASH. C3-split: `*Envelope`/`*Item` RIÊNG (precedent ADR-MOBILE-009). |
| C | 200 = `oneOf [AssetRepairHistoryEnvelope, Error]` (mirror `getAssetIncidentHistory` R28) | Handler `get_asset_repair_history` @`:128` = `handle(svc.get_asset_history)`; svc @`:1212-1220` **0 raise `ServiceError`** ⇒ `handle` LUÔN `_ok` (`api_handler.py:48-51` chỉ bắt `ServiceError`) ⇒ 0 Error branch trên HTTP-200. Khai `oneOf` = claim error-mode không tồn tại + ép codegen route-by-VALUE thừa. SINGLE-shape source-faithful (mirror `listTransfers` ADR-MOBILE-021). |
| D | `sla_breached` = `boolean` (đọc tự-nhiên "đã vi phạm?") | Frappe Check wire **0/1 (int)** KHÔNG `true/false`. Strict-codegen Dart/Kotlin deser `bool` từ `0`/`1` → CRASH (Open#1). `integer` faithful; KHÔNG `enum[0,1]` (GENUINE Check int, KHÔNG enum-bound — mirror `measurement_count`). |
| E | `open_datetime`/`completion_datetime` = `string format:date-time` | Frappe Datetime wire **naive** `'yyyy-MM-dd HH:mm:ss'` (KHÔNG ISO-8601 `Z`/offset). `format:date-time` ⇒ strict parser reject naive → deser fail. `string` no-format faithful (mirror `occurred_datetime` R35). |
| F | Param tên `asset` (mirror `getAssetIncidentHistory`) | Signature THẬT `get_asset_repair_history(asset_ref, ...)` @`:127` dùng **`asset_ref`**. Khai `asset` = drift contract↔source → codegen sinh query-key sai → handler nhận `asset_ref=None` → empty. `asset_ref` live-sig parity. |
| ✅ G | 1 path GET, 2 schema RIÊNG, SINGLE-200, rows-key `history`/asset-key `asset_ref`, `sla_breached` integer, slot `{200,401,403}` | Grounded 1:1 source; blast-radius = +1 path +2 schema (PURE-YAML); codegen sinh `getAssetRepairHistory()` đúng shape; SINGLE vs oneOf phản-ánh đúng KHÔNG có `_err` in-handler; 3 khác-biệt vs incident đều có source-evidence. |

## Consequences

- **(+)** Hành-trình field-tech "quét QR → hồ-sơ thiết bị" ĐÓNG **bộ-ba** read-history: sự-cố (`getAssetIncidentHistory`) + vòng-đời (`getAssetTimeline`) + **sửa-chữa CM (`getAssetRepairHistory`)**. KTV thấy MTTR/SLA-breach ngay tại máy.
- **(+)** Contract GROUNDED 1:1 source — SINGLE-200 (handler 0 `_err`, svc 0 `ServiceError`) mirror `listTransfers`; live-sig parity `{asset_ref, limit}` chống drift; 9 field grounded `RepairRepo.list`; `sla_breached integer`/`mttr_hours number`/dates `string` no-date-time né mọi codegen-deser trap.
- **(+)** **CONTRACT-ONLY** — `git diff` api/imm09.py + services/imm09.py phần `get_asset_repair_history`/`get_asset_history` = TRỐNG ⇒ KHÔNG reload gunicorn, KHÔNG migrate; `test_oas_generator`/`d12`/`d15`/`d17` UNCHANGED (pure mobile-yaml). 51 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator); 0 dangling `$ref` (2 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`). `history[]` RỖNG hợp lệ (asset chưa sửa) → KHÔNG 404.
- **(−)** **3 KHÁC-BIỆT có-chủ-đích vs `getAssetIncidentHistory`** (rows-key `history`, asset-key `asset_ref`, SINGLE-shape) — codegen sinh 2 model riêng (KHÔNG share `AssetIncidentHistoryItem`); đây là phản-ánh ĐÚNG source shape, KHÔNG phải duplication thừa.
- **(−)** `getAssetRepairHistory` là META-read (lịch-sử CM), **KHÔNG tự sinh Lifecycle Event** (read-only — event sinh ở mutation `closeWorkOrder`/`confirmInspection`, KHÔNG ở read; CLAUDE.md §10).
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `483→492` (test_mobile_oas) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `483→492` + `_GUARD_SUITE_SUM` `626→635` + `_MOBILE_OAS_TOTAL` `652→661` (test_mobile_docset) + ~45 site path/opId `51→52` + transfer backward-compat `49→50` — TẤT-CẢ đã đồng-bộ round này.

---

## Đã thực thi (Bước-4 ATOMIC — round BA này)

> CONTRACT-ONLY — KHÔNG đụng `api/*.py`/`services/*.py`. `bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_oas` + `test_mobile_docset` GREEN.

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`):
- +1 path `/api/method/assetcore.api.imm09.get_asset_repair_history` (GET, opId `getAssetRepairHistory`, tag `repair`); 2 param `asset_ref` (req) + `limit` (opt int default 10); 200 = `$ref AssetRepairHistoryEnvelope` SINGLE; slot `{200,401,403}` (`401 Unauthorized401`, `403 Forbidden`).
- +2 schema `AssetRepairHistoryEnvelope` (closed, `data.{asset_ref, history[]}`, success enum[true]) + `AssetRepairHistoryItem` (closed, 9 prop, req `[name]`, `sla_breached integer`, dates `string` no-`format`).
- Tái-dùng (KHÔNG tạo mới): `Unauthorized401`, `Forbidden`. 0 orphan.

**(2) test_mobile_oas.py**: path/opId count `51→52` (~45 site) + transfer backward-compat `49→50` + roadmap regex `r"51 path"→r"52 path"`; +`_ASSET_REPAIR_HISTORY_*` constants + opId convention map + `_MVP_BUSINESS_PATHS` (+`_ASSET_REPAIR_HISTORY_PATH`); +1 TC class `TestMobileGetAssetRepairHistoryContract` (a..i, 9 TC: GET-only/opId/MVP/count · 2-param `asset_ref`-not-`asset` · SINGLE-200-not-oneOf · envelope `history`/`asset_ref` no-pagination · item EXACT-9 · int-bool-trap · 401 slot · 403 single-shape + symmetry + no-dangling · live-sig parity); `_EXPECTED_TEST_COUNT` `483→492`.

**(3) test_mobile_docset.py**: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `483→492` · `_GUARD_SUITE_SUM` `626→635` · `_MOBILE_OAS_TOTAL` `652→661` · transition `repair_history_delta = 9` (TC-09 baseline 191 GIỮ).

**(4) docs narrative**: `04-api-contract.md` (FLOW-2 device-profile repair-history) + `13-be-completion-roadmap.md` (51→52 path) + README ADR-row (ADR-MOBILE-022).

**BACKLOG (vòng kế):** wire `getAssetCalibrationHistory` (nếu có endpoint LIVE) để ĐÓNG bộ-tứ device-profile read-history (sự-cố + vòng-đời + CM + hiệu-chuẩn).
