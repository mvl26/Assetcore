# IMM-02 — Backend Design

> **Wave 2 — Live.** BE service và API đã implement đầy đủ. Tài liệu này phản ánh code thực tế tại `assetcore/services/imm02.py` và `assetcore/api/imm02.py`.

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường** |
| Phiên bản | 1.0.1 |
| Ngày cập nhật | 2026-05-14 |
| Owner | Tech Lead |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [05 API Specification](./05_API_Specification.md) |

---

# Phần I — DocType Catalog

| DocType | Naming | Submittable | track_changes | Module |
|---|---|---|---|---|
| `IMM Tech Spec` | `TS-.YY.-.#####` | Yes | Yes | AssetCore |
| `IMM Market Benchmark` | `MB-.YY.-.#####` | Yes | Yes | AssetCore |
| `IMM Lock-in Risk Assessment` | `LR-.YY.-.#####` | Yes | Yes | AssetCore |
| `Tech Spec Requirement` | (child) | — | — | AssetCore |
| `Benchmark Candidate` | (child) | — | — | AssetCore |
| `Infra Compatibility Item` | (child) | — | — | AssetCore |
| `Lock-in Risk Item` | (child) | — | — | AssetCore |
| `Tech Spec Document` | (child) | — | — | AssetCore |

> Note: `~~Tech Spec Lifecycle Event~~` — KHÔNG tạo. Audit trail dùng `IMM Audit Trail` (root_doctype=IMM Tech Spec).

---

# Phần II — DocType Schemas

## II.1. IMM Tech Spec

Naming: `TS-.YY.-.#####` · Submittable · track_changes=1

> Nguồn ground truth: `assetcore/assetcore/doctype/imm_tech_spec/imm_tech_spec.json`. Field list dưới đây liệt kê đầy đủ theo schema thực tế (đã bỏ field bịa `spec_id`).

| Section | Field | Type | Required | Permlevel | Note |
|---|---|---|---|---|---|
| Header | `naming_series` | Select (`TS-.YY.-.#####`) | Y | 0 | default `TS-.YY.-.#####` |
| | `draft_date` | Date | Y | 0 | default Today |
| | `version` | Data | N | 0 | default "1.0", bump khi reissue |
| | `workflow_state` | Link → Workflow State | — (auto) | 0 | read-only, no_copy, default `Draft`, in_list_view |
| | `parent_spec` | Link → IMM Tech Spec | N | 0 | dùng cho reissue |
| Source | `source_plan` | Link → IMM Procurement Plan | Y | 0 | |
| | `source_plan_line` | Data | N | 0 | tên row plan_line (validate ở service, không reqd JSON) |
| | `source_needs_request` | Link → IMM Needs Request | Y | 0 | |
| Target | `device_model_ref` | Link → IMM Device Model | Y | 0 | in_list_view |
| | `device_category` | Link → AC Asset Category | N (auto) | 0 | `fetch_from=device_model_ref.asset_category`, read_only |
| | `quantity` | Int | Y | 0 | default 1 |
| | `spec_template_ref` | Data | N | 0 | placeholder — Spec Template DocType chưa tồn tại |
| Requirements | `total_mandatory` | Int | — | 0 | read_only, auto rollup, in_list_view |
| | `total_optional` | Int | — | 0 | read_only, auto rollup |
| | `requirements` | Table → Tech Spec Requirement | N (validate ở G01) | 0 | ≥ 8 mandatory at G01 |
| | `documents` | Table → Tech Spec Document | N | 0 | |
| Benchmark | `benchmark_ref` | Link → IMM Market Benchmark | N | 0 | |
| | `candidate_count` | Int | — | 0 | read_only, in_list_view, ≥ 3 at G02 |
| Infra | `infra_status_overall` | Select (`All Compatible` / `Partial` / `Need Major Upgrade`) | — (auto) | 0 | read_only |
| | `infra_compat` | Table → Infra Compatibility Item | N (validate VR-02-05) | 0 | 6 items at G03 |
| Lock-in | `lock_in_risk_ref` | Link → IMM Lock-in Risk Assessment | N | **1** | |
| | `lock_in_score` | Float (precision=4) | — | **1** | read_only, in_list_view |
| | `mitigation_plan` | Long Text | Conditional | **1** | required if lock_in_score > threshold |
| | `mitigation_evidence` | Attach | Conditional | **1** | required cùng mitigation_plan tại G04 |
| Approval | `approver` | Link → User | Conditional | 0 | điền trước Lock |
| | `approval_date` | Date | N | 0 | read_only |
| | `withdrawal_reason` | Long Text | Conditional | 0 | bắt buộc khi withdraw |
| Footer | `amended_from` | Link → IMM Tech Spec | — | 0 | Frappe amend chain, read_only |

