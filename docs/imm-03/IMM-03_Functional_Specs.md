# IMM-03 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Đánh giá nhà cung cấp và quyết định mua sắm |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |

---

## 1. Phạm vi

IMM-03 quản trị toàn bộ chuỗi từ **Vendor management** đến **Purchase Order issuance**:

- Vendor Profile (extension Supplier ERPNext): chứng chỉ pháp lý, ISO, năng lực, banking, banking, đại diện.
- Vendor Evaluation: chấm điểm đa tiêu chí cho từng Tech Spec đã Lock (IMM-02).
- AVL (Approved Vendor List): cấp phép, gia hạn, đình chỉ vendor cho từng device_category.
- Procurement Decision: chọn phương án mua sắm hợp pháp + chốt vendor + giá + nguồn vốn.
- Mint Purchase Order trong ERPNext core sau Award.
- Hậu kiểm: Supplier Audit định kỳ + Vendor Scorecard tổng hợp KPI.

Out of scope:
- Hệ thống đấu thầu E-bidding (chỉ tích hợp upload kết quả).
- Quản lý hợp đồng full text (chỉ link Contract Doc, không soạn HĐ trong AssetCore).
- Thanh toán (do TCKT/ERPNext Payment xử lý).

---

## 2. Actors

> Frappe Role: xem `Module_Overview §7` và `WAVE2_ALIGNMENT.md §6`.

| Tổ chức | Frappe Role | Vai trò |
|---|---|---|
| ĐT-HĐ-NCC Officer | `IMM Procurement Officer` (Wave 2 mới) | Quản lý vendor (AC Supplier), chạy evaluation, lập decision |
| KH-TC Officer | `IMM Planning Officer` (Wave 2 mới) | Chấm Commercial |
| HTM Engineer | `IMM HTM Engineer` (Wave 2 mới) | Chấm Technical |
| TCKT Officer | `IMM Finance Officer` (Wave 2 mới) | Chấm Financial; ghi Contract Signed |
| QA Risk Team | `IMM Risk Officer` (Wave 2 mới) | Chấm Compliance; chạy Supplier Audit |
| PTP Khối 1 | `IMM Department Head` (Wave 1) | Submit, điều phối, trình BGĐ |
| VP Block1 / BGĐ | `IMM Board Approver` (Wave 2 mới) | Approve Decision; ký AVL; sign-off non-AVL |
| CMMS Admin | `IMM System Admin` (Wave 1) | Cấu hình master, override |

---

## 3. User Stories

### 3.1 Vendor Profile & AVL

**US-03-001:** *Là ĐT-HĐ-NCC Officer, tôi muốn tạo Vendor Profile mở rộng từ Supplier ERPNext.*

```
Given Supplier "Vinamed JSC" tồn tại trong ERPNext
When tôi tạo Vendor Profile và link supplier="Vinamed JSC"
And đính kèm chứng chỉ ISO 9001, ĐKLH BYT, GSP với expiry_date
Then Vendor Profile lưu, Supplier.imm_vendor_profile mirror set
```

**US-03-010:** *Là VP Block1, tôi muốn ký AVL cho vendor cho 1+ device_category với hiệu lực 1–3 năm.*

```
Given Vendor Profile đầy đủ chứng chỉ
When PTP Khối 1 tạo AVL Entry với category="Imaging", validity_years=2
And VP Block1 click "Approve"
Then AVL Entry workflow Approved, hiệu lực valid_from..valid_to set
And Supplier.imm_avl_status = "Approved", imm_avl_categories thêm "Imaging"
```

**US-03-011:** *Khi AVL hết hạn, hệ thống auto-Expired và cảnh báo.*

```
Given AVL Entry valid_to = 2026-04-29
When scheduler chạy ngày 2026-04-30
Then status đổi Expired, supplier.imm_avl_status update
And email cảnh báo gửi 60d/30d trước hết hạn
```

### 3.2 Vendor Evaluation

**US-03-020:** *Khi IMM-02 lock spec, tôi muốn Vendor Evaluation tự động seed.*

```
Given event imm02_spec_locked nhận với TS-26-00045
When listener IMM-03 chạy
Then VE-26-00120 tạo với criteria default + spec_ref=TS-26-00045
And state=Draft
```

