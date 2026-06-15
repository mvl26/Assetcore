# ADR-IMM00-RESPONSIVE — Mobile-first responsive web (KHÔNG PWA): breakpoint Tailwind sm/md/lg/xl + pattern table→card + touch≥44px + modal full-screen mobile + DoD checklist

| Mục | Giá trị |
|---|---|
| Trạng thái | **Accepted** ([R1-GATE Phase B] — Gate THIẾT KẾ Vòng 1, PHÂN TÍCH). Thực thi từ Vòng 2+ (implement). |
| Ngày | 2026-06-09 |
| Phạm vi | IMM-00 (cross-cutting — FE shell). Áp cho MỌI view list/form/modal/tab-bar trong `frontend/src/views/**`. KHÔNG PWA, KHÔNG re-architect FE. |
| Owner | BA Lead + System Architect |
| Liên quan | `./ADR-IMM00-CMDK.md` (⌘K dialog full-screen mobile + nút hint), `06_Frontend_Design.md`, `assetcore-fe/references/component-patterns.md` + `lessons-learned.md` (nơi ghi DoD) |
| Supersedes | Không — **chuẩn hoá** pattern responsive đã dùng rải rác (37 view đã có `hidden sm:block`/`sm:hidden`) thành DoD bắt buộc. |

> ADR này là **quyết định cuối** cho chiến lược responsive: breakpoint, pattern bắt buộc, touch target, modal mobile, và DoD checklist. Mọi task FE/QA Vòng 2+ phải nhất quán. Khi mâu thuẫn → ADR thắng.
>
> **Bản chất GATE:** gate PHÂN TÍCH — Vòng 1 **KHÔNG đụng code** (`.vue`/`.ts`). Chỉ chốt pattern + DoD + liệt gap có địa chỉ để Vòng 2+ thực thi. Mỗi quyết định D1–D5 **đo được**.

---

## Bối cảnh (vì sao cần GATE này)

KTV TBYT làm việc **tại hiện trường** (point-of-care) cầm điện thoại quét tem QR (xem ADR-QR-SCAN-ACTION) → cần xem danh sách thiết bị, báo hỏng, tạo WO **ngay trên mobile**. Hiện FE có pattern responsive rải rác (37 view dùng `hidden sm:block`/`sm:hidden` card-pattern) NHƯNG **không có DoD bắt buộc** → view mới dễ quên → bảng tràn ngang trên mobile (table không bọc `overflow-x-auto`), tab-bar dài bị cắt, touch target <44px khó bấm. Không cần PWA (offline/installable) — yêu cầu là **mobile-first responsive web** chạy trong browser.

**Nguy cơ nếu KHÔNG chốt:**
- (a) View mới render `<table>` không bọc `overflow-x-auto` → tràn viewport mobile → vỡ layout.
- (b) Mỗi dev chọn breakpoint khác nhau (custom px) → không nhất quán, khó bảo trì.
- (c) Tab-bar/chip-bar dài (vd AssetDetail 5 tab) không cuộn → tab cuối bị cắt mất trên mobile.
- (d) Touch target <44px (nút icon nhỏ) → khó bấm ngón tay → lỗi thao tác hiện trường.
- (e) Modal centered cố định trên mobile → tràn/khó đọc; cần full-screen.
- (f) Không ghi DoD → mỗi vòng lặp lại bug responsive (memory `wave2_ui_bugs` đã ghi nhiều bug English/raw-code; responsive là họ bug kế tiếp).

**5 câu hỏi domain (assetcore-doc Phần 2):**
1. **WHO HTM stage:** Cross-cutting (IMM-00 FE shell) — responsive phục vụ Operation/Maintenance tại hiện trường (mobile KTV).
2. **NĐ98:** Không mandate trực tiếp; nhưng truy cập mobile tại điểm-quét củng cố **báo cáo sự cố kịp thời** (Art.67) + truy xuất nguồn gốc tại chỗ.
3. **Stakeholder:** KTV TBYT (mobile hiện trường), QL phòng vật tư (tablet), admin (desktop). Mobile-first = ưu tiên persona hiện trường.
4. **Lifecycle event:** responsive KHÔNG phát sinh event — chỉ trình bày. Layout-only.
5. **Hậu quả nếu data sai:** layout vỡ mobile → KTV không báo hỏng được tại hiện trường → sự cố không kịp ghi nhận (ảnh hưởng gián tiếp NĐ98 Art.67 timeliness).

---

## FACTS đã verify tại source (cơ sở quyết định — KHÔNG phỏng đoán)

