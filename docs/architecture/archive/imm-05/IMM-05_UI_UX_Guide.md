# IMM-05 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-05 — Asset Document Repository |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |

---

## 0. Tổng quan màn hình

| # | Trang | Frontend Route (Vue) | Frappe Desk URL | Component |
|---|---|---|---|---|
| 1 | Document List | `/imm05/documents` | `/app/asset-document` | `views/DocumentManagement.vue` |
| 2 | Document Detail | `/imm05/documents/:name` | `/app/asset-document/{name}` | `views/DocumentDetailView.vue` |
| 3 | Document Create | `/imm05/documents/new` | `/app/asset-document/new` | `views/DocumentCreateView.vue` |
| 4 | Asset Documents Tab | `/assets/:name/documents` | `/app/asset/{name}` (tab) | (embed in Asset detail) |
| 5 | Dashboard IMM-05 | `/imm05/dashboard` | `/app/imm05-dashboard` | TBD |
| 6 | Document Request Modal | (modal) | — | `components/imm05/DocumentRequestModal.vue` |
| 7 | Exempt Modal | (modal) | — | `components/imm05/ExemptModal.vue` |

State management: `frontend/src/stores/imm05Store.ts`.

---

## 1. Document List (`DocumentManagement.vue`)

### 1.1 Route & Component

| Item | Value |
|---|---|
| Route | `/imm05/documents` |
| Component | `views/DocumentManagement.vue` |
| API call | `imm05.list_documents` |
| Permission | All authenticated (server tự áp visibility filter) |

### 1.2 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────────┐
│ Hồ sơ Tài liệu                                  [+ Tạo Tài liệu mới] │
│ ──────────────────────────────────────────────────────────────────── │
│  Filter:                                                             │
│  [Asset ▼]  [Nhóm ▼]  [Trạng thái ▼]  [Ngày hết hạn ▼]   [Tìm kiếm] │
│                                                                      │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ # | Số hiệu      | Loại            | Tài sản     | Trạng thái  │ │
│ │   |              |                 |             | Hết hạn     │ │
│ ├─────────────────────────────────────────────────────────────────┤ │
│ │ 1 | NK-2026-0042 | Giấy phép NK    | AC-ASSET-2026..  | ✅ Active   │ │
│ │   |              |                 |             | 442 ngày    │ │
│ │ 2 | CO-2025-12   | Chứng nhận XX   | AC-ASSET-2026..  | ⚠️ Pending  │ │
│ │ 3 | RAD-2024-001 | GP bức xạ       | AC-ASSET-2025..  | ❌ Expired  │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│  ◀ 1 2 3 ... 7 ▶   Hiển thị 1-20/137                                 │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.3 State (Pinia)

| Field | Kiểu | Nguồn |
|---|---|---|
| `documents` | Array | `list_documents.items` |
| `pagination` | Object | `list_documents.pagination` |
| `filters` | Object | UI filters (asset_ref, doc_category, workflow_state, expiry range) |
| `loading` | Boolean | — |

### 1.4 Actions

| Button | Action |
|---|---|
| `+ Tạo Tài liệu mới` | Navigate `/imm05/documents/new` (chỉ HTM Tech / Biomed / Tổ HC-QLCL / Workshop Head / CMMS Admin) |
| Click row | Navigate `/imm05/documents/:name` |
| Filter change | Re-call `list_documents` với filters mới |

### 1.5 Status badge

| State | Badge |
|---|---|
| Draft | Gray "Draft" |
| Pending Review | Yellow "⏳ Chờ duyệt" |
| Active | Green "✅ Đang hiệu lực" |
| Rejected | Red "❌ Bị từ chối" |
| Archived | Gray "📦 Đã lưu trữ" |
| Expired | Red "⚠️ Đã hết hạn" |

Expiry countdown:

| days_until_expiry | Màu |
|---|---|
| > 90 | Xanh |
| 30 – 90 | Vàng |
| 0 – 30 | Cam |
| < 0 | Đỏ |

---

## 2. Document Create (`DocumentCreateView.vue`)

### 2.1 Route & Component

| Item | Value |
|---|---|
| Route | `/imm05/documents/new` |
| Component | `views/DocumentCreateView.vue` |
| API | `imm05.create_document` |
| Permission | HTM Tech / Biomed / Tổ HC-QLCL / Workshop Head / CMMS Admin |

