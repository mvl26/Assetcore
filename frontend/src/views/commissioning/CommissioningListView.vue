<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCommissioningStore } from '@/stores/imm04'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import { formatDate } from '@/utils/docUtils'
import type { CommissioningFilters, WorkflowState } from '@/types/imm04'

const router = useRouter()
const route  = useRoute()
const store  = useCommissioningStore()

const showFilters = ref(false)
const filters = ref<CommissioningFilters>({
  workflow_state: (route.query.workflow_state as WorkflowState) || '',
  vendor_serial_no: '',
  master_item:  '',
  clinical_dept: '',
})

const WORKFLOW_STATES: { value: WorkflowState | ''; label: string }[] = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Draft', label: 'Nháp' },
  { value: 'Pending_Doc_Verify', label: 'Chờ kiểm tra tài liệu' },
  { value: 'To_Be_Installed', label: 'Chờ lắp đặt' },
  { value: 'Installing', label: 'Đang lắp đặt' },
  { value: 'Identification', label: 'Nhận dạng' },
  { value: 'Initial_Inspection', label: 'Kiểm tra ban đầu' },
  { value: 'Clinical_Hold', label: 'Tạm giữ lâm sàng' },
  { value: 'Re_Inspection', label: 'Kiểm tra lại' },
  { value: 'Pending_Release', label: 'Chờ phê duyệt' },
  { value: 'Clinical_Release', label: 'Phát hành lâm sàng' },
  { value: 'Return_To_Vendor', label: 'Trả nhà cung cấp' },
]

