// CR-RBAC-PARITY (2026-07-15) — Guard bất biến: sidebar nav ⇔ route-access.
//
// Bối cảnh: bug điều chuyển (Thủ kho vào /asset-transfers rồi 403; Trưởng phòng
// VT-TTBYT bị /unauthorized) là 1 THỂ HIỆN của lớp lỗi "cap gate lệch domain".
// User yêu cầu MỞ RỘNG soi mọi role: role phải (a) vào được module được phép
// [không dead-gate], (b) KHÔNG chạm module không được phép [không leak], và UI
// (sidebar) phải rõ ràng — KHỚP đúng cái route cho vào.
//
// Hai bất biến (data-driven trên MODULE_NAV × routes THẬT — không hardcode):
//   1. DEAD-GATE guard: nếu sidebar HIỂN THỊ link (user có item.cap) thì route
//      của link đó PHẢI cho vào ('allow'). Ngược lại = user thấy link → click →
//      /unauthorized (UI đánh lừa). Đây chính là lớp bug CAPA/transfer.
//   2. LEAK guard: nếu sidebar item CÓ cap (không phải mở cho mọi người) thì
//      route PHẢI gate — user KHÔNG cap phải bị 'unauthorized'. Route hở
//      (caps=[] + no moduleId) trong khi sidebar gated = lọt module cấm.
//
// Sửa mismatch = đồng bộ cap ở router/index.ts + constants/sidebarNav.ts (KHÔNG
// nới quyền BE). Guard này chốt để mọi route/sidebar mới không tái phát drift.
import { describe, it, expect } from 'vitest'
import {
  resolveRouteAccess,
  type RouteAccessCtx,
  type RouteAccessMeta,
} from './routeAccess'
import { routes } from './index'
import { MODULE_NAV, type NavItem } from '@/constants/sidebarNav'
import type { RouteRecordRaw } from 'vue-router'

// Tìm route THẬT theo path (đệ quy children) — bind guard vào bảng route sản xuất.
function findRoute(path: string): RouteRecordRaw | undefined {
  const stack: RouteRecordRaw[] = [...routes]
  while (stack.length) {
    const r = stack.shift()!
    if (r.path === path) return r
    if (r.children) stack.push(...(r.children as RouteRecordRaw[]))
  }
  return undefined
}

function metaOf(path: string): RouteAccessMeta | undefined {
  return findRoute(path)?.meta as RouteAccessMeta | undefined
}

function ctx(opts: Partial<RouteAccessCtx> = {}): RouteAccessCtx {
  return { isFrappeAdmin: false, can: () => false, hasAnyRole: () => false, ...opts }
}

// Chuẩn hoá item.cap → mảng cap. undefined = mở cho mọi user (bỏ qua guard cap).
function itemCaps(item: NavItem): string[] {
  if (item.cap === undefined) return []
  return Array.isArray(item.cap) ? [...item.cap] : [item.cap]
}

// Mọi (module, item) có path — dùng cho cả 2 guard.
const NAV_ITEMS: Array<{ code: string; label: string; item: NavItem }> = []
for (const mod of Object.values(MODULE_NAV)) {
  for (const item of mod.items) NAV_ITEMS.push({ code: mod.code, label: item.label, item })
}

describe('CR-RBAC-PARITY #1 — DEAD-GATE: thấy link ⇒ route cho vào', () => {
  for (const { code, label, item } of NAV_ITEMS) {
    const caps = itemCaps(item)
    if (caps.length === 0) continue // item mở cho mọi user → guard #2 lo phần route
    it(`[${code}] "${label}" (${item.path}) — user có [${caps.join(',')}] phải vào được`, () => {
      const meta = metaOf(item.path)
      expect(meta, `route ${item.path} không tồn tại trong bảng route`).toBeTruthy()
      // User CHỈ có đúng (các) cap mà sidebar dùng để hiện link.
      const can = (c: string) => caps.includes(c)
      expect(
        resolveRouteAccess(meta!, ctx({ can })),
        `sidebar hiện "${label}" cho cap [${caps.join(',')}] nhưng route ${item.path} chặn ` +
          `(requiredCapabilities=${JSON.stringify(meta!.requiredCapabilities)}) → user click sẽ /unauthorized`,
      ).toBe('allow')
    })
  }
})

describe('CR-RBAC-PARITY #2 — LEAK: sidebar gated ⇒ route gated', () => {
  for (const { code, label, item } of NAV_ITEMS) {
    const caps = itemCaps(item)
    if (caps.length === 0) continue // item mở cho mọi user → route hở là hợp lệ
    it(`[${code}] "${label}" (${item.path}) — user KHÔNG cap phải bị chặn`, () => {
      const meta = metaOf(item.path)
      expect(meta, `route ${item.path} không tồn tại`).toBeTruthy()
      expect(
        resolveRouteAccess(meta!, ctx()), // can()=false toàn bộ
        `sidebar gate "${label}" theo [${caps.join(',')}] nhưng route ${item.path} HỞ ` +
          `(requiredCapabilities=${JSON.stringify(meta!.requiredCapabilities)}) → module lọt cho user không quyền`,
      ).toBe('unauthorized')
    })
  }
})
