<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  listPmSchedules, getPmSchedule, createPmSchedule, updatePmSchedule, deletePmSchedule,
  type PmSchedule,
} from '@/api/imm00'
import { translateStatus, getStatusColor, formatDate } from '@/utils/formatters'
import SmartSelect from '@/components/common/SmartSelect.vue'
import DateInput from '@/components/common/DateInput.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { useMasterDataStore } from '@/stores/useMasterDataStore'
import { useApi } from '@/composables/useApi'

const masterStore = useMasterDataStore()
const apiCall = useApi()
const showFilters = ref(false)
const filters = ref({ pm_type: '', status: '', search: '' })

const PM_TYPES = ['Quarterly', 'Semi-Annual', 'Annual', 'Ad-hoc']
const PM_TYPE_LABEL: Record<string, string> = {
  Quarterly: 'Hàng quý', 'Semi-Annual': 'Nửa năm', Annual: 'Hàng năm', 'Ad-hoc': 'Đột xuất',
}
const STATUS_OPTIONS = ['Active', 'Paused', 'Cancelled']

interface FilterChip { key: 'pm_type' | 'status' | 'search'; label: string }
const filteredItems = computed(() => {
  let arr = items.value
  if (filters.value.pm_type) arr = arr.filter(s => s.pm_type === filters.value.pm_type)
  if (filters.value.status) arr = arr.filter(s => s.status === filters.value.status)
  if (filters.value.search.trim()) {
    const q = filters.value.search.trim().toLowerCase()
    arr = arr.filter(s =>
      (s.name || '').toLowerCase().includes(q)
      || (s.asset_ref || '').toLowerCase().includes(q)
      || (s.asset_name || '').toLowerCase().includes(q)
      || (s.asset_code || '').toLowerCase().includes(q),
    )
  }
  return arr
})
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.pm_type) chips.push({ key: 'pm_type', label: PM_TYPE_LABEL[filters.value.pm_type] || filters.value.pm_type })
  if (filters.value.status) chips.push({ key: 'status', label: translateStatus(filters.value.status) })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)
function quickFilter(key: 'pm_type' | 'status', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  showFilters.value = false
}
function clearChip(key: FilterChip['key']) { filters.value[key] = '' }
function resetFilters() { filters.value = { pm_type: '', status: '', search: '' } }

// Default chu kỳ (ngày) theo loại PM — gợi ý cho form, user có thể override.
const PM_TYPE_INTERVAL: Record<string, number> = {
  Quarterly: 90,
  'Semi-Annual': 180,
  Annual: 365,
  'Ad-hoc': 0,
}

