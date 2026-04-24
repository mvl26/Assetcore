# IMM-01 — UI/UX Guide

| Module | IMM-01 — Đánh Giá Nhu Cầu & Dự Toán |
|---|---|
| Ngày tạo | 2026-04-21 |

---

## 1. Màn hình: Danh sách (NeedsAssessmentListView)

**Route:** `/needs-assessment`

**Layout:** Stats bar + Filter row + Table

**Stats bar (4 tiles):**
- Tổng yêu cầu năm nay
- Đang chờ duyệt (Submitted + Under Review)
- Đã phê duyệt
- Tổng ngân sách được duyệt

**Bộ lọc:** Status (dropdown) · Khoa (dropdown) · Năm · Priority

**Table columns:** Mã phiếu · Khoa · Loại thiết bị · Ưu tiên · Dự toán · Ngân sách duyệt · Trạng thái · Ngày lập

**Status badges:**
- Draft: gray
- Submitted: yellow
- Under Review: blue
- Approved: green
- Rejected: red
- Planned: purple

---

## 2. Màn hình: Tạo mới (NeedsAssessmentCreateView)

**Route:** `/needs-assessment/create`

**Form sections:**

**Section 1 — Thông tin yêu cầu:**
- Khoa yêu cầu (dropdown, required)
- Người đề xuất (auto = current user)
- Ngày lập (date picker, default today)
- Loại thiết bị (text input, required)
- Model thiết bị (optional lookup)
- Số lượng (number, min 1)
- Ưu tiên (radio buttons: Critical/High/Medium/Low với màu)

**Section 2 — Chi tiết kỹ thuật:**
- Lý do y tế (rich text editor, min 50 ký tự, counter hiển thị)
- Tuổi thiết bị hiện tại
- Tần suất hỏng hóc

**Section 3 — Tài chính:**
- Dự toán (VND, required, số tiền + chữ viết tắt)

**Actions:** Lưu Nháp | Nộp Để Xét Duyệt

---

## 3. Màn hình: Chi tiết (NeedsAssessmentDetailView)

**Route:** `/needs-assessment/:name`

**Layout:** Header (mã + status badge) + Content + Action sidebar

**Action buttons theo trạng thái:**

| Status | Actions hiển thị |
|---|---|
| Draft | Nộp xét duyệt · Hủy |
| Submitted | Bắt đầu xem xét (HTM Manager) |
| Under Review | Phê duyệt · Từ chối |
| Approved | Đưa vào kế hoạch |
| Rejected | Xem lý do từ chối |

**Tab: Thông tin chung** — all fields read-only

**Tab: Đánh giá** — htmreview_notes, finance_notes, approved_budget (editable by reviewers)

**Tab: Lịch sử** — Lifecycle events timeline (timestamp, actor, from→to, notes)

---

## 4. Luồng UX tổng quát

```
Clinical Staff → Create (Draft)
                    ↓ Dept Head
              Submit for Review (Submitted)
                    ↓ HTM Manager
              Start Review (Under Review)
                    ↓ Finance Director
         ┌── Approve (Approved) ──► Add to PP (Planned)
         └── Reject (Rejected) ──► Notify Dept
```

---

## 5. Color palette (light theme)

| Yếu tố | Màu |
|---|---|
| Background | #f4f6fa |
| Card | #ffffff |
| Border | #e2e8f0 |
| Text primary | #0f172a |
| Text secondary | #64748b |
| Priority Critical | #ef4444 (red-500) |
| Priority High | #f97316 (orange-500) |
| Priority Medium | #eab308 (yellow-500) |
| Priority Low | #64748b (slate-500) |
| Status Approved | #10b981 (green-500) |
| Status Rejected | #ef4444 (red-500) |
