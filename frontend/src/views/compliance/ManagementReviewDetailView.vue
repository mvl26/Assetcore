<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Chi tiết Soát xét quản lý (BUG-16-10): nhập attendees / scorecard /
// output actions, vòng đời theo workflow JSON
// "IMM-16 Management Review Workflow" (Draft → Held → Minutes Approved →
// Closed). Action labels khớp chính xác workflow.
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import { getManagementReview } from '@/api/imm16'
import type { ManagementReview, MRStatus, MRAttendee, MROutputActionRow } from '@/api/imm16'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import RecordHistory from '@/components/common/RecordHistory.vue'
import DateInput from '@/components/common/DateInput.vue'
import FileUploadField from '@/components/common/FileUploadField.vue'
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import { loadErrorKind, toApiError, type DetailLoadKind } from '@/api/errors'

const route = useRoute()
const router = useRouter()
const store = useImm16Store()
const api = useApi()
const name = route.params.id as string

const mr = ref<ManagementReview | null>(null)
const loading = ref(true)
// '' = nạp OK; 'notfound' = mã cuộc soát xét không tồn tại (404); 'unknown' = lỗi khác.
const loadFailed = ref<'' | DetailLoadKind>('')
const loadErrMsg = ref('')
const historyRef = ref<InstanceType<typeof RecordHistory> | null>(null)

// Server-driven CTA (GATE-8 / LL-FE-51, mirror get_capa/get_audit/get_finding):
// nút vòng đời gate theo `mr.allowed_transitions` (BE derive từ CÙNG SoT
// _MR_TRANSITIONS mà advance_mr_state/finalize_management_review enforce) + cờ
// capability server can_advance/can_close. KHÔNG hardcode client-map làm GATE
// hay `status === 'Minutes Approved'` (dead-control → 403). Thiếu cờ (BE cũ) → 0 nút.
const allowedTransitions = computed<string[]>(() => mr.value?.allowed_transitions ?? [])
// Label-map CHỈ để hiển thị TEXT nút (KHÔNG còn vai trò GATE) — khớp
// imm_16_mr_workflow.json EXACT.
const NEXT_LABEL: Record<string, { label: string; target: MRStatus }> = {
  Draft: { label: 'Đánh dấu Đã họp', target: 'Held' },
  Held: { label: 'Phê duyệt Biên bản', target: 'Minutes Approved' },
}
const status = computed<string>(() => mr.value?.status || 'Draft')
const isClosed = computed(() => status.value === 'Closed')
const editable = computed(() => !isClosed.value)
// Nhãn bước kế theo status (CHỈ tra cứu text — không gate).
const advanceStep = computed(() => NEXT_LABEL[status.value] ?? null)
// Nút 'Đánh dấu Đã họp'/'Phê duyệt Biên bản' chỉ hiện khi server cho phép chuyển
// tới target ĐÓ và user có compliance.submit (can_advance===true).
const canAdvance = computed(() =>
  advanceStep.value !== null
  && allowedTransitions.value.includes(advanceStep.value.target)
  && mr.value?.can_advance === true)
// Nút 'Đóng và xuất biên bản' chỉ hiện khi server cho phép chuyển tới 'Closed' và
// user có compliance.submit (can_close===true). Gỡ hardcode status==='Minutes Approved'.
const canClose = computed(() =>
  allowedTransitions.value.includes('Closed') && mr.value?.can_close === true)
// 0 nút CTA (chưa Closed) → hint giải thích (chống dead/empty action panel, LL-FE-23/26).
const showNoActionHint = computed(() =>
  !isClosed.value && !canAdvance.value && !canClose.value)

// Mã soát xét sai / đã xoá ⇒ 404: nuốt ApiError (không rò console) + empty-state
// chuẩn có lối về danh sách, thay dòng chữ đỏ cụt (dead-end).
async function load() {
  loading.value = true
  // Xoá lỗi ở ĐẦU lượt (INV-UX4-7) — nếu không, banner lỗi cũ đứng nguyên trong lúc
  // request mới đang bay ⇒ nút nạp lại trông như chết.
  loadFailed.value = ''
  loadErrMsg.value = ''
  try {
    mr.value = await getManagementReview(name)
  } catch (e: unknown) {
    loadFailed.value = loadErrorKind(e)
    loadErrMsg.value = toApiError(e).message
    mr.value = null
  } finally {
    loading.value = false
  }
}
function refreshAll() {
  load()
  historyRef.value?.reload()
}

