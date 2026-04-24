# IMM-02 — Functional Specifications

| Module | IMM-02 — Kế Hoạch Mua Sắm | Ngày tạo | 2026-04-21 |
|---|---|---|---|

---

## 1. Validation Rules

### VR-02-01: Ngân sách phân bổ không vượt ngân sách duyệt
```
SUM(items.total_cost) ≤ approved_budget
→ frappe.throw("VR-02-01: Tổng phân bổ vượt ngân sách được duyệt")
```

### VR-02-02: Không có item khi nộp
```
len(items) = 0 khi submit → block
→ frappe.throw("VR-02-02: Kế hoạch chưa có thiết bị nào")
```

### VR-02-03: Needs Assessment phải Approved
```
Nếu item.needs_assessment được fill → NA.status phải = "Approved"
→ frappe.throw("VR-02-03: Phiếu đánh giá nhu cầu chưa được phê duyệt")
```

---

## 2. Business Rules

| Rule | Mô tả |
|---|---|
| BR-02-01 | Mỗi năm chỉ có 1 Procurement Plan ở trạng thái Approved hoặc Budget Locked |
| BR-02-02 | Khi Budget Locked, không thể thêm/xóa item |
| BR-02-03 | Khi item status → PO Raised, tự động link POR từ IMM-03 |

---

## 3. User Stories (Gherkin)

### US-02-01: Tạo kế hoạch mua sắm

```gherkin
Scenario: HTM Manager tạo kế hoạch mua sắm năm 2027
  Given tôi có role "HTM Manager"
    And có ít nhất 3 Needs Assessment đã Approved trong năm 2027
  When tôi tạo Procurement Plan với plan_year=2027, approved_budget=2000000000
    And thêm items từ các NA đã duyệt
  Then plan được tạo với status "Draft"
    And remaining_budget = approved_budget - SUM(items.total_cost)
```

### US-02-02: VR-02-01 Block ngân sách vượt mức

```gherkin
Scenario: Block khi phân bổ vượt ngân sách
  Given Procurement Plan với approved_budget = 1,000,000,000
  When tôi thêm item với total_cost = 1,200,000,000
  Then frappe.throw với "VR-02-01"
```

### US-02-03: VP phê duyệt kế hoạch

```gherkin
Scenario: VP Block2 approve procurement plan
  Given plan ở "Under Review" với đầy đủ items
    And tôi có role "VP Block2" / "Workshop Head"
  When approve_plan(name, notes)
  Then status → "Approved"
    And lifecycle event "plan_approved" được ghi
```

### US-02-04: Khóa ngân sách để bắt đầu procurement

```gherkin
Scenario: Finance Director khóa ngân sách
  Given plan ở "Approved"
  When lock_budget(name)
  Then status → "Budget Locked"
    And các item không thể thêm/xóa
    And HTM Manager có thể bắt đầu tạo PO (IMM-03)
```

---

## 4. Non-Functional Requirements

| NFR | Yêu cầu |
|---|---|
| Tính toàn vẹn | remaining_budget được tính lại mỗi khi save |
| Audit | Mọi status change có Lifecycle Event |
| Quyền | Only HTM Manager trở lên mới được tạo/edit |
