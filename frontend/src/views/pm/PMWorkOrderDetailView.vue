<script setup lang="ts">
import { useNotify } from '@/composables/useNotify'
import { useToast } from '@/composables/useToast'
import { MSG } from '@/i18n/messages'
import DateInput from '@/components/common/DateInput.vue'
import RelatedRecords from '@/components/common/RelatedRecords.vue'
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { onMounted, computed, ref } from 'vue'
import { useImm08Store } from '@/stores/imm08'
import { useRouter } from 'vue-router'
import { pmStatusLabel, pmStatusClass, resultLabel as _resultLabel, pmTypeLabel, woTypeLabel, overallResultLabel } from '@/constants/labels'
import { useCapabilities } from '@/composables/useCapabilities'
import { useDetailAccess } from '@/composables/useDetailAccess'
import type { AvailableAction } from '@/api/imm08'
const notify = useNotify()
const toast = useToast()

const props = defineProps<{ id: string }>()
const store = useImm08Store()
const router = useRouter()
const { can } = useCapabilities()

// Tab màn chi tiết — «Bản ghi liên quan» mount LƯỜI (panel v-if) nên mở phiếu KHÔNG
// còn bắn `get_connections`; panel chính dùng v-show để giữ nguyên dữ liệu đang nhập.
// `ref<string>` chứ KHÔNG `ref<'detail'|'related'>`: prop/emit `active-tab` của shell khai
// `string` ⇒ union hẹp làm `vue-tsc` báo `string not assignable` (bẫy 13.9.3). Khoá tab vẫn
// được giữ chặt trong hằng `DETAIL_TABS: DetailTab[]`.
const activeTab = ref<string>('detail')
const DETAIL_TABS = [
  { key: 'detail', label: 'Chi tiết' },
  { key: 'related', label: 'Bản ghi liên quan' },
]

// ⚠️ ĐƯỜNG FALLBACK DUY NHẤT (AC-CR-77 / FE-3) — 3 computed dưới CHỈ còn dùng khi
// payload THIẾU `available_actions` (worker BE chưa reload / client cũ). Khi BE phát
// `available_actions`, trục QUYỀN do SERVER quyết (`enabled`) — FE KHÔNG nhân bản
// `can('pm.*') && allowedTransitions.includes(...)` cho 4 CTA nữa (nhân bản = nguồn
// "nút chết": FE cho bấm, BE từ chối).
// Capability gate khớp EXACT rbac.require BE (api/imm08.py): bắt đầu/báo lỗi lớn =
// pm.write; hoàn thành (submit_pm_result) = pm.submit; hoãn lịch (reschedule_pm) =
// pm.reschedule. KHÔNG dùng hasAnyRole(ROLES_PM_*) — các hằng này = [] (LL-FE-22) →
// hasAnyRole([]) LUÔN false ⇒ nút chết âm thầm.
const canExecutePM = computed(() => can('pm.write'))
const canSubmitPM = computed(() => can('pm.submit'))
const canManagePM = computed(() => can('pm.reschedule'))

const showMajorModal = ref(false)
const showSubmitModal = ref(false)
const showRescheduleModal = ref(false)
const majorFailureDesc = ref('')
const techNotes = ref('')
const stickerAttached = ref(false)
const durationMin = ref(0)
const submitting = ref(false)
const rescheduleDate = ref('')
const rescheduleReason = ref('')
const rescheduling = ref(false)

onMounted(() => store.fetchWorkOrder(props.id))

const wo = computed(() => store.currentWO)

// ─── CR-74 · quyền ĐỌC phiếu (403 in-envelope, HTTP-200) ────────────────────────
// BE gate get_pm_work_order bằng CÙNG predicate với list/mutate ⇒ thiếu DocPerm read
// hoặc phiếu chưa giao cho mình → {success:false, code:'FORBIDDEN'}. Ở đây CHỈ hiện
// message THẬT của server + ẩn toàn bộ CTA; TUYỆT ĐỐI KHÔNG logout/redirect login
// (đó là việc của dispatcher-403 trong axios interceptor). Handler dùng CHUNG cho
// 4 màn detail (PM/CM/Hiệu chuẩn/Sự cố) — xem composables/useDetailAccess.ts.
// Destructure ĐỔI TÊN (khuôn §13.4.0): truyền `access.kind` nguyên ref vào prop shell sẽ
// đưa cả object truthy sang ⇒ MÀN NÀO CŨNG kẹt ở trạng thái `error` (bẫy 13.9.1).
// `blocked` không còn cần ở template: nhánh `content` của shell ĐÃ là điều kiện đó — CTA
// nằm trong nhánh ấy nên «0 nút chết» đúng bằng CẤU TRÚC, không bằng một `v-if` phải nhớ.
const {
  kind: loadErrorKindRef,
  message: loadErrMsg,
} = useDetailAccess(() => (store.currentWO ? null : store.lastApiError))

