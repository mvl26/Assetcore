# IMM-07 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-07 — Vận hành hàng ngày |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-21 |

---

## 1. Routes

| Path | Name | Component | Mô tả |
|---|---|---|---|
| `/daily-ops` | `DailyOpsDashboard` | `DailyOperationDashboard.vue` | Dashboard trạng thái hôm nay |
| `/daily-ops/log` | `DailyLogCreate` | `DailyLogCreateView.vue` | Tạo nhật ký ca |
| `/daily-ops/logs` | `DailyLogList` | `DailyLogListView.vue` | Danh sách nhật ký |

---

## 2. DailyOperationDashboard.vue

### Layout
- Header: "Vận hành hôm nay" + date + filter by Dept
- KPI row (4 cards):
  - Running: green bg, số thiết bị đang chạy
  - Standby: yellow, thiết bị chờ
  - Fault: red + pulse animation
  - Total runtime hours: blue
- Asset status grid (card per asset):
  - Màu viền: green=Running, yellow=Standby, red=Fault, gray=Not Used, orange=Under Maintenance
  - Hiển thị: asset name, dept, ca hiện tại, runtime hours hôm nay
  - Click → DailyLogListView filter by asset
- Alert panel: Fault devices (nếu có) hiển thị nổi bật

### Asset Card
```
┌─────────────────────┐ (border-green-400)
│ [Running]           │
│ Máy thở Drager      │
│ ICU - Ca sáng       │
│ Runtime: 8.0h       │
└─────────────────────┘
```

---

## 3. DailyLogCreateView.vue

### Form sections

**Section 1 — Thiết bị & Ca**
- `asset`: Link to AC Asset (search)
- `log_date`: Date (default today)
- `shift`: Select (Morning/Afternoon/Night)
- `operated_by`: User (default: session user)
- `dept`: Auto-fill từ asset

**Section 2 — Trạng thái vận hành**
- `operational_status`: Select với màu icon:
  - Running: green circle
  - Standby: yellow circle
  - Fault: red circle
  - Under Maintenance: orange circle
  - Not Used: gray circle
- `start_meter_hours`: Number
- `end_meter_hours`: Number
- `runtime_hours`: Computed display (read-only)
- `usage_cycles`: Number

**Section 3 — Bất thường**
- Toggle: "Có bất thường trong ca?" (Check)
- Khi bật:
  - `anomaly_type`: Select (Minor/Major/Critical) với màu
  - `anomaly_description`: Textarea (required khi toggle on)
  - Warning banner: "Anomaly Critical/Major sẽ tự động tạo Sự cố"

**Actions**
- "Lưu nhật ký" → POST create_daily_log, rồi POST submit_log

---

## 4. DailyLogListView.vue

### Layout
- Header: "Nhật ký Vận hành" + button "Ghi nhật ký ca mới"
- Filter row: Asset, Dept, Date range, Operational Status
- Table: Ngày | Ca | Thiết bị | Trạng thái | Runtime | Bất thường | Review | Cập nhật

### Columns detail

| Column | Display |
|---|---|
| Ngày | YYYY-MM-DD |
| Ca | Badge: Morning=blue, Afternoon=green, Night=purple |
| Thiết bị | Asset name (link) |
| Trạng thái | Color badge per status |
| Runtime | "Xh Ym" format |
| Bất thường | Icon nếu anomaly_detected |
| Review | Badge: Open/Logged/Reviewed |

---

## 5. State-based UI changes

| Workflow State | Log form editable | Actions |
|---|---|---|
| Open | Tất cả fields | "Nộp nhật ký" |
| Logged | Read-only | "Phê duyệt" (Dept Head) / "Yêu cầu chỉnh sửa" |
| Reviewed | Read-only | — |

---

## 6. Key UX Notes

- Dashboard tự refresh mỗi 5 phút (setInterval)
- Fault devices hiển thị pulsing red dot
- Khi tạo log, runtime_hours được tính realtime khi blur end_meter
- Anomaly Critical → banner cảnh báo đỏ trước khi submit
- Mobile-friendly: 1 cột trên mobile, 2 cột trên tablet

*End of UI/UX Guide v1.0.0 — IMM-07*
