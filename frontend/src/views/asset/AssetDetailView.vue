<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAssetStore } from '@/stores/imm00'
import { getAssetTimeline, getAssetKpi, verifyChain, deleteAsset } from '@/api/imm00'
import { getCommissioningOrigin, type CommissioningOrigin } from '@/api/imm04'
import {
  createDecommission, approveDecommission,
  type DisposalMethod,
} from '@/api/imm14'
import {
  showDecommissionButton, canSubmitDecommission, requiresPatientDataConfirm as needsPhiConfirm,
  DECOM_REASON_MIN_LEN,
} from '@/api/decommissionGate'
import AssetDowntimeWidget from '@/components/asset/AssetDowntimeWidget.vue'
import AssetDepreciationSchedule from '@/components/asset/AssetDepreciationSchedule.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import type { AssetLifecycleEvent, AssetKpi, ChainVerifyResult, LifecycleStatus } from '@/types/imm00'
import { translateFrequency, translateDepreciationMethod, translateLifecycleEvent, translateStatus } from '@/utils/formatters'
import { useCapabilities } from '@/composables/useCapabilities'
import { useNotify } from '@/composables/useNotify'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { toApiError } from '@/api/errors'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store = useAssetStore()
const { can } = useCapabilities()
const notify = useNotify()
const toast = useToast()
const auth = useAuthStore()

const timeline = ref<AssetLifecycleEvent[]>([])
const kpi = ref<AssetKpi | null>(null)
const origin = ref<CommissioningOrigin | null>(null)
const chain = ref<ChainVerifyResult | null>(null)
const transitioning = ref(false)
const showTransitionModal = ref(false)
const targetStatus = ref<LifecycleStatus | ''>('')
const transitionReason = ref('')
const activeTab = ref<'info' | 'depreciation' | 'timeline' | 'kpi' | 'audit'>('info')

// IMM-14: 'Decommissioned' CỐ TÌNH loại khỏi mọi transition trực tiếp — giải nhiệm
// PHẢI đi qua "Hồ sơ giải nhiệm" (nút riêng + modal closure-record), không qua nút
// chuyển-trạng-thái chung. Tránh bypass cổng closure từ FE (BE cũng chặn set
// Decommissioned ngoài closure → BAD_STATE).
const TRANSITIONS: Record<string, LifecycleStatus[]> = {
  'Draft': ['Commissioned'],
  'Commissioned': ['Active', 'Out of Service'],
  'Active': ['Under Maintenance', 'Under Repair', 'Calibrating', 'Out of Service'] as LifecycleStatus[],
  'Under Maintenance': ['Active', 'Under Repair', 'Out of Service'] as LifecycleStatus[],
  'Under Repair': ['Active', 'Out of Service'],
  'Calibrating': ['Active', 'Out of Service'],
  'Out of Service': ['Active', 'Under Repair'],
  'Decommissioned': [],
}

const statusColor: Record<string, string> = {
  'Draft': 'bg-slate-100 text-slate-700',
  'Active': 'bg-green-100 text-green-800',
  'Commissioned': 'bg-blue-100 text-blue-800',
  'Under Maintenance': 'bg-amber-100 text-amber-800',
  'Under Repair': 'bg-yellow-100 text-yellow-800',
  'Calibrating': 'bg-purple-100 text-purple-800',
  'Out of Service': 'bg-red-100 text-red-800',
  'Decommissioned': 'bg-gray-200 text-gray-500',
}

const lifecycleLabel: Record<string, string> = {
  'Draft': 'Nháp',
  'Active': 'Đang hoạt động',
  'Commissioned': 'Đã tiếp nhận',
  'Under Maintenance': 'Đang bảo trì',
  'Under Repair': 'Đang sửa chữa',
  'Calibrating': 'Đang hiệu chuẩn',
  'Out of Service': 'Ngừng hoạt động',
  'Decommissioned': 'Đã thanh lý',
}

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function formatDateTime(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleString('vi-VN')
}

function isPmOverdue(date?: string) {
  if (!date) return false
  return new Date(date) < new Date()
}

async function loadTimeline() {
  const res = await getAssetTimeline(props.id, 1, 100) as unknown as { items?: typeof timeline.value }
  if (res?.items) timeline.value = res.items
}

async function loadKpi() {
  const res = await getAssetKpi(props.id) as unknown as typeof kpi.value
  if (res) kpi.value = res
}

async function loadChain() {
  const res = await verifyChain(props.id) as unknown as typeof chain.value
  if (res) chain.value = res
}

