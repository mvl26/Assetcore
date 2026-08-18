# Reusable component patterns

## Modal pattern

```vue
<!-- DetailModal.vue -->
<script setup lang="ts">
defineProps<{ open: boolean; title: string }>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center"
         @click.self="emit('close')">
      <div class="bg-white rounded-lg shadow-xl w-[640px] max-h-[80vh] overflow-auto">
        <header class="flex items-center justify-between px-4 py-3 border-b">
          <h2 class="font-semibold">{{ title }}</h2>
          <button class="text-neutral-400 hover:text-neutral-700" @click="emit('close')">✕</button>
        </header>
        <div class="p-4"><slot /></div>
      </div>
    </div>
  </Teleport>
</template>
```

## Confirm dialog

```ts
import { useConfirm } from '@/composables/useConfirm'
const ok = await useConfirm({ title: 'Đóng work order?', message: 'Hành động này không thể hoàn tác.' })
if (ok) await store.closeWO(...)
```

## Status badge

Single source of truth for color → status. Put in `components/common/StatusBadge.vue`:

```ts
const COLOR: Record<string, string> = {
  Open: 'bg-blue-100 text-blue-700',
  'In Progress': 'bg-amber-100 text-amber-700',
  Completed: 'bg-emerald-100 text-emerald-700',
  Cancelled: 'bg-neutral-200 text-neutral-600',
  'Cannot Repair': 'bg-rose-100 text-rose-700',
}
```

## Pagination

Use `usePagination` composable — handles page change, total pages, jump-to-page. Don't reimplement.

## Table

Common columns layout:

```vue
<table class="w-full text-sm">
  <thead class="bg-neutral-50 text-neutral-600 text-left">
    <tr>
      <th class="px-3 py-2">Mã WO</th>
      <th class="px-3 py-2">Thiết bị</th>
      <th class="px-3 py-2">Trạng thái</th>
      <th class="px-3 py-2">SLA</th>
      <th class="px-3 py-2 text-right">Thao tác</th>
    </tr>
  </thead>
  <tbody class="divide-y">
    <tr v-for="row in items" :key="row.name" class="hover:bg-neutral-50">
      <td class="px-3 py-2 font-mono">{{ row.name }}</td>
      <!-- ... -->
    </tr>
  </tbody>
</table>
```

## Responsive (mobile-first)

> DoD bắt buộc — xem `rules.md` LL-FE-34 + ADR-IMM00-RESPONSIVE. Breakpoint Tailwind DEFAULT (`sm:640 md:768 lg:1024 xl:1280`), KHÔNG custom px, KHÔNG PWA. Mobile-first: base = mobile, thêm `sm:`/`md:`/`lg:`.

**P1 — List = table→card** (desktop table `hidden sm:block`; mobile `mobile-card-list sm:hidden`):

```vue
<!-- Mobile cards (< sm) -->
<div class="mobile-card-list sm:hidden">
  <div v-for="row in items" :key="row.name" class="mobile-card" @click="goDetail(row)">
    <div class="flex items-center justify-between mb-2">
      <span class="font-mono text-sm font-semibold text-brand-700">{{ row.name }}</span>
      <StatusBadge :state="row.status" size="xs" />
    </div>
    <p class="text-sm font-medium text-slate-900 truncate">{{ row.asset_name || row.asset }}</p>
  </div>
</div>

<!-- Desktop table (sm+) — P3: luôn bọc overflow-x-auto -->
<div class="hidden sm:block overflow-x-auto">
  <table class="min-w-full text-sm">…</table>
</div>
```

**P2 — Form grid 1-col mobile → 2-col desktop:**

```vue
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
  <FormField … /> <FormField … />
</div>
```

**P3 — MỌI `<table>` bọc `overflow-x-auto`** (kể cả khi đã có card-list — bảng desktop vẫn cần): `<div class="overflow-x-auto"><table>…</table></div>`.

**P4 — Tab-bar / chip-bar dài cuộn được** (`overflow-x-auto` + mỗi item `shrink-0`, giữ 1 hàng):

```vue
<div class="flex gap-1 mb-4 border-b border-slate-200 overflow-x-auto">
  <button v-for="tab in tabs" :key="tab" class="shrink-0 px-4 py-2 whitespace-nowrap …">{{ label(tab) }}</button>
</div>
```

**P5 — Touch target ≥44px** cho nút icon/action chạm: `min-h-[44px] min-w-[44px]` (hoặc `h-11 w-11`).

**Modal full-screen mobile** (`BaseModal` + ⌘K đồng bộ):

```vue
<!-- card container -->
<div :class="['bg-white shadow-2xl w-full flex flex-col',
   'inset-0 fixed h-full rounded-none max-h-screen',           /* mobile base */
   'sm:inset-auto sm:relative sm:m-auto sm:rounded-2xl sm:h-auto sm:max-h-[90vh]', /* sm:+ centered */
   sizeClass[size]]">
  …
  <!-- nút đóng ≥44px (P5) -->
  <button class="min-h-[44px] min-w-[44px] rounded-lg flex items-center justify-center …" @click="onClose">✕</button>
</div>
```

## Loading + error state (required in all List and Detail views)

Every view that fetches async data must have all three branches. Never use just `v-if="loading"` + `v-else`:

```vue
<!-- List view pattern -->
<div v-if="store.loading" class="py-8 text-center text-neutral-400">
  Đang tải…
</div>

<div v-else-if="store.error"
     class="rounded border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 flex items-center gap-3">
  <span class="flex-1">{{ store.error }}</span>
  <button class="text-sm underline" @click="load()">Thử lại</button>
</div>

<template v-else>
  <table class="w-full text-sm">…</table>
  <BasePagination … />
</template>
```

```vue
<!-- Detail view pattern — skeleton while loading, error card on failure -->
<div v-if="store.loading && !store.current" class="space-y-4 animate-pulse">
  <div class="h-6 bg-neutral-200 rounded w-1/3" />
  <div class="h-4 bg-neutral-100 rounded w-2/3" />
</div>

<div v-else-if="store.error && !store.current"
     class="rounded border border-rose-200 bg-rose-50 px-4 py-6 text-center text-rose-700">
  <p class="mb-3">{{ store.error }}</p>
  <button class="px-3 py-1 rounded bg-rose-100 text-sm" @click="load()">Thử lại</button>
</div>

<div v-else-if="store.current">
  <!-- actual content -->
</div>
```

**Rule:** `v-if/v-else-if/v-else` — always tri-branch. Missing the error branch means errors are swallowed silently and users see an empty state with no feedback.

## Form field with inline error

```vue
<label class="block">
  <span class="text-sm font-medium">Mô tả lỗi</span>
  <textarea v-model="form.failure_description"
            class="mt-1 w-full border rounded px-2 py-1"
            :class="{ 'border-rose-500': formErrors.failure_description }" />
  <p v-if="formErrors.failure_description" class="text-rose-600 text-xs mt-1">
    {{ formErrors.failure_description }}
  </p>
</label>
```

When `useApi.onFieldError` runs, `formErrors[field]` is populated automatically — clear it on next submit.
