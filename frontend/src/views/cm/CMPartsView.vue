<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm09Store } from '@/stores/imm09'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'
import type { SparePartRow, SparePartSuggestion } from '@/api/imm09'

const props = defineProps<{ id: string }>()
const store = useImm09Store()
const router = useRouter()
const notify = useNotify()

// Local editable copy of parts
const parts = ref<SparePartRow[]>([])
const submitting = ref(false)
const startingRepair = ref(false)
const error = ref<string | null>(null)

// Search state
const searchQuery = ref('')
// CR-73(a): kết quả tìm kiếm là GỢI Ý (13 khoá) — khác dòng phiếu `SparePartRow`.
const searchResults = ref<SparePartSuggestion[]>([])
const searchLoading = ref(false)
const showDropdown = ref(false)
let searchDebounce: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  if (!store.currentWO || store.currentWO.name !== props.id) {
    await store.fetchWorkOrder(props.id)
  }
  if (store.currentWO) {
    parts.value = store.currentWO.spare_parts_used.map(p => ({ ...p }))
  }
})

const totalCost = computed(() =>
  parts.value.reduce((sum, p) => sum + (p.unit_cost * p.qty || 0), 0)
)

function onSearchInput() {
  if (searchDebounce) clearTimeout(searchDebounce)
  if (searchQuery.value.length < 2) {
    searchResults.value = []
    showDropdown.value = false
    return
  }
  searchDebounce = setTimeout(async () => {
    searchLoading.value = true
    try {
      searchResults.value = await store.doSearchSpareParts(searchQuery.value)
      showDropdown.value = searchResults.value.length > 0
    } catch {
      searchResults.value = []
    } finally {
      searchLoading.value = false
    }
  }, 300)
}

function addPart(part: SparePartSuggestion) {
  const existing = parts.value.find(p => p.item_code === part.item_code)
  if (existing) {
    existing.qty += 1
    existing.total_cost = existing.qty * existing.unit_cost
    // Bồi khoá THẬT nếu dòng cũ chưa có (dòng nạp từ phiếu không mang `spare_part`).
    if (!existing.spare_part && part.spare_part) existing.spare_part = part.spare_part
  } else {
    // Map GỢI Ý → dòng phiếu: chỉ các field của child `spare_parts_used`
    // + `spare_part` (khoá tra kho, FE-only) — KHÔNG spread cả gợi ý.
    parts.value.push({
      idx: parts.value.length + 1,
      item_code: part.item_code,
      item_name: part.item_name,
      manufacturer_part_no: part.manufacturer_part_no,
      qty: 1,
      uom: part.uom,
      unit_cost: part.unit_cost,
      total_cost: part.unit_cost,
      stock_entry_ref: '',
      notes: '',
      spare_part: part.spare_part,
    })
  }
  searchQuery.value = ''
  searchResults.value = []
  showDropdown.value = false
}

function removePart(idx: number) {
  parts.value = parts.value.filter(p => p.idx !== idx)
  // Re-index
  parts.value.forEach((p, i) => { p.idx = i + 1 })
}

function onQtyChange(part: SparePartRow) {
  part.total_cost = part.qty * part.unit_cost
}

function blurDropdown() { setTimeout(() => { showDropdown.value = false }, 150) }

function stockEntryStatus(part: SparePartRow): 'valid' | 'empty' {
  return part.stock_entry_ref?.trim() ? 'valid' : 'empty'
}

async function handleSaveParts() {
  submitting.value = true
  error.value = null
  const ok = await store.doSaveParts(props.id, parts.value)
  submitting.value = false
  if (ok) {
    notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: 'vật tư sử dụng' } })
  } else {
    notify.fromError(store.lastApiError)
    error.value = store.error ?? 'Không thể lưu vật tư'
  }
}

