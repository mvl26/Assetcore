<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import type { EvalState } from '@/types/imm03'
import { stateLabel, formatVnDate } from '@/utils/wave2Labels'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar, { type FilterChip } from '@/components/common/ListFilterBar.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const router = useRouter()
const store  = useImm03Store()

const EVAL_STATES: EvalState[] = ['Draft', 'Open RFQ', 'Quotation Received', 'Evaluated', 'Cancelled']

const showFilters = ref(false)
const filters = reactive<{
  workflow_state: EvalState | ''
  spec_ref: string
  recommended_candidate: string
  search: string
}>({
  workflow_state: '',
  spec_ref: '',
  recommended_candidate: '',
  search: '',
})

const activeChips = computed<FilterChip[]>(() => {
  const c: FilterChip[] = []
  if (filters.workflow_state)        c.push({ key: 'workflow_state', label: stateLabel(filters.workflow_state) })
  if (filters.spec_ref)              c.push({ key: 'spec_ref', label: `Hồ sơ: ${filters.spec_ref}` })
  if (filters.recommended_candidate) c.push({ key: 'recommended_candidate', label: `NCC đề xuất: ${filters.recommended_candidate}` })
  if (filters.search.trim())         c.push({ key: 'search', label: `"${filters.search.trim()}"` })
  return c
})

function buildPayload(): Record<string, unknown> {
  const f: Record<string, unknown> = {}
  if (filters.workflow_state)        f.workflow_state = filters.workflow_state
  if (filters.spec_ref)              f.spec_ref = filters.spec_ref
  if (filters.recommended_candidate) f.recommended_candidate = filters.recommended_candidate
  if (filters.search.trim())         f.search = filters.search.trim()
  return f
}
function applyFilters() { store.fetchEvaluations(buildPayload()) }
function resetFilters() {
  filters.workflow_state = ''
  filters.spec_ref = ''
  filters.recommended_candidate = ''
  filters.search = ''
  store.fetchEvaluations()
}
function clearChip(key: string) {
  ;(filters as Record<string, string>)[key] = ''
  applyFilters()
}
function quickFilter(key: keyof typeof filters, value: string) {
  ;(filters as Record<string, string>)[key] = value
  showFilters.value = false
  applyFilters()
}

function goDetail(n: string) { router.push({ name: 'VendorEvaluationDetail', params: { id: n } }) }

onMounted(() => store.fetchEvaluations())
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Đánh giá nhà cung cấp"
      :subtitle="`Tổng ${store.evaluations.length} phiếu đánh giá theo hồ sơ kỹ thuật.`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeChips.length" />
      </template>
    </PageHeader>

    <ListFilterBar
      v-model:search="filters.search"
      :show="showFilters"
      :chips="activeChips"
      search-placeholder="Tìm theo mã phiếu, hồ sơ..."
      @apply="applyFilters"
      @reset="resetFilters"
      @clear-chip="clearChip"
    >
      <template #fields>
        <select v-model="filters.workflow_state" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in EVAL_STATES" :key="s" :value="s">{{ stateLabel(s) }}</option>
        </select>
      </template>
    </ListFilterBar>

    <div v-if="store.error" class="alert-error mb-4">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeChips.length > 0">Kết quả lọc: <strong class="text-slate-700">{{ store.evaluations.length }}</strong> phiếu</span>
          <span v-else>Hiển thị <strong class="text-slate-700">{{ store.evaluations.length }}</strong> phiếu</span>
        </span>
        <button v-if="activeChips.length > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="store.loading" class="p-6 text-sm text-slate-500">Đang tải...</div>
      <div v-else-if="store.evaluations.length" class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mã phiếu đánh giá</th>
              <th>Hồ sơ kỹ thuật</th>
              <th>Ngày khởi tạo</th>
              <th>Nhà cung cấp đề xuất</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(ev, idx) in store.evaluations" :key="ev.name"
              class="clickable animate-fade-in"
              :class="[`stagger-${Math.min(idx + 1, 8)}`]"
              @click="goDetail(ev.name)"
            >
              <td><span class="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{{ ev.name }}</span></td>
              <td>
                <button class="link-cell" :title="`Lọc: ${ev.spec_ref}`" @click.stop="quickFilter('spec_ref', ev.spec_ref)">
                  {{ ev.spec_ref }}
                </button>
              </td>
              <td>{{ formatVnDate(ev.draft_date) }}</td>
              <td>
                <button
v-if="ev.recommended_candidate" class="link-cell"
                        :title="`Lọc: ${ev.recommended_candidate}`"
                        @click.stop="quickFilter('recommended_candidate', ev.recommended_candidate)">
                  {{ ev.recommended_candidate }}
                </button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td>
                <button
type="button" class="pill-btn"
                        :title="`Lọc trạng thái: ${stateLabel(ev.workflow_state)}`"
                        @click.stop="quickFilter('workflow_state', ev.workflow_state)">
                  <StatusBadge :state="ev.workflow_state" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có phiếu đánh giá nào phù hợp</p>
        <button v-if="activeChips.length > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>
  </div>
</template>

<!-- styles trong list-view.css -->
