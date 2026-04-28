<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import {
  listPmSchedules, getPmSchedule, createPmSchedule, updatePmSchedule, deletePmSchedule,
  type PmSchedule,
} from '@/api/imm00'
import { translateStatus, getStatusColor, formatDate } from '@/utils/formatters'
import SmartSelect from '@/components/common/SmartSelect.vue'
import DateInput from '@/components/common/DateInput.vue'
import { useMasterDataStore } from '@/stores/useMasterDataStore'

const masterStore = useMasterDataStore()

// Default chu kỳ (ngày) theo loại PM — gợi ý cho form, user có thể override.
const PM_TYPE_INTERVAL: Record<string, number> = {
  Quarterly: 90,
  'Semi-Annual': 180,
  Annual: 365,
  'Ad-hoc': 0,
}

const items = ref<PmSchedule[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 30
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<PmSchedule> & Record<string, unknown>>({})
const err = ref('')

async function load() {
  loading.value = true
  try {
    // Prefetch master data song song để table hiển thị tên tài sản/KTV ngay từ lần đầu.
    const [res] = await Promise.all([
      listPmSchedules({ page: page.value, page_size: PAGE_SIZE }),
      masterStore.fetchDoctype('AC Asset'),
      masterStore.fetchDoctype('User'),
      masterStore.fetchDoctype('PM Checklist Template'),
    ])
    const d = res as unknown as { items: PmSchedule[]; total: number }
    if (d) { items.value = d.items || []; total.value = d.total || 0 }
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = {
    asset_ref: '', pm_type: 'Quarterly', status: 'Active',
    pm_interval_days: 90, alert_days_before: 7, notes: '',
    checklist_template: '', responsible_technician: '', last_pm_date: '',
  }
  err.value = ''; showForm.value = true
}

// Khi đổi loại PM → gợi ý chu kỳ tương ứng (giữ nguyên nếu user đã đổi thủ công).
watch(() => form.value.pm_type, (newType, oldType) => {
  if (!newType || !oldType) return
  const oldDefault = PM_TYPE_INTERVAL[oldType as string]
  if (form.value.pm_interval_days === oldDefault) {
    const next = PM_TYPE_INTERVAL[newType as string]
    if (next) form.value.pm_interval_days = next
  }
})

function technicianLabel(id?: string): string {
  if (!id) return '—'
  return masterStore.getItemById('User', id)?.name || id
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getPmSchedule(name)
  if (r) form.value = { ...(r as unknown as PmSchedule) }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  if (!form.value.asset_ref) { err.value = 'Vui lòng chọn thiết bị.'; return }
  if (!form.value.checklist_template) { err.value = 'Vui lòng chọn template checklist.'; return }
  if (!form.value.pm_interval_days || (form.value.pm_interval_days as number) < 0) {
    err.value = 'Chu kỳ (ngày) phải lớn hơn hoặc bằng 0.'; return
  }
  try {
    if (editingName.value) await updatePmSchedule(editingName.value, form.value)
    else await createPmSchedule(form.value)
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa lịch PM "${name}"?`)) return
  try { await deletePmSchedule(name); await load() }
  catch (e: unknown) { alert((e as Error).message || 'Không thể xóa') }
}

function overdueColor(d?: string) {
  if (!d) return 'text-gray-400'
  const days = Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
  return days < 0 ? 'text-red-600 font-semibold' : days < 14 ? 'text-yellow-600' : 'text-gray-600'
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Lịch bảo trì định kỳ</h1>
      <div class="flex gap-3 items-center">
        <span class="text-sm text-gray-500">{{ total }} lịch</span>
        <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium" @click="openCreate">+ Thêm lịch PM</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="items.length === 0" class="text-center text-gray-400 py-12 text-sm">Chưa có lịch PM.</div>
      <div v-else class="overflow-x-auto">
<table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại PM</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Chu kỳ (ngày)</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">KTV</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Lần trước</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Kế tiếp</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Trạng thái</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="s in items" :key="s.name" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ s.name }}</td>
            <td class="px-4 py-3">
              <div class="font-medium text-gray-900 truncate max-w-[240px]">
                {{ s.asset_name || s.asset_code || s.asset_ref }}
              </div>
              <div v-if="s.asset_name && (s.asset_code || s.asset_ref)"
                   class="text-xs text-gray-500 font-mono">
                {{ s.asset_code || s.asset_ref }}
              </div>
            </td>
            <td class="px-4 py-3">{{ s.pm_type }}</td>
            <td class="px-4 py-3">{{ s.pm_interval_days }}</td>
            <td class="px-4 py-3 text-xs text-gray-600">{{ technicianLabel(s.responsible_technician) }}</td>
            <td class="px-4 py-3 text-xs text-gray-600">{{ formatDate(s.last_pm_date) }}</td>
            <td class="px-4 py-3 text-xs" :class="overdueColor(s.next_due_date)">{{ formatDate(s.next_due_date) }}</td>
            <td class="px-4 py-3">
              <span :class="['inline-block px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(s.status)]">
                {{ translateStatus(s.status) }}
              </span>
            </td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button class="text-blue-600 text-xs font-medium" @click="openEdit(s.name)">Sửa</button>
              <button class="text-red-600 text-xs font-medium" @click="remove(s.name)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[560px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} lịch bảo trì</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị (AC Asset) *</label>
            <SmartSelect
              v-model="(form.asset_ref as string)"
              doctype="AC Asset"
              placeholder="Tìm theo tên / mã / serial..."
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Loại PM *</label>
            <select v-model="form.pm_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Quarterly">Quarterly — 3 tháng</option>
              <option value="Semi-Annual">Semi-Annual — 6 tháng</option>
              <option value="Annual">Annual — 12 tháng</option>
              <option value="Ad-hoc">Ad-hoc</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Chu kỳ (ngày) *</label>
            <input v-model.number="form.pm_interval_days" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Template checklist *</label>
            <SmartSelect
              v-model="(form.checklist_template as string)"
              doctype="PM Checklist Template"
              placeholder="Chọn template (PMCT-...)"
            />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">KTV phụ trách</label>
            <SmartSelect
              v-model="(form.responsible_technician as string)"
              doctype="User"
              placeholder="Tìm theo tên / email..."
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Ngày PM gần nhất</label>
            <DateInput v-model="(form.last_pm_date as string)" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Cảnh báo trước (ngày)</label>
            <input v-model.number="form.alert_days_before" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Trạng thái</label>
            <select v-model="form.status" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Active">Đang hoạt động</option>
              <option value="Paused">Tạm dừng</option>
              <option value="Suspended">Đình chỉ</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
            <textarea v-model="form.notes" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
          </div>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg" @click="showForm = false">Hủy</button>
          <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg" @click="save">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
