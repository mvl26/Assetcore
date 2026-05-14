# IMM-02 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-02 — Thông số kỹ thuật và phân tích thị trường |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |

---

## 1. Phạm vi

Module IMM-02 phục vụ giai đoạn **Specification & Market Analysis** trong WHO HTM Procurement Lifecycle. Nội dung:

- Soạn Tech Spec cho thiết bị y tế dự kiến mua (kế thừa từ Procurement Plan Line — IMM-01).
- Khảo sát & benchmark mô hình thị trường: tối thiểu 3 ứng viên, có spec match %, giá tham chiếu, hỗ trợ kỹ thuật, AVL status.
- Đánh giá tương thích hạ tầng: điện, khí y tế, mạng, không gian, HVAC, HIS/PACS/LIS interface.
- Đánh giá lock-in risk: proprietary protocol, sole-source consumable, software DRM, license tie, parts dependency.
- Phê duyệt và **Lock spec** trước khi mở vendor evaluation IMM-03.

Out of scope:
- Đánh giá nhà cung cấp cụ thể, đấu thầu, ký HĐ → IMM-03.
- Soạn HSMT (E-bidding) hoàn chỉnh — IMM-02 cung cấp output kỹ thuật, biểu mẫu HSMT do hệ thống đấu thầu/E-bidding xử lý.

---

## 2. Actors

> Frappe Role: xem `Module_Overview §7` và `WAVE2_ALIGNMENT.md §6`.

| Tổ chức | Frappe Role | Vai trò |
|---|---|---|
| HTM Engineer | `IMM HTM Engineer` (Wave 2 mới) | Soạn Tech Spec, requirements |
| HTM Lead | `IMM HTM Engineer` (lead subset) | Review requirements, sign-off Reviewing |
| KH-TC Officer | `IMM Planning Officer` (Wave 2 mới) | Soạn Market Benchmark |
| QA Risk Team | `IMM Risk Officer` (Wave 2 mới) | Lock-in Risk Assessment + Infra Compat |
| CNTT | `IMM System Admin` (Wave 1) | Infra Compat (Network/HIS/PACS) |
| PTP Khối 1 | `IMM Department Head` (Wave 1) | Trình duyệt, điều phối |
| VP Block1 / BGĐ | `IMM Board Approver` (Wave 2 mới) | Lock / Withdraw spec |
| Vendor Engineer (consultative) | — | Cung cấp datasheet (read-only attach via session khách hoặc share) |
| CMMS Admin | `IMM System Admin` (Wave 1) | Cấu hình master |

---

## 3. User Stories

### 3.1 Khởi tạo Tech Spec

**US-02-001:** *Là HTM Engineer, tôi muốn tạo Tech Spec từ Procurement Plan Line để không phải nhập lại thông tin model & qty.*

```
Given Procurement Plan PP-26-001 có plan_item NR-26-04-00012 (Máy thở)
When tôi click "Generate Tech Spec Drafts" trên Plan
Then Tech Spec TS-26-00045 được tạo với device_model_ref và quantity copy từ NR
And nếu Device Model có spec_template_ref → requirements được seed sẵn
And state = Draft, link tech_spec_ref được set lại trên NR
```

### 3.2 Soạn Requirements

**US-02-010:** *Là HTM Engineer, tôi muốn nhập tiêu chí kỹ thuật theo bảng — mandatory/optional, value/range, test_method.*

```
Given Tech Spec ở Draft
When tôi thêm requirement {parameter: "Tidal Volume", value_or_range: "20–2000 mL", mandatory: true, test_method: "Bench test theo IEC 60601-2-12"}
And tôi thêm tổng cộng ≥ 8 mandatory requirement
And mọi mandatory requirement đều có test_method
Then click "Gửi rà soát" pass G01
And state = Reviewing
```

**US-02-011 (negative):** *Khi requirement mandatory thiếu test_method, hệ thống chặn G01.*

### 3.3 Market Benchmark

**US-02-020:** *Là KH-TC Officer, tôi muốn nhập 3+ candidate so sánh trên thị trường.*

```
Given Tech Spec ở Reviewing
When tôi nhập Market Benchmark với candidates:
  - Hamilton C6  (spec_match_pct=92, price=2.1B, support=Tier1)
  - Dräger V500  (spec_match_pct=88, price=1.9B, support=Tier1)
  - Mindray SV600 (spec_match_pct=85, price=1.4B, support=Tier2)
Then weighted_recommendation auto-compute
And click "Hoàn tất benchmark" pass G02
```

### 3.4 Infra Compatibility

**US-02-030:** *Là QA Risk Team / CNTT, tôi muốn đánh giá 6 mục hạ tầng để biết bệnh viện có cần upgrade.*

Mục: Electrical, Medical Gas, Network/IT, HIS/PACS Interface, HVAC, Space/Layout.

```
Given Tech Spec ở Benchmarked
When tôi điền 6/6 mục với status (Compatible / Need Upgrade / N/A) + remark
Then G03 pass
And state = Risk Assessed
And nếu có "Need Upgrade", auto tạo task IMM-04 prep checklist
```

### 3.5 Lock-in Risk

