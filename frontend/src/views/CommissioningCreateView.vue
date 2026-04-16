<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCommissioningStore } from '@/stores/commissioning'
import { getPoDetails } from '@/api/imm04'

const router = useRouter()
const store = useCommissioningStore()

// ─── Form state ──────────────────────────────────────────────────────────────

const form = ref({
  po_reference: '',
  master_item: '',
  vendor: '',
  clinical_dept: '',
  expected_installation_date: '',
  vendor_serial_no: '',
  vendor_engineer_name: '',
  is_radiation_device: 0 as 0 | 1,
})

const documents = ref([
  { doc_type: 'CO - Chứng nhận Xuất xứ', status: 'Pending' },
  { doc_type: 'CQ - Chứng nhận Chất lượng', status: 'Pending' },
])

const baselines = ref([
  { parameter: 'Dòng rò điện', measured_val: 0, unit: 'mA', test_result: '', fail_note: '' },
  { parameter: 'Điện trở tiếp địa', measured_val: 0, unit: 'Ohm', test_result: '', fail_note: '' },
  { parameter: 'Kiểm tra khởi động OS', measured_val: 0, unit: '', test_result: '', fail_note: '' },
])

const loading = ref(false)
const error = ref<string | null>(null)
const poLoading = ref(false)
const poItems = ref<{ item_code: string; item_name: string; is_radiation: boolean }[]>([])

// ─── PO auto-fill ────────────────────────────────────────────────────────────

