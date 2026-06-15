# ADR-IMM00-CMDK — Command Palette ⌘K: registry SSoT từ `MODULE_NAV`+route + capability-gate tái dùng + fuzzy/diacritic-fold VI + a11y component riêng

| Mục | Giá trị |
|---|---|
| Trạng thái | **Accepted** ([R1-GATE Phase B] — Gate THIẾT KẾ Vòng 1, PHÂN TÍCH). Thực thi từ Vòng 2+ (implement). |
| Ngày | 2026-06-09 |
| Phạm vi | IMM-00 (cross-cutting — FE shell). Chạm `AppLayout.vue`, `AppTopBar.vue`, `sidebarNav.ts`, `routeAccess.ts`, router. KHÔNG re-architect BE/route, KHÔNG fork nguồn nav. |
| Owner | BA Lead + System Architect |
| Liên quan | `./ADR-IMM00-QR-SCAN-ACTION.md` (capability-gate KHÔNG role-name), `./ADR-IMM00-LIST-SCOPE.md` (anti-leak), memory `role-profile-persona-architecture` (persona FE-only, capability SSoT), `06_Frontend_Design.md` |
| Supersedes | Không — **bổ sung** lối điều hướng nhanh ⌘K trên FE shell hiện hữu. |

> ADR này là **quyết định cuối** cho Command Palette ⌘K: nguồn registry, cơ chế gate, search, keyboard, a11y. Mọi task FE/QA Vòng 2+ phải nhất quán với ADR này. Khi mâu thuẫn → ADR thắng.
>
> **Bản chất GATE:** gate PHÂN TÍCH — Vòng 1 **KHÔNG đụng code** (`.vue`/`.ts`). Chỉ chốt nguồn + gate + search + a11y + sidebar-gọn để Vòng 2+ thực thi. Mỗi quyết định D1–D7 **đo được**; mỗi task map tới đúng 1 quyết định. Phụ lục A audit 130 `meta.title` trước khi feed (acceptance).

---

## Bối cảnh (vì sao cần GATE này)

AssetCore phơi nhiều module (IMM-00..17) qua sidebar nav. Admin/persona đa-module phải click qua nhiều cấp sidebar để tới 1 màn — chậm, overload. ⌘K (Command Palette) là lối nhảy-tức-thì tới bất kỳ đích nào **user có quyền**. Rủi ro lớn nhất: nếu registry/gate của ⌘K **fork** khỏi nguồn nav hiện hữu → drift gate → ⌘K hiện đích user **không có quyền** → click → `/unauthorized` (anti-leak vỡ), HOẶC ẩn đích user **có quyền** (nút chết). Memory `role_profile_persona_architecture` + ADR-QR-SCAN-ACTION đã chốt: **gate = capability, KHÔNG role-name** (anti-pattern "RBAC dead-gate"). ⌘K phải tái dùng đúng predicate gate đó.

**Nguy cơ nếu KHÔNG chốt:**
- (a) Tạo **nguồn registry thứ 3** (list lệnh hardcode riêng cho ⌘K) ≠ `MODULE_NAV` ≠ route → 3 nơi drift, thêm màn quên cập nhật ⌘K.
- (b) Gate ⌘K bằng **role-name** (`hasAnyRole`) → anti-pattern RBAC dead-gate (memory): nút chết âm thầm khi đổi role; HOẶC bỏ gate → lộ đích vượt quyền (anti-leak vỡ).
- (c) Search exact-match → gõ "bao tri" (không dấu) không ra "Bảo trì" → user không tìm được → ⌘K vô dụng cho người gõ nhanh không dấu.
- (d) Tái dùng `BaseModal` (thiếu focus-trap) → ⌘K không trap focus, không return-focus, không combobox a11y → fail WCAG, screen-reader không đọc được.
- (e) Bind phím tay (`addEventListener keydown`) → leak listener, không cleanup, xung đột — trong khi `@vueuse/core` đã có `useMagicKeys`.

