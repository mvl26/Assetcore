# AssetCore Frontend — Design System & UI Specifications

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | Hệ thống thiết kế giao diện AssetCore (HTM Operating System) |
| Phiên bản | 2.0.0 |
| Ngày | 2026-05-07 |
| Phạm vi | Toàn bộ FE Vue 3 — sidebar module-scoped + 17 IMM modules + master/system/audit |
| Ground-truth | `frontend/tailwind.config.js`, `frontend/src/assets/styles/main.css`, `frontend/src/components/common/*` (21 file), `frontend/src/composables/*` (10 file), `frontend/src/router/index.ts` |
| Mục đích | Single source of truth cho mọi quyết định giao diện. Khi thiết kế trang mới, đọc tài liệu này trước khi xem các view sẵn có. |

---

## 0. Triết lý thiết kế

AssetCore phục vụ kỹ sư y sinh, điều dưỡng, lãnh đạo phòng VTYT và kiểm toán viên — những người **không** có thời gian học UI cầu kỳ. Mỗi quyết định thiết kế phải trả lời được 3 câu hỏi:

1. **Người dùng đang ở đâu trong vòng đời thiết bị?** (Needs · Procurement · Install · Operation · Maintenance · Decommission)
2. **Họ cần làm gì tiếp theo?** (CTA chính, không quá 1 trên mỗi vùng nhìn)
3. **Hành động này có để lại dấu vết không?** (mọi mutation phải có audit trail — UI phản ánh điều đó)

Định hướng tổng thể — gọi tắt là **"clinical dossier"**:

- **Mật độ thông tin cao nhưng có nhịp thở** — bảng dữ liệu là trung tâm, không phải card lớn lòe loẹt.
- **Số là ngôi sao** — KPI, đo lường, mã thiết bị đều dùng JetBrains Mono `tabular-nums`. Mọi chữ thường-text khác là sân nền cho con số.
- **Màu = cảnh báo, không phải trang trí** — đỏ = breach, hổ phách = warning, xanh lá = pass. Brand-600 chỉ dành cho CTA và wayfinding.
- **Tiếng Việt là primary** — mọi label, error, action đều tiếng Việt; tiếng Anh chỉ trong code/symbol.
- **Audit trail có mặt khắp nơi** — mỗi DocType detail có panel "Lịch sử" dạng timeline. Không record nào "biến mất khỏi UI mà không để lại dấu".
- **Vòng đời là thanh dẫn hướng** — sidebar đổi context theo IMM module, không gom mọi route vào 1 cây. Module accent stripe là tín hiệu định hướng nhanh.

Khi phân vân: chọn phương án **nhanh nhận biết** thay vì phương án **đẹp**. KTV trực ca đêm cần thấy WO breach SLA trong 1 giây.

---

## 1. Design tokens (đã hiện thực hóa)

Tokens dưới đây đã có trong `tailwind.config.js` + `main.css`. **Không tạo token mới** — extend tokens sẵn có nếu thiếu.

### 1.1. Bảng màu

| Token | Hex | Dùng cho |
|---|---|---|
| `brand-50` → `brand-950` | `#eff6ff` → `#172554` | Brand primary (xanh dương). `brand-600` `#2563eb` là CTA chính. |
| `ink-50` → `ink-900` | `#f0f6fc` → `#0d1117` | Văn bản + neutral surface tối (sidebar dark mode reserve). |
| `slate-*` (Tailwind core) | — | Neutral chính cho text, border, surface |
| `emerald-600` `#059669` | — | Success / completed / passed |
| `amber-600` `#d97706` | — | Warning / pending / overdue soft |
| `red-600` `#dc2626` | — | Danger / failed / cancel / SLA breached |
| `--color-bg` `#f4f6fa` | — | Page background (gần trắng pha xanh lạnh) |
| `--color-surface` `#ffffff` | — | Card, modal, panel |
| `--color-border` `#e2e8f0` / `--color-border-strong` `#cbd5e1` | — | Border thường / divider mạnh |

CSS vars semantic (đã có trong `:root`): `--color-primary`, `--color-success`, `--color-warning`, `--color-danger`, `--color-neutral`, `--color-text-primary` `#0f172a`, `--color-text-secondary` `#475569`, `--color-text-muted` `#94a3b8`. Khi viết CSS thuần dùng vars; khi viết Tailwind dùng class scale.

**Quy tắc đậm-nhạt:**
- Text chính: `text-slate-900`. Phụ: `text-slate-600`. Mờ: `text-slate-400`. Disabled: `text-slate-300`.
- Border thường: `border-slate-200`. Strong / divider mạnh: `border-slate-300`.

**Cấm:**
- Đặt `bg-brand-600` cho card lớn (>200×200px) — chói, không dành cho thiết bị y tế.
- Trộn 2 màu accent trong cùng một widget (tím + cam, xanh lá + xanh dương, …).
- Đổi lại `--color-bg` thành trắng tinh — `#f4f6fa` là lớp đệm để card trắng nổi lên; mất nó là mất phân tầng.

### 1.2. Typography

| Cấp | Font | Size | Weight | Dùng cho |
|---|---|---|---|---|
| H1 | Manrope | `text-xl` (1.3125rem ≈ 19.7px) | `font-semibold` | PageHeader title |
| H2 | Manrope | `text-lg` (1.1875rem ≈ 17.8px) | `font-semibold` | Section trong trang |
| H3 | Manrope | `text-base` (1.0625rem ≈ 15.9px) | `font-semibold` | Card title |
| Body | Inter | `text-base` (1.0625rem) | `font-normal` | Mọi nội dung |
| Small | Inter | `text-sm` (0.9375rem ≈ 14px) | — | Subtitle, caption |
| Tiny | Inter | `text-xs` (0.8125rem ≈ 12.2px) | — | Badge, breadcrumb, metadata |
| Code / số | JetBrains Mono | match context | — | Mã WO, serial, số liệu KPI |

Base size 15px (`html { font-size: 15px }` trong `main.css`) — KHÔNG đổi. Bệnh viện dùng nhiều màn hình 24"–27" nên 15px cân giữa mật độ + đọc xa.

Inter feature settings đã enable: `'cv02', 'cv03', 'cv04', 'cv11'` (chữ số nhất quán 0/1/I, hình dạng `g/l` rõ hơn). Manrope giữ tracking `-0.015em` (đã set ở h1-h4) để header đặc, không loãng.

### 1.3. Spacing & Radius

```
Spacing scale (Tailwind):  1=4px  2=8px  3=12px  4=16px  5=20px  6=24px  7=28px  8=32px
Card padding mặc định:     p-7 (28px). Card-sm: p-4 (16px).
Page padding:              page-container → px-4 sm:px-6 lg:px-8 py-6 md:py-7
Gap giữa card trong grid:  gap-4 (16px) cho dense, gap-6 (24px) cho landing
Radius:
  --radius-card: 10px      → mọi card, modal, alert
  --radius-btn:  7px       → mọi button
  rounded-md (6px)         → input, badge nhỏ
  rounded-lg (8px)         → input lớn, table-wrapper
  rounded-full             → avatar, status dot
```

### 1.4. Shadows

| Token | Khi dùng |
|---|---|
| `shadow-card` | Card mặc định (rất nhẹ, viền 1px ưu thế) |
| `shadow-card-hover` | Hover trên card-interactive |
| `shadow-dropdown` | Menu, popover, suggestion list |
| `shadow-focus` | Ring focus xanh nhạt — đã set ở `*:focus-visible` (3px rgba brand-600/20%) |
| `shadow-topbar` | Đường kẻ dưới topbar |
| `shadow-sidebar` | Hairline phải sidebar (chuẩn bị cho dark theme) |

**Không dùng:**
- `shadow-2xl`, `drop-shadow-*` — quá nặng cho UI nội bộ.
- Nhiều layer shadow phức tạp — hệ thống y tế ưu tiên đơn giản.

### 1.5. Animation

