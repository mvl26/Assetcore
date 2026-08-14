# FE Persona Navigation — Core Doc (Single Source of Truth)

| Mục | Giá trị |
|---|---|
| Phạm vi | Cross-cutting FE shell + RBAC (KHÔNG thuộc 1 IMM-XX) |
| Owner | BA + FE Tech Lead |
| Trạng thái | In Progress — Phase 1.4 (tách ranh giới: BE = Role Profile + Role Permission chuẩn Frappe; **persona = FE-only**; xem §7.quinquies — SUPERSEDES ngôn ngữ "persona" của §7.quater ở tầng BE) |
| Cập nhật | 2026-06-01 |
| Tham chiếu | `frontend/src/components/common/AppSidebar.vue`, `AppTopBar.vue`, `api/layout.py::get_user_context`, `services/shared/rbac.py::CAPABILITY_MAP`, `fixtures/role.json`, design tokens `docs/fe/assets/style.css` + `docs/fe/assets/shell.js`, prototype `docs/fe/index.html` |

> Đây là spec mà BE/FE phải code khớp 100% và QA viết test theo. Mọi drift code↔doc = blocking, reconcile doc trước.

---

## 1. Mục tiêu

Chuyển sidebar điều hướng từ **MODULE-scoped** (cũ: `route.meta.moduleId` + trang `/launcher`) sang **PERSONA/ROLE-scoped**:

- Sidebar hiển thị nav theo **persona đang chọn**, không theo route hiện tại.
- Thêm **persona switcher** ở topbar (`AppTopBar.vue`), suy persona từ **RBAC THẬT** (`roles` + `imm_roles` trả bởi `get_user_context`).
- **Production-safe**: persona chỉ **LỌC nav hiển thị**, KHÔNG cấp thêm quyền. Mọi action vẫn gate qua **DocPerm (BE)** + **`useCapabilities` (FE)**.
- **Bỏ hẳn `/launcher`** (route + `LauncherView.vue` + mọi link/redirect): điều hướng chính = sidebar persona-scoped. `/` redirect thẳng về `/dashboard` (persona dashboard). Click logo sidebar → `/dashboard`, KHÔNG còn launcher.
- **Sidebar gọn**: render theo **group** (`MODULE_NAV` items gom theo module/persona), ẩn group rỗng, chỉ hiện item user đủ **capability**. Bỏ nội dung thừa (back-launcher button, empty-launcher CTA).

### 1.1 Nguyên tắc bảo mật (BẮT BUỘC ghi nhớ)

Persona **KHÔNG phải security boundary** — nó là **client preference** để lọc giao diện. Một user cố sửa `localStorage.ac_persona` sang persona không đủ quyền KHÔNG được phép thấy nav đó (vì `derivePersonas` loại bỏ persona không hợp lệ), và kể cả nếu thấy link thì BE DocPerm vẫn chặn mọi thao tác. Đổi persona KHÔNG sinh audit record (không phải hành vi nghiệp vụ).

---

## 2. Tập 8 Persona (chốt theo prototype `docs/fe/index.html`)

Inference roles dưới đây đối chiếu `services/shared/constants.py::Roles` + `fixtures/role.json` (30 role: 4 System + 26 Domain). Tên role là tên thật, không bịa.

| # | code | Label (VI) | Avatar color | Inference roles (có persona nếu user có ≥1) | Sidebar modules hiển thị | rank |
|---|---|---|---|---|---|---|
| 1 | `admin` | Quản trị viên IT | `#0F172A` | `AssetCore Super Admin`, `System Manager`, `Administrator` | TẤT CẢ module + `system` | 100 |
| 2 | `opsmgr` | Trưởng phòng VT-TTBYT | `#0E6FFF` | `Commissioning Manager`, `Needs Manager`, `Procurement Manager`, `Spec Manager` | `master`, `imm01`, `imm02`, `imm03`, `imm04`, `system` (dashboard, approvals) | 70 |
| 3 | `workshop` | Trưởng xưởng kỹ thuật | `#0891B2` | `PM Manager`, `Repair Manager`, `Calibration Manager`, `Corrective Manager` | `imm08`, `imm09`, `imm11`, `imm12`, `master`, `imm15` | 60 |
| 4 | `tech` | Kỹ thuật viên | `#16A34A` | `PM User`, `Repair User`, `Calibration User`, `Corrective User` | `imm08`, `imm09`, `imm11`, `master` (read) | 40 |
| 5 | `clinical` | Trưởng khoa lâm sàng | `#7C3AED` | `Corrective User`, `Corrective Manager` | `imm12`, `master` (read) | 30 |
| 6 | `doc` | Cán bộ hồ sơ | `#475569` | `Document Manager`, `Document User`, `Training Manager` | `imm05`, `imm06`, `master` | 35 |
| 7 | `store` | Thủ kho phụ tùng | `#B45309` | `Inventory Manager`, `Inventory User` | `imm15`, `imm13` | 35 |
| 8 | `qa` | Cán bộ QA / Kiểm toán | `#DC2626` | `Compliance Manager`, `Compliance User`, `AssetCore Auditor` | `imm16`, `system` (audit-trail, dashboard) | 50 |

> `rank` dùng để chọn persona mặc định khi user có nhiều persona, và để fallback (rank cao nhất hợp lệ).

> `Vendor Engineer` KHÔNG có persona UI — giữ cô lập theo hành vi hiện tại (vendor chỉ thấy WO/Asset được phân công, không vào shell persona).

### 2.1 Mapping persona → sidebar (chi tiết)

Sidebar nav được build bằng cách lấy các `moduleId` trong cột "Sidebar modules" của persona, tra `MODULE_NAV` catalog (đã có trong `AppSidebar.vue`), render theo **group** (mỗi module = 1 group với label). Mỗi `NavItem` lọc bằng **capability** (`item.cap` qua `useCapabilities().can(...)`). Vì vậy:

- Một persona có module trong list nhưng user thiếu capability cho 1 item cụ thể → item đó ẩn.
- Group rỗng sau filter (không còn item visible) → **không render** group label (sidebar gọn).
- `master(read)` nghĩa là module `master` xuất hiện nhưng các item cần Manager-capability tự ẩn.

**RBAC filter — chốt anti-leak (BẮT BUỘC):**

- Mỗi `NavItem` khai `cap?: string | string[]` (capability key từ `services/shared/rbac.py::CAPABILITY_MAP`, vd `pm.read`, `inventory.write`, `data.admin`, `audit.read`). Item KHÔNG có `cap` = mở cho mọi user đã xác thực (vd dashboard, QR-scan).
- `itemVisible(item)` = superuser bypass **HOẶC** `cap` rỗng **HOẶC** `useCapabilities().can(item.cap)`.
- **CẤM** dùng `ROLES_*` empty-stub (rỗng) làm bộ lọc — vì `roles.length === 0` khiến item luôn hiện (leak). Lesson LL-FE-12/22: gate FE bằng **capability**, không so role-name.

`moduleId` hợp lệ (khớp `MODULE_NAV`): `master, system, imm01, imm02, imm03, imm04, imm05, imm06, imm08, imm09, imm11, imm12, imm13, imm15, imm16` (+ `imm14` rỗng). Persona dùng đúng các id này.

---

## 3. RBAC Inference Rule

```
derivePersonas(roles: string[], imm_roles: string[]) -> Persona[]
```

- Gộp `allRoles = roles ∪ imm_roles`.
- **Superuser bypass**: nếu `allRoles` chứa bất kỳ `System Manager` / `Administrator` / `AssetCore Super Admin` → trả về **cả 8 persona**.
- Ngược lại: persona khả dụng nếu `allRoles ∩ persona.inferenceRoles ≠ ∅`.
- Kết quả sort theo `rank` giảm dần (persona quyền cao trước).
- Nếu rỗng (user không có role nào khớp) → trả về mảng rỗng; FE hiển thị shell tối thiểu (chỉ `system` dashboard) — KHÔNG crash.

---

## 4. Persistence & Fallback

