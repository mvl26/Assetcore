<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm09Store } from '@/stores/imm09'
import { useFormDraft } from '@/composables/useFormDraft'
import { useApi } from '@/composables/useApi'
import { getIncident } from '@/api/imm12'
import { searchSpareParts } from '@/api/imm09'
import { frappeGet } from '@/api/helpers'

interface AssetMeta {
  device_model?: string
  lifecycle_status?: string
  risk_class?: string
  asset_name?: string
  location?: string
}

interface PartRow {
  spare_part: string
  qty: number
  remarks?: string
}

const router = useRouter()
const route = useRoute()
const store = useImm09Store()
const api = useApi()
const submitting = ref(false)
const error = ref('')
const assetMeta = ref<AssetMeta | null>(null)
const incidentMeta = ref<{ severity?: string; description?: string } | null>(null)

const form = ref({
  asset_ref: (route.query.asset as string) || '',
  incident_report: (route.query.incident as string) || '',
  source_pm_wo: (route.query.pm_wo as string) || '',
  repair_type: 'Corrective',
  priority: 'Medium',
  failure_description: '',
})

const preRequestParts = ref<PartRow[]>([])
const partSearch = ref('')
const partResults = ref<Array<{ name: string; part_name: string; stock_qty?: number }>>([])

const { clear: clearDraft } = useFormDraft('cm-create', form)

const sourceError = computed(() =>
  !form.value.incident_report && !form.value.source_pm_wo
    ? 'Phải có nguồn sửa chữa: Báo cáo sự cố hoặc Phiếu bảo trì gốc'
    : ''
)

const canSubmit = computed(() =>
  form.value.asset_ref
  && !sourceError.value
  && form.value.failure_description.trim().length >= 10
  && assetMeta.value?.lifecycle_status !== 'Decommissioned'
)

const slaHoursMap: Record<string, number> = {
  Critical: 4, High: 8, Medium: 24, Low: 72,
}
const slaTarget = computed(() => slaHoursMap[form.value.priority] ?? 24)

const isHighRisk = computed(() => {
  const r = assetMeta.value?.risk_class
  return r === 'C' || r === 'D'
})

// ── Asset lookup ──
async function loadAssetMeta() {
  if (!form.value.asset_ref) {
    assetMeta.value = null
    return
  }
  try {
    const r = await frappeGet<AssetMeta>('frappe.client.get_value', {
      doctype: 'AC Asset',
      filters: form.value.asset_ref,
      fieldname: JSON.stringify([
        'device_model', 'lifecycle_status', 'risk_class', 'asset_name', 'location',
      ]),
    })
    assetMeta.value = r ?? null
  } catch {
    assetMeta.value = null
  }
}

watch(() => form.value.asset_ref, loadAssetMeta)

// ── Incident pre-fill ──
async function loadIncidentMeta() {
  if (!form.value.incident_report) {
    incidentMeta.value = null
    return
  }
  const inc = await api.run(
    () => getIncident(form.value.incident_report),
    { silentError: true, silentSuccess: true },
  )
  if (!inc) return
  const data = (inc as { data?: Record<string, unknown> })?.data ?? inc
  const sev = (data as { severity?: string })?.severity
  const desc = (data as { description?: string })?.description
  const asset = (data as { asset?: string })?.asset
  incidentMeta.value = { severity: sev, description: desc }
  // Auto-fill asset
  if (asset && !form.value.asset_ref) form.value.asset_ref = asset
  // Auto-map severity → priority
  if (sev) {
    form.value.priority = sev === 'Critical' ? 'Critical'
      : sev === 'High' ? 'High'
        : sev === 'Medium' ? 'Medium' : 'Low'
  }
  // Pre-fill description if empty
  if (desc && !form.value.failure_description) {
    form.value.failure_description = `[Từ Incident ${form.value.incident_report}]\n${desc.slice(0, 500)}`
  }
}

watch(() => form.value.incident_report, loadIncidentMeta)

