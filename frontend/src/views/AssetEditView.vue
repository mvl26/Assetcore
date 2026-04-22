<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAsset, updateAsset } from '@/api/imm00'
import SmartSelect from '@/components/common/SmartSelect.vue'
import type { AcAsset } from '@/types/imm00'

const props = defineProps<{ id: string }>()
const router = useRouter()

const saving = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const form = ref<Partial<AcAsset>>({})

async function load() {
  loading.value = true
  try {
    const res = await getAsset(props.id) as unknown as AcAsset
    if (res) form.value = { ...res }
  } finally { loading.value = false }
}

async function submit() {
  if (!form.value.asset_name?.trim()) { error.value = 'Tên thiết bị là bắt buộc'; return }
  saving.value = true; error.value = null
  try {
    await updateAsset(props.id, form.value)
    router.push(`/assets/${props.id}`)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally { saving.value = false }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in max-w-3xl">
    <div class="flex items-center gap-3 mb-6">
      <button class="btn-ghost" @click="router.push(`/assets/${id}`)">← Quay lại</button>
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest">IMM-00</p>
        <h1 class="text-xl font-bold text-slate-900">Chỉnh sửa thiết bị</h1>
      </div>
    </div>

    <div v-if="loading" class="card p-8 text-center text-slate-400">Đang tải...</div>
    <div v-else-if="error" class="alert-error mb-4">{{ error }}</div>

    <form v-if="!loading" @submit.prevent="submit" class="space-y-5">
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Thông tin cơ bản</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="md:col-span-2">
            <label class="form-label">Tên thiết bị <span class="text-red-500">*</span></label>
            <input v-model="form.asset_name" type="text" class="form-input w-full" required />
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
            <label class="form-label">Kỹ thuật viên phụ trách</label>
            <input v-model="form.responsible_technician" type="text" class="form-input w-full" />
          </div>
        </div>
      </div>

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

      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Nhận dạng &amp; Pháp lý Thiết bị Y tế</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Số seri nhà sản xuất</label>
            <input v-model="form.manufacturer_sn" type="text" class="form-input w-full font-mono" />
          </div>
          <div>
            <label class="form-label">Mã định danh thiết bị (UDI)</label>
            <input v-model="form.udi_code" type="text" class="form-input w-full font-mono" />
          </div>
          <div>
            <label class="form-label">Mã danh mục thiết bị y tế (GMDN)</label>
            <input v-model="form.gmdn_code" type="text" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Phân loại y tế</label>
            <select v-model="form.medical_device_class" class="form-select w-full">
              <option value="">— Chọn loại —</option>
              <option>Class I</option><option>Class II</option>
              <option>Class IIa</option><option>Class IIb</option><option>Class III</option>
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

      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Lịch bảo trì & Hiệu chuẩn</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex items-center gap-3">
            <input v-model="form.is_pm_required" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 text-blue-600 rounded" id="pm_check" />
            <label for="pm_check" class="text-sm text-slate-700">Yêu cầu bảo trì định kỳ (PM)</label>
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

      <div class="flex gap-3 justify-end">
        <button type="button" class="btn-ghost" @click="router.push(`/assets/${id}`)">Huỷ</button>
        <button type="submit" class="btn-primary" :disabled="saving">
          {{ saving ? 'Đang lưu...' : 'Cập nhật' }}
        </button>
      </div>
    </form>
  </div>
</template>
