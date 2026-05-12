---
name: assetcore-fe
description: Build or extend an AssetCore frontend feature using Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query. Use this whenever the user asks to add a view, list/detail page, form, store, composable, API client, dashboard widget, or any frontend feature for any IMM-XX module — including phrases like "tạo view IMM-09", "thêm trang", "wire FE với BE", "form WO", "Pinia store", "list table với filter", "modal chi tiết". Strongly prefer this skill any time the user is touching the `frontend/` directory or talks about Vue components, even if they don't name the framework.
---

# AssetCore Frontend Module Builder

You are extending the Vue 3 SPA at `/home/miyano/frappe-bench/apps/assetcore/frontend/`. The app talks to the Frappe backend via the `frappeGet` / `frappePost` helpers and uses a strict 4-layer architecture.

## Mental model — 4 layers

```
src/views/<module>/*.vue      ← UI (composition API, <script setup>)
        ↓ uses
src/composables/use*.ts       ← reactive logic (useApi, usePermissions, ...)
        ↓ delegates to
src/stores/<module>.ts        ← Pinia store: shared state across views
        ↓ calls
src/api/<module>.ts           ← typed API client (frappeGet/frappePost)
        ↓ axios
src/api/axios.ts              ← CSRF + auth interceptor
```

**Hard rules:**
- Views never call axios directly. Views call store actions or composables; composables/stores call `src/api/`.
- Every API call goes through `frappeGet`/`frappePost` in `src/api/helpers.ts` — they unwrap the `{message: {success, data}}` envelope and throw `ApiError`.
- **`frappeGet`/`frappePost` return `T` directly, not `ApiResponse<T>`.** API functions must be typed `Promise<T>`, never `Promise<ApiResponse<T>>`. Wrong return type is the #1 root cause of `as unknown as` casts cascading through stores and views — catch it at the API layer, not after.
- Use `useApi().run(fn, opts)` in views to get free toast + loading + field-error wiring.
- Type every API response with an `interface` exported from `src/api/<module>.ts`. The store and views import these — no `any`.
- Stores must NOT re-export the API module (`return { ..., api }` where `api = * from '@/api/xxx'`). That leaks the transport layer into views and breaks the 4-layer separation.
- Catch blocks in stores: always `catch (e: unknown)` + `e instanceof Error ? e.message : String(e)`. Never `catch (e: any)`.

**Display rules (UI/UX — không hiện mã hệ thống với user):**
- **Tên nhà cung cấp**: hiển thị `supplier_name` (tên đọc được), KHÔNG phải `name` (mã `SUP-2026-XXXXX`). Luôn request thêm `supplier_name` trong API response.
- **Tên thiết bị**: hiển thị `asset_name` hoặc device_model — KHÔNG phải `name` (mã `ACC-ASS-*`). Bên dưới mã nhỏ hơn làm sub-text là OK.
- **Người dùng**: hiển thị `full_name`, KHÔNG phải `email` hay system user ID — trừ sub-text phụ.
- **Trạng thái**: dùng `STATUS_LABEL` map để dịch — mọi status key trong map PHẢI khớp **chính xác** với constant trong BE service (`_STATUS_*`). Không tự đặt tên "thân thiện" cho status key.
- **Select options trong form**: options `<select>` PHẢI khớp chính xác với `options` trong DocType JSON field. Không dùng nhãn tiếng Việt làm value — value là string kỹ thuật, label mới là tiếng Việt.
- **Risk class mapping**: AC Asset dùng `"Low/Medium/High/Critical"`. Khi truyền sang DocType khác có schema khác (vd Asset Repair dùng `"Class I/II/III"`), PHẢI có mapping layer trong service BE — FE không tự map.
- **`allowed_transitions` check**: `includes(...)` dùng đúng chuỗi BE trả về, không dùng tên display. Luôn kiểm tra `_VALID_TRANSITIONS` dict trong service khi viết `canXxx` computed.

**Form state rules:**
- `useFormDraft` lưu draft vào localStorage — sau khi fix options/values, test với fresh state (clear localStorage hoặc dùng private window) để tránh bug từ cache cũ.
- Khi thay đổi select options hay default values, luôn kiểm tra: form draft có thể giữ giá trị cũ không còn hợp lệ.

