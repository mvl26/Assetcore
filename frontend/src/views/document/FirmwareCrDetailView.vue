<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team Firmware CR Detail
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getFirmwareCr, transitionFirmwareCr, type FirmwareCR } from '@/api/imm00'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { useApi } from '@/composables/useApi'
import { useNotify } from '@/composables/useNotify'

const props = defineProps<{ id: string }>()
const router = useRouter()
const { run, loading: acting } = useApi()
const notify = useNotify()

const fcr = ref<FirmwareCR | null>(null)
const loading = ref(false)
const err = ref('')

async function load() {
  loading.value = true; err.value = ''
  try {
    fcr.value = await getFirmwareCr(props.id)
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Không tải được dữ liệu'
  } finally { loading.value = false }
}

// ── Server-driven CTA (GATE-8 / LL-FE-51) ────────────────────────────────────
// Ground truth = allowed_transitions từ BE (_FCR_VALID_TRANSITIONS đã LỌC theo
// capability caller) + cờ can_approve. KHÔNG suy nút từ `fcr.status` thô — đó là
// dead-gate (Repair User tự "Duyệt" nhảy-cóc). `status` chỉ dùng cho badge/stepper.
const allowedTransitions = computed<string[]>(() => fcr.value?.allowed_transitions ?? [])
const canApprove = computed(() =>
  allowedTransitions.value.includes('Approved') && fcr.value?.can_approve === true,
)
const canDeploy = computed(() => allowedTransitions.value.includes('Applied'))
const canRollback = computed(() => allowedTransitions.value.includes('Rolled Back'))

async function approve() {
  if (!fcr.value) return
  const ok = await notify.confirm({
    title: 'Phê duyệt yêu cầu thay đổi firmware',
    body: `Xác nhận phê duyệt ${fcr.value.name}? Trạng thái sẽ chuyển sang "Đã phê duyệt".`,
    confirmText: 'Phê duyệt',
  })
  if (!ok) return
  const res = await run(() => transitionFirmwareCr(fcr.value!.name, 'approve'), {
    successMessage: 'Đã phê duyệt yêu cầu thay đổi firmware',
  })
  if (res) await load()
}

async function markDeployed() {
  if (!fcr.value) return
  const ok = await notify.confirm({
    title: 'Xác nhận triển khai firmware',
    body: `Xác nhận đã triển khai firmware cho ${fcr.value.asset_name || fcr.value.asset_ref}?`,
    confirmText: 'Đã triển khai',
  })
  if (!ok) return
  const res = await run(() => transitionFirmwareCr(fcr.value!.name, 'deploy'), {
    successMessage: 'Đã ghi nhận triển khai firmware',
  })
  if (res) await load()
}

// ── Rollback (khôi phục firmware) — cần lý do cho audit NĐ98 ──────────────────
const showRollback = ref(false)
const rollbackReason = ref('')
const rollbackErr = ref('')

function openRollback() {
  rollbackReason.value = ''
  rollbackErr.value = ''
  showRollback.value = true
}

async function submitRollback() {
  if (!fcr.value) return
  if (!rollbackReason.value.trim()) {
    rollbackErr.value = 'Vui lòng nhập lý do khôi phục.'
    return
  }
  const res = await run(
    () => transitionFirmwareCr(fcr.value!.name, 'rollback', rollbackReason.value.trim()),
    { successMessage: 'Đã ghi nhận khôi phục firmware' },
  )
  if (res) {
    showRollback.value = false
    await load()
  }
}

const workflowSteps = [
  { key: 'Draft', label: 'Nháp' },
  { key: 'Approved', label: 'Phê duyệt' },
  { key: 'Applied', label: 'Đã triển khai' },
]

const currentStepIdx = computed(() => {
  const s = fcr.value?.status
  if (s === 'Applied' || s === 'Rolled Back') return 2
  if (s === 'Approved') return 1
  return 0
})

