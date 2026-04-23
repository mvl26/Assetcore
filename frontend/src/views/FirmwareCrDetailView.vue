<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-09 Firmware CR Detail
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getFirmwareCr, updateFirmwareCr, type FirmwareCR } from '@/api/imm00'

const props = defineProps<{ id: string }>()
const router = useRouter()

const fcr = ref<FirmwareCR | null>(null)
const loading = ref(false)
const saving = ref(false)
const err = ref('')

async function load() {
  loading.value = true; err.value = ''
  try {
    const res = await getFirmwareCr(props.id)
    fcr.value = res as unknown as FirmwareCR
  } catch (e: unknown) {
    err.value = (e as Error).message || 'Không tải được dữ liệu'
  } finally { loading.value = false }
}

async function approve() {
  if (!fcr.value || !confirm('Phê duyệt yêu cầu này?')) return
  saving.value = true; err.value = ''
  try {
    await updateFirmwareCr(fcr.value.name, { status: 'Approved' })
    await load()
  } catch (e: unknown) {
    err.value = (e as Error).message || 'Không thể phê duyệt'
  } finally { saving.value = false }
}

async function markDeployed() {
  if (!fcr.value || !confirm('Xác nhận đã deploy firmware?')) return
  saving.value = true; err.value = ''
  try {
    await updateFirmwareCr(fcr.value.name, { status: 'Applied' })
    await load()
  } catch (e: unknown) {
    err.value = (e as Error).message || 'Không thể cập nhật trạng thái'
  } finally { saving.value = false }
}

const STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp',
  'Pending Approval': 'Chờ phê duyệt',
  Approved: 'Đã phê duyệt',
  Applied: 'Đã áp dụng',
  Rejected: 'Từ chối',
  'Rolled Back': 'Đã khôi phục',
}

function statusLabel(s?: string) { return (s && STATUS_LABELS[s]) || s || '—' }

function statusBadge(s?: string) {
  if (s === 'Approved') return 'bg-green-100 text-green-700'
  if (s === 'Applied') return 'bg-blue-100 text-blue-700'
  if (s === 'Rejected' || s === 'Rolled Back') return 'bg-red-100 text-red-700'
  if (s === 'Pending Approval') return 'bg-yellow-100 text-yellow-700'
  return 'bg-gray-100 text-gray-600'
}

const workflowSteps = [
  { key: 'Draft', label: 'Nháp' },
  { key: 'Approved', label: 'Phê duyệt' },
  { key: 'Applied', label: 'Đã deploy' },
]

const currentStepIdx = computed(() => {
  const s = fcr.value?.status
  if (s === 'Applied') return 2
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
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button class="text-gray-500 hover:text-gray-700 text-sm flex items-center gap-1" @click="router.push('/cm/firmware')">
          ← Quay lại
        </button>
        <span class="text-gray-300">|</span>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest">IMM-09 · FCR</p>
      </div>
    </div>

    <div v-if="loading" class="bg-white rounded-xl border p-10 text-center text-gray-400">Đang tải...</div>
    <div v-else-if="err" class="bg-red-50 text-red-700 text-sm p-4 rounded-xl border border-red-200">{{ err }}</div>

    <template v-else-if="fcr">
      <!-- Title + Status -->
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="font-mono text-xs text-gray-400 mb-1">{{ fcr.name }}</p>
            <h1 class="text-xl font-bold text-gray-900">
              Cập nhật Firmware — {{ fcr.asset_name || fcr.asset_ref }}
            </h1>
            <p class="text-sm text-gray-500 font-mono mt-0.5">{{ fcr.asset_ref }}</p>
          </div>
          <span :class="['px-3 py-1 rounded-full text-sm font-medium shrink-0', statusBadge(fcr.status)]">
            {{ statusLabel(fcr.status) }}
          </span>
        </div>

        <!-- Workflow Steps -->
        <div class="mt-5 flex items-center gap-0">
          <template v-for="(step, idx) in workflowSteps" :key="step.key">
            <div class="flex flex-col items-center">
              <div :class="[
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors',
                idx < currentStepIdx ? 'bg-green-500 border-green-500 text-white'
                : idx === currentStepIdx ? 'bg-blue-600 border-blue-600 text-white'
                : 'bg-white border-gray-300 text-gray-400'
              ]">
                <span v-if="idx < currentStepIdx">✓</span>
                <span v-else>{{ idx + 1 }}</span>
              </div>
              <p :class="['text-xs mt-1 font-medium', idx <= currentStepIdx ? 'text-gray-800' : 'text-gray-400']">
                {{ step.label }}
              </p>
            </div>
            <div v-if="idx < workflowSteps.length - 1"
              :class="['flex-1 h-0.5 mx-1 mb-5', idx < currentStepIdx ? 'bg-green-400' : 'bg-gray-200']" />
          </template>
        </div>
      </div>

      <!-- Info Section -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Thông tin chi tiết</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
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
            <p class="text-xs text-gray-400 mb-0.5">Phiếu sửa chữa liên kết</p>
            <p class="font-mono text-blue-600 text-xs">{{ fcr.asset_repair_wo }}</p>
          </div>
        </div>
      </div>

      <!-- Status Section -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Trạng thái xử lý</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-xs text-gray-400 mb-0.5">Người phê duyệt</p>
            <p class="text-gray-800">{{ fcr.approved_by || '—' }}</p>
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

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3">
        <button class="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
          @click="router.push('/cm/firmware')">Quay lại</button>
        <button v-if="fcr.status === 'Draft' || fcr.status === 'Pending Approval'"
          :disabled="saving"
          class="px-5 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
          @click="approve">
          {{ saving ? 'Đang xử lý...' : 'Phê duyệt' }}
        </button>
        <button v-else-if="fcr.status === 'Approved'"
          :disabled="saving"
          class="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
          @click="markDeployed">
          {{ saving ? 'Đang xử lý...' : 'Đã deploy' }}
        </button>
      </div>
    </template>
  </div>
</template>
