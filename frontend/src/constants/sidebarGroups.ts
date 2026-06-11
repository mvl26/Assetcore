// Copyright (c) 2026, AssetCore Team
//
// Sidebar collapsible grouping — Core Doc §7.bis
//   (docs/architecture/FE_Persona_Navigation.md)
//
// Logic THUẦN (unit-test được, tách khỏi AppSidebar.vue như routeAccess.ts):
//   - Persist danh sách group ĐANG ĐÓNG (theo `group.title`) vào localStorage.
//   - Mặc định: group không nằm trong danh sách đóng → MỞ (default expanded).
//   - Group active (chứa route hiện tại) → LUÔN mở dù persist đánh dấu đóng.
//
// KHÔNG đụng RBAC: collapse chỉ ẩn thị giác item, item vẫn thuộc tập được phép.
// Persist lỗi (private mode / quota) → fallback in-memory, không crash.

import type { SidebarGroup } from './sidebarNav'

/** Key localStorage — khác `ac_persona` (chọn persona) và `ac-sidebar` (icon-only). */
export const GROUPS_STORAGE_KEY = 'ac_sidebar_collapsed_groups'

/** Key localStorage cho nhóm GHIM (📌) — D7. Lên đầu + luôn expand. */
export const PINNED_GROUPS_KEY = 'ac_sidebar_pinned_groups'

// ─── D7 — Sidebar gọn cho persona đa-nhóm (ADR-IMM00-CMDK D7) ─────────────────
// THUẦN THỊ GIÁC: chỉ trạng thái expand/collapse của NHÓM. KHÔNG đụng
// itemVisible/resolveRouteAccess/capability (RBAC bất biến).
//
// "Nhóm ít dùng" = Governance/Compliance/Admin: phân loại TĨNH theo title
// (KHÔNG usage-tracking). Khớp MODULE_NAV.title của các module:
//   - imm16  'Theo dõi tuân thủ'    (Compliance/QMS)
//   - system 'Hệ thống'             (Admin/IAM + reference-data)
// Persona ≤ N nhóm (KTV/vendor) → KHÔNG collapse (expand hết). Persona > N → nhóm
// ít dùng default-collapsed, nhóm vận hành expanded.

/** Ngưỡng số nhóm: persona có > N nhóm → bật default-collapse nhóm ít dùng. */
export const LOW_USE_COLLAPSE_THRESHOLD = 4

/**
 * Title các nhóm "ít dùng" — collapse mặc định cho persona đa-nhóm.
 * Khớp CHÍNH XÁC MODULE_NAV.title (constants/sidebarNav.ts).
 */
export const LOW_USE_GROUP_TITLES: readonly string[] = [
  'Theo dõi tuân thủ', // imm16 — Compliance/QMS
  'Hệ thống',          // system — Admin/IAM + reference-data
] as const

/** True nếu nhóm thuộc nhóm "ít dùng" (phân loại tĩnh). */
export function isLowUseGroup(title: string): boolean {
  return LOW_USE_GROUP_TITLES.includes(title)
}

