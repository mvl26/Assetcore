<script setup lang="ts">
defineProps<{
  title: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  danger?: boolean
}>()

const emit = defineEmits<{ close: [] }>()

function onClose() { emit('close') }

// Size cap chỉ áp ở sm:+ (mobile full-screen w-full không bị max-w giới hạn — D3).
const sizeClass: Record<string, string> = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-md',
  lg: 'sm:max-w-lg',
  xl: 'sm:max-w-2xl',
}
</script>

<template>
  <Teleport to="body">
    <!-- Overlay. Mobile: stretch (modal full-screen); sm:+ : centered card (ADR-IMM00-RESPONSIVE D3). -->
    <div
      class="fixed inset-0 z-50 flex items-stretch justify-center sm:items-center sm:justify-center sm:p-4"
      style="background: rgba(0,0,0,0.45)"
      @click.self="onClose"
    >
      <div
        data-testid="modal-card"
        :class="[
          'bg-white shadow-2xl flex flex-col',
          // Mobile (base): full-screen — inset-0 w-full h-full rounded-none, không tràn.
          'inset-0 w-full h-full rounded-none max-h-screen',
          // sm:+ : centered card (giữ pattern desktop hiện hữu).
          'sm:inset-auto sm:m-auto sm:w-full sm:rounded-2xl sm:h-auto sm:max-h-[90vh]',
          sizeClass[size ?? 'md'],
        ]"
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
            data-testid="modal-close"
            aria-label="Đóng"
            class="min-h-[44px] min-w-[44px] -mr-2 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            @click="onClose"
          >
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="w-5 h-5">
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
