<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useImm13Store } from '@/stores/imm13'
import { useRouter } from 'vue-router'

const props = defineProps<{ id: string }>()
const store = useImm13Store()
const router = useRouter()
const submitting = ref(false)
const activeTab = ref<'info' | 'checklist' | 'transfer'>('info')

// Modal state
const showTechReviewModal = ref(false)
const showCompleteTechModal = ref(false)
const showDecisionModal = ref(false)
const showApproveModal = ref(false)
const showRejectModal = ref(false)

// Form refs for modals
const techReviewer = ref('')
const techReviewNotes = ref('')
const residualRiskLevel = ref('')
const residualRiskNotes = ref('')
const estimatedRemainingLife = ref(0)

const decisionOutcome = ref('')
const replacementNeeded = ref(false)
const transferLocation = ref('')
const receivingOfficer = ref('')
const transferDepartment = ref('')
const economicJustification = ref('')

const approvalNotes = ref('')
const rejectionReason = ref('')

const dr = computed(() => store.currentRequest)

const WORKFLOW_STATE_LABELS: Record<string, string> = {
  'Draft': 'Nháp',
  'Pending Tech Review': 'Chờ đánh giá KT',
  'Under Replacement Review': 'Đánh giá thay thế',
  'Approved for Transfer': 'Đã duyệt điều chuyển',
  'Transfer In Progress': 'Đang điều chuyển',
  'Transferred': 'Đã điều chuyển',
  'Pending Decommission': 'Chờ ngừng sử dụng',
  'Completed': 'Hoàn thành',
  'Cancelled': 'Đã hủy',
}

function stateBadgeClass(state: string): string {
  const map: Record<string, string> = {
    'Draft': 'bg-slate-100 text-slate-600',
    'Pending Tech Review': 'bg-blue-100 text-blue-700',
    'Under Replacement Review': 'bg-yellow-100 text-yellow-700',
    'Approved for Transfer': 'bg-green-100 text-green-700',
    'Transfer In Progress': 'bg-orange-100 text-orange-700',
    'Transferred': 'bg-emerald-100 text-emerald-700',
    'Pending Decommission': 'bg-red-100 text-red-700',
    'Completed': 'bg-green-200 text-green-800',
    'Cancelled': 'bg-slate-100 text-slate-500',
  }
  return map[state] ?? 'bg-slate-100 text-slate-600'
}

const OUTCOME_LABELS: Record<string, string> = {
  Suspend: 'Tạm ngừng',
  Transfer: 'Điều chuyển',
  Retire: 'Thanh lý',
}

const RISK_LEVELS = [
  { value: 'Low', label: 'Thấp' },
  { value: 'Medium', label: 'Trung bình' },
  { value: 'High', label: 'Cao' },
  { value: 'Critical', label: 'Nghiêm trọng' },
]

const checklistDone = computed(() =>
  (dr.value?.suspension_checklist ?? []).filter(i => i.completed).length
)
const checklistTotal = computed(() => (dr.value?.suspension_checklist ?? []).length)

async function doSubmitTechReview() {
  if (!dr.value) return
  submitting.value = true
  const ok = await store.doSubmitTechReview({
    name: dr.value.name,
    technical_reviewer: techReviewer.value,
    tech_review_notes: techReviewNotes.value,
    residual_risk_level: residualRiskLevel.value,
    residual_risk_notes: residualRiskNotes.value,
    estimated_remaining_life: estimatedRemainingLife.value || undefined,
  })
  submitting.value = false
  if (ok) showTechReviewModal.value = false
}

async function doCompleteTechReview() {
  if (!dr.value) return
  submitting.value = true
  const ok = await store.doCompleteTechReview({
    name: dr.value.name,
    technical_reviewer: techReviewer.value,
    tech_review_notes: techReviewNotes.value,
    residual_risk_level: residualRiskLevel.value,
    residual_risk_notes: residualRiskNotes.value,
  })
  submitting.value = false
  if (ok) showCompleteTechModal.value = false
}

async function doSetDecision() {
  if (!dr.value) return
  submitting.value = true
  const ok = await store.doSetReplacementDecision({
    name: dr.value.name,
    outcome: decisionOutcome.value,
    replacement_needed: replacementNeeded.value ? 1 : 0,
    transfer_to_location: transferLocation.value,
    receiving_officer: receivingOfficer.value,
    transfer_to_department: transferDepartment.value,
    economic_justification: economicJustification.value,
  })
  submitting.value = false
  if (ok) showDecisionModal.value = false
}

