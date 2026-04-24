<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// UOM management: 3 tabs — Master (CRUD), Parts & UOM (assign), Conversions (per-part)
import { ref, computed, onMounted } from 'vue'
import {
  listUomsFull, createUom, updateUom, deleteUom, seedAcUoms,
  listPartsUom, listPartsMissingUom, updatePartUom, bulkAssignDefaultUom,
  getUomInfo, upsertUomConversion, removeUomConversion,
  type AcUom, type PartUomRow, type PartMissingUom, type UomInfo,
} from '@/api/inventory'

type Tab = 'master' | 'parts' | 'conversions'
const tab = ref<Tab>('master')
const toast = ref(''); const toastError = ref(false)
function showToast(msg: string, err = false) {
  toast.value = msg; toastError.value = err
  setTimeout(() => { toast.value = '' }, 3500)
}

// ─── Tab 1: Master ───────────────────────────────────────────────────────────
const uoms = ref<AcUom[]>([])
const uomSearch = ref('')
const uomLoading = ref(false)
const showUomForm = ref(false)
const uomEditing = ref<string | null>(null)
const uomForm = ref<Partial<AcUom>>({ uom_name: '', symbol: '', must_be_whole_number: 0, is_active: 1, description: '' })

async function loadUoms() {
  uomLoading.value = true
  try { uoms.value = (await listUomsFull({ search: uomSearch.value, limit: 200 })).items }
  finally { uomLoading.value = false }
}

function openCreateUom() {
  uomEditing.value = null
  uomForm.value = { uom_name: '', symbol: '', must_be_whole_number: 0, is_active: 1, description: '' }
  showUomForm.value = true
}
function openEditUom(u: AcUom) {
  uomEditing.value = u.name
  uomForm.value = { ...u }
  showUomForm.value = true
}
async function saveUom() {
  if (!uomForm.value.uom_name?.trim()) { showToast('Tên đơn vị là bắt buộc', true); return }
  try {
    if (uomEditing.value) await updateUom(uomEditing.value, uomForm.value)
    else                  await createUom(uomForm.value)
    showUomForm.value = false
    showToast(uomEditing.value ? 'Đã cập nhật' : 'Đã tạo')
    await loadUoms()
  } catch (e: unknown) { showToast((e as Error).message || 'Lỗi lưu', true) }
}
async function removeUom(name: string) {
  if (!confirm(`Xóa đơn vị "${name}"?\nNếu đang được dùng sẽ chỉ deactivate.`)) return
  try {
    const res = await deleteUom(name)
    showToast(res.soft_deleted ? `Đã deactivate — ${res.reason}` : 'Đã xóa')
    await loadUoms()
  } catch (e: unknown) { showToast((e as Error).message || 'Lỗi xóa', true) }
}
async function doSeed() {
  if (!confirm('Tạo danh mục UOM chuẩn y tế Việt Nam (bỏ qua các UOM đã có)?')) return
  try {
    const res = await seedAcUoms()
    showToast(`Đã tạo ${res.count} UOM mới`)
    await loadUoms()
  } catch (e: unknown) { showToast((e as Error).message || 'Lỗi seed', true) }
}

// ─── Tab 2: Parts & UOM ──────────────────────────────────────────────────────
const parts = ref<PartUomRow[]>([])
const partsMissing = ref<PartMissingUom[]>([])
const partsSearch = ref('')
const partsLoading = ref(false)
const editingPart = ref<string | null>(null)
const editStockUom = ref('')
const editPurchaseUom = ref('')
const defaultUomForBulk = ref('Cái')

async function loadParts() {
  partsLoading.value = true
  try {
    const [p, m] = await Promise.all([
      listPartsUom(partsSearch.value, 300),
      listPartsMissingUom(500),
    ])
    parts.value = p.items
    partsMissing.value = m.items
  } finally { partsLoading.value = false }
}

function openEditPart(p: PartUomRow) {
  editingPart.value = p.name
  editStockUom.value = p.stock_uom || ''
  editPurchaseUom.value = p.purchase_uom || ''
}

async function savePartUom() {
  if (!editingPart.value) return
  try {
    await updatePartUom(editingPart.value, editStockUom.value, editPurchaseUom.value)
    showToast('Đã cập nhật ĐVT cho phụ tùng')
    editingPart.value = null
    await loadParts()
  } catch (e: unknown) { showToast((e as Error).message || 'Lỗi', true) }
}

