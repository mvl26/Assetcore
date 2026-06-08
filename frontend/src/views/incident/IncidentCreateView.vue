<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { reportIncident } from '@/api/imm12'
import SmartSelect from '@/components/common/SmartSelect.vue'
import { useFormDraft } from '@/composables/useFormDraft'
import { incidentSeverityLabel, INCIDENT_TYPE_LABEL } from '@/constants/labels'

const router = useRouter()
const route = useRoute()

// Provenance nguồn báo sự cố (mirror BE contract): chỉ 'qr-scan' khi điều hướng từ
// màn quét QR mới được coi là qr-scan, mọi giá trị khác (kể cả thiếu) → 'manual'.
const querySource = route.query.source === 'qr-scan' ? 'qr-scan' : 'manual'

const form = ref({
  asset: (route.query.asset as string) || '',
  incident_type: '',
  severity: '',
  description: '',
  immediate_action: '',
  fault_code: '',
  workaround_applied: false,
  clinical_impact: '',
  patient_affected: false,
  patient_impact_description: '',
  source: querySource as 'manual' | 'qr-scan',
})

const { clear: clearDraft } = useFormDraft('incident-create', form)

// Khi điều hướng từ /assets/:id (?asset=...) — luôn lấy asset từ query, kể cả khi
// có draft cũ trong localStorage (user vừa click "Báo sự cố" trên trang chi tiết).
const queryAsset = (route.query.asset as string) || ''
if (queryAsset) form.value.asset = queryAsset
// Khoá ô Thiết bị KHI và CHỈ KHI đến từ quét QR (source=qr-scan) + có asset prefill.
// Tạo thủ công (manual / không source) → ô Thiết bị editable như cũ (no regression).
const lockedFromScan = computed(
  () => route.query.source === 'qr-scan' && !!queryAsset,
)

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
      source: form.value.source,
    })
    if (res?.name) {
      clearDraft()
      router.push('/incidents/dashboard')
    }
    else error.value = 'Lỗi khi tạo Incident Report'
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Lỗi khi tạo Incident Report'
  }
  saving.value = false
}

</script>

<template>
  <div class="page-container animate-fade-in space-y-6">
    <div class="flex items-center gap-3">
      <button class="text-slate-500 hover:text-slate-700 text-sm" @click="router.push('/incidents/list')">← Quay lại</button>
      <h1 class="text-xl font-semibold text-slate-800">Tạo Incident Report</h1>
    </div>

    <div class="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
      <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">{{ error }}</div>

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">
          Thiết bị <span class="text-red-500">*</span>
          <span
            v-if="lockedFromScan"
            role="status"
            aria-live="polite"
            class="ml-2 inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700 align-middle"
          >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" /></svg>
            Tạo từ quét QR
          </span>
        </label>
        <SmartSelect v-model="form.asset" doctype="AC Asset" :disabled="lockedFromScan" placeholder="Tìm thiết bị theo tên / mã / serial..." />
        <p v-if="lockedFromScan" class="text-xs text-slate-500 mt-1">Thiết bị đã được xác định từ mã QR — không thể thay đổi.</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label for="inc-type" class="block text-sm font-medium text-slate-700 mb-1">Loại sự cố <span class="text-red-500">*</span></label>
          <select id="inc-type" v-model="form.incident_type" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">-- Chọn --</option>
            <option v-for="t in INCIDENT_TYPES" :key="t" :value="t">{{ INCIDENT_TYPE_LABEL[t] ?? t }}</option>
          </select>
        </div>
        <div>
          <label for="inc-severity" class="block text-sm font-medium text-slate-700 mb-1">Mức độ <span class="text-red-500">*</span></label>
          <select id="inc-severity" v-model="form.severity" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">-- Chọn --</option>
            <option v-for="s in SEVERITIES" :key="s" :value="s">{{ incidentSeverityLabel(s) }}</option>
          </select>
          <p v-if="form.severity === 'Critical'" class="text-xs text-red-600 mt-1">Mức Nghiêm trọng sẽ tự động đưa thiết bị về Ngừng sử dụng và bắt buộc lập RCA trước khi đóng.</p>
        </div>
      </div>

      <div>
        <label for="inc-description" class="block text-sm font-medium text-slate-700 mb-1">Mô tả chi tiết sự cố <span class="text-red-500">*</span></label>
        <textarea id="inc-description" v-model="form.description" rows="4" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="Mô tả đầy đủ sự cố, triệu chứng, bối cảnh..."></textarea>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label for="inc-fault-code" class="block text-sm font-medium text-slate-700 mb-1">Mã lỗi (Fault Code)</label>
          <input id="inc-fault-code" v-model="form.fault_code" type="text" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="vd: E-42, HW-FAIL..." />
          <p class="text-xs text-slate-500 mt-1">Dùng cho phát hiện chronic failure (≥3 sự cố cùng mã trong 90 ngày).</p>
        </div>
        <div class="flex items-end">
          <label class="flex items-center gap-2 cursor-pointer">
            <input id="inc-workaround" v-model="form.workaround_applied" type="checkbox" class="w-4 h-4 rounded" />
            <span class="text-sm text-slate-700">Đã áp dụng workaround tạm thời</span>
          </label>
        </div>
      </div>

      <div>
        <label for="inc-immediate" class="block text-sm font-medium text-slate-700 mb-1">Hành động khắc phục ngay</label>
        <textarea id="inc-immediate" v-model="form.immediate_action" rows="2" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="Đã làm gì ngay tại chỗ để xử lý sự cố..."></textarea>
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
