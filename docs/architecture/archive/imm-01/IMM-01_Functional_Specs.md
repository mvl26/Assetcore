# IMM-01 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |

---

## 1. Phạm vi

Module IMM-01 chuẩn hóa quy trình **Needs Assessment & Budget Estimation** cho thiết bị y tế tại bệnh viện theo WHO HTM lifecycle. Module bao quát:

- Quản trị đề xuất nhu cầu (mới / thay thế / nâng cấp / bổ sung).
- Chấm điểm ưu tiên đầu tư đa tiêu chí (multi-criteria).
- Lập dự toán toàn vòng đời (CAPEX + OPEX 5 năm).
- Quản trị ngoại lệ (exception adjustment) khi vượt budget envelope.
- Dự báo nhu cầu trung-dài hạn (3–5 năm).

Out of scope (xử lý ở module khác):
- Soạn thông số kỹ thuật chi tiết → IMM-02.
- Đánh giá nhà cung cấp, đấu thầu, ký HĐ → IMM-03.
- Lắp đặt nghiệm thu → IMM-04.

---

## 2. Actors & Stakeholders

> Frappe Role tương ứng: xem `Module_Overview §7` và `WAVE2_ALIGNMENT.md §6`.

| Tổ chức | Frappe Role | Tương tác chính |
|---|---|---|
| Department User (KTV/ĐD trưởng khoa) | `IMM Clinical User` | Tạo Draft Needs Request, đính kèm clinical justification |
| Clinical Head (Trưởng khoa) | `IMM Clinical User` (head subset) | Submit Draft → Submitted |
| HTM Reviewer | `IMM HTM Engineer` (Wave 2 mới) | Review/Score clinical_impact + risk |
| KH-TC Officer | `IMM Planning Officer` (Wave 2 mới) | Chấm utilization/replacement/compliance/budget_fit; tạo Procurement Plan |
| TCKT Officer | `IMM Finance Officer` (Wave 2 mới) | Build Budget Estimate, xác nhận funding_source |
| PTP Khối 1 | `IMM Department Head` (Wave 1) | Workflow steward, trình BGĐ |
| VP Block1 / BGĐ | `IMM Board Approver` (Wave 2 mới) | Approve / Reject |
| CMMS Admin | `IMM System Admin` (Wave 1) | Cấu hình master, override |

---

## 3. User Stories

### 3.1 Khởi tạo Needs Request

**US-01-001:** *Là một Trưởng khoa, tôi muốn tạo phiếu đề xuất thiết bị mới để khoa có thiết bị đáp ứng nhu cầu khám chữa bệnh.*

Acceptance Criteria (Gherkin):
```
Given tôi là Clinical Head của khoa "ICU"
When tôi mở form Needs Request và chọn request_type="New", device_model_ref, clinical_justification (≥ 200 ký tự)
And tôi nhập requesting_department="ICU", quantity=2, target_year=2027
And tôi nhấn "Gửi đề xuất"
Then phiếu chuyển từ Draft → Submitted
And lifecycle_event "Submitted" được ghi với actor=tôi
And email thông báo gửi PTP Khối 1 + KH-TC Officer
```

**US-01-002:** *Là KTV khoa, khi báo hỏng nặng thiết bị X, tôi muốn tạo Needs Request thay thế và link sang Decommission Plan.*

Acceptance Criteria:
```
Given Asset "ABG-001" có IMM-13 Decommission Plan trạng thái "Pending"
When tôi tạo Needs Request type="Replacement" với replacement_for_asset="ABG-001"
Then VR-02 pass và phiếu lưu thành công
Given Asset không có Decommission Plan
When tôi cố gắng Submit
Then VR-02 throw "Replacement request yêu cầu Decommission Plan IMM-13 ở trạng thái Pending/Approved"
```

### 3.2 Chấm điểm ưu tiên

**US-01-010:** *Là HTM Reviewer, tôi muốn chấm điểm 6 tiêu chí cho phiếu để xếp loại P1–P4.*

Tiêu chí và trọng số mặc định:

| # | Criterion | Weight | Scale | Hướng dẫn |
|---|---|---|---|---|
| 1 | clinical_impact | 25% | 1–5 | 5 = thiết bị cứu sinh, 1 = tiện nghi |
| 2 | risk_to_patient_or_staff | 20% | 1–5 | 5 = không có gây nguy hiểm cao |
| 3 | utilization_gap | 15% | 1–5 | 5 = downtime > 20% / utilization > 90% |
| 4 | replacement_signal | 15% | 1–5 | 5 = MTBF < 50% benchmark, EOL, recalled |
| 5 | compliance_gap | 15% | 1–5 | 5 = không tuân thủ NĐ98 / WHO HTM |
| 6 | budget_fit | 10% | 1–5 | 5 = trong envelope; 1 = vượt 50%+ |

`weighted_score = Σ (score_i × weight_i)`. Phân loại: P1 ≥ 4.0; P2 3.0–3.99; P3 2.0–2.99; P4 < 2.0.

Acceptance:
```
Given phiếu ở Reviewing
When tôi điền 6 scoring rows
Then weighted_score được auto-compute và hiển thị priority class
And không thể chuyển Prioritized nếu thiếu 1/6 tiêu chí (G02)
```

### 3.3 Dự toán

**US-01-020:** *Là TCKT Officer, tôi muốn lập dự toán CAPEX + OPEX 5 năm để có view tổng chi phí sở hữu.*

Budget lines bắt buộc:

| Section | Lines |
|---|---|
| CAPEX | Device price, installation, training, infrastructure upgrade, accessories |
| OPEX Year 1–5 | PM cost, calibration, spare parts forecast, consumable, software license, insurance |

Acceptance:
```
Given phiếu ở Prioritized
When tôi nhập budget_lines: 5 dòng CAPEX + 5×6 dòng OPEX
Then total_capex và total_opex_5y tự tính
And nếu thiếu OPEX year nào → G03 fail "Budget Estimate phải có cả CAPEX + OPEX 5 năm"
```

### 3.4 Phê duyệt

**US-01-030:** *Là VP Block1, tôi muốn duyệt/bác phiếu kèm lý do và funding_source.*

Acceptance:
```
Given phiếu ở Pending Approval
When tôi nhập board_approver="self", funding_source="NSNN" và nhấn "Approved"
Then phiếu chuyển Approved (docstatus=1)
And lifecycle_event "Approved" ghi với approver, funding_source, approval_date
And phiếu được gom vào Procurement Plan kỳ kế (nếu chưa có) hoặc append vào kế hoạch hiện hành
```

### 3.5 Procurement Plan & Demand Forecast

**US-01-040:** *Là KH-TC Officer, tôi muốn xem Procurement Plan tổng hợp các Needs Request đã duyệt theo quý/năm.*

Acceptance:
```
When tôi mở Procurement Plan PP-26-001
Then thấy danh sách plan_items với priority_rank giảm dần weighted_score
And tổng allocated_budget không vượt envelope đã set
And có thể "Generate IMM-02 Spec Drafts" tạo loạt phiếu Tech Spec rỗng cho từng plan_item
```

**US-01-041:** *Là KH-TC Officer, tôi muốn xem Demand Forecast 5 năm để lập kế hoạch chiến lược.*

Acceptance:
```
When tôi mở Demand Forecast DF-2027 (kỳ next)
Then thấy device_category × year matrix với projected_qty + projected_capex
And driver breakdown (replacement, utilization growth, service expansion)
And accuracy đối chiếu với actual của kỳ trước được hiển thị
```

---

## 4. Functional Requirements

