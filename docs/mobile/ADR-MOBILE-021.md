# ADR-MOBILE-021 — `listTransfers` + `getTransfer` (TRANSFER-READ-WIRE — bồi 2 path READ điều chuyển IMM-13/imm00 vào mobile contract, Đợt-2) — contract GROUNDED 1:1 endpoint LIVE `imm00.list_transfers` / `imm00.get_transfer`

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-021 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-29 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-009** (C3-split cross-domain — `*Envelope`/`*Item` RIÊNG khi field-set THẬT khác) · **ADR-MOBILE-001 (d)/(f)/(g)** (OpenAPI = hợp đồng máy-đọc; closed-schema Decision-B KHÔNG discriminator) · **C6-DETAIL** (`getIncident`/`getCalibration` precedent 200 = oneOf [Detail-Env, Error]) · **C7** (`IncidentListEnvelope` items-key + closed envelope) · Core Doc IMM-13 [`05_API_Specification.md §7`](../imm-13/05_API_Specification.md) + Core Doc IMM-00 [`ADR-IMM00-OPENAPI.md`](../imm-00/ADR-IMM00-OPENAPI.md) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm00.py:2047-2085`, `assetcore/assetcore/doctype/asset_transfer/asset_transfer.json`, `assetcore/tests/test_mobile_oas.py`, `assetcore/tests/test_mobile_docset.py`). Contract narrative (Bước-4 bồi): [`04-api-contract.md` §8.27](./04-api-contract.md) + MÀN↔API [`05-personas-mvp.md §3`](./05-personas-mvp.md). Narrative roadmap: [`13-be-completion-roadmap.md`](./13-be-completion-roadmap.md).

---

## Context

Mobile MVP (field-tech) đã có chuỗi quét-QR → hồ-sơ thiết bị (`getAssetScanInfo`/`getAssetDetail`/`getAssetTimeline`/`getAssetIncidentHistory`) + 4 work-order domain (PM/CM/Calibration/Incident). **Còn THIẾU** read-surface cho nghiệp-vụ **điều chuyển / bàn-giao thiết bị** (IMM-13) — KTV/Trưởng-khoa cần xem **danh-sách phiếu điều chuyển** + **chi-tiết 1 phiếu** trên app (theo dõi trạng-thái duyệt, nhận bàn-giao) mà chưa có path nào trong mobile contract.

**Phân-biệt namespace (ghi rõ chống nhầm):** đề-mục IMM-13 trong Core Doc (`docs/imm-13/`) đặc-tả luồng **Reassignment (RAS-...)** Đợt-3 *chưa scaffold* (`assetcore.api.imm13.*` — `05_API_Specification.md §1`). Tuy nhiên cơ-chế điều-chuyển **ĐANG LIVE** lại nằm ở **`assetcore.api.imm00.*`** trên DocType **`Asset Transfer`** (naming `AT-.YYYY.-.####`) — 6 endpoint (`list_transfers`/`get_transfer`/`create_transfer`/`delete_transfer`/`approve_transfer`/`reject_transfer`/`receive_transfer`). Vòng này wire **2 endpoint READ LIVE** (`list_transfers` + `get_transfer`) — KHÔNG đụng luồng RAS Đợt-3.

Endpoint nguồn **ĐÃ LIVE** (CONTRACT-ONLY): `imm00.list_transfers` (`api/imm00.py:2047-2077`) + `imm00.get_transfer` (`api/imm00.py:2080-2085`). Vòng này **bồi 2 path GET** vào mobile yaml để codegen sinh client; **KHÔNG đụng `.py`** (KHÔNG reload gunicorn, KHÔNG migrate).

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `list_transfers` (`imm00.py:2047-2077`)
- `@frappe.whitelist()` @`:2047` — **bare** (KHÔNG `allow_guest`) ⇒ guest/no-token → **dispatcher-403** (`PermissionError`, `is_whitelisted`); bearer hết-hạn → **401** (`AuthenticationError`). ⇒ response slot `{200,401,403}` (mirror `listAssets`/`listNotifications`, KHÁC `getUserContext` allow_guest).
- `def list_transfers(asset=None, status=None, page=1, page_size=20)` @`:2048-2049` — **4 param DISCRETE query-string** (KHÔNG JSON `filters`; mirror `listAssets`/`listUsers` discrete, KHÁC `list_pm`/`list_repair`/`list_calibrations` JSON-blob). Live-sig parity: `inspect.signature(imm00.list_transfers).parameters == {asset, status, page, page_size}`.
- Handler @`:2051-2077` **LUÔN `return _ok({"pagination": pag, "items": items})`** @`:2077` — **0 nhánh `_err` in-handler** (KHÔNG `try/except`; `int(page)`/`db.count`/`get_list` lỗi → **500 NGOÀI 3-shape**). ⇒ **200 = SINGLE schema `TransferListEnvelope` (KHÔNG oneOf [Env, Error])** — KHÁC `IncidentList`/`AssetList`/`UserList`/`NotificationList` (đều `oneOf [Env, Error]` vì handler tương-ứng CÓ in-handler `_err`).
- rows-key = **`data.items[]`** (mirror `IncidentListEnvelope`/`AssetListEnvelope`, KHÁC `Pm/RepairWorkOrderListEnvelope` `data.data[]`) + `data.pagination` ($ref `Pagination` 5-key qua `paginate()` @`:2058`).
- Element = 16 repo-field (`fields=[...]` @`:2062-2065`) + `asset_name` enrich (@`:2070-2076`) = **17 field**. **0 Check/boolean field** ⇒ 0 prop `integer enum[0,1]` (int-vs-bool trap né sẵn).

