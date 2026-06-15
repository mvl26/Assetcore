// TDD — Command Palette ⌘K registry (ADR-IMM00-CMDK D1 + D1-bis).
// TC-CMDK-01/02/13/14 — registry DẪN XUẤT từ MODULE_NAV + route tĩnh, KHÔNG hardcode.
import { describe, it, expect } from 'vitest'
import { buildCommandRegistry, type RouteLike } from './useCommandRegistry'
import { MODULE_NAV, type ModuleNav } from '@/constants/sidebarNav'

// Route fixture giống router.getRoutes() — gồm: 1 nav-trùng (loại), 1 route tĩnh
// hợp lệ, 1 devOnly (loại), 1 động (loại), 1 auth=false (loại), 1 không title (loại).
const ROUTES: RouteLike[] = [
  { path: '/assets', meta: { requiresAuth: true, title: 'Danh sách Thiết bị' } }, // trùng nav master
  { path: '/incidents/new', meta: { requiresAuth: true, title: 'Tạo báo hỏng', requiredCapabilities: ['corrective.create'] } },
  { path: '/pm/work-orders/new', meta: { requiresAuth: true, title: 'Tạo PM', requiredCapabilities: ['pm.create'] } },
  { path: '/debug/asset-dashboard', meta: { requiresAuth: true, title: 'Tổng quan Thiết bị (Debug)', devOnly: true } },
  { path: '/a/:token', meta: { requiresAuth: true, title: 'Mở hồ sơ thiết bị' } }, // động → loại
  { path: '/login', meta: { requiresAuth: false, title: 'Đăng nhập — AssetCore' } }, // auth=false → loại
  { path: '/qr-scan', meta: { requiresAuth: true, title: 'Mở hồ sơ thiết bị' } }, // trùng nav master /qr-scan? no — master có /qr-scan
  { path: '/no-title', meta: { requiresAuth: true } }, // không title → loại
]

describe('buildCommandRegistry — D1 derived from 2 sources', () => {
  const registry = buildCommandRegistry(MODULE_NAV, ROUTES)

  it('TC-CMDK-01: chứa MỌI NavItem.path của MODULE_NAV (source nav)', () => {
    const navPaths = new Set<string>()
    for (const mod of Object.values(MODULE_NAV)) {
      for (const it of mod.items) navPaths.add(it.path)
    }
    const regNavPaths = new Set(registry.filter((c) => c.source === 'nav').map((c) => c.to))
    for (const p of navPaths) expect(regNavPaths.has(p)).toBe(true)
  })

  it('TC-CMDK-01: route tĩnh whitelisted xuất hiện (source route), 0 entry hardcode ngoài 2 nguồn', () => {
    const incident = registry.find((c) => c.to === '/incidents/new')
    expect(incident).toBeDefined()
    expect(incident?.source).toBe('route')
    // Mỗi command phải có source ∈ {nav, route} — không nguồn thứ 3.
    for (const c of registry) expect(['nav', 'route']).toContain(c.source)
  })

  it('TC-CMDK-13: LOẠI route devOnly + path động + auth=false + không-title', () => {
    expect(registry.find((c) => c.to === '/debug/asset-dashboard')).toBeUndefined()
    expect(registry.find((c) => c.to === '/a/:token')).toBeUndefined()
    expect(registry.find((c) => c.to === '/login')).toBeUndefined()
    expect(registry.find((c) => c.to === '/no-title')).toBeUndefined()
  })

  it('TC-CMDK-13: 0 nhãn chứa "GMDN"/"Status"/"Debug"', () => {
    for (const c of registry) {
      expect(c.title).not.toMatch(/GMDN/i)
      expect(c.title).not.toMatch(/\bStatus\b/)
      expect(c.title).not.toMatch(/Debug/i)
    }
  })

  it('TC-CMDK-14: route /qr-scan (nav master) nhãn "Quét mã QR"; KHÔNG "GMDN Status"', () => {
    // /qr-scan có trong MODULE_NAV master (label "Quét mã QR") → nav thắng route.
    const qr = registry.find((c) => c.to === '/qr-scan')
    expect(qr).toBeDefined()
    expect(qr?.title).toBe('Quét mã QR')
    expect(qr?.title).not.toMatch(/GMDN|Status/)
  })

  it('dedupe path toàn cục: /assets chỉ 1 entry (nav thắng route)', () => {
    const assets = registry.filter((c) => c.to === '/assets')
    expect(assets.length).toBe(1)
    expect(assets[0].source).toBe('nav')
    // /asset-transfers xuất hiện imm13 + imm15 → chỉ 1.
    const transfers = registry.filter((c) => c.to === '/asset-transfers')
    expect(transfers.length).toBe(1)
  })

  it('TC-CMDK-02: thêm 1 NavItem vào fixture MODULE_NAV → registry +1 command (không sửa code ⌘K)', () => {
    const base = buildCommandRegistry(MODULE_NAV, []).length
    const extended: Record<string, ModuleNav> = {
      ...MODULE_NAV,
      _testmod: {
        code: 'TEST', title: 'Nhóm thử', icon: 'grid',
        items: [{ label: 'Màn thử nghiệm', path: '/__test_new__', icon: 'grid', cap: 'pm.read' }],
      },
    }
    const after = buildCommandRegistry(extended, [])
    expect(after.length).toBe(base + 1)
    const added = after.find((c) => c.to === '/__test_new__')
    expect(added).toBeDefined()
    expect(added?.title).toBe('Màn thử nghiệm')
    expect(added?.cap).toBe('pm.read')
  })
})
