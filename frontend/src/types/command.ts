// Copyright (c) 2026, AssetCore Team
//
// CommandItem — shape của 1 lệnh trong Command Palette ⌘K (ADR-IMM00-CMDK D1).
//
// Registry (useCommandRegistry) DẪN XUẤT CommandItem từ 2 nguồn ĐÃ CÓ:
//   - source 'nav'   : flatten MODULE_NAV (constants/sidebarNav.ts) NavItem.
//   - source 'route' : route tĩnh không-nav có meta.title (router.getRoutes()).
// KHÔNG file commands.ts hardcode. Tách type ra type-module để utils/matchCommand
// + store + component cùng tham chiếu mà KHÔNG circular-import composable.

export type CommandSource = 'nav' | 'route'

export interface CommandItem {
  /** ID ổn định = path (route đích). Dùng cho dedupe + recent/pinned key. */
  id: string
  /** Nhãn tiếng Việt hiển thị (KHÔNG leak mã/English/jargon). */
  title: string
  /** Phụ đề tùy chọn — tên module/nhóm để phân biệt nhãn trùng. */
  subtitle?: string
  /** Icon key (tra ICONS trong AppSidebar/CommandPalette). */
  icon?: string
  /** Route đích — router.push(to). */
  to: string
  /**
   * Capability cần để THẤY lệnh (D2). undefined = mở cho mọi user đã xác thực.
   * string[] = OR. Lọc qua itemVisible (nav) / resolveRouteAccess (route).
   */
  cap?: string | readonly string[]
  /** Nguồn dẫn xuất — quyết định predicate gate áp dụng (D2). */
  source: CommandSource
  /** moduleId (chỉ source 'nav') — để gom nhóm / subtitle. */
  moduleId?: string
}
