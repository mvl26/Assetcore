<template>
  <div class="needs-request-detail" v-if="store.currentDoc">
    <div class="page-header">
      <div>
        <h1>
          {{ store.currentDoc.name }}
          <span v-if="store.currentDoc.priority_class"
                :class="['badge', 'priority-' + store.currentDoc.priority_class]">
            {{ priorityBadge(store.currentDoc.priority_class) }}
          </span>
        </h1>
        <div class="meta">
          {{ requestTypeLabel(store.currentDoc.request_type) }} ·
          Khoa {{ store.currentDoc.requesting_department }} ·
          Model {{ store.currentDoc.device_model_ref }} ·
          Số lượng {{ store.currentDoc.quantity }} ·
          Năm dự kiến {{ store.currentDoc.target_year }}
        </div>
      </div>
      <div class="header-actions">
        <button class="btn btn-outline" @click="$router.back()">← Quay lại</button>
      </div>
    </div>

    <!-- Tiến trình duyệt -->
    <div class="stepper">
      <span v-for="(s, i) in WORKFLOW_STATES" :key="s"
            :class="['step', stepClass(s, i)]">
        {{ stateLabel(s) }}
      </span>
    </div>

    <div v-if="store.error" class="alert alert-danger">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <!-- Thẻ nội dung -->
    <div class="tabs">
      <button v-for="t in TABS" :key="t.id"
              :class="['tab', { active: activeTab === t.id }]"
              @click="activeTab = t.id">
        {{ t.label }}
      </button>
    </div>

    <!-- Thẻ 1: Tổng quan -->
    <section v-show="activeTab === 'overview'" class="tab-content">
      <div class="grid-2col">
        <div class="card">
          <h3>Lý do lâm sàng</h3>
          <p class="justification">{{ store.currentDoc.clinical_justification }}</p>
          <div class="meta">
            Độ dài: {{ (store.currentDoc.clinical_justification || '').length }} ký tự
            <span v-if="(store.currentDoc.clinical_justification || '').length < 200" class="error-text">
              (cần tối thiểu 200 ký tự để gửi duyệt)
            </span>
          </div>
        </div>
        <div class="card">
          <h3>Thiết bị cần thay thế</h3>
          <p v-if="store.currentDoc.replacement_for_asset">
            {{ store.currentDoc.replacement_for_asset }}
          </p>
          <p v-else class="muted">
            Không có (đề xuất {{ requestTypeLabel(store.currentDoc.request_type) }})
          </p>
          <div v-if="store.currentDoc.utilization_pct_12m != null" class="kpi-mini">
            <div><strong>Tỷ lệ sử dụng 12 tháng:</strong> {{ store.currentDoc.utilization_pct_12m }}%</div>
            <div><strong>Thời gian ngừng hoạt động:</strong> {{ store.currentDoc.downtime_hr_12m }} giờ</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Thẻ 2: Chấm điểm ưu tiên -->
    <section v-show="activeTab === 'scoring'" class="tab-content">
      <div class="card">
        <h3>Chấm điểm ưu tiên (6 tiêu chí)</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Tiêu chí</th>
              <th class="num">Điểm (1-5)</th>
              <th class="num">Trọng số</th>
              <th class="num">Điểm sau trọng số</th>
              <th>Lý giải</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in editableRows" :key="i">
              <td>{{ criterionLabel(row.criterion) }}</td>
              <td class="num">
                <input v-model.number="row.score" type="number" min="1" max="5" :disabled="!editable" />
              </td>
              <td class="num">{{ row.weight_pct?.toFixed(0) }}%</td>
              <td class="num"><strong>{{ row.weighted?.toFixed(4) }}</strong></td>
              <td>
                <input v-model="row.evidence" type="text" placeholder="Lý giải..." :disabled="!editable" />
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3"><strong>Tổng điểm</strong></td>
              <td class="num"><strong>{{ store.currentDoc.weighted_score?.toFixed(4) }}</strong></td>
              <td>
                <span v-if="store.currentDoc.priority_class"
                      :class="['badge', 'priority-' + store.currentDoc.priority_class]">
                  Mức ưu tiên: {{ priorityBadge(store.currentDoc.priority_class) }}
                </span>
              </td>
            </tr>
          </tfoot>
        </table>
        <div v-if="editable" class="actions">
          <button class="btn btn-primary" @click="saveScoring">Lưu chấm điểm</button>
        </div>
      </div>
    </section>

    <!-- Thẻ 3: Dự toán -->
    <section v-show="activeTab === 'budget'" class="tab-content">
      <div class="grid-2col">
        <div class="card">
          <h3>Đầu tư mua sắm</h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>Hạng mục</th>
                <th class="num">Số lượng</th>
                <th class="num">Đơn giá</th>
                <th class="num">Thành tiền</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in capexLines" :key="r.idx">
                <td>{{ budgetLineLabel(r.line_type) }}</td>
                <td class="num">{{ r.qty }}</td>
                <td class="num">{{ formatVnd(r.unit_cost) }}</td>
                <td class="num">{{ formatVnd(r.amount || 0) }}</td>
              </tr>
              <tr v-if="!capexLines.length">
                <td colspan="4" class="muted text-center">Chưa có dòng đầu tư</td>
              </tr>
            </tbody>
            <tfoot v-if="capexLines.length">
              <tr>
                <td colspan="3"><strong>Tổng đầu tư mua sắm</strong></td>
                <td class="num"><strong>{{ formatVnd(store.currentDoc.total_capex || 0) }}</strong></td>
              </tr>
            </tfoot>
          </table>
        </div>
        <div class="card">
          <h3>Chi phí vận hành 5 năm</h3>
          <table class="data-table">
            <thead>
              <tr><th>Năm</th><th>Hạng mục</th><th class="num">Số tiền</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in opexLines" :key="r.idx">
                <td>Năm thứ {{ r.year_offset }}</td>
                <td>{{ budgetLineLabel(r.line_type) }}</td>
                <td class="num">{{ formatVnd(r.amount || 0) }}</td>
              </tr>
              <tr v-if="!opexLines.length">
                <td colspan="3" class="muted text-center">Chưa có dòng vận hành</td>
              </tr>
            </tbody>
            <tfoot v-if="opexLines.length">
              <tr>
                <td colspan="2"><strong>Tổng vận hành 5 năm</strong></td>
                <td class="num"><strong>{{ formatVnd(store.currentDoc.total_opex_5y || 0) }}</strong></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
      <div class="card tco-summary">
        <strong>Tổng chi phí 5 năm:</strong> {{ formatVnd(store.currentDoc.tco_5y || 0) }}
        <span class="muted">|
          Nguồn vốn: {{ fundingLabel(store.currentDoc.funding_source) }}
        </span>
        <span class="muted">|
          Người phê duyệt: {{ store.currentDoc.board_approver || 'Chưa chọn' }}
        </span>
      </div>
    </section>

    <!-- Hành động quy trình -->
    <div class="action-bar">
      <button v-if="canSubmit" class="btn btn-primary" @click="doTransition('Gửi đề xuất')">Gửi đề xuất</button>
      <button v-if="canApprove" class="btn btn-success" @click="doApprove">Phê duyệt</button>
      <button v-if="canReject" class="btn btn-danger" @click="doReject">Bác đề xuất</button>
    </div>
  </div>

  <div v-else-if="store.loading" class="loading">Đang tải...</div>
  <div v-else class="loading muted">Không có dữ liệu</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useImm01Store } from '@/stores/imm01'
