<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team RCA Detail + 5-Why form
// GATE-8/LL-FE-51: CTA workflow SERVER-DRIVEN. Nút chuyển-trạng-thái gate theo
// `allowed_transitions` + `can_manage_rca` do BE get_rca emit (SSoT
// _RCA_VALID_TRANSITIONS trong services/imm12.py) — KHÔNG hardcode `rca.status === 'X'`.
// status CHỈ dùng cho badge/hiển thị (nhãn tiếng Việt qua rcaStatusLabel), KHÔNG gate action.
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getRca, submitRca, startRca, cancelRca } from '@/api/imm12'
import type { RCADetail } from '@/api/imm12'
import { toApiError } from '@/api/errors'
import { rcaStatusLabel, rcaStatusClass } from '@/constants/labels'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const name = computed(() => route.params.id as string)

const rca = ref<Partial<RCADetail>>({})
const loading = ref(false)
const saving = ref(false)
const starting = ref(false)
const cancelling = ref(false)
const err = ref('')

// Hủy RCA — modal thay window.confirm (lý do bắt buộc, audit ở BE).
const showCancel = ref(false)
const cancelReason = ref('')

const fiveWhy = ref<Array<{ why_number: number; why_question: string; why_answer: string }>>([])
const rootCause = ref('')
const correctiveAction = ref('')
const preventiveAction = ref('')
const rcaNotes = ref('')

// ─── Server-driven gating (GATE-8/LL-FE-51) ────────────────────────────────────
const allowedTransitions = computed<string[]>(() => rca.value.allowed_transitions ?? [])
const canManage = computed(() => !!rca.value.can_manage_rca)
// Đích hợp lệ (_RCA_VALID_TRANSITIONS): 'RCA Required'→['RCA In Progress','Cancelled'];
// 'RCA In Progress'→['Completed','Cancelled']; terminal (Completed/Cancelled)→[].
const canStart = computed(() => canManage.value && allowedTransitions.value.includes('RCA In Progress'))
const canComplete = computed(() => canManage.value && allowedTransitions.value.includes('Completed'))
const canCancel = computed(() => canManage.value && allowedTransitions.value.includes('Cancelled'))
// Terminal = không còn transition nào (đã hoàn thành hoặc đã hủy). Dùng cho form
// read-only + banner tĩnh — KHÔNG so status=== (status chỉ để hiển thị nhãn).
const isTerminal = computed(() => !loading.value && !!rca.value.status && allowedTransitions.value.length === 0)
// Form 5-Why/nguyên nhân chỉ nhập được khi có thể Hoàn thành (đang phân tích + đủ quyền).
const canEdit = computed(() => canComplete.value)

// ─── Lỗi FIELD-LEVEL từ envelope submit_rca (AC-CR-83) ─────────────────────────
// BE trả `fields = {<khoá field>: <câu tiếng Việt>}`; FE CHỈ ĐỌC và gắn câu đó vào
// ĐÚNG ô — KHÔNG tự dựng luật, KHÔNG dịch lại, KHÔNG in mã kỹ thuật.
// Khoá dùng TÊN THAM SỐ GHI (`corrective_action`), không phải tên field đọc
// (`corrective_action_summary`) — bất đối xứng đọc≠ghi, xem `api/imm12.ts`.
const fieldErrors = ref<Record<string, string>>({})

const _WHY_KEY_RE = /^five_why_steps\.(\d+)$/

/** `five_why_steps.<n>` → chỉ số bước; khoá khác → null. */
function whyKeyIndex(key: string): number | null {
  const m = _WHY_KEY_RE.exec(key)
  return m ? Number(m[1]) : null
}

/**
 * Ánh xạ khoá lỗi bước 5-Why → DÒNG đang render.
 * Ưu tiên khớp `why_number` (BE đánh số 1..5 theo nghiệp vụ); nếu không có dòng
 * nào mang số đó thì mới rơi về vị trí trong mảng — để không đánh rơi thông điệp.
 */
