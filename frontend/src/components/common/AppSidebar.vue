<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useSidebar } from '@/composables/useSidebar'

const router = useRouter()
const route = useRoute()
const { collapsed, toggle, sidebarClass } = useSidebar()

interface NavItem {
  label: string
  path: string
  icon: string
}

interface NavGroup {
  title: string
  items: NavItem[]
}

const navGroups: NavGroup[] = [
  {
    title: 'Tổng quan',
    items: [
      { label: 'Dashboard', path: '/dashboard', icon: 'grid' },
    ],
  },
  {
    title: 'IMM-04 Lắp đặt',
    items: [
      { label: 'Danh sách phiếu', path: '/commissioning', icon: 'list' },
      { label: 'Tạo phiếu mới', path: '/commissioning/new', icon: 'plus' },
    ],
  },
  {
    title: 'IMM-05 Hồ sơ',
    items: [
      { label: 'Quản lý Hồ sơ', path: '/documents', icon: 'folder' },
      { label: 'Tải lên tài liệu', path: '/documents/new', icon: 'upload' },
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
    :class="[
      'fixed left-0 top-0 h-full z-40 bg-gray-900 text-white flex flex-col transition-all duration-200 overflow-hidden',
      sidebarClass,
    ]"
  >
    <!-- Logo area -->
    <div class="flex items-center h-16 px-3 border-b border-gray-700 shrink-0">
      <div class="flex items-center gap-2 flex-1 min-w-0">
        <div class="shrink-0 w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-sm">
          AC
        </div>
        <span v-if="!collapsed" class="font-semibold text-sm truncate">AssetCore</span>
      </div>
      <button
        class="shrink-0 p-1 rounded hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
        :title="collapsed ? 'Mở rộng' : 'Thu gọn'"
        @click="toggle"
      >
        <!-- Chevron icon -->
        <svg
          class="w-4 h-4 transition-transform duration-200"
          :class="collapsed ? 'rotate-180' : ''"
          fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto py-3 space-y-1">
      <div v-for="group in navGroups" :key="group.title" class="mb-2">
        <!-- Group label -->
        <div
          v-if="!collapsed"
          class="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider"
        >
          {{ group.title }}
        </div>
        <div v-else class="px-3 py-1">
          <div class="border-t border-gray-700" />
        </div>

        <!-- Nav items -->
        <button
          v-for="item in group.items"
          :key="item.path"
          class="w-full flex items-center gap-3 px-3 py-2 text-sm rounded-md mx-0 transition-colors relative group"
          :class="[
            isActive(item.path)
              ? 'bg-blue-600 text-white'
              : 'text-gray-300 hover:bg-gray-700 hover:text-white',
            collapsed ? 'justify-center' : '',
          ]"
          :title="collapsed ? item.label : ''"
          @click="navigate(item.path)"
        >
          <!-- Icon -->
          <span class="shrink-0 w-5 h-5 flex items-center justify-center">
            <!-- Grid icon (Dashboard) -->
            <svg v-if="item.icon === 'grid'" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="w-5 h-5">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
            <!-- List icon -->
            <svg v-else-if="item.icon === 'list'" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
            <!-- Plus icon -->
            <svg v-else-if="item.icon === 'plus'" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <!-- Folder icon -->
            <svg v-else-if="item.icon === 'folder'" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
            </svg>
            <!-- Upload icon -->
            <svg v-else-if="item.icon === 'upload'" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M16 8l-4-4-4 4M12 4v12" />
            </svg>
          </span>

          <!-- Label (hidden when collapsed) -->
          <span v-if="!collapsed" class="truncate">{{ item.label }}</span>

          <!-- Tooltip when collapsed -->
          <span
            v-if="collapsed"
            class="absolute left-full ml-2 px-2 py-1 text-xs bg-gray-800 text-white rounded shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50"
          >
            {{ item.label }}
          </span>
        </button>
      </div>
    </nav>
  </aside>
</template>
