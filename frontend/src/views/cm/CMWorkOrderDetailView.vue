<script setup lang="ts">
import { onMounted, computed, ref, onUnmounted } from 'vue'
import { useImm09Store } from '@/stores/imm09'
import type { SparePartRow, AvailableAction } from '@/api/imm09'
import { useRouter } from 'vue-router'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'
import { cmStatusLabel, cmStatusClass, priorityLabel, priorityClass, rootCauseLabel, repairTypeLabel, resultLabel, lifecycleStatusLabel, lifecycleStatusClass, riskClassificationLabel } from '@/constants/labels'
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import { useCapabilities } from '@/composables/useCapabilities'
import { useDetailAccess } from '@/composables/useDetailAccess'

import RelatedRecords from '@/components/common/RelatedRecords.vue'
import DetailTabBar from '@/components/common/DetailTabBar.vue'
import DetailLoadError from '@/components/common/DetailLoadError.vue'

const props = defineProps<{ id: string }>()
const store = useImm09Store()
const router = useRouter()
const notify = useNotify()
const { can } = useCapabilities()

/** Sau mỗi action store: success → toast chuẩn; fail → notify.fromError(ApiError đã hydrate). */
function notifyResult(ok: boolean, successCode: string, ctx: Record<string, unknown> = {}): void {
  if (ok) notify.show({ code: successCode, ctx })
  else notify.fromError(store.lastApiError)
}

// Tab màn chi tiết — «Bản ghi liên quan» mount LƯỜI (panel v-if) nên mở phiếu KHÔNG
// còn bắn `get_connections`; panel chính dùng v-show để giữ nguyên dữ liệu đang nhập.
const activeTab = ref<'detail' | 'related'>('detail')
const DETAIL_TABS = [
  { key: 'detail', label: 'Chi tiết' },
  { key: 'related', label: 'Bản ghi liên quan' },
]

// Only Assign and Cannot Repair remain as modals; others navigate to sub-routes
const showAssignModal = ref(false)
const showCannotRepairModal = ref(false)

// Form state for remaining modals
const assignEmail = ref('')
const assignPriority = ref('')
const cannotReason = ref('')
const submitting = ref(false)
// Busy riêng cho «Bắt đầu sửa chữa» (AC-CR-82) — không khoá lây các CTA khác.
const starting = ref(false)

// Realtime elapsed timer
const elapsed = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await store.fetchWorkOrder(props.id)
  startTimer()
})

onUnmounted(() => { if (timer) clearInterval(timer) })

function startTimer() {
  const wo = store.currentWO
  if (!wo?.open_datetime) return
  const startMs = new Date(wo.open_datetime).getTime()
  const isClosed = ['Completed', 'Cannot Repair', 'Cancelled'].includes(wo.status)
  if (isClosed) {
    // Đã đóng: dùng mttr_hours (BE-authoritative, = completion - open) — KHÔNG dùng Date.now()
    if (wo.mttr_hours != null) {
      elapsed.value = Math.max(0, Math.floor(wo.mttr_hours * 3600))
    } else if (wo.completion_datetime) {
      const endMs = new Date(wo.completion_datetime).getTime()
      elapsed.value = Math.max(0, Math.floor((endMs - startMs) / 1000))
    } else {
      elapsed.value = 0
    }
    return
  }
  const update = () => { elapsed.value = Math.floor((Date.now() - startMs) / 1000) }
  update()
  timer = setInterval(update, 1000)
}

const wo = computed(() => store.currentWO)

// ─── CR-74 · quyền ĐỌC phiếu (403 in-envelope, HTTP-200) ────────────────────────
// get_repair_work_order nay gate bằng CÙNG predicate với list_work_orders và
// attach_repair_checklist_photo (invariant read⇔write): KTV không được giao phiếu
// nhận {success:false, code:'FORBIDDEN'} ⇒ trang hiện message THẬT của server, ẩn
// TOÀN BỘ CTA (không còn cảnh "mở được phiếu, bấm đính ảnh mới báo không có quyền").
// KHÔNG logout/redirect — đó là dispatcher-403 (axios interceptor), khác loại.
const {
  kind: loadErrorKindRef,
  blocked: loadBlocked,
  message: loadErrMsg,
} = useDetailAccess(() => (store.currentWO ? null : store.lastApiError))

// ─── Phân loại rủi ro thiết bị (NĐ98) — nhãn VN, KHÔNG leak raw code ─────────────
// Nguồn = `risk_classification` verbatim của AC Asset ∈ {Low,Medium,High,Critical,''}
// (CR-51: BE flatten top-level qua get_repair_work_order; fallback `asset_info.
// risk_classification` = CÙNG giá trị nguồn, robust khi BE chưa flatten). Map sang VI
// qua SSoT `riskClassificationLabel` (Thấp/Trung bình/Cao/Nghiêm trọng) — KHÔNG dùng
// `risk_class` (Class I/II/III = đầu vào ma trận SLA, KHÔNG phải nhãn người dùng).
// Presence-aware (parity CMCreate/CalibrationCreate/AssetScanInfo): rỗng/whitespace/
// absent → 'Chưa phân loại' (phân biệt 'chưa phân loại' vs Class B — KHÔNG '—', KHÔNG
// default); drift ngoài enum → 'Khác' (riskClassificationLabel — KHÔNG leak EN thô).
const riskText = computed(() => {
  const raw = (wo.value?.risk_classification ?? wo.value?.asset_info?.risk_classification ?? '').trim()
  return raw ? riskClassificationLabel(raw) : 'Chưa phân loại'
})

// ─── SSoT server-driven CTA (GATE-8 / LL-FE-51 · mirror IncidentDetailView R3 +
// CalibrationDetailView) ──────────────────────────────────────────────────────
// Mọi nút chuyển-trạng-thái gate theo `allowed_transitions` do BE emit
// (_REPAIR_VALID_TRANSITIONS trong imm09.py) — KHÔNG hardcode `wo.status === 'X'`
// (hardcode = trộn luồng + lộ nút sai pha; đây chính là bug divergence RED của nút
// "Không thể sửa chữa" trước đây render ở MỌI state non-terminal). Mỗi canXxx =
// (capability && allowedTransitions.includes('<trạng-thái-đích>')). Capability khớp
// EXACT rbac.require BE: assign/diagnose/parts/complete-nav/cannot-repair =
// repair.create; xác nhận nghiệm thu (dept-head/QA) = repair.submit. Terminal
// (Completed/Cannot Repair/Cancelled) → allowed=[] → 0 nút CTA (chỉ còn nhãn tĩnh).
const allowedTransitions = computed<string[]>(() => wo.value?.allowed_transitions ?? [])
const canExecuteRepair = computed(() => can('repair.create'))
const canApproveRepair = computed(() => can('repair.submit'))

// ─── AC-CR-82 · CTA SERVER-DRIVEN (`available_actions`) ─────────────────────────
// Hợp đồng: `docs/imm-09/05_API_Specification.md §15` (ADR-IMM09-CTA-01/02/03) —
// `get_repair_work_order` phơi ĐÚNG 6 phần tử, thứ tự CỐ ĐỊNH [assign_technician,
// submit_diagnosis, request_spare_parts, start_repair, close_work_order,
// confirm_inspection], shape {key,label,route,enabled,reason} (route="").
// `enabled` = transition_allowed ∩ has_cap ∩ business_gate do SERVER quyết; `reason`
// là chuỗi VI SERVER trả (bất biến D9: enabled=false ⟺ reason≠""). FE CHỈ RENDER:
// nhãn/disabled/tooltip đều từ payload — KHÔNG bịa chuỗi, KHÔNG tự tính quyền, KHÔNG
// áp thêm điều kiện client cho 6 khoá này (MỘT TRỤC duy nhất).
//   • hết "nút chết": thiếu capability / sai pha ⇒ server trả enabled=false + lý do,
//     nút HIỆN nhưng KHÔNG bấm được (thay vì bấm rồi ăn 403/422 câm).
//   • hết "CTA ma": 'Cancelled' không có endpoint ⇒ server không phát ⇒ FE không vẽ
//     được nút huỷ phiếu.
// Thiếu khoá (worker BE chưa reload) hoặc mảng rỗng ⇒ null ⇒ rơi về FALLBACK
// (`allowed_transitions` ∩ `can()`) — KHÔNG nút nào biến mất, KHÔNG màn trắng.
const serverActions = computed<AvailableAction[] | null>(() => {
  const list = wo.value?.available_actions
  return Array.isArray(list) && list.length > 0 ? list : null
})
const isServerDriven = computed(() => serverActions.value !== null)
const actionMap = computed<Record<string, AvailableAction>>(() =>
  Object.fromEntries((serverActions.value ?? []).map((a) => [a.key, a])),
)

