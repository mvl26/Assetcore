<script setup lang="ts">
// DateTimeInput — text dd/mm/yyyy HH:mm + nút lịch.
// v-model là chuỗi datetime-local "yyyy-mm-ddTHH:mm" (drop-in cho <input type="datetime-local">).
import { useMaskedDateInput, dateTimeMaskConfig } from '@/composables/useMaskedDateInput'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  modelValue?: string | number | null
  id?: string
  required?: boolean
  disabled?: boolean
  min?: string
  max?: string
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'change', v: string): void
}>()

const { text, nativeRef, onInput, onBlur, onNativeChange, openPicker } =
  useMaskedDateInput(() => props.modelValue, emit, dateTimeMaskConfig)
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
      :placeholder="placeholder ?? 'dd/mm/yyyy HH:mm'"
      :required="required"
      :disabled="disabled"
      maxlength="16"
      style="padding-right: 2.25rem;"
      @input="onInput"
      @blur="onBlur"
    />
    <button
      type="button"
      class="absolute right-1.5 inline-flex h-7 w-7 items-center justify-center rounded text-gray-500 hover:text-gray-800 hover:bg-gray-100 disabled:cursor-not-allowed"
      :disabled="disabled"
      tabindex="-1"
      aria-label="Mở lịch"
      @click="openPicker(disabled ?? false)"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" />
        <path d="M16 2v4M8 2v4M3 10h18" />
      </svg>
    </button>
    <input
      ref="nativeRef"
      type="datetime-local"
      :value="String(modelValue ?? '')"
      :min="min"
      :max="max"
      :disabled="disabled"
      tabindex="-1"
      aria-hidden="true"
      class="sr-only"
      @change="onNativeChange"
    />
  </div>
</template>