// ── Edit content ──
const showEdit = ref(false)
interface MREditForm {
  review_date: string
  chair: string
  scorecard_ref: string
  inputs_summary: string
  audit_summary: string
  capa_summary: string
  capa_effectiveness: string
  training_compliance: string
  risk_review: string
  qms_changes_decided: string
  next_review_date: string
  minutes_doc: string
}
const editForm = ref<MREditForm>({
  review_date: '', chair: '', scorecard_ref: '', inputs_summary: '',
  audit_summary: '', capa_summary: '', capa_effectiveness: '',
  training_compliance: '', risk_review: '', qms_changes_decided: '',
  next_review_date: '', minutes_doc: '',
})
const editAttendees = ref<MRAttendee[]>([])
const editActions = ref<MROutputActionRow[]>([])
function openEdit() {
  if (!mr.value) return
  editForm.value = {
    review_date: mr.value.review_date || '',
    chair: mr.value.chair || '',
    scorecard_ref: mr.value.scorecard_ref || '',
    inputs_summary: mr.value.inputs_summary || '',
    audit_summary: mr.value.audit_summary || '',
    capa_summary: mr.value.capa_summary || '',
    capa_effectiveness: mr.value.capa_effectiveness || '',
    training_compliance: mr.value.training_compliance || '',
    risk_review: mr.value.risk_review || '',
    qms_changes_decided: mr.value.qms_changes_decided || '',
    next_review_date: mr.value.next_review_date || '',
    minutes_doc: mr.value.minutes_doc || '',
  }
  editAttendees.value = (mr.value.attendees || []).map(a => ({ ...a }))
  editActions.value = (mr.value.output_actions || []).map(a => ({ ...a }))
  if (!editActions.value.length) addAction()
  showEdit.value = true
}
function addAttendee() { editAttendees.value.push({ user: '', role_title: '', present: true, signed: false }) }
function removeAttendee(i: number) { editAttendees.value.splice(i, 1) }
function addAction() { editActions.value.push({ action_description: '', responsible: '', due_date: '', priority: 'Medium', status: 'Open' }) }
function removeAction(i: number) { editActions.value.splice(i, 1) }

async function saveEdit() {
  const res = await api.run(
    () => store.actionUpdateReview(name, {
      ...editForm.value,
      attendees: editAttendees.value,
      output_actions: editActions.value.filter(a => a.action_description.trim()),
    }),
    { successMessage: 'Đã lưu nội dung soát xét' },
  )
  if (res) { showEdit.value = false; refreshAll() }
}

// ── Workflow advance ──
async function advance() {
  const step = advanceStep.value
  if (!step || !canAdvance.value) return
  const res = await api.run(
    () => store.actionAdvanceMr(name, step.target),
    { successMessage: 'Đã cập nhật trạng thái cuộc soát xét' },
  )
  if (res) refreshAll()
}

// ── Close (finalize) ──
const showClose = ref(false)
const closeMinutes = ref('')
const closeActions = ref<{ action: string; owner: string; due_date: string }[]>([
  { action: '', owner: '', due_date: '' },
])
function openClose() {
  closeMinutes.value = mr.value?.minutes_doc || ''
  closeActions.value = (mr.value?.output_actions || []).map(a => ({
    action: a.action_description, owner: a.responsible, due_date: a.due_date || '',
  }))
  if (!closeActions.value.length) closeActions.value = [{ action: '', owner: '', due_date: '' }]
  showClose.value = true
}
function addCloseAction() { closeActions.value.push({ action: '', owner: '', due_date: '' }) }
function removeCloseAction(i: number) {
  closeActions.value.splice(i, 1)
  if (!closeActions.value.length) addCloseAction()
}
async function submitClose() {
  const actions = closeActions.value.filter(a => a.action.trim() && a.owner.trim())
  if (!closeMinutes.value.trim()) { return }
  if (!actions.length) { return }
  const res = await api.run(
    () => store.actionFinalizeReview(name, closeMinutes.value, actions),
    { successMessage: 'Đã đóng & xuất biên bản soát xét' },
  )
  if (res) { showClose.value = false; refreshAll() }
}

