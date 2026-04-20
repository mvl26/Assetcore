<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  listPmTemplates, getPmTemplate, createPmTemplate, updatePmTemplate, deletePmTemplate,
  type PmTemplate,
} from '@/api/imm00'

const items = ref<PmTemplate[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
type ChecklistItem = { description: string; expected_value?: string; tolerance?: string }
const form = ref<Partial<PmTemplate> & { checklist_items?: ChecklistItem[] } & Record<string, unknown>>({})
const err = ref('')

async function load() {
  loading.value = true
  try {
    const r = await listPmTemplates()
    const d = r as unknown as { items: PmTemplate[]; pagination: { total: number } }
    if (d) { items.value = d.items || []; total.value = d.pagination?.total || 0 }
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = {
    template_name: '', asset_category: '', pm_type: 'Quarterly',
    version: '1.0', effective_date: new Date().toISOString().slice(0, 10),
    checklist_items: [{ description: '', expected_value: '', tolerance: '' }],
  }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getPmTemplate(name)
  if (r) form.value = { ...(r as unknown as PmTemplate) }
  if (!form.value.checklist_items || (form.value.checklist_items as ChecklistItem[]).length === 0) {
    form.value.checklist_items = [{ description: '', expected_value: '', tolerance: '' }]
  }
  err.value = ''; showForm.value = true
}

function addItem() {
  (form.value.checklist_items as ChecklistItem[]).push({ description: '', expected_value: '', tolerance: '' })
}
function removeItem(i: number) {
  (form.value.checklist_items as ChecklistItem[]).splice(i, 1)
}

async function save() {
  err.value = ''
  try {
    const payload = { ...form.value, checklist_items: JSON.stringify(form.value.checklist_items) } as unknown as Partial<PmTemplate>
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
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Template Checklist PM</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ total }} template</span>
        <button @click="openCreate" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Thêm Template</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
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
      <div class="bg-white rounded-xl p-6 w-[720px] max-w-full space-y-4 my-auto">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} Template Checklist PM</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Tên template *</label>
            <input v-model="form.template_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Loại thiết bị (AC Asset Category)</label>
            <input v-model="form.asset_category" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Loại PM</label>
            <select v-model="form.pm_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option>Quarterly</option><option>Semi-Annual</option><option>Annual</option><option>Ad-hoc</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Version</label>
            <input v-model="form.version" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Ngày hiệu lực</label>
            <input v-model="form.effective_date" type="date" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>

        <div class="border-t pt-4">
          <div class="flex items-center justify-between mb-2">
            <label class="text-sm font-semibold text-gray-700">Hạng mục kiểm tra</label>
            <button @click="addItem" type="button" class="text-blue-600 text-xs font-medium">+ Thêm hạng mục</button>
          </div>
          <div class="space-y-2">
            <div v-for="(it, i) in (form.checklist_items as ChecklistItem[])" :key="i" class="grid grid-cols-10 gap-2 items-center">
              <input v-model="it.description" placeholder="Mô tả *" class="col-span-5 border border-gray-300 rounded px-2 py-1.5 text-sm" />
              <input v-model="it.expected_value" placeholder="Giá trị kỳ vọng" class="col-span-2 border border-gray-300 rounded px-2 py-1.5 text-sm" />
              <input v-model="it.tolerance" placeholder="Sai số" class="col-span-2 border border-gray-300 rounded px-2 py-1.5 text-sm" />
              <button @click="removeItem(i)" type="button" class="text-red-600 text-xs">✕</button>
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
