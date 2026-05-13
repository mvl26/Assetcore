# IMM-01 — Đánh giá Nhu cầu & Dự toán (Module Overview)

> **⚠ Wave 2 Alignment** — Trước khi triển khai phải đọc `docs/WAVE2_ALIGNMENT.md` để áp dụng các hiệu chỉnh khớp Wave 1 LIVE: module Frappe `AssetCore` (không phải `imm_planning`); naming series `IMM01-…`; reuse `AC Asset` / `AC Department` / `IMM Device Model` / `IMM Audit Trail`; envelope API `{success, data|error, code}`; ErrorCode enum chuẩn; Frappe Role `IMM …` (6 role mới sẽ được fixture); audit trail dùng `IMM Audit Trail` thay vì child `Needs Lifecycle Event`.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán (Needs Assessment & Budget Estimation) |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT — Wave 2 (chưa triển khai code) |
| Tác giả | AssetCore Team |
| Khối kiến trúc | A. KHỐI 1 — Planning & Procurement |
| QC nền | QC-IMMIS-01 |

---

## 1. Mục đích

IMM-01 là **needs intake gateway** — điểm khởi đầu của vòng đời quản trị thiết bị y tế (WHO HTM lifecycle: *Needs Assessment*). Module chuẩn hóa:

- Tiếp nhận đề xuất nhu cầu thiết bị (mới / thay thế / nâng cấp / bổ sung) từ khoa lâm sàng và kế hoạch chiến lược của bệnh viện.
- Chấm điểm ưu tiên đầu tư đa tiêu chí (clinical impact, risk, utilization gap, replacement signal, compliance gap, budget fit).
- Lập dự toán (CAPEX + OPEX 5 năm) và đối chiếu nguồn vốn (ngân sách, tài trợ, BHYT, xã hội hóa).
- Quản lý ngoại lệ (exception adjustment) khi nhu cầu vượt budget envelope hoặc cần ưu tiên đặc biệt.
- Dự báo nhu cầu (demand forecast) phục vụ kế hoạch đầu tư dài hạn (3–5 năm) cho khối Block 1.

Không có **Procurement Plan** ở trạng thái `Approved` (docstatus=1) thì hồ sơ không được chuyển sang IMM-02 (Spec) và IMM-03 (Vendor / PO).

**Chuẩn tham chiếu:** WHO — *Needs assessment for medical devices* (2011, cập nhật 2025); WHO — *Introduction to medical equipment inventory management*; ISO 13485 §7.1; NĐ 98/2021/NĐ-CP (kế hoạch đầu tư trang thiết bị y tế); Luật Đấu thầu 22/2023/QH15.

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│   Inputs                                                         │
│   • Đề xuất khoa lâm sàng (Clinical Department Request)          │
│   • IMM-07 Performance Tracking (replacement signal)             │
│   • IMM-13 Decommission Plan (asset retirement → replacement)    │
│   • IMM-10 Compliance Gap (compliance-driven needs)              │
│   • Strategic Plan / Master Plan của bệnh viện                   │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│   IMM-01 — Needs Assessment & Budget Estimation (intake gateway) │
│                                                                  │
│   Workflow 8 states · 5 Gate · 6 VR · 7 BR                       │
│   DocTypes:                                                      │
│     • Needs Request           (đầu vào, naming NR-…)             │
│     • Needs Priority Scoring  (chấm điểm đa tiêu chí)            │
│     • Budget Estimate         (CAPEX + OPEX 5 năm)               │
│     • Procurement Plan        (gói đầu tư đã duyệt — cha)        │
│     • Demand Forecast         (dự báo 3–5 năm theo device class) │
│   API: assetcore/api/imm01.py        (≈ 14 endpoints)            │
│   Service: assetcore/services/imm01.py                           │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│   Outputs                                                        │
│   • Procurement Plan (Approved) → IMM-02 (Tech Spec)             │
│   • Procurement Plan → IMM-03 (Vendor Eval & PO)                 │
│   • Demand Forecast → IMM-15 (Spare Parts) & IMM-17 (Predictive) │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. DocTypes

### 3.1 Primary DocTypes

