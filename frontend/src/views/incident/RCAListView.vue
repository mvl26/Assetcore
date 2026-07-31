<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — RCA List (route /rca)
// Mockup: docs/fe/12-incident/rca-list.html. BE: assetcore.api.imm12.list_rcas.
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm12Store } from '@/stores/imm12'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { rcaStatusLabel, rcaStatusClass, rcaTriggerLabel } from '@/constants/labels'

const router = useRouter()
const route = useRoute()
const store = useImm12Store()

const methodFilter = ref('')
const statusFilter = ref('')
// Lọc theo thiết bị — drill từ «Xem tất cả» trong tab «Bản ghi liên quan» của một thiết
// bị (?asset=<mã>, AC-CR-91). Khoá ĐỘC LẬP với method/status: cộng dồn (AND).
// Đường xuống BE đã sẵn: store.fetchRcas({asset}) → api/imm12.listRcas → list_rcas(asset=…).
const assetFilter = ref<string>(_queryAsset())
const showFilters = ref<boolean>(!!_queryAsset())

/** Giá trị `?asset=` hiện tại (chuỗi rỗng nếu không có) — Vue Router có thể trả mảng. */
function _queryAsset(): string {
  const raw = route.query.asset
  const val = Array.isArray(raw) ? raw[0] : raw
  return typeof val === 'string' ? val : ''
}

const METHODS = [
  { value: '', label: 'Tất cả phương pháp' },
  { value: '5-Why', label: '5-Why' },
  { value: 'Fishbone', label: 'Fishbone (Ishikawa)' },
  { value: 'FTA', label: 'Phân tích cây lỗi' },
]

const STATUSES = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'RCA Required', label: 'Cần phân tích' },
  { value: 'RCA In Progress', label: 'Đang phân tích' },
  { value: 'Completed', label: 'Đã hoàn tất' },
  { value: 'Cancelled', label: 'Đã hủy' },
]

interface Chip { key: 'method' | 'status' | 'asset'; label: string }
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
  // Người dùng phải THẤY mình đang lọc theo thiết bị và bỏ lọc được (ADR D-CR5-7 vế 3).
  if (assetFilter.value) {
    chips.push({ key: 'asset', label: `Thiết bị: ${assetFilter.value}` })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function applyFilter(page = 1) {
  store.fetchRcas({
    method: methodFilter.value || undefined,
    status: statusFilter.value || undefined,
    asset: assetFilter.value || undefined,
    page,
  })
}

function resetFilters() {
  methodFilter.value = ''
  statusFilter.value = ''
  assetFilter.value = ''
  store.fetchRcas()
}

function clearChip(key: string) {
  if (key === 'method') methodFilter.value = ''
  else if (key === 'asset') assetFilter.value = ''
  else statusFilter.value = ''
  applyFilter()
}

// Drill lần 2 trên CÙNG route (bấm «Xem tất cả» từ thiết bị B khi đang lọc theo A):
// không có watch này thì màn hình không đổi gì — im lặng và khó chẩn đoán nhất.
watch(() => route.query.asset, () => {
  assetFilter.value = _queryAsset()
  if (assetFilter.value) showFilters.value = true
  applyFilter()
})

// Lọc NGAY từ lần nạp đầu (không nạp-rồi-lọc-lại: hai lời gọi mạng + một nhịp nháy
// dữ liệu sai) — ADR D-CR5-7 vế 1.
onMounted(() => applyFilter())
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Phân tích nguyên nhân gốc"
      :subtitle="`${store.rcaPagination.total} hồ sơ phân tích nguyên nhân gốc · Bắt buộc cho sự cố nghiêm trọng / lặp lại`"
      :breadcrumb="[{ label: 'IMM-12 · Sự cố', to: '/incidents/dashboard' }, { label: 'Phân tích nguyên nhân gốc' }]"
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
          <label class="form-label" for="rca-filter-method">Phương pháp</label>
          <select id="rca-filter-method" v-model="methodFilter" class="form-select">
            <option v-for="m in METHODS" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="rca-filter-status">Trạng thái</label>
          <select id="rca-filter-status" v-model="statusFilter" class="form-select">
            <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="rca-filter-asset">Thiết bị</label>
          <input
            id="rca-filter-asset"
            v-model="assetFilter"
            class="form-input"
            placeholder="Mã thiết bị…"
          />
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
              <th class="table-header">Mã phân tích nguyên nhân gốc</th>
              <th class="table-header">Sự cố nguồn</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Phương pháp</th>
              <th class="table-header">Người phụ trách</th>
              <th class="table-header">Hành động khắc phục/phòng ngừa</th>
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
        <p class="text-sm font-medium text-slate-500">Chưa có hồ sơ phân tích nguyên nhân gốc nào</p>
        <p class="text-xs mt-1">Phân tích nguyên nhân gốc được tạo tự động từ sự cố mức Cao/Nghiêm trọng hoặc lỗi lặp lại.</p>
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