Đã có sẵn 8 keyframes (`fadeIn`, `slideUp`, `slideIn`, `scaleIn`, `shimmer`, `pulseSubtle`, `barFill`, `spin-slow`).

**Quy tắc dùng:**
- Trang vào: `animate-fade-in` (250ms) cho container cấp cao nhất. Không lồng nhiều fade-in.
- List item xuất hiện: `animate-slide-up` + class `stagger-N` (40ms × N, đã có 1→8 trong `main.css`) để có hiệu ứng đợt.
- Skeleton load: `.skeleton::after` (shimmer) — đã wired.
- Modal mở: `animate-scale-in` (200ms).
- KPI số đếm tăng: `animate-bar-fill` cho progress; số dùng tween JS tối đa 600ms (không bắt buộc — hệ thống y tế chấp nhận số thay thẳng).
- **Cấm** animation > 400ms cho UI control. Cảm giác chậm → bệnh viện thấy hệ thống yếu.
- **Cấm** parallax, scroll-triggered fade khắp trang — gây mệt khi xem 8h/ca.

---

## 2. Layout & cấu trúc khung

### 2.1. App shell

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [☰]  AssetCore · IMM-09 — Sửa chữa (CM)         🔍 Search   🔔³  👤 ▾ │ ← AppTopBar   56px
├──┬──────────────────────────────────────────────────────────────────────┤
│  │                                                                       │
│ S│                          PAGE CONTAINER                              │
│ I│                                                                       │
│ D│   PageHeader                                                         │
│ E│   ─────────────────────────                                          │
│ B│   Filters / Tabs                                                     │
│ A│   ─────────────────────────                                          │
│ R│   Content (table | grid | form | dashboard)                         │
│  │                                                                       │
│  │                                                                       │
└──┴──────────────────────────────────────────────────────────────────────┘
   256px / 64px collapsed
```

**File thực tế** (không có thư mục `layouts/`):
- Khung được lắp trong `frontend/src/components/common/AppLayout.vue` — bọc `<AppSidebar />` + `<AppTopBar />` + `<router-view />` + `<ToastContainer />`.
- `App.vue` quyết định khi nào hiện shell vs khi nào render route trần (login). Auth view (`views/auth/LoginView.vue`, `RegisterView.vue`) tự render layout của riêng nó — **không** có file `AuthLayout.vue` riêng. Khi cần thêm auth route mới, copy pattern từ `LoginView.vue`, không tạo layout file mới.
- Hub launcher (`views/modules/...` — Module Hub) dùng cùng `AppLayout` nhưng `<AppSidebar />` đọc `route.meta.moduleId === undefined` và collapse về dạng minimal — **không** có `LauncherLayout.vue` riêng.

Kích thước cố định:
- **Sidebar**: `--sidebar-width: 256px` (mở), `--sidebar-collapsed-width: 64px` (gập). Toggle bằng `useSidebar()` composable, lưu vào localStorage qua `pinia-plugin-persistedstate`.
- **Topbar**: `--topbar-height: 56px`. Cố định (sticky). Đường kẻ dưới `shadow-topbar`.
- **Content**: chiếm phần còn lại. `page-container` đã wrap padding chuẩn.

### 2.2. Sidebar module-scoped

Đặc trưng nhận diện AssetCore: sidebar **đổi context theo `route.meta.moduleId`**. User thấy duy nhất nav-items thuộc module đang ở. Logo bấm về `/launcher` (Hub).

```
┌─────────────────────────┐
│  ⚙ AssetCore       ←→  │ ← Logo + collapse toggle
├─────────────────────────┤
│ ▌ IMM-09 · Sửa chữa    │ ← Module banner — viền trái 4px = accent module (orange-600)
│  ─────────────────────  │
│  📊  Tổng quan sửa chữa │
│  🔧  Lệnh sửa chữa     │ ← Active item: bg-brand-50 text-brand-700, viền trái 3px brand-600
│  💻  Yêu cầu firmware  │
│  📈  MTTR              │
│                         │
│  ─────────────────────  │
│  ↩ Về Hub IMMIS        │ ← Pinned ở dưới: link /launcher
└─────────────────────────┘
```

Nguồn dữ liệu: `MODULE_NAV` map trong `AppSidebar.vue` (≥ 13 entry hiện tại). Khi thêm module mới:
1. Thêm key vào `MODULE_NAV` với items + accent color.
2. Thêm `meta: { moduleId: 'imm-XX' }` cho route.
3. Cập nhật bảng accent §7.

Khi collapsed (64px): chỉ hiện icon, label hiện qua tooltip phải (delay 400ms). Active state vẫn giữ viền trái 3px.

Icon source: `ICONS` map trong `AppSidebar.vue` (~36 icon SVG inline, stroke 1.7, viewBox 24×24, currentColor). Không import icon library ngoài.

### 2.3. Topbar

```
[☰]  Module marker | Title          [⌘K Tìm kiếm]      [🔔³]   [👤 ▾]
```

Quy tắc:
- **Module marker**: chấm tròn 8px màu accent module + tên module (vd `● IMM-09 — Sửa chữa`). Đây là điểm nhận diện nhanh nhất khi user đa nhiệm nhiều tab — chấm màu đập vào mắt trước cả title.
- **Không** lặp lại title trong PageHeader nếu module đã hiển thị ở topbar. PageHeader nói về *trang*, topbar nói về *module*.
- Search global mở popover full-width, gợi ý theo: AC Asset (mã/serial), WO (mã), Người dùng. Phím tắt `⌘K` / `Ctrl+K`. Hiển thị hint `⌘K` trong placeholder.
- Notification icon có badge số (đỏ, max "9+"). Click → dropdown 8 item gần nhất + link "Xem tất cả".
- Avatar dropdown: tên + role + Hồ sơ + Đăng xuất. Role hiển thị nhỏ dưới tên dạng `text-xs text-slate-500`.

### 2.4. Lưới (grid)

Container max-width: **không giới hạn cứng** — page-container chỉ padding. Hệ thống nội bộ dùng full-width tận dụng màn rộng.

Breakpoint:
| Tên | Ngưỡng | Áp dụng |
|---|---|---|
| `sm` | ≥ 640px | Tablet — sidebar mặc định collapsed |
| `md` | ≥ 768px | Sidebar có thể mở |
| `lg` | ≥ 1024px | Bố cục desktop tiêu chuẩn |
| `xl` | ≥ 1280px | Dashboard 3-cột KPI |
| `2xl` | ≥ 1536px | Dashboard 4-cột KPI |

Không thiết kế cho mobile <640px (hệ thống nội bộ desktop-first). Có viewport tablet để dùng tại trạm KTV.

---

## 3. Page archetypes (trang mẫu)

Mọi route trong AssetCore thuộc **một** trong 7 archetype dưới đây. Khi thiết kế trang mới, chọn đúng archetype trước, không pha trộn.

### 3.1. Module Hub (Launcher)

Route: `/launcher`. Đã chuẩn hóa ở `Launcher_Redesign_IMMIS_Hub_2026-05-05.md`. Tinh thần:

```
┌────────── Hub Điều Hướng IMMIS ──────────┐
│   Lifecycle wheel (bán nguyệt 5 arc)      │ ← Visual brand element duy nhất trong hệ thống
│       ┌─────────┐                         │
│       │ 🖥 IMMIS │                         │
│       └─────────┘                         │
│                                           │
│  ┌─ Khối 1 ─┐ ┌─ Khối 2 ─┐                │
│  │ Kế hoạch │ │ Triển khai│                │ ← 4 group cards, mỗi card có 3-4 module entry
│  └──────────┘ └──────────┘                 │
│  ┌─ Khối 3 ─┐ ┌─ Khối 4 ─┐                │
│  │ Sử dụng  │ │ Vận hành  │                │
│  └──────────┘ └──────────┘                 │
└──────────────────────────────────────────┘
```

Hub là trang **duy nhất** phá vỡ pattern sidebar (sidebar collapse về minimal). Không tạo trang nào khác chia sẻ pattern này — Hub là điểm dừng định hướng, không phải template tái dùng.

### 3.2. Dashboard module

Mục đích: KPI tổng quan + 2-3 widget chính của 1 IMM module. Ví dụ: `/cm/dashboard`, `/pm/dashboard`, `/dashboard` (toàn hệ thống).

Bố cục chuẩn:

```
[PageHeader]  Tổng quan Sửa chữa
              Theo dõi WO sửa chữa, MTTR, SLA, vật tư

