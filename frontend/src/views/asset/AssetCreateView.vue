<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
// Copyright (c) 2026, AssetCore Team
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { createAsset, getDeviceModel } from '@/api/imm00'
import SmartSelect from '@/components/common/SmartSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useFormDraft } from '@/composables/useFormDraft'
import type { AcAsset } from '@/types/imm00'

const router = useRouter()

const saving = ref(false)
const error = ref<string | null>(null)
// Lỗi inline cạnh ô Danh mục (parity BE reqd=1 — chặn payload rỗng âm thầm).
const categoryError = ref('')

const form = ref<Partial<AcAsset>>({
  asset_name: '',
  asset_category: '',
  device_model: '',
  department: '',
  location: '',
  supplier: '',
  lifecycle_status: 'Commissioned',
  is_pm_required: 0,
  is_calibration_required: 0,
  gross_purchase_amount: 0,
})

const { clear: clearDraft } = useFormDraft('asset-create', form)

// BR-00-FE-02: khi chọn model → auto-fill PM/Cal + gmdn_code + medical_device_class
watch(() => form.value.device_model, async (modelName) => {
  if (!modelName) return
  try {
    const model = await getDeviceModel(modelName)
    if (!model) return
    form.value.is_pm_required = model.is_pm_required ?? 0
    form.value.pm_interval_days = model.pm_interval_days
    form.value.is_calibration_required = model.is_calibration_required ?? 0
    form.value.calibration_interval_days = model.calibration_interval_days
    if (model.medical_device_class) form.value.medical_device_class = model.medical_device_class
    if (!form.value.gmdn_code && model.gmdn_code) form.value.gmdn_code = model.gmdn_code
  } catch {
    // silent — user có thể điền tay
  }
})

// BR-00-FE-01: đổi danh mục → reset model + PM/Cal
function onCategoryChange() {
  // Chọn/đổi danh mục → xoá lỗi inline reqd (nếu trước đó submit thiếu).
  if (form.value.asset_category) categoryError.value = ''
  form.value.device_model = ''
  form.value.is_pm_required = 0
  form.value.pm_interval_days = undefined
  form.value.is_calibration_required = 0
  form.value.calibration_interval_days = undefined
  form.value.medical_device_class = undefined
  form.value.gmdn_code = ''
}

// D4 (ADR-IMM00-ASSETCODE): pattern parity với BE _ASSET_CODE_PATTERN ở ac_asset.py.
// Mã tài sản chỉ chứa chữ/số + . _ - / (không khoảng trắng, không unicode dấu).
const ASSET_CODE_PATTERN = /^[A-Za-z0-9._\-/]+$/

const assetCodeError = computed(() => {
  const raw = form.value.asset_code?.trim()
  if (!raw) return '' // trống = hợp lệ (BE tự sinh)
  return ASSET_CODE_PATTERN.test(raw)
    ? ''
    : 'Mã tài sản chỉ được chứa chữ, số và các ký tự . _ - / (không khoảng trắng, không dấu).'
})

