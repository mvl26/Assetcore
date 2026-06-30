# ADR-MOBILE-010 — Repair spare-parts sub-flow (`searchSpareParts` GET RAW-list no-403 + `requestSpareParts` POST CLEAN) — `RequestSparePartsResponse` RIÊNG 4-key (KHÔNG reuse `RepairActionResponse` 2-key) + 2 Self-Correction (forward-reservation §8.11 SAI · premise flip-bare→POST STALE)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-010 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-06-27 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | ADR-MOBILE-006 (POST-action route-by-VALUE + 403 SINGLE-SHAPE) · ADR-MOBILE-008 (`getUserContext` slot `{200,401}` no-403 cho path no-cap-gate) · Decision-B (closed-schema oneOf) · C6/C7 (200 oneOf [Env, Error]) · C3-split (`ResolveIncidentResponse`/`AssignTechnicianResponse` precedent: action-success `data` thêm field-thứ-ba ⇒ schema RIÊNG) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (`assetcore/api/imm09.py`, `assetcore/services/imm09.py`). Contract: [`04-api-contract.md §8.22`](./04-api-contract.md) (`searchSpareParts`) + [`§8.23`](./04-api-contract.md) (`requestSpareParts`). Core Doc IMM-09: `docs/imm-09/04_Backend_Design.md §3.5` + `docs/imm-09/05_API_Specification.md §3.6/§3.13`.

---

## Context

Màn repair-detail mobile (`getRepairWorkOrder`, C6-DETAIL) có **dead-end sub-flow vật-tư**: sau `submitDiagnosis(needs_parts=1)` (§8.11-bis → `Pending Parts`) KTV cần (1) **tìm vật tư** rồi (2) **gắn phiếu xuất kho** (`stock_entry_ref`) vào dòng `spare_parts_used` để rời `Pending Parts` → `In Repair`. 2 endpoint BE đã sẵn nhưng CHƯA có path mobile-contract: `search_spare_parts` (GET picker) + `request_spare_parts` (POST gắn-phiếu). Vòng này bồi **2 path** (path/opId 40→42), `info.version` GIỮ `0.1.0-skeleton`, 0 dangling `$ref`.

Cặp này khác các C8-ACTION đã làm ở **4 điểm hợp đồng** cần quyết định — gồm **2 Self-Correction** lỗi thiết-kế-gốc:

1. **`searchSpareParts` `data` = list TRẦN + slot `{200,401}` no-403.** `search_spare_parts` (`api/imm09.py:123` bare `@frappe.whitelist()` GET) return `list[dict]` RAW cap bởi SQL `LIMIT` (`services/imm09.py:1223-1248`) — KHÔNG paginate, KHÔNG object-wrapper. Handler **KHÔNG `rbac.require`** (`api/imm09.py:124-125`) ⇒ KHÔNG in-handler cap-403 (read-only picker — quyền đọc đủ).
2. **Self-Correction #1 — `requestSpareParts` KHÔNG reuse `RepairActionResponse` 2-key.** §8.11 forward-reserve `RepairActionResponse {name,status}` "tái dùng cho `assign_technician`/`submit_diagnosis`/`request_spare_parts`". Đúng cho `submitDiagnosis` (2-key) NHƯNG **SAI cho `request_spare_parts`**: service THẬT trả **4-key** `{name, status, updated, allocation}` (`services/imm09.py:1018-1019`) — `updated` (số row gắn được `stock_entry_ref`, `:982`) + `allocation` (name `IMM Spare Allocation` Gate-2 IMM-15, str\|None `:992,1013`).
3. **Self-Correction #2 — premise "flip bare→`methods=['POST']`" đã STALE.** Acceptance ghi flip decorator `request_spare_parts` bare→POST. NHƯNG `git show HEAD:assetcore/api/imm09.py` cho thấy decorator **đã là `@frappe.whitelist(methods=["POST"])`** (committed vòng trước, `api/imm09.py:77`). ⇒ `requestSpareParts` là **CLEAN POST** (mirror `closeIncident` §8.16 / `confirmInspection` §8.20), KHÔNG verb-divergence.
4. **Dual cap-gate `requestSpareParts`.** api-level `repair.write` (`api/imm09.py:79`) + service-level `repair.create` (`services/imm09.py:973`) — đều in-handler cap-403, đều phủ bởi nhánh Error 200-oneOf.

## Decision

