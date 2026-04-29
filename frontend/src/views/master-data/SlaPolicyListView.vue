<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import DateInput from '@/components/common/DateInput.vue'
import { ref, onMounted, computed } from 'vue'
import {
  listSlaPolicies, getSlaPolicy, createSlaPolicy, updateSlaPolicy, deleteSlaPolicy,
} from '@/api/imm00'
import type { ImmSlaPolicy, Priority, RiskClass } from '@/types/imm00'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import { useMasterDataStore } from '@/stores/useMasterDataStore'
import { formatDate, isCheckOn } from '@/utils/formatters'
const toast = useToast()
const masterStore = useMasterDataStore()

function userLabel(userId?: string | null): string {
  if (!userId) return '—'
  const item = masterStore.getItemById('User', userId)
  return item?.name || userId
}

const policies = ref<ImmSlaPolicy[]>([])
const loading = ref(false)
const showForm = ref(false)
const showDetail = ref(false)
const detail = ref<ImmSlaPolicy | null>(null)
const editingName = ref<string | null>(null)
const form = ref<Partial<ImmSlaPolicy> & Record<string, unknown>>({})
const err = ref('')

const showFilters = ref(false)
const filters = ref<{ priority: string; risk_class: string; is_active: '' | '1' | '0'; search: string }>({
  priority: '',
  risk_class: '',
  is_active: '',
  search: '',
})

// OPTIONS arrays gắn type union để giữ autocomplete khi sửa.
// Maps để Record<string, string> vì priority/risk_class từ API là string lỏng.
const PRIORITY_OPTIONS: Priority[] = ['P1 Critical', 'P1 High', 'P2', 'P3', 'P4']
const PRIORITY_LABEL: Record<string, string> = {
  'P1 Critical': 'P1 Critical — Nguy hiểm tính mạng',
  'P1 High': 'P1 High — Khẩn cấp',
  P2: 'P2 — Cao',
  P3: 'P3 — Trung bình',
  P4: 'P4 — Thấp',
}
const PRIORITY_BADGE: Record<string, string> = {
  'P1 Critical': 'bg-red-100 text-red-700',
  'P1 High': 'bg-orange-100 text-orange-700',
  P2: 'bg-yellow-100 text-yellow-700',
  P3: 'bg-blue-100 text-blue-700',
  P4: 'bg-slate-100 text-slate-600',
}

const RISK_OPTIONS: RiskClass[] = ['Low', 'Medium', 'High', 'Critical']
const RISK_LABEL: Record<string, string> = {
  Low: 'Thấp', Medium: 'Trung bình', High: 'Cao', Critical: 'Khẩn cấp',
}

const filteredPolicies = computed(() => {
  let items = policies.value
  if (filters.value.priority) items = items.filter(p => p.priority === filters.value.priority)
  if (filters.value.risk_class) items = items.filter(p => p.risk_class === filters.value.risk_class)
  if (filters.value.is_active === '1') items = items.filter(p => isCheckOn(p.is_active))
  if (filters.value.is_active === '0') items = items.filter(p => !isCheckOn(p.is_active))
  if (filters.value.search.trim()) {
    const q = filters.value.search.trim().toLowerCase()
    items = items.filter(p =>
      (p.policy_name || '').toLowerCase().includes(q)
      || (p.name || '').toLowerCase().includes(q),
    )
  }
  return items
})

interface FilterChip { key: 'priority' | 'risk_class' | 'is_active' | 'search'; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.priority) chips.push({ key: 'priority', label: PRIORITY_LABEL[filters.value.priority] || filters.value.priority })
  if (filters.value.risk_class) chips.push({ key: 'risk_class', label: `Rủi ro: ${RISK_LABEL[filters.value.risk_class] || filters.value.risk_class}` })
  if (filters.value.is_active === '1') chips.push({ key: 'is_active', label: 'Đang hoạt động' })
  if (filters.value.is_active === '0') chips.push({ key: 'is_active', label: 'Ngừng hoạt động' })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: FilterChip['key']) {
  if (key === 'is_active') filters.value.is_active = ''
  else (filters.value as Record<string, unknown>)[key] = ''
}
function resetFilters() {
  filters.value = { priority: '', risk_class: '', is_active: '', search: '' }
}

