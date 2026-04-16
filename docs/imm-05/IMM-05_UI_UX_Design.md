# IMM-05 UI/UX Design

**Module:** IMM-05 — Đăng ký, Cấp phép & Quản lý Hồ sơ Thiết bị Y tế
**Version:** 1.0-draft
**Ngày:** 2026-04-16
**Trạng thái:** CHỜ PHÊ DUYỆT

---

## 1. Tổng quan Giao diện

IMM-05 có **3 giao diện chính** và **2 giao diện tích hợp**:

| # | Trang | Loại | URL (Desk) | URL (Vue FE) |
|---|-------|------|------------|--------------|
| P-01 | Asset Document Form | DocType Form | /app/asset-document/{name} | /imm05/documents/{name} |
| P-02 | Asset Document List | DocType List | /app/asset-document | /imm05/documents |
| P-03 | IMM-05 Dashboard | Frappe Page | /app/imm05-dashboard | /imm05/dashboard |
| P-04 | Asset Tab "Hồ sơ" | Sidebar/Tab trên Asset Form | /app/asset/{name} (tab) | /assets/{name}/documents |
| P-05 | Expiry Alert Log | DocType List (read-only) | /app/expiry-alert-log | /imm05/alerts |

---

## 2. P-01: Asset Document Form

### 2.1 Layout — Draft State

```
┌─────────────────────────────────────────────────────────────────┐
│ [DOC-AST-2026-0001-2026-00001]          Status: [Draft ●]       │
│ ──────────────────────────────────────────────────────────────── │
│                                                                 │
│ ┌─ Liên kết Thiết bị ───────────────────────────────────────┐  │
│ │ Tài sản*:     [AST-2026-0001 ▼]  │ Phiếu Commissioning: │  │
│ │ Model:        [Auto-fetch     ]  │ [IMM04-26-04-00001 ] │  │
│ │ Khoa/Phòng:   [Auto-fetch     ]  │ Module nguồn: IMM-04 │  │
│ │ ☐ Áp dụng toàn bộ Model         │                       │  │
│ └──────────────────────────────────┴────────────────────────┘  │
│                                                                 │
│ ┌─ Phân loại Tài liệu ─────────────────────────────────────┐  │
│ │ Nhóm Hồ sơ*:  [Legal ▼]         │ Số hiệu*: [RL-2026-  │  │
│ │ Loại cụ thể*: [Giấy phép nhập k │  0042     ]           │  │
│ │                ẩu             ▼]  │ Phiên bản: [1.0]     │  │
│ └──────────────────────────────────┴────────────────────────┘  │
│                                                                 │
│ ┌─ Thông tin Hiệu lực ─────────────────────────────────────┐  │
│ │ Ngày cấp*:     [2026-03-15]     │ Số ngày còn: [    442] │  │
│ │ Ngày hết hạn*: [2027-06-30]     │ ☐ Đã hết hạn          │  │
│ │ Cơ quan cấp*:  [Bộ Y tế]       │                        │  │
│ └──────────────────────────────────┴────────────────────────┘  │
│                                                                 │
│ ┌─ File đính kèm ──────────────────────────────────────────┐  │
│ │ 📎 [Chọn file...] hoặc kéo thả vào đây                   │  │
│ │                                                           │  │
│ │ ┌──────────────────────────────────────────────┐          │  │
│ │ │ 📄 giay-phep-NK-2026-0042.pdf  (2.3 MB)     │  [Xem]  │  │
│ │ └──────────────────────────────────────────────┘          │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─ Ghi chú ────────────────────────────────────────────────┐  │
│ │ [Rich text editor — ghi chú nội bộ]                       │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ──────────────────────────────────────────────────────────────── │
│ [Save]  [Gửi Duyệt →]                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Layout — Pending_Review State

```
Thay đổi so với Draft:
- Tất cả field metadata → READ-ONLY
- File attachment → READ-ONLY (có nút Xem/Download)
- Nút hành động:
  [✓ Approve]  [✗ Reject]  (chỉ hiện cho Biomed/QA)
- Nếu bấm Reject → Dialog popup yêu cầu điền rejection_reason
```

### 2.3 Layout — Active State

```
Thay đổi:
- Badge xanh: "✓ Active — Đang có hiệu lực"
- Section Phê duyệt hiện:
  Người phê duyệt: admin@... | Ngày: 2026-04-16
- Nếu có expiry → Hiển thị countdown badge:
  [⏰ Còn 442 ngày]  (xanh nếu >90, vàng nếu 30-90, đỏ nếu <30)
- Nút: [Upload phiên bản mới]
```

### 2.4 Layout — Expired State

```
Thay đổi:
- Badge đỏ: "⚠ Expired — Đã hết hạn"
- Banner cảnh báo đỏ trên cùng:
  "Tài liệu này đã hết hạn ngày {date}. Vui lòng upload phiên bản mới."