**(1) `searchSpareParts` — GET RAW-list, no-pagination, slot `{200,401}` no-403.** Thêm 1 path `GET /api/method/assetcore.api.imm09.search_spare_parts` opId `searchSpareParts`. `SearchSparePartsEnvelope` closed `required[success,data]`, `success enum[true]`; `data` = **array `<SearchSparePartItem>` TRẦN** (KHÔNG `{...,items}`/pagination — `_ok(list)` `api/imm09.py:125`). `SearchSparePartItem` `additionalProperties:false` **EXACT 10 prop** `{item_code, item_name, manufacturer_part_no, qty, uom, unit_cost, total_cost, stock_entry_ref, notes, idx}` `required[item_code]` (grounded `services/imm09.py:1237-1246`) — **0 boolean/Check field** ⇒ 0 prop `integer enum[0,1]` (Open#1; `qty`/`idx` integer, `unit_cost`/`total_cost` number). 200 = oneOf `[SearchSparePartsEnvelope, Error]` route-by-VALUE `body.success` (0 discriminator). Param `query` (string required) + `limit` (integer default 10). `[]` rỗng hợp lệ (query<2 / no-match — KHÔNG 404). **Slot `{200,401}` — KHÔNG 403** (no api-level cap-gate; mirror `getUserContext` ADR-MOBILE-008 §exempt). `searchSpareParts` **∉ `_MVP_BUSINESS_PATHS`** (read-only no-cap-gate picker) — typed-200 oneOf phủ bởi guard riêng `TestMobileSearchSparePartsContract`.

**(2) `requestSpareParts` — schema RIÊNG `RequestSparePartsResponse` 4-key (C3-split, KHÔNG reuse `RepairActionResponse`).** Thêm 1 path `POST /api/method/assetcore.api.imm09.request_spare_parts` opId `requestSpareParts`. `RequestSparePartsResponse` closed `additionalProperties:false` **EXACT 4 prop** `{name string, status string, updated integer, allocation (string\|null nullable)}` `required[name,status]` (grounded `services/imm09.py:1018-1019`). `status` enum = RepairStatus-canonical 9-state, post-request = `In Repair` (nếu rời `Pending Parts`) hoặc giữ nguyên. `updated` = **GENUINE integer count** (số row gắn `stock_entry_ref`, KHÔNG enum[0,1]). `allocation` = `type:string nullable:true` (name allocation Gate-2 hoặc `null`). 200 = oneOf `[RequestSparePartsEnvelope, Error]` route-by-VALUE (0 discriminator). **KHÔNG reuse `RepairActionResponse` 2-key** (precedent `ResolveIncidentResponse`/`AssignTechnicianResponse` — action-success thêm field-thứ-ba ⇒ schema RIÊNG). `requestSpareParts` **∈ `_MVP_BUSINESS_PATHS`** (cap-gated write) ⇒ 401∧403 symmetry tự cân.

**(3) `requestBody` `requestSpareParts` — `oneOf[json, x-www-form]`, `parts` nested item.** `RequestSparePartsRequest` closed `additionalProperties:false` `required[name, parts]` — `name string`; `parts array<RequestSparePartItem>`. content **oneOf** `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict`; `parts` gửi JSON-array, BE `parse_json` string `api/imm09.py:80`). `RequestSparePartItem` `additionalProperties:false` props `{item_code string, stock_entry_ref string opt, spare_part string opt, qty number opt}` `required[item_code]` (grounded `services/imm09.py:980-997`). `parts` có default `"[]"` ở signature NHƯNG contract khai required (sub-flow luôn gửi ≥1 part).

**(4) CLEAN POST — KHÔNG verb-divergence, `_PARITY_VERB_ALLOWLIST` GIỮ `set()` rỗng.** `request_spare_parts` đã `@frappe.whitelist(methods=['POST'])` SẴN @source (HEAD-committed `api/imm09.py:77`) ⇒ contract POST khớp source POST-only, KHÔNG lệch. **KHÔNG** vào `_PARITY_VERB_ALLOWLIST` (allowlist chỉ dành bare-`@whitelist` write-action chờ fix — `submit_pm_result`/`submit_calibration` §8.14/§8.15). Verb-parity sweep yaml↔handler zero-exception giữ NGUYÊN sau khi thêm path POST mới. Guard TC-a assert POST-ONLY (khớp source — KHÔNG anti-false-green).

**(5) 403 SINGLE-SHAPE + slot — `requestSpareParts {200,401,403}`, `searchSpareParts {200,401}`.** `requestSpareParts`: 403 = SINGLE-SHAPE `Forbidden` (`$ref components/responses/Forbidden`) = dispatcher-403 (guest/no-token trip TRƯỚC `handle()`); in-handler cap-403 (`repair.write`+`repair.create`) đã PHỦ bởi nhánh Error 200-oneOf → slot 403 KHÔNG schema mới (mirror `startRepair`/`closeIncident`). `searchSpareParts`: KHÔNG 403 (no api-level cap-gate). 401 = `Unauthorized401` SINGLE-SHAPE cả 2.

