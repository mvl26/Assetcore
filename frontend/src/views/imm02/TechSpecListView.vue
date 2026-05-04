<template>
  <div class="tech-spec-list">
    <div class="page-header">
      <div>
        <h1>Hồ sơ kỹ thuật</h1>
        <p class="muted">Quản lý yêu cầu kỹ thuật, so sánh thị trường và đánh giá rủi ro phụ thuộc nhà cung cấp.</p>
      </div>
      <button class="btn btn-primary" @click="goCreate">+ Sinh từ kế hoạch</button>
    </div>

    <div v-if="store.kpis" class="kpi-grid">
      <div class="kpi-card">
        <span class="kpi-value">{{ totalLocked }}</span>
        <span class="kpi-label">Đã chốt hồ sơ</span>
      </div>
      <div class="kpi-card warn">
        <span class="kpi-value">{{ store.kpis.backlog_over_30d }}</span>
        <span class="kpi-label">Hồ sơ tồn quá 30 ngày</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-value">{{ store.kpis.avg_lock_in_score.toFixed(2) }}</span>
        <span class="kpi-label">Điểm phụ thuộc trung bình (mục tiêu ≤ 2,5)</span>
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
            <th>Mã hồ sơ</th>
            <th>Phiên bản</th>
            <th>Mẫu thiết bị</th>
            <th class="num">Yêu cầu bắt buộc</th>
            <th class="num">Số ứng viên</th>
            <th class="num">Điểm phụ thuộc</th>
            <th>Trạng thái</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.loading"><td colspan="7" class="muted text-center">Đang tải...</td></tr>
          <tr v-else-if="!store.specs.length"><td colspan="7" class="muted text-center">Chưa có hồ sơ kỹ thuật.</td></tr>
          <tr v-for="s in store.specs" :key="s.name" class="clickable" @click="goDetail(s.name)">
            <td>{{ s.name }}</td>
            <td>{{ s.version }}</td>
            <td>{{ s.device_model_ref }}</td>
            <td class="num">{{ s.total_mandatory ?? 0 }}</td>
            <td class="num">{{ s.candidate_count ?? 0 }}</td>
            <td class="num">
              <span :class="lockInClass(s.lock_in_score)">
                {{ s.lock_in_score != null ? s.lock_in_score.toFixed(2) : '—' }}
              </span>
            </td>
            <td>
              <span :class="['badge', 'state-' + stateSlug(s.workflow_state)]">
                {{ stateLabel(s.workflow_state) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm02Store } from '@/stores/imm02'
import { stateLabel, stateSlug } from '@/utils/wave2Labels'

const router = useRouter()
const store = useImm02Store()

const totalLocked = computed(() => store.kpis?.by_state?.['Locked'] ?? 0)

function goDetail(n: string) { router.push({ name: 'TechSpecDetail', params: { id: n } }) }
function goCreate() { router.push({ name: 'TechSpecCreate' }) }
function lockInClass(score?: number): string {
  if (score == null) return ''
  if (score > 3.5) return 'over'
  if (score > 2.5) return 'warn'
  return 'ok'
}

onMounted(() => { store.fetchList(); store.fetchKpis() })
</script>

<style scoped>
.tech-spec-list { padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
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
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.state-draft { background: #e5e7eb; color: #374151; }
.badge.state-reviewing { background: #fef3c7; color: #92400e; }
.badge.state-benchmarked, .badge.state-locked { background: #d1fae5; color: #065f46; }
.badge.state-risk-assessed, .badge.state-pending-approval { background: #fce7f3; color: #9d174d; }
.badge.state-withdrawn { background: #fee2e2; color: #b91c1c; }
.over { color: #b91c1c; font-weight: 700; }
.warn { color: #c2410c; font-weight: 600; }
.ok   { color: #065f46; font-weight: 500; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; }
</style>
