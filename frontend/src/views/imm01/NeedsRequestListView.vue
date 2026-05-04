<template>
  <div class="needs-request-list">
    <div class="page-header">
      <div>
        <h1>Đề xuất nhu cầu thiết bị</h1>
        <p class="muted">Tiếp nhận, chấm điểm ưu tiên và lập dự toán cho thiết bị y tế.</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-outline" @click="showFilters = !showFilters">Bộ lọc</button>
        <button class="btn btn-primary" @click="goCreate">+ Tạo đề xuất</button>
      </div>
    </div>

    <!-- Bảng chỉ số nhanh -->
    <div v-if="store.kpis" class="kpi-grid">
      <div class="kpi-card">
        <span class="kpi-value">{{ store.kpis.backlog_over_30d }}</span>
        <span class="kpi-label">Phiếu tồn quá 30 ngày</span>
      </div>
      <div class="kpi-card success">
        <span class="kpi-value">{{ store.kpis.g01_pass_rate.toFixed(1) }}%</span>
        <span class="kpi-label">Tỷ lệ qua kiểm tra ban đầu</span>
      </div>
      <div class="kpi-card info">
        <span class="kpi-value">{{ store.kpis.envelope_utilization.toFixed(1) }}%</span>
        <span class="kpi-label">Tỷ lệ sử dụng ngân sách</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-value">{{ totalApproved }}</span>
        <span class="kpi-label">Đã được duyệt</span>
      </div>
    </div>

    <!-- Bộ lọc -->
    <div v-if="showFilters" class="filter-bar">
      <select v-model="localFilters.workflow_state" @change="apply">
        <option value="">Tất cả trạng thái</option>
        <option v-for="s in WORKFLOW_STATES" :key="s" :value="s">{{ stateLabel(s) }}</option>
      </select>
      <select v-model="localFilters.request_type" @change="apply">
        <option value="">Tất cả loại đề xuất</option>
        <option value="New">Mua mới</option>
        <option value="Replacement">Thay thế</option>
        <option value="Upgrade">Nâng cấp</option>
        <option value="Add-on">Bổ sung</option>
      </select>
      <select v-model="localFilters.priority_class" @change="apply">
        <option value="">Tất cả mức ưu tiên</option>
        <option value="P1">Rất cao</option>
        <option value="P2">Cao</option>
        <option value="P3">Trung bình</option>
        <option value="P4">Thấp</option>
      </select>
      <button class="btn btn-sm" @click="reset">Xóa bộ lọc</button>
    </div>

    <div v-if="store.error" class="alert alert-danger">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Mã phiếu</th>
            <th>Loại đề xuất</th>
            <th>Khoa đề xuất</th>
            <th>Model thiết bị</th>
            <th class="num">Số lượng</th>
            <th>Mức ưu tiên</th>
            <th class="num">Tổng chi phí 5 năm</th>
            <th>Trạng thái</th>
            <th>Hành động</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.loading">
            <td colspan="9" class="text-center muted">Đang tải...</td>
          </tr>
          <tr v-else-if="!store.needsRequests.length">
            <td colspan="9" class="text-center muted">Chưa có đề xuất nào.</td>
          </tr>
          <tr v-for="nr in store.needsRequests" :key="nr.name" @click="goDetail(nr.name)" class="clickable">
            <td>{{ nr.name }}</td>
            <td>{{ requestTypeLabel(nr.request_type) }}</td>
            <td>{{ nr.requesting_department }}</td>
            <td>{{ nr.device_model_ref }}</td>
            <td class="num">{{ nr.quantity }}</td>
            <td>
              <span v-if="nr.priority_class" :class="['badge', 'priority-' + nr.priority_class]">
                {{ priorityBadge(nr.priority_class) }}
              </span>
              <span v-else class="muted">—</span>
            </td>
            <td class="num">{{ formatVnd(nr.tco_5y) }}</td>
            <td>
              <span :class="['badge', 'state-' + stateSlug(nr.workflow_state)]">
                {{ stateLabel(nr.workflow_state) }}
              </span>
            </td>
            <td>
              <button class="btn btn-sm btn-outline" @click.stop="goDetail(nr.name)">Xem</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="store.total > store.pageSize" class="pagination">
      <button :disabled="store.page <= 1" class="btn btn-sm" @click="goPage(store.page - 1)">‹ Trước</button>
      <span class="muted">Trang {{ store.page }} / {{ totalPages }} — {{ store.total }} phiếu</span>
      <button :disabled="store.page >= totalPages" class="btn btn-sm" @click="goPage(store.page + 1)">Sau ›</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm01Store } from '@/stores/imm01'