**5 câu hỏi domain (assetcore-doc Phần 2):**
1. **WHO HTM stage:** Cross-cutting (IMM-00 foundation FE shell) — phục vụ điều hướng MỌI stage.
2. **NĐ98:** Không mandate trực tiếp. Nhưng **anti-leak** (KHÔNG hiện đích vượt quyền) gián tiếp bảo vệ phân quyền dữ liệu thiết bị (vendor isolation, RBAC) — cùng nguyên tắc ADR-LIST-SCOPE.
3. **Stakeholder:** mọi persona (admin đa-module hưởng lợi nhất); người dùng power-user gõ nhanh.
4. **Lifecycle event:** ⌘K KHÔNG phát sinh event — chỉ **điều hướng** (router.push). Read-only navigation.
5. **Hậu quả nếu data sai:** gate sai → leo quyền điều hướng (lộ tồn tại màn vượt quyền) hoặc nút chết; a11y thiếu → loại trừ người dùng trợ năng.

---

## FACTS đã verify tại source (cơ sở quyết định — KHÔNG phỏng đoán)

| # | FACT | Evidence (`file:line`) |
|---|---|---|
| F1 | **`MODULE_NAV` = registry nav SSoT** — `export const MODULE_NAV: Record<string, ModuleNav>` (map module→nhóm→`NavItem[]`). Persona resolve `persona.modules → MODULE_NAV → grouped sidebar`. | `frontend/src/constants/sidebarNav.ts:59` |
| F2 | **`itemVisible(item, can, isSuperuser)` = predicate gate nav-entry SSoT** — `if isSuperuser return true; if item.cap===undefined return true; return can(item.cap)`. Gate bằng **capability** (`item.cap`), KHÔNG role-name. | `sidebarNav.ts:205` |
| F3 | **`resolveRouteAccess(meta, ctx)` = predicate gate route-entry SSoT** — admin bypass → `'allow'`; còn lại quyết định authorization theo capability trong `meta`. Trả `'allow'`/`'deny'`/route đích. | `frontend/src/router/routeAccess.ts:57` |
| F4 | **`@vueuse/core ^10.9.0` ĐÃ là dependency** (có `useMagicKeys`). | `frontend/package.json:22` |
| F5 | **`useMagicKeys` CHƯA dùng ở đâu** — greenfield (`grep -rn useMagicKeys src` = 0 ngoài chính ADR). Bind ⌘K là net-new. | `grep src` = 0 |
| F6 | **`BaseModal.vue` tồn tại nhưng KHÔNG focus-trap** — không component nào dùng `focus-trap`/`focusTrap` lib (`grep -rln focus-trap src` = 0). ⟹ tái dùng `BaseModal` cho ⌘K = thiếu trap/return-focus/combobox a11y. | `src/components/common/BaseModal.vue`; `grep focus-trap` = 0 |
| F7 | **`AppLayout.vue` + `AppTopBar.vue` (cả hai ở `frontend/src/components/common/`) đều `<script setup lang="ts">`** — chỗ đặt `useMagicKeys` toàn cục (`AppLayout` bao toàn app). ⚠️ **Đính chính source 2026-06-09:** `AppTopBar` **CHƯA có** nút search (`grep -n 'search\|Tìm' AppTopBar.vue` = 0); dòng `:198-199` thực ra là **Notification Bell** (`:197` `<!-- Notification Bell -->`). ⟹ nút hint ⌘K là **net-new** (thêm vào top-bar cạnh Bell), KHÔNG "đã có". | `components/common/AppLayout.vue:1`; `components/common/AppTopBar.vue:1` (Bell `:197`, search=0) |
| F8 | **Anti-leak + capability-only là luật chốt** (memory `role_profile_persona_architecture`, ADR-QR-SCAN-ACTION D2 "gate=capability KHÔNG role-name", `lessons-learned.md:LL-FE-12` "Role gating CHỈ dùng useCapabilities, không hasAnyRole"). | memory + `assetcore-fe/references/lessons-learned.md:191` |
| F9 | **Route tĩnh không-nav tồn tại** — router có route KHÔNG nằm trong `MODULE_NAV` (vd create-view `/incidents/new`, `/pm/work-orders/new`, ... gate bởi `meta.requiredCapabilities`). ⌘K muốn phủ "tạo nhanh" phải gộp cả route-entry này (D1). | `frontend/src/router/index.ts` (route create-view có `meta.requiredCapabilities`) |
| F10 | **Tailwind default screens** (sm640/md768/lg1024/xl1280) — `tailwind.config.js` KHÔNG custom `screens` → `mobile no-keyboard` xác định bằng absence-of-keyboard, hint button hiện trên mọi viewport, ⌘K dialog full-screen mobile (đồng bộ ADR Responsive). | `frontend/tailwind.config.js` (no `screens`) |
| F11 | **130 route có `meta.title`** — `grep -c "title:" router/index.ts = 130` (đúng số PM giao). Đây là nguồn nhãn cho command `source:'route'` (D1). PHẢI audit leak TRƯỚC khi feed (xem Phụ lục A). | `frontend/src/router/index.ts` (130 × `title:`) |
| F12 | **CHỈ 1 route-title leak user-facing** — `title: 'Quét QR — GMDN Status'` (router `:95`) rò **jargon module "GMDN"** + **English "Status"** vào palette/breadcrumb. 129 title còn lại sạch (VI thuần; ngoặc đơn `(RCA)/(CAPA)/(ISO 13485)/(AVL)/(UOM)/(NCC)` = domain-anchor có chủ đích, KHÔNG leak). Đã ghi STATE.md §FE-P2/P3. | `router/index.ts:95` |
| F13 | **1 route dev-only** — `title: 'Tổng quan Thiết bị (Debug)'` (router `:957`) có `devOnly: true` + `data.admin` → loại khỏi feed CMDK (D1-bis). Không phải user-facing leak nhưng KHÔNG được vào registry production. | `router/index.ts:957` |
| F14 | **Sidebar nhóm theo `sidebarGroups`/`ModuleNav.groups`** — `MODULE_NAV` map module→**nhóm**→`NavItem[]`; admin/persona đa-module render NHIỀU nhóm → dài. Có chỗ chốt "nhóm ít dùng default-collapse" thuần thị giác (D7) KHÔNG đụng `itemVisible`/RBAC. | `sidebarNav.ts:59` (`groups`) |

