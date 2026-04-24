# IMM-02 — UI/UX Guide

## Màn hình: Danh sách (ProcurementPlanListView)
**Route:** `/procurement-plan`

**Stats bar:** Năm hiện tại · Tổng ngân sách được duyệt · % đã phân bổ · Số items

**Table columns:** Mã kế hoạch · Năm · Ngân sách duyệt · Đã phân bổ · Còn lại · Trạng thái

**Status badges:** Draft(gray) · Under Review(yellow) · Approved(green) · Budget Locked(blue)

---

## Màn hình: Chi tiết (ProcurementPlanDetailView)
**Route:** `/procurement-plan/:name`

**Header:** Mã kế hoạch + Year badge + Status badge

**Progress bar:** allocated_budget / approved_budget (color: green < 80%, yellow 80-95%, red > 95%)

**Items table:** columns = Priority · Thiết bị · Model · SL · Đơn giá · Tổng · Quý · Trạng thái

**Actions per state:**
- Draft: Nộp xem xét
- Under Review: Phê duyệt
- Approved: Khóa ngân sách · Thêm item
- Budget Locked: Tạo PO (→ IMM-03)

---

## UX Flow
```
Create Plan → Add Items (from approved NAs) → Review → Approve → Lock → Raise POs (IMM-03)
```
