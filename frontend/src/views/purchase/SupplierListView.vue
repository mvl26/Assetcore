<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { listSuppliers, deleteSupplier } from '@/api/imm00'
import type { AcSupplier } from '@/types/imm00'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
const toast = useToast()

const router = useRouter()
const suppliers = ref<AcSupplier[]>([])
const loading = ref(false)
const error = ref('')
const totalCount = ref(0)
const showFilters = ref(false)
const PAGE_SIZE = 30

const filters = ref({
  search: '',
  vendor_type: '',
  country: '',
  is_active: '' as '' | '1' | '0',
  page: 1,
})

const VENDOR_TYPES: { value: string; label: string }[] = [
  { value: 'Manufacturer', label: 'Nhà sản xuất' },
  { value: 'Distributor', label: 'Nhà phân phối' },
  { value: 'Service Provider', label: 'Dịch vụ' },
  { value: 'Calibration Lab', label: 'Phòng hiệu chuẩn' },
]
const VENDOR_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  VENDOR_TYPES.map(v => [v.value, v.label]),
)

const VENDOR_TYPE_COLORS: Record<string, string> = {
  Manufacturer: 'bg-purple-100 text-purple-700',
  Distributor: 'bg-blue-100 text-blue-700',
  'Service Provider': 'bg-green-100 text-green-700',
  'Calibration Lab': 'bg-yellow-100 text-yellow-700',
}

interface FilterChip { key: 'search' | 'vendor_type' | 'country' | 'is_active'; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.vendor_type) {
    chips.push({ key: 'vendor_type', label: VENDOR_TYPE_LABEL[filters.value.vendor_type] || filters.value.vendor_type })
  }
  if (filters.value.country) chips.push({ key: 'country', label: filters.value.country })
  if (filters.value.is_active === '1') chips.push({ key: 'is_active', label: 'Đang hoạt động' })
  if (filters.value.is_active === '0') chips.push({ key: 'is_active', label: 'Ngừng hoạt động' })
  if (filters.value.search?.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listSuppliers(filters.value.page, PAGE_SIZE, filters.value.search) as unknown as
      { items: AcSupplier[]; pagination: { total: number } }
    let items = res?.items || []
    if (filters.value.vendor_type) items = items.filter(s => s.vendor_type === filters.value.vendor_type)
    if (filters.value.country) items = items.filter(s => (s.country || '').toLowerCase().includes(filters.value.country.toLowerCase()))
    if (filters.value.is_active === '1') items = items.filter(s => s.is_active === 1)
    if (filters.value.is_active === '0') items = items.filter(s => s.is_active === 0)
    suppliers.value = items
    totalCount.value = res?.pagination?.total || 0
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi tải dữ liệu'
  } finally {
    loading.value = false
  }
}

function applyFilters() { filters.value.page = 1; load() }
function quickFilter(key: 'vendor_type' | 'country', value: string) {
  if (!value) return
  if (filters.value[key] === value) return
  filters.value[key] = value
  filters.value.page = 1
  showFilters.value = false
  load()
}
function clearChip(key: FilterChip['key']) {
  if (key === 'is_active') filters.value.is_active = ''
  else (filters.value as Record<string, unknown>)[key] = ''
  applyFilters()
}
function resetFilters() {
  filters.value = { search: '', vendor_type: '', country: '', is_active: '', page: 1 }
  load()
}
function prevPage() { if (filters.value.page > 1) { filters.value.page--; load() } }
function nextPage() { if (filters.value.page * PAGE_SIZE < totalCount.value) { filters.value.page++; load() } }

async function remove(s: AcSupplier, ev: Event) {
  ev.stopPropagation()
  if (!confirm(`Xóa nhà cung cấp "${s.supplier_name}" (${s.name})?`)) return
  try {
    await deleteSupplier(s.name)
    await load()
  } catch (e: unknown) {
    toast.error((e as Error).message || 'Không thể xóa — có thể đang được tham chiếu')
  }
}

