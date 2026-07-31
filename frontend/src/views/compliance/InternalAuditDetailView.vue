<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Chi tiết Kiểm toán nội bộ — Start / Complete checklist / Close.
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import { getAudit } from '@/api/imm16'
import type { InternalAudit, ChecklistItemPayload, AuditChecklistItemRow } from '@/api/imm16'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import DetailLoadError from '@/components/common/DetailLoadError.vue'
import { loadErrorKind, toApiError, type DetailLoadKind } from '@/api/errors'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store = useImm16Store()
const api = useApi()

const audit = ref<InternalAudit | null>(null)
const loading = ref(false)
// '' = nạp OK; 'notfound' = mã kiểm toán không tồn tại (404); 'unknown' = lỗi khác.
const loadFailed = ref<'' | DetailLoadKind>('')
const loadErrMsg = ref('')
const activeTab = ref<'overview' | 'checklist' | 'report'>('overview')

// Mã kiểm toán sai / đã xoá ⇒ 404: trước đây load() không catch (ApiError ra
// console) VÀ template không có nhánh v-else ⇒ TRANG TRẮNG. Nay: empty-state chuẩn.
async function load() {
  loading.value = true
  loadFailed.value = ''
  try {
    audit.value = await getAudit(props.id)
    hydrateChecklist()
  } catch (e: unknown) {
    loadFailed.value = loadErrorKind(e)
    loadErrMsg.value = toApiError(e).message
    audit.value = null
  } finally { loading.value = false }
}

const leadAuditorDisplay = computed(() => {
  const a = audit.value as (InternalAudit & { lead_auditor_name?: string }) | null
  return a?.lead_auditor_name || a?.lead_auditor || '—'
})

// Nhãn loại kiểm toán (display-only) — value gửi BE giữ nguyên (GATE-1: KHÔNG leak enum EN).
const AUDIT_TYPE_LABELS: Record<string, string> = {
  Internal: 'Nội bộ',
  'Self-assessment': 'Tự đánh giá',
  Surveillance: 'Giám sát',
  External: 'Bên ngoài',
}
const auditTypeDisplay = computed(() =>
  audit.value ? (AUDIT_TYPE_LABELS[audit.value.audit_type] ?? audit.value.audit_type) : '',
)

// Server-driven CTA (GATE-8 / LL-FE-51): gate theo allowed_transitions BE derive +
// cờ capability server (can_operate/can_close). KHÔNG hardcode status === '...'.
const allowedTransitions = computed<string[]>(() => audit.value?.allowed_transitions ?? [])
const canStart = computed(
  () => allowedTransitions.value.includes('start') && audit.value?.can_operate === true,
)
const canChecklist = computed(() => allowedTransitions.value.includes('complete_checklist'))
const canClose = computed(
  () => allowedTransitions.value.includes('close') && audit.value?.can_close === true,
)

// Hint dẫn dắt khi không có CTA khả dụng ở pha đang thao tác (non-terminal) —
// vừa hướng luồng (In Progress → Báo cáo), vừa giải thích khi thiếu quyền.
const noActionHint = computed<string>(() => {
  const at = allowedTransitions.value
  if (at.includes('complete_checklist'))
    return 'Hoàn tất bảng kiểm để chuyển sang giai đoạn Báo cáo.'
  if (at.includes('close') && audit.value?.can_close !== true)
    return 'Bạn không có quyền đóng kiểm toán. Liên hệ quản trị hệ thống quản lý chất lượng để được cấp quyền phê duyệt.'
  if (at.includes('start') && audit.value?.can_operate !== true)
    return 'Bạn không có quyền bắt đầu kiểm toán. Liên hệ quản trị hệ thống quản lý chất lượng để được cấp quyền thao tác.'
  return ''
})
const showNoActionHint = computed(
  () => !canStart.value && !canClose.value && noActionHint.value !== '',
)

async function doStart() {
  if (!audit.value) return
  const res = await api.run(() => store.actionStartAudit(audit.value!.name), {
    successMessage: 'Đã bắt đầu kiểm toán',
  })
  if (res) await load()
}

