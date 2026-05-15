<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { listUsers, getAvailableImmRoles, type IMMUserListItem, type ImmRoleOption } from '@/api/user'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

const router = useRouter()
const auth = useAuthStore()

const users = ref<IMMUserListItem[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const PAGE_SIZE = 20

// Filter state
const showFilters = ref(false)
const filters = ref({ search: '', approval_status: '', department: '', role: '' })
const availableRoles = ref<ImmRoleOption[]>([])

interface FilterChip { key: 'search' | 'approval_status' | 'department' | 'role'; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.approval_status) {
    chips.push({ key: 'approval_status', label: APPROVAL_LABELS[filters.value.approval_status] || filters.value.approval_status })
  }
  if (filters.value.department) chips.push({ key: 'department', label: filters.value.department })
  if (filters.value.role) {
    chips.push({ key: 'role', label: availableRoles.value.find(r => r.name === filters.value.role)?.label || filters.value.role })
  }
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)
function clearChip(key: string) { (filters.value as Record<string, string>)[key] = ''; load() }
function resetFilters() { filters.value = { search: '', approval_status: '', department: '', role: '' }; load() }
function quickFilter(key: 'approval_status', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  showFilters.value = false
  load()
}

const APPROVAL_COLORS: Record<string, string> = {
  Approved: 'bg-green-100 text-green-700',
  Pending: 'bg-amber-100 text-amber-700',
  Rejected: 'bg-red-100 text-red-700',
}
const APPROVAL_LABELS: Record<string, string> = {
  Approved: 'Đã duyệt', Pending: 'Chờ duyệt', Rejected: 'Từ chối',
}
const ROLE_GROUP_COLORS: Record<string, string> = {
  Governance:  'bg-purple-100 text-purple-700',
  Department:  'bg-blue-100 text-blue-700',
  Engineering: 'bg-emerald-100 text-emerald-700',
  Support:     'bg-amber-100 text-amber-700',
}

async function load() {
  loading.value = true
  const res = await listUsers({
    search: filters.value.search,
    approval_status: filters.value.approval_status,
    department: filters.value.department || undefined,
    role: filters.value.role || undefined,
    page: page.value,
    page_size: PAGE_SIZE,
  })
  loading.value = false
  if (res) {
    users.value = res.items ?? []
    total.value = res.pagination?.total ?? 0
  }
}

function applyFilters() { page.value = 1; load() }
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; load() } }

onMounted(async () => {
  availableRoles.value = (await getAvailableImmRoles()) ?? []
  await load()
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader title="Quản lý người dùng" :subtitle="`Tổng ${total} người dùng`">
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button
          v-if="auth.isSystemAdmin"
          class="btn-primary shrink-0"
          @click="router.push('/user-profiles/new')"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm người dùng
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="filters.search"
      search-placeholder="Tìm theo tên, email..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái duyệt</label>
          <select v-model="filters.approval_status" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả trạng thái</option>
            <option value="Approved">Đã duyệt</option>
            <option value="Pending">Chờ duyệt</option>
            <option value="Rejected">Từ chối</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Khoa / Phòng</label>
          <SmartSelect
            v-model="filters.department"
            doctype="AC Department"
            placeholder="Tất cả khoa/phòng..."
            @select="applyFilters"
            @clear="applyFilters"
          />
        </div>
        <div class="form-group">
          <label class="form-label">Vai trò</label>
          <select v-model="filters.role" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả vai trò</option>
            <option v-for="r in availableRoles" :key="r.name" :value="r.name">{{ r.label }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span v-if="activeFilterCount > 0">
          Kết quả lọc: <strong class="text-slate-700">{{ users.length }}</strong> / {{ total }} người dùng
        </span>
        <span v-else>
          Hiển thị <strong class="text-slate-700">{{ users.length }}</strong> / {{ total }} người dùng
        </span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="users.length === 0" class="text-center text-slate-400 py-12 text-sm">
        {{ activeFilterCount > 0 ? 'Không có người dùng nào phù hợp.' : 'Không có dữ liệu.' }}
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="u in users"
            :key="u.name"
            class="mobile-card"
            @click="router.push(`/user-profiles/${encodeURIComponent(u.name)}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700 truncate max-w-[60%]">{{ u.name }}</span>
              <span
                class="text-xs px-2 py-0.5 rounded-full font-medium"
                :class="APPROVAL_COLORS[u.imm_approval_status ?? ''] ?? 'bg-gray-100 text-gray-600'"
              >{{ APPROVAL_LABELS[u.imm_approval_status ?? ''] ?? u.imm_approval_status ?? '—' }}</span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ u.full_name || u.name }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ u.email || u.name }}</span>
              <span v-if="u.department_name">· {{ u.department_name }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Họ và tên</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden md:table-cell">Khoa/Phòng</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vai trò IMM</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trạng thái</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr
v-for="u in users" :key="u.name"
                class="hover:bg-gray-50 cursor-pointer"
                @click="router.push(`/user-profiles/${encodeURIComponent(u.name)}`)">
              <td class="px-4 py-3 font-medium text-gray-900">
                {{ u.full_name || u.name }}
              </td>
              <td class="px-4 py-3 text-gray-600 text-xs">{{ u.email || u.name }}</td>
              <td class="px-4 py-3 text-gray-600 text-xs hidden md:table-cell">
                {{ u.department_name || '—' }}
              </td>
              <td class="px-4 py-3">
                <div v-if="u.imm_roles?.length" class="flex flex-wrap gap-1">
                  <span
v-for="r in u.imm_roles" :key="r.name"
                        :title="r.name"
                        class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium"
                        :class="ROLE_GROUP_COLORS[r.group] ?? 'bg-gray-100 text-gray-600'">
                    {{ r.label }}
                  </span>
                </div>
                <span v-else class="text-xs text-gray-300">Chưa gán</span>
              </td>
              <td class="px-4 py-3">
                <button
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium hover:ring-2 hover:ring-current/50"
                  :class="APPROVAL_COLORS[u.imm_approval_status ?? ''] ?? 'bg-gray-100 text-gray-600'"
                  :title="`Lọc: ${APPROVAL_LABELS[u.imm_approval_status ?? ''] ?? u.imm_approval_status}`"
                  @click.stop="u.imm_approval_status && quickFilter('approval_status', u.imm_approval_status)"
                >
                  {{ APPROVAL_LABELS[u.imm_approval_status ?? ''] ?? u.imm_approval_status ?? '—' }}
                </button>
              </td>
              <td class="px-4 py-3">
                <button
class="text-blue-600 hover:underline text-xs"
                        @click.stop="router.push(`/user-profiles/${encodeURIComponent(u.name)}`)">
                  Xem / Sửa
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        </div>
      </template>

      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-gray-200 text-sm text-gray-600">
        <span>Trang {{ page }} · {{ total }} người dùng</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40" @click="prevPage">← Trước</button>
          <button :disabled="page * PAGE_SIZE >= total" class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40" @click="nextPage">Sau →</button>
        </div>
      </div>
    </div>
  </div>
</template>
