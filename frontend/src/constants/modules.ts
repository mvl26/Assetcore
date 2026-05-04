// Copyright (c) 2026, AssetCore Team
// Module Hub catalog — 4 khối kiến trúc (Ho_so_kien_truc_IMMIS.md §2)
// + nhóm Master Data và Hệ thống.
//
// Mỗi ModuleCard:
//   - id, code (IMM-xx), label, description
//   - icon (key trong ICONS map của hub)
//   - to: route đích (dùng router.push)
//   - roles: nếu rỗng → mọi user authenticated; nếu có → cần ≥ 1 role trong list
//
// Role-based visibility: ModuleHubView lọc theo auth.hasAnyRole(card.roles).

import {
  Roles,
  ROLES_ADMIN_USER,
  ROLES_ADMIN_ONLY,
  type RoleName,
} from '@/constants/roles'

export interface ModuleCard {
  id: string
  code?: string                 // IMM-xx hoặc null cho master
  label: string
  description: string
  icon: string                  // key icon
  to: string                    // primary route
  roles: readonly RoleName[]    // [] = all authenticated; ngược lại lọc
  badge?: string                // optional: "Mới", "Đợt 1", "Đợt 2"
}

export interface ModuleGroup {
  id: string
  title: string
  subtitle: string
  accent: 'blue' | 'emerald' | 'amber' | 'rose' | 'slate' | 'indigo'
  cards: ModuleCard[]
}

// ── Role bundles dùng riêng cho hub ─────────────────────────────────────────
const PROC_ROLES: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.STOREKEEPER, Roles.DOC_OFFICER,
] as const
const TECH_ROLES: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.WORKSHOP, Roles.BIOMED, Roles.TECHNICIAN,
] as const
const QA_ROLES: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.QA, Roles.AUDITOR, Roles.DEPT_HEAD,
] as const
const STOCK_ROLES: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.STOREKEEPER, Roles.WORKSHOP, Roles.BIOMED, Roles.TECHNICIAN,
] as const
const DOC_ROLES: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.DOC_OFFICER, Roles.QA, Roles.OPS_MANAGER, Roles.DEPT_HEAD,
] as const

