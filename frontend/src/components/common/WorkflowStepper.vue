<script setup lang="ts">
// WorkflowStepper — hiển thị tiến trình state machine dạng node→node.
// Dùng cho IMM-11 Calibration + IMM-12 Incident detail (mockup docs/fe/*/[detail].html).
// Caller cấp `steps` (mã BE) + `labelFor` (map sang nhãn VN) → no EN leak.
import { computed } from 'vue'

const props = defineProps<{
  steps: string[]
  current: string
  labelFor: (s: string) => string
}>()

const currentIndex = computed(() => props.steps.indexOf(props.current))

function nodeState(i: number): 'done' | 'current' | 'todo' {
  // Nếu current không nằm trong steps (vd nhánh RCA Required) → coi như chưa tới Closed.
  const idx = currentIndex.value
  if (idx === -1) return i === props.steps.length - 1 ? 'todo' : 'done'
  if (i < idx) return 'done'
  if (i === idx) return 'current'
  return 'todo'
}
</script>

<template>
  <div class="flex items-center flex-wrap gap-1" data-testid="workflow-stepper">
    <template v-for="(s, i) in steps" :key="s">
      <div
        class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
        :class="{
          'bg-emerald-100 text-emerald-700': nodeState(i) === 'done',
          'bg-blue-600 text-white': nodeState(i) === 'current',
          'bg-slate-100 text-slate-400': nodeState(i) === 'todo',
        }"
        :data-state="nodeState(i)"
      >
        <span
          class="w-4 h-4 rounded-full flex items-center justify-center text-[10px]"
          :class="nodeState(i) === 'current' ? 'bg-white/30' : ''"
        >
          <span v-if="nodeState(i) === 'done'">✓</span>
          <span v-else>{{ i + 1 }}</span>
        </span>
        {{ labelFor(s) }}
      </div>
      <span v-if="i < steps.length - 1" class="text-slate-300">→</span>
    </template>
  </div>
</template>
