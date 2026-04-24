<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useImm01Store } from '@/stores/imm01'
import SmartSelect from '@/components/common/SmartSelect.vue'
import type { MasterItem } from '@/stores/useMasterDataStore'

const router = useRouter()
const store  = useImm01Store()

// ─── Form state ────────────────────────────────────────────────────────────────

const form = ref({
  requesting_dept:        '',
  equipment_type:         '',
  quantity:               1,
  estimated_budget:       null as number | null,
  clinical_justification: '',
  priority:               'Medium' as string,
  linked_device_model:    '',
  current_equipment_age:  null as number | null,
  failure_frequency:      '',
  technical_specification: '',
})

const PRIORITY_OPTIONS = ['Low', 'Medium', 'High', 'Critical']
const FAILURE_FREQ_OPTIONS = ['Rarely', 'Occasionally', 'Frequently', 'Constant']

// ─── Validation ───────────────────────────────────────────────────────────────

type RequiredField = 'requesting_dept' | 'equipment_type' | 'quantity' | 'estimated_budget' | 'clinical_justification'

const FIELD_LABELS: Record<RequiredField, string> = {
  requesting_dept:        'Khoa đề xuất',
  equipment_type:         'Loại thiết bị',
  quantity:               'Số lượng',
  estimated_budget:       'Ngân sách ước tính',
  clinical_justification: 'Lý do lâm sàng',
}

const fieldErrors = ref<Partial<Record<RequiredField, string>>>({})

function validateField(field: RequiredField) {
  const val = form.value[field]
  if (field === 'quantity' && (Number(val) < 1 || !Number.isInteger(Number(val)))) {
    fieldErrors.value[field] = 'Số lượng phải là số nguyên dương'
    return
  }
  if (field === 'estimated_budget' && Number(val) <= 0) {
    fieldErrors.value[field] = 'Ngân sách phải lớn hơn 0'
    return
  }
  if (field === 'clinical_justification' && String(val).trim().length < 50) {
    fieldErrors.value[field] = 'Lý do lâm sàng phải ít nhất 50 ký tự'
    return
  }
  if (!val && val !== 0) {
    fieldErrors.value[field] = `${FIELD_LABELS[field]} là bắt buộc`
    return
  }
  delete fieldErrors.value[field]
}

function validateAll(): boolean {
  ;(Object.keys(FIELD_LABELS) as RequiredField[]).forEach(validateField)
  return Object.keys(fieldErrors.value).length === 0
}

// ─── Submit ───────────────────────────────────────────────────────────────────

const submitError = ref<string | null>(null)

async function handleSubmit() {
  submitError.value = null
  if (!validateAll()) return
  store.clearError()

  const name = await store.createNA({
    requesting_dept:        form.value.requesting_dept,
    equipment_type:         form.value.equipment_type,
    quantity:               form.value.quantity,
    estimated_budget:       form.value.estimated_budget!,
    clinical_justification: form.value.clinical_justification,
    priority:               form.value.priority,
    linked_device_model:    form.value.linked_device_model || undefined,
    current_equipment_age:  form.value.current_equipment_age ?? undefined,
    failure_frequency:      form.value.failure_frequency || undefined,
    technical_specification: form.value.technical_specification || undefined,
  })

  if (name) {
    router.push(`/planning/needs-assessments/${name}`)
  } else {
    submitError.value = store.error ?? 'Tạo phiếu thất bại'
  }
}

function onDeptSelect(item: MasterItem) {
  form.value.requesting_dept = item.id
  validateField('requesting_dept')
}

function onModelSelect(item: MasterItem) {
  form.value.linked_device_model = item.id
}

function onTsSelect(item: MasterItem) {
  form.value.technical_specification = item.id
}

