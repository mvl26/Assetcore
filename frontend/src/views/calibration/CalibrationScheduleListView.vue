<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import DateInput from '@/components/common/DateInput.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  listCalibrationSchedules, createCalibrationSchedule,
  updateCalibrationSchedule, deleteCalibrationSchedule,
} from '@/api/imm11'
import type { CalibrationSchedule } from '@/api/imm11'
import SmartSelect from '@/components/common/SmartSelect.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { formatAssetDisplay, formatDate } from '@/utils/formatters'
const toast = useToast()

const router = useRouter()
const items = ref<CalibrationSchedule[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const err = ref('')

// Filters
const showFilters = ref(false)
const filters = ref({ calibration_type: '', is_active: '' as '' | '1' | '0', overdue_only: false, search: '' })

const TYPE_LABEL: Record<string, string> = { External: 'Bên ngoài', 'In-House': 'Nội bộ' }

interface FilterChip { key: 'calibration_type' | 'is_active' | 'overdue_only' | 'search'; label: string }
const filteredItems = computed(() => {
  let arr = items.value
  if (filters.value.calibration_type) arr = arr.filter(s => s.calibration_type === filters.value.calibration_type)
  if (filters.value.is_active === '1') arr = arr.filter(s => s.is_active === 1)
  if (filters.value.is_active === '0') arr = arr.filter(s => s.is_active === 0)
  if (filters.value.overdue_only) arr = arr.filter(s => s.next_due_date && new Date(s.next_due_date) < new Date())
  if (filters.value.search.trim()) {
    const q = filters.value.search.trim().toLowerCase()
    arr = arr.filter(s =>
      (s.name || '').toLowerCase().includes(q)
      || (s.asset || '').toLowerCase().includes(q)
      || (s.asset_name || '').toLowerCase().includes(q),
    )
  }
  return arr
})
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.calibration_type) chips.push({ key: 'calibration_type', label: TYPE_LABEL[filters.value.calibration_type] || filters.value.calibration_type })
  if (filters.value.is_active === '1') chips.push({ key: 'is_active', label: 'Đang hoạt động' })
  if (filters.value.is_active === '0') chips.push({ key: 'is_active', label: 'Tạm dừng' })
  if (filters.value.overdue_only) chips.push({ key: 'overdue_only', label: 'Quá hạn' })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)
function quickFilter(key: 'calibration_type', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  showFilters.value = false
}
function clearChip(key: FilterChip['key']) {
  if (key === 'is_active') filters.value.is_active = ''
  else if (key === 'overdue_only') filters.value.overdue_only = false
  else (filters.value as Record<string, unknown>)[key] = ''
}
function resetFilters() {
  filters.value = { calibration_type: '', is_active: '', overdue_only: false, search: '' }
}

const form = ref<Partial<CalibrationSchedule>>({
  calibration_type: 'External',
  interval_days: 365,
  is_active: 1,
})

