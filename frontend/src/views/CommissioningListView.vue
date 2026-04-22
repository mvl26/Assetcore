<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCommissioningStore } from '@/stores/commissioning'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { formatDate } from '@/utils/docUtils'
import type { CommissioningFilters, WorkflowState } from '@/types/imm04'

const router = useRouter()
const route  = useRoute()
const store  = useCommissioningStore()

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

function cleanFilters(): CommissioningFilters {
  const f: CommissioningFilters = {}
  if (filters.value.workflow_state)     f.workflow_state   = filters.value.workflow_state
  if (filters.value.vendor_serial_no?.trim()) f.vendor_serial_no = filters.value.vendor_serial_no.trim()
  if (filters.value.master_item?.trim())      f.master_item      = filters.value.master_item.trim()
  if (filters.value.clinical_dept?.trim())    f.clinical_dept    = filters.value.clinical_dept.trim()
  return f
}

const hasFilters = () =>
  !!(filters.value.workflow_state || filters.value.vendor_serial_no ||
     filters.value.master_item    || filters.value.clinical_dept)

function applyFilters() { store.fetchList(cleanFilters(), 1, store.pagination.page_size) }
function resetFilters()  {
  filters.value = { workflow_state: '', vendor_serial_no: '', master_item: '', clinical_dept: '' }
  store.fetchList({}, 1)
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

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-04</p>
        <h1 class="text-2xl font-bold text-slate-900">Danh sách Phiếu Lắp đặt</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total }}</strong> phiếu
        </p>
      </div>
      <router-link to="/commissioning/new" class="btn-primary shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo phiếu mới
      </router-link>
    </div>

    <!-- Filters -->
    <div class="card mb-6 animate-slide-up">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="form-group">
          <label for="f-state" class="form-label">Trạng thái</label>
          <select id="f-state" v-model="filters.workflow_state" class="form-select">
            <option v-for="s in WORKFLOW_STATES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label for="f-serial" class="form-label">Serial Number</label>
          <input id="f-serial" v-model="filters.vendor_serial_no" type="text" class="form-input font-mono"
                 placeholder="Nhập Serial..." @keyup.enter="applyFilters" />
        </div>
        <div class="form-group">
          <label for="f-model" class="form-label">Model Thiết bị</label>
          <input id="f-model" v-model="filters.master_item" type="text" class="form-input"
                 placeholder="Tên model..." @keyup.enter="applyFilters" />
        </div>
        <div class="form-group">
          <label for="f-dept" class="form-label">Khoa / Phòng</label>
          <input id="f-dept" v-model="filters.clinical_dept" type="text" class="form-input"
                 placeholder="Tên khoa..." @keyup.enter="applyFilters" />
        </div>
      </div>
      <div class="flex items-center gap-2.5 mt-4 pt-4 border-t border-slate-100">
        <button class="btn-primary" :disabled="store.listLoading" @click="applyFilters">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Tìm kiếm
        </button>
        <button v-if="hasFilters()" class="btn-ghost text-slate-500" @click="resetFilters">
          Xóa bộ lọc
        </button>
      </div>
    </div>

    <!-- Loading -->
    <SkeletonLoader v-if="store.listLoading" variant="table" :rows="8" />

    <!-- Error -->
    <div v-else-if="store.error" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline hover:no-underline"
              @click="store.refreshList">Thử lại</button>
    </div>

    <!-- Table -->
    <template v-else>
      <div class="table-wrapper animate-slide-up" style="animation-delay: 80ms">
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
                <div class="text-slate-700">{{ item.clinical_dept_name || item.clinical_dept || '—' }}</div>
                <div v-if="item.clinical_dept && item.clinical_dept_name" class="text-xs text-slate-400">{{ item.clinical_dept }}</div>
              </td>
              <td class="table-cell">
                <span class="font-mono text-xs text-slate-400">{{ item.vendor_serial_no || '—' }}</span>
              </td>
              <td class="table-cell text-slate-600 text-sm">
                {{ formatDate(item.expected_installation_date) }}
              </td>
              <td class="px-5 py-3.5"><StatusBadge :state="item.workflow_state" /></td>
              <td class="table-cell text-slate-400 text-xs">{{ formatDate(item.modified) }}</td>
            </tr>
            <tr v-if="!store.list.length">
              <td colspan="8" class="px-5 py-16 text-center">
                <div class="flex flex-col items-center gap-3 text-slate-400">
                  <svg class="w-10 h-10 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p class="text-sm">Không tìm thấy phiếu nào phù hợp.</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="store.pagination.total_pages > 1"
           class="flex items-center justify-between mt-5 px-1">
        <p class="text-xs text-slate-500">
          Trang <strong>{{ store.pagination.page }}</strong> / {{ store.pagination.total_pages }}
          <span class="ml-1 text-slate-400">({{ store.pagination.total }} bản ghi)</span>
        </p>
        <div class="flex items-center gap-1">
          <button
            class="page-btn-default"
            :disabled="store.pagination.page <= 1 || store.listLoading"
            @click="goToPage(store.pagination.page - 1)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            v-for="p in store.pagination.total_pages"
            :key="p"
            :class="p === store.pagination.page ? 'page-btn-active' : 'page-btn-default'"
            :disabled="store.listLoading"
            @click="goToPage(p)"
          >{{ p }}</button>
          <button
            class="page-btn-default"
            :disabled="store.pagination.page >= store.pagination.total_pages || store.listLoading"
            @click="goToPage(store.pagination.page + 1)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </template>

  </div>
</template>
