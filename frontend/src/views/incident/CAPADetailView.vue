<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Chi tiết CAPA với vòng đời QMS đầy đủ (BUG-16-08):
// RCA method + mô tả, hành động khắc phục/phòng ngừa, xác minh hiệu quả,
// chuyển trạng thái theo workflow JSON "IMM-16 CAPA Workflow" (action labels
// PHẢI khớp chính xác), audit trail, link Finding nguồn.
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import type { CapaDetail, CapaWorkflowState } from '@/api/imm16'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import RecordHistory from '@/components/common/RecordHistory.vue'
import { sanitizeHtml } from '@/utils/sanitizeHtml'
import { translateStatus } from '@/utils/formatters'
import { capaWorkflowLabel } from '@/constants/labels'

const route = useRoute()
const router = useRouter()
const store = useImm16Store()
const api = useApi()
const name = route.params.id as string

const capa = ref<CapaDetail | null>(null)
const loading = ref(true)
const historyRef = ref<InstanceType<typeof RecordHistory> | null>(null)

const RCA_METHODS = ['5-Why', 'Fishbone', 'Fault Tree', 'Pareto', 'Other']

// ── Workflow transitions — labels khớp imm_16_capa_workflow.json EXACT ──
interface Transition { label: string; target: CapaWorkflowState }
const TRANSITIONS: Record<string, Transition[]> = {
  Open: [{ label: 'Bắt đầu điều tra', target: 'Investigating' }],
  Investigating: [{ label: 'Lập kế hoạch hành động', target: 'Action Plan' }],
  'Action Plan': [{ label: 'Bắt đầu thực thi', target: 'Implementation' }],
  Implementation: [{ label: 'Chuyển sang xác minh', target: 'Verification' }],
  Verification: [],          // dùng effectiveness check (Đóng / Mở lại)
  'Re-opened': [{ label: 'Bắt đầu điều tra lại', target: 'Investigating' }],
}

const wfState = computed<string>(() => capa.value?.workflow_state || 'Open')
const transitions = computed<Transition[]>(() => TRANSITIONS[wfState.value] ?? [])
const isVerification = computed(() => wfState.value === 'Verification')
const isClosed = computed(() => wfState.value === 'Closed')
const isEditable = computed(() => !isClosed.value)

// Lifecycle status (SoT) — KHÁC workflow_state (stage). Cron check_capa_overdue
// flip `status`='Overdue' mà KHÔNG đổi workflow_state, nên header phải surface
// CẢ HAI để khớp CAPAListView (render capa.status) + DB + get_capa API.
// Fallback về wfState nếu BE chưa trả status (an toàn, không vỡ layout cũ).
const lifecycleStatus = computed<string>(() => capa.value?.status || wfState.value)

const loadError = ref('')
async function load() {
  loading.value = true
  try {
    capa.value = await store.fetchCapaDetail(name)
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : 'Không tải được CAPA'
  } finally {
    loading.value = false
  }
}

function refreshAll() {
  load()
  historyRef.value?.reload()
}

// ── Edit narrative fields ──
const showEdit = ref(false)
const editForm = ref({
  description: '', root_cause: '', corrective_action: '',
  preventive_action: '', imm_root_cause_method: '', verification_notes: '',
})
function openEdit() {
  if (!capa.value) return
  editForm.value = {
    description: capa.value.description || '',
    root_cause: capa.value.root_cause || '',
    corrective_action: capa.value.corrective_action || '',
    preventive_action: capa.value.preventive_action || '',
    imm_root_cause_method: capa.value.imm_root_cause_method || '',
    verification_notes: capa.value.verification_notes || '',
  }
  showEdit.value = true
}
async function saveEdit() {
  const res = await api.run(
    () => store.actionUpdateCapaFields(name, { ...editForm.value }),
    { successMessage: 'Đã lưu nội dung CAPA' },
  )
  if (res) { showEdit.value = false; refreshAll() }
}

// ── Workflow transition ──
const showTransition = ref(false)
const pendingTransition = ref<Transition | null>(null)
const transitionPayload = ref<{ imm_root_cause_method: string; due_date: string }>({
  imm_root_cause_method: '', due_date: '',
})
function startTransition(t: Transition) {
  pendingTransition.value = t
  transitionPayload.value = {
    imm_root_cause_method: capa.value?.imm_root_cause_method || '5-Why',
    due_date: capa.value?.due_date || '',
  }
  showTransition.value = true
}
async function confirmTransition() {
  if (!pendingTransition.value) return
  const t = pendingTransition.value
  const payload: Record<string, unknown> = {}
  if (t.target === 'Action Plan') {
    payload.imm_root_cause_method = transitionPayload.value.imm_root_cause_method
    if (transitionPayload.value.due_date) payload.due_date = transitionPayload.value.due_date
  }
  const res = await api.run(
    () => store.actionAdvanceCapa(name, t.target, payload),
    { successMessage: `Đã chuyển sang: ${t.target}` },
  )
  if (res) { showTransition.value = false; pendingTransition.value = null; refreshAll() }
}

