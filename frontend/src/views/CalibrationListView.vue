<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm11Store } from '@/stores/imm11'
import { formatAssetDisplay, translateStatus, getStatusColor, formatDate } from '@/utils/formatters'

const router = useRouter()
const store = useImm11Store()

const items = computed(() => store.calibrations)
const pagination = computed(() => store.pagination)
const kpis = computed(() => store.kpis?.kpis ?? null)
const loading = computed(() => store.loading)
const filterStatus = ref('')

async function load(page = 1) {
  await store.fetchList({ page, page_size: 20, status: filterStatus.value || undefined })
}

async function loadKpis() {
  await store.fetchKpis()
}

function isOverdue(date: string | null) {
  return date && new Date(date) < new Date()
}

onMounted(() => { load(); loadKpis() })
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-start justify-between">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-11</p>
        <h1 class="text-2xl font-bold text-slate-900">Hiệu chuẩn thiết bị</h1>
      </div>
      <div class="flex gap-2">
        <button class="btn-ghost text-sm" @click="router.push('/calibration/schedules')">Lịch hiệu chuẩn</button>
        <button class="btn-primary text-sm" @click="router.push('/calibration/new')">+ Tạo phiếu</button>
      </div>
    </div>

    <!-- KPI Cards -->
    <div v-if="kpis" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Tháng này</p>
        <p class="text-2xl font-bold text-slate-700">{{ kpis.total_this_month }}</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Đã qua</p>
        <p class="text-2xl font-bold text-green-600">{{ kpis.completed }}</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Thất bại</p>
        <p class="text-2xl font-bold text-red-600">{{ kpis.failed }}</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Pass rate</p>
        <p class="text-2xl font-bold text-blue-600">{{ kpis.pass_rate_pct }}%</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Quá hạn</p>
        <p class="text-2xl font-bold text-red-500">{{ kpis.overdue_assets }}</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Sắp đến hạn</p>
        <p class="text-2xl font-bold text-yellow-600">{{ kpis.due_soon_assets }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex gap-3 items-center">
      <select v-model="filterStatus" @change="load(1)" class="form-select text-sm">
        <option value="">Tất cả trạng thái</option>
        <option value="Scheduled">Đã lên lịch</option>
        <option value="Sent to Lab">Đã gửi phòng hiệu chuẩn</option>
        <option value="In Progress">Đang thực hiện</option>
        <option value="Certificate Received">Đã nhận chứng nhận</option>
        <option value="Passed">Đạt</option>
        <option value="Failed">Không đạt</option>
        <option value="Conditionally Passed">Đạt có điều kiện</option>
        <option value="Cancelled">Đã hủy</option>
      </select>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-slate-400">Đang tải...</div>
      <div v-else-if="!items.length" class="p-8 text-center text-slate-400 text-sm">Chưa có phiếu hiệu chuẩn.</div>
      <div v-else class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Trạng thái</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Ngày dự kiến</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Kết quả</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Ngày cal tiếp</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-slate-500"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="c in items" :key="c.name" class="hover:bg-slate-50 cursor-pointer" @click="router.push(`/calibration/${c.name}`)">
            <td class="px-4 py-3 font-mono text-xs text-slate-400">{{ c.name }}</td>
            <td class="px-4 py-3">
              <div class="font-medium text-slate-900 truncate max-w-[240px]">
                {{ formatAssetDisplay(c.asset_name, c.asset).main }}
              </div>
              <div v-if="formatAssetDisplay(c.asset_name, c.asset).hasBoth"
                   class="text-xs text-slate-400 font-mono">
                {{ formatAssetDisplay(c.asset_name, c.asset).sub }}
              </div>
            </td>
            <td class="px-4 py-3 text-slate-600">{{ c.calibration_type }}</td>
            <td class="px-4 py-3">
              <span :class="['inline-block px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(c.status)]">
                {{ translateStatus(c.status) }}
              </span>
            </td>
            <td class="px-4 py-3 text-slate-600">{{ formatDate(c.scheduled_date) }}</td>
            <td class="px-4 py-3">
              <span v-if="c.overall_result"
                    :class="['inline-block px-2 py-0.5 rounded-full text-xs font-semibold', getStatusColor(c.overall_result)]">
                {{ translateStatus(c.overall_result) }}
              </span>
              <span v-else class="text-slate-300">—</span>
            </td>
            <td class="px-4 py-3 text-xs" :class="isOverdue(c.next_calibration_date) ? 'text-red-600 font-semibold' : 'text-slate-500'">
              {{ formatDate(c.next_calibration_date) }}
            </td>
            <td class="px-4 py-3 text-right">
              <button class="text-blue-600 text-xs font-medium" @click.stop="router.push(`/calibration/${c.name}`)">Chi tiết</button>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="pagination.total_pages > 1" class="flex justify-center gap-2">
      <button :disabled="pagination.page <= 1" class="btn-ghost text-sm" @click="load(pagination.page - 1)">← Trước</button>
      <span class="text-sm text-slate-500 self-center">{{ pagination.page }}/{{ pagination.total_pages }}</span>
      <button :disabled="pagination.page >= pagination.total_pages" class="btn-ghost text-sm" @click="load(pagination.page + 1)">Sau →</button>
    </div>
  </div>
</template>
