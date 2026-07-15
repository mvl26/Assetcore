# ADR-MOBILE-046 — `createTransfer` (**CREATE / CR-TRANSFER-CREATE-01 · transfer CREATE-action ĐẦU TIÊN** — curate 1 path POST TẠO phiếu yêu cầu điều chuyển thiết bị (`∅ → Pending Approval`) vào OAS mirror; **HOÀN TẤT transfer write-action quartet** (`receiveTransfer` ADR-043 / `approveTransfer` ADR-044 / `rejectTransfer` ADR-045 / create); **FIRST transfer CREATE-action** — sinh record MỚI, **0 name-param đầu vào** (handler đọc `frappe.local.form_dict`, chữ-ký 0-param @`api/imm00.py:2124`); **ĐIỂM KHÁC CỐT-LÕI #1: request RICHEST 4-required + 5-optional = 9 prop** (`asset`/`transfer_type`/`to_department`/`reason` required @`services/imm00.py:2574` + 5 optional) — `from_location`/`from_department`/`from_custodian` **SERVER auto-derive** từ asset hiện tại @`:2592-2594` (**KHÔNG** khai trong request); **ĐIỂM KHÁC CỐT-LÕI #2: `∈ _MVP_CREATE_ENVELOPE`** (create-action mirror `createRepairWorkOrder`/`createCalibration`) — KHÁC receive/approve/reject `∈ _MVP_ACTION_ENVELOPE`; **ĐIỂM KHÁC CỐT-LÕI #3: 403 SINGLE `Forbidden` dispatcher-ONLY** (0 cap-403 — handler+service KHÔNG `rbac.require`; mirror `receiveTransfer` ADR-043, KHÁC `approveTransfer`/`rejectTransfer` cap-403 REACHABLE); response 2-prop `{name,status}` status enum single-value `['Pending Approval']` GROUNDED verbatim hằng `_TRANSFER_STATUS_PENDING` @`:2561`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-046 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-14 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **ADR-MOBILE-021** (TRANSFER-READ-WIRE — `getTransfer`/`listTransfers` READ điều chuyển, tag `asset`, 4 schema Transfer\*) · **ADR-MOBILE-043 §8.45 `receiveTransfer`** (write-action ĐẦU TIÊN domain Điều chuyển — **403 dispatcher-only**, 422-uniform; createTransfer đối xứng receive về mặt 403-slot) · **ADR-MOBILE-044 §8.46 `approveTransfer`** + **ADR-MOBILE-045 §8.47 `rejectTransfer`** (write-action #2/#3 — cap-403 REACHABLE) · **`_MVP_CREATE_ENVELOPE` create-action pattern** (`createRepairWorkOrder`/`createCalibration` — sinh record mới) · Core Doc IMM-00 [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §create_transfer mobile-binding |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (grep @2026-07-14): handler `assetcore/api/imm00.py` `create_transfer()` def@**2124** (`@frappe.whitelist(methods=["POST"])` @**2123** no-`allow_guest` → guest dispatcher-403; **signature 0-param** — đọc `data = {k: v for k, v in frappe.local.form_dict.items() if k not in ("cmd", "doctype")}` @**2126**; `try: return _ok(create_transfer_request(data))` @**2128** / `except frappe.exceptions.ValidationError as e: return _err(str(e), 422)` @**2130**); service `assetcore/services/imm00.py` `create_transfer_request(data: dict)` def@**2568** (`required = ("asset", "transfer_type", "to_department", "reason")` @**2574**; `missing = [f for f in required if not data.get(f)]; if missing: frappe.throw(_("Thiếu trường bắt buộc: {0}").format(...))` @**2575-2577**; `if not frappe.db.exists(_DOCTYPE_ASSET, asset_name): frappe.throw(_("Thiết bị '{0}' không tồn tại").format(asset_name))` @**2580-2581**; `prev = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, ["location","department","custodian"], as_dict=True)` @**2583-2586** → `doc.from_location = prev.get("location")` / `doc.from_department = prev.get("department")` / `doc.from_custodian = prev.get("custodian")` @**2592-2594** — **SERVER auto-derive, KHÔNG nhận client**; `doc.status = _TRANSFER_STATUS_PENDING` @**2601**; `doc.insert(ignore_permissions=False)` @**2602**; `_notify_transfer_approvers(doc)` @**2603**; `log_audit_event(asset=asset_name, event_type="Transfer", ...)` @**2604-2609**; `frappe.db.commit()` @**2610**; **`return {"name": doc.name, "status": doc.status}` @2612 — EXACT 2-key**); hằng `_TRANSFER_STATUS_PENDING = "Pending Approval"` `services/imm00.py:2561` (Select `asset_transfer.json` `status` 5-state). ⚠️ handler+service **KHÔNG** `rbac.require` (0 cap-403 in-handler). Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.48 `createTransfer`).

