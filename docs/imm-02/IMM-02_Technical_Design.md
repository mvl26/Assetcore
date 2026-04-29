# IMM-02 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-02 — Thông số kỹ thuật và phân tích thị trường |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |

---

## 1. Tổng quan

```
Frappe v15 / ERPNext v15 / MariaDB 10.11
   ▼
AssetCore — module AssetCore (chia sẻ với IMM-01)
   • DocTypes: 3 primary + 6 child
   • Service:  assetcore/services/imm02.py
   • API:      assetcore/api/imm02.py
   • Workflow: workflow/imm_02_spec_workflow.json
   • Scheduler: tasks_imm02.py
```

---

## 2. Schema — Primary

### 2.1 IMM Tech Spec

Naming: `IMM02-TS-.YY.-.#####`. Submittable. Module: `AssetCore`.

| Section | Field | Type | Req | Note |
|---|---|---|---|---|
| Header | spec_id | Data (auto) | — | naming |
|  | draft_date | Date | Y | — |
|  | source_plan | Link → IMM Procurement Plan | Y | — |
|  | source_plan_line | Data | Y | name of plan_item row |
|  | source_needs_request | Link → IMM Needs Request | Y | — |
| Target | device_model_ref | Link → IMM Device Model | Y | Cho fetch spec_template_ref |
|  | device_category | Link → Asset Category | N (auto) | — |
|  | quantity | Int | Y | — |
|  | spec_template_ref | Link → IMM Spec Template | N | seed requirements |
|  | parent_spec | Link → IMM Tech Spec | N | versioning (reissue) |
|  | version | Data | N | "1.0", "2.0", ... |
| Requirements | total_mandatory | Int (auto) | — | — |
|  | total_optional | Int (auto) | — | — |
|  | requirements | Table → Tech Spec Requirement | Y | ≥ 8 mandatory ở G01 |
|  | documents | Table → Tech Spec Document | N | — |
| Benchmark | benchmark_ref | Link → IMM Market Benchmark | N | gắn benchmark riêng |
|  | candidate_count | Int (auto) | — | ≥ 3 ở G02 |
| Infra | infra_compat | Table → Infra Compatibility Item | Y | 6 mục ở G03 |
|  | infra_status_overall | Select (auto) | — | All Compatible / Partial / Need Major Upgrade |
| Lock-in | lock_in_risk_ref | Link → IMM Lock-in Risk Assessment | Y | trước G04 |
|  | lock_in_score | Float (auto) | — | permlevel 1 |
|  | mitigation_plan | Long Text | C | bắt buộc nếu lock_in_score > threshold |
| Approval | approver | Link → User | C | trước Lock |
|  | approval_date | Date | N | — |
|  | withdrawal_reason | Long Text | C | khi Withdrawn |
| Workflow | workflow_state | Data | Y | — |
|  | (audit) | — | — | KHÔNG tạo child — dùng `IMM Audit Trail` (root_doctype=IMM Tech Spec) |

Indexes:
- `idx_ts_state_plan (workflow_state, source_plan)`
- `idx_ts_parent (parent_spec)` (sparse, versioning)

### 2.2 IMM Market Benchmark

Naming: `IMM02-MB-.YY.-.#####`. Submittable.

| Field | Type | Note |
|---|---|---|
| spec_ref | Link → IMM Tech Spec | Y |
| benchmark_date | Date | Y |
| recommended_candidate | Link → row name | (top weighted) |
| weighting_scheme | JSON | {price:30, spec:40, support:20, brand:10} |
| candidates | Table → Benchmark Candidate | ≥ 3 |

### 2.3 IMM Lock-in Risk Assessment

Naming: `IMM02-LR-.YY.-.#####`. Submittable.

| Field | Type | Note |
|---|---|---|
| spec_ref | Link → IMM Tech Spec | Y |
| assessment_date | Date | Y |
| lock_in_score | Float (auto) | weighted Σ |
| threshold_used | Float | snapshot từ master |
| items | Table → Lock-in Risk Item | 5 chiều |
| mitigation_plan | Long Text | C khi score > threshold |
| mitigation_evidence | Attach | C |

