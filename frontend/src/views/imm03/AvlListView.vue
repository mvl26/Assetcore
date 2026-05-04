<template>
  <div class="avl-list">
    <div class="page-header">
      <div>
        <h1>Danh mục nhà cung cấp được duyệt</h1>
        <p class="muted">Cấp phép nhà cung cấp theo từng nhóm thiết bị, có hạn hiệu lực.</p>
      </div>
      <button class="btn btn-primary" @click="showCreate = true">+ Cấp mới</button>
    </div>

    <div v-if="store.kpis" class="kpi-grid">
      <div class="kpi-card success">
        <span class="kpi-value">{{ store.kpis.avl_active }}</span>
        <span class="kpi-label">Đang hiệu lực</span>
      </div>
      <div class="kpi-card warn">
        <span class="kpi-value">{{ store.kpis.avl_expiring_30d }}</span>
        <span class="kpi-label">Sắp hết hạn (≤ 30 ngày)</span>
      </div>
    </div>

    <div v-if="store.error" class="alert alert-danger">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="filter-bar">
      <select v-model="stateFilter" @change="apply">
        <option value="">Tất cả</option>
        <option v-for="s in STATES" :key="s" :value="s">{{ s }}</option>
      </select>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Mã giấy phép</th>
            <th>Nhà cung cấp</th>
            <th>Nhóm thiết bị</th>
            <th>Thời hạn hiệu lực</th>
            <th>Trạng thái</th>
            <th>Hành động</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!store.avlEntries.length">
            <td colspan="6" class="muted text-center">Chưa có nhà cung cấp nào được duyệt.</td>
          </tr>
          <tr v-for="a in store.avlEntries" :key="a.name">
            <td>{{ a.name }}</td>
            <td>{{ a.supplier }}</td>
            <td>{{ a.device_category }}</td>
            <td>
              {{ formatVnDate(a.valid_from) }} → {{ formatVnDate(a.valid_to) }}
              <span v-if="isExpiring(a)" class="warn-text">⏰ Còn {{ daysLeft(a) }} ngày</span>
            </td>
            <td>
              <span :class="['badge', 'state-' + stateSlug(a.workflow_state)]">
                {{ stateLabel(a.workflow_state) }}
              </span>
            </td>
            <td class="actions-col">
              <button v-if="a.workflow_state === 'Draft'" class="btn btn-sm btn-success"
                      @click="approveAvl(a)">Phê duyệt</button>
              <button v-if="a.workflow_state === 'Approved' || a.workflow_state === 'Conditional'"
                      class="btn btn-sm btn-danger" @click="suspendAvl(a)">Đình chỉ</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Hộp thoại cấp mới -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-head">
          <h3>Cấp giấy phép cho nhà cung cấp</h3>
          <button class="btn-close" @click="showCreate = false">×</button>
        </div>
        <div class="modal-body">
          <label>Nhà cung cấp <span class="req">*</span>
            <input v-model="newAvl.supplier" type="text" placeholder="Chọn nhà cung cấp..." />
          </label>
          <label>Nhóm thiết bị <span class="req">*</span>
            <input v-model="newAvl.device_category" type="text"
                   placeholder="Ví dụ: Chẩn đoán hình ảnh, Cấp cứu hồi sức..." />
          </label>
          <label>Thời hạn hiệu lực (năm) <span class="req">*</span>
            <input v-model.number="newAvl.validity_years" type="number" min="1" max="3" />
          </label>
          <label>Hiệu lực từ ngày
            <input v-model="newAvl.valid_from" type="date" />
          </label>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" @click="showCreate = false">Huỷ</button>
          <button class="btn btn-primary" @click="doCreate" :disabled="!canCreate">Tạo giấy phép</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useImm03Store } from '@/stores/imm03'
import type { AvlListItem, AvlState } from '@/types/imm03'
import { stateLabel, stateSlug, formatVnDate } from '@/utils/wave2Labels'

