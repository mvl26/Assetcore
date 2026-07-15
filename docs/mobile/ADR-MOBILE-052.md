# ADR-MOBILE-052 — `getInternalAudit` (`imm16.get_audit`) curate vào OAS mirror (**CR-27b · MỞ NHÁNH IMM-16 F7-DETAIL "Audit nội bộ (checklist hiện trường)"** — bồi ĐÚNG 1 GET-detail path trả phiên audit nội bộ CHI TIẾT (header + `checklist_items[]` child + `findings[]` child + `allowed_transitions[]` CTA + `can_operate`/`can_close`) phục vụ Compliance/QMS; DETAIL-sibling của `listInternalAudits` ADR-MOBILE-051; 200 = inline `oneOf [InternalAuditDetailEnvelope, Error]` Decision-B; ⚠️ payload OPEN `additionalProperties:true` vì `doc.as_dict()`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-052 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-15 |
| Tác giả | BA (mobile contract curate) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; oneOf KHÔNG discriminator) · **DETAIL-sibling trực-tiếp**: **ADR-MOBILE-051** (`listInternalAudits` — LIST-ENTRY CÙNG màn F7, CÙNG DocType `IMM Internal Audit`, tag `compliance`) · **mở rộng trực-tiếp**: **ADR-MOBILE-050** (`getAllocation` — payload OPEN vì `doc.as_dict()` surface; `get_audit` COPY Y HỆT pattern) · **precedent shape**: 6 `*Detail` as_dict-based (`CalibrationDetail`/`SpareAllocationDetail`/`TransferDetail`…) · Core Doc IMM-16 [`docs/imm-16/05_API_Specification.md §3.3.2`](../imm-16/05_API_Specification.md) (ADR-IMM-16-02 CTA server-driven) |

---

## 1. Bối cảnh

