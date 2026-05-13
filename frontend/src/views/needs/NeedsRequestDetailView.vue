<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm01Store } from '@/stores/imm01'
import { useAuthStore } from '@/stores/auth'
import { useApi } from '@/composables/useApi'
import { getAllowedTransitions, rollIntoPlan } from '@/api/imm01'
import { Roles } from '@/constants/roles'
import type {
  BudgetEstimateLineRow, NeedsPriorityScoringRow,
  NeedsRequestState, FundingSource,
} from '@/types/imm01'
import {
  stateLabel, requestTypeLabel, criterionLabel,
  priorityBadge, formatVnd,
} from '@/utils/wave2Labels'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const props = defineProps<{ id?: string }>()
const route  = useRoute()
const router = useRouter()
const store  = useImm01Store()
const auth   = useAuthStore()
const api    = useApi()

const { currentDoc, plans, loading, error } = storeToRefs(store)

// ── tabs ──────────────────────────────────────────────────────────────────────
type TabId = 'overview' | 'scoring' | 'budget'
const TABS: { id: TabId; label: string; badge?: () => string }[] = [
  { id: 'overview', label: 'Tổng quan' },
  { id: 'scoring',  label: 'Chấm điểm ưu tiên' },
  { id: 'budget',   label: 'Dự toán' },
]
const activeTab = ref<TabId>('overview')

// ── workflow stepper ─────────────────────────────────────────────────────────
const WORKFLOW_STEPS: NeedsRequestState[] = [
  'Draft', 'Submitted', 'Reviewing', 'Prioritized',
  'Budgeted', 'Pending Approval', 'Approved',
]

function stepStatus(s: NeedsRequestState): 'done' | 'active' | 'pending' {
  const cur = currentDoc.value?.workflow_state ?? 'Draft'
  const ci = WORKFLOW_STEPS.indexOf(cur)
  const si = WORKFLOW_STEPS.indexOf(s)
  if (cur === 'Rejected') return si < ci ? 'done' : 'pending'
  if (si < ci) return 'done'
  if (si === ci) return 'active'
  return 'pending'
}

// ── permissions ───────────────────────────────────────────────────────────────
const isQA         = computed(() => auth.hasRole(Roles.QA) || auth.isSystemAdmin)
const isOpsManager = computed(() => auth.hasRole(Roles.OPS_MANAGER) || auth.isSystemAdmin)
const isBoardApprover = computed(() => auth.hasAnyRole([Roles.DEPT_HEAD, Roles.OPS_MANAGER]) || auth.isSystemAdmin)

const canScore = computed(() =>
  isQA.value && currentDoc.value?.workflow_state === 'Reviewing',
)
const canEditBudget = computed(() =>
  isOpsManager.value && currentDoc.value?.workflow_state === 'Prioritized',
)
const canApproveReject = computed(() =>
  isBoardApprover.value && currentDoc.value?.workflow_state === 'Pending Approval',
)
const canRollIntoPlan = computed(() =>
  currentDoc.value?.workflow_state === 'Approved' && !currentDoc.value?.procurement_plan,
)

// ── allowed workflow transitions ──────────────────────────────────────────────
const allowedActions = ref<string[]>([])
const SPECIAL_ACTIONS = new Set(['Phê duyệt', 'Bác đề xuất'])
const genericActions = computed(() => allowedActions.value.filter(a => !SPECIAL_ACTIONS.has(a)))

async function refreshActions() {
  const name = currentDoc.value?.name
  if (!name) { allowedActions.value = []; return }
  try {
    const res = await getAllowedTransitions(name)
    allowedActions.value = res.transitions.map(t => t.action)
  } catch { allowedActions.value = [] }
}

// ── scoring tab ───────────────────────────────────────────────────────────────
const scoringDraft = ref<NeedsPriorityScoringRow[]>([])
const totalWeight  = computed(() =>
  scoringDraft.value.reduce((s, r) => s + (r.weight_pct ?? 0), 0),
)
const weightError  = computed(() =>
  Math.abs(totalWeight.value - 100) > 0.01 ? `Tổng trọng số phải bằng 100% (hiện: ${totalWeight.value.toFixed(0)}%)` : null,
)
const previewScore = computed(() =>
  scoringDraft.value.reduce((s, r) => s + (r.score * (r.weight_pct ?? 0)) / 100, 0),
)