| # | FACT | Evidence (`file:line`) |
|---|---|---|
| F1 | **Tailwind dùng DEFAULT screens** — `tailwind.config.js` KHÔNG khai `theme.screens` ⟹ breakpoint = mặc định **sm 640px / md 768px / lg 1024px / xl 1280px / 2xl 1536px**. Chốt breakpoint chuẩn này, KHÔNG custom px. | `frontend/tailwind.config.js` (no `screens` key) |
| F2 | **Pattern table→card ĐÃ dùng ở 37 view** — `grep -rln 'hidden sm:block\|sm:hidden\|mobile-card-list' src/views` = 37. ⟹ pattern có precedent, ADR chuẩn-hoá thành DoD (KHÔNG phát minh mới). | `grep -rln 'hidden sm:block\|sm:hidden' frontend/src/views` = 37 |
| F3 | **KHÔNG có cấu hình PWA** — `grep -rln 'vite-plugin-pwa\|manifest.webmanifest\|serviceWorker' frontend` = 0. ⟹ quyết định "KHÔNG PWA" sạch, không phải gỡ gì. | `grep` frontend = 0 |
| F4 | **GAP P2 — `AssetDetailView.vue:555` tab-bar KHÔNG cuộn** — `<div class="flex gap-1 mb-4 border-b ...">` chứa 5 tab (`info/depreciation/timeline/kpi/audit`) nhưng **KHÔNG `overflow-x-auto`** → mobile cắt tab cuối. | `frontend/src/views/asset/AssetDetailView.vue:555` |
| F5 | **GAP P3 — `RCAListView.vue:117` THIẾU mobile card** — list dùng `<table>` bọc `overflow-x-auto` (`:117` `<div class="overflow-x-auto">`) NHƯNG **không có nhánh mobile-card** (`hidden sm:block`+`sm:hidden`) → mobile chỉ cuộn ngang bảng (UX kém so với card-list). | `frontend/src/views/*/RCAListView.vue:117` |
| F6 | **GAP P3 — `ListCard.vue:51`** (component dashboard) — cần kiểm tra responsive khi nhúng nhiều card (grid 1-col mobile). | `frontend/src/components/dashboard/ListCard.vue:51` |
| F7 | **GAP P2 — `PersonaDashboardShell.vue:32` KPI tablet** — shell KPI cần kiểm tra grid breakpoint md (tablet) không vỡ. | `frontend/src/components/dashboard/PersonaDashboardShell.vue:32` |
| F8 | **DoD responsive CHƯA tồn tại trong skill FE** — `component-patterns.md` có `## Table` (`:54`) + `## Modal` (`:3`) nhưng KHÔNG mục responsive/mobile-card/touch; `lessons-learned.md` (858 dòng, LL-FE-1..33 + LL-FE-21/22) KHÔNG có rule responsive. ⟹ thêm DoD = net-new (đúng acceptance (e)). | `assetcore-fe/references/component-patterns.md:3,54`; `lessons-learned.md` (grep responsive=0) |
| F9 | **`BaseModal.vue` tồn tại** — modal hiện centered; cần biến thể full-screen mobile (D3). | `frontend/src/components/common/BaseModal.vue` |
| F10 | **`AssetScanInfoView` (màn quét QR mobile) = use-case mobile lõi** — KTV cầm phone quét tem (ADR-QR-SCAN-ACTION) → responsive ở đây là bắt buộc tuyệt đối. | ADR-QR-SCAN-ACTION (F1-F3) |

> **Đính chính số liệu PM giao:** PM ghi gap "AssetDetailView:555 tab-bar, RCAListView:117, ListCard:51, PersonaDashboardShell:32" — **xác thực tại source 2026-06-09: cả 4 địa chỉ ĐÚNG** (F4-F7). AssetDetailView:555 đúng là tab-bar `flex gap-1` thiếu `overflow-x-auto`; RCAListView:117 đúng là `overflow-x-auto` quanh table nhưng thiếu nhánh card mobile.

---

## Quyết định (5 quyết định — DỨT KHOÁT, mỗi quyết định đo được)

### D1 — BREAKPOINT CHUẨN: Tailwind sm/md/lg/xl (default), mobile-first, KHÔNG PWA

**Quyết định (1 dòng):** dùng **breakpoint mặc định Tailwind** (F1), viết **mobile-first** (base = mobile, thêm prefix `sm:`/`md:`/`lg:` cho màn lớn hơn), **KHÔNG PWA** (F3):

| Breakpoint | min-width | Persona điển hình |
|---|---|---|
| (base) | 0 | **Mobile** — KTV hiện trường (phone) |
| `sm:` | 640px | Phone ngang / phablet |
| `md:` | 768px | **Tablet** — QL vật tư |
| `lg:` | 1024px | Laptop / desktop nhỏ |
| `xl:` | 1280px | **Desktop** — admin |

