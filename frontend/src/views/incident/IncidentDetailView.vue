<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team Incident Detail + Workflow
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getIncident, acknowledgeIncident, startWork, resolveIncident, closeIncident, cancelIncident, createRca } from '@/api/imm12'
import { deleteIncident } from '@/api/imm00'
import type { IncidentDetail } from '@/api/imm12'
import SmartSelect from '@/components/common/SmartSelect.vue'
import WorkflowStepper from '@/components/common/WorkflowStepper.vue'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { useCapabilities } from '@/composables/useCapabilities'
import { sanitizeHtml } from '@/utils/sanitizeHtml'
import { incidentStatusLabel, incidentStatusClass, incidentSeverityLabel, incidentSeverityClass, incidentTypeLabel } from '@/constants/labels'

// Stepper tuyến chính (D3): 6 node — RCA Required là nhánh, render khi đang ở đó.
const INCIDENT_STEPS = ['Open', 'Acknowledged', 'In Progress', 'Resolved', 'Closed']

const route = useRoute()
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const { can } = useCapabilities()
const name = computed(() => route.params.id as string)

// LL-FE-12/22: gate qua capability (đồng bộ BE rbac.CAPABILITY_MAP), KHÔNG dùng
// ROLES_* stub rỗng. incident.acknowledge = write; incident.close = submit.
const canAck = computed(() => can('incident.acknowledge'))
const canCloseIncident = computed(() => can('incident.close'))
const canCancelIncident = computed(() => can('incident.acknowledge'))
const canDeleteIncident = computed(() => auth.isSystemAdmin)

const form = ref<Partial<IncidentDetail>>({})
const loading = ref(false)
const err = ref('')

// Workflow action modals
const showAckModal = ref(false)
const showStartModal = ref(false)
const startNotes = ref('')
const showResolveModal = ref(false)
const showCloseModal = ref(false)
const showCancelModal = ref(false)
const ackNotes = ref('')
const ackAssignedTo = ref('')
const resolveNotes = ref('')
const rootCause = ref('')
const verifyNotes = ref('')
const cancelReason = ref('')
const rcaCreating = ref(false)
const actionLoading = ref(false)

async function load() {
  loading.value = true
  err.value = ''
  try {
    form.value = await getIncident(name.value)
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Không tải được Incident Report'
  } finally { loading.value = false }
}

async function doAcknowledge() {
  actionLoading.value = true
  err.value = ''
  try {
    await acknowledgeIncident(name.value, ackNotes.value, ackAssignedTo.value)
    showAckModal.value = false
    ackNotes.value = ''; ackAssignedTo.value = ''
    toast.success('Đã tiếp nhận sự cố')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi tiếp nhận'
    err.value = msg
    toast.error(msg)
  } finally { actionLoading.value = false }
}

async function doStartWork() {
  actionLoading.value = true
  err.value = ''
  try {
    await startWork(name.value, startNotes.value)
    showStartModal.value = false
    startNotes.value = ''
    toast.success('Đã bắt đầu xử lý sự cố')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi bắt đầu xử lý'
    err.value = msg
    toast.error(msg)
  } finally { actionLoading.value = false }
}

async function doResolve() {
  if (!resolveNotes.value.trim()) {
    err.value = 'Bắt buộc nhập ghi chú giải quyết'
    toast.warning(err.value)
    return
  }
  actionLoading.value = true
  err.value = ''
  try {
    await resolveIncident(name.value, resolveNotes.value, rootCause.value)
    showResolveModal.value = false
    resolveNotes.value = ''; rootCause.value = ''
    toast.success('Đã đánh dấu Incident là đã giải quyết')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi resolve'
    err.value = msg
    toast.error(msg)
  } finally { actionLoading.value = false }
}

async function doClose() {
  actionLoading.value = true
  err.value = ''
  try {
    await closeIncident(name.value, verifyNotes.value)
    showCloseModal.value = false
    verifyNotes.value = ''
    toast.success('Đã đóng Incident')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi close'
    err.value = msg
    toast.error(msg)
  } finally { actionLoading.value = false }
}

async function doCancel() {
  if (!cancelReason.value.trim()) {
    err.value = 'Bắt buộc nhập lý do hủy'
    toast.warning(err.value)
    return
  }
  actionLoading.value = true
  err.value = ''
  try {
    await cancelIncident(name.value, cancelReason.value)
    showCancelModal.value = false
    cancelReason.value = ''
    toast.success('Đã hủy Incident')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi hủy'
    err.value = msg
    toast.error(msg)
  } finally { actionLoading.value = false }
}

async function doCreateRca() {
  rcaCreating.value = true
  err.value = ''
  try {
    const res = await createRca(name.value, '5-Why')
    if (res?.name) router.push(`/rca/${res.name}`)
  } catch (e: unknown) { err.value = e instanceof Error ? e.message : 'Không thể tạo RCA' }
  finally { rcaCreating.value = false }
}