---

## Quyết định (7 quyết định — DỨT KHOÁT, mỗi quyết định đo được)

### D1 — REGISTRY SSoT: view thứ 2 trên `MODULE_NAV` + route tĩnh không-nav, KHÔNG fork nguồn thứ 3

**Quyết định (1 dòng):** danh mục lệnh ⌘K = **dẫn xuất (derived view)** từ 2 nguồn ĐÃ CÓ, KHÔNG list hardcode mới:

1. **Nguồn chính = `MODULE_NAV`** (`sidebarNav.ts:59`) — flatten mọi `NavItem` của mọi module → command "đi tới <màn>".
2. **Bổ sung = route tĩnh không-nav** (`router/index.ts`, F9) — route có `meta.requiredCapabilities` nhưng KHÔNG trong sidebar (vd create-view "Tạo báo hỏng", "Tạo PM"). Lấy từ `router.getRoutes()`, lọc route có `meta.title`/`meta.cmdk:true` và KHÔNG trùng `MODULE_NAV`.

Composable mới **`useCommandRegistry()`** (FE) build list `CommandItem { id, title, subtitle?, icon?, to (route), cap?, source: 'nav'|'route', moduleId? }` từ 2 nguồn trên. **KHÔNG** tạo file `commands.ts` hardcode tách rời.

**D1-bis — FEED-SAFETY (anti-leak nhãn, BẮT BUỘC trước Vòng 2):** nhãn command `source:'route'` lấy từ `meta.title` → PHẢI sạch (KHÔNG English status / raw-code / jargon module — luật anti-leak chung). Audit 130 title (Phụ lục A) chốt:
- (1) **Loại route `meta.devOnly===true`** khỏi registry (F13: `'Tổng quan Thiết bị (Debug)'`) — không vào palette production dù admin.
- (2) **Sửa `router:95`** `'Quét QR — GMDN Status'` → `'Mở hồ sơ thiết bị'` (F12 — bỏ jargon GMDN + English "Status") **TRƯỚC** khi feed CMDK; cùng nhịp với fix STATE.md §FE-P2/P3 (QrResolve/QRScan meta.title). Đây là tiền-điều-kiện DoD CMDK — feed title bẩn = anti-leak vỡ.
- (3) 128 title còn lại sạch (VI-native, gồm ~9 có ngoặc-đơn domain-anchor hợp lệ; trừ 1 leak `:95` + 1 devOnly `:957`) → feed an toàn nguyên trạng (Phụ lục A).

