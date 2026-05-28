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

## 🛑 PRE-DONE GREP GATE (chạy TRƯỚC khi nói DONE)

5 phiên test 2026-05-15..26 leak lại cùng pattern dù LL-FE-3/6/13 đã có. Bắt buộc chạy 3 grep gate dưới đây trên view/component bạn vừa sửa. **Output ≠ 0 → fix, không skip.**

```bash
cd /home/miyano/frappe-bench/apps/assetcore

# GATE-1: English enum leak. Mọi {{ row.status }} / {{ doc.frequency }} / severity
# phải đi qua label map (STATUS_LABEL / FREQ_LABEL / SEVERITY_LABEL).
grep -rnE "\{\{\s*(row|item|doc|d)\.(status|workflow_state|frequency|severity)\s*\}\}" \
  frontend/src/views/<your-domain>/ \
  | grep -v "STATUS_LABEL\|FREQ_LABEL\|SEVERITY_LABEL\|statusLabel\|labelFor"

# GATE-2: Raw code/email leak. row.technician/owner/vendor/model/asset/warehouse
# phải có `_name` / `_full_name` companion từ BE và FE phải dùng `x_name || x`.
grep -rnE "row\.(asset|model|vendor|warehouse|department|technician|assigned_to|owner)\b" \
  frontend/src/views/<your-domain>/ | grep -vE "_name|_full_name|_label"

# GATE-3: Hardcoded English status strings trong code (không phải template)
grep -rnE "['\"](Locked|Evaluated|Contract Signed|Scheduled|Weekly|Minor|Open|In Progress)['\"]" \
  frontend/src/views/<your-domain>/ | grep -v "STATUS_LABEL\|// "
```

Kèm 2 manual check không tự động được:
- DetailView có **TRANSITIONS_BY_STATE đầy đủ initial state** (Draft/Open/Planned)? Count entries trong map phải = số state non-terminal trong workflow JSON.
- ListView có **ít nhất 1 action button** (Tạo / Import / Navigate)? Empty state actionable?

Reference: §0 + §13–§24 trong [CONVENTIONS.md](../CONVENTIONS.md).

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

---

## Lessons Learned 2026-05 (bug patterns đã gặp — phải tránh)

### LL-FE-1: `TRANSITIONS_BY_STATE` map phải đầy đủ TẤT CẢ states

Bug: PD detail view có 8 states, nhưng `TRANSITIONS_BY_STATE` chỉ map 5 states đầu → state "Contract Signed" không có nút "Phát hành PO" → user kẹt.

```typescript
// ❌ SAI — thiếu state Contract Signed
const TRANSITIONS_BY_STATE: Record<string, string[]> = {
  'Draft':             ['Chọn phương án'],
  'Method Selected':   ['Bắt đầu thương thảo'],
  'Negotiation':       ['Đề xuất trúng thầu'],
  'Award Recommended': ['Trình BGĐ'],
  // ❌ Missing 'Contract Signed': ['Phát hành PO']
}

// ✅ ĐÚNG — đếm states từ workflow.json, map đủ
// python3 -c "import json; d=json.load(open('workflow.json')); print(len(d['states']))"
```

**Quy tắc**: map phải có entry cho mọi state có outgoing transition. Test bằng cách traverse full lifecycle qua UI — nếu kẹt ở state nào → bug.

### LL-FE-2: Workflow action labels phải khớp BE EXACT (tiếng Việt có dấu)

Bug: FE gọi `"Trình Ban Giám đốc"` (đầy đủ) nhưng workflow JSON định nghĩa `"Trình BGĐ"` (viết tắt) → 422 `Not a valid Workflow Action`.

**Quy tắc**: import constant từ `@/utils/wave2Labels` hoặc shared module, không hardcode string. Sau khi BE tạo workflow JSON, FE phải đồng bộ ngay.

### LL-FE-3: StatusBadge label/color phải đồng bộ với BE state machine

Bug: BE `workflow_state = "Submitted"`, FE formatter map `Submitted → "Đã duyệt"` (xanh) → user thấy "Đã duyệt" khi thực ra mới submit.

**Quy tắc**: trong `formatters.ts` mỗi BE state có entry trong `STATUS_LABEL` (label đúng nghĩa) và `STATUS_COLOR`. Khi BE thêm state mới → update FE formatter cùng commit.

### LL-FE-4: List page TỐI THIỂU phải có nút tạo mới

Bug: `/procurement-plans` chỉ có filter, không có nút "+ Tạo" → user không tạo được plan qua UI.

**Quy tắc** (DoD cho List page): mỗi list page (trừ trang view-only) phải có:
- Nút "+ Tạo mới" trong `PageHeader #actions` slot
- Modal hoặc navigate đến `/create` view
- Sau khi tạo: navigate đến detail của record mới

### LL-FE-5: Detail page phải có ĐẦY ĐỦ workflow buttons theo state

Bug: PP detail chỉ có nút "Đưa NR vào kế hoạch" cho state Draft, thiếu "Phê duyệt"/"Kích hoạt"/"Đóng" cho các state khác.

**Quy tắc**: count workflow states, count UI buttons. Mỗi state phải có ít nhất 1 button cho transition tiếp theo (trừ terminal states).

### LL-FE-6: Hiển thị display name, không hiển thị code/email

Bug recurring: subtitle hiển thị `AC-DEPT-0101` thay vì `Khoa Tim mạch can thiệp`. Field `requesting_department` là Link, FE phải đọc `requesting_department_name` (BE đã enrich).

**Bug 2026-05-27** (IMM-06 CompetencyListView): `c.device_model` render `IMM-MDL-2026-0023` thay vì "Dräger Evita V500" — BE quên enrich + FE quên fallback. Fix yêu cầu cả 2 phía (xem CONVENTIONS §37 + §38).

