<script setup lang="ts">
// Primitive tầng 0 — ADR-UX-04 (§3.3). Bọc class @layer .card / .card-sm / .card-interactive.
// A11y: khi có tiêu đề, khối được đặt tên bằng chính tiêu đề đó (aria-labelledby trỏ id
// CÓ THẬT) ⇒ trình đọc màn hình thông báo được ranh giới vùng nội dung, thay vì một
// <div> vô danh. Không tiêu đề ⇒ KHÔNG sinh aria-labelledby rỗng (trỏ id không tồn tại
// còn tệ hơn không khai).
import { computed, useId, useSlots } from 'vue'

const props = withDefaults(
  defineProps<{
    padding?: 'sm' | 'md'
    interactive?: boolean
    title?: string
  }>(),
  { padding: 'md', interactive: false, title: undefined },
)

const slots = useSlots()
const headingId = useId()

const hasHeading = computed(() => Boolean(props.title) || Boolean(slots.title))
const rootClass = computed(() => {
  if (props.interactive) return 'card-interactive'
  return props.padding === 'sm' ? 'card-sm' : 'card'
})
</script>

<template>
  <section
    :class="rootClass"
    :aria-labelledby="hasHeading ? headingId : undefined"
    data-testid="ui-card">
    <div v-if="hasHeading" class="flex items-start justify-between gap-3 mb-3">
      <h3 :id="headingId" class="text-base font-semibold text-neutral-700">
        <slot name="title">{{ title }}</slot>
      </h3>
      <div v-if="slots.actions" class="shrink-0">
        <slot name="actions" />
      </div>
    </div>
    <slot />
  </section>
</template>