const whyErrorEntries = computed<Record<number, { key: string; message: string }>>(() => {
  const out: Record<number, { key: string; message: string }> = {}
  for (const [key, message] of Object.entries(fieldErrors.value)) {
    const idx = whyKeyIndex(key)
    if (idx === null) continue
    const row = fiveWhy.value.find(s => s.why_number === idx)
      ?? fiveWhy.value[idx - 1]
      ?? fiveWhy.value[idx]
    if (row) out[row.why_number] = { key, message }
  }
  return out
})

function whyError(n: number): string | undefined {
  return whyErrorEntries.value[n]?.message
}

const rootCauseError = computed(() => fieldErrors.value.root_cause)
const correctiveError = computed(() => fieldErrors.value.corrective_action)
const preventiveError = computed(() => fieldErrors.value.preventive_action)
const notesError = computed(() => fieldErrors.value.rca_notes)
/** Lỗi cả khối 5-Why (thiếu/thừa bước) — không gắn được vào 1 dòng cụ thể. */
const fiveWhyBlockError = computed(() => fieldErrors.value.five_why_steps)
/** Hồ sơ chưa phân công người phụ trách → banner (không có ô nhập trên màn này). */
const assigneeError = computed(() => fieldErrors.value.assigned_to)

const _MAPPED_KEYS = new Set([
  'root_cause', 'corrective_action', 'preventive_action', 'rca_notes',
  'assigned_to', 'five_why_steps',
])

/**
 * Khoá BE gửi mà màn này chưa có ô tương ứng → vẫn PHẢI hiện (banner gom).
 * Nuốt im lặng = người dùng bấm mãi không hiểu vì sao không gửi được.
 */
const unmappedFieldErrors = computed<string[]>(() =>
  Object.entries(fieldErrors.value)
    .filter(([k]) => !_MAPPED_KEYS.has(k) && whyKeyIndex(k) === null)
    .map(([, v]) => v),
)

const hasFieldErrors = computed(() => Object.keys(fieldErrors.value).length > 0)

function clearFieldError(key: string): void {
  if (key in fieldErrors.value) delete fieldErrors.value[key]
}

/** Người dùng sửa 1 ô Why → xoá lỗi của chính dòng đó + lỗi cả khối. */
function onWhyAnswerInput(n: number): void {
  const entry = whyErrorEntries.value[n]
  if (entry) clearFieldError(entry.key)
  clearFieldError('five_why_steps')
}

// ─── Pre-gate client — MIRROR predicate BE, KHÔNG phải luật thứ hai ─────────────
// Cùng 1 ràng buộc `services/imm12.py::validate_five_why_payload`: phương pháp có
// chứa 'why' ⇒ MỖI bước phải đủ CẢ câu hỏi VÀ câu trả lời. Chỉ để tránh 1 vòng
// round-trip vô ích + nói trước lý do; SERVER vẫn là SSoT: phương pháp KHÁC 5-Why
// (hoặc BE đổi luật) ⇒ nút vẫn bấm được và lỗi server vẫn hiển thị đúng ô.
const isFiveWhyMethod = computed(() => (rca.value.rca_method ?? '').toLowerCase().includes('why'))
const missingWhyNumbers = computed<number[]>(() =>
  isFiveWhyMethod.value
    ? fiveWhy.value
      .filter(s => !s.why_question.trim() || !s.why_answer.trim())
      .map(s => s.why_number)
    : [],
)

/** Lý do tiếng Việt khiến nút «Hoàn thành» đang tắt — rỗng nghĩa là bấm được. */
const completeBlockedReason = computed<string>(() => {
  if (!rootCause.value.trim()) return 'Cần nhập Nguyên nhân gốc trước khi hoàn thành.'
  if (!correctiveAction.value.trim()) return 'Cần nhập Hành động khắc phục trước khi hoàn thành.'
  if (missingWhyNumbers.value.length) {
    return `Còn ${missingWhyNumbers.value.length} bước chưa điền đủ câu hỏi/câu trả lời `
      + `(Why ${missingWhyNumbers.value.join(', ')}).`
  }
  return ''
})

