<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import { getApprovedVes, getPpItemsForVe } from '@/api/imm03'
import type { ApprovedVE, PpItem } from '@/api/imm03'

const router = useRouter()
const route  = useRoute()
const store  = useImm03Store()

// ─── State ────────────────────────────────────────────────────────────────────

const approvedVes  = ref<ApprovedVE[]>([])
const ppItems      = ref<PpItem[]>([])
const vesLoading   = ref(false)
const ppLoading    = ref(false)
const submitting   = ref(false)
const submitResults = ref<{ name: string; item: string }[]>([])

// Selected PP items (multi-select via checkbox)
const selectedItemNames = ref<Set<string>>(new Set())

const form = ref({
  linked_evaluation:     (route.query.ve as string) ?? '',
  linked_plan:           '',
  vendor:                '',
  veRecommendedVendor:   '',
  unit_price:            null as number | null,
  delivery_terms:        '',
  payment_terms:         '',
  expected_delivery_date:'',
  warranty_period_months:null as number | null,
  waiver_reason:         '',
  incoterms:             '',
  payment_schedule_notes:'',
})

const errors  = ref<Record<string, string>>({})
const touched = ref<Record<string, boolean>>({})

// ─── Computed ─────────────────────────────────────────────────────────────────

const selectedItems = computed<PpItem[]>(() =>
  ppItems.value.filter(i => selectedItemNames.value.has(i.name)),
)

const totalAmount = computed(() =>
  selectedItems.value.reduce((sum, item) =>
    sum + item.quantity * (form.value.unit_price ?? 0), 0,
  ),
)

const requiresDirectorApproval = computed(() => totalAmount.value > 500_000_000)

const vendorChanged = computed(() =>
  !!form.value.veRecommendedVendor &&
  !!form.value.vendor &&
  form.value.vendor !== form.value.veRecommendedVendor,
)

const allSelected = computed(() =>
  ppItems.value.length > 0 &&
  ppItems.value.every(i => selectedItemNames.value.has(i.name)),
)

function formatBudget(val: number): string {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(val)
}

// ─── Validation ───────────────────────────────────────────────────────────────

function validate(): boolean {
  const e: Record<string, string> = {}
  if (!form.value.linked_evaluation)  e.linked_evaluation = 'Vui lòng chọn phiếu đánh giá NCC'
  if (selectedItemNames.value.size === 0) e.items = 'Vui lòng chọn ít nhất một hạng mục mua sắm'
  if (!form.value.vendor.trim())       e.vendor = 'Vui lòng nhập nhà cung cấp'
  if (!form.value.unit_price || form.value.unit_price <= 0) e.unit_price = 'Đơn giá phải lớn hơn 0'
  if (vendorChanged.value && !form.value.waiver_reason.trim()) {
    e.waiver_reason = 'Cần lý do miễn trừ khi chọn NCC khác với NCC đề xuất (VR-03-07)'
  }
  errors.value = e
  return Object.keys(e).length === 0
}

function touch(field: string) { touched.value[field] = true; validate() }
function fieldError(f: string): string { return touched.value[f] ? (errors.value[f] ?? '') : '' }

// ─── Select/Deselect helpers ──────────────────────────────────────────────────

function toggleItem(itemName: string) {
  const next = new Set(selectedItemNames.value)
  if (next.has(itemName)) next.delete(itemName)
  else next.add(itemName)
  selectedItemNames.value = next
  touched.value.items = true
  validate()
}

function toggleAll() {
  if (allSelected.value) {
    selectedItemNames.value = new Set()
  } else {
    selectedItemNames.value = new Set(ppItems.value.map(i => i.name))
  }
  touched.value.items = true
  validate()
}

// ─── VE selection → load PP items ─────────────────────────────────────────────

async function onVeSelect(veName: string) {
  form.value.linked_evaluation = veName
  form.value.linked_plan       = ''
  form.value.vendor            = ''
  form.value.veRecommendedVendor = ''
  form.value.unit_price        = null
  ppItems.value                = []
  selectedItemNames.value      = new Set()

  if (!veName) return
  touch('linked_evaluation')

  ppLoading.value = true
  try {
    const data = await getPpItemsForVe(veName)
    form.value.linked_plan         = data.linked_plan ?? ''
    form.value.vendor              = data.recommended_vendor ?? ''
    form.value.veRecommendedVendor = data.recommended_vendor ?? ''
    form.value.unit_price          = data.quoted_price || null
    ppItems.value                  = data.pp_items
  } catch {
    ppItems.value = []
  } finally {
    ppLoading.value = false
  }
}

// ─── Submit — one POR per selected item ───────────────────────────────────────

