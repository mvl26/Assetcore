<template>
  <div class="decision-detail" v-if="store.currentDecision">
    <div class="page-header">
      <div>
        <h1>{{ store.currentDecision.name }}</h1>
        <div class="meta">
          Hồ sơ kỹ thuật: {{ store.currentDecision.spec_ref }} ·
          Phiếu đánh giá: {{ store.currentDecision.evaluation_ref }}
        </div>
      </div>
      <button class="btn btn-outline" @click="$router.back()">← Quay lại</button>
    </div>

    <div class="stepper">
      <span v-for="(s, i) in WORKFLOW_STATES" :key="s" :class="['step', stepClass(i)]">
        {{ stateLabel(s) }}
      </span>
    </div>

    <div v-if="store.error" class="alert alert-danger">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="grid-2col">
      <!-- Bên trái: Phương án + nhà cung cấp -->
      <div class="card">
        <h3>1. Phương án mua sắm &amp; nhà cung cấp trúng thầu</h3>
        <dl>
          <dt>Phương án mua sắm:</dt>
          <dd>
            <span class="badge method">{{ store.currentDecision.procurement_method || '—' }}</span>
          </dd>
          <dt v-if="store.currentDecision.method_legal_basis">Cơ sở pháp lý:</dt>
          <dd v-if="store.currentDecision.method_legal_basis" class="legal">
            {{ store.currentDecision.method_legal_basis }}
          </dd>
          <dt>Nhà cung cấp trúng thầu:</dt>
          <dd>
            <span v-if="store.currentDecision.winner_supplier">{{ store.currentDecision.winner_supplier }}</span>
            <span v-else class="muted">— chưa chọn —</span>
          </dd>
          <dt>Số lượng:</dt><dd>{{ store.currentDecision.quantity || 1 }}</dd>
          <dt>Giá trúng thầu:</dt>
          <dd>
            <strong v-if="store.currentDecision.awarded_price">
              {{ formatVnd(store.currentDecision.awarded_price) }}
            </strong>
            <span v-else class="muted">— chưa đặt —</span>
          </dd>
          <dt>So với ngân sách:</dt>
          <dd>
            <span v-if="store.currentDecision.envelope_check_pct != null"
                  :class="envClass(store.currentDecision.envelope_check_pct)">
              {{ store.currentDecision.envelope_check_pct.toFixed(1) }}%
            </span>
            <span v-else class="muted">—</span>
          </dd>
        </dl>
      </div>

      <!-- Bên phải: Nguồn vốn + phê duyệt -->
      <div class="card">
        <h3>2. Nguồn vốn &amp; phê duyệt</h3>
        <dl>
          <dt>Nguồn vốn:</dt><dd>{{ store.currentDecision.funding_source || '—' }}</dd>
          <dt>Người phê duyệt:</dt><dd>{{ store.currentDecision.board_approver || '—' }}</dd>
          <dt>Ngày trao thầu:</dt><dd>{{ formatVnDate(store.currentDecision.awarded_date) }}</dd>
          <dt v-if="store.currentDecision.contract_no">Số hợp đồng:</dt>
          <dd v-if="store.currentDecision.contract_no">{{ store.currentDecision.contract_no }}</dd>
          <dt>Đơn hàng đã mint:</dt>
          <dd>
            <span v-if="store.currentDecision.ac_purchase_ref">
              {{ store.currentDecision.ac_purchase_ref }}
            </span>
            <span v-else class="muted">— sẽ tạo khi trao thầu —</span>
          </dd>
        </dl>
      </div>
    </div>

    <!-- Hành động: Phê duyệt trao thầu -->
    <div v-if="canAward" class="card award-card">
      <h3>★ Phê duyệt trao thầu</h3>
      <p class="muted">
        Khi phê duyệt, hệ thống sẽ tự động: (1) tạo đơn hàng nội bộ tương ứng,
        (2) cập nhật trạng thái dòng kế hoạch sang "Đã trao thầu",
        (3) gửi sự kiện sang module Lắp đặt – Nghiệm thu.
      </p>
      <form class="form" @submit.prevent="doAward">
        <div class="grid-2col">
          <label>Nhà cung cấp trúng thầu <span class="req">*</span>
            <select v-model="awardForm.winner_supplier" required>
              <option value="">— Chọn nhà cung cấp —</option>
              <option v-for="c in evalCandidates" :key="c.supplier" :value="c.supplier">
                {{ c.supplier }} (điểm: {{ c.weighted_score?.toFixed(2) ?? '—' }})
                {{ c.in_avl ? '✓ Đã được duyệt' : '⚠ Chưa được duyệt' }}
              </option>
            </select>
          </label>
          <label>Giá trúng thầu (đồng) <span class="req">*</span>
            <input v-model.number="awardForm.awarded_price" type="number" min="1" required />
          </label>
          <label>Nguồn vốn <span class="req">*</span>
            <select v-model="awardForm.funding_source" required>
              <option value="">— Chọn —</option>
              <option v-for="f in FUNDING_SOURCES" :key="f" :value="f">{{ f }}</option>
            </select>
          </label>
          <label>Người phê duyệt <span class="req">*</span>
            <input v-model="awardForm.board_approver" type="email" required placeholder="email@benhvien.vn" />
          </label>
        </div>
        <label>Đường dẫn file hợp đồng (nếu có)
          <input v-model="awardForm.contract_doc" type="text" placeholder="/tep/hop-dong-2026-001.pdf" />
        </label>
        <label>Ghi chú
          <input v-model="awardForm.remarks" type="text" />
        </label>
        <div class="form-actions">
          <button type="submit" class="btn btn-success" :disabled="!canSubmitAward || awarding">
            {{ awarding ? 'Đang phê duyệt...' : '✓ Phê duyệt & tạo đơn hàng' }}
          </button>
        </div>
      </form>
    </div>

    <!-- Hành động: Ghi nhận hợp đồng -->
    <div v-if="canRecordContract" class="card">
      <h3>Ghi nhận hợp đồng đã ký</h3>
      <form class="form" @submit.prevent="doRecordContract">
        <div class="grid-2col">
          <label>Số hợp đồng <span class="req">*</span>
            <input v-model="contractForm.contract_no" type="text" required placeholder="Số hợp đồng đã ký" />
          </label>
          <label>Ngày ký
            <input v-model="contractForm.signed_date" type="date" />
          </label>
        </div>
        <label>Đường dẫn file hợp đồng đã ký
          <input v-model="contractForm.contract_doc" type="text" />
        </label>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary" :disabled="!contractForm.contract_no">
            Ghi nhận
          </button>
        </div>
      </form>
    </div>

    <!-- Workflow transitions (other states) -->
    <div class="action-bar">
      <button v-for="action in availableActions" :key="action"
              class="btn btn-outline" @click="doTransition(action)">
        {{ action }}
      </button>
    </div>
  </div>

  <div v-else-if="store.loading" class="loading">Đang tải…</div>
  <div v-else class="loading muted">Không có dữ liệu</div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import type { DecisionState, VendorEvalCandidate } from '@/types/imm03'