> Đo được: thêm 1 `NavItem` vào `MODULE_NAV` → command tương ứng xuất hiện trong ⌘K **không sửa code ⌘K**. QA test: `useCommandRegistry()` chứa mọi `NavItem.to` của `MODULE_NAV` + route tĩnh whitelisted; KHÔNG có entry nào hardcode ngoài 2 nguồn; 0 command có nhãn chứa `devOnly` route / 'GMDN' / 'Status'.

### D2 — GATE: TÁI DÙNG `itemVisible` (nav) + `resolveRouteAccess` (route) — capability KHÔNG role-name, KHÔNG bao giờ hiện đích `/unauthorized`

**Quyết định (1 dòng):** ⌘K **lọc** command qua **đúng predicate gate đã có** — KHÔNG viết predicate gate thứ 2:

- Command `source:'nav'` → filter qua **`itemVisible(item, can, isSuperuser)`** (`sidebarNav.ts:205`, F2).
- Command `source:'route'` → filter qua **`resolveRouteAccess(meta, ctx) === 'allow'`** (`routeAccess.ts:57`, F3).
- `can`/`isSuperuser`/`ctx` lấy từ **`useCapabilities()`** store (capability-based, KHÔNG `hasAnyRole`, F8 / LL-FE-12).

**Bất biến anti-leak:** ⌘K **CHỈ** hiển thị command mà predicate trả truthy. Click bất kỳ command đã-hiện → KHÔNG BAO GIỜ landing `/unauthorized`. Command bị gate → **ẩn hoàn toàn** (KHÔNG render disabled — khác ADR-QR-SCAN-ACTION D2 nơi nút disabled+tooltip có chủ đích; ở ⌘K, hiện-disabled = lộ tồn tại màn vượt quyền = anti-leak vỡ → ẨN).

> Đo được: với user thiếu capability X, mọi command yêu cầu X **vắng mặt** trong kết quả ⌘K. QA test: render ⌘K với capability set rỗng → chỉ command `cap===undefined` (mở-cho-mọi-user) hiện; click mọi command hiện → route guard không redirect `/unauthorized`.

### D3 — SEARCH: fuzzy substring + token + diacritic-fold VI, KHÔNG thư viện ngoài

**Quyết định (1 dòng):** matching **tự viết** (utility thuần TS) gồm 3 lớp, KHÔNG thêm fuzzy lib (Fuse.js…):

1. **Diacritic-fold VI** — chuẩn hoá query + title qua `String.normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/đ/gi,'d')` → "bao tri" khớp "Bảo trì", "thiet bi" khớp "Thiết bị".
2. **Substring match** trên chuỗi đã fold (case-insensitive).
3. **Token match** — tách query theo space, mọi token phải xuất hiện (AND) trong title-folded → "tao bao hong" khớp "Tạo báo hỏng".

Ranking: exact-prefix > token-all-prefix > substring > recent/pinned boost (D6). Utility **`foldVi(s)`** + **`matchCommand(query, item)`** ở `frontend/src/utils/` (tái dùng được cho search khác).

> Đo được: gõ "bao tri" → trả command có title "Bảo trì *"; gõ "thiet bi" → "Thiết bị"; gõ "tao pm" → "Tạo PM / Yêu cầu bảo trì". QA test bảng `{query → expected top result}` cho ≥10 cặp không-dấu↔có-dấu.

### D4 — BIND PHÍM: `useMagicKeys` (⌘K/Ctrl+K) toàn cục ở `AppLayout` + nút hint trên `AppTopBar` (mobile no-keyboard)

**Quyết định (1 dòng):** mở ⌘K qua **`useMagicKeys()`** (`@vueuse/core`, F4) ở `AppLayout.vue` (bao toàn app, F7) + **nút hint** mở palette trên `AppTopBar` cho mobile/không-bàn-phím:

- `const { Meta_K, Ctrl_K } = useMagicKeys()` → `watch` → toggle store `useCommandPalette().open`. `preventDefault` để không trigger browser bookmark (⌘K Firefox/search). Cleanup tự động (vueuse) — KHÔNG `addEventListener` tay (F5 tránh leak listener).
- **Nút hint** trên `AppTopBar` (thêm **net-new** cạnh Notification Bell `:197`, F7 — KHÔNG có vùng search sẵn): icon 🔍 + label "Tìm nhanh" + badge "⌘K" (desktop) → click mở palette. Mobile không bàn phím → **nút là lối vào duy nhất** (badge ⌘K ẩn `hidden sm:inline`, đồng bộ ADR Responsive). Touch target ≥44px (ADR Responsive D-pattern).
- Store **`useCommandPalette`** (Pinia) — `open: boolean`, `query`, `recent[]`, `pinned[]` (D6). Single source mở/đóng → bất kỳ chỗ nào (nút, phím, route-guard) toggle 1 store.

> Đo được: nhấn ⌘K (mac) / Ctrl+K (win) ở mọi route → palette mở, browser default bị chặn. Click nút hint mobile → palette mở. QA: simulate keydown → store.open=true; nút có `min-h-[44px]`.

### D5 — A11Y: component RIÊNG (KHÔNG tái dùng `BaseModal`) — role=dialog aria-modal + combobox/listbox + Arrow/Enter/Escape + focus-trap+return-focus

**Quyết định (1 dòng):** ⌘K là **component RIÊNG** `CommandPalette.vue` (KHÔNG `BaseModal`, F6 thiếu trap) với hợp đồng a11y đầy đủ:

| Khía cạnh | Chốt |
|---|---|
| Container | `role="dialog"` `aria-modal="true"` `aria-label="Tìm nhanh"` |
| Input | `role="combobox"` `aria-expanded` `aria-controls=<listbox id>` `aria-activedescendant=<active option id>` |
| Kết quả | `role="listbox"`; mỗi item `role="option"` `aria-selected` |
| Keyboard | `ArrowDown`/`ArrowUp` di chuyển active (wrap), `Enter` chọn (router.push), `Escape` đóng + return-focus, `Home`/`End` đầu/cuối |
| Focus-trap | trap focus trong dialog khi mở (Tab/Shift+Tab vòng trong); **return-focus** về element đang focus trước khi mở (lưu `document.activeElement`) |
| Implement trap | tự viết (vueuse `useFocusTrap` nếu `@vueuse/integrations` có; nếu không → wrap thủ công đầu/cuối tabbable) — KHÔNG thêm dep nặng |

> Đo được: mở ⌘K → focus vào input; ArrowDown highlight item kế (aria-activedescendant đổi); Enter điều hướng; Escape đóng + focus trở lại nút/element gốc; Tab không thoát khỏi dialog. QA: a11y test (Vitest + Testing Library) assert role/aria + keyboard flow.

### D6 — GIẢM OVERLOAD: Gần đây (localStorage, max 5) + Ghim

**Quyết định (1 dòng):** khi query rỗng, palette hiện **Gần đây** (max 5, persist `localStorage`) + **Ghim** (pinned) lên đầu để admin đa-module không phải gõ:

- **Gần đây:** mỗi lần chọn 1 command → unshift vào `recent[]` (dedupe theo `id`), cắt **max 5**, persist `localStorage` key `ac_cmdk_recent`. Hiện khi `query===''`.
- **Ghim:** user ghim command (icon 📌) → `pinned[]` persist `localStorage` `ac_cmdk_pinned`. Hiện trên cùng, trước Gần đây.
- **Gate vẫn áp:** recent/pinned vẫn lọc qua D2 (nếu user mất quyền sau khi ghim → ẩn). Recent/pinned KHÔNG bypass capability.

> Đo được: chọn command A → reload app → mở ⌘K query rỗng → A xuất hiện trong "Gần đây". Ghim B → B lên đầu. Recent ≤5. QA test localStorage persist + dedupe + cap-filter trên recent.

