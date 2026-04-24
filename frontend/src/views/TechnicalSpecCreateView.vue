<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm02Store } from '@/stores/imm02'
import { useImm01Store } from '@/stores/imm01'
import SmartSelect from '@/components/common/SmartSelect.vue'
import type { MasterItem } from '@/stores/useMasterDataStore'

const router   = useRouter()
const route    = useRoute()
const store    = useImm02Store()
const naStore  = useImm01Store()

// Pre-fill from query param khi navigate từ NA hoặc PP Detail
const naId = route.query.na as string | undefined

const form = ref({
  needs_assessment:              naId ?? '',
  equipment_description:         '',
  regulatory_class:              '',
  mdd_class:                    '',
  performance_requirements:      '',
  safety_standards:              '',
  accessories_included:          '',
  warranty_terms:                '',
  expected_delivery_weeks:       null as number | null,
  installation_requirements:     '',
  training_requirements:         '',
  reference_standard:            '',
  device_model:                  '',
  procurement_method:            '',
  required_by_date:              '',
  delivery_location:             '',
  reference_price_estimate:      null as number | null,
  site_requirements:             '',
  lifetime_support_requirements: '',
  device_evaluation_ref:         '',
})

const errors  = ref<Record<string, string>>({})
const touched = ref<Record<string, boolean>>({})

const REGULATORY_CLASSES = ['Class A', 'Class B', 'Class C', 'Class D']
const PROCUREMENT_METHODS = ['RFQ', 'Tender', 'Direct', 'Sole Source']

function validate(): boolean {
  const e: Record<string, string> = {}
  if (!form.value.equipment_description.trim())      e.equipment_description    = 'Vui lòng nhập mô tả thiết bị'
  if (!form.value.regulatory_class)                  e.regulatory_class         = 'Vui lòng chọn phân loại NĐ98'
  if (!form.value.performance_requirements.trim())   e.performance_requirements = 'Vui lòng nhập yêu cầu hiệu năng'
  if (!form.value.safety_standards.trim())           e.safety_standards         = 'Vui lòng nhập tiêu chuẩn an toàn'
  if (!form.value.procurement_method)                e.procurement_method       = 'Vui lòng chọn phương thức mua sắm'
  errors.value = e
  return Object.keys(e).length === 0
}

function touch(field: string) {
  touched.value[field] = true
  validate()
}

async function handleSubmit() {
  Object.keys(form.value).forEach(k => (touched.value[k] = true))
  if (!validate()) return
  const tsName = await store.createTs({
    needs_assessment:              form.value.needs_assessment || undefined,
    equipment_description:         form.value.equipment_description,
    regulatory_class:              form.value.regulatory_class,
    mdd_class:                     form.value.mdd_class || undefined,
    performance_requirements:      form.value.performance_requirements,
    safety_standards:              form.value.safety_standards,
    accessories_included:          form.value.accessories_included || undefined,
    warranty_terms:                form.value.warranty_terms || undefined,
    expected_delivery_weeks:       form.value.expected_delivery_weeks ?? undefined,
    installation_requirements:     form.value.installation_requirements || undefined,
    training_requirements:         form.value.training_requirements || undefined,
    reference_standard:            form.value.reference_standard || undefined,
    device_model:                  form.value.device_model || undefined,
    procurement_method:            form.value.procurement_method || undefined,
    required_by_date:              form.value.required_by_date || undefined,
    delivery_location:             form.value.delivery_location || undefined,
    reference_price_estimate:      form.value.reference_price_estimate ?? undefined,
    site_requirements:             form.value.site_requirements || undefined,
    lifetime_support_requirements: form.value.lifetime_support_requirements || undefined,
    device_evaluation_ref:         form.value.device_evaluation_ref || undefined,
  })
  if (tsName) router.replace(`/planning/technical-specs/${tsName}`)
}

function onDeviceModelSelect(item: MasterItem) {
  form.value.device_model = item.id
}

function fieldError(f: string): string {
  return touched.value[f] ? (errors.value[f] ?? '') : ''
}

