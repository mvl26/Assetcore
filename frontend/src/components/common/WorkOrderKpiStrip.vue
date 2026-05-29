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
}

defineProps<{ items: WoKpiItem[] }>()
</script>

<template>
  <div
    v-if="items.length"
    class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4"
    data-testid="wo-kpi-strip"
  >
    <KpiCard
      v-for="(k, i) in items"
      :key="i"
      :label="k.label"
      :value="k.value"
      :color="k.color ?? 'primary'"
      :trend="k.trend"
    />
  </div>
</template>
