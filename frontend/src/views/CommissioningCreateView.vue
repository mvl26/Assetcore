<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCommissioningStore } from '@/stores/commissioning'
import SmartSelect from '@/components/common/SmartSelect.vue'
import LinkInfoCard from '@/components/common/LinkInfoCard.vue'
import type { DeviceModelDetails } from '@/types/imm04'
import type { MasterItem } from '@/stores/useMasterDataStore'

const router = useRouter()
const store  = useCommissioningStore()

// ─── Form state ───────────────────────────────────────────────────────────────

const form = ref({
  // ── Procurement ──
  po_reference:               '',
  master_item:                '',   // IMM Device Model
  vendor:                     '',   // AC Supplier
  asset_description:          '',
  delivery_note_no:           '',
  purchase_price:             null as number | null,
  warranty_expiry_date:       '',
  // ── Scheduling ──
  clinical_dept:              '',   // AC Department
  expected_installation_date: '',
  reception_date:             '',
  // ── Installation ──
  installation_location:      '',   // AC Location
  received_by:                '',   // User — kho vận
  dept_head_acceptance:       '',   // User — trưởng khoa
  vendor_serial_no:           '',
  vendor_engineer_name:       '',
  commissioned_by:            '',
  is_radiation_device:        0 as 0 | 1,
  doa_incident:               0 as 0 | 1,
  risk_class:                 '' as '' | 'A' | 'B' | 'C' | 'D' | 'Radiation',
})

const RISK_COLOR: Record<string, string> = {
  A: '#059669', B: '#2563eb', C: '#d97706', D: '#dc2626', Radiation: '#7c3aed',
}
const riskColor = computed(() => RISK_COLOR[form.value.risk_class] ?? '#64748b')

// All 7 document types per IMM-04 spec
const documents = ref([
  { doc_type: 'CO - Chứng nhận Xuất xứ',    is_mandatory: 1, status: 'Pending' },
  { doc_type: 'CQ - Chứng nhận Chất lượng', is_mandatory: 1, status: 'Pending' },
  { doc_type: 'Packing List',                is_mandatory: 1, status: 'Pending' },
  { doc_type: 'Manual / HDSD',               is_mandatory: 1, status: 'Pending' },
  { doc_type: 'Warranty Card',               is_mandatory: 0, status: 'Pending' },
  { doc_type: 'Training Certificate',        is_mandatory: 0, status: 'Pending' },
  { doc_type: 'Other',                       is_mandatory: 0, status: 'Pending' },
])

const baselines = ref([
  { parameter: 'Earth Continuity',    is_critical: 1, measurement_type: 'Numeric', measured_val: '', expected_min: 0, expected_max: 0.5, unit: 'Ω',  test_result: 'N/A', na_applicable: 0, fail_note: '' },
  { parameter: 'Insulation Resistance',is_critical: 1, measurement_type: 'Numeric', measured_val: '', expected_min: 2,   expected_max: null, unit: 'MΩ', test_result: 'N/A', na_applicable: 0, fail_note: '' },
  { parameter: 'Leakage Current',     is_critical: 1, measurement_type: 'Numeric', measured_val: '', expected_min: 0, expected_max: 500, unit: 'µA', test_result: 'N/A', na_applicable: 0, fail_note: '' },
  { parameter: 'Applied Part Leakage',is_critical: 1, measurement_type: 'Numeric', measured_val: '', expected_min: 0, expected_max: 100, unit: 'µA', test_result: 'N/A', na_applicable: 0, fail_note: '' },
  { parameter: 'Patient Leakage AC',  is_critical: 1, measurement_type: 'Numeric', measured_val: '', expected_min: 0, expected_max: 10,  unit: 'µA', test_result: 'N/A', na_applicable: 1, fail_note: '' },
  { parameter: 'Patient Leakage DC',  is_critical: 1, measurement_type: 'Numeric', measured_val: '', expected_min: 0, expected_max: 10,  unit: 'µA', test_result: 'N/A', na_applicable: 1, fail_note: '' },
  { parameter: 'Power Input',         is_critical: 0, measurement_type: 'Numeric', measured_val: '', expected_min: null, expected_max: null, unit: 'W',  test_result: 'N/A', na_applicable: 1, fail_note: '' },
  { parameter: 'Visual Inspection',   is_critical: 1, measurement_type: 'Pass/Fail', measured_val: '', expected_min: null, expected_max: null, unit: '',   test_result: 'N/A', na_applicable: 0, fail_note: '' },
])