async function doBulkAssign() {
  if (!defaultUomForBulk.value) { showToast('Chọn UOM default', true); return }
  if (!confirm(`Gán "${defaultUomForBulk.value}" cho ${partsMissing.value.length} phụ tùng thiếu ĐVT?`)) return
  try {
    const res = await bulkAssignDefaultUom(defaultUomForBulk.value)
    showToast(`Đã gán cho ${res.assigned} phụ tùng`)
    await loadParts()
  } catch (e: unknown) { showToast((e as Error).message || 'Lỗi', true) }
}

// ─── Tab 3: Conversions ──────────────────────────────────────────────────────
const convPart = ref<string>('')
const convInfo = ref<UomInfo | null>(null)
const convLoading = ref(false)
const newConv = ref({ uom: '', conversion_factor: 1, is_purchase_uom: 0 as 0 | 1, is_issue_uom: 0 as 0 | 1 })

async function loadConvForPart() {
  if (!convPart.value) { convInfo.value = null; return }
  convLoading.value = true
  try { convInfo.value = await getUomInfo(convPart.value) }
  catch { convInfo.value = null }
  finally { convLoading.value = false }
}

async function addConversion() {
  if (!convPart.value || !newConv.value.uom) { showToast('Chọn phụ tùng + UOM', true); return }
  if (newConv.value.conversion_factor <= 0) { showToast('Hệ số phải > 0', true); return }
  try {
    await upsertUomConversion({
      spare_part: convPart.value,
      uom: newConv.value.uom,
      conversion_factor: newConv.value.conversion_factor,
      is_purchase_uom: newConv.value.is_purchase_uom,
      is_issue_uom: newConv.value.is_issue_uom,
    })
    showToast('Đã lưu quy đổi')
    newConv.value = { uom: '', conversion_factor: 1, is_purchase_uom: 0, is_issue_uom: 0 }
    await loadConvForPart()
  } catch (e: unknown) { showToast((e as Error).message || 'Lỗi', true) }
}

async function deleteConversion(uom: string) {
  if (!convPart.value || !confirm(`Xóa quy đổi "${uom}"?`)) return
  try {
    await removeUomConversion(convPart.value, uom)
    showToast('Đã xóa')
    await loadConvForPart()
  } catch (e: unknown) { showToast((e as Error).message || 'Lỗi', true) }
}

// ─── Init ────────────────────────────────────────────────────────────────────
onMounted(() => {
  loadUoms()
  loadParts()
})

