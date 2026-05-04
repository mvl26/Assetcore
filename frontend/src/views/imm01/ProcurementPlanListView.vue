<template>
  <div class="plan-list">
    <div class="page-header">
      <div>
        <h1>Kế hoạch mua sắm</h1>
        <p class="muted">Tổng hợp các đề xuất nhu cầu đã duyệt theo quý / năm với ngân sách phân bổ.</p>
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
            <th>Mã kế hoạch</th>
            <th>Kỳ kế hoạch</th>
            <th class="num">Năm</th>
            <th class="num">Tổng ngân sách</th>
            <th class="num">Đã phân bổ</th>
            <th class="num">Tỷ lệ sử dụng</th>
            <th>Trạng thái</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!store.plans.length">
            <td colspan="7" class="muted text-center">Chưa có kế hoạch nào.</td>
          </tr>
          <tr v-for="p in store.plans" :key="p.name">
            <td>{{ p.name }}</td>
            <td>{{ planPeriodLabel(p.plan_period) }}</td>
            <td class="num">{{ p.plan_year }}</td>
            <td class="num">{{ formatVnd(p.budget_envelope) }}</td>
            <td class="num">{{ formatVnd(p.allocated_capex || 0) }}</td>
            <td class="num">
              <span :class="utilClass(p.utilization_pct)">{{ (p.utilization_pct || 0).toFixed(1) }}%</span>
            </td>
            <td>
              <span :class="['badge', 'state-' + stateSlug(p.workflow_state)]">
                {{ stateLabel(p.workflow_state) }}
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
import { useImm01Store } from '@/stores/imm01'
import { stateLabel, stateSlug, formatVnd } from '@/utils/wave2Labels'

const store = useImm01Store()

function utilClass(pct?: number): string {
  if ((pct || 0) >= 100) return 'over';
  if ((pct || 0) >= 80)  return 'warn';
  return ''
}

function planPeriodLabel(p?: string): string {
  return ({
    'Q1': 'Quý 1', 'Q2': 'Quý 2', 'Q3': 'Quý 3', 'Q4': 'Quý 4',
    'Annual': 'Cả năm',
  } as Record<string, string>)[p || ''] || (p || '')
}

onMounted(() => store.fetchPlans())
</script>

<style scoped>
.plan-list { padding: 1.5rem; }
.page-header { margin-bottom: 1rem; }
.muted { color: #6b7280; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-close { background: none; border: none; cursor: pointer; }
.table-container { background: white; border-radius: 8px; overflow: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; }
.data-table .num { text-align: right; }
.text-center { text-align: center; }
.over { color: #b91c1c; font-weight: 600; }
.warn { color: #c2410c; font-weight: 600; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.state-draft { background: #e5e7eb; color: #374151; }
.badge.state-approved, .badge.state-active { background: #d1fae5; color: #065f46; }
.badge.state-closed { background: #dbeafe; color: #1e40af; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; }
</style>
