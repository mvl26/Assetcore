<script setup lang="ts">
import { ref, computed } from 'vue'
import type { CommissioningDoc } from '@/types/imm04'
import { approvePending, type GateStatus } from '@/api/imm04'
import { useAuthStore } from '@/stores/auth'
import ApproverSelect from './ApproverSelect.vue'
import SubmitForApprovalModal from './SubmitForApprovalModal.vue'
import { resolveG04Applicable, g04StatusLabel, g04Description } from './g04Gate'

// ─── Props & Emits ────────────────────────────────────────────────────────────

const props = defineProps<{
  doc: CommissioningDoc
  gateStatus: GateStatus
  saving: boolean
  /**
   * CR-76 — thông báo tiếng Việt khi KHÔNG tải được trạng thái cổng (vd người
   * dùng không có quyền đọc phiếu: backend trả 403 trong envelope trên HTTP-200).
   * Có giá trị ⇒ hiện thông báo thay cho danh sách cổng, KHÔNG vẽ 6 thẻ đỏ giả.
   */
  gateError?: string | null
}>()

const emit = defineEmits<{
  (e: 'transition', action: string): void
  (e: 'update-field', field: string, value: unknown): void
  (e: 'refresh'): void
}>()

// ─── Auth ─────────────────────────────────────────────────────────────────────

const auth = useAuthStore()
const currentUser = computed(() => auth.user?.email ?? '')

// ─── Submit-for-approval state ────────────────────────────────────────────────

const SUBMITTABLE_STATES = new Set([
  'Draft', 'Pending Doc Verify', 'To Be Installed', 'Installing',
  'Identification', 'Initial Inspection', 'Clinical Hold', 'Re Inspection',
])

const canSubmitForApproval = computed(() =>
  !props.doc.pending_approver && SUBMITTABLE_STATES.has(props.doc.workflow_state),
)

const isPendingForMe = computed(() =>
  props.doc.pending_approver && props.doc.pending_approver === currentUser.value,
)

const isPendingForOthers = computed(() =>
  props.doc.pending_approver && props.doc.pending_approver !== currentUser.value,
)

const showSubmitModal = ref(false)
const decisionRemarks = ref('')
const decisionSaving  = ref(false)
const decisionError   = ref('')

async function handleDecision(decision: 'Approve' | 'Reject') {
  if (decision === 'Reject' && !decisionRemarks.value.trim()) {
    decisionError.value = 'Phải nhập lý do khi từ chối'
    return
  }
  decisionSaving.value = true
  decisionError.value = ''
  try {
    await approvePending(props.doc.name, decision, decisionRemarks.value)
    decisionRemarks.value = ''
    emit('refresh')
  } catch (e: unknown) {
    decisionError.value = e instanceof Error ? e.message : String(e)
  } finally {
    decisionSaving.value = false
  }
}

