<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getPurchase, submitPurchase, cancelPurchase, deletePurchase, markReceived,
  getPurchaseMovements, createReceiptMovement, getPurchaseCommissionings,
} from '@/api/purchase'
import type { Purchase, LinkedMovement, LinkedCommissioning } from '@/api/purchase'
import { createCommissioningFromPurchase } from '@/api/imm04'
import SmartSelect from '@/components/common/SmartSelect.vue'

const props = defineProps<{ name: string }>()
const router = useRouter()

const doc = ref<Purchase | null>(null)
const movements = ref<LinkedMovement[]>([])
const commissionings = ref<LinkedCommissioning[]>([])
const loading = ref(false)
const acting = ref(false)
const toast = ref('')
const toastError = ref(false)

// Flow summary
const deviceCommissioningDone = computed(() =>
  (doc.value?.devices || []).filter(d => d.commissioning_ref).length,
)
const deviceAssetDone = computed(() =>
  (doc.value?.devices || []).filter(d => d.final_asset).length,
)

// Receipt creation modal
const showReceiptModal = ref(false)
const receiptWarehouse = ref('')
const receiptAutoSubmit = ref(false)
const creatingReceipt = ref(false)

async function load() {
  loading.value = true
  try {
    const [d, m, c] = await Promise.all([
      getPurchase(props.name),
      getPurchaseMovements(props.name),
      getPurchaseCommissionings(props.name),
    ])
    doc.value = d
    movements.value = m
    commissionings.value = c
  } finally { loading.value = false }
}

function showToast(msg: string, error = false) {
  toast.value = msg
  toastError.value = error
  setTimeout(() => { toast.value = '' }, 3500)
}

async function createCommissioning(deviceIdx: number) {
  if (!doc.value) return
  if (doc.value.docstatus !== 1) {
    showToast('Phải duyệt đơn hàng trước khi tiếp nhận thiết bị', true); return
  }
  if (!confirm('Tạo phiếu tiếp nhận cho thiết bị này?')) return
  acting.value = true
  try {
    const res = await createCommissioningFromPurchase(doc.value.name, deviceIdx)
    showToast(`Đã tạo phiếu ${res.name}`)
    router.push(`/commissioning/${res.name}`)
  } catch (e: unknown) {
    showToast((e as Error).message || 'Lỗi tạo phiếu tiếp nhận', true)
  } finally { acting.value = false }
}

async function doSubmit() {
  if (!doc.value || !confirm('Xác nhận duyệt đơn hàng này?')) return
  acting.value = true
  try { await submitPurchase(doc.value.name); showToast('Đã duyệt đơn hàng'); await load() }
  catch (e: unknown) { showToast((e as Error).message || 'Lỗi duyệt đơn', true) }
  finally { acting.value = false }
}

async function doMarkReceived() {
  if (!doc.value || !confirm('Xác nhận đã nhận đủ hàng?')) return
  acting.value = true
  try { await markReceived(doc.value.name); showToast('Đã xác nhận nhận hàng'); await load() }
  catch (e: unknown) { showToast((e as Error).message || 'Lỗi xác nhận', true) }
  finally { acting.value = false }
}

async function doCancel() {
  if (!doc.value || !confirm('Xác nhận huỷ đơn hàng này?')) return
  acting.value = true
  try { await cancelPurchase(doc.value.name); showToast('Đã huỷ đơn hàng'); await load() }
  catch (e: unknown) { showToast((e as Error).message || 'Lỗi huỷ đơn', true) }
  finally { acting.value = false }
}

async function doDelete() {
  if (!doc.value || !confirm('Xoá đơn nháp này? Hành động không thể hoàn tác.')) return
  acting.value = true
  try { await deletePurchase(doc.value.name); router.push('/purchases') }
  catch (e: unknown) { showToast((e as Error).message || 'Lỗi xoá đơn', true); acting.value = false }
}

async function doCreateReceipt() {
  if (!receiptWarehouse.value) { showToast('Phải chọn kho nhập hàng', true); return }
  creatingReceipt.value = true
  try {
    const res = await createReceiptMovement(props.name, receiptWarehouse.value, {
      auto_submit: receiptAutoSubmit.value ? 1 : 0,
    })
    showReceiptModal.value = false
    receiptWarehouse.value = ''
    showToast('Đã tạo phiếu nhập kho: ' + res.movement_name)
    await load()
    router.push(`/stock-movements/${res.movement_name}`)
  } catch (e: unknown) {
    showToast((e as Error).message || 'Lỗi tạo phiếu nhập kho', true)
  } finally { creatingReceipt.value = false }
}

