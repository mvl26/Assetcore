<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — Ad-hoc PM Work Order Create
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createAdhocPMWorkOrder } from '@/api/imm08'
import { checkAssetComplianceStatus, type ComplianceGateResult } from '@/api/imm16'
import { frappeGet } from '@/api/helpers'
import { translateStatus } from '@/utils/formatters'
import SmartSelect from '@/components/common/SmartSelect.vue'
import DateInput from '@/components/common/DateInput.vue'
import { useFormDraft } from '@/composables/useFormDraft'
import { useApi } from '@/composables/useApi'

interface ScheduleRow {
  name: string
  pm_type: string
  pm_interval_days?: number
  next_due_date?: string
  template_ref?: string
  estimated_minutes?: number
}

interface ChecklistItem {
  parameter: string
  expected: string
  is_critical?: number
}

interface AssetMeta {
  device_model?: string
  asset_name?: string
  lifecycle_status?: string
  location?: string
}

const router = useRouter()
const api = useApi()

const form = ref({
  asset_ref: '',
  pm_schedule: '',
  due_date: '',
  assigned_to: '',
  supervisor: '',
  technician_notes: '',
})

const { clear: clearDraft } = useFormDraft('pm-work-order-create', form)

const schedules = ref<ScheduleRow[]>([])
const selectedSchedule = computed(() =>
  schedules.value.find(s => s.name === form.value.pm_schedule),
)
const checklistPreview = ref<ChecklistItem[]>([])
const assetMeta = ref<AssetMeta | null>(null)
// Pre-flight compliance gate (BR-16-09). Reads the SAME SoT as gate_wo_submit
// via api/imm16.checkAssetComplianceStatus — FE only RENDERS result.blocked +
// reasons[] verbatim, never inline-computes 'Critical CAPA open' membership.
const complianceGate = ref<ComplianceGateResult | null>(null)
const loadingSchedules = ref(false)
const loadingChecklist = ref(false)
const saving = ref(false)
const error = ref('')

const canSubmit = computed(() =>
  !!form.value.asset_ref
  && !!form.value.pm_schedule
  && !!form.value.due_date
  && assetMeta.value?.lifecycle_status !== 'Decommissioned'
  && complianceGate.value?.blocked !== true,
)

// ── Asset metadata + pre-flight compliance gate
async function loadAssetMeta() {
  if (!form.value.asset_ref) {
    assetMeta.value = null
    complianceGate.value = null
    schedules.value = []
    return
  }
  // allSettled: a 403/error on the gate must NOT blank the asset panel — both
  // requests are independent and fail-safe (gate → null, banner stays hidden).
  const [metaRes, gateRes] = await Promise.allSettled([
    frappeGet<AssetMeta>('/api/method/frappe.client.get_value', {
      doctype: 'AC Asset',
      filters: form.value.asset_ref,
      fieldname: JSON.stringify(['device_model', 'asset_name', 'lifecycle_status', 'location']),
    }),
    checkAssetComplianceStatus(form.value.asset_ref),
  ])
  assetMeta.value = metaRes.status === 'fulfilled' ? (metaRes.value ?? null) : null
  complianceGate.value = gateRes.status === 'fulfilled' ? (gateRes.value ?? null) : null
  await loadSchedules()
}

async function loadSchedules() {
  if (!form.value.asset_ref) return
  loadingSchedules.value = true
  try {
    const res = await frappeGet<{ data: ScheduleRow[] }>(
      '/api/method/assetcore.api.imm08.list_pm_schedules',
      { asset_ref: form.value.asset_ref, status: 'Active', page_size: 50 },
    )
    schedules.value = res?.data ?? []
  } catch { schedules.value = [] }
  finally { loadingSchedules.value = false }
}

