<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — Ad-hoc PM Work Order Create
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { createAdhocPMWorkOrder } from '@/api/imm08'
import { checkAssetComplianceStatus, type ComplianceGateResult } from '@/api/imm16'
import { getAssetActionMeta } from '@/api/imm00'
// frappeGet vẫn cần cho loadSchedules (imm08.list_pm_schedules) + watch checklist
// (frappe.client.get PM Template) → GIỮ import; CHỈ asset-meta migrate sang getAssetActionMeta.
import { frappeGet } from '@/api/helpers'
import { translateStatus } from '@/utils/formatters'
import { pmTypeLabel } from '@/constants/labels'
import SmartSelect from '@/components/common/SmartSelect.vue'
import DateInput from '@/components/common/DateInput.vue'
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import { useFormDraft } from '@/composables/useFormDraft'
import { useApi } from '@/composables/useApi'
import { useCapabilities } from '@/composables/useCapabilities'

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

// Panel meta thiết bị — derive từ meta NẠC (getAssetActionMeta perm-aware, 6 field,
// KHÔNG full-doc tài chính). Hiển thị display-name (device_model_name /
// location_name), KHÔNG raw Link id (DM-.../LOC-...).
interface AssetMeta {
  device_model_name?: string
  asset_name?: string
  lifecycle_status?: string
  location_name?: string
}

const router = useRouter()
const route = useRoute()
const api = useApi()
const { can } = useCapabilities()

// Deep-link từ màn quét QR (D3): query hằng = {asset, source}. Field nội bộ PM = asset_ref.
// Provenance: chỉ 'qr-scan' mới coi là quét QR; mọi giá trị khác (kể cả thiếu) → manual.
const querySource = route.query.source === 'qr-scan' ? 'qr-scan' : 'manual'
const queryAsset = (route.query.asset as string) || ''

const form = ref({
  asset_ref: queryAsset,
  pm_schedule: '',
  due_date: '',
  assigned_to: '',
  supervisor: '',
  technician_notes: '',
})

// Khoá ô Thiết bị KHI và CHỈ KHI đến từ quét QR + có asset prefill. Tạo thủ công
// (manual / không source) → editable như cũ (no regression).
const lockedFromScan = computed(() => querySource === 'qr-scan' && !!queryAsset)

const { clear: clearDraft } = useFormDraft('pm-work-order-create', form)

// Ưu tiên asset từ query khi deep-link từ màn quét QR — tránh draft cũ trong
// localStorage che mất thiết bị vừa xác định.
if (queryAsset) form.value.asset_ref = queryAsset

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

// Nhãn thiết bị hiển thị trong empty-state — ưu tiên tên đọc được, fallback mã đã
// khoá từ QR để KTV biết đang nói về thiết bị nào (KHÔNG để rỗng).
const assetDisplay = computed(
  () => assetMeta.value?.asset_name || form.value.asset_ref || '',
)

// Empty-state CHỈ hiện khi đã chọn/khoá asset VÀ load xong VÀ thực sự 0 schedule.
// Không flash khi đang tải (loadingSchedules=true → hiện trạng thái tải).
const showScheduleEmpty = computed(
  () =>
    !!form.value.asset_ref
    && !loadingSchedules.value
    && schedules.value.length === 0,
)

// CTA tạo lịch PM chỉ render khi có quyền pm.write (capability, KHÔNG hardcode role).
const canCreateSchedule = computed(() => can('pm.write'))

function goCreateSchedule() {
  router.push('/pm/schedules')
}