## Stack quick-reference

| Concern | Tool | Where it lives |
|---|---|---|
| Component framework | Vue 3 (`<script setup lang="ts">`) | `vite.config.ts` |
| State | Pinia + `pinia-plugin-persistedstate` (auth only) | `src/stores/`, `src/main.ts` |
| Routing | Vue Router 4 | `src/router/index.ts` (12 numbered sections) |
| HTTP | axios + `frappeGet/frappePost` envelope unwrap | `src/api/axios.ts`, `src/api/helpers.ts` |
| Generic CRUD | `FrappeResource<T>` for `/api/resource/...` (rarely needed) | `src/services/frappeResource.ts` |
| Server cache | `@tanstack/vue-query` (`staleTime: 5min`, `gcTime: 10min` global) | `src/main.ts` |
| i18n | `vue-i18n` | `src/locales/` |
| Styling | TailwindCSS (utility-first; emerald-600 primary, neutral-* surfaces) | `tailwind.config.js` |
| Forms | controlled `ref`s + `useApi.onFieldError` + `useFormDraft` autosave | `src/composables/useFormDraft.ts` |
| QR | `qrcode` npm — for asset labels | — |
| Permissions UI | `v-permission` directive | `src/directives/permission.ts` |
| Toast | `useToast` composable + `ToastContainer` mounted in `App.vue` | `src/composables/useToast.ts` |

## File layout

```
frontend/src/
├── api/immXX.ts            # IMM-coded — mirror BE module name
├── stores/immXX.ts         # IMM-coded — match api/ layer
├── composables/use<X>.ts   # reusable reactive logic
├── views/<domain>/         # DOMAIN-named — never immXX
│   ├── ListView.vue
│   ├── DetailView.vue
│   └── components/...
├── components/<domain>/    # shared sub-components (cards, modals)
├── router/index.ts         # add new routes here
└── types/                  # cross-cutting types
```

## Naming convention — NO EXCEPTIONS

The codebase uses **two layers with different naming systems**. Mixing them creates the worst-of-both situation. Stick to:

| Layer | Pattern | Example | Wrong |
|-------|---------|---------|-------|
| `api/` | `immXX.ts` (IMM-coded, mirrors BE) | `api/imm09.ts` | `api/repair.ts`, `api/immXX-cm.ts` |
| `stores/` | `immXX.ts` (IMM-coded, no prefix/suffix) | `stores/imm09.ts` | `stores/useImm09Store.ts`, `stores/repair.ts`, `stores/imm09Store.ts` |
| `views/<domain>/` | Domain folder, lowercase, hyphenated | `views/cm/`, `views/tech-specs/`, `views/master-data/` | `views/imm09/`, `views/IMM09/`, `views/CM/` |
| `components/<domain>/` | Same as views | `components/commissioning/` | `components/imm04/` |

**Domain → IMM module mapping** (canonical — extend this table when adding a new module):

| Domain folder | IMM module | Notes |
|---------------|-----------|-------|
| `needs` | IMM-01 | Needs Requests + Procurement Plans |
| `tech-specs` | IMM-02 | Technical Specifications |
| `procurement` | IMM-03 | Vendor Eval, AVL, Decisions (purchase orders go in `purchase/`) |
| `commissioning` | IMM-04 | Installation + commissioning |
| `document` | IMM-05 | Document repository |
| `training` | IMM-06 | Training programs + sessions |
| `pm` | IMM-08 | Preventive Maintenance |
| `cm` | IMM-09 | Corrective Maintenance / Repair |
| `calibration` | IMM-11 | Calibration |
| `incident` | IMM-12 | Incident + RCA |
| `inventory` | IMM-15 | Spare parts + stock |
| `audit` | IMM-16 | Compliance / audit trail |

**Rationale:**
- `api/` and `stores/` are the "code" layer — they mirror BE for traceability (`assetcore.api.imm09` ↔ `frontend/src/api/imm09.ts`).
- `views/` is the "presentation" layer — URL paths are domain-named (`/cm/work-orders`, not `/imm09/work-orders`), so folders match URLs for readability.
- New modules MUST use domain folder names. If a clean domain noun doesn't exist, propose one in this table before creating the folder.

