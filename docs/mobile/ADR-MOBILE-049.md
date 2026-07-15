# ADR-MOBILE-049 — `listAllocations` (`imm15.list_allocations`) curate vào OAS mirror (**CR-29a · MỞ NHÁNH IMM-15 F9 "Xuất kho phụ tùng phục vụ WO"** — bồi ĐÚNG 1 GET-list path trả danh sách phiếu cấp phát/xuất kho phụ tùng (IMM Spare Allocation) phục vụ Work Order, permission-aware, phân trang; LIST-ENTRY của màn F9; ⚠️ rows-key `data.data[]` **DOUBLE-DATA** (mirror PM/calib) — KHÁC `listCommissioning` `data.items[]`; 200 = oneOf `[Envelope, Error]` Decision-B; list-item MIỄN Check int-0/1)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-049 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-14 |
| Tác giả | BA (mobile contract curate) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; closed-schema oneOf, KHÔNG discriminator) · **sibling trực-tiếp**: **ADR-MOBILE-048** (`listCommissioning`) CÙNG shape paginated list-read qua response-component `oneOf [<ListEnvelope>, Error]`, NHƯNG rows-key KHÁC (`data.items[]` vs `data.data[]` của ADR này) · precedent double-data: `PmWorkOrderListEnvelope`/`CalibrationListEnvelope` (rows-key `data.data[]`) · Core Doc IMM-15 [`docs/imm-15/05_API_Specification.md §3.1`](../imm-15/05_API_Specification.md) + [`04-api-contract.md §6`](./04-api-contract.md) |

---

## 1. Bối cảnh

Màn **F9 "Xuất kho phụ tùng phục vụ WO"** là LIST-ENTRY tiêu thụ `imm15.list_allocations` để hiển thị
danh sách phiếu cấp phát/xuất kho phụ tùng (IMM Spare Allocation) phục vụ Work Order (PM/CM/Repair).
**IMM-15 CHƯA có endpoint nào curate** vào contract mirror (`assetcore-mobile.openapi.yaml`) → mobile
đang gọi raw `apiClient` (0 generated typed-client). Đây là op **MỞ NHÁNH IMM-15** (đầu tiên). Endpoint
**ĐÃ LIVE** ở web-BE. ADR này curate **contract-only** (0 `.py` runtime change / 0 reload / 0 migrate).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler `list_allocations` @`api/imm15.py:42` — `@frappe.whitelist()` **bare** (no `allow_guest`) → GET
  nhận; guest → dispatcher-403. Chữ ký `list_allocations(filters: str = "{}", page: int = 1, page_size:
  int = 20, workflow_state: str = "", asset: str = "", work_order_ref: str = "", urgency: str = "")` = **7
  param**. Thân: `_parse_json(filters)` trong `try/except ServiceError → _err` (malformed → 400
  INVALID_PARAMS TRÊN HTTP-200 @`:49-52`); 4 param discrete **merge lên filter dict** (`workflow_state →
  f["allocation_status"]` @`:54-55`; `asset` @`:56-57`; `work_order_ref` @`:58-59`; `urgency` @`:60-61`);
  rồi `_handle(svc.list_allocations, f, page=int(page), page_size=int(page_size))`.
- Service `list_allocations` @`services/imm15.py:206` — `AllocationRepo.list(filters=normalize_filters(f),
  fields=[...11 field...], order_by="requested_date desc, modified desc", page, page_size)` → `_enrich_display_names(rows, {...})` →
  **`return {"data": rows, "pagination": pg}`** → `_ok` ⇒ **rows-key `data.data[]` (DOUBLE-DATA**, mirror
  PM/calib, KHÁC Commissioning/Asset/Incident `data.items[]`).
- 11 field `AllocationRepo.list` @`services/imm15.py:210-212`: `name · work_order_ref · work_order_doctype ·
  asset · warehouse_from · requested_by · requested_date · urgency · allocation_status · total_value ·
  stock_movement_ref`.
- 3 enrich @`services/imm15.py:216-220` với out-field theo **special-case @`:189-196`** (KHÔNG đoán tên key):
  `asset → asset_name` (@`:189-190`) · `warehouse_from → **warehouse_name**` (@`:191-192`, KHÔNG
  `warehouse_from_name`) · `requested_by → requested_by_name` (@`:195-196`).
- DocType `imm_spare_allocation.json` — field-type grounding (bảng §3).

---

## 2. Quyết định

### (a) 200 = oneOf `[AllocationListEnvelope, Error]` — **Decision-B**

`list_allocations` chạy QUA `_handle(...)` VÀ handler có nhánh `_err` cho malformed `filters` (@`:49-52` →
INVALID_PARAMS). Lỗi đến TRÊN HTTP-200 với body `Error` ⇒ 200 = **oneOf** `[AllocationListEnvelope |
Error]` (KHÁC listTransfers/refdata SINGLE-shape). **KHÔNG raise HTTP-4xx** (không dùng `raise → HTTP-4xx`;
mọi lỗi nghiệp-vụ = in-handler HTTP-200 + Error envelope). Wire qua **response-component** `AllocationList`
(KHÔNG inline) — đối xứng `CommissioningList`/`PmWorkOrderList`. `Error.http_status` thực-tế ⊇ `{400
(malformed filters)}`.

