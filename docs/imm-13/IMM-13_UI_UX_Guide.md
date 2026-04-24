# IMM-13 — Thanh lý Thiết bị Y tế (UI/UX Guide)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-13 — UI/UX Guide |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. Routes

| Route | View Component | Mô tả |
|---|---|---|
| `/decommission` | `DecommissionListView.vue` | Danh sách phiếu thanh lý |
| `/decommission/create` | `DecommissionCreateView.vue` | Tạo phiếu mới |
| `/decommission/:name` | `DecommissionDetailView.vue` | Chi tiết + workflow actions |

---

## 2. DecommissionListView

### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ [IMM-13 · Thanh lý]   Danh sách Yêu cầu Thanh lý           │
│ Tổng XX phiếu                          [+ Tạo yêu cầu]     │
├─────────────────────────────────────────────────────────────┤
│ Stats Bar:                                                   │
│ [12 Đã thanh lý YTD] [3 Chờ phê duyệt] [250M Giá trị TL]   │
├─────────────────────────────────────────────────────────────┤
│ Filters: [Search] [Status ▼] [Năm ▼]                        │
├─────────────────────────────────────────────────────────────┤
│ Mã phiếu  │ Thiết bị   │ Lý do    │ Phương án │ Trạng thái │
│ DR-26-... │ MRI-001    │ End of.. │ Scrap     │ [badge]    │
└─────────────────────────────────────────────────────────────┘
```

### Status Badge Colors
| Status | Tailwind | Mô tả |
|---|---|---|
| Draft | `bg-slate-100 text-slate-600` | Xám nhạt |
| Technical Review | `bg-blue-100 text-blue-700` | Xanh dương |
| Financial Valuation | `bg-violet-100 text-violet-700` | Tím |
| Pending Approval | `bg-amber-100 text-amber-700` | Vàng cam |
| Board Approved | `bg-emerald-100 text-emerald-700` | Xanh lá |
| Execution | `bg-red-100 text-red-700` | Đỏ — đang thực thi |
| Completed | `bg-slate-200 text-slate-500` | Xám — hoàn tất |
| Rejected | `bg-red-200 text-red-800` | Đỏ đậm |

---

## 3. DecommissionCreateView

### Form Sections

**Section 1: Thiết bị**
- `asset`: searchable Link → hiển thị chip với status hiện tại của asset
- `decommission_reason`: Select dropdown
- `reason_details`: Textarea
- `condition_at_decommission`: Radio group (Poor / Non-functional / Partially Functional / Functional but Obsolete)

**Section 2: Thông tin Tài chính**
- `last_service_date`: Date picker
- `total_maintenance_cost`: Currency input
- `current_book_value`: Currency input
- `estimated_disposal_value`: Currency input

**Section 3: Phương án Thanh lý**
- `disposal_method`: Select
- `transfer_destination`: Text (conditional show khi disposal_method = "Transfer to Facility")

**Section 4: Tuân thủ**
- `biological_hazard`: Toggle → nếu bật, hiện `bio_hazard_clearance` textarea
- `data_destruction_required`: Toggle → nếu bật, hiện checkbox `data_destruction_confirmed`
- `regulatory_clearance_required`: Toggle → nếu bật, hiện file upload `regulatory_clearance_doc`

**Nút hành động:**
- `[Huỷ]` → navigate `/decommission`
- `[Lưu nháp]` → POST create_decommission_request (Draft)
- `[Tạo & Gửi đánh giá]` → create + submit_for_technical_review

---

## 4. DecommissionDetailView

### Layout 3 Tab

```
[Chi tiết phiếu] [Checklist] [Lịch sử vòng đời]
```

**Tab 1 — Chi tiết phiếu:**
- Info card: asset, reason, condition, disposal method
- Theo workflow state, hiện section tương ứng:
  - Technical Review: form reviewer + notes + [Hoàn thành] / [Từ chối]
  - Financial Valuation: form finance reviewer + values + [Hoàn thành định giá]
  - Pending Approval: form approver + notes + [Phê duyệt] / [Từ chối]
  - Board Approved: [Bắt đầu thực thi] button
  - Execution: execution form + [Submit để hoàn tất]

**Tab 2 — Checklist:**
- Bảng checklist items với checkbox completed, notes

**Tab 3 — Lịch sử:**
- Timeline vertical list của lifecycle_events

### Action Buttons per State

| State | Buttons |
|---|---|
| Draft | [Gửi đánh giá KT] |
| Technical Review | [Hoàn thành đánh giá] [Từ chối] |
| Financial Valuation | [Hoàn thành định giá] |
| Pending Approval | [Phê duyệt] [Từ chối] |
| Board Approved | [Bắt đầu thực thi] |
| Execution | [Submit hoàn tất] |
| Completed | (read only) [Xem lưu trữ →] link to IMM-14 |
| Rejected | (read only) |

---

## 5. Icons sử dụng (Lucide Vue Next)

| Ngữ cảnh | Icon |
|---|---|
| Header page | `Trash2` |
| Status Completed | `CheckCircle` |
| Status Rejected | `XCircle` |
| Status Execution | `Zap` |
| Bio hazard | `AlertTriangle` |
| Data destruction | `ShieldOff` |
| Regulatory | `FileCheck` |
| Checklist | `ClipboardList` |
| Timeline | `History` |
| Archive link | `Archive` |

---

## 6. Responsive

- Desktop: 3-column grid cho form sections
- Tablet: 2-column
- Mobile: single column, sticky action bar ở bottom

---

*End of UI/UX Guide v1.0.0 — IMM-13*
