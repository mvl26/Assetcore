<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { formatDate } from '@/utils/docUtils'

const router = useRouter()
const store  = useImm03Store()

const filters = ref({ status: '', year: String(new Date().getFullYear()) })

const STATUS_OPTIONS = [
  { value: '',             label: 'Tất cả trạng thái' },
  { value: 'Draft',        label: 'Nháp' },
  { value: 'Under Review', label: 'Chờ duyệt' },
  { value: 'Approved',     label: 'Đã duyệt' },
  { value: 'Released',     label: 'Đã phát hành' },
  { value: 'Fulfilled',    label: 'Đã hoàn thành' },
  { value: 'Cancelled',    label: 'Đã hủy' },
]

function formatBudget(val: number | null | undefined): string {
  if (!val) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(val)
}

const statTotal      = computed(() => store.porTotal)
const statPending    = computed(() => store.porList.filter(p => p.status === 'Under Review').length)
const statReleased   = computed(() => store.porList.filter(p => p.status === 'Released').length)
const statReleasedValue = computed(() =>
  store.porList
    .filter(p => p.status === 'Released')
    .reduce((sum, p) => sum + (p.total_amount ?? 0), 0),
)

function applyFilters() {
  store.fetchPorList({ status: filters.value.status || undefined, year: filters.value.year || undefined })
}

function resetFilters() {
  filters.value = { status: '', year: '' }
  store.fetchPorList()
}

onMounted(() => store.fetchPorList({ year: filters.value.year }))
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-03</p>
        <h1 class="text-2xl font-bold text-slate-900">Yêu cầu Mua sắm (POR)</h1>
        <p class="text-sm text-slate-500 mt-1">Quản lý phiếu yêu cầu mua sắm thiết bị y tế</p>
      </div>
      <router-link to="/planning/purchase-order-requests/new" class="btn-primary shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo POR mới
      </router-link>
    </div>

    <!-- Stats bar -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
      <div class="card animate-slide-up" style="animation-delay:0ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Tổng POR</p>
        <p class="text-2xl font-bold text-slate-900">{{ statTotal }}</p>
      </div>
      <div class="card animate-slide-up" style="animation-delay:30ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Chờ duyệt</p>
        <p class="text-2xl font-bold text-amber-600">{{ statPending }}</p>
      </div>
      <div class="card animate-slide-up" style="animation-delay:60ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Đã phát hành</p>
        <p class="text-2xl font-bold text-blue-600">{{ statReleased }}</p>
      </div>
      <div class="card animate-slide-up" style="animation-delay:90ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Giá trị phát hành</p>
        <p class="text-lg font-bold text-emerald-700 truncate">{{ formatBudget(statReleasedValue) }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="card mb-6 animate-slide-up" style="animation-delay:110ms">
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.status" class="form-select">
            <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Năm</label>
          <input v-model="filters.year" type="text" class="form-input"
                 placeholder="vd: 2026" @keyup.enter="applyFilters" />
        </div>
        <div class="flex items-end gap-2">
          <button class="btn-primary" :disabled="store.loading" @click="applyFilters">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Tìm kiếm
          </button>
          <button class="btn-ghost text-slate-500" @click="resetFilters">Xóa lọc</button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <SkeletonLoader v-if="store.loading" variant="table" :rows="6" />

    <!-- Error -->
    <div v-else-if="store.error" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline hover:no-underline" @click="applyFilters">Thử lại</button>
    </div>

    <!-- Table -->
    <template v-else>
      <div class="table-wrapper animate-slide-up" style="animation-delay:130ms">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã POR</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Nhà cung cấp</th>
              <th class="table-header text-right">Tổng giá trị</th>
              <th class="table-header text-center">Cần GĐ?</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header">Ngày phát hành</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-slate-100">
            <tr
              v-for="(item, i) in store.porList"
              :key="item.name"
              class="table-row cursor-pointer animate-fade-in"
              :style="`animation-delay: ${i * 30}ms`"
              @click="router.push(`/planning/purchase-order-requests/${item.name}`)"
            >
              <td class="table-cell">
                <span class="font-mono text-[12px] font-semibold text-brand-600">{{ item.name }}</span>
              </td>
              <td class="table-cell max-w-48">
                <p class="text-sm text-slate-700 truncate">{{ item.equipment_description }}</p>
              </td>
              <td class="table-cell">
                <p class="text-sm text-slate-700">{{ item.vendor_name || item.vendor }}</p>
              </td>
              <td class="table-cell text-right">
                <span class="font-semibold text-slate-800 text-sm">{{ formatBudget(item.total_amount) }}</span>
              </td>
              <td class="table-cell text-center">
                <span v-if="item.requires_director_approval"
                      class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-700">
                  ⚠ GĐ
                </span>
                <span v-else class="text-slate-300 text-sm">—</span>
              </td>
              <td class="px-5 py-3.5"><StatusBadge :state="item.status" /></td>
              <td class="table-cell text-slate-500 text-sm">
                {{ item.release_date ? formatDate(item.release_date) : '—' }}
              </td>
            </tr>
            <tr v-if="!store.porList.length">
              <td colspan="7" class="px-5 py-16 text-center">
                <div class="flex flex-col items-center gap-3 text-slate-400">
                  <svg class="w-10 h-10 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <p class="text-sm">Không tìm thấy phiếu mua sắm nào.</p>
                  <router-link to="/planning/purchase-order-requests/new" class="btn-primary text-xs">
                    Tạo phiếu đầu tiên
                  </router-link>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

  </div>
</template>
