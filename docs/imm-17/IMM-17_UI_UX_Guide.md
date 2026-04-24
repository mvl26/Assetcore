# IMM-17 — Phân tích dự đoán
## UI/UX Design Guide

**Phiên bản:** 1.0.0
**Ngày tạo:** 2026-04-24
**Tech stack:** Vue 3 + TypeScript + Tailwind CSS + Pinia + Chart.js
**Trạng thái:** Draft

---

## 1. Screen Map — 6 Màn hình

```
/imm17/
├── cockpit                    Screen 1: Predictive Cockpit Dashboard (main)
├── assets/:id/risk            Screen 2: Asset Risk Detail View
├── pm-optimization            Screen 3: PM Optimization View
├── spare-forecast             Screen 4: Spare Parts Forecast View
├── budget-forecast            Screen 5: Budget Forecast View
└── what-if                    Screen 6: What-If Analysis View
```

### Navigation trong App

```
Sidebar IMM-17 menu:
  └─ Phân tích dự đoán
      ├─ [icon] Cockpit Tổng quan
      ├─ [icon] Tối ưu lịch PM
      ├─ [icon] Dự báo phụ tùng
      ├─ [icon] Dự báo ngân sách
      └─ [icon] Phân tích kịch bản
```

---

## 2. Screen 1 — Predictive Cockpit Dashboard

**Route:** `/imm17/cockpit`
**Mô tả:** Landing page chính, hiển thị toàn bộ fleet health status và active alerts.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  IMM-17 Predictive Cockpit                          [Chạy lại dự đoán]│
│  Cập nhật lần cuối: 21/04/2026 06:00  ⚠ Dữ liệu đã 3 ngày tuổi       │
├──────────┬──────────┬──────────┬──────────┬──────────────────────────┤
│ Accuracy │Preventbl │  Cost    │  Alert   │   Data Quality           │
│ Rate     │Failures  │Avoidance │ Response │   Score                  │
│ 73.5%  ↑ │  3 ca    │85M VNĐ  │ 97.2% ✓  │   87.9% ✓               │
│ [sparkline] [sparkline] [sparkline] [sparkline] [progress bar]       │
├──────────┴──────────┴──────────┴──────────┴──────────────────────────┤
│                                                                        │
│  RISK HEATMAP — Fleet (247 thiết bị)     [Filter: All Dept ▼] [Zoom]  │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ [HEATMAP GRID — xem spec chi tiết bên dưới]                  │    │
│  │ Mỗi ô = 1 asset, màu sắc = risk tier                        │    │
│  │ 🟢 Low (184) 🟡 Medium (47) 🟠 High (12) 🔴 Critical (4)   │    │
│  └───────────────────────────────────────────────────────────────┘    │
├─────────────────────────────┬──────────────────────────────────────┤
│  ⚠ Alerts Đang Mở            │  Top 10 Rủi ro Cao Nhất              │
│  Critical: 2 | High: 8      │                                        │
│  ─────────────────────────  │  1. Ventilator Hamilton G5  88.3 🔴   │
│  [ALERT-142] Máy thở ICU    │     ICU — Acknowledge ⚡              │
│  Critical | Quá SLA 15.5h   │  2. X-quang Siemens Ysio  76.1 🟠   │
│  [Xem chi tiết] [Ack]       │     Radiology — Xem chi tiết →       │
│  ─────────────────────────  │  3. Monitor Philips MX700  71.4 🟠   │
│  [ALERT-143] Siêu âm GE     │  ...                                  │
│  High | Còn 32h             │                                        │
│  [Xem chi tiết] [Ack]       │                                        │
└─────────────────────────────┴──────────────────────────────────────┘
```

### Risk Heatmap Component — Spec Chi tiết

```
Component: <RiskHeatmap />

Props:
  assets: PredictionResult[]       -- danh sách assets với risk data
  groupBy: 'department' | 'category' | 'none'
  onAssetClick: (asset: string) => void

Layout:
  - Grid view, mỗi cell = 1 asset
  - Grouping: assets nhóm theo department (label header mỗi nhóm)
  - Cell size: 48×48px (desktop), 36×36px (tablet)
  - Cell content: Asset code (truncated) + score badge

