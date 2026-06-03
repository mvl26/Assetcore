<template>
  <div class="document-management">
    <PageHeader
      title="Quản lý Hồ sơ Thiết bị"
      :subtitle="assetFilter ? `Đang xem hồ sơ thiết bị ${assetFilter}` : 'Toàn bộ hồ sơ thiết bị y tế'"
      :breadcrumb="[{ label: 'IMM-05 · Hồ sơ', to: '/documents' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <button v-if="assetFilter" class="btn-ghost text-xs" @click="clearAssetFilter">Bỏ lọc theo thiết bị</button>
        <button class="btn-ghost text-sm" @click="showFilters = !showFilters">Bộ lọc</button>
        <button v-if="canUpload" class="btn-primary text-sm" @click="goToCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tải lên tài liệu
        </button>
      </template>
    </PageHeader>

    <!-- KPI Banner — clickable tiles mở filter; tile thống kê (missing) render tĩnh -->
    <div v-if="kpiTiles.length" class="kpi-grid">
      <template v-for="tile in kpiTiles" :key="tile.kind">
        <button
          v-if="tile.clickable"
          type="button"
          class="kpi-clickable"
          :aria-label="`Lọc theo: ${tile.label}`"
          @click="filterByKpi(tile.kind)"
        >
          <KpiCard :label="tile.label" :value="tile.value" :color="tile.color" />
        </button>
        <div v-else class="kpi-static" :title="tile.hint || ''">
          <KpiCard :label="tile.label" :value="tile.value" :color="tile.color" />
        </div>
      </template>
    </div>

    <!-- Filters -->
    <div v-if="showFilters" class="filter-bar">
      <select v-model="filters.doc_category" @change="applyFilters">
        <option value="">Tất cả nhóm</option>
        <option value="Legal">Pháp lý</option>
        <option value="Technical">Kỹ thuật</option>
        <option value="Certification">Kiểm định</option>
        <option value="Training">Đào tạo</option>
        <option value="QA">Chất lượng</option>
      </select>
      <select v-model="filters.workflow_state" @change="applyFilters">
        <option value="">Tất cả trạng thái</option>
        <option value="Draft">Nháp</option>
        <option value="Pending Review">Chờ duyệt</option>
        <option value="Active">Hiệu lực</option>
        <option value="Expired">Hết hạn</option>
        <option value="Archived">Lưu trữ</option>
        <option value="Rejected">Từ chối</option>
      </select>
      <select v-model="filterExpiry" aria-label="Lọc theo hết hạn" @change="applyFilters">
        <option v-for="o in EXPIRY_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <input
        v-model="filters.asset_ref"
        placeholder="Mã thiết bị..."
        @keyup.enter="applyFilters"
      />
      <button class="btn btn-sm" @click="resetFilters">Xóa bộ lọc</button>
    </div>

    <!-- Error -->
    <div v-if="store.error" class="alert alert-danger">
      <div>
        <strong>Lỗi:</strong> {{ store.error }}
        <span v-if="store.error.includes('500') || store.error.includes('Internal')" class="error-hint">
          — Kiểm tra <code>bench --site miyano show-pending-jobs</code> để xem traceback
        </span>
      </div>
      <button @click="store.clearError()">×</button>
    </div>

    <!-- Document Table -->
    <div class="table-container">
      <div v-if="store.loading" class="p-4">
        <SkeletonLoader :rows="6" :cols="8" />
      </div>
      <div v-else class="overflow-x-auto">