- **Mobile-first:** class base = trạng thái mobile; **KHÔNG** `max-sm:` ngược chiều trừ khi bất khả kháng. Vd `grid-cols-1 md:grid-cols-2` (KHÔNG `grid-cols-2 max-md:grid-cols-1`).
- **KHÔNG PWA:** không service worker, không manifest, không offline cache, không "install app". Responsive web thuần chạy browser.
- **KHÔNG custom breakpoint px** — cấm `min-[900px]:` ad-hoc; nếu cần md/lg đã đủ.

> Đo được: `grep -rn 'min-\[\|max-\[' src/views` = 0 (không ad-hoc px). `tailwind.config` không thêm `screens`. Không có file `manifest.webmanifest`/`sw.ts`.

### D2 — PATTERN BẮT BUỘC (DoD): list table→card, form grid, table overflow, tab-bar cuộn, touch≥44px

**Quyết định (1 dòng):** 5 pattern **bắt buộc** cho mọi view — vi phạm = blocker FE-DoD (giống LL-FE-4/LL-FE-12):

| # | Pattern | Class chốt | Áp cho |
|---|---|---|---|
| P1 | **List = table→card** | desktop `<table>` bọc `hidden sm:block`; mobile `<div class="mobile-card-list sm:hidden">` mỗi record 1 card | mọi List view (F2 precedent) |
| P2 | **Form = 1-col mobile → 2-col desktop** | `grid grid-cols-1 md:grid-cols-2 gap-*` | mọi form create/edit |
| P3 | **MỌI `<table>` bọc `overflow-x-auto`** | `<div class="overflow-x-auto"><table>...</table></div>` | mọi bảng tự do (kể cả khi có card-list — bảng desktop vẫn cần) |
| P4 | **Tab-bar / chip-bar dài cuộn được** | `overflow-x-auto` (cuộn ngang) HOẶC `flex-wrap` (xuống dòng) trên container | mọi tab-bar/chip-bar (vd AssetDetail F4) |
| P5 | **Touch target ≥44px** | `min-h-[44px] min-w-[44px]` (hoặc `h-11 w-11`) cho nút icon/action chạm | mọi nút bấm bằng ngón tay |

> Đo được: QA grep mỗi List view có cặp `hidden sm:block`+`sm:hidden`; mỗi `<table>` có `overflow-x-auto` cha; mỗi form có `grid-cols-1 md:grid-cols-2`; nút action có `min-h-[44px]`. Visual test Playwright viewport 375px (iPhone) → 0 horizontal-scroll body, tab cuối visible.

### D3 — MODAL FULL-SCREEN MOBILE

**Quyết định (1 dòng):** modal (`BaseModal` + biến thể) **full-screen trên mobile**, centered-card trên `sm:`+ :

- Mobile (base): modal chiếm full viewport `inset-0 w-full h-full rounded-none` → dễ đọc/thao tác ngón tay, không tràn.
- `sm:`+: centered card `sm:inset-auto sm:max-w-lg sm:rounded-xl sm:h-auto` (giữ pattern desktop hiện hữu).
- ⌘K dialog (ADR-CMDK D5) **đồng bộ** rule này: full-screen mobile, centered desktop.
- Nút đóng modal ≥44px (P5).

> Đo được: viewport 375px → modal `w-full h-full`; viewport 768px → modal centered max-w-lg. Playwright snapshot 2 viewport.

### D4 — LIỆT P2/P3 GAP CÓ ĐỊA CHỈ (backlog implement Vòng 2+)

**Quyết định (1 dòng):** 4 gap đã xác thực tại source (F4-F7) → backlog có địa chỉ `file:line`, ưu tiên P2 trước P3:

| Ưu tiên | Gap | Địa chỉ | Sửa (chốt) |
|---|---|---|---|
| **P2** | Tab-bar AssetDetail KHÔNG cuộn | `AssetDetailView.vue:555` | thêm `overflow-x-auto` vào `<div class="flex gap-1 ...">` (P4) |
| **P2** | KPI shell vỡ tablet (md) | `PersonaDashboardShell.vue:32` | kiểm tra + sửa grid breakpoint md cho KPI cards |
| **P3** | RCAList thiếu mobile card | `RCAListView.vue:117` | thêm nhánh `sm:hidden` mobile-card-list bên cạnh table `hidden sm:block` (P1) |
| **P3** | ListCard responsive | `ListCard.vue:51` | kiểm tra grid 1-col mobile khi nhúng nhiều card |

> Đo được: sau Vòng 2, 4 địa chỉ trên pass DoD D2 (grep + Playwright 375px). Backlog P2 đóng trước P3.

### D5 — GHI DoD VÀO SKILL FE LÀM CHECKLIST (acceptance (e))

