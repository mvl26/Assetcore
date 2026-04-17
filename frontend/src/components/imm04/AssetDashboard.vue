<script setup lang="ts">
/**
 * AssetDashboard.vue — Kiểm chứng kết nối API Data Layer
 *
 * Component này dùng song song 2 nguồn dữ liệu:
 *   1. FrappeResource (Base CRUD — /api/resource/)
 *   2. useCommissioningStore (Custom API — /api/method/assetcore...)
 *
 * Mục đích: verify end-to-end connection, không phải production UI.
 */
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCommissioningStore } from '@/stores/commissioning'
import { commissioningListResource } from '@/services/frappeResource'
import type { CommissioningListItem } from '@/types/imm04'
import { formatDate } from '@/utils/docUtils'

// ─── Stores ──────────────────────────────────────────────────────────────────

const auth = useAuthStore()
const store = useCommissioningStore()

// ─── State ───────────────────────────────────────────────────────────────────

const resourceRows = ref<CommissioningListItem[]>([])
const resourceLoading = ref(false)
const resourceError = ref<string | null>(null)

const activeTab = ref<'resource' | 'store'>('resource')

// ─── Computed ─────────────────────────────────────────────────────────────────

const connectionOk = computed(() => {
  if (activeTab.value === 'resource') return resourceRows.value.length >= 0 && !resourceError.value
  return store.list.length >= 0 && !store.error
})

// ─── Fetch via FrappeResource (base CRUD) ────────────────────────────────────

async function loadViaResource() {
  resourceLoading.value = true
  resourceError.value = null
  try {
    resourceRows.value = await commissioningListResource.list({
      fields: ['name', 'asset_name', 'workflow_state', 'clinical_dept', 'commissioning_date', 'modified'],
      order_by: 'modified desc',
      limit_page_length: 20,
    })
  } catch (e) {
    resourceError.value = e instanceof Error ? e.message : 'Lỗi không xác định'
  } finally {
    resourceLoading.value = false
  }
}

// ─── Fetch via Commissioning Store (custom API) ───────────────────────────────

async function loadViaStore() {
  await store.fetchList({}, 1, 20)
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([loadViaResource(), loadViaStore()])
})

// ─── Helpers ─────────────────────────────────────────────────────────────────

function stateClass(state: string): string {
  const map: Record<string, string> = {
    Draft: 'bg-gray-100 text-gray-700',
    Reception: 'bg-blue-100 text-blue-700',
    Site_Preparation: 'bg-yellow-100 text-yellow-700',
    Identification: 'bg-purple-100 text-purple-700',
    Baseline_Safety: 'bg-orange-100 text-orange-700',
    Pending_Release: 'bg-indigo-100 text-indigo-700',
    Clinical_Release: 'bg-green-100 text-green-700',
    Commissioned: 'bg-emerald-100 text-emerald-700',
    Return_To_Vendor: 'bg-red-100 text-red-700',
    Radiation_Hold: 'bg-pink-100 text-pink-700',
  }
  return map[state] ?? 'bg-gray-100 text-gray-600'
}

</script>

