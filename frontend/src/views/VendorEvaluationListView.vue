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
  { value: '',              label: 'Tất cả trạng thái' },
  { value: 'Draft',         label: 'Nháp' },
  { value: 'In Progress',   label: 'Đang đánh giá' },
  { value: 'Tech Reviewed', label: 'Đã duyệt kỹ thuật' },
  { value: 'Approved',      label: 'Đã phê duyệt' },
  { value: 'Cancelled',     label: 'Đã hủy' },
]


const statTotal      = computed(() => store.veTotal)
const statInProgress = computed(() =>
  store.veList.filter(v => ['In Progress', 'Tech Reviewed'].includes(v.status)).length,
)
const statApproved   = computed(() =>
  store.veList.filter(v => v.status === 'Approved').length,
)

function applyFilters() {
  store.fetchVeList({ status: filters.value.status || undefined, year: filters.value.year || undefined })
}

function resetFilters() {
  filters.value = { status: '', year: '' }
  store.fetchVeList()
}

onMounted(() => store.fetchVeList({ year: filters.value.year }))
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-03</p>
        <h1 class="text-2xl font-bold text-slate-900">Đánh giá Nhà cung cấp</h1>
        <p class="text-sm text-slate-500 mt-1">Quản lý phiếu đánh giá và chấm điểm nhà cung cấp</p>
      </div>
      <router-link to="/planning/vendor-evaluations/new" class="btn-primary shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo VE mới
      </router-link>
    </div>

    <!-- Stats bar -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="card animate-slide-up" style="animation-delay:0ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Tổng VE</p>
        <p class="text-2xl font-bold text-slate-900">{{ statTotal }}</p>
      </div>
      <div class="card animate-slide-up" style="animation-delay:40ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Đang đánh giá</p>
        <p class="text-2xl font-bold text-amber-600">{{ statInProgress }}</p>
      </div>
      <div class="card animate-slide-up" style="animation-delay:80ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Đã phê duyệt</p>
        <p class="text-2xl font-bold text-emerald-600">{{ statApproved }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="card mb-6 animate-slide-up" style="animation-delay:100ms">
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
          <button class="btn-primary" :disabled="store.veLoading" @click="applyFilters">
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
    <SkeletonLoader v-if="store.veLoading" variant="table" :rows="6" />

    <!-- Error -->
    <div v-else-if="store.veError" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.veError }}</span>
      <button class="text-xs font-semibold underline hover:no-underline" @click="applyFilters">Thử lại</button>
    </div>

    <!-- Table -->
    <template v-else>
      <div class="table-wrapper animate-slide-up" style="animation-delay:120ms">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã VE</th>
              <th class="table-header">Kế hoạch mua sắm</th>
              <th class="table-header">Ngày đánh giá</th>
              <th class="table-header">NCC đề xuất</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-slate-100">
            <tr
              v-for="(item, i) in store.veList"
              :key="item.name"
              class="table-row cursor-pointer animate-fade-in"
              :style="`animation-delay: ${i * 30}ms`"
              @click="router.push(`/planning/vendor-evaluations/${item.name}`)"
            >
              <td class="table-cell">
                <span class="font-mono text-[12px] font-semibold text-brand-600">{{ item.name }}</span>
              </td>
              <td class="table-cell">
                <span class="text-sm text-slate-700 font-mono">{{ item.linked_plan }}</span>
              </td>
              <td class="table-cell">
                <span class="text-sm text-slate-600">{{ formatDate(item.evaluation_date) }}</span>
              </td>
              <td class="table-cell">
                <span v-if="item.recommended_vendor" class="text-sm font-medium text-emerald-700">
                  {{ item.recommended_vendor }}
                </span>
                <span v-else class="text-slate-400 text-sm">—</span>
              </td>
              <td class="px-5 py-3.5"><StatusBadge :state="item.status" /></td>
            </tr>
            <tr v-if="!store.veList.length">
              <td colspan="6" class="px-5 py-16 text-center">
                <div class="flex flex-col items-center gap-3 text-slate-400">
                  <svg class="w-10 h-10 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p class="text-sm">Không tìm thấy phiếu đánh giá nào phù hợp.</p>
                  <router-link to="/planning/vendor-evaluations/new" class="btn-primary text-xs">
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
