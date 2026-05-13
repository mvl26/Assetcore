<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import DateInput from '@/components/common/DateInput.vue'
import { onMounted, computed, ref } from 'vue'
import { useImm08Store } from '@/stores/imm08'
import { useRouter } from 'vue-router'
import { pmStatusLabel, pmStatusClass, resultLabel as _resultLabel } from '@/constants/labels'
const toast = useToast()

const props = defineProps<{ id: string }>()
const store = useImm08Store()
const router = useRouter()

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

const filledCount = computed(() =>
  wo.value?.checklist_results.filter(r => r.result !== null).length ?? 0
)
const totalCount = computed(() => wo.value?.checklist_results.length ?? 0)
const progressPct = computed(() =>
  totalCount.value > 0 ? Math.round((filledCount.value / totalCount.value) * 100) : 0
)

const canSubmit = computed(() =>
  store.checklistComplete && !store.hasMajorFailure
)

const isOverdue = computed(() => wo.value?.status === 'Overdue')

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
    toast.success('Phiếu bảo trì đã hoàn thành')
    // Force re-fetch to ensure reactive update
    await store.fetchWorkOrder(props.id)
    if (res.cmWoCreated) {
      const go = confirm(`Đã hoàn thành bảo trì. Phiếu sửa chữa khắc phục đã được tạo: ${res.cmWoCreated}\n\nMở phiếu sửa chữa ngay?`)
      if (go) router.push(`/cm/work-orders/${res.cmWoCreated}`)
    }
  } else {
    toast.error(store.error || 'Không thể hoàn thành phiếu bảo trì')
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
  } else {
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
const canStart = computed(() =>
  !!wo.value && (wo.value.status === 'Open' || wo.value.status === 'Overdue') && !!wo.value.assigned_to,
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
    startError.value = store.error || 'Không thể bắt đầu PM'
  }
}
</script>

<template>
  <div class="page-container animate-fade-in">
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

    <!-- Loading Skeleton -->
    <div v-if="store.loading" class="space-y-4">
      <div class="card-sm animate-pulse">
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div v-for="i in 6" :key="i" class="h-5 bg-slate-100 rounded" />
        </div>
      </div>
      <div class="card-sm animate-pulse space-y-3">
        <div class="h-4 bg-slate-100 rounded w-48" />
        <div class="h-2 bg-slate-100 rounded-full" />
        <div v-for="i in 4" :key="i" class="h-20 bg-slate-100 rounded-lg" />
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="store.error && !wo" class="alert-error">
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline hover:no-underline" @click="store.fetchWorkOrder(props.id)">Thử lại</button>
    </div>

    <template v-else-if="wo">
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
            <svg class="w-5 h-5 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
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
            <button class="btn-secondary !py-1.5 !text-xs" @click="openRescheduleModal">Hoãn lịch</button>
            <button class="btn-danger !py-1.5 !text-xs" @click="store.fetchWorkOrder(props.id)">Tiếp tục bảo trì</button>
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
            <span :class="wo.is_late ? 'font-semibold text-red-600 ml-1' : 'font-medium ml-1'">{{ wo.due_date }}</span>
          </div>
          <div><span class="text-slate-500">Loại bảo trì:</span> <span class="font-medium ml-1">{{ wo.pm_type }}</span></div>
          <div><span class="text-slate-500">Kỹ thuật viên:</span> <span class="font-medium ml-1">{{ wo.assigned_to || '—' }}</span></div>
          <div><span class="text-slate-500">Mức rủi ro:</span> <span class="font-medium ml-1">{{ wo.risk_class }}</span></div>
          <div><span class="text-slate-500">Loại phiếu:</span> <span class="font-medium ml-1">{{ wo.wo_type }}</span></div>
        </div>
      </div>

      <!-- Start PM banner (Open/Overdue → In Progress) -->
      <div v-if="canStart" class="alert-info mb-5 sm:items-center sm:justify-between">
        <div>
          <div class="font-semibold">Sẵn sàng bắt đầu bảo trì</div>
          <div class="text-xs text-blue-700 mt-0.5">Bấm "Bắt đầu bảo trì" để chuyển phiếu sang <strong>Đang thực hiện</strong> và đặt thiết bị về <strong>Đang sửa chữa</strong>.</div>
          <div v-if="startError" class="text-xs text-red-600 mt-1">{{ startError }}</div>
        </div>
        <button :disabled="starting" class="btn-primary !py-2 !text-sm whitespace-nowrap ml-auto" @click="handleStart">
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
            <label for="sticker" class="text-sm text-slate-700">Đã gắn sticker bảo trì</label>
          </div>
          <div class="flex items-center gap-3">
            <label for="duration-min" class="text-sm text-slate-600 w-40">Thời gian thực hiện:</label>
            <input id="duration-min" v-model="durationMin" type="number" min="0" class="form-input !py-1.5 !text-sm w-24" />
            <span class="text-sm text-slate-500">phút</span>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div v-if="wo.status !== 'Completed' && wo.status !== 'Cancelled'" class="flex justify-between items-center">
        <button class="btn-danger" @click="showMajorModal = true; majorFailureDesc = ''; majorFailureError = ''">
          Báo lỗi nghiêm trọng
        </button>

        <div v-if="!store.hasMajorFailure" class="relative group">
          <button
            :disabled="!canSubmit || submitting"
            class="btn-success"
            @click="canSubmit && !submitting ? showSubmitModal = true : undefined"
          >
            Hoàn thành bảo trì
          </button>
          <div v-if="!canSubmit"
            class="absolute bottom-full right-0 mb-2 w-56 bg-slate-800 text-white text-xs rounded-md px-2.5 py-1.5 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
            Hoàn thành toàn bộ checklist trước khi nộp
          </div>
        </div>
      </div>

      <!-- Completed summary -->
      <div v-if="wo.status === 'Completed'" class="alert-success">
        <div>
          <div class="font-semibold mb-0.5">Bảo trì đã hoàn thành</div>
          <div class="text-sm">Kết quả: {{ wo.overall_result }} · Ngày: {{ wo.completion_date }}</div>
        </div>
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
              <label for="reschedule-date" class="form-label">Ngày mới <span class="text-red-500">*</span></label>
              <DateInput id="reschedule-date" v-model="rescheduleDate" class="form-input !text-sm" />
            </div>
            <div class="form-group">
              <label for="reschedule-reason" class="form-label">Lý do hoãn <span class="text-red-500">*</span></label>
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
  </div>
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