- Persist persona đang chọn vào `localStorage`, key **`ac_persona`** (khớp prototype `docs/fe/index.html`).
- Khi load: đọc `ac_persona`.
  - Nếu giá trị đó nằm trong `derivePersonas(...)` → dùng.
  - Nếu KHÔNG hợp lệ (user mất quyền / giá trị rác / null) → **fallback persona hợp lệ có `rank` cao nhất**, và ghi đè lại `ac_persona`.
- Nếu `derivePersonas(...)` chỉ có **1 persona** → topbar hiện **label tĩnh** (không dropdown switcher).
- Đổi persona qua switcher → cập nhật state + persist + sidebar re-render ngay (reactive). KHÔNG cần reload trang.

---

## 5. Endpoint Contract

**Phase 1 mặc định: persona inference làm CLIENT-SIDE** từ `roles`/`imm_roles` đã có trong `get_user_context` (xem `api/layout.ts::UserContext`). Production-safe vì persona chỉ lọc nav; mọi action gate ở BE DocPerm.

> KHÔNG bắt buộc endpoint mới ở Phase 1.

Nếu sau này cần server-authoritative (ví dụ persona-based default landing page server-side), contract dự kiến (read-only, chưa implement):

```
GET api/method/assetcore.api.layout.get_personas
  input : none
  output: { personas: [{ code: string, available: boolean }], default: string }
```

---

## 6. UX — Persona Switcher

- **Vị trí**: trong `AppTopBar.vue`, cụm bên phải gần user-menu / locale switcher.
- **Hiển thị**: avatar màu persona + label persona đang chọn.
- **Nhiều persona** → click mở dropdown list các persona đủ quyền (hiện avatar + label); chọn → đổi.
- **1 persona** → label tĩnh, không tương tác dropdown.
- **0 persona** → ẩn switcher (shell tối thiểu).
- Sidebar (`AppSidebar.vue`) đọc persona hiện tại (qua composable dùng chung, ví dụ `usePersona.ts`) để build nav (mục 2.1). Logo/header sidebar hiển thị theo persona thay vì module.
- **`/launcher` bị gỡ bỏ** (route + view + nav). Logo sidebar điều hướng về `/dashboard` (persona dashboard). `/` redirect `/dashboard`.

## 6.1 Style — đồng bộ design tokens `docs/fe`

Sidebar phải bám tokens trong `docs/fe/assets/style.css` (mục `/* Sidebar */`):

| Thuộc tính | Token / giá trị |
|---|---|
| Width | `--sidebar-w: 248px` |
| Nền sidebar | `#13314f` (navy đậm), chữ `#cdd9e8` |
| Header (`side-head`) | nền `--color-navy-header #1F4E79`, chữ `#9fc3e8`, uppercase 12px, letter-spacing .04em, cao 44px |
| Group label (`nav-group-label`) | 10.5px uppercase, letter-spacing .06em, màu `#6f8aa8`, padding `12px 16px 4px` |
| Nav item | padding `10px 16px`, font 14px, màu `#cdd9e8`, gap 12px, icon 20px |
| Nav item hover | nền `rgba(255,255,255,.06)`, chữ `#fff` |
| Nav item active | nền `rgba(14,111,255,.22)`, border-left 3px `--color-primary-500 #0E6FFF`, chữ `#fff`, weight 600 |
| Scrollbar | mảnh, hiện khi hover sidebar |