Màn **F7 "Audit nội bộ (checklist hiện trường)"** đã có LIST-ENTRY (`listInternalAudits`, ADR-MOBILE-051). Bước kế: mở 1 phiên để xem **CHI TIẾT** — header phiên + bảng kiểm (`checklist_items[]`) + phát hiện (`findings[]`) + nút hành động (Bắt đầu / Nhập bảng kiểm / Đóng) gate theo `allowed_transitions`. Đây là **DETAIL-sibling** của `listInternalAudits` (KHÁC LIST: không phân trang; thay vào đó 1 phiên + 2 child table CỦA phiên). Endpoint **ĐÃ LIVE** ở web-BE. ADR này curate **contract-only** (0 `.py` runtime change / 0 reload / 0 migrate).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler `get_audit` @`api/imm16.py:246` — `@frappe.whitelist()` **bare** (no `allow_guest`, no `rbac.require`) → GET nhận; guest/no-token/thiếu DocPerm → **dispatcher-403**. Chữ ký = `get_audit(name: str)` = **ĐÚNG 1 param** (`name`, KHÔNG default ⇒ **required**). Thân = `return _handle(svc.get_audit, name)` ⇒ mọi lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`.
- Service `get_audit` @`services/imm16.py:1626-1640`:
  ```python
  doc = InternalAuditRepo.get(name)
  if not doc: raise ServiceError(ErrorCode.NOT_FOUND, ...)   # → _err TRÊN HTTP-200
  data = doc.as_dict()                                        # ⚠️ FULL as_dict surface
  if data.get("lead_auditor"):
      data["lead_auditor_name"] = User.full_name | lead_auditor   # OPTIONAL enrich
  data["allowed_transitions"] = _AUDIT_VALID_TRANSITIONS.get(doc.status, [])  # GATE-8/ADR-IMM-16-02
  data["can_operate"] = rbac.can(compliance.write)           # boolean
  data["can_close"]   = rbac.can(compliance.approve)         # boolean
  return data
  ```
- DocType `IMM Internal Audit` (header) + child `IMM Audit Checklist Item` (`checklist_items[]`) + child `Audit Finding` (`findings[]`) — field-set VERBATIM @doctype JSON.

---

## 2. Quyết định

### (a) 200 = **inline** `oneOf [InternalAuditDetailEnvelope, Error]` — Decision-B

Mirror `getAllocation` R42 / `getCalibration`: 200 content.schema = `oneOf` 2 nhánh (KHÔNG response-component, KHÔNG discriminator) → route theo `body.success`. `NOT_FOUND` (phiên∄ @`:1629`) đến TRÊN HTTP-200 — KHÔNG status-line 404. status-set `[200, 401, 403]` (bare @whitelist: guest dispatcher-403 + bearer-expired 401). `get_audit` ∈ `_MVP_READ_ENVELOPE` (KHÔNG `_MVP_LIST_ENVELOPE` — detail ≠ list ⇒ `_MVP_LIST_ENVELOPE` GIỮ 12).

### (b) ⚠️ SELF-CORRECTION (MAJOR) — `InternalAuditDetail` + 2 child = **`additionalProperties: true` (OPEN)**, chỉ envelope CLOSED

**Acceptance CR-27b mâu thuẫn nội tại:** yêu cầu "cả 4 schema closed (`additionalProperties:false`) + key-parity EXACT với live emit" NHƯNG ĐỒNG THỜI yêu cầu "parity `getAllocation` R42" — mà R42 = detail **OPEN** (ADR-MOBILE-050). Không thể vừa closed-exact vừa parity-R42.

**Nguyên nhân gốc:** `get_audit` trả `doc.as_dict()` surface (`services/imm16.py:1630`) **Y HỆT** `get_allocation` (`services/imm15.py:224`). `as_dict()` LUÔN emit meta Frappe (`name/owner/creation/modified/modified_by/docstatus/idx/doctype/_user_tags/_comments/_assign/_liked_by`; child rows thêm `parent/parentfield/parenttype/idx/name`) VƯỢT danh sách field nghiệp-vụ. `additionalProperties:false` trên as_dict surface = **hợp đồng nói dối** → strict Dart/Kotlin codegen deser **CRASH** trên meta-key (CÙNG loại rủi ro codegen mà acceptance lo ở cấp enum — ADR-MOBILE-051 §2.c.1 — nhưng ở cấp object).

**Quyết định:** `InternalAuditDetail` + `InternalAuditChecklistItem` + `AuditFindingItem` = **OPEN**; CHỈ `InternalAuditDetailEnvelope` = CLOSED (mirror `SpareAllocationDetailEnvelope`). "closed" trong acceptance là **copy nhầm từ precedent R43 list-item** (`InternalAuditListItem`): LIST dùng `InternalAuditRepo.list` trả CURATED `fields=8` → closed HỢP-LỆ cho LIST; nhưng DETAIL = as_dict → PHẢI OPEN. Precedent nhất-quán: **cả 6 `*Detail` as_dict-based hiện có đều OPEN**.

**Chống false-green KHÔNG bằng closed-exact-parity (bất khả thi với as_dict), mà bằng:**
1. **TC-live subset-guard** (`test_mob_oas_auditdetail_live_field_domain_subset`): `props ⊆ (doctype fieldnames ∪ enrich extra-keys)` — chặn field BỊA (không có ở backend).
2. **live-signature parity**: `inspect.signature(imm16.get_audit).parameters == {name}` — chặn drift chữ ký.

### (c) enum theo quy-tắc **leading-blank Select** (ADR-MOBILE-051 §2.c.1)

`audit_type`/`status` (header) + `result`/`category` (checklist child) + `severity`/`category`/`capa_status` (finding child) khai **`type:string` KHÔNG hard-enum**. Lý do: DocType Select có leading-blank option (hoặc `reqd=None`) ⇒ `""` là value đã-persist hợp-lệ; hard-enum reject `""` → strict-codegen CRASH. Nhất-quán 1 quy-tắc cho MỌI child Select (kể cả `severity` reqd=1 — tránh reasoning per-field dễ sai).

### (d) enrich/CTA field

- `lead_auditor_name`: `type:string`, **OPTIONAL** (∉ `required` — CHỈ set khi `lead_auditor` truthy @`:1631-1634`).
- `allowed_transitions`: `array<string>` (CTA server-driven @`:1637`; FE gate nút theo `includes`, KHÔNG hardcode `status===` — GATE-8/LL-FE-51).
- `can_operate` / `can_close`: **`type:boolean`** (rbac.can @`:1638-1639` — Python bool, KHÔNG Check int-0/1).
- `checklist_items`: `array` `$ref InternalAuditChecklistItem`.
- `findings`: `array` `$ref AuditFindingItem` — **BẮT BUỘC khai** (as_dict LUÔN kèm child table `findings[]` → nếu bỏ, người đọc contract tưởng không có).

### (e) tag `compliance` (REUSE ADR-MOBILE-051 — module-tag IMM-16)

### (f) CONTRACT-ONLY

BE LIVE @`api/imm16.py:246` + `services/imm16.py:1626`. Curate PURE-YAML + guard test. 0 `.py` runtime change / 0 gunicorn reload / 0 `bench migrate`.

---

## 3. Path + param

```
/api/method/assetcore.api.imm16.get_audit  (GET, opId getInternalAudit, tag [compliance])
  param name: in:query, required:true, schema.type:string
  200: inline oneOf [InternalAuditDetailEnvelope, Error]
  401: $ref Unauthorized401   403: $ref Forbidden
