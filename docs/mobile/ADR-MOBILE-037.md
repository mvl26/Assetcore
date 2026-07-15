# ADR-MOBILE-037 — `listRepairWorkOrders` `RepairWorkOrderListItem.status`/`priority` formal enum-parity (**CR-08 · enum-parity-curate** — formal-hoá `enum` cho 2 property `status` (9 giá trị `RepairStatus`) + `priority` (3 giá trị) của schema list-item `RepairWorkOrderListItem` trong OAS mirror; đóng codegen-drift: list-item đang sinh `String` TRẦN thay union typed, dù precedent `CreateRepairWorkOrderResponse.status@yaml:3041` đã khai enum 9-state — cùng `RepairStatus` doctype, 1 SoT)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-037 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-13 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — 200-shape `RepairWorkOrderListEnvelope` `{data:{pagination, data[]}}` KHÔNG đổi; C3-split list-element `RepairWorkOrderListItem`) · **precedent enum-parity**: `CreateRepairWorkOrderResponse.status` (`yaml:3041` — enum 9 `RepairStatus` VERBATIM, đã curate, `imm09.py:786`) — **1 SoT precedent**, KHÔNG chế enum mới · **precedent Select-enum canonical**: `CreateRepairWorkOrderRequest.priority`/`repair_type` (`yaml` — Select-canonical `@asset_repair.json`) · Core Doc IMM-09 narrative [`04-api-contract.md`](./04-api-contract.md) §6.3 (bảng list-element C3-split `RepairWorkOrderListItem`) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (@2026-07-13): service `list_work_orders(filters, *, page, page_size)` @`assetcore/services/imm09.py:1044` trả `status`/`priority` **CANONICAL** — 2 field ∈ `_LIST_WO_FIELDS` @`imm09.py:958-966` (`"...","priority",\n"status",...`), lấy trực-tiếp cột Select DB qua `RepairRepo.list(fields=_LIST_WO_FIELDS)` (`frappe.get_all`) @`imm09.py:1064-1070`. Các enricher `_enrich_rows`/`_enrich_sla_breach`/`_finalize_list_row` **KHÔNG transform** `status`/`priority` (chỉ ĐỌC `status` để derive `sla_paused = (status == RepairStatus.PENDING_PARTS)`). Doctype: `status` Select 9-option + `priority` Select 3-option @`assetcore/assetcore/doctype/asset_repair/asset_repair.json`. `git diff` `services/imm09.py`/`api/imm09.py` vùng `list_work_orders` = TRỐNG round NÀY ⇒ backend ĐÃ LIVE, thay đổi CHỈ ở OAS mirror. Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (`RepairWorkOrderListItem.properties.status.enum` + `.priority.enum`). Nguồn yêu cầu: `assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` CR-08.

---

## Context

Danh sách **"Phiếu CM (sửa chữa) của tôi"** (mobile `CMWorkOrderListView` / tab MVP-5b, `listRepairWorkOrders` → `RepairWorkOrderListEnvelope.data.data[]` phần tử `RepairWorkOrderListItem`) hiển thị mỗi dòng với **badge trạng thái** (Mở / Đã giao / Đang chẩn đoán / … / Đã hoàn thành) và **chip mức ưu tiên** (Bình thường / Khẩn / Cấp cứu).

Cội nguồn codegen-drift (CR-08, phát hiện khi so schema list-item vs schema create-response):
- `RepairWorkOrderListItem.status` + `.priority` khai `type: string` **TRẦN** (không `enum`) ⇒ codegen typescript-axios/Dart sinh `status: string` free-form — client mất union typed (state-machine), mất autocomplete + type-safety cho badge/chip, dễ so-sánh literal sai chính-tả (`'In repair'` vs `'In Repair'`).
- Trái lại `CreateRepairWorkOrderResponse.status` (`yaml:3041`) **ĐÃ curate** enum 9-state `RepairStatus` VERBATIM ⇒ **bất đối xứng contract**: cùng 1 `RepairStatus` doctype, cùng 1 field-semantic, nhưng create-response typed còn list-item không.
- Service `list_work_orders` **ĐÃ trả** `status`/`priority` canonical (Select-column qua `get_all`, `_LIST_WO_FIELDS`) — giá trị wire LUÔN ∈ tập Select doctype. Contract chưa phản ánh ⇒ codegen kém trung thực so với payload thật.