// ── Effectiveness check (Verification) ──
const showEffectiveness = ref(false)
const effResult = ref<'Effective' | 'Partially Effective' | 'Not Effective'>('Effective')
const effEvidence = ref('')
async function submitEffectiveness() {
  const res = await api.run(
    () => store.actionEffectivenessCheck(name, effResult.value, effEvidence.value),
    { successMessage: 'Đã ghi nhận kết quả xác minh hiệu quả' },
  )
  if (res) { showEffectiveness.value = false; effEvidence.value = ''; refreshAll() }
}

function formatDate(d?: string | null) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center gap-3">
      <button class="text-slate-500 hover:text-slate-700 text-sm" @click="router.push('/capas')">← Quay lại</button>
      <h1 class="text-xl font-semibold text-slate-800">Chi tiết CAPA</h1>
    </div>

    <div v-if="loading" class="p-6"><SkeletonLoader variant="form" :rows="6" /></div>
    <div v-else-if="!capa" class="text-center text-red-500 py-12">{{ loadError || 'Không tìm thấy CAPA' }}</div>

    <template v-else>
      <!-- Header -->
      <div class="card p-5 space-y-3">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs text-slate-400 font-mono">{{ capa.name }}</p>
            <p class="text-base font-medium text-slate-800 mt-1">{{ capa.description || '(Chưa có mô tả)' }}</p>
          </div>
          <div class="flex flex-wrap items-end gap-3 flex-shrink-0">
            <div class="flex flex-col items-center gap-1">
              <span class="t-eyebrow">Mức độ</span>
              <StatusBadge :state="capa.severity" />
            </div>
            <!-- Lifecycle status (SoT) — khớp CAPAListView/DB, invariant dưới cron flip -->
            <div class="flex flex-col items-center gap-1">
              <span class="t-eyebrow">Trạng thái</span>
              <StatusBadge :state="lifecycleStatus" />
            </div>
            <!-- Workflow stage (giai đoạn máy trạng thái) — drive nút transition -->
            <div class="flex flex-col items-center gap-1">
              <span class="t-eyebrow">Tiến trình</span>
              <StatusBadge :state="wfState" />
            </div>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm pt-3 border-t border-slate-100">
          <div>
            <p class="t-eyebrow mb-1">Thiết bị</p>
            <p class="font-medium">{{ capa.asset_name || capa.asset || '—' }}</p>
          </div>
          <div>
            <p class="t-eyebrow mb-1">Người phụ trách</p>
            <p class="font-medium">{{ capa.responsible_name || capa.responsible || '—' }}</p>
          </div>
          <div>
            <p class="t-eyebrow mb-1">Hạn xử lý</p>
            <p class="font-medium" :class="capa.due_date && new Date(capa.due_date) < new Date() && !isClosed ? 'text-red-600' : ''">{{ formatDate(capa.due_date) }}</p>
          </div>
          <div>
            <p class="t-eyebrow mb-1">Mức rủi ro / Reopen</p>
            <p class="font-medium">{{ capa.imm_risk_level ? translateStatus(capa.imm_risk_level) : '—' }} · {{ capa.imm_reopen_count ?? 0 }} lần</p>
          </div>
        </div>
        <div v-if="capa.finding_ref || capa.incident_ref" class="pt-3 border-t border-slate-100 space-y-1.5">
          <div v-if="capa.finding_ref">
            <p class="t-eyebrow mb-1">Phát hiện tuân thủ nguồn</p>
            <button class="font-mono text-sm text-brand-700 font-semibold hover:underline" @click="router.push(`/compliance/findings/${capa.finding_ref}`)">
              {{ capa.finding_ref }}
            </button>
            <span v-if="capa.finding_rule" class="text-xs text-slate-400 ml-2">({{ capa.finding_rule }})</span>
          </div>
          <div v-if="capa.incident_ref">
            <p class="t-eyebrow mb-1">Sự cố nguồn</p>
            <button class="font-mono text-sm text-brand-700 font-semibold hover:underline" @click="router.push(`/incidents/${capa.incident_ref}`)">
              {{ capa.incident_ref }}
            </button>
            <span v-if="capa.incident_subject" class="text-xs text-slate-500 ml-2">— {{ capa.incident_subject }}</span>
          </div>
        </div>
      </div>

      <!-- Actions bar -->
      <div class="card p-4 flex flex-wrap items-center gap-2">
        <button v-if="isEditable" class="btn-secondary text-sm" @click="openEdit">Sửa nội dung</button>
        <button
          v-for="t in transitions" :key="t.target"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="startTransition(t)"
        >{{ t.label }}</button>
        <template v-if="isVerification">
          <button class="btn-primary text-sm" :disabled="api.loading.value" @click="effResult = 'Effective'; showEffectiveness = true">Đóng CAPA</button>
          <button class="btn-ghost text-sm" :disabled="api.loading.value" @click="effResult = 'Not Effective'; showEffectiveness = true">Mở lại do chưa hiệu quả</button>
        </template>
        <span v-if="isClosed" class="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-1">CAPA đã đóng — {{ formatDate(capa.closed_date) }}</span>
      </div>

      <!-- QMS content -->
      <div class="card p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
        <div>
          <p class="t-eyebrow mb-1.5">Phương pháp phân tích gốc rễ</p>
          <p class="text-sm text-slate-700">{{ capa.imm_root_cause_method || '— (chưa chọn)' }}</p>
        </div>
        <div>
          <p class="t-eyebrow mb-1.5">Phân tích nguyên nhân gốc</p>
          <div class="rich-text text-sm text-slate-700" v-html="sanitizeHtml(capa.root_cause) || '—'" />
        </div>
        <div>
          <p class="t-eyebrow mb-1.5">Hành động khắc phục</p>
          <div class="rich-text text-sm text-slate-700" v-html="sanitizeHtml(capa.corrective_action) || '—'" />
        </div>
        <div>
          <p class="t-eyebrow mb-1.5">Hành động phòng ngừa</p>
          <div class="rich-text text-sm text-slate-700" v-html="sanitizeHtml(capa.preventive_action) || '—'" />
        </div>
        <div>
          <p class="t-eyebrow mb-1.5">Xác minh hiệu quả</p>
          <p class="text-sm text-slate-700">
            {{ capa.effectiveness_check ? translateStatus(capa.effectiveness_check) : '— (chưa xác minh)' }}
          </p>
        </div>
        <div>
          <p class="t-eyebrow mb-1.5">Ghi chú xác minh</p>
          <p class="text-sm text-slate-700 whitespace-pre-line">{{ capa.verification_notes || '—' }}</p>
        </div>
      </div>

      <!-- BUG-16-08: audit trail -->
      <RecordHistory ref="historyRef" ref-doctype="IMM CAPA Record" :ref-name="capa.name" />
    </template>

    <!-- Edit modal -->
    <BaseModal v-if="showEdit" title="Sửa nội dung CAPA" size="lg" @close="showEdit = false">
      <div class="space-y-3">
        <div class="form-group">
          <label class="form-label">Mô tả</label>
          <textarea v-model="editForm.description" rows="2" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Phương pháp phân tích gốc rễ</label>
          <select v-model="editForm.imm_root_cause_method" class="form-select">
            <option value="">— Chọn —</option>
            <option v-for="m in RCA_METHODS" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Phân tích nguyên nhân gốc</label>
          <textarea v-model="editForm.root_cause" rows="3" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Hành động khắc phục</label>
          <textarea v-model="editForm.corrective_action" rows="3" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Hành động phòng ngừa</label>
          <textarea v-model="editForm.preventive_action" rows="3" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Ghi chú xác minh</label>
          <textarea v-model="editForm.verification_notes" rows="2" class="form-input" />
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showEdit = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="saveEdit">Lưu</button>
      </template>
    </BaseModal>

    <!-- Transition modal -->
    <BaseModal v-if="showTransition && pendingTransition" :title="pendingTransition.label" size="md" @close="showTransition = false">
      <div class="space-y-3">
        <p class="text-sm text-slate-600">Chuyển CAPA sang trạng thái <strong>{{ capaWorkflowLabel(pendingTransition.target) }}</strong>.</p>
        <template v-if="pendingTransition.target === 'Action Plan'">
          <div class="form-group">
            <label class="form-label">Phương pháp phân tích gốc (VR-05) *</label>
            <select v-model="transitionPayload.imm_root_cause_method" class="form-select">
              <option v-for="m in RCA_METHODS" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Hạn xử lý (VR-12: phải sau hôm nay) *</label>
            <input v-model="transitionPayload.due_date" type="date" class="form-input" />
          </div>
        </template>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showTransition = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="confirmTransition">{{ pendingTransition.label }}</button>
      </template>
    </BaseModal>

    <!-- Effectiveness modal -->
    <BaseModal v-if="showEffectiveness" title="Xác minh hiệu quả CAPA" size="md" @close="showEffectiveness = false">
      <div class="space-y-3">
        <div class="form-group">
          <label class="form-label">Kết quả *</label>
          <select v-model="effResult" class="form-select">
            <option value="Effective">Hiệu quả (→ Đóng CAPA)</option>
            <option value="Partially Effective">Hiệu quả một phần (→ Mở lại)</option>
            <option value="Not Effective">Không hiệu quả (→ Mở lại)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Bằng chứng</label>
          <input v-model="effEvidence" class="form-input" placeholder="/files/evidence-...pdf" />
        </div>
        <p class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2" role="alert" aria-live="polite">
          VR-07: chỉ "Hiệu quả" mới đóng được CAPA. Khác → tăng số lần mở lại + về "Mở lại".
        </p>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showEffectiveness = false">Huỷ</button>
        <button
          class="btn-primary"
          :disabled="api.loading.value"
          :title="effResult === 'Effective' ? 'Xác nhận hiệu quả và đóng CAPA' : 'Kết quả khác \'Hiệu quả\' sẽ mở lại CAPA (không đóng)'"
          @click="submitEffectiveness"
        >{{ effResult === 'Effective' ? 'Xác nhận & Đóng CAPA' : 'Xác nhận (Mở lại)' }}</button>
      </template>
    </BaseModal>
  </div>
</template>
