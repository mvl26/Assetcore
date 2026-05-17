<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCapaStore } from '@/stores/imm00'
import type { CapaStatus } from '@/types/imm00'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

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

function clearChip(key: string) {
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
    <PageHeader
      title="Hành động Khắc phục &amp; Phòng ngừa"
      :subtitle="`Tổng ${store.pagination.total} hồ sơ`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary shrink-0" @click="router.push('/capas/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo CAPA
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      :show-search="false"
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilter"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="statusFilter" class="form-select text-sm" @change="applyFilter">
            <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <div v-if="store.error" class="alert-error mb-4">{{ store.error }}</div>

    <div class="card overflow-hidden">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ store.capas.length }}</strong> / {{ store.pagination.total }} hồ sơ</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="store.loading" class="p-6">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="!store.capas.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có CAPA nào</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <template v-else>
        <!-- Mobile cards (< sm) -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="capa in store.capas"
            :key="capa.name"
            class="mobile-card"
            @click="router.push(`/capas/${capa.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ capa.name }}</span>
              <button
                class="px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="STATUS_COLOR[capa.status] || 'bg-slate-100 text-slate-600'"
                @click.stop="quickFilter('status', capa.status)"
              >{{ STATUS_LABEL[capa.status] || capa.status }}</button>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ capa.asset_name || capa.asset || '—' }}</p>
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span :class="{ 'text-red-600': capa.severity === 'Critical', 'text-yellow-600': capa.severity === 'Major', 'text-slate-600': capa.severity === 'Minor' }">
                {{ SEV_LABEL[capa.severity] || capa.severity }}
              </span>
              <span class="text-slate-300">·</span>
              <span :class="isOverdue(capa.due_date) && capa.status !== 'Closed' ? 'text-red-600 font-semibold' : ''">
                {{ formatDate(capa.due_date) }}
              </span>
            </div>
          </div>
          <div v-if="store.capas.length === 0" class="py-12 text-center text-slate-400">
            <p class="text-sm font-medium">Không có dữ liệu</p>
          </div>
        </div>

        <!-- Desktop table (sm+) -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 border-b border-slate-200">
              <tr>
                <th class="table-header">Mã CAPA</th>
                <th class="table-header">Thiết bị</th>
                <th class="table-header">Mức độ</th>
                <th class="table-header">Trạng thái</th>
                <th class="table-header">Hạn xử lý</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="capa in store.capas" :key="capa.name"
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
                  <span
                    class="text-xs font-medium"
                    :class="{ 'text-red-600': capa.severity === 'Critical', 'text-yellow-600': capa.severity === 'Major', 'text-slate-600': capa.severity === 'Minor' }">
                    {{ SEV_LABEL[capa.severity] || capa.severity }}
                  </span>
                </td>
                <td class="px-4 py-3">
                  <button
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                    :class="STATUS_COLOR[capa.status] || 'bg-slate-100 text-slate-600'"
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
      </template>
    </div>

    <BasePagination :pagination="store.pagination" @page-change="goToPage" />
  </div>
</template>