function fmtDate(d?: string | null) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      :title="fcr ? `Cập nhật Firmware — ${fcr.asset_name || fcr.asset_ref}` : (props.id ?? 'Yêu cầu cập nhật firmware')"
      :subtitle="fcr ? fcr.name : 'Yêu cầu cập nhật firmware'"
      :back-to="'/cm/firmware'"
      back-label="← Danh sách yêu cầu thay đổi firmware"
      :breadcrumb="[
        { label: 'IMM-09 · Sửa chữa', to: '/cm/dashboard' },
        { label: 'Firmware', to: '/cm/firmware' },
        { label: props.id },
      ]"
    >
      <template #actions>
        <StatusBadge v-if="fcr?.status" :state="fcr.status" size="md" />
      </template>
    </PageHeader>

    <div v-if="loading" class="bg-white rounded-xl border p-10 text-center text-slate-400">Đang tải…</div>
    <div v-else-if="err" class="bg-red-50 text-red-700 text-sm p-4 rounded-xl border border-red-200">{{ err }}</div>

    <template v-else-if="fcr">
      <!-- Workflow steps card -->
      <div class="bg-white rounded-xl border border-slate-200 p-5">

        <!-- Workflow Steps -->
        <div class="mt-5 flex items-center gap-0">
          <template v-for="(step, idx) in workflowSteps" :key="step.key">
            <div class="flex flex-col items-center">
              <div
:class="[
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors',
                idx < currentStepIdx ? 'bg-green-500 border-green-500 text-white'
                : idx === currentStepIdx ? 'bg-blue-600 border-blue-600 text-white'
                : 'bg-white border-gray-300 text-gray-400'
              ]">
                <svg v-if="idx < currentStepIdx" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
                <span v-else>{{ idx + 1 }}</span>
              </div>
              <p :class="['text-xs mt-1 font-medium', idx <= currentStepIdx ? 'text-gray-800' : 'text-gray-400']">
                {{ step.label }}
              </p>
            </div>
            <div
