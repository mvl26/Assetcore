# AssetCore Design System

A design system for **AssetCore** — a medical-equipment lifecycle management platform (HTM / CMMS) built on ERPNext/Frappe, used by hospitals (initially **Bệnh Viện Nhi Đồng 1** — Children's Hospital 1, HCMC) and delivered by Miyano.

The product orchestrates the full WHO HTM lifecycle:
**Needs → Procurement → Installation → Operation → Maintenance → Decommission**, decomposed into **17 modules (IMM-01 → IMM-17)** with role-based access.

> Language note: the product UI is **Vietnamese-first**. All copy in this design system is written as it would appear in product.

---

## Sources

| Source | Notes |
|---|---|
| `mvl26/assetcore` @ `feature/hieuc/wave-2` (GitHub) | Vue 3 + TypeScript + Tailwind frontend. Source of truth for components, tokens, copy. |
| `assets/dashboard-reference.jpg` | Module-hub mock from product team (illustrative; not the implemented design). |
| `assets/logo-miyano.png`, `assets/logo-nd1.png` | Delivery partner + hospital logos. |
| Repo `CLAUDE.md` | Domain glossary and architectural principles (WHO HTM lifecycle, work-order engine, QMS, etc.). |

---

## Index

- `README.md` — this file
- `colors_and_type.css` — tokens (CSS custom properties + semantic typography classes)
- `SKILL.md` — Agent-Skill manifest
- `assets/` — logos, the dashboard reference mock
- `preview/` — design-system tab cards (foundations + components)
- `ui_kits/web/` — Vue→JSX recreation of the AssetCore admin app (sidebar, topbar, dashboard, module hub, work-order list)
- `slides/` — *(none — no decks were attached)*

---

## 1 · What AssetCore is

> _"AssetCore là hệ thống quản lý vòng đời thiết bị y tế (HTM) xây trên ERPNext (Frappe)."_

A single back-office app for biomedical-engineering departments. Not a CMMS in isolation — it is an "operating architecture" stitching together planning, procurement, commissioning, PM/CM/calibration, spare parts, compliance, and decommission, all anchored to one **Lifecycle Event** stream for audit traceability.

### The 17 modules

| Phase | Module | Title (VI) | English |
|---|---|---|---|
| **A · Planning** | IMM-01 | Nhu cầu & Dự toán | Needs & Budget |
| | IMM-02 | Thông số kỹ thuật | Tech Specs |
| | IMM-03 | Đánh giá NCC & Mua sắm | Vendor Eval & Procurement |
| **B · Deployment** | IMM-04 | Lắp đặt & Nghiệm thu | Installation & Commissioning |
| | IMM-05 | Đăng ký & Hồ sơ | Registration & Documents |
| | IMM-06 | Đào tạo người dùng | User Training |
| **C · Operation** | IMM-07 | Theo dõi hiệu suất | Performance Monitoring |
| | IMM-08 | Bảo trì định kỳ (PM) | Preventive Maintenance |
| | IMM-09 | Sửa chữa (CM) | Corrective Maintenance |
| | IMM-10 | _reserved_ | — |
| | IMM-11 | Hiệu năng & Hiệu chuẩn | Performance & Calibration |
| | IMM-12 | Sự cố & RCA/CAPA | Incidents & RCA / CAPA |
| | IMM-15 | Tồn kho phụ tùng | Spare-parts Inventory |
| | IMM-16 | Theo dõi tuân thủ | Compliance Tracking |
| | IMM-17 | Tích hợp & API | Integration & API |
| **D · End-of-Life** | IMM-13 | Điều chuyển | Transfer |
| | IMM-14 | Giải nhiệm & Khấu hao | Decommission & Depreciation |

Users land on a **Launcher** (the module hub) and drill into one module at a time. The sidebar is **module-scoped** — only the active module's nav items are shown; clicking the brand logo returns to Launcher.

### Roles
Multi-tenant by **role**: Biomedical Engineer, Department Head, Procurement, Finance, Compliance/QMS, Clinical User, External Vendor. Each module surfaces a subset of the data depending on role.

---

## 2 · Content fundamentals

### Language
- **Primary: Vietnamese.** Diacritics are always kept (`Lắp Đặt`, not `Lap Dat`).
- Module names are written `IMM-04 · Lắp đặt & Nghiệm thu` — code, middot, full title.
- English appears only for technical terms with no settled VI translation: **PM**, **CM**, **CAPA**, **RCA**, **SLA**, **QR**, **API**, **FHIR**, **HTM**, **UDI**.

### Tone
**Formal-functional.** This is hospital ops software — not consumer SaaS. Copy is direct, terse, and unambiguous. No marketing flourishes, no emoji.

**Pronoun stance:** the system addresses the user as a peer, not a "you" — most strings are noun phrases or imperatives without a subject.

| ✅ Good | 🚫 Avoid |
|---|---|
| `Đề xuất nhu cầu` | `Hãy đề xuất nhu cầu của bạn nhé!` |
| `Đánh dấu tất cả đã đọc` | `Click here to mark everything read 👍` |
| `Trang này không thuộc module nào.<br>Mở Launcher để chọn module.` | `Oops! Looks like you're lost.` |
| `Đang khởi tạo…` | `One sec…` |
| `Đăng nhập thất bại. Vui lòng kiểm tra lại.` | `Wrong creds!` |

### Casing
- **Sentence case** for body text, button labels, table headers (`Đăng nhập hệ thống`, `Đánh dấu tất cả đã đọc`).
- **UPPERCASE with tracking** only for very small section eyebrows (`CHỨC NĂNG MODULE`, `font-size: 10–11px, letter-spacing: 0.12em`).
- Module titles use **Title Case** in Vietnamese (`Lắp Đặt & Nghiệm Thu` on cards, `Lắp đặt & nghiệm thu` in running text).

### Microcopy patterns
- **Time:** relative VI — `30s trước`, `12 phút trước`, `3 giờ trước`, `2 ngày trước`.
- **Empty state:** one short line of *why*, one short line of *what to do*. Example: `Không có thông báo mới`. Or `Trang này không thuộc module nào. Mở Launcher để chọn module.`
- **Loading:** `Đang [verb]…` — `Đang tải...`, `Đang khởi tạo...`, `Đang đăng nhập...`.
- **Confirmation:** never just "OK" — always state the action: `Đánh dấu tất cả đã đọc`, `Mở Launcher`, `Cập nhật hồ sơ nhân sự →`.

### Emoji & symbols
- **No emoji.** Anywhere. This is regulated-domain software.
- Allowed unicode: `→` (continuation in CTAs), `·` (separator in titles), `/` (breadcrumb separator). Numeric IDs use a real **EN dash** in `IMM-04` (hyphen-minus is acceptable in code; either renders).

---

## 3 · Visual foundations

### Color
A cool, clinical blue palette over white surfaces and slate text. **No gradients except** the brand logo lockup and the login backdrop wash.

- **Primary** `#2563eb` (`brand-600`). Hover `#1d4ed8` (`brand-700`). Used for primary buttons, active nav rail, links, focus ring.
- **Surface**: `#ffffff` cards on `#f4f6fa` page background.
- **Sidebar**: near-black `#0f1623` (custom — not in the Tailwind ink scale). Active item: `rgba(59,130,246,0.25)` with an inset 3px `#3b82f6` left rail.
- **Text**: `#0f172a` primary, `#475569` secondary, `#94a3b8` muted. (Roughly `slate-900 / 600 / 400`.)
- **Semantic**: success `#059669`, warning `#d97706`, danger `#dc2626`, info `#2563eb`.

### Typography
Three families, all from **Google Fonts** (loaded via `<link rel="preconnect">` in `index.html`):

- **Inter** — body, UI, data. Weights 400/500/600/700. OpenType features enabled: `cv02 cv03 cv04 cv11`.
- **Manrope** — display (h1–h4). Weights 500/600/700/800. Tight letter-spacing `-0.015em`.
- **JetBrains Mono** — code, IDs, asset codes, QR labels. Weights 400/500/600.

Base size **15px** at `html`. Scale is gently above Tailwind defaults (xs `13px`, sm `15px`, base `17px`, lg `19px`, xl `21px`, 2xl `24px`, 3xl `30px`) — readable in dense data tables without feeling cramped.

### Spacing & radius
- Layout uses an 8-pt rhythm via Tailwind defaults; cards are padded `p-7` (28px).
- **Radii**: button `7px` (`--radius-btn`), card `10px` (`--radius-card`), input `8px` (Tailwind `rounded-lg`), modal/dropdown `12px` (`rounded-xl`), badge `9999px` (full pill).
- Sidebar width: `256px` expanded, `64px` collapsed. Topbar height: `56px`.

### Shadows
Layered, very low-contrast — never dramatic.
- `shadow-card`: `0 1px 3px rgba(0,0,0,.06), 0 0 0 1px rgba(0,0,0,.04)` (default card)
- `shadow-card-hover`: `0 6px 16px rgba(0,0,0,.10), 0 0 0 1px rgba(0,0,0,.04)` (hover lift)
- `shadow-dropdown`: `0 8px 24px -4px rgba(0,0,0,.14), 0 0 0 1px rgba(0,0,0,.06)` (menus, popovers)
- `shadow-focus`: `0 0 0 3px rgba(37,99,235,.20)` (focus ring — replaces native outline)
- Sidebar gets `4px 0 24px rgba(0,0,0,0.4)` against the page — the only dramatic shadow in the system.

### Borders
- Default: `1px solid #e2e8f0` (`slate-200`). Stronger variant `#cbd5e1` for emphasized dividers.
- Cards combine a `1px ring` shadow with the explicit border for crisp edges on white-on-white.
- KPI cards get a `3px` colored top stripe (`::before` pseudo, color set via `--kpi-color` var).

### Animation
Short, fast, ease-out. Never bouncy. Never decorative.

- `fade-in` 250ms, `slide-up` 300ms, `slide-in` 250ms (horizontal), `scale-in` 200ms.
- **Stagger** list-item entries by **40ms** for items 1–8 (`.stagger-1`..`.stagger-8`).
- **Shimmer** 1.6s linear infinite — only on skeleton placeholders.
- **Pulse-subtle** 2.5s — only on a "pending" indicator dot.
- Hover transitions: `transition-all duration-150` (buttons, nav items). Sidebar collapse: `duration-250`.

### Interaction states
- **Hover** (buttons): darken to `-700` shade + opacity-stable. Nav items: lighten background `rgba(255,255,255,0.1)`, slide `translateX(2px)`.
- **Press**: no shrink. The brand doesn't bounce — it presses cleanly via color change.
- **Focus-visible**: outline replaced with `box-shadow: 0 0 0 3px rgba(37,99,235,.20)`.
- **Disabled**: `opacity-50 cursor-not-allowed`. Form inputs go `bg-slate-50 text-slate-500`.
- **Active nav**: 3px inset left rail + tinted background. Never a full-fill primary color.

### Backgrounds & imagery
- Page background is a single flat `#f4f6fa`. **No** repeating patterns, **no** textures.
- Cards are flat white. Modal/dropdown surfaces are flat white with a 1px ring.
- The only image-as-background is the **Login** screen: a soft `bg-gradient-to-br from-blue-50 to-indigo-100`. Everything else is flat.
- The reference dashboard mock (`assets/dashboard-reference.jpg`) uses a cartoon hospital-grounds illustration — this is an **illustrative concept only** and not present in the shipped UI. Don't reproduce it.
- Photography / illustration vibe (when used): cool, clinical, daylight; never warm; no grain; no duotone.

### Transparency & blur
Used sparingly:
- Hover states on dark sidebar: `rgba(255,255,255,0.05–0.12)`.
- Active nav background: `rgba(59,130,246,0.25)` for soft selection on dark.
- Notification "unread" row: `bg-blue-50/40`.
- **No `backdrop-blur`** anywhere — this is opinionated. Add only if the user explicitly asks for it.

### Layout rules
- **Fixed sidebar** (`position: fixed`, left 0). **Fixed topbar** (`position: fixed`, top 0, left = sidebar width). Content fills the remainder.
- Page content is wrapped in `.page-container` (`px-4 sm:px-6 lg:px-8 py-6 md:py-7`) — never centered max-width; data-dense pages want full width.
- Tables sit in `.table-wrapper` (rounded-lg, white, 1px border). Headers `uppercase tracking-wide` slate-50 background.
- The KPI grid is `grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4`.

### Iconography
See `## 5 · Iconography` below.

---

## 4 · Iconography

**The codebase ships its own inline-SVG icon set.** Icons live as a `const ICONS: Record<string, string>` map in `frontend/src/components/common/AppSidebar.vue` — 32 hand-curated stroke icons rendered via `v-html`. Style is **2px stroke** (`stroke-width="1.7"` in source, `1.8` in topbar), **18×18 px**, `currentColor`, `round` linecaps and joins, **outlined** (no fills except occasional dot accents on the QR / list icons).

Visually, this set sits in the same family as **Lucide / Feather** — and where the codebase didn't define a name we use, we substitute the closest Lucide icon at the same weight. The substitution is flagged in `colors_and_type.css` and the relevant card.

**Inventory (from `AppSidebar.vue` ICONS map):**
`grid · device · template · transfer · trending · cart · clipboard · chart · wrench · calendar · list · tool · code · gauge · alert · shield · log · folder · inbox · box · cog · arrows · warehouse · uom · building · contract · clock · database · users · qr · home`

**Iconography rules:**
- Match stroke weight (1.7–1.8). **Never** mix outlined and filled.
- Nav icons render at **18px**. Topbar action icons (bell, chevron) at 18px. Sub-row glyphs (initials avatar) at 14px.
- Icons get `opacity: 0.6` in their resting state and `opacity: 1` on hover/active.
- **No emoji.** Anywhere. (Also documented in §2.)
- **No third-party icon-font dependency** — the brand prefers controlling each glyph.
- **Logos:** `assets/logo-nd1.png` (hospital — round seal, used in topbar lockup), `assets/logo-miyano.png` (delivery partner — used in About/footer; also serves as the app favicon in the repo).

If you need an icon not in the set, copy a Lucide outline icon at `stroke-width=1.7` and flag the addition.

---

## 5 · Font substitution flag

All three families (**Inter, Manrope, JetBrains Mono**) are loaded from Google Fonts — no local `.ttf` files are shipped in the codebase. The system in `colors_and_type.css` references them via `@import`. No substitution needed.

---

## 6 · Open questions / caveats

See the **CAVEATS** section in the chat that delivered this system.
