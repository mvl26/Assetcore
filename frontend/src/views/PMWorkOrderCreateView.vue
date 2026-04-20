<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-08 Ad-hoc PM Work Order Create
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createAdhocPMWorkOrder } from '@/api/imm08'
import { frappeGet } from '@/api/helpers'
import SmartSelect from '@/components/common/SmartSelect.vue'

const router = useRouter()

const form = ref({
  asset_ref: '',
  pm_schedule: '',
  due_date: '',
  assigned_to: '',
  technician_notes: '',
})

const schedules = ref<Array<{ value: string; label: string }>>([])
const loadingSchedules = ref(false)
const saving = ref(false)
const error = ref('')

async function loadSchedules() {
  if (!form.value.asset_ref) { schedules.value = []; return }
  loadingSchedules.value = true
  try {
    const res = await frappeGet<{ data: Array<{ name: string; pm_type: string; pm_interval_days: number }> }>(
      '/api/method/assetcore.api.imm08.list_pm_schedules',
      { filters: JSON.stringify({ asset_ref: form.value.asset_ref, status: 'Active' }), page_size: 50 },
    )
    schedules.value = (res?.data ?? []).map(s => ({
      value: s.name,
      label: `${s.pm_type} — mỗi ${s.pm_interval_days ?? '?'} ngày (${s.name})`,
    }))
  } catch {
    schedules.value = []
  } finally { loadingSchedules.value = false }
}

async function submit() {
  if (!form.value.asset_ref || !form.value.pm_schedule || !form.value.due_date) {
    error.value = 'Vui lòng điền đầy đủ thông tin bắt buộc (*).'
    return
  }
  saving.value = true; error.value = ''
  try {
    const res = await createAdhocPMWorkOrder(form.value)
    if (res?.name) {
      router.push(`/pm/work-orders/${res.name}`)
    }
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi tạo phiếu bảo trì'
  } finally { saving.value = false }
}

onMounted(() => {
  const today = new Date()
  form.value.due_date = today.toISOString().split('T')[0]
})
</script>

<template>
  <div class="max-w-2xl mx-auto p-6 space-y-6">
    <div class="flex items-center gap-3">
      <button class="text-slate-500 hover:text-slate-700 text-sm" @click="router.push('/pm/work-orders')">← Danh sách phiếu bảo trì</button>
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest">IMM-08</p>
        <h1 class="text-xl font-semibold text-gray-800">Tạo phiếu bảo trì đột xuất</h1>
      </div>
    </div>

    <div class="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
      Phiếu bảo trì thường được tạo tự động theo lịch. Form này dành cho trường hợp tạo thủ công (ngoài lịch định kỳ).
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">{{ error }}</div>

      <!-- Asset -->
      <div>
        <p id="asset-label" class="block text-sm font-medium text-gray-700 mb-1">
          Thiết bị <span class="text-red-500">*</span>
        </p>
        <SmartSelect
          v-model="form.asset_ref"
          doctype="AC Asset"
          placeholder="Chọn thiết bị..."
          @select="loadSchedules"
        />
      </div>

      <!-- PM Schedule -->
      <div>
        <label for="pm-schedule" class="block text-sm font-medium text-gray-700 mb-1">
          PM Schedule <span class="text-red-500">*</span>
        </label>
        <select
          id="pm-schedule"
          v-model="form.pm_schedule"
          :disabled="!form.asset_ref || loadingSchedules"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50 disabled:text-gray-400"
        >
          <option value="">{{ loadingSchedules ? 'Đang tải...' : '-- Chọn lịch PM --' }}</option>
          <option v-for="s in schedules" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <p v-if="form.asset_ref && !loadingSchedules && !schedules.length" class="text-xs text-orange-600 mt-1">
          Thiết bị này chưa có PM Schedule Active. Tạo lịch trước tại mục PM Schedule.
        </p>
      </div>

      <!-- Due Date -->
      <div>
        <label for="due-date" class="block text-sm font-medium text-gray-700 mb-1">
          Ngày thực hiện <span class="text-red-500">*</span>
        </label>
        <input
          id="due-date"
          v-model="form.due_date"
          type="date"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <!-- Assigned To -->
      <div>
        <label for="assigned-to" class="block text-sm font-medium text-gray-700 mb-1">
          Giao cho KTV (email)
        </label>
        <input
          id="assigned-to"
          v-model="form.assigned_to"
          type="email"
          placeholder="ktv@hospital.vn"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <!-- Notes -->
      <div>
        <label for="tech-notes" class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
        <textarea
          id="tech-notes"
          v-model="form.technician_notes"
          rows="2"
          placeholder="Lý do tạo WO ngoài lịch..."
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <button
        :disabled="saving || !form.asset_ref || !form.pm_schedule || !form.due_date"
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-medium"
        @click="submit"
      >
        {{ saving ? 'Đang tạo...' : 'Tạo phiếu bảo trì' }}
      </button>
    </div>
  </div>
</template>
