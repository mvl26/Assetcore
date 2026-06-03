<script setup lang="ts">
import { computed, ref } from 'vue'
import { canAccessDrill } from '@/router/routeAccess'
import { useCapabilities } from '@/composables/useCapabilities'

interface Props {
  labels: string[]
  series: number[]
  colors: string[]
  /** Core Doc §9.2 — canonical codes song song labels (cho drill-down). */
  codes?: string[]
  /** Core Doc §9.5 #9 — route đích của segment-click. Có → gate clickable theo
   * quyền (thiếu quyền vào route → segment KHÔNG click được, không emit). */
  drillRoute?: string
}
const props = defineProps<Props>()
const { can } = useCapabilities()

// Core Doc §9.5 — click segment/legend → emit để parent route tới list filtered.
const emit = defineEmits<{
  (e: 'segment-click', payload: { label: string; code: string; value: number }): void
}>()

const hoveredIdx = ref<number | null>(null)

// Clickable khi có codes VÀ (không khai báo drillRoute HOẶC user vào được route).
const clickable = computed(() => {
  if (!Array.isArray(props.codes) || props.codes.length === 0) return false
  if (props.drillRoute && !canAccessDrill(props.drillRoute, can)) return false
  return true
})

function onSegment(i: number): void {
  if (!clickable.value) return
  const code = props.codes?.[i] ?? props.labels[i] ?? ''
  emit('segment-click', { label: props.labels[i] ?? '', code, value: props.series[i] ?? 0 })
}

const total = computed(() => props.series.reduce((a, b) => a + b, 0))

const SIZE   = 220
const STROKE = 36
const R      = (SIZE - STROKE) / 2
const C      = 2 * Math.PI * R

interface Arc {
  label: string
  value: number
  percent: number
  color: string
  dash: string
  offset: number
}

const arcs = computed<Arc[]>(() => {
  if (total.value === 0) return []
  let cursor = 0
  return props.series.map((v, i) => {
    const percent = v / total.value
    const len = percent * C
    const arc: Arc = {
      label:   props.labels[i],
      value:   v,
      percent,
      color:   props.colors[i] ?? '#94a3b8',
      dash:    `${len} ${C - len}`,
      offset:  -cursor,
    }
    cursor += len
    return arc
  })
})

// Arc đang hover — hiển thị ở trung tâm
const hovered = computed(() =>
  hoveredIdx.value == null ? null : arcs.value[hoveredIdx.value] ?? null,
)

function fmt(n: number): string { return n.toLocaleString('vi-VN') }
</script>

<template>
  <div class="flex flex-col items-center gap-5">
<!-- SVG donut -->
    <div class="relative shrink-0" :style="{ width: `${SIZE}px`, height: `${SIZE}px` }">
      <svg
:width="SIZE" :height="SIZE" :viewBox="`0 0 ${SIZE} ${SIZE}`"
           class="-rotate-90 transform" style="filter: drop-shadow(0 4px 12px rgba(0,0,0,.06))">
        <!-- background ring -->
        <circle
:cx="SIZE/2" :cy="SIZE/2" :r="R"
                fill="none" stroke="#f1f5f9" :stroke-width="STROKE" />
        <!-- slices -->
        <circle
          v-for="(a, i) in arcs" :key="i"
          :cx="SIZE/2" :cy="SIZE/2" :r="R"
          fill="none"
          :stroke="a.color"
          :stroke-width="hoveredIdx === i ? STROKE + 4 : STROKE"
          :stroke-dasharray="a.dash"
          :stroke-dashoffset="a.offset"
          stroke-linecap="round"
          class="transition-all duration-300"
          :class="clickable ? 'cursor-pointer' : ''"
          :style="{ opacity: hoveredIdx != null && hoveredIdx !== i ? 0.4 : 1 }"
          @mouseenter="hoveredIdx = i"
          @mouseleave="hoveredIdx = null"
          @click="onSegment(i)"
        />
      </svg>

      <!-- center label -->
      <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <template v-if="hovered">
          <span class="text-xl font-bold tabular-nums" :style="{ color: hovered.color }">
            {{ fmt(hovered.value) }}
          </span>
          <span class="text-[11px] font-semibold text-slate-500 mt-0.5 text-center max-w-[100px] leading-tight">
            {{ hovered.label }}
          </span>
          <span class="text-xs text-slate-400 mt-0.5">
            {{ (hovered.percent * 100).toFixed(1) }}%
          </span>
        </template>
        <template v-else>
          <span class="text-2xl font-bold text-slate-800 tabular-nums">{{ fmt(total) }}</span>
          <span class="text-[11px] font-medium text-slate-400 uppercase tracking-wider mt-0.5">Thiết bị</span>
        </template>
      </div>
    </div>

    <!-- Legend với progress bars -->
    <ul class="w-full space-y-2.5">
      <li v-if="arcs.length === 0" class="text-sm text-slate-400 italic text-center">
        Chưa có dữ liệu thiết bị
      </li>
      <li
        v-for="(a, i) in arcs" :key="i"
        class="group rounded-md px-1 -mx-1 transition-colors"
        :class="clickable ? 'cursor-pointer hover:bg-slate-50' : ''"
        @mouseenter="hoveredIdx = i"
        @mouseleave="hoveredIdx = null"
        @click="onSegment(i)"
      >
        <div class="flex items-center justify-between mb-1">
          <div class="flex items-center gap-2">
            <span
class="w-2.5 h-2.5 rounded-full shrink-0 transition-transform group-hover:scale-125"
                  :style="{ background: a.color }" />
            <span class="text-xs text-slate-700 font-medium">{{ a.label }}</span>
          </div>
          <div class="flex items-center gap-2 tabular-nums">
            <span class="text-xs font-bold text-slate-800">{{ fmt(a.value) }}</span>
            <span class="text-[10px] text-slate-400 w-10 text-right">{{ (a.percent * 100).toFixed(1) }}%</span>
          </div>
        </div>
        <!-- mini progress bar -->
        <div class="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
class="h-full rounded-full transition-all duration-500"
               :style="{ width: (a.percent * 100) + '%', background: a.color,
                         opacity: hoveredIdx != null && hoveredIdx !== i ? 0.35 : 1 }" />
        </div>
      </li>
    </ul>
  </div>
</template>