import type { NeedsPriorityScoringRow, NeedsRequestState } from '@/types/imm01'
import {
  stateLabel, requestTypeLabel, criterionLabel,
  priorityBadge, formatVnd,
} from '@/utils/wave2Labels'

const route = useRoute()
const store = useImm01Store()
const props = defineProps<{ id: string }>()

type TabId = 'overview' | 'scoring' | 'budget'
const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: '1. Tổng quan' },
  { id: 'scoring',  label: '2. Chấm điểm ưu tiên' },
  { id: 'budget',   label: '3. Dự toán' },
]
const activeTab = ref<TabId>('overview')

const WORKFLOW_STATES: NeedsRequestState[] = [
  'Draft', 'Submitted', 'Reviewing', 'Prioritized',
  'Budgeted', 'Pending Approval', 'Approved',
]

const editable = computed(() => store.currentDoc?.docstatus === 0)
const editableRows = computed<NeedsPriorityScoringRow[]>(() => store.currentDoc?.scoring_rows || [])
const capexLines = computed(() => (store.currentDoc?.budget_lines || []).filter(l => l.budget_section === 'CAPEX'))
const opexLines = computed(() =>
  (store.currentDoc?.budget_lines || []).filter(l => l.budget_section === 'OPEX')
    .sort((a, b) => (a.year_offset || 0) - (b.year_offset || 0)),
)

const canSubmit = computed(() => store.currentDoc?.workflow_state === 'Draft')
const canApprove = computed(() => store.currentDoc?.workflow_state === 'Pending Approval')
const canReject = computed(() => store.currentDoc?.workflow_state === 'Pending Approval')

function stepClass(_s: NeedsRequestState, i: number): string {
  const cur = store.currentDoc?.workflow_state
  if (!cur) return ''
  const curIdx = WORKFLOW_STATES.indexOf(cur)
  if (i < curIdx) return 'done'
  if (i === curIdx) return 'active'
  return ''
}

