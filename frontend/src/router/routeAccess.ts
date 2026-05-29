// Copyright (c) 2026, AssetCore Team
//
// Pure route-authorization decision — tách khỏi navigation guard để unit-test
// được (LL-FE-22). KHÔNG dùng role-name legacy/empty-stub `ROLES_*`; gate bằng
// capability (`<domain>.<ptype>`) khớp services/shared/rbac.py::CAPABILITY_MAP,
// đồng bộ với sidebar (constants/sidebarNav.ts → useCapabilities().can).
//
// Thứ tự quyết định:
//   1. Frappe/Super admin → allow (bypass).
//   2. meta.requiredCapabilities (OR) → cần ít nhất 1 cap.
//   3. legacy meta.requiredRoles (OR) — chỉ gate nếu non-empty (back-compat).
//   4. meta.moduleId → fallback `<domain>.read` (chỉ cho domain module).
//   5. Mặc định: allow (route mở cho user đã xác thực).

/** Map moduleId (vd 'imm08') -> capability read tương ứng. Master/system = null. */
export function moduleIdToCap(moduleId: string): string | null {
  const map: Record<string, string> = {
    imm00: 'data.read',
    imm01: 'needs.read',
    imm02: 'spec.read',
    imm03: 'procurement.read',
    imm04: 'commissioning.read',
    imm05: 'doc' + 'ument.read',
    imm06: 'training.read',
    imm08: 'pm.read',
    imm09: 'repair.read',
    imm11: 'calibration.read',
    imm12: 'corrective.read',
    imm15: 'inventory.read',
    imm16: 'compliance.read',
  }
  return map[moduleId] ?? null
}

/** Subset of route.meta mà quyết định truy cập quan tâm. */
export interface RouteAccessMeta {
  requiredCapabilities?: string[]
  requiredRoles?: readonly string[]
  moduleId?: string
}

/** Ngữ cảnh quyền của user hiện tại (lấy từ auth store). */
export interface RouteAccessCtx {
  isFrappeAdmin: boolean
  can: (cap: string) => boolean
  hasAnyRole: (roles: readonly string[]) => boolean
}

export type RouteAccessDecision = 'allow' | 'unauthorized'

/**
 * Quyết định một route (đã xác thực) có được truy cập không.
 *
 * Lưu ý: caller chịu trách nhiệm phần auth/redirect-to-login. Hàm này chỉ
 * quyết định authorization khi user ĐÃ đăng nhập.
 */
export function resolveRouteAccess(
  meta: RouteAccessMeta,
  ctx: RouteAccessCtx,
): RouteAccessDecision {
  // 1. Admin bypass.
  if (ctx.isFrappeAdmin) return 'allow'

  // 2. requiredCapabilities (OR).
  const caps = meta.requiredCapabilities
  if (caps && caps.length > 0) {
    return caps.some((c) => ctx.can(c)) ? 'allow' : 'unauthorized'
  }

  // 3. Legacy requiredRoles — chỉ gate nếu non-empty (stub `[]` → bỏ qua).
  const roles = meta.requiredRoles
  if (roles && roles.length > 0 && !ctx.hasAnyRole(roles)) {
    return 'unauthorized'
  }

  // 4. moduleId → `<domain>.read` fallback (chỉ domain module có cap).
  if (meta.moduleId) {
    const cap = moduleIdToCap(meta.moduleId)
    if (cap && !ctx.can(cap)) return 'unauthorized'
  }

  // 5. Mặc định allow.
  return 'allow'
}