```vue
<!-- ❌ SAI -->
<p>{{ doc.requesting_department }}</p>
<td>{{ c.device_model }}</td>

<!-- ✅ ĐÚNG — `??` (không `||`), giữ ID gốc làm tooltip -->
<p :title="doc.requesting_department">{{ doc.requesting_department_name ?? doc.requesting_department ?? '—' }}</p>
<td :title="c.device_model">{{ c.device_model_name ?? c.device_model }}</td>
```

`??` (nullish coalescing) thay vì `||` — đề phòng giá trị falsy hợp lệ (vd `""` từ BE) bị fallback nhầm.

**Quy tắc**:
1. Snapshot Playwright → grep tìm `AC-*`, `IMM-*`, `email@...` — nơi nào không phải là link/ID thuần thì bug.
2. Chạy CONVENTIONS §0 GATE-2 grep trước khi mark Done — bắt mọi biến (`row`, `item`, `doc`, `c`, `r`, `x`) reference Link field thiếu `_name`.
3. Nếu BE chưa enrich `<field>_name`, FE KHÔNG được hardcode lookup ở FE — sửa BE (xem `assetcore-be` LL-BE-2 + CONVENTIONS §37) rồi FE mới render.

### LL-FE-7: Frappe child table — KHÔNG hiển thị `row.name`

Bug: `plan_items` hiển thị `5mvh1o4qsa` (Frappe auto-name) thay vì `NR-26-05-00010`.

```vue
<!-- ❌ SAI -->
<td>{{ item.name }}</td>

<!-- ✅ ĐÚNG — đọc Link field gốc -->
<td>{{ item.needs_request || '—' }}</td>
```

**Quy tắc**: `row.name` của child table là internal ID — không bao giờ show cho user.

### LL-FE-8: Form Select options phải match BE DocType JSON

Bug: FE form cho free-text `funding_source` nhưng BE DocType định nghĩa `Select` với options cố định → save fail với `Invalid Value`.

```bash
# Verify DocType options trước khi build form
python3 -c "import json; d=json.load(open('<doctype>.json')); \
  [print(f['fieldname'], '=', repr(f['options'])) for f in d['fields'] if f['fieldtype']=='Select']"
```

**Quy tắc**: dùng constant module shared cho enum/select options (FE + BE đọc cùng nguồn).

### LL-FE-9: Link field input phải dropdown, không free text

Bug pattern: form (Create/Edit/Modal) dùng `<input type="text">` cho field mà DocType khai báo `"fieldtype": "Link"`. User phải gõ ID hệ thống (vd: "IMM-MDL-2026-00012") → không thực dụng + dễ sai → save fail "Could not find Row…" hoặc lưu chuỗi rác qua kiểm tra Frappe.

**Real incidents:**

- 2026-05 Vendor Evaluation: `supplier` text → "Philips Healthcare" → BE reject
- 2026-05-27 IMM-06 Program form: `target_device_model` + `target_device_category` đều Link nhưng FE render `<input type="text">` → user không chọn được, phải copy-paste ID

**Quy tắc (BẮT BUỘC trước khi viết hoặc sửa form):**

1. **Pre-check**: mở DocType JSON, list mọi field Link:

   ```bash
   grep -B1 -A3 '"Link"' assetcore/assetcore/doctype/<dt>/<dt>.json
   ```

2. **Component bắt buộc**: `<SmartSelect v-model="form.field" doctype="<TargetDocType>" placeholder="Chọn..." />`.
   - Nếu target DocType chưa có trong `DocType` union ở `components/common/SmartSelect.vue` → mở rộng union + thêm loader trong `stores/masterData.ts`. KHÔNG fallback `<input type="text">` vì "tạm chưa support".

3. **Loại trừ hợp lệ** (vẫn dùng `<input>`):
   - Field `Data` / `Small Text` (free text user-entered)
   - Field `Link` đến DocType nhỏ-lẻ chỉ dùng 1 chỗ (vd: `qms_doc_ref` → Asset Document): tạm chấp nhận text với hint `<p class="text-xs">Mã ...</p>` mô tả format, NHƯNG phải log gap để chuyển SmartSelect sau

4. **Self-check command** trước khi đóng task:

   ```bash
   grep -E "<input.*v-model=\"form\.(target_|supplier|department|location|asset|model|category|user|custodian|responsible)" frontend/src/views/<module>/*.vue
   ```

   Mỗi match → đối chiếu DocType JSON; nếu là Link → đổi sang SmartSelect.

5. **Data PK field (naming-series)**: nếu field là PK (vd `program_code` với `"autoname": "field:program_code"`), giữ `<input>` nhưng:
   - `:readonly="!isCreateMode"` (không cho đổi sau khi tạo)
   - Có placeholder + helper `<p class="text-xs">` mô tả format gợi ý
   - BE đã validate uniqueness (Frappe duplicate constraint)

Không tuân thủ là blocker FE-DoD — `assetcore-audit` Pillar 6 flag 🟠 HIGH.

### LL-FE-10: TRANSITIONS map phải cover ALL workflow states (bao gồm Draft)

Bug: 2026-05-27 imported asset ở Draft không có nút chuyển trạng thái — `AssetDetailView.vue` có `TRANSITIONS` map nhưng thiếu entry `'Draft': [...]`. Trước đó luồng create_asset auto-transition về Active nên không ai gặp Draft trong UI. Khi feature import được thêm, asset bắt đầu xuất hiện ở Draft → user kẹt.

**Quy tắc:**

1. Mở workflow JSON: `assetcore/assetcore/workflow/<workflow>.json`
2. Đếm `states` (trừ terminal):

   ```bash
   python3 -c "import json; d=json.load(open('<path>.json')); print([s['state'] for s in d['states']])"
   ```