---

## 3. Child Tables

### 3.1 Tech Spec Requirement

| Field | Type | Note |
|---|---|---|
| seq | Int | auto |
| group | Select | Performance / Safety / Connectivity / Power / Mechanical / Software / Service / Compliance |
| parameter | Data | "Tidal Volume" |
| value_or_range | Data | "20–2000 mL" |
| unit | Data | mL |
| is_mandatory | Check | — |
| weight | Int | 1–10 |
| test_method | Small Text | bắt buộc nếu mandatory (VR-03) |
| evidence | Attach | datasheet |
| remark | Small Text | — |

### 3.2 Benchmark Candidate

| Field | Type |
|---|---|
| manufacturer | Data |
| model | Data |
| country | Data |
| spec_match_pct | Percent |
| price_estimate | Currency |
| price_source | Select (Vendor Quote / Public Tender / Web / Other) |
| support_tier | Select (Tier1 / Tier2 / Tier3) |
| local_partner | Data |
| in_avl | Check (link IMM-03 AVL) |
| recommendation_score | Float (auto) |
| notes | Small Text |

### 3.3 Infra Compatibility Item

| Field | Type |
|---|---|
| domain | Select (Electrical / Medical Gas / Network/IT / HIS-PACS-LIS / HVAC / Space-Layout) |
| current_state | Small Text |
| required_state | Small Text |
| compatibility_status | Select (Compatible / Need Upgrade / Need Major Upgrade / N/A) |
| upgrade_owner | Link → User |
| upgrade_eta | Date |
| upgrade_cost_estimate | Currency |
| evidence | Attach |

### 3.4 Lock-in Risk Item

| Field | Type |
|---|---|
| dimension | Select (Protocol Standard / Consumable Source / Software License / Parts Source / Service Tooling) |
| score | Int (1–5) |
| weight_pct | Percent (auto from master) |
| weighted | Float (auto) |
| rationale | Small Text |
| mitigation | Small Text |

### 3.5 ~~Tech Spec Lifecycle Event~~ — reuse `IMM Audit Trail`

KHÔNG tạo child table. Audit ghi vào `IMM Audit Trail` (root_doctype=IMM Tech Spec). VR-02-06 enforce tại tầng IMM Audit Trail.

### 3.6 Tech Spec Document

| Field | Type |
|---|---|
| doc_type | Select (Datasheet / HSMT Excerpt / Technical Drawing / Standard Reference / Other) |
| file_attachment | Attach |
| version | Data |
| issued_date | Date |

---

## 4. Validation Rules & Gates

| ID | Rule | Where |
|---|---|---|
| VR-02-01 | 1 plan_line ↔ 1 Active Tech Spec | `_vr01_unique_per_plan_line` |
| VR-02-02 | ≥ 1 mandatory requirement | `_vr02_mandatory_min_count` |
| VR-02-03 | mandatory requirement có test_method | `_vr03_test_method_present` |
| VR-02-04 | Benchmark ≥ 3 candidate | `_vr04_benchmark_min_3` |
| VR-02-05 | 6 mục Infra có status đánh giá | `_vr05_infra_completeness` |
| VR-02-06 | Lifecycle bất biến | `_vr06_immutable_lifecycle_events` |

| Gate | Yêu cầu | Block |
|---|---|---|
| G01 | requirements ≥ 8 mandatory + 100% test_method | Draft → Reviewing |
| G02 | benchmark ≥ 3 candidate, weighted_recommendation set | Reviewing → Benchmarked |
| G03 | infra_compat 6/6 status | Benchmarked → Risk Assessed |
| G04 | lock_in_score ≤ threshold OR mitigation_plan + evidence | Pending Approval → Locked |

---

## 5. Algorithms

### 5.1 Spec match %

