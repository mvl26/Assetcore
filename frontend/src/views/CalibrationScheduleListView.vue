<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  listCalibrationSchedules, createCalibrationSchedule,
  updateCalibrationSchedule, deleteCalibrationSchedule,
} from '@/api/imm11'
import type { CalibrationSchedule } from '@/api/imm11'
import SmartSelect from '@/components/common/SmartSelect.vue'
import { formatAssetDisplay, formatDate } from '@/utils/formatters'

const router = useRouter()
const items = ref<CalibrationSchedule[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const err = ref('')

const form = ref<Partial<CalibrationSchedule>>({
  calibration_type: 'External',
  interval_days: 365,
  is_active: 1,
})

async function load() {
  loading.value = true
  try {
    const res = await listCalibrationSchedules({}, 1, 50)
    items.value = res.data || []
    total.value = res.pagination?.total || 0
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = { calibration_type: 'External', interval_days: 365, is_active: 1 }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const sched = items.value.find(i => i.name === name)
  if (sched) form.value = { ...sched }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  try {
    if (editingName.value) {
      await updateCalibrationSchedule(editingName.value, form.value)
    } else {
      await createCalibrationSchedule(form.value)
    }
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa lịch "${name}"?`)) return
  try { await deleteCalibrationSchedule(name); await load() }
  catch (e: unknown) { alert((e as Error).message || 'Không thể xóa') }
}

function isOverdue(date: string | null) {
  return date && new Date(date) < new Date()
}

onMounted(load)
</script>

<template>
  <div class="page-container space-y-5">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button class="btn-ghost text-sm" @click="router.push('/calibration')">← Phiếu hiệu chuẩn</button>
        <h1 class="text-xl font-semibold text-slate-800">Lịch Hiệu chuẩn</h1>
        <span class="text-sm text-slate-400">{{ total }} lịch</span>
      </div>
      <button class="btn-primary text-sm" @click="openCreate">+ Thêm lịch</button>
    </div>

    <div class="card overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-slate-400">Đang tải...</div>
      <div v-else-if="!items.length" class="p-8 text-center text-slate-400 text-sm">Chưa có lịch hiệu chuẩn.</div>
      <div v-else class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="bg-slate-50 border-b">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Chu kỳ</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Ngày đến hạn</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Trạng thái</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="s in items" :key="s.name" class="hover:bg-slate-50">
            <td class="px-4 py-3 font-mono text-xs text-slate-400">{{ s.name }}</td>
            <td class="px-4 py-3">
              <div class="font-medium text-slate-900 truncate max-w-[240px]">
                {{ formatAssetDisplay(s.asset_name, s.asset).main }}
              </div>
              <div v-if="formatAssetDisplay(s.asset_name, s.asset).hasBoth"
                   class="text-xs text-slate-400 font-mono">
                {{ formatAssetDisplay(s.asset_name, s.asset).sub }}
              </div>
            </td>
            <td class="px-4 py-3">{{ s.calibration_type }}</td>
            <td class="px-4 py-3">{{ s.interval_days }} ngày</td>
            <td class="px-4 py-3 text-xs" :class="isOverdue(s.next_due_date) ? 'text-red-600 font-semibold' : ''">
              {{ formatDate(s.next_due_date) }}
            </td>
            <td class="px-4 py-3">
              <span class="text-xs font-medium" :class="s.is_active ? 'text-green-600' : 'text-slate-400'">
                {{ s.is_active ? 'Hoạt động' : 'Tạm dừng' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right space-x-2">
              <button class="text-blue-600 text-xs" @click="openEdit(s.name)">Sửa</button>
              <button class="text-red-600 text-xs" @click="remove(s.name)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <!-- Form Modal -->
    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[520px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} Lịch Hiệu chuẩn</h2>
        <div v-if="err" class="alert-error text-sm">{{ err }}</div>
        <div class="space-y-3">
          <div v-if="!editingName">
            <label class="form-label">Thiết bị *</label>
            <SmartSelect v-model="form.asset" doctype="AC Asset" placeholder="Tìm thiết bị..." />
          </div>
          <div>
            <label class="form-label">Loại hiệu chuẩn</label>
            <select v-model="form.calibration_type" class="form-select w-full text-sm">
              <option value="External">External</option>
              <option value="In-House">In-House</option>
            </select>
          </div>
          <div>
            <label class="form-label">Chu kỳ (ngày)</label>
            <input v-model.number="form.interval_days" type="number" min="1" class="form-input w-full text-sm" />
          </div>
          <div>
            <label class="form-label">Ngày đến hạn tiếp theo</label>
            <input v-model="form.next_due_date" type="date" class="form-input w-full text-sm" />
          </div>
          <div>
            <label class="form-label">Lab ưu tiên</label>
            <SmartSelect v-model="(form.preferred_lab as string | undefined)" doctype="AC Supplier" placeholder="Tìm lab..." />
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="form.is_active" :true-value="1" :false-value="0" />
            Đang hoạt động
          </label>
        </div>
        <div class="flex justify-end gap-2 pt-2">
          <button class="btn-ghost text-sm" @click="showForm = false">Huỷ</button>
          <button class="btn-primary text-sm" @click="save">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
