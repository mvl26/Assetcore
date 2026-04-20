<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAssetStore } from '@/stores/imm00'
import { getAssetTimeline, getAssetKpi, verifyChain, deleteAsset } from '@/api/imm00'
import AssetDowntimeWidget from '@/components/asset/AssetDowntimeWidget.vue'
import type { AssetLifecycleEvent, AssetKpi, ChainVerifyResult, LifecycleStatus } from '@/types/imm00'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store = useAssetStore()

const timeline = ref<AssetLifecycleEvent[]>([])
const kpi = ref<AssetKpi | null>(null)
const chain = ref<ChainVerifyResult | null>(null)
const transitioning = ref(false)
const showTransitionModal = ref(false)
const targetStatus = ref<LifecycleStatus | ''>('')
const transitionReason = ref('')
const activeTab = ref<'info' | 'timeline' | 'kpi' | 'audit'>('info')

const TRANSITIONS: Record<string, LifecycleStatus[]> = {
  'Commissioned': ['Active', 'Out of Service', 'Decommissioned'],
  'Active': ['Under Maintenance', 'Under Repair', 'Calibrating', 'Out of Service', 'Decommissioned'] as LifecycleStatus[],
  'Under Maintenance': ['Active', 'Under Repair', 'Out of Service', 'Decommissioned'] as LifecycleStatus[],
  'Under Repair': ['Active', 'Out of Service', 'Decommissioned'],
  'Calibrating': ['Active', 'Out of Service', 'Decommissioned'],
  'Out of Service': ['Active', 'Under Repair', 'Decommissioned'],
  'Decommissioned': [],
}

const statusColor: Record<string, string> = {
  'Active': 'bg-green-100 text-green-800',
  'Commissioned': 'bg-blue-100 text-blue-800',
  'Under Maintenance': 'bg-amber-100 text-amber-800',
  'Under Repair': 'bg-yellow-100 text-yellow-800',
  'Calibrating': 'bg-purple-100 text-purple-800',
  'Out of Service': 'bg-red-100 text-red-800',
  'Decommissioned': 'bg-gray-200 text-gray-500',
}

const lifecycleLabel: Record<string, string> = {
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

async function remove() {
  if (!store.currentAsset || !confirm(`Xóa thiết bị "${store.currentAsset.asset_name}"?`)) return
  try {
    await deleteAsset(props.id)
    router.push('/assets')
  } catch (e: unknown) {
    store.error = (e as Error).message || 'Không thể xóa'
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
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Back + Actions -->
    <div class="flex items-center justify-between mb-5">
      <button class="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800" @click="router.push('/assets')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Danh sách thiết bị
      </button>
      <div v-if="store.currentAsset" class="flex gap-2">
        <button class="btn-ghost text-sm" @click="router.push(`/assets/${id}/edit`)">Chỉnh sửa</button>
        <button class="text-red-600 hover:text-red-800 text-sm font-medium px-3 py-1.5" @click="remove">Xóa</button>
      </div>
    </div>

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

      <!-- Cross-module quick actions — liên kết trực tiếp đến IMM-05/08/09/11/00 -->
      <div class="card p-3 mb-5">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider px-2">Hành động</span>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
            @click="router.push(`/documents?asset=${id}`)"
            title="Xem hồ sơ NĐ98 của thiết bị (IMM-05)"
          >📋 Hồ sơ</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors"
            @click="router.push(`/pm/work-orders?asset=${id}`)"
            title="Lịch sử bảo trì định kỳ (IMM-08)"
          >🛠️ Bảo trì PM</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors"
            @click="router.push(`/cm/work-orders?asset=${id}`)"
            title="Lịch sử sửa chữa (IMM-09)"
          >🔧 Sửa chữa</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-purple-50 text-purple-700 hover:bg-purple-100 transition-colors"
            @click="router.push(`/calibration?asset=${id}`)"
            title="Lịch sử hiệu chuẩn (IMM-11)"
          >📐 Hiệu chuẩn</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
            @click="router.push(`/asset-transfers?asset=${id}`)"
            title="Lịch sử luân chuyển"
          >🔄 Luân chuyển</button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-red-50 text-red-700 hover:bg-red-100 transition-colors"
            @click="router.push(`/incidents/new?asset=${id}`)"
            title="Báo cáo sự cố mới cho thiết bị này"
          >⚠️ Báo sự cố</button>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 mb-4 border-b border-slate-200">
        <button
          v-for="tab in (['info', 'timeline', 'kpi', 'audit'] as const)"
          :key="tab"
          class="px-4 py-2 text-sm font-medium transition-colors"
          :class="activeTab === tab ? 'text-blue-600 border-b-2 border-blue-600 -mb-px' : 'text-slate-500 hover:text-slate-800'"
          @click="onTabChange(tab)"
        >
          {{ { info: 'Thông tin', timeline: 'Lịch sử', kpi: 'KPI', audit: 'Audit Trail' }[tab] }}
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
            <div class="flex justify-between"><dt class="text-slate-400">Số BYT</dt><dd class="text-slate-800">{{ store.currentAsset.byt_reg_no || '—' }}</dd></div>
            <div class="flex justify-between">
              <dt class="text-slate-400">Hạn BYT</dt>
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
                <span class="font-semibold text-sm text-slate-800">{{ event.event_type }}</span>
                <span class="text-xs text-slate-400">{{ formatDateTime(event.event_timestamp) }}</span>
              </div>
              <p v-if="event.from_status || event.to_status" class="text-xs text-slate-500 mt-1">
                {{ event.from_status }} → {{ event.to_status }}
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
        <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="card p-4 text-center">
            <p class="text-xs text-slate-400 mb-1">Uptime</p>
            <p class="text-2xl font-bold text-green-600">{{ kpi.uptime_pct != null ? kpi.uptime_pct.toFixed(1) + '%' : '—' }}</p>
          </div>
          <div class="card p-4 text-center">
            <p class="text-xs text-slate-400 mb-1">MTBF (ngày)</p>
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
  </div>
</template>