async function remove() {
  if (!confirm(`Xóa Incident "${name.value}"?`)) return
  try { await deleteIncident(name.value); router.push('/incidents/list') }
  catch (e: unknown) { err.value = e instanceof Error ? e.message : 'Không thể xóa' }
}

// Ground truth = allowed_transitions từ BE (_VALID_TRANSITIONS trong imm12.py).
// State machine BE (D3): Open → Acknowledged → In Progress → Resolved → Closed
// (+ Cancelled, RCA Required). "Tiếp nhận" tách khỏi "Bắt đầu xử lý".
const allowedTransitions = computed(() => form.value.allowed_transitions ?? [])
const canAcknowledge = computed(() =>
  canAck.value
  && form.value.status === 'Open'
  && allowedTransitions.value.includes('Acknowledged'),
)
const canStartWork = computed(() =>
  canAck.value
  && form.value.status === 'Acknowledged'
  && allowedTransitions.value.includes('In Progress'),
)
const canResolve = computed(() =>
  canAck.value
  && form.value.status === 'In Progress'
  && allowedTransitions.value.includes('Resolved'),
)
const canClose = computed(() =>
  canCloseIncident.value
  && form.value.status === 'Resolved'
  && allowedTransitions.value.includes('Closed'),
)
const canCancel = computed(() =>
  canCancelIncident.value && allowedTransitions.value.includes('Cancelled'),
)
// IMM-12-C: chỉ cho Xóa khi sự cố CÒN ở "Mới mở" (Open). Đã rời Open
// (đặc biệt Critical/đã báo BYT) thì giữ record cho audit trail (NĐ98).
const canDelete = computed(() =>
  canDeleteIncident.value && form.value.status === 'Open',
)
const needsRca = computed(() =>
  (form.value.rca_required === 1) && !form.value.rca_record,
)

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <!-- Header -->
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <button class="text-sm text-slate-500 hover:text-slate-700 mb-1" @click="router.push('/incidents/list')">← Danh sách Sự cố</button>
        <h1 class="text-xl font-semibold text-slate-800">{{ name }}</h1>
        <div class="flex items-center gap-2 mt-1 flex-wrap">
          <span :class="['px-2 py-0.5 rounded text-xs font-medium', incidentSeverityClass(form.severity ?? '')]">{{ incidentSeverityLabel(form.severity ?? '') }}</span>
          <span :class="['px-2 py-0.5 rounded text-xs font-medium', incidentStatusClass(form.status ?? '')]">
            {{ incidentStatusLabel(form.status ?? '') }}
          </span>
          <span v-if="form.status === 'RCA Required'" class="px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">{{ incidentStatusLabel('RCA Required') }}</span>
        </div>
      </div>

      <!-- Workflow actions -->
      <div class="flex gap-2 flex-wrap">
        <button
v-if="canAcknowledge"
          class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showAckModal = true">
          Tiếp nhận
        </button>
        <button
v-if="canStartWork"
          class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showStartModal = true">
          Bắt đầu xử lý
        </button>
        <button
v-if="canResolve"
          class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showResolveModal = true">
          Đánh dấu đã giải quyết
        </button>
        <button
v-if="canClose"
          class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showCloseModal = true">
          Đóng Incident
        </button>
        <button
v-if="canCancel"
          class="bg-slate-500 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showCancelModal = true">
          Hủy (False alarm)
        </button>
        <button
v-if="canDelete"
          class="text-red-500 hover:text-red-700 text-sm font-medium px-3 py-2"
          @click="remove">