async function doApprove() {
  if (!dr.value) return
  submitting.value = true
  const ok = await store.doApproveSuspension({
    name: dr.value.name,
    approval_notes: approvalNotes.value,
  })
  submitting.value = false
  if (ok) showApproveModal.value = false
}

async function doReject() {
  if (!dr.value) return
  submitting.value = true
  const ok = await store.doRejectSuspension({
    name: dr.value.name,
    rejection_reason: rejectionReason.value,
  })
  submitting.value = false
  if (ok) showRejectModal.value = false
}

async function doStartTransfer() {
  if (!dr.value) return
  submitting.value = true
  await store.doStartTransfer(dr.value.name)
  submitting.value = false
}

async function doCompleteTransfer() {
  if (!dr.value) return
  submitting.value = true
  await store.doCompleteTransfer(dr.value.name)
  submitting.value = false
}

async function doCompleteChecklist(idx: number) {
  if (!dr.value) return
  await store.doCompleteChecklistItem(dr.value.name, idx)
}

onMounted(() => store.fetchRequest(props.id))
</script>

<template>
  <div class="p-6">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-5">
      <button class="text-slate-400 hover:text-slate-600" @click="router.back()">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
      <div class="flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-mono text-lg font-bold text-slate-900">{{ dr?.name }}</span>
          <span v-if="dr" :class="['px-2.5 py-1 rounded-full text-xs font-semibold', stateBadgeClass(dr.workflow_state)]">
            {{ WORKFLOW_STATE_LABELS[dr.workflow_state] ?? dr.workflow_state }}
          </span>
          <span v-if="dr?.outcome" class="px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-600">
            {{ OUTCOME_LABELS[dr.outcome] ?? dr.outcome }}
          </span>
        </div>
        <div class="text-sm text-slate-500 mt-0.5">{{ dr?.asset_name || dr?.asset }}</div>
      </div>
    </div>

    <div v-if="store.loading" class="text-center py-12 text-slate-400">Đang tải...</div>
    <div v-else-if="store.error && !dr" class="card p-6 text-center text-red-600">{{ store.error }}</div>

    <div v-else-if="dr" class="grid md:grid-cols-5 gap-6">
      <!-- LEFT: Main content -->
      <div class="md:col-span-3 space-y-5">

        <!-- Tabs -->
        <div class="flex gap-0 border-b border-slate-200">
          <button
            v-for="tab in [['info','Thông tin'], ['checklist','Checklist'], ...(dr.outcome === 'Transfer' ? [['transfer','Điều chuyển']] : [])]"
            :key="tab[0]"
            :class="['px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab[0]
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700']"
            @click="activeTab = tab[0] as any"
          >{{ tab[1] }}</button>
        </div>

        <!-- Tab: Thông tin -->
        <div v-show="activeTab === 'info'" class="space-y-4">
          <!-- Device Info -->
          <div class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Thông tin thiết bị</h2>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div class="col-span-2">
                <span class="text-slate-500">Thiết bị:</span>
                <span class="font-semibold ml-1">{{ dr.asset_name || dr.asset }}</span>
                <span v-if="dr.asset_name" class="ml-2 text-xs text-slate-400 font-mono">{{ dr.asset }}</span>
              </div>
              <div><span class="text-slate-500">Tình trạng:</span> <span class="font-medium">{{ dr.condition_at_suspension || '—' }}</span></div>
              <div>
                <span class="text-slate-500">Giá trị sổ sách:</span>
                <span class="font-medium ml-1">{{ dr.current_book_value ? dr.current_book_value.toLocaleString('vi-VN') + 'đ' : '—' }}</span>
              </div>
              <div class="col-span-2">
                <span class="text-slate-500">Lý do ngừng:</span>
                <span class="font-medium ml-1">{{ dr.suspension_reason || '—' }}</span>
              </div>
              <div v-if="dr.reason_details" class="col-span-2">
                <span class="text-slate-500">Chi tiết:</span>
                <p class="text-slate-700 mt-1 whitespace-pre-wrap">{{ dr.reason_details }}</p>
              </div>
            </div>
          </div>

          <!-- Tech Review section -->
          <div v-if="dr.workflow_state !== 'Draft'" class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Đánh giá Kỹ thuật</h2>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div><span class="text-slate-500">KTV đánh giá:</span> <span class="font-medium">{{ dr.technical_reviewer || '—' }}</span></div>
              <div><span class="text-slate-500">Ngày đánh giá:</span> <span>{{ dr.tech_review_date || '—' }}</span></div>
              <div>
                <span class="text-slate-500">Rủi ro tồn dư:</span>
                <span :class="['ml-1 px-1.5 py-0.5 rounded text-xs font-medium', {
                  'bg-green-100 text-green-700': dr.residual_risk_level === 'Low',
                  'bg-yellow-100 text-yellow-700': dr.residual_risk_level === 'Medium',
                  'bg-orange-100 text-orange-700': dr.residual_risk_level === 'High',
                  'bg-red-100 text-red-700': dr.residual_risk_level === 'Critical',
                  'bg-slate-100 text-slate-600': !dr.residual_risk_level,
                }]">{{ dr.residual_risk_level || '—' }}</span>
              </div>
              <div v-if="dr.estimated_remaining_life"><span class="text-slate-500">Tuổi thọ còn lại:</span> <span>{{ dr.estimated_remaining_life }} tháng</span></div>
              <div v-if="dr.tech_review_notes" class="col-span-2">
                <span class="text-slate-500">Ghi chú KT:</span>
                <p class="mt-1 text-slate-700 whitespace-pre-wrap">{{ dr.tech_review_notes }}</p>
              </div>
            </div>
          </div>

          <!-- Replacement Review -->
          <div v-if="['Under Replacement Review','Approved for Transfer','Transfer In Progress','Transferred','Pending Decommission','Completed'].includes(dr.workflow_state)" class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Quyết định Thay thế</h2>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span class="text-slate-500">Kết quả:</span>
                <span class="font-semibold ml-1">{{ dr.outcome ? OUTCOME_LABELS[dr.outcome] ?? dr.outcome : '—' }}</span>
              </div>
              <div>
                <span class="text-slate-500">Cần thay thế:</span>
                <span class="ml-1">{{ dr.replacement_needed ? 'Có' : 'Không' }}</span>
              </div>
            </div>
          </div>

          <!-- Compliance section -->
          <div class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Tuân thủ</h2>
            <div class="space-y-2 text-sm">
              <div class="flex items-center gap-2">
                <span :class="['w-3 h-3 rounded-full', dr.biological_hazard ? 'bg-red-500' : 'bg-green-400']" />
                <span class="text-slate-700">Nguy cơ sinh học:</span>
                <span class="font-medium">{{ dr.biological_hazard ? 'Có' : 'Không' }}</span>
              </div>
              <div v-if="dr.biological_hazard && dr.bio_hazard_clearance" class="ml-5 text-xs text-slate-500">
                Biện pháp: {{ dr.bio_hazard_clearance }}
              </div>
              <div class="flex items-center gap-2">
                <span :class="['w-3 h-3 rounded-full', dr.data_destruction_required ? (dr.data_destruction_confirmed ? 'bg-green-400' : 'bg-yellow-400') : 'bg-slate-200']" />
                <span class="text-slate-700">Xóa dữ liệu:</span>
                <span class="font-medium">{{ dr.data_destruction_required ? (dr.data_destruction_confirmed ? 'Đã xóa' : 'Chưa xóa') : 'Không yêu cầu' }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span :class="['w-3 h-3 rounded-full', dr.regulatory_clearance_required ? (dr.regulatory_clearance_doc ? 'bg-green-400' : 'bg-yellow-400') : 'bg-slate-200']" />
                <span class="text-slate-700">Giấy phép pháp lý:</span>
                <span class="font-medium">{{ dr.regulatory_clearance_required ? (dr.regulatory_clearance_doc ? 'Đã upload' : 'Chưa upload') : 'Không yêu cầu' }}</span>
              </div>
            </div>
          </div>

          <!-- Approval section -->
          <div v-if="dr.approved" class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Phê duyệt</h2>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div><span class="text-slate-500">Người phê duyệt:</span> <span class="font-medium">{{ dr.approved_by }}</span></div>
              <div><span class="text-slate-500">Ngày phê duyệt:</span> <span>{{ dr.approval_date || '—' }}</span></div>
              <div v-if="dr.approval_notes" class="col-span-2">
                <span class="text-slate-500">Ghi chú:</span>
                <p class="mt-1 text-slate-700">{{ dr.approval_notes }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab: Checklist -->
        <div v-show="activeTab === 'checklist'">
          <div class="bg-white rounded-xl shadow-sm border p-5">
            <div class="flex items-center justify-between mb-3">
              <h2 class="font-semibold text-slate-700 text-sm uppercase tracking-wide">Checklist Ngừng sử dụng</h2>
              <span class="text-xs text-slate-500">{{ checklistDone }}/{{ checklistTotal }} hoàn thành</span>
            </div>
            <!-- Progress -->
            <div class="h-1.5 bg-slate-100 rounded-full mb-4 overflow-hidden">
              <div
                class="h-1.5 bg-green-500 rounded-full transition-all"
                :style="{ width: checklistTotal ? `${Math.round(checklistDone / checklistTotal * 100)}%` : '0%' }"
              />
            </div>
            <div class="space-y-2">
              <div
                v-for="item in dr.suspension_checklist"
                :key="item.idx"
                :class="['flex items-start gap-3 p-3 rounded-lg border transition-colors',
                  item.completed ? 'bg-green-50 border-green-200' : 'border-slate-200 hover:bg-slate-50']"
              >
                <input
                  type="checkbox"
                  :checked="item.completed"
                  :disabled="item.completed || dr.docstatus === 1"
                  class="mt-0.5 rounded border-slate-300 text-green-600"
                  @change="doCompleteChecklist(item.idx)"
                />
                <div class="flex-1">
                  <div class="text-sm font-medium text-slate-800">{{ item.task_name }}</div>
                  <div class="text-xs text-slate-400 mt-0.5">{{ item.task_category }}</div>
                  <div v-if="item.notes" class="text-xs text-slate-500 mt-1 italic">{{ item.notes }}</div>
                  <div v-if="item.completion_date" class="text-xs text-green-600 mt-0.5">✓ {{ item.completion_date }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab: Transfer details -->
        <div v-if="dr.outcome === 'Transfer'" v-show="activeTab === 'transfer'">
          <div class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Chi tiết Điều chuyển</h2>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div><span class="text-slate-500">Địa điểm nhận:</span> <span class="font-medium">{{ dr.transfer_to_location || '—' }}</span></div>
              <div><span class="text-slate-500">Khoa nhận:</span> <span class="font-medium">{{ dr.transfer_to_department || '—' }}</span></div>
              <div class="col-span-2"><span class="text-slate-500">Cán bộ tiếp nhận:</span> <span class="font-medium ml-1">{{ dr.receiving_officer || '—' }}</span></div>
              <div v-if="dr.transfer_start_date"><span class="text-slate-500">Ngày bắt đầu:</span> <span>{{ dr.transfer_start_date }}</span></div>
              <div v-if="dr.economic_justification" class="col-span-2">
                <span class="text-slate-500">Lý do kinh tế:</span>
                <p class="mt-1 text-slate-700 whitespace-pre-wrap">{{ dr.economic_justification }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: Actions -->
      <div class="md:col-span-2 space-y-4">
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="font-semibold text-slate-700 mb-3 text-sm">Thao tác</h2>
          <div class="space-y-2">

            <!-- Draft state -->
            <template v-if="dr.workflow_state === 'Draft'">
              <button class="w-full px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                @click="showTechReviewModal = true">
                Gửi đánh giá KT
              </button>
            </template>

            <!-- Pending Tech Review -->
            <template v-if="dr.workflow_state === 'Pending Tech Review'">
              <button class="w-full px-4 py-2.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
                @click="showCompleteTechModal = true">
                Hoàn thành đánh giá KT
              </button>
            </template>

            <!-- Under Replacement Review -->
            <template v-if="dr.workflow_state === 'Under Replacement Review'">
              <button class="w-full px-4 py-2.5 bg-yellow-600 text-white rounded-lg text-sm font-medium hover:bg-yellow-700 transition-colors"
                @click="showDecisionModal = true">
                Quyết định kết quả
              </button>
            </template>

            <!-- Approved for Transfer -->
            <template v-if="dr.workflow_state === 'Approved for Transfer'">
              <button
                :disabled="submitting"
                class="w-full px-4 py-2.5 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700 disabled:opacity-50 transition-colors"
                @click="doStartTransfer"
              >
                {{ submitting ? 'Đang xử lý...' : 'Bắt đầu điều chuyển' }}
              </button>
            </template>

            <!-- Transfer In Progress -->
            <template v-if="dr.workflow_state === 'Transfer In Progress'">
              <button
                :disabled="submitting"
                class="w-full px-4 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
                @click="doCompleteTransfer"
              >
                {{ submitting ? 'Đang xử lý...' : 'Hoàn thành điều chuyển' }}
              </button>
            </template>

            <!-- Pending Decommission -->
            <template v-if="dr.workflow_state === 'Pending Decommission'">
              <button class="w-full px-4 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
                @click="showApproveModal = true">
                Phê duyệt ngừng sử dụng
              </button>
              <button class="w-full px-4 py-2.5 border border-red-300 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
                @click="showRejectModal = true">
                Từ chối
              </button>
            </template>

            <!-- Terminal states -->
            <div v-if="dr.workflow_state === 'Completed'" class="text-center py-2 text-green-600 font-semibold text-sm">
              ✓ Đã hoàn thành
            </div>
            <div v-if="dr.workflow_state === 'Transferred'" class="text-center py-2 text-emerald-600 font-semibold text-sm">
              ✓ Đã điều chuyển
            </div>
            <div v-if="dr.workflow_state === 'Cancelled'" class="text-center py-2 text-slate-500 font-semibold text-sm">
              ✗ Đã hủy
            </div>
          </div>
        </div>

        <!-- Summary card -->
        <div class="bg-white rounded-xl shadow-sm border p-4 text-sm">
          <div class="flex justify-between text-slate-500 mb-1">
            <span>Checklist:</span>
            <span class="font-medium text-slate-900">{{ checklistDone }}/{{ checklistTotal }}</span>
          </div>
          <div class="flex justify-between text-slate-500 mb-1">
            <span>Ngày tạo:</span>
            <span class="font-medium text-slate-900">{{ dr.creation?.slice(0, 10) }}</span>
          </div>
          <div v-if="dr.docstatus === 1" class="flex justify-between text-slate-500">
            <span>Đã submit:</span>
            <span class="font-medium text-green-600">Có</span>
          </div>
        </div>

        <div v-if="store.error" class="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {{ store.error }}
        </div>
      </div>
    </div>

    <!-- Modal: Submit Tech Review -->
    <Transition name="fade">
    <div v-if="showTechReviewModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="font-bold text-lg mb-4">Gửi đánh giá Kỹ thuật</h3>
        <div class="space-y-3 mb-5">
          <div>
            <label class="block text-sm text-slate-600 mb-1">Email KTV đánh giá</label>
            <input v-model="techReviewer" type="text" class="w-full form-input" placeholder="ktv@hospital.vn" />
          </div>
          <div>
            <label class="block text-sm text-slate-600 mb-1">Mức độ rủi ro tồn dư</label>
            <select v-model="residualRiskLevel" class="form-select w-full">
              <option value="">Chọn mức độ...</option>
              <option v-for="r in RISK_LEVELS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-slate-600 mb-1">Tuổi thọ ước tính còn lại (tháng)</label>
            <input v-model.number="estimatedRemainingLife" type="number" min="0" class="form-input w-full" />
          </div>
          <div>
            <label class="block text-sm text-slate-600 mb-1">Ghi chú đánh giá KT</label>
            <textarea v-model="techReviewNotes" rows="3" class="form-input w-full" placeholder="Nhận xét kỹ thuật..." />
          </div>
        </div>
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showTechReviewModal = false">Hủy</button>
          <button :disabled="submitting" class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50" @click="doSubmitTechReview">
            {{ submitting ? 'Đang xử lý...' : 'Gửi đánh giá' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>

    <!-- Modal: Complete Tech Review -->
    <Transition name="fade">
    <div v-if="showCompleteTechModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="font-bold text-lg mb-4">Hoàn thành đánh giá Kỹ thuật</h3>
        <div class="space-y-3 mb-5">
          <div>
            <label class="block text-sm text-slate-600 mb-1">Mức độ rủi ro tồn dư <span class="text-red-500">*</span></label>
            <select v-model="residualRiskLevel" class="form-select w-full">
              <option value="">Chọn mức độ...</option>
              <option v-for="r in RISK_LEVELS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-slate-600 mb-1">Ghi chú rủi ro tồn dư</label>
            <textarea v-model="residualRiskNotes" rows="2" class="form-input w-full" placeholder="Mô tả rủi ro..." />
          </div>
          <div>
            <label class="block text-sm text-slate-600 mb-1">Ghi chú đánh giá KT</label>
            <textarea v-model="techReviewNotes" rows="3" class="form-input w-full" placeholder="Kết luận đánh giá kỹ thuật..." />
          </div>
        </div>
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showCompleteTechModal = false">Hủy</button>
          <button :disabled="!residualRiskLevel || submitting" class="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium disabled:opacity-50" @click="doCompleteTechReview">
            {{ submitting ? 'Đang xử lý...' : 'Hoàn thành' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>

    <!-- Modal: Decision -->
    <Transition name="fade">
    <div v-if="showDecisionModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 my-4 shadow-2xl">
        <h3 class="font-bold text-lg mb-4">Quyết định kết quả</h3>
        <div class="space-y-3 mb-5">
          <div>
            <label class="block text-sm text-slate-600 mb-1">Kết quả <span class="text-red-500">*</span></label>
            <select v-model="decisionOutcome" class="form-select w-full">
              <option value="">Chọn kết quả...</option>
              <option value="Suspend">Tạm ngừng sử dụng</option>
              <option value="Transfer">Điều chuyển đơn vị khác</option>
              <option value="Retire">Thanh lý / Tiêu hủy</option>
            </select>
          </div>
          <label class="flex items-center gap-2 cursor-pointer">
            <input v-model="replacementNeeded" type="checkbox" class="rounded border-slate-300 text-blue-600" />
            <span class="text-sm text-slate-700">Cần thiết bị thay thế</span>
          </label>
          <template v-if="decisionOutcome === 'Transfer'">
            <div>
              <label class="block text-sm text-slate-600 mb-1">Địa điểm nhận <span class="text-red-500">*</span></label>
              <input v-model="transferLocation" type="text" class="form-input w-full" placeholder="Tên địa điểm/cơ sở..." />
            </div>
            <div>
              <label class="block text-sm text-slate-600 mb-1">Cán bộ tiếp nhận <span class="text-red-500">*</span></label>
              <input v-model="receivingOfficer" type="text" class="form-input w-full" placeholder="Email cán bộ tiếp nhận..." />
            </div>
            <div>
              <label class="block text-sm text-slate-600 mb-1">Khoa / Đơn vị nhận</label>
              <input v-model="transferDepartment" type="text" class="form-input w-full" placeholder="Tên khoa/đơn vị..." />
            </div>
            <div>
              <label class="block text-sm text-slate-600 mb-1">Lý do kinh tế / Điều phối</label>
              <textarea v-model="economicJustification" rows="2" class="form-input w-full" placeholder="Lý do điều chuyển..." />
            </div>
          </template>
        </div>
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showDecisionModal = false">Hủy</button>
          <button
            :disabled="!decisionOutcome || (decisionOutcome === 'Transfer' && (!transferLocation || !receivingOfficer)) || submitting"
            class="px-4 py-2 bg-yellow-600 text-white rounded-lg text-sm font-medium disabled:opacity-50"
            @click="doSetDecision"
          >
            {{ submitting ? 'Đang xử lý...' : 'Xác nhận quyết định' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>

    <!-- Modal: Approve -->
    <Transition name="fade">
    <div v-if="showApproveModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="font-bold text-lg text-green-700 mb-2">Phê duyệt Ngừng sử dụng</h3>
        <p class="text-sm text-slate-600 mb-4">Xác nhận phê duyệt phiếu ngừng sử dụng thiết bị này.</p>
        <div class="mb-5">
          <label class="block text-sm text-slate-600 mb-1">Ghi chú phê duyệt</label>
          <textarea v-model="approvalNotes" rows="3" class="form-input w-full" placeholder="Ghi chú của HTM Manager..." />
        </div>
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showApproveModal = false">Hủy</button>
          <button :disabled="submitting" class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50" @click="doApprove">
            {{ submitting ? 'Đang xử lý...' : 'Phê duyệt' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>

    <!-- Modal: Reject -->
    <Transition name="fade">
    <div v-if="showRejectModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="font-bold text-lg text-red-700 mb-2">Từ chối Phiếu</h3>
        <p class="text-sm text-slate-600 mb-4">Phiếu sẽ được chuyển sang trạng thái Đã hủy.</p>
        <textarea v-model="rejectionReason" rows="3" class="form-input w-full mb-5" placeholder="Lý do từ chối..." />
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showRejectModal = false">Hủy</button>
          <button :disabled="!rejectionReason || submitting" class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-50" @click="doReject">
            {{ submitting ? 'Đang xử lý...' : 'Từ chối' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
