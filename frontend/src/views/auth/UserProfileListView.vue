<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { listUsers, getAvailableImmRoles, type IMMUserListItem, type ImmRoleOption } from '@/api/user'
import {
  initImportFolders, previewRefImport, importRefData, buildErrorReport,
  getExportUrl, getTemplateUrl,
} from '@/api/importData'
import type { ImportPreviewResult, ImportResult, ImportStep } from '@/types/import'
import api from '@/api/axios'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

const router = useRouter()
const auth = useAuthStore()

const users = ref<IMMUserListItem[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const PAGE_SIZE = 20

// Filter state
const showFilters = ref(false)
const filters = ref({ search: '', approval_status: '', department: '', role: '' })
const availableRoles = ref<ImmRoleOption[]>([])

interface FilterChip { key: 'search' | 'approval_status' | 'department' | 'role'; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.approval_status) {
    chips.push({ key: 'approval_status', label: APPROVAL_LABELS[filters.value.approval_status] || filters.value.approval_status })
  }
  if (filters.value.department) chips.push({ key: 'department', label: filters.value.department })
  if (filters.value.role) {
    chips.push({ key: 'role', label: availableRoles.value.find(r => r.name === filters.value.role)?.label || filters.value.role })
  }
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)
function clearChip(key: string) { (filters.value as Record<string, string>)[key] = ''; load() }
function resetFilters() { filters.value = { search: '', approval_status: '', department: '', role: '' }; load() }
function quickFilter(key: 'approval_status', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  showFilters.value = false
  load()
}

const APPROVAL_COLORS: Record<string, string> = {
  Approved: 'bg-green-100 text-green-700',
  Pending: 'bg-amber-100 text-amber-700',
  Rejected: 'bg-red-100 text-red-700',
}
const APPROVAL_LABELS: Record<string, string> = {
  Approved: 'Đã duyệt', Pending: 'Chờ duyệt', Rejected: 'Từ chối',
}
const ROLE_GROUP_COLORS: Record<string, string> = {
  Governance:  'bg-purple-100 text-purple-700',
  Department:  'bg-blue-100 text-blue-700',
  Engineering: 'bg-emerald-100 text-emerald-700',
  Support:     'bg-amber-100 text-amber-700',
}

async function load() {
  loading.value = true
  const res = await listUsers({
    search: filters.value.search,
    approval_status: filters.value.approval_status,
    department: filters.value.department || undefined,
    role: filters.value.role || undefined,
    page: page.value,
    page_size: PAGE_SIZE,
  })
  loading.value = false
  if (res) {
    users.value = res.items ?? []
    total.value = res.pagination?.total ?? 0
  }
}

function applyFilters() { page.value = 1; load() }
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; load() } }

onMounted(async () => {
  availableRoles.value = (await getAvailableImmRoles()) ?? []
  await load()
})

// ── Import / Export ──────────────────────────────────────────────────────────

const showImport = ref(false)
const importStep = ref<ImportStep>('upload')
const uploading = ref(false)
const importLoading = ref(false)
const uploadedFileUrl = ref('')
const uploadedFileName = ref('')
const importFolder = ref('Home/Attachments')
const previewData = ref<ImportPreviewResult | null>(null)
const importResult = ref<ImportResult | null>(null)
const importErr = ref('')
const isDragOver = ref(false)

const hasBlockingErrors = computed(
  () => (previewData.value?.errors ?? []).some(e => e.severity === 'error'),
)

async function openImport() {
  showImport.value = true
  importStep.value = 'upload'
  uploadedFileUrl.value = ''
  uploadedFileName.value = ''
  previewData.value = null
  importResult.value = null
  importErr.value = ''
  try {
    importFolder.value = await initImportFolders('User')
  } catch {
    importFolder.value = 'Home/Attachments'
  }
}

function closeImport() {
  showImport.value = false
  if (importStep.value === 'result' && (importResult.value?.success ?? 0) > 0) load()
}

async function handleFileChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) await _uploadAndPreview(file)
}

async function handleDrop(event: DragEvent) {
  isDragOver.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) await _uploadAndPreview(file)
}

