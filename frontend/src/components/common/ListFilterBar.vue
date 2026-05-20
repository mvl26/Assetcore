<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Chips bar + panel bộ lọc full-width, đặt ngay dưới header trang.
// Toggle button đặt riêng trong header bằng <FilterToggleButton />.
import { onBeforeUnmount } from 'vue'

export interface FilterChip { key: string; label: string }

const props = withDefaults(defineProps<{
  show: boolean
  chips: FilterChip[]
  search?: string
  searchPlaceholder?: string
  showSearch?: boolean
  // Auto-apply `searchDebounceMs` after the user stops typing. Set to 0 to
  // disable (back to button-only). 350ms is the chosen UX sweet spot —
  // small enough to feel instant, large enough to avoid firing on every
  // keystroke during typing.
  searchDebounceMs?: number
}>(), {
  search: '',
  searchPlaceholder: 'Tìm kiếm...',
  showSearch: true,
  searchDebounceMs: 350,
})

const emit = defineEmits<{
  'update:search': [v: string]
  apply:        []
  reset:        []
  'clear-chip': [key: string]
}>()

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function cancelPending() {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
}

// Bind value via :value + @input (not v-model) so programmatic resets
// from the parent (e.g. resetFilters() setting search='') do NOT
// trigger debounced auto-apply — only direct user input does.
function onSearchInput(v: string) {
  emit('update:search', v)
  cancelPending()
  if (props.searchDebounceMs > 0) {
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      emit('apply')
    }, props.searchDebounceMs)
  }
}

function applyNow() {
  cancelPending()
  emit('apply')
}

onBeforeUnmount(cancelPending)
</script>

<template>
  <div>
    <!-- Active chips bar (panel closed) -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div v-if="chips.length > 0 && !show" class="flex flex-wrap items-center gap-2 mb-4">
        <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
        <button
          v-for="chip in chips"
          :key="chip.key"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
          @click="emit('clear-chip', chip.key)"
        >
          {{ chip.label }}
          <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2 transition-colors" @click="emit('reset')">
          Xóa tất cả
        </button>
      </div>
    </Transition>

    <!-- Collapsible panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-96"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-96"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="show" class="card mb-5 p-4">
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-3">
          <slot name="fields" />
        </div>
        <div v-if="showSearch" class="flex gap-2">
          <input
            :value="search"
            :placeholder="searchPlaceholder"
            class="form-input flex-1 text-sm"
            @input="onSearchInput(($event.target as HTMLInputElement).value)"
            @keyup.enter="applyNow"
          />
          <button class="btn-primary text-sm" @click="applyNow">Tìm</button>
          <button class="btn-ghost text-sm" @click="emit('reset')">Đặt lại</button>
        </div>
        <div v-else class="flex gap-2 justify-end">
          <button class="btn-primary text-sm" @click="applyNow">Áp dụng</button>
          <button class="btn-ghost text-sm" @click="emit('reset')">Đặt lại</button>
        </div>

        <div v-if="chips.length > 0" class="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-slate-100">
          <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
          <button
            v-for="chip in chips"
            :key="chip.key"
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
            @click="emit('clear-chip', chip.key)"
          >
            {{ chip.label }}
            <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2 transition-colors" @click="emit('reset')">
            Xóa tất cả
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>
