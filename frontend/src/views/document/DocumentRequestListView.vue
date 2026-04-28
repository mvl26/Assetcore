<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  listDocumentRequests, getDocumentRequest, createDocumentRequest,
  updateDocumentRequest, deleteDocumentRequest, type DocumentRequest,
} from '@/api/imm00'
import SmartSelect from '@/components/common/SmartSelect.vue'

const route = useRoute()
const router = useRouter()

const items = ref<DocumentRequest[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<DocumentRequest> & Record<string, unknown>>({})
const err = ref('')

// Filter state
const filterAsset = ref<string>((route.query.asset as string) || '')
const filterStatus = ref('')

async function load() {
  loading.value = true
  try {
    const r = await listDocumentRequests({
      asset: filterAsset.value || undefined,
      status: filterStatus.value || undefined,
    })
    const d = r as unknown as { items: DocumentRequest[]; pagination: { total: number } }
    if (d) { items.value = d.items || []; total.value = d.pagination?.total || 0 }
  } finally { loading.value = false }
}

function clearAssetFilter() {
  filterAsset.value = ''
  router.replace({ query: {} })
  load()
}

// Re-load when query param changes (e.g. navigating from AssetDetail)
watch(() => route.query.asset, (val) => {
  filterAsset.value = (val as string) || ''
  load()
})

function openCreate() {
  editingName.value = null
  form.value = {
    asset_ref: filterAsset.value || '',
    doc_type_required: '', doc_category: 'Legal',
    status: 'Open', priority: 'Medium',
    due_date: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
  }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getDocumentRequest(name)
  if (r) form.value = { ...(r as unknown as DocumentRequest) }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  try {
    if (editingName.value) await updateDocumentRequest(editingName.value, form.value)
    else await createDocumentRequest(form.value)
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa yêu cầu "${name}"?`)) return
  try { await deleteDocumentRequest(name); await load() }
  catch (e: unknown) { alert((e as Error).message || 'Không thể xóa') }
}

function statusColor(s?: string) {
  return s === 'Fulfilled' ? 'bg-green-100 text-green-700'
    : s === 'Overdue' ? 'bg-red-100 text-red-700'
    : s === 'In_Progress' ? 'bg-blue-100 text-blue-700'
    : s === 'Cancelled' ? 'bg-gray-100 text-gray-500'
    : 'bg-yellow-100 text-yellow-700'
}
function prioColor(p?: string) {
  return p === 'Critical' ? 'text-red-600 font-semibold'
    : p === 'High' ? 'text-orange-600' : 'text-gray-600'
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Yêu cầu Hồ sơ</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ total }} yêu cầu</span>
        <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium" @click="openCreate">+ Thêm Yêu cầu</button>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="flex items-center gap-3">
      <div class="w-64">
        <SmartSelect
          v-model="filterAsset"
          doctype="AC Asset"
          placeholder="Lọc theo thiết bị..."
          @update:model-value="load"
        />
      </div>
      <select v-model="filterStatus" class="border border-gray-300 rounded-lg px-3 py-2 text-sm" @change="load">
        <option value="">Tất cả trạng thái</option>
        <option value="Open">Đang mở</option>
        <option value="In_Progress">Đang xử lý</option>
        <option value="Overdue">Quá hạn</option>
        <option value="Fulfilled">Đã hoàn thành</option>
        <option value="Cancelled">Đã hủy</option>
      </select>
      <button v-if="filterAsset || filterStatus" class="text-xs text-gray-400 hover:text-red-500 underline" @click="filterAsset = ''; filterStatus = ''; clearAssetFilter()">
        Xóa lọc
      </button>
    </div>

    <!-- Active asset filter banner -->
    <div v-if="filterAsset" class="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 text-sm text-blue-700">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      Đang lọc yêu cầu của thiết bị: <strong class="font-mono">{{ filterAsset }}</strong>
      <button class="ml-auto text-blue-400 hover:text-blue-700" @click="clearAssetFilter">✕</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-x-auto">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="items.length === 0" class="text-center text-gray-400 py-12 text-sm">Chưa có yêu cầu.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại tài liệu</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Nhóm</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Ưu tiên</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Giao cho</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Hạn</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Trạng thái</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="d in items" :key="d.name" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-xs">{{ d.name }}</td>
            <td class="px-4 py-3">
              <div class="font-medium text-slate-800">{{ d.asset_name || d.asset_ref }}</div>
              <div v-if="d.asset_name" class="text-xs text-slate-400 font-mono mt-0.5">{{ d.asset_ref }}</div>
            </td>
            <td class="px-4 py-3 font-medium">{{ d.doc_type_required }}</td>
            <td class="px-4 py-3 text-xs">{{ d.doc_category }}</td>
            <td class="px-4 py-3 text-xs" :class="prioColor(d.priority)">{{ d.priority }}</td>
            <td class="px-4 py-3 text-xs">{{ d.assigned_to || '—' }}</td>
            <td class="px-4 py-3 text-xs">{{ d.due_date || '—' }}</td>
            <td class="px-4 py-3">
              <span :class="['text-xs px-2 py-0.5 rounded font-medium', statusColor(d.status)]">{{ d.status }}</span>
            </td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button class="text-blue-600 text-xs font-medium" @click="openEdit(d.name)">Sửa</button>
              <button class="text-red-600 text-xs font-medium" @click="remove(d.name)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[560px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} Yêu cầu Hồ sơ</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị (AC Asset) <span class="text-red-500">*</span></label>
            <SmartSelect v-model="form.asset_ref as string" doctype="AC Asset" placeholder="Chọn thiết bị..." />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Loại tài liệu yêu cầu <span class="text-red-500">*</span></label>
            <input v-model="form.doc_type_required" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Nhóm</label>
            <select v-model="form.doc_category" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option>Legal</option><option>Technical</option><option>Certification</option>
              <option>Training</option><option>QA</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Ưu tiên</label>
            <select v-model="form.priority" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Low">Thấp</option>
              <option value="Medium">Trung bình</option>
              <option value="High">Cao</option>
              <option value="Critical">Khẩn cấp</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Giao cho</label>
            <SmartSelect v-model="form.assigned_to as string" doctype="User" placeholder="Chọn người dùng..." />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hạn xử lý <span class="text-red-500">*</span></label>
            <DateInput v-model="form.due_date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Trạng thái</label>
            <select v-model="form.status" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Open">Đang mở</option>
              <option value="In_Progress">Đang xử lý</option>
              <option value="Overdue">Quá hạn</option>
              <option value="Fulfilled">Đã hoàn thành</option>
              <option value="Cancelled">Đã hủy</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
            <textarea v-model="form.request_note" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
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
