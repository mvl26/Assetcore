<template>
  <div class="vendor-eval-list">
    <div class="page-header">
      <div>
        <h1>Đánh giá nhà cung cấp</h1>
        <p class="muted">Chấm điểm các ứng viên cung cấp thiết bị theo từng hồ sơ kỹ thuật.</p>
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
            <th>Mã phiếu đánh giá</th>
            <th>Hồ sơ kỹ thuật</th>
            <th>Ngày khởi tạo</th>
            <th>Nhà cung cấp đề xuất</th>
            <th>Trạng thái</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!store.evaluations.length">
            <td colspan="5" class="muted text-center">Chưa có phiếu đánh giá nào.</td>
          </tr>
          <tr v-for="ev in store.evaluations" :key="ev.name" class="clickable" @click="goDetail(ev.name)">
            <td>{{ ev.name }}</td>
            <td>{{ ev.spec_ref }}</td>
            <td>{{ formatVnDate(ev.draft_date) }}</td>
            <td>{{ ev.recommended_candidate || '—' }}</td>
            <td>
              <span :class="['badge', 'state-' + stateSlug(ev.workflow_state)]">
                {{ stateLabel(ev.workflow_state) }}
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
import { stateLabel, stateSlug, formatVnDate } from '@/utils/wave2Labels'

const router = useRouter()
const store = useImm03Store()

function goDetail(n: string) { router.push({ name: 'VendorEvaluationDetail', params: { id: n } }) }

onMounted(() => store.fetchEvaluations())
</script>

<style scoped>
.vendor-eval-list { padding: 1.5rem; }
.page-header { margin-bottom: 1rem; }
.muted { color: #6b7280; font-size: 0.85rem; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-close { background: none; border: none; cursor: pointer; }
.table-container { background: white; border-radius: 8px; overflow: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; }
.text-center { text-align: center; }
.data-table tr.clickable { cursor: pointer; }
.data-table tr.clickable:hover { background: #f9fafb; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.state-draft, .badge.state-open-rfq { background: #e5e7eb; color: #374151; }
.badge.state-quotation-received { background: #fef3c7; color: #92400e; }
.badge.state-evaluated { background: #d1fae5; color: #065f46; }
.badge.state-cancelled { background: #fee2e2; color: #b91c1c; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; font-size: 0.85rem; }
</style>