v-if="idx < workflowSteps.length - 1"
              :class="['flex-1 h-0.5 mx-1 mb-5', idx < currentStepIdx ? 'bg-green-400' : 'bg-gray-200']" />
          </template>
        </div>
      </div>

      <!-- Info Section -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Thông tin chi tiết</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <!-- Linked asset -->
          <div class="sm:col-span-2">
            <p class="text-xs text-gray-400 mb-0.5">Thiết bị</p>
            <button
              v-if="fcr.asset_ref"
              class="font-medium text-blue-600 hover:text-blue-800 hover:underline underline-offset-2 text-left"
              @click="router.push(`/assets/${fcr.asset_ref}`)"
            >{{ fcr.asset_name || fcr.asset_ref }}</button>
            <span v-else class="text-gray-500">—</span>
            <span v-if="fcr.asset_name && fcr.asset_ref" class="ml-2 text-xs font-mono text-gray-400">{{ fcr.asset_ref }}</span>
          </div>
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Phiên bản trước</p>
            <p class="font-mono font-medium text-gray-800">{{ fcr.version_before || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Phiên bản mới</p>
            <p class="font-mono font-medium text-blue-700">{{ fcr.version_after || '—' }}</p>
          </div>
          <div class="col-span-2">
            <p class="text-xs text-gray-400 mb-0.5">Nguồn tham chiếu</p>
            <p class="text-gray-700">{{ fcr.source_reference || '—' }}</p>
          </div>
          <div class="col-span-2">
            <p class="text-xs text-gray-400 mb-0.5">Nội dung thay đổi</p>
            <p class="text-gray-700 whitespace-pre-wrap">{{ fcr.change_notes || '—' }}</p>
          </div>
          <div v-if="fcr.asset_repair_wo">
            <p class="text-xs text-gray-400 mb-0.5">Lệnh sửa chữa liên kết</p>
            <button
              class="font-mono text-blue-600 text-xs hover:text-blue-800 hover:underline underline-offset-2"
              @click="router.push(`/cm/work-orders/${fcr.asset_repair_wo}`)"
            >{{ fcr.asset_repair_wo }}</button>
          </div>
        </div>
      </div>

      <!-- Status Section -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Trạng thái xử lý</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Người phê duyệt</p>
            <p class="text-gray-800">{{ fcr.approved_by_name || fcr.approved_by || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Ngày phê duyệt</p>
            <p class="text-gray-800">{{ fmtDate(fcr.approved_datetime) }}</p>
          </div>
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Ngày áp dụng</p>
            <p class="text-gray-800">{{ fmtDate(fcr.applied_datetime) }}</p>
          </div>
          <div v-if="fcr.rollback_reason" class="col-span-2">
            <p class="text-xs text-gray-400 mb-0.5">Lý do khôi phục</p>
            <p class="text-red-700">{{ fcr.rollback_reason }}</p>
          </div>
        </div>
      </div>

      <!-- Actions — gate 100% theo allowed_transitions + can_approve (server-driven,
           GATE-8/LL-FE-51). KHÔNG hardcode fcr.status==='X' trên nút. -->
      <div class="flex flex-wrap items-center justify-end gap-3">
        <button
          class="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="router.push('/cm/firmware')"
        >
          Quay lại
        </button>
        <button
          v-if="canRollback"
          data-testid="cta-rollback"
          :disabled="acting"
          class="px-4 py-2 border border-red-300 text-red-700 rounded-lg text-sm hover:bg-red-50 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
          @click="openRollback"
        >
          Khôi phục firmware
        </button>
        <button
          v-if="canApprove"
          data-testid="cta-approve"
          :disabled="acting"
          class="btn-primary text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="approve"
        >
          {{ acting ? 'Đang xử lý…' : 'Phê duyệt' }}
        </button>
        <button
          v-if="canDeploy"
          data-testid="cta-deploy"
          :disabled="acting"
          class="btn-primary text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="markDeployed"
        >
          {{ acting ? 'Đang xử lý…' : 'Đã triển khai' }}
        </button>
        <p
          v-if="!canApprove && !canDeploy && !canRollback"
          class="text-xs text-gray-400"
          data-testid="no-actions-hint"
        >
          Không có hành động khả dụng cho vai trò / trạng thái hiện tại.
        </p>
      </div>
    </template>

    <!-- Rollback modal — thu thập lý do khôi phục (audit NĐ98) -->
    <BaseModal v-if="showRollback" title="Khôi phục firmware" danger @close="showRollback = false">
      <div class="space-y-3 text-sm">
        <p class="text-gray-600">
          Ghi nhận khôi phục phiên bản firmware về trạng thái trước. Hành động này được
          lưu vết (Lifecycle Event) và không thể hoàn tác.
        </p>
        <div>
          <label for="rollback-reason" class="block text-xs font-medium text-gray-500 mb-1">
            Lý do khôi phục <span class="text-red-500">*</span>
          </label>
          <textarea
            id="rollback-reason"
            v-model="rollbackReason"
            rows="3"
            :aria-invalid="!!rollbackErr"
            aria-describedby="rollback-reason-err"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
            placeholder="Nêu rõ nguyên nhân cần khôi phục firmware…"
          />
          <p v-if="rollbackErr" id="rollback-reason-err" class="mt-1 text-xs text-red-600">{{ rollbackErr }}</p>
        </div>
      </div>
      <template #footer>
        <button
          class="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="showRollback = false"
        >
          Hủy
        </button>
        <button
          data-testid="rollback-submit"
          :disabled="acting"
          class="px-4 py-2 rounded-lg text-sm text-white bg-red-600 hover:bg-red-700 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
          @click="submitRollback"
        >
          {{ acting ? 'Đang xử lý…' : 'Xác nhận khôi phục' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