---

## Context

Module IMM-00 (master/registry) surface domain **Điều chuyển thiết bị** (Asset Transfer) — vòng đời phiếu: **`∅` (tạo)** → `Pending Approval` → `Approved` (duyệt) / `Rejected` (từ chối) → `Received` / `Cancelled`. READ-surface (`getTransfer`/`listTransfers`) đã curate (ADR-021); 3 write-action đã curate: `receiveTransfer` (`Approved → Received`, ADR-043 — MỞ NHÁNH), `approveTransfer` (`Pending Approval → Approved`, ADR-044 — #2), `rejectTransfer` (`Pending Approval → Rejected`, ADR-045 — #3). Còn **cửa VÀO vòng đời — tạo phiếu** (`∅ → Pending Approval`): màn "Điều chuyển" luồng KHỞI TẠO (feature-12) có nút "Tạo phiếu điều chuyển" nhưng vẫn **dead-end** vì codegen client mobile không sinh method `createTransfer`.

`createTransfer` là **CREATE-action ĐẦU TIÊN** của domain Điều chuyển (KHÁC 3 write-action trước — đều là action-on-existing trên phiếu ĐÃ tồn tại): người dùng chọn thiết bị + phòng ban đích + lý do → hệ thống **sinh phiếu MỚI** `status = Pending Approval` (từ vị trí nguồn auto-derive) + notify người duyệt + audit. Endpoint `imm00.create_transfer` **ĐÃ LIVE** @`api/imm00.py:2124` (`@whitelist(methods=["POST"])`, đọc `form_dict`, `try _ok(create_transfer_request(data)) / except ValidationError → _err(…, 422)`) + service `create_transfer_request(data)` @`services/imm00.py:2568` (return EXACT 2-key `{name, status}` @2612).

Vòng này **curate 1 path POST** `create_transfer` vào `assetcore-mobile.openapi.yaml` (đóng CR-TRANSFER-CREATE-01) — **HOÀN TẤT transfer write-action quartet** (read + receive + approve + reject + create). **CONTRACT-ONLY**: `create_transfer` (7 dòng) + `create_transfer_request` (45 dòng) **byte-identical HEAD↔working** (AST-extract 2 vùng so-khớp byte round này — BE LIVE trong-tree), KHÔNG đụng `.py` ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

**⚠️ ĐIỂM KHÁC CỐT-LÕI #1 — CREATE (sinh record MỚI) — 0 name-param đầu vào + request RICHEST 4-req+5-opt, `from_*` SERVER auto-derive:**

3 write-action trước (`receive`/`approve`/`reject`) là **action-on-existing**: nhận `name` = khoá phiếu ĐÃ tồn tại (+ payload phụ). `createTransfer` là **CREATE**: KHÔNG có `name` đầu vào (server sinh naming-series `AT-.YYYY.-.####`). Handler `create_transfer()` **0-param** — đọc `frappe.local.form_dict` @`:2126` (RPC form_dict pattern) → `create_transfer_request(data)`. Request là RICHEST của transfer family: **4 field BẮT BUỘC** (`asset`/`transfer_type`/`to_department`/`reason` — `required` tuple @`:2574`, `frappe.throw 'Thiếu trường bắt buộc'` @`:2577` nếu thiếu) + **5 field optional** (`to_location`/`to_custodian`/`expected_return_date`/`notes`/`transfer_date`). ⚠️ **`from_location`/`from_department`/`from_custodian` KHÔNG khai trong request** — service **auto-derive** từ vị trí HIỆN TẠI của asset (`prev.get("location"/"department"/"custodian")` @`:2592-2594`); khai chúng = cho client gán vị trí NGUỒN giả (drift + lỗ bảo mật). Contract `CreateTransferRequest.required = [asset, transfer_type, to_department, reason]`, `properties` EXACT 9, `additionalProperties:false` (đóng — 3 `from_*` bị chặn). ⚠️ handler 0-param ⇒ **KHÔNG sig-parity request-props** (KHÁC receive/reject); TC-i grounding request qua **required-tuple @source** (`inspect.getsource(create_transfer_request)` assert verbatim tuple).

**⚠️ ĐIỂM KHÁC CỐT-LÕI #2 — `∈ _MVP_CREATE_ENVELOPE` (create-action) — KHÁC receive/approve/reject `∈ _MVP_ACTION_ENVELOPE`:**

3 write-action trước là transition-on-existing ⇒ `∈ _MVP_ACTION_ENVELOPE`. `createTransfer` **sinh record top-level mới** ⇒ `∈ _MVP_CREATE_ENVELOPE` (mirror `createRepairWorkOrder`/`createCalibration`/`reportIncident`/`createPmWorkOrder` — 4 create-action hiện có). ⚠️ **TÊN ENVELOPE RÚT-GỌN `CreateTransferEnvelope`** (mirror `ReceiveTransferEnvelope` transfer-family) — **KHÔNG** `CreateTransferCreatedEnvelope` (create-family `...CreatedEnvelope`): cohesion 4 sibling transfer (`Receive`/`Approve`/`Reject`/`Create`TransferEnvelope) thắng convention create-family. Sweep `_codegen_dry_introspect` @`test_mobile_oas.py:9579` chỉ so **ref-string** trong 200-oneOf (KHÔNG ép substring `Created`) ⇒ tên rút-gọn PASS. TC-h assert `∈ _MVP_CREATE_ENVELOPE` ∧ `∉ _MVP_ACTION_ENVELOPE` (phân-biệt create vs action).

**⚠️ ĐIỂM KHÁC CỐT-LÕI #3 — 403 SINGLE `Forbidden` DISPATCHER-ONLY (0 cap-403) — mirror `receiveTransfer`, KHÁC `approve`/`reject` cap-403 REACHABLE:**

`create_transfer` handler + `create_transfer_request` service **KHÔNG** gọi `rbac.require` ⇒ **0 in-handler cap-403**. 403-slot CHỈ giữ **dispatcher-403** (guest/no-token, POST `@whitelist` no `allow_guest` → Frappe dispatcher raise `PermissionError` → HTTP-403 status-line THẬT + `FrappeRawError` shape). Đối xứng `receiveTransfer` (ADR-043 dispatcher-only), **KHÁC** `approveTransfer`/`rejectTransfer` (CÓ `rbac.require('commissioning.submit')` → cap-403 REACHABLE). op.description GHI RÕ **`dispatcher-only`** + **`0 cap-403`** (chống nhầm createTransfer là cap-gated). *(Ghi chú: `doc.insert(ignore_permissions=False)` @`:2602` vẫn kiểm DocPerm create trên Asset Transfer — nếu thiếu, raise `PermissionError` cũng ESCAPE `except-ValidationError` → dispatcher HTTP-403; nhưng đó là DocPerm-403 dispatcher-style, CÙNG shape `Forbidden`, KHÔNG phải in-handler cap-403 HTTP-200 ⇒ 403-slot VẪN SINGLE `Forbidden`.)*

**⚠️ Cùng transport 3 write-action transfer — KHÁC shape/semantics:** cả 4 là **write json+form body** (2 media-type `application/json` + `application/x-www-form-urlencoded`, Frappe RPC `form_dict` §9 — KHÔNG multipart). NHƯNG:
- `receiveTransfer`: action-on-existing · req`[name]` + `handover_notes` OPTIONAL · Response `{name,status,received_by}` 3-key · **0 cap-403 (dispatcher-only)** · `_MVP_ACTION_ENVELOPE`.
- `approveTransfer`: action-on-existing · req`[name]` 0-optional · Response `{name,status}` 2-key · **cap-403 REACHABLE** · `_MVP_ACTION_ENVELOPE`.
- `rejectTransfer`: action-on-existing · req`[name, rejection_reason]` · Response `{name,status}` 2-key · **cap-403 REACHABLE** · `_MVP_ACTION_ENVELOPE`.
- `createTransfer`: **CREATE (∅→Pending)** · **0 name-param** · req **4-required + 5-optional = 9 prop** (`from_*` server-derive KHÔNG khai) · Response `{name,status}` 2-key status `['Pending Approval']` · **0 cap-403 (dispatcher-only, mirror receive)** · **`_MVP_CREATE_ENVELOPE`** (mirror createRepair/createCalibration).

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `create_transfer()` — POST-only whitelist 0-param (form_dict), Decision-B oneOf
- `@frappe.whitelist(methods=["POST"])` @2123 — **POST-only**, **KHÔNG `allow_guest`** ⇒ guest/no-token → **dispatcher-403**.
- `data = {k: v for k, v in frappe.local.form_dict.items() if k not in ("cmd", "doctype")}` @2126 — đọc form_dict (RPC pattern), loại `cmd`/`doctype`.
- `try: return _ok(create_transfer_request(data))` @2128 / `except frappe.exceptions.ValidationError as e: return _err(str(e), 422)` @2130 ⇒ lỗi nghiệp vụ (service `frappe.throw`) → **Decision-B HTTP-200 + Error envelope** `http_status=422`.
- Service @`imm00.py:2568` `return {"name": doc.name, "status": doc.status}` @2612 (EXACT **2-key**, `status = _TRANSFER_STATUS_PENDING = "Pending Approval"`) → `_ok` → `{"success":true,"data":{name,status}}`. ⇒ 200 = **oneOf [`CreateTransferEnvelope`, `Error`]**.

### Ladder lỗi nghiệp vụ in-handler (2 nhánh — CẢ HAI → 422 ĐỒNG NHẤT qua ValidationError)

| # | Nhánh @source (`services/imm00.py`) | mechanism | http_status |
|---|---|---|---|
| 1 | `missing = [f for f in required if not data.get(f)]; if missing: frappe.throw("Thiếu trường bắt buộc: {0}")` @2575-2577 — thiếu 1 trong 4 field required | `frappe.throw` → `ValidationError` | **422** (handler `_err(str(e),422)` @2130 — **KHÔNG 404**) |
| 2 | `not frappe.db.exists(_DOCTYPE_ASSET, asset_name): frappe.throw("Thiết bị '{0}' không tồn tại")` @2580-2581 — asset∄ | `frappe.throw` → `ValidationError` | **422** (handler `_err(str(e),422)` @2130 — **KHÔNG 404**, KHÁC `getTransfer` 404 tường minh) |

⇒ `Error.http_status` ⊇ **{422}** ĐỒNG NHẤT (2 nhánh, CẢ HAI 422; ARRIVE HTTP-200 body qua `_err` — route theo `body.http_status`). **KHÔNG có 404** (mirror `receiveTransfer` ADR-043 422-uniform, KHÁC `getTransfer`).

### Side-effect success (audit) — contract KHÔNG khai (thuộc service)
`doc.from_* = prev.get(...)` @2592-2594 (auto-derive vị trí nguồn) → `doc.status = "Pending Approval"` @2601 → `doc.insert(ignore_permissions=False)` @2602 → `_notify_transfer_approvers(doc)` @2603 → `log_audit_event(asset, event_type="Transfer", ref_doctype="Asset Transfer", ...)` @2604-2609 (SINH IMM Audit Trail) → `frappe.db.commit()` @2610. Contract này CHỈ khai request/response shape.

## Decision

**Curate 1 path POST GROUNDED 1:1 `imm00.create_transfer`, requestBody 2 media-type (json + x-www-form-urlencoded) cùng `$ref CreateTransferRequest`, 200 = oneOf [`CreateTransferEnvelope`, `Error`] (Decision-B route-by-VALUE 0-discriminator), 403 = SINGLE-SHAPE `Forbidden` **dispatcher-ONLY** (0 cap-403), slot `{200,401,403}`.** Tag **`asset`** (parity transfer family). Path-count **73→74**, opId **73→74** (đếm thật, DUY NHẤT, camelCase). Đặt path SAU `rejectTransfer` (transfer family). CONTRACT-ONLY (pure-yaml).

1. **`createTransfer`** — `POST /api/method/assetcore.api.imm00.create_transfer` › `operationId: createTransfer` (dotted-path tail §8.1, camelCase, UNIQUE). Tag **`asset`**. **POST-only** (`@whitelist(methods=["POST"])` @2123, ∉ `_PARITY_VERB_ALLOWLIST`); ⚠️ handler **0-param** (`inspect.signature(imm00.create_transfer) == ∅` — đọc form_dict). 200 = `oneOf [CreateTransferEnvelope, Error]`. slot `{200,401,403}`.

2. **requestBody = 2 media-type** (`required: true`; **`application/json` + `application/x-www-form-urlencoded`** — CÙNG `$ref CreateTransferRequest`; Frappe RPC `form_dict` §9). **KHÔNG multipart**.

3. **`CreateTransferRequest`** — CLOSED (`additionalProperties: false`), `required: [asset, transfer_type, to_department, reason]` (**4 bắt buộc** — `required` tuple @2574), `properties` EXACT **9** (4 req + 5 optional):

   | prop | required | type | ground |
   |---|---|---|---|
   | `asset` | ✅ | string | Link Asset — thiết bị điều chuyển. @2574; asset∄ → 422 @2581 |
   | `transfer_type` | ✅ | string | Select `asset_transfer.json`. @2574 |
   | `to_department` | ✅ | string | Link AC Department — phòng ban đích. @2574 |
   | `reason` | ✅ | string | lý do điều chuyển. @2574 |
   | `to_location` | — | string | Link AC Location — vị trí đích. `data.get("to_location")` @2595 |
   | `to_custodian` | — | string | Link User — người phụ trách đích. `data.get("to_custodian")` @2597 |
   | `expected_return_date` | — | string (`format:date`) | ngày dự kiến trả. `data.get(...)` @2598 |
   | `notes` | — | string | ghi chú. `data.get("notes")` @2600 |
   | `transfer_date` | — | string (`format:date`) | ngày lập. `data.get("transfer_date") or nowdate()` @2586 |

   *(ANTI-DRIFT: `from_location`/`from_department`/`from_custodian` **∉ properties** — SERVER auto-derive từ asset hiện tại @2592-2594 (`additionalProperties:false` chặn client gửi). TC-c assert 3 field này ∉ props + required EXACT 4 + props EXACT 9 + grounding required-tuple verbatim @source.)*

4. **`CreateTransferResponse`** (data) — CLOSED (`additionalProperties: false`), `required: [name, status]` EXACT **2 prop** (GROUNDED `return {"name","status"}` @2612):

   | prop | type | ground |
   |---|---|---|
   | `name` | string | mã phiếu MỚI tạo (naming AT-.YYYY.-.####; `doc.name` @2612) |
   | `status` | **string enum `['Pending Approval']`** | `_TRANSFER_STATUS_PENDING` @2601,2612 (`services/imm00.py:2561` = `"Pending Approval"`). **Giá-trị TẠO LUÔN `"Pending Approval"`** (state khởi-tạo deterministic) ⇒ **enum single-value `['Pending Approval']` GROUNDED verbatim hằng** `_TRANSFER_STATUS_PENDING` (anti-bịa; TC-e import hằng LIVE assert equality) |

   *(ANTI-DRIFT: response EXACT 2-key `{name, status}` — **KHÔNG `from_*`/`to_*`/`approved_by`/`received_by`/`rejected_by`** (return @2612 CHỈ 2-key).)*

5. **`CreateTransferEnvelope`** — CLOSED (`additionalProperties: false`), `required: [success, data]`; `success.enum: [true]`; **`data` = `$ref CreateTransferResponse`**. **Tên RÚT-GỌN `CreateTransferEnvelope`** (mirror `ReceiveTransferEnvelope` transfer-family, KHÔNG `...CreatedEnvelope`). Nhánh success của 200-oneOf; disjoint required-set với `Error` ⇒ máy-đọc phân-biệt bằng CLOSED-SCHEMA (KHÔNG discriminator — §5c).

6. **200 = `oneOf [CreateTransferEnvelope, Error]`** — Decision-B route-by-VALUE (`body.success` enum[true] vs [false] + `body.http_status`), 0 discriminator. Nhánh `Error` gom **2 nhánh** service (missing-required + asset∄, CẢ HAI 422) ARRIVE HTTP-200.

7. **403 = SINGLE-SHAPE `Forbidden` dispatcher-ONLY** (`$ref #/components/responses/Forbidden`, `FrappeRawError`). `create_transfer` **KHÔNG `rbac.require`** ⇒ 0 in-handler cap-403 ⇒ 403-slot CHỈ giữ dispatcher-403 (guest/no-token). Note dispatcher-only + `0 cap-403` ghi op.description (mirror `receiveTransfer` ADR-043, **KHÁC `approveTransfer`/`rejectTransfer` cap-403 REACHABLE**). **401 = `Unauthorized401`**.

### Naming guard (∅)
`CreateTransfer{Request,Response,Envelope}` ∩ mọi schema hiện có == ∅ (grep verify 0 collision) — prefix `CreateTransfer` ≠ `ReceiveTransfer` ≠ `ApproveTransfer` ≠ `RejectTransfer` ≠ `Transfer` ⇒ KHÔNG đụng `Transfer*` (READ) / 3 sibling write-action / `SendToLab*` / `CancelCalibration*`. Schema RIÊNG (C3-split — dù `{name,status}` cùng field-set với Approve/Reject, `status.enum` khác `['Pending Approval']`).

**Tag `asset` (grounded):** `getTransfer`/`receiveTransfer`/`approveTransfer`/`rejectTransfer` (transfer family) đều tag `asset`@yaml ⇒ `createTransfer` = **`asset`** (đối xứng domain).

**Phạm vi membership-set (test_mobile_oas):** path ∈ `_MVP_BUSINESS_PATHS` (→ 401/403 symmetry auto +1) · **∈ `_MVP_CREATE_ENVELOPE`** (CREATE sinh record mới; envelope RIÊNG; `createTransfer → CreateTransferEnvelope`) · **∉ `_MVP_ACTION_ENVELOPE`** · **POST-only-at-source ∉ `_PARITY_VERB_ALLOWLIST`** · **∈ `_REQBODY_PATHS`** (json+form) · `_EXPECTED` += dotted-path entry `("post","createTransfer")`. **CONTRACT-ONLY**: `create_transfer` (7 dòng) + `create_transfer_request` (45 dòng) = **byte-identical HEAD↔working** (AST-extract so-khớp byte) ⇒ KHÔNG reload gunicorn, KHÔNG migrate — là **[AUTO]**. 73 path hiện-hữu byte-identical.

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | requestBody `multipart/form-data` | SAI transport: `create_transfer` đọc `form_dict` (json/form-urlencoded). CREATE state-machine KHÔNG upload. RPC-form json+form ĐÚNG (mirror 3 write-action transfer). |
| B | khai `from_location`/`from_department`/`from_custodian` trong request | SAI @source + LỖ BẢO MẬT: 3 `from_*` **SERVER auto-derive** từ asset hiện tại @2592-2594 (`prev.get(...)`) — KHÔNG nhận client. Khai chúng = cho client gán vị trí nguồn giả (drift + falsify audit). `additionalProperties:false` chặn. |
| C | `∈ _MVP_ACTION_ENVELOPE` (như 3 write-action transfer) | SAI phân-loại: `createTransfer` **sinh record top-level MỚI** (`doc.insert` @2602) ⇒ create-action (mirror `createRepairWorkOrder`/`createCalibration`), KHÔNG transition-on-existing. `∈ _MVP_CREATE_ENVELOPE`. |
| D | Envelope tên `CreateTransferCreatedEnvelope` (create-family `...CreatedEnvelope`) | LOẠI (cohesion): 4 sibling transfer dùng `<Verb>TransferEnvelope` (`Receive`/`Approve`/`Reject`TransferEnvelope). `createTransfer` theo transfer-family → `CreateTransferEnvelope` rút-gọn. Sweep `_codegen_dry_introspect` so ref-string (KHÔNG ép substring `Created`) ⇒ PASS. |
| E | 403 = SINGLE `Forbidden` **REACHABLE cap-branch** (mirror `approve`/`reject`) | SAI @source: `create_transfer` handler + `create_transfer_request` service **KHÔNG** `rbac.require` ⇒ 0 in-handler cap-403 (mirror `receiveTransfer` dispatcher-only). op.description GHI RÕ dispatcher-only + `0 cap-403`. |
| F | `Error.http_status` khai **404** cho asset∄ (mirror `getTransfer` 404) | SAI @source: `create_transfer_request` dùng `frappe.throw` (`ValidationError`) → handler `_err(str(e), **422**)` @2130 — KHÔNG `_err(…, 404)`. CẢ 2 nhánh (missing-required + asset∄) về **422 ĐỒNG NHẤT** (mirror `receiveTransfer`). |
| G | `status` type `string` **plain (KHÔNG enum)** | LOẠI: `status` trả đơn-trị `"Pending Approval"` @2612 GROUNDED hằng `_TRANSFER_STATUS_PENDING` @2561 — acceptance yêu cầu **enum single-value `['Pending Approval']`**. TC-e import hằng LIVE assert equality (anti-bịa). |
| H | TC-i sig-parity request-props (như `receiveTransfer`/`rejectTransfer`) | SAI: handler `create_transfer()` **0-param** (đọc `form_dict`) — KHÔNG có named-param để sig-parity. TC-i assert signature RỖNG + form_dict pattern; grounding request qua **required-tuple @source** (`inspect.getsource`). |
| ✅ I | 1 path POST json+form body, 3 schema RIÊNG (Request req[4]+5-opt=9-prop `from_*` server-derive KHÔNG khai · Response 2-prop `{name,status}` status enum `['Pending Approval']` · Envelope), 200 oneOf [Env, Error], **403 SINGLE `Forbidden` dispatcher-ONLY**, **Error 422-uniform 2-nhánh**, `_MVP_CREATE_ENVELOPE` + `_REQBODY_PATHS`, tag `asset` | Grounded 1:1 source; blast-radius = +1 path +3 schema (PURE-YAML); codegen sinh 1 method tạo-phiếu type-safe + form 4-required → app "Tạo phiếu điều chuyển"; Decision-B intact; 403 dispatcher-only documented; status enum-grounded; 9-prop request + `from_*` server-derive documented; naming-guard ∅; **HOÀN TẤT transfer write-action quartet** (read+receive+approve+reject+create). |

## Consequences

- **(+)** App mobile màn "Điều chuyển" luồng KHỞI TẠO có method `createTransfer` codegen-ready: người dùng chọn thiết bị + phòng ban đích + lý do (+ vị trí/người/ngày optional) → bấm "Tạo phiếu" → sinh phiếu `Pending Approval` (từ vị trí nguồn auto-derive) + notify người duyệt + audit. **HOÀN TẤT transfer write-action quartet** (`receiveTransfer` ADR-043 / `approveTransfer` ADR-044 / `rejectTransfer` ADR-045 / create) — domain Điều chuyển phủ ĐỦ vòng đời mobile (tạo → duyệt/từ chối → tiếp nhận). **CR-TRANSFER-CREATE-01 ĐÓNG.**
- **(+)** Contract GROUNDED 1:1 source — 3 schema RIÊNG VERBATIM (`CreateTransferRequest` `req[4]` + 5-optional = 9-prop, `from_*` server-derive KHÔNG khai; `CreateTransferResponse` EXACT **2-prop** `{name,status}` @2612; `status.enum==['Pending Approval']` GROUNDED hằng `_TRANSFER_STATUS_PENDING` @2561); 403-slot SINGLE `Forbidden` dispatcher-only. **Naming guard:** `CreateTransfer*` ∩ mọi schema == ∅.
- **(+)** **`from_*` server-derive documented** — ĐIỂM KHÁC #1: FIRST transfer CREATE-action; 3 `from_*` auto từ asset hiện tại (KHÔNG nhận client, chống falsify vị trí nguồn). TC-c assert 3 field ∉ props. Người bồi CREATE-action tiếp có template server-derived-field.
- **(+)** **`∈ _MVP_CREATE_ENVELOPE` documented** — ĐIỂM KHÁC #2: create-action (sinh record mới) vs 3 write-action `_MVP_ACTION_ENVELOPE`. Envelope tên rút-gọn transfer-family (`CreateTransferEnvelope`). TC-h assert `∈ _MVP_CREATE_ENVELOPE` ∧ `∉ _MVP_ACTION_ENVELOPE`.
- **(+)** **403 dispatcher-only documented** — ĐIỂM KHÁC #3: mirror `receiveTransfer` (0 cap-403), KHÁC `approve`/`reject`. op.description ghi rõ dispatcher-only + `0 cap-403` (chống nhầm cap-gated).
- **(+)** **`status` enum single-value `['Pending Approval']` GROUNDED verbatim hằng** — typed badge "Chờ duyệt" màn Điều chuyển; TC-e import hằng LIVE `_TRANSFER_STATUS_PENDING` assert equality (chống bịa/drift).
- **(+)** **CONTRACT-ONLY** — `create_transfer` (7 dòng) + `create_transfer_request` (45 dòng) **byte-identical HEAD↔working** (AST-extract 2 vùng so-khớp byte — verified) ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO], KHÔNG HARD-STOP USER); `test_oas_d12/d15/d17` UNCHANGED (pure mobile-yaml). 73 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator; 2 nhánh oneOf disjoint required-set closed-schema); 0 dangling `$ref` (3 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`/`Error`).
- **(−)** **Handler 0-param (form_dict)** — KHÔNG sig-parity request-props như receive/reject. TC-i assert signature RỖNG + form_dict pattern; grounding request qua required-tuple @source (`inspect.getsource(create_transfer_request)` verbatim). Người đọc PHẢI hiểu request-shape ground từ SERVICE (KHÔNG handler signature).
- **(−)** **Response 2-prop cùng field-set Approve/Reject** (KHÔNG reuse — status enum khác `['Pending Approval']`). Người bồi action IMM-00/transfer tiếp PHẢI grep `return {…}` + hằng status @service.
- **(−)** **`transfer_type` type string plain (KHÔNG enum)** — Select `asset_transfer.json` NHƯNG service KHÔNG validate enum (`doc.transfer_type = data["transfer_type"]` trực-tiếp); contract giữ string (không over-constrain khi chưa grounding option-set doctype). *(Cần khảo sát: nếu doctype Select bounded no-blank → có thể formal enum vòng sau, mirror `RepairWorkOrderListItem` ADR-037.)*
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `694→704` (test_mobile_oas, +10 TC class `TestMobileCreateTransferContract` a..j) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `694→704` + `_GUARD_SUITE_SUM` `837→847` + `_MOBILE_OAS_TOTAL` `863→873` + c5 `62→63` + parity `_PARITY_BUSINESS_PATHS` `62→63` + transition-baseline delta-var `create_transfer_wire_delta=10` + ADR balance `45→46`. ⚠️ **secondary count-guard KHÔNG dùng token `, 73,`** (3 c5 62→63 + 1 parity + 4 backward-compat opId-set-minus [pmhist 72→73 / transfer(-new) 71→72 / dept 72→73 / loc 72→73] + 2 hardcoded `_EXPECTED_TEST_COUNT==694` [receivecert_j/cancelcal_j] + `op_id_unique` `len(set(ids))==73` bare) ⇒ **full-suite THẬT bắt sót** (RED-before demo → **102 FAIL** → restore → GREEN).

---

## Handoff BE/Test (Bước-4 — ĐÃ XONG pure-yaml, ATOMIC)

> **CONTRACT-ONLY — ĐÃ HOÀN TẤT vòng Bước-2 (BA tự code+verify pure-yaml full path-add):** TUYỆT ĐỐI KHÔNG đụng `api/imm00.py`/`services/imm00.py` (`create_transfer` @2124 / `create_transfer_request` @2568 ĐÃ LIVE byte-identical HEAD↔working). Không reload/migrate/commit. DoD ĐÃ VERIFY: `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **'Ran 704 OK' THẬT** (RED-before strip-path → **102 FAIL** → restore → GREEN) · `.test_mobile_docset` = **Ran 9 OK** (balance 46==46).

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`) — ĐÃ BỒI: +1 path `POST /api/method/assetcore.api.imm00.create_transfer` (opId `createTransfer`, **tag `asset`**, đặt SAU rejectTransfer); requestBody 2 media-type json+form CÙNG `$ref CreateTransferRequest`; 200 = `oneOf [CreateTransferEnvelope, Error]`; slot `{200,401,403}` (**`403 Forbidden` SINGLE-SHAPE dispatcher-ONLY** — description GHI RÕ dispatcher-only + `0 cap-403` + 2 nhánh 422 missing-required + asset∄). +3 schema (`CreateTransferRequest` closed `req[asset,transfer_type,to_department,reason]` + 5-optional = 9-prop, `from_*` KHÔNG khai · `CreateTransferResponse` closed EXACT `req[name,status]` status enum `['Pending Approval']` · `CreateTransferEnvelope`). Cả 3 `additionalProperties:false`. 0 orphan, 0 dangling.

**(2) test_mobile_oas.py** — ĐÃ BỒI: path/opId `73→74`; `_EXPECTED` += `create_transfer → createTransfer`; path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_CREATE_ENVELOPE` (∉ `_MVP_ACTION_ENVELOPE`); `_EXPECTED_TEST_COUNT` `694→704`; bulk-bump `, 73,`→`, 74,` (150) + bare `73)`→`74)` + secondary guard (c5 62→63 ×3 · parity 62→63 · backward-compat pmhist 72→73 / transfer(-new) 71→72 / dept 72→73 / loc 72→73 · hardcoded `_EXPECTED_TEST_COUNT` 694→704 ×2); +1 TC class `TestMobileCreateTransferContract` (a..j, 10 TC). TC-c assert `required EXACT [asset,transfer_type,to_department,reason]` + props EXACT 9 + `from_*` ∉ props + grounding required-tuple verbatim @source. TC-e import hằng LIVE `_TRANSFER_STATUS_PENDING` assert `status.enum==['Pending Approval']`. TC-g assert 403 dispatcher-only (desc chứa 'dispatcher-only' + '0 cap-403' + 'missing-required' + 'asset') + `422 ∈ Error.http_status`. TC-h assert `∈ _MVP_CREATE_ENVELOPE` ∧ `∉ _MVP_ACTION_ENVELOPE`. TC-i assert handler 0-param (signature RỖNG) + form_dict pattern + required-tuple grounding.

**(3) test_mobile_docset.py** — ĐÃ BỒI: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `694→704` · `_GUARD_SUITE_SUM` `837→847` · `_MOBILE_OAS_TOTAL` `863→873` + transition-baseline delta-var `create_transfer_wire_delta=10` (giữ `pre_fc3_six==191`). ADR-MOBILE-046 registered README (TC-MOB-DOC-02 glob động — balance ADR-on-disk 46 == README-index 46).

**(4) docs narrative** — ĐÃ XONG: `04-api-contract.md` (§8.48 `createTransfer`) + README ADR-row (ADR-MOBILE-046, balance 45→46) + Core Doc [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §create_transfer 📱 mobile-binding.

**Domain Điều chuyển nay có ĐỦ vòng đời mobile: tạo (∅→Pending Approval) → duyệt/từ chối → tiếp nhận — HOÀN TẤT transfer write-action quartet (read + create + approve + reject + receive).**