Color Coding (Tailwind classes):
  Critical (score ≥ 85):  bg-red-600 text-white     🔴
  High (70–84):           bg-orange-400 text-white   🟠
  Medium (40–69):         bg-yellow-300 text-gray-800 🟡
  Low (< 40):             bg-green-400 text-white    🟢
  No data:                bg-gray-200 text-gray-400  ⬜

On Hover (tooltip):
  ┌────────────────────────────────┐
  │ ACC-2021-00041                  │
  │ Máy thở Ventilator Hamilton G5  │
  │ ICU — Score: 88.3 (Critical)    │
  │ Confidence: High (82%)          │
  │ Top risk: Downtime 8.2%         │
  │ [Xem chi tiết →]               │
  └────────────────────────────────┘

On Click: navigate to /imm17/assets/:id/risk

Legend:
  🟢 Low (< 40)  🟡 Medium (40–69)  🟠 High (70–84)  🔴 Critical (85+)
  ⬜ Không đủ dữ liệu

Filters:
  - Department dropdown (multi-select)
  - Asset Category dropdown
  - Risk tier checkboxes
  - Search by asset code/name
```

### KPI Cards

```
Component: <KpiCard />
Props: { label, value, unit, trend, sparklineData, status }

Card variants:
  - status: 'good' → green border + check icon
  - status: 'warning' → yellow border + warning icon
  - status: 'danger' → red border + alert icon

Trend indicator:
  ↑ Green arrow = improving
  ↓ Red arrow = worsening
  → Gray arrow = stable

Sparkline: 6-month mini line chart (no axes, just trend line)
```

### Staleness Warning Banner

```
IF prediction_age_days > 7:
  <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
    ⚠ Dữ liệu dự đoán đã {days} ngày tuổi (cập nhật lần cuối: {date}).
    Lịch chạy tiếp theo: {next_scheduled}. 
    <button>Chạy ngay</button>
  </div>
```

---

## 3. Screen 2 — Asset Risk Detail View

**Route:** `/imm17/assets/:id/risk`
**Mô tả:** Chi tiết risk score và factor breakdown cho một asset.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  ← Quay lại  |  ACC-2021-00041 — Máy thở Ventilator Hamilton G5       │
│              |  ICU · 70 tháng · Giá trị: 1.8 tỷ VNĐ                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  RISK SCORE                    ACTIVE ALERTS                           │
│  ┌─────────────────┐           ⚠ [ALERT-142] Failure Risk Critical    │
│  │   88.3          │           Created: 21/04 06:13 | Overdue 15.5h   │
│  │   CRITICAL 🔴   │           [Acknowledge →]                        │
│  │   Confidence:   │                                                   │
│  │   HIGH (82%)    │           RECOMMENDATION                          │
│  │   [Gauge chart] │           KHẨN CẤP: Thiết bị có nguy cơ hỏng    │
│  └─────────────────┘           rất cao. Đề xuất kiểm tra ngay và      │
│                                lên lịch CM.                            │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│  FACTOR BREAKDOWN                                                       │
│                                                                        │
│  Tỷ lệ downtime (weight 30%)                          24.6 / 30.0     │
│  ████████████████████████████████░░░░░░ 82.0           [Xem records →]│
│  Giá trị: 8.2% downtime trong 12 tháng                                │
│                                                                        │
│  Chi phí sửa chữa (weight 25%)                        21.0 / 25.0    │
│  █████████████████████████████████░░░░ 84.0            [Xem records →]│
│  Giá trị: 42.1% giá trị tài sản trong 12 tháng                        │
│                                                                        │
│  Tuổi thiết bị (weight 20%)                            11.7 / 20.0   │
│  ████████████████████░░░░░░░░░░░░░░░░ 58.3             [Xem IMM-04 →]│
│  Giá trị: 70 tháng                                                    │
│                                                                        │
│  Tuân thủ PM (weight 15%)                              3.3 / 15.0    │
│  ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 22.0 (đảo ngược) [Xem IMM-08 →]│
│  Giá trị: 78% compliance                                              │
│                                                                        │
│  Suy giảm MTBF (weight 10%)                            7.6 / 10.0   │
│  ██████████████████████████░░░░░░░░ 76.0               [Xem records →]│
│  Giá trị: 38% suy giảm (89d → 55d)                                    │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│  RISK SCORE TREND (6 tháng)         PM RECOMMENDATION                 │
│  [Line chart: Nov→Apr, upward]      Rút ngắn PM: 90d → 72d (-20%)    │
│  Trend: ↑ Tăng đều đặn              Confidence: Medium (78%)          │
│  Cần chú ý đặc biệt                 [Accept] [Reject] [Defer 30d]    │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│  LỊCH SỬ SỰ KIỆN (12 tháng)                         [Xem tất cả →]  │
│  CM-2026-00051  15/03/2026  Lỗi van thở  Downtime: 8h  Cost: 12M     │
│  PM-2026-00089  01/03/2026  PM định kỳ   Issues found: 2             │
│  CM-2025-00287  12/01/2026  Cảnh báo áp suất  Downtime: 4h  Cost: 8M │
└──────────────────────────────────────────────────────────────────────┘
```