> `is_submittable=1`, `track_changes=1`, `title_field=device_model_ref`. Section `Lock-in Risk` được set `permlevel=1` ở Section Break — kế thừa lên 4 field bên trong.

**Permissions (IMM Tech Spec):**

| Role | Read | Write | Create | Delete | Submit | Amend |
|---|---|---|---|---|---|---|
| IMM HTM Engineer | ✅ | ✅ (Draft/Reviewing) | ✅ | ❌ | ❌ | ❌ |
| IMM Planning Officer | ✅ | ✅ (Benchmark fields) | ❌ | ❌ | ❌ | ❌ |
| IMM Risk Officer | ✅ | ✅ (Infra/Lock-in) | ❌ | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| IMM Board Approver | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## II.2. IMM Market Benchmark

Naming: `MB-.YY.-.#####` · Submittable

| Field | Type | Required | Note |
|---|---|---|---|
| `spec_ref` | Link → IMM Tech Spec | Y | |
| `benchmark_date` | Date | Y | |
| `recommended_candidate` | Data | N (auto) | row name of top candidate |
| `weighting_scheme` | JSON | N | `{price:30, spec:40, support:20, brand:10}` |
| `candidates` | Table → Benchmark Candidate | Y | ≥ 3 candidates |

**Permissions (IMM Market Benchmark):**

| Role | Read | Write | Create | Submit |
|---|---|---|---|---|
| IMM HTM Engineer | ✅ | ✅ | ✅ | ❌ |
| IMM Planning Officer | ✅ | ✅ | ✅ | ✅ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ |

## II.3. IMM Lock-in Risk Assessment

Naming: `LR-.YY.-.#####` · Submittable

| Field | Type | Required | Permlevel | Note |
|---|---|---|---|---|
| `spec_ref` | Link → IMM Tech Spec | Y | 0 | |
| `assessment_date` | Date | Y | 0 | |
| `lock_in_score` | Float (auto) | — | **1** | weighted sum |
| `threshold_used` | Float | N | **1** | snapshot from master |
| `items` | Table → Lock-in Risk Item | Y | 0 | 5 dimensions |
| `mitigation_plan` | Long Text | Conditional | **1** | required if score > threshold |
| `mitigation_evidence` | Attach | Conditional | **1** | |

**Permissions (IMM Lock-in Risk Assessment):**

| Role | Read | Write | Create | Submit |
|---|---|---|---|---|
| IMM Risk Officer | ✅ | ✅ | ✅ | ✅ |
| IMM HTM Engineer | ✅ (permlevel 0 only) | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ |
| IMM Board Approver | ✅ (all permlevels) | ❌ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ |

## II.4. Child Tables

### Tech Spec Requirement

| Field | Type | Note |
|---|---|---|
| `seq` | Int | auto-increment |
| `group` | Select | Performance / Safety / Connectivity / Power / Mechanical / Software / Service / Compliance |
| `parameter` | Data | e.g. "Tidal Volume" |
| `value_or_range` | Data | e.g. "20–2000 mL" |
| `unit` | Data | mL |
| `is_mandatory` | Check | |
| `weight` | Int | 1–10 |
| `test_method` | Small Text | required if is_mandatory=1 (VR-02-03) |
| `evidence` | Attach | datasheet |
| `remark` | Small Text | |

