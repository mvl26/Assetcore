# IMM-01 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh Giá Nhu Cầu & Dự Toán |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-21 |
| Trạng thái | Wave 2 — In Development |
| Chuẩn tham chiếu | WHO HTM 2025, NĐ 98/2021 |

---

## 1. Scope

### 1.1 In Scope

| # | Hạng mục |
|---|---|
| 1 | DocType `Needs Assessment` với workflow 5 states |
| 2 | 4 Validation Rules (VR-01-01 → VR-01-04) |
| 3 | 6 REST endpoints (imm01.py) |
| 4 | Auto-link sang IMM-02 khi approved |
| 5 | Dashboard KPIs (budget, approval rate, processing time) |
| 6 | Audit trail bất biến (Lifecycle Event) |

### 1.2 Out of Scope

| # | Hạng mục | Lý do defer |
|---|---|---|
| 1 | Email notification tự động | Cấu hình Frappe Email Engine riêng |
| 2 | Budget forecasting AI | Wave 3 |
| 3 | ERP budget integration | Phụ thuộc ERP Hospital |

---

## 2. Actors

| Actor | Role | Hành động chính |
|---|---|---|
| Clinical Staff | Requester | Tạo phiếu, điền thông tin |
| Department Head | Dept Approver | Xác nhận và nộp |
| HTM Manager | Technical Reviewer | Đánh giá kỹ thuật |
| Finance Director | Budget Approver | Xét duyệt ngân sách |
| CMMS Admin | System Admin | Hủy, override |

---

## 3. Validation Rules

### VR-01-01: Trùng yêu cầu trong năm

```
Nếu cùng requesting_dept + equipment_type trong cùng năm tài chính
AND status ∈ {Draft, Submitted, Under Review}
→ WARN: "Khoa đã có yêu cầu tương tự đang xử lý: {existing_name}"
(warning, không block)
```

### VR-01-02: Dự toán hợp lệ

```
estimated_budget phải > 0
estimated_budget phải ≤ 50,000,000,000 (50 tỷ VND — ceiling cho 1 phiếu)
→ frappe.throw("VR-01-02: Dự toán không hợp lệ")
```

### VR-01-03: Số lượng hợp lệ

```
quantity phải ≥ 1 và ≤ 100 (trên 100 phải tách phiếu)
→ frappe.throw("VR-01-03: Số lượng phải từ 1 đến 100")
```

### VR-01-04: Lý do y tế bắt buộc

```
clinical_justification phải ≥ 50 ký tự khi nộp (Submitted)
→ frappe.throw("VR-01-04: Lý do y tế phải chi tiết ít nhất 50 ký tự")
```

---

## 4. Business Rules

| Rule | Mô tả |
|---|---|
| BR-01-01 | Chỉ Department Head mới được submit (không phải Clinical Staff) |
| BR-01-02 | HTM Manager phải điền htmreview_notes trước khi approve |
| BR-01-03 | Finance Director phải điền approved_budget trước khi approve |
| BR-01-04 | Approved NA tự động notify HTM Manager để đưa vào IMM-02 |
| BR-01-05 | Rejected NA phải có lý do từ chối (reject_reason field) |

---

## 5. User Stories (Gherkin)

### US-01-01: Tạo phiếu đánh giá nhu cầu

```gherkin
Scenario: Clinical staff tạo phiếu đánh giá nhu cầu
  Given tôi có role "Clinical Staff" hoặc "Department Head"
    And tôi thuộc khoa "Hồi sức Tích cực"
  When tôi POST /api/method/assetcore.api.imm01.create_needs_assessment
    với {requesting_dept, equipment_type="Máy thở", quantity=2,
         estimated_budget=500000000, clinical_justification="...", priority="Critical"}
  Then response.success = true
    And data.name khớp regex "^NA-\d{2}-\d{2}-\d{5}$"
    And status = "Draft"
    And lifecycle event "needs_assessment_created" được ghi nhận
```

### US-01-02: VR-01-02 block dự toán không hợp lệ

```gherkin
Scenario: Block khi dự toán = 0
  Given tôi đang tạo phiếu đánh giá nhu cầu
  When estimated_budget = 0
  Then response.success = false
    And error.code = "VALIDATION_ERROR"
    And message chứa "VR-01-02: Dự toán không hợp lệ"
```

### US-01-03: Department Head nộp phiếu

```gherkin
Scenario: Nộp phiếu để HTM review
  Given phiếu NA-26-04-00001 ở trạng thái "Draft"
    And tôi có role "Department Head"
    And clinical_justification có đủ 50 ký tự
  When tôi gọi submit_for_review(name="NA-26-04-00001")
  Then status → "Submitted"
    And HTM Manager nhận notification
    And lifecycle event "submitted_for_review" được ghi
```

### US-01-04: HTM Manager từ chối

```gherkin
Scenario: Từ chối yêu cầu không hợp lệ về mặt kỹ thuật
  Given phiếu NA-26-04-00002 ở trạng thái "Under Review"
    And tôi có role "HTM Manager"
  When tôi gọi reject_needs_assessment(name, reason="Đã có thiết bị tương đương đang hoạt động")
  Then status → "Rejected"
    And reject_reason được lưu
    And Department Head nhận notification
    And lifecycle event "rejected" được ghi với reason
```

### US-01-05: Finance Director phê duyệt với ngân sách điều chỉnh

```gherkin
Scenario: Phê duyệt với ngân sách thấp hơn yêu cầu
  Given phiếu NA-26-04-00003 ở "Under Review"
    And HTM Manager đã điền htmreview_notes
    And tôi có role "Finance Director"
  When tôi gọi approve_needs_assessment(name, approved_budget=400000000, notes="Điều chỉnh theo khung giá BYT")
  Then status → "Approved"
    And approved_budget = 400000000 (≠ estimated_budget 500000000)
    And lifecycle event "approved" được ghi
    And IMM-02 Procurement Plan được notify để add item
```

---

## 6. Non-Functional Requirements

| NFR | Yêu cầu |
|---|---|
| Hiệu năng | List query ≤ 500ms với 10,000 records |
| Audit | Mọi status change phải có Lifecycle Event record |
| Quyền | Department Head chỉ thấy phiếu của khoa mình |
| Lưu trữ | Giữ record ≥ 5 năm (NĐ98) |
