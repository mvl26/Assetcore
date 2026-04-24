# IMM-14 — Lưu trữ & Kết thúc Hồ sơ (UI/UX Guide)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-14 — UI/UX Guide |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. Routes

| Route | View Component | Mô tả |
|---|---|---|
| `/archive` | `ArchiveListView.vue` | Danh sách hồ sơ lưu trữ |
| `/archive/:name` | `ArchiveDetailView.vue` | Chi tiết + document inventory + timeline |

---

## 2. ArchiveListView

### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ [IMM-14 · Lưu trữ]   Hồ sơ Lưu trữ Thiết bị               │
│ Tổng XX hồ sơ                                               │
├─────────────────────────────────────────────────────────────┤
│ Stats Bar:                                                   │
│ [8 Đã lưu trữ] [2 Đang xác minh] [0 Sắp hết hạn]          │
├─────────────────────────────────────────────────────────────┤
│ Filters: [Search] [Status ▼]                                │
├─────────────────────────────────────────────────────────────┤
│ Mã AAR    │ Thiết bị  │ Ngày lưu│ Hết hạn    │ Tài liệu │ TT│
│ AAR-26-.. │ MRI-001   │21/04/26 │ 21/04/2036 │ 35        │[.│
│           │           │         │ ⚠️ 30d     │           │  │
└─────────────────────────────────────────────────────────────┘
```

### Highlight hết hạn
- `release_date` trong 365 ngày tới: `bg-amber-50 border-l-4 border-amber-400`
- `release_date` trong 30 ngày: `bg-red-50 border-l-4 border-red-400` + badge "Sắp hết hạn"

### Status badges
| Status | Màu |
|---|---|
| Draft | Slate |
| Compiling | Blue |
| Verified | Emerald |
| Archived | `bg-slate-200 text-slate-600` — xám trung tính |

---

## 3. ArchiveDetailView

### Layout 3 Tab
```
[Thông tin Lưu trữ] [Danh mục Tài liệu] [Timeline Vòng đời]
```

**Tab 1 — Thông tin Lưu trữ:**
```
┌─────────────────────────────────────────────────────┐
│ [Archive] AAR-26-00001                [Archived]    │
│ Thiết bị: MRI 1.5T Siemens          asset link     │
│ Phiếu thanh lý: DR-26-04-00001      link           │
│ Ngày lưu trữ: 25/04/2026                           │
│ Hết hạn: 25/04/2036 (còn 3.650 ngày)               │
│ Vị trí: Server DMS / Tủ văn thư                    │
│ Tổng tài liệu: 35                                  │
└─────────────────────────────────────────────────────┘

Ghi chú lưu trữ: [text]

[Báo cáo vòng đời tóm tắt PDF ↓]
```

**Action buttons theo state:**
| State | Buttons |
|---|---|
| Draft | [Bắt đầu biên soạn] |
| Compiling | [Biên soạn lịch sử tự động] [Xác minh đầy đủ] |
| Verified | [Hoàn tất lưu trữ (Submit)] |
| Archived | (read only) |

**Tab 2 — Danh mục Tài liệu:**
```
┌───────────────────────────────────────────────────────────────┐
│ [Biên soạn tự động]              Total: 35   Missing: 0       │
├───────────────────────────────────────────────────────────────┤
│ Loại           │ Mã tài liệu     │ Ngày      │ Trạng thái    │
│ Commissioning  │ IMM04-11-03-... │ 15/03/11  │ [Included ✓]  │
│ PM Record      │ WO-PM-2011-...  │ 15/06/11  │ [Included ✓]  │
│ Calibration    │ —               │ —         │ [Missing ⚠️]  │
│ (waived)       │ —               │ —         │ [Waived —]    │
└───────────────────────────────────────────────────────────────┘
```

- Missing items: `bg-amber-50 text-amber-700`
- Waived: `bg-slate-50 text-slate-400 line-through`
- Included: `bg-white text-slate-700`

**Tab 3 — Timeline Vòng đời:**
```
Toàn bộ lifecycle từ commissioned → archived
(gọi get_asset_full_history API)

2011-03-15  ● commissioned    [IMM04-11-03-00001]
2011-06-15  ● pm_completed    [WO-PM-2011-00001]
...
2026-04-21  ● decommissioned  [DR-26-04-00001]
2026-04-25  ● archived        [AAR-26-00001]
```
- Vertical timeline với dots màu theo event_type
- Scroll tới cuối mặc định (most recent)

---

## 4. Icons

| Ngữ cảnh | Lucide Icon |
|---|---|
| Page header | `Archive` |
| Status Archived | `Lock` |
| Status Verified | `CheckCircle2` |
| Document Included | `FileCheck` |
| Document Missing | `FileX` |
| Document Waived | `FileMinus` |
| Timeline | `History` |
| Expiry warning | `AlertTriangle` |
| Compile button | `RefreshCw` |

---

## 5. Empty States

- Không có tài liệu nào: "Chưa có tài liệu. Bấm 'Biên soạn lịch sử tự động' để tổng hợp."
- Timeline trống: "Không có sự kiện vòng đời nào được ghi lại."

---

*End of UI/UX Guide v1.0.0 — IMM-14*