// ── Spare parts search ──
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(partSearch, (q) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!q || q.length < 2) {
    partResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    try {
      const rows = await searchSpareParts(q) as unknown as Array<{ name: string; part_name: string; stock_qty?: number }>
      partResults.value = rows
    } catch { partResults.value = [] }
  }, 300)
})

function addPart(p: { name: string; part_name: string }) {
  if (preRequestParts.value.some(x => x.spare_part === p.name)) return
  preRequestParts.value.push({ spare_part: p.name, qty: 1 })
  partSearch.value = ''
  partResults.value = []
}

function removePart(idx: number) {
  preRequestParts.value.splice(idx, 1)
}

// ── Submit ──
async function handleSubmit() {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = ''
  const name = await store.doCreateRepairWorkOrder({
    ...form.value,
    sla_target_hours: slaTarget.value,
  } as Parameters<typeof store.doCreateRepairWorkOrder>[0])
  submitting.value = false
  if (!name) {
    error.value = store.error ?? 'Không thể tạo phiếu sửa chữa'
    return
  }
  // Pre-request parts (if any) — best-effort
  if (preRequestParts.value.length) {
    const { requestSpareParts } = await import('@/api/imm09')
    try {
      await requestSpareParts(name, preRequestParts.value as unknown as Parameters<typeof requestSpareParts>[1])
    } catch (e) {
      console.warn('Pre-request parts failed', e)
    }
  }
  clearDraft()
  router.push(`/cm/work-orders/${name}`)
}

