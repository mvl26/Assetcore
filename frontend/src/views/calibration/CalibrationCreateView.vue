<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-11 Calibration Create
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { createCalibration } from '@/api/imm11'
import { frappeGet } from '@/api/helpers'
import SmartSelect from '@/components/common/SmartSelect.vue'
import DateInput from '@/components/common/DateInput.vue'
import { useFormDraft } from '@/composables/useFormDraft'
import { useApi } from '@/composables/useApi'

interface AssetMeta {
  device_model?: string
  asset_name?: string
  lifecycle_status?: string
  risk_class?: string
  location?: string
}

interface ScheduleMeta {
  calibration_type?: string
  interval_days?: number
  next_due_date?: string
  reference_standard?: string
}

const router = useRouter()
const route = useRoute()
const api = useApi()

const form = ref({
  asset: (route.query.asset as string) || '',
  calibration_type: 'External' as 'External' | 'In-House',
  scheduled_date: '',
  technician: '',
  lab_supplier: '',
  lab_accreditation_number: '',
  reference_standard_serial: '',
  traceability_reference: '',
  calibration_schedule: (route.query.schedule as string) || '',
  is_recalibration: 0,
})

const { clear: clearDraft } = useFormDraft('calibration-create', form)
const saving = ref(false)
const err = ref('')
const assetMeta = ref<AssetMeta | null>(null)
const scheduleMeta = ref<ScheduleMeta | null>(null)

const isExternal = computed(() => form.value.calibration_type === 'External')
const isInHouse = computed(() => form.value.calibration_type === 'In-House')

const canSubmit = computed(() => {
  if (!form.value.asset || !form.value.scheduled_date || !form.value.technician) return false
  if (isExternal.value && !form.value.lab_supplier) return false
  if (isInHouse.value
    && !(form.value.reference_standard_serial && form.value.traceability_reference)) return false
  if (assetMeta.value?.lifecycle_status === 'Decommissioned') return false
  return true
})

async function loadAssetMeta() {
  if (!form.value.asset) { assetMeta.value = null; return }
  try {
    const r = await frappeGet<AssetMeta>('frappe.client.get_value', {
      doctype: 'AC Asset',
      filters: form.value.asset,
      fieldname: JSON.stringify(['device_model', 'asset_name', 'lifecycle_status', 'risk_class', 'location']),
    })
    assetMeta.value = r ?? null
  } catch { assetMeta.value = null }
}

async function loadSchedule() {
  if (!form.value.calibration_schedule) { scheduleMeta.value = null; return }
  try {
    const r = await frappeGet<ScheduleMeta & { name?: string }>(
      'frappe.client.get_value',
      {
        doctype: 'IMM Calibration Schedule',
        filters: form.value.calibration_schedule,
        fieldname: JSON.stringify(['calibration_type', 'interval_days', 'next_due_date', 'reference_standard']),
      },
    )
    scheduleMeta.value = r ?? null
    if (r?.calibration_type) {
      form.value.calibration_type = r.calibration_type as 'External' | 'In-House'
    }
    if (r?.next_due_date && !form.value.scheduled_date) {
      form.value.scheduled_date = r.next_due_date
    }
    if (r?.reference_standard && !form.value.reference_standard_serial) {
      form.value.reference_standard_serial = r.reference_standard
    }
  } catch { scheduleMeta.value = null }
}

watch(() => form.value.asset, loadAssetMeta)
watch(() => form.value.calibration_schedule, loadSchedule)

async function submit() {
  if (!canSubmit.value) {
    err.value = 'Vui lòng điền đầy đủ thông tin bắt buộc theo loại hiệu chuẩn.'
    return
  }
  saving.value = true; err.value = ''
  const res = await api.run(
    () => createCalibration({
      ...form.value,
      lab_supplier: form.value.lab_supplier || undefined,
      lab_accreditation_number: form.value.lab_accreditation_number || undefined,
      reference_standard_serial: form.value.reference_standard_serial || undefined,
      traceability_reference: form.value.traceability_reference || undefined,
      calibration_schedule: form.value.calibration_schedule || undefined,
    } as Parameters<typeof createCalibration>[0]),
    {
      successMessage: 'Đã tạo phiếu hiệu chuẩn',
      onFieldError: (fields) => { err.value = Object.values(fields).join('; ') },
    },
  )
  saving.value = false
  const r = res as unknown as { name?: string } | null
  if (r?.name) {
    clearDraft()
    router.push(`/calibration/${r.name}`)
  }
}

