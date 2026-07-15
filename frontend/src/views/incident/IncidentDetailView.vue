<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team Incident Detail + Workflow
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getIncident, acknowledgeIncident, startWork, resolveIncident, closeIncident, cancelIncident, reopenIncident, requestRca, createRca, attachIncidentPhoto, MAX_INCIDENT_PHOTOS } from '@/api/imm12'
import { deleteIncident } from '@/api/imm00'
import type { IncidentDetail, ScenePhoto } from '@/api/imm12'
import { ApiError } from '@/api/errors'
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import WorkflowStepper from '@/components/common/WorkflowStepper.vue'
import SlaBreachBadge from '@/components/incident/SlaBreachBadge.vue'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { useCapabilities } from '@/composables/useCapabilities'
import { sanitizeHtml } from '@/utils/sanitizeHtml'
import { incidentStatusLabel, incidentStatusClass, incidentSeverityLabel, incidentSeverityClass, incidentTypeLabel, rcaStatusLabel } from '@/constants/labels'

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
// CR-WF-12-RCA-ENTRY: cap "Yêu cầu RCA" = corrective.write (== _CAP_RCA_MANAGE ở BE,
// cùng cap gate cả họ RCA start/cancel/complete + can_manage_rca). BE là chốt chặn
// (rbac.can → 403 _MSG_RCA_FORBIDDEN); FE chỉ ẩn/hiện. KHÔNG hardcode role-name.
const canManageRca = computed(() => can('corrective.write'))

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
const showReopenModal = ref(false)
const showRequestRcaModal = ref(false)
const ackNotes = ref('')
const ackAssignedTo = ref('')
const resolveNotes = ref('')
const rootCause = ref('')
const verifyNotes = ref('')
const cancelReason = ref('')
const reopenReason = ref('')
const rcaReason = ref('')
const rcaCreating = ref(false)
const actionLoading = ref(false)

// ── Ảnh hiện trường (bằng chứng NĐ98 — CR-17/G6) ──────────────────────────────
const fileInput = ref<HTMLInputElement | null>(null)
const uploadingPhoto = ref(false)
const photoError = ref('')                        // lỗi inline VN dưới control (fields.file)
const lightboxUrl = ref<string | null>(null)      // ảnh đang phóng to

const scenePhotos = computed<ScenePhoto[]>(() => form.value.scene_photos ?? [])
const photosFull = computed(() => scenePhotos.value.length >= MAX_INCIDENT_PHOTOS)
const isTerminalStatus = computed(() =>
  form.value.status === 'Closed' || form.value.status === 'Cancelled',
)
// Reporter tự nhận diện: session user == reported_by (Link User = email). BE vẫn
// authoritative (IDOR-guard AUTH-10) — đây chỉ là gate hiển thị control.
const isReporter = computed(() => !!auth.user?.name && auth.user.name === form.value.reported_by)
const canAttachPhoto = computed(() =>
  !isTerminalStatus.value && (can('incident.acknowledge') || isReporter.value),
)

function triggerPhotoPicker() {
  photoError.value = ''
  fileInput.value?.click()
}

async function onPhotoSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  photoError.value = ''
  uploadingPhoto.value = true
  try {
    await attachIncidentPhoto(name.value, file)
    toast.success('Đã đính ảnh hiện trường')
    await load()                                  // refetch → scene_photos +1
  } catch (e2: unknown) {
    // VALIDATION (sai định dạng / quá 5 ảnh) → thông điệp VN inline dưới control.
    if (e2 instanceof ApiError && e2.fields?.file) photoError.value = e2.fields.file
    else photoError.value = e2 instanceof Error ? e2.message : 'Không thể đính ảnh hiện trường'
    toast.error(photoError.value)
  } finally {
    uploadingPhoto.value = false
    if (input) input.value = ''                   // reset để chọn lại cùng file được
  }
}