async function submit() {
  categoryError.value = ''
  if (!form.value.asset_name?.trim()) {
    error.value = 'Tên thiết bị là bắt buộc'
    return
  }
  // B2 parity BE reqd=1: chặn gửi payload thiếu Danh mục — KHÔNG để BE trả 422 sau.
  if (!form.value.asset_category?.trim()) {
    categoryError.value = 'Vui lòng chọn Danh mục thiết bị'
    error.value = categoryError.value
    return
  }
  // D4: chặn sớm sai pattern asset_code (FE-parity với BE) trước khi gửi.
  if (assetCodeError.value) {
    error.value = assetCodeError.value
    return
  }
  // Trim asset_code: '  TS-001  ' → 'TS-001' (parity test_asset_code_whitespace_trimmed).
  const trimmedCode = form.value.asset_code?.trim()
  if (trimmedCode) form.value.asset_code = trimmedCode
  saving.value = true
  error.value = null
  try {
    const res = await createAsset(form.value)
    if (res?.name) {
      clearDraft()
      router.push(`/assets/${res.name}`)
    }
    else error.value = 'Không thể lưu thiết bị. Vui lòng kiểm tra lại thông tin.'
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}

</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      back-to="/assets"
      title="Thêm thiết bị mới"
      :breadcrumb="[
        { label: 'Thiết bị', to: '/assets' },
        { label: 'Tạo mới' },
      ]"
    />

    <div v-if="error" class="alert-error mb-4">{{ error }}</div>

    <form class="space-y-5" @submit.prevent="submit">
      <!-- Section: Thông tin cơ bản -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Thông tin cơ bản</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="md:col-span-2">
            <label class="form-label">Tên thiết bị <span class="text-red-500">*</span></label>
            <input v-model="form.asset_name" type="text" class="form-input w-full" placeholder="VD: Máy X-quang Philips DR-X" required />
          </div>
          <!-- D1/D4 (ADR-IMM00-ASSETCODE): Mã tài sản = định danh nội bộ (PK), KHÁC Số serial NSX -->
          <div class="md:col-span-2">
            <label for="asset_code" class="form-label">Mã tài sản</label>
            <input
              id="asset_code"
              v-model="form.asset_code"
              type="text"
              class="form-input w-full font-mono"
              :class="{ 'border-red-400': assetCodeError }"
              placeholder="VD: TS-LAB-001 (để trống = hệ thống tự sinh)"
              autocomplete="off"
              :aria-invalid="!!assetCodeError"
              aria-describedby="asset_code_help"
            />
            <p id="asset_code_help" class="mt-1 text-xs text-slate-500">
              Để trống = hệ thống tự sinh; nhập = dùng làm mã định danh, không sửa được sau khi tạo.
            </p>
            <p v-if="assetCodeError" class="mt-1 text-xs text-red-600">{{ assetCodeError }}</p>
          </div>
          <div>
            <label class="form-label">Danh mục <span class="text-red-500">*</span></label>
            <SmartSelect
              v-model="form.asset_category"
              doctype="AC Asset Category"
              placeholder="Tìm danh mục..."
              @select="onCategoryChange"
              @clear="onCategoryChange"
            />
            <p v-if="categoryError" class="mt-1 text-xs text-red-600" role="alert">{{ categoryError }}</p>
          </div>
          <div>
            <label class="form-label">
              Model thiết bị
              <span v-if="form.asset_category" class="text-[10px] font-normal text-blue-500 ml-1">(đã lọc theo danh mục)</span>
            </label>
            <SmartSelect
              v-model="form.device_model"
              doctype="IMM Device Model"
              :filters="form.asset_category ? { asset_category: form.asset_category } : undefined"
              placeholder="Tìm model..."
            />
          </div>
          <div>
            <label class="form-label">Khoa/Phòng</label>
            <SmartSelect v-model="form.department" doctype="AC Department" placeholder="Tìm khoa/phòng..." />
          </div>
          <div>
            <label class="form-label">Vị trí lắp đặt</label>
            <SmartSelect v-model="form.location" doctype="AC Location" placeholder="Tìm vị trí..." />
          </div>
          <div>
            <label class="form-label">Nhà cung cấp</label>
            <SmartSelect v-model="form.supplier" doctype="AC Supplier" placeholder="Tìm nhà cung cấp..." />
          </div>
          <div>
            <label class="form-label">Trạng thái ban đầu</label>
            <select v-model="form.lifecycle_status" class="form-select w-full">
              <option value="Commissioned">Đã tiếp nhận</option>
              <option value="Active">Đang hoạt động</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Section: Mua sắm -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Thông tin mua sắm</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Ngày mua</label>
            <DateInput v-model="form.purchase_date" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Giá mua (VND)</label>
            <input v-model.number="form.gross_purchase_amount" type="number" min="0" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Ngày bảo hành hết hạn</label>
            <DateInput v-model="form.warranty_expiry_date" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Ngày commissioning</label>
            <DateInput v-model="form.commissioning_date" class="form-input w-full" />
          </div>
        </div>
      </div>

      <!-- Section: Nhận dạng HTM -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Nhận dạng HTM / Pháp lý</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- D1/D4: Số serial NSX = field nghiệp vụ riêng, KHÔNG phải mã định danh tài sản -->
          <div>
            <label for="manufacturer_sn" class="form-label">Số serial NSX</label>
            <input id="manufacturer_sn" v-model="form.manufacturer_sn" type="text" class="form-input w-full font-mono" placeholder="SN-XXXX-0001" aria-describedby="manufacturer_sn_help" />
            <p id="manufacturer_sn_help" class="mt-1 text-xs text-slate-500">
              Số serial của nhà sản xuất (NSX). Field nghiệp vụ — KHÔNG phải mã định danh tài sản.
            </p>
          </div>
          <div>
            <label class="form-label">UDI Code</label>
            <input v-model="form.udi_code" type="text" class="form-input w-full font-mono" />
          </div>
          <div>
            <label class="form-label">
              GMDN Code
              <span v-if="form.device_model" class="ml-1 text-[10px] font-normal text-blue-500">(tự điền từ model)</span>
            </label>
            <input v-model="form.gmdn_code" type="text" class="form-input w-full" placeholder="Kế thừa từ Model thiết bị" />
          </div>
          <div>
            <label class="form-label">Phân loại y tế</label>
            <select v-model="form.medical_device_class" class="form-select w-full">
              <option value="">— Chọn mức phân loại —</option>
              <option value="Class I">Loại I — Rủi ro thấp</option>
              <option value="Class II">Loại II — Rủi ro trung bình</option>
              <option value="Class III">Loại III — Rủi ro cao</option>
            </select>
          </div>
          <div>
            <label class="form-label">Số đăng ký Bộ Y tế</label>
            <input v-model="form.byt_reg_no" type="text" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Hạn đăng ký Bộ Y tế</label>
            <DateInput v-model="form.byt_reg_expiry" class="form-input w-full" />
          </div>
        </div>
      </div>

      <!-- Section: Bảo trì / Hiệu chuẩn -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
          Lịch bảo trì & Hiệu chuẩn
          <span v-if="form.device_model" class="text-[10px] font-normal text-blue-500 ml-2">(tự điền từ model — có thể chỉnh)</span>
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex items-center gap-3">
            <input id="pm_check" v-model="form.is_pm_required" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 text-blue-600 rounded" />
            <label for="pm_check" class="text-sm text-slate-700">Yêu cầu bảo trì định kỳ</label>
          </div>
          <div v-if="form.is_pm_required">
            <label class="form-label">Chu kỳ bảo trì (ngày)</label>
            <input v-model.number="form.pm_interval_days" type="number" min="1" class="form-input w-full" />
          </div>
          <div class="flex items-center gap-3">
            <input id="cal_check" v-model="form.is_calibration_required" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 text-blue-600 rounded" />
            <label for="cal_check" class="text-sm text-slate-700">Yêu cầu hiệu chuẩn</label>
          </div>
          <div v-if="form.is_calibration_required">
            <label class="form-label">Chu kỳ hiệu chuẩn (ngày)</label>
            <input v-model.number="form.calibration_interval_days" type="number" min="1" class="form-input w-full" />
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-3 justify-end">
        <button type="button" class="btn-ghost" @click="router.push('/assets')">Huỷ</button>
        <button type="submit" class="btn-primary" :disabled="saving">
          {{ saving ? 'Đang lưu...' : 'Lưu thiết bị' }}
        </button>
      </div>
    </form>
  </div>
</template>