async function load() {
  loading.value = true
  err.value = ''
  fieldErrors.value = {}
  try {
    const res = await getRca(name.value)
    rca.value = res
    const steps = res.five_why_steps ?? []
    fiveWhy.value = steps.length
      ? steps.map(s => ({ why_number: s.why_number, why_question: s.why_question, why_answer: s.why_answer || '' }))
      : Array.from({ length: 5 }, (_, i) => ({ why_number: i + 1, why_question: `Why ${i + 1}?`, why_answer: '' }))
    rootCause.value = res.root_cause || ''
    correctiveAction.value = res.corrective_action_summary || ''
    preventiveAction.value = res.preventive_action_summary || ''
    rcaNotes.value = res.rca_notes || ''
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Không tải được phân tích nguyên nhân gốc'
  } finally { loading.value = false }
}

async function doStart() {
  starting.value = true
  err.value = ''
  try {
    await startRca(name.value)
    toast.success('Đã bắt đầu phân tích nguyên nhân gốc')
    await load()
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Không thể bắt đầu phân tích nguyên nhân gốc'
  } finally { starting.value = false }
}

function openCancel() {
  cancelReason.value = ''
  err.value = ''
  showCancel.value = true
}

async function doCancel() {
  if (!cancelReason.value.trim()) {
    err.value = 'Vui lòng nhập lý do hủy phân tích nguyên nhân gốc'
    return
  }
  cancelling.value = true
  err.value = ''
  try {
    await cancelRca(name.value, cancelReason.value)
    showCancel.value = false
    toast.success('Đã hủy phân tích nguyên nhân gốc')
    await load()
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Không thể hủy phân tích nguyên nhân gốc'
  } finally { cancelling.value = false }
}

async function submit() {
  // Pre-gate client (mirror BE): gắn ngay vào ĐÚNG ô, không banner chung chung.
  const pre: Record<string, string> = {}
  if (!rootCause.value.trim()) pre.root_cause = 'Vui lòng nhập nguyên nhân gốc.'
  if (!correctiveAction.value.trim()) pre.corrective_action = 'Vui lòng nhập hành động khắc phục.'
  for (const n of missingWhyNumbers.value) {
    pre[`five_why_steps.${n}`] = `Bước ${n}: vui lòng điền đủ câu hỏi và câu trả lời.`
  }
  if (Object.keys(pre).length) {
    fieldErrors.value = pre
    err.value = ''
    return
  }
  saving.value = true
  err.value = ''
  fieldErrors.value = {}
  try {
    await submitRca({
      name: name.value,
      root_cause: rootCause.value,
      corrective_action: correctiveAction.value,
      preventive_action: preventiveAction.value,
      five_why_steps: fiveWhy.value,
      rca_notes: rcaNotes.value,
    })
    toast.success('Đã hoàn thành phân tích nguyên nhân gốc và tạo hành động khắc phục/phòng ngừa')
    await load()
  } catch (e: unknown) {
    // SERVER là SSoT: có `fields` ⇒ hiển thị TỪNG Ô (không nhân đôi banner);
    // không có ⇒ giữ nhánh thông điệp chung như cũ. Chỉ đọc message đã curate ở
    // BE — KHÔNG bao giờ echo traceback/_server_messages thô.
    const apiErr = toApiError(e)
    const fields = apiErr.fields
    if (fields && Object.keys(fields).length) {
      fieldErrors.value = { ...fields }
      err.value = ''
    } else {
      fieldErrors.value = {}
      err.value = apiErr.message || 'Lỗi khi gửi phân tích nguyên nhân gốc'
    }
  } finally { saving.value = false }
}

