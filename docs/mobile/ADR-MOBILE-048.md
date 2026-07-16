# ADR-MOBILE-048 — `listCommissioning` (`imm04.list_commissioning`) curate vào OAS mirror (**CR-25a · MỞ NHÁNH IMM-04 F6 "Tiếp nhận & Nghiệm thu hiện trường"** — bồi ĐÚNG 1 GET-list path trả danh sách bản-ghi nghiệm thu (Asset Commissioning) permission-aware, phân trang; LIST-ENTRY của màn F6; rows-key `data.items[]` Asset-style; 200 = oneOf `[Envelope, Error]` Decision-B; list-item MIỄN Check int-0/1 (`is_radiation_device`/`doa_incident` chỉ là filter-key))

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-048 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-14 |
| Tác giả | BE (mobile contract curate) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; closed-schema oneOf, KHÔNG discriminator) · **sibling trực-tiếp**: **ADR-MOBILE (listAssets — `imm00.list_assets`)** — CÙNG shape paginated list-read rows-key `data.items[]`, 200 = response-component có `oneOf [<ListEnvelope>, Error]`; precedent param JSON-string **`WorkOrderFilters`** (@yaml:235) · Core Doc IMM-04 [`04-api-contract.md`](./04-api-contract.md) + [`docs/imm-04/05_API_Specification.md`](../imm-04/05_API_Specification.md) · CR-25 `assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` (repo mobile riêng, KHÔNG checkout ở cây backend — ref inline-code KHÔNG link, mirror ADR-041/042 convention) |

---

## 1. Bối cảnh

Màn **F6 "Tiếp nhận & Nghiệm thu hiện trường"** (`docs/features/38-tiep-nhan-nghiem-thu-thiet-bi.md`)
là LIST-ENTRY tiêu thụ `imm04.list_commissioning` để hiển thị danh sách phiếu nghiệm thu (Asset
Commissioning) đang xử lý. Endpoint **ĐÃ LIVE** nhưng **CHƯA curate** vào contract mirror
(`assetcore-mobile.openapi.yaml`) → chưa có generated typed-client. ADR này curate **contract-only**
(0 `.py` runtime change / 0 reload / 0 migrate).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler `list_commissioning` @`api/imm04.py:24` — `@frappe.whitelist()` **bare** (no `allow_guest`) →
  GET nhận; guest → dispatcher-403. Chữ ký `list_commissioning(filters: str = "{}", page: int = 1,
  page_size: int = 20)`. Thân: `parse_json(filters)` trong `try/except ServiceError → _err` (malformed
  → 400 INVALID_PARAMS TRÊN HTTP-200) rồi `_handle(svc.list_commissioning, f, int(page), int(page_size))`.
- Service `list_commissioning` @`services/imm04.py:831` — `frappe.has_permission(..., throw=True)` fail →
  `raise ServiceError(ErrorCode.FORBIDDEN, ...)` (in-handler FORBIDDEN → `_err` TRÊN HTTP-200 ⇒ **oneOf**).
  Lọc `safe_filters = {k:v for k,v in filters.items() if k in _ALLOWED_FILTER_KEYS}`; `page_size =
  min(max(1,·),100)`; `total = frappe.db.count(_DT, query_filters)`; `frappe.get_all(_DT,
  fields=_LIST_FIELDS, ...)` + enrich `*_name`; `return {"items": records, "pagination": pg}` → `_ok` ⇒
  **rows-key `data.items[]`** (Asset-style, KHÁC PM/calib `data.data[]`).
- `_LIST_FIELDS` @`services/imm04.py:117` (13 field) + 7 enrich (`master_item_name`,
  `device_model_name`, `vendor_name`, `supplier_name`, `clinical_dept_name`, `po_ref_name`,
  `asset_name`) gán @`:875-881` = **20 property**.
- `_ALLOWED_FILTER_KEYS` @`services/imm04.py:125` (frozenset 12 key).
- DocType `asset_commissioning.json` — field-type grounding (bảng §3).

---

## 2. Quyết định

### (a) 200 = oneOf `[CommissioningListPage-envelope, Error]` — **Decision-B**

