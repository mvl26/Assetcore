# IMM-03 — UAT Script

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Đánh Giá Nhà Cung Cấp & Quyết Định Mua Sắm |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-22 |

---

## Test Data Setup

```
Preconditions (phải có từ Wave 1 + IMM-01/02):
  - PP-26-UAT-001 ở trạng thái "Budget Locked"
  - PP Item "Máy thở ICU × 2" (estimated_unit_cost=200M, total_cost=400M, status=PO Raised)
  - NA-26-UAT-001 linked về PP Item (requesting_dept="Hồi sức Tích cực", status=Approved)

Users:
  - ops_manager_01   / role: IMM Operations Manager
  - tech_reviewer_01 / role: IMM Technical Reviewer
  - finance_01       / role: IMM Finance Officer
  - dept_head_01     / role: IMM Department Head
  - storekeeper_01   / role: IMM Storekeeper

Suppliers:
  - ACC-SUP-001: "Công ty TNHH Thiết bị Y tế Phương Nam"
  - ACC-SUP-002: "Công ty CP Kỹ thuật Y sinh ABC"
  - ACC-SUP-003: "Công ty TNHH Medline Việt Nam"
```

---

## TC-03-001: Tạo Technical Specification thành công

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Login ops_manager_01 | Thành công |
| 2 | POST `create_technical_spec` với linked_plan_item=PP Item, regulatory_class="Class B", performance_requirements (>50 ký tự), safety_standards | response.success = true |
| 3 | Kiểm tra data.name | Khớp regex `^TS-\d{2}-\d{5}$` |
| 4 | Kiểm tra status | "Draft" |
| 5 | Kiểm tra lifecycle_events | 1 event: technical_spec_created, domain=imm_planning |

**Pass/Fail:** ___

---

## TC-03-002: VR-03-01 Block khi PP Item không hợp lệ

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | POST `create_technical_spec` với linked_plan_item trỏ tới PP Item status="Pending" | response.success = false |
| 2 | Kiểm tra error.code | "VALIDATION_ERROR" |
| 3 | Kiểm tra message | Chứa "VR-03-01" |

**Pass/Fail:** ___

---

## TC-03-003: VR-03-02 Block khi thiếu regulatory_class

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | POST `create_technical_spec` với regulatory_class="" | response.success = false |
| 2 | Kiểm tra message | Chứa "VR-03-02" |

**Pass/Fail:** ___

---

## TC-03-004: Technical Reviewer phê duyệt TS

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | ops_manager_01 gọi `submit_ts_for_review(TS-26-UAT-001)` | status → "Under Review" |
| 2 | Login tech_reviewer_01 | Thành công |
| 3 | Gọi `approve_technical_spec(name, review_notes)` | response.success = true |
| 4 | Kiểm tra status | "Approved" |
| 5 | Kiểm tra lifecycle_events | event: technical_spec_approved |

**Pass/Fail:** ___

---

## TC-03-005: Tạo Vendor Evaluation với 3 vendors + scoring tự động

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | ops_manager_01 tạo VE linked TS-26-UAT-001 | VE Draft |
| 2 | `add_vendor_to_evaluation` — ACC-SUP-001: tech=8.5, fin=7.0, profile=8.0, risk=9.0 | total_score = 8.05, band = "A (≥8)" |
| 3 | `add_vendor_to_evaluation` — ACC-SUP-002: tech=7.0, fin=8.0, profile=6.5, risk=7.5 | total_score = 7.25, band = "B (6–7.9)" |
| 4 | `add_vendor_to_evaluation` — ACC-SUP-003: tech=6.0, fin=6.5, profile=5.5, risk=8.0 | total_score = 6.35, band = "B (6–7.9)" |
| 5 | Kiểm tra UI VendorScoringTable | Row ACC-SUP-001 được highlight (điểm cao nhất) |

**Pass/Fail:** ___

---

## TC-03-006: VR-03-04 Block khi chỉ có 1 vendor

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Tạo VE mới với chỉ 1 vendor | Tạo thành công |
| 2 | Gọi `approve_vendor_evaluation` | response.success = false |
| 3 | Kiểm tra message | Chứa "VR-03-04" |

**Pass/Fail:** ___

---

