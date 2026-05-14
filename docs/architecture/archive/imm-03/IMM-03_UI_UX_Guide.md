# IMM-03 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Eval & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |

---

## 1. Routes

| Route | Component | Role |
|---|---|---|
| `/imm03/vendor-profile` | `VendorProfileList.vue` | All IMM |
| `/imm03/vendor-profile/:name` | `VendorProfileDetail.vue` | All IMM |
| `/imm03/avl` | `AvlList.vue` | All IMM |
| `/imm03/avl/:name` | `AvlDetail.vue` | All IMM |
| `/imm03/evaluation` | `EvaluationList.vue` | ĐT-HĐ-NCC, KH-TC, HTM Engineer, QA Risk |
| `/imm03/evaluation/:name` | `EvaluationDetail.vue` | (như trên) |
| `/imm03/decision` | `DecisionList.vue` | ĐT-HĐ-NCC, PTP Khối 1, VP Block1 |
| `/imm03/decision/:name` | `DecisionDetail.vue` | (như trên) |
| `/imm03/scorecard` | `ScorecardView.vue` | KH-TC, PTP Khối 1, VP Block1 |
| `/imm03/audit/:name` | `SupplierAuditDetail.vue` | QA Risk Team |
| `/imm03/dashboard` | `Imm03Dashboard.vue` | KH-TC, PTP Khối 1, VP Block1 |

Sidebar group: **Khối 1 — Hoạch định** > Nhà cung cấp & Mua sắm.

---

## 2. Wireframes

### 2.1 VendorProfileList

```
Nhà cung cấp                                         [+ Tạo profile]
─────────────────────────────────────────────────────────────────────
Filter: [AVL Status▾] [Category▾] [Score≥▾] [Audit overdue ⏰]   🔍
─────────────────────────────────────────────────────────────────────
VINAMED       Vinamed JSC      Imaging,Life     ✓ Approved   4.3 ★★★★
                              Support
              Cert: ISO 9001 (✓), ĐKLH (✓), ISO 13485 (⚠ exp 30d)
              Audit 2026-01-15 → next 2027-01-15

HAMILTON-VN   Hamilton Vietnam Imaging          ⚠ Conditional 3.8 ★★★
              Cert: ISO 13485 (✓), CE (✓)
              Audit 2025-08-10 → next 2026-08-10  ⏰
─────────────────────────────────────────────────────────────────────
```

### 2.2 VendorProfileDetail

4-tab layout:

```
[1. Hồ sơ] [2. Chứng chỉ] [3. AVL] [4. Lịch sử Score & Audit]

Header: VINAMED · Vinamed JSC · ★★★★ 4.3 · ✓ Approved
        Imaging, Life Support · MST 0301234567 · VN

Tab 2: bảng Cert với badge status (Active / Expiring 30d / Expired)
Tab 3: AVL entries list theo category + validity timeline
Tab 4: Scorecard chart 5 quarter gần nhất + Audit history với findings
```

### 2.3 EvaluationDetail

3-tab layout với workflow stepper:

```
Stepper: Draft ▶ Open RFQ ▶ Quotation Received ▶ Evaluated

[1. Candidates & RFQ] [2. Chấm điểm] [3. Tổng hợp]

Tab 1:
  Candidate table (≥3 rows for đấu thầu rộng rãi)
    Vendor       AVL?   Quotation         Validity  Price
    Vinamed       ✓     QT-2026-001       60d        2.1 tỷ
    Hamilton VN   ⚠      QT-2026-002       60d        1.9 tỷ
    Mindray VN    ✓     QT-2026-003       45d        1.4 tỷ
  [+ Thêm candidate]   [Open RFQ]   [Upload bulk quotation]

Tab 2: Score grid by group (Technical / Commercial / Financial / Support / Compliance)
  Mỗi group hiển thị scorer phụ trách (HTM/KH-TC/TCKT/QA Risk)
  Inline edit số 1-5 + remark
  Auto-compute weighted_score per candidate (sticky right panel)

Tab 3:
  Recommended badge: Vinamed (4.32) — top weighted
  Compare table 3 candidate side-by-side
  [Tạo Procurement Decision]
```

### 2.4 DecisionDetail

