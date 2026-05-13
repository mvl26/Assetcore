<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Nút toggle bộ lọc — đặt trong header trang. Panel render bằng <ListFilterBar /> bên dưới.
import { computed } from 'vue'

const props = defineProps<{
  modelValue: boolean
  count?: number
}>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const show = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>

<template>
  <button
    class="relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-colors"
    :class="show
      ? 'bg-brand-50 border-brand-300 text-brand-700'
      : 'bg-white border-slate-300 text-slate-600 hover:border-slate-400 hover:text-slate-800'"
    @click="show = !show"
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 8h10M11 12h2M9 16h6" />
    </svg>
    Bộ lọc
    <span
      v-if="(count ?? 0) > 0"
      class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full"
      :class="show ? 'bg-brand-600 text-white' : 'bg-blue-500 text-white'"
    >{{ count }}</span>
    <svg
      class="w-3.5 h-3.5 transition-transform duration-200"
      :class="show ? 'rotate-180' : ''"
      fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  </button>
</template>
