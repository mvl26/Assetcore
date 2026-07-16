<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  listFirmwareCrs, getFirmwareCr, createFirmwareCr, updateFirmwareCr, deleteFirmwareCr,
  type FirmwareCR,
} from '@/api/imm00'
import { listRepairWorkOrders } from '@/api/imm09'
import { frappeGet } from '@/api/helpers'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import { lifecycleStatusLabel } from '@/constants/labels'

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

const STATUS_KEYS = ['Draft', 'Pending Approval', 'Approved', 'Applied', 'Rollback Required', 'Rolled Back']
const STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp',
  'Pending Approval': 'Chờ phê duyệt',
  Approved: 'Đã phê duyệt',
  Applied: 'Đã áp dụng',
  'Rollback Required': 'Cần khôi phục',
  'Rolled Back': 'Đã khôi phục',
}
function statusLabel(s?: string): string { return (s && STATUS_LABELS[s]) || s || '' }
function statusColor(s?: string) {
  return s === 'Approved' ? 'bg-green-100 text-green-700'
    : s === 'Applied' ? 'bg-blue-100 text-blue-700'
    : s === 'Rejected' || s === 'Rolled Back' ? 'bg-red-100 text-red-700'
    : 'bg-gray-100 text-gray-700'
}

// ─── Asset metadata (loaded on selection via SmartSelect) ────────────────────
interface AssetMeta { asset_name?: string; device_model?: string; lifecycle_status?: string; location?: string }
const assetMeta = ref<AssetMeta | null>(null)

async function loadAssetMeta() {
  if (!form.value.asset_ref) { assetMeta.value = null; return }
  try {
    const r = await frappeGet<AssetMeta>('/api/method/frappe.client.get_value', {
      doctype: 'AC Asset',
      filters: form.value.asset_ref,
      fieldname: JSON.stringify(['asset_name', 'device_model', 'lifecycle_status', 'location']),
    })
    assetMeta.value = r ?? null
  } catch { assetMeta.value = null }
}

watch(() => form.value.asset_ref, loadAssetMeta)

// ─── WO autocomplete ─────────────────────────────────────────────────────────
const woQuery = ref('')
const woResults = ref<{ name: string; asset_name?: string }[]>([])
const woDropdownOpen = ref(false)
let woTimer: ReturnType<typeof setTimeout>

function onWoInput() {
  clearTimeout(woTimer)
  if (!woQuery.value.trim()) { woResults.value = []; woDropdownOpen.value = false; return }
  woTimer = setTimeout(async () => {
    const res = await listRepairWorkOrders({}, 1, 10)
    woResults.value = (res.data ?? [])
      .filter(w => w.name.toLowerCase().includes(woQuery.value.toLowerCase()) || (w.asset_name || '').toLowerCase().includes(woQuery.value.toLowerCase()))
      .slice(0, 8)
    woDropdownOpen.value = woResults.value.length > 0
  }, 280)
}

function selectWo(item: { name: string }) {
  form.value.asset_repair_wo = item.name
  woQuery.value = item.name
  woDropdownOpen.value = false
}

function closeWoDropdown() { window.setTimeout(() => { woDropdownOpen.value = false }, 200) }

// ─── Filters (SERVER-SIDE — BE list_firmware_crs áp status/asset/search + phân
// trang; KHÔNG lọc client trên trang bị cắt) ───────────────────────────────────
interface FilterChip { key: 'status' | 'asset' | 'search'; label: string }
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
  filters.value[key] = value; showFilters.value = false
}
function clearChip(key: string) { (filters.value as Record<string, string>)[key] = '' }
function resetFilters() { filters.value = { status: '', asset: '', search: '' } }

// ─── Load (server-side filter + pagination) ────────────────────────────────────
const page = ref(1)
const PAGE_SIZE = 20
async function load() {
  loading.value = true
  try {
    const d = await listFirmwareCrs({
      page: page.value, page_size: PAGE_SIZE,
      status: filters.value.status || undefined,
      asset: filters.value.asset || undefined,
      search: filters.value.search.trim() || undefined,
    })
    items.value = d.items || []; total.value = d.total || 0
  } finally { loading.value = false }
}
// Debounce đổi filter → về trang 1 + reload server (search gõ liên tục).
let filterTimer: ReturnType<typeof setTimeout>
watch(filters, () => {
  clearTimeout(filterTimer)
  filterTimer = setTimeout(() => { page.value = 1; load() }, 300)
}, { deep: true })
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; load() } }