Ràng buộc quyết định:
1. **GIỮ `type: string`** — chỉ **THÊM** khoá `enum` (KHÔNG đổi type sang thứ khác; `RepairStatus`/`priority` là chuỗi Select, enum bó tập giá trị hợp lệ).
2. **status.enum = 9 giá trị VERBATIM, đúng thứ tự** — bằng-hệt (list-equality) `CreateRepairWorkOrderResponse.status.enum@yaml:3041` (**1 SoT precedent**, KHÔNG chế enum mới) + == Select options `@asset_repair.json` (grounding chống-bịa).
3. **priority.enum = 3 giá trị** `[Normal, Urgent, Emergency]` == Select options `@asset_repair.json`.
4. **CONTRACT-ONLY**: service ĐÃ trả 2 field canonical @source — thay đổi CHỈ ở OAS mirror, **KHÔNG đụng `.py`, KHÔNG reload worker, KHÔNG migrate**.
5. **Zero-footprint**: `RepairWorkOrderListItem` GIỮ `additionalProperties:false` + `required:['name']` + **tổng property KHÔNG đổi** (21-prop C3-split — chỉ bồi khoá `enum` vào 2 property CÓ SẴN, KHÔNG thêm/bớt property, KHÔNG đổi type/nullable); path/opId **65 GIỮ** + c5 **54 GIỮ** (field-level enum add ≠ path/schema-component/parameter mới).

## Decision

Bồi khoá `enum` vào 2 property CÓ SẴN của schema `RepairWorkOrderListItem`, GIỮ NGUYÊN `type: string`:

### `RepairWorkOrderListItem.properties.status`
- **`type: string` GIỮ** + **`enum: [Open, Assigned, Diagnosing, Pending Parts, In Repair, Pending Inspection, Completed, Cannot Repair, Cancelled]`** (9 giá trị `RepairStatus` VERBATIM, đúng thứ tự — bằng-hệt `CreateRepairWorkOrderResponse.status@yaml:3041`).

### `RepairWorkOrderListItem.properties.priority`
- **`type: string` GIỮ** + **`enum: [Normal, Urgent, Emergency]`** (3 giá trị Select-canonical `@asset_repair.json`, khớp `_SLA_MATRIX`).

### `RepairWorkOrderListItem.required[]` / `additionalProperties` — KHÔNG đổi
- `required` GIỮ `['name']` (mọi field khác optional — Option A closed-schema); `additionalProperties:false` GIỮ.

### Invariant contract (guard `TestMobileRepairListItemEnumParity` a..f, `test_mobile_oas`)
- **TC-a** `status` + `priority` CÓ khoá `enum` (drift-closed; RED trước bồi → GREEN sau).
- **TC-b** `status` GIỮ `type:string` + `enum` == 9 `RepairStatus` VERBATIM đúng thứ tự (`_REPAIR_STATUS_ENUM`).
- **TC-c** `priority` GIỮ `type:string` + `enum` == `[Normal, Urgent, Emergency]` (`_REPAIR_PRIORITY_ENUM`).
- **TC-d** `RepairWorkOrderListItem.status.enum` **bằng-hệt** `CreateRepairWorkOrderResponse.status.enum` (list-equality — 1 SoT precedent @`yaml:3041`).
- **TC-e** **grounding chống-bịa**: đọc TRỰC TIẾP `asset_repair.json` → `set(status.enum) == set(Select options)` VÀ `set(priority.enum) == set(Select options)` (+ guard 2-chiều `_REPAIR_STATUS_ENUM`/`_REPAIR_PRIORITY_ENUM` SoT-test == doctype).
- **TC-f** **no-structural-drift + zero-footprint**: `additionalProperties:false` GIỮ + `required:['name']` GIỮ + property-set == `_REPAIR_WO_FIELDS` (21-prop KHÔNG đổi) + `status`/`priority` `type:string` no-`nullable` + KHÔNG `string`-prop khác mọc `enum` lạ round NÀY.
- **RED-before/GREEN-after** chứng minh trên TC-a/b/d/e: strip `status.enum` → RED (`DRIFT: RepairWorkOrderListItem.status THIẾU enum`); bồi lại → GREEN.

## Alternatives

