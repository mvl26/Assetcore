<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { createCalibration } from '@/api/imm11'
import SmartSelect from '@/components/common/SmartSelect.vue'
import { useFormDraft } from '@/composables/useFormDraft'

const router = useRouter()
const saving = ref(false)
const err = ref('')

const form = ref({
  asset: '',
  calibration_type: 'External' as 'External' | 'In-House',
  scheduled_date: '',
  technician: '',
  lab_supplier: '',
  calibration_schedule: '',
  is_recalibration: 0,
})

const { clear: clearDraft } = useFormDraft('calibration-create', form)

async function submit() {
  if (!form.value.asset || !form.value.scheduled_date || !form.value.technician) {
    err.value = 'Vui lòng nhập đầy đủ thông tin bắt buộc'
    return
  }
  saving.value = true; err.value = ''
  try {
    const res = await createCalibration({
      ...form.value,
      lab_supplier: form.value.lab_supplier || undefined,
      calibration_schedule: form.value.calibration_schedule || undefined,
    })
    const r = res as unknown as { name: string }
    if (r?.name) {
      clearDraft()
      router.push(`/calibration/${r.name}`)
    }
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi tạo phiếu' }
  finally { saving.value = false }
}
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center gap-3">
      <button class="btn-ghost" @click="router.push('/calibration')">← Quay lại</button>
      <div>
        <h1 class="text-xl font-bold text-slate-900">Tạo Phiếu Hiệu chuẩn</h1>
      </div>
    </div>

    <div v-if="err" class="alert-error">{{ err }}</div>

    <form class="card p-5 space-y-4" @submit.prevent="submit">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="form-label">Thiết bị <span class="text-red-500">*</span></label>
          <SmartSelect v-model="form.asset" doctype="AC Asset" placeholder="Tìm thiết bị..." />
        </div>
        <div>
          <label class="form-label">Loại hiệu chuẩn <span class="text-red-500">*</span></label>
          <select v-model="form.calibration_type" class="form-select w-full">
            <option value="External">External (Bên ngoài)</option>
            <option value="In-House">In-House (Nội bộ)</option>
          </select>
        </div>
        <div>
          <label class="form-label">Ngày dự kiến <span class="text-red-500">*</span></label>
          <DateInput v-model="form.scheduled_date" class="form-input w-full" required />
        </div>
        <div>
          <label class="form-label">Kỹ thuật viên <span class="text-red-500">*</span></label>
          <SmartSelect v-model="form.technician" doctype="User" placeholder="Tìm người dùng..." />
        </div>
        <div v-if="form.calibration_type === 'External'">
          <label class="form-label">Lab hiệu chuẩn</label>
          <SmartSelect v-model="form.lab_supplier" doctype="AC Supplier" placeholder="Tìm lab..." />
        </div>
        <div>
          <label class="form-label">Lịch hiệu chuẩn (nếu có)</label>
          <SmartSelect v-model="form.calibration_schedule" doctype="IMM Calibration Schedule" placeholder="Tìm lịch..." />
        </div>
        <div class="flex items-center gap-2">
          <input id="recal" v-model="form.is_recalibration" type="checkbox" :true-value="1" :false-value="0" class="h-4 w-4 text-blue-600 rounded" />
          <label for="recal" class="text-sm text-slate-700">Là tái hiệu chuẩn sau CAPA</label>
        </div>
      </div>

      <div class="flex gap-2 justify-end pt-2">
        <button type="button" class="btn-ghost" @click="router.push('/calibration')">Huỷ</button>
        <button type="submit" class="btn-primary" :disabled="saving">
          {{ saving ? 'Đang tạo...' : 'Tạo phiếu' }}
        </button>
      </div>
    </form>
  </div>
</template>
