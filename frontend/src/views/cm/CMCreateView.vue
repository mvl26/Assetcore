<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm09Store } from '@/stores/imm09'
import { useFormDraft } from '@/composables/useFormDraft'
import { useApi } from '@/composables/useApi'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'
import { getIncident } from '@/api/imm12'
import { searchSpareParts } from '@/api/imm09'
import { uploadDocumentFile } from '@/api/imm05'
import { getAssetActionMeta } from '@/api/imm00'
import { lifecycleStatusLabel, riskClassificationLabel, incidentSeverityLabel } from '@/constants/labels'
import SmartSelect from '@/components/common/SmartSelect.vue'

// Panel meta thiết bị — derive từ meta NẠC (getAssetActionMeta perm-aware, 6 field,
// KHÔNG full-doc tài chính). Hiển thị display-name (device_model_name /
// location_name), KHÔNG raw Link id.
interface AssetMeta {
  device_model_name?: string
  lifecycle_status?: string
  risk_classification?: string
  asset_name?: string
  location_name?: string
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
const notify = useNotify()
const submitting = ref(false)
const error = ref('')
const assetMeta = ref<AssetMeta | null>(null)
const incidentMeta = ref<{ severity?: string; description?: string } | null>(null)

const form = ref({
  asset_ref: (route.query.asset as string) || '',
  incident_report: (route.query.incident as string) || '',
  source_pm_wo: (route.query.pm_wo as string) || '',
  repair_type: 'Corrective',
  priority: 'Normal',
  failure_description: '',
  fault_image: '',
})

// Item 6: chọn thiết bị theo Asset trực tiếp hoặc theo Model
const selectMode = ref<'asset' | 'model'>('asset')
const selectedModel = ref('')
const uploadingImage = ref(false)
const uploadImageError = ref('')

function onModelChange() {
  // Đổi model → reset asset đã chọn (asset phụ thuộc model)
  form.value.asset_ref = ''
}

async function onFaultImageChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadingImage.value = true
  uploadImageError.value = ''
  try {
    const res = await uploadDocumentFile(file, {
      doctype: 'Asset Repair', fieldname: 'fault_image',
    })
    form.value.fault_image = res.file_url
  } catch (err: unknown) {
    uploadImageError.value = err instanceof Error ? err.message : 'Tải ảnh lên thất bại'
  } finally {
    uploadingImage.value = false
  }
}

const preRequestParts = ref<PartRow[]>([])
const partSearch = ref('')
const partResults = ref<Array<{ name: string; part_name: string; stock_qty?: number }>>([])

const { clear: clearDraft } = useFormDraft('cm-create', form)

// Luôn ưu tiên asset từ query khi điều hướng từ AssetDetail — tránh draft cũ
// che mất thiết bị user vừa chọn.
const _queryAsset = (route.query.asset as string) || ''
if (_queryAsset) form.value.asset_ref = _queryAsset
const _queryIncident = (route.query.incident as string) || ''
if (_queryIncident) form.value.incident_report = _queryIncident

// Deep-link từ màn quét QR (D3): query hằng = {asset, source}. Field nội bộ CM = asset_ref.
// Provenance: chỉ 'qr-scan' mới coi là quét QR; mọi giá trị khác (kể cả thiếu) → manual.
// Khoá ô Thiết bị KHI và CHỈ KHI đến từ quét QR + có asset prefill (no regression khi
// tạo thủ công / không source).
const querySource = route.query.source === 'qr-scan' ? 'qr-scan' : 'manual'
const lockedFromScan = computed(() => querySource === 'qr-scan' && !!_queryAsset)

// BR-09-01 đã được nới ở BE: Incident/PM giờ là tùy chọn (standalone repair).
// Không còn gating canSubmit theo nguồn.
const canSubmit = computed(() =>
  !!form.value.asset_ref
  && form.value.failure_description.trim().length >= 10
  && assetMeta.value?.lifecycle_status !== 'Decommissioned'
)

const slaHoursMap: Record<string, number> = {
  Emergency: 4, Urgent: 24, Normal: 72,
}
const slaTarget = computed(() => slaHoursMap[form.value.priority] ?? 24)

// AC4: isHighRisk derive từ ĐÚNG enum risk_classification ∈ {High, Critical}.
// risk_classification (Low/Medium/High/Critical — fetch_from device_model trên AC
// Asset) là field KHÁC với risk_class (A/B/C/D — letter class WHO/NĐ98 trên
// asset_commissioning/asset_repair). KHÔNG so 'C'/'D' — risk_classification KHÔNG
// BAO GIỜ giữ giá trị đó → so 'C'/'D' là logic câm (banner QA không bao giờ hiện).
const isHighRisk = computed(() => {
  const r = assetMeta.value?.risk_classification
  return r === 'High' || r === 'Critical'
})