┌─ KPI row (4 card) ─────────────────────────────────────────────────┐
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                                │
│ │ 12   │ │ 4.2h │ │ 87%  │ │  3   │  ← .kpi-card với accent top    │
│ │ WO mở│ │ MTTR │ │ SLA  │ │ Tái  │                                │
│ └──────┘ └──────┘ └──────┘ └──────┘                                │
└────────────────────────────────────────────────────────────────────┘

┌─ 2 cột ─────────────────────────────────┬──────────────────────────┐
│ Biểu đồ MTTR theo tuần (line chart)     │ Top 5 thiết bị tái hỏng  │
│                                          │ (list với link → asset)  │
│                                          │                          │
└──────────────────────────────────────────┴──────────────────────────┘

┌─ Hàng cuối ────────────────────────────────────────────────────────┐
│ Bảng WO sắp đến hạn SLA (5 dòng + link "Xem tất cả")              │
└────────────────────────────────────────────────────────────────────┘
```

Quy tắc KPI card (`.kpi-card`):
- Số chính: `text-3xl font-display font-semibold tabular-nums` — số liệu là ngôi sao.
- Đơn vị nhỏ kế bên: `text-base text-slate-500 ml-1` (vd `4.2 h`, `87 %`). KHÔNG ghép sát số.
- Label: `text-sm text-slate-500`.
- Accent top 3px (`.kpi-card::before`, `var(--kpi-color)`) — màu theo ý nghĩa: brand cho count, success cho %, amber cho cảnh báo, red cho breach.
- **Không** dùng icon to bên trong KPI — số liệu đủ. Icon chỉ ở góc trên phải, 16px, `text-slate-300`.
- Trend indicator nhỏ phía dưới: `↑ +2 so với tuần trước` (`text-emerald-600` nếu tốt, `text-red-600` nếu xấu). Mũi tên dùng ký tự thật `↑↓`, không SVG riêng.

**Charting strategy** (quan trọng — không có chart library trong `package.json`):
- AssetCore không bundle Chart.js / ECharts / D3. Mọi chart hiện tại là **SVG thủ công** (sparkline, bar, donut nhỏ) viết tay trong component. Lý do: bundle-size + kiểm soát accessibility + không cần animation phức tạp.
- Khi cần chart mới: viết SVG primitive trong `components/common/charts/` (chưa có — tạo khi xuất hiện ≥ 2 chỗ dùng). Pattern: `<svg viewBox>` + `<polyline>` cho line, `<rect>` cho bar, không tween chạy nền.
- Chỉ thêm chart library nếu xuất hiện yêu cầu **interactive heatmap, 3D, hoặc real-time stream** — và phải qua review kiến trúc.
- Số lượng data point hiển thị trong sparkline ≤ 30 — quá thì dùng bảng.

### 3.3. List view

Mục đích: bảng dữ liệu với filter, search, pagination. Đa số route IMM-XX là List.

```
[PageHeader]   Lệnh Sửa chữa            [+ Tạo WO mới]   ← actions slot

┌─ ListFilterBar ─────────────────────────────────────────────────┐
│ [🔍 Tìm theo mã / serial...]   [Trạng thái ▾] [Ưu tiên ▾]  ⟲  │
└──────────────────────────────────────────────────────────────────┘

┌─ Tabs (optional) ─────────────────────────────────────────────────┐
│ [ Tất cả 124 ]  Mở 12  Đang xử lý 8  Quá SLA 3  Hoàn thành 101   │
└──────────────────────────────────────────────────────────────────┘

┌─ Table ──────────────────────────────────────────────────────────┐
│ MÃ WO       THIẾT BỊ           ƯU TIÊN  TRẠNG THÁI    SLA      THAO TÁC│
│ ─────────────────────────────────────────────────────────────────│
│ WO-RP-     Máy theo dõi BN..  ⚡Khẩn   ●Đang sửa     ⏱02:14   [Xem]   │
│ 2026-0042                                                          │
│ ─────────────────────────────────────────────────────────────────│
│ ...                                                               │
└──────────────────────────────────────────────────────────────────┘

[BasePagination: ‹  1  2  …  8  ›]   [Hiển thị 20/124]
```

Quy tắc List view:
- **PageHeader** luôn đầu trang. Action chính (tạo mới) ở `slot="actions"`.
- **ListFilterBar** sticky top khi scroll dài. Quick filter dropdown ≤ 4. Filter phức tạp → modal "Bộ lọc nâng cao".
- **Tabs** chỉ khi có ≤ 5 trạng thái phổ biến — quá 5 dùng filter dropdown thay vì tab. Tab có badge số.
- **Table**:
  - Cột mã (`name`) luôn đầu, font-mono, có link → detail. Dùng `<CodeLabel>`.
  - Cột trạng thái dùng `<StatusBadge>` (xem §4.4).
  - Cột số/SLA/đo lường: `text-right tabular-nums font-mono`.
  - Cột thao tác cuối — chỉ link "Xem" hoặc icon (trash/edit) khi cần. Tránh nhồi 4-5 button mỗi dòng.
  - Hover row: `hover:bg-slate-50/70` (đã có ở `.table-row`).
  - Row được chọn: `.table-row-selected` (`bg-brand-50`).
  - Khi cell có 2 dòng (chính + phụ): dòng chính `text-slate-900`, dòng phụ `text-xs text-slate-500 mt-0.5`.
- **Pagination** dưới bảng, căn trái. Số trang sang phải. Page size mặc định 20, options 10/20/50.
- **Empty state** xem §5.2.

### 3.4. Detail view

Mục đích: hiển thị chi tiết 1 record (Asset, WO, Calibration, …) + lịch sử + actions.

```
[PageHeader]  ← Quay lại WO       WO-RP-2026-0042                  [In] [Hủy] [✓ Đóng WO]
              Thiết bị: Máy theo dõi BN  ·  Mở: 06/05/2026 14:32

┌─ Status banner ───────────────────────────────────────────────────┐
│ ● Đang sửa chữa     SLA: 02:14 còn lại     Ưu tiên: ⚡Khẩn        │
└───────────────────────────────────────────────────────────────────┘

┌─ 2 cột: 8/12 chi tiết · 4/12 lịch sử ─────────────────────────────┐
│ ┌─ Tabs ────────────────────────────────────┐  ┌─ Lịch sử ────┐   │
│ │ [Thông tin] [Vật tư] [Bảng kiểm] [Ảnh]   │  │ 14:32 Mở WO  │   │
│ └────────────────────────────────────────────┘  │ 14:45 Phân  │   │
│ ┌─ Tab content card ───────────────────────┐    │      công   │   │
│ │ Mã WO:           WO-RP-2026-0042         │    │ 15:10 Bắt   │   │
│ │ Mô tả lỗi:       Tín hiệu nhịp tim mất   │    │      đầu sửa│   │
│ │ ...                                       │    │ ...         │   │
│ │ ─────────────────────────────────────     │    │             │   │
│ │ Chẩn đoán:       [Đã có / Submit form]    │    │ [Xem audit  │   │
│ └────────────────────────────────────────────┘   │  trail đầy  │   │
│                                                  │  đủ →]      │   │
│                                                  └─────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

