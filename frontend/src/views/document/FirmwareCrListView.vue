<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  listFirmwareCrs, getFirmwareCr, createFirmwareCr, updateFirmwareCr, deleteFirmwareCr,
  type FirmwareCR,
} from '@/api/imm00'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
const toast = useToast()

const router = useRouter()

const items = ref<FirmwareCR[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<FirmwareCR> & Record<string, unknown>>({})
const err = ref('')

// Filter state
const showFilters = ref(false)
const filters = ref({ status: '', asset: '', search: '' })

const STATUS_KEYS = ['Draft', 'Pending Approval', 'Approved', 'Applied', 'Rejected', 'Rolled Back']

interface FilterChip { key: 'status' | 'asset' | 'search'; label: string }
const filteredItems = computed(() => {
  let arr = items.value
  if (filters.value.status) arr = arr.filter(f => f.status === filters.value.status)
  if (filters.value.asset) {
    const q = filters.value.asset.toLowerCase()
    arr = arr.filter(f =>
      (f.asset_ref || '').toLowerCase().includes(q)
      || (f.asset_name || '').toLowerCase().includes(q),
    )
  }
  if (filters.value.search.trim()) {
    const q = filters.value.search.trim().toLowerCase()
    arr = arr.filter(f =>
      (f.name || '').toLowerCase().includes(q)
      || (f.version_before || '').toLowerCase().includes(q)
      || (f.version_after || '').toLowerCase().includes(q)
      || (f.source_reference || '').toLowerCase().includes(q),
    )
  }
  return arr
})
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.status) chips.push({ key: 'status', label: STATUS_LABELS[filters.value.status] || filters.value.status })
  if (filters.value.asset) chips.push({ key: 'asset', label: `Thiết bị: ${filters.value.asset}` })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)
function quickFilter(key: 'status' | 'asset', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  showFilters.value = false
}
function clearChip(key: FilterChip['key']) { filters.value[key] = '' }
function resetFilters() { filters.value = { status: '', asset: '', search: '' } }

async function load() {
  loading.value = true
  try {
    const r = await listFirmwareCrs()
    const d = r as unknown as { items: FirmwareCR[]; total: number }
    if (d) { items.value = d.items || []; total.value = d.total || 0 }
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = {
    asset_ref: '', version_before: '', version_after: '', status: 'Draft',
    change_notes: '', source_reference: '',
  }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getFirmwareCr(name)
  if (r) form.value = { ...(r as unknown as FirmwareCR) }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  try {
    if (editingName.value) await updateFirmwareCr(editingName.value, form.value)
    else await createFirmwareCr(form.value)
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa FCR "${name}"?`)) return
  try { await deleteFirmwareCr(name); await load() }
  catch (e: unknown) { toast.error((e as Error).message || 'Không thể xóa') }
}

function statusColor(s?: string) {
  return s === 'Approved' ? 'bg-green-100 text-green-700'
    : s === 'Applied' ? 'bg-blue-100 text-blue-700'
    : s === 'Rejected' || s === 'Rolled Back' ? 'bg-red-100 text-red-700'
    : 'bg-gray-100 text-gray-700'
}

const STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp',
  'Pending Approval': 'Chờ phê duyệt',
  Approved: 'Đã phê duyệt',
  Applied: 'Đã áp dụng',
  Rejected: 'Từ chối',
  'Rolled Back': 'Đã khôi phục',
}
function statusLabel(s?: string): string {
  return (s && STATUS_LABELS[s]) || s || ''
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Yêu cầu cập nhật Firmware</h1>
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
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
          <select v-model="filters.status" class="form-select text-sm">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in STATUS_KEYS" :key="s" :value="s">{{ STATUS_LABELS[s] || s }}</option>
          </select>
          <input v-model="filters.asset" placeholder="Mã/tên thiết bị..." class="form-input text-sm" />
        </div>
        <div class="flex gap-2">
          <input v-model="filters.search" placeholder="Tìm theo mã yêu cầu, phiên bản, nguồn..." class="form-input flex-1 text-sm" />
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
        {{ activeFilterCount > 0 ? 'Không có yêu cầu nào phù hợp.' : 'Chưa có yêu cầu nào.' }}
      </div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phiên bản cũ</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phiên bản mới</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Trạng thái</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phê duyệt</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Áp dụng</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="f in filteredItems" :key="f.name" class="hover:bg-slate-50">
            <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ f.name }}</td>
            <td class="px-4 py-3">
              <button
                v-if="f.asset_ref"
                class="font-medium text-slate-800 text-left hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                @click="quickFilter('asset', f.asset_ref!)"
              >{{ f.asset_name || f.asset_ref }}</button>
              <div v-if="f.asset_name && f.asset_ref" class="text-xs text-slate-400 font-mono mt-0.5">{{ f.asset_ref }}</div>
            </td>
            <td class="px-4 py-3 font-mono text-xs">{{ f.version_before || '—' }}</td>
            <td class="px-4 py-3 font-mono text-xs">{{ f.version_after || '—' }}</td>
            <td class="px-4 py-3">
              <button
                v-if="f.status"
                :class="['text-xs px-2 py-0.5 rounded font-medium hover:ring-2 hover:ring-current/50', statusColor(f.status)]"
                :title="`Lọc: ${statusLabel(f.status)}`"
                @click="quickFilter('status', f.status!)"
              >{{ statusLabel(f.status) }}</button>
            </td>
            <td class="px-4 py-3 text-xs text-slate-500">{{ f.approved_by || '—' }}</td>
            <td class="px-4 py-3 text-xs text-slate-500">{{ f.applied_datetime ? new Date(f.applied_datetime).toLocaleDateString('vi-VN') : '—' }}</td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="router.push(`/cm/firmware/${f.name}`)">Chi tiết</button>
              <button class="text-slate-500 hover:text-slate-700 text-xs font-medium" @click="openEdit(f.name)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="remove(f.name)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[600px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} yêu cầu cập nhật Firmware</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị (AC Asset) *</label>
            <input v-model="form.asset_ref" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Phiên bản hiện tại</label>
            <input v-model="form.version_before" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Phiên bản mới *</label>
            <input v-model="form.version_after" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nguồn (thông báo nhà sản xuất, mã lỗ hổng CVE, v.v.)</label>
            <input v-model="form.source_reference" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nội dung thay đổi *</label>
            <textarea v-model="form.change_notes" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Trạng thái</label>
            <select v-model="form.status" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Draft">Nháp</option>
              <option value="Pending Approval">Chờ phê duyệt</option>
              <option value="Approved">Đã phê duyệt</option>
              <option value="Applied">Đã áp dụng</option>
              <option value="Rejected">Từ chối</option>
              <option value="Rolled Back">Đã khôi phục</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Liên kết phiếu sửa chữa</label>
            <input v-model="form.asset_repair_wo" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="SỬA-..." />
          </div>
          <div v-if="form.status === 'Rolled Back'" class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Lý do khôi phục</label>
            <textarea v-model="form.rollback_reason" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
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
