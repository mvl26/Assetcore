# ADR-MOBILE-043 — `receiveTransfer` (**ACTION / CR-TRANSFER-RECV-01 · transfer WRITE-action ĐẦU TIÊN** — curate 1 path POST XÁC NHẬN TIẾP NHẬN thiết bị điều chuyển vào OAS mirror; **MỞ NHÁNH transfer write-action** sau READ `getTransfer`/`listTransfers` đã curate (TRANSFER-READ-WIRE); `approveTransfer`/`rejectTransfer`/`createTransfer` FORWARD-RESERVE vòng Trục-B kế (mirror `sendToLab` R10 mở nhánh External-cal); **write-ACTION json+form body** như `sendToLab`/`cancelCalibration`; **1 field bắt buộc** `name` + `handover_notes` optional; **ĐIỂM KHÁC CỐT-LÕI [⚠️ AMENDED 2026-07-15 — SUPERSEDED bởi CR-WF-00-TRANSFER-AUTHZ, xem §AMENDMENT]: 403 nay SINGLE Forbidden REACHABLE cap-branch `commissioning.write`** — `confirm_receipt` `rbac.require(commissioning.write)` @`services/imm00.py:2768` propagate NGOÀI `except-ValidationError` @`api/imm00.py:2645-2648` → cap-403 (mirror `approveTransfer`/`sendToLab` cap-403 REACHABLE, KHÁC cap); 403-slot VẪN SINGLE `Forbidden` (schema BẤT BIẾN); **ANTI-DRIFT 422-uniform** — `Error.http_status` = **422 ĐỒNG NHẤT** cho CẢ not-found LẪN wrong-status (KHÁC `getTransfer` 404 tường minh))

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-043 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-14 |
| Tác giả | BA Lead (mobile contract) |
| **Status** | **Amended** (403-reachability SUPERSEDED by CR-WF-00-TRANSFER-AUTHZ — xem [§AMENDMENT 2026-07-15](#️-amendment-2026-07-15--403-reachability-superseded-by-cr-wf-00-transfer-authz); các phần khác GIỮ Accepted) |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B route-by-VALUE `body.success`, Error envelope HTTP-200, 0 discriminator) · **ADR-MOBILE-021** (TRANSFER-READ-WIRE — `getTransfer`/`listTransfers` READ điều chuyển, tag `asset`, 4 schema Transfer*) · **ADR-MOBILE-031 §8.37 `sendToLab`** (template write-ACTION json+form body §9 Frappe form_dict; response 3-prop `{name,status,…}`) · **ADR-MOBILE-027 §8.33 `attachIncidentPhoto`** (403 SINGLE-SHAPE dispatcher-only — handler KHÔNG `rbac.require` cap-403) · Core Doc IMM-00 [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §receive_transfer mobile-binding |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source (grep @2026-07-14): handler `assetcore/api/imm00.py` `receive_transfer` def@**2600-2606** (`@frappe.whitelist(methods=["POST"])` @**2600** no-`allow_guest`; **signature `receive_transfer(name, handover_notes="")`** — `name` positional-KHÔNG-default (bắt buộc) + `handover_notes` default `""` empty-string (KHÔNG None); **KHÔNG `rbac.require`** — 0 in-handler cap-403; `try: return _ok(confirm_receipt(name, handover_notes))` @**2604** / `except frappe.exceptions.ValidationError as e: return _err(str(e), 422)` @**2605-2606**); service `assetcore/services/imm00.py` `confirm_receipt(name, handover_notes="")` def@**2677** (`if not frappe.db.exists(_DT_TRANSFER, name): frappe.throw(_ERR_TRANSFER_NOT_FOUND)` @**2679-2680**; `if doc.status != _TRANSFER_STATUS_APPROVED: frappe.throw("Phiếu phải ở trạng thái 'Approved'…")` @**2683-2684**; patch `status=_TRANSFER_STATUS_RECEIVED` + `received_by=frappe.session.user` + `received_date=nowdate()` @**2686-2693**; `if handover_notes: updates["handover_notes"]=handover_notes` @**2691-2692**; `log_audit_event(event_type="Transfer")` @**2695** + `create_lifecycle_event(event_type="transferred")` @**2701**; **`return {"name": name, "status": _TRANSFER_STATUS_RECEIVED, "received_by": frappe.session.user}` @**2708** — EXACT **3-key**); hằng `_TRANSFER_STATUS_RECEIVED = "Received"` `services/imm00.py:2564` (Select `asset_transfer.json` `status` 5-state). Contract mirror: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml). Narrative: [`04-api-contract.md`](./04-api-contract.md) (§8.45 `receiveTransfer`).

---

## ⚠️ AMENDMENT (2026-07-15) — 403-reachability SUPERSEDED by CR-WF-00-TRANSFER-AUTHZ

> **Status ADR-043 → Amended.** Phần **ĐIỂM KHÁC CỐT-LÕI #1 "403 SINGLE Forbidden dispatcher-ONLY (0 cap-403)"** của ADR này (Context #1 · Decision §7 · Alternatives B · Consequences +403 · §2-loại-403) đã **SUPERSEDED**. Mọi phần khác (transport json+form, ANTI-DRIFT 422-uniform Error, response 3-prop `{name,status,received_by}`, `status` enum `['Received']`, naming-guard, **403 schema shape = SINGLE `$ref Forbidden`**) **VẪN NGUYÊN GIÁ TRỊ**.

**Vì sao đổi:** ADR-043 (2026-07-14) đặc tả contract theo code khi đó — `confirm_receipt` CHƯA có `rbac.require` ⇒ **mọi user login** (kể cả base role) xác nhận tiếp nhận `Approved→Received` được (lỗ leo-quyền **P1**). **CR-WF-00-TRANSFER-AUTHZ** (đã landed working-tree) đóng lỗ bằng cap-gate least-privilege.

**Evidence (@source, VERIFY 2026-07-15):**
- `confirm_receipt` @`services/imm00.py:2760-2796` **+= `rbac.require(_TRANSFER_RECEIVE_CAP)` @2768** — đặt NGAY sau existence-check @2762, TRƯỚC status-check @2771 (mirror ordering `approve_transfer_request`; thiếu quyền → 403 KHÔNG rò trạng thái phiếu).
- `_TRANSFER_RECEIVE_CAP = "commissioning.write"` @`services/imm00.py:2611` — **≠** approve/reject `_TRANSFER_APPROVE_CAP = "commissioning.submit"` @2604 (least-privilege: `Commissioning User` `write=1`/`submit=0` nhận được nhưng KHÔNG duyệt; base fail-closed). `commissioning.write` ĐÃ có trong `CAPABILITY_MAP` ⇒ **0 CAP_SET_VERSION bump, 0 migrate**.
- `rbac.require` → `frappe.throw(..., frappe.PermissionError)` @`services/shared/rbac.py:190-196`.
- Handler `receive_transfer` @`api/imm00.py:2643-2648` **CHỈ `except frappe.exceptions.ValidationError`** ⇒ `PermissionError` **KHÔNG bị bắt/nuốt** → propagate dispatcher → **HTTP-403 status-line THẬT** (KHÔNG convert thành `_err(...,422)` 200-Error).

**Contract sau amendment (đã đồng bộ yaml + 04 §8.45 + imm-00/05):**
- **403 = SINGLE-SHAPE `Forbidden` REACHABLE cap-branch** (`commissioning.write`). 2 nguồn cùng resolve HTTP-403 `FrappeRawError` status-line: (1) **dispatcher-403** (guest/no-token, `@whitelist` no-`allow_guest`); (2) **cap-403** (bearer hợp lệ, THIẾU `commissioning.write`). Cả 2 CÙNG shape ⇒ **403-slot VẪN SINGLE `$ref Forbidden`** — reachability ≠ shape ⇒ **description-only change, schema BẤT BIẾN** (`TestMobileReceiveTransferContract` (g) assert `403 == $ref Forbidden` + `no oneOf` + `http_status ⊇ {422}` → KHÔNG drift; `oas_baseline.py` KHÔNG drift).
- **Mirror mới:** `approveTransfer`/`rejectTransfer`/`sendToLab`/`cancelCalibration` (cap-403 REACHABLE, KHÁC cap) — **KHÔNG CÒN** mirror `attachIncidentPhoto` ADR-027 (dispatcher-only). `createTransfer` (vẫn 0-cap dispatcher-only) nay mirror `attachIncidentPhoto` ADR-027.
- **Client routing:** 403 = thiếu `commissioning.write` → **ẩn/disable nút "Xác nhận tiếp nhận"** (KHÔNG re-login; chỉ **401** re-login). App gate nút theo cap `commissioning.write` — FE `AssetTransferDetailView.vue` `canReceive` + `transfer_cta_flags(status)→{can_approve,can_receive}` (CR-WF-00-TRANSFER-AUTHZ thread-C); app mobile (repo riêng) gate tương tự = mobile-BE owner.
- **GIỮ NGUYÊN (KHÔNG đổi):** ANTI-DRIFT **422-uniform** (phiếu∄ @2762-2763 + status≠Approved @2771-2772 → `frappe.throw`→`ValidationError`→`_err(str(e),422)`, KHÔNG 404) · response 3-prop · naming-guard · Decision-B oneOf.

**Deploy:** .py `confirm_receipt` (@2768) cần **gunicorn reload cho LIVE** (HARD-STOP USER — thread-C, `bench run-tests` fresh-import KHÔNG cần reload). Round contract-sync này (yaml + 04 + ADR + imm-00/05) = **doc-only** (0 NEW .py / 0 migrate / 0 commit).

> **Amendment convention (P-DOC-3):** quyết định gốc GIỮ NGUYÊN bên dưới làm record lịch-sử điểm-thời-gian (2026-07-14). Mọi khẳng định "403 dispatcher-only / 0 cap-403 / `receive_transfer` KHÔNG `rbac.require`" trong §Context/§Decision/§Alternatives/§Consequences bên dưới đọc **QUA amendment này**.

---

## Context

Module IMM-00 (master/registry) surface domain **Điều chuyển thiết bị** (Asset Transfer) — vòng đời phiếu: `Pending Approval` → `Approved` (duyệt) → **`Received`** (bên NHẬN xác nhận tiếp nhận) / `Rejected` / `Cancelled`. READ-surface (`getTransfer` chi-tiết + `listTransfers` danh-sách) **ĐÃ curate** vào OAS mirror (TRANSFER-READ-WIRE / ADR-MOBILE-021, tag `asset`, 4 schema `Transfer*`) — nhưng **CHƯA có write-action nào**: nút "Xác nhận nhận bàn giao" trên màn Điều chuyển (feature-12, luồng NHẬN scan-confirm) là **dead-end** vì codegen client mobile không sinh method `receiveTransfer`.

`receiveTransfer` là **write-action ĐẦU TIÊN** của domain Điều chuyển vào mirror: bên nhận (KTV/thủ kho khoa đích) mở phiếu `Approved` → xác nhận đã tiếp nhận thiết bị → `status = Received` + ghi `received_by`/`received_date` + SINH audit (`log_audit_event "Transfer"` @2695 + `create_lifecycle_event "transferred"` @2701). Endpoint `imm00.receive_transfer` **ĐÃ LIVE** @`api/imm00.py:2600` (`@whitelist(methods=["POST"])`, `try _ok(confirm_receipt) / except ValidationError → _err(…, 422)`) + service `confirm_receipt` @`services/imm00.py:2677` (return EXACT 3-key `{name, status, received_by}` @2708).

Vòng này **curate 1 path POST** `receive_transfer` vào `assetcore-mobile.openapi.yaml`, **MỞ NHÁNH transfer write-action** (đóng CR-TRANSFER-RECV-01). `approveTransfer`/`rejectTransfer`/`createTransfer` là các action điều-chuyển còn lại — **FORWARD-RESERVE vòng Trục-B kế** (mirror cách `sendToLab` mở nhánh External-cal rồi `receiveCertificate`/`cancelCalibration` land sau). **CONTRACT-ONLY**: `receive_transfer` + `confirm_receipt` **byte-identical HEAD↔working** (git diff -U0 2 vùng TRỐNG round này — BE LIVE trong-tree), KHÔNG đụng `.py` ⇒ KHÔNG reload gunicorn, KHÔNG migrate.

**⚠️ ĐIỂM KHÁC CỐT-LÕI #1 — 403 SINGLE Forbidden dispatcher-ONLY (0 in-handler cap-403):** *[⚠️ SUPERSEDED 2026-07-15 — xem [§AMENDMENT](#️-amendment-2026-07-15--403-reachability-superseded-by-cr-wf-00-transfer-authz): 403 nay REACHABLE cap `commissioning.write`; đoạn dưới là record lịch-sử 2026-07-14.]*

`sendToLab`/`receiveCertificate` gate cap `write`; `cancelCalibration` gate cap `cancel` (reachable). NHƯNG `receive_transfer` **KHÔNG có `rbac.require` nào** trong handler (chỉ `try/except` quanh `confirm_receipt`) — quyền tiếp-nhận được điều tiết ở tầng DocPerm/workflow (bên nhận có `write` trên Asset Transfer), KHÔNG qua capability-gate in-handler. ⇒ Nhánh 403 DUY NHẤT là **dispatcher-403** (guest/no-token trip TRƯỚC handler vì `@whitelist` no-`allow_guest`). Không có cap-403 nào để "phủ bởi 200-oneOf Error". ⇒ 403-slot = **SINGLE `Forbidden`** dispatcher-only (mirror `attachIncidentPhoto` ADR-027 — handler KHÔNG `rbac.require`; KHÁC `sendToLab`/`cancelCalibration` có cap-403 in-handler; KHÁC `reportIncident` DUAL-403 `_err(403)`@200).

**⚠️ ĐIỂM KHÁC CỐT-LÕI #2 — ANTI-DRIFT `Error.http_status` = 422 ĐỒNG NHẤT (uniform, KHÔNG 404):**

`confirm_receipt` báo lỗi nghiệp vụ bằng **`frappe.throw(...)`** (KHÔNG `nthrow`/ServiceError với code+http_status riêng): phiếu∄ @2680 VÀ status≠Approved @2684 — CẢ HAI raise `ValidationError`. Handler bắt `except frappe.exceptions.ValidationError → _err(str(e), 422)` @2605-2606 ⇒ **MỌI lỗi nghiệp vụ → HTTP-200 + Error body `http_status=422`** (uniform). Đây KHÁC `getTransfer` (READ cùng domain) dùng `_err(_ERR_TRANSFER_NOT_FOUND, 404)` tường minh → 404. ⇒ **`receive_transfer` KHÔNG bao giờ phát 404** — not-found cũng về 422. Description schema/path PHẢI GHI RÕ 422-uniform (KHÔNG 404) để codegen consumer route `body.http_status` đúng.

**⚠️ Cùng transport `sendToLab`/`cancelCalibration` — KHÁC shape:** cả 3 là **write-ACTION json+form body** (requestBody 2 media-type `application/json` + `application/x-www-form-urlencoded`, Frappe RPC `form_dict` §9 — KHÔNG multipart). NHƯNG:
- `sendToLab`: req`[name]` 1 field · Response `{name, status, sent_date}` 3-key · status enum-8-canonical · cap-403 `write`.
- `cancelCalibration`: req`[name, reason]` 2 field · Response `{name, status}` 2-key · status plain-string · cap-403 `cancel` REACHABLE.
- `receiveTransfer`: req`[name]` + `handover_notes` optional · Response **`{name, status, received_by}` EXACT 3-key** · status **enum single-value `['Received']`** · **0 cap-403** (dispatcher-only) · **422-uniform** (KHÔNG 404).

**Cơ-chế hiện hữu (đã VERIFY @source):**

### `receive_transfer(name, handover_notes="")` — POST-only whitelist, KHÔNG cap-gate, Decision-B oneOf
- `@frappe.whitelist(methods=["POST"])` @2600 — **POST-only**, **KHÔNG `allow_guest`** ⇒ guest/no-token → **dispatcher-403** (`PermissionError` HTTP-403 status-line THẬT TRƯỚC handler).
- **KHÔNG `rbac.require`** — handler đi thẳng `try: return _ok(confirm_receipt(name, handover_notes))` @2604. ⇒ **0 in-handler cap-403.**
- `except frappe.exceptions.ValidationError as e: return _err(str(e), 422)` @2605-2606 ⇒ lỗi nghiệp vụ (service `frappe.throw`) → **Decision-B HTTP-200 + Error envelope** `http_status=422` (KHÔNG raise→4xx status-line).
- Service @`imm00.py:2677` `return {"name","status","received_by"}` @2708 (EXACT **3-key**, `status = _TRANSFER_STATUS_RECEIVED = "Received"`) → `_ok` → `{"success":true,"data":{name,status,received_by}}`. ⇒ 200 = **oneOf [`ReceiveTransferEnvelope`, `Error`]** (handler QUA `try/except _err` + service `frappe.throw` ⇒ CÓ nhánh Error — mirror `sendToLab`/`getTransfer` oneOf, KHÁC `listTransfers` single-shape).

### Ladder lỗi nghiệp vụ in-handler (2 nhánh — CẢ HAI → 422 ĐỒNG NHẤT qua ValidationError)
`exists(doc)` → `status == Approved` → (patch status=Received + received_by + received_date + [handover_notes nếu truthy] + audit + lifecycle + commit). `Error.http_status` phủ:

| # | Nhánh @source (`services/imm00.py`) | mechanism | http_status |
|---|---|---|---|
| 1 | `not frappe.db.exists(_DT_TRANSFER, name)` @2679-2680 (`frappe.throw(_ERR_TRANSFER_NOT_FOUND.format(name))`) — phiếu∄ | `frappe.throw` → `ValidationError` | **422** (handler `_err(str(e),422)` @2606 — **KHÔNG 404**) |
| 2 | `doc.status != _TRANSFER_STATUS_APPROVED` @2683-2684 (`frappe.throw("Phiếu phải ở trạng thái 'Approved' trước khi xác nhận tiếp nhận")`) — sai state | `frappe.throw` → `ValidationError` | **422** (handler `_err(str(e),422)` @2606) |

⇒ `Error.http_status` ⊇ **{422}** ĐỒNG NHẤT (2 nhánh, CẢ HAI 422; tất cả ARRIVE HTTP-200 body qua `_err` — route theo `body.http_status`, KHÔNG status-line). **KHÔNG có 404** (KHÁC `getTransfer` 404) — vì `confirm_receipt` dùng `frappe.throw` (`ValidationError`) thay vì `_err(…, 404)` tường minh. **KHÔNG có 403** trong 200-Error (không cap-403 nào — xem §403-slot).

### 2 loại 403 (mobile-BE contract gotcha) — 403-slot ⇒ SINGLE-SHAPE dispatcher-only
- **dispatcher-403** = guest/no-token (POST `@whitelist` no `allow_guest`) → Frappe dispatcher raise `PermissionError` → **HTTP-403 status-line THẬT** + `FrappeRawError` shape.
- **cap-403 = KHÔNG TỒN TẠI** — handler KHÔNG `rbac.require` ⇒ không có nhánh cap-403 in-handler (KHÁC `sendToLab`/`cancelCalibration`). ⇒ 403-slot chỉ giữ **1 component `Forbidden` SINGLE-SHAPE** (dispatcher-403). Mirror `attachIncidentPhoto` §8.33 (ADR-027 — handler KHÔNG `rbac.require`), **KHÁC `reportIncident` DUAL-403** (dùng `_err(403)`@200) VÀ **KHÁC `sendToLab`/`cancelCalibration`** (có cap-403 in-handler phủ bởi 200-oneOf).

### Side-effect success (lifecycle) — contract KHÔNG khai (thuộc service)
`frappe.db.set_value(_DT_TRANSFER, name, {status:"Received", received_by:session.user, received_date:nowdate(), [handover_notes]})` @2686-2693 → `log_audit_event(asset=doc.asset, event_type="Transfer", change_summary=f"Tiếp nhận tại {doc.to_location}")` @2695 → `create_lifecycle_event(asset=doc.asset, event_type="transferred", …)` @2701 → commit. Contract này CHỈ khai request/response shape (KHÔNG khai side-effect).

## Decision

**Curate 1 path POST GROUNDED 1:1 `imm00.receive_transfer`, requestBody 2 media-type (json + x-www-form-urlencoded) cùng `$ref ReceiveTransferRequest`, 200 = oneOf [`ReceiveTransferEnvelope`, `Error`] (Decision-B route-by-VALUE 0-discriminator), 403 = SINGLE-SHAPE `Forbidden` (dispatcher-only — 0 cap-403), slot `{200,401,403}`.** Tag **`asset`** (domain Điều chuyển surfaced qua api/imm00 — mirror `getTransfer`/`listTransfers`). Path-count **70→71**, opId **70→71** (đếm thật, DUY NHẤT, camelCase). CONTRACT-ONLY (pure-yaml).

1. **`receiveTransfer`** — `POST /api/method/assetcore.api.imm00.receive_transfer` › `operationId: receiveTransfer` (dotted-path tail §8.1, camelCase, UNIQUE). Tag **`asset`** (grounded: `getTransfer`/`listTransfers` READ điều chuyển đều tag `asset`@yaml — domain surfaced qua imm00). **POST-only** (`@whitelist(methods=["POST"])` @2600 — clean POST, KHÔNG verb-divergence, ∉ `_PARITY_VERB_ALLOWLIST`); live-sig parity `inspect.signature(imm00.receive_transfer) == {name, handover_notes}`. 200 = `oneOf [ReceiveTransferEnvelope, Error]`. slot `{200,401,403}`.

2. **requestBody = 2 media-type** (`required: true`; **`application/json` + `application/x-www-form-urlencoded`** — CÙNG `$ref ReceiveTransferRequest`; Frappe RPC `form_dict` §9, mirror `sendToLab`/`cancelCalibration`). **KHÔNG multipart** (action state-machine, KHÔNG upload) — path RPC-form chuẩn ⇒ **KHÔNG** hằng exempt media-type.

3. **`ReceiveTransferRequest`** — CLOSED (`additionalProperties: false`), `required: [name]` (**1 bắt buộc** — KHỚP signature @2601: `name` positional KHÔNG default):

   | prop | type | ground |
   |---|---|---|
   | `name` | string | mã **Asset Transfer** (phiếu `Approved` cần xác nhận tiếp nhận; naming AT-.YYYY.-.####). @2601. **required** |
   | `handover_notes` | string (**NON-nullable**) | ghi chú bàn giao khi tiếp nhận. **Optional** (`handover_notes: str = ""` @2601 — default **empty-string KHÔNG None**; service chỉ patch khi truthy `if handover_notes:` @2691-2692). RỖNG/bỏ qua ⇒ KHÔNG patch. **KHÔNG `nullable:true`** (never null, default `''` — KHÁC `sendToLab` optionals default None → nullable). ∉ required |

   *(KHÔNG thêm/bớt prop — 2 prop khớp signature 2-param; chỉ `name` required. KHÔNG `enum` field nào — 2 free string.)*

4. **`ReceiveTransferResponse`** (data) — CLOSED (`additionalProperties: false`), `required: [name, status, received_by]` EXACT **3 prop** (GROUNDED `return {"name","status","received_by"}` @2708):

   | prop | type | ground |
   |---|---|---|
   | `name` | string | echo name phiếu (`name` @2708) |
   | `status` | **string enum `['Received']`** | `_TRANSFER_STATUS_RECEIVED` @2687,2708 (`services/imm00.py:2564` = `"Received"`). **Giá-trị trả LUÔN `"Received"`** (state đơn-trị deterministic) ⇒ **enum single-value `['Received']` GROUNDED verbatim hằng** `_TRANSFER_STATUS_RECEIVED` (anti-bịa; TC-e import hằng LIVE assert equality) |
   | `received_by` | string | người xác nhận (`frappe.session.user` @2708 — LUÔN có giá trị) |

   *(ANTI-DRIFT: response EXACT 3-key `{name, status, received_by}` — KHÔNG có `sent_date` (đó là `SendToLabResponse`), KHÔNG `handover_notes`/`received_date` (lưu server, KHÔNG echo trong return @2708).)*

5. **`ReceiveTransferEnvelope`** — CLOSED (`additionalProperties: false`), `required: [success, data]`; `success.enum: [true]`; **`data` = `$ref ReceiveTransferResponse`** (object nested, KHÔNG array). Tên RÚT-GỌN `ReceiveTransferEnvelope` (KHÔNG `…ResponseEnvelope` — mirror `attachIncidentPhoto` `AttachIncidentPhotoEnvelope`, theo acceptance). Nhánh success của 200-oneOf; disjoint required-set với `Error` (`req[success,data]` vs `Error req[success,error,code,http_status]`) ⇒ máy-đọc phân-biệt bằng CLOSED-SCHEMA (KHÔNG discriminator — `success` boolean, §5c).

6. **200 = `oneOf [ReceiveTransferEnvelope, Error]`** — Decision-B route-by-VALUE (`body.success` enum[true] vs [false] + `body.http_status`), 0 discriminator. Nhánh `Error` gom **2 nhánh** service (not-found + wrong-status, CẢ HAI 422) ARRIVE HTTP-200. Mirror `sendToLab` §8.37 / `getTransfer` §III (READ cùng domain) 200-oneOf.

7. **403 = SINGLE-SHAPE `Forbidden`** (`$ref #/components/responses/Forbidden`, `FrappeRawError`). *[⚠️ SUPERSEDED 2026-07-15 — xem §AMENDMENT: 403 nay REACHABLE cap-branch `commissioning.write` (dispatcher-403 + cap-403 CÙNG shape); schema shape SINGLE `Forbidden` GIỮ NGUYÊN.]* **CHỈ dispatcher-403** (guest/no-token @ HTTP-403 status-line) — `receive_transfer` **KHÔNG `rbac.require`** ⇒ 0 cap-403 in-handler. Mirror `attachIncidentPhoto` §8.33 (handler KHÔNG cap-gate), **KHÁC `sendToLab`/`cancelCalibration`** (cap-403 in-handler phủ bởi 200-oneOf) VÀ **KHÁC `reportIncident` DUAL-403**. **401 = `Unauthorized401`** (bearer hết-hạn/invalid → HTTP-401 THẬT).

### Naming guard (∅)
`ReceiveTransfer{Request,Response,Envelope}` ∩ mọi schema hiện có == ∅ (grep verify 0 collision) — prefix `ReceiveTransfer` ≠ `ReceiveCertificate` ≠ `Transfer` ⇒ KHÔNG đụng `Transfer*` (READ `TransferListItem`/`TransferListEnvelope`/`TransferDetail`/`TransferDetailEnvelope`) LẪN `ReceiveCertificate*`/`SendToLab*`/`CancelCalibration*`. Schema RIÊNG (KHÔNG reuse `SendToLabResponse` 3-prop dù CÙNG số key — field-set `{name,status,received_by}` ≠ `{name,status,sent_date}`; `additionalProperties:false` validate-FAIL nếu reuse).

**Tag `asset` (grounded):** `getTransfer` §III / `listTransfers` (TRANSFER-READ-WIRE) đều tag `asset`@yaml (domain Điều chuyển surfaced qua api/imm00 — yaml KHÔNG có top-level tag `transfer`) ⇒ `receiveTransfer` = **`asset`** (đối xứng domain).

**Phạm vi membership-set (test_mobile_oas):** path ∈ `_MVP_BUSINESS_PATHS` (→ 401/403 symmetry auto +1) · ∈ `_MVP_ACTION_ENVELOPE` (POST-action-on-existing oneOf [<ActionEnvelope>, Error]; `name` = khoá phiếu ĐÃ tồn tại, mirror `sendToLab`; envelope RIÊNG) · **∉ `_MVP_CREATE_ENVELOPE`** (action trên phiếu có sẵn) · **∉ `_MVP_SINGLE_LIST_ENVELOPE`/`_MVP_LIST_ENVELOPE`/`_MVP_READ_ENVELOPE`** · **c5 envelope-map += `receiveTransfer → ReceiveTransferEnvelope`** (`59→60`, giữ invariant `c5 == _MVP_BUSINESS_PATHS`) · ∈ `_RATE_LIMIT_SOURCE_MAP` (KHÔNG `@rate_limit` @2600 ⇒ VẮNG khỏi `_PATHS_REQUIRE_429`, chống bịa 429) · **POST-only-at-source ∉ `_PARITY_VERB_ALLOWLIST`** · **∈ `_REQBODY_PATHS`** (có requestBody json+form — mirror `sendToLab`, KHÁC 3 path multipart) · **KHÔNG hằng exempt media-type**: path RPC-form chuẩn PHẢI khai CẢ `application/json` + `application/x-www-form-urlencoded` (subject sweep `_RPC_FORM_JSON_MEDIA`) · `_EXPECTED` += dotted-path entry `("post","receiveTransfer")`. **CONTRACT-ONLY**: `git diff HEAD` `api/imm00.py` (`receive_transfer` @2600-2606) + `services/imm00.py` (`confirm_receipt` @2677-2708) = **byte-identical HEAD↔working** (2 vùng diff TRỐNG round này — verified) ⇒ KHÔNG reload gunicorn, KHÔNG migrate — là **[AUTO]**, KHÔNG HARD-STOP USER. 70 path hiện-hữu byte-identical; `test_oas_d12/d15/d17` generator baseline KHÔNG đụng (pure mobile-yaml).

## Alternatives

| # | Phương án | Lý do LOẠI |
|---|---|---|
| A | requestBody `multipart/form-data` (copy 3 path `attach*Photo`) | SAI transport: `receive_transfer` đọc `form_dict` (json/form-urlencoded), KHÔNG `frappe.request.files`. Đây action state-machine KHÔNG upload. RPC-form json+form ĐÚNG (mirror `sendToLab`/`cancelCalibration`). |
| B | 403 = DUAL-SHAPE `ReceiveTransferForbidden` (oneOf Error\|FrappeRawError, mirror `reportIncident`) HOẶC cap-403 phủ-bởi-200 (mirror `sendToLab`) | *[⚠️ post-AMENDMENT 2026-07-15: nay CÓ cap-403 `commissioning.write` @2768 — nhưng KẾT LUẬN GIỮ: cap-403 = raw `PermissionError` HTTP-403 status-line (KHÔNG `_err(403)`@200) ⇒ collapse CÙNG shape dispatcher-403 ⇒ VẪN SINGLE `Forbidden`, VẪN LOẠI dual-shape/phủ-200.]* SAI @source (record 2026-07-14): `receive_transfer` KHÔNG có `rbac.require` — 403 DUY NHẤT là dispatcher-403 (guest) = raw HTTP-403 status-line ⇒ SINGLE `Forbidden` (mirror `attachIncidentPhoto`). |
| C | 200 = SINGLE `ReceiveTransferEnvelope` (mirror `listTransfers` single-shape) | SAI error-mode: handler CÓ `try/except ValidationError → _err(…,422)` + service **2 nhánh `frappe.throw`** (phiếu∄ + sai-state) ⇒ HTTP-200 CÓ nhánh Error. SINGLE-shape bỏ Error = codegen KHÔNG deser được lỗi (phiếu∄/sai-state) → client crash/nuốt lỗi. `oneOf [Env, Error]` ĐÚNG. |
| D | `Error.http_status` khai **404** cho not-found (mirror `getTransfer` 404) | SAI @source: `confirm_receipt` dùng `frappe.throw` (`ValidationError`) → handler `_err(str(e), **422**)` @2606 — KHÔNG `_err(…, 404)`. CẢ not-found LẪN wrong-status về **422 ĐỒNG NHẤT**. Khai 404 = drift contract↔runtime (client route sai `body.http_status`). Description GHI RÕ 422-uniform (KHÔNG 404). |
| E | `ReceiveTransferResponse` = reuse `SendToLabResponse` (3-prop) | SAI dù CÙNG số key (3): field-set khác (`{name,status,sent_date}` vs `{name,status,received_by}`). `receiveTransfer` trả `{name,status,received_by}` @2708. reuse → `additionalProperties:false` validate-FAIL. Schema RIÊNG ĐÚNG. |
| F | `status` type `string` **plain (KHÔNG enum)** (mirror `receiveCertificate`/`cancelCalibration`) | LOẠI: `status` trả đơn-trị `"Received"` @2708 GROUNDED hằng `_TRANSFER_STATUS_RECEIVED` @2564 — acceptance yêu cầu **enum single-value `['Received']`** (mirror `sendToLab` khai enum). Khai enum `['Received']` = typed badge màn Điều chuyển, chống drift. TC-e import hằng LIVE assert equality (anti-bịa). |
| G | `handover_notes` `nullable:true` (mirror `sendToLab` optionals default None) | SAI @source: `handover_notes` default `""` empty-string @2601 (KHÔNG None) — never null. `nullable:true` sai wire-shape. NON-nullable optional-string (∉ required, KHÔNG nullable) ĐÚNG. |
| H | `ReceiveTransferRequest.required = [name, handover_notes]` (coi cả 2 bắt buộc) | SAI signature: `handover_notes` @2601 = **default `""`** (optional) — service chỉ patch khi truthy @2691-2692. required = **1 field `[name]`** (mirror `sendToLab` chỉ `name`). Ép `handover_notes` required = form mobile phải nhập ghi-chú thừa. |
| ✅ I | 1 path POST json+form body, 3 schema RIÊNG (Request req[name] + handover_notes optional NON-nullable · Response 3-prop `{name,status,received_by}` status enum `['Received']`), 200 oneOf [Env, Error], **403 SINGLE `Forbidden` dispatcher-only**, **Error 422-uniform**, `_MVP_ACTION_ENVELOPE` + `_REQBODY_PATHS`, tag `asset` | Grounded 1:1 source; blast-radius = +1 path +3 schema (PURE-YAML); codegen sinh 1 method xác-nhận-tiếp-nhận type-safe + response 3-prop → app "Xác nhận nhận bàn giao"; Decision-B intact; 403-slot sạch (dispatcher-only, 0 cap-403); status enum-grounded; naming-guard ∅; **MỞ NHÁNH transfer write-action** (approve/reject/create forward-reserve), đóng CR-TRANSFER-RECV-01. |

## Consequences

- **(+)** App mobile màn Điều chuyển có method `receiveTransfer` codegen-ready: bên nhận mở phiếu `Approved` → bấm "Xác nhận nhận bàn giao" (ghi-chú optional) → phiếu → `Received` + `received_by`/`received_date` + audit `Transfer` @2695 + lifecycle `transferred` @2701. **MỞ NHÁNH transfer write-action** (READ `getTransfer`/`listTransfers` đã curate; `approveTransfer`/`rejectTransfer`/`createTransfer` forward-reserve vòng kế mirror `sendToLab` R10). **CR-TRANSFER-RECV-01 ĐÓNG.**
- **(+)** Contract GROUNDED 1:1 source — 3 schema RIÊNG VERBATIM (`ReceiveTransferRequest` `req[name]` + `handover_notes` optional khớp signature @2601; `ReceiveTransferResponse` EXACT **3-prop** `{name,status,received_by}` @2708; `status.enum==['Received']` GROUNDED hằng `_TRANSFER_STATUS_RECEIVED` @2564); 403-slot SINGLE `Forbidden` dispatcher-only. **Naming guard:** `ReceiveTransfer*` ∩ mọi schema == ∅ (grep 0; prefix ≠ `ReceiveCertificate`/`Transfer`).
- **(+)** ~~**403 SINGLE dispatcher-only documented**~~ *[⚠️ SUPERSEDED 2026-07-15 — xem §AMENDMENT]* — **[nay]** 403 SINGLE `Forbidden` **REACHABLE cap-branch `commissioning.write`**: `confirm_receipt` `rbac.require(commissioning.write)` @2768 ⇒ cap-403 (mirror `approveTransfer`/`sendToLab`, KHÁC cap). 403-slot VẪN SINGLE `Forbidden` (schema BẤT BIẾN). **App CẦN gate nút "Xác nhận tiếp nhận" theo cap `commissioning.write`** (KHÁC record cũ nói "app KHÔNG cần gate").
- **(+)** **ANTI-DRIFT 422-uniform documented** — ĐIỂM KHÁC #2 vs `getTransfer` (READ cùng domain 404): `confirm_receipt` dùng `frappe.throw` (`ValidationError`) → handler `_err(str(e),422)` cho CẢ not-found LẪN wrong-status ⇒ `Error.http_status` 422 ĐỒNG NHẤT (KHÔNG 404). Description GHI RÕ để codegen consumer route `body.http_status` đúng (không mong đợi 404 từ endpoint này).
- **(+)** **Write-ACTION json+form** (mirror `sendToLab`/`cancelCalibration`, KHÁC 3 path multipart) — **∈ `_REQBODY_PATHS`** + subject sweep `_RPC_FORM_JSON_MEDIA` (KHÔNG exempt).
- **(+)** **`status` enum single-value `['Received']` GROUNDED verbatim hằng** (mirror `sendToLab` enum-khai, KHÁC `receiveCertificate`/`cancelCalibration` plain-string) — typed badge màn Điều chuyển; TC-e import hằng LIVE `_TRANSFER_STATUS_RECEIVED` assert equality (chống bịa/drift).
- **(+)** **CONTRACT-ONLY** — `receive_transfer` @2600-2606 + `confirm_receipt` @2677-2708 **byte-identical HEAD↔working** (git diff -U0 2 vùng TRỐNG round này — verified) ⇒ KHÔNG reload gunicorn, KHÔNG migrate ([AUTO], KHÔNG HARD-STOP USER); `test_oas_d12/d15/d17` UNCHANGED (pure mobile-yaml). 70 path cũ byte-identical.
- **(+)** Decision-B intact (0 discriminator; 2 nhánh oneOf disjoint required-set closed-schema); 0 dangling `$ref` (3 schema mới `$ref` ngay + tái-dùng `Unauthorized401`/`Forbidden`/`Error`).
- **(−)** **`handover_notes` NON-nullable optional** (KHÁC `sendToLab` optionals `nullable:true` default None) — vì default `""` @2601 (never null). Người bồi transfer-action tiếp PHẢI check default param (`""` vs None) TRƯỚC khi khai nullable. Ground bằng SOURCE (introspect signature default), KHÔNG copy schema anh-em.
- **(−)** **Response 3-prop RIÊNG** (KHÔNG reuse `SendToLabResponse` dù cùng 3-key) — field#3 `received_by` ≠ `sent_date`. Người bồi action IMM-00/transfer tiếp PHẢI grep `return {…}` @service TRƯỚC khi khai.
- **(−)** **Forward-reserve** `approveTransfer`/`rejectTransfer`/`createTransfer` — 3 action điều-chuyển còn lại CHƯA curate (vòng Trục-B kế, mirror cách `sendToLab` mở rồi `receiveCertificate`/`cancelCalibration` land sau). Backlog transfer write-action-set.
- **(−)** Đồng-bộ counter: `_EXPECTED_TEST_COUNT` `664→674` (test_mobile_oas, +10 TC class `TestMobileReceiveTransferContract` a..j) + `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `664→674` + `_GUARD_SUITE_SUM` `807→817` + `_MOBILE_OAS_TOTAL` `833→843` (= `_GUARD_SUITE_SUM` 817 + preflight 26) + c5 `59→60` + transition-baseline delta-var `receive_transfer_wire_delta=10` + ADR balance `42→43` (README ADR-row bắt-buộc — TC-MOB-DOC-02). ⚠️ **10 secondary count-guard KHÔNG dùng token `, 70,`** (3 c5 59→60 + 1 parity `_PARITY_BUSINESS_PATHS` 59→60 + 4 backward-compat opId-set-minus [transfer_p 68→69 / pmhist_j 69→70 / dept_h 69→70 / loc_h 69→70] + 2 hardcoded `_EXPECTED_TEST_COUNT==664` [receivecert_j / cancelcal_j] + op_id_unique `len(set)==70`) ⇒ **full-suite THẬT bắt sót** (RED-before demo: strip path → 93 FAIL gồm 6 receiveTransfer TC + path-count cascade → restore → GREEN).

---

## Handoff BE/Test (Bước-4 — ĐÃ XONG pure-yaml, ATOMIC)

> **CONTRACT-ONLY — ĐÃ HOÀN TẤT vòng Bước-2 (BA tự code+verify pure-yaml full path-add):** TUYỆT ĐỐI KHÔNG đụng `api/imm00.py`/`services/imm00.py` (`receive_transfer` @2600 / `confirm_receipt` @2677 ĐÃ LIVE byte-identical HEAD↔working). Không reload/migrate/commit. DoD ĐÃ VERIFY: `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **'Ran 674 OK' THẬT** (RED-before strip-path → 93 FAIL → restore → GREEN) · `.test_mobile_docset` = **Ran 9 OK** (balance 43==43).

**(1) yaml** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`) — ĐÃ BỒI:
- +1 path `POST /api/method/assetcore.api.imm00.receive_transfer` (opId `receiveTransfer`, **tag `asset`**); requestBody `required:true` content **2 media-type** `application/json` + `application/x-www-form-urlencoded` (CÙNG `schema.$ref ReceiveTransferRequest`); 200 = `oneOf [ReceiveTransferEnvelope, Error]`; slot `{200,401,403}` (`401 Unauthorized401`, **`403 Forbidden` SINGLE-SHAPE dispatcher-only**). **description path GHI RÕ 422-uniform (KHÔNG 404) + 403 dispatcher-only (0 cap-403).**
- +3 schema (`ReceiveTransferRequest` closed `req[name]` — `name`:`{type:string}` + `handover_notes:{type:string}` NON-nullable optional · `ReceiveTransferResponse` closed EXACT `req[name,status,received_by]` — `status:{type:string, enum:['Received']}` · `ReceiveTransferEnvelope` closed `req[success,data]` `success.enum[true]` `data=$ref ReceiveTransferResponse`). Cả 3 `additionalProperties:false`. Tái-dùng `Unauthorized401`/`Forbidden`/`Error`. 0 orphan, 0 dangling.

**(2) test_mobile_oas.py** — ĐÃ BỒI: path/opId `70→71`; `_EXPECTED` += `("/api/method/assetcore.api.imm00.receive_transfer": ("post","receiveTransfer"))`; path ∈ `_MVP_BUSINESS_PATHS` + `_MVP_ACTION_ENVELOPE`; c5 map += `receiveTransfer→ReceiveTransferEnvelope` (`59→60`); +1 TC class `TestMobileReceiveTransferContract` (a..j, 10 TC); `_EXPECTED_TEST_COUNT` `664→674`; bulk-bump `, 70,`→`, 71,` (141) + 8 secondary guard (op_id_unique 70→71 · c5 59→60 ×3 · parity 59→60 · backward-compat transfer_p 68→69 / pmhist_j 69→70 / dept_h 69→70 / loc_h 69→70 · hardcoded `_EXPECTED_TEST_COUNT` 664→674 ×2). TC-e import hằng LIVE `_TRANSFER_STATUS_RECEIVED` assert `status.enum==['Received']`. TC-g assert `422 ∈ Error.http_status` (KHÔNG assert 404). TC-i live-sig `{name, handover_notes}` + `handover_notes.default==''`.

**(3) test_mobile_docset.py** — ĐÃ BỒI: `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` `664→674` · `_GUARD_SUITE_SUM` `807→817` · `_MOBILE_OAS_TOTAL` `833→843` (=817+26) + transition-baseline delta-var `receive_transfer_wire_delta=10` (giữ `pre_fc3_six==191`). ADR-MOBILE-043 registered README (TC-MOB-DOC-02 glob động — balance ADR-on-disk 43 == README-index 43).

**(4) docs narrative** — ĐÃ XONG: `04-api-contract.md` (§8.45 `receiveTransfer`) + README ADR-row (ADR-MOBILE-043, balance 42→43) + Core Doc [`05_API_Specification.md`](../imm-00/05_API_Specification.md) §receive_transfer 📱 mobile-binding. Feature-12 §2 (mobile repo) ĐÃ liệt kê `receiveTransfer` — no cross-ref, KHÔNG chỉnh feature doc.

**MỞ NHÁNH TRANSFER WRITE-ACTION** (receiveTransfer CR-TRANSFER-RECV-01 mở). Domain Điều chuyển nay có write-action ĐẦU TIÊN mobile: xác nhận tiếp nhận (Approved→Received). Forward-reserve: `approveTransfer`/`rejectTransfer`/`createTransfer` (vòng Trục-B kế).