async function _uploadAndPreview(file: File) {
  uploading.value = true
  importErr.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('is_private', '1')
    fd.append('folder', importFolder.value)
    const res = await api.post<{ message: { file_url: string } }>(
      '/api/method/upload_file', fd,
      { headers: { 'Content-Type': undefined as unknown as string } },
    )
    uploadedFileUrl.value = res.data.message.file_url
    uploadedFileName.value = file.name
    uploading.value = false
    importLoading.value = true
    previewData.value = await previewRefImport('User', uploadedFileUrl.value)
    importStep.value = 'preview'
  } catch (e: unknown) {
    importErr.value = e instanceof Error ? e.message : 'Lỗi upload hoặc đọc file'
  } finally {
    uploading.value = false
    importLoading.value = false
  }
}

async function runImport() {
  importLoading.value = true
  importErr.value = ''
  try {
    importResult.value = await importRefData('User', uploadedFileUrl.value)
    importStep.value = 'result'
  } catch (e: unknown) {
    importErr.value = e instanceof Error ? e.message : 'Lỗi import'
  } finally {
    importLoading.value = false
  }
}

async function downloadErrorReport() {
  try {
    const r = await buildErrorReport('User', uploadedFileUrl.value)
    globalThis.open(r.fileUrl, '_blank')
  } catch {
    importErr.value = 'Không tạo được báo cáo lỗi'
  }
}

