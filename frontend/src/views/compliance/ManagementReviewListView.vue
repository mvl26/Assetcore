<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Soát xét quản lý (Management Review) — list / create / finalize.
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import type { ManagementReview } from '@/api/imm16'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'

const router = useRouter()
const store = useImm16Store()
const api = useApi()

function goDetail(r: ManagementReview) {
  router.push(`/compliance/mr/${r.name}`)
}
function scorecardDisplay(r: ManagementReview): string {
  const x = r as ManagementReview & { scorecard_score_pct?: number; scorecard_period?: string }
  if (x.scorecard_score_pct != null) {
    return `${x.scorecard_score_pct.toFixed(1)}%${x.scorecard_period ? ' · ' + x.scorecard_period : ''}`
  }
  return r.scorecard_ref || '—'
}

const items = computed(() => store.reviews)
const pagination = computed(() => store.reviewsPagination)
const loading = computed(() => store.reviewsLoading)

const showFilters = ref(false)
const filterStatus = ref<string>('')

const MR_STATUSES: { value: string; label: string }[] = [
  { value: 'Draft',           label: 'Bản nháp' },
  { value: 'Held',            label: 'Đã họp' },
  { value: 'Minutes Approved', label: 'Biên bản đã duyệt' },
  { value: 'Closed',          label: 'Đã đóng' },
]

const chips = computed(() => {
  const c: { key: string; label: string }[] = []
  if (filterStatus.value) {
    const s = MR_STATUSES.find(x => x.value === filterStatus.value)
    c.push({ key: 'status', label: s?.label ?? filterStatus.value })
  }
  return c
})
const activeFilterCount = computed(() => chips.value.length)

function chairDisplay(r: ManagementReview): string {
  const x = r as ManagementReview & { chair_name?: string }
  return x.chair_name || r.chair || '—'
}

function buildFilters() {
  const f: Record<string, unknown> = {}
  if (filterStatus.value) f.status = filterStatus.value
  return f
}

async function load(page = 1) {
  await store.fetchManagementReviews(buildFilters(), page, 20)
}
function clearChip(_k: string) { filterStatus.value = ''; load(1) }
function resetFilters() { filterStatus.value = ''; load(1) }

// ── Create modal ──
const showCreate = ref(false)
const form = ref<Partial<ManagementReview>>({
  quarter: '', review_date: '', chair: '', scorecard_ref: '',
})
function openCreate() {
  form.value = { quarter: '', review_date: '', chair: '', scorecard_ref: '' }
  showCreate.value = true
}
async function submitCreate() {
  const res = await api.run(() => store.actionCreateReview(form.value), {
    successMessage: 'Đã tạo soát xét',
  })
  if (res) { showCreate.value = false; load(1) }
}

onMounted(() => load(1))
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Soát xét quản lý"
      :subtitle="`IMM-16 · Theo dõi tuân thủ — Tổng ${pagination.total} cuộc soát xét`"
      :breadcrumb="[{ label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' }, { label: 'Soát xét quản lý' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo soát xét
        </button>
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
            <option v-for="s in MR_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <div class="table-wrapper">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ items.length }}</strong> / {{ pagination.total }}</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
      <div v-if="loading" class="p-4"><SkeletonLoader variant="table" :rows="5" /></div>
      <div v-else-if="!items.length" class="flex flex-col items-center justify-center py-16">
        <p class="text-sm text-slate-500">Chưa có cuộc soát xét quản lý phù hợp.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
        <button v-else class="btn-primary mt-3" @click="openCreate">Tạo cuộc soát xét đầu tiên</button>
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="r in items"
            :key="r.name"
            class="mobile-card cursor-pointer"
            @click="goDetail(r)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ r.name }}</span>
              <StatusBadge :state="r.status" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ r.quarter }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ formatDate(r.review_date) }}</span>
              <span>· {{ chairDisplay(r) }}</span>
              <span>· {{ scorecardDisplay(r) }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Quý</th>
              <th class="table-header">Ngày soát xét</th>
              <th class="table-header">Chủ tịch</th>
              <th class="table-header">Scorecard</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header">Kế hoạch tới</th>
              <th class="table-header text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="r in items" :key="r.name" class="hover:bg-slate-50 cursor-pointer" @click="goDetail(r)">
              <td class="table-cell">
                <div class="font-medium text-slate-900">{{ r.quarter }}</div>
                <div class="font-mono text-xs text-brand-700 mt-0.5">{{ r.name }}</div>
              </td>
              <td class="table-cell text-slate-600">{{ formatDate(r.review_date) }}</td>
              <td class="table-cell text-slate-800">{{ chairDisplay(r) }}</td>
              <td class="table-cell">
                <span class="text-xs text-slate-700">{{ scorecardDisplay(r) }}</span>
              </td>
              <td class="table-cell"><StatusBadge :state="r.status" /></td>
              <td class="table-cell text-slate-600">{{ formatDate(r.next_review_date) }}</td>
              <td class="table-cell text-right">
                <button class="text-xs text-brand-600 hover:text-brand-700 font-medium" @click.stop="goDetail(r)">Xem / Xử lý</button>
              </td>
            </tr>
          </tbody>
        </table>
        </div>
      </template>
    </div>

    <BasePagination :pagination="pagination" @page-change="load" />

    <!-- Create Modal -->
    <BaseModal v-if="showCreate" title="Tạo soát xét quản lý" size="lg" @close="showCreate = false">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div class="form-group">
          <label class="form-label">Quý (VD: Q2-2026) *</label>
          <input v-model="form.quarter" class="form-input" placeholder="Q2-2026" />
        </div>
        <div class="form-group">
          <label class="form-label">Ngày soát xét *</label>
          <input v-model="form.review_date" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Chủ tịch (User email)</label>
          <input v-model="form.chair" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Scorecard ref</label>
          <input v-model="form.scorecard_ref" class="form-input" placeholder="SCR-2026-..." />
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showCreate = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="submitCreate">
          {{ api.loading.value ? 'Đang lưu…' : 'Tạo soát xét' }}
        </button>
      </template>
    </BaseModal>

  </div>
</template>