### `get_transfer` (`imm00.py:2080-2085`)
- `@frappe.whitelist()` @`:2080` — **bare** ⇒ slot `{200,401,403}` như trên.
- `def get_transfer(name)` @`:2081` — **1 param** `name` (query, required). Live-sig parity: `inspect.signature(imm00.get_transfer).parameters == {name}`.
- Handler @`:2083-2085`: `if not frappe.db.exists(_DT_TRANSFER, name): return _err(_ERR_TRANSFER_NOT_FOUND, 404)` @`:2084` (Error trên **HTTP-200** quirk §5) ELSE `return _ok(frappe.get_doc(_DT_TRANSFER, name).as_dict())` @`:2085`. ⇒ **200 = oneOf [`TransferDetailEnvelope`, `Error`]** closed-schema route-by-VALUE 0-discriminator (mirror `getIncident`/`getCalibration` C6). `Error.http_status` ⊇ `{404}` (đã có trong enum component `Error`).

### DocType `Asset Transfer` (`asset_transfer.json`)
- `is_submittable: 0` (KHÔNG docstatus-flow) · `track_changes: 1` · naming `AT-.YYYY.-.####`.
- `status` = Select `Pending Approval\nApproved\nRejected\nReceived\nCancelled` @`:89` (read_only, default `Pending Approval`) — **enum SSoT verify @source, KHÔNG bịa**.
- `transfer_type` = Select `Internal\nLoan\nExternal\nReturn` @`:77`.

## Decision

**Bồi 2 path GET (`listTransfers` + `getTransfer`) GROUNDED 1:1 `imm00.list_transfers`/`get_transfer`, +4 schema RIÊNG, response slot `{200,401,403}`.** Tag mới `transfer`. Path-count **49→51**, opId **49→51** (đếm thật `len(spec.paths)`). CONTRACT-ONLY (pure-yaml).

1. **`listTransfers`** — `GET /api/method/assetcore.api.imm00.list_transfers` › `operationId: listTransfers` (dotted-tail == opId, camelCase, UNIQUE). 4 param DISCRETE query (`asset?` string · `status?` string · `page?` int default 1 · `page_size?` int default 20). **200 = `$ref TransferListEnvelope` SINGLE** (KHÔNG `oneOf [Env, Error]` — handler LUÔN `_ok`, 0 `_err`). slot `{200,401,403}`: `401 = Unauthorized401` (FrappeRawError) · `403 = Forbidden` SINGLE-SHAPE (FrappeRawError, dispatcher-403 guest/no-token — bare `@whitelist` KHÔNG `allow_guest`).

2. **`getTransfer`** — `GET /api/method/assetcore.api.imm00.get_transfer` › `operationId: getTransfer`. 1 param `name` (query, required, string). **200 = oneOf [`TransferDetailEnvelope`, `Error`]** closed route-by-VALUE 0-discriminator (`get_transfer` 404 `_err` @`:2084` → Error@HTTP-200). slot `{200,401,403}`, `Error.http_status` ⊇ `{404}`.

