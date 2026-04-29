<script setup lang="ts">
import DateTimeInput from '@/components/common/DateTimeInput.vue'
import DateInput from '@/components/common/DateInput.vue'
// Copyright (c) 2026, AssetCore Team
import { ref, computed, onBeforeUnmount, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { createPurchase } from '@/api/purchase'
import type { PurchaseItem, CreatePurchaseDevicePayload } from '@/api/purchase'
import { searchParts } from '@/api/inventory'
import type { SparePart } from '@/types/inventory'
import SmartSelect from '@/components/common/SmartSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useFieldsDraft } from '@/composables/useFormDraft'

const router = useRouter()

function nowLocalISO() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

const supplier = ref('')
const purchaseDate = ref(nowLocalISO())
const invoiceNo = ref('')
const expectedDelivery = ref('')
const notes = ref('')
const items = ref<PurchaseItem[]>([])
const devices = ref<CreatePurchaseDevicePayload[]>([])
const saving = ref(false)
const error = ref('')

const { clear: clearDraft } = useFieldsDraft('purchase-create', {
  supplier: supplier as Ref<unknown>,
  purchaseDate: purchaseDate as Ref<unknown>,
  invoiceNo: invoiceNo as Ref<unknown>,
  expectedDelivery: expectedDelivery as Ref<unknown>,
  notes: notes as Ref<unknown>,
  items: items as Ref<unknown>,
  devices: devices as Ref<unknown>,
})

function makeDevice(model = '', cost = 0): CreatePurchaseDevicePayload {
  return {
    device_model: model, unit_cost: cost,
    vendor_serial_no: '', warranty_months: 12, notes: '',
  }
}
function addDevice() { devices.value.push(makeDevice()) }
function removeDevice(i: number) { devices.value.splice(i, 1) }

// Quick-add N units of same model
const quickModel = ref('')
const quickCount = ref(1)
const quickCost  = ref(0)
function quickAddDevices() {
  if (!quickModel.value || quickCount.value < 1) return
  const n = Math.min(Math.max(1, Math.floor(quickCount.value)), 50)
  for (let i = 0; i < n; i++) devices.value.push(makeDevice(quickModel.value, quickCost.value))
  quickModel.value = ''
  quickCount.value = 1
  quickCost.value = 0
}

const deviceTotal = computed(() =>
  devices.value.reduce((s, d) => s + (d.unit_cost || 0), 0),
)

// Part search state
const searchQuery = ref('')
const searchResults = ref<SparePart[]>([])
const searchLoading = ref(false)
const activeRowIdx = ref<number | null>(null)
const dropdownActiveIdx = ref(-1)
let _debounceTimer: ReturnType<typeof setTimeout> | null = null

const totalValue = computed(() =>
  items.value.reduce((sum, r) => sum + (r.qty || 0) * (r.unit_cost || 0), 0)
)

function addRow() { items.value.push({ spare_part: '', qty: 1, unit_cost: 0 }) }
function removeRow(i: number) { items.value.splice(i, 1) }

async function onSearchPart(query: string, idx: number) {
  activeRowIdx.value = idx
  searchQuery.value = query
  dropdownActiveIdx.value = -1
  if (_debounceTimer) clearTimeout(_debounceTimer)
  if (query.length < 2) { searchResults.value = []; return }
  _debounceTimer = setTimeout(async () => {
    searchLoading.value = true
    try { searchResults.value = await searchParts(query, 10) }
    catch { searchResults.value = [] }
    finally { searchLoading.value = false }
  }, 250)
}

function pickPart(p: SparePart) {
  if (activeRowIdx.value == null) return
  const row = items.value[activeRowIdx.value]
  row.spare_part = p.name
  row.part_name = p.part_name
  row.uom = p.stock_uom
  row.unit_cost = p.unit_cost || 0
  searchResults.value = []
  searchQuery.value = ''
  activeRowIdx.value = null
  dropdownActiveIdx.value = -1
}

function clearPart(idx: number) {
  const row = items.value[idx]
  row.spare_part = ''
  row.part_name = undefined
  row.uom = undefined
  row.unit_cost = 0
  searchResults.value = []
  searchQuery.value = ''
  activeRowIdx.value = idx
}

function onPartBlur() {
  setTimeout(() => {
    activeRowIdx.value = null
    searchResults.value = []
    dropdownActiveIdx.value = -1
  }, 200)
}

function onPartKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    dropdownActiveIdx.value = Math.min(dropdownActiveIdx.value + 1, searchResults.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    dropdownActiveIdx.value = Math.max(dropdownActiveIdx.value - 1, 0)
  } else if (e.key === 'Enter' && dropdownActiveIdx.value >= 0) {
    e.preventDefault()
    pickPart(searchResults.value[dropdownActiveIdx.value])
  } else if (e.key === 'Escape') {
    searchResults.value = []
    activeRowIdx.value = null
  }
}

