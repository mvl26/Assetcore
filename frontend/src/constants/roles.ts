// Copyright (c) 2026, AssetCore Team
// Catalog 30 role (RBAC module-based) — CHỈ để hiển thị/gán ở trang admin.
// KHÔNG dùng cho logic gate (logic dùng useCapabilities().can(...)).
//
// Mọi `ROLES_*` legacy group được ánh xạ sang capability tương đương trong
// `composables/useCapabilities.ts`. Các const dưới giữ lại làm tham chiếu
// catalog + để các view chưa refactor xong vẫn import không vỡ build.
//
// Đồng bộ: assetcore/services/shared/constants.py::Roles, fixtures/role.json.

export interface RoleInfo {
  name: string
  label: string
  description: string
  group: string  // 'System' | one of DOMAINS
  rank: number
}

export const SYSTEM_ROLES = [
  'AssetCore Super Admin',
  'AssetCore System User',
  'AssetCore Auditor',
  'Vendor Engineer',
] as const

// ─── Frappe admin-role SSoT (admin-bypass) ──────────────────────────────────
// Tiêu chí "full platform access" dùng CHUNG cho:
//   - route-guard (router/index.ts → resolveRouteAccess rule #1 admin bypass)
//   - button/affordance-gate (stores/auth.ts::can → admin → can()=true mọi cap)
// PHẢI là MỘT nguồn duy nhất để route-gate và button-gate KHÔNG lệch nhau
// (split-brain: vào được trang nhưng mất nút). KHÔNG lặp literal mảng role ở 2 nơi.
// SUPERUSER_ROLES (constants/personas.ts) re-export const này để nav cũng đồng nhất.
// Đồng bộ với BE: services/shared/rbac.py (System Manager/Administrator/Super Admin
// có DocPerm bao trùm). roles.ts là leaf-module (0 import) → an toàn để auth.ts dùng.
export const FRAPPE_ADMIN_ROLES: readonly string[] = [
  'System Manager',
  'Administrator',
  'AssetCore Super Admin',
] as const

/** True nếu danh sách role chứa ít nhất 1 admin-role (full platform access). */
export function isFrappeAdminRole(roles: readonly string[]): boolean {
  return roles.some((r) => FRAPPE_ADMIN_ROLES.includes(r))
}

export const DOMAINS = [
  'Data', 'Needs', 'Spec', 'Procurement', 'Commissioning',
  'Document', 'Training', 'PM', 'Repair', 'Calibration',
  'Corrective', 'Inventory', 'Compliance',
] as const

const DOMAIN_LABEL: Record<string, string> = {
  Data: 'Dữ liệu nền',
  Needs: 'Nhu cầu & Dự toán',
  Spec: 'Thông số kỹ thuật',
  Procurement: 'NCC & Mua sắm',
  Commissioning: 'Lắp đặt & Nghiệm thu',
  Document: 'Hồ sơ',
  Training: 'Đào tạo',
  PM: 'Bảo trì định kỳ',
  Repair: 'Sửa chữa',
  Calibration: 'Hiệu chuẩn',
  Corrective: 'Bảo trì khắc phục',
  Inventory: 'Tồn kho phụ tùng',
  Compliance: 'Tuân thủ / Hệ thống quản lý chất lượng',
}

/** Nhãn tiếng Việt cho mã phân hệ (group). Fallback: trả mã gốc nếu chưa map. */
export function domainLabel(d: string): string {
  return DOMAIN_LABEL[d] ?? d
}

const SYSTEM_INFO: RoleInfo[] = [
  { name: 'AssetCore Super Admin', label: 'Quản trị hệ thống', group: 'System', rank: 100,
    description: 'Toàn quyền + bao trùm Frappe System Manager' },
  { name: 'AssetCore System User', label: 'Người dùng hệ thống', group: 'System', rank: 0,
    description: 'Vai trò nền: đăng nhập, bảng điều khiển, đọc lõi dùng chung' },
  { name: 'AssetCore Auditor', label: 'Kiểm toán viên', group: 'System', rank: 5,
    description: 'Chỉ đọc toàn bộ + nhật ký truy vết' },
  { name: 'Vendor Engineer', label: 'KTV nhà cung cấp', group: 'System', rank: 5,
    description: 'Bên thứ ba, cô lập theo Lệnh công việc/Tài sản' },
]

const DOMAIN_INFO: RoleInfo[] = DOMAINS.flatMap((d) => ([
  { name: `${d} Manager`, label: `${DOMAIN_LABEL[d]} — Quản lý`, group: d, rank: 50,
    description: 'Toàn quyền + duyệt/hủy quy trình' },
  { name: `${d} User`, label: `${DOMAIN_LABEL[d]} — Người dùng`, group: d, rank: 10,
    description: 'đọc/ghi/tạo, thao tác thường' },
]))

export const ROLE_CATALOG: RoleInfo[] = [...SYSTEM_INFO, ...DOMAIN_INFO]