interface Chip { key: 'workflow_state' | 'vendor_serial_no' | 'master_item' | 'clinical_dept'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (filters.value.workflow_state) {
    const s = WORKFLOW_STATES.find(x => x.value === filters.value.workflow_state)
    chips.push({ key: 'workflow_state', label: s?.label ?? filters.value.workflow_state })
  }
  if (filters.value.vendor_serial_no?.trim()) chips.push({ key: 'vendor_serial_no', label: `Serial: ${filters.value.vendor_serial_no.trim()}` })
  if (filters.value.master_item?.trim()) chips.push({ key: 'master_item', label: `Model: ${filters.value.master_item.trim()}` })
  if (filters.value.clinical_dept?.trim()) chips.push({ key: 'clinical_dept', label: `Khoa: ${filters.value.clinical_dept.trim()}` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  (filters.value as Record<string, unknown>)[key] = ''
  applyFilters()
}

function cleanFilters(): CommissioningFilters {
  const f: CommissioningFilters = {}
  if (filters.value.workflow_state)          f.workflow_state   = filters.value.workflow_state
  if (filters.value.vendor_serial_no?.trim()) f.vendor_serial_no = filters.value.vendor_serial_no.trim()
  if (filters.value.master_item?.trim())      f.master_item      = filters.value.master_item.trim()
  if (filters.value.clinical_dept?.trim())    f.clinical_dept    = filters.value.clinical_dept.trim()
  return f
}

function applyFilters() { store.fetchList(cleanFilters(), 1, store.pagination.page_size) }

function resetFilters() {
  filters.value = { workflow_state: '', vendor_serial_no: '', master_item: '', clinical_dept: '' }
  store.fetchList({}, 1)
}

function quickFilter(key: 'workflow_state' | 'clinical_dept', value: string) {
  if (!value) return
  if (key === 'workflow_state') filters.value.workflow_state = value as WorkflowState
  else if (key === 'clinical_dept') filters.value.clinical_dept = value
  showFilters.value = false
  applyFilters()
}

function goToPage(page: number) { store.fetchList(cleanFilters(), page, store.pagination.page_size) }

onMounted(() => store.fetchList(cleanFilters(), 1))

watch(() => route.query.workflow_state, (val) => {
  filters.value.workflow_state = (val as WorkflowState) || ''
  applyFilters()
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Phiếu Tiếp nhận và lắp đặt"
      :subtitle="`Tổng ${store.pagination.total} phiếu`"
      :breadcrumb="[{ label: 'IMM-04 · Tiếp nhận', to: '/commissioning' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <router-link to="/commissioning/new" class="btn-primary">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu mới
        </router-link>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      :show-search="false"
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.workflow_state" class="form-select" @change="applyFilters">
            <option v-for="s in WORKFLOW_STATES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Serial Number</label>
          <input v-model="filters.vendor_serial_no" class="form-input font-mono" placeholder="Nhập Serial..." @keyup.enter="applyFilters" />
        </div>
        <div class="form-group">
          <label class="form-label">Model Thiết bị</label>
          <input v-model="filters.master_item" class="form-input" placeholder="Tên model..." @keyup.enter="applyFilters" />
        </div>
        <div class="form-group">
          <label class="form-label">Khoa / Phòng</label>
          <input v-model="filters.clinical_dept" class="form-input" placeholder="Tên khoa..." @keyup.enter="applyFilters" />
        </div>
      </template>
    </ListFilterBar>

    <!-- Loading -->
    <SkeletonLoader v-if="store.listLoading" variant="table" :rows="8" />

    <!-- Error -->
    <div v-else-if="store.error" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline hover:no-underline" @click="store.refreshList">Thử lại</button>
    </div>

    <!-- Table -->
    <template v-else>
      <div class="table-wrapper animate-slide-up" style="animation-delay: 80ms">
        <!-- Info row -->
        <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
          <span>Hiển thị <strong class="text-slate-700">{{ store.list.length }}</strong> / {{ store.pagination.total }} phiếu</span>
          <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
        </div>
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Phiếu</th>
              <th class="table-header">Model Thiết bị</th>
              <th class="table-header">Nhà cung cấp</th>
              <th class="table-header">Khoa nhận</th>
              <th class="table-header">Serial NSX</th>
              <th class="table-header">Ngày hẹn</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header">Tài sản</th>
              <th class="table-header">Cập nhật</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-slate-100">
            <tr
              v-for="(item, i) in store.list"
              :key="item.name"
              class="table-row animate-fade-in"
              :style="`animation-delay: ${i * 30}ms`"
              @click="router.push(`/commissioning/${item.name}`)"
            >
              <td class="table-cell">
                <span class="font-mono text-[12px] font-semibold text-brand-600">{{ item.name }}</span>
              </td>
              <td class="table-cell max-w-40">
                <div class="text-slate-700 truncate">{{ item.master_item_name || item.master_item || '—' }}</div>
                <div v-if="item.master_item && item.master_item_name" class="text-xs text-slate-400 font-mono truncate">{{ item.master_item }}</div>
              </td>
              <td class="table-cell max-w-32">
                <div class="text-slate-700 truncate">{{ item.vendor_name || item.vendor || '—' }}</div>
              </td>
              <td class="table-cell">
                <button
                  class="text-slate-700 hover:underline decoration-dotted underline-offset-2 text-left"
                  :title="`Lọc: ${item.clinical_dept_name || item.clinical_dept}`"
                  @click.stop="quickFilter('clinical_dept', item.clinical_dept || '')"
                >
{{ item.clinical_dept_name || item.clinical_dept || '—' }}
</button>
                <div v-if="item.clinical_dept && item.clinical_dept_name" class="text-xs text-slate-400">{{ item.clinical_dept }}</div>
              </td>
              <td class="table-cell">
                <span class="font-mono text-xs text-slate-400">{{ item.vendor_serial_no || '—' }}</span>
              </td>
              <td class="table-cell text-slate-600 text-sm">
                {{ formatDate(item.expected_installation_date) }}
              </td>
              <td class="px-5 py-3.5">
                <button
                  class="transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50 rounded"
                  :title="`Lọc: ${item.workflow_state}`"
                  @click.stop="quickFilter('workflow_state', item.workflow_state || '')"
                >
                  <StatusBadge :state="item.workflow_state" />
                </button>
              </td>
              <td class="table-cell">
                <router-link
                  v-if="item.final_asset"
                  :to="`/assets/${item.final_asset}`"
                  class="font-mono text-[11px] text-blue-600 hover:underline"
                  @click.stop
                >
{{ item.final_asset }}
</router-link>
                <span v-else class="text-slate-300 text-xs">—</span>
              </td>
              <td class="table-cell text-slate-400 text-xs">{{ formatDate(item.modified) }}</td>
            </tr>
            <tr v-if="!store.list.length">
              <td colspan="9" class="px-5 py-16 text-center">
                <div class="flex flex-col items-center gap-3 text-slate-400">
                  <svg class="w-10 h-10 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p class="text-sm">Không tìm thấy phiếu nào phù hợp.</p>
                  <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
                    Xóa bộ lọc để xem tất cả
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </template>

    <BasePagination :pagination="store.pagination" @page-change="goToPage" />
</div>
</template>