async function lookupPO() {
  if (!form.value.po_reference) return
  poLoading.value = true
  error.value = null

  try {
    const res = await getPoDetails(form.value.po_reference)
    if (res.success && res.data) {
      form.value.vendor = res.data.supplier
      poItems.value = res.data.items.map((i) => ({
        item_code: i.item_code,
        item_name: i.item_name,
        is_radiation: i.is_radiation,
      }))
      // Auto-select first item
      if (poItems.value.length === 1) {
        selectItem(poItems.value[0])
      }
    } else {
      error.value = res.error ?? 'Không tìm thấy PO'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Lỗi khi tra cứu PO'
  } finally {
    poLoading.value = false
  }
}

function selectItem(item: { item_code: string; is_radiation: boolean }) {
  form.value.master_item = item.item_code
  form.value.is_radiation_device = item.is_radiation ? 1 : 0
}

// ─── Submit ──────────────────────────────────────────────────────────────────

async function handleCreate() {
  // Basic validation
  const required = ['po_reference', 'master_item', 'vendor', 'clinical_dept', 'expected_installation_date', 'vendor_serial_no'] as const
  const missing = required.filter((f) => !form.value[f])
  if (missing.length) {
    error.value = `Vui lòng điền các trường: ${missing.join(', ')}`
    return
  }

  loading.value = true
  error.value = null

  const name = await store.createDoc({
    ...form.value,
    commissioning_documents: documents.value,
    baseline_tests: baselines.value,
  })

  loading.value = false

  if (name) {
    router.push(`/commissioning/${name}`)
  } else {
    error.value = store.error ?? 'Không thể tạo phiếu'
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto p-6 space-y-6">
    <!-- Breadcrumbs -->
    <nav class="text-sm text-gray-500 flex items-center gap-2">
      <router-link to="/dashboard" class="hover:text-blue-600">Dashboard</router-link>
      <span>/</span>
      <router-link to="/commissioning" class="hover:text-blue-600">Danh sách</router-link>
      <span>/</span>
      <span class="text-gray-800 font-medium">Tạo phiếu mới</span>
    </nav>

    <div class="card">
      <h1 class="text-xl font-bold text-gray-900 mb-6">Tạo Phiếu Tiếp Nhận Thiết Bị Mới (IMM-04)</h1>

      <!-- Error -->
      <div v-if="error" class="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
        {{ error }}
      </div>

      <form class="space-y-8" @submit.prevent="handleCreate">
        <!-- Section: Mua sắm -->
        <div>
          <h3 class="text-base font-semibold text-gray-900 pb-2 border-b mb-4">Thông tin Mua sắm</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="form-label">Lệnh mua hàng (PO) *</label>
              <div class="flex gap-2">
                <input
                  v-model="form.po_reference"
                  type="text"
                  class="form-input flex-1"
                  placeholder="PO-2026-0041"
                />
                <button type="button" class="btn-secondary px-3" :disabled="poLoading" @click="lookupPO">
                  {{ poLoading ? '...' : 'Tra cứu' }}
                </button>
              </div>
            </div>
            <div>
              <label class="form-label">Nhà cung cấp *</label>
              <input v-model="form.vendor" type="text" class="form-input" placeholder="Tự điền khi chọn PO" />
            </div>
            <div>
              <label class="form-label">Model Thiết bị *</label>
              <div v-if="poItems.length > 1" class="space-y-2">
                <button
                  v-for="item in poItems"
                  :key="item.item_code"
                  type="button"
                  class="w-full text-left px-3 py-2 rounded border text-sm"
                  :class="form.master_item === item.item_code ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300'"
                  @click="selectItem(item)"
                >
                  {{ item.item_code }} — {{ item.item_name }}
                  <span v-if="item.is_radiation" class="text-yellow-600 text-xs ml-2">(Bức xạ)</span>
                </button>
              </div>
              <input v-else v-model="form.master_item" type="text" class="form-input" placeholder="Mã Model" />
            </div>
            <div>
              <label class="form-label">Khoa / Phòng nhận *</label>
              <input v-model="form.clinical_dept" type="text" class="form-input" placeholder="ICU - M" />
            </div>
            <div>
              <label class="form-label">Ngày hẹn lắp đặt *</label>
              <input v-model="form.expected_installation_date" type="date" class="form-input" />
            </div>
            <div>
              <label class="form-label">Serial Number Hãng *</label>
              <input v-model="form.vendor_serial_no" type="text" class="form-input font-mono" placeholder="VNT-PHL-20260001" />
            </div>
          </div>
        </div>

        <!-- Section: Hồ sơ đi kèm -->
        <div>
          <h3 class="text-base font-semibold text-gray-900 pb-2 border-b mb-4">Hồ sơ đi kèm</h3>
          <div class="space-y-2">
            <div
              v-for="(doc, i) in documents"
              :key="i"
              class="flex items-center gap-3 p-3 rounded-lg border"
              :class="doc.status === 'Received' ? 'bg-green-50 border-green-200' : 'bg-white border-gray-200'"
            >
              <button
                type="button"
                class="w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0"
                :class="doc.status === 'Received' ? 'bg-green-500 border-green-500 text-white' : 'border-gray-300'"
                @click="doc.status = doc.status === 'Received' ? 'Pending' : 'Received'"
              >
                <svg v-if="doc.status === 'Received'" class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                </svg>
              </button>
              <span class="text-sm">{{ doc.doc_type }}</span>
              <span
                class="text-xs px-2 py-0.5 rounded-full ml-auto"
                :class="doc.status === 'Received' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'"
              >
                {{ doc.status === 'Received' ? 'Đã nhận' : 'Chưa nhận' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Flags -->
        <div class="flex gap-4">
          <label class="flex items-center gap-2">
            <input
              type="checkbox"
              :checked="Boolean(form.is_radiation_device)"
              class="rounded text-yellow-600"
              @change="form.is_radiation_device = ($event.target as HTMLInputElement).checked ? 1 : 0"
            />
            <span class="text-sm text-gray-700">Thiết bị phát bức xạ / tia X</span>
          </label>
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-3 pt-4 border-t">
          <router-link to="/commissioning" class="btn-secondary px-4 py-2">Hủy</router-link>
          <button type="submit" class="btn-primary px-6 py-2" :disabled="loading">
            <svg v-if="loading" class="w-4 h-4 animate-spin mr-1" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {{ loading ? 'Đang tạo...' : 'Tạo Phiếu Tiếp Nhận' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