/** Đọc danh sách group đang đóng. Giá trị rác/null/non-array → [] (mọi group mở). */
export function readClosedGroups(): string[] {
  try {
    const raw = localStorage.getItem(GROUPS_STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((x): x is string => typeof x === 'string')
  } catch {
    return []
  }
}

/** Ghi danh sách group đang đóng. Lỗi quota/private-mode → bỏ qua (in-memory). */
export function writeClosedGroups(titles: readonly string[]): void {
  try {
    localStorage.setItem(GROUPS_STORAGE_KEY, JSON.stringify([...titles]))
  } catch {
    /* private mode / quota — bỏ qua, state vẫn chạy in-memory */
  }
}

/**
 * Toggle 1 group trong danh sách đóng, persist, trả về danh sách mới.
 * - Đang đóng → mở (xóa khỏi danh sách).
 * - Đang mở  → đóng (thêm vào danh sách).
 */
export function toggleClosedGroup(title: string): string[] {
  const closed = readClosedGroups()
  const next = closed.includes(title)
    ? closed.filter((t) => t !== title)
    : [...closed, title]
  writeClosedGroups(next)
  return next
}

/**
 * Quyết định 1 group có đang mở không.
 * - Active (title === activeGroupTitle) → luôn mở (không giấu chức năng đang dùng).
 * - Nằm trong danh sách đóng → đóng.
 * - Còn lại → mở (default expanded).
 */
export function isGroupOpen(
  group: SidebarGroup,
  closedTitles: readonly string[],
  activeGroupTitle: string | null,
): boolean {
  if (activeGroupTitle !== null && group.title === activeGroupTitle) return true
  return !closedTitles.includes(group.title)
}

// ─── D7 — Ghim nhóm + default-collapse (THUẦN THỊ GIÁC) ───────────────────────

/** Đọc danh sách nhóm GHIM. Rác/null/non-array → []. */
export function readPinnedGroups(): string[] {
  try {
    const raw = localStorage.getItem(PINNED_GROUPS_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((x): x is string => typeof x === 'string')
  } catch {
    return []
  }
}

/** Ghi danh sách nhóm ghim. Lỗi quota/private → bỏ qua (in-memory). */
export function writePinnedGroups(titles: readonly string[]): void {
  try {
    localStorage.setItem(PINNED_GROUPS_KEY, JSON.stringify([...titles]))
  } catch {
    /* private mode / quota */
  }
}

/** Toggle ghim 1 nhóm, persist, trả danh sách mới. */
export function togglePinnedGroup(title: string): string[] {
  const pinned = readPinnedGroups()
  const next = pinned.includes(title)
    ? pinned.filter((t) => t !== title)
    : [...pinned, title]
  writePinnedGroups(next)
  return next
}

/**
 * defaultClosedGroups — D7: tập nhóm collapse MẶC ĐỊNH (chỉ thị giác).
 *
 * - Persona có ≤ ngưỡng nhóm (KTV/vendor) → KHÔNG collapse gì ([]).
 * - Persona đa-nhóm (> ngưỡng) → collapse nhóm "ít dùng" (LOW_USE_GROUP_TITLES),
 *   TRỪ nhóm đã ghim (luôn expand) và nhóm active (luôn expand qua isGroupOpen).
 *
 * KHÔNG đụng items / itemVisible — chỉ dựa group.title. Số entry visible bất biến.
 *
 * @param groups danh sách nhóm ĐÃ qua itemVisible (buildSidebarGroupsForRoles)
 * @param pinned danh sách title nhóm ghim (readPinnedGroups)
 * @param threshold ngưỡng (mặc định LOW_USE_COLLAPSE_THRESHOLD = 4)
 */
export function defaultClosedGroups(
  groups: readonly SidebarGroup[],
  pinned: readonly string[] = [],
  threshold: number = LOW_USE_COLLAPSE_THRESHOLD,
): string[] {
  if (groups.length <= threshold) return []
  const pinnedSet = new Set(pinned)
  return groups
    .map((g) => g.title)
    .filter((t) => isLowUseGroup(t) && !pinnedSet.has(t))
}

/**
 * orderGroupsWithPins — nhóm ghim lên đầu (giữ thứ tự ghim), còn lại giữ nguyên
 * thứ tự gốc (persona.modules order). KHÔNG thêm/bớt nhóm → RBAC bất biến.
 */
export function orderGroupsWithPins(
  groups: readonly SidebarGroup[],
  pinned: readonly string[],
): SidebarGroup[] {
  if (pinned.length === 0) return [...groups]
  const pinnedSet = new Set(pinned)
  const pinnedGroups: SidebarGroup[] = []
  // Theo thứ tự pinned[] để ổn định.
  for (const title of pinned) {
    const g = groups.find((grp) => grp.title === title)
    if (g) pinnedGroups.push(g)
  }
  const rest = groups.filter((g) => !pinnedSet.has(g.title))
  return [...pinnedGroups, ...rest]
}