```python
def compute_spec_match(spec, candidate):
    mandatory = [r for r in spec.requirements if r.is_mandatory]
    if not mandatory: return 0
    matched = sum(1 for r in mandatory if candidate.match_param(r.parameter, r.value_or_range))
    return round(matched / len(mandatory) * 100, 1)
```

### 5.2 Lock-in score

```python
DEFAULT_WEIGHTS = {
    "Protocol Standard": 0.30,
    "Consumable Source": 0.20,
    "Software License": 0.20,
    "Parts Source":     0.15,
    "Service Tooling":  0.15,
}

def compute_lock_in(doc):
    score = 0
    for it in doc.items:
        w = DEFAULT_WEIGHTS.get(it.dimension, 0)
        it.weight_pct = round(w * 100, 2)
        it.weighted = round(it.score * w, 4)
        score += it.weighted
    doc.lock_in_score = round(score, 4)
```

### 5.3 Reissue (versioning)

```python
def reissue(spec):
    if spec.workflow_state != "Withdrawn":
        frappe.throw(_("Chỉ Withdraw spec mới có thể Reissue"))
    new = frappe.copy_doc(spec)
    new.parent_spec = spec.name
    new.version = bump_minor(spec.version)  # "1.0" -> "2.0"
    new.workflow_state = "Draft"
    new.lifecycle_events = []
    new.insert()
    return new.name
```

---

## 6. Hooks

```python
doc_events = {
  "IMM Tech Spec": {
    "before_insert": "assetcore.services.imm02.seed_default_requirements",
    "validate":      "assetcore.services.imm02.validate_tech_spec",
    "before_submit": "assetcore.services.imm02.before_submit_tech_spec",
    "on_submit":     "assetcore.services.imm02.lock_spec",
  },
  "IMM Market Benchmark": {
    "validate":  "assetcore.services.imm02.validate_benchmark",
  },
  "IMM Lock-in Risk Assessment": {
    "validate":  "assetcore.services.imm02.compute_lock_in",
  },
}
scheduler_events = {
  "daily":   ["assetcore.tasks_imm02.check_overdue_drafts"],
  "weekly":  ["assetcore.tasks_imm02.benchmark_freshness_alert"],
  # Frappe v15 không có "quarterly" → cron
  "cron": {"0 3 1 1,4,7,10 *": ["assetcore.tasks_imm02.compatibility_recheck"]},
}
```

---

## 7. Permission

Permlevel 0 default; permlevel 1 cho `lock_in_score`, `mitigation_plan`, `mitigation_evidence`, `approver` (chỉ QA Risk Team + PTP Khối 1 + VP Block1 + CMMS Admin).

---

## 8. Integration

| Module | Trigger |
|---|---|
| IMM-01 (Plan) | API `imm01.set_plan_line_in_procurement(plan_line)` khi spec Locked |
| IMM-04 (Commissioning prep) | Khi infra_compat có "Need Upgrade", auto-tạo task `IMM-04 Prep Item` |
| IMM-03 (Vendor Eval) | publish_realtime `imm02_spec_locked` → IMM-03 listener seed Vendor Evaluation |
| IMM-10 (Risk Register) | Khi lock_in_score > threshold + có mitigation, tạo entry trong Risk Register |
| IMM-17 (Predictive) | Market Benchmark export vào data mart phân tích model trend |

---

## 9. Migration

| Patch | Mục đích |
|---|---|
| `v0_1_0.create_imm02_doctypes` | Bootstrap |
| `v0_1_0.install_imm02_workflow` | Workflow JSON |
| `v0_1_0.seed_lock_in_weights` | Master weights |
| `v0_1_0.seed_default_spec_templates` | Template cho 10 device category phổ biến |

---

## 10. Test strategy

- Unit: 6 VR + 4 Gate + spec_match + lock_in compute + reissue.
- Integration: full Draft → Locked + IMM-03 listener triggered.
- Versioning: Withdraw → Reissue chain version 1.0 → 3.0.
- Permission: lock-in score chỉ QA Risk Team thấy permlevel 1.

*End of Technical Design v0.1.0 — IMM-02*