// ─── Validation ───────────────────────────────────────────────────────────────

type RequiredField = 'po_reference' | 'master_item' | 'vendor' | 'clinical_dept' | 'expected_installation_date' | 'vendor_serial_no'

const FIELD_LABELS: Record<RequiredField, string> = {
  po_reference:               'Lệnh mua hàng (PO)',
  master_item:                'Model Thiết bị',
  vendor:                     'Nhà cung cấp',
  clinical_dept:              'Khoa / Phòng nhận',
  expected_installation_date: 'Ngày hẹn lắp đặt',
  vendor_serial_no:           'Serial Number Hãng',
}

const fieldErrors = ref<Partial<Record<RequiredField, string>>>({})

function validateField(field: RequiredField) {
  if (form.value[field]) delete fieldErrors.value[field]
  else fieldErrors.value[field] = `${FIELD_LABELS[field]} là bắt buộc`
}

function validateAll(): boolean {
  ;(Object.keys(FIELD_LABELS) as RequiredField[]).forEach(validateField)
  return Object.keys(fieldErrors.value).length === 0
}

// ─── Loading / state ──────────────────────────────────────────────────────────

const loading     = ref(false)
const submitError = ref<string | null>(null)
const poLoading   = ref(false)

// ─── Selected entity details (cho InfoCards) ──────────────────────────────────

const poInfo           = ref<{ supplier_name: string; transaction_date: string; items_count: number } | null>(null)
const deviceModelInfo  = ref<DeviceModelDetails | null>(null)
const vendorInfo       = ref<MasterItem | null>(null)
const deptInfo         = ref<MasterItem | null>(null)
const locationInfo     = ref<MasterItem | null>(null)

// ─── PO auto-fill ─────────────────────────────────────────────────────────────

async function onPoSelect(item: MasterItem) {
  form.value.po_reference = item.id
  validateField('po_reference')
  await lookupPO(item.id)
}

async function lookupPO(poName: string) {
  if (!poName) return
  poLoading.value   = true
  submitError.value = null
  const data = await store.fetchPoDetails(poName)
  poLoading.value   = false
  if (data) {
    poInfo.value = {
      supplier_name: data.supplier_name,
      transaction_date: data.transaction_date,
      items_count: data.items?.length ?? 0,
    }
    if (data.supplier) {
      form.value.vendor = data.supplier
      validateField('vendor')
    }
  } else {
    poInfo.value = null
    submitError.value = 'Không tìm thấy PO'
  }
}

async function onDeviceModelSelect(item: MasterItem) {
  form.value.master_item = item.id
  validateField('master_item')
  const model = await store.fetchDeviceModelDetails(item.id)
  if (!model) return
  deviceModelInfo.value = model
  // Map WHO class → NĐ98 risk_class
  const classMap: Record<string, typeof form.value.risk_class> = {
    'Class I': 'A', 'Class II': 'B', 'Class III': 'C',
  }
  if (!form.value.risk_class) {
    form.value.risk_class = model.is_radiation_device
      ? 'Radiation'
      : (classMap[model.medical_device_class] ?? '')
  }
  if (model.is_radiation_device) form.value.is_radiation_device = 1
  // Auto-suggest asset_description from model_name if empty
  if (!form.value.asset_description && model.model_name) {
    form.value.asset_description = `${model.model_name} (${model.manufacturer})`
  }
}

