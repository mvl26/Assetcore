<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Quy tắc tuân thủ (Compliance Rules) — list / create / deactivate.
import { ref, computed, onMounted } from 'vue'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import { createRule, updateRule, deactivateRule } from '@/api/imm16'
import type { ComplianceRule, FindingSeverity } from '@/api/imm16'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'

const store = useImm16Store()
const api = useApi()

const items = computed(() => store.rules)
const pagination = computed(() => store.rulesPagination)
const loading = computed(() => store.rulesLoading)

const showFilters = ref(false)
const filterActive = ref<'' | '1' | '0'>('')
const filterCategory = ref('')
const filterSeverity = ref<'' | FindingSeverity>('')

const SEVERITY_LABELS: Record<string, string> = {
  Low: 'Thấp', Medium: 'Trung bình', High: 'Cao', Critical: 'Nghiêm trọng',
}

const chips = computed(() => {
  const c: { key: string; label: string }[] = []
  if (filterActive.value !== '') c.push({ key: 'active', label: filterActive.value === '1' ? 'Đang áp dụng' : 'Ngừng áp dụng' })
  if (filterCategory.value) c.push({ key: 'category', label: `Nhóm: ${filterCategory.value}` })
  if (filterSeverity.value) c.push({ key: 'severity', label: `Mức: ${SEVERITY_LABELS[filterSeverity.value] ?? filterSeverity.value}` })
  return c
})
const activeFilterCount = computed(() => chips.value.length)

function buildFilters() {
  const f: Record<string, unknown> = {}
  if (filterActive.value !== '') f.is_active = Number(filterActive.value)
  if (filterCategory.value) f.category = filterCategory.value
  if (filterSeverity.value) f.severity = filterSeverity.value
  return f
}

async function load(page = 1) {
  await store.fetchRules(buildFilters(), page, 20)
}

function clearChip(key: string) {
  if (key === 'active') filterActive.value = ''
  else if (key === 'category') filterCategory.value = ''
  else if (key === 'severity') filterSeverity.value = ''
  load(1)
}

function resetFilters() {
  filterActive.value = ''; filterCategory.value = ''; filterSeverity.value = ''
  load(1)
}

// ── Create rule modal ────────────────────────────────────────────────
const showCreate = ref(false)
const formErrors = ref<Record<string, string>>({})
const form = ref<Partial<ComplianceRule>>({
  rule_code: '',
  rule_name: '',
  source_module: '',
  category: '',
  severity: 'Medium',
  evaluation_frequency: 'Daily',
  is_active: 1,
})

function openCreate() {
  form.value = {
    rule_code: '', rule_name: '', source_module: '', category: '',
    severity: 'Medium', evaluation_frequency: 'Daily', is_active: 1,
  }
  formErrors.value = {}
  showCreate.value = true
}

async function submitCreate() {
  formErrors.value = {}
  const res = await api.run(() => createRule(form.value), {
    successMessage: 'Đã tạo quy tắc',
    onFieldError: (f) => (formErrors.value = f),
  })
  if (res) {
    showCreate.value = false
    load(1)
  }
}

async function onDeactivate(rule: ComplianceRule) {
  if (!confirm(`Ngừng áp dụng quy tắc "${rule.rule_name}"?`)) return
  const res = await api.run(() => deactivateRule(rule.name), {
    successMessage: 'Đã ngừng áp dụng',
  })
  if (res) load(pagination.value.page)
}

async function onReactivate(rule: ComplianceRule) {
  const res = await api.run(() => updateRule(rule.name, { is_active: 1 }, 'Re-activate via UI'), {
    successMessage: 'Đã kích hoạt lại',
  })
  if (res) load(pagination.value.page)
}