## TC-03-007: VE 2-step approval — Tech Reviewer trước, Finance Officer sau (PATCH-04)

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | VE có 3 vendors (ACC-SUP-001 điểm cao nhất 8.05), status = In Progress | — |
| 2 | Login tech_reviewer_01, gọi `approve_ve_technical(VE-26-UAT-001, notes="Đạt KT")` | status → "Tech Reviewed" |
| 3 | Kiểm tra VE.tech_reviewed_by | Khớp tech_reviewer_01 |
| 4 | Login ops_manager_01 thử gọi `approve_ve_financial` (sai role) | PERMISSION_ERROR |
| 5 | Login finance_01, gọi `approve_ve_financial` với recommended_vendor=ACC-SUP-002, selection_justification="" | response.success = false, chứa "VR-03-05" |
| 6 | Gọi lại với selection_justification="Công ty ABC có kinh nghiệm hơn tại bệnh viện tuyến trên" | response.success = true, status → "Approved" |
| 7 | Kiểm tra VE.approved_by | Khớp finance_01 |

**Pass/Fail:** ___

---

## TC-03-008: Tạo POR và kiểm tra threshold Director

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | finance_01 tạo POR: vendor=ACC-SUP-001, qty=2, unit_price=210000000 | total_amount=420M, requires_director_approval=0 |
| 2 | UI hiện PORApprovalBadge? | Không hiện "Cần Giám đốc ký" |
| 3 | Thay unit_price=310000000, qty=2 | total_amount=620M, requires_director_approval=1 |
| 4 | UI | Hiện badge "⚠ Cần Giám đốc ký" |

**Pass/Fail:** ___

---

## TC-03-009: Phê duyệt, phát hành và xác nhận giao hàng POR ≤500M

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | POR-26-UAT-001 total_amount=420M ở Draft | — |
| 2 | finance_01 gọi `approve_por` | status → "Approved" |
| 3 | ops_manager_01 gọi `release_por` | status → "Released" |
| 4 | Kiểm tra PP Item linked | status = "Ordered" |
| 5 | Kiểm tra frappe background queue | job notify_imm04_readiness được enqueue |
| 6 | Kiểm tra lifecycle_events | event: por_released, domain=imm_planning |
| 7 | storekeeper_01 gọi `confirm_por_delivery(name, delivery_notes="Nhận đủ 2 máy")` | status → "Fulfilled" |
| 8 | Kiểm tra PP Item linked | status = "Delivered" |
| 9 | Kiểm tra lifecycle_events | event: por_fulfilled, domain=imm_planning |

**Pass/Fail:** ___

---

## TC-03-010: End-to-End Flow NA → PP → TS → VE → POR → IMM-04 notify

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Dùng NA-26-UAT-001 (Approved) → PP-26-UAT-001 (Budget Locked) | Precondition đã có |
| 2 | Tạo TS → approve | TS-26-UAT-001 Approved |
| 3 | Tạo VE với 2+ vendors → approve | VE-26-UAT-001 Approved |
| 4 | Tạo POR từ VE → approve → release | POR-26-UAT-001 Released |
| 5 | Kiểm tra PP Item | status = "Ordered" |
| 6 | Kiểm tra Notifications của storekeeper_01 | Nhận thông báo "Chuẩn bị tiếp nhận Máy thở ICU" |
| 7 | Kiểm tra Notifications của dept_head của khoa "Hồi sức Tích cực" | Nhận thông báo đặt hàng |
| 8 | Trace chain: POR → VE → TS → PP Item → NA-26-UAT-001 | Mỗi bước link hợp lệ, audit trail đầy đủ |

**Pass/Fail:** ___

---

## Checklist UAT Sign-off

| Hạng mục | Pass | Fail | Ghi chú |
|---|---|---|---|
| TC-03-001: Tạo TS thành công | | | |
| TC-03-002: VR-03-01 | | | |
| TC-03-003: VR-03-02 | | | |
| TC-03-004: Approve TS | | | |
| TC-03-005: VE scoring tự động | | | |
| TC-03-006: VR-03-04 | | | |
| TC-03-007: VE 2-step approval (PATCH-04) | | | |
| TC-03-008: Director threshold | | | |
| TC-03-009: POR release + delivery confirm (PATCH-05) | | | |
| TC-03-010: End-to-end | | | |

**UAT Approved by:** ___________________ **Ngày:** ___________
