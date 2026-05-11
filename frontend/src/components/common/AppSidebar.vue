<script setup lang="ts">
// AppSidebar — module-scoped navigation.
// Mỗi route có meta.moduleId (IMM-XX | 'master' | 'system'). Sidebar đọc moduleId
// hiện tại và chỉ hiện nav-items thuộc module đó. Click logo → /launcher (home).
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSidebar } from '@/composables/useSidebar'

const router = useRouter()
const route  = useRoute()
const { collapsed, toggle, sidebarClass } = useSidebar()

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

// ─── Module catalog ───────────────────────────────────────────────────────────
// Mỗi entry = một sidebar context. moduleId được set ở route.meta.moduleId.
interface NavItem  { label: string; path: string; icon: string }
interface ModuleNav { code: string; title: string; icon: string; items: NavItem[] }

const MODULE_NAV: Record<string, ModuleNav> = {
  imm01: {
    code: 'IMM-01', title: 'Nhu cầu & Dự toán', icon: 'inbox',
    items: [
      { label: 'Đề xuất nhu cầu',  path: '/needs-requests',    icon: 'inbox' },
      { label: 'Kế hoạch mua sắm', path: '/procurement-plans', icon: 'list'  },
    ],
  },
  imm02: {
    code: 'IMM-02', title: 'Thông số kỹ thuật', icon: 'template',
    items: [
      { label: 'Hồ sơ kỹ thuật', path: '/tech-specs', icon: 'template' },
    ],
  },
  imm03: {
    code: 'IMM-03', title: 'Đánh giá NCC & Mua sắm', icon: 'chart',
    items: [
      { label: 'Đánh giá NCC',          path: '/vendor-evaluations',    icon: 'chart'    },
      { label: 'Danh mục NCC duyệt',    path: '/approved-vendors',      icon: 'shield'   },
      { label: 'Quyết định mua sắm',    path: '/procurement-decisions', icon: 'contract' },
      { label: 'Đơn hàng mua',          path: '/purchases',             icon: 'cart'     },
    ],
  },
  imm04: {
    code: 'IMM-04', title: 'Lắp đặt & Nghiệm thu', icon: 'clipboard',
    items: [
      { label: 'Tiếp nhận thiết bị', path: '/commissioning', icon: 'clipboard' },
    ],
  },
  imm05: {
    code: 'IMM-05', title: 'Đăng ký & Hồ sơ', icon: 'folder',
    items: [
      { label: 'Kho tài liệu',  path: '/documents',          icon: 'folder' },
      { label: 'Yêu cầu hồ sơ', path: '/documents/requests', icon: 'inbox'  },
    ],
  },
  imm06: {
    code: 'IMM-06', title: 'Đào tạo người dùng', icon: 'users',
    items: [
      { label: 'Chương trình đào tạo', path: '/imm06/programs',     icon: 'list'     },
      { label: 'Buổi đào tạo',         path: '/imm06/sessions',     icon: 'calendar' },
      { label: 'Năng lực',             path: '/imm06/competencies', icon: 'shield'   },
    ],
  },
  imm08: {
    code: 'IMM-08', title: 'Bảo trì định kỳ (PM)', icon: 'wrench',
    items: [
      { label: 'Tổng quan bảo trì', path: '/pm/dashboard',   icon: 'chart'    },
      { label: 'Lệnh bảo trì',      path: '/pm/work-orders', icon: 'wrench'   },
      { label: 'Lịch bảo trì',      path: '/pm/calendar',    icon: 'calendar' },
      { label: 'Kế hoạch bảo trì',  path: '/pm/schedules',   icon: 'list'     },
      { label: 'Mẫu bảng kiểm',     path: '/pm/templates',   icon: 'template' },
    ],
  },
  imm09: {
    code: 'IMM-09', title: 'Sửa chữa (CM)', icon: 'tool',
    items: [
      { label: 'Tổng quan sửa chữa',     path: '/cm/dashboard',   icon: 'chart'    },
      { label: 'Lệnh sửa chữa',          path: '/cm/work-orders', icon: 'tool'     },
      { label: 'Yêu cầu cập nhật firmware', path: '/cm/firmware', icon: 'code'     },
      { label: 'Thời gian sửa chữa TB',  path: '/cm/mttr',        icon: 'trending' },
    ],
  },
  imm11: {
    code: 'IMM-11', title: 'Hiệu năng & Hiệu chuẩn', icon: 'gauge',
    items: [
      { label: 'Tổng quan hiệu chuẩn', path: '/calibration/dashboard', icon: 'chart'    },
      { label: 'Phiếu hiệu chuẩn',     path: '/calibration',           icon: 'gauge'    },
      { label: 'Lịch hiệu chuẩn',      path: '/calibration/schedules', icon: 'calendar' },
    ],
  },
  imm12: {
    code: 'IMM-12', title: 'Sự cố & RCA/CAPA', icon: 'alert',
    items: [
      { label: 'Dashboard sự cố', path: '/incidents/dashboard', icon: 'chart'  },
      { label: 'Danh sách sự cố', path: '/incidents/list',      icon: 'alert'  },
      { label: 'CAPA',            path: '/capas',               icon: 'shield' },
    ],
  },
  imm13: {
    code: 'IMM-13', title: 'Điều chuyển thiết bị', icon: 'transfer',
    items: [
      { label: 'Phiếu điều chuyển', path: '/asset-transfers', icon: 'transfer' },
    ],
  },
  imm14: {
    code: 'IMM-14', title: 'Giải nhiệm thiết bị', icon: 'trending',
    items: [
      { label: 'Khấu hao & Giải nhiệm', path: '/depreciation', icon: 'trending' },
    ],
  },
  imm15: {
    code: 'IMM-15', title: 'Tồn kho phụ tùng', icon: 'box',
    items: [
      { label: 'Tổng quan kho', path: '/inventory',       icon: 'chart'     },
      { label: 'Tồn kho',       path: '/stock',           icon: 'box'       },
      { label: 'Phụ tùng',      path: '/spare-parts',     icon: 'cog'       },
      { label: 'Phiếu kho',     path: '/stock-movements', icon: 'arrows'    },
      { label: 'Kho hàng',      path: '/warehouses',      icon: 'warehouse' },
      { label: 'Đơn vị tính',   path: '/inventory/uom',   icon: 'uom'       },
    ],
  },
  imm16: {
    code: 'IMM-16', title: 'Theo dõi tuân thủ', icon: 'log',
    items: [
      { label: 'Nhật ký kiểm toán', path: '/audit-trail', icon: 'log'    },
      { label: 'CAPA',              path: '/capas',       icon: 'shield' },
    ],
  },
  master: {
    code: '', title: 'Tài sản & Đối tác', icon: 'device',
    items: [
      { label: 'Danh sách thiết bị', path: '/assets',          icon: 'device'   },
      { label: 'Quét mã QR',         path: '/qr-scan',         icon: 'qr'       },
      { label: 'Model thiết bị',     path: '/device-models',   icon: 'template' },
      { label: 'Nhà cung cấp',       path: '/suppliers',       icon: 'building' },
      { label: 'Hợp đồng dịch vụ',   path: '/service-contracts', icon: 'contract' },
      { label: 'Chính sách SLA',     path: '/sla-policies',    icon: 'clock'    },
    ],
  },
  system: {
    code: '', title: 'Hệ thống', icon: 'cog',
    items: [
      { label: 'Dashboard tổng quan', path: '/dashboard',         icon: 'chart'    },
      { label: 'Người dùng',          path: '/user-profiles',     icon: 'users'    },
      { label: 'Dữ liệu tham chiếu',  path: '/reference-data',    icon: 'database' },
      { label: 'Phê duyệt chờ',       path: '/approvals/pending', icon: 'inbox'    },
    ],
  },
}