const store = useImm03Store()

const STATES: AvlState[] = ['Draft', 'Approved', 'Conditional', 'Suspended', 'Expired']
const stateFilter = ref<string>('Approved')

const showCreate = ref(false)
const newAvl = reactive({
  supplier: '',
  device_category: '',
  validity_years: 2,
  valid_from: new Date().toISOString().slice(0, 10),
})

const canCreate = computed(() => newAvl.supplier && newAvl.device_category && newAvl.validity_years >= 1)

function apply() {
  const f: Record<string, unknown> = {}
  if (stateFilter.value) f.workflow_state = stateFilter.value
  store.fetchAvl(f)
}

function daysLeft(a: AvlListItem): number {
  if (!a.valid_to) return 0
  const t = new Date(a.valid_to).getTime()
  return Math.ceil((t - Date.now()) / (1000 * 86400))
}
function isExpiring(a: AvlListItem): boolean {
  const d = daysLeft(a)
  return d > 0 && d <= 30
}

async function approveAvl(a: AvlListItem) {
  const approver = globalThis.prompt('Tài khoản người phê duyệt:', 'admin@example.com')
  if (!approver) return
  await store.api.approveAvl(a.name, approver)
  await store.fetchAvl({ workflow_state: stateFilter.value || ['Approved', 'Conditional'] })
}

async function suspendAvl(a: AvlListItem) {
  const reason = globalThis.prompt('Lý do đình chỉ giấy phép:')
  if (!reason) return
  await store.api.suspendAvl(a.name, reason)
  await store.fetchAvl({ workflow_state: stateFilter.value || ['Approved', 'Conditional'] })
}

async function doCreate() {
  if (!canCreate.value) return
  await store.api.createAvlEntry(
    newAvl.supplier, newAvl.device_category,
    newAvl.validity_years, newAvl.valid_from,
  )
  showCreate.value = false
  newAvl.supplier = ''; newAvl.device_category = ''
  await store.fetchAvl()
}

onMounted(() => {
  store.fetchAvl({ workflow_state: ['Approved', 'Conditional', 'Draft'] })
  store.fetchKpis()
})
</script>

<style scoped>
.avl-list { padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.muted { color: #6b7280; font-size: 0.85rem; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; }
.kpi-value { font-size: 1.75rem; font-weight: 700; }
.kpi-label { color: #6b7280; font-size: 0.85rem; }
.kpi-card.success { border-left: 4px solid #10b981; }
.kpi-card.warn { border-left: 4px solid #f59e0b; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-close { background: none; border: none; cursor: pointer; }
.filter-bar { margin-bottom: 1rem; }
.filter-bar select { padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; }
.table-container { background: white; border-radius: 8px; overflow: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; }
.text-center { text-align: center; }
.actions-col { display: flex; gap: 0.5rem; }
.warn-text { color: #c2410c; font-weight: 600; margin-left: 0.5rem; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge.state-draft { background: #e5e7eb; color: #374151; }
.badge.state-approved { background: #d1fae5; color: #065f46; }
.badge.state-conditional { background: #fef3c7; color: #92400e; }
.badge.state-suspended { background: #fee2e2; color: #b91c1c; }
.badge.state-expired { background: #e5e7eb; color: #6b7280; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-success { background: #10b981; color: white; border-color: #10b981; }
.btn-danger { background: #ef4444; color: white; border-color: #ef4444; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
.btn-sm { padding: 0.3rem 0.6rem; font-size: 0.8rem; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; border-radius: 8px; width: 480px; max-width: 90vw; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid #e5e7eb; }
.modal-head h3 { margin: 0; }
.btn-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; }
.modal-body { padding: 1rem; }
.modal-body label { display: block; margin-bottom: 1rem; font-weight: 500; }
.modal-body input { display: block; width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; margin-top: 0.25rem; }
.modal-foot { padding: 1rem; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 0.5rem; }
.req { color: #ef4444; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 4px; }
</style>
