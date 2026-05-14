<script setup lang="ts">
// KpiCard — shared KPI tile, design-system spec §3 + Dashboard.jsx
// - Top 3px stripe (color via prop)
// - Manrope 30px bold, -0.02em tracking
// - 13px slate-600 label
// - 12px trend in semantic color
import { computed } from 'vue'

type ToneName = 'primary' | 'success' | 'warning' | 'danger' | 'neutral' | 'info'

const props = withDefaults(defineProps<{
  label: string
  value: string | number
  trend?: string
  color?: ToneName
}>(), {
  color: 'primary',
})

const TONE: Record<ToneName, { stripe: string; trend: string }> = {
  primary: { stripe: '#2563eb', trend: '#1d4ed8' },
  info:    { stripe: '#2563eb', trend: '#1d4ed8' },
  success: { stripe: '#10b981', trend: '#059669' },
  warning: { stripe: '#d97706', trend: '#d97706' },
  danger:  { stripe: '#ef4444', trend: '#dc2626' },
  neutral: { stripe: '#94a3b8', trend: '#475569' },
}

const tone = computed(() => TONE[props.color])
</script>

<template>
  <div
    class="kpi-tile relative overflow-hidden bg-white border border-slate-200 rounded-[10px] p-5 shadow-card"
    :style="{ '--kpi-stripe': tone.stripe }"
  >
    <div class="kpi-label text-[13px] font-semibold text-slate-600">{{ label }}</div>
    <div
      class="kpi-value font-display font-bold text-[30px] leading-none mt-1.5 tracking-[-0.02em] text-slate-900"
    >
{{ value }}
</div>
    <div
      v-if="trend"
      class="kpi-trend text-xs font-medium mt-1.5"
      :style="{ color: tone.trend }"
    >
{{ trend }}
</div>
  </div>
</template>

<style scoped>
.kpi-tile::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--kpi-stripe);
}
.font-display { font-family: 'Manrope', 'Inter', system-ui, sans-serif; }
</style>
