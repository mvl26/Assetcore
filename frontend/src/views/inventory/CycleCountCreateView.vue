<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-15 · Tạo phiếu kiểm kê tồn kho (Cycle Count). Planned khi tạo.
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm15Store } from '@/stores/imm15'
import { createCycleCount } from '@/api/imm15'
import { listWarehouses, listStockLevels, searchParts } from '@/api/inventory'
import type { Warehouse, SparePart } from '@/types/inventory'
import PageHeader from '@/components/common/PageHeader.vue'
import { useApi } from '@/composables/useApi'
import { useNotify } from '@/composables/useNotify'
import { CYCLE_COUNT_TYPE_OPTIONS } from '@/constants/cycleCountLabels'

const router = useRouter()
const store = useImm15Store()
const api = useApi()
const notify = useNotify()

const warehouse = ref('')
const countType = ref('Cycle')
const warehouses = ref<Warehouse[]>([])

// Optional spare-part chips (multi-add). Empty ⇒ kiểm kê toàn bộ phụ tùng của kho.
interface PartChip { name: string; label: string }
const selectedParts = ref<PartChip[]>([])
const partQuery = ref('')
const partResults = ref<SparePart[]>([])
const searching = ref(false)

const formErrors = ref<Record<string, string>>({})
const submitting = ref(false)

const canSubmit = computed(() => Boolean(warehouse.value) && Boolean(countType.value))

async function onSearchParts() {
  const q = partQuery.value.trim()
  if (q.length < 2) { partResults.value = []; return }
  searching.value = true
  try {
    partResults.value = await searchParts(q, 8, warehouse.value)
  } catch { partResults.value = [] }
  finally { searching.value = false }
}

function addPart(p: SparePart) {
  if (!selectedParts.value.some(x => x.name === p.name))
    selectedParts.value.push({ name: p.name, label: p.part_name || p.name })
  partQuery.value = ''
  partResults.value = []
}
function removePart(name: string) {
  selectedParts.value = selectedParts.value.filter(x => x.name !== name)
}

async function resolveSpareParts(): Promise<string[]> {
  if (selectedParts.value.length) return selectedParts.value.map(p => p.name)
  // Empty selection ⇒ snapshot toàn bộ phụ tùng đang có tồn ở kho đã chọn.
  const r = await listStockLevels({ warehouse: warehouse.value, page: 1, page_size: 500 })
  const names = Array.from(new Set((r?.items || []).map(s => s.spare_part).filter(Boolean)))
  return names
}

