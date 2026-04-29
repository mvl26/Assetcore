<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import DateInput from '@/components/common/DateInput.vue'
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  listDocumentRequests, getDocumentRequest, createDocumentRequest,
  updateDocumentRequest, deleteDocumentRequest, type DocumentRequest,
} from '@/api/imm00'
import SmartSelect from '@/components/common/SmartSelect.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
const toast = useToast()

const route = useRoute()
const router = useRouter()

const items = ref<DocumentRequest[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<DocumentRequest> & Record<string, unknown>>({})
const err = ref('')

// Filter state
const showFilters = ref(false)
const filters = ref({
  asset: (route.query.asset as string) || '',
  status: '',
  priority: '',
  search: '',
})

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: 'Open', label: 'Đang mở' },
  { value: 'In_Progress', label: 'Đang xử lý' },
  { value: 'Overdue', label: 'Quá hạn' },
  { value: 'Fulfilled', label: 'Đã hoàn thành' },
  { value: 'Cancelled', label: 'Đã hủy' },
]
const STATUS_LABEL: Record<string, string> = Object.fromEntries(STATUS_OPTIONS.map(s => [s.value, s.label]))

const PRIORITY_OPTIONS: { value: string; label: string }[] = [
  { value: 'Low', label: 'Thấp' },
  { value: 'Medium', label: 'Trung bình' },
  { value: 'High', label: 'Cao' },
  { value: 'Critical', label: 'Khẩn cấp' },
]
const PRIORITY_LABEL: Record<string, string> = Object.fromEntries(PRIORITY_OPTIONS.map(p => [p.value, p.label]))

const filteredItems = computed(() => {
  let arr = items.value
  if (filters.value.priority) arr = arr.filter(d => d.priority === filters.value.priority)
  if (filters.value.search.trim()) {
    const q = filters.value.search.trim().toLowerCase()
    arr = arr.filter(d =>
      (d.name || '').toLowerCase().includes(q)
      || (d.doc_type_required || '').toLowerCase().includes(q)
      || (d.asset_name || '').toLowerCase().includes(q)
      || (d.asset_ref || '').toLowerCase().includes(q)
      || (d.assigned_to || '').toLowerCase().includes(q),
    )
  }
  return arr
})

interface FilterChip { key: 'asset' | 'status' | 'priority' | 'search'; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.asset) chips.push({ key: 'asset', label: `Thiết bị: ${filters.value.asset}` })
  if (filters.value.status) chips.push({ key: 'status', label: STATUS_LABEL[filters.value.status] || filters.value.status })
  if (filters.value.priority) chips.push({ key: 'priority', label: `Ưu tiên: ${PRIORITY_LABEL[filters.value.priority] || filters.value.priority}` })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: FilterChip['key']) {
  filters.value[key] = ''
  if (key === 'asset') router.replace({ query: {} })
  if (key === 'asset' || key === 'status') load()
}
function resetFilters() {
  filters.value = { asset: '', status: '', priority: '', search: '' }
  router.replace({ query: {} })
  load()
}
function quickFilter(key: 'status' | 'priority' | 'asset', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  showFilters.value = false
  if (key === 'asset' || key === 'status') load()
}

async function load() {
  loading.value = true
  try {
    const r = await listDocumentRequests({
      asset: filters.value.asset || undefined,
      status: filters.value.status || undefined,
    })
    const d = r as unknown as { items: DocumentRequest[]; pagination: { total: number } }
    if (d) { items.value = d.items || []; total.value = d.pagination?.total || 0 }
  } finally { loading.value = false }
}

// Re-load when query param changes (e.g. navigating from AssetDetail)
watch(() => route.query.asset, (val) => {
  filters.value.asset = (val as string) || ''
  load()
})

