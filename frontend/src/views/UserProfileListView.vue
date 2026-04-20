<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { listProfiles } from '@/api/userProfile'
import type { ACUserProfileListItem } from '@/api/userProfile'

const router = useRouter()
const auth = useAuthStore()

const profiles = ref<ACUserProfileListItem[]>([])
const search = ref('')
const department = ref('')
const isActive = ref<'' | '0' | '1'>('')
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const PAGE_SIZE = 20

async function load() {
  loading.value = true
  const params: Record<string, unknown> = { page: page.value, page_size: PAGE_SIZE }
  if (search.value) params.search = search.value
  if (department.value) params.department = department.value
  if (isActive.value !== '') params.is_active = Number(isActive.value)

  const res = await listProfiles(params as Parameters<typeof listProfiles>[0])
  loading.value = false
  if (res) {
    profiles.value = res.items ?? []
    total.value = res.pagination?.total ?? 0
  }
}

function handleSearch() { page.value = 1; load() }
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; load() } }

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Quản lý Người dùng IMM</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ total }} hồ sơ</span>
        <button
          v-if="auth.isSystemAdmin"
          class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          @click="router.push('/user-profiles/new')"
        >
          + Thêm người dùng
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap gap-3">
      <input
        v-model="search"
        type="text"
        placeholder="Tìm theo tên, email, mã NV..."
        class="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        @keyup.enter="handleSearch"
      />
      <select
        v-model="isActive"
        class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        @change="handleSearch"
      >
        <option value="">Tất cả trạng thái</option>
        <option value="1">Đang hoạt động</option>
        <option value="0">Ngừng hoạt động</option>
      </select>
      <button
        class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        @click="handleSearch"
      >
        Tìm
      </button>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="profiles.length === 0" class="text-center text-gray-400 py-12 text-sm">
        Không có dữ liệu.
      </div>
      <div v-else class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Họ và tên</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mã NV</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Chức danh</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Khoa/Phòng</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trạng thái</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thao tác</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr
            v-for="p in profiles"
            :key="p.name"
            class="hover:bg-gray-50 cursor-pointer"
            @click="router.push(`/user-profiles/${encodeURIComponent(p.user)}`)"
          >
            <td class="px-4 py-3 font-medium text-gray-900">{{ p.full_name || p.user }}</td>
            <td class="px-4 py-3 text-gray-600 text-xs">{{ p.user }}</td>
            <td class="px-4 py-3 text-gray-600">{{ p.employee_code || '—' }}</td>
            <td class="px-4 py-3 text-gray-600">{{ p.job_title || '—' }}</td>
            <td class="px-4 py-3">
              <div class="text-gray-700">{{ p.department_name || p.department || '—' }}</div>
              <div v-if="p.department && p.department_name" class="text-xs text-gray-400">{{ p.department }}</div>
            </td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                :class="p.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
              >
                {{ p.is_active ? 'Hoạt động' : 'Ngừng' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <button
                class="text-blue-600 hover:underline text-xs"
                @click.stop="router.push(`/user-profiles/${encodeURIComponent(p.user)}`)"
              >
                Xem / Sửa
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <!-- Pagination -->
      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-gray-200 text-sm text-gray-600">
        <span>Trang {{ page }} · {{ total }} hồ sơ</span>
        <div class="flex gap-2">
          <button
            :disabled="page === 1"
            class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40"
            @click="prevPage"
          >
            ← Trước
          </button>
          <button
            :disabled="page * PAGE_SIZE >= total"
            class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40"
            @click="nextPage"
          >
            Sau →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