import type { NeedsRequestFilters, RequestType, NeedsRequestState } from '@/types/imm01'
import {
  stateLabel, stateSlug, requestTypeLabel, priorityBadge, formatVnd,
} from '@/utils/wave2Labels'

const router = useRouter()
const store = useImm01Store()

const WORKFLOW_STATES: NeedsRequestState[] = [
  'Draft', 'Submitted', 'Reviewing', 'Prioritized',
  'Budgeted', 'Pending Approval', 'Approved', 'Rejected',
]

const showFilters = ref(false)
const localFilters = reactive<NeedsRequestFilters & Record<string, unknown>>({
  workflow_state: '' as unknown as NeedsRequestState,
  request_type: '' as unknown as RequestType,
  priority_class: '' as unknown as 'P1',
})

const totalPages = computed(() => Math.max(1, Math.ceil(store.total / store.pageSize)))
const totalApproved = computed(() => store.kpis?.by_state?.['Approved'] ?? 0)

function apply() {
  const f: NeedsRequestFilters = {}
  if (localFilters.workflow_state) f.workflow_state = localFilters.workflow_state as NeedsRequestState
  if (localFilters.request_type) f.request_type = localFilters.request_type as RequestType
  if (localFilters.priority_class) f.priority_class = localFilters.priority_class
  store.fetchNeedsRequests(f, 1, store.pageSize)
}

function reset() {
  localFilters.workflow_state = '' as unknown as NeedsRequestState
  localFilters.request_type = '' as unknown as RequestType
  localFilters.priority_class = '' as unknown as 'P1'
  store.fetchNeedsRequests({}, 1, store.pageSize)
}

function goCreate()       { router.push({ name: 'NeedsRequestCreate' }) }
function goDetail(n: string) { router.push({ name: 'NeedsRequestDetail', params: { id: n } }) }
function goPage(p: number)   { store.fetchNeedsRequests(store.filters, p, store.pageSize) }

onMounted(() => {
  store.fetchNeedsRequests()
  store.fetchKpis()
})
</script>

<style scoped>
.needs-request-list { padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
.muted { color: #6b7280; font-size: 0.85rem; }
.header-actions { display: flex; gap: 0.5rem; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; }
.kpi-card .kpi-value { font-size: 1.75rem; font-weight: 700; color: #111827; }
.kpi-card .kpi-label { color: #6b7280; font-size: 0.85rem; margin-top: 0.25rem; }
.kpi-card.success { border-left: 4px solid #10b981; }
.kpi-card.info    { border-left: 4px solid #3b82f6; }
.filter-bar { display: flex; gap: 0.5rem; margin-bottom: 1rem; align-items: center; flex-wrap: wrap; }
.filter-bar select, .filter-bar input { padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }
.alert-close { background: none; border: none; cursor: pointer; font-size: 1.25rem; }
.table-container { background: white; border-radius: 8px; overflow: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; font-size: 0.85rem; }
.data-table .num { text-align: right; }
.data-table tr.clickable { cursor: pointer; transition: background 0.1s; }
.data-table tr.clickable:hover { background: #f9fafb; }
.text-center { text-align: center; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.priority-P1 { background: #fee2e2; color: #b91c1c; }
.badge.priority-P2 { background: #fed7aa; color: #c2410c; }
.badge.priority-P3 { background: #fef9c3; color: #a16207; }
.badge.priority-P4 { background: #e5e7eb; color: #4b5563; }
.badge.state-draft { background: #e5e7eb; color: #374151; }
.badge.state-submitted, .badge.state-reviewing { background: #fef3c7; color: #92400e; }
.badge.state-prioritized, .badge.state-budgeted { background: #dbeafe; color: #1e40af; }
.badge.state-pending-approval { background: #fce7f3; color: #9d174d; }
.badge.state-approved { background: #d1fae5; color: #065f46; }
.badge.state-rejected { background: #fee2e2; color: #b91c1c; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; font-size: 0.85rem; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.btn-sm { padding: 0.3rem 0.6rem; font-size: 0.8rem; }
.pagination { display: flex; gap: 1rem; align-items: center; justify-content: center; padding: 1rem; }
code { font-family: ui-monospace, SFMono-Regular, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; font-size: 0.85rem; }
</style>