// ── Checklist preview when schedule selected
watch(() => form.value.pm_schedule, async (sched) => {
  checklistPreview.value = []
  if (!sched) return
  const tmpl = selectedSchedule.value?.template_ref
  if (!tmpl) return
  loadingChecklist.value = true
  try {
    const r = await frappeGet<{ checklist?: ChecklistItem[] }>(
      '/api/method/frappe.client.get',
      { doctype: 'PM Template', name: tmpl },
    )
    const tplDoc = (r as { checklist?: ChecklistItem[] } | null)
    checklistPreview.value = tplDoc?.checklist ?? []
    // Pre-fill due_date from schedule next_due_date if blank
    if (selectedSchedule.value?.next_due_date && !form.value.due_date) {
      form.value.due_date = selectedSchedule.value.next_due_date
    }
  } catch { checklistPreview.value = [] }
  finally { loadingChecklist.value = false }
})

async function submit() {
  if (!canSubmit.value) {
    error.value = 'Vui lòng điền đầy đủ thông tin bắt buộc.'
    return
  }
  saving.value = true; error.value = ''
  const res = await api.run(
    () => createAdhocPMWorkOrder(form.value),
    {
      successMessage: 'Đã tạo phiếu bảo trì',
      onFieldError: (fields) => { error.value = Object.values(fields).join('; ') },
    },
  )
  saving.value = false
  if (res?.name) {
    clearDraft()
    router.push(`/pm/work-orders/${res.name}`)
  }
}

// SmartSelect emits full asset name on selection — no debounce needed since SmartSelect only
// emits on explicit selection, not per keystroke. Direct watch is safe here.
watch(() => form.value.asset_ref, loadAssetMeta)

onMounted(() => {
  if (!form.value.due_date) {
    form.value.due_date = new Date().toISOString().split('T')[0]
  }
})
</script>