| FR-ID | Mô tả | Ưu tiên |
|---|---|---|
| FR-01-01 | Hệ thống cho phép tạo Needs Request 4 type: New / Replacement / Upgrade / Add-on | Must |
| FR-01-02 | Bắt buộc clinical_justification ≥ 200 ký tự | Must |
| FR-01-03 | Hỗ trợ đính kèm tài liệu (clinical evidence, utilization report) | Must |
| FR-01-04 | Auto-fetch utilization data từ IMM-07 khi chọn replacement_for_asset | Must |
| FR-01-05 | Auto-fetch decommission status từ IMM-13 | Must |
| FR-01-06 | 6-criteria priority scoring với weighted_score auto-compute | Must |
| FR-01-07 | Cho phép admin chỉnh trọng số scoring qua master config | Should |
| FR-01-08 | Budget Estimate dạng matrix CAPEX + OPEX 5 năm | Must |
| FR-01-09 | Cảnh báo (soft) khi tổng dự toán > 80% envelope quý | Must |
| FR-01-10 | Cảnh báo (hard block) khi vượt 100% envelope nếu cấu hình `enforce_envelope=1` | Should |
| FR-01-11 | Workflow 8 states với role-based transition | Must |
| FR-01-12 | Audit trail bất biến cho mọi state change | Must |
| FR-01-13 | Procurement Plan gom Needs Request `Approved` theo quý/năm | Must |
| FR-01-14 | Generate IMM-02 Tech Spec drafts từ Procurement Plan | Must |
| FR-01-15 | Demand Forecast monthly auto-generated với driver breakdown | Should |
| FR-01-16 | Dashboard KPI 6 chỉ số (mục 10 Module Overview) | Must |
| FR-01-17 | Email notification cho 7 sự kiện workflow | Must |
| FR-01-18 | Export Procurement Plan ra PDF + Excel | Should |

---

## 5. Non-Functional Requirements

| NFR-ID | Yêu cầu | Mục tiêu |
|---|---|---|
| NFR-01-01 | Performance — load list 1000 Needs Request | < 2s |
| NFR-01-02 | Performance — submit phiếu | < 1.5s |
| NFR-01-03 | Audit retention | ≥ 10 năm theo NĐ98 |
| NFR-01-04 | i18n — toàn bộ label/error message tiếng Việt | 100% |
| NFR-01-05 | Permission — bám role thực, không dùng System Manager cho nghiệp vụ | RULE-F05 |
| NFR-01-06 | Audit trail bất biến — cấm sửa lifecycle_events row đã có | VR-06 |
| NFR-01-07 | API authentication — Frappe session + API key | Must |
| NFR-01-08 | Backup hồ sơ đính kèm | Daily, 30-day retention |

---

## 6. QMS Mapping

| Yêu cầu | Nguồn | Cách đáp ứng |
|---|---|---|
| Planning of product realization | ISO 13485 §7.1 | Workflow + Gates |
| Needs assessment | WHO HTM 2025 | DocType structure + 6-criteria scoring |
| Total Cost of Ownership | WHO HTM Annex 4 | Budget Estimate CAPEX + OPEX 5y |
| Kế hoạch đầu tư trang thiết bị y tế | NĐ 98/2021 §32 | Procurement Plan workflow |
| Dự báo nhu cầu phục vụ đấu thầu tập trung | Luật Đấu thầu 22/2023 | Demand Forecast |
| Audit trail | ISO 13485 §4.2.5 | `Needs Lifecycle Event` immutable |
| Document control | QMS-A | Đính kèm + version qua Frappe File |

---

## 7. Out of Scope (V1)

- Tích hợp BHYT real-time (nguồn vốn xã hội hóa, tài trợ chỉ ghi nhận tay).
- Tự động chạy đấu thầu — IMM-03.
- Phân tích HTA chuyên sâu (chỉ tham chiếu, không build lại HTA framework).
- Tích hợp ERP TCKT real-time — V2.

---

## 8. Acceptance Definition of Done

Module IMM-01 được coi là DONE khi:

- [ ] 5 DocType + 5 child table tạo được, schema match Technical Design
- [ ] Workflow 8 states, 10 transition deploy fixture
- [ ] 6 VR + 5 Gate được implement và unit test pass
- [ ] 14 API endpoint hoạt động, response theo `_ok/_err` pattern
- [ ] 3 scheduler job chạy được (overdue, monthly forecast, weekly envelope alert)
- [ ] Frontend list + detail + create cho 3 primary DocType
- [ ] Dashboard KPI 6 chỉ số hiển thị đúng
- [ ] UAT Script (32 TC) đạt ≥ 95% PASS
- [ ] Audit trail 100% các state change được ghi nhận
- [ ] Tài liệu Module Overview, Functional Specs, Technical Design, API Interface, UI/UX, UAT đầy đủ

*End of Functional Specs v0.1.0 — IMM-01*