<template>
  <div class="p-6 space-y-6">

    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <div class="flex items-start justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">AssetDashboard — Kiểm chứng Data Layer</h2>
        <p class="text-sm text-gray-500 mt-0.5">
          Xác minh kết nối Vue → Frappe qua hai phương thức: FrappeResource + CommissioningStore
        </p>
      </div>

      <!-- Connection badge -->
      <span
        class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
        :class="connectionOk ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
      >
        <span class="w-1.5 h-1.5 rounded-full" :class="connectionOk ? 'bg-green-500' : 'bg-red-500'" />
        {{ connectionOk ? 'Kết nối OK' : 'Lỗi kết nối' }}
      </span>
    </div>

    <!-- ── Session info ────────────────────────────────────────────────────── -->
    <div class="bg-white border border-gray-200 rounded-xl p-4 grid grid-cols-2 gap-4 text-sm">
      <div>
        <span class="text-gray-500">User:</span>
        <span class="ml-2 font-medium text-gray-900">{{ auth.user?.full_name ?? '—' }}</span>
      </div>
      <div>
        <span class="text-gray-500">Email:</span>
        <span class="ml-2 font-medium text-gray-900">{{ auth.user?.email ?? '—' }}</span>
      </div>
      <div>
        <span class="text-gray-500">Roles:</span>
        <span class="ml-2 font-medium text-gray-900">{{ auth.roles.join(', ') || '—' }}</span>
      </div>
      <div>
        <span class="text-gray-500">Authenticated:</span>
        <span
          class="ml-2 font-semibold"
          :class="auth.isAuthenticated ? 'text-green-600' : 'text-red-600'"
        >
          {{ auth.isAuthenticated ? 'Yes' : 'No' }}
        </span>
      </div>
    </div>

    <!-- ── Tabs ───────────────────────────────────────────────────────────── -->
    <div class="border-b border-gray-200">
      <nav class="flex gap-6 text-sm font-medium">
        <button
          class="pb-2 border-b-2 transition-colors"
          :class="activeTab === 'resource'
            ? 'border-blue-500 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700'"
          @click="activeTab = 'resource'"
        >
          FrappeResource <span class="text-xs text-gray-400 font-normal">/api/resource/</span>
        </button>
        <button
          class="pb-2 border-b-2 transition-colors"
          :class="activeTab === 'store'
            ? 'border-blue-500 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700'"
          @click="activeTab = 'store'"
        >
          CommissioningStore <span class="text-xs text-gray-400 font-normal">/api/method/</span>
        </button>
      </nav>
    </div>

    <!-- ── Tab: FrappeResource ────────────────────────────────────────────── -->
    <div v-if="activeTab === 'resource'">
      <div class="flex items-center justify-between mb-3">
        <p class="text-sm text-gray-600">
          <code class="bg-gray-100 px-1.5 py-0.5 rounded text-xs">FrappeResource&lt;CommissioningListItem&gt;.list()</code>
          — {{ resourceRows.length }} bản ghi
        </p>
        <button
          class="text-xs text-blue-600 hover:underline"
          :disabled="resourceLoading"
          @click="loadViaResource"
        >
          {{ resourceLoading ? 'Đang tải...' : 'Tải lại' }}
        </button>
      </div>

      <!-- Error -->
      <div v-if="resourceError" class="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-3">
        {{ resourceError }}
      </div>

      <!-- Loading -->
      <div v-else-if="resourceLoading" class="flex justify-center py-10">
        <svg class="w-6 h-6 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>

      <!-- Empty -->
      <div v-else-if="resourceRows.length === 0" class="text-center py-10 text-sm text-gray-400">
        Không có phiếu nào. (Kết nối thành công — danh sách trống)
      </div>

      <!-- Table -->
      <div v-else class="overflow-x-auto rounded-xl border border-gray-200">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-600 text-xs uppercase">
            <tr>
              <th class="text-left px-4 py-3">Mã phiếu</th>
              <th class="text-left px-4 py-3">Thiết bị</th>
              <th class="text-left px-4 py-3">Khoa</th>
              <th class="text-left px-4 py-3">Trạng thái</th>
              <th class="text-left px-4 py-3">Ngày</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="row in resourceRows" :key="row.name" class="hover:bg-gray-50">
              <td class="px-4 py-3 font-mono text-xs text-blue-600">{{ row.name }}</td>
              <td class="px-4 py-3">{{ row.asset_name ?? '—' }}</td>
              <td class="px-4 py-3 text-gray-600">{{ row.clinical_dept ?? '—' }}</td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="stateClass(row.workflow_state ?? '')">
                  {{ (row.workflow_state ?? 'Draft').replace(/_/g, ' ') }}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-500">{{ formatDate(row.modified) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Tab: CommissioningStore ────────────────────────────────────────── -->
    <div v-if="activeTab === 'store'">
      <div class="flex items-center justify-between mb-3">
        <p class="text-sm text-gray-600">
          <code class="bg-gray-100 px-1.5 py-0.5 rounded text-xs">useCommissioningStore().fetchList()</code>
          — {{ store.list.length }} / {{ store.pagination.total }} bản ghi
        </p>
        <button
          class="text-xs text-blue-600 hover:underline"
          :disabled="store.listLoading"
          @click="loadViaStore"
        >
          {{ store.listLoading ? 'Đang tải...' : 'Tải lại' }}
        </button>
      </div>

      <!-- Error -->
      <div v-if="store.error" class="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-3">
        {{ store.error }}
      </div>

      <!-- Loading -->
      <div v-else-if="store.listLoading" class="flex justify-center py-10">
        <svg class="w-6 h-6 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>

      <!-- Empty -->
      <div v-else-if="store.list.length === 0" class="text-center py-10 text-sm text-gray-400">
        Không có phiếu nào. (Kết nối thành công — danh sách trống)
      </div>

      <!-- Table -->
      <div v-else class="overflow-x-auto rounded-xl border border-gray-200">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-600 text-xs uppercase">
            <tr>
              <th class="text-left px-4 py-3">Mã phiếu</th>
              <th class="text-left px-4 py-3">Thiết bị</th>
              <th class="text-left px-4 py-3">Khoa</th>
              <th class="text-left px-4 py-3">Trạng thái</th>
              <th class="text-left px-4 py-3">Ngày</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="row in store.list" :key="row.name" class="hover:bg-gray-50">
              <td class="px-4 py-3 font-mono text-xs text-blue-600">{{ row.name }}</td>
              <td class="px-4 py-3">{{ row.asset_name ?? '—' }}</td>
              <td class="px-4 py-3 text-gray-600">{{ row.clinical_dept ?? '—' }}</td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="stateClass(row.workflow_state ?? '')">
                  {{ (row.workflow_state ?? 'Draft').replace(/_/g, ' ') }}
                </span>
              </td>
              <td class="px-4 py-3 text-gray-500">{{ formatDate(row.commissioning_date) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination info -->
      <div v-if="store.pagination.total > 0" class="mt-3 text-xs text-gray-400 text-right">
        Trang {{ store.pagination.page }} / {{ store.pagination.total_pages }}
        ({{ store.pagination.total }} tổng)
      </div>
    </div>

  </div>
</template>
