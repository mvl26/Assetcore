<template>
  <div class="tech-spec-detail" v-if="store.currentSpec">
    <div class="page-header">
      <div>
        <h1>{{ store.currentSpec.name }} <span class="muted">phiên bản {{ store.currentSpec.version }}</span></h1>
        <div class="meta">
          Mẫu {{ store.currentSpec.device_model_ref }} ·
          Số lượng {{ store.currentSpec.quantity }} ·
          Đề xuất {{ store.currentSpec.source_needs_request }} ·
          Kế hoạch {{ store.currentSpec.source_plan }}
        </div>
      </div>
      <button class="btn btn-outline" @click="$router.back()">← Quay lại</button>
    </div>

    <div class="stepper">
      <span v-for="(s, i) in WORKFLOW_STATES" :key="s" :class="['step', stepClass(s, i)]">
        {{ stateLabel(s) }}
      </span>
    </div>

    <div v-if="store.error" class="alert alert-danger">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="tabs">
      <button v-for="t in TABS" :key="t.id" :class="['tab', { active: tab === t.id }]" @click="tab = t.id">
        {{ t.label }}
      </button>
    </div>

    <!-- Thẻ: Tổng quan -->
    <section v-show="tab === 'overview'" class="tab-content">
      <div class="grid-2col">
        <div class="card">
          <h3>Thông tin hồ sơ</h3>
          <dl>
            <dt>Kế hoạch nguồn:</dt><dd>{{ store.currentSpec.source_plan }}</dd>
            <dt>Đề xuất nhu cầu:</dt><dd>{{ store.currentSpec.source_needs_request }}</dd>
            <dt>Mẫu thiết bị:</dt><dd>{{ store.currentSpec.device_model_ref }}</dd>
            <dt>Nhóm thiết bị:</dt><dd>{{ store.currentSpec.device_category || '—' }}</dd>
            <dt>Số lượng:</dt><dd>{{ store.currentSpec.quantity }}</dd>
            <dt>Phiên bản:</dt><dd>{{ store.currentSpec.version }}</dd>
            <dt v-if="store.currentSpec.parent_spec">Hồ sơ gốc (đã rút):</dt>
            <dd v-if="store.currentSpec.parent_spec">{{ store.currentSpec.parent_spec }}</dd>
          </dl>
        </div>
        <div class="card">
          <h3>Tình trạng phê duyệt</h3>
          <dl>
            <dt>Trạng thái:</dt>
            <dd><span class="badge">{{ stateLabel(store.currentSpec.workflow_state) }}</span></dd>
            <dt>Người duyệt:</dt><dd>{{ store.currentSpec.approver || '—' }}</dd>
            <dt>Ngày duyệt:</dt><dd>{{ formatVnDate(store.currentSpec.approval_date) }}</dd>
            <dt v-if="store.currentSpec.workflow_state === 'Withdrawn'">Lý do rút:</dt>
            <dd v-if="store.currentSpec.workflow_state === 'Withdrawn'">
              {{ store.currentSpec.withdrawal_reason }}
            </dd>
          </dl>
        </div>
      </div>
    </section>

    <!-- Thẻ: Yêu cầu kỹ thuật -->
    <section v-show="tab === 'req'" class="tab-content">
      <div class="card">
        <h3>
          Yêu cầu kỹ thuật
          ({{ store.currentSpec.total_mandatory || 0 }} bắt buộc ·
          {{ store.currentSpec.total_optional || 0 }} tùy chọn)
        </h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>STT</th>
              <th>Nhóm</th>
              <th>Tham số</th>
              <th>Giá trị / Dải</th>
              <th>Đơn vị</th>
              <th class="center">Bắt buộc</th>
              <th class="num">Trọng số</th>
              <th>Phương pháp kiểm tra</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in store.currentSpec.requirements" :key="r.idx">
              <td>{{ r.seq }}</td>
              <td>{{ requirementGroupLabel(r.group) }}</td>
              <td><strong>{{ r.parameter }}</strong></td>
              <td>{{ r.value_or_range }}</td>
              <td>{{ r.unit }}</td>
              <td class="center">{{ r.is_mandatory ? '✓' : '' }}</td>
              <td class="num">{{ r.weight }}</td>
              <td>{{ r.test_method }}</td>
            </tr>
            <tr v-if="!store.currentSpec.requirements?.length">
              <td colspan="8" class="muted text-center">Chưa có yêu cầu kỹ thuật nào.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Thẻ: Hạ tầng -->
    <section v-show="tab === 'infra'" class="tab-content">
      <div class="card">
        <h3>
          Tương thích hạ tầng —
          {{ infraStatusLabel(store.currentSpec.infra_status_overall) || '—' }}
        </h3>
        <div class="infra-grid">
          <div v-for="d in store.currentSpec.infra_compat" :key="d.idx"
               :class="['infra-card', infraClass(d.compatibility_status)]">
            <h4>{{ infraDomainLabel(d.domain) }}</h4>
            <span class="status">{{ infraStatusLabel(d.compatibility_status) }}</span>
            <p v-if="d.required_state" class="meta">Yêu cầu: {{ d.required_state }}</p>
            <p v-if="d.upgrade_cost_estimate" class="meta">
              Chi phí dự kiến: {{ formatVnd(d.upgrade_cost_estimate) }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Thẻ: Phụ thuộc nhà cung cấp -->
    <section v-show="tab === 'lockin'" class="tab-content">
      <div class="card">
        <h3>Đánh giá rủi ro phụ thuộc nhà cung cấp</h3>
        <div class="score-display" v-if="store.currentSpec.lock_in_score != null">
          <span class="score-value" :class="lockClass(store.currentSpec.lock_in_score)">
            {{ store.currentSpec.lock_in_score.toFixed(4) }}
          </span>
          <span class="score-label">/ 5 điểm (mục tiêu ≤ 2,5)</span>
        </div>
        <p v-else class="muted">Chưa có đánh giá rủi ro phụ thuộc nhà cung cấp.</p>
        <div v-if="store.currentSpec.mitigation_plan" class="mitigation">
          <h4>Phương án giảm thiểu rủi ro</h4>
          <p>{{ store.currentSpec.mitigation_plan }}</p>
        </div>
      </div>
    </section>

    <!-- Hành động -->
    <div class="action-bar">
      <button v-if="canLock" class="btn btn-success" @click="doLock">Chốt hồ sơ</button>
      <button v-if="canWithdraw" class="btn btn-danger" @click="doWithdraw">Rút hồ sơ</button>
      <button v-if="canReissue" class="btn btn-primary" @click="doReissue">Phát hành lại (phiên bản mới)</button>
    </div>
  </div>

  <div v-else-if="store.loading" class="loading">Đang tải...</div>
  <div v-else class="loading muted">Không có dữ liệu</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useImm02Store } from '@/stores/imm02'
