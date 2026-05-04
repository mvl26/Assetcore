<template>
  <div class="tech-spec-create">
    <div class="page-header">
      <div>
        <h1>Sinh hồ sơ kỹ thuật từ kế hoạch mua sắm</h1>
        <p class="muted">
          Mỗi đề xuất nhu cầu trong kế hoạch sẽ được sinh thành một hồ sơ kỹ thuật ở trạng thái nháp.
        </p>
      </div>
      <button class="btn btn-outline" @click="$router.back()">← Quay lại</button>
    </div>

    <div v-if="errorMsg" class="alert alert-danger">
      <strong>Lỗi:</strong> {{ errorMsg }}
      <button class="alert-close" @click="errorMsg = ''">×</button>
    </div>

    <!-- Bước 1: Chọn kế hoạch mua sắm -->
    <div class="card">
      <h3>1. Chọn kế hoạch mua sắm đã duyệt</h3>
      <div class="form-row">
        <select v-model="selectedPlan" @change="loadPlanItems">
          <option value="">— Chọn kế hoạch —</option>
          <option v-for="p in approvedPlans" :key="p.name" :value="p.name">
            {{ p.name }} · {{ planPeriodLabel(p.plan_period) }} {{ p.plan_year }} ·
            Tổng ngân sách {{ formatVnd(p.budget_envelope) }}
          </option>
        </select>
      </div>
      <p v-if="!approvedPlans.length" class="muted">
        Chưa có kế hoạch nào ở trạng thái đã duyệt hoặc đang hiệu lực.
        <router-link :to="{ name: 'ProcurementPlanList' }">Xem danh sách kế hoạch →</router-link>
      </p>
    </div>

    <!-- Bước 2: Chọn dòng đề xuất -->
    <div v-if="selectedPlan && planItems.length" class="card">
      <h3>2. Chọn các đề xuất để sinh hồ sơ kỹ thuật</h3>
      <div class="actions-row">
        <label class="check">
          <input type="checkbox" :checked="allChecked" @change="toggleAll" /> Chọn tất cả
        </label>
        <span class="muted">{{ selectedItems.length }} / {{ planItems.length }} đã chọn</span>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th></th>
            <th>Đề xuất nhu cầu</th>
            <th class="num">Hạng ưu tiên</th>
            <th class="num">Điểm</th>
            <th class="num">Ngân sách phân bổ</th>
            <th>Trạng thái</th>
            <th>Hồ sơ đã có</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in planItems" :key="it.name || ''" :class="{ skipped: hasExistingSpec(it.name || '') }">
            <td>
              <input type="checkbox" :value="it.name" v-model="selectedItems"
                     :disabled="hasExistingSpec(it.name || '')" />
            </td>
            <td>{{ it.needs_request }}</td>
            <td class="num">{{ it.priority_rank }}</td>
            <td class="num">{{ it.weighted_score?.toFixed(2) }}</td>
            <td class="num">{{ formatVnd(it.allocated_budget) }}</td>
            <td>
              <span :class="['badge', 'plan-line-' + stateSlug(it.status)]">
                {{ planLineStatusLabel(it.status) }}
              </span>
            </td>
            <td>
              <span v-if="it.name && existingSpecMap[it.name]">{{ existingSpecMap[it.name] }}</span>
              <span v-else class="muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p class="hint">
        Mỗi đề xuất chỉ được sinh tối đa một hồ sơ kỹ thuật còn hiệu lực;
        các đề xuất đã có hồ sơ sẽ bị khóa chọn.
      </p>
    </div>

    <!-- Bước 3: Hành động -->
    <div v-if="selectedPlan" class="action-bar">
      <button class="btn btn-primary"
              :disabled="!selectedItems.length || submitting"
              @click="submit">
        {{ submitting
            ? 'Đang sinh...'
            : `Sinh ${selectedItems.length} hồ sơ kỹ thuật (nháp)` }}
      </button>
    </div>

    <!-- Kết quả -->
    <div v-if="created.length" class="card success-card">
      <h3>✓ Đã sinh {{ created.length }} hồ sơ kỹ thuật</h3>
      <ul>
        <li v-for="name in created" :key="name">
          <router-link :to="{ name: 'TechSpecDetail', params: { id: name } }">{{ name }}</router-link>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listProcurementPlans } from '@/api/imm01'
import { draftFromPlan, listTechSpecs } from '@/api/imm02'
import { ApiError } from '@/api/errors'
import { frappeGet } from '@/api/helpers'
import type { ProcurementPlanListItem, ProcurementPlanLineRow } from '@/types/imm01'
import { stateSlug, formatVnd, planLineStatusLabel } from '@/utils/wave2Labels'

const router = useRouter()