3. Cho mỗi non-terminal state, FE DetailView phải có entry trong `TRANSITIONS: Record<string, Status[]>` với danh sách target states tương ứng `_VALID_TRANSITIONS` ở `services/<module>.py`
4. **Đặc biệt: state khởi tạo** (vd `Draft`, `Open`, `Planned`) — DỄ BỊ QUÊN vì luồng create thường skip qua state này. Phải check explicit.
5. Self-check:

   ```bash
   states_be=$(grep -E "^\s+_STATUS_\w+\s*=" assetcore/services/<module>.py | wc -l)
   states_fe=$(grep -cE "'\w[\w ]*':\s*\[" frontend/src/views/<domain>/<X>DetailView.vue)
   # states_fe phải >= (states_be - số terminal states)
   ```

### LL-FE-11: TypeScript union types phải sync BE constants

Bug: `LifecycleStatus` union ở `types/imm00.ts` thiếu `'Draft'` và `'Under Maintenance'` — TS compile vẫn pass vì cast as any/never check exhaustive. Khi thêm Draft vào TRANSITIONS map, TypeScript phải compile được mà không cần workaround.

**Quy tắc:**

1. Cho mỗi enum/status field, source-of-truth là `_STATUS_*` constants ở `services/<module>.py`
2. FE TypeScript union ở `types/<module>.ts` phải có TẤT CẢ state values, kể cả terminal/initial
3. Workflow JSON là cross-check thứ 2:

   ```bash
   # BE states
   python3 -c "import json; d=json.load(open('<wf>.json')); [print(s['state']) for s in d['states']]"
   # FE union
   grep -A5 "export type \w*Status" frontend/src/types/<module>.ts
   ```

4. Mismatch → strengthen union; không cast `as any` để bypass

### LL-FE-12: Role gating CHỈ dùng useCapabilities, không hasAnyRole(ROLES_*)

Bug: 2026-05-27 IMM-06 Program/Session list ẩn nút "Tạo mới" → root cause `ROLES_TRAINING_MANAGE = _empty` (`constants/roles.ts:104,129`). Các hằng số `ROLES_*` đã được deprecate thành `[]` từ wave RBAC redesign nhưng 3 view vẫn import & dùng → `hasAnyRole([])` luôn false.

**Quy tắc (BẮT BUỘC mọi view có gate UI):**

1. **CẤM** import `ROLES_*` từ `@/constants/roles` cho logic gate:

   ```bash
   grep -rn "ROLES_\w\+" frontend/src/views/ | grep -v ROLE_CATALOG
   # phải = 0 ngoài file admin/role-picker
   ```

2. **Dùng**: `const { can } = useCapabilities()` + `can('<domain>.<ptype>')`. Capability strings:
   - `<domain>.<ptype>` với ptype ∈ {read, write, create, delete, submit, cancel}
   - Domain enum: data, needs, spec, procurement, commissioning, document, training, pm, repair, calibration, corrective, inventory, compliance
   - Special: `pm.reschedule`, `incident.acknowledge`, `incident.close`, `cal.send_lab`, `doc.approve`, `capa.close`, `data.admin`, `audit.read`

3. **Mapping BE → FE capability** (cùng nguồn `services/shared/rbac.py::CAPABILITY_MAP`):
   - BE `rbac.require("training.write")` → FE `can('training.write')`
   - BE `rbac.require("incident.close")` → FE `can('incident.close')`
   - Phải khớp EXACT — không đặt tên thân thiện ở FE

4. **Self-check command**:

   ```bash
   grep -rn "hasAnyRole\|ROLES_TRAINING\|ROLES_PM\|ROLES_CM\|ROLES_CAL\|ROLES_INCIDENT\|ROLES_DOC\|ROLES_COMPLIANCE\|ROLES_STOCK\|ROLES_PLANNING\|ROLES_PROCUREMENT" frontend/src/views/
   # Mỗi match là 1 bug — đổi sang can('xxx')
   ```

### LL-FE-13: List page phải có hành động khả thi (KHÔNG dead-end UX)

Bug: 2026-05-27 IMM-06 `/competencies` list không có button nào ngoài filter — competency được sinh auto từ session nên không có create endpoint. User vào trang trống → không biết làm gì.

**Quy tắc:**

1. Mọi list page PHẢI có ít nhất 1 trong các hành động:
   - **Create button** (đa số case — gate qua capability)
   - **Navigate button** đến nơi tạo bản ghi (case auto-generated như Competency → "Buổi đào tạo")
   - **Bulk action** (Import / Export / Assign)

2. **Empty state phải actionable**: ngoài text "Chưa có dữ liệu", phải có ít nhất 1 button + 1 dòng giải thích cách tạo:

   ```html
   <div v-else-if="!items.length">
     <p>Chưa có ...</p>
     <p class="text-xs">{{ how_to_create_hint }}</p>
     <button @click="navigateToCreate">+ Tạo / Đi tới ...</button>
   </div>
   ```

3. **Process hint banner** (cho list auto-generated): banner xanh ở đầu trang giải thích "X được sinh tự động khi Y → đi tới Y để bắt đầu" (ví dụ: `CompetencyListView.vue:131-143`)

4. Self-check:

   ```bash
   # List view không có button create/navigate/import → flag
   for f in frontend/src/views/**/[A-Z]*ListView.vue; do
     grep -L "btn-primary\|@click=\"router.push\|@click=\"openImport" "$f" && echo "GAP: $f"
   done
   ```

### LL-FE-14: Cấm `window.confirm()` / `alert()` — dùng `BaseModal`

Bug: 2026-05-16 IMM-11 Calibration submit dùng native `confirm()` còn modules khác dùng styled modal → UX inconsistent + native dialog không brand được + không support Vietnamese formatting đẹp.

**Quy tắc:**

