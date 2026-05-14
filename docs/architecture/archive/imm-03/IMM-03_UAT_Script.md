# IMM-03 — UAT Script

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Eval & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |
| Tổng test case | 36 |

---

## 1. Pre-requisites

- AssetCore deployed; IMM-01, IMM-02 đã có Plan/Spec mẫu (1 Tech Spec Locked).
- Master: `IMM Procurement Method Config` seed; `Vendor Eval Criterion` default 5 nhóm.
- ERPNext: Supplier "Vinamed JSC", "Hamilton Vietnam", "Mindray Vietnam", "Drager VN" đã tồn tại; Item `IMM-MDL-2024-0007` đã có.
- Test users: dt.hd.ncc, kh.tc, htm.engineer, tckt, qa.risk, ptp.k1, vp.block1, cmms.admin.

---

## 2. Test Cases

### A. Vendor Profile (TC-01 → TC-05)

**TC-01 — Tạo Vendor Profile link Supplier**
- Login `dt.hd.ncc`. Tạo profile VINAMED, link Supplier "Vinamed JSC", chứng chỉ ISO 9001.
- Expected: lưu thành công; Supplier.imm_vendor_profile mirror = VINAMED.

**TC-02 — Cert expiry status auto**
- Cert ISO 13485 expiry_date=today+25.
- Expected: status = "Expiring" (badge vàng).

**TC-03 — Cert Expired auto**
- Cert ĐKLH expiry_date=today-1.
- Expected: status = "Expired"; vendor flagged.

**TC-04 — Permission ĐT-HĐ-NCC chỉ create**
- Login `kh.tc` cố tạo Vendor Profile.
- Expected: PERM-DENY.

**TC-05 — Search vendor theo device_category**
- Filter "Imaging".
- Expected: trả VINAMED, HAMILTON-VN.

### B. AVL (TC-06 → TC-10)

**TC-06 — Create AVL Draft**
- VINAMED + category=Imaging + validity=2y, valid_from=2026-05-01.
- Expected: AVL-2026-00045 Draft, valid_to=2028-04-30 auto.

**TC-07 — Approve AVL bởi VP Block1**
- Login `vp.block1` Approve.
- Expected: status Approved; Supplier.imm_avl_status=Approved, imm_avl_categories cập nhật.

**TC-08 — AVL hết hạn auto Expired**
- AVL valid_to=today-1 → trigger scheduler.
- Expected: status Expired; email cảnh báo.

**TC-09 — Suspend AVL**
- QA Risk team Suspend với reason.
- Expected: status Suspended; cảnh báo Eval đang Open có vendor.

**TC-10 — Cảnh báo 60/30 ngày trước hết hạn**
- AVL valid_to=today+59.
- Expected: scheduler gửi cảnh báo 60d.

### C. Vendor Evaluation seed & RFQ (TC-11 → TC-16)

**TC-11 — Auto seed từ event imm02_spec_locked**
- Mock publish event với TS-26-00045.
- Expected: VE-26-00120 tạo Draft với criteria default 5 group.

**TC-12 — Add candidate trong AVL**
- Add VINAMED (Imaging Approved).
- Expected: in_avl=true, no warning.

**TC-13 — Add candidate non-AVL**
- Add HAMILTON-VN (Imaging Conditional).
- Expected: warning "Vendor non-AVL — cần sign-off VP Block1".

**TC-14 — VR-01 không đủ candidate cho Đấu thầu rộng rãi**
- Add 2 candidate, thử Submit.
- Expected: VR-03-01 throw cần ≥ 3.

**TC-15 — Open RFQ → Quotation Received**
- Submit 3 quotation hợp lệ.
- Expected: G02 pass, state Quotation Received.

**TC-16 — VR-03 quotation hết hạn**
- Quotation_validity = today-1.
- Expected: VR-03-03 throw khi cố Submit Eval.

### D. Score & Evaluated (TC-17 → TC-21)

**TC-17 — HTM chấm Technical**
- Login `htm.engineer` chấm 3 candidate, 4 criterion Technical.
- Expected: scores lưu; partial weighted không đầy đủ.

**TC-18 — KH-TC chấm Commercial**
- Login `kh.tc` chấm Commercial group.
- Expected: scores lưu.

