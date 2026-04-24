<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  listFirmwareCrs, getFirmwareCr, createFirmwareCr, updateFirmwareCr, deleteFirmwareCr,
  type FirmwareCR,
} from '@/api/imm00'

const router = useRouter()

const items = ref<FirmwareCR[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<FirmwareCR> & Record<string, unknown>>({})
const err = ref('')

async function load() {
  loading.value = true
  try {
    const r = await listFirmwareCrs()
    const d = r as unknown as { items: FirmwareCR[]; total: number }
    if (d) { items.value = d.items || []; total.value = d.total || 0 }
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = {
    asset_ref: '', version_before: '', version_after: '', status: 'Draft',
    change_notes: '', source_reference: '',
  }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getFirmwareCr(name)
  if (r) form.value = { ...(r as unknown as FirmwareCR) }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  try {
    if (editingName.value) await updateFirmwareCr(editingName.value, form.value)
    else await createFirmwareCr(form.value)
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa FCR "${name}"?`)) return
  try { await deleteFirmwareCr(name); await load() }
  catch (e: unknown) { alert((e as Error).message || 'Không thể xóa') }
}

function statusColor(s?: string) {
  return s === 'Approved' ? 'bg-green-100 text-green-700'
    : s === 'Applied' ? 'bg-blue-100 text-blue-700'
    : s === 'Rejected' || s === 'Rolled Back' ? 'bg-red-100 text-red-700'
    : 'bg-gray-100 text-gray-700'
}

const STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp',
  'Pending Approval': 'Chờ phê duyệt',
  Approved: 'Đã phê duyệt',
  Applied: 'Đã áp dụng',
  Rejected: 'Từ chối',
  'Rolled Back': 'Đã khôi phục',
}
function statusLabel(s?: string): string {
  return (s && STATUS_LABELS[s]) || s || ''
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Yêu cầu Cập nhật Firmware</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ total }} yêu cầu</span>
        <button @click="openCreate" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Thêm yêu cầu</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-x-auto">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="items.length === 0" class="text-center text-gray-400 py-12 text-sm">Chưa có yêu cầu nào.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phiên bản cũ</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phiên bản mới</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Trạng thái</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phê duyệt</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Áp dụng</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="f in items" :key="f.name" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-xs">{{ f.name }}</td>
            <td class="px-4 py-3">
              <div class="font-medium text-slate-800">{{ f.asset_name || f.asset_ref }}</div>
              <div v-if="f.asset_name" class="text-xs text-slate-400 font-mono mt-0.5">{{ f.asset_ref }}</div>
            </td>
            <td class="px-4 py-3 font-mono text-xs">{{ f.version_before || '—' }}</td>
            <td class="px-4 py-3 font-mono text-xs">{{ f.version_after || '—' }}</td>
            <td class="px-4 py-3">
              <span :class="['text-xs px-2 py-0.5 rounded font-medium', statusColor(f.status)]">{{ statusLabel(f.status) }}</span>
            </td>
            <td class="px-4 py-3 text-xs text-gray-500">{{ f.approved_by || '—' }}</td>
            <td class="px-4 py-3 text-xs text-gray-500">{{ f.applied_datetime ? new Date(f.applied_datetime).toLocaleDateString('vi-VN') : '—' }}</td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button @click="router.push(`/cm/firmware/${f.name}`)" class="text-blue-600 text-xs font-medium">Chi tiết</button>
              <button @click="openEdit(f.name)" class="text-gray-500 text-xs font-medium">Sửa</button>
              <button @click="remove(f.name)" class="text-red-600 text-xs font-medium">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[600px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} yêu cầu cập nhật Firmware</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị (AC Asset) *</label>
            <input v-model="form.asset_ref" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Phiên bản hiện tại</label>
            <input v-model="form.version_before" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Phiên bản mới *</label>
            <input v-model="form.version_after" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nguồn (thông báo nhà sản xuất, mã lỗ hổng CVE, v.v.)</label>
            <input v-model="form.source_reference" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nội dung thay đổi *</label>
            <textarea v-model="form.change_notes" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Trạng thái</label>
            <select v-model="form.status" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Draft">Nháp</option>
              <option value="Pending Approval">Chờ phê duyệt</option>
              <option value="Approved">Đã phê duyệt</option>
              <option value="Applied">Đã áp dụng</option>
              <option value="Rejected">Từ chối</option>
              <option value="Rolled Back">Đã khôi phục</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Liên kết phiếu sửa chữa</label>
            <input v-model="form.asset_repair_wo" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="SỬA-..." />
          </div>
          <div v-if="form.status === 'Rolled Back'" class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Lý do khôi phục</label>
            <textarea v-model="form.rollback_reason" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
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
