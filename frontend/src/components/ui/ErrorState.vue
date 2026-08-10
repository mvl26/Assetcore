<script setup lang="ts">
// Primitive tầng 0 — ADR-UX-04 (§3.6). Trả nợ "lỗi câm" của audit: 83/135 màn không có
// lối thử lại khi nạp hỏng ⇒ người dùng thấy trang trắng, không biết làm gì tiếp.
// Bất biến: message rỗng KHÔNG bao giờ để lộ chuỗi kỹ thuật (traceback / 'undefined'),
// mà rơi về một câu tiếng Việt trung tính.
// KHÔNG mang ngữ nghĩa 'notfound'/'forbidden' — đó là components/common/DetailLoadError.vue
// (CR-74) và nhãn nút thử lại của 2 lớp phải TRÙNG NHAU (guard trong ErrorState.test.ts).
import { computed } from 'vue'
import Button from './Button.vue'

const props = withDefaults(
  defineProps<{
    message?: string
    hint?: string
    retryable?: boolean
    retryLabel?: string
  }>(),
  {
    message: '',
    hint: 'Vui lòng thử lại hoặc tải lại trang.',
    retryable: true,
    retryLabel: 'Thử lại',
  },
)

const emit = defineEmits<{ (e: 'retry'): void }>()

const displayMessage = computed(() => props.message?.trim() || 'Không tải được dữ liệu.')
</script>

<template>
  <div class="card p-8 text-center space-y-3" role="alert" data-testid="ui-error">
    <p class="text-base font-medium text-neutral-700" data-testid="ui-error-message">
      {{ displayMessage }}
    </p>
    <p v-if="hint" class="text-sm text-neutral-500">{{ hint }}</p>
    <div class="flex items-center justify-center gap-2">
      <Button
        v-if="retryable"
        variant="ghost"
        size="sm"
        data-testid="ui-error-retry"
        @click="emit('retry')">
        {{ retryLabel }}
      </Button>
      <slot name="action" />
    </div>
  </div>
</template>