3. **`TransferListItem`** — closed (`additionalProperties:false`), `required` EXACT `[name]` (PK; field khác optional — service trả `""`). **17 field GROUNDED** `fields=[...]` @`:2062-2065` + `asset_name` enrich @`:2070-2076`: `name` (string, `AT-2026-0001`) · `asset` (string, Link AC Asset) · `asset_name` (string, enrich) · `transfer_date` (string `format:date`) · `transfer_type` (string enum `[Internal, Loan, External, Return]` @`asset_transfer.json:77`) · `status` (string enum `[Pending Approval, Approved, Rejected, Received, Cancelled]` @`:89`) · `from_location` · `to_location` (string, Link AC Location) · `from_department` · `to_department` (string, Link AC Department) · `from_custodian` · `to_custodian` (string, Link User) · `reason` (string, Small Text) · `approved_by` (string, Link User) · `approval_date` (string `format:date`) · `received_by` (string, Link User) · `received_date` (string `format:date`). **0 boolean** ⇒ 0 int-enum trap.

4. **`TransferListEnvelope`** — closed (`additionalProperties:false`), `required [success, data]`; `success.enum [true]`; `data` = closed object `required [pagination, items]` (`pagination` = `$ref Pagination`; `items` = array of `$ref TransferListItem`). Mirror `IncidentListEnvelope` rows-key `items`.

5. **`TransferDetail`** — **OPEN (`additionalProperties:true`)** = `doc.as_dict()` @`:2085` (mirror `IncidentDetail`/`CalibrationDetail` §3.2). Declared properties = **superset của `TransferListItem`** + field detail-only GROUNDED `asset_transfer.json`: `naming_series` · `expected_return_date` (date) · `notes` (text) · `rejected_by` (Link User) · `rejection_reason` (Small Text) · `handover_notes` (text) · `amended_from` (Link). `required [name]`.

6. **`TransferDetailEnvelope`** — closed (`additionalProperties:false`), `required [success, data]`; `success.enum [true]`; `data` = `$ref TransferDetail`. Mirror `IncidentDetailEnvelope` (envelope đóng disjoint vs `Error` trong 200-oneOf).