> Mục tiêu: sidebar khớp prototype, KHÔNG dùng palette tự chế (#0f1623 cũ). Active state = highlight xanh primary + left-border, không phải box-shadow tím.

---

## 7. Acceptance Criteria

1. `constants/personas.ts` định nghĩa đủ 8 persona: `code`, `label`, `color`, `inferenceRoles`, `modules`, `rank`.
2. `derivePersonas(roles, imm_roles)` đúng spec mục 3 (superuser → 8; theo intersection; sort rank).
3. Sidebar render theo persona đang chọn (mục 2.1), theo **group**, KHÔNG theo `route.meta.moduleId`. Module ngoài persona → không hiện. Group rỗng sau filter → không render.
4. Persona switcher: chỉ list persona đủ quyền; chọn → đổi sidebar + persist; 1 persona → label tĩnh.
5. Persona persisted không hợp lệ → fallback rank cao nhất + ghi đè `ac_persona`.
6. Anti-leak: set `ac_persona` = persona không đủ quyền → `derivePersonas` loại bỏ → KHÔNG render nav persona đó; mọi item lọc bằng **capability** (`item.cap` → `useCapabilities`), KHÔNG dùng role empty-stub.
7. Không regression build/test FE; BE không đổi (chỉ verify `get_user_context` trả `roles`+`imm_roles`).
8. `/launcher` bị gỡ: không còn route component `Launcher`, không còn `LauncherView.vue`, không còn nav link/back-button trỏ launcher trong sidebar. Chỉ giữ 1 dòng **back-compat redirect** `/launcher` → `/dashboard` (chống dead bookmark). `/` → `/dashboard`. Router guard không vỡ.
9. Sidebar style khớp tokens §6.1 (navy `#13314f`, width 248px, active `#0E6FFF` left-border).

## 7.bis Phase 1.1 — Sidebar Collapsible Grouping (vòng 2026-06-01)

### Vấn đề
Persona `admin` (Quản trị viên IT) có 15 module + superuser bypass → mọi `NavItem` của mọi module hiện ra. Sidebar dài quá tầm nhìn, phải scroll nhiều, khó định vị chức năng. Phản hồi user: "sidebar đang bị rất là dài… phân chia rõ theo chức năng… tránh nhét quá nhiều".

> Đây là vấn đề **UX/ergonomics**, KHÔNG phải lỗ hổng bảo mật. Gating thật (BE `rbac.require` + route guard capability-based `resolveRouteAccess` + `itemVisible` capability) đã đúng và GIỮ NGUYÊN. Persona switcher CHỈ lọc nav, không cấp quyền (đã đúng — xem §1.1). Vòng này KHÔNG đổi RBAC.

### 7.bis.1 Hành vi
- Mỗi `SidebarGroup` (do `buildSidebarGroups` trả) render thành **section thu gọn được**: header group (label + chevron) bấm để collapse/expand danh sách item.
- **Persist** trạng thái collapse per-group vào `localStorage` key **`ac_sidebar_collapsed_groups`** (mảng `group.title` đang đóng). Khác key `ac_persona` (chọn persona) và state collapse-toàn-sidebar của `useSidebar` (icon-only mode) — 3 state độc lập.
- **Auto-open nhóm active**: group chứa route hiện tại (item có path khớp `activeItemPath`) LUÔN mở, bất kể trạng thái persist — tránh "ẩn mất" chức năng user đang dùng.
- **Mặc định**: nhóm chưa có trong danh sách persist → **mở** (default expanded). Nghĩa là user phải chủ động đóng; sidebar không tự đóng nhóm khi load lần đầu (tránh giấu chức năng bất ngờ).
- **Icon-only mode** (`useSidebar().collapsed === true`, toàn sidebar thu về icon): KHÔNG áp dụng collapsible group — vẫn render flat deduped như hiện tại (header group không có chỗ hiển thị khi sidebar hẹp).
- **Số lượng group ít** (≤2 group, vd persona `qa`/`store`): vẫn render header group + cho collapse, nhưng không bắt buộc — hành vi đồng nhất, không special-case.

### 7.bis.2 Ràng buộc kỹ thuật
- Logic thuần (đọc/ghi persist + quyết định group nào mở) tách thành unit-test được (giống `routeAccess.ts`): hàm `isGroupOpen(group, persistedClosed, activeGroupTitle)` + helpers đọc/ghi localStorage. Component `AppSidebar.vue` chỉ wiring.
- Persist lỗi (private mode/quota) → fallback in-memory, KHÔNG crash (giống `usePersona`/`useSidebar`).
- KHÔNG đổi `MODULE_NAV`, `personas.ts`, `buildSidebarGroups` signature, RBAC, route guard.
- Style: header group dùng token `nav-group-label` hiện có (§6.1) + thêm chevron; giữ navy `#13314f`.

### 7.bis.3 Acceptance (bổ sung)
10. Mỗi group sidebar có header bấm được để collapse/expand; click toggle danh sách item của đúng group đó.
11. Trạng thái đóng/mở persist qua reload (`localStorage.ac_sidebar_collapsed_groups`); giá trị rác/null → mọi group mở (default), không crash.
12. Group chứa route hiện tại tự mở dù persist đánh dấu đóng.
13. Icon-only mode (toàn sidebar collapsed) không render header group / không áp collapsible — flat deduped như cũ.
14. Không regression RBAC: tập item visible mỗi persona KHÔNG đổi so với Phase 1 (collapse chỉ ẩn thị giác, item vẫn thuộc DOM/được phép). Route guard + capability filter giữ nguyên.

### 7.bis.4 Test cases (TDD — bổ sung)
| ID | Mô tả | Kỳ vọng |
|---|---|---|
| T14 | `isGroupOpen(g, [], null)` — chưa persist gì | `true` (default mở) |
| T15 | `isGroupOpen(g, [g.title], null)` — group nằm trong danh sách đóng | `false` |
| T16 | `isGroupOpen(g, [g.title], g.title)` — group bị đóng NHƯNG là active | `true` (active override) |
| T17 | Toggle 1 group → ghi/xóa `g.title` trong `ac_sidebar_collapsed_groups`; reload đọc lại đúng | persist round-trip đúng |
| T18 | localStorage rác (`"{not json"`) → đọc trả `[]` (mọi group mở), không throw | graceful |
| T19 | Superuser persona `admin`: số group render = số module có ≥1 item (không đổi sau Phase 1.1) | RBAC bất biến |

## 7.ter Phase 1.2 — GỠ persona switcher, nav derive trực tiếp từ ROLE THẬT (vòng 2026-06-01)

### Quyết định user (nguyên văn)
> "bỏ hẳn persona switcher đi, cái tôi muốn là khi thiết lập các role khác nhau thì giao diện và quyền của user đó sẽ khác nhau tương ứng chứ persona switcher không cần thiết, có thể tạo thêm các user có các role khác nhau tương ứng để kiểm thử"

### 7.ter.1 Nguyên tắc mới
- **KHÔNG còn "persona đang chọn"** do user tự đổi. Bỏ hẳn: switcher UI (`AppTopBar`), `setPersona`, `canSwitch`, `currentPersona` (selectable), localStorage key `ac_persona`, mọi state cho phép đổi persona.
- Giao diện (sidebar + nav + dashboard) **suy TRỰC TIẾP từ ROLE THẬT** của session (`roles` từ `get_user_context` = `frappe.get_roles()`).
- User có nhiều role → **HỢP NHẤT (union)** chức năng tất cả persona mà role họ mở khoá. KHÔNG dropdown chọn.
- `PERSONAS` mapping (role→modules→label→color→rank) **GIỮ NGUYÊN** làm cấu trúc nội bộ — chỉ bỏ phần CHO PHÉP user đổi. Đây là cách dịch role thật → tập module hiển thị.
- Persona vẫn KHÔNG phải security boundary: gating thật ở BE DocPerm + route-guard capability + `itemVisible`. Vòng này KHÔNG đổi RBAC/route-guard/capability — chỉ đổi cách build NAV (từ "1 persona đang chọn" → "union mọi persona role mở khoá").

### 7.ter.2 Hàm thuần (TDD, thay phần "selected persona")
```
derivePersonas(roles, imm_roles) -> Persona[]            // GIỮ NGUYÊN (union các persona role mở khoá, sort rank desc)
derivePrimaryPersona(personas) -> Persona | null         // MỚI: persona rank cao nhất (header label/color + default dashboard)
buildSidebarGroupsForRoles(personas, can, isSuperuser) -> SidebarGroup[]   // MỚI: union modules MỌI persona, theo thứ tự rank, dedupe path, lọc capability, ẩn group rỗng
```
- `buildSidebarGroupsForRoles`: duyệt persona theo rank desc; với mỗi persona duyệt `persona.modules`; build group qua cùng logic `itemVisible` + dedupe path **toàn cục** (một path chỉ xuất hiện 1 lần dù nhiều persona/module chứa). Group rỗng sau filter → ẩn.
- `usePersona()` composable đổi thành read-only: trả `{ personas, primaryPersona }` (không `setPersona/canSwitch/currentPersona`). Không đọc/ghi `ac_persona`.
- Header sidebar: dùng `primaryPersona.label/color` (nhãn vai trò chính, KHÔNG cho đổi) hoặc 'AssetCore' nếu rỗng.
- DashboardView: render dashboard theo `primaryPersona.code`; fallback `opsmgr` nếu null. (User nhiều role thấy dashboard của vai trò rank cao nhất — nhất quán, không cần chọn.)

### 7.ter.3 Ràng buộc
- Sidebar collapsible grouping (§7.bis) GIỮ NGUYÊN — `buildSidebarGroupsForRoles` trả cùng kiểu `SidebarGroup[]`, các helper `isGroupOpen`/persist không đổi.
- Route guard `resolveRouteAccess`, capability `useCapabilities`, BE `rbac.require` KHÔNG đổi.
- Dọn `ac_persona` cũ trong localStorage nếu còn (không bắt buộc, không gây lỗi nếu để lại — không còn ai đọc).

### 7.ter.4 User test theo role (kiểm thử "mỗi role thấy khác nhau")
- Seed `assetcore/scripts/seed/seed_test_users.py` (idempotent): mỗi role chính 1 user, tên người Việt thật, email hợp lệ, gán đúng role. Bao phủ đủ persona để chứng minh giao diện/quyền khác nhau theo role. Gồm cả IT Admin (superuser) + role nghiệp vụ.

### 7.ter.5 Acceptance (bổ sung)
15. KHÔNG còn persona switcher trong UI (`AppTopBar` không import `usePersona`, không có dropdown/menu persona). Grep `setPersona|canSwitch|personaMenu|ac_persona` trong `src` (trừ test) = rỗng.
16. `derivePrimaryPersona` trả persona rank cao nhất; `[]` → null.
17. `buildSidebarGroupsForRoles`: user nhiều persona → nav là UNION (vd user có cả `PM User` + `Inventory Manager` thấy cả group PM/CM/Calibration LẪN group Kho). Dedupe path toàn cục.
18. Sidebar/nav derive từ `derivePersonas(roles)` (role thật), KHÔNG từ giá trị persisted do user chọn.
19. RBAC bất biến: user role X vào route ngoài quyền (vd `tech` → `/compliance/rules`) vẫn bị guard chặn → `/unauthorized`. Tập item visible KHÔNG đổi so với Phase 1.1 cho user 1-persona.

### 7.ter.6 Test cases (TDD — bổ sung)
| ID | Mô tả | Kỳ vọng |
|---|---|---|
| T20 | `derivePrimaryPersona(derivePersonas(['AssetCore Super Admin'],[]))` | persona `admin` (rank 100) |
| T21 | `derivePrimaryPersona([])` | `null` |
| T22 | `derivePrimaryPersona(derivePersonas(['Inventory User','PM User'],[]))` | rank cao hơn giữa `tech`(40) và `store`(35) → `tech` |
| T23 | `buildSidebarGroupsForRoles` cho user superuser | union mọi module có ≥1 item (= tập admin Phase 1.1) |
| T24 | `buildSidebarGroupsForRoles` cho personas=[tech] với caps tech | = `buildSidebarGroups(tech,...)` (tương thích 1-persona) |
| T25 | `buildSidebarGroupsForRoles` cho personas=[tech, store] caps cả 2 | union: có group PM/CM/Calibration LẪN group Kho; mỗi path 1 lần |
| T26 | Dedupe path qua nhiều persona (vd `/asset-transfers` ở `store` imm15 và imm13) | xuất hiện đúng 1 lần |
| T27 | `buildSidebarGroupsForRoles([], can, false)` | `[]` (không persona → không nav) |

## 7.quater Phase 1.3 — Role Profile (persona) là cơ chế GÁN ROLE chuẩn — BE-FIRST (vòng 2026-06-01)

### Quyết định user (nguyên văn)
> "trong phần bảng điều khiển loại bỏ các phần ghi vd: 'Cán bộ hồ sơ', các phần role theo personal thì bạn tạo Role Profile (persona) sẽ bao gồm các role được chọn sẵn, khi chọn persona thì sẽ tick luôn các role theo thiết lập và không được sửa role khi chọn role theo persona, chỉ có thể sửa nếu là role thủ công. thiết lập cái này phải từ phần BE lõi của app rồi mới phát triển FE theo"

### 7.quater.0 ĐẢO NGƯỢC mô hình (ghi rõ để tránh nhầm với §7.ter)
Mô hình TRƯỚC (patch v3_1/005 + v3_2/001 + `setup_role_profiles.run` + `test_role_profiles.py`): **bỏ hẳn Role Profile**, gán role trực tiếp qua `Has Role`. Vòng này **đảo ngược**: Role Profile (DocType core Frappe) trở lại làm **cơ chế persona chuẩn** để gán bộ role chọn sẵn. Lý do: user muốn "chọn persona → tick sẵn role → khoá không sửa". Đây CHÍNH là ngữ nghĩa native của Frappe `Role Profile`.

> Phân biệt với §7.ter: §7.ter gỡ persona **switcher** ở FE shell (nav derive từ role thật — GIỮ NGUYÊN). §7.quater nói về **cách GÁN role cho user** ở màn quản trị (bảng điều khiển). Hai việc độc lập: sidebar vẫn derive từ role thật của session; còn cách admin set role giờ ưu tiên qua Role Profile.

### 7.quater.1 Ngữ nghĩa Frappe core (đã verify — load-bearing)
`frappe/core/doctype/user/user.py::populate_role_profile_roles` (gọi trong `validate()` mỗi lần save User):
```python
if self.role_profile_name:
    role_profile = frappe.get_doc("Role Profile", self.role_profile_name)
    self.set("roles", [])                                  # CLEAR sạch
    self.append_roles(*[r.role for r in role_profile.roles])  # REPLACE = role của profile
```
Hệ quả (đây là "khoá role" mà user muốn):
- Khi User có `role_profile_name` ≠ rỗng → mọi lần save, roles bị **clear + replace** = đúng bộ role của profile. Sửa thủ công 1 role rồi save → bị ghi đè lại → **role bị KHOÁ bởi profile**.
- Khi `role_profile_name` = None (rỗng) → `populate_role_profile_roles` no-op → roles **sửa thủ công tự do**.
- Frappe chỉ cho **1** `role_profile_name`/user (single Link). Persona đa-role (vd opsmgr 4 role) map vào **1** Role Profile chứa nhiều role — OK. User cần tổ hợp KHÔNG khớp profile nào → để rỗng + gán thủ công.

### 7.quater.2 Ánh xạ 8 persona → 8 Role Profile (BE fixtures — SSOT)
Tên Role Profile = nhãn tiếng Việt thuần (KHÔNG prefix "AssetCore —" / "IMM -" như legacy đã bị xoá; tránh đụng `_LEGACY_PROFILES`). Role thành viên là tên role THẬT trong `fixtures/role.json` / `Roles.ALL`. Mỗi persona thêm role nền `AssetCore System User` (đăng nhập + đọc shared-core).

| Persona code | Role Profile (name = label VI) | Role thành viên (ngoài `AssetCore System User`) |
|---|---|---|
| `admin` | Quản trị viên IT | `AssetCore Super Admin` |
| `opsmgr` | Trưởng phòng VT-TTBYT | `Commissioning Manager`, `Needs Manager`, `Procurement Manager`, `Spec Manager` |
| `workshop` | Trưởng xưởng kỹ thuật | `PM Manager`, `Repair Manager`, `Calibration Manager`, `Corrective Manager` |
| `tech` | Kỹ thuật viên | `PM User`, `Repair User`, `Calibration User`, `Corrective User` |
| `qa` | Cán bộ QA / Kiểm toán | `Compliance Manager`, `Compliance User`, `AssetCore Auditor` |
| `doc` | Cán bộ hồ sơ | `Document Manager`, `Document User`, `Training Manager` |
| `store` | Thủ kho phụ tùng | `Inventory Manager`, `Inventory User` |
| `clinical` | Trưởng khoa lâm sàng | `Corrective Manager`, `Corrective User` |

> Bộ role mỗi profile = đúng `inferenceRoles` của persona tương ứng ở §2 (trừ role Frappe-native `System Manager`/`Administrator` của `admin` — KHÔNG đưa vào profile vì chúng do Frappe core sở hữu; profile `admin` chỉ chứa `AssetCore Super Admin`). Nhờ vậy gán profile → user mở khoá đúng persona ở sidebar (derive từ role thật — §7.ter nhất quán).

### 7.quater.3 BE — thiết lập (BE-FIRST, bắt buộc làm trước FE)
1. **Catalog SSOT** (`assetcore/setup/role_profiles.py` hoặc constants): dict 8 profile → roles, sinh từ `PERSONAS`/`Roles` để KHÔNG drift. Hàm `seed_assetcore_role_profiles()` idempotent: tạo/cập nhật 8 Role Profile + child `Has Role` đúng bộ role; xoá role thừa nếu profile đã tồn tại.
2. **Bỏ cleanup phá Role Profile**: `setup_role_profiles.run` KHÔNG được xoá 8 profile mới. Giữ dọn legacy (`IMM - *`, `AssetCore — *`) nhưng 8 profile mới dùng tên VI thuần nên không trùng danh sách legacy → an toàn. Hook after_migrate gọi `seed_assetcore_role_profiles()` (thay vì chỉ cleanup).
3. **Fixtures**: thêm `{"dt": "Role Profile", "filters": [["name","in", [...8 tên...]]]}` + child rows vào `hooks.py::fixtures` để `bench migrate` áp được trên site mới (export `role_profile.json`). Đảm bảo idempotent.
4. **API** (`api/user.py`): `list_role_profiles` đổi filter từ `role_profile like 'AssetCore —%'` → 8 tên VI mới (hoặc whitelist theo catalog). `assign_role_profile` GIỮ (đã đúng: set `role_profile_name` → core sync). Bổ sung: khi user CÓ `role_profile_name`, `update_user_roles`/`set_user_roles`/`update_user_info(imm_roles)` phải **từ chối** sửa role thủ công (trả lỗi rõ "role đang khoá bởi Role Profile, bỏ profile trước") — vì core sẽ ghi đè, tránh user tưởng sửa được.
5. **Seed test users** (`scripts/seed_test_users.py`): 8 user persona gán qua `role_profile_name` (thay `add_roles` thủ công) → chứng minh khoá role. User multi-role (tech+store) GIỮ gán thủ công (`role_profile_name=None`) → chứng minh nhánh sửa tự do. Idempotent, fail-fast nếu profile chưa migrate.

### 7.quater.4 FE — phát triển SAU khi BE chốt
- **Bảng điều khiển / màn quản lý user**: bỏ các nhãn persona rời rạc kiểu "Cán bộ hồ sơ" hiển thị như badge tách rời role. Persona giờ = Role Profile (chọn ở dropdown `UserProfileFormView`), KHÔNG còn nhãn lẻ.
- **Khoá role khi có Role Profile**: nếu `detail.role_profile_name` ≠ rỗng → block "Phân quyền (chi tiết)" hiển thị **read-only** (checkbox disabled + ghi chú "Role do persona '<label>' quản lý — bỏ persona để sửa thủ công"). Bỏ profile (chọn "— Không áp dụng persona —" + Áp dụng) → block role mở lại cho sửa.
- `list_role_profiles` trả 8 profile mới; dropdown hiển thị label VI.

### 7.quater.5 Acceptance (bổ sung)
20. `bench migrate` trên site sạch tạo đúng 8 Role Profile (tên VI), mỗi profile chứa đúng bộ role §7.quater.2 (+ `AssetCore System User`). Idempotent: chạy lại không nhân đôi/đổi role.
21. Gán `assign_role_profile(user, "Kỹ thuật viên")` → `user.roles` = đúng bộ tech (clear+replace). Đổi sang "Thủ kho phụ tùng" → roles đổi theo profile mới. Bỏ profile (rỗng) → roles GIỮ nguyên bộ cuối + cho sửa thủ công.
22. Khi user có `role_profile_name`: gọi `update_user_roles`/`set_user_roles` để đổi role thủ công → **bị từ chối** (lỗi rõ) HOẶC bị core ghi đè về bộ profile (test khẳng định roles cuối = bộ profile). Khi `role_profile_name=None`: sửa thủ công thành công.
23. `seed_test_users` gán 8 user persona qua `role_profile_name`; verify mỗi user có đúng bộ role của profile. User multi-role không có profile, giữ 2 role thủ công.
24. FE: user có Role Profile → block role read-only (checkbox disabled); user không profile → block role sửa được. Bảng điều khiển không còn badge persona rời rạc "Cán bộ hồ sơ".

### 7.quater.6 Test cases (TDD — bổ sung, BE Python + FE)
| ID | Lớp | Mô tả | Kỳ vọng |
|---|---|---|---|
| TRP1 | BE | `seed_assetcore_role_profiles()` rồi đếm | 8 Role Profile tồn tại, tên VI đúng §7.quater.2 |
| TRP2 | BE | Profile "Kỹ thuật viên".roles | = {PM/Repair/Calibration/Corrective User} ∪ {AssetCore System User} |
| TRP3 | BE | chạy seed 2 lần | idempotent — vẫn 8 profile, không nhân đôi Has Role |
| TRP4 | BE | `assign_role_profile(u, "Thủ kho phụ tùng")` | u.roles = {Inventory Manager, Inventory User, AssetCore System User} |
| TRP5 | BE | đổi profile u từ tech→store | roles clear bộ tech, set bộ store (không còn PM User) |
| TRP6 | BE | u có profile → `set_user_roles(u, [thêm Compliance Manager])` | từ chối (lỗi) HOẶC sau save roles vẫn = bộ profile (core ghi đè) |
| TRP7 | BE | bỏ profile (`assign_role_profile(u,"")`) rồi `set_user_roles` | sửa thủ công thành công, roles = bộ mới |
| TRP8 | BE | `seed_test_users` | 8 user persona có role_profile_name set; user multi-role role_profile_name=None |
| TRP9 | FE | UserProfileFormView khi role_profile_name set | checkbox role disabled + ghi chú khoá |
| TRP10 | FE | sau khi bỏ profile | checkbox role enabled, sửa được |

## 7.quinquies Phase 1.4 — Tách ranh giới: BE = Role Profile + Role Permission (Frappe-standard); persona = FE-only (vòng 2026-06-01)

### Quyết định user (nguyên văn)
> "tôi nghĩ phần role theo persona nên làm chỉ trên FE thôi, dưới BE quản lý theo role profile và role permission, trên FE sẽ cho theo persona và thủ công thì hợp lý hơn"

### 7.quinquies.0 Bối cảnh — vì sao đảo lại §7.quater
§7.quater (Phase 1.3) đẩy khái niệm **persona** xuống BE: `role_profile_catalog.py` map `persona_code → (Role Profile, roles)`, docstring/biến/thông báo BE dùng từ "persona", `list_role_profiles` doc-comment gọi "8 persona Role Profile", `_profile_lock_error` báo lỗi theo "persona". User phản hồi: BE KHÔNG nên biết "persona" — đó là khái niệm trình bày của FE. BE chỉ quản lý bằng **2 cơ chế chuẩn Frappe**: **Role Profile** (DocType core, gom bộ role chọn sẵn) + **Role Permission** (Has Role / DocPerm). "Persona" → chuyển trọn lên FE.

> Phân biệt với các Phase trước: §7.ter gỡ persona **switcher** (nav derive từ role thật — GIỮ). §7.quater đưa Role Profile làm cơ chế gán role + khoá role (GIỮ cơ chế, vì đó là native Frappe). §7.quinquies chỉ **đổi NGÔN NGỮ/RANH GIỚI**: gỡ chữ "persona" khỏi BE, dời mapping persona↔Role Profile lên FE. KHÔNG đổi RBAC/capability/route-guard, KHÔNG đổi hành vi khoá role.

### 7.quinquies.1 Nguyên tắc ranh giới (chốt)
- **BE biết**: `Role` (Has Role), `Role Profile` (DocType core gom role), `DocPerm` (Role Permission). BE KHÔNG biết "persona", KHÔNG ánh xạ persona, KHÔNG suy persona.
- **FE biết**: `persona` (nhãn/nhóm/màu/nav/rank) + **mapping persona → Role Profile name** (FE constants). FE chịu trách nhiệm dịch "user chọn persona X" → "áp Role Profile Y" rồi gọi API thuần `assign_role_profile(user, Y)`.
- **Khoá role theo Role Profile = GIỮ** (ngữ nghĩa Frappe core `populate_role_profile_roles`, §7.quater.1). Lý do giữ: user nói "BE quản lý theo role profile + role permission" → lock theo `role_profile_name` là cơ chế Frappe hợp lệ, không phải "persona logic". Chỉ **viết lại thông báo** từ ngôn ngữ "persona" sang "Role Profile".

> **Giả định BA đã chọn (ghi rõ để tránh hiểu nhầm — câu user có thể đọc >1 cách):** "role theo persona làm trên FE" KHÔNG có nghĩa bỏ Role Profile ở BE. Role Profile vẫn là cơ chế BE-managed hợp lệ (user nói rõ "dưới BE quản lý theo role profile"). FE "theo persona" = FE map persona→Role Profile rồi áp qua Role Profile. Cơ chế lock-by-role-profile GIỮ. Nếu user muốn bỏ luôn lock → cần xác nhận lại (mặc định: GIỮ).

### 7.quinquies.2 Bảng "BE trước → BE sau"
| Hạng mục BE | TRƯỚC (§7.quater) | SAU (§7.quinquies) | Phân loại |
|---|---|---|---|
| `setup/role_profile_catalog.py` | dict `PERSONA_ROLE_PROFILES[persona_code] = (profile, roles)`; docstring "persona"; hàm `roles_for_profile(persona_code)`, `profile_name_to_roles()` | đổi thành catalog Role Profile **thuần**: `ROLE_PROFILE_CATALOG[profile_name] = [roles]` (key = tên profile, KHÔNG persona_code). Docstring nói "Role Profile", bỏ "persona". `PROFILE_NAMES`, `profile_name_to_roles()` GIỮ (đã là profile-centric) | REFACTOR (gỡ persona-as-key) |
| `setup/setup_role_profiles.py` | seed theo `profile_name_to_roles()`, docstring "persona Role Profile" | GIỮ logic; docstring đổi "8 Role Profile" (bỏ "persona") | GIỮ (chỉ wording) |
| `api/user.py::list_role_profiles` | doc-comment "8 persona Role Profile" | doc-comment "8 Role Profile (catalog)"; bỏ "persona" | GIỮ wrapper (chỉ wording) |
| `api/user.py::assign_role_profile` | wrapper set `role_profile_name` (đã thuần Frappe) | GIỮ NGUYÊN logic | GIỮ (Frappe-standard) |
| `api/user.py::_profile_lock_error` | thông báo: "Role đang quản lý bởi persona '<profile>'. Bỏ persona..." | thông báo: "Role đang quản lý bởi Role Profile '<profile>'. Bỏ Role Profile để sửa role thủ công." | REFACTOR (wording) |
| `api/user.py::set_user_roles/update_user_roles/update_user_info` | gọi `_profile_lock_error` (đúng) | GIỮ NGUYÊN | GIỮ (Frappe-standard) |
| `hooks.py` fixtures `Role Profile` | comment "8 persona Role Profile" | GIỮ fixture; comment bỏ "persona" | GIỮ (Frappe data) |
| Role Permission / DocPerm / `rbac.py` / route guard | — | KHÔNG đổi | GIỮ |

> Kết luận: BE KHÔNG mất tính năng nào — chỉ **gỡ ngôn ngữ persona** + đổi key catalog từ `persona_code` sang `profile_name`. Mọi cơ chế (Role Profile seed/fixtures/assign/lock, RBAC, capability) GIỮ y nguyên hành vi.

### 7.quinquies.3 Persona mapping — giờ ở FE (SSOT = `frontend/src/constants/personas.ts`)
FE giữ mảng `PERSONAS` (đã có: code/label/color/inferenceRoles/modules/rank). Bổ sung **1 trường mapping persona → Role Profile name** để FE biết áp profile nào khi admin "gán theo persona":

```
Persona.roleProfile?: string   // tên Role Profile (Frappe) tương ứng persona này
```

Bảng mapping (FE constants — phải khớp tên profile BE seed; tên profile là dữ liệu Frappe, KHÔNG phải "persona" ở BE):

| persona code (FE) | Persona.label (FE) | Persona.roleProfile (FE → BE Role Profile name) |
|---|---|---|
| `admin` | Quản trị viên IT | `Quản trị viên IT` |
| `opsmgr` | Trưởng phòng VT-TTBYT | `Trưởng phòng VT-TTBYT` |
| `workshop` | Trưởng xưởng kỹ thuật | `Trưởng xưởng kỹ thuật` |
| `tech` | Kỹ thuật viên | `Kỹ thuật viên` |
| `qa` | Cán bộ QA / Kiểm toán | `Cán bộ QA / Kiểm toán` |
| `doc` | Cán bộ hồ sơ | `Cán bộ hồ sơ` |
| `store` | Thủ kho phụ tùng | `Thủ kho phụ tùng` |
| `clinical` | Trưởng khoa lâm sàng | `Trưởng khoa lâm sàng` |

> Mapping sống ở FE constants → nếu BE đổi tên profile, chỉ cần sửa FE mapping; BE KHÔNG trả "persona". `list_role_profiles` trả `{name, label, roles}` (thuần Role Profile) — FE đối chiếu `roleProfile === profile.name` để gắn nhãn persona nếu muốn.

### 7.quinquies.4 FE — màn quản lý user (gán theo persona HOẶC thủ công)
- **Gán theo persona**: dropdown persona (FE) → chọn → FE map sang `Persona.roleProfile` → gọi `assign_role_profile(user, roleProfile)`. Role tự tick + **khoá** (BE lock-by-role-profile). UI nhãn "persona", nhưng API chỉ thấy Role Profile name.
- **Gán thủ công**: bỏ Role Profile (`assign_role_profile(user, "")`) → block role mở cho sửa → `set_user_roles`/`update_user_roles`.
- Thông báo khoá hiển thị ở FE có thể dùng từ "persona" (nhãn FE) hoặc tên Role Profile — tuỳ FE. BE chỉ trả thông báo theo "Role Profile".
- Nav/sidebar tiếp tục derive từ **role thật** session (§7.ter — KHÔNG đổi).

> Dropdown hiện tại của `UserProfileFormView` đang list Role Profile theo `list_role_profiles` (label = profile name). Phase 1.4 cho phép FE **gắn nhãn persona** lên option (đối chiếu `roleProfile` trong `PERSONAS`) — optional, không phá hành vi.

### 7.quinquies.5 Acceptance (bổ sung)
25. BE KHÔNG còn chuỗi "persona" trong code path role/profile: `grep -ri "persona" assetcore/setup/role_profile_catalog.py assetcore/setup/setup_role_profiles.py assetcore/api/user.py` = rỗng (trừ tham chiếu docs trong comment dẫn link Core Doc, nếu có thì viết "FE persona" rõ là khái niệm FE).
26. `role_profile_catalog.py` key catalog = **tên Role Profile** (không phải `persona_code`). `profile_name_to_roles()` vẫn trả `{profile_name: [roles]}` đúng §7.quater.2. Seed/fixtures/assign hành vi KHÔNG đổi (TRP1–TRP8 vẫn xanh).
27. `_profile_lock_error` báo theo "Role Profile" (không "persona"). Lock hành vi giữ: user có `role_profile_name` → `set_user_roles`/`update_user_roles`/`update_user_info(imm_roles)` bị từ chối.
28. FE `personas.ts` có trường `roleProfile` cho cả 8 persona, khớp tên BE seed. FE map persona→roleProfile khi gán; gọi `assign_role_profile(user, roleProfile)`.
29. RBAC/capability/route-guard bất biến (mọi test §7.ter/§7.bis/§9 + BE rbac/test_rbac.py xanh). Không regression build/typecheck FE.

### 7.quinquies.6 Test cases (TDD — bổ sung)
| ID | Lớp | Mô tả | Kỳ vọng |
|---|---|---|---|
| TRP11 | BE | `from assetcore.setup.role_profile_catalog import ROLE_PROFILE_CATALOG` — key | = 8 tên Role Profile VI (§7.quater.2), KHÔNG có `persona_code` |
| TRP12 | BE | `profile_name_to_roles()["Kỹ thuật viên"]` | = {PM/Repair/Calibration/Corrective User, AssetCore System User} (bất biến vs TRP2) |
| TRP13 | BE | grep "persona" trong 3 file BE role-path | rỗng (hoặc chỉ link Core Doc ghi rõ "FE persona") |
| TRP14 | BE | `_profile_lock_error` message | chứa "Role Profile", KHÔNG chứa "persona" |
| TRP15 | FE | `PERSONAS` mọi entry có `roleProfile` non-empty, unique, khớp catalog BE | pass |
| TRP16 | FE | helper `roleProfileForPersona(code)` | trả đúng tên profile; code lạ → null |

## 7.sexies Phase 1.6 — Gỡ NHÃN persona khỏi chrome + bịt lỗ leo quyền role (vòng 2026-06-01)

### Quyết định user (nguyên văn)
> "trên phần góc trái tôi vẫn thấy ghi 'cán bộ hồ sơ', các cái này ko cần ghi chỉ cần quản lý trong role thôi, ngoài ra kiểm tra lại logic và setup role của hệ thống 1 lượt xem có lỗi gì để sửa lại luôn"

### 7.sexies.1 Phần 1 — Gỡ nhãn persona ở header sidebar (góc trái)
- **Vấn đề**: `AppSidebar.vue` header (góc trái trên cùng) render `personaTitle = primaryPersona.label` → hiển thị nhãn persona kiểu "Cán bộ hồ sơ". User KHÔNG muốn nhãn persona ở chrome — chỉ quản trị bằng ROLE.
- **Quyết định**: header sidebar KHÔNG còn hiển thị nhãn persona. Thay bằng **brand tĩnh "AssetCore"** (logo + dòng "Bảng điều khiển"). `primaryPersona` GIỮ để (a) chọn màu logo (cosmetic, không phải nhãn chữ) và (b) DashboardView route dashboard mặc định — nhưng KHÔNG render label persona dưới dạng text.
  - Cụ thể: `personaTitle` đổi từ `primaryPersona.label ?? 'AssetCore'` → **hằng `'AssetCore'`** (không suy từ persona). `personaColor` GIỮ (chỉ tô màu logo-badge, không lộ nhãn).
  - Nhánh suy dashboard mặc định (`DashboardView` dùng `primaryPersona.code`) GIỮ NGUYÊN — đó là logic route, không phải nhãn hiển thị.
- **Phạm vi gỡ nhãn = chrome dùng chung** (sidebar header). Các nơi KHÁC:
  - `AppTopBar.vue`: bên trái chỉ `pageTitle` (tên trang, không persona) — KHÔNG đổi. Bên phải hiển thị tên/email/department + badge `imm_roles` (ROLE THẬT, không persona) — GIỮ (đó là role thật, đúng ý "quản lý trong role").
  - **Màn quản trị user** (`UserProfileFormView`): badge thể hiện Role Profile mà user đang theo = **context quản trị hợp lệ** (admin cần biết user gán profile nào). GIỮ — nhưng đây là nhãn **Role Profile** (Frappe), không phải "persona nav". Không thuộc chrome chung. (Giả định BA: user nói "góc trái" = chrome sidebar; admin user-mgmt giữ để admin vẫn quản trị được. Nếu user muốn gỡ luôn ở đây → xác nhận vòng sau.)
- **Không phá**: nav/sidebar vẫn derive từ role thật (`buildSidebarGroupsForRoles`), dashboard vẫn route đúng theo `primaryPersona.code`. Chỉ gỡ phần TEXT nhãn persona ở header.

### 7.sexies.2 Phần 2 — Bịt lỗ LEO QUYỀN ở endpoint sửa role/profile (P1 security)
Audit phát hiện 2 endpoint cho phép user **tự nâng quyền chính mình** (self-edit bypass admin gate):

| # | Endpoint | Lỗ hổng | Mức |
|---|---|---|---|
| SEC-RBAC-1 | `api/user.py::update_user_roles` | `target = data.user or actor`; khi `target == actor` thì **bỏ qua** `_assert_admin()` → user POST `user=<self>, roles=["AssetCore Super Admin"]` tự thành Super Admin. `_save_user` set `ignore_permissions=True` nên DocPerm không chặn. | **P1** |
| SEC-RBAC-2 | `api/user.py::assign_role_profile` | `if session.user != user and not can(data.admin)` → cho phép **self** đổi Role Profile. User tự `assign_role_profile(self, "Quản trị viên IT")` → core clear+replace roles = bộ profile → có `AssetCore Super Admin`. | **P1** |

**Nguyên tắc chốt (Core Doc)**: đổi role / Role Profile của BẤT KỲ user nào (kể cả chính mình) là **hành vi cấp quyền** → BẮT BUỘC capability `data.admin`. KHÁC với `change_my_password` (self-service hợp lệ, không cấp quyền). Self-edit role KHÔNG phải self-service.

**Fix**:
- `update_user_roles`: bỏ nhánh "self miễn admin". LUÔN gọi `_assert_admin()` (Guest → 401; non-admin → 403). Giữ phần còn lại (lock-by-role-profile, sync, save).
- `assign_role_profile`: bỏ điều kiện `session.user != user` — LUÔN yêu cầu `data.admin` (Guest → 401; non-admin → 403).

> Lưu ý: đây KHÔNG phải "sửa triệu chứng" — root cause là thiết kế gate sai (coi self-edit role như self-service). Sửa tại gate là đúng gốc.

### 7.sexies.3 Trạng thái audit các nguồn khác (KHÔNG đổi — đã đúng, tránh false-positive)
- `services/shared/rbac.py::CAPABILITY_MAP`: capability resolve 100% qua `frappe.has_permission(dt, ptype)` (DocPerm thật) — KHÔNG hardcode grant. Nghi vấn "pm.read/inventory.read cấp rộng" ở memory là về DocPerm trong `role.json`, KHÔNG phải bug rbac.py. rbac.py SẠCH — KHÔNG đổi.
- 3 nguồn `ROLE_PROFILE_CATALOG` (BE) ⟷ `personas.ts.roleProfile` (FE) ⟷ catalog 8 profile: **nhất quán** (8↔8, không drift). `role_profile.json` fixture đồng bộ catalog. KHÔNG đổi.
- `seed_test_users.py`: 8 user qua Role Profile + 1 multi-role thủ công, idempotent, fail-fast. KHÔNG đổi.
- `set_user_roles`, `update_user_info`, `create_system_user`, `reset_user_password`, `list_assignable_roles`: đã gate `data.admin` đúng. KHÔNG đổi.

### 7.sexies.4 Acceptance (bổ sung)
30. Header sidebar (`AppSidebar.vue`) KHÔNG hiển thị nhãn persona text. Hiển thị brand "AssetCore" + "Bảng điều khiển". Grep `personaTitle`/`primaryPersona.label` không còn render ra text persona ở header. `primaryPersona` chỉ dùng cho màu logo + route dashboard.
31. Nav/sidebar groups vẫn derive từ role thật (không regression §7.ter). Dashboard mặc định vẫn route theo `primaryPersona.code`.
32. `update_user_roles`: user thường (non-admin) POST với `user=<chính mình>` + role bất kỳ → **403** (bị từ chối), roles KHÔNG đổi. Admin gọi vẫn thành công.
33. `assign_role_profile`: user thường POST `user=<chính mình>` + profile bất kỳ → **403**. Admin gọi vẫn thành công. Guest → 401.
34. RBAC/capability/route-guard/DocPerm/rbac.py/catalog/fixtures BẤT BIẾN (mọi test §7.* + test_rbac.py + test_role_profiles.py xanh). Không regression FE build/typecheck.

### 7.sexies.5 Test cases (TDD — bổ sung)
| ID | Lớp | Mô tả | Kỳ vọng |
|---|---|---|---|
| SEC-RBAC-1 | BE | non-admin gọi `update_user_roles(user=self, roles=[Super Admin])` | trả `_err` 403; user.roles KHÔNG có Super Admin |
| SEC-RBAC-2 | BE | non-admin gọi `assign_role_profile(user=self, "Quản trị viên IT")` | trả `_err` 403; role_profile_name KHÔNG đổi |
| SEC-RBAC-3 | BE | admin gọi `update_user_roles(user=other, roles=[PM User])` | thành công (regression guard) |
| SEC-RBAC-4 | BE | admin gọi `assign_role_profile(user=other, "Kỹ thuật viên")` | thành công (regression guard) |
| SEC-RBAC-5 | BE | Guest gọi `update_user_roles` / `assign_role_profile` | 401 |
| UI-SIDEBAR-1 | FE | `AppSidebar` header text | = "AssetCore" (không chứa label persona như "Cán bộ hồ sơ") |

## 7.septies Phase 1.7 — Route cap-gate khớp sidebar + bịt over-grant Depreciation (vòng 2026-06-01)

### Quyết định user (nguyên văn)
> "nếu role không có quyền thì ẩn phần đó đi, vd: trang supplier 'Bạn không có quyền thực hiện hành động này.' với quyền nhà cung cấp."
> "rà soát lại các role cho phần /depreciation, phần khấu hao này sao các role của document và training mà cũng nhìn thấy? vd user Email: sohaidiuuu@gmail.com"

### 7.septies.1 Nguyên tắc — thiếu quyền = ẨN nav + CHẶN route (redirect), không render trang "không có quyền"
Thiếu quyền phải xử ở **2 lớp luồng chính**:
1. **Nav**: `itemVisible` ẩn mục khỏi sidebar (đã đúng — `cap` per item).
2. **Route**: `resolveRouteAccess` chặn SỚM trước khi render component → `next({name:'Unauthorized'})` (redirect). KHÔNG để component render trang rỗng kèm câu "Bạn không có quyền thực hiện hành động này." như luồng chính. Guard "không có quyền" trong component CHỈ là defense-in-depth.

> **BẮT BUỘC đồng pha**: cap mà SIDEBAR dùng để ẩn 1 path PHẢI = cap mà ROUTE dùng để chặn path đó. Lệch (sidebar ẩn nhưng route mở) = leak gõ-URL-thẳng.

### 7.septies.2 VĐ1 — Route master-group thiếu `requiredCapabilities` (leak gõ URL)
**Root cause**: route master-group KHÔNG khai `requiredCapabilities`; `tagWorkspace` gán `meta.moduleId='master'`; `moduleIdToCap('master')` trả `null` (master/system không có domain cap) → `resolveRouteAccess` rơi xuống nhánh 5 (default `allow`). Trong khi sidebar gate `data.read`. ⇒ non-data user gõ `/suppliers` thẳng vẫn vào (thấy list rỗng + message). `/suppliers` chỉ là một; quét toàn bộ.

**Route ↔ sidebar cap matrix (master/system list routes — phải khớp)**:

| Route (list) | Sidebar `cap` (sidebarNav.ts) | Route meta TRƯỚC | Quyết định: route meta SAU |
|---|---|---|---|
| `/suppliers` | `data.read` | (none → allow) | `requiredCapabilities:['data.read']` |
| `/device-models` | `data.read` | (none → allow) | `requiredCapabilities:['data.read']` |
| `/service-contracts` | `data.read` | (none → allow) | `requiredCapabilities:['data.read']` |
| `/assets` | (none, mở) | (none) | GIỮ mở (list thiết bị mở cho mọi user xác thực — chủ đích) |
| `/qr-scan` | (none, mở) | (none) | GIỮ mở (QR scan tiện ích chung) |
| `/asset-transfers` | (none, mở) | (none) | GIỮ mở (điều chuyển — store/workshop dùng; không siết vòng này) |
| `/depreciation` | `data.read` → **đổi** (xem 7.septies.3) | (none) | `requiredCapabilities:` = OR-gate finance (7.septies.3) |
| `/purchases` | `procurement.read` (group imm03) | (none) | `requiredCapabilities:['procurement.read']` |
| `/documents/requests` | `doc.approve` | (none) | `requiredCapabilities:['doc.approve']` |

> Ghi chú anti-FP: chỉ siết route mà SIDEBAR đã gate bằng cap. Item sidebar KHÔNG có `cap` (assets/qr-scan/asset-transfers/dashboard/approvals) = chủ đích mở → route GIỮ mở (không tự bịa siết, tránh chặn nhầm). `/documents/requests` sidebar gate `doc.approve` nhưng route đang mở → siết về `doc.approve`.

### 7.septies.3 VĐ2 — Depreciation lộ cho doc/training (over-grant)
**Root cause (verify thật trên site `miyano`)**:
- `sohaidiuuu@gmail.com` roles = `[AssetCore System User, Training Manager, Document Manager, Document User, Training User]` (persona `doc`).
- Sidebar item "Khấu hao tài sản" (`/depreciation`) trong group `master`, gate `cap:'data.read'`.
- `data.read` = `has_permission('IMM Device Model','read')`. **`AssetCore System User` CÓ read `IMM Device Model`** ⇒ `data.read=True` cho **mọi** user AssetCore (kể cả doc/training). ⇒ mục khấu hao lộ.
- Persona `doc.modules` chứa `master` ⇒ group master hiện cho doc; item depreciation không bị cap chặn (vì data.read mở) ⇒ thấy.

**Capability matrix per persona (verify DocPerm thật)** — `True` = có cap:

| cap | admin | opsmgr | workshop | tech | doc | store | qa | clinical |
|---|---|---|---|---|---|---|---|---|
| data.read | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| data.write/admin | ✔ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| needs/spec/procurement/commissioning.read | ✔ | ✔ | ✗ | ✗ | ✗ | ✗ | ✔ | ✗ |
| pm/repair/calibration.read | ✔ | ✗ | ✔ | ✔ | ✗ | ✗ | ✔ | ✗ |

→ `data.read` KHÔNG phân biệt được persona (mọi user True). Không tồn tại 1 cap đơn phân tách sạch {admin,opsmgr,workshop,tech} khỏi {doc,store,clinical}. Lưu ý **qa = AssetCore Auditor đọc MỌI DocType** nên True ở mọi cap.

**Quyết định (Core Doc)**:
- Depreciation (Asset Finance Hub) thuộc **chủ sở hữu tài sản/tài chính**: `admin, opsmgr, workshop, tech`. KHÔNG thuộc `doc, store, clinical`.
- Gate depreciation (nav item + route) bằng **OR-cap finance** =
  `['data.write','needs.read','procurement.read','pm.read','calibration.read']`.
  - admin: SU bypass (route) / superuser (nav) → thấy. ✔
  - opsmgr: `needs.read`/`procurement.read` → thấy. ✔
  - workshop/tech: `pm.read`/`calibration.read` → thấy. ✔
  - doc: không có cap nào trong OR → **ẩn + chặn**. ✔ (fix chính cho sohaidiuuu)
  - store: chỉ `inventory.read` (không trong OR) → ẩn + chặn. ✔
  - clinical: chỉ `corrective.read` (không trong OR) → ẩn + chặn. ✔
  - **qa (Auditor)**: đọc mọi DocType ⇒ match OR ⇒ vẫn thấy. **Chấp nhận có chủ đích**: Auditor có quyền đọc thật toàn hệ (§1.1 — capability = quyền đọc thật; loại Auditor khỏi 1 read-surface là cosmetic, không phải ranh giới bảo mật). KHÔNG bịa loại trừ giả.
- **DocPerm BE**: KHÔNG đổi. `AC Asset Depreciation Schedule` để các `*User` read (cần cho enrich/hiển thị tên/asset — như vòng DEFER trước). Việc lộ là do **NAV/route gate sai (data.read)**, KHÔNG phải do DocPerm. Sửa ở FE gate (nav+route) là đúng gốc; không cần tạo cap `finance.read` mới (tránh fixture churn + grant lệch).

### 7.septies.4 Acceptance (bổ sung)
35. Non-data user (chỉ `AssetCore System User`, không `Data User`/Manager) gõ `/suppliers`, `/device-models`, `/service-contracts` → guard redirect `Unauthorized` (KHÔNG render list rỗng + message). Data user vào bình thường.
36. `/depreciation`: persona `doc` (vd `sohaidiuuu@gmail.com`, `buithihonganh@assetcore.test`), `store`, `clinical` → KHÔNG thấy mục nav + gõ URL bị redirect `Unauthorized`. `admin`/`opsmgr`/`workshop`/`tech` → thấy + vào được.
37. Sidebar ↔ route đồng pha: với mỗi path siết ở 7.septies.2/.3, cap nav (`sidebarNav.ts`) = cap route (`router/index.ts`). Không path nào sidebar-ẩn mà route-mở.
38. Không regression: mọi test §7.* + `routeAccess.test.ts` + `sidebarNav.guard.test.ts` + `personas.test.ts` xanh; FE typecheck/build pass; `bench run-tests` (rbac/role_profiles) xanh.

### 7.septies.5 Test cases (TDD — bổ sung)
| ID | Lớp | Mô tả | Kỳ vọng |
|---|---|---|---|
| RT-CAP-1 | FE | `resolveRouteAccess({requiredCapabilities:['data.read']}, ctx)` ctx.can=false mọi cap | `'unauthorized'` |
| RT-CAP-2 | FE | route `/suppliers` meta có `requiredCapabilities:['data.read']` | meta khai đúng (snapshot/route lookup) |
| RT-DEP-1 | FE | `resolveRouteAccess(depMeta, ctx)` với ctx chỉ `document.read`/`training.read` True | `'unauthorized'` (doc bị chặn) |
| RT-DEP-2 | FE | `resolveRouteAccess(depMeta, ctx)` với ctx `needs.read`=True (opsmgr) | `'allow'` |
| RT-DEP-3 | FE | `resolveRouteAccess(depMeta, ctx)` với ctx `pm.read`=True (tech/workshop) | `'allow'` |
| NAV-DEP-1 | FE | `itemVisible(depItem, can(doc-caps), false)` | `false` (ẩn cho doc) |
| NAV-DEP-2 | FE | `itemVisible(depItem, can(opsmgr/tech-caps), false)` | `true` |
| NAV-SUP-1 | FE | sidebar `master` build với can=`data.read`→false | mục `/suppliers` + `/depreciation` ẩn |

## 8. OUT-of-scope (Phase 1)

- Redesign nội dung 8 dashboard (Phase 2) — **In Progress**, spec riêng tại [`FE_Persona_Dashboards.md`](./FE_Persona_Dashboards.md).
- Redesign module list/detail/form theo `docs/fe/` (Phase 3+).
- Thay đổi DocPerm/role BE (chỉ đọc; endpoint mới read-only nếu thật cần).

## 9. Test cases (viết trước — TDD)

| ID | Mô tả | Kỳ vọng |
|---|---|---|
| T1 | `derivePersonas` với role `AssetCore Super Admin` | trả đủ 8 persona |
| T2 | `derivePersonas` với chỉ `PM User` | chứa `tech`, KHÔNG chứa `workshop`/`admin` |
| T3 | `derivePersonas` với `Inventory Manager` | chứa `store` |
| T4 | `derivePersonas` rỗng (không role khớp) | trả `[]` |
| T5 | Persist hợp lệ giữ nguyên; không hợp lệ → fallback rank cao nhất | đúng persona fallback |
| T6 | 1 persona → switcher label tĩnh (no dropdown) | flag `canSwitch=false` |
| T7 | Sidebar items của persona = union MODULE_NAV được phép, lọc theo capability | đúng tập item |
| T8 | Anti-leak: `ac_persona='admin'` khi user chỉ `PM User` | derive loại bỏ `admin`, current = `tech` |
| T9 | `buildSidebarGroups(persona, can, isSuperuser)` với caps tech (`pm.read`,`repair.read`,`calibration.read`) | có group PM/CM/Calibration, KHÔNG có Compliance/Admin/Needs |
| T10 | Item có `cap` mà user thiếu | item ẩn (KHÔNG leak — empty-stub cũ sẽ FAIL test này) |
| T11 | Group sau filter rỗng | group đó không xuất hiện trong output |
| T12 | Superuser (`isSuperuser=true`) | mọi item của persona hiện, bỏ qua capability |
| T13 | Dedupe item theo `path` qua nhiều module trong 1 persona | mỗi path xuất hiện 1 lần |
