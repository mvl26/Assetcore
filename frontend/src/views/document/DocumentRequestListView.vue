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
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'
const toast = useToast()

const route = useRoute()
const router = useRouter()

const items = ref<DocumentRequest[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<DocumentRequest> & Record<string, unknown>>({})
// `err` = lỗi của HỘP THOẠI lưu biểu mẫu — TUYỆT ĐỐI không nối vào khuôn danh sách
// (INV-UX3-13: một lần lưu hỏng sẽ xoá trắng cả bảng).
const err = ref('')
// AC-UX-047 (lô 1) — lỗi của LƯỢT NẠP danh sách (trước đây `load()` không có `catch`
// ⇒ API hỏng in «Chưa có yêu cầu hồ sơ.»).
const loadError = ref<string | null>(null)

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

const CATEGORY_LABEL: Record<string, string> = {
  Legal: 'Pháp lý', Technical: 'Kỹ thuật', Certification: 'Kiểm định',
  Training: 'Đào tạo', QA: 'Chất lượng',
}

// Lọc SERVER-SIDE: BE list_document_requests áp asset/status/priority/search +
// phân trang. KHÔNG lọc client trên trang bị cắt (bug cũ: priority/search chỉ lọc
// 20 dòng đầu).
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

function clearChip(key: string) {
  (filters.value as Record<string, unknown>)[key] = ''
  if (key === 'asset') router.replace({ query: {} })
}
function resetFilters() {
  filters.value = { asset: '', status: '', priority: '', search: '' }
  router.replace({ query: {} })
}
function quickFilter(key: 'status' | 'priority' | 'asset', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  showFilters.value = false
}

const emptyTitle = computed(() =>
  activeFilterCount.value > 0 ? 'Không có yêu cầu nào phù hợp' : 'Chưa có yêu cầu hồ sơ nào')
const EMPTY_HINT = 'Hãy tạo yêu cầu hồ sơ mới hoặc xoá bộ lọc để xem tất cả.'

const page = ref(1)
const PAGE_SIZE = 20
async function load() {
  loading.value = true
  loadError.value = null                       // INV-UX3-4 — xoá lỗi ĐẦU lượt
  try {
    const d = await listDocumentRequests({
      page: page.value, page_size: PAGE_SIZE,
      asset: filters.value.asset || undefined,
      status: filters.value.status || undefined,
      priority: filters.value.priority || undefined,
      search: filters.value.search.trim() || undefined,
    })
    items.value = d.items || []; total.value = d.total || 0
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : String(e)
    items.value = []; total.value = 0          // INV-UX3-5
  } finally { loading.value = false }
}
// Mọi đổi filter (asset/status/priority/search) → về trang 1 + reload server (debounce cho search).
let filterTimer: ReturnType<typeof setTimeout>
watch(filters, () => {
  clearTimeout(filterTimer)
  filterTimer = setTimeout(() => { page.value = 1; load() }, 300)
}, { deep: true })
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; load() } }