function openCreate() {
  editingName.value = null
  form.value = {
    asset_ref: filters.value.asset || '',
    doc_type_required: '', doc_category: 'Legal',
    status: 'Open', priority: 'Medium',
    due_date: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
  }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getDocumentRequest(name)
  if (r) form.value = { ...(r as unknown as DocumentRequest) }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  try {
    if (editingName.value) await updateDocumentRequest(editingName.value, form.value)
    else await createDocumentRequest(form.value)
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa yêu cầu "${name}"?`)) return
  try { await deleteDocumentRequest(name); await load() }
  catch (e: unknown) { toast.error((e as Error).message || 'Không thể xóa') }
}

function statusColor(s?: string) {
  return s === 'Fulfilled' ? 'bg-green-100 text-green-700'
    : s === 'Overdue' ? 'bg-red-100 text-red-700'
    : s === 'In_Progress' ? 'bg-blue-100 text-blue-700'
    : s === 'Cancelled' ? 'bg-gray-100 text-gray-500'
    : 'bg-yellow-100 text-yellow-700'
}
function prioColor(p?: string) {
  return p === 'Critical' ? 'text-red-600 font-semibold'
    : p === 'High' ? 'text-orange-600' : 'text-gray-600'
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Yêu cầu Hồ sơ</h1>
        <p class="text-sm text-slate-500 mt-1">Tổng <strong class="text-slate-700">{{ total }}</strong> yêu cầu</p>
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
          Thêm yêu cầu
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
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <div>
            <p class="block text-xs font-medium text-slate-600 mb-1">Lọc theo thiết bị</p>
            <SmartSelect v-model="filters.asset" doctype="AC Asset" placeholder="Chọn thiết bị (để trống = tất cả)" @update:model-value="load" />
          </div>
          <select v-model="filters.status" class="form-select text-sm self-end" @change="load">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
          <select v-model="filters.priority" class="form-select text-sm self-end">
            <option value="">Tất cả mức ưu tiên</option>
            <option v-for="p in PRIORITY_OPTIONS" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
        </div>
        <div class="flex gap-2">
          <input v-model="filters.search" placeholder="Tìm theo mã, loại tài liệu, thiết bị, người được giao..." class="form-input flex-1 text-sm" />
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
        </div>
      </div>
    </Transition>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span v-if="activeFilterCount > 0">
          Kết quả lọc: <strong class="text-slate-700">{{ filteredItems.length }}</strong> / {{ total }} yêu cầu
        </span>
        <span v-else>
          Hiển thị <strong class="text-slate-700">{{ filteredItems.length }}</strong> / {{ total }} yêu cầu
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="filteredItems.length === 0" class="text-center text-slate-400 py-12 text-sm">
        {{ activeFilterCount > 0 ? 'Không có yêu cầu nào phù hợp.' : 'Chưa có yêu cầu hồ sơ.' }}
      </div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại tài liệu</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Nhóm</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Ưu tiên</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Giao cho</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Hạn</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Trạng thái</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="d in filteredItems" :key="d.name" class="hover:bg-slate-50">
            <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ d.name }}</td>
            <td class="px-4 py-3">
              <button
                v-if="d.asset_ref"
                class="font-medium text-slate-800 text-left hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                @click="quickFilter('asset', d.asset_ref!)"
              >{{ d.asset_name || d.asset_ref }}</button>
              <div v-if="d.asset_name && d.asset_ref" class="text-xs text-slate-400 font-mono mt-0.5">{{ d.asset_ref }}</div>
            </td>
            <td class="px-4 py-3 font-medium">{{ d.doc_type_required }}</td>
            <td class="px-4 py-3 text-xs">{{ d.doc_category }}</td>
            <td class="px-4 py-3 text-xs">
              <button
                v-if="d.priority"
                :class="['hover:underline', prioColor(d.priority)]"
                :title="`Lọc: ${PRIORITY_LABEL[d.priority] || d.priority}`"
                @click="quickFilter('priority', d.priority!)"
              >{{ PRIORITY_LABEL[d.priority] || d.priority }}</button>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="px-4 py-3 text-xs">{{ d.assigned_to || '—' }}</td>
            <td class="px-4 py-3 text-xs">{{ d.due_date || '—' }}</td>
            <td class="px-4 py-3">
              <button
                v-if="d.status"
                :class="['text-xs px-2 py-0.5 rounded font-medium hover:ring-2 hover:ring-current/50', statusColor(d.status)]"
                :title="`Lọc: ${STATUS_LABEL[d.status] || d.status}`"
                @click="quickFilter('status', d.status!)"
              >{{ STATUS_LABEL[d.status] || d.status }}</button>
            </td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="openEdit(d.name)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="remove(d.name)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[560px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} Yêu cầu Hồ sơ</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị (AC Asset) <span class="text-red-500">*</span></label>
            <SmartSelect v-model="form.asset_ref as string" doctype="AC Asset" placeholder="Chọn thiết bị..." />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Loại tài liệu yêu cầu <span class="text-red-500">*</span></label>
            <input v-model="form.doc_type_required" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Nhóm</label>
            <select v-model="form.doc_category" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option>Legal</option><option>Technical</option><option>Certification</option>
              <option>Training</option><option>QA</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Ưu tiên</label>
            <select v-model="form.priority" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Low">Thấp</option>
              <option value="Medium">Trung bình</option>
              <option value="High">Cao</option>
              <option value="Critical">Khẩn cấp</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Giao cho</label>
            <SmartSelect v-model="form.assigned_to as string" doctype="User" placeholder="Chọn người dùng..." />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hạn xử lý <span class="text-red-500">*</span></label>
            <DateInput v-model="form.due_date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Trạng thái</label>
            <select v-model="form.status" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Open">Đang mở</option>
              <option value="In_Progress">Đang xử lý</option>
              <option value="Overdue">Quá hạn</option>
              <option value="Fulfilled">Đã hoàn thành</option>
              <option value="Cancelled">Đã hủy</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
            <textarea v-model="form.request_note" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
          </div>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg" @click="showForm = false">Hủy</button>
          <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg" @click="save">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