### Benchmark Candidate

| Field | Type | Note |
|---|---|---|
| `manufacturer` | Data | |
| `model` | Data | |
| `country` | Data | |
| `spec_match_pct` | Percent | auto-computed |
| `price_estimate` | Currency | |
| `price_source` | Select | Vendor Quote / Public Tender / Web / Other |
| `support_tier` | Select | Tier1 / Tier2 / Tier3 |
| `local_partner` | Data | |
| `in_avl` | Check | link to IMM-03 AVL |
| `recommendation_score` | Float | auto-computed |
| `notes` | Small Text | |

### Infra Compatibility Item

| Field | Type | Note |
|---|---|---|
| `domain` | Select | Electrical / Medical Gas / Network/IT / HIS-PACS-LIS / HVAC / Space-Layout |
| `current_state` | Small Text | |
| `required_state` | Small Text | |
| `compatibility_status` | Select | Compatible / Need Upgrade / Need Major Upgrade / N/A |
| `upgrade_owner` | Link → User | |
| `upgrade_eta` | Date | |
| `upgrade_cost_estimate` | Currency | |
| `evidence` | Attach | |

### Lock-in Risk Item

| Field | Type | Note |
|---|---|---|
| `dimension` | Select | Protocol Standard / Consumable Source / Software License / Parts Source / Service Tooling |
| `score` | Int | 1–5 |
| `weight_pct` | Percent | auto from DEFAULT_WEIGHTS |
| `weighted` | Float | auto = score × weight_pct |
| `rationale` | Small Text | |
| `mitigation` | Small Text | |

### Tech Spec Document

| Field | Type | Note |
|---|---|---|
| `doc_type` | Select | Datasheet / HSMT Excerpt / Technical Drawing / Standard Reference / Other |
| `file_attachment` | Attach | |
| `version` | Data | |
| `issued_date` | Date | |

---

# Phần III — Service Layer

File: `assetcore/services/imm02.py` — **Đã implement đầy đủ.**

## III.1 Tech Spec lifecycle hooks

| Hook | Function | Mô tả |
|---|---|---|
| `before_insert` | `before_insert_tech_spec(doc)` | Set `draft_date = today()`, `version = "1.0"`, auto-fetch `device_category` từ IMM Device Model |
| `validate` | `validate_tech_spec(doc)` | Chạy VR-02-01..VR-02-05, rollup requirement counts, rollup infra_status_overall, check gates theo state |
| `before_submit` | `before_submit_tech_spec(doc)` | Validate G04 (lock-in check), set approval_date |
| `on_submit` | `on_submit_tech_spec(doc)` | Update Procurement Plan line status → "In Procurement", publish realtime `imm02_spec_locked` |

## III.2 Validation rules (VR)

| VR | Function | Logic |
|---|---|---|
| VR-02-01 | `_vr01_unique_per_plan_line` | 1 source_needs_request ↔ 1 Active Tech Spec (docstatus<1, state≠Withdrawn) |
| VR-02-02 | `_vr02_mandatory_min_count` | `requirements` phải có ≥ 1 dòng `is_mandatory=1` (chỉ enforce khi không rỗng) |
| VR-02-03 | `_vr03_test_method_present` | Mọi mandatory requirement phải có `test_method` không rỗng |
| VR-02-05 | `_vr05_infra_completeness` | 6/6 infra domains có `compatibility_status` (chỉ enforce khi state = Risk Assessed / Pending Approval / Locked) |

## III.3 Gates

| Gate | Function | Kích hoạt khi | Logic |
|---|---|---|---|
| G01 | `_validate_gate_g01` | state = "Reviewing" | ≥ 8 mandatory requirements, 100% có test_method |
| G02 | `_validate_gate_g02` | state = "Benchmarked" | `candidate_count ≥ 3` (từ `benchmark_ref` hoặc `doc.candidate_count`) |
| G03 | `_validate_gate_g03` | state = "Risk Assessed" | 6/6 infra domains có status |
| G04 | `_validate_gate_g04` | `before_submit` | `lock_in_score ≤ threshold` HOẶC có `mitigation_plan` + `mitigation_evidence` |

