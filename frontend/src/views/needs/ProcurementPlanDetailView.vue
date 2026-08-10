<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-01 — Procurement Plan Detail (FE-01-02)
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProcurementPlan, rollIntoPlan, listNeedsRequests, approvePlan, activatePlan, closePlan, setBudgetEnvelope, removeFromPlan } from '@/api/imm01'
import type { ProcurementPlanDetail } from '@/api/imm01'
import { formatVnd, stateLabel, stateSlug } from '@/utils/wave2Labels'
import type { NeedsRequestListItem } from '@/types/imm01'
import CurrencyInput from '@/components/common/CurrencyInput.vue'
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { useDetailAccess } from '@/composables/useDetailAccess'

const route = useRoute()
const router = useRouter()
const props = defineProps<{ id?: string }>()

const plan = ref<ProcurementPlanDetail | null>(null)
const loading = ref(true)                        // INV-UX4-8 — chống nháy 404 một nhịp
// `error` giữ nhiệm vụ CŨ: lỗi của 5 HÀNH ĐỘNG (gom đề xuất / duyệt / kích hoạt / đóng kỳ /
// đặt ngân sách). Nối nó vào `:error-kind` ⇒ một cú bấm hỏng THAY CẢ TRANG bằng banner và
// người dùng mất bảng đề xuất đang xem (bẫy 13.9.7) ⇒ lượt nạp có ref RIÊNG.
const error = ref<string | null>(null)
const loadError = ref<unknown>(null)
const { kind: loadKind, message: loadMsg } = useDetailAccess(() => loadError.value)
const planId = computed<string>(() => props.id || (route.params.id as string) || '')
const showRollModal = ref(false)
const candidateNeeds = ref<NeedsRequestListItem[]>([])
const selectedIds = ref<Set<string>>(new Set())
const rolling = ref(false)
const actioning = ref(false)
const editingBudget = ref(false)
const budgetInput = ref(0)
const removingNr = ref<string | null>(null)

const planItems = computed<Record<string, unknown>[]>(() => (plan.value?.plan_items as Record<string, unknown>[]) || [])

// Server-driven CTA gating (GATE-8 / LL-FE-51): nút chuyển-trạng-thái chỉ hiện khi
// BE xác nhận user hiện tại được phép action đó (allowed_transitions). KHÔNG gate theo
// workflow_state literal — tránh "nút hiện rồi bấm mới báo Bạn không có quyền".
function canDo(action: string): boolean {
  return (plan.value?.allowed_transitions ?? []).includes(action)
}

// Guard against double-click race that triggered the previous "browser freeze"
// (native confirm() blocks the event loop indefinitely when CDP can't accept
// the dialog). We now use a non-blocking confirmation modal instead.
const pendingAction = ref<{ fn: (name: string) => Promise<unknown>; msg: string } | null>(null)

function requestAction(fn: (name: string) => Promise<unknown>, confirmMsg: string) {
  if (!plan.value || actioning.value) return
  pendingAction.value = { fn, msg: confirmMsg }
}

async function confirmPendingAction() {
  if (!plan.value || !pendingAction.value || actioning.value) return
  const { fn } = pendingAction.value
  pendingAction.value = null
  actioning.value = true
  try {
    await fn(plan.value.name as string)
    await loadPlan()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    actioning.value = false
  }
}

function cancelPendingAction() {
  pendingAction.value = null
}

async function loadPlan() {
  loadError.value = null                         // INV-UX4-7 — xoá lỗi ở DÒNG ĐẦU
  const name = planId.value
  if (!name) { loading.value = false; return }
  loading.value = true
  try {
    plan.value = await getProcurementPlan(name)
  } catch (e: unknown) {
    loadError.value = e                          // nguyên đối tượng ⇒ phân loại được kind
    plan.value = null                            // dọn ảnh chụp cũ
  } finally {
    loading.value = false
  }
}

