<script setup lang="ts">
// Primitive tầng 0 — ADR-UX-04 (§3.7). Một KHỐI shimmer nguyên tử bọc class @layer .skeleton.
// Kích thước/bo góc do caller truyền qua fallthrough (class/style) ⇒ thay thế các
// `<div class="skeleton …">` trong SkeletonLoader.vue KHÔNG đổi một pixel.
// aria-hidden: khối trang trí, không có nội dung để đọc; aria-busy báo vùng đang nạp.
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** > 1 ⇒ render bấy nhiêu khối trong một hộp chung */
    lines?: number
    width?: string
    height?: string
    rounded?: string
  }>(),
  { lines: 1, width: undefined, height: undefined, rounded: undefined },
)

const multiline = computed(() => (props.lines ?? 1) > 1)
const blockStyle = computed(() => ({ width: props.width, height: props.height }))
</script>

<template>
  <div
    v-if="multiline"
    class="space-y-2"
    aria-busy="true"
    data-testid="ui-skeleton">
    <div
      v-for="i in lines"
      :key="i"
      class="skeleton"
      :class="rounded"
      :style="blockStyle"
      aria-hidden="true"
      data-testid="ui-skeleton-line" />
  </div>
  <div
    v-else
    class="skeleton"
    :class="rounded"
    :style="blockStyle"
    aria-busy="true"
    aria-hidden="true"
    data-testid="ui-skeleton" />
</template>