// Nhãn dự phòng CHỈ dùng khi server trả label rỗng (hợp đồng nói luôn có) — KHÔNG
// phải nguồn nhãn chính: nhãn hiển thị lấy từ `label` của server.
const CTA_LABEL_FALLBACK: Record<string, string> = {
  assign_technician: 'Phân công kỹ thuật viên',
  submit_diagnosis: 'Chẩn đoán',
  request_spare_parts: 'Quản lý vật tư',
  start_repair: 'Bắt đầu sửa chữa',
  close_work_order: 'Hoàn thành sửa chữa',
  confirm_inspection: 'Xác nhận nghiệm thu — Hoàn thành',
}
/** enabled server-quyết. `!!` chịu được cả bool lẫn 0|1 (quirk envelope Frappe). */
function srvEnabled(key: string): boolean {
  return !!actionMap.value[key]?.enabled
}
/** Lý do khoá — CHỈ khi server disable (D9 bảo đảm reason ≠ "" khi enabled=false). */
function srvReason(key: string): string {
  const a = actionMap.value[key]
  return a && !a.enabled ? (a.reason ?? '') : ''
}
function srvLabel(key: string): string {
  return actionMap.value[key]?.label?.trim() || CTA_LABEL_FALLBACK[key] || key
}
/** Nút "không thể sửa" DÙNG CHUNG khoá close_work_order (cùng endpoint, cannot_repair=1). */
const CTA_CANNOT_REPAIR_KEY = 'close_work_order'
// Danh sách lý do khoá dạng CHỮ (a11y: nút disabled KHÔNG nhận focus nên `title` một
// mình không đủ; WCAG 1.4.1 cũng cấm chỉ dựa màu). Dedupe theo key ⇒ close_work_order
// (2 nút) chỉ liệt kê 1 lần.
const blockedActions = computed<AvailableAction[]>(() =>
  (serverActions.value ?? []).filter((a) => !a.enabled && (a.reason ?? '') !== ''),
)
const hasEnabledServerAction = computed(() => (serverActions.value ?? []).some((a) => !!a.enabled))

// ─── FALLBACK: CTA gate theo (capability ∩ allowed_transitions) ─────────────────
// CHỈ chạy khi payload THIẾU `available_actions` (`!isServerDriven`) — worker BE chưa
// reload / client cũ. Khi BE phát available_actions, cụm server-driven thay thế TOÀN BỘ.
const canAssign = computed(() => !isServerDriven.value && canExecuteRepair.value && allowedTransitions.value.includes('Assigned'))
// Trang chẩn đoán khả dụng khi BE cho phép VÀO pha chẩn đoán: Assigned→'Diagnosing'
// hoặc đang Diagnosing (BE cho phép rời sang 'Pending Parts'). KHÔNG hiện ở Pending
// Inspection — allowed ở đó có 'In Repair' nhưng là đường TRẢ VỀ (nghiệm thu-fail),
// không phải chẩn đoán → dùng dấu hiệu riêng 'Diagnosing'/'Pending Parts'.
const canDiagnose = computed(() =>
  !isServerDriven.value &&
  canExecuteRepair.value &&
  (allowedTransitions.value.includes('Diagnosing') ||
    allowedTransitions.value.includes('Pending Parts')),
)
// "Bắt đầu" (Assigned→Diagnosing) vs "Cập nhật" (Diagnosing→…). CHỈ dùng cho đường
// FALLBACK — ở chế độ server-driven nhãn lấy TỪ `label` của server (hết suy diễn client).
const diagnoseLabel = computed(() =>
  allowedTransitions.value.includes('Diagnosing') ? 'Bắt đầu chẩn đoán' : 'Cập nhật chẩn đoán',
)
// Quản lý vật tư khả dụng khi BE cho phép VÀO 'In Repair' (từ Diagnosing / Pending
// Parts) — TRỪ pha Pending Inspection (nhận diện bằng có 'Completed' trong allowed)
// nơi hành động chính là nghiệm thu, không phải cấp vật tư.
const canManageParts = computed(() =>
  !isServerDriven.value &&
  canExecuteRepair.value &&
  allowedTransitions.value.includes('In Repair') &&
  !allowedTransitions.value.includes('Completed'),
)
const canCompleteRepair = computed(() => !isServerDriven.value && canExecuteRepair.value && allowedTransitions.value.includes('Pending Inspection'))
const canConfirmInspection = computed(() => !isServerDriven.value && canApproveRepair.value && allowedTransitions.value.includes('Completed'))
const canCannotRepair = computed(() => !isServerDriven.value && canExecuteRepair.value && allowedTransitions.value.includes('Cannot Repair'))

// `status` CHỈ dùng cho nhãn/banner hiển thị (display-only) — KHÔNG gate nút CTA nào.
const isTerminal = computed(() => ['Completed', 'Cannot Repair', 'Cancelled'].includes(wo.value?.status ?? ''))
const hasAnyCta = computed(() =>
  canAssign.value || canDiagnose.value || canManageParts.value ||
  canCompleteRepair.value || canConfirmInspection.value || canCannotRepair.value,
)
// Terminal ⇒ BE phát đủ 6 phần tử enabled=false ⇒ ẩn CẢ cụm (tránh 6 nút xám vô
// nghĩa), giữ nhãn tĩnh "Đã hoàn thành"/"Không thể sửa chữa"/"Đã huỷ". Vế
// `hasEnabledServerAction` là chốt an toàn: nếu server VẪN bật một hành động ở trạng
// thái terminal thì KHÔNG được nuốt nút (server là trục quyết định, không phải status).
const showServerCtaBar = computed(
  () => isServerDriven.value && (!isTerminal.value || hasEnabledServerAction.value),
)
// Gợi ý "không có hành động khả dụng" chỉ hiện khi màn KHÔNG nói gì khác: ở chế độ
// server-driven, danh sách `blockedActions` đã giải thích từng nút bị khoá.
const showNoCtaHint = computed(() =>
  !isTerminal.value &&
  (isServerDriven.value
    ? !hasEnabledServerAction.value && blockedActions.value.length === 0
    : !hasAnyCta.value),
)

// ─── Phiếu xuất kho của dòng vật tư (AC-CR-78 / INV-PARTS-1) ──────────────────
// BE là SSoT: `stock_entry_status` derive bằng CÙNG helper với validator BR-09-02
// (`services/imm09.py::validate_spare_parts_stock_entries`) ⇒ badge trên bảng LÀ TẤM
// GƯƠNG của điều kiện chặn submit, không phải một cách diễn giải thứ hai.
// FE KHÔNG tự suy diễn: từ phía client, mã phiếu TREO (bản ghi đã bị xoá) trông y hệt
// mã hợp lệ — trước vòng này dòng treo hiển thị XANH như hợp lệ rồi mới nổ 422 lúc submit.
// 'UNKNOWN' = worker BE chưa reload (2 khoá derived vắng mặt) → GIỮ NGUYÊN hành vi cũ.
type PartStockStatus = 'OK' | 'MISSING' | 'NOT_FOUND' | 'UNKNOWN'
function partStockStatus(p: SparePartRow): PartStockStatus {
  const s = p.stock_entry_status
  return s === 'OK' || s === 'MISSING' || s === 'NOT_FOUND' ? s : 'UNKNOWN'
}