// ── Verdict mapping SSoT (mirror BE _FINDING_STATUS_TO_RESULT, services/imm16.py) ──
// BE lưu FORWARD: finding_status → result. FE hydrate REVERSE: result → finding_status.
// `Non-Conforming` LOSSY (Minor|Major NC gộp) → surface 'Major NC' để reload KHÔNG hạ
// nhẹ một non-conformance. Verdict read-only đọc TRỰC TIẾP từ `result` (không lossy);
// reverse-map chỉ prime lại <select> khi còn sửa được. Keys select PHẢI khớp keys map BE.
const RESULT_TO_FINDING_STATUS: Record<string, ChecklistItemPayload['finding_status']> = {
  Conforming: 'Compliant',
  'Non-Conforming': 'Major NC',
  'Not Applicable': 'N/A',
}
// Nhãn VI cho verdict `result` persisted (GATE-1: KHÔNG leak enum EN ra UI).
const RESULT_LABELS: Record<string, string> = {
  Conforming: 'Phù hợp',
  'Non-Conforming': 'Không phù hợp',
  'Not Applicable': 'Không áp dụng',
}
function resultLabel(result?: string | null): string {
  return RESULT_LABELS[result ?? ''] ?? 'Chưa đánh giá'
}
function verdictPillClass(result?: string | null): string {
  if (result === 'Non-Conforming') return 'bg-red-50 text-red-700 ring-1 ring-red-200'
  if (result === 'Conforming') return 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
  return 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'
}

// Checklist items — local editor. Row = payload + field hiển thị (item_description /
// result đọc-lại từ server).
interface ChecklistRow extends ChecklistItemPayload {
  item_description?: string
  result?: string
}
const checklistItems = ref<ChecklistRow[]>([
  { idx: 1, finding_status: 'Compliant', notes: '', clause_ref: '' },
])

// CR-27b: mở audit ĐÃ nhập bảng kiểm → HYDRATE verdict đã lưu (reverse-map result →
// finding_status) thay vì luôn khởi tạo default 'Compliant'. Rỗng → giữ editor 1 dòng.
function hydrateChecklist() {
  const rows = audit.value?.checklist_items ?? []
  if (rows.length === 0) return
  checklistItems.value = rows.map((r, i) => ({
    idx: r.idx ?? i + 1,
    finding_status: RESULT_TO_FINDING_STATUS[r.result ?? ''] ?? 'Compliant',
    notes: r.notes ?? '',
    clause_ref: '',
    item_description: r.item_description ?? '',
    result: r.result ?? '',
  }))
}

// Verdict per-dòng ĐÃ lưu (read-only) — nhìn lại được sau khi Gửi (Reporting/Closed).
const persistedChecklist = computed<AuditChecklistItemRow[]>(
  () => audit.value?.checklist_items ?? [],
)
const hasPersistedChecklist = computed(() => persistedChecklist.value.length > 0)

function addChecklistRow() {
  checklistItems.value.push({ idx: checklistItems.value.length + 1, finding_status: 'Compliant', notes: '', clause_ref: '' })
}
function removeChecklistRow(i: number) {
  checklistItems.value.splice(i, 1)
  checklistItems.value.forEach((it, idx) => (it.idx = idx + 1))
}

async function submitChecklist() {
  if (!audit.value) return
  // Chỉ gửi đúng signature BE (idx/finding_status/notes/clause_ref) — bỏ field hiển thị.
  const payload: ChecklistItemPayload[] = checklistItems.value.map(
    ({ idx, finding_status, notes, clause_ref }) => ({ idx, finding_status, notes, clause_ref }),
  )
  const res = await api.run(() => store.actionCompleteChecklist(audit.value!.name, payload), {
    successMessage: 'Đã lưu bảng kiểm + sinh findings',
  })
  if (res) await load()
}

