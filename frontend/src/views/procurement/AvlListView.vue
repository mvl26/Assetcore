<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, computed, onMounted } from 'vue'
import { useImm03Store } from '@/stores/imm03'
import { approveAvl, suspendAvl, createAvlEntry } from '@/api/imm03'
import type { AvlListItem, AvlState } from '@/types/imm03'
import { stateLabel, formatVnDate } from '@/utils/wave2Labels'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar, { type FilterChip } from '@/components/common/ListFilterBar.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const store = useImm03Store()

const STATES: AvlState[] = ['Draft', 'Approved', 'Conditional', 'Suspended', 'Expired']
const EXPIRY_BUCKETS = [
  { value: 'expiring30', label: 'Sắp hết hạn (≤ 30 ngày)' },
  { value: 'expired',    label: 'Đã hết hạn' },
] as const
type ExpiryBucket = typeof EXPIRY_BUCKETS[number]['value']

const showFilters = ref(false)
const filters = reactive<{
  workflow_state: AvlState | ''
  supplier: string
  device_category: string
  expiry_bucket: ExpiryBucket | ''
  search: string
}>({
  workflow_state: 'Approved',
  supplier: '',
  device_category: '',
  expiry_bucket: '',
  search: '',
})

const showCreate = ref(false)
const newAvl = reactive({
  supplier: '',
  device_category: '',
  validity_years: 2,
  valid_from: new Date().toISOString().slice(0, 10),
})
const canCreate = computed(() => newAvl.supplier && newAvl.device_category && newAvl.validity_years >= 1)

function daysLeft(a: AvlListItem): number {
  if (!a.valid_to) return 0
  return Math.ceil((new Date(a.valid_to).getTime() - Date.now()) / (1000 * 86400))
}
function isExpiring(a: AvlListItem): boolean {
  const d = daysLeft(a); return d > 0 && d <= 30
}

const activeChips = computed<FilterChip[]>(() => {
  const c: FilterChip[] = []
  if (filters.workflow_state)  c.push({ key: 'workflow_state', label: stateLabel(filters.workflow_state) })
  if (filters.supplier)        c.push({ key: 'supplier', label: `Nhà cung cấp: ${filters.supplier}` })
  if (filters.device_category) c.push({ key: 'device_category', label: `Nhóm: ${filters.device_category}` })
  if (filters.expiry_bucket) {
    const b = EXPIRY_BUCKETS.find(x => x.value === filters.expiry_bucket)
    c.push({ key: 'expiry_bucket', label: b?.label ?? filters.expiry_bucket })
  }
  if (filters.search.trim())   c.push({ key: 'search', label: `"${filters.search.trim()}"` })
  return c
})

function buildPayload(): Record<string, unknown> {
  const f: Record<string, unknown> = {}
  if (filters.workflow_state)  f.workflow_state = filters.workflow_state
  if (filters.supplier)        f.supplier = filters.supplier
  if (filters.device_category) f.device_category = filters.device_category
  if (filters.search.trim())   f.search = filters.search.trim()
  return f
}
function applyFilters() { store.fetchAvl(buildPayload()) }
function resetFilters() {
  filters.workflow_state = ''
  filters.supplier = ''
  filters.device_category = ''
  filters.expiry_bucket = ''
  filters.search = ''
  store.fetchAvl()
}
function clearChip(key: string) {
  ;(filters as Record<string, string>)[key] = ''
  applyFilters()
}
function quickFilter(key: keyof typeof filters, value: string) {
  ;(filters as Record<string, string>)[key] = value
  showFilters.value = false
  applyFilters()
}

const filteredAvl = computed(() => {
  if (!filters.expiry_bucket) return store.avlEntries
  return store.avlEntries.filter(a => {
    const d = daysLeft(a)
    if (filters.expiry_bucket === 'expiring30') return d > 0 && d <= 30
    if (filters.expiry_bucket === 'expired')    return d <= 0
    return true
  })
})

async function doApproveAvl(a: AvlListItem) {
  const approver = globalThis.prompt('Tài khoản người phê duyệt:', 'admin@example.com')
  if (!approver) return
  await approveAvl(a.name, approver)
  applyFilters()
}
async function doSuspendAvl(a: AvlListItem) {
  const reason = globalThis.prompt('Lý do đình chỉ giấy phép:')
  if (!reason) return
  await suspendAvl(a.name, reason)
  applyFilters()
}
async function doCreate() {
  if (!canCreate.value) return
  await createAvlEntry(newAvl.supplier, newAvl.device_category, newAvl.validity_years, newAvl.valid_from)
  showCreate.value = false
  newAvl.supplier = ''; newAvl.device_category = ''
  applyFilters()
}