function openTransitionModal(status: LifecycleStatus) {
  targetStatus.value = status
  transitionReason.value = ''
  showTransitionModal.value = true
}

async function confirmTransition() {
  if (!targetStatus.value) return
  transitioning.value = true
  try {
    const res = await store.transition(props.id, targetStatus.value, transitionReason.value)
    if (res.success) {
      showTransitionModal.value = false
      await Promise.all([store.fetchOne(props.id), loadTimeline(), loadKpi()])
    }
  } finally {
    transitioning.value = false
  }
}

async function onDepreciationUpdated() {
  // Khấu hao vừa thực thi/sinh lại → current_book_value + accumulated_depreciation
  // trên asset đã đổi (BE ghi read-only). Refetch để header (tab Thông tin +
  // tab Khấu hao summary) hiển thị giá trị mới, không stale.
  await store.fetchOne(props.id)
}

async function remove() {
  if (!store.currentAsset || !confirm(`Xóa thiết bị "${store.currentAsset.asset_name}"?`)) return
  try {
    await deleteAsset(props.id)
    router.push('/assets')
  } catch (e: unknown) {
    store.error = (e as Error).message || 'Không thể xóa'
  }
}

// ── IMM-14: Cổng "Hồ sơ giải nhiệm" (Decommission closure record) ──────────────
// Naming contract: api/imm14.ts → assetcore.api.imm14.create_decommission/approve_decommission
// Gate hiển thị nút: capability THẬT 'decommission.approve'/'decommission.create'
// (khớp BE rbac.py CAPABILITY_MAP → Asset Decommission submit/create; cap có thật, tránh
// empty-array trap LL-FE-22) + asset CHƯA terminal (đọc lifecycle_status, KHÔNG hardcode).
// NEG-09 (đang bảo trì/sửa/hiệu chuẩn) KHÔNG disable cứng ở FE — BE là SoT, bấm sẽ nhận
// lỗi gate VI → toast cảnh báo (doc §11.2).

const DISPOSAL_OPTIONS: { value: DisposalMethod; label: string }[] = [
  { value: 'Huỷ', label: 'Huỷ (tiêu huỷ vật lý)' },
  { value: 'Điều chuyển/Donation', label: 'Điều chuyển / Hiến tặng' },
  { value: 'Bán/Trade-in', label: 'Bán / Đổi cũ lấy mới' },
  { value: 'Lưu trữ', label: 'Lưu trữ' },
]
const REASON_MIN_LEN = DECOM_REASON_MIN_LEN

const showDecommissionModal = ref(false)
const decommissioning = ref(false)
const decomForm = ref<{
  disposal_method: DisposalMethod | ''
  patient_data_sanitized: boolean
  sanitization_note: string
  decommission_reason: string
  responsible: string
  confirm_name: string
}>({
  disposal_method: '',
  patient_data_sanitized: false,
  sanitization_note: '',
  decommission_reason: '',
  responsible: '',
  confirm_name: '',
})

// Risk class C/D (WHO §3.6) = High/Critical trên AC Asset → bắt buộc xác nhận xử lý
// dữ liệu bệnh nhân trước khi duyệt. Dùng predicate CHUNG với test (no drift).
const requiresPatientDataConfirm = computed(
  () => needsPhiConfirm(store.currentAsset?.risk_classification),
)

const isDecommissioned = computed(
  () => store.currentAsset?.lifecycle_status === 'Decommissioned',
)

// Nút chỉ hiện khi có quyền duyệt giải nhiệm (Department Head) + asset chưa terminal.
// Capability THẬT khớp BE rbac.py: 'decommission.approve' → ("Asset Decommission","submit").
// KHÔNG hardcode role-name, KHÔNG dùng cap rỗng (LL-FE-12/22). Chấp nhận create-cap như
// fallback OR (luồng MVP create→approve liên tiếp; người mở modal cần ít nhất quyền tạo).
const canDecommission = computed(
  () => showDecommissionButton(
    !!store.currentAsset,
    store.currentAsset?.lifecycle_status,
    can(['decommission.approve', 'decommission.create']),
  ),
)

// Disable nút "Xác nhận giải nhiệm" trong modal nếu chưa đủ field (mirror BE BR).
const decomReasonLen = computed(() => decomForm.value.decommission_reason.trim().length)
const decomCanSubmit = computed(
  () => canSubmitDecommission(
    decomForm.value,
    store.currentAsset?.name ?? '',
    store.currentAsset?.risk_classification,
  ),
)