| DocType | Naming | Submittable | Mô tả |
|---|---|---|---|
| `IMM Needs Request` | `NR-.YY.-.MM.-.#####` | Yes | Phiếu đề xuất nhu cầu thiết bị từ khoa lâm sàng — nguồn nhập |
| `IMM Procurement Plan` | `PP-.YY.-.#####` | Yes | Gói đầu tư tổng hợp đã duyệt — chứa danh sách Needs Request, Budget Estimate, ưu tiên xếp hạng |
| `IMM Demand Forecast` | `DF-.YYYY.-.#####` | No | Dự báo nhu cầu 3–5 năm theo device category, dùng làm input cho Procurement Plan kỳ kế |

### 3.2 Child Tables

| Child DocType | Parent | Mục đích |
|---|---|---|
| `Needs Priority Scoring` | `IMM Needs Request.scoring_rows` | Lưới điểm 6 tiêu chí (clinical_impact, risk, utilization_gap, replacement_signal, compliance_gap, budget_fit) — weighted score |
| `Budget Estimate Line` | `IMM Needs Request.budget_lines` | Chi tiết dự toán: CAPEX device, install, training, OPEX 5 năm (PM, calibration, spare, consumable) |
| `Procurement Plan Line` | `IMM Procurement Plan.plan_items` | 1 dòng = 1 Needs Request được gom vào kế hoạch, kèm priority_rank, allocated_budget |
| ~~Needs Lifecycle Event~~ | — | **KHÔNG tạo child table riêng** — audit trail dùng `IMM Audit Trail` (root_doctype=IMM Needs Request, root_record=name). Reuse Wave 1, đảm bảo nguyên tắc bất biến tập trung. |
| `Forecast Driver` | `IMM Demand Forecast.drivers` | Hệ số dự báo: replacement rate, utilization growth, service expansion |

### 3.3 DocType liên quan (Link)

| DocType | Link |
|---|---|
| `IMM Device Model` | `Needs Request.device_model_ref` (mục tiêu mua) |
| `Department` | `Needs Request.requesting_department` |
| `Asset` | `Needs Request.replacement_for_asset` (nếu là thay thế) |

---

## 4. Service Functions

File dự kiến: `assetcore/services/imm01.py`

| Function | Hook / Caller | Mục đích |
|---|---|---|
| `initialize_needs_request(doc)` | `before_insert` | Set `request_date`, fetch `requester_role`, `clinical_dept`, gắn replacement signal nếu có |
| `compute_priority_score(doc)` | `validate()` + API | Tính `weighted_score` từ 6 tiêu chí; phân loại P1/P2/P3/P4 |
| `validate_budget_estimate(doc)` | `validate()` | Tổng CAPEX + OPEX 5 năm khớp `budget_lines`; warning nếu lệch >10% benchmark |
| `_vr01_unique_active_request_per_asset(doc)` | `validate()` | VR-01: 1 Asset chỉ có 1 Needs Request `Active` (replacement) tại 1 thời điểm |
| `_vr02_replacement_requires_decom_plan(doc)` | `validate()` | VR-02: nếu `request_type=Replacement` thì `replacement_for_asset` phải có IMM-13 Decommission Plan ở trạng thái `Approved` hoặc `Pending` |
| `_vr06_immutable_lifecycle_events(doc)` | `validate()` | Block sửa lifecycle row đã có |
| `validate_gate_g01(doc)` | `validate()` | G01: clinical justification + utilization data đủ trước khi rời `Submitted` |
| `validate_gate_g02(doc)` | `validate()` | G02: priority scoring 6/6 tiêu chí trước `Prioritized` |
| `validate_gate_g03(doc)` | `validate()` | G03: budget estimate đủ CAPEX + OPEX trước `Budgeted` |
| `validate_gate_g04(doc)` | `validate()` | G04: budget envelope check — không vượt allocated cap của khoa/quý |
| `validate_gate_g05(doc)` | `controller.before_submit()` | G05: BGĐ approver + nguồn vốn xác nhận trước `Approved` |
| `roll_into_procurement_plan(doc)` | service | Gom các Needs Request `Approved` thành Procurement Plan kỳ kế |
| `generate_demand_forecast(period)` | scheduler `monthly` | Tổng hợp utilization + replacement signal + service expansion → Demand Forecast |
| `check_pending_request_overdue()` | scheduler `daily` | Cảnh báo PTP Khối 1 các phiếu `Submitted/Reviewing` quá 30 ngày |
| `log_lifecycle_event(doc, event_type, ...)` | controller hooks | Append audit trail |

---

## 5. Workflow States & Transitions