function formatDt(s: string): string {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  return d.toLocaleString('vi-VN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// Inline approve form đã gỡ: endpoint approve_clinical_release chỉ hợp lệ khi
// phiếu ĐÃ ở 'Clinical Release' (state docstatus=1, không còn transition), nên
// form này không bao giờ tới được. Approve clinical release giờ là workflow
// transition 'Phê duyệt phát hành' / 'Phê duyệt sau tái kiểm' / 'Gỡ giữ lâm sàng'
// đi qua transition_state với đúng chuỗi action khớp workflow JSON.

// ─── Conditional approver field visibility ────────────────────────────────────

const showQaOfficer = computed(() =>
  props.doc.is_radiation_device === 1 ||
  ['C', 'D', 'Radiation'].includes(props.doc.risk_class ?? '')
)

// ─── Gate helper ─────────────────────────────────────────────────────────────

// CR-76 — thẻ cổng phải NÓI ĐÚNG cổng thật. Ngữ nghĩa của mỗi khoá là
// BLOCKING-PARITY: `true` = cổng KHÔNG chặn phát hành lâm sàng (predicate chặn ở
// `services/imm04.py` cho phiếu này đi qua), KHÔNG có nghĩa "đã hoàn tất mọi việc".
// Vì vậy mô tả từng cổng được sinh THEO TRẠNG THÁI THẬT, không phải câu cố định.

/** Các khoá cổng hiển thị — `g01_waived`/`g04_applicable` là khoá phụ, không phải thẻ riêng. */
type GateKey = Exclude<keyof GateStatus, 'g01_waived' | 'g04_applicable'>

interface Gate {
  key: GateKey
  label: string
  /** Cổng này có enforcement chặn phát hành ở backend hay không. */
  blocking: boolean
  na: boolean // whether N/A concept applies (radiation)
}

const GATES: Gate[] = [
  { key: 'g01_docs',      label: 'Hồ sơ đi kèm',                 blocking: true,  na: false },
  { key: 'g02_facility',  label: 'Cơ sở hạ tầng',                blocking: false, na: false },
  { key: 'g03_baseline',  label: 'Đo kiểm nền (an toàn điện)',   blocking: true,  na: false },
  { key: 'g04_radiation', label: 'Bức xạ / Giấy phép',           blocking: true,  na: true  },
  { key: 'g05_nc',        label: 'Không có sự không phù hợp mở', blocking: true,  na: false },
  { key: 'g06_approver',  label: 'Người phê duyệt BGĐ',          blocking: true,  na: false },
]

/**
 * AC-CR-85 — cổng G04 có áp dụng không: đọc THẲNG khoá `g04_applicable` của
 * `getGateStatus` (chính predicate `gate_g04_applies` mà VR-07 dùng để chặn),
 * KHÔNG suy từ nguồn thứ hai `doc.is_radiation_device` nữa. Khoá vắng (backend
 * cũ) ⇒ rơi về đúng hành vi cũ.
 */
const g04Applicable = computed(() => resolveG04Applicable(props.gateStatus, props.doc))

// Cổng chỉ áp dụng cho thiết bị bức xạ (G04) → "Không áp dụng" với thiết bị thường.
function isGateNa(gate: Gate): boolean {
  return gate.na && !g04Applicable.value
}

function gateValue(gate: Gate): boolean {
  return Boolean(props.gateStatus[gate.key])
}

/** Nội dung giải trình thiếu hồ sơ (nếu phiếu có) — dùng cho chú thích cổng G01. */
const g01WaiverNote = computed(() => (props.doc.documents_incomplete_note ?? '').trim())

/** Sự kiện trên PHIẾU: đã đánh dấu thiếu hồ sơ + có ghi chú giải trình. */
const g01WaiverOnDoc = computed(
  () => Boolean(props.doc.documents_incomplete) && Boolean(g01WaiverNote.value),
)

/**
 * G01 qua được NHỜ giải trình thiếu hồ sơ (không phải vì đã đủ hồ sơ).
 * Ưu tiên khoá `g01_waived` của backend; nếu backend chưa nạp phiên bản mới
 * (khoá vắng mặt) thì suy ra từ chính phiếu.
 */
const isG01Waived = computed<boolean>(() => {
  if (props.gateStatus.g01_waived !== undefined) return Boolean(props.gateStatus.g01_waived)
  return g01WaiverOnDoc.value
})

/** Nhãn trạng thái ngắn đặt cạnh tên cổng (rỗng = không cần nhãn riêng). */
function gateStateChip(gate: Gate): string {
  // G04 nói đủ 3 trạng thái: không áp dụng / đã có giấy phép / chưa có giấy phép.
  if (gate.key === 'g04_radiation') {
    return g04StatusLabel(g04Applicable.value, gateValue(gate))
  }
  if (isGateNa(gate)) return 'Không áp dụng'
  if (!gate.blocking) return 'Tham khảo'
  if (gate.key === 'g01_docs' && gateValue(gate) && isG01Waived.value) {
    return 'Đạt — có giải trình thiếu hồ sơ'
  }
  return ''
}

function gateChipClass(gate: Gate): string {
  if (isGateNa(gate)) return 'bg-slate-100 text-slate-500'
  if (gate.key === 'g04_radiation') {
    return gateValue(gate) ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
  }
  if (!gate.blocking) return 'bg-sky-100 text-sky-700'
  return 'bg-amber-100 text-amber-800'
}

/** Mô tả đúng trạng thái thật của cổng (không khẳng định điều chưa xảy ra). */
function gateDescription(gate: Gate): string {
  // G04 — nguồn duy nhất là `g04_applicable` (AC-CR-85), gồm cả câu «không áp dụng».
  if (gate.key === 'g04_radiation') {
    return g04Description(g04Applicable.value, gateValue(gate))
  }
  if (isGateNa(gate)) return 'Thiết bị không phát bức xạ nên cổng này không áp dụng.'
  const passed = gateValue(gate)
  switch (gate.key) {
    case 'g01_docs':
      if (passed && isG01Waived.value) {
        return 'Vẫn còn hồ sơ bắt buộc chưa xác nhận, nhưng đã có giải trình được ghi nhận '
          + 'nên cổng này không chặn phát hành.'
      }
      if (passed) return 'Không còn hồ sơ bắt buộc nào chưa được xác nhận.'
      // Phiếu ĐÃ có giải trình mà cổng vẫn báo chặn ⇒ nói đúng hiện trạng, KHÔNG
      // khẳng định oan "chưa có giải trình".
      return g01WaiverOnDoc.value
        ? 'Còn hồ sơ bắt buộc chưa xác nhận. Đã có giải trình trên phiếu nhưng hệ thống vẫn ghi nhận cổng này đang chặn phát hành.'
        : 'Còn hồ sơ bắt buộc chưa xác nhận và chưa có giải trình — cổng này đang chặn phát hành.'
    case 'g02_facility':
      return passed
        ? 'Đã ghi nhận kiểm tra cơ sở hạ tầng đạt yêu cầu. Cổng tham khảo — không chặn phát hành lâm sàng.'
        : 'Chưa ghi nhận kết quả kiểm tra cơ sở hạ tầng. Cổng tham khảo — không chặn phát hành lâm sàng.'
    case 'g03_baseline':
      return passed
        ? 'Mọi phép đo nền đều Đạt hoặc Không áp dụng.'
        : 'Còn phép đo nền chưa đạt, hoặc phiếu chưa có phép đo nào — cổng này đang chặn phát hành.'
    case 'g05_nc':
      return passed
        ? 'Không còn phiếu không phù hợp nào đang mở.'
        : 'Còn phiếu không phù hợp đang mở — cổng này đang chặn phát hành.'
    case 'g06_approver':
      return passed
        ? 'Đã chỉ định người phê duyệt Ban Giám đốc.'
        : 'Chưa chỉ định người phê duyệt Ban Giám đốc — cổng này đang chặn phát hành.'
    default:
      return ''
  }
}

/** Chỉ các cổng CÓ enforcement mới quyết định "còn chặn phát hành hay không". */
const blockingGatesPassed = computed(() =>
  GATES.filter(g => g.blocking && !isGateNa(g)).every(g => gateValue(g)),
)

// ─── Transition label & color map ─────────────────────────────────────────────

// Actions that move the record into Clinical Release. Phải khớp EXACT với
// `action` trong IMM-04 Workflow JSON (lệch chuỗi → 422 Not a valid Workflow Action).
const APPROVE_ACTIONS = [
  'Phê duyệt phát hành',
  'Phê duyệt sau tái kiểm',
  'Gỡ giữ lâm sàng',
]

function isApproveAction(action: string): boolean {
  return APPROVE_ACTIONS.includes(action)
}

// Label map — keys = action chính xác trong workflow JSON. Value = nhãn hiển thị.
function actionLabel(action: string): string {
  const MAP: Record<string, string> = {
    'Gửi kiểm tra tài liệu':       'Gửi kiểm tra tài liệu',
    'Xác nhận đủ tài liệu':        'Xác nhận đủ tài liệu',
    'Yêu cầu bổ sung tài liệu':    'Yêu cầu bổ sung tài liệu',
    'Bắt đầu lắp đặt':             'Bắt đầu lắp đặt',
    'Báo cáo sự cố':               'Báo cáo sự cố',
    'Lắp đặt hoàn thành':          'Lắp đặt hoàn thành',
    'Báo cáo DOA':                 'Báo cáo hỏng khi nhận',
    'Bắt đầu kiểm tra':            'Bắt đầu kiểm tra',
    'Phê duyệt phát hành':         'Phê duyệt phát hành',
    'Giữ lâm sàng':                'Giữ lâm sàng',
    'Báo cáo lỗi baseline':        'Báo cáo lỗi baseline',
    'Gỡ giữ lâm sàng':             'Gỡ giữ lâm sàng',
    'Phê duyệt sau tái kiểm':      'Phê duyệt sau tái kiểm',
    'Khắc phục xong':              'Khắc phục xong',
    'Trả lại nhà cung cấp':        'Trả lại nhà cung cấp',
  }
  return MAP[action] ?? action
}

function actionClass(action: string): string {
  if (isApproveAction(action)) return 'bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  if (action === 'Giữ lâm sàng') return 'bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  if (['Trả lại nhà cung cấp', 'Báo cáo DOA', 'Báo cáo sự cố'].includes(action)) return 'bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  if (['Báo cáo lỗi baseline', 'Yêu cầu bổ sung tài liệu'].includes(action)) return 'bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  if (['Gửi kiểm tra tài liệu', 'Xác nhận đủ tài liệu', 'Bắt đầu lắp đặt', 'Lắp đặt hoàn thành', 'Bắt đầu kiểm tra', 'Khắc phục xong'].includes(action))
    return 'btn-primary disabled:opacity-50 disabled:cursor-not-allowed'
  return 'btn-secondary disabled:opacity-50 disabled:cursor-not-allowed'
}

// CR-54 §1 / gate G06: action phát hành lâm sàng đòi board_approver. Nếu chưa
// chỉ định (gate G06 fail) → CHẶN click ngay ở FE (disable + lý do) thay vì để
// BE trả IMM04-GATE-G06-APPROVER (tránh nút chết / 417 thô rơi ra).
// CR-76: khi KHÔNG đọc được trạng thái cổng (403 trong envelope) thì `g06_approver`
// mặc định `false` — không được vì thế mà kết luận oan "chưa có người ký". Lấy thêm
// chính phiếu làm nguồn; backend vẫn là nơi quyết định cuối cùng.
const boardApproverAssigned = computed(
  () => Boolean(props.gateStatus.g06_approver) || Boolean(props.doc.board_approver),
)

function isApproveBlocked(action: string): boolean {
  return isApproveAction(action) && !boardApproverAssigned.value
}

function handleTransitionClick(action: string) {
  // Defense-in-depth: không emit khi thiếu người ký (nút cũng đã disable).
  if (props.saving || isApproveBlocked(action)) return
  // 'Phê duyệt phát hành' / 'Phê duyệt sau tái kiểm' là workflow transition
  // (không phải approve_clinical_release — endpoint đó chỉ chạy khi đã ở
  // Clinical Release). Emit transition để store gọi transition_state với
  // đúng chuỗi action khớp workflow JSON — board_approver được đính kèm 1-call
  // ở tầng view (handleTransitionFromPanel → store.transitionState).
  emit('transition', action)
}

// Warn if trying to approve without G06 set
const approveGateWarning = computed(() => {
  if (!boardApproverAssigned.value) return 'Chưa chỉ định Người phê duyệt Ban Giám đốc (G06). Vui lòng chỉ định ở mục "Phân công người phê duyệt" trước khi phê duyệt phát hành.'
  return null
})

const uniqueTransitions = computed(() => {
  const seen = new Set<string>()
  return (props.doc?.allowed_transitions ?? []).filter(t => {
    const label = actionLabel(t.action)
    if (seen.has(label)) return false
    seen.add(label)
    return true
  })
})
</script>

<template>
  <div class="space-y-5">
<!-- ─── Pending: chờ người khác duyệt ───────────────────────────────────── -->
    <div v-if="isPendingForOthers" class="card border border-amber-200 bg-amber-50">
      <div class="flex items-start gap-3">
        <span class="text-2xl">⏳</span>
        <div class="flex-1">
          <p class="font-semibold text-amber-800">Đang chờ duyệt</p>
          <p class="text-sm text-amber-700 mt-1">
            Người duyệt: <b>{{ doc.pending_approver }}</b>
          </p>
          <p class="text-xs text-amber-600 mt-0.5">
            Giai đoạn: {{ doc.approval_stage }} · Gửi lúc: {{ formatDt(doc.approval_submitted_at) }}
          </p>
          <p v-if="doc.approval_remarks" class="text-xs italic text-amber-700 mt-1.5 bg-amber-100/60 rounded px-2 py-1">
            {{ doc.approval_remarks }}
          </p>
        </div>
      </div>
    </div>

    <!-- ─── Pending: chờ tôi duyệt ──────────────────────────────────────────── -->
    <div v-if="isPendingForMe" class="card border-2 border-indigo-300 bg-indigo-50">
      <div class="flex items-start gap-3 mb-3">
        <span class="text-2xl">🔔</span>
        <div class="flex-1">
          <p class="font-semibold text-indigo-900">Chờ bạn duyệt</p>
          <p class="text-xs text-indigo-700 mt-0.5">
            Giai đoạn: {{ doc.approval_stage }} · Gửi lúc: {{ formatDt(doc.approval_submitted_at) }}
          </p>
          <p v-if="doc.approval_remarks" class="text-xs italic text-indigo-800 mt-1.5 bg-white/60 rounded px-2 py-1">
            {{ doc.approval_remarks }}
          </p>
        </div>
      </div>
      <textarea
        v-model="decisionRemarks"
        rows="2"
        class="form-input w-full text-sm mb-2"
        placeholder="Nhận xét (bắt buộc nếu từ chối)"
      />
      <div v-if="decisionError" class="text-xs text-red-600 mb-2">{{ decisionError }}</div>
      <div class="flex gap-2">
        <button
          class="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 rounded-lg text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="decisionSaving"
          @click="handleDecision('Approve')"
        >
          {{ decisionSaving ? '...' : '✓ Duyệt' }}
        </button>
        <button
          class="flex-1 bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded-lg text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="decisionSaving"
          @click="handleDecision('Reject')"
        >
          {{ decisionSaving ? '...' : '✗ Từ chối' }}
        </button>
      </div>
    </div>

    <!-- ─── Submit for Approval button ──────────────────────────────────────── -->
    <button
      v-if="canSubmitForApproval"
      class="w-full bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
      @click="showSubmitModal = true"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
      </svg>
      Gửi duyệt
    </button>

    <SubmitForApprovalModal
      :open="showSubmitModal"
      :commissioning="doc.name"
      :workflow-state="doc.workflow_state"
      @close="showSubmitModal = false"
      @submitted="showSubmitModal = false; emit('refresh')"
    />

    <!-- ─── A. Gate Checklist ──────────────────────────────────────────────── -->
    <div class="card">
      <div class="flex items-center justify-between pb-3 border-b mb-4">
        <h3 class="text-base font-semibold text-slate-900">Kiểm tra điều kiện phát hành (G01–G06)</h3>
        <span
          v-if="!gateError"
          class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
          :class="blockingGatesPassed ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'"
        >
          <svg v-if="blockingGatesPassed" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01" />
          </svg>
          {{ blockingGatesPassed ? 'Không còn cổng nào chặn phát hành' : 'Còn cổng đang chặn phát hành' }}
        </span>
      </div>

      <!-- Không đọc được trạng thái cổng (vd thiếu quyền đọc phiếu): báo rõ bằng
           tiếng Việt, KHÔNG vẽ 6 thẻ đỏ giả và KHÔNG để trống màn hình. -->
      <div
        v-if="gateError"
        role="alert"
        data-test="gate-error"
        class="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-800"
      >
        <svg class="w-4 h-4 shrink-0 mt-0.5 text-amber-600" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>{{ gateError }}</span>
      </div>

      <template v-else>
        <p class="text-xs text-slate-500 mb-3">
          Dấu tích nghĩa là cổng đó <b>không chặn</b> phát hành lâm sàng — không đồng nghĩa
          mọi việc đã hoàn tất.
        </p>

        <ul class="divide-y divide-slate-50">
          <li
            v-for="(gate, idx) in GATES"
            :key="gate.key"
            :data-test="`gate-${gate.key}`"
            class="flex items-start gap-3 py-2.5"
          >
            <!-- Gate number -->
            <span class="text-xs font-mono font-bold text-slate-400 shrink-0 w-8 pt-0.5">
              G0{{ idx + 1 }}
            </span>

            <!-- Icon (kèm chữ cho trình đọc màn hình — không phân biệt chỉ bằng màu) -->
            <span class="shrink-0 mt-0.5">
              <svg v-if="isGateNa(gate)" class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M18 12H6" />
              </svg>
              <svg v-else-if="gateValue(gate)" class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <svg v-else-if="!gate.blocking" class="w-4 h-4 text-sky-600" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <svg v-else class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span class="sr-only">
                {{ isGateNa(gate)
                  ? 'Không áp dụng'
                  : gateValue(gate)
                    ? 'Không chặn phát hành'
                    : gate.blocking ? 'Đang chặn phát hành' : 'Chưa ghi nhận, không chặn phát hành' }}
              </span>
            </span>

            <!-- Text -->
            <div class="flex-1 min-w-0">
              <p
                class="text-sm font-medium flex flex-wrap items-center gap-x-2 gap-y-1"
                :class="{
                  'text-emerald-700': !isGateNa(gate) && gateValue(gate),
                  'text-red-600': !isGateNa(gate) && !gateValue(gate) && gate.blocking,
                  'text-slate-600': !isGateNa(gate) && !gateValue(gate) && !gate.blocking,
                  'text-slate-400': isGateNa(gate),
                }"
              >
                <span>{{ gate.label }}</span>
                <span
                  v-if="gateStateChip(gate)"
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold"
                  :class="gateChipClass(gate)"
                  :title="gate.key === 'g01_docs' && isG01Waived && g01WaiverNote ? g01WaiverNote : undefined"
                >{{ gateStateChip(gate) }}</span>
              </p>
              <p class="text-xs text-slate-500 mt-0.5">{{ gateDescription(gate) }}</p>
              <p
                v-if="gate.key === 'g01_docs' && g01WaiverOnDoc"
                class="text-xs italic text-amber-700 mt-1 bg-amber-50 border border-amber-100 rounded px-2 py-1"
              >
                Giải trình: {{ g01WaiverNote }}
              </p>
            </div>
          </li>
        </ul>
      </template>
    </div>

    <!-- ─── B. Approver Assignment ─────────────────────────────────────────── -->
    <div class="card">
      <h3 class="text-base font-semibold text-slate-900 pb-3 border-b mb-4">Phân công người phê duyệt</h3>

      <div class="space-y-1">
        <!-- Board Approver — always required -->
        <ApproverSelect
          :model-value="doc.board_approver"
          role="IMM Operations Manager"
          label="Người phê duyệt BGĐ"
          placeholder="Tìm theo tên hoặc email..."
          :required="true"
          @update:model-value="emit('update-field', 'board_approver', $event)"
        />

        <!-- QA Officer — conditional on radiation/high-risk -->
        <ApproverSelect
          v-if="showQaOfficer"
          :model-value="doc.qa_officer"
          role="IMM QA Officer"
          label="Nhân viên đảm bảo chất lượng"
          placeholder="Tìm theo tên hoặc email..."
          @update:model-value="emit('update-field', 'qa_officer', $event)"
        />

        <!-- IMM Department Head — always shown -->
        <ApproverSelect
          :model-value="doc.clinical_head"
          role="IMM Workshop Lead"
          label="Trưởng khoa"
          placeholder="Tìm theo tên hoặc email..."
          @update:model-value="emit('update-field', 'clinical_head', $event)"
        />

        <!-- Commissioned By -->
        <ApproverSelect
          :model-value="doc.commissioned_by"
          role="IMM Biomed Technician"
          label="Kỹ sư thực hiện"
          placeholder="Tìm theo tên hoặc email..."
          @update:model-value="emit('update-field', 'commissioned_by', $event)"
        />
      </div>
    </div>

    <!-- ─── C. Action Buttons ──────────────────────────────────────────────── -->
    <div
      v-if="uniqueTransitions.length > 0"
      class="card"
    >
      <h3 class="text-base font-semibold text-slate-900 pb-3 border-b mb-4">Hành động workflow</h3>

      <!-- Gate warning for clinical release -->
      <div
        v-if="approveGateWarning && uniqueTransitions.some(t => isApproveAction(t.action))"
        class="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-800 mb-4"
      >
        <svg class="w-4 h-4 shrink-0 mt-0.5 text-amber-600" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>{{ approveGateWarning }}</span>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          v-for="t in uniqueTransitions"
          :key="t.action"
          :class="actionClass(t.action)"
          :disabled="saving || isApproveBlocked(t.action)"
          :aria-disabled="saving || isApproveBlocked(t.action) ? 'true' : undefined"
          :title="isApproveBlocked(t.action) ? (approveGateWarning ?? undefined) : undefined"
          @click="handleTransitionClick(t.action)"
        >
          <span class="flex items-center gap-1.5">
            <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            {{ actionLabel(t.action) }}
          </span>
        </button>
      </div>
    </div>
</div>
</template>
