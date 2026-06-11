<script setup lang="ts">
// AppSidebar — nav derive TRỰC TIẾP từ ROLE THẬT (Core Doc §2.1 + §7.ter).
// Spec: docs/architecture/FE_Persona_Navigation.md
// Phase 1.2: KHÔNG còn persona switcher. usePersona trả tập persona role thật
// mở khoá → buildSidebarGroupsForRoles() UNION module mọi persona → tra
// MODULE_NAV → lọc CAPABILITY (useCapabilities) → render theo group, ẩn group
// rỗng. Header dùng primaryPersona (rank cao nhất) chỉ để HIỂN THỊ, không đổi được.
// Click logo/header → /dashboard. KHÔNG còn /launcher.
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSidebar } from '@/composables/useSidebar'
import { usePersona } from '@/composables/usePersona'
import { useCapabilities } from '@/composables/useCapabilities'
import { useAuthStore } from '@/stores/auth'
import { SUPERUSER_ROLES } from '@/constants/personas'
import { buildSidebarGroupsForRoles, type NavItem, type SidebarGroup } from '@/constants/sidebarNav'
import {
  GROUPS_STORAGE_KEY,
  readClosedGroups,
  toggleClosedGroup,
  isGroupOpen,
  readPinnedGroups,
  togglePinnedGroup,
  defaultClosedGroups,
  orderGroupsWithPins,
} from '@/constants/sidebarGroups'

const router = useRouter()
const route  = useRoute()
const auth   = useAuthStore()
const { can } = useCapabilities()
const { collapsed, toggle, sidebarClass, mobileOpen, closeMobile } = useSidebar()
const { personas, primaryPersona } = usePersona()

// Superuser bypass — Frappe-level admin + AssetCore super admin see mọi nav item.
const isSuperuser = computed(() => auth.hasAnyRole(SUPERUSER_ROLES))

// ─── Icons ────────────────────────────────────────────────────────────────────
const SZ = 'fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24" class="w-[18px] h-[18px]"'
const ICONS: Record<string, string> = {
  grid:      `<svg ${SZ}><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>`,
  device:    `<svg ${SZ}><rect x="2" y="4" width="20" height="14" rx="2"/><path stroke-linecap="round" d="M8 20h8M12 18v2"/></svg>`,
  template:  `<svg ${SZ}><rect x="3" y="3" width="18" height="18" rx="2"/><path stroke-linecap="round" d="M3 9h18M9 21V9"/></svg>`,
  transfer:  `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4"/></svg>`,
  trending:  `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M22 17l-8.5-8.5-5 5L2 7"/><path stroke-linecap="round" stroke-linejoin="round" d="M16 17h6v-6"/></svg>`,
  cart:      `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2 9m12-9l2 9m-9-4h4"/></svg>`,
  clipboard: `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>`,
  chart:     `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>`,
  wrench:    `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>`,
  calendar:  `<svg ${SZ}><rect x="3" y="4" width="18" height="18" rx="2"/><path stroke-linecap="round" d="M16 2v4M8 2v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/></svg>`,
  list:      `<svg ${SZ}><path stroke-linecap="round" d="M9 5h11M9 12h11M9 19h11"/><circle cx="4" cy="5" r="1.2" fill="currentColor"/><circle cx="4" cy="12" r="1.2" fill="currentColor"/><circle cx="4" cy="19" r="1.2" fill="currentColor"/></svg>`,
  tool:      `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M14.7 6.3l4 4-9 9-4-4 9-9zM13 8l3 3M5 15l4 4M3 21h6"/></svg>`,
  code:      `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>`,
  gauge:     `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 0v4M4.22 4.22l2.83 2.83M2 12h4m13.78-7.78l-2.83 2.83M22 12h-4"/><path stroke-linecap="round" d="M12 12l3-4"/></svg>`,
  alert:     `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>`,
  shield:    `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
  log:       `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 12h.01M9 16h.01M13 12h3M13 16h3"/></svg>`,
  folder:    `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/></svg>`,
  inbox:     `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0H4m8-5l-3 3m0 0l3 3m-3-3h6"/></svg>`,
  box:       `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><path stroke-linecap="round" stroke-linejoin="round" d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12"/></svg>`,
  cog:       `<svg ${SZ}><circle cx="12" cy="12" r="3"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>`,
  arrows:    `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4M4 17h12M4 17l4-4M4 17l4 4"/></svg>`,
  warehouse: `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11"/><rect x="9" y="14" width="6" height="7" rx="0.5"/></svg>`,
  uom:       `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M3 7h18M3 12h18M3 17h18"/><path stroke-linecap="round" d="M7 5v4M11 5v4M15 5v4M19 5v4M7 15v4M11 15v4M15 15v4M19 15v4"/></svg>`,
  building:  `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v3M12 14v3M16 14v3"/></svg>`,
  contract:  `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6M9 16h4M5 4h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z"/></svg>`,
  clock:     `<svg ${SZ}><circle cx="12" cy="12" r="10"/><path stroke-linecap="round" d="M12 6v6l4 2"/></svg>`,
  database:  `<svg ${SZ}><ellipse cx="12" cy="5" rx="9" ry="3"/><path stroke-linecap="round" d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path stroke-linecap="round" d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`,
  users:     `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path stroke-linecap="round" stroke-linejoin="round" d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>`,
  qr:        `<svg ${SZ}><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path stroke-linecap="round" d="M14 14h2m3 0h1M14 17h1M17 17h1M20 17v1M14 20h3M18 20h2"/><rect x="5" y="5" width="3" height="3" fill="currentColor"/><rect x="16" y="5" width="3" height="3" fill="currentColor"/><rect x="5" y="16" width="3" height="3" fill="currentColor"/></svg>`,
  home:      `<svg ${SZ}><path stroke-linecap="round" stroke-linejoin="round" d="M3 12l9-9 9 9M5 10v10a1 1 0 001 1h4v-6h4v6h4a1 1 0 001-1V10"/></svg>`,
}