// Số dòng vật tư chưa có phiếu xuất kho hợp lệ (BE aggregate; > 0 ⟺ BR-09-02 chặn submit).
// Khoá vắng mặt / không phải số / ≤ 0 → 0 ⇒ dải cảnh báo ẩn hoàn toàn.
const partsPendingStockEntry = computed(() => {
  const n = wo.value?.parts_pending_stock_entry
  return typeof n === 'number' && Number.isFinite(n) && n > 0 ? Math.trunc(n) : 0
})

// ─── AC-CR-84 · CỔNG ẢNH BẰNG CHỨNG NĐ98 (thiết bị nguy cơ cao) ────────────────
// Hợp đồng: `docs/imm-09/05_API_Specification.md §16` · FE spec `06_Frontend_Design.md
// §CMEvidencePhoto (U1/U2) · INV-CMEVID-1. SERVER là nơi CHẶN (`close_work_order` +
// `confirm_inspection` đọc CÙNG predicate SSoT `repair_evidence_missing_idxs`); màn này
// chỉ là TẤM GƯƠNG — FE KHÔNG dựng predicate thứ hai:
//   • KHÔNG suy "nguy cơ cao" từ `risk_class` (Class I/II/III — ánh xạ MẤT MÁT, chính là
//     lý do cổng ảnh từng là CODE CHẾT ở client mobile — CR-51/LL-BE-58) và cũng KHÔNG
//     tự đọc `risk_classification` để bật cổng: chỉ đọc cờ `evidence_photo_required`.
//   • KHÔNG đếm lại số mục thiếu ảnh từ `repair_checklist[].photo` — dùng NGUYÊN VĂN
//     `evidence_photo_missing_idxs` (đúng tập server từ chối) làm mẫu số/tử số.
//   • KHÔNG gate nút «Hoàn thành sửa chữa» ở client (xem cụm CTA server-driven AC-CR-82):
//     nút bật/tắt 100% theo `available_actions` — thêm điều kiện ảnh ở đây sẽ tạo GATE
//     THỨ HAI lệch pha với server.
// Vắng cả 3 khoá (worker BE chưa reload / client cũ) ⇒ `undefined` ⇒ ẩn TOÀN BỘ khối,
// KHÔNG khẳng định "đã đủ ảnh" và cũng KHÔNG suy "không có cổng" (chống lặp bug CR-51).
const evidenceGateApplies = computed(() => wo.value?.evidence_photo_required === 1)
const evidenceMissingIdxs = computed<number[]>(() => {
  const raw = wo.value?.evidence_photo_missing_idxs
  return Array.isArray(raw)
    ? raw.filter((n): n is number => typeof n === 'number' && Number.isFinite(n))
    : []
})
const evidenceTotalRequired = computed(() => {
  const n = wo.value?.evidence_photo_total_required
  return typeof n === 'number' && Number.isFinite(n) && n > 0 ? Math.trunc(n) : 0
})
/** Tử số = mẫu số − số mục thiếu (SSoT server, KHÔNG đếm lại phía client). */
const evidenceDoneCount = computed(() =>
  Math.max(0, evidenceTotalRequired.value - evidenceMissingIdxs.value.length),
)
const evidenceComplete = computed(
  () => evidenceGateApplies.value && evidenceMissingIdxs.value.length === 0,
)
/**
 * Mục thiếu ảnh hiển thị bằng `test_description` của ĐÚNG dòng `repair_checklist` khớp
 * `idx` — KHÔNG in số thứ tự kỹ thuật ra giao diện (idx là khoá máy, không phải ngôn ngữ
 * người dùng). Dòng không tra được mô tả (phiếu legacy) → nhãn trung tính tiếng Việt.
 */
const evidenceMissingItems = computed<{ idx: number; label: string }[]>(() =>
  evidenceMissingIdxs.value.map((idx) => {
    const row = wo.value?.repair_checklist?.find((r) => Number(r.idx) === idx)
    const desc = (row?.test_description ?? '').trim()
    return { idx, label: desc || 'Mục nghiệm thu chưa có mô tả' }
  }),
)
/** Dòng checklist này có nằm trong tập server báo thiếu ảnh không (chip U2). */
function isEvidenceMissing(idx: number): boolean {
  return evidenceGateApplies.value && evidenceMissingIdxs.value.includes(Number(idx))
}

// ─── Trạng thái vòng đời THỰC của thiết bị (BR-09-09 / INV-09-RESTORE-1) ───────
// Bind theo `asset_info.lifecycle_status` THẬT từ response — KHÔNG hardcode 'Active'.
// Sau khi đóng WO (complete_repair), asset CHỈ về 'Active' khi trước đó là 'Under
// Repair'; nếu đang giữ hold governance khác (vd 'Out of Service' do calib-fail/CAPA/
// incident) thì WO=Completed NHƯNG asset KHÔNG về Active → badge phải phản ánh đúng.
const assetLifecycleStatus = computed<string | null>(() => wo.value?.asset_info?.lifecycle_status ?? null)

// WO đã đóng (Completed) nhưng thiết bị KHÔNG ở 'Active' → còn hold hạng mục khác.
// Hiện note phụ nhắc xử lý riêng (không để user tưởng "đóng phiếu = thiết bị trở lại").
const showHoldNote = computed(() =>
  wo.value?.status === 'Completed' &&
  !!assetLifecycleStatus.value &&
  assetLifecycleStatus.value !== 'Active',
)

const elapsedDisplay = computed(() => {
  const h = Math.floor(elapsed.value / 3600)
  const m = Math.floor((elapsed.value % 3600) / 60)
  const s = elapsed.value % 60
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
})

const slaPercent = computed(() => {
  const w = wo.value
  if (!w?.open_datetime || !w.sla_target_hours) return 0
  const elapsedH = elapsed.value / 3600
  return Math.min(100, Math.round((elapsedH / w.sla_target_hours) * 100))
})

const slaBarColor = computed(() => {
  if (slaPercent.value >= 100) return 'bg-red-500'
  if (slaPercent.value >= 75) return 'bg-orange-400'
  if (slaPercent.value >= 50) return 'bg-yellow-400'
  return 'bg-green-400'
})

const slaTextColor = computed(() => {
  if (slaPercent.value >= 100) return 'text-red-600'
  if (slaPercent.value >= 75) return 'text-orange-500'
  return 'text-slate-600'
})

// ─── BR-09-10 / INV-CM-HOLD: đồng hồ SLA TẠM DỪNG khi WO chờ phụ tùng ──────────
// Khi `status === 'Pending Parts'` (chờ phụ tùng hết kho — blocker cung ứng ngoài
// tầm đội sửa), BE KHÔNG cộng khoảng này vào elapsed (SoT repair_elapsed_hours).
// FE phản ánh đúng: thay vì để live-timer chạy gây hiểu nhầm "đang trễ SLA", hiện
// badge VI giải thích đồng hồ đang dừng. KHÔNG tự tính lại — chỉ trình bày trạng thái.
const isOnPartsHold = computed(() => wo.value?.status === 'Pending Parts')

// ─── LIVE vượt SLA (CR-37 · BR-09-07 LIVE, INV parity list↔detail) ─────────────
// Badge/indicator đọc cờ LIVE `is_sla_breached ?? sla_breached` (live ưu tiên,
// fallback cờ thô STORED — forward-compat, đối xứng list CM đã dùng LIVE +
// cmSlaBreachedDivergence.test.ts case (C)). Chặn badge "Cam kết dịch vụ vi phạm"
// đọc cờ STORED `sla_breached` trễ 1 nhịp scheduler khi WO open-overdue vượt hạn
// nhưng cron chưa stamp (cận an-toàn người bệnh). WO đã đóng: live == cờ thô (equiv).
const isSlaBreached = computed(() => wo.value?.is_sla_breached ?? !!wo.value?.sla_breached)

