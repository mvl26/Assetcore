# ADR-MOBILE-050 — `getAllocation` (`imm15.get_allocation`) curate vào OAS mirror (**CR-29b · MỞ NHÁNH IMM-15 F9-DETAIL "Xuất kho phụ tùng phục vụ WO"** — bồi ĐÚNG 1 GET-detail path trả phiếu cấp phát/xuất kho phụ tùng CHI TIẾT (header + `items[]` child table + `allowed_transitions[]` CTA) phục vụ Work Order, permission-aware; DETAIL-sibling của `listAllocations` ADR-MOBILE-049; 200 = inline `oneOf [SpareAllocationDetailEnvelope, Error]` Decision-B; ⚠️ payload OPEN `additionalProperties:true` vì `doc.as_dict()`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-050 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-14 |
| Tác giả | BA (mobile contract curate) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; closed-schema oneOf, KHÔNG discriminator) · **DETAIL-sibling trực-tiếp**: **ADR-MOBILE-049** (`listAllocations` — LIST-ENTRY CÙNG màn F9, CÙNG DocType `IMM Spare Allocation`, tag `inventory`) · **precedent shape**: `getCalibration` (imm11 — `get_allocation` COPY Y HỆT pattern `doc.as_dict()` + enrich + `allowed_transitions`), `getTransfer` (imm00 — as_dict single-detail inline oneOf), `getPmWorkOrder` (imm08 — detail có child `items[]` + `allowed_transitions[]`) · Core Doc IMM-15 [`docs/imm-15/05_API_Specification.md §3.0`](../imm-15/05_API_Specification.md) + [`04_Backend_Design.md §VI.1.1`](../imm-15/04_Backend_Design.md) (ADR-IMM-15-10) |

---

## 1. Bối cảnh

Màn **F9 "Xuất kho phụ tùng phục vụ WO"** đã có LIST-ENTRY (`listAllocations`, ADR-MOBILE-049). Bước kế:
mở 1 phiếu để xem **CHI TIẾT** (header + danh sách dòng phụ tùng + nút hành động Duyệt/Xuất kho/Hủy/Trả).
Đây là **DETAIL-sibling** của `listAllocations` — KHÁC LIST (không phân trang, không `items[]` mảng-phiếu;
thay vào đó 1 phiếu + `items[]` = child rows phụ tùng CỦA phiếu đó). Endpoint **ĐÃ LIVE** ở web-BE. ADR
này curate **contract-only** (0 `.py` runtime change / 0 reload / 0 migrate).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler `get_allocation` @`api/imm15.py:66` — `@frappe.whitelist()` **bare** (no `allow_guest`, no
  `rbac.require`, no cap-gate) → GET nhận; guest/no-token/thiếu DocPerm → **dispatcher-403**. Chữ ký =
  `get_allocation(name: str)` = **ĐÚNG 1 param** (`name`, KHÔNG default ⇒ **required**). Thân đúng 1 dòng:
  `return _handle(svc.get_allocation, name)`. `_handle` (@`api/imm15.py:28-36`) bọc `try: _ok(fn())` /
  `except ServiceError: _err(e.message, e.code)` / `except Exception: _err(...INTERNAL)` ⇒ **mọi lỗi
  nghiệp-vụ đến TRÊN HTTP-200 body `Error`** (KHÔNG raise → HTTP-4xx). Permission matrix (05 §2) =
  `get_allocation` **R cho cả 6 persona** (read-open base user).
- Service `get_allocation` @`services/imm15.py:224` — **`data = doc.as_dict()`** (@`:229`) → enrich `items`
  (@`:231-237`: mỗi row có `spare_part` → nạp `part_name`@`:235`/`uom`@`:236`/`unit_value`@`:237` từ `AC
  Spare Part`) → 3 enrich header `asset_name`@`:239`/`warehouse_name`@`:240`/`requested_by_name`@`:241` →
  `data["allowed_transitions"] = _allocation_allowed_transitions(data.get("allocation_status"))` (@`:244`,
  ADR-IMM-15-10) → `return data`. Doc∄ → `raise ServiceError(ErrorCode.NOT_FOUND, ...)` (@`:228`).
- DocType `imm_spare_allocation.json` (header) + `imm_spare_allocation_item.json` (child) — field-type
  grounding (bảng §3).

---

## 2. Quyết định

