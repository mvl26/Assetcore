// Copyright (c) 2026, AssetCore Team
// Module Hub catalog — đầy đủ 17 module IMM-01..IMM-17 theo BA
// Ho_so_kien_truc_IMMIS.md §A.4 + 2 group cross-cutting (master, system).
//
// Quy tắc: mỗi IMM-XX = đúng 1 tile trong launcher. Sub-function nằm trong
// sidebar của module đó (xem AppSidebar.MODULE_NAV).
//
// Module chưa có FE+BE: disabled=true, không router.push.
// Module có một phần (đợt 3 chưa hoàn thiện): badge "Một phần", link tạm route gần nhất.

import {
  Roles,
  ROLES_ADMIN_USER,
  ROLES_ADMIN_ONLY,
  type RoleName,
} from '@/constants/roles'

export interface ModuleCard {
  id: string
  code?: string                 // IMM-xx | undefined cho master/system items
  label: string
  description: string
  icon: string
  to: string                    // primary route
  roles: readonly RoleName[]    // [] = all authenticated; ngược lại lọc
  badge?: string                // "Đợt 1" | "Đợt 2" | "Đợt 3" | "Một phần"
  disabled?: boolean            // true = chưa có FE+BE, hiển thị nhưng không click
}

export interface ModuleGroup {
  id: string
  title: string
  subtitle: string
  accent: 'blue' | 'emerald' | 'amber' | 'rose' | 'slate' | 'indigo'
  cards: ModuleCard[]
}

// ── Role bundles ────────────────────────────────────────────────────────────
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

