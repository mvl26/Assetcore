<script setup lang="ts">
// Primitive tầng 0 — ADR-UX-04 (§3.2). Nhãn chữ do caller truyền qua slot ⇒ 0 chuỗi
// tiếng Anh lọt vào primitive; màu LUÔN đi qua token ngữ nghĩa, không palette thô.
// KHÔNG đụng components/common/StatusBadge.vue (nó ánh xạ enum → nhãn VI qua
// utils/formatters.ts — hợp nhất 2 lớp là việc vòng sau, sổ AC-UX-038).
import { computed } from 'vue'

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'brand'
type Size = 'xs' | 'sm' | 'md'

const props = withDefaults(defineProps<{ tone?: Tone; size?: Size }>(), {
  tone: 'neutral',
  size: 'sm',
})

// Map TĨNH (JIT-safe). Chỉ dùng bậc 50/500/700 đã khai — xem bẫy deep-merge §2.5.
const TONE_CLASS: Record<Tone, string> = {
  neutral: 'bg-neutral-50 text-neutral-700',
  success: 'bg-success-50 text-success-700',
  warning: 'bg-warning-50 text-warning-700',
  danger: 'bg-danger-50 text-danger-700',
  info: 'bg-info-50 text-info-700',
  brand: 'bg-brand-50 text-brand-700',
}
// Sao ĐÚNG 3 bậc kích thước của StatusBadge.vue ⇒ 2 lớp badge không lệch pixel.
const SIZE_CLASS: Record<Size, string> = {
  xs: 'px-1.5 py-0.5 text-[10px]',
  sm: 'px-2.5 py-0.5 text-[11px]',
  md: 'px-3 py-1 text-xs',
}

const toneClass = computed(() => TONE_CLASS[props.tone])
const sizeClass = computed(() => SIZE_CLASS[props.size])
</script>

<template>
  <span
    class="inline-flex items-center font-medium rounded-full leading-none whitespace-nowrap"
    :class="[toneClass, sizeClass]"
    data-testid="ui-badge">
    <slot />
  </span>
</template>
