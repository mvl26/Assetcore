<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSidebar } from '@/composables/useSidebar'

const router = useRouter()
const route = useRoute()
const { collapsed, toggle, sidebarClass, closeMobile } = useSidebar()

interface NavItem {
  label: string
  path: string
  icon: string
  badge?: string          // Mã module (IMM-xx)
  children?: NavItem[]    // Sub-items (hiển thị khi expand)
}
interface NavGroup { title: string; items: NavItem[] }

// Sidebar theo WHO HTM lifecycle — giảm clutter, gộp theo nghiệp vụ
const navGroups: NavGroup[] = [
  {
    title: '',
    items: [{ label: 'Trang chủ', path: '/dashboard', icon: 'dashboard' }],
  },
  {
    title: 'Vòng đời thiết bị',
    items: [
      {
        label: 'Thiết bị', path: '/assets', icon: 'cube',
        children: [
          { label: 'Danh sách', path: '/assets', icon: 'list' },
          { label: 'Luân chuyển', path: '/asset-transfers', icon: 'arrow' },
          { label: 'Hợp đồng DV', path: '/service-contracts', icon: 'document' },
          { label: 'Khấu hao', path: '/depreciation', icon: 'chart' },
        ],
      },
      { label: 'Tiếp nhận & Lắp đặt', path: '/commissioning', icon: 'truck', badge: '04' },
      { label: 'Hồ sơ thiết bị', path: '/documents', icon: 'folder', badge: '05' },
    ],
  },
  {
    title: 'Bảo trì & Vận hành',
    items: [
      {
        label: 'Bảo trì định kỳ', path: '/pm/dashboard', icon: 'wrench', badge: '08',
        children: [
          { label: 'Dashboard', path: '/pm/dashboard', icon: 'chart' },
          { label: 'Lịch PM', path: '/pm/calendar', icon: 'calendar' },
          { label: 'Work Orders', path: '/pm/work-orders', icon: 'list' },
          { label: 'PM Schedules', path: '/pm/schedules', icon: 'repeat' },
          { label: 'Templates', path: '/pm/templates', icon: 'template' },
        ],
      },
      {
        label: 'Sửa chữa', path: '/cm/dashboard', icon: 'repair', badge: '09',
        children: [
          { label: 'Dashboard', path: '/cm/dashboard', icon: 'chart' },
          { label: 'Tạo WO sửa chữa', path: '/cm/create', icon: 'plus' },
          { label: 'Work Orders', path: '/cm/work-orders', icon: 'list' },
          { label: 'Firmware CR', path: '/cm/firmware', icon: 'chip' },
          { label: 'MTTR Report', path: '/cm/mttr', icon: 'chart' },
        ],
      },
      {
        label: 'Hiệu chuẩn', path: '/calibration/dashboard', icon: 'calibration', badge: '11',
        children: [
          { label: 'Dashboard', path: '/calibration/dashboard', icon: 'chart' },
          { label: 'Danh sách phiếu', path: '/calibration', icon: 'list' },
          { label: 'Lịch hiệu chuẩn', path: '/calibration/schedules', icon: 'calendar' },
          { label: 'Tạo phiếu', path: '/calibration/new', icon: 'plus' },
        ],
      },
    ],
  },
  {
    title: 'Chất lượng & Tuân thủ',
    items: [
      { label: 'Sự cố', path: '/incidents', icon: 'alert' },
      { label: 'CAPA', path: '/capas', icon: 'shield' },
      { label: 'Audit Trail', path: '/audit-trail', icon: 'lock' },
    ],
  },
  {
    title: 'Hệ thống',
    items: [
      {
        label: 'Dữ liệu gốc', path: '/reference-data', icon: 'settings',
        children: [
          { label: 'Nhà cung cấp', path: '/suppliers', icon: 'building' },
          { label: 'Device Model', path: '/device-models', icon: 'template' },
          { label: 'SLA Policy', path: '/sla-policies', icon: 'document' },
          { label: 'Reference', path: '/reference-data', icon: 'folder' },
        ],
      },
      { label: 'Người dùng', path: '/user-profiles', icon: 'users' },
    ],
  },
]