function formatDate(d?: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : '—'
}
function daysUntilExpiry(d?: string) {
  if (!d) return null
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
}
function expiryClass(d?: string) {
  const days = daysUntilExpiry(d)
  if (days === null) return 'text-slate-400'
  if (days < 0) return 'text-red-700 font-semibold'
  if (days < 30) return 'text-red-600 font-medium'
  if (days < 90) return 'text-yellow-600 font-medium'
  return 'text-slate-600'
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <div class="flex items-start justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Nhà cung cấp</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ totalCount }}</strong> nhà cung cấp
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button
          class="relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-colors"
          :class="showFilters
            ? 'bg-brand-50 border-brand-300 text-brand-700'
            : 'bg-white border-slate-300 text-slate-600 hover:border-slate-400 hover:text-slate-800'"
          @click="showFilters = !showFilters"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 8h10M11 12h2M9 16h6" />
          </svg>
          Bộ lọc
          <span
            v-if="activeFilterCount > 0"
            class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full"
            :class="showFilters ? 'bg-brand-600 text-white' : 'bg-blue-500 text-white'"
          >{{ activeFilterCount }}</span>
          <svg
            class="w-3.5 h-3.5 transition-transform duration-200"
            :class="showFilters ? 'rotate-180' : ''"
            fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button class="btn-primary shrink-0" @click="router.push('/suppliers/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm nhà cung cấp
        </button>
      </div>
    </div>

    <!-- Active filter chips -->
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
        <button
          v-for="chip in activeChips" :key="chip.key"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
          @click="clearChip(chip.key)"
        >
          {{ chip.label }}
          <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">
          Xóa tất cả
        </button>
      </div>
    </Transition>

    <!-- Filter panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-96"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-96"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="showFilters" class="card mb-5 p-4">
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-3">
          <select v-model="filters.vendor_type" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả loại</option>
            <option v-for="t in VENDOR_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
          <input
            v-model="filters.country"
            placeholder="Quốc gia..."
            class="form-input text-sm"
            @keyup.enter="applyFilters"
          />
          <select v-model="filters.is_active" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả trạng thái</option>
            <option value="1">Đang hoạt động</option>
            <option value="0">Ngừng hoạt động</option>
          </select>
        </div>
        <div class="flex gap-2">
          <input
            v-model="filters.search"
            placeholder="Tìm theo mã, tên, email, mã số thuế..."
            class="form-input flex-1 text-sm"
            @keyup.enter="applyFilters"
          />
          <button class="btn-primary text-sm" @click="applyFilters">Tìm</button>
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
        </div>
      </div>
    </Transition>

    <div v-if="error" class="alert-error mb-4">{{ error }}</div>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeFilterCount > 0">
            Kết quả lọc: <strong class="text-slate-700">{{ suppliers.length }}</strong> nhà cung cấp
          </span>
          <span v-else>
            Hiển thị <strong class="text-slate-700">{{ suppliers.length }}</strong> / {{ totalCount }} nhà cung cấp
          </span>
        </span>
        <button v-if="activeFilterCount > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">
          Xóa tất cả
        </button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="suppliers.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có nhà cung cấp nào phù hợp.</p>
        <button v-if="activeFilterCount > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã nhà cung cấp</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Tên nhà cung cấp</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Loại</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Quốc gia</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Email liên hệ</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Hết hạn HĐ</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-slate-500">Trạng thái</th>
              <th class="px-4 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="s in suppliers" :key="s.name"
              class="hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/suppliers/${s.name}`)"
            >
              <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ s.name }}</td>
              <td class="px-4 py-3 font-medium text-slate-800">{{ s.supplier_name }}</td>
              <td class="px-4 py-3">
                <button
                  v-if="s.vendor_type"
                  :class="['text-xs px-2 py-0.5 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', VENDOR_TYPE_COLORS[s.vendor_type] || 'bg-gray-100 text-gray-600']"
                  :title="`Lọc: ${VENDOR_TYPE_LABEL[s.vendor_type] || s.vendor_type}`"
                  @click.stop="quickFilter('vendor_type', s.vendor_type!)"
                >{{ VENDOR_TYPE_LABEL[s.vendor_type] || s.vendor_type }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3">
                <button
                  v-if="s.country"
                  class="text-left text-slate-700 hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                  @click.stop="quickFilter('country', s.country!)"
                >{{ s.country }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-slate-500">{{ s.email_id || '—' }}</td>
              <td class="px-4 py-3" :class="expiryClass(s.contract_end)">
                {{ formatDate(s.contract_end) }}
              </td>
              <td class="px-4 py-3 text-center">
                <span
                  class="text-xs px-2 py-0.5 rounded-full font-medium"
                  :class="s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
                >{{ s.is_active ? 'Hoạt động' : 'Ngừng' }}</span>
              </td>
              <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                <button
                  class="text-blue-600 hover:text-blue-800 text-xs font-medium"
                  @click.stop="router.push(`/suppliers/${s.name}/edit`)"
                >Sửa</button>
                <button
                  class="text-red-600 hover:text-red-800 text-xs font-medium"
                  @click="(ev) => remove(s, ev)"
                >Xóa</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (filters.page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(filters.page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button :disabled="filters.page === 1" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="prevPage">‹ Trước</button>
          <button :disabled="filters.page * PAGE_SIZE >= totalCount" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="nextPage">Sau ›</button>
        </div>
      </div>
    </div>
  </div>
</template>
