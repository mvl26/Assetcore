// TDD — LL-FE-22: route-guard `requiredRoles: ROLES_*` no-op fix.
//
// Bug: mọi hằng `ROLES_*` ở constants/roles.ts là empty-stub `[]`, nên nhánh
// guard `requiredRoles` (length === 0) bị skip → route không được gate. Routes
// `master`/`system`/unmapped (không có moduleId → capability) hoàn toàn hở.
//
// Fix: `resolveRouteAccess` — hàm thuần quyết định allow/deny dựa trên:
//   1. frappe-admin bypass
//   2. requiredCapabilities (OR)
//   3. legacy requiredRoles (OR) — vẫn hỗ trợ nếu non-empty
//   4. moduleId → `<domain>.read` fallback
// Route mở (không meta nào) → allow.
import { describe, it, expect } from 'vitest'
import { resolveRouteAccess, type RouteAccessCtx } from './routeAccess'

function ctx(opts: Partial<RouteAccessCtx> = {}): RouteAccessCtx {
  return {
    isFrappeAdmin: false,
    can: () => false,
    hasAnyRole: () => false,
    ...opts,
  }
}
const canOnly =
  (...caps: string[]) =>
  (c: string) =>
    caps.includes(c)

describe('resolveRouteAccess — frappe admin bypass', () => {
  it('admin luôn allow kể cả khi thiếu mọi capability', () => {
    expect(
      resolveRouteAccess({ requiredCapabilities: ['data.admin'] }, ctx({ isFrappeAdmin: true })),
    ).toBe('allow')
  })
})

describe('resolveRouteAccess — requiredCapabilities (OR)', () => {
  it('deny khi không có cap', () => {
    expect(resolveRouteAccess({ requiredCapabilities: ['data.admin'] }, ctx())).toBe('unauthorized')
  })
  it('allow khi có một trong các cap', () => {
    expect(
      resolveRouteAccess(
        { requiredCapabilities: ['pm.write', 'pm.create'] },
        ctx({ can: canOnly('pm.create') }),
      ),
    ).toBe('allow')
  })
})

describe('resolveRouteAccess — legacy requiredRoles (no-op khi rỗng)', () => {
  it('requiredRoles rỗng [] KHÔNG gate (về allow nếu không meta khác) — nhưng đây CHÍNH LÀ bug; route hở phải đã chuyển sang capability', () => {
    // Empty array → branch skip. Nếu route chỉ dựa vào [] thì hở.
    expect(resolveRouteAccess({ requiredRoles: [] }, ctx())).toBe('allow')
  })
  it('requiredRoles non-empty vẫn gate đúng (defense-in-depth)', () => {
    expect(
      resolveRouteAccess({ requiredRoles: ['AssetCore Auditor'] }, ctx({ hasAnyRole: () => false })),
    ).toBe('unauthorized')
    expect(
      resolveRouteAccess({ requiredRoles: ['AssetCore Auditor'] }, ctx({ hasAnyRole: () => true })),
    ).toBe('allow')
  })
})

describe('resolveRouteAccess — moduleId → <domain>.read fallback', () => {
  it('deny khi thiếu cap read của module', () => {
    expect(resolveRouteAccess({ moduleId: 'imm08' }, ctx())).toBe('unauthorized')
  })
  it('allow khi có pm.read cho imm08', () => {
    expect(resolveRouteAccess({ moduleId: 'imm08' }, ctx({ can: canOnly('pm.read') }))).toBe('allow')
  })
  it('master/system moduleId không map cap → không gate qua nhánh này', () => {
    // master không có cap read → nhánh moduleId bỏ qua; route phải tự khai requiredCapabilities.
    expect(resolveRouteAccess({ moduleId: 'master' }, ctx())).toBe('allow')
  })
})

describe('resolveRouteAccess — route mở', () => {
  it('không meta gate nào → allow', () => {
    expect(resolveRouteAccess({}, ctx())).toBe('allow')
  })
})

describe('resolveRouteAccess — requiredCapabilities ưu tiên hơn moduleId', () => {
  it('có cap đáp ứng requiredCapabilities → allow, bỏ qua moduleId', () => {
    expect(
      resolveRouteAccess(
        { requiredCapabilities: ['data.admin'], moduleId: 'master' },
        ctx({ can: canOnly('data.admin') }),
      ),
    ).toBe('allow')
  })
})