async function load() {
  loading.value = true
  try {
    const res = await listCalibrationSchedules({}, 1, 50)
    items.value = res.data || []
    total.value = res.pagination?.total || 0
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = { calibration_type: 'External', interval_days: 365, is_active: 1 }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const sched = items.value.find(i => i.name === name)
  if (sched) form.value = { ...sched }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  try {
    if (editingName.value) {
      await updateCalibrationSchedule(editingName.value, form.value)
    } else {
      await createCalibrationSchedule(form.value)
    }
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa lịch "${name}"?`)) return
  try { await deleteCalibrationSchedule(name); await load() }
  catch (e: unknown) { toast.error((e as Error).message || 'Không thể xóa') }
}

function isOverdue(date: string | null) {
  return date && new Date(date) < new Date()
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-4">
      <div>
        <div class="flex items-center gap-2 text-xs text-slate-500 mb-1">
          <button class="hover:text-blue-600 hover:underline" @click="router.push('/calibration')">Phiếu hiệu chuẩn</button>
          <span class="text-slate-300">/</span>
          <span class="text-slate-700 font-medium">Lịch hiệu chuẩn</span>
        </div>
        <h1 class="text-2xl font-bold text-slate-900">Lịch hiệu chuẩn</h1>
        <p class="text-sm text-slate-500 mt-1">Tổng <strong class="text-slate-700">{{ total }}</strong> lịch</p>
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
          <span v-if="activeFilterCount > 0" class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-blue-500 text-white">
            {{ activeFilterCount }}
          </span>
          <svg class="w-3.5 h-3.5 transition-transform" :class="showFilters ? 'rotate-180' : ''" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button class="btn-primary shrink-0" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm lịch
        </button>
      </div>
    </div>

    <!-- Active chips -->
    <div v-if="activeChips.length > 0 && !showFilters" class="flex flex-wrap items-center gap-2 mb-4">
      <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
      <button
        v-for="chip in activeChips" :key="chip.key"
        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100"
        @click="clearChip(chip.key)"
      >
        {{ chip.label }}
        <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">Xóa tất cả</button>
    </div>

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
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <select v-model="filters.calibration_type" class="form-select text-sm">
            <option value="">Tất cả loại</option>
            <option value="External">Bên ngoài</option>
            <option value="In-House">Nội bộ</option>
          </select>
          <select v-model="filters.is_active" class="form-select text-sm">
            <option value="">Tất cả trạng thái</option>
            <option value="1">Đang hoạt động</option>
            <option value="0">Tạm dừng</option>
          </select>
          <label class="flex items-center gap-2 text-sm text-slate-700 px-2">
            <input v-model="filters.overdue_only" type="checkbox" />
            Chỉ quá hạn
          </label>
        </div>
        <div class="flex gap-2">
          <input v-model="filters.search" placeholder="Tìm theo mã, tên thiết bị..." class="form-input flex-1 text-sm" />
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
        </div>
      </div>
    </Transition>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span v-if="activeFilterCount > 0">
          Kết quả lọc: <strong class="text-slate-700">{{ filteredItems.length }}</strong> / {{ total }} lịch
        </span>
        <span v-else>
          Hiển thị <strong class="text-slate-700">{{ filteredItems.length }}</strong> / {{ total }} lịch
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="filteredItems.length === 0" class="p-8 text-center text-slate-400 text-sm">
        {{ activeFilterCount > 0 ? 'Không có lịch phù hợp.' : 'Chưa có lịch hiệu chuẩn.' }}
      </div>
      <div v-else class="overflow-x-auto">
<table class="w-full text-sm">
        <thead class="bg-slate-50 border-b">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Chu kỳ</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Ngày đến hạn</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Trạng thái</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="s in filteredItems" :key="s.name" class="hover:bg-slate-50">
            <td class="px-4 py-3 font-mono text-xs text-slate-400">{{ s.name }}</td>
            <td class="px-4 py-3">
              <div class="font-medium text-slate-900 truncate max-w-[240px]">
                {{ formatAssetDisplay(s.asset_name, s.asset).main }}
              </div>
              <div v-if="formatAssetDisplay(s.asset_name, s.asset).hasBoth" class="text-xs text-slate-400 font-mono">
                {{ formatAssetDisplay(s.asset_name, s.asset).sub }}
              </div>
            </td>
            <td class="px-4 py-3">
              <button
                v-if="s.calibration_type"
                class="text-xs px-2 py-0.5 rounded-full font-medium bg-purple-100 text-purple-700 hover:ring-2 hover:ring-purple-400"
                :title="`Lọc: ${TYPE_LABEL[s.calibration_type] || s.calibration_type}`"
                @click="quickFilter('calibration_type', s.calibration_type!)"
              >{{ TYPE_LABEL[s.calibration_type] || s.calibration_type }}</button>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="px-4 py-3">{{ s.interval_days }} ngày</td>
            <td class="px-4 py-3 text-xs" :class="isOverdue(s.next_due_date) ? 'text-red-600 font-semibold' : ''">
              {{ formatDate(s.next_due_date) }}
            </td>
            <td class="px-4 py-3">
              <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
                {{ s.is_active ? 'Hoạt động' : 'Tạm dừng' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="openEdit(s.name)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="remove(s.name)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <!-- Form Modal -->
    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[520px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} Lịch Hiệu chuẩn</h2>
        <div v-if="err" class="alert-error text-sm">{{ err }}</div>
        <div class="space-y-3">
          <div v-if="!editingName">
            <label class="form-label">Thiết bị *</label>
            <SmartSelect v-model="form.asset" doctype="AC Asset" placeholder="Tìm thiết bị..." />
          </div>
          <div>
            <label class="form-label">Loại hiệu chuẩn</label>
            <select v-model="form.calibration_type" class="form-select w-full text-sm">
              <option value="External">External</option>
              <option value="In-House">In-House</option>
            </select>
          </div>
          <div>
            <label class="form-label">Chu kỳ (ngày)</label>
            <input v-model.number="form.interval_days" type="number" min="1" class="form-input w-full text-sm" />
          </div>
          <div>
            <label class="form-label">Ngày đến hạn tiếp theo</label>
            <DateInput v-model="form.next_due_date" class="form-input w-full text-sm" />
          </div>
          <div>
            <label class="form-label">Lab ưu tiên</label>
            <SmartSelect v-model="(form.preferred_lab as string | undefined)" doctype="AC Supplier" placeholder="Tìm lab..." />
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0" />
            Đang hoạt động
          </label>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button class="btn-ghost text-sm" @click="showForm = false">Huỷ</button>
          <button class="btn-primary text-sm" @click="save">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