async function openRollModal() {
  showRollModal.value = true
  try {
    const res = await listNeedsRequests({ workflow_state: 'Approved' }, 1, 100)
    candidateNeeds.value = res.items
    selectedIds.value = new Set()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function toggleSelect(id: string) {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
}

async function confirmRoll() {
  if (!plan.value || !selectedIds.value.size) return
  rolling.value = true
  try {
    await rollIntoPlan(
      plan.value.plan_year as number,
      plan.value.plan_period as string,
      Array.from(selectedIds.value),
    )
    showRollModal.value = false
    await loadPlan()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    rolling.value = false
  }
}

async function saveBudget() {
  if (!plan.value) return
  actioning.value = true
  try {
    await setBudgetEnvelope(plan.value.name as string, budgetInput.value)
    editingBudget.value = false
    await loadPlan()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    actioning.value = false
  }
}

async function doRemoveNr(nrName: string) {
  // Non-blocking confirmation — native confirm() blocks the event loop and
  // breaks automated testing (see BUG-001 root cause).
  if (!plan.value || removingNr.value) return
  removingNr.value = nrName
  try {
    await removeFromPlan(plan.value.name as string, nrName)
    await loadPlan()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    removingNr.value = null
  }
}

onMounted(loadPlan)
</script>

<template>
  <DetailPageShell
    :loading="loading"
    :error-kind="loadKind"
    :error-message="loadMsg"
    :doc="plan"
    entity-label="kế hoạch mua sắm"
    :record-id="planId"
    back-label="Về danh sách kế hoạch mua sắm"
    @retry="loadPlan()"
    @back="router.push('/procurement-plans')">
    <template #title>
      <div class="page-header">
        <div>
          <h1>
            {{ plan?.name || planId }}
            <span v-if="plan" :class="['badge', 'state-' + stateSlug(plan.workflow_state as string)]">
              {{ stateLabel(plan.workflow_state as string) }}
            </span>
          </h1>
          <div v-if="plan" class="meta">
            Kỳ {{ plan.plan_period }} · Năm {{ plan.plan_year }}
          </div>
        </div>
      </div>
    </template>

    <!-- CTA vòng đời — CHỈ tồn tại ở trạng thái content (AC-UX-053).
         5 chỗ gate `workflow_state === 'Draft'` giữ NGUYÊN ở lô này: chúng cần cờ server
         `can_edit`, là hard-dependency BE ⇒ AC-UX-049, ngoài phạm vi lô 2. -->
    <template #actions>
      <button class="btn btn-outline" data-testid="cta-back" @click="router.back()">← Quay lại</button>
      <button class="btn btn-outline" data-testid="cta-roll-in" @click="openRollModal"
              v-if="plan && plan.workflow_state === 'Draft'">
        Đưa đề xuất vào kế hoạch
      </button>
      <button class="btn btn-primary" :disabled="actioning"
              v-if="canDo('Phê duyệt kế hoạch')" data-testid="cta-approve"
              @click="requestAction(approvePlan, 'Phê duyệt kế hoạch này?')">
        {{ actioning ? 'Đang xử lý...' : 'Phê duyệt' }}
      </button>
      <button class="btn btn-primary" :disabled="actioning"
              v-if="canDo('Kích hoạt')" data-testid="cta-activate"
              @click="requestAction(activatePlan, 'Kích hoạt kế hoạch? Kế hoạch sẽ chuyển sang trạng thái Đang hiệu lực.')">
        {{ actioning ? 'Đang xử lý...' : 'Kích hoạt' }}
      </button>
      <button class="btn btn-outline btn-danger" :disabled="actioning"
              v-if="canDo('Đóng kỳ kế hoạch')" data-testid="cta-close"
              @click="requestAction(closePlan, 'Đóng kế hoạch? Hành động không thể hoàn tác.')">
        {{ actioning ? 'Đang xử lý...' : 'Đóng kế hoạch' }}
      </button>
    </template>

    <template v-if="plan">
      <!-- Lỗi HÀNH ĐỘNG — kênh riêng, KHÔNG thay cả trang (bẫy 13.9.7). -->
      <div v-if="error" role="alert" class="alert-error"><strong>Lỗi:</strong> {{ error }}</div>

      <div class="grid-3col">
        <div class="card">
          <div class="muted">Ngân sách
            <button v-if="plan.workflow_state === 'Draft' && !editingBudget"
                    class="text-xs text-blue-500 hover:underline ml-2"
                    @click="() => { budgetInput = (plan?.budget_envelope as number) || 0; editingBudget = true }">
              Sửa
            </button>
          </div>
          <div v-if="editingBudget" class="mt-1 flex gap-2 items-center">
            <CurrencyInput v-model="budgetInput" aria-label="Ngân sách"
                   class="w-full border border-gray-300 rounded px-2 py-1 text-sm" />
            <button class="text-xs bg-blue-600 text-white px-2 py-1 rounded" :disabled="actioning" @click="saveBudget">Lưu</button>
            <button class="text-xs px-2 py-1 rounded border" @click="editingBudget = false">Hủy</button>
          </div>
          <div v-else class="kpi">{{ formatVnd((plan.budget_envelope as number) || 0) }}</div>
        </div>
        <div class="card">
          <div class="muted">Đã phân bổ</div>
          <div class="kpi">{{ formatVnd((plan.allocated_capex as number) || 0) }}</div>
        </div>
        <div class="card">
          <div class="muted">Tỷ lệ sử dụng</div>
          <div class="kpi">{{ ((plan.utilization_pct as number) || 0).toFixed(1) }}%</div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between mb-2">
          <h3 style="margin:0">Danh sách Đề nghị nhu cầu đã gom</h3>
          <button v-if="plan.workflow_state === 'Draft'" class="btn btn-outline text-sm" @click="openRollModal">
            + Thêm đề xuất
          </button>
        </div>
        <table v-if="planItems.length" class="data-table">
          <thead>
            <tr>
              <th>Mã đề xuất</th>
              <th>Khoa</th>
              <th class="num">Điểm ưu tiên</th>
              <th class="num">Đầu tư mua sắm dự kiến</th>
              <th class="num">Tổng chi phí sở hữu 5 năm</th>
              <th v-if="plan.workflow_state === 'Draft'"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(it, i) in planItems" :key="i">
              <td class="font-mono text-sm">{{ it.needs_request || it.needs_request_ref || it.name }}</td>
              <td>{{ it.department_name || it.requesting_department || '—' }}</td>
              <td class="num">{{ it.weighted_score != null ? Number(it.weighted_score).toFixed(2) : (it.priority_rank || '—') }}</td>
              <td class="num">{{ formatVnd((it.allocated_budget as number) || (it.allocated_capex as number) || 0) }}</td>
              <td class="num">{{ formatVnd((it.tco_5y as number) || 0) }}</td>
              <td v-if="plan.workflow_state === 'Draft'" class="text-right">
                <button class="text-xs text-danger-500 hover:text-danger-700"
                        :disabled="removingNr === (it.needs_request as string)"
                        @click="doRemoveNr(it.needs_request as string)">
                  {{ removingNr === (it.needs_request as string) ? '...' : 'Xóa' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="muted text-center" style="padding:1.5rem">
          Chưa có đề xuất nào — nhấn "+ Thêm đề xuất" để gom đề xuất đã duyệt vào kế hoạch.
        </div>
      </div>
    </template>

    <!-- Confirmation modal (replaces native confirm() which froze the browser) -->
    <div v-if="pendingAction" class="modal-backdrop" @click.self="cancelPendingAction">
      <div class="modal modal-confirm">
        <h3>Xác nhận</h3>
        <p style="margin: 0.75rem 0 1rem">{{ pendingAction.msg }}</p>
        <div class="modal-actions">
          <button class="btn btn-outline" :disabled="actioning" @click="cancelPendingAction">Huỷ</button>
          <button class="btn btn-primary" :disabled="actioning" @click="confirmPendingAction">
            {{ actioning ? 'Đang xử lý...' : 'Xác nhận' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Roll-into-plan modal -->
    <div v-if="showRollModal" class="modal-backdrop" @click.self="showRollModal = false">
      <div class="modal">
        <h3>Đưa đề xuất vào kế hoạch {{ plan?.name }}</h3>
        <div v-if="!candidateNeeds.length" class="muted">Không có đề xuất "Đã duyệt" để gom.</div>
        <div v-else class="modal-body">
          <table class="data-table">
            <thead>
              <tr>
                <th></th>
                <th>Mã đề xuất</th>
                <th>Khoa</th>
                <th class="num">Điểm</th>
                <th class="num">Đầu tư mua sắm</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="n in candidateNeeds" :key="n.name">
                <td>
                  <input type="checkbox" :checked="selectedIds.has(n.name)"
                         @change="toggleSelect(n.name)" />
                </td>
                <td>{{ n.name }}</td>
                <td>{{ n.department_name || n.requesting_department }}</td>
                <td class="num">{{ (n.weighted_score || 0).toFixed(2) }}</td>
                <td class="num">{{ formatVnd(n.total_capex || 0) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showRollModal = false">Huỷ</button>
          <button class="btn btn-primary" :disabled="!selectedIds.size || rolling"
                  @click="confirmRoll">
            {{ rolling ? 'Đang gom...' : `Đưa ${selectedIds.size} đề xuất vào kế hoạch` }}
          </button>
        </div>
      </div>
    </div>
  </DetailPageShell>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
.header-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.meta { color: #6b7280; font-size: 0.85rem; }
.muted { color: #6b7280; }
.text-center { text-align: center; }
.grid-3col { display: grid; grid-template-columns: 1fr; gap: 1rem; margin-bottom: 1rem; }
@media (min-width: 640px) { .grid-3col { grid-template-columns: 1fr 1fr; } }
@media (min-width: 768px) { .grid-3col { grid-template-columns: 1fr 1fr 1fr; } }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; }
.card h3 { margin: 0 0 0.75rem; font-size: 1rem; color: #111827; }
.kpi { font-size: 1.5rem; font-weight: 700; color: #111827; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; font-size: 0.9rem; }
.data-table th { background: #f9fafb; font-weight: 600; }
.data-table .num { text-align: right; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.state-draft { background: #e5e7eb; color: #374151; }
.badge.state-approved, .badge.state-active { background: #d1fae5; color: #065f46; }
.badge.state-closed { background: #dbeafe; color: #1e40af; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.btn-danger { color: #dc2626; border-color: #dc2626; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.loading { padding: 3rem; text-align: center; color: #6b7280; }
.alert-error { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: white; border-radius: 12px; padding: 1.25rem; width: min(600px, 92vw); max-height: 85vh; display: flex; flex-direction: column; overflow-y: auto; }
.modal-body { overflow-y: auto; max-height: 60vh; margin: 0.75rem 0; }
.modal-actions { display: flex; gap: 0.5rem; justify-content: flex-end; }
</style>
