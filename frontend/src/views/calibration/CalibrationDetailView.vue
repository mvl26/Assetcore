<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getCalibration, updateCalibration } from '@/api/imm11'
import type { AssetCalibration, CalibrationMeasurement } from '@/api/imm11'
import { uploadDocumentFile } from '@/api/imm05'
import { useToast } from '@/composables/useToast'
import { useNotify } from '@/composables/useNotify'
import { useImm11Store } from '@/stores/imm11'
import { MSG } from '@/i18n/messages'
import { useCapabilities } from '@/composables/useCapabilities'
import StatusBadge from '@/components/common/StatusBadge.vue'
import WorkflowStepper from '@/components/common/WorkflowStepper.vue'
import { calibrationStatusLabel } from '@/constants/labels'

const props = defineProps<{ id: string }>()
const router = useRouter()
const toast = useToast()
const notify = useNotify()
const store = useImm11Store()
const { can } = useCapabilities()

const form = ref<Partial<AssetCalibration> & { measurements?: CalibrationMeasurement[] }>({})
const loading = ref(false)
const saving = ref(false)
const submitting = ref(false)
const err = ref('')
const uploadingCert = ref(false)

// BUG-007: Gate UI bằng capability (đồng bộ BE rbac.require ở api/imm11.py).
// `calibration.write` cấp cho KTV Hiệu chuẩn (Calibration User/Manager) — bao
// cả thao tác Start / Send Lab / Receive Cert / Save / Submit.
// `calibration.cancel` (write của Calibration Manager) gate riêng hành động hủy.
const canExecuteCal = computed(() => can('calibration.write'))
const canManageCal = computed(() => can('calibration.cancel') || can('calibration.submit'))

const isSubmitted = computed(() => form.value.docstatus === 1)
const isFailed = computed(() => form.value.overall_result === 'Failed')
const isExternal = computed(() => form.value.calibration_type === 'External')

// Workflow stepper (mockup docs/fe/11-calibration/calibration-detail.html).
// External đi qua lab; In-House đi thẳng. Terminal: Passed/Failed/Conditionally Passed.
const calStepperSteps = computed(() => {
  const terminal = form.value.status === 'Failed'
    ? 'Failed'
    : form.value.status === 'Conditionally Passed'
      ? 'Conditionally Passed'
      : 'Passed'
  if (isExternal.value) {
    return ['Scheduled', 'Sent to Lab', 'Certificate Received', terminal]
  }
  return ['Scheduled', 'In Progress', terminal]
})

// SoT server-driven CTA (mirror IncidentDetailView R3): mọi nút workflow gate theo
// allowed_transitions BE (_CAL_VALID_TRANSITIONS) — KHÔNG hardcode status→button
// client-side. Đây là fix "quá nhiều nút / trộn luồng In-House↔External": mỗi
// trạng thái CHỈ lộ đúng hành động-kế hợp lệ mà server cho phép.
const allowedTransitions = computed(() => form.value.allowed_transitions ?? [])
// overall_result của giai đoạn nhập kết quả (Đạt/Không đạt/Đạt có điều kiện).
const RESULT_STATES = ['Passed', 'Failed', 'Conditionally Passed']

