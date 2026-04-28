<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getDeviceModel, createDeviceModel, updateDeviceModel, deleteDeviceModel,
  listAssetCategories, uploadDeviceModelFile,
} from '@/api/imm00'
import type { ImmDeviceModel, AcAssetCategory } from '@/types/imm00'
import { useFormDraft } from '@/composables/useFormDraft'

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
const { clear: clearDraft } = useFormDraft('device-model-create', form, { enabled: !isEdit.value })

const categories = ref<AcAssetCategory[]>([])
const selectedCategory = computed<AcAssetCategory | null>(() =>
  categories.value.find(c => c.name === form.value.asset_category) ?? null,
)
const loading = ref(false)
const saving = ref(false)
const err = ref('')

// File upload state
const uploadingImage   = ref(false)
const uploadingCatalog = ref(false)
const uploadImageError = ref('')
const uploadCatalogError = ref('')

const MAX_IMAGE_MB   = 5
const MAX_CATALOG_MB = 20

async function uploadFile(
  file: File, fieldname: 'model_image' | 'catalog_file', maxMB: number,
): Promise<string> {
  if (file.size > maxMB * 1024 * 1024) {
    throw new Error(`File quá lớn. Tối đa ${maxMB}MB.`)
  }
  const res = await uploadDeviceModelFile(file, fieldname, name.value || '')
  return res.file_url
}

function fileNameFromUrl(url: string): string {
  if (!url) return ''
  try {
    const clean = url.split('?')[0].split('#')[0]
    const parts = clean.split('/')
    return decodeURIComponent(parts[parts.length - 1] || url)
  } catch {
    return url
  }
}

async function onImageChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  uploadingImage.value = true
  uploadImageError.value = ''
  try {
    form.value.model_image = await uploadFile(file, 'model_image', MAX_IMAGE_MB)
  } catch (ex) {
    uploadImageError.value = (ex as Error).message || 'Upload thất bại'
  } finally {
    uploadingImage.value = false
    target.value = ''
  }
}

async function onCatalogChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  uploadingCatalog.value = true
  uploadCatalogError.value = ''
  try {
    form.value.catalog_file = await uploadFile(file, 'catalog_file', MAX_CATALOG_MB)
  } catch (ex) {
    uploadCatalogError.value = (ex as Error).message || 'Upload thất bại'
  } finally {
    uploadingCatalog.value = false
    target.value = ''
  }
}

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
    clearDraft()
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

// Lightbox xem ảnh full-size
const showImagePreview = ref(false)
function openImagePreview() { if (form.value.model_image) showImagePreview.value = true }
function closeImagePreview() { showImagePreview.value = false }

// Auto-fill PM/Calibration từ Asset Category khi user chọn (chỉ ở chế độ tạo mới).
// Mỗi lần đổi category thì sync lại flag + interval theo danh mục — user có thể
// override sau đó.
watch(() => form.value.asset_category, (catName, prev) => {
  if (isEdit.value || !catName || catName === prev) return
  const cat = categories.value.find(c => c.name === catName)
  if (!cat) return
  form.value.is_pm_required = cat.default_pm_required ? 1 : 0
  if (cat.default_pm_required && cat.default_pm_interval_days) {
    form.value.pm_interval_days = cat.default_pm_interval_days
  }
  form.value.is_calibration_required = cat.default_calibration_required ? 1 : 0
  if (cat.default_calibration_required && cat.default_calibration_interval_days) {
    form.value.calibration_interval_days = cat.default_calibration_interval_days
  }
})

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
          <!-- Image upload + preview -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Hình ảnh đại diện</label>
            <div
v-if="form.model_image"
                 class="flex items-start gap-3 p-3 rounded-lg border border-gray-200 bg-gray-50">
              <button
type="button"
                      class="w-24 h-24 rounded-lg border border-slate-200 bg-white overflow-hidden flex-shrink-0 hover:ring-2 hover:ring-blue-400 transition cursor-zoom-in"
                      title="Bấm để xem kích thước đầy đủ"
                      @click="openImagePreview">
                <img
:src="form.model_image as string" alt="model preview"
                     class="w-full h-full object-cover" />
              </button>
              <div class="flex-1 min-w-0 space-y-1.5">
                <a