function useLastWhyAsRoot() {
  const last = [...fiveWhy.value].reverse().find(s => s.why_answer.trim())
  if (last) rootCause.value = last.why_answer
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-start justify-between flex-wrap gap-3">
      <div>
        <button class="text-sm text-slate-500 hover:text-slate-700 mb-1 focus-visible:ring-2 focus-visible:ring-emerald-500 rounded" @click="router.push(rca?.incident_report ? `/incidents/${rca.incident_report}` : '/incidents/list')">← Quay lại</button>
        <h1 class="text-xl font-semibold text-slate-800">{{ name }}</h1>
        <div class="flex items-center gap-2 mt-1">
          <span data-testid="rca-status-badge" :class="['text-xs px-2 py-0.5 rounded', rcaStatusClass(rca.status ?? '')]">{{ rcaStatusLabel(rca.status ?? '') }}</span>
          <span v-if="rca.rca_method" class="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700">{{ rca.rca_method }}</span>
          <button v-if="rca.incident_report" class="text-xs text-blue-600 hover:underline font-mono focus-visible:ring-2 focus-visible:ring-emerald-500 rounded" @click="router.push(`/incidents/${rca.incident_report}`)">
            ← {{ rca.incident_report }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="err" role="alert" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ err }}</div>

    <!-- Tóm tắt lỗi field-level: chỉ dẫn hướng, câu chi tiết nằm ngay dưới từng ô -->
    <div
      v-if="hasFieldErrors"
      data-testid="rca-field-error-summary"
      role="alert"
      class="bg-amber-50 text-amber-800 p-3 rounded-lg text-sm space-y-1">
      <p>Chưa gửi được hồ sơ phân tích nguyên nhân gốc. Vui lòng kiểm tra các ô được đánh dấu bên dưới.</p>
      <p v-if="assigneeError" data-testid="rca-error-assigned-to" class="font-medium">{{ assigneeError }}</p>
      <p v-for="(msg, i) in unmappedFieldErrors" :key="`unmapped-${i}`" data-testid="rca-error-unmapped">{{ msg }}</p>
    </div>

    <div v-if="loading" class="text-center text-slate-400 py-12">Đang tải...</div>

    <div v-else class="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
      <div class="p-6">
        <div class="text-sm font-semibold text-slate-800 mb-3">Phân tích 5-Why</div>
        <p
          v-if="fiveWhyBlockError"
          data-testid="rca-error-five-why-steps"
          role="alert"
          class="mb-3 text-sm text-red-600">
{{ fiveWhyBlockError }}
</p>
        <div class="space-y-3">
          <div v-for="step in fiveWhy" :key="step.why_number" class="grid grid-cols-12 gap-2 items-start">
            <div class="col-span-1 pt-2 text-center text-sm font-mono text-indigo-600">#{{ step.why_number }}</div>
            <div class="col-span-4">
              <label :for="`why-q-${step.why_number}`" class="sr-only">Câu hỏi Why {{ step.why_number }}</label>
              <textarea
:id="`why-q-${step.why_number}`" v-model="step.why_question" :disabled="!canEdit" rows="2"
                class="w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm disabled:bg-slate-50"
                placeholder="Câu hỏi Why..."></textarea>
            </div>
            <div class="col-span-7">
              <label :for="`why-a-${step.why_number}`" class="sr-only">Câu trả lời Why {{ step.why_number }}</label>
              <textarea
