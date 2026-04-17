<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useSidebar } from '@/composables/useSidebar'

const router = useRouter()
const route = useRoute()
const { collapsed, toggle, sidebarClass } = useSidebar()

interface NavItem { label: string; path: string; icon: string }
interface NavGroup { title: string; items: NavItem[] }

const navGroups: NavGroup[] = [
  {
    title: 'Tổng quan',
    items: [{ label: 'Dashboard', path: '/dashboard', icon: 'dashboard' }],
  },
  {
    title: 'IMM-04 Lắp đặt',
    items: [
      { label: 'Danh sách phiếu', path: '/commissioning', icon: 'list' },
    ],
  },
  {
    title: 'IMM-05 Hồ sơ',
    items: [
      { label: 'Quản lý Hồ sơ', path: '/documents', icon: 'folder' },
    ],
  },
  {
    title: 'IMM-08 Bảo trì PM',
    items: [
      { label: 'Lịch bảo trì', path: '/pm/calendar', icon: 'calendar' },
      { label: 'Phiếu bảo trì', path: '/pm/work-orders', icon: 'list' },
      { label: 'Dashboard PM', path: '/pm/dashboard', icon: 'chart' },
    ],
  },
  {
    title: 'IMM-09 Sửa chữa (CM)',
    items: [
      { label: 'Dashboard CM', path: '/cm/dashboard', icon: 'chart' },
      { label: 'Danh sách WO', path: '/cm/work-orders', icon: 'list' },
      { label: 'MTTR Report', path: '/cm/mttr', icon: 'chart' },
    ],
  },
]

function isActive(path: string): boolean {
  if (path === '/commissioning') return route.path === '/commissioning'
  if (path === '/documents') return route.path === '/documents'
  return route.path === path || route.path.startsWith(path + '/')
}

function navigate(path: string): void {
  router.push(path)
}
</script>

<template>
  <aside
    :class="['fixed left-0 top-0 h-full z-40 flex flex-col transition-all duration-200 overflow-hidden', sidebarClass]"
    style="background: #0d1117; box-shadow: 1px 0 0 rgba(255,255,255,0.05)"
  >
    <!-- Logo -->
    <div class="flex items-center h-14 px-3 shrink-0" style="border-bottom: 1px solid rgba(255,255,255,0.07)">
      <div class="flex items-center gap-2.5 flex-1 min-w-0">
        <div
          class="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs text-white"
          style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)"
        >
          AC
        </div>
        <div v-if="!collapsed" class="min-w-0 animate-fade-in">
          <p class="font-semibold text-sm text-white truncate leading-none">AssetCore</p>
          <p class="text-[10px] mt-0.5 truncate" style="color: rgba(255,255,255,0.3)">HTM Platform</p>
        </div>
      </div>
      <button
        class="shrink-0 p-1.5 rounded-md transition-all duration-150"
        style="color: rgba(255,255,255,0.3)"
        :title="collapsed ? 'Mở rộng' : 'Thu gọn'"
        @click="toggle"
      >
        <svg
          class="w-3.5 h-3.5 transition-transform duration-200"
          :class="collapsed ? 'rotate-180' : ''"
          fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto py-3 px-2">
      <div v-for="group in navGroups" :key="group.title" class="mb-4">
        <div
          v-if="!collapsed"
          class="px-2 mb-1 text-[10px] font-semibold uppercase tracking-widest"
          style="color: rgba(255,255,255,0.22)"
        >
          {{ group.title }}
        </div>
        <div v-else class="my-2" style="border-top: 1px solid rgba(255,255,255,0.07)" />

        <button
          v-for="item in group.items"
          :key="item.path"
          class="relative w-full flex items-center gap-2.5 px-2.5 py-2 text-[13px] rounded-md transition-all duration-150 group"
          :class="collapsed ? 'justify-center' : ''"
          :style="isActive(item.path)
            ? 'background: rgba(37,99,235,0.16); color: #93c5fd; font-weight: 500;'
            : 'color: rgba(255,255,255,0.48);'"
          :title="collapsed ? item.label : ''"
          @click="navigate(item.path)"
        >
          <!-- Active accent stripe -->
          <span
            v-if="isActive(item.path)"
            class="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r"
            style="background: #3b82f6"
          />

          <!-- Icon -->
          <span class="shrink-0 w-4 h-4 flex items-center justify-center">
            <svg v-if="item.icon === 'dashboard'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4">
              <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
              <rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
            </svg>
            <svg v-else-if="item.icon === 'list'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
            <svg v-else-if="item.icon === 'plus'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4">
              <circle cx="12" cy="12" r="9" /><path stroke-linecap="round" d="M12 8v8M8 12h8" />
            </svg>
            <svg v-else-if="item.icon === 'folder'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
            </svg>
            <svg v-else-if="item.icon === 'upload'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M16 8l-4-4-4 4M12 4v12" />
            </svg>
            <svg v-else-if="item.icon === 'chart'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <!-- Calendar icon -->
            <svg v-else-if="item.icon === 'calendar'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-4 h-4">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </span>

          <!-- Label -->
          <span v-if="!collapsed" class="truncate">{{ item.label }}</span>

          <!-- Collapsed tooltip -->
          <span
            v-if="collapsed"
            class="absolute left-full ml-2.5 px-2.5 py-1.5 text-xs rounded-md whitespace-nowrap
                   opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 text-white"
            style="background: #161b22; border: 1px solid rgba(255,255,255,0.10)"
          >
            {{ item.label }}
          </span>
        </button>
      </div>
    </nav>

    <!-- Footer -->
    <div
      v-if="!collapsed"
      class="px-4 py-3 text-[10px]"
      style="border-top: 1px solid rgba(255,255,255,0.07); color: rgba(255,255,255,0.18)"
    >
      AssetCore v1.0 · Wave 1
    </div>
  </aside>
</template>
