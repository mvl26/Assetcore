<script setup lang="ts">
// KPI card — persona dashboards (Core Doc §2 + §9.1). Nhận PersonaKpi từ BE.
// tone drive màu nền/viền; giá trị null → hiển thị "—" (KHÔNG số 0 giả).
// Khi kpi.drill có giá trị → render RouterLink click-through tới list view
// đã pre-apply filter (Core Doc §9.1).
import { computed } from 'vue'
import type { PersonaKpi } from '@/api/dashboard'
import { canAccessDrill } from '@/router/routeAccess'
import { useCapabilities } from '@/composables/useCapabilities'

const props = defineProps<{ kpi: PersonaKpi }>()
const { can } = useCapabilities()

const TONE: Record<string, { bar: string; val: string; bg: string; dot: string }> = {
  primary: { bar: 'bg-blue-500',    val: 'text-blue-700',    bg: 'from-blue-50/60',    dot: 'bg-blue-400' },
  info:    { bar: 'bg-cyan-500',    val: 'text-cyan-700',    bg: 'from-cyan-50/60',    dot: 'bg-cyan-400' },
  ok:      { bar: 'bg-emerald-500', val: 'text-emerald-700', bg: 'from-emerald-50/60', dot: 'bg-emerald-400' },
  warn:    { bar: 'bg-amber-500',   val: 'text-amber-700',   bg: 'from-amber-50/60',   dot: 'bg-amber-400' },
  danger:  { bar: 'bg-rose-500',    val: 'text-rose-700',    bg: 'from-rose-50/60',    dot: 'bg-rose-400' },
}
const t = computed(() => TONE[props.kpi.tone] ?? TONE.info)

const display = computed(() => {
  const v = props.kpi.value
  if (v === null || v === undefined) return '—'
  return typeof v === 'number' ? v.toLocaleString('vi-VN') : String(v)
})

// Core Doc §9.1 + §9.5 #9 — drill descriptor → RouterLink target {path, query}.
// CHỈ clickable khi user vào được route đích (canAccessDrill); thiếu quyền →
// card tĩnh, KHÔNG link tới /unauthorized (bug opsmgr 2026-06-02).
const drillTo = computed(() => {
  const d = props.kpi.drill
  if (!d || !canAccessDrill(d.route, can)) return null
  return { path: d.route, query: d.query }
})
</script>

<template>
  <!-- Drillable: RouterLink với hover affordance + mũi tên (Core Doc §9.1, §9.5). -->
  <RouterLink
    v-if="drillTo"
    :to="drillTo"
    class="group relative block overflow-hidden rounded-2xl border border-neutral-200/80 bg-gradient-to-br to-white
           p-5 shadow-sm ring-1 ring-neutral-900/[0.02] transition-all duration-200
           hover:-translate-y-0.5 hover:border-neutral-300 hover:shadow-lg
           focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
    :class="t.bg"
  >
    <span class="absolute left-0 top-0 h-full w-1" :class="t.bar" />
    <div class="flex items-start justify-between">
      <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">{{ kpi.label_vi }}</p>
      <span
        class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/70 text-neutral-300
               shadow-sm transition group-hover:text-neutral-500"
      >
        <svg class="h-3.5 w-3.5 transition group-hover:translate-x-0.5"
          fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </span>
    </div>
    <p class="mt-2 text-[2rem] font-bold leading-none tabular-nums" :class="t.val">{{ display }}</p>
    <p v-if="kpi.foot_vi" class="mt-2 text-xs text-neutral-400">{{ kpi.foot_vi }}</p>
  </RouterLink>

  <!-- Tĩnh: không drill được → card thường, không con trỏ pointer giả (§9.5). -->
  <div
    v-else
    class="relative overflow-hidden rounded-2xl border border-neutral-200/80 bg-gradient-to-br to-white
           p-5 shadow-sm ring-1 ring-neutral-900/[0.02]"
    :class="t.bg"
  >
    <span class="absolute left-0 top-0 h-full w-1" :class="t.bar" />
    <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">{{ kpi.label_vi }}</p>
    <p class="mt-2 text-[2rem] font-bold leading-none tabular-nums" :class="t.val">{{ display }}</p>
    <p v-if="kpi.foot_vi" class="mt-2 text-xs text-neutral-400">{{ kpi.foot_vi }}</p>
  </div>
</template>