// ─── SSoT server-driven CTA (GATE-8 / LL-FE-51 · mirror IncidentDetailView) ──────
// allowed_transitions do get_pm_work_order emit = _PM_VALID_TRANSITIONS.get(status, [])
// (imm08.py:652). Nút workflow gate theo (capability && includes('<đích>')) — KHÔNG
// hardcode `wo.status === 'X'`. Chuỗi đích khớp EXACT PMStatus (en-dash:
// 'Halted–Major Failure' / 'Pending–Device Busy'). Terminal (Completed/Cancelled) → [].
const allowedTransitions = computed<string[]>(() => wo.value?.allowed_transitions ?? [])

// ─── AC-CR-77 · CTA SERVER-DRIVEN (`available_actions`) ─────────────────────────
// `get_pm_work_order` phơi ĐÚNG 4 phần tử, thứ tự CỐ ĐỊNH [start_work, submit_result,
// reschedule, report_major_failure], shape {key,label,route,enabled,reason} (route="").
// `enabled` = transition_allowed ∩ has_cap ∩ business_gate do SERVER quyết; `reason`
// là chuỗi VI SERVER trả (bất biến D9: enabled=false ⟺ reason≠""). FE CHỈ RENDER:
// nhãn/disabled/tooltip đều từ payload — KHÔNG bịa chuỗi, KHÔNG tự tính quyền.
//   • hết "nút chết": thiếu capability ⇒ server trả enabled=false + lý do, nút hiện
//     nhưng KHÔNG bấm được (thay vì bấm rồi ăn 403 câm).
//   • hết "CTA ma": 'Cancelled' có trong _PM_VALID_TRANSITIONS nhưng KHÔNG có endpoint
//     ⇒ server không phát ⇒ FE không thể vẽ.
// Thiếu khoá (BE chưa reload) hoặc mảng rỗng ⇒ null ⇒ rơi về đường FALLBACK bên dưới
// (`allowed_transitions` + capability) — KHÔNG nút nào biến mất, KHÔNG màn trắng.
const serverActions = computed<AvailableAction[] | null>(() => {
  const list = wo.value?.available_actions
  return Array.isArray(list) && list.length > 0 ? list : null
})
const isServerDriven = computed(() => serverActions.value !== null)

// Chỉ đếm mục đã có kết quả (Đạt/Không đạt/N/A) là "đã hoàn thành" (IMM-08-A).
const filledCount = computed(() => store.ratedCount)
const totalCount = computed(() => wo.value?.checklist_results.length ?? 0)
const progressPct = computed(() =>
  totalCount.value > 0 ? Math.round((filledCount.value / totalCount.value) * 100) : 0
)

// Lý do chặn CỤC BỘ — CHỈ những điều kiện SERVER KHÔNG THẤY ĐƯỢC: form nhập tay chưa
// lưu (thời lượng / tem / kết quả bảng kiểm đang chấm dở trong bộ nhớ client). Dùng
// cho CẢ 2 đường (server-driven ∧ fallback): trục quyền/trạng-thái để server quyết,
// trục dữ-liệu-chưa-gửi để client quyết. CHỈ được SIẾT thêm, KHÔNG nới.
const localCompletionBlockReason = computed(() => {
  // BR-08-08 (chặn nghiệm-thu-giả): bảng kiểm RỖNG (thiếu bảng kiểm mẫu) → không có
  // bằng chứng công việc ⇒ chặn hoàn thành. Hint RIÊNG, khác "chưa chấm hết" — mirror
  // gate BE IMM08_CHECKLIST_EMPTY (AC-CR-77 A5: server cũng disable submit_result với
  // CÙNG điều kiện ⇒ display ⇔ enforcement parity). PHẢI kiểm trước checklistComplete
  // (rỗng cũng làm checklistComplete=false nhưng thông điệp phải chỉ đúng nguyên nhân).
  if (totalCount.value === 0) return 'Chưa có mục bảng kiểm — không thể nghiệm thu PM'
  if (!store.checklistComplete) return 'Phải chấm kết quả cho tất cả mục checklist trước khi hoàn thành'
  if (durationMin.value <= 0) return 'Thời gian thực hiện phải lớn hơn 0 phút'
  if (!stickerAttached.value) return 'Phải xác nhận đã gắn tem bảo trì'
  if (store.hasMajorFailure) return 'Có lỗi nghiêm trọng — dùng "Báo lỗi nghiêm trọng"'
  return ''
})
// Lý do không thể hoàn thành trên đường FALLBACK (FE mirror của gate BE BR-08-08/09/10)
// — thêm trục QUYỀN cục bộ vì payload cũ không nói được quyền.
const completionBlockReason = computed(() => {
  if (!canSubmitPM.value) return 'Bạn không có quyền hoàn thành bảo trì'
  return localCompletionBlockReason.value
})
const canSubmit = computed(() => completionBlockReason.value === '')

