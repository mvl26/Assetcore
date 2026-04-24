<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getDeviceModel, createDeviceModel, updateDeviceModel, deleteDeviceModel,
  listAssetCategories,
} from '@/api/imm00'
import type { ImmDeviceModel, AcAssetCategory } from '@/types/imm00'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const name = computed(() => route.params.id as string | undefined)

const form = ref<Partial<ImmDeviceModel> & Record<string, unknown>>({
  model_name: '',
  model_version: '',
  manufacturer: '',
  asset_category: '',
  country_of_origin: '',
  power_supply: '',
  expected_lifespan_years: 10,
  medical_device_class: 'Class II',
  risk_classification: 'Medium',
  gmdn_code: '',
  emdn_code: '',
  hsn_code: '',
  registration_required: 1,
  is_radiation_device: 0,
  is_pm_required: 1,
  pm_interval_days: 180,
  pm_alert_days: 14,
  is_calibration_required: 0,
  calibration_interval_days: 365,
  calibration_alert_days: 30,
  default_calibration_type: '',
  model_image: '',
  catalog_file: '',
  specifications: '',
  dimensions: '',
  weight_kg: 0,
  notes: '',
})
const categories = ref<AcAssetCategory[]>([])
const selectedCategory = computed<AcAssetCategory | null>(() =>
  categories.value.find(c => c.name === form.value.asset_category) ?? null,
)
const loading = ref(false)
const saving = ref(false)
const err = ref('')

async function load() {
  loading.value = true
  try {
    const cats = await listAssetCategories() as unknown as AcAssetCategory[]
    categories.value = cats || []
    if (isEdit.value && name.value) {
      const res = await getDeviceModel(name.value)
      if (res) form.value = { ...(res as unknown as ImmDeviceModel) }
    }
  } finally { loading.value = false }
}

