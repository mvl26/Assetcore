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

// ─── Drill-down access (Core Doc §9.5 #9) ───────────────────────────────────
// Một KPI/segment chỉ được render CLICKABLE khi user thật sự vào được route đích.
// Nếu thiếu capability → render card TĨNH (không link), KHÔNG đẩy user về
// /unauthorized (bug opsmgr 2026-06-02: drill PM/CM/Sự cố rớt /unauthorized vì
// persona oversight không có quyền đọc doctype vận hành).
//
// Map prefix → moduleId: tập con CHỈ gồm route mà dashboard drill tới. SSOT đầy
// đủ là MODULE_RULES (router/index.ts); giữ tách ở đây để tránh circular-import
// (index.ts import mọi view). Khi thêm drill route mới phải đồng bộ cả 2 nơi.
const DRILL_MODULE_RULES: ReadonlyArray<[RegExp, string]> = [
  [/^\/pm/, 'imm08'],
  [/^\/cm/, 'imm09'],
  [/^\/calibration/, 'imm11'],
  [/^\/incidents/, 'imm12'],
  [/^\/rca/, 'imm12'],
  [/^\/capas/, 'imm16'],
  [/^\/compliance/, 'imm16'],
  [/^\/spare-parts/, 'imm15'],
  [/^\/inventory/, 'imm15'],
  [/^\/stock/, 'imm15'],
  [/^\/warehouses/, 'imm15'],
  [/^\/documents/, 'imm05'],
  [/^\/commissioning/, 'imm04'],
  // Master/system route (assets, depreciation, device-model…) → moduleId
  // không cần cap đặc thù (moduleIdToCap trả null) → luôn cho phép.
  [/^\/assets/, 'master'],
  [/^\/depreciation/, 'master'],
  [/^\/device-models/, 'master'],
  [/^\/suppliers/, 'master'],
  [/^\/service-contracts/, 'master'],
]

// Drill route gate bằng capability TRỰC TIẾP (không qua moduleId) — cho route mà
// cap đích KHÔNG khớp `<module>.read` (sửa drift §9.4.9). SSOT là route.meta
// trong router/index.ts; giữ tách ở đây tránh circular-import. Khi đổi
// requiredCapabilities của các route này phải đồng bộ cả hai nơi.
//   /audit-trail → audit.read (route.meta dùng audit.read, KHÔNG phải compliance.read)
//   /user-profiles, /admin/roles → data.admin (quản trị user/phân quyền)
const DRILL_CAP_RULES: ReadonlyArray<[RegExp, string]> = [
  [/^\/audit-trail/, 'audit.read'],
  [/^\/user-profiles/, 'data.admin'],
  [/^\/admin\/roles/, 'data.admin'],
]

// ─── Nút «Tạo …» điều hướng tới màn tạo (tab «Bản ghi liên quan») ────────────
// Backend biết quyền TẠO trên DocType (DocPerm/capability) nhưng KHÔNG biết route FE
// nào gác capability nào. Nút tạo mà route-guard đá ra `/unauthorized` ngay sau cú bấm
// là dạng "nút chết" tệ nhất (người dùng đã tin là làm được). Bảng dưới mirror
// `requiredCapabilities` của đúng các route `/…/new` trong `router/index.ts` — parity
// khoá bằng `connectionsCreateParity.test.ts`, cùng tinh thần `createButtonAffordance.test.ts`.
export const CREATE_ROUTE_CAP: Record<string, string> = {
  '/pm/work-orders/new': 'pm.create',
  '/cm/create': 'repair.create',
  '/calibration/new': 'calibration.create',
  '/incidents/new': 'corrective.create',
  '/documents/new': 'doc' + 'ument.write',
  '/asset-transfers/new': 'commissioning.create',
  '/purchases/new': 'purchase.create',
  '/service-contracts/new': 'data.create',
}

/** Capability mà route tạo yêu cầu, hoặc `null` khi route chưa được khai. */
export function capabilityForCreateRoute(path: string): string | null {
  const clean = (path || '').split('?')[0].split('#')[0]
  return CREATE_ROUTE_CAP[clean] ?? null
}

/**
 * Nút «Tạo …» có được render không (lớp phòng thủ thứ hai, sau `can_create` của backend).
 *
 * **Fail-CLOSED** với route chưa khai: thà thiếu một nút (bắt ĐỎ ngay ở test parity
 * backend↔FE) còn hơn dựng nút dẫn thẳng tới `/unauthorized`. Khác `canAccessDrill`
 * (fail-open) vì drill chỉ là đường XEM, còn đây là lời mời GHI dữ liệu.
 */
export function canAccessCreateRoute(path: string, can: (cap: string) => boolean): boolean {
  const cap = capabilityForCreateRoute(path)
  return cap ? can(cap) : false
}

/**
 * Quyết định một drill-target (route đích của KPI/segment) có click được không.
 *
 * Mirror chính xác bước 4 của resolveRouteAccess: moduleId → `<domain>.read`.
 * Route ngoài map (master/system/null cap, hoặc không khớp) → cho phép — KHÔNG
 * chặn nhầm; route-guard vẫn là chốt chặn cuối nếu đoán sai.
 *
 * @param path  drill.route (pathname, không kèm query)
 * @param can   ctx.can — kiểm tra capability (từ useCapabilities)
 */
export function canAccessDrill(path: string, can: (cap: string) => boolean): boolean {
  if (!path) return true
  // 1. Route có cap đích trực tiếp (audit-trail, user-profiles, admin/roles) —
  //    ưu tiên trước module-rule để dùng đúng capability (sửa drift §9.4.9).
  const capRule = DRILL_CAP_RULES.find(([re]) => re.test(path))
  if (capRule) return can(capRule[1])
  // 2. Route module → `<domain>.read`.
  const rule = DRILL_MODULE_RULES.find(([re]) => re.test(path))
  if (!rule) return true
  const cap = moduleIdToCap(rule[1])
  if (!cap) return true // master/system → không gate bằng cap đặc thù
  return can(cap)
}