function doExport() { globalThis.location.href = getExportUrl('User') }
function doDownloadTemplate() { globalThis.location.href = getTemplateUrl('User') }
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader title="Quản lý người dùng" :subtitle="`Tổng ${total} người dùng`">
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button
          v-if="auth.isSystemAdmin"
          class="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 flex items-center gap-1.5"
          title="Xuất danh sách người dùng về Excel"
          @click="doExport"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Xuất Excel
        </button>
        <button
          v-if="auth.isSystemAdmin"
          class="px-3 py-2 text-sm border border-emerald-300 rounded-lg hover:bg-emerald-50 text-emerald-700 flex items-center gap-1.5"
          @click="openImport"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Import
        </button>
        <button
          v-if="auth.isSystemAdmin"
          class="btn-primary shrink-0"
          @click="router.push('/user-profiles/new')"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm người dùng
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="filters.search"
      search-placeholder="Tìm theo tên, email..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái duyệt</label>
          <select v-model="filters.approval_status" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả trạng thái</option>
            <option value="Approved">Đã duyệt</option>
            <option value="Pending">Chờ duyệt</option>
            <option value="Rejected">Từ chối</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Khoa / Phòng</label>
          <SmartSelect
            v-model="filters.department"
            doctype="AC Department"
            placeholder="Tất cả khoa/phòng..."
            @select="applyFilters"
            @clear="applyFilters"
          />
        </div>
        <div class="form-group">
          <label class="form-label">Vai trò</label>
          <select v-model="filters.role" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả vai trò</option>
            <option v-for="r in availableRoles" :key="r.name" :value="r.name">{{ r.label }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span v-if="activeFilterCount > 0">
          Kết quả lọc: <strong class="text-slate-700">{{ users.length }}</strong> / {{ total }} người dùng
        </span>
        <span v-else>
          Hiển thị <strong class="text-slate-700">{{ users.length }}</strong> / {{ total }} người dùng
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="users.length === 0" class="text-center text-slate-400 py-12 text-sm">
        {{ activeFilterCount > 0 ? 'Không có người dùng nào phù hợp.' : 'Không có dữ liệu.' }}
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="u in users"
            :key="u.name"
            class="mobile-card"
            @click="router.push(`/user-profiles/${encodeURIComponent(u.name)}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700 truncate max-w-[60%]">{{ u.name }}</span>
              <span
                class="text-xs px-2 py-0.5 rounded-full font-medium"
                :class="APPROVAL_COLORS[u.imm_approval_status ?? ''] ?? 'bg-gray-100 text-gray-600'"
              >{{ APPROVAL_LABELS[u.imm_approval_status ?? ''] ?? u.imm_approval_status ?? '—' }}</span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ u.full_name || u.name }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ u.email || u.name }}</span>
              <span v-if="u.department_name">· {{ u.department_name }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Họ và tên</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden md:table-cell">Khoa/Phòng</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vai trò</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trạng thái</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr
v-for="u in users" :key="u.name"
                class="hover:bg-gray-50 cursor-pointer"
                @click="router.push(`/user-profiles/${encodeURIComponent(u.name)}`)">
              <td class="px-4 py-3 font-medium text-gray-900">
                {{ u.full_name || u.name }}
              </td>
              <td class="px-4 py-3 text-gray-600 text-xs">{{ u.email || u.name }}</td>
              <td class="px-4 py-3 text-gray-600 text-xs hidden md:table-cell">
                {{ u.department_name || '—' }}
              </td>
              <td class="px-4 py-3">
                <div v-if="u.imm_roles?.length" class="flex flex-wrap gap-1">
                  <span
v-for="r in u.imm_roles" :key="r.name"
                        :title="r.name"
                        class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium"
                        :class="ROLE_GROUP_COLORS[r.group] ?? 'bg-gray-100 text-gray-600'">
                    {{ r.label }}
                  </span>
                </div>
                <span v-else class="text-xs text-gray-300">Chưa gán</span>
              </td>
              <td class="px-4 py-3">
                <button
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium hover:ring-2 hover:ring-current/50"
                  :class="APPROVAL_COLORS[u.imm_approval_status ?? ''] ?? 'bg-gray-100 text-gray-600'"
                  :title="`Lọc: ${APPROVAL_LABELS[u.imm_approval_status ?? ''] ?? u.imm_approval_status}`"
                  @click.stop="u.imm_approval_status && quickFilter('approval_status', u.imm_approval_status)"
                >
                  {{ APPROVAL_LABELS[u.imm_approval_status ?? ''] ?? u.imm_approval_status ?? '—' }}
                </button>
              </td>
              <td class="px-4 py-3">
                <button
class="text-blue-600 hover:underline text-xs"
                        @click.stop="router.push(`/user-profiles/${encodeURIComponent(u.name)}`)">
                  Xem / Sửa
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        </div>
      </template>

      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-gray-200 text-sm text-gray-600">
        <span>Trang {{ page }} · {{ total }} người dùng</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40" @click="prevPage">← Trước</button>
          <button :disabled="page * PAGE_SIZE >= total" class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40" @click="nextPage">Sau →</button>
        </div>
      </div>
    </div>

    <!-- ── Import Modal ──────────────────────────────────────────────────── -->
    <div
      v-if="showImport"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="closeImport"
    >
      <div class="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 class="text-base font-semibold text-gray-800">Import người dùng</h2>
            <p class="text-xs text-gray-500 mt-0.5">
              {{ importStep === 'upload' ? 'Tải file Excel / CSV lên' : importStep === 'preview' ? 'Kiểm tra dữ liệu trước khi import' : 'Kết quả import' }}
            </p>
          </div>
          <button class="text-gray-400 hover:text-gray-600 p-1" @click="closeImport">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex gap-0 border-b border-gray-100">
          <div v-for="(label, idx) in ['1. Upload', '2. Kiểm tra', '3. Kết quả']" :key="idx"
            :class="['flex-1 text-center py-2 text-xs font-medium',
              (importStep === 'upload' && idx === 0) || (importStep === 'preview' && idx === 1) || (importStep === 'result' && idx === 2)
                ? 'text-blue-600 border-b-2 border-blue-600 -mb-px'
                : 'text-gray-400']">
            {{ label }}
          </div>
        </div>

        <div class="p-6 space-y-4">
          <div v-if="importErr" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
            {{ importErr }}
          </div>

          <!-- STEP 1: UPLOAD -->
          <template v-if="importStep === 'upload'">
            <div class="flex items-center justify-between">
              <p class="text-sm text-gray-600">Tải template, điền dữ liệu rồi upload lại:</p>
              <button class="text-xs text-blue-600 hover:underline flex items-center gap-1" @click="doDownloadTemplate">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Tải template Excel
              </button>
            </div>
            <label
              :class="['block border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors',
                isDragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50']"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleDrop"
            >
              <input type="file" class="hidden" accept=".xlsx,.xls,.csv" @change="handleFileChange" />
              <div v-if="uploading || importLoading" class="text-gray-500 text-sm">
                <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                {{ uploading ? 'Đang tải file...' : 'Đang đọc dữ liệu...' }}
              </div>
              <div v-else>
                <svg class="w-10 h-10 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p class="text-sm text-gray-600 font-medium">Kéo thả file vào đây hoặc click để chọn</p>
                <p class="text-xs text-gray-400 mt-1">Chấp nhận .xlsx, .xls, .csv</p>
              </div>
            </label>
          </template>

          <!-- STEP 2: PREVIEW -->
          <template v-else-if="importStep === 'preview' && previewData">
            <div class="flex items-center gap-4 text-sm">
              <span class="text-gray-600">Tổng: <strong>{{ previewData.totalRows }}</strong> dòng</span>
              <span class="text-green-700">Hợp lệ: <strong>{{ previewData.validRows }}</strong></span>
              <span v-if="previewData.errors.length" class="text-red-600">Lỗi: <strong>{{ previewData.errors.length }}</strong></span>
              <span v-if="previewData.warnings.length" class="text-amber-600">Cảnh báo: <strong>{{ previewData.warnings.length }}</strong></span>
              <span class="text-xs text-gray-400">{{ uploadedFileName }}</span>
            </div>
            <div v-if="previewData.errors.length || previewData.warnings.length" class="space-y-1 max-h-48 overflow-y-auto">
              <div
                v-for="(issue, i) in [...previewData.errors, ...previewData.warnings].slice(0, 50)"
                :key="i"
                :class="['flex gap-3 text-xs px-3 py-2 rounded-lg',
                  issue.severity === 'error' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700']"
              >
                <span class="font-bold shrink-0">Dòng {{ issue.row }}</span>
                <span class="font-medium shrink-0">{{ issue.field || '—' }}</span>
                <span>{{ issue.message }}</span>
              </div>
              <p v-if="previewData.errors.length + previewData.warnings.length > 50"
                class="text-xs text-gray-400 text-center pt-1">
                Chỉ hiển thị 50 vấn đề đầu tiên — tải báo cáo để xem đầy đủ.
              </p>
            </div>
            <div v-else class="bg-green-50 text-green-700 text-sm px-4 py-3 rounded-lg flex items-center gap-2">
              <svg class="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              Dữ liệu hợp lệ, sẵn sàng import.
            </div>
            <div v-if="previewData.preview.length" class="border border-gray-200 rounded-lg overflow-x-auto">
              <p class="text-xs text-gray-500 px-3 pt-2 pb-1 font-medium">Xem trước 10 dòng đầu:</p>
              <table class="w-full text-xs">
                <thead class="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th v-for="fn in previewData.fieldnames.slice(0, 6)" :key="fn"
                      class="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">{{ fn }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in previewData.preview" :key="ri" class="border-t border-gray-100 hover:bg-gray-50">
                    <td v-for="fn in previewData.fieldnames.slice(0, 6)" :key="fn"
                      class="px-3 py-1.5 text-gray-700 max-w-[120px] truncate" :title="String(row[fn] ?? '')">
                      {{ row[fn] ?? '—' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="flex items-center justify-between pt-2">
              <div class="flex gap-2">
                <button class="text-xs text-gray-500 hover:text-gray-700 underline" @click="importStep = 'upload'">← Đổi file</button>
                <button v-if="previewData.errors.length" class="text-xs text-red-600 hover:text-red-800 underline" @click="downloadErrorReport">
                  Tải báo cáo lỗi (.xlsx)
                </button>
              </div>
              <button
                :disabled="hasBlockingErrors || importLoading"
                :class="['px-4 py-2 text-sm rounded-lg font-medium transition-colors flex items-center gap-2',
                  hasBlockingErrors || importLoading
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-emerald-600 hover:bg-emerald-700 text-white']"
                @click="runImport"
              >
                <div v-if="importLoading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {{ importLoading ? 'Đang import...' : 'Bắt đầu Import ▶' }}
              </button>
            </div>
          </template>

          <!-- STEP 3: RESULT -->
          <template v-else-if="importStep === 'result' && importResult">
            <div :class="['p-5 rounded-xl text-center',
              importResult.failed === 0 ? 'bg-green-50' : importResult.success === 0 ? 'bg-red-50' : 'bg-amber-50']">
              <p class="text-3xl font-bold mb-1"
                :class="importResult.failed === 0 ? 'text-green-700' : importResult.success === 0 ? 'text-red-700' : 'text-amber-700'">
                {{ importResult.success }} / {{ importResult.total }}
              </p>
              <p class="text-sm text-gray-600">
                người dùng import thành công
                <span v-if="importResult.failed"> — <span class="text-red-600 font-medium">{{ importResult.failed }} lỗi</span></span>
              </p>
            </div>
            <div v-if="importResult.errors.length" class="space-y-1 max-h-40 overflow-y-auto">
              <p class="text-xs font-medium text-gray-500">Chi tiết lỗi:</p>
              <div v-for="(e, i) in importResult.errors" :key="i"
                class="flex gap-3 text-xs px-3 py-2 bg-red-50 text-red-700 rounded-lg">
                <span class="font-bold shrink-0">Dòng {{ e.row }}</span>
                <span>{{ e.message }}</span>
              </div>
            </div>
            <div class="flex justify-end pt-2">
              <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700" @click="closeImport">
                Đóng
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