**US-02-040:** *Là QA Risk Team, tôi muốn chấm 5 chiều lock-in để chặn spec proprietary không có lý do.*

Chiều: Protocol Standard (HL7/DICOM/IHE), Consumable Source, Software License, Parts Source, Service Tooling.

```
Given Tech Spec ở Risk Assessed
When tôi chấm 5/5 chiều, weighted lock_in_score = 3.2
And ngưỡng config = 2.5
Then G04 fail nếu không có "mitigation_plan" được phê duyệt
And user phải nhập mitigation và đính kèm chứng cứ trước Lock
```

### 3.6 Lock & Output

**US-02-050:** *Là VP Block1, tôi muốn Lock spec để mở giai đoạn vendor IMM-03.*

```
Given Tech Spec Pending Approval, G04 pass
When VP Block1 Lock
Then docstatus=1, state=Locked
And event "imm02_spec_locked" publish realtime
And IMM-03 nhận trigger tạo Vendor Evaluation request kèm tech_spec_ref
And Procurement Plan Line.status = "In Procurement"
```

### 3.7 Re-issue

**US-02-060:** *Khi spec đã Lock cần chỉnh, tôi muốn Withdraw + Reissue (versioning) thay vì sửa trực tiếp.*

```
Given Tech Spec Locked
When tôi click "Rút spec" (Withdraw) với reason
Then state Withdrawn (docstatus=1)
And tôi click "Reissue" → tạo TS-26-00046 với version=2.0, parent_spec=TS-26-00045
```

---

## 4. Functional Requirements

| FR-ID | Mô tả | Ưu tiên |
|---|---|---|
| FR-02-01 | Tạo Tech Spec từ Procurement Plan Line (1-click batch) | Must |
| FR-02-02 | Pre-fill requirements từ Device Model.spec_template_ref | Must |
| FR-02-03 | Requirement editor inline (parameter, value/range, mandatory, test_method, weight, evidence) | Must |
| FR-02-04 | Đính kèm tài liệu input (datasheet vendor, HSMT excerpt) | Must |
| FR-02-05 | Market Benchmark candidate so sánh ≥ 3 ứng viên | Must |
| FR-02-06 | Spec match % auto-compute theo mandatory pass / total mandatory | Must |
| FR-02-07 | Infra Compat 6 mục với status + remark + auto handoff IMM-04 prep | Must |
| FR-02-08 | Lock-in Risk Assessment 5 chiều với mitigation plan | Must |
| FR-02-09 | Workflow 7 state với role-based transition | Must |
| FR-02-10 | Audit trail bất biến | Must |
| FR-02-11 | Withdraw + Reissue (versioning) cho spec Locked | Must |
| FR-02-12 | Locked spec → trigger IMM-03 vendor eval seed | Must |
| FR-02-13 | Dashboard 6 KPI + lookup spec template re-use rate | Must |
| FR-02-14 | Cảnh báo benchmark stale (> 6 tháng) | Should |
| FR-02-15 | Export Tech Spec → PDF (HSMT-ready Annex) | Should |
| FR-02-16 | Compare to baseline (IMM-04 commissioning data) | Should |

---

## 5. Non-Functional

| NFR-ID | Yêu cầu | Mục tiêu |
|---|---|---|
| NFR-02-01 | Performance load list 1000 spec | < 2s |
| NFR-02-02 | Performance lock spec | < 2s |
| NFR-02-03 | Audit retention | ≥ 10 năm |
| NFR-02-04 | i18n VN 100% | Must |
| NFR-02-05 | Spec template versioning theo Frappe Version | Must |
| NFR-02-06 | Permission permlevel cho lock-in score (chỉ QA Risk + VP Block1) | Must |

---

## 6. QMS Mapping

| Yêu cầu | Nguồn | Đáp ứng |
|---|---|---|
| Design input | ISO 13485 §7.3.3 | Tech Spec Requirement table |
| Design verification | ISO 13485 §7.3.6 | test_method field bắt buộc |
| Health Technology Assessment | WHO HTA 2nd ed. | Market Benchmark + Infra Compat + Lock-in Risk |
| Procurement specification | WHO Procurement Guide | Tech Spec workflow |
| HSMT mô tả tính năng kỹ thuật | Luật Đấu thầu 22/2023 | Tech Spec output PDF |
| Audit trail | ISO 13485 §4.2.5 | Tech Spec Lifecycle Event |

---

## 7. Out of Scope (V1)

- Đấu thầu E-bidding tích hợp.
- Soạn HSMT đầy đủ (chỉ output Annex kỹ thuật).
- Auto vendor crawl (Market Benchmark vẫn nhập tay với template).

---

## 8. Definition of Done

- [ ] 3 DocType + 6 child schema match TD
- [ ] Workflow 7 state + 9 transition fixture
- [ ] 6 VR + 4 Gate test pass
- [ ] 14 API endpoint hoạt động
- [ ] 3 scheduler job
- [ ] Frontend list + detail + create cho 3 DocType
- [ ] Withdraw + Reissue versioning
- [ ] UAT ≥ 95% PASS
- [ ] Audit trail 100%

*End of Functional Specs v0.1.0 — IMM-02*