**(6) `IMM09_NOT_FOUND` (404) Error-on-HTTP-200 cho `requestSpareParts` (ARRIVE nhánh Error, KHÔNG status-line).** WO∄ → `nthrow(MSG.IMM09_NOT_FOUND, name=name)` (`services/imm09.py:975-976`) ⇒ Error `code=NOT_FOUND http_status=404`, đến trên HTTP-200 (quirk §5). Client route theo `body.http_status` ∈ bounded enum {400,401,403,404,409,413,422,429,500} (R11). KHÔNG mở schema/slot mới. `searchSpareParts` KHÔNG có in-handler business-error (chỉ trả `[]` cho query<2 / no-match — KHÔNG 404).

## Alternatives (rejected)

- **(a) `searchSpareParts` data bọc `{query, items}`** (như `getAssetIncidentHistory {asset,items}`) — svc THẬT trả list trần, thêm wrapper = lệch source + drift codegen. Loại.
- **(b) `searchSpareParts` thêm pagination `{page,page_size,total}`** — svc không paginate (chỉ `limit` cap), bịa `total` = sai. Loại.
- **(c) `searchSpareParts` khai slot 403 / vào `_MVP_BUSINESS_PATHS`** — handler KHÔNG `rbac.require` ⇒ không in-handler cap-403; khai 403 = phantom; vào `_MVP_BUSINESS_PATHS` ép 401∧403 symmetry → vỡ (mirror `getUserContext` no-403). Loại.
- **(d) `requestSpareParts` reuse `RepairActionResponse` 2-key** — DROP `updated`+`allocation`, client mất tín-hiệu "gắn mấy dòng" + "allocation Gate-2 nào" → thừa re-fetch + lệch source 4-key (Self-Correction #1). Loại.
- **(e) flip decorator `request_spare_parts` bare→POST round này** — đã POST-only @source (Self-Correction #2), flip = no-op + vi phạm PURE-YAML. Loại.
- **(f) đưa `requestSpareParts` vào `_PARITY_VERB_ALLOWLIST`** — allowlist chỉ cho bare-`@whitelist` write-action chờ fix; request đã CLEAN POST ⇒ giữ `set()` rỗng. Loại.
- **(g) khai status-line 404 cho `requestSpareParts`** — lỗi nghiệp vụ in-handler arrive HTTP-200 + Error (route `body.http_status`), KHÔNG status-line (quirk §5). Loại.

## Consequences

- Mobile đóng **sub-flow vật-tư** repair: `searchSpareParts` (picker) → `requestSpareParts` (gắn phiếu) → rời `Pending Parts` → `In Repair`. `searchSpareParts` có đích tiêu-thụ rõ (feed picker cho `requestSpareParts.parts[].item_code`).
- Path/opId 40→42 (`searchSpareParts` 41, `requestSpareParts` 42). `info.version` GIỮ `0.1.0-skeleton`. 0 dangling `$ref`.
- Codegen sinh: `searchSpareParts(query, limit?)` → `List<SearchSparePartItem>`; `requestSpareParts(name, parts)` → `RequestSparePartsResponse` (đọc `updated`/`allocation`).
- `RepairActionResponse` (§8.11) nay chỉ còn đúng forward-reserve cho action 2-key thuần (`submitDiagnosis`) — Self-Correction #1 thu hẹp phạm vi reservation.
- **0 đụng `.py`** (PURE-YAML cho cả 2 — search bare GET untouched; request đã POST-only @HEAD untouched; `git diff api/imm09.py` cho 2 hàm = empty). Sau USER reload gunicorn `--preload` → LIVE reject GET(405) cho `request_spare_parts`; trước reload stale worker còn nhận GET — **KHÔNG curl-verify LIVE** (LL-DEPLOY-07). KHÔNG reload/migrate/commit (HARD-STOP USER).
- Guard: `TestMobileSearchSparePartsContract` + `TestMobileRequestSparePartsContract` (mỗi class a..i; RED-before chứng minh cho TC mới). Re-baseline `test_oas_d12/d15/d17` get/post count **theo số LIVE @source** (1 path POST mới `request_spare_parts` đã POST-only @HEAD ⇒ KHÔNG verb-flip runtime; số đếm static-path đổi — re-verify @source, KHÔNG tin tuyệt đối acceptance). `test_imm09` no-regress.

---

## Liên kết

- ADR-MOBILE-006 — POST-action route-by-VALUE + 403 SINGLE-SHAPE (mẫu kế thừa).
- ADR-MOBILE-008 — `getUserContext` slot `{200,401}` no-403 cho path no-cap-gate (precedent `searchSpareParts`).
- ADR-MOBILE-009 — `confirmInspection` C3-split cross-ACTION + clean POST (precedent schema-RIÊNG + CLEAN POST).
- Core Doc IMM-09: `docs/imm-09/04_Backend_Design.md §3.5` (ADR-IMM09-SPARE-SEARCH + ADR-IMM09-REQUEST-PARTS) · `docs/imm-09/05_API_Specification.md §3.6/§3.13`.
- Contract: `04-api-contract.md §8.22` (`searchSpareParts`) + `§8.23` (`requestSpareParts`).