function openLightbox(url: string) { lightboxUrl.value = url }
function closeLightbox() { lightboxUrl.value = null }
function onKeydown(e: KeyboardEvent) { if (e.key === 'Escape' && lightboxUrl.value) closeLightbox() }

async function load() {
  loading.value = true
  err.value = ''
  try {
    form.value = await getIncident(name.value)
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Không tải được phiếu sự cố'
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
    toast.success('Đã đánh dấu sự cố là đã giải quyết')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi giải quyết'
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
    toast.success('Đã đóng sự cố')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi đóng'
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
    toast.success('Đã hủy sự cố')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi hủy'
    err.value = msg
    toast.error(msg)
  } finally { actionLoading.value = false }
}

// BR-12-23 (CR-WF-12): "Mở lại điều tra" đưa phiếu Resolved → In Progress. `reason`
// bắt buộc (mirror doCancel: pre-check FE + BE re-validate IMM12_REOPEN_REASON_REQUIRED).
async function doReopen() {
  if (!reopenReason.value.trim()) {
    err.value = 'Vui lòng nhập lý do mở lại điều tra'
    toast.warning(err.value)
    return
  }
  actionLoading.value = true
  err.value = ''
  try {
    await reopenIncident(name.value, reopenReason.value)
    showReopenModal.value = false
    reopenReason.value = ''
    toast.success('Đã mở lại điều tra sự cố')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi mở lại điều tra'
    err.value = msg
    toast.error(msg)
  } finally { actionLoading.value = false }
}