### D7 — SIDEBAR GỌN cho high-rank/admin: default-collapse nhóm ít dùng + Ghim nhóm — THUẦN THỊ GIÁC, KHÔNG ĐỤNG RBAC

**Quyết định (1 dòng):** với persona đa-module (admin/high-rank thấy nhiều `sidebarGroups`), sidebar **mặc định thu gọn (collapse) nhóm ít dùng** + cho **ghim nhóm** lên đầu — **CHỈ thay đổi trạng thái hiển thị/expand**, TUYỆT ĐỐI KHÔNG đổi nhóm/mục nào user **thấy** (đó vẫn do `itemVisible` quyết định — RBAC bất biến):

| Khía cạnh | Chốt |
|---|---|
| Phạm vi | CHỈ trạng thái `expanded/collapsed` của **nhóm** (`ModuleNav.groups`, F14) — KHÔNG ẩn/hiện entry. Entry-visibility = `itemVisible` (F2) GIỮ NGUYÊN. |
| Default-collapse | Nhóm "ít dùng" mặc định collapsed cho persona có **> N nhóm** (N=4, ngưỡng cấu hình). Persona ít nhóm (KTV, vendor) → KHÔNG collapse (vẫn expand hết — không phạt persona gọn). |
| "Ít dùng" xác định sao | Tĩnh: nhóm Governance/Compliance/Admin (vd `qms`, `iam`, `reference`) collapsed mặc định; nhóm vận hành (assets/maintenance/incident) expand. KHÔNG suy ra từ usage-tracking (tránh phức tạp + privacy). |
| Ghim nhóm | User ghim nhóm (📌) → nhóm lên đầu + luôn expanded; persist `localStorage` `ac_sidebar_pinned_groups`. Đối xứng D6 (ghim command). |
| Persist trạng thái | expand/collapse mỗi nhóm persist `localStorage` `ac_sidebar_collapsed_groups` per-user (client-only). Reload giữ trạng thái. |
| Bất biến RBAC | **KHÔNG** gọi/đổi `itemVisible`/`resolveRouteAccess`/capability. Collapse 1 nhóm KHÔNG cấp/thu quyền. Nhóm rỗng-sau-gate (0 entry visible) vẫn KHÔNG render (logic cũ) — collapse chỉ áp nhóm CÓ entry visible. |
| Quan hệ ⌘K | Sidebar gọn + ⌘K **bổ trợ nhau**: sidebar collapse giảm nhiễu thị giác; ⌘K là lối nhảy nhanh tới nhóm đã collapse mà không cần expand tay. |

**Lý do tách RBAC:** acceptance ghi rõ "CHỈ thị giác, KHÔNG đụng RBAC". Lẫn collapse với gate = tái phạm anti-pattern "ẩn entry bằng UI thay vì capability" → drift gate. Collapse chỉ là `v-show`/`expanded` toggle trên nhóm; entry bên trong vẫn được `itemVisible` lọc như cũ.

> Đo được: admin (>4 nhóm) → load sidebar → nhóm Governance/Admin collapsed, vận hành expanded; click expand → hiện đúng entry `itemVisible` cho phép (KHÔNG nhiều/ít hơn). Ghim 1 nhóm → reload → vẫn lên đầu + expanded. KTV (≤4 nhóm) → tất cả expanded. QA test: collapse state KHÔNG đổi `itemVisible` output (số entry visible bất biến trước/sau collapse).

---

## Anti-pattern PHẢI tránh (rút từ memory + lessons-learned)