Quy tắc Detail:
- **Status banner** sát PageHeader — status + SLA + ưu tiên + người được phân công. Một dòng. Đây là thông tin user muốn thấy đầu tiên. Khi SLA breach: nền `bg-red-50 border border-red-200`, chữ `text-red-700`, icon ⚠.
- **Action chính** ở `actions` slot của PageHeader, bên phải. Xếp theo **mức độ destructive**: `[Cancel]` xám → `[Save]` brand → `[Submit/Approve]` success/danger nếu là final action.
- **Tabs** trong detail: dùng `ref<string>` cục bộ + `useRoute().query.tab` đồng bộ URL. Không quá 5 tab.
- **Lịch sử** ở cột phải hẹp (4/12 cols) — timeline dạng dot + thời gian + actor. Click "Xem audit trail đầy đủ" mở modal full-screen với hash chain (đọc từ DocType `imm_audit_trail`).
- **Form trong tab**: 2 cột (`grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4`). Field name ngắn-dài: trường ngắn cùng hàng, trường dài (textarea) full-width.
- **Field-value pair** (read mode): `<dt class="text-xs text-slate-500 uppercase tracking-wide">` + `<dd class="text-base text-slate-900 mt-0.5">`. Khi giá trị là số: `font-mono tabular-nums`.

### 3.5. Form view (Create / Edit)

Mục đích: nhập dữ liệu cho 1 record mới hoặc sửa.

```
[PageHeader]  Tạo Lệnh Sửa chữa    [Hủy] [Lưu nháp] [✓ Tạo WO]

┌─ Form panel ─────────────────────────────────────────────────────┐
│ ┌─ Section: Thiết bị ────────────────────────────────────────┐   │
│ │ Thiết bị *      [LinkSearch: AC Asset ▾]                   │   │
│ │ Loại sửa chữa * [Select: Corrective | Emergency | …]       │   │
│ │ Ưu tiên *       [Radio chip: Normal · Urgent · Emergency]  │   │
│ └─────────────────────────────────────────────────────────────┘   │
│ ┌─ Section: Triệu chứng & Nguồn ─────────────────────────────┐   │
│ │ Mô tả lỗi *     [Textarea, 4 rows]                         │   │
│ │ Nguồn:          ⚪ Từ sự cố [LinkSearch IR]                │   │
│ │                 ⚪ Từ PM gốc [LinkSearch PM WO]            │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                   │
│ Validation summary (nếu có lỗi):                                  │
│ ⚠ Vui lòng chọn nguồn sửa chữa (sự cố hoặc PM gốc)               │
└──────────────────────────────────────────────────────────────────┘
```

Quy tắc Form:
- **Section break** mỗi 4–6 trường. Section title `text-sm font-semibold text-slate-700`, không in hoa, không gạch.
- **Required**: dấu `*` đỏ (`text-red-500`) sau label, không phải trước.
- **Field error inline**: dưới field, `text-rose-600 text-xs mt-1`. Border field đổi `border-rose-500`.
- **Validation summary**: trên cùng form khi submit fail (server trả nhiều field error). Liệt kê 5 lỗi đầu, "+N lỗi khác" nếu nhiều.
- **Autosave draft**: dùng `useFormDraft` composable cho form > 5 trường. Hiển thị `Đã lưu nháp 14:32` cạnh title, `text-xs text-slate-400`.
- **CTA chính**: bên phải nút Hủy. Brand cho create/save. Success cho submit (irreversible). Danger cho delete (luôn cần confirm modal).
- **Phím tắt**: `Esc` = Cancel. `Cmd/Ctrl+S` = Save (không submit).
- **Date input**: luôn dùng `<DateInput>` / `<DateTimeInput>` — đã có mask `dd/mm/yyyy`. Không dùng `<input type="date">` (không validate format VN, hiện picker browser khác nhau).

### 3.6. Wizard (multi-step form)

Mục đích: form dài chia bước — phục vụ Procurement Decision (Wave 2), commissioning checklist, vendor evaluation.

```
[PageHeader]  Quyết định mua sắm — PD-2026-0008      [Hủy]

┌─ Stepper (sticky top) ───────────────────────────────────────────┐
│  ① Thông tin cơ bản → ② Đánh giá NCC → ③ Phê duyệt → ④ Xác nhận │
│  ─●─────────────●─────────────○─────────────○                    │
└──────────────────────────────────────────────────────────────────┘

┌─ Step content ───────────────────────────────────────────────────┐
│   (form section của bước hiện tại — pattern §3.5)                │
└──────────────────────────────────────────────────────────────────┘

[← Quay lại]                                    [Lưu nháp] [Tiếp →]
```

Quy tắc:
- **Stepper** dùng component `Stepper` (chưa có — sẽ tạo trong `components/common/Stepper.vue`). 3-5 bước. ≥6 bước → tách thành nhiều form / detail page riêng.
- Bước đã hoàn thành: chấm `bg-emerald-600` + ✓. Bước hiện tại: chấm `bg-brand-600` viền sáng. Bước chưa: chấm `bg-slate-200 border border-slate-300`.
- **Click ngược** vào bước đã qua: cho phép, không hỏi confirm. Dữ liệu không reset.
- Nút "Tiếp" disabled khi step hiện tại còn lỗi validation.
- Bước cuối ("Xác nhận"): hiển thị bản tóm tắt + button submit primary/danger tùy ngữ nghĩa.
- Lưu nháp xuyên bước qua `useFormDraft`.

### 3.7. Auth view

Route: `/login`, `/register`. Centered card, no chrome. View tự render layout (xem §2.1).

```
                  ┌──────────────────────┐
                  │   AssetCore (logo)   │
                  │                      │
                  │   Đăng nhập IMMIS    │
                  │   ─────────────      │
                  │   [Email]            │
                  │   [Mật khẩu]         │
                  │   ☐ Ghi nhớ          │
                  │                      │
                  │   [   Đăng nhập   ]  │
                  │                      │
                  │   Quên mật khẩu?     │
                  └──────────────────────┘
                       Bệnh viện X · v3.x.y
```

Quy tắc:
- Card 400px wide, padding 32px, shadow-card.
- Logo + tên hệ thống đầu, sau đó form, footer phiên bản.
- Error login: alert đỏ phía trên form, không inline field — user không cần biết "email hay password sai" để chống enumeration.
- Background: gradient nhẹ `from-slate-50 to-blue-50` HOẶC `--color-bg`. Không gradient tím/cam.

---

## 4. Component composition rules

### 4.1. Component canonical (21 file trong `components/common/`)

**Bao giờ tự build cũng phải kiểm tra trước.** Bảng dưới đây là canonical — KHÔNG reimplement những thứ đã có.

| File | Khi cần |
|---|---|
| `AppLayout.vue` | Khung shell — không import trực tiếp, App.vue tự xử |
| `AppSidebar.vue` | Sidebar module-scoped + ICONS map |
| `AppTopBar.vue` | Topbar + module marker + search global |
| `PageHeader.vue` | Header trang (title, subtitle, breadcrumb, backTo, slot actions) |
| `BaseModal.vue` | Modal — đã có focus trap + esc + backdrop click |
| `BasePagination.vue` | Pagination (xem §3.3) |
| `StatusBadge.vue` | Trạng thái record — map status string → màu (xem §4.4) |
| `CodeLabel.vue` | Mã / link tới detail (font-mono, hover underline) |
| `ListFilterBar.vue` | Filter bar trên list (search + dropdowns + reset) |
| `DateInput.vue` / `DateTimeInput.vue` | Date / datetime input có mask `dd/mm/yyyy` |
| `LinkSearch.vue` | Search 1 link DocType — autocomplete |
| `SmartSelect.vue` | Select có icon / mô tả (≥ 6 options) |
| `LoadingSpinner.vue` | Spinner — chỉ dùng cho action ngắn |
| `SkeletonLoader.vue` | Skeleton load (mô phỏng layout) |
| `ToastContainer.vue` | Toast — mount 1 lần ở App.vue |
| `FilterToggleButton.vue` | Filter toggle (mở drawer ở mobile/tablet) |
| `LinkInfoCard.vue` | Snippet info từ Link DocType (preview hover) |
| `LocaleSwitcher.vue` | Switch ngôn ngữ |
| `RouteErrorBoundary.vue` | Boundary cho route fail (hiện trong AppLayout) |
| `UomConverter.vue` | Chuyển đơn vị (kg ↔ lb, °C ↔ °F, …) |

