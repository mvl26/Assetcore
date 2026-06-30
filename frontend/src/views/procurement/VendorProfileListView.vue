<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-03 — Vendor Profile List (FE-03-01)
import { ref, onMounted } from 'vue'
import { listVendorProfiles, type VendorProfileListItem } from '@/api/imm03'
import PageHeader from '@/components/common/PageHeader.vue'
import { avlStatusLabel } from '@/constants/labels'

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

function statusTone(s?: string): 'success' | 'warning' | 'danger' | 'neutral' {
  switch (s) {
    case 'Approved':    return 'success'
    case 'Conditional': return 'warning'
    case 'Suspended':   return 'danger'
    default:            return 'neutral'
  }
}

function statusBgClass(s?: string): string {
  const t = statusTone(s)
  return {
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    warning: 'bg-amber-50 text-amber-700 border-amber-200',
    danger:  'bg-red-50 text-red-700 border-red-200',
    neutral: 'bg-slate-50 text-slate-600 border-slate-200',
  }[t]
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Hồ sơ Nhà cung cấp"
      :subtitle="`Tổng ${total} nhà cung cấp — đánh giá AVL, kiểm tra, chứng chỉ.`"
    />

    <div class="card mb-4 flex flex-wrap items-center gap-2">
      <select v-model="filters.avl_status" class="form-select text-sm" @change="load">
        <option value="">Tất cả trạng thái AVL</option>
        <option value="Approved">Đã duyệt</option>
        <option value="Conditional">Có điều kiện</option>
        <option value="Suspended">Tạm đình chỉ</option>
        <option value="Expired">Hết hạn</option>
        <option value="Not Applicable">Không áp dụng</option>
      </select>
      <input v-model="filters.device_category" class="form-input text-sm max-w-[220px]" placeholder="Nhóm thiết bị..." @change="load" />
      <input
v-model.number="filters.min_score" type="number" min="0" max="5" step="0.1"
             class="form-input text-sm max-w-[160px]" placeholder="Điểm tối thiểu" @change="load" />
      <label class="flex items-center gap-1.5 text-sm text-slate-600">
        <input v-model="filters.audit_overdue" type="checkbox" @change="load" />
        Chỉ nhà cung cấp quá hạn kiểm tra
      </label>
    </div>

    <div v-if="error" class="alert-error mb-4">
      <span><strong>Lỗi:</strong> {{ error }}</span>
    </div>

    <div class="card overflow-hidden">
      <div v-if="loading" class="p-6 text-sm text-slate-500">Đang tải...</div>
      <template v-else-if="items.length">
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="v in items"
            :key="v.name"
            class="mobile-card"
            @click="$router.push(`/vendor-profiles/${v.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ v.name }}</span>
              <span :class="['px-2.5 py-0.5 rounded-full text-xs font-medium border', statusBgClass(v.imm_avl_status)]">
                {{ avlStatusLabel(v.imm_avl_status) }}
              </span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ v.supplier_name || v.name }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="v.imm_avl_categories">{{ v.imm_avl_categories }}</span>
              <span>· Điểm: {{ (v.imm_overall_score || 0).toFixed(2) }}</span>
              <span v-if="(v.cert_expiring_soon || 0) > 0">· Sắp hết hạn: {{ v.cert_expiring_soon }}</span>
            </div>
          </div>
          <div v-if="items.length === 0" class="py-12 text-center text-slate-400">
            <p class="text-sm">Không có dữ liệu</p>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>Tên Nhà cung cấp</th>
                <th>Trạng thái AVL</th>
                <th>Nhóm thiết bị (AVL)</th>
                <th class="num">Điểm</th>
                <th>Kiểm tra gần nhất</th>
                <th>Kiểm tra kế tiếp</th>
                <th class="num">Chứng chỉ</th>
                <th class="num">Sắp hết hạn</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(v, idx) in items" :key="v.name"
                class="animate-fade-in" :class="[`stagger-${Math.min(idx + 1, 8)}`]"
              >
                <td>
                  <router-link :to="`/vendor-profiles/${v.name}`" class="link-cell font-medium">
                    {{ v.supplier_name || v.name }}
                  </router-link>
                  <div class="mt-0.5"><span class="font-mono text-[11px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">{{ v.name }}</span></div>
                </td>
                <td>
                  <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border', statusBgClass(v.imm_avl_status)]">
                    {{ avlStatusLabel(v.imm_avl_status) }}
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
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Chưa có nhà cung cấp nào.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* styles trong list-view.css */
</style>