onMounted(() => {
  if (form.value.asset) loadAssetMeta()
  if (form.value.calibration_schedule) loadSchedule()
})
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center gap-3">
      <button class="btn-ghost" @click="router.push('/calibration')">← Quay lại</button>
      <h1 class="text-xl font-bold text-slate-900">Tạo Phiếu Hiệu chuẩn</h1>
    </div>

    <div v-if="err" class="alert-error">{{ err }}</div>

    <form class="card p-5 space-y-4" @submit.prevent="submit">
      <!-- Asset -->
      <div>
        <label class="form-label">Thiết bị <span class="text-red-500">*</span></label>
        <SmartSelect v-model="form.asset" doctype="AC Asset" placeholder="Tìm thiết bị..." />
        <div v-if="assetMeta" class="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div class="bg-gray-50 rounded px-2 py-1.5"><span class="text-gray-500">Tên:</span> <b>{{ assetMeta.asset_name || '—' }}</b></div>
          <div class="bg-gray-50 rounded px-2 py-1.5"><span class="text-gray-500">Model:</span> {{ assetMeta.device_model || '—' }}</div>
          <div :class="['rounded px-2 py-1.5', assetMeta.lifecycle_status === 'Decommissioned' ? 'bg-red-50 text-red-700' : 'bg-gray-50']">
            <span class="text-gray-500">Trạng thái:</span> <b>{{ assetMeta.lifecycle_status || '—' }}</b>
          </div>
          <div class="bg-gray-50 rounded px-2 py-1.5"><span class="text-gray-500">Risk:</span> <b>{{ assetMeta.risk_class || '—' }}</b></div>
        </div>
        <div v-if="assetMeta?.lifecycle_status === 'Decommissioned'" class="mt-2 alert-error">
          ⛔ Thiết bị đã thanh lý — không thể hiệu chuẩn.
        </div>
      </div>

      <!-- Schedule (optional) -->
      <div>
        <label class="form-label">Lịch hiệu chuẩn (nếu có)</label>
        <SmartSelect v-model="form.calibration_schedule" doctype="IMM Calibration Schedule" placeholder="Tìm lịch..." />
        <div v-if="scheduleMeta" class="mt-2 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800 grid grid-cols-3 gap-2">
          <div><span class="text-blue-600">Loại:</span> <b>{{ scheduleMeta.calibration_type }}</b></div>
          <div><span class="text-blue-600">Chu kỳ:</span> <b>{{ scheduleMeta.interval_days }} ngày</b></div>
          <div><span class="text-blue-600">Lần tới:</span> <b>{{ scheduleMeta.next_due_date || '—' }}</b></div>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="form-label">Loại hiệu chuẩn <span class="text-red-500">*</span></label>
          <select v-model="form.calibration_type" class="form-select w-full">
            <option value="External">External (Bên ngoài)</option>
            <option value="In-House">In-House (Nội bộ)</option>
          </select>
        </div>
        <div>
          <label class="form-label">Ngày dự kiến <span class="text-red-500">*</span></label>
          <DateInput v-model="form.scheduled_date" class="form-input w-full" required />
        </div>
        <div>
          <label class="form-label">Kỹ thuật viên <span class="text-red-500">*</span></label>
          <SmartSelect v-model="form.technician" doctype="User" placeholder="Tìm người dùng..." />
        </div>
        <div class="flex items-center gap-2">
          <input id="recal" v-model="form.is_recalibration" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 text-blue-600 rounded" />
          <label for="recal" class="text-sm text-slate-700">Là tái hiệu chuẩn sau CAPA</label>
        </div>
      </div>

      <!-- External Lab section -->
      <div v-if="isExternal" class="border-l-4 border-purple-300 pl-4 space-y-3 bg-purple-50/30 py-3">
        <h3 class="font-semibold text-sm text-purple-800">Thông tin Lab External</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Lab hiệu chuẩn <span class="text-red-500">*</span></label>
            <SmartSelect v-model="form.lab_supplier" doctype="AC Supplier" placeholder="Tìm lab..." />
          </div>
          <div>
            <label class="form-label">Số công nhận ISO 17025</label>
            <input v-model="form.lab_accreditation_number" class="form-input w-full" placeholder="VILAS-XXX" />
          </div>
        </div>
      </div>

      <!-- In-House section -->
      <div v-if="isInHouse" class="border-l-4 border-emerald-300 pl-4 space-y-3 bg-emerald-50/30 py-3">
        <h3 class="font-semibold text-sm text-emerald-800">Thông tin In-House</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Serial chuẩn đo lường <span class="text-red-500">*</span></label>
            <input v-model="form.reference_standard_serial" class="form-input w-full" placeholder="VD: STD-2026-001" />
          </div>
          <div>
            <label class="form-label">Traceability ref <span class="text-red-500">*</span></label>
            <input v-model="form.traceability_reference" class="form-input w-full" placeholder="VD: NIST-12345" />
          </div>
        </div>
        <p class="text-xs text-emerald-700">
          Cần liên kết tới chuẩn đã được công nhận để đảm bảo traceability theo ISO 17025.
        </p>
      </div>

      <div class="flex gap-2 justify-end pt-2">
        <button type="button" class="btn-ghost" @click="router.push('/calibration')">Huỷ</button>
        <button type="submit" class="btn-primary" :disabled="!canSubmit || saving">
          {{ saving ? 'Đang tạo...' : 'Tạo phiếu' }}
        </button>
      </div>
    </form>
  </div>
</template>