<template>
  <div class="page-container animate-fade-in space-y-6">
    <div class="flex items-center gap-3">
      <button class="text-slate-500 hover:text-slate-700 text-sm" @click="router.push('/pm/work-orders')">
        ← Danh sách phiếu bảo trì
      </button>
      <h1 class="text-xl font-semibold text-slate-800">Tạo phiếu bảo trì đột xuất</h1>
    </div>

    <div class="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
      Phiếu bảo trì thường tạo tự động theo lịch. Form này dành cho trường hợp ngoại lệ.
    </div>

    <div class="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
      <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">{{ error }}</div>

      <!-- Asset -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">
          Thiết bị <span class="text-red-500">*</span>
        </label>
        <SmartSelect v-model="form.asset_ref" doctype="AC Asset" placeholder="Chọn thiết bị..." />
        <div v-if="assetMeta" class="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div class="bg-slate-50 rounded px-2 py-1.5"><span class="text-slate-500">Tên:</span> <b>{{ assetMeta.asset_name || '—' }}</b></div>
          <div class="bg-slate-50 rounded px-2 py-1.5"><span class="text-slate-500">Model:</span> {{ assetMeta.device_model || '—' }}</div>
          <div class="bg-slate-50 rounded px-2 py-1.5"><span class="text-slate-500">Vị trí:</span> {{ assetMeta.location || '—' }}</div>
          <div :class="['rounded px-2 py-1.5', assetMeta.lifecycle_status === 'Decommissioned' ? 'bg-red-50 text-red-700' : 'bg-slate-50']">
            <span class="text-slate-500">Trạng thái:</span> <b>{{ assetMeta.lifecycle_status || '—' }}</b>
          </div>
        </div>
        <div v-if="assetMeta?.lifecycle_status === 'Decommissioned'" class="mt-2 alert-error text-sm">
          Thiết bị đã thanh lý — không thể tạo phiếu PM.
        </div>

        <!-- Pre-flight compliance gate banner (BR-16-09) — cảnh báo SỚM trước
             khi submit. Render verbatim BE gate result; status dịch qua SSoT. -->
        <div
          v-if="complianceGate?.blocked"
          role="alert"
          aria-live="assertive"
          class="mt-3 alert-warning text-sm"
        >
          <p class="font-semibold">
            Thiết bị đang bị chặn tạo lệnh do CAPA tuân thủ chưa đóng
          </p>
          <ul class="mt-1.5 list-disc list-inside space-y-0.5">
            <li v-for="r in complianceGate.reasons" :key="r.ref">
              {{ r.ref }} — {{ translateStatus(r.status) }}
            </li>
          </ul>
          <p class="mt-1.5 text-xs">
            Hãy đóng các CAPA nghiêm trọng nêu trên trước khi tạo phiếu bảo trì.
          </p>
        </div>
      </div>

      <!-- PM Schedule -->
      <div>
        <label class="form-label">
          Lịch bảo trì <span class="text-red-500">*</span>
        </label>
        <select
          v-model="form.pm_schedule"
          :disabled="!form.asset_ref || loadingSchedules"
          class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-slate-50 disabled:text-slate-400"
        >
          <option value="">{{ loadingSchedules ? 'Đang tải...' : '-- Chọn lịch PM --' }}</option>
          <option v-for="s in schedules" :key="s.name" :value="s.name">
            {{ s.pm_type }} — mỗi {{ s.pm_interval_days ?? '?' }} ngày ({{ s.name }})
          </option>
        </select>
        <p v-if="form.asset_ref && !loadingSchedules && !schedules.length" class="text-xs text-orange-600 mt-1">
          Thiết bị này chưa có PM Schedule Active. Tạo lịch trước tại mục PM Schedule.
        </p>
        <div v-if="selectedSchedule" class="mt-2 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800 grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div><span class="text-blue-600">Loại:</span> <b>{{ selectedSchedule.pm_type }}</b></div>
          <div><span class="text-blue-600">Chu kỳ:</span> <b>{{ selectedSchedule.pm_interval_days }} ngày</b></div>
          <div><span class="text-blue-600">Ước lượng:</span> <b>{{ selectedSchedule.estimated_minutes ?? '—' }} phút</b></div>
          <div><span class="text-blue-600">Lần tới:</span> <b>{{ selectedSchedule.next_due_date || '—' }}</b></div>
        </div>
      </div>

      <!-- Checklist preview -->
      <div v-if="form.pm_schedule">
        <label class="block text-sm font-medium text-slate-700 mb-1">Checklist (xem trước)</label>
        <div v-if="loadingChecklist" class="text-xs text-slate-500">Đang tải checklist...</div>
        <div v-else-if="!checklistPreview.length" class="text-xs text-slate-400 italic">
          PM Schedule này không gắn template checklist (kỹ thuật viên sẽ ghi nhận tự do trên phiếu).
        </div>
        <ul v-else class="border border-slate-200 rounded-lg divide-y text-sm max-h-56 overflow-y-auto">
          <li v-for="(it, i) in checklistPreview" :key="i" class="px-3 py-2 flex justify-between items-center">
            <div>
              <span class="font-medium">{{ it.parameter }}</span>
              <span class="text-slate-400 ml-2">→ {{ it.expected }}</span>
            </div>
            <span v-if="it.is_critical" class="text-xs bg-red-100 text-red-700 rounded px-2 py-0.5">CRITICAL</span>
          </li>
        </ul>
        <p v-if="checklistPreview.length" class="text-xs text-slate-500 mt-1">{{ checklistPreview.length }} mục — kỹ thuật viên sẽ điền kết quả khi In Progress.</p>
      </div>

      <!-- Due Date -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">
          Ngày thực hiện <span class="text-red-500">*</span>
        </label>
        <DateInput v-model="form.due_date" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
      </div>

      <!-- Assigned To -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">Giao cho kỹ thuật viên (email)</label>
        <input
          v-model="form.assigned_to"
          type="email"
          placeholder="ktv@hospital.vn"
          class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <!-- Supervisor -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">Người giám sát</label>
        <SmartSelect v-model="form.supervisor" doctype="User" placeholder="Chọn người giám sát..." />
      </div>

      <!-- Notes -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">Ghi chú</label>
        <textarea
          v-model="form.technician_notes"
          rows="2"
          placeholder="Lý do tạo WO ngoài lịch..."
          class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <button
        :disabled="!canSubmit || saving"
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white py-2.5 rounded-lg text-sm font-medium transition-colors"
        @click="submit"
      >
        {{ saving ? 'Đang tạo...' : 'Tạo phiếu bảo trì' }}
      </button>
    </div>
  </div>
</template>
