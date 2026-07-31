<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import DateInput from '@/components/common/DateInput.vue'
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  listCalibrationSchedules, createCalibrationSchedule,
  updateCalibrationSchedule, deleteCalibrationSchedule,
} from '@/api/imm11'
import type { CalibrationSchedule } from '@/api/imm11'
import SmartSelect from '@/components/common/SmartSelect.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import { formatAssetDisplay, formatDate } from '@/utils/formatters'
import { deriveCalStatus } from '@/utils/calibrationStatus'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import { useNotify } from '@/composables/useNotify'
import { useImm11Store } from '@/stores/imm11'
import { MSG } from '@/i18n/messages'
const toast = useToast()
const notify = useNotify()
const store = useImm11Store()

const PAGE_SIZE = 20

const items = ref<CalibrationSchedule[]>([])
const total = ref(0)
const page = ref(1)
const totalPages = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const err = ref('')

// Filters
const route = useRoute()
const router = useRouter()
const showFilters = ref(false)
// R6 §9.4.3 + BR-11-08 — pre-apply từ KPI drill:
//   ?overdue=1   → overdue_only (next_due_date < today, card calib_overdue);
//   ?due_soon=1  → due_soon (cửa-sổ-2-biên [today, today+30], card calib_due —
//                  KHỚP CHÍNH XÁC tập KPI, overdue rows KHÔNG lẫn);
//   ?due_before=X→ due_before (next_due_date <= X, cutoff-tùy-ý tập-BAO legacy).
// Toàn bộ lọc/tìm-kiếm/drill chạy SERVER-SIDE (BE list_schedules: pop_search trên
// ['name','asset'] + link_search asset_name + virtual overdue/due_soon/due_before).
// FE KHÔNG còn lọc client-side — tránh divergence total vs rows và miss rows >page_size.
// AC-CR-94 — thêm khoá thứ 4: `?asset=<mã>` (deep-link «Xem tất cả» từ ô «Lịch hiệu
// chuẩn» trong tab «Bản ghi liên quan» của một thiết bị). `asset` là điều kiện ĐỘC LẬP,
// GIAO (AND) với ưu tiên overdue > due_soon > due_before — KHÔNG nằm trong chuỗi else-if
// đó (nếu nhét vào, một trong hai điều kiện sẽ bị mất tuỳ thứ tự). BE lọc theo cột
// `asset`, KHÔNG tự thêm `is_active` ⇒ lịch tạm dừng vẫn hiện, khớp count ô liên quan.
const filters = ref({
  calibration_type: '', is_active: '' as '' | '1' | '0',
  overdue_only: route.query.overdue === '1',
  due_soon: route.query.due_soon === '1',
  due_before: (route.query.due_before as string) || '',
  asset: (route.query.asset as string) || '',
  search: '',
})

const TYPE_LABEL: Record<string, string> = { External: 'Bên ngoài', 'In-House': 'Nội bộ' }

interface FilterChip { key: 'calibration_type' | 'is_active' | 'overdue_only' | 'due_soon' | 'due_before' | 'asset' | 'search'; label: string }
// Nhãn chip thiết bị: tên đọc được của dòng đầu khớp mã (BE list_schedules enrich
// `asset_name`), lùi về MÃ khi chưa có tên — chip không bao giờ rỗng.
const assetChipLabel = computed(() => {
  const code = filters.value.asset
  if (!code) return ''
  return items.value.find(s => s.asset === code)?.asset_name || code
})
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.asset) chips.push({ key: 'asset', label: `Thiết bị: ${assetChipLabel.value}` })
  if (filters.value.calibration_type) chips.push({ key: 'calibration_type', label: TYPE_LABEL[filters.value.calibration_type] || filters.value.calibration_type })
  if (filters.value.is_active === '1') chips.push({ key: 'is_active', label: 'Đang hoạt động' })
  if (filters.value.is_active === '0') chips.push({ key: 'is_active', label: 'Tạm dừng' })
  // Ưu tiên overdue > due_soon > due_before (khớp _normalize_schedule_filters BE).
  if (filters.value.overdue_only) chips.push({ key: 'overdue_only', label: 'Quá hạn' })
  else if (filters.value.due_soon) chips.push({ key: 'due_soon', label: 'Sắp đến hạn (30 ngày)' })
  else if (filters.value.due_before) chips.push({ key: 'due_before', label: `Đến hạn trước ${formatDate(filters.value.due_before)}` })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)