## III.4 Rollup functions

| Function | Mô tả |
|---|---|
| `_rollup_requirement_counts(doc)` | Tính `total_mandatory`, `total_optional`, auto-increment `seq` |
| `_rollup_infra_status(doc)` | Tính `infra_status_overall`: "All Compatible" / "Partial" / "Need Major Upgrade" |

## III.5 Market Benchmark

Function `validate_market_benchmark(doc)`:
- Parse `weighting_scheme` JSON (default: `{price:30, spec:40, support:20, brand:10}`)
- Tính `recommendation_score` cho mỗi candidate
- Chọn `recommended_candidate` = top scorer
- Sync `benchmark_ref` và `candidate_count` vào Tech Spec parent

Scoring formula: `score = spec*(w_spec/100) + price*(w_price/100) + support*(w_support/100) + brand*(w_brand/100)` × 5

## III.6 Lock-in Risk Assessment

Function `validate_lock_in_assessment(doc)`:
- Tính `lock_in_score = Σ (item.score × weight)` với DEFAULT_WEIGHTS:

| Dimension | Weight |
|---|---|
| `Protocol Standard` | 0.30 |
| `Consumable Source` | 0.20 |
| `Software License` | 0.20 |
| `Parts Source` | 0.15 |
| `Service Tooling` | 0.15 |

- Sync `lock_in_risk_ref`, `lock_in_score`, `mitigation_plan`, `mitigation_evidence` vào Tech Spec parent

## III.7 Versioning functions (via API layer)

| Function | Mô tả |
|---|---|
| `_reissue_spec(from_spec)` (trong `api/imm02.py`) | **Guard `rbac.can("spec.create")` → FORBIDDEN**; validate state=Withdrawn; copy doc, set `parent_spec`, bump version ("1.0"→"2.0"), reset approval/withdrawal fields, insert mới ở Draft |
| `_withdraw_spec(name, reason)` (trong `api/imm02.py`) | **Guard `rbac.can("spec.submit")` → FORBIDDEN** (trước state); validate state in [Pending Approval, Locked], set `withdrawal_reason`, submit nếu docstatus=0 |
| `_lock_spec(name, approver, remarks)` (trong `api/imm02.py`) | **Guard `rbac.can("spec.submit")` → FORBIDDEN** (trước state); validate state=Pending Approval; set approver + `workflow_state=Locked`; `doc.submit()` |

### III.7.1 CTA gating server-driven (GATE-8 / LL-FE-51 — vòng 6)

Chi tiết đặc tả: `02_Analysis_Design.md` §IV.3 + ADR-IMM02-01. Tóm tắt BE:

- **SoT map** `_SPEC_CTA_TRANSITIONS: dict[str, list[str]]` (trong `api/imm02.py`):
  `{"Pending Approval": ["lock","withdraw"], "Locked": ["withdraw"], "Withdrawn": ["reissue"]}` — state khác `.get(state, [])` → `[]`.
- **`_get_tech_spec`** bổ sung (import `from assetcore.services.shared import rbac`):
  ```python
  state   = doc.workflow_state or "Draft"
  allowed = _SPEC_CTA_TRANSITIONS.get(state, [])
  approve = rbac.can("spec.submit")
  data["allowed_transitions"] = allowed
  data["can_lock"]     = int("lock"     in allowed and approve)
  data["can_withdraw"] = int("withdraw" in allowed and approve)
  data["can_reissue"]  = int("reissue"  in allowed and rbac.can("spec.create"))
  ```
