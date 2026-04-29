# IMM-01 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |

---

## 1. Tổng quan kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│  Frappe v15  ·  ERPNext v15  ·  MariaDB 10.11                    │
│  Workflow Engine · Scheduler · ORM · Permission Engine           │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  AssetCore — module AssetCore                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  DocTypes (3 primary + 5 child)                            │  │
│  │  Controllers: imm_needs_request.py · imm_procurement_plan  │  │
│  │  Service:  assetcore/services/imm01.py                     │  │
│  │  API:      assetcore/api/imm01.py                          │  │
│  │  Workflow: workflow/imm_01_needs_workflow.json             │  │
│  │  Scheduler: tasks_imm01.py                                 │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

Module name (Frappe `modules.txt`): `AssetCore` (Wave 1 dùng 1 module duy nhất; KHÔNG tạo `imm_planning`).

---

## 2. Schema — Primary DocType

### 2.1 IMM Needs Request

Naming: `IMM01-NR-.YY.-.MM.-.#####`. Submittable. Module: `AssetCore`.

| Section | Field | Type | Req | Default | Options / Link | Rule |
|---|---|---|---|---|---|---|
| **Header** | request_id | Data | Y (auto) | — | — | Read-only naming |
|  | request_date | Date | Y | today | — | `before_insert` set |
|  | request_type | Select | Y | New | New / Replacement / Upgrade / Add-on | Drives VR-02 |
|  | requesting_department | Link | Y | user dept | Department | — |
|  | clinical_head | Link | Y | dept head | User | Auto-fetch |
| **Target** | device_model_ref | Link | Y | — | IMM Device Model | Phải Active |
|  | device_category | Link | N | fetch | Asset Category | Auto từ model |
|  | quantity | Int | Y | 1 | min=1 | — |
|  | target_year | Int | Y | year+1 | — | ≥ current year |
|  | priority_class | Select | N (auto) | — | P1 / P2 / P3 / P4 | Auto từ weighted_score |
| **Justification** | clinical_justification | Long Text | Y | — | — | ≥ 200 chars (VR-03) |
|  | replacement_for_asset | Link | C* | — | Asset | Bắt buộc khi type=Replacement |
|  | utilization_pct_12m | Float | C | — | — | Auto-fetch từ IMM-07 |
|  | downtime_hr_12m | Float | C | — | — | Auto-fetch từ IMM-07 |
|  | compliance_driven | Check | N | 0 | — | Cờ từ IMM-10 |
| **Scoring** | weighted_score | Float | N (auto) | 0 | — | Auto-compute từ scoring_rows |
|  | scoring_rows | Table | C | — | Needs Priority Scoring | 6 rows mandatory ở G02 |
| **Budget** | total_capex | Currency | N (auto) | — | — | Σ budget_lines (CAPEX) |
|  | total_opex_5y | Currency | N (auto) | — | — | Σ budget_lines (OPEX) |
|  | tco_5y | Currency | N (auto) | — | — | total_capex + total_opex_5y |
|  | budget_lines | Table | C | — | Budget Estimate Line | ≥ 1 CAPEX + 5 OPEX years (G03) |
|  | funding_source | Select | C | — | NSNN / Tài trợ / Xã hội hóa / BHYT / Khác | Bắt buộc trước Submit (G05) |
|  | funding_evidence | Attach | N | — | — | — |
| **Approval** | board_approver | Link | C | — | User | Bắt buộc trước Approved (G05) |
|  | approval_date | Date | N (auto) | — | — | — |
|  | rejection_reason | Long Text | C | — | — | Bắt buộc khi Reject |
| **Linkage** | procurement_plan | Link | N | — | IMM Procurement Plan | Set khi gom vào plan |
|  | tech_spec_ref | Link | N | — | IMM Tech Spec | Set khi IMM-02 generate |
| **Workflow** | workflow_state | Data | Y (auto) | Draft | (workflow) | — |
|  | (audit) | — | — | — | `IMM Audit Trail` (Wave 1) | KHÔNG tạo child table riêng — query qua root_doctype/root_record |

(*) C = conditional required.

**Indexes:**
- `idx_nr_state_dept (workflow_state, requesting_department)`
- `idx_nr_replacement (replacement_for_asset)` (sparse)
- `idx_nr_plan (procurement_plan)`

### 2.2 IMM Procurement Plan

Naming: `IMM01-PP-.YY.-.#####`. Submittable. Module: `AssetCore`.

| Section | Field | Type | Req | Note |
|---|---|---|---|---|
| Header | plan_period | Select | Y | Q1/Q2/Q3/Q4/Annual |
|  | plan_year | Int | Y | — |
|  | budget_envelope | Currency | Y | Tổng cap được duyệt cho kỳ |
|  | allocated_capex | Currency | N (auto) | Σ allocated_budget của plan_items |
|  | utilization_pct | Percent | N (auto) | allocated / envelope |
| Items | plan_items | Table | Y | Procurement Plan Line |
| Approval | approved_by | Link → User | C | — |
|  | approved_date | Date | N | — |
| State | workflow_state | — | — | Draft / Approved / Active / Closed |