### Chart Types

| Section | Chart Type | Library |
|---|---|---|
| Risk Score | Gauge / Radial chart | Chart.js (doughnut variant) |
| Factor Breakdown | Horizontal bar (progress) | Native CSS + Tailwind |
| Risk Score Trend | Line chart (6-month) | Chart.js |

### Gauge Chart — Color Zones

```
0–39:   Green zone  → text "Thấp"
40–69:  Yellow zone → text "Trung bình"
70–84:  Orange zone → text "Cao"
85–100: Red zone    → text "Nghiêm trọng"

Center text: score + tier label + confidence badge
```

---

## 4. Screen 3 — PM Optimization View

**Route:** `/imm17/pm-optimization`
**Mô tả:** Danh sách đề xuất tối ưu lịch PM, cho phép accept/reject.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  PM Optimization Recommendations                                        │
│  [Filter: All Status ▼] [Department ▼] [Sort: Confidence ▼]           │
│                                                                        │
│  14 đề xuất đang chờ review  (Accepted: 8, Rejected: 3, Deferred: 2) │
├──────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ 🔴 Máy thở Ventilator Hamilton G5 — ACC-2021-00041  ICU        │  │
│  │                                                                 │  │
│  │  Hiện tại: 90 ngày    →    Đề xuất: 72 ngày  (-20%)           │  │
│  │            ████████████    ██████████  [SHORTEN ↓]             │  │
│  │                                                                 │  │
│  │  Confidence: Medium (78%)  ●●●○○                               │  │
│  │  Lý do: 45% failures trong 30 ngày trước PM.                  │  │
│  │  Data: 8 PM cycles, 11 CM events analysed.                     │  │
│  │                                                                 │  │
│  │  [✓ Accept]  [✗ Reject]  [⏸ Defer 30d]  [📋 Chi tiết]        │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ 🟠 Monitor Bệnh nhân Philips MX700 — ACC-2022-00078  Ward B   │  │
│  │                                                                 │  │
│  │  Hiện tại: 180 ngày   →    Đề xuất: 216 ngày (+20%)           │  │
│  │            ████████████████  ████████████████████ [LENGTHEN ↑]│  │
│  │                                                                 │  │
│  │  Confidence: High (83%)  ●●●●○                                 │  │
│  │  Lý do: Chỉ 12% PM phát hiện vấn đề trong 12 tháng qua.      │  │
│  │  Data: 5 PM cycles, 4 CM events analysed.                      │  │
│  │                                                                 │  │
│  │  [✓ Accept]  [✗ Reject]  [⏸ Defer 30d]  [📋 Chi tiết]        │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### Accept/Reject Flow

```
On Accept:
  → Modal confirm: "Chấp nhận đề xuất thay đổi PM interval từ 90d → 72d?"
  → Note: "Điều này sẽ tạo Change Request cho HTM Manager phê duyệt."
  → [Xác nhận] → POST API → record status = Accepted
  → Toast: "Đề xuất đã được ghi nhận. Change Request đã tạo (CR-2026-00XX)"
  
On Reject:
  → Modal: "Lý do từ chối?" (required textarea)
  → [Xác nhận] → POST API → record status = Rejected, reason saved
  
On Defer:
  → No modal needed → POST API → snoozed 30 days
  → Toast: "Đề xuất sẽ xuất hiện lại vào {date+30}"
```