// ─── Legacy compatibility (deprecated) ──────────────────────────────────────
// Các name dưới ánh xạ persona cũ sang role mới gần nhất. Mục đích: các view
// chưa refactor xong vẫn build được. KHÔNG dùng cho logic mới — dùng
// `useCapabilities().can('<cap>')` thay vì so role name.
export const Roles = {
  SYS_ADMIN:        'AssetCore Super Admin',
  OPS_MANAGER:      'Commissioning Manager',
  DEPT_HEAD:        'Commissioning Manager',
  DEPT_DEPUTY:      'Commissioning Manager',
  WORKSHOP:         'PM Manager',
  QA:               'Compliance Manager',
  BIOMED:           'PM User',
  TECHNICIAN:       'PM User',
  DOC_OFFICER:      'Document Manager',
  STOREKEEPER:      'Inventory Manager',
  CLINICAL:         'Corrective User',
  AUDITOR:          'AssetCore Auditor',
  VENDOR_ENGINEER:  'Vendor Engineer',
  PLANNING:         'Needs Manager',
  FINANCE:          'Needs Manager',
  HTM_ENGINEER:     'Spec Manager',
  PROCUREMENT:      'Procurement Manager',
  RISK:             'Spec Manager',
  BOARD_APPROVER:   'Procurement Manager',
  TRAINING_OFFICER: 'Training Manager',
} as const

/**
 * Base role BẮT BUỘC của mọi user AssetCore (định danh "user AssetCore" + đăng
 * nhập SPA + đọc shared-core). Mirror BE `role_profile_catalog.BASE_ROLE`. BE
 * luôn re-inject role này khi sửa role → UI hiển thị KHOÁ (không gỡ được).
 */
export const BASE_ROLE = 'AssetCore System User'

// RoleName chap nhan moi role-name dang string (legacy + new module roles).
// Khong narrow lai persona — code nen gate bang capability (useCapabilities).
export type RoleName = string

export const ALL_IMM_ROLES: readonly string[] = ROLE_CATALOG.map((r) => r.name)

// Deprecated ROLES_* groups — empty arrays, mọi view nên chuyển sang capability.
// Giữ export để không vỡ import; các template dùng `hasAnyRole(ROLES_X)` sẽ tự
// về false (đúng nghĩa: không gate theo role-name — gate theo capability).
const _empty: readonly string[] = []
export const ROLES_CREATE_WO = _empty
export const ROLES_APPROVE = _empty
export const ROLES_APPROVE_DEP = _empty
export const ROLES_CANCEL = _empty
export const ROLES_MANAGE_DOCS = _empty
export const ROLES_MANAGE_STOCK = _empty
export const ROLES_ADMIN_USER = _empty
export const ROLES_ADMIN_ONLY = _empty
export const ROLES_PM_MANAGE = _empty
export const ROLES_PM_EXECUTE = _empty
export const ROLES_CM_MANAGE = _empty
export const ROLES_CM_EXECUTE = _empty
export const ROLES_CAL_MANAGE = _empty
export const ROLES_CAL_EXECUTE = _empty
export const ROLES_INCIDENT_REPORT = _empty
export const ROLES_INCIDENT_ACK = _empty
export const ROLES_RCA_OWNER = _empty
export const ROLES_CAPA_CLOSE = _empty
export const ROLES_DOC_APPROVE = _empty
export const ROLES_AUDIT_READ = _empty
export const ROLES_COMPLIANCE_MANAGE = _empty
export const ROLES_STOCK_MANAGE = _empty
export const ROLES_PLANNING = _empty
export const ROLES_PROCUREMENT = _empty
export const ROLES_TRAINING_MANAGE = _empty
export const ROLES_TRAINING_CONDUCT = _empty
export const ROLES_TRAINING_SIGNOFF = _empty
export const ROLES_PM_VIEW = _empty
export const ROLES_CM_VIEW = _empty
export const ROLES_CAL_VIEW = _empty
export const ROLES_INCIDENT_VIEW = _empty
export const ROLES_SPARE_VIEW = _empty
export const ROLES_TRAINING_VIEW = _empty
export const ROLES_COMPLIANCE_VIEW = _empty
export const ROLES_CREATE = _empty

// Role metadata types (legacy)
export interface RoleMeta {
  name: string
  label: string
  description: string
  group: string
}

// Legacy + new groups — RoleGroup la string thuoc tinh, khong narrow.
export const ROLE_GROUPS = [
  'System', ...DOMAINS,
  // Legacy aliases for UI/forms still in use:
  'Governance', 'Department', 'Engineering', 'Support',
] as const
export type RoleGroup = string

export const ROLE_GROUP_LABEL: Record<string, string> = {
  System: 'Hệ thống',
  ...DOMAIN_LABEL,
  Governance: 'Quản trị & Duyệt',
  Department: 'Khoa / Phòng',
  Engineering: 'Kỹ thuật',
  Support: 'Hỗ trợ / Hậu cần',
}