**Sẽ thêm** (Wave 2/3, đặt vào `components/common/`):
- `Stepper.vue` — multi-step form indicator (xem §3.6).
- `RadioChip.vue` — radio dạng chip cho priority/risk class.
- `AuditTrailTimeline.vue` — timeline chuẩn cho audit trail (đang inline ở vài view).
- `MetricNumber.vue` — số + đơn vị + trend (gói pattern KPI).
- `Sparkline.vue` — SVG line nhỏ (≤30 điểm).

**Cấm**:
- Tự reimplement modal/dropdown/toast — phá nhất quán z-index, focus trap, escape behavior.
- Inline status logic (mapping color-trạng thái mỗi nơi mỗi khác). Phải đẩy vào `<StatusBadge>` props.

### 4.2. Composables (10 file trong `composables/`)

| Composable | Dùng cho |
|---|---|
| `useApi` | Wrapper axios + toast + loading + field error mapping (BE ErrorCode → toast tier) |
| `useToast` | Push toast (success / error / warning / info), API ngắn |
| `useFormDraft` | Autosave form vào localStorage, restore khi reload |
| `usePagination` | State page/page_size + URL query sync + total |
| `useSidebar` | State open/collapse + persist (pinia-plugin-persistedstate) |
| `useWorkflow` | Lấy transitions cho phép theo role + docstatus, render action button |
| `usePermissions` | Check `<v-permission>` style: hide button khi user không có quyền (DOM-remove) |
| `useAssets` | Query AC Asset (cached qua TanStack Vue Query) |
| `useDashboard` | Query KPI tổng hợp (toàn module hoặc 1 module) |
| `useMaskedDateInput` | Internal cho DateInput/DateTimeInput — không gọi trực tiếp |

Tất cả query async dùng **TanStack Vue Query** (`@tanstack/vue-query` 5.99). Key pattern: `[doctype, filters?, name?]`. Stale time mặc định 30s; mutation invalidate đúng key cha (không refetch toàn page).

### 4.3. Buttons — phân cấp rõ

```
┌──────────────────────────────────────────────────────┐
│ Primary    .btn-primary    bg-brand-600 → CTA chính  │
│ Success    .btn-success    bg-emerald-600 → Submit  │
│ Danger     .btn-danger     bg-red-600 → Delete/Cancel│
│ Secondary  .btn-secondary  Outline → Action phụ     │
│ Ghost      .btn-ghost      Plain → Inline action    │
└──────────────────────────────────────────────────────┘
```

Mỗi vùng (page header, form, modal footer) **chỉ một** primary. Các button khác ghost hoặc secondary. Nếu thấy 3 primary trong cùng vùng → bố cục sai.

Kích thước: `.btn` mặc định (text-base, py-2.5). Inline trong table dùng size-sm: `text-sm px-3 py-1.5`.

Loading state: thay icon đầu button bằng spinner `animate-spin-slow`, label đổi `Đang lưu…`, button disabled. **Không** thay nguyên button bằng spinner — mất ngữ cảnh hành động.

### 4.4. Form controls

| Control | Class | Khi dùng |
|---|---|---|
| Text / number | `.form-input` | 1 dòng |
| Select native | `.form-select` | < 6 options, không cần search |
| Smart select | `<SmartSelect>` | ≥ 6 options HOẶC cần icon/mô tả |
| Link search | `<LinkSearch>` | Liên kết DocType — autocomplete |
| Textarea | `.form-textarea` | Mô tả ≥ 2 dòng, `resize-none` mặc định |
| Date | `<DateInput>` | dd/mm/yyyy mask |
| Datetime | `<DateTimeInput>` | dd/mm/yyyy hh:mm |
| Checkbox | Tailwind forms plugin defaults | Boolean |
| Radio chip | `<RadioChip>` (sẽ build) | Priority/risk class — dễ click |

**Label**: luôn có, `.form-label` (`text-base font-semibold text-slate-700 mb-2`). KHÔNG dùng placeholder thay label. Placeholder chỉ là ví dụ giá trị (`vd: 35.6`).

### 4.5. Status & semantic badges

Trạng thái workflow → màu badge cố định, không invent:

| Trạng thái nhóm | Màu | Class chip |
|---|---|---|
| Open / Draft / Pending / Scheduled | blue | `bg-blue-100 text-blue-700` |
| In Progress / Diagnosing / Assigned | amber | `bg-amber-100 text-amber-700` |
| Pending Parts / Pending Inspection | violet | `bg-violet-100 text-violet-700` |
| Completed / Approved / Pass / Released | emerald | `bg-emerald-100 text-emerald-700` |
| Cancelled / Rejected / N/A | neutral | `bg-slate-200 text-slate-600` |
| Cannot Repair / Failed / Out of Service | rose | `bg-rose-100 text-rose-700` |
| Overdue / SLA breached | red đậm | `bg-red-600 text-white` (rõ ràng — đây là báo động) |

`<StatusBadge>` nhận `status: string` và map qua bảng trên. Khi thêm trạng thái BE (workflow JSON), cập nhật `<StatusBadge>` ở 1 chỗ duy nhất. Workflow fixtures hiện tại: 14 file trong `assetcore/workflow/` — bất kỳ state mới nào trong fixture phải có entry tương ứng trong StatusBadge.

Anatomy chip:
```
●  Đang sửa chữa
↑   ↑
dot label (capitalize, không in hoa)
```
- Dot 6px tròn, màu theo nhóm.
- Padding `px-2 py-0.5`, rounded-full, text-xs.
- Khi badge ở SLA breach: thêm icon ⚠ trước label.

### 4.6. Tables

- Wrap table trong `.table-wrapper` (overflow-x-auto + viền).
- Header `.table-header` (uppercase, tracking-wide).
- Cell `.table-cell` (py-4, base size).
- Row có row.click → đi detail thì set `.table-row` (cursor pointer + hover bg).
- Cột số/tiền: `text-right tabular-nums font-mono`.
- Cột trạng thái dùng `<StatusBadge>`.
- Khi có > 8 cột → cân nhắc:
  - Hide cột phụ trong dropdown "Cột hiển thị".
  - Hoặc chuyển detail-on-row-expand thay vì cột thêm.

### 4.7. Cards

| Variant | Class | Dùng |
|---|---|---|
| Standard | `.card` | Container nội dung mặc định (p-7) |
| Small | `.card-sm` (p-4) | Nested card, chip lớn |
| Interactive | `.card-interactive` | Card click được — hover lift `-translate-y-0.5` |
| KPI | `.kpi-card` | Có dải accent top, dùng ở dashboard |

Cấm card lồng nhau quá 2 lớp (parent → child). Nếu thấy card-trong-card-trong-card → flatten hoặc dùng section divider.

### 4.8. Numeric & unit display (riêng cho HTM)

AssetCore hiển thị nhiều số đo: nhiệt độ phòng, áp suất khí y tế, sai số calibration, MTTR. Quy ước:

- Số luôn `font-mono tabular-nums`. Đảm bảo cột số căn lề phải vẫn thẳng.
- Đơn vị **tách dấu cách** với số, font sans, `text-slate-500` cỡ nhỏ hơn 1 cấp:
  ```
  35.6 °C        4.2 h        87 %        220 / 240 V
  ```
- Số âm: dùng dấu `−` (U+2212), không hyphen `-`.
- Threshold ngữ nghĩa:
  - In-tolerance: text mặc định.
  - Out-of-tolerance: `text-rose-600 font-semibold`, kèm icon ⚠.