### Confidence Level Visual

```
Level    Indicator         Color
High     ●●●●●            text-green-600
Medium   ●●●○○            text-yellow-600
Low      ●○○○○            text-red-600
```

---

## 5. Screen 4 — Spare Parts Forecast View

**Route:** `/imm17/spare-forecast`
**Mô tả:** Bảng dự báo nhu cầu phụ tùng và thông tin đặt hàng.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  Dự báo Nhu cầu Phụ tùng                      [Xuất Excel]            │
│  Dự báo: 3 tháng tới (May–Jul 2026)                                   │
│  [Forecast Months: 3 ▼] [Device Model ▼] [Chỉ hiện cần đặt ☐]       │
├──────────────────────────────────────────────────────────────────────┤
│  SUMMARY BANNER                                                         │
│  ⚠ 12 phụ tùng cần đặt hàng (stock < reorder point)                  │
│  🚨 3 phụ tùng có nguy cơ stockout trong 14 ngày                      │
├──────────────────────────────────────────────────────────────────────┤
│                          Tháng 5  Tháng 6  Tháng 7  │Tồn kho│ Điểm  │
│  Mã phụ tùng / Tên        (dự báo)(dự báo)(dự báo)  │ Hiện  │ Đặt   │
├──────────────────────────────────────────────────────┼───────┼───────┤
│  🚨 SPARE-VENT-FILTER-001                            │       │       │
│  Bộ lọc vi khuẩn Hamilton G5                         │       │       │
│     10.5     9.8     11.2                            │  8    │  15   │
│  ⚠ Cần đặt 30 units  Lead time: 21 ngày             │       │       │
│  [📊 Xem biểu đồ]                                   │       │       │
├──────────────────────────────────────────────────────┼───────┼───────┤
│  ✓ SPARE-ECG-LEAD-003                               │       │       │
│  Dây điện tim 5-lead Philips                         │       │       │
│     12.0     12.0     12.0                           │  45   │  20   │
│  Đủ dự trữ — Đặt tiếp vào 15/06/2026               │       │       │
│  [📊 Xem biểu đồ]                                   │       │       │
├──────────────────────────────────────────────────────────────────────┤
│  [Trang 1/5]  [Xem tất cả]                                           │
└──────────────────────────────────────────────────────────────────────┘
```

### Status Indicators

```
🚨 Đỏ: Stockout risk trong 14 ngày (cần đặt khẩn)
⚠  Vàng: Below reorder point (cần đặt)
✓  Xanh: Stock adequate
⬜ Xám: Insufficient history
```

### Individual Part Forecast Chart (on expand)

```
Chart type: Line chart
X axis: Tháng (12 months history + 3 months forecast)
Series:
  - Actual consumption (solid line, blue)
  - Forecast (dashed line, orange)
  - Reorder point (horizontal dashed red line)
  - Stock level (step area, light green)

Annotations:
  - "Vùng dự báo" label on forecast period (shaded background)
  - Confidence band (upper/lower) shaded area