// ─── FALLBACK: CTA gate theo allowed_transitions (KHÔNG hardcode status) ────────
// CHỈ chạy khi payload THIẾU `available_actions` (`!isServerDriven`). Khi BE phát
// available_actions, cụm CTA server-driven bên dưới thay thế TOÀN BỘ 4 nút này.
// Báo lỗi nghiêm trọng: In Progress → Halted–Major Failure. Chỉ render khi BE cho phép.
const canReportMajor = computed(() =>
  !isServerDriven.value && canExecutePM.value && allowedTransitions.value.includes('Halted–Major Failure'),
)
// "Hoàn thành bảo trì" render khi BE cho phép chuyển 'Completed' + chưa có lỗi lớn;
// điều kiện checklist/quyền/tem/thời-lượng (canSubmit) chi phối trạng thái disabled + tooltip.
const canCompleteRender = computed(() =>
  !isServerDriven.value && allowedTransitions.value.includes('Completed') && !store.hasMajorFailure,
)
// Hoãn lịch (pm.reschedule) trong banner quá hạn: BE cho phép quay lại In Progress.
const canReschedule = computed(() =>
  !isServerDriven.value && canManagePM.value &&
  (allowedTransitions.value.includes('In Progress') || allowedTransitions.value.includes('Pending–Device Busy')),
)
// Tiếp tục bảo trì (resume — thao tác thực hiện, pm.write) trong banner quá hạn.
const canResume = computed(() =>
  canExecutePM.value &&
  (allowedTransitions.value.includes('In Progress') || allowedTransitions.value.includes('Pending–Device Busy')),
)

// LIVE quá hạn (CR-37 · BR-08-11 LIVE) — đọc cờ SERVER `is_overdue` do
// get_pm_work_order enrich (CÙNG predicate _enrich_pm_overdue của list-item), ưu
// tiên hơn cờ STORED. Fallback `status === 'Overdue'` (forward-compat: BE chưa emit
// → undefined). Chặn banner Quá-hạn trễ 1 nhịp scheduler khi WO đã vượt due_date
// nhưng status chưa được cron stamp sang Overdue. Đối xứng list badge + is_sla_breached.
const isOverdue = computed(() => wo.value?.is_overdue ?? (wo.value?.status === 'Overdue'))

// Compute overdue days from due_date
const overdueDays = computed(() => {
  if (!wo.value?.due_date) return 0
  const due = new Date(wo.value.due_date)
  const now = new Date()
  const diff = Math.floor((now.getTime() - due.getTime()) / (1000 * 60 * 60 * 24))
  return Math.max(0, diff)
})

function resultClass(result: string | null) {
  if (result === 'Pass') return 'border-emerald-300 bg-emerald-50/60'
  if (result === 'Fail–Minor') return 'border-amber-300 bg-amber-50/60'
  if (result === 'Fail–Major') return 'border-red-300 bg-red-50/60'
  return 'border-slate-200'
}

async function handleSubmit() {
  submitting.value = true
  const res = await store.doSubmitResult(techNotes.value, stickerAttached.value, durationMin.value)
  submitting.value = false
  showSubmitModal.value = false
  if (res.success) {
    notify.show({ code: MSG.IMM08_SUBMIT_SUCCESS, ctx: { name: wo.value?.name ?? props.id } })
    // Force re-fetch to ensure reactive update
    await store.fetchWorkOrder(props.id)
    if (res.cmWoCreated) {
      const go = confirm(`Đã hoàn thành bảo trì. Phiếu sửa chữa khắc phục đã được tạo: ${res.cmWoCreated}\n\nMở phiếu sửa chữa ngay?`)
      if (go) router.push(`/cm/work-orders/${res.cmWoCreated}`)
    }
  } else {
    notify.fromError(store.lastApiError)
  }
}

const majorFailureError = ref('')

async function handleMajorFailure() {
  majorFailureError.value = ''
  const cmWo = await store.doReportMajorFailure(majorFailureDesc.value)
  if (cmWo) {
    showMajorModal.value = false
    toast.success(`Đã báo lỗi nghiêm trọng. Phiếu sửa chữa đã được tạo: ${cmWo}\nThiết bị đã được đặt trạng thái Ngừng hoạt động.`)
    router.push(`/cm/work-orders/${cmWo}`)
  } else {
    notify.fromError(store.lastApiError)
    majorFailureError.value = store.error || 'Không thể báo lỗi. Vui lòng thử lại.'
  }
}

const rescheduleError = ref('')

async function handleReschedule() {
  if (!wo.value || !rescheduleDate.value || !rescheduleReason.value) return
  rescheduling.value = true
  rescheduleError.value = ''
  const ok = await store.doReschedule(wo.value.name, rescheduleDate.value, rescheduleReason.value)
  rescheduling.value = false
  if (ok) {
    showRescheduleModal.value = false
    rescheduleDate.value = ''
    rescheduleReason.value = ''
    toast.success('Đã hoãn lịch bảo trì')
  } else {
    notify.fromError(store.lastApiError)
    rescheduleError.value = store.error || 'Hoãn lịch thất bại'
  }
}

function openRescheduleModal() {
  rescheduleDate.value = ''
  rescheduleReason.value = ''
  rescheduleError.value = ''
  showRescheduleModal.value = true
}

const startError = ref('')
const starting = ref(false)
// FALLBACK — Bắt đầu bảo trì (→ In Progress): gate theo allowed_transitions BE + guard
// assigned_to (KHÔNG hardcode status === 'Open'|'Overdue'). Cần capability pm.write
// (BE assign_technician). Tắt hẳn khi payload có `available_actions`.
const canStart = computed(() =>
  !isServerDriven.value && !!wo.value && canExecutePM.value &&
  allowedTransitions.value.includes('In Progress') && !!wo.value.assigned_to,
)