### (b) ⚠️ rows-key `data.data[]` (DOUBLE-DATA) — điểm phân-biệt CỐT-LÕI

Service `return {"data": rows, "pagination": pg}` @`:221` → `_ok` bọc thêm 1 lớp `data` ⇒ envelope
`{success:true, data:{data:[…], pagination:{…}}}` — **DOUBLE-DATA**. Mirror `PmWorkOrderListEnvelope`/
`CalibrationListEnvelope` (di-sản service layer PM/calib). **KHÁC** `CommissioningListPage`/`AssetListEnvelope`
rows-key `data.items[]`. Bẫy copy-nhầm listCommissioning → guard TC c chốt: `AllocationListPage` set-keys
== `{data, pagination}` CHÍNH XÁC, assert `'items' ∉ keys`.

Envelope `AllocationListEnvelope = {success:[true], data: $ref AllocationListPage}`; `AllocationListPage =
{data: array<AllocationListItem>, pagination: $ref Pagination}`. REUSE component `Pagination` (@yaml:785) —
KHÔNG tạo mới.

### (c) `AllocationListItem` = **EXACT 14 property**, closed, `required:[name]`

11 field `AllocationRepo.list` + 3 enrich (`asset_name` · `warehouse_name` · `requested_by_name`).
`additionalProperties:false`. Chỉ `name` REQUIRED (PK naming-series `SAL-.YYYY.-.#####`); mọi field khác
optional (Option A closed-schema). 3 enrich key **ground-verbatim** từ special-case @`:189-196` — KHÔNG suy
tên (`warehouse_from → warehouse_name`, KHÔNG `warehouse_from_name`).

### (d) **List-item MIỄN Check int-0/1 (CR-01)**

`AllocationRepo.list.fields` = 11 field ∅ `Check` (0 property `type: boolean`); `total_value` = `Currency`
(`number`). ⇒ `AllocationListItem` MIỄN coercion `Number(x)===1` (CR-01 family). Guard TC b: `0 prop
type:boolean`.

### (e) tag mới `inventory`

Op-level `tags: [inventory]` (module-tag IMM-15 "Spare Parts Inventory" — parity, KHÔNG có top-level
`tags:` block trong mirror; đối xứng `[commissioning]`/`[calibration]`). Đây là op ĐẦU TIÊN mang tag
`inventory` (dành forward-reserve các endpoint IMM-15 kế: transfer/cycle-count).

### (f) 7 param typed **1:1 argspec** — 5 inline + 2 `$ref`

Params path = ĐÚNG 7, đúng thứ-tự argspec: `filters` (inline string JSON-passthrough, optional) · `$ref
Page` (page int) · `$ref PageSize` (page_size int) · `workflow_state` · `asset` · `work_order_ref` ·
`urgency` (4 inline string optional). REUSE `Page`/`PageSize` component (page/page_size int). 4 param discrete
là **override merge** lên filter dict (KHÔNG JSON-blob riêng như `CommissioningFilters`) — đúng cơ-chế
handler @`:54-61`. KHÔNG `mine`/`WorkOrderFilters`/`CommissioningFilters` (né lẫn sibling).

### (g) No-collision / naming-guard

Namespace `Allocation*` (schema `AllocationListItem`/`AllocationListPage`/`AllocationListEnvelope`, opId
`listAllocations`) DISJOINT với `Commissioning*`/`DueCalibration*` (khác endpoint, khác NGUỒN). Guard TC g:
`Allocation*` schema-family == ĐÚNG 3; `listAllocations`/`listCommissioning`/`getDueCalibrations` tồn tại
song song; codify tương-phản rows-key (`AllocationListPage.data` vs `CommissioningListPage.items`).

### (h) CONTRACT-ONLY

Backend `imm15.list_allocations` ĐÃ LIVE (`api/imm15.py:42` · `services/imm15.py:206`) → **0 `.py` runtime
change · 0 reload · 0 migrate**. Chỉ chạm YAML mirror + test guard + docs (ADR này). Guard TC f khẳng-định
live-signature parity: `inspect.signature(imm15.list_allocations)` == ĐÚNG 7 param (yaml KHÔNG bịa/sót).

---

## 3. `AllocationListItem` — type ĐÚNG từng field (GROUNDED `imm_spare_allocation.json`)