// ─── Form ─────────────────────────────────────────────────────────────────────
function openCreate() {
  editingName.value = null
  // KHÔNG set status ở FE — BE default 'Draft' (DocType). Status là máy quản.
  form.value = { asset_ref: '', version_before: '', version_after: '', change_notes: '', source_reference: '' }
  assetMeta.value = null; woQuery.value = ''
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getFirmwareCr(name)
  form.value = { ...r }
  woQuery.value = r.asset_repair_wo || ''
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  // Status + cờ server-derived KHÔNG đi qua CRUD chung (chỉ đổi qua transition
  // endpoint có kiểm soát). Loại khỏi payload để FE không gửi dead-kwarg.
  const { status: _s, allowed_transitions: _at, can_approve: _ca, ...payload } = form.value
  void _s; void _at; void _ca
  try {
    if (editingName.value) await updateFirmwareCr(editingName.value, payload)
    else await createFirmwareCr(payload)
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = e instanceof Error ? e.message : 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa yêu cầu thay đổi firmware "${name}"?`)) return
  try { await deleteFirmwareCr(name); await load() }
  catch (e: unknown) { toast.error(e instanceof Error ? e.message : 'Không thể xóa') }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Yêu cầu cập nhật Firmware"
      :subtitle="`Tổng ${total} yêu cầu`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm yêu cầu
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="filters.search"
      search-placeholder="Tìm theo mã yêu cầu, phiên bản, nguồn..."
      @reset="resetFilters"
      @clear-chip="clearChip"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.status" class="form-select">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in STATUS_KEYS" :key="s" :value="s">{{ STATUS_LABELS[s] || s }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Thiết bị</label>
          <input v-model="filters.asset" placeholder="Mã thiết bị..." class="form-input" />
        </div>
      </template>
    </ListFilterBar>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span v-if="activeFilterCount > 0">
          Kết quả lọc: <strong class="text-slate-700">{{ items.length }}</strong> / {{ total }} yêu cầu
        </span>
        <span v-else>
          Hiển thị <strong class="text-slate-700">{{ items.length }}</strong> / {{ total }} yêu cầu
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="items.length === 0" class="text-center text-slate-400 py-12 text-sm">
        {{ activeFilterCount > 0 ? 'Không có yêu cầu nào phù hợp.' : 'Chưa có yêu cầu nào.' }}
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="f in items"
            :key="f.name"
            class="mobile-card"
            @click="router.push(`/cm/firmware/${f.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ f.name }}</span>
              <span v-if="f.status" :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', statusColor(f.status)]">
                {{ statusLabel(f.status) }}
              </span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ f.asset_name || f.asset_ref || '—' }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="f.version_before">{{ f.version_before }}</span>
              <span v-if="f.version_after">→ {{ f.version_after }}</span>
              <span v-if="f.approved_by">· {{ f.approved_by_name || f.approved_by }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <table class="hidden sm:table w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="table-header">Mã</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Phiên bản cũ</th>
              <th class="table-header">Phiên bản mới</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header">Phê duyệt</th>
              <th class="table-header">Áp dụng</th>
              <th class="px-4 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="f in items" :key="f.name" class="hover:bg-slate-50">
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
                  @click="quickFilter('status', f.status!)"
                >{{ statusLabel(f.status) }}</button>
              </td>
              <td class="px-4 py-3 text-xs text-slate-500">{{ f.approved_by_name || f.approved_by || '—' }}</td>
              <td class="px-4 py-3 text-xs text-slate-500">{{ f.applied_datetime ? new Date(f.applied_datetime).toLocaleDateString('vi-VN') : '—' }}</td>
              <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="router.push(`/cm/firmware/${f.name}`)">Chi tiết</button>
                <button class="text-slate-500 hover:text-slate-700 text-xs font-medium" @click="openEdit(f.name)">Sửa</button>
                <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="remove(f.name)">Xóa</button>
              </td>
            </tr>
          </tbody>
        </table>
      </template>

      <!-- Pagination -->
      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} / {{ total }}</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" aria-label="Trang trước" @click="prevPage">‹</button>
          <button :disabled="page * PAGE_SIZE >= total" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" aria-label="Trang sau" @click="nextPage">›</button>
        </div>
      </div>
    </div>

    <!-- Form modal -->
    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4" @click.self="showForm = false">
      <div class="bg-white rounded-t-2xl sm:rounded-xl w-full sm:max-w-2xl max-h-[90svh] overflow-y-auto">
        <div class="sticky top-0 bg-white border-b border-slate-100 px-5 py-4 flex items-center justify-between">
          <h2 class="text-base font-semibold text-slate-900">{{ editingName ? 'Sửa' : 'Thêm' }} yêu cầu cập nhật Firmware</h2>
          <button class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-500" @click="showForm = false">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="p-5 space-y-4">
          <div v-if="err" class="alert-error">{{ err }}</div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <!-- Asset SmartSelect -->
            <div class="sm:col-span-2 form-group">
              <label class="form-label">Thiết bị (AC Asset) <span class="text-red-500">*</span></label>
              <SmartSelect
                v-model="form.asset_ref as string"
                doctype="AC Asset"
                placeholder="Tìm thiết bị theo tên / mã / serial..."
              />
              <div v-if="assetMeta" class="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                <div class="bg-slate-50 rounded px-2 py-1.5">
                  <span class="text-slate-500">Tên:</span> <b>{{ assetMeta.asset_name || '—' }}</b>
                </div>
                <div class="bg-slate-50 rounded px-2 py-1.5">
                  <span class="text-slate-500">Model:</span> {{ assetMeta.device_model || '—' }}
                </div>
                <div
                  :class="['rounded px-2 py-1.5', assetMeta.lifecycle_status === 'Decommissioned' ? 'bg-red-50 text-red-700' : 'bg-slate-50']"
                >
                  <span class="text-slate-500">Trạng thái:</span> <b>{{ assetMeta.lifecycle_status ? lifecycleStatusLabel(assetMeta.lifecycle_status) : '—' }}</b>
                </div>
              </div>
              <div v-if="assetMeta?.lifecycle_status === 'Decommissioned'" class="mt-1.5 text-xs text-red-600">
                Thiết bị đã thanh lý — không thể tạo yêu cầu firmware.
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Phiên bản hiện tại</label>
              <input v-model="form.version_before" class="form-input font-mono" placeholder="v1.2.3" />
            </div>
            <div class="form-group">
              <label class="form-label">Phiên bản mới <span class="text-red-500">*</span></label>
              <input v-model="form.version_after" class="form-input font-mono" placeholder="v1.3.0" />
            </div>

            <div class="sm:col-span-2 form-group">
              <label class="form-label">Nguồn tham chiếu</label>
              <input v-model="form.source_reference" class="form-input" placeholder="Thông báo NSX, mã CVE, v.v." />
            </div>
            <div class="sm:col-span-2 form-group">
              <label class="form-label">Nội dung thay đổi <span class="text-red-500">*</span></label>
              <textarea v-model="form.change_notes" rows="3" class="form-textarea" placeholder="Mô tả các thay đổi của bản firmware mới..."></textarea>
            </div>

            <!-- Trạng thái = máy quản (SSoT server). KHÔNG cho đổi tùy tiện qua form
                 CRUD — chỉ qua nút hành động có kiểm soát ở trang chi tiết (transition
                 endpoint + audit). Ở đây chỉ HIỂN THỊ read-only khi đang sửa. -->
            <div v-if="editingName" class="form-group">
              <label class="form-label">Trạng thái</label>
              <div>
                <span :class="['inline-flex px-2.5 py-1 rounded-full text-xs font-medium', statusColor(form.status)]">
                  {{ statusLabel(form.status) }}
                </span>
                <p class="mt-1 text-xs text-slate-400">
                  Trạng thái chỉ thay đổi qua các nút Duyệt / Triển khai / Khôi phục ở trang chi tiết.
                </p>
              </div>
            </div>

            <!-- WO autocomplete -->
            <div class="form-group">
              <label class="form-label">Liên kết lệnh sửa chữa</label>
              <div class="relative">
                <input
                  v-model="woQuery"
                  class="form-input font-mono"
                  placeholder="Tìm mã lệnh công việc..."
                  autocomplete="off"
                  @input="onWoInput"
                  @blur="closeWoDropdown"
                />
                <div v-if="woDropdownOpen" class="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden">
                  <button
                    v-for="w in woResults"
                    :key="w.name"
                    class="w-full text-left px-3 py-2.5 hover:bg-slate-50 flex flex-col gap-0.5 border-b border-slate-100 last:border-0"
                    @mousedown.prevent="selectWo(w)"
                  >
                    <span class="text-xs font-mono font-medium text-slate-800">{{ w.name }}</span>
                    <span v-if="w.asset_name" class="text-xs text-slate-400">{{ w.asset_name }}</span>
                  </button>
                </div>
              </div>
            </div>

            <div v-if="form.status === 'Rolled Back'" class="sm:col-span-2 form-group">
              <label class="form-label">Lý do khôi phục</label>
              <textarea v-model="form.rollback_reason" rows="2" class="form-textarea"></textarea>
            </div>
          </div>
        </div>

        <div class="sticky bottom-0 bg-white border-t border-slate-100 px-5 py-4 flex justify-end gap-2">
          <button class="btn-secondary" @click="showForm = false">Hủy</button>
          <button class="btn-primary" @click="save">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
