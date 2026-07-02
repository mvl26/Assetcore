<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-11 Calibration Create
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { createCalibration, listCalibrationSchedules, type CalibrationSchedule } from '@/api/imm11'
import { getAssetActionMeta } from '@/api/imm00'
import { frappeGet } from '@/api/helpers'
import { lifecycleStatusLabel, riskClassificationLabel, calibrationTypeLabel } from '@/constants/labels'
import SmartSelect from '@/components/common/SmartSelect.vue'
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import DateInput from '@/components/common/DateInput.vue'
import { useFormDraft } from '@/composables/useFormDraft'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'

// Panel meta thiết bị — derive từ meta NẠC (getAssetActionMeta perm-aware, 6 field,
// KHÔNG full-doc tài chính). Hiển thị display-name (device_model_name /
// location_name), KHÔNG raw Link id. Field rủi ro là risk_classification (field
// 'risk_class' KHÔNG tồn tại trên AC Asset).
interface AssetMeta {
  device_model_name?: string
  asset_name?: string
  lifecycle_status?: string
  risk_classification?: string
  location_name?: string
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
const toast = useToast()
const notify = useNotify()
const todayIso = new Date().toISOString().slice(0, 10)
const assetSchedules = ref<CalibrationSchedule[]>([])
const loadingSchedules = ref(false)

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

// Deep-link từ màn quét QR (D3): query hằng = {asset, source}. Field nội bộ Cal = 'asset'.
// Provenance: chỉ 'qr-scan' mới coi là quét QR; mọi giá trị khác (kể cả thiếu) → manual.
// Ưu tiên asset từ query (tránh draft cũ che mất thiết bị vừa xác định) + khoá ô Thiết bị
// KHI và CHỈ KHI đến từ quét QR + có asset prefill (no regression khi tạo thủ công).
const queryAsset = (route.query.asset as string) || ''
if (queryAsset) form.value.asset = queryAsset
const querySource = route.query.source === 'qr-scan' ? 'qr-scan' : 'manual'
const lockedFromScan = computed(() => querySource === 'qr-scan' && !!queryAsset)

const saving = ref(false)
const err = ref('')
const assetMeta = ref<AssetMeta | null>(null)
const scheduleMeta = ref<ScheduleMeta | null>(null)

const isExternal = computed(() => form.value.calibration_type === 'External')
const isInHouse = computed(() => form.value.calibration_type === 'In-House')

// AC2/AC3: Nhãn VI an toàn cho ô "Mức rủi ro" qua SSoT riskClassificationLabel
// (parity AC1 màn CM). risk_classification ∈ {Low,Medium,High,Critical} (fetch_from
// device_model trên AC Asset) — KHÔNG nhầm risk_class (A/B/C/D field KHÁC).
//   rỗng/whitespace/undefined → 'Chưa phân loại' (parity scan-info Vòng 38, 1 SSoT).
//   in-enum → VI (Thấp/Trung bình/Cao/Nghiêm trọng).
//   drift/legacy ngoài 4 enum → 'Khác' (KHÔNG leak EN/code thô).
const riskClassDisplay = computed(() => {
  const r = (assetMeta.value?.risk_classification ?? '').trim()
  return r ? riskClassificationLabel(r) : 'Chưa phân loại'
})

const canSubmit = computed(() => {
  if (!form.value.asset || !form.value.scheduled_date || !form.value.technician) return false
  if (isExternal.value && !form.value.lab_supplier) return false
  if (isInHouse.value
    && !(form.value.reference_standard_serial && form.value.traceability_reference)) return false
  if (assetMeta.value?.lifecycle_status === 'Decommissioned') return false
  return true
})

// Nạp meta qua getAssetActionMeta (api/imm00) — endpoint NẠC perm-aware (IDOR guard
// + DocPerm read ở BE), CHỈ 6 field meta → KHÔNG over-fetch giá mua/khấu hao/giá trị
// sổ sách qua đường QR scan-action. KHÔNG dùng frappe.client.get_value (LL-FE-40).
// Lỗi (403 vendor-IDOR / 404 / network) → assetMeta=null (fail-safe): panel ẩn,
// KHÔNG vỡ trang, KHÔNG leak raw exception/email/qr_token ra UI.
async function loadAssetMeta() {
  if (!form.value.asset) { assetMeta.value = null; return }
  try {
    const a = await getAssetActionMeta(form.value.asset)
    assetMeta.value = {
      asset_name: a.asset_name,
      device_model_name: a.device_model_name,
      lifecycle_status: a.lifecycle_status,
      risk_classification: a.risk_classification,
      location_name: a.location_name,
    }
  } catch { assetMeta.value = null }
}

async function loadAssetSchedules() {
  assetSchedules.value = []
  if (!form.value.asset) return
  loadingSchedules.value = true
  try {
    const res = await listCalibrationSchedules({ asset: form.value.asset, is_active: 1 }, 1, 20)
    const list = res?.data || []
    assetSchedules.value = list
    // Nếu chưa có schedule được chọn và có lịch active → auto chọn lịch sớm nhất
    if (!form.value.calibration_schedule && list.length > 0) {
      const sorted = [...list].sort((a, b) => (a.next_due_date || '').localeCompare(b.next_due_date || ''))
      form.value.calibration_schedule = sorted[0].name
    }
  } catch { assetSchedules.value = [] }
  finally { loadingSchedules.value = false }
}

async function loadSchedule() {
  if (!form.value.calibration_schedule) { scheduleMeta.value = null; return }
  try {
    const r = await frappeGet<ScheduleMeta & { name?: string }>(
      '/api/method/frappe.client.get_value',
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

watch(() => form.value.asset, () => {
  loadAssetMeta()
  loadAssetSchedules()
})
watch(() => form.value.calibration_schedule, loadSchedule)

async function submit() {
  if (!canSubmit.value) {
    err.value = 'Vui lòng điền đầy đủ thông tin bắt buộc theo loại hiệu chuẩn.'
    return
  }
  if (form.value.scheduled_date && form.value.scheduled_date < todayIso) {
    err.value = 'Ngày dự kiến không được nằm trong quá khứ.'
    toast.error(err.value)
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
      silentSuccess: true,
      onFieldError: (fields) => { err.value = Object.values(fields).join('; ') },
    },
  )
  saving.value = false
  const r = res as unknown as { name?: string } | null
  if (r?.name) {
    clearDraft()
    notify.show({ code: MSG.IMM11_CREATE_SUCCESS, ctx: { name: r.name, asset: form.value.asset } })
    router.push(`/calibration/${r.name}`)
  }
}

onMounted(() => {
  if (form.value.asset) {
    loadAssetMeta()
    loadAssetSchedules()
  }
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
        <label class="form-label">
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
        <SmartSelect v-model="form.asset" doctype="AC Asset" :disabled="lockedFromScan" placeholder="Tìm thiết bị..." />
        <p v-if="lockedFromScan" class="text-xs text-slate-500 mt-1">Thiết bị đã được xác định từ mã QR — không thể thay đổi.</p>
        <!-- Panel meta thiết bị (scan-action) — a11y dl/dt/dd parity panel Incident
             round 26 + màn CM. Render khi assetMeta (loader-lỗi→null→ẩn). KHÔNG đổi
             điều kiện hiển thị / loader getAssetActionMeta / shape assetMeta. -->
        <section
          v-if="assetMeta"
          data-test="scan-cal-meta"
          aria-labelledby="scan-cal-meta-heading"
          class="mt-2"
        >
          <h3 id="scan-cal-meta-heading" class="sr-only">Thông tin thiết bị</h3>
          <dl class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            <div data-test="scan-cal-meta-name" class="bg-slate-50 rounded px-2 py-1.5">
              <dt class="inline text-slate-500">Tên:</dt>
              <dd class="inline font-bold">{{ assetMeta.asset_name || 'Chưa có tên' }}</dd>
            </div>
            <div data-test="scan-cal-meta-model" class="bg-slate-50 rounded px-2 py-1.5">
              <dt class="inline text-slate-500">Mẫu máy:</dt>
              <dd class="inline">{{ assetMeta.device_model_name || 'Chưa gán' }}</dd>
            </div>
            <div data-test="scan-cal-meta-location" class="bg-slate-50 rounded px-2 py-1.5">
              <dt class="inline text-slate-500">Vị trí:</dt>
              <dd class="inline">{{ assetMeta.location_name || 'Chưa gán' }}</dd>
            </div>
            <div
              data-test="scan-cal-meta-status"
              :class="['rounded px-2 py-1.5', assetMeta.lifecycle_status === 'Decommissioned' ? 'bg-red-50 text-red-700' : 'bg-slate-50']"
            >
              <dt class="inline text-slate-500">Trạng thái:</dt>
              <dd class="inline font-bold">{{ assetMeta.lifecycle_status ? lifecycleStatusLabel(assetMeta.lifecycle_status) : 'Chưa xác định' }}</dd>
            </div>
            <div data-test="scan-cal-meta-risk" class="bg-slate-50 rounded px-2 py-1.5">
              <dt class="inline text-slate-500">Mức rủi ro:</dt>
              <dd class="inline font-bold">{{ riskClassDisplay }}</dd>
            </div>
          </dl>
        </section>
        <div v-if="assetMeta?.lifecycle_status === 'Decommissioned'" class="mt-2 alert-error text-sm">
          Thiết bị đã thanh lý — không thể hiệu chuẩn.
        </div>
      </div>

      <!-- Schedule (optional) -->
      <div>
        <label class="form-label">Lịch hiệu chuẩn (nếu có)</label>
        <div v-if="loadingSchedules" class="text-xs text-slate-400 mb-2">Đang tải lịch sẵn có...</div>
        <div
          v-else-if="form.asset && assetSchedules.length > 0"
          class="mb-2 grid grid-cols-1 gap-1.5 max-h-40 overflow-auto"
        >
          <button
            v-for="s in assetSchedules" :key="s.name"
            type="button"
            class="flex items-center justify-between gap-2 px-3 py-2 rounded-lg border text-left text-xs transition-colors"
            :class="form.calibration_schedule === s.name
              ? 'bg-brand-50 border-brand-400 text-brand-800'
              : 'bg-white border-slate-200 hover:border-brand-300 text-slate-700'"
            @click="form.calibration_schedule = s.name"
          >
            <div>
              <div class="font-mono text-[11px]">{{ s.name }}</div>
              <div class="text-slate-500">
                {{ calibrationTypeLabel(s.calibration_type) }} · {{ s.interval_days }} ngày · Lần tới: <b>{{ s.next_due_date || '—' }}</b>
              </div>
            </div>
            <svg v-if="form.calibration_schedule === s.name" class="w-4 h-4 text-brand-600" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
          </button>
        </div>
        <div v-else-if="form.asset" class="mb-2 text-xs text-slate-400">
          Thiết bị này chưa có lịch hiệu chuẩn — có thể tìm lịch khác hoặc tạo phiếu tự do.
        </div>
        <SmartSelect v-model="form.calibration_schedule" doctype="IMM Calibration Schedule" placeholder="Tìm lịch khác..." />
        <div v-if="scheduleMeta" class="mt-2 bg-brand-50 border border-brand-200 rounded-lg p-3 text-xs text-brand-800 grid grid-cols-1 sm:grid-cols-3 gap-2">
          <div><span class="text-brand-600">Loại:</span> <b>{{ calibrationTypeLabel(scheduleMeta.calibration_type) }}</b></div>
          <div><span class="text-brand-600">Chu kỳ:</span> <b>{{ scheduleMeta.interval_days }} ngày</b></div>
          <div><span class="text-brand-600">Lần tới:</span> <b>{{ scheduleMeta.next_due_date || '—' }}</b></div>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="form-label">Loại hiệu chuẩn <span class="text-red-500">*</span></label>
          <select v-model="form.calibration_type" class="form-select w-full">
            <option value="External">Bên ngoài (ISO 17025)</option>
            <option value="In-House">Nội bộ</option>
          </select>
        </div>
        <div>
          <label class="form-label">Ngày dự kiến <span class="text-red-500">*</span></label>
          <DateInput v-model="form.scheduled_date" :min="todayIso" class="form-input w-full" required />
          <p class="text-[11px] text-slate-400 mt-1">Không được chọn ngày trong quá khứ.</p>
        </div>
        <div>
          <label class="form-label">Kỹ thuật viên <span class="text-red-500">*</span></label>
          <ApproverSelect v-model="form.technician" context="calibration" placeholder="Tìm kỹ thuật viên..." />
        </div>
        <div class="flex items-center gap-2">
          <input id="recal" v-model="form.is_recalibration" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 text-blue-600 rounded" />
          <label for="recal" class="text-sm text-slate-700">Là tái hiệu chuẩn sau hành động khắc phục/phòng ngừa</label>
        </div>
      </div>

      <!-- External Lab section -->
      <div v-if="isExternal" class="border-l-4 border-purple-300 pl-4 space-y-3 bg-purple-50/30 py-3">
        <h3 class="font-semibold text-sm text-purple-800">Thông tin Lab bên ngoài</h3>
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
        <h3 class="font-semibold text-sm text-emerald-800">Thông tin nội bộ</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Số serial chuẩn đo lường <span class="text-red-500">*</span></label>
            <input v-model="form.reference_standard_serial" class="form-input w-full" placeholder="VD: STD-2026-001" />
          </div>
          <div>
            <label class="form-label">Tham chiếu liên kết chuẩn <span class="text-red-500">*</span></label>
            <input v-model="form.traceability_reference" class="form-input w-full" placeholder="VD: NIST-12345" />
          </div>
        </div>
        <p class="text-xs text-emerald-700">
          Cần liên kết tới chuẩn đã được công nhận để đảm bảo liên kết chuẩn theo ISO 17025.
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
