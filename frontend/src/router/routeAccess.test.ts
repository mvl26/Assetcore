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

// ─── §7.septies — route master-group gate khớp sidebar + depreciation finance-gate
// ─── A6 — route AssetScanInfo (màn info mobile-first khi quét QR) ──────────────
describe('A6 — route AssetScanInfo gate asset.read', () => {
  // Route /assets/:id/info (name='AssetScanInfo') khai requiredCapabilities:
  // ['asset.read'] — tái dùng cap A2 (KHÔNG cap mới). Defense-in-depth với BE
  // require('asset.read'): URL trực tiếp KHÔNG bypass được nếu thiếu quyền.
  const META = { requiredCapabilities: ['asset.read'] }
  it('thiếu asset.read → unauthorized (KHÔNG bypass bằng URL trực tiếp)', () => {
    expect(resolveRouteAccess(META, ctx())).toBe('unauthorized')
    // Có cap khác nhưng KHÔNG asset.read → vẫn chặn.
    expect(resolveRouteAccess(META, ctx({ can: canOnly('pm.read', 'data.read') }))).toBe(
      'unauthorized',
    )
  })
  it('có asset.read → allow', () => {
    expect(resolveRouteAccess(META, ctx({ can: canOnly('asset.read') }))).toBe('allow')
  })
  it('frappe admin → allow (bypass kể cả khi thiếu asset.read)', () => {
    expect(resolveRouteAccess(META, ctx({ isFrappeAdmin: true }))).toBe('allow')
  })
})

describe('§7.septies.2 — master-group list route gate data.read (VĐ1)', () => {
  // RT-CAP-1: route /suppliers,/device-models,/service-contracts khai
  // requiredCapabilities:['data.read']. Non-data user (can=false) bị chặn —
  // KHÔNG còn rơi xuống default allow như khi route chỉ có moduleId='master'.
  it('RT-CAP-1: requiredCapabilities data.read + không có cap → unauthorized', () => {
    expect(
      resolveRouteAccess(
        { requiredCapabilities: ['data.read'], moduleId: 'master' },
        ctx(),
      ),
    ).toBe('unauthorized')
  })
  it('data user (data.read) → allow vào /suppliers', () => {
    expect(
      resolveRouteAccess(
        { requiredCapabilities: ['data.read'], moduleId: 'master' },
        ctx({ can: canOnly('data.read') }),
      ),
    ).toBe('allow')
  })
})

// ─── TC-RT-06-DASH-01 — route TrainingDashboard cap-gate training.read
describe('TC-RT-06-DASH-01 — /imm06/dashboard yêu cầu cap training.read (parity IMM-06)', () => {
  // Mirror chính xác meta route TrainingDashboard trong router/index.ts.
  const DASH_META = { requiredCapabilities: ['training.read'], moduleId: 'imm06' }
  it('persona thiếu cap training.read → unauthorized', () => {
    expect(resolveRouteAccess(DASH_META, ctx())).toBe('unauthorized')
    // có cap module khác cũng KHÔNG mở được dashboard đào tạo
    expect(resolveRouteAccess(DASH_META, ctx({ can: canOnly('pm.read', 'inventory.read') }))).toBe('unauthorized')
  })
  it('persona có training.read → allow (parity với /imm06/competencies)', () => {
    expect(resolveRouteAccess(DASH_META, ctx({ can: canOnly('training.read') }))).toBe('allow')
  })
  it('frappe-admin bypass → allow', () => {
    expect(resolveRouteAccess(DASH_META, ctx({ isFrappeAdmin: true }))).toBe('allow')
  })
})

// ─── A2 (ADR-001 D4) — route QrDeepLink /a/:token gate asset.read
describe('A2 — /a/:token (QrDeepLink) yêu cầu cap asset.read', () => {
  // Mirror chính xác meta route QrDeepLink trong router/index.ts. asset.read chỉ
  // tồn tại SAU khi BE thêm domain Asset (_DOMAIN_PRIMARY) — chống RBAC dead-gate:
  // user có DocPerm read AC Asset → cap True → vào được; thiếu → unauthorized
  // (KHÔNG dead-gate âm thầm vì cap tồn tại thật trong CAPABILITY_MAP).
  const QR_META = { requiredCapabilities: ['asset.read'] }
  it('user KHÔNG có asset.read → unauthorized', () => {
    expect(resolveRouteAccess(QR_META, ctx())).toBe('unauthorized')
    // cap module khác KHÔNG mở được deep-link QR
    expect(resolveRouteAccess(QR_META, ctx({ can: canOnly('pm.read', 'data.read') }))).toBe('unauthorized')
  })
  it('user có asset.read → allow', () => {
    expect(resolveRouteAccess(QR_META, ctx({ can: canOnly('asset.read') }))).toBe('allow')
  })
  it('frappe-admin bypass → allow', () => {
    expect(resolveRouteAccess(QR_META, ctx({ isFrappeAdmin: true }))).toBe('allow')
  })
})