| Phương án | Vì sao LOẠI |
|---|---|
| **A. Giữ nguyên (`string` TRẦN, không bồi enum)** | Không đóng CR-08 — codegen sinh `String` free-form, client mất union typed (state-machine badge/chip), bất đối xứng vĩnh viễn với `CreateRepairWorkOrderResponse.status` đã typed; dễ so-literal sai chính-tả. |
| **B. Chế enum mới (tự liệt kê giá trị)** | Vi phạm 1-SoT — `RepairStatus` đã có precedent `@yaml:3041` + doctype Select. Enum tự-chế lệch = 2 nguồn-sự-thật cho 1 doctype → drift. VERBATIM copy precedent + grounding doctype là đúng (TC-d/TC-e). |
| **C. Đổi `type` (vd `type` khác / thêm `nullable`)** | `status`/`priority` là chuỗi Select non-null (doctype có `default`, list emit canonical). Đổi type/thêm nullable = sai wire-shape + phá zero-footprint (TC-f khoá `type:string` no-nullable). |
| **D. Thêm `status`/`priority` vào `required`** | Vô-nghĩa cho enum-curate — Option A closed-schema chỉ `required:['name']`; enum bó GIÁ-TRỊ khi field xuất hiện, KHÔNG ép field bắt-buộc. Zero-footprint GIỮ `required:['name']`. |
| **E. Tách schema `RepairStatus`/`Priority` component + `$ref`** | Over-engineer cho field-level enum inline (mirror-shape precedent `CreateRepairWorkOrderResponse.status` inline enum, KHÔNG component); thêm schema-component = phá zero-footprint (path/opId/c5 phải GIỮ). Inline enum là đối xứng. |

## Consequences

- **(+)** Codegen client phơi `status`/`priority` là **union typed** (enum) ⇒ danh sách "Phiếu CM của tôi" render badge trạng-thái + chip ưu-tiên typed, đối xứng `CreateRepairWorkOrderResponse.status`; đóng codegen-drift list-item, chống so-literal sai chính-tả.
- **(+)** enum khai == service emit canonical (`_LIST_WO_FIELDS` get_all) + == precedent `CreateRepairWorkOrderResponse.status@yaml:3041` (TC-d) + == doctype Select options (TC-e grounding) ⇒ contract trung thực @source, chống drift 2-chiều.
- **(+)** FIELD-LEVEL ENUM ADD: path-count **65 GIỮ**, opId **65 GIỮ**, c5 **54 GIỮ**, `additionalProperties:false` GIỮ NGUYÊN, `required` GIỮ `['name']`, tổng property `RepairWorkOrderListItem` 21 KHÔNG đổi ⇒ baseline closed-schema sweep + path-count guard + YAML lint + C3-split field-disjoint guard (`test_mob_oas_21d`) KHÔNG đỏ.
- **(0)** CONTRACT-ONLY: 0 đụng `.py`, 0 reload worker, 0 migrate. Test: `test_mobile_oas` 616→**622** (+6 TC `TestMobileRepairListItemEnumParity` a..f) · `test_mobile_docset` sync `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` 616→622 / `_GUARD_SUITE_SUM` 759→**765** / `_MOBILE_OAS_TOTAL` 785→**791** + delta var `repair_listitem_enum_parity_delta=6` (transition-baseline doc_09). BE regression `test_imm09` (SoT `list_work_orders` @`imm09.py:1044` KHÔNG đổi) — đỏ round NÀY do fixture-contamination môi trường (`DoesNotExistError: Asset None not found` trong setUp, 78/80 errors + 2 RBAC/firmware-state env failures — ĐỘC LẬP với thay đổi pure-yaml; test_imm09 KHÔNG import mobile yaml).

### Naming guard (∅)
Không thêm schema/component/parameter mới ⇒ 0 va chạm tên. 2 khoá `enum` là field-level inline của property CÓ SẴN `status`/`priority` — không đăng ký `components/schemas` mới. Precedent `CreateRepairWorkOrderResponse.status.enum` (create-response) GIỮ nguyên (2 schema khác nhau CÙNG share tập `RepairStatus`, list-equality = có chủ đích).

## Handoff CORE-DEV (native repo — ngoài `assetcore`)

Sau khi regenerate client từ OAS mirror: model list-item (`repair-work-order-list-item.ts` hoặc tương đương) có `status` + `priority` là **enum typed** (`RepairStatusEnum` 9-value / `PriorityEnum` 3-value) thay `string` trần. Danh sách "Phiếu CM của tôi" render badge trạng-thái + chip ưu-tiên map từ enum typed (SSoT label VI — TÁI DÙNG map như create-flow/detail-flow). CR-08 → RESOLVED (contract enum-parity, backend đã ship canonical).