// ─── Role thật → sidebar nav (Phase 1.2) ───────────────────────────────────────
// Phase 1.6 (Core Doc §7.sexies.1): header sidebar KHÔNG còn hiển thị NHÃN persona
// (vd nhãn vai trò tiếng Việt). Brand tĩnh "AssetCore" — quản trị bằng ROLE, không
// nhãn persona ở chrome. `primaryPersona` GIỮ để tô màu logo (cosmetic) +
// DashboardView route dashboard mặc định — KHÔNG render label text.
const BRAND_TITLE = 'AssetCore'
const personaColor = computed<string>(() => primaryPersona.value?.color ?? '#0E6FFF')

// Nav theo GROUP — buildSidebarGroupsForRoles UNION module mọi persona role thật,
// lọc capability + dedupe path toàn cục + bỏ group rỗng.
// D7: chỉ ORDER lại (nhóm ghim lên đầu) — KHÔNG đụng items/itemVisible (RBAC bất
// biến: orderGroupsWithPins không thêm/bớt nhóm hay entry nào).
const pinnedGroups = ref<string[]>(readPinnedGroups())
const navGroups = computed(() =>
  orderGroupsWithPins(
    buildSidebarGroupsForRoles(personas.value, can, isSuperuser.value),
    pinnedGroups.value,
  ),
)
// Flat list (collapsed mode + active-path matching).
const navItems = computed<NavItem[]>(() => navGroups.value.flatMap((g) => g.items))
const hasNav = computed<boolean>(() => navItems.value.length > 0)

// ─── Active item (longest prefix match) ───────────────────────────────────────
const NAME_TO_PATH: Record<string, string> = {
  IncidentDetail: '/incidents/list',
  IncidentCreate: '/incidents/list',
  RCADetail:      '/incidents/list',
  CMCreate:       '/cm/work-orders',
  CMDiagnose:     '/cm/work-orders',
  CMParts:        '/cm/work-orders',
  CMChecklist:    '/cm/work-orders',
}

const activeItemPath = computed<string>(() => {
  const name = route.name as string | undefined
  if (name && NAME_TO_PATH[name]) return NAME_TO_PATH[name]

  const p = route.path
  let best = ''
  for (const it of navItems.value) {
    if ((p === it.path || p.startsWith(it.path + '/')) && it.path.length > best.length) {
      best = it.path
    }
  }
  return best
})
function isActive(path: string): boolean { return activeItemPath.value === path }