import { stateLabel, formatVnd, formatVnDate } from '@/utils/wave2Labels'

const props = defineProps<{ id: string }>()
const route = useRoute()
const store = useImm03Store()

const WORKFLOW_STATES: DecisionState[] = [
  'Draft', 'Method Selected', 'Negotiation', 'Award Recommended',
  'Pending Approval', 'Awarded', 'Contract Signed', 'PO Issued',
]

const FUNDING_SOURCES = ['NSNN', 'Tài trợ', 'Xã hội hóa', 'BHYT', 'Khác']

const TRANSITIONS_BY_STATE: Record<string, string[]> = {
  'Draft':             ['Chọn phương án'],
  'Method Selected':   ['Bắt đầu thương thảo'],
  'Negotiation':       ['Đề xuất trúng thầu'],
  'Award Recommended': ['Trình Ban Giám đốc'],
}

const evalCandidates = ref<VendorEvalCandidate[]>([])

const awardForm = reactive({
  winner_supplier: '', awarded_price: 0,
  funding_source: '', board_approver: '',
  contract_doc: '', remarks: '',
})
const contractForm = reactive({ contract_no: '', contract_doc: '', signed_date: '' })
const awarding = ref(false)

const canAward = computed(() => store.currentDecision?.workflow_state === 'Pending Approval')
const canRecordContract = computed(() => store.currentDecision?.workflow_state === 'Awarded')
const canSubmitAward = computed(() =>
  awardForm.winner_supplier && awardForm.awarded_price > 0
  && awardForm.funding_source && awardForm.board_approver,
)

