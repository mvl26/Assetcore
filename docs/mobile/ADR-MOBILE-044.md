# ADR-MOBILE-044 — `approveTransfer` (**ACTION / CR-TRANSFER-APPROVE-01 · transfer WRITE-action #2** — curate 1 path POST PHÊ DUYỆT phiếu điều chuyển thiết bị vào OAS mirror; **write-action #2 domain Điều chuyển** sau `receiveTransfer` (ADR-043) đã MỞ NHÁNH; `rejectTransfer`/`createTransfer` FORWARD-RESERVE vòng Trục-B kế; **write-ACTION json+form body** như `sendToLab`/`cancelCalibration`/`receiveTransfer`; **1 field bắt buộc** `name` **0 optional** (KHÁC `receiveTransfer` có `handover_notes`); **ĐIỂM KHÁC CỐT-LÕI #1: 403 cap-branch REACHABLE** — `rbac.require('commissioning.submit')` @`services/imm00.py:2620` raise `PermissionError` **NGOÀI** `except-ValidationError` → HTTP-403 status-line THẬT (mirror `sendToLab`/`cancelCalibration`, **KHÁC `receiveTransfer` dispatcher-only-403**); **ĐIỂM KHÁC CỐT-LÕI #2: response 2-prop** `{name,status}` **KHÔNG** echo `approved_by` (KHÁC `receiveTransfer` 3-prop `{name,status,received_by}`); **ANTI-DRIFT 422-uniform** — `Error.http_status` = **422 ĐỒNG NHẤT** cho CẢ not-found LẪN wrong-status (KHÁC `getTransfer` 404 tường minh))

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-044 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-14 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **ADR-MOBILE-021** (TRANSFER-READ-WIRE — `getTransfer`/`listTransfers` READ điều chuyển, tag `asset`, 4 schema Transfer\*) · **ADR-MOBILE-043 §8.45 `receiveTransfer`** (write-action ĐẦU TIÊN domain Điều chuyển — MỞ NHÁNH transfer write-action json+form body) · **ADR-MOBILE-033 §8.39 `cancelCalibration`** (403 SINGLE `Forbidden` **REACHABLE** — cap `rbac.require` raise `PermissionError` → HTTP-403 THẬT; reachability ≠ shape) · Core Doc IMM-00 [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §approve_transfer mobile-binding |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (grep @2026-07-14): handler `assetcore/api/imm00.py` `approve_transfer` def@**2582-2588** (`@frappe.whitelist(methods=["POST"])` @**2582** no-`allow_guest`; **signature `approve_transfer(name)`** — `name` positional-KHÔNG-default (bắt buộc); **0 optional param** — KHÁC `receiveTransfer` `handover_notes`; `try: return _ok(approve_transfer_request(name))` @**2586** / `except frappe.exceptions.ValidationError as e: return _err(str(e), 422)` @**2587-2588**); service `assetcore/services/imm00.py` `approve_transfer_request(name)` def@**2615** (`if not frappe.db.exists(_DT_TRANSFER, name): frappe.throw(_ERR_TRANSFER_NOT_FOUND.format(name))` @**2617-2618**; **`rbac.require(_TRANSFER_APPROVE_CAP)` @2620** — `_TRANSFER_APPROVE_CAP = "commissioning.submit"` @**2559**; `if doc.status != _TRANSFER_STATUS_PENDING: frappe.throw("Phiếu đang ở trạng thái '{0}', không thể phê duyệt")` @**2623-2624**; patch `status=_TRANSFER_STATUS_APPROVED` + `approved_by=session.user` + `approval_date=nowdate()` @**2626-2630**; `transfer_asset(...)` cập vị trí thiết bị NGAY @**2632-2639**; `_notify_transfer_requester(doc, approved=True)` @**2641**; **`return {"name": name, "status": _TRANSFER_STATUS_APPROVED}` @2643 — EXACT 2-key**); hằng `_TRANSFER_STATUS_APPROVED = "Approved"` `services/imm00.py:2562` (Select `asset_transfer.json` `status` 5-state); `rbac.require` @`services/shared/rbac.py:190` (`frappe.throw(msg, frappe.PermissionError)` — raise **`PermissionError`**, KHÔNG `ValidationError`). Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.46 `approveTransfer`).

---

## Context