// ── Asset metadata + pre-flight compliance gate
async function loadAssetMeta() {
  if (!form.value.asset_ref) {
    assetMeta.value = null
    complianceGate.value = null
    schedules.value = []
    return
  }
  // allSettled: meta + compliance gate độc lập, fail-safe. Nạp meta qua
  // getAssetActionMeta (api/imm00) — endpoint NẠC perm-aware (IDOR guard + DocPerm
  // read ở BE), CHỈ 6 field meta → KHÔNG over-fetch giá mua/khấu hao/giá trị sổ sách
  // qua đường QR scan-action. KHÔNG dùng frappe.client.get_value (LL-FE-40) → hết RÒ
  // mã thô Model/Vị trí + hết filters dị dạng kiểu BUG-META-1 (417-risk).
  // Lỗi meta (403 vendor-IDOR / 404 / network) → assetMeta=null: panel ẩn, KHÔNG
  // vỡ trang, KHÔNG leak raw exception/email/qr_token. Gate lỗi → banner ẩn (độc lập).
  const [metaRes, gateRes] = await Promise.allSettled([
    getAssetActionMeta(form.value.asset_ref),
    checkAssetComplianceStatus(form.value.asset_ref),
  ])
  if (metaRes.status === 'fulfilled' && metaRes.value) {
    const a = metaRes.value
    assetMeta.value = {
      asset_name: a.asset_name,
      device_model_name: a.device_model_name,
      lifecycle_status: a.lifecycle_status,
      location_name: a.location_name,
    }
  } else {
    assetMeta.value = null
  }
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
  // Prefill từ deep-link QR: nạp panel meta + schedules + compliance gate ngay.
  if (form.value.asset_ref) loadAssetMeta()
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
        <SmartSelect v-model="form.asset_ref" doctype="AC Asset" :disabled="lockedFromScan" placeholder="Chọn thiết bị..." />
        <p v-if="lockedFromScan" class="text-xs text-slate-500 mt-1">Thiết bị đã được xác định từ mã QR — không thể thay đổi.</p>
        <div v-if="assetMeta" class="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div class="bg-slate-50 rounded px-2 py-1.5"><span class="text-slate-500">Tên:</span> <b>{{ assetMeta.asset_name || 'Chưa có tên' }}</b></div>
          <div class="bg-slate-50 rounded px-2 py-1.5"><span class="text-slate-500">Mẫu máy:</span> {{ assetMeta.device_model_name || 'Chưa gán' }}</div>
          <div class="bg-slate-50 rounded px-2 py-1.5"><span class="text-slate-500">Vị trí:</span> {{ assetMeta.location_name || 'Chưa gán' }}</div>
          <div :class="['rounded px-2 py-1.5', assetMeta.lifecycle_status === 'Decommissioned' ? 'bg-red-50 text-red-700' : 'bg-slate-50']">
            <span class="text-slate-500">Trạng thái:</span> <b>{{ assetMeta.lifecycle_status ? translateStatus(assetMeta.lifecycle_status) : 'Chưa xác định' }}</b>
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
            {{ pmTypeLabel(s.pm_type) }} — mỗi {{ s.pm_interval_days ?? '?' }} ngày ({{ s.name }})
          </option>
        </select>
        <!-- Empty-state có cấu trúc (BUG-PM-2): thiết bị chưa có lịch PM Active.
             Hiện khi đã khoá/chọn asset + load xong + 0 schedule (KHÔNG flash lúc tải).
             Nêu rõ TÊN thiết bị + lối thoát điều hướng (gate pm.write). -->
        <div
          v-if="showScheduleEmpty"
          data-test="pm-schedule-empty"
          role="status"
          aria-live="polite"
          class="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
        >
          <p class="font-semibold">
            <template v-if="lockedFromScan">
              Thiết bị <b>{{ assetDisplay }}</b> (quét từ mã QR) chưa có lịch bảo trì
              định kỳ đang hoạt động.
            </template>
            <template v-else>
              Thiết bị <b>{{ assetDisplay }}</b> chưa có lịch bảo trì định kỳ đang
              hoạt động.
            </template>
          </p>
          <p class="mt-1 text-xs text-amber-700">
            Cần có ít nhất một lịch bảo trì để tạo phiếu cho thiết bị này.
          </p>
          <button
            v-if="canCreateSchedule"
            data-test="pm-schedule-create-cta"
            type="button"
            class="mt-2.5 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-700 transition-colors min-h-[40px]"
            @click="goCreateSchedule"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg>
            Tạo lịch bảo trì
          </button>
          <p v-else class="mt-2 text-xs text-amber-700">
            Liên hệ quản lý vật tư để tạo lịch PM cho thiết bị này.
          </p>
        </div>
        <div v-if="selectedSchedule" class="mt-2 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800 grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div><span class="text-blue-600">Loại:</span> <b>{{ pmTypeLabel(selectedSchedule.pm_type) }}</b></div>
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
            <span v-if="it.is_critical" class="text-xs bg-red-100 text-red-700 rounded px-2 py-0.5">TRỌNG YẾU</span>
          </li>
        </ul>
        <p v-if="checklistPreview.length" class="text-xs text-slate-500 mt-1">{{ checklistPreview.length }} mục — kỹ thuật viên sẽ điền kết quả khi đang thực hiện.</p>
      </div>

      <!-- Due Date -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">
          Ngày thực hiện <span class="text-red-500">*</span>
        </label>
        <DateInput v-model="form.due_date" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
      </div>

      <!-- Assigned To — picker user AssetCore ĐỦ NĂNG LỰC bảo trì (PM Manager/User
           + admin), lọc server-side theo capability thay free-text email. -->
      <div>
        <ApproverSelect
          v-model="form.assigned_to"
          context="pm"
          label="Giao cho kỹ thuật viên"
          placeholder="Tìm KTV theo tên hoặc email..."
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

      <!-- Lý do nút bị khoá: phải chọn Lịch bảo trì (BE hard-require pm_schedule).
           Khi 0 schedule → trỏ tới empty-state phía trên (lối thoát Tạo lịch). -->
      <p
        v-if="form.asset_ref && !form.pm_schedule"
        data-test="submit-guidance"
        class="-mt-2 text-center text-xs text-slate-500"
      >
        <template v-if="showScheduleEmpty">
          Chưa thể tạo phiếu — thiết bị chưa có lịch bảo trì (xem hướng dẫn ở mục
          “Lịch bảo trì” phía trên).
        </template>
        <template v-else>
          Cần chọn “Lịch bảo trì” để tạo phiếu.
        </template>
      </p>
    </div>
  </div>
</template>