// ─── Resolve current module from route meta ───────────────────────────────────
const currentModuleId = computed<string | null>(() =>
  (route.meta.moduleId as string | undefined) ?? null,
)
const currentModule = computed<ModuleNav | null>(() => {
  const id = currentModuleId.value
  return id ? (MODULE_NAV[id] ?? null) : null
})
const navItems = computed<NavItem[]>(() => currentModule.value?.items ?? [])

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

// ─── Logo → launcher (home) ───────────────────────────────────────────────────
function goLauncher() { router.push('/launcher') }
</script>

<template>
  <aside
    :class="['fixed left-0 top-0 h-full z-40 flex flex-col transition-all duration-250 overflow-hidden', sidebarClass]"
    class="sidebar-root"
  >
    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <div class="sidebar-header flex items-center h-16 px-3 shrink-0">
      <button
        type="button"
        class="logo-button flex items-center gap-3 flex-1 min-w-0 rounded-lg p-1 -m-1 transition-colors"
        title="Về Trang chủ Launcher"
        @click="goLauncher"
      >
        <div class="logo-badge shrink-0 w-9 h-9 rounded-xl flex items-center justify-center text-white">
          <span v-html="ICONS.home" />
        </div>
        <Transition name="fade-x">
          <div v-if="!collapsed" class="min-w-0 text-left">
            <p v-if="currentModule" class="font-bold text-[14px] text-white tracking-tight leading-none truncate">
              <span v-if="currentModule.code" class="text-blue-400">{{ currentModule.code }} · </span>{{ currentModule.title }}
            </p>
            <p v-else class="font-bold text-[15px] text-white tracking-tight leading-none">AssetCore</p>
            <p class="text-[11px] mt-1 text-slate-400 font-medium">Về Trang chủ</p>
          </div>
        </Transition>
      </button>
      <button
        class="toggle-btn shrink-0 w-7 h-7 rounded-lg flex items-center justify-center"
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

    <!-- ── Module section label ───────────────────────────────────────────── -->
    <Transition name="fade-x">
      <div v-if="!collapsed && currentModule" class="module-section px-4 pt-3 pb-1">
        <span class="module-section-label">Chức năng module</span>
      </div>
    </Transition>

    <!-- ── Navigation ──────────────────────────────────────────────────────── -->
    <nav class="flex-1 overflow-y-auto py-2 scrollbar-thin">
      <!-- Empty state: route ngoài map module -->
      <Transition name="fade-x">
        <div v-if="!currentModule && !collapsed" class="empty-nav px-4 py-6 text-center">
          <p class="text-[12px] text-slate-500 leading-relaxed">
            Trang này không thuộc module nào.<br>
            Mở Launcher để chọn module.
          </p>
          <button class="open-launcher-btn mt-3" @click="goLauncher">
            Mở Launcher
          </button>
        </div>
      </Transition>

      <!-- Expanded -->
      <template v-if="!collapsed && currentModule">
        <div class="px-3 space-y-0.5">
          <button
            v-for="(item, idx) in navItems"
            :key="item.path"
            class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150"
            :class="isActive(item.path) ? 'active' : ''"
            :style="{ animationDelay: `${idx * 35}ms` }"
            @click="router.push(item.path)"
          >
            <span class="nav-icon shrink-0 w-[18px] h-[18px] flex items-center justify-center"
                  v-html="ICONS[item.icon] || ICONS.grid" />
            <span class="truncate text-left font-medium leading-snug">{{ item.label }}</span>
          </button>
        </div>
      </template>

      <!-- Collapsed: icon-only -->
      <template v-if="collapsed && currentModule">
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

    <!-- ── Back-to-launcher button ─────────────────────────────────────────── -->
    <div class="sidebar-footer px-3 py-3 shrink-0">
      <button
        class="back-launcher w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all"
        :class="collapsed ? 'justify-center' : ''"
        :title="collapsed ? 'Trang chủ Launcher' : ''"
        @click="goLauncher"
      >
        <span class="w-[18px] h-[18px] flex items-center justify-center" v-html="ICONS.home" />
        <Transition name="fade-x">
          <span v-if="!collapsed" class="truncate text-left text-[13px] font-medium">Trang chủ Launcher</span>
        </Transition>
      </button>
      <Transition name="fade-x">
        <p v-if="!collapsed" class="text-[10.5px] text-slate-500 font-medium text-center mt-2">AssetCore v1.0</p>
      </Transition>
    </div>
  </aside>
