<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Kiểm toán nội bộ (Internal Audit) — list + create.
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import { createAudit } from '@/api/imm16'
import type { InternalAudit } from '@/api/imm16'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'

const router = useRouter()
const store = useImm16Store()
const api = useApi()

const items = computed(() => store.audits)
const pagination = computed(() => store.auditsPagination)
const loading = computed(() => store.auditsLoading)

const showFilters = ref(false)
const filterStatus = ref<string>('')
const filterType = ref<string>('')

const STATUSES: { value: string; label: string }[] = [
  { value: 'Planned',     label: 'Đã lập kế hoạch' },
  { value: 'In Progress', label: 'Đang thực hiện' },
  { value: 'Reporting',   label: 'Đang lập báo cáo' },
  { value: 'Closed',      label: 'Đã đóng' },
]

const chips = computed(() => {
  const c: { key: string; label: string }[] = []
  if (filterStatus.value) {
    const s = STATUSES.find(x => x.value === filterStatus.value)
    c.push({ key: 'status', label: s?.label ?? filterStatus.value })
  }
  if (filterType.value) c.push({ key: 'type', label: `Loại: ${filterType.value}` })
  return c
})
const activeFilterCount = computed(() => chips.value.length)

function buildFilters() {
  const f: Record<string, unknown> = {}
  if (filterStatus.value) f.status = filterStatus.value
  if (filterType.value) f.audit_type = filterType.value
  return f
}

async function load(page = 1) {
  await store.fetchAudits(buildFilters(), page, 20)
}

function clearChip(key: string) {
  if (key === 'status') filterStatus.value = ''
  else if (key === 'type') filterType.value = ''
  load(1)
}
function resetFilters() {
  filterStatus.value = ''; filterType.value = ''
  load(1)
}

// ── Create modal ──
const showCreate = ref(false)
const form = ref<Partial<InternalAudit>>({
  audit_code: '', audit_type: 'Internal',
  planned_start: '', planned_end: '', lead_auditor: '',
})

function openCreate() {
  form.value = { audit_code: '', audit_type: 'Internal', planned_start: '', planned_end: '', lead_auditor: '' }
  showCreate.value = true
}

async function submitCreate() {
  const res = await api.run(() => createAudit(form.value), { successMessage: 'Đã tạo kiểm toán' })
  if (res) { showCreate.value = false; load(1) }
}

onMounted(() => load(1))
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Kiểm toán nội bộ"
      :subtitle="`IMM-16 · Theo dõi tuân thủ — Tổng ${pagination.total} đợt kiểm toán`"
      :breadcrumb="[{ label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' }, { label: 'Kiểm toán' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo kiểm toán
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
          <select v-model="filterStatus" class="form-select" @change="load(1)">
            <option value="">Tất cả</option>
            <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Loại</label>
          <input v-model="filterType" class="form-input" placeholder="VD: Internal, External..." @keyup.enter="load(1)" />
        </div>
      </template>
    </ListFilterBar>

    <div class="table-wrapper">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ items.length }}</strong> / {{ pagination.total }}</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
      <div v-if="loading" class="p-4"><SkeletonLoader variant="table" :rows="6" /></div>
      <div v-else-if="!items.length" class="flex flex-col items-center justify-center py-16">
        <p class="text-sm text-slate-500">Chưa có đợt kiểm toán phù hợp.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
        <button v-else class="btn-primary mt-3" @click="openCreate">Tạo đợt kiểm toán đầu tiên</button>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã kiểm toán</th>
              <th class="table-header">Loại</th>
              <th class="table-header">Bắt đầu</th>
              <th class="table-header">Kết thúc</th>
              <th class="table-header">Trưởng đoàn</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header text-right">Phát hiện</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="a in items" :key="a.name"
                class="hover:bg-slate-50 cursor-pointer"
                @click="router.push(`/compliance/audits/${a.name}`)">
              <td class="table-cell">
                <div class="font-medium text-slate-900">{{ a.audit_code }}</div>
                <div class="font-mono text-xs text-brand-700 mt-0.5">{{ a.name }}</div>
              </td>
              <td class="table-cell text-slate-600">{{ a.audit_type }}</td>
              <td class="table-cell text-slate-600">{{ formatDate(a.planned_start) }}</td>
              <td class="table-cell text-slate-600">{{ formatDate(a.planned_end) }}</td>
              <td class="table-cell text-slate-600">{{ (a as any).lead_auditor_name || a.lead_auditor || '—' }}</td>
              <td class="table-cell"><StatusBadge :state="a.status" /></td>
              <td class="table-cell text-right font-semibold tabular-nums">{{ a.findings_count ?? 0 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <BasePagination :pagination="pagination" @page-change="load" />

    <BaseModal v-if="showCreate" title="Tạo đợt kiểm toán" size="lg" @close="showCreate = false">
      <div class="space-y-3 grid grid-cols-2 gap-3">
        <div class="form-group">
          <label class="form-label">Mã kiểm toán *</label>
          <input v-model="form.audit_code" class="form-input" placeholder="AUD-2026-Q1" />
        </div>
        <div class="form-group">
          <label class="form-label">Loại *</label>
          <select v-model="form.audit_type" class="form-select">
            <option value="Internal">Internal</option>
            <option value="External">External</option>
            <option value="Surveillance">Surveillance</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Bắt đầu *</label>
          <input v-model="form.planned_start" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Kết thúc *</label>
          <input v-model="form.planned_end" type="date" class="form-input" />
        </div>
        <div class="form-group col-span-2">
          <label class="form-label">Trưởng đoàn (User email)</label>
          <input v-model="form.lead_auditor" class="form-input" placeholder="user@hospital.vn" />
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showCreate = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="submitCreate">
          {{ api.loading.value ? 'Đang lưu…' : 'Tạo kiểm toán' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>
