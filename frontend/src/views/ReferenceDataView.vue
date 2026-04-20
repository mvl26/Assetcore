<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  listLocations, createLocation, updateLocation, deleteLocation,
  listDepartments, createDepartment, updateDepartment, deleteDepartment,
  listAssetCategories, createAssetCategory, updateAssetCategory, deleteAssetCategory,
} from '@/api/imm00'
import type { AcLocation, AcDepartment, AcAssetCategory } from '@/types/imm00'

type Tab = 'location' | 'department' | 'category'
const tab = ref<Tab>('location')

const locations = ref<AcLocation[]>([])
const departments = ref<AcDepartment[]>([])
const categories = ref<AcAssetCategory[]>([])
const loading = ref(false)

const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Record<string, unknown>>({})
const err = ref('')

async function load() {
  loading.value = true
  try {
    if (tab.value === 'location') {
      const r = await listLocations(); if (r) locations.value = (r as unknown as AcLocation[]) || []
    } else if (tab.value === 'department') {
      const r = await listDepartments(); if (r) departments.value = (r as unknown as AcDepartment[]) || []
    } else {
      const r = await listAssetCategories(); if (r) categories.value = (r as unknown as AcAssetCategory[]) || []
    }
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = tab.value === 'location' ? { location_name: '', location_type: 'Building', is_active: 1 }
    : tab.value === 'department' ? { department_name: '' }
    : { category_name: '', default_pm_interval_days: 180, default_calibration_interval_days: 365 }
  err.value = ''; showForm.value = true
}

function openEdit(row: Record<string, unknown>) {
  editingName.value = row.name as string
  form.value = { ...row }
  err.value = ''; showForm.value = true
}

async function save() {
  err.value = ''
  try {
    if (tab.value === 'location') {
      editingName.value
        ? await updateLocation(editingName.value, form.value as Partial<AcLocation>)
        : await createLocation(form.value as Partial<AcLocation>)
    } else if (tab.value === 'department') {
      editingName.value
        ? await updateDepartment(editingName.value, form.value as Partial<AcDepartment>)
        : await createDepartment(form.value as Partial<AcDepartment>)
    } else {
      editingName.value
        ? await updateAssetCategory(editingName.value, form.value as Partial<AcAssetCategory>)
        : await createAssetCategory(form.value as Partial<AcAssetCategory>)
    }
    showForm.value = false
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa "${name}"?`)) return
  try {
    if (tab.value === 'location') await deleteLocation(name)
    else if (tab.value === 'department') await deleteDepartment(name)
    else await deleteAssetCategory(name)
    await load()
  } catch (e: unknown) { alert((e as Error).message || 'Lỗi xóa — có thể đang được tham chiếu') }
}

const currentRows = computed(() =>
  tab.value === 'location' ? locations.value
  : tab.value === 'department' ? departments.value
  : categories.value,
)

const tabLabel = computed(() =>
  tab.value === 'location' ? 'Vị trí' : tab.value === 'department' ? 'Khoa/Phòng' : 'Loại thiết bị',
)

function switchTab(t: Tab) { tab.value = t; load() }
onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Dữ liệu tham chiếu — IMM-00</h1>
      <button @click="openCreate" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
        + Thêm {{ tabLabel }}
      </button>
    </div>

    <div class="border-b border-gray-200 flex gap-1">
      <button v-for="t in (['location','department','category'] as Tab[])" :key="t"
        @click="switchTab(t)"
        :class="['px-4 py-2 text-sm font-medium border-b-2 -mb-px',
          tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700']">
        {{ t === 'location' ? 'Vị trí' : t === 'department' ? 'Khoa/Phòng' : 'Loại thiết bị' }}
      </button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="currentRows.length === 0" class="text-center text-gray-400 py-12 text-sm">Không có dữ liệu.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr v-if="tab === 'location'">
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên vị trí</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Cấp trên</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Kích hoạt</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
          <tr v-else-if="tab === 'department'">
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên khoa</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Parent</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Trưởng khoa</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
          <tr v-else>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Bảo trì (ngày)</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Hiệu chuẩn (ngày)</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="r in (currentRows as Record<string, unknown>[])" :key="r.name as string" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ r.name }}</td>
            <template v-if="tab === 'location'">
              <td class="px-4 py-3 font-medium text-gray-800">{{ r.location_name }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.location_type || '—' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.parent_ac_location || '—' }}</td>
              <td class="px-4 py-3">
                <span :class="r.is_active ? 'text-green-600' : 'text-gray-400'">{{ r.is_active ? '✓' : '—' }}</span>
              </td>
            </template>
            <template v-else-if="tab === 'department'">
              <td class="px-4 py-3 font-medium text-gray-800">{{ r.department_name }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.parent_ac_department || '—' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.head_of_department || '—' }}</td>
            </template>
            <template v-else>
              <td class="px-4 py-3 font-medium text-gray-800">{{ r.category_name }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.default_pm_interval_days || '—' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.default_calibration_interval_days || '—' }}</td>
            </template>
            <td class="px-4 py-3 text-right space-x-2">
              <button @click="openEdit(r)" class="text-blue-600 hover:text-blue-800 text-xs font-medium">Sửa</button>
              <button @click="remove(r.name as string)" class="text-red-600 hover:text-red-800 text-xs font-medium">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Form -->
    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[500px] max-w-full space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} {{ tabLabel }}</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>

        <div v-if="tab === 'location'" class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tên vị trí *</label>
            <input v-model="form.location_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Loại</label>
            <select v-model="form.location_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option value="Building">Tòa nhà</option>
              <option value="Floor">Tầng</option>
              <option value="Room">Phòng</option>
              <option value="Zone">Khu vực</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Vị trí cha (tùy chọn)</label>
            <input v-model="form.parent_ac_location" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Mã AC Location" />
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="form.is_active" :true-value="1" :false-value="0" /> Đang hoạt động
          </label>
        </div>

        <div v-else-if="tab === 'department'" class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tên khoa/phòng *</label>
            <input v-model="form.department_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Khoa cha (tùy chọn)</label>
            <input v-model="form.parent_ac_department" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Mã AC Department" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Trưởng khoa</label>
            <input v-model="form.head_of_department" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="User email" />
          </div>
        </div>

        <div v-else class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tên loại thiết bị *</label>
            <input v-model="form.category_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Chu kỳ bảo trì (ngày)</label>
              <input type="number" v-model.number="form.default_pm_interval_days" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Chu kỳ hiệu chuẩn (ngày)</label>
              <input type="number" v-model.number="form.default_calibration_interval_days" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button @click="showForm = false" class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Hủy</button>
          <button @click="save" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
