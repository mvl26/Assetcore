// Copyright (c) 2026, AssetCore Team
//
// Sidebar navigation catalog + group builder.
// Single Source of Truth: docs/architecture/FE_Persona_Navigation.md §2.1 + §6.
//
// Mental model:
//   persona.modules (ordered) ──tra──> MODULE_NAV ──render──> grouped sidebar nav
//   Mỗi NavItem lọc bằng CAPABILITY (item.cap → useCapabilities().can(...)).
//   KHÔNG dùng role-name / ROLES_* empty-stub (LL-FE-12/22). Group rỗng → ẩn.
//
// Capability strings khớp EXACT services/shared/rbac.py::CAPABILITY_MAP:
//   <domain>.<ptype> với ptype ∈ {read,write,create,delete,submit,cancel}
//   domain ∈ {data,needs,spec,procurement,commissioning,document,training,
//             pm,repair,calibration,corrective,inventory,compliance}
//   special: pm.reschedule, incident.acknowledge, incident.close, cal.send_lab,
//            doc.approve, capa.close, data.admin, audit.read

import type { Persona } from './personas'

/** Capability predicate — `useCapabilities().can`. */
export type CanFn = (cap: string | readonly string[]) => boolean

// §7.septies.3 — OR-cap "finance" cho mục Khấu hao (Asset Finance Hub).
// PHẢI khớp `FINANCE_READ_CAPS` trong router/index.ts (sidebar-ẩn = route-chặn).
// `data.read` lộ cho mọi user (AssetCore System User read IMM Device Model) → doc/
// training thấy khấu hao. Gate bằng OR-cap chỉ chủ sở hữu tài sản/tài chính có.
export const FINANCE_READ_CAPS = [
  'data.write', 'needs.read', 'procurement.read', 'pm.read', 'calibration.read',
] as const

export interface NavItem {
  label: string
  path: string
  icon: string
  /**
   * Capability cần để thấy item. Bỏ trống = mở cho mọi user đã xác thực
   * (dashboard, QR-scan, list read-level mặc định mở). String[] = OR.
   */
  cap?: string | readonly string[]
}

export interface ModuleNav {
  code: string
  title: string
  icon: string
  items: NavItem[]
}

/** Một nhóm sidebar đã render (sau filter) — module-scoped. */
export interface SidebarGroup {
  code: string
  title: string
  icon: string
  items: NavItem[]
}

