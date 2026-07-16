<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, computed, onMounted } from 'vue'
import { useImm03Store } from '@/stores/imm03'
import { createAvlEntry, AVL_ACTIONS } from '@/api/imm03'
import type { AvlListItem, AvlState } from '@/types/imm03'
import { stateLabel, formatVnDate } from '@/utils/wave2Labels'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar, { type FilterChip } from '@/components/common/ListFilterBar.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import DateInput from '@/components/common/DateInput.vue'

const store = useImm03Store()
const notify = useNotify()

const STATES: AvlState[] = ['Draft', 'Approved', 'Conditional', 'Suspended', 'Expired']
const EXPIRY_BUCKETS = [
  { value: 'expiring30', label: 'Sắp hết hạn (≤ 30 ngày)' },
  { value: 'expired',    label: 'Đã hết hạn' },
] as const
type ExpiryBucket = typeof EXPIRY_BUCKETS[number]['value']

const showFilters = ref(false)
const filters = reactive<{
  workflow_state: AvlState | ''
  supplier: string
  device_category: string
  expiry_bucket: ExpiryBucket | ''
  search: string
}>({
  workflow_state: 'Approved',
  supplier: '',
  device_category: '',
  expiry_bucket: '',
  search: '',
})

const showCreate = ref(false)
const newAvl = reactive({
  supplier: '',
  device_category: '',
  validity_years: 2,
  valid_from: new Date().toISOString().slice(0, 10),
})
const canCreate = computed(() => newAvl.supplier && newAvl.device_category && newAvl.validity_years >= 1)

function daysLeft(a: AvlListItem): number {
  if (!a.valid_to) return 0
  return Math.ceil((new Date(a.valid_to).getTime() - Date.now()) / (1000 * 86400))
}
function isExpiring(a: AvlListItem): boolean {
  const d = daysLeft(a); return d > 0 && d <= 30
}

const activeChips = computed<FilterChip[]>(() => {
  const c: FilterChip[] = []
  if (filters.workflow_state)  c.push({ key: 'workflow_state', label: stateLabel(filters.workflow_state) })
  if (filters.supplier)        c.push({ key: 'supplier', label: `Nhà cung cấp: ${filters.supplier}` })
  if (filters.device_category) c.push({ key: 'device_category', label: `Nhóm: ${filters.device_category}` })
  if (filters.expiry_bucket) {
    const b = EXPIRY_BUCKETS.find(x => x.value === filters.expiry_bucket)
    c.push({ key: 'expiry_bucket', label: b?.label ?? filters.expiry_bucket })
  }
  if (filters.search.trim())   c.push({ key: 'search', label: `"${filters.search.trim()}"` })
  return c
})

function buildPayload(): Record<string, unknown> {
  const f: Record<string, unknown> = {}
  if (filters.workflow_state)  f.workflow_state = filters.workflow_state
  if (filters.supplier)        f.supplier = filters.supplier
  if (filters.device_category) f.device_category = filters.device_category
  if (filters.search.trim())   f.search = filters.search.trim()
  return f
}
function applyFilters() { store.fetchAvl(buildPayload()) }
function resetFilters() {
  filters.workflow_state = ''
  filters.supplier = ''
  filters.device_category = ''
  filters.expiry_bucket = ''
  filters.search = ''
  store.fetchAvl()
}
function clearChip(key: string) {
  ;(filters as Record<string, string>)[key] = ''
  applyFilters()
}
function quickFilter(key: keyof typeof filters, value: string) {
  ;(filters as Record<string, string>)[key] = value
  showFilters.value = false
  applyFilters()
}

const filteredAvl = computed(() => {
  if (!filters.expiry_bucket) return store.avlEntries
  return store.avlEntries.filter(a => {
    const d = daysLeft(a)
    if (filters.expiry_bucket === 'expiring30') return d > 0 && d <= 30
    if (filters.expiry_bucket === 'expired')    return d <= 0
    return true
  })
})