:href="form.model_image as string" target="_blank" rel="noopener"
                   class="block text-sm text-blue-600 hover:underline truncate"
                   :title="form.model_image as string">
                  {{ fileNameFromUrl(form.model_image as string) }}
                </a>
                <div class="flex items-center gap-2">
                  <label class="inline-flex items-center gap-1 text-xs text-gray-600 hover:text-blue-600 cursor-pointer">
                    <input
type="file" accept="image/*" class="hidden"
                           :disabled="uploadingImage"
                           @change="onImageChange" />
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
                    </svg>
                    {{ uploadingImage ? 'Đang tải...' : 'Thay ảnh' }}
                  </label>
                  <button
type="button"
                          class="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-red-600"
                          @click="form.model_image = ''">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Xóa
                  </button>
                </div>
              </div>
            </div>
            <label
v-else
                   class="flex flex-col items-center justify-center gap-1 h-24 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 hover:border-gray-400 transition-colors">
              <input
type="file" accept="image/*" class="hidden"
                     :disabled="uploadingImage"
                     @change="onImageChange" />
              <svg v-if="!uploadingImage" class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
              </svg>
              <span class="text-xs text-gray-500">
                {{ uploadingImage ? 'Đang tải lên...' : 'Bấm để chọn ảnh (jpg, png, webp — tối đa 5MB)' }}
              </span>
            </label>
            <p v-if="uploadImageError" class="text-xs text-red-600 mt-1">{{ uploadImageError }}</p>
          </div>

          <!-- Catalog upload -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Catalogue / Brochure</label>
            <div
v-if="form.catalog_file"
                 class="flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-200 bg-gray-50">
              <svg class="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.122 2.122l7.81-7.81" />
              </svg>
              <a
:href="form.catalog_file" target="_blank" rel="noopener"
                 class="flex-1 min-w-0 text-sm text-blue-600 hover:underline truncate"
                 :title="form.catalog_file">
                {{ fileNameFromUrl(form.catalog_file as string) }}
              </a>
              <button
type="button"
                      class="text-gray-400 hover:text-red-600 text-xs flex-shrink-0"
                      title="Xóa file"
                      @click="form.catalog_file = ''">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <label
v-else
                   class="flex items-center justify-center gap-2 h-11 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 hover:border-gray-400 transition-colors">
              <input
type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,application/pdf"
                     class="hidden"
                     :disabled="uploadingCatalog"
                     @change="onCatalogChange" />
              <svg v-if="!uploadingCatalog" class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.122 2.122l7.81-7.81" />
              </svg>
              <span class="text-xs text-gray-500">
                {{ uploadingCatalog ? 'Đang tải lên...' : 'Đính kèm PDF / DOC / XLSX' }}
              </span>
            </label>
            <p v-if="uploadCatalogError" class="text-xs text-red-600 mt-1">{{ uploadCatalogError }}</p>
          </div>
        </div>
      </div>

      <div class="pt-4 border-t border-gray-100 space-y-3">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Thông số kỹ thuật chi tiết</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Kích thước (DxRxC mm)</label>
            <input
v-model="form.dimensions" type="text" placeholder="1200x800x600"
                   class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Khối lượng (kg)</label>
            <input
v-model.number="form.weight_kg" type="number" min="0" step="0.1"
                   class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Thông số kỹ thuật đầy đủ</label>
          <textarea
v-model="form.specifications" rows="4"
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

    <!-- Lightbox xem ảnh model -->
    <div
v-if="showImagePreview && form.model_image"
         class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6 cursor-zoom-out"
         @click="closeImagePreview"
         @keydown.esc="closeImagePreview">
      <div class="relative max-w-5xl max-h-[90vh] flex flex-col items-center" @click.stop>
        <img
:src="form.model_image as string" alt="model preview"
             class="max-w-full max-h-[80vh] object-contain rounded-lg shadow-2xl bg-white" />
        <div class="mt-3 flex items-center gap-3 text-white text-sm">
          <span class="font-medium">{{ fileNameFromUrl(form.model_image as string) }}</span>
          <a
:href="form.model_image as string" target="_blank" rel="noopener"
             class="text-blue-200 hover:text-white underline-offset-4 hover:underline">
            Mở tab mới
          </a>
          <button
type="button"
                  class="ml-2 px-3 py-1 rounded-md bg-white/10 hover:bg-white/20 border border-white/20"
                  @click="closeImagePreview">
Đóng (Esc)
</button>
        </div>
      </div>
    </div>
  </div>
</template>