function quickFilter(key: 'calibration_type', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  showFilters.value = false
}
/** Xoá khoá `asset` khỏi URL — để lại thì F5/back là lọc lại đúng cái user vừa bỏ. */
function dropAssetQuery() {
  if (!route.query.asset) return
  const query = { ...route.query }
  delete query.asset
  router.replace({ query })
}
function clearChip(key: string) {
  if (key === 'is_active') filters.value.is_active = ''
  else if (key === 'overdue_only') filters.value.overdue_only = false
  else if (key === 'due_soon') filters.value.due_soon = false
  else if (key === 'due_before') filters.value.due_before = ''
  else (filters.value as Record<string, unknown>)[key] = ''
  // Bỏ chip thiết bị dọn LUÔN query (chỉ khoá asset — drill quá hạn/sắp hạn giữ nguyên).
  if (key === 'asset') dropAssetQuery()
  // search-chip không nằm trong watch → reload thủ công (watched keys tự reload).
  if (key === 'search') load(1)
}
function resetFilters() {
  filters.value = {
    calibration_type: '', is_active: '', overdue_only: false, due_soon: false,
    due_before: '', asset: '', search: '',
  }
  dropAssetQuery()
  load(1)
}

const form = ref<Partial<CalibrationSchedule>>({
  calibration_type: 'External',
  interval_days: 365,
  is_active: 1,
})

// Build server-side filter dict từ ref filters. Ưu tiên overdue > due_soon >
// due_before (khớp _normalize_schedule_filters của BE). due_soon = card calib_due
// (2-biên, list tái lập CHÍNH XÁC tập KPI). search/calibration_type/is_active gửi xuống.
function buildFilters(): Record<string, unknown> {
  const f: Record<string, unknown> = {}
  if (filters.value.calibration_type) f.calibration_type = filters.value.calibration_type
  if (filters.value.is_active !== '') f.is_active = Number(filters.value.is_active)
  if (filters.value.overdue_only) f.overdue = 1
  else if (filters.value.due_soon) f.due_soon = 1
  else if (filters.value.due_before) f.due_before = filters.value.due_before
  // ĐỘC LẬP với chuỗi ưu tiên trên (deep-link thiết bị GIAO với drill hạn, không
  // clobber và không bị clobber). BE giao `asset` với tập SoT của nhánh virtual.
  if (filters.value.asset) f.asset = filters.value.asset
  const q = filters.value.search.trim()
  if (q) f.search = q
  return f
}

async function load(toPage = page.value) {
  loading.value = true
  try {
    page.value = toPage
    const res = await listCalibrationSchedules(buildFilters(), toPage, PAGE_SIZE)
    items.value = res.data || []
    total.value = res.pagination?.total || 0
    totalPages.value = (res.pagination?.total_pages as number) || 0
  } catch (e: unknown) {
    store._captureError(e)
    notify.fromError(store.lastApiError)
  } finally { loading.value = false }
}

// Mỗi thay đổi filter/chip → về trang 1 + reload server (search debounce qua
// ListFilterBar @apply). Drill ?overdue/?due_soon/?due_before set ref rồi load() server-side.
watch(
  () => [filters.value.calibration_type, filters.value.is_active,
    filters.value.overdue_only, filters.value.due_soon, filters.value.due_before,
    filters.value.asset],
  () => load(1),
)
// Sync drill query khi điều hướng từ dashboard (giống PMWorkOrderListView).
watch(() => route.query.overdue, (v) => { filters.value.overdue_only = v === '1' })
watch(() => route.query.due_soon, (v) => { filters.value.due_soon = v === '1' })
watch(() => route.query.due_before, (v) => { filters.value.due_before = (v as string) || '' })
// Deep-link «Xem tất cả» tới CÙNG route (thiết bị khác) không remount ⇒ sync query → ref.
watch(() => route.query.asset, (v) => { filters.value.asset = (v as string) || '' })

const paginationMeta = computed(() => ({
  page: page.value, page_size: PAGE_SIZE, total: total.value, total_pages: totalPages.value,
}))

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

const todayIso = computed(() => new Date().toISOString().slice(0, 10))

