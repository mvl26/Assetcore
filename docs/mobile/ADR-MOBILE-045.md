# ADR-MOBILE-045 — `rejectTransfer` (**ACTION / CR-TRANSFER-REJECT-01 · transfer WRITE-action #3** — curate 1 path POST TỪ CHỐI phiếu điều chuyển thiết bị vào OAS mirror; **HOÀN TẤT cặp quyết định duyệt** (`approveTransfer` ADR-044 / reject) cho màn "Điều chuyển – Chờ duyệt"; `receiveTransfer` (ADR-043) MỞ NHÁNH, `approveTransfer` (ADR-044) #2, reject #3; `createTransfer` FORWARD-RESERVE; **write-ACTION json+form body** như `approveTransfer`/`receiveTransfer`; **ĐIỂM KHÁC CỐT-LÕI #1: request có body BẮT BUỘC** `rejection_reason` (service validate `len(rejection_reason.strip()) < 5` @`services/imm00.py:2653-2654` → `ValidationError` → 422) — **FIRST transfer action có required text-body** (KHÁC `approveTransfer` name-only 0-body & `receiveTransfer` `handover_notes` OPTIONAL); **ĐIỂM KHÁC CỐT-LÕI #2: NHÁNH 422 THỨ-3** mới — `rejection_reason` thiếu/<5 (ngoài not-found + wrong-status); **ĐIỂM KHÁC CỐT-LÕI #3: status enum single-value** `['Rejected']` (vs `['Approved']`), response **2-prop** `{name,status}` **KHÔNG** echo `rejected_by`/`rejection_reason`; **GIỐNG `approveTransfer`: 403 cap-branch REACHABLE** `commissioning.submit` (`rbac.require` @`services/imm00.py:2651` raise `PermissionError` NGOÀI `except-ValidationError` → HTTP-403 status-line THẬT))

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-045 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-14 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **ADR-MOBILE-021** (TRANSFER-READ-WIRE — `getTransfer`/`listTransfers` READ điều chuyển, tag `asset`, 4 schema Transfer\*) · **ADR-MOBILE-043 §8.45 `receiveTransfer`** (write-action ĐẦU TIÊN domain Điều chuyển — MỞ NHÁNH transfer write-action json+form body) · **ADR-MOBILE-044 §8.46 `approveTransfer`** (write-action #2 — 403 REACHABLE cap `commissioning.submit`, response 2-prop `{name,status}`, 422-uniform; reject là ĐỐI-TÁC quyết định) · Core Doc IMM-00 [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §reject_transfer mobile-binding |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (grep @2026-07-14): handler `assetcore/api/imm00.py` `reject_transfer` def@**2591-2597** (`@frappe.whitelist(methods=["POST"])` @**2591** no-`allow_guest`; **signature `reject_transfer(name, rejection_reason: str = "")`** — `name` positional-KHÔNG-default (bắt buộc), `rejection_reason` có default `""` tại handler NHƯNG **service ép bắt buộc runtime** ⇒ contract REQUIRED; `try: return _ok(reject_transfer_request(name, rejection_reason))` @**2595** / `except frappe.exceptions.ValidationError as e: return _err(str(e), 422)` @**2596-2597**); service `assetcore/services/imm00.py` `reject_transfer_request(name, rejection_reason)` def@**2646** (`if not frappe.db.exists(_DT_TRANSFER, name): frappe.throw(_ERR_TRANSFER_NOT_FOUND.format(name))` @**2648-2649**; **`rbac.require(_TRANSFER_APPROVE_CAP)` @2651** — `_TRANSFER_APPROVE_CAP = "commissioning.submit"` @**2559**; **`if not rejection_reason or len(rejection_reason.strip()) < 5: frappe.throw("Lý do từ chối là bắt buộc (tối thiểu 5 ký tự)")` @2653-2654** — NHÁNH 422 THỨ-3; `if doc.status != _TRANSFER_STATUS_PENDING: frappe.throw("Phiếu đang ở trạng thái '{0}', không thể từ chối")` @**2657-2658**; patch `status=_TRANSFER_STATUS_REJECTED` + `rejected_by=session.user` + `rejection_reason=rejection_reason.strip()` @**2660-2664**; `log_audit_event(... event_type="Transfer" ...)` @**2666**; `_notify_transfer_requester(doc, approved=False)` @**2672**; **`return {"name": name, "status": _TRANSFER_STATUS_REJECTED}` @2674 — EXACT 2-key**); hằng `_TRANSFER_STATUS_REJECTED = "Rejected"` `services/imm00.py:2563` (Select `asset_transfer.json` `status` 5-state); `rbac.require` @`services/shared/rbac.py:190` (`frappe.throw(msg, frappe.PermissionError)` — raise **`PermissionError`**, KHÔNG `ValidationError`). Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.47 `rejectTransfer`).

---

## Context

Module IMM-00 (master/registry) surface domain **Điều chuyển thiết bị** (Asset Transfer) — vòng đời phiếu: `Pending Approval` → `Approved` (duyệt) / **`Rejected`** (từ chối) → `Received` / `Cancelled`. READ-surface (`getTransfer`/`listTransfers`) đã curate (ADR-021); write-action `receiveTransfer` (`Approved → Received`) đã curate (ADR-043 — MỞ NHÁNH); write-action `approveTransfer` (`Pending Approval → Approved`) đã curate (ADR-044 — #2). Màn "Điều chuyển – Chờ duyệt" (feature-12 luồng DUYỆT) có **2 nút song sinh**: "Phê duyệt" (approve) và "Từ chối" (reject). `approveTransfer` đã đóng; nhưng nút "Từ chối" vẫn **dead-end** vì codegen client mobile không sinh method `rejectTransfer`.

`rejectTransfer` là **write-action #3** của domain Điều chuyển: người có quyền phê duyệt (cap `commissioning.submit`) mở phiếu `Pending Approval` → từ chối (kèm **lý do bắt buộc**) → `status = Rejected` + ghi `rejected_by`/`rejection_reason` + audit + notify người yêu cầu. Endpoint `imm00.reject_transfer` **ĐÃ LIVE** @`api/imm00.py:2591` (`@whitelist(methods=["POST"])`, `try _ok(reject_transfer_request) / except ValidationError → _err(…, 422)`) + service `reject_transfer_request` @`services/imm00.py:2646` (return EXACT 2-key `{name, status}` @2674).

Vòng này **curate 1 path POST** `reject_transfer` vào `assetcore-mobile.openapi.yaml` (đóng CR-TRANSFER-REJECT-01) — **HOÀN TẤT cặp quyết định duyệt** (`approveTransfer` / reject) cho màn "Điều chuyển – Chờ duyệt". `createTransfer` là action điều-chuyển còn lại — **FORWARD-RESERVE vòng Trục-B kế**. **CONTRACT-ONLY**: `reject_transfer` + `reject_transfer_request` **byte-identical HEAD↔working** (git diff 2 vùng TRỐNG round này — BE LIVE trong-tree), KHÔNG đụng `.py` ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

**⚠️ ĐIỂM KHÁC CỐT-LÕI #1 — request có body BẮT BUỘC `rejection_reason` (FIRST transfer action có required text-body):**

`approveTransfer` = name-only (0 body optional); `receiveTransfer` = `handover_notes` OPTIONAL (`if handover_notes:` patch). NHƯNG `reject_transfer_request` ép **`if not rejection_reason or len(rejection_reason.strip()) < 5: frappe.throw(...)` @2653-2654** — `rejection_reason` là **required text-body ≥5 ký tự** (sau strip). Handler signature `reject_transfer(name, rejection_reason: str = "")` có default `""` (Python-level), NHƯNG service ép bắt buộc runtime ⇒ **contract REQUIRED**. Contract khai `RejectTransferRequest.required = [name, rejection_reason]` + `rejection_reason.minLength: 5` (**TYPED-HINT** ràng độ dài THÔ; ngữ nghĩa RUNTIME là **strip-then-≥5** — chuỗi 5 dấu-cách vẫn 422 — documented trong description).

**⚠️ ĐIỂM KHÁC CỐT-LÕI #2 — NHÁNH 422 THỨ-3 mới (`rejection_reason` thiếu/<5):**

`approveTransfer` có 2 nhánh ValidationError (not-found + wrong-status). `rejectTransfer` có **3 nhánh**: not-found @2649 + **rejection_reason thiếu/<5 @2653-2654** + wrong-status @2657-2658 — CẢ BA `frappe.throw` → `ValidationError` → handler `_err(str(e), **422**)` @2596-2597. ⇒ `Error.http_status` = **422 ĐỒNG NHẤT** cho CẢ 3 nhánh (KHÔNG 404). op.description GHI RÕ nhánh `rejection_reason` (chống drift missing-branch — người bồi contract action kèm required text-body tiếp PHẢI khai đủ nhánh validate reason).

**⚠️ ĐIỂM KHÁC CỐT-LÕI #3 — status enum `['Rejected']` + response 2-prop `{name,status}` (KHÔNG `rejected_by`/`rejection_reason`):**

`reject_transfer_request` patch `rejected_by=session.user` + `rejection_reason=rejection_reason.strip()` vào DB @2662-2663 NHƯNG `return {"name": name, "status": _TRANSFER_STATUS_REJECTED}` @2674 CHỈ 2-key — KHÔNG echo `rejected_by`/`rejection_reason`. ⇒ `RejectTransferResponse` EXACT 2-prop; `status` = enum single-value **`['Rejected']`** GROUNDED verbatim hằng `_TRANSFER_STATUS_REJECTED` @2563 (vs `approveTransfer` `['Approved']`). Người bồi action transfer tiếp PHẢI grep `return {…}` @service TRƯỚC khi khai (KHÔNG copy schema anh-em).

**⚠️ GIỐNG `approveTransfer` — 403 cap-branch REACHABLE (KHÁC `receiveTransfer` dispatcher-only):**

`reject_transfer_request` gọi **`rbac.require(_TRANSFER_APPROVE_CAP='commissioning.submit')` @2651** — bên trong service, sau exists-check, TRƯỚC reason-check. `rbac.require` @`rbac.py:190` raise **`PermissionError`** (KHÔNG `ValidationError`). Handler `try _ok(reject_transfer_request(...)) except frappe.exceptions.ValidationError` @2596 — `PermissionError` **NGOÀI** except-ValidationError ⇒ **KHÔNG bị bắt** ⇒ propagate tới Frappe dispatcher → **HTTP-403 status-line THẬT** (dispatcher-style, KHÔNG HTTP-200 Error). ⇒ 403-slot có 2 nguồn REACHABLE (dispatcher-403 guest + in-handler cap-403 rbac.require) NHƯNG cả hai đều HTTP-403 status-line + `FrappeRawError` shape ⇒ 403-slot VẪN **SINGLE `Forbidden`** (reachability ≠ shape — mirror `approveTransfer` ADR-044 / `cancelCalibration` ADR-033). Description GHI RÕ **REACHABLE** + cap `commissioning.submit` (chống nút-chết — app gate nút "Từ chối" theo capability, cùng cap với "Phê duyệt").

**⚠️ Cùng transport `approveTransfer`/`receiveTransfer` — KHÁC shape:** cả 3 là **write-ACTION json+form body** (2 media-type `application/json` + `application/x-www-form-urlencoded`, Frappe RPC `form_dict` §9 — KHÔNG multipart). NHƯNG:
- `approveTransfer`: req`[name]` **0 optional** · Response `{name, status}` 2-key · status enum `['Approved']` · cap-403 REACHABLE · **2 nhánh 422**.
- `receiveTransfer`: req`[name]` + `handover_notes` OPTIONAL · Response `{name, status, received_by}` 3-key · **0 cap-403** (dispatcher-only) · 2 nhánh 422.
- `rejectTransfer`: req`[name, rejection_reason]` **rejection_reason BẮT BUỘC** (minLength:5) · Response **`{name, status}` EXACT 2-key** (KHÔNG `rejected_by`/`rejection_reason`) · status **enum single-value `['Rejected']`** · **cap-403 `commissioning.submit` REACHABLE** · **3 nhánh 422** (+rejection_reason).

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `reject_transfer(name, rejection_reason="")` — POST-only whitelist, service-level cap-gate, Decision-B oneOf
- `@frappe.whitelist(methods=["POST"])` @2591 — **POST-only**, **KHÔNG `allow_guest`** ⇒ guest/no-token → **dispatcher-403**.
- Handler đi thẳng `try: return _ok(reject_transfer_request(name, rejection_reason))` @2595.
- `except frappe.exceptions.ValidationError as e: return _err(str(e), 422)` @2596-2597 ⇒ lỗi nghiệp vụ (service `frappe.throw`) → **Decision-B HTTP-200 + Error envelope** `http_status=422`. **`PermissionError` từ `rbac.require` KHÔNG bị bắt** (NGOÀI except-ValidationError) → dispatcher HTTP-403.
- Service @`imm00.py:2646` `return {"name","status"}` @2674 (EXACT **2-key**, `status = _TRANSFER_STATUS_REJECTED = "Rejected"`) → `_ok` → `{"success":true,"data":{name,status}}`. ⇒ 200 = **oneOf [`RejectTransferEnvelope`, `Error`]** (handler QUA `try/except _err` + service `frappe.throw` ⇒ CÓ nhánh Error).

### Ladder lỗi nghiệp vụ in-handler (3 nhánh — CẢ BA → 422 ĐỒNG NHẤT qua ValidationError)
`exists(doc)` → `rbac.require(cap)` [→ PermissionError HTTP-403 nếu thiếu quyền] → `rejection_reason strip ≥5` → `status == Pending Approval` → (patch status=Rejected + rejected_by + rejection_reason + audit + notify + commit). `Error.http_status` phủ:

| # | Nhánh @source (`services/imm00.py`) | mechanism | http_status |
|---|---|---|---|
| 1 | `not frappe.db.exists(_DT_TRANSFER, name)` @2648-2649 (`frappe.throw(_ERR_TRANSFER_NOT_FOUND.format(name))`) — phiếu∄ | `frappe.throw` → `ValidationError` | **422** (handler `_err(str(e),422)` @2597 — **KHÔNG 404**) |
| 2 | `not rejection_reason or len(rejection_reason.strip()) < 5` @2653-2654 (`frappe.throw("Lý do từ chối là bắt buộc (tối thiểu 5 ký tự)")`) — **NHÁNH 422 THỨ-3 mới** | `frappe.throw` → `ValidationError` | **422** (handler `_err(str(e),422)` @2597) |
| 3 | `doc.status != _TRANSFER_STATUS_PENDING` @2657-2658 (`frappe.throw("Phiếu đang ở trạng thái '{0}', không thể từ chối")`) — sai state | `frappe.throw` → `ValidationError` | **422** (handler `_err(str(e),422)` @2597) |

⇒ `Error.http_status` ⊇ **{422}** ĐỒNG NHẤT (3 nhánh, CẢ BA 422; ARRIVE HTTP-200 body qua `_err` — route theo `body.http_status`). **KHÔNG có 404** (KHÁC `getTransfer`).

### 403 REACHABLE (mobile-BE contract gotcha) — 403-slot ⇒ SINGLE-SHAPE reachability ≠ shape
- **dispatcher-403** = guest/no-token (POST `@whitelist` no `allow_guest`) → Frappe dispatcher raise `PermissionError` → **HTTP-403 status-line THẬT** + `FrappeRawError` shape.
- **cap-403 REACHABLE** = bearer hợp lệ nhưng thiếu cap `commissioning.submit`: `rbac.require(_TRANSFER_APPROVE_CAP)` @2651 (TRONG service, sau exists-check) raise `PermissionError`. Vì handler `except` CHỈ bắt `ValidationError` @2596, `PermissionError` **escape** → dispatcher → **HTTP-403 status-line THẬT** (KHÔNG HTTP-200 Error). ⇒ 403-slot có 2 nguồn REACHABLE nhưng **CÙNG shape** (`FrappeRawError` HTTP-403) ⇒ **1 component `Forbidden` SINGLE-SHAPE**. Mirror `approveTransfer` §8.46 (ADR-044) / `cancelCalibration` §8.39 (ADR-033), **KHÁC `receiveTransfer`** (0 `rbac.require` — dispatcher-only). Note REACHABLE + cap ghi trong op.description (chống nút-chết). ⚠️ `rbac.require` @2651 chạy **TRƯỚC** reason-check @2653 ⇒ user thiếu cap KHÔNG bao giờ chạm nhánh reason-422 (403 chặn trước).

### Side-effect success (audit) — contract KHÔNG khai (thuộc service)
`frappe.db.set_value(_DT_TRANSFER, name, {status:"Rejected", rejected_by:session.user, rejection_reason:reason.strip()})` @2660-2664 → `log_audit_event(asset=doc.asset, event_type="Transfer", ...)` @2666 (SINH IMM Audit Trail) → `_notify_transfer_requester(doc, approved=False)` @2672 → commit. Contract này CHỈ khai request/response shape.

## Decision

**Curate 1 path POST GROUNDED 1:1 `imm00.reject_transfer`, requestBody 2 media-type (json + x-www-form-urlencoded) cùng `$ref RejectTransferRequest`, 200 = oneOf [`RejectTransferEnvelope`, `Error`] (Decision-B route-by-VALUE 0-discriminator), 403 = SINGLE-SHAPE `Forbidden` **REACHABLE cap-branch** (`commissioning.submit`), slot `{200,401,403}`.** Tag **`asset`** (parity transfer family — `getTransfer`/`approveTransfer`/`receiveTransfer` cùng tag). Path-count **72→73**, opId **72→73** (đếm thật, DUY NHẤT, camelCase). Đặt path SAU `approveTransfer` (transfer family). CONTRACT-ONLY (pure-yaml).

1. **`rejectTransfer`** — `POST /api/method/assetcore.api.imm00.reject_transfer` › `operationId: rejectTransfer` (dotted-path tail §8.1, camelCase, UNIQUE). Tag **`asset`** (parity transfer family). **POST-only** (`@whitelist(methods=["POST"])` @2591 — clean POST, ∉ `_PARITY_VERB_ALLOWLIST`); live-sig parity `inspect.signature(imm00.reject_transfer) == {name, rejection_reason}` (2-param). 200 = `oneOf [RejectTransferEnvelope, Error]`. slot `{200,401,403}`.

2. **requestBody = 2 media-type** (`required: true`; **`application/json` + `application/x-www-form-urlencoded`** — CÙNG `$ref RejectTransferRequest`; Frappe RPC `form_dict` §9, mirror `approveTransfer`/`receiveTransfer`). **KHÔNG multipart**.

3. **`RejectTransferRequest`** — CLOSED (`additionalProperties: false`), `required: [name, rejection_reason]` (**2 bắt buộc** — KHỚP ép runtime service; KHÁC `approveTransfer` name-only):

   | prop | type | ground |
   |---|---|---|
   | `name` | string | mã **Asset Transfer** (phiếu `Pending Approval` cần từ chối; naming AT-.YYYY.-.####). @2592. **required** |
   | `rejection_reason` | **string** (`minLength: 5` typed-hint) | lý do từ chối — service ép `len(rejection_reason.strip()) < 5 → frappe.throw` @2653-2654 (⇒ contract **required**). minLength:5 ràng độ dài THÔ; ngữ nghĩa RUNTIME **strip-then-≥5** (documented — chuỗi 5 dấu-cách vẫn 422). Service lưu `reason.strip()` @2663. **required** |

   *(ANTI-DRIFT: `rejection_reason` ∈ required — FIRST transfer action có required text-body. `minLength:5` là TYPED-HINT, KHÔNG thay runtime strip-then-≥5.)*

4. **`RejectTransferResponse`** (data) — CLOSED (`additionalProperties: false`), `required: [name, status]` EXACT **2 prop** (GROUNDED `return {"name","status"}` @2674):

   | prop | type | ground |
   |---|---|---|
   | `name` | string | echo name phiếu (`name` @2674) |
   | `status` | **string enum `['Rejected']`** | `_TRANSFER_STATUS_REJECTED` @2661,2674 (`services/imm00.py:2563` = `"Rejected"`). **Giá-trị trả LUÔN `"Rejected"`** (state đơn-trị deterministic) ⇒ **enum single-value `['Rejected']` GROUNDED verbatim hằng** `_TRANSFER_STATUS_REJECTED` (anti-bịa; TC-e import hằng LIVE assert equality) |

   *(ANTI-DRIFT: response EXACT 2-key `{name, status}` — **KHÔNG `rejected_by`/`rejection_reason`** (patch DB @2662-2663 NHƯNG KHÔNG echo trong return @2674); KHÔNG `received_by` (đó là `ReceiveTransferResponse`); KHÔNG `approved_by`/`approval_date`.)*

5. **`RejectTransferEnvelope`** — CLOSED (`additionalProperties: false`), `required: [success, data]`; `success.enum: [true]`; **`data` = `$ref RejectTransferResponse`**. Tên RÚT-GỌN `RejectTransferEnvelope` (mirror `ApproveTransferEnvelope`). Nhánh success của 200-oneOf; disjoint required-set với `Error` ⇒ máy-đọc phân-biệt bằng CLOSED-SCHEMA (KHÔNG discriminator — §5c).

6. **200 = `oneOf [RejectTransferEnvelope, Error]`** — Decision-B route-by-VALUE (`body.success` enum[true] vs [false] + `body.http_status`), 0 discriminator. Nhánh `Error` gom **3 nhánh** service (not-found + rejection_reason thiếu/<5 + wrong-status, CẢ BA 422) ARRIVE HTTP-200.

7. **403 = SINGLE-SHAPE `Forbidden` REACHABLE** (`$ref #/components/responses/Forbidden`, `FrappeRawError`). **2 nguồn REACHABLE** (dispatcher-403 guest + in-handler cap-403 `rbac.require('commissioning.submit')` @2651 → `PermissionError` NGOÀI except → HTTP-403 THẬT), CÙNG shape. Note REACHABLE + cap ghi op.description (mirror `approveTransfer` ADR-044, **KHÁC `receiveTransfer` dispatcher-only**). **401 = `Unauthorized401`**.

### Naming guard (∅)
`RejectTransfer{Request,Response,Envelope}` ∩ mọi schema hiện có == ∅ (grep verify 0 collision) — prefix `RejectTransfer` ≠ `ApproveTransfer` ≠ `ReceiveTransfer` ≠ `Transfer` ⇒ KHÔNG đụng `Transfer*` (READ) / `ApproveTransfer*` / `ReceiveTransfer*` / `SendToLab*` / `CancelCalibration*`. Schema RIÊNG (KHÔNG reuse `ApproveTransferResponse` dù cùng 2-key `{name,status}` — status enum khác `['Rejected']` vs `['Approved']`, C3-split).

**Tag `asset` (grounded):** `getTransfer`/`approveTransfer`/`receiveTransfer` (transfer family) đều tag `asset`@yaml ⇒ `rejectTransfer` = **`asset`** (đối xứng domain).

**Phạm vi membership-set (test_mobile_oas):** path ∈ `_MVP_BUSINESS_PATHS` (→ 401/403 symmetry auto +1) · ∈ `_MVP_ACTION_ENVELOPE` (POST-action-on-existing; `name` = khoá phiếu ĐÃ tồn tại, mirror `approveTransfer`; envelope RIÊNG) · **∉ `_MVP_CREATE_ENVELOPE`** · **c5 envelope-map += `rejectTransfer → RejectTransferEnvelope`** (`61→62`, giữ invariant `c5 == _MVP_BUSINESS_PATHS`) · ∈ `_RATE_LIMIT_SOURCE_MAP` (KHÔNG `@rate_limit` @2591 ⇒ VẮNG khỏi `_PATHS_REQUIRE_429`) · **POST-only-at-source ∉ `_PARITY_VERB_ALLOWLIST`** · **∈ `_REQBODY_PATHS`** (json+form) · `_EXPECTED` += dotted-path entry `("post","rejectTransfer")`. **CONTRACT-ONLY**: `git diff HEAD` `api/imm00.py` (`reject_transfer` @2591-2597) + `services/imm00.py` (`reject_transfer_request` @2646-2674) = **byte-identical HEAD↔working** ⇒ KHÔNG reload gunicorn, KHÔNG migrate — là **[AUTO]**. 72 path hiện-hữu byte-identical.

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | requestBody `multipart/form-data` | SAI transport: `reject_transfer` đọc `form_dict` (json/form-urlencoded). Action state-machine KHÔNG upload. RPC-form json+form ĐÚNG (mirror `approveTransfer`/`receiveTransfer`). |
| B | `RejectTransferRequest.required = [name]` (rejection_reason OPTIONAL như `receiveTransfer` handover_notes) | SAI @source: service ép `if not rejection_reason or len(rejection_reason.strip()) < 5: frappe.throw` @2653-2654 ⇒ `rejection_reason` **required** (khai optional = client bỏ trống → 422 bất ngờ, drift contract↔runtime). |
| C | 403 = SINGLE `Forbidden` **dispatcher-only** (mirror `receiveTransfer`) | SAI @source: `reject_transfer_request` CÓ `rbac.require('commissioning.submit')` @2651 raise `PermissionError` NGOÀI except-ValidationError → HTTP-403 REACHABLE (KHÁC `receiveTransfer` 0 rbac.require). 403-slot SINGLE `Forbidden` NHƯNG **REACHABLE** (note description — mirror `approveTransfer`). |
| D | `Error.http_status` khai CHỈ **2 nhánh** (not-found + wrong-status, bỏ rejection_reason) | SAI @source: `reject_transfer_request` có 3 nhánh `frappe.throw` (thêm reason thiếu/<5 @2653-2654). Bỏ nhánh reason = missing-branch drift (client không biết reason<5 → 422). Description PHẢI ghi nhánh rejection_reason. |
| E | `RejectTransferResponse` += `rejection_reason`/`rejected_by` (echo giống input) | SAI @source: patch `rejection_reason`/`rejected_by` vào DB @2662-2663 NHƯNG `return` @2674 CHỈ `{name,status}` — KHÔNG echo. Khai thêm = drift contract↔runtime (client mong field không tồn tại). |
| F | `RejectTransferResponse` = reuse `ApproveTransferResponse` (cùng `{name,status}`) | SAI: dù cùng field-set `{name,status}`, `status.enum` KHÁC (`['Rejected']` vs `['Approved']`) — reuse → codegen sinh badge sai giá-trị. Schema RIÊNG (C3-split, enum-grounded riêng). |
| G | `status` type `string` **plain (KHÔNG enum)** | LOẠI: `status` trả đơn-trị `"Rejected"` @2674 GROUNDED hằng `_TRANSFER_STATUS_REJECTED` @2563 — acceptance yêu cầu **enum single-value `['Rejected']`**. TC-e import hằng LIVE assert equality (anti-bịa). |
| H | `Error.http_status` khai **404** cho not-found (mirror `getTransfer` 404) | SAI @source: `reject_transfer_request` dùng `frappe.throw` (`ValidationError`) → handler `_err(str(e), **422**)` @2597 — KHÔNG `_err(…, 404)`. CẢ 3 nhánh về **422 ĐỒNG NHẤT**. |
| ✅ I | 1 path POST json+form body, 3 schema RIÊNG (Request req[name,rejection_reason] minLength:5 · Response 2-prop `{name,status}` status enum `['Rejected']` · Envelope), 200 oneOf [Env, Error], **403 SINGLE `Forbidden` REACHABLE cap-branch**, **Error 422-uniform 3-nhánh**, `_MVP_ACTION_ENVELOPE` + `_REQBODY_PATHS`, tag `asset` | Grounded 1:1 source; blast-radius = +1 path +3 schema (PURE-YAML); codegen sinh 1 method từ-chối type-safe + form lý-do required → app "Từ chối điều chuyển"; Decision-B intact; 403-slot REACHABLE documented (chống nút-chết); status enum-grounded; required text-body + 3-nhánh 422 documented; naming-guard ∅; đóng CR-TRANSFER-REJECT-01 (HOÀN TẤT cặp duyệt). |

## Consequences

- **(+)** App mobile màn "Điều chuyển – Chờ duyệt" có method `rejectTransfer` codegen-ready: người có quyền mở phiếu `Pending Approval` → nhập lý do (≥5 ký tự) → bấm "Từ chối" → phiếu → `Rejected` + `rejected_by`/`rejection_reason` + audit + notify người yêu cầu. **HOÀN TẤT cặp quyết định duyệt** (`approveTransfer` ADR-044 / reject) — 2 nút song sinh màn Chờ duyệt hết dead-end. **write-action #3 domain Điều chuyển** (`createTransfer` forward-reserve). **CR-TRANSFER-REJECT-01 ĐÓNG.**
- **(+)** Contract GROUNDED 1:1 source — 3 schema RIÊNG VERBATIM (`RejectTransferRequest` `req[name,rejection_reason]` + `rejection_reason.minLength:5` khớp guard @2653-2654; `RejectTransferResponse` EXACT **2-prop** `{name,status}` @2674; `status.enum==['Rejected']` GROUNDED hằng `_TRANSFER_STATUS_REJECTED` @2563); 403-slot SINGLE `Forbidden` REACHABLE. **Naming guard:** `RejectTransfer*` ∩ mọi schema == ∅.
- **(+)** **Required text-body `rejection_reason` documented** — ĐIỂM KHÁC #1 vs `approveTransfer`: FIRST transfer action có body bắt buộc; `minLength:5` typed-hint + strip-then-≥5 runtime semantics. Người bồi action kèm lý-do bắt buộc tiếp có template.
- **(+)** **NHÁNH 422 THỨ-3 documented** — ĐIỂM KHÁC #2: `Error.http_status` = 422 cho CẢ 3 nhánh (not-found + rejection_reason thiếu/<5 + wrong-status). op.description ghi rõ nhánh rejection_reason (anti-drift missing-branch).
- **(+)** **`status` enum single-value `['Rejected']` GROUNDED verbatim hằng** — ĐIỂM KHÁC #3: typed badge "Đã từ chối" màn Điều chuyển; TC-e import hằng LIVE `_TRANSFER_STATUS_REJECTED` assert equality (chống bịa/drift). Response 2-prop KHÔNG echo `rejected_by`/`rejection_reason`.
- **(+)** **403 REACHABLE cap-branch documented** — GIỐNG `approveTransfer`: `rbac.require('commissioning.submit')` @2651 raise `PermissionError` NGOÀI except-ValidationError → HTTP-403 THẬT. App gate nút "Từ chối" theo capability (cùng cap "Phê duyệt"). Mirror `approveTransfer` ADR-044.
- **(+)** **CONTRACT-ONLY** — `reject_transfer` @2591-2597 + `reject_transfer_request` @2646-2674 **byte-identical HEAD↔working** (2 vùng diff TRỐNG round này — verified) ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO], KHÔNG HARD-STOP USER); `test_oas_d12/d15/d17` UNCHANGED (pure mobile-yaml). 72 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator; 2 nhánh oneOf disjoint required-set closed-schema); 0 dangling `$ref` (3 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`/`Error`).
- **(−)** **Required text-body ép runtime (KHÔNG Python-level)** — handler signature `rejection_reason: str = ""` có default (không bắt buộc ở Python), NHƯNG service ép ≥5 ký tự. Contract khai REQUIRED + minLength:5 typed-hint. Người đọc PHẢI hiểu `minLength` là hint, semantics thật = strip-then-≥5 (documented).
- **(−)** **Response 2-prop RIÊNG** (KHÔNG reuse `ApproveTransferResponse` dù cùng field-set) — status enum khác. Người bồi action IMM-00/transfer tiếp PHẢI grep `return {…}` + hằng status @service.
- **(−)** **Forward-reserve** `createTransfer` — action điều-chuyển còn lại CHƯA curate (vòng Trục-B kế). Backlog transfer write-action-set (read + receive + approve + reject ĐÃ xong; create CÒN).
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `684→694` (test_mobile_oas, +10 TC class `TestMobileRejectTransferContract` a..j) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `684→694` + `_GUARD_SUITE_SUM` `827→837` + `_MOBILE_OAS_TOTAL` `853→863` + c5 `61→62` + parity `_PARITY_BUSINESS_PATHS` `61→62` + transition-baseline delta-var `reject_transfer_wire_delta=10` + ADR balance `44→45`. ⚠️ **secondary count-guard KHÔNG dùng token `, 72,`** (3 c5 61→62 + 1 parity + 4 backward-compat opId-set-minus [pmhist 71→72 / transfer(-new) 70→71 / dept 71→72 / loc 71→72] + 2 hardcoded `_EXPECTED_TEST_COUNT==684` [receivecert_j/cancelcal_j] + `op_id_unique` `len(set(ids))==72` bare + pushdata_g `len(_EXPECTED)` count + test_05 `_EXPECTED` opId-convention set) ⇒ **full-suite THẬT bắt sót** (RED-before demo → **97 FAIL** → restore → GREEN).

---

## Handoff BE/Test (Bước-4 — ĐÃ XONG pure-yaml, ATOMIC)

> **CONTRACT-ONLY — ĐÃ HOÀN TẤT vòng Bước-2 (BA tự code+verify pure-yaml full path-add):** TUYỆT ĐỐI KHÔNG đụng `api/imm00.py`/`services/imm00.py` (`reject_transfer` @2591 / `reject_transfer_request` @2646 ĐÃ LIVE byte-identical HEAD↔working). Không reload/migrate/commit. DoD ĐÃ VERIFY: `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **'Ran 694 OK' THẬT** (RED-before strip-path → **97 FAIL** → restore → GREEN) · `.test_mobile_docset` = **Ran 9 OK** (balance 45==45).

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`) — ĐÃ BỒI: +1 path `POST /api/method/assetcore.api.imm00.reject_transfer` (opId `rejectTransfer`, **tag `asset`**, đặt SAU approveTransfer); requestBody 2 media-type json+form CÙNG `$ref RejectTransferRequest`; 200 = `oneOf [RejectTransferEnvelope, Error]`; slot `{200,401,403}` (**`403 Forbidden` SINGLE-SHAPE REACHABLE** — description GHI RÕ REACHABLE + cap `commissioning.submit` + nhánh 422 rejection_reason). +3 schema (`RejectTransferRequest` closed `req[name,rejection_reason]` + `rejection_reason.minLength:5` · `RejectTransferResponse` closed EXACT `req[name,status]` status enum `['Rejected']` · `RejectTransferEnvelope`). Cả 3 `additionalProperties:false`. 0 orphan, 0 dangling.

**(2) test_mobile_oas.py** — ĐÃ BỒI: path/opId `72→73`; `_EXPECTED` += `reject_transfer → rejectTransfer`; path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_ACTION_ENVELOPE`; c5 map += `rejectTransfer→RejectTransferEnvelope` (`61→62`); +1 TC class `TestMobileRejectTransferContract` (a..j, 10 TC); `_EXPECTED_TEST_COUNT` `684→694`; bulk-bump `, 72,`→`, 73,` (147) + bare `72)`→`73)` + secondary guard (op_id_unique 72→73 · c5 61→62 ×3 · parity 61→62 · backward-compat pmhist 71→72 / transfer(-new) 70→71 / dept 71→72 / loc 71→72 · hardcoded `_EXPECTED_TEST_COUNT` 684→694 ×2 · `_EXPECTED` entry [fix pushdata_g count + test_05 opId-convention]). TC-c assert `required ⊇ {rejection_reason}` + props EXACT 2 + `rejection_reason.minLength==5`. TC-e import hằng LIVE `_TRANSFER_STATUS_REJECTED` assert `status.enum==['Rejected']`. TC-g assert 403 REACHABLE (desc chứa 'REACHABLE' + cap + 'rejection_reason') + `422 ∈ Error.http_status`. TC-i live-sig `{name, rejection_reason}` 2-param.

**(3) test_mobile_docset.py** — ĐÃ BỒI: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `684→694` · `_GUARD_SUITE_SUM` `827→837` · `_MOBILE_OAS_TOTAL` `853→863` + transition-baseline delta-var `reject_transfer_wire_delta=10` (giữ `pre_fc3_six==191`). ADR-MOBILE-045 registered README (TC-MOB-DOC-02 glob động — balance ADR-on-disk 45 == README-index 45).

**(4) docs narrative** — ĐÃ XONG: `04-api-contract.md` (§8.47 `rejectTransfer`) + README ADR-row (ADR-MOBILE-045, balance 44→45) + Core Doc [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §reject_transfer 📱 mobile-binding.

**Domain Điều chuyển nay có write-action #3 mobile: từ chối (Pending Approval→Rejected) — HOÀN TẤT cặp quyết định duyệt (approve/reject).** Forward-reserve: `createTransfer` (vòng Trục-B kế).
