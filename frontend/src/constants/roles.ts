// Copyright (c) 2026, AssetCore Team
// Role constants — đồng bộ với assetcore/services/shared/constants.py::Roles
// và assetcore/fixtures/role.json. Dùng cho router guards, v-permission, auth.

export const Roles = {
  SYS_ADMIN:   'IMM System Admin',
  OPS_MANAGER: 'IMM Operations Manager',
  DEPT_HEAD:   'IMM Department Head',
  DEPT_DEPUTY: 'IMM Deputy Department Head',
  WORKSHOP:    'IMM Workshop Lead',
  QA:          'IMM QA Officer',
  BIOMED:      'IMM Biomed Technician',
  TECHNICIAN:  'IMM Technician',
  DOC_OFFICER: 'IMM Document Officer',
  STOREKEEPER: 'IMM Storekeeper',
  CLINICAL:    'IMM Clinical User',
  AUDITOR:     'IMM Auditor',
  VENDOR_ENGINEER: 'Vendor Engineer',
} as const

export type RoleName = (typeof Roles)[keyof typeof Roles]

export const ALL_IMM_ROLES: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY,
  Roles.WORKSHOP, Roles.QA, Roles.BIOMED, Roles.TECHNICIAN,
  Roles.DOC_OFFICER, Roles.STOREKEEPER, Roles.CLINICAL, Roles.AUDITOR,
  Roles.VENDOR_ENGINEER,
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

// ─── Module-specific role groups (per docs/imm-xx audit) ─────────────────
// IMM-08 PM: Workshop Lead schedules + assigns; tech submits result
export const ROLES_PM_MANAGE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.WORKSHOP,
] as const
export const ROLES_PM_EXECUTE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.WORKSHOP, Roles.BIOMED, Roles.TECHNICIAN,
] as const

// IMM-09 CM: Workshop Lead creates WO; SysAdmin auto-creates from PM
export const ROLES_CM_MANAGE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.WORKSHOP,
] as const
export const ROLES_CM_EXECUTE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.WORKSHOP, Roles.BIOMED, Roles.TECHNICIAN,
] as const

// IMM-11 Calibration: Workshop Lead schedules; tech executes; QA reviews CAPA
export const ROLES_CAL_MANAGE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.WORKSHOP,
] as const
export const ROLES_CAL_EXECUTE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.WORKSHOP, Roles.TECHNICIAN, Roles.BIOMED,
] as const

// IMM-12 Incident: Clinical user reports; Workshop Lead/Dept Head acknowledge
export const ROLES_INCIDENT_REPORT: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.WORKSHOP,
  Roles.BIOMED, Roles.TECHNICIAN, Roles.CLINICAL,
] as const
export const ROLES_INCIDENT_ACK: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.WORKSHOP, Roles.DEPT_HEAD,
] as const

// RCA + CAPA: Workshop Lead + QA Officer drive
export const ROLES_RCA_OWNER: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.WORKSHOP, Roles.QA,
] as const
export const ROLES_CAPA_CLOSE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.QA,
] as const

// IMM-05 Doc approve gate
export const ROLES_DOC_APPROVE: readonly RoleName[] = [
  Roles.SYS_ADMIN, Roles.QA,
] as const

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