</template>

<style scoped>
/* ── Shell ─────────────────────────────────────────────────────────────────── */
.sidebar-root {
  background: #0f1623;
  border-right: 1px solid rgba(255,255,255,0.06);
  box-shadow: 4px 0 24px rgba(0,0,0,0.4);
}
.sidebar-header {
  border-bottom: 1px solid rgba(255,255,255,0.07);
  background: rgba(255,255,255,0.02);
}
.logo-badge {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  box-shadow: 0 0 16px rgba(59,130,246,0.35);
}
.logo-button { background: transparent; border: none; cursor: pointer; }
.logo-button:hover { background: rgba(255,255,255,0.05); }
.logo-button:hover .logo-badge { box-shadow: 0 0 24px rgba(59,130,246,0.55); transform: scale(1.04); }
.logo-button .logo-badge { transition: transform 0.2s ease, box-shadow 0.2s ease; }

.toggle-btn {
  color: rgba(255,255,255,0.6);
  transition: color 0.15s, background 0.15s;
  background: transparent; border: none; cursor: pointer;
}
.toggle-btn:hover { color: #fff; background: rgba(255,255,255,0.12); }

.sidebar-footer {
  border-top: 1px solid rgba(255,255,255,0.06);
}

/* ── Module section ────────────────────────────────────────────────────────── */
.module-section-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(148,163,184,0.7);
}

