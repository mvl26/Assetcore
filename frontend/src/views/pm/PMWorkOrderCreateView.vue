<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — Ad-hoc PM Work Order Create
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createAdhocPMWorkOrder } from '@/api/imm08'
import { frappeGet } from '@/api/helpers'
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
  technician_notes: '',
})

const { clear: clearDraft } = useFormDraft('pm-work-order-create', form)

const schedules = ref<ScheduleRow[]>([])
const selectedSchedule = computed(() =>
  schedules.value.find(s => s.name === form.value.pm_schedule),
)
const checklistPreview = ref<ChecklistItem[]>([])
const assetMeta = ref<AssetMeta | null>(null)
const loadingSchedules = ref(false)
const loadingChecklist = ref(false)
const saving = ref(false)
const error = ref('')

const canSubmit = computed(() =>
  !!form.value.asset_ref
  && !!form.value.pm_schedule
  && !!form.value.due_date
  && assetMeta.value?.lifecycle_status !== 'Decommissioned',
)

// ── Asset metadata
async function loadAssetMeta() {
  if (!form.value.asset_ref) {
    assetMeta.value = null
    schedules.value = []
    return
  }
  try {
    const r = await frappeGet<AssetMeta>('frappe.client.get_value', {
      doctype: 'AC Asset',
      filters: form.value.asset_ref,
      fieldname: JSON.stringify(['device_model', 'asset_name', 'lifecycle_status', 'location']),
    })
    assetMeta.value = r ?? null
  } catch { assetMeta.value = null }
  await loadSchedules()
}

async function loadSchedules() {
  if (!form.value.asset_ref) return
  loadingSchedules.value = true
  try {
    const res = await frappeGet<{ data: ScheduleRow[] }>(
      '/api/method/assetcore.api.imm08.list_pm_schedules',
      { filters: JSON.stringify({ asset_ref: form.value.asset_ref, status: 'Active' }), page_size: 50 },
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
      'frappe.client.get',
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
      <h1 class="text-xl font-semibold text-gray-800">Tạo phiếu bảo trì đột xuất</h1>
    </div>

    <div class="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
      Phiếu bảo trì thường tạo tự động theo lịch. Form này dành cho trường hợp ngoại lệ.
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">{{ error }}</div>

      <!-- Asset -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Thiết bị <span class="text-red-500">*</span>
        </label>
        <SmartSelect v-model="form.asset_ref" doctype="AC Asset" placeholder="Chọn thiết bị..." />
        <div v-if="assetMeta" class="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div class="bg-gray-50 rounded px-2 py-1.5"><span class="text-gray-500">Tên:</span> <b>{{ assetMeta.asset_name || '—' }}</b></div>
          <div class="bg-gray-50 rounded px-2 py-1.5"><span class="text-gray-500">Model:</span> {{ assetMeta.device_model || '—' }}</div>
          <div class="bg-gray-50 rounded px-2 py-1.5"><span class="text-gray-500">Vị trí:</span> {{ assetMeta.location || '—' }}</div>
          <div :class="['rounded px-2 py-1.5', assetMeta.lifecycle_status === 'Decommissioned' ? 'bg-red-50 text-red-700' : 'bg-gray-50']">
            <span class="text-gray-500">Trạng thái:</span> <b>{{ assetMeta.lifecycle_status || '—' }}</b>
          </div>
        </div>
        <div v-if="assetMeta?.lifecycle_status === 'Decommissioned'" class="mt-2 bg-red-50 border border-red-200 rounded-lg p-2 text-sm text-red-700">
          ⛔ Thiết bị đã thanh lý — không thể tạo phiếu PM.
        </div>
      </div>

      <!-- PM Schedule -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          PM Schedule <span class="text-red-500">*</span>
        </label>
        <select
          v-model="form.pm_schedule"
          :disabled="!form.asset_ref || loadingSchedules"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50 disabled:text-gray-400"
        >
          <option value="">{{ loadingSchedules ? 'Đang tải...' : '-- Chọn lịch PM --' }}</option>
          <option v-for="s in schedules" :key="s.name" :value="s.name">
            {{ s.pm_type }} — mỗi {{ s.pm_interval_days ?? '?' }} ngày ({{ s.name }})
          </option>
        </select>
        <p v-if="form.asset_ref && !loadingSchedules && !schedules.length" class="text-xs text-orange-600 mt-1">
          Thiết bị này chưa có PM Schedule Active. Tạo lịch trước tại mục PM Schedule.
        </p>
        <div v-if="selectedSchedule" class="mt-2 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800 grid grid-cols-2 gap-2">
          <div><span class="text-blue-600">Loại:</span> <b>{{ selectedSchedule.pm_type }}</b></div>
          <div><span class="text-blue-600">Chu kỳ:</span> <b>{{ selectedSchedule.pm_interval_days }} ngày</b></div>
          <div><span class="text-blue-600">Ước lượng:</span> <b>{{ selectedSchedule.estimated_minutes ?? '—' }} phút</b></div>
          <div><span class="text-blue-600">Lần tới:</span> <b>{{ selectedSchedule.next_due_date || '—' }}</b></div>
        </div>
      </div>

      <!-- Checklist preview -->
      <div v-if="form.pm_schedule">
        <label class="block text-sm font-medium text-gray-700 mb-1">Checklist (xem trước)</label>
        <div v-if="loadingChecklist" class="text-xs text-gray-500">Đang tải checklist...</div>
        <div v-else-if="!checklistPreview.length" class="text-xs text-gray-400 italic">
          PM Schedule này không gắn template checklist (KTV sẽ ghi nhận tự do trên phiếu).
        </div>
        <ul v-else class="border border-gray-200 rounded-lg divide-y text-sm max-h-56 overflow-y-auto">
          <li v-for="(it, i) in checklistPreview" :key="i" class="px-3 py-2 flex justify-between items-center">
            <div>
              <span class="font-medium">{{ it.parameter }}</span>
              <span class="text-gray-400 ml-2">→ {{ it.expected }}</span>
            </div>
            <span v-if="it.is_critical" class="text-xs bg-red-100 text-red-700 rounded px-2 py-0.5">CRITICAL</span>
          </li>
        </ul>
        <p v-if="checklistPreview.length" class="text-xs text-gray-500 mt-1">{{ checklistPreview.length }} mục — KTV sẽ điền kết quả khi In Progress.</p>
      </div>

      <!-- Due Date -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Ngày thực hiện <span class="text-red-500">*</span>
        </label>
        <DateInput v-model="form.due_date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
      </div>

      <!-- Assigned To -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Giao cho KTV (email)</label>
        <input
          v-model="form.assigned_to"
          type="email"
          placeholder="ktv@hospital.vn"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <!-- Notes -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
        <textarea
          v-model="form.technician_notes"
          rows="2"
          placeholder="Lý do tạo WO ngoài lịch..."
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
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