const EXACT_MATCH_PATHS = new Set([
  '/commissioning', '/documents', '/assets', '/suppliers', '/device-models',
  '/incidents', '/capas', '/asset-transfers', '/service-contracts',
  '/pm/work-orders', '/cm/work-orders', '/calibration',
])

function isActive(path: string): boolean {
  if (EXACT_MATCH_PATHS.has(path)) return route.path === path
  return route.path === path || route.path.startsWith(path + '/')
}

// Group nào được expand (lưu trong localStorage)
const EXPAND_STORAGE_KEY = 'ac-sidebar-expanded'
const initialExpanded: Record<string, boolean> = (() => {
  try {
    return JSON.parse(localStorage.getItem(EXPAND_STORAGE_KEY) || '{}')
  } catch { return {} }
})()
const expanded = ref<Record<string, boolean>>(initialExpanded)

// Auto-expand nhóm chứa active route
function hasActiveChild(item: NavItem): boolean {
  if (!item.children) return false
  return item.children.some(c => isActive(c.path))
}

function isExpanded(item: NavItem): boolean {
  return expanded.value[item.path] === true || hasActiveChild(item)
}

function toggleExpand(item: NavItem, event: MouseEvent): void {
  event.stopPropagation()
  expanded.value = { ...expanded.value, [item.path]: !isExpanded(item) }
  localStorage.setItem(EXPAND_STORAGE_KEY, JSON.stringify(expanded.value))
}

function navigate(path: string): void {
  closeMobile()
  router.push(path)
}

