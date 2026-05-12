<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-03 — Vendor Profile List (FE-03-01)
import { ref, onMounted } from 'vue'
import { listVendorProfiles, type VendorProfileListItem } from '@/api/imm03'

const items = ref<VendorProfileListItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const filters = ref({
  avl_status: '',
  device_category: '',
  min_score: '' as number | '',
  audit_overdue: false,
})

async function load() {
  loading.value = true
  error.value = null
  try {
    const f: Record<string, unknown> = {}
    if (filters.value.avl_status)      f.avl_status = filters.value.avl_status
    if (filters.value.device_category) f.device_category = filters.value.device_category
    if (filters.value.min_score !== '') f.min_score = filters.value.min_score
    if (filters.value.audit_overdue)   f.audit_overdue = true
    const res = await listVendorProfiles(f, 1, 100)
    items.value = res.items
    total.value = res.total
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function statusClass(s?: string): string {
  switch (s) {
    case 'Approved':    return 'badge-success'
    case 'Conditional': return 'badge-warn'
    case 'Suspended':   return 'badge-danger'
    case 'Expired':     return 'badge-muted'
    default:            return 'badge-muted'
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>Hồ sơ Nhà cung cấp</h1>
        <div class="muted">Tổng {{ total }} nhà cung cấp · IMM-03</div>
      </div>
    </div>

    <div class="card filters">
      <select v-model="filters.avl_status" @change="load">
        <option value="">Tất cả AVL Status</option>
        <option>Approved</option>
        <option>Conditional</option>
        <option>Suspended</option>
        <option>Expired</option>
        <option>Not Applicable</option>
      </select>
      <input v-model="filters.device_category" placeholder="Nhóm thiết bị..." @change="load" />
      <input v-model.number="filters.min_score" type="number" min="0" max="5" step="0.1"
             placeholder="Điểm tối thiểu" @change="load" />
      <label class="checkbox">
        <input v-model="filters.audit_overdue" type="checkbox" @change="load" />
        Chỉ vendor quá hạn audit
      </label>
    </div>

    <div v-if="error" class="alert-error">{{ error }}</div>
    <div v-if="loading" class="muted">Đang tải...</div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Tên NCC</th>
            <th>AVL Status</th>
            <th>Nhóm thiết bị (AVL)</th>
            <th class="num">Điểm</th>
            <th>Audit gần nhất</th>
            <th>Audit kế tiếp</th>
            <th class="num">Chứng chỉ</th>
            <th class="num">Sắp hết hạn</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in items" :key="v.name">
            <td>
              <router-link :to="`/vendor-profiles/${v.name}`">
                {{ v.supplier_name || v.name }}
              </router-link>
              <code class="text-xs text-slate-400 ml-1">{{ v.name }}</code>
            </td>
            <td>
              <span :class="['badge', statusClass(v.imm_avl_status)]">
                {{ v.imm_avl_status || '—' }}
              </span>
            </td>
            <td>{{ v.imm_avl_categories || '—' }}</td>
            <td class="num">{{ (v.imm_overall_score || 0).toFixed(2) }}</td>
            <td>{{ v.imm_last_audit_date || '—' }}</td>
            <td>{{ v.imm_next_audit_date || '—' }}</td>
            <td class="num">{{ v.cert_count || 0 }}</td>
            <td class="num">
              <span :class="(v.cert_expiring_soon || 0) > 0 ? 'warn' : ''">
                {{ v.cert_expiring_soon || 0 }}
              </span>
            </td>
          </tr>
          <tr v-if="!items.length && !loading">
            <td colspan="8" class="muted text-center">Chưa có nhà cung cấp nào.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page-container { padding: 1.5rem; }
.page-header { display: flex; justify-content: space-between; margin-bottom: 1rem; }
.muted { color: #6b7280; }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.filters { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.filters select, .filters input[type=text], .filters input[type=number] {
  padding: 0.4rem 0.6rem; border: 1px solid #d1d5db; border-radius: 6px;
}
.checkbox { display: flex; align-items: center; gap: 0.25rem; font-size: 0.875rem; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th, .data-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; }
.data-table .num { text-align: right; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-success { background: #d1fae5; color: #065f46; }
.badge-warn    { background: #fef9c3; color: #a16207; }
.badge-danger  { background: #fee2e2; color: #b91c1c; }
.badge-muted   { background: #e5e7eb; color: #4b5563; }
.warn { color: #c2410c; font-weight: 600; }
.text-center { text-align: center; }
.alert-error { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.5rem 0.75rem; border-radius: 6px; color: #b91c1c; margin-bottom: 1rem; }
code { font-family: ui-monospace, monospace; background: #f3f4f6; padding: 0.05rem 0.25rem; border-radius: 3px; }
</style>
