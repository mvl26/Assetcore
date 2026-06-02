<script setup lang="ts">
// Bar chart card — KPI dạng cột (vd MTTR/SLA tóm tắt). Nhận series {label, value}.
import { computed } from 'vue'
import { canAccessDrill } from '@/router/routeAccess'
import { useCapabilities } from '@/composables/useCapabilities'

export interface BarDrill { route: string; query: Record<string, string> }
export interface Bar {
  label: string
  value: number
  suffix?: string
  /** R8 §9.4.6 — bar drill descriptor. Có → bar click-through (RouterLink). */
  drill?: BarDrill | null
}
const props = defineProps<{ title: string; bars: Bar[] }>()
const { can } = useCapabilities()

const max = computed(() => Math.max(1, ...props.bars.map((b) => b.value)))
function h(v: number): string {
  return `${Math.round((v / max.value) * 100)}%`
}
// §9.5 #9 — bar chỉ clickable khi vào được route đích; thiếu quyền → bar tĩnh.
function drillTo(b: Bar) {
  if (!b.drill || !canAccessDrill(b.drill.route, can)) return null
  return { path: b.drill.route, query: b.drill.query }
}
</script>

<template>
  <div class="rounded-xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-100 px-4 py-3">
      <h3 class="text-sm font-semibold text-neutral-800">{{ title }}</h3>
    </div>
    <div class="p-4">
      <div v-if="bars.length" class="grid gap-3" :style="`grid-template-columns:repeat(${bars.length},1fr)`">
        <component
          :is="drillTo(b) ? 'RouterLink' : 'div'"
          v-for="(b, i) in bars" :key="i"
          :to="drillTo(b) ?? undefined"
          class="block text-center rounded-lg"
          :class="drillTo(b) ? 'group cursor-pointer transition hover:bg-emerald-50/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400' : ''"
        >
          <div class="flex h-24 items-end justify-center">
            <div class="w-8 rounded-t bg-emerald-500 transition group-hover:bg-emerald-600" :style="`height:${h(b.value)}`" />
          </div>
          <p class="mt-1 text-sm font-semibold tabular-nums text-neutral-700">
            {{ b.value.toLocaleString('vi-VN') }}{{ b.suffix ?? '' }}
          </p>
          <p class="text-xs" :class="drillTo(b) ? 'text-emerald-600 group-hover:underline' : 'text-neutral-400'">{{ b.label }}</p>
        </component>
      </div>
      <p v-else class="py-6 text-center text-sm text-neutral-400">Chưa có dữ liệu</p>
    </div>
  </div>
</template>
