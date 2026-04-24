<script setup lang="ts">
import { ref, watch } from 'vue'
import { useImm13Store } from '@/stores/imm13'
import { useRouter } from 'vue-router'

const store = useImm13Store()
const router = useRouter()

const assetInput = ref('')
const checkingEligibility = ref(false)
const submitting = ref(false)

const form = ref({
  asset: '',
  suspension_reason: '',
  reason_details: '',
  condition_at_suspension: '',
  current_book_value: 0,
  biological_hazard: false,
  bio_hazard_clearance: '',
  data_destruction_required: false,
  regulatory_clearance_required: false,
})

const SUSPENSION_REASONS = [
  { value: 'End_of_Life', label: 'Hết tuổi thọ' },
  { value: 'Cannot_Repair', label: 'Không thể sửa chữa' },
  { value: 'Regulatory', label: 'Yêu cầu pháp lý' },
  { value: 'Upgrade', label: 'Nâng cấp thiết bị' },
  { value: 'Transfer', label: 'Điều chuyển đơn vị' },
  { value: 'Other', label: 'Khác' },
]

const CONDITION_OPTIONS = [
  { value: 'Working', label: 'Còn hoạt động' },
  { value: 'Degraded', label: 'Hoạt động kém' },
  { value: 'Non_Functional', label: 'Không hoạt động' },
  { value: 'Damaged', label: 'Hư hỏng nặng' },
]

async function checkEligibility() {
  if (!assetInput.value.trim()) return
  checkingEligibility.value = true
  store.eligibility = null
  form.value.asset = ''
  try {
    await store.checkEligibility(assetInput.value.trim())
    const elig = store.eligibility as { eligible: boolean } | null
    if (elig?.eligible) {
      form.value.asset = assetInput.value.trim()
    }
  } finally {
    checkingEligibility.value = false
  }
}

async function submit() {
  if (!form.value.asset || !form.value.suspension_reason) return
  submitting.value = true
  const name = await store.doCreateRequest({
    asset: form.value.asset,
    suspension_reason: form.value.suspension_reason,
    reason_details: form.value.reason_details,
    condition_at_suspension: form.value.condition_at_suspension,
    current_book_value: form.value.current_book_value,
    biological_hazard: form.value.biological_hazard ? 1 : 0,
    data_destruction_required: form.value.data_destruction_required ? 1 : 0,
    regulatory_clearance_required: form.value.regulatory_clearance_required ? 1 : 0,
  })
  submitting.value = false
  if (name) {
    router.push(`/decommission/${name}`)
  }
}

watch(assetInput, () => {
  store.eligibility = null
  form.value.asset = ''
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <button class="text-slate-400 hover:text-slate-600" @click="router.back()">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest">IMM-13</p>
        <h1 class="text-2xl font-bold text-slate-900">Tạo Phiếu Ngừng sử dụng</h1>
      </div>
    </div>

    <div class="max-w-2xl">
      <div class="bg-white rounded-xl shadow-sm border p-6 space-y-5">

        <!-- Asset field + eligibility check -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Thiết bị <span class="text-red-500">*</span></label>
          <div class="flex gap-2">
            <input
              v-model="assetInput"
              type="text"
              placeholder="Nhập mã thiết bị (ví dụ: ACC-0001)"
              class="form-input flex-1"
              @keyup.enter="checkEligibility"
            />
            <button
              :disabled="!assetInput.trim() || checkingEligibility"
              class="px-4 py-2 bg-slate-600 text-white rounded-lg text-sm font-medium hover:bg-slate-700 disabled:opacity-50 transition-colors whitespace-nowrap"
              @click="checkEligibility"
            >
              {{ checkingEligibility ? 'Đang kiểm tra...' : 'Kiểm tra' }}
            </button>
          </div>

          <!-- Eligibility result -->
          <div v-if="store.eligibility" class="mt-3 p-3 rounded-lg border text-sm"
            :class="store.eligibility.eligible
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'"
          >
            <div class="font-semibold mb-1">
              {{ store.eligibility.eligible ? '✓ Thiết bị đủ điều kiện tạo phiếu' : '✗ Thiết bị chưa đủ điều kiện' }}
            </div>
            <div v-if="store.eligibility.asset_name" class="text-xs opacity-80 mb-1">
              Tên: {{ store.eligibility.asset_name }} · Trạng thái: {{ store.eligibility.asset_status }}
            </div>
            <ul v-if="store.eligibility.reasons.length" class="list-disc list-inside space-y-0.5 text-xs">
              <li v-for="(r, i) in store.eligibility.reasons" :key="i">{{ r }}</li>
            </ul>
          </div>

          <div v-if="store.error" class="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {{ store.error }}
          </div>
        </div>

        <!-- Suspension reason -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Lý do ngừng sử dụng <span class="text-red-500">*</span></label>
          <select v-model="form.suspension_reason" class="form-select w-full">
            <option value="">Chọn lý do...</option>
            <option v-for="r in SUSPENSION_REASONS" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>

        <!-- Reason details -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Chi tiết lý do</label>
          <textarea
            v-model="form.reason_details"
            rows="3"
            placeholder="Mô tả chi tiết lý do ngừng sử dụng..."
            class="form-input w-full"
          />
        </div>

        <!-- Condition at suspension -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Tình trạng thiết bị khi ngừng</label>
          <select v-model="form.condition_at_suspension" class="form-select w-full">
            <option value="">Chọn tình trạng...</option>
            <option v-for="c in CONDITION_OPTIONS" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
        </div>

        <!-- Current book value -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Giá trị sổ sách hiện tại (VNĐ)</label>
          <input
            v-model.number="form.current_book_value"
            type="number"
            min="0"
            step="1000000"
            class="form-input w-full"
            placeholder="0"
          />
        </div>

        <!-- Compliance flags -->
        <div class="space-y-3 pt-2 border-t border-slate-100">
          <p class="text-sm font-medium text-slate-700">Yêu cầu tuân thủ</p>

          <!-- Biological hazard -->
          <div>
            <label class="flex items-center gap-2 cursor-pointer">
              <input v-model="form.biological_hazard" type="checkbox" class="rounded border-slate-300 text-blue-600" />
              <span class="text-sm text-slate-700">Thiết bị có nguy cơ sinh học</span>
            </label>
            <div v-if="form.biological_hazard" class="mt-2 ml-6">
              <label class="block text-xs text-slate-500 mb-1">Biện pháp xử lý an toàn sinh học (bắt buộc)</label>
              <textarea
                v-model="form.bio_hazard_clearance"
                rows="2"
                placeholder="Mô tả biện pháp xử lý..."
                class="form-input w-full text-sm"
              />
            </div>
          </div>

          <!-- Data destruction -->
          <label class="flex items-center gap-2 cursor-pointer">
            <input v-model="form.data_destruction_required" type="checkbox" class="rounded border-slate-300 text-blue-600" />
            <span class="text-sm text-slate-700">Yêu cầu xóa dữ liệu bệnh nhân</span>
          </label>

          <!-- Regulatory clearance -->
          <label class="flex items-center gap-2 cursor-pointer">
            <input v-model="form.regulatory_clearance_required" type="checkbox" class="rounded border-slate-300 text-blue-600" />
            <span class="text-sm text-slate-700">Yêu cầu giấy phép cơ quan quản lý</span>
          </label>
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-3 pt-2">
          <button class="btn-ghost" @click="router.back()">Hủy</button>
          <button
            :disabled="!form.asset || !form.suspension_reason || submitting"
            class="btn-primary disabled:opacity-50"
            @click="submit"
          >
            {{ submitting ? 'Đang tạo...' : 'Tạo phiếu' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