```

- Đặt **liền sau** block `listInternalAudits` (CR-27a) trong `paths:` + schema đặt **liền sau** `InternalAuditListEnvelope` trong `components.schemas:` — giữ nhánh IMM-16 liền mạch.

---

## 4. Guard test (`test_mobile_oas.py` — class RIÊNG `TestMobileGetInternalAuditDetailContract` a..g + live)

- **a** — YAML load + mọi `$ref` resolve + 4 schema mới KHÔNG orphan.
- **b** — path tồn tại + CHỈ GET + opId `getInternalAudit` + tag `[compliance]`; ∈ `_MVP_BUSINESS_PATHS`; ∉ `_STUB_PATHS`/`_MVP_LIST_ENVELOPE`; ∈ `_MVP_READ_ENVELOPE`.
- **c** — ĐÚNG 1 param `name` typed (query/required/string); KHÔNG requestBody.
- **d** — 200 oneOf ĐÚNG 2 `[InternalAuditDetailEnvelope, Error]` 0-discriminator; 401/403 uniform.
- **e** — `InternalAuditDetail` OPEN; `required:[name]`; `checklist_items`/`findings` array `$ref` đúng child; `allowed_transitions` array; `can_operate`/`can_close` boolean; `lead_auditor_name` ∈ props; `audit_type`/`status` string-no-enum.
- **f** — 2 child OPEN; props ⊇ field nghiệp-vụ; `result`/`category`/`severity`/`capa_status` string-no-enum.
- **g** — reconcile count: paths 83, opId 83, c5 72 == `_MVP_BUSINESS_PATHS`, `_PARITY_BUSINESS_PATHS` 72, `_MVP_LIST_ENVELOPE` GIỮ 12.
- **live** — subset-guard (`props ⊆ doctype ∪ enrich`, cả 3 schema) + signature parity `get_audit(name)=={name}`.

### Bulk-bump bookkeeping (reconcile — ghi rõ để cân guard)

- `_EXPECTED_TEST_COUNT` 750 → **758** (+8).
- path/opId count 82 → **83**; c5 71 → **72**; `_PARITY_BUSINESS_PATHS` 71 → **72**.
- cross-file `test_mobile_docset.py`: `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 750 → **758**; `_GUARD_SUITE_SUM` 893 → **901**; `_MOBILE_OAS_TOTAL` 919 → **927**; transition-baseline delta `get_internal_audit_detail_delta = 8`.

---

## 5. Hệ quả

- **+**: màn F7 detail codegen-ready; FE mobile bind header + bảng kiểm + phát hiện + CTA gate từ 1 typed envelope; false-green chặn bằng subset + signature guard.
- **+**: nhất-quán ADR-MOBILE-050 (OPEN detail as_dict) — KHÔNG đẻ pattern closed-lie mới.
- **−/đánh đổi**: payload OPEN ⇒ codegen model có `additionalProperties` escape-hatch (meta Frappe không typed) — CHẤP NHẬN (đúng bản chất as_dict; giống 6 `*Detail` hiện có). Nếu sau này cần typed-strict, phải đổi BE trả curated dict (KHÔNG `as_dict()`) — ADR mới Supersede.
- **KHÔNG** đổi backend / workflow / DocType. CONTRACT-ONLY.