function openDecommissionModal() {
  decomForm.value = {
    disposal_method: '',
    patient_data_sanitized: false,
    sanitization_note: '',
    decommission_reason: '',
    responsible: auth.user?.email ?? '',
    confirm_name: '',
  }
  showDecommissionModal.value = true
}

async function confirmDecommission() {
  if (!store.currentAsset || !decomCanSubmit.value) return
  decommissioning.value = true
  try {
    // 2-call tuần tự (doc §11.3): create_decommission (docstatus=0) → approve_decommission
    // (submit → transition asset). Lỗi gate nào cũng surface qua toast cảnh báo VI.
    const created = await createDecommission({
      asset: store.currentAsset.name,
      disposal_method: decomForm.value.disposal_method as DisposalMethod,
      decommission_reason: decomForm.value.decommission_reason.trim(),
      patient_data_sanitized: decomForm.value.patient_data_sanitized,
      responsible: decomForm.value.responsible,
      sanitization_note: decomForm.value.sanitization_note.trim() || undefined,
    })
    await approveDecommission(created.name)
    showDecommissionModal.value = false
    // Refresh asset → badge đổi 'Đã thanh lý' qua label map SSoT, nút tự ẩn.
    await Promise.all([store.fetchOne(props.id), loadTimeline()])
    toast.success('Đã giải nhiệm thiết bị thành công.')
  } catch (e: unknown) {
    // Gate-error: toast CẢNH BÁO với message VI verbatim từ BE (KHÔNG 'Lỗi hệ thống',
    // KHÔNG leak EN/raw status). toApiError giữ code + message BE đã VI hoá.
    notify.fromError(toApiError(e))
  } finally {
    decommissioning.value = false
  }
}

async function onTabChange(tab: typeof activeTab.value) {
  activeTab.value = tab
  if (tab === 'timeline' && !timeline.value.length) await loadTimeline()
  if (tab === 'kpi' && !kpi.value) await loadKpi()
  if (tab === 'audit' && !chain.value) await loadChain()
}

