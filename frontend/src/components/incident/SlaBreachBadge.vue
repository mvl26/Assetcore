<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-12 BR-12-09/13 — Badge trạng thái SLA cho sự cố.
// Đọc TRỰC TIẾP cờ DERIVED của BE (is_response_breached/is_resolution_breached, 0|1)
// mà consumer truyền vào response-breached/resolution-breached — KHÔNG so ngày
// client-clock (SSoT overdue_server_flag). Nhãn tiếng Việt qua SSoT (constants/
// labels.ts) — KHÔNG leak "breached"/English.
//
// Hai chế độ (1 component, tái dùng — KHÔNG tách component mới):
//  • Combined (list/dashboard, mặc định — KHÔNG set `kind`): render badge đỏ
//    "Vi phạm cam kết mức dịch vụ …" cho MỖI loại đang breach; không breach → không
//    render gì (v-if). Giữ nguyên hành vi cũ.
//  • Single-status (màn Chi tiết §Tình trạng SLA — set `kind`): LUÔN render đúng 1
//    badge cho `kind` đó — "Quá hạn" (đỏ) nếu cờ bật, "Trong hạn" (xanh) nếu không.
import { computed } from 'vue'
import {
  SLA_BREACH_LABEL, SLA_BREACH_BADGE_CLASS,
  SLA_STATUS_LABEL, SLA_WITHIN_BADGE_CLASS,
} from '@/constants/labels'

const props = defineProps<{
  responseBreached?: number | null
  resolutionBreached?: number | null
  size?: 'xs' | 'sm'
  // Set → chế độ trạng thái đơn (màn Chi tiết): render 1 badge Quá hạn/Trong hạn
  // cho loại này. KHÔNG set → chế độ combined (list/dashboard) như cũ.
  kind?: 'response' | 'resolution'
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

// ── Chế độ trạng thái đơn (§Tình trạng SLA) ──────────────────────────────────
// Đọc CỜ tương ứng với `kind` (đã là cờ derived server-side do consumer truyền
// `is_*_breached ?? *_breached`). KHÔNG dùng ngày để tự suy ra quá hạn.
const isBreached = computed(() =>
  props.kind === 'response' ? !!props.responseBreached : !!props.resolutionBreached,
)
const statusLabel = computed(() =>
  isBreached.value ? SLA_STATUS_LABEL.breached : SLA_STATUS_LABEL.within,
)
const statusBadgeClass = computed(() =>
  isBreached.value ? SLA_BREACH_BADGE_CLASS : SLA_WITHIN_BADGE_CLASS,
)
</script>

<template>
  <!-- Single-status mode (màn Chi tiết): luôn render 1 badge Quá hạn/Trong hạn -->
  <span
    v-if="kind"
    class="inline-flex items-center gap-1 font-medium rounded leading-none whitespace-nowrap"
    :class="[sizeClass, statusBadgeClass]"
    :title="statusLabel"
  >
    <!-- Icon khác nhau theo trạng thái (không dựa màu-một-mình — WCAG) -->
    <svg v-if="isBreached" class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
    </svg>
    <svg v-else class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    {{ statusLabel }}
  </span>

  <!-- Combined-breach mode (list/dashboard): chỉ render badge đỏ khi breached -->
  <template v-else>
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
</template>
