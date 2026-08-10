<script setup lang="ts">
// Primitive tầng 0 — ADR-UX-04 (docs/ui-ux/01_DESIGN_SYSTEM.md §3.1).
// Luật no-fork: BỌC class @layer components sẵn có trong main.css (.btn-*), KHÔNG chép
// lại chuỗi utility của chúng ⇒ đổi 1 chỗ trong main.css là toàn hệ đổi theo.
// Nợ a11y bắt tại gốc: nút chỉ có biểu tượng mà thiếu nhãn cho trình đọc màn hình sẽ
// bị cảnh báo ngay lúc mount (AC-UX-002 — 87/135 màn đang thiếu nhãn a11y).
import { computed, onMounted } from 'vue'

type Variant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
type Size = 'sm' | 'md'

const props = withDefaults(
  defineProps<{
    variant?: Variant
    size?: Size
    /** mặc định 'button' để không vô tình gửi form khi đặt trong <form> */
    type?: 'button' | 'submit'
    disabled?: boolean
    loading?: boolean
    /** nút chỉ có biểu tượng — BẮT BUỘC kèm ariaLabel */
    iconOnly?: boolean
    ariaLabel?: string
  }>(),
  {
    variant: 'secondary',
    size: 'md',
    type: 'button',
    disabled: false,
    loading: false,
    iconOnly: false,
    ariaLabel: undefined,
  },
)

const emit = defineEmits<{ (e: 'click', ev: MouseEvent): void }>()

// Map TĨNH — Tailwind JIT chỉ quét chuỗi literal, nội suy `btn-${variant}` sẽ bị purge.
const VARIANT_CLASS: Record<Variant, string> = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  danger: 'btn-danger',
  success: 'btn-success',
  ghost: 'btn-ghost',
}
const SIZE_CLASS: Record<Size, string> = {
  sm: 'text-sm px-3 py-1.5',
  md: '',
}

const blocked = computed(() => props.disabled || props.loading)
const rootClass = computed(() => [
  VARIANT_CLASS[props.variant],
  SIZE_CLASS[props.size],
  props.iconOnly ? 'px-2' : '',
])

function onClick(ev: MouseEvent): void {
  if (blocked.value) return
  emit('click', ev)
}

onMounted(() => {
  if (props.iconOnly && !props.ariaLabel) {
    console.warn(
      '[ui/Button] Nút chỉ có biểu tượng phải kèm prop ariaLabel — trình đọc màn hình sẽ đọc rỗng nếu thiếu.',
    )
  }
})
</script>

<template>
  <button
    :type="type"
    :class="rootClass"
    :disabled="blocked"
    :aria-disabled="blocked ? 'true' : undefined"
    :aria-busy="loading ? 'true' : undefined"
    :aria-label="ariaLabel"
    data-testid="ui-button"
    @click="onClick">
    <slot />
  </button>
</template>
