// Copyright (c) 2026, AssetCore Team
// Role constants — đồng bộ với assetcore/services/shared/constants.py::Roles
// và assetcore/fixtures/role.json. Dùng cho router guards, v-permission, auth.

export const Roles = {
  SYS_ADMIN:      'IMM System Admin',
  OPS_MANAGER:    'IMM Operations Manager',
  DEPT_HEAD:      'IMM Department Head',
  DEPT_DEPUTY:    'IMM Deputy Department Head',
  WORKSHOP:       'IMM Workshop Lead',
  QA:             'IMM QA Officer',
  BIOMED:         'IMM Biomed Technician',
  TECHNICIAN:     'IMM Technician',
  DOC_OFFICER:    'IMM Document Officer',
  STOREKEEPER:    'IMM Storekeeper',
  CLINICAL:       'IMM Clinical User',
  AUDITOR:        'IMM Auditor',
  TECH_REVIEWER:  'IMM Technical Reviewer',
  FINANCE_OFFICER:'IMM Finance Officer',
} as const

export type RoleName = (typeof Roles)[keyof typeof Roles]

export const ALL_IMM_ROLES: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY,
  Roles.WORKSHOP, Roles.QA, Roles.BIOMED, Roles.TECHNICIAN,
  Roles.DOC_OFFICER, Roles.STOREKEEPER, Roles.CLINICAL,
  Roles.AUDITOR, Roles.TECH_REVIEWER, Roles.FINANCE_OFFICER,
] as const

// Planning-specific role groups (Wave 2 — IMM-01/02/03)
export const ROLES_PLANNING_VIEW: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD,
  Roles.TECH_REVIEWER, Roles.FINANCE_OFFICER, Roles.STOREKEEPER,
] as const

export const ROLES_PLANNING_MANAGE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER,
] as const

export const ROLES_PLANNING_REVIEW: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.TECH_REVIEWER,
] as const

export const ROLES_PLANNING_FINANCE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.FINANCE_OFFICER, Roles.DEPT_HEAD,
] as const

// Role-group policies (đồng bộ với BE Roles.CAN_*)
export const ROLES_CREATE_WO: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.WORKSHOP, Roles.BIOMED, Roles.TECHNICIAN,
] as const

export const ROLES_APPROVE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD, Roles.QA,
] as const

export const ROLES_APPROVE_DEP: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY, Roles.QA,
] as const

export const ROLES_CANCEL: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD,
] as const

export const ROLES_MANAGE_DOCS: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.DOC_OFFICER, Roles.QA,
] as const

export const ROLES_MANAGE_STOCK: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.STOREKEEPER, Roles.OPS_MANAGER,
] as const

export const ROLES_ADMIN_USER: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER,
] as const

export const ROLES_ADMIN_ONLY: readonly RoleName[] = [Roles.SYS_ADMIN] as const

// Legacy alias — giữ để không break các view hiện có
export const ROLES_CREATE = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY,
  Roles.WORKSHOP, Roles.QA, Roles.BIOMED, Roles.TECHNICIAN,
] as const

// Role metadata types
export interface RoleMeta {
  name: string
  label: string
  description: string
  group: string
}

export const ROLE_GROUPS = ['Governance', 'Department', 'Engineering', 'Support'] as const
export type RoleGroup = (typeof ROLE_GROUPS)[number]

export const ROLE_GROUP_LABEL: Record<RoleGroup, string> = {
  Governance:  'Quản trị & Duyệt',
  Department:  'Khoa / Phòng',
  Engineering: 'Kỹ thuật',
  Support:     'Hỗ trợ / Hậu cần',
}
