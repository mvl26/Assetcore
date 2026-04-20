<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { frappePost } from '@/api/helpers'
import SmartSelect from '@/components/common/SmartSelect.vue'

const router = useRouter()

const form = ref({
  contract_title: '',
  supplier: '',
  contract_type: '',
  contract_start: '',
  contract_end: '',
  contract_value: 0,
  auto_renew: false,
  sla_response_hours: 0,
  coverage_description: '',
  notes: '',
})

const saving = ref(false)
const error = ref('')

const TYPES = ['Preventive Maintenance', 'Calibration', 'Repair', 'Full Service', 'Warranty Extension']
const BASE = '/api/method/assetcore.api.imm00'

async function submit() {
  if (!form.value.contract_title || !form.value.supplier || !form.value.contract_type
      || !form.value.contract_start || !form.value.contract_end) {
    error.value = 'Vui lòng điền đầy đủ các trường bắt buộc (*).'
    return
  }
  if (new Date(form.value.contract_end) <= new Date(form.value.contract_start)) {
    error.value = 'Ngày kết thúc phải sau ngày bắt đầu.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await frappePost<void>(`${BASE}.create_service_contract`, {
      ...form.value,
      auto_renew: form.value.auto_renew ? 1 : 0,
    })
    router.push('/service-contracts')
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi tạo hợp đồng'
  }
  saving.value = false
}

</script>

<template>
  <div class="max-w-2xl mx-auto p-6 space-y-6">
    <div class="flex items-center gap-3">
      <button @click="router.back()" class="text-gray-500 hover:text-gray-700 text-sm">← Quay lại</button>
      <h1 class="text-xl font-semibold text-gray-800">Tạo Hợp đồng dịch vụ</h1>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">{{ error }}</div>

      <div>
        <label for="sc-title" class="block text-sm font-medium text-gray-700 mb-1">Tên hợp đồng <span class="text-red-500">*</span></label>
        <input id="sc-title" v-model="form.contract_title" type="text" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">NCC <span class="text-red-500">*</span></label>
          <SmartSelect v-model="form.supplier" doctype="AC Supplier" placeholder="Tìm nhà cung cấp..." />
        </div>
        <div>
          <label for="sc-type" class="block text-sm font-medium text-gray-700 mb-1">Loại HĐ <span class="text-red-500">*</span></label>
          <select id="sc-type" v-model="form.contract_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">-- Chọn --</option>
            <option v-for="t in TYPES" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="sc-start" class="block text-sm font-medium text-gray-700 mb-1">Bắt đầu <span class="text-red-500">*</span></label>
          <input id="sc-start" v-model="form.contract_start" type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
        <div>
          <label for="sc-end" class="block text-sm font-medium text-gray-700 mb-1">Kết thúc <span class="text-red-500">*</span></label>
          <input id="sc-end" v-model="form.contract_end" type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="sc-value" class="block text-sm font-medium text-gray-700 mb-1">Giá trị HĐ (VND)</label>
          <input id="sc-value" v-model.number="form.contract_value" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
        <div>
          <label for="sc-sla" class="block text-sm font-medium text-gray-700 mb-1">SLA phản hồi (giờ)</label>
          <input id="sc-sla" v-model.number="form.sla_response_hours" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
      </div>

      <label class="flex items-center gap-2 cursor-pointer">
        <input id="sc-renew" type="checkbox" v-model="form.auto_renew" class="w-4 h-4 rounded" />
        <span class="text-sm text-gray-700">Tự động gia hạn</span>
      </label>

      <div>
        <label for="sc-coverage" class="block text-sm font-medium text-gray-700 mb-1">Phạm vi dịch vụ</label>
        <textarea id="sc-coverage" v-model="form.coverage_description" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"></textarea>
      </div>

      <div>
        <label for="sc-notes" class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
        <textarea id="sc-notes" v-model="form.notes" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"></textarea>
      </div>

      <button
        @click="submit"
        :disabled="saving"
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium"
      >{{ saving ? 'Đang tạo...' : 'Tạo Hợp đồng' }}</button>
    </div>
  </div>
</template>