1. Mọi destructive/confirm action dùng `<BaseModal>` từ `components/common/BaseModal.vue`
2. Cấm `window.confirm()`, `alert()`, `prompt()` trong `frontend/src/views/**`:

   ```bash
   grep -rn "window\.confirm\|\bconfirm(\|\balert(\|\bprompt(" frontend/src/views/
   # = 0 match
   ```

3. Pattern cho confirm modal: `<BaseModal v-model="showConfirm" title="..." @confirm="doAction">...</BaseModal>` + button trigger `@click="showConfirm = true"`
4. Pattern cho destructive: thêm warning banner đỏ + require typed confirmation (vd "Nhập DELETE để xác nhận") cho action không thể hoàn tác

### LL-FE-15: Rich-text field phải render HTML qua `sanitizeHtml`, không raw text

Bug: 2026-05-16 IMM-12 Incident "Mô tả sự cố" hiển thị `<p>Bệnh nhân...</p><b>nguy cấp</b>` dưới dạng text → user thấy raw HTML markup thay vì văn bản format.

**Quy tắc:**

1. Field DocType `Text Editor` / `HTML` / `Long Text` (chứa markup) phải render qua `v-html` + sanitize:

   ```vue
   <script>import { sanitizeHtml } from '@/utils/sanitizeHtml'</script>
   <div v-html="sanitizeHtml(doc.description)" class="prose prose-sm"></div>
   ```

2. **CẤM `{{ doc.description }}`** cho rich-text — sẽ escape HTML thành text raw
3. **CẤM `v-html="doc.description"` trần** — XSS risk (NEG-06)
4. Mọi `v-html` phải qua `sanitizeHtml()` (file `frontend/src/utils/sanitizeHtml.ts` whitelist `<p><b><i><ul><ol><li><br><a><strong><em>` + strip script/iframe/on*)
5. Self-check:

   ```bash
   grep -rn 'v-html=' frontend/src/views/ | grep -v sanitizeHtml
   # = 0 match
   ```

### LL-FE-16: Destructive button (Xóa) chỉ render ở Draft state

Bug: 2026-05-16 IMM-12 Incident "Critical" ở state "Đang điều tra" vẫn show button "Xóa" → user có thể xóa cứng evidence giữa luồng investigation → audit trail bị mất.

**Quy tắc:**

1. Button "Xóa" / Delete chỉ hiện khi:
   - State = Draft / Open (chưa submit) **VÀ**
   - `canDelete` capability gate **VÀ**
   - Không có child record dependency
2. Sau khi rời Draft, dùng "Hủy" (cancel/void) hoặc "Đóng" (close) — KHÔNG delete:

   ```vue
   <!-- ❌ SAI -->
   <button v-if="canDelete" @click="doDelete">Xóa</button>

   <!-- ✅ ĐÚNG -->
   <button v-if="canDelete && doc.workflow_state === 'Draft'" @click="doDelete">Xóa</button>
   <button v-else-if="canCancel && !isTerminalState(doc.workflow_state)" @click="doCancel">Hủy</button>
   ```

3. BE backup gate: `services/<module>.py:delete_xxx()` phải `require state == "Draft"` — không tin FE
4. Self-check:

   ```bash
   grep -B2 'doDelete\|deleteDoc' frontend/src/views/**/*DetailView.vue | grep -v "workflow_state === 'Draft'\|state === 'Open'"
   # mỗi match là 1 gap
   ```

### LL-FE-17: Dashboard KPI phải dùng cùng query/source với list view

Bug: 2026-05-16 IMM-15 Dashboard "Cảnh báo tồn thấp: 0" nhưng `/stock` list hiển thị 5 bins đang low-stock — root cause: dashboard KPI tính total across warehouses (sum ≥ threshold) thay vì per-bin check.

**Quy tắc:**

1. KPI service function phải dùng cùng predicate với list filter:

   ```python
   # ❌ SAI: aggregate trước, check threshold sau
   total = sum(b.qty for b in bins)
   low_count = 1 if total < threshold else 0

   # ✅ ĐÚNG: check per-row giống list
   low_count = sum(1 for b in bins if b.qty < b.min_threshold)
   ```

2. FE Dashboard widget click → navigate đến list page với filter pre-applied, expected count = KPI number
3. Acceptance test: KPI count ở dashboard PHẢI khớp số dòng ở list khi apply cùng filter

### LL-FE-18: Mọi BE service user-initiated phải có UI button trigger

Bug: 2026-05-16 IMM-16 Compliance: `compliance.run_scan()` + `generate_scorecard()` chỉ có scheduler/seed gọi → FE không có button "Chạy quét tuân thủ" → user không thể trigger thủ công → findings/scorecards rỗng ngoài lịch chạy.

**Quy tắc:**

1. Mọi service function trong `services/<module>.py` có ý nghĩa "user-initiated" (run_*, generate_*, scan_*, trigger_*, recalculate_*) phải có:
   - API endpoint trong `api/<module>.py`
   - UI button ở list/dashboard view tương ứng (gate qua capability)
2. Scheduler + seed là FALLBACK, không substitute UI trigger
3. Tự check: với mỗi `@frappe.whitelist()` POST endpoint, grep FE views có call:

   ```bash
   grep -rn "<endpoint_name>" frontend/src/api/<module>.ts frontend/src/views/<domain>/
   # phải >= 1 match
   ```

### LL-FE-19: Test data không được leak vào production UI

Bug: 2026-05-26 IMM-06 production list hiển thị `_TEST-PROG-IMM06-SHARED`, `_Test Program IMM06 Shared`, `_Test Category`; IMM-16 hiển thị `TEST-R-IMM08-PM-90`, `_Test Asset IMM08-wo`, "Test effectiveness". Test rollback fail ở một point — orphan test records còn lại.

**Quy tắc (cả BE test + FE display):**

