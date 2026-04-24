# IMM-03 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Đánh Giá Nhà Cung Cấp & Quyết Định Mua Sắm |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-22 |
| Trạng thái | Wave 2 — In Development |
| Chuẩn tham chiếu | NĐ 98/2021 · TT 68/2022/TT-BTC · WHO HTM 2025 |

---

## 1. Scope

### 1.1 In Scope

| # | Hạng mục |
|---|---|
| 1 | DocType `Technical Specification` — workflow 4 states |
| 2 | DocType `Vendor Evaluation` + child `Vendor Evaluation Item` — weighted scoring, 2-step approval |
| 3 | DocType `Purchase Order Request` — workflow 6 states, director threshold |
| 4 | 7 Validation Rules (VR-03-01 → VR-03-07) |
| 5 | 6 Business Rules (BR-03-01 → BR-03-06) |
| 6 | 8 REST endpoints (imm03.py) |
| 7 | Auto-link POR → PP Item → NA (traceability chain) |
| 8 | Background job: `notify_imm04_readiness` khi POR Released |
| 9 | Audit trail bất biến (Asset Lifecycle Event, domain=imm_planning) |

### 1.2 Out of Scope

| # | Hạng mục | Lý do defer |
|---|---|---|
| 1 | Tích hợp hệ thống đấu thầu điện tử (eProcurement) | Phase 2 |
| 2 | Phân tích giá lịch sử và benchmark tự động | Wave 3 / AI module |
| 3 | Hợp đồng mua sắm sau POR | Thuộc module IMM-04 onboarding |

---

## 2. Actors

| Actor | Role | Hành động chính |
|---|---|---|
| HTM Manager | IMM Operations Manager | Tạo TS, VE, POR; phát hành POR |
| Technical Reviewer | IMM Technical Reviewer | Phê duyệt TS, xác nhận VE kỹ thuật |
| Finance Officer | IMM Finance Officer | Xác nhận VE tài chính, phê duyệt POR ≤500M |
| Department Head | IMM Department Head | Phê duyệt POR >500M |
| Storekeeper | IMM Storekeeper | Xác nhận giao hàng (Fulfilled) |

---

## 3. Validation Rules

### VR-03-01: TS phải link về Procurement Plan Item
```
Technical Specification.linked_plan_item phải được điền
AND PP Item.status phải ∈ {PO Raised}
→ frappe.throw("VR-03-01: Đặc tả kỹ thuật phải liên kết với dòng kế hoạch mua sắm hợp lệ")
```

### VR-03-02: Regulatory class bắt buộc
```
Technical Specification.regulatory_class phải ∈ {Class A, Class B, Class C, Class D}
→ frappe.throw("VR-03-02: Phân loại NĐ98 là bắt buộc")
```

### VR-03-03: TS phải có chữ ký Technical Reviewer trước khi Approved
```
Workflow transition Under Review → Approved
chỉ actor có role IMM Technical Reviewer mới được thực hiện
(enforce qua Frappe Workflow role permission)
```

### VR-03-04: Vendor Evaluation phải có tối thiểu 2 vendors
```
len(Vendor Evaluation.items) < 2 khi submit
→ frappe.throw("VR-03-04: Cần ít nhất 2 nhà cung cấp để đảm bảo tính cạnh tranh")
```

### VR-03-05: recommended_vendor phải là vendor điểm cao nhất hoặc có biên bản giải trình
```
IF recommended_vendor ≠ vendor có total_score cao nhất trong items
AND selection_justification IS NULL OR len(selection_justification) < 30
→ frappe.throw("VR-03-05: Cần biên bản giải trình khi không chọn nhà cung cấp điểm cao nhất")
```

### VR-03-06: POR total_amount không vượt quá 110% ngân sách PP Item
```
POR.total_amount > PP_item.total_cost × 1.10
→ frappe.throw("VR-03-06: Giá trị POR vượt 10% so với ngân sách kế hoạch. Cần phê duyệt bổ sung.")
```

### VR-03-07: POR vendor phải là recommended_vendor của VE (hoặc có waiver)
```
POR.vendor ≠ VE.recommended_vendor AND POR.waiver_reason IS NULL
→ frappe.throw("VR-03-07: Nhà cung cấp trong POR không khớp với kết quả đánh giá. Cần waiver.")
```

---

## 4. Business Rules