- **Guard helper** dùng chung, thứ tự **capability → state**:
  ```python
  def _require_spec_approver() -> None:
      if not rbac.can("spec.submit"):
          raise ServiceError(ErrorCode.FORBIDDEN,
              _("Không đủ quyền phê duyệt/rút hồ sơ kỹ thuật"))
  ```
  Đặt gọi đầu `_lock_spec`/`_withdraw_spec`; `_reissue_spec` dùng biến thể `spec.create`. `ServiceError(FORBIDDEN)` được `_handle` bắt → `_err(...)` = **HTTP-200 + envelope** (in-handler cap-403, KHÔNG raise→HTTP-4xx).
- **INVARIANT** (map ⊆ guard): cờ `get_tech_spec` ⊆ tập guard cho phép — test `test_imm02` phải khẳng định với mọi state không có cờ nào mở hành động guard sẽ reject.
- **REGRESSION** (chuỗi lesson "full quyền vẫn không duyệt được"): `AssetCore Super Admin` có DocPerm submit=1 → `spec.submit`=True → `can_lock`=1 tại Pending Approval **và** `lock_spec` chạy OK.

> ⚠️ **Drift cần lưu ý (report — light-touch):** bảng §V.1/§V.2 dưới dùng role-name persona cũ (`IMM HTM Engineer`, `IMM Board Approver`…) KHÔNG khớp fixture `assetcore/fixtures/workflow.json` (`Spec User`, `Needs Manager`, `Spec Manager`, `Commissioning Manager`, `Procurement Manager`, `AssetCore Super Admin`, `System Manager`). CTA gating vòng 6 KHÔNG dựa vào role-name mà dựa **capability** (`spec.submit`/`spec.create`) nên không bị ảnh hưởng; nhưng nên đồng bộ V.1/V.2 với fixture ở lượt chuẩn hoá docs riêng.

### III.7.2 SSoT 6 transition trung gian — `_SPEC_VALID_TRANSITIONS` (CR-WF-02-SPEC, vòng 24)

Ground truth spec: `02_Analysis_Design.md` §IV.4 + ADR-IMM02-02. Tóm tắt BE (`services/imm02.py`, **mirror `services/imm03.py::_AVL_VALID_TRANSITIONS`**):

- **SSoT** `_SPEC_VALID_TRANSITIONS: dict[str, list[tuple[str, str, frozenset]]]` — 6 cạnh, mỗi cạnh `(action, next_state, roles)`. Roles = tập `allowed` gom-vai của group `(state, action, next_state)` trong `imm_02_spec_workflow.json` (grounded, không bịa). Định nghĩa DRY:
  ```python
  _SPEC_ADMIN_ROLES = frozenset({"AssetCore Super Admin", "System Manager"})

  _SPEC_VALID_TRANSITIONS: dict[str, list[tuple[str, str, frozenset]]] = {
      "Draft": [
          ("Gửi rà soát", "Reviewing", frozenset({"Spec User"}) | _SPEC_ADMIN_ROLES),
      ],
      "Reviewing": [
          ("Yêu cầu chỉnh spec", "Draft",
           frozenset({"Spec User", "Needs Manager"}) | _SPEC_ADMIN_ROLES),
          ("Hoàn tất benchmark", "Benchmarked",
           frozenset({"Needs Manager"}) | _SPEC_ADMIN_ROLES),
      ],
      "Benchmarked": [
          ("Đánh giá rủi ro xong", "Risk Assessed",
           frozenset({"Spec Manager"}) | _SPEC_ADMIN_ROLES),
      ],
      "Risk Assessed": [
          ("Trình duyệt spec", "Pending Approval",
           frozenset({"Commissioning Manager"}) | _SPEC_ADMIN_ROLES),
      ],
      "Pending Approval": [
          ("Yêu cầu chỉnh risk", "Risk Assessed",
           frozenset({"Procurement Manager"}) | _SPEC_ADMIN_ROLES),
      ],
      # Locked / Withdrawn (docstatus=1, terminal workflow-engine) → không key → []
  }

  _SPEC_EXCEPTION_ACTIONS = frozenset({"Phê duyệt spec", "Rút spec"})
  ```
