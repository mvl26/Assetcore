# 06 — Thiết kế Frontend (IMM-07 — Theo dõi hiệu suất)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Trạng thái | Skeleton — FE chưa scaffold (Wave 3) |
| Stack | Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query |
| Cập nhật | 2026-05-10 |

> Tham chiếu design system: [`../res/design/design-frontend.md`](../res/design/design-frontend.md). Pattern FE: skill [`assetcore-fe-module`](../../.claude/skills/assetcore-fe-module/SKILL.md).

---

## 1. Sitemap / Route map

| Route | Mô tả | Role chính |
|---|---|---|
| `/imm-07` | Cockpit hiệu suất (overview KPI tổng hợp) | BGĐ / QLCL / Workshop |
| `/imm-07/snapshots` | Danh sách KPI snapshot theo chu kỳ | QLCL / Workshop |
| `/imm-07/snapshots/:id` | Chi tiết snapshot + KPI value + drill-down event nguồn | QLCL / Workshop |
| `/imm-07/signals` | Danh sách replacement signal | QLCL / BGĐ |
| `/imm-07/signals/:id` | Chi tiết signal + lịch sử KPI + action xử lý | QLCL |
| `/imm-07/catalog` | Quản trị KPI catalog (admin) | QLCL |
| `/imm-07/rules` | Quản trị performance rule (admin) | QLCL |

## 2. Sidebar nav module

Group "Vận hành" → mục "Hiệu suất" với 4 sub: Cockpit, Snapshots, Signals, Cấu hình (Catalog + Rules).

## 3. Thiết kế giao diện

### 3.a. UI Mockup (pre-build)

*(Wireframe sẽ chèn ở `docs/ba/Phase_06_UX_Screen_Dashboard_Design/imm-07/` — bổ sung Wave 3 sprint 1)*

### 3.b. UI Screenshot (post-build)

*(Cập nhật mỗi release)*

## 3.c. Trang chi tiết theo archetype

### 3.1. Cockpit (`/imm-07`)

- Hero metrics: Availability, Utilization, Downtime, MTBF, MTTR (toàn viện).
- Heatmap khoa × KPI theo tháng gần nhất.
- Top 10 thiết bị có signal đang mở.
- Filter: chu kỳ (ngày/tuần/tháng/quý), khoa, model.

### 3.2. List Snapshot (`/imm-07/snapshots`)

- Table: Period · Scope · Status (Draft/Computed/Verified/Closed) · Verified by · Action.
- Filter: status, period range, scope.
- Bulk action: verify (cho QLCL).

### 3.3. Detail Snapshot (`/imm-07/snapshots/:id`)

- Header: scope, period, status, audit (created/verified by).
- KPI value table (mỗi row là 1 KPI + value + threshold + sparkline 6 chu kỳ).
- Drill-down 1-click → list event nguồn (mở dialog hoặc link sang IMM-08/09/11/12).
- Button: Verify (4-mắt) / Reopen (có quyền).

### 3.4. List Signal (`/imm-07/signals`)

- Table: Asset · Rule · Period vi phạm · Status · Khuyến nghị.
- Filter: status (Open/Reviewing/Resolved/Dismissed), khoa.

### 3.5. Detail Signal (`/imm-07/signals/:id`)

- Asset card + KPI timeseries (chart).
- Rule áp dụng + threshold + chu kỳ vi phạm.
- Action: Resolve (kèm resolution: replace / repair / monitor) hoặc Dismiss (kèm lý do).

## 4. Component custom của module

- `KpiCard.vue` — hero metric card.
- `KpiHeatmap.vue` — khoa × KPI matrix.
- `KpiSparkline.vue` — mini chart 6 chu kỳ.
- `SignalSeverityBadge.vue` — badge theo mức độ.
- `EventDrillDownDialog.vue` — modal show event nguồn.

## 5. Pinia store

`stores/imm07.ts` — state: `currentSnapshot`, `cockpitData`, `signalList`. Actions tương ứng API calls. Refer pattern store skill `assetcore-fe-module`.

## 6. Vue Query keys

- `['imm07','cockpit', filters]`
- `['imm07','snapshots','list', filters]`
- `['imm07','snapshot','detail', id]`
- `['imm07','signals','list', filters]`
- `['imm07','signal','detail', id]`

## 6b. API call pattern

Dùng `useApi().run()` wrap (refer skill `assetcore-fe-module`). Mọi error map qua `ErrorCode` enum để hiển thị i18n.

## 6c. TypeScript types

Folder `frontend/src/types/imm07/`:
- `snapshot.ts`, `kpi.ts`, `signal.ts`, `rule.ts`.

*(Sinh khi FE scaffold Wave 3)*.

## 7. Quy tắc ngôn ngữ FE

### 7.a. Nguyên tắc cứng

- Tiếng Việt cho user-facing label (BGĐ / QLCL / Workshop).
- KPI tên hiển thị: tiếng Việt + viết tắt EN trong ngoặc (vd "Khả dụng (Availability)").

### 7.b. Entity display pattern

- Snapshot: `<period> · <scope>` (vd "Tháng 4/2026 · Khoa CĐHA").
- Signal: `<asset_id> · <rule_code>` (vd "AS-2024-00321 · MTBF-DROP").

### 7.c. Bảng từ ngữ chuẩn

Refer chung `docs/res/design/design-frontend.md` §"Glossary". Bổ sung:

| EN | VN |
|---|---|
| Availability | Tỷ lệ khả dụng |
| Utilization | Tỷ lệ sử dụng |
| Downtime | Thời gian dừng |
| MTBF | Thời gian giữa hai sự cố |
| MTTR | Thời gian sửa chữa |
| Replacement signal | Cảnh báo thay thế |
| Snapshot | Bản chốt KPI |

## 7d. Cascade fields

- Filter cockpit: `Khoa → Phòng → Vị trí → Asset` (cascade từ IMM-04 location tree).
- Khi đổi `Khoa`, reset `Phòng/Vị trí/Asset`.

## 7e. Input tight

- Period: dùng date-range picker với preset (tháng này / tháng trước / quý này / năm).
- Scope: dropdown picker, không free-text.
- Lý do dismiss/resolve: textarea bắt buộc ≥ 20 ký tự.

---

## DoD — File 06 (IMM-07)

- [x] Sitemap 7 route
- [x] Component list
- [x] Pinia store + Query keys
- [x] i18n glossary
- [ ] *(Pending: wireframe Wave 3 sprint 1, screenshot post-build)*