Module IMM-00 (master/registry) surface domain **Điều chuyển thiết bị** (Asset Transfer) — vòng đời phiếu: `Pending Approval` → **`Approved`** (duyệt) → `Received` (bên NHẬN xác nhận tiếp nhận) / `Rejected` / `Cancelled`. READ-surface (`getTransfer`/`listTransfers`) đã curate (ADR-021), và write-action `receiveTransfer` (`Approved → Received`) đã curate ở vòng trước (ADR-043 — MỞ NHÁNH transfer write-action). Nhưng nút "Phê duyệt" trên màn Điều chuyển (feature-12 luồng DUYỆT) vẫn **dead-end** vì codegen client mobile không sinh method `approveTransfer`.

`approveTransfer` là **write-action #2** của domain Điều chuyển: người có quyền phê duyệt (cap `commissioning.submit`) mở phiếu `Pending Approval` → phê duyệt → `status = Approved` + ghi `approved_by`/`approval_date` + **`transfer_asset(...)` cập vị trí thiết bị NGAY** @2632-2639 (đổi location/department/custodian + SINH Lifecycle Event audit). Endpoint `imm00.approve_transfer` **ĐÃ LIVE** @`api/imm00.py:2582` (`@whitelist(methods=["POST"])`, `try _ok(approve_transfer_request) / except ValidationError → _err(…, 422)`) + service `approve_transfer_request` @`services/imm00.py:2615` (return EXACT 2-key `{name, status}` @2643).

Vòng này **curate 1 path POST** `approve_transfer` vào `assetcore-mobile.openapi.yaml` (đóng CR-TRANSFER-APPROVE-01). `rejectTransfer`/`createTransfer` là 2 action điều-chuyển còn lại — **FORWARD-RESERVE vòng Trục-B kế**. **CONTRACT-ONLY**: `approve_transfer` + `approve_transfer_request` **byte-identical HEAD↔working** (git diff 2 vùng TRỐNG round này — BE LIVE trong-tree), KHÔNG đụng `.py` ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

**⚠️ ĐIỂM KHÁC CỐT-LÕI #1 — 403 cap-branch REACHABLE (KHÁC `receiveTransfer` dispatcher-only):**

`receiveTransfer` KHÔNG `rbac.require` in-handler ⇒ 403 chỉ là dispatcher-403 (guest). NHƯNG `approve_transfer_request` gọi **`rbac.require(_TRANSFER_APPROVE_CAP='commissioning.submit')` @2620** — bên trong service, sau khi kiểm phiếu tồn tại. `rbac.require` @`rbac.py:190` raise **`PermissionError`** (KHÔNG `ValidationError`). Handler `try _ok(approve_transfer_request(name)) except frappe.exceptions.ValidationError` @2587 — `PermissionError` **NGOÀI** phạm vi except-ValidationError ⇒ **KHÔNG bị bắt** ⇒ propagate tới Frappe dispatcher → **HTTP-403 status-line THẬT** (dispatcher-style, KHÔNG HTTP-200 Error). ⇒ 403-slot có **2 nguồn REACHABLE** (dispatcher-403 guest + in-handler cap-403 rbac.require) NHƯNG cả hai đều là HTTP-403 status-line + `FrappeRawError` shape ⇒ 403-slot VẪN **SINGLE `Forbidden`** (reachability ≠ shape — mirror `cancelCalibration` ADR-033). Description GHI RÕ **REACHABLE** + cap `commissioning.submit` (chống nút-chết — app biết gate nút theo capability).

**⚠️ ĐIỂM KHÁC CỐT-LÕI #2 — response 2-prop `{name,status}` (KHÔNG `approved_by`):**

`approve_transfer_request` patch `approved_by=session.user` vào DB @2628 NHƯNG `return {"name": name, "status": _TRANSFER_STATUS_APPROVED}` @2643 CHỈ 2-key — KHÔNG echo `approved_by`. ⇒ `ApproveTransferResponse` EXACT 2-prop, KHÁC `ReceiveTransferResponse` 3-prop (`received_by`). Người bồi action transfer tiếp PHẢI grep `return {…}` @service TRƯỚC khi khai (KHÔNG copy schema anh-em).

**⚠️ ĐIỂM KHÁC CỐT-LÕI #3 — request name-only 0 optional:**