import type { SpecState } from '@/types/imm02'
import {
  stateLabel, formatVnd, formatVnDate,
  requirementGroupLabel, infraDomainLabel, infraStatusLabel,
} from '@/utils/wave2Labels'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()
const store = useImm02Store()

type TabId = 'overview' | 'req' | 'infra' | 'lockin'
const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: '1. Tổng quan' },
  { id: 'req',      label: '2. Yêu cầu kỹ thuật' },
  { id: 'infra',    label: '3. Tương thích hạ tầng' },
  { id: 'lockin',   label: '4. Phụ thuộc nhà cung cấp' },
]
const tab = ref<TabId>('overview')

const WORKFLOW_STATES: SpecState[] = [
  'Draft', 'Reviewing', 'Benchmarked', 'Risk Assessed', 'Pending Approval', 'Locked',
]

const canLock = computed(() => store.currentSpec?.workflow_state === 'Pending Approval')
const canWithdraw = computed(() =>
  store.currentSpec?.workflow_state === 'Pending Approval'
  || store.currentSpec?.workflow_state === 'Locked',
)
const canReissue = computed(() => store.currentSpec?.workflow_state === 'Withdrawn')

function stepClass(_s: SpecState, i: number): string {
  const cur = store.currentSpec?.workflow_state
  if (!cur || cur === 'Withdrawn') return ''
  const ci = WORKFLOW_STATES.indexOf(cur)
  if (i < ci) return 'done'
  if (i === ci) return 'active'
  return ''
}
function infraClass(s: string): string {
  return ({
    'Compatible': 'ok', 'N/A': 'na',
    'Need Upgrade': 'warn', 'Need Major Upgrade': 'danger',
  } as Record<string, string>)[s] || ''
}
function lockClass(s: number): string {
  if (s > 3.5) return 'danger'; if (s > 2.5) return 'warn'; return 'ok'
}

