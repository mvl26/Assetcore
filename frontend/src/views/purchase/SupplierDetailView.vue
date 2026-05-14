<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSupplier, deleteSupplier } from '@/api/imm00'
import PageHeader from '@/components/common/PageHeader.vue'
import { listPurchases } from '@/api/purchase'
import type { AcSupplier } from '@/types/imm00'
import type { Purchase } from '@/api/purchase'

const route = useRoute()
const router = useRouter()
const name = computed(() => route.params.id as string)

const supplier = ref<AcSupplier | null>(null)
const purchases = ref<Purchase[]>([])
const purchasesTotal = ref(0)
const loading = ref(true)
const error = ref('')

const VENDOR_TYPE_LABEL: Record<string, string> = {
  Manufacturer: 'Nhà sản xuất',
  Distributor: 'Nhà phân phối',
  'Service Provider': 'Dịch vụ',
  'Calibration Lab': 'Phòng hiệu chuẩn',
}

const STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp', Submitted: 'Đã duyệt', Received: 'Đã nhận', Cancelled: 'Đã huỷ',
}
const STATUS_CLASS: Record<string, string> = {
  Draft: 'bg-slate-100 text-slate-600',
  Submitted: 'bg-blue-50 text-blue-700',
  Received: 'bg-emerald-50 text-emerald-700',
  Cancelled: 'bg-red-50 text-red-700',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [s, pur] = await Promise.all([
      getSupplier(name.value),
      listPurchases({ supplier: name.value, page_size: 10 }),
    ])
    supplier.value = (s as unknown as AcSupplier) || null
    purchases.value = pur.data
    purchasesTotal.value = pur.total
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Không thể tải nhà cung cấp'
  } finally {
    loading.value = false
  }
}

async function remove() {
  if (!supplier.value) return
  if (!confirm(`Xóa nhà cung cấp "${supplier.value.supplier_name}" (${supplier.value.name})?`)) return
  try {
    await deleteSupplier(supplier.value.name)
    router.push('/suppliers')
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Không thể xóa — có thể đang được tham chiếu'
  }
}