function onVendorSelect(item: MasterItem)   { vendorInfo.value = item }
function onDeptSelect(item: MasterItem)     { deptInfo.value = item }
function onLocationSelect(item: MasterItem) { locationInfo.value = item }

function onClearMasterItem()  { deviceModelInfo.value = null }
function onClearPo()          { poInfo.value = null }
function onClearVendor()      { vendorInfo.value = null }
function onClearDept()        { deptInfo.value = null }
function onClearLocation()    { locationInfo.value = null }

function toggleDoc(i: number) {
  documents.value[i].status = documents.value[i].status === 'Received' ? 'Pending' : 'Received'
}

// ─── Submit ───────────────────────────────────────────────────────────────────

async function handleCreate() {
  submitError.value = null
  if (!validateAll()) return

  loading.value = true
  const name = await store.createDoc({
    ...form.value,
    commissioning_documents: documents.value,
    baseline_tests:          baselines.value,
  })
  loading.value = false

  if (name) router.push(`/commissioning/${name}`)
  else submitError.value = store.error ?? 'Không thể tạo phiếu'
}
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Breadcrumb -->
    <nav class="flex items-center gap-1.5 text-xs text-slate-400 mb-6">
      <button class="hover:text-slate-600 transition-colors" @click="router.push('/dashboard')">Tổng quan</button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <button class="hover:text-slate-600 transition-colors" @click="router.push('/commissioning')">Danh sách phiếu</button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <span class="font-semibold text-slate-700">Tạo phiếu mới</span>
    </nav>

    <!-- Page header -->
    <div class="mb-7">
      <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-04</p>
      <h1 class="text-2xl font-bold text-slate-900">Tạo Phiếu Tiếp Nhận Thiết Bị</h1>
      <p class="text-sm text-slate-500 mt-1">Điền đầy đủ thông tin để khởi tạo quy trình lắp đặt</p>
    </div>

    <!-- Error banner -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="submitError" class="alert-error mb-6">
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="flex-1 text-sm">{{ submitError }}</span>
        <button class="text-red-400 hover:text-red-600 transition-colors" @click="submitError = null">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </Transition>

    <form class="space-y-6" @submit.prevent="handleCreate">

      <!-- ─── Section 1: Mua sắm & Thiết bị ─────────────────────────────────── -->
      <div class="card animate-slide-up" style="animation-delay: 40ms">
        <h3 class="text-sm font-semibold text-slate-800 mb-5 flex items-center gap-2">
          <span class="w-5 h-5 rounded-md bg-brand-600 text-white flex items-center justify-center text-[11px] font-bold shrink-0">1</span>
          Thông tin Mua sắm &amp; Thiết bị
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">

          <!-- PO Reference -->
          <div class="form-group">
            <p class="form-label">Lệnh mua hàng (PO) <span class="text-red-500">*</span></p>
            <SmartSelect
              v-model="form.po_reference"
              doctype="Purchase Order"
              placeholder="PO-2026-0041"
              :has-error="!!fieldErrors.po_reference"
              @select="onPoSelect"
              @clear="onClearPo"
              @blur="validateField('po_reference')"
            />
            <p v-if="fieldErrors.po_reference" class="mt-1 text-xs text-red-500">{{ fieldErrors.po_reference }}</p>
            <LinkInfoCard
              v-if="poInfo"
              title="Thông tin PO"
              variant="info"
              :fields="[
                { label: 'NCC', value: poInfo.supplier_name },
                { label: 'Ngày PO', value: poInfo.transaction_date },
                { label: 'Số mặt hàng', value: poInfo.items_count },
              ]"
            />
          </div>

          <!-- Vendor (AC Supplier — auto-filled from PO if match found) -->
          <div class="form-group">
            <p class="form-label">Nhà cung cấp <span class="text-red-500">*</span></p>
            <SmartSelect
              v-model="form.vendor"
              doctype="AC Supplier"
              placeholder="Tự điền khi chọn PO (nếu có)"
              :has-error="!!fieldErrors.vendor"
              @select="onVendorSelect"
              @clear="onClearVendor"
              @blur="validateField('vendor')"
            />
            <p v-if="fieldErrors.vendor" class="mt-1 text-xs text-red-500">{{ fieldErrors.vendor }}</p>
            <LinkInfoCard
              v-if="vendorInfo"
              title="Nhà cung cấp đã chọn"
              variant="success"
              :fields="[
                { label: 'Tên', value: vendorInfo.name },
                { label: 'Mã NCC', value: vendorInfo.id, type: 'mono' },
                { label: 'Loại / Mô tả', value: vendorInfo.description },
              ]"
            />
          </div>

          <!-- Master Item — IMM Device Model -->
          <div class="form-group md:col-span-2">
            <p class="form-label">Model Thiết bị <span class="text-red-500">*</span></p>
            <SmartSelect
              v-model="form.master_item"
              doctype="IMM Device Model"
              placeholder="Tìm theo tên model hoặc nhà sản xuất"
              :has-error="!!fieldErrors.master_item"
              @select="onDeviceModelSelect"
              @clear="onClearMasterItem"
              @blur="validateField('master_item')"
            />
            <p v-if="fieldErrors.master_item" class="mt-1 text-xs text-red-500">{{ fieldErrors.master_item }}</p>
            <LinkInfoCard
              v-if="deviceModelInfo"
              title="Chi tiết Device Model — auto-fill risk class & PM/Calibration"
              variant="info"
              :fields="[
                { label: 'Model', value: deviceModelInfo.model_name },
                { label: 'Hãng', value: deviceModelInfo.manufacturer },
                { label: 'WHO Class', value: deviceModelInfo.medical_device_class, type: 'badge' },
                { label: 'Risk', value: deviceModelInfo.risk_classification, type: 'badge' },
                { label: 'Bức xạ', value: deviceModelInfo.is_radiation_device ? 'Có ⚠️' : 'Không' },
                { label: 'PM định kỳ', value: deviceModelInfo.is_pm_required ? `${deviceModelInfo.pm_interval_days} ngày` : 'Không yêu cầu' },
                { label: 'Hiệu chuẩn', value: deviceModelInfo.is_calibration_required ? `${deviceModelInfo.calibration_interval_days} ngày` : 'Không yêu cầu' },
              ]"
            />
          </div>

          <!-- Clinical Dept — AC Department -->
          <div class="form-group">
            <p class="form-label">Khoa / Phòng sử dụng <span class="text-red-500">*</span></p>
            <SmartSelect
              v-model="form.clinical_dept"
              doctype="AC Department"
              placeholder="Tìm theo tên hoặc mã khoa"
              :has-error="!!fieldErrors.clinical_dept"
              @select="onDeptSelect"
              @clear="onClearDept"
              @blur="validateField('clinical_dept')"
            />
            <p v-if="fieldErrors.clinical_dept" class="mt-1 text-xs text-red-500">{{ fieldErrors.clinical_dept }}</p>
            <LinkInfoCard
              v-if="deptInfo"
              title="Khoa / Phòng"
              variant="success"
              :fields="[
                { label: 'Tên', value: deptInfo.name },
                { label: 'Mã', value: deptInfo.id, type: 'mono' },
                { label: 'Ghi chú', value: deptInfo.description },
              ]"
            />
          </div>

          <!-- Installation Location — AC Location -->
          <div class="form-group">
            <p class="form-label">Vị trí lắp đặt</p>
            <SmartSelect
              v-model="form.installation_location"
              doctype="AC Location"
              placeholder="Phòng / khu vực cụ thể"
              @select="onLocationSelect"
              @clear="onClearLocation"
            />
            <p class="mt-1 text-[11px] text-slate-400">Phòng hoặc khu vực lắp đặt trong khoa (tùy chọn)</p>
            <LinkInfoCard
              v-if="locationInfo"
              title="Vị trí lắp đặt"
              variant="success"
              :fields="[
                { label: 'Tên', value: locationInfo.name },
                { label: 'Mã', value: locationInfo.id, type: 'mono' },
                { label: 'Khu vực', value: locationInfo.description },
              ]"
            />
          </div>

          <!-- Serial Number -->
          <div class="form-group">
            <label for="vendor_serial_no" class="form-label">Serial Number Hãng <span class="text-red-500">*</span></label>
            <input
              id="vendor_serial_no"
              v-model="form.vendor_serial_no"
              type="text"
              class="form-input font-mono"
              :class="{ 'border-red-400 ring-1 ring-red-300': fieldErrors.vendor_serial_no }"
              placeholder="VNT-PHL-20260001"
              @blur="validateField('vendor_serial_no')"
            />
            <p v-if="fieldErrors.vendor_serial_no" class="mt-1 text-xs text-red-500">{{ fieldErrors.vendor_serial_no }}</p>
          </div>

          <!-- Risk Class (auto-filled, display-only) -->
          <div class="form-group">
            <p class="form-label">Phân loại rủi ro</p>
            <div class="flex items-center gap-2 h-9">
              <span
                v-if="form.risk_class"
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold"
                :style="`background: ${riskColor}18; color: ${riskColor}; border: 1px solid ${riskColor}40`"
              >
                <span class="w-2 h-2 rounded-full" :style="`background: ${riskColor}`" />
                Class {{ form.risk_class }}
              </span>
              <span v-else class="text-sm text-slate-400 italic">Tự động điền khi chọn Model</span>
            </div>
          </div>

          <!-- Expected installation date -->
          <div class="form-group">
            <label for="expected_installation_date" class="form-label">Ngày hẹn lắp đặt <span class="text-red-500">*</span></label>
            <input
              id="expected_installation_date"
              v-model="form.expected_installation_date"
              type="date"
              class="form-input"
              :class="{ 'border-red-400 ring-1 ring-red-300': fieldErrors.expected_installation_date }"
              @change="validateField('expected_installation_date')"
            />
            <p v-if="fieldErrors.expected_installation_date" class="mt-1 text-xs text-red-500">{{ fieldErrors.expected_installation_date }}</p>
          </div>

          <!-- Reception date -->
          <div class="form-group">
            <label for="reception_date" class="form-label">Ngày tiếp nhận thực tế</label>
            <input
              id="reception_date"
              v-model="form.reception_date"
              type="date"
              class="form-input"
            />
            <p class="mt-1 text-[11px] text-slate-400">Để trống nếu chưa nhận hàng</p>
          </div>

          <!-- Asset description — becomes asset_name trên AC Asset -->
          <div class="form-group">
            <label for="asset_description" class="form-label">Tên / Mô tả Tài sản</label>
            <input
              id="asset_description"
              v-model="form.asset_description"
              type="text"
              class="form-input"
              placeholder="Máy siêu âm Philips Affiniti 70"
            />
            <p class="mt-1 text-[11px] text-slate-400">Dùng làm asset_name khi tạo AC Asset</p>
          </div>

          <!-- Delivery note / Packing list -->
          <div class="form-group">
            <label for="delivery_note_no" class="form-label">Số Phiếu Giao Hàng / Packing List</label>
            <input
              id="delivery_note_no"
              v-model="form.delivery_note_no"
              type="text"
              class="form-input font-mono"
              placeholder="DN-2026-0123"
            />
          </div>

          <!-- Purchase price -->
          <div class="form-group">
            <label for="purchase_price" class="form-label">Giá trị Mua sắm (VNĐ)</label>
            <input
              id="purchase_price"
              v-model.number="form.purchase_price"
              type="number"
              min="0"
              class="form-input"
              placeholder="0"
            />
            <p class="mt-1 text-[11px] text-slate-400">Theo PO / hợp đồng</p>
          </div>

          <!-- Warranty expiry -->
          <div class="form-group">
            <label for="warranty_expiry_date" class="form-label">Ngày Hết Bảo Hành</label>
            <input
              id="warranty_expiry_date"
              v-model="form.warranty_expiry_date"
              type="date"
              class="form-input"
            />
          </div>

          <!-- Vendor engineer -->
          <div class="form-group">
            <label for="vendor_engineer_name" class="form-label">Kỹ sư Nhà cung cấp</label>
            <input
              id="vendor_engineer_name"
              v-model="form.vendor_engineer_name"
              type="text"
              class="form-input"
              placeholder="Nguyễn Văn A"
            />
          </div>

          <!-- Commissioned by -->
          <div class="form-group">
            <p class="form-label">KTV thực hiện lắp đặt</p>
            <SmartSelect
              v-model="form.commissioned_by"
              doctype="User"
              placeholder="Chọn KTV..."
            />
          </div>

          <!-- Received by — kho vận -->
          <div class="form-group">
            <p class="form-label">Người tiếp nhận (Kho vận)</p>
            <SmartSelect
              v-model="form.received_by"
              doctype="User"
              placeholder="NV kho vận xác nhận hàng..."
            />
          </div>

          <!-- Dept head acceptance — trưởng khoa -->
          <div class="form-group">
            <p class="form-label">Trưởng khoa tiếp nhận</p>
            <SmartSelect
              v-model="form.dept_head_acceptance"
              doctype="User"
              placeholder="Trưởng khoa ký biên bản..."
            />
          </div>
        </div>

        <!-- Flags -->
        <div class="flex flex-wrap gap-5 mt-5 pt-5 border-t border-slate-100">
          <label for="is_radiation_device" class="flex items-center gap-2.5 cursor-pointer group">
            <input
              id="is_radiation_device"
              type="checkbox"
              class="sr-only"
              :checked="Boolean(form.is_radiation_device)"
              @change="form.is_radiation_device = ($event.target as HTMLInputElement).checked ? 1 : 0"
            />
            <div
              class="w-5 h-5 rounded border-2 flex items-center justify-center transition-colors pointer-events-none"
              :class="form.is_radiation_device ? 'bg-purple-600 border-purple-600' : 'border-slate-300 group-hover:border-purple-400'"
            >
              <svg v-if="form.is_radiation_device" class="w-3 h-3 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <span class="text-sm text-slate-700">Thiết bị phát bức xạ / tia X</span>
            <span class="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-medium">Radiation</span>
          </label>

          <label for="doa_incident" class="flex items-center gap-2.5 cursor-pointer group">
            <input
              id="doa_incident"
              type="checkbox"
              class="sr-only"
              :checked="Boolean(form.doa_incident)"
              @change="form.doa_incident = ($event.target as HTMLInputElement).checked ? 1 : 0"
            />
            <div
              class="w-5 h-5 rounded border-2 flex items-center justify-center transition-colors pointer-events-none"
              :class="form.doa_incident ? 'bg-red-600 border-red-600' : 'border-slate-300 group-hover:border-red-400'"
            >
              <svg v-if="form.doa_incident" class="w-3 h-3 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <span class="text-sm text-slate-700">Sự cố DOA (Dead-on-Arrival)</span>
            <span class="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-medium">DOA</span>
          </label>
        </div>
      </div>

      <!-- ─── Section 2: Hồ sơ đi kèm ──────────────────────────────────────── -->
      <div class="card animate-slide-up" style="animation-delay: 80ms">
        <h3 class="text-sm font-semibold text-slate-800 mb-5 flex items-center gap-2">
          <span class="w-5 h-5 rounded-md bg-brand-600 text-white flex items-center justify-center text-[11px] font-bold shrink-0">2</span>
          Hồ sơ đi kèm
          <span class="ml-auto text-xs font-normal text-slate-400">
            {{ documents.filter(d => d.status === 'Received').length }}/{{ documents.length }} đã nhận
          </span>
        </h3>
        <div class="space-y-2">
          <div
            v-for="(doc, i) in documents"
            :key="i"
            class="flex items-center gap-3 px-4 py-3 rounded-xl border transition-all cursor-pointer"
            :class="doc.status === 'Received'
              ? 'bg-emerald-50 border-emerald-200'
              : 'bg-white border-slate-100 hover:border-slate-200'"
            @click="toggleDoc(i)"
          >
            <div
              class="w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-all"
              :class="doc.status === 'Received'
                ? 'bg-emerald-500 border-emerald-500'
                : 'border-slate-300'"
            >
              <svg v-if="doc.status === 'Received'" class="w-3 h-3 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <span class="text-sm text-slate-700 flex-1">{{ doc.doc_type }}</span>
            <span v-if="doc.is_mandatory" class="text-[10px] font-semibold text-red-500 bg-red-50 px-1.5 py-0.5 rounded">Bắt buộc</span>
            <span
              class="text-[11px] font-medium px-2.5 py-0.5 rounded-full"
              :class="doc.status === 'Received' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'"
            >
              {{ doc.status === 'Received' ? 'Đã nhận' : 'Chưa nhận' }}
            </span>
          </div>
        </div>
      </div>

      <!-- ─── Section 3: Checklist kiểm tra an toàn điện ────────────────────── -->
      <div class="card animate-slide-up" style="animation-delay: 120ms">
        <h3 class="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
          <span class="w-5 h-5 rounded-md bg-brand-600 text-white flex items-center justify-center text-[11px] font-bold shrink-0">3</span>
          Checklist Kiểm tra An toàn Điện
        </h3>
        <p class="text-xs text-slate-400 mb-5 ml-7">Kết quả sẽ được điền sau khi lắp đặt (có thể bỏ qua lúc tạo)</p>

        <div class="overflow-x-auto -mx-6">
          <table class="min-w-full">
            <thead>
              <tr>
                <th class="table-header pl-6">Thông số</th>
                <th class="table-header text-center">Quan trọng</th>
                <th class="table-header">Loại đo</th>
                <th class="table-header">Giới hạn</th>
                <th class="table-header">Đơn vị</th>
                <th class="table-header text-center pr-6">N/A</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="(row, i) in baselines"
                :key="i"
                class="hover:bg-slate-50 transition-colors"
              >
                <td class="table-cell pl-6 font-medium text-slate-700">{{ row.parameter }}</td>
                <td class="table-cell text-center">
                  <span
                    class="inline-block w-2 h-2 rounded-full"
                    :class="row.is_critical ? 'bg-red-500' : 'bg-slate-300'"
                    :title="row.is_critical ? 'Critical' : 'Non-critical'"
                  />
                </td>
                <td class="table-cell text-slate-500 text-xs">{{ row.measurement_type }}</td>
                <td class="table-cell text-xs font-mono text-slate-500">
                  <template v-if="row.expected_min != null || row.expected_max != null">
                    {{ row.expected_min ?? '—' }} ~ {{ row.expected_max ?? '∞' }}
                  </template>
                  <template v-else>—</template>
                </td>
                <td class="table-cell font-mono text-xs text-slate-400">{{ row.unit || '—' }}</td>
                <td class="table-cell text-center pr-6">
                  <input
                    v-model="row.na_applicable"
                    type="checkbox"
                    class="rounded text-brand-600"
                    :true-value="1"
                    :false-value="0"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ─── Actions ─────────────────────────────────────────────────────────── -->
      <div class="flex items-center justify-between gap-4 animate-slide-up" style="animation-delay: 160ms">
        <button
          type="button"
          class="btn-secondary"
          @click="router.push('/commissioning')"
        >
          Hủy
        </button>

        <button
          type="submit"
          class="btn-primary px-8"
          :disabled="loading"
        >
          <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          {{ loading ? 'Đang tạo phiếu...' : 'Tạo Phiếu Tiếp Nhận' }}
        </button>
      </div>

    </form>
  </div>
</template>