// ─── Collapsible groups (Core Doc §7.bis + ADR-IMM00-CMDK D7) ─────────────────
// Persist danh sách group ĐANG ĐÓNG; default mở; group active luôn mở.
// D7: persona đa-nhóm (> ngưỡng) → nhóm "ít dùng" (Governance/Compliance/Admin)
// default-collapsed; nhóm vận hành expanded. CHỈ áp khi user CHƯA tự tuỳ chỉnh
// (chưa có key persist) — tôn trọng lựa chọn user sau khi họ đã toggle.
// Nhóm GHIM (📌) luôn expand (defaultClosedGroups đã loại pinned).
const hasPersistedClosed = localStorage.getItem(GROUPS_STORAGE_KEY) !== null
const closedGroups = ref<string[]>(
  hasPersistedClosed
    ? readClosedGroups()
    : defaultClosedGroups(
        buildSidebarGroupsForRoles(personas.value, can, isSuperuser.value),
        pinnedGroups.value,
      ),
)

// Group chứa item đang active → để auto-open (không giấu chức năng đang dùng).
const activeGroupTitle = computed<string | null>(() => {
  const p = activeItemPath.value
  if (!p) return null
  const g = navGroups.value.find((grp) => grp.items.some((it) => it.path === p))
  return g ? g.title : null
})

function groupOpen(group: SidebarGroup): boolean {
  // Nhóm ghim → luôn mở (D7).
  if (pinnedGroups.value.includes(group.title)) return true
  return isGroupOpen(group, closedGroups.value, activeGroupTitle.value)
}

function toggleGroup(group: SidebarGroup): void {
  closedGroups.value = toggleClosedGroup(group.title)
}

function togglePinGroup(group: SidebarGroup, e: Event): void {
  e.stopPropagation()
  pinnedGroups.value = togglePinnedGroup(group.title)
}
function isGroupPinned(title: string): boolean {
  return pinnedGroups.value.includes(title)
}

// ─── Logo → dashboard (persona home) ──────────────────────────────────────────
function goHome() { router.push('/dashboard') }
</script>

