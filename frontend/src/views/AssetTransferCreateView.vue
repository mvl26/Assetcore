<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { frappePost } from '@/api/helpers'
import SmartSelect from '@/components/common/SmartSelect.vue'

const router = useRouter()

const form = ref({
  asset: '',
  transfer_date: new Date().toISOString().slice(0, 10),
  transfer_type: '',
  to_location: '',
  to_department: '',
  to_custodian: '',
  reason: '',
  approved_by: '',
  expected_return_date: '',
  notes: '',
})

const saving = ref(false)
const error = ref('')

const TRANSFER_TYPES = ['Internal', 'Loan', 'External', 'Return']
const BASE = '/api/method/assetcore.api.imm00'

const isLoan = computed(() => form.value.transfer_type === 'Loan')

async function submit() {
  if (!form.value.asset || !form.value.transfer_type || !form.value.to_location || !form.value.reason) {
    error.value = 'Vui lòng điền đầy đủ các trường bắt buộc (*).'
    return
  }
  if (isLoan.value && !form.value.expected_return_date) {
    error.value = 'Ngày trả dự kiến bắt buộc khi loại chuyển giao là Loan.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await frappePost<void>(`${BASE}.create_transfer`, form.value)
    router.push('/asset-transfers')
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi tạo Asset Transfer'
  }
  saving.value = false
}

</script>

<template>
  <div class="max-w-2xl mx-auto p-6 space-y-6">
    <div class="flex items-center gap-3">
      <button @click="router.back()" class="text-gray-500 hover:text-gray-700 text-sm">← Quay lại</button>
      <h1 class="text-xl font-semibold text-gray-800">Tạo Asset Transfer</h1>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">{{ error }}</div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị <span class="text-red-500">*</span></label>
          <SmartSelect v-model="form.asset" doctype="AC Asset" placeholder="Tìm thiết bị..." />
        </div>
        <div>
          <label for="at-type" class="block text-sm font-medium text-gray-700 mb-1">Loại chuyển giao <span class="text-red-500">*</span></label>
          <select id="at-type" v-model="form.transfer_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">-- Chọn --</option>
            <option v-for="t in TRANSFER_TYPES" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="at-date" class="block text-sm font-medium text-gray-700 mb-1">Ngày chuyển giao <span class="text-red-500">*</span></label>
          <input id="at-date" v-model="form.transfer_date" type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
        <div v-if="isLoan">
          <label for="at-return-date" class="block text-sm font-medium text-gray-700 mb-1">Ngày trả dự kiến <span class="text-red-500">*</span></label>
          <input id="at-return-date" v-model="form.expected_return_date" type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
      </div>

      <div class="border-t border-gray-100 pt-4">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Đến</p>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Vị trí mới <span class="text-red-500">*</span></label>
            <SmartSelect v-model="form.to_location" doctype="AC Location" placeholder="Tìm vị trí..." />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Phòng ban mới</label>
            <SmartSelect v-model="form.to_department" doctype="AC Department" placeholder="Tìm phòng ban..." />
          </div>
        </div>
      </div>

      <div>
        <label for="at-reason" class="block text-sm font-medium text-gray-700 mb-1">Lý do <span class="text-red-500">*</span></label>
        <textarea id="at-reason" v-model="form.reason" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="Mô tả lý do chuyển giao..."></textarea>
      </div>

      <div>
        <label for="at-notes" class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
        <textarea id="at-notes" v-model="form.notes" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"></textarea>
      </div>

      <button
        @click="submit"
        :disabled="saving"
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium"
      >{{ saving ? 'Đang tạo...' : 'Tạo Asset Transfer' }}</button>
    </div>
  </div>
</template>