```

---

## 6. Screen 5 — Budget Forecast View

**Route:** `/imm17/budget-forecast`
**Mô tả:** Dự báo ngân sách bảo trì 12 tháng rolling với comparison vs. actual.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  Dự báo Ngân sách Bảo trì 12 Tháng                    [Xuất báo cáo] │
│  Tháng 5/2026 – Tháng 4/2027  ·  Fleet: 247 thiết bị                 │
│  [Department ▼] [Loại chi phí ▼] [So sánh với ngân sách ☐]          │
├──────────────────────────────────────────────────────────────────────┤
│  ANNUAL FORECAST TOTAL                                                  │
│  4,820,000,000 VNĐ                                                    │
│  Khoảng tin cậy: 4,097M – 5,543M VNĐ (±15%)                          │
│  Ngân sách được duyệt: 4,200M VNĐ  ⚠ VƯỢT DỰ BÁO +14.8%            │
├──────────────────────────────────────────────────────────────────────┤
│  STACKED BAR CHART (12 tháng)                                          │
│                                                                        │
│  700M │                          ████                                 │
│  600M │         ████  ████  ████ ████ ████                           │
│  500M │  ████  ████  ████  ████ ████ ████ ████ ████                 │
│  400M │  ████  ████  ████  ████ ████ ████ ████ ████ ████ ████ ████  │
│  300M │  ...                                                          │
│       └──────────────────────────────────────────────────────────────│
│       T5  T6  T7  T8  T9  T10 T11 T12 T1  T2  T3  T4               │
│       ◄───── Thực tế ─────►◄─────── Dự báo ──────────────────►      │
│                                                                        │
│  Chú thích: ■ PM  ■ CM  ■ Hiệu chuẩn  ■ Phụ tùng  ─ Confidence band│
├──────────────────────────────────────────────────────────────────────┤
│  BREAKDOWN TABLE                                                        │
│  Tháng     PM Cost   CM Cost  CAL Cost  Parts Cost   Tổng   So sánh │
│  T4/2026   118M      94M      21M       134M         367M   (actual) │
│  T5/2026   125M      87M      23M       156M         391M   +6.5%    │
│  T6/2026   118M      92M      45M       149M         404M   (CAL tăng)│
│  ...                                                                  │
├──────────────────────────────────────────────────────────────────────┤
│  [Phân tích kịch bản What-If →]  "Nếu thay 10 máy cũ → tiết kiệm?" │
└──────────────────────────────────────────────────────────────────────┘
```

### Chart Specification

```
Chart type: Stacked bar chart (Chart.js)
Datasets:
  - PM Cost: bg-blue-400
  - CM Cost: bg-orange-400
  - Calibration: bg-purple-400
  - Parts Cost: bg-teal-400
  - Confidence upper (line): dashed gray
  - Confidence lower (line): dashed gray
  - Budget line (horizontal): dashed red

X-axis: Month labels
Y-axis: VNĐ (millions, formatted as "400M")

Interactivity:
  - Hover: tooltip với breakdown chi tiết
  - Click on bar: drill-down modal với WO list cho tháng đó
  - Toggle datasets via legend

Actual vs. Forecast split:
  - Past months: solid fill
  - Future months: hatched/lighter fill + "DỰ BÁO" label
```

---

## 7. Screen 6 — What-If Analysis View

**Route:** `/imm17/what-if`
**Mô tả:** Scenario builder và impact simulation.

### Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  Phân tích Kịch bản What-If                                            │
│  [+ Tạo kịch bản mới]  [Lịch sử kịch bản ▼]                         │
├─────────────────────────────┬──────────────────────────────────────┤
│  SCENARIO BUILDER            │  SIMULATION RESULTS                    │
│                              │                                        │
│  Tên kịch bản:               │  [Chưa chạy — điền thông tin và       │
│  [Giảm PM interval Vent 20%] │   nhấn "Chạy mô phỏng"]              │
│                              │                                        │
│  Loại thay đổi:              │                                        │
│  ○ PM Interval               │                                        │
│  ○ Fleet Reduction           │                                        │
│  ○ Parts Cost                │                                        │
│  ○ Staff Capacity            │                                        │
│                              │                                        │
│  Phạm vi:                    │                                        │
│  [Device Model ▼]            │                                        │
│  [Hamilton G5      ________] │                                        │
│                              │                                        │
│  Mức thay đổi:               │                                        │
│  [-20  %]  ← Giảm 20%       │                                        │
│                              │                                        │
│  Ghi chú:                    │                                        │
│  [Phân tích cho Q2...]       │                                        │
│                              │                                        │
│  [▶ Chạy mô phỏng]          │                                        │
└─────────────────────────────┴──────────────────────────────────────┘
```

### After Simulation Completes

```
┌─────────────────────────────┬──────────────────────────────────────┐
│  SCENARIO BUILDER            │  KẾT QUẢ MÔ PHỎNG                   │
│  [Tên: Giảm PM Vent 20%]    │  "Giảm PM interval 20% (90d → 72d)  │
│  ...                         │  cho 12 máy thở Hamilton G5"         │
│                              │                                        │
│                              │  ┌─────────────────────────────────┐ │
│                              │  │ BEFORE    │    AFTER   │ DELTA  │ │
│                              │  ├───────────┼────────────┼────────┤ │
│                              │  │Chi phí/năm│ Chi phí/năm│        │ │
│                              │  │1,240M VNĐ │ 1,327M VNĐ│+87M ↑  │ │
│                              │  ├───────────┼────────────┼────────┤ │
│                              │  │Failure rate│Failure rate│       │ │
│                              │  │2.8/100    │ 1.96/100   │-30% ↓  │ │
│                              │  ├───────────┼────────────┼────────┤ │
│                              │  │Downtime   │ Downtime   │        │ │
│                              │  │312 h/năm  │ 218 h/năm  │-94h ↓  │ │
│                              │  ├───────────┼────────────┼────────┤ │
│                              │  │Spare demand│Spare demand│       │ │
│                              │  │420 units  │ 445 units  │+25 ↑   │ │
│                              │  └─────────────────────────────────┘ │
│                              │                                        │
│                              │  Interpretation:                       │
│                              │  "Tăng 87M VNĐ/năm để giảm 94 giờ   │
│                              │  downtime và 30% tỷ lệ hỏng hóc."    │
│                              │                                        │
│                              │  ⚠ Kết quả ước tính ±15%            │
│                              │  ⚠ Không dùng như cam kết ngân sách  │
│                              │  Hết hạn: 21/07/2026                  │
│                              │                                        │
│                              │  [💾 Lưu kịch bản]  [📤 Xuất PDF]  │
│                              │  [📧 Chia sẻ link]                   │
└─────────────────────────────┴──────────────────────────────────────┘
```

### Scenario Builder — Form Spec

```vue
<!-- WhatIfScenarioBuilder.vue -->
<template>
  <form @submit.prevent="runSimulation">
    <!-- Scenario Type Radio Group -->
    <RadioGroup v-model="form.scenario_type" :options="scenarioTypes" />
    
    <!-- Dynamic Scope Picker based on scenario_type -->
    <ScopePicker
      v-model="form.scope"
      :scenario-type="form.scenario_type"
    />
    
    <!-- Change Value Slider + Input -->
    <div class="flex items-center gap-4">
      <input type="range" v-model="form.change_value" :min="-50" :max="50" />
      <input type="number" v-model="form.change_value" class="w-20" />
      <span>%</span>
    </div>
    
    <!-- Real-time preview of what will change -->
    <ScenarioPreview :form="form" />
    
    <Button type="submit" :loading="isSimulating" :disabled="!isFormValid">
      {{ isSimulating ? 'Đang mô phỏng...' : '▶ Chạy mô phỏng' }}
    </Button>
  </form>
</template>
```

---

## 8. Pinia Store — `useImm17Store.ts`

```typescript
// stores/imm17.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  DashboardData,
  AssetRiskDetail,
  PmRecommendation,
  SpareForecast,
  BudgetForecast,
  WhatIfResult,
  PredictiveAlert,
  AlertConfig,
} from '@/types/imm17'

