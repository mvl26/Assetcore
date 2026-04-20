// Copyright (c) 2026, AssetCore Team
// Role constants — đồng bộ với assetcore/services/shared/constants.py::Roles.
// Dùng cho router guards, v-permission directive, auth store, component logic.

export const Roles = {
  SYS_ADMIN: 'IMM System Admin',
  QA: 'IMM QA Officer',
  DEPT_HEAD: 'IMM Department Head',
  OPS_MANAGER: 'IMM Operations Manager',
  WORKSHOP: 'IMM Workshop Lead',
  TECHNICIAN: 'IMM Technician',
  DOC_OFFICER: 'IMM Document Officer',
  STOREKEEPER: 'IMM Storekeeper',
  CLINICAL: 'IMM Clinical User',
} as const

export type RoleName = (typeof Roles)[keyof typeof Roles]

export const ALL_IMM_ROLES: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.QA, Roles.DEPT_HEAD, Roles.OPS_MANAGER,
  Roles.WORKSHOP, Roles.TECHNICIAN, Roles.DOC_OFFICER,
  Roles.STOREKEEPER, Roles.CLINICAL,
] as const

// Role-group policies (đồng bộ với BE Roles.CAN_*)
export const ROLES_CREATE_WO: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.WORKSHOP, Roles.TECHNICIAN,
] as const

export const ROLES_APPROVE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.QA, Roles.DEPT_HEAD, Roles.OPS_MANAGER,
] as const

export const ROLES_MANAGE_DOCS: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.DOC_OFFICER, Roles.QA,
] as const

export const ROLES_ADMIN_USER: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER,
] as const

export const ROLES_ADMIN_ONLY: readonly RoleName[] = [Roles.SYS_ADMIN] as const

// Legacy aliases để tránh break các view hiện có
export const ROLES_CREATE = [
  Roles.SYS_ADMIN, Roles.QA, Roles.DEPT_HEAD, Roles.OPS_MANAGER,
  Roles.WORKSHOP, Roles.TECHNICIAN,
] as const
