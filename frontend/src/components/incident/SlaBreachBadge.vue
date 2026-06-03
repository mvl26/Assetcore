<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-12 BR-12-09 — Badge "Vi phạm SLA" cho sự cố.
// Đọc TRỰC TIẾP cờ Incident Report.response_breached / resolution_breached (0|1).
// Render 1 badge cho mỗi loại breach đang bật; không cờ nào bật → không render gì.
// Nhãn tiếng Việt qua SSoT (constants/labels.ts) — KHÔNG leak "breached"/English.
import { computed } from 'vue'
import { SLA_BREACH_LABEL, SLA_BREACH_BADGE_CLASS } from '@/constants/labels'

const props = defineProps<{
  responseBreached?: number | null
  resolutionBreached?: number | null
  size?: 'xs' | 'sm'
}>()

interface BreachItem { key: 'response' | 'resolution'; label: string }

const breaches = computed<BreachItem[]>(() => {
  const items: BreachItem[] = []
  if (props.responseBreached) items.push({ key: 'response', label: SLA_BREACH_LABEL.response })
  if (props.resolutionBreached) items.push({ key: 'resolution', label: SLA_BREACH_LABEL.resolution })
  return items
})

const sizeClass = computed(() =>
  props.size === 'xs' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-[11px]',
)
const badgeClass = SLA_BREACH_BADGE_CLASS
</script>

<template>
  <span
    v-for="b in breaches"
    :key="b.key"
    class="inline-flex items-center gap-1 font-medium rounded leading-none whitespace-nowrap"
    :class="[sizeClass, badgeClass]"
    :title="b.label"
  >
    <svg class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
    </svg>
    {{ b.label }}
  </span>
</template>