### (a) 200 = **inline** `oneOf [SpareAllocationDetailEnvelope, Error]` — Decision-B (⚠️ SELF-CORRECTION #2)

`get_allocation` qua `_handle(...)`; service raise `ServiceError(NOT_FOUND)` khi doc∄ → `_err` ⇒ Error đến
**TRÊN HTTP-200** (KHÔNG status-line 404). ⇒ 200 = **oneOf** `[SpareAllocationDetailEnvelope | Error]`,
CLOSED-schema route-by-VALUE `body.success` (KHÔNG discriminator — `success:boolean` OAS 3.x cấm
discriminator). `Error.http_status` thực-tế ⊇ `{404 (NOT_FOUND)}`.

> **⚠️ SELF-CORRECTION #2 vs acceptance ("Response component oneOf …"):** đề mục ghi "Response component".
> **Ground-truth**: MỌI 6 GET-detail read hiện có (`getPmWorkOrder`/`getRepairWorkOrder`/`getIncident`/
> `getCalibration`/`getTransfer`/`getAsset`) wire 200 bằng **INLINE `oneOf`** dưới
> `content.application/json.schema` — **KHÔNG** `#/components/responses/*` (named response-component chỉ
> dùng cho LIST path: `AllocationList`/`CommissioningList`). ⇒ getAllocation dùng **inline oneOf** (mirror
> `getCalibration` @yaml:10339-10347) + `401` `$ref Unauthorized401` + `403` `$ref Forbidden`. Slot =
> `{200,401,403}` (KHÔNG 404 status-line).

**2 loại 403 (DONE-gate spec-contract):** ở đây CHỈ có **dispatcher-403** (guest/no-token/thiếu DocPerm —
`@whitelist` bare, KHÔNG `rbac.require`) → GIỮ status-line key `403 Forbidden`. **KHÔNG có in-handler
cap-403** (service `get_allocation` KHÔNG có vendor-IDOR-guard/`_require_*` — KHÁC `getCalibration`/
`getPmWorkOrder` vốn có `assert_vendor_can_access` → in-handler 403-in-body). ⇒ nhánh Error chỉ mang
`NOT_FOUND` (KHÔNG FORBIDDEN-in-body). Đừng bịa vendor-IDOR-403.

### (b) ⚠️ SELF-CORRECTION #1 (MAJOR) — `SpareAllocationDetail` + `SpareAllocationItem` = **`additionalProperties: true` (OPEN)**, KHÔNG closed

Đề mục yêu cầu "2 schema CLOSED (additionalProperties:false)". **Ground-truth mâu thuẫn**: service trả
**`doc.as_dict()`** (@`services/imm15.py:229`) ⇒ payload mang **TOÀN BỘ** field DocType + meta Frappe
(`owner`/`creation`/`modified`/`modified_by`/`docstatus`/`idx`/`doctype`/`naming_series`/`workflow_state`…;
child rows còn `parent`/`parentfield`/`parenttype`) — VƯỢT XA danh sách field nghiệp-vụ liệt kê. **CLOSED
schema sẽ NÓI DỐI wire-shape** (reject key `as_dict` thật) + phá native codegen sealed-class strict-deser.

**Precedent tuyệt đối nhất-quán**: CẢ 6 `*Detail` as_dict-based hiện có đều **`additionalProperties: true`**
— `AssetDetail`/`PmWorkOrderDetail`/`RepairWorkOrderDetail`/`IncidentDetail`/`CalibrationDetail`/
`TransferDetail`. Chú thích `PmWorkOrderDetailEnvelope` @yaml nói thẳng: *"Envelope additionalProperties:false;
payload …Detail GIỮ additionalProperties:true (§3.2)"*. `get_allocation` COPY Y HỆT `get_calibration`
(`doc.as_dict()` + enrich + `allowed_transitions`) → `CalibrationDetail` = OPEN ⇒ `SpareAllocationDetail`
PHẢI OPEN. Tương tự child: `items` từ `doc.as_dict()` → child rows mang meta ⇒ `SpareAllocationItem` OPEN.

**DECISION:** `SpareAllocationItem` + `SpareAllocationDetail` = **`additionalProperties: true`**. CHỈ
**envelope** `SpareAllocationDetailEnvelope` = **`additionalProperties: false`** (mirror
`CalibrationDetailEnvelope`/`TransferDetailEnvelope` — envelope đóng, payload mở). Guard: assert Detail +
Item `additionalProperties == true`; Envelope `== false`.

