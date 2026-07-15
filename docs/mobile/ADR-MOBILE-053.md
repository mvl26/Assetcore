# ADR-MOBILE-053 — `getCommissioning` (`imm04.get_form_context`) curate vào OAS mirror (**CR-25 · MỞ NHÁNH IMM-04 F6-DETAIL "Tiếp nhận & Nghiệm thu hiện trường"** — bồi ĐÚNG 1 GET-detail path trả phiếu nghiệm thu hiện trường CHI TIẾT (header 44-field + `baseline_tests[]` + `commissioning_documents[]` + `lifecycle_events[]` + `allowed_transitions[]` CTA) phục vụ nghiệm thu/lắp đặt thiết bị; DETAIL-sibling của `listCommissioning` ADR-MOBILE-048; 200 = inline `oneOf [CommissioningDetailEnvelope, Error]` Decision-B; ⚠️ payload OPEN `additionalProperties:true` theo parity 8 `*Detail`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-053 |
| Phase | C — API contract (codegen-ready) |
| Ngày | 2026-07-15 |
| Tác giả | BE (mobile contract curate) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; oneOf KHÔNG discriminator) · **DETAIL-sibling trực-tiếp**: **ADR-MOBILE-048** (`listCommissioning` — LIST-ENTRY CÙNG màn F6, CÙNG DocType `Asset Commissioning`, tag `commissioning`) · **precedent DETAIL trực-tiếp**: **ADR-MOBILE-050** (`getAllocation` OPEN detail) + **ADR-MOBILE-052** (`getInternalAudit` OPEN detail) · **precedent shape**: 8 `*Detail` (`CalibrationDetail`/`SpareAllocationDetail`/`InternalAuditDetail`/`TransferDetail`…) đều OPEN · Core Doc IMM-04 [`docs/imm-04/05_API_Specification.md`](../imm-04/05_API_Specification.md) |

---