Workflow JSON: `assetcore/assetcore/workflow/imm_01_needs_workflow.json` — `IMM-01 Needs Workflow`.
`workflow_state_field = workflow_state`.

### 5.1 States (8)

| State | doc_status | Type | Allow Edit | Gate |
|---|---|---|---|---|
| `Draft` | 0 | Success | Clinical Head / Department User | — |
| `Submitted` | 0 | Warning | Department User | G01 |
| `Reviewing` | 0 | Warning | HTM Reviewer | — |
| `Prioritized` | 0 | Success | KH-TC Officer | G02 |
| `Budgeted` | 0 | Success | TCKT Officer | G03 + G04 |
| `Pending Approval` | 0 | Warning | PTP Khối 1 | — |
| `Approved` | 1 | Success | BGĐ / VP Block1 | G05 (terminal positive) |
| `Rejected` | 1 | Danger | BGĐ / VP Block1 | terminal negative |

### 5.2 Transition matrix (rút gọn)

| From → To | Action (vi) | Allowed Role |
|---|---|---|
| Draft → Submitted | Gửi đề xuất | Clinical Head / Department User |
| Submitted → Reviewing | Tiếp nhận rà soát | HTM Reviewer / KH-TC Officer |
| Submitted → Draft | Yêu cầu bổ sung | HTM Reviewer |
| Reviewing → Prioritized | Hoàn tất chấm điểm | KH-TC Officer |
| Reviewing → Rejected | Bác đề xuất (sớm) | PTP Khối 1 |
| Prioritized → Budgeted | Lập dự toán xong | TCKT Officer |
| Budgeted → Pending Approval | Trình BGĐ | PTP Khối 1 |
| Pending Approval → Approved | BGĐ duyệt | VP Block1 / BGĐ |
| Pending Approval → Rejected | BGĐ bác | VP Block1 / BGĐ |
| Pending Approval → Budgeted | Yêu cầu chỉnh dự toán | VP Block1 |

---

## 6. Schedulers

| Job | Tần suất | Logic | Recipient |
|---|---|---|---|
| `assetcore.services.imm01.check_pending_request_overdue` | Daily 02:00 | docstatus=0, không terminal, request_date > 30 ngày | PTP Khối 1, KH-TC Officer (email) |
| `assetcore.services.imm01.generate_demand_forecast` | Monthly (1st, 02:30) | Quét utilization IMM-07 + replacement signal IMM-13 + service expansion → tạo Demand Forecast draft | KH-TC Officer |
| `assetcore.services.imm01.budget_envelope_alert` | Weekly | Cảnh báo khi tổng dự toán vượt 80% budget envelope quý | PTP Khối 1, TCKT Head |

---

## 7. Roles & Permissions

Cột "Tổ chức" để tham chiếu — JSON permission DocType phải dùng tên Frappe Role ở cột "Role".

| Role (Frappe) | Tổ chức tương ứng | Quyền chính trên IMM-01 |
|---|---|---|
| `IMM Clinical User` | Department User (khoa lâm sàng) | Create/Read/Write Needs Request (filter dept của user) |
| `IMM Clinical User` (head subset) | Clinical Head (Trưởng khoa) | Submit (Draft → Submitted) phiếu khoa mình |
| `IMM HTM Engineer` *(Wave 2 mới)* | HTM Reviewer (Nhóm HTM) | Read/Write toàn bộ; chấm clinical_impact + risk |
| `IMM Planning Officer` *(Wave 2 mới)* | KH-TC Officer | Chấm utilization, replacement, compliance, budget_fit; tạo Procurement Plan |
| `IMM Finance Officer` *(Wave 2 mới)* | TCKT Officer | Build Budget Estimate; xác nhận funding_source |
| `IMM Department Head` (đã có Wave 1) | PTP Khối 1 | Submit / Cancel; điều phối, trình BGĐ |
| `IMM Board Approver` *(Wave 2 mới)* | VP Block1 / BGĐ | Approve / Reject (terminal) |
| `IMM System Admin` (đã có Wave 1) | CMMS Admin | Full access |

---

## 8. Business Rules

