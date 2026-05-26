<script setup lang="ts">
// NotificationModal — blocking dialog cho severity 'critical' và confirm() prompts.
// Mount 1 lần ở App.vue song song với ToastContainer.
//
// Render queue từ useModal() — chỉ hiển thị item đầu tiên (FIFO).
// ESC + click backdrop = dismiss với ok=false (alert resolve void).
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useModal, type ModalRequest } from '@/composables/useModal'

const { queue, dismiss } = useModal()

const current = computed<ModalRequest | undefined>(() => queue.value[0])

const TONE_CFG: Record<NonNullable<ModalRequest['tone']>, { bar: string; icon: string; emoji: string }> = {
  error:    { bar: 'bg-red-500',    icon: 'text-red-600',    emoji: '✕' },
  warning:  { bar: 'bg-amber-500',  icon: 'text-amber-600',  emoji: '!' },
  info:     { bar: 'bg-blue-500',   icon: 'text-blue-600',   emoji: 'i' },
  critical: { bar: 'bg-red-600',    icon: 'text-red-700',    emoji: '⚠' },
}

function cfg(req: ModalRequest) {
  return TONE_CFG[req.tone ?? 'critical']
}

function onConfirm() {
  if (current.value) dismiss(current.value.id, true)
}

function onCancel() {
  if (!current.value) return
  // alert → resolve void; confirm → resolve false. ok=false works for both.
  dismiss(current.value.id, false)
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') onCancel()
}

onMounted(() => globalThis.addEventListener('keydown', onKey))
onBeforeUnmount(() => globalThis.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="current"
        class="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-slate-900/50"
        role="dialog"
        aria-modal="true"
        @click.self="onCancel"
      >
        <div class="w-full max-w-md bg-white rounded-lg shadow-xl overflow-hidden flex flex-col">
          <div :class="['h-1', cfg(current).bar]" />
          <div class="p-6 flex items-start gap-4">
            <span
              :class="['shrink-0 inline-flex items-center justify-center w-10 h-10 rounded-full text-lg font-bold ring-2 ring-current/20 bg-current/5', cfg(current).icon]"
              aria-hidden="true"
            >{{ cfg(current).emoji }}</span>
            <div class="flex-1 min-w-0">
              <h2 class="text-base font-semibold text-slate-900 mb-1">{{ current.title }}</h2>
              <p class="text-sm text-slate-700 whitespace-pre-line">{{ current.body }}</p>
              <p
                v-if="current.actionHint"
                class="mt-2 text-xs text-slate-500 italic"
              >
                {{ current.actionHint }}
              </p>
            </div>
          </div>
          <div class="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-2">
            <button
              v-if="current.kind === 'confirm'"
              type="button"
              class="px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50"
              @click="onCancel"
            >
              {{ current.cancelText }}
            </button>
            <button
              type="button"
              :class="[
                'px-3 py-1.5 text-sm font-semibold text-white rounded-md',
                current.tone === 'critical' || current.tone === 'error' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700',
              ]"
              @click="onConfirm"
            >
              {{ current.kind === 'confirm' ? current.confirmText : 'Đã hiểu' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 150ms ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