// Actions
async function doAssign() {
  submitting.value = true
  const ok = await store.doAssignTechnician(wo.value!.name, assignEmail.value, assignPriority.value || undefined)
  submitting.value = false
  notifyResult(ok, MSG.UI_SAVE_SUCCESS, { entity: 'phân công kỹ thuật viên' })
  if (ok) showAssignModal.value = false
}

async function doCannotRepair() {
  submitting.value = true
  // CR-24 idempotency: khoá 1 lần cho mỗi lần bấm "Không thể sửa" (cùng endpoint
  // close_work_order). Ổn định qua auto-retry, đổi khi user chủ động thử lại.
  const clientRequestId = globalThis.crypto.randomUUID()
  const ok = await store.doCloseWorkOrder({
    name: wo.value!.name,
    repair_summary: '',
    root_cause_category: '',
    dept_head_name: '',
    checklist_results: [],
    cannot_repair: true,
    cannot_repair_reason: cannotReason.value,
    client_request_id: clientRequestId,
  })
  submitting.value = false
  notifyResult(ok, MSG.UI_SAVE_SUCCESS, { entity: 'trạng thái “Không thể sửa”' })
  if (ok) showCannotRepairModal.value = false
}

function navigateDiagnose() {
  router.push(`/cm/work-orders/${props.id}/diagnose`)
}

function navigateParts() {
  router.push(`/cm/work-orders/${props.id}/parts`)
}

function navigateChecklist() {
  router.push(`/cm/work-orders/${props.id}/checklist`)
}

async function doConfirmInspection() {
  submitting.value = true
  const ok = await store.doConfirmInspection(wo.value!.name)
  submitting.value = false
  notifyResult(ok, MSG.UI_SAVE_SUCCESS, { entity: 'nghiệm thu sửa chữa' })
}

// AC-CR-82 / D-CM-3 — «Bắt đầu sửa chữa» (endpoint `api/imm09.py:136` LIVE nhưng màn
// Chi tiết trước đây KHÔNG có đường vào: chỉ tới được từ CMPartsView). Nút này CHỈ
// render ở chế độ server-driven (đường fallback giữ nguyên hành vi cũ — không nút mới).
async function doStartRepairAction() {
  if (!wo.value) return
  starting.value = true
  const ok = await store.doStartRepair(wo.value.name)
  starting.value = false
  notifyResult(ok, MSG.UI_SAVE_SUCCESS, { entity: 'bắt đầu sửa chữa' })
}

// ─── AC-CR-82 · lớp RENDER cho 6 CTA server-driven (7 nút ↔ 6 khoá) ─────────────
// Bảng này chỉ quyết ĐỊNH DẠNG + đường thực thi FE (testid / lớp CSS / handler / cờ
// bận) — KHÔNG quyết `enabled` (đó là việc của SERVER). Mỗi `key` ánh xạ 1-1 tới ĐÚNG
// 1 endpoint whitelisted của assetcore/api/imm09.py. `close_work_order` xuất hiện 2
// lần (hoàn thành / không thể sửa) vì CÙNG endpoint, khác cờ `cannot_repair` ⇒ 2 nút
// bật-tắt THEO CÙNG một action object (không thể lệch nhau).
// Thứ tự hiển thị giữ nguyên luồng UI hiện có, chèn «Bắt đầu sửa chữa» sau «Quản lý
// vật tư» — thứ tự MẢNG do server phát vẫn là hợp đồng dữ liệu, không phải thứ tự vẽ.
interface CmCtaSpec {
  testid: string
  key: string
  cls: string
  run: () => void
  busy: boolean
  /**
   * Nhãn RIÊNG cho nút khi 2 nút DÙNG CHUNG một khoá server (`close_work_order`):
   * server chỉ phát ĐƯỢC 1 nhãn cho 1 khoá, nhưng «Hoàn thành sửa chữa» và «Không thể
   * sửa chữa» là 2 lối vào KHÁC NGHĨA của cùng endpoint (khác cờ `cannot_repair`).
   * Không có override ⇒ 2 nút hiện y hệt chữ (bug lộ ra khi RENDER THẬT). Đây là
   * biến thể HIỂN THỊ — KHÔNG đụng `enabled`/`reason` (vẫn 100% do server quyết).
   */
  labelOverride?: string
}
const serverCtaSpecs = computed<CmCtaSpec[]>(() => [
  {
    testid: 'cta-assign', key: 'assign_technician',
    cls: 'bg-blue-600 hover:bg-blue-700 focus-visible:ring-blue-500 text-white',
    run: () => { showAssignModal.value = true }, busy: false,
  },
  {
    testid: 'cta-diagnose', key: 'submit_diagnosis',
    cls: 'bg-purple-600 hover:bg-purple-700 focus-visible:ring-purple-500 text-white',
    run: navigateDiagnose, busy: false,
  },
  {
    testid: 'cta-parts', key: 'request_spare_parts',
    cls: 'bg-orange-600 hover:bg-orange-700 focus-visible:ring-orange-500 text-white',
    run: navigateParts, busy: false,
  },
  {
    testid: 'cta-start-repair', key: 'start_repair',
    cls: 'bg-emerald-600 hover:bg-emerald-700 focus-visible:ring-emerald-500 text-white',
    run: () => { void doStartRepairAction() }, busy: starting.value,
  },
  {
    testid: 'cta-complete', key: 'close_work_order',
    cls: 'bg-green-600 hover:bg-green-700 focus-visible:ring-green-500 text-white',
    run: navigateChecklist, busy: false, labelOverride: 'Hoàn thành sửa chữa',
  },
  {
    testid: 'cta-confirm-inspection', key: 'confirm_inspection',
    cls: 'bg-cyan-600 hover:bg-cyan-700 focus-visible:ring-cyan-500 text-white',
    run: () => { void doConfirmInspection() }, busy: submitting.value,
  },
  {
    testid: 'cta-cannot-repair', key: CTA_CANNOT_REPAIR_KEY,
    cls: 'border border-red-300 text-red-600 hover:bg-red-50 focus-visible:ring-red-400',
    run: () => { showCannotRepairModal.value = true }, busy: false,
    labelOverride: 'Không thể sửa chữa',
  },
])
/** Nhãn hiển thị: override HIỂN THỊ (nếu có) > nhãn SERVER > hằng dự phòng FE. */
function ctaLabel(spec: CmCtaSpec): string {
  return spec.labelOverride || srvLabel(spec.key)
}
/** Bấm = no-op khi server khoá hoặc đang bận (phòng thủ kép với `:disabled`). */
function runServerCta(spec: CmCtaSpec): void {
  if (!srvEnabled(spec.key) || spec.busy) return
  spec.run()
}
</script>

