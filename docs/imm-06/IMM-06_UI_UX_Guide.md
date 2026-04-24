# IMM-06 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — Bàn giao & Đào tạo |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. Routes

| Path | Name | Component | Mô tả |
|---|---|---|---|
| `/handover` | `HandoverList` | `HandoverListView.vue` | Danh sách phiếu bàn giao |
| `/handover/create` | `HandoverCreate` | `HandoverCreateView.vue` | Tạo phiếu bàn giao |
| `/handover/:name` | `HandoverDetail` | `HandoverDetailView.vue` | Chi tiết + training sessions |

---

## 2. HandoverListView.vue

### Layout
- Header: "Danh sách Bàn giao & Đào tạo" + button "Tạo phiếu mới"
- Stats row: tổng Pending, Handed Over tháng, đang Training
- Filter row: Status, Dept, Asset
- Table: Name | Asset | Khoa | Ngày BG | Loại | Trạng thái | Cập nhật
- Pagination

### Status Badges
| Status | Color |
|---|---|
| Draft | gray |
| Training Scheduled | blue |
| Training Completed | teal |
| Handover Pending | amber |
| Handed Over | green |
| Cancelled | red |

---

## 3. HandoverCreateView.vue

### Form sections

**Section 1 — Commissioning**
- `commissioning_ref`: Link to Asset Commissioning (search by name)
- `asset`: auto-fill (read-only) khi chọn commissioning
- Alert banner nếu commissioning chưa Clinical Release

**Section 2 — Thông tin bàn giao**
- `clinical_dept`: Select (Link AC Department)
- `handover_date`: Date picker
- `received_by`: User select
- `handover_type`: Radio (Full / Conditional / Temporary)
- `conditions_if_conditional`: Text area (hiện khi Conditional/Temporary)

**Section 3 — Ghi chú**
- `handover_notes`: Rich text editor

**Actions**
- "Lưu nháp" → POST create_handover_record
- "Lên lịch đào tạo" → redirect sang HandoverDetailView tab Training

---

## 4. HandoverDetailView.vue

### Tabs
1. **Thông tin bàn giao** — fields readonly sau Draft
2. **Đào tạo** — list Training Sessions + button "Lên lịch"
3. **Lịch sử vòng đời** — timeline Asset Lifecycle Events

### Workflow Action Buttons (state-based)

| State hiện tại | Buttons hiển thị |
|---|---|
| Draft | "Lên lịch đào tạo" |
| Training Scheduled | "Xác nhận hoàn thành đào tạo" / "Huỷ lịch" |
| Training Completed | "Gửi bàn giao" |
| Handover Pending | "Ký nhận bàn giao" (Dept Head only) / "Yêu cầu đào tạo thêm" |
| Handed Over | (read-only, badge success) |
| Cancelled | (read-only, badge danger) |

### Training Session Card
```
[TS-26-04-00001]
Loại: Vận hành | Ngày: 20/04/2026 | Trainer: Nguyễn A
Trạng thái: Completed | Đạt: 5/5 học viên
[Xem chi tiết]
```

### Training Session Modal (Lên lịch)
- `training_type`: Select
- `trainer`: User select
- `training_date`: Date
- `duration_hours`: Number
- `trainees`: Dynamic table (add/remove rows)
- Button "Lưu lịch"

### Complete Training Modal
- List trainee rows: Tên | Điểm | Đạt/Không
- "Lưu kết quả"

---

## 5. State-based UI changes

| State | Form editable | Buttons |
|---|---|---|
| Draft | Tất cả fields | Save, Schedule Training |
| Training Scheduled | Chỉ handover_notes | Complete Training, Cancel |
| Training Completed | Read-only | Send for Handover |
| Handover Pending | Read-only | Confirm Handover (Dept Head), Request More Training |
| Handed Over | Read-only | — |

---

## 6. Key UX Notes

- Khi chọn commissioning_ref, auto-fill asset và hiển thị asset name rõ ràng
- Badge trạng thái luôn hiển thị ở góc trên phải header
- Lifecycle events timeline ở tab riêng, sắp xếp descending
- Training session list hiển thị progress bar "X/Y học viên đạt"

*End of UI/UX Guide v1.0.0 — IMM-06*