export const useImm17Store = defineStore('imm17', () => {
  // --- State ---
  const dashboardData = ref<DashboardData | null>(null)
  const assetRiskMap = ref<Map<string, AssetRiskDetail>>(new Map())
  const pmRecommendations = ref<PmRecommendation[]>([])
  const spareForecasts = ref<SpareForecast[]>([])
  const budgetForecast = ref<BudgetForecast | null>(null)
  const activeAlerts = ref<PredictiveAlert[]>([])
  const whatIfResults = ref<Map<string, WhatIfResult>>(new Map())
  
  // Loading states
  const isLoadingDashboard = ref(false)
  const isLoadingAsset = ref(false)
  const isRunningSimulation = ref(false)
  const isRunningPrediction = ref(false)
  
  // Error states
  const dashboardError = ref<string | null>(null)
  
  // Filters
  const activeFilters = ref({
    department: '',
    assetCategory: '',
    riskTier: 'All',
  })

  // --- Computed ---
  const criticalAlertCount = computed(
    () => activeAlerts.value.filter(a => a.severity === 'Critical').length
  )

  const overdueAlertCount = computed(
    () => activeAlerts.value.filter(a => a.is_overdue).length
  )

  const heatmapData = computed(() => {
    const data = dashboardData.value?.heatmap_data ?? []
    if (activeFilters.value.department) {
      return data.filter(a => a.department === activeFilters.value.department)
    }
    return data
  })

  const pmRecommendationsPending = computed(
    () => pmRecommendations.value.filter(r => r.status === 'Pending')
  )

  // --- Actions ---
  async function fetchDashboard(filters = {}) {
    isLoadingDashboard.value = true
    dashboardError.value = null
    try {
      const response = await fetch(
        `/api/method/assetcore.api.imm17.get_failure_risk_dashboard?${new URLSearchParams(filters)}`
      )
      const json = await response.json()
      dashboardData.value = json.message.data
    } catch (err) {
      dashboardError.value = 'Không thể tải dữ liệu dashboard'
    } finally {
      isLoadingDashboard.value = false
    }
  }

  async function fetchAssetRisk(assetId: string) {
    isLoadingAsset.value = true
    try {
      const response = await fetch(
        `/api/method/assetcore.api.imm17.get_asset_risk_score?asset=${assetId}&include_history=true`
      )
      const json = await response.json()
      assetRiskMap.value.set(assetId, json.message.data)
    } finally {
      isLoadingAsset.value = false
    }
  }

  async function fetchPmRecommendations(filters = {}) {
    const response = await fetch(
      `/api/method/assetcore.api.imm17.get_pm_recommendations?${new URLSearchParams(filters)}`
    )
    const json = await response.json()
    pmRecommendations.value = json.message.data.recommendations
  }

  async function acceptPmRecommendation(resultId: string) {
    const response = await fetch(
      '/api/method/assetcore.api.imm17.accept_pm_recommendation',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prediction_result: resultId }),
      }
    )
    if (response.ok) {
      const rec = pmRecommendations.value.find(r => r.prediction_result === resultId)
      if (rec) rec.status = 'Accepted'
    }
  }

  async function acknowledgeAlert(alertName: string, actionTaken: string) {
    const response = await fetch(
      '/api/method/assetcore.api.imm17.acknowledge_alert',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_name: alertName, action_taken: actionTaken }),
      }
    )
    if (response.ok) {
      const alert = activeAlerts.value.find(a => a.name === alertName)
      if (alert) alert.status = 'Acknowledged'
    }
  }

  async function runWhatIfAnalysis(scenario: Record<string, unknown>) {
    isRunningSimulation.value = true
    try {
      const response = await fetch(
        '/api/method/assetcore.api.imm17.run_what_if_analysis',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(scenario),
        }
      )
      const json = await response.json()
      const result = json.message.data
      whatIfResults.value.set(result.scenario_name, result)
      return result
    } finally {
      isRunningSimulation.value = false
    }
  }

  async function fetchActiveAlerts(filters = {}) {
    const response = await fetch(
      `/api/method/assetcore.api.imm17.get_active_alerts?${new URLSearchParams(filters)}`
    )
    const json = await response.json()
    activeAlerts.value = json.message.data.alerts
  }

  function setFilter(key: string, value: string) {
    activeFilters.value = { ...activeFilters.value, [key]: value }
  }

  function resetFilters() {
    activeFilters.value = { department: '', assetCategory: '', riskTier: 'All' }
  }

  return {
    // State
    dashboardData,
    assetRiskMap,
    pmRecommendations,
    spareForecasts,
    budgetForecast,
    activeAlerts,
    whatIfResults,
    isLoadingDashboard,
    isLoadingAsset,
    isRunningSimulation,
    isRunningPrediction,
    dashboardError,
    activeFilters,
    // Computed
    criticalAlertCount,
    overdueAlertCount,
    heatmapData,
    pmRecommendationsPending,
    // Actions
    fetchDashboard,
    fetchAssetRisk,
    fetchPmRecommendations,
    acceptPmRecommendation,
    acknowledgeAlert,
    runWhatIfAnalysis,
    fetchActiveAlerts,
    setFilter,
    resetFilters,
  }
})
```

---

## 9. Data Refresh Strategy

### Polling vs SSE

| Data Type | Strategy | Interval | Rationale |
|---|---|---|---|
| Dashboard KPIs | Polling | 5 phút | Predictions chạy weekly — không cần realtime |
| Active Alerts count | Polling | 60 giây | Alerts có thể được tạo daily job |
| Active Alerts list | Polling | 2 phút | User cần biết kịp thời |
| Budget / Spare forecast | On demand | -- | Heavy data, chỉ load khi user mở |
| PM recommendations | On demand | -- | Ổn định, không cần live update |
| What-If result | SSE / polling | 5 giây khi running | Show progress indicator |

### Alert Polling Component

```typescript
// composables/useAlertPolling.ts
export function useAlertPolling(intervalMs = 60_000) {
  const store = useImm17Store()
  let intervalId: ReturnType<typeof setInterval> | null = null

  function start() {
    store.fetchActiveAlerts()
    intervalId = setInterval(() => {
      store.fetchActiveAlerts()
    }, intervalMs)
  }

  function stop() {
    if (intervalId) clearInterval(intervalId)
  }

  onMounted(start)
  onUnmounted(stop)

  return { start, stop }
}
```

---

## 10. Loading States

### Long-Running Prediction State

```
Loading skeleton khi fetchDashboard():
  - KPI cards: 5 gray skeleton blocks
  - Heatmap: Gray grid with shimmer animation
  - Alert list: 3 skeleton rows