### 2.2 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ Tạo Tài liệu mới                                Status: [Draft ●]│
│ ──────────────────────────────────────────────────────────────── │
│ ┌─ Liên kết Thiết bị ──────────────────────────────────────┐    │
│ │ Tài sản*: [Tìm AST-...     ▼]   Phiếu Commissioning:    │    │
│ │ Model:    [Auto-fetch       ]   [Auto-fetch          ▼] │    │
│ │ Khoa:     [Auto-fetch       ]   ☐ Áp dụng toàn Model    │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ ┌─ Phân loại Tài liệu ────────────────────────────────────┐     │
│ │ Nhóm*:   [Legal             ▼]   Số hiệu*: [           ]│     │
│ │ Loại*:   [Giấy phép nhập... ▼]   Phiên bản: [1.0       ]│     │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ ┌─ Thông tin Hiệu lực ────────────────────────────────────┐     │
│ │ Ngày cấp*:   [📅 2026-03-15]    Cơ quan cấp*: [Bộ Y tế] │     │
│ │ Ngày hết hạn:[📅 2027-06-30]    Còn lại: 442 ngày       │     │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ ┌─ File đính kèm ─────────────────────────────────────────┐     │
│ │ 📎 [Chọn file...] hoặc kéo thả                           │     │
│ │ ⓘ Chấp nhận: PDF, JPG, PNG, DOCX (tối đa 25 MB)          │     │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ ┌─ Phạm vi xem ────────────────────────────────────────────┐    │
│ │ ⦿ Public      ○ Internal_Only                             │    │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ──────────────────────────────────────────────────────────────── │
│   [Hủy]                                  [Lưu Draft] [Gửi duyệt] │
└──────────────────────────────────────────────────────────────────┘
```

### 2.3 State

| Field | Kiểu | Validate FE |
|---|---|---|
| `asset_ref` | string | reqd |
| `doc_category` | enum | reqd, dropdown từ Required Document Type |
| `doc_type_detail` | string | reqd, autocomplete theo doc_category |
| `doc_number` | string | reqd |
| `version` | string | default "1.0" |
| `issued_date` | date | reqd |
| `expiry_date` | date | reqd nếu category IN (Legal, Certification) — VR-07 |
| `issuing_authority` | string | reqd nếu category=Legal — VR-04 |
| `file_attachment` | file | reqd; ext IN allowed — VR-08 |
| `change_summary` | textarea | reqd nếu version != "1.0" — VR-09 |
| `visibility` | enum | default "Public" |

### 2.4 Actions

| Button | Action |
|---|---|
| Lưu Draft | `create_document` với `workflow_state="Draft"` |
| Gửi duyệt | `create_document` rồi action workflow "Gửi duyệt" → `Pending_Review` |
| Hủy | Navigate back |

Hiển thị toast lỗi tiếng Việt từ `error.message` khi `success=false`.

---

## 3. Document Detail (`DocumentDetailView.vue`)

### 3.1 Route & Component

| Item | Value |
|---|---|
| Route | `/imm05/documents/:name` |
| Component | `views/DocumentDetailView.vue` |
| API | `imm05.get_document`, `get_document_history`, `approve_document`, `reject_document`, `update_document` |

### 3.2 Layout — theo state

**Draft / Rejected:** Form editable + nút [Lưu], [Gửi duyệt] (Draft) hoặc [Sửa và Gửi lại] (Rejected).

**Pending_Review:** Form READ-ONLY + nút [Approve] [Reject] (chỉ user thuộc `_APPROVE_ROLES`). Nút Reject mở dialog yêu cầu `rejection_reason`.

**Active:** Badge xanh "✅ Active — Đang hiệu lực". Section Phê duyệt hiện `approved_by`, `approval_date`. Hiển thị countdown badge expiry. Nút [Upload phiên bản mới] → mở Create form pre-fill version=N+1.

**Expired:** Badge đỏ "⚠️ Expired — Đã hết hạn ngày {expiry_date}". Banner cảnh báo. Nút [Upload phiên bản mới].

**Archived:** Read-only, badge xám "📦 Archived — Thay thế bởi {superseded_by}".

### 3.3 Tab "Lịch sử" (History)

Gọi `get_document_history(name)` → render timeline:

```
2026-04-18 10:00 | biomed@hosp.vn   | Workflow Transition
                                    | Pending_Review → Active
                                    | + approved_by, approval_date
2026-04-17 15:30 | ktv@hosp.vn      | Field Update
                                    | doc_number: "" → "NK-2026-0042"
