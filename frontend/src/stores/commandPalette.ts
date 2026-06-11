// Copyright (c) 2026, AssetCore Team
//
// commandPalette — Pinia store ⌘K (ADR-IMM00-CMDK D2 + D6).
//
// State: open / query / recent[≤5] / pinned[]. Persist recent + pinned localStorage.
// Getter filteredCommands ÁP D2 GATE (capability) qua itemVisible (nav) +
// resolveRouteAccess (route) + matchCommand (fuzzy). KHÔNG predicate gate thứ 2.
//
// Registry KHÔNG sống trong store (tránh import router vào store) — view inject
// qua setRegistry(items) từ useCommandRegistry().registry. Store thuần state +
// gate + search → unit-test được không cần router.

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useCapabilities } from '@/composables/useCapabilities'
import { useAuthStore } from '@/stores/auth'
import { itemVisible, type NavItem } from '@/constants/sidebarNav'
import { resolveRouteAccess } from '@/router/routeAccess'
import { matchCommand } from '@/utils/matchCommand'
import type { CommandItem } from '@/types/command'

const RECENT_KEY = 'ac_cmdk_recent'
const PINNED_KEY = 'ac_cmdk_pinned'
const RECENT_MAX = 5

function readIds(key: string): string[] {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((x): x is string => typeof x === 'string')
  } catch {
    return []
  }
}

function writeIds(key: string, ids: readonly string[]): void {
  try {
    localStorage.setItem(key, JSON.stringify([...ids]))
  } catch {
    /* private mode / quota — bỏ qua, in-memory vẫn chạy */
  }
}

export const useCommandPaletteStore = defineStore('commandPalette', () => {
  const open = ref(false)
  const query = ref('')
  const recent = ref<string[]>(readIds(RECENT_KEY))
  const pinned = ref<string[]>(readIds(PINNED_KEY))
  // Registry inject từ view (useCommandRegistry). Mặc định rỗng.
  const registry = ref<CommandItem[]>([])

  function setRegistry(items: readonly CommandItem[]): void {
    registry.value = [...items]
  }

  // ── D2 GATE: chỉ command user CÓ QUYỀN mới qua. Tái dùng predicate hiện hữu. ──
  function gatedCommands(): CommandItem[] {
    const { can } = useCapabilities()
    const auth = useAuthStore()
    const isSuperuser = auth.isFrappeAdmin
    const ctx = {
      isFrappeAdmin: auth.isFrappeAdmin,
      can: (cap: string) => can(cap),
      hasAnyRole: (roles: readonly string[]) => auth.hasAnyRole(roles),
    }
    return registry.value.filter((cmd) => {
      if (cmd.source === 'nav') {
        // itemVisible nhận NavItem {label,path,icon,cap}. Map từ CommandItem.
        const navItem: NavItem = {
          label: cmd.title,
          path: cmd.to,
          icon: cmd.icon ?? 'grid',
          cap: cmd.cap,
        }
        return itemVisible(navItem, can, isSuperuser)
      }
      // source 'route' → resolveRouteAccess(meta, ctx) === 'allow'.
      return resolveRouteAccess(
        {
          requiredCapabilities: cmd.cap
            ? (Array.isArray(cmd.cap) ? [...cmd.cap] : [cmd.cap])
            : undefined,
          moduleId: cmd.moduleId,
        },
        ctx,
      ) === 'allow'
    })
  }

  /** Lệnh đã gate — KHÔNG tính query (anti-leak: gate luôn áp trước). */
  const visibleCommands = computed<CommandItem[]>(() => gatedCommands())

  /** Lệnh đã ghim, đã gate (mất quyền → ẩn). Theo thứ tự pinned[]. */
  const pinnedCommands = computed<CommandItem[]>(() => {
    const byId = new Map(visibleCommands.value.map((c) => [c.id, c]))
    return pinned.value.map((id) => byId.get(id)).filter((c): c is CommandItem => Boolean(c))
  })

  /** Lệnh gần đây, đã gate (mất quyền → ẩn), bỏ trùng pinned. Theo thứ tự recent[]. */
  const recentCommands = computed<CommandItem[]>(() => {
    const byId = new Map(visibleCommands.value.map((c) => [c.id, c]))
    const pinnedSet = new Set(pinned.value)
    return recent.value
      .filter((id) => !pinnedSet.has(id))
      .map((id) => byId.get(id))
      .filter((c): c is CommandItem => Boolean(c))
  })

  /** Kết quả search: gate → matchCommand(query) với boost recent/pinned. */
  const filteredCommands = computed<CommandItem[]>(() =>
    matchCommand(query.value, visibleCommands.value, {
      pinned: pinned.value,
      recent: recent.value,
    }),
  )

  // ── Actions ────────────────────────────────────────────────────────────────
  function openPalette(): void { open.value = true }
  function closePalette(): void { open.value = false; query.value = '' }
  function toggle(): void { open.value ? closePalette() : openPalette() }
  function setQuery(q: string): void { query.value = q }

  /** Ghi lệnh vừa chọn vào recent (unshift + dedupe + cắt 5 + persist). */
  function selectCommand(id: string): void {
    const next = [id, ...recent.value.filter((x) => x !== id)].slice(0, RECENT_MAX)
    recent.value = next
    writeIds(RECENT_KEY, next)
  }

  /** Ghim / bỏ ghim 1 lệnh (persist). */
  function togglePin(id: string): void {
    const next = pinned.value.includes(id)
      ? pinned.value.filter((x) => x !== id)
      : [...pinned.value, id]
    pinned.value = next
    writeIds(PINNED_KEY, next)
  }

  function isPinned(id: string): boolean {
    return pinned.value.includes(id)
  }

  return {
    open, query, recent, pinned, registry,
    setRegistry,
    visibleCommands, pinnedCommands, recentCommands, filteredCommands,
    openPalette, closePalette, toggle, setQuery,
    selectCommand, togglePin, isPinned,
  }
})