`list_commissioning` chạy QUA `_handle(...)` VÀ service `raise ServiceError(FORBIDDEN)` (+ handler
`_err` cho malformed `filters` → INVALID_PARAMS). Lỗi nghiệp-vụ đến TRÊN HTTP-200 với body `Error` ⇒
200 = **oneOf** `[CommissioningListEnvelope | Error]` (KHÁC listTransfers/refdata SINGLE-shape vì
những cái đó 0 `_err` in-handler). Mirror `listAssets`/`listIncidents`. Wire qua **response-component**
`CommissioningList` (KHÔNG inline) — đối xứng `AssetList`/`IncidentList`, để sweep C7/`_MVP_LIST_ENVELOPE`
resolve được `content.schema.oneOf`.

`Error.http_status` thực-tế ⊇ `{400 (malformed filters), 403 (FORBIDDEN cap-read)}`.

### (b) rows-key `data.items[]` (Asset-style)

Envelope `CommissioningListEnvelope = {success:[true], data: $ref CommissioningListPage}`;
`CommissioningListPage = {items: array<CommissioningListItem>, pagination: $ref Pagination}`.
`data.items[]` — **KHÁC** PM/calib `data.data[]`; mirror `AssetListEnvelope`/`IncidentListEnvelope`.
REUSE component `Pagination` (@yaml:752) — KHÔNG tạo mới.

### (c) `CommissioningListItem` = **EXACT 20 property**, closed, `required:[name]`

13 `_LIST_FIELDS` + 7 enrich `*_name`. `additionalProperties:false`. Chỉ `name` REQUIRED (PK); mọi
field khác optional (mirror `AssetListItem`).

### (d) **List-item MIỄN Check int-0/1 (CR-01)** — điểm phân-biệt cốt-lõi

`is_radiation_device` + `doa_incident` là `Check` (int 0/1) NHƯNG **chỉ ∈ `_ALLOWED_FILTER_KEYS`**
(filter-key), **KHÔNG ∈ `_LIST_FIELDS`** → **KHÔNG** xuất hiện trong list-item. Vì vậy
`CommissioningListItem` **0 property `Check` int-0/1** ⇒ MIỄN coercion `Number(x)===1` (CR-01 family) ở
tầng list. (Check int-0/1 chỉ xuất hiện ở DETAIL `get_form_context` — ngoài phạm-vi ADR này.)

### (e) tag mới `commissioning`

Op-level `tags: [commissioning]` (module-tag parity — KHÔNG có top-level `tags:` block trong mirror;
đối xứng `[asset]`/`[incident]`/`[calibration]`). Đây là op ĐẦU TIÊN mang tag `commissioning`.

### (f) `CommissioningFilters` param — JSON-string honor 12 key

Component parameter mới `CommissioningFilters` (`name: filters`, `in: query`, `required: false`,
`schema.type: string`, `default: '{}'`) — mirror-style `WorkOrderFilters` (@yaml:235). Mô-tả liệt-kê
12 key ∈ `_ALLOWED_FILTER_KEYS`: `workflow_state · po_reference · master_item · vendor · clinical_dept ·
docstatus · is_radiation_device · doa_incident · vendor_serial_no · internal_tag_qr ·
expected_installation_date · final_asset`. Params path = ĐÚNG 3, đúng thứ tự `[CommissioningFilters,
Page, PageSize]`.

### (g) No-collision với `AssetCommissioningOrigin` / `getAssetCommissioningOrigin`

Nhánh IMM-04 F6 (`listCommissioning`, schema `Commissioning*List*`) **KHÁC nguồn** với
`getAssetCommissioningOrigin` (`imm00.get_commissioning_origin`, schema `AssetCommissioningOrigin*`,
asset-detail sub-tab #4, ADR-041). Tên schema/opId disjoint (namespace `Commissioning*List*` ∩
`AssetCommissioning*` = ∅) → 0 nhầm/ghi-đè. Guard TC7 khẳng-định `AssetCommissioningOrigin` +
`getAssetCommissioningOrigin` GIỮ NGUYÊN.

### (h) CONTRACT-ONLY

Backend `imm04.list_commissioning` ĐÃ LIVE (`api/imm04.py:24` · `services/imm04.py:831`) → **0 `.py`
runtime change · 0 reload · 0 migrate**. Chỉ chạm YAML + test guard + docs.

---

## 3. `CommissioningListItem` — type ĐÚNG từng field (GROUNDED `asset_commissioning.json`)