<template>
  <div class="p-6">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-5">
      <button class="text-slate-400 hover:text-slate-600" @click="router.push('/cm/work-orders')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div class="flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-mono text-lg font-bold text-slate-900">{{ wo?.name }}</span>
          <span v-if="wo" :class="['px-2.5 py-1 rounded-full text-xs font-semibold', cmStatusClass(wo.status)]">{{ cmStatusLabel(wo.status) }}</span>
          <span v-if="wo?.is_repeat_failure" class="px-2 py-0.5 rounded-full text-xs bg-amber-100 text-amber-700 font-medium">Tái hỏng</span>
          <span v-if="isSlaBreached" data-testid="cm-sla-breach-badge" class="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 font-semibold">Cam kết dịch vụ vi phạm</span>
          <!-- Trạng thái vòng đời THỰC của thiết bị (BR-09-09) — bind giá trị thật, không hardcode -->
          <span
            v-if="assetLifecycleStatus"
            :class="['px-2 py-0.5 rounded-full text-xs font-medium', lifecycleStatusClass(assetLifecycleStatus)]"
            :title="`Trạng thái thiết bị: ${assetLifecycleStatus}`"
            data-testid="asset-lifecycle-badge"
          >
            Thiết bị: {{ lifecycleStatusLabel(assetLifecycleStatus) }}
          </span>
        </div>
        <div class="text-sm text-slate-500 mt-0.5">{{ wo?.asset_name || wo?.asset_ref }}</div>
      </div>
    </div>

    <div v-if="store.loading && !wo" class="space-y-4">
      <div class="bg-white rounded-xl border p-5 animate-pulse">
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div v-for="i in 6" :key="i" class="h-5 bg-slate-100 rounded" />
        </div>
      </div>
      <div class="bg-white rounded-xl border p-5 animate-pulse h-40" />
    </div>
    <!-- Nạp thất bại (403 thiếu quyền / 404 / lỗi khác) — empty-state CHUNG, có lối
         thoát, 0 CTA render (CR-74 · chống dead-control). -->
    <DetailLoadError
      v-else-if="loadBlocked"
      :kind="loadErrorKindRef || 'unknown'"
      entity-label="lệnh sửa chữa"
      :record-id="props.id"
      :message="loadErrMsg"
      back-label="Về danh sách sửa chữa"
      @retry="store.fetchWorkOrder(props.id)"
      @back="router.push('/cm/work-orders')"
    />
    <template v-else-if="wo">
      <!-- Thanh tab: gác theo CÙNG điều kiện `wo` như khối liên quan cũ ⇒ chưa tải xong
           hoặc bị chặn đọc thì KHÔNG có nút tab chết. Modal nằm NGOÀI 2 panel (nếu nằm
           trong panel v-show sẽ bị display:none nuốt mất). -->
      <DetailTabBar v-model="activeTab" :tabs="DETAIL_TABS" />

      <div v-show="activeTab === 'detail'" data-testid="tab-panel-detail" class="grid grid-cols-1 md:grid-cols-5 gap-6">
      <!-- LEFT PANEL (60%) -->
      <div class="md:col-span-3 space-y-5">
        <!-- Asset Info -->
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Thông tin thiết bị</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div class="col-span-2">
              <span class="text-slate-500">Thiết bị:</span>
              <span class="font-semibold ml-1">{{ wo.asset_name || wo.asset_ref }}</span>
              <span v-if="wo.asset_name" class="ml-2 text-xs text-slate-400 font-mono">{{ wo.asset_ref }}</span>
            </div>
            <div v-if="wo.department_name"><span class="text-slate-500">Khoa:</span> <span class="font-medium">{{ wo.department_name }}</span></div>
            <div v-if="wo.location_name"><span class="text-slate-500">Vị trí:</span> <span class="font-medium">{{ wo.location_name }}</span></div>
            <div><span class="text-slate-500">Số serial:</span> <span class="font-mono text-xs">{{ wo.serial_no || '—' }}</span></div>
            <div><span class="text-slate-500">Phân loại rủi ro:</span> <span class="font-medium" data-testid="wo-risk-classification">{{ riskText }}</span></div>
            <div><span class="text-slate-500">Loại sửa chữa:</span> <span class="font-medium">{{ repairTypeLabel(wo.repair_type) }}</span></div>
            <div>
              <span class="text-slate-500">Ưu tiên:</span>
              <span :class="['ml-1 px-1.5 py-0.5 rounded text-xs font-medium', priorityClass(wo.priority)]">{{ priorityLabel(wo.priority) }}</span>
            </div>
          </div>

          <!-- Source badge — clickable cross-module nav -->
          <div class="mt-3 flex gap-2 flex-wrap">
            <router-link
              v-if="wo.incident_report"
              :to="`/incidents/${wo.incident_report}`"
              class="text-xs bg-purple-100 text-purple-700 hover:bg-purple-200 px-2 py-1 rounded-full transition-colors"
              title="Mở báo cáo sự cố nguồn"
            >
Sự cố {{ wo.incident_report }} →
</router-link>
            <router-link
              v-if="wo.source_pm_wo"
              :to="`/pm/work-orders/${wo.source_pm_wo}`"
              class="text-xs bg-blue-100 text-blue-700 hover:bg-blue-200 px-2 py-1 rounded-full transition-colors"
              title="Mở phiếu bảo trì gốc"
            >
Phiếu bảo trì {{ wo.source_pm_wo }} →
</router-link>
          </div>
        </div>

        <!-- Diagnosis -->
        <div v-if="wo.diagnosis_notes" class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="font-semibold text-slate-700 mb-2 text-sm uppercase tracking-wide">Chẩn đoán</h2>
          <div class="text-sm text-slate-600 whitespace-pre-wrap">{{ wo.diagnosis_notes }}</div>
          <div v-if="wo.root_cause_category" class="mt-2">
            <span class="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">{{ rootCauseLabel(wo.root_cause_category) }}</span>
          </div>
        </div>

        <!-- Spare Parts -->
        <div v-if="wo.spare_parts_used?.length" class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">
            Vật tư sử dụng ({{ wo.spare_parts_used.length }} mục)
          </h2>

          <!-- AC-CR-78: cảnh báo TRƯỚC khi submit (BE aggregate = số dòng stock_entry_ok 0).
               > 0 ⟺ validator BR-09-02 sẽ chặn hoàn tất phiếu. Ẩn hoàn toàn khi = 0/vắng mặt. -->
          <div
            v-if="partsPendingStockEntry > 0"
            role="alert"
            data-testid="parts-pending-banner"
            class="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            Còn {{ partsPendingStockEntry }} dòng vật tư chưa có phiếu xuất kho hợp lệ — chưa thể hoàn tất phiếu sửa chữa.
          </div>

          <div class="overflow-x-auto">