onBeforeUnmount(() => { if (_debounceTimer) clearTimeout(_debounceTimer) })

async function submit(autoSubmit: boolean) {
  error.value = ''
  if (!supplier.value) { error.value = 'Phải chọn nhà cung cấp'; return }
  const validItems = items.value.filter(r => r.spare_part && r.qty)
  const validDevices = devices.value.filter(d => d.device_model)
  if (!validItems.length && !validDevices.length) {
    error.value = 'Phải có ít nhất 1 thiết bị hoặc 1 phụ tùng'; return
  }
  if (items.value.some(r => r.spare_part && !r.qty)) {
    error.value = 'Dòng phụ tùng thiếu số lượng'; return
  }
  saving.value = true
  try {
    const res = await createPurchase({
      supplier: supplier.value,
      purchase_date: purchaseDate.value ? purchaseDate.value.replace('T', ' ') + ':00' : undefined,
      invoice_no: invoiceNo.value || undefined,
      expected_delivery: expectedDelivery.value || undefined,
      notes: notes.value || undefined,
      items: validItems.map(r => ({ spare_part: r.spare_part, qty: r.qty, unit_cost: r.unit_cost })),
      devices: validDevices,
      auto_submit: autoSubmit ? 1 : 0,
    })
    clearDraft()
    router.push(`/purchases/${res.name}`)
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi tạo đơn hàng'
  } finally { saving.value = false }
}

function vnd(v?: number) {
  if (!v) return '0 đ'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      back-to="/purchases"
      title="Tạo đơn mua hàng"
      :breadcrumb="[
        { label: 'Đơn mua hàng', to: '/purchases' },
        { label: 'Tạo mới' },
      ]"
    />

    <div class="mb-6">
      <p class="text-xs text-slate-500 mt-1">
        PO có thể chứa <b>thiết bị y tế</b> (→ phiếu tiếp nhận) <b>hoặc</b> <b>phụ tùng</b> (→ phiếu nhập kho) — không bắt buộc cả hai.
      </p>
      <p class="text-[11px] text-slate-400 mt-0.5 italic">
        Phân công khoa/phòng ban cho từng máy được thực hiện ở bước tạo Asset, không cần khai trên PO.
      </p>
    </div>

    <div v-if="error" class="mb-4 alert-error">{{ error }}</div>

    <!-- Basic info -->
    <div class="card p-5 mb-4">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Thông tin đơn hàng</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label for="pur-supplier" class="form-label">Nhà cung cấp *</label>
          <SmartSelect id="pur-supplier" v-model="supplier" doctype="AC Supplier" placeholder="Chọn nhà cung cấp..." />
        </div>
        <div>
          <label for="pur-date" class="form-label">Ngày đặt hàng *</label>
          <DateTimeInput id="pur-date" v-model="purchaseDate" class="form-input w-full" />
        </div>
        <div>
          <label for="pur-invoice" class="form-label">Số hóa đơn / Mã PO</label>
          <input
id="pur-invoice" v-model="invoiceNo" type="text" class="form-input w-full font-mono"
                 placeholder="VD: INV-2026-0001, PO-00123" />
        </div>
        <div>
          <label for="pur-delivery" class="form-label">Ngày giao hàng dự kiến</label>
          <DateInput id="pur-delivery" v-model="expectedDelivery" class="form-input w-full" />
        </div>
      </div>
    </div>

    <!-- Devices (thiết bị y tế) -->
    <div class="card p-5 mb-4">
      <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
        <div>
          <h2 class="text-sm font-semibold text-slate-700">Thiết bị y tế</h2>
          <p class="text-xs text-slate-400 mt-0.5">Mỗi dòng sẽ được tạo 1 phiếu tiếp nhận sau khi nhập kho.</p>
        </div>
        <button class="btn-secondary text-xs" @click="addDevice">+ Thêm thiết bị</button>
      </div>

      <!-- Quick-add N units of same model -->
      <div class="mb-4 p-3 rounded-lg border border-dashed border-indigo-200 bg-indigo-50/40">
        <p class="text-xs font-semibold text-indigo-800 mb-2">Thêm nhanh nhiều máy cùng model</p>
        <div class="grid grid-cols-12 gap-2 items-end">
          <div class="col-span-12 md:col-span-5">
            <p class="text-[10px] text-slate-500 mb-1">Model thiết bị</p>
            <SmartSelect v-model="quickModel" doctype="IMM Device Model" placeholder="Chọn model..." />
          </div>
          <div class="col-span-4 md:col-span-2">
            <label for="qa-count" class="text-[10px] text-slate-500 mb-1 block">Số máy (1–50)</label>
            <input
