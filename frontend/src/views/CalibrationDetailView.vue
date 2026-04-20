<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getCalibration, updateCalibration, submitCalibration } from '@/api/imm11'
import type { AssetCalibration, CalibrationMeasurement } from '@/api/imm11'

const props = defineProps<{ id: string }>()
const router = useRouter()

const form = ref<Partial<AssetCalibration> & { measurements?: CalibrationMeasurement[] }>({})
const loading = ref(false)
const saving = ref(false)
const submitting = ref(false)
const err = ref('')

const isSubmitted = computed(() => form.value.docstatus === 1)
const isFailed = computed(() => form.value.overall_result === 'Failed')

const statusColor: Record<string, string> = {
  Scheduled: 'bg-blue-100 text-blue-700',
  'Sent to Lab': 'bg-indigo-100 text-indigo-700',
  'In Progress': 'bg-yellow-100 text-yellow-700',
  'Certificate Received': 'bg-purple-100 text-purple-700',
  Passed: 'bg-green-100 text-green-700',
  Failed: 'bg-red-100 text-red-700',
  'Conditionally Passed': 'bg-orange-100 text-orange-700',
  Cancelled: 'bg-gray-100 text-gray-500',
}

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
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
  finally { saving.value = false }
}

async function submit() {
  if (!confirm('Submit phiếu hiệu chuẩn? Sau khi submit sẽ không thể chỉnh sửa.')) return
  submitting.value = true; err.value = ''
  try {
    await submitCalibration(props.id)
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi submit' }
  finally { submitting.value = false }
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
  <div class="page-container animate-fade-in space-y-5 max-w-4xl">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button class="btn-ghost text-sm" @click="router.push('/calibration')">← Quay lại</button>
        <div>
          <p class="text-xs text-slate-400">IMM-11 · Phiếu hiệu chuẩn</p>
          <h1 class="text-xl font-bold text-slate-900">{{ form.name }}</h1>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="form.status" class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
          :class="statusColor[form.status] || 'bg-gray-100'">{{ form.status }}</span>
        <span v-if="isSubmitted && form.overall_result" class="text-xs font-semibold px-2 py-1 rounded"
          :class="form.overall_result === 'Passed' ? 'text-green-700 bg-green-50' : 'text-red-600 bg-red-50'">
          {{ form.overall_result }}
        </span>
      </div>
    </div>

    <div v-if="err" class="alert-error">{{ err }}</div>
    <div v-if="loading" class="card p-8 text-center text-slate-400">Đang tải...</div>

    <template v-else>
      <!-- Info Grid -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b">Thông tin chung</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <p class="text-xs text-slate-400 mb-1">Thiết bị</p>
            <p class="font-medium">{{ form.asset }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Loại hiệu chuẩn</p>
            <p>{{ form.calibration_type }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Kỹ thuật viên</p>
            <p>{{ form.technician }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Ngày dự kiến</p>
            <p>{{ form.scheduled_date }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Ngày thực hiện</p>
            <template v-if="!isSubmitted">
              <input v-model="form.actual_date" type="date" class="form-input w-full text-xs" />
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
        <h2 class="text-sm font-semibold text-slate-700 pb-2 border-b">Cập nhật trạng thái</h2>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="form-label">Trạng thái</label>
            <select v-model="form.status" class="form-select w-full text-sm">
              <option value="Scheduled">Đã lên lịch</option>
              <option value="Sent to Lab">Đã gửi phòng hiệu chuẩn</option>
              <option value="In Progress">Đang thực hiện</option>
              <option value="Certificate Received">Đã nhận chứng nhận</option>
              <option value="Cancelled">Đã hủy</option>
            </select>
          </div>
          <div v-if="form.calibration_type === 'External'">
            <label class="form-label">Ngày gửi phòng hiệu chuẩn</label>
            <input v-model="form.sent_date" type="date" class="form-input w-full text-sm" />
          </div>
        </div>

        <template v-if="form.calibration_type === 'External'">
          <div class="grid grid-cols-2 gap-4">
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
              <input v-model="form.certificate_date" type="date" class="form-input w-full text-sm" />
            </div>
          </div>
        </template>

        <template v-if="form.calibration_type === 'In-House'">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="form-label">Serial thiết bị chuẩn</label>
              <input v-model="form.reference_standard_serial" type="text" class="form-input w-full text-sm" />
            </div>
            <div>
              <label class="form-label">Traceability ref</label>
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
          <button v-if="!isSubmitted" class="text-blue-600 text-xs font-medium" @click="addMeasurement">+ Thêm tham số</button>
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
            <input v-if="!isSubmitted" v-model="m.parameter_name" class="col-span-2 form-input text-xs px-2 py-1" placeholder="Tên tham số" />
            <span v-else class="col-span-2 text-sm font-medium">{{ m.parameter_name }}</span>

            <input v-if="!isSubmitted" v-model="m.unit" class="form-input text-xs px-2 py-1" placeholder="cmH₂O" />
            <span v-else class="text-sm">{{ m.unit }}</span>

            <input v-if="!isSubmitted" v-model.number="m.nominal_value" type="number" class="form-input text-xs px-2 py-1" />
            <span v-else class="text-sm">{{ m.nominal_value }}</span>

            <input v-if="!isSubmitted" v-model.number="m.tolerance_positive" type="number" class="form-input text-xs px-2 py-1" placeholder="5" />
            <span v-else class="text-sm">±{{ m.tolerance_positive }}%</span>

            <input v-if="!isSubmitted" v-model.number="m.measured_value" type="number" step="any" class="form-input text-xs px-2 py-1"
              :class="m.measured_value !== null && computeResult(m) === 'Fail' ? 'border-red-400 bg-red-50' : ''" />
            <span v-else class="text-sm">{{ m.measured_value ?? '—' }}</span>

            <div class="flex items-center gap-1">
              <span v-if="m.pass_fail" class="text-xs font-semibold" :class="m.pass_fail === 'Pass' ? 'text-green-600' : 'text-red-600'">
                {{ m.pass_fail }}
              </span>
              <span v-else-if="m.measured_value !== null && m.measured_value !== undefined" class="text-xs font-semibold"
                :class="computeResult(m) === 'Pass' ? 'text-green-600' : 'text-red-600'">
                {{ computeResult(m) }}
              </span>
              <button v-if="!isSubmitted" class="text-red-400 text-xs ml-auto" @click="removeMeasurement(i)">✕</button>
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

      <!-- Actions -->
      <div class="flex gap-2 justify-end pt-2">
        <button class="btn-ghost text-sm" @click="router.push('/calibration')">Quay lại</button>
        <template v-if="!isSubmitted">
          <button class="btn-ghost text-sm" :disabled="saving" @click="save">
            {{ saving ? 'Đang lưu...' : 'Lưu' }}
          </button>
          <button class="btn-primary text-sm" :disabled="submitting" @click="submit">
            {{ submitting ? 'Đang submit...' : 'Submit' }}
          </button>
        </template>
      </div>
    </template>
  </div>
</template>
