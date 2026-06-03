<script setup lang="ts">
// Lối tắt quản trị (admin) — Core Doc §9.8 (R4). Thay subtitle trang trí cũ
// ("Người dùng · Phân quyền · Master data · Audit chain" — text không bấm được)
// bằng nav tiles THẬT. Mỗi tile gate canAccessDrill: thiếu cap → ẩn (không
// dead-end /unauthorized, mirror §9.5 #12). Admin (data.admin) thấy đủ.
import { computed } from 'vue'
import { canAccessDrill } from '@/router/routeAccess'
import { useCapabilities } from '@/composables/useCapabilities'
import DashboardSection from '@/components/dashboard/DashboardSection.vue'

const { can } = useCapabilities()

interface Tile {
  to: string
  label: string
  desc: string
  icon: string // heroicons-style path
  tone: string // text/bg accent
}

const ALL_TILES: Tile[] = [
  {
    to: '/user-profiles', label: 'Người dùng', desc: 'Quản lý tài khoản IMM',
    icon: 'M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z',
    tone: 'text-blue-600 bg-blue-50',
  },
  {
    to: '/admin/roles', label: 'Phân quyền', desc: 'Vai trò theo module',
    icon: 'M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
    tone: 'text-purple-600 bg-purple-50',
  },
  {
    to: '/device-models', label: 'Dữ liệu gốc', desc: 'Model thiết bị',
    icon: 'M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z',
    tone: 'text-emerald-600 bg-emerald-50',
  },
  {
    to: '/suppliers', label: 'Nhà cung cấp', desc: 'Vendor & dịch vụ',
    icon: 'M13.5 21v-7.5a.75.75 0 0 1 .75-.75h3a.75.75 0 0 1 .75.75V21m-4.5 0H2.36m11.14 0H18m0 0h3.64m-1.39 0V9.349M3.75 21V9.349m0 0a3.001 3.001 0 0 0 3.75-.615A2.993 2.993 0 0 0 9.75 9.75c.896 0 1.7-.393 2.25-1.016a2.993 2.993 0 0 0 2.25 1.016c.896 0 1.7-.393 2.25-1.015a3.001 3.001 0 0 0 3.75.614m-16.5 0a3.004 3.004 0 0 1-.621-4.72l1.189-1.19A1.5 1.5 0 0 1 5.378 3h13.243a1.5 1.5 0 0 1 1.06.44l1.19 1.189a3 3 0 0 1-.621 4.72M6.75 18h3.75a.75.75 0 0 0 .75-.75V13.5a.75.75 0 0 0-.75-.75H6.75a.75.75 0 0 0-.75.75v3.75c0 .414.336.75.75.75Z',
    tone: 'text-amber-600 bg-amber-50',
  },
  {
    to: '/service-contracts', label: 'Hợp đồng', desc: 'Bảo trì & dịch vụ',
    icon: 'M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z',
    tone: 'text-cyan-600 bg-cyan-50',
  },
  {
    to: '/audit-trail', label: 'Nhật ký Kiểm toán', desc: 'Chuỗi audit ISO 13485',
    icon: 'M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25',
    tone: 'text-rose-600 bg-rose-50',
  },
]

// Gate: chỉ hiển thị tile user thật sự vào được (mirror §9.5 #12 — không dead-end).
const tiles = computed(() => ALL_TILES.filter((t) => canAccessDrill(t.to, can)))
</script>

<template>
  <DashboardSection title="Lối tắt quản trị" hint="Truy nhanh người dùng, phân quyền, dữ liệu gốc, kiểm toán">
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      <RouterLink
        v-for="t in tiles"
        :key="t.to"
        :to="t.to"
        class="group flex flex-col gap-2 rounded-xl border border-neutral-200/80 bg-white p-3.5
               shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-neutral-300
               hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
      >
        <span class="flex h-9 w-9 items-center justify-center rounded-lg" :class="t.tone">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" :d="t.icon" />
          </svg>
        </span>
        <div class="min-w-0">
          <p class="truncate text-sm font-semibold text-neutral-800 group-hover:text-blue-700">{{ t.label }}</p>
          <p class="truncate text-xs text-neutral-400">{{ t.desc }}</p>
        </div>
      </RouterLink>
    </div>
  </DashboardSection>
</template>