function vnd(v?: number) {
  if (!v) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function formatDt(d?: string) { return d ? new Date(d).toLocaleString('vi-VN') : '—' }
function formatDate(d?: string) { return d ? new Date(d).toLocaleDateString('vi-VN') : '—' }

const STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp', Submitted: 'Đã duyệt', Received: 'Đã nhận hàng', Cancelled: 'Đã huỷ',
}
const STATUS_CLASS: Record<string, string> = {
  Draft: 'bg-slate-100 text-slate-600',
  Submitted: 'bg-blue-50 text-blue-700',
  Received: 'bg-emerald-50 text-emerald-700',
  Cancelled: 'bg-red-50 text-red-700',
}
const MOV_TYPE_LABELS: Record<string, string> = {
  Receipt: 'Nhập kho', Issue: 'Xuất kho', Transfer: 'Chuyển kho', Adjustment: 'Điều chỉnh',
}
const MOV_TYPE_CLASS: Record<string, string> = {
  Receipt: 'bg-emerald-50 text-emerald-700',
  Issue: 'bg-red-50 text-red-700',
  Transfer: 'bg-blue-50 text-blue-700',
  Adjustment: 'bg-amber-50 text-amber-700',
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <button class="btn-ghost mb-4" @click="router.push('/purchases')">← Quay lại</button>

    <div v-if="loading && !doc" class="text-center py-20 text-slate-400">Đang tải...</div>

    <div v-else-if="doc">
      <!-- Header -->
      <div class="flex items-start justify-between mb-6 gap-4">
        <div>
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00 · Mua hàng</p>
          <h1 class="text-2xl font-bold text-slate-900">{{ doc.name }}</h1>
          <div class="flex items-center gap-2 mt-2">
            <span class="text-xs px-2.5 py-1 rounded-full font-medium"
                  :class="STATUS_CLASS[doc.status] || 'bg-slate-100 text-slate-600'">
              {{ STATUS_LABELS[doc.status] || doc.status }}
            </span>
          </div>
        </div>
        <div class="flex gap-2 flex-wrap justify-end">
          <button v-if="doc.docstatus === 0" class="btn-ghost" :disabled="acting"
                  @click="router.push(`/purchases/${doc.name}/edit`)">Sửa</button>
          <button v-if="doc.docstatus === 0"
                  class="text-sm px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 font-medium"
                  :disabled="acting" @click="doDelete">Xoá</button>
          <button v-if="doc.docstatus === 0" class="btn-primary" :disabled="acting" @click="doSubmit">
            {{ acting ? '...' : 'Duyệt đơn' }}
          </button>
          <button v-if="doc.docstatus === 1 && doc.status === 'Submitted'"
                  class="btn-secondary" :disabled="acting" @click="doMarkReceived">
            {{ acting ? '...' : 'Xác nhận nhận hàng' }}
          </button>
          <button v-if="doc.docstatus === 1 && doc.status !== 'Received' && doc.status !== 'Cancelled'"
                  class="btn-secondary text-red-600" :disabled="acting" @click="doCancel">
            {{ acting ? '...' : 'Huỷ đơn' }}
          </button>
        </div>
      </div>

      <!-- Toast -->
      <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg text-sm transition-all"
           :class="toastError ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">
        {{ toast }}
      </div>

      <!-- Info -->
      <div class="card p-5 mb-4">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Thông tin đơn hàng</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-xs text-slate-500 mb-0.5">Nhà cung cấp</p>
            <button class="font-medium text-blue-600 hover:underline text-left"
                    @click="router.push(`/suppliers/${doc.supplier}`)">
              {{ doc.supplier_name || doc.supplier }}
            </button>
          </div>
          <div>
            <p class="text-xs text-slate-500 mb-0.5">Ngày đặt hàng</p>
            <p class="font-medium text-slate-800">{{ formatDt(doc.purchase_date) }}</p>
          </div>
          <div v-if="doc.invoice_no">
            <p class="text-xs text-slate-500 mb-0.5">Số hóa đơn / Mã PO</p>
            <p class="font-mono font-medium text-slate-800">{{ doc.invoice_no }}</p>
          </div>
          <div v-if="doc.expected_delivery">
            <p class="text-xs text-slate-500 mb-0.5">Ngày giao hàng dự kiến</p>
            <p class="font-medium text-slate-800">{{ formatDate(doc.expected_delivery) }}</p>
          </div>
        </div>
        <div v-if="doc.notes" class="mt-4 pt-3 border-t border-slate-100">
          <p class="text-xs text-slate-500 mb-1">Ghi chú</p>
          <p class="text-sm text-slate-700 whitespace-pre-wrap">{{ doc.notes }}</p>
        </div>
      </div>

      <!-- Flow summary -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <div v-if="doc.devices && doc.devices.length"
             class="flex items-center gap-3 p-3 rounded-lg border border-indigo-200 bg-indigo-50/40">
          <div class="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center text-lg">🏥</div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-semibold text-indigo-800">Thiết bị y tế → Phiếu tiếp nhận</p>
            <p class="text-xs text-indigo-600 mt-0.5">
              {{ deviceCommissioningDone }} / {{ doc.devices.length }} đã tạo phiếu
              <span v-if="deviceAssetDone"> · {{ deviceAssetDone }} đã thành tài sản</span>
            </p>
          </div>
        </div>
        <div v-if="doc.items && doc.items.length"
             class="flex items-center gap-3 p-3 rounded-lg border border-emerald-200 bg-emerald-50/40">
          <div class="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center text-lg">📦</div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-semibold text-emerald-800">Phụ tùng → Phiếu nhập kho</p>
            <p class="text-xs text-emerald-600 mt-0.5">
              {{ doc.items.length }} dòng ·
              <span v-if="movements.length">{{ movements.length }} phiếu nhập kho</span>
              <span v-else>chưa có phiếu nhập kho</span>
            </p>
          </div>
        </div>
      </div>

      <!-- Devices -->
      <div v-if="doc && doc.devices && doc.devices.length" class="card p-5 mb-4">
        <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
          <div>
            <h2 class="text-sm font-semibold text-slate-700">Thiết bị y tế — {{ doc.devices.length }} máy</h2>
            <p class="text-[11px] text-slate-400 mt-0.5">Mỗi máy là 1 thực thể riêng (1 Asset, 1 Serial, 1 Phiếu tiếp nhận).</p>
          </div>
          <span v-if="doc.docstatus !== 1" class="text-xs text-amber-600">
            Cần duyệt đơn hàng để tiếp nhận
          </span>
        </div>
        <div class="space-y-3">
          <div v-for="(d, idx) in doc.devices" :key="d.name || idx"
               class="flex items-start gap-3 p-3 rounded-lg border border-slate-200 bg-white">
            <span class="shrink-0 inline-flex items-center justify-center w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold font-mono">
              #{{ idx + 1 }}
            </span>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-slate-800">{{ d.device_model_name || d.device_model }}</p>
              <p class="text-xs text-slate-500 font-mono mt-0.5">{{ d.device_model }}</p>
              <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-slate-600">
                <span v-if="d.unit_cost">Đơn giá: <b>{{ vnd(d.unit_cost) }}</b></span>
                <span v-if="d.vendor_serial_no">
                  S/N: <span class="font-mono font-semibold text-slate-800">{{ d.vendor_serial_no }}</span>
                </span>
                <span v-else class="text-amber-600 italic">S/N: điền khi tiếp nhận</span>
                <span v-if="d.warranty_months">BH: <b>{{ d.warranty_months }}</b> tháng</span>
                <span v-if="d.clinical_dept">Khoa: <b>{{ d.clinical_dept }}</b></span>
              </div>
            </div>
            <div class="shrink-0">
              <div v-if="d.commissioning_ref" class="space-y-1">
                <button
                  class="text-xs px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100 transition-colors font-medium flex items-center gap-1.5"
                  @click="router.push(`/commissioning/${d.commissioning_ref}`)"
                >
                  🔗 {{ d.commissioning_ref }}
                </button>
                <p v-if="d.commissioning_state" class="text-[10px] text-slate-500 text-right">
                  {{ d.commissioning_state }}
                </p>
                <p v-if="d.final_asset" class="text-[10px] text-emerald-600 text-right">
                  ✓ Tài sản: <span class="font-mono">{{ d.final_asset }}</span>
                </p>
              </div>
              <button
                v-else
                class="text-xs px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="doc.docstatus !== 1 || acting"
                @click="createCommissioning(d.idx || (idx + 1))"
              >
                Tạo phiếu tiếp nhận
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Items (phụ tùng → nhập kho) -->
      <div v-if="doc.items && doc.items.length" class="card p-5 mb-4">
        <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
          <div>
            <h2 class="text-sm font-semibold text-slate-700">Phụ tùng ({{ doc.items.length }})</h2>
            <p class="text-[11px] text-slate-400 mt-0.5">Sau khi duyệt, phụ tùng được nhập vào kho qua phiếu nhập kho.</p>
          </div>
          <button
            v-if="doc.docstatus === 1 && doc.status === 'Submitted'"
            class="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="acting"
            @click="showReceiptModal = true"
          >
            + Tạo phiếu nhập kho
          </button>
          <span v-else-if="doc.docstatus !== 1" class="text-xs text-amber-600">
            Cần duyệt đơn trước khi nhập kho
          </span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-slate-400 border-b border-slate-100">
                <th class="py-2 text-left font-medium">Phụ tùng</th>
                <th class="py-2 text-right font-medium">SL đặt</th>
                <th class="py-2 text-left font-medium">ĐVT</th>
                <th class="py-2 text-right font-medium">Đơn giá</th>
                <th class="py-2 text-right font-medium">Thành tiền</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in (doc.items || [])" :key="i" class="border-b border-slate-50">
                <td class="py-2.5">
                  <p class="font-medium text-slate-800">{{ r.part_name }}</p>
                  <p class="text-[11px] text-slate-400 font-mono">{{ r.spare_part }}</p>
                </td>
                <td class="py-2.5 text-right font-semibold">{{ r.qty }}</td>
                <td class="py-2.5 text-xs text-slate-500">{{ r.uom }}</td>
                <td class="py-2.5 text-right text-slate-600">{{ vnd(r.unit_cost) }}</td>
                <td class="py-2.5 text-right font-medium text-slate-800">{{ vnd(r.total_cost) }}</td>
              </tr>
            </tbody>
            <tfoot class="border-t-2 border-slate-200">
              <tr>
                <td colspan="3" class="py-3 text-right text-sm font-semibold text-slate-500">Tổng giá trị đặt hàng</td>
                <td class="py-3 text-right text-lg font-bold text-emerald-700">{{ vnd(doc.total_value) }}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <!-- Linked commissioning records -->
      <div v-if="doc.devices && doc.devices.length" class="card p-5 mb-4">
        <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
          <h2 class="text-sm font-semibold text-slate-700">Phiếu tiếp nhận thiết bị liên quan</h2>
          <span class="text-xs text-slate-400">{{ commissionings.length }} phiếu</span>
        </div>

        <div v-if="!commissionings.length" class="py-8 text-center text-slate-400 text-sm">
          Chưa có phiếu tiếp nhận nào tham chiếu đơn hàng này
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-slate-400 border-b border-slate-100">
                <th class="py-2 text-left font-medium">Mã phiếu</th>
                <th class="py-2 text-left font-medium">Model thiết bị</th>
                <th class="py-2 text-left font-medium">Serial</th>
                <th class="py-2 text-left font-medium">Khoa sử dụng</th>
                <th class="py-2 text-left font-medium">Tài sản</th>
                <th class="py-2 text-center font-medium">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in commissionings" :key="c.name"
                  class="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                  @click="router.push(`/commissioning/${c.name}`)">
                <td class="py-2.5 font-mono text-xs text-blue-600 hover:underline">{{ c.name }}</td>
                <td class="py-2.5 text-slate-700">{{ c.master_item || '—' }}</td>
                <td class="py-2.5 font-mono text-xs text-slate-500">{{ c.vendor_serial_no || '—' }}</td>
                <td class="py-2.5 text-slate-600">{{ c.clinical_dept || '—' }}</td>
                <td class="py-2.5">
                  <button v-if="c.final_asset"
                    class="text-xs text-blue-600 hover:underline font-mono"
                    @click.stop="router.push(`/assets/${c.final_asset}`)">
                    {{ c.final_asset }}
                  </button>
                  <span v-else class="text-slate-400 text-xs">Chưa tạo</span>
                </td>
                <td class="py-2.5 text-center">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                        :class="c.workflow_state === 'Released'
                          ? 'bg-emerald-50 text-emerald-700'
                          : c.workflow_state === 'Cancelled'
                          ? 'bg-red-50 text-red-600'
                          : 'bg-blue-50 text-blue-700'">
                    {{ c.workflow_state || 'Draft' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Linked stock movements -->
      <div v-if="doc.items && doc.items.length" class="card p-5">
        <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
          <h2 class="text-sm font-semibold text-slate-700">Phiếu nhập kho liên quan</h2>
          <span class="text-xs text-slate-400">{{ movements.length }} phiếu</span>
        </div>

        <div v-if="!movements.length" class="py-8 text-center text-slate-400 text-sm">
          Chưa có phiếu nhập kho nào được tạo từ đơn hàng này
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-slate-400 border-b border-slate-100">
                <th class="py-2 text-left font-medium">Mã phiếu</th>
                <th class="py-2 text-left font-medium">Ngày</th>
                <th class="py-2 text-left font-medium">Loại</th>
                <th class="py-2 text-left font-medium">Kho nhập</th>
                <th class="py-2 text-right font-medium">Giá trị</th>
                <th class="py-2 text-center font-medium">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in movements" :key="m.name"
                  class="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                  @click="router.push(`/stock-movements/${m.name}`)">
                <td class="py-2.5 font-mono text-xs text-blue-600 hover:underline">{{ m.name }}</td>
                <td class="py-2.5 text-slate-600">{{ formatDt(m.movement_date) }}</td>
                <td class="py-2.5">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                        :class="MOV_TYPE_CLASS[m.movement_type] || 'bg-slate-100 text-slate-600'">
                    {{ MOV_TYPE_LABELS[m.movement_type] || m.movement_type }}
                  </span>
                </td>
                <td class="py-2.5 text-slate-700">{{ m.to_warehouse_code || m.to_warehouse || '—' }}</td>
                <td class="py-2.5 text-right font-semibold text-slate-800">{{ vnd(m.total_value) }}</td>
                <td class="py-2.5 text-center">
                  <span class="text-xs px-2 py-0.5 rounded-full"
                        :class="m.docstatus === 1 ? 'bg-emerald-50 text-emerald-700' :
                                m.docstatus === 2 ? 'bg-red-50 text-red-600' :
                                                    'bg-slate-100 text-slate-600'">
                    {{ m.docstatus === 1 ? 'Đã duyệt' : m.docstatus === 2 ? 'Đã huỷ' : 'Nháp' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Receipt creation modal -->
    <Teleport to="body">
      <div v-if="showReceiptModal"
           class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
           @click.self="showReceiptModal = false">
        <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 animate-fade-in">
          <h3 class="text-lg font-bold text-slate-900 mb-1">Tạo phiếu nhập kho</h3>
          <p class="text-sm text-slate-500 mb-5">
            Tạo phiếu nhập kho (Receipt) từ đơn hàng <span class="font-mono font-semibold">{{ props.name }}</span>.
            Tất cả phụ tùng trong đơn sẽ được sao chép vào phiếu.
          </p>

          <div class="mb-4">
            <label for="receipt-wh" class="form-label">Kho nhập hàng *</label>
            <SmartSelect id="receipt-wh" v-model="receiptWarehouse"
                         doctype="AC Warehouse" placeholder="Chọn kho nhập..." />
          </div>

          <div class="flex items-center gap-2 mb-6">
            <input id="receipt-auto-submit" v-model="receiptAutoSubmit" type="checkbox"
                   class="w-4 h-4 rounded border-slate-300 text-emerald-600" />
            <label for="receipt-auto-submit" class="text-sm text-slate-700 cursor-pointer">
              Duyệt phiếu ngay (cập nhật tồn kho ngay lập tức)
            </label>
          </div>

          <div class="flex gap-3 justify-end">
            <button class="btn-ghost" :disabled="creatingReceipt"
                    @click="showReceiptModal = false; receiptWarehouse = ''">Huỷ</button>
            <button class="btn-primary" :disabled="creatingReceipt || !receiptWarehouse"
                    @click="doCreateReceipt">
              {{ creatingReceipt ? 'Đang tạo...' : 'Tạo phiếu nhập kho' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
