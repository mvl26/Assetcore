<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDeviceModel, createDeviceModel, updateDeviceModel, deleteDeviceModel } from '@/api/imm00'
import type { ImmDeviceModel } from '@/types/imm00'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const name = computed(() => route.params.id as string | undefined)

const form = ref<Partial<ImmDeviceModel> & Record<string, unknown>>({
  model_name: '',
  model_number: '',
  manufacturer: '',
  medical_device_class: 'Class II',
  gmdn_code: '',
  is_radiation_device: 0,
  is_pm_required: 1,
  pm_interval_days: 180,
  is_calibration_required: 0,
  calibration_interval_days: 365,
})
const loading = ref(false)
const saving = ref(false)
const err = ref('')

async function load() {
  if (!isEdit.value || !name.value) return
  loading.value = true
  try {
    const res = await getDeviceModel(name.value)
    if (res) form.value = { ...(res as unknown as ImmDeviceModel) }
  } finally { loading.value = false }
}

async function save() {
  saving.value = true; err.value = ''
  try {
    if (isEdit.value && name.value) await updateDeviceModel(name.value, form.value)
    else await createDeviceModel(form.value)
    router.push('/device-models')
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
  finally { saving.value = false }
}

async function remove() {
  if (!name.value || !confirm(`Xóa Model "${name.value}"?`)) return
  try {
    await deleteDeviceModel(name.value)
    router.push('/device-models')
  } catch (e: unknown) { err.value = (e as Error).message || 'Không thể xóa' }
}

onMounted(load)
</script>

<template>
  <div class="p-6 max-w-3xl mx-auto space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">
        {{ isEdit ? `Sửa Model — ${name}` : 'Thêm Device Model' }}
      </h1>
      <button v-if="isEdit" @click="remove" class="text-red-600 hover:text-red-800 text-sm font-medium">Xóa</button>
    </div>

    <div v-if="err" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ err }}</div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
    <div v-else class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Tên Model *</label>
          <input v-model="form.model_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Model Number</label>
          <input v-model="form.model_number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Hãng sản xuất</label>
          <input v-model="form.manufacturer" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Phân loại TB Y tế</label>
          <select v-model="form.medical_device_class" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="Class I">Class I</option>
            <option value="Class II">Class II</option>
            <option value="Class IIa">Class IIa</option>
            <option value="Class IIb">Class IIb</option>
            <option value="Class III">Class III</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">GMDN Code</label>
          <input v-model="form.gmdn_code" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>

      <div class="border-t pt-4 space-y-3">
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" v-model="form.is_radiation_device" :true-value="1" :false-value="0" /> Thiết bị bức xạ
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" v-model="form.is_pm_required" :true-value="1" :false-value="0" /> Yêu cầu PM định kỳ
        </label>
        <div v-if="form.is_pm_required" class="pl-6">
          <label class="block text-sm font-medium text-gray-700 mb-1">PM Interval (ngày)</label>
          <input type="number" v-model.number="form.pm_interval_days" class="w-48 border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" v-model="form.is_calibration_required" :true-value="1" :false-value="0" /> Yêu cầu hiệu chuẩn
        </label>
        <div v-if="form.is_calibration_required" class="pl-6">
          <label class="block text-sm font-medium text-gray-700 mb-1">Calibration Interval (ngày)</label>
          <input type="number" v-model.number="form.calibration_interval_days" class="w-48 border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>

      <div class="flex justify-end gap-2 pt-4 border-t border-gray-100">
        <button @click="router.push('/device-models')" class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Hủy</button>
        <button @click="save" :disabled="saving" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {{ saving ? 'Đang lưu...' : (isEdit ? 'Cập nhật' : 'Tạo mới') }}
        </button>
      </div>
    </div>
  </div>
</template>
