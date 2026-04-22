<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  listPmSchedules, getPmSchedule, createPmSchedule, updatePmSchedule, deletePmSchedule,
  type PmSchedule,
} from '@/api/imm00'
import { formatAssetDisplay, translateStatus, getStatusColor, formatDate } from '@/utils/formatters'

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
    const res = await listPmSchedules({ page: page.value, page_size: PAGE_SIZE })
    const d = res as unknown as { items: PmSchedule[]; total: number }
    if (d) { items.value = d.items || []; total.value = d.total || 0 }
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = {
    asset_ref: '', pm_type: 'Quarterly', status: 'Active',
    pm_interval_days: 90, alert_days_before: 7, notes: '',
  }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getPmSchedule(name)
  if (r) form.value = { ...(r as unknown as PmSchedule) }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
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
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Lịch bảo trì định kỳ</h1>
      <div class="flex gap-3 items-center">
        <span class="text-sm text-gray-500">{{ total }} lịch</span>
        <button @click="openCreate" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Thêm lịch PM</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="items.length === 0" class="text-center text-gray-400 py-12 text-sm">Chưa có lịch PM.</div>
      <div v-else class="overflow-x-auto"><table class="w-full text-sm">
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
                {{ formatAssetDisplay(s.asset_name, s.asset_ref).main }}
              </div>
              <div v-if="formatAssetDisplay(s.asset_name, s.asset_ref).hasBoth"
                   class="text-xs text-gray-500 font-mono">
                {{ formatAssetDisplay(s.asset_name, s.asset_ref).sub }}
              </div>
            </td>
            <td class="px-4 py-3">{{ s.pm_type }}</td>
            <td class="px-4 py-3">{{ s.pm_interval_days }}</td>
            <td class="px-4 py-3 text-xs text-gray-600">{{ s.responsible_technician || '—' }}</td>
            <td class="px-4 py-3 text-xs text-gray-600">{{ formatDate(s.last_pm_date) }}</td>
            <td class="px-4 py-3 text-xs" :class="overdueColor(s.next_due_date)">{{ formatDate(s.next_due_date) }}</td>
            <td class="px-4 py-3">
              <span :class="['inline-block px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(s.status)]">
                {{ translateStatus(s.status) }}
              </span>
            </td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button @click="openEdit(s.name)" class="text-blue-600 text-xs font-medium">Sửa</button>
              <button @click="remove(s.name)" class="text-red-600 text-xs font-medium">Xóa</button>
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
            <input v-model="form.asset_ref" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Loại PM</label>
            <select v-model="form.pm_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option>Quarterly</option><option>Semi-Annual</option><option>Annual</option><option>Ad-hoc</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Chu kỳ (ngày)</label>
            <input type="number" v-model.number="form.pm_interval_days" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Template Checklist</label>
            <input v-model="form.checklist_template" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="PMCT-..." />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">KTV phụ trách</label>
            <input v-model="form.responsible_technician" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="User email" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Cảnh báo trước (ngày)</label>
            <input type="number" v-model.number="form.alert_days_before" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
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
          <button @click="showForm = false" class="px-4 py-2 text-sm border border-gray-300 rounded-lg">Hủy</button>
          <button @click="save" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