async function save() {
  err.value = ''
  if (form.value.next_due_date && form.value.next_due_date < todayIso.value) {
    err.value = 'Ngày đến hạn không được nằm trong quá khứ'
    toast.error(err.value)
    return
  }
  if (form.value.interval_days != null && form.value.interval_days <= 0) {
    err.value = 'Chu kỳ (ngày) phải lớn hơn 0'
    toast.error(err.value)
    return
  }
  try {
    if (editingName.value) {
      await updateCalibrationSchedule(editingName.value, form.value)
      notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: 'lịch hiệu chuẩn' } })
    } else {
      const r = await createCalibrationSchedule(form.value) as unknown as { next_due_date?: string }
      notify.show({ code: MSG.IMM11_SCHEDULE_CREATE_SUCCESS, ctx: { next_due_date: r?.next_due_date ?? form.value.next_due_date ?? '' } })
    }
    showForm.value = false; await load()
  } catch (e: unknown) {
    store._captureError(e)
    err.value = store.error ?? ''
    notify.fromError(store.lastApiError)
  }
}

// LL-FE-14: cấm window.confirm() — dùng BaseModal styled confirm.
const showDeleteModal = ref(false)
const deleteTarget = ref<string | null>(null)
const deleting = ref(false)

function askRemove(name: string) {
  deleteTarget.value = name
  showDeleteModal.value = true
}

function closeDeleteModal() {
  if (deleting.value) return
  showDeleteModal.value = false
  deleteTarget.value = null
}

async function confirmRemove() {
  const name = deleteTarget.value
  if (!name) return
  deleting.value = true
  try {
    await deleteCalibrationSchedule(name)
    notify.show({ code: MSG.UI_DELETE_SUCCESS, ctx: { entity: 'lịch hiệu chuẩn' } })
    showDeleteModal.value = false
    deleteTarget.value = null
    await load()
  } catch (e: unknown) {
    store._captureError(e)
    notify.fromError(store.lastApiError)
  } finally {
    deleting.value = false
  }
}

// Trạng thái tuân thủ hiệu chuẩn derive THUẦN từ next_due_date (SoT) — date-only,
// khớp BE _overdue_asset_ids/_due_soon_asset_ids (BR-11-08). FAIL due-now
// (next_due_date <= today) → 'Quá hạn'/'Đến hạn' (đỏ/cam), KHÔNG 'Đúng lịch'.
function calStatus(date: string | null | undefined) {
  return deriveCalStatus(date)
}

