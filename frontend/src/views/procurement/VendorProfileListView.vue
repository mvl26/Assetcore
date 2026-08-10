<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-03 — Vendor Profile List (FE-03-01)
import { ref, computed, onMounted } from 'vue'
import { listVendorProfiles, type VendorProfileListItem } from '@/api/imm03'
import PageHeader from '@/components/common/PageHeader.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'
import { avlStatusLabel } from '@/constants/labels'

const items = ref<VendorProfileListItem[]>([])
const total = ref(0)
const loading = ref(false)
// AC-UX-041 — trước đây banner .alert-error hiện SONG SONG với câu «Chưa có nhà cung
// cấp nào.» (double-state) và không có nút thử lại. Nay lỗi là trạng thái loại trừ.
const errorMessage = ref<string | null>(null)

const DEFAULT_FILTERS = () => ({
  avl_status: '',
  device_category: '',
  min_score: '' as number | '',
  audit_overdue: false,
})
const filters = ref(DEFAULT_FILTERS())

async function load() {
  loading.value = true
  errorMessage.value = null          // INV-UX3-4 — xoá lỗi ĐẦU lượt nạp
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
    errorMessage.value = e instanceof Error ? e.message : String(e)
    items.value = []                 // INV-UX3-5 — không giữ số cũ dưới dải lỗi
    total.value = 0
  } finally {
    loading.value = false            // INV-UX3-3 — luôn hạ cờ
  }
}

const hasActiveFilter = computed(() =>
  Boolean(filters.value.avl_status) || Boolean(filters.value.device_category)
  || filters.value.min_score !== '' || filters.value.audit_overdue)

function resetFilters() {
  filters.value = DEFAULT_FILTERS()
  load()
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
  <ListPageShell
    :loading="loading"
    :error-message="errorMessage"
    :is-empty="!items.length"
    empty-title="Chưa có nhà cung cấp nào"
    empty-hint="Hãy xoá bộ lọc để xem tất cả nhà cung cấp."
    @retry="load"
  >
    <template #header>
      <PageHeader
        title="Hồ sơ Nhà cung cấp"
        :subtitle="`Tổng ${total} nhà cung cấp — đánh giá & duyệt nhà cung cấp, kiểm tra, chứng chỉ.`"
      />
    </template>

    <template #filters>
      <div class="card mb-4 flex flex-wrap items-center gap-2">
        <label class="sr-only" for="vendor-filter-avl">Trạng thái duyệt nhà cung cấp</label>
        <select id="vendor-filter-avl" v-model="filters.avl_status" class="form-select text-sm" @change="load">
          <option value="">Tất cả trạng thái duyệt</option>
          <option value="Approved">Đã duyệt</option>
          <option value="Conditional">Có điều kiện</option>
          <option value="Suspended">Tạm đình chỉ</option>
          <option value="Expired">Hết hạn</option>
          <option value="Not Applicable">Không áp dụng</option>
        </select>
        <label class="sr-only" for="vendor-filter-category">Nhóm thiết bị</label>
        <input id="vendor-filter-category" v-model="filters.device_category" class="form-input text-sm max-w-[220px]" placeholder="Nhóm thiết bị..." @change="load" />
        <label class="sr-only" for="vendor-filter-score">Điểm tối thiểu</label>
        <input
id="vendor-filter-score" v-model.number="filters.min_score" type="number" min="0" max="5" step="0.1"
               class="form-input text-sm max-w-[160px]" placeholder="Điểm tối thiểu" @change="load" />
        <label class="flex items-center gap-1.5 text-sm text-slate-600">
          <input v-model="filters.audit_overdue" type="checkbox" @change="load" />
          Chỉ nhà cung cấp quá hạn kiểm tra
        </label>
      </div>
    </template>

    <template #skeleton>
      <SkeletonLoader variant="table" :rows="6" />
    </template>

    <template #empty-action>
      <button v-if="hasActiveFilter" class="btn-ghost text-sm" @click="resetFilters">
        Xóa bộ lọc để xem tất cả
      </button>
    </template>

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
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>Tên Nhà cung cấp</th>
                <th>Trạng thái duyệt nhà cung cấp</th>
                <th>Nhóm thiết bị</th>
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
    <!-- Không có phân trang: endpoint kéo 1 lượt (page_size=100) — vòng 4 mới chuẩn hoá. -->
  </ListPageShell>
</template>

<style scoped>
/* styles trong list-view.css */
</style>