// ── Module catalog ──────────────────────────────────────────────────────────
export const MODULE_GROUPS: readonly ModuleGroup[] = [
  // ──────────────── KHỐI 1 — Hoạch định & Mua sắm ────────────────
  {
    id: 'planning',
    title: 'Khối 1 — Hoạch định & Mua sắm',
    subtitle: 'Nhu cầu · Kỹ thuật · NCC · Quyết định mua',
    accent: 'indigo',
    cards: [
      {
        id: 'imm01',
        code: 'IMM-01',
        label: 'Nhu cầu & Dự toán',
        description: 'Đề xuất, chấm điểm ưu tiên, lập dự toán mua sắm',
        icon: 'inbox',
        to: '/needs-requests',
        roles: PROC_ROLES,
        badge: 'Đợt 2',
      },
      {
        id: 'procurement-plan',
        code: 'IMM-01',
        label: 'Kế hoạch mua sắm',
        description: 'Tổng hợp kế hoạch năm, theo dõi giải ngân',
        icon: 'list',
        to: '/procurement-plans',
        roles: PROC_ROLES,
      },
      {
        id: 'imm02',
        code: 'IMM-02',
        label: 'Hồ sơ kỹ thuật',
        description: 'Yêu cầu kỹ thuật, benchmark, tương thích hạ tầng',
        icon: 'template',
        to: '/tech-specs',
        roles: PROC_ROLES,
      },
      {
        id: 'imm03-eval',
        code: 'IMM-03',
        label: 'Đánh giá NCC',
        description: 'Vendor evaluation, scorecard',
        icon: 'chart',
        to: '/vendor-evaluations',
        roles: PROC_ROLES,
      },
      {
        id: 'imm03-avl',
        code: 'IMM-03',
        label: 'Danh mục NCC duyệt (AVL)',
        description: 'Approved vendor list, hậu kiểm năng lực',
        icon: 'shield',
        to: '/approved-vendors',
        roles: PROC_ROLES,
      },
      {
        id: 'imm03-decision',
        code: 'IMM-03',
        label: 'Quyết định mua sắm',
        description: 'Hồ sơ quyết định lựa chọn nhà cung cấp',
        icon: 'contract',
        to: '/procurement-decisions',
        roles: [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DOC_OFFICER],
      },
      {
        id: 'purchases',
        label: 'Đơn hàng mua',
        description: 'Theo dõi đơn mua thiết bị / vật tư',
        icon: 'cart',
        to: '/purchases',
        roles: STOCK_ROLES,
      },
    ],
  },

  // ──────────────── KHỐI 2 — Triển khai & Lắp đặt ────────────────
  {
    id: 'deployment',
    title: 'Khối 2 — Triển khai & Lắp đặt',
    subtitle: 'Tiếp nhận · Định danh · Hồ sơ · Đào tạo',
    accent: 'emerald',
    cards: [
      {
        id: 'imm04',
        code: 'IMM-04',
        label: 'Tiếp nhận & Nghiệm thu',
        description: 'Lắp đặt, định danh, baseline, release gate',
        icon: 'clipboard',
        to: '/commissioning',
        roles: TECH_ROLES.concat([Roles.DEPT_HEAD, Roles.QA]),
        badge: 'Đợt 1',
      },
      {
        id: 'imm05',
        code: 'IMM-05',
        label: 'Hồ sơ & Cấp phép',
        description: 'Document repository, kiểm soát hiệu lực',
        icon: 'folder',
        to: '/documents',
        roles: DOC_ROLES,
        badge: 'Đợt 1',
      },
      {
        id: 'imm05-req',
        code: 'IMM-05',
        label: 'Yêu cầu hồ sơ',
        description: 'Yêu cầu bổ sung tài liệu thiết bị',
        icon: 'inbox',
        to: '/documents/requests',
        roles: DOC_ROLES.concat([Roles.WORKSHOP, Roles.BIOMED, Roles.TECHNICIAN, Roles.CLINICAL]),
      },
    ],
  },

  // ──────────────── KHỐI 3 — Vận hành & Bảo trì ────────────────
  {
    id: 'operations',
    title: 'Khối 3 — Vận hành & Bảo trì',
    subtitle: 'PM · Sửa chữa · Hiệu chuẩn · Sự cố · Tồn kho · CAPA',
    accent: 'blue',
    cards: [
      {
        id: 'imm08',
        code: 'IMM-08',
        label: 'Bảo trì định kỳ (PM)',
        description: 'Lập lịch · Work Order · Bảng kiểm · Compliance',
        icon: 'wrench',
        to: '/pm/dashboard',
        roles: TECH_ROLES,
        badge: 'Đợt 1',
      },
      {
        id: 'imm09',
        code: 'IMM-09',
        label: 'Sửa chữa (CM)',
        description: 'Corrective WO, phụ tùng, firmware change',
        icon: 'tool',
        to: '/cm/dashboard',
        roles: TECH_ROLES.concat([Roles.VENDOR_ENGINEER]),
        badge: 'Đợt 1',
      },
      {
        id: 'imm11',
        code: 'IMM-11',
        label: 'Hiệu chuẩn',
        description: 'Inspection, calibration, certificate',
        icon: 'gauge',
        to: '/calibration',
        roles: TECH_ROLES,
        badge: 'Đợt 1',
      },
      {
        id: 'imm12-incident',
        code: 'IMM-12',
        label: 'Sự cố & Triage',
        description: 'Báo sự cố, escalation, SLA corrective',
        icon: 'alert',
        to: '/incidents/dashboard',
        roles: [...TECH_ROLES, Roles.CLINICAL, Roles.QA, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY],
      },
      {
        id: 'imm12-rca',
        code: 'IMM-12',
        label: 'RCA & CAPA',
        description: 'Phân tích nguyên nhân, hành động khắc phục',
        icon: 'shield',
        to: '/capas',
        roles: QA_ROLES.concat([Roles.WORKSHOP, Roles.BIOMED]),
      },
      {
        id: 'imm15',
        code: 'IMM-15',
        label: 'Tồn kho phụ tùng',
        description: 'Spare parts, kiểm kê, dự báo cấp phát',
        icon: 'box',
        to: '/inventory',
        roles: STOCK_ROLES,
      },
      {
        id: 'imm16-audit',
        code: 'IMM-16',
        label: 'Nhật ký kiểm toán',
        description: 'Audit trail, truy vết toàn hệ thống',
        icon: 'log',
        to: '/audit-trail',
        roles: QA_ROLES,
      },
    ],
  },

  // ──────────────── KHỐI 4 — Kết thúc vòng đời ────────────────
  {
    id: 'eol',
    title: 'Khối 4 — Kết thúc vòng đời',
    subtitle: 'Điều chuyển · Khấu hao · Thanh lý',
    accent: 'amber',
    cards: [
      {
        id: 'imm13',
        code: 'IMM-13',
        label: 'Điều chuyển thiết bị',
        description: 'Chuyển giao nội viện, đổi trạng thái',
        icon: 'transfer',
        to: '/asset-transfers',
        roles: [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY, Roles.WORKSHOP],
      },
      {
        id: 'imm14',
        code: 'IMM-14',
        label: 'Khấu hao & Thanh lý',
        description: 'Đóng vòng đời, đối soát kế toán',
        icon: 'trending',
        to: '/depreciation',
        roles: [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD],
      },
    ],
  },

  // ──────────────── Master / Tài sản & Đối tác ────────────────
  {
    id: 'master',
    title: 'Tài sản & Đối tác',
    subtitle: 'Master data dùng xuyên suốt vòng đời',
    accent: 'slate',
    cards: [
      {
        id: 'assets',
        label: 'Danh sách thiết bị',
        description: 'Asset registry — toàn bộ trang thiết bị',
        icon: 'device',
        to: '/assets',
        roles: [],
      },
      {
        id: 'qr-scan',
        label: 'Quét mã QR',
        description: 'Tra cứu nhanh thiết bị qua QR',
        icon: 'qr',
        to: '/qr-scan',
        roles: [],
      },
      {
        id: 'device-models',
        label: 'Model thiết bị',
        description: 'Cấu hình, mã GMDN, manufacturer',
        icon: 'template',
        to: '/device-models',
        roles: [],
      },
      {
        id: 'suppliers',
        label: 'Nhà cung cấp',
        description: 'Danh sách NCC, thông tin liên hệ',
        icon: 'building',
        to: '/suppliers',
        roles: [],
      },
      {
        id: 'service-contracts',
        label: 'Hợp đồng dịch vụ',
        description: 'Hợp đồng bảo trì, hiệu chuẩn',
        icon: 'contract',
        to: '/service-contracts',
        roles: [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DOC_OFFICER, Roles.WORKSHOP, Roles.QA],
      },
      {
        id: 'sla',
        label: 'Chính sách SLA',
        description: 'Cấu hình SLA cho corrective / PM / calibration',
        icon: 'clock',
        to: '/sla-policies',
        roles: [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.QA],
      },
    ],
  },

  // ──────────────── Hệ thống ────────────────
  {
    id: 'system',
    title: 'Hệ thống',
    subtitle: 'Cấu hình hệ thống · Người dùng · Dashboard',
    accent: 'rose',
    cards: [
      {
        id: 'dashboard',
        label: 'Dashboard điều hành',
        description: 'KPI tổng quan, repair active, PM upcoming',
        icon: 'chart',
        to: '/dashboard',
        roles: [],
      },
      {
        id: 'users',
        label: 'Quản lý người dùng',
        description: 'Tạo / phân quyền / Role Profile',
        icon: 'users',
        to: '/user-profiles',
        roles: ROLES_ADMIN_USER,
      },
      {
        id: 'reference',
        label: 'Dữ liệu tham chiếu',
        description: 'Khoa/Phòng, vị trí, UOM, danh mục',
        icon: 'database',
        to: '/reference-data',
        roles: ROLES_ADMIN_ONLY,
      },
    ],
  },
] as const
