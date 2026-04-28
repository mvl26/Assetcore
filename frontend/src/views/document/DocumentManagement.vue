<template>
  <div class="document-management">
<!-- Header -->
    <div class="page-header">
      <div>
        <h1>Quản lý Hồ sơ Thiết bị</h1>
        <p v-if="assetFilter" class="asset-filter-hint">
          Đang xem hồ sơ thiết bị: <strong>{{ assetFilter }}</strong>
          <button class="clear-filter" @click="clearAssetFilter">✕ Xóa</button>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-outline" @click="showFilters = !showFilters">Bộ lọc</button>
        <button class="btn btn-primary" @click="goToCreate">+ Tải lên Tài liệu</button>
      </div>
    </div>

    <!-- KPI Banner -->
    <div v-if="store.kpis" class="kpi-grid">
      <div class="kpi-card">
        <span class="kpi-value">{{ store.kpis.total_active }}</span>
        <span class="kpi-label">Tài liệu Active</span>
      </div>
      <div class="kpi-card warn">
        <span class="kpi-value">{{ store.kpis.expiring_90d }}</span>
        <span class="kpi-label">Sắp hết hạn (90 ngày)</span>
      </div>
      <div class="kpi-card danger">
        <span class="kpi-value">{{ store.kpis.expired_not_renewed }}</span>
        <span class="kpi-label">Đã hết hạn</span>
      </div>
      <div class="kpi-card info">
        <span class="kpi-value">{{ store.kpis.assets_missing_docs }}</span>
        <span class="kpi-label">Thiết bị thiếu hồ sơ</span>
      </div>
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
        <option value="Pending_Review">Chờ duyệt</option>
        <option value="Active">Hiệu lực</option>
        <option value="Expired">Hết hạn</option>
        <option value="Archived">Lưu trữ</option>
        <option value="Rejected">Từ chối</option>
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
            <td colspan="8" class="text-center text-muted">Không có tài liệu nào.</td>
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
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm05Store } from '@/stores/imm05Store'
import { useAuthStore } from '@/stores/auth'
import type { AssetDocumentItem, DocumentFilters } from '@/api/imm05'
import { formatDatetime } from '@/utils/docUtils'
import DocumentRow from '@/components/document/DocumentRow.vue'
import DocumentRequestModal from '@/components/document/DocumentRequestModal.vue'
import ExemptModal from '@/components/document/ExemptModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const router = useRouter()
const route = useRoute()
const store = useImm05Store()
const auth = useAuthStore()

// ── Role-based visibility filter (Task 1c) ───────────────────────────────────
function buildRoleVisibilityFilter(base: DocumentFilters): DocumentFilters {
  const isClinicalHead = auth.roles.includes('Clinical Head')
  const isPrivileged = auth.roles.includes('CMMS Admin') || auth.roles.includes('QA Risk Team')
  if (isClinicalHead && !isPrivileged) {
    return { ...base, visibility: 'Public' }
  }
  return base
}

const showFilters = ref(false)
const filters = reactive<DocumentFilters>({ doc_category: '', workflow_state: '', asset_ref: '' })

// ── QR deep-link: ?asset=AST-xxx ────────────────────────────────────────────
const assetFilter = computed(() => route.query.asset as string | undefined)

function clearAssetFilter() {
  router.replace({ query: {} })
  store.fetchDocuments({}, 1)
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
  const initialFilters: DocumentFilters = {}
  if (assetFilter.value) {
    initialFilters.asset_ref = assetFilter.value
    filters.asset_ref = assetFilter.value
  }
  await Promise.all([
    store.fetchDocuments(buildRoleVisibilityFilter(initialFilters)),
    store.fetchDashboardStats(),
  ])
})

// ── Methods ───────────────────────────────────────────────────────────────────

function applyFilters() {
  const active: DocumentFilters = {}
  if (filters.doc_category) active.doc_category = filters.doc_category
  if (filters.workflow_state) active.workflow_state = filters.workflow_state
  if (filters.asset_ref) active.asset_ref = filters.asset_ref
  store.fetchDocuments(buildRoleVisibilityFilter(active), 1)
}

function resetFilters() {
  filters.doc_category = ''
  filters.workflow_state = ''
  filters.asset_ref = ''
  store.fetchDocuments(buildRoleVisibilityFilter({}), 1)
}

function goToCreate() {
  router.push('/documents/new')
}

async function handleApprove(name: string) {
  if (!confirm(`Xác nhận DUYỆT tài liệu ${name}?`)) return
  await store.approveDocument(name)
}

function openRejectDialog(name: string) {
  rejectDialog.targetName = name
  rejectDialog.reason = ''
  rejectDialog.open = true
}

async function handleReject() {
  if (!rejectDialog.reason) return
  const ok = await store.rejectDocument(rejectDialog.targetName, rejectDialog.reason)
  if (ok) rejectDialog.open = false
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
  } catch (e) {
    store.error = e instanceof Error ? e.message : 'Lỗi kết nối'
    historyDialog.open = false
  } finally {
    historyDialog.loading = false
  }
}

function onRequestCreated(name: string) {
  requestModal.open = false
  alert(`Yêu cầu tài liệu ${name} đã được tạo.`)
}

function onExempted(docName: string) {
  exemptModal.open = false
  store.fetchDocuments(store.currentFilters, store.pagination.page)
  alert(`Đã đánh dấu Exempt. Tài liệu mới: ${docName}`)
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

/* KPI */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card { background: white; border-radius: 8px; padding: 1rem; border-left: 4px solid #4f8ef7; box-shadow: 0 1px 4px rgba(0,0,0,.08); display: flex; flex-direction: column; }
.kpi-card.warn { border-color: #f59e0b; }
.kpi-card.danger { border-color: #ef4444; }
.kpi-card.info { border-color: #6366f1; }
.kpi-value { font-size: 2rem; font-weight: 700; }
.kpi-label { font-size: 0.8rem; color: #6b7280; }

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

/* Utils */
.text-center { text-align: center; }
.text-muted { color: #9ca3af; }

/* TransitionGroup list animation */
.list-enter-active,
.list-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.list-enter-from { opacity: 0; transform: translateY(-6px); }
.list-leave-to { opacity: 0; transform: translateY(6px); }
</style>
