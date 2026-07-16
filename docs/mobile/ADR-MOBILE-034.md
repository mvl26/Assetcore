# ADR-MOBILE-034 — `resolveQrToken` + `getAssetScanInfo` typed-query-param (**CR-05 · typed-query-param** — chuyển `?token=`/`?name=` từ prose-only sang query param CÓ KIỂU trong OAS mirror để codegen phơi tham số typed, bỏ `axios options.params` cast; **PARAMS-ONLY** — 0 schema drift, 0 path/opId mới, 200-shape GIỮ NGUYÊN; **required:false** giữ OR-resolve semantics)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-034 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-12 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator — 200-shape 2 path NÀY KHÔNG đổi) · **§8.7 R4 typed reads** (`resolveQrToken`/`getAssetScanInfo`/`getAsset` rời STUB, typed `data`) · precedent param typed: `getAsset` `parameters:[AssetName]` (`name` required) + `getAssetIncidentHistory` `parameters:[asset,limit]` (asset required + limit optional) · Core Doc IMM-00 [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §III.3 (endpoint scan/resolve) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (introspect argspec @2026-07-12): handler `assetcore/api/imm00.py` `resolve_qr_token` def@**605** (`@frappe.whitelist()` @603 + `@rate_limit(...)` @604 no-`allow_guest`/no-`methods=POST` → **GET**; **signature `resolve_qr_token(token: str = "")`** — **1 param `token`, default `""`**; `rbac.require("asset.read")` → PermissionError dispatcher-403; token rỗng/không khớp → `_err(_ERR_ASSET_NOT_FOUND, 404)` leak-safe; vendor-IDOR → `ServiceError(FORBIDDEN)` caught → `_err`) · `get_asset_scan_info` def@**648** (`@frappe.whitelist()` @646 + `@rate_limit(...)` @647; **signature `get_asset_scan_info(token: str = "", name: str = "")`** — **2 param `token`+`name`, cả hai default `""`**; **OR-resolve** — nhánh `if token: … elif name and frappe.db.exists(...)` → asset_name hoặc None (404 no-leak); rbac + vendor-IDOR y hệt `resolve_qr_token`). Introspect: `inspect.signature(imm00.resolve_qr_token).parameters == {token}` · `... get_asset_scan_info ... == {token, name}`. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (2 path `parameters:` block). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§C6 read-path · CR-05 note). Nguồn yêu cầu: [`assetcore-mobile/docs/api/CONTRACT-REQUESTS.md`](../../../../../assetcore-mobile/docs/api/CONTRACT-REQUESTS.md) CR-05.

---

## Context

`resolveQrToken` (`/a/<token>` → định danh asset) và `getAssetScanInfo` (màn hồ-sơ mobile-first sau quét QR) nhận tham số qua **query string** (`?token=<...>` và, với scan-info, thêm `?name=<...>`). TRƯỚC vòng NÀY 2 tham số CHỈ được mô tả trong prose `description` của path (verbatim `GET ?token=<...> HOẶC ?name=<...>`) — path block **KHÔNG có khối `parameters:`**.

Hệ quả contract-gap (CR-05, phát hiện live khi đóng vai CORE-DEV sinh client):
- Generated `typescript-axios` **KHÔNG sinh tham số query typed** cho 2 operation ⇒ CORE-DEV phải truyền `token`/`name` qua **`axios request options.params` cast thủ công** (mất type-safety, dễ sai tên param, gọi axios "mò" ngoài generated client).
- `getAsset` (ADR-MODULE-1) đã được bồi `parameters:[AssetName]` nên KHÔNG dính gap; `getAssetIncidentHistory`/`listAssets`/`getAssetTimeline` curate `parameters:` đầy đủ từ đầu. CHỈ CÒN 2 path scan-QR NÀY prose-only.

Ràng buộc quyết định:
1. **OR-resolve semantics** (backend, `imm00.py:648`): `get_asset_scan_info` resolve theo `token` **HOẶC** `name` — CẢ HAI optional (default `""`), rơi 404 no-leak nếu cả hai rỗng/không khớp. `resolve_qr_token` cũng có `token` default `""` (rỗng → 404). ⇒ **KHÔNG được** đánh dấu bất kỳ param nào `required:true` (sẽ phá lane resolve kia + phá chữ-ký backend LIVE).
2. **CONTRACT-ONLY**: handler + service ĐÃ LIVE @source — thay đổi CHỈ ở OAS mirror (documentation/contract), **KHÔNG đụng `.py`, KHÔNG reload worker, KHÔNG migrate**.
3. **KHÔNG drift 200-shape**: 2 path giữ `oneOf [<Envelope>, Error]` closed-schema Decision-B (ADR-001) — thay đổi params KHÔNG được chạm response/schema/path/opId.

## Decision

Bồi khối `parameters:` TYPED cho 2 path scan-QR, khai đúng chữ-ký backend LIVE (introspect argspec), TẤT CẢ `required:false`:

### `resolveQrToken` — `parameters: [token]`
- **`token`**: `in:query`, `required:false`, `schema.type:string`. `description` = verbatim dòng đầu docstring `resolve_qr_token` (`GET — A2 (ADR-001 D4): tra mã QR (deep-link /a/<token>) → định danh asset`) + line-ref `imm00.py:605` + ghi chú backend default `""` → 404 leak-safe ⇒ `required:false`.

### `getAssetScanInfo` — `parameters: [token, name]`
- **`token`**: `in:query`, `required:false`, `schema.type:string`. `description` verbatim docstring `get_asset_scan_info` OR-resolve line (`Resolve theo token (deep-link QR) HOẶC name (điều hướng nội bộ list/desktop)`) + line-ref `imm00.py:648`.
- **`name`**: `in:query`, `required:false`, `schema.type:string`. Fallback khi KHÔNG có `token` (điều hướng nội bộ `/assets/:id/info`) + line-ref `imm00.py:648`.

### Invariant contract (guard `TestMobileScanQrTypedParams` a..e, `test_mobile_oas`)
- **TC-a** `resolveQrToken` ĐÚNG 1 param `{token}` (in:query, required:false, string).
- **TC-b** `getAssetScanInfo` ĐÚNG 2 param `{token,name}` (cả hai in:query, required:false, string).
- **TC-c** TẤT CẢ 3 param `required:false` (0 param `required:true` — OR-resolve).
- **TC-d** param khai **== chữ-ký backend LIVE** (introspect `inspect.signature`) — 0 bịa, 0 thiếu: `resolve_qr_token=={token}` / `get_asset_scan_info=={token,name}`.
- **TC-e** 200-shape `oneOf [<Envelope>, Error]` closed GIỮ NGUYÊN (params-only regression guard).
- **RED-before/GREEN-after** chứng minh trên TC-a/TC-c: `parameters` key vắng (prose-only) → RED; có → GREEN.

## Alternatives

| Phương án | Vì sao LOẠI |
|---|---|
| **A. Giữ prose-only** (không bồi `parameters:`) | Không đóng CR-05 — CORE-DEV vẫn phải cast `axios options.params` thủ công, mất type-safety. |
| **B. Đánh dấu `token`/`name` `required:true`** | PHÁ OR-resolve (resolve theo token HOẶC name; `required:true` 1 lane buộc client luôn gửi lane đó) + LỆCH chữ-ký backend LIVE (default `""`). LOẠI cứng. |
| **C. Gộp thành 1 param `id`** hoặc đổi path `/scan/{token}` (path-param) | Đổi contract/opId/shape — KHÔNG params-only; RPC Frappe KHÔNG dùng path-template (endpoint dotted-path). LOẠI. |
| **D. Bồi qua `$ref components/parameters`** (như `AssetName`) | 2 param NÀY chỉ dùng 1 chỗ (không tái sử dụng) — inline params đủ + mirror `getAssetIncidentHistory` inline (`asset`/`limit`). Không cần component mới. |

## Consequences

- **(+)** Codegen `typescript-axios` phơi `token`/`name` typed ⇒ CORE-DEV bỏ `axios options.params` cast, có type-safety + tên param đúng.
- **(+)** Params khai == chữ-ký backend LIVE (TC-d introspect) ⇒ contract trung thực @source, chống drift bịa param.
- **(+)** PARAMS-ONLY: path-count 65 GIỮ, opId 65 GIỮ, c5 54 GIỮ, 200-shape/schema/`additionalProperties:false` GIỮ NGUYÊN ⇒ baseline closed-schema sweep + path-count guard + d12/d15/d17 KHÔNG đỏ.
- **(−/đánh đổi)** `required:false` cả 3 param ⇒ codegen sinh param optional — client CÓ THỂ gọi thiếu cả hai (backend trả 404 no-leak, đã có nhánh Error 200-oneOf); đây là hành vi ĐÚNG theo OR-resolve (KHÔNG phải khiếm khuyết).
- **(0)** CONTRACT-ONLY: 0 đụng `.py`, 0 reload worker, 0 migrate. Test: `test_mobile_oas` 601→**606** (+5 TC) · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 601→606 / `_GUARD_SUITE_SUM` 744→749 / `_MOBILE_OAS_TOTAL` 770→775 + transition-baseline `scanqr_typed_params_delta=5`.

### Naming guard (∅)
Không thêm schema/component mới ⇒ 0 va chạm tên. Param inline (`token`/`name`) không đăng ký `components/parameters` — không đụng `AssetName`/`AssetParent`/… hiện có.

## Handoff CORE-DEV (native repo — ngoài `assetcore`)

Sau khi regenerate client từ OAS mirror: `resolveQrToken(token?: string)` + `getAssetScanInfo(token?: string, name?: string)` phơi param typed. GỠ mọi `axios request options.params` cast thủ công cho 2 operation NÀY. Giữ OR-resolve: gọi `getAssetScanInfo({ token })` (deep-link QR) HOẶC `getAssetScanInfo({ name })` (điều hướng nội bộ) — KHÔNG bắt buộc cả hai.