onMounted(async () => {
  await store.fetchOne(props.id)
  try { origin.value = await getCommissioningOrigin(props.id) } catch { origin.value = null }
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      back-to="/assets"
      back-label="← Danh sách thiết bị"
      :title="store.currentAsset?.asset_name || 'Chi tiết thiết bị'"
      :subtitle="store.currentAsset ? `Mã: ${store.currentAsset.name}` : ''"
      :breadcrumb="[
        { label: 'Thiết bị', to: '/assets' },
        { label: store.currentAsset?.asset_name || id },
      ]"
    >
      <template #actions>
        <button v-if="store.currentAsset" class="btn-ghost text-sm" @click="router.push(`/assets/${id}/edit`)">Chỉnh sửa</button>
        <button v-if="store.currentAsset" class="text-red-600 hover:text-red-800 text-sm font-medium px-3 py-1.5" @click="remove">Xóa</button>
      </template>
    </PageHeader>

    <div v-if="store.loading" class="card p-8 text-center text-slate-400">Đang tải...</div>
    <div v-else-if="store.error" class="alert-error">{{ store.error }}</div>

    <template v-else-if="store.currentAsset">
      <!-- Asset Header -->
      <div class="card p-5 mb-5">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">AC Asset</p>
            <h1 class="text-xl font-bold text-slate-900">{{ store.currentAsset.asset_name }}</h1>
            <p class="text-sm text-slate-400 mt-0.5">{{ store.currentAsset.name }}</p>
          </div>
          <span
            class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
            :class="statusColor[store.currentAsset.lifecycle_status] || 'bg-gray-100 text-gray-600'"
          >
            {{ lifecycleLabel[store.currentAsset.lifecycle_status] || store.currentAsset.lifecycle_status }}
          </span>
        </div>

        <!-- Transition buttons -->
        <div v-if="TRANSITIONS[store.currentAsset.lifecycle_status]?.length" class="mt-4 flex flex-wrap gap-2">
          <span class="text-xs text-slate-400 self-center">Chuyển trạng thái:</span>
          <button
            v-for="s in TRANSITIONS[store.currentAsset.lifecycle_status]"
            :key="s"
            class="px-3 py-1 text-xs rounded-md border border-slate-300 text-slate-600 hover:bg-slate-100 transition-colors"
            @click="openTransitionModal(s)"
          >
            → {{ lifecycleLabel[s] || s }}
          </button>
        </div>
      </div>

      <!-- Nguồn gốc: Purchase → Commissioning → Asset trail -->
      <div v-if="origin?.commissioning" class="card p-4 mb-5 bg-gradient-to-r from-blue-50 to-emerald-50 border border-blue-200">
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Nguồn gốc tài sản</p>
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <router-link
            v-if="origin.commissioning.po_reference"
            :to="`/purchases/${origin.commissioning.po_reference}`"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-lg border border-slate-200 hover:border-blue-400 hover:shadow-sm transition-all"
          >
            <span class="text-xs text-slate-400">Đơn mua:</span>
            <span class="font-mono text-xs font-semibold text-blue-700">{{ origin.commissioning.po_reference }}</span>
          </router-link>
          <svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          <router-link
            :to="`/commissioning/${origin.commissioning.name}`"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-lg border border-slate-200 hover:border-blue-400 hover:shadow-sm transition-all"
          >
            <span class="text-xs text-slate-400">Phiếu tiếp nhận:</span>
            <span class="font-mono text-xs font-semibold text-indigo-700">{{ origin.commissioning.name }}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 ml-1">
              {{ origin.commissioning.workflow_state }}
            </span>
          </router-link>
          <svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          <span class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 rounded-lg text-white text-xs font-semibold">
            ✓ Tài sản đã hình thành
          </span>
        </div>
        <div class="flex flex-wrap gap-x-5 gap-y-1 mt-3 text-xs text-slate-600">
          <span v-if="origin.commissioning.vendor_serial_no">
            S/N: <span class="font-mono font-medium">{{ origin.commissioning.vendor_serial_no }}</span>
          </span>
          <span v-if="origin.commissioning.reception_date">
            Nhận hàng: <b>{{ origin.commissioning.reception_date }}</b>
          </span>
          <span v-if="origin.commissioning.commissioning_date">
            Nghiệm thu: <b>{{ origin.commissioning.commissioning_date }}</b>
          </span>
          <span v-if="origin.commissioning.transferred_doc_count !== undefined">
            Hồ sơ: <b>{{ origin.commissioning.transferred_doc_count }}</b> tài liệu tự động chuyển
          </span>
        </div>
      </div>

      <!-- Cross-module quick actions — liên kết trực tiếp đến IMM-05/08/09/11/00 -->
      <div class="card p-3 mb-5">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider px-2">Hành động</span>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
            title="Xem hồ sơ NĐ98 của thiết bị"
            @click="router.push(`/documents?asset=${id}`)"
          >
📋 Hồ sơ
</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors"
            title="Lịch sử bảo trì định kỳ"
            @click="router.push(`/pm/work-orders?asset=${id}`)"
          >
🛠️ Bảo trì định kỳ
</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors"
            title="Lịch sử sửa chữa"
            @click="router.push(`/cm/work-orders?asset=${id}`)"
          >
🔧 Sửa chữa
</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-purple-50 text-purple-700 hover:bg-purple-100 transition-colors"
            title="Lịch sử hiệu chuẩn"
            @click="router.push(`/calibration?asset=${id}`)"
          >
📐 Hiệu chuẩn
</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
            title="Lịch sử luân chuyển"
            @click="router.push(`/asset-transfers?asset=${id}`)"
          >
🔄 Luân chuyển
</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-red-50 text-red-700 hover:bg-red-100 transition-colors"
            title="Báo cáo sự cố mới cho thiết bị này"
            @click="router.push(`/incidents/new?asset=${id}`)"
          >
⚠️ Báo sự cố
</button>
          <!-- IMM-14: Giải nhiệm thiết bị — chỉ hiện khi có quyền + asset chưa terminal -->
          <button
            v-if="canDecommission"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
            title="Lập hồ sơ giải nhiệm thiết bị (cần đóng phiếu bảo trì/sửa/hiệu chuẩn đang mở trước)"
            data-testid="btn-decommission"
            @click="openDecommissionModal"
          >
🗑️ Giải nhiệm thiết bị
</button>
          <span
            v-else-if="isDecommissioned"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-gray-200 text-gray-500"
            data-testid="badge-decommissioned"
          >
✓ Đã giải nhiệm
</span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 mb-4 border-b border-slate-200">
        <button
          v-for="tab in (['info', 'depreciation', 'timeline', 'kpi', 'audit'] as const)"
          :key="tab"
          class="px-4 py-2 text-sm font-medium transition-colors"
          :class="activeTab === tab ? 'text-blue-600 border-b-2 border-blue-600 -mb-px' : 'text-slate-500 hover:text-slate-800'"
          @click="onTabChange(tab)"
        >
          {{ { info: 'Thông tin', depreciation: 'Khấu hao', timeline: 'Lịch sử', kpi: 'KPI', audit: 'Audit Trail' }[tab] }}
        </button>
      </div>

      <!-- Tab: Info -->
      <div v-if="activeTab === 'info'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <AssetDowntimeWidget class="md:col-span-2" :asset-name="store.currentAsset.name" />
        <div class="card p-4">
          <h3 class="text-sm font-semibold text-slate-700 mb-3">Thông tin chung</h3>
          <dl class="space-y-2 text-sm">
            <div class="flex justify-between gap-2">
              <dt class="text-slate-400 shrink-0">Danh mục</dt>
              <dd class="text-slate-800 text-right">
                <div>{{ store.currentAsset.category_name || store.currentAsset.asset_category || '—' }}</div>
                <div v-if="store.currentAsset.asset_category && store.currentAsset.category_name" class="text-xs text-slate-400">{{ store.currentAsset.asset_category }}</div>
              </dd>
            </div>
            <div class="flex justify-between gap-2">
              <dt class="text-slate-400 shrink-0">Nhà cung cấp</dt>
              <dd class="text-slate-800 text-right">
                <div>{{ store.currentAsset.supplier_name || store.currentAsset.supplier || '—' }}</div>
                <div v-if="store.currentAsset.supplier && store.currentAsset.supplier_name" class="text-xs text-slate-400">{{ store.currentAsset.supplier }}</div>
              </dd>
            </div>
            <div class="flex justify-between gap-2">
              <dt class="text-slate-400 shrink-0">Khoa/Phòng</dt>
              <dd class="text-slate-800 text-right">
                <div>{{ store.currentAsset.department_name || store.currentAsset.department || '—' }}</div>
                <div v-if="store.currentAsset.department && store.currentAsset.department_name" class="text-xs text-slate-400">{{ store.currentAsset.department }}</div>
              </dd>
            </div>
            <div class="flex justify-between gap-2">
              <dt class="text-slate-400 shrink-0">Vị trí</dt>
              <dd class="text-slate-800 text-right">
                <div>{{ store.currentAsset.location_name || store.currentAsset.location || '—' }}</div>
                <div v-if="store.currentAsset.location && store.currentAsset.location_name" class="text-xs text-slate-400">{{ store.currentAsset.location }}</div>
              </dd>
            </div>
            <div class="flex justify-between gap-2">
              <dt class="text-slate-400 shrink-0">Kỹ thuật viên</dt>
              <dd class="text-slate-800 text-right">
                <div>{{ store.currentAsset.responsible_technician_name || store.currentAsset.responsible_technician || '—' }}</div>
                <div v-if="store.currentAsset.responsible_technician && store.currentAsset.responsible_technician_name" class="text-xs text-slate-400">{{ store.currentAsset.responsible_technician }}</div>
              </dd>
            </div>
            <div class="flex justify-between"><dt class="text-slate-400">Ngày mua</dt><dd class="text-slate-800">{{ formatDate(store.currentAsset.purchase_date) }}</dd></div>
            <div class="flex justify-between"><dt class="text-slate-400">Giá mua</dt><dd class="text-slate-800">{{ store.currentAsset.gross_purchase_amount?.toLocaleString('vi-VN') || '—' }} VND</dd></div>
          </dl>
        </div>
        <div class="card p-4">
          <h3 class="text-sm font-semibold text-slate-700 mb-3">Thông tin HTM</h3>
          <dl class="space-y-2 text-sm">
            <div class="flex justify-between"><dt class="text-slate-400">Serial No</dt><dd class="text-slate-800 font-mono text-xs">{{ store.currentAsset.manufacturer_sn || '—' }}</dd></div>
            <div class="flex justify-between"><dt class="text-slate-400">UDI Code</dt><dd class="text-slate-800 font-mono text-xs">{{ store.currentAsset.udi_code || '—' }}</dd></div>
            <div class="flex justify-between"><dt class="text-slate-400">GMDN</dt><dd class="text-slate-800">{{ store.currentAsset.gmdn_code || '—' }}</dd></div>
            <div class="flex justify-between items-center">
              <dt class="text-slate-400 shrink-0">Phiếu nghiệm thu</dt>
              <dd class="text-right">
                <router-link
                  v-if="store.currentAsset.commissioning_ref"
                  :to="`/commissioning/${store.currentAsset.commissioning_ref}`"
                  class="font-mono text-xs text-blue-600 hover:underline"
                >
{{ store.currentAsset.commissioning_ref }}
</router-link>
                <span v-else class="text-slate-400">—</span>
              </dd>
            </div>
            <div class="flex justify-between"><dt class="text-slate-400">Ngày nghiệm thu</dt><dd class="text-slate-800">{{ formatDate(store.currentAsset.commissioning_date) }}</dd></div>
            <div class="flex justify-between"><dt class="text-slate-400">Số đăng ký Bộ Y tế</dt><dd class="text-slate-800">{{ store.currentAsset.byt_reg_no || '—' }}</dd></div>
            <div class="flex justify-between">
              <dt class="text-slate-400">Hạn đăng ký Bộ Y tế</dt>
              <dd :class="isPmOverdue(store.currentAsset.byt_reg_expiry) ? 'text-red-600 font-semibold' : 'text-slate-800'">
                {{ formatDate(store.currentAsset.byt_reg_expiry) }}
              </dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-slate-400">Bảo trì tiếp theo</dt>
              <dd :class="isPmOverdue(store.currentAsset.next_pm_date) ? 'text-red-600 font-semibold' : 'text-slate-800'">
                {{ formatDate(store.currentAsset.next_pm_date) }}
              </dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-slate-400">Hiệu chuẩn tiếp theo</dt>
              <dd :class="isPmOverdue(store.currentAsset.next_calibration_date) ? 'text-red-600 font-semibold' : 'text-slate-800'">
                {{ formatDate(store.currentAsset.next_calibration_date) }}
              </dd>
            </div>
          </dl>
        </div>

        <!-- Depreciation summary card (Tier 1 rules) -->
        <div class="card p-4 md:col-span-2">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-slate-700">Khấu hao</h3>
            <button class="text-xs text-blue-600 hover:underline" @click="activeTab = 'depreciation'">
              Xem chi tiết →
            </button>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p class="text-xs text-slate-400 mb-0.5">Phương pháp</p>
              <p class="font-medium text-slate-800">{{ translateDepreciationMethod(store.currentAsset.depreciation_method) }}</p>
              <p v-if="store.currentAsset.total_depreciation_months" class="text-xs text-slate-400 mt-0.5">
                {{ store.currentAsset.total_depreciation_months }} tháng · {{ translateFrequency(store.currentAsset.depreciation_frequency) }}
              </p>
            </div>
            <div>
              <p class="text-xs text-slate-400 mb-0.5">Nguyên giá</p>
              <p class="font-semibold text-slate-900">
                {{ store.currentAsset.gross_purchase_amount?.toLocaleString('vi-VN') || '—' }}
              </p>
              <p class="text-xs text-slate-400 mt-0.5">VND</p>
            </div>
            <div>
              <p class="text-xs text-slate-400 mb-0.5">Đã khấu hao</p>
              <p class="font-semibold text-red-600">
                −{{ store.currentAsset.accumulated_depreciation?.toLocaleString('vi-VN') || '0' }}
              </p>
              <p class="text-xs text-slate-400 mt-0.5">VND</p>
            </div>
            <div>
              <p class="text-xs text-slate-400 mb-0.5">Giá trị còn lại</p>
              <p class="font-semibold text-emerald-600">
                {{ store.currentAsset.current_book_value?.toLocaleString('vi-VN')
                   || store.currentAsset.gross_purchase_amount?.toLocaleString('vi-VN')
                   || '—' }}
              </p>
              <p class="text-xs text-slate-400 mt-0.5">VND</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: Depreciation -->
      <div v-if="activeTab === 'depreciation'">
        <!-- @updated: sau khi chạy/sinh lại khấu hao, refetch asset để header
             "Giá trị còn lại" (current_book_value) khớp ngay dòng schedule cuối
             (INV-DEP-3) — không hiển thị giá trị cũ stale. -->
        <AssetDepreciationSchedule
          :asset-name="store.currentAsset.name"
          @updated="onDepreciationUpdated"
        />
      </div>

      <!-- Tab: Timeline -->
      <div v-if="activeTab === 'timeline'">
        <div v-if="!timeline.length" class="card p-8 text-center text-slate-400 text-sm">
          Chưa có sự kiện vòng đời
        </div>
        <div v-else class="relative">
          <div class="absolute left-5 top-0 bottom-0 w-0.5 bg-slate-200"></div>
          <div v-for="event in timeline" :key="event.name" class="relative flex gap-4 mb-4">
            <div class="shrink-0 w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center z-10">
              <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div class="card flex-1 p-3">
              <div class="flex justify-between items-start">
                <span class="font-semibold text-sm text-slate-800" data-testid="ale-event-type">{{ translateLifecycleEvent(event.event_type) }}</span>
                <span class="text-xs text-slate-400">{{ formatDateTime(event.event_timestamp) }}</span>
              </div>
              <p v-if="event.from_status || event.to_status" class="text-xs text-slate-500 mt-1" data-testid="ale-status-transition">
                {{ translateStatus(event.from_status) }} → {{ translateStatus(event.to_status) }}
              </p>
              <p v-if="event.notes" class="text-xs text-slate-600 mt-1">{{ event.notes }}</p>
              <p class="text-xs text-slate-400 mt-1">bởi {{ event.actor }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: KPI -->
      <div v-if="activeTab === 'kpi'">
        <div v-if="!kpi" class="card p-8 text-center text-slate-400 text-sm">Đang tải KPI...</div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div class="card p-4 text-center">
            <p class="text-xs text-slate-400 mb-1">Uptime</p>
            <p class="text-2xl font-bold text-green-600">{{ kpi.uptime_pct != null ? kpi.uptime_pct.toFixed(1) + '%' : '—' }}</p>
          </div>
          <div class="card p-4 text-center">
            <p class="text-xs text-slate-400 mb-1">Thời gian giữa 2 lần hỏng (ngày)</p>
            <p class="text-2xl font-bold text-blue-600">{{ kpi.mtbf_days ?? '—' }}</p>
          </div>
          <div class="card p-4 text-center">
            <p class="text-xs text-slate-400 mb-1">Thời gian sửa TB (giờ)</p>
            <p class="text-2xl font-bold text-yellow-600">{{ kpi.mttr_hours ?? '—' }}</p>
          </div>
          <div class="card p-4 text-center">
            <p class="text-xs text-slate-400 mb-1">Bảo trì đúng hạn</p>
            <p class="text-2xl font-bold text-purple-600">{{ kpi.pm_compliance_pct != null ? kpi.pm_compliance_pct.toFixed(1) + '%' : '—' }}</p>
          </div>
          <div class="card p-4 text-center col-span-2 md:col-span-4">
            <p class="text-xs text-slate-400 mb-1">Tổng chi phí sửa chữa</p>
            <p class="text-xl font-bold text-red-600">{{ kpi.total_repair_cost?.toLocaleString('vi-VN') ?? '—' }} VND</p>
          </div>
        </div>
      </div>

      <!-- Tab: Audit Trail -->
      <div v-if="activeTab === 'audit'">
        <div v-if="chain" class="card p-3 mb-4 flex items-center gap-3">
          <span
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
            :class="chain.valid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path v-if="chain.valid" stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              <path v-else stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            {{ chain.valid ? 'Chain hợp lệ' : 'Chain bị phá vỡ' }}
          </span>
          <span class="text-xs text-slate-500">{{ chain.count }} bản ghi</span>
          <span v-if="!chain.valid" class="text-xs text-red-600">Tại: {{ chain.broken_at }}</span>
        </div>
        <p v-else class="text-xs text-slate-400 mb-3">Chưa verify chain</p>
        <button v-if="!chain" class="btn-ghost text-xs mb-4" @click="loadChain">Verify Audit Chain</button>
        <p class="text-sm text-slate-500 italic">Xem audit trail chi tiết tại tab Lịch sử hoặc query API.</p>
      </div>
    </template>

    <!-- Transition Modal -->
    <div v-if="showTransitionModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
        <h3 class="font-semibold text-slate-900 mb-1">Chuyển trạng thái</h3>
        <p class="text-sm text-slate-500 mb-4">
          {{ store.currentAsset?.lifecycle_status }} → <strong>{{ targetStatus }}</strong>
        </p>
        <label class="block text-xs font-medium text-slate-600 mb-1">Lý do (tùy chọn)</label>
        <textarea
          v-model="transitionReason"
          rows="3"
          class="form-input w-full text-sm mb-4"
          placeholder="Mô tả lý do chuyển trạng thái..."
        />
        <div class="flex gap-2 justify-end">
          <button class="btn-ghost text-sm" @click="showTransitionModal = false">Huỷ</button>
          <button class="btn-primary text-sm" :disabled="transitioning" @click="confirmTransition">
            {{ transitioning ? 'Đang xử lý...' : 'Xác nhận' }}
          </button>
        </div>
      </div>
    </div>

    <!-- IMM-14: Modal Hồ sơ giải nhiệm (closure record) -->
    <BaseModal
      v-if="showDecommissionModal"
      title="Hồ sơ giải nhiệm thiết bị"
      size="lg"
      danger
      @close="showDecommissionModal = false"
    >
      <div class="space-y-4 text-sm">
        <div class="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800">
          Hành động <strong>không thể đảo ngược</strong>. Sau khi duyệt, thiết bị chuyển sang
          trạng thái <strong>Đã thanh lý</strong> và không thể thao tác tiếp.
        </div>

        <!-- Phương thức xử lý -->
        <div>
          <label class="block text-xs font-medium text-slate-600 mb-1">
            Phương thức xử lý <span class="text-red-500">*</span>
          </label>
          <select
            v-model="decomForm.disposal_method"
            class="form-input w-full text-sm"
            data-testid="decom-disposal-method"
          >
            <option value="" disabled>— Chọn phương thức xử lý —</option>
            <option v-for="o in DISPOSAL_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
          <p class="text-xs text-slate-400 mt-1">Theo WHO §3.8 / NĐ98.</p>
        </div>

        <!-- Xác nhận xử lý dữ liệu bệnh nhân -->
        <div
          class="rounded-lg px-3 py-2.5"
          :class="requiresPatientDataConfirm ? 'bg-red-50 border border-red-200' : 'bg-slate-50 border border-slate-200'"
        >
          <label class="flex items-start gap-2 cursor-pointer">
            <input
              v-model="decomForm.patient_data_sanitized"
              type="checkbox"
              class="mt-0.5"
              data-testid="decom-patient-data"
            />
            <span class="text-xs text-slate-700">
              Đã xoá / xử lý dữ liệu bệnh nhân trên thiết bị.
              <span v-if="requiresPatientDataConfirm" class="block text-red-600 font-medium mt-0.5">
                Thiết bị phân loại nguy cơ C/D — bắt buộc xác nhận (WHO §3.6).
              </span>
            </span>
          </label>
          <input
            v-model="decomForm.sanitization_note"
            type="text"
            class="form-input w-full text-xs mt-2"
            placeholder="Ghi chú cách xử lý dữ liệu (tuỳ chọn)..."
            data-testid="decom-sanitization-note"
          />
        </div>

        <!-- Lý do giải nhiệm -->
        <div>
          <label class="block text-xs font-medium text-slate-600 mb-1">
            Lý do giải nhiệm <span class="text-red-500">*</span>
          </label>
          <textarea
            v-model="decomForm.decommission_reason"
            rows="3"
            class="form-input w-full text-sm"
            placeholder="Mô tả lý do giải nhiệm (hết khấu hao, sửa chữa không kinh tế, có quyết định thanh lý...)"
            data-testid="decom-reason"
          />
          <p class="text-xs mt-1" :class="decomReasonLen < REASON_MIN_LEN ? 'text-red-500' : 'text-slate-400'">
            {{ decomReasonLen }}/{{ REASON_MIN_LEN }} ký tự tối thiểu
          </p>
        </div>

        <!-- Người chịu trách nhiệm -->
        <div>
          <label class="block text-xs font-medium text-slate-600 mb-1">
            Người chịu trách nhiệm <span class="text-red-500">*</span>
          </label>
          <SmartSelect
            v-model="decomForm.responsible"
            doctype="User"
            placeholder="Chọn người chịu trách nhiệm..."
            data-testid="decom-responsible"
          />
        </div>

        <!-- Xác nhận 2 bước: gõ đúng mã thiết bị -->
        <div class="pt-2 border-t border-slate-100">
          <label class="block text-xs font-medium text-slate-600 mb-1">
            Gõ mã thiết bị <span class="font-mono text-slate-800">{{ store.currentAsset?.name }}</span>
            để xác nhận <span class="text-red-500">*</span>
          </label>
          <input
            v-model="decomForm.confirm_name"
            type="text"
            class="form-input w-full text-sm font-mono"
            :placeholder="store.currentAsset?.name"
            data-testid="decom-confirm-name"
          />
        </div>
      </div>

      <template #footer>
        <button class="btn-ghost text-sm" @click="showDecommissionModal = false">Huỷ</button>
        <button
          class="text-sm px-4 py-2 rounded-lg font-medium text-white transition-colors"
          :class="decomCanSubmit && !decommissioning ? 'bg-red-600 hover:bg-red-700' : 'bg-slate-300 cursor-not-allowed'"
          :disabled="!decomCanSubmit || decommissioning"
          data-testid="decom-submit"
          @click="confirmDecommission"
        >
          {{ decommissioning ? 'Đang xử lý...' : 'Xác nhận giải nhiệm' }}
        </button>
      </template>
    </BaseModal>
</div>
</template>