// ─── Module catalog ─────────────────────────────────────────────────────────
// Mỗi entry = một group sidebar (module hoặc cross-cutting master/system).
export const MODULE_NAV: Record<string, ModuleNav> = {
  imm01: {
    code: 'IMM-01', title: 'Nhu cầu & Dự toán', icon: 'inbox',
    items: [
      { label: 'Đề xuất nhu cầu',  path: '/needs-requests',    icon: 'inbox', cap: 'needs.read' },
      { label: 'Kế hoạch mua sắm', path: '/procurement-plans', icon: 'list',  cap: 'needs.read' },
    ],
  },
  imm02: {
    code: 'IMM-02', title: 'Thông số kỹ thuật', icon: 'template',
    items: [
      { label: 'Hồ sơ kỹ thuật', path: '/tech-specs', icon: 'template', cap: 'spec.read' },
    ],
  },
  imm03: {
    code: 'IMM-03', title: 'Đánh giá NCC & Mua sắm', icon: 'chart',
    items: [
      { label: 'Hồ sơ Nhà cung cấp',      path: '/vendor-profiles',       icon: 'building', cap: 'procurement.read' },
      { label: 'Đánh giá Nhà cung cấp',   path: '/vendor-evaluations',    icon: 'chart',    cap: 'procurement.read' },
      { label: 'Danh mục NCC được duyệt', path: '/approved-vendors',      icon: 'shield',   cap: 'procurement.read' },
      { label: 'Quyết định mua sắm',      path: '/procurement-decisions', icon: 'contract', cap: 'procurement.read' },
      { label: 'Đơn hàng mua',            path: '/purchases',             icon: 'cart',     cap: 'procurement.read' },
    ],
  },
  imm04: {
    code: 'IMM-04', title: 'Lắp đặt & Nghiệm thu', icon: 'clipboard',
    items: [
      { label: 'Tiếp nhận thiết bị', path: '/commissioning', icon: 'clipboard', cap: 'commissioning.read' },
    ],
  },
  imm05: {
    code: 'IMM-05', title: 'Đăng ký & Hồ sơ', icon: 'folder',
    items: [
      { label: 'Kho tài liệu',  path: '/documents',          icon: 'folder', cap: 'document.read' },
      { label: 'Yêu cầu hồ sơ', path: '/documents/requests', icon: 'inbox',  cap: 'doc.approve' },
    ],
  },
  imm06: {
    code: 'IMM-06', title: 'Đào tạo người dùng', icon: 'users',
    items: [
      { label: 'Tổng quan đào tạo',    path: '/imm06/dashboard',    icon: 'chart',    cap: 'training.read' },
      { label: 'Chương trình đào tạo', path: '/imm06/programs',     icon: 'list',     cap: 'training.read' },
      { label: 'Buổi đào tạo',         path: '/imm06/sessions',     icon: 'calendar', cap: 'training.read' },
      { label: 'Năng lực',             path: '/imm06/competencies', icon: 'shield',   cap: 'training.read' },
    ],
  },
  imm08: {
    code: 'IMM-08', title: 'Bảo trì định kỳ', icon: 'wrench',
    items: [
      { label: 'Tổng quan bảo trì', path: '/pm/dashboard',   icon: 'chart',    cap: 'pm.read' },
      { label: 'Lệnh bảo trì',      path: '/pm/work-orders', icon: 'wrench',   cap: 'pm.read' },
      { label: 'Lịch bảo trì',      path: '/pm/calendar',    icon: 'calendar', cap: 'pm.read' },
      { label: 'Kế hoạch bảo trì',  path: '/pm/schedules',   icon: 'list',     cap: 'pm.write' },
      { label: 'Mẫu bảng kiểm',     path: '/pm/templates',   icon: 'template', cap: 'pm.write' },
    ],
  },
  imm09: {
    code: 'IMM-09', title: 'Sửa chữa', icon: 'tool',
    items: [
      { label: 'Tổng quan sửa chữa',            path: '/cm/dashboard',   icon: 'chart',    cap: 'repair.read' },
      { label: 'Lệnh sửa chữa',                 path: '/cm/work-orders', icon: 'tool',     cap: 'repair.read' },
      { label: 'Yêu cầu cập nhật firmware',     path: '/cm/firmware',    icon: 'code',     cap: 'repair.write' },
      { label: 'Thời gian sửa chữa trung bình', path: '/cm/mttr',        icon: 'trending', cap: 'repair.read' },
    ],
  },
  imm11: {
    code: 'IMM-11', title: 'Hiệu năng & Hiệu chuẩn', icon: 'gauge',
    items: [
      { label: 'Tổng quan hiệu chuẩn', path: '/calibration/dashboard', icon: 'chart',    cap: 'calibration.read' },
      { label: 'Phiếu hiệu chuẩn',     path: '/calibration',           icon: 'gauge',    cap: 'calibration.read' },
      { label: 'Lịch hiệu chuẩn',      path: '/calibration/schedules', icon: 'calendar', cap: 'calibration.write' },
    ],
  },
  imm12: {
    code: 'IMM-12', title: 'Sự cố & Phân tích nguyên nhân gốc', icon: 'alert',
    items: [
      { label: 'Tổng quan sự cố', path: '/incidents/dashboard', icon: 'chart', cap: 'corrective.read' },
      { label: 'Danh sách sự cố', path: '/incidents/list',      icon: 'alert', cap: 'corrective.read' },
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
      { label: 'Biên bản giải nhiệm', path: '/decommissions', icon: 'trending', cap: 'decommission.read' },
    ],
  },
  imm15: {
    code: 'IMM-15', title: 'Tồn kho phụ tùng', icon: 'box',
    items: [
      { label: 'Tổng quan kho',        path: '/inventory',           icon: 'chart',     cap: 'inventory.read' },
      { label: 'Tồn kho',              path: '/stock',               icon: 'box',       cap: 'inventory.read' },
      { label: 'Phụ tùng',             path: '/spare-parts',         icon: 'cog',       cap: 'inventory.read' },
      { label: 'Phiếu kho',            path: '/stock-movements',     icon: 'arrows',    cap: 'inventory.read' },
      { label: 'Kiểm kê tồn kho',      path: '/inventory/cycle-counts', icon: 'clipboard', cap: 'inventory.read' },
      { label: 'Kho hàng',             path: '/warehouses',          icon: 'warehouse', cap: 'inventory.read' },
      { label: 'Đơn vị tính',          path: '/inventory/uom',       icon: 'uom',       cap: 'inventory.write' },
      { label: 'Dự báo phụ tùng',      path: '/inventory/forecasts', icon: 'chart',     cap: 'inventory.write' },
      { label: 'Watchlist',            path: '/inventory/watchlist', icon: 'shield',    cap: 'inventory.write' },
      { label: 'Điều chuyển thiết bị', path: '/asset-transfers',     icon: 'transfer' },
    ],
  },
  imm16: {
    code: 'IMM-16', title: 'Theo dõi tuân thủ', icon: 'log',
    items: [
      { label: 'Quy tắc tuân thủ',  path: '/compliance/rules',     icon: 'shield',   cap: 'compliance.write' },
      { label: 'Phát hiện',         path: '/compliance/findings',  icon: 'alert',    cap: 'compliance.read' },
      { label: 'Kiểm toán nội bộ',  path: '/compliance/audits',    icon: 'clipboard', cap: 'compliance.read' },
      { label: 'Bảng điểm',         path: '/compliance/scorecard', icon: 'chart',    cap: 'compliance.read' },
      { label: 'Soát xét quản lý',  path: '/compliance/mr',        icon: 'log',      cap: 'compliance.write' },
      { label: 'Bản đồ nhiệt',      path: '/compliance/heatmap',   icon: 'grid',     cap: 'compliance.read' },
      { label: 'Hành động khắc phục/phòng ngừa', path: '/capas',   icon: 'shield',   cap: 'capa.close' },
      { label: 'Nhật ký kiểm toán', path: '/audit-trail',          icon: 'database', cap: 'audit.read' },
    ],
  },
  master: {
    code: '', title: 'Tài sản & Đối tác', icon: 'device',
    items: [
      { label: 'Danh sách thiết bị', path: '/assets',            icon: 'device'   },
      { label: 'Khấu hao tài sản',   path: '/depreciation',      icon: 'trending', cap: FINANCE_READ_CAPS },
      { label: 'Quét mã QR',         path: '/qr-scan',           icon: 'qr'       },
      { label: 'Model thiết bị',     path: '/device-models',     icon: 'template', cap: 'data.read' },
      { label: 'Nhà cung cấp',       path: '/suppliers',         icon: 'building', cap: 'data.read' },
      { label: 'Hợp đồng dịch vụ',   path: '/service-contracts', icon: 'contract', cap: 'data.read' },
      { label: 'Chính sách cam kết mức dịch vụ', path: '/sla-policies', icon: 'clock', cap: 'data.admin' },
    ],
  },
  system: {
    code: '', title: 'Hệ thống', icon: 'cog',
    items: [
      { label: 'Dashboard tổng quan', path: '/dashboard',         icon: 'chart'    },
      { label: 'Người dùng',          path: '/user-profiles',     icon: 'users',    cap: 'data.admin' },
      { label: 'Dữ liệu tham chiếu',  path: '/reference-data',    icon: 'database', cap: 'data.admin' },
      { label: 'Phê duyệt chờ',       path: '/approvals/pending', icon: 'inbox'    },
    ],
  },
}

