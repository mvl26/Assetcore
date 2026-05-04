<template>
  <div class="decision-list">
    <div class="page-header">
      <div>
        <h1>Quyết định mua sắm</h1>
        <p class="muted">Tổng hợp các quyết định trao thầu, ký hợp đồng và phát hành đơn hàng.</p>
      </div>
    </div>

    <div v-if="store.kpis" class="kpi-grid">
      <div class="kpi-card">
        <span class="kpi-value">{{ store.kpis.decision_states['Awarded'] || 0 }}</span>
        <span class="kpi-label">Đã trao thầu</span>
      </div>
      <div class="kpi-card warn">
        <span class="kpi-value">{{ store.kpis.decision_states['Pending Approval'] || 0 }}</span>
        <span class="kpi-label">Chờ phê duyệt</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-value">{{ store.kpis.decision_states['PO Issued'] || 0 }}</span>
        <span class="kpi-label">Đã phát hành đơn hàng</span>
      </div>
    </div>

    <div v-if="store.error" class="alert alert-danger">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Mã quyết định</th>
            <th>Hồ sơ kỹ thuật</th>
            <th>Nhà cung cấp trúng thầu</th>
            <th class="num">Giá trúng thầu</th>
            <th class="num">So với ngân sách</th>
            <th>Đơn hàng đã mint</th>
            <th>Trạng thái</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.loading"><td colspan="7" class="muted text-center">Đang tải...</td></tr>
          <tr v-else-if="!store.decisions.length">
            <td colspan="7" class="muted text-center">Chưa có quyết định mua sắm nào.</td>
          </tr>
          <tr v-for="d in store.decisions" :key="d.name" class="clickable" @click="goDetail(d.name)">
            <td>{{ d.name }}</td>
            <td>{{ d.spec_ref }}</td>
            <td>{{ d.winner_supplier || '—' }}</td>
            <td class="num">{{ formatVnd(d.awarded_price) }}</td>
            <td class="num">
              <span :class="envClass(d.envelope_check_pct)">
                {{ d.envelope_check_pct ? d.envelope_check_pct.toFixed(1) + '%' : '—' }}
              </span>
            </td>
            <td>
              <span v-if="d.ac_purchase_ref">{{ d.ac_purchase_ref }}</span>
              <span v-else class="muted">—</span>
            </td>
            <td>
              <span :class="['badge', 'state-' + stateSlug(d.workflow_state)]">
                {{ stateLabel(d.workflow_state) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import { stateLabel, stateSlug, formatVnd } from '@/utils/wave2Labels'

const router = useRouter()
const store = useImm03Store()

function goDetail(n: string) { router.push({ name: 'ProcurementDecisionDetail', params: { id: n } }) }

function envClass(pct?: number): string {
  if (pct == null) return ''
  if (pct > 105) return 'over'
  if (pct > 90)  return 'warn'
  return 'ok'
}

onMounted(() => { store.fetchDecisions(); store.fetchKpis() })
</script>

<style scoped>
.decision-list { padding: 1.5rem; }
.page-header { margin-bottom: 1rem; }
.muted { color: #6b7280; font-size: 0.85rem; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; }
.kpi-value { font-size: 1.75rem; font-weight: 700; }
.kpi-label { color: #6b7280; font-size: 0.85rem; }
.kpi-card.warn { border-left: 4px solid #f59e0b; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-close { background: none; border: none; cursor: pointer; }
.table-container { background: white; border-radius: 8px; overflow: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; }
.data-table .num { text-align: right; }
.text-center { text-align: center; }
.data-table tr.clickable { cursor: pointer; }
.data-table tr.clickable:hover { background: #f9fafb; }
.over { color: #b91c1c; font-weight: 700; }
.warn { color: #c2410c; font-weight: 600; }
.ok { color: #065f46; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.state-draft, .badge.state-method-selected { background: #e5e7eb; color: #374151; }
.badge.state-negotiation, .badge.state-pending-approval, .badge.state-award-recommended { background: #fef3c7; color: #92400e; }
.badge.state-awarded, .badge.state-contract-signed, .badge.state-po-issued { background: #d1fae5; color: #065f46; }
.badge.state-cancelled { background: #fee2e2; color: #b91c1c; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; font-size: 0.85rem; }
</style>