- Nút: [Upload phiên bản mới]
```

### 2.5 Layout — Archived State

```
Thay đổi:
- Badge xám: "Archived"
- Tất cả read-only
- Hiển thị:
  "Đã thay thế bởi: [DOC-...-00002]" (link)
  "Ngày archive: 2026-04-16"
- Không có nút hành động
```

### 2.6 Field Visibility theo State

| Field/Section | Draft | Pending_Review | Active | Expired | Archived | Rejected |
|--------------|:-----:|:--------------:|:------:|:-------:|:--------:|:--------:|
| Liên kết Thiết bị | Edit | Read | Read | Read | Read | Read |
| Phân loại | Edit | Read | Read | Read | Read | Read |
| Hiệu lực | Edit | Read | Read | Read | Read | Read |
| File đính kèm | Edit | Read + View | Read + View | Read + View | Read + View | Read |
| Ghi chú | Edit | Read | Edit | Read | Read | Read |
| Section Phê duyệt | Hidden | Hidden | Show | Show | Show | Show |
| Section Version Control | Hidden | Hidden | Hidden | Hidden | Show | Hidden |
| Rejection Reason | Hidden | Hidden | Hidden | Hidden | Hidden | Show |
| Nút "Gửi Duyệt" | Show | Hidden | Hidden | Hidden | Hidden | Hidden |
| Nút Approve/Reject | Hidden | Show (Biomed/QA) | Hidden | Hidden | Hidden | Hidden |
| Nút "Upload mới" | Hidden | Hidden | Show | Show | Hidden | Hidden |

---

## 3. P-02: Asset Document List View

### 3.1 Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ Hồ sơ Thiết bị                     [+ Tạo mới] [⟳ Làm mới]        │
│ ────────────────────────────────────────────────────────────────── │
│ Bộ lọc:                                                            │
│ [Nhóm ▼] [Trạng thái ▼] [Khoa ▼] [Sắp hết hạn ☐] [Tìm kiếm...] │
│ ────────────────────────────────────────────────────────────────── │
│                                                                     │
│ ┌───────────┬─────────────┬───────────┬───────────┬───────┬──────┐ │
│ │ Mã        │ Tài sản     │ Loại      │ Nhóm      │ Expiry│Status│ │
│ ├───────────┼─────────────┼───────────┼───────────┼───────┼──────┤ │
│ │ DOC-...01 │ AST-2026-01 │ Giấy phép │ Legal     │ 06/27 │ ✓   │ │
│ │ DOC-...02 │ AST-2026-01 │ HDSD      │ Technical │ —     │ ✓   │ │
│ │ DOC-...03 │ AST-2026-02 │ Cert hiệu │ Certif... │ 01/27 │ ⏰  │ │
│ │ DOC-...04 │ AST-2026-03 │ Warranty  │ QA        │ 04/26 │ ⚠   │ │
│ └───────────┴─────────────┴───────────┴───────────┴───────┴──────┘ │
│                                                                     │
│ [‹ Trước]  Trang 1 / 12  [Sau ›]                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Status Icons trong List

| workflow_state | Icon | Màu |
|---------------|------|-----|
| Draft | ○ | Gray |
| Pending_Review | ◐ | Blue |
| Active | ✓ | Green |
| Expired | ⚠ | Red |
| Archived | ▪ | Dark Gray |
| Rejected | ✗ | Red |

### 3.3 Expiry Column Logic

| Trạng thái | Hiển thị |
|-----------|----------|
| Không có expiry_date | `—` |
| > 90 ngày | `MM/YY` (text thường) |
| 30-90 ngày | `MM/YY` (vàng, bold) + icon ⏰ |
| < 30 ngày | `MM/YY` (đỏ, bold) + icon ⚠ |
| Đã hết hạn | `HẾT HẠN` (đỏ, badge) |

---

## 4. P-03: IMM-05 Dashboard

### 4.1 Layout tổng thể

```
┌─────────────────────────────────────────────────────────────────────┐
│ [IMM-05] Dashboard Hồ sơ & Cấp phép Thiết bị Y tế                 │
│                                        [+ Tạo mới] [⟳ Làm mới]    │
│ ──────────────────────────────────────────────────────────────────── │
│                                                                     │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│ │   342    │ │    12    │ │     3    │ │     8    │ │   85%    │  │
│ │ Active   │ │ Sắp hết │ │ Đã hết  │ │ Thiếu   │ │Compliance│  │
│ │ Docs     │ │ hạn 90d  │ │ hạn!    │ │ hồ sơ   │ │ Rate     │  │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                                     │
│ ┌─ Timeline Hết hạn ──────────────────────────────────────────────┐ │
│ │ ┌──────────┬──────────────┬────────────────┬────────┬─────────┐ │ │
│ │ │ Tài liệu │ Tài sản      │ Loại           │ Expiry │ Còn lại │ │ │
│ │ ├──────────┼──────────────┼────────────────┼────────┼─────────┤ │ │
│ │ │ DOC-..03 │ AST-2026-02  │ Cert hiệu chuẩn│ 01/27  │ 15 ngày │ │ │
│ │ │ DOC-..04 │ AST-2026-03  │ Warranty Card   │ 05/26  │ 28 ngày │ │ │
│ │ │ DOC-..08 │ AST-2026-05  │ Giấy phép BXạ   │ 07/26  │ 62 ngày │ │ │
│ │ └──────────┴──────────────┴────────────────┴────────┴─────────┘ │ │
│ └────────────────────────────────────────────────────────────────── │
│                                                                     │
│ ┌─ Compliance theo Khoa ──────────────┐ ┌─ Hồ sơ Chờ duyệt ─────┐ │
│ │                                     │ │                        │ │
│ │  ICU      ████████████░░  88%       │ │ DOC-..12 — Giấy phép  │ │
│ │  OR       █████████░░░░░  72%       │ │ DOC-..13 — Service Man │ │
│ │  Cấp cứu ██████████████  100%      │ │ DOC-..14 — HDSD        │ │
│ │  Nhi      ███████░░░░░░░  56%       │ │                        │ │
│ │  XN       █████████████░  92%       │ │ [Xem tất cả →]        │ │
│ │                                     │ │                        │ │
│ └─────────────────────────────────────┘ └────────────────────────┘ │
│                                                                     │
│ ┌─ Assets Thiếu Hồ sơ Bắt buộc ──────────────────────────────────┐ │
│ │ ┌──────────────┬──────────┬──────────────────┬─────────────────┐ │ │
│ │ │ Tài sản      │ Khoa     │ Thiếu            │ Completeness    │ │ │
│ │ ├──────────────┼──────────┼──────────────────┼─────────────────┤ │ │
│ │ │ AST-2026-07  │ Nhi      │ HDSD, Warranty   │ ███░░░ 57%     │ │ │
│ │ │ AST-2026-11  │ OR       │ Cert lưu hành    │ █████░ 86%     │ │ │
│ │ └──────────────┴──────────┴──────────────────┴─────────────────┘ │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 KPI Card Behavior

