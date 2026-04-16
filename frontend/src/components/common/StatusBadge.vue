<script setup lang="ts">
import { computed } from 'vue'
import { getStateConfig } from '@/composables/useWorkflow'
import type { WorkflowState } from '@/types/imm04'

const props = defineProps<{
  state: WorkflowState | string
  size?: 'sm' | 'md' | 'lg'
}>()

const config = computed(() => getStateConfig(props.state as WorkflowState))

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'px-2 py-0.5 text-xs'
    case 'lg':
      return 'px-3 py-1.5 text-sm'
    default:
      return 'px-2.5 py-1 text-xs'
  }
})
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1 font-medium rounded-full',
      config.badgeClass,
      sizeClass,
    ]"
  >
    <span class="w-1.5 h-1.5 rounded-full bg-current opacity-70" />
    {{ config.label }}
  </span>
</template>