### (c) `SpareAllocationItem` — 13 field nghiệp-vụ liệt kê (OPEN), `required: [spare_part]`

Ground `imm_spare_allocation_item.json` (13 field, §3.A). `spare_part`/`part_name`/`uom`/`unit_value` vừa là
field DocType vừa được enrich lại trong `get_allocation` (@`:231-235`). Chỉ `spare_part` REQUIRED (Link — PK
nghiệp-vụ của dòng; `name`=row-docname đến qua `additionalProperties`). Mọi field khác optional (Option A).

### (d) ⚠️ SELF-CORRECTION #3 — enum theo quy-tắc **leading-blank Select** của repo

Đề mục ghi `used_for enum[Replacement,Test,Calibration,Spare]` (4) + `return_condition enum[Good,Damaged,Used]`
(3). **Ground `imm_spare_allocation_item.json`**: options string = `",Replacement,Test,Calibration,Spare"`
và `",Good,Damaged,Used"` — **LEADING-BLANK** (member rỗng `""` đầu tiên = giá-trị unset hợp lệ;
`create_allocation` KHÔNG set 2 field này ⇒ dòng mới emit `""`). Repo có **quy-tắc đã đặt tên** (CR-10c /
ADR-MOBILE-028, hằng `_ASSET_CATEGORY_STRING_NULLABLE_SELECT_PROP`): *"Select LEADING-BLANK → string
nullable KHÔNG enum (`''` hợp lệ)"* vs *"Select bounded no-blank → string enum"*.

**DECISION (theo quy-tắc repo):**
- `used_for`, `return_condition` = **`type: string, nullable: true`, KHÔNG hard-enum** (giá-trị liệt kê ở
  `description`). Hard 4/3-enum sẽ reject dòng unset `""` → sai wire.
- `allocation_status` (header, options `"Requested,…,Cancelled"` **KHÔNG leading-blank**, `create` luôn set
  `"Requested"`) = **`type: string, enum: [Requested, Approved, Picked, Issued, Returned, Cancelled]`** (6) —
  ĐÚNG như acceptance yêu cầu.

### (e) `SpareAllocationDetail` — header field liệt kê (OPEN) + `items[]` + 3 enrich + `allowed_transitions[]`