function handleItemClick(item: NavItem): void {
  // Nếu có children và sidebar không collapsed, click vào item vừa mở vừa navigate
  navigate(item.path)
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
        <div v-if="!collapsed" class="min-w-0">
          <p class="font-display font-bold text-lg text-white truncate leading-tight">AssetCore</p>
          <p class="text-[12px] mt-0.5 truncate" style="color: rgba(255,255,255,0.42)">HTM Platform</p>
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
      <div v-for="(group, gi) in navGroups" :key="group.title || `g-${gi}`" class="mb-4">
        <div
          v-if="!collapsed && group.title"
          class="font-display px-2.5 mb-2 text-[13px] font-semibold uppercase tracking-[0.08em]"
          style="color: rgba(255,255,255,0.55)"
        >
          {{ group.title }}
        </div>
        <div v-else-if="collapsed && gi > 0" class="my-2.5" style="border-top: 1px solid rgba(255,255,255,0.06)" />

        <template v-for="item in group.items" :key="item.path">
          <!-- Main item button -->
          <button
            class="relative w-full flex items-center gap-3.5 px-3 py-3 text-base rounded-md transition-all duration-150 group"
            :class="collapsed ? 'justify-center' : ''"
            :style="isActive(item.path)
              ? 'background: rgba(37,99,235,0.18); color: #bfdbfe; font-weight: 600;'
              : 'color: rgba(255,255,255,0.7); font-weight: 450;'"
            :title="collapsed ? item.label : ''"
            @click="handleItemClick(item)"
          >
            <span
              v-if="isActive(item.path)"
              class="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r"
              style="background: #3b82f6"
            />

            <!-- Icon -->
            <span class="shrink-0 w-5 h-5 flex items-center justify-center">
              <svg v-if="item.icon === 'dashboard'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
                <rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
              </svg>
              <svg v-else-if="item.icon === 'list'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
              <svg v-else-if="item.icon === 'plus'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <circle cx="12" cy="12" r="9" /><path stroke-linecap="round" d="M12 8v8M8 12h8" />
              </svg>
              <svg v-else-if="item.icon === 'cube'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25M21 7.5v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
              </svg>
              <svg v-else-if="item.icon === 'truck'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
              </svg>
              <svg v-else-if="item.icon === 'folder'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
              </svg>
              <svg v-else-if="item.icon === 'wrench'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m5.108-.233l-5.108.233" />
              </svg>
              <svg v-else-if="item.icon === 'repair'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
              </svg>
              <svg v-else-if="item.icon === 'calibration'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" />
              </svg>
              <svg v-else-if="item.icon === 'calendar'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
              <svg v-else-if="item.icon === 'repeat'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16 4l4 4-4 4M20 8H8a4 4 0 00-4 4v1M8 20l-4-4 4-4M4 16h12a4 4 0 004-4v-1" />
              </svg>
              <svg v-else-if="item.icon === 'template'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <rect x="3" y="3" width="18" height="18" rx="2"/><path stroke-linecap="round" d="M3 9h18M9 21V9"/>
              </svg>
              <svg v-else-if="item.icon === 'chart'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 3v18h18M7 14l4-4 4 4 5-5" />
              </svg>
              <svg v-else-if="item.icon === 'chip'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <rect x="6" y="6" width="12" height="12" rx="1.5" /><path stroke-linecap="round" d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
              </svg>
              <svg v-else-if="item.icon === 'document'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                <path stroke-linecap="round" stroke-linejoin="round" d="M14 2v6h6M9 13h6M9 17h4"/>
              </svg>
              <svg v-else-if="item.icon === 'alert'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              </svg>
              <svg v-else-if="item.icon === 'shield'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <svg v-else-if="item.icon === 'lock'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <rect x="4" y="11" width="16" height="10" rx="2"/><path stroke-linecap="round" d="M8 11V7a4 4 0 118 0v4"/>
              </svg>
              <svg v-else-if="item.icon === 'arrow'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"/>
              </svg>
              <svg v-else-if="item.icon === 'settings'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <circle cx="12" cy="12" r="3" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
              </svg>
              <svg v-else-if="item.icon === 'users'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path stroke-linecap="round" stroke-linejoin="round" d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
              <svg v-else-if="item.icon === 'building'" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-[18px] h-[18px]">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 21h18M5 21V5a2 2 0 012-2h10a2 2 0 012 2v16M9 7h2M9 11h2M9 15h2M13 7h2M13 11h2M13 15h2"/>
              </svg>
            </span>

            <!-- Label + badge -->
            <span v-if="!collapsed" class="flex-1 truncate text-left">{{ item.label }}</span>
            <span
              v-if="!collapsed && item.badge"
              class="text-[10px] font-mono px-1.5 py-0.5 rounded"
              style="background: #2563eb; color: #ffffff;"
            >{{ item.badge }}</span>

            <!-- Chevron khi có children -->
            <button
              v-if="!collapsed && item.children"
              class="shrink-0 p-0.5 rounded hover:bg-white/5"
              @click="toggleExpand(item, $event)"
              :title="isExpanded(item) ? 'Thu gọn' : 'Mở rộng'"
            >
              <svg
                class="w-3 h-3 transition-transform duration-150"
                :class="isExpanded(item) ? 'rotate-90' : ''"
                fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>

            <!-- Tooltip khi collapsed -->
            <span
              v-if="collapsed"
              class="absolute left-full ml-2.5 px-2.5 py-1.5 text-xs rounded-md whitespace-nowrap
                     opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 text-white"
              style="background: #161b22; border: 1px solid rgba(255,255,255,0.10)"
            >
              {{ item.label }}<span v-if="item.badge" class="ml-1.5 opacity-60">· {{ item.badge }}</span>
            </span>
          </button>

          <!-- Sub-items (chỉ hiển thị khi expanded + sidebar không collapsed) -->
          <div v-if="!collapsed && item.children && isExpanded(item)" class="ml-3 pl-3 mb-1" style="border-left: 1px solid rgba(255,255,255,0.06)">
            <button
              v-for="child in item.children"
              :key="child.path"
              class="w-full flex items-center gap-2.5 px-2 py-1.5 text-[12.5px] rounded-md transition-all duration-150"
              :style="isActive(child.path)
                ? 'color: #bfdbfe; background: rgba(37,99,235,0.12); font-weight: 500;'
                : 'color: rgba(255,255,255,0.55); font-weight: 400;'"
              @click="navigate(child.path)"
            >
              <span class="w-1 h-1 rounded-full shrink-0" style="background: currentColor"></span>
              <span class="truncate text-left">{{ child.label }}</span>
            </button>
          </div>
        </template>
      </div>
    </nav>

    <!-- Footer -->
    <div
      v-if="!collapsed"
      class="px-4 py-3 text-[10px]"
      style="border-top: 1px solid rgba(255,255,255,0.07); color: rgba(255,255,255,0.2)"
    >
      AssetCore v1.0 · Wave 1
    </div>
  </aside>
</template>