**US-03-021:** *Là ĐT-HĐ-NCC Officer, tôi muốn add candidate và check AVL.*

```
Given Evaluation VE-26-00120
When tôi add vendor "Hamilton VN" — không có AVL cho Imaging
Then warning hiển thị "Vendor non-AVL — cần sign-off VP Block1"
And VR-02 chỉ throw khi cố Submit không có sign-off
```

**US-03-022:** *Tôi muốn nhập quotation (giá, payment terms, delivery) cho từng vendor.*

```
Given Evaluation Draft
When tôi click "Open RFQ" → state Open RFQ
And tôi nhập quotation 3 vendor: 2.0B / 1.9B / 1.4B
And quotation_validity 60d
Then state Quotation Received, G02 pass
```

**US-03-023:** *Là HTM Engineer + KH-TC + QA Risk, tôi muốn chấm điểm criteria theo từng nhóm.*

5 nhóm tiêu chí default + trọng số:

| Group | Default Weight |
|---|---|
| Technical (spec match, brand, support tier) | 35% |
| Commercial (price, payment terms, delivery) | 25% |
| Financial (financial health, banking) | 10% |
| Support (training, warranty, parts availability) | 15% |
| Compliance (ISO, ĐKLH, NC history, audit) | 15% |

```
Given Quotation Received
When 3 nhóm chấm xong: Technical(htm), Commercial(khtc), Compliance(qa)
Then weighted_score per candidate auto compute
And recommended_vendor = top weighted
```

### 3.3 Procurement Decision

**US-03-030:** *Là ĐT-HĐ-NCC Officer, tôi muốn chọn phương án mua sắm hợp pháp.*

```
Given budget allocated 2.5B, hàng nhập khẩu, 1 nhà cung cấp đáp ứng
When tôi chọn procurement_method="Chỉ định thầu"
Then G04 check: hợp pháp khi giá ≤ ngưỡng + có giải trình; OK
Khi chọn "Chào hàng cạnh tranh"
Then yêu cầu ≥ 3 báo giá (kế thừa từ Evaluation)
Khi chọn "Đấu thầu rộng rãi"
Then yêu cầu ≥ 3 candidate + giá > 1B (vd luật quy định)
```

**US-03-031:** *Tôi muốn tham chiếu Evaluation để Award Recommended.*

```
Given Decision PD-26-00045
When tôi link evaluation_ref=VE-26-00120 và select winner_candidate=Hamilton VN
And nhập awarded_price=2.0B (≤ 105% envelope)
Then state Award Recommended; G01 + G03 pass
And nếu awarded > 105% envelope → warning + cần justification
```

**US-03-032:** *Là VP Block1, tôi Approve để mint PO.*

```
Given Decision Pending Approval, G05 pass (contract_doc + funding_source + board_approver)
When VP Block1 click "Awarded"
Then docstatus=1, state Awarded
And ERPNext Purchase Order tạo với imm_procurement_decision link
And Procurement Plan Line.status = Awarded
And event "imm03_decision_awarded" publish realtime → IMM-04 prep listener
```

**US-03-033:** *Sau khi Awarded, tôi update PO Issued + Contract Signed.*

```
When ĐT-HĐ-NCC Officer set "PO Issued" với PO ERPNext name
And TCKT Officer set "Contract Signed" với contract_no, signed_date
Then substate update; lifecycle event ghi
```

### 3.4 Vendor Scorecard & Audit

**US-03-040:** *Là KH-TC Officer, tôi muốn xem Scorecard vendor cập nhật quý.*

KPI Scorecard chiều:

| Dimension | Source | Weight |
|---|---|---|
| Delivery on-time | IMM-04 commissioning | 20% |
| Quality (NC rate) | IMM-04/IMM-10 | 25% |
| After-sales response | IMM-09 repair | 20% |
| Spare fill rate | IMM-15 | 15% |
| Compliance (audit, recall) | IMM-10 | 20% |

```
When scheduler quarterly chạy
Then Scorecard VS-2026-Q2-Hamilton tạo, kpi_rows + overall_score auto compute
And Supplier.imm_overall_score update
```

**US-03-041:** *Là QA Risk Team, tôi muốn chạy Supplier Audit định kỳ và ghi findings + CAPA.*