// ── Server-driven CTA (GATE-8 / LL-FE-51) ─────────────────────────────────────
// Nút render CHỈ khi action ∈ row.allowed_transitions (BE derive từ
// `_AVL_VALID_TRANSITIONS`, đã lọc theo capability/role). KHÔNG hardcode
// `workflow_state === 'X'` (dead-gate + lộ nút sai role). allowed_transitions
// rỗng/undefined → 0 nút (degrade an toàn, không dead-control 403).
function allowedActions(a: AvlListItem): string[] { return a.allowed_transitions ?? [] }
function canApproveAvl(a: AvlListItem): boolean { return allowedActions(a).includes(AVL_ACTIONS.APPROVE) }
function canRestoreAvl(a: AvlListItem): boolean { return allowedActions(a).includes(AVL_ACTIONS.RESTORE) }
function canSuspendAvl(a: AvlListItem): boolean { return allowedActions(a).includes(AVL_ACTIONS.SUSPEND) }
function canGrantConditional(a: AvlListItem): boolean { return allowedActions(a).includes(AVL_ACTIONS.GRANT_CONDITIONAL) }
function canDowngradeConditional(a: AvlListItem): boolean { return allowedActions(a).includes(AVL_ACTIONS.DOWNGRADE_CONDITIONAL) }
function hasAnyCta(a: AvlListItem): boolean {
  return canApproveAvl(a) || canGrantConditional(a) || canDowngradeConditional(a) || canRestoreAvl(a) || canSuspendAvl(a)
}

// Phê duyệt (Draft→Approved) & Phục hồi (Conditional/Suspended→Approved) đều gọi
// approveAvlEntry — approver = frappe.session.user (server-side), FE KHÔNG nhập email.
async function doApproveAvl(a: AvlListItem, restore = false) {
  const who = a.vendor_name || a.supplier
  const ok = await notify.confirm({
    title: restore ? 'Phục hồi giấy phép' : 'Phê duyệt giấy phép',
    body: restore
      ? `Phục hồi giấy phép ${a.name} của ${who} về trạng thái Đã duyệt?`
      : `Phê duyệt giấy phép ${a.name} cho ${who}?`,
    confirmText: restore ? 'Phục hồi' : 'Phê duyệt',
  })
  if (!ok) return
  const success = await store.approveAvlEntry(a.name)
  if (success) notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: `giấy phép ${a.name}` } })
  else notify.fromError(store.lastApiError)
}

// Đình chỉ: giữ modal nhập lý do (suspension_reason bắt buộc) thay window.prompt.
const suspendTarget = ref<AvlListItem | null>(null)
const suspendReason = ref('')
const suspendBusy = ref(false)
function openSuspendAvl(a: AvlListItem) { suspendTarget.value = a; suspendReason.value = '' }
function closeSuspendAvl() { suspendTarget.value = null; suspendReason.value = '' }
async function confirmSuspendAvl() {
  const a = suspendTarget.value
  const reason = suspendReason.value.trim()
  if (!a || !reason) return
  suspendBusy.value = true
  const success = await store.suspendAvlEntry(a.name, reason)
  suspendBusy.value = false
  if (success) {
    notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: `giấy phép ${a.name}` } })
    closeSuspendAvl()
  } else {
    notify.fromError(store.lastApiError)
  }
}
// Cấp/Hạ xuống có điều kiện: modal nhập điều kiện kèm theo (condition_notes bắt buộc,
// parity với Đình chỉ). 1 modal dùng chung cho cả 2 nhánh — mode phân biệt Draft
// (cấp) vs Approved (hạ xuống); cả hai chuyển sang trạng thái 'Có điều kiện'.
type ConditionalMode = 'grant' | 'downgrade'
const conditionalTarget = ref<AvlListItem | null>(null)
const conditionalMode = ref<ConditionalMode>('grant')
const conditionNotes = ref('')
const conditionalBusy = ref(false)
function openConditional(a: AvlListItem, mode: ConditionalMode) {
  conditionalTarget.value = a; conditionalMode.value = mode; conditionNotes.value = ''
}
function closeConditional() { conditionalTarget.value = null; conditionNotes.value = '' }
async function confirmConditional() {
  const a = conditionalTarget.value
  const notes = conditionNotes.value.trim()
  if (!a || !notes) return
  conditionalBusy.value = true
  const success = await store.setAvlConditional(a.name, notes)
  conditionalBusy.value = false
  if (success) {
    notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: `giấy phép ${a.name}` } })
    closeConditional()
  } else {
    notify.fromError(store.lastApiError)
  }
}