| KPI | Click action | Màu border |
|-----|-------------|-----------|
| Active Docs | → List View filter Active | Blue |
| Sắp hết hạn 90d | → List View filter expiry <= 90d | Yellow |
| Đã hết hạn | → List View filter Expired | Red (pulse nếu > 0) |
| Thiếu hồ sơ | → Bảng "Assets Thiếu" scroll | Orange |
| Compliance Rate | Tooltip hiện breakdown | Green/Yellow/Red theo % |

### 4.3 Responsive

| Viewport | KPI Grid | Tables | Charts |
|----------|---------|--------|--------|
| Desktop (>1200px) | 5 columns | Full | Side-by-side |
| Tablet (768-1200px) | 3 columns | Scrollable | Stacked |
| Mobile (<768px) | 2 columns | Card view | Hidden |

---

## 5. P-04: Asset Tab "Hồ sơ"

### 5.1 Tích hợp trên form Asset

Thêm 1 tab hoặc section trên form Asset (via Custom Script hoặc Client Script):

```
[Tab: Details] [Tab: Maintenance] [Tab: Hồ sơ ★]

┌─ Hồ sơ Thiết bị ─────────────────────────────────────────────────┐
│                                                                   │
│ Tỷ lệ đầy đủ: ██████████░░ 71% (5/7 bắt buộc)                   │
│ Hồ sơ hết hạn gần nhất: 2027-06-30 (Giấy phép nhập khẩu)        │
│                                                                   │
│ ── Pháp lý ──────────────────────────────────────────────────────│
│  ✓ Giấy phép nhập khẩu        v1.0   Active   Exp: 06/2027     │
│  ✗ Chứng nhận đăng ký lưu hành         — THIẾU —               │
│                                                                   │
│ ── Kỹ thuật ─────────────────────────────────────────────────────│
│  ✓ User Manual (HDSD)          v1.0   Active   —                │
│  ○ Service Manual              v1.0   Draft    —                │
│                                                                   │
│ ── Chất lượng ───────────────────────────────────────────────────│
│  ✓ CO - Chứng nhận Xuất xứ    v1.0   Active   —                │
│  ✓ CQ - Chứng nhận Chất lượng v1.0   Active   —                │
│  ✓ Warranty Card               v1.0   Active   Exp: 04/2028    │
│                                                                   │
│ [+ Upload tài liệu mới]  [Xem toàn bộ lịch sử →]               │
└───────────────────────────────────────────────────────────────────┘
```

