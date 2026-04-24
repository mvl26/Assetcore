<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useImm01Store } from '@/stores/imm01'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import ApprovalModal from '@/components/common/ApprovalModal.vue'
import { formatDate } from '@/utils/docUtils'
import type { MasterItem } from '@/stores/useMasterDataStore'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store  = useImm01Store()

// ─── Workflow modal state ──────────────────────────────────────────────────────

const showApproveModal   = ref(false)
const showRejectModal    = ref(false)
const showSubmitModal    = ref(false)
const approveForm = ref({ approved_budget: null as number | null, notes: '' })
const rejectForm  = ref({ reason: '' })
const actionError = ref<string | null>(null)

const doc = computed(() => store.currentDoc)

// ─── Status helpers ────────────────────────────────────────────────────────────

const canSubmit      = computed(() => doc.value?.status === 'Draft')
const canBeginReview = computed(() => doc.value?.status === 'Submitted')
const canApprove     = computed(() => doc.value?.status === 'Under Review')
const canReject      = computed(() =>
  doc.value?.status === 'Submitted' || doc.value?.status === 'Under Review'
)
const isTerminal = computed(() =>
  ['Approved', 'Rejected', 'Planned'].includes(doc.value?.status ?? '')
)

// ─── Actions ──────────────────────────────────────────────────────────────────

async function handleSubmitForReview(approver: string) {
  showSubmitModal.value = false
  actionError.value = null
  const ok = await store.submitForReview(props.id, approver)
  if (!ok) actionError.value = store.error
}

async function handleBeginReview() {
  actionError.value = null
  const ok = await store.beginReview(props.id)
  if (!ok) actionError.value = store.error
}

async function handleApprove() {
  actionError.value = null
  if (!approveForm.value.approved_budget || approveForm.value.approved_budget <= 0) {
    actionError.value = 'Vui lòng nhập ngân sách được duyệt'
    return
  }
  const ok = await store.approveNA(props.id, approveForm.value.approved_budget, approveForm.value.notes)
  if (ok) {
    showApproveModal.value = false
    approveForm.value = { approved_budget: null, notes: '' }
  } else {
    actionError.value = store.error
  }
}

async function handleReject() {
  actionError.value = null
  if (!rejectForm.value.reason || rejectForm.value.reason.trim().length < 5) {
    actionError.value = 'Lý do từ chối phải ít nhất 5 ký tự'
    return
  }
  const ok = await store.rejectNA(props.id, rejectForm.value.reason)
  if (ok) {
    showRejectModal.value = false
    rejectForm.value = { reason: '' }
  } else {
    actionError.value = store.error
  }
}

function openApproveModal() {
  approveForm.value.approved_budget = doc.value?.estimated_budget ?? null
  actionError.value = null
  showApproveModal.value = true
}

function openRejectModal() {
  actionError.value = null
  showRejectModal.value = true
}

// ─── Format helpers ────────────────────────────────────────────────────────────

function formatBudget(val: number | null | undefined): string {
  if (!val) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(val)
}


// ─── Step indicator ───────────────────────────────────────────────────────────

function stepIndex(status: string): number {
  const order = ['Draft', 'Submitted', 'Under Review', 'Approved', 'Planned']
  return order.indexOf(status)
}

// ─── HTM Review Notes ─────────────────────────────────────────────────────────

const htmNotesEdit = ref('')
const htmNotesSaving = ref(false)
const htmNotesError = ref<string | null>(null)

function startEditHtmNotes() {
  htmNotesEdit.value = doc.value?.htmreview_notes ?? ''
}

async function handleSaveHtmNotes() {
  htmNotesError.value = null
  if (!htmNotesEdit.value.trim()) {
    htmNotesError.value = 'Nhận xét không được để trống'
    return
  }
  htmNotesSaving.value = true
  const ok = await store.saveHtmNotes(props.id, htmNotesEdit.value)
  htmNotesSaving.value = false
  if (!ok) htmNotesError.value = store.error
}

// ─── Technical Specification ──────────────────────────────────────────────────

const showLinkTsPanel   = ref(false)
const selectedTs        = ref('')
const tsActionError     = ref<string | null>(null)

function onTsSelect(item: MasterItem) {
  selectedTs.value = item.id
}

async function handleLinkTs() {
  tsActionError.value = null
  if (!selectedTs.value) {
    tsActionError.value = 'Vui lòng chọn đặc tả kỹ thuật'
    return
  }
  const ok = await store.linkTs(props.id, selectedTs.value)
  if (ok) {
    showLinkTsPanel.value = false
    selectedTs.value = ''
  } else {
    tsActionError.value = store.error
  }
}

