<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { listSpareParts, createSparePart } from '@/api/inventory'
import type { SparePart } from '@/types/inventory'

const router = useRouter()
const rows = ref<SparePart[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 30
const loading = ref(false)
const showFilters = ref(false)

const q = ref('')
const categoryFilter = ref('')
const showForm = ref(false)
const saving = ref(false)
const toast = ref('')

const form = ref<Partial<SparePart>>({
  part_name: '', part_category: 'Other', manufacturer: '', manufacturer_part_no: '',
  unit_cost: 0, uom: 'Nos', min_stock_level: 0, max_stock_level: 0, is_critical: 0, is_active: 1,
})

const CATEGORIES = [
  { v: '', l: 'Tất cả' },
  { v: 'Electrical', l: 'Điện' },
  { v: 'Mechanical', l: 'Cơ khí' },
  { v: 'Consumable', l: 'Tiêu hao' },
  { v: 'Filter', l: 'Bộ lọc' },
  { v: 'Battery', l: 'Pin/Ắc-quy' },
  { v: 'Sensor', l: 'Cảm biến' },
  { v: 'Other', l: 'Khác' },
]
const UOMS = ['Nos', 'Pcs', 'Set', 'Box', 'Meter', 'Liter', 'Kg']

interface Chip { key: 'q' | 'category'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (q.value.trim()) chips.push({ key: 'q', label: `"${q.value.trim()}"` })
  if (categoryFilter.value) {
    const c = CATEGORIES.find(x => x.v === categoryFilter.value)
    chips.push({ key: 'category', label: c?.l ?? categoryFilter.value })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: Chip['key']) {
  if (key === 'q') q.value = ''
  else categoryFilter.value = ''
  page.value = 1; load()
}

function resetFilters() {
  q.value = ''
  categoryFilter.value = ''
  page.value = 1; load()
}

function quickFilter(key: 'category', value: string) {
  if (!value) return
  categoryFilter.value = value
  showFilters.value = false
  page.value = 1; load()
}

async function load() {
  loading.value = true
  try {
    const r = await listSpareParts({ page: page.value, page_size: PAGE_SIZE, q: q.value, category: categoryFilter.value })
    rows.value = r?.items || []
    total.value = r?.pagination?.total || 0
  } finally { loading.value = false }
}

const debouncedSearch = useDebounceFn(() => { page.value = 1; load() }, 300)
watch(q, debouncedSearch)
watch(categoryFilter, () => { page.value = 1; load() })

function openCreate() {
  form.value = {
    part_name: '', part_category: 'Other', manufacturer: '', manufacturer_part_no: '',
    unit_cost: 0, uom: 'Nos', min_stock_level: 0, max_stock_level: 0, is_critical: 0, is_active: 1,
  }
  showForm.value = true
}

async function submit() {
  if (!form.value.part_name) { toast.value = 'Tên phụ tùng là bắt buộc'; return }
  saving.value = true
  try {
    const res = await createSparePart(form.value)
    showForm.value = false
    toast.value = `Đã tạo ${res.part_code}`
    await load()
    setTimeout(() => { toast.value = '' }, 3000)
  } catch (e: unknown) {
    toast.value = (e as Error).message || 'Lỗi tạo phụ tùng'
  } finally { saving.value = false }
}

function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; load() } }