function scorecardText(): string {
  const x = mr.value as (ManagementReview & { scorecard_score_pct?: number; scorecard_period?: string }) | null
  if (x?.scorecard_score_pct != null) {
    return `${x.scorecard_score_pct.toFixed(1)}% (${x.scorecard_period || ''}) · ${x.scorecard_ref}`
  }
  return mr.value?.scorecard_ref || '—'
}

onMounted(load)
</script>

<template>
  <DetailPageShell
    :loading="loading"
    :error-kind="loadFailed"
    :error-message="loadErrMsg"
    :doc="mr"
    entity-label="cuộc soát xét quản lý"
    :record-id="name"
    back-label="Về danh sách soát xét"
    @retry="load()"
    @back="router.push('/compliance/mr')"
  >
    <template #header>
      <PageHeader
        v-if="mr"
        :title="`Soát xét quản lý ${mr.quarter}`"
        :subtitle="`IMM-16 · ${mr.name}`"
        :breadcrumb="[
          { label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' },
          { label: 'Soát xét quản lý', to: '/compliance/mr' },
          { label: mr.quarter },
        ]"
      />
    </template>

    <!-- Panel thao tác — chỉ render ở trạng thái content (INV-UX4-5): không còn
         cảnh nút "Đóng và xuất biên bản" hiện trên khung chi tiết rỗng. -->
    <template #actions>
      <button v-if="editable" class="btn-secondary text-sm" @click="openEdit">Sửa nội dung</button>
      <button
        v-if="canAdvance"
        data-testid="cta-advance"
        class="btn-primary text-sm"
        :disabled="api.loading.value"
        @click="advance"
      >{{ advanceStep?.label }}</button>
      <button
        v-if="canClose"
        data-testid="cta-close"
        class="btn-primary text-sm"
        :disabled="api.loading.value"
        @click="openClose"
      >Đóng và xuất biên bản</button>
      <span
        v-if="showNoActionHint"
        data-testid="no-actions-hint"
        class="text-xs text-slate-500 italic max-w-xs text-right"
      >Bạn không có quyền chuyển trạng thái cuộc soát xét này. Liên hệ quản trị viên hoặc Quản lý chất lượng để duyệt/đóng.</span>
    </template>

    <template v-if="mr">
      <div class="card p-5 space-y-4">
        <div class="flex flex-wrap items-center gap-2">
          <StatusBadge :state="mr.status" />
          <span class="text-xs text-slate-400">Cập nhật vòng đời: Bản nháp → Đã họp → Biên bản đã duyệt → Đã đóng</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div><p class="t-eyebrow mb-1">Quý</p><p class="text-slate-700">{{ mr.quarter }}</p></div>
          <div><p class="t-eyebrow mb-1">Ngày họp</p><p class="text-slate-700">{{ formatDate(mr.review_date) }}</p></div>
          <div><p class="t-eyebrow mb-1">Chủ tọa</p><p class="text-slate-700">{{ mr.chair_name || mr.chair || '—' }}</p></div>
          <div><p class="t-eyebrow mb-1">Bảng điểm</p><p class="text-slate-700">{{ scorecardText() }}</p></div>
          <div><p class="t-eyebrow mb-1">Họp tiếp theo</p><p class="text-slate-700">{{ formatDate(mr.next_review_date) }}</p></div>
          <div class="sm:col-span-2 lg:col-span-3">
            <p class="t-eyebrow mb-1">Biên bản</p>
            <a v-if="mr.minutes_doc" :href="mr.minutes_doc" target="_blank" class="text-brand-700 hover:underline text-sm break-all">{{ mr.minutes_doc }}</a>
            <span v-else class="text-slate-400 text-sm">—</span>
          </div>
        </div>
      </div>

      <!-- Summaries -->
      <div class="card p-5 grid grid-cols-1 md:grid-cols-2 gap-5 text-sm">
        <div><p class="t-eyebrow mb-1">Tóm tắt đầu vào</p><p class="text-slate-700 whitespace-pre-line">{{ mr.inputs_summary || '—' }}</p></div>
        <div><p class="t-eyebrow mb-1">Tóm tắt kiểm toán</p><p class="text-slate-700 whitespace-pre-line">{{ mr.audit_summary || '—' }}</p></div>
        <div><p class="t-eyebrow mb-1">Tóm tắt hành động khắc phục/phòng ngừa</p><p class="text-slate-700 whitespace-pre-line">{{ mr.capa_summary || '—' }}</p></div>
        <div><p class="t-eyebrow mb-1">Hiệu quả hành động khắc phục/phòng ngừa</p><p class="text-slate-700 whitespace-pre-line">{{ mr.capa_effectiveness || '—' }}</p></div>
        <div><p class="t-eyebrow mb-1">Tuân thủ đào tạo</p><p class="text-slate-700 whitespace-pre-line">{{ mr.training_compliance || '—' }}</p></div>
        <div><p class="t-eyebrow mb-1">Xem xét rủi ro</p><p class="text-slate-700 whitespace-pre-line">{{ mr.risk_review || '—' }}</p></div>
        <div class="md:col-span-2"><p class="t-eyebrow mb-1">Thay đổi hệ thống quản lý chất lượng đã quyết định</p><p class="text-slate-700 whitespace-pre-line">{{ mr.qms_changes_decided || '—' }}</p></div>
      </div>

      <!-- Attendees -->
      <div class="card p-5">
        <h2 class="font-semibold text-slate-700 mb-3">Thành viên tham dự</h2>
        <table v-if="(mr.attendees || []).length" class="min-w-full divide-y divide-slate-100 text-sm">
          <thead><tr><th class="table-header">Người</th><th class="table-header">Chức danh</th><th class="table-header">Có mặt</th><th class="table-header">Đã ký</th></tr></thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="(a, i) in mr.attendees" :key="i">
              <td class="table-cell">{{ a.user_name || a.user }}</td>
              <td class="table-cell">{{ a.role_title || '—' }}</td>
              <td class="table-cell">{{ a.present ? '✓' : '—' }}</td>
              <td class="table-cell">{{ a.signed ? '✓' : '—' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-sm text-slate-400">Chưa có thành viên.</p>
      </div>

      <!-- Output actions -->
      <div class="card p-5">
        <h2 class="font-semibold text-slate-700 mb-3">Hành động đầu ra</h2>
        <table v-if="(mr.output_actions || []).length" class="min-w-full divide-y divide-slate-100 text-sm">
          <thead><tr><th class="table-header">Mô tả</th><th class="table-header">Người phụ trách</th><th class="table-header">Hạn</th><th class="table-header">Ưu tiên</th><th class="table-header">Trạng thái</th></tr></thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="(a, i) in mr.output_actions" :key="i">
              <td class="table-cell">{{ a.action_description }}</td>
              <td class="table-cell">{{ a.responsible_name || a.responsible }}</td>
              <td class="table-cell">{{ formatDate(a.due_date) }}</td>
              <td class="table-cell">{{ a.priority || '—' }}</td>
              <td class="table-cell">{{ a.status || '—' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-sm text-slate-400">Chưa có hành động đầu ra. Cần ≥1 hành động trước khi đóng.</p>
      </div>

      <RecordHistory ref="historyRef" ref-doctype="IMM Management Review" :ref-name="mr.name" />
    </template>

    <!-- Edit modal -->
    <BaseModal v-if="showEdit" title="Sửa nội dung soát xét" size="xl" @close="showEdit = false">
      <div class="space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="form-group"><label class="form-label">Ngày họp</label><DateInput v-model="editForm.review_date" class="form-input" /></div>
          <div class="form-group"><label class="form-label">Chủ tọa</label><ApproverSelect v-model="editForm.chair" context="user" placeholder="Chọn người dùng..." /></div>
          <div class="form-group"><label class="form-label">Tham chiếu bảng điểm</label><input v-model="editForm.scorecard_ref" class="form-input" placeholder="SCR-2026-..." /></div>
          <div class="form-group"><label class="form-label">Họp tiếp theo</label><DateInput v-model="editForm.next_review_date" class="form-input" /></div>
          <div class="form-group sm:col-span-2">
            <FileUploadField
              v-model="editForm.minutes_doc"
              label="Biên bản họp"
              doctype="IMM Management Review"
              fieldname="minutes_doc"
              :docname="name"
              hint="Bấm để tải biên bản họp (pdf, doc — tối đa 10MB)"
            />
          </div>
        </div>
        <div class="form-group"><label class="form-label">Tóm tắt đầu vào</label><textarea v-model="editForm.inputs_summary" rows="2" class="form-input" /></div>
        <div class="form-group"><label class="form-label">Tóm tắt kiểm toán</label><textarea v-model="editForm.audit_summary" rows="2" class="form-input" /></div>
        <div class="form-group"><label class="form-label">Tóm tắt hành động khắc phục/phòng ngừa</label><textarea v-model="editForm.capa_summary" rows="2" class="form-input" /></div>
        <div class="form-group"><label class="form-label">Xem xét rủi ro</label><textarea v-model="editForm.risk_review" rows="2" class="form-input" /></div>
        <div class="form-group"><label class="form-label">Thay đổi hệ thống quản lý chất lượng đã quyết định</label><textarea v-model="editForm.qms_changes_decided" rows="2" class="form-input" /></div>

        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="form-label !mb-0">Thành viên tham dự</label>
            <button class="text-xs text-brand-600 font-medium hover:underline" @click="addAttendee">Thêm thành viên</button>
          </div>
          <div v-for="(a, i) in editAttendees" :key="'att'+i" class="grid grid-cols-12 gap-2 mb-2 items-center">
            <ApproverSelect v-model="a.user" context="user" class="col-span-4" placeholder="Chọn người dùng..." />
            <input v-model="a.role_title" class="form-input text-sm col-span-4" placeholder="Chức danh" />
            <label class="col-span-2 text-xs flex items-center gap-1"><input v-model="a.present" type="checkbox" /> Có mặt</label>
            <button class="col-span-2 text-xs text-red-600" @click="removeAttendee(i)">Xoá</button>
          </div>
        </div>

        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="form-label !mb-0">Hành động đầu ra</label>
            <button class="text-xs text-brand-600 font-medium hover:underline" @click="addAction">Thêm hành động</button>
          </div>
          <div v-for="(a, i) in editActions" :key="'act'+i" class="grid grid-cols-12 gap-2 mb-2 items-center">
            <input v-model="a.action_description" class="form-input text-sm col-span-5" placeholder="Mô tả" />
            <ApproverSelect v-model="a.responsible" context="user" class="col-span-3" placeholder="Người phụ trách..." />
            <DateInput v-model="a.due_date" class="form-input text-sm col-span-3" />
            <button class="col-span-1 text-xs text-red-600" @click="removeAction(i)">×</button>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showEdit = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="saveEdit">Lưu</button>
      </template>
    </BaseModal>

    <!-- Close modal -->
    <BaseModal v-if="showClose" title="Đóng & xuất biên bản" size="xl" @close="showClose = false">
      <div class="space-y-4">
        <div class="form-group">
          <label class="form-label">URL biên bản *</label>
          <input v-model="closeMinutes" class="form-input" placeholder="https://..." />
        </div>
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="form-label !mb-0">Hành động đầu ra (≥ 1) *</label>
            <button class="text-xs text-brand-600 font-medium hover:underline" @click="addCloseAction">Thêm hành động</button>
          </div>
          <div v-for="(a, i) in closeActions" :key="i" class="grid grid-cols-12 gap-2 mb-2 items-center">
            <input v-model="a.action" class="form-input text-sm col-span-5" placeholder="Mô tả" />
            <ApproverSelect v-model="a.owner" context="user" class="col-span-3" placeholder="Chọn người phụ trách..." />
            <DateInput v-model="a.due_date" class="form-input text-sm col-span-3" />
            <button class="col-span-1 text-xs text-red-600" @click="removeCloseAction(i)">×</button>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showClose = false">Huỷ</button>
        <button class="btn-primary" data-testid="cta-close-confirm" :disabled="api.loading.value" @click="submitClose">Đóng soát xét</button>
      </template>
    </BaseModal>
  </DetailPageShell>
</template>
