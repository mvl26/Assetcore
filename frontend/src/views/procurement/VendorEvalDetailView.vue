<template>
  <DetailPageShell
    :loading="loading"
    :error-kind="loadKind"
    :error-message="loadMsg"
    :doc="store.currentEval"
    entity-label="hồ sơ đánh giá nhà cung cấp"
    :record-id="evalId"
    back-label="Về danh sách đánh giá nhà cung cấp"
    @retry="loadEvaluation()"
    @back="router.push('/vendor-evaluations')">
    <template #title>
      <div class="page-header">
        <div>
          <h1>{{ store.currentEval?.name || evalId }}</h1>
          <div v-if="store.currentEval" class="meta">
            Hồ sơ kỹ thuật: {{ store.currentEval.spec_ref }} ·
            Ngày khởi tạo: {{ formatVnDate(store.currentEval.draft_date) }}
          </div>
        </div>
        <button class="btn btn-outline" @click="$router.back()">← Quay lại</button>
      </div>
    </template>

    <!-- Hành động server-driven (1 nút / action hợp lệ theo allowed_transitions) — CHỈ
         tồn tại ở trạng thái content ⇒ 0 nút chết trên bản ghi không đọc được. -->
    <template #actions>
      <button v-for="action in availableActions" :key="action"
              class="btn btn-primary" data-testid="workflow-action" :data-action="action"
              @click="doTransition(action)">
        {{ action }}
      </button>
    </template>

    <template v-if="store.currentEval">
    <!-- Tiến trình -->
    <div class="stepper">
      <span v-for="(s, i) in WORKFLOW_STATES" :key="s" :class="['step', stepClass(i)]">
        {{ stateLabel(s) }}
      </span>
    </div>

    <div v-if="store.error" class="alert alert-danger">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button v-for="t in TABS" :key="t.id"
              :class="['tab', { active: tab === t.id }]" @click="tab = t.id">
        {{ t.label }}
      </button>
    </div>

    <!-- Thẻ: Ứng viên + Báo giá -->
    <section v-show="tab === 'candidates'" class="tab-content">
      <!-- INV-VE-TIE: cảnh báo HÒA điểm — KHÔNG để '—' câm khiến tưởng chưa chấm -->
      <div v-if="hasTopTie" class="tie-banner" role="alert" aria-live="assertive">
        <strong>⚖ {{ EVAL_TIE_BANNER }}</strong>
        <p>
          Có {{ tiedSuppliers.length }} nhà cung cấp đồng hạng nhất — hệ thống KHÔNG tự gợi ý
          trúng thầu. Người chấm cần áp tiêu chí phân định có hồ sơ.
        </p>
        <ul class="tie-list">
          <li v-for="s in tiedSuppliers" :key="s.supplier">{{ s.label }}</li>
        </ul>
      </div>

      <div class="card">
        <div class="card-head">
          <h3>Ứng viên ({{ store.currentEval.candidates?.length || 0 }})</h3>
          <button v-if="editable" class="btn btn-sm btn-primary" @click="showAddCandidate = true">
            + Thêm nhà cung cấp
          </button>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Nhà cung cấp</th>
              <th class="center">Trạng thái cấp phép</th>
              <th class="num">Điểm tổng</th>
              <th>Người duyệt ngoại lệ</th>
              <th>Ghi chú</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!store.currentEval.candidates?.length">
              <td colspan="5" class="muted text-center">Chưa có ứng viên nào.</td>
            </tr>
            <tr v-for="c in store.currentEval.candidates || []" :key="c.idx"
                :class="{
                  winner: !hasTopTie && store.currentEval.recommended_candidate === c.supplier,
                  tied: hasTopTie && tiedSet.has(c.supplier),
                }">
              <td>
                <!-- Chỉ 1 dòng được gắn 'Gợi ý trúng thầu' khi KHÔNG hòa -->
                <strong v-if="!hasTopTie && store.currentEval.recommended_candidate === c.supplier"
                        class="rec-tag" title="Gợi ý trúng thầu">★ Gợi ý trúng thầu</strong>
                <span v-else-if="hasTopTie && tiedSet.has(c.supplier)" class="tied-tag"
                      title="Đồng hạng nhất — chờ phân định thủ công">⚖ Đồng hạng nhất</span>
                <div>{{ c.supplier_name || c.supplier }}</div>
              </td>
              <td class="center">
                <span :class="['badge', c.in_avl ? 'avl-yes' : 'avl-no']">
                  {{ c.in_avl ? '✓ Đã được duyệt' : '⚠ Chưa được duyệt' }}
                </span>
              </td>
              <td class="num"><strong>{{ c.weighted_score?.toFixed(4) ?? '—' }}</strong></td>
              <td>{{ c.sign_off_non_avl || '—' }}</td>
              <td>{{ c.notes || '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3>Báo giá ({{ store.currentEval.quotations?.length || 0 }})</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Nhà cung cấp</th>
              <th>Số báo giá</th>
              <th>Hết hạn</th>
              <th class="num">Giá</th>
              <th>Điều khoản thanh toán</th>
              <th class="num">Giao hàng (ngày)</th>
              <th class="num">Bảo hành (tháng)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!store.currentEval.quotations?.length">
              <td colspan="7" class="muted text-center">Chưa nhập báo giá.</td>
            </tr>
            <tr v-for="q in store.currentEval.quotations || []" :key="q.idx">
              <td>{{ q.candidate_supplier_name || q.candidate_supplier }}</td>
              <td>{{ q.quotation_no }}</td>
              <td :class="{ expired: isExpired(q.quotation_validity) }">
                {{ formatVnDate(q.quotation_validity) }}
              </td>
              <td class="num">{{ formatVnd(q.price) }}</td>
              <td>{{ q.payment_terms }}</td>
              <td class="num">{{ q.delivery_days }}</td>
              <td class="num">{{ q.warranty_months }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="editable && store.currentEval.candidates?.length" class="card-footer">
          <button class="btn btn-outline" @click="showAddQuote = true">+ Thêm báo giá</button>
        </div>
      </div>
    </section>

    <!-- Thẻ: Chấm điểm -->
    <section v-show="tab === 'scoring'" class="tab-content">
      <div class="card">
        <h3>Bộ tiêu chí chấm điểm</h3>
        <table class="data-table small">
          <thead>
            <tr>
              <th>Nhóm tiêu chí</th>
              <th>Tiêu chí</th>
              <th class="num">Trọng số</th>
              <th>Vai trò chấm điểm</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in store.currentEval.criteria || []" :key="c.criterion">
              <td><span class="badge">{{ evalGroupLabel(c.group) }}</span></td>
              <td>{{ c.criterion }}</td>
              <td class="num">{{ c.weight_pct }}%</td>
              <td>{{ c.scorer_role || '—' }}</td>
            </tr>
            <tr v-if="!store.currentEval.criteria?.length">
              <td colspan="4" class="muted text-center">Chưa có tiêu chí.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="editable && store.currentEval.candidates?.length && store.currentEval.criteria?.length"
           class="card">
        <div class="card-head">
          <h3>Chấm điểm theo nhóm tiêu chí</h3>
          <select v-model="scoringGroup">
            <option v-for="g in groupSet" :key="g" :value="g">{{ evalGroupLabel(g) }}</option>
          </select>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Nhà cung cấp</th>
              <th v-for="c in criteriaInGroup" :key="c.criterion" class="num">
                {{ c.criterion }}<br /><span class="muted small">({{ c.weight_pct }}%)</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in store.currentEval.candidates || []" :key="c.idx">
              <td>{{ c.supplier_name || c.supplier }}</td>
              <td v-for="crit in criteriaInGroup" :key="crit.criterion" class="num">
                <input type="number" min="1" max="5" step="0.5"
                       :value="getScore(c.supplier, crit.criterion)"
                       @input="setScore(c.supplier, crit.criterion, ($event.target as HTMLInputElement).value)" />
              </td>
            </tr>
          </tbody>
        </table>
        <div class="card-footer">
          <button class="btn btn-primary" @click="saveScoring" :disabled="savingScores">
            {{ savingScores ? 'Đang lưu…' : `Lưu điểm nhóm "${evalGroupLabel(scoringGroup)}"` }}
          </button>
        </div>
      </div>
    </section>

    <!-- Thẻ: Scorecard (FE-03-02) -->
    <section v-show="tab === 'scorecard'" class="tab-content">
      <div class="card">
        <h3>Bảng điểm nhà cung cấp</h3>
        <div class="card-head">
          <label>Nhà cung cấp:
            <select v-model="scorecardSupplier">
              <option value="">— Chọn —</option>
              <option v-for="c in store.currentEval.candidates || []" :key="c.idx" :value="c.supplier">
                {{ c.supplier_name || c.supplier }}
              </option>
            </select>
          </label>
          <label>Năm: <input v-model.number="scorecardYear" type="number" /></label>
          <label>Quý: <input v-model.number="scorecardQuarter" type="number" min="1" max="4" /></label>
          <button class="btn btn-primary" :disabled="!scorecardSupplier || scorecardBusy"
                  @click="loadScorecard">
            {{ scorecardBusy ? 'Đang tải...' : 'Xem' }}
          </button>
        </div>
        <div v-if="scorecardError" class="alert alert-danger">{{ scorecardError }}</div>
        <div v-if="scorecard" class="scorecard">
          <div class="score-display">
            <span class="score-value">{{ Number(scorecard.overall_score || 0).toFixed(2) }}</span>
            <span class="score-label">/ 5 (kỳ {{ scorecard.period_year }}-Q{{ scorecard.period_quarter }})</span>
          </div>
          <table class="data-table small">
            <thead>
              <tr><th>Chỉ số hiệu suất</th><th class="num">Điểm</th><th class="num">Trọng số</th><th class="num">Điểm trọng số</th></tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in (scorecard.kpi_rows || [])" :key="i">
                <td>{{ r.kpi || r.criterion }}</td>
                <td class="num">{{ r.score }}</td>
                <td class="num">{{ r.weight_pct }}%</td>
                <td class="num">{{ r.weighted }}</td>
              </tr>
              <tr v-if="!(scorecard.kpi_rows || []).length">
                <td colspan="4" class="muted text-center">Không có dòng chỉ số hiệu suất.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Hộp thoại: Thêm nhà cung cấp -->
    <div v-if="showAddCandidate" class="modal-overlay" @click.self="showAddCandidate = false">
      <div class="modal">
        <div class="modal-head">
          <h3>Thêm nhà cung cấp ứng viên</h3>
          <button class="btn-close" @click="showAddCandidate = false">×</button>
        </div>
        <div class="modal-body">
          <label>Nhà cung cấp <span class="req">*</span>
            <select v-model="newCand.supplier">
              <option value="">— Chọn nhà cung cấp —</option>
              <option v-for="s in supplierOptions" :key="s.name" :value="s.name">
                {{ s.supplier_name }} ({{ s.name }})
              </option>
            </select>
          </label>
          <label>Người ký duyệt ngoại lệ
            <input v-model="newCand.sign_off_non_avl" type="email"
                   placeholder="email@benhvien.vn — chỉ điền khi nhà cung cấp chưa được duyệt" />
          </label>
          <p v-if="addCandWarning" class="warn-msg">⚠ {{ addCandWarning }}</p>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" @click="showAddCandidate = false">Huỷ</button>
          <button class="btn btn-primary" :disabled="!newCand.supplier" @click="doAddCandidate">Thêm</button>
        </div>
      </div>
    </div>

    <!-- Hộp thoại: Thêm báo giá -->
    <div v-if="showAddQuote" class="modal-overlay" @click.self="showAddQuote = false">
      <div class="modal">
        <div class="modal-head">
          <h3>Thêm báo giá</h3>
          <button class="btn-close" @click="showAddQuote = false">×</button>
        </div>
        <div class="modal-body">
          <label>Nhà cung cấp <span class="req">*</span>
            <select v-model="newQuote.candidate_supplier">
              <option value="">— Chọn —</option>
              <option v-for="c in store.currentEval.candidates || []" :key="c.idx" :value="c.supplier">
                {{ c.supplier_name || c.supplier }}
              </option>
            </select>
          </label>
          <label>Số báo giá
            <input v-model="newQuote.quotation_no" type="text" placeholder="Số báo giá của nhà cung cấp" />
          </label>
          <label>Ngày báo giá <DateInput v-model="newQuote.quotation_date" class="form-input w-full" /></label>
          <label>Hết hạn báo giá <span class="req">*</span>
            <DateInput v-model="newQuote.quotation_validity" class="form-input w-full" />
          </label>
          <label>Giá (đồng) <span class="req">*</span>
            <CurrencyInput v-model="newQuote.price" aria-label="Giá báo giá" class="form-input w-full" />
          </label>
          <label>Điều khoản thanh toán
            <input v-model="newQuote.payment_terms" type="text"
                   placeholder="Ví dụ: 30 ngày sau giao / 60 ngày sau nghiệm thu" />
          </label>
          <div class="grid-2">
            <label>Thời gian giao hàng (ngày)
              <input v-model.number="newQuote.delivery_days" type="number" />
            </label>
            <label>Thời hạn bảo hành (tháng)
              <input v-model.number="newQuote.warranty_months" type="number" />
            </label>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" @click="showAddQuote = false">Huỷ</button>
          <button class="btn btn-primary" :disabled="!canSaveQuote" @click="doAddQuote">Thêm</button>
        </div>
      </div>
    </div>
    </template>
  </DetailPageShell>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { useDetailAccess } from '@/composables/useDetailAccess'
import { useImm03Store } from '@/stores/imm03'
import CurrencyInput from '@/components/common/CurrencyInput.vue'
import DateInput from '@/components/common/DateInput.vue'
import {
  scoreEvaluation, addCandidate, submitQuotations, transitionEvalWorkflow,
  getVendorScorecard, listVendorProfiles,
} from '@/api/imm03'
import type { EvalState, VendorQuotationLine } from '@/types/imm03'
import {
  stateLabel, formatVnd, formatVnDate, EVAL_TIE_BANNER, parseTiedCandidates,
} from '@/utils/wave2Labels'
import { useNotify } from '@/composables/useNotify'

const props = defineProps<{ id: string }>()
const route = useRoute()
const store = useImm03Store()
const notify = useNotify()

type TabId = 'candidates' | 'scoring' | 'scorecard'
const TABS: { id: TabId; label: string }[] = [
  { id: 'candidates', label: '1. Ứng viên & Báo giá' },
  { id: 'scoring',    label: '2. Chấm điểm' },
  { id: 'scorecard',  label: '3. Bảng điểm nhà cung cấp' },
]
const tab = ref<TabId>('candidates')

// ── Scorecard (FE-03-02) ──
const scorecardSupplier = ref<string>('')
const scorecardYear     = ref<number>(new Date().getFullYear())
const scorecardQuarter  = ref<number>(Math.floor(new Date().getMonth() / 3) + 1)
const scorecard         = ref<Record<string, any> | null>(null)
const scorecardBusy     = ref(false)
const scorecardError    = ref<string | null>(null)
async function loadScorecard() {
  if (!scorecardSupplier.value) return
  scorecardBusy.value = true
  scorecardError.value = null
  try {
    scorecard.value = await getVendorScorecard(
      scorecardSupplier.value, scorecardYear.value, scorecardQuarter.value,
    ) as Record<string, any>
  } catch (e: unknown) {
    scorecardError.value = e instanceof Error ? e.message : String(e)
    scorecard.value = null
  } finally {
    scorecardBusy.value = false
  }
}

// Bản dịch nhóm tiêu chí (Technical/Commercial/...)
function evalGroupLabel(g?: string): string {
  return ({
    'Technical':  'Kỹ thuật',
    'Commercial': 'Thương mại',
    'Financial':  'Tài chính',
    'Support':    'Hỗ trợ – bảo hành',
    'Compliance': 'Tuân thủ',
  } as Record<string, string>)[g || ''] || (g || '')
}

const WORKFLOW_STATES: EvalState[] = ['Draft', 'Open RFQ', 'Quotation Received', 'Evaluated']

const editable = computed(() => store.currentEval?.docstatus === 0)

// ── INV-VE-TIE: bám cờ BE verbatim, KHÔNG tự suy tie từ điểm ──
const hasTopTie = computed(() => Boolean(store.currentEval?.has_top_tie))
const tiedSet = computed(
  () => new Set(parseTiedCandidates(store.currentEval?.tied_candidates)),
)
// Map supplier → display name (ưu tiên supplier_name, fallback mã) để KHÔNG leak code.
const tiedSuppliers = computed(() => {
  const byCode = new Map(
    (store.currentEval?.candidates || []).map(c => [c.supplier, c.supplier_name || c.supplier]),
  )
  return parseTiedCandidates(store.currentEval?.tied_candidates).map(supplier => ({
    supplier,
    label: byCode.get(supplier) || supplier,
  }))
})

// Server-driven CTA (GATE-8 / LL-FE-51): nút chuyển-trạng-thái gate theo tập ACTION
// hợp lệ do BE emit (SoT = get_evaluation → _EVAL_VALID_TRANSITIONS, parity
// get_decision, khớp fixture 'IMM-03 Vendor Eval Workflow'). KHÔNG hardcode theo
// trạng thái ở client / client-map cũ — gây lệch khi workflow đổi ⇒ QTV/Commissioning
// Manager thấy nút sai quyền. Vắng cờ (BE cũ chưa reload) → [] → degrade an toàn (0 nút).
const availableActions = computed(() => store.currentEval?.allowed_transitions ?? [])

function stepClass(i: number): string {
  const cur = store.currentEval?.workflow_state
  if (!cur || cur === 'Cancelled') return ''
  const ci = WORKFLOW_STATES.indexOf(cur)
  if (i < ci) return 'done'
  if (i === ci) return 'active'
  return ''
}

// Scoring matrix
const scoringGroup = ref('Technical')
const groupSet = computed(() => {
  const s = new Set<string>()
  for (const c of store.currentEval?.criteria || []) s.add(c.group)
  return Array.from(s)
})
const criteriaInGroup = computed(() =>
  (store.currentEval?.criteria || []).filter(c => c.group === scoringGroup.value),
)

// scoresMap[supplier][criterion] = number
const scoresMap = reactive<Record<string, Record<string, number>>>({})
const savingScores = ref(false)

function ensureSupplier(s: string) { if (!scoresMap[s]) scoresMap[s] = {} }
function getScore(supplier: string, criterion: string): number | string {
  return scoresMap[supplier]?.[criterion] ?? ''
}
function setScore(supplier: string, criterion: string, val: string) {
  ensureSupplier(supplier)
  const n = parseFloat(val) || 0
  scoresMap[supplier][criterion] = Math.max(1, Math.min(5, n))
}

async function saveScoring() {
  if (!store.currentEval?.name) return
  savingScores.value = true
  try {
    // Chỉ submit scores cho group đang chấm
    const payload: Record<string, Record<string, number>> = {}
    for (const c of store.currentEval.candidates || []) {
      payload[c.supplier] = {}
      for (const crit of criteriaInGroup.value) {
        const v = scoresMap[c.supplier]?.[crit.criterion]
        if (v != null) payload[c.supplier][crit.criterion] = v
      }
    }
    await scoreEvaluation(store.currentEval.name, scoringGroup.value, payload)
    await store.fetchEvaluation(store.currentEval.name)
  } finally {
    savingScores.value = false
  }
}

// Add candidate
const showAddCandidate = ref(false)
const newCand = reactive({ supplier: '', sign_off_non_avl: '' })
const addCandWarning = ref('')
const supplierOptions = ref<{ name: string; supplier_name: string }[]>([])
async function doAddCandidate() {
  if (!store.currentEval?.name || !newCand.supplier) return
  try {
    const res = await addCandidate(
      store.currentEval.name, newCand.supplier, newCand.sign_off_non_avl,
    )
    if (res.warning) addCandWarning.value = res.warning
    await store.fetchEvaluation(store.currentEval.name)
    if (!res.warning) {
      showAddCandidate.value = false
      newCand.supplier = ''; newCand.sign_off_non_avl = ''
    }
  } catch (e) {
    notify.fromError(e)
  }
}

// Add quotation
const showAddQuote = ref(false)
const newQuote = reactive<Partial<VendorQuotationLine>>({
  candidate_supplier: '', quotation_no: '', quotation_date: '',
  quotation_validity: '', price: 0, payment_terms: '',
  delivery_days: 0, warranty_months: 12,
})
const canSaveQuote = computed(() =>
  newQuote.candidate_supplier && newQuote.quotation_validity && (newQuote.price || 0) > 0,
)
async function doAddQuote() {
  if (!store.currentEval?.name) return
  try {
    await submitQuotations(store.currentEval.name, [newQuote as VendorQuotationLine])
    await store.fetchEvaluation(store.currentEval.name)
    showAddQuote.value = false
    newQuote.quotation_no = ''; newQuote.price = 0
  } catch (e) {
    notify.fromError(e)
  }
}

async function doTransition(action: string) {
  if (!store.currentEval?.name) return
  const ok = await notify.confirm({
    title: 'Xác nhận thao tác',
    body: `Thực hiện "${action}" cho ${store.currentEval.name}?`,
  })
  if (!ok) return
  try {
    await transitionEvalWorkflow(store.currentEval.name, action)
    await store.fetchEvaluation(store.currentEval.name)
  } catch (e) {
    notify.fromError(e)
  }
}

function isExpired(d?: string): boolean {
  return Boolean(d && new Date(d).getTime() < Date.now())
}

// ── Lượt NẠP hồ sơ đánh giá (lô 2, nhóm N4) ───────────────────────────────────
// Mã cũ gọi `store.fetchEvaluation(...)` KHÔNG await, KHÔNG catch ⇒ 403/404/mất mạng rơi
// xuống nhánh `v-else` in «Không có dữ liệu». `stores/imm03` chỉ giữ `error` dạng CHUỖI ⇒
// view tự `try/catch` và giữ ref lỗi riêng (KHÔNG sửa `stores/`, §13.3).
const router = useRouter()
const evalId = computed<string>(() => props.id || (route.params.id as string))
const loading = ref(true)                        // INV-UX4-8 — chống nháy 404 một nhịp
const loadError = ref<unknown>(null)
const { kind: loadKind, message: loadMsg } = useDetailAccess(() => loadError.value)

async function loadEvaluation(): Promise<void> {
  loadError.value = null                         // INV-UX4-7 — xoá lỗi ở DÒNG ĐẦU
  loading.value = true
  try {
    await store.fetchEvaluation(evalId.value)
  } catch (e: unknown) {
    loadError.value = e
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadEvaluation()
  // Danh sách nhà cung cấp là dữ liệu PHỤ: 1×403 ở đây không được làm hỏng màn chính
  // (LL-FE-45 — cùng tinh thần allSettled).
  try {
    const res = await listVendorProfiles({}, 1, 100)
    supplierOptions.value = (res.items || []) as { name: string; supplier_name: string }[]
  } catch { /* danh sách phụ — bỏ qua, ô chọn nhà cung cấp sẽ rỗng */ }
})
</script>

<style scoped>
.vendor-eval-detail { padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
.meta { color: #6b7280; font-size: 0.85rem; }
.muted { color: #6b7280; }
.muted.small { font-size: 0.75rem; }
.stepper { display: flex; gap: 0.5rem; margin: 1rem 0 1.5rem; flex-wrap: wrap; }
.step { padding: 0.4rem 0.9rem; border-radius: 999px; background: #f3f4f6; color: #6b7280; font-size: 0.8rem; }
.step.done { background: #d1fae5; color: #065f46; }
.step.active { background: #2563eb; color: white; font-weight: 600; }
.tabs { display: flex; gap: 0.25rem; border-bottom: 2px solid #e5e7eb; margin-bottom: 1rem; }
.tab { padding: 0.6rem 1.2rem; border: none; background: none; cursor: pointer; font-weight: 500; color: #6b7280; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.tab.active { color: #2563eb; border-bottom-color: #2563eb; }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; }
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.card-head select { padding: 0.4rem; border: 1px solid #d1d5db; border-radius: 4px; }
.card-footer { padding: 0.75rem 0 0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.data-table.small { font-size: 0.85rem; }
.data-table th, .data-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; }
.data-table .num { text-align: right; }
.data-table .center { text-align: center; }
.text-center { text-align: center; }
.data-table tr.winner { background: #fffbeb; }
.data-table tr.tied { background: #fef3f2; }
.rec-tag { color: #b45309; font-size: 0.78rem; display: block; }
.tied-tag { color: #b91c1c; font-size: 0.78rem; font-weight: 600; display: block; }
.tie-banner { background: #fef3f2; border: 1px solid #fca5a5; border-left: 4px solid #dc2626;
  border-radius: 6px; padding: 0.85rem 1.1rem; margin-bottom: 1rem; color: #7f1d1d; }
.tie-banner strong { display: block; font-size: 0.95rem; margin-bottom: 0.25rem; }
.tie-banner p { margin: 0 0 0.5rem; font-size: 0.85rem; }
.tie-list { margin: 0; padding-left: 1.2rem; font-size: 0.85rem; }
.tie-list li { font-weight: 600; }
.data-table input[type="number"] { width: 80px; padding: 0.3rem; border: 1px solid #d1d5db; border-radius: 4px; }
.expired { color: #b91c1c; font-weight: 600; }
.action-bar { position: sticky; bottom: 0; background: white; padding: 0.75rem 1rem; margin-top: 1rem; border-top: 1px solid #e5e7eb; display: flex; gap: 0.5rem; justify-content: flex-end; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-close { background: none; border: none; cursor: pointer; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-sm { padding: 0.3rem 0.7rem; font-size: 0.85rem; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-primary:disabled { background: #9ca3af; border-color: #9ca3af; cursor: not-allowed; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; background: #e5e7eb; color: #374151; }
.badge.avl-yes { background: #d1fae5; color: #065f46; }
.badge.avl-no  { background: #fee2e2; color: #b91c1c; }
.req { color: #ef4444; }
.warn-msg { color: #c2410c; background: #fef3c7; padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; border-radius: 8px; width: 540px; max-width: 90vw; max-height: 90vh; overflow: auto; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid #e5e7eb; }
.modal-head h3 { margin: 0; }
.btn-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; }
.modal-body { padding: 1rem; }
.modal-body label { display: block; margin-bottom: 0.75rem; font-weight: 500; font-size: 0.9rem; }
.modal-body input, .modal-body select { display: block; width: 100%; padding: 0.4rem; border: 1px solid #d1d5db; border-radius: 4px; margin-top: 0.2rem; }
.modal-body .grid-2 { display: grid; grid-template-columns: 1fr; gap: 0.5rem; }
@media (min-width: 480px) { .modal-body .grid-2 { grid-template-columns: 1fr 1fr; } }
.modal-foot { padding: 1rem; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 0.5rem; }
.loading { padding: 3rem; text-align: center; color: #6b7280; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; font-size: 0.85rem; }
.scorecard { margin-top: 1rem; }
.score-display { font-size: 2rem; font-weight: 700; padding: 0.5rem 0 1rem; }
.score-value { color: #065f46; }
.score-label { font-size: 0.9rem; color: #6b7280; font-weight: 400; margin-left: 0.5rem; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.5rem 0.75rem; border-radius: 6px; margin: 0.5rem 0; }
.alert-danger { color: #b91c1c; }
</style>
