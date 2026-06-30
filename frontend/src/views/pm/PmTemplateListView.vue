<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import DateInput from '@/components/common/DateInput.vue'
import { ref, computed, onMounted } from 'vue'
import {
  listPmTemplates, getPmTemplate, createPmTemplate, updatePmTemplate, deletePmTemplate,
  applyPmTemplateToCategory,
  type PmTemplate, type PmChecklistItem,
} from '@/api/imm00'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import { translatePmType } from '@/utils/formatters'
const toast = useToast()

const items = ref<PmTemplate[]>([])
const total = ref(0)
const loading = ref(false)
const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<Partial<PmTemplate> & { checklist_items: PmChecklistItem[] }>({
  checklist_items: [],
})
const err = ref('')

// Filter state
const showFilters = ref(false)
const filters = ref({ pm_type: '', asset_category: '', search: '' })

const PM_TYPES = ['Quarterly', 'Semi-Annual', 'Annual', 'Ad-hoc']
// Nhãn pm_type: dùng SSoT translatePmType (@/utils/formatters) — không map cục bộ.

interface FilterChip { key: 'pm_type' | 'asset_category' | 'search'; label: string }
const filteredItems = computed(() => {
  let arr = items.value
  if (filters.value.pm_type) arr = arr.filter(t => t.pm_type === filters.value.pm_type)
  if (filters.value.asset_category) {
    const q = filters.value.asset_category.toLowerCase()
    arr = arr.filter(t => (t.asset_category || '').toLowerCase().includes(q))
  }
  if (filters.value.search.trim()) {
    const q = filters.value.search.trim().toLowerCase()
    arr = arr.filter(t =>
      (t.name || '').toLowerCase().includes(q)
      || (t.template_name || '').toLowerCase().includes(q)
      || (t.display_template_name || '').toLowerCase().includes(q)
      || (t.version || '').toLowerCase().includes(q),
    )
  }
  return arr
})
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.pm_type) chips.push({ key: 'pm_type', label: translatePmType(filters.value.pm_type) })
  if (filters.value.asset_category) chips.push({ key: 'asset_category', label: `Danh mục: ${filters.value.asset_category}` })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)
function quickFilter(key: 'pm_type' | 'asset_category', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  showFilters.value = false
}
function clearChip(key: string) { (filters.value as Record<string, string>)[key] = '' }
function resetFilters() { filters.value = { pm_type: '', asset_category: '', search: '' } }

function newItem(): PmChecklistItem {
  return {
    description: '',
    measurement_type: 'Pass/Fail',
    unit: '',
    expected_min: null,
    expected_max: null,
    is_critical: 0,
    reference_section: '',
  }
}

async function load() {
  loading.value = true
  try {
    const r = await listPmTemplates()
    const d = r as unknown as { data: PmTemplate[]; pagination: { total: number } }
    if (d) { items.value = d.data || []; total.value = d.pagination?.total || 0 }
  } finally { loading.value = false }
}

function openCreate() {
  editingName.value = null
  form.value = {
    template_name: '', asset_category: '', pm_type: 'Quarterly',
    version: '1.0', effective_date: new Date().toISOString().slice(0, 10),
    checklist_items: [newItem()],
  }
  err.value = ''; showForm.value = true
}

async function openEdit(name: string) {
  editingName.value = name
  const r = await getPmTemplate(name)
  const d = r as unknown as PmTemplate
  if (d) form.value = { ...d, checklist_items: (d.checklist_items as PmChecklistItem[]) || [] }
  if (!form.value.checklist_items.length) form.value.checklist_items = [newItem()]
  err.value = ''; showForm.value = true
}

function addItem() { form.value.checklist_items.push(newItem()) }
function removeItem(i: number) { form.value.checklist_items.splice(i, 1) }

