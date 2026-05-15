<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team Incident List
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm12Store } from '@/stores/imm12'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

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
  { value: 'Acknowledged', label: 'Đã tiếp nhận' },
  { value: 'In Progress', label: 'Đang điều tra' },
  { value: 'RCA Required', label: 'Cần RCA' },
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

function clearChip(key: string) {
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
    <PageHeader
      title="Sự cố thiết bị"
      :subtitle="`Tổng ${store.pagination.total} sự cố`"
      :breadcrumb="[{ label: 'IMM-12 · Sự cố', to: '/incidents/dashboard' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary" @click="router.push('/incidents/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Báo cáo sự cố
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
          <label class="form-label">Mức độ</label>
          <select v-model="severityFilter" class="form-select">
            <option v-for="s in SEVERITIES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="statusFilter" class="form-select">
            <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <div v-if="store.error" class="alert-error mb-4">{{ store.error }}</div>

    <!-- Loading -->
    <div v-if="store.loading" class="table-wrapper">
      <SkeletonLoader variant="table" :rows="6" />
    </div>

    <template v-else>
      <!-- Info row (shared) -->
      <div class="flex items-center justify-between text-xs text-slate-500 pb-1 sm:hidden">
        <span>Hiển thị <strong class="text-slate-700">{{ store.incidents.length }}</strong> / {{ store.pagination.total }} sự cố</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <!-- Mobile cards (< sm) -->
      <div class="mobile-card-list sm:hidden">
        <div
          v-for="ir in store.incidents"
          :key="ir.name"
          class="mobile-card"
          @click="router.push(`/incidents/${ir.name}`)"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-sm font-semibold text-brand-700">{{ ir.name }}</span>
            <button @click.stop="quickFilter('status', ir.status || '')">
              <StatusBadge :state="ir.status || ''" />
            </button>
          </div>
          <p class="text-sm font-medium text-slate-900 truncate">{{ ir.asset_name || ir.asset || '—' }}</p>
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
            <button
              class="px-1.5 py-0.5 rounded text-[11px] font-medium"
              :class="SEV_COLOR[ir.severity] || 'bg-slate-100 text-slate-600'"
              @click.stop="quickFilter('severity', ir.severity)"
            >{{ ir.severity }}</button>
            <span class="text-slate-300">·</span>
            <span>{{ formatDateTime(ir.reported_at) }}</span>
            <span v-if="ir.patient_affected" class="text-red-600 font-semibold">BN: Có</span>
          </div>
        </div>
        <div v-if="store.incidents.length === 0" class="py-12 text-center text-slate-400">
          <p class="text-sm font-medium">Không có sự cố nào được báo cáo</p>
        </div>
      </div>

      <!-- Desktop table (sm+) -->
      <div class="hidden sm:block table-wrapper">
        <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
          <span>Hiển thị <strong class="text-slate-700">{{ store.incidents.length }}</strong> / {{ store.pagination.total }} sự cố</span>
          <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
        </div>
        <div v-if="store.incidents.length" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-100">
            <thead>
              <tr>
                <th class="table-header">Sự cố</th>
                <th class="table-header">Thiết bị</th>
                <th class="table-header">Mức độ</th>
                <th class="table-header">Trạng thái</th>
                <th class="table-header">Thời gian</th>
                <th class="table-header">BN</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="ir in store.incidents" :key="ir.name"
                class="hover:bg-slate-50 cursor-pointer transition-colors"
                @click="router.push(`/incidents/${ir.name}`)"
              >
                <td class="table-cell">
                  <p class="font-medium text-slate-800 truncate max-w-xs">
                    {{ ir.description?.replace(/<[^>]+>/g, '').slice(0, 70) || '—' }}
                  </p>
                  <p class="font-mono text-xs text-slate-400 mt-0.5">{{ ir.name }}</p>
                </td>
                <td class="table-cell">
                  <div class="text-slate-700">{{ ir.asset_name || ir.asset || '—' }}</div>
                  <div v-if="ir.asset && ir.asset_name" class="text-xs text-slate-400 font-mono mt-0.5">{{ ir.asset }}</div>
                </td>
                <td class="table-cell">
                  <button
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                    :class="SEV_COLOR[ir.severity] || 'bg-slate-100 text-slate-600'"
                    @click.stop="quickFilter('severity', ir.severity)"
                  >{{ ir.severity }}</button>
                </td>
                <td class="table-cell">
                  <button @click.stop="quickFilter('status', ir.status || '')">
                    <StatusBadge :state="ir.status || ''" />
                  </button>
                </td>
                <td class="table-cell text-slate-500 text-xs whitespace-nowrap">{{ formatDateTime(ir.reported_at) }}</td>
                <td class="table-cell">
                  <span v-if="ir.patient_affected" class="text-xs font-semibold text-red-600">Có</span>
                  <span v-else class="text-xs text-slate-400">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
          <svg class="w-10 h-10 text-slate-200 mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          <p class="text-sm font-medium text-slate-500">Không có sự cố nào được báo cáo</p>
          <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
            Xóa bộ lọc để xem tất cả
          </button>
          <button v-else class="btn-ghost text-xs mt-3" @click="router.push('/incidents/new')">
            + Báo cáo sự cố đầu tiên
          </button>
        </div>
      </div>
    </template>

    <BasePagination :pagination="store.pagination" @page-change="goToPage" />
  </div>
</template>
