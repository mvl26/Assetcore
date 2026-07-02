<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { frappePost } from '@/api/helpers'
import SmartSelect from '@/components/common/SmartSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useFormDraft } from '@/composables/useFormDraft'
import { numToWordsVi } from '@/utils/numToWordsVi'

const router = useRouter()

const form = ref({
  contract_code: '',
  contract_title: '',
  supplier: '',
  contract_type: '',
  sign_date: '',
  contract_start: '',
  contract_end: '',
  contract_value: 0,
  amount_in_words: '',
  auto_renew: false,
  sla_response_hours: 0,
  coverage_description: '',
  notes: '',
  covered_assets: [] as { asset: string; coverage_note: string }[],
})

function addAssetRow() {
  form.value.covered_assets.push({ asset: '', coverage_note: '' })
}
function removeAssetRow(idx: number) {
  form.value.covered_assets.splice(idx, 1)
}

// Hiển thị contract_value với dấu phân cách hàng nghìn, lưu giá trị số.
const contractValueDisplay = computed<string>({
  get: () => form.value.contract_value
    ? new Intl.NumberFormat('vi-VN').format(form.value.contract_value)
    : '',
  set: (v: string) => {
    const n = Number(String(v).replace(/[^\d]/g, ''))
    form.value.contract_value = Number.isFinite(n) ? n : 0
  },
})

// "Số tiền bằng chữ" — tự suy ra từ giá trị HĐ (preview); BE tính lại khi lưu.
const amountInWords = computed<string>(() => numToWordsVi(form.value.contract_value))

const { clear: clearDraft } = useFormDraft('service-contract-create', form)

const saving = ref(false)
const error = ref('')

const TYPES: { value: string; label: string }[] = [
  { value: 'Preventive Maintenance', label: 'Bảo trì định kỳ' },
  { value: 'Calibration', label: 'Hiệu chuẩn' },
  { value: 'Repair', label: 'Sửa chữa' },
  { value: 'Full Service', label: 'Trọn gói' },
  { value: 'Warranty Extension', label: 'Gia hạn bảo hành' },
]
const BASE = '/api/method/assetcore.api.imm00'

async function submit() {
  if (!form.value.contract_code || !form.value.contract_title || !form.value.supplier
      || !form.value.contract_type || !form.value.contract_start || !form.value.contract_end) {
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
      amount_in_words: amountInWords.value,
      auto_renew: form.value.auto_renew ? 1 : 0,
      covered_assets: JSON.stringify(
        form.value.covered_assets.filter(r => r.asset),
      ),
    })
    clearDraft()
    router.push('/service-contracts')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Lỗi khi tạo hợp đồng'
  }
  saving.value = false
}

</script>

<template>
  <div class="page-container animate-fade-in space-y-6">
    <PageHeader
      back-to="/service-contracts"
      title="Tạo hợp đồng dịch vụ"
      :breadcrumb="[
        { label: 'Hợp đồng dịch vụ', to: '/service-contracts' },
        { label: 'Tạo mới' },
      ]"
    />

    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">{{ error }}</div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label for="sc-code" class="block text-sm font-medium text-gray-700 mb-1">Mã hợp đồng <span class="text-red-500">*</span></label>
          <input id="sc-code" v-model="form.contract_code" type="text" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="VD: HD-2026-001" />
        </div>
        <div>
          <label for="sc-sign-date" class="block text-sm font-medium text-gray-700 mb-1">Ngày ký</label>
          <DateInput id="sc-sign-date" v-model="form.sign_date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
      </div>

      <div>
        <label for="sc-title" class="block text-sm font-medium text-gray-700 mb-1">Tên hợp đồng <span class="text-red-500">*</span></label>
        <input id="sc-title" v-model="form.contract_title" type="text" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nhà cung cấp <span class="text-red-500">*</span></label>
          <SmartSelect v-model="form.supplier" doctype="AC Supplier" placeholder="Tìm nhà cung cấp..." />
        </div>
        <div>
          <label for="sc-type" class="block text-sm font-medium text-gray-700 mb-1">Loại HĐ <span class="text-red-500">*</span></label>
          <select id="sc-type" v-model="form.contract_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">-- Chọn --</option>
            <option v-for="t in TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label for="sc-start" class="block text-sm font-medium text-gray-700 mb-1">Bắt đầu <span class="text-red-500">*</span></label>
          <DateInput id="sc-start" v-model="form.contract_start" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
        <div>
          <label for="sc-end" class="block text-sm font-medium text-gray-700 mb-1">Kết thúc <span class="text-red-500">*</span></label>
          <DateInput id="sc-end" v-model="form.contract_end" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label for="sc-value" class="block text-sm font-medium text-gray-700 mb-1">Giá trị HĐ (VND)</label>
          <input id="sc-value" v-model="contractValueDisplay" type="text" inputmode="numeric" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="0" />
          <p v-if="amountInWords" class="mt-1 text-xs text-gray-500 italic">Bằng chữ: {{ amountInWords }}</p>
        </div>
        <div>
          <label for="sc-sla" class="block text-sm font-medium text-gray-700 mb-1">Cam kết mức dịch vụ phản hồi (giờ)</label>
          <input id="sc-sla" v-model.number="form.sla_response_hours" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
      </div>

      <label class="flex items-center gap-2 cursor-pointer">
        <input id="sc-renew" v-model="form.auto_renew" type="checkbox" class="w-4 h-4 rounded" />
        <span class="text-sm text-gray-700">Tự động gia hạn</span>
      </label>

      <div>
        <label for="sc-coverage" class="block text-sm font-medium text-gray-700 mb-1">Phạm vi dịch vụ</label>
        <textarea id="sc-coverage" v-model="form.coverage_description" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"></textarea>
      </div>

      <div class="border-t border-gray-100 pt-5">
        <div class="flex items-center justify-between mb-2">
          <label class="block text-sm font-medium text-gray-700">Thiết bị thuộc hợp đồng</label>
          <button
            type="button"
            class="text-sm px-3 py-1.5 border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 font-medium"
            @click="addAssetRow"
          >+ Thêm thiết bị</button>
        </div>

        <p v-if="form.covered_assets.length === 0" class="text-sm text-gray-400 italic py-3">
          Chưa có thiết bị nào — nhấn "Thêm thiết bị" để gắn thiết bị vào hợp đồng.
        </p>

        <div v-else class="space-y-2">
          <div
            v-for="(row, idx) in form.covered_assets"
            :key="idx"
            class="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-2 items-start"
          >
            <SmartSelect
              v-model="row.asset"
              doctype="AC Asset"
              placeholder="Chọn thiết bị..."
            />
            <input
              v-model="row.coverage_note"
              type="text"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="Ghi chú phạm vi (tùy chọn)"
            />
            <button
              type="button"
              class="px-3 py-2 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
              title="Xóa dòng"
              @click="removeAssetRow(idx)"
            >Xóa</button>
          </div>
        </div>
      </div>

      <div>
        <label for="sc-notes" class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
        <textarea id="sc-notes" v-model="form.notes" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"></textarea>
      </div>

      <button
        :disabled="saving"
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium"
        @click="submit"
      >
{{ saving ? 'Đang tạo...' : 'Tạo Hợp đồng' }}
</button>
    </div>
  </div>
</template>