function vnd(v?: number) {
  if (!v) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-5">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00 · Inventory</p>
        <h1 class="text-2xl font-bold text-slate-900">Danh mục phụ tùng</h1>
        <p class="text-sm text-slate-500 mt-1">Tổng <strong class="text-slate-700">{{ total }}</strong> phụ tùng</p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button
          class="relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-colors"
          :class="showFilters
            ? 'bg-brand-50 border-brand-300 text-brand-700'
            : 'bg-white border-slate-300 text-slate-600 hover:border-slate-400'"
          @click="showFilters = !showFilters"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 8h10M11 12h2M9 16h6" />
          </svg>
          Bộ lọc
          <span v-if="activeFilterCount > 0"
            class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-blue-500 text-white">
            {{ activeFilterCount }}
          </span>
          <svg class="w-3.5 h-3.5 transition-transform duration-200" :class="showFilters ? 'rotate-180' : ''"
               fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button class="btn-primary shrink-0" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Phụ tùng mới
        </button>
      </div>
    </div>

    <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm">{{ toast }}</div>

    <!-- Active chips -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="activeChips.length > 0 && !showFilters" class="flex flex-wrap items-center gap-2 mb-4">
        <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
        <button v-for="chip in activeChips" :key="chip.key"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
          @click="clearChip(chip.key)"
        >
          {{ chip.label }}
          <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">Xóa tất cả</button>
      </div>
    </Transition>

    <!-- Collapsible filter panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-40"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-40"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="showFilters" class="card p-4 mb-4 space-y-3">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label for="sp-search" class="form-label">Tìm kiếm</label>
            <input id="sp-search" v-model="q" type="text" class="form-input w-full"
                   placeholder="Tên / mã / part no NSX..." />
          </div>
          <div>
            <label for="sp-cat" class="form-label">Loại</label>
            <select id="sp-cat" v-model="categoryFilter" class="form-select w-full">
              <option v-for="c in CATEGORIES" :key="c.v" :value="c.v">{{ c.l }}</option>
            </select>
          </div>
        </div>
        <div v-if="activeChips.length > 0" class="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
          <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
          <button v-for="chip in activeChips" :key="chip.key"
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
            @click="clearChip(chip.key)"
          >
            {{ chip.label }}
            <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">Xóa tất cả</button>
        </div>
      </div>
    </Transition>

    <div class="card overflow-hidden">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ rows.length }}</strong> / {{ total }} phụ tùng</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading && !rows.length" class="text-center py-12 text-slate-400">Đang tải...</div>
      <div v-else-if="rows.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có phụ tùng nào.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Phụ tùng</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 hidden md:table-cell">NSX / Mã NSX</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Loại</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500">Đơn giá</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500">Tồn</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 hidden lg:table-cell">Min</th>
              <th class="px-4 py-3 text-center text-xs font-semibold text-slate-500">Cờ</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="p in rows" :key="p.name"
              class="hover:bg-slate-50/70 cursor-pointer transition-all hover:translate-x-0.5"
              @click="router.push(`/spare-parts/${p.name}`)"
            >
              <td class="px-4 py-3">
                <p class="font-medium text-slate-800">{{ p.part_name }}</p>
                <p class="text-[11px] text-slate-400 font-mono">{{ p.part_code || p.name }}</p>
              </td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">
                {{ p.manufacturer || '—' }}<span v-if="p.manufacturer_part_no" class="ml-1 font-mono">· {{ p.manufacturer_part_no }}</span>
              </td>
              <td class="px-4 py-3">
                <button v-if="p.part_category"
                  class="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 transition-all hover:ring-2 hover:ring-offset-1 hover:ring-slate-300"
                  :title="`Lọc: ${p.part_category}`"
                  @click.stop="quickFilter('category', p.part_category!)"
                >{{ p.part_category }}</button>
              </td>
              <td class="px-4 py-3 text-right text-sm">{{ vnd(p.unit_cost) }}</td>
              <td class="px-4 py-3 text-right font-medium"
                  :class="p.is_low_stock ? 'text-red-600' : 'text-slate-700'">
                {{ p.total_stock || 0 }} <span class="text-xs text-slate-400">{{ p.uom }}</span>
              </td>
              <td class="px-4 py-3 text-right text-xs text-slate-400 hidden lg:table-cell">
                {{ p.min_stock_level || '—' }}
              </td>
              <td class="px-4 py-3 text-center">
                <span v-if="p.is_critical" class="inline-block text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-700 font-semibold"
                      title="Phụ tùng quan trọng">!</span>
                <span v-if="p.is_low_stock" class="inline-block ml-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-semibold"
                      title="Tồn thấp">Low</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} / {{ total }}</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50" @click="prevPage">‹</button>
          <button :disabled="page * PAGE_SIZE >= total" class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50" @click="nextPage">›</button>
        </div>
      </div>
    </div>

    <!-- Create modal -->
    <Transition name="fade">
      <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
           @click.self="showForm = false">
        <div class="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h2 class="font-semibold text-slate-800">Tạo phụ tùng mới</h2>
            <button class="p-1.5 rounded-md text-slate-400 hover:bg-slate-100" @click="showForm = false">✕</button>
          </div>
          <div class="p-6 space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="md:col-span-2">
                <label for="sp-name" class="form-label">Tên phụ tùng *</label>
                <input id="sp-name" v-model="form.part_name" type="text" class="form-input w-full" />
              </div>
              <div>
                <label for="sp-code" class="form-label">Mã phụ tùng (để trống sẽ tự sinh)</label>
                <input id="sp-code" v-model="form.part_code" type="text" class="form-input w-full" />
              </div>
              <div>
                <label for="sp-cat-form" class="form-label">Loại</label>
                <select id="sp-cat-form" v-model="form.part_category" class="form-select w-full">
                  <option v-for="c in CATEGORIES.slice(1)" :key="c.v" :value="c.v">{{ c.l }}</option>
                </select>
              </div>
              <div>
                <label for="sp-mfr" class="form-label">Nhà sản xuất</label>
                <input id="sp-mfr" v-model="form.manufacturer" type="text" class="form-input w-full" />
              </div>
              <div>
                <label for="sp-mpn" class="form-label">Mã NSX</label>
                <input id="sp-mpn" v-model="form.manufacturer_part_no" type="text" class="form-input w-full font-mono" />
              </div>
              <div>
                <label for="sp-cost" class="form-label">Đơn giá (VND)</label>
                <input id="sp-cost" v-model.number="form.unit_cost" type="number" min="0" class="form-input w-full" />
              </div>
              <div>
                <label for="sp-uom" class="form-label">ĐVT</label>
                <select id="sp-uom" v-model="form.uom" class="form-select w-full">
                  <option v-for="u in UOMS" :key="u" :value="u">{{ u }}</option>
                </select>
              </div>
              <div>
                <label for="sp-min" class="form-label">Tồn min</label>
                <input id="sp-min" v-model.number="form.min_stock_level" type="number" min="0" class="form-input w-full" />
              </div>
              <div>
                <label for="sp-max" class="form-label">Tồn max</label>
                <input id="sp-max" v-model.number="form.max_stock_level" type="number" min="0" class="form-input w-full" />
              </div>
              <div class="flex items-center gap-3 pt-6">
                <input id="sp-crit" v-model="form.is_critical" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 rounded" />
                <label for="sp-crit" class="text-sm text-slate-700">Phụ tùng quan trọng</label>
              </div>
              <div class="flex items-center gap-3 pt-6">
                <input id="sp-active" v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 rounded" />
                <label for="sp-active" class="text-sm text-slate-700">Đang sử dụng</label>
              </div>
            </div>
          </div>
          <div class="flex gap-3 justify-end px-6 py-4 border-t border-slate-100">
            <button class="btn-ghost" @click="showForm = false">Huỷ</button>
            <button class="btn-primary" :disabled="saving" @click="submit">
              {{ saving ? 'Đang lưu...' : 'Tạo' }}
            </button>
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
