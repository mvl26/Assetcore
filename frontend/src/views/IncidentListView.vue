<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-12 Incident List
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm12Store } from '@/stores/useImm12Store'

const router = useRouter()
const store = useImm12Store()

const severityFilter = ref('')
const statusFilter = ref('')
const showFilters = ref(false)

const SEVERITIES = [
  { value: '', label: 'Tất cả mức độ' },
  { value: 'Low', label: 'Thấp' },
  { value: 'Medium', label: 'Trung bình' },
  { value: 'High', label: 'Cao' },
  { value: 'Critical', label: 'Nghiêm trọng' },
]

const STATUSES = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Open', label: 'Mới mở' },
  { value: 'Under Investigation', label: 'Đang điều tra' },
  { value: 'Resolved', label: 'Đã giải quyết' },
  { value: 'Closed', label: 'Đã đóng' },
  { value: 'Cancelled', label: 'Đã hủy' },
]

const SEV_COLOR: Record<string, string> = {
  Low: 'bg-green-100 text-green-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  High: 'bg-orange-100 text-orange-700',
  Critical: 'bg-red-100 text-red-700',
}

const STATUS_COLOR: Record<string, string> = {
  Open: 'bg-blue-100 text-blue-700',
  'Under Investigation': 'bg-yellow-100 text-yellow-800',
  Resolved: 'bg-purple-100 text-purple-700',
  Closed: 'bg-green-100 text-green-700',
  Cancelled: 'bg-gray-100 text-gray-500',
}

const STATUS_LABEL: Record<string, string> = {
  Open: 'Mới mở',
  'Under Investigation': 'Đang điều tra',
  Resolved: 'Đã giải quyết',
  Closed: 'Đã đóng',
  Cancelled: 'Đã hủy',
}

function formatDateTime(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleString('vi-VN')
}

interface Chip { key: 'severity' | 'status'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (severityFilter.value) {
    const s = SEVERITIES.find(x => x.value === severityFilter.value)
    chips.push({ key: 'severity', label: s?.label ?? severityFilter.value })
  }
  if (statusFilter.value) {
    const s = STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  return chips
})

const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: Chip['key']) {
  if (key === 'severity') severityFilter.value = ''
  else statusFilter.value = ''
  applyFilter()
}

function resetFilters() {
  severityFilter.value = ''
  statusFilter.value = ''
  store.fetchList()
}

function applyFilter() {
  store.fetchList({
    severity: severityFilter.value || undefined,
    status: statusFilter.value || undefined,
  })
}

// Nhấp vào badge trong bảng → lọc ngay
function quickFilter(key: 'severity' | 'status', value: string) {
  if (!value) return
  if (key === 'severity') severityFilter.value = value
  else statusFilter.value = value
  showFilters.value = false
  applyFilter()
}

function goToPage(page: number) {
  store.fetchList({
    severity: severityFilter.value || undefined,
    status: statusFilter.value || undefined,
    page,
  })
}