**Quyết định (1 dòng):** DoD responsive (D1-D3) ghi vào **2 nơi trong skill FE** (nguồn `WAVE2-RECURRING-BUGS.md` cũ đã consolidate vào skill FE — xác thực: file standalone KHÔNG còn tồn tại; home hiện tại = `assetcore-fe/references/`):

1. **`assetcore-fe/references/lessons-learned.md`** — thêm **`LL-FE-34: Responsive DoD (mobile-first)`** (nối tiếp LL-FE-1..33): liệt 5 pattern P1-P5 + breakpoint + modal full-screen + "vi phạm = blocker FE-DoD, audit Pillar 6 flag 🟠".
2. **`assetcore-fe/references/component-patterns.md`** — thêm mục **`## Responsive (mobile-first)`** sau `## Table` (`:54`): snippet table→card, form grid, tab-bar overflow, touch-44, modal full-screen mobile.

> Đo được: 2 file skill chứa rule responsive (grep `LL-FE-34`/`## Responsive` > 0). Mọi view Vòng 2+ check checklist này trong DONE-criteria.

---

## Anti-pattern PHẢI tránh (rút từ memory wave2_ui_bugs + lessons-learned)

- ❌ **`<table>` không bọc `overflow-x-auto`** → tràn mobile. P3 bắt buộc.
- ❌ **Custom breakpoint px ad-hoc** (`min-[900px]:`) → không nhất quán. Dùng sm/md/lg/xl (D1).
- ❌ **Tab-bar/chip-bar không cuộn** → cắt item cuối mobile (F4). P4.
- ❌ **Nút icon <44px** → khó bấm hiện trường. P5.
- ❌ **Modal centered cố định mobile** → tràn. Full-screen mobile (D3).
- ❌ **PWA/service worker** → ngoài scope, phức tạp hoá. KHÔNG PWA (D1).
- ❌ **Quên DoD → lặp bug responsive mỗi vòng** → ghi skill (D5).

---

## Test-case TDD sẽ viết ở Vòng implement (D-TEST)

| ID | Mức | Khẳng định |
|---|---|---|
| TC-RWD-01 | static/grep | `grep -rn 'min-\[\|max-\[' src/views` = 0 (không ad-hoc breakpoint px) (D1). |
| TC-RWD-02 | static/grep | mọi List view có cặp `hidden sm:block` (table) + `sm:hidden` (card-list) (P1). |
| TC-RWD-03 | static/grep | mọi `<table>` trong views có cha `overflow-x-auto` (P3). |
| TC-RWD-04 | static/grep | mọi form create/edit có `grid-cols-1 md:grid-cols-2` (P2). |
| TC-RWD-05 | static/grep | nút action chạm có `min-h-[44px]` (P5). |
| TC-RWD-06 | visual/Playwright | viewport 375px (iPhone): body KHÔNG horizontal-scroll trên AssetList/IncidentList/AssetScanInfo (D2). |
| TC-RWD-07 | visual/Playwright | viewport 375px: AssetDetail tab-bar cuộn, tab cuối "audit" reachable (F4 fix). |
| TC-RWD-08 | visual/Playwright | modal: 375px → full-screen (`w-full h-full`); 768px → centered max-w-lg (D3). |
| TC-RWD-09 | visual/Playwright | RCAList 375px → render card-list (KHÔNG chỉ table cuộn ngang) (F5 fix). |
| TC-RWD-10 | doc | `lessons-learned.md` chứa `LL-FE-34`; `component-patterns.md` chứa `## Responsive` (D5). |

---

## Tác động & non-goals

**Đụng (Vòng 2+ implement):** sửa 4 gap (F4-F7: `AssetDetailView.vue`, `PersonaDashboardShell.vue`, `RCAListView.vue`, `ListCard.vue`), thêm biến thể full-screen `BaseModal.vue`, áp DoD cho view mới, ghi `lessons-learned.md` (LL-FE-34) + `component-patterns.md` (## Responsive), bồi `06_Frontend_Design.md`.

**NON-GOAL (KHÔNG làm ADR này):** KHÔNG PWA/offline/installable; KHÔNG native app; KHÔNG re-design layout shell (AppLayout giữ nguyên cấu trúc); KHÔNG đổi design tokens/màu; KHÔNG custom breakpoint; KHÔNG audit-rewrite toàn bộ 37 view đã đúng (chỉ 4 gap + DoD cho view mới — light-touch).

---

*Gate THIẾT KẾ Vòng 1 — PHÂN TÍCH. KHÔNG đụng code. Thực thi D1–D5 từ Vòng 2. Mọi spec FE phải cross-link ADR này khi nói về responsive / mobile.*
