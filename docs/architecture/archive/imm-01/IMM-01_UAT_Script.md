# IMM-01 — UAT Script

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |
| Tổng test case | 32 |

---

## 1. Pre-requisites

- AssetCore deployed; `bench migrate` thành công.
- Master data: `IMM Device Model`, `Department`, role-permission, scoring weights seeded.
- Test users:
  - `dept_user@hospital.vn` — Department User (ICU)
  - `head.icu@hospital.vn` — Clinical Head (ICU)
  - `htm.reviewer@hospital.vn` — HTM Reviewer
  - `khtc@hospital.vn` — KH-TC Officer
  - `tckt@hospital.vn` — TCKT Officer
  - `ptp.k1@hospital.vn` — PTP Khối 1
  - `vp.block1@hospital.vn` — VP Block1
  - `cmms.admin@hospital.vn` — CMMS Admin

---

## 2. Test Cases

### A. Tạo & validate cơ bản (TC-01 → TC-08)

**TC-01 — Tạo Needs Request hợp lệ (New)**
- Login `head.icu`. Tạo NR type=New, đủ field, justification ≥ 200 chars.
- Expected: lưu thành công, state=Draft, name=NR-26-MM-XXXXX.

**TC-02 — VR-03 thiếu justification**
- Tạo NR với justification 50 chars.
- Expected: throw "VR-01-03: clinical_justification phải ≥ 200 ký tự".

**TC-03 — VR-02 Replacement không có Decom Plan**
- Tạo NR type=Replacement, asset không có IMM-13 plan.
- Expected: VR-01-02 throw.

**TC-04 — VR-02 Replacement có Decom Plan Pending**
- Tạo Decom Plan IMM-13 trạng thái Pending → tạo NR Replacement.
- Expected: pass.

**TC-05 — VR-04 target_year < current_year**
- target_year=2025 (current=2026).
- Expected: VR-01-04 throw.

**TC-06 — Auto-fetch utilization từ IMM-07**
- Tạo NR Replacement, asset có 12-month KPI trong IMM-07.
- Expected: utilization_pct_12m, downtime_hr_12m auto-fill.

**TC-07 — Permission Department User không sửa NR khoa khác**
- Login `dept_user` (ICU); cố mở NR khoa NICU.
- Expected: 403 / không thấy.

**TC-08 — Submit Draft → Submitted (G01 pass)**
- Login `head.icu`, NR đủ data + utilization → Submit.
- Expected: state Submitted; lifecycle event "Submitted" ghi.

### B. Scoring & Priority (TC-09 → TC-14)

**TC-09 — G01 thiếu utilization (Replacement)**
- NR Replacement, không fill utilization_pct_12m, click Submit.
- Expected: G01 fail.

**TC-10 — Score 6 tiêu chí + tính weighted**
- Login `htm.reviewer`. Điền: 5,5,4,5,3,3 → expected weighted = 4.30 (theo trọng số mặc định).
- Expected: weighted_score=4.30, priority_class=P1.

**TC-11 — VR-05 score consistency**
- Manual chỉnh `weighted` rows ≠ score×weight, save.
- Expected: VR-01-05 throw, recompute auto.

**TC-12 — G02 thiếu 1 tiêu chí**
- Chấm 5/6, click "Hoàn tất chấm điểm".
- Expected: G02 fail "Cần đủ 6/6 tiêu chí".

**TC-13 — Reviewing → Prioritized happy path**
- 6 score đầy đủ → Prioritized.
- Expected: state Prioritized, lifecycle event "Prioritized".

**TC-14 — Master weights override**
- Admin chỉnh trọng số (vd: clinical_impact 30%) → recompute NR có sẵn.
- Expected: weighted_score đổi theo trọng số mới.

### C. Budget Estimate (TC-15 → TC-19)

