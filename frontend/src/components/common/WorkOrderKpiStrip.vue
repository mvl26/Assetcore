<script setup lang="ts">
// WorkOrderKpiStrip — KPI summary strip cho list-page IMM-08/09
// (docs/fe/08-pm/pm-list.html, docs/fe/09-repair/repair-list.html — 4 KPI card trên filter bar).
// Tái dùng common/KpiCard (Phase 2 design system). Labels do caller cấp (VI) → no EN leak.
import KpiCard from './KpiCard.vue'

type ToneName = 'primary' | 'success' | 'warning' | 'danger' | 'neutral' | 'info'

export interface WoKpiItem {
  label: string
  value: string | number
  color?: ToneName
  trend?: string
  /**
   * Optional click affordance. Khi true → card render như button + emit `kpi-click`.
   * Item KHÔNG set cờ này → giữ render tĩnh (không phá call-site IMM-08/09).
   */
  clickable?: boolean
}

defineProps<{ items: WoKpiItem[] }>()
const emit = defineEmits<{ (e: 'kpi-click', index: number): void }>()
</script>

<template>
  <div
    v-if="items.length"
    class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4"
    data-testid="wo-kpi-strip"
  >
    <component
      :is="k.clickable ? 'button' : 'div'"
      v-for="(k, i) in items"
      :key="i"
      type="button"
      :class="k.clickable ? 'text-left transition-transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-amber-400 rounded-[10px]' : ''"
      :data-testid="k.clickable ? 'wo-kpi-clickable' : undefined"
      @click="k.clickable && emit('kpi-click', i)"
    >
      <KpiCard
        :label="k.label"
        :value="k.value"
        :color="k.color ?? 'primary'"
        :trend="k.trend"
      />
    </component>
  </div>
</template>
