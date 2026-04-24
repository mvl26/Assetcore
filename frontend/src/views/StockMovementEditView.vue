<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStockMovement, updateStockMovement, searchParts } from '@/api/inventory'
import type { MovementType, StockMovementItem, SparePart } from '@/types/inventory'
import SmartSelect from '@/components/common/SmartSelect.vue'

const props = defineProps<{ name: string }>()
const router = useRouter()

interface FormRow extends StockMovementItem { _key?: number }

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
const activeRowIdx = ref<number | null>(null)

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
  if (query.length < 2) { searchResults.value = []; return }
  try { searchResults.value = await searchParts(query, 10) }
  catch { searchResults.value = [] }
}

function pickPart(p: SparePart) {
  if (activeRowIdx.value == null) return
  const row = items.value[activeRowIdx.value]
  row.spare_part = p.name
  row.part_name = p.part_name
  row.uom = p.uom
  row.unit_cost = p.unit_cost || 0
  searchResults.value = []
  searchQuery.value = ''
  activeRowIdx.value = null
}

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
            <SmartSelect v-model="supplier" doctype="AC Supplier" placeholder="Chọn NCC..." />
          </div>
          <div>
            <label for="sm-edit-ref-type" class="form-label">Loại chứng từ</label>
            <select id="sm-edit-ref-type" v-model="referenceType" class="form-select w-full">
              <option value="">— Không —</option>
              <option value="Asset Repair">Asset Repair</option>
              <option value="PM Work Order">PM Work Order</option>
              <option value="Purchase">Purchase</option>
              <option value="Manual">Manual</option>
            </select>
          </div>
          <div>
            <label for="sm-edit-ref-name" class="form-label">Mã chứng từ</label>
            <input id="sm-edit-ref-name" v-model="referenceName" type="text" class="form-input w-full font-mono"
                   placeholder="Nhập mã chứng từ nguồn..." />
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
               class="grid grid-cols-12 gap-2 items-start p-3 bg-slate-50 rounded-lg">
            <div class="col-span-12 md:col-span-5 relative">
              <label class="text-[10px] text-slate-500 mb-1 block">Phụ tùng</label>
              <input type="text"
                     :value="row.part_name || row.spare_part"
                     class="form-input w-full text-sm"
                     placeholder="Gõ để tìm..."
                     @input="onSearchPart(($event.target as HTMLInputElement).value, idx)"
                     @focus="activeRowIdx = idx" />
              <div v-if="activeRowIdx === idx && searchResults.length > 0"
                   class="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-y-auto z-20">
                <button v-for="p in searchResults" :key="p.name"
                        class="w-full text-left px-3 py-2 hover:bg-slate-50 border-b border-slate-50 last:border-0"
                        @click="pickPart(p)">
                  <p class="text-sm font-medium">{{ p.part_name }}</p>
                  <p class="text-[10px] text-slate-400 font-mono">{{ p.part_code || p.name }} · {{ vnd(p.unit_cost) }}</p>
                </button>
              </div>
            </div>
            <div class="col-span-4 md:col-span-2">
              <label class="text-[10px] text-slate-500 mb-1 block">Số lượng</label>
              <input v-model.number="row.qty" type="number" :min="movementType === 'Adjustment' ? undefined : 0.01"
                     step="0.01" class="form-input w-full text-sm" />
            </div>
            <div class="col-span-4 md:col-span-2">
              <label class="text-[10px] text-slate-500 mb-1 block">ĐVT</label>
              <input :value="row.uom" readonly class="form-input w-full text-sm bg-slate-100" />
            </div>
            <div class="col-span-4 md:col-span-2">
              <label class="text-[10px] text-slate-500 mb-1 block">Đơn giá</label>
              <input v-model.number="row.unit_cost" type="number" min="0" step="1000"
                     class="form-input w-full text-sm" />
            </div>
            <div class="col-span-12 md:col-span-1 flex items-end">
              <button class="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
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