// AC1/AC3: Nhãn VI an toàn cho ô "Mức rủi ro" qua SSoT riskClassificationLabel.
//   rỗng/whitespace/undefined → 'Chưa phân loại' (parity scan-info Vòng 38 —
//     KHÔNG '—' câm, 1 SSoT nhãn rỗng).
//   in-enum (Low/Medium/High/Critical) → VI (Thấp/Trung bình/Cao/Nghiêm trọng).
//   drift/legacy ngoài 4 enum → 'Khác' (KHÔNG leak EN/code thô).
const riskClassDisplay = computed(() => {
  const r = (assetMeta.value?.risk_classification ?? '').trim()
  return r ? riskClassificationLabel(r) : 'Chưa phân loại'
})

// ── Asset lookup ──
// Nạp meta qua getAssetActionMeta (api/imm00) — endpoint NẠC perm-aware (IDOR guard
// + DocPerm read ở BE), CHỈ 6 field meta → KHÔNG over-fetch giá mua/khấu hao/giá trị
// sổ sách qua đường QR scan-action. KHÔNG dùng frappe.client.get_value (LL-FE-40).
// Lỗi (403 vendor-IDOR / 404 / network) → assetMeta=null (fail-safe): panel ẩn,
// KHÔNG vỡ trang, KHÔNG leak raw exception/email/qr_token ra UI.
async function loadAssetMeta() {
  if (!form.value.asset_ref) {
    assetMeta.value = null
    return
  }
  try {
    const a = await getAssetActionMeta(form.value.asset_ref)
    assetMeta.value = {
      asset_name: a.asset_name,
      device_model_name: a.device_model_name,
      lifecycle_status: a.lifecycle_status,
      risk_classification: a.risk_classification,
      location_name: a.location_name,
    }
  } catch {
    assetMeta.value = null
  }
}