<table class="doc-table">
        <thead>
          <tr>
            <th>Mã tài liệu</th>
            <th>Thiết bị</th>
            <th>Nhóm</th>
            <th>Loại tài liệu</th>
            <th>Phiên bản</th>
            <th>Trạng thái</th>
            <th>Hết hạn</th>
            <th>Hành động</th>
          </tr>
        </thead>
        <TransitionGroup name="list" tag="tbody">
          <tr v-if="store.documents.length === 0" key="empty">
            <td colspan="8" class="empty-cell">
              <div class="empty-state">
                <svg class="empty-icon" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <p class="empty-title">Chưa có tài liệu nào.</p>
                <button v-if="canUpload" class="btn-primary text-sm mt-3" @click="goToCreate">
                  + Tạo Tài liệu mới
                </button>
                <p v-else class="empty-hint">Nhấn [+ Tạo Tài liệu mới] để bắt đầu.</p>
              </div>
            </td>
          </tr>
          <DocumentRow
            v-for="doc in store.documents"
            :key="doc.name"
            :doc="doc"
            @approve="handleApprove"
            @reject="openRejectDialog"
            @request-doc="openRequestModal"
            @exempt="openExemptModal"
            @history="openHistoryDialog"
          />
        </TransitionGroup>
      </table>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="store.pagination.total_pages > 1" class="pagination">
      <button :disabled="store.pagination.page <= 1" @click="store.changePage(store.pagination.page - 1)">← Trước</button>
      <span>Trang {{ store.pagination.page }} / {{ store.pagination.total_pages }}</span>
      <button :disabled="store.pagination.page >= store.pagination.total_pages" @click="store.changePage(store.pagination.page + 1)">Sau →</button>
    </div>

    <!-- ── Reject Dialog ──────────────────────────────────────────── -->
    <div v-if="rejectDialog.open" class="modal-overlay" @click.self="rejectDialog.open = false">
      <div class="modal">
        <h3>Lý do từ chối</h3>
        <textarea v-model="rejectDialog.reason" rows="3" placeholder="Nhập lý do từ chối..." />
        <div class="modal-actions">
          <button class="btn btn-outline" @click="rejectDialog.open = false">Hủy</button>
          <button class="btn btn-danger" :disabled="!rejectDialog.reason" @click="handleReject">
            Xác nhận Từ chối
          </button>
        </div>
      </div>
    </div>

    <!-- ── History Dialog ─────────────────────────────────────────── -->
    <div v-if="historyDialog.open" class="modal-overlay" @click.self="historyDialog.open = false">
      <div class="modal modal-wide">
        <div class="modal-header">
          <h3>Lịch sử thay đổi — {{ historyDialog.docName }}</h3>
          <button class="close-btn" @click="historyDialog.open = false">×</button>
        </div>
        <div v-if="historyDialog.loading" class="loading-spinner">Đang tải lịch sử...</div>
        <div v-else-if="historyDialog.entries.length === 0" class="text-muted text-center" style="padding:1rem">
          Chưa có thay đổi nào được ghi nhận.
        </div>
        <div v-else class="history-list">
          <div v-for="(entry, i) in historyDialog.entries" :key="i" class="history-entry">
            <div class="history-meta">
              <span class="history-time">{{ formatDatetime(entry.timestamp) }}</span>
              <span class="history-user">{{ entry.user }}</span>
              <span class="history-action" :class="entry.action === 'Workflow Transition' ? 'action-transition' : 'action-update'">
                {{ entry.action }}
              </span>
            </div>
            <div v-if="entry.from_state || entry.to_state" class="state-change">
              <span class="state-from">{{ entry.from_state ?? '—' }}</span>
              <span class="arrow">→</span>
              <span class="state-to">{{ entry.to_state ?? '—' }}</span>
            </div>
            <div v-if="entry.changes.length" class="field-changes">
              <span v-for="c in entry.changes" :key="c.field" class="field-change">
                <code>{{ c.field }}</code>: {{ c.old ?? '∅' }} → {{ c.new ?? '∅' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Document Request Modal ─────────────────────────────────── -->
    <DocumentRequestModal
      v-if="requestModal.open && requestModal.doc"
      :model-value="requestModal.doc"
      @close="requestModal.open = false"
      @created="onRequestCreated"
    />

    <!-- ── Exempt Modal ───────────────────────────────────────────── -->
    <ExemptModal
      v-if="exemptModal.open && exemptModal.doc"
      :model-value="exemptModal.doc"
      @close="exemptModal.open = false"
      @exempted="onExempted"
    />
</div>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm05Store } from '@/stores/imm05'
import { useCapabilities } from '@/composables/useCapabilities'
import type { AssetDocumentItem, DocumentFilters } from '@/api/imm05'
import { formatDatetime } from '@/utils/docUtils'
import {
  EXPIRY_OPTIONS,
  KPI_FILTERS,
  buildExpiryFilter,
  buildKpiFilter,
  composeFilters,
  type KpiKind,
} from './documentFilters'
import DocumentRow from '@/components/document/DocumentRow.vue'
import DocumentRequestModal from '@/components/document/DocumentRequestModal.vue'
import ExemptModal from '@/components/document/ExemptModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import KpiCard from '@/components/common/KpiCard.vue'
const toast = useToast()

const router = useRouter()
const route = useRoute()
const store = useImm05Store()
const { can } = useCapabilities()

// Capability gate (LL-FE): UI hide is UX-only — BE rbac.require is the chokepoint.
// `document.write` = can upload/manage; `document.read` = may view Internal_Only.
const canUpload = computed(() => can('document.write'))

// BE enforces visibility server-side (_apply_visibility_filter via document.read);
// FE no longer guesses by role-name. We only narrow the query for non-privileged
// users to avoid a needless round-trip, mirroring the BE rule.
function visibilityNarrow(): DocumentFilters {
  return can('document.read') ? {} : { visibility: 'Public' }
}

const showFilters = ref(false)
const filters = reactive<DocumentFilters>({ doc_category: '', workflow_state: '', asset_ref: '' })
const filterExpiry = ref('')

const kpiTiles = computed(() =>
  store.kpis
    ? KPI_FILTERS.map((k) => ({ ...k, value: store.kpis![k.field] ?? 0 }))
    : [],
)

// ── QR deep-link: ?asset=AST-xxx ────────────────────────────────────────────
const assetFilter = computed(() => route.query.asset as string | undefined)

function clearAssetFilter() {
  router.replace({ query: {} })
  filters.asset_ref = ''
  store.fetchDocuments(buildActiveFilters(), 1)
}

// ── Reject dialog ────────────────────────────────────────────────────────────
const rejectDialog = reactive({ open: false, targetName: '', reason: '' })

// ── History dialog ───────────────────────────────────────────────────────────
const historyDialog = reactive<{
  open: boolean; docName: string; loading: boolean
  entries: Array<{ timestamp: string; user: string; action: string; from_state: string | null; to_state: string | null; changes: Array<{ field: string; old: unknown; new: unknown }> }>
}>({ open: false, docName: '', loading: false, entries: [] })

// ── Request & Exempt modals ──────────────────────────────────────────────────
const requestModal = reactive<{
  open: boolean
  doc: AssetDocumentItem | null
  docName: string
  assetRef: string
  docType: string
  reason: string
  dueDate: string
}>({ open: false, doc: null, docName: '', assetRef: '', docType: '', reason: '', dueDate: '' })
const exemptModal = reactive<{ open: boolean; doc: AssetDocumentItem | null }>({ open: false, doc: null })

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  if (assetFilter.value) {
    filters.asset_ref = assetFilter.value
  }
  await Promise.all([
    store.fetchDocuments(buildActiveFilters()),
    store.fetchDashboardStats(),
  ])
})