async function handleSubmit() {
  Object.keys(form.value).forEach(k => (touched.value[k] = true))
  touched.value.items = true
  if (!validate()) return

  submitting.value  = true
  store.error       = null
  submitResults.value = []

  const common = {
    linked_evaluation:      form.value.linked_evaluation,
    vendor:                 form.value.vendor,
    unit_price:             form.value.unit_price!,
    delivery_terms:         form.value.delivery_terms || undefined,
    payment_terms:          form.value.payment_terms || undefined,
    expected_delivery_date: form.value.expected_delivery_date || undefined,
    warranty_period_months: form.value.warranty_period_months ?? undefined,
    waiver_reason:          form.value.waiver_reason || undefined,
    incoterms:              form.value.incoterms || undefined,
    payment_schedule_notes: form.value.payment_schedule_notes || undefined,
  }

  for (const item of selectedItems.value) {
    const name = await store.createPor({
      ...common,
      linked_plan_item:      item.name,
      equipment_description: item.equipment_description,
      quantity:              item.quantity,
    })
    if (name) submitResults.value.push({ name, item: item.equipment_description })
  }

  submitting.value = false

  if (submitResults.value.length === selectedItems.value.size) {
    if (submitResults.value.length === 1) {
      router.replace(`/planning/purchase-order-requests/${submitResults.value[0].name}`)
    } else {
      router.replace('/planning/purchase-order-requests')
    }
  }
}

// ─── Load ─────────────────────────────────────────────────────────────────────

watch(() => form.value.linked_evaluation, veName => { if (veName) onVeSelect(veName) })