async function save() {
  saving.value = true; err.value = ''
  try {
    if (isEdit.value && name.value) await updateDeviceModel(name.value, form.value)
    else await createDeviceModel(form.value)
    router.push('/device-models')
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
  finally { saving.value = false }
}

async function remove() {
  if (!name.value || !confirm(`Xóa Model thiết bị "${name.value}"?`)) return
  try {
    await deleteDeviceModel(name.value)
    router.push('/device-models')
  } catch (e: unknown) { err.value = (e as Error).message || 'Không thể xóa' }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">
        {{ isEdit ? `Sửa Model thiết bị — ${name}` : 'Thêm Model thiết bị' }}
      </h1>
      <button v-if="isEdit" class="text-red-600 hover:text-red-800 text-sm font-medium" @click="remove">Xóa</button>
    </div>

    <div v-if="err" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ err }}</div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
    <div v-else class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Tên Model <span class="text-red-500">*</span></label>
          <input v-model="form.model_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Phiên bản Model</label>
          <input v-model="form.model_version" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Hãng sản xuất <span class="text-red-500">*</span></label>
          <input v-model="form.manufacturer" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Danh mục tài sản <span class="text-red-500">*</span></label>
          <select v-model="form.asset_category" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">— Chọn danh mục —</option>
            <option v-for="c in categories" :key="c.name" :value="c.name">{{ c.category_name }}</option>
          </select>
          <div v-if="selectedCategory" class="mt-2 p-2 rounded-lg bg-blue-50 border border-blue-200 text-xs text-blue-800">
            <p class="font-semibold mb-0.5">Luật khấu hao kế thừa từ danh mục:</p>
            <div class="flex flex-wrap gap-x-3 gap-y-0.5">
              <span v-if="selectedCategory.default_depreciation_method">
                Phương pháp: <b>{{ selectedCategory.default_depreciation_method }}</b>
              </span>
              <span v-if="selectedCategory.total_depreciation_months">
                Thời gian: <b>{{ selectedCategory.total_depreciation_months }} tháng</b>
              </span>
              <span v-if="selectedCategory.depreciation_frequency">
                Tần suất: <b>{{ selectedCategory.depreciation_frequency }}</b>
              </span>
              <span v-if="selectedCategory.default_residual_value_pct">
                Thu hồi: <b>{{ selectedCategory.default_residual_value_pct }}%</b>
              </span>
              <span v-if="selectedCategory.default_pm_required">
                Bảo trì mỗi <b>{{ selectedCategory.default_pm_interval_days }}</b> ngày
              </span>
              <span v-if="selectedCategory.default_calibration_required">
                Hiệu chuẩn mỗi <b>{{ selectedCategory.default_calibration_interval_days }}</b> ngày
              </span>
            </div>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Quốc gia sản xuất</label>
          <input v-model="form.country_of_origin" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nguồn điện</label>
          <input v-model="form.power_supply" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="VD: 220V/50Hz" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Tuổi thọ dự kiến (năm)</label>
          <input v-model.number="form.expected_lifespan_years" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Phân loại thiết bị y tế <span class="text-red-500">*</span></label>
          <select v-model="form.medical_device_class" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="Class I">Loại I — Rủi ro thấp</option>
            <option value="Class II">Loại II — Rủi ro trung bình</option>
            <option value="Class III">Loại III — Rủi ro cao</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Phân loại rủi ro</label>
          <select v-model="form.risk_classification" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="Low">Thấp</option>
            <option value="Medium">Trung bình</option>
            <option value="High">Cao</option>
            <option value="Critical">Nghiêm trọng</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">GMDN Code</label>
          <input v-model="form.gmdn_code" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">EMDN Code</label>
          <input v-model="form.emdn_code" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">HSN Code</label>
          <input v-model="form.hsn_code" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>

      <div class="border-t pt-4 space-y-3">
        <label class="flex items-center gap-2 text-sm">
          <input v-model="form.registration_required" type="checkbox" :true-value="1" :false-value="0" /> Yêu cầu đăng ký Bộ Y tế
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="form.is_radiation_device" type="checkbox" :true-value="1" :false-value="0" /> Thiết bị bức xạ
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="form.is_pm_required" type="checkbox" :true-value="1" :false-value="0" /> Yêu cầu bảo trì định kỳ
        </label>
        <div v-if="form.is_pm_required" class="grid grid-cols-1 sm:grid-cols-2 gap-4 pl-6">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">PM Interval (ngày)</label>
            <input v-model.number="form.pm_interval_days" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">PM Alert trước (ngày)</label>
            <input v-model.number="form.pm_alert_days" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="form.is_calibration_required" type="checkbox" :true-value="1" :false-value="0" /> Yêu cầu hiệu chuẩn
        </label>
        <div v-if="form.is_calibration_required" class="grid grid-cols-1 sm:grid-cols-2 gap-4 pl-6">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Chu kỳ hiệu chuẩn (ngày)</label>
            <input v-model.number="form.calibration_interval_days" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Alert hiệu chuẩn trước (ngày)</label>
            <input v-model.number="form.calibration_alert_days" type="number" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
      </div>

      <!-- Media + Specs (Tier 2) -->
      <div class="pt-4 border-t border-gray-100 space-y-4">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Hình ảnh & Tài liệu</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hình ảnh đại diện (URL)</label>
            <input v-model="form.model_image" type="text"
                   placeholder="/files/xxx.jpg hoặc URL"
                   class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" />
            <img v-if="form.model_image" :src="form.model_image"
                 class="mt-2 h-24 w-24 object-cover rounded-lg border border-gray-200" alt="Model preview" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Catalogue / Brochure (URL PDF)</label>
            <input v-model="form.catalog_file" type="text"
                   placeholder="/files/catalog.pdf"
                   class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono" />
            <a v-if="form.catalog_file" :href="form.catalog_file" target="_blank"
               class="mt-2 inline-flex items-center text-xs text-blue-600 hover:underline">
              📄 Xem catalog
            </a>
          </div>
        </div>
      </div>

      <div class="pt-4 border-t border-gray-100 space-y-3">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Thông số kỹ thuật chi tiết</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Kích thước (DxRxC mm)</label>
            <input v-model="form.dimensions" type="text" placeholder="1200x800x600"
                   class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Khối lượng (kg)</label>
            <input v-model.number="form.weight_kg" type="number" min="0" step="0.1"
                   class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Thông số kỹ thuật đầy đủ</label>
          <textarea v-model="form.specifications" rows="4"
                    placeholder="Công suất, điện áp, tần số, yêu cầu môi trường, accessory…"
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
        <textarea v-model="form.notes" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
      </div>

      <div class="flex justify-end gap-2 pt-4 border-t border-gray-100">
        <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50" @click="router.push('/device-models')">Hủy</button>
        <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50" :disabled="saving" @click="save">
          {{ saving ? 'Đang lưu...' : (isEdit ? 'Cập nhật' : 'Tạo mới') }}
        </button>
      </div>
    </div>
  </div>
</template>