async function save() {
  err.value = ''
  if (!form.value.template_name || !form.value.asset_category || !form.value.pm_type) {
    err.value = 'Tên mẫu, Danh mục tài sản, Loại bảo trì là bắt buộc'
    return
  }
  const cleanItems = form.value.checklist_items
    .filter(it => (it.description || '').trim())
    .map(it => ({
      description: it.description.trim(),
      measurement_type: it.measurement_type || 'Pass/Fail',
      unit: it.unit || '',
      expected_min: it.expected_min ?? null,
      expected_max: it.expected_max ?? null,
      is_critical: it.is_critical ? 1 : 0,
      reference_section: it.reference_section || '',
    }))
  if (cleanItems.length === 0) { err.value = 'Phải có ít nhất 1 hạng mục checklist'; return }

  try {
    const payload = {
      template_name: form.value.template_name,
      asset_category: form.value.asset_category,
      pm_type: form.value.pm_type,
      version: form.value.version,
      effective_date: form.value.effective_date,
      checklist_items: JSON.stringify(cleanItems),
    } as unknown as Partial<PmTemplate>
    if (editingName.value) await updatePmTemplate(editingName.value, payload)
    else await createPmTemplate(payload)
    showForm.value = false; await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
}

async function remove(name: string) {
  if (!confirm(`Xóa template "${name}"?`)) return
  try { await deletePmTemplate(name); await load() }
  catch (e: unknown) { toast.error((e as Error).message || 'Không thể xóa') }
}

const applying = ref(false)
async function applyToCategoryAssets() {
  if (!editingName.value) return
  const cat = form.value.asset_category
  if (!cat) { toast.error('Danh mục tài sản chưa chọn'); return }
  const msg = `Tạo PM Schedule cho mọi thiết bị thuộc danh mục "${cat}" theo template "${editingName.value}"?\n\n`
    + 'Thiết bị đã có lịch cùng loại PM sẽ được giữ nguyên.'
  if (!confirm(msg)) return
  applying.value = true
  try {
    const r = await applyPmTemplateToCategory(editingName.value)
    toast.success(
      `Đã tạo ${r.created} lịch trên ${r.total_assets} thiết bị. `
      + `Bỏ qua ${r.skipped_existing} (đã có lịch). Lỗi: ${r.errors}.`,
    )
  } catch (e: unknown) {
    toast.error((e as Error).message || 'Không thể áp dụng template')
  } finally {
    applying.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Template checklist PM"
      :subtitle="`Tổng ${total} template`"
      :breadcrumb="[{ label: 'IMM-08 · Bảo trì', to: '/pm/dashboard' }, { label: 'Template PM' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm template
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="filters.search"
      search-placeholder="Tìm theo mã, tên template, phiên bản..."
      @reset="resetFilters"
      @clear-chip="clearChip"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Loại PM</label>
          <select v-model="filters.pm_type" class="form-select">
            <option value="">Tất cả loại PM</option>
            <option v-for="t in PM_TYPES" :key="t" :value="t">{{ translatePmType(t) }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Danh mục tài sản</label>
          <SmartSelect v-model="filters.asset_category" doctype="AC Asset Category" placeholder="Chọn danh mục..." />
        </div>
      </template>
    </ListFilterBar>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span v-if="activeFilterCount > 0">
          Kết quả lọc: <strong class="text-slate-700">{{ filteredItems.length }}</strong> / {{ total }} template
        </span>
        <span v-else>
          Hiển thị <strong class="text-slate-700">{{ filteredItems.length }}</strong> / {{ total }} template
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="filteredItems.length === 0" class="text-center text-slate-400 py-12 text-sm">
        {{ activeFilterCount > 0 ? 'Không có template nào phù hợp.' : 'Chưa có template.' }}
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="t in filteredItems"
            :key="t.name"
            class="mobile-card cursor-pointer"
            @click="openEdit(t.name)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ t.name }}</span>
              <span
                v-if="t.pm_type"
                class="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-700"
              >{{ translatePmType(t.pm_type) }}</span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ t.display_template_name || t.template_name }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="t.asset_category">{{ t.category_name || t.asset_category }}</span>
              <span>· v{{ t.version || '—' }}</span>
            </div>
            <div class="mt-2 flex gap-2">
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click.stop="openEdit(t.name)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click.stop="remove(t.name)">Xóa</button>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <table class="hidden sm:table w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Tên template</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Danh mục tài sản</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Loại PM</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Phiên bản</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Hiệu lực</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="t in filteredItems" :key="t.name" class="hover:bg-slate-50">
            <td class="px-4 py-3 font-mono text-xs text-slate-500">
              <button class="hover:text-blue-600 hover:underline" @click="openEdit(t.name)">{{ t.name }}</button>
            </td>
            <td class="px-4 py-3 font-medium text-slate-800">
              <button class="text-left hover:text-blue-600 hover:underline decoration-dotted underline-offset-2" @click="openEdit(t.name)">
                {{ t.display_template_name || t.template_name }}
              </button>
            </td>
            <td class="px-4 py-3">
              <button
                v-if="t.asset_category"
                class="text-left text-slate-700 hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                :title="t.asset_category"
                @click="quickFilter('asset_category', t.asset_category!)"
              >{{ t.category_name || t.asset_category }}</button>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="px-4 py-3">
              <button
                v-if="t.pm_type"
                class="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-700 hover:ring-2 hover:ring-slate-400"
                :title="`Lọc: ${translatePmType(t.pm_type)}`"
                @click="quickFilter('pm_type', t.pm_type!)"
              >{{ translatePmType(t.pm_type) }}</button>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="px-4 py-3 text-slate-600">{{ t.version || '—' }}</td>
            <td class="px-4 py-3 text-xs text-slate-600">{{ t.effective_date || '—' }}</td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="openEdit(t.name)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="remove(t.name)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
      </template>
    </div>

    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 overflow-y-auto py-6" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-[860px] max-w-full space-y-4 my-auto">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} Template Checklist PM</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label class="sm:col-span-2 block">
            <span class="block text-sm font-medium text-slate-700 mb-1">Tên template *</span>
            <input v-model="form.template_name" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          </label>
          <label class="block">
            <span class="block text-sm font-medium text-slate-700 mb-1">Danh mục tài sản *</span>
            <SmartSelect v-model="(form.asset_category as string)" doctype="AC Asset Category" placeholder="Chọn danh mục..." />
            <span class="block text-[11px] text-slate-400 mt-1">
              Mọi tài sản thuộc danh mục này sẽ áp dụng template khi tạo PM Schedule.
            </span>
          </label>
          <label class="block">
            <span class="block text-sm font-medium text-slate-700 mb-1">Loại bảo trì *</span>
            <select v-model="form.pm_type" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
              <option value="Quarterly">Hàng quý</option>
              <option value="Semi-Annual">Nửa năm</option>
              <option value="Annual">Hàng năm</option>
              <option value="Ad-hoc">Đột xuất</option>
            </select>
          </label>
          <label class="block">
            <span class="block text-sm font-medium text-slate-700 mb-1">Phiên bản</span>
            <input v-model="form.version" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          </label>
          <label class="block">
            <span class="block text-sm font-medium text-slate-700 mb-1">Ngày hiệu lực</span>
            <DateInput v-model="form.effective_date" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          </label>
        </div>

        <div class="border-t pt-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-slate-700">Hạng mục kiểm tra *</span>
            <button type="button" class="text-blue-600 text-xs font-medium" @click="addItem">+ Thêm hạng mục</button>
          </div>
          <div class="space-y-2">
            <div v-for="(it, i) in form.checklist_items" :key="i" class="grid grid-cols-12 gap-2 items-center">
              <input v-model="it.description" placeholder="Mô tả *" class="col-span-4 border border-slate-300 rounded px-2 py-1.5 text-sm" />
              <select v-model="it.measurement_type" class="col-span-2 border border-slate-300 rounded px-2 py-1.5 text-sm">
                <option>Pass/Fail</option><option>Numeric</option><option>Text</option>
              </select>
              <input v-model="it.unit" placeholder="Đơn vị" class="col-span-1 border border-slate-300 rounded px-2 py-1.5 text-sm" />
              <input v-model.number="it.expected_min" type="number" placeholder="Tối thiểu" class="col-span-1 border border-slate-300 rounded px-2 py-1.5 text-sm" />
              <input v-model.number="it.expected_max" type="number" placeholder="Tối đa" class="col-span-1 border border-slate-300 rounded px-2 py-1.5 text-sm" />
              <label class="col-span-2 flex items-center gap-1 text-xs text-slate-600">
                <input v-model="it.is_critical" type="checkbox" /> Trọng yếu
              </label>
              <button type="button" class="col-span-1 text-red-500 hover:text-red-700" aria-label="Xoá mục" @click="removeItem(i)">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
          </div>
        </div>

        <div v-if="editingName" class="pt-2 border-t">
          <button
            :disabled="applying || !form.asset_category"
            class="w-full text-xs px-3 py-2 rounded-lg border border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 disabled:opacity-50 transition-colors"
            @click="applyToCategoryAssets"
          >
            {{ applying ? 'Đang áp dụng...' : '🔄 Tạo PM Schedule cho mọi thiết bị thuộc danh mục này' }}
          </button>
          <p class="text-[10px] text-slate-500 mt-1 text-center">
            Thiết bị đã có lịch cùng loại PM sẽ được giữ nguyên (bảo vệ lịch hiện hữu).
          </p>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button class="px-4 py-2 text-sm border border-slate-300 rounded-lg" @click="showForm = false">Hủy</button>
          <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg" @click="save">Lưu</button>
        </div>
      </div>
    </div>
  </div>
</template>
