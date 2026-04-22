<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { createAsset } from '@/api/imm00'
import SmartSelect from '@/components/common/SmartSelect.vue'
import type { AcAsset } from '@/types/imm00'

const router = useRouter()

const saving = ref(false)
const error = ref<string | null>(null)

const form = ref<Partial<AcAsset>>({
  asset_name: '',
  asset_category: '',
  device_model: '',
  department: '',
  location: '',
  supplier: '',
  lifecycle_status: 'Commissioned',
  is_pm_required: 0,
  pm_interval_days: 90,
  is_calibration_required: 0,
  calibration_interval_days: 365,
  gross_purchase_amount: 0,
})

async function submit() {
  if (!form.value.asset_name?.trim()) {
    error.value = 'Tên thiết bị là bắt buộc'
    return
  }
  saving.value = true
  error.value = null
  try {
    const res = await createAsset(form.value) as unknown as { name?: string }
    if (res?.name) router.push(`/assets/${res.name}`)
    else error.value = 'Không thể lưu thiết bị. Vui lòng kiểm tra lại thông tin.'
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}

</script>

<template>
  <div class="page-container animate-fade-in max-w-3xl">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <button class="btn-ghost" @click="router.push('/assets')">← Quay lại</button>
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest">IMM-00</p>
        <h1 class="text-xl font-bold text-slate-900">Thêm thiết bị mới</h1>
      </div>
    </div>

    <div v-if="error" class="alert-error mb-4">{{ error }}</div>

    <form @submit.prevent="submit" class="space-y-5">
      <!-- Section: Thông tin cơ bản -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Thông tin cơ bản</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="md:col-span-2">
            <label class="form-label">Tên thiết bị <span class="text-red-500">*</span></label>
            <input v-model="form.asset_name" type="text" class="form-input w-full" placeholder="VD: Máy X-quang Philips DR-X" required />
          </div>
          <div>
            <label class="form-label">Danh mục</label>
            <SmartSelect v-model="form.asset_category" doctype="AC Asset Category" placeholder="Tìm danh mục..." />
          </div>
          <div>
            <label class="form-label">Model thiết bị</label>
            <SmartSelect v-model="form.device_model" doctype="IMM Device Model" placeholder="Tìm model..." />
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
            <SmartSelect v-model="form.supplier" doctype="AC Supplier" placeholder="Tìm NCC..." />
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
            <input v-model="form.purchase_date" type="date" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Giá mua (VND)</label>
            <input v-model.number="form.gross_purchase_amount" type="number" min="0" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Ngày bảo hành hết hạn</label>
            <input v-model="form.warranty_expiry_date" type="date" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Ngày commissioning</label>
            <input v-model="form.commissioning_date" type="date" class="form-input w-full" />
          </div>
        </div>
      </div>

      <!-- Section: Nhận dạng HTM -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Nhận dạng HTM / Pháp lý</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Serial Number</label>
            <input v-model="form.manufacturer_sn" type="text" class="form-input w-full font-mono" placeholder="SN-XXXX-0001" />
          </div>
          <div>
            <label class="form-label">UDI Code</label>
            <input v-model="form.udi_code" type="text" class="form-input w-full font-mono" />
          </div>
          <div>
            <label class="form-label">GMDN Code</label>
            <input v-model="form.gmdn_code" type="text" class="form-input w-full" />
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
            <label class="form-label">Số đăng ký BYT</label>
            <input v-model="form.byt_reg_no" type="text" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Hạn đăng ký BYT</label>
            <input v-model="form.byt_reg_expiry" type="date" class="form-input w-full" />
          </div>
        </div>
      </div>

      <!-- Section: Bảo trì / Hiệu chuẩn -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Lịch bảo trì & Hiệu chuẩn</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex items-center gap-3">
            <input v-model="form.is_pm_required" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 text-blue-600 rounded" id="pm_check" />
            <label for="pm_check" class="text-sm text-slate-700">Yêu cầu bảo trì định kỳ</label>
          </div>
          <div v-if="form.is_pm_required">
            <label class="form-label">Chu kỳ bảo trì (ngày)</label>
            <input v-model.number="form.pm_interval_days" type="number" min="1" class="form-input w-full" />
          </div>
          <div class="flex items-center gap-3">
            <input v-model="form.is_calibration_required" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 text-blue-600 rounded" id="cal_check" />
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