### 2.3 IMM Demand Forecast

Naming: `IMM01-DF-.YYYY.-.#####`. Read-only output, không submittable.

| Field | Type | Note |
|---|---|---|
| forecast_year | Int | Năm bắt đầu |
| horizon_years | Int | Số năm dự báo (3 hoặc 5) |
| device_category | Link → Asset Category | — |
| projected_qty | Int | Tổng số thiết bị dự kiến |
| projected_capex | Currency | Tổng CAPEX dự kiến |
| accuracy_prev | Percent | Đối chiếu kỳ trước |
| drivers | Table → Forecast Driver | replacement / utilization growth / service expansion |
| generated_at | Datetime | Auto |
| generated_by | Link → User | scheduler |

---

## 3. Child Tables

### 3.1 Needs Priority Scoring

| Field | Type | Note |
|---|---|---|
| criterion | Select | clinical_impact / risk / utilization_gap / replacement_signal / compliance_gap / budget_fit |
| score | Int | 1–5 |
| weight_pct | Percent | Read-only fetch từ master |
| weighted | Float | score × weight |
| evidence | Long Text | Lý giải |

### 3.2 Budget Estimate Line

| Field | Type | Note |
|---|---|---|
| budget_section | Select | CAPEX / OPEX |
| line_type | Select | Device / Install / Training / Infra / Accessory / PM / Calibration / Spare / Consumable / Software / Insurance / Other |
| year_offset | Int | 0 = year of purchase; 1–5 = OPEX years |
| qty | Float | — |
| unit_cost | Currency | — |
| amount | Currency | qty × unit_cost (auto) |
| benchmark_source | Data | Tham chiếu thị trường |
| notes | Small Text | — |

### 3.3 Procurement Plan Line

| Field | Type | Note |
|---|---|---|
| needs_request | Link → IMM Needs Request | Y |
| priority_rank | Int | Auto sort by weighted_score desc |
| allocated_budget | Currency | Y |
| target_quarter | Select | Q1–Q4 |
| status | Select | Pending Spec / In Spec / In Procurement / Awarded / Cancelled |

### 3.4 ~~Needs Lifecycle Event~~ — reuse `IMM Audit Trail` (Wave 1)

**KHÔNG tạo child table riêng.** Mọi state change ghi vào `IMM Audit Trail` với:
- `root_doctype = "IMM Needs Request"`
- `root_record = doc.name`
- `event_type`, `from_status`, `to_status`, `actor`, `timestamp`, `ip_address`, `notes`

VR-01-06 (immutable) đã được enforce ở chính `IMM Audit Trail` → không cần lặp lại trong module IMM-01.

(Nội dung legacy về schema lifecycle event bên dưới giữ làm tham chiếu shape — nhưng triển khai thực tế dùng `IMM Audit Trail`.)

| Field | Type |
|---|---|
| event_type | Data (Submitted/Reviewing/Prioritized/Budgeted/Approved/Rejected/Returned) |
| from_status | Data |
| to_status | Data |
| actor | Link → User |
| event_timestamp | Datetime |
| ip_address | Data |
| remarks | Small Text |

VR-06: row đã có `event_timestamp` không cho update/delete.

### 3.5 Forecast Driver

| Field | Type |
|---|---|
| driver_type | Select (replacement / utilization_growth / service_expansion / compliance / strategic) |
| weight_pct | Percent |
| projected_value | Float |
| source_module | Data (IMM-07 / IMM-13 / IMM-10) |

---

## 4. Validation Rules (VR)

| ID | Rule | Function | Trigger |
|---|---|---|---|
| VR-01-01 | 1 Asset chỉ có 1 Active Needs Request thay thế | `_vr01_unique_active_request_per_asset()` | `validate()` |
| VR-01-02 | Replacement type cần Decommission Plan | `_vr02_replacement_requires_decom_plan()` | `validate()` |
| VR-01-03 | clinical_justification ≥ 200 chars | `_vr03_clinical_justification()` | `validate()` |
| VR-01-04 | target_year ≥ current_year | `_vr04_target_year()` | `validate()` |
| VR-01-05 | weighted_score = Σ score × weight, sai số < 0.01 | `_vr05_score_consistency()` | `validate()` |
| VR-01-06 | Lifecycle events bất biến | `_vr06_immutable_lifecycle_events()` | `validate()` |

## 5. Gates

| Gate | Yêu cầu | Block transition |
|---|---|---|
| G01 | clinical_justification + utilization_pct_12m (nếu Replacement/Upgrade) | Submitted → Reviewing |
| G02 | 6/6 scoring rows + weighted_score | Reviewing → Prioritized |
| G03 | total_capex > 0 + 5 năm OPEX present | Prioritized → Budgeted |
| G04 | tổng allocated trong Procurement Plan ≤ envelope (warning soft, hard nếu config) | Budgeted → Pending Approval |
| G05 | board_approver + funding_source | Pending Approval → Approved |

---

## 6. Hooks

`hooks.py`:

```python
doc_events = {
    "IMM Needs Request": {
        "before_insert": "assetcore.services.imm01.initialize_needs_request",
        "validate":      "assetcore.services.imm01.validate_needs_request",
        "before_submit": "assetcore.services.imm01.before_submit_needs_request",
        "on_submit":     "assetcore.services.imm01.on_submit_needs_request",
        "on_cancel":     "assetcore.services.imm01.on_cancel_needs_request",
    },
    "IMM Procurement Plan": {
        "validate":      "assetcore.services.imm01.validate_procurement_plan",
        "on_submit":     "assetcore.services.imm01.on_submit_procurement_plan",
    },
}

scheduler_events = {
    "daily": [
        "assetcore.tasks_imm01.check_pending_request_overdue",
    ],
    "weekly": [
        "assetcore.tasks_imm01.budget_envelope_alert",
    ],
    "monthly": [
        "assetcore.tasks_imm01.generate_demand_forecast",
    ],
}
```

---

## 7. Algorithms

### 7.1 Priority scoring

```python
DEFAULT_WEIGHTS = {
    "clinical_impact": 0.25,
    "risk": 0.20,
    "utilization_gap": 0.15,
    "replacement_signal": 0.15,
    "compliance_gap": 0.15,
    "budget_fit": 0.10,
}

def compute_priority_score(doc):
    weights = get_master_weights()  # fallback DEFAULT_WEIGHTS
    score = 0.0
    for row in doc.scoring_rows:
        w = weights.get(row.criterion, 0)
        row.weight_pct = round(w * 100, 2)
        row.weighted = round(row.score * w, 4)
        score += row.weighted
    doc.weighted_score = round(score, 4)
    if   score >= 4.0: doc.priority_class = "P1"
    elif score >= 3.0: doc.priority_class = "P2"
    elif score >= 2.0: doc.priority_class = "P3"
    else:              doc.priority_class = "P4"
```

### 7.2 Demand forecast (monthly)

```
Input:
  - utilization_pct, downtime, MTBF (IMM-07)
  - decommission queue (IMM-13)
  - service expansion plan (master config)
Pipeline:
  1. group asset by device_category
  2. project replacement_qty = decommission_due_5y + (mtbf_under_threshold × replacement_rate)
  3. apply utilization_growth × current_qty
  4. add service_expansion (manual entry)
  5. multiply by avg_unit_cost (12m benchmark) → projected_capex
  6. write Demand Forecast doc; compute accuracy_prev = 1 - |forecast(t-1) - actual| / actual
```

---

## 8. Permission matrix (snapshot)

Permlevel 0 fields = standard; permlevel 1 = `funding_source`, `funding_evidence`, `board_approver` (chỉ TCKT + PTP Khối 1 + VP Block1).

| Role | Read | Write | Create | Submit | Cancel | Permlevel 1 W |
|---|---|---|---|---|---|---|
| Department User | own dept | own dept (Draft) | Y | — | — | — |
| Clinical Head | own dept | own dept | Y | — | — | — |
| HTM Reviewer | All | Reviewing | — | — | — | — |
| KH-TC Officer | All | Prioritized | — | — | — | — |
| TCKT Officer | All | Budgeted | — | — | — | Y |
| PTP Khối 1 | All | Pending Approval | — | Y | Y | Y |
| VP Block1 | All | — | — | Y | Y | Y |
| CMMS Admin | All | All | Y | Y | Y | Y |

---

## 9. Integration contracts

| Module | Trigger | Cơ chế |
|---|---|---|
| IMM-07 | Khi chọn `replacement_for_asset` | API `imm07.get_asset_kpi_12m(asset)` → fetch utilization_pct, downtime |
| IMM-13 | VR-02 + tự động sync khi state Decommission đổi | API `imm13.get_active_decom_plan(asset)` |
| IMM-10 | Tự động set `compliance_driven=1` | Hook khi Compliance Gap mới tạo có `recommended_replacement=1` |
| IMM-02 | Action `Generate Tech Spec Drafts` từ Procurement Plan | Service `imm02.draft_from_plan(plan)` |
| IMM-03 | Sau khi Tech Spec lock | Service `imm03.create_vendor_eval_from_plan(plan)` |
| IMM-15 | Demand Forecast publish | Realtime event `imm01_demand_forecast_published` |

---

## 10. Migration & Patches

| Patch | Mục đích |
|---|---|
| `assetcore.patches.v0_1_0.create_imm01_doctypes` | Bootstrap 8 DocType |
| `assetcore.patches.v0_1_0.install_imm01_workflow` | Install workflow JSON |
| `assetcore.patches.v0_1_0.seed_priority_weights` | Seed master weights mặc định |
| `assetcore.patches.v0_1_0.backfill_replacement_links` | Map IMM-13 Decommission Plan → Needs Request đã có |

---

## 11. Test strategy

- Unit test: 6 VR + 5 Gate + scoring algorithm + forecast pipeline.
- Integration test: full happy path Draft → Approved + Procurement Plan rollup.
- Load test: 10k Needs Request, list query < 2s.
- Workflow test: each transition role-restricted.

*End of Technical Design v0.1.0 — IMM-01*