onMounted(async () => {
  store.error = null
  vesLoading.value = true
  try { approvedVes.value = await getApprovedVes() }
  catch { approvedVes.value = [] }
  finally { vesLoading.value = false }

  if (route.query.ve) await onVeSelect(route.query.ve as string)
})
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-03</p>
        <h1 class="text-2xl font-bold text-slate-900">Tạo Yêu cầu Mua sắm (POR)</h1>
        <p class="text-sm text-slate-500 mt-1">
          Chọn phiếu đánh giá NCC đã duyệt → chọn hạng mục → xác nhận thông tin
        </p>
      </div>
      <button class="btn-ghost shrink-0" @click="router.back()">Quay lại</button>
    </div>

    <!-- Error -->
    <div v-if="store.error" class="alert-error mb-4">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline" @click="store.error = null">Đóng</button>
    </div>

    <!-- Progress results (while submitting multiple) -->
    <div v-if="submitting && submitResults.length > 0" class="card mb-5 bg-blue-50 border border-blue-100">
      <p class="text-sm font-semibold text-blue-700 mb-2">Đang tạo POR…</p>
      <ul class="space-y-1">
        <li v-for="r in submitResults" :key="r.name" class="text-xs text-blue-700 flex items-center gap-1.5">
          <svg class="w-3 h-3 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
          </svg>
          <span class="font-mono">{{ r.name }}</span> — {{ r.item }}
        </li>
      </ul>
    </div>

    <!-- ── Section 1: Phiếu đánh giá NCC ──────────────────────────────────── -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:0ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
        Bước 1 — Chọn Phiếu đánh giá NCC
      </h2>
      <div class="form-group">
        <label class="form-label">Phiếu đánh giá NCC <span class="text-red-500">*</span></label>
        <div v-if="vesLoading" class="form-input text-slate-400 text-sm">Đang tải...</div>
        <select
          v-else
          v-model="form.linked_evaluation"
          class="form-select"
          :class="{ 'border-red-400': fieldError('linked_evaluation') }"
          @change="touch('linked_evaluation')"
        >
          <option value="">— Chọn phiếu đánh giá NCC đã phê duyệt —</option>
          <option v-for="ve in approvedVes" :key="ve.name" :value="ve.name">
            {{ ve.name }}
            {{ ve.linked_plan ? `· KH: ${ve.linked_plan}` : '' }}
            {{ ve.recommended_vendor ? `· NCC: ${ve.recommended_vendor}` : '' }}
          </option>
        </select>
        <p v-if="fieldError('linked_evaluation')" class="mt-1 text-xs text-red-500">
          {{ fieldError('linked_evaluation') }}
        </p>
        <p v-if="!vesLoading && approvedVes.length === 0" class="mt-1 text-xs text-amber-600">
          Chưa có phiếu đánh giá NCC nào được phê duyệt.
        </p>
      </div>

      <!-- Info bar -->
      <div v-if="form.linked_plan" class="mt-3 grid grid-cols-2 gap-3">
        <div class="p-3 bg-slate-50 rounded-lg border border-slate-100">
          <p class="text-xs text-slate-400 mb-0.5">Kế hoạch mua sắm</p>
          <p class="text-sm font-semibold font-mono text-brand-700">{{ form.linked_plan }}</p>
        </div>
        <div class="p-3 bg-emerald-50 rounded-lg border border-emerald-100">
          <p class="text-xs text-slate-400 mb-0.5">NCC được đề xuất</p>
          <p class="text-sm font-semibold text-emerald-700">{{ form.veRecommendedVendor || '—' }}</p>
        </div>
      </div>
    </div>

    <!-- ── Section 2: Hạng mục mua sắm (multi-select) ─────────────────────── -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:40ms">
      <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
        <h2 class="text-sm font-semibold text-slate-700">
          Bước 2 — Chọn Hạng mục từ Kế hoạch mua sắm
        </h2>
        <button
          v-if="ppItems.length > 1"
          class="text-xs text-brand-600 font-semibold hover:underline"
          @click="toggleAll"
        >
          {{ allSelected ? 'Bỏ chọn tất cả' : 'Chọn tất cả' }}
        </button>
      </div>

      <div v-if="!form.linked_evaluation" class="py-6 text-center text-sm text-slate-400 italic">
        Vui lòng chọn phiếu đánh giá NCC ở bước 1 trước.
      </div>
      <div v-else-if="ppLoading" class="py-6 text-center text-sm text-slate-400">
        Đang tải hạng mục...
      </div>
      <div v-else-if="ppItems.length === 0" class="py-6 text-center text-sm text-slate-400 italic">
        Kế hoạch mua sắm này chưa có hạng mục nào.
      </div>
      <div v-else>
        <div class="space-y-2">
          <label
            v-for="item in ppItems"
            :key="item.name"
            class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors select-none"
            :class="selectedItemNames.has(item.name)
              ? 'border-brand-400 bg-brand-50'
              : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'"
          >
            <input
              type="checkbox"
              :checked="selectedItemNames.has(item.name)"
              class="mt-0.5 accent-brand-600 shrink-0 w-4 h-4"
              @change="toggleItem(item.name)"
            />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-slate-800">{{ item.equipment_description }}</span>
                <span
                  class="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold"
                  :class="item.status === 'Pending'
                    ? 'bg-slate-100 text-slate-500'
                    : item.status === 'PO Raised'
                    ? 'bg-blue-50 text-blue-700'
                    : item.status === 'Ordered'
                    ? 'bg-amber-50 text-amber-700'
                    : 'bg-emerald-50 text-emerald-700'"
                >
                  {{ item.status === 'Pending' ? 'Chờ mua'
                   : item.status === 'PO Raised' ? 'Đã tạo POR'
                   : item.status === 'Ordered' ? 'Đã đặt hàng'
                   : item.status === 'Delivered' ? 'Đã giao'
                   : item.status ?? '—' }}
                </span>
              </div>
              <p class="text-xs text-slate-400 mt-0.5">
                Mã: <span class="font-mono text-slate-600">{{ item.name }}</span>
                · SL: <strong class="text-slate-600">{{ item.quantity }}</strong>
                <template v-if="item.por_reference">
                  · POR: <span class="font-mono text-blue-600">{{ item.por_reference }}</span>
                </template>
              </p>
              <p v-if="item.por_reference && selectedItemNames.has(item.name)"
                 class="mt-1.5 text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded-md">
                Hạng mục này đã có POR <strong>{{ item.por_reference }}</strong>. Tạo thêm sẽ sinh POR mới.
              </p>
            </div>
          </label>
        </div>

        <p v-if="fieldError('items')" class="mt-2 text-xs text-red-500">{{ fieldError('items') }}</p>

        <!-- Summary of selected -->
        <div v-if="selectedItems.length > 0"
             class="mt-4 p-3 bg-brand-50 border border-brand-100 rounded-lg flex items-center justify-between">
          <span class="text-sm font-semibold text-brand-700">
            Đã chọn {{ selectedItems.length }} hạng mục
          </span>
          <span class="text-xs text-slate-500">
            Tổng SL: {{ selectedItems.reduce((s, i) => s + i.quantity, 0) }}
          </span>
        </div>
      </div>
    </div>

    <!-- ── Section 3: NCC & Giá ─────────────────────────────────────────────── -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:80ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
        Bước 3 — Xác nhận Nhà cung cấp & Giá
      </h2>
      <p class="text-xs text-slate-400 mb-4">
        Đơn giá áp dụng cho tất cả hạng mục đã chọn. Mỗi hạng mục sẽ tạo một POR riêng.
      </p>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

        <div class="form-group sm:col-span-2">
          <label class="form-label">Nhà cung cấp <span class="text-red-500">*</span></label>
          <input
            v-model="form.vendor"
            type="text"
            class="form-input"
            :class="{ 'border-red-400': fieldError('vendor'), 'border-amber-400': vendorChanged }"
            placeholder="Mã nhà cung cấp"
            @blur="touch('vendor')"
          />
          <div v-if="vendorChanged"
               class="mt-2 flex items-start gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
            <svg class="w-4 h-4 shrink-0 text-amber-500 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>NCC khác NCC đề xuất (<strong>{{ form.veRecommendedVendor }}</strong>). Cần điền lý do miễn trừ — VR-03-07.</span>
          </div>
          <p v-if="fieldError('vendor')" class="mt-1 text-xs text-red-500">{{ fieldError('vendor') }}</p>
        </div>

        <div class="form-group">
          <label class="form-label">Đơn giá (VNĐ) <span class="text-red-500">*</span></label>
          <input
            v-model.number="form.unit_price"
            type="number"
            min="0"
            step="1000000"
            class="form-input"
            :class="{ 'border-red-400': fieldError('unit_price') }"
            placeholder="Từ báo giá VE"
            @blur="touch('unit_price')"
          />
          <p class="mt-1 text-xs text-slate-400">Tự động từ báo giá NCC trong phiếu VE — có thể điều chỉnh</p>
          <p v-if="fieldError('unit_price')" class="mt-1 text-xs text-red-500">{{ fieldError('unit_price') }}</p>
        </div>

        <div class="form-group">
          <label class="form-label">Tổng giá trị ước tính</label>
          <div class="form-input bg-slate-50 font-semibold text-slate-800 select-none cursor-default"
               :class="{ 'text-amber-700': requiresDirectorApproval }">
            {{ totalAmount > 0 ? formatBudget(totalAmount) : '—' }}
          </div>
          <div v-if="requiresDirectorApproval"
               class="mt-2 flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
            <svg class="w-4 h-4 shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>Vượt 500M — Cần phê duyệt Giám đốc</span>
          </div>
        </div>

        <div v-if="vendorChanged" class="form-group sm:col-span-2">
          <label class="form-label">
            Lý do miễn trừ <span class="text-red-500">*</span>
            <span class="text-xs font-normal text-amber-600 ml-1">(VR-03-07)</span>
          </label>
          <textarea
            v-model="form.waiver_reason"
            rows="3"
            class="form-input resize-none"
            :class="{ 'border-red-400': fieldError('waiver_reason') }"
            placeholder="Ghi rõ lý do chọn NCC khác với NCC được đề xuất từ phiếu đánh giá..."
            @blur="touch('waiver_reason')"
          />
          <p v-if="fieldError('waiver_reason')" class="mt-1 text-xs text-red-500">{{ fieldError('waiver_reason') }}</p>
        </div>
      </div>
    </div>

    <!-- ── Section 4: Điều khoản ────────────────────────────────────────────── -->
    <div class="card mb-5 animate-slide-up" style="animation-delay:120ms">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
        Điều khoản <span class="text-xs font-normal text-slate-400">(tùy chọn — áp dụng cho tất cả POR)</span>
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="form-group">
          <label class="form-label">Điều khoản giao hàng</label>
          <input v-model="form.delivery_terms" type="text" class="form-input"
                 placeholder="vd: DAP Bệnh viện, trong vòng 90 ngày" />
        </div>
        <div class="form-group">
          <label class="form-label">Incoterms</label>
          <select v-model="form.incoterms" class="form-select">
            <option value="">— Chọn Incoterms —</option>
            <option v-for="t in ['EXW','FOB','CIF','DDP','DAP','FCA']" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Điều khoản thanh toán</label>
          <input v-model="form.payment_terms" type="text" class="form-input"
                 placeholder="vd: 30% tạm ứng, 70% sau nghiệm thu" />
        </div>
        <div class="form-group">
          <label class="form-label">Ngày giao hàng dự kiến</label>
          <input v-model="form.expected_delivery_date" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Bảo hành (tháng)</label>
          <input v-model.number="form.warranty_period_months" type="number" min="0" class="form-input"
                 placeholder="vd: 24" />
        </div>
        <div class="form-group sm:col-span-2">
          <label class="form-label">Lịch thanh toán chi tiết</label>
          <textarea v-model="form.payment_schedule_notes" class="form-textarea" rows="3"
                    placeholder="Mô tả các mốc thanh toán (tùy chọn)" />
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-3 pb-8">
      <button
        class="btn-primary"
        :disabled="submitting || store.loading"
        @click="handleSubmit"
      >
        <svg v-if="submitting || store.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        <template v-if="submitting">
          Đang tạo ({{ submitResults.length }}/{{ selectedItems.length }})…
        </template>
        <template v-else>
          Tạo {{ selectedItems.length > 1 ? `${selectedItems.length} POR` : 'POR' }}
        </template>
      </button>
      <button class="btn-ghost" :disabled="submitting" @click="router.back()">Hủy</button>
    </div>

  </div>
</template>