// ── Methods ───────────────────────────────────────────────────────────────────

/** Compose the current UI filter state into a BE-ready DocumentFilters payload. */
function buildActiveFilters(): DocumentFilters {
  return composeFilters(
    visibilityNarrow(),
    {
      doc_category: filters.doc_category ?? '',
      workflow_state: filters.workflow_state ?? '',
      asset_ref: filters.asset_ref ?? '',
    },
    buildExpiryFilter(filterExpiry.value),
  )
}

function applyFilters() {
  store.fetchDocuments(buildActiveFilters(), 1)
}

function resetFilters() {
  filters.doc_category = ''
  filters.workflow_state = ''
  filters.asset_ref = ''
  filterExpiry.value = ''
  store.fetchDocuments(composeFilters(visibilityNarrow()), 1)
}

function filterByKpi(kind: KpiKind) {
  // Tile non-clickable (vd 'missing') render tĩnh, không gọi vào đây. Guard an toàn:
  // KHÔNG điều hướng nếu không có filter document-list thật (tránh điều hướng sai lệch).
  if (buildKpiFilter(kind) === null) return
  showFilters.value = true
  filters.doc_category = ''
  filters.asset_ref = ''
  const kpiFilter = buildKpiFilter(kind) ?? {}
  // Reflect the KPI choice in the visible filter controls.
  filters.workflow_state = (kpiFilter.workflow_state as string) ?? ''
  filterExpiry.value = kind === 'expiring' ? '90' : ''
  store.fetchDocuments(composeFilters(visibilityNarrow(), kpiFilter), 1)
}

