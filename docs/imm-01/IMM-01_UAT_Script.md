# IMM-01 — UAT Script

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh Giá Nhu Cầu & Dự Toán |
| Phiên bản | 1.0.0 |
| Ngày tạo | 2026-04-21 |

---

## Test Data Setup

```
Dept: "Hồi sức Tích cực" (ICU)
Users:
  - clinical_staff_01 / role: HTM Technician
  - dept_head_icu / role: Workshop Head
  - htm_manager_01 / role: HTM Manager
  - finance_dir_01 / role: CMMS Admin (acting Finance)
  - admin_01 / role: CMMS Admin
```

---

## TC-01-001: Tạo phiếu thành công

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Login clinical_staff_01 | Thành công |
| 2 | POST create_needs_assessment với đủ dữ liệu hợp lệ | response.success = true |
| 3 | Kiểm tra data.name | Khớp regex NA-\d{2}-\d{2}-\d{5} |
| 4 | Kiểm tra status | "Draft" |
| 5 | Kiểm tra lifecycle_events | 1 event: needs_assessment_created |

**Pass/Fail:** ___

---

## TC-01-002: VR-01-02 Block dự toán = 0

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | POST create_needs_assessment với estimated_budget=0 | response.success = false |
| 2 | Kiểm tra error.code | "VALIDATION_ERROR" |
| 3 | Kiểm tra message | Chứa "VR-01-02" |

**Pass/Fail:** ___

---

## TC-01-003: VR-01-04 Lý do quá ngắn khi submit

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Tạo phiếu với clinical_justification = "Cần mua" (8 ký tự) | Tạo thành công (Draft) |
| 2 | Login dept_head_icu, gọi submit_for_review | response.success = false |
| 3 | message | Chứa "VR-01-04" |

**Pass/Fail:** ___

---

## TC-01-004: Flow đầy đủ Draft → Approved

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Tạo phiếu với đủ dữ liệu | status = Draft |
| 2 | dept_head_icu: submit_for_review | status = Submitted |
| 3 | htm_manager_01: start_review | status = Under Review |
| 4 | htm_manager_01: điền htmreview_notes | Lưu thành công |
| 5 | finance_dir_01: approve với approved_budget=450M | status = Approved |
| 6 | Kiểm tra lifecycle_events count | ≥ 5 events |
| 7 | Kiểm tra approved_budget | 450000000 |

**Pass/Fail:** ___

---

## TC-01-005: Từ chối và kiểm tra reason

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Tạo và submit phiếu mới | status = Submitted → Under Review |
| 2 | htm_manager_01: reject với reason="Thiết bị đã có" | status = Rejected |
| 3 | Kiểm tra reject_reason field | = "Thiết bị đã có" |
| 4 | Kiểm tra lifecycle event | event_type = "rejected" |

**Pass/Fail:** ___

---

## TC-01-006: Dashboard stats chính xác

| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Tạo 3 phiếu: 2 Approved, 1 Rejected | Done |
| 2 | GET get_dashboard_stats | response.success = true |
| 3 | data.approval_rate | > 0 |
| 4 | data.total_approved_budget | > 0 |

**Pass/Fail:** ___

---

## Tổng kết UAT

| Test Case | Pass | Fail | Blocked |
|---|---|---|---|
| TC-01-001 | | | |
| TC-01-002 | | | |
| TC-01-003 | | | |
| TC-01-004 | | | |
| TC-01-005 | | | |
| TC-01-006 | | | |
| **Tổng** | | | |
