# IMM-03 — UI/UX Guide

| Module | IMM-03 — Đánh Giá Nhà Cung Cấp & Quyết Định Mua Sắm |
|---|---|
| Ngày tạo | 2026-04-22 |

---

## 1. Màn hình: Danh sách Technical Specification (TSListView)

**Route:** `/planning/technical-specs`

**Layout:** Stats bar + Filter row + Table

**Stats bar (3 tiles):**
- Tổng TS năm nay
- Đang xem xét (Under Review)
- Đã phê duyệt (Approved)

**Bộ lọc:** Status (dropdown) · Năm · Regulatory Class

**Table columns:** Mã TS · Tên thiết bị · Phân loại NĐ98 · Kế hoạch mua sắm · Trạng thái · Ngày tạo

**Status badges:**
- Draft: gray
- Under Review: blue
- Approved: green
- Revised: orange

**Actions:** Nút "Tạo TS mới" (requiredRoles: ROLES_PLANNING_MANAGE)

---

## 2. Màn hình: Tạo Technical Specification (TSCreateView)

**Route:** `/planning/technical-specs/new`

**Pattern nguồn:** `CommissioningCreateView.vue` (multi-section form)

**Form sections:**

**Section 1 — Liên kết kế hoạch:**
- Kế hoạch mua sắm (SmartSelect → Procurement Plan, filter: status=Budget Locked)
- Dòng kế hoạch (SmartSelect → Procurement Plan Item, filter theo PP đã chọn)
- Model thiết bị (LinkSearch → IMM Device Model, optional)
- Tên thiết bị (auto-fill từ PP Item, editable)

**Section 2 — Yêu cầu kỹ thuật:**
- Yêu cầu kỹ thuật & hiệu suất (Text Editor, rich text, required)
- Tiêu chuẩn an toàn (Text, required)
- Phân loại NĐ98 (Select: Class A/B/C/D, required, hiển thị mô tả khi hover)
- Phân loại MDD (Select: I/II/III, optional)

**Section 3 — Điều khoản:**
- Phụ kiện đi kèm
- Điều khoản bảo hành
- Thời gian giao hàng (tuần)
- Yêu cầu lắp đặt
- Yêu cầu đào tạo

**Actions:** Lưu Nháp | Gửi Xem Xét

---

## 3. Màn hình: Chi tiết Technical Specification (TSDetailView)

**Route:** `/planning/technical-specs/:id`

**Pattern nguồn:** `CommissioningDetailView.vue`

**Layout:** Header (status badge + actions) + Info cards + Sections

**Header actions (theo trạng thái):**
- Draft: Gửi Xem Xét (WorkflowActions)
- Under Review: Phê duyệt | Yêu cầu chỉnh sửa (chỉ Technical Reviewer)
- Approved: readonly

**Info cards:**
- LinkInfoCard → Procurement Plan
- LinkInfoCard → PP Item (tên thiết bị, số lượng, ngân sách)
- LinkInfoCard → IMM Device Model (nếu có)

**Audit trail:** LifecycleEventTimeline (lifecycle_events table)

---

## 4. Màn hình: Chi tiết Vendor Evaluation (VEDetailView)

**Route:** `/planning/vendor-evaluations/:id`

**Pattern nguồn:** `CommissioningDetailView.vue` + `BaselineTestTable.vue` (pattern)

**Layout:** Header + Info + VendorScoringTable + Result section

**Header actions (PATCH-04 — 2-step approval):**
- Draft: Bắt đầu đánh giá
- In Progress: Thêm vendor | Duyệt kỹ thuật (chỉ IMM Technical Reviewer)
- Tech Reviewed: Duyệt tài chính + Chốt vendor (chỉ IMM Finance Officer)
- Approved: readonly

**VendorScoringTable (component mới):**

```text
Columns: Nhà cung cấp | Báo giá | KT(×0.4) | TC(×0.3) | NL(×0.2) | RR(×0.1) | Tổng | Band | ND98 | Chọn
Row mode: edit khi In Progress, readonly khi Approved
Footer: highlight row có total_score cao nhất
```

**Result section (hiện khi Approved):**
- Nhà cung cấp được chọn + score_band badge
- Căn cứ lựa chọn
- Thành viên hội đồng

**Info cards:**
- LinkInfoCard → Technical Specification
- LinkInfoCard → PP Item

---

