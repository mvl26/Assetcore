<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  listPmTemplates, getPmTemplate, createPmTemplate, updatePmTemplate, deletePmTemplate,
  type PmTemplate, type PmChecklistItem,
} from '@/api/imm00'

const items = ref<PmTemplate[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<PmTemplate> & { checklist_items: PmChecklistItem[] }>({
  checklist_items: [],
})
const err = ref('')

function newItem(): PmChecklistItem {
  return {
    description: '',
    measurement_type: 'Pass/Fail',
    unit: '',
    expected_min: null,
    expected_max: null,
    is_critical: 0,
    reference_section: '',
  }
}

async function load() {
  loading.value = true
  try {
    const r = await listPmTemplates()
    const d = r as unknown as { data: PmTemplate[]; pagination: { total: number } }
    if (d) { items.value = d.data || []; total.value = d.pagination?.total || 0 }
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = {
    template_name: '', asset_category: '', pm_type: 'Quarterly',
    version: '1.0', effective_date: new Date().toISOString().slice(0, 10),
    checklist_items: [newItem()],
  }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getPmTemplate(name)
  const d = r as unknown as PmTemplate
  if (d) form.value = { ...d, checklist_items: (d.checklist_items as PmChecklistItem[]) || [] }
  if (!form.value.checklist_items.length) form.value.checklist_items = [newItem()]
  err.value = ''; showForm.value = true
}

function addItem() { form.value.checklist_items.push(newItem()) }
function removeItem(i: number) { form.value.checklist_items.splice(i, 1) }

async function save() {
  err.value = ''
  if (!form.value.template_name || !form.value.asset_category || !form.value.pm_type) {
    err.value = 'Tên mẫu, Loại thiết bị, Loại bảo trì là bắt buộc'
    return
  }
  const cleanItems = form.value.checklist_items
    .filter(it => (it.description || '').trim())
    .map(it => ({
      description: it.description.trim(),
      measurement_type: it.measurement_type || 'Pass/Fail',
      unit: it.unit || '',
      expected_min: it.expected_min ?? null,
      expected_max: it.expected_max ?? null,
      is_critical: it.is_critical ? 1 : 0,
      reference_section: it.reference_section || '',
    }))
  if (cleanItems.length === 0) { err.value = 'Phải có ít nhất 1 hạng mục checklist'; return }

  try {
    const payload = {
      template_name: form.value.template_name,
      asset_category: form.value.asset_category,
      pm_type: form.value.pm_type,
      version: form.value.version,
      effective_date: form.value.effective_date,
      checklist_items: JSON.stringify(cleanItems),
    } as unknown as Partial<PmTemplate>
    if (editingName.value) await updatePmTemplate(editingName.value, payload)
    else await createPmTemplate(payload)
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa template "${name}"?`)) return
  try { await deletePmTemplate(name); await load() }
  catch (e: unknown) { alert((e as Error).message || 'Không thể xóa') }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Template Checklist PM</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ total }} template</span>
        <button @click="openCreate" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Thêm Template</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-x-auto">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="items.length === 0" class="text-center text-gray-400 py-12 text-sm">Chưa có template.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên template</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại PM</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Version</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Hiệu lực</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="t in items" :key="t.name" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ t.name }}</td>
            <td class="px-4 py-3 font-medium">{{ t.template_name }}</td>
            <td class="px-4 py-3">{{ t.asset_category || '—' }}</td>
            <td class="px-4 py-3">{{ t.pm_type || '—' }}</td>
            <td class="px-4 py-3">{{ t.version || '—' }}</td>
            <td class="px-4 py-3 text-xs">{{ t.effective_date || '—' }}</td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button @click="openEdit(t.name)" class="text-blue-600 text-xs font-medium">Sửa</button>
              <button @click="remove(t.name)" class="text-red-600 text-xs font-medium">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 overflow-y-auto py-6" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[860px] max-w-full space-y-4 my-auto">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} Template Checklist PM</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-2 gap-3">
          <label class="col-span-2 block">
            <span class="block text-sm font-medium text-gray-700 mb-1">Tên template *</span>
            <input v-model="form.template_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </label>
          <label class="block">
            <span class="block text-sm font-medium text-gray-700 mb-1">Loại thiết bị *</span>
            <input v-model="form.asset_category" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </label>
          <label class="block">
            <span class="block text-sm font-medium text-gray-700 mb-1">Loại bảo trì *</span>
            <select v-model="form.pm_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Quarterly">Hàng quý</option>
              <option value="Semi-Annual">Nửa năm</option>
              <option value="Annual">Hàng năm</option>
              <option value="Ad-hoc">Đột xuất</option>
            </select>
          </label>
          <label class="block">
            <span class="block text-sm font-medium text-gray-700 mb-1">Phiên bản</span>
            <input v-model="form.version" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </label>
          <label class="block">
            <span class="block text-sm font-medium text-gray-700 mb-1">Ngày hiệu lực</span>
            <input v-model="form.effective_date" type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </label>
        </div>

        <div class="border-t pt-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-gray-700">Hạng mục kiểm tra *</span>
            <button @click="addItem" type="button" class="text-blue-600 text-xs font-medium">+ Thêm hạng mục</button>
          </div>
          <div class="space-y-2">
            <div v-for="(it, i) in form.checklist_items" :key="i" class="grid grid-cols-12 gap-2 items-center">
              <input v-model="it.description" placeholder="Mô tả *" class="col-span-4 border border-gray-300 rounded px-2 py-1.5 text-sm" />
              <select v-model="it.measurement_type" class="col-span-2 border border-gray-300 rounded px-2 py-1.5 text-sm">
                <option>Pass/Fail</option><option>Numeric</option><option>Text</option>
              </select>
              <input v-model="it.unit" placeholder="Đơn vị" class="col-span-1 border border-gray-300 rounded px-2 py-1.5 text-sm" />
              <input v-model.number="it.expected_min" type="number" placeholder="Min" class="col-span-1 border border-gray-300 rounded px-2 py-1.5 text-sm" />
              <input v-model.number="it.expected_max" type="number" placeholder="Max" class="col-span-1 border border-gray-300 rounded px-2 py-1.5 text-sm" />
              <label class="col-span-2 flex items-center gap-1 text-xs text-gray-600">
                <input v-model="it.is_critical" type="checkbox" /> Trọng yếu
              </label>
              <button @click="removeItem(i)" type="button" class="col-span-1 text-red-600 text-xs">✕</button>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button @click="showForm = false" class="px-4 py-2 text-sm border border-gray-300 rounded-lg">Hủy</button>
          <button @click="save" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