onMounted(() => load(1))
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Quy tắc tuân thủ"
      :subtitle="`IMM-16 · Theo dõi tuân thủ — Tổng ${pagination.total} quy tắc`"
      :breadcrumb="[{ label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' }, { label: 'Quy tắc' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo quy tắc
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters" :chips="chips" :show-search="false"
      @reset="resetFilters" @clear-chip="clearChip" @apply="load(1)"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filterActive" class="form-select" @change="load(1)">
            <option value="">Tất cả</option>
            <option value="1">Đang áp dụng</option>
            <option value="0">Ngừng áp dụng</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Nhóm</label>
          <input v-model="filterCategory" placeholder="VD: PM, Calibration..." class="form-input" @keyup.enter="load(1)" />
        </div>
        <div class="form-group">
          <label class="form-label">Mức độ</label>
          <select v-model="filterSeverity" class="form-select" @change="load(1)">
            <option value="">Tất cả</option>
            <option value="Low">Thấp</option>
            <option value="Medium">Trung bình</option>
            <option value="High">Cao</option>
            <option value="Critical">Nghiêm trọng</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <div class="table-wrapper">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ items.length }}</strong> / {{ pagination.total }} quy tắc</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-4">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="!items.length" class="flex flex-col items-center justify-center py-16">
        <p class="text-sm text-slate-500">Chưa có quy tắc tuân thủ phù hợp.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
        <button v-else class="btn-primary mt-3" @click="openCreate">Tạo quy tắc đầu tiên</button>
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="r in items"
            :key="r.name"
            class="mobile-card"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ r.rule_code }}</span>
              <StatusBadge :state="r.severity" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ r.rule_name }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="r.category">{{ r.category }}</span>
              <span v-if="r.source_module">· {{ r.source_module }}</span>
              <span
                :class="r.is_active ? 'text-emerald-700' : 'text-slate-400'"
              >· {{ r.is_active ? 'Đang áp dụng' : 'Ngừng' }}</span>
            </div>
            <div class="mt-2 flex gap-2">
              <button v-if="r.is_active" class="text-xs text-red-600 hover:text-red-700 font-medium" @click="onDeactivate(r)">Ngừng áp dụng</button>
              <button v-else class="text-xs text-emerald-600 hover:text-emerald-700 font-medium" @click="onReactivate(r)">Kích hoạt lại</button>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Tên quy tắc</th>
              <th class="table-header">Nhóm</th>
              <th class="table-header">Module nguồn</th>
              <th class="table-header">Mức độ</th>
              <th class="table-header">Tần suất</th>
              <th class="table-header">Phiên bản</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="r in items" :key="r.name" class="hover:bg-slate-50">
              <td class="table-cell">
                <div class="font-medium text-slate-900">{{ r.rule_name }}</div>
                <div class="font-mono text-xs text-brand-700 mt-0.5">{{ r.rule_code }}</div>
              </td>
              <td class="table-cell text-slate-600">{{ r.category || '—' }}</td>
              <td class="table-cell text-slate-600">{{ r.source_module || '—' }}</td>
              <td class="table-cell">
                <StatusBadge :state="r.severity" />
              </td>
              <td class="table-cell text-slate-600">{{ r.evaluation_frequency || '—' }}</td>
              <td class="table-cell font-mono text-xs text-slate-500">{{ r.version || '1.0' }}</td>
              <td class="table-cell">
                <span
                  :class="r.is_active ? 'text-emerald-700 bg-emerald-50 border-emerald-100' : 'text-slate-600 bg-slate-50 border-slate-200'"
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium border"
                >
                  {{ r.is_active ? 'Đang áp dụng' : 'Ngừng áp dụng' }}
                </span>
              </td>
              <td class="table-cell text-right">
                <button v-if="r.is_active" class="text-xs text-red-600 hover:text-red-700 font-medium" @click="onDeactivate(r)">Ngừng áp dụng</button>
                <button v-else class="text-xs text-emerald-600 hover:text-emerald-700 font-medium" @click="onReactivate(r)">Kích hoạt lại</button>
              </td>
            </tr>
          </tbody>
        </table>
        </div>
      </template>
    </div>

    <BasePagination :pagination="pagination" @page-change="load" />

    <!-- Create Modal -->
    <BaseModal v-if="showCreate" title="Tạo quy tắc tuân thủ" size="lg" @close="showCreate = false">
      <div class="space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="form-group">
            <label class="form-label">Mã quy tắc *</label>
            <input v-model="form.rule_code" class="form-input" placeholder="R-IMM08-PM-COMP-90" />
            <p v-if="formErrors.rule_code" class="text-xs text-red-600 mt-1">{{ formErrors.rule_code }}</p>
          </div>
          <div class="form-group">
            <label class="form-label">Tên quy tắc *</label>
            <input v-model="form.rule_name" class="form-input" />
            <p v-if="formErrors.rule_name" class="text-xs text-red-600 mt-1">{{ formErrors.rule_name }}</p>
          </div>
          <div class="form-group">
            <label class="form-label">Module nguồn</label>
            <input v-model="form.source_module" class="form-input" placeholder="IMM-08" />
          </div>
          <div class="form-group">
            <label class="form-label">Nhóm</label>
            <select v-model="form.category" class="form-select">
              <option value="">-- Chọn nhóm --</option>
              <option value="Document">Document</option>
              <option value="PM">PM</option>
              <option value="Calibration">Calibration</option>
              <option value="Training">Training</option>
              <option value="Stock">Stock</option>
              <option value="SLA">SLA</option>
              <option value="Safety">Safety</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Mức độ *</label>
            <select v-model="form.severity" class="form-select">
              <option value="Low">Thấp</option>
              <option value="Medium">Trung bình</option>
              <option value="High">Cao</option>
              <option value="Critical">Nghiêm trọng</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Tần suất đánh giá</label>
            <select v-model="form.evaluation_frequency" class="form-select">
              <option value="Daily">Hàng ngày</option>
              <option value="Weekly">Hàng tuần</option>
              <option value="Monthly">Hàng tháng</option>
              <option value="Quarterly">Hàng quý</option>
            </select>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showCreate = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="submitCreate">
          {{ api.loading.value ? 'Đang lưu…' : 'Tạo quy tắc' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