## API client template

```ts
// src/api/immXX.ts
import { frappeGet, frappePost } from './helpers'

export interface XThing {
  name: string
  asset_ref: string
  status: 'Open' | 'In Progress' | 'Completed'
  // ...
}

export interface XListResponse {
  data: XThing[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

// ✅ Return type is Promise<T>, never Promise<ApiResponse<T>>
// frappeGet/frappePost already unwrap the Frappe envelope — wrapping again
// causes cascade `as unknown as` casts in stores and views.
export function listXThings(filters: Record<string, unknown> = {}, page = 1, pageSize = 20)
  : Promise<XListResponse> {
  return frappeGet('assetcore.api.immXX.list_x_things', {
    filters: JSON.stringify(filters), page, page_size: pageSize,
  })
}

export function createXThing(payload: Partial<XThing>): Promise<{ name: string }> {
  return frappePost('assetcore.api.immXX.create_x_thing', payload)
}

// ✅ Direct return — no redundant `const res = await ...; return res`
export function getXThing(name: string): Promise<XThing> {
  return frappeGet('assetcore.api.immXX.get_x_thing', { name })
}
```

**Conventions:**
- Always pass dict/list params as `JSON.stringify(...)` — BE expects strings and parses them.
- Endpoint path mirrors BE: `assetcore.api.<module>.<function_name>` (snake_case).
- Status values are unioned string literals — keep them in sync with BE's `XStatus` class.
- Read endpoints → `frappeGet`. Mutating → `frappePost` (BE must declare `methods=["POST"]`).

## Store template (Pinia setup syntax)

```ts
// src/stores/immXX.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { listXThings, getXThing, createXThing, type XThing } from '@/api/immXX'

export const useImmXXStore = defineStore('immXX', () => {
  // state
  const items = ref<XThing[]>([])
  const current = ref<XThing | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  // getters
  const openItems = computed(() => items.value.filter(i => i.status === 'Open'))

  // actions
  async function fetchItems(filters = {}, page = 1) {
    loading.value = true; error.value = null
    try {
      const res = await listXThings(filters, page)
      items.value = res.data
      pagination.value = res.pagination
    } catch (e: unknown) {
      // Never `catch (e: any)` — use unknown + instanceof guard
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  return { items, current, loading, error, pagination, openItems, fetchItems }
})
```

**Conventions:**
- Use the Pinia "setup" syntax (function returning refs/computed/actions). Don't use `state/getters/actions` object form — codebase is uniform on setup syntax.
- Store name is camelCase (`'immXX'`, `'imm09'`). Hook name is `useImmXXStore`.
- Don't `import { useToast }` inside stores — toasts belong in views via `useApi`. Stores set `error` and let views surface it.
- Mutating actions should re-fetch the affected record after success so the store stays consistent (`await fetchWorkOrder(name)`).

## View template

```vue
<!-- src/views/immXX/RepairListView.vue -->
<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useImmXXStore } from '@/stores/immXX'
import { useApi } from '@/composables/useApi'
import { usePermissions } from '@/composables/usePermissions'

const store = useImmXXStore()
const { items, loading, pagination } = storeToRefs(store)
const api = useApi()
const router = useRouter()
const perms = usePermissions()

const filters = reactive({ status: '', priority: '' })

async function load(page = 1) {
  await api.run(() => store.fetchItems(filters, page), { silentSuccess: true })
}

onMounted(() => load())
</script>

<template>
  <div class="p-6">
    <header class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-semibold">Lệnh sửa chữa</h1>
      <button v-if="perms.canCreateWO"
              class="px-3 py-2 rounded bg-emerald-600 text-white"
              @click="router.push({ name: 'imm09-create' })">
        Tạo mới
      </button>
    </header>

    <!-- filters -->
    <div class="flex gap-2 mb-4">
      <select v-model="filters.status" @change="load(1)" class="border rounded px-2 py-1">
        <option value="">Tất cả trạng thái</option>
        <option value="Open">Mở</option>
        <option value="In Progress">Đang xử lý</option>
      </select>
    </div>

    <!-- loading state -->
    <div v-if="loading" class="py-8 text-center text-neutral-400">Đang tải…</div>

    <!-- error state — must always be present alongside loading -->
    <div v-else-if="error"
         class="rounded border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 flex items-center gap-3">
      <span class="flex-1">{{ error }}</span>
      <button class="text-sm underline" @click="load()">Thử lại</button>
    </div>

    <!-- data -->
    <table v-else class="w-full text-sm">…</table>
  </div>
</template>
```