// CR-WF-12-RCA-ENTRY: "Yêu cầu phân tích nguyên nhân gốc" đưa phiếu Resolved → RCA
// Required qua apply_workflow(action='Yêu cầu RCA') + tạo/link RCA Record (BE
// idempotent, reuse create_rca). `rca_reason` TÙY CHỌN (BE precondition duy nhất =
// status phải 'Resolved' → 422; KHÔNG tự đặt luật required ở FE). Sau khi thành công
// refetch → stepper hiện nhánh RCA Required + badge cập nhật.
async function doRequestRca() {
  actionLoading.value = true
  err.value = ''
  try {
    await requestRca(name.value, rcaReason.value)
    showRequestRcaModal.value = false
    rcaReason.value = ''
    toast.success('Đã chuyển phiếu sang trạng thái cần phân tích nguyên nhân gốc')
    await load()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Lỗi khi yêu cầu phân tích nguyên nhân gốc'
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
  } catch (e: unknown) { err.value = e instanceof Error ? e.message : 'Không thể tạo phân tích nguyên nhân gốc' }
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
// BR-12-23 (CR-WF-12): "Mở lại điều tra" — server-driven CTA (GATE-8/LL-FE-51).
// `status === 'Resolved'` KHÔNG thừa: 'In Progress' cũng là đích của canStartWork
// (Acknowledged → start_work) nên phải phân định pha để chào đúng nút; cap
// incident.close (parity Close), KHÔNG hardcode role-name. Nút chỉ hiện khi BE đã
// đối soát map (allowed_transitions[Resolved] chứa 'In Progress').
const canReopen = computed(() =>
  canCloseIncident.value
  && form.value.status === 'Resolved'
  && allowedTransitions.value.includes('In Progress'),
)
// CR-WF-12-RCA-ENTRY: "Yêu cầu phân tích nguyên nhân gốc" — server-driven CTA
// (GATE-8/LL-FE-51). Chỉ hiện khi cap corrective.write ∧ status==='Resolved' ∧
// allowed_transitions chứa 'RCA Required' (driver THẬT do BE cấp qua request_rca).
// `status === 'Resolved'` KHÔNG thừa: 'RCA Required' chỉ là đích hợp lệ TỪ Resolved
// (∈ _VALID_TRANSITIONS[Resolved]) — phân định pha, KHÔNG hardcode role-name.
const canRequestRca = computed(() =>
  canManageRca.value
  && form.value.status === 'Resolved'
  && allowedTransitions.value.includes('RCA Required'),
)
const canCancel = computed(() =>
  canCancelIncident.value && allowedTransitions.value.includes('Cancelled'),
)
// Stepper tuyến chính + nhánh RCA Required: chèn node 'RCA Required' giữa 'Resolved'
// và 'Closed' KHI phiếu đang ở nhánh này → stepper hiện đúng pha (Resolved → RCA
// Required → Closed) thay vì "rơi ra ngoài steps".
const stepperSteps = computed(() => {
  if (form.value.status !== 'RCA Required') return INCIDENT_STEPS
  const i = INCIDENT_STEPS.indexOf('Resolved')
  return [...INCIDENT_STEPS.slice(0, i + 1), 'RCA Required', ...INCIDENT_STEPS.slice(i + 1)]
})
// IMM-12-C: chỉ cho Xóa khi sự cố CÒN ở "Mới mở" (Open). Đã rời Open
// (đặc biệt Critical/đã báo BYT) thì giữ record cho audit trail (NĐ98).
const canDelete = computed(() =>
  canDeleteIncident.value && form.value.status === 'Open',
)
const needsRca = computed(() =>
  (form.value.rca_required === 1) && !form.value.rca_record,
)

onMounted(load)
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
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
          Đóng sự cố
        </button>
        <button
v-if="canRequestRca"
          class="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
          @click="showRequestRcaModal = true">
          Yêu cầu phân tích nguyên nhân gốc
        </button>
        <button
v-if="canReopen"
          class="bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showReopenModal = true">
          Mở lại điều tra
        </button>
        <button
v-if="canCancel"
          class="bg-slate-500 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="showCancelModal = true">
          Hủy (báo nhầm)
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
      <WorkflowStepper :steps="stepperSteps" :current="form.status" :label-for="incidentStatusLabel" />
    </div>

    <!-- SLA + NĐ98 banner khi ảnh hưởng bệnh nhân -->
    <div v-if="!loading && form.patient_affected" class="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-800 space-y-1">
      <div><strong>Ảnh hưởng bệnh nhân:</strong> {{ form.patient_impact_description || 'Có ảnh hưởng (chưa mô tả chi tiết)' }}</div>
      <div v-if="form.linked_repair_wo">Đã sinh lệnh sửa chữa: <strong>{{ form.linked_repair_wo }}</strong> — thiết bị chuyển Ngừng sử dụng.</div>
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

      <!-- Tình trạng SLA (BR-12-09/13) — ĐỌC cờ DERIVED server-side (is_*_breached),
           fallback cờ thô (*_breached). TUYỆT ĐỐI KHÔNG so ngày client-clock
           (overdue_server_flag SSoT). Badge tái dùng SlaBreachBadge (như danh sách). -->
      <div class="p-6 space-y-2">
        <h2 class="text-sm font-semibold text-slate-700">Tình trạng SLA</h2>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
          <div class="flex items-center justify-between gap-3">
            <dt class="text-sm text-slate-500">Phản hồi</dt>
            <dd>
              <SlaBreachBadge
                kind="response"
                :response-breached="form.is_response_breached ?? form.response_breached"
              />
            </dd>
          </div>
          <div class="flex items-center justify-between gap-3">
            <dt class="text-sm text-slate-500">Xử lý</dt>
            <dd>
              <SlaBreachBadge
                kind="resolution"
                :resolution-breached="form.is_resolution_breached ?? form.resolution_breached"
              />
            </dd>
          </div>
        </dl>
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

      <!-- Ảnh hiện trường (bằng chứng NĐ98 — CR-17/G6) -->
      <div class="p-6 space-y-3">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <h2 class="text-sm font-semibold text-slate-700">
            Ảnh hiện trường
            <span class="text-xs font-normal text-slate-400">({{ scenePhotos.length }}/{{ MAX_INCIDENT_PHOTOS }})</span>
          </h2>
          <div v-if="canAttachPhoto" class="flex flex-col items-end gap-1">
            <!-- input file ẩn (a11y: kích hoạt qua nút chữ có nhãn rõ ràng) -->
            <input
              ref="fileInput" type="file" accept="image/jpeg,image/png"
              class="sr-only" tabindex="-1" aria-hidden="true"
              @change="onPhotoSelected">
            <button
              type="button"
              :disabled="uploadingPhoto || photosFull"
              class="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-1.5 rounded-lg text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
              aria-label="Đính ảnh hiện trường (JPG hoặc PNG)"
              @click="triggerPhotoPicker">
              {{ uploadingPhoto ? 'Đang tải lên...' : '+ Đính ảnh' }}
            </button>
            <p v-if="photosFull" class="text-[11px] text-amber-600">
              Đã đạt tối đa {{ MAX_INCIDENT_PHOTOS }} ảnh
            </p>
          </div>
        </div>

        <!-- Lỗi inline VN (định dạng sai / quá số lượng) -->
        <p v-if="photoError" class="text-xs text-red-600" role="alert">{{ photoError }}</p>

        <!-- Lưới thumbnail (click để phóng to) -->
        <div v-if="scenePhotos.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          <button
            v-for="(photo, idx) in scenePhotos" :key="photo.file_url"
            type="button"
            class="group relative aspect-square rounded-lg overflow-hidden border border-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
            :aria-label="`Phóng to ảnh hiện trường ${idx + 1}: ${photo.file_name}`"
            @click="openLightbox(photo.file_url)">
            <img
              :src="photo.file_url"
              :alt="`Ảnh hiện trường ${idx + 1} — ${photo.file_name}`"
              class="w-full h-full object-cover transition-transform group-hover:scale-105"
              loading="lazy">
          </button>
        </div>
        <!-- Empty-state -->
        <div v-else class="text-sm text-slate-400 bg-slate-50 border border-dashed border-slate-200 rounded-lg p-4 text-center">
          Chưa có ảnh
          <p v-if="canAttachPhoto" class="text-xs text-slate-400 mt-1">
            Đính ảnh hiện trường làm bằng chứng theo Nghị định 98.
          </p>
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
          <div class="text-sm font-semibold text-slate-700">Phân tích nguyên nhân gốc</div>
          <button
v-if="needsRca" :disabled="rcaCreating"
            class="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg text-xs font-medium"
            @click="doCreateRca">
            {{ rcaCreating ? 'Đang tạo...' : 'Tạo phân tích nguyên nhân gốc' }}
          </button>
        </div>
        <div v-if="form.rca" class="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
          <div class="flex items-center justify-between">
            <div>
              <button class="text-sm font-mono text-indigo-700 hover:underline" @click="router.push(`/rca/${form.rca.name}`)">{{ form.rca.name }}</button>
              <span class="ml-2 text-xs px-2 py-0.5 rounded bg-white border">{{ rcaStatusLabel(form.rca.status) }}</span>
            </div>
          </div>
          <div v-if="form.rca.root_cause" class="text-xs text-slate-700 mt-2">
            <span class="text-slate-500">Nguyên nhân gốc:</span>
            <span class="rich-text" v-html="sanitizeHtml(form.rca.root_cause)" />
          </div>
        </div>
        <div v-else-if="needsRca" class="text-xs text-amber-700 bg-amber-50 p-3 rounded">
          Sự cố mức {{ incidentSeverityLabel(form.severity ?? '') }} yêu cầu phân tích nguyên nhân gốc trước khi đóng giải quyết.
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
          <div class="text-xs text-slate-500 mb-0.5">Liên kết hành động khắc phục/phòng ngừa</div>
          <button class="text-sm text-purple-600 hover:underline font-mono" @click="router.push(`/capas/${form.linked_capa}`)">
            {{ form.linked_capa }}
          </button>
        </div>
        <div v-if="form.linked_repair_wo">
          <div class="text-xs text-slate-500 mb-0.5">Liên kết lệnh sửa chữa</div>
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
          <label class="block text-sm font-medium text-slate-700 mb-1">Giao cho (người dùng)</label>
          <ApproverSelect v-model="ackAssignedTo" context="incident" placeholder="Tìm user theo tên / email..." />
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
          Mức độ {{ incidentSeverityLabel(form.severity ?? '') }} — Hành động khắc phục/phòng ngừa sẽ tự động tạo sau khi đóng giải quyết.
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
        <h2 class="font-semibold text-slate-800">Hủy sự cố (báo nhầm)</h2>
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
        <h2 class="font-semibold text-slate-800">Đóng phiếu sự cố</h2>
        <div>
          <label for="verify-notes" class="block text-sm font-medium text-slate-700 mb-1">Ghi chú xác minh (tùy chọn)</label>
          <textarea id="verify-notes" v-model="verifyNotes" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400" placeholder="Đã xác minh kết quả xử lý, không tái phát..."></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg" @click="showCloseModal = false">Hủy</button>
          <button :disabled="actionLoading" class="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50" @click="doClose">
            {{ actionLoading ? 'Đang đóng...' : 'Đóng sự cố' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Reopen modal (BR-12-23 — Mở lại điều tra, lý do bắt buộc) -->
    <div v-if="showReopenModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Mở lại điều tra sự cố</h2>
        <p class="text-xs text-slate-500">Đưa phiếu từ "Đã giải quyết" về "Đang xử lý" để điều tra tiếp. Thao tác được ghi vào nhật ký kiểm toán.</p>
        <div>
          <label for="reopen-reason" class="block text-sm font-medium text-slate-700 mb-1">Lý do mở lại <span class="text-red-500">*</span></label>
          <textarea id="reopen-reason" v-model="reopenReason" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" placeholder="Vì sao cần mở lại điều tra (vd: sự cố tái phát, phát hiện nguyên nhân mới...)"></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg" @click="showReopenModal = false">Quay lại</button>
          <button :disabled="actionLoading || !reopenReason.trim()" class="px-4 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50" @click="doReopen">
            {{ actionLoading ? 'Đang xử lý...' : 'Xác nhận mở lại' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Request RCA modal (CR-WF-12-RCA-ENTRY — Yêu cầu phân tích nguyên nhân gốc) -->
    <div v-if="showRequestRcaModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Yêu cầu phân tích nguyên nhân gốc</h2>
        <p class="text-xs text-slate-500">Chuyển phiếu từ "Đã giải quyết" sang "Cần phân tích nguyên nhân gốc" và tạo hồ sơ phân tích (RCA) liên kết. Thao tác được ghi vào nhật ký kiểm toán.</p>
        <div>
          <label for="rca-reason" class="block text-sm font-medium text-slate-700 mb-1">Lý do yêu cầu (tùy chọn)</label>
          <textarea id="rca-reason" v-model="rcaReason" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400" placeholder="Vì sao cần phân tích nguyên nhân gốc (vd: sự cố nghiêm trọng, có nguy cơ tái diễn...)"></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg" @click="showRequestRcaModal = false">Quay lại</button>
          <button :disabled="actionLoading" class="px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50" @click="doRequestRca">
            {{ actionLoading ? 'Đang xử lý...' : 'Xác nhận yêu cầu' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Lightbox ảnh hiện trường (Esc hoặc click nền để đóng) -->
    <div v-if="lightboxUrl" class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" @click="closeLightbox">
      <div class="relative max-w-3xl max-h-full" @click.stop>
        <button
          type="button"
          class="absolute -top-3 -right-3 bg-white text-slate-700 rounded-full w-8 h-8 flex items-center justify-center shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          aria-label="Đóng ảnh phóng to"
          @click="closeLightbox">✕</button>
        <img :src="lightboxUrl" alt="Ảnh hiện trường phóng to" class="max-w-full max-h-[85vh] rounded-lg object-contain">
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