## 5. Màn hình: Danh sách Purchase Order Request (PORListView)

**Route:** `/planning/purchase-order-requests`

**Stats bar (4 tiles):**
- Tổng POR năm nay
- Chờ phê duyệt (Under Review)
- Đã phát hành (Released)
- Tổng giá trị đã phát hành (currency)

**Bộ lọc:** Status · Nhà cung cấp · Năm · Cờ Director

**Table columns:** Mã POR · Thiết bị · Nhà cung cấp · Tổng giá trị · Director? · Trạng thái · Ngày phát hành

**Status badges:**
- Draft: gray
- Under Review: yellow
- Approved: blue
- Released: green
- Fulfilled: teal
- Cancelled: red

---

## 6. Màn hình: Tạo Purchase Order Request (PORCreateView)

**Route:** `/planning/purchase-order-requests/new`

**Form sections:**

**Section 1 — Liên kết:**
- Dòng kế hoạch (SmartSelect → PP Item, filter: status=PO Raised/Ordered)
- Đặc tả kỹ thuật (auto-fill từ PP Item nếu có TS, editable)
- Phiếu đánh giá NCC (SmartSelect → VE, filter: status=Approved)

**Section 2 — Nhà cung cấp & Hàng hóa:**
- Nhà cung cấp (SmartSelect → AC Supplier, auto-fill từ VE.recommended_vendor)
- Tên thiết bị (auto-fill, editable)
- Số lượng (Int)
- Đơn giá (Currency)
- **Tổng giá trị** (readonly, hiện ngay khi nhập qty × price)
- `PORApprovalBadge` — hiện "⚠ Cần Giám đốc ký" nếu total > 500M

**Section 3 — Điều khoản:**
- Điều khoản giao hàng
- Điều khoản thanh toán
- Ngày giao hàng dự kiến
- Bảo hành (tháng)
- Lý do miễn trừ (waiver — chỉ hiện khi vendor ≠ recommended)

**Actions:** Lưu Nháp | Gửi Phê Duyệt

---

## 7. Màn hình: Chi tiết Purchase Order Request (PORDetailView)

**Route:** `/planning/purchase-order-requests/:id`

**Header:**
- Status badge lớn
- `PORApprovalBadge` (nếu requires_director_approval = 1)
- WorkflowActions theo trạng thái + role:
  - Under Review + Finance Officer/Ops Manager: Phê duyệt (nếu ≤500M)
  - Under Review + Dept Head: Phê duyệt (nếu >500M)
  - Approved + Ops Manager: Phát hành POR
  - Released + Storekeeper: Xác nhận giao hàng

**Info cards:**
- LinkInfoCard → Vendor Evaluation (điểm số vendor được chọn)
- LinkInfoCard → Technical Specification
- LinkInfoCard → Procurement Plan / PP Item

**Audit trail:** LifecycleEventTimeline

---

## 8. Sidebar Navigation Group (Planning)

```text
Kế hoạch Mua sắm
  ├── Tổng quan KH         → /planning/dashboard     icon: chart
  ├── Đánh giá nhu cầu     → /planning/needs-assessments
  ├── Kế hoạch mua sắm     → /planning/procurement-plans
  ├── Đặc tả kỹ thuật      → /planning/technical-specs
  ├── Đánh giá NCC         → /planning/vendor-evaluations
  └── Yêu cầu mua sắm      → /planning/purchase-order-requests
```

---

## 9. Status Badge Color Map (bổ sung vào StatusBadge.vue)

```typescript
// Append vào status color config trong StatusBadge.vue:
const planningStatusColors: Record<string, string> = {
  // Technical Specification
  'Revised':       'bg-orange-100 text-orange-700',
  // Vendor Evaluation
  'In Progress':   'bg-indigo-100 text-indigo-700',
  'Tech Reviewed': 'bg-cyan-100 text-cyan-700',
  // Purchase Order Request
  'Released':      'bg-green-100 text-green-800',
  'Fulfilled':     'bg-teal-100 text-teal-700',
  // Procurement Plan
  'Budget Locked': 'bg-purple-100 text-purple-700',
  // Needs Assessment
  'Planned':       'bg-purple-100 text-purple-700',
  // PP Item
  'PO Raised':     'bg-yellow-100 text-yellow-700',
  'Ordered':       'bg-blue-100 text-blue-700',
  'Delivered':     'bg-teal-100 text-teal-700',
}
```
