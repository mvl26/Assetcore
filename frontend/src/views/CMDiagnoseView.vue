<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm09Store } from '@/stores/imm09'

const props = defineProps<{ id: string }>()
const store = useImm09Store()
const router = useRouter()

const ROOT_CAUSES = ['Electrical', 'Mechanical', 'Software', 'User Error', 'Wear and Tear', 'Unknown'] as const
type RootCause = typeof ROOT_CAUSES[number]

const rootCause = ref<RootCause | ''>('')
const diagnosisDetail = ref('')
const needsParts = ref<'no' | 'yes'>('no')
const needsFirmwareUpdate = ref(false)
const estimatedDate = ref('')
const estimatedTime = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

const detailValid = computed(() => diagnosisDetail.value.trim().length >= 20)
const canSubmit = computed(() => rootCause.value !== '' && detailValid.value && !submitting.value)

onMounted(async () => {
  if (!store.currentWO || store.currentWO.name !== props.id) {
    await store.fetchWorkOrder(props.id)
  }
})

async function handleSubmit() {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = null
  try {
    const ok = await store.doSubmitDiagnosis(diagnosisDetail.value, needsParts.value === 'yes')
    if (ok) {
      router.push(`/cm/work-orders/${props.id}`)
    } else {
      error.value = store.error ?? 'Không thể lưu chẩn đoán'
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
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest">IMM-09 / Chẩn đoán</p>
        <h1 class="text-xl font-bold text-slate-900">Chẩn đoán — {{ id }}</h1>
      </div>
    </div>

    <!-- Error banner -->
    <Transition name="fade">
      <div v-if="error" class="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
        {{ error }}
      </div>
    </Transition>

    <div class="max-w-2xl space-y-5">
      <!-- Root cause -->
      <div class="card slide-up-enter-active">
        <label class="block text-sm font-semibold text-slate-700 mb-3">
          Nguyên nhân gốc rễ <span class="text-red-500">*</span>
        </label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="rc in ROOT_CAUSES"
            :key="rc"
            :class="[
              'px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-150',
              rootCause === rc
                ? 'bg-purple-600 border-purple-600 text-white'
                : 'bg-white border-gray-300 text-gray-700 hover:border-purple-400 hover:text-purple-600'
            ]"
            @click="rootCause = rc"
          >
            {{ rc }}
          </button>
        </div>
        <p v-if="rootCause === ''" class="mt-2 text-xs text-red-500">Bắt buộc chọn nguyên nhân</p>
      </div>

      <!-- Diagnosis detail -->
      <div class="card">
        <label for="diag-detail" class="block text-sm font-semibold text-slate-700 mb-2">
          Mô tả chi tiết chẩn đoán <span class="text-red-500">*</span>
          <span class="text-xs font-normal text-slate-400 ml-1">(tối thiểu 20 ký tự)</span>
        </label>
        <textarea
          id="diag-detail"
          v-model="diagnosisDetail"
          rows="5"
          :class="[
            'w-full border rounded-lg px-3 py-2.5 text-sm resize-none transition-colors',
            diagnosisDetail.length > 0 && !detailValid
              ? 'border-red-300 focus:ring-red-200 focus:border-red-400'
              : 'border-gray-300 focus:ring-purple-200 focus:border-purple-400'
          ]"
          placeholder="Mô tả kỹ thuật: bộ phận bị hỏng, triệu chứng quan sát, các bước chẩn đoán đã thực hiện..."
        />
        <div class="flex justify-between mt-1">
          <p v-if="diagnosisDetail.length > 0 && !detailValid" class="text-xs text-red-500">
            Cần thêm {{ 20 - diagnosisDetail.trim().length }} ký tự nữa
          </p>
          <span v-else class="text-xs text-transparent">_</span>
          <span :class="['text-xs', detailValid ? 'text-green-600' : 'text-slate-400']">
            {{ diagnosisDetail.trim().length }} ký tự
          </span>
        </div>
      </div>

      <!-- Needs parts -->
      <div class="card">
        <p class="text-sm font-semibold text-slate-700 mb-3">Yêu cầu vật tư?</p>
        <div class="space-y-2">
          <label class="flex items-center gap-3 cursor-pointer group">
            <input
              v-model="needsParts"
              type="radio"
              value="no"
              class="w-4 h-4 text-purple-600"
            />
            <span class="text-sm text-slate-700 group-hover:text-slate-900">
              Không cần vật tư — tiếp tục sửa chữa ngay
            </span>
          </label>
          <label class="flex items-center gap-3 cursor-pointer group">
            <input
              v-model="needsParts"
              type="radio"
              value="yes"
              class="w-4 h-4 text-purple-600"
            />
            <span class="text-sm text-slate-700 group-hover:text-slate-900">
              Cần vật tư — chuyển trạng thái <span class="font-medium text-orange-600">Pending Parts</span>
            </span>
          </label>
        </div>
      </div>

      <!-- Firmware update -->
      <div class="card">
        <label class="flex items-center gap-3 cursor-pointer group">
          <input
            v-model="needsFirmwareUpdate"
            type="checkbox"
            class="w-4 h-4 text-purple-600 rounded"
          />
          <span class="text-sm text-slate-700 group-hover:text-slate-900">
            Cập nhật Firmware trong lần sửa này
            <span class="text-xs text-slate-400 ml-1">(sẽ yêu cầu tạo Firmware Change Request)</span>
          </span>
        </label>
      </div>

      <!-- Estimated completion -->
      <div class="card">
        <p class="text-sm font-semibold text-slate-700 mb-3">Dự kiến thời gian hoàn thành</p>
        <div class="flex gap-3">
          <input
            v-model="estimatedDate"
            type="date"
            class="form-input flex-1"
          />
          <input
            v-model="estimatedTime"
            type="time"
            class="form-input w-36"
          />
        </div>
      </div>

      <!-- Actions -->
      <div class="flex justify-end gap-3 pt-2 pb-6">
        <button
          class="px-5 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          @click="router.push(`/cm/work-orders/${id}`)"
        >
          Hủy
        </button>
        <button
          :disabled="!canSubmit"
          :class="[
            'px-5 py-2.5 rounded-lg text-sm font-medium text-white transition-all duration-150',
            canSubmit ? 'bg-purple-600 hover:bg-purple-700 shadow-sm' : 'bg-purple-300 cursor-not-allowed'
          ]"
          @click="handleSubmit"
        >
          {{ submitting ? 'Đang lưu...' : 'Lưu chẩn đoán' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active { transition: all 0.3s ease-out; }
.slide-up-enter-from { transform: translateY(8px); opacity: 0; }
</style>