**Conventions:**
- `<script setup lang="ts">` — never the Options API.
- Use `storeToRefs` so destructured store state stays reactive.
- Wrap user actions in `api.run(...)` — gets toast + loading + field-error free.
- Tailwind classes inline. Avoid SCSS modules. Brand: `emerald-600` for primary, `neutral-*` for surfaces.
- All UI strings in Vietnamese (project default). Use `vue-i18n` keys when adding new locales.

## useApi pattern (memorize this)

```ts
const api = useApi()

const formErrors = reactive<Record<string, string>>({})

const result = await api.run(() => createXThing(payload), {
  successMessage: 'Đã tạo work order',
  onFieldError: (fields) => Object.assign(formErrors, fields),
})

if (result) {
  // happy path — result is the unwrapped data
  router.push({ name: 'imm09-detail', params: { name: result.name } })
}
// `result` is null on error; toast already shown unless silentError: true
```

`useApi` automatically:
- Shows green toast on `successMessage`.
- Shows yellow toast for `BUSINESS_RULE_VIOLATION` / `VALIDATION_ERROR` / `CONFLICT` (`isBusinessError`).
- Shows red toast for `INTERNAL_ERROR` / network errors.
- Skips toast for 401/403 (axios interceptor redirects to login).
- Calls `onFieldError(fields)` so your form can render inline errors next to inputs.

## Routing

```ts
// src/router/index.ts — add to existing routes array
import { ROLES_CM_MANAGE } from '@/constants/roles'

{
  path: '/imm09',
  meta: { requiresAuth: true, roles: ROLES_CM_MANAGE },
  children: [
    { path: '', name: 'imm09-list', component: () => import('@/views/cm/ListView.vue') },
    { path: ':name', name: 'imm09-detail', component: () => import('@/views/cm/DetailView.vue'), props: true },
  ],
}
```

Conventions:
- Lazy-import every view (`() => import(...)`) — keeps initial bundle small.
- `meta.roles` should be a `readonly RoleName[]` from `@/constants/roles` (not inline strings). The navigation guard in `router/index.ts` checks them against `useAuthStore().roles` and redirects to `/login` or `/403` accordingly.
- Existing routing convention sections are documented at the top of `router/index.ts` (12 sections: Auth/Root, IMM-00, IMM-04, …, Errors). Insert new routes into the matching section instead of appending.

## Permissions — three layers, pick the right one

**1. Role constants — `@/constants/roles`** (mirrors BE `services.shared.constants.Roles`):

```ts
import { Roles, ALL_IMM_ROLES, ROLES_CREATE_WO, ROLES_APPROVE, ROLES_PM_MANAGE,
         ROLES_CM_MANAGE, ROLES_CAL_MANAGE, ROLES_INCIDENT_REPORT, ROLES_RCA_OWNER,
         ROLES_CAPA_CLOSE, ROLES_MANAGE_DOCS, ROLES_ADMIN_ONLY } from '@/constants/roles'
```

Every role and group used by routes / directives must come from this file. Adding a role to BE? Mirror it here.

**2. Auth store — `useAuthStore()`** is the source of truth at runtime:

```ts
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()

auth.hasRole(Roles.WORKSHOP)
auth.hasAnyRole(ROLES_APPROVE)
auth.canCreate          // group computeds
auth.canApprove
auth.canSubmit
auth.canManageDocs
auth.isSystemAdmin
```

**3. `v-permission` directive** — for declarative show/hide:

```vue
<button v-permission="Roles.SYS_ADMIN">Admin only</button>
<button v-permission="ROLES_APPROVE">Approve</button>
```

The directive removes the element from the DOM if the user lacks the role — it's not just `display: none`, so don't rely on `v-permission` to hide truly sensitive data (the API check is what matters).

**Note on the `usePermissions` composable:** an older composable at `composables/usePermissions.ts` exposes a thinner subset (`isAdmin`, `isQA`, `canApproveRelease`). New code should prefer `useAuthStore()` directly — it has more accurate IMM role helpers and stays in sync with the role constants. The composable is kept for the few legacy components still using it.

## TanStack Query (for read-heavy lists)

Vue Query is configured globally in `src/main.ts` with `staleTime: 5min` and `gcTime: 10min` — use those defaults unless you have a reason to override. When a list is queried from many places and benefits from background refresh / stale-while-revalidate, prefer Vue Query over a Pinia action:

```ts
import { useQuery } from '@tanstack/vue-query'

const { data, isLoading, refetch } = useQuery({
  queryKey: ['imm09', 'list', filters],
  queryFn: () => listXThings(unref(filters)),
  // staleTime: 30_000,  // override only if needed
})
```

Reserve Pinia for client-owned state (auth, current selection, draft form). Use Vue Query for server-owned state. Auth store uses `pinia-plugin-persistedstate` to keep the user across reloads — your modules typically don't need persistence.

## Forms with autosave

Use `useFormDraft` for any multi-step or long form (saves to localStorage). See `src/composables/useFormDraft.ts`.

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Cascade of `as unknown as T` casts in store/views | API function typed `Promise<ApiResponse<T>>` instead of `Promise<T>` | Fix return type in `api/immXX.ts` — `frappeGet`/`frappePost` already unwrap the envelope |
| Runtime crash: `e.message` is undefined | `catch (e: any)` when `e` is a string or plain object | Use `catch (e: unknown)` + `e instanceof Error ? e.message : String(e)` |
| View can call `store.api.xxx()` — layer violation | Store returns `api` namespace in its return object | Remove `api` from store return; views import directly from `@/api/` |
| `object` / `object[]` param not type-safe | API function typed `param: object` | Use `Record<string, unknown>` or `Record<string, unknown>[]` |
| Empty table flashes before data loads | `v-if="!loading"` shows table with 0 rows during first fetch | Use `v-if="loading"` / `v-else-if="error"` / `v-else` tri-branch |
| Error is swallowed silently, user sees empty list | `v-else` shows empty state even when `store.error !== null` | Always add `v-else-if="error"` branch with error banner + retry button |
| 403 on every POST after login | CSRF token not refreshed | `setCsrfToken(loginResponse.data.csrf_token)` after login |
| Store updates but view doesn't re-render | Used `const { items } = store` instead of `storeToRefs` | Use `storeToRefs` |
| Toast shows red for "asset already under repair" | BE returned wrong code (should be `CONFLICT`) | Fix BE — UX category derives from `ErrorCode` |
| Form errors don't appear | Forgot `onFieldError` in `api.run` opts | Add it; bind to a reactive `formErrors` |
| `JSON.parse` error from FE | BE used `frappe.whitelist` without methods=POST and FE sent body | BE needs `methods=["POST"]` |
| Hot reload broken | Vite proxy not configured for `/api/method` | Check `vite.config.ts` proxy |
| Table cell hiển thị raw `WO-RP-2026-00123` thay vì tên thiết bị | BE list endpoint chỉ trả `asset_ref` (Link ID), thiếu `asset_name` | **Fix BE**: `services/immXX.py` thêm `asset_name` vào `fields=[...]` của `frappe.get_all(...)`. FE không workaround bằng extra fetch. |
| FE template dùng pattern `{{ wo.asset_name \|\| wo.asset_ref }}` fallback | BE response shape không nhất quán — đôi khi trả name, đôi khi không | **Fix BE** một lần cho dứt; FE bỏ fallback sau khi BE đã chuẩn |
| Form Create gọi `loadAssetMeta(ref)` riêng sau khi user nhập ref → N+1 query, UX chậm | BE list/search endpoint cho Link field không kèm meta | **Fix BE**: link search endpoint trả `{name, asset_name, device_model_name, location_name, risk_class}` trong cùng response. FE bỏ `loadXxxMeta()` |
| Sidebar trống khi vào module | Route thiếu `meta.moduleId` hoặc key sai với `MODULE_NAV` | Set `meta.moduleId: 'immXX'` matching key trong `MODULE_NAV` |
| Module mới không hiện trong launcher | Tile có `disabled: true` từ wave trước hoặc `to:` route không tồn tại | Set `disabled: false` + verify route tồn tại trong router |

