<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Findings (Phát hiện tuân thủ) — list.
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import type { FindingSeverity, FindingStatus } from '@/api/imm16'
import { formatDate, formatAssetDisplay } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const router = useRouter()
const route = useRoute()
const store = useImm16Store()

const items = computed(() => store.findings)
const pagination = computed(() => store.findingsPagination)
const loading = computed(() => store.findingsLoading)

const showFilters = ref(false)
const filterStatus = ref<'' | FindingStatus>((route.query.status as FindingStatus) || '')
const filterSeverity = ref<'' | FindingSeverity>((route.query.severity as FindingSeverity) || '')
const filterRule = ref<string>((route.query.rule as string) || '')
const filterAsset = ref<string>((route.query.asset as string) || '')

const STATUSES: { value: FindingStatus; label: string }[] = [
  { value: 'Open', label: 'Mở' },
  { value: 'Under Review', label: 'Đang xem xét' },
  { value: 'Confirmed NC', label: 'Đã xác nhận NC' },
  { value: 'False Positive', label: 'Sai' },
  { value: 'Waived', label: 'Đã miễn' },
  { value: 'Resolved', label: 'Đã giải quyết' },
  { value: 'Closed', label: 'Đã đóng' },
]

const chips = computed(() => {
  const c: { key: string; label: string }[] = []
  if (filterStatus.value) {
    const s = STATUSES.find(x => x.value === filterStatus.value)
    c.push({ key: 'status', label: s?.label ?? filterStatus.value })
  }
  if (filterSeverity.value) c.push({ key: 'severity', label: `Mức: ${filterSeverity.value}` })
  if (filterRule.value) c.push({ key: 'rule', label: `Quy tắc: ${filterRule.value}` })
  if (filterAsset.value) c.push({ key: 'asset', label: `Thiết bị: ${filterAsset.value}` })
  return c
})
const activeFilterCount = computed(() => chips.value.length)

function buildFilters() {
  const f: Record<string, unknown> = {}
  if (filterStatus.value) f.status = filterStatus.value
  if (filterSeverity.value) f.severity = filterSeverity.value
  if (filterRule.value) f.rule = filterRule.value
  if (filterAsset.value) f.asset = filterAsset.value
  return f
}

async function load(page = 1) {
  await store.fetchFindings(buildFilters(), page, 20)
}

function clearChip(key: string) {
  if (key === 'status') filterStatus.value = ''
  else if (key === 'severity') filterSeverity.value = ''
  else if (key === 'rule') filterRule.value = ''
  else if (key === 'asset') filterAsset.value = ''
  load(1)
}

function resetFilters() {
  filterStatus.value = ''; filterSeverity.value = ''
  filterRule.value = ''; filterAsset.value = ''
  load(1)
}

function quickFilter(value: FindingStatus) {
  filterStatus.value = value
  showFilters.value = false
  load(1)
}

watch(() => route.query, (q) => {
  filterStatus.value = (q.status as FindingStatus) || ''
  filterSeverity.value = (q.severity as FindingSeverity) || ''
  filterRule.value = (q.rule as string) || ''
  filterAsset.value = (q.asset as string) || ''
  load(1)
})

onMounted(() => load(1))
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Phát hiện tuân thủ"
      :subtitle="`IMM-16 · Theo dõi tuân thủ — Tổng ${pagination.total} phát hiện`"
      :breadcrumb="[{ label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' }, { label: 'Phát hiện' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-secondary text-sm" @click="router.push('/compliance/rules')">Xem quy tắc</button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters" :chips="chips" :show-search="false"
      @reset="resetFilters" @clear-chip="clearChip" @apply="load(1)"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filterStatus" class="form-select" @change="load(1)">
            <option value="">Tất cả</option>
            <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Mức độ</label>
          <select v-model="filterSeverity" class="form-select" @change="load(1)">
            <option value="">Tất cả</option>
            <option value="Low">Thấp</option>
            <option value="Medium">Trung bình</option>
            <option value="High">Cao</option>
            <option value="Critical">Nghiêm trọng</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Quy tắc</label>
          <input v-model="filterRule" placeholder="Mã quy tắc..." class="form-input" @keyup.enter="load(1)" />
        </div>
        <div class="form-group">
          <label class="form-label">Thiết bị</label>
          <input v-model="filterAsset" placeholder="Mã AC Asset..." class="form-input" @keyup.enter="load(1)" />
        </div>
      </template>
    </ListFilterBar>

    <div class="table-wrapper">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ items.length }}</strong> / {{ pagination.total }} phát hiện</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
      <div v-if="loading" class="p-4">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="!items.length" class="flex flex-col items-center justify-center py-16">
        <p class="text-sm text-slate-500">Chưa có phát hiện phù hợp.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="f in items"
            :key="f.name"
            class="mobile-card"
            @click="router.push(`/compliance/findings/${f.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ f.name }}</span>
              <StatusBadge :state="f.severity" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ f.rule }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ formatAssetDisplay(f.asset_name, f.asset).main }}</span>
              <span>· {{ formatDate(f.detected_date) }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã phát hiện</th>
              <th class="table-header">Quy tắc</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Mức độ</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header">CAPA</th>
              <th class="table-header">Phát hiện ngày</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="f in items" :key="f.name"
              class="hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/compliance/findings/${f.name}`)"
            >
              <td class="table-cell font-mono text-xs text-brand-700 font-semibold">{{ f.name }}</td>
              <td class="table-cell">
                <div class="font-medium text-slate-900 truncate max-w-[260px]">{{ f.rule }}</div>
              </td>
              <td class="table-cell">
                <div class="font-medium text-slate-900 truncate max-w-[200px]">
                  {{ formatAssetDisplay(f.asset_name, f.asset).main }}
                </div>
                <div v-if="formatAssetDisplay(f.asset_name, f.asset).hasBoth" class="font-mono text-xs text-brand-700 mt-0.5">
                  {{ formatAssetDisplay(f.asset_name, f.asset).sub }}
                </div>
              </td>
              <td class="table-cell"><StatusBadge :state="f.severity" /></td>
              <td class="table-cell">
                <button @click.stop="quickFilter(f.status)">
                  <StatusBadge :state="f.status" />
                </button>
              </td>
              <td class="table-cell">
                <span v-if="f.capa_ref" class="font-mono text-xs text-brand-700">{{ f.capa_ref }}</span>
                <span v-else class="text-slate-300">—</span>
              </td>
              <td class="table-cell text-xs text-slate-500">{{ formatDate(f.detected_date) }}</td>
            </tr>
          </tbody>
        </table>
        </div>
      </template>
    </div>

    <BasePagination :pagination="pagination" @page-change="load" />
  </div>
</template>