`approve_transfer(name)` signature 1-param (chỉ `name`) — KHÁC `receive_transfer(name, handover_notes="")` 2-param. ⇒ `ApproveTransferRequest` EXACT 1-prop `{name}` required, 0 optional body.

**⚠️ ANTI-DRIFT `Error.http_status` = 422 ĐỒNG NHẤT (uniform, KHÔNG 404):**

`approve_transfer_request` báo lỗi nghiệp vụ bằng **`frappe.throw(...)`**: phiếu∄ @2617-2618 VÀ status≠`Pending Approval` @2623-2624 — CẢ HAI raise `ValidationError`. Handler bắt `except frappe.exceptions.ValidationError → _err(str(e), 422)` @2587-2588 ⇒ **MỌI lỗi nghiệp vụ → HTTP-200 + Error body `http_status=422`** (uniform). KHÁC `getTransfer` (READ cùng domain) dùng `_err(_ERR_TRANSFER_NOT_FOUND, 404)` → 404. ⇒ **`approve_transfer` KHÔNG bao giờ phát 404** — not-found cũng về 422 (mirror `receiveTransfer` ADR-043).

**⚠️ Cùng transport `sendToLab`/`cancelCalibration`/`receiveTransfer` — KHÁC shape:** cả 4 là **write-ACTION json+form body** (2 media-type `application/json` + `application/x-www-form-urlencoded`, Frappe RPC `form_dict` §9 — KHÔNG multipart). NHƯNG:
- `cancelCalibration`: req`[name, reason]` 2 field · Response `{name, status}` 2-key · cap-403 `calibration.cancel` REACHABLE (api-level @197).
- `receiveTransfer`: req`[name]` + `handover_notes` optional · Response `{name, status, received_by}` 3-key · **0 cap-403** (dispatcher-only) · 422-uniform.
- `approveTransfer`: req`[name]` **0 optional** · Response **`{name, status}` EXACT 2-key** (KHÔNG `approved_by`) · status **enum single-value `['Approved']`** · **cap-403 `commissioning.submit` REACHABLE** (service-level @2620, PermissionError NGOÀI except) · **422-uniform** (KHÔNG 404).

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `approve_transfer(name)` — POST-only whitelist, service-level cap-gate, Decision-B oneOf
- `@frappe.whitelist(methods=["POST"])` @2582 — **POST-only**, **KHÔNG `allow_guest`** ⇒ guest/no-token → **dispatcher-403**.
- Handler đi thẳng `try: return _ok(approve_transfer_request(name))` @2586.
- `except frappe.exceptions.ValidationError as e: return _err(str(e), 422)` @2587-2588 ⇒ lỗi nghiệp vụ (service `frappe.throw`) → **Decision-B HTTP-200 + Error envelope** `http_status=422`. **`PermissionError` từ `rbac.require` KHÔNG bị bắt** (NGOÀI except-ValidationError) → dispatcher HTTP-403.
- Service @`imm00.py:2615` `return {"name","status"}` @2643 (EXACT **2-key**, `status = _TRANSFER_STATUS_APPROVED = "Approved"`) → `_ok` → `{"success":true,"data":{name,status}}`. ⇒ 200 = **oneOf [`ApproveTransferEnvelope`, `Error`]** (handler QUA `try/except _err` + service `frappe.throw` ⇒ CÓ nhánh Error).

### Ladder lỗi nghiệp vụ in-handler (2 nhánh — CẢ HAI → 422 ĐỒNG NHẤT qua ValidationError)
`exists(doc)` → `rbac.require(cap)` [→ PermissionError HTTP-403 nếu thiếu quyền] → `status == Pending Approval` → (patch status=Approved + approved_by + approval_date + transfer_asset + notify + commit). `Error.http_status` phủ:

| # | Nhánh @source (`services/imm00.py`) | mechanism | http_status |
|---|---|---|---|
| 1 | `not frappe.db.exists(_DT_TRANSFER, name)` @2617-2618 (`frappe.throw(_ERR_TRANSFER_NOT_FOUND.format(name))`) — phiếu∄ | `frappe.throw` → `ValidationError` | **422** (handler `_err(str(e),422)` @2588 — **KHÔNG 404**) |
| 2 | `doc.status != _TRANSFER_STATUS_PENDING` @2623-2624 (`frappe.throw("Phiếu đang ở trạng thái '{0}', không thể phê duyệt")`) — sai state | `frappe.throw` → `ValidationError` | **422** (handler `_err(str(e),422)` @2588) |