// ─── B (ADR-001 D4, siết RBAC least-privilege) — route AssetLabelPrint gate asset.write
describe('B — /assets/labels/print (AssetLabelPrint) yêu cầu cap asset.write', () => {
  // Mirror chính xác meta route AssetLabelPrint trong router/index.ts: in nhãn QR
  // = side-effect (ghi ALE label_printed + audit) → gate asset.WRITE, KHÔNG
  // asset.read. User chỉ-đọc (asset.read) KHÔNG vào được màn in. Defense-in-depth
  // với BE get_asset_label_data_batch/mark_label_printed require('asset.write').
  const LABEL_META = { requiredCapabilities: ['asset.write'] }
  it('user chỉ-đọc (asset.read, KHÔNG asset.write) → unauthorized', () => {
    expect(resolveRouteAccess(LABEL_META, ctx({ can: canOnly('asset.read') }))).toBe('unauthorized')
    // cap module khác cũng KHÔNG mở được màn in
    expect(resolveRouteAccess(LABEL_META, ctx({ can: canOnly('pm.write', 'data.read') }))).toBe('unauthorized')
  })
  it('user có asset.write → allow', () => {
    expect(resolveRouteAccess(LABEL_META, ctx({ can: canOnly('asset.write') }))).toBe('allow')
  })
  it('frappe-admin bypass → allow (kể cả khi thiếu asset.write)', () => {
    expect(resolveRouteAccess(LABEL_META, ctx({ isFrappeAdmin: true }))).toBe('allow')
  })
})

// ─── B regression: route read-only quét QR vẫn CHỈ cần asset.read (KHÔNG bị siết nhầm)
describe('B regression — QrDeepLink + AssetScanInfo giữ asset.read (read-only quét QR)', () => {
  const QR_DEEPLINK_META = { requiredCapabilities: ['asset.read'] }
  const SCAN_INFO_META = { requiredCapabilities: ['asset.read'] }
  it('user chỉ-đọc (asset.read, KHÔNG asset.write) → vẫn quét QR + xem thông tin được', () => {
    const readOnly = ctx({ can: canOnly('asset.read') })
    expect(resolveRouteAccess(QR_DEEPLINK_META, readOnly)).toBe('allow')
    expect(resolveRouteAccess(SCAN_INFO_META, readOnly)).toBe('allow')
  })
})

describe('§7.septies.3 — /depreciation finance OR-gate (VĐ2)', () => {
  // PHẢI khớp FINANCE_READ_CAPS = data.write|needs.read|procurement.read|pm.read|calibration.read
  const DEP_META = {
    requiredCapabilities: [
      'data.write', 'needs.read', 'procurement.read', 'pm.read', 'calibration.read',
    ],
    moduleId: 'master',
  }
  it('RT-DEP-1: persona doc/training (document.read+training.read) → unauthorized', () => {
    expect(
      resolveRouteAccess(DEP_META, ctx({ can: canOnly('document.read', 'training.read', 'data.read') })),
    ).toBe('unauthorized')
  })
  it('RT-DEP-2: opsmgr (needs.read/procurement.read) → allow', () => {
    expect(resolveRouteAccess(DEP_META, ctx({ can: canOnly('needs.read') }))).toBe('allow')
    expect(resolveRouteAccess(DEP_META, ctx({ can: canOnly('procurement.read') }))).toBe('allow')
  })
  it('RT-DEP-3: workshop/tech (pm.read/calibration.read) → allow', () => {
    expect(resolveRouteAccess(DEP_META, ctx({ can: canOnly('pm.read') }))).toBe('allow')
    expect(resolveRouteAccess(DEP_META, ctx({ can: canOnly('calibration.read') }))).toBe('allow')
  })
  it('store (chỉ inventory.read) → unauthorized', () => {
    expect(resolveRouteAccess(DEP_META, ctx({ can: canOnly('inventory.read', 'data.read') }))).toBe('unauthorized')
  })
  it('clinical (chỉ corrective.read) → unauthorized', () => {
    expect(resolveRouteAccess(DEP_META, ctx({ can: canOnly('corrective.read', 'data.read') }))).toBe('unauthorized')
  })
  it('admin bypass → allow', () => {
    expect(resolveRouteAccess(DEP_META, ctx({ isFrappeAdmin: true }))).toBe('allow')
  })
})