- **Derive fn** (mirror `avl_allowed_transitions`):
  ```python
  def spec_allowed_actions(workflow_state, user_roles=None) -> list[str]:
      rows = _SPEC_VALID_TRANSITIONS.get(workflow_state or "", [])
      if user_roles is None:
          return [action for action, _n, _r in rows]
      ur = set(user_roles)
      return [action for action, _n, roles in rows if roles & ur]
  ```
- **Emit ở API** (`api/imm02.py::_get_tech_spec`, NGAY SAU `data.update(svc._spec_cta_flags(doc))`):
  ```python
  data["allowed_actions"] = svc.spec_allowed_actions(
      doc.workflow_state, frappe.get_roles(frappe.session.user))
  ```
  `allowed_actions` (nhãn ACTION) ≠ `allowed_transitions` (next-STATE của vòng 6) — 2 key riêng, KHÔNG collide.
- **`transition_workflow`** GIỮ NGUYÊN — đã áp qua `apply_workflow` (native enforce `allowed` role). KHÔNG thêm guard role tường minh (khác AVL vốn dùng `db.set_value`). 2 loại 403: dispatcher-403 (guest) · in-handler cap-403 (`PermissionError`→`_err(FORBIDDEN)`=HTTP-200+envelope).
- **INVARIANT-1 (reconcile, STATIC)** — `test_spec_allowed_transitions_matches_workflow_fixture`: (a) ∀ `(state,action,next_state,roles)∈map`: `roles == ∪allowed` của group workflow tương ứng (EXACT); (b) `{action workflow} − {action map} == _SPEC_EXCEPTION_ACTIONS`. RED khi map rỗng/thiếu cạnh → GREEN sau 6 cạnh.
- **INVARIANT-2 (advertise ⟺ reachable)** — bảo đảm bởi INVARIANT-1 (map roles == workflow roles) + `apply_workflow` native. Tách **RBAC-gate** (role) khỏi **business-gate** (G01–G04): `allowed_actions` chỉ advertise cạnh role-reachable; bấm vẫn có thể `BUSINESS_RULE` (UX đúng).
- **KHÔNG đụng** `imm_02_spec_workflow.json` (giữ `test_workflow_admin_override` GREEN); KHÔNG migrate; chỉ sửa `.py` → cần worker reload để live.

### III.7.3 Đóng dead-gate persona `Spec User` + INVARIANT coverage (CR-WF-RBAC-PROFILE-COVERAGE, vòng 34)

Ground truth spec: `02_Analysis_Design.md` §IV.5 + ADR-IMM02-03. Tóm tắt BE:

- **Root-cause:** `Gửi rà soát` (Draft→Reviewing) sole non-admin gate = `Spec User`, nhưng `Spec User ∉` mọi Role Profile trong `setup/role_profile_catalog.py::ROLE_PROFILE_CATALOG` → chỉ Super Admin/System Manager duyệt được (dead-gate). Scan 22 workflow: `Spec User` là role UNCOVERED **duy nhất**.
- **Fix (catalog-only, KHÔNG re-gate workflow):** thêm `"Spec User"` vào list `"Trưởng phòng VT-TTBYT"`:
  ```python
  "Trưởng phòng VT-TTBYT": [
      "Commissioning Manager", "Needs Manager",
      "Procurement Manager", "Spec Manager", "Spec User",   # + CR vòng 34
  ],
  ```
  `_SPEC_VALID_TRANSITIONS`, `imm_02_spec_workflow.json`, `fixtures/workflow.json`, `allow_edit` (Draft/Reviewing=`Spec User`) — **GIỮ NGUYÊN**. Persona VT-TTBYT nay có `Spec User` → tạo Draft + G01 + `Gửi rà soát` thông cùng 1 role.
