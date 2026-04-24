# IMM-02 — UAT Script

## TC-02-001: Tạo kế hoạch và thêm items
| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | create_procurement_plan(plan_year=2027, approved_budget=2B) | status=Draft |
| 2 | add_item với total_cost = 500M | allocated_budget = 500M, remaining = 1.5B |
| 3 | Thêm item thứ 2 với total_cost = 800M | allocated = 1.3B, remaining = 700M |
| 4 | Kiểm tra remaining_budget | = 700,000,000 |

## TC-02-002: VR-02-01 Vượt ngân sách
| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Có plan với approved_budget=1B và allocated=800M | remaining=200M |
| 2 | Thêm item với total_cost=500M | frappe.throw VR-02-01 |

## TC-02-003: Flow đầy đủ đến Budget Locked
| Bước | Hành động | Kết quả mong đợi |
|---|---|---|
| 1 | Tạo plan với items hợp lệ | Draft |
| 2 | submit_for_review | Under Review |
| 3 | approve_plan | Approved |
| 4 | lock_budget | Budget Locked |
| 5 | Thử add_item khi Budget Locked | Error: INVALID_STATE |

## Tổng kết
| Test Case | Pass | Fail |
|---|---|---|
| TC-02-001 | | |
| TC-02-002 | | |
| TC-02-003 | | |
