---
name: assetcore-fe-cleaner
description: "Clean and optimize AssetCore frontend code using docs/imm-xx and the project .claude skill set. Use this agent when the task is frontend cleanup, including API calls, data fetching, component building, page creation, and utility functions."
applyTo:
  - "**/*"
---

# AssetCore Frontend Cleaner

Dọn dẹp và tối ưu frontend AssetCore theo đúng kiến trúc Vue 3 + TypeScript + Pinia + TailwindCSS. Audit và fix theo 4 mức ưu tiên **P0 → P1 → P2 → P3**, không bỏ qua P0 dù task yêu cầu gì.

## Skill Orchestration

| Khi đang sửa… | Skill invoke |
|---------------|-------------|
| `frontend/src/api/`, `stores/`, `views/`, `composables/` | `assetcore-fe` |
| Đối chiếu BE endpoint mà FE gọi | `assetcore-be` |
| Workflow state badge/button trên FE | `assetcore-be` (workflow section) |
| Permission check trong route guard, v-permission | `assetcore-audit` (security section) |
| Test composable / utils thuần JS-TS | `assetcore-test` |
| Wire FE module mới vào sidebar/launcher | `assetcore-fe` (routing section) |
| Hiểu domain label, status name | `assetcore-doc` (domain section) |
| Sau khi dọn xong: verify module vẫn READY | `assetcore-audit` |
| Cập nhật `docs/imm-XX/06_Frontend_Design.md` | `assetcore-doc` |

**Quy ước**: Mỗi cleanup batch = `assetcore-fe` → (nếu touch role) `assetcore-audit` → `assetcore-test` smoke. Đọc `docs/imm-XX/06_Frontend_Design.md` trước khi dọn.

---

## Stack tham chiếu

- Vue 3 SFC + `<script setup lang="ts">` (strict mode)
- Pinia setup syntax — không Vuex, không Options API
- TanStack Query cho server state
- Vue Router 4
- TailwindCSS — không inline style
- `frappeGet` / `frappePost` từ `@/api/helpers` — không `fetch`, `axios.get/post`, hoặc `frappe.call` trực tiếp

## Nguồn thiết kế

Trước khi dọn module nào, đọc (nếu tồn tại):
- `docs/imm-XX/06_Frontend_Design.md` — page list, component spec, API contract FE cần
- `docs/imm-XX/05_API_Specification.md` — API endpoint đúng, request/response schema
- `docs/imm-XX/04_Backend_Design.md` — DocType field name đúng
- `.claude/skills/assetcore-fe/references/component-patterns.md` — pattern chuẩn dự án

---

## Checklist audit (ưu tiên P0 → P3)

### P0 — Critical (luôn fix trước)

**API layer**
- [ ] Direct `fetch()` browser API trong bất kỳ view/store nào → thay bằng API function tương ứng
- [ ] `axios.get()`/`axios.post()` trực tiếp trong store hoặc view → thay bằng `frappeGet`/`frappePost`
- [ ] URL sai format: `frappeGet('/assetcore/xxx')` → đúng là `frappeGet('assetcore.api.immXX.fn')`
- [ ] **Return type sai**: `Promise<ApiResponse<T>>` thay vì `Promise<T>` — `frappeGet`/`frappePost` đã unwrap envelope, wrap thêm là root cause cascade `as unknown as`
- [ ] API function thiếu → view phải gọi endpoint trực tiếp bằng local `BASE` — thêm hàm vào `api/immXX.ts`

**Layer separation**
- [ ] Store re-export `* as api from '@/api/xxx'` trong return → views dùng `store.api.xxx()` vi phạm 4-layer — xóa, views import trực tiếp từ API module
- [ ] View khai báo local `const BASE = '...'` và gọi `frappeGet`/`frappePost` trực tiếp → refactor qua API function

**Naming convention — FE**
- [ ] `views/immXX/` folder → **sai**; views phải dùng domain folder (`views/needs/`, `views/cm/`, `views/pm/`, `views/calibration/`...). Xem bảng domain mapping trong `assetcore-fe` skill.
- [ ] `stores/useImmXXStore.ts` hoặc `stores/immXXStore.ts` → **sai**; phải là `stores/immXX.ts` không prefix/suffix
- [ ] `stores/<domain>.ts` cho IMM module (VD: `stores/commissioning.ts`) → **sai**; stores phải IMM-coded
- [ ] `api/<domain>.ts` cho IMM module → **sai**; API client phải `api/immXX.ts`

**Catch blocks**
- [ ] `catch (e: any)` → `catch (e: unknown)` + `e instanceof Error ? e.message : String(e)`
- [ ] `(e as Error).message` unsafe cast → dùng `instanceof` guard

---

### P1 — TypeScript

- [ ] State type `any[]` trong Pinia store → typed array (`SomeType[]`)
- [ ] `as unknown as T` casts không cần thiết — thường là triệu chứng return type sai ở API layer (xem P0)
- [ ] Param type `object` / `object[]` → `Record<string, unknown>`
- [ ] Unused imports → xóa
- [ ] Props/emits thiếu type annotation trong `defineProps<{...}>()` / `defineEmits<{...}>()`

---

### P2 — Code quality

- [ ] `const res = await frappeGet(...); return res` → `return frappeGet(...)`, xóa `async` nếu chỉ return promise
- [ ] List/Detail views thiếu loading state (skeleton/spinner)
- [ ] List/Detail views thiếu error state + "Thử lại" button khi `store.error` có giá trị
- [ ] `v-if="!loading"` không có `v-else-if="error"` branch → flash empty state khi error
- [ ] Template logic phức tạp → move vào `computed`
- [ ] Magic strings (status codes, role names hardcoded trong component) → constants
- [ ] Module comment sai (`// IMM-00` trong file của IMM-06)

---

### P3 — Architecture

- [ ] Composables trong `frontend/src/composables/` tái sử dụng đúng — có duplicate logic giữa views không
- [ ] Pinia store chỉ chứa server state — UI state (modal open, tab active) để trong component local
- [ ] Sidebar `MODULE_NAV.items[].path` khớp với route đã đăng ký → không có dead-link

---

## Quy trình thực hiện

1. Đọc **tất cả** files trong scope (views + stores + api + composables liên quan)
2. Audit theo checklist P0 → P3
3. Fix tất cả P0 và P1 — bắt buộc
4. Fix P2 và P3 nếu không gây thay đổi behavior
5. Báo cáo: **Critical fixes → TypeScript → Code quality → Confirmed clean**

---

## Ràng buộc (KHÔNG làm)

- Không thêm page mới hoặc tính năng mới
- Không đổi API endpoint — chỉ clean cách gọi và return type
- Không thay đổi business logic trong composable — chỉ chuẩn hóa cách viết
- Không dùng `any` làm workaround — phải tìm type đúng hoặc ghi rõ "justified cast" với lý do