| Mã | Mô tả |
|---|---|
| BR-03-01 | POR.total_amount > 500,000,000 VND → `requires_director_approval = 1` tự động |
| BR-03-02 | POR.total_amount ≤ 500,000,000 VND → Ops Manager / Finance Officer đủ thẩm quyền |
| BR-03-03 | Chỉ phát hành POR sau khi PP.status = Budget Locked |
| BR-03-04 | Mỗi PP Item chỉ có 1 POR ở trạng thái Released tại 1 thời điểm |
| BR-03-05 | Khi POR Released → PP Item.status tự động = Ordered (sync) |
| BR-03-06 | Khi POR Released → `frappe.enqueue(notify_imm04_readiness)` async |
| BR-03-07 | Khi POR Fulfilled → PP Item.status tự động = Delivered (sync, PATCH-05) |
| BR-03-08 | VE approval: bước 1 = Technical Reviewer; bước 2 = Finance Officer (AND, không phải OR, PATCH-04) |

---

## 5. User Stories (Gherkin)

### US-03-01: Tạo đặc tả kỹ thuật từ PP Item

```gherkin
Scenario: HTM Manager tạo TS cho máy thở
  Given PP-26-00001 ở trạng thái "Budget Locked"
    And PP Item "Máy thở ICU × 2" có status "PO Raised"
    And tôi có role "IMM Operations Manager"
  When tôi POST create_technical_spec với {linked_plan_item, regulatory_class="Class B",
       performance_requirements="...", safety_standards="IEC 60601-1"}
  Then response.success = true
    And data.name khớp regex "^TS-\d{2}-\d{5}$"
    And status = "Draft"
    And lifecycle event "technical_spec_created" được ghi với domain "imm_planning"
```

### US-03-02: VR-03-02 Block khi thiếu regulatory_class

```gherkin
Scenario: Block khi không điền phân loại NĐ98
  Given tôi đang tạo Technical Specification
  When regulatory_class = "" (trống)
  Then response.success = false
    And error.code = "VALIDATION_ERROR"
    And message chứa "VR-03-02"
```

### US-03-03: Đánh giá vendor với 3 nhà cung cấp

```gherkin
Scenario: HTM Manager tạo VE với 3 vendors
  Given TS-26-00001 ở trạng thái "Approved"
    And tôi có role "IMM Operations Manager"
  When tôi tạo Vendor Evaluation với evaluation_method="RFQ"
    And thêm 3 Vendor Evaluation Items với điểm số đầy đủ
  Then mỗi item.total_score được tính tự động (tech×0.4+fin×0.3+profile×0.2+risk×0.1)
    And item.score_band hiện A/B/C/D tương ứng
```

### US-03-04: VR-03-04 Block khi chỉ có 1 vendor

```gherkin
Scenario: Block VE chỉ có 1 vendor
  Given Vendor Evaluation Draft với 1 item
  When tôi submit VE
  Then response.success = false
    And message chứa "VR-03-04"
```

### US-03-05: Tạo POR và phát hành

```gherkin
Scenario: Finance Officer tạo và phát hành POR ≤500M
  Given VE-26-00001 ở "Approved" với recommended_vendor = "Công ty ABC"
    And tôi có role "IMM Finance Officer"
  When tôi tạo POR với {vendor="Công ty ABC", quantity=2, unit_price=200000000}
  Then total_amount = 400000000
    And requires_director_approval = 0
    And workflow chỉ cần Ops Manager / Finance Officer approve (không cần Director)
  When approve_por(name)
    And release_por(name)
  Then POR.status = "Released"
    And PP Item.status = "Ordered"
    And frappe.enqueue notify_imm04_readiness được gọi với por_name
```

### US-03-06-a: Storekeeper xác nhận giao hàng (PATCH-05)

```gherkin
Scenario: Storekeeper xác nhận đã nhận hàng
  Given POR-26-00001 ở trạng thái "Released"
    And tôi có role "IMM Storekeeper"
  When tôi POST confirm_por_delivery với {name, delivery_notes="Đã nhận đủ 2 máy"}
  Then POR.status = "Fulfilled"
    And PP Item.status = "Delivered"
    And lifecycle event "por_fulfilled" được ghi
```

### US-03-07: POR >500M yêu cầu Director ký

```gherkin
Scenario: POR lớn cần Director
  Given POR.total_amount = 600000000 (600M VND)
  When validate POR
  Then requires_director_approval = 1
    And workflow hiện thêm bước "Phê duyệt Director" trong Approval Flow
  When Finance Officer cố approve trực tiếp
  Then response chứa lỗi "Cần phê duyệt từ Giám đốc / Trưởng phòng"
```

---

## 6. Non-Functional Requirements

| NFR | Yêu cầu |
|---|---|
| Audit | Mọi status transition ghi `Asset Lifecycle Event` bất biến |
| Traceability | POR → VE → TS → PP Item → NA phải truy nguyên được |
| Hiệu năng | List query ≤ 500ms với 5,000 records |
| Phân quyền | Clinical User không có quyền xem POR/VE/TS |
| Lưu trữ | Records ≥ 5 năm (NĐ98/2021) |
| Background job | `notify_imm04_readiness` timeout ≤ 300s, queue = "default" |
