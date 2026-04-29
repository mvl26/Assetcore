<script setup lang="ts">
import { ref, computed } from 'vue'
import { useWorkflow } from '@/composables/useWorkflow'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { WorkflowState, WorkflowTransition } from '@/types/imm04'

const props = defineProps<{
  currentState: WorkflowState
  allowedTransitions: WorkflowTransition[]
  isLocked: boolean
  canSubmit?: boolean
  loading?: boolean
  // GW-2: compliance gate
  imm05IsCompliant?: boolean
}>()

const emit = defineEmits<{
  (e: 'transition', action: string): void
  (e: 'submit'): void
}>()

const { filteredActions, getActionConfig } = useWorkflow(
  () => props.currentState,
  () => props.allowedTransitions,
)

// Confirmation dialog state
const confirmAction = ref<string | null>(null)
const confirmMessage = ref('')
const processing = ref(false)

function handleActionClick(action: string) {
  const config = getActionConfig(action)
  if (config.requiresConfirm || config.requireConfirm) {
    confirmAction.value = action
    confirmMessage.value = config.confirmMessage ?? `Bạn có chắc muốn thực hiện "${config.label}"?`
  } else {
    doTransition(action)
  }
}

async function doTransition(action: string) {
  confirmAction.value = null
  processing.value = true
  try {
    emit('transition', action)
  } finally {
    processing.value = false
  }
}

function cancelConfirm() {
  confirmAction.value = null
  confirmMessage.value = ''
}

const isProcessing = computed(() => props.loading || processing.value)

const hasActions = computed(() => filteredActions.value.length > 0 || props.canSubmit)

// GW-2: chặn Submit nếu chưa compliant (chỉ áp dụng ở Clinical_Release)
const gw2Block = computed(() =>
  props.canSubmit &&
  props.currentState === 'Clinical_Release' &&
  props.imm05IsCompliant === false
)
</script>

<template>
  <div>
    <!-- No actions available -->
    <div v-if="!hasActions && !isLocked" class="text-sm text-gray-500 italic">
      Không có hành động nào khả dụng với vai trò hiện tại.
    </div>

    <!-- Locked state -->
    <div v-if="isLocked" class="flex items-center gap-2 text-sm text-green-700 bg-green-50 px-4 py-2 rounded-md border border-green-200">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
      Phiếu đã được Submit và không thể chỉnh sửa.
    </div>

    <!-- Action buttons -->
    <div v-else-if="hasActions" class="flex flex-wrap gap-3">
      <!-- Loading overlay -->
      <div v-if="isProcessing" class="flex items-center gap-2 text-sm text-gray-500">
        <LoadingSpinner size="sm" />
        <span>Đang xử lý...</span>
      </div>

      <template v-else>
        <!-- Workflow transition buttons -->
        <button
          v-for="transition in filteredActions"
          :key="transition.action"
          :class="['btn', getActionConfig(transition.action).buttonClass ?? `btn-${getActionConfig(transition.action).variant}`]"
          @click="handleActionClick(transition.action)"
        >
          {{ getActionConfig(transition.action).label }}
          <span class="text-xs opacity-70">(→ {{ transition.next_state }})</span>
        </button>

        <!-- GW-2 warning banner (trước nút Submit khi chưa compliant) -->
        <div
          v-if="gw2Block"
          class="flex items-start gap-2 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 max-w-sm"
        >
          <svg class="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>
            <strong>GW-2 Blocked:</strong> Hồ sơ chưa đạt chuẩn.
            Vui lòng bổ sung tài liệu bắt buộc trước khi Submit.
          </span>
        </div>

        <!-- Submit button (separate, higher prominence) -->
        <div class="relative group">
          <button
            v-if="canSubmit"
            class="btn text-white ring-2"
            :class="gw2Block
              ? 'bg-gray-400 cursor-not-allowed ring-gray-200 opacity-70'
              : 'bg-emerald-600 hover:bg-emerald-700 ring-emerald-300'"
            :disabled="gw2Block"
            @click="!gw2Block && emit('submit')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Submit & Kích hoạt Tài sản
          </button>
          <!-- Tooltip khi bị block -->
          <div
            v-if="gw2Block"
            class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50"
          >
            Cần hoàn thiện hồ sơ trước. Vào tab "Kết quả triển khai" để xem chi tiết.
            <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
          </div>
        </div>
      </template>
    </div>

    <!-- Confirmation Dialog -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="confirmAction"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
        >
          <div class="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
            <div class="flex items-start gap-4">
              <div class="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div class="flex-1">
                <h3 class="text-base font-semibold text-gray-900 mb-2">Xác nhận hành động</h3>
                <p class="text-sm text-gray-600">{{ confirmMessage }}</p>
              </div>
            </div>

            <div class="flex gap-3 mt-6 justify-end">
              <button class="btn-secondary" @click="cancelConfirm">Hủy</button>
              <button
                class="btn bg-yellow-600 hover:bg-yellow-700 text-white"
                @click="doTransition(confirmAction!)"
              >
                Xác nhận
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