```

### 3.4 Actions matrix

| Action | Visible khi | Endpoint |
|---|---|---|
| Sửa metadata | state IN (Draft, Rejected) | `update_document` |
| Gửi duyệt | state = Draft | Workflow action |
| Approve | state = Pending_Review, role IN `_APPROVE_ROLES` | `approve_document` |
| Reject | state = Pending_Review, role IN `_APPROVE_ROLES` | `reject_document` (dialog) |
| Upload phiên bản mới | state IN (Active, Expired) | Navigate Create + pre-fill |
| Tải file | tất cả state | Frappe File API |

---

## 4. Asset Documents Tab (Asset detail)

### 4.1 Route & Component

| Item | Value |
|---|---|
| Route | `/assets/:name/documents` (tab trong Asset Detail) |
| API | `imm05.get_asset_documents(asset)` |
| Permission | All authenticated; server lọc Internal_Only theo role |

### 4.2 Layout wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ Asset: AC-ASSET-2026-0001 (Monitor Philips)                          │
│ Khoa: ICU                                                       │
│ ──────────────────────────────────────────────────────────────  │
│ [Thông tin] [Hồ sơ ●] [Bảo trì] [Lịch sử]                       │
│                                                                 │
│ Compliance: ████████████░░░  71.4%   Status: Compliant          │
│ Còn thiếu: Warranty Card                                        │
│                                                                 │
│ ──── Legal (3) ────                                             │
│   ✅ Chứng nhận đăng ký lưu hành    NK-2025-001  Active  428d   │
│   ✅ Giấy phép nhập khẩu            NK-2026-042  Active  442d   │
│   📦 Giấy phép nhập khẩu            NK-2024-099  Archived       │
│                                                                 │
│ ──── Technical (2) ────                                         │
│   ✅ User Manual (HDSD)             v3.2         Active         │
│   ✅ Service Manual                 v2.0         Active         │
│                                                                 │
│ ──── Certification (1) ────                                     │
│   ⚠️ Chứng chỉ hiệu chuẩn          C-2025-007   Expiring 28d   │
│                                                                 │
│ [+ Upload tài liệu mới]   [Yêu cầu tài liệu thiếu]              │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Actions

| Button | Action |
|---|---|
| `+ Upload tài liệu mới` | Navigate Create với `asset_ref` pre-filled |
| `Yêu cầu tài liệu thiếu` | Mở `DocumentRequestModal` |

Click row doc → navigate Document Detail.

---

## 5. Dashboard IMM-05 (TBD frontend)

### 5.1 Route & Component

| Item | Value |
|---|---|
| Route | `/imm05/dashboard` |
| Component | TBD |
| API | `get_dashboard_stats`, `get_expiring_documents`, `get_compliance_by_dept` |
| Permission | Workshop Head, VP Block2, CMMS Admin, Tổ HC-QLCL |

### 5.2 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ IMM-05 Document Compliance Dashboard                              │
│ ──────────────────────────────────────────────────────────────── │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│ │ Total      │ │ Expiring   │ │ Expired    │ │ Assets     │    │
│ │  Active    │ │  90 ngày   │ │  Not Renew │ │  Missing   │    │
│ │   412      │ │   28       │ │    5       │ │   17       │    │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│                                                                  │
│ ┌─────── Expiry Timeline 90 ngày ───────┐ ┌──── Compliance ───┐ │
│ │  Loại               Thiết bị   Còn   │ │  ICU   ████ 92%   │ │
│ │  Giấy phép NK      AC-ASSET-001    7 ngày │ │  OR    ███  78%   │ │
│ │  CN ĐK lưu hành    AC-ASSET-014    14 ngày│ │  ER    ██   65%   │ │
│ │  ...                                  │ │  CT    █    42%   │ │
│ └───────────────────────────────────────┘ └───────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3 KPIs

| KPI | API field | Click action |
|---|---|---|
| Total Active | `kpis.total_active` | Filter list state=Active |
| Expiring 90d | `kpis.expiring_90d` | `get_expiring_documents(90)` |
| Expired | `kpis.expired_not_renewed` | Filter list state=Expired |
| Assets Missing | `kpis.assets_missing_docs` | Báo cáo riêng |

---

## 6. Document Request Modal (`DocumentRequestModal.vue`)

### 6.1 Trigger

| Trigger | From |
|---|---|
| Asset Documents tab | Button "Yêu cầu tài liệu thiếu" |
| Dashboard | Button "Tạo Request" trên row missing |

### 6.2 Layout

```
┌─────────────────────────────────────────────┐
│ Yêu cầu Tài liệu                       [✕] │
│ ─────────────────────────────────────────── │
│ Tài sản:           AC-ASSET-2026-0001 (locked)   │
│ Loại tài liệu*:    [Warranty Card        ▼] │
│ Nhóm*:             [QA                   ▼] │
│ Giao cho*:         [📧 vendor@...       ▼] │
│ Hạn hoàn thành*:   [📅 2026-05-18         ] │
│ Ưu tiên:           ⦿ Medium ○ High ○ Crit  │
│ Ghi chú:           [textarea               ] │
│                                              │
│                       [Hủy] [Tạo Request]   │
└─────────────────────────────────────────────┘
```

API: `create_document_request`. Default `due_date = today + 30`, `assigned_to = session.user`, `source_type = "Manual"`.

---

## 7. Exempt Modal (`ExemptModal.vue`)

### 7.1 Trigger & Permission

| Item | Value |
|---|---|
| Trigger | Button "Đánh dấu Exempt" trên Asset Detail (chỉ khi thiếu CN ĐK lưu hành) |
| Permission | Tổ HC-QLCL, CMMS Admin, Workshop Head |
| API | `mark_exempt` |

### 7.2 Layout

```
┌───────────────────────────────────────────────┐
│ Miễn đăng ký NĐ98                       [✕]  │
│ ───────────────────────────────────────────── │
│ Tài sản:         AC-ASSET-2026-0001 (locked)       │
│ Loại tài liệu*:  ⦿ Chứng nhận ĐK lưu hành    │
│                  ○ Giấy phép nhập khẩu        │
│ Lý do miễn*:     [textarea                  ] │
│                  (tối thiểu 30 ký tự)         │
│ Văn bản miễn*:   📎 [Chọn file...           ] │
│                                                │
│ ⚠ Lưu ý: Hành động này tạo Asset Document    │
│   Active với is_exempt=1, GW-2 sẽ unblock.    │
│                                                │
│                    [Hủy] [Xác nhận Miễn ĐK]   │
└───────────────────────────────────────────────┘
```

VR-11 enforce trong UI: dropdown `doc_type_detail` chỉ hiện 2 lựa chọn được phép.

Sau success: hiện toast "Đã đánh dấu Exempt. Trạng thái Asset: Compliant (Exempt)" + reload Asset detail.

---

## 8. UX Patterns chung

### 8.1 Toast / Notification

| Loại | Màu | Nội dung mẫu |
|---|---|---|
| Success | Xanh | "✅ Đã tạo tài liệu DOC-..." |
| Warning | Vàng | "⚠️ Tài liệu sắp hết hạn trong 28 ngày" |
| Error | Đỏ | Hiển thị `response.error.message` (tiếng Việt từ VR/`_err`) |

### 8.2 Empty states

| Page | Empty message |
|---|---|
| Document List | "Chưa có tài liệu nào. [+ Tạo mới]" |
| Asset Documents Tab | "Asset chưa có hồ sơ. Upload tài liệu đầu tiên." |
| Dashboard | "Không có dữ liệu compliance" |

### 8.3 Loading states

Skeleton loader cho list/grid. Spinner cho actions (approve/reject/create).

### 8.4 Visibility indicators

Badge nhỏ cạnh tên tài liệu:

- 🌐 Public (mặc định, không hiện)
- 🔒 Internal_Only (icon ổ khóa)

### 8.5 Responsive

- Desktop ≥ 1280px: Layout 2 column (form + side panel history)
- Tablet 768-1279px: 1 column, history collapse
- Mobile < 768px: Tab navigation cho Asset Documents tab

---

## 9. Permission-driven UI

| UI Element | Hide khi |
|---|---|
| `+ Tạo Tài liệu mới` | role NOT IN {HTM Tech, Biomed, Tổ HC-QLCL, Workshop Head, CMMS Admin} |
| Nút [Approve] | state ≠ Pending_Review hoặc role NOT IN `_APPROVE_ROLES` |
| Nút [Reject] | giống Approve |
| Nút [Đánh dấu Exempt] | role NOT IN `_EXEMPT_ROLES` |
| Doc với `visibility=Internal_Only` | server đã lọc; FE không hiện thêm |
| Tab Dashboard | role NOT IN {Workshop Head, VP Block2, CMMS Admin, Tổ HC-QLCL} |

---

## 10. Accessibility

| Yêu cầu | Implementation |
|---|---|
| Keyboard navigation | Tab order qua form fields, Enter submit |
| ARIA labels | Buttons, status badges có `aria-label` tiếng Việt |
| Color contrast | Badge màu đảm bảo WCAG AA (4.5:1) |
| Screen reader | Toast + modal sử dụng `role="alert"` / `role="dialog"` |
