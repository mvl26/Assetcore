<script setup lang="ts">
// KPI card — persona dashboards (Core Doc §2). Nhận PersonaKpi từ BE.
// tone drive màu nền/viền; giá trị null → hiển thị "—" (KHÔNG số 0 giả).
import { computed } from 'vue'
import type { PersonaKpi } from '@/api/dashboard'

const props = defineProps<{ kpi: PersonaKpi }>()

const TONE: Record<string, { bar: string; val: string; bg: string }> = {
  primary: { bar: 'bg-blue-500',   val: 'text-blue-700',   bg: 'bg-blue-50/40' },
  info:    { bar: 'bg-cyan-500',   val: 'text-cyan-700',   bg: 'bg-cyan-50/40' },
  ok:      { bar: 'bg-emerald-500', val: 'text-emerald-700', bg: 'bg-emerald-50/40' },
  warn:    { bar: 'bg-amber-500',  val: 'text-amber-700',  bg: 'bg-amber-50/40' },
  danger:  { bar: 'bg-rose-500',   val: 'text-rose-700',   bg: 'bg-rose-50/40' },
}
const t = computed(() => TONE[props.kpi.tone] ?? TONE.info)

const display = computed(() => {
  const v = props.kpi.value
  if (v === null || v === undefined) return '—'
  return typeof v === 'number' ? v.toLocaleString('vi-VN') : String(v)
})
</script>

<template>
  <div class="relative overflow-hidden rounded-xl border border-neutral-200 p-4" :class="t.bg">
    <span class="absolute left-0 top-0 h-full w-1" :class="t.bar" />
    <p class="text-xs font-medium text-neutral-500">{{ kpi.label_vi }}</p>
    <p class="mt-1 text-3xl font-bold tabular-nums" :class="t.val">{{ display }}</p>
    <p v-if="kpi.foot_vi" class="mt-1 text-xs text-neutral-400">{{ kpi.foot_vi }}</p>
  </div>
</template>