async function doCreate() {
  if (!canCreate.value) return
  await createAvlEntry(newAvl.supplier, newAvl.device_category, newAvl.validity_years, newAvl.valid_from)
  showCreate.value = false
  newAvl.supplier = ''; newAvl.device_category = ''
  applyFilters()
}

onMounted(() => {
  store.fetchAvl({ workflow_state: 'Approved' })
  store.fetchKpis()
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Danh mục nhà cung cấp được duyệt"
      :subtitle="`Tổng ${store.avlEntries.length} giấy phép — cấp phép theo nhóm thiết bị, có hạn hiệu lực.`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeChips.length" />
        <button class="btn-primary shrink-0" @click="showCreate = true">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Cấp mới
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      v-model:search="filters.search"
      :show="showFilters"
      :chips="activeChips"
      search-placeholder="Tìm theo mã duyệt hoặc tên nhà cung cấp..."
      @apply="applyFilters"
      @reset="resetFilters"
      @clear-chip="clearChip"
    >
      <template #fields>
        <select v-model="filters.workflow_state" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in STATES" :key="s" :value="s">{{ stateLabel(s) }}</option>
        </select>
        <select v-model="filters.expiry_bucket" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả hiệu lực</option>
          <option v-for="b in EXPIRY_BUCKETS" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </template>
    </ListFilterBar>

    <div v-if="store.kpis" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
      <KpiCard label="Đang hiệu lực" :value="store.kpis.avl_active" color="success" />
      <KpiCard
        label="Sắp hết hạn (≤ 30 ngày)"
        :value="store.kpis.avl_expiring_30d"
        :color="store.kpis.avl_expiring_30d > 0 ? 'warning' : 'neutral'"
      />
    </div>

    <div v-if="store.error" class="alert-error mb-4">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeChips.length > 0">Kết quả lọc: <strong class="text-slate-700">{{ filteredAvl.length }}</strong> giấy phép</span>
          <span v-else>Hiển thị <strong class="text-slate-700">{{ filteredAvl.length }}</strong> giấy phép</span>
        </span>
        <button v-if="activeChips.length > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="store.loading" class="p-6 text-sm text-slate-500">Đang tải...</div>
      <template v-else-if="filteredAvl.length">
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="a in filteredAvl"
            :key="a.name"
            class="mobile-card"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ a.name }}</span>
              <StatusBadge :state="a.workflow_state" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ a.vendor_name || a.supplier }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ a.device_category_name || a.device_category }}</span>
              <span>· {{ formatVnDate(a.valid_from) }} → {{ formatVnDate(a.valid_to) }}</span>
              <span v-if="isExpiring(a)" class="warn-text">⏰ Còn {{ daysLeft(a) }} ngày</span>
            </div>
            <div class="flex flex-wrap gap-2 mt-2">
              <button v-if="canApproveAvl(a)" class="btn-mini btn-success" @click.stop="doApproveAvl(a)">Phê duyệt</button>
              <button v-if="canGrantConditional(a)" class="btn-mini btn-warning" @click.stop="openConditional(a, 'grant')">Cấp có điều kiện</button>
              <button v-if="canDowngradeConditional(a)" class="btn-mini btn-warning" @click.stop="openConditional(a, 'downgrade')">Hạ xuống có điều kiện</button>
              <button v-if="canRestoreAvl(a)" class="btn-mini btn-success" @click.stop="doApproveAvl(a, true)">Phục hồi</button>
              <button v-if="canSuspendAvl(a)" class="btn-mini btn-danger" @click.stop="openSuspendAvl(a)">Đình chỉ</button>
            </div>
          </div>
          <div v-if="filteredAvl.length === 0" class="py-12 text-center text-slate-400">
            <p class="text-sm">Không có dữ liệu</p>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mã giấy phép</th>
                <th>Nhà cung cấp</th>
                <th>Nhóm thiết bị</th>
                <th>Thời hạn hiệu lực</th>
                <th>Trạng thái</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(a, idx) in filteredAvl" :key="a.name"
                class="animate-fade-in" :class="[`stagger-${Math.min(idx + 1, 8)}`]"
              >
                <td><span class="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{{ a.name }}</span></td>
                <td>
                  <button class="link-cell" :title="`Lọc: ${a.supplier}`" @click="quickFilter('supplier', a.supplier)">
                    {{ a.vendor_name || a.supplier }}
                  </button>
                </td>
                <td>
                  <button class="link-cell" :title="`Lọc: ${a.device_category}`" @click="quickFilter('device_category', a.device_category)">
                    {{ a.device_category_name || a.device_category }}
                  </button>
                </td>
                <td>
                  {{ formatVnDate(a.valid_from) }} → {{ formatVnDate(a.valid_to) }}
                  <span v-if="isExpiring(a)" class="warn-text">⏰ Còn {{ daysLeft(a) }} ngày</span>
                </td>
                <td>
                  <button
  type="button" class="pill-btn"
                          :title="`Lọc trạng thái: ${stateLabel(a.workflow_state)}`"
                          @click="quickFilter('workflow_state', a.workflow_state)">
                    <StatusBadge :state="a.workflow_state" />
                  </button>
                </td>
                <td class="actions-col">
                  <button v-if="canApproveAvl(a)" data-testid="cta-approve" class="btn-mini btn-success" @click="doApproveAvl(a)">Phê duyệt</button>
                  <button v-if="canGrantConditional(a)" data-testid="cta-grant-conditional" class="btn-mini btn-warning" @click="openConditional(a, 'grant')">Cấp có điều kiện</button>
                  <button v-if="canDowngradeConditional(a)" data-testid="cta-downgrade-conditional" class="btn-mini btn-warning" @click="openConditional(a, 'downgrade')">Hạ xuống có điều kiện</button>
                  <button v-if="canRestoreAvl(a)" data-testid="cta-restore" class="btn-mini btn-success" @click="doApproveAvl(a, true)">Phục hồi</button>
                  <button v-if="canSuspendAvl(a)" data-testid="cta-suspend" class="btn-mini btn-danger" @click="openSuspendAvl(a)">Đình chỉ</button>
                  <span v-if="!hasAnyCta(a)" class="text-xs text-slate-400">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else-if="!filteredAvl.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có giấy phép nào phù hợp</p>
        <button v-if="activeChips.length > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-head">
          <h3>Cấp giấy phép cho nhà cung cấp</h3>
          <button class="btn-close" @click="showCreate = false">×</button>
        </div>
        <div class="modal-body">
          <label>Nhà cung cấp <span class="req">*</span>
            <input v-model="newAvl.supplier" type="text" placeholder="Chọn nhà cung cấp..." />
          </label>
          <label>Nhóm thiết bị <span class="req">*</span>
            <input v-model="newAvl.device_category" type="text" placeholder="Ví dụ: Chẩn đoán hình ảnh..." />
          </label>
          <label>Thời hạn hiệu lực (năm) <span class="req">*</span>
            <input v-model.number="newAvl.validity_years" type="number" min="1" max="3" />
          </label>
          <label>Hiệu lực từ ngày
            <DateInput v-model="newAvl.valid_from" class="form-input w-full" />
          </label>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" @click="showCreate = false">Huỷ</button>
          <button class="btn-primary" :disabled="!canCreate" @click="doCreate">Tạo giấy phép</button>
        </div>
      </div>
    </div>

    <!-- Suspend modal (thay window.prompt) — lý do đình chỉ bắt buộc -->
    <BaseModal
      v-if="suspendTarget"
      title="Đình chỉ giấy phép nhà cung cấp"
      size="md"
      danger
      @close="closeSuspendAvl"
    >
      <p class="text-sm text-slate-600 mb-3">
        Đình chỉ giấy phép
        <strong class="font-mono">{{ suspendTarget.name }}</strong>
        của {{ suspendTarget.vendor_name || suspendTarget.supplier }}.
      </p>
      <label for="avl-suspend-reason" class="block text-sm font-medium text-slate-700 mb-1">
        Lý do đình chỉ <span class="text-red-500">*</span>
      </label>
      <textarea
        id="avl-suspend-reason"
        v-model="suspendReason"
        data-testid="avl-suspend-reason"
        rows="3"
        aria-describedby="avl-suspend-hint"
        class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
        placeholder="Ví dụ: Chứng chỉ ISO 13485 đã hết hạn, chưa gia hạn..."
      ></textarea>
      <p id="avl-suspend-hint" class="mt-1 text-xs text-slate-400">
        Lý do được lưu vào hồ sơ và hiển thị trong lịch sử giấy phép.
      </p>
      <template #footer>
        <button class="btn-ghost" @click="closeSuspendAvl">Huỷ</button>
        <button
          class="btn-mini btn-danger"
          data-testid="cta-suspend-confirm"
          :disabled="!suspendReason.trim() || suspendBusy"
          @click="confirmSuspendAvl"
        >
          Đình chỉ
        </button>
      </template>
    </BaseModal>

    <!-- Cấp / Hạ xuống có điều kiện — điều kiện kèm theo bắt buộc (thay window.prompt) -->
    <BaseModal
      v-if="conditionalTarget"
      :title="conditionalMode === 'grant' ? 'Cấp giấy phép có điều kiện' : 'Hạ giấy phép xuống có điều kiện'"
      size="md"
      @close="closeConditional"
    >
      <p class="text-sm text-slate-600 mb-3">
        <template v-if="conditionalMode === 'grant'">Cấp</template>
        <template v-else>Hạ</template>
        giấy phép
        <strong class="font-mono">{{ conditionalTarget.name }}</strong>
        của {{ conditionalTarget.vendor_name || conditionalTarget.supplier }}
        về trạng thái <strong>Có điều kiện</strong>.
      </p>
      <label for="avl-condition-notes" class="block text-sm font-medium text-slate-700 mb-1">
        Điều kiện kèm theo <span class="text-red-500">*</span>
      </label>
      <textarea
        id="avl-condition-notes"
        v-model="conditionNotes"
        data-testid="avl-condition-notes"
        rows="3"
        aria-describedby="avl-condition-hint"
        class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
        placeholder="Ví dụ: Chỉ đạt 2/3 tiêu chí — bổ sung chứng chỉ ISO trong 90 ngày..."
      ></textarea>
      <p id="avl-condition-hint" class="mt-1 text-xs text-slate-400">
        Điều kiện được lưu vào hồ sơ giấy phép và hiển thị trong lịch sử.
      </p>
      <template #footer>
        <button class="btn-ghost" @click="closeConditional">Huỷ</button>
        <button
          class="btn-mini btn-warning"
          data-testid="cta-conditional-confirm"
          :disabled="!conditionNotes.trim() || conditionalBusy"
          @click="confirmConditional"
        >
          {{ conditionalMode === 'grant' ? 'Cấp có điều kiện' : 'Hạ xuống có điều kiện' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.actions-col { display: flex; gap: 0.5rem; }
.warn-text { color: #b45309; font-weight: 600; margin-left: 0.5rem; }
.btn-mini { padding: 0.3rem 0.6rem; font-size: 0.8rem; border-radius: 6px; border: 1px solid #cbd5e1; cursor: pointer; font: inherit; }
.btn-mini.btn-success { background: #059669; color: white; border-color: #059669; }
.btn-mini.btn-danger  { background: #dc2626; color: white; border-color: #dc2626; }
.btn-mini.btn-warning { background: #d97706; color: white; border-color: #d97706; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; border-radius: 8px; width: 480px; max-width: 90vw; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid #e5e7eb; }
.modal-head h3 { margin: 0; }
.btn-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; }
.modal-body { padding: 1rem; }
.modal-body label { display: block; margin-bottom: 1rem; font-weight: 500; }
.modal-body input { display: block; width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; margin-top: 0.25rem; }
.modal-foot { padding: 1rem; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 0.5rem; }
.req { color: #ef4444; }
</style>