<template>
  <aside
    :class="[
      'fixed left-0 top-0 h-full z-40 flex flex-col transition-all duration-300 overflow-hidden',
      sidebarClass,
      mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
    ]"
    class="sidebar-root"
  >
    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <div class="sidebar-header flex items-center h-14 px-3 shrink-0">
      <button
        type="button"
        class="logo-button flex items-center gap-3 flex-1 min-w-0 rounded-lg p-1 -m-1 transition-colors"
        title="Về Bảng điều khiển"
        @click="goHome"
      >
        <div
          class="logo-badge shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-white"
          :style="{ background: `linear-gradient(135deg, ${personaColor} 0%, ${personaColor} 100%)` }"
        >
          <span v-html="ICONS.home" />
        </div>
        <Transition name="fade-x">
          <div v-if="!collapsed" class="min-w-0 text-left">
            <p class="font-bold text-[13.5px] text-white tracking-tight leading-none truncate">
              {{ BRAND_TITLE }}
            </p>
            <p class="text-[10.5px] mt-1 side-foot-text font-medium">Bảng điều khiển</p>
          </div>
        </Transition>
      </button>
      <!-- Mobile close button (X) — hidden on desktop -->
      <button
        class="toggle-btn shrink-0 w-7 h-7 rounded-lg flex items-center justify-center lg:hidden"
        title="Đóng menu"
        @click="closeMobile"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      <!-- Desktop collapse toggle — hidden on mobile -->
      <button
        class="toggle-btn shrink-0 w-7 h-7 rounded-lg items-center justify-center hidden lg:flex"
        :title="collapsed ? 'Mở rộng' : 'Thu gọn'"
        @click="toggle"
      >
        <svg
          class="w-4 h-4 transition-transform duration-250"
          :class="collapsed ? 'rotate-180' : ''"
          fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
    </div>

    <!-- ── Navigation ──────────────────────────────────────────────────────── -->
    <nav class="flex-1 overflow-y-auto py-2 scrollbar-thin">
      <!-- Empty state: user không có persona / không có nav item -->
      <div v-if="!hasNav && !collapsed" class="empty-nav px-4 py-6 text-center">
        <p class="text-[12px] leading-relaxed">
          Chưa có chức năng nào được phân quyền.<br>
          Liên hệ quản trị viên nếu cần truy cập.
        </p>
      </div>

      <!-- Expanded: grouped + collapsible (Core Doc §7.bis) -->
      <template v-if="!collapsed && hasNav">
        <div v-for="group in navGroups" :key="group.title + group.code" class="nav-group">
          <div class="nav-group-header w-full flex items-center justify-between">
            <button
              type="button"
              class="nav-group-toggle flex-1 flex items-center justify-between min-w-0"
              :aria-expanded="groupOpen(group)"
              :title="groupOpen(group) ? 'Thu gọn nhóm' : 'Mở rộng nhóm'"
              @click="toggleGroup(group)"
            >
              <span class="nav-group-label truncate">{{ group.title }}</span>
              <svg
                class="nav-group-chevron w-3.5 h-3.5 shrink-0 transition-transform duration-200"
                :class="groupOpen(group) ? '' : '-rotate-90'"
                fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <!-- D7: ghim nhóm → lên đầu + luôn expand -->
            <button
              type="button"
              class="nav-group-pin shrink-0"
              :class="isGroupPinned(group.title) ? 'pinned' : ''"
              :aria-label="isGroupPinned(group.title) ? 'Bỏ ghim nhóm' : 'Ghim nhóm'"
              :title="isGroupPinned(group.title) ? 'Bỏ ghim nhóm' : 'Ghim nhóm lên đầu'"
              @click="togglePinGroup(group, $event)"
            >
              <svg fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24" class="w-3 h-3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 5l14 14M9 4h6l-1 5 3 3v2H7v-2l3-3-1-5z" />
              </svg>
            </button>
          </div>
          <div v-show="groupOpen(group)">
            <button
              v-for="item in group.items"
              :key="item.path"
              class="nav-item w-full flex items-center gap-3"
              :class="isActive(item.path) ? 'active' : ''"
              @click="router.push(item.path)"
            >
              <span class="nav-icon shrink-0 w-5 flex items-center justify-center"
                    v-html="ICONS[item.icon] || ICONS.grid" />
              <span class="truncate text-left leading-snug">{{ item.label }}</span>
            </button>
          </div>
        </div>
      </template>

      <!-- Collapsed: icon-only (flat, deduped) -->
      <template v-if="collapsed && hasNav">
        <div class="px-2 space-y-0.5">
          <button
            v-for="item in navItems"
            :key="item.path"
            class="collapsed-item relative w-full flex items-center justify-center py-2.5 rounded-lg group/tip transition-all duration-150"
            :class="isActive(item.path) ? 'active' : ''"
            :title="item.label"
            @click="router.push(item.path)"
          >
            <span class="w-[18px] h-[18px] flex items-center justify-center"
                  v-html="ICONS[item.icon] || ICONS.grid" />
            <span class="tooltip">{{ item.label }}</span>
          </button>
        </div>
      </template>
    </nav>

    <!-- ── Footer ──────────────────────────────────────────────────────────── -->
    <div class="sidebar-footer px-3 py-2.5 shrink-0">
      <p v-if="!collapsed" class="text-[10.5px] font-medium text-center side-foot-text">AssetCore v0.0.3</p>
    </div>
  </aside>
</template>

<style scoped>
/* ── Shell — design tokens từ docs/fe/assets/style.css (mục Sidebar) ─────────── */
/* Navy sidebar #13314f, text #cdd9e8, header #1F4E79, active #0E6FFF. */
.sidebar-root {
  background: #13314f;
  border-right: 1px solid rgba(0,0,0,0.18);
  box-shadow: 2px 0 8px rgba(15,23,42,0.18);
  color: #cdd9e8;
}

