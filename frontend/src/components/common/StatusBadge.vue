<script setup lang="ts">
// Badge trạng thái dùng chung — wrapper trên global formatters.
// Tất cả label + màu đều đi qua src/utils/formatters.ts → single source of truth.
import { computed } from 'vue'
import { translateStatus, getStatusColor } from '@/utils/formatters'

const props = defineProps<{
  state: string
  size?: 'xs' | 'sm' | 'md'
}>()

const label = computed(() => translateStatus(props.state))
const colorClass = computed(() => getStatusColor(props.state))

const sizeClass = computed(() => {
  switch (props.size) {
    case 'xs': return 'px-1.5 py-0.5 text-[10px]'
    case 'md': return 'px-3 py-1 text-xs'
    default:   return 'px-2.5 py-0.5 text-[11px]'
  }
})
</script>

<template>
  <span
    class="inline-flex items-center font-medium rounded-full leading-none whitespace-nowrap"
    :class="[sizeClass, colorClass]"
  >
    {{ label }}
  </span>
</template>