- Số lớn nhóm 3 chữ số: `1 250 000` (space, kiểu khoa học/Pháp), KHÔNG dùng `,` (mâu thuẫn với decimal VN).
- Decimal: `.` (thay vì `,`) — dùng `Intl.NumberFormat('en-US')` rồi format khoảng trắng nghìn ở app layer.
- Time delta SLA: `02:14` (mm:ss tới 60 phút) hoặc `1d 4h` (vượt giờ). Khi còn < 15% SLA: `text-red-600 font-semibold`.

---

## 5. State patterns

Mỗi list/detail/form phải xử lý **5 trạng thái**: Loading · Empty · Success · Error · Partial. Bỏ sót state nào → UX gãy.

### 5.1. Loading

| Tình huống | Pattern |
|---|---|
| Trang load lần đầu | `<SkeletonLoader>` mô phỏng layout — không spinner full page |
| Refresh trong trang | Loading bar 2px brand-600 ở top, animate-pulse |
| Submit form | Button primary disabled + spinner trong button: `[⟳ Đang lưu…]` |
| Polling KPI | Dot pulse nhỏ trên card title (`animate-pulse-subtle`) |

**Không** dùng `<LoadingSpinner>` chiếm toàn trang trừ khi thật sự không có gì để show. Skeleton tạo cảm giác app "đang chuẩn bị" thay vì "đứng".

TanStack Vue Query `isPending` → skeleton; `isFetching && data` → indicator nhỏ (xem §5.4).

### 5.2. Empty

```
┌────────────────────────────────────────────────────┐
│                                                    │
│              📋  (icon nhẹ, slate-300)            │
│                                                    │
│         Chưa có lệnh sửa chữa nào                  │
│   Khi có sự cố thiết bị, lệnh sẽ tự động tạo từ   │
│   báo cáo sự cố hoặc tạo thủ công bên dưới.        │
│                                                    │
│              [+ Tạo WO mới]                        │
└────────────────────────────────────────────────────┘
```

Quy tắc:
- Icon nhẹ (slate-300, ≤48px). Tránh illustration sặc sỡ.
- Tiêu đề ngắn (1 dòng). Mô tả 1-2 câu giải thích **tại sao** trống và **làm gì** kế tiếp.
- 1 CTA chính (primary). Không nhồi nhiều lựa chọn.
- Khi empty do filter: "Không tìm thấy WO khớp bộ lọc" + "[Xóa bộ lọc]" (thay CTA tạo mới).
- Khi empty do thiếu quyền (`usePermissions` chặn): "Bạn không có quyền xem dữ liệu này. Liên hệ quản trị nếu cần truy cập." — không CTA.

### 5.3. Error

| Cấp | Pattern |
|---|---|
| Field error | `text-rose-600 text-xs` dưới input (đã có) |
| Form-level error | `.alert-error` trên cùng form |
| Page-level error | `<RouteErrorBoundary>` + thông báo "Không tải được dữ liệu" + nút Thử lại |
| Toast | `<ToastContainer>` — error đỏ tự đóng sau 6s |
| 401/403 | Redirect `/login` (axios interceptor) — không show toast |
| Business rule | Toast màu **vàng** (warning) — không phải đỏ. Người dùng hiểu là "anh sai" chứ không phải "hệ thống lỗi" |

**Mapping ErrorCode (BE) → UI tier**: BE trả `error_code` (xem `assetcore/services/shared/constants.py`). `useApi` map:
- `VALIDATION_*` → field error inline + toast warning vàng.
- `PERMISSION_*` → toast warning + không reset form.
- `STATE_*` (workflow transition không hợp lệ) → modal alert (không toast — đây là hành vi user expect khác).
- `SYSTEM_*` / unknown → toast error đỏ + log console.

### 5.4. Partial / stale data

Khi cache vẫn show data cũ và đang refetch nền: chấm xanh nhỏ ở góc card title `●` (`bg-brand-400 animate-pulse-subtle`), không che data. Thấy `isFetching && data` thì show indicator. Tooltip "Đang cập nhật…".

### 5.5. Success / confirmation

- CRUD thành công: toast xanh ngắn (3s) — "Đã tạo WO WO-RP-2026-0042". Click vào toast → mở record vừa tạo.
- Hành động không thể undo (Approve, Submit final, Decommission, Cancel WO sau khi Submit): mở `<BaseModal>` confirm với tóm tắt + checkbox "Tôi xác nhận hành động này". Button danger.
- Soft action (Save draft, Cancel form chưa submit): không cần confirm, toast nhẹ là đủ.
- Sau Submit thành công ở Wizard: redirect tới detail page — KHÔNG ở lại wizard với màn xanh.

---

## 6. Navigation & wayfinding

### 6.1. Breadcrumb

Mọi trang ngoài Hub phải có breadcrumb tối đa 3 cấp:

```
Hub  /  IMM-09 — CM  /  WO-RP-2026-0042
```

- Cấp cuối là current — đậm, không link.
- Cấp giữa là module — link về list của module.
- Đầu tiên luôn là "Hub" hoặc tên module nếu vào thẳng.
- Separator dùng `/` thay vì `>` (đỡ rối với mã có dấu `>`).

### 6.2. Back button

`<PageHeader backTo="...">` — luôn dùng route đích cụ thể, **không** `router.back()` (gãy khi mở URL trực tiếp). Label mặc định "← Danh sách".

### 6.3. Active state trong nav

- Sidebar nav-item active: `bg-brand-50 text-brand-700` + viền trái 3px `border-l-3 border-brand-600`.
- Tab active trong detail: underline 2px brand-600, text brand-700.
- Filter chip active: `bg-brand-600 text-white`. Inactive: `bg-white border text-slate-600`.

### 6.4. Quy ước URL

Hiện tại đang có **drift**: một số module dùng tên semantic (`/cm`, `/pm`, `/calibration`, `/commissioning`, `/document`, `/incident`, `/inventory`, `/purchase`), một số dùng code (`/imm01`, `/imm02`, `/imm03`). **Quy ước cố định từ v2:**

- **Module slug = tên semantic** khi đã có; mới đặt thì dùng semantic kebab-case (vd `/needs`, `/tech-spec`, `/procurement` thay vì `/imm01/02/03`).
- **List**: `/<module>/<entity-plural>` — vd `/cm/work-orders`, `/calibration/schedules`.
- **Detail**: `/<module>/<entity-plural>/:name` — `name` là PK Frappe (vd `WO-RP-2026-0042`).
- **Create**: `/<module>/<entity-plural>/new` — không dùng `?action=create`.
- **Edit**: thường = detail page (mode tự động khi user có quyền). Nếu cần page riêng: `/<module>/<entity-plural>/:name/edit`.
- **Dashboard module**: `/<module>/dashboard`. Toàn hệ thống: `/dashboard`.
- **Audit trail full view**: `/audit/:doctype/:name`.

Migration `/imm0X/*` → semantic slug: làm khi chạm vào module đó tiếp theo (Wave 2 cleanup). Giữ redirect 1-1 trong router cho bookmark cũ tối thiểu 1 release.

Tham chiếu chi tiết: `Frontend_Router_Navigation_Map.md`.

---

## 7. Module visual identity

Mỗi IMM module có 1 accent color riêng dùng cho icon nav, KPI top stripe, header marker, sidebar banner border. Brand-600 vẫn là CTA chính ở mọi nơi — accent chỉ để **phân biệt context**, không phải để lòe.