// Close
const showClose = ref(false)
const reportSummary = ref('')
async function doClose() {
  if (!audit.value) return
  const res = await api.run(() => store.actionCloseAudit(audit.value!.name, reportSummary.value), {
    successMessage: 'Đã đóng kiểm toán',
  })
  if (res) { showClose.value = false; reportSummary.value = ''; await load() }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div v-if="loading" class="p-6"><SkeletonLoader variant="form" :rows="6" /></div>

    <DetailLoadError
      v-else-if="!audit"
      :kind="loadFailed || 'notfound'"
      entity-label="cuộc kiểm toán nội bộ"
      :record-id="props.id"
      :message="loadErrMsg"
      back-label="Về danh sách kiểm toán"
      @retry="load()"
      @back="router.push('/compliance/audits')"
    />

    <template v-else>
      <PageHeader
        :back-to="'/compliance/audits'"
        :title="audit.audit_code"
        :subtitle="`IMM-16 · Theo dõi tuân thủ — ${auditTypeDisplay} · ${formatDate(audit.planned_start)} → ${formatDate(audit.planned_end)}`"
        :breadcrumb="[
          { label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' },
          { label: 'Kiểm toán', to: '/compliance/audits' },
          { label: audit.audit_code },
        ]"
      >
        <template #actions>
          <button v-if="canStart" data-testid="cta-start" class="btn-primary text-sm" @click="doStart">Bắt đầu kiểm toán</button>
          <button v-if="canClose" data-testid="cta-close" class="btn-secondary text-sm" @click="showClose = true">Đóng kiểm toán</button>
          <span v-if="showNoActionHint" data-testid="no-actions-hint" class="text-xs text-slate-500 italic max-w-xs text-right">
            {{ noActionHint }}
          </span>
        </template>
      </PageHeader>

      <!-- Summary card -->
      <div class="card p-5">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p class="t-eyebrow mb-1.5">Trạng thái</p>
            <StatusBadge :state="audit.status" />
          </div>
          <div>
            <p class="t-eyebrow mb-1.5">Trưởng đoàn</p>
            <p class="text-sm text-slate-800">{{ leadAuditorDisplay }}</p>
          </div>
          <div>
            <p class="t-eyebrow mb-1.5">Bắt đầu thực tế</p>
            <p class="text-sm text-slate-700">{{ formatDate(audit.actual_start) }}</p>
          </div>
          <div>
            <p class="t-eyebrow mb-1.5">Kết thúc thực tế</p>
            <p class="text-sm text-slate-700">{{ formatDate(audit.actual_end) }}</p>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="border-b border-slate-200">
        <nav class="-mb-px flex gap-6">
          <button
:class="['py-2 px-1 border-b-2 text-sm font-medium transition-colors',
            activeTab === 'overview' ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-700']"
            @click="activeTab = 'overview'">
            Tổng quan
          </button>
          <button
:class="['py-2 px-1 border-b-2 text-sm font-medium transition-colors',
            activeTab === 'checklist' ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-700']"
            @click="activeTab = 'checklist'">
            Bảng kiểm
          </button>
          <button
:class="['py-2 px-1 border-b-2 text-sm font-medium transition-colors',
            activeTab === 'report' ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-700']"
            @click="activeTab = 'report'">
            Báo cáo & Phát hiện
          </button>
        </nav>
      </div>

      <!-- Tab content -->
      <div v-if="activeTab === 'overview'" class="card p-5">
        <p class="text-sm text-slate-600">
          Tổng số phát hiện trong đợt kiểm toán: <strong>{{ audit.findings_count }}</strong>
        </p>
        <button
          class="mt-3 text-sm text-brand-600 hover:text-brand-700 font-medium hover:underline"
          @click="router.push({ path: '/compliance/findings', query: { audit: audit.name } })"
        >
          Xem các phát hiện liên quan →
        </button>
      </div>

      <div v-else-if="activeTab === 'checklist'" class="card p-5">
        <!-- Đang thực hiện → editor có thể sửa (hydrate verdict đã lưu nếu có) -->
        <div v-if="canChecklist" data-testid="checklist-editor">
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-slate-100">
              <thead>
                <tr>
                  <th class="table-header w-12">#</th>
                  <th class="table-header">Tham chiếu điều khoản</th>
                  <th class="table-header">Kết quả</th>
                  <th class="table-header">Ghi chú</th>
                  <th class="table-header w-16"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="(item, i) in checklistItems" :key="i">
                  <td class="table-cell font-mono text-xs text-brand-700">{{ item.idx }}</td>
                  <td class="table-cell">
                    <p v-if="item.item_description" class="text-xs text-slate-500 mb-1">{{ item.item_description }}</p>
                    <input
                      v-model="item.clause_ref"
                      :aria-label="`Tham chiếu điều khoản dòng ${item.idx}`"
                      class="form-input text-sm"
                      placeholder="ISO 13485 §7.5.6"
                    />
                  </td>
                  <td class="table-cell">
                    <select
                      v-model="item.finding_status"
                      :aria-label="`Kết quả đánh giá dòng ${item.idx}`"
                      class="form-select text-sm"
                    >
                      <option value="Compliant">Phù hợp</option>
                      <option value="Minor NC">Không phù hợp nhẹ</option>
                      <option value="Major NC">Không phù hợp nặng</option>
                      <option value="N/A">Không áp dụng</option>
                    </select>
                  </td>
                  <td class="table-cell">
                    <input v-model="item.notes" :aria-label="`Ghi chú dòng ${item.idx}`" class="form-input text-sm" />
                  </td>
                  <td class="table-cell text-right">
                    <button
                      class="text-xs text-red-600 hover:text-red-700 font-medium"
                      :disabled="checklistItems.length === 1"
                      @click="removeChecklistRow(i)"
                    >
Xoá
</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="flex justify-between mt-3">
            <button class="btn-secondary text-sm" @click="addChecklistRow">Thêm dòng</button>
            <button class="btn-primary text-sm" :disabled="api.loading.value" @click="submitChecklist">
              {{ api.loading.value ? 'Đang lưu…' : 'Hoàn tất bảng kiểm' }}
            </button>
          </div>
        </div>

        <!-- Đã Gửi (Reporting/Closed) → verdict per-dòng đã lưu, chỉ đọc (CR-27b UI) -->
        <div v-else-if="hasPersistedChecklist" data-testid="checklist-readonly">
          <p class="text-sm text-slate-600 mb-3">Kết quả bảng kiểm đã ghi nhận (chỉ đọc).</p>
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-slate-100">
              <thead>
                <tr>
                  <th class="table-header w-12">#</th>
                  <th class="table-header">Mục kiểm tra</th>
                  <th class="table-header">Kết quả</th>
                  <th class="table-header">Ghi chú</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="(item, i) in persistedChecklist" :key="i">
                  <td class="table-cell font-mono text-xs text-brand-700">{{ item.idx }}</td>
                  <td class="table-cell text-sm text-slate-700">{{ item.item_description || '—' }}</td>
                  <td class="table-cell">
                    <span
                      data-testid="readonly-verdict"
                      :class="verdictPillClass(item.result)"
                      class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                    >{{ resultLabel(item.result) }}</span>
                  </td>
                  <td class="table-cell text-sm text-slate-600">{{ item.notes || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Chưa nhập + không sửa được -->
        <div v-else class="text-sm text-slate-500 py-6 text-center">
          Bảng kiểm chỉ chỉnh sửa được khi kiểm toán ở trạng thái "Đang thực hiện".
          <span v-if="allowedTransitions.includes('start')">— Hãy nhấn "Bắt đầu" trước.</span>
        </div>
      </div>

      <div v-else-if="activeTab === 'report'" class="card p-5">
        <p class="text-sm text-slate-600 mb-3">Danh sách phát hiện sinh từ đợt kiểm toán này.</p>
        <button
          class="btn-secondary text-sm"
          @click="router.push({ path: '/compliance/findings', query: { audit: audit.name } })"
        >
          Mở danh sách phát hiện →
        </button>
      </div>
    </template>

    <BaseModal v-if="showClose" title="Đóng đợt kiểm toán" size="md" @close="showClose = false">
      <div class="form-group">
        <label class="form-label">Tóm tắt báo cáo</label>
        <textarea v-model="reportSummary" rows="5" class="form-input" />
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showClose = false">Huỷ</button>
        <button data-testid="cta-close-confirm" class="btn-primary" :disabled="api.loading.value" @click="doClose">
          {{ api.loading.value ? 'Đang đóng…' : 'Đóng kiểm toán' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