/* ── Nav items ─────────────────────────────────────────────────────────────── */
.nav-item {
  color: rgba(255,255,255,0.78);
  background: transparent; border: none; cursor: pointer;
  animation: itemSlideIn 0.22s ease both;
}
.nav-item:hover {
  background: rgba(255,255,255,0.1);
  color: #fff;
  transform: translateX(2px);
}
.nav-item.active {
  background: rgba(59,130,246,0.25);
  color: #dbeafe;
  box-shadow: inset 3px 0 0 #3b82f6;
}
.nav-item.active:hover { background: rgba(59,130,246,0.22); transform: none; }
.nav-icon { opacity: 0.6; transition: opacity 0.15s, transform 0.15s; }
.nav-item:hover .nav-icon { opacity: 1; transform: scale(1.1); }
.nav-item.active .nav-icon { opacity: 1; }

/* ── Collapsed items ───────────────────────────────────────────────────────── */
.collapsed-item {
  color: rgba(255,255,255,0.7);
  background: transparent; border: none; cursor: pointer;
}
.collapsed-item:hover { background: rgba(255,255,255,0.12); color: #fff; }
.collapsed-item.active {
  background: rgba(59,130,246,0.28);
  color: #dbeafe;
  box-shadow: inset 3px 0 0 #3b82f6;
}

/* ── Tooltip ───────────────────────────────────────────────────────────────── */
.tooltip {
  position: absolute;
  left: calc(100% + 10px); top: 50%;
  transform: translateY(-50%) translateX(-4px);
  padding: 5px 10px;
  background: #1e2a3a;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  font-size: 12.5px; font-weight: 500;
  color: rgba(255,255,255,0.88);
  white-space: nowrap;
  pointer-events: none; opacity: 0;
  transition: opacity 0.15s ease, transform 0.15s ease;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  z-index: 100;
}
.group\/tip:hover .tooltip {
  opacity: 1;
  transform: translateY(-50%) translateX(0);
}

/* ── Empty state ───────────────────────────────────────────────────────────── */
.empty-nav { color: rgba(148,163,184,0.7); }
.open-launcher-btn {
  font-size: 12px; font-weight: 600;
  color: #dbeafe;
  background: rgba(59,130,246,0.2);
  border: 1px solid rgba(59,130,246,0.3);
  padding: 5px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}
.open-launcher-btn:hover { background: rgba(59,130,246,0.3); }

/* ── Back-launcher button ──────────────────────────────────────────────────── */
.back-launcher {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.85);
  cursor: pointer;
}
.back-launcher:hover { background: rgba(59,130,246,0.18); border-color: rgba(59,130,246,0.4); color: #dbeafe; }

/* ── Animations ────────────────────────────────────────────────────────────── */
@keyframes itemSlideIn {
  from { opacity: 0; transform: translateX(-8px); }
  to   { opacity: 1; transform: translateX(0); }
}
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
