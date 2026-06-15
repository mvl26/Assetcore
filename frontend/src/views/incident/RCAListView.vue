<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — RCA List (route /rca)
// Mockup: docs/fe/12-incident/rca-list.html. BE: assetcore.api.imm12.list_rcas.
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm12Store } from '@/stores/imm12'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { rcaStatusLabel, rcaStatusClass, rcaTriggerLabel } from '@/constants/labels'

const router = useRouter()
const store = useImm12Store()

const methodFilter = ref('')
const statusFilter = ref('')
const showFilters = ref(false)

const METHODS = [
  { value: '', label: 'Tất cả phương pháp' },
  { value: '5-Why', label: '5-Why' },
  { value: 'Fishbone', label: 'Fishbone (Ishikawa)' },
  { value: 'FTA', label: 'FTA (cây lỗi)' },
]

const STATUSES = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'RCA Required', label: 'Cần phân tích' },
  { value: 'RCA In Progress', label: 'Đang phân tích' },
  { value: 'Completed', label: 'Đã hoàn tất' },
  { value: 'Cancelled', label: 'Đã hủy' },
]

interface Chip { key: 'method' | 'status'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (methodFilter.value) {
    const m = METHODS.find(x => x.value === methodFilter.value)
    chips.push({ key: 'method', label: m?.label ?? methodFilter.value })
  }
  if (statusFilter.value) {
    const s = STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function applyFilter(page = 1) {
  store.fetchRcas({
    method: methodFilter.value || undefined,
    status: statusFilter.value || undefined,
    page,
  })
}

function resetFilters() {
  methodFilter.value = ''
  statusFilter.value = ''
  store.fetchRcas()
}

function clearChip(key: string) {
  if (key === 'method') methodFilter.value = ''
  else statusFilter.value = ''
  applyFilter()
}

onMounted(() => store.fetchRcas())
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Phân tích nguyên nhân gốc (RCA)"
      :subtitle="`${store.rcaPagination.total} hồ sơ RCA · Bắt buộc cho sự cố nghiêm trọng / lặp lại`"
      :breadcrumb="[{ label: 'IMM-12 · Sự cố', to: '/incidents/dashboard' }, { label: 'RCA' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-ghost" @click="router.push('/incidents/list')">Danh sách sự cố</button>
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
          <label class="form-label">Phương pháp</label>
          <select v-model="methodFilter" class="form-select">
            <option v-for="m in METHODS" :key="m.value" :value="m.value">{{ m.label }}</option>
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

    <div v-if="store.rcaError" class="alert-error mb-4">{{ store.rcaError }}</div>

    <div v-if="store.rcaLoading" class="table-wrapper">
      <SkeletonLoader variant="table" :rows="6" />
    </div>

    <div v-else class="table-wrapper">
      <!-- Mobile cards (< sm) — P1 table→card: mỗi RCA 1 card (mã/sự cố/thiết bị/trạng thái). -->
      <div v-if="store.rcaListItems.length" class="mobile-card-list sm:hidden">
        <div
          v-for="rca in store.rcaListItems"
          :key="rca.name"
          class="mobile-card"
          @click="router.push(`/rca/${rca.name}`)"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-sm font-semibold text-brand-700">{{ rca.name }}</span>
            <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium leading-none whitespace-nowrap', rcaStatusClass(rca.status)]">
              {{ rcaStatusLabel(rca.status) }}
            </span>
          </div>
          <p class="text-sm font-medium text-slate-900 truncate" :title="rca.asset">
            {{ rca.asset_name ?? rca.asset ?? '—' }}
          </p>
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
            <span v-if="rca.incident_report" class="font-mono">{{ rca.incident_report }}</span>
            <span v-else>{{ rca.trigger_type ? rcaTriggerLabel(rca.trigger_type) : '—' }}</span>
            <span class="text-slate-300">·</span>
            <span>{{ rca.rca_method || '—' }}</span>
            <template v-if="rca.linked_capa">
              <span class="text-slate-300">·</span>
              <span class="text-purple-600 font-mono">{{ rca.linked_capa }}</span>
            </template>
          </div>
        </div>
      </div>

      <!-- Desktop table (sm+) — P3: giữ overflow-x-auto quanh bảng. -->
      <div v-if="store.rcaListItems.length" class="hidden sm:block overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã RCA</th>
              <th class="table-header">Sự cố nguồn</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Phương pháp</th>
              <th class="table-header">Người phụ trách</th>
              <th class="table-header">CAPA</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="rca in store.rcaListItems" :key="rca.name"
              class="hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/rca/${rca.name}`)"
            >
              <td class="table-cell font-mono text-xs text-brand-700 font-semibold">{{ rca.name }}</td>
              <td class="table-cell">
                <span v-if="rca.incident_report" class="font-mono text-xs text-slate-600">{{ rca.incident_report }}</span>
                <span v-else class="text-xs text-slate-400">{{ rca.trigger_type ? rcaTriggerLabel(rca.trigger_type) : '—' }}</span>
              </td>
              <td class="table-cell">
                <div class="text-slate-700" :title="rca.asset">{{ rca.asset_name ?? rca.asset ?? '—' }}</div>
              </td>
              <td class="table-cell text-slate-600 text-sm">{{ rca.rca_method || '—' }}</td>
              <td class="table-cell text-slate-600 text-sm" :title="rca.assigned_to">{{ rca.assigned_to_name ?? rca.assigned_to ?? '—' }}</td>
              <td class="table-cell">
                <button
                  v-if="rca.linked_capa"
                  class="font-mono text-xs text-purple-600 hover:underline"
                  @click.stop="router.push(`/capas/${rca.linked_capa}`)"
                >{{ rca.linked_capa }}</button>
                <span v-else class="text-xs text-slate-400">—</span>
              </td>
              <td class="table-cell">
                <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', rcaStatusClass(rca.status)]">
                  {{ rcaStatusLabel(rca.status) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm font-medium text-slate-500">Chưa có hồ sơ RCA nào</p>
        <p class="text-xs mt-1">RCA được tạo tự động từ sự cố mức Cao/Nghiêm trọng hoặc lỗi lặp lại.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
        <button v-else class="btn-ghost text-xs mt-3" @click="router.push('/incidents/list')">
          Đi tới danh sách sự cố
        </button>
      </div>
    </div>

    <BasePagination :pagination="store.rcaPagination" @page-change="applyFilter" />
  </div>
</template>
