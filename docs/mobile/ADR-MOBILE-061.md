# ADR-MOBILE-061 — `submitBaselineChecklist` (`imm04.submit_baseline_checklist`) curate vào OAS mirror (**CR-25c · MỞ NHÁNH IMM-04 F6-WRITE "Tiếp nhận & Nghiệm thu hiện trường"** — bồi ĐÚNG 1 POST write-action nộp bảng-kiểm cơ-sở (Initial Inspection → `overall_result='Pass'` + `clinical_hold_required`), WRITE-op ĐẦU TIÊN & DUY NHẤT của cụm F6 sau `listCommissioning`/`getCommissioning`; 200 = inline `oneOf [SubmitBaselineChecklistEnvelope, Error]` Decision-B; **HOÀN TẤT 3/3 core commissioning ops** list+get+submit)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-061 |
| Phase | C — API contract (codegen-ready) — CONTRACT-ONLY (0 `.py` runtime) |
| Ngày | 2026-07-18 |
| Tác giả | BA (spec CR-25c) → BE (Bước-4 curate YAML + guard test + doc) |
| **Status** | **Accepted** |
| Bám quyết định | **ADR-MOBILE-001** (Decision-B — lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`, route theo `body.success`; `200`-oneOf KHÔNG discriminator) · **cụm F6 sibling**: **ADR-MOBILE-048** (`listCommissioning` — LIST-ENTRY) + **ADR-MOBILE-053** (`getCommissioning` — DETAIL) + **ADR-MOBILE-055** (transitions fix) — CÙNG DocType `Asset Commissioning`, tag `commissioning` · **precedent write-action envelope**: `submitPmResult` (`PmSubmitResultEnvelope`, yaml action-envelope 2-nhánh closed-schema route-by-VALUE) · **precedent Hyrum keep-name**: **ADR-MOBILE-060** §CR-27a (`getInternalAudit` GIỮ, KHÔNG rename `getAudit`) · **domain SoT**: Core Doc IMM-04 [`../imm-04/05_API_Specification.md`](../imm-04/05_API_Specification.md) BR-04-04 / VR-07 |

---

## 1. Bối cảnh

Màn **F6 "Tiếp nhận & Nghiệm thu hiện trường"** (IMM-04) đã có 2 op READ: `listCommissioning` (ADR-MOBILE-048) + `getCommissioning` (ADR-MOBILE-053, transitions fix ADR-MOBILE-055). Op còn thiếu để đóng luồng nghiệm thu = **WRITE**: kỹ-thuật-viên/QA nộp **bảng-kiểm cơ-sở** (`baseline_tests[]`) khi phiếu ở trạng thái **Initial Inspection** — ghi `measured_val`/`test_result`/`fail_note` từng dòng, chốt kết-luận `overall_result='Pass'` và tính cờ **`clinical_hold_required`** (VR-07: thiết-bị Class C/D/Radiation cần giữ lâm-sàng). Đây là WRITE-op **ĐẦU TIÊN & DUY NHẤT** của cụm F6 (2 op NC còn lại `list_non_conformances`/`report_nonconformance` = backlog riêng — xem §5).

Endpoint `submit_baseline_checklist` **ĐÃ LIVE** @web-BE ⇒ round này **CONTRACT-ONLY**: curate 1 path + 4 schema + guard test + doc, **0** `.py`/reload/migrate/commit.

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- Handler @`api/imm04.py:155-162` = `@frappe.whitelist(methods=["POST"])` + **`rbac.require("commissioning.write")` @`:157` TRƯỚC `_handle`** ⇒ cap-403 **REACHABLE HTTP-403 THẬT** (KHÁC bare-whitelist read F6). Chữ ký = `submit_baseline_checklist(name: str, results: str = "")` — `name` positional (required) + `results` = JSON-string (`_parse_json(results, default=[])` @`:159`). Thân = `return _handle(svc.submit_baseline_checklist, name, parsed)`.
- Service `submit_baseline_checklist(name, results)` @`services/imm04.py:1437-1456`:
  ```python
  doc = CommissioningRepo.get(name)
  if not doc:
      raise ServiceError(ErrorCode.NOT_FOUND, ...)          # → _err TRÊN HTTP-200, KHÔNG status-line 404
  if doc.workflow_state != _STATE_INITIAL_INSPECTION:
      raise ServiceError(ErrorCode.INVALID_PARAMS, ...)     # gate state ≠ Initial Inspection
  result_map = {r.get("parameter"): r for r in results}     # khoá `parameter`
  for row in doc.baseline_tests or []:                      # ghi measured_val/test_result/fail_note
      ...
  fails = [r.parameter for r in (doc.baseline_tests or []) if r.test_result == "Fail"]
  if fails:
      raise ServiceError(ErrorCode.VALIDATION, f"BR-04-04: Thông số sau không đạt: {', '.join(fails)}")
  is_high_risk = check_auto_clinical_hold(doc)              # VR-07 -> bool
  doc.overall_inspection_result = "Pass"
  doc.save(ignore_permissions=True)
  return {"name": doc.name, "overall_result": "Pass", "clinical_hold_required": is_high_risk}
  ```
- `check_auto_clinical_hold(doc) -> bool` @`services/imm04.py:405-410`: `high_risk = doc.risk_class in ("C","D","Radiation") if doc.risk_class else bool(doc.is_radiation_device)` — **kết-quả toán-tử `in`/`bool()` = Python `bool` THẬT**, KHÔNG đọc thẳng Frappe `Check` docfield.

---

## 2. Quyết định

### (a) 200 = **inline** `oneOf [SubmitBaselineChecklistEnvelope, Error]` — Decision-B

Mirror `submitPmResult`: 200 content.schema = `oneOf` ĐÚNG 2 nhánh (KHÔNG response-component, KHÔNG discriminator) → route theo `body.success`. **3 lỗi nghiệp-vụ đến TRÊN HTTP-200 body `Error`** (KHÔNG status-line 4xx):

1. **`NOT_FOUND`** — phiếu∄ @`:1440`.
2. **`INVALID_PARAMS`** — `workflow_state != "Initial Inspection"` @`:1442` ("Chỉ submit checklist khi ở Initial Inspection").
3. **`VALIDATION` (BR-04-04)** — ≥1 dòng `test_result == "Fail"` @`:1451-1452` ("BR-04-04: Thông số sau không đạt: `<params>`" — chỉ liệt-kê tên thông-số, **KHÔNG kèm fields-map**).

status-set = **`[200, 401, 403]`**. `403` = **SINGLE `Forbidden`** nhưng **REACHABLE cap-branch** (`rbac.require("commissioning.write")` @`:157` TRƯỚC `_handle` — cap-403 HTTP-403 THẬT; KHÁC read F6 `getCommissioning` bare-whitelist dispatcher-only-403). `submit_baseline_checklist` ∈ `_MVP_ACTION_ENVELOPE` (POST write-action) + `_MVP_BUSINESS_PATHS` (401/403 symmetry); **∉ `_MVP_READ_ENVELOPE`/`_MVP_LIST_ENVELOPE`** (write ≠ read/list ⇒ `_MVP_LIST_ENVELOPE` GIỮ 13).

### (b) `clinical_hold_required` = **`type:boolean` THẬT** (KHÔNG `integer enum[0,1]` — KHÁC CR-01 family)

`check_auto_clinical_hold` khai `-> bool` @`:405`; thân trả kết-quả toán-tử `in` / `bool(...)` = **Python `bool` GENUINE** (`True`/`False`) — Frappe JSON-encoder serialize `true`/`false`. **KHÁC** trap CR-01 (Frappe `Check` docfield emit raw int `0|1`, phải khai `integer enum[0,1]` để codegen Dart/Kotlin không CRASH). Vì giá-trị này KHÔNG đọc thẳng docfield `Check` mà là biểu-thức tính-toán ⇒ khai **`boolean`** ĐÚNG. Precedent 1:1 trong cùng module = `getCommissioning.is_locked` (`docstatus==1` → Python bool → `boolean`, ADR-MOBILE-053 §2(d)); precedent cross-module = `PmSubmitResultResponse.is_late` (`bool()`-coerce @`services/imm08.py`, khai `boolean`). Guard chống-drift bằng `typing.get_type_hints(check_auto_clinical_hold)["return"] is bool` (import source — nếu BE đổi về Check-read thì RED).

### (c) `overall_result` = **`type:string` + `enum: [Pass]`** (single-value grounded)

Khi reach return @`:1454-1456`, `overall_inspection_result` LUÔN `"Pass"` (mọi dòng `Fail` đã raise BR-04-04 @`:1451` ⇒ KHÔNG bao giờ emit giá-trị khác). Khai `enum: [Pass]` phản-ánh CHÍNH-XÁC không-gian giá-trị của **nhánh success** (không phải toàn Select docfield). `type:string` giữ codegen sinh `String` (không phải native enum 1-value vô-nghĩa).

### (d) `results` = **`type:array` items `$ref BaselineChecklistResultInput` default `[]`** (JSON-string convention)

`api/imm04.py:159` `_parse_json(results, default=[])` ⇒ client gửi **JSON-string** mảng, BE parse → `list[dict]`. Mỗi phần-tử = `BaselineChecklistResultInput` CLOSED 4 prop string `{parameter, measured_val, test_result, fail_note}` grounded `result_map` khoá `parameter` @`:1443` + `r.get(measured_val/test_result/fail_note)` @`:1447-1449`. Dòng KHÔNG khớp `parameter` với `baseline_tests[]` bị **bỏ qua im lặng** (chỉ ghi row khớp). Precedent shape = `SubmitPmResultRequest.checklist_results` (nested array).

### (e) 4 schema CLOSED (`additionalProperties:false`) — 3-tầng Request + 3-tầng Response

- `BaselineChecklistResultInput` — element-shape nested `results[]` (4 prop string).
- `SubmitBaselineChecklistRequest` — body `{name (req), results (array default [])}`.
- `SubmitBaselineChecklistResponse` — payload `data` = **EXACT 3 prop** `{name:string, overall_result:string enum[Pass], clinical_hold_required:boolean}`, `required` = cả 3 (return luôn emit đủ @`:1456`).
- `SubmitBaselineChecklistEnvelope` — `{success.enum[true], data:$ref SubmitBaselineChecklistResponse}`, `required[success,data]` (grounded `_ok` wrapper). Mirror `PmSubmitResultEnvelope`.

### (f) ⚠️ GIỮ tên schema `SubmitBaselineChecklist*` — KHÔNG rename `BaselineChecklistResult*` (Hyrum / One-Version)

Đề-mục CR-25c gợi-ý tên success-schema `BaselineChecklistResult` + envelope `BaselineChecklistResultEnvelope`. NHƯNG YAML + guard đã curate & **committed** (commit `6600c2c`) với tên `SubmitBaselineChecklistResponse` + `SubmitBaselineChecklistEnvelope` (đồng-bộ tiền-tố opId `submitBaselineChecklist` + `SubmitBaselineChecklistRequest`). Tên schema = **class name codegen sinh** ⇒ observable contract; rename sau khi committed = **breaking Hyrum / One-Version** (mobile repo có thể đã generate). Precedent 1:1 = ADR-MOBILE-060 §CR-27a (`getInternalAudit` GIỮ, KHÔNG rename `getAudit`). ⇒ **GIỮ `SubmitBaselineChecklist*`**; contract nghiệp-vụ (3-field CLOSED, `clinical_hold_required` boolean, `overall_result` enum[Pass], Decision-B) **KHỚP 100%** acceptance — chỉ khác nhãn tên. Tương-tự guard-class GIỮ `TestMobileSubmitBaselineChecklist` (KHÔNG rename `TestMobileCommissioningSubmitContract` — test-class KHÔNG là contract codegen; rename = churn 0-giá-trị).

### (g) tag `commissioning` (REUSE — module-tag IMM-04, cùng `listCommissioning`/`getCommissioning`)

### (h) CONTRACT-ONLY

BE LIVE @`api/imm04.py:155` + `services/imm04.py:1437`. Curate PURE-YAML + guard test + doc. **0** `.py` runtime change / gunicorn reload / `bench migrate` / commit ⇒ DoD = `bench --site miyano run-tests --module ...test_mobile_oas` + `...test_mobile_docset` in `Ran N OK` (KHÔNG curl — worker stale cho phantom-417).

---

## 3. Path + body

```
/api/method/assetcore.api.imm04.submit_baseline_checklist  (POST, opId submitBaselineChecklist, tag [commissioning])
  requestBody: required:true, application/json.schema.$ref → SubmitBaselineChecklistRequest
    name:    string (required)
    results: array<BaselineChecklistResultInput>, default []  (client gửi JSON-string)
  200: inline oneOf [SubmitBaselineChecklistEnvelope, Error]   (Decision-B, 0 discriminator)
  401: $ref Unauthorized401   403: $ref Forbidden (cap commissioning.write REACHABLE)
```

- Đặt **liền sau** cụm F6 schema (`SubmitBaselineChecklistRequest`/`BaselineChecklistResultInput`/`SubmitBaselineChecklistResponse`/`SubmitBaselineChecklistEnvelope` liền `PmSubmitResultEnvelope` trong `components.schemas`) + path đặt trong `paths:` — giữ cụm write-action liền mạch.

---

## 4. Guard test (`test_mobile_oas.py` — class RIÊNG `TestMobileSubmitBaselineChecklist`, 9 TC)

- **test_submit_baseline_path_and_opid_exists** — path tồn tại + CHỈ POST + opId `submitBaselineChecklist` + tag `[commissioning]`; ∈ `_MVP_BUSINESS_PATHS` + `_MVP_ACTION_ENVELOPE`; ∉ `_STUB_PATHS`.
- **test_request_body_required_json** — requestBody `required:true`, `application/json.schema.$ref → SubmitBaselineChecklistRequest`; KHÔNG query params.
- **test_submit_baseline_request_schema_closed** — Request CLOSED; `required==['name']`; `name` string; `results` array items `$ref BaselineChecklistResultInput` default `[]`.
- **test_baseline_result_input_closed_4str** — `BaselineChecklistResultInput` CLOSED; keys ĐÚNG 4 `{parameter,measured_val,test_result,fail_note}`; mỗi prop `type:string`.
- **test_submit_baseline_response_oneof2_closed** — 200 oneOf ĐÚNG 2 `[SubmitBaselineChecklistEnvelope, Error]` 0-discriminator; 401 `Unauthorized401` + 403 `Forbidden`; status-set `[200,401,403]`.
- **test_envelope_and_response_closed_boolean** — Envelope CLOSED `required{success,data}` success const true; Response CLOSED 3-prop `{name:string, overall_result:string, clinical_hold_required:boolean}` — assert `boolean` **VÀ** `assertNotEqual integer` **VÀ** `assertNotIn enum` (KHÁC Check int-0/1 trap CR-01).
- **test_path_count_increments_by_one** — assert-delta `len(paths)==len(paths∖submit)+1` (chống hardcode) + reconcile counts + `_MVP_ACTION_ENVELOPE[submit]→SubmitBaselineChecklistEnvelope` + `_MVP_LIST_ENVELOPE` GIỮ 13.
- **test_yaml_loads_all_refs_resolve_no_orphan** — mọi `$ref` resolve; 4 schema mới KHÔNG orphan.
- **test_live_signature_parity** (**PARITY-DRIFT guard**) — `inspect.signature(imm04.submit_baseline_checklist).parameters == {name, results}` + `svc` source chứa 3 return-key `{name, overall_result, clinical_hold_required}` + `get_type_hints(check_auto_clinical_hold)["return"] is bool` ⇒ đỏ nếu BE đổi shape/kiểu mà YAML không đổi.

### Bulk-bump bookkeeping (đã landed commit `6600c2c` — ghi để cân guard)

- CR-25c delta riêng = **+1 path** (`submit_baseline_checklist`) + **+4 schema** + **+9 TC** (`_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` +9) + path/opId +1 + c5/`_PARITY_BUSINESS_PATHS` +1 + `_EXPECTED` += `submit_baseline_checklist → submitBaselineChecklist` + `_MVP_ACTION_ENVELOPE` += submit-path.
- Suite live SAU các round kế-tiếp (CR-35 label / CR-27a audit) = `test_mobile_oas` **Ran 856 OK** · `test_mobile_docset` **Ran 9 OK** (module-isolated, LL-TEST-30). Counter path/opId hiện `96`, c5 `85` — CR-25c đã reconcile trong dòng thời-gian này.

---

## 5. Hệ quả

- **+**: **HOÀN TẤT 3/3 core commissioning ops** — cụm F6 codegen-ready đủ `listCommissioning` (list) + `getCommissioning` (detail) + `submitBaselineChecklist` (write-baseline). FE mobile bind luồng: mở list → xem chi tiết → nộp bảng-kiểm → nhận `overall_result='Pass'` + cờ `clinical_hold_required` để cảnh-báo "Cần giữ lâm-sàng".
- **+**: false-green chặn bằng parity-drift guard (signature + return-key + `check_auto_clinical_hold` return-annotation `bool`) — endpoint LIVE.
- **−/đánh đổi**: GIỮ tên `SubmitBaselineChecklist*` khác gợi-ý đề-mục `BaselineChecklistResult*` — CHẤP NHẬN (Hyrum/One-Version, tên committed = contract codegen; nghiệp-vụ khớp 100%).
- **backlog (2 NC ops còn lại của IMM-04 — NGOÀI 3 core commissioning)**: `list_non_conformances` (READ list NC) + `report_nonconformance` (WRITE tạo NC — variant #3 `body.data-as-array`, cần schema `type:array`). Curate vòng kế theo cùng pattern.
- **KHÔNG** đổi backend / workflow / DocType. CONTRACT-ONLY.
