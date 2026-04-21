<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { listUsers, type IMMUserListItem } from '@/api/user'

const router = useRouter()
const auth = useAuthStore()

const users = ref<IMMUserListItem[]>([])
const search = ref('')
const approvalStatus = ref('')
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const PAGE_SIZE = 20

const APPROVAL_COLORS: Record<string, string> = {
  Approved: 'bg-green-100 text-green-700',
  Pending: 'bg-amber-100 text-amber-700',
  Rejected: 'bg-red-100 text-red-700',
}
const APPROVAL_LABELS: Record<string, string> = {
  Approved: 'Đã duyệt', Pending: 'Chờ duyệt', Rejected: 'Từ chối',
}

async function load() {
  loading.value = true
  const res = await listUsers({
    search: search.value,
    approval_status: approvalStatus.value,
    page: page.value,
    page_size: PAGE_SIZE,
  })
  loading.value = false
  if (res) {
    users.value = res.items ?? []
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
        <span class="text-sm text-gray-500">{{ total }} người dùng</span>
        <button v-if="auth.isSystemAdmin"
                class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                @click="router.push('/user-profiles/new')">
          + Thêm người dùng
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap gap-3">
      <input v-model="search" type="text" placeholder="Tìm theo tên, email..."
             class="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
             @keyup.enter="handleSearch" />
      <select v-model="approvalStatus"
              class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              @change="handleSearch">
        <option value="">Tất cả trạng thái</option>
        <option value="Approved">Đã duyệt</option>
        <option value="Pending">Chờ duyệt</option>
        <option value="Rejected">Từ chối</option>
      </select>
      <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
              @click="handleSearch">Tìm</button>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="users.length === 0" class="text-center text-gray-400 py-12 text-sm">Không có dữ liệu.</div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Họ và tên</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden md:table-cell">Khoa/Phòng</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trạng thái</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="u in users" :key="u.name"
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
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                      :class="APPROVAL_COLORS[u.imm_approval_status ?? ''] ?? 'bg-gray-100 text-gray-600'">
                  {{ APPROVAL_LABELS[u.imm_approval_status ?? ''] ?? u.imm_approval_status ?? '—' }}
                </span>
              </td>
              <td class="px-4 py-3">
                <button class="text-blue-600 hover:underline text-xs"
                        @click.stop="router.push(`/user-profiles/${encodeURIComponent(u.name)}`)">
                  Xem / Sửa
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

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
