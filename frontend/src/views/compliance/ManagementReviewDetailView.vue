<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Chi tiết Soát xét quản lý (BUG-16-10): nhập attendees / scorecard /
// output actions, vòng đời theo workflow JSON
// "IMM-16 Management Review Workflow" (Draft → Held → Minutes Approved →
// Closed). Action labels khớp chính xác workflow.
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import { getManagementReview } from '@/api/imm16'
import type { ManagementReview, MRStatus, MRAttendee, MROutputActionRow } from '@/api/imm16'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import RecordHistory from '@/components/common/RecordHistory.vue'

const route = useRoute()
const store = useImm16Store()
const api = useApi()
const name = route.params.id as string

const mr = ref<ManagementReview | null>(null)
const loading = ref(true)
const historyRef = ref<InstanceType<typeof RecordHistory> | null>(null)

// Workflow action labels — khớp imm_16_mr_workflow.json EXACT.
const NEXT_LABEL: Record<string, { label: string; target: MRStatus }> = {
  Draft: { label: 'Đánh dấu Đã họp', target: 'Held' },
  Held: { label: 'Phê duyệt Biên bản', target: 'Minutes Approved' },
}
const status = computed<string>(() => mr.value?.status || 'Draft')
const nextStep = computed(() => NEXT_LABEL[status.value] ?? null)
const canClose = computed(() => status.value === 'Minutes Approved')
const isClosed = computed(() => status.value === 'Closed')
const editable = computed(() => !isClosed.value)