| Module | Accent | Tailwind | Lý do |
|---|---|---|---|
| IMM-01 Nhu cầu | violet | `violet-600` | Khởi đầu vòng đời — màu khởi tạo |
| IMM-02 Tech Specs | indigo | `indigo-600` | Kỹ thuật, dữ liệu chuẩn |
| IMM-03 Mua sắm | sky | `sky-600` | Quyết định, đối tác bên ngoài |
| IMM-04 Lắp đặt | teal | `teal-600` | Chuyển từ giấy tờ → thực địa |
| IMM-05 Hồ sơ | slate | `slate-600` | Lưu trữ, đáng tin |
| IMM-06 Đào tạo | amber | `amber-600` | Năng lượng, chuyển giao |
| IMM-08 PM | emerald | `emerald-600` | Sức khỏe, định kỳ |
| IMM-09 CM | orange | `orange-600` | Cảnh báo, cần can thiệp |
| IMM-11 Hiệu chuẩn | cyan | `cyan-600` | Đo lường, độ chính xác |
| IMM-12 Sự cố | red | `red-600` | Khẩn cấp |
| IMM-13 Báo cáo | fuchsia | `fuchsia-600` | Tổng hợp, xuyên module |
| IMM-14 Phân tích | lime | `lime-600` | Insight |
| IMM-15 Decommission | stone | `stone-600` | Kết thúc vòng đời |
| IMM-16 Tài chính | yellow | `yellow-600` | Chi phí (rõ rệt) |
| Master / IMM-00 / System | brand | `brand-600` (default) | Trung tính |

Áp dụng accent ở:
- **Sidebar module banner**: viền trái 4px solid accent.
- **KPI card top stripe**: `style="--kpi-color: theme('colors.<accent>.600')"`.
- **Topbar module marker**: chấm 8px tròn cùng accent.
- **Empty state icon trong module**: `text-<accent>-300`.

**Không** thay đổi text body theo accent — vẫn slate-900 mọi nơi. Không tô background lớn theo accent — chỉ stripe + dot.

---

## 8. Responsive behavior

Desktop-first. Hỗ trợ tablet ≥ 768px. Không hỗ trợ phone < 640px (ngoại trừ login).

| Breakpoint | Behavior |
|---|---|
| ≥ 1280px (`xl`) | Sidebar mở mặc định. Dashboard 4 KPI cards/row. |
| 1024–1279px (`lg`) | Sidebar mở. Dashboard 3 KPI cards/row. |
| 768–1023px (`md`) | Sidebar collapsed mặc định, mở overlay khi cần. 2 KPI cards/row. |
| 640–767px (`sm`) | Sidebar overlay only. List view: `<FilterToggleButton>` mở filter trong drawer. Table → ẩn cột phụ. |
| < 640px | Login chỉ. Các page khác show banner "Vui lòng dùng màn hình lớn hơn". |

Quy tắc table responsive:
- Cột mã (PK), trạng thái, action: **luôn** giữ.
- Cột phụ (mô tả dài, metadata): hide ở `<lg`.
- Không dùng card-list pattern thay table — phá mật độ thông tin user cần.

---

## 9. Motion & micro-interactions

### 9.1. Khi nào động

| Sự kiện | Animation | Lý do |
|---|---|---|
| Page enter | `animate-fade-in` 250ms | Mượt context switch |
| Modal open | `animate-scale-in` 200ms | Tâm điểm mới |
| Toast in | `animate-slide-up` 300ms | Đến từ hành động vừa làm |
| List item streamed | `animate-slide-up` + stagger 1-8 | Kết quả load có nhịp |
| Skeleton | `.skeleton::after` shimmer infinite | "Đang tải" rõ |
| Hover card-interactive | `-translate-y-0.5` + shadow-card-hover (200ms) | Tín hiệu click được |
| Button press | `active:scale-[0.98]` (100ms) | Tactile |
| Status change | Ngắn 200ms color crossfade | Mềm mại |
| Progress bar | `animate-bar-fill` 700ms | Biến động ngân sách / SLA usage |

### 9.2. Khi nào tĩnh

- Form input focus → chỉ ring (không shake/bounce).
- Validation error xuất hiện → fade in nhẹ, **không** shake field.
- Nav item active → đổi state ngay, không transition (giúp định vị nhanh).
- Đổi tab → swap content, không slide ngang.
- Số đếm trong KPI thay đổi: ưu tiên thay thẳng. Tween chỉ khi delta ≥ 10% và ≤ 600ms.

### 9.3. Reduce motion

Respect `prefers-reduced-motion: reduce`. Thêm vào cuối `main.css`:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Hiện chưa có trong `main.css` — coi là gap cần fix khi cập nhật token tiếp theo.

---

## 10. Accessibility (WCAG 2.1 AA)

Hệ thống được dùng bởi nhiều người, có người không thạo công nghệ — accessibility không tùy chọn.

### 10.1. Yêu cầu cứng

- **Contrast** ≥ 4.5:1 cho text thường, 3:1 cho text lớn (≥ 18px). Brand-600 trên trắng đạt 5.2:1 ✓. Slate-500 trên trắng ~4.7:1 ✓ (gần ngưỡng — không dùng cho thông tin quan trọng).
- **Keyboard navigation**: mọi action tới được bằng `Tab`. `Esc` đóng modal/dropdown. `Enter`/`Space` activate button.
- **Focus visible**: đã có `box-shadow: 0 0 0 3px rgba(37,99,235,.20)` ở `*:focus-visible`. **Không** xóa outline.
- **ARIA**:
  - Modal: `role="dialog" aria-modal="true" aria-labelledby="..."`.
  - Status badge: `<span role="status">` cho trạng thái dynamic.
  - Loading: `aria-busy="true"` trên container đang load.
  - Pagination: `aria-label="Phân trang"` trên nav, `aria-current="page"` trên page hiện tại.
  - Stepper: `aria-current="step"` trên step hiện tại.
- **Form label**: liên kết qua `<label for="...">` HOẶC bao input trong `<label>`. Không placeholder-only.
- **Image alt**: mọi `<img>` có alt. Decorative → `alt=""` (không bỏ trống chính tả).
- **Màu KHÔNG là kênh thông tin duy nhất**: status có dot + label, error có icon + text. Mù màu vẫn dùng được.

### 10.2. Khuyến nghị

- Skip link đầu page: `<a href="#main">Bỏ qua điều hướng</a>` (hidden until focus).
- Heading order đúng: H1 (PageHeader) → H2 (sections) → H3. Không skip cấp.
- Live region cho toast: `<div aria-live="polite" aria-atomic="true">` (đã có trong `<ToastContainer>` nếu setup đúng).
- Date input: chấp nhận cả paste `06/05/2026` lẫn `2026-05-06`.
- Tooltip không phải nguồn duy nhất — nếu thông tin quan trọng, hiển thị inline.

---

## 11. Internationalization

Project dùng `vue-i18n` 9 ở `src/locales/`. Hiện chỉ có `vi` (default). Khi thêm `en`:

- **Không** hardcode label trong component — luôn `{{ t('imm09.create.title') }}`.
- Key namespace theo module: `auth.*`, `imm09.*`, `cm.*`, `common.*`. Tránh `app.*` chung chung.
- Số / ngày dùng `Intl.NumberFormat`, `Intl.DateTimeFormat` với locale từ store.
- Đơn vị tiền: `Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' })` — không cộng chuỗi `'đ'` thủ công.
- Tránh ghép câu kiểu `'Tạo ' + entity` — dùng key đầy đủ `t('imm09.action.create_wo')`.
- RTL không hỗ trợ (không có locale Ả Rập/Hebrew trong roadmap).

---

## 12. Iconography

- **Bộ icon**: SVG inline trong `ICONS` map của `AppSidebar.vue` (~36 icon). Phong cách: stroke 1.7, viewBox 24×24, currentColor.
- **Kích thước chuẩn**: 18×18 trong nav, 16×16 inline trong text, 24×24 trong PageHeader / empty state, 48×48 trong empty illustration.
- **Cấm**:
  - Import icon library lớn (FontAwesome, Material, Heroicons full) — bundle bloat.
  - Mix nhiều style icon (solid + line + 3D).
  - Icon cảnh báo màu sặc sỡ ngoài mục đích cảnh báo (đỏ chỉ cho danger, amber chỉ cho warning).

Khi cần icon mới:
- Dùng nhiều nơi (≥ 3) → thêm vào `ICONS` map của `AppSidebar.vue` HOẶC tạo `src/components/common/icons/<name>.vue`.
- Dùng 1 nơi → inline SVG ngay trong component đó.

---

## 13. Print & export