## Critical anti-patterns (từ bugs thực tế — KHÔNG lặp lại)

### ✅ Pattern chuẩn: BASE URL trong API client
```typescript
// ✅ ĐÚNG — dùng const BASE như IMM-09 gold standard
const BASE = '/api/method/assetcore.api.imm06'
return frappeGet(`${BASE}.list_programs`, params)
```
`frappeGet` nhận full path string và pass thẳng vào axios (baseURL = `''`). Pattern `const BASE = '/api/method/assetcore.api.immXX'` là **chuẩn** và nhất quán với IMM-09. Đây KHÔNG phải double-prefix bug.

### 🚫 Lỗi #2: Function name không khớp BE
FE gọi `assetcore.api.imm06.list_programs` nhưng BE expose `list_training_programs`. Result: 100% call fail 404. **Trước khi build FE**: verify mỗi endpoint name trong `assetcore/api/immXX.py` khớp với gì FE sẽ gọi.

Verify command:
```bash
grep "@frappe.whitelist" assetcore/api/immXX.py -A1 | grep "def " | awk '{print $2}' | cut -d'(' -f1
```

### 🚫 Lỗi #3: Planning/Wave 2 roles thiếu trong roles.ts
FE `constants/roles.ts` có thể thiếu roles mới thêm vào BE (`PLANNING`, `TRAINING_OFFICER`, v.v.). **Trước khi build views**: check `assetcore/services/shared/constants.py` và sync tất cả Roles chưa có trong `frontend/src/constants/roles.ts`.

### 🚫 Lỗi #4: Store thiếu nhưng view vẫn chạy (silent undefined)
Một số modules chỉ có API client mà không có dedicated Pinia store — views dùng composable inline hoặc `useMasterDataStore`. **Check trước**: nếu module có ≥3 views hoặc shared state giữa views, cần store riêng. Nếu không, document rõ "module X dùng `useMasterDataStore`".

## Where to look for live examples

- `src/api/imm09.ts`, `src/stores/imm09.ts`, `src/views/cm/` — full IMM-09 vertical (Corrective Maintenance)
- `src/api/imm08.ts`, `src/stores/imm08.ts`, `src/views/pm/` — IMM-08 (Preventive Maintenance)
- `src/api/imm11.ts`, `src/views/calibration/` — IMM-11 (Calibration)
- `src/api/helpers.ts` — `frappeGet`, `frappePost`, envelope unwrap
- `src/api/errors.ts` — `ApiError`, `ErrorCode`, `httpStatusToCode`, `toApiError`
- `src/api/axios.ts` — CSRF interceptor (`setCsrfToken`, `getCsrfToken`, retry-on-CSRF-fail)
- `src/services/frappeResource.ts` — generic `FrappeResource<T>` wrapper for `/api/resource/...` (Frappe core CRUD); use sparingly, prefer module-specific endpoints in `src/api/`
- `src/composables/useApi.ts` — request wrapper (toast + loading + field-error)
- `src/composables/usePagination.ts`, `useFormDraft.ts`, `useWorkflow.ts`, `useToast.ts` — common composables
- `src/components/common/` — `BaseModal`, `BasePagination`, `StatusBadge`, `ListFilterBar`, `LinkSearch`, `SmartSelect`, `LoadingSpinner`, `SkeletonLoader`, `ToastContainer`, `PageHeader`, `AppLayout`, `AppSidebar`, `AppTopBar` — reuse these instead of rebuilding
- `src/constants/roles.ts` — role catalog (mirror of BE)
- `src/directives/permission.ts` — `v-permission`
- `src/stores/auth.ts` — auth + role helpers (canCreate, canApprove, etc.)
- `src/main.ts` — app bootstrap (Pinia + persisted state, Vue Query defaults, i18n, error handlers)