<table class="w-full text-sm">
            <thead class="bg-slate-50">
              <tr>
                <th class="text-left px-3 py-2 text-xs font-medium text-slate-500">Vật tư</th>
                <th class="text-right px-3 py-2 text-xs font-medium text-slate-500">Số lượng</th>
                <th class="text-right px-3 py-2 text-xs font-medium text-slate-500">Thành tiền</th>
                <th class="text-center px-3 py-2 text-xs font-medium text-slate-500">Phiếu xuất kho</th>
              </tr>
            </thead>
            <tbody class="divide-y">
              <tr v-for="p in wo.spare_parts_used" :key="p.idx">
                <td class="px-3 py-2">
                  <div class="font-medium">{{ p.item_name }}</div>
                  <div class="text-xs text-slate-400 font-mono">{{ p.item_code }}</div>
                </td>
                <td class="px-3 py-2 text-right text-slate-600">{{ p.qty }} {{ p.uom }}</td>
                <td class="px-3 py-2 text-right text-slate-600">{{ p.total_cost?.toLocaleString('vi-VN') }}đ</td>
                <!-- AC-CR-78: 3 trạng thái THẬT theo SSoT BE, không suy diễn từ sự có mặt của mã.
                     Nhãn chữ đầy đủ (KHÔNG chỉ phân biệt bằng màu — WCAG 2.1 AA 1.4.1). -->
                <td class="px-3 py-2 text-center" data-testid="part-stock-cell">
                  <template v-if="partStockStatus(p) === 'OK'">
                    <span class="text-emerald-700 text-xs font-mono">{{ p.stock_entry_ref }}</span>
                  </template>
                  <template v-else-if="partStockStatus(p) === 'MISSING'">
                    <span class="text-red-600 text-xs">Chưa có phiếu xuất kho</span>
                  </template>
                  <template v-else-if="partStockStatus(p) === 'NOT_FOUND'">
                    <span class="text-red-700 text-xs font-semibold">Phiếu xuất kho không tồn tại</span>
                    <span class="block text-red-500 text-xs font-mono line-through">{{ p.stock_entry_ref }}</span>
                  </template>
                  <!-- Worker BE chưa reload (thiếu khoá derived) → giữ ĐÚNG hành vi trước vòng. -->
                  <template v-else>
                    <span v-if="p.stock_entry_ref" class="text-emerald-700 text-xs font-mono">{{ p.stock_entry_ref }}</span>
                    <span v-else class="text-red-600 text-xs">Chưa có</span>
                  </template>
                </td>
              </tr>
            </tbody>
            <tfoot class="bg-slate-50">
              <tr>
                <td colspan="2" class="px-3 py-2 text-sm text-slate-500 text-right font-medium">Tổng:</td>
                <td class="px-3 py-2 text-right font-semibold text-slate-900">{{ wo.total_parts_cost?.toLocaleString('vi-VN') }}đ</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
      </div>
        </div>

        <!-- AC-CR-84 · ẢNH BẰNG CHỨNG NĐ98 (U1) — CHỈ render khi SERVER nói cổng áp dụng
             (`evidence_photo_required === 1`, tức thiết bị nhóm nguy cơ cao). Thiết bị
             Thấp/Trung bình/chưa phân loại ⇒ 0 nhiễu. Vắng khoá (worker BE chưa reload)
             ⇒ cũng KHÔNG render (không khẳng định gì). Số liệu lấy NGUYÊN VĂN từ server —
             FE không đếm lại từ `repair_checklist[].photo`. -->
        <div
          v-if="evidenceGateApplies"
          data-testid="cm-evidence-card"
          role="region"
          aria-labelledby="cm-evidence-title"
          :class="[
            'rounded-xl shadow-sm border p-5',
            evidenceComplete ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200',
          ]"
        >
          <h2 id="cm-evidence-title" class="font-semibold text-slate-700 text-sm uppercase tracking-wide">
            Ảnh bằng chứng (NĐ98)
          </h2>
          <!-- Nhãn CHỮ đầy đủ, không chỉ phân biệt bằng màu nền (WCAG 2.1 AA 1.4.1). -->
          <p
            data-testid="cm-evidence-headline"
            :class="['mt-2 text-sm font-medium', evidenceComplete ? 'text-emerald-800' : 'text-amber-900']"
          >
            <template v-if="evidenceComplete">
              Bằng chứng NĐ98: đã có ảnh {{ evidenceDoneCount }}/{{ evidenceTotalRequired }} mục
            </template>
            <template v-else>
              Bằng chứng NĐ98: còn {{ evidenceMissingIdxs.length }}/{{ evidenceTotalRequired }} mục chưa có ảnh — cần đính đủ trước khi hoàn thành sửa chữa
            </template>
          </p>
          <p v-if="!evidenceComplete" data-testid="cm-evidence-progress" class="mt-1 text-sm text-amber-900">
            Đã có {{ evidenceDoneCount }}/{{ evidenceTotalRequired }} mục có ảnh.
          </p>

          <!-- Mục còn thiếu — nêu ĐÍCH DANH bằng mô tả mục nghiệm thu (không in số thứ tự
               kỹ thuật), để người dùng biết phải chụp cái gì. -->
          <div v-if="evidenceMissingItems.length" class="mt-3">
            <p class="text-xs font-semibold text-amber-900">Các mục nghiệm thu còn thiếu ảnh:</p>
            <ul data-testid="cm-evidence-missing-list" class="mt-1 space-y-1">
              <li
                v-for="m in evidenceMissingItems"
                :key="`cm-evidence-missing-${m.idx}`"
                class="flex items-start gap-1.5 text-sm text-amber-900"
              >
                <span aria-hidden="true">•</span>
                <span>{{ m.label }}</span>
              </li>
            </ul>
          </div>

          <!-- ĐƯỜNG KHẮC PHỤC (chống dead-end): mở luồng đính ảnh SẴN CÓ ở màn nghiệm thu
               (mỗi mục có nút tải ảnh lên — GATE-9). Lý do chặn luôn đi kèm lối ra. -->
          <button
            v-if="!evidenceComplete"
            type="button"
            data-testid="cm-evidence-attach-cta"
            class="mt-3 inline-flex items-center rounded-lg border border-amber-400 bg-white px-3 py-1.5 text-sm font-medium text-amber-900 transition-colors hover:bg-amber-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
            @click="navigateChecklist"
          >
            Đính ảnh bằng chứng
          </button>
        </div>

        <!-- Repair Checklist -->
        <div v-if="wo.repair_checklist?.length" class="bg-white rounded-xl shadow-sm border p-5">
          <div class="flex items-center justify-between mb-3">
            <h2 class="font-semibold text-slate-700 text-sm uppercase tracking-wide">Checklist nghiệm thu</h2>
            <span class="text-xs text-slate-500">
              {{ wo.repair_checklist.filter(r => r.result === 'Pass').length }}/{{ wo.repair_checklist.length }} Đạt
            </span>
          </div>
          <!-- Progress -->
          <div class="h-1.5 bg-slate-100 rounded-full mb-4 overflow-hidden">
            <div
              class="h-1.5 bg-green-500 rounded-full"
              :style="{ width: `${Math.round(wo.repair_checklist.filter(r => r.result === 'Pass').length / wo.repair_checklist.length * 100)}%` }"
            />
          </div>
          <div class="space-y-2">
            <div
              v-for="item in wo.repair_checklist"
              :key="item.idx"
              :class="[
                'flex items-start gap-3 p-3 rounded-lg border',
                item.result === 'Pass' ? 'bg-green-50 border-green-200' :
                item.result === 'Fail' ? 'bg-red-50 border-red-200' :
                item.result === 'N/A' ? 'bg-slate-50 border-slate-200' : 'border-slate-200'
              ]"
            >
              <span