onMounted(() => {
  // R6 §9.3 — drill-down từ dashboard: mở panel filter để user thấy + xoá được.
  if (filters.value.overdue_only || filters.value.due_soon || filters.value.due_before
    || filters.value.asset) showFilters.value = true
  load(1)
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Lịch hiệu chuẩn"
      :subtitle="`Tổng ${total} lịch`"
      :breadcrumb="[{ label: 'IMM-11 · Hiệu chuẩn', to: '/calibration' }, { label: 'Lịch hiệu chuẩn' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm lịch
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      v-model:search="filters.search"
      :show="showFilters"
      :chips="activeChips"
      search-placeholder="Tìm theo mã, tên thiết bị..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="load(1)"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Loại hiệu chuẩn</label>
          <select v-model="filters.calibration_type" class="form-select">
            <option value="">Tất cả loại</option>
            <option value="External">Bên ngoài</option>
            <option value="In-House">Nội bộ</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.is_active" class="form-select">
            <option value="">Tất cả trạng thái</option>
            <option value="1">Đang hoạt động</option>
            <option value="0">Tạm dừng</option>
          </select>
        </div>
        <div class="form-group flex items-center gap-2 pt-5">
          <input v-model="filters.overdue_only" type="checkbox" class="rounded border-slate-300" />
          <label class="form-label mb-0">Chỉ quá hạn</label>
        </div>
      </template>
    </ListFilterBar>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span v-if="activeFilterCount > 0">
          Kết quả lọc: <strong class="text-slate-700">{{ total }}</strong> lịch
        </span>
        <span v-else>
          Tổng <strong class="text-slate-700">{{ total }}</strong> lịch
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="items.length === 0" class="p-8 text-center text-slate-400 text-sm">
        {{ activeFilterCount > 0 ? 'Không có lịch phù hợp.' : 'Chưa có lịch hiệu chuẩn.' }}
      </div>
      <template v-else>
        <!-- Mobile cards (< sm) -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="s in items"
            :key="s.name"
            class="mobile-card"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ s.name }}</span>
              <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="s.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'">
                {{ s.is_active ? 'Hoạt động' : 'Tạm dừng' }}
              </span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ formatAssetDisplay(s.asset_name, s.asset).main }}</p>
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <button
                v-if="s.calibration_type"
                class="text-xs px-1.5 py-0.5 rounded-full font-medium bg-purple-100 text-purple-700"
                @click="quickFilter('calibration_type', s.calibration_type!)"
              >{{ TYPE_LABEL[s.calibration_type] || s.calibration_type }}</button>
              <span class="text-slate-300">·</span>
              <span>{{ s.interval_days }} ngày</span>
              <span class="text-slate-300">·</span>
              <span :class="calStatus(s.next_due_date).textClass">{{ formatDate(s.next_due_date) }}</span>
              <span class="text-xs px-1.5 py-0.5 rounded-full font-medium" :class="calStatus(s.next_due_date).badgeClass">
                {{ calStatus(s.next_due_date).label }}
              </span>
            </div>
            <div class="flex justify-end gap-3 mt-2 pt-2 border-t border-slate-100" @click.stop>
              <button class="text-blue-600 text-xs font-medium" @click="openEdit(s.name)">Sửa</button>
              <button class="text-red-600 text-xs font-medium" @click="askRemove(s.name)">Xóa</button>
            </div>
          </div>
          <div v-if="items.length === 0" class="py-12 text-center text-slate-400">
            <p class="text-sm font-medium">Không có dữ liệu</p>
          </div>
        </div>

        <!-- Desktop table (sm+) -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 border-b">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Thiết bị</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Loại</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Chu kỳ</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Ngày đến hạn</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Trạng thái lịch</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Hoạt động</th>
                <th class="px-4 py-3 text-right"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="s in items" :key="s.name" class="hover:bg-slate-50">
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
                <td class="px-4 py-3 text-xs" :class="calStatus(s.next_due_date).textClass">
                  {{ formatDate(s.next_due_date) }}
                </td>
                <td class="px-4 py-3">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="calStatus(s.next_due_date).badgeClass">
                    {{ calStatus(s.next_due_date).label }}
                  </span>
                </td>
                <td class="px-4 py-3">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="s.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'">
                    {{ s.is_active ? 'Hoạt động' : 'Tạm dừng' }}
                  </span>
                </td>
                <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                  <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="openEdit(s.name)">Sửa</button>
                  <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="askRemove(s.name)">Xóa</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <!-- Pagination: truy cập trang >1 (rows >page_size). Server-side total. -->
    <BasePagination :pagination="paginationMeta" @page-change="load" />

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
              <option value="External">Bên ngoài</option>
              <option value="In-House">Nội bộ</option>
            </select>
          </div>
          <div>
            <label class="form-label">Chu kỳ (ngày)</label>
            <input v-model.number="form.interval_days" type="number" min="1" class="form-input w-full text-sm" />
          </div>
          <div>
            <label class="form-label">Ngày đến hạn tiếp theo</label>
            <DateInput v-model="form.next_due_date" :min="todayIso" class="form-input w-full text-sm" />
            <p class="text-[11px] text-slate-400 mt-1">Không được chọn ngày trong quá khứ.</p>
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

    <!-- LL-FE-14: confirm xoá lịch hiệu chuẩn qua BaseModal (thay window.confirm) -->
    <BaseModal
      v-if="showDeleteModal"
      title="Xoá lịch hiệu chuẩn"
      size="sm"
      danger
      data-testid="cal-schedule-delete-modal"
      @close="closeDeleteModal"
    >
      <p class="text-sm text-slate-600">
        Bạn có chắc muốn xoá lịch hiệu chuẩn
        <span class="font-mono font-medium text-slate-800">{{ deleteTarget }}</span>?
        Thao tác này không thể hoàn tác.
      </p>
      <template #footer>
        <button class="btn-ghost text-sm" :disabled="deleting" @click="closeDeleteModal">Quay lại</button>
        <button
          class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          :disabled="deleting"
          data-testid="cal-schedule-delete-confirm"
          @click="confirmRemove"
        >
          {{ deleting ? 'Đang xoá...' : 'Xác nhận xoá' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