id="qa-count" v-model.number="quickCount" type="number" min="1" max="50" step="1"
                   class="form-input w-full text-sm" />
          </div>
          <div class="col-span-4 md:col-span-3">
            <label for="qa-cost" class="text-[10px] text-slate-500 mb-1 block">Đơn giá / máy</label>
            <input
id="qa-cost" v-model.number="quickCost" type="number" min="0" step="1000"
                   class="form-input w-full text-sm" />
          </div>
          <div class="col-span-4 md:col-span-2">
            <button
              class="w-full text-xs px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!quickModel || quickCount < 1"
              @click="quickAddDevices"
            >
+ Thêm {{ quickCount }} máy
</button>
          </div>
        </div>
        <p class="text-[10px] text-indigo-600 mt-2 italic">
          Mỗi máy là 1 thực thể riêng: 1 Asset, 1 Serial, 1 Phiếu tiếp nhận.
        </p>
      </div>

      <div v-if="!devices.length" class="text-center py-6 text-sm text-slate-400 italic">
        Chưa có thiết bị. Dùng "Thêm nhanh" ở trên hoặc bấm "+ Thêm thiết bị".
      </div>

      <div v-else class="space-y-3">
        <div
v-for="(d, idx) in devices" :key="idx"
             class="grid grid-cols-12 gap-2 items-start p-3 rounded-lg border border-slate-200 bg-white">
          <div class="col-span-12 md:col-span-1 flex items-center">
            <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold font-mono">
              #{{ idx + 1 }}
            </span>
          </div>
          <div class="col-span-12 md:col-span-5">
            <p class="text-[10px] text-slate-500 mb-1">Model thiết bị *</p>
            <SmartSelect v-model="d.device_model" doctype="IMM Device Model" placeholder="Chọn model..." />
          </div>
          <div class="col-span-6 md:col-span-2">
            <label :for="`dev-cost-${idx}`" class="text-[10px] text-slate-500 mb-1 block">Đơn giá</label>
            <input
:id="`dev-cost-${idx}`" v-model.number="d.unit_cost" type="number" min="0" step="1000"
                   class="form-input w-full text-sm" />
          </div>
          <div class="col-span-5 md:col-span-3">
            <label :for="`dev-wm-${idx}`" class="text-[10px] text-slate-500 mb-1 block">BH (tháng)</label>
            <input
:id="`dev-wm-${idx}`" v-model.number="d.warranty_months" type="number" min="0" step="1"
                   class="form-input w-full text-sm" />
          </div>
          <div class="col-span-1 flex items-end pb-0.5 justify-end">
            <button
class="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                    title="Xóa máy này"
                    @click="removeDevice(idx)">