1. **Naming convention TEST data**: tất cả test fixtures phải có prefix DỄ GREP để cleanup safe:
   - `_Test*` (underscore prefix, Vietnamese name)
   - `_TEST-*` (uppercase với dash)
   - `TEST-*` (uppercase prefix cho code)
2. **Test teardown**: dùng `frappe.delete_doc(force=True, ignore_permissions=True)` — không rely on `tearDownClass` rollback:

   ```python
   @classmethod
   def tearDownClass(cls):
       for name in cls._created_docs:
           try:
               frappe.delete_doc(cls._doctype, name, force=True, ignore_permissions=True)
           except Exception:
               pass
       super().tearDownClass()
   ```

3. **Pre-release sanity check**:

   ```bash
   # SQL grep tất cả test records leak vào production tables
   bench --site miyano mariadb -e "
     SELECT name FROM \`tabIMM Training Program\` WHERE name LIKE '\\_Test%' OR name LIKE 'TEST-%';
     SELECT name FROM \`tabAC Asset\` WHERE name LIKE '\\_Test%' OR asset_name LIKE '\\_Test%';
     -- ...repeat cho mọi DocType operational
   "
   ```

4. **FE defensive filter** (tạm thời, không substitute fix BE): list view filter ra `name.startsWith('_Test')`:

   ```typescript
   const filtered = items.value.filter(x => !x.name?.startsWith('_Test') && !x.name?.startsWith('TEST-'))
   ```

5. **Audit checkpoint**: trước khi tag release, chạy SQL grep ở (3); kết quả phải = 0.

### LL-FE-20: Computed field (qty × price) phải render — không để "—"

Bug: 2026-05-16 IMM-15 stock-movement detail line "Thành tiền" hiển thị "—" (qty × price không tính); footer total đúng. Detail row computed column bị bỏ trống vì FE không tính client-side và BE không trả field.

**Quy tắc:**

1. Field computed (vd `line_total = qty * price`, `days_until_expiry = expiry_date - today`) phải:
   - Tính ở BE service rồi trả về `_computed` companion field, HOẶC
   - Tính ở FE qua `computed()` từ source fields
2. KHÔNG render "—" / null cho field có thể compute từ data sẵn có:

   ```vue
   <!-- ❌ SAI -->
   <td>{{ line.line_total ?? '—' }}</td>

   <!-- ✅ ĐÚNG -->
   <td>{{ formatVND((line.qty ?? 0) * (line.price ?? 0)) }}</td>
   ```

3. Self-check: footer total ≠ 0 nhưng row "—" → bug (data có nhưng FE không render)

### LL-FE-21: `STATUS_MAP` + `STATUS_COLOR` ở `utils/formatters.ts` là single source of truth

Bug session 2026-05-26: FE hiển thị "Locked", "Evaluated", "Contract Signed" English vì 11 workflow states Wave-2 KHÔNG có entry trong `STATUS_MAP`. `StatusBadge.vue` fallback `STATUS_MAP[status] ?? status` → English literal.

**Quy tắc khi thêm workflow state mới ở BE:**

1. Mọi state trong `workflow.json` BẮT BUỘC có entry trong CẢ 2 map ở `frontend/src/utils/formatters.ts`:
   - `STATUS_MAP` (label tiếng Việt)
   - `STATUS_COLOR` (1 trong 6: COLOR_GREEN/BLUE/YELLOW/ORANGE/RED/PURPLE/GRAY)

2. Audit script trước khi tag release:
   ```bash
   # Dump all states từ workflow JSON files:
   for wf in assetcore/assetcore/workflow/*.json; do
     python3 -c "import json; d=json.load(open('$wf')); [print(s['state']) for s in d['states']]"
   done | sort -u > /tmp/be_states.txt
   # Dump all keys trong STATUS_MAP:
   grep -oE "^\s+'[A-Z][^']*':" frontend/src/utils/formatters.ts | sed "s/.*'\([^']*\)'.*/\1/" | sort -u > /tmp/fe_labels.txt
   # Diff:
   comm -23 /tmp/be_states.txt /tmp/fe_labels.txt
   # Output không rỗng → có state thiếu label → bug.
   ```

3. **KHÔNG dùng local `XXX_LABELS` map trùng lặp** trừ khi key thuộc namespace khác (vd: frequency, severity-only) — dùng STATUS_MAP làm primary, dùng local map cho enum không phải workflow state (vd `FREQUENCY_LABELS = { Daily, Weekly, ... }`).

4. Cross-reference: `wave2Labels.ts:stateLabel()` ĐÃ có labels nhưng `StatusBadge.vue` dùng `formatters.ts:translateStatus()` → CHỌN MỘT map. Hiện `formatters.ts` là canonical.

### LL-FE-22: BE thêm Link field mới → FE detail/list PHẢI render `_name` companion

Bug session 2026-05-26: BE commit 83884c8 wire `linked_incident` / `source_type` / `source_ref` cho `IMM CAPA Record`, nhưng FE `CAPADetailView.vue` chỉ render `finding_ref` cũ → linked incident invisible.

**Quy tắc:**

1. Khi BE commit thêm Link field mới trên DocType + enrich `<field>_name` trong service:
   - FE phải thêm vào TypeScript type (`api/<module>.ts`)
   - Detail view phải thêm section render với fallback `(x as any).foo_name || x.foo`
   - List view (nếu cột hiển thị) phải dùng `_name` ưu tiên
2. Pattern chuẩn rendering Link với fallback navigate:
   ```vue
   <div v-if="capa.incident_ref">
     <p class="t-eyebrow">Sự cố nguồn</p>
     <button class="font-mono text-brand-700 hover:underline"
             @click="router.push(`/incidents/${capa.incident_ref}`)">
       {{ capa.incident_ref }}
     </button>
     <span v-if="capa.incident_subject" class="text-xs text-slate-500 ml-2">
       — {{ capa.incident_subject }}
     </span>
   </div>
   ```
