<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// — Depreciation & Asset Accounting
import { ref, computed, onMounted } from 'vue'
import { frappeGet, frappePost } from '@/api/helpers'

// ─── Types ────────────────────────────────────────────────────────────────────
interface AssetDeprRow {
  name: string
  asset_name: string
  asset_category?: string
  department?: string
  purchase_date?: string
  in_service_date?: string
  gross_purchase_amount?: number
  residual_value?: number
  depreciation_method?: string
  useful_life_years?: number
  accumulated_depreciation?: number
  current_book_value?: number
  lifecycle_status?: string
  configured?: boolean
  pct_depreciated?: number
}
interface Stats {
  total_assets: number
  configured_count: number
  unconfigured_count: number
  fully_depreciated: number
  total_gross: number
  total_accumulated: number
  total_book_value: number
  overall_pct: number
  by_method: { method: string; count: number }[]
  by_category: { category: string; book_value: number }[]
}
interface ScheduleRow {
  year: number
  annual_depr: number
  accumulated: number
  book_value: number
  is_current: boolean
  is_future: boolean
}
interface Schedule {
  name: string
  asset_name: string
  gross: number
  residual: number
  method: string
  years: number
  in_service: string
  schedule: ScheduleRow[]
}

const BASE = '/api/method/assetcore.api.depreciation'

// ─── State ────────────────────────────────────────────────────────────────────
const stats        = ref<Stats | null>(null)
const rows         = ref<AssetDeprRow[]>([])
const total        = ref(0)
const page         = ref(1)
const PAGE_SIZE    = 30

const methodFilter   = ref('')
const statusFilter   = ref('')
const categoryFilter = ref('')

const statsLoading  = ref(false)
const listLoading   = ref(false)
const computing     = ref<string | null>(null)
const computingAll  = ref(false)
const toast         = ref('')
const toastOk       = ref(true)

const scheduleOpen   = ref(false)
const schedule       = ref<Schedule | null>(null)
const scheduleLoading = ref(false)

// ─── Fetch ────────────────────────────────────────────────────────────────────
async function loadStats() {
  statsLoading.value = true
  try {
    stats.value = await frappeGet<Stats>(`${BASE}.get_depreciation_stats`)
  } finally { statsLoading.value = false }
}

async function loadList() {
  listLoading.value = true
  try {
    const res = await frappeGet<{ items: AssetDeprRow[]; pagination: { total: number } }>(
      `${BASE}.list_assets_depreciation`, {
        page: page.value,
        page_size: PAGE_SIZE,
        method_filter:   methodFilter.value,
        status_filter:   statusFilter.value,
        category_filter: categoryFilter.value,
      },
    )
    if (res) {
      rows.value  = res.items || []
      total.value = res.pagination?.total || 0
    }
  } finally { listLoading.value = false }
}

async function applyFilters() {
  page.value = 1
  await loadList()
}

function prevPage() { if (page.value > 1) { page.value--; loadList() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; loadList() } }

// ─── Compute ──────────────────────────────────────────────────────────────────
async function computeOne(name: string) {
  computing.value = name
  try {
    await frappeGet(`${BASE}.compute_one_depreciation`, { name })
    showToast('Đã tính lại khấu hao', true)
    await Promise.all([loadStats(), loadList()])
  } catch (e: unknown) {
    showToast((e as Error).message || 'Lỗi tính khấu hao', false)
  } finally { computing.value = null }
}

async function computeAll() {
  if (!confirm(`Tính lại khấu hao cho toàn bộ ${stats.value?.configured_count || 0} thiết bị đã cấu hình?`)) return
  computingAll.value = true
  try {
    const res = await frappePost<{ updated: number; skipped: number }>(`${BASE}.compute_all_depreciation`)
    showToast(`Cập nhật ${res?.updated || 0} thiết bị, bỏ qua ${res?.skipped || 0}`, true)
    await Promise.all([loadStats(), loadList()])
  } catch (e: unknown) {
    showToast((e as Error).message || 'Lỗi tính khấu hao hàng loạt', false)
  } finally { computingAll.value = false }
}

