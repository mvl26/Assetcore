<script setup lang="ts">
import { onMounted, computed, ref, onUnmounted } from 'vue'
import { useImm09Store } from '@/stores/imm09'
import { useRouter } from 'vue-router'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'
import { cmStatusLabel, cmStatusClass, priorityLabel, priorityClass, rootCauseLabel, repairTypeLabel, resultLabel, lifecycleStatusLabel, lifecycleStatusClass } from '@/constants/labels'

const props = defineProps<{ id: string }>()
const store = useImm09Store()
const router = useRouter()
const notify = useNotify()

/** Sau mỗi action store: success → toast chuẩn; fail → notify.fromError(ApiError đã hydrate). */
function notifyResult(ok: boolean, successCode: string, ctx: Record<string, unknown> = {}): void {
  if (ok) notify.show({ code: successCode, ctx })
  else notify.fromError(store.lastApiError)
}

// Only Assign and Cannot Repair remain as modals; others navigate to sub-routes
const showAssignModal = ref(false)
const showCannotRepairModal = ref(false)

// Form state for remaining modals
const assignEmail = ref('')
const assignPriority = ref('')
const cannotReason = ref('')
const submitting = ref(false)

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
  const ok = await store.doCloseWorkOrder({
    name: wo.value!.name,
    repair_summary: '',
    root_cause_category: '',
    dept_head_name: '',
    checklist_results: [],
    cannot_repair: true,
    cannot_repair_reason: cannotReason.value,
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
          <span v-if="wo?.sla_breached" class="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 font-semibold">SLA vi phạm</span>
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
    <div v-else-if="store.error && !wo" class="card text-center py-16">
      <p class="text-base font-semibold text-slate-700 mb-1">Không thể tải lệnh sửa chữa</p>
      <p class="text-sm text-red-500 mb-4">{{ store.error }}</p>
      <div class="flex gap-3 justify-center">
        <button class="btn-secondary" @click="router.push('/cm/work-orders')">Quay lại danh sách</button>
        <button class="btn-primary" @click="store.fetchWorkOrder(props.id)">Thử lại</button>
      </div>
    </div>
    <div v-else-if="wo" class="grid grid-cols-1 md:grid-cols-5 gap-6">
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
            <div><span class="text-slate-500">Serial:</span> <span class="font-mono text-xs">{{ wo.serial_no || '—' }}</span></div>
            <div><span class="text-slate-500">Risk Class:</span> <span class="font-medium">{{ wo.risk_class }}</span></div>
            <div><span class="text-slate-500">Loại SC:</span> <span class="font-medium">{{ repairTypeLabel(wo.repair_type) }}</span></div>
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
              title="Mở Incident Report nguồn"
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
          <div class="overflow-x-auto">
<table class="w-full text-sm">
            <thead class="bg-slate-50">
              <tr>
                <th class="text-left px-3 py-2 text-xs font-medium text-slate-500">Vật tư</th>
                <th class="text-right px-3 py-2 text-xs font-medium text-slate-500">Số lượng</th>
                <th class="text-right px-3 py-2 text-xs font-medium text-slate-500">Thành tiền</th>
                <th class="text-center px-3 py-2 text-xs font-medium text-slate-500">Phiếu XK</th>
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
                <td class="px-3 py-2 text-center">
                  <span v-if="p.stock_entry_ref" class="text-emerald-700 text-xs font-mono">{{ p.stock_entry_ref }}</span>
                  <span v-else class="text-red-600 text-xs">Chưa có</span>
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
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT PANEL (40%) -->
      <div class="md:col-span-2 space-y-4">
        <!-- SLA Indicator -->
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="font-semibold text-slate-700 mb-3 text-sm">Chỉ số SLA</h2>

          <!-- WO đã đóng: kết quả cuối, không có timer/progress -->
          <template v-if="['Completed', 'Cannot Repair', 'Cancelled'].includes(wo.status)">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-slate-500">Thời gian sửa chữa (TTR)</span>
              <span class="text-xs text-slate-500">SLA target</span>
            </div>
            <div class="flex items-center justify-between mb-3">
              <span :class="['text-xl font-bold font-mono', wo.sla_breached ? 'text-red-600' : 'text-emerald-600']">
                {{ wo.mttr_hours != null ? `${wo.mttr_hours}h` : '—' }}
              </span>
              <span class="text-slate-400 text-sm">/</span>
              <span class="text-xl font-bold font-mono text-slate-700">{{ wo.sla_target_hours ?? '—' }}h</span>
            </div>
            <div class="flex items-center justify-center gap-2 py-2 rounded-lg"
                 :class="wo.sla_breached ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">
              <span class="text-base font-semibold">
                {{ wo.sla_breached ? '✗ Vi phạm SLA' : '✓ Đạt SLA' }}
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
                <p class="text-sm font-semibold">Chờ phụ tùng — SLA tạm dừng</p>
                <p class="text-xs mt-0.5 text-amber-700">
                  Đồng hồ SLA/MTTR đang dừng trong thời gian chờ phụ tùng hết kho;
                  khoảng này không tính vào thời gian sửa chữa.
                </p>
              </div>
            </div>
            <div class="flex items-center justify-between mt-3 text-xs text-slate-500">
              <span>SLA target</span>
              <span class="font-mono font-semibold text-slate-700">{{ wo.sla_target_hours ?? '—' }}h</span>
            </div>
          </template>

          <!-- WO active: timer + progress bar -->
          <template v-else>
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs text-slate-500">Đã trôi: {{ (elapsed / 3600).toFixed(1) }}h / {{ wo.sla_target_hours || '—' }}h SLA</span>
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
              <span class="text-slate-500">Thời gian sửa chữa (TTR):</span>
              <span :class="['font-semibold', wo.sla_breached ? 'text-red-600' : 'text-green-600']">{{ wo.mttr_hours }}h</span>
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
            <!-- Open → Assign (modal) -->
            <template v-if="wo.status === 'Open'">
              <button
class="w-full px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                @click="showAssignModal = true">
Phân công kỹ thuật viên
</button>
            </template>

            <!-- Assigned → navigate /diagnose -->
            <template v-if="wo.status === 'Assigned'">
              <button
class="w-full px-4 py-2.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
                @click="navigateDiagnose">
Bắt đầu chẩn đoán
</button>
            </template>

            <!-- Diagnosing → navigate /diagnose -->
            <template v-if="wo.status === 'Diagnosing'">
              <button
class="w-full px-4 py-2.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
                @click="navigateDiagnose">
Cập nhật chẩn đoán
</button>
            </template>

            <!-- Pending Parts → navigate /parts -->
            <template v-if="wo.status === 'Pending Parts'">
              <button
class="w-full px-4 py-2.5 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700 transition-colors"
                @click="navigateParts">
Quản lý vật tư
</button>
            </template>

            <!-- In Repair → navigate /parts + /checklist -->
            <template v-if="wo.status === 'In Repair'">
              <button
class="w-full px-4 py-2.5 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700 transition-colors"
                @click="navigateParts">
Quản lý vật tư
</button>
              <button
class="w-full px-4 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
                @click="navigateChecklist">
Hoàn thành sửa chữa
</button>
            </template>

            <!-- Pending Inspection → xác nhận nghiệm thu (QA / trưởng khoa) -->
            <template v-if="wo.status === 'Pending Inspection'">
              <button
                class="w-full px-4 py-2.5 bg-cyan-600 text-white rounded-lg text-sm font-medium hover:bg-cyan-700 disabled:opacity-50 transition-colors"
                :disabled="submitting"
                @click="doConfirmInspection">
                {{ submitting ? 'Đang xử lý...' : 'Xác nhận nghiệm thu — Hoàn thành' }}
              </button>
              <p class="text-[11px] text-center text-slate-400 mt-1">
                Yêu cầu quyền phê duyệt cấp khoa/QA. Sau bước này MTTR & SLA được chốt.
              </p>
            </template>

            <!-- Cannot Repair button for non-terminal statuses -->
            <template v-if="!['Completed','Cannot Repair','Cancelled'].includes(wo.status)">
              <button
class="w-full px-4 py-2.5 border border-red-300 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
                @click="showCannotRepairModal = true">
Không thể sửa chữa
</button>
            </template>

            <!-- Terminal states -->
            <div v-if="wo.status === 'Completed'" class="text-center py-2 text-emerald-600 font-semibold text-sm">
              Đã hoàn thành
            </div>
            <div v-if="wo.status === 'Cannot Repair'" class="text-center py-2 text-red-600 font-semibold text-sm">
              Không thể sửa chữa
            </div>
          </div>
        </div>

        <!-- Vật tư summary (right panel) -->
        <div class="bg-white rounded-xl shadow-sm border p-4 text-sm">
          <div class="flex justify-between text-slate-500">
            <span>Vật tư:</span>
            <span class="font-medium text-slate-900">{{ wo.spare_parts_used?.length || 0 }} mục</span>
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

    <!-- Assign Modal -->
    <Transition name="fade">
    <div v-if="showAssignModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="font-bold text-lg mb-4">Phân công kỹ thuật viên</h3>
        <div class="space-y-3 mb-5">
          <div>
            <label for="assign-email" class="block text-sm text-slate-600 mb-1">Email kỹ thuật viên *</label>
            <input id="assign-email" v-model="assignEmail" type="email" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" placeholder="ktv@hospital.vn" />
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