3. Cross-check: sau BE merge, grep FE detail view có reference đến field mới không. Nếu không → gap, mở FE follow-up.

### LL-FE-23: Cell `'—'` khi data có nghĩa null vs khi data CÓ nhưng FE không render

Bug session 2026-05-26: IMM-03 Decisions list cột "Đơn hàng đã mint" hiển thị `AC-PUR-2026-00011` (raw code). BE enrich `ac_purchase_ref_name` nhưng FE template không dùng → user thấy code, không thấy tên.

**Quy tắc cell render Link field:**

```vue
<!-- ❌ SAI: chỉ raw value -->
<td>{{ d.ac_purchase_ref || '—' }}</td>

<!-- ✅ ĐÚNG: prefer _name, fallback raw (raw vẫn meaningful nếu doc name là PO code chính nó) -->
<td>{{ (d as any).ac_purchase_ref_name || d.ac_purchase_ref || '—' }}</td>
```

Khi `_name` là `null` (field display ở DB chưa populate), fallback về `d.ac_purchase_ref` (doc name) là ACCEPTABLE — user vẫn thấy identifier. Backfill data quality là backlog, không phải FE bug.

### LL-FE-24: Vue `(x as any)` cast pattern khi BE enrich field chưa có trong TS type

Tạm thời (trước khi update type): dùng `(x as any).foo_name || x.foo`. Đừng cast cả `(x as any)` cho thân lớn — chỉ inline để type-check không fail.

Lý tưởng: sau khi BE merge, update `api/<module>.ts` interface:
```typescript
export interface CapaDetail extends CapaRecord {
  incident_ref?: string
  incident_subject?: string
  linked_incident?: string | null
}
```
Sau đó remove `as any` cast.

### LL-FE-21: Sidebar / module-context detection PHẢI synchronous từ URL — không chờ `afterEach`

Bug 2026-05-26 (BUG-003): Deep-link `/pm/schedules` → sidebar hiển thị "Trang này không thuộc module nào. Mở Launcher để chọn module." trong 2–3s, action button bị disabled trong khoảng đó. Root cause: `currentModule` chỉ set bởi `router.afterEach` guard → guard chạy SAU first paint.

**Quy tắc:**

1. **`router.isReady()` await trước `app.mount()`** — đảm bảo first paint đã có `route.meta.moduleId`:
   ```ts
   // main.ts
   import { router } from './router'
   const app = createApp(App)
   app.use(router)
   await router.isReady()      // ← bắt buộc
   app.mount('#app')
   ```
2. **Sidebar fallback URL-based, đồng bộ**: extract `resolveModuleId(pathname)` từ router's regex table, export, để sidebar dùng làm fallback khi `route.meta.moduleId` chưa hydrate:
   ```ts
   // router/index.ts
   export function resolveModuleId(path: string): string | undefined {
     for (const [regex, mod] of MODULE_RULES) if (regex.test(path)) return mod
   }
   // AppSidebar.vue
   const currentModuleId = computed(
     () => route.meta.moduleId || resolveModuleId(route.path)
   )
   ```
3. **Action buttons KHÔNG được phụ thuộc `currentModule` hydration** — gate qua `useCapabilities().can('xxx')` thay vì `!!currentModule`.
4. Self-check: thử reload trang ở mọi sub-route — sidebar phải hiển thị module đúng ngay tức thì.
5. Reference: `frontend/src/router/index.ts:resolveModuleId`, `components/common/AppSidebar.vue`, `main.ts:isReady`.

### LL-FE-22: Empty `ROLES_*` stub arrays = silent permission denial

Bug 2026-05-26 (BUG-006/007/011): Calibration "Bắt đầu" + Training "Thêm học viên" + Competency "Nhập điểm" — buttons exist nhưng không render vì gate `auth.hasAnyRole(ROLES_CAL_EXECUTE)` evaluated false. Root cause: `ROLES_CAL_EXECUTE` (và các array khác) được giữ là `[]` trong `frontend/src/constants/roles.ts` như legacy stub — không có role nào pass.

**Quy tắc:**

1. **Empty `ROLES_*` array TRONG roles.ts = bug**. Hoặc fill role names đúng, hoặc xóa hẳn const và migrate caller sang `can('<cap>')`.
2. **Forbidden**: `auth.hasAnyRole(ROLES_*)` cho gating workflow buttons. Required: `useCapabilities().can('<domain>.<ptype>')` — đã sync với BE `rbac.require()`.
3. **Audit trigger**: nếu thấy `ROLES_*` empty `[]` ở roles.ts → grep usage, migrate hết:
   ```bash
   grep -E "^export const ROLES_\w+\s*=\s*\[\s*\]" frontend/src/constants/roles.ts
   # Mỗi empty const → grep usage để migrate
   grep -rn "ROLES_CAL_EXECUTE\|ROLES_TRAINING_MANAGE" frontend/src/
   ```
4. CONVENTIONS §11 đã forbid `hasAnyRole(ROLES_*)` — empty arrays là FE-side violation chính của rule này.
5. Reference: `composables/useCapabilities.ts`, `services/shared/rbac.CAPABILITY_MAP`.

### LL-FE-23: Khi action không render do permission, PHẢI show explicit hint — không silent empty panel

Bug 2026-05-26 (BUG-006/007): User mở Calibration "Đã lên lịch" + Training "Đã lập kế hoạch" → action panel hoàn toàn trống. User kết luận "tính năng vỡ" → ghi vào regression report. Thực tế chỉ là role thiếu.

**Quy tắc:**