Ground `imm_spare_allocation.json` (bỏ Section/Column Break). 1 field `Check` = `approval_required` →
**`integer, enum: [0,1]`** (né int-vs-bool trap Open#1 — mirror `CalibrationDetail.is_recalibration`).
`allowed_transitions` = `array<string>` (server-driven CTA, ADR-IMM-15-10; **KHÔNG enum-bound cứng** né
drift — mirror `PmWorkOrderDetail.allowed_transitions`). `items` = `array $ref SpareAllocationItem`. Chỉ
`name` REQUIRED. Bảng đầy đủ §3.B.

### (f) tag `inventory` (REUSE) — namespace `SpareAllocation*` DISJOINT `Allocation*`

Op-level `tags: [inventory]` (đã mở bởi ADR-049, KHÔNG tạo tag mới). Schema-family **`SpareAllocation*`**
(`SpareAllocationItem`/`SpareAllocationDetail`/`SpareAllocationDetailEnvelope`) — prefix `Spare*`
DISJOINT với `Allocation*` (list-family 3 schema). **Naming-guard hiện có AN TOÀN**: guard-g ADR-049 dùng
`n.startswith("Allocation")` (@test_mobile_oas.py:25034) ⇒ `SpareAllocation*` (startswith `"Spare"`) KHÔNG
lọt ⇒ `alloc_names == 3` GIỮ GREEN, 0 regression.

### (g) CONTRACT-ONLY

`imm15.get_allocation` ĐÃ LIVE (`api/imm15.py:66` · `services/imm15.py:224`) → **0 `.py` runtime change ·
0 reload gunicorn · 0 bench migrate**. Chỉ chạm YAML mirror + test guard + docs (ADR này + imm-15/05 note).
Guard live-signature parity: `inspect.signature(imm15.get_allocation)` == ĐÚNG 1 param `name`.

---

## 3. Schema — type ĐÚNG từng field (GROUNDED DocType JSON + service)

### 3.A `SpareAllocationItem` (`additionalProperties: true`, `required: [spare_part]`) — 13 field

| # | property | nguồn | fieldtype | OpenAPI type | ghi chú |
|---|---|---|---|---|---|
| 1 | `spare_part` | item `:232` | Link (AC Spare Part) | `string` | **required** (PK dòng) |
| 2 | `part_name` | Data + enrich `:235` | Data | `string` nullable | tên phụ tùng (fallback `spare_part`) |
| 3 | `qty_requested` | item | Float | `number` nullable | SL yêu cầu |
| 4 | `qty_approved` | item | Float | `number` nullable | SL phê duyệt |
| 5 | `qty_issued` | item | Float | `number` nullable | SL đã xuất |
| 6 | `qty_returned` | item | Float | `number` nullable | SL trả lại |
| 7 | `uom` | Link + enrich `:236` | Link (AC UOM) | `string` nullable | ĐVT (fallback `stock_uom`) |
| 8 | `batch_no` | item | Data | `string` nullable | số lô |
| 9 | `serial_no` | item | Data | `string` nullable | số serial |
| 10 | `unit_value` | Currency + enrich `:237` | Currency | `number` nullable | đơn giá (fallback `unit_cost`, or 0) |
| 11 | `line_value` | item | Currency | `number` nullable | thành tiền |
| 12 | `used_for` | item | Select **leading-blank** `,Replacement,Test,Calibration,Spare` | `string` nullable **KHÔNG enum** | §2.d — `""` unset hợp lệ; values ở description |
| 13 | `return_condition` | item | Select **leading-blank** `,Good,Damaged,Used` | `string` nullable **KHÔNG enum** | §2.d — `""` unset hợp lệ; values ở description |

> Meta Frappe child (`name`/`owner`/`creation`/`modified`/`docstatus`/`idx`/`parent`/`parentfield`/
> `parenttype`/`doctype`) đến qua `additionalProperties:true` — KHÔNG liệt kê.

### 3.B `SpareAllocationDetail` (`additionalProperties: true`, `required: [name]`) — 27 property

| # | property | nguồn | fieldtype | OpenAPI type | ghi chú |
|---|---|---|---|---|---|
| 1 | `name` | as_dict | (autoname `SAL-.YYYY.-.#####`) | `string` | **required** (PK) |
| 2 | `naming_series` | as_dict | Select | `string` | |
| 3 | `workflow_state` | as_dict | Link (Workflow State) | `string` nullable | desk dual-track (ADR-IMM-15-10) |
| 4 | `work_order_doctype` | as_dict | Select (IMM PM/CM WO · Asset Repair) | `string` nullable | |
| 5 | `work_order_ref` | as_dict | Dynamic Link (`work_order_doctype`) | `string` nullable | WO liên kết |
| 6 | `asset` | as_dict | Link (AC Asset) | `string` nullable | thiết bị |
| 7 | `warehouse_from` | as_dict | Link (AC Warehouse) | `string` nullable | kho xuất |
| 8 | `requested_by` | as_dict | Link (User) | `string` nullable | người yêu cầu |
| 9 | `requested_date` | as_dict | Date | `string` `format:date` nullable | |
| 10 | `required_date` | as_dict | Date | `string` `format:date` nullable | |
| 11 | `urgency` | as_dict | Select (Routine/Urgent/Emergency, no-blank) | `string` | (parity list-item: `string`, values ở description) |
| 12 | `allocation_status` | as_dict `:229` | Select 6, no-blank | `string` **enum** `[Requested,Approved,Picked,Issued,Returned,Cancelled]` | §2.d |
| 13 | `items` | as_dict `:229` (`:231` enrich loop) | Table (IMM Spare Allocation Item) | `array` `$ref SpareAllocationItem` | child rows phụ tùng |
| 14 | `total_value` | as_dict | Currency | `number` nullable | tổng giá trị |
| 15 | `approval_required` | as_dict | **Check** | **`integer` enum `[0,1]`** | §2.e — int-vs-bool trap |
| 16 | `approved_by` | as_dict | Link (User) | `string` nullable | |
| 17 | `approval_date` | as_dict | Datetime | `string` `format:date-time` nullable | |
| 18 | `override_approver_2` | as_dict | Link (User) | `string` nullable | duyệt Emergency 2 |
| 19 | `override_reason` | as_dict | Small Text | `string` nullable | |
| 20 | `stock_movement_ref` | as_dict | Link (AC Stock Movement) | `string` nullable | bút toán Xuất |
| 21 | `stock_movement_return_ref` | as_dict | Link (AC Stock Movement) | `string` nullable | bút toán Trả lại |
| 22 | `notes` | as_dict | Text Editor | `string` nullable | |
| 23 | `audit_flags` | as_dict | Small Text | `string` nullable | |
| 24 | `asset_name` | enrich `:239` | (denorm AC Asset.asset_name) | `string` | tên thiết bị |
| 25 | `warehouse_name` | enrich `:240` | (denorm AC Warehouse.warehouse_name) | `string` | tên kho — **KHÔNG** `warehouse_from_name` |
| 26 | `requested_by_name` | enrich `:241` | (denorm User.full_name) | `string` | tên người yêu cầu |
| 27 | `allowed_transitions` | `:244` (ADR-IMM-15-10) | (server CTA) | `array` items `string` | next-state; terminal Returned/Cancelled → `[]`; **KHÔNG enum-bound** |

### 3.C `SpareAllocationDetailEnvelope` (`additionalProperties: false`, `required: [success, data]`)

`{success: {type: boolean, enum: [true]}, data: {$ref: SpareAllocationDetail}}` — mirror
`CalibrationDetailEnvelope`. **Envelope đóng; payload mở** (§2.b).

---

## 4. Path + param

```
/api/method/assetcore.api.imm15.get_allocation:
  get:
    tags: [inventory]
    operationId: getAllocation
    summary: '[F9-DETAIL] Chi tiết phiếu cấp phát/xuất kho phụ tùng (màn detail + CTA workflow) — detail-read'
    parameters:
      - name: name
        in: query
        required: true              # chữ ký get_allocation(name) 1-param no-default @api/imm15.py:66
        schema: { type: string }    # PK naming-series SAL-.YYYY.-.#####
    responses:
      '200':
        content:
          application/json:
            schema:
              oneOf:
                - $ref: '#/components/schemas/SpareAllocationDetailEnvelope'
                - $ref: '#/components/schemas/Error'
      '401': { $ref: '#/components/responses/Unauthorized401' }
      '403': { $ref: '#/components/responses/Forbidden' }
```

---

## 5. Guard test (`test_mobile_oas.py` — class RIÊNG `TestMobileGetAllocationContract` a..h)

> KHÔNG gộp vào `TestMobileGetDetailContract` (đóng băng ĐÚNG 4 detail @test_mobile_oas.py:8244
> `len(set(data_refs)) == 4`) — mirror cách `getTransfer` có xử-lý RIÊNG. Đặt class riêng.

- **a** — path `.../imm15.get_allocation` method **GET-only** + `operationId: getAllocation` + `tags:
  [inventory]`; ∈ `_MVP_BUSINESS_PATHS`; path/opId count == **81** unique camelCase (RED-before 80).
- **b** — param ĐÚNG 1: `name` `in:query`, **`required: true`**, `schema.type == string`; KHÔNG param khác;
  KHÔNG requestBody. Live-sig parity: `inspect.signature(imm15.get_allocation)` == 1 param `name`.
- **c** — `SpareAllocationItem`: **`additionalProperties == true`** (§2.b); `set(properties)` ⊇ 13 field
  §3.A; `required == [spare_part]`; `used_for`/`return_condition` = `type:string` **KHÔNG `enum` key**
  (§2.d leading-blank); 4 `qty_*` = `number`; 0 property `type:boolean`.
- **d** — `SpareAllocationDetail`: **`additionalProperties == true`** (§2.b); `set(properties)` ⊇ 27 prop
  §3.B; `required == [name]`; `items.$ref` → `/SpareAllocationItem`; `allocation_status.enum` == 6 giá-trị
  `[Requested,Approved,Picked,Issued,Returned,Cancelled]`; `approval_required` = `integer` enum `[0,1]`
  (KHÔNG boolean); `allowed_transitions` = `array` items `string` (KHÔNG enum-bound); 3 enrich key hiện
  diện (`asset_name`/`warehouse_name`/`requested_by_name`).
- **e** — `SpareAllocationDetailEnvelope`: **`additionalProperties == false`** (§2.b — envelope đóng);
  `success.enum == [true]`; `data.$ref` → `/SpareAllocationDetail`; `required == [success, data]`.
- **f** — 200 = **inline** `oneOf [SpareAllocationDetailEnvelope, Error]` (0 discriminator, closed-disjoint
  required-set); **KHÔNG** dùng `#/components/responses/*` (§2.b SELF-CORRECTION #2); status set ==
  `[200,401,403]` (KHÔNG 404 status-line); `401` `$ref Unauthorized401`, `403` `$ref Forbidden`.
- **g** — registry self-consistency: path ∈ `_MVP_READ_ENVELOPE` (trỏ `SpareAllocationDetailEnvelope`) ∧ ∈
  `_MVP_BUSINESS_PATHS`; **∉ `_MVP_LIST_ENVELOPE`** (detail KHÔNG list — giữ len 11); `c5 == _MVP_BUSINESS_PATHS`.
- **h** — naming/no-collision: `SpareAllocation*` schema-family == ĐÚNG 3 (`Item`/`Detail`/`DetailEnvelope`);
  DISJOINT `Allocation*` (list-family 3, `startswith("Allocation")` KHÔNG match `Spare*` — §2.f); `getAllocation`
  ∥ `listAllocations` tồn tại song song; codify: `SpareAllocationDetail` (1 phiếu + child `items[]`) ≠
  `AllocationListItem` (1 dòng danh-sách phiếu).

### Bulk-bump bookkeeping (BE reconcile — ghi rõ để cân guard)

| Counter | File | Δ |
|---|---|---|
| path / opId count | yaml | 80 → **81** (+1 GET-detail) |
| `_MVP_READ_ENVELOPE` | test_mobile_oas.py | +1 (`_GET_ALLOCATION_PATH → SpareAllocationDetailEnvelope`) |
| `_MVP_BUSINESS_PATHS` | test_mobile_oas.py | +1 (union line `| {_GET_ALLOCATION_PATH}` — mirror getTransfer:2099) |
| `c5` | test_mobile_oas.py:9923 | 69 → **70** (== `_MVP_BUSINESS_PATHS`; auto qua `_MVP_READ_ENVELOPE`) |
| `_PARITY_BUSINESS_PATHS` | test_mobile_oas.py:10215 | 69 → **70** (`= set(_MVP_BUSINESS_PATHS)`) |
| `_MVP_LIST_ENVELOPE` | test_mobile_oas.py | **KHÔNG đổi** (11 — detail ≠ list) |
| `_DETAIL_READ_PATHS` | test_mobile_oas.py | **KHÔNG đụng** (đóng băng 4 @:8244) |
| `_EXPECTED_TEST_COUNT` | test_mobile_oas.py:212 | 735 → **743** (+8 TC class mới `TestMobileGetAllocationContract` a..h) |
| `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` | test_mobile_docset.py:759 | 735 → **743** |
| `_GUARD_SUITE_SUM` | test_mobile_docset.py:927 | 878 → **886** |
| `_MOBILE_OAS_TOTAL` | test_mobile_docset.py:1116 | 904 → **912** (= 886 + 26 preflight) |

> Nếu BE chọn số TC khác 8 → đồng-bộ 4 counter test-count (`_EXPECTED_TEST_COUNT` /
> `_GUARD_SUITE_EXPECTED` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL`) theo CÙNG delta.

---

## 6. Hệ quả

- **+**: mobile FE codegen typed-client cho màn **F9-DETAIL** (mở phiếu → header + `items[]` + nút CTA gated
  theo `allowed_transitions` server-driven, KHÔNG hardcode `allocation_status===` — GATE-8/LL-FE-51). Đóng
  cặp list→detail của nhánh IMM-15 `inventory`.
- **−**: +2 schema (`SpareAllocationItem`/`SpareAllocationDetail`) + 1 envelope + 1 path. Cân qua bookkeeping.
- **Đánh đổi (SELF-CORRECTION #1)**: giữ payload **OPEN** (`additionalProperties:true`) = nói ĐÚNG sự-thật
  `doc.as_dict()` (mang meta Frappe + full DocType field-set). CLOSED sẽ reject wire thật + phá sealed-class
  codegen — đi ngược 6 precedent `*Detail` hiện có. KNOWN-GAP (Phase-E, đụng service `.py`): chuẩn-hoá
  `get_*` detail sang whitelist-field explicit dict (như `get_pm_work_order`) để đóng payload — NGOÀI phạm-vi
  round contract-only.
- **Backlog (deferred, ADR-IMM-15-10)**: wire Pick chain (`pick_allocation`) + `close_allocation` (re-close)
  để gỡ EXCEPTION `allowed_transitions`; FE build `AllocationDetailView.vue` thật (06 §II.5) gate nút theo
  `allowed_transitions.includes(next)`.