⇒ `Error.http_status` ⊇ **{422}** ĐỒNG NHẤT (2 nhánh, CẢ HAI 422; ARRIVE HTTP-200 body qua `_err` — route theo `body.http_status`). **KHÔNG có 404** (KHÁC `getTransfer`).

### 403 REACHABLE (mobile-BE contract gotcha) — 403-slot ⇒ SINGLE-SHAPE reachability ≠ shape
- **dispatcher-403** = guest/no-token (POST `@whitelist` no `allow_guest`) → Frappe dispatcher raise `PermissionError` → **HTTP-403 status-line THẬT** + `FrappeRawError` shape.
- **cap-403 REACHABLE** = bearer hợp lệ nhưng thiếu cap `commissioning.submit`: `rbac.require(_TRANSFER_APPROVE_CAP)` @2620 (TRONG service, sau exists-check) raise `PermissionError`. Vì handler `except` CHỈ bắt `ValidationError` @2587, `PermissionError` **escape** → dispatcher → **HTTP-403 status-line THẬT** (KHÔNG HTTP-200 Error). ⇒ 403-slot có 2 nguồn REACHABLE nhưng **CÙNG shape** (`FrappeRawError` HTTP-403) ⇒ **1 component `Forbidden` SINGLE-SHAPE**. Mirror `cancelCalibration` §8.39 (ADR-033 — cap-403 REACHABLE via `rbac.require`), **KHÁC `receiveTransfer`** (0 `rbac.require` — dispatcher-only) VÀ **KHÁC `reportIncident` DUAL-403** (dùng `_err(403)`@200). Note REACHABLE + cap ghi trong op.description (chống nút-chết).

### Side-effect success (lifecycle) — contract KHÔNG khai (thuộc service)
`frappe.db.set_value(_DT_TRANSFER, name, {status:"Approved", approved_by:session.user, approval_date:nowdate()})` @2626-2630 → `transfer_asset(asset, to_location, to_department, to_custodian, transfer_doc, actor)` @2632-2639 (cập vị trí thiết bị NGAY + SINH Lifecycle Event) → `_notify_transfer_requester(doc, approved=True)` @2641 → commit. Contract này CHỈ khai request/response shape.

## Decision

**Curate 1 path POST GROUNDED 1:1 `imm00.approve_transfer`, requestBody 2 media-type (json + x-www-form-urlencoded) cùng `$ref ApproveTransferRequest`, 200 = oneOf [`ApproveTransferEnvelope`, `Error`] (Decision-B route-by-VALUE 0-discriminator), 403 = SINGLE-SHAPE `Forbidden` **REACHABLE cap-branch** (`commissioning.submit`), slot `{200,401,403}`.** Tag **`asset`** (parity transfer family — `getTransfer`/`receiveTransfer` cùng tag). Path-count **71→72**, opId **71→72** (đếm thật, DUY NHẤT, camelCase). Đặt path SAU `getTransfer`/`receiveTransfer` (transfer family). CONTRACT-ONLY (pure-yaml).

1. **`approveTransfer`** — `POST /api/method/assetcore.api.imm00.approve_transfer` › `operationId: approveTransfer` (dotted-path tail §8.1, camelCase, UNIQUE). Tag **`asset`** (parity transfer family). **POST-only** (`@whitelist(methods=["POST"])` @2582 — clean POST, ∉ `_PARITY_VERB_ALLOWLIST`); live-sig parity `inspect.signature(imm00.approve_transfer) == {name}` (1-param). 200 = `oneOf [ApproveTransferEnvelope, Error]`. slot `{200,401,403}`.

2. **requestBody = 2 media-type** (`required: true`; **`application/json` + `application/x-www-form-urlencoded`** — CÙNG `$ref ApproveTransferRequest`; Frappe RPC `form_dict` §9, mirror `receiveTransfer`/`sendToLab`). **KHÔNG multipart**.