function handleCreateTs() {
  router.push(`/planning/technical-specs/new?na=${props.id}`)
}

// ─── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  await store.fetchOne(props.id)
  htmNotesEdit.value = store.currentDoc?.htmreview_notes ?? ''
}

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Breadcrumb -->
    <nav class="flex items-center gap-1.5 text-xs text-slate-400 mb-6">
      <button class="hover:text-slate-600 transition-colors"
              @click="router.push('/planning/needs-assessments')">
        Đánh giá Nhu cầu
      </button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <span class="font-mono font-semibold text-slate-700">{{ id }}</span>
      <StatusBadge v-if="doc" :state="doc.status" size="xs" class="ml-1" />
    </nav>

    <!-- Loading -->
    <SkeletonLoader v-if="store.loading" variant="form" />

    <!-- Error -->
    <div v-else-if="store.error && !doc" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline hover:no-underline" @click="load">Thử lại</button>
    </div>

    <template v-else-if="doc">

      <!-- Page header -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-01</p>
          <h1 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
            {{ doc.equipment_type }}
          </h1>
          <p class="text-sm text-slate-500 mt-1 font-mono">{{ doc.name }}</p>
        </div>

        <!-- Workflow action buttons -->
        <div v-if="!isTerminal" class="flex items-center gap-2 shrink-0">
          <button
            v-if="canSubmit"
            class="btn-primary"
            :disabled="store.loading"
            @click="showSubmitModal = true"
          >
            <svg v-if="store.loading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Nộp xét duyệt
          </button>

          <button
            v-if="canBeginReview"
            class="btn-primary"
            :disabled="store.loading"
            @click="handleBeginReview"
          >
            Bắt đầu xét duyệt
          </button>

          <template v-if="canApprove">
            <button class="btn-primary" :disabled="store.loading" @click="openApproveModal">
              Phê duyệt
            </button>
          </template>

          <button
            v-if="canReject"
            class="btn-danger"
            :disabled="store.loading"
            @click="openRejectModal"
          >
            Từ chối
          </button>
        </div>
      </div>

      <!-- Action error -->
      <div v-if="actionError" class="alert-error mb-5">
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="flex-1">{{ actionError }}</span>
        <button class="text-xs font-medium" @click="actionError = null">✕</button>
      </div>

      <!-- Rejected reason banner -->
      <div v-if="doc.status === 'Rejected' && doc.reject_reason"
           class="flex items-start gap-3 px-4 py-3 rounded-xl border mb-5 text-sm"
           style="background: #fff1f2; border-color: #fecdd3">
        <svg class="w-4 h-4 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <p class="font-semibold text-red-700">Lý do từ chối</p>
          <p class="text-red-600 mt-0.5">{{ doc.reject_reason }}</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <!-- Main info cards (2/3 width) -->
        <div class="lg:col-span-2 space-y-6">

          <!-- Basic info -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
              Thông tin Thiết bị
            </h3>
            <dl class="grid grid-cols-2 gap-x-6 gap-y-4">
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Loại thiết bị</dt>
                <dd class="text-sm font-medium text-slate-800">{{ doc.equipment_type }}</dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Khoa đề xuất</dt>
                <dd class="text-sm text-slate-700">{{ doc.requesting_dept || '—' }}</dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Số lượng</dt>
                <dd class="text-sm text-slate-700">{{ doc.quantity }}</dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Ưu tiên</dt>
                <dd class="text-sm text-slate-700">{{ doc.priority }}</dd>
              </div>
              <div v-if="doc.linked_device_model">
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Model liên kết</dt>
                <dd class="text-sm font-mono text-brand-600">{{ doc.linked_device_model }}</dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Ngày đề xuất</dt>
                <dd class="text-sm text-slate-700">{{ formatDate(doc.request_date) }}</dd>
              </div>
            </dl>
          </div>

          <!-- Budget -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
              Ngân sách
            </h3>
            <div class="grid grid-cols-2 gap-6">
              <div>
                <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Ngân sách ước tính</p>
                <p class="text-lg font-semibold text-slate-800">{{ formatBudget(doc.estimated_budget) }}</p>
              </div>
              <div>
                <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Ngân sách được duyệt</p>
                <p class="text-lg font-semibold"
                   :class="doc.approved_budget ? 'text-emerald-700' : 'text-slate-400'">
                  {{ formatBudget(doc.approved_budget) }}
                </p>
              </div>
            </div>
            <div v-if="doc.finance_notes" class="mt-3 pt-3 border-t border-slate-100">
              <p class="text-xs text-slate-400 mb-1">Ghi chú tài chính</p>
              <p class="text-sm text-slate-600">{{ doc.finance_notes }}</p>
            </div>
          </div>

          <!-- Clinical justification -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-100">
              Lý do Lâm sàng
            </h3>
            <p class="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
              {{ doc.clinical_justification }}
            </p>
            <div v-if="doc.current_equipment_age || doc.failure_frequency"
                 class="flex gap-6 mt-4 pt-3 border-t border-slate-100">
              <div v-if="doc.current_equipment_age">
                <p class="text-xs text-slate-400">Tuổi thiết bị hiện tại</p>
                <p class="text-sm text-slate-700">{{ doc.current_equipment_age }} năm</p>
              </div>
              <div v-if="doc.failure_frequency">
                <p class="text-xs text-slate-400">Tần suất hỏng hóc</p>
                <p class="text-sm text-slate-700">{{ doc.failure_frequency }}</p>
              </div>
            </div>
          </div>

          <!-- Technical Specification -->
          <div class="card">
            <div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
              <h3 class="text-sm font-semibold text-slate-700">Đặc tả thiết bị (IMM-03)</h3>
              <div v-if="!doc.technical_specification" class="flex items-center gap-2">
                <button class="btn-primary text-xs py-1.5 px-3" @click="handleCreateTs" :disabled="store.loading">
                  Tạo đặc tả mới
                </button>
                <button class="btn-ghost text-xs py-1.5 px-3" @click="showLinkTsPanel = !showLinkTsPanel">
                  Gắn có sẵn
                </button>
              </div>
              <button v-else class="text-xs text-brand-600 hover:underline font-medium"
                      @click="router.push(`/planning/technical-specs/${doc.technical_specification}`)">
                Xem đặc tả →
              </button>
            </div>

            <!-- Link TS panel -->
            <Transition name="slide-fade">
              <div v-if="showLinkTsPanel && !doc.technical_specification"
                   class="mb-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
                <p class="text-xs text-slate-500 mb-2">Chọn đặc tả kỹ thuật đã có để gắn vào phiếu này:</p>
                <div v-if="tsActionError" class="alert-error mb-2 text-xs">{{ tsActionError }}</div>
                <SmartSelect
                  doctype="Technical Specification"
                  placeholder="Tìm đặc tả kỹ thuật..."
                  :model-value="selectedTs"
                  @select="onTsSelect"
                />
                <div class="flex gap-2 mt-2">
                  <button class="btn-primary text-xs py-1.5 px-3" :disabled="store.loading" @click="handleLinkTs">
                    Xác nhận gắn
                  </button>
                  <button class="btn-ghost text-xs py-1.5 px-3" @click="showLinkTsPanel = false">Hủy</button>
                </div>
              </div>
            </Transition>

            <div v-if="doc.technical_specification"
                 class="flex items-center gap-3 p-3 bg-blue-50 rounded-xl border border-blue-100 cursor-pointer"
                 @click="router.push(`/planning/technical-specs/${doc.technical_specification}`)">
              <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <p class="text-sm font-semibold text-blue-800 font-mono">{{ doc.technical_specification }}</p>
                <p class="text-xs text-blue-600">Nhấn để xem chi tiết đặc tả kỹ thuật</p>
              </div>
            </div>

            <div v-else-if="!showLinkTsPanel" class="py-4 text-center text-sm text-slate-400 italic">
              Chưa có đặc tả thiết bị. Tạo mới hoặc gắn đặc tả đã có.
            </div>
          </div>

          <!-- HTM review notes (editable when Under Review) -->
          <div v-if="doc.htmreview_notes || doc.status === 'Under Review'" class="card">
            <h3 class="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b border-slate-100">
              Nhận xét Kỹ thuật (HTM)
              <span v-if="doc.status === 'Under Review'"
                    class="ml-2 text-xs font-normal text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
                Bắt buộc trước khi duyệt
              </span>
            </h3>

            <!-- Editable mode when Under Review -->
            <template v-if="doc.status === 'Under Review'">
              <div v-if="htmNotesError" class="alert-error mb-3 text-xs">{{ htmNotesError }}</div>
              <textarea
                v-model="htmNotesEdit"
                rows="4"
                class="form-textarea w-full"
                placeholder="Nhập nhận xét kỹ thuật của HTM Manager... (bắt buộc để phê duyệt)"
                @focus="!htmNotesEdit && startEditHtmNotes()"
              />
              <div class="flex items-center gap-2 mt-2">
                <button
                  class="btn-primary text-xs py-1.5 px-3"
                  :disabled="htmNotesSaving || store.loading"
                  @click="handleSaveHtmNotes"
                >
                  {{ htmNotesSaving ? 'Đang lưu...' : 'Lưu nhận xét' }}
                </button>
                <span v-if="doc.htmreview_notes" class="text-xs text-emerald-600 flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                  Đã lưu
                </span>
              </div>
            </template>

            <!-- Read-only after Under Review -->
            <p v-else class="text-sm text-slate-700 leading-relaxed">
              {{ doc.htmreview_notes }}
            </p>
          </div>

        </div>

        <!-- Right column: status & timeline -->
        <div class="space-y-6">

          <!-- Status card -->
          <div class="card">
            <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Trạng thái</h3>
            <StatusBadge :state="doc.status" size="md" />

            <!-- Workflow steps indicator -->
            <div class="mt-4 space-y-2">
              <div v-for="step in ['Draft', 'Submitted', 'Under Review', 'Approved']" :key="step"
                   class="flex items-center gap-2 text-xs">
                <span class="w-2 h-2 rounded-full shrink-0"
                      :style="{
                        background: doc.status === step ? '#3b82f6'
                          : ['Approved','Planned'].includes(doc.status) || stepIndex(step) < stepIndex(doc.status)
                            ? '#10b981' : '#e2e8f0'
                      }" />
                <span :class="doc.status === step ? 'text-slate-800 font-medium' : 'text-slate-400'">
                  {{ step === 'Draft' ? 'Nháp' : step === 'Submitted' ? 'Đã nộp'
                     : step === 'Under Review' ? 'Đang xét duyệt' : 'Đã duyệt' }}
                </span>
              </div>
              <div v-if="doc.status === 'Rejected'"
                   class="flex items-center gap-2 text-xs text-red-500">
                <span class="w-2 h-2 rounded-full shrink-0 bg-red-500" />
                Từ chối
              </div>
            </div>
          </div>

          <!-- Meta info -->
          <div class="card">
            <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Thông tin</h3>
            <dl class="space-y-3">
              <div>
                <dt class="text-xs text-slate-400">Người tạo</dt>
                <dd class="text-sm text-slate-700">{{ doc.requested_by }}</dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400">Ngày tạo</dt>
                <dd class="text-sm text-slate-700">{{ formatDate(doc.request_date) }}</dd>
              </div>
            </dl>
          </div>

        </div>
      </div>
    </template>

    <!-- ─── Approve Modal ─── -->
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="showApproveModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
           @click.self="showApproveModal = false">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-fade-in">
          <h3 class="text-base font-semibold text-slate-800 mb-4">Phê duyệt Đánh giá Nhu cầu</h3>

          <div v-if="actionError" class="alert-error mb-4 text-sm">{{ actionError }}</div>

          <div class="space-y-4">
            <div class="form-group">
              <label class="form-label">Ngân sách được duyệt (VNĐ) <span class="text-red-500">*</span></label>
              <input
                v-model.number="approveForm.approved_budget"
                type="number"
                min="0"
                step="1000000"
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Ghi chú <span class="text-slate-400 text-xs">(tùy chọn)</span></label>
              <textarea v-model="approveForm.notes" rows="3" class="form-input resize-none"
                        placeholder="Ghi chú phê duyệt..." />
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button class="btn-ghost" @click="showApproveModal = false">Hủy</button>
            <button class="btn-primary" :disabled="store.loading" @click="handleApprove">
              <svg v-if="store.loading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Xác nhận duyệt
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ─── Reject Modal ─── -->
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="showRejectModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
           @click.self="showRejectModal = false">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-fade-in">
          <h3 class="text-base font-semibold text-slate-800 mb-4">Từ chối Đánh giá Nhu cầu</h3>

          <div v-if="actionError" class="alert-error mb-4 text-sm">{{ actionError }}</div>

          <div class="form-group">
            <label class="form-label">Lý do từ chối <span class="text-red-500">*</span></label>
            <textarea v-model="rejectForm.reason" rows="4" class="form-input resize-none"
                      placeholder="Ghi rõ lý do từ chối (tối thiểu 5 ký tự)..." />
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button class="btn-ghost" @click="showRejectModal = false">Hủy</button>
            <button class="btn-danger" :disabled="store.loading" @click="handleReject">
              Xác nhận từ chối
            </button>
          </div>
        </div>
      </div>
    </Transition>

  </div>

  <ApprovalModal
    :show="showSubmitModal"
    title="Nộp xét duyệt — Chọn người phê duyệt"
    :loading="store.loading"
    @confirm="handleSubmitForReview"
    @cancel="showSubmitModal = false"
  />
</template>

<style scoped>
.slide-fade-enter-active, .slide-fade-leave-active { transition: all .2s ease; }
.slide-fade-enter-from, .slide-fade-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