async function submit() {
  formErrors.value = {}
  if (!warehouse.value) { formErrors.value.warehouse = 'Vui lòng chọn kho kiểm kê'; return }
  submitting.value = true
  try {
    const spare_parts = await resolveSpareParts()
    if (!spare_parts.length) {
      formErrors.value.spare_parts =
        'Kho này chưa có phụ tùng nào để kiểm kê. Vui lòng chọn phụ tùng cụ thể.'
      return
    }
    const res = await api.run(
      () => createCycleCount({ warehouse: warehouse.value, count_type: countType.value, spare_parts }),
      {
        successMessage: 'Đã tạo phiếu kiểm kê (trạng thái: Đã lập kế hoạch)',
        onFieldError: (fields) => { formErrors.value = { ...formErrors.value, ...fields } },
      },
    )
    if (res) {
      store.fetchCycleCounts()  // refresh danh sách để phiếu mới nằm đầu
      router.push({ name: 'CycleCountDetail', params: { name: res.name } })
    }
  } catch (e: unknown) {
    notify.fromError(e)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const r = await listWarehouses({ page: 1, page_size: 100, active_only: 1 })
    warehouses.value = r?.items || []
  } catch { /* form 0-state xử lý bên dưới */ }
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Tạo phiếu kiểm kê tồn kho"
      subtitle="IMM-15 · Tồn kho phụ tùng — Phiếu mới ở trạng thái Đã lập kế hoạch"
      :breadcrumb="[
        { label: 'IMM-15 · Tồn kho phụ tùng', to: '/inventory' },
        { label: 'Kiểm kê tồn kho', to: '/inventory/cycle-counts' },
        { label: 'Tạo phiếu' },
      ]"
    />

    <div class="card max-w-2xl p-6 space-y-5">
      <!-- 0-state: chưa có kho hoạt động -->
      <div v-if="warehouses.length === 0" class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        <p class="font-medium">Chưa có kho hoạt động.</p>
        <p class="mt-1">Cần khai báo ít nhất một kho trước khi tạo phiếu kiểm kê.</p>
        <button class="btn-secondary mt-3" @click="router.push('/warehouses')">Đi tới danh sách kho</button>
      </div>

      <template v-else>
        <div class="form-group">
          <label class="form-label" for="cc-warehouse">Kho kiểm kê <span class="text-red-500">*</span></label>
          <select id="cc-warehouse" v-model="warehouse" class="form-select"
                  :aria-invalid="Boolean(formErrors.warehouse)"
                  :aria-describedby="formErrors.warehouse ? 'cc-warehouse-err' : undefined">
            <option value="">— Chọn kho —</option>
            <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name }}</option>
          </select>
          <p v-if="formErrors.warehouse" id="cc-warehouse-err" class="text-xs text-red-600 mt-1">{{ formErrors.warehouse }}</p>
        </div>

        <div class="form-group">
          <label class="form-label" for="cc-type">Loại kiểm kê <span class="text-red-500">*</span></label>
          <select id="cc-type" v-model="countType" class="form-select">
            <option v-for="o in CYCLE_COUNT_TYPE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label" for="cc-part-search">Phụ tùng kiểm kê <span class="text-slate-400 font-normal">(tùy chọn)</span></label>
          <p class="text-xs text-slate-500 mb-2">Để trống ⇒ kiểm kê toàn bộ phụ tùng đang có tồn ở kho.</p>

          <div v-if="selectedParts.length" class="flex flex-wrap gap-2 mb-2">
            <span v-for="p in selectedParts" :key="p.name" class="inline-flex items-center gap-1 rounded-full bg-emerald-50 text-emerald-700 px-2.5 py-1 text-xs">
              {{ p.label }}
              <button type="button" class="hover:text-emerald-900 focus-visible:ring-2 focus-visible:ring-emerald-500 rounded"
                      :aria-label="`Bỏ ${p.label}`" @click="removePart(p.name)">×</button>
            </span>
          </div>

          <input
            id="cc-part-search"
            v-model="partQuery"
            type="text"
            class="form-input"
            placeholder="Tìm phụ tùng theo mã hoặc tên…"
            :disabled="!warehouse"
            @input="onSearchParts"
          />
          <p v-if="formErrors.spare_parts" class="text-xs text-red-600 mt-1">{{ formErrors.spare_parts }}</p>
          <ul v-if="partResults.length" class="mt-1 border border-slate-200 rounded-lg divide-y divide-slate-100 max-h-56 overflow-y-auto">
            <li v-for="p in partResults" :key="p.name">
              <button type="button" data-testid="cc-part-result" class="w-full text-left px-3 py-2 text-sm hover:bg-slate-50 focus-visible:bg-slate-50"
                      @click="addPart(p)">
                <span class="font-medium text-slate-800">{{ p.part_name || p.name }}</span>
                <span class="text-xs text-slate-400 ml-2 font-mono">{{ p.part_code || p.name }}</span>
              </button>
            </li>
          </ul>
          <p v-else-if="searching" class="text-xs text-slate-400 mt-1">Đang tìm…</p>
        </div>

        <div class="flex items-center justify-end gap-3 pt-2">
          <button type="button" class="btn-secondary" @click="router.push({ name: 'CycleCountList' })">Hủy</button>
          <button type="button" data-testid="cc-submit" class="btn-primary" :disabled="!canSubmit || submitting" @click="submit">
            {{ submitting ? 'Đang tạo…' : 'Tạo phiếu kiểm kê' }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