// ── 17 module + master + system ────────────────────────────────────────────
export const MODULE_GROUPS: readonly ModuleGroup[] = [
  // ════════════════════ KHỐI 1 — Hoạch định & Mua sắm ════════════════════
  // 3 module: IMM-01, 02, 03
  {
    id: 'planning',
    title: 'Khối 1 — Hoạch định & Mua sắm',
    subtitle: 'Nhu cầu · Kỹ thuật · NCC · Quyết định mua',
    accent: 'indigo',
    cards: [
      {
        id: 'imm01', code: 'IMM-01',
        label: 'Đánh giá nhu cầu & Dự toán',
        description: 'Tiếp nhận nhu cầu, chấm điểm ưu tiên, lập dự toán, dự báo nhu cầu',
        icon: 'inbox',
        to: '/needs-requests',
        roles: PROC_ROLES,
        badge: 'Đợt 2',
      },
      {
        id: 'imm02', code: 'IMM-02',
        label: 'Thông số kỹ thuật & Phân tích thị trường',
        description: 'Hồ sơ kỹ thuật, benchmark, tương thích hạ tầng, lock-in risk',
        icon: 'template',
        to: '/tech-specs',
        roles: PROC_ROLES,
        badge: 'Đợt 2',
      },
      {
        id: 'imm03', code: 'IMM-03',
        label: 'Đánh giá NCC & Quyết định mua sắm',
        description: 'Vendor evaluation, AVL, scorecard, quyết định mua, đơn hàng',
        icon: 'chart',
        to: '/vendor-evaluations',
        roles: PROC_ROLES,
        badge: 'Đợt 2',
      },
    ],
  },

  // ════════════════════ KHỐI 2 — Triển khai & Lắp đặt ════════════════════
  // 3 module: IMM-04, 05, 06
  {
    id: 'deployment',
    title: 'Khối 2 — Triển khai & Lắp đặt',
    subtitle: 'Tiếp nhận · Định danh · Hồ sơ · Đào tạo',
    accent: 'emerald',
    cards: [
      {
        id: 'imm04', code: 'IMM-04',
        label: 'Lắp đặt, Định danh & Kiểm tra ban đầu',
        description: 'Tiếp nhận, baseline, initial inspection, release gate',
        icon: 'clipboard',
        to: '/commissioning',
        roles: TECH_ROLES.concat([Roles.DEPT_HEAD, Roles.QA]),
        badge: 'Đợt 1',
      },
      {
        id: 'imm05', code: 'IMM-05',
        label: 'Đăng ký, Cấp phép & Hồ sơ',
        description: 'Document repository, kiểm soát hiệu lực, audit trail tài liệu',
        icon: 'folder',
        to: '/documents',
        roles: DOC_ROLES,
        badge: 'Đợt 1',
      },
      {
        id: 'imm06', code: 'IMM-06',
        label: 'Đào tạo người dùng',
        description: 'Lịch đào tạo, tài liệu hướng dẫn, competency, chứng nhận',
        icon: 'users',
        to: '/imm06/programs',
        roles: TECH_ROLES.concat([Roles.CLINICAL, Roles.DEPT_HEAD]),
        badge: 'Đợt 2',
      },
    ],
  },

  // ════════════════════ KHỐI 3 — Vận hành & Bảo trì ════════════════════
  // 9 module: IMM-07, 08, 09, 10, 11, 12, 15, 16, 17
  {
    id: 'operations',
    title: 'Khối 3 — Vận hành & Bảo trì',
    subtitle: 'KPI · PM · CM · Hậu kiểm · Hiệu chuẩn · CAPA · Tồn kho · Tuân thủ · Dự đoán',
    accent: 'blue',
    cards: [
      {
        id: 'imm07', code: 'IMM-07',
        label: 'Theo dõi hiệu suất',
        description: 'KPI/KRI vận hành: availability, utilization, downtime, MTBF/MTTR',
        icon: 'chart',
        to: '/dashboard',
        roles: TECH_ROLES.concat([Roles.QA, Roles.DEPT_HEAD]),
        badge: 'Một phần',
      },
      {
        id: 'imm08', code: 'IMM-08',
        label: 'Bảo trì định kỳ (PM)',
        description: 'Lập lịch · Work Order · Bảng kiểm · Compliance dashboard',
        icon: 'wrench',
        to: '/pm/dashboard',
        roles: TECH_ROLES,
        badge: 'Đợt 1',
      },
      {
        id: 'imm09', code: 'IMM-09',
        label: 'Sửa chữa, Phụ tùng & Cập nhật phần mềm',
        description: 'Corrective WO, truy nguyên phụ tùng, firmware/software change',
        icon: 'tool',
        to: '/cm/dashboard',
        roles: TECH_ROLES.concat([Roles.VENDOR_ENGINEER]),
        badge: 'Đợt 1',
      },
      {
        id: 'imm10', code: 'IMM-10',
        label: 'Hậu kiểm & Tuân thủ',
        description: 'Post-market surveillance, recall/FSCA, action tracker',
        icon: 'alert',
        to: '/capas',
        roles: QA_ROLES,
        badge: 'Một phần',
      },
      {
        id: 'imm11', code: 'IMM-11',
        label: 'Hiệu năng & Hiệu chuẩn',
        description: 'Inspection, calibration, certificate, fail/out-of-tolerance',
        icon: 'gauge',
        to: '/calibration/dashboard',
        roles: TECH_ROLES,
        badge: 'Đợt 1',
      },
      {
        id: 'imm12', code: 'IMM-12',
        label: 'Bảo trì khắc phục',
        description: 'Triage sự cố, escalation, RCA, SLA corrective',
        icon: 'shield',
        to: '/incidents/dashboard',
        roles: [...TECH_ROLES, Roles.CLINICAL, Roles.QA, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY],
        badge: 'Đợt 1',
      },
      {
        id: 'imm15', code: 'IMM-15',
        label: 'Theo dõi tồn kho phụ tùng',
        description: 'Spare parts, kiểm kê, truy nguyên cấp phát, dự báo demand',
        icon: 'box',
        to: '/inventory',
        roles: STOCK_ROLES,
        badge: 'Đợt 2',
      },
      {
        id: 'imm16', code: 'IMM-16',
        label: 'Theo dõi tuân thủ',
        description: 'Compliance monitoring, audit, NC/CAPA, scorecard',
        icon: 'log',
        to: '/compliance/findings',
        roles: QA_ROLES,
        badge: 'Đợt 2',
      },
      {
        id: 'imm17', code: 'IMM-17',
        label: 'Phân tích dự đoán',
        description: 'Predictive analytics, model governance, what-if, replacement signal',
        icon: 'trending',
        to: '/predictive',
        roles: QA_ROLES.concat([Roles.OPS_MANAGER]),
        badge: 'Đợt 3',
        disabled: true,
      },
    ],
  },

  // ════════════════════ KHỐI 4 — Kết thúc vòng đời ════════════════════
  // 2 module: IMM-13, 14
  {
    id: 'eol',
    title: 'Khối 4 — Kết thúc vòng đời',
    subtitle: 'Điều chuyển · Khấu hao · Giải nhiệm',
    accent: 'amber',
    cards: [
      {
        id: 'imm13', code: 'IMM-13',
        label: 'Ngừng sử dụng & Điều chuyển',
        description: 'Chuyển trạng thái, điều chuyển nội viện, replacement review',
        icon: 'transfer',
        to: '/asset-transfers',
        roles: [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY, Roles.WORKSHOP],
        badge: 'Đợt 3',
      },
      {
        id: 'imm14', code: 'IMM-14',
        label: 'Giải nhiệm thiết bị',
        description: 'Đóng vòng đời, khấu hao, đối soát kế toán, closure record',
        icon: 'trending',
        to: '/depreciation',
        roles: [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD],
        badge: 'Một phần',
      },
    ],
  },

  // ════════════════════ Master / Tài sản & Đối tác ════════════════════
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

  // ════════════════════ Hệ thống ════════════════════
  {
    id: 'system',
    title: 'Hệ thống',
    subtitle: 'Cấu hình hệ thống · Người dùng · Tổng quan',
    accent: 'rose',
    cards: [
      {
        id: 'dashboard',
        label: 'Dashboard tổng quan',
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
      {
        id: 'approvals',
        label: 'Phê duyệt chờ',
        description: 'Workflow chờ phê duyệt của bạn',
        icon: 'inbox',
        to: '/approvals/pending',
        roles: [],
      },
    ],
  },
] as const