:class="[
                'shrink-0 px-1.5 py-0.5 rounded text-xs font-bold',
                item.result === 'Pass' ? 'bg-green-500 text-white' :
                item.result === 'Fail' ? 'bg-red-500 text-white' :
                item.result === 'N/A' ? 'bg-slate-400 text-white' : 'bg-slate-200 text-slate-500'
              ]">{{ item.result ? resultLabel(item.result) : '?' }}</span>
              <div>
                <div class="text-sm text-slate-800">{{ item.test_description }}</div>
                <div class="text-xs text-slate-400">{{ item.test_category }}</div>
                <div v-if="item.notes" class="text-xs text-slate-600 mt-1 italic">{{ item.notes }}</div>
                <!-- AC-CR-84 (U2) — dòng nằm trong tập SERVER báo thiếu ảnh. Nhãn CHỮ
                     (không chỉ màu); nguồn là `evidence_photo_missing_idxs`, KHÔNG suy từ
                     `item.photo` (một predicate, nhiều nơi đọc). -->
                <span
                  v-if="isEvidenceMissing(item.idx)"
                  data-testid="cm-evidence-missing-chip"
                  class="mt-1.5 inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
                >
                  Chưa có ảnh bằng chứng
                </span>
                <!-- Ảnh bằng chứng mục (NĐ98 Class C/D) — read-only cho QL/Kiểm toán xem.
                     photo null/'' → không render (không crash). -->
                <a
                  v-if="item.photo"
                  :href="item.photo"
                  target="_blank"
                  rel="noopener"
                  class="inline-block mt-2 rounded-lg overflow-hidden border border-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
                  :aria-label="`Xem ảnh bằng chứng mục #${item.idx}`"
                >
                  <img
                    :src="item.photo"
                    :alt="`Ảnh bằng chứng mục #${item.idx} — ${item.test_description}`"
                    class="h-20 w-20 object-cover"
                    loading="lazy"
                  >
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT PANEL (40%) -->
      <div class="md:col-span-2 space-y-4">
        <!-- SLA Indicator -->
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="font-semibold text-slate-700 mb-3 text-sm">Chỉ số cam kết dịch vụ</h2>

          <!-- WO đã đóng: kết quả cuối, không có timer/progress -->
          <template v-if="['Completed', 'Cannot Repair', 'Cancelled'].includes(wo.status)">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-slate-500">Thời gian sửa chữa</span>
              <span class="text-xs text-slate-500">Mục tiêu cam kết mức dịch vụ</span>
            </div>
            <div class="flex items-center justify-between mb-3">
              <span :class="['text-xl font-bold font-mono', isSlaBreached ? 'text-red-600' : 'text-emerald-600']">
                {{ wo.mttr_hours != null ? `${wo.mttr_hours}h` : '—' }}
              </span>
              <span class="text-slate-400 text-sm">/</span>
              <span class="text-xl font-bold font-mono text-slate-700">{{ wo.sla_target_hours ?? '—' }}h</span>
            </div>
            <div class="flex items-center justify-center gap-2 py-2 rounded-lg"
                 :class="isSlaBreached ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">
              <span class="text-base font-semibold">
                {{ isSlaBreached ? '✗ Vi phạm cam kết dịch vụ' : '✓ Đạt cam kết dịch vụ' }}
              </span>
            </div>
            <div v-if="wo.status !== 'Completed'" class="text-xs text-center text-slate-400 mt-2">
              ({{ wo.status === 'Cancelled' ? 'Phiếu đã huỷ' : 'Không thể sửa chữa' }})
            </div>
          </template>

          <!-- WO chờ phụ tùng (BR-09-10): đồng hồ SLA TẠM DỪNG — không hiện progress chạy -->
          <template v-else-if="isOnPartsHold">
            <div
              role="alert"
              aria-live="polite"
              data-testid="parts-hold-banner"
              class="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800"
            >
              <svg class="w-4 h-4 mt-0.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p class="text-sm font-semibold">Chờ phụ tùng — cam kết dịch vụ tạm dừng</p>
                <p class="text-xs mt-0.5 text-amber-700">
                  Đồng hồ cam kết dịch vụ/thời gian sửa chữa trung bình đang dừng trong thời gian chờ phụ tùng hết kho;
                  khoảng này không tính vào thời gian sửa chữa.
                </p>
              </div>
            </div>
            <div class="flex items-center justify-between mt-3 text-xs text-slate-500">
              <span>Mục tiêu cam kết mức dịch vụ</span>
              <span class="font-mono font-semibold text-slate-700">{{ wo.sla_target_hours ?? '—' }}h</span>
            </div>
          </template>

          <!-- WO active: timer + progress bar -->
          <template v-else>
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs text-slate-500">Đã trôi: {{ (elapsed / 3600).toFixed(1) }}h / {{ wo.sla_target_hours || '—' }}h cam kết dịch vụ</span>
              <span :class="['text-xs font-semibold', slaTextColor]">{{ slaPercent }}%</span>
            </div>
            <div class="h-3 bg-slate-100 rounded-full overflow-hidden mb-2">
              <div :class="['h-3 rounded-full transition-all', slaBarColor]" :style="{ width: `${slaPercent}%` }" />
            </div>
            <div class="text-center font-mono text-xl font-bold text-slate-700 mt-2">{{ elapsedDisplay }}</div>
          </template>
        </div>

        <!-- Kỹ thuật viên & Timeline -->
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="font-semibold text-slate-700 mb-3 text-sm">Trạng thái</h2>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-slate-500">Kỹ thuật viên:</span>
              <span class="font-medium" :title="wo.assigned_to || ''">{{ wo.assigned_to_name || wo.assigned_to || '—' }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Mở lúc:</span>
              <span class="text-slate-700">{{ wo.open_datetime?.slice(0,16) }}</span>
            </div>
            <div v-if="wo.assigned_datetime" class="flex justify-between">
              <span class="text-slate-500">Phân công:</span>
              <span class="text-slate-700">{{ wo.assigned_datetime?.slice(0,16) }}</span>
            </div>
            <div v-if="wo.completion_datetime" class="flex justify-between">
              <span class="text-slate-500">Hoàn thành:</span>
              <span class="text-slate-700">{{ wo.completion_datetime?.slice(0,16) }}</span>
            </div>
            <div v-if="wo.mttr_hours" class="flex justify-between">
              <span class="text-slate-500">Thời gian sửa chữa:</span>
              <span :class="['font-semibold', isSlaBreached ? 'text-red-600' : 'text-green-600']">{{ wo.mttr_hours }}h</span>
            </div>
          </div>

          <!-- BR-09-09: WO đã đóng nhưng thiết bị vẫn giữ hold hạng mục khác (không về Active) -->
          <div
            v-if="showHoldNote"
            class="mt-3 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800"
            data-testid="asset-hold-note"
          >
            Thiết bị giữ trạng thái
            <b>{{ lifecycleStatusLabel(assetLifecycleStatus!) }}</b>
            do hạng mục khác — cần xử lý riêng (phiếu sửa chữa đã hoàn thành nhưng chưa giải toả hold).
          </div>
        </div>

        <!-- Action Bar -->
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="font-semibold text-slate-700 mb-3 text-sm">Thao tác</h2>
          <div class="space-y-2">
            <!-- AC-CR-82 — CỤM CTA SERVER-DRIVEN (GATE-8 / LL-FE-51 · hợp đồng
                 ADR-IMM09-CTA-01/02/03 @ docs/imm-09/05_API_Specification.md §15).
                 MỘT TRỤC DUY NHẤT: `enabled`/`reason`/`label` đều của SERVER
                 (`available_actions`) — FE KHÔNG cộng thêm điều kiện client, KHÔNG
                 gate bằng `wo.status === 'X'`, KHÔNG suy từ tên vai trò.
                 Nút thiếu quyền/sai pha vẫn HIỆN (disabled + lý do tiếng Việt) thay vì
                 biến mất hoặc bấm-rồi-ăn-403; 'Cancelled' không có endpoint ⇒ server
                 không phát ⇒ không thể vẽ nút huỷ phiếu.
                 Payload thiếu `available_actions` ⇒ khối này KHÔNG render, cụm FALLBACK
                 bên dưới giữ NGUYÊN hành vi cũ (worker BE chưa reload / client cũ). -->
            <template v-if="showServerCtaBar">
              <div data-testid="cm-cta-bar" class="space-y-2">
                <template v-for="spec in serverCtaSpecs" :key="spec.testid">
                  <button
                    type="button"
                    :data-testid="spec.testid"
                    :data-action-key="spec.key"
                    :class="['w-full px-4 py-2.5 rounded-lg text-sm font-medium transition-colors focus-visible:ring-2 disabled:opacity-50 disabled:cursor-not-allowed', spec.cls]"
                    :disabled="!srvEnabled(spec.key) || spec.busy"
                    :aria-disabled="srvEnabled(spec.key) ? undefined : 'true'"
                    :title="srvReason(spec.key) || undefined"
                    :aria-label="srvReason(spec.key)
                      ? `${ctaLabel(spec)} — không khả dụng: ${srvReason(spec.key)}`
                      : ctaLabel(spec)"
                    :aria-describedby="srvReason(spec.key) ? `cm-cta-reason-${spec.key}` : undefined"
                    @click="runServerCta(spec)"
                  >
                    {{ spec.busy ? 'Đang xử lý…' : ctaLabel(spec) }}
                  </button>
                  <p v-if="spec.testid === 'cta-confirm-inspection'" class="text-[11px] text-center text-slate-400">
                    Yêu cầu quyền phê duyệt cấp khoa/đảm bảo chất lượng. Sau bước này thời gian sửa chữa trung bình &amp; cam kết dịch vụ được chốt.
                  </p>
                </template>
              </div>
              <!-- Lý do khoá dạng CHỮ (KHÔNG chỉ tooltip/màu) — nút disabled không nhận
                   focus nên screen-reader không đọc được `title` (WCAG 2.1 AA). -->
              <ul v-if="blockedActions.length" data-testid="cm-cta-reasons" aria-live="polite" class="mt-3 space-y-1">
                <li
                  v-for="a in blockedActions"
                  :id="`cm-cta-reason-${a.key}`"
                  :key="`cm-cta-reason-${a.key}`"
                  class="flex items-start gap-1.5 text-xs text-slate-500"
                >
                  <span aria-hidden="true">🔒</span>
                  <span><span class="font-medium">{{ srvLabel(a.key) }}:</span> {{ a.reason }}</span>
                </li>
              </ul>
            </template>

            <!-- FALLBACK (payload THIẾU `available_actions`) — gate theo
                 (capability ∩ allowed_transitions BE), KHÔNG hardcode wo.status === 'X'
                 (GATE-8 / LL-FE-51). Giữ NGUYÊN hợp đồng cũ để BE stale không làm mất nút. -->

            <!-- → Assigned: phân công KTV (modal) -->
            <button
              v-if="canAssign"
              data-testid="cta-assign"
              class="w-full px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
              @click="showAssignModal = true">
              Phân công kỹ thuật viên
            </button>

            <!-- → Diagnosing / In Repair / Pending Parts: trang chẩn đoán -->
            <button
              v-if="canDiagnose"
              data-testid="cta-diagnose"
              class="w-full px-4 py-2.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 focus-visible:ring-2 focus-visible:ring-purple-500 transition-colors"
              @click="navigateDiagnose">
              {{ diagnoseLabel }}
            </button>

            <!-- → In Repair: quản lý vật tư -->
            <button
              v-if="canManageParts"
              data-testid="cta-parts"
              class="w-full px-4 py-2.5 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700 focus-visible:ring-2 focus-visible:ring-orange-500 transition-colors"
              @click="navigateParts">
              Quản lý vật tư
            </button>

            <!-- → Pending Inspection: hoàn thành sửa chữa (trang checklist) -->
            <button
              v-if="canCompleteRepair"
              data-testid="cta-complete"
              class="w-full px-4 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 focus-visible:ring-2 focus-visible:ring-green-500 transition-colors"
              @click="navigateChecklist">
              Hoàn thành sửa chữa
            </button>

            <!-- → Completed: xác nhận nghiệm thu (QA / trưởng khoa = repair.submit) -->
            <template v-if="canConfirmInspection">
              <button
                data-testid="cta-confirm-inspection"
                class="w-full px-4 py-2.5 bg-cyan-600 text-white rounded-lg text-sm font-medium hover:bg-cyan-700 focus-visible:ring-2 focus-visible:ring-cyan-500 disabled:opacity-50 transition-colors"
                :disabled="submitting"
                @click="doConfirmInspection">
                {{ submitting ? 'Đang xử lý...' : 'Xác nhận nghiệm thu — Hoàn thành' }}
              </button>
              <p class="text-[11px] text-center text-slate-400 mt-1">
                Yêu cầu quyền phê duyệt cấp khoa/đảm bảo chất lượng. Sau bước này thời gian sửa chữa trung bình & cam kết dịch vụ được chốt.
              </p>
            </template>

            <!-- → Cannot Repair: chỉ render khi BE cho phép chuyển 'Cannot Repair'
                 (theo _REPAIR_VALID_TRANSITIONS: chỉ In Repair). KHÔNG render ở
                 Open/Assigned/Diagnosing/Pending Parts (BE cấm) — đây là fix divergence RED. -->
            <button
              v-if="canCannotRepair"
              data-testid="cta-cannot-repair"
              class="w-full px-4 py-2.5 border border-red-300 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-400 transition-colors"
              @click="showCannotRepairModal = true">
              Không thể sửa chữa
            </button>

            <!-- Nhãn trạng thái terminal (hiển thị TĨNH — KHÔNG phải CTA) -->
            <div v-if="wo.status === 'Completed'" class="text-center py-2 text-emerald-600 font-semibold text-sm">
              Đã hoàn thành
            </div>
            <div v-if="wo.status === 'Cannot Repair'" class="text-center py-2 text-red-600 font-semibold text-sm">
              Không thể sửa chữa
            </div>
            <div v-if="wo.status === 'Cancelled'" class="text-center py-2 text-slate-500 font-semibold text-sm">
              Đã huỷ
            </div>

            <!-- Non-terminal nhưng không có CTA khả dụng (thiếu quyền) — LL-FE-23/26.
                 Ở chế độ server-driven, `blockedActions` đã nêu lý do từng nút ⇒ chỉ
                 hiện gợi ý này khi màn KHÔNG nói gì khác. -->
            <div
              v-if="showNoCtaHint"
              class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2"
            >
              Không có hành động khả dụng cho vai trò hiện tại. Liên hệ quản trị để cấp quyền sửa chữa phù hợp.
            </div>
          </div>
        </div>

        <!-- Vật tư summary (right panel) -->
        <div class="bg-white rounded-xl shadow-sm border p-4 text-sm">
          <div class="flex justify-between text-slate-500">
            <span>Vật tư:</span>
            <!-- AC-CR-78: nêu luôn số dòng chưa xuất kho ở panel tóm tắt (chỉ khi > 0). -->
            <span class="font-medium text-slate-900" data-testid="parts-summary">
              {{ wo.spare_parts_used?.length || 0 }} mục<span
                v-if="partsPendingStockEntry > 0"
                class="text-red-600"
              > ({{ partsPendingStockEntry }} chưa xuất kho)</span>
            </span>
          </div>
          <div v-if="wo.total_parts_cost" class="flex justify-between text-slate-500 mt-1">
            <span>Chi phí:</span>
            <span class="font-medium text-slate-900">{{ wo.total_parts_cost.toLocaleString('vi-VN') }}đ</span>
          </div>
          <div class="flex justify-between text-slate-500 mt-1">
            <span>Checklist:</span>
            <span class="font-medium text-slate-900">{{ wo.repair_checklist?.filter(r => r.result === 'Pass').length || 0 }}/{{ wo.repair_checklist?.length || 0 }} Đạt</span>
          </div>
        </div>
      </div>
      </div>

      <!-- Bản ghi liên quan: TAB RIÊNG, mount LƯỜI (v-if) — nội dung do đồ thị liên kết
           ở backend quyết định. -->
      <div v-if="activeTab === 'related'" data-testid="tab-panel-related">
        <RelatedRecords doctype="Asset Repair" :name="wo.name" />
      </div>
    </template>

    <!-- Assign Modal -->
    <Transition name="fade">
    <div v-if="showAssignModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="font-bold text-lg mb-4">Phân công kỹ thuật viên</h3>
        <div class="space-y-3 mb-5">
          <div>
            <!-- Picker user AssetCore ĐỦ NĂNG LỰC sửa chữa (Repair Manager/User + admin),
                 lọc server-side theo capability — thay free-text email tránh gán nhầm. -->
            <ApproverSelect
              v-model="assignEmail"
              context="repair"
              label="Kỹ thuật viên"
              required
              placeholder="Tìm KTV theo tên hoặc email..."
            />
          </div>
          <div>
            <label for="assign-priority" class="block text-sm text-slate-600 mb-1">Ưu tiên</label>
            <select id="assign-priority" v-model="assignPriority" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
              <option value="">Giữ nguyên</option>
              <option value="Normal">Bình thường</option>
              <option value="Urgent">Gấp</option>
              <option value="Emergency">Khẩn cấp</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showAssignModal = false">Hủy</button>
          <button :disabled="!assignEmail || submitting" class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50" @click="doAssign">
            {{ submitting ? 'Đang xử lý...' : 'Phân công' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>

    <!-- Cannot Repair Modal -->
    <Transition name="fade">
    <div v-if="showCannotRepairModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="font-bold text-lg text-red-700 mb-2">Không thể sửa chữa</h3>
        <p class="text-sm text-slate-600 mb-4">Thiết bị sẽ được đặt trạng thái "Ngừng hoạt động".</p>
        <textarea v-model="cannotReason" rows="3" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm mb-4" placeholder="Lý do không thể sửa chữa..." />
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showCannotRepairModal = false">Hủy</button>
          <button :disabled="!cannotReason || submitting" class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-50" @click="doCannotRepair">
            {{ submitting ? 'Đang xử lý...' : 'Xác nhận' }}
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

.slide-up-enter-active { transition: all 0.3s ease-out; }
.slide-up-enter-from { transform: translateY(8px); opacity: 0; }
</style>