## UI Completeness — bắt buộc trước khi khai báo Done

Mọi module page phải đáp ứng checklist này. **Thiếu một mục = module chưa xong.**

### List page checklist
- [ ] Có nút **"Tạo mới"** (hoặc "Tạo kế hoạch", "Tạo WO", tùy ngữ cảnh) — click → vào form tạo hoặc modal
- [ ] Click row → navigate đúng detail URL (`:id` hoặc `:name` match route param)
- [ ] Filter → table cập nhật (không chỉ hiển thị danh sách tĩnh)
- [ ] Pagination hoạt động nếu có nhiều records
- [ ] Empty state có CTA rõ ràng, không chỉ "Không có dữ liệu"
- [ ] Loading skeleton hoặc spinner khi đang fetch
- [ ] Error banner + retry button khi API lỗi

### Detail page checklist
- [ ] Hiển thị đủ fields — không section nào toàn "—" nếu data tồn tại
- [ ] Workflow action buttons đúng theo state:
  - Draft/Pending: nút chuyển sang state tiếp theo
  - Final state (Closed/Cancelled/Expired): không có nút transition, chỉ read-only
  - Button disabled + tooltip nếu precondition chưa đủ (không âm thầm ẩn)
- [ ] Nút **"← Quay lại"** về list page
- [ ] Nút **"Chỉnh sửa"** nếu record có thể edit ở trạng thái hiện tại
- [ ] Tabs có dữ liệu (KPI, Audit trail, Timeline) — không empty state giả vì thiếu seed data
- [ ] **Stats tabs (KPI, Uptime, MTBF, Khấu hao)**: phải có work order data + lifecycle events trước khi claim pass. Số liệu luôn 0 dù có WO = bug.

### Lỗi phổ biến cần kiểm tra ngay
| Symptom | Root cause | Fix |
|---|---|---|
| List page không có "Tạo mới" | Button bị quên hoặc wrapped trong permission guard sai | Thêm button; check `v-if` / `v-permission` |
| Click row vào detail → 404 | Route param `id` nhưng link dùng `record.name` (đúng, cần verify naming) hoặc ngược lại | Kiểm tra router `:id` vs link `:to` pattern |
| Tab "KPI"/"Audit" empty dù đã click | Data chưa được seed (work orders, lifecycle events) | Seed data trước khi test, không khai báo tab pass khi chưa có data |
| Workflow button không hiện | State constant FE ≠ BE (vd FE check `=== 'draft'` nhưng BE trả `'Draft'`) | Grep BE service `_STATUS_*` constants và sync FE |
| Stats luôn = 0 | API endpoint không aggregate đúng, hoặc FE không gọi đúng API | Kiểm tra BE service function tính KPI có join đúng table không |

## Build sequence for a new IMM module on FE (exact file paths)

**Tạo các files theo thứ tự này:**
```
frontend/src/api/immXX.ts          ← 1. API client
frontend/src/stores/immXX.ts       ← 2. Pinia store
frontend/src/views/<domain>/       ← 3. View folder (domain-named, không phải immXX/)
    ListView.vue
    DetailView.vue
    components/
```

1. **Verify BE endpoint names trước tiên** (BLOCKING — không skip):
   ```bash
   grep "@frappe.whitelist" -A1 assetcore/api/immXX.py | grep "def " | awk '{print $2}' | cut -d'(' -f1
   ```
   Đây là danh sách path FE phải gọi (`assetcore.api.immXX.<name>`). Đối chiếu với `docs/imm-XX/05_API_Specification.md`. Nếu BE và spec lệch → fix BE trước.

