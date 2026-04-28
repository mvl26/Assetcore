<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Modal: gửi phiếu tiếp nhận đến người duyệt theo role của giai đoạn hiện tại.
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { submitForApproval } from '@/api/imm04'
import ApproverSelect from './ApproverSelect.vue'

const props = defineProps<{
  open: boolean
  commissioning: string
  workflowState: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submitted', result: { name: string; pending_approver: string; approval_stage: string }): void
}>()

interface StageInfo { stage: string; role: string; label: string }

const STATE_TO_STAGE: Record<string, StageInfo> = {
  'Draft':              { stage: 'Doc Verify',       role: 'Biomed Engineer', label: 'Kiểm tra tài liệu' },
  'Pending Doc Verify': { stage: 'Doc Verify',       role: 'Biomed Engineer', label: 'Kiểm tra tài liệu' },
  'To Be Installed':    { stage: 'Facility Check',   role: 'Biomed Engineer', label: 'Kiểm tra cơ sở hạ tầng' },
  'Installing':         { stage: 'Facility Check',   role: 'Biomed Engineer', label: 'Xác nhận lắp đặt' },
  'Identification':     { stage: 'Baseline Review',  role: 'Biomed Engineer', label: 'Duyệt định danh' },
  'Initial Inspection': { stage: 'Clinical Release', role: 'VP Block2',       label: 'Phê duyệt phát hành lâm sàng' },
  'Clinical Hold':      { stage: 'Clinical Release', role: 'VP Block2',       label: 'Gỡ giữ và phát hành' },
  'Re Inspection':      { stage: 'Baseline Review',  role: 'Biomed Engineer', label: 'Duyệt kiểm tra lại' },
}

const stageInfo = computed<StageInfo | null>(() => STATE_TO_STAGE[props.workflowState] ?? null)

const approver = ref('')
const remarks  = ref('')
const saving   = ref(false)
const error    = ref('')

function reset() {
  approver.value = ''
  remarks.value = ''
  error.value = ''
  saving.value = false
}

watch(() => props.open, (isOpen) => { if (isOpen) reset() })

async function onSubmit() {
  if (!approver.value) { error.value = 'Phải chọn người duyệt'; return }
  if (!stageInfo.value) { error.value = 'Trạng thái hiện tại không hỗ trợ gửi duyệt'; return }
  saving.value = true
  error.value = ''
  try {
    const result = await submitForApproval(
      props.commissioning, approver.value, stageInfo.value.stage, remarks.value,
    )
    emit('submitted', result)
    emit('close')
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi gửi duyệt'
  } finally {
    saving.value = false
  }
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open) emit('close')
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 bg-slate-900/50 z-50 flex items-center justify-center p-4"
      @click.self="emit('close')"
    >
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-semibold text-slate-900">Gửi duyệt phiếu tiếp nhận</h2>
            <p class="text-xs font-mono text-slate-500 mt-0.5">{{ commissioning }}</p>
          </div>
          <button class="text-slate-400 hover:text-slate-600 p-1" @click="emit('close')">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div v-if="stageInfo" class="bg-indigo-50 border border-indigo-200 rounded-lg p-3 text-sm">
          <p class="font-medium text-indigo-900">Giai đoạn: {{ stageInfo.label }}</p>
          <p class="text-xs text-indigo-700 mt-0.5">
            Người duyệt phải có vai trò: <b>{{ stageInfo.role }}</b>
          </p>
        </div>
        <div v-else class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
          Trạng thái <b>{{ workflowState }}</b> không hỗ trợ gửi duyệt.
        </div>

        <div v-if="stageInfo">
          <ApproverSelect
            v-model="approver"
            :role="stageInfo.role"
            label="Người duyệt"
            placeholder="Tìm theo tên hoặc email..."
            :required="true"
          />
        </div>

        <div>
          <label for="submit-remarks" class="form-label">Ghi chú gửi duyệt</label>
          <textarea
            id="submit-remarks"
            v-model="remarks"
            rows="3"
            class="form-input w-full text-sm"
            placeholder="Tóm tắt nội dung hoặc yêu cầu lưu ý..."
          />
        </div>

        <div v-if="error" class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2.5">
          {{ error }}
        </div>

        <div class="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <button class="btn-ghost" :disabled="saving" @click="emit('close')">Hủy</button>
          <button
            class="btn-primary"
            :disabled="saving || !approver || !stageInfo"
            @click="onSubmit"
          >
            {{ saving ? 'Đang gửi...' : 'Gửi duyệt' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
