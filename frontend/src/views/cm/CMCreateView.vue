<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm09Store } from '@/stores/imm09'
import { useFormDraft } from '@/composables/useFormDraft'

const router = useRouter()
const store = useImm09Store()
const submitting = ref(false)
const error = ref('')

const form = ref({
  asset_ref: '',
  incident_report: '',
  source_pm_wo: '',
  repair_type: 'Corrective',
  priority: 'Normal',
  failure_description: '',
})

const { clear: clearDraft } = useFormDraft('cm-create', form)

const sourceError = computed(() => {
  if (!form.value.incident_report && !form.value.source_pm_wo) {
    return 'Phải có nguồn sửa chữa: Báo cáo sự cố hoặc Phiếu bảo trì gốc'
  }
  return ''
})

const canSubmit = computed(() =>
  form.value.asset_ref && !sourceError.value && form.value.failure_description
)

async function handleSubmit() {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = ''
  const name = await store.doCreateRepairWorkOrder(form.value)
  submitting.value = false
  if (name) {
    clearDraft()
    router.push(`/cm/work-orders/${name}`)
  } else {
    error.value = store.error ?? 'Không thể tạo phiếu sửa chữa'
  }
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <div class="flex items-center gap-3 mb-6">
      <button class="text-gray-400 hover:text-gray-600" @click="router.back()">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <h1 class="text-xl font-bold text-gray-900">Tạo Phiếu Sửa Chữa</h1>
    </div>

    <div class="bg-white rounded-xl shadow-sm border p-6 space-y-5">
      <!-- Asset -->
      <div>
        <h2 class="font-semibold text-gray-700 mb-3">Thông tin thiết bị</h2>
        <div>
          <label for="asset-ref" class="block text-sm text-gray-600 mb-1">Mã thiết bị *</label>
          <input id="asset-ref" v-model="form.asset_ref" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="ACC-ASS-2026-XXXXX" />
        </div>
      </div>

      <!-- Source -->
      <div>
        <h2 class="font-semibold text-gray-700 mb-1">Nguồn sửa chữa <span class="text-red-500">*</span></h2>
        <p class="text-xs text-gray-500 mb-3">Điền ít nhất một trong hai trường bên dưới</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label for="incident-report" class="block text-sm text-gray-600 mb-1">Báo cáo sự cố</label>
            <input id="incident-report" v-model="form.incident_report" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="IR-2026-XXXXX" />
          </div>
          <div>
            <label for="source-pm-wo" class="block text-sm text-gray-600 mb-1">Phiếu bảo trì gốc</label>
            <input id="source-pm-wo" v-model="form.source_pm_wo" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="PM-WO-2026-XXXXX" />
          </div>
        </div>
        <p v-if="sourceError && (form.incident_report !== '' || form.source_pm_wo !== '' || form.asset_ref !== '')" class="text-xs text-red-600 mt-1">{{ sourceError }}</p>
      </div>

      <!-- Type & Priority -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label for="repair-type" class="block text-sm text-gray-600 mb-1">Loại sửa chữa *</label>
          <select id="repair-type" v-model="form.repair_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="Corrective">Sửa chữa khắc phục</option>
            <option value="Emergency">Cấp cứu</option>
            <option value="Warranty Repair">Bảo hành</option>
          </select>
        </div>
        <div>
          <label for="priority" class="block text-sm text-gray-600 mb-1">Ưu tiên *</label>
          <select id="priority" v-model="form.priority" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="Normal">Bình thường</option>
            <option value="Urgent">Khẩn</option>
            <option value="Emergency">Cấp cứu</option>
          </select>
        </div>
      </div>

      <!-- Emergency confirm -->
      <div v-if="form.priority === 'Emergency'" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
        ⚠ Bạn đang tạo phiếu sửa chữa <strong>KHẨN CẤP</strong>. Workshop Manager sẽ được thông báo ngay lập tức.
      </div>

      <!-- Description -->
      <div>
        <label for="failure-description" class="block text-sm text-gray-600 mb-1">Mô tả sự cố *</label>
        <textarea id="failure-description" v-model="form.failure_description" rows="4" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Mô tả triệu chứng hỏng hóc, bộ phận bị ảnh hưởng..." />
      </div>

      <!-- Error -->
      <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{{ error }}</div>

      <!-- Actions -->
      <div class="flex justify-end gap-3 pt-2">
        <button class="px-5 py-2.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50" @click="router.back()">Hủy</button>
        <button
          :disabled="!canSubmit || submitting"
          :class="[
            'px-5 py-2.5 rounded-lg text-sm font-medium transition-all',
            canSubmit && !submitting ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          ]"
          @click="handleSubmit"
        >
{{ submitting ? 'Đang tạo...' : 'Tạo phiếu sửa chữa' }}
</button>
      </div>
    </div>
  </div>
</template>