### 5.2 Logic hiển thị

- **Row có ✓:** doc Active tồn tại
- **Row có ✗ + "THIẾU":** doc bắt buộc nhưng chưa có Active doc
- **Row có ○:** doc tồn tại nhưng chưa Active (Draft/Pending)
- **Row có ⚠:** doc Expired
- Required docs lấy từ `Required Document Type` master table

---

## 6. UI States

### 6.1 Loading State

```
┌──────────────────────────────────────┐
│                                      │
│        ◌ Đang tải dữ liệu...        │
│                                      │
│  [Skeleton KPI cards]                │
│  [Skeleton table rows]               │
│                                      │
└──────────────────────────────────────┘
```

### 6.2 Empty State

```
┌──────────────────────────────────────┐
│                                      │
│         📂 Chưa có hồ sơ nào        │
│                                      │
│  Bắt đầu upload tài liệu cho       │
│  thiết bị y tế tại đây.             │
│                                      │
│       [+ Upload tài liệu mới]       │
│                                      │
└──────────────────────────────────────┘
```

### 6.3 Error State

```
┌──────────────────────────────────────┐
│                                      │
│    ⚠ Không thể tải dữ liệu         │
│                                      │
│    Vui lòng kiểm tra kết nối        │
│    hoặc thử lại sau.                │
│                                      │
│    [Thử lại]  [Báo lỗi IT]          │
│                                      │
└──────────────────────────────────────┘
```

### 6.4 Permission Denied State

```
┌──────────────────────────────────────┐
│                                      │
│    🔒 Bạn không có quyền truy cập   │
│                                      │
│    Liên hệ quản trị viên CMMS       │
│    để được cấp quyền xem hồ sơ.     │
│                                      │
└──────────────────────────────────────┘
```

---

## 7. Interaction Patterns

### 7.1 Upload File

```
Người dùng click "Upload" hoặc kéo thả file
  │
  ├─ File > 25MB → Toast đỏ: "File quá lớn (tối đa 25MB)"
  ├─ File format sai → Toast đỏ: "Chỉ chấp nhận PDF, JPG, PNG"
  └─ Hợp lệ → Upload progress bar → Hiển thị preview
```

### 7.2 Approve Document

```
Reviewer click [✓ Approve]
  │
  ├─ Nếu có version cũ Active:
  │   → Dialog confirm: "Version cũ (v1.0) sẽ được Archive. Tiếp tục?"
  │   → [Xác nhận] → API call → Toast xanh: "Đã phê duyệt"
  │
  └─ Không có version cũ:
      → API call → Toast xanh: "Đã phê duyệt"
```

### 7.3 Reject Document

```
Reviewer click [✗ Reject]
  │
  → Dialog popup:
    ┌─ Từ chối Tài liệu ──────────────────┐
    │ Lý do từ chối*:                      │
    │ [                                  ] │
    │                                      │
    │           [Hủy]  [Xác nhận Từ chối]  │
    └──────────────────────────────────────┘
  │
  → API call → Toast cam: "Đã từ chối — người upload sẽ nhận thông báo"
```

### 7.4 Expiry Alert Notification

```
In-app notification bell:
  ┌──────────────────────────────────────┐
  │ ⏰ Cảnh báo Hết hạn                  │
  │                                      │
  │ Giấy phép bức xạ (AST-2026-02)      │
  │ hết hạn sau 30 ngày (2026-05-16).    │
  │ [Xem tài liệu →]                    │
  └──────────────────────────────────────┘
```

---

## 8. Color System

| Semantic | Hex | Dùng cho |
|----------|-----|---------|
| Success / Active | #28a745 | Active badge, compliance >=80% |
| Warning / Expiring | #ffc107 | 30-90 ngày, compliance 60-80% |
| Danger / Expired | #dc3545 | Expired, thiếu hồ sơ, compliance <60% |
| Info / Pending | #17a2b8 | Pending_Review, info alert |
| Muted / Archived | #6c757d | Archived, disabled |
| Primary / Action | var(--primary) | Buttons, links |

---

## 9. Frappe Desk vs Vue Frontend

Tất cả UI trên được thiết kế **dual-compatible**:

| Thành phần | Frappe Desk | Vue Frontend |
|-----------|-------------|-------------|
| Form Asset Document | Native DocType form + JS | Custom Vue component + API |
| List View | Native List + JS override | Vue table + imm05.list_documents |
| Dashboard | Frappe Page (HTML + JS + CSS) | Vue page + imm05.get_dashboard_stats |
| Asset Tab | Client Script inject | Vue sidebar component |
| Notifications | frappe.publish_realtime | WebSocket listener |

API layer (`api/imm05.py`) phục vụ **cả hai** — Desk gọi qua `frappe.call()`, Vue gọi qua `fetch()`.