const DEFAULT_CRITERIA: Array<{ criterion: NeedsPriorityScoringRow['criterion']; weight_pct: number }> = [
  { criterion: 'clinical_impact',    weight_pct: 30 },
  { criterion: 'risk',               weight_pct: 20 },
  { criterion: 'utilization_gap',    weight_pct: 20 },
  { criterion: 'replacement_signal', weight_pct: 10 },
  { criterion: 'compliance_gap',     weight_pct: 10 },
  { criterion: 'budget_fit',         weight_pct: 10 },
]

function initScoringDraft() {
  const existing = currentDoc.value?.scoring_rows ?? []
  scoringDraft.value = DEFAULT_CRITERIA.map(def => {
    const row = existing.find(r => r.criterion === def.criterion)
    return {
      criterion: def.criterion,
      score:      row?.score      ?? 3,
      weight_pct: row?.weight_pct ?? def.weight_pct,
      evidence:   row?.evidence   ?? '',
    }
  })
}

async function saveScoring() {
  if (!currentDoc.value?.name || weightError.value) return
  const res = await api.run(
    () => store.score(currentDoc.value!.name!, scoringDraft.value),
    { successMessage: 'Đã lưu chấm điểm' },
  )
  if (res) {
    await store.fetchOne(currentDoc.value.name)
    await refreshActions()
  }
}

// ── budget tab ─────────────────────────────────────────────────────────────────
const budgetEditMode    = ref(false)
const capexDraft        = ref<BudgetEstimateLineRow[]>([])
const opexDraft         = ref<BudgetEstimateLineRow[]>([])
const fundingSourceDraft = ref<FundingSource>('' as FundingSource)

const LINE_TYPES_CAPEX = ['Device','Install','Training','Infra','Accessory','Other']
const LINE_TYPES_OPEX  = ['PM','Calibration','Spare','Consumable','Software','Insurance','Other']
const FUNDING_OPTIONS: FundingSource[] = ['NSNN','Tài trợ','Xã hội hóa','BHYT','Khác']

const capexTotal = computed(() =>
  capexDraft.value.reduce((s, r) => s + (r.qty ?? 1) * (r.unit_cost ?? 0), 0),
)
const opexTotal = computed(() =>
  opexDraft.value.reduce((s, r) => s + (r.unit_cost ?? 0), 0),
)

function enterBudgetEdit() {
  budgetEditMode.value = true
  capexDraft.value = (currentDoc.value?.budget_lines ?? [])
    .filter(l => l.budget_section === 'CAPEX').map(l => ({ ...l }))
  opexDraft.value = (currentDoc.value?.budget_lines ?? [])
    .filter(l => l.budget_section === 'OPEX').map(l => ({ ...l }))
  fundingSourceDraft.value = (currentDoc.value?.funding_source ?? '') as FundingSource
}
function cancelBudgetEdit() {
  budgetEditMode.value = false
}
function addCapex() {
  capexDraft.value.push({ budget_section: 'CAPEX', line_type: 'Device', qty: 1, unit_cost: 0 })
}
function addOpex() {
  opexDraft.value.push({ budget_section: 'OPEX', line_type: 'PM', year_offset: 1, unit_cost: 0 })
}
function removeCapex(i: number) { capexDraft.value.splice(i, 1) }
function removeOpex(i: number)  { opexDraft.value.splice(i, 1) }

async function saveBudget() {
  if (!currentDoc.value?.name) return
  const lines = [...capexDraft.value, ...opexDraft.value]
  const res = await api.run(
    () => store.submitBudget(currentDoc.value!.name!, lines, fundingSourceDraft.value || undefined),
    { successMessage: 'Đã lưu dự toán' },
  )
  if (res) {
    await store.fetchOne(currentDoc.value.name)
    await refreshActions()
    budgetEditMode.value = false
  }
}

// line type label
function lineTypeLabel(t?: string): string {
  return ({
    Device:'Mua thiết bị', Install:'Lắp đặt', Training:'Đào tạo', Infra:'Hạ tầng',
    Accessory:'Phụ kiện', PM:'Bảo trì', Calibration:'Hiệu chuẩn', Spare:'Phụ tùng dự phòng',
    Consumable:'Vật tư tiêu hao', Software:'Phần mềm', Insurance:'Bảo hiểm', Other:'Khác',
  } as Record<string, string>)[t ?? ''] ?? (t ?? '')
}

// ── approval modal ────────────────────────────────────────────────────────────
const showApproveModal  = ref(false)
const approverInput     = ref('')
const approveRemarks    = ref('')
const showRejectModal   = ref(false)
const rejectReasonInput = ref('')