// Bản dịch nhãn dòng dự toán (line_type) sang tiếng Việt
function budgetLineLabel(t?: string): string {
  return ({
    'Device':      'Mua thiết bị chính',
    'Install':     'Lắp đặt',
    'Training':    'Đào tạo người dùng',
    'Infra':       'Cải tạo hạ tầng',
    'Accessory':   'Phụ kiện',
    'PM':          'Bảo trì định kỳ',
    'Calibration': 'Hiệu chuẩn',
    'Spare':       'Phụ tùng dự phòng',
    'Consumable':  'Vật tư tiêu hao',
    'Software':    'Phần mềm – nâng cấp',
    'Insurance':   'Bảo hiểm',
    'Other':       'Khác',
  } as Record<string, string>)[t || ''] || (t || '')
}

function fundingLabel(s?: string): string {
  if (!s) return 'Chưa chọn'
  return s  // các giá trị đã ở dạng tiếng Việt: NSNN / Tài trợ / Xã hội hóa / BHYT / Khác
}

async function saveScoring() {
  if (!store.currentDoc?.name) return
  await store.score(store.currentDoc.name, editableRows.value)
  await store.fetchOne(store.currentDoc.name)
}

async function doTransition(action: string) {
  if (!store.currentDoc?.name) return
  if (!globalThis.confirm(`Thực hiện hành động "${action}" cho phiếu ${store.currentDoc.name}?`)) return
  await store.transition(store.currentDoc.name, action)
  await store.fetchOne(store.currentDoc.name)
}

async function doApprove() {
  if (!store.currentDoc?.name) return
  const approver = globalThis.prompt('Nhập tài khoản người duyệt thuộc Ban Giám đốc:', 'admin@example.com')
  if (!approver) return
  await store.approve(store.currentDoc.name, approver, 'Đã duyệt')
  await store.fetchOne(store.currentDoc.name)
}

async function doReject() {
  if (!store.currentDoc?.name) return
  const reason = globalThis.prompt('Lý do bác đề xuất:')
  if (!reason) return
  await store.reject(store.currentDoc.name, reason)
  await store.fetchOne(store.currentDoc.name)
}

onMounted(() => {
  const name = props.id || (route.params.id as string)
  if (name) store.fetchOne(name)
})
</script>

<style scoped>
.needs-request-detail { padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
.meta { color: #6b7280; font-size: 0.85rem; }
.muted { color: #6b7280; }
.error-text { color: #b91c1c; }
.stepper { display: flex; gap: 0.5rem; margin: 1rem 0 1.5rem; flex-wrap: wrap; }
.step { padding: 0.4rem 0.9rem; border-radius: 999px; background: #f3f4f6; color: #6b7280; font-size: 0.8rem; }
.step.done { background: #d1fae5; color: #065f46; }
.step.active { background: #2563eb; color: white; font-weight: 600; }
.tabs { display: flex; gap: 0.25rem; border-bottom: 2px solid #e5e7eb; margin-bottom: 1rem; }
.tab { padding: 0.6rem 1.2rem; border: none; background: none; cursor: pointer; font-weight: 500; color: #6b7280; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.tab.active { color: #2563eb; border-bottom-color: #2563eb; }
.tab-content { animation: fade 0.2s ease-in; }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; font-size: 1rem; color: #111827; }
.justification { white-space: pre-wrap; }
.kpi-mini { display: flex; gap: 1rem; margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #f1f5f9; font-size: 0.9rem; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; font-size: 0.9rem; }
.data-table th { background: #f9fafb; font-weight: 600; }
.data-table .num { text-align: right; }
.data-table input { width: 100%; padding: 0.3rem; border: 1px solid #d1d5db; border-radius: 4px; }
.data-table input:disabled { background: #f9fafb; }
.text-center { text-align: center; }
.tco-summary { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
.actions { padding: 0.75rem 0; }
.action-bar { position: sticky; bottom: 0; background: white; padding: 0.75rem 1rem; margin-top: 1rem; border-top: 1px solid #e5e7eb; display: flex; gap: 0.5rem; justify-content: flex-end; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }
.alert-close { background: none; border: none; cursor: pointer; font-size: 1.25rem; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.priority-P1 { background: #fee2e2; color: #b91c1c; }
.badge.priority-P2 { background: #fed7aa; color: #c2410c; }
.badge.priority-P3 { background: #fef9c3; color: #a16207; }
.badge.priority-P4 { background: #e5e7eb; color: #4b5563; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-success { background: #10b981; color: white; border-color: #10b981; }
.btn-danger { background: #ef4444; color: white; border-color: #ef4444; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.loading { padding: 3rem; text-align: center; color: #6b7280; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; }
</style>