Loading state khi runWhatIfAnalysis():
  - Button: "▶ Đang mô phỏng..." với spinner
  - Results panel: progress indicator
  - "Đang tính toán kịch bản cho 12 thiết bị..."

No data state:
  <EmptyState
    icon="chart-bar"
    title="Chưa có dữ liệu dự đoán"
    message="Chạy prediction model lần đầu để xem kết quả."
    action="Chạy ngay"
    @action="triggerPredictionRun"
  />

Insufficient data state (per asset cell in heatmap):
  Cell: bg-gray-200, tooltip "Chưa đủ dữ liệu — cần 6+ tháng vận hành"
```

---

## 11. Vue Router Configuration

```typescript
// router/imm17.routes.ts
import { RouteRecordRaw } from 'vue-router'

export const imm17Routes: RouteRecordRaw[] = [
  {
    path: '/imm17',
    component: () => import('@/layouts/Imm17Layout.vue'),
    meta: { module: 'IMM-17', requiresAuth: true },
    children: [
      {
        path: 'cockpit',
        name: 'Imm17Cockpit',
        component: () => import('@/views/imm17/CockpitView.vue'),
        meta: { title: 'Predictive Cockpit', roles: ['HTM Engineer', 'HTM Manager', 'Innovation Center', 'QLCL'] },
      },
      {
        path: 'assets/:id/risk',
        name: 'Imm17AssetRisk',
        component: () => import('@/views/imm17/AssetRiskDetailView.vue'),
        meta: { title: 'Asset Risk Detail', roles: ['HTM Engineer', 'HTM Manager', 'Workshop', 'Innovation Center'] },
      },
      {
        path: 'pm-optimization',
        name: 'Imm17PmOptimization',
        component: () => import('@/views/imm17/PmOptimizationView.vue'),
        meta: { title: 'PM Optimization', roles: ['HTM Engineer', 'HTM Manager'] },
      },
      {
        path: 'spare-forecast',
        name: 'Imm17SpareForecast',
        component: () => import('@/views/imm17/SpareForecastView.vue'),
        meta: { title: 'Spare Parts Forecast', roles: ['Workshop', 'Warehouse', 'HTM Manager'] },
      },
      {
        path: 'budget-forecast',
        name: 'Imm17BudgetForecast',
        component: () => import('@/views/imm17/BudgetForecastView.vue'),
        meta: { title: 'Budget Forecast', roles: ['KH-TC', 'HTM Manager', 'BGĐ', 'QLCL'] },
      },
      {
        path: 'what-if',
        name: 'Imm17WhatIf',
        component: () => import('@/views/imm17/WhatIfView.vue'),
        meta: { title: 'What-If Analysis', roles: ['HTM Manager', 'KH-TC', 'Innovation Center'] },
      },
    ],
  },
]
```

---

*File tiếp theo: IMM-17_UAT_Script.md*
