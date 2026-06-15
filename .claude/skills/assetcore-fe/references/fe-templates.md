# assetcore-fe — Templates (API client · Store · View · Forms · TanStack Query)

> Heavy reference moved out of `SKILL.md` (progressive disclosure). Copy these templates verbatim when scaffolding a new IMM module on FE. Principles + naming + the grep gate stay in `SKILL.md`.

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

## Forms with autosave

Use `useFormDraft` for any multi-step or long form (saves to localStorage). See `src/composables/useFormDraft.ts`.

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