:id="`why-a-${step.why_number}`" v-model="step.why_answer" :disabled="!canEdit" rows="2"
                :aria-invalid="whyError(step.why_number) ? 'true' : undefined"
                :aria-describedby="whyError(step.why_number) ? `why-a-err-${step.why_number}` : undefined"
                :class="['w-full border rounded-lg px-2 py-1.5 text-sm disabled:bg-slate-50',
                         whyError(step.why_number) ? 'border-red-400' : 'border-slate-300']"
                placeholder="Câu trả lời Why..."
                @input="onWhyAnswerInput(step.why_number)"></textarea>
              <p
                v-if="whyError(step.why_number)"
                :id="`why-a-err-${step.why_number}`"
                :data-testid="`rca-error-why-${step.why_number}`"
                role="alert"
                class="mt-1 text-xs text-red-600">
{{ whyError(step.why_number) }}
</p>
            </div>
          </div>
        </div>
        <button v-if="canEdit" class="mt-3 text-xs text-indigo-600 hover:underline focus-visible:ring-2 focus-visible:ring-emerald-500 rounded" @click="useLastWhyAsRoot">
          → Dùng câu trả lời cuối làm nguyên nhân gốc
        </button>
      </div>

      <div class="p-6 space-y-4">
        <div>
          <label for="rca-root-cause" class="block text-sm font-medium text-slate-700 mb-1">Nguyên nhân gốc <span class="text-red-500">*</span></label>
          <textarea
id="rca-root-cause" v-model="rootCause" :disabled="!canEdit" rows="2"
            :aria-invalid="rootCauseError ? 'true' : undefined"
            :aria-describedby="rootCauseError ? 'rca-root-cause-err' : undefined"
            :class="['w-full border rounded-lg px-3 py-2 text-sm disabled:bg-slate-50',
                     rootCauseError ? 'border-red-400' : 'border-slate-300']"
            placeholder="Nguyên nhân gốc rễ xác định được..."
            @input="clearFieldError('root_cause')"></textarea>
          <p
            v-if="rootCauseError" id="rca-root-cause-err" data-testid="rca-error-root-cause"
            role="alert" class="mt-1 text-xs text-red-600">
{{ rootCauseError }}
</p>
        </div>
        <div>
          <label for="rca-corrective" class="block text-sm font-medium text-slate-700 mb-1">Hành động khắc phục <span class="text-red-500">*</span></label>
          <textarea
id="rca-corrective" v-model="correctiveAction" :disabled="!canEdit" rows="3"
            :aria-invalid="correctiveError ? 'true' : undefined"
            :aria-describedby="correctiveError ? 'rca-corrective-err' : undefined"
            :class="['w-full border rounded-lg px-3 py-2 text-sm disabled:bg-slate-50',
                     correctiveError ? 'border-red-400' : 'border-slate-300']"
            placeholder="Hành động khắc phục cụ thể..."
            @input="clearFieldError('corrective_action')"></textarea>
          <p
            v-if="correctiveError" id="rca-corrective-err" data-testid="rca-error-corrective-action"
            role="alert" class="mt-1 text-xs text-red-600">
{{ correctiveError }}
</p>
        </div>
        <div>
          <label for="rca-preventive" class="block text-sm font-medium text-slate-700 mb-1">Hành động phòng ngừa</label>
          <textarea
id="rca-preventive" v-model="preventiveAction" :disabled="!canEdit" rows="3"
            :aria-invalid="preventiveError ? 'true' : undefined"
            :aria-describedby="preventiveError ? 'rca-preventive-err' : undefined"
            :class="['w-full border rounded-lg px-3 py-2 text-sm disabled:bg-slate-50',
                     preventiveError ? 'border-red-400' : 'border-slate-300']"
            placeholder="Hành động phòng ngừa tái diễn..."
            @input="clearFieldError('preventive_action')"></textarea>
          <p
            v-if="preventiveError" id="rca-preventive-err" data-testid="rca-error-preventive-action"
            role="alert" class="mt-1 text-xs text-red-600">
{{ preventiveError }}
</p>
        </div>
        <div>
          <label for="rca-notes" class="block text-sm font-medium text-slate-700 mb-1">Ghi chú</label>
          <textarea
