<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCapaStore } from '@/stores/imm00'
import type { CapaStatus } from '@/types/imm00'

const router = useRouter()
const store = useCapaStore()

const statusFilter = ref<CapaStatus | ''>('')
const showFilters = ref(false)

const STATUSES: { value: CapaStatus | ''; label: string }[] = [
  { value: '', label: 'Tất cả' },
  { value: 'Open', label: 'Mở' },
  { value: 'In Progress', label: 'Đang xử lý' },
  { value: 'Pending Verification', label: 'Chờ xác minh' },
  { value: 'Closed', label: 'Đã đóng' },
  { value: 'Overdue', label: 'Quá hạn' },
]

const STATUS_COLOR: Record<string, string> = {
  'Open': 'bg-blue-100 text-blue-700',
  'In Progress': 'bg-yellow-100 text-yellow-700',
  'Pending Verification': 'bg-purple-100 text-purple-700',
  'Closed': 'bg-green-100 text-green-700',
  'Overdue': 'bg-red-100 text-red-700',
}

const STATUS_LABEL: Record<string, string> = {
  'Open': 'Mới mở',
  'In Progress': 'Đang xử lý',
  'Pending Verification': 'Chờ xác nhận',
  'Closed': 'Đã đóng',
  'Overdue': 'Quá hạn',
}

const SEV_LABEL: Record<string, string> = {
  'Critical': 'Nghiêm trọng',
  'Major': 'Quan trọng',
  'Minor': 'Nhỏ',
}

interface Chip { key: 'status'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (statusFilter.value) {
    const s = STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: Chip['key']) {
  if (key === 'status') statusFilter.value = ''
  applyFilter()
}

function resetFilters() {
  statusFilter.value = ''
  store.fetchList()
}

function quickFilter(_key: 'status', value: string) {
  if (!value) return
  statusFilter.value = value as CapaStatus
  showFilters.value = false
  applyFilter()
}

function applyFilter() {
  store.fetchList({ status: statusFilter.value || undefined })
}

function goToPage(page: number) {
  store.fetchList({ status: statusFilter.value || undefined, page })
}

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function isOverdue(date?: string) {
  if (!date) return false
  return new Date(date) < new Date()
}

onMounted(() => store.fetchList())
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-5">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00</p>
        <h1 class="text-2xl font-bold text-slate-900">Hành động Khắc phục &amp; Phòng ngừa</h1>
        <p class="text-sm text-slate-500 mt-1">Tổng <strong>{{ store.pagination.total }}</strong> hồ sơ</p>
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
        <button class="btn-primary shrink-0" @click="router.push('/capas/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo CAPA
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
            <label for="capa-status-filter" class="text-sm text-slate-600 shrink-0">Trạng thái:</label>
            <select id="capa-status-filter" v-model="statusFilter" class="form-select text-sm" @change="applyFilter">
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
        <span>Hiển thị <strong class="text-slate-700">{{ store.capas.length }}</strong> / {{ store.pagination.total }} hồ sơ</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="store.loading" class="p-6 text-center text-slate-400 text-sm">Đang tải...</div>
      <div v-else-if="store.capas.length" class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Mã CAPA</th>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Thiết bị</th>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Mức độ</th>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Trạng thái</th>
              <th class="text-left px-4 py-3 font-semibold text-slate-600">Hạn xử lý</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="capa in store.capas" :key="capa.name"
              class="hover:bg-slate-50 cursor-pointer transition-all hover:translate-x-0.5"
              @click="router.push(`/capas/${capa.name}`)"
            >
              <td class="px-4 py-3">
                <p class="font-mono text-xs text-slate-700">{{ capa.name }}</p>
                <p v-if="capa.title" class="text-xs text-slate-400 mt-0.5">{{ capa.title }}</p>
              </td>
              <td class="px-4 py-3">
                <div class="text-slate-700 text-sm">{{ capa.asset_name || capa.asset || '—' }}</div>
                <div v-if="capa.asset && capa.asset_name" class="text-xs text-slate-400 font-mono">{{ capa.asset }}</div>
              </td>
              <td class="px-4 py-3">
                <span class="text-xs font-medium"
                  :class="{ 'text-red-600': capa.severity === 'Critical', 'text-yellow-600': capa.severity === 'Major', 'text-slate-600': capa.severity === 'Minor' }">
                  {{ SEV_LABEL[capa.severity] || capa.severity }}
                </span>
              </td>
              <td class="px-4 py-3">
                <button
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                  :class="STATUS_COLOR[capa.status] || 'bg-gray-100 text-gray-600'"
                  :title="`Lọc: ${STATUS_LABEL[capa.status] || capa.status}`"
                  @click.stop="quickFilter('status', capa.status)"
                >{{ STATUS_LABEL[capa.status] || capa.status }}</button>
              </td>
              <td class="px-4 py-3">
                <span :class="isOverdue(capa.due_date) && capa.status !== 'Closed' ? 'text-red-600 font-semibold' : 'text-slate-600'" class="text-xs">
                  {{ formatDate(capa.due_date) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có CAPA nào</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>

    <div v-if="store.pagination.total_pages > 1" class="flex justify-between items-center mt-4 text-sm text-slate-600">
      <span>Trang {{ store.pagination.page }} / {{ store.pagination.total_pages }}</span>
      <div class="flex gap-2">
        <button class="btn-ghost text-xs" :disabled="store.pagination.page <= 1" @click="goToPage(store.pagination.page - 1)">← Trước</button>
        <button class="btn-ghost text-xs" :disabled="store.pagination.page >= store.pagination.total_pages" @click="goToPage(store.pagination.page + 1)">Sau →</button>
      </div>
    </div>
  </div>
</template>