- ❌ **Nguồn registry thứ 3** (hardcode `commands.ts`) → drift với nav. Derive từ `MODULE_NAV`+route (D1).
- ❌ **`hasAnyRole(ROLES_*)`** gate ⌘K → RBAC dead-gate (LL-FE-12, LL-FE-22 empty-stub silent-deny). Dùng `itemVisible`/`resolveRouteAccess`+capability (D2).
- ❌ **Render command disabled** (lộ tồn tại đích vượt quyền) → anti-leak vỡ. ẨN hoàn toàn (D2).
- ❌ **Tái dùng `BaseModal`** cho ⌘K → thiếu focus-trap/combobox (F6). Component riêng (D5).
- ❌ **`addEventListener('keydown')` tay** → leak listener, không cleanup. `useMagicKeys` (D4).
- ❌ **Thêm Fuse.js / fuzzy lib** → bloat. Tự viết fold+substring+token (D3).
- ❌ **Hardcode nhãn VI trong .vue** → dùng nhãn từ `MODULE_NAV.title`/route `meta.title` (SSoT nav), đồng bộ LL-FE labels rule.
- ❌ **Feed `meta.title` bẩn vào palette** (English 'Status'/jargon 'GMDN'/devOnly route) → anti-leak vỡ trên màn tìm-nhanh. Audit + fix `:95` + loại devOnly TRƯỚC feed (D1-bis, Phụ lục A).
- ❌ **Dùng collapse/ẩn nhóm sidebar để CHẶN QUYỀN** (thay capability) → drift gate, RBAC dead-gate. Collapse CHỈ thị giác; gate = `itemVisible` (D7).

---

## Test-case TDD sẽ viết ở Vòng implement (D-TEST)

| ID | Mức | Khẳng định |
|---|---|---|
| TC-CMDK-01 | unit | `useCommandRegistry()` chứa mọi `NavItem.to` của `MODULE_NAV` + route tĩnh whitelisted; 0 entry hardcode ngoài 2 nguồn (D1). |
| TC-CMDK-02 | unit | thêm 1 `NavItem` vào fixture `MODULE_NAV` → registry +1 command tự động (D1). |
| TC-CMDK-03 | unit | với capability set X → command nav lọc qua `itemVisible`; command route lọc qua `resolveRouteAccess` (D2). |
| TC-CMDK-04 | unit | capability rỗng → chỉ command `cap===undefined` hiện; KHÔNG command gated nào lộ (D2 anti-leak). |
| TC-CMDK-05 | unit | `foldVi('Bảo trì')==='bao tri'`, `foldVi('Thiết bị')==='thiet bi'`, `foldVi('Đo')==='do'` (D3). |
| TC-CMDK-06 | unit | bảng `{query→top result}`: "bao tri"→"Bảo trì*", "thiet bi"→"Thiết bị*", "tao pm"→"Tạo PM*" (≥10 cặp) (D3). |
| TC-CMDK-07 | component | keydown ⌘K/Ctrl+K → `useCommandPalette().open=true`; preventDefault gọi (D4). |
| TC-CMDK-08 | component | nút hint `AppTopBar` có `min-h-[44px]`; click → open=true; badge "⌘K" `hidden sm:inline` (D4). |
| TC-CMDK-09 | a11y | container `role=dialog aria-modal`; input `role=combobox aria-controls/activedescendant`; item `role=option aria-selected` (D5). |
| TC-CMDK-10 | a11y | ArrowDown/Up đổi active (wrap); Enter router.push đích; Escape đóng + return-focus về gốc; Tab không thoát dialog (D5). |
| TC-CMDK-11 | unit | chọn command → `recent[]` unshift, dedupe, ≤5, persist `localStorage`; reload → hiện lại (D6). |
| TC-CMDK-12 | unit | recent/pinned vẫn lọc qua D2 (mất quyền → ẩn khỏi recent) (D6). |
| TC-CMDK-13 | unit | registry LOẠI route `meta.devOnly===true` (F13); nhãn KHÔNG chứa 'GMDN'/'Status'/'Debug' (D1-bis). |
| TC-CMDK-14 | unit | sau fix `:95`, route QRScan title = 'Mở hồ sơ thiết bị' (KHÔNG 'GMDN Status') (D1-bis / Phụ lục A). |
| TC-CMDK-15 | component | admin (>4 nhóm) → nhóm Governance/Admin collapsed mặc định, vận hành expanded; KTV (≤4) → expand hết (D7). |
| TC-CMDK-16 | unit | collapse/expand 1 nhóm KHÔNG đổi số entry `itemVisible` cho phép (RBAC bất biến); ghim nhóm persist `localStorage` + lên đầu (D7). |

---

## Tác động & non-goals

