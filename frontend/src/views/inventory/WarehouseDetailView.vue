<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getWarehouse, updateWarehouse, deleteWarehouse } from '@/api/inventory'
import type { Warehouse, StockRow } from '@/types/inventory'
import SmartSelect from '@/components/common/SmartSelect.vue'
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'

const props = defineProps<{ name: string }>()
const router = useRouter()

type WarehouseDetail = Warehouse & { stock_items: StockRow[]; total_value: number }

const wh = ref<WarehouseDetail | null>(null)
const loading = ref(false)
const showEdit = ref(false)
const saving = ref(false)
const toast = ref('')
const form = ref<Partial<Warehouse>>({})

async function load() {
  loading.value = true
  try { wh.value = await getWarehouse(props.name) as WarehouseDetail }
  catch (e: unknown) { toast.value = (e as Error).message || 'Lỗi tải kho' }
  finally { loading.value = false }
}

function openEdit() {
  if (!wh.value) return
  form.value = {
    warehouse_name: wh.value.warehouse_name,
    department: wh.value.department,
    location: wh.value.location,
    manager: wh.value.manager,
    is_active: wh.value.is_active,
    notes: wh.value.notes,
  }
  showEdit.value = true
}

async function saveEdit() {
  if (!form.value.warehouse_name) { toast.value = 'Tên kho là bắt buộc'; return }
  saving.value = true
  try {
    await updateWarehouse(props.name, form.value)
    showEdit.value = false
    await load()
    toast.value = 'Cập nhật thành công'
    setTimeout(() => { toast.value = '' }, 3000)
  } catch (e: unknown) {
    toast.value = (e as Error).message || 'Lỗi lưu'
  } finally { saving.value = false }
}

async function doDeactivate() {
  if (!wh.value) return
  if (!confirm(`Ngừng hoạt động kho "${wh.value.warehouse_name}"? Kho phải không còn tồn kho.`)) return
  try {
    await deleteWarehouse(props.name)
    toast.value = 'Đã ngừng hoạt động kho'
    await load()
    setTimeout(() => { toast.value = '' }, 3000)
  } catch (e: unknown) {
    toast.value = (e as Error).message || 'Lỗi ngừng kho'
  }
}