**Phạm vi membership-set (test_mobile_oas):** 2 path **∈ `_MVP_BUSINESS_PATHS`** (bare `@whitelist` ⇒ 401/403 symmetry +2) · `getTransfer` ∈ `_DETAIL_OPID` + `_MVP_READ_ENVELOPE` (oneOf read-envelope) · **`listTransfers` ∉ `_MVP_LIST_ENVELOPE`** nếu set đó assert `oneOf [Env, Error]` (listTransfers SINGLE-shape — cần TC RIÊNG assert 200 = single `$ref`, KHÔNG oneOf) — **xem delta Bước-4**. **∉ `_AUTH_PATHS` / `_ALLOW_GUEST_PATHS`**. **CONTRACT-ONLY**: `git diff HEAD -- api/imm00.py + services/imm00.py` phần transfer = **TRỐNG** ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO] thật, né HARD-STOP USER). 49 path hiện-hữu **byte-identical**; `d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | KHÔNG wire `listTransfers`/`getTransfer`, app dùng web cho điều chuyển | Hành-trình field-tech "nhận bàn-giao" đứt mạch trên app — KTV phải mở web để xem phiếu điều chuyển. Endpoint LIVE @source, bồi contract = codegen-ready ngay. |
| B | `listTransfers` 200 = `oneOf [TransferListEnvelope, Error]` (mirror IncidentList/AssetList) | Handler `list_transfers` @`:2051-2077` **KHÔNG `try/except`** ⇒ 0 nhánh `_err` in-handler. Khai `oneOf [Env, Error]` = contract nói dối (claim error-mode không tồn tại) + ép codegen route-by-VALUE thừa. SINGLE schema source-faithful (KHÁC `listAssets` có `except Exception` @source ⇒ oneOf). |
| C | **`TransferDetail` closed (`additionalProperties:false`)** — như chữ "closed superset" trong acceptance | **SAI** — `get_transfer` @`:2085` trả `doc.as_dict()` LUÔN kèm field meta Frappe (`owner`/`creation`/`modified`/`modified_by`/`docstatus`/`idx`/`doctype`/`parent*`) NGOÀI field DocType. Closed-schema chỉ liệt-kê field DocType ⇒ response THẬT mang key meta → **validate-FAIL / codegen deser drop**. Precedent §3.2: `IncidentDetail`/`CalibrationDetail` đều `additionalProperties:true` (OPEN). **[SELF-CORRECTION]** — "closed superset" reconcile = **ENVELOPE đóng** (`TransferDetailEnvelope`) + **Detail MỞ superset-by-declared-property** (mirror `getIncident`). Xem §Consequences. |
| D | Gộp `listTransfers`/`getTransfer` vào namespace `imm13.*` (theo Core Doc IMM-13 §1) | Endpoint LIVE nằm ở `imm00.*` trên DocType `Asset Transfer` — KHÔNG phải `imm13.reassignment` (RAS Đợt-3 chưa scaffold). Contract phải trỏ path THẬT `imm00.list_transfers`. Gộp = path không-tồn-tại → 404 runtime. |
| E | `transfer_type`/`status` để string tự-do (không enum) | Cả 2 là Select @`asset_transfer.json:77,89` — giá-trị bounded SSoT. Khai enum GROUNDED ⇒ codegen sinh enum-type tường minh (client validate được). KHÔNG bịa giá-trị ngoài source. |
| F | `getTransfer` slot `{200,401}` (no-403, mirror searchSpareParts/getUserContext) | `get_transfer` bare `@whitelist` KHÔNG `allow_guest` ⇒ guest/no-token = **dispatcher-403** (`PermissionError` HTTP-403). Bỏ 403 = bịa thiếu nhánh. slot `{200,401,403}` faithful (mirror `getIncident`/`getCalibration`). |
| ✅ G | 2 path GET, 4 schema RIÊNG, `listTransfers` SINGLE-200 + `getTransfer` oneOf-200, `TransferDetail` OPEN + envelope đóng, slot `{200,401,403}` | Grounded 1:1 source; blast-radius = +2 path +4 schema (PURE-YAML); codegen sinh `listTransfers()`/`getTransfer()` đúng shape; SINGLE vs oneOf phản-ánh đúng có/không `_err` in-handler. |

## Consequences

- **(+)** Hành-trình field-tech "theo-dõi điều-chuyển / nhận bàn-giao" (IMM-13 Đợt-2) ĐÓNG mạch read trên app: `listTransfers` (danh-sách phiếu, lọc `asset`/`status`) + `getTransfer` (chi-tiết 1 phiếu + chuỗi duyệt). Bổ-trợ chuỗi quét-QR → hồ-sơ thiết-bị.
- **(+)** Contract GROUNDED 1:1 source — `listTransfers` SINGLE-200 (handler LUÔN `_ok`, 0 `_err`) vs `getTransfer` oneOf-200 (404 `_err` @`:2084`); live-sig parity `{asset,status,page,page_size}` / `{name}` chống drift; `status`/`transfer_type` enum @`asset_transfer.json` chống bịa; 0 boolean → 0 int-vs-bool trap.
- **(+)** **CONTRACT-ONLY** — `git diff` api/imm00.py + services/imm00.py phần transfer = TRỐNG ⇒ KHÔNG reload gunicorn, KHÔNG migrate; `test_oas_generator`/`d12`/`d15`/`d17` UNCHANGED (pure mobile-yaml). 49 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator toàn file); 0 dangling `$ref` (4 schema mới `$ref` ngay + tái-dùng `Pagination`/`NotFound404`/`Unauthorized401`/`Forbidden`/`Error` đã defined).
- **(−)** **[SELF-CORRECTION đối-acceptance]** Acceptance ghi "`TransferDetail(+Envelope)` closed superset" — bồi **CHÍNH-XÁC** thành **`TransferDetailEnvelope` đóng + `TransferDetail` MỞ** (Alternative C): `doc.as_dict()` mang field meta Frappe ngoài DocType ⇒ Detail closed sẽ validate-fail. "Closed" áp ENVELOPE (như `IncidentDetailEnvelope`), Detail mở superset-by-property (như `IncidentDetail` §3.2).
- **(−)** **[SELF-CORRECTION số-liệu test]** Acceptance ghi `_EXPECTED_TEST_COUNT:186` — **STALE**; hằng-số THẬT @`test_mobile_oas.py:186` = **`467`** (bump = `467 + N_TC_mới`). Acceptance ghi "cập nhật 49→51 tại `1791/1802/1810`" — **THIẾU**: có **~25 site** assert path/opId == `49` trong `test_mobile_oas.py` (xem delta) + `test_mobile_docset` (`_GUARD_SUITE_EXPECTED` transition + `_GUARD_SUITE_SUM` + `_MOBILE_OAS_TOTAL`). TẤT-CẢ phải đồng-bộ — KHÔNG chỉ 3 dòng.
- **(−)** `listTransfers`/`getTransfer` là META-read (theo-dõi phiếu điều-chuyển), **KHÔNG tự sinh Lifecycle Event** (read-only — event sinh ở `approve`/`receive` mutation, KHÔNG ở read; CLAUDE.md §10).

---

## RED-before (Bước-4 BE-dev chứng minh — execution delta)

> ADR chốt thiết-kế; BE-dev (Bước-4) thực-thi yaml + test ATOMIC rồi `bench --site miyano run-tests test_mobile_oas test_mobile_docset` GREEN. **CONTRACT-ONLY — KHÔNG đụng `api/*.py`/`services/*.py`.**

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`):
- +2 path: `/api/method/assetcore.api.imm00.list_transfers` (GET, opId `listTransfers`, tag `transfer`) + `/api/method/assetcore.api.imm00.get_transfer` (GET, opId `getTransfer`, tag `transfer`).
- +4 schema: `TransferListItem` (closed, 17 prop, req `[name]`) · `TransferListEnvelope` (closed, `data.{pagination,items[]}`) · `TransferDetail` (OPEN, superset) · `TransferDetailEnvelope` (closed, `data=$ref TransferDetail`).
- `listTransfers` 200 = `$ref TransferListEnvelope` SINGLE; `getTransfer` 200 = `oneOf [TransferDetailEnvelope, Error]`; cả 2 slot `{200,401,403}` (`401 $ref Unauthorized401`, `403 $ref Forbidden`).
- Tái-dùng (KHÔNG tạo mới): `Pagination`, `Unauthorized401`, `Forbidden`, `Error`. 0 orphan.

**(2) test_mobile_oas.py**:
- **path/opId count `49→51`** tại MỌI site (grep `\b49\b` assert): `1791`, `1802`, `1810`, `3711`, `3757`, `3810`, `4292/94/95`, `4630/32/33`, `4918/20/21`, `7356/64/65`, `8392`, `9251/52`, `9803/04/05`, `10024/25/26`, `10244/45/46`, `10489/90/91`, `10702/03/04`, `10957/58/59`, `11175`, `11392/93/94`, `11598/99/600`, `11796`… (verify lại bằng grep — KHÔNG sót).
- `_MVP_BUSINESS_PATHS` (+`_LIST_TRANSFERS_PATH`, +`_GET_TRANSFER_PATH`) ⇒ 401/403 symmetry +2.
- `_DETAIL_OPID` (+`getTransfer`) · `_MVP_READ_ENVELOPE` (+`getTransfer` oneOf).
- `_MVP_LIST_ENVELOPE`: **KHÔNG thêm `listTransfers`** nếu set assert `oneOf [Env, Error]` — listTransfers SINGLE-shape ⇒ TC RIÊNG assert `200.content.schema` = single `$ref` (KHÔNG `oneOf`).
- `_LIST_PARAM_EXPECT[listTransfers] = {asset, status, page, page_size}` (discrete query, KHÔNG `$ref WorkOrderFilters`) + `_LIST_LIVE_FN[listTransfers] = ("assetcore.api.imm00", "list_transfers", {"asset","status","page","page_size"})`.
- +2 TC class: `TestMobileListTransfersContract` (a..i, SINGLE-200 + 17-field item + discrete param + live-sig) + `TestMobileGetTransferContract` (a..i, oneOf-200 + Detail-open + slot + live-sig). `_EXPECTED_TEST_COUNT` `467 → 467 + (#TC mới)`.

**(3) test_mobile_docset.py**: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `467→<new>` (+ transition-narrative entry) · `_GUARD_SUITE_SUM` · `_MOBILE_OAS_TOTAL` đồng-bộ delta. (ADR-021 + README ADR-row đã land round BA ⇒ TC-MOB-DOC-02 parity GIỮ.)

**(4) docs narrative** (BE-dev hoặc BA-follow): `04-api-contract.md` §8.27 (transfer read surface) + `05-personas-mvp.md §3` (Bước "điều chuyển / nhận bàn-giao" hành-trình field-tech) — đồng-bộ với yaml THẬT.

**BACKLOG (vòng kế — KHÔNG làm round này):** wire write-action điều-chuyển (`approveTransfer`/`rejectTransfer`/`receiveTransfer` POST @`imm00.py:2543/2552/2561`) để app đóng vòng "duyệt + nhận bàn-giao" (hiện chỉ READ). Mỗi cái slot `{200,401,403}` + response RIÊNG GROUNDED service return-shape.