function formatDate(d?: string) { return d ? new Date(d).toLocaleDateString('vi-VN') : '—' }
function vnd(v?: number) {
  if (!v) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function daysUntilExpiry(d?: string) {
  if (!d) return null
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
}
function expiryClass(d?: string) {
  const days = daysUntilExpiry(d)
  if (days === null) return 'text-slate-400'
  if (days < 0) return 'text-red-700 font-semibold'
  if (days < 30) return 'text-red-600 font-medium'
  if (days < 90) return 'text-yellow-600 font-medium'
  return 'text-slate-700'
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      back-to="/suppliers"
      :title="supplier?.supplier_name || 'Chi tiết nhà cung cấp'"
      :subtitle="supplier ? `Mã: ${supplier.name}` : ''"
      :breadcrumb="[
        { label: 'Nhà cung cấp', to: '/suppliers' },
        { label: supplier?.supplier_name || name },
      ]"
    >
      <template #actions>
        <button
          v-if="supplier"
          class="px-4 py-2 text-sm border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 font-medium"
          @click="router.push(`/suppliers/${supplier.name}/edit`)"
        >Sửa</button>
        <button
          v-if="supplier"
          class="px-4 py-2 text-sm border border-red-300 text-red-700 rounded-lg hover:bg-red-50 font-medium"
          @click="remove"
        >Xóa</button>
      </template>
    </PageHeader>

    <div v-if="error" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ error }}</div>
    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
    <div v-else-if="!supplier" class="text-center text-gray-400 py-12">Không tìm thấy nhà cung cấp.</div>

    <template v-else>
      <!-- Thông tin chính -->
      <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div class="flex items-start justify-between pb-4 border-b border-gray-100">
          <div>
            <p class="text-xs text-gray-500 uppercase tracking-wide">Mã nhà cung cấp</p>
            <p class="font-mono text-sm text-gray-700 mt-0.5">{{ supplier.name }}</p>
            <h2 class="text-lg font-semibold text-gray-800 mt-2">{{ supplier.supplier_name }}</h2>
          </div>
          <span
            class="text-xs px-3 py-1 rounded-full font-medium"
            :class="supplier.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
          >{{ supplier.is_active ? 'Đang hoạt động' : 'Ngừng hoạt động' }}</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div><span class="text-gray-500">Loại nhà cung cấp:</span>
            <span class="ml-2 text-gray-800">{{ VENDOR_TYPE_LABEL[supplier.vendor_type || ''] || supplier.vendor_type || '—' }}</span>
          </div>
          <div><span class="text-gray-500">Quốc gia:</span>
            <span class="ml-2 text-gray-800">{{ supplier.country || '—' }}</span>
          </div>
          <div><span class="text-gray-500">Email:</span>
            <a v-if="supplier.email_id" :href="`mailto:${supplier.email_id}`" class="ml-2 text-blue-600 hover:underline">{{ supplier.email_id }}</a>
            <span v-else class="ml-2 text-gray-400">—</span>
          </div>
          <div><span class="text-gray-500">Điện thoại bàn:</span>
            <span class="ml-2 text-gray-800">{{ supplier.phone || '—' }}</span>
          </div>
          <div><span class="text-gray-500">Di động:</span>
            <span class="ml-2 text-gray-800">{{ supplier.mobile_no || '—' }}</span>
          </div>
          <div><span class="text-gray-500">Website:</span>
            <a v-if="supplier.website" :href="supplier.website" target="_blank" rel="noopener" class="ml-2 text-blue-600 hover:underline">{{ supplier.website }}</a>
            <span v-else class="ml-2 text-gray-400">—</span>
          </div>
          <div class="sm:col-span-2"><span class="text-gray-500">Địa chỉ:</span>
            <span class="ml-2 text-gray-800 whitespace-pre-line">{{ supplier.address || '—' }}</span>
          </div>
          <div><span class="text-gray-500">Mã số thuế:</span>
            <span class="ml-2 font-mono text-gray-800">{{ supplier.tax_id || '—' }}</span>
          </div>
        </div>
      </div>

      <!-- Hợp đồng & Chứng chỉ -->
      <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-3">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Hợp đồng & Chứng chỉ</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div><span class="text-gray-500">Hợp đồng từ:</span>
            <span class="ml-2 text-gray-800">{{ formatDate(supplier.contract_start) }}</span>
          </div>
          <div><span class="text-gray-500">Hợp đồng đến:</span>
            <span class="ml-2" :class="expiryClass(supplier.contract_end)">{{ formatDate(supplier.contract_end) }}</span>
          </div>
          <div><span class="text-gray-500">ISO 13485:</span>
            <span class="ml-2 font-mono text-gray-800">{{ supplier.iso_13485_cert || '—' }}</span>
          </div>
          <div><span class="text-gray-500">ISO 13485 hết hạn:</span>
            <span class="ml-2" :class="expiryClass(supplier.iso_13485_expiry)">{{ formatDate(supplier.iso_13485_expiry) }}</span>
          </div>
          <div><span class="text-gray-500">ISO 17025:</span>
            <span class="ml-2 font-mono text-gray-800">{{ supplier.iso_17025_cert || '—' }}</span>
          </div>
          <div><span class="text-gray-500">ISO 17025 hết hạn:</span>
            <span class="ml-2" :class="expiryClass(supplier.iso_17025_expiry)">{{ formatDate(supplier.iso_17025_expiry) }}</span>
          </div>
        </div>
      </div>

      <!-- Lịch sử đơn mua -->
      <div class="bg-white rounded-xl border border-gray-200 p-5">
        <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
          <h2 class="text-sm font-semibold text-slate-700">Lịch sử đơn hàng mua</h2>
          <span class="text-xs text-slate-400">{{ purchasesTotal }} đơn</span>
        </div>
        <div v-if="!purchases.length" class="py-8 text-center text-slate-400 text-sm">
          Nhà cung cấp này chưa có đơn hàng nào
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-slate-400 border-b border-slate-100">
                <th class="py-2 text-left font-medium">Mã đơn</th>
                <th class="py-2 text-left font-medium">Ngày đặt</th>
                <th class="py-2 text-left font-medium">Số hóa đơn</th>
                <th class="py-2 text-right font-medium">Tổng giá trị</th>
                <th class="py-2 text-center font-medium">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="p in purchases" :key="p.name"
                class="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                @click="router.push(`/purchases/${p.name}`)"
              >
                <td class="py-2.5 font-mono text-xs text-blue-600 hover:underline">{{ p.name }}</td>
                <td class="py-2.5 text-slate-600 text-xs">{{ formatDate(p.purchase_date) }}</td>
                <td class="py-2.5 font-mono text-xs text-slate-500">{{ p.invoice_no || '—' }}</td>
                <td class="py-2.5 text-right font-semibold text-slate-800">{{ vnd(p.total_value) }}</td>
                <td class="py-2.5 text-center">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                        :class="STATUS_CLASS[p.status] || 'bg-slate-100 text-slate-600'">
                    {{ STATUS_LABELS[p.status] || p.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="purchasesTotal > 10" class="pt-3 text-center">
            <button
              class="text-xs text-blue-600 hover:underline"
              @click="router.push(`/purchases?supplier=${supplier!.name}`)"
            >Xem tất cả {{ purchasesTotal }} đơn hàng →</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