Một số trang (WO closed report, calibration certificate, asset passport, audit log export) cần in. Quy ước:

- Class `print:` của Tailwind áp dụng. `print:hidden` cho topbar/sidebar/action button. `print:bg-white print:text-black`.
- Layout in: 1 cột, max 800px width, padding A4-friendly. Body font giữ Inter (dễ đọc khi in laser).
- Mã + serial luôn hiện rõ. Audit chain hash hiện ở footer (verify được).
- Calibration certificate: dùng print format Frappe (server-side) để đảm bảo font tiếng Việt + chữ ký số. **Không** generate PDF từ FE (jsPDF / html2canvas) — sai font, mất accent VN.
- QR code: `qrcode` (đã có trong dependencies) — render `<canvas>` 256×256 cho asset passport, link tới `/asset/:name`.

---

## 14. Anti-patterns (đừng làm)

| ❌ | Tại sao |
|---|---|
| Card lớn ôm cả trang form 2000px | Vô nghĩa với mật độ dữ liệu y tế; người dùng phải scroll xa |
| Sidebar gom hết route 17 module | Mất context module; không scale được khi thêm Wave 3 |
| Spinner full-page mỗi action | Cảm giác "đứng máy"; dùng skeleton + button-state thay |
| Toast cho mọi success | Spam; chỉ cho create/update/delete và hành động không hiển thị inline |
| Modal trong modal | Z-index war; rephrase flow thành stepper hoặc page |
| Inline edit table cell | Mâu thuẫn với audit trail; dùng detail page modal |
| Animation > 400ms cho UI chính | Cảm giác chậm |
| Status text-only không có badge | Mất tín hiệu thị giác — màu là wayfinding chính cho KTV |
| Icon-only button không có aria-label / tooltip | Không accessible |
| Dùng `display: none` để hide vì role | `<v-permission>` đã DOM-remove — đúng cho action button. Nhưng dữ liệu nhạy cảm phải lọc ở BE, không ẩn ở FE |
| Dùng `<input type="text">` cho ngày | Không validate format VN; dùng `<DateInput>` |
| Chữ tiếng Anh xen tiếng Việt nhúng giữa câu | Khó đọc; chuẩn hóa toàn VN trừ technical token (mã WO, ErrorCode) |
| Số không `tabular-nums` trong cột số | Cột nhảy chân răng cưa khi pagination |
| Import chart library nặng cho 1 sparkline | Bundle bloat; viết SVG primitive trong `components/common/charts/` |
| Tạo `layouts/` folder và move AppLayout | Khác convention hiện tại; AppLayout sống trong `components/common/` cho tới khi có lý do tách bạch |
| Dùng `,` cho nghìn và `.` cho thập phân (kiểu VN cũ) | Mâu thuẫn với Inter `tabular-nums` + dữ liệu khoa học; dùng space + `.` |
| Tự định nghĩa lại màu accent trong component | Phá tính nhất quán module; chỉnh ở §7 rồi import |

---

## 15. Checklist trước khi merge UI PR

- [ ] Dùng `<PageHeader>` với title + breadcrumb + backTo
- [ ] Dùng các component common có sẵn trước khi tạo mới (kiểm bảng §4.1)
- [ ] Xử lý đủ 5 state: loading, empty, success, error, partial
- [ ] Action chính ≤ 1 primary mỗi vùng
- [ ] Mọi mutation gọi qua `useApi.run()` để có toast + loading + field-error
- [ ] Form có required marker + autosave nếu > 5 trường
- [ ] Status hiển thị qua `<StatusBadge>` (không inline color)
- [ ] Tabs ≤ 5; nhiều hơn → chuyển filter
- [ ] Số dùng `font-mono tabular-nums`; đơn vị tách dấu cách
- [ ] Module accent đúng bảng §7 (sidebar banner, KPI stripe, topbar dot)
- [ ] Keyboard tab order hợp lý; `Esc` đóng modal/dropdown
- [ ] Contrast text ≥ 4.5:1 (kiểm bằng DevTools)
- [ ] Responsive: kiểm 1280, 1024, 768
- [ ] Motion: dưới 400ms cho mọi transition control; respect `prefers-reduced-motion`
- [ ] Tiếng Việt full; technical token rõ font-mono
- [ ] Print check: hide chrome, layout 1 cột (nếu trang có in)
- [ ] `npm run typecheck && npm run lint` clean
- [ ] Không thêm chart/icon/date library mới mà không đọc §3.2 / §12 / §4.4

---

## 16. Tham chiếu

- **Tokens**: `frontend/tailwind.config.js`, `frontend/src/assets/styles/main.css`
- **Layout shell**: `frontend/src/components/common/AppLayout.vue`, `AppSidebar.vue`, `AppTopBar.vue` (KHÔNG có thư mục `layouts/`)
- **Page header**: `frontend/src/components/common/PageHeader.vue`
- **Common kit**: `frontend/src/components/common/` (21 file — xem §4.1)
- **Composables**: `frontend/src/composables/` (10 file — xem §4.2)
- **Routing model**: `docs/res/Frontend_Router_Navigation_Map.md`
- **Hub launcher**: `docs/res/Launcher_Redesign_IMMIS_Hub_2026-05-05.md`
- **BE error codes** (mapping FE color/UX): `assetcore/services/shared/constants.py` — class `ErrorCode`
- **Workflow fixtures** (StatusBadge mapping source): `assetcore/workflow/*.json` (14 file)
- **Skill phát triển FE**: `.claude/skills/assetcore-fe-module/`

Đọc Launcher Redesign trước nếu thiết kế trang Hub-style. Đọc Router Navigation Map trước khi thêm route.

---

## 17. Roadmap thiết kế (theo Wave)

**Wave 1 (đã có)**: Hub, Dashboard, IMM-04/05/08/09/11/12 list+detail+form. Design system stable. View tree hiện tại bao phủ: `asset/`, `audit/`, `auth/`, `calibration/`, `cm/`, `commissioning/`, `dashboard/`, `document/`, `incident/`, `inventory/`, `master-data/`, `modules/` (hub), `pm/`, `purchase/`, `system/`.

**Wave 2 (đang làm)**: IMM-01/02/03 — planning & procurement (`imm01/`, `imm02/`, `imm03/` đã tồn tại). Cần thêm:
- **Compare table** cho Vendor Evaluation (so sánh ≥ 2 NCC trên cùng tiêu chí — table với column-per-vendor, header sticky, score màu theo ngưỡng).
- **Multi-step form (wizard)** cho Procurement Decision — đưa vào archetype §3.6 và build `Stepper.vue`.
- **Approval matrix UI** cho Board Approver — list các phê duyệt đang chờ + signature pad (canvas, lưu PNG base64 vào DocType).
- **Migration URL** `/imm0X/*` → semantic slug (xem §6.4).

**Wave 3 (planned)**: IMM-13/14/15/16 (Báo cáo, Phân tích, Decommission, Tài chính). Dự kiến cần:
- **Risk heatmap** (matrix màu theo likelihood × impact) — SVG tay, không lib.
- **Asset retirement timeline** (variant của Detail timeline, focus on chronology dài hạn — span năm).
- **Cost breakdown chart** (stacked bar / treemap nhỏ — lại SVG primitive).
- **Cross-module report builder** (chọn doctype, field, filter, group) — dùng `SmartSelect` cascading.

Update tài liệu này khi:
1. Thêm component common mới → cập nhật §4.1 bảng canonical (đếm lại con số).
2. Thêm composable mới → cập nhật §4.2.
3. Thêm IMM module → bổ sung accent ở §7.
4. Thêm/sửa workflow JSON → review StatusBadge ở §4.5.
5. Pattern mới được dùng ≥ 3 nơi → promote thành §3 archetype mới.
6. Đổi tên route module → cập nhật §6.4 và Router Navigation Map.

---

*Tài liệu này có thẩm quyền cao hơn các quyết định ad-hoc trong PR. Bất đồng → mở thread PR và update tài liệu trước, code sau.*