function goToCreate() {
  router.push('/documents/new')
}

async function handleApprove(name: string) {
  if (!confirm(`Phê duyệt tài liệu ${name} sẽ tự động lưu trữ phiên bản cũ. Tiếp tục?`)) return
  const ok = await store.approveDocument(name)
  if (ok) {
    // BR-05-01: phiên bản cũ bị auto-archive ở BE → reload để list phản ánh đúng
    await store.fetchDocuments(store.currentFilters, store.pagination.page)
  }
}

function openRejectDialog(name: string) {
  rejectDialog.targetName = name
  rejectDialog.reason = ''
  rejectDialog.open = true
}

async function handleReject() {
  if (!rejectDialog.reason) return
  const ok = await store.rejectDocument(rejectDialog.targetName, rejectDialog.reason)
  if (ok) {
    rejectDialog.open = false
    await store.fetchDocuments(store.currentFilters, store.pagination.page)
  }
}

function openRequestModal(doc: AssetDocumentItem) {
  requestModal.doc = doc
  requestModal.docName = doc.name
  requestModal.assetRef = doc.asset_ref
  requestModal.docType = doc.doc_type_detail
  requestModal.reason = ''
  requestModal.dueDate = ''
  requestModal.open = true
}

function openExemptModal(doc: AssetDocumentItem) {
  exemptModal.doc = doc
  exemptModal.open = true
}

async function openHistoryDialog(name: string) {
  historyDialog.docName = name
  historyDialog.entries = []
  historyDialog.loading = true
  historyDialog.open = true
  try {
    const data = await store.fetchDocumentHistory(name)
    if (data) {
      historyDialog.entries = data.history
    } else {
      store.error = 'Không tải được lịch sử'
      historyDialog.open = false
    }
  } catch (e: unknown) {
    store.error = e instanceof Error ? e.message : 'Lỗi kết nối'
    historyDialog.open = false
  } finally {
    historyDialog.loading = false
  }
}

function onRequestCreated(name: string) {
  requestModal.open = false
  toast.success(`Yêu cầu tài liệu ${name} đã được tạo.`)
}

function onExempted(docName: string) {
  exemptModal.open = false
  store.fetchDocuments(store.currentFilters, store.pagination.page)
  toast.success(`Đã đánh dấu Exempt. Tài liệu mới: ${docName}`)
}

</script>

<style scoped>
.document-management { padding: 1.5rem; }