async function handleStart() {
  if (!wo.value || !wo.value.assigned_to) return
  starting.value = true
  startError.value = ''
  const ok = await store.doAssignTechnician(wo.value.name, wo.value.assigned_to)
  starting.value = false
  if (ok) {
    toast.success('Đã bắt đầu thực hiện bảo trì')
    await store.fetchWorkOrder(props.id)
  } else {
    notify.fromError(store.lastApiError)
    startError.value = store.error || 'Không thể bắt đầu bảo trì định kỳ'
  }
}

// ─── AC-CR-77 · lớp render cho CTA server-driven ────────────────────────────────
// Mỗi `key` ánh xạ 1-1 tới ĐÚNG 1 endpoint whitelisted của assetcore/api/imm08.py
// (start_work→assign_technician · submit_result→submit_pm_result ·
// reschedule→reschedule_pm · report_major_failure→report_major_failure). Bảng dưới
// chỉ quyết ĐỊNH DẠNG (testid/lớp CSS/nhãn dự phòng) — KHÔNG quyết enabled.
const CTA_TESTID: Record<string, string> = {
  start_work: 'cta-start',
  submit_result: 'cta-complete',
  reschedule: 'cta-reschedule',
  report_major_failure: 'cta-major',
}
const CTA_CLASS: Record<string, string> = {
  start_work: 'btn-primary',
  submit_result: 'btn-success',
  reschedule: 'btn-secondary',
  report_major_failure: 'btn-danger',
}
// Nhãn dự phòng CHỈ dùng khi server trả label rỗng (hợp đồng nói luôn có) — KHÔNG
// phải nguồn nhãn chính: nhãn hiển thị lấy từ `a.label` của server.
const CTA_LABEL_FALLBACK: Record<string, string> = {
  start_work: 'Bắt đầu bảo trì',
  submit_result: 'Hoàn thành bảo trì',
  reschedule: 'Hoãn lịch',
  report_major_failure: 'Báo lỗi nghiêm trọng',
}

// Bảng HÀNH ĐỘNG: key → thao tác FE thực thi. Vừa là nơi dispatch click, vừa là
// nguồn kiểm "key này có đường thực thi ở FE không" (một map, không hai danh sách).
const CTA_HANDLERS: Record<string, () => void> = {
  start_work: () => { void handleStart() },
  submit_result: () => { showSubmitModal.value = true },
  reschedule: () => { openRescheduleModal() },
  report_major_failure: () => {
    majorFailureDesc.value = ''
    majorFailureError.value = ''
    showMajorModal.value = true
  },
}
// Overlay FE (trục "handler-resolvability", song song ROUTE_UNAVAILABLE_REASON của
// màn quét QR): BE thêm action key MỚI mà bản giao diện này chưa biết ⇒ nút sẽ là
// no-op câm nếu vẫn cho bấm. Render nhưng KHÓA + nói rõ lý do là failure-mode an toàn.
const UNSUPPORTED_ACTION_REASON =
  'Thao tác chưa được hỗ trợ trên phiên bản giao diện này — vui lòng tải lại trang'

function actionLabel(a: AvailableAction): string {
  return a.label?.trim() || CTA_LABEL_FALLBACK[a.key] || a.key
}

// Precondition CỤC BỘ (server không thấy): key lạ + dữ liệu chưa gửi + phiếu chưa
// phân công. CHỈ SIẾT thêm, KHÔNG nới — server nói disabled thì luôn disabled.
function localBlockReason(a: AvailableAction): string {
  if (!CTA_HANDLERS[a.key]) return UNSUPPORTED_ACTION_REASON
  if (a.key === 'start_work' && !wo.value?.assigned_to) {
    return 'Phiếu chưa được phân công kỹ thuật viên'
  }
  if (a.key === 'submit_result') return localCompletionBlockReason.value
  return ''
}
function actionEnabled(a: AvailableAction): boolean {
  return a.enabled && localBlockReason(a) === ''
}
// Tooltip: ƯU TIÊN TUYỆT ĐỐI chuỗi `reason` của SERVER khi server disable (không đè
// bằng chuỗi FE); chỉ khi server cho phép mới hiện lý do cục bộ.
function actionReason(a: AvailableAction): string {
  return a.enabled ? localBlockReason(a) : a.reason
}
function actionBusy(a: AvailableAction): boolean {
  if (a.key === 'start_work') return starting.value
  if (a.key === 'submit_result') return submitting.value
  return false
}
// Danh sách lý do khoá — hiển thị dạng text (a11y: nút disabled KHÔNG focus được nên
// `title` một mình không đủ; WCAG 1.4.1 cũng cấm chỉ dựa màu).
const blockedActions = computed<AvailableAction[]>(() =>
  (serverActions.value ?? []).filter((a) => !actionEnabled(a) && actionReason(a) !== ''),
)