1. Mỗi action panel phải có fallback hint khi tất cả buttons bị gate ra:
   ```vue
   <div v-if="canAnyAction" class="flex gap-2">
     <button v-if="canStart" @click="doStart">Bắt đầu</button>
     <button v-if="canCancel" @click="doCancel">Hủy</button>
   </div>
   <div v-else-if="isNonTerminal" class="alert-amber text-xs">
     Bạn không có quyền thực hiện hành động trên phiếu này.
     Liên hệ quản trị để cấp role <b>Calibration User/Manager</b>.
   </div>
   ```
2. Hint chỉ render khi state non-terminal (terminal state không có action nào là expected).
3. Có thể nâng cấp: hiển thị tên role/capability cần có (UX bonus).
4. Self-check khi audit: navigate đến mỗi DetailView ở từng state, KHÔNG có panel nào empty mà không có giải thích.
5. Reference: `views/calibration/CalibrationDetailView.vue` (showPermissionHint), `views/training/SessionDetailView.vue`.

### LL-FE-24: DocType cross-reference — copy đúng string, không gõ lại

Bug 2026-05-26 (BUG-019 — BE-side nhưng FE cũng dính): Một file dùng `"AC Department"` 3 lần đúng + 1 lần `"Department"` sai → crash. Pattern này gặp ở FE qua type strings, API call paths, store action names.

**Quy tắc (FE-side):**

1. **Copy-paste DocType string từ existing usage** trong file thay vì gõ lại từ trí nhớ.
2. **Self-check khi thêm `frappeGet`/`frappePost`** với hardcoded path: verify path khớp `assetcore/api/<module>.<func>` thực tế:
   ```bash
   # Endpoint path FE
   grep -oE "assetcore\.api\.\w+\.\w+" frontend/src/api/immXX.ts | sort -u
   # Function names BE
   grep -E "^def \w+" assetcore/api/immXX.py
   ```
3. Reference: BE-side LL-BE-10.

### LL-FE-25: Dual-display Link field — name primary + code subtitle là pattern chuẩn

Pattern chuẩn 2026-05-26 (verified `AssetDetailView.vue:306-323`): trường Link hiển thị 2 dòng — dòng 1 display name (text-base), dòng 2 raw code (text-xs slate-400 subtitle, chỉ hiện khi cả 2 đều có).

```vue
<dt class="text-slate-400 shrink-0">Nhà cung cấp</dt>
<dd>
  <div>{{ doc.supplier_name || doc.supplier || '—' }}</div>
  <div v-if="doc.supplier && doc.supplier_name"
       class="text-xs text-slate-400">{{ doc.supplier }}</div>
</dd>
```

**Quy tắc**:
- Dòng 1 (primary): luôn `*_name || *` — name có ưu tiên, fallback code, fallback `—`
- Dòng 2 (subtitle): CHỈ hiển thị khi BOTH name + code có giá trị
- KHÔNG xóa subtitle để "clean UI" — operations team cần code để query trong Frappe Desk
- Khi audit bằng Playwright `browser_evaluate`: probe theo label+valueGroup, không chỉ leaf-text (xem `assetcore-test` LL-TEST-13). False positive "code leak" thường vì leaf-probe chỉ bắt subtitle.

### LL-FE-26: Role-gated action panel — bắt buộc empty-state hint cho user không quyền

Bug session 2026-05-26: `CalibrationDetailView.vue` state "Đã lên lịch" không hiện button nào cho user role thấp (Chu Hiếu thiếu CAL_EXECUTE). Workflow JSON có 3 transitions; FE wire đúng; nhưng UI dead-end.

```vue
<!-- ❌ SAI — silent empty panel khi user thiếu role -->
<div class="actions">
  <button v-if="canExecuteCal">Bắt đầu hiệu chuẩn</button>
  <button v-if="canManageCal">Hủy phiếu</button>
</div>

<!-- ✅ ĐÚNG — empty-state hint khi không button nào render -->
<div class="actions">
  <button v-if="canExecuteCal">Bắt đầu hiệu chuẩn</button>
  <button v-if="canManageCal">Hủy phiếu</button>
  <div v-if="!canExecuteCal && !canManageCal && !isTerminal"
       class="text-sm text-slate-500 italic">
    Không có hành động khả dụng cho vai trò hiện tại.
    Liên hệ {{ ROLE_OWNER_HINT[currentStateGroup] || 'quản trị viên' }} để xử lý.
  </div>
</div>
```

**Quy tắc** (cross-ref [[LL-FE-23]]):
- Mọi DetailView panel có 2+ buttons gate bằng `v-if="canXxx"` PHẢI có hint khi tất cả ẩn
- Hint: (1) tại sao ẩn, (2) role nào có thể, (3) action — "Liên hệ KTV"
- Terminal states (Completed/Cancelled/Closed) miễn hint — đặt cờ `isTerminal` để loại
- Audit grep:
  ```bash
  for f in frontend/src/views/**/*DetailView.vue; do
    btns=$(grep -c 'v-if="can' "$f")
    hint=$(grep -c 'Không có hành động khả dụng\|Bạn không có quyền' "$f")
    [ "$btns" -ge 2 ] && [ "$hint" -eq 0 ] && echo "MISSING HINT: $f ($btns gated buttons)"
  done
  ```

### LL-FE-27: Nghi ngờ "FE thiếu enrich" — chạy `bench execute` xem response TRƯỚC khi sửa FE

Bug 2026-05-26 (FP avoidance): UI hiển thị raw code → reflex sửa FE thêm `*_name || *`. Thực tế BE đã enrich, FE template đã đúng, chỉ là DOM probe sai layer.

