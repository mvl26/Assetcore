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
