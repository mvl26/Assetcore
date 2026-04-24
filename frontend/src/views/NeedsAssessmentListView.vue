<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm01Store } from '@/stores/imm01'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { formatDate } from '@/utils/docUtils'

const router = useRouter()
const store  = useImm01Store()

const filters = ref({ status: '', dept: '', year: String(new Date().getFullYear()) })

const STATUS_OPTIONS = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Draft',        label: 'Nháp' },
  { value: 'Submitted',    label: 'Đã nộp' },
  { value: 'Under Review', label: 'Đang xét duyệt' },
  { value: 'Approved',     label: 'Đã duyệt' },
  { value: 'Rejected',     label: 'Từ chối' },
  { value: 'Planned',      label: 'Đã lên kế hoạch' },
]

const PRIORITY_COLOR: Record<string, string> = {
  High:     'text-red-600 bg-red-50',
  Medium:   'text-amber-600 bg-amber-50',
  Low:      'text-slate-500 bg-slate-100',
  Critical: 'text-purple-600 bg-purple-50',
}

function cleanFilters() {
  const f: Record<string, string> = {}
  if (filters.value.status) f.status = filters.value.status
  if (filters.value.dept?.trim()) f.dept = filters.value.dept.trim()
  if (filters.value.year?.trim()) f.year = filters.value.year.trim()
  return f
}

const hasFilters = () => !!(filters.value.status || filters.value.dept || filters.value.year)

function applyFilters() { store.fetchList(cleanFilters(), 1, store.pagination.page_size) }
function resetFilters() {
  filters.value = { status: '', dept: '', year: '' }
  store.fetchList({}, 1)
}
function goToPage(p: number) { store.fetchList(cleanFilters(), p, store.pagination.page_size) }

function formatBudget(val: number | null | undefined): string {
  if (!val) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(val)
}

onMounted(() => store.fetchList(cleanFilters(), 1))
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-01</p>
        <h1 class="text-2xl font-bold text-slate-900">Đánh giá Nhu cầu</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total }}</strong> phiếu
        </p>
      </div>
      <router-link to="/planning/needs-assessments/new" class="btn-primary shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo phiếu mới
      </router-link>
    </div>

    <!-- Filters -->
    <div class="card mb-6 animate-slide-up">
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.status" class="form-select">
            <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Khoa / Phòng</label>
          <input v-model="filters.dept" type="text" class="form-input"
                 placeholder="Tên khoa..." @keyup.enter="applyFilters" />
        </div>
        <div class="form-group">
          <label class="form-label">Năm</label>
          <input v-model="filters.year" type="text" class="form-input"
                 placeholder="vd: 2026" @keyup.enter="applyFilters" />
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
      <button class="text-xs font-semibold underline hover:no-underline" @click="store.refreshList">
        Thử lại
      </button>
    </div>

    <!-- Table -->
    <template v-else>
      <div class="table-wrapper animate-slide-up" style="animation-delay: 80ms">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Phiếu</th>
              <th class="table-header">Loại thiết bị</th>
              <th class="table-header">Khoa đề xuất</th>
              <th class="table-header">SL</th>
              <th class="table-header">Ngân sách ước tính</th>
              <th class="table-header">Ưu tiên</th>
              <th class="table-header">Ngày đề xuất</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-slate-100">
            <tr
              v-for="(item, i) in store.list"
              :key="item.name"
              class="table-row animate-fade-in cursor-pointer"
              :style="`animation-delay: ${i * 30}ms`"
              @click="router.push(`/planning/needs-assessments/${item.name}`)"
            >
              <td class="table-cell">
                <span class="font-mono text-[12px] font-semibold text-brand-600">{{ item.name }}</span>
              </td>
              <td class="table-cell max-w-40">
                <div class="text-slate-700 truncate">{{ item.equipment_type }}</div>
              </td>
              <td class="table-cell">
                <div class="text-slate-700">{{ item.requesting_dept || '—' }}</div>
              </td>
              <td class="table-cell text-slate-600 text-sm text-right">
                {{ item.estimated_budget ? '' : '' }}{{ /* quantity not in list fields */ '' }}
              </td>
              <td class="table-cell text-slate-700 text-sm">
                {{ formatBudget(item.estimated_budget) }}
              </td>
              <td class="table-cell">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium"
                  :class="PRIORITY_COLOR[item.priority] ?? 'text-slate-500 bg-slate-100'"
                >
                  {{ item.priority }}
                </span>
              </td>
              <td class="table-cell text-slate-500 text-sm">{{ formatDate(item.request_date) }}</td>
              <td class="px-5 py-3.5"><StatusBadge :state="item.status" /></td>
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
          <button class="page-btn-default"
                  :disabled="store.pagination.page <= 1 || store.listLoading"
                  @click="goToPage(store.pagination.page - 1)">
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
          <button class="page-btn-default"
                  :disabled="store.pagination.page >= store.pagination.total_pages || store.listLoading"
                  @click="goToPage(store.pagination.page + 1)">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </template>

  </div>
</template>