// ─── Schedule modal ───────────────────────────────────────────────────────────
async function openSchedule(name: string) {
  scheduleOpen.value   = true
  scheduleLoading.value = true
  schedule.value       = null
  try {
    schedule.value = await frappeGet<Schedule>(`${BASE}.get_depreciation_schedule`, { name })
  } finally { scheduleLoading.value = false }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function showToast(msg: string, ok: boolean) {
  toast.value = msg; toastOk.value = ok
  setTimeout(() => { toast.value = '' }, 4000)
}

function vnd(v?: number) {
  if (v == null) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function vndShort(v?: number) {
  if (v == null) return '—'
  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + ' tỷ'
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + ' tr'
  return vnd(v)
}

function pctBar(pct?: number) { return Math.min(100, pct || 0) }
function pctColor(pct?: number) {
  if (!pct) return '#94a3b8'
  if (pct >= 90) return '#ef4444'
  if (pct >= 60) return '#f59e0b'
  return '#10b981'
}

function methodLabel(m?: string) {
  const map: Record<string, string> = {
    'Straight Line': 'Đường thẳng',
    'Double Declining': 'Số dư giảm dần',
  }
  return m ? (map[m] || m) : '—'
}

const maxCategoryValue = computed(() =>
  Math.max(...(stats.value?.by_category?.map(c => c.book_value) || [1]), 1)
)

onMounted(() => Promise.all([loadStats(), loadList()]))
</script>

<template>
  <div class="page-container animate-fade-in">
<!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Kế toán tài sản</p>
        <h1 class="text-2xl font-bold text-slate-900">Khấu hao thiết bị</h1>
        <p class="text-sm text-slate-500 mt-1">Theo dõi giá trị còn lại và lịch khấu hao toàn bộ danh mục</p>
      </div>
      <button
        class="btn-primary flex items-center gap-2"
        :disabled="computingAll"
        @click="computeAll"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {{ computingAll ? 'Đang tính...' : 'Tính lại toàn bộ' }}
      </button>
    </div>

    <!-- Toast -->
    <Transition name="fade">
      <div
v-if="toast"
           :class="['mb-4 px-4 py-3 rounded-lg text-sm font-medium', toastOk ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200']">
        {{ toast }}
      </div>
    </Transition>

    <!-- KPI Cards -->
    <div v-if="statsLoading && !stats" class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div v-for="i in 4" :key="i" class="card p-5 h-24 animate-pulse bg-slate-100" />
    </div>

    <div v-else-if="stats" class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div class="card p-5">
        <p class="text-xs font-medium text-slate-500 mb-1">Nguyên giá toàn bộ</p>
        <p class="text-2xl font-bold text-slate-900">{{ vndShort(stats.total_gross) }}</p>
        <p class="text-xs text-slate-400 mt-1">{{ stats.total_assets }} thiết bị</p>
      </div>
      <div class="card p-5">
        <p class="text-xs font-medium text-slate-500 mb-1">Khấu hao lũy kế</p>
        <p class="text-2xl font-bold text-amber-600">{{ vndShort(stats.total_accumulated) }}</p>
        <p class="text-xs text-slate-400 mt-1">{{ stats.overall_pct }}% nguyên giá</p>
      </div>
      <div class="card p-5">
        <p class="text-xs font-medium text-slate-500 mb-1">Giá trị còn lại</p>
        <p class="text-2xl font-bold text-emerald-600">{{ vndShort(stats.total_book_value) }}</p>
        <p class="text-xs text-slate-400 mt-1">{{ 100 - stats.overall_pct }}% giá trị</p>
      </div>
      <div class="card p-5">
        <p class="text-xs font-medium text-slate-500 mb-1">Trạng thái cấu hình</p>
        <p class="text-2xl font-bold text-slate-900">{{ stats.configured_count }}<span class="text-base font-normal text-slate-400">/{{ stats.total_assets }}</span></p>
        <p class="text-xs text-slate-400 mt-1">{{ stats.unconfigured_count }} chưa cấu hình · {{ stats.fully_depreciated }} hết KH</p>
      </div>
    </div>

    <!-- Charts row -->
    <div v-if="stats" class="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
<!-- Overall progress -->
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-slate-700 mb-4">Tiến độ khấu hao tổng thể</h3>
        <div class="flex items-center justify-center mb-4">
          <div class="relative w-32 h-32">
            <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="#f1f5f9" stroke-width="3" />
              <circle
cx="18" cy="18" r="15.9" fill="none"
                      :stroke="pctColor(stats.overall_pct)" stroke-width="3"
                      :stroke-dasharray="`${stats.overall_pct} ${100 - stats.overall_pct}`"
                      stroke-linecap="round" />
            </svg>
            <div class="absolute inset-0 flex flex-col items-center justify-center">
              <span class="text-2xl font-bold text-slate-900">{{ stats.overall_pct }}%</span>
              <span class="text-[10px] text-slate-400">đã khấu hao</span>
            </div>
          </div>
        </div>
        <div class="space-y-2 text-xs">
          <div class="flex justify-between">
            <span class="text-slate-500">Nguyên giá</span>
            <span class="font-medium">{{ vndShort(stats.total_gross) }}</span>
          </div>
          <div class="flex justify-between text-amber-600">
            <span>Đã khấu hao</span>
            <span class="font-medium">{{ vndShort(stats.total_accumulated) }}</span>
          </div>
          <div class="flex justify-between text-emerald-600">
            <span>Còn lại</span>
            <span class="font-medium">{{ vndShort(stats.total_book_value) }}</span>
          </div>
        </div>
      </div>

      <!-- By method -->
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-slate-700 mb-4">Phương pháp khấu hao</h3>
        <div class="space-y-3">
          <div v-for="m in stats.by_method" :key="m.method" class="flex items-center gap-3">
            <div class="flex-1">
              <div class="flex justify-between mb-1">
                <span class="text-xs text-slate-600">{{ methodLabel(m.method) }}</span>
                <span class="text-xs font-medium">{{ m.count }} TS</span>
              </div>
              <div class="h-2 bg-slate-100 rounded-full">
                <div
class="h-2 bg-blue-500 rounded-full"
                     :style="`width:${Math.round(m.count / stats!.configured_count * 100)}%`" />
              </div>
            </div>
          </div>
          <div v-if="stats.unconfigured_count > 0" class="flex items-center gap-3">
            <div class="flex-1">
              <div class="flex justify-between mb-1">
                <span class="text-xs text-slate-400">Chưa cấu hình</span>
                <span class="text-xs">{{ stats.unconfigured_count }} TS</span>
              </div>
              <div class="h-2 bg-slate-100 rounded-full">
                <div
class="h-2 bg-slate-300 rounded-full"
                     :style="`width:${Math.round(stats.unconfigured_count / stats.total_assets * 100)}%`" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- By category -->
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-slate-700 mb-4">Giá trị còn lại theo danh mục</h3>
        <div class="space-y-2">
          <div v-for="c in stats.by_category.slice(0,6)" :key="c.category">
            <div class="flex justify-between text-xs mb-0.5">
              <span class="text-slate-600 truncate max-w-[140px]" :title="c.category">{{ c.category }}</span>
              <span class="font-medium text-slate-700 shrink-0 ml-1">{{ vndShort(c.book_value) }}</span>
            </div>
            <div class="h-1.5 bg-slate-100 rounded-full">
              <div
class="h-1.5 bg-emerald-500 rounded-full"
                   :style="`width:${Math.round(c.book_value / maxCategoryValue * 100)}%`" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="card p-4 mb-4">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label for="depr-method-filter" class="form-label">Phương pháp khấu hao</label>
          <select id="depr-method-filter" v-model="methodFilter" class="form-select w-full" @change="applyFilters">
            <option value="">Tất cả</option>
            <option value="Straight Line">Đường thẳng</option>
            <option value="Double Declining">Số dư giảm dần</option>
          </select>
        </div>
        <div>
          <label for="depr-status-filter" class="form-label">Trạng thái thiết bị</label>
          <select id="depr-status-filter" v-model="statusFilter" class="form-select w-full" @change="applyFilters">
            <option value="">Tất cả</option>
            <option value="Active">Đang hoạt động</option>
            <option value="Commissioned">Đã tiếp nhận</option>
            <option value="Under Repair">Đang sửa chữa</option>
            <option value="Out of Service">Ngưng sử dụng</option>
            <option value="Decommissioned">Đã thanh lý</option>
          </select>
        </div>
        <div>
          <label for="depr-category-filter" class="form-label">Danh mục</label>
          <input
id="depr-category-filter" v-model="categoryFilter" type="text" class="form-input w-full"
                 placeholder="Lọc theo danh mục..." @input="applyFilters" />
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-5 py-3 border-b border-slate-100">
        <p class="text-sm font-semibold text-slate-700">
          Danh sách thiết bị
          <span class="text-slate-400 font-normal ml-1">({{ total }} thiết bị)</span>
        </p>
      </div>

      <div v-if="listLoading && !rows.length" class="text-center text-slate-400 py-12">Đang tải...</div>
      <div v-else-if="rows.length === 0" class="text-center text-slate-400 py-12 text-sm">Không có dữ liệu.</div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Thiết bị</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Phương pháp</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 hidden md:table-cell">Ngày đưa vào SD</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 hidden lg:table-cell">Tuổi thọ</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500">Nguyên giá</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 hidden md:table-cell">Lũy kế KH</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500">Còn lại</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">% KH</th>
              <th class="px-4 py-3" />
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="a in rows" :key="a.name" class="hover:bg-slate-50/70">
              <td class="px-4 py-3">
                <p class="font-medium text-slate-800 text-sm">{{ a.asset_name }}</p>
                <p class="text-[11px] text-slate-400 font-mono">{{ a.name }}</p>
              </td>
              <td class="px-4 py-3">
                <span v-if="a.configured" class="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                  {{ methodLabel(a.depreciation_method) }}
                </span>
                <span v-else class="text-xs text-slate-400">Chưa cấu hình</span>
              </td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">
                {{ a.in_service_date || '—' }}
              </td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden lg:table-cell">
                {{ a.useful_life_years ? a.useful_life_years + ' năm' : '—' }}
              </td>
              <td class="px-4 py-3 text-right text-sm font-medium text-slate-700">
                {{ vnd(a.gross_purchase_amount) }}
              </td>
              <td class="px-4 py-3 text-right text-sm text-amber-600 hidden md:table-cell">
                {{ a.configured ? vnd(a.accumulated_depreciation) : '—' }}
              </td>
              <td class="px-4 py-3 text-right text-sm font-semibold text-emerald-700">
                {{ vnd(a.current_book_value) }}
              </td>
              <td class="px-4 py-3">
                <div v-if="a.configured" class="flex items-center gap-2 min-w-[80px]">
                  <div class="flex-1 h-1.5 bg-slate-100 rounded-full">
                    <div
class="h-1.5 rounded-full transition-all"
                         :style="`width:${pctBar(a.pct_depreciated)}%;background:${pctColor(a.pct_depreciated)}`" />
                  </div>
                  <span class="text-xs text-slate-500 w-9 shrink-0">{{ a.pct_depreciated }}%</span>
                </div>
                <span v-else class="text-xs text-slate-300">—</span>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2 justify-end">
                  <button
v-if="a.configured"
                          class="text-xs text-slate-500 hover:text-blue-600 font-medium transition-colors"
                          @click="openSchedule(a.name)">
                    Lịch KH
                  </button>
                  <button
v-if="a.configured"
                          class="text-xs text-blue-600 hover:text-blue-800 font-medium disabled:opacity-40"
                          :disabled="computing === a.name"
                          @click="computeOne(a.name)">
                    {{ computing === a.name ? '...' : 'Tính lại' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} / {{ total }}</span>
        <div class="flex gap-2">
          <button
:disabled="page === 1"
                  class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
                  @click="prevPage">
‹
</button>
          <button
:disabled="page * PAGE_SIZE >= total"
                  class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
                  @click="nextPage">
›
</button>
        </div>
      </div>
    </div>

    <!-- Depreciation Schedule Modal -->
    <Transition name="fade">
      <div
v-if="scheduleOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
           @click.self="scheduleOpen = false">
        <div class="bg-white rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
<!-- Modal header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <div>
              <h2 class="font-semibold text-slate-800 text-base">Lịch khấu hao</h2>
              <p v-if="schedule" class="text-xs text-slate-500 mt-0.5">{{ schedule.asset_name }}</p>
            </div>
            <button
class="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                    @click="scheduleOpen = false">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Modal body -->
          <div class="overflow-y-auto flex-1 px-6 py-4">
            <div v-if="scheduleLoading" class="text-center text-slate-400 py-8">Đang tải...</div>
            <div v-else-if="schedule">
              <!-- Summary -->
              <div class="grid grid-cols-3 gap-3 mb-5 text-center">
                <div class="bg-slate-50 rounded-lg p-3">
                  <p class="text-[10px] text-slate-400 mb-1">Nguyên giá</p>
                  <p class="text-sm font-semibold text-slate-700">{{ vnd(schedule.gross) }}</p>
                </div>
                <div class="bg-slate-50 rounded-lg p-3">
                  <p class="text-[10px] text-slate-400 mb-1">Phương pháp</p>
                  <p class="text-sm font-semibold text-slate-700">{{ methodLabel(schedule.method) }}</p>
                </div>
                <div class="bg-slate-50 rounded-lg p-3">
                  <p class="text-[10px] text-slate-400 mb-1">Tuổi thọ</p>
                  <p class="text-sm font-semibold text-slate-700">{{ schedule.years }} năm</p>
                </div>
              </div>

              <!-- Schedule table -->
              <table class="w-full text-sm">
                <thead>
                  <tr class="text-xs text-slate-400 border-b border-slate-100">
                    <th class="py-2 text-left font-medium">Năm</th>
                    <th class="py-2 text-right font-medium">KH năm</th>
                    <th class="py-2 text-right font-medium">Lũy kế</th>
                    <th class="py-2 text-right font-medium">Còn lại</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
v-for="r in schedule.schedule" :key="r.year"
                      :class="['border-b border-slate-50',
                                r.is_current ? 'bg-blue-50/60 font-medium' : '',
                                r.is_future ? 'text-slate-400' : '']">
                    <td class="py-2.5 text-left">
                      {{ r.year }}
                      <span
v-if="r.is_current"
                            class="ml-1.5 text-[10px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded-full">
                        Năm nay
                      </span>
                    </td>
                    <td class="py-2.5 text-right text-amber-600">{{ vnd(r.annual_depr) }}</td>
                    <td class="py-2.5 text-right text-slate-500">{{ vnd(r.accumulated) }}</td>
                    <td class="py-2.5 text-right text-emerald-600 font-semibold">{{ vnd(r.book_value) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </Transition>
</div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
