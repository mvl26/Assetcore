<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCommissioningStore } from '@/stores/commissioning'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { formatDate } from '@/utils/docUtils'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { CommissioningFilters, WorkflowState } from '@/types/imm04'

const router = useRouter()
const route = useRoute()
const store = useCommissioningStore()

// ─── Filters ─────────────────────────────────────────────────────────────────

const filters = ref<CommissioningFilters>({
  workflow_state: (route.query.workflow_state as WorkflowState) || '',
  vendor_serial_no: '',
  master_item: '',
  clinical_dept: '',
})

const WORKFLOW_STATES: { value: WorkflowState | ''; label: string }[] = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Draft', label: 'Nháp' },
  { value: 'Identification', label: 'Nhận dạng' },
  { value: 'Installing', label: 'Đang lắp đặt' },
  { value: 'Initial_Inspection', label: 'Kiểm tra lần đầu' },
  { value: 'Clinical_Hold', label: 'Tạm giữ lâm sàng' },
  { value: 'Re_Inspection', label: 'Kiểm tra lại' },
  { value: 'Pending_Release', label: 'Chờ phê duyệt' },
  { value: 'Clinical_Release', label: 'Phát hành lâm sàng' },
  { value: 'Return_To_Vendor', label: 'Trả lại nhà cung cấp' },
]

// ─── Pagination ───────────────────────────────────────────────────────────────

function goToPage(page: number) {
  store.fetchList(cleanFilters(), page, store.pagination.page_size)
}

function cleanFilters(): CommissioningFilters {
  const f: CommissioningFilters = {}
  if (filters.value.workflow_state) f.workflow_state = filters.value.workflow_state
  if (filters.value.vendor_serial_no?.trim()) f.vendor_serial_no = filters.value.vendor_serial_no.trim()
  if (filters.value.master_item?.trim()) f.master_item = filters.value.master_item.trim()
  if (filters.value.clinical_dept?.trim()) f.clinical_dept = filters.value.clinical_dept.trim()
  return f
}

function applyFilters() {
  store.fetchList(cleanFilters(), 1, store.pagination.page_size)
}

function resetFilters() {
  filters.value = { workflow_state: '', vendor_serial_no: '', master_item: '', clinical_dept: '' }
  store.fetchList({}, 1)
}

function goToDetail(name: string) {
  router.push(`/commissioning/${name}`)
}

// ─── Init ─────────────────────────────────────────────────────────────────────

onMounted(() => {
  store.fetchList(cleanFilters(), 1)
})

watch(
  () => route.query.workflow_state,
  (val) => {
    filters.value.workflow_state = (val as WorkflowState) || ''
    applyFilters()
  },
)
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Danh sách Phiếu Commissioning</h1>
        <p class="text-sm text-gray-500 mt-1">
          Tổng: <strong>{{ store.pagination.total }}</strong> phiếu
        </p>
      </div>
      <router-link to="/commissioning/new" class="btn-primary px-4 py-2 text-sm">
        + Tạo phiếu mới
      </router-link>
    </div>

    <!-- Filters -->
    <div class="card mb-6">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.workflow_state" class="form-select">
            <option v-for="s in WORKFLOW_STATES" :key="s.value" :value="s.value">
              {{ s.label }}
            </option>
          </select>
        </div>
        <div>
          <label class="form-label">Serial Number</label>
          <input
            v-model="filters.vendor_serial_no"
            type="text"
            class="form-input font-mono"
            placeholder="Nhập Serial..."
            @keyup.enter="applyFilters"
          />
        </div>
        <div>
          <label class="form-label">Model Thiết bị</label>
          <input
            v-model="filters.master_item"
            type="text"
            class="form-input"
            placeholder="Tên model..."
            @keyup.enter="applyFilters"
          />
        </div>
        <div>
          <label class="form-label">Khoa / Phòng</label>
          <input
            v-model="filters.clinical_dept"
            type="text"
            class="form-input"
            placeholder="Tên khoa..."
            @keyup.enter="applyFilters"
          />
        </div>
      </div>
      <div class="flex gap-3 mt-4">
        <button class="btn-primary" :disabled="store.listLoading" @click="applyFilters">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Tìm kiếm
        </button>
        <button class="btn-secondary" @click="resetFilters">Xóa bộ lọc</button>
      </div>
    </div>

    <!-- Loading -->
    <LoadingSpinner v-if="store.listLoading" size="lg" label="Đang tải danh sách..." class="py-16" />

    <!-- Error -->
    <div v-else-if="store.error" class="card text-center py-12">
      <p class="text-red-600 mb-4">{{ store.error }}</p>
      <button class="btn-primary" @click="store.refreshList">Thử lại</button>
    </div>

    <!-- Table -->
    <template v-else>
      <div class="card p-0 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
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
            <tbody class="bg-white divide-y divide-gray-100">
              <tr
                v-for="item in store.list"
                :key="item.name"
                class="table-row cursor-pointer"
                @click="goToDetail(item.name)"
              >
                <td class="table-cell">
                  <span class="font-mono text-blue-600 hover:underline text-sm">{{ item.name }}</span>
                </td>
                <td class="table-cell max-w-40 truncate">{{ item.master_item }}</td>
                <td class="table-cell max-w-32 truncate">{{ item.vendor }}</td>
                <td class="table-cell">{{ item.clinical_dept }}</td>
                <td class="table-cell font-mono text-xs">{{ item.vendor_serial_no || '—' }}</td>
                <td class="table-cell text-sm">
                  {{ formatDate(item.expected_installation_date) }}
                </td>
                <td class="px-6 py-4">
                  <StatusBadge :state="item.workflow_state" />
                </td>
                <td class="table-cell text-gray-500 text-xs">
                  {{ formatDate(item.modified) }}
                </td>
              </tr>

              <tr v-if="!store.list.length">
                <td colspan="8" class="px-6 py-16 text-center text-gray-400">
                  <svg class="w-10 h-10 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p class="text-sm">Không tìm thấy phiếu nào phù hợp.</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div
          v-if="store.pagination.total_pages > 1"
          class="px-6 py-4 border-t border-gray-200 flex items-center justify-between"
        >
          <p class="text-sm text-gray-500">
            Trang {{ store.pagination.page }} / {{ store.pagination.total_pages }}
            ({{ store.pagination.total }} bản ghi)
          </p>
          <div class="flex gap-2">
            <button
              class="btn-secondary px-3 py-1.5 text-sm"
              :disabled="store.pagination.page <= 1 || store.listLoading"
              @click="goToPage(store.pagination.page - 1)"
            >
              Trang trước
            </button>
            <button
              class="btn-secondary px-3 py-1.5 text-sm"
              :disabled="store.pagination.page >= store.pagination.total_pages || store.listLoading"
              @click="goToPage(store.pagination.page + 1)"
            >
              Trang sau
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