const canSendToLab = computed(() =>
  // 'Sent to Lab' có trong allowed cả In-House lẫn External (state machine Scheduled),
  // nên vẫn cần isExternal để KHÔNG hiện "Gửi phòng hiệu chuẩn" cho phiếu nội bộ.
  canExecuteCal.value && isExternal.value && allowedTransitions.value.includes('Sent to Lab'),
)
const canReceiveCert = computed(() =>
  canExecuteCal.value && allowedTransitions.value.includes('Certificate Received'),
)
const canCancel = computed(() =>
  canManageCal.value && allowedTransitions.value.includes('Cancelled'),
)
// Scheduled → In Progress: "Bắt đầu hiệu chuẩn" (In-House, và External khi hiệu
// chuẩn tại chỗ bằng reference standard thay vì gửi lab).
const canStartCal = computed(() =>
  canExecuteCal.value && allowedTransitions.value.includes('In Progress'),
)
// Giai đoạn NHẬP KẾT QUẢ = khi BE cho phép chuyển sang Passed/Failed/Cond
// (status In Progress hoặc Certificate Received). Trước đó (Scheduled / Sent to Lab)
// KHÔNG lộ bảng nhập tham số đo + "Lưu kết quả" + "Gửi duyệt". `!isSubmitted` bắt
// buộc: phiếu Failed sau submit vẫn còn allowed=[Conditionally Passed] (luồng sửa
// đổi của Compliance Manager) — không được nhầm là còn nhập-đo được.
const canEnterResults = computed(() =>
  canExecuteCal.value && !isSubmitted.value &&
  RESULT_STATES.some(s => allowedTransitions.value.includes(s)),
)
const startingCal = ref(false)
async function doStartCal() {
  startingCal.value = true; err.value = ''
  try {
    await updateCalibration(props.id, { status: 'In Progress' } as Partial<AssetCalibration>)
    notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: 'phiếu hiệu chuẩn' } })
    await load()
  } catch (e: unknown) {
    store._captureError(e)
    err.value = store.error ?? ''
    notify.fromError(store.lastApiError)
  } finally { startingCal.value = false }
}

const showSendModal = ref(false)
const showReceiveModal = ref(false)
const showCancelModal = ref(false)
const sendData = ref({ sent_date: '', lab_supplier: '', lab_contract_ref: '' })
const recvData = ref({
  certificate_file: '', certificate_number: '', certificate_date: '',
  traceability_reference: '', reference_standard_serial: '',
})
const cancelReason = ref('')
const actionLoading = ref(false)

async function doSendToLab() {
  actionLoading.value = true; err.value = ''
  const res = await store.doSendToLab(props.id, {
    sent_date: sendData.value.sent_date || undefined,
    lab_supplier: sendData.value.lab_supplier || undefined,
    lab_contract_ref: sendData.value.lab_contract_ref || undefined,
  })
  actionLoading.value = false
  if (res) {
    showSendModal.value = false
    sendData.value = { sent_date: '', lab_supplier: '', lab_contract_ref: '' }
    notify.show({ code: MSG.IMM11_SEND_LAB_SUCCESS, ctx: { name: props.id } })
    await load()
  } else {
    err.value = store.error ?? ''
    notify.fromError(store.lastApiError)
  }
}

async function uploadCertificateFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input?.files?.[0]
  if (!file) return
  uploadingCert.value = true
  err.value = ''
  try {
    const result = await uploadDocumentFile(file, { docname: props.id, isPrivate: true })
    recvData.value.certificate_file = result.file_url
    toast.success(`Đã tải lên "${file.name}"`)
  } catch (e: unknown) {
    store._captureError(e)
    err.value = store.error ?? ''
    notify.fromError(store.lastApiError)
  } finally {
    uploadingCert.value = false
    if (input) input.value = ''
  }
}

async function doReceiveCert() {
  if (!recvData.value.certificate_file || !recvData.value.certificate_number || !recvData.value.certificate_date) {
    notify.show({ code: MSG.IMM11_CERT_FIELDS_REQUIRED })
    err.value = 'Bắt buộc: file chứng chỉ, số chứng chỉ, ngày cấp'
    return
  }
  actionLoading.value = true; err.value = ''
  const res = await store.doReceiveCertificate(props.id, {
    certificate_file: recvData.value.certificate_file,
    certificate_number: recvData.value.certificate_number,
    certificate_date: recvData.value.certificate_date,
    traceability_reference: recvData.value.traceability_reference || undefined,
    reference_standard_serial: recvData.value.reference_standard_serial || undefined,
  })
  actionLoading.value = false
  if (res) {
    showReceiveModal.value = false
    notify.show({
      code: MSG.IMM11_CERT_RECEIVED_SUCCESS,
      ctx: { name: props.id, certificate_number: recvData.value.certificate_number },
    })
    await load()
  } else {
    err.value = store.error ?? ''
    notify.fromError(store.lastApiError)
  }
}

