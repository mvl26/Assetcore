<script setup lang="ts">
// ToastContainer — render queue toast của useToast() ở top-right (fixed).
// Mount 1 lần ở App.vue để mọi nơi có thể gọi useToast().success/error/...
import { useToast, type ToastType } from '@/composables/useToast'

const { toasts } = useToast()

const TYPE_CFG: Record<ToastType, { bar: string; icon: string; emoji: string; ring: string }> = {
  success: { bar: 'bg-emerald-500',  icon: 'text-emerald-600',  emoji: '✓', ring: 'ring-emerald-200' },
  error:   { bar: 'bg-red-500',      icon: 'text-red-600',      emoji: '✕', ring: 'ring-red-200' },
  warning: { bar: 'bg-amber-500',    icon: 'text-amber-600',    emoji: '!', ring: 'ring-amber-200' },
  info:    { bar: 'bg-blue-500',     icon: 'text-blue-600',     emoji: 'i', ring: 'ring-blue-200' },
}

function dismiss(id: number) {
  toasts.value = toasts.value.filter(t => t.id !== id)
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none w-[360px] max-w-[calc(100vw-2rem)]">
      <TransitionGroup name="toast" tag="div" class="flex flex-col gap-2">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto bg-white rounded-lg shadow-lg ring-1 ring-black/5 overflow-hidden flex items-stretch"
          role="alert"
        >
          <div :class="['w-1 shrink-0', TYPE_CFG[t.type].bar]" />
          <div class="flex-1 px-4 py-3 flex items-start gap-3">
            <span
              :class="['shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ring-2', TYPE_CFG[t.type].icon, TYPE_CFG[t.type].ring]"
              aria-hidden="true"
            >{{ TYPE_CFG[t.type].emoji }}</span>
            <div class="flex-1 text-sm text-slate-700 leading-snug whitespace-pre-line">{{ t.message }}</div>
            <button
              type="button"
              class="shrink-0 text-slate-400 hover:text-slate-700 -mr-1"
              aria-label="Đóng thông báo"
              @click="dismiss(t.id)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all 200ms ease; }
.toast-enter-from { opacity: 0; transform: translateX(20px); }
.toast-leave-to   { opacity: 0; transform: translateX(20px); }
</style>