const approvedPlans = ref<ProcurementPlanListItem[]>([])
const selectedPlan = ref<string>('')
const planItems = ref<ProcurementPlanLineRow[]>([])
const selectedItems = ref<string[]>([])
const existingSpecMap = ref<Record<string, string>>({})
const submitting = ref(false)
const errorMsg = ref('')
const created = ref<string[]>([])

const allChecked = computed(() => {
  const eligible = planItems.value.filter(it => !hasExistingSpec(it.name || ''))
  return eligible.length > 0 && eligible.every(it => selectedItems.value.includes(it.name || ''))
})

function toggleAll() {
  const eligible = planItems.value.filter(it => !hasExistingSpec(it.name || ''))
  if (allChecked.value) selectedItems.value = []
  else selectedItems.value = eligible.map(it => it.name || '').filter(Boolean)
}

function hasExistingSpec(planLineName: string): boolean {
  return Boolean(existingSpecMap.value[planLineName])
}

function planPeriodLabel(p?: string): string {
  return ({
    'Q1': 'Quý 1', 'Q2': 'Quý 2', 'Q3': 'Quý 3', 'Q4': 'Quý 4',
    'Annual': 'Cả năm',
  } as Record<string, string>)[p || ''] || (p || '')
}

async function loadApprovedPlans() {
  try {
    const res = await listProcurementPlans({ workflow_state: ['in', ['Approved', 'Active']] }, 1, 100)
    approvedPlans.value = res.items
  } catch (e) {
    errorMsg.value = e instanceof ApiError ? e.message : String(e)
  }
}

async function loadPlanItems() {
  selectedItems.value = []
  planItems.value = []
  existingSpecMap.value = {}
  if (!selectedPlan.value) return
  try {
    // Lấy doc full Plan để có plan_items
    const doc = await frappeGet<{ plan_items: ProcurementPlanLineRow[] }>(
      '/api/method/frappe.client.get',
      { doctype: 'IMM Procurement Plan', name: selectedPlan.value },
    )
    planItems.value = doc.plan_items || []
    // Tra Tech Spec đã có cho plan này
    const specs = await listTechSpecs({ source_plan: selectedPlan.value }, 1, 100)
    for (const s of specs.items) {
      // Map source_plan_line → spec name (nếu có)
      // FE chỉ check theo source_needs_request — đơn giản hơn
      const matched = planItems.value.find(it => it.needs_request === (s as unknown as { source_needs_request: string }).source_needs_request)
      if (matched && matched.name) existingSpecMap.value[matched.name] = s.name
    }
  } catch (e) {
    errorMsg.value = e instanceof ApiError ? e.message : String(e)
  }
}

async function submit() {
  if (!selectedPlan.value || !selectedItems.value.length) return
  submitting.value = true
  errorMsg.value = ''
  try {
    const res = await draftFromPlan(selectedPlan.value, selectedItems.value)
    created.value = res.created
    if (res.created.length === 1) {
      // Auto-redirect khi chỉ sinh 1 spec
      router.push({ name: 'TechSpecDetail', params: { id: res.created[0] } })
    }
  } catch (e) {
    errorMsg.value = e instanceof ApiError ? e.message : String(e)
  } finally {
    submitting.value = false
  }
}

onMounted(() => loadApprovedPlans())
</script>

<style scoped>
.tech-spec-create { padding: 1.5rem; max-width: 1100px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
.muted { color: #6b7280; font-size: 0.85rem; }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; }
.success-card { border-left: 4px solid #10b981; }
.success-card ul { margin: 0; padding-left: 1.5rem; }
.form-row select { padding: 0.55rem; border: 1px solid #d1d5db; border-radius: 6px; min-width: 480px; max-width: 100%; }
.actions-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.check { display: flex; gap: 0.4rem; align-items: center; cursor: pointer; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; font-size: 0.85rem; }
.data-table .num { text-align: right; }
.data-table tr.skipped { opacity: 0.5; background: #f9fafb; }
.hint { font-size: 0.85rem; color: #6b7280; margin-top: 0.5rem; }
.action-bar { position: sticky; bottom: 0; background: white; padding: 0.75rem 1rem; border-top: 1px solid #e5e7eb; display: flex; gap: 0.5rem; justify-content: flex-end; margin-bottom: 1rem; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-close { background: none; border: none; cursor: pointer; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-primary:disabled { background: #9ca3af; border-color: #9ca3af; cursor: not-allowed; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.plan-line-pending-spec { background: #e5e7eb; color: #374151; }
.badge.plan-line-in-spec { background: #fef3c7; color: #92400e; }
.badge.plan-line-in-procurement { background: #dbeafe; color: #1e40af; }
.badge.plan-line-awarded { background: #d1fae5; color: #065f46; }
.badge.plan-line-cancelled { background: #fee2e2; color: #b91c1c; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; }
</style>
