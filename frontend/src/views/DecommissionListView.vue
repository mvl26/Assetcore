<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useImm13Store } from '@/stores/imm13'
import { useRouter } from 'vue-router'

const store = useImm13Store()
const router = useRouter()

const workflowStateFilter = ref('')
const assetFilter = ref('')

const WORKFLOW_STATES = [
  { value: 'Draft', label: 'Nháp' },
  { value: 'Pending Tech Review', label: 'Chờ đánh giá KT' },
  { value: 'Under Replacement Review', label: 'Đánh giá thay thế' },
  { value: 'Approved for Transfer', label: 'Đã duyệt điều chuyển' },
  { value: 'Transfer In Progress', label: 'Đang điều chuyển' },
  { value: 'Transferred', label: 'Đã điều chuyển' },
  { value: 'Pending Decommission', label: 'Chờ ngừng sử dụng' },
  { value: 'Completed', label: 'Hoàn thành' },
  { value: 'Cancelled', label: 'Đã hủy' },
]

const SUSPENSION_REASONS: Record<string, string> = {
  End_of_Life: 'Hết tuổi thọ',
  Cannot_Repair: 'Không thể sửa chữa',
  Regulatory: 'Yêu cầu pháp lý',
  Upgrade: 'Nâng cấp thiết bị',
  Transfer: 'Điều chuyển đơn vị',
  Other: 'Khác',
}

const OUTCOME_LABELS: Record<string, string> = {
  Suspend: 'Tạm ngừng',
  Transfer: 'Điều chuyển',
  Retire: 'Thanh lý',
}

function stateBadgeClass(state: string): string {
  const map: Record<string, string> = {
    'Draft': 'bg-slate-100 text-slate-600',
    'Pending Tech Review': 'bg-blue-100 text-blue-700',
    'Under Replacement Review': 'bg-yellow-100 text-yellow-700',
    'Approved for Transfer': 'bg-green-100 text-green-700',
    'Transfer In Progress': 'bg-orange-100 text-orange-700',
    'Transferred': 'bg-emerald-100 text-emerald-700',
    'Pending Decommission': 'bg-red-100 text-red-700',
    'Completed': 'bg-green-200 text-green-800',
    'Cancelled': 'bg-slate-100 text-slate-500',
  }
  return map[state] ?? 'bg-slate-100 text-slate-600'
}

function applyFilters() {
  store.fetchRequests(workflowStateFilter.value, assetFilter.value)
}

function resetFilters() {
  workflowStateFilter.value = ''
  assetFilter.value = ''
  store.fetchRequests()
}

const totalPages = computed(() => Math.ceil(store.pagination.total / store.pagination.page_size))

onMounted(() => store.fetchRequests())
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-5">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-13 · Ngừng sử dụng & Điều chuyển</p>
        <h1 class="text-2xl font-bold text-slate-900">Phiếu Ngừng sử dụng & Điều chuyển</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total }}</strong> phiếu
        </p>
      </div>
      <button class="btn-primary shrink-0" @click="router.push('/decommission/create')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo phiếu
      </button>
    </div>

    <!-- Filter bar -->
    <div class="card mb-5 p-4">
      <div class="flex flex-wrap gap-3">
        <input
          v-model="assetFilter"
          placeholder="Tìm theo mã thiết bị..."
          class="form-input flex-1 min-w-48"
          @keyup.enter="applyFilters"
        />
        <select v-model="workflowStateFilter" class="form-select w-56">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in WORKFLOW_STATES" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <button class="btn-primary px-4" @click="applyFilters">Tìm kiếm</button>
        <button class="btn-ghost" @click="resetFilters">Đặt lại</button>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="store.loading" class="card">
      <div v-for="i in 6" :key="i" class="flex gap-4 py-3 border-b border-slate-100 last:border-0 animate-pulse px-4">
        <div class="h-4 bg-slate-100 rounded w-32" />
        <div class="h-4 bg-slate-100 rounded flex-1" />
        <div class="h-4 bg-slate-100 rounded w-24" />
        <div class="h-4 bg-slate-100 rounded w-20" />
        <div class="h-4 bg-slate-100 rounded w-28" />
      </div>
    </div>

    <!-- Table -->
    <div v-else class="table-wrapper">
      <table class="min-w-full divide-y divide-slate-100">
        <thead>
          <tr>
            <th class="table-header">Mã phiếu</th>
            <th class="table-header">Thiết bị</th>
            <th class="table-header">Lý do ngừng</th>
            <th class="table-header">Kết quả</th>
            <th class="table-header">Trạng thái</th>
            <th class="table-header">Ngày tạo</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr
            v-for="req in store.requests"
            :key="req.name"
            class="hover:bg-slate-50 cursor-pointer transition-colors"
            @click="router.push(`/decommission/${req.name}`)"
          >
            <td class="table-cell">
              <div class="font-mono text-sm font-semibold text-blue-700">{{ req.name }}</div>
            </td>
            <td class="table-cell">
              <div class="font-medium text-slate-900">{{ req.asset_name || req.asset }}</div>
              <div class="text-xs text-slate-400 font-mono mt-0.5">{{ req.asset }}</div>
            </td>
            <td class="table-cell text-sm text-slate-600">
              {{ SUSPENSION_REASONS[req.suspension_reason] ?? req.suspension_reason ?? '—' }}
            </td>
            <td class="table-cell">
              <span v-if="req.outcome" class="text-sm text-slate-700">
                {{ OUTCOME_LABELS[req.outcome] ?? req.outcome }}
              </span>
              <span v-else class="text-slate-400 text-sm">—</span>
            </td>
            <td class="table-cell">
              <span :class="['px-2.5 py-1 rounded-full text-xs font-medium', stateBadgeClass(req.workflow_state)]">
                {{ WORKFLOW_STATES.find(s => s.value === req.workflow_state)?.label ?? req.workflow_state }}
              </span>
            </td>
            <td class="table-cell text-sm text-slate-500">
              {{ req.creation ? req.creation.slice(0, 10) : '—' }}
            </td>
          </tr>
          <tr v-if="store.requests.length === 0">
            <td colspan="6" class="py-16 text-center text-slate-400">
              <p class="text-sm font-medium">Không tìm thấy phiếu nào</p>
              <button class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
                Xóa bộ lọc để xem tất cả
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex justify-center mt-5 gap-1">
      <button
        v-for="p in totalPages"
        :key="p"
        :class="['px-3 py-1.5 rounded-lg text-sm border transition-colors font-medium',
          p === store.pagination.page
            ? 'bg-blue-600 text-white border-blue-600'
            : 'border-slate-300 text-slate-600 hover:bg-slate-50']"
        @click="store.fetchRequests(workflowStateFilter, assetFilter, p)"
      >{{ p }}</button>
    </div>
  </div>
</template>
