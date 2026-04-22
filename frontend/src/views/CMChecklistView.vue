<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm09Store } from '@/stores/imm09'
import type { RepairChecklistRow } from '@/api/imm09'

const props = defineProps<{ id: string }>()
const store = useImm09Store()
const router = useRouter()

const checklist = ref<RepairChecklistRow[]>([])
const deptHeadName = ref('')
const deptHeadTitle = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  if (!store.currentWO || store.currentWO.name !== props.id) {
    await store.fetchWorkOrder(props.id)
  }
  if (store.currentWO) {
    checklist.value = store.currentWO.repair_checklist.map(r => ({ ...r }))
  }
})

const passCount = computed(() => checklist.value.filter(r => r.result === 'Pass').length)
const totalCount = computed(() => checklist.value.length)
const progressPct = computed(() =>
  totalCount.value > 0 ? Math.round((passCount.value / totalCount.value) * 100) : 0
)
const hasAnyFail = computed(() => checklist.value.some(r => r.result === 'Fail'))
const allAnswered = computed(() => checklist.value.every(r => r.result !== null))

const canComplete = computed(() =>
  allAnswered.value &&
  !hasAnyFail.value &&
  deptHeadName.value.trim() !== ''
)

function setResult(item: RepairChecklistRow, result: 'Pass' | 'Fail' | 'N/A') {
  item.result = result
}

function resultButtonClass(item: RepairChecklistRow, result: 'Pass' | 'Fail' | 'N/A'): string {
  const active = item.result === result
  const base = 'px-3 py-1 rounded text-xs font-semibold border transition-all duration-150'
  if (result === 'Pass') {
    return active
      ? `${base} bg-green-600 border-green-600 text-white`
      : `${base} border-gray-300 text-gray-600 hover:border-green-400 hover:text-green-600`
  }
  if (result === 'Fail') {
    return active
      ? `${base} bg-red-600 border-red-600 text-white`
      : `${base} border-gray-300 text-gray-600 hover:border-red-400 hover:text-red-600`
  }
  return active
    ? `${base} bg-gray-500 border-gray-500 text-white`
    : `${base} border-gray-300 text-gray-600 hover:border-gray-400`
}

