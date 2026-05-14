<script setup lang="ts">
defineProps<{
  title: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  danger?: boolean
}>()

const emit = defineEmits<{ close: [] }>()

function onClose() { emit('close') }

const sizeClass: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      style="background: rgba(0,0,0,0.45)"
      @click.self="onClose"
    >
      <div
        :class="['bg-white rounded-2xl shadow-2xl w-full flex flex-col', sizeClass[size ?? 'md']]"
        style="max-height: 90vh"
      >
        <!-- Header -->
        <div
          class="flex items-center justify-between px-6 py-4 shrink-0"
          :class="danger ? 'border-b border-red-100' : 'border-b border-slate-100'"
        >
          <h2
            class="text-lg font-semibold"
            :class="danger ? 'text-red-700' : 'text-slate-800'"
          >
            {{ title }}
          </h2>
          <button
            class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            @click="onClose"
          >
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto px-6 py-5">
          <slot />
        </div>

        <!-- Footer -->
        <div v-if="$slots.footer" class="px-6 py-4 border-t border-slate-100 shrink-0 flex justify-end gap-3">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
