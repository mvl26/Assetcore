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
import { resolveRouteAccess, type RouteAccessCtx, type RouteAccessMeta } from '@/router/routeAccess'
import { routes } from '@/router/index'

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

// ─── D6 (ADR-IMM00-QR-SCAN-ACTION, phương án B) — route AssetLabelPrint gate asset.print
describe('D6 — /assets/labels/print (AssetLabelPrint) yêu cầu cap asset.print', () => {
  // Mirror chính xác meta route AssetLabelPrint trong router/index.ts: in nhãn QR
  // = quyền PRINT (DocPerm print=1 sẵn cho persona vận hành) → gate asset.PRINT,
  // KHÔNG còn asset.write (chỉ Super Admin). Defense-in-depth với BE
  // get_asset_label_data_batch/mark_label_printed require('asset.print').
  const LABEL_META = { requiredCapabilities: ['asset.print'] }
  it('user KHÔNG có asset.print (chỉ read) → unauthorized', () => {
    expect(resolveRouteAccess(LABEL_META, ctx({ can: canOnly('asset.read') }))).toBe('unauthorized')
    // cap module khác cũng KHÔNG mở được màn in
    expect(resolveRouteAccess(LABEL_META, ctx({ can: canOnly('pm.write', 'data.read') }))).toBe('unauthorized')
  })
  it('user có asset.print → allow', () => {
    expect(resolveRouteAccess(LABEL_META, ctx({ can: canOnly('asset.print') }))).toBe('allow')
  })
  it('frappe-admin bypass → allow (kể cả khi thiếu asset.print)', () => {
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

// ─── CR-TRF-AUTHZ: Asset Transfer route-access = Commissioning domain ─────────
// Bug (2026-07-15): /asset-transfers gate qua imm15→inventory.read (SAI domain).
// BE gate TOÀN BỘ vòng đời transfer theo Commissioning (DocPerm Asset Transfer +
// service commissioning.submit/write). Hệ quả: Thủ kho (inventory) lọt route-gate
// rồi 403 ở list_transfers; Trưởng phòng VT-TTBYT (commissioning) bị /unauthorized.
// Fix: gate route theo commissioning.read (view) / commissioning.create (new) —
// khớp BE, KHÔNG cấp quyền mới. Guard bind vào ROUTE THẬT (routes import).
describe('CR-TRF-AUTHZ — Asset Transfer route gate theo Commissioning (FE↔BE parity)', () => {
  const findRoute = (path: string) => {
    const stack = [...routes]
    while (stack.length) {
      const r = stack.shift()!
      if (r.path === path) return r
      if (r.children) stack.push(...r.children)
    }
    return undefined
  }
  const invCtx = ctx({ can: canOnly('inventory.read', 'inventory.create', 'inventory.write') })
  const comReadCtx = ctx({ can: canOnly('commissioning.read') })

  it('CR-TRF-ROUTE-1: /asset-transfers (list) — inventory-only DENY, commissioning ALLOW', () => {
    const r = findRoute('/asset-transfers')
    expect(r).toBeTruthy()
    const meta = r!.meta as RouteAccessMeta
    expect(resolveRouteAccess(meta, invCtx)).toBe('unauthorized')
    expect(resolveRouteAccess(meta, comReadCtx)).toBe('allow')
  })

  it('CR-TRF-ROUTE-2: /asset-transfers/:id (detail) — inventory-only DENY, commissioning ALLOW', () => {
    const meta = findRoute('/asset-transfers/:id')!.meta as RouteAccessMeta
    expect(resolveRouteAccess(meta, invCtx)).toBe('unauthorized')
    expect(resolveRouteAccess(meta, comReadCtx)).toBe('allow')
  })

  it('CR-TRF-ROUTE-3: /asset-transfers/new (create) — commissioning.create ALLOW, inventory.create DENY', () => {
    const meta = findRoute('/asset-transfers/new')!.meta as RouteAccessMeta
    expect(resolveRouteAccess(meta, ctx({ can: canOnly('commissioning.create') }))).toBe('allow')
    expect(resolveRouteAccess(meta, ctx({ can: canOnly('inventory.create') }))).toBe('unauthorized')
  })
})

// ─── CR-SPEC-AUTHZ: /tech-specs route gate theo Spec domain (khớp BE) ─────────
// Audit RBAC-parity (2026-07-15) phát hiện drift cùng lớp transfer: 3 route
// /tech-specs gate 'needs.read' (SAI domain) trong khi BE IMM Tech Spec = Spec
// roles (Spec Manager/User + Auditor) và sidebar item đã dùng 'spec.read'. Latent
// leak: user spec-only sẽ thấy link (spec.read) nhưng route chặn (needs.read).
// Fix: list/detail → spec.read, /new → spec.create.
describe('CR-SPEC-AUTHZ — /tech-specs gate theo Spec domain (FE↔BE parity)', () => {
  const find = (path: string) => {
    const stack = [...routes]
    while (stack.length) {
      const r = stack.shift()!
      if (r.path === path) return r
      if (r.children) stack.push(...r.children)
    }
    return undefined
  }
  const needsOnly = ctx({ can: canOnly('needs.read', 'needs.create') })
  const specRead = ctx({ can: canOnly('spec.read') })

  it('CR-SPEC-1: /tech-specs (list) — needs-only DENY, spec.read ALLOW', () => {
    const meta = find('/tech-specs')!.meta as RouteAccessMeta
    expect(resolveRouteAccess(meta, needsOnly)).toBe('unauthorized')
    expect(resolveRouteAccess(meta, specRead)).toBe('allow')
  })
  it('CR-SPEC-2: /tech-specs/:id (detail) — needs-only DENY, spec.read ALLOW', () => {
    const meta = find('/tech-specs/:id')!.meta as RouteAccessMeta
    expect(resolveRouteAccess(meta, needsOnly)).toBe('unauthorized')
    expect(resolveRouteAccess(meta, specRead)).toBe('allow')
  })
  it('CR-SPEC-3: /tech-specs/new (create) — spec.create ALLOW, needs.read DENY', () => {
    const meta = find('/tech-specs/new')!.meta as RouteAccessMeta
    expect(resolveRouteAccess(meta, ctx({ can: canOnly('spec.create') }))).toBe('allow')
    expect(resolveRouteAccess(meta, ctx({ can: canOnly('needs.read', 'needs.create') }))).toBe('unauthorized')
  })
})

// ─── CR-RBAC-PARITY: list ⇔ detail cùng cấp XEM (không dead-gate khi click) ──────
// Audit mở rộng (2026-07-15) phát hiện thêm lỗi cùng lớp transfer: route DETAIL
// gate cap CHẶT hơn route LIST → user mở được list, click 1 hàng → /unauthorized.
// Sidebar-parity guard (sidebarRouteParity.test.ts) chỉ soi path LIST (path có ở
// sidebar); test này chốt riêng cặp list↔detail cho CAPA (compliance.read) và
// Firmware CR (repair.write). Hành động DUYỆT/ĐÓNG trong detail vẫn gate
// server-driven (allowed_transitions / firmware.approve), KHÔNG do route cấp.
describe('CR-RBAC-PARITY — XEM list ⇔ detail đồng cấp (chống dead-gate khi click hàng)', () => {
  const find = (path: string) => {
    const stack = [...routes]
    while (stack.length) {
      const r = stack.shift()!
      if (r.path === path) return r
      if (r.children) stack.push(...r.children)
    }
    return undefined
  }
  it('CAPA: /capas (list) và /capas/:id (detail) — compliance.read vào được CẢ HAI', () => {
    const complianceRead = ctx({ can: canOnly('compliance.read') })
    expect(resolveRouteAccess(find('/capas')!.meta as RouteAccessMeta, complianceRead)).toBe('allow')
    expect(resolveRouteAccess(find('/capas/:id')!.meta as RouteAccessMeta, complianceRead)).toBe('allow')
  })
  it('CAPA: user chỉ capa.close (submit) KHÔNG bị coi là điều kiện XEM — vẫn cần compliance.read', () => {
    // Không nới quyền đóng: capa.close-only mà thiếu compliance.read thì không XEM
    // (edge lý thuyết — thực tế submit⇒read). Chốt: XEM neo vào compliance.read.
    const capaCloseOnly = ctx({ can: canOnly('capa.close') })
    expect(resolveRouteAccess(find('/capas/:id')!.meta as RouteAccessMeta, capaCloseOnly)).toBe('unauthorized')
  })
  it('Firmware CR: /cm/firmware và /cm/firmware/:id — repair.write vào được, repair.read-only DENY', () => {
    const write = ctx({ can: canOnly('repair.write') })
    const readOnly = ctx({ can: canOnly('repair.read') })
    expect(resolveRouteAccess(find('/cm/firmware')!.meta as RouteAccessMeta, write)).toBe('allow')
    expect(resolveRouteAccess(find('/cm/firmware/:id')!.meta as RouteAccessMeta, write)).toBe('allow')
    expect(resolveRouteAccess(find('/cm/firmware')!.meta as RouteAccessMeta, readOnly)).toBe('unauthorized')
  })
  it('RCA: /rca và /rca/:id — corrective.read vào được (khớp drill-map), soạn thảo server-gated', () => {
    // Persona giám sát read-only (opsmgr) drill sự cố → RCA: XEM được read-only.
    // TRƯỚC gate corrective.write → drill dead-gate. can_manage_rca gate soạn thảo.
    const read = ctx({ can: canOnly('corrective.read') })
    expect(resolveRouteAccess(find('/rca')!.meta as RouteAccessMeta, read)).toBe('allow')
    expect(resolveRouteAccess(find('/rca/:id')!.meta as RouteAccessMeta, read)).toBe('allow')
  })
})

// ─── CR-AFFORD: /purchases/new gate theo purchase.create (khớp BE AC Purchase) ──
// Route cũ KHÔNG khai requiredCapabilities → fallback imm03→procurement.read (cap
// READ) cho hành động TẠO. BE create AC Purchase = Procurement Manager/User
// (purchase.create). Fix: gate purchase.create — procurement.read-only (vd Auditor)
// KHÔNG tạo được (parity BE, tránh form→submit→403).
describe('CR-AFFORD — /purchases/new gate purchase.create (FE↔BE parity)', () => {
  const find = (path: string) => {
    const stack = [...routes]
    while (stack.length) {
      const r = stack.shift()!
      if (r.path === path) return r
      if (r.children) stack.push(...r.children)
    }
    return undefined
  }
  it('purchase.create ALLOW, procurement.read-only DENY', () => {
    const meta = find('/purchases/new')!.meta as RouteAccessMeta
    expect(resolveRouteAccess(meta, ctx({ can: canOnly('purchase.create') }))).toBe('allow')
    expect(resolveRouteAccess(meta, ctx({ can: canOnly('procurement.read') }))).toBe('unauthorized')
  })
})

// ─── CR-AFFORD: /needs-requests/new gate theo needs.create (khớp BE) ───────────
// Route TẠO đề xuất nhu cầu gate 'needs.read' (cap ĐỌC) → user chỉ-đọc mở form
// tạo rồi doc.insert() 403 (DocPerm create IMM Needs Request = needs.create). Fix:
// gate needs.create — parity BE + nút "Tạo đề xuất" (NeedsRequestListView) cùng cap.
describe('CR-AFFORD — /needs-requests/new gate needs.create (FE↔BE parity)', () => {
  const find = (path: string) => {
    const stack = [...routes]
    while (stack.length) {
      const r = stack.shift()!
      if (r.path === path) return r
      if (r.children) stack.push(...r.children)
    }
    return undefined
  }
  it('needs.create ALLOW, needs.read-only DENY', () => {
    const meta = find('/needs-requests/new')!.meta as RouteAccessMeta
    expect(resolveRouteAccess(meta, ctx({ can: canOnly('needs.create') }))).toBe('allow')
    expect(resolveRouteAccess(meta, ctx({ can: canOnly('needs.read') }))).toBe('unauthorized')
  })
})

// ─── CR-RBAC-PARITY: /device-models/:id XEM = data.read (form render read-only) ──
// DeviceModelListView click-toàn-hàng → /device-models/:id. TRƯỚC gate data.write
// (chỉ có route SỬA) → user data.read (thấy list) click model → /unauthorized
// (dead-gate). Fix: route data.read; DeviceModelFormView render READ-ONLY khi thiếu
// data.write (fieldset :disabled + ẩn Lưu/Xóa). Ghi vẫn cần data.write ở BE.
describe('CR-RBAC-PARITY — /device-models/:id XEM data.read (read-only khi thiếu write)', () => {
  const find = (path: string) => {
    const stack = [...routes]
    while (stack.length) {
      const r = stack.shift()!
      if (r.path === path) return r
      if (r.children) stack.push(...r.children)
    }
    return undefined
  }
  it('data.read vào được (đọc), no-cap DENY', () => {
    const meta = find('/device-models/:id')!.meta as RouteAccessMeta
    expect(resolveRouteAccess(meta, ctx({ can: canOnly('data.read') }))).toBe('allow')
    expect(resolveRouteAccess(meta, ctx())).toBe('unauthorized')
  })
})
