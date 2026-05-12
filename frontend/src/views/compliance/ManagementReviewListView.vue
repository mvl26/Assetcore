<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Soát xét quản lý (Management Review) — list / create / finalize.
import { ref, computed, onMounted } from 'vue'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import type { ManagementReview, MROutputAction } from '@/api/imm16'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'

const store = useImm16Store()
const api = useApi()

const items = computed(() => store.reviews)
const pagination = computed(() => store.reviewsPagination)
const loading = computed(() => store.reviewsLoading)

const showFilters = ref(false)
const filterStatus = ref<string>('')

const chips = computed(() => {
  const c: { key: string; label: string }[] = []
  if (filterStatus.value) c.push({ key: 'status', label: filterStatus.value })
  return c
})
const activeFilterCount = computed(() => chips.value.length)

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

// ── Finalize modal ──
const showFinalize = ref(false)
const finalizing = ref<ManagementReview | null>(null)
const minutesDoc = ref('')
const outputActions = ref<MROutputAction[]>([{ action: '', owner: '', due_date: '' }])

function openFinalize(r: ManagementReview) {
  finalizing.value = r
  minutesDoc.value = r.minutes_doc || ''
  outputActions.value = [{ action: '', owner: '', due_date: '' }]
  showFinalize.value = true
}
function addAction() { outputActions.value.push({ action: '', owner: '', due_date: '' }) }
function removeAction(i: number) {
  outputActions.value.splice(i, 1)
  if (outputActions.value.length === 0) addAction()
}

async function submitFinalize() {
  if (!finalizing.value) return
  const actions = outputActions.value.filter(a => a.action.trim() && a.owner.trim())
  const res = await api.run(
    () => store.actionFinalizeReview(finalizing.value!.name, minutesDoc.value, actions),
    { successMessage: 'Đã đóng soát xét quản lý' },
  )
  if (res) { showFinalize.value = false; load(pagination.value.page) }
}

onMounted(() => load(1))
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Soát xét quản lý"
      :subtitle="`Tổng ${pagination.total} cuộc soát xét`"
      :breadcrumb="[{ label: 'IMM-16 · Tuân thủ' }, { label: 'Soát xét quản lý' }]"
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
            <option value="Draft">Bản nháp</option>
            <option value="In Progress">Đang thực hiện</option>
            <option value="Closed">Đã đóng</option>
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
      <div v-else-if="!items.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm font-medium">Chưa có cuộc soát xét nào</p>
      </div>
      <div v-else class="overflow-x-auto">
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
            <tr v-for="r in items" :key="r.name" class="hover:bg-slate-50">
              <td class="table-cell">
                <div class="font-medium text-slate-900">{{ r.quarter }}</div>
                <div class="text-xs text-slate-400 font-mono mt-0.5">{{ r.name }}</div>
              </td>
              <td class="table-cell text-slate-600">{{ formatDate(r.review_date) }}</td>
              <td class="table-cell text-slate-600">{{ r.chair || '—' }}</td>
              <td class="table-cell">
                <span v-if="r.scorecard_ref" class="font-mono text-xs text-blue-600">{{ r.scorecard_ref }}</span>
                <span v-else class="text-slate-300">—</span>
              </td>
              <td class="table-cell"><StatusBadge :state="r.status" /></td>
              <td class="table-cell text-slate-600">{{ formatDate(r.next_review_date) }}</td>
              <td class="table-cell text-right">
                <button v-if="r.status !== 'Closed'"
                        class="text-xs text-emerald-700 hover:text-emerald-900 font-medium"
                        @click="openFinalize(r)">Đóng & xuất biên bản</button>
                <span v-else class="text-xs text-slate-400">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <BasePagination :pagination="pagination" @page-change="load" />

    <!-- Create Modal -->
    <BaseModal v-if="showCreate" title="Tạo soát xét quản lý" size="lg" @close="showCreate = false">
      <div class="space-y-3 grid grid-cols-2 gap-3">
        <div class="form-group">
          <label class="form-label">Quý (VD: 2026-Q1) *</label>
          <input v-model="form.quarter" class="form-input" placeholder="2026-Q2" />
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
        <button class="btn-ghost" @click="showCreate = false">Hủy</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="submitCreate">Tạo</button>
      </template>
    </BaseModal>

    <!-- Finalize Modal -->
    <BaseModal v-if="showFinalize" title="Đóng cuộc soát xét quản lý" size="xl" @close="showFinalize = false">
      <div class="space-y-4">
        <p v-if="finalizing" class="text-sm text-slate-500">
          {{ finalizing.quarter }} — {{ formatDate(finalizing.review_date) }}
        </p>
        <div class="form-group">
          <label class="form-label">URL biên bản (minutes) *</label>
          <input v-model="minutesDoc" class="form-input" placeholder="https://..." />
        </div>
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="form-label !mb-0">Hành động đầu ra</label>
            <button class="text-xs text-blue-600 hover:underline" @click="addAction">+ Thêm hành động</button>
          </div>
          <table class="min-w-full divide-y divide-slate-100">
            <thead>
              <tr>
                <th class="table-header">Mô tả</th>
                <th class="table-header w-48">Người phụ trách</th>
                <th class="table-header w-40">Hạn</th>
                <th class="table-header w-12"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="(a, i) in outputActions" :key="i">
                <td class="table-cell"><input v-model="a.action" class="form-input text-sm" /></td>
                <td class="table-cell"><input v-model="a.owner" class="form-input text-sm" placeholder="user@hospital.vn" /></td>
                <td class="table-cell"><input v-model="a.due_date" type="date" class="form-input text-sm" /></td>
                <td class="table-cell text-right">
                  <button class="text-xs text-red-500 hover:text-red-700" @click="removeAction(i)">×</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showFinalize = false">Hủy</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="submitFinalize">Đóng soát xét</button>
      </template>
    </BaseModal>
  </div>
</template>
