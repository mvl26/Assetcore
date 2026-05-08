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