| # | property | nguồn | fieldtype | OpenAPI type | ghi chú |
|---|---|---|---|---|---|
| 1 | `name` | `_LIST_FIELDS` | (autoname) | `string` | PK — **required** |
| 2 | `workflow_state` | `_LIST_FIELDS` | Link (Workflow State) | `string` | trạng thái workflow |
| 3 | `docstatus` | `_LIST_FIELDS` | (builtin) | `integer` | 0 Draft / 1 Submitted / 2 Cancelled |
| 4 | `po_reference` | `_LIST_FIELDS` | Link (AC Purchase) | `string` | phiếu mua gốc |
| 5 | `master_item` | `_LIST_FIELDS` | Link (IMM Device Model) | `string` | model/cấu hình thiết bị |
| 6 | `vendor` | `_LIST_FIELDS` | Link (AC Supplier) | `string` | nhà cung cấp |
| 7 | `clinical_dept` | `_LIST_FIELDS` | Link (AC Department) | `string` | khoa/phòng lâm sàng |
| 8 | `expected_installation_date` | `_LIST_FIELDS` | Date | `string` `format:date` nullable | ngày lắp đặt dự kiến |
| 9 | `installation_date` | `_LIST_FIELDS` | Datetime | `string` nullable | ngày lắp đặt thực tế |
| 10 | `vendor_serial_no` | `_LIST_FIELDS` | Data | `string` | số serial nhà cung cấp |
| 11 | `internal_tag_qr` | `_LIST_FIELDS` | Data | `string` | mã QR/tem nội bộ |
| 12 | `final_asset` | `_LIST_FIELDS` | Link (AC Asset) | `string` | mã thiết bị (AC Asset) sinh ra |
| 13 | `modified` | `_LIST_FIELDS` | (builtin) | `string` | thời điểm sửa gần nhất (ISO) |
| 14 | `master_item_name` | enrich `:876` | (denorm model_name) | `string` | tên model |
| 15 | `device_model_name` | enrich `:877` | alias `master_item_name` | `string` | tên model (alias) |
| 16 | `vendor_name` | enrich `:878` | (denorm supplier_name) | `string` | tên nhà cung cấp |
| 17 | `supplier_name` | enrich `:879` | alias `vendor_name` | `string` | tên nhà cung cấp (alias) |
| 18 | `clinical_dept_name` | enrich `:880` | (denorm department_name) | `string` | tên khoa/phòng |
| 19 | `po_ref_name` | enrich `:881` | (denorm purchase_name) | `string` | tên/số phiếu mua |
| 20 | `asset_name` | enrich `:882` | (denorm asset_name) | `string` | tên thiết bị (AC Asset) |

**KHÔNG có** field `Check` int-0/1 (`is_radiation_device`/`doa_incident` ∉ `_LIST_FIELDS`; xem §2.d).

`*_date` = `string` nullable (Date/Datetime có thể null); mọi `Link` = `string`; enrich = `string`
(coalesce `""` khi FK dangling — `.get(...) or ""`).

---

## 4. Guard test (test_mobile_oas TestMobileListCommissioningContract a..h)

- a — path `.../imm04.list_commissioning` method GET + `operationId: listCommissioning` + `tags:
  [commissioning]` (TC1 · RED-before khi chưa curate).
- b — `CommissioningListItem` closed + `set(properties)` == EXACT 20 (13 `_LIST_FIELDS` + 7 enrich);
  drift-guard (BE thêm list-field mà quên schema → RED) (TC2).
- c — `CommissioningListItem` KHÔNG có `is_radiation_device`/`doa_incident`/bất-kỳ Check int-0/1
  (AC2 · list-item MIỄN CR-01).
- d — `CommissioningListPage` closed + `items.items.$ref` → `/CommissioningListItem` + `pagination.$ref`
  → `/Pagination` (TC3).
- e — `listCommissioning.parameters` = 3 `$ref` đúng thứ-tự `[CommissioningFilters, Page, PageSize]`
  + `CommissioningFilters` = query string param (TC4).
- f — 200 = response-component `CommissioningList` có `oneOf [CommissioningListEnvelope, Error]` +
  401 `$ref Unauthorized401` (parity listIncidents) (TC5).
- g — `CommissioningListEnvelope` closed + `success.enum:[true]` + `data.$ref` →
  `/CommissioningListPage` (rows-key `data.items[]`) (AC3/AC4).
- h — no-collision: `AssetCommissioningOrigin` schema + `getAssetCommissioningOrigin` opId GIỮ NGUYÊN
  (TC7).

Bulk-bump guard: path/opId count +1 (75→76 live) · `_MVP_LIST_ENVELOPE` 8→9 · c5 64→65 ·
`_PARITY_BUSINESS_PATHS` 64→65 · `_EXPECTED_TEST_COUNT` +8 · docset 3 counter +8.