**TC-15 — Submit Budget Estimate đủ CAPEX + 5y OPEX**
- Login `tckt`, fill 5 CAPEX + 5×6 OPEX.
- Expected: total_capex, total_opex_5y, tco_5y compute đúng.

**TC-16 — G03 thiếu OPEX year 4**
- Bỏ qua year 4.
- Expected: G03 fail "Phải có OPEX 5 năm liên tục".

**TC-17 — G04 vượt envelope (warning soft)**
- Tổng CAPEX vượt 80% envelope quý.
- Expected: warning hiển thị, không block.

**TC-18 — G04 hard block (config enforce)**
- Config enforce_envelope=1, CAPEX vượt 100%.
- Expected: G04 fail.

**TC-19 — Funding source bắt buộc trước Submit**
- Cố Submit không funding_source.
- Expected: G05 fail.

### D. Approval flow (TC-20 → TC-24)

**TC-20 — Trình BGĐ**
- Login `ptp.k1` chuyển Budgeted → Pending Approval.
- Expected: state Pending Approval, email VP Block1.

**TC-21 — VP Block1 Approve**
- Login `vp.block1` Approve, ghi remarks.
- Expected: docstatus=1, state Approved, lifecycle event ghi với approver.

**TC-22 — VP Block1 Reject**
- Reject với rejection_reason.
- Expected: docstatus=1, state Rejected.

**TC-23 — Reject thiếu reason**
- Reject không nhập reason.
- Expected: throw "Phải nhập rejection_reason".

**TC-24 — Permission: Department User cố Approve**
- Login `dept_user` gọi `approve_needs_request`.
- Expected: PERM-DENY 403.

### E. Procurement Plan (TC-25 → TC-28)

**TC-25 — Roll into Plan**
- 5 NR Approved → `roll_into_plan` plan_year=2027.
- Expected: PP-26-001 tạo, plan_items sort by weighted_score desc.

**TC-26 — Generate Tech Spec Drafts**
- Click action trên Plan.
- Expected: 5 Tech Spec draft (IMM-02) được tạo, link `tech_spec_ref` set.

**TC-27 — Allocated > envelope**
- Try allocate > envelope.
- Expected: warning + utilization_pct hiển thị > 100%.

**TC-28 — Plan immutable sau Submit**
- Submit Plan → cố sửa plan_items.
- Expected: cấm.

### F. Demand Forecast (TC-29 → TC-30)

**TC-29 — Monthly forecast generation**
- Trigger scheduler `generate_demand_forecast`.
- Expected: Demand Forecast doc tạo, drivers + matrix populated.

**TC-30 — Accuracy đối chiếu kỳ trước**
- Forecast 2026 đã có; nhập actual 2026.
- Expected: accuracy_prev compute.

### G. Audit & Dashboard (TC-31 → TC-32)

**TC-31 — Lifecycle events bất biến**
- Cố sửa row lifecycle có timestamp.
- Expected: VR-01-06 throw.

**TC-32 — Dashboard KPI 6 chỉ số**
- GET `dashboard_kpis?period=2026-Q2`.
- Expected: 6 KPI đúng công thức + delta so với Q1.

---

## 3. Test Data

| Asset | Department | Để dùng cho |
|---|---|---|
| ASSET-ICU-0014 | ICU | TC-04 (có Decom Plan) |
| ASSET-NICU-0021 | NICU | TC-03 (không Decom Plan) |

| Device Model | Để dùng cho |
|---|---|
| IMM-MDL-2024-0007 (Máy thở) | TC-01, TC-04 |
| IMM-MDL-2023-0103 (Lồng ấp) | TC-25 |

---

## 4. Defect log template

| ID | TC | Severity | Mô tả | Steps | Expected | Actual | Status | Owner |
|---|---|---|---|---|---|---|---|---|

---

## 5. Acceptance

- ≥ 95% PASS để release.
- 0 Critical + ≤ 2 High open.
- Audit trail complete cho mọi state change.

*End of UAT Script v0.1.0 — IMM-01*