async function load() {
  loading.value = true
  try {
    mr.value = await getManagementReview(name)
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
  if (!nextStep.value) return
  const step = nextStep.value
  const res = await api.run(
    () => store.actionAdvanceMr(name, step.target),
    { successMessage: `Đã chuyển sang: ${step.target}` },
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
  <div class="page-container animate-fade-in space-y-5">
    <div v-if="loading" class="p-6"><SkeletonLoader variant="form" :rows="6" /></div>
    <div v-else-if="!mr" class="text-center text-red-500 py-12">Không tìm thấy cuộc soát xét</div>

    <template v-else>
      <PageHeader
        :title="`Soát xét quản lý ${mr.quarter}`"
        :subtitle="`IMM-16 · ${mr.name}`"
        :breadcrumb="[
          { label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' },
          { label: 'Soát xét quản lý', to: '/compliance/mr' },
          { label: mr.quarter },
        ]"
      >
        <template #actions>
          <button v-if="editable" class="btn-secondary text-sm" @click="openEdit">Sửa nội dung</button>
          <button v-if="nextStep" class="btn-primary text-sm" :disabled="api.loading.value" @click="advance">{{ nextStep.label }}</button>
          <button v-if="canClose" class="btn-primary text-sm" :disabled="api.loading.value" @click="openClose">Đóng và xuất biên bản</button>
        </template>
      </PageHeader>

      <div class="card p-5 space-y-4">
        <div class="flex flex-wrap items-center gap-2">
          <StatusBadge :state="mr.status" />
          <span class="text-xs text-slate-400">Cập nhật vòng đời: Draft → Held → Minutes Approved → Closed</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div><p class="t-eyebrow mb-1">Quý</p><p class="text-slate-700">{{ mr.quarter }}</p></div>
          <div><p class="t-eyebrow mb-1">Ngày họp</p><p class="text-slate-700">{{ formatDate(mr.review_date) }}</p></div>
          <div><p class="t-eyebrow mb-1">Chủ tọa</p><p class="text-slate-700">{{ mr.chair_name || mr.chair || '—' }}</p></div>
          <div><p class="t-eyebrow mb-1">Scorecard</p><p class="text-slate-700">{{ scorecardText() }}</p></div>
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
        <div><p class="t-eyebrow mb-1">Tóm tắt audit</p><p class="text-slate-700 whitespace-pre-line">{{ mr.audit_summary || '—' }}</p></div>
        <div><p class="t-eyebrow mb-1">Tóm tắt CAPA</p><p class="text-slate-700 whitespace-pre-line">{{ mr.capa_summary || '—' }}</p></div>
        <div><p class="t-eyebrow mb-1">Hiệu quả CAPA</p><p class="text-slate-700 whitespace-pre-line">{{ mr.capa_effectiveness || '—' }}</p></div>
        <div><p class="t-eyebrow mb-1">Tuân thủ đào tạo</p><p class="text-slate-700 whitespace-pre-line">{{ mr.training_compliance || '—' }}</p></div>
        <div><p class="t-eyebrow mb-1">Xem xét rủi ro</p><p class="text-slate-700 whitespace-pre-line">{{ mr.risk_review || '—' }}</p></div>
        <div class="md:col-span-2"><p class="t-eyebrow mb-1">Thay đổi QMS đã quyết định</p><p class="text-slate-700 whitespace-pre-line">{{ mr.qms_changes_decided || '—' }}</p></div>
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
          <div class="form-group"><label class="form-label">Ngày họp</label><input v-model="editForm.review_date" type="date" class="form-input" /></div>
          <div class="form-group"><label class="form-label">Chủ tọa (User)</label><input v-model="editForm.chair" class="form-input" /></div>
          <div class="form-group"><label class="form-label">Scorecard ref</label><input v-model="editForm.scorecard_ref" class="form-input" placeholder="SCR-2026-..." /></div>
          <div class="form-group"><label class="form-label">Họp tiếp theo</label><input v-model="editForm.next_review_date" type="date" class="form-input" /></div>
          <div class="form-group sm:col-span-2"><label class="form-label">URL biên bản</label><input v-model="editForm.minutes_doc" class="form-input" placeholder="https://..." /></div>
        </div>
        <div class="form-group"><label class="form-label">Tóm tắt đầu vào</label><textarea v-model="editForm.inputs_summary" rows="2" class="form-input" /></div>
        <div class="form-group"><label class="form-label">Tóm tắt audit</label><textarea v-model="editForm.audit_summary" rows="2" class="form-input" /></div>
        <div class="form-group"><label class="form-label">Tóm tắt CAPA</label><textarea v-model="editForm.capa_summary" rows="2" class="form-input" /></div>
        <div class="form-group"><label class="form-label">Xem xét rủi ro</label><textarea v-model="editForm.risk_review" rows="2" class="form-input" /></div>
        <div class="form-group"><label class="form-label">Thay đổi QMS đã quyết định</label><textarea v-model="editForm.qms_changes_decided" rows="2" class="form-input" /></div>

        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="form-label !mb-0">Thành viên tham dự</label>
            <button class="text-xs text-brand-600 font-medium hover:underline" @click="addAttendee">Thêm thành viên</button>
          </div>
          <div v-for="(a, i) in editAttendees" :key="'att'+i" class="grid grid-cols-12 gap-2 mb-2 items-center">
            <input v-model="a.user" class="form-input text-sm col-span-4" placeholder="user@hospital.vn" />
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
            <input v-model="a.responsible" class="form-input text-sm col-span-3" placeholder="Người phụ trách" />
            <input v-model="a.due_date" type="date" class="form-input text-sm col-span-3" />
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
          <label class="form-label">URL biên bản (minutes) *</label>
          <input v-model="closeMinutes" class="form-input" placeholder="https://..." />
        </div>
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="form-label !mb-0">Hành động đầu ra (≥ 1) *</label>
            <button class="text-xs text-brand-600 font-medium hover:underline" @click="addCloseAction">Thêm hành động</button>
          </div>
          <div v-for="(a, i) in closeActions" :key="i" class="grid grid-cols-12 gap-2 mb-2 items-center">
            <input v-model="a.action" class="form-input text-sm col-span-5" placeholder="Mô tả" />
            <input v-model="a.owner" class="form-input text-sm col-span-3" placeholder="user@hospital.vn" />
            <input v-model="a.due_date" type="date" class="form-input text-sm col-span-3" />
            <button class="col-span-1 text-xs text-red-600" @click="removeCloseAction(i)">×</button>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showClose = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="submitClose">Đóng soát xét</button>
      </template>
    </BaseModal>
  </div>
</template>