- **INVARIANT own-file mới** — `assetcore/tests/guards/test_workflow_role_profile_coverage.py` (FILE-driven, glob source JSON + đọc catalog; mirror `_transition_groups` của `test_workflows.py`):
  - **INV-COV:** ∀ transition trong 22 source JSON, mọi `allowed` non-admin role ∈ `(∪roles_for_profile) ∪ {AssetCore Super Admin, System Manager} ∪ EXCEPTION_ROLES`, với `EXCEPTION_ROLES = frozenset({"Vendor Engineer"})`. RED-trước = `{Spec User}` uncovered → GREEN-sau.
  - **INV-EXC-REACH:** ∀ transition-group `allowed ∩ EXCEPTION_ROLES ≠ ∅` PHẢI có ≥1 role ∈ `∪roles_for_profile` (KHÔNG sole-gate bằng EXCEPTION). 3 group IMM-04 co-list `PM User` → GREEN.
- **BE integration test** (mirror pattern `test_imm02` ensure_user + profile): user profile "Trưởng phòng VT-TTBYT" (non-admin) → Draft 8 spec-line → `transition_workflow('Gửi rà soát')` = success, `workflow_state=='Reviewing'`; base `AssetCore System User` → VẪN chặn. RED-trước: guard `spec_allowed_actions` role-filter `[]` → `BAD_STATE` (API) / `apply_workflow` `PermissionError` (raw).
- **Deploy (sync live, KHÔNG migrate):** `bench --site miyano execute assetcore.setup.setup_role_profiles.run` — idempotent, ép `update_all_users` đồng bộ (flag `in_install`), re-sync `user.roles` cho user mang profile. Chạy lại = `unchanged`.

## III.8 Schedulers

| Function | Tần suất | Logic |
|---|---|---|
| `check_overdue_drafts()` | Daily | Spec docstatus=0, state in [Draft, Reviewing, Benchmarked], > 30 ngày → log |
| `benchmark_freshness_alert()` | Weekly | Benchmark > 6 tháng (benchmark_date) → log |

---

# Phần IV — Controller Hooks

## IV.1. DocType files (thực tế)

| DocType | Controller file |
|---|---|
| `IMM Tech Spec` | `assetcore/assetcore/doctype/imm_tech_spec/imm_tech_spec.py` |
| `IMM Market Benchmark` | `assetcore/assetcore/doctype/imm_market_benchmark/imm_market_benchmark.py` |
| `IMM Lock-in Risk Assessment` | `assetcore/assetcore/doctype/imm_lock_in_risk_assessment/imm_lock_in_risk_assessment.py` |

Child table DocTypes (folder names — xác nhận từ `assetcore/assetcore/doctype/`):
- `tech_spec_requirement/`
- `tech_spec_document/`
- `benchmark_candidate/`
- `infra_compatibility_item/`
- `lock_in_risk_item/`

## IV.2. Hooks pattern

Controller gọi service theo pattern chuẩn AssetCore 3-tier:
- `IMM Tech Spec`: `before_insert` → `before_insert_tech_spec`, `validate` → `validate_tech_spec`, `before_submit` → `before_submit_tech_spec`, `on_submit` → `on_submit_tech_spec`
- `IMM Market Benchmark`: `validate` → `validate_market_benchmark`
- `IMM Lock-in Risk Assessment`: `validate` → `validate_lock_in_assessment`

---

# Phần V — Workflow Definition

> Nguồn ground truth: `assetcore/assetcore/workflow/imm_02_spec_workflow.json` + patch `v3_1.002_install_imm02`.

## V.1. States (7)

| State | doc_status | Style (`type`) | Allow Edit | Gate |
|---|---|---|---|---|
| `Draft` | 0 | Success | IMM HTM Engineer | — |
| `Reviewing` | 0 | Warning | IMM HTM Engineer | G01 (để vào) |
| `Benchmarked` | 0 | Success | IMM Planning Officer | G02 (để vào) |
| `Risk Assessed` | 0 | Warning | IMM Risk Officer | G03 (để vào) |
| `Pending Approval` | 0 | Warning | IMM Department Head | — |
| `Locked` | 1 | Success | IMM System Admin | G04 (terminal +) |
| `Withdrawn` | 1 | Danger | IMM System Admin | terminal − |

