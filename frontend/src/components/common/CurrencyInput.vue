<script setup lang="ts">
// CurrencyInput — ô nhập số tiền VND, hiển thị phân nhóm hàng nghìn KIỂU VIỆT
// NAM (1.000.000) ngay khi gõ. Drop-in replacement cho
// <input type="number" v-model.number="...">: v-model là number | null SẠCH
// (submit thẳng cho BE Currency, KHÔNG chuỗi). $attrs (class/id/placeholder…)
// đổ xuống <input> trong (inheritAttrs:false) — giữ y nguyên style form-input.
import { useThousandsInput } from '@/composables/useThousandsInput'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  modelValue?: number | null
  id?: string
  required?: boolean
  disabled?: boolean
  placeholder?: string
  ariaLabel?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: number | null): void
  (e: 'change', v: number | null): void
}>()

const { text, onInput, onBlur } = useThousandsInput(() => props.modelValue, emit)
</script>

<template>
  <div class="relative inline-flex w-full items-center" :class="disabled ? 'opacity-60' : ''">
    <input
      v-bind="$attrs"
      :id="id"
      v-model="text"
      type="text"
      inputmode="numeric"
      autocomplete="off"
      :placeholder="placeholder ?? '0'"
      :required="required"
      :disabled="disabled"
      :aria-label="ariaLabel"
      style="padding-right: 2rem;"
      @input="onInput"
      @blur="onBlur"
    />
    <span
      class="pointer-events-none absolute right-2.5 select-none text-xs font-medium text-gray-400"
      aria-hidden="true"
    >₫</span>
  </div>
</template>