Xóa
</button>
      </div>
    </div>

    <!-- Workflow stepper -->
    <div v-if="!loading && form.status" class="bg-white rounded-xl border border-slate-200 p-4">
      <WorkflowStepper :steps="INCIDENT_STEPS" :current="form.status" :label-for="incidentStatusLabel" />
    </div>

    <!-- SLA + NĐ98 banner khi ảnh hưởng bệnh nhân -->
    <div v-if="!loading && form.patient_affected" class="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-800 space-y-1">
      <div><strong>Ảnh hưởng bệnh nhân:</strong> {{ form.patient_impact_description || 'Có ảnh hưởng (chưa mô tả chi tiết)' }}</div>
      <div v-if="form.linked_repair_wo">Đã sinh lệnh sửa chữa (CM): <strong>{{ form.linked_repair_wo }}</strong> — thiết bị chuyển Ngừng sử dụng.</div>
      <div class="text-red-700"><strong>Cảnh báo NĐ98:</strong> Sự cố ảnh hưởng bệnh nhân — cần báo cáo Bộ Y tế trong 48h nếu xác định lỗi sản phẩm.</div>
    </div>

    <div v-if="err" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ err }}</div>
    <div v-if="loading" class="text-center text-slate-400 py-12">Đang tải...</div>

    <!-- Detail card -->
    <div v-else class="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
      <!-- Basic info -->
      <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <div class="text-xs text-slate-500 mb-0.5">Thiết bị</div>
          <div class="text-sm font-medium">{{ form.asset_name || form.asset || '—' }}</div>
          <div v-if="form.asset_name" class="text-xs text-slate-400 font-mono">{{ form.asset }}</div>
        </div>
        <div>
          <div class="text-xs text-slate-500 mb-0.5">Loại sự cố</div>
          <div class="text-sm">{{ form.incident_type ? incidentTypeLabel(form.incident_type) : '—' }}</div>
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
          <div v-if="form.description" class="rich-text text-sm text-slate-700 bg-slate-50 p-3 rounded-lg" v-html="sanitizeHtml(form.description)" />
          <div v-else class="text-sm text-slate-700 bg-slate-50 p-3 rounded-lg">—</div>
        </div>
        <div v-if="form.immediate_action">
          <div class="text-xs text-slate-500 mb-1">Biện pháp tức thời</div>
          <div class="rich-text text-sm text-slate-700" v-html="sanitizeHtml(form.immediate_action)" />
        </div>
      </div>

      <!-- Thông tin bệnh nhân / Bộ Y tế -->
      <div v-if="form.patient_affected || form.reported_to_byt" class="p-6 space-y-2">
        <div v-if="form.patient_affected" class="text-sm text-orange-700 bg-orange-50 p-3 rounded-lg">
          <strong>Ảnh hưởng bệnh nhân:</strong> {{ form.patient_impact_description || 'Có ảnh hưởng (chưa mô tả)' }}
        </div>
        <div v-if="form.reported_to_byt" class="text-sm text-slate-600">
          Đã báo cáo Bộ Y tế ({{ form.byt_report_date || 'chưa ghi ngày' }})
        </div>
      </div>

      <!-- Resolution -->
      <div v-if="form.resolution_notes || form.root_cause_summary" class="p-6 space-y-3">
        <div v-if="form.root_cause_summary">
          <div class="text-xs text-slate-500 mb-1">Nguyên nhân gốc rễ</div>
          <div class="rich-text text-sm text-slate-700 bg-slate-50 p-3 rounded-lg" v-html="sanitizeHtml(form.root_cause_summary)" />
        </div>
        <div v-if="form.resolution_notes">
          <div class="text-xs text-slate-500 mb-1">Ghi chú giải quyết</div>
          <div class="rich-text text-sm text-slate-700 bg-slate-50 p-3 rounded-lg" v-html="sanitizeHtml(form.resolution_notes)" />
        </div>
        <div v-if="form.closed_date" class="text-xs text-slate-500">
          Ngày đóng: {{ new Date(form.closed_date).toLocaleDateString('vi-VN') }}
        </div>
      </div>

      <!-- RCA section -->
      <div v-if="form.rca_required === 1 || form.rca_record" class="p-6 space-y-3">
        <div class="flex items-center justify-between">
          <div class="text-sm font-semibold text-slate-700">Root Cause Analysis (RCA)</div>
          <button
