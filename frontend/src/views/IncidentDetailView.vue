<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-12 Incident Detail + Workflow
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getIncident, acknowledgeIncident, resolveIncident, closeIncident } from '@/api/imm12'
import { deleteIncident } from '@/api/imm00'
import type { IncidentDetail } from '@/api/imm12'

const route = useRoute()
const router = useRouter()
const name = computed(() => route.params.id as string)

const form = ref<Partial<IncidentDetail>>({})
const loading = ref(false)
const err = ref('')

// Workflow action modals
const showAckModal = ref(false)
const showResolveModal = ref(false)
const showCloseModal = ref(false)
const ackNotes = ref('')
const ackAssignedTo = ref('')
const resolveNotes = ref('')
const rootCause = ref('')
const verifyNotes = ref('')
const actionLoading = ref(false)

async function load() {
  loading.value = true
  err.value = ''
  try {
    const res = await getIncident(name.value)
    if (res) form.value = res as unknown as IncidentDetail
  } catch {
    err.value = 'Không tải được Incident Report'
  } finally { loading.value = false }
}

async function doAcknowledge() {
  actionLoading.value = true
  err.value = ''
  try {
    await acknowledgeIncident(name.value, ackNotes.value, ackAssignedTo.value)
    showAckModal.value = false
    ackNotes.value = ''; ackAssignedTo.value = ''
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi khi acknowledge' }
  finally { actionLoading.value = false }
}

async function doResolve() {
  if (!resolveNotes.value.trim()) { err.value = 'Bắt buộc nhập ghi chú giải quyết'; return }
  actionLoading.value = true
  err.value = ''
  try {
    await resolveIncident(name.value, resolveNotes.value, rootCause.value)
    showResolveModal.value = false
    resolveNotes.value = ''; rootCause.value = ''
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi khi resolve' }
  finally { actionLoading.value = false }
}

async function doClose() {
  actionLoading.value = true
  err.value = ''
  try {
    await closeIncident(name.value, verifyNotes.value)
    showCloseModal.value = false
    verifyNotes.value = ''
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi khi close' }
  finally { actionLoading.value = false }
}

async function remove() {
  if (!confirm(`Xóa Incident "${name.value}"?`)) return
  try { await deleteIncident(name.value); router.push('/incidents') }
  catch (e: unknown) { err.value = (e as Error).message || 'Không thể xóa' }
}

const canAcknowledge = computed(() =>
  form.value.status === 'Open' && (form.value.allowed_transitions ?? []).includes('Under Investigation'),
)
const canResolve = computed(() =>
  form.value.status === 'Under Investigation' && (form.value.allowed_transitions ?? []).includes('Resolved'),
)
const canClose = computed(() =>
  form.value.status === 'Resolved' && (form.value.allowed_transitions ?? []).includes('Closed'),
)
const isClosed = computed(() => form.value.status === 'Closed')

const SEV_COLOR: Record<string, string> = {
  Critical: 'bg-red-100 text-red-700',
  High: 'bg-orange-100 text-orange-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  Low: 'bg-gray-100 text-gray-700',
}
function sevColor(s?: string) {
  return SEV_COLOR[s ?? ''] ?? 'bg-gray-100 text-gray-700'
}

const STATUS_COLOR: Record<string, string> = {
  'Open': 'bg-blue-100 text-blue-700',
  'Under Investigation': 'bg-yellow-100 text-yellow-800',
  'Resolved': 'bg-purple-100 text-purple-700',
  'Closed': 'bg-green-100 text-green-700',
}

const STATUS_LABEL: Record<string, string> = {
  'Open': 'Mới mở',
  'Under Investigation': 'Đang điều tra',
  'Resolved': 'Đã giải quyết',
  'Closed': 'Đã đóng',
}

onMounted(load)
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto space-y-5">
    <!-- Header -->
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <button class="text-sm text-slate-500 hover:text-slate-700 mb-1" @click="router.push('/incidents')">← Danh sách Incident</button>
        <h1 class="text-xl font-semibold text-gray-800">{{ name }}</h1>
        <div class="flex items-center gap-2 mt-1 flex-wrap">
          <span :class="['px-2 py-0.5 rounded text-xs font-medium', sevColor(form.severity)]">{{ form.severity }}</span>
          <span :class="['px-2 py-0.5 rounded text-xs font-medium', STATUS_COLOR[form.status ?? ''] || 'bg-gray-100']">
            {{ STATUS_LABEL[form.status ?? ''] || form.status }}
          </span>
        </div>
      </div>

      <!-- Workflow actions -->
      <div class="flex gap-2 flex-wrap">
        <button v-if="canAcknowledge"
          class="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showAckModal = true">
          Bắt đầu điều tra
        </button>
        <button v-if="canResolve"
          class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showResolveModal = true">
          Đánh dấu đã giải quyết
        </button>
        <button v-if="canClose"
          class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showCloseModal = true">
          Đóng Incident
        </button>
        <button v-if="!isClosed"
          class="text-red-500 hover:text-red-700 text-sm font-medium px-3 py-2"
          @click="remove">Xóa</button>
      </div>
    </div>

    <div v-if="err" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ err }}</div>
    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>

    <!-- Detail card -->
    <div v-else class="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <!-- Basic info -->
      <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <div class="text-xs text-slate-500 mb-0.5">Thiết bị</div>
          <div class="text-sm font-medium">{{ form.asset_name || form.asset || '—' }}</div>
          <div v-if="form.asset_name" class="text-xs text-slate-400 font-mono">{{ form.asset }}</div>
        </div>
        <div>
          <div class="text-xs text-slate-500 mb-0.5">Loại sự cố</div>
          <div class="text-sm">{{ form.incident_type || '—' }}</div>
        </div>
        <div>
          <div class="text-xs text-slate-500 mb-0.5">Người báo cáo</div>
          <div class="text-sm">{{ form.reported_by || '—' }}</div>
        </div>
        <div>
          <div class="text-xs text-slate-500 mb-0.5">Thời điểm báo cáo</div>
          <div class="text-sm">{{ form.reported_at ? new Date(form.reported_at).toLocaleString('vi-VN') : '—' }}</div>
        </div>
      </div>

      <!-- Description -->
      <div class="p-6 space-y-3">
        <div>
          <div class="text-xs text-slate-500 mb-1">Mô tả sự cố</div>
          <div class="text-sm text-gray-700 whitespace-pre-line bg-gray-50 p-3 rounded-lg">{{ form.description || '—' }}</div>
        </div>
        <div v-if="form.immediate_action">
          <div class="text-xs text-slate-500 mb-1">Biện pháp tức thời</div>
          <div class="text-sm text-gray-700 whitespace-pre-line">{{ form.immediate_action }}</div>
        </div>
      </div>

      <!-- Patient / BYT -->
      <div v-if="form.patient_affected || form.reported_to_byt" class="p-6 space-y-2">
        <div v-if="form.patient_affected" class="text-sm text-orange-700 bg-orange-50 p-3 rounded-lg">
          <strong>Ảnh hưởng bệnh nhân:</strong> {{ form.patient_impact_description || 'Có ảnh hưởng (chưa mô tả)' }}
        </div>
        <div v-if="form.reported_to_byt" class="text-sm text-slate-600">
          ✓ Đã báo cáo Bộ Y tế ({{ form.byt_report_date || 'chưa ghi ngày' }})
        </div>
      </div>

      <!-- Resolution -->
      <div v-if="form.resolution_notes || form.root_cause_summary" class="p-6 space-y-3">
        <div v-if="form.root_cause_summary">
          <div class="text-xs text-slate-500 mb-1">Nguyên nhân gốc rễ</div>
          <div class="text-sm text-gray-700 whitespace-pre-line bg-gray-50 p-3 rounded-lg">{{ form.root_cause_summary }}</div>
        </div>
        <div v-if="form.resolution_notes">
          <div class="text-xs text-slate-500 mb-1">Ghi chú giải quyết</div>
          <div class="text-sm text-gray-700 whitespace-pre-line bg-gray-50 p-3 rounded-lg">{{ form.resolution_notes }}</div>
        </div>
        <div v-if="form.closed_date" class="text-xs text-slate-500">
          Ngày đóng: {{ new Date(form.closed_date).toLocaleDateString('vi-VN') }}
        </div>
      </div>

      <!-- Links -->
      <div v-if="form.linked_repair_wo || form.linked_capa" class="p-6 flex gap-4 flex-wrap">
        <div v-if="form.linked_capa">
          <div class="text-xs text-slate-500 mb-0.5">Liên kết CAPA</div>
          <button class="text-sm text-purple-600 hover:underline font-mono" @click="router.push(`/capas/${form.linked_capa}`)">
            {{ form.linked_capa }}
          </button>
        </div>
        <div v-if="form.linked_repair_wo">
          <div class="text-xs text-slate-500 mb-0.5">Liên kết Repair WO</div>
          <button class="text-sm text-blue-600 hover:underline font-mono" @click="router.push(`/cm/work-orders/${form.linked_repair_wo}`)">
            {{ form.linked_repair_wo }}
          </button>
        </div>
      </div>
    </div>

    <!-- Acknowledge modal -->
    <div v-if="showAckModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-gray-800">Bắt đầu điều tra</h2>
        <div>
          <label for="ack-notes" class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
          <textarea id="ack-notes" v-model="ackNotes" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400" placeholder="Mô tả bước tiếp theo, tình hình hiện tại..."></textarea>
        </div>
        <div>
          <label for="ack-assigned" class="block text-sm font-medium text-gray-700 mb-1">Giao cho (email user)</label>
          <input id="ack-assigned" v-model="ackAssignedTo" type="email" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400" placeholder="ktv@hospital.vn" />
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg" @click="showAckModal = false">Hủy</button>
          <button :disabled="actionLoading" class="px-4 py-2 text-sm bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50" @click="doAcknowledge">
            {{ actionLoading ? 'Đang xử lý...' : 'Xác nhận điều tra' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Resolve modal -->
    <div v-if="showResolveModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-gray-800">Đánh dấu đã giải quyết</h2>
        <div>
          <label for="resolve-notes" class="block text-sm font-medium text-gray-700 mb-1">Ghi chú giải quyết <span class="text-red-500">*</span></label>
          <textarea id="resolve-notes" v-model="resolveNotes" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400" placeholder="Đã làm gì để giải quyết sự cố..."></textarea>
        </div>
        <div>
          <label for="root-cause" class="block text-sm font-medium text-gray-700 mb-1">Nguyên nhân gốc rễ</label>
          <textarea id="root-cause" v-model="rootCause" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400" placeholder="5-Why / Fishbone..."></textarea>
        </div>
        <p v-if="form.severity === 'High' || form.severity === 'Critical'" class="text-xs text-orange-600 bg-orange-50 p-2 rounded">
          ⚠ Severity {{ form.severity }} — CAPA sẽ tự động tạo sau khi resolve.
        </p>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg" @click="showResolveModal = false">Hủy</button>
          <button :disabled="actionLoading || !resolveNotes.trim()" class="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50" @click="doResolve">
            {{ actionLoading ? 'Đang xử lý...' : 'Xác nhận giải quyết' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Close modal -->
    <div v-if="showCloseModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-gray-800">Đóng Incident Report</h2>
        <div>
          <label for="verify-notes" class="block text-sm font-medium text-gray-700 mb-1">Ghi chú xác minh (tùy chọn)</label>
          <textarea id="verify-notes" v-model="verifyNotes" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400" placeholder="Đã xác minh kết quả xử lý, không tái phát..."></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg" @click="showCloseModal = false">Hủy</button>
          <button :disabled="actionLoading" class="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50" @click="doClose">
            {{ actionLoading ? 'Đang đóng...' : 'Đóng Incident' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