const activeUoms = computed(() => uoms.value.filter(u => u.is_active))
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="mb-5">
      <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00 · Đơn vị tính</p>
      <h1 class="text-2xl font-bold text-slate-900">Quản lý Đơn vị tính (UOM)</h1>
      <p class="text-sm text-slate-500 mt-1">Tạo/sửa ĐVT, gán cho phụ tùng, và thiết lập bảng quy đổi.</p>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="mb-4 px-4 py-2.5 rounded-lg text-sm"
         :class="toastError ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">
      {{ toast }}
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-4 border-b border-slate-200">
      <button
        v-for="t in (['master', 'parts', 'conversions'] as const)"
        :key="t"
        class="px-4 py-2 text-sm font-medium transition-colors"
        :class="tab === t ? 'text-blue-600 border-b-2 border-blue-600 -mb-px' : 'text-slate-500 hover:text-slate-800'"
        @click="tab = t"
      >
        {{ { master: 'Đơn vị tính (Master)', parts: `Phụ tùng & ĐVT ${partsMissing.length ? `(${partsMissing.length} thiếu)` : ''}`, conversions: 'Bảng quy đổi' }[t] }}
      </button>
    </div>

    <!-- ═══════════════════ Tab 1: Master ═══════════════════ -->
    <div v-if="tab === 'master'">
      <div class="flex items-center justify-between mb-3">
        <div class="flex gap-2">
          <input v-model="uomSearch" type="text" placeholder="Tìm ĐVT..."
                 class="form-input text-sm" @keyup.enter="loadUoms" />
          <button class="btn-ghost text-sm" @click="loadUoms">Tìm</button>
        </div>
        <div class="flex gap-2">
          <button class="btn-secondary text-sm" @click="doSeed">🌱 Seed UOM chuẩn</button>
          <button class="btn-primary text-sm" @click="openCreateUom">+ Thêm ĐVT</button>
        </div>
      </div>

      <div class="card p-0 overflow-hidden">
        <div v-if="uomLoading" class="text-center py-10 text-slate-400">Đang tải...</div>
        <div v-else-if="!uoms.length" class="text-center py-10 text-slate-400 text-sm">
          Chưa có ĐVT nào. Bấm "Seed UOM chuẩn" để tạo danh mục mặc định.
        </div>
        <table v-else class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">Tên ĐVT</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">Ký hiệu</th>
              <th class="px-4 py-2 text-center text-xs font-medium text-slate-500">Số nguyên</th>
              <th class="px-4 py-2 text-center text-xs font-medium text-slate-500">Đang dùng</th>
              <th class="px-4 py-2 text-right text-xs font-medium text-slate-500">Số lần sử dụng</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">Mô tả</th>
              <th class="px-4 py-2 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="u in uoms" :key="u.name" :class="!u.is_active ? 'bg-slate-50/60 text-slate-400' : ''">
              <td class="px-4 py-2 font-medium">{{ u.uom_name }}</td>
              <td class="px-4 py-2 font-mono text-xs">{{ u.symbol || '—' }}</td>
              <td class="px-4 py-2 text-center">{{ u.must_be_whole_number ? '✓' : '—' }}</td>
              <td class="px-4 py-2 text-center">
                <span v-if="u.is_active" class="text-emerald-600">✓</span>
                <span v-else class="text-slate-400">off</span>
              </td>
              <td class="px-4 py-2 text-right text-xs">
                <span v-if="u.use_count" class="font-semibold text-slate-700">{{ u.use_count }}</span>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-2 text-xs text-slate-500 max-w-xs truncate" :title="u.description">
                {{ u.description || '—' }}
              </td>
              <td class="px-4 py-2 text-right space-x-2 whitespace-nowrap">
                <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="openEditUom(u)">Sửa</button>
                <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="removeUom(u.name)">Xóa</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ═══════════════════ Tab 2: Parts & UOM ═══════════════════ -->
    <div v-if="tab === 'parts'">
      <!-- Missing UOM alert -->
      <div v-if="partsMissing.length" class="card p-4 mb-4 bg-amber-50 border border-amber-200">
        <div class="flex items-start gap-3">
          <span class="text-2xl">⚠️</span>
          <div class="flex-1">
            <p class="font-semibold text-amber-900">
              {{ partsMissing.length }} phụ tùng chưa gán đơn vị tồn kho
            </p>
            <p class="text-xs text-amber-700 mt-1">
              Không thể nhập kho / xuất kho nếu thiếu stock_uom. Gán nhanh đơn vị mặc định:
            </p>
            <div class="mt-3 flex items-end gap-2">
              <select v-model="defaultUomForBulk" class="form-input text-sm w-40">
                <option v-for="u in activeUoms" :key="u.name" :value="u.name">{{ u.uom_name }}</option>
              </select>
              <button class="btn-primary text-sm" @click="doBulkAssign">
                Gán "{{ defaultUomForBulk }}" cho tất cả
              </button>
            </div>
            <details class="mt-3">
              <summary class="text-xs text-amber-700 cursor-pointer hover:text-amber-900">
                Xem danh sách {{ partsMissing.length }} phụ tùng
              </summary>
              <div class="mt-2 max-h-48 overflow-y-auto text-xs space-y-0.5">
                <div v-for="p in partsMissing" :key="p.name"
                     class="px-2 py-1 rounded bg-white border border-amber-100 font-mono">
                  {{ p.part_code || p.name }} — {{ p.part_name }}
                </div>
              </div>
            </details>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between mb-3">
        <div class="flex gap-2">
          <input v-model="partsSearch" type="text" placeholder="Tìm phụ tùng..."
                 class="form-input text-sm" @keyup.enter="loadParts" />
          <button class="btn-ghost text-sm" @click="loadParts">Tìm</button>
        </div>
        <span class="text-xs text-slate-500">{{ parts.length }} phụ tùng</span>
      </div>

      <div class="card p-0 overflow-hidden">
        <div v-if="partsLoading" class="text-center py-10 text-slate-400">Đang tải...</div>
        <table v-else class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">Mã</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">Tên phụ tùng</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">ĐVT tồn kho</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">ĐVT mua hàng</th>
              <th class="px-4 py-2 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="p in parts" :key="p.name"
                :class="!p.stock_uom ? 'bg-amber-50/40' : ''">
              <td class="px-4 py-2 font-mono text-xs text-slate-500">{{ p.part_code || p.name }}</td>
              <td class="px-4 py-2 font-medium text-slate-800">{{ p.part_name }}</td>
              <template v-if="editingPart === p.name">
                <td class="px-4 py-2">
                  <select v-model="editStockUom" class="form-input text-sm w-32">
                    <option value="">— chọn —</option>
                    <option v-for="u in activeUoms" :key="u.name" :value="u.name">{{ u.uom_name }}</option>
                  </select>
                </td>
                <td class="px-4 py-2">
                  <select v-model="editPurchaseUom" class="form-input text-sm w-32">
                    <option value="">(giống ĐVT tồn kho)</option>
                    <option v-for="u in activeUoms" :key="u.name" :value="u.name">{{ u.uom_name }}</option>
                  </select>
                </td>
                <td class="px-4 py-2 text-right space-x-2 whitespace-nowrap">
                  <button class="text-emerald-600 hover:text-emerald-800 text-xs font-medium" @click="savePartUom">Lưu</button>
                  <button class="text-slate-500 hover:text-slate-700 text-xs" @click="editingPart = null">Hủy</button>
                </td>
              </template>
              <template v-else>
                <td class="px-4 py-2">
                  <span v-if="p.stock_uom" class="inline-block px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-xs font-medium">
                    {{ p.stock_uom }}
                  </span>
                  <span v-else class="text-red-500 text-xs italic">⚠️ thiếu</span>
                </td>
                <td class="px-4 py-2 text-xs text-slate-600">{{ p.purchase_uom || '(= tồn kho)' }}</td>
                <td class="px-4 py-2 text-right">
                  <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="openEditPart(p)">Sửa</button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ═══════════════════ Tab 3: Conversions ═══════════════════ -->
    <div v-if="tab === 'conversions'">
      <div class="card p-4 mb-4">
        <label for="conv-part" class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Chọn phụ tùng để quản lý quy đổi
        </label>
        <select id="conv-part" v-model="convPart" class="form-input w-full" @change="loadConvForPart">
          <option value="">— Chọn —</option>
          <option v-for="p in parts" :key="p.name" :value="p.name">
            {{ p.part_name }} ({{ p.part_code || p.name }}) — stock: {{ p.stock_uom || '??' }}
          </option>
        </select>
      </div>

      <div v-if="convLoading" class="card p-8 text-center text-slate-400">Đang tải...</div>

      <div v-else-if="!convPart" class="card p-8 text-center text-slate-400 text-sm">
        Chọn 1 phụ tùng ở trên để xem / chỉnh bảng quy đổi.
      </div>

      <div v-else-if="convInfo" class="space-y-4">
        <!-- Info -->
        <div class="card p-4 bg-blue-50 border-blue-200">
          <p class="text-sm">
            <b>{{ convInfo.part_name }}</b> — stock_uom = <b>{{ convInfo.stock_uom }}</b>
            <span v-if="convInfo.purchase_uom && convInfo.purchase_uom !== convInfo.stock_uom">
              · purchase_uom = <b>{{ convInfo.purchase_uom }}</b>
            </span>
          </p>
        </div>

        <!-- Add new -->
        <div class="card p-4">
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Thêm / cập nhật quy đổi</p>
          <div class="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
            <div>
              <label class="block text-xs text-slate-500 mb-1">Đơn vị</label>
              <select v-model="newConv.uom" class="form-input text-sm w-full">
                <option value="">— chọn —</option>
                <option v-for="u in activeUoms.filter(x => x.name !== convInfo?.stock_uom)"
                        :key="u.name" :value="u.name">{{ u.uom_name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-slate-500 mb-1">1 {{ newConv.uom || '?' }} = X {{ convInfo.stock_uom }}</label>
              <input v-model.number="newConv.conversion_factor" type="number" min="0.000001" step="any"
                     class="form-input text-sm w-full" />
            </div>
            <label class="flex items-center gap-2 text-xs">
              <input v-model="newConv.is_purchase_uom" type="checkbox" :true-value="1" :false-value="0" />
              Mặc định mua hàng
            </label>
            <label class="flex items-center gap-2 text-xs">
              <input v-model="newConv.is_issue_uom" type="checkbox" :true-value="1" :false-value="0" />
              Mặc định xuất kho
            </label>
            <button class="btn-primary text-sm" @click="addConversion">+ Lưu</button>
          </div>
        </div>

        <!-- Current conversions table -->
        <div class="card p-0 overflow-hidden">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 border-b border-slate-200">
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">Đơn vị</th>
                <th class="px-4 py-2 text-right text-xs font-medium text-slate-500">Hệ số (= stock_uom)</th>
                <th class="px-4 py-2 text-center text-xs font-medium text-slate-500">Mua hàng</th>
                <th class="px-4 py-2 text-center text-xs font-medium text-slate-500">Xuất kho</th>
                <th class="px-4 py-2 text-right"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr class="bg-blue-50/40">
                <td class="px-4 py-2 font-semibold">{{ convInfo.stock_uom }}
                  <span class="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded ml-1">stock_uom</span>
                </td>
                <td class="px-4 py-2 text-right font-mono">1.0</td>
                <td class="px-4 py-2"></td><td class="px-4 py-2"></td><td class="px-4 py-2"></td>
              </tr>
              <tr v-for="c in convInfo.conversions.filter(r => r.uom !== convInfo?.stock_uom)" :key="c.uom">
                <td class="px-4 py-2 font-medium">{{ c.uom }}</td>
                <td class="px-4 py-2 text-right font-mono">{{ c.conversion_factor }}</td>
                <td class="px-4 py-2 text-center">
                  <span v-if="c.is_purchase_uom" class="text-emerald-600">✓</span>
                  <span v-else class="text-slate-300">—</span>
                </td>
                <td class="px-4 py-2 text-center">
                  <span v-if="c.is_issue_uom" class="text-emerald-600">✓</span>
                  <span v-else class="text-slate-300">—</span>
                </td>
                <td class="px-4 py-2 text-right">
                  <button class="text-red-600 hover:text-red-800 text-xs" @click="deleteConversion(c.uom)">Xóa</button>
                </td>
              </tr>
              <tr v-if="convInfo.conversions.filter(r => r.uom !== convInfo?.stock_uom).length === 0">
                <td colspan="5" class="px-4 py-6 text-center text-xs text-slate-400 italic">
                  Chưa có quy đổi. Thêm ở form bên trên.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- UOM Form Modal -->
    <div v-if="showUomForm" class="fixed inset-0 bg-slate-900/50 z-50 flex items-center justify-center p-4"
         @click.self="showUomForm = false">
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
        <h2 class="text-lg font-semibold text-slate-900">
          {{ uomEditing ? `Sửa ĐVT: ${uomEditing}` : 'Thêm đơn vị tính' }}
        </h2>
        <div>
          <label class="block text-xs font-medium text-slate-600 mb-1">Tên ĐVT *</label>
          <input v-model="uomForm.uom_name" :disabled="!!uomEditing" type="text"
                 class="form-input w-full disabled:bg-slate-100" placeholder="VD: Cái, Hộp, mL" />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-600 mb-1">Ký hiệu</label>
          <input v-model="uomForm.symbol" type="text" class="form-input w-full" placeholder="VD: pc, ml" />
        </div>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="uomForm.must_be_whole_number" type="checkbox" :true-value="1" :false-value="0" />
          Chỉ nhận số nguyên
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="uomForm.is_active" type="checkbox" :true-value="1" :false-value="0" />
          Đang sử dụng
        </label>
        <div>
          <label class="block text-xs font-medium text-slate-600 mb-1">Mô tả</label>
          <textarea v-model="uomForm.description" rows="2" class="form-input w-full" />
        </div>
        <div class="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <button class="btn-ghost text-sm" @click="showUomForm = false">Hủy</button>
          <button class="btn-primary text-sm" @click="saveUom">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
