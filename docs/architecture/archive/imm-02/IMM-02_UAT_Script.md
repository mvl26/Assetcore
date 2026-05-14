# IMM-02 — UAT Script

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-02 — Tech Spec & Market Analysis |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |
| Tổng test case | 28 |

---

## 1. Pre-requisites

- AssetCore deployed; IMM-01 đã có Procurement Plan với plan_items được Approved.
- Master: IMM Spec Template đã seed cho category Imaging, Life Support.
- Test users: htm.engineer, htm.lead, khtc, qa.risk, cntt, ptp.k1, vp.block1, cmms.admin.

---

## 2. Test Cases

### A. Tạo & Requirements (TC-01 → TC-08)

**TC-01 — draft_from_plan tạo Tech Spec từ plan_line**
- Login `khtc`. Plan PP-26-001 có 5 plan_items.
- Action: click "Generate Tech Spec Drafts".
- Expected: 5 spec TS-26-… tạo, mỗi spec link đúng plan_line, requirements seed từ template.

**TC-02 — VR-01 trùng plan_line**
- Cố tạo Tech Spec thứ 2 cho plan_line đã có Active.
- Expected: VR-02-01 throw.

**TC-03 — Thêm requirement hợp lệ**
- Login `htm.engineer`. Thêm 1 requirement mandatory + test_method.
- Expected: lưu thành công.

**TC-04 — VR-03 mandatory thiếu test_method**
- Mandatory requirement không nhập test_method.
- Expected: VR-02-03 throw.

**TC-05 — VR-02 không có mandatory requirement**
- Spec chỉ có optional.
- Expected: VR-02-02 throw.

**TC-06 — Bulk import requirements từ Excel**
- Upload file Excel 25 dòng requirement.
- Expected: 25 dòng vào requirements, validation per row.

**TC-07 — G01 Reviewing thiếu mandatory < 8**
- 6 mandatory + 5 optional, click "Gửi rà soát".
- Expected: G01 fail "Cần ≥ 8 mandatory requirement".

**TC-08 — G01 pass → Reviewing**
- Đủ 8 mandatory + test_method 100%.
- Expected: state Reviewing, lifecycle event "Reviewing".

### B. Market Benchmark (TC-09 → TC-13)

**TC-09 — Submit benchmark 3 candidates**
- Login `khtc`, nhập 3 candidate.
- Expected: MB-26-… tạo, recommended_candidate auto-set.

**TC-10 — VR-04 < 3 candidates**
- 2 candidates submit.
- Expected: VR-02-04 throw.

**TC-11 — Spec match % auto-compute**
- Spec có 8 mandatory; candidate match 7/8 → expected 87.5%.
- Expected: spec_match_pct correct.

**TC-12 — Weighting scheme thay đổi → recommended đổi**
- Đổi price weight 30→50; 1 candidate giá thấp nhất rise top.
- Expected: recommended_candidate đổi.

**TC-13 — G02 Reviewing → Benchmarked**
- 3 candidate đủ.
- Expected: state Benchmarked, lifecycle event ghi.

### C. Infra Compat (TC-14 → TC-17)

**TC-14 — 6/6 mục Infra**
- Login `qa.risk` + `cntt`. Điền 6 mục.
- Expected: pass G03, infra_status_overall compute (Compatible / Partial / Need Major Upgrade).

**TC-15 — Need Upgrade → tạo IMM-04 prep task**
- Có "Need Upgrade" cho Medical Gas + Space.
- Expected: 2 IMM-04 prep task tạo, link spec.

**TC-16 — VR-05 thiếu 1 mục**
- 5/6 mục.
- Expected: VR-02-05 / G03 fail.

**TC-17 — Upgrade cost rollup**
- Tổng upgrade_cost_estimate hiển thị trong header.

### D. Lock-in Risk (TC-18 → TC-22)

**TC-18 — Lock-in score compute**
- 5 dimension scores: 2,4,3,3,4 với trọng số mặc định.
- Expected: lock_in_score = 0.30×2 + 0.20×4 + 0.20×3 + 0.15×3 + 0.15×4 = 3.05.

**TC-19 — G04 score > threshold không có mitigation**
- threshold 2.5, score 3.05, không nhập mitigation_plan.
- Expected: G04 fail trước Lock.

**TC-20 — G04 với mitigation pass**
- Nhập mitigation_plan + evidence.
- Expected: G04 pass.

**TC-21 — Permlevel 1 — HTM Engineer không thấy lock_in_score**
- Login `htm.engineer`.
- Expected: field hidden / icon 🔒.

**TC-22 — Lock-in > 2.5 nhưng < 3.5: cảnh báo soft, không block**
- Threshold soft = 2.5, hard = 3.5; score 3.0 + mitigation.
- Expected: pass với warning.

### E. Approval & Lock (TC-23 → TC-26)

**TC-23 — Trình duyệt và Lock**
- Login `vp.block1`. Approve.
- Expected: docstatus=1, state Locked, event `imm02_spec_locked` publish.
- Expected: IMM-03 Vendor Evaluation seed được tạo (mock listener).
- Expected: IMM-01 Plan line.status = "In Procurement".

**TC-24 — Withdraw spec**
- Locked spec → Withdraw với reason.
- Expected: state Withdrawn, IMM-03 pending eval cancel.

**TC-25 — Reissue (versioning)**
- Click Reissue trên Withdrawn.
- Expected: TS-26-00046 v2.0, parent_spec=TS-26-00045, requirements copy, state Draft.

**TC-26 — Locked spec không sửa được**
- Cố sửa requirement trên Locked.
- Expected: throw "Spec Locked — chỉ Withdraw + Reissue mới chỉnh được".

### F. Audit & Dashboard (TC-27 → TC-28)

**TC-27 — Lifecycle event bất biến**
- Sửa row có timestamp.
- Expected: VR-02-06 throw.

**TC-28 — Dashboard 6 KPI**
- GET dashboard_kpis.
- Expected: 6 KPI compute đúng + delta.

---

## 3. Acceptance

- ≥ 95% PASS để release.
- 0 Critical, ≤ 2 High open.
- Audit trail 100%.

*End of UAT Script v0.1.0 — IMM-02*