v-if="needsRca" :disabled="rcaCreating"
            class="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg text-xs font-medium"
            @click="doCreateRca">
            {{ rcaCreating ? 'Đang tạo...' : 'Tạo RCA' }}
          </button>
        </div>
        <div v-if="form.rca" class="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
          <div class="flex items-center justify-between">
            <div>
              <button class="text-sm font-mono text-indigo-700 hover:underline" @click="router.push(`/rca/${form.rca.name}`)">{{ form.rca.name }}</button>
              <span class="ml-2 text-xs px-2 py-0.5 rounded bg-white border">{{ form.rca.status }}</span>
            </div>
          </div>
          <div v-if="form.rca.root_cause" class="text-xs text-slate-700 mt-2">
            <span class="text-slate-500">Root cause:</span>
            <span class="rich-text" v-html="sanitizeHtml(form.rca.root_cause)" />
          </div>
        </div>
        <div v-else-if="needsRca" class="text-xs text-amber-700 bg-amber-50 p-3 rounded">
          Sự cố mức {{ incidentSeverityLabel(form.severity ?? '') }} yêu cầu RCA trước khi đóng giải quyết.
        </div>
      </div>

      <div v-if="form.chronic_failure_flag === 1" class="p-6 bg-red-50 border-t border-red-200">
        <div class="text-sm text-red-700"><strong>Sự cố lặp lại:</strong> thiết bị này đã có ≥3 sự cố cùng mã lỗi trong 90 ngày.</div>
      </div>

      <div v-if="form.clinical_impact" class="p-6">
        <div class="text-xs text-slate-500 mb-1">Tác động lâm sàng</div>
        <div class="rich-text text-sm text-slate-700 bg-red-50 p-3 rounded-lg" v-html="sanitizeHtml(form.clinical_impact)" />
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
        <h2 class="font-semibold text-slate-800">Tiếp nhận sự cố</h2>
        <div>
          <label for="ack-notes" class="block text-sm font-medium text-slate-700 mb-1">Ghi chú</label>
          <textarea id="ack-notes" v-model="ackNotes" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400" placeholder="Mô tả bước tiếp theo, tình hình hiện tại..."></textarea>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Giao cho (User)</label>
          <SmartSelect v-model="ackAssignedTo" doctype="User" placeholder="Tìm user theo tên / email..." />
          <p class="text-[11px] text-slate-400 mt-1">Tùy chọn — nếu chọn, hệ thống sẽ gửi email thông báo cho user này.</p>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg" @click="showAckModal = false">Hủy</button>
          <button :disabled="actionLoading" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50" @click="doAcknowledge">
            {{ actionLoading ? 'Đang xử lý...' : 'Xác nhận tiếp nhận' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Start work modal -->
    <div v-if="showStartModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Bắt đầu xử lý</h2>
        <div>
          <label for="start-notes" class="block text-sm font-medium text-slate-700 mb-1">Ghi chú</label>
          <textarea id="start-notes" v-model="startNotes" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" placeholder="Bắt đầu can thiệp thiết bị, hành động đầu tiên..."></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg" @click="showStartModal = false">Hủy</button>
          <button :disabled="actionLoading" class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50" @click="doStartWork">
            {{ actionLoading ? 'Đang xử lý...' : 'Bắt đầu xử lý' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Resolve modal -->
    <div v-if="showResolveModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Đánh dấu đã giải quyết</h2>
        <div>
          <label for="resolve-notes" class="block text-sm font-medium text-slate-700 mb-1">Ghi chú giải quyết <span class="text-red-500">*</span></label>
          <textarea id="resolve-notes" v-model="resolveNotes" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400" placeholder="Đã làm gì để giải quyết sự cố..."></textarea>
        </div>
        <div>
          <label for="root-cause" class="block text-sm font-medium text-slate-700 mb-1">Nguyên nhân gốc rễ</label>
          <textarea id="root-cause" v-model="rootCause" rows="2" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400" placeholder="5-Why / Fishbone..."></textarea>
        </div>
        <p v-if="form.severity === 'High' || form.severity === 'Critical'" class="text-xs text-amber-700 bg-amber-50 p-2 rounded">
          Mức độ {{ incidentSeverityLabel(form.severity ?? '') }} — CAPA sẽ tự động tạo sau khi đóng giải quyết.
        </p>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg" @click="showResolveModal = false">Hủy</button>
          <button :disabled="actionLoading || !resolveNotes.trim()" class="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50" @click="doResolve">
            {{ actionLoading ? 'Đang xử lý...' : 'Xác nhận giải quyết' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Cancel modal -->
    <div v-if="showCancelModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Hủy Incident (False Alarm)</h2>
        <div>
          <label for="cancel-reason" class="block text-sm font-medium text-slate-700 mb-1">Lý do hủy <span class="text-red-500">*</span></label>
          <textarea id="cancel-reason" v-model="cancelReason" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400" placeholder="Lý do (vd: báo cáo nhầm, không phải sự cố...)"></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg" @click="showCancelModal = false">Quay lại</button>
          <button :disabled="actionLoading || !cancelReason.trim()" class="px-4 py-2 text-sm bg-slate-600 text-white rounded-lg hover:bg-slate-700 disabled:opacity-50" @click="doCancel">
            {{ actionLoading ? 'Đang hủy...' : 'Xác nhận hủy' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Close modal -->
    <div v-if="showCloseModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Đóng Incident Report</h2>
        <div>
          <label for="verify-notes" class="block text-sm font-medium text-slate-700 mb-1">Ghi chú xác minh (tùy chọn)</label>
          <textarea id="verify-notes" v-model="verifyNotes" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400" placeholder="Đã xác minh kết quả xử lý, không tái phát..."></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg" @click="showCloseModal = false">Hủy</button>
          <button :disabled="actionLoading" class="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50" @click="doClose">
            {{ actionLoading ? 'Đang đóng...' : 'Đóng Incident' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rich-text :deep(p) { margin: 0 0 0.5rem; }
.rich-text :deep(p:last-child) { margin-bottom: 0; }
.rich-text :deep(ul),
.rich-text :deep(ol) { margin: 0 0 0.5rem 1.25rem; list-style: revert; }
.rich-text :deep(li) { margin: 0.125rem 0; }
.rich-text :deep(b),
.rich-text :deep(strong) { font-weight: 600; }
.rich-text :deep(a) { color: #2563eb; text-decoration: underline; }
</style>