const justificationLength = () => form.value.clinical_justification.trim().length
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Breadcrumb -->
    <nav class="flex items-center gap-1.5 text-xs text-slate-400 mb-6">
      <button class="hover:text-slate-600 transition-colors"
              @click="router.push('/planning/needs-assessments')">
        Đánh giá Nhu cầu
      </button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <span class="text-slate-700 font-medium">Tạo phiếu mới</span>
    </nav>

    <!-- Page title -->
    <div class="mb-7">
      <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-01</p>
      <h1 class="text-2xl font-bold text-slate-900">Tạo Đánh giá Nhu cầu</h1>
      <p class="text-sm text-slate-500 mt-1">Điền đầy đủ thông tin để gửi đề xuất trang bị thiết bị y tế.</p>
    </div>

    <!-- Error banner -->
    <div v-if="submitError" class="alert-error mb-6">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ submitError }}</span>
      <button class="text-red-400 hover:text-red-600 transition-colors" @click="submitError = null">✕</button>
    </div>

    <form class="space-y-6" @submit.prevent="handleSubmit">

      <!-- Card 1: Thông tin thiết bị -->
      <div class="card">
        <h2 class="text-sm font-semibold text-slate-700 mb-5 pb-3 border-b border-slate-100">
          Thông tin Thiết bị
        </h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">

          <!-- Khoa đề xuất -->
          <div class="form-group">
            <p class="form-label">Khoa / Phòng đề xuất <span class="text-red-500">*</span></p>
            <SmartSelect
              doctype="AC Department"
              placeholder="Chọn khoa..."
              :model-value="form.requesting_dept"
              :has-error="!!fieldErrors.requesting_dept"
              @select="onDeptSelect"
            />
            <p v-if="fieldErrors.requesting_dept" class="mt-1 text-xs text-red-500">
              {{ fieldErrors.requesting_dept }}
            </p>
          </div>

          <!-- Loại thiết bị -->
          <div class="form-group">
            <label for="equipment_type" class="form-label">
              Loại / Tên thiết bị <span class="text-red-500">*</span>
            </label>
            <input
              id="equipment_type"
              v-model="form.equipment_type"
              type="text"
              class="form-input"
              placeholder="vd: Máy siêu âm, Máy xét nghiệm..."
              @blur="validateField('equipment_type')"
            />
            <p v-if="fieldErrors.equipment_type" class="mt-1 text-xs text-red-500">
              {{ fieldErrors.equipment_type }}
            </p>
          </div>

          <!-- Model liên kết -->
          <div class="form-group">
            <p class="form-label">
              Model thiết bị
              <span class="text-xs font-normal text-slate-400 ml-1">(tùy chọn)</span>
            </p>
            <SmartSelect
              doctype="IMM Device Model"
              placeholder="Tìm model..."
              :model-value="form.linked_device_model"
              @select="onModelSelect"
            />
          </div>

          <!-- Ưu tiên -->
          <div class="form-group">
            <label for="priority" class="form-label">Mức độ ưu tiên</label>
            <select id="priority" v-model="form.priority" class="form-select">
              <option v-for="p in PRIORITY_OPTIONS" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>

        </div>
      </div>

      <!-- Card 2: Số lượng & Ngân sách -->
      <div class="card">
        <h2 class="text-sm font-semibold text-slate-700 mb-5 pb-3 border-b border-slate-100">
          Số lượng &amp; Ngân sách
        </h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">

          <div class="form-group">
            <label for="quantity" class="form-label">
              Số lượng <span class="text-red-500">*</span>
            </label>
            <input
              id="quantity"
              v-model.number="form.quantity"
              type="number"
              min="1"
              step="1"
              class="form-input"
              @blur="validateField('quantity')"
            />
            <p v-if="fieldErrors.quantity" class="mt-1 text-xs text-red-500">
              {{ fieldErrors.quantity }}
            </p>
          </div>

          <div class="form-group">
            <label for="estimated_budget" class="form-label">
              Ngân sách ước tính (VNĐ) <span class="text-red-500">*</span>
            </label>
            <input
              id="estimated_budget"
              v-model.number="form.estimated_budget"
              type="number"
              min="0"
              step="1000000"
              class="form-input"
              placeholder="0"
              @blur="validateField('estimated_budget')"
            />
            <p v-if="fieldErrors.estimated_budget" class="mt-1 text-xs text-red-500">
              {{ fieldErrors.estimated_budget }}
            </p>
            <p v-if="form.estimated_budget && !fieldErrors.estimated_budget"
               class="mt-1 text-xs text-slate-400">
              ≈ {{ new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(form.estimated_budget) }}
            </p>
          </div>

        </div>
      </div>

      <!-- Card 3: Lý do lâm sàng -->
      <div class="card">
        <h2 class="text-sm font-semibold text-slate-700 mb-5 pb-3 border-b border-slate-100">
          Lý do Lâm sàng
        </h2>
        <div class="space-y-5">

          <div class="form-group">
            <label for="clinical_justification" class="form-label">
              Mô tả nhu cầu <span class="text-red-500">*</span>
            </label>
            <textarea
              id="clinical_justification"
              v-model="form.clinical_justification"
              rows="5"
              class="form-textarea"
              placeholder="Mô tả chi tiết lý do cần trang bị, tình trạng hiện tại, tác động lâm sàng... (tối thiểu 50 ký tự)"
              @blur="validateField('clinical_justification')"
            />
            <div class="flex items-start justify-between mt-1">
              <p v-if="fieldErrors.clinical_justification" class="text-xs text-red-500">
                {{ fieldErrors.clinical_justification }}
              </p>
              <p v-else class="text-xs text-slate-400">Tối thiểu 50 ký tự</p>
              <span class="text-xs shrink-0 ml-2"
                    :class="justificationLength() >= 50 ? 'text-emerald-500' : 'text-slate-400'">
                {{ justificationLength() }} ký tự
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">

            <div class="form-group">
              <label for="equipment_age" class="form-label">
                Tuổi thiết bị hiện tại (năm)
                <span class="text-xs font-normal text-slate-400 ml-1">(nếu có)</span>
              </label>
              <input
                id="equipment_age"
                v-model.number="form.current_equipment_age"
                type="number"
                min="0"
                class="form-input"
                placeholder="0"
              />
            </div>

            <div class="form-group">
              <label for="failure_freq" class="form-label">
                Tần suất hỏng hóc
                <span class="text-xs font-normal text-slate-400 ml-1">(nếu có)</span>
              </label>
              <select id="failure_freq" v-model="form.failure_frequency" class="form-select">
                <option value="">— Không xác định —</option>
                <option v-for="f in FAILURE_FREQ_OPTIONS" :key="f" :value="f">{{ f }}</option>
              </select>
            </div>

          </div>
        </div>
      </div>

      <!-- Card 4: Đặc tả thiết bị -->
      <div class="card">
        <h2 class="text-sm font-semibold text-slate-700 mb-5 pb-3 border-b border-slate-100">
          Đặc tả thiết bị
          <span class="text-xs font-normal text-slate-400 ml-1">(tùy chọn — có thể tạo sau)</span>
        </h2>
        <div class="form-group">
          <p class="form-label">Chọn đặc tả kỹ thuật đã có</p>
          <SmartSelect
            doctype="Technical Specification"
            placeholder="Tìm đặc tả kỹ thuật..."
            :model-value="form.technical_specification"
            @select="onTsSelect"
          />
          <p class="mt-1 text-xs text-slate-400">
            Nếu chưa có, để trống và tạo đặc tả sau khi phiếu được duyệt.
          </p>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3 pt-2">
        <button
          type="button"
          class="btn-ghost"
          :disabled="store.loading"
          @click="router.push('/planning/needs-assessments')"
        >
          Hủy
        </button>
        <button type="submit" class="btn-primary" :disabled="store.loading">
          <svg v-if="store.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <span>{{ store.loading ? 'Đang lưu...' : 'Tạo phiếu' }}</span>
        </button>
      </div>

    </form>
  </div>
</template>