3. **`ApproveTransferRequest`** — CLOSED (`additionalProperties: false`), `required: [name]` (**1 bắt buộc, 0 optional** — KHỚP signature @2583: `name` positional KHÔNG default; KHÁC `receiveTransfer` handover_notes):

   | prop | type | ground |
   |---|---|---|
   | `name` | string | mã **Asset Transfer** (phiếu `Pending Approval` cần phê duyệt; naming AT-.YYYY.-.####). @2583. **required** |

   *(KHÔNG thêm prop nào — signature 1-param. 0 optional. KHÔNG `enum` field.)*

4. **`ApproveTransferResponse`** (data) — CLOSED (`additionalProperties: false`), `required: [name, status]` EXACT **2 prop** (GROUNDED `return {"name","status"}` @2643):

   | prop | type | ground |
   |---|---|---|
   | `name` | string | echo name phiếu (`name` @2643) |
   | `status` | **string enum `['Approved']`** | `_TRANSFER_STATUS_APPROVED` @2627,2643 (`services/imm00.py:2562` = `"Approved"`). **Giá-trị trả LUÔN `"Approved"`** (state đơn-trị deterministic) ⇒ **enum single-value `['Approved']` GROUNDED verbatim hằng** `_TRANSFER_STATUS_APPROVED` (anti-bịa; TC-e import hằng LIVE assert equality) |

   *(ANTI-DRIFT: response EXACT 2-key `{name, status}` — **KHÔNG `approved_by`** (patch DB @2628 NHƯNG KHÔNG echo trong return @2643); KHÔNG `received_by` (đó là `ReceiveTransferResponse`); KHÔNG `approval_date`/`sent_date`.)*

5. **`ApproveTransferEnvelope`** — CLOSED (`additionalProperties: false`), `required: [success, data]`; `success.enum: [true]`; **`data` = `$ref ApproveTransferResponse`**. Tên RÚT-GỌN `ApproveTransferEnvelope` (mirror `ReceiveTransferEnvelope`). Nhánh success của 200-oneOf; disjoint required-set với `Error` ⇒ máy-đọc phân-biệt bằng CLOSED-SCHEMA (KHÔNG discriminator — §5c).

6. **200 = `oneOf [ApproveTransferEnvelope, Error]`** — Decision-B route-by-VALUE (`body.success` enum[true] vs [false] + `body.http_status`), 0 discriminator. Nhánh `Error` gom **2 nhánh** service (not-found + wrong-status, CẢ HAI 422) ARRIVE HTTP-200.

7. **403 = SINGLE-SHAPE `Forbidden` REACHABLE** (`$ref #/components/responses/Forbidden`, `FrappeRawError`). **2 nguồn REACHABLE** (dispatcher-403 guest + in-handler cap-403 `rbac.require('commissioning.submit')` @2620 → `PermissionError` NGOÀI except → HTTP-403 THẬT), CÙNG shape. Note REACHABLE + cap ghi op.description (mirror `cancelCalibration` ADR-033, **KHÁC `receiveTransfer` dispatcher-only**). **401 = `Unauthorized401`**.

### Naming guard (∅)
`ApproveTransfer{Request,Response,Envelope}` ∩ mọi schema hiện có == ∅ (grep verify 0 collision) — prefix `ApproveTransfer` ≠ `ReceiveTransfer` ≠ `Transfer` ⇒ KHÔNG đụng `Transfer*` (READ) / `ReceiveTransfer*` / `SendToLab*` / `CancelCalibration*`. Schema RIÊNG (KHÔNG reuse `ReceiveTransferResponse` — field-set `{name,status}` ≠ `{name,status,received_by}`).

**Tag `asset` (grounded):** `getTransfer`/`receiveTransfer` (transfer family) đều tag `asset`@yaml ⇒ `approveTransfer` = **`asset`** (đối xứng domain).

**Phạm vi membership-set (test_mobile_oas):** path ∈ `_MVP_BUSINESS_PATHS` (→ 401/403 symmetry auto +1) · ∈ `_MVP_ACTION_ENVELOPE` (POST-action-on-existing; `name` = khoá phiếu ĐÃ tồn tại, mirror `receiveTransfer`; envelope RIÊNG) · **∉ `_MVP_CREATE_ENVELOPE`** · **c5 envelope-map += `approveTransfer → ApproveTransferEnvelope`** (`60→61`, giữ invariant `c5 == _MVP_BUSINESS_PATHS`) · ∈ `_RATE_LIMIT_SOURCE_MAP` (KHÔNG `@rate_limit` @2582 ⇒ VẮNG khỏi `_PATHS_REQUIRE_429`) · **POST-only-at-source ∉ `_PARITY_VERB_ALLOWLIST`** · **∈ `_REQBODY_PATHS`** (json+form) · `_EXPECTED` += dotted-path entry `("post","approveTransfer")`. **CONTRACT-ONLY**: `git diff HEAD` `api/imm00.py` (`approve_transfer` @2582-2588) + `services/imm00.py` (`approve_transfer_request` @2615-2643) = **byte-identical HEAD↔working** ⇒ KHÔNG reload gunicorn, KHÔNG migrate — là **[AUTO]**. 71 path hiện-hữu byte-identical.

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | requestBody `multipart/form-data` | SAI transport: `approve_transfer` đọc `form_dict` (json/form-urlencoded). Action state-machine KHÔNG upload. RPC-form json+form ĐÚNG (mirror `receiveTransfer`/`sendToLab`). |
| B | 403 = SINGLE `Forbidden` **dispatcher-only** (mirror `receiveTransfer`) | SAI @source: `approve_transfer_request` CÓ `rbac.require('commissioning.submit')` @2620 raise `PermissionError` NGOÀI except-ValidationError → HTTP-403 REACHABLE (KHÁC `receiveTransfer` 0 rbac.require). 403-slot SINGLE `Forbidden` NHƯNG **REACHABLE** (note trong description — mirror `cancelCalibration`). |
| C | 403 = DUAL-SHAPE hoặc cap-403 phủ-bởi-200 (mirror `reportIncident`/`sendToLab`-oneOf-200) | SAI @source: `rbac.require` raise `PermissionError` (KHÔNG `ValidationError`) ⇒ handler except-ValidationError KHÔNG bắt ⇒ escape → dispatcher HTTP-403 status-line (KHÔNG HTTP-200 Error). ⇒ SINGLE `Forbidden` status-line (KHÔNG dual, KHÔNG phủ-200). |
| D | `ApproveTransferResponse` = reuse `ReceiveTransferResponse` (3-prop) | SAI: `approve_transfer_request` trả `{name,status}` @2643 (2-key, KHÔNG `received_by`/`approved_by`). reuse 3-prop → `additionalProperties:false` validate-FAIL. Schema RIÊNG 2-prop ĐÚNG. |
| E | `ApproveTransferResponse` += `approved_by` (echo giống `receiveTransfer` received_by) | SAI @source: patch `approved_by` vào DB @2628 NHƯNG `return` @2643 CHỈ `{name,status}` — KHÔNG echo `approved_by`. Khai `approved_by` = drift contract↔runtime (client mong field không tồn tại). |
| F | `Error.http_status` khai **404** cho not-found (mirror `getTransfer` 404) | SAI @source: `approve_transfer_request` dùng `frappe.throw` (`ValidationError`) → handler `_err(str(e), **422**)` @2588 — KHÔNG `_err(…, 404)`. CẢ not-found LẪN wrong-status về **422 ĐỒNG NHẤT**. |
| G | `status` type `string` **plain (KHÔNG enum)** | LOẠI: `status` trả đơn-trị `"Approved"` @2643 GROUNDED hằng `_TRANSFER_STATUS_APPROVED` @2562 — acceptance yêu cầu **enum single-value `['Approved']`**. TC-e import hằng LIVE assert equality (anti-bịa). |
| H | `ApproveTransferRequest` += `handover_notes`/optional (copy `receiveTransfer`) | SAI signature: `approve_transfer(name)` @2583 = **1-param** (chỉ `name`). Thêm optional = form mobile nhập field thừa + live-sig parity FAIL. |
| ✅ I | 1 path POST json+form body, 3 schema RIÊNG (Request req[name] 0 optional · Response 2-prop `{name,status}` status enum `['Approved']`), 200 oneOf [Env, Error], **403 SINGLE `Forbidden` REACHABLE cap-branch**, **Error 422-uniform**, `_MVP_ACTION_ENVELOPE` + `_REQBODY_PATHS`, tag `asset` | Grounded 1:1 source; blast-radius = +1 path +3 schema (PURE-YAML); codegen sinh 1 method phê-duyệt type-safe + response 2-prop → app "Phê duyệt điều chuyển"; Decision-B intact; 403-slot REACHABLE documented (chống nút-chết); status enum-grounded; naming-guard ∅; đóng CR-TRANSFER-APPROVE-01. |

## Consequences

- **(+)** App mobile màn Điều chuyển có method `approveTransfer` codegen-ready: người có quyền mở phiếu `Pending Approval` → bấm "Phê duyệt" → phiếu → `Approved` + `approved_by`/`approval_date` + **transfer_asset cập vị trí thiết bị NGAY** @2632-2639 + Lifecycle Event audit. **write-action #2 domain Điều chuyển** (`receiveTransfer` ADR-043 đã mở nhánh; `rejectTransfer`/`createTransfer` forward-reserve). **CR-TRANSFER-APPROVE-01 ĐÓNG.**
- **(+)** Contract GROUNDED 1:1 source — 3 schema RIÊNG VERBATIM (`ApproveTransferRequest` `req[name]` 0 optional khớp signature @2583; `ApproveTransferResponse` EXACT **2-prop** `{name,status}` @2643; `status.enum==['Approved']` GROUNDED hằng `_TRANSFER_STATUS_APPROVED` @2562); 403-slot SINGLE `Forbidden` REACHABLE. **Naming guard:** `ApproveTransfer*` ∩ mọi schema == ∅.
- **(+)** **403 REACHABLE cap-branch documented** — ĐIỂM KHÁC #1 vs `receiveTransfer`: `rbac.require('commissioning.submit')` @2620 raise `PermissionError` NGOÀI except-ValidationError → HTTP-403 THẬT. App PHẢI gate nút "Phê duyệt" theo capability (chống nút-chết cho user thiếu quyền). Mirror `cancelCalibration` ADR-033.
- **(+)** **Response 2-prop `{name,status}`** — ĐIỂM KHÁC #2 vs `receiveTransfer` 3-prop: KHÔNG echo `approved_by` (return @2643 CHỈ 2-key). Người bồi action transfer tiếp PHẢI grep `return {…}` @service.
- **(+)** **ANTI-DRIFT 422-uniform documented** — `approve_transfer_request` dùng `frappe.throw` (`ValidationError`) → handler `_err(str(e),422)` cho CẢ not-found LẪN wrong-status ⇒ `Error.http_status` 422 ĐỒNG NHẤT (KHÔNG 404, mirror `receiveTransfer`).
- **(+)** **`status` enum single-value `['Approved']` GROUNDED verbatim hằng** — typed badge màn Điều chuyển; TC-e import hằng LIVE `_TRANSFER_STATUS_APPROVED` assert equality (chống bịa/drift).
- **(+)** **CONTRACT-ONLY** — `approve_transfer` @2582-2588 + `approve_transfer_request` @2615-2643 **byte-identical HEAD↔working** (2 vùng diff TRỐNG round này — verified) ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO], KHÔNG HARD-STOP USER); `test_oas_d12/d15/d17` UNCHANGED (pure mobile-yaml). 71 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator; 2 nhánh oneOf disjoint required-set closed-schema); 0 dangling `$ref` (3 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`/`Error`).
- **(−)** **403 REACHABLE nhưng SINGLE-shape** — người bồi action tiếp PHẢI phân biệt reachability (rbac.require CÓ/KHÔNG) vs shape (VẪN SINGLE Forbidden nếu cùng `PermissionError` status-line). Ground bằng SOURCE (grep `rbac.require` + kiểm except-scope), KHÔNG copy 403-slot anh-em.
- **(−)** **Response 2-prop RIÊNG** (KHÔNG reuse `ReceiveTransferResponse` dù cùng domain) — field-set khác (2-key vs 3-key). Người bồi action IMM-00/transfer tiếp PHẢI grep `return {…}` @service.
- **(−)** **Forward-reserve** `rejectTransfer`/`createTransfer` — 2 action điều-chuyển còn lại CHƯA curate (vòng Trục-B kế). Backlog transfer write-action-set.
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `674→684` (test_mobile_oas, +10 TC class `TestMobileApproveTransferContract` a..j) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `674→684` + `_GUARD_SUITE_SUM` `817→827` + `_MOBILE_OAS_TOTAL` `843→853` + c5 `60→61` + parity `_PARITY_BUSINESS_PATHS` `60→61` + transition-baseline delta-var `approve_transfer_wire_delta=10` + ADR balance `43→44`. ⚠️ **secondary count-guard KHÔNG dùng token `, 71,`** (3 c5 60→61 + 1 parity + 4 backward-compat opId-set-minus [pmhist 70→71 / transfer(-new) 69→70 / dept 70→71 / loc 70→71] + 2 hardcoded `_EXPECTED_TEST_COUNT==674` [receivecert_j/cancelcal_j] + `op_id_unique` `len(set(ids))==71` bare) ⇒ **full-suite THẬT bắt sót** (RED-before demo → FAIL → restore → GREEN).

---

## Handoff BE/Test (Bước-4 — ĐÃ XONG pure-yaml, ATOMIC)

> **CONTRACT-ONLY — ĐÃ HOÀN TẤT vòng Bước-2 (BA tự code+verify pure-yaml full path-add):** TUYỆT ĐỐI KHÔNG đụng `api/imm00.py`/`services/imm00.py` (`approve_transfer` @2582 / `approve_transfer_request` @2615 ĐÃ LIVE byte-identical HEAD↔working). Không reload/migrate/commit. DoD ĐÃ VERIFY: `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **'Ran 684 OK' THẬT** (RED-before strip-path → FAIL → restore → GREEN) · `.test_mobile_docset` = **Ran 9 OK** (balance 44==44).

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`) — ĐÃ BỒI: +1 path `POST /api/method/assetcore.api.imm00.approve_transfer` (opId `approveTransfer`, **tag `asset`**, đặt SAU getTransfer/receiveTransfer); requestBody 2 media-type json+form CÙNG `$ref ApproveTransferRequest`; 200 = `oneOf [ApproveTransferEnvelope, Error]`; slot `{200,401,403}` (**`403 Forbidden` SINGLE-SHAPE REACHABLE** — description GHI RÕ REACHABLE + cap `commissioning.submit`). +3 schema (`ApproveTransferRequest` closed `req[name]` 0 optional · `ApproveTransferResponse` closed EXACT `req[name,status]` status enum `['Approved']` · `ApproveTransferEnvelope`). Cả 3 `additionalProperties:false`. 0 orphan, 0 dangling.

**(2) test_mobile_oas.py** — ĐÃ BỒI: path/opId `71→72`; `_EXPECTED` += `approve_transfer → approveTransfer`; path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_ACTION_ENVELOPE`; c5 map += `approveTransfer→ApproveTransferEnvelope` (`60→61`); +1 TC class `TestMobileApproveTransferContract` (a..j, 10 TC); `_EXPECTED_TEST_COUNT` `674→684`; bulk-bump `, 71,`→`, 72,` (144) + secondary guard (op_id_unique 71→72 bare · c5 60→61 ×3 · parity 60→61 · backward-compat pmhist 70→71 / transfer(-new) 69→70 / dept 70→71 / loc 70→71 · hardcoded `_EXPECTED_TEST_COUNT` 674→684 ×2). TC-e import hằng LIVE `_TRANSFER_STATUS_APPROVED` assert `status.enum==['Approved']`. TC-g assert 403 REACHABLE (desc chứa 'REACHABLE' + cap) + `422 ∈ Error.http_status` (KHÔNG 404). TC-i live-sig `{name}` 1-param.

**(3) test_mobile_docset.py** — ĐÃ BỒI: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `674→684` · `_GUARD_SUITE_SUM` `817→827` · `_MOBILE_OAS_TOTAL` `843→853` + transition-baseline delta-var `approve_transfer_wire_delta=10` (giữ `pre_fc3_six==191`). ADR-MOBILE-044 registered README (TC-MOB-DOC-02 glob động — balance ADR-on-disk 44 == README-index 44).

**(4) docs narrative** — ĐÃ XONG: `04-api-contract.md` (§8.46 `approveTransfer`) + README ADR-row (ADR-MOBILE-044, balance 43→44) + Core Doc [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §approve_transfer 📱 mobile-binding.

**Domain Điều chuyển nay có write-action #2 mobile: phê duyệt (Pending Approval→Approved).** Forward-reserve: `rejectTransfer`/`createTransfer` (vòng Trục-B kế).
