<script setup lang="ts">
// Donut chart dùng SVG thuần (không cần chart lib) — hiệu năng cao, render tức thời.
import { computed } from 'vue'

interface Props {
  labels: string[]
  series: number[]
  colors: string[]
}
const props = defineProps<Props>()

const total = computed(() => props.series.reduce((a, b) => a + b, 0))

const SIZE = 180
const STROKE = 28
const R = (SIZE - STROKE) / 2
const C = 2 * Math.PI * R

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
      label: props.labels[i],
      value: v,
      percent,
      color: props.colors[i] ?? '#94a3b8',
      dash: `${len} ${C - len}`,
      offset: -cursor,
    }
    cursor += len
    return arc
  })
})

function fmt(n: number): string {
  return n.toLocaleString('vi-VN')
}
</script>

<template>
  <div class="flex flex-col md:flex-row items-center gap-6">
    <!-- SVG donut -->
    <div class="relative shrink-0" :style="{ width: `${SIZE}px`, height: `${SIZE}px` }">
      <svg :width="SIZE" :height="SIZE" :viewBox="`0 0 ${SIZE} ${SIZE}`" class="-rotate-90 transform">
        <!-- Background ring -->
        <circle :cx="SIZE / 2" :cy="SIZE / 2" :r="R"
                fill="none" stroke="#f1f5f9" :stroke-width="STROKE" />
        <!-- Slices -->
        <circle v-for="(a, i) in arcs" :key="i"
                :cx="SIZE / 2" :cy="SIZE / 2" :r="R"
                fill="none"
                :stroke="a.color"
                :stroke-width="STROKE"
                :stroke-dasharray="a.dash"
                :stroke-dashoffset="a.offset"
                class="transition-all duration-500" />
      </svg>
      <!-- Center text -->
      <div class="absolute inset-0 flex flex-col items-center justify-center">
        <span class="text-2xl font-bold text-slate-800">{{ fmt(total) }}</span>
        <span class="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Thiết bị</span>
      </div>
    </div>

    <!-- Legend -->
    <ul class="flex-1 space-y-2 w-full">
      <li v-if="arcs.length === 0" class="text-sm text-slate-400 italic">
        Chưa có dữ liệu thiết bị
      </li>
      <li v-for="(a, i) in arcs" :key="i"
          class="flex items-center gap-3 text-sm">
        <span class="w-3 h-3 rounded-sm shrink-0" :style="{ background: a.color }" />
        <span class="flex-1 text-slate-700 truncate">{{ a.label }}</span>
        <span class="font-semibold text-slate-800 tabular-nums">{{ fmt(a.value) }}</span>
        <span class="w-12 text-right text-xs text-slate-400 tabular-nums">
          {{ (a.percent * 100).toFixed(1) }}%
        </span>
      </li>
    </ul>
  </div>
</template>
