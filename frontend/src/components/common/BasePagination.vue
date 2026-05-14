<script setup lang="ts">
import type { PaginationMeta } from '@/types/common'

defineProps<{ pagination: PaginationMeta }>()
const emit = defineEmits<{ 'page-change': [page: number] }>()
</script>

<template>
  <div v-if="pagination.total_pages > 1" class="flex items-center justify-between mt-4">
    <span class="text-sm text-slate-500">
      Trang {{ pagination.page }}/{{ pagination.total_pages }}
      <span class="text-slate-400">({{ pagination.total }} bản ghi)</span>
    </span>
    <div class="flex gap-1">
      <button
        v-for="p in pagination.total_pages"
        :key="p"
        :class="[
          'px-3 py-1 rounded text-sm border transition-colors',
          p === pagination.page
            ? 'bg-blue-600 text-white border-blue-600'
            : 'border-slate-300 hover:bg-slate-50 text-slate-600',
        ]"
        @click="emit('page-change', p)"
      >
{{ p }}
</button>
    </div>
  </div>
</template>