> ⚠️ **SUPERSEDE-IN-PART (2026-07-15, CR-25-FIX vòng 47 → [`ADR-MOBILE-055`](./ADR-MOBILE-055.md)):** claim shape `allowed_transitions = array[string]` ở **§(c) bullet-3 (dòng 57)** + **§4 `test_detail_child_refs_resolve`** + **§4 "5 schema"** là **SAI wire** — `get_form_context` gán `_get_workflow_transitions()` (`services/imm04.py:667-678`) trả **`list[dict]{action,next_state,allowed_role}`**, KHÁC 4 sibling (`array[string]` từ `_*_VALID_TRANSITIONS` map). ADR-MOBILE-055 sửa → `allowed_transitions.items = $ref CommissioningTransitionItem` (`array[object]`, +1 schema CLOSED ⇒ **6 schema**). Phần còn lại ADR-053 (Decision-B / opId-domain / Check→int / date-string / OPEN-vs-CLOSED SC#2) **GIỮ NGUYÊN**.

## 1. Bối cảnh

Màn **F6 "Tiếp nhận & Nghiệm thu hiện trường"** đã có LIST-ENTRY (`listCommissioning`, ADR-MOBILE-048). Bước kế: mở 1 phiếu để xem **CHI TIẾT** — header phiếu + bảng kiểm nghiệm thu (`baseline_tests[]`) + hồ sơ nghiệm thu (`commissioning_documents[]`) + sự kiện vòng đời (`lifecycle_events[]`) + nút hành động (gate theo `allowed_transitions`). Đây là **DETAIL-sibling** của `listCommissioning` (KHÁC LIST: không phân trang; thay vào đó 1 phiếu + 3 child table). Endpoint **ĐÃ LIVE** ở web-BE. ADR này curate **contract-only** (0 `.py` runtime change / 0 reload / 0 migrate).

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler `get_form_context` @`api/imm04.py:19` — `@frappe.whitelist()` **bare** (no `allow_guest`, no `rbac.require`) → GET nhận; guest/no-token/thiếu DocPerm → **dispatcher-403**. Chữ ký = `get_form_context(name: str)` = **ĐÚNG 1 param** (`name`, KHÔNG default ⇒ **required**). Thân = `return _handle(svc.get_form_context, name)` ⇒ mọi lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`.
- Service `get_form_context` @`services/imm04.py:796-808`:
  ```python
  doc = CommissioningRepo.get(name)
  if not doc:
      nthrow(MSG.IMM04_NOT_FOUND, name=name)        # → _err TRÊN HTTP-200, KHÔNG status-line 404
  frappe.has_permission(_DT, ptype="read", doc=name, throw=True)  # PermissionError → FORBIDDEN
  result = _serialize_commissioning(doc)            # ⚠️ dict CURATED (KHÔNG doc.as_dict)
  result["allowed_transitions"] = _get_workflow_transitions(name)  # CTA server-driven @:807
  return result
  ```
- `_serialize_commissioning` @`services/imm04.py:728-791` = **dict CURATED 44 field header** (`@:743-790`, KHÔNG `doc.as_dict()`) + 3 enrich display-name (`master_item_name`/`vendor_name`/`clinical_dept_name` @`:734-741`) + 3 child serializer.
- 3 child serializer: `_serialize_baseline_tests` @`:681` (child `Commissioning Checklist` — 11 field) · `_serialize_comm_documents` @`:697` (child `Commissioning Document Record` — 9 field) · `_serialize_lifecycle_events` @`:712` (child `lifecycle_events` — 8 field).

---

## 2. Quyết định

### (a) 200 = **inline** `oneOf [CommissioningDetailEnvelope, Error]` — Decision-B

Mirror `getAllocation` R42 / `getInternalAudit` R44 / `getCalibration`: 200 content.schema = `oneOf` 2 nhánh (KHÔNG response-component, KHÔNG discriminator) → route theo `body.success`. `IMM04_NOT_FOUND` (phiếu∄ @`:801`) đến TRÊN HTTP-200 — KHÔNG status-line 404. status-set `[200, 401, 403]` (bare @whitelist: guest dispatcher-403 + bearer-expired 401). `get_form_context` ∈ `_MVP_READ_ENVELOPE` (KHÔNG `_MVP_LIST_ENVELOPE` — detail ≠ list ⇒ `_MVP_LIST_ENVELOPE` GIỮ 12).

### (b) operationId theo **DOMAIN** (`getCommissioning`), KHÔNG theo tên hàm

Tên hàm backend `get_form_context` **generic** (không mang ngữ nghĩa domain). Đặt opId theo DOMAIN `getCommissioning` — nhất quán precedent `getRepairWorkOrder`/`getAllocation`/`getInternalAudit` (opId ≠ tên hàm khi tên hàm không rõ domain). Codegen sinh method `getCommissioning()` đọc-được. Entry ghi vào `_EXPECTED` registry map (`test_mobile_oas.py`).

### (c) ⚠️ `CommissioningDetail` + 3 child = **`additionalProperties: true` (OPEN)**, chỉ envelope CLOSED — theo **parity 8 `*Detail`**

Khác `getAllocation`/`getInternalAudit` (OPEN vì `doc.as_dict()` surface), `get_form_context` trả **dict CURATED** (`_serialize_commissioning` liệt kê tường minh 44 khoá — KHÔNG `as_dict()`), nên về lý-thuyết CÓ THỂ khai CLOSED-exact. **Quyết định GIỮ OPEN** vì:

1. **Nhất-quán precedent**: cả 8 `*Detail` hiện có (`CalibrationDetail`/`SpareAllocationDetail`/`InternalAuditDetail`/`TransferDetail`…) đều OPEN. Một `*Detail` CLOSED lẻ loi = ngoại lệ khó nhớ, dễ gây tranh cãi "sao cái này khác".
2. **Chi phí bảo trì**: CLOSED-exact đòi key-parity 44+ field ↔ serializer — mọi lần BE thêm 1 khoá vào `_serialize_commissioning` mà quên cập YAML ⇒ strict codegen reject-valid-row (CRASH). OPEN chịu-được thêm-khoá additive (Hyrum-safe).
3. **CHỈ `CommissioningDetailEnvelope` = CLOSED** (mirror `SpareAllocationDetailEnvelope`) — grounded `_ok(result)` @`utils/response.py:92` = `{success:True, data}` (đúng 2 khoá, đóng an-toàn cho route-by-VALUE `body.success`).

**Chống false-green KHÔNG bằng closed-exact-parity mà bằng:**
- **live-signature parity** (`test_live_signature_parity`): `inspect.signature(imm04.get_form_context).parameters == {name}` — chặn drift chữ ký (endpoint LIVE).
- **no-orphan + all-refs-resolve** (`test_yaml_loads_all_refs_resolve_no_orphan`): 5 schema mới đều `$ref`'d, 0 dangling.
- **header field-sample present** (`test_detail_child_refs_resolve`): 10 field header đại diện + 3 child array $ref + `allowed_transitions` array[string] — chặn stub/rỗng detail.

### (d) 4 doc-level Check + 3 child Check → **`type:integer enum[0,1]`** (CR-01 family, KHÔNG boolean)

- Doc-level: `facility_checklist_pass` (`or 0` @`:765`) · `is_radiation_device` (raw @`:771`) · `doa_incident` (raw @`:772`) · `documents_incomplete` (`or 0` @`:773`).
- Child: `is_critical`/`na_applicable` (`BaselineTestItem` @`:687`/`:691`) · `is_mandatory` (`CommissioningDocumentItem` @`:703`).

Frappe `Check` fieldtype → wire emit **raw int 0|1** (KHÔNG `true`/`false`). Khai `boolean` = strict Dart/Kotlin codegen deser **CRASH** trên `0`/`1` int payload (CR-01 family — cùng lỗi `is_active`/`is_group` các round ref-data). ⚠️ Phân biệt: `is_locked` @`:786` = Python bool THẬT (`doc.docstatus==1`) → khai `boolean` ĐÚNG. `current_user_roles` @`:787` = `frappe.get_roles()` → `array<string>`.

### (e) Select leading-blank → **`type:string` KHÔNG hard-enum** (ADR-MOBILE-051 §2.c.1)

`risk_class` (NĐ98) / `overall_inspection_result` (doc) + `test_result`/`measurement_type` (baseline child) + `doc_type`/`status` (document child) khai `type:string` KHÔNG hard-enum: DocType Select leading-blank ⇒ `""` là value đã-persist hợp-lệ; hard-enum reject `""` → strict-codegen CRASH. ⚠️ `risk_class` = phân loại NĐ98 (A/B/C/D) — **KHÁC** `risk_classification` (Low/Med/High/Critical); cite `field+doctype` để không lẫn (LL-BE-58).

### (f) tag `commissioning` (REUSE ADR-MOBILE-048 — module-tag IMM-04)

### (g) CONTRACT-ONLY

BE LIVE @`api/imm04.py:19` + `services/imm04.py:796`. Curate PURE-YAML + guard test. 0 `.py` runtime change / 0 gunicorn reload / 0 `bench migrate`.

---

## 3. Path + param

```
/api/method/assetcore.api.imm04.get_form_context  (GET, opId getCommissioning, tag [commissioning])
  param name: in:query, required:true, schema.type:string
  200: inline oneOf [CommissioningDetailEnvelope, Error]
  401: $ref Unauthorized401   403: $ref Forbidden
```

- Đặt **liền sau** block `listCommissioning` (CR-25a) trong `paths:` + 5 schema đặt **liền sau** `CommissioningListEnvelope` trong `components.schemas:` — giữ cụm IMM-04 liền mạch.

---

## 4. Guard test (`test_mobile_oas.py` — class RIÊNG `TestMobileGetCommissioningDetail`, 9 TC)

- **test_path_and_operation_present** — path tồn tại + CHỈ GET + opId `getCommissioning` (theo DOMAIN) + tag `[commissioning]`; ∈ `_MVP_BUSINESS_PATHS`; ∉ `_STUB_PATHS`/`_MVP_LIST_ENVELOPE`; ∈ `_MVP_READ_ENVELOPE`.
- **test_param_name_required_query** — ĐÚNG 1 param `name` typed (query/required/string); KHÔNG requestBody.
- **test_200_oneof_envelope_error_decisionB** — 200 oneOf ĐÚNG 2 `[CommissioningDetailEnvelope, Error]` 0-discriminator; 401/403 uniform; status-set `[200,401,403]`.
- **test_envelope_closed_success_const** — `CommissioningDetailEnvelope` CLOSED; `required⊇{success,data}`; `success` const/enum true; `data.$ref → CommissioningDetail`.
- **test_detail_child_refs_resolve** — `CommissioningDetail` OPEN; `required:[name]`; 3 child array `$ref` đúng child (`BaselineTestItem`/`CommissioningDocumentItem`/`CommissioningLifecycleEventItem`) + resolve + child OPEN; `allowed_transitions` array[string]; header field-sample ⊆ props; `current_user_roles` array.
- **test_check_flags_typed_integer** — 4 doc-level Check + `is_critical`/`na_applicable` (baseline) + `is_mandatory` (document) = `type:integer enum[0,1]` (KHÔNG boolean).
- **test_path_count_increments_by_one** — assert-delta `len(paths)==len(paths∖getCommissioning)+1` (chống hardcode) + reconcile: paths 84, opId 84, c5 73 == `_MVP_BUSINESS_PATHS` == `_PARITY_BUSINESS_PATHS`, `_MVP_LIST_ENVELOPE` GIỮ 12.
- **test_yaml_loads_all_refs_resolve_no_orphan** — mọi `$ref` resolve; 5 schema mới KHÔNG orphan.
- **test_live_signature_parity** — signature parity `get_form_context(name)=={name}` (CONTRACT-ONLY, endpoint LIVE).

### Bulk-bump bookkeeping (reconcile — ghi rõ để cân guard)

- `_EXPECTED_TEST_COUNT` 758 → **767** (+9).
- path/opId count 83 → **84**; c5 72 → **73**; `_PARITY_BUSINESS_PATHS` 72 → **73**; `_MVP_LIST_ENVELOPE` GIỮ **12**.
- `_EXPECTED` registry map += `get_form_context → (get, getCommissioning)`.
- cross-file `test_mobile_docset.py`: `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 758 → **767**; `_GUARD_SUITE_SUM` 901 → **910**; `_MOBILE_OAS_TOTAL` 927 → **936**; transition-baseline delta `getcommissioning_detail_delta = 9`.
- backward-compat frozen-delta các test khác bump theo tổng (`set(ids)-{...}` 82→83 / 81→82); 2 counter-guard `_EXPECTED_TEST_COUNT, 758→767`.

---

## 5. Hệ quả

- **+**: màn F6 detail codegen-ready; FE mobile bind header + bảng kiểm nghiệm thu + hồ sơ + lifecycle + CTA gate từ 1 typed envelope; false-green chặn bằng signature + no-orphan + header-sample guard.
- **+**: nhất-quán 8 `*Detail` OPEN — KHÔNG đẻ pattern closed-detail lẻ loi.
- **−/đánh đổi**: payload OPEN ⇒ codegen model có `additionalProperties` escape-hatch (khoá ngoài 44+3-child không typed) — CHẤP NHẬN (parity + Hyrum-safe additive). Nếu sau này cần typed-strict cho DETAIL curated này, có thể đổi sang CLOSED-exact bằng ADR mới Supersede (BE trả dict CURATED nên khả-thi, khác as_dict).
- **submit_baseline_checklist** (op WRITE còn lại của F6) vẫn **PENDING** — curate vòng kế (CONTRACT-REQUESTS CR-25).
- **KHÔNG** đổi backend / workflow / DocType. CONTRACT-ONLY.