const items = ref<PmSchedule[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 30
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<PmSchedule> & Record<string, unknown>>({})
const err = ref('')

const loadError = ref<string | null>(null)

async function load() {
  loading.value = true
  loadError.value = null
  // silentError: lỗi load list render fallback "Thử lại" inline; vẫn toast nhẹ.
  const res = await apiCall.run(() => Promise.all([
    listPmSchedules({ page: page.value, page_size: PAGE_SIZE }),
    masterStore.fetchDoctype('AC Asset'),
    masterStore.fetchDoctype('User'),
    masterStore.fetchDoctype('PM Checklist Template'),
  ]), { errorMessage: 'Không tải được danh sách lịch PM' })
  loading.value = false

  if (res === null) {
    loadError.value = apiCall.lastError.value?.message || 'Không tải được dữ liệu'
    return
  }
  const d = res[0] as unknown as { items: PmSchedule[]; total: number }
  if (d) { items.value = d.items || []; total.value = d.total || 0 }
}

function openCreate() {
  editingName.value = null
  form.value = {
    asset_ref: '', pm_type: 'Quarterly', status: 'Active',
    pm_interval_days: 90, alert_days_before: 7, notes: '',
    checklist_template: '', responsible_technician: '', last_pm_date: '',
  }
  err.value = ''; showForm.value = true
}

// Khi đổi loại PM → gợi ý chu kỳ tương ứng (giữ nguyên nếu user đã đổi thủ công).
watch(() => form.value.pm_type, (newType, oldType) => {
  if (!newType || !oldType) return
  const oldDefault = PM_TYPE_INTERVAL[oldType as string]
  if (form.value.pm_interval_days === oldDefault) {
    const next = PM_TYPE_INTERVAL[newType as string]
    if (next) form.value.pm_interval_days = next
  }
})

function technicianLabel(id?: string): string {
  if (!id) return '—'
  return masterStore.getItemById('User', id)?.name || id
}

const fieldErrors = ref<Record<string, string>>({})

async function openEdit(name: string) {
  err.value = ''
  fieldErrors.value = {}
  editingName.value = name
  const r = await apiCall.run(() => getPmSchedule(name),
    { errorMessage: 'Không tải được lịch PM' })
  if (r) {
    form.value = { ...(r as unknown as PmSchedule) }
    showForm.value = true
  }
}

const saving = ref(false)

async function save() {
  err.value = ''
  fieldErrors.value = {}
  if (!form.value.asset_ref) { err.value = 'Vui lòng chọn thiết bị.'; return }
  if (!form.value.checklist_template) { err.value = 'Vui lòng chọn template checklist.'; return }
  if (!form.value.pm_interval_days || (form.value.pm_interval_days as number) < 0) {
    err.value = 'Chu kỳ (ngày) phải lớn hơn hoặc bằng 0.'; return
  }
  saving.value = true
  const ok = await apiCall.run(
    () => editingName.value
      ? updatePmSchedule(editingName.value, form.value)
      : createPmSchedule(form.value),
    {
      successMessage: editingName.value ? 'Đã cập nhật lịch PM' : 'Đã tạo lịch PM mới',
      onFieldError: (fields) => { fieldErrors.value = fields },
    },
  )
  saving.value = false
  if (ok) {
    showForm.value = false
    await load()
  } else {
    err.value = apiCall.lastError.value?.message || 'Lỗi lưu'
  }
}

async function remove(name: string) {
  if (!confirm(`Xóa lịch PM "${name}"?`)) return
  await apiCall.run(() => deletePmSchedule(name), {
    successMessage: `Đã xóa lịch PM "${name}"`,
    errorMessage: 'Không thể xóa lịch PM',
  })
  if (apiCall.lastError.value === null) await load()
}

function overdueColor(d?: string) {
  if (!d) return 'text-gray-400'
  const days = Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
  return days < 0 ? 'text-red-600 font-semibold' : days < 14 ? 'text-yellow-600' : 'text-gray-600'
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Lịch bảo trì định kỳ</h1>
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
          Thêm lịch PM
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
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
          <select v-model="filters.pm_type" class="form-select text-sm">
            <option value="">Tất cả loại PM</option>
            <option v-for="t in PM_TYPES" :key="t" :value="t">{{ PM_TYPE_LABEL[t] || t }}</option>
          </select>
          <select v-model="filters.status" class="form-select text-sm">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">{{ translateStatus(s) }}</option>
          </select>
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
          Kết quả lọc: <strong class="text-slate-700">{{ filteredItems.length }}</strong> / {{ items.length }} lịch
        </span>
        <span v-else>
          Hiển thị <strong class="text-slate-700">{{ filteredItems.length }}</strong> / {{ total }} lịch
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="loadError" class="text-center py-12 px-6">
        <div class="text-3xl mb-2">⚠️</div>
        <p class="text-sm text-red-700 mb-4">{{ loadError }}</p>
        <button class="btn-primary" @click="load">Thử lại</button>
      </div>
      <div v-else-if="filteredItems.length === 0" class="text-center py-12 px-6">
        <div class="text-3xl mb-2 text-slate-300">📋</div>
        <p class="text-sm text-slate-500 mb-4">
          {{ activeFilterCount > 0 ? 'Không có lịch PM nào phù hợp với bộ lọc.' : 'Chưa có lịch PM nào.' }}
        </p>
        <button v-if="activeFilterCount > 0" class="btn-ghost" @click="resetFilters">Xóa bộ lọc</button>
        <button v-else class="btn-primary" @click="openCreate">+ Thêm lịch PM</button>
      </div>
      <div v-else class="overflow-x-auto">
<table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại PM</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Chu kỳ (ngày)</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">KTV</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Lần trước</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Kế tiếp</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Trạng thái</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="s in filteredItems" :key="s.name" class="hover:bg-slate-50">
            <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ s.name }}</td>
            <td class="px-4 py-3">
              <div class="font-medium text-slate-900 truncate max-w-[240px]">
                {{ s.asset_name || s.asset_code || s.asset_ref }}
              </div>
              <div v-if="s.asset_name && (s.asset_code || s.asset_ref)" class="text-xs text-slate-500 font-mono">
                {{ s.asset_code || s.asset_ref }}
              </div>
            </td>
            <td class="px-4 py-3">
              <button
                v-if="s.pm_type"
                class="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-700 hover:ring-2 hover:ring-slate-400"
                :title="`Lọc: ${PM_TYPE_LABEL[s.pm_type] || s.pm_type}`"
                @click="quickFilter('pm_type', s.pm_type!)"
              >{{ PM_TYPE_LABEL[s.pm_type] || s.pm_type }}</button>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="px-4 py-3">{{ s.pm_interval_days }}</td>
            <td class="px-4 py-3 text-xs text-slate-600">{{ technicianLabel(s.responsible_technician) }}</td>
            <td class="px-4 py-3 text-xs text-slate-600">{{ formatDate(s.last_pm_date) }}</td>
            <td class="px-4 py-3 text-xs" :class="overdueColor(s.next_due_date)">{{ formatDate(s.next_due_date) }}</td>
            <td class="px-4 py-3">
              <button
                v-if="s.status"
                :class="['inline-block px-2 py-0.5 rounded-full text-xs font-medium hover:ring-2 hover:ring-current/50', getStatusColor(s.status)]"
                :title="`Lọc: ${translateStatus(s.status)}`"
                @click="quickFilter('status', s.status!)"
              >{{ translateStatus(s.status) }}</button>
              <span v-else class="text-slate-400">—</span>
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

    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[560px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} lịch bảo trì</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị (AC Asset) *</label>
            <SmartSelect
              v-model="(form.asset_ref as string)"
              doctype="AC Asset"
              :has-error="!!fieldErrors.asset_ref"
              placeholder="Tìm theo tên / mã / serial..."
            />
            <p v-if="fieldErrors.asset_ref" class="text-xs text-red-600 mt-1">{{ fieldErrors.asset_ref }}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Loại PM *</label>
            <select v-model="form.pm_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Quarterly">Quarterly — 3 tháng</option>
              <option value="Semi-Annual">Semi-Annual — 6 tháng</option>
              <option value="Annual">Annual — 12 tháng</option>
              <option value="Ad-hoc">Ad-hoc</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Chu kỳ (ngày) *</label>
            <input v-model.number="form.pm_interval_days" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Template checklist *</label>
            <SmartSelect
              v-model="(form.checklist_template as string)"
              doctype="PM Checklist Template"
              :has-error="!!fieldErrors.checklist_template"
              placeholder="Chọn template (PMCT-...)"
            />
            <p v-if="fieldErrors.checklist_template" class="text-xs text-red-600 mt-1">{{ fieldErrors.checklist_template }}</p>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">KTV phụ trách</label>
            <SmartSelect
              v-model="(form.responsible_technician as string)"
              doctype="User"
              placeholder="Tìm theo tên / email..."
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Ngày PM gần nhất</label>
            <DateInput v-model="(form.last_pm_date as string)" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Cảnh báo trước (ngày)</label>
            <input v-model.number="form.alert_days_before" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Trạng thái</label>
            <select v-model="form.status" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Active">Đang hoạt động</option>
              <option value="Paused">Tạm dừng</option>
              <option value="Suspended">Đình chỉ</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
            <textarea v-model="form.notes" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
          </div>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg" :disabled="saving" @click="showForm = false">Hủy</button>
          <button
            class="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg inline-flex items-center gap-2"
            :disabled="saving"
            @click="save"
          >
            <svg v-if="saving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
              <path fill="currentColor" class="opacity-75" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            {{ saving ? 'Đang lưu...' : 'Lưu' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