async function doApprove() {
  if (!currentDoc.value?.name || !approverInput.value.trim()) return
  const res = await api.run(
    () => store.approve(currentDoc.value!.name!, approverInput.value.trim(), approveRemarks.value),
    { successMessage: 'Đã phê duyệt đề xuất' },
  )
  if (res) {
    showApproveModal.value = false
    approverInput.value = ''
    approveRemarks.value = ''
    await store.fetchOne(currentDoc.value.name)
    await refreshActions()
  }
}

async function doReject() {
  if (!currentDoc.value?.name || !rejectReasonInput.value.trim()) return
  const res = await api.run(
    () => store.reject(currentDoc.value!.name!, rejectReasonInput.value.trim()),
    { successMessage: 'Đã bác đề xuất' },
  )
  if (res) {
    showRejectModal.value = false
    rejectReasonInput.value = ''
    await store.fetchOne(currentDoc.value.name)
    await refreshActions()
  }
}

// ── generic workflow transition ───────────────────────────────────────────────
async function doTransition(action: string) {
  if (!currentDoc.value?.name) return
  const res = await api.run(
    () => store.transition(currentDoc.value!.name!, action),
    { successMessage: `Đã thực hiện: ${action}` },
  )
  if (res) {
    await store.fetchOne(currentDoc.value.name)
    await refreshActions()
  }
}

function actionVariant(action: string): string {
  if (action.includes('Bác') || action.includes('Huỷ')) return 'danger'
  if (action.includes('Trình') || action.includes('Hoàn tất')) return 'success'
  return 'primary'
}

// ── roll into plan modal ──────────────────────────────────────────────────────
const showRollModal    = ref(false)
const selectedPlanName = ref('')

async function openRollModal() {
  showRollModal.value = true
  await store.fetchPlans({ workflow_state: ['in', ['Draft', 'Approved']] }, 1, 50)
}

async function doRollIntoPlan() {
  if (!currentDoc.value?.name || !selectedPlanName.value) return
  const plan = plans.value.find(p => p.name === selectedPlanName.value)
  if (!plan) return
  const res = await api.run(
    () => rollIntoPlan(plan.plan_year, plan.plan_period, [currentDoc.value!.name!]),
    { successMessage: `Đã thêm vào kế hoạch ${plan.name}` },
  )
  if (res) {
    showRollModal.value = false
    selectedPlanName.value = ''
    await store.fetchOne(currentDoc.value.name)
  }
}

// ── init ──────────────────────────────────────────────────────────────────────
const docName = computed(() => props.id ?? (route.params.id as string) ?? (route.params.name as string))

onMounted(async () => {
  if (!docName.value) return
  await store.fetchOne(docName.value)
  await refreshActions()
})

watch(currentDoc, (doc) => {
  if (doc) initScoringDraft()
}, { immediate: true })
</script>