async function doCancel() {
  if (!cancelReason.value.trim()) {
    notify.show({ code: MSG.IMM11_CANCEL_REASON_REQUIRED })
    err.value = 'Bắt buộc nhập lý do hủy'
    return
  }
  actionLoading.value = true; err.value = ''
  const res = await store.doCancel(props.id, cancelReason.value)
  actionLoading.value = false
  if (res) {
    showCancelModal.value = false
    cancelReason.value = ''
    notify.show({ code: MSG.IMM11_CANCEL_SUCCESS, ctx: { name: props.id } })
    await load()
  } else {
    err.value = store.error ?? ''
    notify.fromError(store.lastApiError)
  }
}

const showSubmitModal = ref(false)

// IMM-11-E (FE mirror của gate BE before_submit): cần ≥1 tham số đo + mọi
// tham số đã có giá trị + có kết quả tổng trước khi gửi duyệt.
const measurementCount = computed(() => form.value.measurements?.length ?? 0)
const allMeasured = computed(() =>
  measurementCount.value > 0 &&
  (form.value.measurements ?? []).every(
    m => m.measured_value !== null && m.measured_value !== undefined,
  ),
)
const computedOverall = computed<'Passed' | 'Failed' | null>(() => {
  if (!allMeasured.value) return null
  const anyFail = (form.value.measurements ?? []).some(m => computeResult(m) === 'Fail')
  return anyFail ? 'Failed' : 'Passed'
})
const submitBlockReason = computed(() => {
  if (!canExecuteCal.value) return 'Bạn không có quyền gửi duyệt phiếu hiệu chuẩn'
  if (measurementCount.value === 0) return 'Phải nhập ít nhất 1 tham số đo trước khi gửi duyệt'
  if (!allMeasured.value) return 'Tất cả tham số phải có giá trị đo trước khi gửi duyệt'
  if (!computedOverall.value) return 'Phiếu chưa có kết quả tổng (Đạt/Không đạt)'
  return ''
})
const canSubmitCal = computed(() => submitBlockReason.value === '')

// BUG-007: Khi user không có quyền nào — show hint để hiểu vì sao panel trống.
const hasAnyAction = computed(() =>
  canCancel.value || canStartCal.value || canSendToLab.value ||
  canReceiveCert.value || (canExecuteCal.value && !isSubmitted.value),
)
const showPermissionHint = computed(() =>
  !loading.value && !isSubmitted.value && !hasAnyAction.value,
)

async function load() {
  loading.value = true
  try {
    const res = await getCalibration(props.id) as unknown as AssetCalibration
    if (res) form.value = { ...res }
  } finally { loading.value = false }
}

async function save() {
  saving.value = true; err.value = ''
  try {
    await updateCalibration(props.id, form.value as AssetCalibration)
    notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: 'phiếu hiệu chuẩn' } })
    await load()
  } catch (e: unknown) {
    store._captureError(e)
    err.value = store.error ?? ''
    notify.fromError(store.lastApiError)
  } finally { saving.value = false }
}

function openSubmitModal() {
  if (!canSubmitCal.value) {
    err.value = submitBlockReason.value
    toast.warning(submitBlockReason.value)
    return
  }
  err.value = ''
  showSubmitModal.value = true
}

async function submit() {
  submitting.value = true; err.value = ''
  const res = await store.doSubmit(props.id)
  submitting.value = false
  if (res) {
    showSubmitModal.value = false
    notify.show({ code: MSG.IMM11_SUBMIT_SUCCESS, ctx: { name: props.id } })
    await load()
  } else {
    err.value = store.error ?? ''
    notify.fromError(store.lastApiError)
  }
}

function addMeasurement() {
  if (!form.value.measurements) form.value.measurements = []
  form.value.measurements.push({
    parameter_name: '', unit: '', nominal_value: 0,
    tolerance_positive: 5, tolerance_negative: 5, measured_value: null,
  })
}