function vnd(v?: number) {
  if (!v) return '0 đ'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function formatDt(d?: string) { return d ? new Date(d).toLocaleDateString('vi-VN') : '—' }

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm">{{ toast }}</div>

    <div v-if="loading && !wh" class="text-center py-20 text-slate-400">Đang tải…</div>

    <div v-else-if="wh">
      <PageHeader
        :back-to="'/warehouses'"
        :title="wh.warehouse_name"
        :subtitle="`IMM-15 · Tồn kho phụ tùng — ${wh.warehouse_code || wh.name}`"
        :breadcrumb="[{ label: 'IMM-15 · Tồn kho phụ tùng', to: '/inventory/dashboard' }, { label: 'Kho', to: '/warehouses' }, { label: wh.warehouse_name }]"
      >
        <template #actions>
          <button class="btn-secondary" @click="openEdit">Chỉnh sửa</button>
          <button v-if="wh.is_active" class="btn-ghost text-red-600 hover:bg-red-50" @click="doDeactivate">Ngừng hoạt động</button>
        </template>
      </PageHeader>

      <!-- Summary -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div class="kpi-card p-4" style="--kpi-color: #2563eb">
          <p class="t-eyebrow mb-2">Số SKU</p>
          <p class="t-metric tabular-nums">{{ wh.stock_count || wh.stock_items.length }}</p>
        </div>
        <div class="kpi-card p-4" style="--kpi-color: #059669">
          <p class="t-eyebrow mb-2">Giá trị tồn</p>
          <p class="t-metric tabular-nums text-emerald-600">{{ vnd(wh.total_value) }}</p>
        </div>
        <div class="kpi-card p-4" style="--kpi-color: #475569">
          <p class="t-eyebrow mb-2">Người phụ trách</p>
          <p class="text-sm font-semibold text-slate-900 truncate mt-1">{{ wh.manager || '—' }}</p>
        </div>
        <div class="kpi-card p-4" :style="`--kpi-color: ${wh.is_active ? '#059669' : '#94a3b8'}`">
          <p class="t-eyebrow mb-2">Trạng thái</p>
          <span v-if="wh.is_active" class="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-medium border border-emerald-100">Đang hoạt động</span>
          <span v-else class="text-[11px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium border border-slate-200">Đã ngừng</span>
        </div>
      </div>

      <!-- Notes -->
      <div v-if="wh.notes" class="card p-4 mb-6">
        <p class="text-xs text-slate-500 mb-1">Ghi chú</p>
        <p class="text-sm text-slate-700 whitespace-pre-wrap">{{ wh.notes }}</p>
      </div>

      <!-- Stock items -->
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-slate-700 mb-4">Tồn kho trong kho</h3>
        <div v-if="wh.stock_items.length === 0" class="text-center py-10 text-slate-400">
          Kho chưa có tồn kho nào
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-slate-400 border-b border-slate-100">
                <th class="py-2 text-left font-medium">Phụ tùng</th>
                <th class="py-2 text-right font-medium" title="Tồn vật lý thực có trong kho">Tồn</th>
                <th
                  class="py-2 text-right font-medium cursor-help"
                  title="Đã giữ = phiếu cấp phát chưa xuất đang giữ chỗ. Khả dụng = Tồn − Đã giữ."
                >
                  <span class="border-b border-dotted border-slate-300">Đã giữ</span>
                </th>
                <th class="py-2 text-right font-medium" title="Khả dụng = Tồn − Đã giữ (phần có thể xuất)">Khả dụng</th>
                <th class="py-2 text-right font-medium">Đơn giá</th>
                <th class="py-2 text-right font-medium">Giá trị</th>
                <th class="py-2 text-left font-medium hidden md:table-cell">Giao dịch cuối</th>
              </tr>
            </thead>
            <tbody>
              <tr
v-for="s in wh.stock_items" :key="s.spare_part"
                  class="border-b border-slate-50 hover:bg-slate-50 cursor-pointer"
                  @click="router.push(`/spare-parts/${s.spare_part}`)">
                <td class="py-2.5">
                  <p class="font-medium text-slate-900">{{ s.part_name || s.spare_part }}</p>
                  <p class="font-mono text-xs text-brand-700 mt-0.5">{{ s.spare_part }}</p>
                </td>
                <td class="py-2.5 text-right font-semibold text-slate-800">
                  {{ s.qty_on_hand }}
                </td>
                <td
                  class="py-2.5 text-right"
                  :class="s.reserved_qty > 0 ? 'text-amber-600 font-medium' : 'text-slate-400'"
                  :title="s.reserved_qty > 0 ? 'Đang được phiếu cấp phát chưa xuất giữ chỗ' : undefined"
                >{{ s.reserved_qty ?? 0 }}</td>
                <td class="py-2.5 text-right text-emerald-600 font-medium">{{ s.available_qty ?? 0 }}</td>
                <td class="py-2.5 text-right text-xs text-slate-500">{{ vnd(s.unit_cost) }}</td>
                <td class="py-2.5 text-right font-medium text-slate-700">{{ vnd(s.stock_value) }}</td>
                <td class="py-2.5 text-xs text-slate-400 hidden md:table-cell">{{ formatDt(s.last_movement_date) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <Transition name="fade">
      <div
v-if="showEdit" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
           @click.self="showEdit = false">
        <div class="bg-white rounded-xl w-full max-w-xl shadow-modal border border-slate-200">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200">
            <h2 class="font-semibold text-slate-900">Chỉnh sửa kho</h2>
            <button class="p-1.5 rounded-md text-slate-400 hover:bg-slate-100" aria-label="Đóng" @click="showEdit = false">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="md:col-span-2">
                <label for="wh-edit-name" class="form-label">Tên kho *</label>
                <input id="wh-edit-name" v-model="form.warehouse_name" type="text" class="form-input w-full" />
              </div>
              <div>
                <label for="wh-edit-location" class="form-label">Vị trí vật lý</label>
                <SmartSelect id="wh-edit-location" v-model="form.location" doctype="AC Location" placeholder="Chọn vị trí..." />
              </div>
              <div>
                <label for="wh-edit-dept" class="form-label">Khoa quản lý</label>
                <SmartSelect id="wh-edit-dept" v-model="form.department" doctype="AC Department" placeholder="Chọn khoa..." />
              </div>
              <div>
                <label for="wh-edit-manager" class="form-label">Người phụ trách</label>
                <ApproverSelect id="wh-edit-manager" v-model="form.manager" context="user" placeholder="Chọn người dùng..." />
              </div>
              <div class="flex items-center gap-3 pt-6">
                <input
id="wh-edit-active" v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0"
                       class="h-4 w-4 text-blue-600 rounded" />
                <label for="wh-edit-active" class="text-sm text-slate-700">Đang hoạt động</label>
              </div>
            </div>
            <div>
              <label for="wh-edit-notes" class="form-label">Ghi chú</label>
              <textarea id="wh-edit-notes" v-model="form.notes" rows="2" class="form-input w-full" />
            </div>
          </div>
          <div class="flex gap-3 justify-end px-6 py-4 border-t border-slate-100">
            <button class="btn-ghost" @click="showEdit = false">Huỷ</button>
            <button class="btn-primary" :disabled="saving" @click="saveEdit">
              {{ saving ? 'Đang lưu…' : 'Lưu thay đổi' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
