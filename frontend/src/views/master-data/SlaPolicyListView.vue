<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
import { ref, onMounted } from 'vue'
import {
  listSlaPolicies, getSlaPolicy, createSlaPolicy, updateSlaPolicy, deleteSlaPolicy,
} from '@/api/imm00'
import type { ImmSlaPolicy } from '@/types/imm00'

const policies = ref<ImmSlaPolicy[]>([])
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<ImmSlaPolicy> & Record<string, unknown>>({})
const err = ref('')

async function load() {
  loading.value = true
  try {
    const res = await listSlaPolicies()
    if (res) policies.value = (res as unknown as ImmSlaPolicy[]) || []
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = {
    policy_name: '', priority: 'P3', risk_class: 'Medium',
    response_time_minutes: 240, resolution_time_hours: 24,
    working_hours_only: 1, is_active: 1, is_default: 0,
    escalation_l1_role: '', escalation_l1_hours: 4,
    escalation_l2_role: '', escalation_l2_hours: 8,
    effective_date: '', expiry_date: '',
  }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const res = await getSlaPolicy(name)
  if (res) form.value = { ...(res as unknown as ImmSlaPolicy) }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  try {
    if (editingName.value) await updateSlaPolicy(editingName.value, form.value)
    else await createSlaPolicy(form.value)
    showForm.value = false
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa SLA Policy "${name}"?`)) return
  try { await deleteSlaPolicy(name); await load() }
  catch (e: unknown) { alert((e as Error).message || 'Không thể xóa') }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Chính sách SLA</h1>
      <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium" @click="openCreate">+ Thêm Policy</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-x-auto">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="policies.length === 0" class="text-center text-gray-400 py-12 text-sm">Chưa có SLA Policy.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên Policy</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mức ưu tiên</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Risk Class</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Response (phút)</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Resolution (giờ)</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mặc định</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Kích hoạt</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="p in policies" :key="p.name" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-800">{{ p.policy_name }}</td>
            <td class="px-4 py-3">{{ p.priority }}</td>
            <td class="px-4 py-3">{{ p.risk_class }}</td>
            <td class="px-4 py-3">{{ p.response_time_minutes }}</td>
            <td class="px-4 py-3">{{ p.resolution_time_hours }}</td>
            <td class="px-4 py-3">{{ p.is_default ? '✓' : '—' }}</td>
            <td class="px-4 py-3">
              <span :class="p.is_active ? 'text-green-600' : 'text-gray-400'">{{ p.is_active ? '✓' : '—' }}</span>
            </td>
            <td class="px-4 py-3 text-right space-x-2">
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="openEdit(p.name)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="remove(p.name)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal -->
    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[560px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} SLA Policy</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>

        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Tên chính sách *</label>
            <input v-model="form.policy_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Mức ưu tiên <span class="text-red-500">*</span></label>
            <select v-model="form.priority" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="P1 Critical">P1 Critical — Nguy hiểm tính mạng</option>
              <option value="P1 High">P1 High — Khẩn cấp</option>
              <option value="P2">P2 — Cao</option>
              <option value="P3">P3 — Trung bình</option>
              <option value="P4">P4 — Thấp</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Phân loại rủi ro</label>
            <select v-model="form.risk_class" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="">— Tất cả —</option>
              <option value="Low">Thấp</option>
              <option value="Medium">Trung bình</option>
              <option value="High">Cao</option>
              <option value="Critical">Khẩn cấp</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Response time (phút)</label>
            <input v-model.number="form.response_time_minutes" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Resolution time (giờ)</label>
            <input v-model.number="form.resolution_time_hours" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hiệu lực từ</label>
            <DateInput v-model="form.effective_date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hết hiệu lực</label>
            <DateInput v-model="form.expiry_date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>

        <div class="border-t pt-3 space-y-3">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Escalation</p>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">L1 Role</label>
              <input v-model="form.escalation_l1_role" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="VD: IMM Workshop Lead" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">L1 sau (giờ)</label>
              <input v-model.number="form.escalation_l1_hours" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">L2 Role</label>
              <input v-model="form.escalation_l2_role" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="VD: IMM Department Head" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">L2 sau (giờ)</label>
              <input v-model.number="form.escalation_l2_hours" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
        </div>

        <div class="space-y-2">
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.working_hours_only" type="checkbox" :true-value="1" :false-value="0" /> Chỉ giờ hành chính
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_default" type="checkbox" :true-value="1" :false-value="0" /> Policy mặc định
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0" /> Đang hoạt động
          </label>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50" @click="showForm = false">Hủy</button>
          <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700" @click="save">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