const availableActions = computed(() =>
  TRANSITIONS_BY_STATE[store.currentDecision?.workflow_state || ''] || []
)

function stepClass(i: number): string {
  const cur = store.currentDecision?.workflow_state
  if (!cur || cur === 'Cancelled') return ''
  const ci = WORKFLOW_STATES.indexOf(cur)
  if (i < ci) return 'done'
  if (i === ci) return 'active'
  return ''
}

function envClass(pct: number): string {
  if (pct > 105) return 'over'
  if (pct > 90) return 'warn'
  return 'ok'
}

async function loadEvalCandidates() {
  if (!store.currentDecision?.evaluation_ref) return
  try {
    const ev = await store.api.getEvaluation(store.currentDecision.evaluation_ref)
    evalCandidates.value = ev.candidates || []
  } catch { /* ignore — fallback to empty */ }
}

async function doAward() {
  if (!store.currentDecision?.name || !canSubmitAward.value) return
  if (!globalThis.confirm(
    `Phê duyệt trúng thầu cho ${awardForm.winner_supplier} với giá ${formatVnd(awardForm.awarded_price)}?`,
  )) return
  awarding.value = true
  try {
    await store.api.awardDecision(
      store.currentDecision.name,
      awardForm.winner_supplier,
      awardForm.awarded_price,
      awardForm.funding_source,
      awardForm.board_approver,
      awardForm.contract_doc,
      awardForm.remarks,
    )
    await store.fetchDecision(store.currentDecision.name)
  } finally {
    awarding.value = false
  }
}

async function doRecordContract() {
  if (!store.currentDecision?.name) return
  await store.api.recordContract(
    store.currentDecision.name,
    contractForm.contract_no,
    contractForm.contract_doc,
    contractForm.signed_date,
  )
  await store.fetchDecision(store.currentDecision.name)
}

async function doTransition(action: string) {
  if (!store.currentDecision?.name) return
  if (!globalThis.confirm(`Thực hiện "${action}"?`)) return
  await store.api.transitionDecisionWorkflow(store.currentDecision.name, action)
  await store.fetchDecision(store.currentDecision.name)
}

onMounted(async () => {
  await store.fetchDecision(props.id || (route.params.id as string))
  await loadEvalCandidates()
})
</script>

<style scoped>
.decision-detail { padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
.meta { color: #6b7280; font-size: 0.85rem; }
.muted { color: #6b7280; }
.stepper { display: flex; gap: 0.5rem; margin: 1rem 0 1.5rem; flex-wrap: wrap; }
.step { padding: 0.4rem 0.9rem; border-radius: 999px; background: #f3f4f6; color: #6b7280; font-size: 0.8rem; }
.step.done { background: #d1fae5; color: #065f46; }
.step.active { background: #2563eb; color: white; font-weight: 600; }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; }
.award-card { border-left: 4px solid #f59e0b; background: #fffbeb; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.5rem 1rem; margin: 0; }
dl dt { color: #6b7280; }
dl dd { margin: 0; font-weight: 500; }
.legal { font-style: italic; }
.form label { display: block; margin-bottom: 0.75rem; font-weight: 500; }
.form input, .form select {
  display: block; width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; margin-top: 0.25rem;
}
.form-actions { padding-top: 0.5rem; display: flex; justify-content: flex-end; }
.action-bar { position: sticky; bottom: 0; background: white; padding: 0.75rem 1rem; margin-top: 1rem; border-top: 1px solid #e5e7eb; display: flex; gap: 0.5rem; justify-content: flex-end; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-close { background: none; border: none; cursor: pointer; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-success { background: #10b981; color: white; border-color: #10b981; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.method { background: #dbeafe; color: #1e40af; }
.over { color: #b91c1c; font-weight: 700; }
.warn { color: #c2410c; font-weight: 600; }
.ok { color: #065f46; }
.req { color: #ef4444; }
.loading { padding: 3rem; text-align: center; color: #6b7280; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; font-size: 0.85rem; }
</style>
