<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCapaStore } from '@/stores/imm00'
import type { CapaStatus } from '@/types/imm00'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { translateStatus } from '@/utils/formatters'

const router = useRouter()
const route = useRoute()
const store = useCapaStore()

const statusFilter = ref<CapaStatus | ''>((route.query.status as CapaStatus) || '')
// R10 §9.4.8 — drill từ KPI qa: ?not_closed=1 (capa_open) / ?overdue=1 (capa_overdue).
const notClosed = ref<boolean>(route.query.not_closed === '1')
const overdueOnly = ref<boolean>(route.query.overdue === '1')
const showFilters = ref<boolean>(!!(route.query.status || route.query.not_closed || route.query.overdue))

// Dropdown options cho <select> lọc trạng thái. Nhãn derive qua translateStatus
// SSoT (formatters.ts) — KHỚP badge StatusBadge trên list/detail, KHÔNG drift.
// Giá trị (value) giữ CODE English để gửi cho BE; chỉ nhãn hiển thị là VI.
const STATUS_CODES: (CapaStatus | '')[] = ['', 'Open', 'In Progress', 'Pending Verification', 'Closed', 'Overdue']
const STATUSES = computed<{ value: CapaStatus | ''; label: string }[]>(() =>
  STATUS_CODES.map(v => ({ value: v, label: v === '' ? 'Tất cả' : translateStatus(v) })))

interface Chip { key: 'status' | 'notClosed' | 'overdue'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (overdueOnly.value) chips.push({ key: 'overdue', label: 'Quá hạn' })
  else if (notClosed.value) chips.push({ key: 'notClosed', label: 'Chưa đóng' })
  if (statusFilter.value) {
    chips.push({ key: 'status', label: translateStatus(statusFilter.value) })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'status') statusFilter.value = ''
  else if (key === 'notClosed') notClosed.value = false
  else if (key === 'overdue') overdueOnly.value = false
  applyFilter()
}

function resetFilters() {
  statusFilter.value = ''
  notClosed.value = false
  overdueOnly.value = false
  store.fetchList()
}

function quickFilter(_key: 'status', value: string) {
  if (!value) return
  statusFilter.value = value as CapaStatus
  showFilters.value = false
  applyFilter()
}

function buildParams(extra: Record<string, unknown> = {}) {
  return {
    status: statusFilter.value || undefined,
    not_closed: notClosed.value ? 1 : undefined,
    overdue: overdueOnly.value ? 1 : undefined,
    ...extra,
  }
}

function applyFilter() {
  store.fetchList(buildParams())
}

function goToPage(page: number) {
  store.fetchList(buildParams({ page }))
}

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function isOverdue(date?: string) {
  if (!date) return false
  return new Date(date) < new Date()
}

onMounted(() => applyFilter())
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
          Tạo hành động khắc phục/phòng ngừa
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
        <p class="text-sm">Không có hành động khắc phục/phòng ngừa nào</p>
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
                :title="`Lọc: ${translateStatus(capa.status)}`"
                @click.stop="quickFilter('status', capa.status)"
              ><StatusBadge :state="capa.status" /></button>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ capa.asset_name || capa.asset || '—' }}</p>
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <StatusBadge :state="capa.severity" size="xs" />
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
                <th class="table-header">Mã hành động khắc phục/phòng ngừa</th>
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
                  <StatusBadge :state="capa.severity" />
                </td>
                <td class="px-4 py-3">
                  <button
                    class="transition-all hover:ring-2 hover:ring-offset-1 hover:ring-brand-300 rounded-full"
                    :title="`Lọc: ${translateStatus(capa.status)}`"
                    @click.stop="quickFilter('status', capa.status)"
                  ><StatusBadge :state="capa.status" /></button>
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