✕
</button>
          </div>
          <div class="col-span-12">
            <label :for="`dev-sn-${idx}`" class="text-[10px] text-slate-500 mb-1 block">Serial Number Hãng (máy #{{ idx + 1 }})</label>
            <input
:id="`dev-sn-${idx}`" v-model="d.vendor_serial_no" type="text"
                   class="form-input w-full text-sm font-mono" placeholder="Có thể bỏ trống, điền khi tiếp nhận" />
          </div>
        </div>

        <div class="flex justify-between items-center text-sm pt-2 border-t border-slate-100">
          <span class="text-xs text-slate-500">
            Tổng: <b class="text-slate-800">{{ devices.length }}</b> máy
          </span>
          <span>
            <span class="text-slate-500 mr-2">Tổng giá trị:</span>
            <span class="font-bold text-emerald-700">{{ vnd(deviceTotal) }}</span>
          </span>
        </div>
      </div>
    </div>

    <!-- Items (phụ tùng) -->
    <div class="card p-5 mb-4">
      <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
        <div>
          <h2 class="text-sm font-semibold text-slate-700">Phụ tùng</h2>
          <p class="text-[11px] text-slate-400 mt-0.5">Nhập kho qua phiếu nhập kho sau khi duyệt PO.</p>
        </div>
        <button class="btn-secondary text-xs" @click="addRow">+ Thêm phụ tùng</button>
      </div>

      <div v-if="!items.length" class="text-center py-6 text-sm text-slate-400 italic">
        Chưa có phụ tùng. Bấm "+ Thêm phụ tùng" nếu đơn hàng có phụ tùng.
      </div>

      <div v-else class="space-y-3">
        <div
v-for="(row, idx) in items" :key="idx"
             class="grid grid-cols-12 gap-2 items-start p-3 rounded-lg border transition-colors"
             :class="row.spare_part ? 'bg-white border-slate-200' : 'bg-slate-50 border-dashed border-slate-200'">
<!-- Part picker -->
          <div class="col-span-12 md:col-span-5 relative">
            <p class="text-[10px] text-slate-500 mb-1">Phụ tùng *</p>

            <!-- Chip: selected -->
            <div
v-if="row.spare_part"
                 class="flex items-start gap-2 px-2.5 py-2 bg-slate-50 rounded-lg border border-slate-200">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-slate-800 truncate">{{ row.part_name }}</p>
                <span class="text-[11px] font-mono text-slate-400">{{ row.spare_part }}</span>
              </div>
              <button
type="button"
                      class="shrink-0 p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
                      title="Xóa chọn"
                      @click="clearPart(idx)">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Input: searching -->
            <div v-else class="relative">
              <input
:id="`pur-part-${idx}`" type="text"
                     class="form-input w-full text-sm pr-8"
                     placeholder="Gõ tên hoặc mã phụ tùng..."
                     @input="onSearchPart(($event.target as HTMLInputElement).value, idx)"
                     @focus="activeRowIdx = idx; dropdownActiveIdx = -1"
                     @blur="onPartBlur"
                     @keydown="onPartKeydown" />
              <span class="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                <svg
v-if="searchLoading && activeRowIdx === idx"
                     class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </span>
            </div>

            <!-- Dropdown -->
            <div
v-if="activeRowIdx === idx && searchResults.length > 0"
                 class="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-52 overflow-y-auto z-20">
              <button
v-for="(p, pi) in searchResults" :key="p.name"
                      class="w-full text-left px-3 py-2.5 border-b border-slate-50 last:border-0 transition-colors"
                      :class="dropdownActiveIdx === pi ? 'bg-blue-50' : 'hover:bg-slate-50'"
                      @mousedown.prevent="pickPart(p)"
                      @mouseenter="dropdownActiveIdx = pi">
                <p class="text-sm font-medium text-slate-800">{{ p.part_name }}</p>
                <div class="flex items-center gap-2 mt-0.5">
                  <span class="text-[10px] font-mono text-slate-400">{{ p.part_code || p.name }}</span>
                  <span class="text-[10px] text-slate-400">{{ vnd(p.unit_cost) }}</span>
                </div>
              </button>
            </div>

            <!-- No results -->
            <div
v-else-if="activeRowIdx === idx && !searchLoading && searchQuery.length >= 2 && !row.spare_part"
                 class="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-sm px-3 py-2.5 text-sm text-slate-400 z-20">
              Không tìm thấy phụ tùng nào
            </div>
          </div>

          <!-- Qty -->
          <div class="col-span-4 md:col-span-2">
            <label :for="`pur-qty-${idx}`" class="text-[10px] text-slate-500 mb-1 block">Số lượng *</label>
            <input
:id="`pur-qty-${idx}`" v-model.number="row.qty" type="number" min="0.01"
                   step="0.01" class="form-input w-full text-sm" />
          </div>

          <!-- UOM badge -->
          <div class="col-span-4 md:col-span-2">
            <p class="text-[10px] text-slate-500 mb-1">ĐVT</p>
            <div class="flex items-center h-9 px-2.5 rounded-lg bg-slate-100 border border-slate-200 text-sm text-slate-600">
              {{ row.uom || '—' }}
            </div>
          </div>

          <!-- Unit cost -->
          <div class="col-span-4 md:col-span-2">
            <label :for="`pur-cost-${idx}`" class="text-[10px] text-slate-500 mb-1 block">Đơn giá</label>
            <input
:id="`pur-cost-${idx}`" v-model.number="row.unit_cost" type="number" min="0" step="1000"
                   class="form-input w-full text-sm" />
          </div>

          <!-- Remove -->
          <div class="col-span-12 md:col-span-1 flex items-end pb-0.5">
            <button
class="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                    :disabled="items.length === 1"
                    @click="removeRow(idx)">
✕
</button>
          </div>
        </div>
      </div>

      <div class="mt-4 flex justify-end text-sm">
        <span class="text-slate-500 mr-2">Tổng giá trị:</span>
        <span class="font-bold text-lg text-emerald-700">{{ vnd(totalValue) }}</span>
      </div>
    </div>

    <!-- Notes -->
    <div class="card p-5 mb-4">
      <label for="pur-notes" class="form-label">Ghi chú</label>
      <textarea
id="pur-notes" v-model="notes" rows="3" class="form-input w-full"
                placeholder="Mô tả đơn hàng, điều khoản, yêu cầu đặc biệt..." />
    </div>

    <!-- Actions -->
    <div class="flex gap-3 justify-end">
      <button class="btn-ghost" @click="router.push('/purchases')">Huỷ</button>
      <button class="btn-secondary" :disabled="saving" @click="submit(false)">
        {{ saving ? 'Đang lưu...' : 'Lưu nháp' }}
      </button>
      <button class="btn-primary" :disabled="saving" @click="submit(true)">
        {{ saving ? 'Đang duyệt...' : 'Lưu & Duyệt' }}
      </button>
    </div>
  </div>
</template>