<template>
  <!-- Loading -->
  <div v-if="loading && !currentDoc" class="p-8">
    <SkeletonLoader variant="form" />
  </div>

  <!-- Error -->
  <div v-else-if="error && !currentDoc"
       class="m-8 rounded-xl border border-rose-200 bg-rose-50 px-6 py-8 text-center">
    <p class="text-rose-700 mb-4">{{ error }}</p>
    <button class="px-4 py-2 rounded-lg bg-rose-100 text-rose-700 text-sm"
            @click="store.fetchOne(docName)">Thử lại</button>
  </div>

  <div v-else-if="currentDoc" class="page-container animate-fade-in space-y-5">

    <!-- ── Header ── -->
    <PageHeader
      :title="currentDoc.name ?? ''"
      :subtitle="`${requestTypeLabel(currentDoc.request_type)} · ${currentDoc.requesting_department_name || currentDoc.requesting_department} · ${currentDoc.quantity} thiết bị · Năm ${currentDoc.target_year}`"
      :breadcrumb="[
        { label: 'IMM-01 · Đề xuất nhu cầu', to: '/needs-requests' },
        { label: currentDoc.name ?? '' },
      ]"
    >
      <template #actions>
        <StatusBadge :state="currentDoc.workflow_state ?? ''" />
        <span v-if="currentDoc.priority_class"
              :class="[
                'inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold',
                currentDoc.priority_class === 'P1' ? 'bg-rose-100 text-rose-700' :
                currentDoc.priority_class === 'P2' ? 'bg-orange-100 text-orange-700' :
                currentDoc.priority_class === 'P3' ? 'bg-amber-100 text-amber-700' :
                'bg-neutral-100 text-neutral-600',
              ]">
          {{ priorityBadge(currentDoc.priority_class) }}
        </span>
        <button class="btn-secondary text-sm" @click="router.back()">← Quay lại</button>
      </template>
    </PageHeader>

    <!-- ── Workflow stepper ── -->
    <div class="flex items-center gap-0 overflow-x-auto pb-1">
      <template v-for="(s, i) in WORKFLOW_STEPS" :key="s">
        <div :class="[
          'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors',
          stepStatus(s) === 'done'    ? 'bg-emerald-100 text-emerald-700' :
          stepStatus(s) === 'active'  ? 'bg-blue-600 text-white shadow-sm' :
                                        'bg-neutral-100 text-neutral-400',
        ]">
          <svg v-if="stepStatus(s) === 'done'" class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
          {{ stateLabel(s) }}
        </div>
        <div v-if="i < WORKFLOW_STEPS.length - 1" class="w-5 h-px bg-neutral-200 flex-shrink-0" />
      </template>
    </div>

    <!-- ── Error banner ── -->
    <div v-if="error"
         class="flex items-center gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 text-sm">
      <span class="flex-1">{{ error }}</span>
      <button class="underline" @click="store.clearError()">Đóng</button>
    </div>

    <!-- ── Tabs ── -->
    <div class="border-b border-neutral-200">
      <nav class="flex gap-1 -mb-px">
        <button v-for="t in TABS" :key="t.id"
                :class="[
                  'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                  activeTab === t.id
                    ? 'border-blue-600 text-blue-700'
                    : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300',
                ]"
                @click="activeTab = t.id">
          {{ t.label }}
        </button>
      </nav>
    </div>

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- Tab 1 — Tổng quan                                       -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <div v-show="activeTab === 'overview'" class="grid grid-cols-1 lg:grid-cols-2 gap-4">

      <div class="card">
        <h3 class="card-title">Lý do lâm sàng</h3>
        <p class="text-sm text-neutral-700 whitespace-pre-wrap leading-relaxed">
          {{ currentDoc.clinical_justification }}
        </p>
        <p class="text-xs text-neutral-400 mt-2">{{ (currentDoc.clinical_justification || '').length }} ký tự</p>
      </div>

      <div class="card space-y-3">
        <h3 class="card-title">Thông tin thiết bị</h3>
        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt class="text-neutral-500">Mã model</dt>
          <dd class="font-medium">{{ currentDoc.device_model_ref }}</dd>
          <dt class="text-neutral-500">Danh mục</dt>
          <dd>{{ (currentDoc as any).device_category_name || (currentDoc as any).asset_category_name || currentDoc.device_category || '—' }}</dd>
          <dt class="text-neutral-500">Thay thế cho</dt>
          <dd>{{ currentDoc.replacement_for_asset || '—' }}</dd>
          <template v-if="currentDoc.utilization_pct_12m != null">
            <dt class="text-neutral-500">Tỷ lệ sử dụng</dt>
            <dd>{{ currentDoc.utilization_pct_12m }}%</dd>
            <dt class="text-neutral-500">Ngừng HĐ 12 tháng</dt>
            <dd>{{ currentDoc.downtime_hr_12m }} giờ</dd>
          </template>
        </dl>
      </div>

      <!-- Score summary card (if scored) -->
      <div v-if="currentDoc.weighted_score" class="card lg:col-span-2">
        <h3 class="card-title">Kết quả chấm điểm</h3>
        <div class="flex items-center gap-6">
          <div class="text-center">
            <div class="text-3xl font-bold text-blue-600">{{ currentDoc.weighted_score?.toFixed(2) }}</div>
            <div class="text-xs text-neutral-500 mt-1">Tổng điểm</div>
          </div>
          <div v-if="currentDoc.priority_class" class="text-center">
            <div :class="[
              'text-2xl font-bold px-4 py-1 rounded-full',
              currentDoc.priority_class === 'P1' ? 'bg-rose-100 text-rose-700' :
              currentDoc.priority_class === 'P2' ? 'bg-orange-100 text-orange-700' :
              currentDoc.priority_class === 'P3' ? 'bg-amber-100 text-amber-700' :
              'bg-neutral-100 text-neutral-600',
            ]">{{ currentDoc.priority_class }}</div>
            <div class="text-xs text-neutral-500 mt-1">Mức ưu tiên</div>
          </div>
          <div v-if="currentDoc.tco_5y" class="text-center">
            <div class="text-2xl font-bold text-neutral-700">{{ formatVnd(currentDoc.tco_5y) }}</div>
            <div class="text-xs text-neutral-500 mt-1">TCO 5 năm</div>
          </div>
        </div>
      </div>

    </div>

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- Tab 2 — Chấm điểm ưu tiên                              -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <div v-show="activeTab === 'scoring'">

      <!-- State guidance -->
      <div v-if="!canScore && currentDoc.workflow_state !== 'Prioritized'"
           class="mb-4 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-700">
        <strong>Lưu ý:</strong>
        Chỉ QA Officer có thể chấm điểm khi phiếu ở trạng thái
        <strong>{{ stateLabel('Reviewing') }}</strong>.
        Trạng thái hiện tại: <strong>{{ stateLabel(currentDoc.workflow_state) }}</strong>.
      </div>

      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h3 class="card-title mb-0">6 tiêu chí ưu tiên</h3>
          <div v-if="canScore" class="flex items-center gap-2">
            <span :class="['text-xs font-medium px-2 py-1 rounded-full',
              weightError ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700']">
              Tổng trọng số: {{ totalWeight.toFixed(0) }}%
            </span>
            <span class="text-xs text-neutral-500">
              Dự kiến: <strong>{{ previewScore.toFixed(2) }}</strong>
            </span>
          </div>
        </div>

        <p v-if="weightError" class="text-xs text-rose-600 mb-3">{{ weightError }}</p>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="th text-left">Tiêu chí</th>
                <th class="th text-center w-36">Điểm (1–5)</th>
                <th class="th text-center w-28">Trọng số (%)</th>
                <th class="th text-right w-28">Điểm × trọng số</th>
                <th class="th text-left">Lý giải / Bằng chứng</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scoringDraft" :key="row.criterion"
                  class="border-b border-neutral-50 hover:bg-neutral-50/50">
                <td class="td">
                  <span class="font-medium text-neutral-700">{{ criterionLabel(row.criterion) }}</span>
                </td>
                <td class="td text-center">
                  <template v-if="canScore">
                    <!-- Star-style 1-5 input -->
                    <div class="flex justify-center gap-1">
                      <button v-for="n in 5" :key="n"
                              :class="['w-7 h-7 rounded-full text-xs font-bold transition-colors',
                                row.score >= n ? 'bg-blue-600 text-white' : 'bg-neutral-100 text-neutral-400 hover:bg-neutral-200']"
                              @click="row.score = n">
                        {{ n }}
                      </button>
                    </div>
                  </template>
                  <template v-else>
                    <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-50 text-blue-700 font-bold">
                      {{ row.score }}
                    </span>
                  </template>
                </td>
                <td class="td text-center">
                  <input v-if="canScore"
                         v-model.number="row.weight_pct"
                         type="number" min="0" max="100" step="5"
                         class="w-16 text-center border border-neutral-300 rounded px-1.5 py-0.5 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500" />
                  <span v-else class="text-neutral-600">{{ row.weight_pct?.toFixed(0) }}%</span>
                </td>
                <td class="td text-right font-semibold text-neutral-700">
                  {{ ((row.score * (row.weight_pct ?? 0)) / 100).toFixed(3) }}
                </td>
                <td class="td">
                  <input v-if="canScore"
                         v-model="row.evidence"
                         type="text"
                         placeholder="Bằng chứng, số liệu hỗ trợ…"
                         class="w-full border border-neutral-300 rounded px-2 py-1 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500" />
                  <span v-else class="text-neutral-500 text-xs">{{ row.evidence || '—' }}</span>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="border-t-2 border-neutral-200 bg-neutral-50">
                <td class="td font-semibold" colspan="3">Tổng</td>
                <td class="td text-right font-bold text-blue-700 text-base">
                  {{ previewScore.toFixed(3) }}
                </td>
                <td class="td">
                  <span v-if="currentDoc.priority_class" :class="[
                    'inline-block px-2.5 py-0.5 rounded-full text-xs font-bold',
                    currentDoc.priority_class === 'P1' ? 'bg-rose-100 text-rose-700' :
                    currentDoc.priority_class === 'P2' ? 'bg-orange-100 text-orange-700' :
                    currentDoc.priority_class === 'P3' ? 'bg-amber-100 text-amber-700' :
                    'bg-neutral-100 text-neutral-600',
                  ]">{{ priorityBadge(currentDoc.priority_class) }}</span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div v-if="canScore" class="flex justify-end mt-4">
          <button class="btn-primary" :disabled="!!weightError" @click="saveScoring">
            Lưu chấm điểm
          </button>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- Tab 3 — Dự toán                                         -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <div v-show="activeTab === 'budget'" class="space-y-4">

      <!-- State guidance -->
      <div v-if="!canEditBudget && !['Budgeted','Pending Approval','Approved'].includes(currentDoc.workflow_state ?? '')"
           class="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-700">
        <strong>Lưu ý:</strong>
        Ops Manager có thể lập dự toán khi phiếu ở trạng thái
        <strong>{{ stateLabel('Prioritized') }}</strong>.
        Trạng thái hiện tại: <strong>{{ stateLabel(currentDoc.workflow_state) }}</strong>.
      </div>

      <!-- Toolbar -->
      <div class="flex items-center justify-between">
        <h3 class="text-base font-semibold text-neutral-700">Bảng dự toán chi phí</h3>
        <div class="flex gap-2">
          <template v-if="canEditBudget && !budgetEditMode">
            <button class="btn-secondary text-sm" @click="enterBudgetEdit">
              ✏️ Chỉnh sửa dự toán
            </button>
          </template>
          <template v-else-if="budgetEditMode">
            <button class="btn-secondary text-sm" @click="cancelBudgetEdit">Huỷ</button>
            <button class="btn-primary text-sm" @click="saveBudget">Lưu dự toán</button>
          </template>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- CAPEX -->
        <div class="card">
          <div class="flex items-center justify-between mb-3">
            <h4 class="font-semibold text-neutral-700">Đầu tư mua sắm (CAPEX)</h4>
            <span class="text-sm font-semibold text-blue-700">{{ formatVnd(budgetEditMode ? capexTotal : (currentDoc.total_capex ?? 0)) }}</span>
          </div>
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="th text-left">Hạng mục</th>
                <th class="th text-right w-16">SL</th>
                <th class="th text-right w-28">Đơn giá</th>
                <th class="th text-right w-28">Thành tiền</th>
                <th v-if="budgetEditMode" class="th w-8" />
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in (budgetEditMode ? capexDraft : (currentDoc.budget_lines ?? []).filter(l => l.budget_section === 'CAPEX'))"
                  :key="i" class="border-b border-neutral-50">
                <td class="td">
                  <select v-if="budgetEditMode" v-model="r.line_type"
                          class="w-full border border-neutral-300 rounded px-1.5 py-1 text-sm">
                    <option v-for="lt in LINE_TYPES_CAPEX" :key="lt" :value="lt">{{ lineTypeLabel(lt) }}</option>
                  </select>
                  <template v-else>{{ lineTypeLabel(r.line_type) }}</template>
                </td>
                <td class="td text-right">
                  <input v-if="budgetEditMode" v-model.number="r.qty" type="number" min="1"
                         class="w-14 text-right border border-neutral-300 rounded px-1 py-0.5 text-sm" />
                  <template v-else>{{ r.qty ?? 1 }}</template>
                </td>
                <td class="td text-right">
                  <input v-if="budgetEditMode" v-model.number="r.unit_cost" type="number" min="0"
                         class="w-24 text-right border border-neutral-300 rounded px-1 py-0.5 text-sm" />
                  <template v-else>{{ formatVnd(r.unit_cost) }}</template>
                </td>
                <td class="td text-right font-medium">
                  {{ formatVnd((r.qty ?? 1) * (r.unit_cost ?? 0)) }}
                </td>
                <td v-if="budgetEditMode" class="td">
                  <button class="text-neutral-400 hover:text-rose-600 text-lg leading-none" @click="removeCapex(i)">×</button>
                </td>
              </tr>
              <tr v-if="!(budgetEditMode ? capexDraft : (currentDoc.budget_lines ?? []).filter(l => l.budget_section === 'CAPEX')).length">
                <td :colspan="budgetEditMode ? 5 : 4" class="td text-center text-neutral-400 py-4">Chưa có dòng đầu tư</td>
              </tr>
            </tbody>
          </table>
          <button v-if="budgetEditMode" class="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium" @click="addCapex">
            + Thêm dòng CAPEX
          </button>
        </div>

        <!-- OPEX -->
        <div class="card">
          <div class="flex items-center justify-between mb-3">
            <h4 class="font-semibold text-neutral-700">Chi phí vận hành 5 năm (OPEX)</h4>
            <span class="text-sm font-semibold text-violet-700">{{ formatVnd(budgetEditMode ? opexTotal : (currentDoc.total_opex_5y ?? 0)) }}</span>
          </div>
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="th text-left w-16">Năm</th>
                <th class="th text-left">Hạng mục</th>
                <th class="th text-right w-28">Số tiền</th>
                <th v-if="budgetEditMode" class="th w-8" />
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in (budgetEditMode ? opexDraft : (currentDoc.budget_lines ?? []).filter(l => l.budget_section === 'OPEX'))"
                  :key="i" class="border-b border-neutral-50">
                <td class="td">
                  <input v-if="budgetEditMode" v-model.number="r.year_offset" type="number" min="1" max="5"
                         class="w-12 border border-neutral-300 rounded px-1 py-0.5 text-sm text-center" />
                  <template v-else>Năm {{ r.year_offset }}</template>
                </td>
                <td class="td">
                  <select v-if="budgetEditMode" v-model="r.line_type"
                          class="w-full border border-neutral-300 rounded px-1.5 py-1 text-sm">
                    <option v-for="lt in LINE_TYPES_OPEX" :key="lt" :value="lt">{{ lineTypeLabel(lt) }}</option>
                  </select>
                  <template v-else>{{ lineTypeLabel(r.line_type) }}</template>
                </td>
                <td class="td text-right font-medium">
                  <input v-if="budgetEditMode" v-model.number="r.unit_cost" type="number" min="0"
                         class="w-24 text-right border border-neutral-300 rounded px-1 py-0.5 text-sm" />
                  <template v-else>{{ formatVnd(r.unit_cost) }}</template>
                </td>
                <td v-if="budgetEditMode" class="td">
                  <button class="text-neutral-400 hover:text-rose-600 text-lg leading-none" @click="removeOpex(i)">×</button>
                </td>
              </tr>
              <tr v-if="!(budgetEditMode ? opexDraft : (currentDoc.budget_lines ?? []).filter(l => l.budget_section === 'OPEX')).length">
                <td :colspan="budgetEditMode ? 4 : 3" class="td text-center text-neutral-400 py-4">Chưa có dòng vận hành</td>
              </tr>
            </tbody>
          </table>
          <button v-if="budgetEditMode" class="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium" @click="addOpex">
            + Thêm dòng OPEX
          </button>
        </div>
      </div>

      <!-- Funding source + TCO summary -->
      <div class="card">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="text-xs font-medium text-neutral-500 uppercase tracking-wide">Nguồn vốn</label>
            <div v-if="budgetEditMode" class="mt-1">
              <select v-model="fundingSourceDraft"
                      class="w-full border border-neutral-300 rounded-lg px-3 py-2 text-sm">
                <option value="">Chưa chọn</option>
                <option v-for="f in FUNDING_OPTIONS" :key="f" :value="f">{{ f }}</option>
              </select>
            </div>
            <div v-else class="mt-1 text-sm font-semibold">
              {{ currentDoc.funding_source || 'Chưa xác định' }}
            </div>
          </div>
          <div>
            <label class="text-xs font-medium text-neutral-500 uppercase tracking-wide">CAPEX</label>
            <div class="mt-1 text-lg font-bold text-blue-700">{{ formatVnd(currentDoc.total_capex ?? 0) }}</div>
          </div>
          <div>
            <label class="text-xs font-medium text-neutral-500 uppercase tracking-wide">TCO 5 năm</label>
            <div class="mt-1 text-lg font-bold text-violet-700">{{ formatVnd(currentDoc.tco_5y ?? 0) }}</div>
          </div>
        </div>
      </div>

    </div>

    <!-- ── Sticky action bar ── -->
    <div class="sticky bottom-0 z-10 bg-white/95 backdrop-blur border-t border-neutral-200 px-4 py-3 flex items-center justify-between gap-3 -mx-4">
      <div class="text-sm text-neutral-500">
        Trạng thái: <strong class="text-neutral-700">{{ stateLabel(currentDoc.workflow_state) }}</strong>
      </div>
      <div class="flex gap-2 flex-wrap justify-end">

        <!-- Roll into Plan -->
        <button v-if="canRollIntoPlan"
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-700 transition-colors"
                @click="openRollModal">
          📋 Đưa vào kế hoạch mua sắm
        </button>

        <!-- Approve / Reject -->
        <template v-if="canApproveReject">
          <button class="btn-danger text-sm" @click="showRejectModal = true">Bác đề xuất</button>
          <button class="btn-success text-sm" @click="showApproveModal = true">Phê duyệt ✓</button>
        </template>

        <!-- Generic workflow transitions -->
        <button v-for="action in genericActions" :key="action"
                :class="[
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  actionVariant(action) === 'danger'  ? 'bg-rose-100 text-rose-700 hover:bg-rose-200' :
                  actionVariant(action) === 'success'  ? 'bg-emerald-600 text-white hover:bg-emerald-700' :
                                                        'btn-primary',
                ]"
                @click="doTransition(action)">
          {{ action }}
        </button>

      </div>
    </div>

  </div>

  <!-- ── Approve modal ── -->
  <BaseModal v-if="showApproveModal" title="Phê duyệt đề xuất nhu cầu" size="md"
             @close="showApproveModal = false">
    <div class="p-4 space-y-4">
      <div>
        <label class="form-label">Người duyệt (tài khoản BGĐ) <span class="text-rose-500">*</span></label>
        <input v-model="approverInput" type="text" placeholder="vd: nguyen.van.a@hospital.vn"
               class="form-input mt-1" />
      </div>
      <div>
        <label class="form-label">Ghi chú phê duyệt</label>
        <textarea v-model="approveRemarks" rows="3" placeholder="Nội dung ghi chú…"
                  class="form-input mt-1 resize-none" />
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end gap-2 px-4 pb-4">
        <button class="btn-secondary text-sm" @click="showApproveModal = false">Huỷ</button>
        <button class="btn-success text-sm" :disabled="!approverInput.trim()" @click="doApprove">
          Xác nhận phê duyệt
        </button>
      </div>
    </template>
  </BaseModal>

  <!-- ── Reject modal ── -->
  <BaseModal v-if="showRejectModal" title="Bác đề xuất" size="md" :danger="true"
             @close="showRejectModal = false">
    <div class="p-4 space-y-4">
      <p class="text-sm text-neutral-600">
        Vui lòng nhập lý do bác đề xuất <strong>{{ currentDoc?.name }}</strong>.
        Hành động này không thể hoàn tác.
      </p>
      <div>
        <label class="form-label">Lý do <span class="text-rose-500">*</span></label>
        <textarea v-model="rejectReasonInput" rows="4"
                  placeholder="Nêu rõ lý do không đủ điều kiện phê duyệt…"
                  class="form-input mt-1 resize-none" />
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end gap-2 px-4 pb-4">
        <button class="btn-secondary text-sm" @click="showRejectModal = false">Huỷ</button>
        <button class="btn-danger text-sm" :disabled="!rejectReasonInput.trim()" @click="doReject">
          Xác nhận bác đề xuất
        </button>
      </div>
    </template>
  </BaseModal>

  <!-- ── Roll into Plan modal ── -->
  <BaseModal v-if="showRollModal" title="Đưa vào kế hoạch mua sắm" size="lg"
             @close="showRollModal = false">
    <div class="p-4 space-y-4">
      <p class="text-sm text-neutral-600">
        Chọn kế hoạch mua sắm để thêm đề xuất <strong>{{ currentDoc?.name }}</strong>.
      </p>

      <div v-if="!plans.length" class="text-center py-8 text-neutral-400 text-sm">
        Không có kế hoạch nào ở trạng thái Draft hoặc Approved.
      </div>

      <div v-else class="space-y-2">
        <label v-for="p in plans" :key="p.name"
               :class="[
                 'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                 selectedPlanName === p.name
                   ? 'border-blue-500 bg-blue-50'
                   : 'border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50',
               ]">
          <input v-model="selectedPlanName" type="radio" :value="p.name"
                 class="mt-0.5 accent-blue-600" />
          <div class="flex-1 min-w-0">
            <div class="font-medium text-sm text-neutral-800">{{ p.name }}</div>
            <div class="text-xs text-neutral-500 mt-0.5">
              Năm {{ p.plan_year }} · {{ p.plan_period }}
              · Ngân sách: {{ formatVnd(p.budget_envelope) }}
              <span :class="[
                'ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold',
                p.workflow_state === 'Approved' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700',
              ]">{{ stateLabel(p.workflow_state) }}</span>
            </div>
          </div>
        </label>
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end gap-2 px-4 pb-4">
        <button class="btn-secondary text-sm" @click="showRollModal = false">Huỷ</button>
        <button class="btn-primary text-sm" :disabled="!selectedPlanName" @click="doRollIntoPlan">
          Thêm vào kế hoạch này
        </button>
      </div>
    </template>
  </BaseModal>

</template>

<style scoped>
.card         { @apply bg-white rounded-xl border border-neutral-200 p-4; }
.card-title   { @apply text-sm font-semibold text-neutral-700 mb-3; }
.th           { @apply px-3 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wide; }
.td           { @apply px-3 py-2.5; }
.form-label   { @apply text-sm font-medium text-neutral-700; }
.form-input   { @apply w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500; }
.btn-primary  { @apply inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed; }
.btn-secondary { @apply inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-neutral-300 bg-white text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors; }
.btn-success  { @apply inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed; }
.btn-danger   { @apply inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-rose-600 text-white text-sm font-medium hover:bg-rose-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed; }
</style>