async function handleComplete() {
  if (!canComplete.value) return
  submitting.value = true
  error.value = null
  try {
    const ok = await store.doCloseWorkOrder({
      name: props.id,
      repair_summary: '',
      root_cause_category: store.currentWO?.root_cause_category ?? '',
      dept_head_name: `${deptHeadName.value} — ${deptHeadTitle.value}`,
      checklist_results: checklist.value,
    })
    if (ok) {
      router.push(`/cm/work-orders/${props.id}`)
    } else {
      error.value = store.error ?? 'Không thể hoàn thành sửa chữa'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <button
        class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        @click="router.push(`/cm/work-orders/${id}`)"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest">IMM-09 / Nghiệm thu</p>
        <h1 class="text-xl font-bold text-slate-900">Nghiệm thu sau sửa chữa — {{ id }}</h1>
      </div>
    </div>

    <!-- Error banner -->
    <Transition name="fade">
      <div v-if="error" class="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
        {{ error }}
      </div>
    </Transition>

    <div class="max-w-2xl space-y-5">
      <!-- Progress bar -->
      <div class="card">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-semibold text-slate-700">Tiến độ nghiệm thu</span>
          <span class="text-sm font-medium text-slate-600">{{ passCount }} / {{ totalCount }} mục Pass</span>
        </div>
        <div class="h-3 bg-slate-100 rounded-full overflow-hidden">
          <div
            :class="[
              'h-3 rounded-full transition-all duration-500',
              hasAnyFail ? 'bg-red-500' : progressPct === 100 ? 'bg-green-500' : 'bg-blue-500'
            ]"
            :style="{ width: `${progressPct}%` }"
          />
        </div>
        <div class="flex justify-between mt-2 text-xs text-slate-400">
          <span>{{ progressPct }}% hoàn thành</span>
          <span v-if="hasAnyFail" class="text-red-500 font-medium">⚠ Có mục Fail — không thể hoàn thành</span>
          <span v-else-if="allAnswered && progressPct === 100" class="text-green-600 font-medium">✓ Tất cả đã Pass</span>
        </div>
      </div>

      <!-- Checklist items -->
      <div v-if="checklist.length === 0" class="card text-center text-slate-400 text-sm py-8">
        Không có mục checklist nào cho phiếu sửa chữa này.
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="item in checklist"
          :key="item.idx"
          :class="[
            'card transition-all duration-200',
            item.result === 'Pass' ? 'border-green-200 bg-green-50' :
            item.result === 'Fail' ? 'border-red-200 bg-red-50' :
            item.result === 'N/A' ? 'border-gray-200 bg-gray-50' : 'border-slate-200'
          ]"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-xs font-semibold text-slate-400">#{{ item.idx }}</span>
                <span class="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{{ item.test_category }}</span>
              </div>
              <p class="text-sm font-medium text-slate-800">{{ item.test_description }}</p>
              <div v-if="item.expected_value || item.measured_value" class="flex gap-4 mt-1.5 text-xs text-slate-500">
                <span v-if="item.expected_value">Yêu cầu: <strong>{{ item.expected_value }}</strong></span>
                <span v-if="item.measured_value">Đo được: <strong>{{ item.measured_value }}</strong></span>
              </div>
              <p v-if="item.result === 'Fail'" class="mt-1.5 text-xs font-semibold text-red-600">
                ⚠ Kết quả Không đạt — không thể hoàn thành nghiệm thu
              </p>
            </div>
            <!-- Result buttons -->
            <div class="flex gap-1.5 shrink-0">
              <button :class="resultButtonClass(item, 'Pass')" @click="setResult(item, 'Pass')">Đạt</button>
              <button :class="resultButtonClass(item, 'Fail')" @click="setResult(item, 'Fail')">Không đạt</button>
              <button :class="resultButtonClass(item, 'N/A')" @click="setResult(item, 'N/A')">Không áp dụng</button>
            </div>
          </div>
          <!-- Notes field -->
          <div v-if="item.result === 'Fail' || item.result === 'N/A'" class="mt-3">
            <input
              v-model="item.notes"
              type="text"
              :class="[
                'w-full border rounded px-3 py-1.5 text-xs',
                item.result === 'Fail' ? 'border-red-300 bg-white' : 'border-gray-300'
              ]"
              placeholder="Ghi chú (tùy chọn)..."
            />
          </div>
        </div>
      </div>

      <!-- Dept head confirmation -->
      <div class="card">
        <p class="text-sm font-semibold text-slate-700 mb-3">
          Xác nhận trưởng khoa phòng <span class="text-red-500">*</span>
        </p>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs text-slate-500 mb-1">Họ tên *</label>
            <input
              v-model="deptHeadName"
              type="text"
              class="form-input"
              placeholder="Nguyễn Văn A"
            />
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">Chức danh</label>
            <input
              v-model="deptHeadTitle"
              type="text"
              class="form-input"
              placeholder="Trưởng khoa ICU"
            />
          </div>
        </div>
        <p v-if="!deptHeadName.trim() && allAnswered && !hasAnyFail" class="mt-2 text-xs text-red-500">
          Bắt buộc nhập họ tên trưởng khoa
        </p>
      </div>

      <!-- Actions -->
      <div class="flex justify-between items-center pt-2 pb-6">
        <button
          class="px-5 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          @click="router.push(`/cm/work-orders/${id}`)"
        >
          Quay lại
        </button>
        <button
          :disabled="!canComplete || submitting"
          :class="[
            'px-6 py-2.5 rounded-lg text-sm font-semibold text-white transition-all duration-150',
            canComplete && !submitting
              ? 'bg-green-600 hover:bg-green-700 shadow-sm'
              : 'bg-green-300 cursor-not-allowed'
          ]"
          @click="handleComplete"
        >
          {{ submitting ? 'Đang xử lý...' : 'Hoàn thành sửa chữa' }}
        </button>
      </div>

      <!-- Hint when not ready -->
      <Transition name="fade">
        <div v-if="!canComplete && checklist.length > 0" class="pb-4 text-xs text-slate-400 text-center">
          <span v-if="!allAnswered">Cần điền đầy đủ kết quả cho tất cả {{ totalCount - passCount - checklist.filter(r => r.result === 'Fail' || r.result === 'N/A').length }} mục chưa chọn</span>
          <span v-else-if="hasAnyFail">Có {{ checklist.filter(r => r.result === 'Fail').length }} mục Fail — cần xử lý trước khi hoàn thành</span>
          <span v-else-if="!deptHeadName.trim()">Cần nhập họ tên trưởng khoa phòng</span>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active { transition: all 0.3s ease-out; }
.slide-up-enter-from { transform: translateY(8px); opacity: 0; }
</style>
