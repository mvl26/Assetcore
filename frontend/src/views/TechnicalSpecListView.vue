<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listTechnicalSpecs } from '@/api/imm03'
import type { TechnicalSpecListItem } from '@/api/imm03'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { formatDate } from '@/utils/docUtils'

const router = useRouter()

const items      = ref<TechnicalSpecListItem[]>([])
const loading    = ref(false)
const error      = ref<string | null>(null)
const pagination = ref({ page: 1, page_size: 20, total: 0, total_pages: 0 })

const filters = ref({ status: '', regulatory_class: '', year: '' })

const STATUS_OPTIONS = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Draft',        label: 'Nháp' },
  { value: 'Under Review', label: 'Đang xét duyệt' },
  { value: 'Approved',     label: 'Đã duyệt' },
]

const CLASS_OPTIONS = [
  { value: '', label: 'Tất cả phân loại' },
  { value: 'Class I',   label: 'Class I' },
  { value: 'Class IIa', label: 'Class IIa' },
  { value: 'Class IIb', label: 'Class IIb' },
  { value: 'Class III', label: 'Class III' },
]

function cleanFilters() {
  const f: Record<string, unknown> = {}
  if (filters.value.status) f.status = filters.value.status
  if (filters.value.regulatory_class) f.regulatory_class = filters.value.regulatory_class
  if (filters.value.year?.trim()) f.year = filters.value.year.trim()
  return f
}

async function fetchList(page = 1) {
  loading.value = true
  error.value = null
  try {
    const res = await listTechnicalSpecs({ ...cleanFilters(), page, page_size: 20 })
    items.value = res.items
    pagination.value = {
      page,
      page_size: 20,
      total: res.total,
      total_pages: Math.ceil(res.total / 20) || 1,
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
    items.value = []
  } finally {
    loading.value = false
  }
}

function applyFilters() { fetchList(1) }
function resetFilters()  { filters.value = { status: '', regulatory_class: '', year: '' }; fetchList(1) }
function goToPage(p: number) { fetchList(p) }
const hasFilters = () => !!(filters.value.status || filters.value.regulatory_class || filters.value.year)

onMounted(() => fetchList(1))
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-03</p>
        <h1 class="text-2xl font-bold text-slate-900">Đặc tả Kỹ thuật</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ pagination.total }}</strong> đặc tả
        </p>
      </div>
      <router-link to="/planning/technical-specs/new" class="btn-primary shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo đặc tả
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
          <label class="form-label">Phân loại thiết bị</label>
          <select v-model="filters.regulatory_class" class="form-select">
            <option v-for="c in CLASS_OPTIONS" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Năm</label>
          <input v-model="filters.year" type="text" class="form-input" placeholder="vd: 2026"
                 @keyup.enter="applyFilters" />
        </div>
      </div>
      <div class="flex items-center gap-2.5 mt-4 pt-4 border-t border-slate-100">
        <button class="btn-primary" :disabled="loading" @click="applyFilters">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Tìm kiếm
        </button>
        <button v-if="hasFilters()" class="btn-ghost" @click="resetFilters">Xóa bộ lọc</button>
      </div>
    </div>

    <SkeletonLoader v-if="loading" variant="table" :rows="6" />

    <div v-else-if="error" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ error }}</span>
      <button class="text-xs font-semibold underline" @click="fetchList(pagination.page)">Thử lại</button>
    </div>

    <template v-else>
      <div class="table-wrapper animate-slide-up" style="animation-delay:80ms">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Đặc tả</th>
              <th class="table-header">Mô tả thiết bị</th>
              <th class="table-header">Phân loại</th>
              <th class="table-header">Ngày tạo</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-slate-100">
            <tr v-for="(item, i) in items" :key="item.name"
                class="table-row animate-fade-in cursor-pointer"
                :style="`animation-delay: ${i * 30}ms`"
                @click="router.push(`/planning/technical-specs/${item.name}`)">
              <td class="table-cell">
                <span class="font-mono text-[12px] font-semibold text-brand-600">{{ item.name }}</span>
              </td>
              <td class="table-cell text-slate-700">{{ item.equipment_description }}</td>
              <td class="table-cell">
                <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {{ item.regulatory_class }}
                </span>
              </td>
              <td class="table-cell text-slate-500 text-sm">{{ formatDate(item.creation) }}</td>
              <td class="px-5 py-4"><StatusBadge :state="item.status" /></td>
            </tr>
            <tr v-if="!items.length">
              <td colspan="5" class="px-5 py-16 text-center">
                <div class="flex flex-col items-center gap-3 text-slate-400">
                  <svg class="w-10 h-10 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p class="text-sm">Không có đặc tả nào phù hợp.</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="pagination.total_pages > 1" class="flex items-center justify-between mt-5 px-1">
        <p class="text-xs text-slate-500">
          Trang <strong>{{ pagination.page }}</strong> / {{ pagination.total_pages }}
        </p>
        <div class="flex items-center gap-1">
          <button class="page-btn-default"
                  :disabled="pagination.page <= 1 || loading"
                  @click="goToPage(pagination.page - 1)">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button v-for="p in pagination.total_pages" :key="p"
                  :class="p === pagination.page ? 'page-btn-active' : 'page-btn-default'"
                  :disabled="loading" @click="goToPage(p)">{{ p }}</button>
          <button class="page-btn-default"
                  :disabled="pagination.page >= pagination.total_pages || loading"
                  @click="goToPage(pagination.page + 1)">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </template>

  </div>
</template>