> `Withdrawn` có `doc_status=1` trong JSON (Frappe lưu spec đã withdraw như submitted record để bảo toàn audit trail; service tự set `withdrawal_reason`).

## V.2. Transitions (9 — JSON thực tế)

`Reviewing → Draft` được khai báo 2 lần (1 cho `IMM HTM Engineer`, 1 cho `IMM Planning Officer`), tổng 9 transitions.

| # | From | To | Action (Vietnamese) | Allowed Role | Gate |
|---|---|---|---|---|---|
| 1 | Draft | Reviewing | Gửi rà soát | IMM HTM Engineer | G01 |
| 2 | Reviewing | Draft | Yêu cầu chỉnh spec | IMM HTM Engineer | — |
| 3 | Reviewing | Draft | Yêu cầu chỉnh spec | IMM Planning Officer | — |
| 4 | Reviewing | Benchmarked | Hoàn tất benchmark | IMM Planning Officer | G02 |
| 5 | Benchmarked | Risk Assessed | Đánh giá rủi ro xong | IMM Risk Officer | G03 |
| 6 | Risk Assessed | Pending Approval | Trình duyệt spec | IMM Department Head | — |
| 7 | Pending Approval | Locked | Phê duyệt spec | IMM Board Approver | G04 |
| 8 | Pending Approval | Withdrawn | Rút spec | IMM Board Approver | — |
| 9 | Pending Approval | Risk Assessed | Yêu cầu chỉnh risk | IMM Board Approver | — |

Mọi transition đều có `allow_self_approval=1` (settings nội bộ — không yêu cầu second person).

---

# Phần VI — Schedulers

| Job | Function | Tần suất | Cron | Logic |
|---|---|---|---|---|
| `check_overdue_drafts` | `assetcore.services.imm02.check_overdue_drafts` | Daily | — | Spec docstatus=0, > 30d Draft/Reviewing/Benchmarked → log |
| `benchmark_freshness_alert` | `assetcore.services.imm02.benchmark_freshness_alert` | Weekly | — | Benchmark > 6 tháng → log |

---

# Phần VII — Database Indexes

**Hiện trạng Wave 2 (verify từ DocType JSON + patch `assetcore.patches.v3_1.002_install_imm02`):** không khai báo composite index hay `search_fields` tùy biến — module hoàn toàn dùng index mặc định của Frappe.

Mặc định Frappe tạo sẵn:
- PRIMARY KEY `name` cho mọi DocType (`tabIMM Tech Spec`, `tabIMM Market Benchmark`, `tabIMM Lock-in Risk Assessment`, `tabTech Spec Requirement`, `tabBenchmark Candidate`, `tabInfra Compatibility Item`, `tabLock-in Risk Item`, `tabTech Spec Document`).
- KEY trên `parent`, `parentfield`, `parenttype` cho mọi child table.
- KEY `creation`, `modified`, `owner`, `modified_by` chuẩn Frappe.
- Mỗi `Link` field (vd `source_plan`, `source_needs_request`, `device_model_ref`, `parent_spec`, `benchmark_ref`, `lock_in_risk_ref`, `spec_ref`, `approver`, `amended_from`, `workflow_state`) tự được tạo index khi `frappe.db.sync_doctypes` chạy.

**Composite index cần bổ sung (post-Wave 2, theo dõi p95 trước khi quyết định):**

```sql
-- Khuyến nghị nếu p95 list_tech_specs vượt 1.5s (NFR-02-01)
CREATE INDEX idx_ts_state_plan       ON `tabIMM Tech Spec`(workflow_state, source_plan);
CREATE INDEX idx_ts_device_model_st  ON `tabIMM Tech Spec`(device_model_ref, workflow_state);
CREATE INDEX idx_tsr_parent_mand     ON `tabTech Spec Requirement`(parent, is_mandatory);
```

Cách add khi cần (idempotent): viết patch `v3_x.add_imm02_indexes` gọi `frappe.db.add_index("IMM Tech Spec", ["workflow_state", "source_plan"])`. Không bắt buộc ở Wave 2.