// SmartSelect emits asset name on explicit selection (không phải per keystroke) →
// gọi loadAssetMeta() trực tiếp, không cần debounce.
watch(() => form.value.asset_ref, () => { loadAssetMeta() })

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
    form.value.priority = sev === 'Critical' ? 'Emergency'
      : sev === 'High' ? 'Urgent'
        : 'Normal'
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
      // justified cast: BE search_spare_parts trả {name, part_name, stock_qty}
      // nhưng api/imm09.ts khai báo SparePartRow[] (mismatch sẵn có ở API layer,
      // ngoài scope của cleanup này — không sửa endpoint).
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
    // Thông báo chuẩn hoá (title + action_hint + severity) từ ApiError BE đã hydrate.
    notify.fromError(store.lastApiError)
    error.value = store.error ?? 'Không thể tạo phiếu sửa chữa'
    return
  }
  notify.show({ code: MSG.IMM09_CREATE_SUCCESS, ctx: { name, asset: form.value.asset_ref } })
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
      <button class="text-slate-400 hover:text-slate-600" @click="router.push('/cm/dashboard')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <h1 class="text-xl font-bold text-slate-900">Tạo Phiếu Sửa Chữa</h1>
    </div>

    <div class="bg-white rounded-xl shadow-sm border p-6 space-y-5">
      <!-- Source (tùy chọn — BR-09-01 đã nới) -->
      <div>
        <h2 class="font-semibold text-slate-700 mb-1">Nguồn sửa chữa <span class="text-xs text-slate-400 font-normal">(tùy chọn)</span></h2>
        <p class="text-xs text-slate-500 mb-3">Nếu có Sự cố/bảo trì định kỳ, điền để tự điền sẵn thiết bị, mức độ, mô tả. Có thể bỏ trống (sửa chữa độc lập).</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm text-slate-600 mb-1">Báo cáo sự cố</label>
            <input v-model="form.incident_report" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" placeholder="IR-2026-XXXXX" />
          </div>
          <div>
            <label class="block text-sm text-slate-600 mb-1">Phiếu bảo trì gốc</label>
            <input v-model="form.source_pm_wo" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" placeholder="PM-WO-2026-XXXXX" />
          </div>
        </div>
        <div v-if="incidentMeta" class="mt-2 alert-info text-xs">
          Đã đọc sự cố: mức độ <b>{{ incidentSeverityLabel(incidentMeta.severity ?? '') }}</b> — ưu tiên đặt tự động.
        </div>
      </div>

      <!-- Asset -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-semibold text-slate-700">
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
          </h2>
          <div v-if="!lockedFromScan" class="inline-flex rounded-lg border border-slate-200 overflow-hidden text-xs font-medium">
            <button
              type="button"
              :class="['px-3 py-1.5', selectMode === 'asset' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600']"
              @click="selectMode = 'asset'"
            >Chọn theo tài sản</button>
            <button
              type="button"
              :class="['px-3 py-1.5', selectMode === 'model' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600']"
              @click="selectMode = 'model'"
            >Chọn theo mẫu máy</button>
          </div>
        </div>

        <div v-if="!lockedFromScan && selectMode === 'model'" class="mb-3">
          <label class="block text-sm text-slate-600 mb-1">Mẫu thiết bị</label>
          <SmartSelect
            v-model="selectedModel"
            doctype="IMM Device Model"
            placeholder="Chọn mẫu máy..."
            @select="onModelChange"
            @clear="onModelChange"
          />
          <label v-if="selectedModel" class="block text-sm text-slate-600 mb-1 mt-3">Chọn thiết bị thuộc mẫu máy này</label>
          <SmartSelect
            v-if="selectedModel"
            v-model="form.asset_ref"
            doctype="AC Asset"
            :filters="{ device_model: selectedModel }"
            placeholder="Tìm thiết bị thuộc mẫu máy..."
          />
        </div>
        <SmartSelect v-else v-model="form.asset_ref" doctype="AC Asset" :disabled="lockedFromScan" placeholder="Tìm thiết bị theo tên / mã / serial..." />
        <p v-if="lockedFromScan" class="text-xs text-slate-500 mt-1">Thiết bị đã được xác định từ mã QR — không thể thay đổi.</p>
        <!-- Panel meta thiết bị (scan-action) — a11y dl/dt/dd parity panel Incident
             round 26. Render khi assetMeta (loader-lỗi→null→ẩn). KHÔNG đổi điều kiện
             hiển thị / loader getAssetActionMeta / shape assetMeta. -->
        <section
          v-if="assetMeta"
          data-test="scan-cm-meta"
          aria-labelledby="scan-cm-meta-heading"
          class="mt-2"
        >
          <h3 id="scan-cm-meta-heading" class="sr-only">Thông tin thiết bị</h3>
          <dl class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            <div data-test="scan-cm-meta-name" class="bg-slate-50 rounded px-2 py-1.5">
              <dt class="inline text-slate-500">Tên:</dt>
              <dd class="inline font-bold">{{ assetMeta.asset_name || 'Chưa có tên' }}</dd>
            </div>
            <div data-test="scan-cm-meta-model" class="bg-slate-50 rounded px-2 py-1.5">
              <dt class="inline text-slate-500">Mẫu máy:</dt>
              <dd class="inline">{{ assetMeta.device_model_name || 'Chưa gán' }}</dd>
            </div>
            <div data-test="scan-cm-meta-location" class="bg-slate-50 rounded px-2 py-1.5">
              <dt class="inline text-slate-500">Vị trí:</dt>
              <dd class="inline">{{ assetMeta.location_name || 'Chưa gán' }}</dd>
            </div>
            <div
              data-test="scan-cm-meta-status"
              :class="['rounded px-2 py-1.5', assetMeta.lifecycle_status === 'Decommissioned' ? 'bg-red-50 text-red-700' : 'bg-slate-50']"
            >
              <dt class="inline text-slate-500">Trạng thái:</dt>
              <dd class="inline font-bold">{{ assetMeta.lifecycle_status ? lifecycleStatusLabel(assetMeta.lifecycle_status) : 'Chưa xác định' }}</dd>
            </div>
            <div
              data-test="scan-cm-meta-risk"
              :class="['rounded px-2 py-1.5', isHighRisk ? 'bg-orange-50 text-orange-700' : 'bg-slate-50']"
            >
              <dt class="inline text-slate-500">Mức rủi ro:</dt>
              <dd class="inline font-bold">{{ riskClassDisplay }}</dd>
            </div>
          </dl>
        </section>
        <div v-if="assetMeta?.lifecycle_status === 'Decommissioned'" class="mt-2 alert-error text-sm">
          Thiết bị đã thanh lý — không thể tạo phiếu sửa chữa.
        </div>
        <div v-if="isHighRisk" class="mt-2 alert-warning text-sm">
          Mức rủi ro {{ riskClassDisplay }} — bắt buộc đảm bảo chất lượng phê duyệt khi đóng phiếu.
        </div>
      </div>

      <!-- Type & Priority & SLA -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label class="block text-sm text-slate-600 mb-1">Loại sửa chữa *</label>
          <select v-model="form.repair_type" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
            <option value="Corrective">Sửa chữa khắc phục</option>
            <option value="Breakdown">Hỏng đột xuất</option>
            <option value="Warranty Repair">Bảo hành</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-slate-600 mb-1">Ưu tiên *</label>
          <select v-model="form.priority" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
            <option value="Normal">Bình thường</option>
            <option value="Urgent">Khẩn</option>
            <option value="Emergency">Cấp cứu</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-slate-600 mb-1">Cam kết mức dịch vụ (giờ)</label>
          <div class="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-semibold">
            {{ slaTarget }}h
          </div>
        </div>
      </div>

      <div v-if="form.priority === 'Emergency'" class="alert-error text-sm">
        Phiếu mức <strong>Khẩn cấp</strong>. Trưởng xưởng sẽ được thông báo realtime, cam kết dịch vụ chỉ {{ slaTarget }} giờ.
      </div>

      <!-- Description -->
      <div>
        <label class="block text-sm text-slate-600 mb-1">Mô tả lỗi * <span class="text-xs text-slate-400">(tối thiểu 10 ký tự)</span></label>
        <textarea v-model="form.failure_description" rows="4" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" placeholder="Mô tả triệu chứng hỏng hóc, bộ phận bị ảnh hưởng..." />
      </div>

      <!-- Fault image -->
      <div>
        <label class="block text-sm text-slate-600 mb-1">Ảnh mô tả lỗi <span class="text-xs text-slate-400">(tùy chọn)</span></label>
        <input type="file" accept="image/*" :disabled="uploadingImage" class="block w-full text-sm" @change="onFaultImageChange" />
        <p v-if="uploadingImage" class="text-xs text-slate-500 mt-1">Đang tải ảnh lên...</p>
        <p v-if="uploadImageError" class="text-xs text-red-600 mt-1">{{ uploadImageError }}</p>
        <div v-if="form.fault_image" class="mt-2">
          <img :src="form.fault_image" alt="Ảnh lỗi" class="max-h-40 rounded-lg border border-slate-200" />
        </div>
      </div>

      <!-- Pre-request parts -->
      <div>
        <h2 class="font-semibold text-slate-700 mb-2">Phụ tùng dự kiến (tùy chọn)</h2>
        <div class="relative">
          <input v-model="partSearch" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" placeholder="Tìm phụ tùng theo tên/code..." />
          <ul v-if="partResults.length" class="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-56 overflow-y-auto">
            <li v-for="p in partResults" :key="p.name"
                class="px-3 py-2 text-sm hover:bg-blue-50 cursor-pointer flex justify-between"
                @click="addPart(p)">
              <span><b>{{ p.name }}</b> — {{ p.part_name }}</span>
              <span class="text-xs text-slate-500">Kho: {{ p.stock_qty ?? '—' }}</span>
            </li>
          </ul>
        </div>
        <ul v-if="preRequestParts.length" class="mt-2 space-y-1.5">
          <li v-for="(p, i) in preRequestParts" :key="p.spare_part"
              class="flex items-center gap-2 bg-slate-50 rounded px-2 py-1.5 text-sm">
            <span class="flex-1">{{ p.spare_part }}</span>
            <input v-model.number="p.qty" type="number" min="1" class="w-16 border border-slate-300 rounded px-2 py-1 text-sm" />
            <button class="text-red-500 hover:text-red-700" @click="removePart(i)">×</button>
          </li>
        </ul>
      </div>

      <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{{ error }}</div>

      <div class="flex justify-end gap-3 pt-2">
        <button class="px-5 py-2.5 border border-slate-300 rounded-lg text-sm hover:bg-slate-50" @click="router.push('/cm/dashboard')">Hủy</button>
        <button
          :disabled="!canSubmit || submitting"
          :class="[
            'px-5 py-2.5 rounded-lg text-sm font-medium transition-all',
            canSubmit && !submitting ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-slate-100 text-slate-400 cursor-not-allowed'
          ]"
          @click="handleSubmit"
        >
          {{ submitting ? 'Đang tạo...' : 'Tạo phiếu sửa chữa' }}
        </button>
      </div>
    </div>
  </div>
</template>