**Diagnostic procedure TRƯỚC khi đụng FE**:
```bash
# 1. Check BE service trả gì
bench --site miyano execute assetcore.api.imm00.get_asset --kwargs '{"name":"AC-ASSET-2026-00407"}' \
  | grep -oE '"supplier_name":[^,]*|"location_name":[^,]*'

# 2. Nếu BE trả đúng → check FE store có overwrite không
grep -n "currentAsset\|setAsset" frontend/src/stores/<module>.ts

# 3. Nếu store OK → check template binding
grep -n "supplier\|location" frontend/src/views/<domain>/<X>DetailView.vue

# 4. Nếu cả 3 layer đúng → cache stale (TanStack Query) hoặc DOM probe sai (xem LL-TEST-13)
```

### LL-FE-28: Audit Trail Tab — mọi DetailView nghiệp vụ PHẢI có (2026-05-27)

**Bug RC-05:** Phiếu nghiệm thu (ACC) tab "Lịch sử phiếu" trống dù BE đã log `IMM Audit Trail`. Nguyên nhân: FE detail view không render tab Lịch sử, hoặc render nhưng query sai filter.

**Quy tắc:**

1. Mọi `XxxDetailView.vue` của DocType nghiệp vụ PHẢI có tab "Lịch sử phiếu" (hoặc "Lịch sử thay đổi"):
   ```vue
   <Tabs>
     <Tab id="info">Thông tin</Tab>
     <Tab id="workflow">Quy trình</Tab>
     <Tab id="history">Lịch sử phiếu</Tab>
   </Tabs>

   <TabPanel id="history">
     <AuditTrailTab :doctype="DOCTYPE" :name="doc.name" />
   </TabPanel>
   ```

2. **Component canonical**: `<AuditTrailTab>` ở `components/common/AuditTrailTab.vue`. Nếu chưa tồn tại, tạo trong PR đầu tiên touching nhiều DetailView. Component bắt buộc:
   - Merged timeline (lifecycle events + audit trail + workflow transitions)
   - Sort timestamp desc
   - Mỗi row: actor + action + timestamp + change_summary
   - Click vào row → expand JSON diff (nếu có)

3. **API endpoint chuẩn**: `assetcore.api.audit.list_for_doc(doctype, name)` → response merged + sorted.

4. **Empty state actionable**: nếu timeline trống → text + warning:
   ```vue
   <div v-if="!events.length" class="text-center py-8">
     <p class="text-gray-500">Chưa có sự kiện được ghi nhận</p>
     <p class="text-xs text-amber-600 mt-2">
       ⚠️ Nếu phiếu đã có nhiều thao tác mà ô này trống — báo dev (BE có thể chưa log).
     </p>
   </div>
   ```
   Empty silent = bug ẩn (hook chain BE thiếu — xem LL-BE-23).

5. **Self-check trước khi đóng task DetailView**:
   ```bash
   for f in frontend/src/views/**/[A-Z]*DetailView.vue; do
     grep -L "AuditTrailTab\|Lịch sử" "$f" && echo "GAP: $f"
   done
   ```

Reference: `CONVENTIONS.md §42`, `assetcore-be` LL-BE-23 (hook chain), `assetcore-audit` Pillar 5 + Pillar 9.

### LL-FE-29: KPI Scope Disambiguation — label phải nêu rõ phạm vi (2026-05-27)

**Bug RC-09, RC-10:** `/dashboard` báo "Phiếu chờ duyệt: 3" trong khi `/approvals/pending` báo "0". Cả 2 đúng theo logic riêng (toàn hệ thống vs của tôi) nhưng user thấy mâu thuẫn → mất niềm tin vào số liệu.

**Khác LL-FE-17** (KPI count phải bằng list count cùng filter): LL-FE-29 nói về SCOPE LABELING khi 2 trang khác phạm vi.

**Quy tắc:**

1. **Mọi `<KpiTile>` PHẢI có scope qualifier** trong label:
   ```vue
   <!-- ❌ SAI -->
   <KpiTile label="Phiếu chờ duyệt" :value="3" />

   <!-- ✅ ĐÚNG -->
   <KpiTile label="Phiếu chờ duyệt toàn hệ thống" :value="3" :scope="'all'" />
   <KpiTile label="Phiếu chờ duyệt của tôi" :value="0" :scope="'mine'" />
   ```

2. **Scope enum chuẩn** (chọn 1 — type-safe trong TS):
   ```typescript
   export type KpiScope = 'all' | 'mine' | 'department' | 'overdue' | 'next7d'

   const SCOPE_LABEL: Record<KpiScope, string> = {
     all: 'toàn hệ thống',
     mine: 'của tôi',
     department: `khoa ${userStore.department}`,
     overdue: 'quá hạn',
     next7d: '7 ngày tới',
   }
   ```

3. **Click KPI → navigate phải pass scope qua query param**:
   ```typescript
   const onKpiClick = (kpi: KpiDef) => {
     router.push({ path: kpi.target, query: { scope: kpi.scope }})
   }
   ```
   List view đọc `route.query.scope` apply cùng filter — count khớp 100%.

4. **Single-source service** (BE) — nhận `scope` param thay vì 2 endpoint riêng (xem LL-BE-23 hook chain idempotent pattern):
   ```typescript
   // FE API
   countPendingApprovals(scope: KpiScope = 'all'): Promise<number>
   ```

5. **Self-check** (chạy trước commit dashboard/widget):
   ```bash
   grep -rnE "label=\"(Phiếu|Đơn|Yêu cầu|PM|CM|Lịch|Báo cáo)[^\"]*\"" frontend/src/views/ \
     | grep -v "toàn hệ thống\|của tôi\|tôi phụ trách\|khoa\|quá hạn\|7 ngày\|tháng này"
   # Mỗi match → review xem có cần scope không
   ```

6. **Document scope trong page header**: list page có filter scope → render `<PageHeader subtitle="Hiển thị: Của tôi" />` để user thấy ngay phạm vi đang xem.

Reference: `CONVENTIONS.md §43`, `assetcore-fe` LL-FE-17 (KPI consistency — bổ trợ).
