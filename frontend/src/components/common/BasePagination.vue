<script setup lang="ts">
import { computed } from 'vue'
import type { PaginationMeta } from '@/types/common'

const props = defineProps<{ pagination: PaginationMeta }>()
const emit = defineEmits<{ 'page-change': [page: number] }>()

const hasPrev = computed(() => props.pagination.page > 1)
const hasNext = computed(() => props.pagination.page < props.pagination.total_pages)

// Show at most 5 page buttons centered around the current page
const visiblePages = computed<number[]>(() => {
  const { page, total_pages } = props.pagination
  if (total_pages <= 7) return Array.from({ length: total_pages }, (_, i) => i + 1)
  const delta = 2
  const range: number[] = []
  for (let i = Math.max(2, page - delta); i <= Math.min(total_pages - 1, page + delta); i++) {
    range.push(i)
  }
  if (range[0] > 2) range.unshift(-1)       // -1 = ellipsis
  if (range[range.length - 1] < total_pages - 1) range.push(-2)  // -2 = ellipsis
  return [1, ...range, total_pages]
})
</script>

<template>
  <div v-if="pagination.total_pages > 1" class="flex flex-col sm:flex-row items-center justify-between gap-3 mt-4">
    <span class="text-sm text-slate-500 order-2 sm:order-1">
      Trang {{ pagination.page }}/{{ pagination.total_pages }}
      <span class="text-slate-400">({{ pagination.total }} bản ghi)</span>
    </span>

    <div class="flex items-center gap-1 order-1 sm:order-2">
      <!-- Prev -->
      <button
        :disabled="!hasPrev"
        class="px-2.5 py-1.5 rounded border text-sm transition-colors min-h-[36px]"
        :class="hasPrev ? 'border-slate-300 hover:bg-slate-50 text-slate-600' : 'border-slate-200 text-slate-300 cursor-not-allowed'"
        @click="hasPrev && emit('page-change', pagination.page - 1)"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <!-- Page numbers (hidden on xs if many pages) -->
      <template v-for="p in visiblePages" :key="p">
        <span v-if="p < 0" class="px-1 text-slate-400 text-sm">…</span>
        <button
          v-else
          :class="[
            'px-3 py-1.5 rounded border text-sm transition-colors min-h-[36px] min-w-[36px]',
            p === pagination.page
              ? 'bg-blue-600 text-white border-blue-600 font-semibold'
              : 'border-slate-300 hover:bg-slate-50 text-slate-600',
          ]"
          @click="emit('page-change', p)"
        >{{ p }}</button>
      </template>

      <!-- Next -->
      <button
        :disabled="!hasNext"
        class="px-2.5 py-1.5 rounded border text-sm transition-colors min-h-[36px]"
        :class="hasNext ? 'border-slate-300 hover:bg-slate-50 text-slate-600' : 'border-slate-200 text-slate-300 cursor-not-allowed'"
        @click="hasNext && emit('page-change', pagination.page + 1)"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  </div>
</template>
