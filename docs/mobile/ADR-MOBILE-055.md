# ADR-MOBILE-055 — `getCommissioning.allowed_transitions` **`array[string]` → `array[object]` `$ref CommissioningTransitionItem`** (**CR-25-FIX · P1 codegen-crash · SELF-CORRECTION SC#1 của ADR-MOBILE-053** — IMM-04 emit `allowed_transitions` = `list[dict]{action,next_state,allowed_role}` KHÁC 4 sibling `array[string]`; sửa shape sai wire + false-green test-assertion + thêm LIVE-emit source-parity guard; CONTRACT-ONLY pure-YAML + test, 0 `.py`)

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-055 |
| Phase | C — API contract (codegen-ready) — hot-fix shape |
| Ngày | 2026-07-15 |
| Tác giả | BA (Self-Correction, factory vòng 47) |
| **Status** | **Accepted** |
| Bám / Supersede | **Supersede-in-part ADR-MOBILE-053** §(c) dòng 57 + §4 dòng 97 + §4 dòng 106 ("5 schema") — CHỈ claim shape `allowed_transitions = array[string]`; phần còn lại của ADR-053 (Decision-B / opId-domain / Check→int / OPEN-vs-CLOSED SC#2) GIỮ NGUYÊN · **Bám** ADR-MOBILE-001 (Decision-B) · **Core Doc SoT**: [`docs/imm-04/05_API_Specification.md §21`](../imm-04/05_API_Specification.md) §21.0 SC#1 + §21.2(a) `CommissioningTransitionItem` + §21.4(d3) |

---

## 1. Bối cảnh — lỗi thiết kế gốc (design-root, factual wire-shape)

`getCommissioning` (ADR-MOBILE-053, CR-25) curate `CommissioningDetail.allowed_transitions` = **`array` items `type:string`** (`yaml:2644-2647`), sao chép mù mẫu 4 sibling `*Detail` (`IncidentDetail`/`PmWorkOrderDetail`/`RepairWorkOrderDetail`/`CalibrationDetail`) — tất cả đều `array[string]`. **SAI wire cho IMM-04.**

**Grounded @source (đọc TRỰC-TIẾP, KHÔNG bịa):**

- `get_form_context` @`services/imm04.py:796-808` gán `result["allowed_transitions"] = _get_workflow_transitions(name)` @`:807`.
- `_get_workflow_transitions` @`services/imm04.py:667-678` **return `list[dict]`**:
  ```python
  return [
      {"action": t.action, "next_state": t.next_state, "allowed_role": t.allowed}
      for t in workflow.transitions
      if t.state == current_state and t.allowed in user_roles
  ]
  ```
  ⇒ mỗi phần tử = **object 3-key** `{action, next_state, allowed_role}`, role-filtered live theo `Workflow "IMM-04 Workflow"`.
- Web Core Doc ĐÃ model ĐÚNG: `WorkflowTransition[]` = `{action, next_state, allowed_role}` (`frontend/src/types/imm04.ts:32-35,157`; `05_API_Specification.md:213,217-221`; render `ApprovalPanel.vue`).

**⚠️ Vì sao IMM-04 KHÁC 4 sibling (KHÔNG "mirror mù"):** shape `allowed_transitions` là **per-module** — quyết định bởi HELPER emit của từng module, KHÔNG phải một quy ước chung:

| Detail | Helper emit | Return | Shape ĐÚNG |
|---|---|---|---|
| `IncidentDetail` | `imm12.py:778` (`_VALID_TRANSITIONS` map) | `list[str]` (mã trạng thái) | `array[string]` ✅ |
| `PmWorkOrderDetail` | `_PM_VALID_TRANSITIONS.get(status,[])` `imm08.py` | `list[str]` | `array[string]` ✅ |
| `RepairWorkOrderDetail` | `_REPAIR_VALID_TRANSITIONS.get(status,[])` `imm09.py` | `list[str]` | `array[string]` ✅ |
| `CalibrationDetail` | `_CAL_VALID_TRANSITIONS.get(status,[])` `imm11.py` | `list[str]` | `array[string]` ✅ |
| **`CommissioningDetail`** | **`_get_workflow_transitions()` `imm04.py:667`** | **`list[dict]{action,next_state,allowed_role}`** | **`array[object]`** ⚠️ |

4 sibling build từ **hằng map `dict[str,list[str]]`** (SSoT static) → phần tử là **mã trạng thái (string)**. IMM-04 build TRỰC-TIẾP từ **`Workflow.transitions` doc** → phần tử là **dict 3-field** (mang thêm `next_state` + `allowed_role` FE cần để render nút + gate role). Curate `array[string]` cho IMM-04 = strict Dart/Kotlin codegen **deser CRASH** trên payload object (ADR-MOBILE-051/052/053 failure-family) + **mất** `next_state`/`allowed_role`.

**Failure-mode P1:** client native codegen sinh `List<String>` cho `allowedTransitions`; runtime wire = `[{"action":...,"next_state":...,"allowed_role":...}]` ⇒ JSON-deser ném `type 'Map' is not a subtype of 'String'` (Dart) / `IllegalStateException: Expected a string but was BEGIN_OBJECT` (Kotlin/Moshi) ⇒ toàn bộ màn F6-DETAIL crash, KHÔNG render được phiếu.

---

## 2. Quyết định

### (a) SC#1 — `allowed_transitions.items` = `$ref CommissioningTransitionItem` (`array[object]`), KHÔNG `type:string`

`CommissioningDetail.properties.allowed_transitions`:
```yaml
allowed_transitions:
  type: array
  items:
    $ref: '#/components/schemas/CommissioningTransitionItem'
  description: >
    Hành động workflow hợp lệ ở trạng thái hiện tại (server-driven CTA
    @services/imm04.py:807, role-filtered). FE gate nút theo includes/action —
    KHÔNG hardcode status===. Phần tử = object 3-field (KHÔNG string) vì
    _get_workflow_transitions (:667-678) trả list[dict] — KHÁC 4 sibling array[string].
```

### (b) Schema MỚI `CommissioningTransitionItem` — CLOSED, 3-field `required`

Grounded VERBATIM dict-literal `_get_workflow_transitions` (`services/imm04.py:675`) — dict LUÔN đủ 3 key, 0 field ngoài ⇒ CLOSED an-toàn (curated, KHÔNG `as_dict()` meta-leak):
```yaml
CommissioningTransitionItem:
  type: object
  additionalProperties: false
  properties:
    action:       { type: string }   # t.action  — nhãn nút workflow (vd "Bắt đầu kiểm tra")
    next_state:   { type: string }   # t.next_state — trạng thái đích sau transition
    allowed_role: { type: string }   # t.allowed  — role được phép (đã role-filter theo session user)
  required: [action, next_state, allowed_role]
```
Đặt **liền sau** `CommissioningDetailEnvelope` trong `components.schemas:` (giữ cụm IMM-04 liền mạch).

### (c) Sửa false-green test-assertion + THÊM LIVE-emit source-parity guard

- **Sửa** `TestMobileGetCommissioningDetail.test_detail_child_refs_resolve` (`test_mobile_oas.py:26321-26324`): assertion `items.type == "string"` = **false-green** (khai đúng ý nhưng SAI wire). Đổi thành: `allowed_transitions.items.$ref == '#/components/schemas/CommissioningTransitionItem'` + resolve KHÔNG dangling + `CommissioningTransitionItem` CLOSED (`additionalProperties:false`) + `required == [action, next_state, allowed_role]` + cả 3 prop `type:string`.
- **THÊM** 1 TC MỚI `test_live_emit_allowed_transitions_dict_shaped` (mirror sibling `test_pmtrans_f_live_emit_grounded` `test_mobile_oas.py:8579-8593`) — **LIVE-emit source-parity** (AST-grounding, KHÔNG cần DB seed): `inspect.getsource(imm04.get_form_context)` chứa `"allowed_transitions"` VÀ `_get_workflow_transitions(`; `inspect.getsource(imm04._get_workflow_transitions)` chứa cả 3 literal `"action"` + `"next_state"` + `"allowed_role"`. Chứng minh **builder dict-shaped** → chống drift contract↔live (contract array[object] khớp wire THẬT).

### (d) ⚠️ REGRESSION-BOUNDARY — 4 sibling `allowed_transitions` VẪN `array[string]`

`IncidentDetail`/`PmWorkOrderDetail`/`RepairWorkOrderDetail`/`CalibrationDetail` build từ `_*_VALID_TRANSITIONS` map (`list[str]`) → GIỮ NGUYÊN `array[string]` + guard cũ (`TestMobilePm/Repair/CalAllowedTransitionsContract`). **TUYỆT ĐỐI KHÔNG "đồng bộ" nhầm** 4 sibling sang object (sẽ SAI wire chiều ngược). Chỉ IMM-04 đổi.

### (e) CONTRACT-ONLY

Backend `get_form_context`/`_get_workflow_transitions` **ĐÃ LIVE, KHÔNG đụng** — chỉ sửa YAML (1 items shape + 1 schema mới) + test (1 assertion + 1 TC). **0 `.py` runtime change / 0 gunicorn reload / 0 `bench migrate`**. `bench run-tests` fresh-load ⇒ guard xanh KHÔNG cần reload.

---

## 3. Phạm vi — CHỈ SC#1 (SC#2 defer)

| Self-Correction | Nội dung | Vòng 47 (CR-25-FIX)? |
|---|---|---|
| **SC#1** (shape) | `allowed_transitions` `array[string]` → `array[object]` `$ref CommissioningTransitionItem` | ✅ **TRONG SCOPE** — P1 codegen-crash |
| **SC#2** (OPEN→CLOSED) | `CommissioningDetail` + 3 child `additionalProperties:true` → `false` | ❌ **DEFER** — xem §5 |

Acceptance vòng 47 giới hạn **SC#1** ("Sửa shape allowed_transitions … đồng thời sửa false-green test + LIVE-emit parity"). SC#2 KHÔNG được nêu; endpoint reaffirm giữ nguyên ("0 backend .py", "4 sibling VẪN array[string]"). `CommissioningTransitionItem` (schema MỚI) khai CLOSED vì dict curated 3-key — **KHÔNG** kéo theo flip của `CommissioningDetail` (parent GIỮ OPEN vòng này).

---

## 4. Guard bump + reconcile (đọc LIVE trước bump — đa-phiên drift)

**Baseline LIVE 2026-07-15 (grep-verify @source NGAY trước bump — KHÔNG tin số học, `multi_session_concurrency`):**

- `_EXPECTED_TEST_COUNT` (`test_mobile_oas.py:212`) = **774** → **775** (+1: TC `test_live_emit_allowed_transitions_dict_shaped`).
- `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` (`test_mobile_docset.py:759`) = **774** → **775**.
- `_GUARD_SUITE_SUM` (`test_mobile_docset.py:927`) = **917** → **918**.
- `_MOBILE_OAS_TOTAL` (`test_mobile_docset.py:1116`) = **943** → **944** (= SUM 918 + preflight 26).
- **`test_detail_child_refs_resolve` = SỬA in-place (0 delta count)** — assertion đổi, KHÔNG thêm/bớt method.
- **KHÔNG đổi:** path/opId count = **85** (thêm SCHEMA `CommissioningTransitionItem`, KHÔNG thêm PATH) · `c5`/`_PARITY_BUSINESS_PATHS`/`_MVP_*`/`_MVP_LIST_ENVELOPE` GIỮ · `_COMMISSIONING_CHILD_ARRAY_TO_SCHEMA` (3 child) GIỮ (`allowed_transitions` test tách riêng, KHÔNG trong map này).
- **no-orphan:** `CommissioningTransitionItem` được `$ref` bởi `allowed_transitions.items` ⇒ resolve, KHÔNG orphan (`test_yaml_loads_all_refs_resolve_no_orphan` xanh). CLOSED ⇒ native-pass global closed-schema guard, KHÔNG cần thêm OPEN-allowlist.

**RED-before / GREEN-after (KHÔNG "xanh suông"):**
- RED-before: YAML còn `items.type:string` → assertion mới (`items.$ref == CommissioningTransitionItem`) ĐỎ; TC LIVE-emit ĐỎ nếu source thiếu grounding.
- GREEN-after: `bench --site miyano run-tests` cho `test_mobile_oas` + `test_mobile_docset` + `test_mobile_preflight` = `Ran N OK`, **0 skip**.

---

## 5. Hệ quả

- **+**: màn F6-DETAIL codegen-ready ĐÚNG wire — client native deser `List<CommissioningTransitionItem>` khớp payload `list[dict]`; FE render nút CTA từ `action` + gate `allowed_role` + biết `next_state` (đủ 3 field, KHÔNG mất). Đóng P1 codegen-crash.
- **+**: false-green đóng bằng shape-assert ĐÚNG + LIVE-emit source-parity (chống drift contract↔live tương lai).
- **+**: chốt nguyên tắc **`allowed_transitions` shape = per-module theo helper emit** — ground theo helper của module, KHÔNG "mirror mù" sibling (LL cho ADR tương lai chạm `allowed_transitions`).
- **− / OPEN-ISSUE (SC#2 — defer, cần BA/QA vòng sau chốt):** `CommissioningDetail` + `BaselineTestItem`/`CommissioningDocumentItem`/`CommissioningLifecycleEventItem` hiện **OPEN** (`additionalProperties:true`, theo ADR-053 §c "parity 8 *Detail"). Core Doc §21.2/§21.4(d2)/Boundaries (`05_API_Specification.md:975-978`) LẬP LUẬN nên **CLOSED** vì `_serialize_commissioning` là **curated explicit-dict** (KHÔNG `as_dict()` → 0 meta-leak) — parity sibling **cùng-module** `CommissioningListItem`/`DueCalibrationListItem` (CLOSED), KHÁC tiền-đề as_dict của 8 *Detail. Lập luận SC#2 **sound** nhưng KHÔNG phải P1 codegen-crash (OPEN vẫn codegen-safe) ⇒ **defer thành CR riêng** (CR-25-FIX-2), tránh scope-creep vòng 47 (flip 5 schema + đổi `test_detail_child_refs_resolve`/`test_check_flags` OPEN→CLOSED assertion + docset OPEN-allowlist — blast-radius vượt "P1 shape-fix"). Ghi vào backlog.
- **KHÔNG** đổi backend / workflow / DocType / migrate. Working tree để USER review (KHÔNG commit — HARD-STOP user).