function removeMeasurement(i: number) {
  form.value.measurements?.splice(i, 1)
}

function computeResult(m: CalibrationMeasurement) {
  if (m.measured_value === null || m.measured_value === undefined) return null
  const base = Math.abs(m.nominal_value || 0)
  const tolPlus = (m.tolerance_positive || 0) / 100 * base
  const tolMinus = (m.tolerance_negative || 0) / 100 * base
  const dev = (m.measured_value || 0) - (m.nominal_value || 0)
  return dev > tolPlus || dev < -tolMinus ? 'Fail' : 'Pass'
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button class="btn-ghost text-sm" @click="router.push('/calibration')">← Quay lại</button>
        <div>
          <p class="text-xs text-slate-400">Phiếu hiệu chuẩn</p>
          <h1 class="text-xl font-bold text-slate-900">{{ form.name }}</h1>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <StatusBadge v-if="form.status" :state="form.status" size="md" />
        <StatusBadge v-if="isSubmitted && form.overall_result" :state="form.overall_result" size="md" />
      </div>
    </div>

    <!-- Workflow stepper -->
    <div v-if="!loading && form.status && form.status !== 'Cancelled'" class="card p-4">
      <WorkflowStepper :steps="calStepperSteps" :current="form.status" :label-for="calibrationStatusLabel" />
    </div>

    <div v-if="err" class="alert-error">{{ err }}</div>
    <div v-if="loading" class="card p-8 text-center text-slate-400">Đang tải...</div>

    <template v-else>
      <!-- Info Grid -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b">Thông tin chung</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <p class="text-xs text-slate-400 mb-1">Thiết bị</p>
            <p class="font-medium">{{ form.asset_name || form.asset }}</p>
            <p v-if="form.asset_name" class="text-xs text-slate-400 font-mono">{{ form.asset }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Loại hiệu chuẩn</p>
            <p>{{ form.calibration_type === 'External' ? 'Bên ngoài (ISO 17025)' : form.calibration_type === 'In-House' ? 'Nội bộ' : (form.calibration_type || '—') }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Kỹ thuật viên</p>
            <p>{{ form.technician_name || form.technician || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Ngày dự kiến</p>
            <p>{{ form.scheduled_date }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Ngày thực hiện</p>
            <template v-if="!isSubmitted">
              <DateInput v-model="form.actual_date" class="form-input w-full text-xs" />
            </template>
            <p v-else>{{ form.actual_date || '—' }}</p>
          </div>
          <div v-if="form.next_calibration_date">
            <p class="text-xs text-slate-400 mb-1">Ngày hiệu chuẩn tiếp theo</p>
            <p class="font-semibold text-blue-600">{{ form.next_calibration_date }}</p>
          </div>
        </div>
      </div>

      <!-- Status + External fields -->
      <div v-if="!isSubmitted" class="card p-5 space-y-4">
        <h2 class="text-sm font-semibold text-slate-700 pb-2 border-b">Thông tin bổ sung</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Trạng thái</label>
            <div class="flex items-center gap-2 h-10">
              <StatusBadge v-if="form.status" :state="form.status" size="md" />
              <span class="text-xs text-slate-400">— chuyển trạng thái qua các nút thao tác bên dưới</span>
            </div>
          </div>
          <div v-if="form.calibration_type === 'External'">
            <label class="form-label">Ngày gửi phòng hiệu chuẩn</label>
            <DateInput v-model="form.sent_date" class="form-input w-full text-sm" />
          </div>
        </div>

        <template v-if="form.calibration_type === 'External'">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="form-label">Số hợp đồng Lab</label>
              <input v-model="form.lab_contract_ref" type="text" class="form-input w-full text-sm" />
            </div>
            <div>
              <label class="form-label">Số công nhận ISO 17025</label>
              <input v-model="form.lab_accreditation_number" type="text" class="form-input w-full text-sm" />
            </div>
            <div>
              <label class="form-label">Số chứng chỉ</label>
              <input v-model="form.certificate_number" type="text" class="form-input w-full text-sm" />
            </div>
            <div>
              <label class="form-label">Ngày cấp chứng chỉ</label>
              <DateInput v-model="form.certificate_date" class="form-input w-full text-sm" />
            </div>
          </div>
        </template>

        <template v-if="form.calibration_type === 'In-House'">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="form-label">Số serial thiết bị chuẩn</label>
              <input v-model="form.reference_standard_serial" type="text" class="form-input w-full text-sm" />
            </div>
            <div>
              <label class="form-label">Tham chiếu liên kết chuẩn</label>
              <input v-model="form.traceability_reference" type="text" class="form-input w-full text-sm" />
            </div>
          </div>
        </template>

        <div>
          <label class="form-label">Ghi chú kỹ thuật viên</label>
          <textarea v-model="form.technician_notes" rows="2" class="form-input w-full text-sm"></textarea>
        </div>
      </div>

      <!-- Measurements -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-sm font-semibold text-slate-700">Tham số đo lường</h2>
          <button v-if="canEnterResults" class="text-blue-600 text-xs font-medium" @click="addMeasurement">+ Thêm tham số</button>
        </div>
        <div v-if="!form.measurements?.length" class="text-sm text-slate-400 py-3">Chưa có tham số đo.</div>
        <div v-else class="space-y-2">
          <div class="grid grid-cols-7 gap-2 text-xs font-medium text-slate-500 pb-1 border-b">
            <span class="col-span-2">Tham số</span>
            <span>Đơn vị</span>
            <span>Danh định</span>
            <span>Dung sai ±%</span>
            <span>Đo được</span>
            <span>Kết quả</span>
          </div>
          <div v-for="(m, i) in form.measurements" :key="i" class="grid grid-cols-7 gap-2 items-center">
            <input v-if="canEnterResults" v-model="m.parameter_name" class="col-span-2 form-input text-xs px-2 py-1" placeholder="Tên tham số" />
            <span v-else class="col-span-2 text-sm font-medium">{{ m.parameter_name }}</span>

            <input v-if="canEnterResults" v-model="m.unit" class="form-input text-xs px-2 py-1" placeholder="cmH₂O" />
            <span v-else class="text-sm">{{ m.unit }}</span>

            <input v-if="canEnterResults" v-model.number="m.nominal_value" type="number" class="form-input text-xs px-2 py-1" />
            <span v-else class="text-sm">{{ m.nominal_value }}</span>

            <input v-if="canEnterResults" v-model.number="m.tolerance_positive" type="number" class="form-input text-xs px-2 py-1" placeholder="5" />
            <span v-else class="text-sm">±{{ m.tolerance_positive }}%</span>

            <input
v-if="canEnterResults" v-model.number="m.measured_value" type="number" step="any" class="form-input text-xs px-2 py-1"
              :class="m.measured_value !== null && computeResult(m) === 'Fail' ? 'border-red-400 bg-red-50' : ''" />
            <span v-else class="text-sm">{{ m.measured_value ?? '—' }}</span>

            <div class="flex items-center gap-1">
              <span v-if="m.pass_fail" class="text-xs font-semibold" :class="m.pass_fail === 'Pass' ? 'text-green-600' : 'text-red-600'">
                {{ m.pass_fail }}
              </span>
              <span
v-else-if="m.measured_value !== null && m.measured_value !== undefined" class="text-xs font-semibold"
                :class="computeResult(m) === 'Pass' ? 'text-green-600' : 'text-red-600'">
                {{ computeResult(m) }}
              </span>
              <button v-if="canEnterResults" class="text-red-400 hover:text-red-600 ml-auto" aria-label="Xoá đo" @click="removeMeasurement(i)">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- CAPA Alert on Fail -->
      <div v-if="isSubmitted && isFailed && form.capa_record" class="card p-4 bg-red-50 border-red-200 flex items-center gap-3">
        <svg class="w-5 h-5 text-red-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div>
          <p class="text-sm font-semibold text-red-700">Hiệu chuẩn thất bại — CAPA đã tạo</p>
          <p class="text-xs text-red-600">{{ form.capa_record }}</p>
        </div>
        <button class="ml-auto text-xs text-red-700 font-medium underline" @click="router.push(`/capas/${form.capa_record}`)">Xem CAPA</button>
      </div>

      <!-- BUG-007: Permission hint khi user không có quyền hành động -->
      <div v-if="showPermissionHint" class="card p-4 bg-amber-50 border-amber-200 text-sm text-amber-800 flex items-start gap-3">
        <svg class="w-5 h-5 shrink-0 text-amber-500 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
        </svg>
        <div>
          <p class="font-medium">Bạn không có quyền thực hiện hành động trên phiếu này.</p>
          <p class="text-xs mt-0.5">Liên hệ quản trị để cấp vai trò Kỹ thuật viên Hiệu chuẩn (Calibration User/Manager).</p>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-2 justify-end pt-2 flex-wrap">
        <button class="btn-ghost text-sm" @click="router.push('/calibration')">Quay lại</button>
        <button
v-if="canCancel" class="bg-slate-500 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm"
          @click="showCancelModal = true">
Hủy phiếu
</button>
        <button
v-if="canStartCal" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          :disabled="startingCal"
          @click="doStartCal">
{{ startingCal ? 'Đang bắt đầu...' : 'Bắt đầu hiệu chuẩn' }}
</button>
        <button
v-if="canSendToLab" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm"
          @click="showSendModal = true">
Gửi phòng hiệu chuẩn
</button>
        <button
v-if="canReceiveCert" class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm"
          @click="showReceiveModal = true">
Nhận chứng chỉ
</button>
        <button
v-if="!isSubmitted && canExecuteCal" class="btn-ghost text-sm" :disabled="saving" @click="save">
          {{ saving ? 'Đang lưu...' : 'Lưu' }}
        </button>
        <!-- "Gửi duyệt" CHỈ ở giai đoạn nhập kết quả (In Progress / Đã nhận chứng chỉ),
             KHÔNG lộ disabled-kèm-tooltip ở Scheduled/Sent to Lab như trước. -->
        <div v-if="canEnterResults" class="relative group">
          <button
            class="btn-primary text-sm"
            :disabled="submitting || !canSubmitCal"
            @click="openSubmitModal"
          >
            {{ submitting ? 'Đang gửi duyệt...' : 'Gửi duyệt' }}
          </button>
          <div
            v-if="!canSubmitCal"
            class="absolute bottom-full right-0 mb-2 w-64 bg-slate-800 text-white text-xs rounded-md px-2.5 py-1.5 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-10"
          >
            {{ submitBlockReason }}
          </div>
        </div>
      </div>
    </template>

    <!-- Send to Lab Modal -->
    <div v-if="showSendModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Gửi phòng hiệu chuẩn</h2>
        <div>
          <label for="send-date" class="block text-sm font-medium mb-1">Ngày gửi</label>
          <DateInput id="send-date" v-model="sendData.sent_date" class="form-input w-full text-sm" />
        </div>
        <div>
          <label for="send-lab" class="block text-sm font-medium mb-1">Phòng hiệu chuẩn</label>
          <input id="send-lab" v-model="sendData.lab_supplier" type="text" class="form-input w-full text-sm" placeholder="Quatest, Vilas..." />
        </div>
        <div>
          <label for="send-contract" class="block text-sm font-medium mb-1">Số hợp đồng</label>
          <input id="send-contract" v-model="sendData.lab_contract_ref" type="text" class="form-input w-full text-sm" />
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border rounded-lg" @click="showSendModal = false">Hủy</button>
          <button :disabled="actionLoading" class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50" @click="doSendToLab">
            {{ actionLoading ? 'Đang gửi...' : 'Xác nhận gửi' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Receive Certificate Modal -->
    <div v-if="showReceiveModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Nhận chứng chỉ hiệu chuẩn</h2>
        <div>
          <label for="recv-file" class="block text-sm font-medium mb-1">File chứng chỉ <span class="text-red-500">*</span></label>
          <div class="flex items-center gap-2">
            <input
              id="recv-file"
              type="file"
              accept="application/pdf,image/*"
              class="form-input w-full text-sm"
              :disabled="uploadingCert"
              @change="uploadCertificateFile"
            />
            <span v-if="uploadingCert" class="text-xs text-slate-500">Đang tải lên...</span>
          </div>
          <p v-if="recvData.certificate_file" class="text-xs text-emerald-700 mt-1 truncate">
            Đã đính kèm:
            <a :href="recvData.certificate_file" target="_blank" class="underline">{{ recvData.certificate_file }}</a>
          </p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label for="recv-num" class="block text-sm font-medium mb-1">Số chứng chỉ <span class="text-red-500">*</span></label>
            <input id="recv-num" v-model="recvData.certificate_number" type="text" class="form-input w-full text-sm" />
          </div>
          <div>
            <label for="recv-date" class="block text-sm font-medium mb-1">Ngày cấp <span class="text-red-500">*</span></label>
            <DateInput id="recv-date" v-model="recvData.certificate_date" class="form-input w-full text-sm" />
          </div>
        </div>
        <div>
          <label for="recv-trace" class="block text-sm font-medium mb-1">Tham chiếu liên kết chuẩn</label>
          <input id="recv-trace" v-model="recvData.traceability_reference" type="text" class="form-input w-full text-sm" />
        </div>
        <div>
          <label for="recv-std" class="block text-sm font-medium mb-1">Số serial thiết bị chuẩn</label>
          <input id="recv-std" v-model="recvData.reference_standard_serial" type="text" class="form-input w-full text-sm" />
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border rounded-lg" @click="showReceiveModal = false">Hủy</button>
          <button :disabled="actionLoading" class="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50" @click="doReceiveCert">
            {{ actionLoading ? 'Đang xử lý...' : 'Xác nhận' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Cancel Modal -->
    <div v-if="showCancelModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Hủy phiếu hiệu chuẩn</h2>
        <div>
          <label for="cal-cancel-reason" class="block text-sm font-medium mb-1">Lý do <span class="text-red-500">*</span></label>
          <textarea id="cal-cancel-reason" v-model="cancelReason" rows="3" class="form-input w-full text-sm" placeholder="Lý do hủy phiếu..."></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border rounded-lg" @click="showCancelModal = false">Quay lại</button>
          <button :disabled="actionLoading || !cancelReason.trim()" class="px-4 py-2 text-sm bg-slate-600 text-white rounded-lg hover:bg-slate-700 disabled:opacity-50" @click="doCancel">
            {{ actionLoading ? 'Đang hủy...' : 'Xác nhận hủy' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Submit Confirmation Modal (IMM-11-E: thay confirm() native) -->
    <div v-if="showSubmitModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Xác nhận gửi duyệt phiếu hiệu chuẩn</h2>
        <div class="text-sm text-slate-600 space-y-1.5">
          <div>Số tham số đo: <strong>{{ measurementCount }}</strong></div>
          <div>
            Kết quả tổng:
            <strong :class="computedOverall === 'Failed' ? 'text-red-600' : 'text-green-600'">
              {{ computedOverall === 'Failed' ? 'Không đạt' : computedOverall === 'Passed' ? 'Đạt' : '—' }}
            </strong>
          </div>
          <p class="text-xs text-amber-700 bg-amber-50 p-2 rounded">
            Sau khi gửi duyệt sẽ không thể chỉnh sửa phiếu (BR-11-05).
          </p>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border rounded-lg" @click="showSubmitModal = false">Hủy</button>
          <button :disabled="submitting" class="btn-primary text-sm disabled:opacity-50" @click="submit">
            {{ submitting ? 'Đang gửi duyệt...' : 'Xác nhận gửi duyệt' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