onMounted(() => {
  if (form.value.incident_report) loadIncidentMeta()
  if (form.value.asset_ref) loadAssetMeta()
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <div class="flex items-center gap-3 mb-6">
      <button class="text-gray-400 hover:text-gray-600" @click="router.push('/cm/dashboard')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <h1 class="text-xl font-bold text-gray-900">Tạo Phiếu Sửa Chữa</h1>
    </div>

    <div class="bg-white rounded-xl shadow-sm border p-6 space-y-5">
      <!-- Source -->
      <div>
        <h2 class="font-semibold text-gray-700 mb-1">Nguồn sửa chữa <span class="text-red-500">*</span></h2>
        <p class="text-xs text-gray-500 mb-3">Điền ít nhất một nguồn — sẽ tự pre-fill asset, severity, mô tả</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm text-gray-600 mb-1">Báo cáo sự cố</label>
            <input v-model="form.incident_report" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="IR-2026-XXXXX" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Phiếu bảo trì gốc</label>
            <input v-model="form.source_pm_wo" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="PM-WO-2026-XXXXX" />
          </div>
        </div>
        <div v-if="incidentMeta" class="mt-2 bg-blue-50 border border-blue-200 rounded-lg p-2 text-xs text-blue-800">
          ✓ Đã đọc Incident: severity <b>{{ incidentMeta.severity }}</b> → priority đặt tự động.
        </div>
        <p v-if="sourceError && (form.incident_report || form.source_pm_wo || form.asset_ref)" class="text-xs text-red-600 mt-1">
          {{ sourceError }}
        </p>
      </div>

      <!-- Asset -->
      <div>
        <h2 class="font-semibold text-gray-700 mb-3">Thiết bị</h2>
        <input v-model="form.asset_ref" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="ACC-ASS-2026-XXXXX *" />
        <div v-if="assetMeta" class="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div class="bg-gray-50 rounded px-2 py-1.5"><span class="text-gray-500">Tên:</span> <b>{{ assetMeta.asset_name || '—' }}</b></div>
          <div class="bg-gray-50 rounded px-2 py-1.5"><span class="text-gray-500">Model:</span> {{ assetMeta.device_model || '—' }}</div>
          <div :class="['rounded px-2 py-1.5', assetMeta.lifecycle_status === 'Decommissioned' ? 'bg-red-50 text-red-700' : 'bg-gray-50']">
            <span class="text-gray-500">Trạng thái:</span> <b>{{ assetMeta.lifecycle_status || '—' }}</b>
          </div>
          <div :class="['rounded px-2 py-1.5', isHighRisk ? 'bg-orange-50 text-orange-700' : 'bg-gray-50']">
            <span class="text-gray-500">Risk class:</span> <b>{{ assetMeta.risk_class || '—' }}</b>
          </div>
        </div>
        <div v-if="assetMeta?.lifecycle_status === 'Decommissioned'" class="mt-2 bg-red-50 border border-red-200 rounded-lg p-2 text-sm text-red-700">
          ⛔ Thiết bị đã thanh lý — không thể tạo phiếu sửa chữa.
        </div>
        <div v-if="isHighRisk" class="mt-2 bg-orange-50 border border-orange-200 rounded-lg p-2 text-sm text-orange-700">
          ⚠ Risk class {{ assetMeta?.risk_class }} — bắt buộc QA approval khi đóng phiếu.
        </div>
      </div>

      <!-- Type & Priority & SLA -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label class="block text-sm text-gray-600 mb-1">Loại sửa chữa *</label>
          <select v-model="form.repair_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="Corrective">Sửa chữa khắc phục</option>
            <option value="Emergency">Cấp cứu</option>
            <option value="Warranty Repair">Bảo hành</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Ưu tiên *</label>
          <select v-model="form.priority" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Critical">Critical</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">SLA (giờ)</label>
          <div class="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm font-semibold">
            {{ slaTarget }}h
          </div>
        </div>
      </div>

      <div v-if="form.priority === 'Critical'" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
        ⚠ Phiếu <strong>CRITICAL</strong>. IMM Workshop Lead sẽ được thông báo realtime, SLA chỉ {{ slaTarget }}h.
      </div>

      <!-- Description -->
      <div>
        <label class="block text-sm text-gray-600 mb-1">Mô tả sự cố * <span class="text-xs text-gray-400">(tối thiểu 10 ký tự)</span></label>
        <textarea v-model="form.failure_description" rows="4" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Mô tả triệu chứng hỏng hóc, bộ phận bị ảnh hưởng..." />
      </div>

      <!-- Pre-request parts -->
      <div>
        <h2 class="font-semibold text-gray-700 mb-2">Phụ tùng dự kiến (tùy chọn)</h2>
        <div class="relative">
          <input v-model="partSearch" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Tìm phụ tùng theo tên/code..." />
          <ul v-if="partResults.length" class="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-y-auto">
            <li v-for="p in partResults" :key="p.name"
                class="px-3 py-2 text-sm hover:bg-blue-50 cursor-pointer flex justify-between"
                @click="addPart(p)">
              <span><b>{{ p.name }}</b> — {{ p.part_name }}</span>
              <span class="text-xs text-gray-500">Kho: {{ p.stock_qty ?? '—' }}</span>
            </li>
          </ul>
        </div>
        <ul v-if="preRequestParts.length" class="mt-2 space-y-1.5">
          <li v-for="(p, i) in preRequestParts" :key="p.spare_part"
              class="flex items-center gap-2 bg-gray-50 rounded px-2 py-1.5 text-sm">
            <span class="flex-1">{{ p.spare_part }}</span>
            <input v-model.number="p.qty" type="number" min="1" class="w-16 border border-gray-300 rounded px-2 py-1 text-sm" />
            <button class="text-red-500 hover:text-red-700" @click="removePart(i)">×</button>
          </li>
        </ul>
      </div>

      <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{{ error }}</div>

      <div class="flex justify-end gap-3 pt-2">
        <button class="px-5 py-2.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50" @click="router.push('/cm/dashboard')">Hủy</button>
        <button
          :disabled="!canSubmit || submitting"
          :class="[
            'px-5 py-2.5 rounded-lg text-sm font-medium transition-all',
            canSubmit && !submitting ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
          @click="handleSubmit"
        >
          {{ submitting ? 'Đang tạo...' : 'Tạo phiếu sửa chữa' }}
        </button>
      </div>
    </div>
  </div>
</template>
