<script setup lang="ts">
// Bar chart card — KPI dạng cột (vd MTTR/SLA tóm tắt). Nhận series {label, value}.
import { computed } from 'vue'

export interface Bar {
  label: string
  value: number
  suffix?: string
}
const props = defineProps<{ title: string; bars: Bar[] }>()

const max = computed(() => Math.max(1, ...props.bars.map((b) => b.value)))
function h(v: number): string {
  return `${Math.round((v / max.value) * 100)}%`
}
</script>

<template>
  <div class="rounded-xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-100 px-4 py-3">
      <h3 class="text-sm font-semibold text-neutral-800">{{ title }}</h3>
    </div>
    <div class="p-4">
      <div v-if="bars.length" class="grid gap-3" :style="`grid-template-columns:repeat(${bars.length},1fr)`">
        <div v-for="(b, i) in bars" :key="i" class="text-center">
          <div class="flex h-24 items-end justify-center">
            <div class="w-8 rounded-t bg-emerald-500" :style="`height:${h(b.value)}`" />
          </div>
          <p class="mt-1 text-sm font-semibold tabular-nums text-neutral-700">
            {{ b.value.toLocaleString('vi-VN') }}{{ b.suffix ?? '' }}
          </p>
          <p class="text-xs text-neutral-400">{{ b.label }}</p>
        </div>
      </div>
      <p v-else class="py-6 text-center text-sm text-neutral-400">Chưa có dữ liệu</p>
    </div>
  </div>
</template>