**TC-19 — Compute weighted_score đủ 5 group**
- Đủ 5 group; weighting_scheme default {Tech 35, Comm 25, Fin 10, Sup 15, Comp 15}.
- Expected: weighted compute đúng; recommended_candidate=top.

**TC-20 — G01 thiếu group Compliance score**
- Submit Eval khi QA Risk chưa chấm.
- Expected: G01 fail.

**TC-21 — Eval Evaluated submit**
- Đủ 5 group + recommended set.
- Expected: docstatus=1, state Evaluated.

### E. Procurement Decision (TC-22 → TC-30)

**TC-22 — Tạo Decision từ Eval**
- create_decision với evaluation_ref=VE-26-00120, method=Đấu thầu rộng rãi.
- Expected: PD-26-00045 Draft.

**TC-23 — G04 method legality OK**
- Đấu thầu rộng rãi cho gói 6 tỷ + ≥ 3 quote.
- Expected: G04 pass, state Method Selected.

**TC-24 — G04 fail Chỉ định thầu vượt ngưỡng**
- Chỉ định thầu cho gói 200tr (ngưỡng config 50tr).
- Expected: G04 fail.

**TC-25 — VR-04 envelope > 105% warning**
- awarded_price=2.7B, allocated=2.5B → 108%.
- Expected: warning + cần justification.

**TC-26 — VR-05 winner non-AVL không có sign-off**
- winner=HAMILTON-VN (Conditional), không sign-off.
- Expected: VR-03-05 throw khi Awarded.

**TC-27 — Sign-off non-AVL pass**
- VP Block1 sign-off candidate non-AVL.
- Expected: VR-03-05 pass.

**TC-28 — VR-07 Spec đã có Decision Awarded**
- Tạo Decision thứ 2 cho TS-26-00045.
- Expected: VR-03-07 throw.

**TC-29 — G05 thiếu contract_doc**
- Trình BGĐ không attach contract.
- Expected: G05 fail.

**TC-30 — Award Decision → mint PO**
- Login `vp.block1` Award.
- Expected: docstatus=1, state Awarded; PO ERPNext tạo với imm_procurement_decision=PD-26-00045; lifecycle event "Awarded"; Plan Line.status=Awarded; event imm03_decision_awarded publish.

### F. PO bridge & Contract (TC-31 → TC-33)

**TC-31 — Tạo PO TBYT direct (không qua Decision)**
- Login `dt.hd.ncc` tạo PO direct với item TBYT, không có imm_procurement_decision.
- Expected: throw "PO TBYT phải đi qua IMM-03 Procurement Decision".

**TC-32 — Contract Signed substate**
- Login `tckt` set contract_no, signed_date.
- Expected: state Contract Signed; lifecycle event ghi.

**TC-33 — PO Issued substate**
- Login `dt.hd.ncc` set po_ref đã mint.
- Expected: state PO Issued.

### G. Audit & Scorecard (TC-34 → TC-36)

**TC-34 — Supplier Audit due**
- Vendor last_audit > 12 tháng → trigger scheduler.
- Expected: SA-26-00012 task tạo cho QA Risk.

**TC-35 — Audit Critical finding → Suspend AVL**
- Audit submit với 1 finding Critical.
- Expected: AVL của vendor đó set Suspended; email VP Block1.

**TC-36 — Vendor Scorecard quarterly**
- Trigger scheduler quarterly với data IMM-04/09/15/10.
- Expected: VS-2026-Q2-VINAMED tạo, kpi_rows compute, overall_score = weighted Σ; idempotent re-run không tạo duplicate.

---

## 3. Test Data

| Vendor | AVL | Cho TC |
|---|---|---|
| VINAMED | Imaging Approved | TC-12, TC-30 |
| HAMILTON-VN | Imaging Conditional | TC-13, TC-26, TC-27 |
| MINDRAY-VN | Imaging Approved | TC-15 |
| DRAGER-VN | Suspended | TC-09 |

---

## 4. Acceptance

- ≥ 95% PASS để release.
- 0 Critical, ≤ 2 High open.
- PO mint 100% thành công với decision hợp lệ.
- Audit trail 100%.

*End of UAT Script v0.1.0 — IMM-03*