// Điều hướng từ AssetDetail (?asset=...) → cập nhật filter (deep watcher tự reload).
watch(() => route.query.asset, (val) => {
  filters.value.asset = (val as string) || ''
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
  form.value = { ...r }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  try {
    if (editingName.value) await updateDocumentRequest(editingName.value, form.value)
    else await createDocumentRequest(form.value)
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = e instanceof Error ? e.message : 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa yêu cầu "${name}"?`)) return
  try { await deleteDocumentRequest(name); await load() }
  catch (e: unknown) { toast.error(e instanceof Error ? e.message : 'Không thể xóa') }
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
  <!-- AC-UX-047 (lô 1) — khuôn 4 trạng thái loại trừ (ui/ListPageShell). -->
  <ListPageShell
    :loading="loading"
    :error-message="loadError"
    :is-empty="!items.length"
    :empty-title="emptyTitle"
    :empty-hint="EMPTY_HINT"
    @retry="load">
    <template #header>
      <PageHeader
        title="Yêu cầu Hồ sơ"
        :subtitle="`Tổng ${total} yêu cầu`"
      >
        <template #actions>
          <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
          <button class="btn-primary shrink-0" @click="openCreate">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Thêm yêu cầu
          </button>
        </template>
      </PageHeader>
    </template>

    <template #filters>
      <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="filters.search"
      search-placeholder="Tìm theo mã, loại tài liệu, thiết bị, người được giao..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="load"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Lọc theo thiết bị</label>
          <SmartSelect v-model="filters.asset" doctype="AC Asset" placeholder="Chọn thiết bị (để trống = tất cả)" @update:model-value="load" />
        </div>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.status" class="form-select text-sm" @change="load">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Mức ưu tiên</label>
          <select v-model="filters.priority" class="form-select text-sm">
            <option value="">Tất cả mức ưu tiên</option>
            <option v-for="p in PRIORITY_OPTIONS" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
        </div>
      </template>
      </ListFilterBar>
    </template>

    <template #skeleton>
      <SkeletonLoader variant="table" :rows="6" />
    </template>

    <template #empty-action>
      <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
        Xóa bộ lọc để xem tất cả
      </button>
    </template>

    <template #toolbar>
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span v-if="activeFilterCount > 0">
          Kết quả lọc: <strong class="text-slate-700">{{ items.length }}</strong> / {{ total }} yêu cầu
        </span>
        <span v-else>
          Hiển thị <strong class="text-slate-700">{{ items.length }}</strong> / {{ total }} yêu cầu
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
    </template>

    <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="d in items"
            :key="d.name"
            class="mobile-card"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ d.name }}</span>
              <span v-if="d.status" :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', statusColor(d.status)]">
                {{ STATUS_LABEL[d.status] || d.status }}
              </span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ d.doc_type_required }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="d.asset_name || d.asset_ref">{{ d.asset_name || d.asset_ref }}</span>
              <span v-if="d.priority">· <span :class="prioColor(d.priority)">{{ PRIORITY_LABEL[d.priority] || d.priority }}</span></span>
              <span v-if="d.due_date">· Hạn: {{ d.due_date }}</span>
            </div>
            <div class="flex gap-2 mt-2">
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click.stop="openEdit(d.name)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click.stop="remove(d.name)">Xóa</button>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <table class="hidden sm:table w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="table-header">Mã</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Loại tài liệu</th>
              <th class="table-header">Nhóm</th>
              <th class="table-header">Ưu tiên</th>
              <th class="table-header">Giao cho</th>
              <th class="table-header">Hạn</th>
              <th class="table-header">Trạng thái</th>
              <th class="px-4 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="d in items" :key="d.name" class="hover:bg-slate-50">
              <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ d.name }}</td>
              <td class="px-4 py-3">
                <button
                  v-if="d.asset_ref"
                  class="font-medium text-slate-800 text-left hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                  @click="quickFilter('asset', d.asset_ref!)"
                >{{ d.asset_name || d.asset_ref }}</button>
                <div v-if="d.asset_name && d.asset_ref && d.asset_name !== d.asset_ref" class="text-xs text-slate-400 font-mono mt-0.5">{{ d.asset_ref }}</div>
              </td>
              <td class="px-4 py-3 font-medium">{{ d.doc_type_required }}</td>
              <td class="px-4 py-3 text-xs">{{ d.doc_category ? (CATEGORY_LABEL[d.doc_category] ?? d.doc_category) : '—' }}</td>
              <td class="px-4 py-3 text-xs">
                <button
                  v-if="d.priority"
                  :class="['hover:underline', prioColor(d.priority)]"
                  :title="`Lọc: ${PRIORITY_LABEL[d.priority] || d.priority}`"
                  @click="quickFilter('priority', d.priority!)"
                >{{ PRIORITY_LABEL[d.priority] || d.priority }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-xs">{{ (d as any).assigned_to_name || d.assigned_to || '—' }}</td>
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

    <template #pagination>
      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} / {{ total }}</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" aria-label="Trang trước" @click="prevPage">‹</button>
          <button :disabled="page * PAGE_SIZE >= total" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" aria-label="Trang sau" @click="nextPage">›</button>
        </div>
      </div>
    </template>
  </ListPageShell>

  <!-- Hộp thoại đặt NGOÀI khuôn: mở được ở CẢ 4 trạng thái (INV-UX3-17). -->
  <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[560px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} Yêu cầu Hồ sơ</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="sm:col-span-2">
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
              <option value="Legal">Pháp lý</option><option value="Technical">Kỹ thuật</option><option value="Certification">Kiểm định</option>
              <option value="Training">Đào tạo</option><option value="QA">Chất lượng</option>
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
            <ApproverSelect v-model="form.assigned_to as string" context="user" placeholder="Chọn người dùng..." />
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
</template>