function runServerAction(a: AvailableAction): void {
  if (!actionEnabled(a) || actionBusy(a)) return
  CTA_HANDLERS[a.key]?.()
}
</script>

<template>
  <DetailPageShell
    :loading="store.loading"
    :error-kind="loadErrorKindRef"
    :error-message="loadErrMsg"
    :doc="wo"
    entity-label="phiếu bảo trì định kỳ"
    :record-id="props.id"
    back-label="Về danh sách bảo trì định kỳ"
    :tabs="DETAIL_TABS"
    v-model:active-tab="activeTab"
    @retry="store.fetchWorkOrder(props.id)"
    @back="router.push('/pm/work-orders')">
    <template #title>
    <!-- Back + Header -->
    <div class="flex items-center gap-3 mb-5">
      <button class="text-slate-400 hover:text-slate-700 transition-colors" aria-label="Quay lại danh sách" @click="router.push('/pm/work-orders')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="code-pill-lg">{{ wo?.name }}</span>
          <span v-if="wo" :class="['px-2.5 py-0.5 rounded-full text-[11px] font-medium', pmStatusClass(wo.status)]">
            {{ pmStatusLabel(wo.status) }}
          </span>
          <span class="text-[11.5px] text-slate-400 font-medium">IMM-08 · Bảo trì định kỳ</span>
        </div>
        <h1 class="text-xl font-semibold text-slate-900 mt-1 truncate">{{ wo?.asset_name || wo?.asset_ref || 'Phiếu bảo trì' }}</h1>
      </div>
    </div>
    </template>

    <!-- Thanh tab HOISTING lên prop shell (ADR-UX-25): shell là nơi DUY NHẤT vẽ thanh tab,
         và nó nằm trong nhánh `content` ⇒ phiếu bị chặn đọc KHÔNG có nút tab chết, đúng
         bằng CẤU TRÚC (không cần `v-if` bù — bẫy 13.9.10). -->
    <template v-if="wo">
      <div v-show="activeTab === 'detail'" data-testid="tab-panel-detail">
      <!-- Overdue Warning Banner -->
      <Transition
        enter-active-class="transition duration-200"
        enter-from-class="opacity-0 -translate-y-2"
        leave-active-class="transition duration-150"
        leave-to-class="opacity-0 -translate-y-2"
      >
        <div
          v-if="isOverdue"
          class="alert-error mb-5 flex-col sm:flex-row sm:items-center sm:justify-between"
        >
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-danger-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-2.694-.833-3.464 0L3.34 16.5C2.57 18.333 3.532 20 5.07 20z" />
            </svg>
            <div>
              <div class="font-semibold text-red-700 text-sm">
                Bảo trì quá hạn{{ overdueDays > 0 ? ` ${overdueDays} ngày` : '' }} — Đến hạn: {{ wo.due_date }}
              </div>
              <div class="text-xs text-red-600 mt-0.5">Vui lòng hoàn thành hoặc hoãn lịch có ghi lý do</div>
            </div>
          </div>
          <div class="flex gap-2 shrink-0">
            <button v-if="canReschedule" data-testid="cta-reschedule" class="btn-secondary !py-1.5 !text-xs" @click="openRescheduleModal">Hoãn lịch</button>
            <button v-if="canResume" data-testid="cta-resume" class="btn-danger !py-1.5 !text-xs" @click="store.fetchWorkOrder(props.id)">Tiếp tục bảo trì</button>
          </div>
        </div>
      </Transition>

      <!-- Info grid -->
      <div class="card-sm mb-5">
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div class="md:col-span-2">
            <span class="text-slate-500">Thiết bị:</span>
            <span class="font-semibold ml-1">{{ wo.asset_name || wo.asset_ref }}</span>
            <span v-if="wo.asset_name" class="ml-2 text-xs text-slate-400 font-mono">{{ wo.asset_ref }}</span>
          </div>
          <div>
            <span class="text-slate-500">Đến hạn:</span>
            <!-- Red-highlight đọc cờ LIVE `isOverdue` (đang quá hạn) HỢP với `is_late`
                 (STORED — hoàn-thành-trễ, giữ tín hiệu lịch sử cho phiếu đã Hoàn thành).
                 Live-overdue mở (is_late=0) vẫn đỏ, không trễ nhịp scheduler. -->
            <span :class="(isOverdue || wo.is_late) ? 'font-semibold text-red-600 ml-1' : 'font-medium ml-1'">{{ wo.due_date }}</span>
          </div>
          <div><span class="text-slate-500">Loại bảo trì:</span> <span class="font-medium ml-1">{{ pmTypeLabel(wo.pm_type) }}</span></div>
          <div><span class="text-slate-500">Kỹ thuật viên:</span> <span class="font-medium ml-1">{{ wo.assigned_to_name || wo.assigned_to || '—' }}</span></div>
          <div><span class="text-slate-500">Người giám sát:</span> <span class="font-medium ml-1">{{ wo.supervisor_name || wo.supervisor || '—' }}</span></div>
          <div><span class="text-slate-500">Mức rủi ro:</span> <span class="font-medium ml-1">{{ wo.risk_class }}</span></div>
          <div><span class="text-slate-500">Loại phiếu:</span> <span class="font-medium ml-1">{{ woTypeLabel(wo.wo_type) }}</span></div>
        </div>
      </div>

      <!-- Start PM banner (Open/Overdue → In Progress) — FALLBACK: `canStart` tự tắt
           khi payload có `available_actions` (nút «bắt đầu» nằm ở cụm CTA server-driven). -->
      <div v-if="canStart" class="alert-info mb-5 sm:items-center sm:justify-between">
        <div>
          <div class="font-semibold">Sẵn sàng bắt đầu bảo trì</div>
          <div class="text-xs text-blue-700 mt-0.5">Bấm "Bắt đầu bảo trì" để chuyển phiếu sang <strong>Đang thực hiện</strong> và đặt thiết bị về <strong>Đang sửa chữa</strong>.</div>
          <div v-if="startError" class="text-xs text-red-600 mt-1">{{ startError }}</div>
        </div>
        <button :disabled="starting" data-testid="cta-start" class="btn-primary !py-2 !text-sm whitespace-nowrap ml-auto" @click="handleStart">
          {{ starting ? 'Đang bắt đầu...' : 'Bắt đầu bảo trì' }}
        </button>
      </div>

      <!-- Checklist Section -->
      <div class="card-sm mb-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-semibold text-slate-800">Checklist ({{ filledCount }}/{{ totalCount }} đã hoàn thành)</h2>
          <span :class="['text-sm font-medium', progressPct === 100 ? 'text-emerald-600' : 'text-brand-600']">
            {{ progressPct }}%
          </span>
        </div>

        <!-- Progress Bar (smooth 500ms transition) -->
        <div class="h-2 bg-slate-100 rounded-full mb-5 overflow-hidden">
          <div
            class="h-2 rounded-full transition-all duration-500"
            :class="progressPct === 100 ? 'bg-emerald-500' : 'bg-brand-600'"
            :style="{ width: `${progressPct}%` }"
          />
        </div>

        <!-- Checklist Items -->
        <div class="space-y-4">
          <div
            v-for="item in wo.checklist_results"
            :key="item.idx"
            :class="['border rounded-lg p-4 transition-colors duration-200', resultClass(item.result)]"
          >
            <div class="flex items-start gap-3 mb-3">
              <span class="shrink-0 w-6 h-6 rounded-full bg-slate-200 text-slate-600 text-xs font-bold flex items-center justify-center">
                {{ item.idx }}
              </span>
              <div class="flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-medium text-slate-800 text-sm">{{ item.description }}</span>
                  <span v-if="item.result === 'Fail–Major'"
                    class="text-[10px] bg-red-600 text-white px-1.5 py-0.5 rounded font-semibold uppercase tracking-wide">Nghiêm trọng</span>
                  <span v-if="item.measurement_type === 'Numeric'" class="text-[10px] bg-brand-50 text-brand-700 px-1.5 py-0.5 rounded uppercase tracking-wide">Số đo</span>
                </div>
              </div>
            </div>

            <!-- Result Buttons -->
            <div v-if="wo.status !== 'Completed'" class="flex flex-wrap gap-2 mb-3">
              <button
                v-for="opt in ['Pass', 'Fail–Minor', 'Fail–Major', 'N/A']"
                :key="opt"
                :class="[
                  'px-3 py-1.5 rounded-md text-xs font-medium border transition-all duration-150',
                  item.result === opt
                    ? opt === 'Pass' ? 'bg-emerald-600 text-white border-emerald-600'
                    : opt === 'Fail–Minor' ? 'bg-amber-500 text-white border-amber-500'
                    : opt === 'Fail–Major' ? 'bg-red-600 text-white border-red-600'
                    : 'bg-slate-500 text-white border-slate-500'
                    : 'bg-white text-slate-600 border-slate-300 hover:border-slate-400'
                ]"
                @click="store.updateChecklistResult(item.idx, { result: opt as any })"
              >
                {{ _resultLabel(opt) }}
              </button>
            </div>
            <div v-else class="mb-2">
              <span
