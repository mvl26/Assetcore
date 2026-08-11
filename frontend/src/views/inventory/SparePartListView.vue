<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed, watch } from 'vue'
import { SPARE_PART_CATEGORY_LABEL } from '@/constants/labels'
import { useRouter, useRoute } from 'vue-router'
import { listSpareParts, createSparePart } from '@/api/inventory'
import type { SparePart } from '@/types/inventory'
import SmartSelect from '@/components/common/SmartSelect.vue'
import CurrencyInput from '@/components/common/CurrencyInput.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'

const router = useRouter()
const route = useRoute()
const rows = ref<SparePart[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 30
const loading = ref(false)
// AC-UX-047 (lô 1) — lỗi của LƯỢT NẠP danh mục. Trước đây `load()` không có `catch`
// ⇒ API hỏng in «Chưa có phụ tùng phù hợp» ⇒ người dùng tin là KHO RỖNG.
const loadError = ref<string | null>(null)
// R7 §9.4.5 — drill từ KPI store 'low_stock': ?low_stock=1 → chỉ parts dưới định mức.
const lowStockOnly = ref<boolean>(route.query.low_stock === '1')
const showFilters = ref<boolean>(lowStockOnly.value)

const q = ref('')
const categoryFilter = ref('')
const showForm = ref(false)
const saving = ref(false)
const toast = ref('')

const form = ref<Partial<SparePart>>({
  part_name: '', part_category: 'Other', manufacturer: '', manufacturer_part_no: '',
  unit_cost: 0, stock_uom: 'Cái', min_stock_level: 0, max_stock_level: 0, is_critical: 0, is_active: 1,
})

// Nhãn lấy từ SSoT `constants/labels.ts` — map cục bộ ở đây từng là bản sao thứ
// hai, dễ lệch với file nhập/xuất Excel (guard parity BE↔FE khoá điều này).
const CATEGORIES = [
  { v: '', l: 'Tất cả' },
  ...Object.entries(SPARE_PART_CATEGORY_LABEL).map(([v, l]) => ({ v, l })),
]
interface Chip { key: 'q' | 'category' | 'lowStock'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (lowStockOnly.value) chips.push({ key: 'lowStock', label: 'Dưới định mức' })
  if (q.value.trim()) chips.push({ key: 'q', label: `"${q.value.trim()}"` })
  if (categoryFilter.value) {
    const c = CATEGORIES.find(x => x.v === categoryFilter.value)
    chips.push({ key: 'category', label: c?.l ?? categoryFilter.value })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'q') q.value = ''
  else if (key === 'lowStock') lowStockOnly.value = false
  else categoryFilter.value = ''
  page.value = 1; load()
}

function resetFilters() {
  q.value = ''
  categoryFilter.value = ''
  lowStockOnly.value = false
  page.value = 1; load()
}

function quickFilter(_key: 'category', value: string) {
  if (!value) return
  categoryFilter.value = value
  showFilters.value = false
  page.value = 1; load()
}

const emptyTitle = computed(() =>
  activeFilterCount.value > 0 ? 'Không có phụ tùng nào phù hợp' : 'Chưa có phụ tùng nào')
const EMPTY_HINT = 'Hãy thêm phụ tùng mới hoặc xoá bộ lọc để xem tất cả.'

async function load() {
  loading.value = true
  loadError.value = null                       // INV-UX3-4 — xoá lỗi ĐẦU lượt
  try {
    const r = await listSpareParts({
      page: page.value, page_size: PAGE_SIZE, q: q.value,
      category: categoryFilter.value,
      ...(lowStockOnly.value ? { low_stock: 1 } : {}),
    })
    rows.value = r?.items || []
    total.value = r?.pagination?.total || 0
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : String(e)
    rows.value = []; total.value = 0           // INV-UX3-5
  } finally { loading.value = false }
}

// Search debounce is handled by ListFilterBar.vue (@apply fires after pause).
watch(categoryFilter, () => { page.value = 1; load() })
watch(lowStockOnly, () => { page.value = 1; load() })
// Drill-down lần 2 (cùng route, query khác) — re-sync từ route.query (§9.3).
watch(() => route.query.low_stock, (val) => { lowStockOnly.value = val === '1' })

function openCreate() {
  form.value = {
    part_name: '', part_category: 'Other', manufacturer: '', manufacturer_part_no: '',
    unit_cost: 0, stock_uom: 'Cái', min_stock_level: 0, max_stock_level: 0, is_critical: 0, is_active: 1,
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
  <!-- AC-UX-047 (lô 1) — khuôn 4 trạng thái loại trừ (ui/ListPageShell). -->
  <ListPageShell
    :loading="loading"
    :error-message="loadError"
    :is-empty="!rows.length"
    :empty-title="emptyTitle"
    :empty-hint="EMPTY_HINT"
    @retry="load">
    <template #header>
      <PageHeader
        title="Danh mục phụ tùng"
        :subtitle="`IMM-15 · Tồn kho phụ tùng — Tổng ${total} phụ tùng`"
        :breadcrumb="[{ label: 'IMM-15 · Tồn kho phụ tùng', to: '/inventory/dashboard' }, { label: 'Danh mục' }]"
      >
        <template #actions>
          <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
          <button class="btn-primary shrink-0" @click="openCreate">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Tạo phụ tùng
          </button>
        </template>
      </PageHeader>
      <!-- Dải phản hồi tạo phụ tùng sống ở CẢ 4 trạng thái (INV-UX3-17). -->
      <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm">{{ toast }}</div>
    </template>

    <template #filters>
      <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="q"
      search-placeholder="Tên / mã / mã NSX..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="() => { page = 1; load() }"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Loại</label>
          <select v-model="categoryFilter" class="form-select w-full">
            <option v-for="c in CATEGORIES" :key="c.v" :value="c.v">{{ c.l }}</option>
          </select>
        </div>
      </template>
      </ListFilterBar>
    </template>

    <template #skeleton>
      <SkeletonLoader variant="table" :rows="6" />
    </template>

    <template #empty-action>
      <button v-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline" @click="resetFilters">
        Xóa bộ lọc để xem tất cả
      </button>
      <button v-else class="btn-primary" @click="openCreate">Thêm phụ tùng đầu tiên</button>
    </template>

    <template #toolbar>
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ rows.length }}</strong> / {{ total }} phụ tùng</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
    </template>

    <!-- Mobile cards (< sm) -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="p in rows"
            :key="p.name"
            class="mobile-card"
            @click="router.push(`/spare-parts/${p.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ p.part_code || p.name }}</span>
              <span
                v-if="p.is_low_stock"
                class="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-semibold border border-amber-100"
              >Tồn thấp</span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ p.part_name }}</p>
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <button
                v-if="p.part_category"
                class="text-xs px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600"
                @click.stop="quickFilter('category', p.part_category!)"
              >{{ CATEGORIES.find(c => c.v === p.part_category)?.l ?? p.part_category }}</button>
              <span class="text-slate-300">·</span>
              <span :class="p.is_low_stock ? 'text-red-600 font-medium' : ''">{{ p.total_stock || 0 }} {{ p.stock_uom }}</span>
              <span class="text-slate-300">·</span>
              <span>{{ vnd(p.unit_cost) }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table (sm+) -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 border-b border-slate-100">
              <tr>
                <th class="table-header">Phụ tùng</th>
                <th class="table-header hidden md:table-cell">NSX / Mã NSX</th>
                <th class="table-header">Loại</th>
                <th class="table-header text-right">Đơn giá</th>
                <th class="table-header text-right">Tồn</th>
                <th class="table-header text-right hidden lg:table-cell">Min</th>
                <th class="table-header text-center">Cờ</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-50">
              <tr
                v-for="p in rows" :key="p.name"
                class="hover:bg-slate-50/70 cursor-pointer transition-all hover:translate-x-0.5"
                @click="router.push(`/spare-parts/${p.name}`)"
              >
                <td class="px-4 py-3">
                  <p class="font-medium text-slate-900">{{ p.part_name }}</p>
                  <p class="font-mono text-xs text-brand-700 mt-0.5">{{ p.part_code || p.name }}</p>
                </td>
                <td class="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">
                  {{ p.manufacturer || '—' }}<span v-if="p.manufacturer_part_no" class="ml-1 font-mono">· {{ p.manufacturer_part_no }}</span>
                </td>
                <td class="px-4 py-3">
                  <button
                    v-if="p.part_category"
                    class="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 transition-all hover:ring-2 hover:ring-offset-1 hover:ring-slate-300"
                    :title="`Lọc: ${CATEGORIES.find(c => c.v === p.part_category)?.l ?? p.part_category}`"
                    @click.stop="quickFilter('category', p.part_category!)"
                  >{{ CATEGORIES.find(c => c.v === p.part_category)?.l ?? p.part_category }}</button>
                </td>
                <td class="px-4 py-3 text-right text-sm">{{ vnd(p.unit_cost) }}</td>
                <td
                  class="px-4 py-3 text-right font-medium tabular-nums"
                  :class="p.is_low_stock ? 'text-red-600' : 'text-slate-700'">
                  {{ p.total_stock || 0 }} <span class="text-xs text-slate-400">{{ p.stock_uom }}</span>
                </td>
                <td class="px-4 py-3 text-right text-xs text-slate-500 tabular-nums hidden lg:table-cell">
                  {{ p.min_stock_level || '—' }}
                </td>
                <td class="px-4 py-3 text-center">
                  <span
                    v-if="p.is_critical" class="inline-block text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-700 font-semibold border border-red-100"
                    title="Phụ tùng quan trọng">Quan trọng</span>
                  <span
                    v-if="p.is_low_stock" class="inline-block ml-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-semibold border border-amber-100"
                    title="Tồn dưới mức min">Tồn thấp</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

    <template #pagination>
      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} / {{ total }}</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50" @click="prevPage">Trước</button>
          <button :disabled="page * PAGE_SIZE >= total" class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50" @click="nextPage">Sau</button>
        </div>
      </div>
    </template>
  </ListPageShell>

  <!-- Hộp thoại tạo đặt NGOÀI khuôn: mở được ở CẢ 4 trạng thái (INV-UX3-17). -->
  <Transition name="fade">
      <div
v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
           @click.self="showForm = false">
        <div class="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-modal border border-slate-200">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200">
            <h2 class="font-semibold text-slate-900">Tạo phụ tùng</h2>
            <button class="p-1.5 rounded-md text-slate-400 hover:bg-slate-100" aria-label="Đóng" @click="showForm = false">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
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
                <CurrencyInput id="sp-cost" v-model="form.unit_cost" aria-label="Đơn giá" class="form-input w-full" />
              </div>
              <div>
                <p class="form-label">Đơn vị tính cơ bản</p>
                <SmartSelect v-model="form.stock_uom" doctype="AC UOM" placeholder="Cái, Hộp, Bộ..." />
              </div>
              <div>
                <p class="form-label">Đơn vị tính mua hàng</p>
                <SmartSelect v-model="form.purchase_uom" doctype="AC UOM" placeholder="Để trống = dùng đơn vị tồn kho..." />
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
          <div class="flex gap-3 justify-end px-6 py-4 border-t border-slate-200">
            <button class="btn-ghost" @click="showForm = false">Huỷ</button>
            <button class="btn-primary" :disabled="saving" @click="submit">
              {{ saving ? 'Đang lưu…' : 'Tạo phụ tùng' }}
            </button>
          </div>
        </div>
      </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