| # | property | nguồn | fieldtype | OpenAPI type | ghi chú |
|---|---|---|---|---|---|
| 1 | `name` | `AllocationRepo.list` | (autoname `SAL-.YYYY.-.#####`) | `string` | PK — **required** |
| 2 | `work_order_ref` | list `:210` | Dynamic Link (`work_order_doctype`) | `string` | WO liên kết |
| 3 | `work_order_doctype` | list `:210` | Select (IMM PM/CM WO · Asset Repair) | `string` | DocType của WO |
| 4 | `asset` | list `:210` | Link (AC Asset) | `string` | thiết bị |
| 5 | `warehouse_from` | list `:211` | Link (AC Warehouse) | `string` | kho xuất |
| 6 | `requested_by` | list `:211` | Link (User) | `string` | người yêu cầu |
| 7 | `requested_date` | list `:211` | Date | `string` `format:date` nullable | ngày yêu cầu (order_by) |
| 8 | `urgency` | list `:211` | Select (Routine/Urgent/Emergency) | `string` | mức khẩn |
| 9 | `allocation_status` | list `:212` | Select (Requested/Approved/Picked/Issued/Returned/Cancelled) | `string` | trạng thái (⟵ `workflow_state` merge @`:54-55`) |
| 10 | `total_value` | list `:212` | Currency | `number` | tổng giá trị phụ tùng |
| 11 | `stock_movement_ref` | list `:212` | Link (AC Stock Movement) | `string` nullable | bút toán kho khi xuất |
| 12 | `asset_name` | enrich `:217` (special-case `:189-190`) | (denorm `asset_name`) | `string` | tên thiết bị |
| 13 | `warehouse_name` | enrich `:218` (special-case `:191-192`) | (denorm `warehouse_name`) | `string` | tên kho — **KHÔNG** `warehouse_from_name` |
| 14 | `requested_by_name` | enrich `:219` (special-case `:195-196`) | (denorm `full_name`) | `string` | tên người yêu cầu |

**KHÔNG có** field `Check` int-0/1 → 0 property `type: boolean` (§2.d). `total_value` = `number`
(Currency). `*_date`/`Link` nullable = `string` (`.get(...) or ""` coalesce khi FK dangling).

---

## 4. Guard test (test_mobile_oas `TestMobileListAllocationContract` a..g)

- a — path `.../imm15.list_allocations` method GET-only + `operationId: listAllocations` + `tags:
  [inventory]`; ∈ `_MVP_BUSINESS_PATHS`; path/opId count == 80 unique camelCase (RED-before).
- b — `AllocationListItem` closed + `set(properties)` == EXACT 14 (11 list + 3 enrich); `required:[name]`;
  3 enrich key hiện diện (special-case ground-verbatim); 0 property `type: boolean` (MIỄN CR-01).
- c — **anti-copy-listCommissioning**: `AllocationListPage` closed, set-keys == `{data, pagination}`
  CHÍNH XÁC, assert `'items' ∉ keys`; `data.items.$ref` → `/AllocationListItem`; `pagination.$ref` →
  `/Pagination`.
- d — parameters ĐÚNG 7 (1:1 argspec): 2 `$ref [Page, PageSize]` + 5 inline `{filters, workflow_state,
  asset, work_order_ref, urgency}` mỗi cái query/string/optional; KHÔNG `mine`/`WorkOrderFilters`/
  `CommissioningFilters`.
- e — 200 = response-component `AllocationList` `oneOf [AllocationListEnvelope, Error]` 0-discr; `Envelope.data.$ref`
  → `/AllocationListPage` (rows-key `data.data[]`); success enum `[true]`/`[false]`; 401 `Unauthorized401`,
  403 `Forbidden`; status set `[200,401,403]`; KHÔNG requestBody.
- f — 3 schema closed; ∈ `_MVP_LIST_ENVELOPE` (len==11) trỏ `AllocationListEnvelope`; self-consistent
  (path ∈ `_MVP_BUSINESS_PATHS ∩ _MVP_LIST_ENVELOPE`); live-signature parity == ĐÚNG 7 param.
- g — naming-guard: `Allocation*` == ĐÚNG 3 schema, disjoint `Commissioning*`/`DueCalibration*`; rows-key
  tương-phản codified.

Bulk-bump guard: path/opId count +1 (79→80 live) · `_MVP_LIST_ENVELOPE` 10→11 · c5 68→69 ·
`_PARITY_BUSINESS_PATHS` 68→69 · `_EXPECTED_TEST_COUNT` +7 (728→735) · docset 3 counter (test_mobile_oas.py
728→735 · `_GUARD_SUITE_SUM` 871→878 · `_MOBILE_OAS_TOTAL` 897→904 · transition-baseline `list_allocations_delta=7`).

---

## 5. Hệ quả

- **+**: mobile FE codegen được typed-client cho màn F9 (thay raw `apiClient`); mở nhánh IMM-15 (tag
  `inventory` sẵn cho transfer/cycle-count kế). Double-data trap được test khóa (chống deser rỗng rows).
- **−**: thêm 3 schema + 1 response-component + 1 path vào mirror (đã cân bằng qua bookkeeping). Rows-key
  `data.data[]` là di-sản service layer (KNOWN-GAP normalize về 1 key chung = Phase-E, đụng service `.py`
  — NGOÀI phạm-vi round contract-only này).
- **Đánh đổi**: giữ nguyên rows-key `data.data[]` (KHÔNG hợp-nhất về `items`) = nói ĐÚNG sự-thật wire-shape
  cho codegen native (nếu khai `items` → model deser sai key → rows rỗng).