async function handleStartRepair() {
  startingRepair.value = true
  error.value = null
  const ok = await store.doStartRepair(props.id)
  startingRepair.value = false
  if (ok) {
    notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: 'bắt đầu sửa chữa' } })
    router.push(`/cm/work-orders/${props.id}`)
  } else {
    notify.fromError(store.lastApiError)
    error.value = store.error ?? 'Không thể bắt đầu sửa chữa'
  }
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <button
        class="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
        @click="router.push(`/cm/work-orders/${id}`)"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest">Vật tư</p>
        <h1 class="text-xl font-bold text-slate-900">Vật tư sửa chữa — {{ id }}</h1>
      </div>
    </div>

    <!-- Error banner -->
    <Transition name="fade">
      <div v-if="error" class="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
        {{ error }}
      </div>
    </Transition>

    <div class="space-y-5">
      <!-- Search combobox -->
      <div class="card">
        <label class="block text-sm font-semibold text-slate-700 mb-2">Tìm vật tư</label>
        <div class="relative">
          <div class="relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="8" /><path stroke-linecap="round" d="m21 21-4.35-4.35" />
            </svg>
            <input
              v-model="searchQuery"
              type="text"
              class="form-input pl-9"
              placeholder="Tìm theo mã hoặc tên vật tư..."
              @input="onSearchInput"
              @blur="blurDropdown"
              @focus="showDropdown = searchResults.length > 0"
            />
            <span v-if="searchLoading" class="absolute right-3 top-1/2 -translate-y-1/2">
              <svg class="animate-spin w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
              </svg>
            </span>
          </div>
          <!-- Dropdown results -->
          <Transition name="fade">
            <div v-if="showDropdown" class="absolute z-20 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden">
              <button
                v-for="item in searchResults"
                :key="`${item.spare_part || item.item_code}|${item.device_model ?? ''}`"
                class="w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-slate-50 transition-colors text-left"
                @mousedown.prevent="addPart(item)"
              >
                <div>
                  <span class="font-medium text-slate-800">{{ item.item_name }}</span>
                  <span class="text-xs text-slate-400 font-mono ml-2">{{ item.manufacturer_part_no || item.item_code }}</span>
                  <span v-if="item.device_model_name || item.device_model" class="block text-xs text-slate-500">
                    Model thiết bị: {{ item.device_model_name || item.device_model }}
                  </span>
                </div>
                <span class="text-xs text-slate-500">{{ item.unit_cost?.toLocaleString('vi-VN') }}đ / {{ item.uom }}</span>
              </button>
            </div>
          </Transition>
        </div>
      </div>

      <!-- Parts table -->
      <div class="card p-0 overflow-x-auto">
        <div class="px-5 py-4 border-b border-slate-100">
          <h3 class="text-sm font-semibold text-slate-800">
            Danh sách vật tư
            <span class="ml-1 text-xs font-normal text-slate-400">({{ parts.length }} mục)</span>
          </h3>
        </div>

        <div v-if="parts.length === 0" class="px-5 py-10 text-center text-sm text-slate-400">
          Chưa có vật tư nào. Tìm và thêm vật tư bên trên.
        </div>

        <div v-else>
          <table class="min-w-full divide-y divide-slate-100">
            <thead class="bg-slate-50">
              <tr>
                <th class="table-header">#</th>
                <th class="table-header">Vật tư</th>
                <th class="table-header w-20">Số lượng</th>
                <th class="table-header w-24">Đơn giá</th>
                <th class="table-header w-28">Thành tiền</th>
                <th class="table-header">Phiếu XK</th>
                <th class="table-header w-10"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-50">
              <tr
                v-for="part in parts"
                :key="part.idx"
                class="transition-colors hover:bg-slate-50"
              >
                <td class="table-cell text-xs text-slate-400 w-10">{{ part.idx }}</td>
                <td class="table-cell">
                  <div class="font-medium text-slate-800 text-sm">{{ part.item_name }}</div>
                  <div class="text-xs text-slate-400 font-mono">{{ part.item_code }}</div>
                </td>
                <td class="table-cell">
                  <input
                    v-model.number="part.qty"
                    type="number"
                    min="1"
                    class="w-16 border border-slate-300 rounded px-2 py-1 text-sm text-center"
                    @change="onQtyChange(part)"
                  />
                </td>
                <td class="table-cell text-sm text-slate-600 text-right">
                  {{ part.unit_cost?.toLocaleString('vi-VN') }}đ
                </td>
                <td class="table-cell text-sm font-medium text-slate-800 text-right">
                  {{ (part.qty * part.unit_cost)?.toLocaleString('vi-VN') }}đ
                </td>
                <td class="table-cell">
                  <div class="flex items-center gap-1.5">
                    <input
                      v-model="part.stock_entry_ref"
                      type="text"
                      :class="[
                        'flex-1 border rounded px-2 py-1 text-xs font-mono transition-colors',
                        stockEntryStatus(part) === 'valid'
                          ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                          : 'border-slate-300'
                      ]"
                      placeholder="STE-2026-XXXXX"
                    />
                    <span v-if="stockEntryStatus(part) === 'valid'" class="text-emerald-600 text-xs font-semibold shrink-0">Đã xuất</span>
                    <span v-else class="text-amber-600 text-xs font-semibold shrink-0">Chưa xuất</span>
                  </div>
                </td>
                <td class="table-cell">
                  <button
                    class="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                    @click="removePart(part.idx)"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
            <tfoot class="bg-slate-50 border-t border-slate-200">
              <tr>
                <td colspan="4" class="px-4 py-3 text-sm font-semibold text-slate-600 text-right">
                  Tổng chi phí vật tư:
                </td>
                <td class="px-4 py-3 text-sm font-bold text-slate-900 text-right">
                  {{ totalCost.toLocaleString('vi-VN') }} VNĐ
                </td>
                <td colspan="2" class="px-4 py-3"></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <!-- BR note -->
        <div class="px-5 py-3 border-t border-slate-100 bg-amber-50">
          <p class="text-xs text-amber-700">
            Tất cả vật tư phải có phiếu xuất kho (BR-09-02)
          </p>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex justify-between items-center pt-2 pb-6">
        <button
          class="px-5 py-2.5 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          @click="router.push(`/cm/work-orders/${id}`)"
        >
          Quay lại
        </button>
        <div class="flex gap-3">
          <button
            :disabled="submitting"
            :class="[
              'px-5 py-2.5 rounded-lg text-sm font-medium border transition-colors',
              submitting ? 'border-slate-200 text-slate-400 cursor-not-allowed' : 'border-blue-300 text-blue-600 hover:bg-blue-50'
            ]"
            @click="handleSaveParts"
          >
            {{ submitting ? 'Đang lưu...' : 'Lưu vật tư' }}
          </button>
          <button
            :disabled="startingRepair"
            :class="[
              'px-5 py-2.5 rounded-lg text-sm font-medium text-white transition-colors',
              startingRepair ? 'bg-green-300 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700 shadow-sm'
            ]"
            @click="handleStartRepair"
          >
            {{ startingRepair ? 'Đang xử lý...' : 'Bắt đầu sửa chữa' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active { transition: all 0.3s ease-out; }
.slide-up-enter-from { transform: translateY(8px); opacity: 0; }
</style>
