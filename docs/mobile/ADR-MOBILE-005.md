# ADR-MOBILE-005 — `listUsers` pagination 4-key (KHÔNG `offset`) — dedicated schema, KHÔNG `$ref Pagination`

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-005 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-16 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | Decision-B (closed-schema oneOf) · C3-split (field-disjoint element) · LL-BE-57 (mobile-meta no-financial) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/user.py`, `assetcore/services/shared/constants.py`, `assetcore/utils/pagination.py`). Contract: [`04-api-contract.md §6.3`](./04-api-contract.md).

---

## Context

Vòng 10 bồi path `listUsers` (`GET /api/method/assetcore.api.user.list_users`, opId `listUsers`) vào contract mobile để 2 form đóng required-field cụt: `createCalibration.technician` (Link User) + flow `assign_technician.technician` — picker KTV/assignee cần API liệt kê System User (lọc role/department/active).

Khi đặc tả `UserListEnvelope.data.pagination`, phát hiện **divergence wire-shape** so với 5 list path còn lại:

- 5/6 list path (`listPm*`/`listRepair*`/`listIncidents`/`listCalibrations`/`listAssets`) trả pagination qua `paginate()` (`utils/pagination.py:6`) ⇒ **5-key** `{page, page_size, total, total_pages, offset}`. Đây là shape của schema dùng chung `components/schemas/Pagination` (`required: [page, page_size, total, total_pages, offset]`).
- `user.list_users` **KHÔNG gọi `paginate()`** — build dict inline `api/user.py:368-373`, CHỈ **4 key** `{page, page_size, total, total_pages}` (KHÔNG `offset`; `total_pages = max(1, ceil(total/page_size))` — floor 1, KHÁC `paginate` =0 khi total=0).

Nếu `UserListEnvelope.data.pagination` `$ref` thẳng `Pagination` (cho "gọn"), codegen native (Dart/dio, Kotlin) sinh model có `offset` **required non-null**. Runtime trả body 4-key (không `offset`) ⇒ strict deserializer **crash** (missing required field) — đúng anti-pattern "in-handler 404/422 đến trên HTTP-200 KHÔNG status-line → codegen route sai" đã ghi memory `mobile_be_openapi_contract_gotchas.md`.

## Decision

`UserListEnvelope.data.pagination` dùng **DEDICATED sub-schema `UserListPagination`**:

- `type: object`, `additionalProperties: false`
- `properties`: `page`/`page_size`/`total`/`total_pages` (cả 4 `integer`)
- `required: [page, page_size, total, total_pages]` — **KHÔNG `offset`**

**KHÔNG `$ref components/schemas/Pagination`.** Khai đúng 4-key = nói SỰ THẬT wire-shape `list_users` ⇒ codegen sinh model deser được body runtime, không crash.

## Alternatives (đã loại)

1. **`$ref Pagination` (5-key) cho gọn** — LOẠI: buộc `offset` required → deser-crash khi body 4-key (sự cố câm). Vi phạm "contract nói đúng wire-shape".
2. **Sửa `user.list_users` gọi `paginate()` cho đồng nhất 5-key** — LOẠI round này: đụng `.py` BE (`api/user.py`) ⇒ cần reload gunicorn + risk regression web-FE đang tiêu thụ shape 4-key. Ràng buộc vòng 10 = pure-yaml, KHÔNG `.py`. → Forward-reserve Phase-E (normalize pagination toàn bộ list về `paginate()`).
3. **Để `offset` optional trong `Pagination`** — LOẠI: làm yếu hợp đồng cho 5 path kia (đang đúng 5-key); đổi schema dùng chung = lan rộng.

## Consequences

- (+) `listUsers` codegen-valid: client native deser body 4-key không crash.
- (+) Hợp đồng phản ánh ĐÚNG di sản 2 đường pagination (`paginate()` vs inline) — minh bạch cho integrator.
- (−) 2 shape pagination cùng tồn tại trong contract (`Pagination` 5-key + `UserListPagination` 4-key) — known-gap. Phase-E normalize `list_users` → `paginate()` rồi gộp về `Pagination`, **Supersede** ADR này.
- (−) `total_pages` floor-1 của `list_users` (=1 khi total=0) KHÁC `paginate` (=0). Client KHÔNG được suy "list rỗng" từ `total_pages==0` cho `listUsers`; dùng `len(items)==0` (đã ghi §6.3).

## Guard

`TestMobileListUsersContract` (`assetcore/tests/test_mobile_oas.py`, read-only yaml): `UserListPagination` 4-key + KHÔNG `offset` + `required`==4-key + `total_pages` floor-1 documented; `UserListEnvelope.data.pagination` `$ref UserListPagination` (KHÔNG `Pagination`). 0 đụng `.py`, KHÔNG reload/migrate.
