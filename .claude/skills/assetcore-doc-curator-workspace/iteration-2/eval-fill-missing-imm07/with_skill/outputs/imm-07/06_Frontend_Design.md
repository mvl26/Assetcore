# IMM-07 — Thiết kế Frontend

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Stack | Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query |
| Trạng thái | Skeleton (FE bám theo BE Wave 3.1) |

## I. Sitemap (route)

| Route | View | Actor mục tiêu |
|---|---|---|
| `/imm-07` | Dashboard tổng | Mọi role có quyền |
| `/imm-07/scorecard` | Scorecard điều hành (toàn viện) | BGĐ |
| `/imm-07/department/:deptId` | Dashboard theo khoa | Trưởng khoa, PTP |
| `/imm-07/asset/:assetId` | Drill-down KPI 1 asset | PTP, Kỹ thuật viên |
| `/imm-07/data-quality` | Hàng đợi flag cần xác minh | Data Steward, Kỹ thuật viên |
| `/imm-07/replacement-signal` | Inbox tín hiệu thay thế | KPI Owner, IMM-13 owner |
| `/imm-07/kpi-definition` | Quản lý định nghĩa KPI + version | KPI Owner |

## II. Components & Stores

| Loại | Tên | Mục đích |
|---|---|---|
| Store | `useImm07Store` | KPI summary + dashboard cache |
| Store | `useReplacementSignalStore` | Inbox + acknowledge action |
| Composable | `useKpiHistory(assetId, range)` | TanStack query lịch sử KPI |
| Composable | `useDepartmentScope` | Lọc data theo permission khoa |
| Component | `KpiCard.vue` | Card hiển thị 1 KPI + trend |
| Component | `KpiTrendChart.vue` | Line chart 12 tháng |
| Component | `DataQualityFlagTable.vue` | Bảng flag với action verify |
| Component | `ReplacementSignalList.vue` | List + detail panel |
| Component | `KpiFormulaEditor.vue` | Form định nghĩa KPI có version |

## III. Cascade fields

Trong dashboard và filter:

```
Khoa (Department)
  └─ Loại thiết bị (Device Model Class)
       └─ Asset
            └─ Kỳ (period: month / quarter / year)
```

Cascade dropdown lazy-load qua API IMM-04/05 master data, không gọi lại API IMM-07.

## IV. Validation

| Trường | Rule |
|---|---|
| KPI period range | Bắt buộc, max 24 tháng |
| Manual override value | Bắt buộc justification text ≥ 20 ký tự |
| Replacement signal acknowledge | Bắt buộc chọn root cause from enum |
| KPI formula | Validate trên BE (không cho phép sửa tại FE bypass) |

## V. UX & Design system

Mọi component bám theo design system tại `docs/res/design-frontend.md` (typography, spacing, color tokens).

Đặc điểm UI IMM-07:
- Dashboard ưu tiên density cao (BGĐ scan nhanh) — dùng `KpiCard` compact mode.
- Trend chart dùng màu warning/danger khi vượt ngưỡng (gắn với threshold từ BE).
- Replacement signal có badge severity (Info / Warning / Critical).
- Mobile responsive ở mức xem-only (không tối ưu form trên mobile).

## VI. Quyền hiển thị

UI hide/show theo role (FE check + BE re-check):
- BGĐ chỉ thấy aggregated, ẩn drill-down asset chi tiết của khoa khác.
- Trưởng khoa chỉ thấy khoa được gán.
- Kỹ thuật viên Workshop xem được tất cả nhưng action verify chỉ trong scope khoa.

## VII. Mockup

*(Wireframe — designer cập nhật trong Phase_06, refer `docs/ba/Phase_06_UX_Screen_Dashboard_Design/`)*

## VIII. Tham chiếu

- Skill build: `.claude/skills/assetcore-fe-module/SKILL.md`
- Component patterns: `.claude/skills/assetcore-fe-module/references/component-patterns.md`
- Design system: `docs/res/design-frontend.md`