**Đụng (Vòng 2+ implement):** `frontend/src/components/common/CommandPalette.vue` (mới), `composables/useCommandRegistry.ts` (mới), `stores/commandPalette.ts` (mới), `utils/foldVi.ts` + `matchCommand.ts` (mới), sửa `AppLayout.vue` (bind useMagicKeys) + `AppTopBar.vue` (nút hint net-new cạnh Bell, F7), `router/index.ts:95` (fix title GMDN→'Mở hồ sơ thiết bị', D1-bis) + loại `meta.devOnly` khỏi feed, **D7:** sidebar collapse/pin state (`Sidebar.vue`/`AppLayout.vue` + store `sidebar` localStorage — CHỈ expand-state), bồi `06_Frontend_Design.md`. KHÔNG sửa `sidebarNav.ts`/`routeAccess.ts` LOGIC gate (chỉ TÁI DÙNG export — read-only import).

**NON-GOAL (KHÔNG làm ADR này):** KHÔNG đổi `MODULE_NAV` structure; KHÔNG đổi route definitions (ngoài fix title `:95`); KHÔNG đổi predicate gate `itemVisible`/`resolveRouteAccess` (chỉ gọi); KHÔNG dùng collapse-nhóm để chặn quyền (D7 thuần thị giác); KHÔNG action-command BE (chạy lệnh nghiệp vụ qua ⌘K) — chỉ điều hướng (roadmap); KHÔNG thêm fuzzy/command lib ngoài; KHÔNG usage-tracking suy "nhóm ít dùng" (D7 dùng phân loại tĩnh).

---

## Phụ lục A — Audit 130 `meta.title` TRƯỚC khi feed CMDK (acceptance "liệt audit 130 meta.title")

**Phương pháp:** `grep -nP "title:\s*'" router/index.ts` (130 entry, F11) → soi từng nhãn theo luật anti-leak (English status / raw-code / jargon module). Kết quả 2026-06-09:

| Phân loại | Số | Hành động trước feed |
|---|---|---|
| ✅ **Sạch (VI thuần)** | ~119 | Feed nguyên trạng. |
| ✅ **VI + ngoặc đơn domain-anchor** (`(RCA)` ×2, `(CAPA)`, `(ISO 13485)`, `(AVL)`, `(UOM)`, `(NCC)` ×2, `Firmware CR`) | ~9 | Feed nguyên trạng — ngoặc đơn là **anchor có chủ đích**, luôn kèm cụm VI đầy đủ, KHÔNG phải raw-code trần. (`Firmware CR` cân nhắc đổi 'CR'→'yêu cầu thay đổi' — P3, KHÔNG chặn feed.) |
| 🔴 **LEAK user-facing** (sửa TRƯỚC feed) | **1** | `router:95` `'Quét QR — GMDN Status'` → `'Mở hồ sơ thiết bị'`. Bỏ jargon **GMDN** + English **"Status"**. (Trùng STATE.md §FE-P2/P3 — fix 1 lần lan cả breadcrumb + palette.) |
| 🟡 **Dev-only** (loại khỏi feed) | **1** | `router:957` `'Tổng quan Thiết bị (Debug)'` `devOnly:true`+`data.admin` → registry LOẠI route `meta.devOnly` (D1-bis). Không vào palette production. |

**Kết luận feed-safety:** registry CMDK `source:'route'` an toàn feed **sau khi** (a) sửa 1 leak `:95`, (b) loại route `devOnly`. Title còn lại sạch (VI-native). KHÔNG cần i18n-map riêng cho title — chỉ 1 nguồn `meta.title` sau fix. Cross-check: command `source:'nav'` lấy nhãn từ `NavItem.title` của `MODULE_NAV` (đã VI-native, không có entry GMDN/English — ngoài phạm vi audit này).

---

*Gate THIẾT KẾ Vòng 1 — PHÂN TÍCH. KHÔNG đụng code. Thực thi D1–D7 từ Vòng 2 (D1-bis fix title `:95` + loại devOnly là tiền-điều-kiện feed). Mọi spec FE phải cross-link ADR này khi nói về Command Palette / sidebar gọn / điều hướng nhanh.*
