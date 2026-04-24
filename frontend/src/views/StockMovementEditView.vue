<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { getStockMovement, updateStockMovement, searchParts, searchReferenceDocs } from '@/api/inventory'
import type { RefDoc } from '@/api/inventory'
import type { MovementType, StockMovementItem, SparePart } from '@/types/inventory'
import SmartSelect from '@/components/common/SmartSelect.vue'

const props = defineProps<{ name: string }>()
const router = useRouter()

interface FormRow extends StockMovementItem { _key?: number; _available_qty?: number; _searchQuery?: string }

const movementType = ref<MovementType>('Receipt')
const fromWarehouse = ref('')
const toWarehouse = ref('')
const supplier = ref('')
const referenceType = ref('')
const referenceName = ref('')
const notes = ref('')
const items = ref<FormRow[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
let _keySeq = 0

const searchQuery = ref('')
const searchResults = ref<SparePart[]>([])
const searchLoading = ref(false)
const activeRowIdx = ref<number | null>(null)
const dropdownActiveIdx = ref(-1)
let _debounceTimer: ReturnType<typeof setTimeout> | null = null

// Reference doc search state
const refQuery = ref('')
const refResults = ref<RefDoc[]>([])
const refDropdownOpen = ref(false)
const refLabel = ref('')

const needsRefSearch = computed(() =>
  ['Asset Repair', 'PM Work Order', 'AC Purchase'].includes(referenceType.value)
)

watch(referenceType, () => {
  referenceName.value = ''
  refQuery.value = ''
  refResults.value = []
  refLabel.value = ''
  refDropdownOpen.value = false
})

async function onRefSearch(q: string) {
  refQuery.value = q
  refLabel.value = q
  referenceName.value = ''
  if (q.length < 2) { refResults.value = []; refDropdownOpen.value = false; return }
  try {
    refResults.value = await searchReferenceDocs(referenceType.value, q)
    refDropdownOpen.value = refResults.value.length > 0
  } catch { refResults.value = []; refDropdownOpen.value = false }
}

function pickRefDoc(r: RefDoc) {
  referenceName.value = r.name
  refLabel.value = r.label
  refResults.value = []
  refDropdownOpen.value = false
}

const totalValue = computed(() =>
  items.value.reduce((sum, it) => sum + (it.qty || 0) * (it.unit_cost || 0), 0)
)
const needsFromWarehouse = computed(() =>
  ['Issue', 'Transfer', 'Adjustment'].includes(movementType.value)
)
const needsToWarehouse = computed(() =>
  ['Receipt', 'Transfer'].includes(movementType.value)
)

async function load() {
  loading.value = true
  try {
    const doc = await getStockMovement(props.name)
    if (doc.docstatus !== 0) {
      error.value = 'Chỉ có thể sửa phiếu ở trạng thái Nháp'
      return
    }
    movementType.value = doc.movement_type as MovementType
    fromWarehouse.value = doc.from_warehouse || ''
    toWarehouse.value = doc.to_warehouse || ''
    supplier.value = doc.supplier || ''
    referenceType.value = doc.reference_type || ''
    referenceName.value = doc.reference_name || ''
    refLabel.value = doc.reference_name || ''
    notes.value = doc.notes || ''
    items.value = (doc.items || []).map(r => ({ ...r, _key: ++_keySeq }))
    if (items.value.length === 0) items.value = [{ spare_part: '', qty: 1, unit_cost: 0, _key: ++_keySeq }]
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi tải phiếu'
  } finally { loading.value = false }
}

function addRow() { items.value.push({ spare_part: '', qty: 1, unit_cost: 0, _key: ++_keySeq }) }
function removeRow(i: number) { items.value.splice(i, 1) }

async function onSearchPart(query: string, idx: number) {
  activeRowIdx.value = idx
  searchQuery.value = query
  items.value[idx]._searchQuery = query
  dropdownActiveIdx.value = -1
  if (_debounceTimer) clearTimeout(_debounceTimer)
  if (query.length < 2) { searchResults.value = []; return }
  _debounceTimer = setTimeout(async () => {
    searchLoading.value = true
    const isIssueOrTransfer = ['Issue', 'Transfer'].includes(movementType.value)
    const warehouse = isIssueOrTransfer ? fromWarehouse.value : ''
    const showStockOnly = isIssueOrTransfer ? 1 : 0
    try { searchResults.value = await searchParts(query, 10, warehouse, showStockOnly) }
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
  row._available_qty = p.available_qty
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
  row._available_qty = undefined
  row._searchQuery = ''
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

function isQtyOverStock(row: FormRow): boolean {
  if (!['Issue', 'Transfer'].includes(movementType.value)) return false
  if (row._available_qty === undefined) return false
  return (row.qty || 0) > row._available_qty
}

watch(movementType, () => { items.value.forEach(r => { r._available_qty = undefined }) })
watch(fromWarehouse, () => { items.value.forEach(r => { r._available_qty = undefined }) })

onBeforeUnmount(() => { if (_debounceTimer) clearTimeout(_debounceTimer) })

async function save() {
  error.value = ''
  if (needsFromWarehouse.value && !fromWarehouse.value) { error.value = 'Phải chọn kho xuất'; return }
  if (needsToWarehouse.value && !toWarehouse.value) { error.value = 'Phải chọn kho nhập'; return }
  if (movementType.value === 'Transfer' && fromWarehouse.value === toWarehouse.value) {
    error.value = 'Kho nguồn và kho đích phải khác nhau'; return
  }
  if (items.value.length === 0 || items.value.some(r => !r.spare_part || !r.qty)) {
    error.value = 'Phải có ít nhất 1 dòng với phụ tùng và số lượng'; return
  }
  if ((referenceType.value === 'Manual' || movementType.value === 'Adjustment') && !notes.value.trim()) {
    error.value = 'Phiếu Manual / Điều chỉnh bắt buộc phải có Ghi chú (lý do)'; return
  }
  if (needsRefSearch.value && !referenceName.value) {
    error.value = 'Phải chọn chứng từ nguồn từ danh sách'; return
  }
  saving.value = true
  try {
    await updateStockMovement(props.name, {
      movement_type: movementType.value,
      from_warehouse: fromWarehouse.value || undefined,
      to_warehouse: toWarehouse.value || undefined,
      supplier: supplier.value || undefined,
      reference_type: referenceType.value || undefined,
      reference_name: referenceName.value || undefined,
      notes: notes.value,
      items: items.value.map(r => ({
        spare_part: r.spare_part, qty: r.qty, unit_cost: r.unit_cost,
        serial_no: r.serial_no, notes: r.notes,
      })),
    })
    router.push(`/stock-movements/${props.name}`)
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi lưu phiếu'
  } finally { saving.value = false }
}

function vnd(v?: number) {
  if (!v) return '0 đ'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <button class="btn-ghost mb-4" @click="router.push(`/stock-movements/${props.name}`)">← Quay lại</button>

    <div class="mb-6">
      <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00 · Inventory</p>
      <h1 class="text-2xl font-bold text-slate-900">Sửa phiếu kho <span class="font-mono text-lg">{{ props.name }}</span></h1>
    </div>

    <div v-if="loading" class="text-center py-20 text-slate-400">Đang tải...</div>

    <template v-else>
      <div v-if="error" class="mb-4 alert-error">{{ error }}</div>

      <!-- Basic info -->
      <div class="card p-5 mb-4">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Thông tin phiếu</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="sm-edit-type" class="form-label">Loại giao dịch *</label>
            <select id="sm-edit-type" v-model="movementType" class="form-select w-full">
              <option value="Receipt">Nhập kho (Receipt)</option>
              <option value="Issue">Xuất kho (Issue)</option>
              <option value="Transfer">Chuyển kho (Transfer)</option>
              <option value="Adjustment">Điều chỉnh (Adjustment)</option>
            </select>
          </div>
          <div v-if="needsFromWarehouse">
            <label class="form-label">Kho xuất / nguồn *</label>
            <SmartSelect v-model="fromWarehouse" doctype="AC Warehouse" placeholder="Chọn kho..." />
          </div>
          <div v-if="needsToWarehouse">
            <label class="form-label">Kho nhập / đích *</label>
            <SmartSelect v-model="toWarehouse" doctype="AC Warehouse" placeholder="Chọn kho..." />
          </div>
          <div v-if="movementType === 'Receipt'">
            <label class="form-label">Nhà cung cấp</label>
            <SmartSelect v-model="supplier" doctype="AC Supplier" placeholder="Chọn nhà cung cấp..." />
          </div>
          <div>
            <label for="sm-edit-ref-type" class="form-label">Loại chứng từ</label>
            <select id="sm-edit-ref-type" v-model="referenceType" class="form-select w-full">
              <option value="">— Không —</option>
              <option value="Asset Repair">Sửa chữa (Asset Repair)</option>
              <option value="PM Work Order">Bảo trì / Hiệu chuẩn (PM Work Order)</option>
              <option value="AC Purchase">Mua hàng (Purchase)</option>
              <option value="Manual">Thủ công (Manual)</option>
            </select>
          </div>

          <!-- Asset Repair / PM Work Order / AC Purchase: searchable dropdown -->
          <div v-if="needsRefSearch" class="relative">
            <label for="sm-edit-ref-name" class="form-label">Mã chứng từ *</label>
            <input id="sm-edit-ref-name" type="text" class="form-input w-full font-mono"
                   :value="refLabel"
                   :placeholder="referenceType === 'Asset Repair' ? 'Tìm phiếu sửa chữa...'
                                : referenceType === 'AC Purchase'  ? 'Tìm đơn hàng / hóa đơn...'
                                :                                    'Tìm lệnh bảo trì / hiệu chuẩn...'"
                   @input="onRefSearch(($event.target as HTMLInputElement).value)"
                   @blur="refDropdownOpen = false" />
            <div v-if="refDropdownOpen"
                 class="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-52 overflow-y-auto z-20">
              <button v-for="r in refResults" :key="r.name"
                      class="w-full text-left px-3 py-2 hover:bg-slate-50 border-b border-slate-50 last:border-0"
                      @mousedown.prevent="pickRefDoc(r)">
                <p class="text-sm font-medium font-mono">{{ r.name }}</p>
                <p class="text-[11px] text-slate-400">{{ r.label }}</p>
                <p v-if="r.description" class="text-[10px] text-slate-300">{{ r.description }}</p>
              </button>
            </div>
            <p v-if="referenceName" class="text-[10px] text-emerald-600 mt-0.5">Đã chọn: {{ referenceName }}</p>
          </div>

          <!-- Manual: no reference_name; notes required -->
          <div v-else-if="referenceType === 'Manual'" class="flex items-center">
            <p class="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 w-full">
              Phiếu thủ công — bắt buộc điền Ghi chú (lý do) bên dưới
            </p>
          </div>
        </div>
      </div>

      <!-- Items -->
      <div class="card p-5 mb-4">
        <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
          <h2 class="text-sm font-semibold text-slate-700">Chi tiết phụ tùng</h2>
          <button class="btn-secondary text-xs" @click="addRow">+ Thêm dòng</button>
        </div>
        <div class="space-y-3">
          <div v-for="(row, idx) in items" :key="row._key"
               class="grid grid-cols-12 gap-2 items-start p-3 rounded-lg border transition-colors"
               :class="row.spare_part ? 'bg-white border-slate-200' : 'bg-slate-50 border-dashed border-slate-200'">

            <!-- Part picker -->
            <div class="col-span-12 md:col-span-5 relative">
              <p class="text-[10px] text-slate-500 mb-1">Phụ tùng *</p>

              <!-- Chip: part selected -->
              <div v-if="row.spare_part"
                   class="flex items-start gap-2 px-2.5 py-2 bg-slate-50 rounded-lg border border-slate-200">
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-800 truncate">{{ row.part_name }}</p>
                  <div class="flex items-center gap-2 mt-0.5 flex-wrap">
                    <span class="text-[11px] font-mono text-slate-400">{{ row.spare_part }}</span>
                    <span v-if="['Issue', 'Transfer'].includes(movementType) && row._available_qty !== undefined"
                          class="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                          :class="row._available_qty > 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'">
                      Tồn: {{ row._available_qty }} {{ row.uom }}
                    </span>
                  </div>
                </div>
                <button type="button"
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
                <input type="text" class="form-input w-full text-sm pr-8"
                       placeholder="Gõ tên hoặc mã phụ tùng..."
                       @input="onSearchPart(($event.target as HTMLInputElement).value, idx)"
                       @focus="activeRowIdx = idx; dropdownActiveIdx = -1"
                       @blur="onPartBlur"
                       @keydown="onPartKeydown" />
                <span class="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                  <svg v-if="searchLoading && activeRowIdx === idx"
                       class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </span>
              </div>

              <!-- Dropdown -->
              <div v-if="activeRowIdx === idx && searchResults.length > 0"
                   class="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-52 overflow-y-auto z-20">
                <button v-for="(p, pi) in searchResults" :key="p.name"
                        class="w-full text-left px-3 py-2.5 border-b border-slate-50 last:border-0 transition-colors"
                        :class="dropdownActiveIdx === pi ? 'bg-blue-50' : 'hover:bg-slate-50'"
                        @mousedown.prevent="pickPart(p)"
                        @mouseenter="dropdownActiveIdx = pi">
                  <p class="text-sm font-medium text-slate-800">{{ p.part_name }}</p>
                  <div class="flex items-center gap-2 mt-0.5 flex-wrap">
                    <span class="text-[10px] font-mono text-slate-400">{{ p.part_code || p.name }}</span>
                    <span class="text-[10px] text-slate-400">{{ vnd(p.unit_cost) }}</span>
                    <span v-if="p.available_qty !== undefined"
                          class="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                          :class="(p.available_qty ?? 0) > 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'">
                      Tồn: {{ p.available_qty }} {{ p.stock_uom }}
                    </span>
                  </div>
                </button>
              </div>

              <!-- No results -->
              <div v-else-if="activeRowIdx === idx && !searchLoading && (row._searchQuery?.length ?? 0) >= 2 && !row.spare_part"
                   class="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-sm px-3 py-2.5 text-sm text-slate-400 z-20">
                Không tìm thấy phụ tùng nào
              </div>
            </div>

            <!-- Qty -->
            <div class="col-span-4 md:col-span-2">
              <label class="text-[10px] text-slate-500 mb-1 block">Số lượng *</label>
              <input v-model.number="row.qty" type="number" :min="movementType === 'Adjustment' ? undefined : 0.01"
                     step="0.01" class="form-input w-full text-sm"
                     :class="isQtyOverStock(row) ? 'border-red-400 focus:ring-red-200' : ''" />
              <p v-if="isQtyOverStock(row)" class="text-[10px] text-red-500 mt-0.5">
                Vượt tồn ({{ row._available_qty }})
              </p>
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
              <label class="text-[10px] text-slate-500 mb-1 block">Đơn giá</label>
              <input v-model.number="row.unit_cost" type="number" min="0" step="1000"
                     class="form-input w-full text-sm" />
            </div>

            <!-- Remove -->
            <div class="col-span-12 md:col-span-1 flex items-end pb-0.5">
              <button class="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                      :disabled="items.length === 1"
                      @click="removeRow(idx)">✕</button>
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
        <label for="sm-edit-notes" class="form-label">Ghi chú</label>
        <textarea id="sm-edit-notes" v-model="notes" rows="3" class="form-input w-full"
                  placeholder="Mô tả nghiệp vụ phát sinh..." />
      </div>

      <!-- Actions -->
      <div class="flex gap-3 justify-end">
        <button class="btn-ghost" @click="router.push(`/stock-movements/${props.name}`)">Huỷ</button>
        <button class="btn-primary" :disabled="saving" @click="save">
          {{ saving ? 'Đang lưu...' : 'Lưu thay đổi' }}
        </button>
      </div>
    </template>
  </div>
</template>