onMounted(() => {
  store.fetchAvl({ workflow_state: 'Approved' })
  store.fetchKpis()
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Danh mục nhà cung cấp được duyệt"
      :subtitle="`Tổng ${store.avlEntries.length} giấy phép — cấp phép theo nhóm thiết bị, có hạn hiệu lực.`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeChips.length" />
        <button class="btn-primary shrink-0" @click="showCreate = true">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Cấp mới
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      v-model:search="filters.search"
      :show="showFilters"
      :chips="activeChips"
      search-placeholder="Tìm theo nhà cung cấp, nhóm thiết bị..."
      @apply="applyFilters"
      @reset="resetFilters"
      @clear-chip="clearChip"
    >
      <template #fields>
        <select v-model="filters.workflow_state" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in STATES" :key="s" :value="s">{{ stateLabel(s) }}</option>
        </select>
        <select v-model="filters.expiry_bucket" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả hiệu lực</option>
          <option v-for="b in EXPIRY_BUCKETS" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </template>
    </ListFilterBar>

    <div v-if="store.kpis" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
      <KpiCard label="Đang hiệu lực" :value="store.kpis.avl_active" color="success" />
      <KpiCard
        label="Sắp hết hạn (≤ 30 ngày)"
        :value="store.kpis.avl_expiring_30d"
        :color="store.kpis.avl_expiring_30d > 0 ? 'warning' : 'neutral'"
      />
    </div>

    <div v-if="store.error" class="alert-error mb-4">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeChips.length > 0">Kết quả lọc: <strong class="text-slate-700">{{ filteredAvl.length }}</strong> giấy phép</span>
          <span v-else>Hiển thị <strong class="text-slate-700">{{ filteredAvl.length }}</strong> giấy phép</span>
        </span>
        <button v-if="activeChips.length > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="store.loading" class="p-6 text-sm text-slate-500">Đang tải...</div>
      <div v-else-if="filteredAvl.length" class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mã giấy phép</th>
              <th>Nhà cung cấp</th>
              <th>Nhóm thiết bị</th>
              <th>Thời hạn hiệu lực</th>
              <th>Trạng thái</th>
              <th>Hành động</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(a, idx) in filteredAvl" :key="a.name"
              class="animate-fade-in" :class="[`stagger-${Math.min(idx + 1, 8)}`]"
            >
              <td><span class="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{{ a.name }}</span></td>
              <td>
                <button class="link-cell" :title="`Lọc: ${a.supplier}`" @click="quickFilter('supplier', a.supplier)">
                  {{ a.vendor_name || a.supplier }}
                </button>
              </td>
              <td>
                <button class="link-cell" :title="`Lọc: ${a.device_category}`" @click="quickFilter('device_category', a.device_category)">
                  {{ (a as any).device_category_name || a.device_category }}
                </button>
              </td>
              <td>
                {{ formatVnDate(a.valid_from) }} → {{ formatVnDate(a.valid_to) }}
                <span v-if="isExpiring(a)" class="warn-text">⏰ Còn {{ daysLeft(a) }} ngày</span>
              </td>
              <td>
                <button
type="button" class="pill-btn"
                        :title="`Lọc trạng thái: ${stateLabel(a.workflow_state)}`"
                        @click="quickFilter('workflow_state', a.workflow_state)">
                  <StatusBadge :state="a.workflow_state" />
                </button>
              </td>
              <td class="actions-col">
                <button v-if="a.workflow_state === 'Draft'" class="btn-mini btn-success" @click="doApproveAvl(a)">Phê duyệt</button>
                <button
v-if="a.workflow_state === 'Approved' || a.workflow_state === 'Conditional'"
                        class="btn-mini btn-danger" @click="doSuspendAvl(a)">
Đình chỉ
</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="!filteredAvl.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có giấy phép nào phù hợp</p>
        <button v-if="activeChips.length > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-head">
          <h3>Cấp giấy phép cho nhà cung cấp</h3>
          <button class="btn-close" @click="showCreate = false">×</button>
        </div>
        <div class="modal-body">
          <label>Nhà cung cấp <span class="req">*</span>
            <input v-model="newAvl.supplier" type="text" placeholder="Chọn nhà cung cấp..." />
          </label>
          <label>Nhóm thiết bị <span class="req">*</span>
            <input v-model="newAvl.device_category" type="text" placeholder="Ví dụ: Chẩn đoán hình ảnh..." />
          </label>
          <label>Thời hạn hiệu lực (năm) <span class="req">*</span>
            <input v-model.number="newAvl.validity_years" type="number" min="1" max="3" />
          </label>
          <label>Hiệu lực từ ngày
            <input v-model="newAvl.valid_from" type="date" />
          </label>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" @click="showCreate = false">Huỷ</button>
          <button class="btn-primary" :disabled="!canCreate" @click="doCreate">Tạo giấy phép</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.actions-col { display: flex; gap: 0.5rem; }
.warn-text { color: #b45309; font-weight: 600; margin-left: 0.5rem; }
.btn-mini { padding: 0.3rem 0.6rem; font-size: 0.8rem; border-radius: 6px; border: 1px solid #cbd5e1; cursor: pointer; font: inherit; }
.btn-mini.btn-success { background: #059669; color: white; border-color: #059669; }
.btn-mini.btn-danger  { background: #dc2626; color: white; border-color: #dc2626; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; border-radius: 8px; width: 480px; max-width: 90vw; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid #e5e7eb; }
.modal-head h3 { margin: 0; }
.btn-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; }
.modal-body { padding: 1rem; }
.modal-body label { display: block; margin-bottom: 1rem; font-weight: 500; }
.modal-body input { display: block; width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; margin-top: 0.25rem; }
.modal-foot { padding: 1rem; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 0.5rem; }
.req { color: #ef4444; }
</style>
