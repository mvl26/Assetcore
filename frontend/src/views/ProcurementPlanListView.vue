<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm02Store } from '@/stores/imm02'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const router = useRouter()
const store  = useImm02Store()

const filters = ref({ status: '', year: String(new Date().getFullYear()) })

const STATUS_OPTIONS = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Draft',        label: 'Nháp' },
  { value: 'Under Review', label: 'Đang xét duyệt' },
  { value: 'Approved',     label: 'Đã duyệt' },
  { value: 'Budget Locked',label: 'Khóa ngân sách' },
]

function formatBudget(val: number | null | undefined): string {
  if (!val) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(val)
}

function budgetUsedPct(doc: { allocated_budget: number; approved_budget: number }): number {
  if (!doc.approved_budget) return 0
  return Math.min(100, Math.round((doc.allocated_budget / doc.approved_budget) * 100))
}

function applyFilters() { store.fetchList(cleanFilters(), 1, store.pagination.page_size) }
function resetFilters()  { filters.value = { status: '', year: '' }; store.fetchList({}, 1) }
function goToPage(p: number) { store.fetchList(cleanFilters(), p, store.pagination.page_size) }

function cleanFilters() {
  const f: Record<string, string> = {}
  if (filters.value.status) f.status = filters.value.status
  if (filters.value.year?.trim()) f.year = filters.value.year.trim()
  return f
}

const hasFilters = () => !!(filters.value.status || filters.value.year)

onMounted(() => store.fetchList(cleanFilters(), 1))
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-02</p>
        <h1 class="text-2xl font-bold text-slate-900">Kế hoạch Mua sắm</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total }}</strong> kế hoạch
        </p>
      </div>
      <router-link to="/planning/procurement-plans/new" class="btn-primary shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo kế hoạch
      </router-link>
    </div>

    <!-- Filters -->
    <div class="card mb-6 animate-slide-up">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.status" class="form-select">
            <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Năm</label>
          <input v-model="filters.year" type="text" class="form-input" placeholder="vd: 2026"
                 @keyup.enter="applyFilters" />
        </div>
      </div>
      <div class="flex items-center gap-2.5 mt-4 pt-4 border-t border-slate-100">
        <button class="btn-primary" :disabled="store.listLoading" @click="applyFilters">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Tìm kiếm
        </button>
        <button v-if="hasFilters()" class="btn-ghost" @click="resetFilters">Xóa bộ lọc</button>
      </div>
    </div>

    <!-- Loading -->
    <SkeletonLoader v-if="store.listLoading" variant="table" :rows="6" />

    <!-- Error -->
    <div v-else-if="store.error" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline" @click="store.refreshList">Thử lại</button>
    </div>

    <!-- Table -->
    <template v-else>
      <div class="table-wrapper animate-slide-up" style="animation-delay: 80ms">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Kế hoạch</th>
              <th class="table-header">Năm</th>
              <th class="table-header text-right">Ngân sách duyệt</th>
              <th class="table-header text-right">Đã phân bổ</th>
              <th class="table-header">Sử dụng</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-slate-100">
            <tr
              v-for="(item, i) in store.list"
              :key="item.name"
              class="table-row animate-fade-in"
              :style="`animation-delay: ${i * 30}ms`"
              @click="router.push(`/planning/procurement-plans/${item.name}`)"
            >
              <td class="table-cell">
                <span class="font-mono text-[12px] font-semibold text-brand-600">{{ item.name }}</span>
              </td>
              <td class="table-cell text-slate-700 font-medium">{{ item.plan_year }}</td>
              <td class="table-cell text-right text-slate-700">{{ formatBudget(item.approved_budget) }}</td>
              <td class="table-cell text-right text-slate-700">{{ formatBudget(item.allocated_budget) }}</td>
              <td class="table-cell min-w-[120px]">
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all duration-500"
                      :style="{
                        width: `${budgetUsedPct(item)}%`,
                        background: budgetUsedPct(item) > 90 ? '#ef4444' : budgetUsedPct(item) > 70 ? '#f59e0b' : '#10b981',
                      }"
                    />
                  </div>
                  <span class="text-xs text-slate-500 shrink-0">{{ budgetUsedPct(item) }}%</span>
                </div>
              </td>
              <td class="px-5 py-4"><StatusBadge :state="item.status" /></td>
            </tr>
            <tr v-if="!store.list.length">
              <td colspan="6" class="px-5 py-16 text-center">
                <div class="flex flex-col items-center gap-3 text-slate-400">
                  <svg class="w-10 h-10 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p class="text-sm">Không có kế hoạch nào phù hợp.</p>
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
        </p>
        <div class="flex items-center gap-1">
          <button class="page-btn-default"
                  :disabled="store.pagination.page <= 1 || store.listLoading"
                  @click="goToPage(store.pagination.page - 1)">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button v-for="p in store.pagination.total_pages" :key="p"
                  :class="p === store.pagination.page ? 'page-btn-active' : 'page-btn-default'"
                  :disabled="store.listLoading" @click="goToPage(p)">{{ p }}</button>
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