async function doLock() {
  if (!store.currentSpec?.name) return
  const approver = globalThis.prompt('Tài khoản người chốt hồ sơ:', 'admin@example.com')
  if (!approver) return
  await store.lock(store.currentSpec.name, approver, 'Đã chốt qua giao diện')
  await store.fetchOne(store.currentSpec.name)
}
async function doWithdraw() {
  if (!store.currentSpec?.name) return
  const reason = globalThis.prompt('Lý do rút hồ sơ:')
  if (!reason) return
  await store.withdraw(store.currentSpec.name, reason)
  await store.fetchOne(store.currentSpec.name)
}
async function doReissue() {
  if (!store.currentSpec?.name) return
  const res = await store.reissue(store.currentSpec.name)
  router.push({ name: 'TechSpecDetail', params: { id: res.name } })
}

onMounted(() => { store.fetchOne(props.id || (route.params.id as string)) })
</script>

<style scoped>
.tech-spec-detail { padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
.meta { color: #6b7280; font-size: 0.85rem; }
.muted { color: #6b7280; }
.stepper { display: flex; gap: 0.5rem; margin: 1rem 0 1.5rem; flex-wrap: wrap; }
.step { padding: 0.4rem 0.9rem; border-radius: 999px; background: #f3f4f6; color: #6b7280; font-size: 0.8rem; }
.step.done { background: #d1fae5; color: #065f46; }
.step.active { background: #2563eb; color: white; font-weight: 600; }
.tabs { display: flex; gap: 0.25rem; border-bottom: 2px solid #e5e7eb; margin-bottom: 1rem; }
.tab { padding: 0.6rem 1.2rem; border: none; background: none; cursor: pointer; font-weight: 500; color: #6b7280; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.tab.active { color: #2563eb; border-bottom-color: #2563eb; }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.5rem 1rem; margin: 0; }
dl dt { color: #6b7280; }
dl dd { margin: 0; font-weight: 500; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.data-table th, .data-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; }
.data-table .num { text-align: right; }
.data-table .center { text-align: center; }
.text-center { text-align: center; }
.infra-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
.infra-card { padding: 1rem; border-radius: 8px; border: 1px solid #e5e7eb; background: white; }
.infra-card h4 { margin: 0 0 0.5rem; }
.infra-card .status { font-weight: 600; }
.infra-card.ok { border-left: 4px solid #10b981; }
.infra-card.warn { border-left: 4px solid #f59e0b; }
.infra-card.danger { border-left: 4px solid #ef4444; background: #fef2f2; }
.infra-card.na { opacity: 0.6; }
.score-display { font-size: 2.5rem; font-weight: 700; padding: 1rem; }
.score-value.danger { color: #b91c1c; }
.score-value.warn { color: #c2410c; }
.score-value.ok { color: #065f46; }
.score-label { font-size: 1rem; color: #6b7280; font-weight: 400; margin-left: 0.5rem; }
.mitigation { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #f1f5f9; }
.action-bar { position: sticky; bottom: 0; background: white; padding: 0.75rem 1rem; margin-top: 1rem; border-top: 1px solid #e5e7eb; display: flex; gap: 0.5rem; justify-content: flex-end; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-close { background: none; border: none; cursor: pointer; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-success { background: #10b981; color: white; border-color: #10b981; }
.btn-danger { background: #ef4444; color: white; border-color: #ef4444; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.loading { padding: 3rem; text-align: center; color: #6b7280; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; background: #e5e7eb; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; }
</style>
