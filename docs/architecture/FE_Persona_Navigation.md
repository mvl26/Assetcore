# FE Persona Navigation — Core Doc (Single Source of Truth)

| Mục | Giá trị |
|---|---|
| Phạm vi | Cross-cutting FE shell + RBAC (KHÔNG thuộc 1 IMM-XX) |
| Owner | BA + FE Tech Lead |
| Trạng thái | In Progress — Phase 1 |
| Cập nhật | 2026-05-29 |
| Tham chiếu | `frontend/src/components/common/AppSidebar.vue`, `AppTopBar.vue`, `api/layout.py::get_user_context`, `services/shared/constants.py::Roles`, `fixtures/role.json`, prototype `docs/fe/index.html` |

> Đây là spec mà BE/FE phải code khớp 100% và QA viết test theo. Mọi drift code↔doc = blocking, reconcile doc trước.

---

## 1. Mục tiêu

Chuyển sidebar điều hướng từ **MODULE-scoped** (hiện tại: `route.meta.moduleId` + trang `/launcher`) sang **PERSONA/ROLE-scoped**:

- Sidebar hiển thị nav theo **persona đang chọn**, không theo route hiện tại.
- Thêm **persona switcher** ở topbar (`AppTopBar.vue`), suy persona từ **RBAC THẬT** (`roles` + `imm_roles` trả bởi `get_user_context`).
- **Production-safe**: persona chỉ **LỌC nav hiển thị**, KHÔNG cấp thêm quyền. Mọi action vẫn gate qua **DocPerm (BE)** + **`useCapabilities` (FE)**.

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

Sidebar nav được build bằng cách lấy các `moduleId` trong cột "Sidebar modules" của persona, tra `MODULE_NAV` catalog (đã có trong `AppSidebar.vue`), gộp `items`. Mỗi `NavItem` vẫn lọc tiếp bằng capability (`item.roles` / `useCapabilities`). Vì vậy:

- Một persona có module trong list nhưng user thiếu capability cho 1 item cụ thể → item đó ẩn (giữ nguyên cơ chế `itemVisible` hiện tại).
- `master(read)` nghĩa là module `master` xuất hiện nhưng các item cần Manager-capability tự ẩn.

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
- `/launcher` có thể giữ làm fallback route, nhưng KHÔNG còn là cơ chế điều hướng chính.

---

## 7. Acceptance Criteria

1. `constants/personas.ts` định nghĩa đủ 8 persona: `code`, `label`, `color`, `inferenceRoles`, `modules`, `rank`.
2. `derivePersonas(roles, imm_roles)` đúng spec mục 3 (superuser → 8; theo intersection; sort rank).
3. Sidebar render theo persona đang chọn (mục 2.1), KHÔNG theo `route.meta.moduleId`. Module ngoài persona → không hiện.
4. Persona switcher: chỉ list persona đủ quyền; chọn → đổi sidebar + persist; 1 persona → label tĩnh.
5. Persona persisted không hợp lệ → fallback rank cao nhất + ghi đè `ac_persona`.
6. Anti-leak: set `ac_persona` = persona không đủ quyền → `derivePersonas` loại bỏ → KHÔNG render nav persona đó; mọi item vẫn lọc bằng capability.
7. Không regression build/test FE; BE không đổi (chỉ verify `get_user_context` trả `roles`+`imm_roles`).

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
