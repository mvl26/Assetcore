<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import type { EvalState } from '@/types/imm03'
import { createEvaluation } from '@/api/imm03'
import { listTechSpecs } from '@/api/imm02'
import type { TechSpecListItem } from '@/types/imm02'
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
  if (filters.recommended_candidate) c.push({ key: 'recommended_candidate', label: `Nhà cung cấp đề xuất: ${filters.recommended_candidate}` })
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

// ─── Tạo phiếu đánh giá từ Hồ sơ kỹ thuật (Locked) — VR create_evaluation ────
const showCreate = ref(false)
const lockedSpecs = ref<TechSpecListItem[]>([])
const selectedSpec = ref('')
const creating = ref(false)
const createError = ref<string | null>(null)

async function openCreate() {
  showCreate.value = true
  createError.value = null
  selectedSpec.value = ''
  try {
    const res = await listTechSpecs({ workflow_state: 'Locked' }, 1, 100)
    lockedSpecs.value = res.items
  } catch (e) {
    createError.value = e instanceof Error ? e.message : String(e)
  }
}

async function submitCreate() {
  if (!selectedSpec.value) { createError.value = 'Vui lòng chọn hồ sơ kỹ thuật.'; return }
  creating.value = true
  createError.value = null
  try {
    const r = await createEvaluation(selectedSpec.value)
    showCreate.value = false
    router.push({ name: 'VendorEvaluationDetail', params: { id: r.name } })
  } catch (e) {
    createError.value = e instanceof Error ? e.message : String(e)
  } finally {
    creating.value = false
  }
}

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
        <button type="button" class="btn-primary" @click="openCreate">
          + Tạo phiếu đánh giá
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      v-model:search="filters.search"
      :show="showFilters"
      :chips="activeChips"
      search-placeholder="Tìm theo mã phiếu hoặc mã hồ sơ..."
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
      <template v-else-if="store.evaluations.length">
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="ev in store.evaluations"
            :key="ev.name"
            class="mobile-card"
            @click="goDetail(ev.name)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ ev.name }}</span>
              <StatusBadge :state="ev.workflow_state" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ ev.spec_ref }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="ev.draft_date">{{ formatVnDate(ev.draft_date) }}</span>
              <span v-if="ev.recommended_candidate">· {{ ev.vendor_name || ev.recommended_candidate }}</span>
            </div>
          </div>
          <div v-if="store.evaluations.length === 0" class="py-12 text-center text-slate-400">
            <p class="text-sm">Không có dữ liệu</p>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
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
                          :title="`Lọc: ${ev.vendor_name || ev.recommended_candidate}`"
                          @click.stop="quickFilter('recommended_candidate', ev.recommended_candidate)">
                    {{ ev.vendor_name || ev.recommended_candidate }}
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
      </template>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có phiếu đánh giá nào phù hợp</p>
        <button v-if="activeChips.length > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>

    <!-- Modal: tạo phiếu đánh giá từ Hồ sơ kỹ thuật (Locked) -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal-panel max-w-md">
        <h3 class="text-base font-semibold mb-1">Tạo phiếu đánh giá nhà cung cấp</h3>
        <p class="text-xs text-slate-500 mb-4">Chọn hồ sơ kỹ thuật đã chốt để khởi tạo phiếu đánh giá.</p>

        <div v-if="createError" class="alert-error mb-3 text-sm">{{ createError }}</div>

        <label class="block text-sm font-medium text-slate-700 mb-1">Hồ sơ kỹ thuật</label>
        <select v-model="selectedSpec" class="form-select w-full text-sm mb-4">
          <option value="">— Chọn hồ sơ —</option>
          <option v-for="s in lockedSpecs" :key="s.name" :value="s.name">
            {{ s.name }} · {{ (s as any).device_model_name || s.device_model_ref }}
          </option>
        </select>
        <p v-if="lockedSpecs.length === 0 && !createError" class="text-xs text-amber-600 mb-4">
          Chưa có hồ sơ kỹ thuật nào ở trạng thái Đã chốt.
        </p>

        <div class="flex justify-end gap-2">
          <button type="button" class="btn-secondary" @click="showCreate = false">Hủy</button>
          <button type="button" class="btn-primary" :disabled="creating || !selectedSpec" @click="submitCreate">
            {{ creating ? 'Đang tạo...' : 'Tạo phiếu' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<!-- styles trong list-view.css -->
