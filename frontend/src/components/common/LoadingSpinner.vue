<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  size?: 'sm' | 'md' | 'lg'
  label?: string
  overlay?: boolean
}>()

const spinnerSize = computed(() => {
  switch (props.size) {
    case 'sm': return 'w-4 h-4'
    case 'lg': return 'w-10 h-10'
    default: return 'w-6 h-6'
  }
})
</script>

<template>
  <div
    :class="[
      'flex flex-col items-center justify-center gap-3',
      overlay ? 'fixed inset-0 bg-white/80 z-50' : '',
    ]"
  >
    <svg
      :class="['animate-spin text-blue-600', spinnerSize]"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
    <p v-if="label" class="text-sm text-gray-500">{{ label }}</p>
  </div>
</template>