onMounted(() => store.fetchList())
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-5">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-12</p>
        <h1 class="text-2xl font-bold text-slate-900">Sự cố thiết bị</h1>
        <p class="text-sm text-slate-500 mt-1">Tổng <strong>{{ store.pagination.total }}</strong> sự cố</p>
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
          <span v-if="activeFilterCount > 0"
            class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-blue-500 text-white">
            {{ activeFilterCount }}
          </span>
          <svg class="w-3.5 h-3.5 transition-transform duration-200" :class="showFilters ? 'rotate-180' : ''"
               fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button class="btn-primary shrink-0" @click="router.push('/incidents/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Báo cáo sự cố
        </button>
      </div>
    </div>

    <!-- Active chips -->
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
        <button v-for="chip in activeChips" :key="chip.key"
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

    <!-- Collapsible filter panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-40"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-40"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="showFilters" class="card mb-5 p-4 space-y-3">
        <div class="flex flex-wrap gap-3 items-center">
          <div class="flex items-center gap-2">
            <label for="sev-filter" class="text-sm text-slate-600 shrink-0">Mức độ:</label>
            <select id="sev-filter" v-model="severityFilter" class="form-select text-sm" @change="applyFilter">
              <option v-for="s in SEVERITIES" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <label for="status-filter" class="text-sm text-slate-600 shrink-0">Trạng thái:</label>
            <select id="status-filter" v-model="statusFilter" class="form-select text-sm" @change="applyFilter">
              <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
        </div>
        <div v-if="activeChips.length > 0" class="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
          <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
          <button v-for="chip in activeChips" :key="chip.key"
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
            @click="clearChip(chip.key)"
          >
            {{ chip.label }}
            <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </Transition>

    <div v-if="store.error" class="alert-error mb-4">{{ store.error }}</div>

    <div class="card overflow-hidden">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ store.incidents.length }}</strong> / {{ store.pagination.total }} sự cố</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="store.loading" class="p-6 text-center text-slate-400 text-sm">Đang tải...</div>
      <div v-else-if="store.incidents.length" class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Sự cố</th>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Thiết bị</th>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Mức độ</th>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Trạng thái</th>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Thời gian</th>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">BN</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="ir in store.incidents" :key="ir.name"
              class="hover:bg-slate-50 cursor-pointer"
              @click="router.push(`/incidents/${ir.name}`)"
            >
              <td class="px-4 py-3">
                <p class="font-medium text-slate-800 truncate max-w-xs">
                  {{ ir.description?.replace(/<[^>]+>/g, '').slice(0, 70) || '—' }}
                </p>
                <p class="font-mono text-xs text-slate-400">{{ ir.name }}</p>
              </td>
              <td class="px-4 py-3">
                <div class="text-slate-700">{{ ir.asset_name || ir.asset || '—' }}</div>
                <div v-if="ir.asset && ir.asset_name" class="text-xs text-slate-400 font-mono">{{ ir.asset }}</div>
              </td>
              <!-- Severity — click để lọc -->
              <td class="px-4 py-3">
                <button
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                  :class="SEV_COLOR[ir.severity] || 'bg-gray-100 text-gray-600'"
                  :title="`Lọc: ${ir.severity}`"
                  @click.stop="quickFilter('severity', ir.severity)"
                >{{ ir.severity }}</button>
              </td>
              <!-- Status — click để lọc -->
              <td class="px-4 py-3">
                <button
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                  :class="(ir.status && STATUS_COLOR[ir.status]) || 'bg-gray-100 text-gray-600'"
                  :title="`Lọc: ${ir.status && STATUS_LABEL[ir.status] || ir.status}`"
                  @click.stop="quickFilter('status', ir.status || '')"
                >{{ (ir.status && STATUS_LABEL[ir.status]) || ir.status || '—' }}</button>
              </td>
              <td class="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                {{ formatDateTime(ir.reported_at) }}
              </td>
              <td class="px-4 py-3">
                <span v-if="ir.patient_affected" class="text-xs font-semibold text-red-600">Có</span>
                <span v-else class="text-xs text-slate-400">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có sự cố nào được báo cáo</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
        <button v-else class="btn-ghost text-xs mt-3" @click="router.push('/incidents/new')">
          + Báo cáo sự cố đầu tiên
        </button>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="store.pagination.total_pages > 1" class="flex justify-between items-center mt-4 text-sm text-slate-600">
      <span>Trang {{ store.pagination.page }} / {{ store.pagination.total_pages }}</span>
      <div class="flex gap-2">
        <button class="btn-ghost text-xs" :disabled="store.pagination.page <= 1"
                @click="goToPage(store.pagination.page - 1)">← Trước</button>
        <button class="btn-ghost text-xs" :disabled="store.pagination.page >= store.pagination.total_pages"
                @click="goToPage(store.pagination.page + 1)">Sau →</button>
      </div>
    </div>
  </div>
</template>
