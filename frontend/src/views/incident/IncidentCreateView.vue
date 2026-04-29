<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { reportIncident } from '@/api/imm12'
import SmartSelect from '@/components/common/SmartSelect.vue'
import { useFormDraft } from '@/composables/useFormDraft'

const router = useRouter()

const form = ref({
  asset: '',
  incident_type: '',
  severity: '',
  description: '',
  immediate_action: '',
  fault_code: '',
  workaround_applied: false,
  clinical_impact: '',
  patient_affected: false,
  patient_impact_description: '',
})

const { clear: clearDraft } = useFormDraft('incident-create', form)

const saving = ref(false)
const error = ref('')

const SEVERITIES = ['Low', 'Medium', 'High', 'Critical'] as const
const INCIDENT_TYPES = ['Failure', 'Safety Event', 'Near Miss', 'Malfunction'] as const

async function submit() {
  if (!form.value.asset || !form.value.incident_type || !form.value.severity || !form.value.description.trim()) {
    error.value = 'Vui lòng điền đầy đủ thông tin bắt buộc (*).'
    return
  }
  if (form.value.severity === 'Critical' && !form.value.clinical_impact.trim()) {
    error.value = 'Incident Critical bắt buộc nhập Tác động lâm sàng.'
    return
  }
  if (form.value.patient_affected && !form.value.patient_impact_description.trim()) {
    error.value = 'Vui lòng mô tả ảnh hưởng đến bệnh nhân.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const res = await reportIncident({
      asset: form.value.asset,
      incident_type: form.value.incident_type,
      severity: form.value.severity,
      description: form.value.description,
      fault_code: form.value.fault_code,
      workaround_applied: form.value.workaround_applied ? 1 : 0,
      clinical_impact: form.value.clinical_impact,
      patient_affected: form.value.patient_affected ? 1 : 0,
      patient_impact_description: form.value.patient_impact_description,
      immediate_action: form.value.immediate_action,
    })
    const r = res as unknown as { name?: string }
    if (r?.name) {
      clearDraft()
      router.push('/incidents/dashboard')
    }
    else error.value = 'Lỗi khi tạo Incident Report'
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi tạo Incident Report'
  }
  saving.value = false
}

</script>

<template>
  <div class="page-container animate-fade-in space-y-6">
    <div class="flex items-center gap-3">
      <button class="text-gray-500 hover:text-gray-700 text-sm" @click="router.push('/incidents/list')">← Quay lại</button>
      <h1 class="text-xl font-semibold text-gray-800">Tạo Incident Report</h1>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">{{ error }}</div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị <span class="text-red-500">*</span></label>
        <SmartSelect v-model="form.asset" doctype="AC Asset" placeholder="Tìm thiết bị theo tên / mã / serial..." />
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label for="inc-type" class="block text-sm font-medium text-gray-700 mb-1">Loại sự cố <span class="text-red-500">*</span></label>
          <select id="inc-type" v-model="form.incident_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">-- Chọn --</option>
            <option v-for="t in INCIDENT_TYPES" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
        <div>
          <label for="inc-severity" class="block text-sm font-medium text-gray-700 mb-1">Severity <span class="text-red-500">*</span></label>
          <select id="inc-severity" v-model="form.severity" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">-- Chọn --</option>
            <option v-for="s in SEVERITIES" :key="s" :value="s">{{ s }}</option>
          </select>
          <p v-if="form.severity === 'Critical'" class="text-xs text-red-600 mt-1">⚠ Critical sẽ tự động tạo CAPA khi submit.</p>
        </div>
      </div>

      <div>
        <label for="inc-description" class="block text-sm font-medium text-gray-700 mb-1">Mô tả chi tiết sự cố <span class="text-red-500">*</span></label>
        <textarea id="inc-description" v-model="form.description" rows="4" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="Mô tả đầy đủ sự cố, triệu chứng, bối cảnh..."></textarea>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label for="inc-fault-code" class="block text-sm font-medium text-gray-700 mb-1">Mã lỗi (Fault Code)</label>
          <input id="inc-fault-code" v-model="form.fault_code" type="text" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="vd: E-42, HW-FAIL..." />
          <p class="text-xs text-gray-500 mt-1">Dùng cho phát hiện chronic failure (≥3 sự cố cùng mã trong 90 ngày).</p>
        </div>
        <div class="flex items-end">
          <label class="flex items-center gap-2 cursor-pointer">
            <input id="inc-workaround" v-model="form.workaround_applied" type="checkbox" class="w-4 h-4 rounded" />
            <span class="text-sm text-gray-700">Đã áp dụng workaround tạm thời</span>
          </label>
        </div>
      </div>

      <div>
        <label for="inc-immediate" class="block text-sm font-medium text-gray-700 mb-1">Hành động khắc phục ngay</label>
        <textarea id="inc-immediate" v-model="form.immediate_action" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="Đã làm gì ngay tại chỗ để xử lý sự cố..."></textarea>
      </div>

      <div v-if="form.severity === 'Critical'" class="bg-red-50 border border-red-200 rounded-lg p-4">
        <label for="inc-clinical-impact" class="block text-sm font-medium text-red-800 mb-1">Tác động lâm sàng (clinical impact) <span class="text-red-500">*</span></label>
        <textarea id="inc-clinical-impact" v-model="form.clinical_impact" rows="2" class="w-full border border-red-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400" placeholder="Mô tả mức độ ảnh hưởng đến hoạt động lâm sàng / bệnh nhân..."></textarea>
      </div>

      <div class="bg-orange-50 border border-orange-200 rounded-lg p-4 space-y-3">
        <label class="flex items-center gap-2 cursor-pointer">
          <input id="inc-patient-affected" v-model="form.patient_affected" type="checkbox" class="w-4 h-4 rounded" />
          <span class="text-sm font-medium text-orange-800">Có ảnh hưởng đến bệnh nhân</span>
        </label>
        <div v-if="form.patient_affected">
          <label for="inc-patient-impact" class="block text-sm text-orange-700 mb-1">Mô tả ảnh hưởng <span class="text-red-500">*</span></label>
          <textarea id="inc-patient-impact" v-model="form.patient_impact_description" rows="2" class="w-full border border-orange-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400" placeholder="Ảnh hưởng đến bệnh nhân như thế nào..."></textarea>
        </div>
      </div>

      <button
        :disabled="saving"
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium"
        @click="submit"
      >
{{ saving ? 'Đang tạo...' : 'Tạo Incident Report' }}
</button>
    </div>
  </div>
</template>
