<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useImm08Store } from '@/stores/imm08'
import { useRouter } from 'vue-router'

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
  if (result === 'Pass') return 'border-green-400 bg-green-50'
  if (result === 'Fail–Minor') return 'border-yellow-400 bg-yellow-50'
  if (result === 'Fail–Major') return 'border-red-400 bg-red-50'
  return 'border-gray-200'
}

async function handleSubmit() {
  submitting.value = true
  const res = await store.doSubmitResult(techNotes.value, stickerAttached.value, durationMin.value)
  submitting.value = false
  showSubmitModal.value = false
  if (res.success) {
    if (res.cmWoCreated) {
      alert(`Đã hoàn thành PM. WO sửa chữa khắc phục đã được tạo: ${res.cmWoCreated}`)
    }
  }
}

async function handleMajorFailure() {
  const cmWo = await store.doReportMajorFailure(majorFailureDesc.value)
  showMajorModal.value = false
  if (cmWo) {
    alert(`Đã báo lỗi Major. CM Work Order đã được tạo: ${cmWo}\nThiết bị đã được đặt trạng thái Out of Service.`)
    router.push(`/cm/work-orders/${cmWo}`)
  }
}

async function handleReschedule() {
  if (!wo.value || !rescheduleDate.value || !rescheduleReason.value) return
  rescheduling.value = true
  await store.doReschedule(wo.value.name, rescheduleDate.value, rescheduleReason.value)
  rescheduling.value = false
  showRescheduleModal.value = false
}