async function load() {
  loading.value = true
  try {
    const res = await listSlaPolicies()
    if (res) policies.value = (res as unknown as ImmSlaPolicy[]) || []
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = {
    policy_name: '', priority: 'P3', risk_class: 'Medium',
    response_time_minutes: 240, resolution_time_hours: 24,
    is_active: 1, is_default: 0,
    escalation_l1_user: '', escalation_l1_hours: 4,
    escalation_l2_user: '', escalation_l2_hours: 8,
    effective_date: '', expiry_date: '',
  }
  err.value = ''; showForm.value = true
}

async function openDetail(name: string) {
  err.value = ''
  // Prefetch User cache song song với fetch detail — chỉ load khi user thực sự mở modal
  const [res] = await Promise.all([
    getSlaPolicy(name),
    masterStore.fetchDoctype('User'),
  ])
  if (res) detail.value = res as unknown as ImmSlaPolicy
  showDetail.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const res = await getSlaPolicy(name)
  if (res) form.value = { ...(res as unknown as ImmSlaPolicy) }
  err.value = ''; showDetail.value = false; showForm.value = true
}

async function save() {
  err.value = ''
  // Cross-field check: L1 phải đi trước L2 trong dòng thời gian leo thang
  const l1h = Number(form.value.escalation_l1_hours) || 0
  const l2h = Number(form.value.escalation_l2_hours) || 0
  if (l1h && l2h && l1h > l2h) {
    err.value = 'Thời gian leo thang L1 phải nhỏ hơn hoặc bằng L2.'
    return
  }
  try {
    if (editingName.value) await updateSlaPolicy(editingName.value, form.value)
    else await createSlaPolicy(form.value)
    showForm.value = false
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string, ev?: Event) {
  ev?.stopPropagation()
  if (!confirm(`Xóa chính sách SLA "${name}"?`)) return
  try {
    await deleteSlaPolicy(name)
    showDetail.value = false
    await load()
  } catch (e: unknown) {
    toast.error((e as Error).message || 'Không thể xóa — có thể đang được tham chiếu')
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <div class="flex items-start justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Chính sách SLA</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ policies.length }}</strong> chính sách
        </p>
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
          Thêm chính sách
        </button>
      </div>
    </div>

    <!-- Active chips -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
    >
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
          <select v-model="filters.priority" class="form-select text-sm">
            <option value="">Tất cả mức ưu tiên</option>
            <option v-for="p in PRIORITY_OPTIONS" :key="p" :value="p">{{ PRIORITY_LABEL[p] || p }}</option>
          </select>
          <select v-model="filters.risk_class" class="form-select text-sm">
            <option value="">Tất cả rủi ro</option>
            <option v-for="r in RISK_OPTIONS" :key="r" :value="r">{{ RISK_LABEL[r] }}</option>
          </select>
          <select v-model="filters.is_active" class="form-select text-sm">
            <option value="">Tất cả trạng thái</option>
            <option value="1">Đang hoạt động</option>
            <option value="0">Ngừng hoạt động</option>
          </select>
        </div>
        <div class="flex gap-2">
          <input v-model="filters.search" placeholder="Tìm theo tên chính sách hoặc mã..." class="form-input flex-1 text-sm" />
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
        </div>
      </div>
    </Transition>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span v-if="activeFilterCount > 0">
          Kết quả lọc: <strong class="text-slate-700">{{ filteredPolicies.length }}</strong> / {{ policies.length }} chính sách
        </span>
        <span v-else>
          Hiển thị <strong class="text-slate-700">{{ filteredPolicies.length }}</strong> chính sách
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 4" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="filteredPolicies.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400 text-sm">
        <p>{{ activeFilterCount > 0 ? 'Không có chính sách nào phù hợp.' : 'Chưa có chính sách SLA.' }}</p>
        <button v-if="activeFilterCount > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Tên chính sách</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mức ưu tiên</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Phân loại rủi ro</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-slate-500">Thời gian phản hồi (phút)</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-slate-500">Thời gian xử lý (giờ)</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-slate-500">Mặc định</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-slate-500">Trạng thái</th>
              <th class="px-4 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="p in filteredPolicies" :key="p.name"
              class="hover:bg-slate-50 cursor-pointer"
              @click="openDetail(p.name)"
            >
              <td class="px-4 py-3">
                <p class="font-medium text-slate-800">{{ p.policy_name }}</p>
                <p class="text-xs text-slate-400 font-mono">{{ p.name }}</p>
              </td>
              <td class="px-4 py-3">
                <span :class="['text-xs px-2 py-0.5 rounded-full font-medium', PRIORITY_BADGE[p.priority || ''] || 'bg-slate-100 text-slate-600']">
                  {{ p.priority }}
                </span>
              </td>
              <td class="px-4 py-3 text-slate-700">{{ RISK_LABEL[p.risk_class || ''] || p.risk_class || '—' }}</td>
              <td class="px-4 py-3 text-right text-slate-700">{{ p.response_time_minutes }}</td>
              <td class="px-4 py-3 text-right text-slate-700">{{ p.resolution_time_hours }}</td>
              <td class="px-4 py-3 text-center">
                <span v-if="isCheckOn(p.is_default)" class="text-xs px-2 py-0.5 rounded-full font-medium bg-purple-100 text-purple-700">★ Mặc định</span>
                <span v-else class="text-slate-300">—</span>
              </td>
              <td class="px-4 py-3 text-center">
                <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="isCheckOn(p.is_active) ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
                  {{ isCheckOn(p.is_active) ? 'Đang hoạt động' : 'Ngừng hoạt động' }}
                </span>
              </td>
              <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click.stop="openEdit(p.name)">Sửa</button>
                <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="(ev) => remove(p.name, ev)">Xóa</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Detail modal (xem) -->
    <div v-if="showDetail && detail" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showDetail = false">
      <div class="bg-white rounded-xl p-6 w-[560px] max-w-full space-y-4">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-semibold text-slate-800">{{ detail.policy_name }}</h2>
            <p class="text-xs text-slate-400 font-mono mt-0.5">{{ detail.name }}</p>
          </div>
          <button class="text-slate-400 hover:text-slate-600" @click="showDetail = false">✕</button>
        </div>

        <div class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div><span class="text-slate-500">Mức ưu tiên:</span>
            <span class="ml-2 inline-block text-xs px-2 py-0.5 rounded-full font-medium" :class="PRIORITY_BADGE[detail.priority || ''] || 'bg-slate-100 text-slate-600'">
              {{ detail.priority }}
            </span>
          </div>
          <div><span class="text-slate-500">Phân loại rủi ro:</span>
            <span class="ml-2 text-slate-800">{{ RISK_LABEL[detail.risk_class || ''] || detail.risk_class || '—' }}</span>
          </div>
          <div><span class="text-slate-500">Thời gian phản hồi:</span>
            <span class="ml-2 text-slate-800">{{ detail.response_time_minutes }} phút</span>
          </div>
          <div><span class="text-slate-500">Thời gian xử lý:</span>
            <span class="ml-2 text-slate-800">{{ detail.resolution_time_hours }} giờ</span>
          </div>
          <div><span class="text-slate-500">Hiệu lực từ:</span>
            <span class="ml-2 text-slate-800">{{ formatDate(detail.effective_date) }}</span>
          </div>
          <div><span class="text-slate-500">Hết hiệu lực:</span>
            <span class="ml-2 text-slate-800">{{ formatDate(detail.expiry_date) }}</span>
          </div>
          <div><span class="text-slate-500">Trạng thái:</span>
            <span class="ml-2 text-xs px-2 py-0.5 rounded-full font-medium" :class="isCheckOn(detail.is_active) ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
              {{ isCheckOn(detail.is_active) ? 'Đang hoạt động' : 'Ngừng hoạt động' }}
            </span>
          </div>
        </div>

        <div v-if="detail.escalation_l1_user || detail.escalation_l2_user" class="border-t pt-3 space-y-1.5">
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Người leo thang xử lý</p>
          <p v-if="detail.escalation_l1_user" class="text-sm">
            <span class="text-slate-500">L1 (sau {{ detail.escalation_l1_hours }}h):</span>
            <span class="ml-2 text-slate-800">{{ userLabel(detail.escalation_l1_user) }}</span>
            <span class="ml-1 text-xs text-slate-400 font-mono">({{ detail.escalation_l1_user }})</span>
          </p>
          <p v-if="detail.escalation_l2_user" class="text-sm">
            <span class="text-slate-500">L2 (sau {{ detail.escalation_l2_hours }}h):</span>
            <span class="ml-2 text-slate-800">{{ userLabel(detail.escalation_l2_user) }}</span>
            <span class="ml-1 text-xs text-slate-400 font-mono">({{ detail.escalation_l2_user }})</span>
          </p>
        </div>

        <div class="flex justify-end gap-2 pt-4 border-t border-slate-100">
          <button class="px-4 py-2 text-sm border border-red-300 text-red-700 rounded-lg hover:bg-red-50 font-medium" @click="remove(detail.name)">Xóa</button>
          <button class="px-4 py-2 text-sm border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 font-medium" @click="openEdit(detail.name)">Sửa</button>
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50" @click="showDetail = false">Đóng</button>
        </div>
      </div>
    </div>

    <!-- Create/edit modal -->
    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[560px] max-w-full space-y-4 max-h-[90vh] overflow-y-auto">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} chính sách SLA</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>

        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Tên chính sách <span class="text-red-500">*</span></label>
            <input v-model="form.policy_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Mức ưu tiên <span class="text-red-500">*</span></label>
            <select v-model="form.priority" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option v-for="p in PRIORITY_OPTIONS" :key="p" :value="p">{{ PRIORITY_LABEL[p] || p }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Phân loại rủi ro</label>
            <select v-model="form.risk_class" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="">— Tất cả —</option>
              <option v-for="r in RISK_OPTIONS" :key="r" :value="r">{{ RISK_LABEL[r] }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Thời gian phản hồi (phút)</label>
            <input v-model.number="form.response_time_minutes" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Thời gian xử lý (giờ)</label>
            <input v-model.number="form.resolution_time_hours" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hiệu lực từ</label>
            <DateInput v-model="form.effective_date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hết hiệu lực</label>
            <DateInput v-model="form.expiry_date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>

        <div class="border-t pt-3 space-y-3">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Người leo thang xử lý</p>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Người xử lý L1</label>
              <SmartSelect
                :model-value="(form.escalation_l1_user as string | undefined)"
                doctype="User"
                placeholder="Chọn người xử lý L1..."
                @update:model-value="(v: string) => form.escalation_l1_user = v"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">L1 sau (giờ)</label>
              <input v-model.number="form.escalation_l1_hours" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Người xử lý L2</label>
              <SmartSelect
                :model-value="(form.escalation_l2_user as string | undefined)"
                doctype="User"
                placeholder="Chọn người xử lý L2..."
                @update:model-value="(v: string) => form.escalation_l2_user = v"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">L2 sau (giờ)</label>
              <input v-model.number="form.escalation_l2_hours" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
        </div>

        <div class="space-y-2">
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_default" type="checkbox" :true-value="1" :false-value="0" /> Chính sách mặc định
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0" /> Đang hoạt động
          </label>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50" @click="showForm = false">Hủy</button>
          <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700" @click="save">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
