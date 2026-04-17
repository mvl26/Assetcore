<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCommissioningStore } from '@/stores/commissioning'
import { getPoDetails } from '@/api/imm04'
import { frappeGet } from '@/api/helpers'
import LinkSearch from '@/components/common/LinkSearch.vue'
import type { LinkItem } from '@/types/imm04'

const router = useRouter()
const store  = useCommissioningStore()

// ─── Form state ───────────────────────────────────────────────────────────────

const form = ref({
  po_reference:              '',
  master_item:               '',
  vendor:                    '',
  clinical_dept:             '',
  expected_installation_date:'',
  reception_date:            '',
  vendor_serial_no:          '',
  vendor_engineer_name:      '',
  commissioned_by:           '',
  is_radiation_device:       0 as 0 | 1,
  doa_incident:              0 as 0 | 1,
  risk_class:                '' as '' | 'A' | 'B' | 'C' | 'D' | 'Radiation',
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

const loading   = ref(false)
const submitError = ref<string | null>(null)
const poLoading   = ref(false)
const poItems     = ref<{ item_code: string; item_name: string; is_radiation: boolean }[]>([])

// ─── PO auto-fill ─────────────────────────────────────────────────────────────

async function onPoSelect(item: LinkItem) {
  form.value.po_reference = item.value
  validateField('po_reference')
  await lookupPO(item.value)
}

async function lookupPO(poName: string) {
  if (!poName) return
  poLoading.value   = true
  submitError.value = null
  try {
    const res = await getPoDetails(poName)
    if (res.success && res.data) {
      form.value.vendor = res.data.supplier
      validateField('vendor')
      poItems.value = res.data.items
      if (poItems.value.length === 1) selectItem(poItems.value[0])
    } else {
      submitError.value = res.error ?? 'Không tìm thấy PO'
    }
  } catch (e) {
    submitError.value = e instanceof Error ? e.message : 'Lỗi khi tra cứu PO'
  } finally {
    poLoading.value = false
  }
}

async function fetchItemRiskClass(itemCode: string) {
  try {
    const res = await frappeGet<{ message: { custom_risk_class?: string } }>(
      '/api/method/frappe.client.get_value',
      { doctype: 'Item', name: itemCode, fieldname: 'custom_risk_class' },
    )
    const rc = res?.message?.custom_risk_class
    if (rc && ['A', 'B', 'C', 'D', 'Radiation'].includes(rc)) {
      form.value.risk_class = rc as typeof form.value.risk_class
      if (rc === 'Radiation') form.value.is_radiation_device = 1
    }
  } catch { /* non-critical */ }
}

function selectItem(item: { item_code: string; is_radiation: boolean }) {
  form.value.master_item        = item.item_code
  form.value.is_radiation_device = item.is_radiation ? 1 : 0
  validateField('master_item')
  fetchItemRiskClass(item.item_code)
}

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
      <button class="hover:text-slate-600 transition-colors" @click="router.push('/dashboard')">Dashboard</button>
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
            <div class="flex gap-2">
              <div class="flex-1">
                <LinkSearch
                  v-model="form.po_reference"
                  doctype="Purchase Order"
                  placeholder="PO-2026-0041"
                  :has-error="!!fieldErrors.po_reference"
                  @select="onPoSelect"
                  @blur="validateField('po_reference')"
                />
              </div>
              <button
                type="button"
                class="btn-secondary px-3 text-sm whitespace-nowrap"
                :disabled="poLoading || !form.po_reference"
                @click="lookupPO(form.po_reference)"
              >
                <svg v-if="poLoading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                <span v-else>Tra cứu</span>
              </button>
            </div>
            <p v-if="fieldErrors.po_reference" class="mt-1 text-xs text-red-500">{{ fieldErrors.po_reference }}</p>
          </div>

          <!-- Vendor (auto-filled) -->
          <div class="form-group">
            <p class="form-label">Nhà cung cấp <span class="text-red-500">*</span></p>
            <LinkSearch
              v-model="form.vendor"
              doctype="Supplier"
              placeholder="Tự điền khi chọn PO"
              :has-error="!!fieldErrors.vendor"
              @blur="validateField('vendor')"
            />
            <p v-if="fieldErrors.vendor" class="mt-1 text-xs text-red-500">{{ fieldErrors.vendor }}</p>
          </div>

          <!-- Master Item -->
          <div class="form-group">
            <p class="form-label">Model Thiết bị <span class="text-red-500">*</span></p>
            <div v-if="poItems.length > 1" class="space-y-1.5">
              <button
                v-for="item in poItems"
                :key="item.item_code"
                type="button"
                class="w-full text-left px-3 py-2 rounded-lg border text-sm transition-colors"
                :class="form.master_item === item.item_code
                  ? 'border-brand-500 bg-brand-50 text-brand-800'
                  : 'border-slate-200 hover:border-brand-300 text-slate-700'"
                @click="selectItem(item)"
              >
                {{ item.item_code }} — {{ item.item_name }}
                <span v-if="item.is_radiation" class="text-purple-600 text-xs ml-1">(Bức xạ)</span>
              </button>
            </div>
            <LinkSearch
              v-else
              v-model="form.master_item"
              doctype="Item"
              placeholder="Mã Model thiết bị"
              :has-error="!!fieldErrors.master_item"
              @select="(i: LinkItem) => selectItem({ item_code: i.value, is_radiation: false })"
              @blur="validateField('master_item')"
            />
            <p v-if="fieldErrors.master_item" class="mt-1 text-xs text-red-500">{{ fieldErrors.master_item }}</p>
          </div>

          <!-- Clinical Dept -->
          <div class="form-group">
            <p class="form-label">Khoa / Phòng nhận <span class="text-red-500">*</span></p>
            <LinkSearch
              v-model="form.clinical_dept"
              doctype="Department"
              placeholder="ICU - M"
              :has-error="!!fieldErrors.clinical_dept"
              @blur="validateField('clinical_dept')"
            />
            <p v-if="fieldErrors.clinical_dept" class="mt-1 text-xs text-red-500">{{ fieldErrors.clinical_dept }}</p>
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
            <label for="commissioned_by" class="form-label">KTV thực hiện lắp đặt</label>
            <input
              id="commissioned_by"
              v-model="form.commissioned_by"
              type="text"
              class="form-input"
              placeholder="Tên KTV / mã nhân viên"
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