function openRescheduleModal() {
  rescheduleDate.value = ''
  rescheduleReason.value = ''
  showRescheduleModal.value = true
}
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto">
    <!-- Back + Header -->
    <div class="flex items-center gap-3 mb-5">
      <button class="text-gray-400 hover:text-gray-600 transition-colors" @click="router.back()">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div class="flex-1">
        <div class="flex items-center gap-2">
          <span class="font-mono text-lg font-semibold text-gray-900">{{ wo?.name }}</span>
          <span v-if="wo" :class="['px-2 py-0.5 rounded-full text-xs font-medium',
            wo.status === 'Overdue' ? 'bg-red-100 text-red-700' :
            wo.status === 'Completed' ? 'bg-green-100 text-green-700' :
            wo.status === 'In Progress' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600']">
            {{ wo.status }}
          </span>
        </div>
        <div class="text-sm text-gray-500">{{ wo?.asset_name || wo?.asset_ref }}</div>
      </div>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="store.loading" class="space-y-4">
      <div class="bg-white rounded-xl border p-5 animate-pulse">
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div v-for="i in 6" :key="i" class="h-5 bg-gray-100 rounded" />
        </div>
      </div>
      <div class="bg-white rounded-xl border p-5 animate-pulse space-y-3">
        <div class="h-4 bg-gray-100 rounded w-48" />
        <div class="h-2 bg-gray-100 rounded-full" />
        <div v-for="i in 4" :key="i" class="h-20 bg-gray-100 rounded-xl" />
      </div>
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
          class="mb-5 bg-red-50 border border-red-300 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
        >
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-2.694-.833-3.464 0L3.34 16.5C2.57 18.333 3.532 20 5.07 20z"/>
            </svg>
            <div>
              <div class="font-semibold text-red-700 text-sm">
                PM QUÁ HẠN {{ overdueDays > 0 ? overdueDays + ' NGÀY' : '' }} — Đến hạn: {{ wo.due_date }}
              </div>
              <div class="text-xs text-red-600 mt-0.5">Vui lòng hoàn thành hoặc hoãn lịch có ghi lý do</div>
            </div>
          </div>
          <div class="flex gap-2 shrink-0">
            <button
              class="text-xs bg-white border border-red-300 text-red-600 px-3 py-1.5 rounded-lg hover:bg-red-50 transition-colors"
              @click="openRescheduleModal"
            >
              Hoãn lịch
            </button>
            <button
              class="text-xs bg-red-600 text-white px-3 py-1.5 rounded-lg hover:bg-red-700 transition-colors"
              @click="store.fetchWorkOrder(props.id)"
            >
              Tiếp tục PM
            </button>
          </div>
        </div>
      </Transition>

      <!-- Info grid -->
      <div class="bg-white rounded-xl shadow-sm border p-5 mb-5">
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div><span class="text-gray-500">Thiết bị:</span> <span class="font-medium">{{ wo.asset_ref }}</span></div>
          <div><span class="text-gray-500">Đến hạn:</span>
            <span :class="wo.is_late ? 'font-semibold text-red-600' : 'font-medium'">{{ wo.due_date }}</span>
          </div>
          <div><span class="text-gray-500">Loại PM:</span> <span class="font-medium">{{ wo.pm_type }}</span></div>
          <div><span class="text-gray-500">KTV:</span> <span class="font-medium">{{ wo.assigned_to || '—' }}</span></div>
          <div><span class="text-gray-500">Risk Class:</span> <span class="font-medium">{{ wo.risk_class }}</span></div>
          <div><span class="text-gray-500">Loại WO:</span> <span class="font-medium">{{ wo.wo_type }}</span></div>
        </div>
      </div>

      <!-- Checklist Section -->
      <div class="bg-white rounded-xl shadow-sm border p-5 mb-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-semibold text-gray-800">Checklist ({{ filledCount }}/{{ totalCount }} đã hoàn thành)</h2>
          <span :class="['text-sm font-medium', progressPct === 100 ? 'text-green-600' : 'text-blue-600']">
            {{ progressPct }}%
          </span>
        </div>

        <!-- Progress Bar (smooth 500ms transition) -->
        <div class="h-2 bg-gray-100 rounded-full mb-5 overflow-hidden">
          <div
            class="h-2 rounded-full transition-all duration-500"
            :class="progressPct === 100 ? 'bg-green-500' : 'bg-blue-500'"
            :style="{ width: `${progressPct}%` }"
          />
        </div>

        <!-- Checklist Items -->
        <div class="space-y-4">
          <div
            v-for="item in wo.checklist_results"
            :key="item.idx"
            :class="['border rounded-xl p-4 transition-colors duration-200', resultClass(item.result)]"
          >
            <div class="flex items-start gap-3 mb-3">
              <span class="shrink-0 w-6 h-6 rounded-full bg-gray-200 text-gray-600 text-xs font-bold flex items-center justify-center">
                {{ item.idx }}
              </span>
              <div class="flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-medium text-gray-800 text-sm">{{ item.description }}</span>
                  <!-- CRITICAL badge: shown when checklist item result is Fail–Major -->
                  <span
                    v-if="item.result === 'Fail–Major'"
                    class="text-xs bg-red-600 text-white px-1.5 py-0.5 rounded font-semibold tracking-wide"
                  >CRITICAL</span>
                  <span v-if="item.measurement_type === 'Numeric'" class="text-xs bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded">Số đo</span>
                </div>
              </div>
            </div>

            <!-- Result Buttons -->
            <div v-if="wo.status !== 'Completed'" class="flex flex-wrap gap-2 mb-3">
              <button
                v-for="opt in ['Pass', 'Fail–Minor', 'Fail–Major', 'N/A']"
                :key="opt"
                :class="[
                  'px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-150',
                  item.result === opt
                    ? opt === 'Pass' ? 'bg-green-500 text-white border-green-500'
                    : opt === 'Fail–Minor' ? 'bg-yellow-500 text-white border-yellow-500'
                    : opt === 'Fail–Major' ? 'bg-red-500 text-white border-red-500'
                    : 'bg-gray-500 text-white border-gray-500'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
                ]"
                @click="store.updateChecklistResult(item.idx, { result: opt as any })"
              >
                {{ opt }}
              </button>
            </div>
            <div v-else class="mb-2">
              <span :class="['px-2 py-1 rounded text-xs font-medium',
                item.result === 'Pass' ? 'bg-green-100 text-green-700' :
                item.result === 'Fail–Minor' ? 'bg-yellow-100 text-yellow-700' :
                item.result === 'Fail–Major' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600']">
                {{ item.result }}
              </span>
            </div>

            <!-- Numeric value -->
            <div v-if="item.measurement_type === 'Numeric'" class="mb-2">
              <input
                v-if="wo.status !== 'Completed'"
                :value="item.measured_value"
                type="number"
                placeholder="Giá trị đo được"
                class="border border-gray-300 rounded px-3 py-1.5 text-sm w-40"
                @input="store.updateChecklistResult(item.idx, { measured_value: Number(($event.target as HTMLInputElement).value) })"
              />
              <span v-else class="text-sm text-gray-600">{{ item.measured_value }} {{ item.unit }}</span>
            </div>

            <!-- Notes for failures -->
            <div v-if="item.result && item.result !== 'Pass' && item.result !== 'N/A'">
              <textarea
                v-if="wo.status !== 'Completed'"
                :value="item.notes"
                placeholder="Ghi chú lỗi (bắt buộc khi Fail)..."
                rows="2"
                class="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
                @input="store.updateChecklistResult(item.idx, { notes: ($event.target as HTMLTextAreaElement).value })"
              />
              <p v-else class="text-sm text-gray-600 italic">{{ item.notes }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Kết quả tổng thể -->
      <div v-if="wo.status !== 'Completed'" class="bg-white rounded-xl shadow-sm border p-5 mb-5">
        <h2 class="font-semibold text-gray-800 mb-4">Kết quả tổng thể</h2>
        <div class="space-y-3">
          <div>
            <label for="tech-notes" class="block text-sm text-gray-600 mb-1">Ghi chú KTV</label>
            <textarea id="tech-notes" v-model="techNotes" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Ghi chú kỹ thuật..."/>
          </div>
          <div class="flex items-center gap-3">
            <input id="sticker" v-model="stickerAttached" type="checkbox" class="w-4 h-4" />
            <label for="sticker" class="text-sm text-gray-700">Đã gắn sticker PM</label>
          </div>
          <div class="flex items-center gap-3">
            <label for="duration-min" class="text-sm text-gray-600 w-40">Thời gian thực hiện:</label>
            <input id="duration-min" v-model="durationMin" type="number" min="0" class="border border-gray-300 rounded px-3 py-1.5 text-sm w-24" />
            <span class="text-sm text-gray-500">phút</span>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div v-if="wo.status !== 'Completed' && wo.status !== 'Cancelled'" class="flex justify-between items-center">
        <!-- Major failure: always visible; complete: disabled with tooltip when hasMajorFailure -->
        <button
          class="px-4 py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 flex items-center gap-2 transition-colors"
          @click="showMajorModal = true"
        >
          🔴 Báo lỗi Major
        </button>

        <div v-if="!store.hasMajorFailure" class="flex gap-3">
          <button class="px-4 py-2.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition-colors">
            Lưu nháp
          </button>
          <div class="relative group">
            <button
              :disabled="!canSubmit || submitting"
              :class="[
                'px-5 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2',
                canSubmit && !submitting
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              ]"
              @click="canSubmit && !submitting ? showSubmitModal = true : undefined"
            >
              ✓ Hoàn thành
            </button>
            <!-- Tooltip when disabled because checklist incomplete -->
            <div
              v-if="!canSubmit"
              class="absolute bottom-full right-0 mb-2 w-48 bg-gray-800 text-white text-xs rounded-lg px-2.5 py-1.5 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity"
            >
              Hoàn thành toàn bộ checklist trước khi nộp
            </div>
          </div>
        </div>
        <!-- When hasMajorFailure: complete button completely hidden -->
      </div>

      <!-- Completed summary -->
      <div v-if="wo.status === 'Completed'" class="bg-green-50 border border-green-200 rounded-xl p-4">
        <div class="text-green-700 font-semibold mb-1">✓ PM đã hoàn thành</div>
        <div class="text-sm text-green-600">Kết quả: {{ wo.overall_result }} | Ngày: {{ wo.completion_date }}</div>
      </div>
    </template>

    <!-- Reschedule Modal (from Overdue banner) -->
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 scale-95"
      leave-active-class="transition duration-150"
      leave-to-class="opacity-0 scale-95"
    >
      <div v-if="showRescheduleModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showRescheduleModal = false">
        <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
          <h3 class="font-bold text-lg text-gray-900 mb-4">Hoãn lịch PM</h3>
          <div class="space-y-4">
            <div>
              <label for="reschedule-date" class="block text-sm text-gray-600 mb-1">Ngày mới <span class="text-red-500">*</span></label>
              <input id="reschedule-date" v-model="rescheduleDate" type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label for="reschedule-reason" class="block text-sm text-gray-600 mb-1">Lý do hoãn <span class="text-red-500">*</span></label>
              <textarea
                id="reschedule-reason"
                v-model="rescheduleReason"
                rows="3"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="Nhập lý do hoãn lịch..."
              />
            </div>
          </div>
          <div class="flex justify-end gap-3 mt-5">
            <button class="px-4 py-2 border border-gray-300 rounded-lg text-sm" @click="showRescheduleModal = false">Hủy</button>
            <button
              :disabled="!rescheduleDate || !rescheduleReason || rescheduling"
              class="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 disabled:opacity-50 transition-colors"
              @click="handleReschedule"
            >{{ rescheduling ? 'Đang xử lý...' : 'Xác nhận hoãn' }}</button>
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
      <div v-if="showMajorModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showMajorModal = false">
        <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
          <h3 class="font-bold text-lg text-red-700 mb-2">⛔ Báo lỗi Major Failure</h3>
          <p class="text-sm text-gray-600 mb-4">Thiết bị sẽ được đặt trạng thái "Out of Service" và tạo CM Work Order khẩn cấp.</p>
          <label for="major-failure-desc" class="sr-only">Mô tả lỗi Major</label>
          <textarea
            id="major-failure-desc"
            v-model="majorFailureDesc"
            rows="4"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4"
            placeholder="Mô tả chi tiết lỗi Major..."
          />
          <div class="flex justify-end gap-3">
            <button class="px-4 py-2 border border-gray-300 rounded-lg text-sm" @click="showMajorModal = false">Hủy</button>
            <button
              :disabled="!majorFailureDesc"
              class="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
              @click="handleMajorFailure"
            >Xác nhận báo lỗi</button>
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
      <div v-if="showSubmitModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showSubmitModal = false">
        <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
          <h3 class="font-bold text-lg text-gray-900 mb-4">✓ Xác nhận hoàn thành PM</h3>
          <div class="text-sm text-gray-600 space-y-2 mb-4">
            <div>Checklist: <strong class="text-green-600">{{ filledCount }}/{{ totalCount }} mục</strong></div>
            <div>Thời gian: <strong>{{ durationMin }} phút</strong></div>
            <div>Sticker: <strong>{{ stickerAttached ? '✓ Đã gắn' : '✗ Chưa gắn' }}</strong></div>
            <div v-if="store.hasMinorFailure" class="text-yellow-600">
              ⚠ Có {{ wo?.checklist_results.filter(r => r.result === 'Fail–Minor').length }} mục Fail Minor — sẽ tạo CM WO Medium priority
            </div>
          </div>
          <div class="flex justify-end gap-3">
            <button class="px-4 py-2 border border-gray-300 rounded-lg text-sm" @click="showSubmitModal = false">Hủy</button>
            <button
              :disabled="submitting"
              class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
              @click="handleSubmit"
            >{{ submitting ? 'Đang xử lý...' : 'Hoàn thành PM' }}</button>
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