```
Given Vendor "Drager VN" đến hạn audit (>12 tháng)
When scheduler tạo SA-26-00012 task
And QA Risk Team thực hiện audit, nhập findings + CAPA
Then SA submit; vendor.imm_last_audit_date update
And nếu finding mức Major → trigger Suspended AVL
```

---

## 4. Functional Requirements

| FR-ID | Mô tả | Ưu tiên |
|---|---|---|
| FR-03-01 | Vendor Profile extension Supplier với chứng chỉ + bank + đại diện | Must |
| FR-03-02 | AVL Entry per category với validity 1–3 năm | Must |
| FR-03-03 | Auto-seed Vendor Evaluation từ event `imm02_spec_locked` | Must |
| FR-03-04 | Add candidate có check AVL (warning) + sign-off non-AVL | Must |
| FR-03-05 | RFQ → Quotation Received với validity check | Must |
| FR-03-06 | 5-group criteria chấm điểm có trọng số chỉnh được | Must |
| FR-03-07 | Recommended vendor auto-compute (weighted_score) | Must |
| FR-03-08 | Procurement Decision với 5 phương án mua sắm | Must |
| FR-03-09 | Validate phương án hợp pháp theo giá trị + loại (G04) | Must |
| FR-03-10 | Mint ERPNext PO khi Awarded; link bidirectional | Must |
| FR-03-11 | Cập nhật Plan Line status = Awarded | Must |
| FR-03-12 | Workflow Eval (5 state) + Decision (9 state) + AVL (4 state) | Must |
| FR-03-13 | Audit trail bất biến | Must |
| FR-03-14 | Vendor Scorecard quarterly từ feedback IMM-04/09/15/10 | Must |
| FR-03-15 | Supplier Audit periodic (12 tháng default) | Must |
| FR-03-16 | AVL expiry auto + cảnh báo 60/30 ngày | Must |
| FR-03-17 | Dashboard 7 KPI | Must |
| FR-03-18 | Export Decision → PDF (cho hồ sơ thầu) | Should |

---

## 5. Non-Functional

| NFR-ID | Yêu cầu | Mục tiêu |
|---|---|---|
| NFR-03-01 | Performance load Vendor Profile list 5000 | < 2s |
| NFR-03-02 | Mint PO < 3s | Must |
| NFR-03-03 | Audit retention | ≥ 10 năm |
| NFR-03-04 | i18n VN 100% | Must |
| NFR-03-05 | Permission permlevel cho Award price + funding (KH-TC + TCKT + PTP Khối 1 + VP Block1) | Must |
| NFR-03-06 | Vendor Scorecard idempotent re-run | Must |

---

## 6. QMS Mapping

| Yêu cầu | Nguồn | Đáp ứng |
|---|---|---|
| Purchasing process | ISO 13485 §7.4 | Vendor Eval + AVL + Audit |
| Supplier evaluation & re-evaluation | ISO 13485 §7.4.1 | Scorecard + Audit |
| Đấu thầu hợp pháp | Luật Đấu thầu 22/2023 | G04 method check |
| AVL | NĐ 98 §32, ISO 13485 | AVL Entry workflow |
| Audit trail | ISO 13485 §4.2.5 | Decision Lifecycle Event |
| Recall / FSCA tracking | NĐ 98 + WHO HTM Annex | Compliance dimension scorecard |

---

## 7. Out of Scope (V1)

- Tích hợp E-bidding hệ thống đấu thầu nhà nước (chỉ upload kết quả).
- Quản lý hợp đồng đầy đủ (link Contract Doc).
- Auto crawl giá thị trường (manual).

---

## 8. Definition of Done

- [ ] 6 DocType + 7 child schema
- [ ] 3 Workflow JSON deploy
- [ ] 7 VR + 5 Gate test
- [ ] 18 API endpoint
- [ ] 4 scheduler job
- [ ] PO mint + back-link bidirectional
- [ ] Frontend list + detail + create cho Vendor Profile, Evaluation, Decision, AVL
- [ ] Vendor Scorecard quarterly chạy được
- [ ] UAT ≥ 95% PASS

*End of Functional Specs v0.1.0 — IMM-03*