| BR ID | Rule | Enforce | Chuẩn |
|---|---|---|---|
| BR-01-01 | Mỗi đề xuất phải gắn `requesting_department` và `clinical_justification` ≥ 200 ký tự | `_vr03_clinical_justification()` | WHO Needs Assessment §3.2 |
| BR-01-02 (G01) | Utilization data (12 tháng) bắt buộc nếu `request_type=Replacement` hoặc `Upgrade` | `validate_gate_g01()` | WHO HTM §2.4 |
| BR-01-03 (VR-01) | 1 Asset chỉ có 1 Needs Request `Active` thay thế tại 1 thời điểm | `_vr01_unique_active_request_per_asset()` | Tránh double-allocation |
| BR-01-04 (G02) | Priority scoring đủ 6/6 tiêu chí + weighted_score tính đúng | `compute_priority_score()` + `validate_gate_g02()` | Multi-criteria HTA |
| BR-01-05 (G03) | Budget Estimate phải có cả CAPEX + OPEX 5 năm; thiếu OPEX bị block | `validate_gate_g03()` | WHO Total Cost of Ownership |
| BR-01-06 (G04) | Tổng dự toán không vượt budget envelope quý của khoa (warning soft, hard cap nếu cấu hình) | `validate_gate_g04()` | NĐ 98 §32 |
| BR-01-07 (G05) | `board_approver` + `funding_source` (NSNN / tài trợ / xã hội hóa) bắt buộc trước Submit | `validate_gate_g05()` | Quy trình BV |
| BR-01-08 | Replacement request phải link Decommission Plan (IMM-13) trạng thái Pending/Approved | `_vr02_replacement_requires_decom_plan()` | Lifecycle traceability |

---

## 9. Dependencies

| Module | Quan hệ | Cơ chế |
|---|---|---|
| IMM-07 Performance Tracking | INPUT | Cung cấp `utilization_pct`, `availability`, `downtime` cho replacement signal |
| IMM-10 Compliance | INPUT | Compliance gap → cờ `compliance_driven=1` |
| IMM-13 Decommission | INPUT | Replacement Needs Request phải link Decommission Plan |
| IMM-02 Tech Spec | OUTPUT | Procurement Plan (Approved) → trigger `IMM Tech Spec.draft_from_plan()` |
| IMM-03 Vendor / PO | OUTPUT | Procurement Plan → tạo Vendor Evaluation request và PO sau khi spec lock |
| IMM-15 Spare Parts | OUTPUT | Demand Forecast feed spare demand planning |
| IMM-17 Predictive | OUTPUT | Demand Forecast là input chính cho predictive cockpit |

---

## 10. KPI / Dashboard

KPI-DASH-IMMIS-01:

| KPI | Công thức | Mục tiêu |
|---|---|---|
| Lead time intake → Approved | `avg(approved_date - request_date)` | < 45 ngày |
| % Needs Request đúng thủ tục G01 | `pass_g01 / total_submitted` | ≥ 95% |
| Budget envelope utilization | `Σ approved_capex / quarterly_envelope` | 70–95% |
| Replacement-signal coverage | `replacement_requests / decommissioned_assets` | ≥ 80% |
| Demand Forecast accuracy | `1 − abs(forecast − actual) / actual` | ≥ 85% |
| Backlog > 30 ngày | count `Submitted/Reviewing` quá 30d | giảm dần |

---

## 11. Trạng thái triển khai (Wave 2)

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| DocType + child tables | 📐 DESIGN | Chưa scaffold |
| Workflow 8 states | 📐 DESIGN | JSON pending |
| API layer (~14 endpoints) | 📐 DESIGN | Hợp đồng OpenAPI cần draft |
| Service layer | 📐 DESIGN | — |
| Validation VR-01 → VR-06 | 📐 DESIGN | — |
| Gates G01 → G05 | 📐 DESIGN | — |
| Demand forecast engine | 📐 DESIGN | Cần dữ liệu IMM-07 đầy đủ trước |
| Dashboard KPIs | 📐 DESIGN | — |
| UAT | ⏳ Chưa lập | — |

---

## 12. Tài liệu liên quan

- `IMM-01_Functional_Specs.md` — yêu cầu nghiệp vụ, user stories, acceptance criteria
- `IMM-01_Technical_Design.md` — schema, validation impl, hooks, indexes
- `IMM-01_API_Interface.md` — endpoints với request/response
- `IMM-01_UAT_Script.md` — kịch bản UAT
- `IMM-01_UI_UX_Guide.md` — wireframes, routes, component specs

*End of Module Overview v0.1.0 — IMM-01*