1b. **Verify role constants**: Check `assetcore/services/shared/constants.py::Roles` xem có role mới nào. Sync vào `frontend/src/constants/roles.ts` nếu chưa có.
2. Define TypeScript interfaces in `src/api/<module>.ts` mirroring BE response shape (status union, datetime as `string | null`).
3. Implement endpoint functions using `frappeGet`/`frappePost` (path = `assetcore.api.<module>.<fn>`).
4. Build Pinia store with state + actions. Re-fetch after every mutation so cache stays consistent.
5. Build views: list → detail → form. Each wraps actions in `api.run(...)`. Reuse `BaseModal`, `BasePagination`, `StatusBadge`, `ListFilterBar`, `LinkSearch` from `components/common/` instead of rebuilding.
6. Add routes to the matching numbered section in `src/router/index.ts`. Use `meta.roles = ROLES_X_MANAGE` from `@/constants/roles`. Lazy-import every view.
7. Add nav entries via `composables/useSidebar.ts`.
8. Add role constants/groups to `@/constants/roles.ts` if BE introduced new ones — keep BE/FE in sync.
9. `cd frontend && npm run typecheck && npm run lint` before claiming done (`vue-tsc --noEmit` catches most regressions).
9b. **Verify endpoint connectivity**: Với mỗi `frappeGet/frappePost` trong `api/immXX.ts`, grep tên function trong `assetcore/api/immXX.py` để confirm khớp. Không để API mismatch lọt vào PR.
10. `npm run dev` (with `bench start` running for `/api/method` proxy) and exercise happy path + at least one BE error path in the browser.

---

## UI Completeness Rules (bắt buộc)

Mọi module FE PHẢI có đủ:

### List page
- **Create button**: nút "Tạo [entity]" hoặc "+ Thêm mới" ở PageHeader `#actions` slot → navigate đến create form
- **Row clickable**: `@click="router.push('/path/' + row.name)"` → detail page
- **Empty state CTA**: nút "Tạo [entity] đầu tiên" khi list rỗng

### Detail page
- **Back button**: nút ← quay lại list
- **Workflow action buttons**: computed `canXxx` based trên `status` + `allowed_transitions`; nút hiện đúng state
  - Pattern: `v-if="canApprove"` → gọi action → reload data → toast
  - Không để page ở trạng thái "read-only hoàn toàn" trừ khi document đã Closed/Cancelled
- **Edit functionality**: nếu Draft → có inline edit hoặc nút "Sửa"
- **Tabs có data**: KPI tab phải hiện số liệu thực (uptime, MTBF, MTTR từ API); Audit Trail tab fetch và hiện events; không hard-code empty state

### Workflow button pattern chuẩn

```vue
<div class="flex gap-2 mt-4">
  <button v-if="canApprove" class="btn-primary" @click="doApprove">
    Phê duyệt
  </button>
  <button v-if="canActivate" class="btn-primary" @click="doActivate">
    Kích hoạt
  </button>
  <button v-if="canClose" class="btn-outline" @click="doClose">
    Đóng
  </button>
</div>

<script setup>
const canApprove = computed(() => form.value.workflow_state === 'Draft')
const canActivate = computed(() => form.value.workflow_state === 'Approved')
const canClose = computed(() => form.value.workflow_state === 'Active')

async function doApprove() {
  await api.run(() => approvePlan(form.value.name))
  await loadData()
}
</script>
```

### API function naming convention
- `create[Entity]` — POST tạo mới
- `approve[Entity]` / `activate[Entity]` / `close[Entity]` — workflow transitions
- `set[Field]` — update single field
- `remove[Child]From[Parent]` — xóa child row

---

## Cross-skill conventions

Read [`/.claude/skills/CONVENTIONS.md`](../CONVENTIONS.md) for project-wide rules. Especially relevant to this skill:

- §3. Error Handling — FE error codes mirror BE `ErrorCode` enum; sync via `frontend/src/api/errors.ts`
- §8. Vietnamese vs English — labels VN, code EN
- §9. Wave-aware — IMM-09 is the BE reference; mirror its FE patterns

### Module-specific gotchas
- `useWorkflow` composable is the canonical workflow-aware form pattern
- `usePermissions` is legacy; new code should use `useAuthStore()`
- Routes for IMM-XX live under `frontend/src/views/<module>/`