.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 1.5rem;
}
.page-header h1 { margin: 0; font-size: 1.5rem; }
.asset-filter-hint { margin: 4px 0 0; font-size: 0.85rem; color: #6b7280; }
.clear-filter {
  margin-left: 8px; background: none; border: none; cursor: pointer;
  color: #9ca3af; font-size: 0.8rem;
}
.clear-filter:hover { color: #ef4444; }
.header-actions { display: flex; gap: 0.75rem; }

/* KPI — tiles render via shared KpiCard; wrapper button makes them clickable */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-clickable { all: unset; cursor: pointer; display: block; border-radius: 10px; transition: transform .12s ease, box-shadow .12s ease; }
.kpi-clickable:hover { transform: translateY(-2px); }
.kpi-clickable:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
/* Tile thống kê (không điều hướng) — không cursor/hover, phân biệt với clickable */
.kpi-static { display: block; border-radius: 10px; cursor: default; }
@media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }

/* Filters */
.filter-bar { display: flex; gap: 0.75rem; align-items: center; background: #f9fafb; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; flex-wrap: wrap; }
.filter-bar select, .filter-bar input { padding: 0.4rem 0.6rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.875rem; }

/* Table */
.table-container { background: white; border-radius: 8px; overflow: auto; }
.doc-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.doc-table th { background: #f9fafb; text-align: left; padding: 0.75rem 1rem; font-weight: 600; border-bottom: 1px solid #e5e7eb; }
.doc-table :deep(td) { padding: 0.65rem 1rem; border-bottom: 1px solid #f3f4f6; }
.doc-table :deep(tr.row-pending) { background: #fefce8; }
.doc-table :deep(tr.row-expired) { background: #fef2f2; }
.doc-table :deep(tr.row-rejected) { background: #f9fafb; color: #6b7280; }

/* Buttons */
.btn { padding: 0.45rem 1rem; border-radius: 4px; border: none; cursor: pointer; font-size: 0.875rem; }
.btn-primary { background: #2563eb; color: #ffffff; }
.btn-outline { background: transparent; border: 1px solid #d1d5db; color: #374151; }
.btn-danger { background: #dc2626; color: #ffffff; }
.btn-sm { padding: 0.3rem 0.75rem; font-size: 0.8rem; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Alerts */
.alert { padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-danger { background: #fee2e2; color: #991b1b; }

/* Pagination */
.pagination { display: flex; gap: 1rem; align-items: center; justify-content: center; margin-top: 1rem; }

/* Modal base */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: white; border-radius: 8px; padding: 1.5rem; width: 400px; max-width: 95vw; }
.modal-wide { width: 600px; max-height: 80vh; overflow-y: auto; }
.modal h3 { margin: 0 0 1rem; }
.modal textarea { width: 100%; border: 1px solid #d1d5db; border-radius: 4px; padding: 0.5rem; box-sizing: border-box; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1rem; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.modal-header h3 { margin: 0; }
.close-btn { background: none; border: none; font-size: 1.25rem; cursor: pointer; color: #6b7280; }

/* History */
.history-list { display: flex; flex-direction: column; gap: 0.75rem; }
.history-entry { background: #f9fafb; border-radius: 6px; padding: 0.75rem; }
.history-meta { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 4px; }
.history-time { font-size: 0.8rem; color: #6b7280; }
.history-user { font-size: 0.8rem; font-weight: 600; color: #374151; }
.history-action { font-size: 0.75rem; padding: 1px 6px; border-radius: 10px; }
.action-transition { background: #dbeafe; color: #1e40af; }
.action-update { background: #e5e7eb; color: #374151; }
.state-change { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; margin-bottom: 4px; }
.state-from { background: #fee2e2; color: #991b1b; padding: 1px 8px; border-radius: 10px; }
.state-to { background: #d1fae5; color: #065f46; padding: 1px 8px; border-radius: 10px; }
.arrow { color: #9ca3af; font-weight: bold; }
.field-changes { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.field-change { font-size: 0.75rem; color: #374151; background: white; border: 1px solid #e5e7eb; padding: 2px 6px; border-radius: 4px; }
.field-change code { font-weight: 600; color: #5b21b6; }

/* Empty state (Core Doc §8 — actionable) */
.empty-cell { padding: 0 !important; }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 3rem 1rem; color: #94a3b8; }
.empty-icon { width: 2.5rem; height: 2.5rem; margin-bottom: 0.75rem; color: #cbd5e1; }
.empty-title { font-size: 0.9rem; font-weight: 500; color: #475569; }
.empty-hint { font-size: 0.8rem; margin-top: 0.5rem; }

/* Utils */
.text-center { text-align: center; }
.text-muted { color: #9ca3af; }

/* TransitionGroup list animation */
.list-enter-active,
.list-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.list-enter-from { opacity: 0; transform: translateY(-6px); }
.list-leave-to { opacity: 0; transform: translateY(6px); }
</style>