:class="['px-2 py-1 rounded text-xs font-medium',
                item.result === 'Pass' ? 'bg-emerald-100 text-emerald-700' :
                item.result === 'Fail–Minor' ? 'bg-amber-100 text-amber-700' :
                item.result === 'Fail–Major' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600']">
                {{ item.result ? _resultLabel(item.result) : '—' }}
              </span>
            </div>

            <!-- Numeric value -->
            <div v-if="item.measurement_type === 'Numeric'" class="mb-2">
              <input
                v-if="wo.status !== 'Completed'"
                :value="item.measured_value"
                type="number"
                placeholder="Giá trị đo được"
                class="form-input !py-1.5 !text-sm w-40"
                @input="store.updateChecklistResult(item.idx, { measured_value: Number(($event.target as HTMLInputElement).value) })"
              />
              <span v-else class="text-sm text-slate-600">{{ item.measured_value }} {{ item.unit }}</span>
            </div>

            <!-- Notes for failures -->
            <div v-if="item.result && item.result !== 'Pass' && item.result !== 'N/A'">
              <textarea
                v-if="wo.status !== 'Completed'"
                :value="item.notes"
                placeholder="Ghi chú lỗi (bắt buộc khi Fail)..."
                rows="2"
                class="form-textarea !text-sm"
                @input="store.updateChecklistResult(item.idx, { notes: ($event.target as HTMLTextAreaElement).value })"
              />
              <p v-else class="text-sm text-slate-600 italic">{{ item.notes }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Kết quả tổng thể -->
      <div v-if="wo.status !== 'Completed'" class="card-sm mb-5">
        <h2 class="font-semibold text-slate-800 mb-4">Kết quả tổng thể</h2>
        <div class="space-y-3">
          <div class="form-group">
            <label for="tech-notes" class="form-label">Ghi chú kỹ thuật viên</label>
            <textarea id="tech-notes" v-model="techNotes" rows="3" class="form-textarea !text-sm" placeholder="Ghi chú kỹ thuật..." />
          </div>
          <div class="flex items-center gap-3">
            <input id="sticker" v-model="stickerAttached" type="checkbox" class="w-4 h-4 accent-brand-600" />
            <label for="sticker" class="text-sm text-slate-700">Đã gắn tem bảo trì</label>
          </div>
          <div class="flex items-center gap-3">
            <label for="duration-min" class="text-sm text-slate-600 w-40">Thời gian thực hiện:</label>
            <input id="duration-min" v-model="durationMin" type="number" min="0" class="form-input !py-1.5 !text-sm w-24" />
            <span class="text-sm text-slate-500">phút</span>
          </div>
        </div>
      </div>

      <!-- AC-CR-77 — CỤM CTA SERVER-DRIVEN. v-for render MỌI phần tử `available_actions`
           theo ĐÚNG thứ tự BE phát (start_work, submit_result, reschedule,
           report_major_failure): nhãn = `label` server, disabled = !enabled, tooltip =
           `reason` server. KHÔNG ẩn nút thiếu quyền (người dùng thấy nút + lý do thay
           vì bấm rồi ăn 403 câm) và KHÔNG BAO GIỜ vẽ được CTA ma (server không phát
           'Cancelled' vì không có endpoint). Payload thiếu khoá ⇒ khối này không render
           và các nút FALLBACK bên dưới/bên trên hiện y như cũ. -->
      <div v-if="isServerDriven" data-testid="pm-cta-bar" class="card-sm">
        <div class="flex flex-wrap items-center justify-end gap-2">
          <button
            v-for="a in serverActions"
            :key="a.key"
            type="button"
            :data-testid="CTA_TESTID[a.key]"
            :data-action-key="a.key"
            :class="CTA_CLASS[a.key] || 'btn-secondary'"
            :disabled="!actionEnabled(a) || actionBusy(a)"
            :aria-disabled="actionEnabled(a) ? undefined : 'true'"
            :title="actionReason(a) || undefined"
            :aria-label="actionReason(a) ? `${actionLabel(a)} — không khả dụng: ${actionReason(a)}` : actionLabel(a)"
            :aria-describedby="actionReason(a) ? `pm-cta-reason-${a.key}` : undefined"
            @click="runServerAction(a)"
          >
            {{ actionBusy(a) ? 'Đang xử lý…' : actionLabel(a) }}
          </button>
        </div>
        <!-- Lý do khoá dạng chữ (KHÔNG chỉ tooltip/màu) — nút disabled không nhận
             focus nên screen-reader không đọc được `title`. -->
        <ul v-if="blockedActions.length" aria-live="polite" class="mt-3 space-y-1">
          <li
            v-for="a in blockedActions"
            :id="`pm-cta-reason-${a.key}`"
            :key="`pm-cta-reason-${a.key}`"
            class="flex items-start gap-1.5 text-xs text-slate-500"
          >
            <span aria-hidden="true">🔒</span>
            <span><span class="font-medium">{{ actionLabel(a) }}:</span> {{ actionReason(a) }}</span>
          </li>
        </ul>
      </div>

      <!-- FALLBACK (payload thiếu available_actions) — gate theo (capability &&
           allowed_transitions BE), KHÔNG hardcode wo.status === 'X' (GATE-8 / LL-FE-51). -->
      <div v-if="canReportMajor || canCompleteRender" class="flex justify-between items-center">
        <button v-if="canReportMajor" data-testid="cta-major" class="btn-danger" @click="showMajorModal = true; majorFailureDesc = ''; majorFailureError = ''">
          Báo lỗi nghiêm trọng
        </button>

        <div v-if="canCompleteRender" class="relative group ml-auto">
          <button
            data-testid="cta-complete"
            :disabled="!canSubmit || submitting"
            class="btn-success"
            @click="canSubmit && !submitting ? showSubmitModal = true : undefined"
          >
            Hoàn thành bảo trì
          </button>
          <div v-if="!canSubmit"
            class="absolute bottom-full right-0 mb-2 w-64 bg-slate-800 text-white text-xs rounded-md px-2.5 py-1.5 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
            {{ completionBlockReason }}
          </div>
        </div>
      </div>

      <!-- Completed summary -->
      <div v-if="wo.status === 'Completed'" class="alert-success">
        <div>
          <div class="font-semibold mb-0.5">Bảo trì đã hoàn thành</div>
          <div class="text-sm">Kết quả: {{ overallResultLabel(wo.overall_result) }} · Ngày: {{ wo.completion_date }}</div>
        </div>
      </div>
      </div>

      <!-- Bản ghi liên quan: TAB RIÊNG, mount LƯỜI (v-if) — nội dung do đồ thị liên kết
           ở backend quyết định. -->
      <div v-if="activeTab === 'related'" data-testid="tab-panel-related">
        <RelatedRecords doctype="PM Work Order" :name="wo.name" />
      </div>
    </template>

    <!-- Reschedule Modal (from Overdue banner) -->
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 scale-95"
      leave-active-class="transition duration-150"
      leave-to-class="opacity-0 scale-95"
    >
      <div v-if="showRescheduleModal" class="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" @click.self="showRescheduleModal = false">
        <div class="bg-white rounded-xl p-6 w-full max-w-md mx-4 shadow-dropdown">
          <h3 class="font-semibold text-lg text-slate-900 mb-4">Hoãn lịch bảo trì</h3>
          <div class="space-y-4">
            <div v-if="rescheduleError" class="alert-error text-sm">{{ rescheduleError }}</div>
            <div class="form-group">
              <label for="reschedule-date" class="form-label">Ngày mới <span class="text-danger-500">*</span></label>
              <DateInput id="reschedule-date" v-model="rescheduleDate" class="form-input !text-sm" />
            </div>
            <div class="form-group">
              <label for="reschedule-reason" class="form-label">Lý do hoãn <span class="text-danger-500">*</span></label>
              <textarea
                id="reschedule-reason"
                v-model="rescheduleReason"
                rows="3"
                class="form-textarea !text-sm"
                placeholder="Nhập lý do hoãn lịch (tối thiểu 5 ký tự)..."
              />
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-5">
            <button class="btn-secondary" @click="showRescheduleModal = false">Huỷ</button>
            <button :disabled="!rescheduleDate || !rescheduleReason || rescheduling" class="btn-primary" @click="handleReschedule">
              {{ rescheduling ? 'Đang xử lý...' : 'Xác nhận hoãn' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Major Failure Modal -->
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 scale-95"
      leave-active-class="transition duration-150"
      leave-to-class="opacity-0 scale-95"
    >
      <div v-if="showMajorModal" class="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" @click.self="showMajorModal = false">
        <div class="bg-white rounded-xl p-6 w-full max-w-md mx-4 shadow-dropdown">
          <h3 class="font-semibold text-lg text-red-700 mb-2">Báo lỗi nghiêm trọng</h3>
          <p class="text-sm text-slate-600 mb-4">Thiết bị sẽ được đặt trạng thái "Ngừng hoạt động" và tạo phiếu sửa chữa khẩn cấp.</p>
          <div v-if="majorFailureError" class="alert-error text-sm mb-3">{{ majorFailureError }}</div>
          <label for="major-failure-desc" class="sr-only">Mô tả lỗi nghiêm trọng</label>
          <textarea
            id="major-failure-desc"
            v-model="majorFailureDesc"
            rows="4"
            class="form-textarea !text-sm mb-4"
            placeholder="Mô tả chi tiết lỗi nghiêm trọng..."
          />
          <div class="flex justify-end gap-2">
            <button class="btn-secondary" @click="showMajorModal = false">Huỷ</button>
            <button :disabled="!majorFailureDesc" class="btn-danger" @click="handleMajorFailure">Xác nhận báo lỗi</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Submit Modal -->
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 scale-95"
      leave-active-class="transition duration-150"
      leave-to-class="opacity-0 scale-95"
    >
      <div v-if="showSubmitModal" class="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50" @click.self="showSubmitModal = false">
        <div class="bg-white rounded-xl p-6 w-full max-w-md mx-4 shadow-dropdown">
          <h3 class="font-semibold text-lg text-slate-900 mb-4">Xác nhận hoàn thành bảo trì</h3>
          <div class="text-sm text-slate-600 space-y-2 mb-4">
            <div>Bảng kiểm: <strong class="text-emerald-600">{{ filledCount }}/{{ totalCount }} mục</strong></div>
            <div>Thời gian: <strong>{{ durationMin }} phút</strong></div>
            <div>Tem bảo trì: <strong>{{ stickerAttached ? 'Đã gắn' : 'Chưa gắn' }}</strong></div>
            <div v-if="store.hasMinorFailure" class="text-amber-700">
              Có {{ wo?.checklist_results.filter(r => r.result === 'Fail–Minor').length }} mục lỗi nhỏ — sẽ tạo phiếu sửa chữa mức ưu tiên Trung bình
            </div>
          </div>
          <div class="flex justify-end gap-2">
            <button class="btn-secondary" @click="showSubmitModal = false">Huỷ</button>
            <button :disabled="submitting" class="btn-success" @click="handleSubmit">
              {{ submitting ? 'Đang xử lý...' : 'Hoàn thành bảo trì' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </DetailPageShell>
</template>

<style scoped>
/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
