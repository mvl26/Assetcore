<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team Firmware CR Detail
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getFirmwareCr, updateFirmwareCr, type FirmwareCR } from '@/api/imm00'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()

const fcr = ref<FirmwareCR | null>(null)
const loading = ref(false)
const saving = ref(false)
const err = ref('')

async function load() {
  loading.value = true; err.value = ''
  try {
    fcr.value = await getFirmwareCr(props.id)
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Không tải được dữ liệu'
  } finally { loading.value = false }
}

async function approve() {
  if (!fcr.value || !confirm('Phê duyệt yêu cầu này?')) return
  saving.value = true; err.value = ''
  try {
    await updateFirmwareCr(fcr.value.name, { status: 'Approved' })
    await load()
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Không thể phê duyệt'
  } finally { saving.value = false }
}

async function markDeployed() {
  if (!fcr.value || !confirm('Xác nhận đã triển khai firmware?')) return
  saving.value = true; err.value = ''
  try {
    await updateFirmwareCr(fcr.value.name, { status: 'Applied' })
    await load()
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Không thể cập nhật trạng thái'
  } finally { saving.value = false }
}

const workflowSteps = [
  { key: 'Draft', label: 'Nháp' },
  { key: 'Approved', label: 'Phê duyệt' },
  { key: 'Applied', label: 'Đã triển khai' },
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
    <PageHeader
      :title="fcr ? `Cập nhật Firmware — ${fcr.asset_name || fcr.asset_ref}` : (props.id ?? 'Yêu cầu cập nhật firmware')"
      :subtitle="fcr ? fcr.name : 'Yêu cầu cập nhật firmware'"
      :back-to="'/cm/firmware'"
      back-label="← Danh sách FCR"
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

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3">
        <button
class="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
          @click="router.push('/cm/firmware')">
Quay lại
</button>
        <button
          v-if="fcr.status === 'Draft' || fcr.status === 'Pending Approval'"
          :disabled="saving"
          class="btn-primary text-sm"
          @click="approve"
        >
          {{ saving ? 'Đang xử lý…' : 'Phê duyệt' }}
        </button>
        <button
          v-else-if="fcr.status === 'Approved'"
          :disabled="saving"
          class="btn-primary text-sm"
          @click="markDeployed"
        >
          {{ saving ? 'Đang xử lý…' : 'Đã triển khai' }}
        </button>
      </div>
    </template>
  </div>
</template>
