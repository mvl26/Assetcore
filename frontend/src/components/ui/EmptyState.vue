<script setup lang="ts">
// Primitive tầng 0 — ADR-UX-04 (§3.5). Trả nợ "khung rỗng câm" của audit §7.2:
// 26/135 màn hiện không có trạng thái rỗng, hoặc chỉ in một câu cụt (vd '/dashboard').
// Bất biến: LUÔN có câu tiếng Việt đầy đủ; có lối thoát khi caller truyền hành động.
import { computed, useSlots } from 'vue'
import Button from './Button.vue'

const props = withDefaults(
  defineProps<{
    title?: string
    /** câu gợi ý phía dưới tiêu đề */
    description?: string
    /** bí danh cũ của `description` (giữ để caller đã viết `hint` không vỡ) */
    hint?: string
    /** có nhãn ⇒ hiện nút mặc định phát sự kiện 'action' */
    actionLabel?: string
  }>(),
  {
    title: 'Chưa có dữ liệu',
    description: undefined,
    hint: undefined,
    actionLabel: undefined,
  },
)

const emit = defineEmits<{ (e: 'action'): void }>()

const slots = useSlots()
const descriptionText = computed(() => props.description ?? props.hint)
const hasAction = computed(() => Boolean(props.actionLabel) || Boolean(slots.action))
</script>

<template>
  <div class="card p-8 text-center space-y-2" role="status" data-testid="ui-empty">
    <p class="text-base font-medium text-neutral-700" data-testid="ui-empty-title">{{ title }}</p>
    <p
      v-if="descriptionText"
      class="text-sm text-neutral-500"
      data-testid="ui-empty-description">
      {{ descriptionText }}
    </p>
    <slot />
    <div v-if="hasAction" class="pt-2">
      <slot name="action">
        <Button variant="secondary" size="sm" data-testid="ui-empty-action" @click="emit('action')">
          {{ actionLabel }}
        </Button>
      </slot>
    </div>
  </div>
</template>