onMounted(async () => {
  store.clearError()
  // Auto-fill equipment_description từ NA nếu navigate từ phiếu nhu cầu
  if (naId) {
    await naStore.fetchOne(naId)
    if (naStore.currentDoc?.equipment_type) {
      form.value.equipment_description = naStore.currentDoc.equipment_type
    }
  }
})
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-03</p>
        <h1 class="text-2xl font-bold text-slate-900">Tạo Đặc tả Kỹ thuật</h1>
        <p class="text-sm text-slate-500 mt-1">Điền đầy đủ thông tin kỹ thuật cho thiết bị cần mua sắm</p>
      </div>
      <button class="btn-ghost shrink-0" @click="router.back()">Quay lại</button>
    </div>

    <div v-if="store.tsError" class="alert-error mb-4">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.tsError }}</span>
      <button class="text-xs font-semibold underline" @click="store.clearError">Đóng</button>
    </div>

    <!-- Banner NA liên kết -->
    <div v-if="form.needs_assessment"
         class="mb-5 p-3 bg-blue-50 border border-blue-100 rounded-xl text-xs text-blue-800 flex items-center gap-2">
      <svg class="w-4 h-4 shrink-0 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
      <span>Đặc tả này sẽ được liên kết với phiếu nhu cầu
        <strong class="font-mono">{{ form.needs_assessment }}</strong>
      </span>
    </div>

    <!-- Card 1: Thông tin thiết bị -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:0ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4">Thông tin thiết bị</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="form-group sm:col-span-2">
          <label class="form-label">Mô tả thiết bị <span class="text-red-500">*</span></label>
          <input v-model="form.equipment_description" type="text" class="form-input"
                 :class="{ 'border-red-400': fieldError('equipment_description') }"
                 placeholder="vd: Máy siêu âm tim xách tay"
                 @blur="touch('equipment_description')" />
          <p v-if="fieldError('equipment_description')" class="mt-1 text-xs text-red-500">
            {{ fieldError('equipment_description') }}
          </p>
        </div>
        <div class="form-group">
          <label class="form-label">Mẫu thiết bị (Device Model)</label>
          <SmartSelect
            doctype="IMM Device Model"
            placeholder="Chọn mẫu thiết bị (tùy chọn)..."
            :model-value="form.device_model"
            @select="onDeviceModelSelect"
            @clear="form.device_model = ''"
          />
        </div>
      </div>
    </div>

    <!-- Card 2: Phân loại & Tiêu chuẩn -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:40ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4">Phân loại & Tiêu chuẩn</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="form-group">
          <label class="form-label">Phân loại NĐ98 <span class="text-red-500">*</span></label>
          <select v-model="form.regulatory_class" class="form-select"
                  :class="{ 'border-red-400': fieldError('regulatory_class') }"
                  @change="touch('regulatory_class')">
            <option value="">— Chọn phân loại —</option>
            <option v-for="c in REGULATORY_CLASSES" :key="c" :value="c">{{ c }}</option>
          </select>
          <p v-if="fieldError('regulatory_class')" class="mt-1 text-xs text-red-500">
            {{ fieldError('regulatory_class') }}
          </p>
        </div>
        <div class="form-group">
          <label class="form-label">Phân loại MDD</label>
          <input v-model="form.mdd_class" type="text" class="form-input"
                 placeholder="vd: MDD Class IIa (tùy chọn)" />
        </div>
        <div class="form-group sm:col-span-2">
          <label class="form-label">Tiêu chuẩn tham chiếu</label>
          <input v-model="form.reference_standard" type="text" class="form-input"
                 placeholder="vd: ISO 13485:2016, IEC 60601-1 (tùy chọn)" />
        </div>
      </div>
    </div>

    <!-- Card 3: Thông tin Mua sắm (WHO 6.2) -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:70ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4">Thông tin Mua sắm <span class="text-xs font-normal text-slate-400">(WHO 6.2)</span></h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="form-group">
          <label class="form-label">Phương thức mua sắm <span class="text-red-500">*</span></label>
          <select v-model="form.procurement_method" class="form-select"
                  :class="{ 'border-red-400': fieldError('procurement_method') }"
                  @change="touch('procurement_method')">
            <option value="">— Chọn phương thức —</option>
            <option v-for="m in PROCUREMENT_METHODS" :key="m" :value="m">{{ m }}</option>
          </select>
          <p v-if="fieldError('procurement_method')" class="mt-1 text-xs text-red-500">
            {{ fieldError('procurement_method') }}
          </p>
        </div>
        <div class="form-group">
          <label class="form-label">Cần giao trước ngày</label>
          <input v-model="form.required_by_date" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Địa điểm lắp đặt</label>
          <input v-model="form.delivery_location" type="text" class="form-input"
                 placeholder="vd: Khoa Tim mạch, Tòa nhà B, Tầng 3" />
        </div>
        <div class="form-group">
          <label class="form-label">Giá tham chiếu ước tính (VND)</label>
          <input v-model.number="form.reference_price_estimate" type="number" min="0" step="1000000" class="form-input"
                 placeholder="vd: 500000000" />
        </div>
      </div>
    </div>

    <!-- Card 4: Yêu cầu Vòng đời (WHO 6.3) -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:80ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4">Yêu cầu Vòng đời <span class="text-xs font-normal text-slate-400">(WHO 6.3)</span></h2>
      <div class="grid grid-cols-1 gap-4">
        <div class="form-group">
          <label class="form-label">Yêu cầu địa điểm & hạ tầng</label>
          <textarea v-model="form.site_requirements" class="form-textarea" rows="3"
                    placeholder="Yêu cầu về không gian, nguồn điện, nhiệt độ, độ ẩm, khí nén… (tùy chọn)" />
        </div>
        <div class="form-group">
          <label class="form-label">Yêu cầu hỗ trợ vòng đời</label>
          <textarea v-model="form.lifetime_support_requirements" class="form-textarea" rows="3"
                    placeholder="Yêu cầu về vận hành, bảo trì định kỳ, phụ tùng thay thế… (tùy chọn)" />
        </div>
        <div class="form-group">
          <label class="form-label">Chứng nhận thiết bị (IEC/ISO)</label>
          <input v-model="form.device_evaluation_ref" type="text" class="form-input"
                 placeholder="vd: IEC 60601-1, ISO 13485:2016 (tùy chọn)" />
        </div>
      </div>
    </div>

    <!-- Card 5: Yêu cầu kỹ thuật -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:110ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4">Yêu cầu kỹ thuật</h2>
      <div class="grid grid-cols-1 gap-4">
        <div class="form-group">
          <label class="form-label">Yêu cầu hiệu năng <span class="text-red-500">*</span></label>
          <textarea v-model="form.performance_requirements" class="form-textarea" rows="4"
                    :class="{ 'border-red-400': fieldError('performance_requirements') }"
                    placeholder="Mô tả chi tiết các yêu cầu về hiệu năng (độ phân giải, tần số, độ chính xác…)"
                    @blur="touch('performance_requirements')" />
          <p v-if="fieldError('performance_requirements')" class="mt-1 text-xs text-red-500">
            {{ fieldError('performance_requirements') }}
          </p>
        </div>
        <div class="form-group">
          <label class="form-label">Tiêu chuẩn an toàn <span class="text-red-500">*</span></label>
          <textarea v-model="form.safety_standards" class="form-textarea" rows="4"
                    :class="{ 'border-red-400': fieldError('safety_standards') }"
                    placeholder="Mô tả các tiêu chuẩn an toàn áp dụng (điện, cơ học, điện từ…)"
                    @blur="touch('safety_standards')" />
          <p v-if="fieldError('safety_standards')" class="mt-1 text-xs text-red-500">
            {{ fieldError('safety_standards') }}
          </p>
        </div>
        <div class="form-group">
          <label class="form-label">Phụ kiện đi kèm</label>
          <textarea v-model="form.accessories_included" class="form-textarea" rows="3"
                    placeholder="Liệt kê phụ kiện, cáp, đầu dò… đi kèm (tùy chọn)" />
        </div>
      </div>
    </div>

    <!-- Card 6: Bàn giao & Bảo hành -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:150ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4">Bàn giao & Bảo hành</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="form-group">
          <label class="form-label">Điều khoản bảo hành</label>
          <input v-model="form.warranty_terms" type="text" class="form-input"
                 placeholder="vd: 24 tháng từ ngày nghiệm thu" />
        </div>
        <div class="form-group">
          <label class="form-label">Thời gian giao hàng (tuần)</label>
          <input v-model.number="form.expected_delivery_weeks" type="number" min="1" class="form-input"
                 placeholder="vd: 12" />
        </div>
        <div class="form-group">
          <label class="form-label">Yêu cầu lắp đặt</label>
          <textarea v-model="form.installation_requirements" class="form-textarea" rows="3"
                    placeholder="Điều kiện phòng, nguồn điện, khí nén… (tùy chọn)" />
        </div>
        <div class="form-group">
          <label class="form-label">Yêu cầu đào tạo</label>
          <textarea v-model="form.training_requirements" class="form-textarea" rows="3"
                    placeholder="Số lượng người, thời lượng, nội dung đào tạo… (tùy chọn)" />
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-2 pb-8">
      <button class="btn-primary" :disabled="store.tsLoading" @click="handleSubmit">
        <svg v-if="store.tsLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        {{ store.tsLoading ? 'Đang lưu…' : 'Tạo Đặc tả Kỹ thuật' }}
      </button>
      <button class="btn-ghost" :disabled="store.tsLoading" @click="router.back()">Hủy</button>
    </div>

  </div>
</template>
