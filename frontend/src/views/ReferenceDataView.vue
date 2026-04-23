<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  listLocations, getLocation, createLocation, updateLocation, deleteLocation,
  listDepartments, getDepartment, createDepartment, updateDepartment, deleteDepartment,
  listAssetCategories, getAssetCategory, createAssetCategory, updateAssetCategory, deleteAssetCategory,
} from '@/api/imm00'
import type { AcLocation, AcDepartment, AcAssetCategory } from '@/types/imm00'
import SmartSelect from '@/components/common/SmartSelect.vue'

type Tab = 'location' | 'department' | 'category'
type FormData = Record<string, string | number | null | undefined>

const tab = ref<Tab>('location')
const locations = ref<AcLocation[]>([])
const departments = ref<AcDepartment[]>([])
const categories = ref<AcAssetCategory[]>([])
const loading = ref(false)
const loadError = ref('')
let loadSeq = 0

const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<FormData>({})
const err = ref('')

async function load() {
  const seq = ++loadSeq
  loading.value = true
  loadError.value = ''
  try {
    if (tab.value === 'location') {
      const r = await listLocations() as unknown as AcLocation[]
      if (seq === loadSeq) locations.value = r || []
    } else if (tab.value === 'department') {
      const r = await listDepartments() as unknown as AcDepartment[]
      if (seq === loadSeq) departments.value = r || []
    } else {
      const r = await listAssetCategories() as unknown as AcAssetCategory[]
      if (seq === loadSeq) categories.value = r || []
    }
  } catch (e: unknown) {
    if (seq === loadSeq) loadError.value = (e as Error).message || 'Lỗi tải dữ liệu'
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function openCreate() {
  editingName.value = null
  form.value = tab.value === 'location'
    ? { location_name: '', location_code: '', parent_location: '', is_group: 0,
        clinical_area_type: '', infection_control_level: '',
        power_backup_available: 0, emergency_contact: '',
        dept_head: '', technical_contact: '', notes: '' }
    : tab.value === 'department'
    ? { department_name: '', department_code: '', parent_department: '', is_group: 0,
        dept_head: '', phone: '', email: '', is_active: 1 }
    : { category_name: '', description: '',
        default_pm_required: 1, default_pm_interval_days: 180,
        default_calibration_required: 0, default_calibration_interval_days: 365,
        has_radiation: 0, is_active: 1 }
  err.value = ''; showForm.value = true
}

function normChecks(doc: Record<string, unknown>, fields: string[]): FormData {
  const d = { ...doc } as FormData
  for (const f of fields) d[f] = d[f] ? 1 : 0
  return d
}

async function openEdit(row: Record<string, unknown>) {
  const name = row.name as string
  editingName.value = name
  err.value = ''
  try {
    let doc: Record<string, unknown>
    if (tab.value === 'location') {
      doc = await getLocation(name) as unknown as Record<string, unknown>
      form.value = normChecks(doc, ['is_group', 'power_backup_available'])
    } else if (tab.value === 'department') {
      doc = await getDepartment(name) as unknown as Record<string, unknown>
      form.value = normChecks(doc, ['is_group', 'is_active'])
    } else {
      doc = await getAssetCategory(name) as unknown as Record<string, unknown>
      form.value = normChecks(doc, ['default_pm_required', 'default_calibration_required', 'has_radiation', 'is_active'])
    }
  } catch {
    form.value = { ...row } as FormData
  }
  showForm.value = true
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

function switchTab(t: Tab) { tab.value = t; showForm.value = false; load() }
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
      <div v-else-if="loadError" class="text-center text-red-500 py-12 text-sm">{{ loadError }}</div>
      <div v-else-if="currentRows.length === 0" class="text-center text-gray-400 py-12 text-sm">Không có dữ liệu.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr v-if="tab === 'location'">
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên vị trí</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Khu vực lâm sàng</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Vị trí cha</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Is Group</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
          <tr v-else-if="tab === 'department'">
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên khoa</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Khoa cha</th>
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
              <td class="px-4 py-3 text-gray-500">{{ r.clinical_area_type || '—' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.parent_location || '—' }}</td>
              <td class="px-4 py-3">
                <span :class="r.is_group ? 'text-green-600' : 'text-gray-400'">{{ r.is_group ? '✓' : '—' }}</span>
              </td>
            </template>
            <template v-else-if="tab === 'department'">
              <td class="px-4 py-3 font-medium text-gray-800">{{ r.department_name }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.parent_department || '—' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.dept_head || '—' }}</td>
            </template>
            <template v-else>
              <td class="px-4 py-3 font-medium text-gray-800">{{ r.category_name }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.default_pm_required ? (r.default_pm_interval_days || '—') : '—' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.default_calibration_required ? (r.default_calibration_interval_days || '—') : '—' }}</td>
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
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Tên vị trí <span class="text-red-500">*</span></label>
              <input v-model="form.location_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Mã vị trí</label>
              <input v-model="form.location_code" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Vị trí cha</label>
              <SmartSelect v-model="form.parent_location as string" doctype="AC Location" placeholder="Chọn vị trí cha..." />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Khu vực lâm sàng</label>
              <select v-model="form.clinical_area_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="">— Chọn —</option>
                <option value="ICU">ICU</option>
                <option value="OR">Phòng mổ (OR)</option>
                <option value="Lab">Xét nghiệm (Lab)</option>
                <option value="Imaging">Chẩn đoán hình ảnh</option>
                <option value="General Ward">Khoa thường</option>
                <option value="Storage">Kho</option>
                <option value="Office">Văn phòng</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Mức kiểm soát nhiễm khuẩn</label>
              <select v-model="form.infection_control_level" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="">— Chọn —</option>
                <option value="Standard">Chuẩn</option>
                <option value="Enhanced">Tăng cường</option>
                <option value="Isolation">Cách ly</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Liên hệ khẩn cấp</label>
              <input v-model="form.emergency_contact" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Phụ trách kỹ thuật</label>
              <SmartSelect v-model="form.dept_head as string" doctype="User" placeholder="Chọn người dùng..." />
            </div>
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Liên hệ kỹ thuật</label>
              <SmartSelect v-model="form.technical_contact as string" doctype="User" placeholder="Chọn người dùng..." />
            </div>
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
              <textarea v-model="form.notes" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
            </div>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.power_backup_available" type="checkbox" :true-value="1" :false-value="0" /> Có nguồn điện dự phòng
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_group" type="checkbox" :true-value="1" :false-value="0" /> Là nhóm (tree group)
          </label>
        </div>

        <div v-else-if="tab === 'department'" class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Tên khoa/phòng <span class="text-red-500">*</span></label>
              <input v-model="form.department_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Mã khoa</label>
              <input v-model="form.department_code" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Khoa cha</label>
              <SmartSelect v-model="form.parent_department as string" doctype="AC Department" placeholder="Chọn khoa cha..." />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Trưởng khoa</label>
              <SmartSelect v-model="form.dept_head as string" doctype="User" placeholder="Chọn người dùng..." />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Điện thoại</label>
              <input v-model="form.phone" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input v-model="form.email" type="email" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_group" type="checkbox" :true-value="1" :false-value="0" /> Là nhóm (tree group)
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0" /> Đang hoạt động
          </label>
        </div>

        <div v-else class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tên loại thiết bị <span class="text-red-500">*</span></label>
            <input v-model="form.category_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Mô tả</label>
            <textarea v-model="form.description" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.default_pm_required" type="checkbox" :true-value="1" :false-value="0" /> Mặc định yêu cầu PM
          </label>
          <div class="pl-6">
            <label class="block text-sm font-medium text-gray-700 mb-1">Chu kỳ PM mặc định (ngày)</label>
            <input v-model.number="form.default_pm_interval_days" type="number"
              :disabled="form.default_pm_required !== 1"
              class="w-48 border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed" />
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.default_calibration_required" type="checkbox" :true-value="1" :false-value="0" /> Mặc định yêu cầu hiệu chuẩn
          </label>
          <div class="pl-6">
            <label class="block text-sm font-medium text-gray-700 mb-1">Chu kỳ hiệu chuẩn mặc định (ngày)</label>
            <input v-model.number="form.default_calibration_interval_days" type="number"
              :disabled="form.default_calibration_required !== 1"
              class="w-48 border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed" />
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.has_radiation" type="checkbox" :true-value="1" :false-value="0" /> Chứa nguồn bức xạ
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0" /> Đang hoạt động
          </label>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button @click="showForm = false" class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Hủy</button>
          <button @click="save" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