/* Mobile: sidebar is always full-width drawer (collapse state ignored) */
@media (max-width: 1023px) {
  .sidebar-root { width: 16rem !important; }
  .sidebar-root:not(.translate-x-0) { pointer-events: none; }
}
.sidebar-header {
  border-bottom: 1px solid rgba(0,0,0,0.18);
  background: #1F4E79; /* --color-navy-header */
}
.logo-badge {
  background: linear-gradient(135deg, #0E6FFF 0%, #16A34A 100%);
  box-shadow: 0 1px 2px rgba(15,23,42,0.25);
}
.logo-button { background: transparent; border: none; cursor: pointer; }
.logo-button:hover { background: rgba(255,255,255,0.08); }
.logo-button:hover .logo-badge { transform: scale(1.04); }
.logo-button .logo-badge { transition: transform 0.2s ease; }

.toggle-btn {
  color: #9fc3e8;
  transition: color 0.15s, background 0.15s;
  background: transparent; border: none; cursor: pointer;
}
.toggle-btn:hover { color: #fff; background: rgba(255,255,255,0.12); }

.sidebar-footer { border-top: 1px solid rgba(255,255,255,0.08); }
.side-foot-text { color: #6f8aa8; }

/* ── Group label + collapsible header ──────────────────────────────────────── */
.nav-group { padding-bottom: 2px; }
.nav-group-header {
  padding: 12px 16px 4px;
  color: #6f8aa8;
}
.nav-group-toggle {
  background: transparent; border: none; cursor: pointer;
  color: inherit;
  transition: color 0.15s;
  padding: 0;
}
.nav-group-toggle:hover { color: #9fc3e8; }
.nav-group-toggle:hover .nav-group-chevron { color: #9fc3e8; }
.nav-group-pin {
  background: transparent; border: none; cursor: pointer;
  color: #4a6280;
  margin-left: 6px;
  opacity: 0;
  transition: color 0.15s, opacity 0.15s;
}
.nav-group-header:hover .nav-group-pin { opacity: 1; }
.nav-group-pin:hover { color: #9fc3e8; }
.nav-group-pin.pinned { color: #0E6FFF; opacity: 1; }
.nav-group-label {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: inherit;
}
.nav-group-chevron { color: #5b7491; }

/* ── Nav items (token: padding 10px 16px, gap 12px, font 14px) ───────────────── */
.nav-item {
  padding: 10px 16px;
  font-size: 14px;
  color: #cdd9e8;
  background: transparent;
  border: none; border-left: 3px solid transparent;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.nav-item:hover { background: rgba(255,255,255,0.06); color: #fff; }
.nav-item.active {
  background: rgba(14,111,255,0.22);
  border-left-color: #0E6FFF;
  color: #fff;
  font-weight: 600;
}
.nav-icon { font-size: 15px; opacity: 0.85; transition: opacity 0.15s; }
.nav-item:hover .nav-icon,
.nav-item.active .nav-icon { opacity: 1; }

/* ── Collapsed items ───────────────────────────────────────────────────────── */
.collapsed-item {
  color: #cdd9e8;
  background: transparent; border: none; cursor: pointer;
}
.collapsed-item:hover { background: rgba(255,255,255,0.06); color: #fff; }
.collapsed-item.active {
  background: rgba(14,111,255,0.22);
  color: #fff;
  box-shadow: inset 3px 0 0 #0E6FFF;
}

/* ── Tooltip ───────────────────────────────────────────────────────────────── */
.tooltip {
  position: absolute;
  left: calc(100% + 10px); top: 50%;
  transform: translateY(-50%) translateX(-4px);
  padding: 5px 10px;
  background: #1F4E79;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  font-size: 12.5px; font-weight: 500;
  color: #fff;
  white-space: nowrap;
  pointer-events: none; opacity: 0;
  transition: opacity 0.15s ease, transform 0.15s ease;
  box-shadow: 0 4px 16px rgba(15,23,42,0.4);
  z-index: 100;
}
.group\/tip:hover .tooltip {
  opacity: 1;
  transform: translateY(-50%) translateX(0);
}

/* ── Empty state ───────────────────────────────────────────────────────────── */
.empty-nav { color: #6f8aa8; }

/* ── Animations ────────────────────────────────────────────────────────────── */
.fade-x-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-x-leave-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.fade-x-enter-from   { opacity: 0; transform: translateX(-8px); }
.fade-x-leave-to     { opacity: 0; transform: translateX(-8px); }

/* scrollbar */
.scrollbar-thin::-webkit-scrollbar       { width: 4px; }
.scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
.scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
.scrollbar-thin::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
