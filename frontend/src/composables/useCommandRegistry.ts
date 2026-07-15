// Copyright (c) 2026, AssetCore Team
//
// useCommandRegistry — danh mục lệnh ⌘K DẪN XUẤT từ 2 nguồn ĐÃ CÓ
// (ADR-IMM00-CMDK D1 + D1-bis). KHÔNG file commands.ts hardcode.
//
//   1. MODULE_NAV (constants/sidebarNav.ts) → flatten mọi NavItem → command 'nav'.
//   2. route tĩnh không-nav (router.getRoutes()) có meta.title, KHÔNG trùng
//      path MODULE_NAV → command 'route'.
//
// D1-bis FEED-SAFETY:
//   - LOẠI route meta.devOnly===true (không vào palette production).
//   - LOẠI nhãn rỗng / route động (path chứa ':' hoặc '*').
//   - router:95 đã sửa title 'Quét QR — GMDN Status' → 'Mở hồ sơ thiết bị' (nguồn).
//
// Dedupe path TOÀN CỤC (vd /assets xuất hiện ở nhiều persona/module; route
// trùng path nav cũng bị loại). Nav thắng route khi cùng path. Command thừa kế
// `cap` của NavItem → ⌘K cũng gate theo capability (transfer = commissioning.read).
//
// Logic build TÁCH ra hàm thuần `buildCommandRegistry(modules, routes)` để
// unit-test KHÔNG cần mount router (TC-CMDK-01/02/13/14).

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { RouteRecordNormalized } from 'vue-router'
import { MODULE_NAV, type ModuleNav } from '@/constants/sidebarNav'
import type { CommandItem } from '@/types/command'

/** Subset route cần để build command 'route' (test cấp fixture nhẹ). */
export interface RouteLike {
  path: string
  meta?: {
    title?: unknown
    devOnly?: unknown
    requiredCapabilities?: string[]
    moduleId?: string
    requiresAuth?: unknown
  }
}

/** Nhãn route → bỏ hậu tố " — AssetCore" (đồng bộ AppTopBar pageTitle). */
function cleanRouteTitle(raw: string): string {
  return raw.replace(/\s*—\s*AssetCore$/, '').trim()
}

/** Path động (param/wildcard) → không phải đích ⌘K hợp lệ. */
function isDynamicPath(path: string): boolean {
  return path.includes(':') || path.includes('*')
}

/**
 * buildCommandRegistry — hàm THUẦN (không Vue). Dẫn xuất CommandItem[].
 *
 * @param modules MODULE_NAV (map moduleId → ModuleNav)
 * @param routes  danh sách route tĩnh (router.getRoutes() hoặc fixture)
 */
export function buildCommandRegistry(
  modules: Record<string, ModuleNav>,
  routes: readonly RouteLike[],
): CommandItem[] {
  const out: CommandItem[] = []
  const seen = new Set<string>()

  // 1. Nguồn chính: MODULE_NAV (nav). Nav thắng route khi trùng path.
  for (const [moduleId, mod] of Object.entries(modules)) {
    for (const item of mod.items) {
      if (seen.has(item.path)) continue
      seen.add(item.path)
      out.push({
        id: item.path,
        title: item.label,
        subtitle: mod.title,
        icon: item.icon,
        to: item.path,
        cap: item.cap,
        source: 'nav',
        moduleId,
      })
    }
  }

  // 2. Bổ sung: route tĩnh không-nav có meta.title (route).
  for (const r of routes) {
    const meta = r.meta ?? {}
    // D1-bis: loại dev-only.
    if (meta.devOnly === true) continue
    // route công khai / auth=false (login/register/404…) KHÔNG vào palette.
    if (meta.requiresAuth === false) continue
    if (isDynamicPath(r.path)) continue
    if (seen.has(r.path)) continue
    const rawTitle = typeof meta.title === 'string' ? meta.title : ''
    const title = cleanRouteTitle(rawTitle)
    if (!title) continue
    seen.add(r.path)
    out.push({
      id: r.path,
      title,
      to: r.path,
      cap: meta.requiredCapabilities && meta.requiredCapabilities.length > 0
        ? meta.requiredCapabilities
        : undefined,
      source: 'route',
      moduleId: meta.moduleId,
    })
  }

  return out
}

/**
 * useCommandRegistry — reactive registry cho component/store.
 * Routes lấy live từ router.getRoutes(); MODULE_NAV tĩnh.
 */
export function useCommandRegistry() {
  const router = useRouter()
  const registry = computed<CommandItem[]>(() =>
    buildCommandRegistry(MODULE_NAV, router.getRoutes() as RouteRecordNormalized[]),
  )
  return { registry }
}