id="rca-notes" v-model="rcaNotes" :disabled="!canEdit" rows="2"
            :aria-invalid="notesError ? 'true' : undefined"
            :aria-describedby="notesError ? 'rca-notes-err' : undefined"
            :class="['w-full border rounded-lg px-3 py-2 text-sm disabled:bg-slate-50',
                     notesError ? 'border-red-400' : 'border-slate-300']"
            @input="clearFieldError('rca_notes')"></textarea>
          <p
            v-if="notesError" id="rca-notes-err" data-testid="rca-error-rca-notes"
            role="alert" class="mt-1 text-xs text-red-600">
{{ notesError }}
</p>
        </div>
      </div>

      <div v-if="rca.linked_capa" class="p-6 flex items-center gap-2 text-sm">
        <span class="text-slate-500">Hành động khắc phục/phòng ngừa liên kết:</span>
        <button class="text-purple-600 hover:underline font-mono focus-visible:ring-2 focus-visible:ring-emerald-500 rounded" @click="router.push(`/capas/${rca.linked_capa}`)">{{ rca.linked_capa }}</button>
      </div>

      <!-- CTA server-driven: chỉ render đích ∈ allowed_transitions ∧ can_manage_rca -->
      <div v-if="canStart || canComplete || canCancel" class="p-6 flex flex-wrap items-center justify-end gap-2">
        <p
          v-if="canComplete && completeBlockedReason"
          id="rca-complete-blocked-hint"
          data-testid="rca-complete-blocked-hint"
          role="status"
          class="mr-auto text-xs text-slate-500">
{{ completeBlockedReason }}
</p>
        <button
          v-if="canCancel"
          data-testid="cta-cancel-rca"
          :disabled="cancelling"
          class="btn-secondary focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="openCancel">
          Hủy RCA
        </button>
        <button
          v-if="canStart"
          data-testid="cta-start-rca"
          :disabled="starting"
          class="btn-primary focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="doStart">
          {{ starting ? 'Đang bắt đầu...' : 'Bắt đầu phân tích RCA' }}
        </button>
        <button
          v-if="canComplete"
          data-testid="cta-complete-rca"
          :disabled="saving || !!completeBlockedReason"
          :title="completeBlockedReason || undefined"
          :aria-describedby="completeBlockedReason ? 'rca-complete-blocked-hint' : undefined"
          class="btn-primary focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="submit">
          {{ saving ? 'Đang gửi...' : 'Hoàn thành RCA' }}
        </button>
      </div>
      <div v-else-if="isTerminal" class="p-6">
        <div
          data-testid="rca-terminal-banner"
          :class="['rounded-lg p-3 text-sm', rca.completed_date ? 'alert-success' : 'bg-slate-50 text-slate-600']">
          Phân tích nguyên nhân gốc: {{ rcaStatusLabel(rca.status ?? '') }}<span v-if="rca.completed_date"> (hoàn thành ngày {{ rca.completed_date }})</span>
        </div>
      </div>
      <div v-else class="p-6 text-sm text-slate-400">
        Không có hành động khả dụng cho vai trò hiện tại
      </div>
    </div>

    <BaseModal v-if="showCancel" title="Hủy phân tích nguyên nhân gốc" size="md" danger @close="showCancel = false">
      <div class="space-y-3">
        <p class="text-sm text-slate-600">Nhập lý do hủy. Hành động này được ghi vào nhật ký hệ thống và không thể hoàn tác.</p>
        <div>
          <label for="rca-cancel-reason" class="block text-sm font-medium text-slate-700 mb-1">Lý do hủy <span class="text-red-500">*</span></label>
          <textarea
            id="rca-cancel-reason" v-model="cancelReason" rows="3"
            class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-emerald-500"
            placeholder="Lý do hủy phân tích nguyên nhân gốc..."></textarea>
        </div>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="showCancel = false">Đóng</button>
        <button
          data-testid="cta-cancel-rca-confirm"
          :disabled="cancelling || !cancelReason.trim()"
          class="btn-danger focus-visible:ring-2 focus-visible:ring-red-500"
          @click="doCancel">
          {{ cancelling ? 'Đang hủy...' : 'Xác nhận hủy' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