```
Stepper: Draft ▶ Method Selected ▶ Negotiation ▶ Award Recommended ▶ Pending Approval ▶ Awarded ▶ Contract Signed ▶ PO Issued

Header: PD-26-00045 · TS-26-00045 · Plan PP-26-001 · Đấu thầu rộng rãi

Block "Phương án mua sắm":
  procurement_method (select)  — auto-validate G04 với giá trị + loại hàng
  method_legal_basis (richtext) — bắt buộc với "Chỉ định thầu"

Block "Winner & Giá":
  winner_candidate (select từ Eval) → auto fill awarded_vendor
  awarded_price (currency) — envelope_check_pct gauge
  funding_source (select) + funding_evidence (attach)

Block "Phê duyệt":
  board_approver  +  contract_doc

Action footer:
  [Trình BGĐ] / [Awarded ✓ Mint PO] / [Cancel]   theo state + role
  Sau Awarded: tab phụ "PO" → ERPNext PO link clickable
```

### 2.5 AvlDetail

```
AVL-2026-00045 · VINAMED · Imaging
Validity: 2026-05-01 → 2028-04-30  (2 năm)
Status: Approved by VP Block1 trên 2026-05-15

Timeline visual:
  ▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░  Jun-26 (1m)  Hết hạn 2028-04-30
  Cảnh báo 60d / 30d / 0d
```

### 2.6 ScorecardView

```
Vendor: VINAMED · 2026 Q2 · Overall 4.3 ★★★★

Radar chart 5 dimension:
        Delivery 4.5
          ╱   ╲
   Comp 4.0     Quality 4.4
          ╲   ╱
   Spare 4.1   Aftersales 4.2

Trendline 5 quarter gần nhất
Dimension breakdown table: raw_value · normalized · weighted · source
```

### 2.7 Imm03Dashboard

```
KPI tiles (7):
  Lead time Eval→Awarded   AVL coverage   Avg vendor score
       55d / 60d                 82%             4.1 / 4.0
  AVL pick rate   Audit completion   Supplier NC rate   Cost saving
       92% / 90%       97% / 95%          0.8% (↓)        7.2%

Charts:
  - Funnel: Eval Draft → Awarded → PO Issued
  - AVL expiry timeline (next 6 months)
  - Vendor scorecard ranking top 10
  - NC heatmap by vendor × month
```

---

## 3. Components

| Component | Mục đích |
|---|---|
| `<VendorProfileForm>` | Form tổng 4 tab |
| `<CertTable>` | Cert table có badge expiry |
| `<AvlTimeline>` | Timeline validity per category |
| `<EvalCandidateGrid>` | Candidate + AVL badge + Quotation |
| `<ScoreGroupGrid>` | Chấm điểm by group, scorer phụ trách |
| `<DecisionMethodPicker>` | Method select có auto validate G04 |
| `<EnvelopeGauge>` | Gauge awarded vs envelope (xanh/vàng/đỏ) |
| `<ScorecardRadar>` | Radar 5 dimension |
| `<AuditFindingTable>` | Findings + CAPA tracker |

---

## 4. UX rules

- AVL badge consistent: ✓ Approved (xanh) / ⚠ Conditional (vàng) / 🚫 Suspended (đỏ) / ◷ Expired (xám).
- Awarded price field permlevel 1 → user thiếu quyền thấy `***`.
- Method select disable nếu không hợp pháp với giá trị (G04 inline).
- Confirm dialog khi Award → hiển thị tóm tắt: vendor, price, envelope %, funding, approver.
- PO mint async — toast progress + redirect đến PO khi xong.
- Suspend AVL bắt buộc reason; tự cập nhật mọi Eval đang Open có vendor đó (cảnh báo).
- Audit findings Critical → modal escalation auto-hiện.

---

## 5. Permission UI

| Role | Action visible |
|---|---|
| ĐT-HĐ-NCC Officer | Tạo Vendor Profile, AVL Draft, Evaluation, Decision Draft, RFQ, Quotation, PO Issued |
| HTM Engineer | Chấm Technical group (Tab 2 Eval) |
| KH-TC Officer | Chấm Commercial; xem Scorecard |
| TCKT Officer | Chấm Financial; Contract Signed |
| QA Risk Team | Chấm Compliance; Supplier Audit; Suspend AVL |
| PTP Khối 1 | Submit, trình BGĐ |
| VP Block1 | Approve AVL, Award Decision, sign-off non-AVL |

---

## 6. Empty/loading/error

- Empty Vendor list: "Chưa có vendor — tạo từ Supplier ERPNext".
- Empty Eval candidates: "Thêm tối thiểu 3 candidate cho phương án Đấu thầu rộng rãi".
- 403: "Trường giá trúng thầu chỉ hiển thị với KH-TC/TCKT/PTP Khối 1/VP Block1".
- 409 PO mint fail: "Mint PO thất bại — kiểm tra item mapping của Tech Spec; Decision đã rollback về Pending Approval".

*End of UI/UX Guide v0.1.0 — IMM-03*