/**
 * itemVisible — chốt anti-leak.
 * - superuser → luôn thấy.
 * - item không có cap → mở cho mọi user đã xác thực.
 * - còn lại → cần `can(cap)` đúng.
 */
export function itemVisible(item: NavItem, can: CanFn, isSuperuser: boolean): boolean {
  if (isSuperuser) return true
  if (item.cap === undefined) return true
  return can(item.cap)
}

/**
 * buildSidebarGroups — Core Doc §2.1.
 * Lấy module theo thứ tự persona.modules → lọc item theo capability → dedupe
 * theo path (toàn cục) → bỏ group rỗng. Group rỗng KHÔNG render (sidebar gọn).
 */
export function buildSidebarGroups(
  persona: Persona,
  can: CanFn,
  isSuperuser: boolean,
): SidebarGroup[] {
  const seen = new Set<string>()
  const out: SidebarGroup[] = []

  for (const moduleId of persona.modules) {
    const mod = MODULE_NAV[moduleId]
    if (!mod) continue
    const items: NavItem[] = []
    for (const item of mod.items) {
      if (seen.has(item.path)) continue
      if (!itemVisible(item, can, isSuperuser)) continue
      seen.add(item.path)
      items.push(item)
    }
    if (items.length === 0) continue // ẩn group rỗng
    out.push({ code: mod.code, title: mod.title, icon: mod.icon, items })
  }
  return out
}

/**
 * buildSidebarGroupsForRoles — Core Doc §7.ter (Phase 1.2).
 * Nav derive từ ROLE THẬT: UNION module của MỌI persona role mở khoá.
 *
 * - `personas` = derivePersonas(roles) (đã sort rank desc). Duyệt theo thứ tự đó
 *   → persona quyền cao xuất hiện trước, module/group sắp theo rank.
 * - Dedupe path TOÀN CỤC: một path chỉ render 1 lần dù nhiều persona/module chứa.
 *   Group cũng dedupe theo code/title — module xuất hiện ở nhiều persona gộp làm 1.
 * - Lọc capability qua itemVisible (anti-leak giữ nguyên). Group rỗng → ẩn.
 * - personas rỗng → [] (không nav). KHÔNG còn khái niệm "persona đang chọn".
 */
export function buildSidebarGroupsForRoles(
  personas: readonly Persona[],
  can: CanFn,
  isSuperuser: boolean,
): SidebarGroup[] {
  const seenPath = new Set<string>()
  const seenGroup = new Set<string>()
  const out: SidebarGroup[] = []

  for (const persona of personas) {
    for (const moduleId of persona.modules) {
      const groupKey = `${moduleId}::${MODULE_NAV[moduleId]?.title ?? ''}`
      if (seenGroup.has(groupKey)) continue
      const mod = MODULE_NAV[moduleId]
      if (!mod) continue
      const items: NavItem[] = []
      for (const item of mod.items) {
        if (seenPath.has(item.path)) continue
        if (!itemVisible(item, can, isSuperuser)) continue
        seenPath.add(item.path)
        items.push(item)
      }
      if (items.length === 0) continue // ẩn group rỗng
      seenGroup.add(groupKey)
      out.push({ code: mod.code, title: mod.title, icon: mod.icon, items })
    }
  }
  return out
}
